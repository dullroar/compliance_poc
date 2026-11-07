"""Offline proof of opt-in, durable budget accounting, and request limits."""
import json
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from test_openai_live_smoke import (BUDGET, MAX_REQUESTS, REQUEST_BOUND, BudgetError,
    GuardedResponses, Ledger, LiveRequestError, actual_estimate, estimate, read_usage, MODEL, OUTPUT_LIMIT)


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'ledger.jsonl'
        self.ledger = Ledger(self.path)

    def rows(self):
        return [json.loads(line) for line in self.path.read_text().splitlines()]

    def test_live_test_skips_without_opt_in(self):
        import test_openai_live_smoke as live
        with patch.dict(os.environ, {'RUN_LIVE_OPENAI_TESTS': ''}):
            namespace = {'__name__': 'offline_probe', '__file__': live.__file__}
            exec(compile(Path(live.__file__).read_text(), live.__file__, 'exec'), namespace)
            self.assertTrue(namespace['OpenAILiveSmoke'].__unittest_skip__)

    def test_usage_includes_nested_counts_and_cost_never_double_counts_reasoning(self):
        response = {'usage': {'input_tokens': 100, 'output_tokens': 20, 'total_tokens': 120,
                    'input_tokens_details': {'cached_tokens': 40, 'cache_write_tokens': 30,
                        'cache_write_tokens_details': {'ttl_30m_tokens': 30, 'ttl_12h_tokens': 0}},
                    'output_tokens_details': {'reasoning_tokens': 10}}}
        usage = read_usage(response)
        self.assertEqual((usage['cached_input_tokens'], usage['cache_write_30m_tokens'], usage['reasoning_tokens']), (40, 30, 10))
        self.assertEqual(estimate(usage), Decimal('0.0000715'))
        self.assertEqual(actual_estimate(usage, 'default'), Decimal('0.00001715'))
        usage['reasoning_tokens'] = 20
        self.assertEqual(estimate(usage), Decimal('0.0000715'))
        usage['total_tokens'] = 121
        self.assertIsNone(estimate(usage))

    def test_long_context_and_unknown_rates(self):
        usage = {'input_tokens': 300000, 'output_tokens': 2000, 'total_tokens': 302000,
                 'cached_input_tokens': 50000, 'cache_write_tokens': 50000,
                 'cache_write_30m_tokens': 30000, 'cache_write_12h_tokens': 20000}
        # Long input and cache rates double; the output rate is 1.5 times short.
        self.assertEqual(actual_estimate(usage, 'default'), Decimal('0.060'))
        self.assertIsNone(actual_estimate(usage, 'priority'))
        usage['cache_write_12h_tokens'] = None
        self.assertIsNone(actual_estimate(usage, 'default'))
        self.assertIsNotNone(estimate(usage))

    def test_unreported_service_tier_keeps_full_reservation(self):
        self.ledger.start_cycle('tier')
        seq = self.ledger.start_request('tier', 'seeded')
        self.ledger.outcome('tier', 'seeded', seq, 'response',
                            {'input_tokens': 100, 'output_tokens': 20, 'total_tokens': 120}, 1)
        self.ledger.end_cycle('tier', {}, 1)
        _, incurred, reserved = Ledger.state(self.rows())
        self.assertEqual((incurred, reserved), (0, REQUEST_BOUND))

    def test_cycle_cap_and_restart_budget_recovery(self):
        self.ledger.start_cycle('a')
        for n in range(1, MAX_REQUESTS + 1):
            self.assertEqual(Ledger(self.path).start_request('a', 'seeded'), n)
        with self.assertRaises(BudgetError):
            self.ledger.start_request('a', 'model')
        self.ledger.end_cycle('a', {}, 1)
        _, incurred, reserved = Ledger.state(self.rows())
        self.assertEqual(incurred, 0)
        self.assertEqual(reserved, REQUEST_BOUND * MAX_REQUESTS)
        n = 0
        while incurred + reserved + MAX_REQUESTS * REQUEST_BOUND <= BUDGET:
            n += 1
            Ledger(self.path).start_cycle('restart-' + str(n))
            _, incurred, reserved = Ledger.state(self.rows())
        with self.assertRaises(BudgetError):
            Ledger(self.path).start_cycle('over-budget')

    def test_missing_usage_and_timeout_keep_reservation_and_release_unused(self):
        self.ledger.start_cycle('timeout')
        seq = self.ledger.start_request('timeout', 'model')
        self.ledger.outcome('timeout', 'model', seq, 'TimeoutError', None, 2)
        self.ledger.end_cycle('timeout', {}, 2)
        _, incurred, reserved = Ledger.state(self.rows())
        self.assertEqual((incurred, reserved), (0, REQUEST_BOUND))
        self.assertIsNone(self.rows()[-2]['estimated_cost_usd'])

    def test_known_usage_retry_and_mode_totals(self):
        self.ledger.start_cycle('ok')
        usage = {'input_tokens': 100, 'output_tokens': 20, 'total_tokens': 120}
        for mode in ('seeded', 'model', 'model'):
            seq = self.ledger.start_request('ok', mode)
            self.ledger.outcome('ok', mode, seq, 'response', usage, 0.1, 'default')
        self.ledger.end_cycle('ok', {'seeded': {'passed': True}, 'model': {'passed': True}}, 2)
        row = self.rows()[-1]
        self.assertEqual(row['modes']['model']['requests'], 2)
        self.assertEqual(row['modes']['seeded']['requests'], 1)
        self.assertEqual(row['successful_narratives'], 2)
        _, incurred, reserved = Ledger.state(self.rows())
        self.assertEqual(incurred, 3 * estimate(usage))
        self.assertEqual(reserved, 0)

    def test_guard_records_before_network_and_sanitizes_failures(self):
        self.ledger.start_cycle('guard')
        parent = self
        class Delegate:
            def create(self, **kwargs):
                parent.assertEqual(parent.rows()[-1]['event'], 'request_reservation')
                raise TimeoutError('sensitive data must not be recorded')
        guard = GuardedResponses(Delegate(), self.ledger, 'guard')
        guard.mode = 'seeded'
        with self.assertRaises(LiveRequestError) as caught:
            guard.create(model=MODEL, store=False, max_output_tokens=OUTPUT_LIMIT)
        self.assertNotIn('sensitive', str(caught.exception))
        self.assertNotIn('sensitive', self.path.read_text())
        self.assertEqual(self.rows()[-1]['outcome'], 'TimeoutError')

    def test_malformed_ledger_refuses_to_spend(self):
        self.path.write_text('{partial')
        with self.assertRaises(BudgetError):
            self.ledger.start_cycle('new')

    def test_a2a_harness_reaches_both_modes_with_sdk_fake_and_real_mcp(self):
        import test_openai_live_smoke as live
        from test_openai_backend import NARRATIVE
        calls = []
        usage = {'input_tokens': 100, 'output_tokens': 20, 'total_tokens': 120,
                 'input_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 0,
                     'cache_write_tokens_details': {'ttl_30m_tokens': 0, 'ttl_12h_tokens': 0}},
                 'output_tokens_details': {'reasoning_tokens': 0}}
        class Responses:
            def create(self, **request):
                calls.append(request.get('tool_choice'))
                if isinstance(request.get('tool_choice'), dict):
                    item = SimpleNamespace(type='function_call', name='ybs_evaluate', arguments='{}', call_id='fake-call')
                    return SimpleNamespace(output=[item], output_text='', usage=usage, service_tier='default')
                return SimpleNamespace(output=[], output_text=json.dumps(NARRATIVE), usage=usage, service_tier='default')
        class Client:
            def __init__(self, **kwargs):
                self.responses = Responses()
            def close(self):
                pass
        with patch('openai.OpenAI', Client), patch.object(live, 'LEDGER', self.path), \
                patch.object(live, 'PRICE_CHECKED', datetime.now(ZoneInfo('America/Denver')).date().isoformat()), \
                patch.dict(os.environ, {'OPENAI_API_KEY': 'offline-placeholder'}):
            live.OpenAILiveSmoke('test_seeded_and_model_a2a_paths').test_seeded_and_model_a2a_paths()
        self.assertEqual(len(calls), 3)
        self.assertEqual(self.rows()[-1]['successful_narratives'], 2)


def legacy_state(rows):
    """The pre-generalization Ledger.state, kept verbatim as the reference that old rows must still replay to."""
    cycles = {}
    for row in rows:
        kind, cid = row.get('event'), row.get('cycle_id')
        if kind == 'cycle_reservation':
            if cid in cycles:
                raise BudgetError('Duplicate cycle in ledger')
            cycles[cid] = {'bound': Decimal(row['request_bound_usd']), 'slots': MAX_REQUESTS,
                           'starts': {}, 'resolved': {}, 'released': 0, 'ended': False}
        elif kind in ('request_reservation', 'request_outcome', 'cycle_end'):
            if cid not in cycles:
                raise BudgetError('Orphan ledger event')
            c = cycles[cid]
            if kind == 'request_reservation':
                seq = row['sequence']
                if c['ended'] or seq in c['starts'] or len(c['starts']) >= MAX_REQUESTS:
                    raise BudgetError('Invalid request reservation')
                c['starts'][seq] = row
            elif kind == 'request_outcome':
                seq = row['sequence']
                if seq not in c['starts'] or seq in c['resolved']:
                    raise BudgetError('Invalid request outcome')
                c['resolved'][seq] = row
            else:
                if c['ended']:
                    raise BudgetError('Duplicate cycle end')
                c['ended'] = True
                c['released'] = MAX_REQUESTS - len(c['starts'])
    incurred, reserved = Decimal(0), Decimal(0)
    for c in cycles.values():
        known = [Decimal(x['budget_charge_usd']) for x in c['resolved'].values() if x.get('budget_charge_usd') is not None]
        incurred += sum(known, Decimal(0))
        reserved += c['bound'] * (MAX_REQUESTS - c['released'] - len(known))
    return cycles, incurred, reserved


class GeneralizedLedgerTests(unittest.TestCase):
    """A cycle may carry its own request count, per-request bound and input bound; legacy rows replay unchanged."""

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'ledger.jsonl'
        self.ledger = Ledger(self.path)

    def rows(self):
        return [json.loads(line) for line in self.path.read_text().splitlines()]

    def test_the_archived_ledger_replays_to_identical_totals(self):
        archived = Path(__file__).resolve().parents[1] / 'plans/archive/openai-smoketest/runs.jsonl'
        rows = [json.loads(line) for line in archived.read_text().splitlines() if line.strip()]
        # Cycles written with the original six-request bounds must replay identically; later registry-wide cycles carry
        # their own bounds (more than six requests) and are outside what the old implementation can read.
        legacy = {r['cycle_id'] for r in rows if r.get('event') == 'cycle_reservation'
                  and r.get('max_requests') == MAX_REQUESTS and Decimal(r['request_bound_usd']) == REQUEST_BOUND}
        rows = [r for r in rows if r.get('cycle_id') in legacy]
        self.assertTrue(rows)
        old, new = legacy_state(rows), Ledger.state(rows)
        self.assertEqual((old[1], old[2]), (new[1], new[2]))
        self.assertEqual({k: (v['bound'], v['slots'], v['released'], v['ended']) for k, v in old[0].items()},
                         {k: (v['bound'], v['slots'], v['released'], v['ended']) for k, v in new[0].items()})

    def test_generated_legacy_cycles_and_rows_without_optional_fields_replay_identically(self):
        self.ledger.start_cycle('a')
        usage = {'input_tokens': 100, 'output_tokens': 20, 'total_tokens': 120}
        for mode in ('seeded', 'model', 'model'):
            seq = self.ledger.start_request('a', mode)
            self.ledger.outcome('a', mode, seq, 'response', usage, 0.1, 'default')
        self.ledger.start_cycle('b')
        self.ledger.start_request('b', 'seeded')
        self.ledger.end_cycle('a', {}, 1)
        rows = self.rows()
        self.assertTrue(all('role' not in r for r in rows))
        stripped = [{k: v for k, v in r.items() if k != 'max_requests'} for r in rows]       # rows written before the field existed
        for candidate in (rows, stripped):
            self.assertEqual(legacy_state(candidate)[1:], Ledger.state(candidate)[1:])
        self.assertEqual(self.rows()[0]['max_requests'], MAX_REQUESTS)
        self.assertEqual(self.rows()[0]['input_bound_tokens'], 1_050_000)

    def test_a_cycle_with_its_own_bounds_reserves_and_releases_by_its_own_slots(self):
        bound = Decimal('0.0617584')
        self.ledger.start_cycle('p', 56, bound, 100_000)
        row = self.rows()[0]
        self.assertEqual((row['max_requests'], row['request_bound_usd'], row['cycle_bound_usd'], row['input_bound_tokens']),
                         (56, '0.0617584', str(56 * bound), 100_000))
        _, incurred, reserved = Ledger.state(self.rows())
        self.assertEqual((incurred, reserved), (0, 56 * bound))
        for n in range(1, 57):
            self.assertEqual(self.ledger.start_request('p', 'model', 'ybs'), n)
        with self.assertRaises(BudgetError):
            self.ledger.start_request('p', 'model', 'ybs')
        self.assertEqual({r['role'] for r in self.rows() if r['event'] == 'request_reservation'}, {'ybs'})
        self.ledger.end_cycle('p', {}, 1)
        self.assertEqual(Ledger.state(self.rows())[2], 56 * bound)       # all 56 started, none resolved: fully retained
        self.ledger.start_cycle('q', 20, bound, 100_000)
        for _ in range(5):
            self.ledger.start_request('q', 'seeded', 'hmda')
        self.ledger.end_cycle('q', {}, 1)
        self.assertEqual(Ledger.state(self.rows())[2], 56 * bound + 5 * bound)    # the 15 unused slots were released

    def test_role_labels_are_optional_and_recorded_on_outcomes_too(self):
        self.ledger.start_cycle('r', 3, Decimal('0.06'), 100_000)
        a = self.ledger.start_request('r', 'model', 'hmda')
        b = self.ledger.start_request('r', 'model')
        usage = {'input_tokens': 100, 'output_tokens': 20, 'total_tokens': 120}
        self.ledger.outcome('r', 'model', a, 'response', usage, 0.1, 'default', role='hmda')
        self.ledger.outcome('r', 'model', b, 'response', usage, 0.1, 'default')
        rows = {(r['event'], r['sequence']): r for r in self.rows() if 'sequence' in r}
        self.assertEqual(rows[('request_reservation', 1)]['role'], 'hmda')
        self.assertEqual(rows[('request_outcome', 1)]['role'], 'hmda')
        self.assertNotIn('role', rows[('request_reservation', 2)])
        self.assertNotIn('role', rows[('request_outcome', 2)])

    def test_end_cycle_counts_the_supplied_successes_and_the_expected_denominator(self):
        usage = {'input_tokens': 100, 'output_tokens': 20, 'total_tokens': 120,
                 'input_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 0,
                                          'cache_write_tokens_details': {'ttl_30m_tokens': 0, 'ttl_12h_tokens': 0}},
                 'output_tokens_details': {'reasoning_tokens': 0}}
        flat = read_usage({'usage': usage})
        self.ledger.start_cycle('s', 4, Decimal('0.06'), 100_000)
        for _ in range(4):
            seq = self.ledger.start_request('s', 'model', 'ybs')
            self.ledger.outcome('s', 'model', seq, 'response', flat, 0.1, 'default', role='ybs')
        self.ledger.end_cycle('s', {'model': {'passed': True}}, 1, successes=3, expected_successes=4)
        end = self.rows()[-1]
        self.assertEqual(end['successful_narratives'], 3)
        self.assertIsNone(end['cost_per_completed_cycle_usd'])                # 3 of 4 is not a completed cycle
        self.assertLess(abs(Decimal(end['cost_per_successful_narrative_usd']) * 3 - Decimal(end['estimated_cost_usd'])), Decimal('1e-20'))
        self.ledger.start_cycle('t', 2, Decimal('0.06'), 100_000)
        for _ in range(2):
            seq = self.ledger.start_request('t', 'model', 'ybs')
            self.ledger.outcome('t', 'model', seq, 'response', flat, 0.1, 'default')
        self.ledger.end_cycle('t', {}, 1, successes=2, expected_successes=2)
        self.assertIsNotNone(self.rows()[-1]['cost_per_completed_cycle_usd'])

    def test_invalid_cycle_bounds_are_refused_without_writing(self):
        for args in ((0, Decimal('0.06'), 100_000), (81, Decimal('0.06'), 100_000), (5, Decimal(0), 100_000),
                     (5, Decimal('0.06'), 0), (5, Decimal('0.06'), 2_000_000), (True, Decimal('0.06'), 100_000), (2.5, Decimal('0.06'), 100_000)):
            with self.subTest(args=args), self.assertRaises(BudgetError):
                self.ledger.start_cycle('bad', *args)
        self.assertFalse(self.path.exists() and self.path.read_text())

    def test_the_shared_cumulative_cap_holds_across_mixed_cycles_and_restarts(self):
        self.ledger.start_cycle('legacy')                                      # 6 x 0.5842584 held
        bound, n = Decimal('0.0617584'), 0
        _, incurred, reserved = Ledger.state(self.rows())
        while incurred + reserved + 56 * bound <= BUDGET:
            n += 1
            Ledger(self.path).start_cycle(f'parity-{n}', 56, bound, 100_000)
            _, incurred, reserved = Ledger.state(self.rows())
        self.assertGreaterEqual(n, 4)
        self.assertLessEqual(incurred + reserved, BUDGET)
        with self.assertRaises(BudgetError):
            Ledger(self.path).start_cycle('one-too-many', 56, bound, 100_000)
        with self.assertRaises(BudgetError):                                   # a legacy cycle is held to the same cap
            Ledger(self.path).start_cycle('legacy-too-many')


if __name__ == '__main__':
    unittest.main()

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


if __name__ == '__main__':
    unittest.main()

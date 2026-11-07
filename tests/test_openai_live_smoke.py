"""Opt-in synthetic YBS smoke test and durable Responses spending guard.

The ledger contains metadata only. It never stores request or response bodies.
"""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
import fcntl
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import sys
import time
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / 'plans/archive/openai-smoketest/runs.jsonl'
MODEL = 'gpt-6-luna'
PRICING_URL = 'https://developers.openai.com/api/docs/models/gpt-6-luna'
PRICE_CHECKED = '2026-11-07'
BUDGET = Decimal('20')
MAX_REQUESTS = 6
# Model context window is a hard ceiling. Include long-context prices, 12-hour
# cache-write rate for every input token, and a 10% regional uplift.
# This deliberately over-reserves rather than guessing request tokenization.
CONTEXT_LIMIT = 1_050_000
OUTPUT_LIMIT = 8192
RATES = {'input': '0.20', 'cached_input': '0.02', 'cache_write_30m': '0.25',
         'cache_write_12h': '0.50', 'output': '0.75', 'uplift': '1.10'}
SHORT_RATES = {'input': '0.10', 'cached_input': '0.01', 'cache_write_30m': '0.125',
               'cache_write_12h': '0.25', 'output': '0.50'}
REQUEST_BOUND = ((Decimal(CONTEXT_LIMIT) * Decimal(RATES['cache_write_12h'])
                  + Decimal(OUTPUT_LIMIT) * Decimal(RATES['output'])) * Decimal(RATES['uplift']) / Decimal(1_000_000))
COMMAND = 'RUN_LIVE_OPENAI_TESTS=1 python3 -m unittest discover -s tests -p test_openai_live_smoke.py -v'
# Registry-wide live parity profile (plans/archive/live-parity): a cycle may carry its own request count, per-request bound and input
# bound. Legacy rows carry the constants above and replay to identical totals.
PARITY_INPUT_BOUND_TOKENS = 100_000          # UTF-8 bytes bound tokens from above; the guarded client refuses larger requests
PARITY_MAX_REQUESTS = 80
PARITY_REQUEST_BOUND = ((Decimal(PARITY_INPUT_BOUND_TOKENS) * Decimal(RATES['cache_write_12h'])
                         + Decimal(OUTPUT_LIMIT) * Decimal(RATES['output'])) * Decimal(RATES['uplift']) / Decimal(1_000_000))


class BudgetError(Exception):
    pass


class LiveRequestError(Exception):
    """An intentionally sanitized transport/API failure."""


def now():
    return datetime.now(timezone.utc).isoformat()


def get(obj, key):
    return obj.get(key) if isinstance(obj, dict) else getattr(obj, key, None)


def read_usage(response):
    usage = get(response, 'usage')
    details = get(usage, 'input_tokens_details')
    writes = get(details, 'cache_write_tokens_details')
    output_details = get(usage, 'output_tokens_details')
    return {'input_tokens': get(usage, 'input_tokens'), 'cached_input_tokens': get(details, 'cached_tokens'),
            'cache_write_tokens': get(details, 'cache_write_tokens'),
            'cache_write_30m_tokens': get(writes, 'ttl_30m_tokens'),
            'cache_write_12h_tokens': get(writes, 'ttl_12h_tokens'),
            'output_tokens': get(usage, 'output_tokens'), 'reasoning_tokens': get(output_details, 'reasoning_tokens'),
            'total_tokens': get(usage, 'total_tokens')}


def estimate(usage):
    """Conservative charge based on total input/output, without double counting cache or reasoning.

    Since cache-write details may be absent, price every input token once at
    the highest documented write rate. Long-context and regional
    prices are used even for shorter requests; this is an upper estimate.
    """
    i, o, total = (usage.get(k) for k in ('input_tokens', 'output_tokens', 'total_tokens'))
    if any(type(v) is not int or v < 0 for v in (i, o, total)) or total != i + o:
        return None
    if i > CONTEXT_LIMIT or o > OUTPUT_LIMIT:
        return None
    return ((Decimal(i) * Decimal(RATES['cache_write_12h'])
             + Decimal(o) * Decimal(RATES['output'])) * Decimal(RATES['uplift']) / Decimal(1_000_000))


def actual_estimate(usage, service_tier):
    """Documented standard rates, using non-overlapping input categories."""
    if service_tier != 'default' or estimate(usage) is None:
        return None
    keys = ('cached_input_tokens', 'cache_write_tokens', 'cache_write_30m_tokens', 'cache_write_12h_tokens')
    values = [usage.get(key) for key in keys]
    if any(type(v) is not int or v < 0 for v in values):
        return None
    cached, written, w30, w12 = values
    i, o = usage['input_tokens'], usage['output_tokens']
    if written != w30 + w12 or cached + written > i:
        return None
    long_context = i > 272_000
    factor = Decimal(2) if long_context else Decimal(1)
    output_rate = Decimal('0.75') if long_context else Decimal('0.50')
    cost = ((Decimal(i-cached-written)*Decimal('0.10') + Decimal(cached)*Decimal('0.01')
             + Decimal(w30)*Decimal('0.125') + Decimal(w12)*Decimal('0.25'))*factor
            + Decimal(o)*output_rate) / Decimal(1_000_000)
    return cost


class Ledger:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else LEDGER

    @contextmanager
    def locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open('a+', encoding='utf-8') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0)
            try:
                rows = [json.loads(line) for line in f if line.strip()]
            except (ValueError, UnicodeError) as exc:
                raise BudgetError('Ledger unreadable; refusing to spend') from exc
            yield f, rows

    @staticmethod
    def append(f, event):
        event['timestamp'] = now()
        f.seek(0, os.SEEK_END)
        f.write(json.dumps(event, sort_keys=True, separators=(',', ':')) + '\n')
        f.flush()
        os.fsync(f.fileno())

    @staticmethod
    def state(rows):
        cycles = {}
        for row in rows:
            kind, cid = row.get('event'), row.get('cycle_id')
            if kind == 'cycle_reservation':
                if cid in cycles:
                    raise BudgetError('Duplicate cycle in ledger')
                cycles[cid] = {'bound': Decimal(row['request_bound_usd']), 'slots': row.get('max_requests', MAX_REQUESTS),
                               'starts': {}, 'resolved': {}, 'released': 0, 'ended': False}
            elif kind in ('request_reservation', 'request_outcome', 'cycle_end'):
                if cid not in cycles:
                    raise BudgetError('Orphan ledger event')
                c = cycles[cid]
                if kind == 'request_reservation':
                    seq = row['sequence']
                    if c['ended'] or seq in c['starts'] or len(c['starts']) >= c['slots']:
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
                    c['released'] = c['slots'] - len(c['starts'])
        incurred, reserved = Decimal(0), Decimal(0)
        for c in cycles.values():
            known = [Decimal(x['budget_charge_usd']) for x in c['resolved'].values()
                     if x.get('budget_charge_usd') is not None]
            incurred += sum(known, Decimal(0))
            reserved += c['bound'] * (c['slots'] - c['released'] - len(known))
        return cycles, incurred, reserved

    def start_cycle(self, cycle_id, max_requests=None, request_bound=None, input_bound_tokens=None, command=None):
        max_requests = MAX_REQUESTS if max_requests is None else max_requests
        request_bound = REQUEST_BOUND if request_bound is None else request_bound
        input_bound_tokens = CONTEXT_LIMIT if input_bound_tokens is None else input_bound_tokens
        if type(max_requests) is not int or not 1 <= max_requests <= PARITY_MAX_REQUESTS or request_bound <= 0 or not 0 < input_bound_tokens <= CONTEXT_LIMIT:
            raise BudgetError('Invalid cycle bounds')
        with self.locked() as (f, rows):
            cycles, incurred, reserved = self.state(rows)
            if cycle_id in cycles or incurred + reserved + max_requests * request_bound > BUDGET:
                raise BudgetError('Cycle reservation would exceed cumulative budget')
            self.append(f, {'event': 'cycle_reservation', 'cycle_id': cycle_id, 'model': MODEL,
                            'service_tier': 'default', 'max_requests': max_requests,
                            'request_bound_usd': str(request_bound), 'cycle_bound_usd': str(max_requests * request_bound),
                            'input_bound_tokens': input_bound_tokens, 'output_bound_tokens': OUTPUT_LIMIT,
                            'pricing_url': PRICING_URL, 'pricing_checked': PRICE_CHECKED,
                            'short_rates_usd_per_million': SHORT_RATES, 'long_rates_usd_per_million': RATES,
                            'long_context_threshold_input_tokens': 272000,
                            'python_version': sys.version.split()[0], 'sdk_version': importlib.metadata.version('openai'),
                            'command': command or COMMAND, 'cumulative_incurred_usd': str(incurred),
                            'cumulative_reserved_usd': str(reserved + max_requests * request_bound)})

    def start_request(self, cycle_id, mode, role=None):
        with self.locked() as (f, rows):
            cycles, incurred, reserved = self.state(rows)
            c = cycles[cycle_id]
            if c['ended'] or len(c['starts']) >= c['slots'] or incurred + reserved > BUDGET:
                raise BudgetError('Request limit or budget exceeded')
            seq = len(c['starts']) + 1
            self.append(f, {'event': 'request_reservation', 'cycle_id': cycle_id, 'mode': mode, 'sequence': seq,
                            'model': MODEL, 'service_tier': 'default', 'reservation_usd': str(c['bound']),
                            **({'role': role} if role is not None else {})})
            return seq

    def outcome(self, cycle_id, mode, seq, outcome, usage, elapsed, service_tier=None, role=None):
        # Only settle against the budget when the actual processing tier is
        # reported and matches the explicitly requested standard tier.
        cost = estimate(usage) if usage and service_tier == 'default' else None
        actual = actual_estimate(usage, service_tier) if usage else None
        with self.locked() as (f, rows):
            cycles, _, _ = self.state(rows)
            c = cycles[cycle_id]
            if seq not in c['starts'] or seq in c['resolved'] or (cost is not None and cost > c['bound']):
                raise BudgetError('Invalid outcome or charge exceeds reservation')
            self.append(f, {'event': 'request_outcome', 'cycle_id': cycle_id, 'mode': mode, 'sequence': seq,
                            **({'role': role} if role is not None else {}), 'outcome': outcome, 'elapsed_seconds': round(elapsed, 3), 'usage': usage,
                            'service_tier': service_tier,
                            'estimated_cost_usd': str(actual) if actual is not None else None,
                            'budget_charge_usd': str(cost) if cost is not None else None,
                            'estimate_kind': 'standard price estimate' if actual is not None else 'unavailable; conservative budget charge or reservation retained',
                            'unknown_explanation': 'API usage or service tier missing, inconsistent, or unexpected' if cost is None else
                                ('Some usage breakdown fields not reported' if any(v is None for v in usage.values()) else None)})

    def end_cycle(self, cycle_id, outcomes, elapsed, successes=None, expected_successes=2):
        with self.locked() as (f, rows):
            cycles, incurred, reserved = self.state(rows)
            c = cycles[cycle_id]
            if c['ended']:
                raise BudgetError('Cycle already ended')
            modes = {}
            usage_keys = ('input_tokens', 'cached_input_tokens', 'cache_write_tokens', 'cache_write_30m_tokens',
                          'cache_write_12h_tokens', 'output_tokens', 'reasoning_tokens', 'total_tokens')
            def aggregate(results):
                totals = {}
                for key in usage_keys:
                    values = [(x.get('usage') or {}).get(key) if x else None for x in results]
                    totals[key] = sum(values) if values and all(type(v) is int for v in values) else None
                return totals
            for mode in ('seeded', 'model'):
                starts = [x for x in c['starts'].values() if x['mode'] == mode]
                results = [c['resolved'].get(x['sequence']) for x in starts]
                known = [Decimal(x['budget_charge_usd']) for x in results if x and x.get('budget_charge_usd') is not None]
                exact = [x.get('estimated_cost_usd') if x else None for x in results]
                exact_mode = sum((Decimal(x) for x in exact), Decimal(0)) if exact and all(x is not None for x in exact) else None
                modes[mode] = {'requests': len(starts), 'known_cost_usd': str(sum(known, Decimal(0))),
                               'estimated_cost_usd': str(exact_mode) if exact_mode is not None else None,
                               'unknown_requests': len(starts)-len(known), 'usage_totals': aggregate(results),
                               'outcome': outcomes.get(mode)}
            released = c['bound'] * (c['slots']-len(c['starts']))
            all_results = [c['resolved'].get(x) for x in c['starts']]
            exact_costs = [x.get('estimated_cost_usd') if x else None for x in all_results]
            exact_total = sum((Decimal(x) for x in exact_costs), Decimal(0)) if exact_costs and all(x is not None for x in exact_costs) else None
            if successes is None:
                successes = sum(1 for x in outcomes.values() if x and x.get('passed'))
            completed = successes == expected_successes
            self.append(f, {'event': 'cycle_end', 'cycle_id': cycle_id, 'modes': modes,
                            'elapsed_seconds': round(elapsed, 3), 'requests': len(c['starts']),
                            'usage_totals': aggregate(all_results),
                            'estimated_cost_usd': str(exact_total) if exact_total is not None else None,
                            'cumulative_incurred_usd': str(incurred), 'cumulative_reserved_usd': str(reserved-released),
                            'successful_narratives': successes,
                            'cost_per_successful_narrative_usd': str(exact_total / successes) if exact_total is not None and successes else None,
                            'cost_per_completed_cycle_usd': str(exact_total) if exact_total is not None and completed else None,
                            'cost_ratio_explanation': None if exact_total is not None and completed else 'Complete usage or successful denominator unavailable'})


class GuardedResponses:
    def __init__(self, delegate, ledger, cycle_id, validate=None):
        self.delegate, self.ledger, self.cycle_id, self.mode = delegate, ledger, cycle_id, None
        self.validate = validate

    def create(self, **request):
        if (request.get('model') != MODEL or request.get('store') is not False
                or request.get('max_output_tokens') != OUTPUT_LIMIT):
            raise BudgetError('Unexpected request configuration')
        if self.validate:
            self.validate(request, self.mode)
        request['service_tier'] = 'default'
        seq = self.ledger.start_request(self.cycle_id, self.mode)
        started = time.monotonic()
        try:
            response = self.delegate.create(**request)
        except BaseException as exc:
            self.ledger.outcome(self.cycle_id, self.mode, seq, type(exc).__name__, None, time.monotonic()-started)
            if not isinstance(exc, Exception):
                raise
            raise LiveRequestError('OpenAI request failed: ' + type(exc).__name__) from None
        self.ledger.outcome(self.cycle_id, self.mode, seq, 'response', read_usage(response), time.monotonic()-started,
                            get(response, 'service_tier'))
        return response


@unittest.skipUnless(os.getenv('RUN_LIVE_OPENAI_TESTS') == '1', 'set RUN_LIVE_OPENAI_TESTS=1 for live OpenAI smoke test')
class OpenAILiveSmoke(unittest.TestCase):
    def test_seeded_and_model_a2a_paths(self):
        import httpx
        import jsonschema
        from dotenv import dotenv_values
        from openai import OpenAI
        from google.protobuf.json_format import MessageToDict, ParseDict
        from google.protobuf.struct_pb2 import Struct
        from agent_prompts import AGENTS
        from agents.a2a_server import ComplianceExecutor, build_app
        from agents.backends import Backend
        import agents.runner as runner
        from compliance_common.narrative_schema import NARRATIVE_SCHEMA
        from compliance_common.regulations import regulation_text
        from compliance_mcp.registry import adapter
        from compliance_mcp.ybs import evaluate_ybs
        from compliance_mcp.ybs.server import server as ybs_server
        from orchestrator.a2a_client import send
        from zoneinfo import ZoneInfo

        self.assertEqual(datetime.now(ZoneInfo('America/Denver')).date().isoformat(), PRICE_CHECKED,
                         'Pricing must be freshly verified and updated before another day of testing')
        key = os.getenv('OPENAI_API_KEY') or dotenv_values(ROOT / '.env').get('OPENAI_API_KEY')
        self.assertTrue(key, 'OPENAI_API_KEY is required')
        case = json.loads((ROOT / 'sample_ybs_case.json').read_text(encoding='utf-8'))
        loan = {'case_information': {'case_id': case['case_id']}, 'ybs_case': case}
        # A2A data parts use protobuf Struct, which represents JSON numbers as
        # doubles; direct parity must use the exact facts the receiver sees.
        loan = MessageToDict(ParseDict(loan, Struct()))
        case = loan['ybs_case']
        canonical, reason = adapter('ybs').tool_arguments(loan)
        self.assertFalse(reason)
        direct = evaluate_ybs(case)
        reg, provenance = regulation_text('ybs')
        self.assertTrue(reg and provenance, 'Regulations must be present')
        expected_system = AGENTS['ybs']['system_prompt'] + '\n\n' + runner.REGULATIONS_HEADER + reg
        expected_user = runner._narration_input(AGENTS['ybs'], 'ybs', loan, canonical, adapter('ybs'))
        expected_prefix, expected_case_json = expected_user.split('\n\n', 1)
        expected_case = json.loads(expected_case_json)

        def validate_request(request, mode):
            # All first-request sources are the inspected repository prompt, YBS
            # regulation snapshot and fixture. Subsequent turns add only this
            # evaluator's output, model-generated content and guard feedback.
            if request.get('instructions') != expected_system or mode not in ('seeded', 'model'):
                raise BudgetError('Unexpected outbound instructions or mode')
            items = request.get('input')
            if not isinstance(items, list) or not items or not isinstance(items[0], dict):
                raise BudgetError('Unexpected outbound input')
            first = items[0]
            content = first.get('content', '')
            if first.get('role') != 'user' or not content.startswith(expected_prefix + '\n\n'):
                raise BudgetError('Unexpected outbound case')
            try:
                case_data, _ = json.JSONDecoder().raw_decode(content[len(expected_prefix) + 2:])
            except (TypeError, ValueError):
                raise BudgetError('Unexpected outbound case encoding') from None
            if case_data != expected_case:
                raise BudgetError('Unexpected outbound case facts')
            if request.get('tools') and any(t.get('type') != 'function' or t.get('name') != 'ybs_evaluate' for t in request['tools']):
                raise BudgetError('Unexpected outbound tool')
            if len(items) >= 3 and isinstance(items[1], dict) and items[1].get('type') == 'function_call' and mode == 'seeded':
                seeded_result = json.loads(items[2]['output'])
                if (json.loads(items[1]['arguments']) != canonical
                        or seeded_result.get('decision_id') != direct['decision_id']
                        or seeded_result.get('final_classification') != direct['final_classification']):
                    raise BudgetError('Seeded exchange differs from canonical decision')

        ledger, cycle_id = Ledger(), uuid.uuid4().hex
        ledger.start_cycle(cycle_id)
        outcomes, start, calls = {}, time.monotonic(), []
        old_disable = logging.root.manager.disable
        logging.disable(logging.CRITICAL)
        client = None
        try:
            client = OpenAI(api_key=key, base_url='https://api.openai.com/v1', timeout=60.0, max_retries=0)
            guarded = GuardedResponses(client.responses, ledger, cycle_id, validate_request)
            client.responses = guarded
            backend = Backend('openai', MODEL, client=client)
            original_call = runner.call_tool

            async def capture_call(target, name, arguments):
                calls.append((name, arguments))
                return await original_call(target, name, arguments)

            async def run_mode(mode):
                url = 'http://ybs.test/'
                executor = ComplianceExecutor('ybs', backend=backend, tool_target=ybs_server, options={'tool_mode': mode})
                app = build_app('ybs', url, executor)
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=url) as http:
                    return await send(url, loan, http)

            with patch('agents.runner.call_tool', capture_call):
                for mode in ('seeded', 'model'):
                    guarded.mode = mode
                    before = len(calls)
                    mode_started = time.monotonic()
                    try:
                        result = asyncio.run(run_mode(mode))
                        guard = result['narrative_guard']
                        outcomes[mode] = {'passed': False, 'guard_source': guard.get('source'),
                                          'guard_attempts': guard.get('attempts'),
                                          'fallback': any(x.get('by') == 'harness' for x in result['tool_calls'])}
                        self.assertEqual(result['provider'], 'openai')
                        self.assertEqual(result['model'], MODEL)
                        self.assertEqual(result['tool_mode'], mode)
                        self.assertEqual(result['decision']['decision_id'], direct['decision_id'])
                        self.assertEqual(result['decision']['final_classification'], direct['final_classification'])
                        self.assertEqual(result['parsed']['domain_determination']['classification'], direct['final_classification'])
                        self.assertEqual(result['tool_calls'], [{'name': 'ybs_evaluate', 'by': mode}])
                        self.assertTrue(calls[before:] and all(n == 'ybs_evaluate' and a == canonical for n, a in calls[before:]))
                        self.assertIsNone(result['parse_error'])
                        self.assertIn(guard['source'], ('model', 'model_retry'))
                        self.assertFalse(guard.get('retry_violations'))
                        parsed_response = json.loads(result['raw_text'])
                        jsonschema.validate(parsed_response, NARRATIVE_SCHEMA)
                        with ledger.locked() as (_, rows):
                            mode_results = [r for r in rows if r.get('event') == 'request_outcome'
                                            and r.get('cycle_id') == cycle_id and r.get('mode') == mode]
                        self.assertTrue(mode_results, 'No provider request recorded for mode')
                        self.assertTrue(all(r.get('budget_charge_usd') is not None for r in mode_results),
                                        'Provider usage or service tier was not reported; reservation retained')
                        outcomes[mode]['passed'] = True
                    except Exception as exc:
                        outcomes.setdefault(mode, {'passed': False})
                        outcomes[mode]['failure_type'] = type(exc).__name__
                        raise AssertionError('Live mode failed: ' + mode + ' (' + type(exc).__name__ + ')') from None
                    finally:
                        outcomes[mode]['elapsed_seconds'] = round(time.monotonic() - mode_started, 3)
        finally:
            if client is not None:
                client.close()
            ledger.end_cycle(cycle_id, outcomes, time.monotonic() - start)
            logging.disable(old_disable)

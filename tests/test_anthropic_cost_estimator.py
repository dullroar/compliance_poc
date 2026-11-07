"""Offline tests for Anthropic cost bounds and durable budget accounting."""
import json
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.anthropic_cost_estimator import (BUDGET, PRICE_CHECKED, BudgetError, baseline,
    estimate, locked, reserve, settle, state)


class AnthropicCostEstimatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'ledger.jsonl'
        self.path.write_text(json.dumps({'event': 'baseline_unknown', 'version': 1}) + '\n')

    def state(self):
        with locked(self.path) as (_, rows):
            return state(rows)

    def test_price_bound_covers_attempts_cache_and_geography(self):
        value = estimate('claude-sonnet-5-5', 2, 10000, 8192, PRICE_CHECKED)
        self.assertEqual(value, Decimal('0.268224'))
        self.assertEqual(estimate('claude-sonnet-4-6', 2, 10000, 8192, PRICE_CHECKED), Decimal('0.402336'))
        self.assertEqual(estimate('claude-opus-5-5', 2, 10000, 8192, PRICE_CHECKED), Decimal('0.536448'))

    def test_haiku_price_tier_applies_to_full_request_above_threshold(self):
        short = estimate('claude-haiku-5-5', 1, 100000, 100, PRICE_CHECKED)
        long = estimate('claude-haiku-5-5', 1, 100001, 100, PRICE_CHECKED)
        self.assertEqual(short, Decimal('0.022055'))
        self.assertEqual(long, Decimal('0.1102761'))
        baseline(self.path, '0', 'owner-confirmed')
        reserve(self.path, 'claude-haiku-5-5', 1, 100001, 100, PRICE_CHECKED)
        event = json.loads(self.path.read_text().splitlines()[-1])
        self.assertEqual(Decimal(event['input_rate_usd_per_million']), Decimal('0.50'))
        self.assertEqual(Decimal(event['output_rate_usd_per_million']), Decimal('2.50'))

    def test_unverified_baseline_refuses_reservation_without_changing_ledger(self):
        before = self.path.read_text()
        with self.assertRaisesRegex(BudgetError, 'unknown'):
            reserve(self.path, 'claude-sonnet-5-5', 1, 1000, 1000, PRICE_CHECKED)
        self.assertEqual(before, self.path.read_text())
        self.assertIsNone(self.state()[0])

    def test_prior_spend_reservations_and_settlement_survive_reopen(self):
        baseline(self.path, '5.20', 'billing-dashboard')
        rid, bound = reserve(self.path, 'claude-sonnet-5-5', 2, 10000, 8192, PRICE_CHECKED)
        spent, held, _ = self.state()
        self.assertEqual((spent, held), (Decimal('5.20'), bound))
        settle(self.path, rid, '0.12', 'api-usage')
        spent, held, _ = self.state()
        self.assertEqual((spent, held), (Decimal('5.32'), Decimal(0)))
        with self.assertRaises(BudgetError):
            settle(self.path, rid, '0.12', 'api-usage')
        with self.assertRaises(BudgetError):
            baseline(self.path, '0', 'owner-confirmed')

    def test_unresolved_reservations_reduce_capacity_and_block_overspend(self):
        baseline(self.path, '19.80', 'usage-export')
        rid, bound = reserve(self.path, 'claude-sonnet-5-5', 1, 10000, 8192, PRICE_CHECKED)
        self.assertLess(bound, Decimal('.20'))
        with self.assertRaisesRegex(BudgetError, 'exceed'):
            reserve(self.path, 'claude-sonnet-5-5', 1, 10000, 8192, PRICE_CHECKED)
        self.assertEqual(self.state()[1], bound)
        self.assertIn(rid, self.state()[2])

    def test_underestimated_actual_is_recorded_even_when_over_budget(self):
        baseline(self.path, '19.90', 'owner-confirmed')
        rid, _ = reserve(self.path, 'claude-sonnet-5-5', 1, 0, 1, PRICE_CHECKED)
        settle(self.path, rid, '0.20', 'billing-dashboard')
        self.assertGreater(self.state()[0], BUDGET)
        self.assertTrue(json.loads(self.path.read_text().splitlines()[-1])['exceeds_reservation'])

    def test_unknown_models_stale_rates_bad_limits_and_bad_amounts_fail(self):
        cases = [
            ('unknown', 1, 100, 100, PRICE_CHECKED),
            ('claude-sonnet-5-5', 0, 100, 100, PRICE_CHECKED),
            ('claude-sonnet-5-5', 1, 1000001, 100, PRICE_CHECKED),
            ('claude-sonnet-5-5', 1, 100, 128001, PRICE_CHECKED),
            ('claude-sonnet-5-5', 1, 100, 0, PRICE_CHECKED),
            ('claude-sonnet-5-5', 1, 100, 100, '2000-01-01'),
        ]
        for values in cases:
            with self.subTest(values=values), self.assertRaises(BudgetError):
                estimate(*values)
        for value in ('-1', 'NaN', 'Infinity', 'nonsense'):
            with self.subTest(value=value), self.assertRaises(BudgetError):
                baseline(self.path, value, 'billing-dashboard')

    def test_missing_or_unrecognized_ledger_fails_closed(self):
        with self.assertRaises(BudgetError):
            with locked(self.path.parent / 'missing'):
                pass
        with self.path.open('a') as f:
            f.write('{"event":"unknown"}\n')
        with self.assertRaises(BudgetError):
            self.state()


if __name__ == '__main__':
    unittest.main()

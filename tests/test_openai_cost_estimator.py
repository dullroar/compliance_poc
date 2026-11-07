"""Offline checks for budget-preflight assumptions and archived-ledger continuity."""
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.openai_cost_estimator import assess
from test_openai_live_smoke import BUDGET, MAX_REQUESTS, MODEL, PRICE_CHECKED, REQUEST_BOUND, Ledger


class OpenAICostEstimatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'runs.jsonl'
        Ledger(self.path).start_cycle('prior')
        Ledger(self.path).end_cycle('prior', {}, 0)

    def test_preflight_reserves_for_whole_cycle_not_only_expected_requests(self):
        result = assess(MODEL, 1, self.path, PRICE_CHECKED)
        self.assertEqual(result['expected_request_bound_usd'], REQUEST_BOUND)
        self.assertEqual(result['required_cycle_reservation_usd'], MAX_REQUESTS * REQUEST_BOUND)
        self.assertTrue(result['fits'])

    def test_unresolved_prior_cycles_reduce_remaining_budget_across_restarts(self):
        ledger = Ledger(self.path)
        while True:
            result = assess(MODEL, 1, self.path, PRICE_CHECKED)
            if not result['fits']:
                break
            ledger.start_cycle('cycle-' + str(len(self.path.read_text().splitlines())))
        self.assertLess(result['remaining_before_cycle_usd'], MAX_REQUESTS * REQUEST_BOUND)
        self.assertLessEqual(result['outstanding_reservations_usd'], BUDGET)
        self.assertEqual(result['conservative_incurred_usd'], Decimal(0))

    def test_invalid_or_unverifiable_inputs_fail_closed(self):
        for model, count, path, date in (
            ('other-model', 1, self.path, PRICE_CHECKED),
            (MODEL, 0, self.path, PRICE_CHECKED),
            (MODEL, 7, self.path, PRICE_CHECKED),
            (MODEL, 1, self.path, '2000-01-01'),
            (MODEL, 1, self.path.parent / 'missing', PRICE_CHECKED),
        ):
            with self.subTest(model=model, count=count, date=date), self.assertRaises(ValueError):
                assess(model, count, path, date)

    def test_unknown_ledger_event_is_not_ignored(self):
        with self.path.open('a') as f:
            f.write('{"event":"unrecognized"}\n')
        with self.assertRaises(ValueError):
            assess(MODEL, 1, self.path, PRICE_CHECKED)


if __name__ == '__main__':
    unittest.main()

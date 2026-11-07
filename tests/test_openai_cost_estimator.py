"""Offline checks for budget-preflight assumptions and archived-ledger continuity."""
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.openai_cost_estimator import assess
from test_openai_live_smoke import (BUDGET, MAX_REQUESTS, MODEL, PARITY_INPUT_BOUND_TOKENS, PARITY_MAX_REQUESTS, PARITY_REQUEST_BOUND,
                                    PRICE_CHECKED, REQUEST_BOUND, Ledger)


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


class ParityProfileTests(unittest.TestCase):
    """The registry-wide profile: more requests per cycle, each bounded at 100000 input tokens, within a per-run ceiling."""

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'runs.jsonl'
        Ledger(self.path).start_cycle('prior')
        Ledger(self.path).end_cycle('prior', {}, 0)

    def test_the_default_profile_still_refuses_more_than_six_requests(self):
        with self.assertRaises(ValueError):
            assess(MODEL, 7, self.path, PRICE_CHECKED)
        with self.assertRaises(ValueError):
            assess(MODEL, 7, self.path, PRICE_CHECKED, 'smoke')

    def test_the_parity_profile_reports_the_new_cycle_bound(self):
        result = assess(MODEL, 56, self.path, PRICE_CHECKED, 'parity')
        self.assertEqual(result['profile'], 'parity')
        self.assertEqual(result['input_bound_tokens_per_request'], PARITY_INPUT_BOUND_TOKENS)
        self.assertEqual(result['required_cycle_reservation_usd'], 56 * PARITY_REQUEST_BOUND)
        self.assertEqual(result['expected_request_bound_usd'], 56 * PARITY_REQUEST_BOUND)
        self.assertEqual(PARITY_REQUEST_BOUND, Decimal('0.0617584'))
        self.assertTrue(result['fits'])
        self.assertLessEqual(result['required_cycle_reservation_usd'], result['per_run_ceiling_usd'])

    def test_the_parity_profile_bounds_and_fail_closed_behavior(self):
        for model, count, path, date, profile in (
            ('other-model', 56, self.path, PRICE_CHECKED, 'parity'),
            (MODEL, 0, self.path, PRICE_CHECKED, 'parity'),
            (MODEL, PARITY_MAX_REQUESTS + 1, self.path, PRICE_CHECKED, 'parity'),
            (MODEL, 56, self.path, '2000-01-01', 'parity'),
            (MODEL, 56, self.path.parent / 'missing', PRICE_CHECKED, 'parity'),
            (MODEL, 56, self.path, PRICE_CHECKED, 'unknown'),
        ):
            with self.subTest(model=model, count=count, date=date, profile=profile), self.assertRaises(ValueError):
                assess(model, count, path, date, profile)
        self.assertTrue(assess(MODEL, PARITY_MAX_REQUESTS, self.path, PRICE_CHECKED, 'parity')['required_cycle_reservation_usd'] > 0)

    def test_the_per_run_ceiling_and_the_cumulative_budget_both_gate_fits(self):
        self.assertFalse(assess(MODEL, PARITY_MAX_REQUESTS, self.path, PRICE_CHECKED, 'parity')['fits'] and PARITY_MAX_REQUESTS * PARITY_REQUEST_BOUND > 5)
        ledger = Ledger(self.path)
        n = 0
        while assess(MODEL, 56, self.path, PRICE_CHECKED, 'parity')['fits']:
            n += 1
            ledger.start_cycle(f'parity-{n}', 56, PARITY_REQUEST_BOUND, PARITY_INPUT_BOUND_TOKENS)
        result = assess(MODEL, 56, self.path, PRICE_CHECKED, 'parity')
        self.assertLess(result['remaining_before_cycle_usd'], result['required_cycle_reservation_usd'])
        self.assertLessEqual(result['outstanding_reservations_usd'], BUDGET)

    def test_a_cycle_that_released_slots_returns_them_to_the_budget(self):
        Ledger(self.path).start_cycle('p', 56, PARITY_REQUEST_BOUND, PARITY_INPUT_BOUND_TOKENS)
        held = assess(MODEL, 56, self.path, PRICE_CHECKED, 'parity')['outstanding_reservations_usd']
        self.assertEqual(held, 56 * PARITY_REQUEST_BOUND)
        Ledger(self.path).end_cycle('p', {}, 0)
        self.assertEqual(assess(MODEL, 56, self.path, PRICE_CHECKED, 'parity')['outstanding_reservations_usd'], 0)

    def test_the_command_line_picks_parity_only_above_the_smoke_maximum(self):
        import subprocess
        import sys
        root = Path(__file__).resolve().parents[1]
        done = subprocess.run([sys.executable, 'scripts/openai_cost_estimator.py', '--model', MODEL, '--requests', '56'],
                              cwd=root, capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn('profile: parity', done.stdout)
        small = subprocess.run([sys.executable, 'scripts/openai_cost_estimator.py', '--model', MODEL, '--requests', '3'],
                               cwd=root, capture_output=True, text=True, timeout=120)
        self.assertNotIn('profile:', small.stdout)
        too_many = subprocess.run([sys.executable, 'scripts/openai_cost_estimator.py', '--model', MODEL, '--requests', '81'],
                                  cwd=root, capture_output=True, text=True, timeout=120)
        self.assertEqual(too_many.returncode, 1)


if __name__ == '__main__':
    unittest.main()

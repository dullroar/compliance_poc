import csv
import json
import os
import unittest
from datetime import UTC, datetime
from pathlib import Path

from compliance_mcp.hpml import evaluate_hpml
from intake.apor import AporLookupError, fill_case, lookup_apor

FIXED_NOW = lambda: datetime(2026, 10, 9, 12, 0, 0, tzinfo=UTC)  # noqa: E731


class FakeApi:
    def __init__(self, spread="3.140"):
        self.spread, self.requests = spread, []

    def __call__(self, payload):
        self.requests.append(payload)
        return json.dumps({"rateSpread": self.spread}).encode()


def hpml_case(**changes):
    value = dict(rate_set_date="2024-04-10", consumer_purpose=True, closed_end=True, secured_by_principal_dwelling=True,
                 lien_position="first", principal_obligation=425000, applicable_conforming_limit=766550, apr=8.12, amortization_type="fixed", apor_term_years=30,
                 escrow_established_before_consummation=True, appraisal_requirements_met=True)
    value.update(changes)
    return value


class AporIntakeTests(unittest.TestCase):
    def test_apor_is_the_probe_minus_the_returned_spread(self):
        api = FakeApi("3.140")
        result = lookup_apor("2024-04-10", "fixed", 30, api, FIXED_NOW)
        self.assertEqual(result["apor"], 6.86)
        ref = result["apor_reference"]
        self.assertEqual(ref["table_date"], "2024-04-08")               # Monday of that week
        self.assertEqual(ref["retrieved_at"], "2026-10-09T12:00:00Z")
        self.assertEqual(len(ref["response_sha256"]), 64)
        self.assertIn("derived", ref["table_date_basis"])

    def test_no_loan_data_is_sent_only_the_probe_apr_date_and_term(self):
        api = FakeApi()
        lookup_apor("2024-04-10", "adjustable", 5, api, FIXED_NOW)
        self.assertEqual(api.requests, [{"actionTakenType": 1, "loanTerm": 5, "amortizationType": "VariableRate",
                                         "apr": 10.0, "lockInDate": "2024-04-10", "reverseMortgage": 2}])

    def test_failures_never_guess(self):
        cases = [
            lambda: lookup_apor("2016-06-13", "fixed", 30, FakeApi()),         # before the API's range
            lambda: lookup_apor("2024-04-10", "fixed", 0, FakeApi()),
            lambda: lookup_apor("2024-04-10", "fixed", 51, FakeApi()),
            lambda: lookup_apor("2024-04-10", "balloon", 30, FakeApi()),
            lambda: lookup_apor("2024-04-10", "fixed", 30, FakeApi("NA")),
            lambda: lookup_apor("2024-04-10", "fixed", 30, lambda p: b"<html>captcha</html>"),
        ]
        for index, call in enumerate(cases):
            with self.subTest(case=index), self.assertRaises(AporLookupError):
                call()

    def test_fill_case_records_evidence_and_the_evaluator_accepts_it(self):
        loan = {"hpml_case": hpml_case()}
        added = fill_case(loan, post=FakeApi("3.140"))
        self.assertEqual(loan["hpml_case"]["apor"], 6.86)
        self.assertEqual(added["apor"], 6.86)
        result = evaluate_hpml(loan["hpml_case"])                            # schema accepts the evidence fields
        self.assertEqual(result["final_classification"], "Not HPML")        # 8.12 - 6.86 = 1.26 < 1.5
        self.assertEqual(result["hpml_evaluation"]["apor_reference"]["response_sha256"], added["apor_reference"]["response_sha256"])

    def test_existing_apor_is_kept_unless_forced(self):
        loan = {"hpml_case": hpml_case(apor=7.02)}
        api = FakeApi("3.140")
        self.assertIsNone(fill_case(loan, post=api))
        self.assertEqual((loan["hpml_case"]["apor"], api.requests), (7.02, []))
        fill_case(loan, force=True, post=api)
        self.assertEqual(loan["hpml_case"]["apor"], 6.86)

    def test_missing_selector_fields_are_reported(self):
        case = hpml_case()
        del case["apor_term_years"]
        with self.assertRaisesRegex(AporLookupError, "apor_term_years"):
            fill_case({"hpml_case": case}, post=FakeApi())
        with self.assertRaisesRegex(AporLookupError, "no hpml_case"):
            fill_case({}, post=FakeApi())


@unittest.skipUnless(os.getenv("RUN_LIVE_APOR_TESTS") == "1", "set RUN_LIVE_APOR_TESTS=1 to call the live rate-spread API")
class LiveAporTests(unittest.TestCase):
    def test_live_api_agrees_with_the_legacy_csv_on_the_last_legacy_week(self):
        base = Path(__file__).resolve().parents[1] / "compliance_mcp/hpml/sources/apor"
        legacy = {r[0]: r for r in csv.reader(open(base / "YieldTableFixed.CSV"))}["12/25/2017"][30]
        live = lookup_apor("2017-12-25", "fixed", 30)["apor"]
        self.assertAlmostEqual(live, float(legacy), places=2)


if __name__ == "__main__":
    unittest.main()

import asyncio
import hashlib
import unittest
from datetime import date
from pathlib import Path

import yaml

from compliance_common.calendar import add_business_days, creditor_business_day, nth_weekday, specific_business_day, subtract_business_days
from compliance_common.mcp_client import call_tool
from compliance_common.pack import EvaluatorValidationError
from compliance_mcp.trid import evaluate_trid, validate_trid_decision_record, validate_trid_rule_pack
from compliance_mcp.trid.server import server as trid_server

ROOT = Path(__file__).resolve().parents[1]
HOLIDAYS = yaml.safe_load((ROOT / "compliance_mcp/trid/pack/calendar.yaml").read_text(encoding="utf-8"))["holidays"]


def case(**changes):
    # Application Mon 2026-05-04; consummation Fri 2026-06-12.
    value = dict(
        closed_end=True, secured_by_real_property_or_cooperative_unit=True,
        application_received_date="2026-05-04", consummation_date="2026-06-12",
        loan_estimate=dict(delivery_date="2026-05-06", delivery_method="in_person"),
        closing_disclosure=dict(delivery_date="2026-06-08", delivery_method="in_person"),
        charges=[dict(id="orig", category="zero_tolerance", disclosed_amount=1000, actual_amount=1000),
                 dict(id="title", category="ten_percent_tolerance", disclosed_amount=2000, actual_amount=2000)],
    )
    value.update(changes)
    return value


def outcomes(result):
    return {r["rule_id"]: r["outcome"] for r in result["rule_results"]}


class CalendarTests(unittest.TestCase):
    def test_holiday_rules(self):
        self.assertEqual(nth_weekday(2025, 11, 3, 4), date(2025, 11, 27))   # Thanksgiving
        self.assertEqual(nth_weekday(2026, 5, 0, -1), date(2026, 5, 25))    # Memorial Day
        self.assertEqual(nth_weekday(2026, 9, 0, 1), date(2026, 9, 7))      # Labor Day

    def test_specific_business_days_skip_sundays_and_holidays_but_count_saturdays(self):
        sb = specific_business_day(HOLIDAYS)
        self.assertTrue(sb(date(2026, 6, 6)))                  # Saturday counts
        self.assertFalse(sb(date(2026, 6, 7)))                 # Sunday
        self.assertFalse(sb(date(2026, 5, 25)))                # Memorial Day
        self.assertFalse(sb(date(2026, 6, 19)))                # Juneteenth
        self.assertTrue(sb(date(2020, 6, 19)))                 # not a holiday before 2021
        self.assertEqual(subtract_business_days(date(2026, 6, 4), 3, sb), date(2026, 6, 1))
        self.assertEqual(subtract_business_days(date(2026, 6, 12), 7, sb), date(2026, 6, 4))   # Saturday counted
        self.assertEqual(add_business_days(date(2026, 5, 22), 3, sb), date(2026, 5, 27))       # Sun + Memorial Day skipped

    def test_creditor_business_days_follow_open_days(self):
        weekdays = creditor_business_day(["mon", "tue", "wed", "thu", "fri"])
        self.assertEqual(add_business_days(date(2026, 5, 4), 3, weekdays), date(2026, 5, 7))
        self.assertEqual(add_business_days(date(2026, 5, 7), 3, weekdays), date(2026, 5, 12))  # skips the weekend
        with_sat = creditor_business_day(["mon", "tue", "wed", "thu", "fri", "sat"])
        self.assertEqual(add_business_days(date(2026, 5, 7), 3, with_sat), date(2026, 5, 11))


class TRIDTimingTests(unittest.TestCase):
    def test_all_compliant(self):
        result = evaluate_trid(case())
        self.assertEqual((result["final_classification"], result["compliance_result"]), ("TRID Covered", "Compliant"))

    def test_loan_estimate_three_business_day_boundary(self):
        on_time = evaluate_trid(case(loan_estimate=dict(delivery_date="2026-05-07", delivery_method="in_person")))
        late = evaluate_trid(case(loan_estimate=dict(delivery_date="2026-05-08", delivery_method="in_person")))
        self.assertEqual(outcomes(on_time)["TRID-LE-3DAY"], "satisfied")
        self.assertEqual(outcomes(late)["TRID-LE-3DAY"], "not_satisfied")
        self.assertEqual(late["compliance_result"], "Non-Compliant")

    def test_creditor_open_days_change_the_three_day_deadline(self):
        # Application Thu 2026-05-07; with Saturday open the 3rd business day is Mon 05-11, otherwise Tue 05-12.
        late = dict(application_received_date="2026-05-07", loan_estimate=dict(delivery_date="2026-05-12", delivery_method="in_person"))
        self.assertEqual(outcomes(evaluate_trid(case(**late)))["TRID-LE-3DAY"], "satisfied")
        self.assertEqual(outcomes(evaluate_trid(case(creditor_open_days=["mon", "tue", "wed", "thu", "fri", "sat"], **late)))["TRID-LE-3DAY"], "not_satisfied")

    def test_loan_estimate_seven_business_day_boundary_and_waiver(self):
        self.assertEqual(outcomes(evaluate_trid(case(loan_estimate=dict(delivery_date="2026-06-04", delivery_method="in_person"))))["TRID-LE-7DAY"], "satisfied")
        late = case(loan_estimate=dict(delivery_date="2026-06-05", delivery_method="in_person"), application_received_date="2026-06-04")
        self.assertEqual(outcomes(evaluate_trid(late))["TRID-LE-7DAY"], "not_satisfied")
        waived = case(loan_estimate=dict(delivery_date="2026-06-05", delivery_method="in_person", waiver_documented=True), application_received_date="2026-06-04")
        self.assertEqual(outcomes(evaluate_trid(waived))["TRID-LE-7DAY"], "does_not_apply")

    def test_closing_disclosure_three_business_day_boundary(self):
        self.assertEqual(outcomes(evaluate_trid(case(closing_disclosure=dict(delivery_date="2026-06-09", delivery_method="in_person"))))["TRID-CD-3DAY"], "satisfied")
        result = evaluate_trid(case(closing_disclosure=dict(delivery_date="2026-06-10", delivery_method="in_person")))
        self.assertEqual(outcomes(result)["TRID-CD-3DAY"], "not_satisfied")
        self.assertEqual(result["compliance_result"], "Non-Compliant")

    def test_mailed_closing_disclosure_is_presumed_received_three_business_days_later(self):
        # Mailed Fri 06-05 -> presumed received Tue 06-09 (Sat, Mon, Tue; Sunday skipped): on time.
        ok = evaluate_trid(case(closing_disclosure=dict(delivery_date="2026-06-05", delivery_method="mail")))
        self.assertEqual(outcomes(ok)["TRID-CD-3DAY"], "satisfied")
        self.assertEqual(ok["trid_evaluation"]["TRID-CD-3DAY_receipt_date"], "2026-06-09")
        late = evaluate_trid(case(closing_disclosure=dict(delivery_date="2026-06-06", delivery_method="electronic")))
        self.assertEqual(outcomes(late)["TRID-CD-3DAY"], "not_satisfied")

    def test_closing_disclosure_waiver(self):
        waived = case(closing_disclosure=dict(delivery_date="2026-06-11", delivery_method="in_person", waiver_documented=True))
        self.assertEqual(outcomes(evaluate_trid(waived))["TRID-CD-3DAY"], "does_not_apply")

    def test_changes_requiring_a_new_waiting_period(self):
        triggers = dict(cd_changes_requiring_new_waiting_period=["apr_inaccurate"])
        missing = evaluate_trid(case(**triggers))
        self.assertEqual(outcomes(missing)["TRID-CD-REVISED-3DAY"], "unable_to_determine")
        self.assertEqual(missing["compliance_result"], "Potential Issue")
        late = evaluate_trid(case(revised_closing_disclosure=dict(delivery_date="2026-06-11", delivery_method="in_person"), **triggers))
        self.assertEqual(outcomes(late)["TRID-CD-REVISED-3DAY"], "not_satisfied")
        ok = evaluate_trid(case(revised_closing_disclosure=dict(delivery_date="2026-06-09", delivery_method="in_person"), **triggers))
        self.assertEqual(outcomes(ok)["TRID-CD-REVISED-3DAY"], "satisfied")

    def test_corrected_disclosure_without_new_wait_must_arrive_by_consummation(self):
        ok = evaluate_trid(case(revised_closing_disclosure=dict(delivery_date="2026-06-12", delivery_method="in_person")))
        late = evaluate_trid(case(revised_closing_disclosure=dict(delivery_date="2026-06-12", delivery_method="mail")))
        self.assertEqual(outcomes(ok)["TRID-CD-CORRECTED"], "satisfied")
        self.assertEqual(outcomes(late)["TRID-CD-CORRECTED"], "not_satisfied")

    def test_missing_disclosures_never_guess(self):
        value = case()
        del value["loan_estimate"], value["closing_disclosure"]
        result = evaluate_trid(value)
        self.assertEqual({outcomes(result)[k] for k in ("TRID-LE-3DAY", "TRID-LE-7DAY", "TRID-CD-3DAY")}, {"unable_to_determine"})
        self.assertEqual(result["compliance_result"], "Potential Issue")


class TRIDScopeAndToleranceTests(unittest.TestCase):
    def test_scope_exclusions(self):
        for changes in ({"closed_end": False}, {"secured_by_real_property_or_cooperative_unit": False}, {"reverse_mortgage": True}):
            with self.subTest(changes=changes):
                result = evaluate_trid(case(**changes))
                self.assertEqual((result["final_classification"], result["compliance_result"]), ("Not Covered", "Not Applicable"))

    def test_timeshare_and_pre_trid_applications_are_not_guessed(self):
        timeshare = evaluate_trid(case(timeshare=True))
        self.assertEqual((timeshare["final_classification"], timeshare["determination_status"]), ("Review Required", "Review Required"))
        old = evaluate_trid(case(application_received_date="2015-09-01", consummation_date="2015-10-20"))
        self.assertEqual(old["final_classification"], "Unable To Determine")

    def test_zero_tolerance_any_increase_is_an_excess(self):
        charges = [dict(id="orig", category="zero_tolerance", disclosed_amount=1000, actual_amount=1000.01)]
        result = evaluate_trid(case(charges=charges))
        self.assertEqual(outcomes(result)["TRID-TOLERANCE"], "not_satisfied")
        self.assertEqual(result["trid_evaluation"]["tolerance"]["total_excess"], "0.01")
        self.assertEqual(result["trid_evaluation"]["tolerance"]["cure_due_by"], "2026-08-11")

    def test_ten_percent_aggregate_boundary(self):
        def run(a, b):
            return evaluate_trid(case(charges=[
                dict(id="t1", category="ten_percent_tolerance", disclosed_amount=1000, actual_amount=a),
                dict(id="t2", category="ten_percent_tolerance", disclosed_amount=1000, actual_amount=b)]))
        self.assertEqual(outcomes(run(1500, 700))["TRID-TOLERANCE"], "satisfied")     # one charge up 50%, aggregate under 10%
        self.assertEqual(outcomes(run(1100, 1100))["TRID-TOLERANCE"], "satisfied")    # exactly 10%
        over = run(1100, 1100.01)
        self.assertEqual(outcomes(over)["TRID-TOLERANCE"], "not_satisfied")
        self.assertEqual(over["trid_evaluation"]["tolerance"]["ten_percent_excess"], "0.01")

    def test_no_tolerance_bona_fide_charges_are_not_tested(self):
        charges = [dict(id="prepaid", category="no_tolerance_bona_fide", disclosed_amount=100, actual_amount=900)]
        self.assertEqual(outcomes(evaluate_trid(case(charges=charges)))["TRID-TOLERANCE"], "satisfied")

    def test_documented_revision_resets_the_baseline_but_undocumented_does_not(self):
        base = dict(id="orig", category="zero_tolerance", disclosed_amount=1000, actual_amount=1200, revised_amount=1200, revision_reason="changed_circumstance_settlement")
        documented = evaluate_trid(case(charges=[dict(base, revision_documented=True)]))
        undocumented = evaluate_trid(case(charges=[base]))
        self.assertEqual(outcomes(documented)["TRID-TOLERANCE"], "satisfied")
        self.assertEqual(outcomes(undocumented)["TRID-TOLERANCE"], "not_satisfied")
        self.assertIn("ignored", undocumented["trid_evaluation"]["tolerance"]["notes"][0])

    def test_refund_cure_window(self):
        charges = [dict(id="orig", category="zero_tolerance", disclosed_amount=1000, actual_amount=1100)]
        cured = evaluate_trid(case(charges=charges, tolerance_refund=dict(amount=100, date="2026-08-11")))   # day 60
        self.assertEqual((outcomes(cured)["TRID-TOLERANCE"], cured["compliance_result"]), ("satisfied", "Compliant"))
        late = evaluate_trid(case(charges=charges, tolerance_refund=dict(amount=100, date="2026-08-12")))
        short = evaluate_trid(case(charges=charges, tolerance_refund=dict(amount=99.99, date="2026-07-01")))
        self.assertEqual(outcomes(late)["TRID-TOLERANCE"], "not_satisfied")
        self.assertEqual(outcomes(short)["TRID-TOLERANCE"], "not_satisfied")

    def test_uncured_excess_is_a_potential_issue_until_the_cure_period_has_run(self):
        charges = [dict(id="orig", category="zero_tolerance", disclosed_amount=1000, actual_amount=1100)]
        self.assertEqual(evaluate_trid(case(charges=charges))["compliance_result"], "Potential Issue")
        self.assertEqual(evaluate_trid(case(charges=charges, review_date="2026-08-11"))["compliance_result"], "Potential Issue")
        self.assertEqual(evaluate_trid(case(charges=charges, review_date="2026-08-12"))["compliance_result"], "Non-Compliant")


class TRIDContractTests(unittest.TestCase):
    def test_pack_sources_and_contracts_validate(self):
        validate_trid_rule_pack()
        manifest = yaml.safe_load((ROOT / "compliance_mcp/trid/pack/manifest.yaml").read_text(encoding="utf-8"))
        for source in manifest["sources"]:
            with self.subTest(source=source["id"]):
                self.assertEqual(hashlib.sha256((ROOT / source["local_path"]).read_bytes()).hexdigest(), source["sha256"])

    def test_thresholds_match_the_pinned_regulation_text(self):
        text = (ROOT / "compliance_mcp/trid/pack/sources/12-cfr-1026-19.xml").read_text(encoding="utf-8")
        for needle in ("not later than the third business day after the creditor receives the consumer's application",
                       "not later than the seventh business day before consummation",
                       "no later than three business days before consummation",
                       "by more than 10 percent", "no later than 60 days after consummation"):
            self.assertIn(needle, text)

    def test_schema_rejects_malformed_input_and_output(self):
        with self.assertRaisesRegex(EvaluatorValidationError, "Additional properties"):
            evaluate_trid(case(surprise=1))
        with self.assertRaisesRegex(EvaluatorValidationError, "precedes"):
            evaluate_trid(case(consummation_date="2026-05-01"))
        record = evaluate_trid(case())
        del record["rule_pack"]
        with self.assertRaisesRegex(EvaluatorValidationError, "rule_pack"):
            validate_trid_decision_record(record)

    def test_replay_and_mcp_parity(self):
        direct = evaluate_trid(case())
        self.assertEqual(direct["decision_id"], evaluate_trid(case())["decision_id"])
        self.assertEqual(asyncio.run(call_tool(trid_server, "trid_evaluate", {"case": case()}))["decision_id"], direct["decision_id"])


if __name__ == "__main__":
    unittest.main()

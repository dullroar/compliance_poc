import unittest

from compliance_mcp.ecoa import evaluate_ecoa, validate_ecoa_decision_record, validate_ecoa_rule_pack
from compliance_mcp.ecoa.server import server
from evaluator_contract import contract_tests, outcomes

FULL = {"action_statement": True, "creditor_name_address": True, "ecoa_notice": True, "agency_name_address": True, "reasons_or_right_disclosure": True}


def case(**changes):
    value = dict(application_received_date="2024-03-01", application_complete_date="2024-03-01", decision_date="2024-03-20",
                 decision_type="approved_as_requested", notice={"sent": True, "date": "2024-03-31", "written": True},
                 age_public_assistance={"age_use": "none", "public_assistance_use": "none"},
                 marital_status_inquiry={"asked": False}, spouse_signature={"required": False})
    value.update(changes)
    return value


def denial(**notice):
    n = {"sent": True, "date": "2024-03-31", "written": True, "contents": dict(FULL), "reasons_basis": "statement_of_reasons", "specific_reasons": True}
    n.update(notice)
    return case(decision_type="denied", notice=n)


class ECOANotificationTests(unittest.TestCase):
    def test_approval_notice_30_day_boundary(self):
        ok = evaluate_ecoa(case())                                          # Mar 1 + 30 days = Mar 31
        late = evaluate_ecoa(case(notice={"sent": True, "date": "2024-04-01", "written": True}))
        self.assertEqual((outcomes(ok)["ECOA-NOTICE-TIMING"], ok["final_classification"], ok["compliance_result"]), ("satisfied", "No Adverse Action", "Compliant"))
        self.assertEqual((outcomes(late)["ECOA-NOTICE-TIMING"], late["compliance_result"]), ("not_satisfied", "Non-Compliant"))

    def test_denial_that_is_fully_compliant(self):
        r = evaluate_ecoa(denial())
        self.assertEqual((r["final_classification"], r["compliance_result"]), ("Adverse Action Notice Required", "Compliant"))
        self.assertEqual(outcomes(r)["ECOA-NOTICE-CONTENT"], "satisfied")

    def test_each_missing_notice_element_is_not_satisfied(self):
        for key in FULL:
            with self.subTest(key=key):
                r = evaluate_ecoa(denial(contents={**FULL, key: False}))
                self.assertEqual((outcomes(r)["ECOA-NOTICE-CONTENT"], r["compliance_result"]), ("not_satisfied", "Non-Compliant"))

    def test_unknown_element_or_unwritten_notice(self):
        unknown = evaluate_ecoa(denial(contents={k: v for k, v in FULL.items() if k != "ecoa_notice"}))
        self.assertEqual((outcomes(unknown)["ECOA-NOTICE-CONTENT"], unknown["compliance_result"]), ("unable_to_determine", "Potential Issue"))
        self.assertEqual(outcomes(evaluate_ecoa(denial(written=False)))["ECOA-NOTICE-CONTENT"], "not_satisfied")

    def test_no_notice_at_all_on_a_denial(self):
        r = evaluate_ecoa(case(decision_type="denied", notice={"sent": False}))
        self.assertEqual((outcomes(r)["ECOA-NOTICE-CONTENT"], r["compliance_result"]), ("not_satisfied", "Non-Compliant"))

    def test_specific_reasons_standard(self):
        self.assertEqual(outcomes(evaluate_ecoa(denial(specific_reasons=False)))["ECOA-REASONS-SPECIFIC"], "not_satisfied")
        disclosure = denial(reasons_basis="right_disclosure")
        self.assertNotIn("ECOA-REASONS-SPECIFIC", outcomes(evaluate_ecoa(disclosure)))

    def test_small_volume_creditor_may_notify_orally(self):
        r = evaluate_ecoa({**denial(written=False, contents={}), "creditor_applications_prior_year": 150})
        self.assertEqual(outcomes(r)["ECOA-NOTICE-CONTENT"], "does_not_apply")
        r = evaluate_ecoa({**denial(written=False, contents={}), "creditor_applications_prior_year": 151})
        self.assertEqual(outcomes(r)["ECOA-NOTICE-CONTENT"], "not_satisfied")

    def test_existing_account_adverse_action_runs_from_the_decision_date(self):
        base = dict(decision_type="existing_account_adverse", decision_date="2024-03-01", notice={"sent": True, "date": "2024-03-31", "written": True, "contents": dict(FULL), "reasons_basis": "right_disclosure"})
        self.assertEqual(outcomes(evaluate_ecoa(case(**base)))["ECOA-NOTICE-TIMING"], "satisfied")
        base["notice"]["date"] = "2024-04-01"
        self.assertEqual(outcomes(evaluate_ecoa(case(**base)))["ECOA-NOTICE-TIMING"], "not_satisfied")

    def test_withdrawal_and_excluded_refusals_need_no_notice(self):
        for kind, label in (("withdrawn_by_applicant", "Withdrawal"), ("not_adverse_law_prohibits", "No Adverse Action"), ("not_adverse_product_not_offered", "No Adverse Action")):
            r = evaluate_ecoa(case(decision_type=kind, notice={"sent": False}))
            self.assertEqual((r["final_classification"], outcomes(r)["ECOA-NOTICE-TIMING"], r["compliance_result"]), (label, "does_not_apply", "Compliant"), kind)

    def test_large_business_credit_is_a_reasonable_time_standard(self):
        r = evaluate_ecoa(case(business_credit=True, business_revenue_over_1m=True))
        self.assertEqual((outcomes(r)["ECOA-NOTICE-TIMING"], r["compliance_result"]), ("review_required", "Potential Issue"))

    def test_multiple_applicants_notice_goes_to_the_primary_applicant(self):
        self.assertEqual(outcomes(evaluate_ecoa({**denial(delivered_to="primary"), "joint_application": True}))["ECOA-NOTICE-RECIPIENT"], "satisfied")
        self.assertEqual(outcomes(evaluate_ecoa({**denial(delivered_to="other"), "joint_application": True}))["ECOA-NOTICE-RECIPIENT"], "not_satisfied")
        self.assertEqual(outcomes(evaluate_ecoa({**denial(), "joint_application": True}))["ECOA-NOTICE-RECIPIENT"], "unable_to_determine")


class ECOACounterofferAndIncompleteTests(unittest.TestCase):
    def counter(self, accepted, notice_date="2024-03-05", review="2024-06-01", notice=None):
        return case(decision_type="counteroffer", counteroffer={"notice_date": notice_date, "accepted": accepted}, review_date=review,
                    notice=notice or {"sent": False})

    def test_accepted_counteroffer_is_not_adverse_action(self):
        r = evaluate_ecoa(self.counter(True))
        self.assertEqual((r["final_classification"], outcomes(r)["ECOA-ADVERSE-ACTION"]), ("Counteroffer", "does_not_apply"))
        self.assertEqual(outcomes(r)["ECOA-NOTICE-TIMING"], "satisfied")

    def test_declined_counteroffer_is_adverse_action_needing_a_notice_within_90_days(self):
        notice = {"sent": True, "date": "2024-06-03", "written": True, "contents": dict(FULL), "reasons_basis": "right_disclosure"}   # Mar 5 + 90 = Jun 3
        ok = evaluate_ecoa(self.counter(False, notice=notice))
        self.assertEqual((outcomes(ok)["ECOA-ADVERSE-ACTION"], outcomes(ok)["ECOA-NOTICE-TIMING-COUNTEROFFER"]), ("applies", "satisfied"))
        notice["date"] = "2024-06-04"
        self.assertEqual(outcomes(evaluate_ecoa(self.counter(False, notice=notice)))["ECOA-NOTICE-TIMING-COUNTEROFFER"], "not_satisfied")

    def test_unanswered_counteroffer_becomes_adverse_after_90_days(self):
        pending = evaluate_ecoa(self.counter(None, review="2024-06-03"))
        self.assertEqual(outcomes(pending)["ECOA-ADVERSE-ACTION"], "unable_to_determine")
        lapsed = evaluate_ecoa(self.counter(None, review="2024-06-04"))
        self.assertEqual(outcomes(lapsed)["ECOA-ADVERSE-ACTION"], "applies")

    def test_incomplete_application_may_get_an_incompleteness_notice(self):
        inc = {"sent": True, "date": "2024-03-31", "specifies_info_needed": True, "reasonable_period_designated": True, "warns_no_further_consideration": True}
        r = evaluate_ecoa(case(decision_type="closed_incomplete", application_complete_date=None, notice={"sent": False}, incompleteness_notice=inc))
        self.assertEqual((r["final_classification"], outcomes(r)["ECOA-NOTICE-TIMING"], outcomes(r)["ECOA-NOTICE-CONTENT"], r["compliance_result"]),
                         ("Incomplete Application Procedure", "satisfied", "satisfied", "Compliant"))
        late = dict(inc, date="2024-04-01")
        r = evaluate_ecoa(case(decision_type="closed_incomplete", application_complete_date=None, notice={"sent": False}, incompleteness_notice=late))
        self.assertEqual(outcomes(r)["ECOA-NOTICE-TIMING"], "not_satisfied")
        r = evaluate_ecoa(case(decision_type="closed_incomplete", application_complete_date=None, notice={"sent": False}, incompleteness_notice=dict(inc, warns_no_further_consideration=False)))
        self.assertEqual(outcomes(r)["ECOA-NOTICE-CONTENT"], "not_satisfied")


class ECOAProcessRuleTests(unittest.TestCase):
    def test_marital_status_inquiry_limits(self):
        asked = lambda **k: evaluate_ecoa(case(marital_status_inquiry={"asked": True, **k}))["rule_results"]  # noqa: E731
        by = lambda rules: {r["rule_id"]: r["outcome"] for r in rules}["ECOA-MARITAL-INQUIRY"]  # noqa: E731
        self.assertEqual(by(asked(credit_type="individual_unsecured")), "not_satisfied")
        self.assertEqual(by(asked(credit_type="individual_unsecured", community_property=True)), "satisfied")
        self.assertEqual(by(asked(credit_type="other", terms_valid=True)), "satisfied")
        self.assertEqual(by(asked(credit_type="other", terms_valid=False)), "not_satisfied")
        self.assertEqual(by(asked()), "unable_to_determine")

    def test_spousal_signature(self):
        sig = lambda **k: outcomes(evaluate_ecoa(case(spouse_signature={"required": True, **k})))["ECOA-SPOUSE-SIGNATURE"]  # noqa: E731
        self.assertEqual(sig(applicant_qualified_alone=True, joint_applicant=False), "not_satisfied")
        self.assertEqual(sig(applicant_qualified_alone=True, joint_applicant=True), "satisfied")
        self.assertEqual(sig(applicant_qualified_alone=False, joint_applicant=False), "satisfied")
        self.assertEqual(sig(applicant_qualified_alone=True, joint_applicant=False, signature_required_by_state_law_to_reach_collateral=True), "does_not_apply")
        self.assertEqual(sig(), "unable_to_determine")

    def test_age_and_public_assistance_use(self):
        use = lambda **k: outcomes(evaluate_ecoa(case(age_public_assistance=k)))["ECOA-AGE-PUBLIC-ASSISTANCE"]  # noqa: E731
        self.assertEqual(use(age_use="other", public_assistance_use="none"), "not_satisfied")
        self.assertEqual(use(age_use="favors_elderly", public_assistance_use="judgmental_pertinent_element"), "satisfied")
        self.assertEqual(use(age_use="none", public_assistance_use="other"), "not_satisfied")
        value = case()
        del value["age_public_assistance"]
        self.assertEqual(outcomes(evaluate_ecoa(value))["ECOA-AGE-PUBLIC-ASSISTANCE"], "unable_to_determine")

    def test_silence_is_not_compliance(self):
        value = case()
        del value["marital_status_inquiry"], value["spouse_signature"]
        r = evaluate_ecoa(value)
        self.assertEqual((outcomes(r)["ECOA-MARITAL-INQUIRY"], outcomes(r)["ECOA-SPOUSE-SIGNATURE"], r["compliance_result"]), ("unable_to_determine", "unable_to_determine", "Potential Issue"))


Contract = contract_tests("ecoa", evaluate_ecoa, validate_ecoa_rule_pack, validate_ecoa_decision_record, server, case,
                          ["within: (i) 30 days after receiving a completed application", "(iv) 90 days after notifying the applicant of a counteroffer",
                           "did not receive more than 150 applications", "shall not inquire about the applicant's marital status",
                           "shall not require the signature of an applicant's spouse or other person"])

if __name__ == "__main__":
    unittest.main()

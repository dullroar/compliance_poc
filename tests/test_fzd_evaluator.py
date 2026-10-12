import unittest

from compliance_mcp.fzd import evaluate_fzd, validate_fzd_decision_record, validate_fzd_rule_pack
from compliance_mcp.fzd.server import server
from evaluator_contract import contract_tests, outcomes

NOTICE_CONTENTS = {k: True for k in ("warning", "purchase_requirement_description", "nfip_private_availability", "same_coverage_private_statement", "compare_policies_statement", "disaster_relief_statement")}


def case(**changes):
    """A designated residential loan with everything in order."""
    value = dict(transaction_type="make", transaction_date="2024-05-01", credit_purpose="consumer", lien_position="first", loan_balance=425000, term_months=360,
                 collateral={"structure": "building", "residential": True},
                 determination={"completed": True, "standard_form_used": True, "retained": True, "date": "2024-03-20"},
                 sfha={"in_sfha": True, "flood_insurance_available": True, "zone": "AE"},
                 insurance={"type": "nfip", "in_force": True, "coverage_amount": 250000, "max_available_coverage": 250000, "effective_date": "2024-04-30", "expiration_date": "2025-04-30"},
                 notice={"borrower_date": "2024-04-20", "servicer_date": "2024-04-22", "record_retained": True, "contents": dict(NOTICE_CONTENTS)},
                 escrow={"escrowed": True})
    value.update(changes)
    return value


class FZDApplicabilityTests(unittest.TestCase):
    def test_designated_loan_in_good_order_is_compliant(self):
        r = evaluate_fzd(case())
        self.assertEqual((r["final_classification"], r["compliance_result"]), ("Flood Insurance Required", "Compliant"))

    def test_not_in_an_sfha_requires_nothing(self):
        r = evaluate_fzd(case(sfha={"in_sfha": False, "flood_insurance_available": True, "zone": "X"}))
        self.assertEqual((r["final_classification"], r["compliance_result"]), ("Flood Insurance Not Required", "Not Applicable"))
        self.assertNotIn("FZD-INSURANCE", outcomes(r))

    def test_no_building_or_mobile_home_means_not_a_designated_loan(self):
        r = evaluate_fzd(case(collateral={"structure": "none"}))
        self.assertEqual(r["final_classification"], "Flood Insurance Not Required")

    def test_sfha_without_available_insurance_still_needs_the_notice(self):
        r = evaluate_fzd(case(sfha={"in_sfha": True, "flood_insurance_available": False}))
        self.assertEqual((r["final_classification"], outcomes(r)["FZD-NOTICE"]), ("Flood Insurance Not Required", "satisfied"))
        self.assertNotIn("FZD-INSURANCE", outcomes(r))
        bare = evaluate_fzd(case(sfha={"in_sfha": True, "flood_insurance_available": False}, notice={}))
        self.assertEqual(outcomes(bare)["FZD-NOTICE"], "unable_to_determine")

    def test_unknown_sfha_status_is_never_assumed(self):
        for sfha in ({"flood_insurance_available": True}, {"in_sfha": None}, {"in_sfha": True}):
            with self.subTest(sfha=sfha):
                r = evaluate_fzd(case(sfha=sfha))
                self.assertEqual(r["final_classification"], "Unable To Determine")
                self.assertTrue(r["missing_facts"])
        self.assertEqual(evaluate_fzd(case(collateral={}))["final_classification"], "Unable To Determine")

    def test_deficient_determination_makes_the_sfha_status_unreliable(self):
        for change in ({"standard_form_used": False}, {"retained": False}, {"completed": False}, {"date": "2024-05-02"}):
            with self.subTest(change=change):
                r = evaluate_fzd(case(determination={"completed": True, "standard_form_used": True, "retained": True, "date": "2024-03-20", **change}))
                self.assertEqual((r["final_classification"], outcomes(r)["FZD-DETERMINATION"], r["compliance_result"]), ("Potential Flood Compliance Issue", "not_satisfied", "Non-Compliant"))
        self.assertEqual(evaluate_fzd(case(determination={}))["final_classification"], "Unable To Determine")


class FZDInsuranceTests(unittest.TestCase):
    def ins(self, **changes):
        return evaluate_fzd(case(insurance={**case()["insurance"], **changes}))

    def test_required_amount_is_the_lesser_of_balance_and_maximum_available(self):
        self.assertEqual(outcomes(self.ins())["FZD-INSURANCE"], "satisfied")                      # lesser = 250000
        self.assertEqual(outcomes(self.ins(coverage_amount=249999.99))["FZD-INSURANCE"], "not_satisfied")
        small = evaluate_fzd(case(loan_balance=100000, insurance={**case()["insurance"], "coverage_amount": 100000}))
        self.assertEqual((outcomes(small)["FZD-INSURANCE"], small["fzd_evaluation"]["required_coverage"]), ("satisfied", "100000"))
        self.assertEqual(outcomes(evaluate_fzd(case(loan_balance=100000, insurance={**case()["insurance"], "coverage_amount": 99999})))["FZD-INSURANCE"], "not_satisfied")

    def test_no_insurance_or_not_in_force(self):
        self.assertEqual(outcomes(self.ins(type="none"))["FZD-INSURANCE"], "not_satisfied")
        self.assertEqual(outcomes(self.ins(in_force=False))["FZD-INSURANCE"], "not_satisfied")
        self.assertEqual(self.ins(type="none")["compliance_result"], "Non-Compliant")

    def test_policy_term_must_cover_the_transaction_date(self):
        self.assertEqual(outcomes(self.ins(effective_date="2024-05-01"))["FZD-INSURANCE"], "satisfied")
        self.assertEqual(outcomes(self.ins(effective_date="2024-05-02"))["FZD-INSURANCE"], "not_satisfied")
        self.assertEqual(outcomes(self.ins(expiration_date="2024-04-30"))["FZD-INSURANCE"], "not_satisfied")

    def test_private_and_mutual_aid_policies_need_their_conditions(self):
        self.assertEqual(outcomes(self.ins(type="private_compliant"))["FZD-INSURANCE"], "satisfied")
        self.assertEqual(outcomes(self.ins(type="private_discretionary"))["FZD-INSURANCE"], "not_satisfied")
        self.assertEqual(outcomes(self.ins(type="private_discretionary", discretionary_sufficiency_documented=True))["FZD-INSURANCE"], "satisfied")
        self.assertEqual(outcomes(self.ins(type="mutual_aid"))["FZD-INSURANCE"], "not_satisfied")
        self.assertEqual(outcomes(self.ins(type="mutual_aid", mutual_aid_fca_determination=True))["FZD-INSURANCE"], "satisfied")

    def test_missing_amount_facts_are_unable_to_determine(self):
        value = case()
        del value["insurance"]["max_available_coverage"]
        r = evaluate_fzd(value)
        self.assertEqual((outcomes(r)["FZD-INSURANCE"], r["compliance_result"]), ("unable_to_determine", "Potential Issue"))


class FZDNoticeEscrowAndMonitoringTests(unittest.TestCase):
    def notice(self, **changes):
        n = {**case()["notice"], **changes}
        return outcomes(evaluate_fzd(case(notice=n)))["FZD-NOTICE"]

    def test_notice_timing_and_record(self):
        self.assertEqual(self.notice(), "satisfied")
        self.assertEqual(self.notice(borrower_date="2024-05-01"), "review_required")        # same day: reasonable-time judgment
        self.assertEqual(self.notice(borrower_date="2024-05-02"), "not_satisfied")
        self.assertEqual(self.notice(record_retained=False), "not_satisfied")
        self.assertEqual(self.notice(record_retained=None), "unable_to_determine")
        n = dict(case()["notice"])
        del n["servicer_date"]
        self.assertEqual(outcomes(evaluate_fzd(case(notice=n)))["FZD-NOTICE"], "unable_to_determine")

    def test_every_notice_element_is_required(self):
        for key in NOTICE_CONTENTS:
            with self.subTest(key=key):
                self.assertEqual(self.notice(contents={**NOTICE_CONTENTS, key: False}), "not_satisfied")

    def escrow(self, **changes):
        return outcomes(evaluate_fzd(case(**changes)))["FZD-ESCROW"]

    def test_escrow_requirement_and_exceptions(self):
        self.assertEqual(self.escrow(), "satisfied")
        self.assertEqual(self.escrow(escrow={"escrowed": False}), "not_satisfied")
        self.assertEqual(self.escrow(escrow={}), "unable_to_determine")
        for change in ({"credit_purpose": "agricultural"}, {"credit_purpose": "business"}, {"heloc": True}, {"nonperforming_90_days": True}, {"term_months": 12},
                       {"lien_position": "subordinate", "senior_lien_flood_insured": True}, {"escrow": {"escrowed": False, "small_lender_exception": True}}):
            with self.subTest(change=change):
                self.assertEqual(self.escrow(**{"escrow": {"escrowed": False}, **change}), "does_not_apply")
        self.assertEqual(self.escrow(term_months=13, escrow={"escrowed": False}), "not_satisfied")
        self.assertEqual(self.escrow(transaction_date="2015-12-31", determination={"completed": True, "standard_form_used": True, "retained": True, "date": "2015-12-01"},
                                     insurance={**case()["insurance"], "effective_date": "2015-12-01", "expiration_date": "2016-12-01"},
                                     notice={**case()["notice"], "borrower_date": "2015-12-20", "servicer_date": "2015-12-21"}), "does_not_apply")
        non_resi = evaluate_fzd(case(collateral={"structure": "building", "residential": False}))
        self.assertEqual(outcomes(non_resi)["FZD-ESCROW"], "does_not_apply")

    def test_force_placement_after_a_lapse(self):
        lapse = lambda **k: outcomes(evaluate_fzd(case(monitoring={"lapse_or_shortfall_detected": True, "borrower_notified_date": "2024-06-01", **k})))["FZD-FORCE-PLACEMENT"]  # noqa: E731
        self.assertEqual(lapse(review_date="2024-07-16"), "satisfied")                      # day 45: period not expired
        self.assertEqual(lapse(review_date="2024-07-17"), "not_satisfied")                  # day 46, no cure, no force placement
        self.assertEqual(lapse(review_date="2024-07-17", force_placed_date="2024-07-17"), "satisfied")
        self.assertEqual(lapse(review_date="2024-07-17", coverage_restored_date="2024-07-16"), "satisfied")
        self.assertEqual(lapse(), "unable_to_determine")
        self.assertEqual(outcomes(evaluate_fzd(case()))["FZD-FORCE-PLACEMENT"], "does_not_apply")


Contract = contract_tests("fzd", evaluate_fzd, validate_fzd_rule_pack, validate_fzd_decision_record, server, case,
                          ["at least equal to the lesser of the outstanding principal balance of the designated loan or the maximum limit of coverage available",
                           "within 45 days after notification", "A warning, in a form approved by the Administrator of FEMA",
                           "Designated loan means a loan secured by a building or mobile home that is located or to be located in a special flood hazard area",
                           "A System institution shall use the standard flood hazard determination form"])

if __name__ == "__main__":
    unittest.main()

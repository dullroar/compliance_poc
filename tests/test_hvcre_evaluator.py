import unittest

from compliance_mcp.hvcre import evaluate_hvcre, validate_hvcre_decision_record, validate_hvcre_rule_pack
from compliance_mcp.hvcre.server import server
from evaluator_contract import contract_tests, outcomes

PROPERTY = {"one_to_four_family_residential": False, "agricultural_land_bona_fide_farmer": False, "existing_income_producing": False, "improvement_to_existing_income_producing": False}


def case(**changes):
    """An ADC project that meets the definition and fails every exclusion (so: HVCRE)."""
    value = dict(loan_date="2025-06-01", credit_facility_amount=900000, primarily_finances_adc=True, purpose_income_producing=True,
                 dependent_on_future_income_or_sales=True, property=dict(PROPERTY),
                 capital={"as_completed_value": 1000000, "ltv_ratio": 70, "ltv_limit": 80, "contributions": {"cash": 100000},
                          "contributed_before_advances": True, "contractually_retained_until_reclassified": True})
    value.update(changes)
    return value


def cls(**changes):
    return evaluate_hvcre(case(**changes))["final_classification"]


class HVCREDefinitionTests(unittest.TestCase):
    def test_project_meeting_the_definition_with_no_exclusion_is_hvcre(self):
        r = evaluate_hvcre(case())
        self.assertEqual((r["final_classification"], r["compliance_result"]), ("HVCRE", "Compliant"))
        self.assertEqual(r["hvcre_evaluation"]["capital_required"], "150000.00")

    def test_loans_made_before_2025_are_not_hvcre(self):
        self.assertEqual(cls(loan_date="2024-12-31"), "Non-HVCRE")
        self.assertEqual(cls(loan_date="2025-01-01"), "HVCRE")

    def test_each_prong_is_required(self):
        for prong in ("primarily_finances_adc", "purpose_income_producing", "dependent_on_future_income_or_sales"):
            with self.subTest(prong=prong):
                self.assertEqual(cls(**{prong: False}), "Non-HVCRE")
                value = case()
                del value[prong]
                r = evaluate_hvcre(value)
                self.assertEqual((r["final_classification"], r["compliance_result"]), ("Unable To Determine", "Unable To Determine"))

    def test_reclassified_facilities_are_not_hvcre(self):
        self.assertEqual(cls(reclassified_to_non_hvcre=True), "Non-HVCRE")


class HVCREExclusionTests(unittest.TestCase):
    def prop(self, **changes):
        return case(property={**PROPERTY, **changes})

    def test_one_to_four_family_residential_needs_the_dwelling_at_50_percent(self):
        base = dict(one_to_four_family_residential=True)
        self.assertEqual(evaluate_hvcre(self.prop(dwelling_percent_of_collateral_value=50, **base))["final_classification"], "Non-HVCRE")
        self.assertEqual(evaluate_hvcre(self.prop(dwelling_percent_of_collateral_value=49.99, **base))["final_classification"], "HVCRE")
        self.assertEqual(evaluate_hvcre(self.prop(dwelling_percent_of_collateral_value=80, finances_only_land_improvements=True, **base))["final_classification"], "HVCRE")
        r = evaluate_hvcre(self.prop(**base))
        self.assertEqual((r["final_classification"], r["determination_status"]), ("Potential HVCRE", "Review Required"))

    def test_agricultural_land_exclusion_not_for_farm_construction_or_land_development(self):
        self.assertEqual(evaluate_hvcre(self.prop(agricultural_land_bona_fide_farmer=True))["final_classification"], "Non-HVCRE")
        self.assertEqual(evaluate_hvcre(self.prop(agricultural_land_bona_fide_farmer=True, farm_property_construction_or_land_development=True))["final_classification"], "HVCRE")

    def test_existing_income_producing_property_needs_sufficient_cash_flow(self):
        for key in ("existing_income_producing", "improvement_to_existing_income_producing"):
            with self.subTest(key=key):
                self.assertEqual(evaluate_hvcre(self.prop(**{key: True, "cash_flow_sufficient_for_permanent": True}))["final_classification"], "Non-HVCRE")
                self.assertEqual(evaluate_hvcre(self.prop(**{key: True, "cash_flow_sufficient_for_permanent": False}))["final_classification"], "HVCRE")
                self.assertEqual(evaluate_hvcre(self.prop(**{key: True}))["final_classification"], "Potential HVCRE")

    def test_loans_under_500000_are_excluded(self):
        self.assertEqual(cls(credit_facility_amount=499999.99, capital={}), "Non-HVCRE")
        self.assertEqual(cls(credit_facility_amount=500000, capital={"as_completed_value": 1000000, "ltv_ratio": 70, "ltv_limit": 80, "contributions": {"cash": 100000},
                                                                    "contributed_before_advances": True, "contractually_retained_until_reclassified": True}), "HVCRE")


class HVCRECapitalExclusionTests(unittest.TestCase):
    def capital(self, **changes):
        return evaluate_hvcre(case(capital={**case()["capital"], "contributions": {"cash": 150000}, **changes}))

    def test_fifteen_percent_boundary(self):
        self.assertEqual(self.capital()["final_classification"], "Non-HVCRE")
        self.assertEqual(self.capital(contributions={"cash": 149999.99})["final_classification"], "HVCRE")

    def test_all_contribution_forms_count_and_sum(self):
        mix = {"cash": 50000, "marketable_assets": 40000, "paid_development_expenses": 30000, "contributed_real_property_appraised": 30000}
        r = self.capital(contributions=mix)
        self.assertEqual((r["final_classification"], r["hvcre_evaluation"]["capital_contributed"]), ("Non-HVCRE", "150000"))

    def test_ltv_must_not_exceed_the_limit(self):
        self.assertEqual(self.capital(ltv_ratio=80)["final_classification"], "Non-HVCRE")
        self.assertEqual(self.capital(ltv_ratio=80.01)["final_classification"], "HVCRE")

    def test_capital_must_precede_advances_and_be_retained(self):
        self.assertEqual(self.capital(contributed_before_advances=False)["final_classification"], "HVCRE")
        self.assertEqual(self.capital(contractually_retained_until_reclassified=False)["final_classification"], "HVCRE")

    def test_as_is_value_is_used_only_when_no_as_completed_value_exists(self):
        value = case(capital={"as_is_value": 1000000, "ltv_ratio": 70, "ltv_limit": 80, "contributions": {"cash": 150000}, "contributed_before_advances": True, "contractually_retained_until_reclassified": True})
        r = evaluate_hvcre(value)
        self.assertEqual(r["final_classification"], "Non-HVCRE")
        self.assertIn("as-is value used", [x for x in r["rule_results"] if x["rule_id"] == "HVCRE-EXCL-CAPITAL"][0]["message"])

    def test_missing_ltv_limit_is_unable_to_determine_not_assumed(self):
        value = case(capital={"as_completed_value": 1000000, "contributions": {"cash": 150000}, "contributed_before_advances": True, "contractually_retained_until_reclassified": True})
        r = evaluate_hvcre(value)
        self.assertEqual((r["final_classification"], r["determination_status"]), ("Potential HVCRE", "Review Required"))
        self.assertTrue(any("ltv" in m["field"] for m in r["missing_facts"]))
        self.assertEqual(outcomes(r)["HVCRE-EXCL-CAPITAL"], "unable_to_determine")


Contract = contract_tests("hvcre", evaluate_hvcre, validate_hvcre_rule_pack, validate_hvcre_decision_record, server, case,
                          ["The borrower has contributed capital of at least 15 percent of the real property's appraised",
                           "An HVCRE exposure does not include any loan made prior to January 1, 2025",
                           "Loans originated for less than $500,000", "at least 50 percent of the total appraised value of the collateral",
                           "does not apply to loans for farm property construction and land development"])

if __name__ == "__main__":
    unittest.main()

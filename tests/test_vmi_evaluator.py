import unittest

from compliance_mcp.vmi import evaluate_vmi, validate_vmi_decision_record, validate_vmi_rule_pack
from compliance_mcp.vmi.server import server
from evaluator_contract import contract_tests, outcomes

PROVIDED = {"requested": True, "provided": True}
ITEMS = {k: dict(PROVIDED) for k in ("ethnicity", "race", "sex", "marital_status", "age")}
FIREWALL = {"underwriting_access_restricted": True, "decision_makers_without_access": True, "audit_logging": True}


def case(**changes):
    value = dict(evaluation_date="2024-05-01", primarily_purchase_or_refinance=True, principal_residence=True, secured_by_dwelling=True, dwelling_units=1,
                 hmda_reportable=True, application_channel="face_to_face", monitoring={"disclosure_given": True, "items": {k: dict(v) for k, v in ITEMS.items()}},
                 data_use={"used_in_underwriting": False}, firewall=dict(FIREWALL))
    value.update(changes)
    return value


def with_item(name, **item):
    c = case()
    c["monitoring"]["items"][name] = item
    return c


class VMIRequirementTests(unittest.TestCase):
    def test_fully_collected_is_proper(self):
        r = evaluate_vmi(case())
        self.assertEqual((r["final_classification"], r["compliance_result"], r["vmi_evaluation"]["collection_required"]), ("VMI Collected Properly", "Compliant", True))

    def test_required_only_for_purchase_or_refinance_of_a_1_to_4_unit_principal_residence_secured_by_it(self):
        for field, value in (("primarily_purchase_or_refinance", False), ("principal_residence", False), ("secured_by_dwelling", False), ("dwelling_units", 5)):
            with self.subTest(field=field):
                self.assertFalse(evaluate_vmi(case(**{field: value}))["vmi_evaluation"]["collection_required"])
        self.assertTrue(evaluate_vmi(case(dwelling_units=4))["vmi_evaluation"]["collection_required"])

    def test_not_required_is_permitted_when_hmda_reportable_else_not_required(self):
        self.assertEqual(evaluate_vmi(case(principal_residence=False))["final_classification"], "VMI Permitted")
        r = evaluate_vmi(case(principal_residence=False, hmda_reportable=False))
        self.assertEqual((r["final_classification"], r["compliance_result"]), ("VMI Not Required", "Not Applicable"))

    def test_marital_status_for_individual_unsecured_credit_is_prohibited(self):
        r = evaluate_vmi(case(principal_residence=False, individual_unsecured=True))
        self.assertEqual((r["final_classification"], r["compliance_result"]), ("VMI Collection Deficiency", "Non-Compliant"))
        self.assertEqual(evaluate_vmi(case(principal_residence=False, individual_unsecured=True, community_property=True))["final_classification"], "VMI Permitted")

    def test_missing_coverage_facts_are_unable_to_determine(self):
        value = case()
        del value["principal_residence"]
        r = evaluate_vmi(value)
        self.assertEqual((r["final_classification"], r["compliance_result"]), ("Unable To Determine", "Unable To Determine"))


class VMIItemTests(unittest.TestCase):
    def test_any_item_not_requested_is_a_deficiency(self):
        for name in ("ethnicity", "race", "sex", "marital_status", "age"):
            with self.subTest(name=name):
                r = evaluate_vmi(with_item(name, requested=False))
                self.assertEqual((outcomes(r)[f"VMI-REQUEST-{name.upper().replace('_', '-')}"], r["final_classification"], r["compliance_result"]), ("not_satisfied", "VMI Collection Deficiency", "Non-Compliant"))

    def test_the_samples_marital_status_gap_is_a_deficiency(self):
        r = evaluate_vmi(with_item("marital_status", requested=False))
        self.assertIn("marital status", [x["message"] for x in r["rule_results"] if x["outcome"] == "not_satisfied"][0].lower())

    def test_declination_must_be_noted_on_the_form(self):
        noted = evaluate_vmi(with_item("age", requested=True, declined=True, declination_noted=True))
        self.assertEqual(outcomes(noted)["VMI-REQUEST-AGE"], "satisfied")
        self.assertEqual(outcomes(evaluate_vmi(with_item("age", requested=True, declined=True, declination_noted=False)))["VMI-REQUEST-AGE"], "not_satisfied")
        self.assertEqual(outcomes(evaluate_vmi(with_item("age", requested=True, declined=True)))["VMI-REQUEST-AGE"], "unable_to_determine")
        self.assertEqual(outcomes(evaluate_vmi(with_item("age", requested=True)))["VMI-REQUEST-AGE"], "unable_to_determine")

    def test_declined_ethnicity_race_sex_need_observation_or_surname(self):
        base = dict(requested=True, declined=True, declination_noted=True)
        self.assertEqual(outcomes(evaluate_vmi(with_item("race", observation_or_surname_noted=True, **base)))["VMI-OBSERVATION-RACE"], "satisfied")
        self.assertEqual(outcomes(evaluate_vmi(with_item("race", observation_or_surname_noted=False, **base)))["VMI-OBSERVATION-RACE"], "not_satisfied")
        phone = with_item("race", observation_or_surname_noted=False, **base)
        phone["application_channel"] = "telephone"
        self.assertEqual(outcomes(evaluate_vmi(phone))["VMI-OBSERVATION-RACE"], "review_required")
        self.assertNotIn("VMI-OBSERVATION-AGE", outcomes(evaluate_vmi(with_item("age", **base))))

    def test_marital_terms_and_disclosure(self):
        self.assertEqual(outcomes(evaluate_vmi(with_item("marital_status", requested=True, provided=True, terms_valid=False)))["VMI-MARITAL-TERMS"], "not_satisfied")
        no_disclosure = case()
        no_disclosure["monitoring"]["disclosure_given"] = False
        self.assertEqual(outcomes(evaluate_vmi(no_disclosure))["VMI-DISCLOSURE"], "not_satisfied")
        unknown = case()
        del unknown["monitoring"]["disclosure_given"]
        self.assertEqual(evaluate_vmi(unknown)["final_classification"], "Potential Issue")

    def test_no_record_of_a_request_is_a_potential_issue(self):
        value = case()
        del value["monitoring"]
        r = evaluate_vmi(value)
        self.assertEqual((r["final_classification"], r["compliance_result"]), ("VMI Required", "Potential Issue"))

    def test_substitute_monitoring_program_is_reviewed_not_assumed(self):
        r = evaluate_vmi(case(substitute_monitoring_program=True))
        self.assertEqual((r["final_classification"], r["determination_status"]), ("VMI Required", "Review Required"))


class VMIPolicyRuleTests(unittest.TestCase):
    def test_use_in_underwriting_and_firewall_are_policy_rules(self):
        used = case(data_use={"used_in_underwriting": True})
        r = evaluate_vmi(used)
        self.assertEqual((outcomes(r)["VMI-USE"], r["final_classification"]), ("not_satisfied", "VMI Collection Deficiency"))
        self.assertEqual({x["basis"] for x in r["rule_results"] if x["rule_id"] in ("VMI-USE", "VMI-FIREWALL")}, {"institution_policy"})
        for key in FIREWALL:
            broken = case(firewall={**FIREWALL, key: False})
            self.assertEqual(outcomes(evaluate_vmi(broken))["VMI-FIREWALL"], "not_satisfied", key)
        unknown = case(firewall={"underwriting_access_restricted": True})
        self.assertEqual(outcomes(evaluate_vmi(unknown))["VMI-FIREWALL"], "unable_to_determine")


Contract = contract_tests("vmi", evaluate_vmi, validate_vmi_rule_pack, validate_vmi_decision_record, server, case,
                          ["shall request as part of the application the following information", "Marital status, using the categories married, unmarried, and separated",
                           "that fact shall be noted on the form", "visual observation or surname", "contains one to four units"])

if __name__ == "__main__":
    unittest.main()

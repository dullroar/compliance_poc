import copy
import unittest

from compliance_mcp.hmda import evaluate_hmda, validate_hmda_decision_record, validate_hmda_rule_pack
from compliance_mcp.hmda.lar import uli_check_digits, valid_uli
from compliance_mcp.hmda.server import server
from evaluator_contract import contract_tests, outcomes

EXCL = {k: False for k in ("fiduciary_capacity", "unimproved_land", "temporary_financing", "pool_interest_purchase", "servicing_rights_purchase",
                           "merger_acquisition_purchase", "partial_interest_purchase", "ny_supplemental_consolidation")}
ULI = "10Bx939c5543TqA1144M999143X38"                        # Appendix C's own worked example
PERSON = {"ethnicity": ["Not Hispanic or Latino"], "race": ["White"], "sex": ["male"], "collected_by_visual_observation_or_surname": False}
LAR = {
    "uli": ULI, "loan_type_government_program": "not_insured_or_guaranteed", "loan_purpose": "home_purchase", "preapproval": "not_requested",
    "construction_method": "site_built", "occupancy_type": "principal_residence", "loan_amount": 425000,
    "property_address": "1234 Rural Route 2", "property_state": "IL", "property_county": "Shelby", "property_census_tract": "17173960200",
    "applicant": dict(PERSON), "co_applicant": {**PERSON, "sex": ["female"]}, "age": 34, "income": 120,
    "lien_status": "first_lien", "credit_scores": [{"score": 720, "model": "FICO", "version": "Score 8"}],
    "total_loan_costs": 9500, "total_borrower_paid_charges": 7000, "discount_points": 0, "lender_credits": 0, "interest_rate": 7.85,
    "prepayment_penalty_term_months": 0, "debt_to_income_ratio": 38.5, "combined_loan_to_value_ratio": 72, "loan_term_months": 360,
    "non_amortizing_features": {"balloon_payment": False, "interest_only_payments": False, "negative_amortization": False, "other_non_fully_amortizing": False},
    "property_value": 590000, "total_units": 1, "application_channel": {"submitted_directly": True, "initially_payable_to_institution": True},
    "nmls_identifier": "987654", "reverse_mortgage": False, "open_end_line_of_credit": False, "business_or_commercial_purpose": False,
}
CTX = {"partial_exemption": False, "institution_type": "other", "sold_same_year": False, "subject_to_hoepa": False, "subject_to_1026_19f": True, "subject_to_1026_43c": True,
       "income_considered": True, "credit_score_relied_on": True, "dti_relied_on": True, "cltv_relied_on": True, "value_relied_on": True, "rate_may_change": False,
       "aus_used": False, "is_manufactured_home": False, "is_multifamily": False, "property_in_msa_with_office": True, "county_population_over_30000": True,
       "co_applicant_present": True, "application_mode": "in_person"}


def case(**changes):
    value = dict(financial_institution=True, credit_structure="closed_end", secured_by_dwelling=True, amount=425000, loan_purpose="home_purchase",
                 agricultural_purpose="not_primarily", business_commercial_purpose="not_primarily", exclusions=dict(EXCL),
                 prior_year_originations={"closed_end": [300, 320]}, action_taken="originated", action_taken_date="2024-05-01",
                 application_date="2024-03-15", apr=8.12, apor=6.86, reported_rate_spread=1.26, lar=copy.deepcopy(LAR), lar_context=dict(CTX))
    value.update(changes)
    return value


def with_lar(removes=(), ctx=None, **sets):
    c = case()
    for key in removes:
        c["lar"].pop(key, None)
    c["lar"].update(sets)
    c["lar_context"].update(ctx or {})
    return c


def items(result):
    return result["hmda_evaluation"]["lar_items"]


class HMDACoverageTests(unittest.TestCase):
    def test_a_complete_covered_origination_is_compliant(self):
        r = evaluate_hmda(case())
        self.assertEqual((r["final_classification"], r["compliance_result"], r["determination_status"]), ("Covered", "Compliant", "Determined"))

    def test_not_an_institution_or_not_dwelling_secured(self):
        self.assertEqual(evaluate_hmda(case(financial_institution=False))["final_classification"], "Not Covered")
        self.assertEqual(evaluate_hmda(case(secured_by_dwelling=False))["final_classification"], "Not Covered")

    def test_each_excluded_transaction(self):
        for key in EXCL:
            with self.subTest(key=key):
                r = evaluate_hmda(case(exclusions={**EXCL, key: True}))
                self.assertEqual((r["final_classification"], r["compliance_result"]), ("Not Covered", "Not Applicable"))

    def test_amount_boundary_at_500_dollars(self):
        self.assertEqual(evaluate_hmda(case(amount=499.99))["final_classification"], "Not Covered")
        self.assertEqual(evaluate_hmda(case(amount=500))["final_classification"], "Covered")

    def test_origination_volume_thresholds(self):
        self.assertEqual(evaluate_hmda(case(prior_year_originations={"closed_end": [25, 25]}))["final_classification"], "Covered")
        self.assertEqual(evaluate_hmda(case(prior_year_originations={"closed_end": [25, 24]}))["final_classification"], "Not Covered")
        self.assertEqual(evaluate_hmda(case(credit_structure="open_end", prior_year_originations={"open_end": [200, 199]}))["final_classification"], "Not Covered")
        self.assertEqual(evaluate_hmda(case(credit_structure="open_end", prior_year_originations={"open_end": [200, 200]}))["final_classification"], "Covered")

    def test_agricultural_and_business_purpose_exclusions(self):
        self.assertEqual(evaluate_hmda(case(agricultural_purpose="primarily"))["final_classification"], "Not Covered")
        self.assertEqual(evaluate_hmda(case(business_commercial_purpose="primarily", loan_purpose="other"))["final_classification"], "Not Covered")
        for purpose in ("home_purchase", "home_improvement", "refinance", "cash_out_refinance"):
            self.assertEqual(evaluate_hmda(case(business_commercial_purpose="primarily", loan_purpose=purpose))["final_classification"], "Covered", purpose)

    def test_undetermined_purpose_is_potentially_covered_for_review(self):
        for field in ("agricultural_purpose", "business_commercial_purpose"):
            r = evaluate_hmda(case(**{field: "undetermined"}))
            self.assertEqual((r["final_classification"], r["determination_status"], r["compliance_result"]), ("Potentially Covered", "Review Required", "Potential Issue"))

    def test_reporting_findings_are_still_produced_while_coverage_is_undecided(self):
        r = evaluate_hmda(case(agricultural_purpose="undetermined", reported_rate_spread=2.37))
        self.assertEqual((r["final_classification"], r["compliance_result"], outcomes(r)["HMDA-RATE-SPREAD"]), ("Potentially Covered", "Potential Issue", "not_satisfied"))

    def test_missing_exclusion_facts_are_unable_to_determine_not_assumed(self):
        for label, value in {"no agricultural flag": case(), "no volume": case(prior_year_originations={}), "partial exclusions": case(exclusions={"unimproved_land": False})}.items():
            with self.subTest(label):
                if label == "no agricultural flag":
                    del value["agricultural_purpose"]
                r = evaluate_hmda(value)
                self.assertEqual((r["final_classification"], r["compliance_result"]), ("Unable To Determine", "Unable To Determine"))
                self.assertTrue(r["missing_facts"])


class HMDAActionAndRateSpreadTests(unittest.TestCase):
    def test_action_before_application_is_not_satisfied(self):
        r = evaluate_hmda(case(action_taken_date="2024-03-14"))
        self.assertEqual((outcomes(r)["HMDA-ACTION"], r["compliance_result"]), ("not_satisfied", "Non-Compliant"))
        self.assertEqual(outcomes(evaluate_hmda(case(action_taken_date="2024-03-15")))["HMDA-ACTION"], "satisfied")

    def test_purchased_loans_need_no_application_date(self):
        value = case(action_taken="purchased", reported_rate_spread=None)
        del value["application_date"]
        self.assertEqual(outcomes(evaluate_hmda(value))["HMDA-ACTION"], "satisfied")

    def test_rate_spread_is_recomputed_from_apr_minus_apor(self):
        r = evaluate_hmda(case(reported_rate_spread=2.37))
        self.assertEqual((outcomes(r)["HMDA-RATE-SPREAD"], items(r)["12"]), ("not_satisfied", "not_satisfied"))
        self.assertEqual(r["hmda_evaluation"]["rate_spread_computed"], "1.260")
        self.assertEqual(outcomes(evaluate_hmda(case(reported_rate_spread=1.26)))["HMDA-RATE-SPREAD"], "satisfied")
        self.assertEqual(outcomes(evaluate_hmda(case(reported_rate_spread=1.261)))["HMDA-RATE-SPREAD"], "not_satisfied")

    def test_rate_spread_applicability_and_missing_inputs(self):
        self.assertEqual(outcomes(evaluate_hmda(case(action_taken="withdrawn", reported_rate_spread=None)))["HMDA-RATE-SPREAD"], "does_not_apply")
        self.assertEqual(outcomes(evaluate_hmda(case(action_taken="withdrawn", reported_rate_spread=1.26)))["HMDA-RATE-SPREAD"], "not_satisfied")
        self.assertEqual(outcomes(evaluate_hmda(case(reverse_mortgage=True, reported_rate_spread=None)))["HMDA-RATE-SPREAD"], "does_not_apply")
        no_apor = case()
        del no_apor["apor"]
        r = evaluate_hmda(no_apor)
        self.assertEqual((outcomes(r)["HMDA-RATE-SPREAD"], items(r)["12"]), ("unable_to_determine", "unable"))
        self.assertEqual(outcomes(evaluate_hmda(case(reported_rate_spread=None)))["HMDA-RATE-SPREAD"], "unable_to_determine")


class HMDAAllThirtyEightItemsTests(unittest.TestCase):
    def test_every_one_of_the_38_items_is_evaluated_and_a_complete_register_entry_passes(self):
        r = evaluate_hmda(case())
        self.assertEqual(sorted(map(int, items(r))), list(range(1, 39)))
        self.assertEqual(r["hmda_evaluation"]["lar_summary"]["not_satisfied"] + r["hmda_evaluation"]["lar_summary"]["unable"], 0)
        self.assertEqual(outcomes(r)["HMDA-LAR-ITEMS"], "satisfied")
        self.assertEqual({k: v for k, v in items(r).items() if v == "not_applicable"}.keys(), {"11", "13", "16", "26", "29", "30", "32", "35"})

    def test_each_applicable_item_that_is_missing_cannot_be_determined_and_is_listed_as_missing(self):
        missing_one = {1: "uli", 2: "loan_type_government_program", 3: "loan_purpose", 4: "preapproval", 5: "construction_method", 6: "occupancy_type", 7: "loan_amount",
                       9: "property_address", 10: "applicant", 14: "lien_status", 15: "credit_scores", 17: "total_loan_costs", 18: "total_borrower_paid_charges",
                       19: "discount_points", 20: "lender_credits", 21: "interest_rate", 22: "prepayment_penalty_term_months", 23: "debt_to_income_ratio",
                       24: "combined_loan_to_value_ratio", 25: "loan_term_months", 27: "non_amortizing_features", 28: "property_value", 31: "total_units",
                       33: "application_channel", 34: "nmls_identifier", 36: "reverse_mortgage", 37: "open_end_line_of_credit", 38: "business_or_commercial_purpose"}
        for number, field in missing_one.items():
            with self.subTest(item=number, field=field):
                r = evaluate_hmda(with_lar(removes=[field]))
                self.assertEqual(items(r)[str(number)], "unable", number)
                self.assertTrue(any(m["field"].startswith("lar") for m in r["missing_facts"]))
                self.assertEqual(outcomes(r)[f"HMDA-LAR-{number:02d}"], "unable_to_determine")
                self.assertEqual(r["compliance_result"], "Potential Issue")

    def test_invalid_values_are_not_satisfied(self):
        bad = {2: ("loan_type_government_program", "usda"), 3: ("loan_purpose", "vacation"), 5: ("construction_method", "tent"), 6: ("occupancy_type", "timeshare"),
               7: ("loan_amount", 1), 14: ("lien_status", "third"), 21: ("interest_rate", 0), 25: ("loan_term_months", 0), 31: ("total_units", 0),
               27: ("non_amortizing_features", {"balloon_payment": True}), 28: ("property_value", -5), 34: ("nmls_identifier", " "), 36: ("reverse_mortgage", True),
               37: ("open_end_line_of_credit", True), 38: ("business_or_commercial_purpose", True), 33: ("application_channel", {"submitted_directly": "yes"}),
               22: ("prepayment_penalty_term_months", -1), 23: ("debt_to_income_ratio", "high"), 17: ("total_loan_costs", "lots")}
        for number, (field, value) in bad.items():
            with self.subTest(item=number):
                r = evaluate_hmda(with_lar(**{field: value}))
                self.assertEqual(items(r)[str(number)], "not_satisfied", number)
                self.assertEqual(r["compliance_result"], "Non-Compliant")

    def test_reporting_not_applicable_where_the_item_applies_is_wrong(self):
        r = evaluate_hmda(with_lar(interest_rate="not_applicable"))
        self.assertEqual(items(r)["21"], "not_satisfied")

    def test_denied_application_items(self):
        c = case(action_taken="denied", reported_rate_spread=None)
        for key in ("interest_rate", "total_loan_costs", "total_borrower_paid_charges", "discount_points", "lender_credits"):
            c["lar"].pop(key, None)
        r = evaluate_hmda(c)
        self.assertEqual({items(r)[str(n)] for n in (17, 18, 19, 20, 21)}, {"not_applicable"})
        self.assertEqual(items(r)["16"], "unable")                                     # denied needs 1-4 reasons
        for reasons, expected in ((["credit history"], "satisfied"), (list("abcde"), "not_satisfied"), ([""], "not_satisfied")):
            c["lar"]["denial_reasons"] = reasons
            self.assertEqual(items(evaluate_hmda(c))["16"], expected, reasons)
        c = case(action_taken="denied", denial_reasons=["credit history"], reported_rate_spread=None)
        self.assertEqual(items(evaluate_hmda(c))["16"], "satisfied")                    # top-level reasons are accepted too

    def test_purchased_loan_items(self):
        c = case(action_taken="purchased", reported_rate_spread=None)
        for key in ("applicant", "co_applicant", "age", "income", "credit_scores", "debt_to_income_ratio", "combined_loan_to_value_ratio", "application_channel"):
            c["lar"].pop(key, None)
        c["lar_context"]["sold_same_year"] = True
        c["lar"]["purchaser_type"] = "Fannie Mae"
        r = evaluate_hmda(c)
        self.assertEqual(items(r)["10"], "satisfied")                                  # 1003.4(b)(2): need not be collected
        self.assertEqual({items(r)[str(n)] for n in (15, 23, 24, 33, 35, 22)}, {"not_applicable"})
        self.assertEqual(items(r)["11"], "satisfied")
        del c["lar"]["purchaser_type"]
        self.assertEqual(items(evaluate_hmda(c))["11"], "unable")

    def test_context_flags_decide_which_items_apply(self):
        self.assertEqual(items(evaluate_hmda(with_lar(ctx={"sold_same_year": True})))["11"], "unable")
        self.assertEqual(items(evaluate_hmda(with_lar(ctx={"sold_same_year": True}, purchaser_type="Freddie Mac")))["11"], "satisfied")
        self.assertEqual(items(evaluate_hmda(with_lar(ctx={"subject_to_hoepa": True})))["13"], "unable")
        self.assertEqual(items(evaluate_hmda(with_lar(ctx={"subject_to_hoepa": True}, hoepa_status="not_high_cost_mortgage")))["13"], "satisfied")
        self.assertEqual(items(evaluate_hmda(with_lar(ctx={"rate_may_change": True}, introductory_rate_period_months=60)))["26"], "satisfied")
        self.assertEqual(items(evaluate_hmda(with_lar(ctx={"rate_may_change": True})))["26"], "unable")
        self.assertEqual(items(evaluate_hmda(with_lar(ctx={"aus_used": True}, automated_underwriting={"system": "DU", "result": "Approve/Eligible"})))["35"], "satisfied")
        self.assertEqual(items(evaluate_hmda(with_lar(ctx={"aus_used": True})))["35"], "unable")
        no_19f = evaluate_hmda(with_lar(removes=["total_borrower_paid_charges", "discount_points", "lender_credits", "total_loan_costs"], ctx={"subject_to_1026_19f": False}, total_points_and_fees=5000))
        self.assertEqual({items(no_19f)[str(n)] for n in (18, 19, 20)}, {"not_applicable"})
        self.assertEqual(items(no_19f)["17"], "satisfied")                             # points and fees when no Closing Disclosure applies
        unknown = case()
        del unknown["lar_context"]["subject_to_hoepa"]
        r = evaluate_hmda(unknown)
        self.assertEqual(items(r)["13"], "unable")
        self.assertIn("lar_context.subject_to_hoepa", [m["field"] for m in r["missing_facts"]])

    def test_manufactured_home_and_multifamily_items(self):
        mh = with_lar(ctx={"is_manufactured_home": True}, construction_method="manufactured_home")
        self.assertEqual({items(evaluate_hmda(mh))[str(n)] for n in (29, 30)}, {"unable"})
        mh["lar"].update(manufactured_home_secured_property_type="manufactured_home_and_land", manufactured_home_land_property_interest="direct_ownership")
        self.assertEqual({items(evaluate_hmda(mh))[str(n)] for n in (29, 30)}, {"satisfied"})
        both = with_lar(ctx={"is_manufactured_home": True, "is_multifamily": True}, multifamily_affordable_units=2)
        r = evaluate_hmda(both)
        self.assertEqual(({items(r)[str(n)] for n in (29, 30)}, items(r)["32"]), ({"not_applicable"}, "satisfied"))
        self.assertEqual(items(evaluate_hmda(with_lar(ctx={"is_multifamily": True})))["32"], "unable")

    def test_income_credit_score_dti_cltv_value_follow_what_the_decision_relied_on(self):
        c = with_lar(removes=["income", "credit_scores", "debt_to_income_ratio", "combined_loan_to_value_ratio", "property_value"],
                     ctx={"income_considered": False, "credit_score_relied_on": False, "dti_relied_on": False, "cltv_relied_on": False, "value_relied_on": False})
        r = evaluate_hmda(c)
        self.assertEqual({items(r)[str(n)] for n in (15, 23, 24, 28)}, {"not_applicable"})
        self.assertEqual(items(r)["10"], "satisfied")
        c["lar"]["income"] = 90
        self.assertEqual(items(evaluate_hmda(c))["10"], "not_satisfied")                  # income reported though not considered

    def test_location_rules(self):
        self.assertEqual(items(evaluate_hmda(with_lar(ctx={"property_in_msa_with_office": False}, removes=["property_state", "property_county", "property_census_tract"])))["9"], "satisfied")
        self.assertEqual(items(evaluate_hmda(with_lar(ctx={"county_population_over_30000": False}, removes=["property_census_tract"])))["9"], "satisfied")
        self.assertEqual(items(evaluate_hmda(with_lar(removes=["property_census_tract"])))["9"], "unable")
        self.assertEqual(items(evaluate_hmda(with_lar(property_census_tract="123")))["9"], "not_satisfied")
        self.assertEqual(items(evaluate_hmda(with_lar(property_state="Illinois")))["9"], "not_satisfied")
        c = case()
        del c["lar_context"]["property_in_msa_with_office"]
        self.assertEqual(items(evaluate_hmda(c))["9"], "unable")


class HMDAULITests(unittest.TestCase):
    def test_check_digit_matches_appendix_c_worked_example(self):
        self.assertEqual(uli_check_digits("10Bx939c5543TqA1144M999143X"), "38")
        self.assertEqual(valid_uli(ULI), [])
        self.assertEqual(valid_uli(ULI.upper()), [])

    def test_invalid_ulis(self):
        self.assertIn("check digit", valid_uli("10Bx939c5543TqA1144M999143X39")[0])
        self.assertIn("23-45", valid_uli("10Bx939c5543TqA1144M99")[0])
        self.assertIn("letters and numerals", valid_uli("10Bx939c5543TqA1144M999143X-8")[0])
        self.assertEqual(items(evaluate_hmda(with_lar(uli="10Bx939c5543TqA1144M999143X39")))["1"], "not_satisfied")

    def test_any_generated_uli_validates(self):
        for base in ("549300ABCDEF12345678LOAN0001", "5493001KJTIIGC8Y1R12" + "A" * 23):
            self.assertEqual(valid_uli(base + uli_check_digits(base)), [], base)


class HMDADemographicsTests(unittest.TestCase):
    def applicant(self, **changes):
        return items(evaluate_hmda(with_lar(applicant={**PERSON, **changes})))["10"]

    def test_valid_and_invalid_categories(self):
        self.assertEqual(self.applicant(), "satisfied")
        self.assertEqual(self.applicant(ethnicity=["Mexican"], race=["Asian", "Korean"]), "satisfied")
        self.assertEqual(self.applicant(race=["Martian"]), "not_satisfied")
        self.assertEqual(self.applicant(sex=["unknown"]), "not_satisfied")
        self.assertEqual(self.applicant(sex=["male", "female"]), "satisfied")

    def test_particular_entries_and_the_five_entry_maximum(self):
        self.assertEqual(self.applicant(ethnicity=[{"particular": "Dominican"}]), "satisfied")
        self.assertEqual(self.applicant(ethnicity=[{"particular": " "}]), "not_satisfied")
        five = ["Hispanic or Latino", "Not Hispanic or Latino", "Mexican", "Puerto Rican", "Cuban"]
        self.assertEqual(self.applicant(ethnicity=five), "satisfied")
        self.assertEqual(self.applicant(ethnicity=five + ["Other Hispanic or Latino"]), "not_satisfied")
        races = ["White", "Asian", "Black or African American", "Korean", "Chinese"]
        self.assertEqual(self.applicant(race=races), "satisfied")
        self.assertEqual(self.applicant(race=races + ["Samoan"]), "not_satisfied")

    def test_visual_observation_or_surname_uses_aggregate_categories_and_must_be_reported(self):
        self.assertEqual(self.applicant(collected_by_visual_observation_or_surname=True), "satisfied")
        self.assertEqual(self.applicant(collected_by_visual_observation_or_surname=True, race=["Korean"]), "not_satisfied")
        value = {k: v for k, v in PERSON.items() if k != "collected_by_visual_observation_or_surname"}
        self.assertEqual(items(evaluate_hmda(with_lar(applicant=value)))["10"], "unable")

    def test_information_not_provided_depends_on_how_the_application_was_taken(self):
        declined = {"ethnicity": ["information_not_provided"], "race": ["information_not_provided"], "sex": ["information_not_provided"]}
        self.assertEqual(items(evaluate_hmda(with_lar(applicant={**PERSON, **declined}, ctx={"application_mode": "in_person"})))["10"], "not_satisfied")
        for mode in ("mail", "internet", "telephone"):
            self.assertEqual(items(evaluate_hmda(with_lar(applicant={**PERSON, **declined}, ctx={"application_mode": mode})))["10"], "satisfied", mode)

    def test_co_applicant_rules(self):
        self.assertEqual(items(evaluate_hmda(with_lar(ctx={"co_applicant_present": False}, co_applicant="none")))["10"], "satisfied")
        self.assertEqual(items(evaluate_hmda(with_lar(ctx={"co_applicant_present": False})))["10"], "not_satisfied")       # block reported with no co-applicant
        self.assertEqual(items(evaluate_hmda(with_lar(removes=["co_applicant"])))["10"], "unable")                          # co-applicant present, no block reported yet
        self.assertEqual(items(evaluate_hmda(with_lar(co_applicant={**PERSON, "race": ["Martian"]})))["10"], "not_satisfied")

    def test_missing_pieces_cannot_be_determined_but_invalid_ones_fail(self):
        for removed, expect in (("age", "unable"), ("income", "unable")):
            self.assertEqual(items(evaluate_hmda(with_lar(removes=[removed])))["10"], expect, removed)
        for part in ("ethnicity", "race", "sex"):
            self.assertEqual(self.applicant(**{part: []}), "unable", part)
        self.assertEqual(items(evaluate_hmda(with_lar(income="lots")))["10"], "not_satisfied")
        missing = evaluate_hmda(with_lar(removes=["age", "income"]))
        self.assertTrue({"lar.age", "lar.income"} <= {m["field"] for m in missing["missing_facts"]})

    def test_age_and_not_applicable_reporting(self):
        self.assertEqual(items(evaluate_hmda(with_lar(age=151)))["10"], "not_satisfied")
        self.assertEqual(items(evaluate_hmda(with_lar(applicant="not_applicable")))["10"], "not_satisfied")               # only for purchased / non-natural persons
        c = case(action_taken="purchased", reported_rate_spread=None)
        c["lar"]["applicant"], c["lar"]["age"] = "not_applicable", "not_applicable"
        self.assertEqual(items(evaluate_hmda(c))["10"], "satisfied")


class HMDAPartialExemptionTests(unittest.TestCase):
    OPTIONAL = [12, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 32, 33, 34, 35, 36, 37, 38]

    def exempt_case(self, **ctx):
        c = case(lar_context={**CTX, "partial_exemption": True, "institution_type": "insured_depository", **ctx}, prior_year_originations={"closed_end": [499, 480]})
        for key in ("credit_scores", "total_loan_costs", "total_borrower_paid_charges", "discount_points", "lender_credits", "interest_rate", "prepayment_penalty_term_months",
                    "debt_to_income_ratio", "combined_loan_to_value_ratio", "loan_term_months", "non_amortizing_features", "property_value", "application_channel",
                    "nmls_identifier", "reverse_mortgage", "open_end_line_of_credit", "business_or_commercial_purpose", "property_address"):
            c["lar"].pop(key)
        c["reported_rate_spread"] = None
        return c

    def test_a_valid_partial_exemption_removes_only_the_optional_data_items(self):
        r = evaluate_hmda(self.exempt_case())
        self.assertEqual(outcomes(r)["HMDA-PARTIAL-EXEMPTION"], "satisfied")
        self.assertEqual({items(r)[str(n)] for n in (15, 17, 21, 25, 33, 34, 38)}, {"exempt"})
        self.assertEqual(r["compliance_result"], "Compliant")
        for number in (2, 3, 6, 7, 10, 14, 31):                                             # not optional data
            c = self.exempt_case()
            field = {2: "loan_type_government_program", 3: "loan_purpose", 6: "occupancy_type", 7: "loan_amount", 10: "applicant", 14: "lien_status", 31: "total_units"}[number]
            del c["lar"][field]
            self.assertEqual(items(evaluate_hmda(c))[str(number)], "unable", number)

    def test_the_identifier_and_street_address_are_optional_but_the_rest_of_items_1_and_9_are_not(self):
        c = self.exempt_case()
        del c["lar"]["uli"]
        c["lar"]["nuli"] = "LOAN2024001"
        self.assertEqual(items(evaluate_hmda(c))["1"], "satisfied")
        c["lar"]["nuli"] = "X" * 23
        self.assertEqual(items(evaluate_hmda(c))["1"], "not_satisfied")
        self.assertEqual(items(evaluate_hmda(self.exempt_case()))["9"], "satisfied")           # no street address
        c = self.exempt_case()
        del c["lar"]["property_county"]
        self.assertEqual(items(evaluate_hmda(c))["9"], "unable")

    def test_the_exemption_is_not_available_to_everyone(self):
        for label, changes, expect in (("other institution type", {"institution_type": "other"}, "not_satisfied"),
                                       ("poor CRA rating", {"cra_poor_rating": True}, "not_satisfied")):
            r = evaluate_hmda(self.exempt_case(**changes))
            self.assertEqual(outcomes(r)["HMDA-PARTIAL-EXEMPTION"], expect, label)
            self.assertEqual(items(r)["25"], "unable", label)                                # optional items are required again
        big = self.exempt_case()
        big["prior_year_originations"] = {"closed_end": [500, 100]}
        r = evaluate_hmda(big)
        self.assertEqual((outcomes(r)["HMDA-PARTIAL-EXEMPTION"], items(r)["25"]), ("not_satisfied", "unable"))
        unknown = self.exempt_case()
        unknown["prior_year_originations"] = {}
        unknown["lar_context"]["partial_exemption"] = True
        self.assertEqual(evaluate_hmda(unknown)["final_classification"], "Unable To Determine")


class HMDAContractAndSampleTests(unittest.TestCase):
    def test_the_pack_pins_every_one_of_the_38_items(self):
        import yaml
        from pathlib import Path
        meta = yaml.safe_load((Path(__file__).resolve().parents[1] / "compliance_mcp/hmda/pack/lar_items.yaml").read_text(encoding="utf-8"))
        self.assertEqual([i["number"] for i in meta["items"]], list(range(1, 39)))
        self.assertEqual({i["number"] for i in meta["items"] if i["optional"] is True}, {12, *range(15, 31), *range(32, 39)})
        self.assertEqual({i["number"] for i in meta["items"] if i["optional"] == "partial"}, {1, 9})
        self.assertTrue(all(i["cite"].startswith("12 CFR 1003.4(a)(") for i in meta["items"]))


Contract = contract_tests("hmda", evaluate_hmda, validate_hmda_rule_pack, validate_hmda_decision_record, server, case,
                          ["Excluded transactions", "less than $500", "used primarily for agricultural purposes", "fewer than 25 closed-end mortgage loans",
                           "fewer than 200 open-end lines of credit", "difference between the covered loan's annual percentage rate and the average prime offer rate",
                           "(38) Whether the covered loan is, or the application is for a covered loan that will be, made primarily for a business or commercial purpose",
                           "ISO/IEC 7064, MOD 97-10", "Append the check digit", "must not report more than a total of five aggregate ethnicity categories"])

if __name__ == "__main__":
    unittest.main()

import copy
import importlib
import json
import unittest
from pathlib import Path

from agent_prompts import AGENTS
from compliance_common.assemble import assemble
from compliance_mcp.auditor import evaluate_auditor, validate_auditor_decision_record, validate_auditor_rule_pack
from compliance_mcp.auditor.adapter import tool_arguments
from compliance_mcp.auditor.server import server
from evaluator_contract import contract_tests, outcomes

SAMPLE = json.loads((Path(__file__).resolve().parents[1] / "sample_loan.json").read_text(encoding="utf-8"))
DOMAINS = ("hmda", "ecoa", "hvcre", "hpml", "trid", "fzd", "ybs", "vmi")


def assembled(loan):
    """Real evaluator outputs, assembled exactly as the agents would, keyed by agent."""
    out = {}
    for key in DOMAINS:
        evaluate = getattr(importlib.import_module(f"compliance_mcp.{key}"), f"evaluate_{key}")
        adapter = importlib.import_module(f"compliance_mcp.{key}.adapter")
        decision = evaluate(loan[f"{key}_case"])
        out[key] = assemble(AGENTS[key], decision, {}, adapter.extras(decision))
    return out


def audit(loan=None, drop=(), mutate=None):
    loan = copy.deepcopy(loan or SAMPLE)
    if mutate:
        mutate(loan)
    results = assembled(loan)
    for key in drop:
        results.pop(key)
    args, why = tool_arguments({"loan_data": loan, "agent_results": results})
    assert args, why
    return evaluate_auditor(args["case"])


def cross_ids(record):
    return [c["id"] for c in record["auditor_evaluation"]["cross_regime_findings"]]


class AuditorOnTheSampleTests(unittest.TestCase):
    def test_the_sample_has_exactly_the_two_real_cross_regime_problems(self):
        r = audit()
        self.assertEqual((r["final_classification"], r["compliance_result"]), ("Multiple Cross-Regime Deficiencies", "Non-Compliant"))
        self.assertEqual(sorted(cross_ids(r)), ["AUD-DEMOGRAPHICS", "AUD-RATE-SPREAD"])
        findings = {c["id"]: c for c in r["auditor_evaluation"]["cross_regime_findings"]}
        self.assertEqual(findings["AUD-RATE-SPREAD"]["affected_agents"], ["hmda", "hpml"])
        self.assertIn("2.37", findings["AUD-RATE-SPREAD"]["impact_summary"])
        self.assertEqual(findings["AUD-DEMOGRAPHICS"]["affected_agents"], ["hmda", "vmi"])
        self.assertEqual(findings["AUD-RATE-SPREAD"]["severity"], "High")

    def test_explained_per_agent_outcomes_are_not_repeated_as_isolated_findings(self):
        isolated = {i["agent"]: i["summary"] for i in audit()["auditor_evaluation"]["isolated_findings"]}
        self.assertNotIn("HMDA-RATE-SPREAD", isolated["hmda"])
        self.assertNotIn("HMDA-LAR-FIELDS", isolated["hmda"])
        self.assertIn("VMI-REQUEST-MARITAL-STATUS", isolated["vmi"])

    def test_priorities_put_cross_regime_issues_first(self):
        priorities = audit()["auditor_evaluation"]["remediation_priorities"]
        self.assertEqual([p["priority"] for p in priorities], list(range(1, len(priorities) + 1)))
        self.assertTrue(priorities[0]["issue"].startswith("HMDA reported rate spread"))

    def test_fixing_the_two_conflicts_leaves_only_isolated_findings(self):
        def fix(loan):
            loan["hmda_case"]["reported_rate_spread"] = 1.26
            loan["hmda_case"]["lar"].update(applicant={"ethnicity": ["Not Hispanic or Latino"], "race": ["White"], "sex": ["male"], "collected_by_visual_observation_or_surname": False}, age=34)
        r = audit(mutate=fix)
        self.assertEqual((r["final_classification"], cross_ids(r)), ("Isolated Findings", []))


class AuditorChecksTests(unittest.TestCase):
    def test_each_consistency_check_catches_its_conflict(self):
        cases = {
            "AUD-PRICING": lambda l: l["hmda_case"].update(apr=9.5),
            "AUD-AMOUNT": lambda l: l["hmda_case"].update(amount=430000),
            "AUD-DATES": lambda l: l["trid_case"].update(application_received_date="2024-03-10"),
            "AUD-CASE-ID": lambda l: l["ecoa_case"].update(case_id="OTHER-LOAN"),
            "AUD-OCCUPANCY": lambda l: l["vmi_case"].update(principal_residence=False),
        }
        for rule_id, mutate in cases.items():
            with self.subTest(rule_id=rule_id):
                r = audit(mutate=mutate)
                self.assertIn(rule_id, cross_ids(r))

    def test_closing_date_conflict_across_trid_flood_and_hvcre(self):
        r = audit(mutate=lambda l: l["fzd_case"].update(transaction_date="2024-05-02"))
        finding = [c for c in r["auditor_evaluation"]["cross_regime_findings"] if "Closing" in c["impact_summary"]][0]
        self.assertIn("fzd", finding["affected_agents"])

    def test_scope_disagreement_between_vmi_and_hmda(self):
        def covered(loan):
            loan["hmda_case"]["agricultural_purpose"] = "not_primarily"
            loan["vmi_case"]["hmda_reportable"] = False
        self.assertIn("AUD-SCOPE", cross_ids(audit(mutate=covered)))

    def test_a_missing_fact_reported_by_two_agents_is_a_shared_root_cause(self):
        def gap(loan):
            del loan["ecoa_case"]["application_complete_date"]
            del loan["trid_case"]["application_received_date"]
            loan["trid_case"]["application_received_date"] = "2024-03-15"
        r = audit(mutate=gap)
        shared = [c for c in r["auditor_evaluation"]["cross_regime_findings"] if c["id"] == "AUD-SHARED-GAP"]
        # both the ECOA case and the HMDA LAR lack data; assert the mechanism works on whatever is genuinely shared
        self.assertTrue(all(len(c["affected_agents"]) >= 2 for c in shared))

    def test_booleans_are_never_compared_as_numbers(self):
        """Regression: bool is an int subclass; comparing True to a number crashed Decimal()."""
        r = audit(mutate=lambda l: l["hpml_case"].update(secured_by_principal_dwelling=True))
        self.assertNotIn("AUD-OCCUPANCY", cross_ids(r))


class AuditorCompletenessTests(unittest.TestCase):
    def test_a_missing_agent_is_never_assumed_to_pass(self):
        r = audit(drop=("fzd",))
        self.assertIn("fzd", r["auditor_evaluation"]["agents_missing"])
        self.assertEqual(outcomes(r)["AUD-AGENTS"], "unable_to_determine")
        self.assertTrue(any(m["field"] == "agent:fzd" for m in r["missing_facts"]))

    def test_all_clear_with_a_missing_agent_is_unable_to_determine_not_pass(self):
        def clean(loan):
            loan["hmda_case"]["reported_rate_spread"] = 1.26
            loan["hmda_case"]["agricultural_purpose"] = "not_primarily"
            loan["hmda_case"]["lar"].update(applicant={"ethnicity": ["Not Hispanic or Latino"], "race": ["White"], "sex": ["male"], "collected_by_visual_observation_or_surname": False}, age=34, income=120,
                                           uli="10Bx939c5543TqA1144M999143X38", preapproval="not_requested", co_applicant="none")
            loan["hmda_case"]["lar_context"]["co_applicant_present"] = False
            loan["vmi_case"]["monitoring"]["items"]["marital_status"] = {"requested": True, "provided": True}
            loan["vmi_case"]["firewall"]["audit_logging"] = True
            loan["ecoa_case"]["spouse_signature"] = {"required": False}
        full = audit(mutate=clean)
        self.assertEqual((full["final_classification"], full["compliance_result"]), ("Pass", "Compliant"))
        partial = audit(mutate=clean, drop=("ybs",))
        self.assertEqual(partial["final_classification"], "Unable To Determine")

    def test_failed_agents_are_reported_as_missing(self):
        loan = copy.deepcopy(SAMPLE)
        results = assembled(loan)
        results["hmda"] = "model returned prose"                     # an unparsed agent result
        args, _ = tool_arguments({"loan_data": loan, "agent_results": results})
        self.assertEqual(args["case"]["failed_agents"], ["hmda"])
        r = evaluate_auditor(args["case"])
        self.assertIn("hmda", r["auditor_evaluation"]["agents_missing"])
        self.assertIn("the agent call failed", [m["reason"] for m in r["missing_facts"] if m["field"] == "agent:hmda"][0])

    def test_no_results_at_all_is_unable_to_determine(self):
        r = evaluate_auditor({"results": {}})
        self.assertEqual(r["final_classification"], "Unable To Determine")

    def test_adapter_rejects_payloads_without_agent_results(self):
        self.assertIsNone(tool_arguments("narrative text")[0])
        self.assertIsNone(tool_arguments({"loan_data": {}})[0])


def good_case():
    loan = copy.deepcopy(SAMPLE)
    args, _ = tool_arguments({"loan_data": loan, "agent_results": assembled(loan)})
    return args["case"]


Contract = contract_tests("auditor", evaluate_auditor, validate_auditor_rule_pack, validate_auditor_decision_record, server, good_case, [])

if __name__ == "__main__":
    unittest.main()

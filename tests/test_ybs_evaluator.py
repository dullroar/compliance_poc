import hashlib
import json
import unittest
from pathlib import Path

import yaml

from compliance_rules.tools import execute_tool, run_ollama_ybs_tool_loop, tool_definition
from compliance_rules.ybs import evaluate_ybs
from compliance_orchestrator import _guard_ybs_model_output, call_agent, prepare_ybs_evaluation


def person(subject_id="p1", **changes):
    value = {
        "id": subject_id,
        "type": "person",
        "is_agricultural_producer": True,
        "date_of_birth": "1991-06-02",
        "years_farming": 10,
        "annual_gross_ag_sales": 400000,
    }
    value.update(changes)
    return value


def case(subjects, evaluation_date="2026-06-01", target_ids=None):
    return {
        "case_id": "YBS-TEST",
        "evaluation_date": evaluation_date,
        "subjects": subjects,
        "determination_subject_ids": target_ids or [subject["id"] for subject in subjects],
        "evidence": [{"id": "app", "type": "application"}],
    }


class YBSEvaluatorTests(unittest.TestCase):
    def test_all_threshold_boundaries(self):
        result = evaluate_ybs(case([person()]))
        self.assertEqual(result["final_classification"], "Young + Beginning + Small")

        result = evaluate_ybs(case([person(date_of_birth="1991-06-01")]))
        self.assertEqual(result["subject_results"][0]["categories"]["young"], "not_eligible")

        result = evaluate_ybs(case([person(years_farming=11, annual_gross_ag_sales=400001)]))
        self.assertEqual(result["subject_results"][0]["categories"]["beginning"], "not_eligible")
        self.assertEqual(result["subject_results"][0]["categories"]["small"], "not_eligible")

    def test_effective_date_transition_and_unsupported_period(self):
        old = evaluate_ybs(case([person(annual_gross_ag_sales=300000)], "2024-06-01"))
        self.assertEqual(old["threshold_record"]["id"], "ybs-policy-2024")
        self.assertEqual(old["subject_results"][0]["categories"]["small"], "not_eligible")
        unsupported = evaluate_ybs(case([person()], "2023-12-31"))
        self.assertEqual(unsupported["final_classification"], "Unable To Determine")

    def test_missing_and_conflicting_facts_are_not_inferred(self):
        missing = evaluate_ybs(case([person(date_of_birth=None)]))
        self.assertEqual(missing["final_classification"], "Unable To Determine")
        conflicting = evaluate_ybs(case([person(conflicting_fields=["annual_gross_ag_sales"])]))
        self.assertEqual(conflicting["subject_results"][0]["categories"]["small"], "unable_to_determine")

    def test_full_entity_attribution_cases(self):
        eligible_entity = {"id": "llc", "type": "entity", "attribution": [{"subject_id": "p1", "role": "managing_member"}]}
        result = evaluate_ybs(case([person(), eligible_entity], target_ids=["llc"]))
        self.assertEqual(result["final_classification"], "Young + Beginning + Small")

        mixed_entity = {"id": "partnership", "type": "entity", "attribution": [{"subject_id": "p1", "role": "general_partner"}, {"subject_id": "p2", "role": "operator"}]}
        result = evaluate_ybs(case([person(), person("p2", years_farming=11), mixed_entity], target_ids=["partnership"]))
        self.assertEqual(result["subject_results"][-1]["categories"]["beginning"], "not_eligible")

        trust = {"id": "trust", "type": "entity", "attribution": [{"subject_id": "p1", "role": "trustee"}]}
        self.assertEqual(evaluate_ybs(case([person(), trust], target_ids=["trust"]))["final_classification"], "Young + Beginning + Small")

        successor = {"id": "successor", "type": "entity", "attribution": []}
        self.assertEqual(evaluate_ybs(case([successor], target_ids=["successor"]))["final_classification"], "Review Required")

        conflict = {"id": "reorg", "type": "entity", "attribution_conflict": True}
        self.assertEqual(evaluate_ybs(case([conflict], target_ids=["reorg"]))["final_classification"], "Review Required")

    def test_replay_tool_contract_and_llm_guard(self):
        input_case = case([person()])
        first = evaluate_ybs(input_case)
        second = execute_tool("evaluate_ybs", {"case": input_case})
        self.assertEqual(first["decision_id"], second["decision_id"])
        self.assertIn("input_schema", tool_definition("anthropic"))
        self.assertEqual(tool_definition("ollama")["function"]["name"], "evaluate_ybs")
        parsed, guard = _guard_ybs_model_output({"domain_determination": {"classification": "Not Eligible"}}, first)
        self.assertFalse(guard["passed"])
        self.assertEqual(parsed["domain_determination"]["classification"], "Young + Beginning + Small")

    def test_ollama_tool_loop_uses_the_same_evaluator(self):
        responses = iter([
            {"message": {"role": "assistant", "tool_calls": [{"function": {"name": "evaluate_ybs", "arguments": {"case": case([person()])}}}]}},
            {"message": {"role": "assistant", "content": "explained"}},
        ])
        result = run_ollama_ybs_tool_loop(lambda _: next(responses), {"model": "tool-model", "messages": []})
        self.assertEqual(result["message"]["content"], "explained")

    def test_runner_model_override_is_replaced(self):
        class FakeOllama:
            def create_message(self, **_):
                return json.dumps({"domain_determination": {"classification": "Not Eligible"}, "determination_status": {"result": "Non-Compliant"}})

        result = call_agent("ybs", {"ybs_case": case([person()])}, client=FakeOllama(), provider="ollama", model="fake")
        self.assertFalse(result["deterministic_guard"]["passed"])
        self.assertEqual(result["parsed"]["domain_determination"]["classification"], "Young + Beginning + Small")

    def test_pack_manifest_pins_policy_hash(self):
        root = Path(__file__).resolve().parents[1]
        manifest = yaml.safe_load((root / "rulepacks/ybs/ybs-v0.1/manifest.yaml").read_text(encoding="utf-8"))
        policy = root / "rulepacks/ybs/ybs-v0.1/entity_policy.yaml"
        actual = hashlib.sha256(policy.read_bytes()).hexdigest()
        policy_source = next(item for item in manifest["sources"] if item["id"] == "institution-ybs-pilot-policy-v0-1")
        self.assertEqual(policy_source["sha256"], actual)
        regulatory_source = next(item for item in manifest["sources"] if item["id"] == "ecfr-12-cfr-614-4165-2026-09-24")
        snapshot = root / regulatory_source["local_path"]
        self.assertEqual(regulatory_source["sha256"], hashlib.sha256(snapshot.read_bytes()).hexdigest())

    def test_legacy_runner_input_is_not_a_final_determination(self):
        result = prepare_ybs_evaluation({"ybs_information": {"young_farmer_criteria": {"age": 30}}})
        self.assertEqual(result["final_classification"], "Unable To Determine")


if __name__ == "__main__":
    unittest.main()

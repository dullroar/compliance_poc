import hashlib
import json
import unittest
from pathlib import Path

import yaml

from compliance_orchestrator import _guard_ybs_model_output, call_agent, prepare_ybs_evaluation
from compliance_rules.tools import (
    YBS_TOOL_PARAMETERS,
    execute_mcp_tool,
    execute_tool,
    mcp_tool_definition,
    run_anthropic_ybs_tool_loop,
    run_ollama_ybs_tool_loop,
    tool_definition,
)
from compliance_rules.ybs import (
    YBSValidationError,
    evaluate_ybs,
    validate_ybs_decision_record,
    validate_ybs_rule_pack,
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "ybs"


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


class _ToolUse:
    type = "tool_use"
    id = "call-1"
    name = "evaluate_ybs"

    def __init__(self, payload):
        self.input = payload


class _Response:
    def __init__(self, content):
        self.content = content


class _FakeMessages:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return next(self.responses)


class _FakeAnthropic:
    def __init__(self, responses):
        self.messages = _FakeMessages(responses)


class YBSFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scenarios = json.loads((FIXTURE_ROOT / "scenarios.json").read_text(encoding="utf-8"))
        cls.regressions = json.loads((FIXTURE_ROOT / "representative_loan_cases.json").read_text(encoding="utf-8"))

    def assert_fixture(self, fixture):
        result = evaluate_ybs(fixture["case"])
        expected = fixture["expected"]
        self.assertEqual(result["final_classification"], expected["classification"])
        if "threshold_id" in expected:
            actual = result["threshold_record"]["id"] if result["threshold_record"] else None
            self.assertEqual(actual, expected["threshold_id"])
        results = {item["subject_id"]: item for item in result["subject_results"]}
        for subject_id, categories in expected.get("categories", {}).items():
            for name, expected_outcome in categories.items():
                self.assertEqual(results[subject_id]["categories"][name], expected_outcome)
        missing_fields = {fact["field"] for fact in result["missing_facts"]}
        self.assertTrue(set(expected.get("missing_fields", [])).issubset(missing_fields))
        validate_ybs_decision_record(result)

    def test_every_threshold_boundary_date_transition_missing_conflict_and_historical_fixture(self):
        for fixture in self.scenarios:
            with self.subTest(fixture=fixture["id"]):
                self.assert_fixture(fixture)

    def test_representative_loan_regression_fixtures(self):
        for fixture in self.regressions:
            with self.subTest(fixture=fixture["id"]):
                self.assert_fixture(fixture)


class YBSContractTests(unittest.TestCase):
    def test_rule_pack_sources_and_contracts_validate(self):
        validate_ybs_rule_pack()
        root = Path(__file__).resolve().parents[1]
        manifest = yaml.safe_load((root / "rulepacks/ybs/ybs-v0.1/manifest.yaml").read_text(encoding="utf-8"))
        for source in manifest["sources"]:
            with self.subTest(source=source["id"]):
                self.assertEqual(hashlib.sha256((root / source["local_path"]).read_bytes()).hexdigest(), source["sha256"])

    def test_schema_rejects_malformed_canonical_input_and_decision_output(self):
        invalid_input = case([person()])
        invalid_input["subjects"][0]["unexpected"] = "not in contract"
        with self.assertRaisesRegex(YBSValidationError, "Additional properties"):
            evaluate_ybs(invalid_input)
        valid = evaluate_ybs(case([person()]))
        del valid["rule_pack"]
        with self.assertRaisesRegex(YBSValidationError, "rule_pack"):
            validate_ybs_decision_record(valid)

    def test_all_provider_and_mcp_tools_share_one_contract_and_decision(self):
        input_case = case([person()])
        expected = evaluate_ybs(input_case)
        anthropic = tool_definition("anthropic")
        ollama = tool_definition("ollama")
        mcp = mcp_tool_definition()
        self.assertEqual(anthropic["input_schema"], YBS_TOOL_PARAMETERS)
        self.assertEqual(ollama["function"]["parameters"], YBS_TOOL_PARAMETERS)
        self.assertEqual(mcp["inputSchema"], YBS_TOOL_PARAMETERS)
        self.assertEqual(anthropic["name"], ollama["function"]["name"])
        self.assertEqual(anthropic["name"], mcp["name"])
        for runner in (execute_tool, execute_mcp_tool):
            with self.subTest(runner=runner.__name__):
                self.assertEqual(runner("evaluate_ybs", {"case": input_case})["decision_id"], expected["decision_id"])

    def test_replay_is_identical_across_repeated_native_and_mcp_execution(self):
        input_case = case([person()])
        decisions = [
            evaluate_ybs(input_case),
            evaluate_ybs(json.loads(json.dumps(input_case))),
            execute_tool("evaluate_ybs", {"case": input_case}),
            execute_mcp_tool("evaluate_ybs", {"case": input_case}),
        ]
        self.assertEqual({item["decision_id"] for item in decisions}, {decisions[0]["decision_id"]})
        self.assertEqual({item["final_classification"] for item in decisions}, {"Young + Beginning + Small"})

    def test_anthropic_and_ollama_tool_loops_use_the_same_evaluator(self):
        input_case = case([person()])
        expected = evaluate_ybs(input_case)["decision_id"]
        anthropic = _FakeAnthropic([_Response([_ToolUse({"case": input_case})]), _Response([])])
        response = run_anthropic_ybs_tool_loop(
            anthropic, model="fake", system="system", messages=[], max_tokens=1,
        )
        self.assertEqual(response.content, [])
        tool_result = anthropic.messages.requests[1]["messages"][-1]["content"][0]
        self.assertEqual(json.loads(tool_result["content"])["decision_id"], expected)

        responses = iter([
            {"message": {"role": "assistant", "tool_calls": [{"function": {"name": "evaluate_ybs", "arguments": {"case": input_case}}}]}},
            {"message": {"role": "assistant", "content": "explained"}},
        ])
        result = run_ollama_ybs_tool_loop(lambda _: next(responses), {"model": "tool-model", "messages": []})
        self.assertEqual(result["message"]["content"], "explained")

    def test_runner_guard_preserves_authoritative_decision(self):
        class FakeOllama:
            def create_message(self, **_):
                return json.dumps({"domain_determination": {"classification": "Not Eligible"}, "determination_status": {"result": "Non-Compliant"}})

        result = call_agent("ybs", {"ybs_case": case([person()])}, client=FakeOllama(), provider="ollama", model="fake")
        self.assertFalse(result["deterministic_guard"]["passed"])
        self.assertEqual(result["parsed"]["domain_determination"]["classification"], "Young + Beginning + Small")
        parsed, guard = _guard_ybs_model_output({"domain_determination": {"classification": "Not Eligible"}}, result["deterministic_evaluation"])
        self.assertFalse(guard["passed"])
        self.assertEqual(parsed["domain_determination"]["classification"], "Young + Beginning + Small")

    def test_legacy_input_is_not_a_final_determination(self):
        result = prepare_ybs_evaluation({"ybs_information": {"young_farmer_criteria": {"age": 30}}})
        self.assertEqual(result["final_classification"], "Unable To Determine")


if __name__ == "__main__":
    unittest.main()

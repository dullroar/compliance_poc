import asyncio
import hashlib
import json
import unittest
from pathlib import Path

import yaml

from compliance_common.mcp_client import call_tool, list_tool_specs, stdio_target
from compliance_common.tools import native_definition, run_anthropic_tool_loop, run_ollama_tool_loop, seed_anthropic, seed_ollama
from compliance_mcp.ybs import (
    YBSValidationError,
    evaluate_ybs,
    validate_ybs_decision_record,
    validate_ybs_rule_pack,
)
from compliance_mcp.ybs.server import server as ybs_server


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
    name = "ybs_evaluate"

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
        manifest = yaml.safe_load((root / "compliance_mcp/ybs/pack/manifest.yaml").read_text(encoding="utf-8"))
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
        spec = asyncio.run(list_tool_specs(ybs_server))[0]
        self.assertEqual(spec["name"], "ybs_evaluate")
        self.assertEqual(native_definition(spec, "anthropic")["input_schema"], spec["inputSchema"])
        self.assertEqual(native_definition(spec, "ollama")["function"]["parameters"], spec["inputSchema"])
        for target in (ybs_server, stdio_target("ybs")):
            with self.subTest(target=type(target).__name__):
                result = asyncio.run(call_tool(target, "ybs_evaluate", {"case": input_case}))
                self.assertEqual(result["decision_id"], expected["decision_id"])

    def test_replay_is_identical_across_repeated_direct_and_mcp_execution(self):
        input_case = case([person()])
        decisions = [
            evaluate_ybs(input_case),
            evaluate_ybs(json.loads(json.dumps(input_case))),
            asyncio.run(call_tool(ybs_server, "ybs_evaluate", {"case": input_case})),
        ]
        self.assertEqual({item["decision_id"] for item in decisions}, {decisions[0]["decision_id"]})
        self.assertEqual({item["final_classification"] for item in decisions}, {"Young + Beginning + Small"})

    def test_anthropic_and_ollama_tool_loops_use_the_same_evaluator(self):
        input_case = case([person()])
        expected = evaluate_ybs(input_case)["decision_id"]
        spec = asyncio.run(list_tool_specs(ybs_server))[0]
        execute = lambda name, args: asyncio.run(call_tool(ybs_server, name, args))  # noqa: E731
        calls = []
        anthropic = _FakeAnthropic([_Response([_ToolUse({"case": input_case})]), _Response([])])
        response = run_anthropic_tool_loop(
            anthropic, spec, execute, model="fake", system="system", messages=[], max_tokens=1, calls_made=calls,
        )
        self.assertEqual(response.content, [])
        tool_result = anthropic.messages.requests[1]["messages"][-1]["content"][0]
        self.assertEqual(json.loads(tool_result["content"])["decision_id"], expected)
        self.assertEqual(calls[0]["result"]["decision_id"], expected)

        responses = iter([
            {"message": {"role": "assistant", "tool_calls": [{"function": {"name": "ybs_evaluate", "arguments": {"case": input_case}}}]}},
            {"message": {"role": "assistant", "content": "explained"}},
        ])
        result = run_ollama_tool_loop(lambda _: next(responses), spec, execute, {"model": "tool-model", "messages": []})
        self.assertEqual(result["message"]["content"], "explained")


class ToolEnforcementFormatTests(unittest.TestCase):
    SPEC = {"name": "ybs_evaluate", "description": "d", "inputSchema": {"type": "object"}}

    def test_anthropic_first_request_can_force_the_tool_and_later_ones_cannot(self):
        client = _FakeAnthropic([_Response([_ToolUse({"case": {}})]), _Response([])])
        execute = lambda name, args: {"decision_id": "x" * 64}  # noqa: E731
        run_anthropic_tool_loop(client, self.SPEC, execute, model="m", system="s", messages=[], max_tokens=1, force_first=True)
        first, second = client.messages.requests
        self.assertEqual((first["tool_choice"]["type"], first["tool_choice"]["name"]), ("tool", "ybs_evaluate"))
        self.assertEqual(second["tool_choice"]["type"], "auto")
        free = _FakeAnthropic([_Response([])])
        run_anthropic_tool_loop(free, self.SPEC, execute, model="m", system="s", messages=[], max_tokens=1)
        self.assertEqual(free.messages.requests[0]["tool_choice"]["type"], "auto")

    def test_seed_formats_are_the_providers_native_tool_exchange(self):
        anth = seed_anthropic(self.SPEC, {"case": {"a": 1}}, {"decision_id": "d"})
        self.assertEqual((anth[0]["role"], anth[0]["content"][0]["type"], anth[0]["content"][0]["input"]), ("assistant", "tool_use", {"case": {"a": 1}}))
        self.assertEqual((anth[1]["role"], anth[1]["content"][0]["type"], anth[1]["content"][0]["tool_use_id"]), ("user", "tool_result", anth[0]["content"][0]["id"]))
        oll = seed_ollama(self.SPEC, {"case": {"a": 1}}, {"decision_id": "d"})
        self.assertEqual(oll[0]["tool_calls"][0]["function"], {"name": "ybs_evaluate", "arguments": {"case": {"a": 1}}})
        self.assertEqual((oll[1]["role"], oll[1]["tool_name"], json.loads(oll[1]["content"])), ("tool", "ybs_evaluate", {"decision_id": "d"}))

    def test_a_seeded_ollama_conversation_goes_straight_to_the_final_answer(self):
        seen = []
        def request(payload):
            seen.append(payload["messages"])
            return {"message": {"role": "assistant", "content": "narrative"}}
        payload = {"model": "m", "messages": [{"role": "user", "content": "u"}, *seed_ollama(self.SPEC, {}, {"decision_id": "d"})]}
        out = run_ollama_tool_loop(request, self.SPEC, lambda n, a: {}, payload)
        self.assertEqual((out["message"]["content"], len(seen)), ("narrative", 1))
        self.assertEqual([m["role"] for m in seen[0]], ["user", "assistant", "tool"])


if __name__ == "__main__":
    unittest.main()

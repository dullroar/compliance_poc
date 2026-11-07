"""Offline contract tests for the OpenAI Responses runtime adapter."""
from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from agents.backends import Backend, MAX_TOKENS
from agents.runner import run_agent
from compliance_common.narrative_schema import NARRATIVE_SCHEMA
from compliance_mcp.ybs import evaluate_ybs


GOOD_TEXT = ("The deterministic review classified this case as Young + Beginning + Small with the result Compliant. "
             "Every rule in the decision record was satisfied or did not apply, and the record lists no missing facts.")
NARRATIVE = {"narrative": {"reasoning": GOOD_TEXT, "examiner_narrative": GOOD_TEXT, "data_gaps_followups": []}}


def person(**changes):
    value = {
        "id": "p1", "type": "person", "is_agricultural_producer": True,
        "date_of_birth": "1991-06-02", "years_farming": 10, "annual_gross_ag_sales": 400000,
    }
    value.update(changes)
    return value


def ybs_case(subjects):
    return {
        "case_id": "YBS-OPENAI-TEST", "evaluation_date": "2026-06-01", "subjects": subjects,
        "determination_subject_ids": [subject["id"] for subject in subjects],
        "evidence": [{"id": "app", "type": "application"}],
    }


class _FakeResponses:
    def __init__(self, responses=(), error=None):
        self.responses = iter(responses)
        self.error = error
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        if self.error is not None:
            raise self.error
        return next(self.responses)


class _FakeOpenAI:
    def __init__(self, responses=(), error=None):
        self.responses = _FakeResponses(responses, error)


def response(text="", output=()):
    return SimpleNamespace(output_text=text, output=list(output))


def function_call(arguments, *, name="ybs_evaluate", call_id="call-1"):
    return SimpleNamespace(type="function_call", name=name, arguments=arguments, call_id=call_id)


YBS_SPEC = {"name": "ybs_evaluate", "description": "Evaluate YBS eligibility.", "inputSchema": {"type": "object"}}


async def _fake_list_tool_specs(_target):
    return [YBS_SPEC]


async def _fake_call_tool(_target, name, arguments):
    if name != "ybs_evaluate":
        raise ValueError(f"unexpected tool {name}")
    return evaluate_ybs(arguments["case"])


class OpenAIBackendTests(unittest.TestCase):
    def setUp(self):
        self._api_key = os.environ.pop("OPENAI_API_KEY", None)

    def tearDown(self):
        if self._api_key is not None:
            os.environ["OPENAI_API_KEY"] = self._api_key

    def test_openai_requires_an_explicit_model(self):
        with patch.dict(os.environ, {"COMPLIANCE_MODEL": ""}, clear=False):
            with self.assertRaisesRegex(ValueError, "explicit model"):
                Backend("openai", client=_FakeOpenAI())

    def test_chat_accepts_explicit_openai_model_without_model_environment_variable(self):
        from orchestrator.cli import repl

        constructed = []

        class SDK:
            def __init__(self, **kwargs):
                constructed.append(kwargs)

        with patch("agents.backends.OpenAI", SDK), patch.dict(
            os.environ, {"OPENAI_API_KEY": "test-key", "COMPLIANCE_MODEL": ""}, clear=False,
        ), patch("builtins.input", return_value="exit"), patch("builtins.print"):
            repl("ybs", provider="openai", model="approved-model")
        self.assertEqual(len(constructed), 1)

    def test_client_requires_a_key_and_uses_bounded_settings(self):
        constructed = []

        class SDK:
            def __init__(self, **kwargs):
                constructed.append(kwargs)

        with patch("agents.backends.OpenAI", SDK), patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY not set"):
                Backend("openai", model="approved-model")
        with patch("agents.backends.OpenAI", SDK), patch.dict(
            os.environ, {"OPENAI_API_KEY": "test-key", "OPENAI_TIMEOUT": "17", "OPENAI_MAX_RETRIES": "3"}, clear=False,
        ):
            Backend("openai", model="approved-model")
        self.assertEqual(constructed, [{"api_key": "test-key", "timeout": 17.0, "max_retries": 3}])

    def test_ordinary_completion_uses_stateless_json_mode_without_a_key(self):
        client = _FakeOpenAI([response('{"answer": "ok"}')])
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            text = Backend("openai", model="approved-model", client=client).complete("system", [{"role": "user", "content": "hello"}])
        self.assertEqual(text, '{"answer": "ok"}')
        request = client.responses.requests[0]
        self.assertEqual(request["model"], "approved-model")
        self.assertEqual(request["instructions"], "system")
        self.assertEqual(request["input"], [{"role": "user", "content": "hello"}])
        self.assertEqual((request["max_output_tokens"], request["store"]), (MAX_TOKENS, False))
        self.assertEqual(request["text"], {"format": {"type": "json_object"}})

    def test_schema_constrained_completion_and_seeded_continuation(self):
        spec = {"name": "ybs_evaluate", "description": "evaluate", "inputSchema": {"type": "object"}}
        client = _FakeOpenAI([response(json.dumps(NARRATIVE)), response(json.dumps(NARRATIVE))])
        backend = Backend("openai", model="approved-model", client=client)
        backend.complete("system", [], schema=NARRATIVE_SCHEMA)
        backend.complete_seeded("system", [{"role": "user", "content": "case"}], spec, lambda *_: {}, [],
                                {"case": {"id": "canonical"}}, {"decision_id": "d"}, schema=NARRATIVE_SCHEMA)
        ordinary, seeded = client.responses.requests
        expected_format = {"format": {"type": "json_schema", "name": "compliance_narrative", "strict": True, "schema": NARRATIVE_SCHEMA}}
        self.assertEqual(ordinary["text"], expected_format)
        self.assertEqual(seeded["text"], expected_format)
        self.assertEqual(seeded["input"][1]["type"], "function_call")
        self.assertEqual(json.loads(seeded["input"][1]["arguments"]), {"case": {"id": "canonical"}})
        self.assertEqual((seeded["input"][2]["type"], json.loads(seeded["input"][2]["output"])),
                         ("function_call_output", {"decision_id": "d"}))
        self.assertEqual((seeded["tool_choice"], seeded["parallel_tool_calls"], seeded["store"]), ("none", False, False))
        self.assertEqual([tool["name"] for tool in seeded["tools"]], ["ybs_evaluate"])

    def test_model_tool_mode_requests_structured_narration(self):
        client = _FakeOpenAI([
            response(output=[function_call(json.dumps({"case": {}}))]),
            response(json.dumps(NARRATIVE)),
        ])
        backend = Backend("openai", model="approved-model", client=client)
        output = backend.complete_with_tool("system", [], YBS_SPEC, lambda *_: {"decision_id": "d"}, [])
        self.assertEqual(json.loads(output), NARRATIVE)
        for request in client.responses.requests:
            self.assertEqual(request["text"], {"format": {"type": "json_schema", "name": "compliance_narrative",
                                                           "strict": True, "schema": NARRATIVE_SCHEMA}})

    def test_model_tool_mode_forces_one_evaluator_and_runner_pins_canonical_facts(self):
        canonical = ybs_case([person()])
        payload = {"case_information": {"case_id": "YBS-OPENAI-TEST"}, "ybs_case": canonical}
        tampered = {"case": ybs_case([person(date_of_birth="1960-01-01", years_farming=40, annual_gross_ag_sales=9_000_000)])}
        client = _FakeOpenAI([
            response(output=[function_call(json.dumps(tampered))]),
            response(json.dumps(NARRATIVE)),
        ])
        with patch("agents.runner.list_tool_specs", _fake_list_tool_specs), patch("agents.runner.call_tool", _fake_call_tool):
            result = run_agent("ybs", payload, Backend("openai", model="approved-model", client=client), tool_target=object())
        self.assertEqual(result["decision"]["decision_id"], evaluate_ybs(canonical)["decision_id"])
        self.assertEqual(result["decision"]["final_classification"], "Young + Beginning + Small")
        self.assertEqual(result["tool_calls"], [{"name": "ybs_evaluate", "by": "model"}])
        first, second = client.responses.requests
        self.assertEqual(first["tool_choice"], {"type": "function", "name": "ybs_evaluate"})
        self.assertFalse(first["parallel_tool_calls"])
        self.assertEqual(second["tool_choice"], "auto")
        self.assertEqual(json.loads(second["input"][-1]["output"])["decision_id"], result["decision"]["decision_id"])

    def test_openai_narrative_still_retries_then_uses_deterministic_fallback(self):
        canonical = ybs_case([person()])
        payload = {"case_information": {"case_id": "YBS-OPENAI-TEST"}, "ybs_case": canonical}
        client = _FakeOpenAI([
            response(output=[function_call(json.dumps({"case": canonical}))]),
            response("not json"),
            response("still not json"),
        ])
        with patch("agents.runner.list_tool_specs", _fake_list_tool_specs), patch("agents.runner.call_tool", _fake_call_tool):
            result = run_agent("ybs", payload, Backend("openai", model="approved-model", client=client), tool_target=object())
        self.assertEqual(result["narrative_guard"]["source"], "deterministic_fallback")
        self.assertEqual(result["narrative_guard"]["attempts"], 2)
        self.assertEqual(result["parsed"]["domain_determination"]["classification"], "Young + Beginning + Small")
        self.assertIn("rejected twice", result["parsed"]["narrative_warnings"][0])
        self.assertEqual(client.responses.requests[2]["text"]["format"]["type"], "json_schema")

    def test_ungrounded_openai_narrative_is_retried_then_replaced(self):
        canonical = ybs_case([person()])
        payload = {"case_information": {"case_id": "YBS-OPENAI-TEST"}, "ybs_case": canonical}
        invented = {"narrative": dict(NARRATIVE["narrative"], reasoning=GOOD_TEXT + " The unsupported amount is 987654321.")}
        raw = json.dumps(invented)
        client = _FakeOpenAI([
            response(output=[function_call(json.dumps({"case": canonical}))]),
            response(raw),
            response(raw),
        ])
        with patch("agents.runner.list_tool_specs", _fake_list_tool_specs), patch("agents.runner.call_tool", _fake_call_tool):
            result = run_agent("ybs", payload, Backend("openai", model="approved-model", client=client), tool_target=object())
        self.assertEqual(result["decision"]["decision_id"], evaluate_ybs(canonical)["decision_id"])
        self.assertEqual(result["narrative_guard"]["source"], "deterministic_fallback")
        self.assertEqual(result["narrative_guard"]["attempts"], 2)
        self.assertIn("987654321", client.responses.requests[2]["input"][-1]["content"])
        self.assertEqual(result["raw_text"], raw)
        self.assertNotIn("987654321", json.dumps(result["parsed"]["compliance_determination_summary"]))
        self.assertIn("987654321", json.dumps(result["parsed"]["narrative_warnings"]))

    def test_refusal_or_malformed_output_is_observable(self):
        backend = Backend("openai", model="approved-model", client=_FakeOpenAI([response()]))
        with self.assertRaisesRegex(RuntimeError, "no output text"):
            backend.complete("system", [])
        spec = {"name": "ybs_evaluate", "description": "evaluate", "inputSchema": {"type": "object"}}
        malformed = Backend("openai", model="approved-model", client=_FakeOpenAI([response(output=[function_call("not-json")])]))
        with self.assertRaisesRegex(RuntimeError, "malformed function arguments"):
            malformed.complete_with_tool("system", [], spec, lambda *_: {}, [])

    def test_timeout_rate_limit_and_transport_errors_propagate(self):
        class Timeout(Exception):
            pass

        class RateLimit(Exception):
            pass

        for error in (Timeout("timed out"), RateLimit("rate limited"), RuntimeError("transport failed")):
            with self.subTest(error=type(error).__name__):
                backend = Backend("openai", model="approved-model", client=_FakeOpenAI(error=error))
                with self.assertRaises(type(error)):
                    backend.complete("system", [])


if __name__ == "__main__":
    unittest.main()

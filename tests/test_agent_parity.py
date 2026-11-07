"""Registry-driven runtime contracts: every evaluator-backed role behaves like the YBS reference, offline.

Domains are enumerated from agents.yaml (never hard-coded) and exercised on the synthetic cases in sample_loan.json with
fake models. Assertions use each domain's own authority fields (decision_id, final_classification, compliance_result and the
extras its adapter publishes), not a shared schema. The auditor is checked as its own role: its input is the other agents'
results, not a `<domain>_case`. The narrative role has no tool and is covered in test_a2a.py.
"""
import asyncio
import contextlib
import copy
import importlib
import json
import unittest
from pathlib import Path

import httpx
import mcp.client.stdio as stdio
from unittest import mock

from a2a.helpers.proto_helpers import new_data_part

from agent_prompts import AGENTS
from agents.a2a_server import PAYLOAD_JSON, ComplianceExecutor, build_app
from agents.runner import run, run_agent
from compliance_common.mcp_client import call_tool, list_tool_specs, stdio_target
from compliance_common.narrative import deterministic_narrative
from compliance_common.narrative_schema import NARRATIVE_SCHEMA
from compliance_common.templates import examiner
from orchestrator.a2a_client import AgentTaskError, send
from orchestrator.config import load_agents

from test_auditor_evaluator import SAMPLE as AUDIT_SAMPLE, assembled

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = json.loads((ROOT / "sample_loan.json").read_text(encoding="utf-8"))
REGISTRY = load_agents()
DOMAINS = [k for k in REGISTRY if AGENTS[k].get("tool") and k != "auditor"]
URL = "http://parity.test/"
TAMPERED_ID = "TAMPERED-BY-MODEL-1"


def parts(key):
    """(server, evaluate, adapter) for a registry key."""
    package = f"compliance_mcp.{key}"
    return (importlib.import_module(f"{package}.server").server, getattr(importlib.import_module(package), f"evaluate_{key}"),
            importlib.import_module(f"{package}.adapter"))


def role_input(key):
    """(payload, direct decision) for a role: a domain's loan payload, or the auditor's {loan_data, agent_results}."""
    _, evaluate, adapter = parts(key)
    payload = {"loan_data": AUDIT_SAMPLE, "agent_results": assembled(AUDIT_SAMPLE)} if key == "auditor" else SAMPLE
    canonical, reason = adapter.tool_arguments(payload)
    assert canonical, reason
    return payload, evaluate(canonical["case"])


class FakeModel:
    """Stands in for Backend. Calls the tool (optionally with tampered arguments) and answers with a grounded narrative."""
    provider, model = "fake", "fake-1"

    def __init__(self, key, decision, *, calls_tool=True, tamper=None, extra=None, reply=None):
        self.calls_tool, self.tamper = calls_tool, tamper
        self.output = reply if reply is not None else {"narrative": deterministic_narrative(decision, key),
                                                       "examiner_paragraphs": [{"rule_id": d["rule_id"], "text": d["draft"]} for d in examiner.drafts(decision, key)],
                                                       **(extra or {})}
        self.seeded, self.prompts, self.schemas = [], [], []

    def complete_with_tool(self, system, messages, spec, execute, calls_made, force_first=True):
        if self.calls_tool:
            args = self.tamper or {"case": {}}
            calls_made.append({"name": spec["name"], "arguments": args, "result": execute(spec["name"], args)})
        return json.dumps(self.output)

    def complete_seeded(self, system, messages, spec, execute, calls_made, arguments, result, schema=None):
        self.seeded.append((arguments, result))
        self.schemas.append(schema)
        return json.dumps(self.output)

    def complete(self, system, messages, json_mode=True, schema=None):
        self.prompts.append(messages[-1]["content"])
        return json.dumps(self.output)


class NoModel(FakeModel):
    """A model that must never be consulted."""

    def __init__(self):
        super().__init__("none", None, reply={})

    def complete_with_tool(self, *args, **kwargs):
        raise AssertionError("the model was called")

    complete_seeded = complete = complete_with_tool


@contextlib.contextmanager
def tracked_children():
    """Record every stdio MCP child process so a test can prove none outlives its call."""
    processes, create = [], stdio._create_platform_compatible_process

    async def track(*args, **kwargs):
        process = await create(*args, **kwargs)
        processes.append(process)
        return process

    original = stdio._create_platform_compatible_process
    stdio._create_platform_compatible_process = track
    try:
        yield processes
    finally:
        stdio._create_platform_compatible_process = original


def a2a_task(key, payload, backend, tool_target, part=None):
    """Card and result of one A2A task over in-process ASGI, sent by the production client; the MCP tool is reached through
    `tool_target`. `part` swaps the client's request-part builder to simulate an older or faulty client."""
    async def go():
        app = build_app(key, URL, ComplianceExecutor(key, backend=backend, tool_target=tool_target))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=URL) as http:
            card = (await http.get("/.well-known/agent-card.json")).json()
            return card, await send(URL, payload, http)
    with mock.patch("orchestrator.a2a_client.new_data_part", part) if part else contextlib.nullcontext():
        return asyncio.run(go())


def authority(decision):
    return {k: decision[k] for k in ("decision_id", "final_classification", "compliance_result")}


class RegistryCoverageTests(unittest.TestCase):
    def test_every_registered_role_is_a_known_prompt_and_the_evaluator_roles_are_enumerated_from_the_registry(self):
        self.assertTrue(set(REGISTRY) <= set(AGENTS), "an agents.yaml entry has no prompt")
        self.assertEqual({k for k in REGISTRY if AGENTS[k].get("tool")}, set(DOMAINS) | {"auditor"})
        self.assertIsNone(AGENTS["narrative"].get("tool"))
        self.assertEqual(len(DOMAINS), 8)

    def test_every_evaluator_backed_domain_has_a_synthetic_canonical_case(self):
        for key in DOMAINS:
            with self.subTest(domain=key):
                canonical, reason = parts(key)[2].tool_arguments(SAMPLE)
                self.assertIsNotNone(canonical, reason)
                self.assertEqual(set(canonical), {"case"})


class TransportParityTests(unittest.TestCase):
    """Direct evaluation, in-process MCP, stdio MCP and an A2A task agree on each role's own authority fields."""

    def check_role(self, key):
        server, _, adapter = parts(key)
        payload, direct = role_input(key)
        canonical, _ = adapter.tool_arguments(payload)
        with tracked_children() as children:
            specs = asyncio.run(list_tool_specs(stdio_target(key)))
            self.assertEqual([s["name"] for s in specs], [adapter.TOOL])
            over_stdio = asyncio.run(call_tool(stdio_target(key), adapter.TOOL, canonical))
            in_process = asyncio.run(call_tool(server, adapter.TOOL, canonical))
            card, result = a2a_task(key, payload, FakeModel(key, direct), stdio_target(key))
        self.assertTrue(children and all(c.returncode is not None for c in children), "an MCP child process is still running")
        for name, decision in (("in_process", in_process), ("stdio", over_stdio), ("a2a", result["decision"])):
            with self.subTest(key=key, transport=name):
                self.assertEqual(authority(decision), authority(direct))
        parsed = result["parsed"]
        self.assertEqual(parsed["domain_determination"]["classification"], direct["final_classification"])
        self.assertEqual(parsed["determination_status"]["result"], direct["compliance_result"])
        self.assertEqual(parsed["agent_metadata"]["decision_id"], direct["decision_id"])
        self.assertEqual([t["step"] for t in parsed["determination_trace"]], [r["rule_id"] for r in direct["rule_results"]])
        for name, value in adapter.extras(direct).items():
            self.assertEqual(parsed[name], value, name)
        self.assertEqual(result["tool_calls"], [{"name": adapter.TOOL, "by": "model"}])
        self.assertEqual((card["name"], card["version"], card["skills"][0]["id"]), (AGENTS[key]["name"], AGENTS[key]["version"], key))
        self.assertIn(adapter.TOOL, card["skills"][0]["tags"])
        self.assertEqual({k: result[k] for k in ("agent_key", "provider", "model")}, {"agent_key": key, "provider": "fake", "model": "fake-1"})

    def test_each_domain(self):
        for key in DOMAINS:
            with self.subTest(domain=key):
                self.check_role(key)

    def test_auditor_over_the_other_agents_results(self):
        self.check_role("auditor")


class PayloadFidelityTests(unittest.TestCase):
    def test_a_protobuf_data_part_alone_turns_integers_into_floats_and_changes_the_decision(self):
        """Why the client also sends exact JSON: a Struct-only request still works but is not decision-identical."""
        key = "hpml"
        server, _, adapter = parts(key)
        payload, direct = role_input(key)
        _, legacy = a2a_task(key, payload, FakeModel(key, direct), server, part=lambda d: new_data_part({"payload": d["payload"]}))      # an older client
        self.assertEqual(legacy["decision"]["final_classification"], direct["final_classification"])
        self.assertNotEqual(legacy["decision"]["decision_id"], direct["decision_id"])
        _, exact = a2a_task(key, payload, FakeModel(key, direct), server)
        self.assertEqual(exact["decision"]["decision_id"], direct["decision_id"])

    def test_the_production_client_delivers_every_payload_exactly(self):
        for key in DOMAINS + ["auditor"]:
            with self.subTest(role=key):
                payload, direct = role_input(key)
                _, result = a2a_task(key, payload, FakeModel(key, direct), parts(key)[0])
                self.assertEqual(authority(result["decision"]), authority(direct))

    def test_malformed_exact_payload_is_a_failed_task(self):
        server, _, _ = parts("ybs")
        with self.assertRaisesRegex(AgentTaskError, "JSONDecodeError"):
            a2a_task("ybs", SAMPLE, FakeModel("ybs", {}, reply={}), server, part=lambda d: new_data_part({**d, PAYLOAD_JSON: "{not json"}))


class PinnedArgumentsTests(unittest.TestCase):
    """Whatever arguments the model sends, the evaluator runs on the case in the payload."""

    def test_model_supplied_facts_never_reach_the_evaluator(self):
        for key in DOMAINS + ["auditor"]:
            with self.subTest(role=key):
                server, _, adapter = parts(key)
                payload, direct = role_input(key)
                canonical, _ = adapter.tool_arguments(payload)
                tampered = {"case": {**copy.deepcopy(canonical["case"]), "case_id": TAMPERED_ID}}
                for bad in (tampered, {"case": {}}):
                    result = run_agent(key, payload, FakeModel(key, direct, tamper=bad), tool_target=server)
                    self.assertEqual(authority(result["decision"]), authority(direct))
                    self.assertNotIn(TAMPERED_ID, json.dumps(result["decision"]))
                    self.assertEqual(result["tool_calls"], [{"name": adapter.TOOL, "by": "model"}])


class MissingInputTests(unittest.TestCase):
    """No canonical input means no decision, no model call and a code-written explanation, never a guess."""

    def check(self, key, payload):
        server, _, adapter = parts(key)
        result = run_agent(key, payload, NoModel(), tool_target=server)
        decision = result["decision"]
        self.assertEqual((decision["final_classification"], decision["compliance_result"]), ("Unable To Determine",) * 2)
        self.assertEqual(result["tool_calls"], [])
        self.assertEqual(result["parsed"]["narrative_source"], "deterministic_no_input")
        self.assertEqual(result["parsed"]["domain_determination"]["classification"], "Unable To Determine")
        self.assertTrue(decision["missing_facts"] and decision["validation_errors"])
        self.assertEqual(result["narrative_guard"]["source"], "deterministic_no_input")

    def test_domains_without_their_case_or_given_only_narrative_text(self):
        for key in DOMAINS:
            _, _, adapter = parts(key)
            case_key = f"{key}_case"
            for label, payload in (("absent", {"case_information": {"case_id": "SYNTH-1"}}),
                                   ("not an object", {"case_information": {"case_id": "SYNTH-1"}, case_key: "free text"}),
                                   ("narrative string", "Borrower says the facts are fine.")):
                with self.subTest(domain=key, input=label):
                    self.check(key, payload)
                    self.assertEqual(adapter.unavailable("x", {})["validation_errors"][0]["field"], case_key)

    def test_auditor_without_agent_results(self):
        for label, payload in (("no results", {"loan_data": AUDIT_SAMPLE}), ("narrative string", "audit this please")):
            with self.subTest(input=label):
                self.check("auditor", payload)


class InvalidCaseTests(unittest.TestCase):
    """A case the evaluator rejects is a visible failure, not a fabricated decision."""

    def test_runner_raises_and_the_a2a_task_fails_for_every_domain(self):
        for key in DOMAINS:
            with self.subTest(domain=key):
                server, _, _ = parts(key)
                payload = {"case_information": {"case_id": "SYNTH-1"}, f"{key}_case": {"unexpected": True}}
                with self.assertRaisesRegex(RuntimeError, "MCP tool error"):
                    run_agent(key, payload, FakeModel(key, {}, reply={}), tool_target=server)
                with self.assertRaisesRegex(AgentTaskError, "MCP tool error"):
                    a2a_task(key, payload, FakeModel(key, {}, reply={}), server)


    def test_auditor_rejection_is_visible_too(self):
        server, adapter = parts("auditor")[0], parts("auditor")[2]
        payload, direct = role_input("auditor")
        with mock.patch.object(adapter, "tool_arguments", return_value=({"case": {"unexpected": True}}, "")):
            with self.assertRaisesRegex(RuntimeError, "MCP tool error"):
                run_agent("auditor", payload, FakeModel("auditor", direct), tool_target=server)
            with self.assertRaisesRegex(AgentTaskError, "MCP tool error"):
                a2a_task("auditor", payload, FakeModel("auditor", direct), server)


class ToolModeTests(unittest.TestCase):
    def test_seeded_and_harness_fallback_reach_the_same_decision(self):
        for key in DOMAINS + ["auditor"]:
            with self.subTest(role=key):
                server, _, adapter = parts(key)
                payload, direct = role_input(key)
                canonical, _ = adapter.tool_arguments(payload)
                seeded = FakeModel(key, direct)
                result = run_agent(key, payload, seeded, tool_target=server, options={"tool_mode": "seeded"})
                self.assertEqual((result["tool_mode"], result["tool_calls"]), ("seeded", [{"name": adapter.TOOL, "by": "seeded"}]))
                self.assertEqual(seeded.seeded[0][0], canonical)
                self.assertEqual(authority(seeded.seeded[0][1]), authority(direct))
                self.assertEqual(seeded.schemas, [NARRATIVE_SCHEMA])
                self.assertEqual(authority(result["decision"]), authority(direct))

                skipping = FakeModel(key, direct, calls_tool=False)
                result = run_agent(key, payload, skipping, tool_target=server)
                self.assertEqual((result["tool_mode"], result["tool_calls"]), ("model", [{"name": adapter.TOOL, "by": "harness"}]))
                self.assertIn("TOOL RESULT", skipping.prompts[0])
                self.assertEqual(authority(result["decision"]), authority(direct))

                self.assertEqual(run_agent(key, payload, FakeModel(key, direct), tool_target=server)["tool_calls"][0]["by"], "model")
                with self.assertRaisesRegex(ValueError, "tool_mode"):
                    run_agent(key, payload, FakeModel(key, direct), tool_target=server, options={"tool_mode": "other"})


class NarrativeGuardTests(unittest.TestCase):
    def test_decision_owned_fields_authored_by_the_model_are_stripped_and_reported(self):
        for key in DOMAINS + ["auditor"]:
            with self.subTest(role=key):
                server, _, _ = parts(key)
                payload, direct = role_input(key)
                forged = {"domain_determination": {"classification": "Forged Classification"}, "determination_status": {"result": "Forged"},
                          "determination_trace": [{"step": "FORGED"}]}
                result = run_agent(key, payload, FakeModel(key, direct, extra=forged), tool_target=server)
                guard = result["narrative_guard"]
                self.assertFalse(guard["passed"])
                self.assertEqual(guard["model_proposed_classification"], "Forged Classification")
                self.assertEqual(guard["authoritative_classification"], direct["final_classification"])
                self.assertEqual(set(guard["stripped_fields"]), set(forged))
                parsed = result["parsed"]
                self.assertEqual(parsed["domain_determination"]["classification"], direct["final_classification"])
                self.assertEqual(parsed["determination_status"]["result"], direct["compliance_result"])
                self.assertNotIn("FORGED", json.dumps(parsed))
                self.assertIn("decision-owned fields", " ".join(parsed["narrative_warnings"]))
                self.assertEqual(parsed["narrative_source"], "model")

    def test_an_ungrounded_narrative_is_rejected_twice_and_replaced_by_code(self):
        for key in DOMAINS + ["auditor"]:
            with self.subTest(role=key):
                server, _, _ = parts(key)
                payload, direct = role_input(key)
                narrative = deterministic_narrative(direct, key)
                narrative["reasoning"] += " The borrower also owes 987654321 dollars under file ZZ-987654321."
                backend = FakeModel(key, direct, reply={"narrative": narrative})
                result = run_agent(key, payload, backend, tool_target=server)
                guard = result["narrative_guard"]
                self.assertEqual((guard["source"], guard["attempts"], guard["grounded"]), ("deterministic_fallback", 2, False))
                self.assertTrue(guard["violations"] and guard["retry_violations"])
                self.assertEqual(result["parsed"]["narrative_source"], "deterministic_fallback")
                self.assertEqual(result["parsed"]["compliance_determination_summary"]["reasoning"],
                                 deterministic_narrative(direct, key)["reasoning"])
                self.assertNotIn("987654321", json.dumps(result["parsed"]["compliance_determination_summary"]))
                self.assertEqual(result["parsed"]["domain_determination"]["classification"], direct["final_classification"])
                self.assertIn("rejected twice", " ".join(result["parsed"]["narrative_warnings"]))
                self.assertIsNotNone(result["parse_error"])
                self.assertIn("987654321", result["raw_text"])            # the rejected model text stays observable

    def test_unparseable_model_text_still_returns_the_decision_with_the_raw_text(self):
        for key in DOMAINS + ["auditor"]:
            with self.subTest(role=key):
                server, _, _ = parts(key)
                payload, direct = role_input(key)

                class Prose(FakeModel):
                    def complete_with_tool(self, *args, **kwargs):
                        super().complete_with_tool(*args, **kwargs)
                        return "I refuse to produce JSON."

                    def complete(self, system, messages, json_mode=True, schema=None):
                        return "Still not JSON."

                result = run_agent(key, payload, Prose(key, direct), tool_target=server)
                self.assertEqual(result["parsed"]["narrative_source"], "deterministic_fallback")
                self.assertEqual(authority(result["decision"]), authority(direct))
                self.assertEqual(result["raw_text"], "Still not JSON.")
                self.assertIn("not valid JSON", result["narrative_guard"]["violations"][0])

    def test_regulation_provenance_is_retained_for_domains_and_absent_for_the_auditor(self):
        for key in DOMAINS + ["auditor"]:
            with self.subTest(role=key):
                server, _, _ = parts(key)
                payload, direct = role_input(key)
                given = run_agent(key, payload, FakeModel(key, direct), tool_target=server)["regulations_given"]
                off = run_agent(key, payload, FakeModel(key, direct), tool_target=server, options={"include_regulations": False})["regulations_given"]
                self.assertEqual(off, [])
                if key == "auditor":
                    self.assertEqual(given, [])        # a cross-regime consolidation with no regulatory source of its own
                else:
                    self.assertTrue(given and all(len(g["sha256"]) == 64 and g["citation"] for g in given))


class AuditorRoleTests(unittest.TestCase):
    """The auditor takes the other agents' results; a failed or unparsed agent is missing, never a pass."""

    def test_a_failed_agent_is_reported_missing_through_the_whole_stack(self):
        server, _, _ = parts("auditor")
        results = assembled(AUDIT_SAMPLE)
        results["hmda"] = {"agent_key": "hmda", "parsed": None, "parse_error": "RuntimeError: model unreachable"}
        payload = {"loan_data": AUDIT_SAMPLE, "agent_results": results}
        direct = role_input("auditor")[1]
        result = run_agent("auditor", payload, FakeModel("auditor", direct), tool_target=server)
        evaluation = result["decision"]["auditor_evaluation"]
        self.assertIn("hmda", evaluation["agents_missing"])
        self.assertNotIn("hmda", evaluation["agents_reviewed"])
        self.assertEqual(result["parsed"]["audit_summary"]["agents_missing"], evaluation["agents_missing"])
        self.assertNotEqual(result["decision"]["final_classification"], direct["final_classification"])

    def test_the_auditor_narration_prompt_carries_no_loan_case(self):
        server, _, _ = parts("auditor")
        payload, direct = role_input("auditor")
        backend = FakeModel("auditor", direct, calls_tool=False)
        run_agent("auditor", payload, backend, tool_target=server)
        self.assertIn("audit input was passed to the tool", backend.prompts[0])
        self.assertNotIn("hmda_case", backend.prompts[0].split("TOOL RESULT")[0])

    def test_run_dispatches_tool_backed_roles_to_the_tool_path_and_others_to_the_plain_path(self):
        server, _, _ = parts("ybs")
        payload, direct = role_input("ybs")
        self.assertEqual(run("ybs", payload, FakeModel("ybs", direct), tool_target=server)["tool_calls"][0]["name"], "ybs_evaluate")
        with self.assertRaisesRegex(ValueError, "Unknown agent"):
            run("no_such_agent", payload, FakeModel("ybs", direct))


if __name__ == "__main__":
    unittest.main()

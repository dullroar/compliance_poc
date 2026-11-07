"""A2A end-to-end with no network: ASGI in-process transport and a fake backend."""
import asyncio
import importlib
import json
import unittest
from pathlib import Path

import httpx
from google.protobuf.json_format import MessageToDict
from unittest import mock

from a2a.client import ClientConfig, create_client
from a2a.helpers.proto_helpers import new_data_part
from a2a.types.a2a_pb2 import Message, Role, SendMessageRequest

from agent_prompts import AGENTS
from agents.a2a_server import ComplianceExecutor, build_app
from compliance_mcp.ybs.server import server as ybs_server
from orchestrator.a2a_client import AgentTaskError, send
from orchestrator.config import load_agents

from test_agent_parity import FakeModel, role_input
from test_agent_runner import NARRATIVE, FakeBackend, loan
from test_auditor_evaluator import assembled
from test_ybs_evaluator import person

URL = "http://ybs.test/"


class _PlainBackend:
    provider, model = "fake", "fake-1"

    def __init__(self, text):
        self.text = text

    def complete(self, system, messages, json_mode=True):
        return self.text


def client_for(app, base):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=base)


class A2ATests(unittest.TestCase):
    def test_agent_card_and_tool_backed_task(self):
        async def go():
            app = build_app("ybs", URL, ComplianceExecutor("ybs", backend=FakeBackend(NARRATIVE), tool_target=ybs_server))
            async with client_for(app, URL) as http:
                card = (await http.get("/.well-known/agent-card.json")).json()
                result = await send(URL, loan([person()]), http)
            return card, result

        card, result = asyncio.run(go())
        self.assertEqual(card["version"], AGENTS["ybs"]["version"])
        self.assertEqual(card["skills"][0]["id"], "ybs")
        self.assertEqual(result["parsed"]["domain_determination"]["classification"], "Young + Beginning + Small")
        self.assertEqual(result["tool_calls"], [{"name": "ybs_evaluate", "by": "model"}])
        self.assertEqual(result["decision"]["decision_id"], result["parsed"]["agent_metadata"]["decision_id"])

    def test_plain_agent_and_markdown_agent(self):
        async def go():
            out = {}
            for key, text in (("plainx", json.dumps({"summary": {"reasoning": "ok"}})), ("narrative", "# Report")):
                app = build_app(key, URL, ComplianceExecutor(key, backend=_PlainBackend(text)))
                async with client_for(app, URL) as http:
                    out[key] = await send(URL, {"loan": 1}, http)
            return out

        with mock.patch.dict(AGENTS, {"plainx": {"key": "plainx", "name": "Plain Test Agent", "version": "0.0.1", "compliance_track": "Test", "system_prompt": "You are a test agent."}}):
            out = asyncio.run(go())
        self.assertEqual(out["plainx"]["parsed"]["summary"]["reasoning"], "ok")
        self.assertNotIn("decision", out["plainx"])
        self.assertEqual(out["narrative"]["raw_text"], "# Report")
        self.assertIsNone(out["narrative"]["parsed"])

    def test_backend_failure_is_a_failed_task_not_a_crash(self):
        class Boom(_PlainBackend):
            def complete(self, *a, **k):
                raise RuntimeError("model unreachable")

        async def go():
            app = build_app("narrative", URL, ComplianceExecutor("narrative", backend=Boom("")))
            async with client_for(app, URL) as http:
                await send(URL, {"loan": 1}, http)

        with self.assertRaisesRegex(AgentTaskError, "model unreachable"):
            asyncio.run(go())


REGISTRY = load_agents()


async def raw_task(app, payload):
    """The completed Task itself (all artifacts), not just the agent_result the orchestrator keeps."""
    async with client_for(app, URL) as http:
        client = await create_client(URL, ClientConfig(httpx_client=http, streaming=False))
        request = SendMessageRequest(message=Message(message_id="m1", role=Role.ROLE_USER, parts=[new_data_part({"payload": payload})]))
        return [r.task async for r in client.send_message(request) if r.HasField("task")][-1]


class EveryRegisteredRoleTests(unittest.TestCase):
    """Cards and tasks exist for every agents.yaml entry, and each role returns the artifacts its contract names."""

    def test_every_registry_entry_has_a_card_derived_from_its_prompt(self):
        async def go(key):
            async with client_for(build_app(key, URL, ComplianceExecutor(key, backend=_PlainBackend("{}"))), URL) as http:
                return (await http.get("/.well-known/agent-card.json")).json()

        for key in REGISTRY:
            with self.subTest(role=key):
                agent, card = AGENTS[key], asyncio.run(go(key))
                skill = card["skills"][0]
                self.assertEqual((card["name"], card["version"], skill["id"]), (agent["name"], agent["version"], key))
                self.assertEqual(card["supportedInterfaces"][0]["url"], URL)
                if agent.get("tool"):
                    self.assertIn(agent["tool"], skill["tags"])
                    self.assertIn(f"deterministic decisions come from MCP tool {agent['tool']}", card["description"])
                else:
                    self.assertEqual(skill["tags"], ["compliance", key])
                    self.assertIn("LLM-only agent", card["description"])

    def test_registry_urls_are_unique_and_every_entry_names_a_prompt(self):
        self.assertEqual(len({e["url"] for e in REGISTRY.values()}), len(REGISTRY))
        self.assertTrue(set(REGISTRY) <= set(AGENTS))

    def test_tool_backed_roles_return_result_and_decision_artifacts_and_the_narrative_returns_a_report(self):
        sample = json.loads((Path(__file__).resolve().parents[1] / "sample_loan.json").read_text(encoding="utf-8"))
        payloads = {"hpml": sample, "auditor": {"loan_data": sample, "agent_results": assembled(sample)}}
        for key, payload in payloads.items():
            with self.subTest(role=key):
                server = importlib.import_module(f"compliance_mcp.{key}.server").server
                _, direct = role_input(key)
                app = build_app(key, URL, ComplianceExecutor(key, backend=FakeModel(key, direct), tool_target=server))
                task = asyncio.run(raw_task(app, payload))
                self.assertEqual([a.name for a in task.artifacts], ["agent_result", "decision"])
                data = {a.name: MessageToDict(a.parts[0].data) for a in task.artifacts}
                self.assertEqual(data["decision"]["final_classification"], data["agent_result"]["decision"]["final_classification"])
                self.assertEqual(data["agent_result"]["parsed"]["agent_metadata"]["decision_id"], data["decision"]["decision_id"])
                self.assertTrue(data["agent_result"]["raw_text"])               # raw model text retained beside the parsed result

        app = build_app("narrative", URL, ComplianceExecutor("narrative", backend=_PlainBackend("# Report\n\nAll findings explained.")))
        task = asyncio.run(raw_task(app, {"hpml": {"classification": "Not HPML"}}))
        self.assertEqual([a.name for a in task.artifacts], ["agent_result", "report"])
        result = MessageToDict(task.artifacts[0].parts[0].data)
        self.assertNotIn("decision", result)                                      # the narrator is not asked for a decision or MCP result
        self.assertNotIn("tool_calls", result)
        self.assertEqual((result["raw_text"], result.get("parsed"), result.get("parse_error")), ("# Report\n\nAll findings explained.", None, None))
        self.assertEqual(task.artifacts[1].parts[0].text, "# Report\n\nAll findings explained.")

    def test_a_plain_agent_that_answers_with_prose_keeps_the_raw_text_and_the_parse_error(self):
        with mock.patch.dict(AGENTS, {"plainx": {"key": "plainx", "name": "Plain Test Agent", "version": "0.0.1", "compliance_track": "Test", "system_prompt": "x"}}):
            app = build_app("plainx", URL, ComplianceExecutor("plainx", backend=_PlainBackend("Prose, not JSON.")))
            result = asyncio.run(self.send_to(app))
        self.assertEqual((result["raw_text"], result["parsed"]), ("Prose, not JSON.", None))
        self.assertTrue(result["parse_error"])

    @staticmethod
    async def send_to(app):
        async with client_for(app, URL) as http:
            return await send(URL, {"loan": 1}, http)

    def test_the_registry_options_reach_the_executor_of_a_tool_backed_role(self):
        _, direct = role_input("ybs")
        recorder = FakeModel("ybs", direct)
        app = build_app("ybs", URL, ComplianceExecutor("ybs", backend=recorder, tool_target=importlib.import_module("compliance_mcp.ybs.server").server,
                                                       options={"tool_mode": "seeded"}))
        result = asyncio.run(self.send_to_ybs(app))
        self.assertEqual((result["tool_mode"], result["tool_calls"]), ("seeded", [{"name": "ybs_evaluate", "by": "seeded"}]))

    @staticmethod
    async def send_to_ybs(app):
        async with client_for(app, URL) as http:
            return await send(URL, loan([person()]), http)


if __name__ == "__main__":
    unittest.main()

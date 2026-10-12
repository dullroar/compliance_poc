"""A2A end-to-end with no network: ASGI in-process transport and a fake backend."""
import asyncio
import json
import unittest

import httpx
from unittest import mock

from agent_prompts import AGENTS
from agents.a2a_server import ComplianceExecutor, build_app
from compliance_mcp.ybs.server import server as ybs_server
from orchestrator.a2a_client import AgentTaskError, send

from test_agent_runner import NARRATIVE, FakeBackend, loan
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


if __name__ == "__main__":
    unittest.main()

"""Expose one compliance agent as an A2A server (Agent Card + executor).

Request: a user Message with a data Part {"payload": <loan dict | narrative str |
auditor/narrative input>} (a bare text Part is also accepted as the payload).
Response: a Task with artifacts
  agent_result  data  the full result dict (parsed/assembled output, decision, guards)
  decision      data  the deterministic decision record (tool-backed agents only)
  report        text  markdown (markdown-output agents only)
Local (Ollama) and remote (Anthropic) models sit behind the same interface: the
backend comes from agents.yaml, not from the protocol.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from google.protobuf.json_format import MessageToDict
from starlette.applications import Starlette

from a2a.helpers.proto_helpers import new_data_artifact, new_task_from_user_message, new_text_artifact, new_text_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue_v2 import EventQueue
from a2a.server.request_handlers import DefaultRequestHandlerV2
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types.a2a_pb2 import AgentCapabilities, AgentCard, AgentInterface, AgentSkill, Part
from a2a.utils.constants import PROTOCOL_VERSION_CURRENT, TransportProtocol

from agent_prompts import AGENTS
from compliance_common.obs import get_logger

from .backends import Backend
from .runner import run

RESULT_ARTIFACT = "agent_result"


def agent_card(agent_key: str, url: str) -> AgentCard:
    agent = AGENTS[agent_key]
    tool = agent.get("tool")
    return AgentCard(
        name=agent["name"],
        description=f"{agent['compliance_track']}. "
                    + (f"Narrative-only; deterministic decisions come from MCP tool {tool}." if tool else "LLM-only agent."),
        version=agent["version"],
        supported_interfaces=[AgentInterface(url=url, protocol_binding=TransportProtocol.JSONRPC,
                                             protocol_version=PROTOCOL_VERSION_CURRENT)],
        capabilities=AgentCapabilities(streaming=False),
        default_input_modes=["application/json", "text/plain"],
        default_output_modes=["application/json", "text/markdown"],
        skills=[AgentSkill(id=agent_key, name=agent["name"], description=agent["compliance_track"],
                           tags=["compliance", agent_key] + ([tool] if tool else []))],
    )


def _payload(context: RequestContext) -> Any:
    for part in context.message.parts:
        if part.HasField("data"):
            data = MessageToDict(part.data)
            return data["payload"] if isinstance(data, dict) and "payload" in data else data
    return context.get_user_input()


class ComplianceExecutor(AgentExecutor):
    def __init__(self, agent_key: str, provider: str | None = None, model: str | None = None,
                 backend: Any | None = None, tool_target: Any | None = None, options: dict[str, Any] | None = None) -> None:
        self.agent_key, self.provider, self.model = agent_key, provider, model
        self._backend, self.tool_target, self.options = backend, tool_target, options
        self.log = get_logger(f"a2a.{agent_key}", AGENTS[agent_key]["version"])

    def backend(self) -> Any:
        return self._backend or Backend(self.provider, self.model)

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        if context.current_task is None:  # v2 handler requires the Task before any status update
            await event_queue.enqueue_event(new_task_from_user_message(context.message))
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        extra = {"task_id": context.task_id, "agent": self.agent_key}
        await updater.start_work()
        try:
            payload = _payload(context)
            self.log.info("task started", extra=extra)
            result = await asyncio.to_thread(
                run, self.agent_key, payload, self.backend(), None, self.tool_target, self.options)
        except Exception as exc:  # surfaced as a failed task, never a server crash
            self.log.error("task failed: %s", exc, extra=extra)
            await updater.failed(new_text_message(f"{type(exc).__name__}: {exc}"))
            return
        artifacts = [new_data_artifact(RESULT_ARTIFACT, json.loads(json.dumps(result, default=str)))]
        decision = result.get("decision")
        if decision:
            artifacts.append(new_data_artifact("decision", decision))
        if AGENTS[self.agent_key].get("output_format") == "markdown":
            artifacts.append(new_text_artifact("report", result["raw_text"], media_type="text/markdown"))
        for artifact in artifacts:
            await updater.add_artifact(list(artifact.parts), name=artifact.name)
        self.log.info("task completed", extra={**extra, **({"decision_id": decision["decision_id"]} if decision else {})})
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        await TaskUpdater(event_queue, context.task_id, context.context_id).cancel()


def build_app(agent_key: str, url: str, executor: ComplianceExecutor | None = None,
              provider: str | None = None, model: str | None = None, options: dict[str, Any] | None = None) -> Starlette:
    card = agent_card(agent_key, url)
    handler = DefaultRequestHandlerV2(
        agent_executor=executor or ComplianceExecutor(agent_key, provider, model, options=options),
        task_store=InMemoryTaskStore(), agent_card=card)
    return Starlette(routes=[*create_agent_card_routes(card), *create_jsonrpc_routes(handler, rpc_url="/")])

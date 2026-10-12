"""Send a payload to a compliance agent over A2A and return its result dict."""
from __future__ import annotations

import uuid
from typing import Any

import httpx
from google.protobuf.json_format import MessageToDict

from a2a.client import ClientConfig, create_client
from a2a.helpers.proto_helpers import new_data_part
from a2a.types.a2a_pb2 import Message, Role, SendMessageRequest, TaskState

from agents.a2a_server import RESULT_ARTIFACT

AGENT_TIMEOUT = 1800.0  # local models are slow; a full ollama agent run can take minutes


class AgentTaskError(RuntimeError):
    pass


def _artifact_data(task: Any, name: str) -> Any:
    for artifact in task.artifacts:
        if artifact.name == name:
            for part in artifact.parts:
                if part.HasField("data"):
                    return MessageToDict(part.data)
    return None


async def send(url: str, payload: Any, httpx_client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    """Run one agent task at `url` and return the agent_result artifact (a result dict)."""
    own = httpx_client is None
    http = httpx_client or httpx.AsyncClient(timeout=AGENT_TIMEOUT)
    try:
        client = await create_client(url, ClientConfig(httpx_client=http, streaming=False))
        request = SendMessageRequest(message=Message(
            message_id=str(uuid.uuid4()), role=Role.ROLE_USER, parts=[new_data_part({"payload": payload})]))
        task = None
        async for response in client.send_message(request):
            if response.HasField("task"):
                task = response.task
        if task is None:
            raise AgentTaskError(f"{url}: no task returned")
        if task.status.state != TaskState.TASK_STATE_COMPLETED:
            text = " ".join(p.text for p in task.status.message.parts if p.text)
            raise AgentTaskError(f"{url}: task ended {TaskState.Name(task.status.state)}: {text}")
        result = _artifact_data(task, RESULT_ARTIFACT)
        if result is None:
            raise AgentTaskError(f"{url}: task completed without an {RESULT_ARTIFACT} artifact")
        return result
    finally:
        if own:
            await http.aclose()

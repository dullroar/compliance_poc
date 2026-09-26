"""Portable function-tool surface for optional interactive YBS use.

The batch runner invokes ``evaluate_ybs`` directly.  These definitions exist so
provider adapters or a future MCP server can expose the identical evaluator.
"""

from __future__ import annotations

import json
from typing import Any

from .ybs import evaluate_ybs


YBS_TOOL_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {
        "case": {"type": "object", "description": "Canonical YBS case object."},
        "rule_pack_id": {"type": "string", "description": "Pinned YBS rule-pack identifier."},
    },
    "required": ["case"],
    "additionalProperties": False,
}


def tool_definition(provider: str) -> dict[str, Any]:
    """Return the native function declaration for Anthropic or Ollama."""
    if provider == "anthropic":
        return {"name": "evaluate_ybs", "description": "Run the authoritative offline YBS rule evaluator.", "input_schema": YBS_TOOL_PARAMETERS}
    if provider == "ollama":
        return {"type": "function", "function": {"name": "evaluate_ybs", "description": "Run the authoritative offline YBS rule evaluator.", "parameters": YBS_TOOL_PARAMETERS}}
    raise ValueError("Supported providers are anthropic and ollama")


def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name != "evaluate_ybs":
        raise ValueError(f"Unknown compliance tool: {name}")
    return evaluate_ybs(arguments["case"], arguments.get("rule_pack_id", "ybs-v0.1"))


def run_anthropic_ybs_tool_loop(client: Any, *, model: str, system: str, messages: list[dict[str, Any]], max_tokens: int) -> Any:
    """Run an optional Anthropic client-tool loop using the shared evaluator.

    The normal batch path intentionally does not use this: it calls the
    evaluator before model invocation. This helper is for an interactive UI
    that elects to let a tool-capable Claude model request the same function.
    """
    working_messages = list(messages)
    while True:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=working_messages,
            tools=[tool_definition("anthropic")],
            tool_choice={"type": "auto", "disable_parallel_tool_use": True},
        )
        calls = [block for block in response.content if getattr(block, "type", None) == "tool_use"]
        if not calls:
            return response
        working_messages.append({"role": "assistant", "content": response.content})
        working_messages.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": call.id,
                "content": json.dumps(execute_tool(call.name, call.input)),
            } for call in calls],
        })


def run_ollama_ybs_tool_loop(request: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """Run an optional Ollama tool loop with an injected JSON request function.

    ``request`` receives a chat payload and returns the decoded Ollama response.
    Keeping HTTP outside this helper makes the tool contract testable and keeps
    the evaluator independent from a provider transport.
    """
    working = dict(payload)
    working["tools"] = [tool_definition("ollama")]
    working["stream"] = False
    working["messages"] = list(payload.get("messages", []))
    while True:
        response = request(working)
        calls = response.get("message", {}).get("tool_calls", [])
        if not calls:
            return response
        working["messages"].append(response["message"])
        for call in calls:
            function = call["function"]
            working["messages"].append({
                "role": "tool",
                "tool_name": function["name"],
                "content": json.dumps(execute_tool(function["name"], function.get("arguments", {}))),
            })

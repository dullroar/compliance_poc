"""Provider tool adapters and tool loops, generic over an MCP-style tool spec.

A tool spec is the MCP shape: {"name", "description", "inputSchema"}. The same spec
is exposed natively to Anthropic and Ollama, so every transport sees one contract.
`execute(name, arguments)` is injected: an MCP client call in production, a direct
evaluator call in tests.
"""
from __future__ import annotations

import json
from typing import Any, Callable

ToolSpec = dict[str, Any]
Execute = Callable[[str, dict[str, Any]], dict[str, Any]]


def native_definition(spec: ToolSpec, provider: str) -> dict[str, Any]:
    """Return the native function declaration for Anthropic or Ollama."""
    if provider == "anthropic":
        return {"name": spec["name"], "description": spec["description"], "input_schema": spec["inputSchema"]}
    if provider == "ollama":
        return {"type": "function", "function": {"name": spec["name"], "description": spec["description"], "parameters": spec["inputSchema"]}}
    raise ValueError("Supported providers are anthropic and ollama")


def seed_anthropic(spec: ToolSpec, arguments: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    """The assistant's tool_use and the matching tool_result, as if the model had made the call itself."""
    call_id = "toolu_seeded_1"
    return [{"role": "assistant", "content": [{"type": "tool_use", "id": call_id, "name": spec["name"], "input": arguments}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": call_id, "content": json.dumps(result)}]}]


def seed_ollama(spec: ToolSpec, arguments: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"role": "assistant", "content": "", "tool_calls": [{"function": {"name": spec["name"], "arguments": arguments}}]},
            {"role": "tool", "tool_name": spec["name"], "content": json.dumps(result)}]


def run_anthropic_tool_loop(client: Any, spec: ToolSpec, execute: Execute, *, model: str, system: str,
                            messages: list[dict[str, Any]], max_tokens: int,
                            calls_made: list[dict[str, Any]] | None = None, force_first: bool = False) -> Any:
    """Run an Anthropic client-tool loop. Tool calls are appended to `calls_made`.

    force_first=True makes the FIRST request require the tool (`tool_choice: tool`), so the model cannot answer
    without calling it; later requests are free so it can write the final answer."""
    working = list(messages)
    first = True
    while True:
        choice = ({"type": "tool", "name": spec["name"], "disable_parallel_tool_use": True} if force_first and first
                  else {"type": "auto", "disable_parallel_tool_use": True})
        first = False
        response = client.messages.create(
            model=model, max_tokens=max_tokens, system=system, messages=working,
            tools=[native_definition(spec, "anthropic")], tool_choice=choice,
        )
        calls = [block for block in response.content if getattr(block, "type", None) == "tool_use"]
        if not calls:
            return response
        working.append({"role": "assistant", "content": response.content})
        results = []
        for call in calls:
            result = execute(call.name, call.input)
            if calls_made is not None:
                calls_made.append({"name": call.name, "arguments": call.input, "result": result})
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": json.dumps(result)})
        working.append({"role": "user", "content": results})


def run_ollama_tool_loop(request: Callable[[dict[str, Any]], dict[str, Any]], spec: ToolSpec, execute: Execute,
                         payload: dict[str, Any], calls_made: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Run an Ollama tool loop with an injected JSON request function."""
    working = dict(payload)
    working["tools"] = [native_definition(spec, "ollama")]
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
            arguments = function.get("arguments", {})
            result = execute(function["name"], arguments)
            if calls_made is not None:
                calls_made.append({"name": function["name"], "arguments": arguments, "result": result})
            working["messages"].append({"role": "tool", "tool_name": function["name"], "content": json.dumps(result)})

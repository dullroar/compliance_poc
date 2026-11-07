"""Provider tool adapters and tool loops, generic over an MCP-style tool spec.

A tool spec is the MCP shape: {"name", "description", "inputSchema"}. The same spec
is exposed natively to Anthropic, Ollama, and OpenAI, so every transport sees one contract.
`execute(name, arguments)` is injected: an MCP client call in production, a direct
evaluator call in tests.
"""
from __future__ import annotations

import json
from typing import Any, Callable

ToolSpec = dict[str, Any]
Execute = Callable[[str, dict[str, Any]], dict[str, Any]]


def native_definition(spec: ToolSpec, provider: str) -> dict[str, Any]:
    """Return the native function declaration for a supported provider."""
    if provider == "anthropic":
        return {"name": spec["name"], "description": spec["description"], "input_schema": spec["inputSchema"]}
    if provider == "ollama":
        return {"type": "function", "function": {"name": spec["name"], "description": spec["description"], "parameters": spec["inputSchema"]}}
    if provider == "openai":
        # MCP input schemas can contain optional fields, which is incompatible with OpenAI strict function schemas.
        # The runner still pins every evaluator input to the canonical loan payload, so non-strict model arguments
        # cannot influence a decision.
        return {"type": "function", "name": spec["name"], "description": spec["description"],
                "parameters": spec["inputSchema"], "strict": False}
    raise ValueError("Supported providers are anthropic, ollama, and openai")


def seed_anthropic(spec: ToolSpec, arguments: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    """The assistant's tool_use and the matching tool_result, as if the model had made the call itself."""
    call_id = "toolu_seeded_1"
    return [{"role": "assistant", "content": [{"type": "tool_use", "id": call_id, "name": spec["name"], "input": arguments}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": call_id, "content": json.dumps(result)}]}]


def seed_ollama(spec: ToolSpec, arguments: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"role": "assistant", "content": "", "tool_calls": [{"function": {"name": spec["name"], "arguments": arguments}}]},
            {"role": "tool", "tool_name": spec["name"], "content": json.dumps(result)}]


def seed_openai(spec: ToolSpec, arguments: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    """A completed Responses API function exchange, as if the model had called the evaluator."""
    call_id = "call_seeded_1"
    return [{"type": "function_call", "call_id": call_id, "name": spec["name"], "arguments": json.dumps(arguments)},
            {"type": "function_call_output", "call_id": call_id, "output": json.dumps(result)}]


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


def run_openai_tool_loop(client: Any, spec: ToolSpec, execute: Execute, *, model: str, system: str,
                         messages: list[dict[str, Any]], max_tokens: int,
                         calls_made: list[dict[str, Any]] | None = None, force_first: bool = False,
                         schema: dict[str, Any] | None = None) -> Any:
    """Run a stateless Responses API function loop using only the supplied evaluator function.

    Each response output is replayed in full because ``store=False`` prevents a continuation through
    ``previous_response_id``. Parallel calls are disabled: this POC exposes one deterministic evaluator only.
    """
    working: list[Any] = list(messages)
    first = True
    tool = native_definition(spec, "openai")
    while True:
        choice: str | dict[str, str] = ({"type": "function", "name": spec["name"]} if force_first and first else "auto")
        first = False
        request: dict[str, Any] = {
            "model": model, "instructions": system, "input": working, "max_output_tokens": max_tokens,
            "store": False, "tools": [tool], "tool_choice": choice, "parallel_tool_calls": False,
        }
        if schema:
            request["text"] = {"format": {"type": "json_schema", "name": "compliance_narrative",
                                          "strict": True, "schema": schema}}
        response = client.responses.create(**request)
        calls = [item for item in response.output if getattr(item, "type", None) == "function_call"]
        if not calls:
            return response
        working.extend(response.output)
        for call in calls:
            try:
                arguments = json.loads(call.arguments)
            except (TypeError, json.JSONDecodeError) as exc:
                raise RuntimeError("OpenAI returned malformed function arguments") from exc
            if not isinstance(arguments, dict):
                raise RuntimeError("OpenAI returned function arguments that were not an object")
            result = execute(call.name, arguments)
            if calls_made is not None:
                calls_made.append({"name": call.name, "arguments": arguments, "result": result})
            working.append({"type": "function_call_output", "call_id": call.call_id, "output": json.dumps(result)})

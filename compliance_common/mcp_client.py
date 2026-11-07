"""Thin async MCP client helpers for calling a domain evaluator over stdio."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

from mcp import Client
from mcp.client.stdio import StdioServerParameters, stdio_client

from .obs import get_logger

log = get_logger("mcp-client", "1")


def stdio_target(domain: str) -> StdioServerParameters:
    """Launch compliance_mcp.<domain>.server as a stdio subprocess."""
    return StdioServerParameters(command=sys.executable, args=["-m", f"compliance_mcp.{domain}.server"], env=dict(os.environ))


def _transport(target: Any) -> Any:
    return stdio_client(target) if isinstance(target, StdioServerParameters) else target


def _decode(result: Any) -> dict[str, Any]:
    if getattr(result, "is_error", False) or getattr(result, "isError", False):
        text = " ".join(getattr(block, "text", "") for block in result.content)
        raise RuntimeError(f"MCP tool error: {text}")
    structured = getattr(result, "structured_content", None) or getattr(result, "structuredContent", None)
    if structured:
        return structured.get("result", structured) if set(structured) == {"result"} else structured
    return json.loads(result.content[0].text)


def _leaf(error: BaseException) -> BaseException:
    """The first underlying error of an anyio task-group failure, so the tool's own message reaches the caller."""
    while isinstance(error, BaseExceptionGroup) and error.exceptions:
        error = error.exceptions[0]
    return error


async def list_tool_specs(target: Any) -> list[dict[str, Any]]:
    """Return MCP-shaped tool specs {name, description, inputSchema}."""
    try:
        async with Client(_transport(target)) as client:
            listing = await client.list_tools()
    except BaseExceptionGroup as group:
        raise _leaf(group) from group
    return [{"name": t.name, "description": t.description or "", "inputSchema": t.input_schema} for t in listing.tools]


async def call_tool(target: Any, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    log.trace("mcp call", extra={"tool": name}, payload=arguments)
    try:
        async with Client(_transport(target)) as client:
            result = _decode(await client.call_tool(name, arguments))
    except BaseExceptionGroup as group:       # e.g. "MCP tool error: Invalid canonical HMDA input ..." instead of "unhandled errors in a TaskGroup"
        raise _leaf(group) from group
    log.trace("mcp result", extra={"tool": name, "decision_id": result.get("decision_id", "")}, payload=result)
    return result

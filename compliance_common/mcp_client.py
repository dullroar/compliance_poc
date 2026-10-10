"""Thin async MCP client helpers for calling a domain evaluator over stdio."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from .obs import get_logger

log = get_logger("mcp-client", "1")


def stdio_target(domain: str) -> StdioServerParameters:
    """Launch compliance_mcp.<domain>.server as a stdio subprocess."""
    return StdioServerParameters(command=sys.executable, args=["-m", f"compliance_mcp.{domain}.server"], env=dict(os.environ))


def _decode(result: Any) -> dict[str, Any]:
    if getattr(result, "is_error", False) or getattr(result, "isError", False):
        text = " ".join(getattr(block, "text", "") for block in result.content)
        raise RuntimeError(f"MCP tool error: {text}")
    structured = getattr(result, "structured_content", None) or getattr(result, "structuredContent", None)
    if structured:
        return structured.get("result", structured) if set(structured) == {"result"} else structured
    return json.loads(result.content[0].text)


async def list_tool_specs(target: Any) -> list[dict[str, Any]]:
    """Return MCP-shaped tool specs {name, description, inputSchema}."""
    async with Client(target) as client:
        listing = await client.list_tools()
    return [{"name": t.name, "description": t.description or "", "inputSchema": t.input_schema} for t in listing.tools]


async def call_tool(target: Any, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    log.trace("mcp call", extra={"tool": name}, payload=arguments)
    async with Client(target) as client:
        result = _decode(await client.call_tool(name, arguments))
    log.trace("mcp result", extra={"tool": name, "decision_id": result.get("decision_id", "")}, payload=result)
    return result

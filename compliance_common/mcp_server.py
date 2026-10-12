"""Generic stdio MCP server for a deterministic evaluator.

Each domain's server.py is a few lines: it names the tool, the evaluator and its
version. Logging follows compliance_common.obs (INFO decision summary, DEBUG
inputs/outputs, TRACE full record). stdout belongs to the MCP protocol.
"""
from __future__ import annotations

from typing import Any, Callable

from mcp.server.mcpserver import MCPServer

from .obs import get_logger
from .pack import EvaluatorValidationError


def build_server(domain: str, version: str, description: str, evaluate: Callable[[dict[str, Any]], dict[str, Any]]) -> MCPServer:
    log = get_logger(f"mcp.{domain}", version)
    server = MCPServer(f"{domain}-evaluator")

    def tool(case: dict[str, Any]) -> dict[str, Any]:
        log.debug("tool call", extra={"tool": f"{domain}_evaluate"}, payload=case)
        try:
            record = evaluate(case)
        except EvaluatorValidationError as exc:
            log.error("evaluation rejected: %s", exc, extra={"tool": f"{domain}_evaluate"})
            raise
        log.info(
            "%s -> %s (%s)", domain, record["final_classification"], record["determination_status"],
            extra={"decision_id": record["decision_id"], "tool": f"{domain}_evaluate"},
        )
        log.trace("decision record", extra={"decision_id": record["decision_id"]}, payload=record)
        return record

    server.add_tool(tool, name=f"{domain}_evaluate", description=f"{description} (evaluator v{version})")
    return server

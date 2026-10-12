"""MCP stdio server: `python -m compliance_mcp.auditor.server`."""
from compliance_common.mcp_server import build_server

from .rules import EVALUATOR_VERSION, evaluate_auditor

server = build_server("auditor", EVALUATOR_VERSION, "Run the deterministic cross-regime audit checks over the other agents' results", evaluate_auditor)

if __name__ == "__main__":
    server.run()

"""MCP stdio server: `python -m compliance_mcp.hmda.server`."""
from compliance_common.mcp_server import build_server

from .rules import EVALUATOR_VERSION, evaluate_hmda

server = build_server("hmda", EVALUATOR_VERSION, "Run the authoritative offline HMDA (Regulation C) coverage and 38-item LAR rule evaluator", evaluate_hmda)

if __name__ == "__main__":
    server.run()

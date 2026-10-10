"""MCP stdio server: `python -m compliance_mcp.hpml.server`."""
from compliance_common.mcp_server import build_server

from .rules import EVALUATOR_VERSION, evaluate_hpml

server = build_server("hpml", EVALUATOR_VERSION, "Run the authoritative offline HPML (12 CFR 1026.35) rule evaluator", evaluate_hpml)

if __name__ == "__main__":
    server.run()

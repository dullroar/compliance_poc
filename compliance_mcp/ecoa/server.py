"""MCP stdio server: `python -m compliance_mcp.ecoa.server`."""
from compliance_common.mcp_server import build_server

from .rules import EVALUATOR_VERSION, evaluate_ecoa

server = build_server("ecoa", EVALUATOR_VERSION, "Run the authoritative offline ECOA (Regulation B) notification and fair-lending-process rule evaluator", evaluate_ecoa)

if __name__ == "__main__":
    server.run()

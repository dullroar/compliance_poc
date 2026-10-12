"""MCP stdio server: `python -m compliance_mcp.vmi.server`."""
from compliance_common.mcp_server import build_server

from .rules import EVALUATOR_VERSION, evaluate_vmi

server = build_server("vmi", EVALUATOR_VERSION, "Run the authoritative offline VMI (Regulation B monitoring information) rule evaluator", evaluate_vmi)

if __name__ == "__main__":
    server.run()

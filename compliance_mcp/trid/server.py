"""MCP stdio server: `python -m compliance_mcp.trid.server`."""
from compliance_common.mcp_server import build_server

from .rules import EVALUATOR_VERSION, evaluate_trid

server = build_server("trid", EVALUATOR_VERSION, "Run the authoritative offline TRID (12 CFR 1026.19(e)/(f)) rule evaluator", evaluate_trid)

if __name__ == "__main__":
    server.run()

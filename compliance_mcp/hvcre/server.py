"""MCP stdio server: `python -m compliance_mcp.hvcre.server`."""
from compliance_common.mcp_server import build_server

from .rules import EVALUATOR_VERSION, evaluate_hvcre

server = build_server("hvcre", EVALUATOR_VERSION, "Run the authoritative offline HVCRE (FCA capital rule 12 CFR 628.2) classification evaluator", evaluate_hvcre)

if __name__ == "__main__":
    server.run()

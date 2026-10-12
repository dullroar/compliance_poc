"""MCP stdio server: `python -m compliance_mcp.fzd.server`."""
from compliance_common.mcp_server import build_server

from .rules import EVALUATOR_VERSION, evaluate_fzd

server = build_server("fzd", EVALUATOR_VERSION, "Run the authoritative offline flood-insurance (FCA 12 CFR 614 subpart S) rule evaluator", evaluate_fzd)

if __name__ == "__main__":
    server.run()

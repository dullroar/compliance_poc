"""MCP stdio server: `python -m compliance_mcp.ybs.server`."""
from compliance_common.mcp_server import build_server

from .rules import EVALUATOR_VERSION, evaluate_ybs

server = build_server("ybs", EVALUATOR_VERSION, "Run the authoritative offline YBS eligibility rule evaluator", evaluate_ybs)

if __name__ == "__main__":
    server.run()

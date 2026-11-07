"""Direct, in-process, and wire calls share the deterministic YBS contract."""
import json
import unittest
from pathlib import Path

from compliance_common.mcp_client import call_tool, stdio_target
from compliance_mcp.ybs import evaluate_ybs
from compliance_mcp.ybs.server import server as ybs_server


class MCPContractTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = json.loads((Path(__file__).resolve().parents[1] / "sample_ybs_case.json").read_text())
        cls.expected = evaluate_ybs(cls.case)

    def assert_decision_matches(self, result):
        self.assertEqual(result["decision_id"], self.expected["decision_id"])
        self.assertEqual(result["final_classification"], self.expected["final_classification"])

    async def test_in_process_parity(self):
        result = await call_tool(ybs_server, "ybs_evaluate", {"case": self.case})
        self.assert_decision_matches(result)

    async def test_stdio_wire_parity(self):
        result = await call_tool(stdio_target("ybs"), "ybs_evaluate", {"case": self.case})
        self.assert_decision_matches(result)

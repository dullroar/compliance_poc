"""Evaluator adapters run directly in async MCP handlers, without worker threads."""
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from compliance_common.mcp_client import call_tool
from compliance_common.mcp_server import build_server
from compliance_mcp.ybs import evaluate_ybs
from compliance_mcp.ybs.server import server as ybs_server


async def reject_worker_bridge(*args, **kwargs):
    raise AssertionError("MCP evaluator used the AnyIO worker bridge")


class MCPServerRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_sync_evaluator_runs_once_without_worker_bridge(self):
        case = {"case_id": "synthetic-case"}
        decision = {"decision_id": "synthetic-decision", "final_classification": "test",
                    "determination_status": "test"}
        evaluate = Mock(return_value=decision)
        server = build_server("probe", "1", "Synthetic probe", evaluate)
        with patch("anyio.to_thread.run_sync", side_effect=reject_worker_bridge):
            result = await call_tool(server, "probe_evaluate", {"case": case})
        self.assertEqual(result, decision)
        evaluate.assert_called_once_with(case)

    async def test_ybs_decision_and_classification_match_direct_evaluation(self):
        case = json.loads((Path(__file__).resolve().parents[1] / "sample_ybs_case.json").read_text())
        expected = evaluate_ybs(case)
        with patch("anyio.to_thread.run_sync", side_effect=reject_worker_bridge):
            result = await call_tool(ybs_server, "ybs_evaluate", {"case": case})
        self.assertEqual(result["decision_id"], expected["decision_id"])
        self.assertEqual(result["final_classification"], expected["final_classification"])

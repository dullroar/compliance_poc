"""Exercise real stdio discovery, evaluator invocation, and child cleanup."""
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import mcp.client.stdio as stdio

from compliance_common.mcp_client import call_tool, list_tool_specs, stdio_target
from compliance_mcp.ybs import evaluate_ybs


class MCPStdioClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_ybs_discovery_call_and_child_cleanup(self):
        case = json.loads((Path(__file__).resolve().parents[1] / "sample_ybs_case.json").read_text())
        expected = evaluate_ybs(case)
        processes = []
        create_process = stdio._create_platform_compatible_process

        async def track_process(*args, **kwargs):
            process = await create_process(*args, **kwargs)
            processes.append(process)
            return process

        with patch.object(stdio, "_create_platform_compatible_process", side_effect=track_process):
            specs = await list_tool_specs(stdio_target("ybs"))
            self.assertEqual([spec["name"] for spec in specs], ["ybs_evaluate"])
            self.assertEqual(len(processes), 1)
            self.assertIsNotNone(processes[0].returncode, "discovery child still running")

            result = await call_tool(stdio_target("ybs"), "ybs_evaluate", {"case": case})
            self.assertEqual(len(processes), 2)
            self.assertIsNotNone(processes[1].returncode, "tool call child still running")

        self.assertEqual(result["decision_id"], expected["decision_id"])
        self.assertEqual(result["final_classification"], expected["final_classification"])

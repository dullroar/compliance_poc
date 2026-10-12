"""Opt-in live verification of deterministic YBS behavior with local Gemma."""

import json
import os
from pathlib import Path
import unittest

from agents.backends import Backend
from agents.runner import run


@unittest.skipUnless(
    os.getenv("RUN_LIVE_OLLAMA_TESTS") == "1",
    "set RUN_LIVE_OLLAMA_TESTS=1 to run the local Ollama/Gemma integration test",
)
class YBSGemmaIntegrationTests(unittest.TestCase):
    def test_gemma_cannot_change_a_replayed_deterministic_decision(self):
        case = json.loads((Path(__file__).resolve().parents[1] / "sample_ybs_case.json").read_text(encoding="utf-8"))
        loan = {"case_information": {"case_id": case["case_id"]}, "ybs_case": case}
        model = os.getenv("COMPLIANCE_MODEL", "gemma4:26b")
        first = run("ybs", loan, Backend("ollama", model))
        second = run("ybs", loan, Backend("ollama", model))

        for result in (first, second):
            self.assertIsNone(result["parse_error"], result["raw_text"])
            self.assertTrue(result["tool_calls"], "agent never reached the ybs_evaluate tool")
            self.assertIsNotNone(result["parsed"])
            self.assertEqual(result["provider"], "ollama")
            self.assertEqual(result["model"], model)
        self.assertEqual(
            first["decision"]["decision_id"],
            second["decision"]["decision_id"],
        )
        self.assertEqual(
            first["decision"]["final_classification"],
            second["decision"]["final_classification"],
        )
        self.assertEqual(
            first["parsed"]["domain_determination"]["classification"],
            first["decision"]["final_classification"],
        )
        self.assertEqual(
            second["parsed"]["domain_determination"]["classification"],
            second["decision"]["final_classification"],
        )


if __name__ == "__main__":
    unittest.main()

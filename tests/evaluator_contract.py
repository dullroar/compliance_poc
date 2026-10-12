"""Contract tests every evaluator domain must pass; build a TestCase with `contract_tests(...)`."""
import asyncio
import hashlib
import unittest
from pathlib import Path

import yaml

from builders.sourcing import normalize
from compliance_common.mcp_client import call_tool
from compliance_common.pack import EvaluatorValidationError

ROOT = Path(__file__).resolve().parents[1]


def contract_tests(domain, evaluate, validate_pack, validate_record, server, good_case, phrases, bad_key="surprise"):
    class Contract(unittest.TestCase):
        def test_pack_sources_and_contracts_validate(self):
            validate_pack()
            manifest = yaml.safe_load((ROOT / f"compliance_mcp/{domain}/pack/manifest.yaml").read_text(encoding="utf-8"))
            self.assertEqual(manifest["id"], domain)
            self.assertEqual(manifest["status"], "draft_engineering_review")
            for source in manifest["sources"]:
                with self.subTest(source=source["id"]):
                    self.assertEqual(hashlib.sha256((ROOT / source["local_path"]).read_bytes()).hexdigest(), source["sha256"])

        def test_thresholds_match_the_pinned_regulation_text(self):
            pinned = " ".join(normalize(p.read_bytes()) for p in (ROOT / f"compliance_mcp/{domain}/pack/sources").glob("*.xml"))
            for phrase in phrases:
                with self.subTest(phrase=phrase):
                    self.assertIn(phrase, pinned)

        def test_schema_rejects_malformed_input_and_output(self):
            with self.assertRaisesRegex(EvaluatorValidationError, "Additional properties"):
                evaluate({**good_case(), bad_key: 1})
            with self.assertRaises(EvaluatorValidationError):
                evaluate({})
            record = evaluate(good_case())
            del record["rule_pack"]
            with self.assertRaisesRegex(EvaluatorValidationError, "rule_pack"):
                validate_record(record)

        def test_every_rule_has_a_legal_outcome_and_basis_and_a_stable_decision_id(self):
            record = evaluate(good_case())
            self.assertTrue(record["rule_results"])
            self.assertEqual(record["decision_id"], evaluate(good_case())["decision_id"])
            self.assertEqual(record["llm_contract"]["authoritative_classification"], record["final_classification"])
            self.assertFalse(record["evaluator"]["network_accessed"])

        def test_mcp_parity(self):
            direct = evaluate(good_case())
            over = asyncio.run(call_tool(server, f"{domain}_evaluate", {"case": good_case()}))
            self.assertEqual(over["decision_id"], direct["decision_id"])

    Contract.__name__ = f"{domain.upper()}ContractTests"
    return Contract


def outcomes(result):
    return {r["rule_id"]: r["outcome"] for r in result["rule_results"]}

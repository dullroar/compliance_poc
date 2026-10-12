import asyncio
import hashlib
import unittest
from pathlib import Path

import yaml

from compliance_common.mcp_client import call_tool
from compliance_common.pack import EvaluatorValidationError
from compliance_mcp.hpml import evaluate_hpml, validate_hpml_decision_record, validate_hpml_rule_pack
from compliance_mcp.hpml.server import server as hpml_server

REF = {"table_date": "2026-05-28", "product": "30-year fixed", "source": "FFIEC APOR table"}


def case(**changes):
    value = dict(rate_set_date="2026-06-01", consumer_purpose=True, closed_end=True, secured_by_principal_dwelling=True,
                 lien_position="first", principal_obligation=400000, apr=7.25, apor=5.75, apor_reference=REF,
                 escrow_established_before_consummation=True, appraisal_requirements_met=True)
    value.update(changes)
    return value


def outcomes(result):
    return {r["rule_id"]: r["outcome"] for r in result["rule_results"]}


class HPMLCoverageTests(unittest.TestCase):
    def classify(self, **changes):
        return evaluate_hpml(case(**changes))["final_classification"]

    def test_first_lien_conforming_boundary(self):
        self.assertEqual(self.classify(apr=7.24), "Not HPML")   # 1.49
        self.assertEqual(self.classify(apr=7.25), "HPML")       # exactly 1.50 ("or more")
        self.assertEqual(self.classify(apr=7.26), "HPML")

    def test_decimal_arithmetic_has_no_float_error(self):
        # 0.1 + 0.2 style traps: 5.65 + 1.5 must equal 7.15 exactly.
        self.assertEqual(self.classify(apor=5.65, apr=7.15), "HPML")

    def test_first_lien_above_freddie_limit_needs_2_5(self):
        jumbo = dict(principal_obligation=900000, applicable_conforming_limit=832750, conforming_limit_source="FHFA 2026")
        self.assertEqual(self.classify(apr=7.74, **jumbo), "Not HPML")  # 1.99
        self.assertEqual(self.classify(apr=8.24, **jumbo), "Not HPML")  # 2.49
        self.assertEqual(self.classify(apr=8.25, **jumbo), "HPML")      # 2.50

    def test_amount_over_pinned_baseline_without_limit_is_unable_to_determine(self):
        result = evaluate_hpml(case(principal_obligation=900000))
        self.assertEqual(result["final_classification"], "Unable To Determine")
        self.assertEqual(result["missing_facts"][0]["field"], "applicable_conforming_limit")

    def test_amount_at_pinned_baseline_is_conforming_without_supplied_limit(self):
        result = evaluate_hpml(case(principal_obligation=832750, apr=7.25))
        self.assertEqual(result["hpml_evaluation"]["conforming_limit_source"], "pinned_baseline")
        self.assertEqual(result["final_classification"], "HPML")

    def test_subordinate_lien_needs_3_5(self):
        self.assertEqual(self.classify(lien_position="subordinate", apr=9.24), "Not HPML")  # 3.49
        self.assertEqual(self.classify(lien_position="subordinate", apr=9.25), "HPML")      # 3.50

    def test_out_of_scope_transactions_are_not_covered(self):
        for field in ("consumer_purpose", "closed_end", "secured_by_principal_dwelling"):
            with self.subTest(field=field):
                result = evaluate_hpml(case(**{field: False}))
                self.assertEqual(result["final_classification"], "Not Covered")
                self.assertEqual(result["compliance_result"], "Not Applicable")

    def test_missing_or_unsupported_inputs_never_guess(self):
        for label, changes in {"no apor": {"apor": None}, "rate set before pack window": {"rate_set_date": "2013-12-01"}}.items():
            with self.subTest(label):
                value = case(**changes)
                value = {k: v for k, v in value.items() if v is not None}
                result = evaluate_hpml(value)
                self.assertEqual(result["final_classification"], "Unable To Determine")
                self.assertEqual(result["compliance_result"], "Unable To Determine")
                self.assertTrue(result["missing_facts"])

    def test_non_hpml_has_no_obligations(self):
        result = evaluate_hpml(case(apr=6.0))
        self.assertEqual(set(outcomes(result)), {"HPML-SCOPE", "HPML-SPREAD"})
        self.assertEqual(result["compliance_result"], "Not Applicable")


class HPMLObligationTests(unittest.TestCase):
    def test_satisfied_obligations_are_compliant(self):
        result = evaluate_hpml(case())
        self.assertEqual((outcomes(result)["HPML-ESCROW"], outcomes(result)["HPML-APPRAISAL"]), ("satisfied", "satisfied"))
        self.assertEqual(result["compliance_result"], "Compliant")

    def test_missing_escrow_is_non_compliant(self):
        result = evaluate_hpml(case(escrow_established_before_consummation=False))
        self.assertEqual(outcomes(result)["HPML-ESCROW"], "not_satisfied")
        self.assertEqual(result["compliance_result"], "Non-Compliant")
        self.assertEqual(result["final_classification"], "HPML")

    def test_unknown_obligation_facts_are_a_potential_issue(self):
        value = case()
        del value["appraisal_requirements_met"]
        result = evaluate_hpml(value)
        self.assertEqual(outcomes(result)["HPML-APPRAISAL"], "unable_to_determine")
        self.assertEqual(result["compliance_result"], "Potential Issue")

    def test_escrow_exemptions_and_subordinate_lien(self):
        for kind in ("cooperative", "initial_construction", "bridge_loan_12_months_or_less", "reverse_mortgage", "pace"):
            result = evaluate_hpml(case(escrow_exemption=kind, escrow_established_before_consummation=False))
            self.assertEqual(outcomes(result)["HPML-ESCROW"], "does_not_apply", kind)
        documented = evaluate_hpml(case(escrow_exemption_documented=True, escrow_established_before_consummation=False))
        self.assertEqual(outcomes(documented)["HPML-ESCROW"], "does_not_apply")
        sub = evaluate_hpml(case(lien_position="subordinate", apr=9.25, escrow_established_before_consummation=False))
        self.assertEqual(outcomes(sub)["HPML-ESCROW"], "does_not_apply")

    def test_documented_appraisal_exemption(self):
        result = evaluate_hpml(case(appraisal_requirements_met=False, appraisal_exemption_documented=True))
        self.assertEqual(outcomes(result)["HPML-APPRAISAL"], "does_not_apply")
        self.assertEqual(result["compliance_result"], "Compliant")


class HPMLContractTests(unittest.TestCase):
    def test_pack_sources_and_contracts_validate(self):
        validate_hpml_rule_pack()
        root = Path(__file__).resolve().parents[1]
        manifest = yaml.safe_load((root / "compliance_mcp/hpml/pack/manifest.yaml").read_text(encoding="utf-8"))
        for source in manifest["sources"]:
            with self.subTest(source=source["id"]):
                self.assertEqual(hashlib.sha256((root / source["local_path"]).read_bytes()).hexdigest(), source["sha256"])

    def test_spread_thresholds_match_the_pinned_regulation_text(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / "compliance_mcp/hpml/pack/sources/12-cfr-1026-35.xml").read_text(encoding="utf-8")
        for needle in ("By 1.5 or more percentage points", "By 2.5 or more percentage points", "By 3.5 or more percentage points"):
            self.assertIn(needle, text)

    def test_schema_rejects_malformed_input_and_output(self):
        with self.assertRaisesRegex(EvaluatorValidationError, "Additional properties"):
            evaluate_hpml(case(surprise=1))
        with self.assertRaisesRegex(EvaluatorValidationError, "required"):
            evaluate_hpml({"rate_set_date": "2026-06-01"})
        record = evaluate_hpml(case())
        del record["rule_pack"]
        with self.assertRaisesRegex(EvaluatorValidationError, "rule_pack"):
            validate_hpml_decision_record(record)

    def test_replay_and_mcp_parity(self):
        value = case()
        direct = evaluate_hpml(value)
        self.assertEqual(direct["decision_id"], evaluate_hpml(dict(value))["decision_id"])
        over_mcp = asyncio.run(call_tool(hpml_server, "hpml_evaluate", {"case": value}))
        self.assertEqual(over_mcp["decision_id"], direct["decision_id"])


if __name__ == "__main__":
    unittest.main()

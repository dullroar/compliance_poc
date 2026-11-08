"""The every-regime-fails synthetic loan (tests/fixtures/loan_every_regime_fails.json).

sample_loan.json produces findings in only four roles (hmda, ecoa, vmi and the auditor), so a live run on it never asks a model to write
an examiner paragraph for ybs, hpml, trid, fzd or hvcre. This fixture is the same synthetic loan with one realistic fault per regime, so
every domain role and the auditor has at least one finding. Synthetic data only; the evaluators, not the fixture, decide each result.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from compliance_common.templates import examiner
from live_parity_common import PHASES, ScriptedProvider, parts, role_failures, run_registry
from test_auditor_evaluator import assembled

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/loan_every_regime_fails.json"
DOMAINS = ("ybs", "hpml", "trid", "hmda", "ecoa", "vmi", "fzd", "hvcre")


def load() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def decision_for(key: str, loan: dict) -> dict:
    _, evaluate, adapter = parts(key)
    canonical, _ = adapter.tool_arguments(loan)
    return evaluate(canonical["case"])


class FixtureTests(unittest.TestCase):
    def test_every_domain_role_has_at_least_one_finding_that_renders_within_its_limits(self):
        loan = load()
        for key in DOMAINS:
            with self.subTest(role=key):
                paragraphs = examiner.render(decision_for(key, loan), key)            # strict: raises if a paragraph cannot fit
                self.assertGreaterEqual(len(paragraphs), 1)

    def test_the_auditor_has_a_cross_regime_finding_on_the_fixture(self):
        loan = load()
        decision = decision_for("auditor", {"loan_data": loan, "agent_results": assembled(loan)})
        self.assertGreaterEqual(len(examiner.render(decision, "auditor")), 1)

    def test_the_fixture_is_the_sample_loan_with_changes_only_in_the_regime_sections(self):
        sample = json.loads((ROOT / "sample_loan.json").read_text(encoding="utf-8"))
        changed = {k for k in sample if sample[k] != load().get(k)}
        self.assertEqual(changed, {"hpml_case", "trid_case", "ybs_case", "fzd_case", "hvcre_case"})
        self.assertEqual(set(load()), set(sample))

    def test_a_full_offline_registry_run_passes_every_role_in_both_phases(self):
        for phase in PHASES:
            with self.subTest(phase=phase):
                out = run_registry(ScriptedProvider().backend(), phase, payload=load())
                self.assertTrue(out["summary"]["ok"], out["summary"]["failed"])
                for record in out["records"]:
                    self.assertEqual(role_failures(record), [], f"{record['role']}/{phase}")
                    if record["role"] in DOMAINS:
                        sources = record["paragraph_sources"]
                        self.assertGreaterEqual(sum(sources.values()), 1, f"{record['role']}: no examiner paragraph was asked of the model")
                        self.assertEqual(set(sources), {"model"}, f"{record['role']}: {sources}")


if __name__ == "__main__":
    unittest.main()

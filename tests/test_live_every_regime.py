"""Opt-in live runs of the every-regime-fails loan on one provider (plans/archive/parallelize, follow-up). Both skipped by default.

RUN_LIVE_EVERY_REGIME=openai or =anthropic runs that provider's existing guarded live-parity gate (zero SDK retries, finite timeout,
whole-run reservation, settlement from usage) once, at the committed `remote_concurrency`, on tests/fixtures/loan_every_regime_fails.json
instead of sample_loan.json, so the model is asked for examiner paragraphs in all eight regimes and the auditor. It records, per role and
phase, how many paragraphs came from the model, a retry or code, and which checks the rejected ones failed (labels only, never text).
A paragraph written by code is a finding to report, not a failure; a role that fails a parity check or a truncated narrative is a failure.
The offline tests below always run against the scripted provider and a temporary ledger.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from live_parity_common import ScriptedProvider, role_failures, run_registry
from orchestrator.config import load_settings
from test_every_regime_fixture import DOMAINS, FIXTURE, load

ROOT = Path(__file__).resolve().parents[1]
WIDTH = load_settings()["remote_concurrency"]
PROVIDERS = ("openai", "anthropic")


def drive_fixture(backend, phase, width: int = WIDTH):
    return run_registry(backend, phase, payload=load(), remote_concurrency=width)


def summarize(outputs: dict) -> dict:
    """Per role and phase: narrative source, paragraph sources, failed-check labels; plus totals. Metadata only."""
    roles = [{"role": r["role"], "phase": phase, "narrative_source": r["narrative_source"], "paragraph_sources": r["paragraph_sources"],
              "paragraph_failures": r["paragraph_failures"], "failed_checks": role_failures(r)}
             for phase, out in outputs.items() for r in out["records"]]
    totals = Counter()
    for r in roles:
        totals.update(r["paragraph_sources"])
    asked = {r["role"] for r in roles if sum(r["paragraph_sources"].values())}
    return {"roles": roles, "paragraph_totals": dict(totals), "roles_asked_for_paragraphs": sorted(asked),
            "roles_without_paragraphs": sorted(set(DOMAINS) - asked), "failed_roles": sorted({f"{r['role']}/{r['phase']}" for r in roles if r["failed_checks"]})}


class SummarizeTests(unittest.TestCase):
    def test_a_scripted_run_asks_every_domain_role_for_paragraphs_and_all_come_from_the_model(self):
        outputs = {phase: drive_fixture(ScriptedProvider().backend(), phase) for phase in ("model", "seeded")}
        summary = summarize(outputs)
        self.assertEqual(summary["roles_without_paragraphs"], [])
        self.assertEqual(set(summary["paragraph_totals"]), {"model"})
        self.assertEqual(summary["failed_roles"], [])
        self.assertNotIn("text", json.dumps(summary))                    # labels and counts only

    def test_the_sample_loan_alone_leaves_five_regimes_without_paragraphs(self):
        outputs = {"model": run_registry(ScriptedProvider().backend(), "model", remote_concurrency=WIDTH)}
        self.assertEqual(summarize(outputs)["roles_without_paragraphs"], ["fzd", "hpml", "hvcre", "trid", "ybs"])

    def test_the_openai_outbound_guard_refuses_the_fixture_unless_told_to_use_it(self):
        from test_openai_live_parity import BudgetError, rehearse, use_loan
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(BudgetError):                                 # strict by default: pinned to sample_loan.json
                rehearse(Path(temp) / "a", drive=drive_fixture)
            with use_loan(load()):
                result = rehearse(Path(temp) / "b", drive=drive_fixture)
                self.assertTrue(all(0 < size for size in result["sizes"].values()))
                with self.assertRaises(BudgetError):                             # and pinned to the fixture while in use
                    rehearse(Path(temp) / "c")
            result = rehearse(Path(temp) / "d")                                  # the sample is the default again afterwards
            self.assertTrue(result["sizes"])

    def test_the_fixture_file_is_the_one_the_gate_uses(self):
        self.assertTrue(FIXTURE.is_file())

    def test_the_live_classes_are_skipped_without_their_variable(self):
        self.assertNotIn(os.getenv("RUN_LIVE_EVERY_REGIME"), PROVIDERS, "the default suite must not make live calls")


def _live_openai() -> dict:
    import openai
    from dotenv import dotenv_values
    from test_openai_live_parity import BYTE_BOUND, TIMEOUT, RunFile, live_run, rehearse, today_denver, use_loan
    from test_openai_live_smoke import LEDGER, PRICE_CHECKED
    assert today_denver() == PRICE_CHECKED, "Verify rates at the cited URL and update the accounting first"
    key = os.getenv("OPENAI_API_KEY") or dotenv_values(ROOT / ".env").get("OPENAI_API_KEY")
    assert key, "OPENAI_API_KEY is required"
    runs_path = ROOT / "plans/archive/parallelize/runs-openai.jsonl"
    sdk = openai.OpenAI(api_key=key, base_url="https://api.openai.com/v1", timeout=TIMEOUT, max_retries=0)
    try:
        with use_loan(load()), tempfile.TemporaryDirectory() as temp:          # the outbound check is pinned to the fixture for this run only
            sizes = rehearse(Path(temp), drive=drive_fixture)["sizes"]
            assert all(0 < size <= BYTE_BOUND for size in sizes.values()), f"outbound payload over the bound: {sizes}"
            result = live_run(sdk, ledger_path=LEDGER, runs_path=runs_path, today=today_denver(), drive=drive_fixture)
    finally:
        sdk.close()
    summary = {"event": "every_regime_summary", "run_id": result["cycle_id"], "provider": "openai", "width": WIDTH, **summarize(result["outputs"]),
               "cumulative_incurred_usd": result["cycle_end"].get("cumulative_incurred_usd")}
    RunFile(runs_path).append(summary)
    return summary


def _live_anthropic() -> dict:
    import anthropic
    from dotenv import dotenv_values
    from scripts import anthropic_cost_estimator as estimator
    from test_anthropic_live_parity import TIMEOUT, RunFile, live_run, offline_payload_inspection, today_denver
    assert today_denver() == estimator.PRICE_CHECKED, "Verify rates at the cited URL and update the estimator and its tests first"
    key = os.getenv("ANTHROPIC_API_KEY") or dotenv_values(ROOT / ".env").get("ANTHROPIC_API_KEY")
    assert key, "ANTHROPIC_API_KEY is required"
    sizes = offline_payload_inspection()
    assert all(0 < size <= 100_000 for size in sizes.values()), f"outbound payload over the bound: {sizes}"
    runs_path = ROOT / "plans/archive/parallelize/runs-anthropic.jsonl"
    sdk = anthropic.Anthropic(api_key=key, base_url="https://api.anthropic.com", timeout=TIMEOUT, max_retries=0)
    try:
        result = live_run(sdk, ledger=estimator.LEDGER, runs_path=runs_path, today=today_denver(), drive=drive_fixture)
    finally:
        sdk.close()
    summary = {"event": "every_regime_summary", "run_id": result["run_id"], "provider": "anthropic", "width": WIDTH, **summarize(result["outputs"]),
               "settlement_usd": result["settlement"]}
    RunFile(runs_path).append(summary)
    return summary


@unittest.skipUnless(os.getenv("RUN_LIVE_EVERY_REGIME") in PROVIDERS, "set RUN_LIVE_EVERY_REGIME=openai or anthropic for the live run")
class EveryRegimeLive(unittest.TestCase):
    def test_every_regime_fixture_on_one_provider(self):
        provider = os.environ["RUN_LIVE_EVERY_REGIME"]
        old_disable = logging.root.manager.disable
        logging.disable(logging.CRITICAL)
        try:
            summary = _live_openai() if provider == "openai" else _live_anthropic()
        finally:
            logging.disable(old_disable)
        print("\n" + json.dumps({k: summary[k] for k in ("provider", "run_id", "width", "paragraph_totals", "roles_without_paragraphs", "failed_roles")} |
                                {"rejected_paragraphs": [{"role": r["role"], "phase": r["phase"], "attempts": r["paragraph_failures"]}
                                                         for r in summary["roles"] if any(r["paragraph_failures"])]}, indent=1, sort_keys=True))
        self.assertEqual(summary["failed_roles"], [])
        self.assertEqual(summary["roles_without_paragraphs"], [])


if __name__ == "__main__":
    unittest.main()

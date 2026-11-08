"""Opt-in live check of the committed remote width on gpt-6-luna (plans/parallelize, follow-up). Skipped unless RUN_LIVE_OPENAI_PARALLEL=1.

One run of the OpenAI live-parity gate (tests/test_openai_live_parity.py: guarded client, zero SDK retries, finite timeout, whole-cycle
reservation in the shared ledger) at the committed `remote_concurrency`, on the synthetic sample_loan.json case through the production
batch path. It answers two questions Anthropic alone could not: does the committed width draw rate limits from OpenAI, and does the
bounded narrative role finish without truncation on OpenAI. Run metadata (timings, counts, labels; never bodies) is appended to
plans/parallelize/runs-openai.jsonl. The offline tests below always run: they drive the same function against the scripted provider
and a temporary ledger.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import unittest
from pathlib import Path

import httpx
import openai

from live_parity_common import ScriptedProvider, registry_roles, role_failures, run_registry
from orchestrator.config import load_settings
from test_openai_live_parity import BYTE_BOUND, TIMEOUT, Ledger, RunFile, live_run, rehearse, today_denver
from test_openai_live_smoke import LEDGER, PRICE_CHECKED

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "plans/parallelize/runs-openai.jsonl"
RATE_LIMIT_OUTCOMES = frozenset({"RateLimitError"})
KEY = "sk-OFFLINE-SENTINEL-0000"


COMMITTED_WIDTH = load_settings()["remote_concurrency"]
COMMAND = "RUN_LIVE_OPENAI_PARALLEL=1 python3 -m unittest discover -s tests -p test_openai_live_parallel.py -v"


def width_errors(cycle_rows: list[dict], run_rows: list[dict], outputs: dict) -> dict:
    """Rate limits, other request-level errors and role failures of one run, from its ledger rows and records (labels and counts only).
    A narrative the guard rewrote or a failed quality check is reported by the parity checks, not counted here as a width error."""
    outcomes = [r.get("outcome") for r in cycle_rows if r.get("event") == "request_outcome"]
    return {"rate_limits": sum(1 for o in outcomes if o in RATE_LIMIT_OUTCOMES),
            "other_request_errors": sorted({o for o in outcomes if o not in ("response", *RATE_LIMIT_OUTCOMES)}),
            "refusals": sum(1 for r in run_rows if r.get("event") == "refusal"),
            "role_failures": sorted({f"{r['role']}/{r['phase']}" for out in outputs.values() for r in out["records"] if r.get("failure")})}


def has_error(errors: dict) -> bool:
    return bool(errors["rate_limits"] or errors["other_request_errors"] or errors["refusals"] or errors["role_failures"])


def phase_row(out: dict) -> dict:
    summary = out["summary"]
    timing = summary["timing"]
    return {"ok": summary["ok"], "failed_roles": sorted(summary["failed"]), "domain_phase_seconds": timing["domain_phase_seconds"],
            "auditor_seconds": timing["auditor_seconds"], "narrative_seconds": timing["narrative_seconds"], "total_seconds": timing["total_seconds"],
            "role_seconds": {r["role"]: r["elapsed_seconds"] for r in out["records"]}}


def measure_width(sdk, *, ledger_path: Path | str, runs_path: Path | str, today: str, width: int = COMMITTED_WIDTH, live=live_run) -> dict:
    """One full registry run (both phases) at `width`, through the OpenAI live-parity gate: reservation first, settled from usage."""
    result = live(sdk, ledger_path=ledger_path, runs_path=runs_path, today=today,
                  drive=lambda backend, phase: run_registry(backend, phase, remote_concurrency=width))
    with Ledger(ledger_path).locked() as (_, rows):
        cycle_rows = [r for r in rows if r.get("cycle_id") == result["cycle_id"]]
    records = [r for out in result["outputs"].values() for r in out["records"]]
    run_rows = RunFile(runs_path).rows(result["cycle_id"])
    row = {"event": "width_measurement", "run_id": result["cycle_id"], "width": width, "errors": width_errors(cycle_rows, run_rows, result["outputs"]),
           "requests": sum(1 for r in run_rows if r.get("event") == "request_start"),
           "narratives_from_model": sum(1 for r in records if r["narrative_source"] in ("model", "model_retry") and not role_failures(r)),
           "truncated_roles": sorted(f"{r['role']}/{r['phase']}" for r in records if "not_truncated" in role_failures(r)),
           "cumulative_incurred_usd": result["cycle_end"].get("cumulative_incurred_usd"),
           "unknown_requests": result["table"]["per_run"]["unknown_requests"],
           "phases": {phase: phase_row(out) for phase, out in result["outputs"].items()}}
    RunFile(runs_path).append(row)
    return row


class RateLimited(ScriptedProvider):
    """Answers 429 from the `after`-th request on (the width under test is the one running then)."""

    def __init__(self, after, **kwargs):
        super().__init__(**kwargs)
        self.after = after

    def handler(self, request):
        if len(self.requests) >= self.after:
            return httpx.Response(429, json={"error": {"message": "synthetic", "type": "rate_limit_exceeded", "code": "rate_limit_exceeded"}})
        return super().handler(request)


def sdk_for(script):
    return openai.OpenAI(api_key=KEY, max_retries=0, timeout=5.0, http_client=httpx.Client(transport=httpx.MockTransport(script.handler)))


class MeasureWidthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ledger = Path(self.temp.name) / "ledger.jsonl"
        Ledger(self.ledger).start_cycle("rehearsal-prior", 1)
        Ledger(self.ledger).end_cycle("rehearsal-prior", {}, 0)
        self.runs_path = Path(self.temp.name) / "runs.jsonl"

    def measure(self, script, width):
        script.caps = False
        live = lambda sdk, **kw: live_run(sdk, observer=script.begin_role, **kw)
        return measure_width(sdk_for(script), ledger_path=self.ledger, runs_path=self.runs_path, today=PRICE_CHECKED, width=width, live=live)

    def test_the_committed_width_is_the_remote_width_in_agents_yaml(self):
        self.assertEqual(COMMITTED_WIDTH, load_settings()["remote_concurrency"])

    def test_a_clean_run_at_width_8_records_widths_timing_and_no_errors(self):
        result = self.measure(ScriptedProvider(provider="openai"), 8)
        self.assertEqual(result["width"], 8)
        self.assertFalse(has_error(result["errors"]), result["errors"])
        self.assertEqual(sorted(result["phases"]), ["model", "seeded"])
        for phase in result["phases"].values():
            self.assertTrue(phase["ok"])
            self.assertGreater(phase["domain_phase_seconds"], 0)
            self.assertGreaterEqual(phase["total_seconds"], phase["domain_phase_seconds"])
        self.assertEqual(result["narratives_from_model"], 2 * len(registry_roles()))
        self.assertEqual(result["truncated_roles"], [])
        self.assertGreaterEqual(result["requests"], 2 * len(registry_roles()))          # at least one request per role and phase
        recorded = [r for r in RunFile(self.runs_path).rows() if r["event"] == "width_measurement"]
        self.assertEqual([r["width"] for r in recorded], [8])
        with Ledger(self.ledger).locked() as (_, rows):
            cycles = [r for r in rows if r.get("event") == "cycle_reservation"]
        self.assertEqual(len(cycles), 2)                                 # the prior rehearsal row and exactly one new reservation

    def test_a_rate_limited_run_is_reported_as_an_error_of_the_width(self):
        result = self.measure(RateLimited(after=10, provider="openai"), 8)
        self.assertGreater(result["errors"]["rate_limits"], 0)
        self.assertTrue(has_error(result["errors"]))

    def test_the_live_class_is_skipped_without_its_own_variable(self):
        self.assertNotEqual(os.getenv("RUN_LIVE_OPENAI_PARALLEL"), "1", "the default suite must not make live calls")


@unittest.skipUnless(os.getenv("RUN_LIVE_OPENAI_PARALLEL") == "1", "set RUN_LIVE_OPENAI_PARALLEL=1 for the live OpenAI width check")
class OpenAILiveParallel(unittest.TestCase):
    def test_committed_width_has_no_errors_and_no_truncation(self):
        from dotenv import dotenv_values

        self.assertEqual(today_denver(), PRICE_CHECKED, "Verify rates at the cited URL and update the accounting first")
        key = os.getenv("OPENAI_API_KEY") or dotenv_values(ROOT / ".env").get("OPENAI_API_KEY")
        self.assertTrue(key, "OPENAI_API_KEY is required")
        with tempfile.TemporaryDirectory() as temp:
            rehearsal = rehearse(Path(temp))
        self.assertTrue(all(0 < size <= BYTE_BOUND for size in rehearsal["sizes"].values()), f"outbound payload over the bound: {rehearsal['sizes']}")
        old_disable = logging.root.manager.disable
        logging.disable(logging.CRITICAL)
        sdk = openai.OpenAI(api_key=key, base_url="https://api.openai.com/v1", timeout=TIMEOUT, max_retries=0)
        try:
            row = measure_width(sdk, ledger_path=LEDGER, runs_path=RUNS, today=today_denver())
        finally:
            sdk.close()
            logging.disable(old_disable)
        print("\n" + json.dumps({k: row[k] for k in ("run_id", "width", "errors", "requests", "narratives_from_model", "truncated_roles",
                                                       "cumulative_incurred_usd", "unknown_requests")} | {"phases": {
            p: {k: v[k] for k in ("ok", "domain_phase_seconds", "auditor_seconds", "narrative_seconds", "total_seconds")}
            for p, v in row["phases"].items()}}, indent=1, sort_keys=True))
        self.assertFalse(has_error(row["errors"]), row["errors"])
        self.assertEqual(row["truncated_roles"], [])
        self.assertEqual(row["unknown_requests"], 0, "provider usage was not fully reported; reservation retained")


if __name__ == "__main__":
    unittest.main()

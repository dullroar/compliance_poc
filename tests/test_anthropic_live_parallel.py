"""Opt-in live width ramp on claude-haiku-5-5 (plans/parallelize, step 03). Skipped unless RUN_LIVE_ANTHROPIC_PARALLEL=1.

The live-parity run (tests/test_anthropic_live_parity.py: guarded client, reservation, settlement) is repeated at remote width 1,
then 2, 4 and 8, one run each, on the synthetic sample_loan.json case through the production batch path. The ramp stops at the
first width that shows a rate limit or any other non-cost error, and before the plan's spend bound could be passed. Run metadata
(timings, counts, labels, money; never bodies) is appended to plans/parallelize/runs-anthropic.jsonl beside the live-parity rows.
The offline tests below always run: they drive the same `measure` function against the scripted provider and a temporary ledger.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import anthropic
import httpx

from live_parity_common import ScriptedProvider, run_registry
from scripts import anthropic_cost_estimator as estimator
from test_anthropic_live_parity import MODEL, TIMEOUT, RunFile, live_run, offline_payload_inspection, today_denver

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "plans/parallelize/runs-anthropic.jsonl"
WIDTHS = (1, 2, 4, 8)
PLAN_SPEND_BOUND = Decimal("0.50")            # spec, delegated authority: at most USD 0.50 of actual spend for this plan
FIRST_RUN_ESTIMATE = Decimal("0.07")          # one full Haiku registry run (both phases) cost about this in the archive
HEADROOM = Decimal("1.5")                     # the next run must fit with 50% to spare over the dearest run so far
COMMAND = "RUN_LIVE_ANTHROPIC_PARALLEL=1 python3 -m unittest discover -s tests -p test_anthropic_live_parallel.py -v"
RATE_LIMIT_OUTCOMES = frozenset({"RateLimitError"})


def next_run_allowed(spent: Decimal, costs: list[Decimal], bound: Decimal = PLAN_SPEND_BOUND, first: Decimal = FIRST_RUN_ESTIMATE) -> bool:
    """Whether one more run fits: spend so far plus the dearest earlier run (or the archive estimate) with headroom stays within the bound."""
    return spent + max(costs, default=first) * HEADROOM <= bound


def width_errors(rows: list[dict], outputs: dict) -> dict:
    """Rate limits, other request-level errors and role failures of one run, from its metadata rows and records (labels and counts only).
    A narrative the guard rewrote or a failed quality check is not an error of the width; it is reported by the live-parity checks."""
    outcomes = [r.get("outcome") for r in rows if r.get("event") == "request_outcome"]
    return {"rate_limits": sum(1 for o in outcomes if o in RATE_LIMIT_OUTCOMES),
            "other_request_errors": sorted({o for o in outcomes if o not in ("response", *RATE_LIMIT_OUTCOMES)}),
            "refusals": sum(1 for r in rows if r.get("event") == "refusal"),
            "role_failures": sorted({f"{r['role']}/{r['phase']}" for out in outputs.values() for r in out["records"] if r.get("failure")})}


def has_error(errors: dict) -> bool:
    return bool(errors["rate_limits"] or errors["other_request_errors"] or errors["refusals"] or errors["role_failures"])


def phase_row(out: dict) -> dict:
    summary = out["summary"]
    timing = summary["timing"]
    return {"ok": summary["ok"], "failed_roles": sorted(summary["failed"]), "domain_phase_seconds": timing["domain_phase_seconds"],
            "auditor_seconds": timing["auditor_seconds"], "narrative_seconds": timing["narrative_seconds"], "total_seconds": timing["total_seconds"],
            "cpu_seconds": timing["cpu_seconds"], "role_seconds": {r["role"]: r["elapsed_seconds"] for r in out["records"]}}


def measure(sdk, *, ledger: Path | str, runs_path: Path | str, today: str, widths: tuple[int, ...] = WIDTHS, bound: Decimal = PLAN_SPEND_BOUND,
            first: Decimal = FIRST_RUN_ESTIMATE, live=live_run) -> dict:
    """Run the registry once per width, climbing while the previous width was clean and the spend bound allows another run."""
    runs, rows_out, spent, costs, stopped = RunFile(runs_path), [], Decimal(0), [], None
    for width in widths:
        if not next_run_allowed(spent, costs, bound, first):
            stopped = {"before_width": width, "reason": "spend bound", "spent_usd": str(spent), "bound_usd": str(bound)}
            break
        drive = (lambda backend, phase: run_registry(backend, phase)) if width == 1 else \
                (lambda backend, phase, w=width: run_registry(backend, phase, remote_concurrency=w))
        try:
            result = live(sdk, ledger=ledger, runs_path=runs_path, today=today, drive=drive)
        except Exception as exc:                      # the live run settled or retained its reservation before re-raising
            stopped = {"at_width": width, "reason": "run raised", "error": type(exc).__name__}
            runs.append({"event": "width_stopped", **stopped})
            break
        rows = runs.rows(result["run_id"])
        errors = width_errors(rows, result["outputs"])
        cost = None if result["settlement"] is None else Decimal(result["settlement"])
        row = {"event": "width_measurement", "width": width, "run_id": result["run_id"], "requests": sum(1 for r in rows if r["event"] == "request_start"),
               "settlement_usd": result["settlement"], "reservation_retained": cost is None, "errors": errors,
               "phases": {phase: phase_row(out) for phase, out in result["outputs"].items()}}
        runs.append(row)
        rows_out.append(row)
        if cost is not None:
            spent += cost
            costs.append(cost)
        if cost is None or has_error(errors):          # a failed request has unknown cost, so a rate limit also retains the reservation
            stopped = {"at_width": width, "reason": "error at this width" if has_error(errors) else "usage unknown; reservation retained",
                       "errors": errors, "reservation_retained": cost is None}
            runs.append({"event": "width_stopped", **stopped})
            break
    return {"widths": rows_out, "spent_usd": str(spent), "stopped": stopped}


def change_table(measured: list[dict]) -> list[dict]:
    """Per width and phase, wall time and the percentage change against width 1 (negative = faster)."""
    if not measured or measured[0]["width"] != 1:
        return []
    base = measured[0]["phases"]
    table = []
    for row in measured:
        for phase, p in row["phases"].items():
            b = base[phase]
            table.append({"width": row["width"], "phase": phase,
                          **{k: p[k] for k in ("domain_phase_seconds", "total_seconds")},
                          "domain_change_pct": round(100 * (p["domain_phase_seconds"] - b["domain_phase_seconds"]) / b["domain_phase_seconds"], 1),
                          "total_change_pct": round(100 * (p["total_seconds"] - b["total_seconds"]) / b["total_seconds"], 1)})
    return table


# --- offline tests (always run) ----------------------------------------------------------------------------------------------
KEY = "sk-ant-OFFLINE-SENTINEL-0000"


class RateLimitedAfter(ScriptedProvider):
    """Answers 429 once `after` requests have been served in total (the width that trips the limit is the one running then)."""

    def __init__(self, after, **kwargs):
        super().__init__(**kwargs)
        self.after = after

    def handler(self, request):
        if len(self.requests) >= self.after:
            return httpx.Response(429, json={"type": "error", "error": {"type": "rate_limit_error", "message": "synthetic"}})
        return super().handler(request)


def sdk_for(script):
    return anthropic.Anthropic(api_key=KEY, max_retries=0, timeout=5.0, http_client=httpx.Client(transport=httpx.MockTransport(script.handler)))


class MeasureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ledger = Path(self.temp.name) / "ledger.jsonl"
        self.ledger.write_text(json.dumps({"event": "baseline_unknown", "version": 1}) + "\n")
        estimator.baseline(self.ledger, "0", "owner-confirmed")
        self.runs_path = Path(self.temp.name) / "runs.jsonl"
        self.today = estimator.PRICE_CHECKED

    def rows(self):
        return [json.loads(line) for line in self.ledger.read_text().splitlines()]

    def measure(self, script, **kwargs):
        script.caps = False
        live = lambda sdk, **kw: live_run(sdk, observer=script.begin_role, **kw)
        return measure(sdk_for(script), ledger=self.ledger, runs_path=self.runs_path, today=self.today, live=live, **kwargs)

    def test_the_ramp_climbs_one_width_at_a_time_with_one_reservation_and_settlement_each(self):
        script = ScriptedProvider()
        result = self.measure(script, widths=(1, 2, 4), bound=Decimal(1))
        self.assertEqual([w["width"] for w in result["widths"]], [1, 2, 4])
        self.assertIsNone(result["stopped"])
        events = [r["event"] for r in self.rows()]
        self.assertEqual((events.count("reservation"), events.count("settlement")), (3, 3))
        for row in result["widths"]:
            self.assertEqual(set(row["phases"]), {"model", "seeded"})
            self.assertFalse(has_error(row["errors"]))
            for phase in row["phases"].values():
                self.assertTrue(phase["ok"])
                self.assertGreater(phase["domain_phase_seconds"], 0)
                self.assertGreaterEqual(phase["total_seconds"], phase["domain_phase_seconds"])
                self.assertEqual(set(phase["cpu_seconds"]), {"self", "children"})
        recorded = [r for r in RunFile(self.runs_path).rows() if r["event"] == "width_measurement"]
        self.assertEqual([r["width"] for r in recorded], [1, 2, 4])
        self.assertEqual(len(change_table(result["widths"])), 6)
        self.assertEqual(change_table(result["widths"])[0]["domain_change_pct"], 0.0)

    def test_the_ramp_stops_at_the_first_width_that_is_rate_limited_and_records_it(self):
        first = self.measure(ScriptedProvider(), widths=(1,), bound=Decimal(1))
        per_run = first["widths"][0]["requests"]
        script = RateLimitedAfter(after=per_run + per_run // 2)                    # the second run (width 2) is cut off part way
        self.ledger.write_text(json.dumps({"event": "baseline_unknown", "version": 1}) + "\n")
        estimator.baseline(self.ledger, "0", "owner-confirmed")
        result = self.measure(script, widths=(1, 2, 4, 8), bound=Decimal(1))
        self.assertEqual([w["width"] for w in result["widths"]], [1, 2])
        self.assertEqual(result["stopped"]["at_width"], 2)
        self.assertGreater(result["widths"][1]["errors"]["rate_limits"], 0)
        self.assertFalse(has_error(result["widths"][0]["errors"]))
        self.assertEqual(sum(1 for r in self.rows() if r["event"] == "reservation"), 2)      # width 4 and 8 never reserved or called
        self.assertTrue(any(r["event"] == "width_stopped" for r in RunFile(self.runs_path).rows()))

    def test_the_ramp_does_not_start_a_run_the_spend_bound_cannot_cover(self):
        script = ScriptedProvider()
        result = self.measure(script, widths=(1, 2), bound=Decimal("0.01"), first=Decimal("0.07"))
        self.assertEqual((result["widths"], result["stopped"]["reason"]), ([], "spend bound"))
        self.assertEqual(script.requests, [])
        self.assertEqual([r["event"] for r in self.rows()], ["baseline_unknown", "baseline_verified"])      # nothing was even reserved

    def test_the_bound_rule_uses_the_dearest_run_so_far_with_headroom(self):
        bound = Decimal("0.50")
        self.assertTrue(next_run_allowed(Decimal(0), [], bound))                                     # 0.07 x 1.5 fits
        self.assertTrue(next_run_allowed(Decimal("0.28"), [Decimal("0.07")] * 4, bound))              # 0.28 + 0.105 fits
        self.assertFalse(next_run_allowed(Decimal("0.40"), [Decimal("0.08")] * 5, bound))             # 0.40 + 0.12 does not
        self.assertFalse(next_run_allowed(Decimal("0.30"), [Decimal("0.15"), Decimal("0.15")], bound))     # a dear run raises the estimate

    def test_the_live_class_is_skipped_without_its_own_variable(self):
        self.assertNotEqual(os.getenv("RUN_LIVE_ANTHROPIC_PARALLEL"), "1", "the default suite must not make live calls")


@unittest.skipUnless(os.getenv("RUN_LIVE_ANTHROPIC_PARALLEL") == "1", "set RUN_LIVE_ANTHROPIC_PARALLEL=1 for the live width ramp")
class AnthropicLiveParallel(unittest.TestCase):
    def test_width_ramp_1_2_4_8(self):
        from dotenv import dotenv_values

        self.assertEqual(today_denver(), estimator.PRICE_CHECKED, "Verify rates at the cited URL and update the estimator and its tests first")
        key = os.getenv("ANTHROPIC_API_KEY") or dotenv_values(ROOT / ".env").get("ANTHROPIC_API_KEY")
        self.assertTrue(key, "ANTHROPIC_API_KEY is required")
        sizes = offline_payload_inspection()
        self.assertTrue(all(0 < size <= 100_000 for size in sizes.values()), f"outbound payload over the bound: {sizes}")
        old_disable = logging.root.manager.disable
        logging.disable(logging.CRITICAL)
        sdk = anthropic.Anthropic(api_key=key, base_url="https://api.anthropic.com", timeout=TIMEOUT, max_retries=0)
        try:
            result = measure(sdk, ledger=estimator.LEDGER, runs_path=RUNS, today=today_denver())
        finally:
            sdk.close()
            logging.disable(old_disable)
        print("\n" + json.dumps({"spent_usd": result["spent_usd"], "stopped": result["stopped"], "table": change_table(result["widths"])}, indent=1, sort_keys=True))
        self.assertTrue(result["widths"], "no width was run")
        self.assertLessEqual(Decimal(result["spent_usd"]), PLAN_SPEND_BOUND)


if __name__ == "__main__":
    unittest.main()

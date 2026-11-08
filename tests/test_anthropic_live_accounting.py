"""Offline proofs for the guarded Anthropic live run: caps, zero retries, durable accounting. No network, no credentials."""
import contextvars
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest import mock
from decimal import Decimal
from pathlib import Path

import anthropic
import httpx

from agent_prompts import AGENTS
from agents.backends import Backend
from live_parity_common import PHASES, ScriptedProvider, registry_roles, role_failures, run_registry, worst_case_requests, worst_case_table
from scripts import anthropic_cost_estimator as estimator
from test_agent_parity import SAMPLE
from test_anthropic_live_parity import (ALLOWED_MODELS, BYTE_BOUND, MAX_TOKENS, MODEL, RUN_LIMIT, GuardedAnthropic, GuardRefusal, RunFile, aggregate, cost_table,
                                        flag_truncation, live_run, offline_payload_inspection, read_usage, request_bytes, usage_cost)

ROOT = Path(__file__).resolve().parents[1]
KEY = "sk-ant-OFFLINE-SENTINEL-0000"
TODAY = estimator.PRICE_CHECKED
ROLES = registry_roles()


class NoUsage(ScriptedProvider):
    """Serves responses whose usage block is missing, malformed or non-standard."""
    variant = "missing"

    def handler(self, request):
        response = super().handler(request)
        body = json.loads(response.content)
        if self.variant == "missing":
            body.pop("usage", None)
        elif self.variant == "negative":
            body["usage"]["output_tokens"] = -1
        elif self.variant == "text":
            body["usage"]["input_tokens"] = "12"
        elif self.variant == "priority":
            body["usage"]["service_tier"] = "priority"
        return httpx.Response(200, json=body)


class Failing(ScriptedProvider):
    def handler(self, request):
        raise httpx.ConnectError("synthetic network failure")


def sdk_for(script, *, retries=0, timeout=5.0):
    return anthropic.Anthropic(api_key=KEY, max_retries=retries, timeout=timeout, http_client=httpx.Client(transport=httpx.MockTransport(script.handler)))


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ledger = Path(self.temp.name) / "ledger.jsonl"
        self.ledger.write_text(json.dumps({"event": "baseline_unknown", "version": 1}) + "\n")
        self.runs_path = Path(self.temp.name) / "runs.jsonl"
        self.runs = RunFile(self.runs_path)

    def verify_baseline(self, prior="0"):
        estimator.baseline(self.ledger, prior, "owner-confirmed")

    def ledger_state(self):
        with estimator.locked(self.ledger) as (_, rows):
            return estimator.state(rows)

    def guard(self, script, **kwargs):
        params = dict(run_id="r1", reservation_id="res", runs=self.runs, observer=script.begin_role)
        params.update(kwargs)
        guard = GuardedAnthropic(sdk_for(script), **params)
        return guard

    def request(self, role="ybs", **overrides):
        spec = {"name": AGENTS[role]["tool"], "description": "d", "input_schema": {"type": "object"}} if AGENTS[role].get("tool") else None
        request = {"model": MODEL, "max_tokens": MAX_TOKENS, "system": AGENTS[role]["system_prompt"],
                   "messages": [{"role": "user", "content": "synthetic"}], "output_config": {"effort": "low"}}
        if spec:
            request.update(tools=[spec], tool_choice={"type": "tool", "name": spec["name"], "disable_parallel_tool_use": True})
        request.update(overrides)
        return {k: v for k, v in request.items() if v is not None}


class TruncationTests(Base):
    @staticmethod
    def truncating(role):
        class Truncating(ScriptedProvider):
            def _text(self, anthropic, text):
                body = super()._text(anthropic, text)
                if self.role == role:
                    body["stop_reason"] = "max_tokens"
                return body
        return Truncating(caps=False)

    def drive(self, role):
        guard = self.guard(self.truncating(role))
        out = run_registry(Backend("anthropic", MODEL, client=guard), "model")
        self.assertTrue(out["summary"]["ok"])                                    # the text was present, so the driver alone passes it
        self.assertEqual(guard.truncated, {(role, "model")})
        return guard, out

    def test_a_truncated_narrative_fails_like_any_other_role(self):
        guard, out = self.drive("narrative")
        flag_truncation(out, "model", guard.truncated)
        self.assertFalse(out["summary"]["ok"])
        self.assertEqual(out["summary"]["failed"], {"narrative": ["not_truncated"]})

    def test_every_role_cut_off_at_max_tokens_fails(self):
        for role in ("hmda", "auditor", "narrative"):
            with self.subTest(role=role):
                guard, out = self.drive(role)
                flag_truncation(out, "model", guard.truncated)
                self.assertFalse(out["summary"]["ok"])
                self.assertEqual(out["summary"]["failed"], {role: ["not_truncated"]})

    def test_no_truncation_tolerance_remains_and_only_the_truncated_phase_is_flagged(self):
        import test_anthropic_live_parity as live
        self.assertFalse(hasattr(live, "TOLERATED_TRUNCATION"))
        guard, out = self.drive("narrative")
        flag_truncation(out, "seeded", set())                                     # nothing was truncated in the seeded phase
        self.assertTrue(out["summary"]["ok"])
        flag_truncation(out, "model", guard.truncated)
        self.assertEqual(out["summary"]["failed"], {"narrative": ["not_truncated"]})
        self.assertNotIn("tolerated", out["summary"])


class GuardLimitTests(Base):
    def test_zero_sdk_retries_and_a_finite_timeout_are_required(self):
        script = ScriptedProvider()
        for retries, timeout in ((2, 5.0), (None, 5.0), (0, None), (0, float("inf")), (0, 0), (0, httpx.Timeout(None))):
            with self.subTest(retries=retries, timeout=timeout), self.assertRaises(GuardRefusal):
                GuardedAnthropic(sdk_for(script, retries=retries, timeout=timeout) if retries is not None and timeout is not None else
                                 type("Sdk", (), {"max_retries": retries, "timeout": timeout})(),
                                 run_id="r", reservation_id="res", runs=self.runs)
        GuardedAnthropic(sdk_for(script, timeout=httpx.Timeout(5.0)), run_id="r", reservation_id="res", runs=self.runs)
        self.assertEqual(script.requests, [])

    def test_the_real_module_builds_its_client_with_zero_retries_and_a_finite_timeout(self):
        source = (ROOT / "tests/test_anthropic_live_parity.py").read_text(encoding="utf-8")
        self.assertIn("timeout=TIMEOUT, max_retries=0", source)
        self.assertTrue(0 < __import__("test_anthropic_live_parity").TIMEOUT < float("inf"))

    def test_each_refusal_happens_before_a_request_leaves_and_is_recorded(self):
        script = ScriptedProvider(caps=False)
        cases = {
            "model": self.request(model="claude-sonnet-5-5"), "max_tokens": self.request(max_tokens=MAX_TOKENS + 1),
            "fewer tokens": self.request(max_tokens=100), "stream": {**self.request(), "stream": True},
            "tier": {**self.request(), "service_tier": "auto"}, "hosted tool": self.request(tools=[{"type": "web_search_20250305", "name": "web_search"}]),
            "second tool": self.request(tools=[{"name": "hmda_evaluate", "description": "d", "input_schema": {}}]),
            "other tool": self.request(tools=[{"name": "bash", "description": "d", "input_schema": {}}]),
            "tool_choice any": self.request(tool_choice={"type": "any", "disable_parallel_tool_use": True}),
            "parallel": self.request(tool_choice={"type": "auto"}), "other prompt": self.request(system="You are a pirate."),
            "no user turn": self.request(messages=[{"role": "assistant", "content": "x"}]), "thinking": {**self.request(), "thinking": {"type": "enabled"}},
            "no effort": self.request(output_config=None), "medium effort": self.request(output_config={"effort": "medium"}),
            "extra output_config": self.request(output_config={"effort": "low", "format": {"type": "json_schema", "schema": {}}}),
        }
        guard = self.guard(script)
        guard.begin_role("ybs", "model")
        for name, request in cases.items():
            with self.subTest(case=name), self.assertRaises(GuardRefusal):
                guard.messages.create(**request)
        self.assertEqual(script.requests, [])
        self.assertEqual(sum(1 for r in self.runs.rows() if r["event"] == "refusal"), len(cases))
        guard.begin_role("narrative", "model")
        with self.assertRaises(GuardRefusal):
            guard.messages.create(**self.request("ybs"))                      # the narrative role has no tool and another prompt
        with self.assertRaises(GuardRefusal):
            self.guard(script).messages.create(**self.request())             # no role context

    def test_no_reservation_means_no_request(self):
        script = ScriptedProvider(caps=False)
        guard = self.guard(script, reservation_id=None)
        guard.begin_role("ybs", "model")
        with self.assertRaisesRegex(GuardRefusal, "reservation"):
            guard.messages.create(**self.request())
        self.assertEqual(script.requests, [])

    def test_the_input_byte_bound_is_exact(self):
        script = ScriptedProvider(caps=False)
        request = self.request()
        size = request_bytes(request)
        guard = self.guard(script, byte_bound=size)
        guard.begin_role("ybs", "model")
        guard.messages.create(**request)
        self.assertEqual(len(script.requests), 1)
        tight = self.guard(ScriptedProvider(caps=False), byte_bound=size - 1)
        tight.begin_role("ybs", "model")
        with self.assertRaisesRegex(GuardRefusal, "input bound"):
            tight.messages.create(**request)
        big = self.request(system=AGENTS["ybs"]["system_prompt"] + "é" * (BYTE_BOUND // 2))        # multi-byte text counts in UTF-8 bytes
        self.assertGreater(request_bytes(big), BYTE_BOUND)
        full = self.guard(ScriptedProvider(caps=False))
        full.begin_role("ybs", "model")
        with self.assertRaisesRegex(GuardRefusal, "input bound"):
            full.messages.create(**big)

    def test_the_run_cap_and_the_role_cap_stop_requests(self):
        script = ScriptedProvider(caps=False)
        guard = self.guard(script, limit=3)
        for role in ("ybs", "hmda", "ecoa", "trid"):
            guard.begin_role(role, "model")
            if len(script.requests) < 3:
                guard.messages.create(**self.request(role))
            else:
                with self.assertRaisesRegex(GuardRefusal, "run request cap"):
                    guard.messages.create(**self.request(role))
        self.assertEqual(len(script.requests), 3)
        role_script = ScriptedProvider(caps=False)
        guard = self.guard(role_script)
        guard.begin_role("narrative", "seeded")
        guard.messages.create(**self.request("narrative"))
        with self.assertRaisesRegex(GuardRefusal, "role request cap"):
            guard.messages.create(**self.request("narrative"))
        guard.begin_role("narrative", "model")                                # a new role context has its own allowance
        guard.messages.create(**self.request("narrative"))
        self.assertEqual(len(role_script.requests), 2)

    def test_the_default_run_cap_is_the_derived_total_and_within_the_plan_ceiling(self):
        self.assertEqual(RUN_LIMIT, worst_case_table("anthropic")["total"])
        self.assertLessEqual(RUN_LIMIT, 80)

    def test_the_measured_payloads_fit_the_bound_and_every_request_in_a_full_run_passes_the_guard(self):
        sizes = offline_payload_inspection()
        self.assertEqual(set(sizes), set(ROLES))
        self.assertTrue(all(0 < v <= BYTE_BOUND for v in sizes.values()), sizes)


class LiveRunAccountingTests(Base):
    def run_live(self, script=None, **kwargs):
        script = script or ScriptedProvider(caps=False)
        result = live_run(sdk_for(script), ledger=self.ledger, runs_path=self.runs_path, today=TODAY, observer=script.begin_role, **kwargs)
        return script, result

    def test_one_reservation_and_one_settlement_per_run_from_reported_usage(self):
        self.verify_baseline("1.5")
        script, result = self.run_live()
        rows = [json.loads(line) for line in self.ledger.read_text().splitlines()]
        self.assertEqual([r["event"] for r in rows], ["baseline_unknown", "baseline_verified", "reservation", "settlement"])
        reservation, settlement = rows[2], rows[3]
        self.assertEqual((reservation["attempts"], reservation["input_tokens_per_attempt"], reservation["output_tokens_per_attempt"], reservation["model"]),
                         (RUN_LIMIT, BYTE_BOUND, MAX_TOKENS, MODEL))
        self.assertLessEqual(Decimal(settlement["cost_usd"]), Decimal(reservation["bound_usd"]))
        self.assertFalse(settlement["exceeds_reservation"])
        self.assertLessEqual(Decimal(reservation["bound_usd"]), 5)
        self.assertLessEqual(len(script.requests), RUN_LIMIT)
        spent, held, _ = self.ledger_state()
        self.assertEqual(held, 0)
        self.assertEqual(spent, Decimal("1.5") + Decimal(settlement["cost_usd"]))
        # each request is 1 input and 1 output token in the fake: 1.1 * (1*0.10 + 1*0.50) / 1e6
        self.assertEqual(Decimal(settlement["cost_usd"]), len(script.requests) * Decimal("1.1") * Decimal("0.60") / Decimal(1_000_000))

    def test_run_rows_give_a_complete_per_role_phase_and_run_table_with_cost_per_narrative(self):
        self.verify_baseline()
        script, result = self.run_live()
        rows = self.runs.rows(result["run_id"])
        events = [r["event"] for r in rows]
        self.assertEqual((events[0], events[-1], events.count("run_reservation"), events.count("run_summary")), ("run_reservation", "run_summary", 1, 1))
        self.assertEqual(events.count("request_start"), events.count("request_outcome"))
        summary = rows[-1]
        cells = summary["cost_table"]["per_role_phase"]
        self.assertEqual(set(cells), {f"{role}/{phase}" for role in ROLES for phase in PHASES})
        for key, cell in cells.items():
            role, phase = key.split("/")
            self.assertGreaterEqual(cell["requests"], 1)
            self.assertLessEqual(cell["requests"], worst_case_requests("anthropic", phase, role))
        self.assertEqual(summary["cost_table"]["per_run"]["requests"], sum(c["requests"] for c in cells.values()))
        self.assertEqual(summary["successful_narratives"], 20)
        self.assertEqual(Decimal(summary["cost_per_successful_narrative_usd"]) * 20, Decimal(summary["cost_table"]["per_run"]["cost_usd"]))
        self.assertEqual(Decimal(summary["settlement_usd"]), Decimal(summary["cost_table"]["per_run"]["cost_usd"]))
        self.assertFalse(summary["reservation_retained"])
        self.assertEqual(summary["fallbacks"], [])
        self.assertTrue(all(r["tool_calls"] is not None for r in summary["roles"]))

    def test_fallbacks_are_reported_and_leave_no_successful_narrative_denominator_for_those_roles(self):
        self.verify_baseline()
        script, result = self.run_live(ScriptedProvider(caps=False, narrative="ungrounded"))
        summary = self.runs.rows(result["run_id"])[-1]
        self.assertEqual(len(summary["fallbacks"]), 18)
        self.assertEqual(summary["successful_narratives"], 2)               # only the plain narrative role, once per phase
        self.assertTrue(all(c["requests"] <= worst_case_requests("anthropic", k.split("/")[1], k.split("/")[0])
                            for k, c in summary["cost_table"]["per_role_phase"].items()))

    def test_unknown_or_odd_usage_keeps_the_whole_reservation_and_leaves_costs_null(self):
        for variant in ("missing", "negative", "text", "priority"):
            with self.subTest(variant=variant):
                self.setUp()
                self.verify_baseline("2")
                script = NoUsage(caps=False)
                script.variant = variant
                _, result = self.run_live(script)
                rows = [json.loads(line) for line in self.ledger.read_text().splitlines()]
                self.assertEqual([r["event"] for r in rows], ["baseline_unknown", "baseline_verified", "reservation"])
                spent, held, _ = self.ledger_state()
                self.assertEqual(spent, Decimal(2))
                self.assertEqual(held, Decimal(rows[2]["bound_usd"]))
                summary = self.runs.rows(result["run_id"])[-1]
                self.assertTrue(summary["reservation_retained"])
                self.assertIsNone(summary["settlement_usd"])
                self.assertIsNone(summary["cost_table"]["per_run"]["cost_usd"])
                self.assertIsNone(summary["cost_per_successful_narrative_usd"])
                self.assertTrue(all(c["cost_usd"] is None for c in summary["cost_table"]["per_role_phase"].values()))

    def test_a_failed_request_is_counted_with_its_error_type_and_retains_the_reservation(self):
        self.verify_baseline()
        script, result = self.run_live(Failing(caps=False))
        rows = self.runs.rows(result["run_id"])
        outcomes = [r for r in rows if r["event"] == "request_outcome"]
        self.assertTrue(outcomes and all(r["outcome"] == "APIConnectionError" and r["cost_usd"] is None for r in outcomes))
        self.assertTrue(rows[-1]["reservation_retained"])
        self.assertEqual(self.ledger_state()[1], Decimal(rows[0]["bound_usd"]))

    def test_usage_is_not_double_counted_and_odd_values_are_rejected(self):
        class U:
            input_tokens, cache_creation_input_tokens, cache_read_input_tokens, output_tokens, service_tier = 1000, 2000, 10000, 500, "standard"

        class R:
            usage = U
        usage = read_usage(R)
        self.assertEqual(usage, {"input_tokens": 1000, "cache_creation_input_tokens": 2000, "cache_read_input_tokens": 10000, "output_tokens": 500})
        expected = ((Decimal(1000) + Decimal(2000) * 2 + Decimal(10000) * Decimal("0.1")) * Decimal("0.10") + Decimal(500) * Decimal("0.50")) * Decimal("1.1") / Decimal(1_000_000)
        self.assertEqual(usage_cost(usage), expected)
        self.assertIsNone(usage_cost(None))
        for bad in ({"input_tokens": True}, {"output_tokens": 1.5}, {"cache_read_input_tokens": -1}, {"service_tier": "batch"}):
            U_bad = type("Ub", (U,), bad)
            self.assertIsNone(read_usage(type("Rb", (), {"usage": U_bad})), bad)

    def test_the_cumulative_cap_is_enforced_before_any_request(self):
        self.verify_baseline("19")                                             # 1.00 left; the run's bound is about 1.72
        script = ScriptedProvider(caps=False)
        with self.assertRaisesRegex(estimator.BudgetError, "exceed"):
            self.run_live(script)
        self.assertEqual(script.requests, [])
        self.assertEqual(self.runs.rows(), [])
        self.assertEqual(self.ledger_state()[1], 0)

    def test_an_unsettled_run_reduces_capacity_for_the_next_one(self):
        self.verify_baseline("17.5")
        script = NoUsage(caps=False)
        self.run_live(script)                                                  # usage missing: 1.72 stays held
        second = ScriptedProvider(caps=False)
        with self.assertRaises(estimator.BudgetError):
            self.run_live(second)
        self.assertEqual(second.requests, [])

    def test_an_unknown_baseline_blocks_the_run_before_any_request_or_file_change(self):
        script = ScriptedProvider(caps=False)
        before = self.ledger.read_text()
        with self.assertRaisesRegex(estimator.BudgetError, "unknown"):
            self.run_live(script)
        self.assertEqual((script.requests, self.ledger.read_text(), self.runs.rows()), ([], before, []))

    def test_a_stale_price_date_blocks_the_run(self):
        self.verify_baseline()
        script = ScriptedProvider(caps=False)
        before = self.ledger.read_text()
        with self.assertRaisesRegex(estimator.BudgetError, "stale"):
            live_run(sdk_for(script), ledger=self.ledger, runs_path=self.runs_path, today="2000-01-01", observer=script.begin_role)
        self.assertEqual((script.requests, self.ledger.read_text()), ([], before))

    def test_a_missing_ledger_blocks_the_run(self):
        script = ScriptedProvider(caps=False)
        with self.assertRaises(estimator.BudgetError):
            live_run(sdk_for(script), ledger=Path(self.temp.name) / "absent.jsonl", runs_path=self.runs_path, today=TODAY)
        self.assertEqual(script.requests, [])


# --- simultaneous calls (plans/archive/parallelize, step 02) --------------------------------------------------------------------------
class PromptChecked(ScriptedProvider):
    """Records the role the guard attributed each request to beside the role whose system prompt it actually carries."""

    def __init__(self, *args, overlap=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.pairs, self.overlap, self.inflight, self.peak, self._mutex = [], overlap, 0, 0, threading.Lock()

    def handler(self, request):
        body = json.loads(request.content)
        system = body.get("system") or body.get("instructions") or ""
        actual = next((k for k, v in AGENTS.items() if system.startswith(v["system_prompt"])), None)
        with self._mutex:
            self.pairs.append((self.role, actual))
            self.inflight += 1
            self.peak = max(self.peak, self.inflight)
        try:
            deadline = time.monotonic() + 5.0
            while self.overlap and self.peak < 2 and time.monotonic() < deadline:      # hold the first request until a second is in flight
                time.sleep(0.001)
            return super().handler(request)
        finally:
            with self._mutex:
                self.inflight -= 1


def released_together(jobs, *, context=None):
    """Run each job on its own thread, all released at once. `context` = "copy": each thread runs in a copy of the caller's context.
    Returns [(True, value) | (False, exception)] in job order."""
    barrier, out = threading.Barrier(len(jobs)), [None] * len(jobs)

    def work(i):
        barrier.wait()
        try:
            out[i] = (True, jobs[i]())
        except Exception as exc:
            out[i] = (False, exc)

    threads = [threading.Thread(target=(contextvars.copy_context().run if context == "copy" else lambda f, i: f(i)), args=(work, i)) for i in range(len(jobs))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return out


PER_REQUEST = Decimal("1.1") * Decimal("0.60") / Decimal(1_000_000)      # the fake reports 1 input and 1 output token on Haiku 5.5


class ConcurrentGuardTests(Base):
    """The guard must keep its caps, counters, role context and rows exact when requests arrive at the same time."""
    ROUNDS = 8

    def fresh(self, name, script, **kwargs):
        runs = RunFile(Path(self.temp.name) / f"{name}.jsonl")
        guard = GuardedAnthropic(sdk_for(script), run_id=name, reservation_id="res", runs=runs, observer=script.begin_role, **kwargs)
        return guard, runs

    def test_with_two_slots_left_exactly_two_of_eight_simultaneous_requests_proceed(self):
        for variant in ("shared", "copied", "own_roles"):
            for round_ in range(self.ROUNDS):
                with self.subTest(variant=variant, round=round_):
                    script = PromptChecked(caps=False)
                    guard, runs = self.fresh(f"{variant}{round_}", script, limit=2)
                    roles = ["hmda", "ecoa", "hvcre", "hpml", "fzd", "ybs", "vmi", "trid"]
                    if variant == "own_roles":
                        def job(role):
                            def go():
                                guard.begin_role(role, "model")
                                return guard.messages.create(**self.request(role))
                            return go
                        results = released_together([job(r) for r in roles])
                    else:
                        guard.begin_role("ybs", "model")
                        results = released_together([lambda: guard.messages.create(**self.request("ybs")) for _ in roles],
                                                    context="copy" if variant == "copied" else None)
                    ok = [r for r in results if r[0]]
                    refused = [r[1] for r in results if not r[0]]
                    self.assertEqual((len(ok), len(refused)), (2, 6))
                    self.assertTrue(all(isinstance(e, GuardRefusal) and "run request cap reached" in str(e) for e in refused), refused)
                    self.assertEqual((len(script.requests), guard.sent, len(guard.costs)), (2, 2, 2))
                    rows = runs.rows("%s%d" % (variant, round_))
                    self.assertEqual(sorted(r["sequence"] for r in rows if r["event"] == "request_start"), [1, 2])
                    self.assertEqual(sorted(r["sequence"] for r in rows if r["event"] == "request_outcome"), [1, 2])
                    self.assertEqual(sum(1 for r in rows if r["event"] == "refusal"), 6)
                    total = aggregate(rows)["total"]
                    self.assertEqual((total["requests"], total["unknown"], total["cost"]), (2, 0, 2 * PER_REQUEST))

    def test_threads_sharing_one_role_cannot_exceed_its_allowance(self):
        for round_ in range(self.ROUNDS):
            with self.subTest(round=round_):
                script = PromptChecked(caps=False)
                guard, runs = self.fresh(f"share{round_}", script)
                guard.begin_role("ybs", "model")
                allowance = worst_case_requests("anthropic", "model", "ybs")
                results = released_together([lambda: guard.messages.create(**self.request("ybs")) for _ in range(allowance + 4)], context="copy")
                self.assertEqual(sum(1 for r in results if r[0]), allowance)
                self.assertTrue(all("role request cap reached" in str(r[1]) for r in results if not r[0]))
                self.assertEqual((len(script.requests), guard.role_sent), (allowance, allowance))

    def test_roles_in_flight_together_each_keep_their_own_context_allowance_and_rows(self):
        script = PromptChecked(caps=False, overlap=True)
        guard, runs = self.fresh("roles", script)
        roles = ["hmda", "ecoa", "hvcre", "hpml", "fzd", "ybs", "vmi", "trid"]

        def one_role(role):
            def go():
                guard.begin_role(role, "model")
                allowance = worst_case_requests("anthropic", "model", role)
                for _ in range(allowance):
                    guard.messages.create(**self.request(role))
                    self.assertEqual((guard.role, guard.phase), (role, "model"))      # this thread still sees its own role
                with self.assertRaisesRegex(GuardRefusal, "role request cap reached"):
                    guard.messages.create(**self.request(role))
                return allowance
            return go

        results = released_together([one_role(r) for r in roles])
        self.assertTrue(all(r[0] for r in results), [r[1] for r in results if not r[0]])
        expected = sum(r[1] for r in results)
        self.assertEqual((len(script.requests), guard.sent, len(guard.costs)), (expected, expected, expected))
        self.assertTrue(all(attributed == actual for attributed, actual in script.pairs), "a request was attributed to another role")
        rows = runs.rows("roles")
        starts = [r for r in rows if r["event"] == "request_start"]
        self.assertEqual(sorted(r["sequence"] for r in starts), list(range(1, expected + 1)))
        self.assertEqual({r["role"] for r in starts}, set(roles))
        for role in roles:
            self.assertEqual(sum(1 for r in starts if r["role"] == role), worst_case_requests("anthropic", "model", role))
        self.assertEqual(sum(1 for r in rows if r["event"] == "refusal"), len(roles))
        self.assertGreater(script.peak, 1)                                                         # they really overlapped
        total = aggregate(rows)["total"]
        self.assertEqual((total["requests"], total["unknown"], total["cost"]), (expected, 0, expected * PER_REQUEST))
        self.assertEqual(sum(guard.costs, Decimal(0)), total["cost"])

    def test_the_run_file_stays_one_valid_row_per_line_and_replays_identically(self):
        script = PromptChecked(caps=False)
        guard, runs = self.fresh("lines", script)
        roles = ["hmda", "ecoa", "hpml", "ybs"]
        released_together([(lambda r=r: (guard.begin_role(r, "model"), guard.messages.create(**self.request(r)))) for r in roles * 2])
        lines = runs.path.read_text(encoding="utf-8").splitlines()
        rows = [json.loads(line) for line in lines]          # raises if two writers interleaved a line
        self.assertEqual(len(lines), len(rows))
        self.assertEqual(cost_table(rows), cost_table(RunFile(runs.path).rows()))

    def test_a_full_registry_run_at_width_four_is_attributed_counted_and_settled_exactly(self):
        self.verify_baseline()
        script = PromptChecked(overlap=True)
        drive = lambda backend, phase: run_registry(backend, phase, remote_concurrency=4)
        before = {p: p.stat().st_size for p in Path("logs").glob("*.jsonl")}
        result = live_run(sdk_for(script), ledger=self.ledger, runs_path=self.runs_path, today=TODAY, observer=script.begin_role, drive=drive)
        for phase, out in result["outputs"].items():
            self.assertTrue(out["summary"]["ok"], (phase, out["summary"]["failed"]))
        self.assertGreater(script.peak, 1)
        self.assertTrue(all(attributed == actual for attributed, actual in script.pairs))
        self.assertEqual(script.refused, [])
        rows = self.runs.rows(result["run_id"])
        starts = [r for r in rows if r["event"] == "request_start"]
        self.assertEqual(sorted(r["sequence"] for r in starts), list(range(1, len(script.requests) + 1)))
        self.assertEqual(len(starts), len(script.requests))
        for role in ROLES:
            for phase in PHASES:
                self.assertLessEqual(sum(1 for r in starts if (r["role"], r["phase"]) == (role, phase)), worst_case_requests("anthropic", phase, role))
        expected = len(script.requests) * PER_REQUEST
        self.assertEqual(Decimal(result["settlement"]), expected)
        self.assertEqual(aggregate(rows)["total"]["cost"], expected)
        spent, held, _ = self.ledger_state()
        self.assertEqual((spent, held), (expected, 0))
        for path, size in before.items():                                                              # log files written during the run
            with path.open("rb") as f:
                f.seek(size)
                for line in f.read().decode("utf-8").splitlines():
                    json.loads(line)

    def test_log_lines_from_simultaneous_writers_do_not_interleave(self):
        from compliance_common.obs import get_logger
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(os.environ, {"COMPLIANCE_LOG_DIR": directory}):
            name = "stress" + os.urandom(4).hex()
            log = get_logger(name, "1")
            pad = "x" * 3000
            try:
                released_together([(lambda i=i: [log.info("writer %d line %d %s", i, n, pad) for n in range(50)]) for i in range(8)])
            finally:
                for handler in list(log.logger.handlers):
                    handler.close()
                    log.logger.removeHandler(handler)
            lines = Path(directory, f"{name}.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 8 * 50)
        self.assertEqual(len({json.loads(line)["msg"] for line in lines}), 8 * 50)


# --- candidate models (plans/archive/tune-ais, step 01) --------------------------------------------------------------------------------
SONNET = "claude-sonnet-5-5"
OTHER_MODELS = ("claude-opus-5-5", "claude-fable-5-1", "claude-haiku-4-5-20251001", "claude-sonnet-4-6", "claude-haiku-5", "claude-sonnet-5-5-x", "")


class CandidateModelGuardTests(Base):
    """The live guard admits Haiku 5.5 and Sonnet 5.5 and nothing else new; Sonnet is never sent a forced tool choice."""

    def test_the_allow_list_is_the_two_candidates_and_the_guard_refuses_every_other_model_at_construction(self):
        self.assertEqual(ALLOWED_MODELS, ("claude-haiku-5-5", "claude-sonnet-5-5"))
        for model in ALLOWED_MODELS:
            with self.subTest(model=model):
                self.assertEqual(self.guard(ScriptedProvider(model=model), model=model).model, model)
        for model in OTHER_MODELS:
            with self.subTest(model=model), self.assertRaisesRegex(GuardRefusal, "not an allowed model"):
                self.guard(ScriptedProvider(), model=model)

    def test_each_guard_sends_only_its_own_model_and_records_a_refusal_for_any_other(self):
        for own, other in ((MODEL, SONNET), (SONNET, MODEL)):
            with self.subTest(own=own):
                script = ScriptedProvider(caps=False, model=own)
                guard = self.guard(script, model=own)
                guard.begin_role("narrative", "model")
                with self.assertRaisesRegex(GuardRefusal, "unexpected model"):
                    guard.messages.create(**self.request("narrative", model=other))
                self.assertEqual(script.requests, [])
                guard.messages.create(**self.request("narrative", model=own))
                self.assertEqual([r["model"] for r in script.requests], [own])
        self.assertIn("unexpected model", [r.get("reason") for r in self.runs.rows()])

    def test_a_forced_tool_choice_is_refused_for_sonnet_before_it_leaves_and_allowed_for_haiku(self):
        script = ScriptedProvider(caps=False, model=SONNET)
        guard = self.guard(script, model=SONNET)
        guard.begin_role("ybs", "model")
        forced = self.request("ybs", model=SONNET)
        self.assertEqual(forced["tool_choice"]["type"], "tool")
        with self.assertRaisesRegex(GuardRefusal, "forced tool_choice"):
            guard.messages.create(**forced)
        self.assertEqual(script.requests, [])
        auto = self.request("ybs", model=SONNET, tool_choice={"type": "auto", "disable_parallel_tool_use": True})
        guard.messages.create(**auto)
        self.assertEqual(len(script.requests), 1)
        haiku = ScriptedProvider(caps=False)
        guard = self.guard(haiku)
        guard.begin_role("ybs", "model")
        guard.messages.create(**self.request("ybs"))
        self.assertEqual(len(haiku.requests), 1)

    def test_cost_is_priced_at_the_rates_of_the_model_that_ran(self):
        usage = {"input_tokens": 1000, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "output_tokens": 500}
        self.assertEqual(usage_cost(usage), Decimal("1.1") * (1000 * Decimal("0.10") + 500 * Decimal("0.50")) / 1_000_000)
        self.assertEqual(usage_cost(usage, MODEL), usage_cost(usage))
        self.assertEqual(usage_cost(usage, SONNET), Decimal("1.1") * (1000 * Decimal(2) + 500 * Decimal(10)) / 1_000_000)
        script = ScriptedProvider(caps=False, model=SONNET)
        guard = self.guard(script, model=SONNET)
        guard.begin_role("narrative", "model")
        guard.messages.create(**self.request("narrative", model=SONNET))
        self.assertEqual(guard.costs, [Decimal("1.1") * (Decimal(2) + Decimal(10)) / 1_000_000])      # the fake reports 1 input and 1 output token

    def test_a_sonnet_role_run_completes_in_model_mode_with_the_tool_called_by_the_model_never_a_400(self):
        script = ScriptedProvider(model=SONNET)
        guard = self.guard(script, model=SONNET, limit=RUN_LIMIT)
        out = run_registry(Backend("anthropic", SONNET, client=guard), "model")
        self.assertEqual(script.rejected, [])
        self.assertEqual(out["summary"]["failed"], {}, out["summary"]["failed"])
        self.assertFalse(script.refused)
        for record in out["records"]:
            if record["tool_backed"]:
                self.assertEqual({c["by"] for c in record["tool_calls"]}, {"model"}, record["role"])
        for row in script.requests:
            self.assertNotEqual((row["tool_choice"] or {}).get("type"), "tool")

    def test_a_sonnet_that_ignores_the_instruction_is_covered_by_the_harness_inside_the_bound(self):
        script = ScriptedProvider(model=SONNET, tool="none")
        guard = self.guard(script, model=SONNET, limit=RUN_LIMIT)
        out = run_registry(Backend("anthropic", SONNET, client=guard), "model")
        self.assertEqual(script.rejected, [])
        record = next(r for r in out["records"] if r["role"] == "hmda")
        self.assertEqual({c["by"] for c in record["tool_calls"]}, {"harness"})
        for role in ROLES:
            self.assertLessEqual(script.count(role, "model"), worst_case_requests("anthropic", "model", role))


class DurabilityAndHygieneTests(Base):
    def test_a_crash_after_reserving_leaves_the_reservation_held_and_the_rows_replay_identically(self):
        self.verify_baseline("3")
        rid, bound = estimator.reserve(self.ledger, MODEL, RUN_LIMIT, BYTE_BOUND, MAX_TOKENS, TODAY)
        script = ScriptedProvider(caps=False)
        guard = self.guard(script, reservation_id=rid)
        for role in ("hmda", "ybs"):
            guard.begin_role(role, "model")
            guard.messages.create(**self.request(role))
        before = aggregate(self.runs.rows())
        # a new process: nothing in memory, only the files
        reopened = RunFile(self.runs_path)
        self.assertEqual(aggregate(reopened.rows()), before)
        self.assertEqual(cost_table(reopened.rows()), cost_table(self.runs.rows()))
        self.assertEqual(self.ledger_state()[1], bound)
        estimator.estimate(MODEL, 600, BYTE_BOUND, MAX_TOKENS, TODAY)          # 3 + 15.90 fits alone, but not beside the held 1.72
        with self.assertRaisesRegex(estimator.BudgetError, "exceed"):
            estimator.reserve(self.ledger, MODEL, 600, BYTE_BOUND, MAX_TOKENS, TODAY)

    def test_a_started_request_without_an_outcome_replays_as_unknown(self):
        self.runs.append({"event": "request_start", "run_id": "r9", "sequence": 1, "role": "ybs", "phase": "model"})
        table = cost_table(self.runs.rows())
        self.assertEqual((table["per_run"]["requests"], table["per_run"]["unknown_requests"], table["per_run"]["cost_usd"]), (1, 1, None))

    def test_no_credentials_or_bodies_reach_any_file(self):
        self.verify_baseline()
        script = ScriptedProvider(caps=False)
        live_run(sdk_for(script), ledger=self.ledger, runs_path=self.runs_path, today=TODAY, observer=script.begin_role)
        text = self.ledger.read_text() + self.runs_path.read_text()
        case_id = SAMPLE["case_information"]["case_id"]
        fragments = [KEY, "sk-ant", case_id, "Synthetic report", "examiner_narrative", "Narrate the decision record", "TOOL RESULT", "api_key",
                     AGENTS["ybs"]["system_prompt"][:60], "Authorization"]
        for fragment in fragments:
            self.assertNotIn(fragment, text)

    def test_the_default_suite_skips_the_live_module_and_contacts_nothing(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("RUN_LIVE_")}
        env["ANTHROPIC_API_KEY"] = ""
        done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_anthropic_live_parity.py", "-v"],
                              cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
        self.assertEqual(done.returncode, 0, done.stderr[-500:])
        self.assertIn("skipped", done.stderr)
        self.assertIn("OK (skipped=1)", done.stderr)


if __name__ == "__main__":
    unittest.main()

"""Offline proofs for the guarded Anthropic live run: caps, zero retries, durable accounting. No network, no credentials."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import anthropic
import httpx

from agent_prompts import AGENTS
from agents.backends import Backend
from live_parity_common import PHASES, ScriptedProvider, registry_roles, role_failures, run_registry, worst_case_requests, worst_case_table
from scripts import anthropic_cost_estimator as estimator
from test_agent_parity import SAMPLE
from test_anthropic_live_parity import (BYTE_BOUND, MAX_TOKENS, MODEL, RUN_LIMIT, GuardedAnthropic, GuardRefusal, RunFile, aggregate, cost_table,
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

    def test_a_truncated_narrative_is_tolerated_but_still_detected_and_reported(self):
        guard, out = self.drive("narrative")
        flag_truncation(out, "model", guard.truncated)
        self.assertTrue(out["summary"]["ok"])
        self.assertEqual(out["summary"]["failed"], {})
        self.assertEqual(out["summary"]["tolerated"], {"narrative": ["truncated_at_max_tokens"]})
        self.assertEqual([r["role"] for r in out["records"] if r.get("tolerated")], ["narrative"])

    def test_every_other_role_cut_off_at_max_tokens_still_fails(self):
        for role in ("hmda", "auditor"):
            with self.subTest(role=role):
                guard, out = self.drive(role)
                flag_truncation(out, "model", guard.truncated)
                self.assertFalse(out["summary"]["ok"])
                self.assertEqual(out["summary"]["failed"], {role: ["not_truncated"]})
                self.assertEqual(out["summary"]["tolerated"], {})

    def test_the_tolerance_names_exactly_the_recorded_exception_and_no_other_phase_is_touched(self):
        from test_anthropic_live_parity import TOLERATED_TRUNCATION
        self.assertEqual(TOLERATED_TRUNCATION, frozenset({"narrative"}))
        record = (ROOT / "plans/archive/live-parity/exception-record.md").read_text(encoding="utf-8")
        self.assertIn("TOLERATED_TRUNCATION", record)
        self.assertIn("Review by", record)
        guard, out = self.drive("narrative")
        flag_truncation(out, "seeded", set())
        self.assertEqual(out["summary"]["tolerated"], {})
        flag_truncation(out, "model", guard.truncated, frozenset())               # without the exception the same truncation fails
        self.assertEqual(out["summary"]["failed"], {"narrative": ["not_truncated"]})


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

"""Offline proofs for the guarded OpenAI registry-wide live run: caps, validation, durable shared-ledger accounting. No network."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import httpx
import openai

from agent_prompts import AGENTS
from live_parity_common import PHASES, ScriptedProvider, registry_roles, worst_case_requests, worst_case_table
from scripts.openai_cost_estimator import assess
from test_agent_parity import SAMPLE
from test_openai_live_parity import (BYTE_BOUND, RUN_LIMIT, SCHEMA_FORMAT, GuardedOpenAI, GuardRefusal, RunFile, aggregate, expected_outbound,
                                     live_run, rehearse, request_bytes, validate_outbound)
from test_openai_live_smoke import (BUDGET, MODEL, OUTPUT_LIMIT, PARITY_INPUT_BOUND_TOKENS, PARITY_REQUEST_BOUND, PRICE_CHECKED, BudgetError,
                                    Ledger)

ROOT = Path(__file__).resolve().parents[1]
KEY = "sk-OFFLINE-SENTINEL-0000"
ROLES = registry_roles()


class NoUsage(ScriptedProvider):
    """Responses without usage, or with inconsistent usage, so the reservation must be retained."""
    variant = "missing"

    def handler(self, request):
        response = super().handler(request)
        body = json.loads(response.content)
        if self.variant == "missing":
            body.pop("usage", None)
        elif self.variant == "inconsistent":
            body["usage"]["total_tokens"] = 99
        elif self.variant == "tier":
            body["service_tier"] = "priority"
        return httpx.Response(200, json=body)


class Failing(ScriptedProvider):
    def handler(self, request):
        raise httpx.ConnectError("synthetic network failure")


def sdk_for(script, *, retries=0, timeout=5.0):
    return openai.OpenAI(api_key=KEY, max_retries=retries, timeout=timeout, http_client=httpx.Client(transport=httpx.MockTransport(script.handler)))


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ledger_path = Path(self.temp.name) / "ledger.jsonl"
        Ledger(self.ledger_path).start_cycle("prior", 1)                  # a shared ledger is never empty
        Ledger(self.ledger_path).end_cycle("prior", {}, 0)
        self.runs_path = Path(self.temp.name) / "runs.jsonl"
        self.runs = RunFile(self.runs_path)
        self.ledger = Ledger(self.ledger_path)

    def ledger_rows(self):
        return [json.loads(line) for line in self.ledger_path.read_text().splitlines()]

    def state(self):
        return Ledger.state(self.ledger_rows())

    def start(self, slots=RUN_LIMIT):
        self.ledger.start_cycle("c1", slots, PARITY_REQUEST_BOUND, PARITY_INPUT_BOUND_TOKENS)

    def guard(self, script, **kwargs):
        if not self.ledger_rows()[-1].get("cycle_id") == "c1" and not any(r.get("cycle_id") == "c1" for r in self.ledger_rows()):
            self.start()
        return GuardedOpenAI(sdk_for(script), self.ledger, "c1", self.runs, observer=script.begin_role, **kwargs)

    def request(self, role="ybs", phase="model", **overrides):
        """The request the production runner would send first for a domain role."""
        system, user = expected_outbound(role)
        tool = AGENTS[role].get("tool")
        request = {"model": MODEL, "instructions": system, "input": [{"role": "user", "content": user or "x"}], "max_output_tokens": OUTPUT_LIMIT, "store": False}
        if tool:
            request.update(tools=[{"type": "function", "name": tool, "description": "d", "parameters": {"type": "object"}, "strict": False}],
                           tool_choice={"type": "function", "name": tool}, parallel_tool_calls=False, text=SCHEMA_FORMAT)
        request.update(overrides)
        return {k: v for k, v in request.items() if v is not None}


class OutboundValidationTests(Base):
    def test_every_role_has_an_expected_prompt_and_a_domain_case_is_the_synthetic_fixture(self):
        for role in ROLES:
            system, user = expected_outbound(role)
            self.assertTrue(system.startswith(AGENTS[role]["system_prompt"]))
            if role == "narrative":
                self.assertIsNone(user)
            else:
                self.assertIn(AGENTS[role]["tool"], user)
        self.assertIn(SAMPLE["case_information"]["case_id"], expected_outbound("ybs")[1])
        self.assertNotIn("987654321", expected_outbound("ybs")[1])

    def test_a_faithful_first_request_is_accepted_for_every_role_and_phase(self):
        for role in ROLES:
            for phase in PHASES:
                with self.subTest(role=role, phase=phase):
                    if role == "narrative":
                        request = self.request(role, content=None)
                        request["input"] = [{"role": "user", "content": AGENTS[role].get("user_message_prefix", __import__("agents.runner").runner.DEFAULT_PREFIX)
                                             + "\n\n" + json.dumps({k: {} for k in ROLES[:-1]}, indent=2)}]
                    else:
                        request = self.request(role)
                    validate_outbound(request, role, phase)

    def test_later_turns_may_append_the_decision_block_but_not_alter_the_case(self):
        request = self.request("ybs")
        request["input"][0]["content"] += "\n\nTOOL RESULT (authoritative decision record; explain it, do not change it)\n{}"
        validate_outbound(request, "ybs", "model")
        request["input"][0]["content"] = request["input"][0]["content"].replace("TEST-2024-001", "REAL-CUSTOMER-77", 1)
        with self.assertRaises(GuardRefusal):
            validate_outbound(request, "ybs", "model")

    def test_each_unexpected_request_is_refused(self):
        system, user = expected_outbound("ybs")
        tool = "ybs_evaluate"
        good_tool = {"type": "function", "name": tool, "description": "d", "parameters": {}, "strict": False}
        cases = {
            "model": {"model": "gpt-6"}, "store": {"store": True}, "store missing": {"store": None}, "tokens": {"max_output_tokens": 100},
            "instructions": {"instructions": "You are a pirate."}, "extra field": {"metadata": {"a": "b"}}, "background": {"background": True},
            "stream": {"stream": True}, "service tier": {"service_tier": "priority"}, "hosted tool": {"tools": [{"type": "web_search"}]},
            "second tool": {"tools": [good_tool, {**good_tool, "name": "hmda_evaluate"}]}, "other function": {"tools": [{**good_tool, "name": "bash"}]},
            "strict tool": {"tools": [{**good_tool, "strict": True}]}, "tool_choice required": {"tool_choice": "required"},
            "tool_choice other": {"tool_choice": {"type": "function", "name": "hmda_evaluate"}}, "parallel": {"parallel_tool_calls": True},
            "format": {"text": {"format": {"type": "json_object"}}}, "no format": {"text": None},
            "other case": {"input": [{"role": "user", "content": user.replace("ybs_case", "xyz_case")}]},
            "assistant first": {"input": [{"role": "assistant", "content": user}]}, "empty input": {"input": []},
            "non-string content": {"input": [{"role": "user", "content": [{"type": "input_text", "text": user}]}]},
        }
        for name, overrides in cases.items():
            with self.subTest(case=name), self.assertRaises(GuardRefusal):
                validate_outbound(self.request("ybs", **overrides), "ybs", "model")
        with self.assertRaises(GuardRefusal):
            validate_outbound(self.request("narrative", tools=[good_tool]), "narrative", "model")
        with self.assertRaises(GuardRefusal):
            validate_outbound(self.request("narrative", text=SCHEMA_FORMAT), "narrative", "model")

    def test_the_seeded_exchange_must_match_the_canonical_case(self):
        from compliance_mcp.registry import adapter
        canonical = adapter("ybs").tool_arguments(SAMPLE)[0]
        request = self.request("ybs", tool_choice="none")
        request["input"] += [{"type": "function_call", "call_id": "c", "name": "ybs_evaluate", "arguments": json.dumps(canonical)},
                             {"type": "function_call_output", "call_id": "c", "output": json.dumps({"decision_id": "d"})}]
        validate_outbound(request, "ybs", "seeded")
        request["input"][1]["arguments"] = json.dumps({"case": {"case_id": "TAMPERED"}})
        with self.assertRaises(GuardRefusal):
            validate_outbound(request, "ybs", "seeded")
        request["input"][1]["arguments"] = json.dumps(canonical)
        request["input"][1]["name"] = "other"
        with self.assertRaises(GuardRefusal):
            validate_outbound(request, "ybs", "seeded")


class GuardTests(Base):
    def test_zero_retries_and_a_finite_timeout_are_required(self):
        script = ScriptedProvider(provider="openai")
        self.start()
        for retries, timeout in ((2, 5.0), (None, 5.0), (0, None), (0, float("inf")), (0, 0), (0, httpx.Timeout(None))):
            with self.subTest(retries=retries, timeout=timeout), self.assertRaises(GuardRefusal):
                sdk = (type("Sdk", (), {"max_retries": retries, "timeout": timeout})() if retries is None or timeout is None
                       else sdk_for(script, retries=retries, timeout=timeout))
                GuardedOpenAI(sdk, self.ledger, "c1", self.runs)
        GuardedOpenAI(sdk_for(script, timeout=httpx.Timeout(5.0)), self.ledger, "c1", self.runs)
        self.assertIn("timeout=TIMEOUT, max_retries=0", (ROOT / "tests/test_openai_live_parity.py").read_text(encoding="utf-8"))

    def test_refusals_leave_no_request_and_no_ledger_reservation(self):
        script = ScriptedProvider(provider="openai", caps=False)
        guard = self.guard(script)
        guard.begin_role("ybs", "model")
        before = len(self.ledger_rows())
        for overrides in ({"model": "other"}, {"store": True}, {"max_output_tokens": 1}, {"instructions": "x"}):
            with self.assertRaises(GuardRefusal):
                guard.responses.create(**self.request("ybs", **overrides))
        with self.assertRaises(GuardRefusal):
            self.guard(script).responses.create(**self.request("ybs"))                   # a new guard has no role context
        self.assertEqual((script.requests, len(self.ledger_rows())), ([], before))
        self.assertEqual(sum(1 for r in self.runs.rows() if r["event"] == "refusal"), 5)

    def test_the_cycle_is_reserved_before_a_request_leaves_and_the_outcome_follows(self):
        seen = []

        class Peek(ScriptedProvider):
            def handler(inner, request):
                seen.append([r["event"] for r in self.ledger_rows()][-2:])
                return super().handler(request)
        script = Peek(provider="openai", caps=False)
        guard = self.guard(script)
        guard.begin_role("ybs", "model")
        guard.responses.create(**self.request("ybs"))
        self.assertEqual(seen, [["cycle_reservation", "request_reservation"]])
        self.assertEqual(self.ledger_rows()[-1]["event"], "request_outcome")
        self.assertEqual(self.ledger_rows()[-1]["role"], "ybs")
        self.assertEqual(self.ledger_rows()[-1]["mode"], "model")

    def test_the_service_tier_is_pinned_and_the_request_is_otherwise_unchanged(self):
        script = ScriptedProvider(provider="openai", caps=False)
        guard = self.guard(script)
        guard.begin_role("ybs", "model")
        guard.responses.create(**self.request("ybs"))
        sent = script.requests[0]
        self.assertEqual((sent["model"], sent["tool_choice"]), (MODEL, {"type": "function", "name": "ybs_evaluate"}))

    def test_the_input_byte_bound_is_exact(self):
        script = ScriptedProvider(provider="openai", caps=False)
        request = self.request("ybs")
        size = request_bytes(request)
        guard = self.guard(script, byte_bound=size)
        guard.begin_role("ybs", "model")
        guard.responses.create(**request)
        tight = GuardedOpenAI(sdk_for(script), self.ledger, "c1", self.runs, byte_bound=size - 1)
        tight.begin_role("ybs", "model")
        with self.assertRaisesRegex(GuardRefusal, "input bound"):
            tight.responses.create(**request)
        big = self.request("ybs")
        big["input"][0]["content"] += "\n\nTOOL RESULT (authoritative decision record; explain it, do not change it)\n" + "é" * (BYTE_BOUND // 2)
        self.assertGreater(request_bytes(big), BYTE_BOUND)
        full = self.guard(script)
        full.begin_role("ybs", "model")
        with self.assertRaisesRegex(GuardRefusal, "input bound"):
            full.responses.create(**big)
        self.assertEqual(len(script.requests), 1)

    def test_the_run_cap_and_the_role_cap_stop_requests(self):
        script = ScriptedProvider(provider="openai", caps=False)
        self.start(slots=3)
        guard = GuardedOpenAI(sdk_for(script), self.ledger, "c1", self.runs, limit=3, observer=script.begin_role)
        for role in ("ybs", "hmda", "ecoa", "trid"):
            guard.begin_role(role, "model")
            if len(script.requests) < 3:
                guard.responses.create(**self.request(role))
            else:
                with self.assertRaisesRegex(GuardRefusal, "run request cap"):
                    guard.responses.create(**self.request(role))
        self.assertEqual(len(script.requests), 3)
        self.assertEqual(sum(1 for r in self.ledger_rows() if r["event"] == "request_reservation"), 3)
        other = ScriptedProvider(provider="openai", caps=False)
        self.ledger.start_cycle("c2", RUN_LIMIT, PARITY_REQUEST_BOUND, PARITY_INPUT_BOUND_TOKENS)
        guard = GuardedOpenAI(sdk_for(other), self.ledger, "c2", self.runs, observer=other.begin_role)
        guard.begin_role("ybs", "seeded")
        bound = worst_case_requests("openai", "seeded", "ybs")
        for _ in range(bound):
            guard.responses.create(**self.request("ybs", tool_choice="none"))
        with self.assertRaisesRegex(GuardRefusal, "role request cap"):
            guard.responses.create(**self.request("ybs", tool_choice="none"))
        self.assertEqual(len(other.requests), bound)

    def test_a_failed_request_is_recorded_sanitized_and_keeps_its_reservation(self):
        script = Failing(provider="openai", caps=False)
        guard = self.guard(script)
        guard.begin_role("ybs", "model")
        with self.assertRaises(Exception) as caught:
            guard.responses.create(**self.request("ybs"))
        self.assertNotIn("synthetic network failure", str(caught.exception))
        self.assertNotIn("synthetic network failure", self.ledger_path.read_text())
        last = self.ledger_rows()[-1]
        self.assertEqual((last["event"], last["outcome"], last["budget_charge_usd"], last["role"]), ("request_outcome", "APIConnectionError", None, "ybs"))
        self.assertEqual(self.state()[2], PARITY_REQUEST_BOUND * RUN_LIMIT)           # all slots still held until the cycle ends


class LiveRunAccountingTests(Base):
    def run_live(self, script=None, **kwargs):
        script = script or ScriptedProvider(provider="openai", caps=False)
        result = live_run(sdk_for(script), ledger_path=self.ledger_path, runs_path=self.runs_path, today=PRICE_CHECKED, observer=script.begin_role, **kwargs)
        return script, result

    def test_the_whole_cycle_is_reserved_first_and_every_role_and_phase_is_accounted(self):
        script, result = self.run_live()
        rows = self.ledger_rows()
        cycle = next(r for r in rows if r.get("cycle_id") == result["cycle_id"] and r["event"] == "cycle_reservation")
        self.assertEqual((cycle["max_requests"], cycle["request_bound_usd"], cycle["input_bound_tokens"]),
                         (RUN_LIMIT, str(PARITY_REQUEST_BOUND), PARITY_INPUT_BOUND_TOKENS))
        self.assertLessEqual(Decimal(cycle["cycle_bound_usd"]), 5)
        self.assertEqual(rows[1]["event"], "cycle_end")                                # the prior cycle precedes it untouched
        self.assertEqual(rows.index(cycle), 2)
        cells = result["table"]["per_role_phase"]
        self.assertEqual(set(cells), {f"{role}/{phase}" for role in ROLES for phase in PHASES})
        for key, cell in cells.items():
            role, phase = key.split("/")
            self.assertTrue(1 <= cell["requests"] <= worst_case_requests("openai", phase, role))
            self.assertEqual(cell["unknown_requests"], 0)
        per_run = result["table"]["per_run"]
        self.assertEqual(per_run["requests"], len(script.requests))
        self.assertEqual(per_run["requests"], sum(c["requests"] for c in cells.values()))
        self.assertEqual(per_run["input_tokens"], len(script.requests))             # the fake reports 1 input and 1 output token per request
        self.assertEqual(per_run["output_tokens"], len(script.requests))
        end = result["cycle_end"]
        self.assertEqual((end["successful_narratives"], end["requests"]), (2 * len(ROLES), len(script.requests)))
        self.assertIsNotNone(end["cost_per_successful_narrative_usd"])
        self.assertIsNotNone(end["cost_per_completed_cycle_usd"])
        spent, held = self.state()[1:]
        self.assertEqual(held, 0)
        self.assertEqual(spent, Decimal(per_run["budget_charge_usd"]) + Decimal(rows[1].get("cumulative_incurred_usd", "0")))

    def test_the_run_file_summary_and_a_replay_from_the_ledger_agree(self):
        _, result = self.run_live()
        rows = self.runs.rows(result["cycle_id"])
        events = [r["event"] for r in rows]
        self.assertEqual((events[0], events[-1], events.count("run_reservation"), events.count("run_summary")), ("run_reservation", "run_summary", 1, 1))
        summary = rows[-1]
        self.assertEqual(summary["cost_table"], json.loads(json.dumps(result["table"])))
        self.assertEqual(aggregate(self.ledger_rows(), result["cycle_id"]), result["table"])                       # identical on replay
        self.assertEqual(aggregate(self.ledger_rows(), "no-such-cycle")["per_run"]["requests"], 0)
        self.assertEqual((summary["successful_narratives"], summary["fallbacks"], summary["error"]), (20, [], None))
        self.assertTrue(all(r["failed_checks"] == [] for r in summary["roles"]))
        self.assertEqual(summary["requests"], summary["cost_table"]["per_run"]["requests"])

    def test_fallbacks_are_reported_and_not_counted_as_narratives(self):
        _, result = self.run_live(ScriptedProvider(provider="openai", caps=False, narrative="ungrounded"))
        summary = self.runs.rows(result["cycle_id"])[-1]
        self.assertEqual(len(summary["fallbacks"]), 18)
        self.assertEqual(summary["successful_narratives"], 2)
        self.assertIsNone(result["cycle_end"]["cost_per_completed_cycle_usd"])
        self.assertIsNotNone(summary["cost_per_successful_narrative_usd"])

    def test_missing_inconsistent_or_non_standard_usage_keeps_the_reservation_and_leaves_costs_null(self):
        for variant in ("missing", "inconsistent", "tier"):
            with self.subTest(variant=variant):
                self.setUp()
                script = NoUsage(provider="openai", caps=False)
                script.variant = variant
                script, result = self.run_live(script)
                per_run = result["table"]["per_run"]
                self.assertEqual(per_run["unknown_requests"], per_run["requests"])
                self.assertIsNone(per_run["budget_charge_usd"])
                self.assertEqual(self.state()[1], 0)
                self.assertEqual(self.state()[2], PARITY_REQUEST_BOUND * per_run["requests"])         # unused slots released, the rest retained
                self.assertIsNone(result["cycle_end"]["cost_per_successful_narrative_usd"])
                self.assertTrue(all(c["budget_charge_usd"] is None for c in result["table"]["per_role_phase"].values()))

    def test_requests_that_raise_are_counted_and_retained(self):
        script, result = self.run_live(Failing(provider="openai", caps=False))
        per_run = result["table"]["per_run"]
        self.assertTrue(per_run["requests"] > 0 and per_run["unknown_requests"] == per_run["requests"])
        self.assertEqual(self.state()[2], PARITY_REQUEST_BOUND * per_run["requests"])
        self.assertEqual(self.runs.rows(result["cycle_id"])[-1]["successful_narratives"], 0)

    def test_the_shared_cumulative_cap_blocks_the_run_before_any_request(self):
        bound, n = PARITY_REQUEST_BOUND, 0
        while self.state()[1] + self.state()[2] + RUN_LIMIT * bound <= BUDGET:
            n += 1
            self.ledger.start_cycle(f"fill-{n}", RUN_LIMIT, bound, PARITY_INPUT_BOUND_TOKENS)
        self.assertGreaterEqual(n, 4)
        script = ScriptedProvider(provider="openai", caps=False)
        before = self.ledger_path.read_text()
        with self.assertRaisesRegex(BudgetError, "does not fit"):
            self.run_live(script)
        self.assertEqual((script.requests, self.ledger_path.read_text(), self.runs.rows()), ([], before, []))

    def test_stale_prices_a_missing_or_unreadable_ledger_and_a_wrong_model_fail_closed(self):
        script = ScriptedProvider(provider="openai", caps=False)
        before = self.ledger_path.read_text()
        with self.assertRaises(ValueError):
            live_run(sdk_for(script), ledger_path=self.ledger_path, runs_path=self.runs_path, today="2000-01-01")
        with self.assertRaises(ValueError):
            live_run(sdk_for(script), ledger_path=Path(self.temp.name) / "absent.jsonl", runs_path=self.runs_path, today=PRICE_CHECKED)
        self.ledger_path.write_text("{partial")
        with self.assertRaises((ValueError, BudgetError)):
            live_run(sdk_for(script), ledger_path=self.ledger_path, runs_path=self.runs_path, today=PRICE_CHECKED)
        self.assertEqual(script.requests, [])
        self.ledger_path.write_text(before)
        self.assertEqual(assess(MODEL, RUN_LIMIT, self.ledger_path, PRICE_CHECKED, "parity")["fits"], True)

    def test_a_restart_sees_unresolved_reservations_and_the_same_totals(self):
        self.start()
        guard = self.guard(ScriptedProvider(provider="openai", caps=False))
        guard.begin_role("ybs", "model")
        guard.responses.create(**self.request("ybs"))
        # the process dies here: no end_cycle. A new process reads only the files.
        reopened = Ledger(self.ledger_path)
        with reopened.locked() as (_, rows):
            cycles, incurred, reserved = Ledger.state(rows)
        self.assertFalse(cycles["c1"]["ended"])
        self.assertEqual(reserved, PARITY_REQUEST_BOUND * (RUN_LIMIT - 1))                # the resolved request's slot became spend
        self.assertEqual(aggregate(rows, "c1"), aggregate(self.ledger_rows(), "c1"))
        self.assertGreater(incurred, 0)
        self.assertEqual(assess(MODEL, RUN_LIMIT, self.ledger_path, PRICE_CHECKED, "parity")["outstanding_reservations_usd"], reserved)

    def test_the_default_ledger_is_not_touched_by_these_tests(self):
        from test_openai_live_smoke import LEDGER
        self.assertNotEqual(self.ledger_path, LEDGER)
        before = LEDGER.read_bytes()
        self.run_live()
        self.assertEqual(LEDGER.read_bytes(), before)


class HygieneTests(Base):
    def test_rehearsal_sends_every_role_through_the_guard_and_the_validator_without_refusals(self):
        result = rehearse(Path(self.temp.name) / "rehearsal")
        self.assertEqual(set(result["sizes"]), set(ROLES))
        self.assertTrue(all(0 < v <= BYTE_BOUND for v in result["sizes"].values()), result["sizes"])
        self.assertTrue(all(out["summary"]["ok"] for out in result["outputs"].values()))

    def test_no_credentials_or_bodies_reach_any_file(self):
        script = ScriptedProvider(provider="openai", caps=False)
        live_run(sdk_for(script), ledger_path=self.ledger_path, runs_path=self.runs_path, today=PRICE_CHECKED, observer=script.begin_role)
        text = self.ledger_path.read_text() + self.runs_path.read_text()
        case_id = SAMPLE["case_information"]["case_id"]
        for fragment in (KEY, "sk-", case_id, "Synthetic report", "examiner_narrative", "Narrate the decision record", "TOOL RESULT",
                         AGENTS["ybs"]["system_prompt"][:60], "Authorization", "instructions"):
            self.assertNotIn(fragment, text)

    def test_the_default_suite_skips_the_live_module_and_contacts_nothing(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("RUN_LIVE_")}
        env["OPENAI_API_KEY"] = ""
        done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_openai_live_parity.py", "-v"],
                              cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
        self.assertEqual(done.returncode, 0, done.stderr[-500:])
        self.assertIn("OK (skipped=1)", done.stderr)

    def test_the_derived_total_fits_the_plan_ceiling_and_the_per_run_reservation_ceiling(self):
        self.assertEqual(RUN_LIMIT, worst_case_table("openai")["total"])
        self.assertLessEqual(RUN_LIMIT, 80)
        self.assertLessEqual(RUN_LIMIT * PARITY_REQUEST_BOUND, 5)


if __name__ == "__main__":
    unittest.main()

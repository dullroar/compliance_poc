"""Opt-in live registry-wide parity run on claude-haiku-5-5 (plans/archive/live-parity, steps 02 and 04).

Skipped unless RUN_LIVE_ANTHROPIC_PARITY=1. When it runs, every role in agents.yaml is exercised in two phases (model-directed,
then seeded) on the synthetic sample_loan.json case through the production batch and A2A path over in-process ASGI, and only
api.anthropic.com is contacted. `GuardedAnthropic` enforces the limits inside the client: zero SDK retries, a finite timeout, a
request cap per run and per role, an input-byte bound, `max_tokens`, one model, one tool per role and the standard tier.
`live_run` reserves the run's worst case once in usage/anthropic-api-ledger.jsonl before the first request, settles from
reported usage, or retains the whole reservation when any usage is missing. Run metadata (never bodies) goes to
plans/archive/live-parity/runs-anthropic.jsonl.
"""
from __future__ import annotations

import fcntl
import importlib.metadata
import json
import logging
import math
import os
import sys
import time
import uuid
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from agent_prompts import AGENTS
from agents.backends import Backend
from live_parity_common import PHASES, RUN_REQUEST_LIMIT, registry_roles, role_failures, run_registry, worst_case_requests, worst_case_table
from scripts import anthropic_cost_estimator as estimator

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "plans/archive/live-parity/runs-anthropic.jsonl"
MODEL = "claude-haiku-5-5"
MAX_TOKENS = 16384       # the Anthropic default (agents.backends.ANTHROPIC_MAX_TOKENS); asserted equal by the accounting tests
BYTE_BOUND = 100_000                    # UTF-8 bytes bound tokens from above; Haiku costs 5x above 100k input tokens
TIMEOUT = 120.0
RUN_LIMIT = worst_case_table("anthropic")["total"]
RUN_RESERVATION_CEILING = Decimal(5)    # spec R1: one conservative reservation of at most USD 5 per run
COMMAND = "RUN_LIVE_ANTHROPIC_PARITY=1 python3 -m unittest discover -s tests -p test_anthropic_live_parity.py -v"
ALLOWED_KEYS = frozenset({"model", "max_tokens", "system", "messages", "tools", "tool_choice", "output_config"})
OUTPUT_CONFIG = {"effort": "low"}              # the repository default for Claude 5-family narration (compliance_common.tools)
USAGE_KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
assert RUN_LIMIT <= RUN_REQUEST_LIMIT


class GuardRefusal(Exception):
    """A request the guard refused before sending it. Deliberately not a RuntimeError: the runner must not turn it into a fallback."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def today_denver() -> str:
    return datetime.now(ZoneInfo("America/Denver")).date().isoformat()


class RunFile:
    """Append-only, fsynced JSON-lines run metadata. Rows hold counts, labels, hashes and money, never bodies."""

    def __init__(self, path: Path | str = RUNS) -> None:
        self.path = Path(path)

    def append(self, row: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0, os.SEEK_END)
            f.write(json.dumps({**row, "timestamp": now()}, sort_keys=True, separators=(",", ":")) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def rows(self, run_id: str | None = None) -> list[dict]:
        if not self.path.is_file():
            return []
        with self.path.open(encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]
        return [r for r in rows if run_id is None or r.get("run_id") == run_id]


def _jsonable(value):
    dump = getattr(value, "model_dump", None)
    return dump(mode="json") if dump else str(value)


def request_bytes(request: dict) -> int:
    """UTF-8 size of the JSON request. A token is at least one byte, so this bounds the input tokens from above."""
    return len(json.dumps(request, ensure_ascii=False, separators=(",", ":"), default=_jsonable).encode("utf-8"))


def read_usage(response) -> dict | None:
    """Reported usage, or None when it is missing, malformed or not standard-tier (the reservation is then retained)."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    values = {key: getattr(usage, key, None) for key in USAGE_KEYS}
    for key in ("cache_creation_input_tokens", "cache_read_input_tokens"):
        if values[key] is None:                 # not reported when no caching applied
            values[key] = 0
    if any(type(v) is not int or v < 0 for v in values.values()):
        return None
    if getattr(usage, "service_tier", None) not in (None, "standard"):
        return None
    return values


def usage_cost(usage: dict | None) -> Decimal | None:
    """Cost from reported usage under the estimator's conservative assumptions (cache writes at 2x input, US premium 1.1x).
    The four token kinds are disjoint in the Anthropic usage object, so nothing is counted twice."""
    if usage is None:
        return None
    total_input = usage["input_tokens"] + usage["cache_creation_input_tokens"] + usage["cache_read_input_tokens"]
    rate_in, rate_out = estimator.rates_for(MODEL, total_input)
    tokens = (Decimal(usage["input_tokens"]) + usage["cache_creation_input_tokens"] * Decimal(2) + usage["cache_read_input_tokens"] * Decimal("0.1"))
    return (tokens * rate_in + Decimal(usage["output_tokens"]) * rate_out) * Decimal("1.1") / Decimal(1_000_000)


def _finite_timeout(timeout) -> bool:
    values = [getattr(timeout, k, None) for k in ("connect", "read", "write", "pool")] if hasattr(timeout, "read") else [timeout]
    return all(isinstance(v, (int, float)) and not isinstance(v, bool) and 0 < v and math.isfinite(v) for v in values)


class _GuardedMessages:
    def __init__(self, guard: "GuardedAnthropic") -> None:
        self.guard = guard

    def create(self, **request):
        return self.guard.send(request)


class GuardedAnthropic:
    """The only object the Backend can reach: `.messages.create` and `.begin_role`. Everything is checked before a request leaves."""

    def __init__(self, sdk, *, run_id: str, reservation_id: str | None, runs: RunFile, limit: int = RUN_LIMIT,
                 byte_bound: int = BYTE_BOUND, model: str = MODEL, max_tokens: int = MAX_TOKENS, observer=None) -> None:
        if getattr(sdk, "max_retries", None) != 0:
            raise GuardRefusal("SDK retries must be disabled (max_retries=0)")
        if not _finite_timeout(getattr(sdk, "timeout", None)):
            raise GuardRefusal("the SDK timeout must be finite")
        self._sdk, self.run_id, self.reservation_id, self.runs = sdk, run_id, reservation_id, runs
        self.limit, self.byte_bound, self.model, self.max_tokens, self.observer = limit, byte_bound, model, max_tokens, observer
        self.messages = _GuardedMessages(self)
        self.role = self.phase = None
        self.sent = self.role_sent = 0
        self.unknown_cost = False           # a request was sent whose cost is not known: keep the whole reservation
        self.costs: list[Decimal] = []
        self.truncated: set[tuple[str, str]] = set()   # (role, phase) pairs with a response that stopped at max_tokens

    def begin_role(self, role: str, phase: str) -> None:
        if role not in AGENTS or phase not in PHASES:
            raise GuardRefusal("unknown role or phase")
        self.role, self.phase, self.role_sent = role, phase, 0
        if self.observer:
            self.observer(role, phase)

    def refuse(self, reason: str) -> None:
        self.runs.append({"event": "refusal", "run_id": self.run_id, "role": self.role, "phase": self.phase, "reason": reason})
        raise GuardRefusal(reason)

    def check(self, request: dict) -> int:
        if not self.reservation_id:
            self.refuse("no durable reservation")
        if self.role is None:
            self.refuse("no role context")
        if not set(request) <= ALLOWED_KEYS or not {"model", "max_tokens", "system", "messages"} <= set(request):
            self.refuse("unexpected request fields")
        if request["model"] != self.model:
            self.refuse("unexpected model")
        if request["max_tokens"] != self.max_tokens:
            self.refuse("unexpected max_tokens")
        if request.get("output_config") != OUTPUT_CONFIG:
            self.refuse("unexpected output_config")
        tool = AGENTS[self.role].get("tool")
        tools, choice = request.get("tools"), request.get("tool_choice")
        if tool:
            if tools is not None and (len(tools) != 1 or not isinstance(tools[0], dict) or set(tools[0]) != {"name", "description", "input_schema"}
                                      or tools[0]["name"] != tool):
                self.refuse("unexpected tool")
            if choice is not None and (not isinstance(choice, dict) or choice.get("type") not in ("tool", "auto")
                                       or choice.get("disable_parallel_tool_use") is not True
                                       or (choice["type"] == "tool" and choice.get("name") != tool)):
                self.refuse("unexpected tool_choice")
            if (tools is None) != (choice is None):
                self.refuse("tools and tool_choice must go together")
        elif tools or choice:
            self.refuse("this role has no tool")
        system, messages = request["system"], request["messages"]
        if not isinstance(system, str) or not system.startswith(AGENTS[self.role]["system_prompt"]):
            self.refuse("system prompt is not the repository prompt")
        if not isinstance(messages, list) or not messages or not isinstance(messages[0], dict) or messages[0].get("role") != "user":
            self.refuse("unexpected message structure")
        size = request_bytes(request)
        if size > self.byte_bound:
            self.refuse(f"request exceeds the {self.byte_bound}-byte input bound")
        if self.sent >= self.limit:
            self.refuse("run request cap reached")
        if self.role_sent >= worst_case_requests("anthropic", self.phase, self.role):
            self.refuse("role request cap reached")
        return size

    def send(self, request: dict):
        size = self.check(request)
        self.sent += 1
        self.role_sent += 1
        seq, row = self.sent, {"run_id": self.run_id, "sequence": self.sent, "role": self.role, "phase": self.phase, "model": self.model,
                               "bytes": size, "max_tokens": request["max_tokens"], "tools": bool(request.get("tools")),
                               "tool_choice": (request.get("tool_choice") or {}).get("type")}
        self.runs.append({"event": "request_start", **row})                  # durable before the request leaves
        started = time.monotonic()
        try:
            response = self._sdk.messages.create(**request, service_tier="standard_only")
        except BaseException as exc:
            self.unknown_cost = True                                           # it may have been processed and billed
            self.runs.append({"event": "request_outcome", "run_id": self.run_id, "sequence": seq, "role": self.role, "phase": self.phase,
                              "outcome": type(exc).__name__, "usage": None, "cost_usd": None,
                              "elapsed_seconds": round(time.monotonic() - started, 3)})
            if not isinstance(exc, Exception):
                raise
            raise GuardRefusal("Anthropic request failed: " + type(exc).__name__) from None
        usage = read_usage(response)
        cost = usage_cost(usage)
        if getattr(response, "stop_reason", None) == "max_tokens":
            self.truncated.add((self.role, self.phase))
        if cost is None:
            self.unknown_cost = True
        else:
            self.costs.append(cost)
        self.runs.append({"event": "request_outcome", "run_id": self.run_id, "sequence": seq, "role": self.role, "phase": self.phase,
                          "outcome": "response", "stop_reason": getattr(response, "stop_reason", None), "usage": usage,
                          "cost_usd": None if cost is None else str(cost), "elapsed_seconds": round(time.monotonic() - started, 3)})
        return response


def aggregate(rows: list[dict]) -> dict:
    """Per-role/phase and per-run totals from request rows alone, so a replay of the file gives identical numbers.
    A total is None (unknown) as soon as any contributing request has unknown cost or usage."""
    starts = {(r["run_id"], r["sequence"]): r for r in rows if r.get("event") == "request_start"}
    outcomes = {(r["run_id"], r["sequence"]): r for r in rows if r.get("event") == "request_outcome"}
    table: dict[tuple[str, str], dict] = {}
    for key, start in starts.items():
        out = outcomes.get(key)
        cell = table.setdefault((start["role"], start["phase"]), {"requests": 0, "cost": Decimal(0), "unknown": 0,
                                                                  **{k: 0 for k in USAGE_KEYS}})
        cell["requests"] += 1
        cost = None if out is None or out.get("cost_usd") is None else Decimal(out["cost_usd"])
        if cost is None:
            cell["unknown"] += 1
        else:
            cell["cost"] += cost
            for k in USAGE_KEYS:
                cell[k] += out["usage"][k]
    total = {"requests": sum(c["requests"] for c in table.values()), "unknown": sum(c["unknown"] for c in table.values()),
             "cost": sum((c["cost"] for c in table.values()), Decimal(0)), **{k: sum(c[k] for c in table.values()) for k in USAGE_KEYS}}
    return {"cells": table, "total": total}


def cost_table(rows: list[dict]) -> dict:
    agg = aggregate(rows)
    cells = {f"{role}/{phase}": {"requests": c["requests"], "unknown_requests": c["unknown"],
                                 "cost_usd": None if c["unknown"] else str(c["cost"]), **{k: c[k] for k in USAGE_KEYS}}
             for (role, phase), c in sorted(agg["cells"].items())}
    total = agg["total"]
    return {"per_role_phase": cells, "per_run": {"requests": total["requests"], "unknown_requests": total["unknown"],
                                                  "cost_usd": None if total["unknown"] else str(total["cost"]), **{k: total[k] for k in USAGE_KEYS}}}


# Owner-approved (plans/archive/live-parity/exception-record.md, 2026-11-07, review by 2026-12-07): the narrative report is longer than the
# output cap on this model. It is still detected, recorded and reported; it no longer fails the gate. No other role is excused.
TOLERATED_TRUNCATION = frozenset({"narrative"})


def flag_truncation(out: dict, phase: str, truncated: set, tolerated: frozenset = TOLERATED_TRUNCATION) -> None:
    """A reply cut off at max_tokens is not a finished narrative, even when some text came back: fail that role and phase,
    except for a role named in the exception record, which is marked `tolerated` instead."""
    for record in out["records"]:
        if (record["role"], phase) in truncated:
            if record["role"] in tolerated:
                record["tolerated"] = ["truncated_at_max_tokens"]
            else:
                record["checks"]["not_truncated"] = False
    summary = out["summary"]
    summary["failed"] = {r["role"]: role_failures(r) for r in out["records"] if role_failures(r)}
    summary["tolerated"] = {r["role"]: r["tolerated"] for r in out["records"] if r.get("tolerated")}
    summary["ok"] = not summary["failed"] and len(out["records"]) == len(registry_roles())


def live_run(sdk, *, ledger: Path | str = estimator.LEDGER, runs_path: Path | str = RUNS, today: str | None = None,
             observer=None, drive=run_registry) -> dict:
    """Reserve, run both phases, settle or retain, write the metadata. Fails closed before any request on any precondition."""
    today = today or today_denver()
    bound = estimator.estimate(MODEL, RUN_LIMIT, BYTE_BOUND, MAX_TOKENS, today)   # a stale price date or bad bounds raise here
    if bound > RUN_RESERVATION_CEILING:
        raise estimator.BudgetError("the run's worst-case bound exceeds the per-run reservation ceiling")
    runs, run_id = RunFile(runs_path), uuid.uuid4().hex
    reservation_id, bound = estimator.reserve(Path(ledger), MODEL, RUN_LIMIT, BYTE_BOUND, MAX_TOKENS, today)      # raises when unknown or short
    runs.append({"event": "run_reservation", "run_id": run_id, "reservation_id": reservation_id, "model": MODEL, "bound_usd": str(bound),
                 "request_limit": RUN_LIMIT, "input_bound_bytes": BYTE_BOUND, "max_tokens": MAX_TOKENS, "timeout_seconds": TIMEOUT,
                 "pricing_url": estimator.PRICE_URL, "pricing_checked": estimator.PRICE_CHECKED, "python_version": sys.version.split()[0],
                 "sdk_version": importlib.metadata.version("anthropic"), "command": COMMAND, "worst_case": worst_case_table("anthropic")["per_role"]})
    guard = GuardedAnthropic(sdk, run_id=run_id, reservation_id=reservation_id, runs=runs, observer=observer)
    backend = Backend("anthropic", MODEL, client=guard)
    outputs: dict[str, dict] = {}
    started, error = time.monotonic(), None
    try:
        for phase in PHASES:
            outputs[phase] = drive(backend, phase)
            flag_truncation(outputs[phase], phase, guard.truncated)
    except BaseException as exc:
        error = type(exc).__name__
        raise
    finally:
        settlement = None
        if not guard.unknown_cost:
            total = sum(guard.costs, Decimal(0))
            estimator.settle(Path(ledger), reservation_id, total, "api-usage")
            settlement = str(total)
        rows = runs.rows(run_id)
        table = cost_table(rows)
        records = [r for out in outputs.values() for r in out["records"]]
        good = sum(1 for r in records if r["narrative_source"] in ("model", "model_retry") and not role_failures(r))
        per_run_cost = table["per_run"]["cost_usd"]
        runs.append({"event": "run_summary", "run_id": run_id, "reservation_id": reservation_id, "error": error,
                     "elapsed_seconds": round(time.monotonic() - started, 3), "requests": guard.sent, "reservation_usd": str(bound),
                     "settlement_usd": settlement, "reservation_retained": settlement is None,
                     "roles": [{"role": r["role"], "phase": r["phase"], "narrative_source": r["narrative_source"],
                                "guard_attempts": r["guard_attempts"], "violation_kinds": r["violation_kinds"], "tolerated": r.get("tolerated", []), "tool_calls": r["tool_calls"],
                                "failed_checks": role_failures(r),
                                "elapsed_seconds": r["elapsed_seconds"]} for r in records],
                     "fallbacks": [f"{r['role']}/{r['phase']}" for r in records if r["narrative_source"] == "deterministic_fallback"],
                     "successful_narratives": good, "cost_table": table,
                     "tolerated": [f"{r['role']}/{r['phase']}: {', '.join(r['tolerated'])}" for r in records if r.get("tolerated")],
                     "cost_per_successful_narrative_usd": str(Decimal(per_run_cost) / good) if per_run_cost is not None and good else None})
    return {"run_id": run_id, "reservation_id": reservation_id, "outputs": outputs, "settlement": settlement, "table": table}


def offline_payload_inspection() -> dict[str, int]:
    """Largest request per role from a complete offline run against the recording fake (no network, no credentials)."""
    from live_parity_common import ScriptedProvider
    script = ScriptedProvider(provider="anthropic", caps=False)
    for phase in PHASES:
        run_registry(script.backend(), phase)
    return {role: max(r["bytes"] for r in script.requests if r["role"] == role) for role in registry_roles()}


@unittest.skipUnless(os.getenv("RUN_LIVE_ANTHROPIC_PARITY") == "1", "set RUN_LIVE_ANTHROPIC_PARITY=1 for the live Anthropic parity run")
class AnthropicLiveParity(unittest.TestCase):
    def test_every_registry_role_in_both_phases(self):
        import anthropic
        from dotenv import dotenv_values

        self.assertEqual(today_denver(), estimator.PRICE_CHECKED, "Verify rates at the cited URL and update the estimator and its tests first")
        key = os.getenv("ANTHROPIC_API_KEY") or dotenv_values(ROOT / ".env").get("ANTHROPIC_API_KEY")
        self.assertTrue(key, "ANTHROPIC_API_KEY is required")
        sizes = offline_payload_inspection()
        self.assertTrue(all(0 < size <= BYTE_BOUND for size in sizes.values()), f"outbound payload over the bound: {sizes}")
        old_disable = logging.root.manager.disable
        logging.disable(logging.CRITICAL)
        sdk = anthropic.Anthropic(api_key=key, base_url="https://api.anthropic.com", timeout=TIMEOUT, max_retries=0)
        try:
            result = live_run(sdk)
        finally:
            sdk.close()
            logging.disable(old_disable)
        print("\n" + json.dumps({"run_id": result["run_id"], "settlement_usd": result["settlement"], "cost_table": result["table"]}, indent=1, sort_keys=True))
        for phase, out in result["outputs"].items():
            for record in out["records"]:
                with self.subTest(role=record["role"], phase=phase):
                    self.assertEqual(role_failures(record), [], f"{record['role']}/{phase}: narrative_source={record['narrative_source']}")
            self.assertTrue(out["summary"]["ok"], out["summary"]["failed"])
        self.assertIsNotNone(result["settlement"], "usage was not fully reported; the reservation is retained")


if __name__ == "__main__":
    unittest.main()

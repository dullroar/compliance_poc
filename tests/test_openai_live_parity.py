"""Opt-in live registry-wide parity run on gpt-6-luna (plans/archive/live-parity, steps 03 and 05).

Skipped unless RUN_LIVE_OPENAI_PARITY=1. Every role in agents.yaml is exercised in two phases (model-directed, then seeded) on the
synthetic sample_loan.json case through the production batch and A2A path over in-process ASGI; only api.openai.com is contacted.
`GuardedOpenAI` enforces the limits inside the client: zero SDK retries, a finite timeout, `store: false`, the standard tier,
`max_output_tokens=8192`, one model, one function per role, a request cap per run and per role, a 100000-byte input bound, and the
outbound-payload validation of the smoke test applied to every role. The whole cycle is reserved in the shared ledger
(plans/archive/openai-smoketest/runs.jsonl) before the first request; run metadata (never bodies) goes to
plans/archive/live-parity/runs-openai.jsonl.
"""
from __future__ import annotations

import contextlib
import fcntl
import importlib.metadata
import json
import logging
import math
import os
import sys
import threading
import time
import unittest
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import agents.runner as runner
from agent_prompts import AGENTS
from agents.backends import Backend
from compliance_common.narrative_schema import NARRATIVE_SCHEMA
from compliance_common.regulations import regulation_text
from compliance_mcp.registry import adapter as domain_adapter
from live_parity_common import PHASES, RUN_REQUEST_LIMIT, RoleScoped, registry_roles, role_failures, run_registry, worst_case_requests, worst_case_table
from scripts.openai_cost_estimator import assess
from test_agent_parity import SAMPLE
from test_openai_live_smoke import (LEDGER, MODEL, OUTPUT_LIMIT, PARITY_INPUT_BOUND_TOKENS, PARITY_REQUEST_BOUND, PRICE_CHECKED, BudgetError,
                                    Ledger, LiveRequestError, get, read_usage)

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "plans/archive/live-parity/runs-openai.jsonl"
BYTE_BOUND = PARITY_INPUT_BOUND_TOKENS          # UTF-8 bytes bound tokens from above
TIMEOUT = 120.0
RUN_LIMIT = worst_case_table("openai")["total"]
COMMAND = "RUN_LIVE_OPENAI_PARITY=1 python3 -m unittest discover -s tests -p test_openai_live_parity.py -v"
ALLOWED_KEYS = frozenset({"model", "instructions", "input", "max_output_tokens", "store", "tools", "tool_choice", "parallel_tool_calls", "text"})
SCHEMA_FORMAT = {"format": {"type": "json_schema", "name": "compliance_narrative", "strict": True, "schema": NARRATIVE_SCHEMA}}
DECISION_BLOCK = "\n\nTOOL RESULT (authoritative decision record; explain it, do not change it)"
assert RUN_LIMIT <= RUN_REQUEST_LIMIT


class GuardRefusal(BudgetError):
    """A request refused before it left. Not a RuntimeError: the runner must not turn it into a harness fallback."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def today_denver() -> str:
    return datetime.now(ZoneInfo("America/Denver")).date().isoformat()


class RunFile:
    """Append-only, fsynced JSON-lines run metadata: counts, labels and money, never bodies."""

    def __init__(self, path: Path | str = RUNS) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()          # one writer at a time inside the process; flock covers other processes

    def append(self, row: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self.path.open("a+", encoding="utf-8") as f:
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
    """UTF-8 size of the JSON request; a token is at least one byte, so this bounds the input tokens from above."""
    return len(json.dumps(request, ensure_ascii=False, separators=(",", ":"), default=_jsonable).encode("utf-8"))


def _finite_timeout(timeout) -> bool:
    values = [getattr(timeout, k, None) for k in ("connect", "read", "write", "pool")] if hasattr(timeout, "read") else [timeout]
    return all(isinstance(v, (int, float)) and not isinstance(v, bool) and 0 < v and math.isfinite(v) for v in values)


# --- outbound validation (the smoke test's pattern, applied to every role) --------------------------------------------------
_expected_cache: dict[str, tuple[str, str | None]] = {}
_LOAN = [SAMPLE]                    # the synthetic loan the outbound check is pinned to; sample_loan.json unless `use_loan` says otherwise


@contextlib.contextmanager
def use_loan(loan: dict):
    """Pin the outbound validation to another synthetic loan (for example the every-regime fixture) while the block runs."""
    previous = _LOAN[0]
    _LOAN[0] = loan
    _expected_cache.clear()
    try:
        yield
    finally:
        _LOAN[0] = previous
        _expected_cache.clear()


def expected_outbound(role: str) -> tuple[str, str | None]:
    """(instructions, first user content) a role must send. Domain roles are fully determined by repository prompts, the pinned
    regulation snapshot and the synthetic fixture; the auditor's and the narrative role's cases depend on earlier results, so the
    narrative role's content is checked structurally (None) and the auditor's narration input is static by design."""
    if role in _expected_cache:
        return _expected_cache[role]
    agent = AGENTS[role]
    tool = agent.get("tool")
    system = agent["system_prompt"]
    if not tool:
        value = (system, None)
    else:
        domain = tool.removesuffix("_evaluate")
        reg_text, _ = regulation_text(domain, runner.DEFAULT_OPTIONS["max_regulation_chars"])
        if reg_text:
            system = system + "\n\n" + runner.REGULATIONS_HEADER + reg_text
        adapt = domain_adapter(domain)
        if role == "auditor":
            user = runner._narration_input(agent, domain, {}, {"case": {}}, adapt)
        else:
            canonical, reason = adapt.tool_arguments(_LOAN[0])
            if canonical is None:
                raise BudgetError("the synthetic fixture has no canonical input for " + role + ": " + str(reason))
            user = runner._narration_input(agent, domain, _LOAN[0], canonical, adapt)
        value = (system, user)
    _expected_cache[role] = value
    return value


def validate_outbound(request: dict, role: str, phase: str) -> None:
    """Raise GuardRefusal unless the request is exactly what the production runner sends for this role and phase."""
    def refuse(reason):
        raise GuardRefusal(reason)

    if not set(request) <= ALLOWED_KEYS or not {"model", "instructions", "input", "max_output_tokens", "store"} <= set(request):
        refuse("unexpected request fields")
    if request["model"] != MODEL or request["store"] is not False or request["max_output_tokens"] != OUTPUT_LIMIT:
        refuse("unexpected model, store or max_output_tokens")
    agent, tool = AGENTS[role], AGENTS[role].get("tool")
    system, user = expected_outbound(role)
    if request["instructions"] != system:
        refuse("instructions are not the repository prompt")
    tools, choice, text = request.get("tools"), request.get("tool_choice"), request.get("text")
    if tool:
        if text != SCHEMA_FORMAT:
            refuse("unexpected response format")
        if tools is not None:
            if (not isinstance(tools, list) or len(tools) != 1 or not isinstance(tools[0], dict) or tools[0].get("type") != "function"
                    or tools[0].get("name") != tool or tools[0].get("strict") is not False
                    or set(tools[0]) != {"type", "name", "description", "parameters", "strict"}):
                refuse("unexpected tool")
            if request.get("parallel_tool_calls") is not False:
                refuse("parallel tool calls must be disabled")
            if choice not in ("auto", "none", {"type": "function", "name": tool}):
                refuse("unexpected tool_choice")
        elif choice is not None or "parallel_tool_calls" in request:
            refuse("tool settings without tools")
    elif tools or choice is not None or text is not None or "parallel_tool_calls" in request:
        refuse("this role has no tool and no response format")
    items = request["input"]
    if not isinstance(items, list) or not items or not isinstance(items[0], dict) or items[0].get("role") != "user":
        refuse("unexpected input structure")
    content = items[0].get("content")
    if not isinstance(content, str):
        refuse("unexpected input content")
    if user is not None:
        if content != user and not content.startswith(user + DECISION_BLOCK):
            refuse("first user turn is not the expected case narration")
    else:                                                                  # the narrative role: prefix, then a JSON object of earlier results
        prefix = agent.get("user_message_prefix", runner.DEFAULT_PREFIX) + "\n\n"
        try:
            body, end = json.JSONDecoder().raw_decode(content[len(prefix):])
        except ValueError:
            body, end = None, 0
        domains = [k for k in registry_roles() if AGENTS[k].get("tool")]
        if not content.startswith(prefix) or not isinstance(body, dict) or list(body) != domains or content[len(prefix) + end:].strip():
            refuse("unexpected narrative input")
    if phase == "seeded" and tool and len(items) >= 3 and isinstance(items[1], dict) and items[1].get("type") == "function_call":
        try:
            arguments = json.loads(items[1]["arguments"])
            result = json.loads(items[2]["output"])
        except (KeyError, TypeError, ValueError):
            refuse("unreadable seeded exchange")
        if items[1].get("name") != tool or not isinstance(arguments, dict) or set(arguments) != {"case"} or not isinstance(result, dict):
            refuse("unexpected seeded exchange")
        if role != "auditor" and arguments != domain_adapter(tool.removesuffix("_evaluate")).tool_arguments(_LOAN[0])[0]:
            refuse("seeded arguments differ from the canonical case")


# --- the guarded client -------------------------------------------------------------------------------------------------------
class _GuardedResponses:
    def __init__(self, guard: "GuardedOpenAI") -> None:
        self.guard = guard

    def create(self, **request):
        return self.guard.send(request)


class GuardedOpenAI(RoleScoped):
    """The only client object the Backend can reach: `.responses.create` and `.begin_role`.

    Safe for simultaneous calls: the cap check, the counters, the ledger reservation and the request_start row happen together under
    `self.lock`; the request itself does not hold it. Each calling chain has its own role."""

    def __init__(self, sdk, ledger: Ledger, cycle_id: str, runs: RunFile, *, limit: int = RUN_LIMIT, byte_bound: int = BYTE_BOUND,
                 validate=validate_outbound, observer=None) -> None:
        if getattr(sdk, "max_retries", None) != 0:
            raise GuardRefusal("SDK retries must be disabled (max_retries=0)")
        if not _finite_timeout(getattr(sdk, "timeout", None)):
            raise GuardRefusal("the SDK timeout must be finite")
        self._sdk, self.ledger, self.cycle_id, self.runs = sdk, ledger, cycle_id, runs
        self.limit, self.byte_bound, self.validate, self.observer = limit, byte_bound, validate, observer
        self.responses = _GuardedResponses(self)
        self._init_scope()

    def begin_role(self, role: str, phase: str) -> None:
        if role not in AGENTS or phase not in PHASES:
            raise GuardRefusal("unknown role or phase")
        self._enter_role(role, phase)
        if self.observer:
            self.observer(role, phase)

    def refuse(self, reason: str) -> None:
        context = self._context
        self.runs.append({"event": "refusal", "run_id": self.cycle_id, "role": context.role, "phase": context.phase, "reason": reason})
        raise GuardRefusal(reason)

    def send(self, request: dict):
        context = self._context
        with self.lock:                  # check, count, the ledger reservation and the start row are one step
            if context.role is None:
                self.refuse("no role context")
            try:
                self.validate(request, context.role, context.phase)
            except GuardRefusal as exc:
                self.refuse(str(exc))
            size = request_bytes(request)
            if size > self.byte_bound:
                self.refuse(f"request exceeds the {self.byte_bound}-byte input bound")
            if self.sent >= self.limit:
                self.refuse("run request cap reached")
            if context.sent >= worst_case_requests("openai", context.phase, context.role):
                self.refuse("role request cap reached")
            request = {**request, "service_tier": "default"}
            seq = self.ledger.start_request(self.cycle_id, context.phase, context.role)         # durable reservation before the request leaves
            self.sent += 1
            context.sent += 1
            self.runs.append({"event": "request_start", "run_id": self.cycle_id, "sequence": seq, "role": context.role, "phase": context.phase,
                              "bytes": size, "tool_choice": request.get("tool_choice") if isinstance(request.get("tool_choice"), str)
                              else (request.get("tool_choice") or {}).get("type"), "tools": bool(request.get("tools"))})
        started = time.monotonic()
        try:
            response = self._sdk.responses.create(**request)
        except BaseException as exc:
            self.ledger.outcome(self.cycle_id, context.phase, seq, type(exc).__name__, None, time.monotonic() - started, role=context.role)
            if not isinstance(exc, Exception):
                raise
            raise LiveRequestError("OpenAI request failed: " + type(exc).__name__) from None
        self.ledger.outcome(self.cycle_id, context.phase, seq, "response", read_usage(response), time.monotonic() - started,
                            get(response, "service_tier"), role=context.role)
        return response


# --- aggregation (replayable from ledger rows alone) -----------------------------------------------------------------------
USAGE_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_tokens", "total_tokens")


def aggregate(rows: list[dict], cycle_id: str) -> dict:
    """Per (role, phase) and per-run request, usage and cost totals from ledger rows. A total is None (unknown) as soon as one
    contributing request lacks it; cached and reasoning tokens are reported but are parts of input and output, never added again."""
    starts = [r for r in rows if r.get("cycle_id") == cycle_id and r.get("event") == "request_reservation"]
    outcomes = {r["sequence"]: r for r in rows if r.get("cycle_id") == cycle_id and r.get("event") == "request_outcome"}
    cells: dict[str, dict] = {}
    for start in starts:
        out = outcomes.get(start["sequence"])
        cell = cells.setdefault(f"{start.get('role')}/{start['mode']}", {"requests": 0, "unknown_requests": 0, "charge": Decimal(0),
                                                                          "estimates": [], **{f: [] for f in USAGE_FIELDS}})
        cell["requests"] += 1
        charge = None if out is None or out.get("budget_charge_usd") is None else Decimal(out["budget_charge_usd"])
        if charge is None:
            cell["unknown_requests"] += 1
        else:
            cell["charge"] += charge
        cell["estimates"].append(None if out is None else out.get("estimated_cost_usd"))
        for f in USAGE_FIELDS:
            cell[f].append(((out or {}).get("usage") or {}).get(f))

    def finish(cell):
        total = lambda values: sum(values) if values and all(type(v) is int for v in values) else None
        estimates = cell["estimates"]
        return {"requests": cell["requests"], "unknown_requests": cell["unknown_requests"],
                "budget_charge_usd": None if cell["unknown_requests"] else str(cell["charge"]),
                "estimated_cost_usd": str(sum((Decimal(e) for e in estimates), Decimal(0))) if estimates and all(e is not None for e in estimates) else None,
                **{f: total(cell[f]) for f in USAGE_FIELDS}}

    per_cell = {key: finish(cell) for key, cell in sorted(cells.items())}
    merged = {"requests": 0, "unknown_requests": 0, "charge": Decimal(0), "estimates": [], **{f: [] for f in USAGE_FIELDS}}
    for cell in cells.values():
        merged["requests"] += cell["requests"]
        merged["unknown_requests"] += cell["unknown_requests"]
        merged["charge"] += cell["charge"]
        merged["estimates"] += cell["estimates"]
        for f in USAGE_FIELDS:
            merged[f] += cell[f]
    return {"per_role_phase": per_cell, "per_run": finish(merged)}


def live_run(sdk, *, ledger_path: Path | str = LEDGER, runs_path: Path | str = RUNS, today: str | None = None, observer=None,
             drive=run_registry) -> dict:
    """Preflight, reserve the whole cycle, run both phases, record outcomes. Fails closed before any request."""
    today = today or today_denver()
    pre = assess(MODEL, RUN_LIMIT, Path(ledger_path), today, "parity")          # stale price, unreadable ledger, unknown model raise here
    if not pre["fits"]:
        raise BudgetError("the cycle reservation does not fit the remaining cumulative budget or the per-run ceiling")
    ledger, runs, cycle_id = Ledger(ledger_path), RunFile(runs_path), uuid.uuid4().hex
    ledger.start_cycle(cycle_id, RUN_LIMIT, PARITY_REQUEST_BOUND, PARITY_INPUT_BOUND_TOKENS, COMMAND)
    runs.append({"event": "run_reservation", "run_id": cycle_id, "model": MODEL, "request_limit": RUN_LIMIT,
                 "request_bound_usd": str(PARITY_REQUEST_BOUND), "cycle_bound_usd": str(PARITY_REQUEST_BOUND * RUN_LIMIT),
                 "input_bound_bytes": BYTE_BOUND, "max_output_tokens": OUTPUT_LIMIT, "timeout_seconds": TIMEOUT,
                 "pricing_checked": PRICE_CHECKED, "python_version": sys.version.split()[0], "sdk_version": importlib.metadata.version("openai"),
                 "command": COMMAND, "worst_case": worst_case_table("openai")["per_role"]})
    guard = GuardedOpenAI(sdk, ledger, cycle_id, runs, observer=observer)
    backend = Backend("openai", MODEL, client=guard)
    outputs: dict[str, dict] = {}
    outcomes: dict[str, dict] = {}
    started, error = time.monotonic(), None
    try:
        for phase in PHASES:
            phase_started = time.monotonic()
            outputs[phase] = drive(backend, phase)
            outcomes[phase] = {"passed": bool(outputs[phase]["summary"]["ok"]), "failed_roles": sorted(outputs[phase]["summary"]["failed"]),
                               "elapsed_seconds": round(time.monotonic() - phase_started, 3)}
    except BaseException as exc:
        error = type(exc).__name__
        raise
    finally:
        records = [r for out in outputs.values() for r in out["records"]]
        good = sum(1 for r in records if r["narrative_source"] in ("model", "model_retry") and not role_failures(r))
        elapsed = time.monotonic() - started
        ledger.end_cycle(cycle_id, outcomes, elapsed, successes=good, expected_successes=2 * len(registry_roles()))
        with ledger.locked() as (_, rows):
            table = aggregate(rows, cycle_id)
            end = next((r for r in rows if r.get("cycle_id") == cycle_id and r.get("event") == "cycle_end"), {})
        runs.append({"event": "run_summary", "run_id": cycle_id, "error": error, "elapsed_seconds": round(elapsed, 3), "requests": guard.sent,
                     "phases": outcomes, "roles": [{"role": r["role"], "phase": r["phase"], "narrative_source": r["narrative_source"],
                                                    "guard_attempts": r["guard_attempts"], "violation_kinds": r["violation_kinds"],
                                                    "paragraph_failures": r["paragraph_failures"], "paragraph_sources": r["paragraph_sources"], "tool_calls": r["tool_calls"],
                                                    "failed_checks": role_failures(r), "elapsed_seconds": r["elapsed_seconds"]} for r in records],
                     "fallbacks": [f"{r['role']}/{r['phase']}" for r in records if r["narrative_source"] == "deterministic_fallback"],
                     "successful_narratives": good, "cost_table": table, "cumulative_incurred_usd": end.get("cumulative_incurred_usd"),
                     "cumulative_reserved_usd": end.get("cumulative_reserved_usd"),
                     "cost_per_successful_narrative_usd": end.get("cost_per_successful_narrative_usd")})
    return {"cycle_id": cycle_id, "outputs": outputs, "outcomes": outcomes, "table": table, "cycle_end": end}


def rehearse(workdir: Path, drive=run_registry) -> dict:
    """The complete run against the offline recording fake, with a temporary ledger and run file: every role's real outbound
    request goes through the guard and the validator before any request is made to OpenAI. Raises unless nothing was refused."""
    import httpx
    import openai
    from live_parity_common import ScriptedProvider
    workdir.mkdir(parents=True, exist_ok=True)
    ledger = workdir / "ledger.jsonl"
    Ledger(ledger).start_cycle("rehearsal-prior", 1)
    Ledger(ledger).end_cycle("rehearsal-prior", {}, 0)
    script = ScriptedProvider(provider="openai", caps=False)
    sdk = openai.OpenAI(api_key="offline-placeholder", max_retries=0, timeout=5.0, http_client=httpx.Client(transport=httpx.MockTransport(script.handler)))
    result = live_run(sdk, ledger_path=ledger, runs_path=workdir / "runs.jsonl", today=PRICE_CHECKED, observer=script.begin_role, drive=drive)
    if any(r["event"] == "refusal" for r in RunFile(workdir / "runs.jsonl").rows()):
        raise BudgetError("the rehearsal was refused by the guard")
    result["sizes"] = {role: max(r["bytes"] for r in script.requests if r["role"] == role) for role in registry_roles()}
    return result


@unittest.skipUnless(os.getenv("RUN_LIVE_OPENAI_PARITY") == "1", "set RUN_LIVE_OPENAI_PARITY=1 for the live OpenAI parity run")
class OpenAILiveParity(unittest.TestCase):
    def test_every_registry_role_in_both_phases(self):
        import tempfile
        import openai
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
            result = live_run(sdk)
        finally:
            sdk.close()
            logging.disable(old_disable)
        print("\n" + json.dumps({"cycle_id": result["cycle_id"], "cost_table": result["table"], "cycle_end": {
            k: result["cycle_end"].get(k) for k in ("requests", "estimated_cost_usd", "cumulative_incurred_usd", "cumulative_reserved_usd",
                                                      "successful_narratives", "cost_per_successful_narrative_usd")}}, indent=1, sort_keys=True))
        for phase, out in result["outputs"].items():
            for record in out["records"]:
                with self.subTest(role=record["role"], phase=phase):
                    self.assertEqual(role_failures(record), [], f"{record['role']}/{phase}: narrative_source={record['narrative_source']}")
            self.assertTrue(out["summary"]["ok"], out["summary"]["failed"])
        self.assertEqual(result["table"]["per_run"]["unknown_requests"], 0, "provider usage was not fully reported; reservation retained")


if __name__ == "__main__":
    unittest.main()

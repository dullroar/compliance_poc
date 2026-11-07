"""Provider-neutral registry-run driver for the live parity runs (plans/archive/live-parity), plus an offline recording provider.

`run_registry(backend, tool_mode)` drives the production batch path over in-process ASGI: one `build_app` and
`ComplianceExecutor` per role from agents.yaml, `orchestrator.batch.run_batch` / `run_narrative` and `a2a_client.send`, the
real MCP evaluators, then the auditor, then the narrative role. The Backend may be real or fake; this module never contacts a
network. It returns metadata-only per-role records (no prompts, payloads, decisions or model text) and a run summary.

`ScriptedProvider` is an offline fake that serves real Anthropic and OpenAI SDK clients through an httpx mock transport, so the
bytes it measures are the bytes the SDK would send, and the requests it counts are the requests the tool loops make.
"""
from __future__ import annotations

import asyncio
import contextlib
import contextvars
import json
import resource
import threading
import time
from typing import Any, Callable
from unittest import mock

import httpx
from jsonschema import Draft202012Validator

from agent_prompts import AGENTS
from agents.a2a_server import ComplianceExecutor, build_app
from agents.runner import DEFAULT_OPTIONS
from compliance_common.assemble import DECISION_OWNED
from compliance_common.narrative import deterministic_narrative
from compliance_common.narrative_schema import NARRATIVE_SCHEMA
from compliance_common.templates import examiner
from compliance_common.tools import TOOL_FIRST_MARKER, rejects_forced_tool_choice
from orchestrator import batch
from orchestrator.a2a_client import send as a2a_send
from orchestrator.batch import AUDITOR_KEYS, domain_keys, run_batch, run_narrative
from orchestrator.config import load_agents

from test_agent_parity import SAMPLE, authority, parts

PHASES = ("model", "seeded")
GOOD_SOURCES = ("model", "model_retry")
NARRATIVE_FIELDS = tuple(NARRATIVE_SCHEMA["properties"]["narrative"]["required"])
_NARRATIVE_VALIDATOR = Draft202012Validator(NARRATIVE_SCHEMA["properties"]["narrative"])
DECISION_MARKER = "TOOL RESULT (authoritative decision record; explain it, do not change it)\n"

# --- request bounds ----------------------------------------------------------------------------------------------------
# The tool loops in compliance_common.tools are `while True`: the code itself bounds a role only through the model stopping.
# The bound below is therefore the harness-enforced budget per role run (a cap the guarded client must apply), set to the most
# the runner's own paths can legitimately use:
#   model phase  : tool-loop turns (forced call + final answer) + one harness fallback completion + guard retries
#   seeded phase : anthropic runs the same loop on a conversation that already holds the call (turns <= TOOL_LOOP_TURNS);
#                  openai sends one `tool_choice: none` request; plus guard retries
#   plain role   : one completion; the narrative role has no guard and no tool
TOOL_LOOP_TURNS = 2
HARNESS_FALLBACK = 1
GUARD_RETRIES = DEFAULT_OPTIONS["max_retries"]         # taken from the runner, not restated
RUN_REQUEST_LIMIT = 80                                 # the plan's per-run ceiling (spec R1)


def worst_case_requests(provider: str, phase: str, role: str) -> int:
    """Most provider requests one role may use in one phase (see the derivation above)."""
    if provider not in ("anthropic", "openai"):
        raise ValueError(f"no bound derived for provider {provider!r}")
    if phase not in PHASES:
        raise ValueError(f"unknown phase {phase!r}")
    if not AGENTS[role].get("tool"):
        return 1
    if phase == "model":
        return TOOL_LOOP_TURNS + HARNESS_FALLBACK + GUARD_RETRIES
    return (TOOL_LOOP_TURNS if provider == "anthropic" else 1) + GUARD_RETRIES


def registry_roles(config: dict[str, dict] | None = None) -> list[str]:
    """Execution order: every domain role in registry order, then the auditor, then the narrative role. Derived from agents.yaml."""
    config = config or load_agents()
    return domain_keys(config) + [k for k in AUDITOR_KEYS if k in config]


def worst_case_table(provider: str, config: dict[str, dict] | None = None) -> dict[str, Any]:
    """Per-role, per-phase bounds and their total for one run (both phases of every role)."""
    roles = registry_roles(config)
    table = {phase: {role: worst_case_requests(provider, phase, role) for role in roles} for phase in PHASES}
    return {"per_role": table, "total": sum(sum(rows.values()) for rows in table.values()), "limit": RUN_REQUEST_LIMIT}


# --- role context and locking for simultaneous requests ---------------------------------------------------------------------
# With a remote width above 1 (plans/parallelize), several roles are in flight at once and each calls the guarded client from its
# own worker thread. The role a request belongs to is therefore held per call chain (a context variable, copied into worker
# threads by asyncio.to_thread), not on the client, and every counter and row write is made under the client's one lock.
_ROLE_CONTEXTS: contextvars.ContextVar[dict] = contextvars.ContextVar("live_parity_role_contexts", default={})


class _RoleContext:
    """One role and phase, and the requests it has used so far (its own allowance)."""
    __slots__ = ("role", "phase", "sent", "truncated")

    def __init__(self, role: str | None, phase: str | None) -> None:
        self.role, self.phase, self.sent, self.truncated = role, phase, 0, False      # truncated: a reply of this call chain stopped at max_tokens


class RoleScoped:
    """Mixin for a guarded client or a recording fake: `role`, `phase` and `role_sent` are those of the calling chain.

    A thread that never called `begin_role` (and holds no copied context) sees the most recent role: the serial behavior of
    a run at width 1. Counters shared by the whole run (`sent`, caps, rows) must be changed only while holding `self.lock`."""

    def _init_scope(self) -> None:
        self.lock = threading.RLock()
        self._latest = _RoleContext(None, None)
        self.sent = 0

    def _enter_role(self, role: str, phase: str) -> None:
        context = _RoleContext(role, phase)
        with self.lock:
            self._latest = context
        _ROLE_CONTEXTS.set({**_ROLE_CONTEXTS.get(), id(self): context})

    @property
    def _context(self) -> _RoleContext:
        return _ROLE_CONTEXTS.get().get(id(self)) or self._latest

    role = property(lambda self: self._context.role)
    phase = property(lambda self: self._context.phase)
    role_sent = property(lambda self: self._context.sent)


# --- the driver --------------------------------------------------------------------------------------------------------
_CURRENT_ROLE: contextvars.ContextVar[str | None] = contextvars.ContextVar("live_parity_current_role", default=None)


class _Run:
    """One phase: routes the production client's sends to in-process ASGI apps and records what was sent."""

    def __init__(self, backend: Any, tool_mode: str, config: dict[str, dict], target_for: Callable[[str], Any]) -> None:
        self.backend, self.tool_mode, self.target_for = backend, tool_mode, target_for
        self.urls = {key: f"http://{key}.parity.test/" for key in config}
        self.by_url = {url: key for key, url in self.urls.items()}
        self.sent: list[tuple[str, Any]] = []
        self.timings: dict[str, float] = {}
        self.began: dict[str, float] = {}          # monotonic start of each role's call, for the phase wall times
        self.evaluator_calls: dict[str, list[tuple[str, Any]]] = {}
        self.role: str | None = None
        self.hook = getattr(getattr(backend, "client", None), "begin_role", None) or getattr(backend, "begin_role", None)

    async def send(self, url: str, payload: Any, http_client: Any = None) -> dict[str, Any]:
        key = self.by_url[url]
        self.sent.append((key, json.loads(json.dumps(payload))))        # the exact JSON the production client transmits
        self.role = key
        _CURRENT_ROLE.set(key)                                          # per call chain: roles may be in flight together
        self.began[key] = time.monotonic()
        if self.hook:
            self.hook(key, self.tool_mode)
        started = time.monotonic()
        try:
            target = self.target_for(key) if AGENTS[key].get("tool") else None          # the narrative role has no tool
            executor = ComplianceExecutor(key, backend=self.backend, tool_target=target, options={"tool_mode": self.tool_mode})
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=build_app(key, url, executor)), base_url=url) as http:
                return await a2a_send(url, payload, http)
        finally:
            self.timings[key] = round(time.monotonic() - started, 3)

    def recording_call_tool(self, real: Callable) -> Callable:
        async def call(target: Any, name: str, arguments: dict[str, Any]) -> Any:
            self.evaluator_calls.setdefault(_CURRENT_ROLE.get() or self.role or "", []).append((name, json.loads(json.dumps(arguments))))
            return await real(target, name, arguments)
        return call


def _check(record: dict[str, Any], name: str, passed: bool) -> None:
    record["checks"][name] = bool(passed)


def violation_kind(violation: str) -> str:
    """A label for a narrative-guard violation. The text itself can quote model output, so only the kind is ever recorded."""
    for prefix, kind in (("the number", "number"), ("the date", "date"), ("the identifier", "identifier"),
                         ("the reply was not valid JSON", "invalid_json"), ("the narrative is empty", "empty")):
        if violation.startswith(prefix):
            return kind
    return "other"


def _record_for(run: _Run, key: str, phase: str, result: dict[str, Any], payload: Any) -> dict[str, Any]:
    """Metadata only: hashes, labels, counts and booleans. The result, decision, payload and model text are not kept."""
    record: dict[str, Any] = {"role": key, "phase": phase, "checks": {}, "elapsed_seconds": run.timings.get(key),
                              "tool_backed": bool(AGENTS[key].get("tool")), "failure": None}
    tool = AGENTS[key].get("tool")
    if result.get("parse_error") and result.get("parsed") is None and not result.get("raw_text") and "decision" not in result:
        record["failure"] = str(result["parse_error"])[:200]                          # the task failed (batch._failed)
    if not tool:
        text = result.get("raw_text") or ""
        record.update(narrative_source="model" if text.strip() and not record["failure"] else None, guard_attempts=0,
                      tool_calls=[], stripped_fields=[], violation_kinds=[], decision=None)
        _check(record, "schema_valid", bool(text.strip()))            # a markdown report: present and non-empty (no schema, no guard)
        _check(record, "no_decision", result.get("decision") is None and not result.get("tool_calls") and result.get("parsed") is None)
        _check(record, "ordering", _ordering_ok(run, key))
        _check(record, "no_leak", result.get("decision") is None)
        _check(record, "decision_parity", True)
        _check(record, "canonical_arguments", key not in run.evaluator_calls)
        _check(record, "tool_provenance", not result.get("tool_calls"))
        return record
    _, evaluate, adapter = parts(key)
    canonical, _ = adapter.tool_arguments(payload)
    direct = evaluate(canonical["case"]) if canonical else None
    decision, parsed = result.get("decision"), result.get("parsed")
    guard = result.get("narrative_guard") or {}
    calls = result.get("tool_calls") or []
    source = (parsed or {}).get("narrative_source") if isinstance(parsed, dict) else None
    record.update(narrative_source=source, guard_attempts=guard.get("attempts"), stripped_fields=list(guard.get("stripped_fields") or []),
                  violation_kinds=[[violation_kind(v) for v in guard.get(k) or []] for k in ("violations", "retry_violations")],
                  tool_calls=[{"name": c.get("name"), "by": c.get("by")} for c in calls],
                  decision=None if not decision else {k: decision.get(k) for k in ("decision_id", "final_classification", "compliance_result")})
    if record["failure"] or not isinstance(decision, dict) or not isinstance(parsed, dict) or direct is None:
        record["failure"] = record["failure"] or "no decision or parsed result"
        for name in ("decision_parity", "canonical_arguments", "tool_provenance", "schema_valid", "no_leak", "ordering"):
            _check(record, name, False)
        return record
    _check(record, "decision_parity", authority(decision) == authority(direct))
    seen = run.evaluator_calls.get(key, [])
    _check(record, "canonical_arguments", bool(seen) and all(name == adapter.TOOL and args == canonical for name, args in seen))
    expected_by = "model" if phase == "model" else "seeded"
    _check(record, "tool_provenance", bool(calls) and all(c.get("name") == adapter.TOOL and c.get("by") == expected_by for c in calls))
    summary = parsed.get("compliance_determination_summary") or {}
    _check(record, "schema_valid", all(f in summary for f in NARRATIVE_FIELDS)
           and not list(_NARRATIVE_VALIDATOR.iter_errors({f: summary[f] for f in NARRATIVE_FIELDS})))
    _check(record, "no_leak", parsed["domain_determination"]["classification"] == direct["final_classification"]
           and parsed["determination_status"]["result"] == direct["compliance_result"]
           and [t["step"] for t in parsed["determination_trace"]] == [r["rule_id"] for r in direct["rule_results"]]
           and parsed["agent_metadata"]["decision_id"] == direct["decision_id"] and not (set(DECISION_OWNED) & set(summary)))
    _check(record, "ordering", _ordering_ok(run, key))
    return record


def _ordering_ok(run: _Run, key: str) -> bool:
    order = [k for k, _ in run.sent]
    expected = registry_roles({k: {} for k in run.urls})
    if order != expected[:len(order)] or key not in order:
        return False
    payload = dict(run.sent)[key]
    domains = domain_keys({k: {} for k in run.urls})
    if key == "auditor":
        return list(payload.get("agent_results", {})) == domains and order.index(key) == len(domains)
    if key == "narrative":
        return list(payload) == domains + ["auditor"] and order.index(key) == len(domains) + 1
    return order.index(key) < len(domains)


def role_failures(record: dict[str, Any]) -> list[str]:
    """Names of the checks a role record fails. A fallback or missing narrative fails `narrative_source`."""
    failed = [name for name, passed in record["checks"].items() if not passed]
    if record["narrative_source"] not in GOOD_SOURCES:
        failed.append("narrative_source")
    if record["failure"]:
        failed.append("task")
    return failed


def run_registry(backend: Any, tool_mode: str, *, payload: Any = None, target_for: Callable[[str], Any] | None = None,
                 config: dict[str, dict] | None = None, remote_concurrency: int | None = None) -> dict[str, Any]:
    """Run every registry role once in one phase and return {"records", "summary"} (metadata only).

    Serial (`concurrency=1`) unless `remote_concurrency` is given, which is the opt-in width of the domain phase."""
    if tool_mode not in PHASES:
        raise ValueError(f"tool_mode must be one of {PHASES}")
    config = config or load_agents()
    payload = SAMPLE if payload is None else payload
    run = _Run(backend, tool_mode, config, target_for or (lambda key: parts(key)[0]))
    routed = {key: {**entry, "url": run.urls[key]} for key, entry in config.items()}

    async def go() -> dict[str, dict]:
        if remote_concurrency is None:
            results = await run_batch(payload, routed, verbose=False, concurrency=1)
        else:
            results = await run_batch(payload, routed, verbose=False, remote_concurrency=remote_concurrency,
                                      provider=getattr(backend, "provider", None))
        results["narrative"] = await run_narrative(results, routed, verbose=False)
        return results

    started, cpu_before = time.monotonic(), _cpu_seconds()
    with mock.patch.object(batch, "send", run.send), mock.patch("agents.runner.call_tool", run.recording_call_tool(_real_call_tool())):
        results = asyncio.run(go())
    elapsed = round(time.monotonic() - started, 3)
    cpu_after = _cpu_seconds()
    sent = dict(run.sent)
    records = [_record_for(run, key, tool_mode, results[key], sent[key]) for key in registry_roles(config) if key in results]
    summary = summarize(records, backend, tool_mode, [k for k, _ in run.sent], elapsed)
    summary["timing"] = _phase_timing(run, started, elapsed, cpu_before, cpu_after)
    return {"records": records, "summary": summary}


def _cpu_seconds() -> dict[str, float]:
    """CPU time of this process and of its finished child processes (the MCP evaluator subprocesses)."""
    own, children = resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)
    return {"self": own.ru_utime + own.ru_stime, "children": children.ru_utime + children.ru_stime}


def _phase_timing(run: _Run, started: float, elapsed: float, before: dict[str, float], after: dict[str, float]) -> dict[str, Any]:
    """Wall time of the domain phase (batch start to the last domain role finishing), the auditor, the narrative role and the whole batch."""
    domains = [k for k in run.began if k not in AUDITOR_KEYS]
    ends = {k: run.began[k] + run.timings.get(k, 0.0) for k in run.began}
    domain_end = max((ends[k] for k in domains), default=started)
    return {"domain_phase_seconds": round(domain_end - started, 3), "auditor_seconds": run.timings.get("auditor"),
            "narrative_seconds": run.timings.get("narrative"), "total_seconds": elapsed,
            "cpu_seconds": {k: round(after[k] - before[k], 3) for k in after}}


def _real_call_tool() -> Callable:
    from compliance_common.mcp_client import call_tool
    return call_tool


def summarize(records: list[dict[str, Any]], backend: Any, phase: str, order: list[str], elapsed: float) -> dict[str, Any]:
    failed = {r["role"]: role_failures(r) for r in records if role_failures(r)}
    return {"provider": getattr(backend, "provider", None), "model": getattr(backend, "model", None), "phase": phase,
            "roles": len(records), "order": order, "ok": not failed and len(records) == len(registry_roles()),
            "narrative_sources": {r["role"]: r["narrative_source"] for r in records},
            "fallbacks": [r["role"] for r in records if r["narrative_source"] == "deterministic_fallback"],
            "failed": failed, "elapsed_seconds": elapsed}


# --- offline recording provider ----------------------------------------------------------------------------------------
class RequestCapExceeded(Exception):
    """Raised by the fake when a role exceeds its bound, as the guarded client of steps 02/03 will."""


def _decision_in(items: list[Any]) -> dict[str, Any] | None:
    """The latest decision record found in an Anthropic message list or an OpenAI input list."""
    found = None
    for item in items:
        item = item if isinstance(item, dict) else getattr(item, "model_dump", lambda **_: {})()
        candidates = []
        if item.get("type") == "function_call_output":
            candidates.append(item.get("output"))
        content = item.get("content")
        if isinstance(content, str):
            candidates.append(content)
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                candidates.append(block.get("content"))
        for text in candidates:
            if not isinstance(text, str):
                continue
            if DECISION_MARKER in text:
                text = text.split(DECISION_MARKER, 1)[1]
            with contextlib.suppress(ValueError):
                value, _ = json.JSONDecoder().raw_decode(text.lstrip())
                if isinstance(value, dict) and "decision_id" in value:
                    found = value
    return found


class ScriptedProvider(RoleScoped):
    """Serves real Anthropic and OpenAI SDK clients (zero retries) from an httpx mock transport and records every request.

    behavior: tool = "call" (the model calls the tool when asked), "none" (it never calls it), "repeat" (it calls it on every turn)
              narrative = "grounded" | "ungrounded" (adds an invented figure, so the guard rejects it and the retry also fails)
              empty_after_tool = True (the final answer after a tool result is empty text)
    """

    def __init__(self, *, tool: str = "call", narrative: str = "grounded", empty_after_tool: bool = False, caps: bool = True,
                 provider: str = "anthropic", model: str | None = None) -> None:
        self.provider, self.tool, self.narrative, self.empty_after_tool, self.caps = provider, tool, narrative, empty_after_tool, caps
        self.model = model or ("claude-haiku-5-5" if provider == "anthropic" else "gpt-6-luna")
        self._init_scope()
        self.requests: list[dict[str, Any]] = []
        self.rejected: list[dict[str, Any]] = []          # forced tool choices answered with the API's 400 for a model that rejects them
        self.refused: list[dict[str, Any]] = []
        self.decisions: dict[str, dict] = {}

    # labelling hook used by run_registry
    def begin_role(self, role: str, phase: str) -> None:
        self._enter_role(role, phase)

    def count(self, role: str, phase: str) -> int:
        return sum(1 for r in self.requests if r["role"] == role and r["phase"] == phase)

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        record = {"role": self.role, "phase": self.phase, "path": request.url.path, "bytes": len(request.content),
                  "tool_choice": body.get("tool_choice"), "model": body.get("model")}
        with self.lock:                  # check and count together, so simultaneous requests cannot both take the last slot
            if self.caps and self.count(self.role, self.phase) + 1 > worst_case_requests(self.provider, self.phase, self.role):
                self.refused.append(record)
                raise RequestCapExceeded(f"{self.role}/{self.phase}")
            self.requests.append(record)
        anthropic = request.url.path.endswith("/messages")
        items = body["messages"] if anthropic else body["input"]
        decision = _decision_in(items)
        if decision:
            with self.lock:
                self.decisions[self.role] = decision
        forced = (body.get("tool_choice") or {}).get("type") in ("tool", "function") if isinstance(body.get("tool_choice"), dict) else False
        if anthropic and forced and rejects_forced_tool_choice(body.get("model")):
            with self.lock:
                self.rejected.append(record)
            return httpx.Response(400, json={"type": "error", "error": {"type": "invalid_request_error",
                                                                          "message": "tool_choice: forced tool use is not supported by this model"}})
        told = anthropic and TOOL_FIRST_MARKER in (body.get("system") or "") and not forced      # asked to call it by name, not forced
        has_result = decision is not None and any(self._is_result(i) for i in items)
        call = body.get("tools") and (self.tool == "repeat" and body.get("tool_choice") != "none" or (self.tool == "call" and (forced or told) and not has_result))
        if call:
            return httpx.Response(200, json=self._tool_call(anthropic, body))
        return httpx.Response(200, json=self._text(anthropic, self._answer(decision or self.decisions.get(self.role), body)))

    @staticmethod
    def _is_result(item: Any) -> bool:
        if isinstance(item, dict) and item.get("type") == "function_call_output":
            return True
        content = item.get("content") if isinstance(item, dict) else None
        return isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content)

    def _answer(self, decision: dict | None, body: dict) -> str:
        if not AGENTS[self.role].get("tool"):
            return "# Compliance narrative\n\nSynthetic report."
        if self.empty_after_tool and decision is not None and not self._after_marker(body):
            return ""
        if decision is None:
            return "I will answer without the tool."
        narrative = deterministic_narrative(decision, AGENTS[self.role]["tool"].removesuffix("_evaluate"))
        if self.narrative == "ungrounded":
            narrative["reasoning"] += " The borrower also owes 987654321 dollars under file ZZ-987654321."
        domain = AGENTS[self.role]["tool"].removesuffix("_evaluate")
        record = {k: v for k, v in decision.items() if k != "examiner_paragraph_drafts"}
        paragraphs = [{"rule_id": d["rule_id"], "text": d["draft"]} for d in examiner.drafts(record, domain)]     # a faithful model echoes the drafts
        return json.dumps({"narrative": narrative, "examiner_paragraphs": paragraphs})

    @staticmethod
    def _after_marker(body: dict) -> bool:
        return json.dumps(DECISION_MARKER)[1:-1] in json.dumps(body)         # newlines are escaped in the serialized body

    def _tool_call(self, anthropic: bool, body: dict) -> dict[str, Any]:
        name = body["tools"][0]["name"]
        usage = {"input_tokens": 1, "output_tokens": 1}
        if anthropic:
            return {"id": "msg_s", "type": "message", "role": "assistant", "model": self.model, "stop_reason": "tool_use", "stop_sequence": None,
                    "content": [{"type": "tool_use", "id": f"toolu_{len(self.requests)}", "name": name, "input": {"case": {}}}], "usage": usage}
        return {"id": "resp_s", "object": "response", "created_at": 0, "model": self.model, "status": "completed", "parallel_tool_calls": False,
                "tool_choice": "auto", "tools": [], "service_tier": "default", "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2,
                                                              "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0, "cache_write_tokens_details": {"ttl_30m_tokens": 0, "ttl_12h_tokens": 0}}, "output_tokens_details": {"reasoning_tokens": 0}},
                "output": [{"type": "function_call", "id": f"fc_{len(self.requests)}", "call_id": f"call_{len(self.requests)}", "name": name,
                            "arguments": json.dumps({"case": {}}), "status": "completed"}]}

    def _text(self, anthropic: bool, text: str) -> dict[str, Any]:
        if anthropic:
            content = [{"type": "text", "text": text}] if text else []
            return {"id": "msg_s", "type": "message", "role": "assistant", "model": self.model, "stop_reason": "end_turn", "stop_sequence": None,
                    "content": content, "usage": {"input_tokens": 1, "output_tokens": 1}}
        output = [{"type": "message", "id": "msg_s", "role": "assistant", "status": "completed",
                   "content": [{"type": "output_text", "text": text, "annotations": []}]}] if text else []
        return {"id": "resp_s", "object": "response", "created_at": 0, "model": self.model, "status": "completed", "parallel_tool_calls": False,
                "tool_choice": "auto", "tools": [], "service_tier": "default", "output": output,
                "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2,
                          "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0, "cache_write_tokens_details": {"ttl_30m_tokens": 0, "ttl_12h_tokens": 0}}, "output_tokens_details": {"reasoning_tokens": 0}}}

    def client(self) -> Any:
        """A real SDK client over the mock transport with max_retries=0, plus the labelling hook."""
        transport = httpx.MockTransport(self.handler)
        if self.provider == "anthropic":
            import anthropic
            sdk = anthropic.Anthropic(api_key="offline-placeholder", max_retries=0, timeout=5.0, http_client=httpx.Client(transport=transport))
        else:
            import openai
            sdk = openai.OpenAI(api_key="offline-placeholder", max_retries=0, timeout=5.0, http_client=httpx.Client(transport=transport))
        return _HookedClient(sdk, self)

    def backend(self) -> Any:
        from agents.backends import Backend
        return Backend(self.provider, self.model, client=self.client())


class _HookedClient:
    def __init__(self, sdk: Any, provider: ScriptedProvider) -> None:
        self._sdk, self.begin_role = sdk, provider.begin_role

    def __getattr__(self, name: str) -> Any:
        return getattr(self._sdk, name)

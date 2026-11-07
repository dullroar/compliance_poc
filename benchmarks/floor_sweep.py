"""Tune-ais sweep (plans/archive/tune-ais): climb a ladder of rungs per role and score every run with the bar in benchmarks/floor_bar.py.

  python3 -m benchmarks.floor_sweep --dry-run [--out RUNS.jsonl] [--width N] [--weak ROLE,...] [--rung1 all|needed]
  python3 -m benchmarks.floor_sweep --scenarios-md plans/archive/tune-ais/scenarios.md

Rungs, cheapest first: 0 code only (no model is asked; the narrative and paragraphs are the code-written ones), 1 claude-haiku-5-5 at
today's setting, 2 claude-sonnet-5-5 at effort low with thinking unset. A role's lowest passing rung is the first that clears the bar.
Rung 2 is run only for a role that clears neither rung 0 nor rung 1. By default (Jim, 2026-11-07) rung 1 is run only for a role that failed
rung 0 (literal spec R3: a role stops at its first passing rung); `--rung1 all` runs it for every role.

`--dry-run` drives the real runner, the real evaluators and the real checks with fake model backends: no network, no credentials, no
spend. `--live --provider anthropic` scores rung 0 offline, then makes the one-request diagnostic per candidate model (reserved, guarded, settled
from usage); if any role fails rung 0 it stops (exit 3) instead of climbing, because the per-role live reservations are Jim's decision.
Run files hold metadata only (labels, counts, booleans, ids); paragraph texts go to a separate `--texts` file when asked for.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import itertools
import json
import os
import re
import sys
import time
import uuid
from decimal import Decimal
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "tests"):              # the evaluator fixtures and in-process MCP targets live with the tests
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from agent_prompts import AGENTS  # noqa: E402
from agents.runner import DRAFTS_KEY, run  # noqa: E402
from compliance_common.narrative import deterministic_narrative  # noqa: E402
from compliance_common.templates import examiner, loan_officer  # noqa: E402
from orchestrator.config import load_agents, load_settings  # noqa: E402

from benchmarks import floor_bar  # noqa: E402

import response_fixtures as fixtures  # noqa: E402  (tests/response_fixtures.py: the cases the evaluator suites use)
from test_agent_parity import SAMPLE, parts  # noqa: E402

REGISTRY = load_agents()
DOMAINS = [k for k in REGISTRY if AGENTS[k].get("tool") and k != "auditor"]
ROLES = DOMAINS + ["auditor", "narrative"]
RUNGS = {0: {"label": "code only", "model": None}, 1: {"label": "Haiku 5.5, effort low", "model": "claude-haiku-5-5"},
         2: {"label": "Sonnet 5.5, effort low", "model": "claude-sonnet-5-5"}}
T5_ROLES = DOMAINS + ["auditor"]
OPTIONS = {"templates": "model"}                       # today's committed setting; only tool_mode varies per cell
CODE_OPTIONS = {"tool_mode": "seeded", "templates": "code"}
TABLE_COLUMNS = ("Role", "Lowest passing rung", "Rung 0: code only", "Rung 1: Haiku 5.5", "Rung 2: Sonnet 5.5",
                 "First-pass rate at that rung", "Cost per successful narrative (USD)", "Tokens in / out", "Latency (s)")


# --- scenarios ---------------------------------------------------------------------------------------------------------------
@dataclass
class Scenario:
    id: str
    kind: str                       # sample | fail | gap
    regime: str                     # a domain, or "all"
    loan: dict[str, Any]
    source: str                     # how the script chose it
    summary: str = ""


def _decision_summary(decision: dict[str, Any]) -> str:
    counts: dict[str, int] = {}
    for r in decision.get("rule_results", []):
        if r.get("outcome") in examiner.FINDING_OUTCOMES:
            counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
    return f"{decision.get('final_classification')} / {decision.get('compliance_result')}; findings " + (
        ", ".join(f"{n} {k}" for k, n in sorted(counts.items())) or "none")


def _chosen(domain: str) -> dict[str, tuple[str, dict[str, Any], dict[str, Any]]]:
    """First failing case (a not_satisfied finding) and first information-gap case (unable_to_determine, nothing not_satisfied) of a regime,
    in the fixture order of tests/response_fixtures.py: bases in order, then each leaf dropped, then each boolean flipped, then values."""
    evaluate = fixtures._evaluators()[domain]
    found: dict[str, tuple[str, dict[str, Any], dict[str, Any]]] = {}
    for number, base in enumerate(fixtures._base_cases()[domain]):
        variants = itertools.chain(fixtures._mutations(base), fixtures._value_mutations(base, domain == "hmda") if domain in fixtures.VALUE_DOMAINS else ())
        for label, case in variants:
            try:
                decision = evaluate(case)
            except fixtures.EvaluatorValidationError:
                continue
            outcomes = {r.get("outcome") for r in decision.get("rule_results", [])}
            if "fail" not in found and "not_satisfied" in outcomes:
                found["fail"] = (f"{domain}#{number} {label}", copy.deepcopy(case), decision)
            if "gap" not in found and "unable_to_determine" in outcomes and "not_satisfied" not in outcomes:
                found["gap"] = (f"{domain}#{number} {label}", copy.deepcopy(case), decision)
            if len(found) == 2:
                return found
    return found


def build_scenarios() -> dict[str, Scenario]:
    """sample_loan.json, and for each regime one failing and one information-gap case, then the all-regimes versions the auditor and the
    narrative role see. Deterministic: the same repository gives the same list. A regime with no such case is simply absent."""
    scenarios = {"sample": Scenario("sample", "sample", "all", copy.deepcopy(SAMPLE), "sample_loan.json as committed")}
    chosen = {domain: _chosen(domain) for domain in DOMAINS}
    for domain in DOMAINS:
        for kind in ("fail", "gap"):
            if kind in chosen[domain]:
                label, case, decision = chosen[domain][kind]
                loan = copy.deepcopy(SAMPLE)
                loan[f"{domain}_case"] = case
                scenarios[f"{kind}:{domain}"] = Scenario(f"{kind}:{domain}", kind, domain, loan, f"{label} of the response-templates fixtures",
                                                         _decision_summary(decision))
    for kind in ("fail", "gap"):
        loan, parts_ = copy.deepcopy(SAMPLE), []
        for domain in DOMAINS:
            if kind in chosen[domain]:
                loan[f"{domain}_case"] = chosen[domain][kind][1]
                parts_.append(domain)
        scenarios[f"{kind}:all"] = Scenario(f"{kind}:all", kind, "all", loan, f"the {kind} case of every regime that has one: " + ", ".join(parts_))
    return scenarios


def role_scenarios(role: str, scenarios: dict[str, Scenario]) -> list[str]:
    own = ["sample"] + [f"{k}:{role}" for k in ("fail", "gap")] if role in DOMAINS else ["sample", "fail:all", "gap:all"]
    return [s for s in own if s in scenarios]


# --- inputs per role ---------------------------------------------------------------------------------------------------------
class DryModel:
    """A Backend double that behaves like a cooperative model: it calls the tool, echoes the code-written drafts and writes a grounded
    narrative. `weak` makes it add an invented figure, so the guard rejects both attempts (a model that is not tall enough)."""
    provider, model = "dry", "dry-model"

    def __init__(self, *, weak: bool = False, truncated: bool = False, hold: Callable[[], None] | None = None) -> None:
        self.weak, self.truncated, self.hold = weak, truncated, hold

    @staticmethod
    def _role(system: str) -> str:
        return next(k for k, v in AGENTS.items() if system.startswith(v["system_prompt"]))

    def _reply(self, domain: str, decision: dict[str, Any]) -> str:
        narrative = deterministic_narrative(decision, domain)
        if self.weak:
            narrative["reasoning"] += " The borrower also owes 987654321 dollars under file ZZ-987654321."
        drafts = decision.get(DRAFTS_KEY) or examiner.drafts(decision, domain)
        return json.dumps({"narrative": narrative, "examiner_paragraphs": [{"rule_id": d["rule_id"], "text": d["draft"]} for d in drafts]})

    def complete_with_tool(self, system, messages, spec, execute, calls_made, force_first=True, schema=None):
        if self.hold:
            self.hold()
        result = execute(spec["name"], {"case": {}})
        calls_made.append({"name": spec["name"], "arguments": {"case": {}}, "result": result})
        return self._reply(spec["name"].removesuffix("_evaluate"), result)

    def complete_seeded(self, system, messages, spec, execute, calls_made, arguments, result, schema=None):
        if self.hold:
            self.hold()
        return self._reply(spec["name"].removesuffix("_evaluate"), result)

    def complete(self, system, messages, json_mode=True, schema=None):
        if self.hold:
            self.hold()
        role = self._role(system)
        if role == "narrative":
            return "The review is complete. Each role's result and its follow-up items are in the sections below." + (
                " The borrower also owes 987654321 dollars." if self.weak else "")
        marker = "explain it, do not change it)\n"
        text = next(m["content"] for m in reversed(messages) if isinstance(m.get("content"), str) and marker in m["content"])
        decision, _ = json.JSONDecoder().raw_decode(text.split(marker, 1)[1])
        return self._reply(AGENTS[role]["tool"].removesuffix("_evaluate"), decision)


class InputCache:
    """The payload each role is given for a scenario. The auditor and the narrative role need the other roles' results; those come from
    code only (rung 0 behavior), so building them costs nothing and does not depend on the model being tuned."""

    def __init__(self, scenarios: dict[str, Scenario]) -> None:
        self.scenarios, self._results = scenarios, {}

    def code_results(self, scenario_id: str) -> dict[str, dict[str, Any]]:
        if scenario_id not in self._results:
            loan = self.scenarios[scenario_id].loan
            results = {d: run(d, loan, DryModel(), tool_target=parts(d)[0], options=CODE_OPTIONS) for d in DOMAINS}
            audit_input = {"loan_data": loan, "agent_results": {d: r["parsed"] for d, r in results.items()}}
            results["auditor"] = run("auditor", audit_input, DryModel(), tool_target=parts("auditor")[0], options=CODE_OPTIONS)
            self._results[scenario_id] = results
        return self._results[scenario_id]

    def payload(self, role: str, scenario_id: str) -> Any:
        if role in DOMAINS:
            return self.scenarios[scenario_id].loan
        results = self.code_results(scenario_id)
        if role == "auditor":
            return {"loan_data": self.scenarios[scenario_id].loan, "agent_results": {d: results[d]["parsed"] for d in DOMAINS}}
        return {k: v["parsed"] for k, v in results.items()}            # what the batch hands the narrative role

    def direct(self, role: str, scenario_id: str) -> dict[str, Any]:
        _, evaluate, adapter = parts(role)
        canonical, reason = adapter.tool_arguments(self.payload(role, scenario_id))
        assert canonical, reason
        return evaluate(canonical["case"])


# --- records -----------------------------------------------------------------------------------------------------------------
def _kind(problem: str) -> str:
    """A label for a violation: its leading words, up to the first digit or quote, so a record never quotes model text."""
    return " ".join(re.split(r"[\d\"'`:]", str(problem), maxsplit=1)[0].split()[:6]) or "problem"


def _items(sheet: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    out = []
    for key, kind in (("needed_from_customer", "customer"), ("refer_to_compliance", "refer")):
        for item in sheet.get(key, []):
            sentences = floor_bar.sentences(item.get("text", ""))
            out.append({"kind": kind, "sentences": len(sentences), "max_sentence_words": max((len(s.split()) for s in sentences), default=0)})
    return out


def _paragraphs(templates: dict[str, Any], decision: dict[str, Any], domain: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The runner builds its paragraphs in the order of `examiner.render`, and a rule id can repeat (the auditor has one per subject), so
    each paragraph is checked against the expected one at the same position, not looked up by rule id."""
    expected = examiner.render(decision, domain, strict=False)
    paragraphs, texts = [], []
    for number, p in enumerate(templates["examiner"]):
        base = expected[number] if number < len(expected) and expected[number]["rule_id"] == p["rule_id"] else None
        problems = [_kind(x) for x in examiner.check_paragraph(p["text"], base, decision, domain)] if base else ["unexpected paragraph"]
        paragraphs.append({"rule_id": p["rule_id"], "source": p["source"], "words": len(p["text"].split()), "problems": problems,
                           **({"over_limit": True} if p.get("over_limit") else {})})
        texts.append({"rule_id": p["rule_id"], "source": p["source"], "text": p["text"]})
    return paragraphs, texts


def code_record(role: str, scenario: str, inputs: InputCache) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Rung 0: what code alone writes for this role and scenario, scored by the same bar. No model is asked, so no runner call is made."""
    base = {"role": role, "rung": 0, "scenario": scenario, "tool_mode": None, "rep": 0, "design": "code", "stopped_at_max_tokens": False,
            "attempts": 0, "latency_seconds": 0.0}
    if role == "narrative":
        return {**base, "narrative_source": None, "summary": {"source": "code", "words": 0, "violations": []}}, []
    direct = inputs.direct(role, scenario)
    domain = AGENTS[role]["tool"].removesuffix("_evaluate")
    templates = {"examiner": [{**p, "source": "code"} for p in examiner.render(direct, domain, strict=False)]}
    paragraphs, texts = _paragraphs(templates, direct, domain)
    return {**base, "narrative_source": "code", "decision_id": direct["decision_id"], "classification": direct["final_classification"],
            "direct_decision_id": direct["decision_id"], "direct_classification": direct["final_classification"],
            "paragraphs": paragraphs, "items": _items(loan_officer.render(direct))}, texts


def model_record(role: str, rung: int, scenario: str, mode: str, rep: int, result: dict[str, Any], inputs: InputCache,
                 truncated: bool, seconds: float, templates: str = "model") -> tuple[dict[str, Any], list[dict[str, Any]]]:
    base = {"role": role, "rung": rung, "scenario": scenario, "tool_mode": mode, "rep": rep, "design": "model", "templates": templates,
            "stopped_at_max_tokens": bool(truncated), "latency_seconds": round(seconds, 3)}
    if role == "narrative":
        return {**base, "narrative_source": None, "attempts": 1,
                "summary": {"source": result.get("summary_source"), "words": result.get("summary_words"), "violations": [_kind(v) for v in result.get("summary_violations") or []]}}, []
    decision, parsed = result.get("decision"), result.get("parsed")
    if not isinstance(decision, dict) or not isinstance(parsed, dict):
        return {**base, "narrative_source": None, "attempts": 0, "failure": str(result.get("parse_error"))[:80]}, []        # no decision: fails T1/T3/T4
    direct = inputs.direct(role, scenario)
    domain = AGENTS[role]["tool"].removesuffix("_evaluate")
    templates = parsed.get("response_templates") or {"examiner": [], "loan_officer": {}}
    paragraphs, texts = _paragraphs(templates, decision, domain)
    return {**base, "narrative_source": parsed.get("narrative_source"), "attempts": (result.get("narrative_guard") or {}).get("attempts"),
            "tool_by": sorted({c.get("by") for c in result.get("tool_calls") or []}), "decision_id": decision.get("decision_id"),
            "classification": decision.get("final_classification"), "direct_decision_id": direct["decision_id"],
            "direct_classification": direct["final_classification"], "paragraphs": paragraphs, "items": _items(templates.get("loan_officer") or {})}, [
        t for t in texts if t["source"] in floor_bar.GOOD_SOURCES]


# --- backends ----------------------------------------------------------------------------------------------------------------
class DryBackends:
    """Fake model backends for `--dry-run`. `weak` roles get a model that is not tall enough at rung 1 (never at rung 2)."""

    def __init__(self, weak: set[str] | None = None, truncating: set[str] | None = None, hold: Callable[[], None] | None = None,
                 weak_rungs: set[int] | None = None) -> None:
        self.weak, self.truncating, self.hold, self.weak_rungs = weak or set(), truncating or set(), hold, weak_rungs or {1}
        self.asked: list[tuple[int, str]] = []

    def get(self, rung: int, role: str, mode: str | None = None) -> tuple[Any, Callable[[], bool]]:
        self.asked.append((rung, role))
        truncated = rung == 1 and role in self.truncating
        return DryModel(weak=rung in self.weak_rungs and role in self.weak, hold=self.hold), lambda: truncated

    def open_batch(self, rung: int, role: str, mode: str | None, cells: int) -> None:
        pass

    def close_batch(self, rung: int, role: str, mode: str | None) -> None:
        pass


# --- the sweep ---------------------------------------------------------------------------------------------------------------
def run_cell(role: str, rung: int, scenario: str, mode: str | None, rep: int, inputs: InputCache, backends: Any,
             templates: str = "model") -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if rung == 0:
        return code_record(role, scenario, inputs)
    backend, probe = backends.get(rung, role, mode)
    begin = getattr(getattr(backend, "client", None), "begin_role", None)
    if begin:
        begin(role, mode or "model")                       # the guard keeps each cell's role, allowance and truncation flag per call chain
    payload = inputs.payload(role, scenario)
    started = time.monotonic()
    try:
        if role == "narrative":
            result = run("narrative", payload, backend)
        else:
            result = run(role, payload, backend, tool_target=parts(role)[0], options={"templates": templates, "tool_mode": mode})
    except Exception as exc:                   # a run that raises is a failed run, never a skipped one
        record = {"role": role, "rung": rung, "scenario": scenario, "tool_mode": mode, "rep": rep, "design": "model", "templates": templates, "attempts": 0,
                  "narrative_source": None, "stopped_at_max_tokens": bool(probe()), "failure": type(exc).__name__,
                  "latency_seconds": round(time.monotonic() - started, 3)}
        return record, []
    return model_record(role, rung, scenario, mode, rep, result, inputs, probe(), time.monotonic() - started, templates)


async def _run_cells(cells: list[tuple], width: int, work: Callable[[tuple], Any]) -> list[Any]:
    gate = asyncio.Semaphore(width)

    async def one(cell: tuple) -> Any:
        async with gate:
            return await asyncio.to_thread(work, cell)

    return await asyncio.gather(*(one(cell) for cell in cells))


def run_rung(roles: list[str], rung: int, scenarios: dict[str, Scenario], inputs: InputCache, backends: Any, width: int,
             templates: str = "model") -> dict[str, Any]:
    """Every cell of the grid for each role at one rung; returns {role: {"records": [...], "texts": [...], "verdict": {...}}}.
    A live rung runs one batch per role and tool mode: the backend reserves the batch's worst case first and settles it afterwards."""
    cells = [(role, s, mode, rep) for role in roles for s in role_scenarios(role, scenarios)
             for (_, mode, rep) in sorted(floor_bar.expected_cells(rung, [s]), key=str)]
    for role in roles:                                    # build every shared input before any thread starts
        for s in role_scenarios(role, scenarios):
            inputs.payload(role, s)
            if role != "narrative":
                inputs.direct(role, s)
    groups: dict[tuple, list[tuple]] = {}
    for cell in cells:
        groups.setdefault((cell[0], cell[2]), []).append(cell)
    work = lambda cell: run_cell(cell[0], rung, cell[1], cell[2], cell[3], inputs, backends, templates)
    by_role: dict[str, dict[str, Any]] = {r: {"records": [], "texts": []} for r in roles}
    for (role, mode), group in groups.items():
        if rung > 0:
            backends.open_batch(rung, role, mode, len(group))
        try:
            outputs = asyncio.run(_run_cells(group, 1 if rung == 0 else width, work))
        finally:
            if rung > 0:
                backends.close_batch(rung, role, mode)
        for (_, s, _, rep), (record, texts) in zip(group, outputs):
            by_role[role]["records"].append(record)
            by_role[role]["texts"] += [{"role": role, "scenario": s, "tool_mode": mode, "rep": rep, **t} for t in texts]
    for role in roles:
        by_role[role]["verdict"] = floor_bar.setting_verdict(by_role[role]["records"], rung=rung, scenarios=role_scenarios(role, scenarios))
    return by_role


def sweep(scenarios: dict[str, Scenario], backends: Any, *, width: int, rung1: str = "needed", roles: list[str] | None = None,
          templates: str = "model", max_rung: int = 2, log: Callable[[str], None] = lambda _: None) -> dict[str, Any]:
    """Climb the ladder: rung 0 for every role, rung 1 for every role (or only where rung 0 failed), rung 2 where neither cleared."""
    inputs = InputCache(scenarios)
    all_roles = [r for r in ROLES if roles is None or r in roles]
    tried: dict[str, dict[int, dict[str, Any]]] = {r: {} for r in all_roles}
    notes: dict[str, dict[int, str]] = {r: {} for r in all_roles}
    texts: dict[tuple[str, int], list[dict[str, Any]]] = {}
    records: list[dict[str, Any]] = []

    def climb(rung: int, roles: list[str]) -> None:
        log(f"rung {rung} ({RUNGS[rung]['label']}): {len(roles)} role(s), width {1 if rung == 0 else width}")
        for role, out in run_rung(roles, rung, scenarios, inputs, backends, width, templates).items():
            tried[role][rung] = out["verdict"]
            records.extend(out["records"])
            texts[(role, rung)] = out["texts"]

    climb(0, all_roles)
    needed1 = [r for r in all_roles if rung1 == "all" or not tried[r][0]["clears"]]
    for role in all_roles:
        if role not in needed1:
            notes[role][1] = "not run: rung 0 cleared the bar"
    if max_rung >= 1:
        climb(1, needed1)
    else:
        needed1 = []
        for role in all_roles:
            notes[role].setdefault(1, "not run: limited to rung 0 for this run")
    needed2 = [r for r in all_roles if not any(v["clears"] for v in tried[r].values())]
    for role in all_roles:
        if role not in needed2:
            notes[role][2] = "not run: " + ("rung 0" if tried[role].get(0, {}).get("clears") else "rung 1") + " cleared the bar"
        elif max_rung < 2:
            notes[role][2] = f"not run: this run was limited to rung {max_rung}"
    needed2 = [r for r in needed2 if max_rung >= 2]
    if needed2:
        climb(2, needed2)
    ladder = {r: {"tried": {k: v for k, v in sorted(tried[r].items())}, "skipped": notes[r],
                  "lowest_passing_rung": floor_bar.lowest_passing_rung(tried[r])} for r in all_roles}
    return {"ladder": ladder, "records": records, "texts": texts, "scenarios": list(scenarios), "templates": templates}


# --- reporting ---------------------------------------------------------------------------------------------------------------
def _cell(role_ladder: dict[str, Any], rung: int) -> str:
    verdict = role_ladder["tried"].get(rung)
    if verdict is None:
        return role_ladder["skipped"].get(rung, "not run")
    if verdict["clears"]:
        return "pass" + (f" ({verdict['retried']} retried)" if verdict["retried"] else "")
    failed = [f"{k}×{n}" for k, n in verdict["failures"].items() if n]
    return "fail: " + (", ".join(failed) or "; ".join(verdict["reasons"]))


def table_rows(result: dict[str, Any], usage: dict[tuple[str, int], dict[str, Any]] | None = None) -> list[list[str]]:
    rows = []
    for role, ladder in result["ladder"].items():
        low = ladder["lowest_passing_rung"]
        used = (usage or {}).get((role, low)) if low is not None else None
        verdict = ladder["tried"].get(low) if low is not None else None
        rows.append([role, "none" if low is None else f"{low} ({RUNGS[low]['label']})", _cell(ladder, 0), _cell(ladder, 1), _cell(ladder, 2),
                     "—" if verdict is None else f"{verdict['first_pass_rate']:.0%}",
                     used["cost_per_successful_narrative_usd"] if used else "n/a", used["tokens"] if used else "n/a", used["latency"] if used else "n/a"])
    return rows


def render_table(rows: list[list[str]]) -> str:
    """The layout plans/archive/tune-ais/floor.md uses, so a re-run prints a table comparable with the committed report."""
    lines = ["| " + " | ".join(TABLE_COLUMNS) + " |", "|" + "---|" * len(TABLE_COLUMNS)]
    return "\n".join(lines + ["| " + " | ".join(str(c) for c in row) + " |" for row in rows])


def t5_candidates(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Paragraphs of each role's lowest passing rung, for the T5 sample (identity only; the texts stay in the texts file)."""
    out = []
    for role in (r for r in T5_ROLES if r in result["ladder"]):
        low = result["ladder"][role]["lowest_passing_rung"]
        for t in result["texts"].get((role, low), []) if low is not None else []:
            out.append({k: t[k] for k in ("role", "scenario", "tool_mode", "rep", "rule_id", "source")})
    return out


def write_run_file(path: Path, result: dict[str, Any], header: dict[str, Any]) -> None:
    """Metadata only: one row per run, one per rung verdict, one per role ladder."""
    rows = [{"event": "sweep_start", **header}] + [{"event": "run", **r} for r in result["records"]]
    for role, ladder in result["ladder"].items():
        rows += [{"event": "verdict", "role": role, "rung": rung, **verdict} for rung, verdict in ladder["tried"].items()]
        rows.append({"event": "ladder", "role": role, "lowest_passing_rung": ladder["lowest_passing_rung"],
                     "rungs_tried": sorted(ladder["tried"]), "skipped": {str(k): v for k, v in ladder["skipped"].items()}})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:                      # append: a live sweep's batch and request rows are already in the file
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def scenarios_markdown(scenarios: dict[str, Scenario]) -> str:
    grid = len(floor_bar.expected_cells(1, ["x"]))
    lines = ["---", 'gist: "Read when: confirming or auditing which synthetic scenarios the tune-ais sweep runs, how the script chose them and how many runs that makes."',
             "---", "", "# Tune AIs: scenarios", "",
             "Generated by `python3 -m benchmarks.floor_sweep --scenarios-md plans/archive/tune-ais/scenarios.md`; do not edit by hand. Synthetic data only.", "",
             "Each domain role runs `sample` and its own regime's `fail` and `gap` case. The auditor and the narrative role run `sample`, `fail:all` and "
             "`gap:all`; their inputs (the other roles' results) are built by code only, so they do not depend on the model being tuned. "
             f"Per role and rung 1 or 2 that is scenarios × 2 tool modes × {floor_bar.REPS} repetitions; rung 0 is deterministic (one run per scenario).", "",
             "Choice rule: for each regime, in the fixture order of `tests/response_fixtures.py` (base cases, then each leaf dropped, then each boolean flipped, "
             "then value changes), the first case with a `not_satisfied` finding is `fail`, and the first with an `unable_to_determine` finding and no "
             "`not_satisfied` finding is `gap`. The spec names `tests/fixtures/*/scenarios.json`, but only YBS has one; the other regimes' cases come from the "
             "same fixture source the response-templates sweep used (the cases each evaluator suite already uses).", "",
             "| Scenario | Regime | Kind | Chosen case | Evaluator result |", "|---|---|---|---|---|"]
    for s in scenarios.values():
        lines.append(f"| `{s.id}` | {s.regime} | {s.kind} | {s.source} | {s.summary or '—'} |")
    missing = [f"{k}:{d}" for d in DOMAINS for k in ("fail", "gap") if f"{k}:{d}" not in scenarios]
    lines += ["", "Regimes with no failing or no gap case in the fixtures (these roles run fewer scenarios): " + (", ".join(missing) or "none") + ".", "",
              "| Role | Scenarios | Runs at rung 1 or 2 | Runs at rung 0 |", "|---|---|---|---|"]
    total = 0
    for role in ROLES:
        names = role_scenarios(role, scenarios)
        total += len(names) * grid
        lines.append(f"| {role} | {', '.join(names)} | {len(names) * grid} | {len(names)} |")
    lines += ["", f"Total at one rung for all {len(ROLES)} roles: {total} runs. Each domain or auditor run makes about 2 model requests (more on a retry or a harness fallback); "
              "a narrative run makes 1.", ""]
    return "\n".join(lines)


# --- live: one-request diagnostics ---------------------------------------------------------------------------------------------
RUNS = ROOT / "plans/archive/tune-ais/runs-anthropic.jsonl"
DIAGNOSTIC_ROLE = "ybs"


class _Done(Exception):
    """Raised by the stub tool executor: the first response is all a diagnostic needs."""


class _Capture:
    """The client the loop sees: the guarded client, remembering the one response."""

    def __init__(self, guard: Any) -> None:
        self.guard, self.response = guard, None
        self.messages = self
        self.begin_role = guard.begin_role

    def create(self, **request: Any) -> Any:
        self.response = self.guard.messages.create(**request)
        return self.response


def diagnose(sdk: Any, model: str, *, ledger: Path | str, runs_path: Path | str, today: str, role: str = DIAGNOSTIC_ROLE) -> dict[str, Any]:
    """One request on one synthetic case: the first request of model mode, exactly as the production loop builds it (a forced tool choice,
    or `auto` plus the instruction for a model that rejects forcing). Reserved first, sent through the guard (zero SDK retries, finite
    timeout, a limit of one request, one model), settled from reported usage or retained whole. Records metadata only."""
    from agents.runner import _narration_input
    from agents.backends import ANTHROPIC_MAX_TOKENS
    from compliance_common.mcp_client import list_tool_specs
    from compliance_common.tools import run_anthropic_tool_loop
    from scripts import anthropic_cost_estimator as estimator
    from test_anthropic_live_parity import BYTE_BOUND, GuardedAnthropic, RunFile, read_usage, usage_cost

    runs, run_id = RunFile(runs_path), uuid.uuid4().hex
    bound = estimator.estimate(model, 1, BYTE_BOUND, ANTHROPIC_MAX_TOKENS, today)           # a stale price date or a model not priced raises here
    target, _, adapter = parts(role)
    canonical, reason = adapter.tool_arguments(SAMPLE)
    assert canonical, reason
    spec = next(s for s in asyncio.run(list_tool_specs(target)) if s["name"] == adapter.TOOL)
    system = AGENTS[role]["system_prompt"]
    messages = [{"role": "user", "content": _narration_input(AGENTS[role], adapter.TOOL.removesuffix("_evaluate"), SAMPLE, canonical, adapter)}]
    from test_anthropic_live_parity import ALLOWED_MODELS
    if model not in ALLOWED_MODELS:
        from test_anthropic_live_parity import GuardRefusal
        raise GuardRefusal(f"{model!r} is not an allowed model")
    reservation_id, bound = estimator.reserve(Path(ledger), model, 1, BYTE_BOUND, ANTHROPIC_MAX_TOKENS, today)
    runs.append({"event": "diagnostic_reservation", "run_id": run_id, "reservation_id": reservation_id, "model": model, "bound_usd": str(bound),
                 "request_limit": 1, "input_bound_bytes": BYTE_BOUND, "max_tokens": ANTHROPIC_MAX_TOKENS, "role": role, "pricing_checked": estimator.PRICE_CHECKED})
    guard = GuardedAnthropic(sdk, run_id=run_id, reservation_id=reservation_id, runs=runs, limit=1, model=model)
    capture = _Capture(guard)
    guard.begin_role(role, "model")
    started, outcome, error = time.monotonic(), "no_tool_call", None

    def execute(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        raise _Done

    try:
        run_anthropic_tool_loop(capture, spec, execute, model=model, system=system, messages=messages, max_tokens=ANTHROPIC_MAX_TOKENS, force_first=True)
    except _Done:
        outcome = "tool_called"
    except Exception as exc:                       # the guard turns an API error into a GuardRefusal; its type is all we keep
        outcome, error = "error", type(exc).__name__
    response = capture.response
    usage = read_usage(response) if response is not None else None
    cost = usage_cost(usage, model)
    settled = None
    if not guard.unknown_cost and cost is not None:
        estimator.settle(Path(ledger), reservation_id, cost, "api-usage")
        settled = str(cost)
    row = {"event": "diagnostic", "run_id": run_id, "reservation_id": reservation_id, "model": model, "role": role, "outcome": outcome, "error": error,
           "tool_choice_sent": next((r.get("tool_choice") for r in runs.rows(run_id) if r["event"] == "request_start"), None),
           "requests": guard.sent, "stop_reason": getattr(response, "stop_reason", None),
           "blocks": [getattr(b, "type", None) for b in getattr(response, "content", [])], "usage": usage, "settlement_usd": settled,
           "reservation_retained": settled is None, "elapsed_seconds": round(time.monotonic() - started, 3)}
    runs.append(row)
    return row


class BudgetStop(Exception):
    """A live batch that would pass the per-run ceiling or the plan bound, or whose usage is unknown: the sweep stops and the case goes to Jim."""


class LiveBackends:
    """Anthropic backends for rungs 1 and 2. One reservation per batch (a role in one tool mode: its cells run together), made at the batch's
    worst case before the first request, settled from reported usage afterwards, or retained whole when any usage is unknown. Every request
    goes through GuardedAnthropic: zero SDK retries, finite timeout, one allowed model, the per-role request bound, a byte bound."""
    BATCH_CEILING = Decimal("1.50")            # spec R5: at most USD 1.50 reserved per run
    PLAN_BOUND = Decimal("5")                  # spec R5: at most USD 5 of live spend for this plan

    def __init__(self, sdk: Any, *, ledger: Path | str, runs_path: Path | str, today: str, templates: str = "model", spent: Decimal = Decimal(0),
                 observer: Callable[[str, str], None] | None = None) -> None:
        from test_anthropic_live_parity import RunFile
        self.sdk, self.ledger, self.today, self.templates = sdk, Path(ledger), today, templates
        self.runs, self.spent, self.observer = RunFile(runs_path), spent, observer       # observer: a test double's role hook; unused live
        self._guards: dict[tuple, Any] = {}
        self._open: dict[tuple, tuple] = {}
        self._usage: dict[tuple[str, int], dict[str, Any]] = {}

    def open_batch(self, rung: int, role: str, mode: str | None, cells: int) -> None:
        from agents.backends import ANTHROPIC_MAX_TOKENS
        from live_parity_common import worst_case_requests
        from scripts import anthropic_cost_estimator as estimator
        from test_anthropic_live_parity import BYTE_BOUND, GuardedAnthropic
        model = RUNGS[rung]["model"]
        attempts = cells * worst_case_requests("anthropic", mode or "model", role)
        bound = estimator.estimate(model, attempts, BYTE_BOUND, ANTHROPIC_MAX_TOKENS, self.today)
        if bound > self.BATCH_CEILING:
            raise BudgetStop(f"{role} rung {rung} {mode}: the batch worst case USD {bound} is over the USD {self.BATCH_CEILING} per-run ceiling")
        if self.spent + bound > self.PLAN_BOUND:
            raise BudgetStop(f"{role} rung {rung}: settled USD {self.spent} plus a batch worst case USD {bound} would pass the USD {self.PLAN_BOUND} plan bound")
        rid, bound = estimator.reserve(self.ledger, model, attempts, BYTE_BOUND, ANTHROPIC_MAX_TOKENS, self.today)
        run_id = uuid.uuid4().hex
        self.runs.append({"event": "batch_reservation", "run_id": run_id, "reservation_id": rid, "role": role, "rung": rung, "tool_mode": mode, "model": model,
                          "cells": cells, "request_limit": attempts, "bound_usd": str(bound), "templates": self.templates})
        guard = GuardedAnthropic(self.sdk, run_id=run_id, reservation_id=rid, runs=self.runs, limit=attempts, model=model, observer=self.observer)
        self._guards[(rung, role, mode)] = guard
        self._open[(rung, role, mode)] = (rid, run_id, bound)

    def get(self, rung: int, role: str, mode: str | None = None) -> tuple[Any, Callable[[], bool]]:
        from agents.backends import Backend
        guard = self._guards[(rung, role, mode)]
        return Backend("anthropic", RUNGS[rung]["model"], client=guard), lambda: guard._context.truncated

    def close_batch(self, rung: int, role: str, mode: str | None) -> None:
        from scripts import anthropic_cost_estimator as estimator
        guard = self._guards.pop((rung, role, mode))
        rid, run_id, bound = self._open.pop((rung, role, mode))
        if guard.unknown_cost:
            self.runs.append({"event": "batch_settlement", "run_id": run_id, "reservation_id": rid, "role": role, "rung": rung, "settlement_usd": None,
                              "reservation_retained": True, "requests": guard.sent})
            raise BudgetStop(f"{role} rung {rung} {mode}: usage unknown for a request; the whole reservation USD {bound} is retained")
        total = sum(guard.costs, Decimal(0))
        estimator.settle(self.ledger, rid, total, "api-usage")
        self.spent += total
        rows = [r for r in self.runs.rows(run_id) if r.get("event") == "request_outcome" and r.get("usage")]
        use = self._usage.setdefault((role, rung), {"cost": Decimal(0), "in": 0, "out": 0, "requests": 0})
        use["cost"] += total
        use["in"] += sum(r["usage"]["input_tokens"] + r["usage"]["cache_creation_input_tokens"] + r["usage"]["cache_read_input_tokens"] for r in rows)
        use["out"] += sum(r["usage"]["output_tokens"] for r in rows)
        use["requests"] += guard.sent
        self.runs.append({"event": "batch_settlement", "run_id": run_id, "reservation_id": rid, "role": role, "rung": rung, "tool_mode": mode,
                          "settlement_usd": str(total), "reservation_retained": False, "requests": guard.sent})

    def usage_table(self, result: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
        """Per role and rung: cost per successful narrative (a run that passes T1-T4), tokens in / out per such run, mean latency of the runs."""
        out = {}
        for (role, rung), use in self._usage.items():
            records = [r for r in result["records"] if r["role"] == role and r["rung"] == rung]
            good = sum(1 for r in records if floor_bar.run_passes(r))
            lat = [r["latency_seconds"] for r in records if r.get("latency_seconds") is not None]
            out[(role, rung)] = {"cost_per_successful_narrative_usd": f"{use['cost'] / good:.6f}" if good else "n/a (none succeeded)",
                                 "tokens": f"{use['in'] // max(good, 1)} / {use['out'] // max(good, 1)}" if good else "n/a",
                                 "latency": f"{sum(lat) / len(lat):.1f}" if lat else "n/a", "settled_usd": str(use["cost"]), "requests": use["requests"]}
        return out


class LiveClimbRequired(Exception):
    """A role failed rung 0, so rung 1 or 2 would need live requests: the plan's reservations for that are brought to Jim, not improvised."""


class _NoLiveClimb:
    def open_batch(self, rung: int, role: str, mode: str | None, cells: int) -> None:
        raise LiveClimbRequired(f"{role} needs rung {rung}")

    def get(self, rung: int, role: str, mode: str | None = None) -> Any:
        raise LiveClimbRequired(f"{role} needs rung {rung}")


def live(provider: str | None, out: Path, *, climb: bool = False, templates: str = "model", rung1: str = "needed", max_rung: int = 2,
         width: int | None = None) -> int:
    """Rung 0 offline, then either the two one-request diagnostics (default) or, with `climb` (Jim's authorization for live rungs), the live
    climb: rung 1 where `rung1` says, rung 2 only if `max_rung` allows, each batch reserved first and settled from usage."""
    if provider != "anthropic":
        print("--live supports only --provider anthropic (no OpenAI live call is authorized by this plan).", file=sys.stderr)
        return 2
    scenarios = build_scenarios()
    width = width or load_settings()["remote_concurrency"]
    log = lambda m: print(m, file=sys.stderr)
    if not climb:
        try:
            result = sweep(scenarios, _NoLiveClimb(), width=1, rung1="needed", log=log)
        except LiveClimbRequired as exc:
            print(f"STOP: {exc}. A role failed rung 0; the per-role live reservations for rungs 1 and 2 are a decision for Jim (spec 'Escalate when').", file=sys.stderr)
            return 3
    from dotenv import dotenv_values
    import anthropic
    from scripts import anthropic_cost_estimator as estimator
    from test_anthropic_live_parity import ALLOWED_MODELS, TIMEOUT, today_denver
    if today_denver() != estimator.PRICE_CHECKED:
        print("STOP: verify rates at the cited URL and update the estimator first (stale PRICE_CHECKED).", file=sys.stderr)
        return 2
    key = os.getenv("ANTHROPIC_API_KEY") or dotenv_values(ROOT / ".env").get("ANTHROPIC_API_KEY")
    if not key:
        print("STOP: ANTHROPIC_API_KEY is required for live requests.", file=sys.stderr)
        return 2
    sdk = anthropic.Anthropic(api_key=key, base_url="https://api.anthropic.com", timeout=TIMEOUT, max_retries=0)
    try:
        if climb:
            backends = LiveBackends(sdk, ledger=estimator.LEDGER, runs_path=out, today=today_denver(), templates=templates)
            header = {"mode": "live-climb", "rung1": rung1, "max_rung": max_rung, "templates": templates, "width": width}
            try:
                result = sweep(scenarios, backends, width=width, rung1=rung1, templates=templates, max_rung=max_rung, log=log)
            except BudgetStop as exc:
                print(f"STOP (nothing further is spent; any open reservation stays held): {exc}", file=sys.stderr)
                return 3
            write_run_file(out, result, {**header, "scenarios": result["scenarios"], "settled_usd": str(backends.spent)})
            print(render_table(table_rows(result, backends.usage_table(result))))
            print(f"\nsettled USD {backends.spent} for this run; rung 1 setting: Haiku 5.5, effort low, templates: {templates}")
            return 0
        write_run_file(out, result, {"mode": "live", "rung1": "needed", "scenarios": result["scenarios"], "live_rungs_needed": []})
        diagnostics = [diagnose(sdk, model, ledger=estimator.LEDGER, runs_path=out, today=today_denver()) for model in ALLOWED_MODELS]
    finally:
        sdk.close()
    print(render_table(table_rows(result)))
    for d in diagnostics:
        print(f"diagnostic {d['model']}: {d['outcome']} (tool_choice {d['tool_choice_sent']}, stop {d['stop_reason']}, blocks {d['blocks']}, "
              f"USD {d['settlement_usd']}, retained {d['reservation_retained']})")
    return 0 if all(d["outcome"] != "error" for d in diagnostics) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="fake model backends: no network, no credentials, no spend")
    parser.add_argument("--live", action="store_true", help="rung 0 offline, then one live diagnostic request per candidate model (Anthropic only)")
    parser.add_argument("--provider", help="with --live (step 03)")
    parser.add_argument("--out", type=Path, help="write the metadata-only run file here")
    parser.add_argument("--texts", type=Path, help="write the paragraph texts of the T5 candidates here (synthetic data; keep out of the run file)")
    parser.add_argument("--width", type=int, help="runs in flight at once (default: agents.yaml remote_concurrency)")
    parser.add_argument("--weak", default="", help="dry run: comma-separated roles whose rung-1 model is not tall enough")
    parser.add_argument("--rung1", choices=("all", "needed"), default="needed", help="needed (default, Jim 2026-11-07): rung 1 only where rung 0 failed; all: every role")
    parser.add_argument("--scenarios-md", type=Path, help="write the scenario list here and exit")
    parser.add_argument("--climb", action="store_true", help="with --live: authorized live rungs (rung 1, and rung 2 if --max-rung allows), reserved per batch")
    parser.add_argument("--templates", choices=("model", "code"), default="model", help="the examiner-paragraph setting rungs 1 and 2 run under")
    parser.add_argument("--max-rung", type=int, choices=(1, 2), default=2, help="highest rung this run may climb to")
    args = parser.parse_args(argv)
    if args.live:
        return live(args.provider, args.out or RUNS, climb=args.climb, templates=args.templates, rung1=args.rung1, max_rung=args.max_rung, width=args.width)
    scenarios = build_scenarios()
    if args.scenarios_md:
        args.scenarios_md.write_text(scenarios_markdown(scenarios), encoding="utf-8")
        print(f"wrote {args.scenarios_md} ({len(scenarios)} scenarios)")
        return 0
    if not args.dry_run:
        parser.error("choose --dry-run, or --scenarios-md PATH")
    width = args.width or load_settings()["remote_concurrency"]
    weak = {r for r in args.weak.split(",") if r}
    unknown = weak - set(ROLES)
    if unknown:
        parser.error(f"unknown role(s): {', '.join(sorted(unknown))}")
    result = sweep(scenarios, DryBackends(weak=weak), width=width, rung1=args.rung1, templates=args.templates, max_rung=args.max_rung,
                   log=lambda m: print(m, file=sys.stderr))
    print(render_table(table_rows(result)))
    sample = floor_bar.t5_sample(t5_candidates(result), T5_ROLES)
    print(f"\nT5 sample: {sample['total']} paragraphs chosen by script" + (f"; short: {sample['short']}" if sample["short"] else ""))
    if args.out:
        write_run_file(args.out, result, {"mode": "dry-run", "width": width, "rung1": args.rung1, "scenarios": result["scenarios"]})
        print(f"[run file written to {args.out}]", file=sys.stderr)
    if args.texts:
        wanted = {(p["role"], p["scenario"], p["tool_mode"], p["rep"], p["rule_id"]) for p in sample["sample"]}
        with args.texts.open("w", encoding="utf-8") as f:
            for (role, rung), items in result["texts"].items():
                for t in items:
                    if (t["role"], t["scenario"], t["tool_mode"], t["rep"], t["rule_id"]) in wanted and result["ladder"][role]["lowest_passing_rung"] == rung:
                        f.write(json.dumps(t, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

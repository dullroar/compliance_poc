"""The quality bar of plans/archive/tune-ais (spec R2) as pure functions over run records. No I/O, no model, no network.

A run record is metadata only (benchmarks/floor_sweep.py builds it from one role run; see `Record` below). A setting (a role at one rung)
clears the bar when, over every scenario in both tool modes and 3 repetitions, T1-T4 hold in all runs and at least 90% of the runs are
first-pass. T5 (twelve paragraphs read by Jim) is a human step; `t5_sample` only chooses which twelve, by script.

  T1  the narrative source is the model's (`model` or `model_retry`), never a code fallback. A rung that asks no model (design "code")
      has nothing to fall back from and passes T1 by construction; the report says so rather than hiding it.
  T2  no output stopped at `max_tokens`. An unrecorded value is a fail: unknown is not a pass.
  T3  the decision id and classification equal direct evaluation (a sanity check; code owns them).
  T4  every examiner paragraph and loan-officer item is within the limits of plan response-templates, and no paragraph was rewritten
      by code after the model's one retry. The narrative role's summary: plain, grounded, at most SUMMARY_WORD_LIMIT words, by the model.

Record fields used here (all optional ones are treated as failing when absent):
  role, rung, scenario, tool_mode (None at rung 0), rep, design ("model" | "code"), templates ("model" | "code"; "code" = the paragraphs are
  code-written by design, so a "code" paragraph source is not a rewrite), narrative_source, attempts, stopped_at_max_tokens,
  decision_id, classification, direct_decision_id, direct_classification,
  paragraphs [{rule_id, source ("model" | "model_retry" | "code"), words, problems [labels], over_limit?}],
  items [{kind ("customer" | "refer"), sentences, max_sentence_words}], summary {source, words, violations} (narrative role only).
"""
from __future__ import annotations

import hashlib
import itertools
import re
from typing import Any, Iterable

from compliance_common.templates import examiner, report

REPS = 3
TOOL_MODES = ("model", "seeded")
FIRST_PASS_MIN = 0.90
GOOD_SOURCES = ("model", "model_retry")
CHECKS = ("T1", "T2", "T3", "T4")
# Loan-officer sheet limits from plan response-templates (step 02: customer items at most 2 sentences of at most 20 words, referrals exactly
# 1 sentence of at most 20 words); tests/test_floor_bar.py checks every sheet the real renderer produces against them.
ITEM_LIMITS = {"customer": (2, 20), "refer": (1, 20)}          # (most sentences, most words in a sentence)
PARAGRAPH_FLOOR = examiner.FLOOR
PARAGRAPH_LIMITS = examiner.LIMITS
SUMMARY_WORD_LIMIT = report.SUMMARY_WORD_LIMIT
T5_TOTAL = 12
T5_COUNTS = {"hmda": 4}                                         # every other role contributes 1 (nine roles: 4 + 8 = 12)


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if s]


def _is_code(record: dict[str, Any]) -> bool:
    return record.get("design") == "code"


def t1(record: dict[str, Any]) -> bool:
    if _is_code(record):
        return True
    if record.get("role") == "narrative":
        return (record.get("summary") or {}).get("source") == "model"
    return record.get("narrative_source") in GOOD_SOURCES


def t2(record: dict[str, Any]) -> bool:
    return record.get("stopped_at_max_tokens") is False


def t3(record: dict[str, Any]) -> bool:
    if record.get("role") == "narrative":
        return True                                              # the report's summary carries no decision of its own
    pairs = (("decision_id", "direct_decision_id"), ("classification", "direct_classification"))
    return all(record.get(a) is not None and record.get(a) == record.get(b) for a, b in pairs)


def _paragraph_ok(paragraph: dict[str, Any], role: str, design: str, templates: str | None = None) -> bool:
    words = paragraph.get("words")
    if paragraph.get("problems") or paragraph.get("over_limit") or not isinstance(words, int):
        return False
    if not PARAGRAPH_FLOOR <= words <= PARAGRAPH_LIMITS.get(role, 0):
        return False
    # "code" in a model rung = the model's paragraph failed twice, unless templates: code made code the author by design (Jim, 2026-11-07)
    return design == "code" or templates == "code" or paragraph.get("source") in GOOD_SOURCES


def _item_ok(item: dict[str, Any]) -> bool:
    limits = ITEM_LIMITS.get(item.get("kind"))
    if limits is None or not isinstance(item.get("sentences"), int) or not isinstance(item.get("max_sentence_words"), int):
        return False
    most_sentences, most_words = limits
    if item["kind"] == "refer" and item["sentences"] != 1:
        return False
    return 1 <= item["sentences"] <= most_sentences and 1 <= item["max_sentence_words"] <= most_words


def t4(record: dict[str, Any]) -> bool:
    design = record.get("design", "model")
    if record.get("role") == "narrative":
        summary = record.get("summary")
        if not isinstance(summary, dict) or summary.get("violations") or not isinstance(summary.get("words"), int):
            return False
        if summary["words"] > SUMMARY_WORD_LIMIT or (design != "code" and (summary["words"] < 1 or summary.get("source") != "model")):
            return False
        return True
    paragraphs, items = record.get("paragraphs"), record.get("items")
    if not isinstance(paragraphs, list) or not isinstance(items, list):
        return False
    templates = record.get("templates")
    return all(_paragraph_ok(p, record.get("role"), design, templates) for p in paragraphs) and all(_item_ok(i) for i in items)


def run_checks(record: dict[str, Any]) -> dict[str, bool]:
    return {"T1": t1(record), "T2": t2(record), "T3": t3(record), "T4": t4(record)}


def run_passes(record: dict[str, Any]) -> bool:
    return all(run_checks(record).values())


def first_pass(record: dict[str, Any]) -> bool:
    """Passes T1-T4 and needed no retry: the narrative and every paragraph came from the model's first reply."""
    if not run_passes(record):
        return False
    if _is_code(record):
        return True
    if record.get("role") == "narrative":
        return True                                              # one request, no retry exists
    by_code = record.get("templates") == "code"
    return record.get("narrative_source") == "model" and (by_code or all(p.get("source") == "model" for p in record.get("paragraphs", [])))


def expected_cells(rung: int, scenarios: Iterable[str]) -> set[tuple]:
    """The (scenario, tool_mode, rep) cells a setting must have run. Rung 0 is deterministic, so one cell per scenario."""
    scenarios = list(scenarios)
    if rung == 0:
        return {(s, None, 0) for s in scenarios}
    return set(itertools.product(scenarios, TOOL_MODES, range(REPS)))


def setting_verdict(records: list[dict[str, Any]], *, rung: int, scenarios: Iterable[str]) -> dict[str, Any]:
    """Whether one role at one rung clears the bar. A missing, skipped, duplicated or timed-out cell is never a pass."""
    expected = expected_cells(rung, scenarios)
    seen: dict[tuple, dict[str, Any]] = {}
    duplicates = 0
    for record in records:
        key = (record.get("scenario"), record.get("tool_mode"), record.get("rep"))
        if key in seen:
            duplicates += 1
        seen[key] = record
    missing = sorted(expected - set(seen), key=str)
    extra = sorted(set(seen) - expected, key=str)
    failures = {name: 0 for name in CHECKS}
    for record in seen.values():
        for name, ok in run_checks(record).items():
            failures[name] += 0 if ok else 1
    firsts = sum(1 for record in seen.values() if first_pass(record))
    rate = firsts / len(seen) if seen else 0.0
    reasons = []
    if missing:
        reasons.append(f"incomplete: {len(expected) - len(missing)} of {len(expected)} runs")
    if duplicates or extra:
        reasons.append(f"unexpected runs: {duplicates} duplicated, {len(extra)} outside the plan")
    reasons += [f"{name} failed in {count} run(s)" for name, count in failures.items() if count]
    if seen and rate < FIRST_PASS_MIN:
        reasons.append(f"first-pass rate {rate:.0%} is below {FIRST_PASS_MIN:.0%}")
    return {"clears": not reasons and bool(seen), "runs": len(seen), "expected": len(expected), "failures": failures,
            "first_pass_rate": round(rate, 4), "retried": len(seen) - firsts, "reasons": reasons}


def lowest_passing_rung(verdicts: dict[int, dict[str, Any]]) -> int | None:
    """The first rung, climbing from the cheapest, whose verdict clears the bar."""
    return next((rung for rung in sorted(verdicts) if verdicts[rung]["clears"]), None)


def t5_sample(paragraphs: Iterable[dict[str, Any]], roles: Iterable[str], seed: str = "tune-ais-t5-v1") -> dict[str, Any]:
    """Choose the paragraphs Jim reads (T5) by script, from paragraphs of the cheapest passing setting. No randomness: the order is a hash of
    the seed and the paragraph's identity, preferring different scenarios and rules within a role. Each entry needs role, scenario,
    tool_mode, rep, rule_id. Returns {"sample": [...], "short": {role: missing count}, "total": n}."""
    by_role: dict[str, list[dict[str, Any]]] = {}
    for p in paragraphs:
        by_role.setdefault(p["role"], []).append(p)
    sample, short = [], {}
    for role in roles:
        want = T5_COUNTS.get(role, 1)
        ranked = sorted(by_role.get(role, []), key=lambda p: hashlib.sha256(
            "|".join([seed, *(str(p.get(k)) for k in ("role", "scenario", "tool_mode", "rep", "rule_id"))]).encode()).hexdigest())
        chosen: list[dict[str, Any]] = []
        scenarios: set[Any] = set()
        rules: set[Any] = set()
        stages = (lambda p: p.get("scenario") not in scenarios and p.get("rule_id") not in rules,      # different scenario and rule first,
                  lambda p: p.get("rule_id") not in rules,                                              # then a different rule,
                  lambda p: True)                                                                        # then whatever is left
        for stage in stages:
            for p in ranked:
                if len(chosen) < want and p not in chosen and stage(p):
                    chosen.append(p)
                    scenarios.add(p.get("scenario"))
                    rules.add(p.get("rule_id"))
        sample += chosen
        if len(chosen) < want:
            short[role] = want - len(chosen)
    return {"sample": sample, "short": short, "total": len(sample)}

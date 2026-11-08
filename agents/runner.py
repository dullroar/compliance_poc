"""Run one agent: the model calls the domain's MCP tool, then writes the narrative.

Tool-backed agents (prompt header `Tool:`) get a decision record from the evaluator.
The harness forces the tool arguments to the canonical input taken from the loan
payload, so the model triggers the call but cannot alter the facts. If the model
never calls the tool, the harness calls it and injects the result (WARNING logged).
The final result is assembled from the decision plus the model's narrative.
"""
from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Any

from agent_prompts import AGENTS
from compliance_common.assemble import DECISION_OWNED, assemble, narrative_guard
from compliance_common.narrative import check_narrative, check_paragraphs, deterministic_narrative, retry_message
from compliance_common.narrative_schema import schema_for
from compliance_common.templates import examiner, loan_officer, report
from compliance_common.mcp_client import call_tool, list_tool_specs, stdio_target
from compliance_common.obs import get_logger
from compliance_common.regulations import regulation_text
from compliance_mcp.registry import adapter as domain_adapter

from .backends import Backend

DEFAULT_PREFIX = (
    "Evaluate the following loan data and return your compliance determination "
    "as a JSON object per your output contract."
)


_THINK = re.compile(r"<(think|thinking)>(.*?)</\1>", re.S | re.I)


def split_thinking(text: str) -> tuple[str, str]:
    """(answer, reasoning). Some models (e.g. LFM2.5) put their reasoning inline in <think>...</think> before the answer."""
    thoughts = [m.group(2).strip() for m in _THINK.finditer(text)]
    answer = _THINK.sub("", text)
    closer = re.search(r"</think(?:ing)?>", answer, re.I)          # a closer with no opener: everything before it is reasoning
    if closer:
        parts = re.split(r"</think(?:ing)?>", answer, flags=re.I)
        thoughts.append(parts[0].strip())
        answer = parts[-1]
    return answer.strip(), "\n".join(t for t in thoughts if t)


def extract_json(text: str) -> tuple[Any, str | None]:
    """Parse the first complete JSON object in model text, ignoring inline reasoning, code fences and surrounding prose."""
    answer, _ = split_thinking(text)
    cleaned = answer.strip()
    if cleaned.startswith("```"):
        cleaned = "\n".join(l for l in cleaned.splitlines() if not l.strip().startswith("```")).strip()
    try:
        return json.loads(cleaned), None
    except json.JSONDecodeError as first:
        decoder, start = json.JSONDecoder(), cleaned.find("{")
        while start != -1:
            try:
                return decoder.raw_decode(cleaned[start:])[0], None
            except json.JSONDecodeError:
                start = cleaned.find("{", start + 1)
        return None, str(first)


def _user_content(agent: dict, loan_data: Any) -> str:
    if isinstance(loan_data, dict):
        return agent.get("user_message_prefix", DEFAULT_PREFIX) + "\n\n" + json.dumps(loan_data, indent=2)
    return str(loan_data)


DEFAULT_OPTIONS = {"tool_mode": "model", "include_regulations": True, "max_regulation_chars": 60000, "max_retries": 1, "templates": "model"}
TOOL_MODES = ("model", "seeded")
TEMPLATE_MODES = ("model", "code")
DRAFTS_KEY = "examiner_paragraph_drafts"
REGULATIONS_HEADER = (
    "## Regulations As Given\n"
    "This is the pinned regulation text for your domain (eCFR as issued on the date shown, identified by hash). It and the tool's\n"
    "decision record are your only sources. Quote or cite only from them. Do no outside research and do not rely on remembered law,\n"
    "case law or guidance; if something is not here, say it is not in the material you were given.\n\n"
)


NARRATE_PREFIX = ("Narrate the decision record that {tool} returns for this case, following your Output Contract. "
                  "The case input below is context only; the decision record is the authority.")


def _narration_input(agent: dict, domain: str, loan_data: Any, canonical: dict | None, adapt: Any) -> str:
    """What a tool-backed agent is shown: its own case and nothing else (not the other 27 sections of the loan file)."""
    if canonical is None:
        return _user_content(agent, loan_data)
    prefix = NARRATE_PREFIX.format(tool=agent["tool"])
    if not getattr(adapt, "NARRATE_CASE", True):
        return prefix + "\n\n(The audit input was passed to the tool; the decision record contains everything you need.)"
    case_id = (loan_data.get("case_information") or {}).get("case_id") if isinstance(loan_data, dict) else None
    return prefix + "\n\n" + json.dumps({"case_id": case_id, f"{domain}_case": canonical["case"]}, indent=2)


def _verified_narrative(raw_text: str, decision: dict[str, Any], case: Any, reg_text: str, domain: str, *, backend: Backend, system: str,
                        base_messages: list[dict], max_retries: int, log: Any, expected: list[dict[str, Any]] | None = None,
                        prompt_decision: dict[str, Any] | None = None, schema: dict[str, Any] | None = None) -> dict[str, Any]:
    """Accept the model's narrative only if it adds no fact the record, the case or the regulation text lacks.

    One retry with the specific violations fed back; if that also fails (or the reply is unusable), code writes the narrative.
    With `expected` (the code-written examiner paragraphs; templates: model) each paragraph is judged separately in the same replies:
    a paragraph that fails any check drives the same single retry, and one that still fails is written by code. `accepted` maps a rule id
    to the model's paragraph and the attempt that passed."""
    attempts: list[dict[str, Any]] = []
    text, tries = raw_text, 0
    shown = prompt_decision or decision
    while True:
        output, parse_error = extract_json(text)
        narrative = output.get("narrative") if isinstance(output, dict) else None
        violations = ["the reply was not valid JSON: " + str(parse_error)[:100]] if parse_error else check_narrative(narrative, decision, case, reg_text, cross_regime=domain == "auditor")
        paragraph_violations = {} if parse_error or expected is None else check_paragraphs(output, expected, decision, case, reg_text, domain)
        bad = {key: found for key, found in paragraph_violations.items() if found}
        entries = (output.get("examiner_paragraphs") if isinstance(output, dict) else None) or []
        attempts.append({"violations": violations, "stripped_fields": [k for k in DECISION_OWNED if isinstance(output, dict) and k in output],
                         "paragraph_violations": bad,
                         "paragraphs": {e["rule_id"]: e["text"] for e in entries if isinstance(e, dict) and e.get("rule_id") in paragraph_violations
                                        and e["rule_id"] not in bad and isinstance(e.get("text"), str)}})
        if not violations and not bad:
            return {"narrative": narrative, "source": "model" if tries == 0 else "model_retry", "attempts": attempts, "output": output, "raw_text": text}
        log.warning("narrative rejected (attempt %d): %s", tries + 1, "; ".join(violations[:3] or [f"{k}: {v[0]}" for k, v in bad.items()][:3]),
                    extra={"decision_id": decision["decision_id"]})
        if tries >= max_retries:
            if violations:
                return {"narrative": deterministic_narrative(decision, domain), "source": "deterministic_fallback", "attempts": attempts, "output": output, "raw_text": text}
            return {"narrative": narrative, "source": "model" if tries == 0 else "model_retry", "attempts": attempts, "output": output, "raw_text": text}
        feedback = violations + [f"examiner paragraph {key}: {found}" for key, items in bad.items() for found in items]
        retry_messages = [*base_messages[:-1], {"role": "user", "content": base_messages[-1]["content"] + _decision_block(shown)},
                          {"role": "assistant", "content": text}, {"role": "user", "content": retry_message(feedback)}]
        text = backend.complete(system, retry_messages, json_mode=True, schema=schema or schema_for("model"))
        log.trace("raw model text (retry)", extra={"decision_id": decision["decision_id"]}, payload=text)
        tries += 1


def _response_templates(decision: dict[str, Any], domain: str, templates: str, expected: list[dict[str, Any]], verdict: dict[str, Any] | None) -> dict[str, Any]:
    """{loan_officer, examiner}: the sheet is always code; each examiner paragraph is the model's (if it passed every check) or code's."""
    accepted: dict[str, tuple[str, str]] = {}
    for number, attempt in enumerate(verdict["attempts"] if verdict else []):
        for key, text in attempt.get("paragraphs", {}).items():
            accepted.setdefault(key, (text, "model" if number == 0 else "model_retry"))
    paragraphs = []
    for p in expected:
        text, source = accepted.get(p["rule_id"], (p["text"], "code")) if templates == "model" else (p["text"], "code")
        paragraphs.append({"rule_id": p["rule_id"], "rule_ids": p["rule_ids"], "grouped": p["grouped"], "subject_id": p["subject_id"], "text": text,
                           "words": len(text.split()), "source": source, **({"over_limit": True} if p.get("over_limit") else {})})
    return {"templates": templates, "loan_officer": loan_officer.render(decision), "examiner": paragraphs}


def run_agent(agent_key: str, loan_data: Any, backend: Backend, history: list[dict] | None = None,
              tool_target: Any | None = None, options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run a tool-backed agent. `tool_target` overrides the MCP stdio server (tests).

    options (from agents.yaml): tool_mode "model" (the model calls the tool; Anthropic's first call is forced; if a model
    still does not call it the harness does) or "seeded" (the harness makes the call and places it in the conversation as
    the agent's own first step, in the provider's native tool-call format); include_regulations (default True);
    max_retries (default 1): how many times a rejected narrative is sent back before code writes it;
    templates "model" (default: the same narrative call also rephrases a code-written draft of each examiner paragraph, shown to the
    model in the tool result; a paragraph that fails the checks is retried once, then written by code) or "code" (nothing extra is
    asked of the model; code writes every paragraph). The loan-officer sheet is always written by code."""
    opts = {**DEFAULT_OPTIONS, **(options or {})}
    if opts["tool_mode"] not in TOOL_MODES:
        raise ValueError(f"tool_mode must be one of {TOOL_MODES}, got {opts['tool_mode']!r}")
    if opts["templates"] not in TEMPLATE_MODES:
        raise ValueError(f"templates must be one of {TEMPLATE_MODES}, got {opts['templates']!r}")
    agent = AGENTS[agent_key]
    domain = agent["tool"].removesuffix("_evaluate")
    log = get_logger(f"agent.{agent_key}", agent["version"])
    adapt = domain_adapter(domain)
    target = tool_target if tool_target is not None else stdio_target(domain)
    canonical, reason = adapt.tool_arguments(loan_data)
    calls: list[dict[str, Any]] = []

    def execute(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name != adapt.TOOL:
            raise ValueError(f"Unknown compliance tool: {name}")
        if arguments != canonical:
            log.warning("model-supplied tool arguments differ from the loan payload; using the payload")
        result = asyncio.run(call_tool(target, name, canonical))
        if opts["templates"] == "model" and isinstance(result, dict) and "decision_id" in result:
            return {**result, DRAFTS_KEY: examiner.drafts(result, domain)}         # for the model to rephrase; removed from the record below
        return result

    messages = list(history or [])
    messages.append({"role": "user", "content": _narration_input(agent, domain, loan_data, canonical, adapt)})
    system = agent["system_prompt"]
    regulation_provenance: list[dict[str, str]] = []
    reg_text = ""
    if opts["include_regulations"]:
        reg_text, regulation_provenance = regulation_text(domain, opts["max_regulation_chars"])
        if reg_text:
            system = system + "\n\n" + REGULATIONS_HEADER + reg_text
    log.trace("system prompt", payload=system)

    raw_text = ""
    if canonical is None:
        decision = adapt.unavailable(reason, loan_data)
        log.warning("no canonical input for %s: %s; the narrative is written by code, no model call", agent["tool"], reason)
        verdict = {"narrative": deterministic_narrative(decision, domain), "source": "deterministic_no_input", "attempts": [], "output": None, "raw_text": ""}
        expected = examiner.render(decision, domain, strict=False)
    else:
        spec = next(s for s in asyncio.run(list_tool_specs(target)) if s["name"] == adapt.TOOL)
        if opts["tool_mode"] == "seeded":
            seeded_result = execute(adapt.TOOL, canonical)
            calls.append({"name": adapt.TOOL, "arguments": canonical, "result": seeded_result, "by": "seeded"})
            raw_text = backend.complete_seeded(system, messages, spec, execute, calls, canonical, seeded_result, schema=schema_for(opts["templates"]))
        else:
            try:
                raw_text = (backend.complete_with_tool(system, messages, spec, execute, calls) if opts["templates"] == "model"
                            else backend.complete_with_tool(system, messages, spec, execute, calls, schema=schema_for("code")))
            except RuntimeError as exc:        # e.g. Ollama HTTP 500 when a small model emits a malformed tool call
                log.warning("tool-calling turn failed (%s); falling back to the harness", str(exc)[:200])
                calls.clear()
        if not calls:
            log.warning("model did not call %s; harness calling it", adapt.TOOL)
            decision = execute(adapt.TOOL, canonical)
            calls.append({"name": adapt.TOOL, "arguments": canonical, "result": decision, "by": "harness"})
            raw_text = backend.complete(system, [*messages[:-1], {"role": "user", "content": messages[-1]["content"] + _decision_block(decision)}],
                                        json_mode=True, schema=schema_for(opts["templates"]))
        prompt_decision = calls[-1]["result"]
        decision = {k: v for k, v in prompt_decision.items() if k != DRAFTS_KEY}
        log.trace("raw model text", extra={"decision_id": decision["decision_id"]}, payload=raw_text)
        _, reasoning = split_thinking(raw_text)
        if reasoning:
            log.trace("model reasoning (inline)", extra={"decision_id": decision["decision_id"]}, payload=reasoning)
        expected = examiner.render(decision, domain, strict=False)
        verdict = _verified_narrative(raw_text, decision, canonical["case"], reg_text, domain, backend=backend, system=system,
                                      base_messages=messages, max_retries=opts["max_retries"], log=log,
                                      expected=expected if opts["templates"] == "model" else None, prompt_decision=prompt_decision,
                                      schema=schema_for(opts["templates"]))
    raw_text = verdict["raw_text"] or raw_text
    first = verdict["attempts"][0] if verdict["attempts"] else {"violations": [], "stripped_fields": []}
    guard = narrative_guard(verdict["output"], decision)
    guard.update({"source": verdict["source"], "attempts": len(verdict["attempts"]), "violations": first["violations"],
                  "retry_violations": verdict["attempts"][1]["violations"] if len(verdict["attempts"]) > 1 else [],
                  "paragraph_violations": first.get("paragraph_violations", {}),
                  "retry_paragraph_violations": verdict["attempts"][1].get("paragraph_violations", {}) if len(verdict["attempts"]) > 1 else {},
                  "grounded": verdict["source"] == "model", "stripped_fields": first["stripped_fields"]})
    extras = adapt.extras(decision) if canonical is not None else None
    templates = _response_templates(decision, domain, opts["templates"], expected, verdict if canonical is not None else None)
    sources = [p["source"] for p in templates["examiner"]]
    guard["paragraphs"] = {source: sources.count(source) for source in ("model", "model_retry", "code") if sources.count(source)}
    parsed = assemble(agent, decision, {"narrative": verdict["narrative"]}, extras, canonical["case"] if canonical else None, verdict["source"], templates)
    warnings = []
    if opts["templates"] == "model" and canonical is not None and "code" in sources:
        warnings.append("examiner paragraphs the model did not write acceptably were written by code: " + ", ".join(p["rule_id"] for p in templates["examiner"] if p["source"] == "code"))
    if first["stripped_fields"]:
        warnings.append(f"the model tried to author decision-owned fields ({', '.join(first['stripped_fields'])}); they were discarded")
    if verdict["source"] == "model_retry":
        warnings.append("the first narrative was rejected and the model rewrote it: " + "; ".join(first["violations"][:3]))
    elif verdict["source"] == "deterministic_fallback":
        warnings.append("the model's narrative was rejected twice, so the narrative was written from the decision record by code: " + "; ".join(first["violations"][:3]))
    if warnings:
        parsed["narrative_warnings"] = warnings            # travels with the result to the auditor, the report and any human reader
    log.info("assembled %s (narrative: %s)", decision["final_classification"], verdict["source"], extra={"decision_id": decision["decision_id"]})
    return {
        "agent_key": agent_key, "agent_name": agent["name"], "agent_version": agent["version"],
        "provider": backend.provider, "model": backend.model,
        "raw_text": raw_text, "parsed": parsed, "parse_error": None if verdict["source"] in ("model", "model_retry") else (first["violations"][0] if first["violations"] else None),
        "decision": decision, "tool_calls": [{"name": c["name"], "by": c.get("by", "model")} for c in calls],
        "narrative_guard": guard, "tool_mode": opts["tool_mode"], "regulations_given": regulation_provenance,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _decision_block(decision: dict[str, Any]) -> str:
    return ("\n\nTOOL RESULT (authoritative decision record; explain it, do not change it)\n"
            + json.dumps(decision, indent=2))


def run_narrative_agent(agent_key: str, results: dict[str, Any], backend: Backend, history: list[dict] | None = None) -> dict[str, Any]:
    """The narrative role: one short model summary, and a report that code assembles from the role results.

    The model is shown a digest (not the report) and writes one paragraph of at most 150 words. One request, no retry: a summary that is
    empty of text, too long, not plain text or ungrounded is replaced by one that code writes, and the report is complete either way.
    A model request that fails raises, so the stage fails visibly and no empty report is written."""
    agent = AGENTS[agent_key]
    log = get_logger(f"agent.{agent_key}", agent["version"])
    shown = report.digest(results)
    messages = [*(history or []), {"role": "user", "content": _user_content(agent, shown)}]
    log.trace("system prompt", payload=agent["system_prompt"])
    raw_text = backend.complete(agent["system_prompt"], messages, json_mode=False)
    log.trace("raw model text", payload=raw_text)
    summary = report.clean_summary(raw_text)
    violations = report.check_summary(summary, shown)
    source = "model" if not violations else "code"
    if violations:
        log.warning("summary rejected, code writes it: %s", "; ".join(violations[:3]))
    text = report.build_report(results, summary if source == "model" else None)
    log.info("assembled the report (summary: %s)", source)
    return {
        "agent_key": agent_key, "agent_name": agent["name"], "agent_version": agent["version"],
        "provider": backend.provider, "model": backend.model,
        "raw_text": text, "parsed": None, "parse_error": None,
        "summary_source": source, "summary_words": len(summary.split()), "summary_violations": violations,
        "model_text": raw_text, "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def run_plain_agent(agent_key: str, loan_data: Any, backend: Backend, history: list[dict] | None = None) -> dict[str, Any]:
    """Run an agent with no deterministic tool (auditor, narrative, not-yet-ported domains)."""
    if agent_key == "narrative" and isinstance(loan_data, dict) and report.has_templates(loan_data):
        return run_narrative_agent(agent_key, loan_data, backend, history)          # results with templates: code assembles the report
    agent = AGENTS[agent_key]
    log = get_logger(f"agent.{agent_key}", agent["version"])
    messages = list(history or [])
    messages.append({"role": "user", "content": _user_content(agent, loan_data)})
    markdown = agent.get("output_format") == "markdown"
    log.trace("system prompt", payload=agent["system_prompt"])
    raw_text = backend.complete(agent["system_prompt"], messages, json_mode=not markdown)
    log.trace("raw model text", payload=raw_text)
    parsed, parse_error = (None, None) if markdown else extract_json(raw_text)
    log.info("completed %s", agent_key)
    return {
        "agent_key": agent_key, "agent_name": agent["name"], "agent_version": agent["version"],
        "provider": backend.provider, "model": backend.model,
        "raw_text": raw_text, "parsed": parsed, "parse_error": parse_error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def run(agent_key: str, loan_data: Any, backend: Backend, history: list[dict] | None = None,
        tool_target: Any | None = None, options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run any agent: tool-backed agents call their MCP tool; others are prompt-only."""
    if agent_key not in AGENTS:
        raise ValueError(f"Unknown agent '{agent_key}'. Valid keys: {list(AGENTS)}")
    if AGENTS[agent_key].get("tool"):
        return run_agent(agent_key, loan_data, backend, history, tool_target, options)
    return run_plain_agent(agent_key, loan_data, backend, history)

"""The standard blocks every tool-backed agent prompt starts with, so the agent "wakes up with the tool in its hand".

Built from the tool name and the case key only (no model involved), inserted right after the prompt's intro line, and
idempotent: running it again replaces the same blocks. The agent-builder writes only the domain body; this module adds
  ## Your Tool   what to do first: call the tool; the record it returns is the answer
  ## Your Role   narrator, not investigator: no independent research, only the tool's record and the regulations given
The pinned regulation text itself is added to the system prompt at run time (agents/runner.py), not stored here.
"""
from __future__ import annotations

import re

HARNESS_SECTIONS = ("Your Tool", "Your Role", "Your Output", "How You Work", "What You Add", "Evidence and identifiers (strict)", "Output Contract")


def tool_block(tool: str, case_key: str | None) -> str:
    argument = (f"Call it with the `{case_key}` object from the user message as its `case` argument." if case_key
                else "Call it with the audit input found in the user message (the other agents' results and the loan data) as its `case` argument.")
    return f'''## Your Tool
You start this job with one tool already in your hand: `{tool}`. It is the deterministic evaluator for your domain.
Your first action, before you write anything else, is to call `{tool}`. {argument}
(The system re-supplies the exact input, so a faithful copy is all that is needed; any difference is discarded and logged.)
The tool returns a decision record. That record IS the determination: the classification, every rule outcome, the missing
facts and the provenance. You cannot do this job without calling the tool, and nothing you write can change what it returns.

'''


def role_block(tool: str) -> str:
    return f'''## Your Role
You are a narrator, not an investigator. Your job is to turn two things into a clear, examiner-ready narrative:
1. the decision record returned by `{tool}`, and
2. the regulation text given to you under "Regulations As Given" (when your domain has any).
You do no independent research. You use no remembered law, guidance, case law or other source. You do not re-decide, re-compute
or second-guess the tool. If the record and the regulation text do not cover something, say so plainly instead of filling the gap.
If the tool returns Unable To Determine or Review Required, your job is to explain exactly what is missing or what a reviewer must judge.

'''


def output_block() -> str:
    return '''## Your Output
You write three things, and only these, as the JSON object in the Output Contract:
- reasoning: walk the decision record in order. For each rule that was not satisfied or could not be completed, say what the rule
  found, in the record's own words and figures, and cite its rule id in parentheses. Say briefly what was satisfied or did not apply.
- examiner_narrative: a short, plain-language statement an examiner can read on its own: the classification and result exactly as the
  record gives them, the decisive findings, and what remains open.
- data_gaps_followups: one entry per missing fact in the record, naming the field and what is needed.
Everything else (evidence lists, data-quality scores, the rule trace, provenance) is produced by code; do not write it.

'''


def _split(text: str) -> tuple[str, str, list[tuple[str, str]]]:
    """(header line, intro, [(section title, section text including its heading)])."""
    header, _, rest = text.partition("\n")
    parts = re.split(r"(?m)^(?=## )", rest.lstrip("\n"))
    intro, sections = parts[0], []
    for part in parts[1:]:
        title = part.split("\n", 1)[0][3:].strip()
        sections.append((title, part))
    return header, intro, sections


def inject_tool_blocks(text: str, tool: str, case_key: str | None) -> str:
    """Return `text` with the standard blocks (re)inserted after the intro and the old How-You-Work steps removed."""
    header, intro, sections = _split(text)
    kept = [body for title, body in sections if title not in HARNESS_SECTIONS]
    from pathlib import Path
    contract = (Path(__file__).resolve().parent / "narrative_contract.md").read_text(encoding="utf-8").rstrip("\n") + "\n"
    kept = [re.sub(r"(?m)^- List evidence as present.*(?:\n  .*)*\n", "", body) for body in kept]
    return (header + "\n\n" + intro.strip() + "\n\n" + tool_block(tool, case_key) + role_block(tool) + output_block() + "".join(
        body if body.endswith("\n\n") else body.rstrip("\n") + "\n\n" for body in kept) + contract)

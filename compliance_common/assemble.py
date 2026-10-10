"""Assemble the final agent result: a code-owned decision plus a verified narrative.

The decision record (from the MCP tool) is the only source for classification, status, thresholds, trace, evidence,
data-quality and change blocks, and provenance. The model contributes prose only (reasoning, examiner narrative, follow-ups),
and that prose is verified by compliance_common.narrative before it is used. Any decision field a model emits is stripped and
reported in `narrative_guard`.
"""
from __future__ import annotations

import re
from typing import Any

# Top-level keys a narrative-only agent must not author.
DECISION_OWNED = (
    "authority", "determination_status", "domain_determination", "determination_trace",
    "threshold_evaluation", "eligibility_trace",
)
_CONFIDENCE = {"Determined": "High", "Review Required": "Moderate", "Unable To Determine": "Low"}
_NARRATIVE_FIELDS = ("reasoning", "examiner_narrative", "status_change_narrative", "data_gaps_followups")


def narrative_guard(model_output: dict[str, Any] | None, decision: dict[str, Any]) -> dict[str, Any]:
    """Report which decision-owned fields the model tried to author."""
    model_output = model_output if isinstance(model_output, dict) else {}
    stripped = [key for key in DECISION_OWNED if key in model_output]
    domain = model_output.get("domain_determination")
    proposed = domain.get("classification") if isinstance(domain, dict) else None
    contradicted = proposed is not None and proposed != decision["final_classification"]
    return {
        "passed": not contradicted,
        "stripped_fields": stripped,
        "model_proposed_classification": proposed,
        "authoritative_classification": decision["final_classification"],
        "decision_id": decision["decision_id"],
    }


_NEGATIVE = re.compile(r"non-?\s?compliant|violat|deficien|not satisfied|\bfails?\b|failure|not met\b", re.I)
_POSITIVE = re.compile(r"(?<!non-)(?<!non )(?<!not )\b(?:fully\s+)?compliant\b|\bcomplies with all\b|\bmeets? (?:all|every)\b|"
                       r"\bsatisf(?:ies|ied) (?:all|each|every)\b|\bsatisf(?:ies|ied) the (?:statutory|regulatory) requirements of (?:each|all|every)\b|\bno deficiencies\b", re.I)


def contradicts_result(compliance_result: str, text: str) -> str | None:
    """A heuristic watchdog (the decision record, not the prose, is authoritative): does the narrative claim the opposite of the
    code-decided compliance result? (Not Applicable is never contradicted by negative words: "fails to exceed the spread" is normal there.) Returns a short note, or None."""
    if compliance_result == "Compliant" and _NEGATIVE.search(text) and not _POSITIVE.search(text):
        return "the narrative describes violations or deficiencies, but the decision record's result is " + compliance_result
    if compliance_result == "Non-Compliant" and _POSITIVE.search(text):
        return "the narrative claims compliance, but the decision record's result is Non-Compliant"
    return None


def assemble(agent: dict[str, Any], decision: dict[str, Any], model_output: dict[str, Any] | None,
             extras: dict[str, Any] | None = None, case: dict[str, Any] | None = None, narrative_source: str = "model") -> dict[str, Any]:
    """Build the result object downstream consumers (auditor, narrative) expect.

    `model_output["narrative"]` is the narrative that survived verification (or the deterministic fallback); `narrative_source` says which.
    Evidence, data-quality and change blocks are derived from the record and the case, never taken from the model."""
    from .narrative import derived_assessments        # local import: narrative.py imports contradicts_result from this module
    model_output = model_output if isinstance(model_output, dict) else {}
    narrative = model_output.get("narrative") if isinstance(model_output.get("narrative"), dict) else {}
    rule_pack = decision.get("rule_pack") or {}
    evaluator = decision.get("evaluator") or {}
    sources = rule_pack.get("source_sha256") or {}
    result: dict[str, Any] = {
        "agent_metadata": {
            "agent_name": agent["name"],
            "agent_version": agent["version"],
            "compliance_track": agent["compliance_track"],
            "evaluation_timestamp": decision.get("evaluation_timestamp", ""),
            "decision_id": decision["decision_id"],
            "evaluator": f"{evaluator.get('name', '')} {evaluator.get('version', '')}".strip(),
            "rule_pack": f"{rule_pack.get('id', '')} {rule_pack.get('version', '')}".strip(),
        },
        "authority": {"primary_authorities": sorted(sources), "regulatory_version": rule_pack.get("version", "")},
        "determination_status": {
            "result": decision["compliance_result"],
            "confidence": _CONFIDENCE.get(decision["determination_status"], "Low"),
        },
        "domain_determination": {
            "classification": decision["final_classification"],
            "applicable_obligations": decision.get("applicable_obligations", []),
            "classification_basis": (
                f"Deterministic evaluation {evaluator.get('name', '')} v{evaluator.get('version', '')}, "
                f"rule pack {rule_pack.get('id', '')} v{rule_pack.get('version', '')}, decision {decision['decision_id']}"
            ),
        },
        **derived_assessments(decision, case),
        "determination_trace": [
            {"step": r["rule_id"], "finding": f"{r['outcome']}: {r['message']}", "basis": r["basis"]}
            for r in decision.get("rule_results", [])
        ],
        "compliance_determination_summary": {key: narrative.get(key, [] if key == "data_gaps_followups" else "")
                                             for key in _NARRATIVE_FIELDS},
        "missing_facts": decision.get("missing_facts", []),
        "narrative_source": narrative_source,
    }
    if extras:
        result.update(extras)
    if agent.get("key") == "auditor":                    # the auditor's contract names its narrative block differently
        result["audit_determination_summary"] = result["compliance_determination_summary"]
    return result

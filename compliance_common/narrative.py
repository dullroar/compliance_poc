"""Everything about a narrative that code can own, so the model owns only phrasing.

* `deterministic_narrative`  a complete narrative written from the decision record alone (the fallback, and ground truth);
* `derived_assessments`      the evidence / data-quality / change blocks, derived from the record and the case, never the model;
* `check_narrative`          verifies a model narrative adds no fact the record, the case or the regulation text lacks, does not
                              contradict the code-decided result, and is not empty. Violations drive one retry, then the fallback.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from .assemble import contradicts_result

MIN_NARRATIVE_CHARS = 120
_BAD = ("not_satisfied", "unable_to_determine", "review_required", "not_eligible")
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_NUMBER = re.compile(r"\d[\d,]*\.?\d*")
_ID = re.compile(r"\b[A-Za-z]+(?:-[A-Za-z0-9]+)+\b")

# What each evaluator deliberately does NOT decide. Code-owned (it used to be an open-ended prompt list that invited the model to
# opine from outside knowledge); the narrative states it as a plain limit of the review.
SCOPE_NOTES: dict[str, str] = {
    "hmda": "This review does not check the Filing Instructions Guide code lists or file format, the correctness of the context flags supplied, "
            "quarterly recording or annual submission timing, preapproval requests, purchased loans, assumptions, or construction-to-permanent loans.",
    "ecoa": "This review does not decide whether discrimination occurred, whether stated reasons match the true reasons, policy exceptions or overrides, "
            "or statistical patterns; monitoring-information collection under 12 CFR 1002.13 is reviewed separately under VMI.",
    "vmi": "This review does not check the form wording against Appendix B to part 1003, co-applicants beyond the first, or system conversions and data migrations.",
    "fzd": "This review does not make a flood-zone determination, and does not assess map revisions (LOMA/LOMR), multiple structures or parcels, or life-of-loan tracking systems.",
    "hvcre": "This review does not validate any appraisal, assign regulatory capital or a risk rating, or apply the Appendix A loan-to-value limit unless one is supplied.",
    "hpml": "This review does not decide ability-to-repay, the timing or content of disclosures, or HOEPA high-cost status.",
    "trid": "This review does not decide the timing of revised Loan Estimates, the accuracy of form contents, or the settlement service provider list.",
    "ybs": "This review applies the institution's pilot policy for the thresholds and the entity-attribution method; 12 CFR 614.4165 requires the program but does not supply those values.",
    "auditor": "This audit applies explicit consistency checks across the regimes' inputs and results; it does not re-decide any single regime.",
}


def _bad_rules(decision: dict[str, Any]) -> list[dict[str, Any]]:
    return [r for r in decision.get("rule_results", []) if r.get("outcome") in _BAD]


def deterministic_narrative(decision: dict[str, Any], domain: str) -> dict[str, Any]:
    """A complete, accurate narrative assembled from the decision record only (no model)."""
    cls, result, status = decision["final_classification"], decision["compliance_result"], decision["determination_status"]
    rules, bad = decision.get("rule_results", []), _bad_rules(decision)
    fine = [r for r in rules if r.get("outcome") not in _BAD]
    lines = [f"The deterministic review ({decision['evaluator']['name']} {decision['evaluator']['version']}) classified this case as '{cls}' "
             f"with the result '{result}' (determination status: {status})."]
    if bad:
        lines.append("These rules were not satisfied or could not be completed: " + " ".join(f"{r['rule_id']}: {r['message']}" for r in bad))
    if fine:
        lines.append(f"{len(fine)} other rule(s) were satisfied or did not apply: " + ", ".join(r["rule_id"] for r in fine) + ".")
    reasoning = " ".join(lines)
    examiner = " ".join([lines[0]] + ([f"The following need follow-up: {', '.join(r['rule_id'] for r in bad)}."] if bad else ["No rule is outstanding."]) + [SCOPE_NOTES.get(domain, "")]).strip()
    followups = [f"Obtain {m['field']}: {m['reason']}" for m in decision.get("missing_facts", [])]
    return {"reasoning": reasoning, "examiner_narrative": examiner, "status_change_narrative": "", "data_gaps_followups": followups}


def derived_assessments(decision: dict[str, Any], case: dict[str, Any] | None) -> dict[str, Any]:
    """Evidence, data-quality and change blocks, derived from the record and the case (the model no longer writes these)."""
    missing = decision.get("missing_facts", [])
    documents = [f"{e.get('type', 'document')} ({e.get('id', '')})" for e in (case or {}).get("evidence", []) if isinstance(e, dict)]
    determined = decision["determination_status"] == "Determined"
    rating = "Insufficient" if decision["determination_status"] == "Unable To Determine" else ("Sufficient" if determined and not missing else "Partially Sufficient")
    issues = [f"{m['field']}: {m['reason']}" for m in missing] + [f"{e['field']}: {e['reason']}" for e in decision.get("validation_errors", [])]
    return {
        "evidence_assessment": {"rating": rating, "primary_evidence_present": documents, "primary_evidence_missing": [m["field"] for m in missing],
                                "secondary_evidence_present": [], "secondary_evidence_missing": []},
        "data_quality": {"completeness": "High" if not missing else ("Moderate" if len(missing) <= 3 else "Low"), "issues": issues},
        "change_assessment": {"status_changed": False, "prior_status": None, "triggering_evidence": None},
    }


def _normal(token: str) -> str | None:
    try:
        return format(Decimal(token.replace(",", "").rstrip(".")).normalize(), "f")
    except InvalidOperation:
        return None


def allowed_numbers(*sources: str) -> set[str]:
    found: set[str] = set()
    for text in sources:
        for token in _NUMBER.findall(text):
            n = _normal(token)
            if n is not None:
                found.add(n)
    return found


def check_narrative(narrative: dict[str, Any] | None, decision: dict[str, Any], case: Any, regulations: str) -> list[str]:
    """Violations in a model narrative (empty list = acceptable). The decision record, the case and the regulation text are the
    only sources of fact; the narrative may restate them, never extend them."""
    if not isinstance(narrative, dict):
        return ["the reply did not contain the required narrative object"]
    parts = [str(narrative.get(k, "")) for k in ("reasoning", "examiner_narrative", "status_change_narrative")]
    parts += [str(x) for x in narrative.get("data_gaps_followups") or []]
    text = "\n".join(p for p in parts if p)
    if len(text.strip()) < MIN_NARRATIVE_CHARS:
        return ["the narrative is empty or too short to explain the decision record"]
    source = json.dumps(decision, default=str) + json.dumps(case, default=str) + regulations
    violations = []
    known = allowed_numbers(source)
    for token in dict.fromkeys(_NUMBER.findall(text)):
        n = _normal(token)
        if n is not None and (len(n.replace(".", "").replace("-", "")) > 1 or "." in token) and n not in known:
            violations.append(f"the number '{token.rstrip('.')}' does not appear in the decision record, the case, or the regulation text")
    source_lower = source.lower()
    for date in dict.fromkeys(_DATE.findall(text)):
        if date not in source:
            violations.append(f"the date '{date}' does not appear in the decision record or the case")
    for ident in dict.fromkeys(_ID.findall(text)):
        if any(c.isdigit() for c in ident) and ident.lower() not in source_lower:
            violations.append(f"the identifier '{ident}' does not appear in the decision record or the case")
    note = contradicts_result(decision.get("compliance_result", ""), text)
    if note:
        violations.append(note)
    return violations


def retry_message(violations: list[str]) -> str:
    return ("Your narrative cannot be accepted:\n" + "\n".join(f"- {v}" for v in violations[:8]) +
            "\n\nRewrite it. Use ONLY facts, numbers, dates and names that appear in the decision record (the tool result) or the regulation text. "
            "Do not add, infer, compute or round anything. State the classification and result exactly as the record gives them. "
            "If something is not in the record, leave it out. Reply with the same JSON object.")

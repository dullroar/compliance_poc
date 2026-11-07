"""The examiner finding: one paragraph per failing rule, in a fixed order, under a per-regime word limit. Written by code from the record.

Order (audit convention, mapped to the record): Requirement (the rule and its citation), Condition (what the record shows, in its own
words and figures), Basis (why this outcome), Effect (the classification and result the record states), Action (what closes it).
Every number and date comes from the record or the catalog entry. A paragraph over its limit is never cut: the compact form drops the
requirement sentence and keeps the rule id and citation; if that still does not fit, `LimitError` says so and the caller escalates.
"""
from __future__ import annotations

import re
from typing import Any

from .catalog import _regex, resolve_field, resolve_rule

FLOOR = 25
# Words per paragraph, set per regime from the number of facts a finding must carry and the density of the regime (spec R4).
LIMITS: dict[str, int] = {"ybs": 70, "vmi": 100, "hpml": 90, "fzd": 90, "hvcre": 90, "ecoa": 100, "trid": 100, "auditor": 110, "hmda": 130}
FINDING_OUTCOMES = ("not_satisfied", "unable_to_determine", "review_required")
OUTCOME_WORDS = {"not_satisfied": "not satisfied", "unable_to_determine": "unable to determine", "review_required": "review required"}
BASIS = {
    "not_satisfied": "Not satisfied: the facts break the rule.",
    "unable_to_determine": "Unable to determine: a fact is absent or conflicts.",
    "review_required": "Review required: a reviewer must judge.",
}
MAX_FACTS = 3
OUTCOME_ORDER = ("not_satisfied", "unable_to_determine", "review_required")
# Above this many findings in one HMDA result, the LAR item findings are grouped by LAR section (decided by Jim, 2026-11-07).
GROUP_THRESHOLD = 20
_LAR_ITEM = re.compile(r"^HMDA-LAR-(\d\d)$")


def _section(id_: str, title: str, items: list[int], requirement: str, action: str, who: str) -> dict[str, Any]:
    cite = f"12 CFR 1003.4(a)({items[0]})" + "".join(f", ({n})" for n in items[1:])
    return {"id": id_, "rule_id": f"HMDA-LAR-SECTION-{id_.upper()}", "title": title, "items": items, "cite": cite,
            "requirement": requirement, "action": action, "who": who}


# The partition of the 38 numbered items of 1003.4(a) into sections is an executor draft: the regulation lists the items flat.
# Compliance should review it (spec, step 03). It affects only how findings are grouped above the threshold.
LAR_SECTIONS: list[dict[str, Any]] = [
    _section("identity", "Loan identity and action", [1, 8, 33, 34], "The register must identify the loan and the action taken on it.",
             "Record the identifier, the action and its date, the application channel and the NMLS identifier.", "loan operations"),
    _section("terms", "Loan type, purpose and features", [2, 3, 4, 5, 6, 7, 11, 13, 14, 25, 26, 27, 36, 37, 38],
             "The register must describe the loan type, purpose, amount, lien, term and features.",
             "Record each listed item from the loan file, or correct the value that was reported.", "loan operations"),
    _section("property", "Property", [9, 28, 29, 30, 31, 32], "The register must describe the property, its location, value and units.",
             "Record each listed property item from the file, or correct the value that was reported.", "loan officer"),
    _section("applicant", "Applicant and credit decision", [10, 15, 16, 23, 24, 35],
             "The register must report the applicant data, credit score, ratios, underwriting result and denial reasons.",
             "Record each listed item from the file, or correct the value that was reported.", "credit analyst"),
    _section("pricing", "Pricing and costs", [12, 17, 18, 19, 20, 21, 22], "The register must report the rate spread, costs, points, credits, rate and penalty.",
             "Record each listed pricing item from the loan file, or correct the value that was reported.", "closing staff"),
]


class LimitError(ValueError):
    """A finding cannot be written within its regime's word limit without dropping a required element."""


def findings(decision: dict[str, Any]) -> list[dict[str, Any]]:
    """The failing rule results, each with its subject id where the record has subjects (the top-level list does not carry it)."""
    subjects = decision.get("subject_results") or []
    if subjects:
        return [{**r, "subject_id": s["subject_id"]} for s in subjects for r in s.get("rule_results", []) if r["outcome"] in FINDING_OUTCOMES]
    return [{**r, "subject_id": r.get("subject_id")} for r in decision.get("rule_results", []) if r["outcome"] in FINDING_OUTCOMES]


def _condition(finding: dict[str, Any], decision: dict[str, Any], domain: str) -> str:
    text = finding["message"].strip().rstrip(".")
    if "value" in finding and "threshold" in finding and str(finding["value"]) not in text:
        text += f"; the record shows {finding['value']} against {finding['threshold']}"
    labels: list[str] = []
    for fact in decision.get("missing_facts", []):
        if fact.get("subject_id") not in (None, finding.get("subject_id")):
            continue
        entry = resolve_field(domain, fact["field"])
        label = entry.text(entry.label)
        if entry.rule and _regex(entry.rule).match(finding["rule_id"]) and label not in labels and label.lower() not in text.lower():
            labels.append(label)
    if labels:
        text += "; missing: " + ", ".join(labels[:MAX_FACTS]) + (" and others" if len(labels) > MAX_FACTS else "")
    return text


def _effect(decision: dict[str, Any]) -> str:
    classification, result = decision["final_classification"], decision["compliance_result"]
    return f"classification and result {result}" if classification == result else f"classification {classification}, result {result}"


def _paragraph(finding: dict[str, Any], decision: dict[str, Any], domain: str, full: bool) -> str:
    entry = resolve_rule(finding["rule_id"])
    subject = f" (subject {finding['subject_id']})" if finding.get("subject_id") else ""
    requirement = f"{finding['rule_id']}{subject}, {entry.cite}" + (f": {entry.text(entry.requirement).rstrip('.')}" if full else "")
    return (f"Requirement: {requirement}. Condition: {_condition(finding, decision, domain)}. Basis: {BASIS[finding['outcome']]} "
            f"Effect: {_effect(decision)}. "
            f"Action: {entry.text(entry.action).rstrip('.')}.")


def _grouped_paragraph(section: dict[str, Any], members: list[dict[str, Any]], decision: dict[str, Any], domain: str) -> str:
    ids = {outcome: [m["rule_id"] for m in members if m["outcome"] == outcome] for outcome in OUTCOME_ORDER}
    parts = [f"{OUTCOME_WORDS[outcome]}: {', '.join(found)}" for outcome, found in ids.items() if found]
    labels: list[str] = []
    for fact in decision.get("missing_facts", []):
        entry = resolve_field(domain, fact["field"])
        label = entry.text(entry.label)
        if entry.rule and any(_regex(entry.rule).match(m["rule_id"]) for m in members) and label not in labels:
            labels.append(label)
    if labels:
        parts.append("missing: " + ", ".join(labels[:MAX_FACTS]) + (" and others" if len(labels) > MAX_FACTS else ""))
    numbers = [int(_LAR_ITEM.match(m["rule_id"]).group(1)) for m in members]
    cite = f"12 CFR 1003.4(a)({numbers[0]})" + "".join(f", ({n})" for n in numbers[1:])        # only the items that fail
    return (f"Requirement: {section['rule_id']}, {cite}: {section['requirement'].rstrip('.')}. Condition: {'; '.join(parts)}. "
            f"Basis: Item by item, values break the rules or a fact is absent or conflicts. Effect: {_effect(decision)}. "
            f"Action: {section['action'].rstrip('.')}.")


def render(decision: dict[str, Any], domain: str, strict: bool = True) -> list[dict[str, Any]]:
    """One paragraph per finding: {rule_id, rule_ids, subject_id, finding, findings, grouped, text, words, form}. Raises LimitError if a finding cannot fit.

    Above GROUP_THRESHOLD findings in one HMDA result, the LAR item findings of one section become one grouped paragraph per section
    that has two or more failing items (every finding still appears once); other findings keep their own paragraph.

    With strict=False a paragraph that fits no form is still returned (compact form, `over_limit` true) instead of raising, so the runtime
    never drops a finding; the caller reports it."""
    found = findings(decision)
    members: dict[str, list[dict[str, Any]]] = {}
    if domain == "hmda" and len(found) > GROUP_THRESHOLD:
        for finding in found:
            item = _LAR_ITEM.match(finding["rule_id"])
            if item:
                section = next(sec for sec in LAR_SECTIONS if int(item.group(1)) in sec["items"])
                members.setdefault(section["id"], []).append(finding)
    limit, out, done = LIMITS[domain], [], set()
    for finding in found:
        item = _LAR_ITEM.match(finding["rule_id"])
        section = next((sec for sec in LAR_SECTIONS if item and int(item.group(1)) in sec["items"]), None) if members else None
        group = members.get(section["id"], []) if section else []
        if len(group) > 1:
            if section["id"] in done:
                continue
            done.add(section["id"])
            text = _grouped_paragraph(section, group, decision, domain)
            count = len(text.split())
            if count > limit and strict:
                raise LimitError(f"{section['rule_id']} needs {count} words; the {domain} limit is {limit}")
            out.append({"rule_id": section["rule_id"], "rule_ids": [m["rule_id"] for m in group], "subject_id": None, "finding": None, "findings": group,
                        "grouped": True, "section": section["id"], "text": text, "words": count, "form": "full", "over_limit": count > limit})
            continue
        for form in ("full", "compact"):
            text = _paragraph(finding, decision, domain, form == "full")
            count = len(text.split())
            if count <= limit:
                break
        else:
            if strict:
                raise LimitError(f"{finding['rule_id']} needs {count} words in the compact form; the {domain} limit is {limit}")
        if count < FLOOR and strict:
            raise LimitError(f"{finding['rule_id']} has {count} words, under the floor of {FLOOR}")
        out.append({"rule_id": finding["rule_id"], "rule_ids": [finding["rule_id"]], "subject_id": finding.get("subject_id"), "finding": finding,
                    "findings": [finding], "grouped": False, "text": text, "words": count, "form": form, "over_limit": count > limit})
    return out


def drafts(decision: dict[str, Any], domain: str) -> list[dict[str, Any]]:
    """What a model is shown to rephrase: the code-written paragraph for each finding, with its word limit."""
    return [{"rule_id": p["rule_id"], "draft": p["text"], "word_limit": LIMITS[domain]} for p in render(decision, domain, strict=False)]


def catalog_text(paragraph: dict[str, Any]) -> str:
    """The catalog and section wording a paragraph may quote (its citations, requirement and action), as one source string."""
    if paragraph["grouped"]:
        section = next(sec for sec in LAR_SECTIONS if sec["id"] == paragraph["section"])
        return " ".join([section["cite"], section["requirement"], section["action"]])
    entry = resolve_rule(paragraph["rule_id"])
    return " ".join([entry.cite, entry.text(entry.requirement), entry.text(entry.action)])


_LABELS = ("Requirement", "Condition", "Basis", "Effect", "Action")


def check_paragraph(text: Any, expected: dict[str, Any], decision: dict[str, Any], domain: str) -> list[str]:
    """Structural violations in a model-phrased paragraph (empty list = acceptable). `expected` is the code paragraph for the same finding.

    Grounding (numbers, dates, identifiers) and contradiction are checked by compliance_common.narrative.check_paragraphs, which calls this."""
    if not isinstance(text, str) or not text.strip():
        return ["the paragraph is empty"]
    out: list[str] = []
    positions = [text.find(label + ":") for label in _LABELS]
    if -1 in positions or positions != sorted(positions) or any(text.count(label + ":") != 1 for label in _LABELS):
        out.append("the paragraph must have the parts Requirement:, Condition:, Basis:, Effect: and Action: once each, in that order")
    for rule_id in [expected["rule_id"], *expected["rule_ids"]]:
        if rule_id not in text:
            out.append(f"the paragraph must name {rule_id}")
    if not expected["grouped"]:
        entry = resolve_rule(expected["rule_id"])
        if entry.cite not in text:
            out.append(f"the paragraph must cite {entry.cite}")
        message = expected["finding"]["message"].strip().rstrip(".")
        if message not in text:
            out.append("the Condition must quote the record's own words for this rule")
    lowered = text.lower()
    for outcome in {f["outcome"] for f in expected["findings"]}:
        if OUTCOME_WORDS[outcome] not in lowered:
            out.append(f"the paragraph must state the outcome '{OUTCOME_WORDS[outcome]}'")
    if decision["compliance_result"] not in text:
        out.append(f"the paragraph must state the result {decision['compliance_result']}")
    action = text.partition("Action:")[2].strip()
    if len(action.split()) < 3:
        out.append("the Action must say what closes the finding")
    count = len(text.split())
    if count < FLOOR:
        out.append(f"the paragraph has {count} words; the floor is {FLOOR}")
    if count > LIMITS[domain]:
        out.append(f"the paragraph has {count} words; the limit is {LIMITS[domain]}")
    return out

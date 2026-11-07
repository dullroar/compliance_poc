"""The loan-officer sheet: what the customer's file still needs, and what to refer to compliance. Written by code from the record.

`render(decision)` reads only the decision record and the catalog. It never asks the customer for something the institution did
or decided: a field is a customer request only when its catalog entry says `customer` and the rule it belongs to is an
information gap or a value rule (kind G or V). Findings of kind P (a fact about what the institution did) and R (reviewer judgment)
go to the referral list, whatever the field is called, so `ECOA-MARITAL-INQUIRY` can never become "obtain marital status".
"""
from __future__ import annotations

from typing import Any

from .catalog import FieldEntry, RuleEntry, _regex, resolve_field, resolve_rule

FINDING_OUTCOMES = ("not_satisfied", "unable_to_determine", "review_required")
CUSTOMER_KINDS = ("G", "V")
# A roll-up repeats findings that are listed one by one, so it adds nothing to the sheet.
ROLLUPS = ("HMDA-LAR-ITEMS",)
REFER_TITLE = "Refer to compliance, not a customer request"
CUSTOMER_TITLE = "Needed from the customer"


def _domain(decision: dict[str, Any]) -> str:
    return str((decision.get("evaluator") or {}).get("name", ""))


def _findings(decision: dict[str, Any]) -> list[dict[str, Any]]:
    return [r for r in decision.get("rule_results", []) if r.get("outcome") in FINDING_OUTCOMES and r.get("rule_id") not in ROLLUPS]


def _rule_ids_for(entry: FieldEntry, findings: list[dict[str, Any]]) -> list[str]:
    """The failing rule ids this missing fact belongs to (a glob in `entry.rule` names a family)."""
    matcher = _regex(entry.rule) if entry.rule else None
    return [f["rule_id"] for f in findings if matcher and matcher.match(f["rule_id"])]


def _route(entry: FieldEntry, rule_ids: list[str]) -> str:
    """Route by the rule and its kind, not by the field name."""
    if entry.route != "customer":
        return "refer"
    kinds = {resolve_rule(rule_id).kind for rule_id in rule_ids} or {resolve_rule(entry.rule.replace("*", "X")).kind if entry.rule else "R"}
    return "customer" if kinds <= set(CUSTOMER_KINDS) else "refer"


def _who(rule_ids: list[str], entry: FieldEntry) -> str:
    if rule_ids:
        return resolve_rule(rule_ids[0]).who
    return resolve_rule(entry.rule.replace("*", "X")).who if entry.rule else "compliance reviewer"


def render(decision: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """{needed_from_customer: [...], refer_to_compliance: [...]}; every missing fact appears once, in exactly one list."""
    domain = _domain(decision)
    findings = _findings(decision)
    customer: list[dict[str, Any]] = []
    refer: list[dict[str, Any]] = []
    seen: set[tuple[Any, str]] = set()
    explained: set[str] = set()
    for fact in decision.get("missing_facts", []):
        key = (fact.get("subject_id"), fact["field"])
        if key in seen:
            continue
        seen.add(key)
        entry = resolve_field(domain, fact["field"])
        rule_ids = _rule_ids_for(entry, findings)
        explained.update(rule_ids)
        item = {"subject_id": fact.get("subject_id"), "field": fact["field"], "label": entry.text(entry.label), "text": entry.text(entry.why),
                "decline": entry.decline, "rule_ids": rule_ids}
        if _route(entry, rule_ids) == "customer":
            customer.append(item)
        else:
            refer.append({**item, "decline": False, "who": _who(rule_ids, entry)})
    for finding in findings:                                   # failures that no missing fact explains (a value or timing violation, a judgment, a record fact)
        if finding["rule_id"] in explained:
            continue
        entry: RuleEntry = resolve_rule(finding["rule_id"])
        refer.append({"subject_id": finding.get("subject_id"), "field": None, "label": entry.cite,
                      "text": entry.text(entry.refer), "decline": False, "rule_ids": [finding["rule_id"]], "who": entry.who})
    return {"needed_from_customer": _by_subject(customer), "refer_to_compliance": _by_subject(refer)}


def _by_subject(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order: dict[Any, int] = {}
    for item in items:
        order.setdefault(item["subject_id"], len(order))
    return sorted(items, key=lambda item: order[item["subject_id"]])         # stable: subjects grouped, catalog order kept within one

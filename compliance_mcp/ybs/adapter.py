"""Maps a loan payload to the YBS tool call and a decision record to report extras."""
from __future__ import annotations

from typing import Any

from compliance_common.decision import unavailable_record

from .rules import EVALUATOR_VERSION

TOOL = "ybs_evaluate"
_CATEGORIES = ("young", "beginning", "small")


def tool_arguments(loan_data: Any) -> tuple[dict[str, Any] | None, str]:
    """Return ({"case": ...}, "") or (None, reason) when no canonical case exists."""
    if not isinstance(loan_data, dict):
        return None, "Narrative input cannot produce a final deterministic YBS determination; provide ybs_case."
    case = loan_data.get("ybs_case")
    if not isinstance(case, dict):
        return None, "Canonical ybs_case is required for a final deterministic YBS determination."
    return {"case": case}, ""


def unavailable(reason: str, loan_data: Any) -> dict[str, Any]:
    return unavailable_record("ybs", EVALUATOR_VERSION, "ybs_case", reason, loan_data)


def extras(decision: dict[str, Any]) -> dict[str, Any]:
    """YBS-specific report objects, derived from the decision record only."""
    record = decision.get("threshold_record") or {}
    threshold_evaluation = {
        "authority_source": "Institution YBS pilot policy (12 CFR 614.4165 requires the program, not these values)",
        "authority_version": (decision.get("rule_pack") or {}).get("version", ""),
        "evaluation_date": decision.get("evaluation_date", ""),
        "threshold_record_id": record.get("id", ""),
        "threshold_record_effective_date": record.get("effective_start", ""),
        "young_age_limit": record.get("young_age_limit", ""),
        "beginning_years_limit": record.get("beginning_years_limit", ""),
        "small_farmer_sales_limit": record.get("small_farmer_sales_limit", ""),
        "authority_reference": record.get("authority_reference", ""),
    }
    subjects = []
    for result in decision.get("subject_results", []):
        entry: dict[str, Any] = {"subject_id": result["subject_id"], "subject_type": result["subject_type"],
                                 "classification": result["classification"]}
        for category in _CATEGORIES:
            rule = next((r for r in result["rule_results"] if category.upper() in r["rule_id"]), None)
            entry[f"{category}_analysis"] = {
                "threshold": rule.get("threshold", "") if rule else "",
                "borrower_value": rule.get("value", "") if rule else "",
                "result": result["categories"].get(category, ""),
            }
        subjects.append(entry)
    return {"threshold_evaluation": threshold_evaluation, "eligibility_trace": {"subjects": subjects}}

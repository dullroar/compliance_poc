"""Maps a loan payload to the HPML tool call and a decision record to report extras."""
from __future__ import annotations

from typing import Any

from compliance_common.decision import unavailable_record

from .rules import EVALUATOR_VERSION

TOOL = "hpml_evaluate"


def tool_arguments(loan_data: Any) -> tuple[dict[str, Any] | None, str]:
    if not isinstance(loan_data, dict):
        return None, "Narrative input cannot produce a final deterministic HPML determination; provide hpml_case."
    case = loan_data.get("hpml_case")
    if not isinstance(case, dict):
        return None, "Canonical hpml_case is required for a final deterministic HPML determination."
    return {"case": case}, ""


def unavailable(reason: str, loan_data: Any) -> dict[str, Any]:
    return unavailable_record("hpml", EVALUATOR_VERSION, "hpml_case", reason, loan_data)


def extras(decision: dict[str, Any]) -> dict[str, Any]:
    return {"hpml_evaluation": decision.get("hpml_evaluation", {})}

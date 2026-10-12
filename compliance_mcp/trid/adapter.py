"""Maps a loan payload to the TRID tool call and a decision record to report extras."""
from __future__ import annotations

from typing import Any

from compliance_common.decision import unavailable_record

from .rules import EVALUATOR_VERSION

TOOL = "trid_evaluate"


def tool_arguments(loan_data: Any) -> tuple[dict[str, Any] | None, str]:
    if not isinstance(loan_data, dict):
        return None, "Narrative input cannot produce a final deterministic TRID determination; provide trid_case."
    case = loan_data.get("trid_case")
    if not isinstance(case, dict):
        return None, "Canonical trid_case is required for a final deterministic TRID determination."
    return {"case": case}, ""


def unavailable(reason: str, loan_data: Any) -> dict[str, Any]:
    return unavailable_record("trid", EVALUATOR_VERSION, "trid_case", reason, loan_data)


def extras(decision: dict[str, Any]) -> dict[str, Any]:
    return {"trid_evaluation": decision.get("trid_evaluation", {})}

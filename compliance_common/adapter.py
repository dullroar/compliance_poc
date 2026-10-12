"""Generic loan-payload adapter for a domain whose canonical input lives under `<domain>_case`."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from .decision import unavailable_record


def make_adapter(domain: str, version: str, case_key: str | None = None, extras_key: str | None = None) -> SimpleNamespace:
    """Return the four names the runner expects: TOOL, tool_arguments, unavailable, extras."""
    case_key = case_key or f"{domain}_case"
    extras_key = extras_key or f"{domain}_evaluation"
    label = domain.upper()

    def tool_arguments(loan_data: Any) -> tuple[dict[str, Any] | None, str]:
        if not isinstance(loan_data, dict):
            return None, f"Narrative input cannot produce a final deterministic {label} determination; provide {case_key}."
        case = loan_data.get(case_key)
        if not isinstance(case, dict):
            return None, f"Canonical {case_key} is required for a final deterministic {label} determination."
        return {"case": case}, ""

    def unavailable(reason: str, loan_data: Any) -> dict[str, Any]:
        return unavailable_record(domain, version, case_key, reason, loan_data)

    def extras(decision: dict[str, Any]) -> dict[str, Any]:
        return {extras_key: decision.get(extras_key, {})}

    return SimpleNamespace(TOOL=f"{domain}_evaluate", tool_arguments=tool_arguments, unavailable=unavailable, extras=extras)

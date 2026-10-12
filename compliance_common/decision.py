"""Decision-record helpers shared by every deterministic evaluator."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from .pack import EvaluatorValidationError, Pack

# Eligibility-style outcomes (YBS) and obligation-style outcomes (HPML, TRID, ...).
OUTCOMES = {
    "eligible", "not_eligible", "unable_to_determine", "review_required",
    "applies", "does_not_apply", "satisfied", "not_satisfied",
}
BASES = {"regulatory", "institution_policy"}
LLM_INSTRUCTION = (
    "The model may explain this decision record but must not change its classification, "
    "rule outcomes, thresholds, dates, or provenance."
)


def rule(rule_id: str, outcome: str, basis: str, message: str, **extra: Any) -> dict[str, Any]:
    if outcome not in OUTCOMES:
        raise EvaluatorValidationError(f"Invalid outcome {outcome!r}")
    if basis not in BASES:
        raise EvaluatorValidationError(f"Invalid basis {basis!r}")
    return {"rule_id": rule_id, "outcome": outcome, "basis": basis, "message": message, **extra}


def fact(subject: dict[str, Any], field: str, facts_used: list, missing: list) -> Any:
    """Read a required fact, recording it as used, missing, or conflicting."""
    if field in set(subject.get("conflicting_fields", [])):
        missing.append({"subject_id": subject.get("id"), "field": field, "reason": "conflicting evidence requires review"})
        return None
    value = subject.get(field)
    if value is None or value == "":
        missing.append({"subject_id": subject.get("id"), "field": field, "reason": "required fact is absent"})
        return None
    facts_used.append({"subject_id": subject.get("id"), "field": field, "value": value})
    return value


def comparison(value: float, threshold: float, operator: str) -> bool:
    return {"lt": value < threshold, "lte": value <= threshold, "gt": value > threshold, "gte": value >= threshold}[operator]


def base_record(name: str, evaluator_version: str, pack: Pack, case: dict[str, Any], evaluation_date) -> dict[str, Any]:
    return {
        "evaluator": {"name": name, "version": evaluator_version, "network_accessed": False},
        "rule_pack": {
            "id": pack.manifest["id"], "version": pack.manifest["version"], "status": pack.manifest["status"],
            "git_revision": pack.manifest.get("git_revision", "uncommitted"),
            "file_sha256": pack.file_hashes(), "source_sha256": pack.source_hashes(),
        },
        "case_id": case.get("case_id"),
        "evaluation_date": evaluation_date.isoformat(),
        "facts_used": [], "missing_facts": [], "rule_results": [], "subject_results": [],
        "evidence_references": case.get("evidence", []),
    }


COMPLIANCE_RESULTS = {"Compliant", "Non-Compliant", "Potential Issue", "Not Applicable", "Unable To Determine"}


def seal(record: dict[str, Any], *, timestamp: bool = True) -> dict[str, Any]:
    """Compute decision_id over the substantive content (excluding timestamp) and stamp the time."""
    substantive = {k: v for k, v in record.items() if k not in {"evaluation_timestamp", "decision_id"}}
    record["decision_id"] = hashlib.sha256(
        json.dumps(substantive, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()
    if timestamp:
        record["evaluation_timestamp"] = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return record


def finalize(record: dict[str, Any], classification: str, status: str, compliance_result: str,
             *, timestamp: bool = True) -> dict[str, Any]:
    """Set the verdict, llm_contract, decision_id and timestamp on a record.

    `compliance_result` is the code-owned pass/fail-style status shown to readers
    (Compliant, Non-Compliant, Potential Issue, Not Applicable, Unable To Determine).
    """
    if compliance_result not in COMPLIANCE_RESULTS:
        raise EvaluatorValidationError(f"Invalid compliance_result {compliance_result!r}")
    record["final_classification"] = classification
    record["determination_status"] = status
    record["compliance_result"] = compliance_result
    record["llm_contract"] = {"authoritative_classification": classification, "instruction": LLM_INSTRUCTION}
    return seal(record, timestamp=timestamp)


def unavailable_record(name: str, version: str, input_key: str, reason: str, loan_data: Any) -> dict[str, Any]:
    """A safe evaluator-shaped record for when the tool cannot run (never a guess)."""
    case_id = loan_data.get("case_information", {}).get("case_id") if isinstance(loan_data, dict) else None
    return seal({
        "evaluator": {"name": name, "version": version, "network_accessed": False},
        "case_id": case_id,
        "determination_status": "Unable To Determine",
        "final_classification": "Unable To Determine",
        "compliance_result": "Unable To Determine",
        "rule_results": [], "facts_used": [],
        "missing_facts": [{"field": input_key, "reason": reason}],
        "validation_errors": [{"field": input_key, "reason": reason}],
        "llm_contract": {"authoritative_classification": "Unable To Determine", "instruction": LLM_INSTRUCTION},
    })

"""Generate a domain decision-record JSON schema (committed into each pack by the builder)."""
from __future__ import annotations

from typing import Any

from .decision import COMPLIANCE_RESULTS, OUTCOMES

_REQUIRED = [
    "evaluator", "rule_pack", "evaluation_date", "determination_status", "final_classification",
    "compliance_result", "rule_results", "facts_used", "missing_facts", "llm_contract", "decision_id",
]


def decision_record_schema(title: str, classifications: list[str]) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": title,
        "type": "object",
        "required": _REQUIRED,
        "properties": {
            "final_classification": {"enum": classifications},
            "determination_status": {"enum": ["Determined", "Unable To Determine", "Review Required"]},
            "compliance_result": {"enum": sorted(COMPLIANCE_RESULTS)},
            "decision_id": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
            "rule_results": {"type": "array", "items": {
                "type": "object", "required": ["rule_id", "outcome", "basis", "message"],
                "properties": {"rule_id": {"type": "string"}, "outcome": {"enum": sorted(OUTCOMES)},
                               "basis": {"enum": ["regulatory", "institution_policy"]}, "message": {"type": "string"}}}},
            "facts_used": {"type": "array", "items": {"type": "object", "required": ["field", "value"]}},
            "missing_facts": {"type": "array", "items": {"type": "object", "required": ["field", "reason"]}},
            "evaluator": {"type": "object", "required": ["name", "version"]},
            "rule_pack": {"type": "object", "required": ["id", "version", "status"]},
            "llm_contract": {"type": "object", "required": ["authoritative_classification", "instruction"]},
        },
    }

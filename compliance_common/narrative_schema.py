"""The JSON schema of what the model writes for a tool-backed agent (mirrors builders/narrative_contract.md).

The model writes prose only: a narrative, and (when `templates: model`) one examiner paragraph per finding, each rephrasing a draft that
code wrote from the decision record (`NARRATIVE_SCHEMA`). With `templates: code` the model is not asked for paragraphs and the reply is
constrained to `NARRATIVE_SCHEMA_CODE`. Everything else in a result (classification, status, rule trace, evidence, data quality, change
assessment, provenance) is produced by code. On Ollama the reply is constrained to this schema, so the model cannot answer in
prose, use other keys, or emit inline reasoning. `tests/test_agent_runner.py` checks the schema stays in step with the contract text.
"""
from __future__ import annotations

from typing import Any

NARRATIVE_SCHEMA_CODE: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["narrative"],
    "properties": {
        "narrative": {
            "type": "object",
            "additionalProperties": False,
            "required": ["reasoning", "examiner_narrative", "data_gaps_followups"],
            "properties": {
                "reasoning": {"type": "string"},
                "examiner_narrative": {"type": "string"},
                "data_gaps_followups": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
}

# One entry per finding, keyed by rule id (a list, because strict structured output cannot take data-dependent keys).
_PARAGRAPHS = {
    "type": "array",
    "items": {"type": "object", "additionalProperties": False, "required": ["rule_id", "text"],
              "properties": {"rule_id": {"type": "string"}, "text": {"type": "string"}}},
}
NARRATIVE_SCHEMA: dict[str, Any] = {
    **NARRATIVE_SCHEMA_CODE,
    "required": ["narrative", "examiner_paragraphs"],
    "properties": {**NARRATIVE_SCHEMA_CODE["properties"], "examiner_paragraphs": _PARAGRAPHS},
}


def schema_for(templates: str) -> dict[str, Any]:
    return NARRATIVE_SCHEMA if templates == "model" else NARRATIVE_SCHEMA_CODE

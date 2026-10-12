"""The JSON schema of what the model writes for a tool-backed agent (mirrors builders/narrative_contract.md).

The model writes prose only. Everything else in a result (classification, status, rule trace, evidence, data quality, change
assessment, provenance) is produced by code. On Ollama the reply is constrained to this schema, so the model cannot answer in
prose, use other keys, or emit inline reasoning. `tests/test_agent_runner.py` checks the schema stays in step with the contract text.
"""
from __future__ import annotations

from typing import Any

NARRATIVE_SCHEMA: dict[str, Any] = {
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

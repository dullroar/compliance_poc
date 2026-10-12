"""Maps the orchestrator's auditor payload ({loan_data, agent_results}) to the auditor tool's canonical case."""
from __future__ import annotations

from typing import Any

from compliance_common.decision import unavailable_record

from .rules import EVALUATOR_VERSION

TOOL = "auditor_evaluate"


def _rules(result: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for item in result.get("determination_trace", []) or []:
        outcome, _, message = str(item.get("finding", "")).partition(": ")
        out.append({"rule_id": item.get("step", ""), "outcome": outcome, "message": message, "basis": item.get("basis", "")})
    return out


def tool_arguments(payload: Any) -> tuple[dict[str, Any] | None, str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("agent_results"), dict):
        return None, "The auditor needs {loan_data, agent_results} with the other agents' assembled results."
    loan = payload.get("loan_data") if isinstance(payload.get("loan_data"), dict) else {}
    results, failed = {}, []
    for key, r in payload["agent_results"].items():
        if not isinstance(r, dict) or "domain_determination" not in r:
            failed.append(key)               # a failed or unparsed agent is reported as missing, never assumed to pass
            continue
        results[key] = {
            "classification": r["domain_determination"].get("classification"),
            "compliance_result": (r.get("determination_status") or {}).get("result"),
            "decision_id": (r.get("agent_metadata") or {}).get("decision_id"),
            "agent_version": (r.get("agent_metadata") or {}).get("agent_version"),
            "rules": _rules(r), "missing_facts": r.get("missing_facts", []),
            "evaluation": r.get(f"{key}_evaluation") or r.get("threshold_evaluation") or {},
        }
    cases = {k: v for k, v in loan.items() if k.endswith("_case") and isinstance(v, dict)}
    case: dict[str, Any] = {"results": results, "cases": cases, "failed_agents": failed}
    case_id = (loan.get("case_information") or {}).get("case_id")
    if case_id:
        case["case_id"] = case_id
    return {"case": case}, ""


def unavailable(reason: str, loan_data: Any) -> dict[str, Any]:
    return unavailable_record("auditor", EVALUATOR_VERSION, "agent_results", reason, loan_data)


def extras(decision: dict[str, Any]) -> dict[str, Any]:
    ev = decision.get("auditor_evaluation", {})
    return {"auditor_evaluation": ev, "audit_conclusion": decision.get("final_classification"),
            "audit_summary": {"agents_reviewed": ev.get("agents_reviewed", []), "agents_missing": ev.get("agents_missing", [])},
            "cross_regime_findings": ev.get("cross_regime_findings", []), "isolated_findings": ev.get("isolated_findings", []),
            "remediation_priorities": ev.get("remediation_priorities", [])}

# the auditor is shown no case in its narration prompt (the audit input goes to the tool)
NARRATE_CASE = False

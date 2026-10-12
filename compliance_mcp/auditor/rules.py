"""Deterministic cross-regime audit evaluator.

Consumes the other agents' results (classification, compliance result, rule outcomes, missing facts, evaluation
extras) and the canonical cases from the loan payload, and applies explicit checks. It never re-decides any
regime: it looks for places where regimes disagree about the same fact, share a root cause, or are missing.

Checks (each a rule; a failed check is a cross-regime finding):
  AUD-AGENTS        expected agents present (a missing agent is never assumed to pass)
  AUD-RATE-SPREAD   HMDA's reported rate spread vs the spread HPML and HMDA compute from APR - APOR
  AUD-PRICING       APR / APOR / rate-set evidence equal across the HPML and HMDA cases
  AUD-AMOUNT        loan amount equal across the HPML, HMDA, TRID-adjacent and flood cases
  AUD-DATES         application, decision and closing dates consistent across cases
  AUD-CASE-ID       one loan, one case id
  AUD-DEMOGRAPHICS  VMI says monitoring data was provided/declined-and-noted while HMDA's LAR lacks it
  AUD-OCCUPANCY     principal-residence facts agree across VMI, HPML and HMDA
  AUD-SCOPE         VMI's HMDA-reportable flag agrees with HMDA coverage
  AUD-SHARED-GAP    the same missing fact reported by two or more agents
Per-agent problems that no check links across regimes are reported as isolated findings.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from compliance_common.decision import base_record, finalize, rule
from compliance_common.pack import EvaluatorValidationError, Pack, load_pack, validate_instance

EVALUATOR_VERSION = "0.1.0"
PACK_DIR = Path(__file__).resolve().parent / "pack"
BAD = {"not_satisfied", "unable_to_determine", "review_required", "not_eligible"}
DEMOGRAPHIC_ITEMS = ("ethnicity", "race", "sex", "age")
# A cross-regime finding already explains these per-agent rule outcomes, so they are not repeated as isolated findings.
EXPLAINS = {"AUD-RATE-SPREAD": {"HMDA-RATE-SPREAD"}, "AUD-DEMOGRAPHICS": {"HMDA-LAR-FIELDS"}}
DATE_KEYS = ("action_taken_date", "consummation_date", "transaction_date", "loan_date", "evaluation_date", "decision_date", "application_received_date")


def _pack() -> Pack:
    return load_pack("auditor", PACK_DIR, ("thresholds",))


def validate_auditor_rule_pack() -> None:
    _pack()


def validate_auditor_decision_record(record: dict[str, Any]) -> None:
    validate_instance(record, _pack().decision_schema, "auditor decision record")


def _get(cases: dict[str, Any], name: str, *path: str) -> Any:
    value: Any = cases.get(name)
    for key in path:
        value = value.get(key) if isinstance(value, dict) else None
    return value


def _lar_has(lar: dict[str, Any], item: str) -> bool:
    """Does the HMDA LAR carry this monitoring item (ethnicity / race / sex inside the applicant block, age on its own)?"""
    if item == "age":
        return lar.get("age") not in (None, "", [])
    applicant = lar.get("applicant")
    return isinstance(applicant, dict) and applicant.get(item) not in (None, "", [])


def _equal(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):          # bool is an int subclass; never compare it as a number
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return Decimal(str(a)) == Decimal(str(b))
    return a == b


class _Findings:
    def __init__(self) -> None:
        self.rules: list[dict[str, Any]] = []
        self.cross: list[dict[str, Any]] = []

    def check(self, rule_id: str, ok: bool | None, message: str, *, agents: list[str], severity: str, root_cause: str, action: str) -> None:
        """ok True: consistent; False: conflict (finding); None: not enough data to compare (silent, no rule)."""
        if ok is None:
            return
        self.rules.append(rule(rule_id, "satisfied" if ok else "not_satisfied", "institution_policy", message))
        if not ok:
            self.cross.append({"id": rule_id, "root_cause": root_cause, "affected_agents": sorted(agents), "impact_summary": message, "severity": severity, "recommended_action": action})


def _compare(f: _Findings, rule_id: str, label: str, values: dict[str, Any], agents: dict[str, str], severity: str, action: str) -> None:
    present = {k: v for k, v in values.items() if v is not None}
    if len(present) < 2:
        return
    first = next(iter(present.values()))
    ok = all(_equal(first, v) for v in present.values())
    detail = ", ".join(f"{k}={v}" for k, v in present.items())
    f.check(rule_id, ok, f"{label} {'agrees' if ok else 'DIFFERS'} across cases: {detail}.", agents=sorted({agents[k] for k in present}),
            severity=severity, root_cause=f"{label} is recorded differently in different regimes' inputs", action=action)


def _cross_checks(results: dict[str, Any], cases: dict[str, Any], t: dict[str, Any]) -> _Findings:
    f = _Findings()
    hmda_rs = _get(cases, "hmda_case", "reported_rate_spread")
    hmda_computed = (results.get("hmda", {}).get("evaluation") or {}).get("rate_spread_computed")
    hpml_spread = (results.get("hpml", {}).get("evaluation") or {}).get("spread")
    if hmda_rs is not None and hpml_spread is not None:
        ok = _equal(Decimal(str(hmda_rs)).quantize(Decimal("0.001")), Decimal(str(hpml_spread)).quantize(Decimal("0.001")))
        f.check("AUD-RATE-SPREAD", ok, f"HMDA reported rate spread {hmda_rs}; HPML computed APR minus APOR = {hpml_spread}" + (f"; HMDA recomputed {hmda_computed}" if hmda_computed else "") + ".",
                agents=["hmda", "hpml"], severity="High", root_cause="The HMDA reported rate spread was not derived from the same APR and APOR evidence HPML used",
                action="Recompute the HMDA rate spread as APR minus the APOR for the rate-set date and correct the LAR entry.")
    _compare(f, "AUD-PRICING", "APR", {"hpml_case": _get(cases, "hpml_case", "apr"), "hmda_case": _get(cases, "hmda_case", "apr")}, {"hpml_case": "hpml", "hmda_case": "hmda"}, "High", "Reconcile the APR between the HPML and HMDA inputs.")
    _compare(f, "AUD-PRICING", "APOR", {"hpml_case": _get(cases, "hpml_case", "apor"), "hmda_case": _get(cases, "hmda_case", "apor")}, {"hpml_case": "hpml", "hmda_case": "hmda"}, "High", "Use one APOR lookup (apor_reference) for both regimes.")
    _compare(f, "AUD-AMOUNT", "Loan amount",
             {"hpml_case": _get(cases, "hpml_case", "principal_obligation"), "hmda_case": _get(cases, "hmda_case", "amount"), "fzd_case": _get(cases, "fzd_case", "loan_balance"), "hvcre_case": _get(cases, "hvcre_case", "credit_facility_amount")},
             {"hpml_case": "hpml", "hmda_case": "hmda", "fzd_case": "fzd", "hvcre_case": "hvcre"}, "Moderate", "Confirm the loan amount at closing and correct the inputs that differ.")
    _compare(f, "AUD-DATES", "Application date",
             {"hmda_case": _get(cases, "hmda_case", "application_date"), "trid_case": _get(cases, "trid_case", "application_received_date"), "ecoa_case": _get(cases, "ecoa_case", "application_received_date")},
             {"hmda_case": "hmda", "trid_case": "trid", "ecoa_case": "ecoa"}, "Moderate", "Confirm the application received date and correct the inputs that differ.")
    _compare(f, "AUD-DATES", "Closing/action date",
             {"hmda_case": _get(cases, "hmda_case", "action_taken_date") if _get(cases, "hmda_case", "action_taken") == "originated" else None,
              "trid_case": _get(cases, "trid_case", "consummation_date"), "fzd_case": _get(cases, "fzd_case", "transaction_date"), "hvcre_case": _get(cases, "hvcre_case", "loan_date")},
             {"hmda_case": "hmda", "trid_case": "trid", "fzd_case": "fzd", "hvcre_case": "hvcre"}, "Moderate", "Confirm the consummation date and correct the inputs that differ.")
    ids = {name: _get(cases, name, "case_id") for name in cases}
    _compare(f, "AUD-CASE-ID", "Case id", ids, {n: n.removesuffix("_case") for n in cases}, "Low", "Confirm all inputs describe the same loan.")
    # VMI says it asked / got the monitoring data; HMDA's LAR must then carry it
    vmi_items = (_get(cases, "vmi_case", "monitoring", "items") or {})
    lar = _get(cases, "hmda_case", "lar")
    if vmi_items and lar is not None and results.get("hmda", {}).get("classification") in ("Covered", "Potentially Covered"):
        have = [i for i in DEMOGRAPHIC_ITEMS if (vmi_items.get(i) or {}).get("provided") or (vmi_items.get(i) or {}).get("declined")]
        absent = [i for i in have if not _lar_has(lar, i)]
        f.check("AUD-DEMOGRAPHICS", not absent,
                (f"VMI records {', '.join(have)} as provided or declined, but the HMDA LAR is missing {', '.join(absent)}." if absent else "VMI's monitoring data and HMDA's LAR demographics are consistent."),
                agents=["vmi", "hmda"], severity="High", root_cause="Monitoring information collected under Regulation B did not reach the HMDA loan/application register",
                action="Transfer the collected ethnicity, race, sex and age (and how each was collected) to the LAR, or correct the VMI record.")
    occ = {"vmi_case": _get(cases, "vmi_case", "principal_residence"), "hpml_case": _get(cases, "hpml_case", "secured_by_principal_dwelling")}
    lar_occ = (lar or {}).get("occupancy_type") if isinstance(lar, dict) else None
    if lar_occ is not None:
        occ["hmda_case"] = str(lar_occ).lower().replace(" ", "_") in ("principal_residence", "principal", "1")
    _compare(f, "AUD-OCCUPANCY", "Principal-residence status", occ, {"vmi_case": "vmi", "hpml_case": "hpml", "hmda_case": "hmda"}, "Moderate", "Confirm occupancy and correct the inputs that differ.")
    vmi_reportable, hmda_class = _get(cases, "vmi_case", "hmda_reportable"), results.get("hmda", {}).get("classification")
    if vmi_reportable is not None and hmda_class in ("Covered", "Not Covered"):
        ok = vmi_reportable == (hmda_class == "Covered")
        f.check("AUD-SCOPE", ok, f"VMI treats the loan as {'HMDA-reportable' if vmi_reportable else 'not HMDA-reportable'}; HMDA classified it {hmda_class}.",
                agents=["vmi", "hmda"], severity="Moderate", root_cause="Regimes disagree on whether the loan is HMDA-reportable", action="Align the VMI hmda_reportable flag with the HMDA coverage determination.")
    # same missing fact reported by two or more agents
    seen: dict[str, set[str]] = {}
    for key, r in results.items():
        for m in r.get("missing_facts", []):
            name = str(m.get("field", "")).split(".")[-1].strip()
            if name:
                seen.setdefault(name, set()).add(key)
    for name, agents in sorted(seen.items()):
        if len(agents) >= 2:
            f.check("AUD-SHARED-GAP", False, f"The fact '{name}' is missing in {', '.join(sorted(agents))}.", agents=sorted(agents), severity="Moderate",
                    root_cause=f"A single missing fact ('{name}') blocks more than one regime", action=f"Obtain '{name}' once and supply it to every regime.")
    return f


def evaluate_auditor(case: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a canonical audit case without network or model calls."""
    if not isinstance(case, dict):
        raise EvaluatorValidationError("auditor input must be an object")
    pack = _pack()
    validate_instance(case, pack.input_schema, "canonical auditor input")
    t = pack.files["thresholds"]
    results, cases = case["results"], case.get("cases") or {}
    dates = sorted(str(v) for c in cases.values() if isinstance(c, dict) for k, v in c.items() if k in DATE_KEYS and isinstance(v, str))
    base = base_record("auditor", EVALUATOR_VERSION, pack, case, date.fromisoformat(dates[-1] if dates else "1970-01-01"))
    rules, missing = base["rule_results"], base["missing_facts"]
    expected = case.get("expected_agents") or t["expected_agents"]
    absent = [k for k in expected if k not in results]
    failed = case.get("failed_agents") or []
    for k in absent:
        missing.append({"field": f"agent:{k}", "reason": "no result from this agent" + (" (the agent call failed)" if k in failed else "") + "; it is never assumed to pass or fail"})
    rules.append(rule("AUD-AGENTS", "unable_to_determine" if absent else "satisfied", "institution_policy",
                      f"Missing agent result(s): {', '.join(absent)}." if absent else f"All {len(expected)} expected agents reported."))
    ev: dict[str, Any] = {"agents_reviewed": sorted(results), "agents_missing": absent}

    def done(classification: str, status: str, result: str) -> dict[str, Any]:
        base["auditor_evaluation"] = ev
        finalize(base, classification, status, result)
        validate_instance(base, pack.decision_schema, "auditor decision record")
        return base

    if not results:
        ev.update(cross_regime_findings=[], isolated_findings=[], remediation_priorities=[])
        return done("Unable To Determine", "Unable To Determine", "Unable To Determine")
    checks = _cross_checks(results, cases, t)
    rules.extend(checks.rules)
    explained = {rid for c in checks.cross for rid in EXPLAINS.get(c["id"], set())}
    isolated = []
    for key in sorted(results):
        r = results[key]
        bad = [x for x in r.get("rules", []) if x.get("outcome") in BAD and x.get("rule_id") not in explained]
        if bad:
            isolated.append({"agent": key, "compliance_result": r.get("compliance_result"), "classification": r.get("classification"),
                             "summary": "; ".join(f"{x['rule_id']} {x['outcome']}" for x in bad[:6]) + (f" (+{len(bad) - 6} more)" if len(bad) > 6 else "")})
    cross = checks.cross
    priorities = []
    for rank, c in enumerate(sorted(cross, key=lambda c: {"High": 0, "Moderate": 1, "Low": 2}[c["severity"]]), 1):
        priorities.append({"priority": rank, "issue": c["impact_summary"], "recommended_action": c["recommended_action"]})
    for item in isolated:
        priorities.append({"priority": len(priorities) + 1, "issue": f"{item['agent']}: {item['summary']}", "recommended_action": f"Resolve the {item['agent']} findings listed in its decision record."})
    ev.update(cross_regime_findings=cross, isolated_findings=isolated, remediation_priorities=priorities,
              agent_outcomes={k: {"classification": r.get("classification"), "compliance_result": r.get("compliance_result")} for k, r in sorted(results.items())})
    problems = bool(cross or isolated)
    worst = any(r.get("compliance_result") == "Non-Compliant" for r in results.values())
    if len(cross) >= 2:
        classification = "Multiple Cross-Regime Deficiencies"
    elif cross:
        classification = "Cross-Regime Deficiency"
    elif isolated:
        classification = "Isolated Findings"
    else:
        classification = "Pass"
    if absent and classification == "Pass":
        return done("Unable To Determine", "Unable To Determine", "Unable To Determine")
    result = "Non-Compliant" if worst else ("Potential Issue" if problems or absent else "Compliant")
    return done(classification, "Determined", result)

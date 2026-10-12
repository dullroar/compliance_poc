"""Deterministic HPML evaluator (12 CFR 1026.35).

Coverage: a closed-end consumer credit transaction secured by the principal dwelling
whose APR exceeds the APOR by the spread for its lien/size (first lien within the Freddie
Mac limit 1.5, first lien above it 2.5, subordinate lien 3.5; "or more" = inclusive).
Obligations for an HPML: escrow (first lien, 1026.35(b)) and appraisal (1026.35(c)).
Exemption eligibility is a documented input fact; this evaluator never infers it.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from compliance_common.decision import base_record, fact, finalize, rule
from compliance_common.pack import EvaluatorValidationError, Pack, as_date, load_pack, threshold_record, validate_instance

EVALUATOR_VERSION = "0.1.0"
PACK_DIR = Path(__file__).resolve().parent / "pack"
_ESCROW_EXEMPT_KINDS = {"cooperative", "initial_construction", "bridge_loan_12_months_or_less", "reverse_mortgage", "pace"}


def _pack() -> Pack:
    return load_pack("hpml", PACK_DIR, ("thresholds", "conforming_limits"))


def validate_hpml_rule_pack() -> None:
    _pack()


def validate_hpml_decision_record(record: dict[str, Any]) -> None:
    validate_instance(record, _pack().decision_schema, "HPML decision record")


def _dec(value: Any) -> Decimal:
    return Decimal(str(value))


def _limit(case: dict[str, Any], pack: Pack, rate_set: date, facts: list, missing: list) -> tuple[Decimal | None, str]:
    """The conforming limit usable for this loan, and where it came from."""
    if case.get("applicable_conforming_limit") is not None:
        facts.append({"field": "applicable_conforming_limit", "value": case["applicable_conforming_limit"]})
        return _dec(case["applicable_conforming_limit"]), "supplied"
    baseline = next((r["one_unit_baseline"] for r in pack.files["conforming_limits"]["records"] if r["year"] == rate_set.year), None)
    amount = _dec(case["principal_obligation"])
    if baseline is not None and amount <= _dec(baseline):
        # Every Freddie Mac limit (any unit count, any county) is >= the one-unit baseline.
        facts.append({"field": "pinned_one_unit_baseline", "value": baseline})
        return _dec(baseline), "pinned_baseline"
    reason = (f"principal obligation exceeds the pinned {rate_set.year} baseline; the applicable Freddie Mac limit must be supplied"
              if baseline is not None else f"no pinned conforming-limit baseline for {rate_set.year}; the applicable limit must be supplied")
    missing.append({"field": "applicable_conforming_limit", "reason": reason})
    return None, "missing"


def _obligations(case: dict[str, Any], lien: str, facts: list, missing: list) -> list[dict[str, Any]]:
    rules = []
    # Escrow: first-lien HPMLs only, unless exempt.
    if lien != "first":
        rules.append(rule("HPML-ESCROW", "does_not_apply", "regulatory", "Escrow requirement applies to first-lien HPMLs only (1026.35(b)(1))."))
    elif case.get("escrow_exemption", "none") in _ESCROW_EXEMPT_KINDS:
        rules.append(rule("HPML-ESCROW", "does_not_apply", "regulatory", f"Escrow exempt: {case['escrow_exemption']} (1026.35(b)(2)(i))."))
    elif case.get("escrow_exemption_documented") is True:
        rules.append(rule("HPML-ESCROW", "does_not_apply", "regulatory", "Creditor documented eligibility for the 1026.35(b)(2)(iii) exemption."))
    else:
        established = fact(case, "escrow_established_before_consummation", facts, missing)
        outcome = "unable_to_determine" if established is None else ("satisfied" if established else "not_satisfied")
        rules.append(rule("HPML-ESCROW", outcome, "regulatory", "Escrow for property taxes and required insurance must be established before consummation (1026.35(b)(1))."))
    # Appraisal.
    if case.get("appraisal_exemption_documented") is True:
        rules.append(rule("HPML-APPRAISAL", "does_not_apply", "regulatory", "A 1026.35(c)(2) exemption is documented."))
    else:
        met = fact(case, "appraisal_requirements_met", facts, missing)
        outcome = "unable_to_determine" if met is None else ("satisfied" if met else "not_satisfied")
        rules.append(rule("HPML-APPRAISAL", outcome, "regulatory", "HPML appraisal requirements of 1026.35(c) must be met."))
    return rules


def _result(classification: str, obligations: list[dict[str, Any]]) -> str:
    if classification == "Unable To Determine":
        return "Unable To Determine"
    if classification != "HPML":
        return "Not Applicable"
    outcomes = {r["outcome"] for r in obligations}
    if "not_satisfied" in outcomes:
        return "Non-Compliant"
    return "Potential Issue" if "unable_to_determine" in outcomes else "Compliant"


def evaluate_hpml(case: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a canonical HPML case without network or model calls."""
    if not isinstance(case, dict):
        raise EvaluatorValidationError("HPML input must be an object")
    pack = _pack()
    validate_instance(case, pack.input_schema, "canonical HPML input")
    rate_set = as_date(case["rate_set_date"], "rate_set_date")
    base = base_record("hpml", EVALUATOR_VERSION, pack, case, rate_set)
    facts, missing, rules = base["facts_used"], base["missing_facts"], base["rule_results"]
    threshold = threshold_record(pack.files["thresholds"], rate_set)
    base["threshold_record"] = threshold

    def done(classification: str, obligations: list | None = None, **extra: Any) -> dict[str, Any]:
        base.update(extra)
        status = "Unable To Determine" if classification == "Unable To Determine" else "Determined"
        finalize(base, classification, status, _result(classification, obligations or []))
        validate_instance(base, pack.decision_schema, "HPML decision record")
        return base

    if threshold is None:
        missing.append({"field": "rate_set_date", "reason": "no effective threshold record for this rate-set date"})
        return done("Unable To Determine")

    scope = {k: case[k] for k in ("consumer_purpose", "closed_end", "secured_by_principal_dwelling")}
    facts.extend({"field": k, "value": v} for k, v in scope.items())
    if not all(scope.values()):
        failed = sorted(k for k, v in scope.items() if not v)
        rules.append(rule("HPML-SCOPE", "does_not_apply", "regulatory",
                          f"Not a closed-end consumer transaction secured by the principal dwelling ({', '.join(failed)} is false)."))
        return done("Not Covered")
    rules.append(rule("HPML-SCOPE", "applies", "regulatory", "Closed-end consumer credit secured by the principal dwelling."))

    apor_ref = case.get("apor_reference")
    if case.get("apor") is None or apor_ref is None:
        missing.append({"field": "apor", "reason": "APOR and its apor_reference (table date, product, source) are required"})
        return done("Unable To Determine")
    apr, apor = _dec(case["apr"]), _dec(case["apor"])
    facts.extend([{"field": "apr", "value": case["apr"]}, {"field": "apor", "value": case["apor"]},
                  {"field": "apor_reference", "value": apor_ref}, {"field": "lien_position", "value": case["lien_position"]},
                  {"field": "principal_obligation", "value": case["principal_obligation"]}])

    lien = case["lien_position"]
    if lien == "first":
        limit, limit_source = _limit(case, pack, rate_set, facts, missing)
        if limit is None:
            return done("Unable To Determine")
        jumbo = _dec(case["principal_obligation"]) > limit
        key, label = ("first_lien_jumbo_spread", "first lien above the Freddie Mac limit") if jumbo else ("first_lien_conforming_spread", "first lien within the Freddie Mac limit")
    else:
        limit, limit_source = None, "n/a"
        key, label = "subordinate_lien_spread", "subordinate lien"
    required = _dec(threshold[key])
    spread = apr - apor
    is_hpml = spread >= required
    rules.append(rule("HPML-SPREAD", "applies" if is_hpml else "does_not_apply", "regulatory",
                      f"APR minus APOR is {spread} points; {label} threshold is {required} or more.",
                      value=str(spread), threshold=str(required), operator="gte"))
    classification = "HPML" if is_hpml else "Not HPML"
    obligations = _obligations(case, lien, facts, missing) if is_hpml else []
    rules.extend(obligations)
    return done(classification, obligations, hpml_evaluation={
        "apr": str(apr), "apor": str(apor), "spread": str(spread), "threshold": str(required), "threshold_basis": label,
        "conforming_limit": str(limit) if limit is not None else None, "conforming_limit_source": limit_source,
        "apor_reference": apor_ref,
    })

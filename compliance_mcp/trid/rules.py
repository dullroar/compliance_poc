"""Deterministic TRID evaluator (12 CFR 1026.19(e) Loan Estimate, (f) Closing Disclosure).

Checks, from supplied dates and amounts only:
  scope; LE within 3 creditor business days of application and >= 7 business days before
  consummation; CD received >= 3 business days before consummation (mail/electronic delivery
  is presumed received 3 business days later); a new 3-day wait after APR / product /
  prepayment-penalty changes; and good-faith tolerances (zero, 10% aggregate) with the
  60-day refund cure. Not evaluated (reported as follow-ups by the agent): revised-LE
  timing under (e)(4), content accuracy of the forms, settlement-service-provider lists.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from compliance_common.calendar import add_business_days, creditor_business_day, specific_business_day, subtract_business_days
from compliance_common.decision import base_record, finalize, rule
from compliance_common.pack import EvaluatorValidationError, Pack, as_date, load_pack, threshold_record, validate_instance

EVALUATOR_VERSION = "0.1.0"
PACK_DIR = Path(__file__).resolve().parent / "pack"
_VALID_REVISION_REASONS = {
    "changed_circumstance_settlement", "changed_circumstance_eligibility", "consumer_requested",
    "interest_rate_dependent", "expiration", "construction_delayed_settlement",
}


def _pack() -> Pack:
    return load_pack("trid", PACK_DIR, ("thresholds", "calendar"))


def validate_trid_rule_pack() -> None:
    _pack()


def validate_trid_decision_record(record: dict[str, Any]) -> None:
    validate_instance(record, _pack().decision_schema, "TRID decision record")


def _dec(value: Any) -> Decimal:
    return Decimal(str(value))


class _Ctx:
    def __init__(self, case: dict[str, Any], pack: Pack, threshold: dict[str, Any]) -> None:
        self.case, self.t = case, threshold
        self.consummation = as_date(case["consummation_date"], "consummation_date")
        self.specific = specific_business_day(pack.files["calendar"]["holidays"])
        open_days = case.get("creditor_open_days") or threshold["default_creditor_open_days"]
        self.open_days_supplied = bool(case.get("creditor_open_days"))
        closed = [as_date(d, "creditor_closed_dates") for d in case.get("creditor_closed_dates", [])]
        self.creditor = creditor_business_day(open_days, closed)

    def receipt(self, disclosure: dict[str, Any]) -> date:
        delivered = as_date(disclosure["delivery_date"], "delivery_date")
        if disclosure["delivery_method"] == "in_person":
            return delivered
        return add_business_days(delivered, self.t["not_in_person_receipt_business_days"], self.specific)


def _timing_rule(rule_id: str, ok: bool, message: str, **extra: Any) -> dict[str, Any]:
    return rule(rule_id, "satisfied" if ok else "not_satisfied", "regulatory", message, **extra)


def _cd_rule(ctx: _Ctx, rule_id: str, label: str, disclosure: dict[str, Any], facts: list, ev: dict) -> dict[str, Any]:
    deadline = subtract_business_days(ctx.consummation, ctx.t["cd_business_days_before_consummation"], ctx.specific)
    receipt = ctx.receipt(disclosure)
    ev[f"{rule_id}_receipt_date"], ev[f"{rule_id}_deadline"] = receipt.isoformat(), deadline.isoformat()
    facts.append({"field": label, "value": disclosure})
    if disclosure.get("waiver_documented"):
        return rule(rule_id, "does_not_apply", "regulatory", f"{label}: three-business-day wait waived by a documented bona fide emergency (1026.19(f)(1)(iv)).")
    return _timing_rule(rule_id, receipt <= deadline,
                        f"{label} received {receipt.isoformat()}; must be received on or before {deadline.isoformat()} (3 business days before consummation, 1026.19(f)(1)(ii)).",
                        value=receipt.isoformat(), threshold=deadline.isoformat(), operator="lte")


def _tolerance(ctx: _Ctx, rules: list, facts: list, missing: list, ev: dict) -> bool:
    """Evaluate good-faith tolerances. Returns True when an uncured excess exists."""
    charges = ctx.case.get("charges")
    if charges is None:
        missing.append({"field": "charges", "reason": "charge-level disclosed and actual amounts are required for the tolerance test"})
        rules.append(rule("TRID-TOLERANCE", "unable_to_determine", "regulatory", "No charges supplied; good-faith tolerance cannot be tested."))
        return False
    zero_excess = Decimal(0)
    ten_base = ten_actual = Decimal(0)
    notes: list[str] = []
    for charge in charges:
        baseline = _dec(charge["disclosed_amount"])
        if charge.get("revised_amount") is not None:
            if charge.get("revision_reason") in _VALID_REVISION_REASONS and charge.get("revision_documented") is True:
                baseline = _dec(charge["revised_amount"])
            else:
                notes.append(f"{charge['id']}: revised amount ignored (no documented permitted reason, 1026.19(e)(3)(iv))")
        actual = _dec(charge["actual_amount"])
        if charge["category"] == "zero_tolerance":
            zero_excess += max(Decimal(0), actual - baseline)
        elif charge["category"] == "ten_percent_tolerance":
            ten_base += baseline
            ten_actual += actual
    allowed = ten_base * (1 + _dec(ctx.t["ten_percent_tolerance"]))
    ten_excess = max(Decimal(0), ten_actual - allowed)
    total = zero_excess + ten_excess
    due = ctx.consummation + timedelta(days=ctx.t["refund_calendar_days_after_consummation"])
    ev["tolerance"] = {"zero_tolerance_excess": str(zero_excess), "ten_percent_baseline": str(ten_base),
                       "ten_percent_allowed": str(allowed), "ten_percent_actual": str(ten_actual),
                       "ten_percent_excess": str(ten_excess), "total_excess": str(total),
                       "cure_due_by": due.isoformat(), "notes": notes}
    facts.append({"field": "charges", "value": len(charges)})
    if total == 0:
        rules.append(rule("TRID-TOLERANCE", "satisfied", "regulatory", "Charges are within the zero and 10% tolerances (1026.19(e)(3)).",
                          value=str(total), threshold="0", operator="lte"))
        return False
    refund = ctx.case.get("tolerance_refund")
    if refund and _dec(refund["amount"]) >= total and as_date(refund["date"], "tolerance_refund.date") <= due:
        rules.append(rule("TRID-TOLERANCE", "satisfied", "regulatory",
                          f"Excess of {total} was refunded {refund['date']}, within 60 days of consummation (1026.19(f)(2)(v)).",
                          value=str(total), threshold="0", operator="lte"))
        return False
    rules.append(rule("TRID-TOLERANCE", "not_satisfied", "regulatory",
                      f"Charges exceed tolerance by {total}; refund no later than {due.isoformat()} is required (1026.19(f)(2)(v)).",
                      value=str(total), threshold="0", operator="lte"))
    return True


def evaluate_trid(case: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a canonical TRID case without network or model calls."""
    if not isinstance(case, dict):
        raise EvaluatorValidationError("TRID input must be an object")
    pack = _pack()
    validate_instance(case, pack.input_schema, "canonical TRID input")
    application = as_date(case["application_received_date"], "application_received_date")
    consummation = as_date(case["consummation_date"], "consummation_date")
    if consummation < application:
        raise EvaluatorValidationError("consummation_date precedes application_received_date")
    base = base_record("trid", EVALUATOR_VERSION, pack, case, application)
    facts, missing, rules = base["facts_used"], base["missing_facts"], base["rule_results"]
    threshold = threshold_record(pack.files["thresholds"], application)
    base["threshold_record"] = threshold
    ev: dict[str, Any] = {}

    def done(classification: str, status: str, result: str) -> dict[str, Any]:
        base["trid_evaluation"] = ev
        finalize(base, classification, status, result)
        validate_instance(base, pack.decision_schema, "TRID decision record")
        return base

    if threshold is None:
        missing.append({"field": "application_received_date", "reason": "application predates the TRID rule-pack window (2015-10-03)"})
        return done("Unable To Determine", "Unable To Determine", "Unable To Determine")

    scope = {"closed_end": case["closed_end"], "secured_by_real_property_or_cooperative_unit": case["secured_by_real_property_or_cooperative_unit"],
             "not_reverse_mortgage": not case.get("reverse_mortgage", False)}
    facts.extend({"field": k, "value": v} for k, v in scope.items())
    if not all(scope.values()):
        rules.append(rule("TRID-SCOPE", "does_not_apply", "regulatory",
                          "Not a closed-end consumer credit transaction secured by real property or a cooperative unit, other than a reverse mortgage (1026.19(e)(1)(i))."))
        return done("Not Covered", "Determined", "Not Applicable")
    rules.append(rule("TRID-SCOPE", "applies", "regulatory", "Closed-end credit secured by real property or a cooperative unit (1026.19(e)(1)(i))."))
    if case.get("timeshare"):
        missing.append({"field": "timeshare", "reason": "timeshare timing differs (1026.19(e)(1)(iii)(C), (f)(1)(ii)(B)) and is not evaluated"})
        return done("Review Required", "Review Required", "Potential Issue")

    ctx = _Ctx(case, pack, threshold)
    if not ctx.open_days_supplied:
        facts.append({"field": "creditor_open_days", "value": threshold["default_creditor_open_days"], "source": "pack default (institution policy)"})

    le = case.get("loan_estimate")
    if le is None:
        missing.append({"field": "loan_estimate", "reason": "Loan Estimate delivery date and method are required"})
        rules.append(rule("TRID-LE-3DAY", "unable_to_determine", "regulatory", "No Loan Estimate delivery supplied."))
        rules.append(rule("TRID-LE-7DAY", "unable_to_determine", "regulatory", "No Loan Estimate delivery supplied."))
    else:
        facts.append({"field": "loan_estimate", "value": le})
        delivered = as_date(le["delivery_date"], "loan_estimate.delivery_date")
        d3 = add_business_days(application, threshold["le_business_days_after_application"], ctx.creditor)
        d7 = subtract_business_days(consummation, threshold["le_business_days_before_consummation"], ctx.specific)
        ev["loan_estimate"] = {"delivered": delivered.isoformat(), "three_day_deadline": d3.isoformat(), "seven_day_deadline": d7.isoformat(),
                               "presumed_receipt": ctx.receipt(le).isoformat()}
        rules.append(_timing_rule("TRID-LE-3DAY", delivered <= d3,
                                  f"Loan Estimate delivered {delivered.isoformat()}; due by {d3.isoformat()} (3rd creditor business day after application, 1026.19(e)(1)(iii)(A)).",
                                  value=delivered.isoformat(), threshold=d3.isoformat(), operator="lte"))
        if le.get("waiver_documented"):
            rules.append(rule("TRID-LE-7DAY", "does_not_apply", "regulatory", "Seven-business-day wait waived by a documented bona fide emergency (1026.19(e)(1)(v))."))
        else:
            rules.append(_timing_rule("TRID-LE-7DAY", delivered <= d7,
                                      f"Loan Estimate delivered {delivered.isoformat()}; must be delivered on or before {d7.isoformat()} (7th business day before consummation, 1026.19(e)(1)(iii)(B)).",
                                      value=delivered.isoformat(), threshold=d7.isoformat(), operator="lte"))

    cd = case.get("closing_disclosure")
    if cd is None:
        missing.append({"field": "closing_disclosure", "reason": "Closing Disclosure delivery date and method are required"})
        rules.append(rule("TRID-CD-3DAY", "unable_to_determine", "regulatory", "No Closing Disclosure delivery supplied."))
    else:
        rules.append(_cd_rule(ctx, "TRID-CD-3DAY", "Closing Disclosure", cd, facts, ev))

    triggers = case.get("cd_changes_requiring_new_waiting_period", [])
    revised = case.get("revised_closing_disclosure")
    if triggers:
        facts.append({"field": "cd_changes_requiring_new_waiting_period", "value": triggers})
        if revised is None:
            missing.append({"field": "revised_closing_disclosure", "reason": f"changes {triggers} require corrected disclosures and a new 3-business-day wait"})
            rules.append(rule("TRID-CD-REVISED-3DAY", "unable_to_determine", "regulatory", "A change requiring a new waiting period was reported but no revised Closing Disclosure was supplied (1026.19(f)(2)(ii))."))
        else:
            rules.append(_cd_rule(ctx, "TRID-CD-REVISED-3DAY", "Revised Closing Disclosure", revised, facts, ev))
    elif revised is not None:
        receipt = ctx.receipt(revised)
        facts.append({"field": "revised_closing_disclosure", "value": revised})
        rules.append(_timing_rule("TRID-CD-CORRECTED", receipt <= consummation,
                                  f"Corrected Closing Disclosure received {receipt.isoformat()}; must be received at or before consummation {consummation.isoformat()} (1026.19(f)(2)(i)).",
                                  value=receipt.isoformat(), threshold=consummation.isoformat(), operator="lte"))

    uncured = _tolerance(ctx, rules, facts, missing, ev)

    outcomes = {r["rule_id"]: r["outcome"] for r in rules}
    timing_failed = any(v == "not_satisfied" for k, v in outcomes.items() if k != "TRID-TOLERANCE")
    if timing_failed:
        result = "Non-Compliant"
    elif uncured:
        review = case.get("review_date")
        due = date.fromisoformat(ev["tolerance"]["cure_due_by"])
        result = "Non-Compliant" if review and as_date(review, "review_date") > due else "Potential Issue"
    elif "unable_to_determine" in outcomes.values():
        result = "Potential Issue"
    else:
        result = "Compliant"
    return done("TRID Covered", "Determined", result)

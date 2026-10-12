"""Deterministic ECOA / Regulation B (12 CFR part 1002) evaluator.

Covers the mechanical rules:
  * the outcome class of the credit decision and whether it is adverse action (1002.2(c));
  * notification timing (1002.9(a)(1), (c), (e): 30 days / 90 days after a counteroffer);
  * adverse-action notice content and the "specific reasons" standard (1002.9(a)(2), (b));
  * incompleteness-notice content (1002.9(c)(2)); notice to the primary applicant (1002.9(f));
  * marital-status inquiry limits (1002.5(d)(1)), spousal signature (1002.7(d)(1)),
    age and public-assistance use (1002.6(b)(2)).
Monitoring-information collection (1002.13) is the VMI evaluator's scope. Whether discrimination
occurred is never decided; "reasonable time" standards for large business credit are Review Required.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from compliance_common.decision import base_record, finalize, rule
from compliance_common.pack import EvaluatorValidationError, Pack, as_date, load_pack, validate_instance

EVALUATOR_VERSION = "0.1.0"
PACK_DIR = Path(__file__).resolve().parent / "pack"
CONTENT_ITEMS = {
    "action_statement": "a statement of the action taken",
    "creditor_name_address": "the creditor's name and address",
    "ecoa_notice": "the section 701(a) ECOA notice (1002.9(b)(1))",
    "agency_name_address": "the name and address of the Federal agency that administers compliance",
    "reasons_or_right_disclosure": "either a statement of specific reasons or the right-to-reasons disclosure",
}
CLASSIFICATION = {
    "approved_as_requested": "No Adverse Action", "not_adverse_law_prohibits": "No Adverse Action",
    "not_adverse_product_not_offered": "No Adverse Action", "denied": "Adverse Action Notice Required",
    "existing_account_adverse": "Adverse Action Notice Required", "counteroffer": "Counteroffer",
    "withdrawn_by_applicant": "Withdrawal", "closed_incomplete": "Incomplete Application Procedure",
}


def _pack() -> Pack:
    return load_pack("ecoa", PACK_DIR, ("thresholds",))


def validate_ecoa_rule_pack() -> None:
    _pack()


def validate_ecoa_decision_record(record: dict[str, Any]) -> None:
    validate_instance(record, _pack().decision_schema, "ECOA decision record")


def _d(case: dict[str, Any], key: str) -> date | None:
    value = case.get(key)
    return as_date(value, key) if value else None


def _deadline_rule(rule_id: str, label: str, notice_date: date | None, start: date | None, days: int, cite: str,
                   missing: list, field: str) -> dict[str, Any]:
    if notice_date is None or start is None:
        missing.append({"field": field, "reason": f"needed to test the {days}-day notification deadline ({cite})"})
        return rule(rule_id, "unable_to_determine", "regulatory", f"{label}: the notice date or the start date is missing, so the {days}-day deadline cannot be tested.")
    deadline = start + timedelta(days=days)
    ok = notice_date <= deadline
    return rule(rule_id, "satisfied" if ok else "not_satisfied", "regulatory",
                f"{label}: notified {notice_date}; deadline {deadline} ({days} days after {start}) ({cite}).",
                value=notice_date.isoformat(), threshold=deadline.isoformat(), operator="lte")


def _timing(case: dict[str, Any], decision: str, adverse: bool, t: dict[str, Any], missing: list) -> list[dict[str, Any]]:
    notice = case.get("notice") or {}
    notice_date = _d(notice, "date") if notice.get("sent") else None
    received, complete = _d(case, "application_received_date"), _d(case, "application_complete_date")
    if case.get("business_credit") and case.get("business_revenue_over_1m"):
        return [rule("ECOA-NOTICE-TIMING", "review_required", "regulatory",
                    "Business credit to a business with gross revenues over $1 million: notice is due within a reasonable time (1002.9(a)(3)(ii)); a reviewer must judge it.")]
    if decision == "withdrawn_by_applicant":
        return [rule("ECOA-NOTICE-TIMING", "does_not_apply", "regulatory", "Withdrawal by the applicant is not an action requiring notification.")]
    if decision in ("not_adverse_law_prohibits", "not_adverse_product_not_offered"):
        return [rule("ECOA-NOTICE-TIMING", "does_not_apply", "regulatory", "The refusal is excluded from adverse action (1002.2(c)(2)(iv)/(v)).")]
    if decision == "closed_incomplete":
        inc = case.get("incompleteness_notice") or {}
        candidates = [d for d in (notice_date, _d(inc, "date") if inc.get("sent") else None) if d]
        chosen = min(candidates) if candidates else None
        return [_deadline_rule("ECOA-NOTICE-TIMING", "Incomplete application", chosen, received, t["notification_days"], "1002.9(c)(1)", missing, "notice.date or incompleteness_notice.date")]
    if decision == "existing_account_adverse":
        return [_deadline_rule("ECOA-NOTICE-TIMING", "Adverse action on an existing account", notice_date, _d(case, "decision_date"), t["notification_days"], "1002.9(a)(1)(iii)", missing, "notice.date / decision_date")]
    if decision == "counteroffer":
        counter = case.get("counteroffer") or {}
        out = [_deadline_rule("ECOA-NOTICE-TIMING", "Counteroffer notification", _d(counter, "notice_date"), complete, t["notification_days"], "1002.9(a)(1)(i)", missing, "counteroffer.notice_date / application_complete_date")]
        if adverse:
            out.append(_deadline_rule("ECOA-NOTICE-TIMING-COUNTEROFFER", "Adverse action after an unaccepted counteroffer", notice_date, _d(counter, "notice_date"), t["counteroffer_response_days"], "1002.9(a)(1)(iv)", missing, "notice.date"))
        return out
    return [_deadline_rule("ECOA-NOTICE-TIMING", "Notification of action taken", notice_date, complete, t["notification_days"], "1002.9(a)(1)(i)", missing, "notice.date / application_complete_date")]


def _content(case: dict[str, Any], decision: str, adverse: bool, t: dict[str, Any], missing: list, rules: list) -> None:
    notice = case.get("notice") or {}
    if not adverse and decision != "closed_incomplete":
        rules.append(rule("ECOA-NOTICE-CONTENT", "does_not_apply", "regulatory", "No adverse action: the 1002.9(a)(2) content requirements do not apply."))
        return
    if decision == "closed_incomplete" and not notice.get("sent"):
        inc = case.get("incompleteness_notice") or {}
        if not inc.get("sent"):
            rules.append(rule("ECOA-NOTICE-CONTENT", "unable_to_determine", "regulatory", "Neither an action notice nor an incompleteness notice is recorded."))
            return
        elements = {"specifies_info_needed": "specify the information needed", "reasonable_period_designated": "designate a reasonable period",
                    "warns_no_further_consideration": "state that failure to respond ends consideration"}
        lacking = [text for key, text in elements.items() if inc.get(key) is False]
        unknown = [key for key in elements if inc.get(key) is None]
        for key in unknown:
            missing.append({"field": f"incompleteness_notice.{key}", "reason": "needed to test the notice of incompleteness content (1002.9(c)(2))"})
        outcome = "not_satisfied" if lacking else ("unable_to_determine" if unknown else "satisfied")
        rules.append(rule("ECOA-NOTICE-CONTENT", outcome, "regulatory",
                          f"Notice of incompleteness must {', '.join(lacking)} (1002.9(c)(2))." if lacking else
                          "Notice of incompleteness contains the required elements (1002.9(c)(2))." if not unknown else "Some incompleteness-notice elements are not recorded."))
        return
    if not notice.get("sent"):
        rules.append(rule("ECOA-NOTICE-CONTENT", "not_satisfied", "regulatory", "Adverse action was taken but no notification is recorded as sent (1002.9(a)(1))."))
        return
    volume = case.get("creditor_applications_prior_year")
    if volume is not None and volume <= t["small_volume_creditor_max_applications"]:
        rules.append(rule("ECOA-NOTICE-CONTENT", "does_not_apply", "regulatory", "The creditor received no more than 150 applications in the preceding calendar year; oral notification satisfies 1002.9 (1002.9(d))."))
        return
    if case.get("business_credit") and case.get("business_revenue_over_1m"):
        rules.append(rule("ECOA-NOTICE-CONTENT", "review_required", "regulatory", "Business credit over $1 million revenue has different content rules (1002.9(a)(3)(ii)); a reviewer must judge it."))
        return
    contents = notice.get("contents") or {}
    lacking = [key for key in CONTENT_ITEMS if contents.get(key) is False]
    unknown = [key for key in CONTENT_ITEMS if contents.get(key) is None]
    if notice.get("written") is False:
        lacking.append("written")
    elif notice.get("written") is None:
        unknown.append("written")
    for key in unknown:
        missing.append({"field": f"notice.contents.{key}" if key != "written" else "notice.written", "reason": "needed to test adverse-action notice content (1002.9(a)(2))"})
    outcome = "not_satisfied" if lacking else ("unable_to_determine" if unknown else "satisfied")
    detail = ("; missing: " + ", ".join(CONTENT_ITEMS.get(k, "a written notice") for k in lacking)) if lacking else ""
    rules.append(rule("ECOA-NOTICE-CONTENT", outcome, "regulatory",
                      ("Adverse-action notice is written and contains every element (1002.9(a)(2))." if outcome == "satisfied" else
                       f"Adverse-action notice content is deficient{detail} (1002.9(a)(2))." if lacking else "Some notice-content facts are not recorded.")))
    if notice.get("reasons_basis") == "statement_of_reasons":
        specific = notice.get("specific_reasons")
        if specific is None:
            missing.append({"field": "notice.specific_reasons", "reason": "needed to test the specific-reasons standard (1002.9(b)(2))"})
        rules.append(rule("ECOA-REASONS-SPECIFIC", "unable_to_determine" if specific is None else ("satisfied" if specific else "not_satisfied"), "regulatory",
                          "Statement of reasons must be specific; internal standards or a failed credit score alone are insufficient (1002.9(b)(2))."))


def _other_rules(case: dict[str, Any], missing: list, rules: list) -> None:
    ms = case.get("marital_status_inquiry")
    if ms is None:
        missing.append({"field": "marital_status_inquiry", "reason": "whether marital status was asked must be recorded; silence is not compliance (1002.5(d)(1))"})
        rules.append(rule("ECOA-MARITAL-INQUIRY", "unable_to_determine", "regulatory", "It is not recorded whether marital status was asked."))
    elif not ms.get("asked"):
        rules.append(rule("ECOA-MARITAL-INQUIRY", "does_not_apply", "regulatory", "Marital status was not asked in the credit decision process (monitoring collection under 1002.13 is evaluated by VMI)."))
    elif ms.get("credit_type") == "individual_unsecured" and not ms.get("community_property"):
        rules.append(rule("ECOA-MARITAL-INQUIRY", "not_satisfied", "regulatory", "A creditor shall not inquire about marital status for individual unsecured credit outside a community property context (1002.5(d)(1))."))
    elif ms.get("terms_valid") is False:
        rules.append(rule("ECOA-MARITAL-INQUIRY", "not_satisfied", "regulatory", "Marital status must use only the terms married, unmarried and separated (1002.5(d)(1))."))
    elif ms.get("credit_type") is None:
        missing.append({"field": "marital_status_inquiry.credit_type", "reason": "needed to apply 1002.5(d)(1)"})
        rules.append(rule("ECOA-MARITAL-INQUIRY", "unable_to_determine", "regulatory", "The credit type of the inquiry is not recorded."))
    else:
        rules.append(rule("ECOA-MARITAL-INQUIRY", "satisfied", "regulatory", "The marital-status inquiry is permitted for this credit type and uses the allowed terms (1002.5(d)(1))."))
    sig = case.get("spouse_signature")
    if sig is None:
        missing.append({"field": "spouse_signature", "reason": "whether a spouse or other-person signature was required must be recorded (1002.7(d))"})
        rules.append(rule("ECOA-SPOUSE-SIGNATURE", "unable_to_determine", "regulatory", "It is not recorded whether a spouse or other-person signature was required."))
    elif not sig.get("required"):
        rules.append(rule("ECOA-SPOUSE-SIGNATURE", "does_not_apply", "regulatory", "No spouse or other-person signature was required (1002.7(d))."))
    elif sig.get("signature_required_by_state_law_to_reach_collateral"):
        rules.append(rule("ECOA-SPOUSE-SIGNATURE", "does_not_apply", "regulatory", "A signature needed under state law to reach the collateral is permitted for secured credit (1002.7(d)(4)); reviewer should confirm the law cited."))
    elif sig.get("applicant_qualified_alone") is None or sig.get("joint_applicant") is None:
        missing.append({"field": "spouse_signature.applicant_qualified_alone/joint_applicant", "reason": "needed to apply 1002.7(d)(1)"})
        rules.append(rule("ECOA-SPOUSE-SIGNATURE", "unable_to_determine", "regulatory", "Whether the applicant qualified alone and whether the signer is a joint applicant is not recorded."))
    else:
        bad = sig["applicant_qualified_alone"] and not sig["joint_applicant"]
        rules.append(rule("ECOA-SPOUSE-SIGNATURE", "not_satisfied" if bad else "satisfied", "regulatory",
                          "A qualified applicant's spouse or other non-joint person may not be required to sign the credit instrument (1002.7(d)(1))." if bad else
                          "The signature requirement is consistent with 1002.7(d)(1)."))
    use = case.get("age_public_assistance")
    if not use:
        rules.append(rule("ECOA-AGE-PUBLIC-ASSISTANCE", "unable_to_determine", "regulatory", "No record of how age and public-assistance income were treated."))
        missing.append({"field": "age_public_assistance", "reason": "needed to test 1002.6(b)(2)"})
        return
    allowed_age = {"none", "favors_elderly", "credit_scoring_non_negative", "judgmental_pertinent_element"}
    allowed_pa = {"none", "judgmental_pertinent_element"}
    bad = [x for x, v, ok in (("age", use.get("age_use"), allowed_age), ("public-assistance income", use.get("public_assistance_use"), allowed_pa)) if v not in ok]
    rules.append(rule("ECOA-AGE-PUBLIC-ASSISTANCE", "not_satisfied" if bad else "satisfied", "regulatory",
                      f"Use of {' and '.join(bad)} is not within a permitted use (1002.6(b)(2))." if bad else "Age and public-assistance income were not used outside the uses permitted by 1002.6(b)(2)."))


def evaluate_ecoa(case: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a canonical ECOA case without network or model calls."""
    if not isinstance(case, dict):
        raise EvaluatorValidationError("ECOA input must be an object")
    pack = _pack()
    validate_instance(case, pack.input_schema, "canonical ECOA input")
    t = pack.files["thresholds"]
    received = as_date(case["application_received_date"], "application_received_date")
    base = base_record("ecoa", EVALUATOR_VERSION, pack, case, received)
    facts, missing, rules = base["facts_used"], base["missing_facts"], base["rule_results"]
    decision = case["decision_type"]
    classification = CLASSIFICATION[decision]
    counter = case.get("counteroffer") or {}
    ev: dict[str, Any] = {"decision_type": decision}
    facts.append({"field": "decision_type", "value": decision})

    # Is this adverse action (1002.2(c))?
    if decision in ("denied", "existing_account_adverse"):
        adverse = True
    elif decision == "counteroffer":
        accepted = counter.get("accepted")
        review, notice_date = _d(case, "review_date"), _d(counter, "notice_date")
        adverse = accepted is False or (accepted is None and bool(review and notice_date and review > notice_date + timedelta(days=t["counteroffer_response_days"])))
        pending = accepted is None and not adverse
        rules.append(rule("ECOA-ADVERSE-ACTION", "unable_to_determine" if pending else ("applies" if adverse else "does_not_apply"), "regulatory",
                          "The counteroffer's outcome is not yet determined (no express acceptance or use, and the 90-day period has not run)." if pending else
                          "The applicant did not accept or use the counteroffer, so it is adverse action (1002.2(c)(1)(i))." if adverse else "The applicant accepted the counteroffer, so there is no adverse action (1002.2(c)(1)(i))."))
        if pending:
            missing.append({"field": "counteroffer.accepted / review_date", "reason": "acceptance or the passing of 90 days decides whether adverse action occurred"})
    elif decision == "closed_incomplete":
        adverse = bool((case.get("notice") or {}).get("sent"))
    else:
        adverse = False
    if decision != "counteroffer":
        rules.append(rule("ECOA-ADVERSE-ACTION", "applies" if adverse else "does_not_apply", "regulatory",
                          f"Decision '{decision}' {'is' if adverse else 'is not'} adverse action as defined in 1002.2(c)."))
    ev["adverse_action"] = adverse

    rules.extend(_timing(case, decision, adverse, t, missing))
    _content(case, decision, adverse, t, missing, rules)
    if adverse and case.get("joint_application") and (case.get("notice") or {}).get("sent"):
        to = case["notice"].get("delivered_to")
        if to is None:
            missing.append({"field": "notice.delivered_to", "reason": "needed to apply 1002.9(f) (notice to the primary applicant)"})
        rules.append(rule("ECOA-NOTICE-RECIPIENT", "unable_to_determine" if to is None else ("satisfied" if to == "primary" else "not_satisfied"), "regulatory",
                          "With multiple applicants, notice must go to the primary applicant where one is readily apparent (1002.9(f))."))
    _other_rules(case, missing, rules)

    outcomes = {r["outcome"] for r in rules}
    if "not_satisfied" in outcomes:
        result = "Non-Compliant"
    elif outcomes & {"unable_to_determine", "review_required"}:
        result = "Potential Issue"
    else:
        result = "Compliant"
    base["ecoa_evaluation"] = ev
    finalize(base, classification, "Determined", result)
    validate_instance(base, pack.decision_schema, "ECOA decision record")
    return base

"""Deterministic flood-insurance evaluator (FCA, 12 CFR part 614 subpart S).

Never makes a flood-zone determination: `sfha.in_sfha` is a supplied fact from the standard FEMA form.
From supplied facts it decides:
  * use, retention and timing of the standard flood hazard determination (614.4940);
  * whether the loan is a "designated loan" (building or mobile home in an SFHA where insurance is
    available, 614.4925) and so whether flood insurance is required (614.4930);
  * the required amount: lesser of outstanding principal and the maximum available coverage (614.4930(a)),
    acceptable policy types (614.4930(c)), and coverage in force at the transaction;
  * the notice of special flood hazards: six content elements, borrower before completion, servicer, record
    retained (614.4955); escrow of premiums with its exceptions (614.4935);
  * force placement after a lapse or shortfall: notify, then purchase if not cured in 45 days (614.4945(a)).
"Reasonable time" for the notice is read as: delivered on a date before the transaction date; same-day delivery
is Review Required (an interpretation, flagged for compliance review).
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from compliance_common.decision import base_record, finalize, rule
from compliance_common.pack import EvaluatorValidationError, Pack, as_date, load_pack, threshold_record, validate_instance

EVALUATOR_VERSION = "0.1.0"
PACK_DIR = Path(__file__).resolve().parent / "pack"
NOTICE_ITEMS = {
    "warning": "the FEMA-approved warning (614.4955(b)(1))",
    "purchase_requirement_description": "a description of the purchase requirement (b)(2)",
    "nfip_private_availability": "that coverage is available from NFIP-participating insurers or the NFIP (b)(3)",
    "same_coverage_private_statement": "that equivalent private coverage may be available (b)(4)",
    "compare_policies_statement": "the encouragement to compare policies (b)(5)",
    "disaster_relief_statement": "whether Federal disaster relief may be available (b)(6)",
}
ESCROW_EXCEPTION_PURPOSES = {"business", "commercial", "agricultural"}


def _pack() -> Pack:
    return load_pack("fzd", PACK_DIR, ("thresholds",))


def validate_fzd_rule_pack() -> None:
    _pack()


def validate_fzd_decision_record(record: dict[str, Any]) -> None:
    validate_instance(record, _pack().decision_schema, "FZD decision record")


def _determination(case: dict[str, Any], transaction, rules: list, missing: list) -> str:
    """Return 'ok', 'defective' or 'unknown'."""
    det = case.get("determination") or {}
    keys = ("completed", "standard_form_used", "retained")
    unknown = [k for k in keys if det.get(k) is None] + ([] if det.get("date") else ["date"])
    for k in unknown:
        missing.append({"field": f"determination.{k}", "reason": "needed to test the standard flood hazard determination (614.4940)"})
    problems = [k for k in keys if det.get(k) is False]
    when = as_date(det["date"], "determination.date") if det.get("date") else None
    if when and when > transaction:
        problems.append("dated after the transaction")
    if problems:
        rules.append(rule("FZD-DETERMINATION", "not_satisfied", "regulatory",
                          "The standard flood hazard determination is deficient (" + ", ".join(p.replace("_", " ") for p in problems) + ") (614.4940)."))
        return "defective"
    if unknown:
        rules.append(rule("FZD-DETERMINATION", "unable_to_determine", "regulatory", "Determination facts are missing; see missing_facts."))
        return "unknown"
    rules.append(rule("FZD-DETERMINATION", "satisfied", "regulatory", "A completed standard FEMA flood hazard determination was obtained before the transaction and is retained (614.4940)."))
    return "ok"


def _insurance(case: dict[str, Any], transaction, rules: list, missing: list, ev: dict) -> None:
    ins = case.get("insurance") or {}
    balance, cap = case.get("loan_balance"), ins.get("max_available_coverage")
    if ins.get("type") in (None, "none") or ins.get("in_force") is False:
        rules.append(rule("FZD-INSURANCE", "not_satisfied", "regulatory", "No flood insurance is in force on a designated loan (614.4930(a))."))
        return
    absent = [k for k, v in (("loan_balance", balance), ("insurance.max_available_coverage", cap), ("insurance.coverage_amount", ins.get("coverage_amount")),
                             ("insurance.effective_date", ins.get("effective_date")), ("insurance.expiration_date", ins.get("expiration_date"))) if v is None]
    for k in absent:
        missing.append({"field": k, "reason": "needed to test the flood insurance amount and term (614.4930(a))"})
    if absent:
        rules.append(rule("FZD-INSURANCE", "unable_to_determine", "regulatory", "Facts needed to test the amount and term of coverage are missing."))
        return
    required = min(Decimal(str(balance)), Decimal(str(cap)))
    coverage = Decimal(str(ins["coverage_amount"]))
    ev["required_coverage"], ev["coverage_amount"] = str(required), str(coverage)
    problems = []
    if coverage < required:
        problems.append(f"coverage {coverage} is below the required {required} (lesser of principal {balance} and maximum available {cap})")
    if not as_date(ins["effective_date"], "effective_date") <= transaction <= as_date(ins["expiration_date"], "expiration_date"):
        problems.append("the policy term does not cover the transaction date")
    kind = ins["type"]
    if kind == "private_discretionary" and not ins.get("discretionary_sufficiency_documented"):
        problems.append("discretionary acceptance of a private policy needs a written sufficiency conclusion (614.4930(c)(3)(iv))")
    if kind == "mutual_aid" and not ins.get("mutual_aid_fca_determination"):
        problems.append("a mutual aid plan needs an FCA determination that it qualifies (614.4930(c)(4)(i))")
    rules.append(rule("FZD-INSURANCE", "not_satisfied" if problems else "satisfied", "regulatory",
                      ("; ".join(problems).capitalize() + " (614.4930).") if problems else f"Coverage of {coverage} meets the required {required} for the transaction date (614.4930(a)).",
                      value=str(coverage), threshold=str(required), operator="gte"))


def _notice(case: dict[str, Any], transaction, rules: list, missing: list) -> None:
    n = case.get("notice") or {}
    if not n.get("borrower_date"):
        missing.append({"field": "notice.borrower_date", "reason": "a notice of special flood hazards is required whenever the collateral is in an SFHA (614.4955(a)); its date is not recorded"})
        rules.append(rule("FZD-NOTICE", "unable_to_determine", "regulatory", "No borrower notice date is recorded for a loan secured by collateral in an SFHA (614.4955(a))."))
        return
    sent = as_date(n["borrower_date"], "notice.borrower_date")
    contents = n.get("contents") or {}
    problems = [f"missing {NOTICE_ITEMS[k]}" for k in NOTICE_ITEMS if contents.get(k) is False]
    unknown = [f"notice.contents.{k}" for k in NOTICE_ITEMS if contents.get(k) is None]
    if sent > transaction:
        problems.append("delivered after the transaction")
    if n.get("servicer_date") is None:
        unknown.append("notice.servicer_date")
    if n.get("record_retained") is False:
        problems.append("no record of receipt retained (614.4955(d))")
    elif n.get("record_retained") is None:
        unknown.append("notice.record_retained")
    for field in unknown:
        missing.append({"field": field, "reason": "needed to test the notice of special flood hazards (614.4955)"})
    if problems:
        outcome, text = "not_satisfied", "Notice of special flood hazards is deficient: " + "; ".join(problems) + "."
    elif unknown:
        outcome, text = "unable_to_determine", "Some notice-content, servicer or record facts are not recorded."
    elif sent == transaction:
        outcome, text = "review_required", "Notice was delivered on the transaction date; whether that is 'a reasonable time before completion' needs reviewer judgment (614.4955(c))."
    else:
        outcome, text = "satisfied", f"Notice with all six elements was delivered {sent}, before the transaction on {transaction}, and sent to the servicer (614.4955)."
    rules.append(rule("FZD-NOTICE", outcome, "regulatory", text))


def _escrow(case: dict[str, Any], transaction, t: dict[str, Any], rules: list, missing: list) -> None:
    coll, esc = case.get("collateral") or {}, case.get("escrow") or {}
    if not coll.get("residential") or transaction < as_date(t["escrow_effective_date"], "escrow_effective_date"):
        rules.append(rule("FZD-ESCROW", "does_not_apply", "regulatory", "Escrow applies to residential improved real estate or a mobile home for transactions on or after 2016-01-01 (614.4935(a)(1))."))
        return
    reasons = []
    if case.get("credit_purpose") in ESCROW_EXCEPTION_PURPOSES:
        reasons.append("business, commercial or agricultural purpose (614.4935(a)(2)(i))")
    if case.get("lien_position") == "subordinate" and case.get("senior_lien_flood_insured"):
        reasons.append("subordinate lien with the senior lien flood-insured (a)(2)(ii)")
    if (case.get("insurance") or {}).get("condo_master_policy"):
        reasons.append("association master policy (a)(2)(iii)")
    if case.get("heloc"):
        reasons.append("home equity line of credit (a)(2)(iv)")
    if case.get("nonperforming_90_days"):
        reasons.append("nonperforming loan (a)(2)(v)")
    if case.get("term_months") is not None and case["term_months"] <= 12:
        reasons.append("term of 12 months or less (a)(2)(vi)")
    if esc.get("small_lender_exception"):
        reasons.append("small lender exception (614.4935(c))")
    if reasons:
        rules.append(rule("FZD-ESCROW", "does_not_apply", "regulatory", "Escrow exception: " + "; ".join(reasons) + "."))
        return
    if case.get("credit_purpose") is None:
        missing.append({"field": "credit_purpose", "reason": "needed to test the business/commercial/agricultural escrow exception (614.4935(a)(2)(i))"})
        rules.append(rule("FZD-ESCROW", "unable_to_determine", "regulatory", "The credit purpose is not recorded, so the escrow exception cannot be ruled out."))
        return
    escrowed = esc.get("escrowed")
    if escrowed is None:
        missing.append({"field": "escrow.escrowed", "reason": "needed to test 614.4935(a)(1)"})
    rules.append(rule("FZD-ESCROW", "unable_to_determine" if escrowed is None else ("satisfied" if escrowed else "not_satisfied"), "regulatory",
                      "Flood insurance premiums and fees must be escrowed for this designated loan (614.4935(a)(1))."))


def _monitoring(case: dict[str, Any], t: dict[str, Any], rules: list, missing: list) -> None:
    m = case.get("monitoring") or {}
    if not m.get("lapse_or_shortfall_detected"):
        rules.append(rule("FZD-FORCE-PLACEMENT", "does_not_apply", "regulatory", "No lapse or coverage shortfall is recorded."))
        return
    if not m.get("borrower_notified_date") or not m.get("review_date"):
        missing.append({"field": "monitoring.borrower_notified_date / review_date", "reason": "needed to test force placement (614.4945(a))"})
        rules.append(rule("FZD-FORCE-PLACEMENT", "unable_to_determine", "regulatory", "A lapse is recorded but the borrower-notice date or the review date is missing."))
        return
    notified, review = as_date(m["borrower_notified_date"], "borrower_notified_date"), as_date(m["review_date"], "review_date")
    due = notified + timedelta(days=t["force_placement_days"])
    if m.get("coverage_restored_date") and as_date(m["coverage_restored_date"], "coverage_restored_date") <= due:
        rules.append(rule("FZD-FORCE-PLACEMENT", "satisfied", "regulatory", "The borrower cured the lapse within 45 days of notification (614.4945(a))."))
    elif review <= due:
        rules.append(rule("FZD-FORCE-PLACEMENT", "satisfied", "regulatory", f"Borrower notified {notified}; the 45-day period runs to {due} and has not expired at review {review} (614.4945(a))."))
    elif m.get("force_placed_date"):
        rules.append(rule("FZD-FORCE-PLACEMENT", "satisfied", "regulatory", f"Insurance was force-placed {m['force_placed_date']} after the 45-day period ended {due} (614.4945(a))."))
    else:
        rules.append(rule("FZD-FORCE-PLACEMENT", "not_satisfied", "regulatory", f"The 45-day period ended {due} without cure and no force-placed coverage is recorded (614.4945(a)).",
                          value=review.isoformat(), threshold=due.isoformat(), operator="lte"))


def evaluate_fzd(case: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a canonical flood case without network or model calls."""
    if not isinstance(case, dict):
        raise EvaluatorValidationError("FZD input must be an object")
    pack = _pack()
    validate_instance(case, pack.input_schema, "canonical FZD input")
    t = pack.files["thresholds"]
    transaction = as_date(case["transaction_date"], "transaction_date")
    base = base_record("fzd", EVALUATOR_VERSION, pack, case, transaction)
    facts, missing, rules = base["facts_used"], base["missing_facts"], base["rule_results"]
    ev: dict[str, Any] = {"transaction_type": case["transaction_type"]}
    base["threshold_record"] = threshold_record(pack.files["thresholds"], transaction)

    def done(classification: str, status: str, result: str) -> dict[str, Any]:
        base["fzd_evaluation"] = ev
        finalize(base, classification, status, result)
        validate_instance(base, pack.decision_schema, "FZD decision record")
        return base

    structure = (case.get("collateral") or {}).get("structure")
    if structure is None:
        missing.append({"field": "collateral.structure", "reason": "needed to know whether a building or mobile home secures the loan"})
        rules.append(rule("FZD-APPLICABILITY", "unable_to_determine", "regulatory", "Whether a building or mobile home secures the loan is not recorded."))
        return done("Unable To Determine", "Unable To Determine", "Unable To Determine")
    if structure == "none":
        rules.append(rule("FZD-APPLICABILITY", "does_not_apply", "regulatory", "No building or mobile home secures the loan, so it is not a designated loan (614.4925)."))
        return done("Flood Insurance Not Required", "Determined", "Not Applicable")

    verdict = _determination(case, transaction, rules, missing)
    sfha = case.get("sfha") or {}
    in_sfha, available = sfha.get("in_sfha"), sfha.get("flood_insurance_available")
    if verdict == "defective":
        rules.append(rule("FZD-APPLICABILITY", "review_required", "regulatory", "SFHA status cannot be relied on because the determination is deficient."))
        return done("Potential Flood Compliance Issue", "Review Required", "Non-Compliant")
    if verdict == "unknown" or in_sfha is None:
        if in_sfha is None:
            missing.append({"field": "sfha.in_sfha", "reason": "SFHA status from the standard determination form is required"})
        rules.append(rule("FZD-APPLICABILITY", "unable_to_determine", "regulatory", "The determination or SFHA status is not available, so flood requirements cannot be decided."))
        return done("Unable To Determine", "Unable To Determine", "Unable To Determine")
    facts.append({"field": "sfha.in_sfha", "value": in_sfha})
    if not in_sfha:
        rules.append(rule("FZD-APPLICABILITY", "does_not_apply", "regulatory", "The collateral is not in a special flood hazard area; flood insurance and the SFHA notice are not required."))
        return done("Flood Insurance Not Required", "Determined", "Not Applicable")

    designated = available is True
    if available is None:
        missing.append({"field": "sfha.flood_insurance_available", "reason": "insurance must be available under the 1968 Act for a designated loan (614.4925)"})
    rules.append(rule("FZD-APPLICABILITY", "applies" if designated else ("does_not_apply" if available is False else "unable_to_determine"), "regulatory",
                      "Building or mobile home in an SFHA where insurance is available: a designated loan (614.4925)." if designated else
                      "In an SFHA but insurance is not available under the 1968 Act, so not a designated loan; the SFHA notice is still required (614.4955(a))." if available is False
                      else "Whether insurance is available under the 1968 Act is not recorded."))
    if available is None:
        return done("Unable To Determine", "Unable To Determine", "Unable To Determine")
    _notice(case, transaction, rules, missing)
    if designated:
        _insurance(case, transaction, rules, missing, ev)
        _escrow(case, transaction, t, rules, missing)
        _monitoring(case, t, rules, missing)
    outcomes = {r["outcome"] for r in rules}
    result = "Non-Compliant" if "not_satisfied" in outcomes else ("Potential Issue" if outcomes & {"unable_to_determine", "review_required"} else "Compliant")
    classification = "Flood Insurance Required" if designated else "Flood Insurance Not Required"
    return done(classification, "Determined", result)

"""Deterministic HMDA (Regulation C, 12 CFR part 1003) evaluator.

Decides, from supplied facts only:
  * coverage: institution, excluded transactions (1003.3(c)), agricultural / business-purpose
    exclusions, and the origination-volume thresholds;
  * for covered transactions: action-taken validity and chronology (1003.4(a)(8)), the rate spread
    recomputed as APR - APOR (1003.4(a)(12)), partial-exemption eligibility (1003.3(d)), and ALL 38 LAR
    items of 1003.4(a), each with its own applicability, presence and value checks (see lar.py).
Judgment calls (primary agricultural / business purpose) are input facts: "undetermined" yields
Potentially Covered, never a guess.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from compliance_common.decision import base_record, finalize, rule
from compliance_common.pack import EvaluatorValidationError, Pack, as_date, load_pack, validate_instance

from .lar import evaluate_items, partial_exemption_status

EVALUATOR_VERSION = "0.2.0"
PACK_DIR = Path(__file__).resolve().parent / "pack"
RATE_SPREAD_ACTIONS = {"originated", "approved_not_accepted"}
_EXCLUSION_CITES = {
    "fiduciary_capacity": "1003.3(c)(1)", "unimproved_land": "1003.3(c)(2)", "temporary_financing": "1003.3(c)(3)",
    "pool_interest_purchase": "1003.3(c)(4)", "servicing_rights_purchase": "1003.3(c)(5)",
    "merger_acquisition_purchase": "1003.3(c)(6)", "partial_interest_purchase": "1003.3(c)(8)",
    "ny_supplemental_consolidation": "1003.3(c)(13)",
}


def _pack() -> Pack:
    return load_pack("hmda", PACK_DIR, ("thresholds", "lar_items", "appendix_b"))


def validate_hmda_rule_pack() -> None:
    _pack()


def validate_hmda_decision_record(record: dict[str, Any]) -> None:
    validate_instance(record, _pack().decision_schema, "HMDA decision record")


def _coverage(case: dict[str, Any], t: dict[str, Any], rules: list, facts: list, missing: list) -> str:
    """Return 'Covered', 'Not Covered', 'Potentially Covered' or 'Unable To Determine'."""
    facts.append({"field": "financial_institution", "value": case["financial_institution"]})
    if not case["financial_institution"]:
        rules.append(rule("HMDA-INSTITUTION", "does_not_apply", "regulatory", "The institution is not a financial institution under 1003.2(g) (or is exempt), so Regulation C does not apply."))
        return "Not Covered"
    rules.append(rule("HMDA-INSTITUTION", "applies", "regulatory", "The institution is a financial institution under 1003.2(g)."))

    structure = case["credit_structure"]
    if not case["secured_by_dwelling"]:
        rules.append(rule("HMDA-DWELLING", "does_not_apply", "regulatory", "Not secured by a lien on a dwelling, so not a closed-end mortgage loan or open-end line of credit (1003.2(d), (o))."))
        return "Not Covered"
    rules.append(rule("HMDA-DWELLING", "applies", "regulatory", "Secured by a lien on a dwelling (1003.2(d), (o))."))

    unknown, excluded = False, False
    flags = case.get("exclusions") or {}
    for key, cite in _EXCLUSION_CITES.items():
        value = flags.get(key)
        if value is None:
            missing.append({"field": f"exclusions.{key}", "reason": f"needed to test excluded transaction {cite}"})
            unknown = True
        elif value:
            rules.append(rule(f"HMDA-EXCL-{key.upper().replace('_', '-')}", "applies", "regulatory", f"Excluded transaction under {cite}."))
            excluded = True
    amount = Decimal(str(case["amount"]))
    if amount < t["minimum_amount"]:
        rules.append(rule("HMDA-EXCL-AMOUNT", "applies", "regulatory", f"Total dollar amount {amount} is less than {t['minimum_amount']} (1003.3(c)(7)).", value=str(amount), threshold=str(t["minimum_amount"]), operator="lt"))
        excluded = True
    if excluded:
        return "Not Covered"

    purpose, agri, business = case.get("loan_purpose"), case.get("agricultural_purpose"), case.get("business_commercial_purpose")
    if agri is None:
        missing.append({"field": "agricultural_purpose", "reason": "needed to test the agricultural-purpose exclusion (1003.3(c)(9))"})
        unknown = True
    if business is None:
        missing.append({"field": "business_commercial_purpose", "reason": "needed to test the business-purpose exclusion (1003.3(c)(10))"})
        unknown = True
    if agri == "primarily":
        rules.append(rule("HMDA-EXCL-AGRICULTURAL", "applies", "regulatory", "Used primarily for agricultural purposes (1003.3(c)(9))."))
        return "Not Covered"
    if business == "primarily":
        if purpose in t["business_purpose_covered_purposes"]:
            rules.append(rule("HMDA-EXCL-BUSINESS", "does_not_apply", "regulatory", f"Business or commercial purpose, but a {purpose} loan stays covered (1003.3(c)(10))."))
        elif purpose is None:
            missing.append({"field": "loan_purpose", "reason": "needed because a business-purpose loan is covered only if home purchase, home improvement or refinancing"})
            unknown = True
        else:
            rules.append(rule("HMDA-EXCL-BUSINESS", "applies", "regulatory", "Primarily business or commercial purpose and not a home purchase, home improvement or refinancing (1003.3(c)(10))."))
            return "Not Covered"
    vol = case.get("prior_year_originations") or {}
    limit = t["closed_end_minimum_originations"] if structure == "closed_end" else t["open_end_minimum_originations"]
    counts = vol.get(structure)
    cite = "1003.3(c)(11)" if structure == "closed_end" else "1003.3(c)(12)"
    if counts is None:
        missing.append({"field": f"prior_year_originations.{structure}", "reason": f"needed to test the volume exclusion {cite}"})
        unknown = True
    elif min(counts) < limit:
        rules.append(rule("HMDA-EXCL-VOLUME", "applies", "regulatory", f"Fewer than {limit} {structure.replace('_', '-')} originations in one of the two preceding calendar years ({cite}).", value=min(counts), threshold=limit, operator="lt"))
        return "Not Covered"
    if unknown:
        rules.append(rule("HMDA-COVERAGE", "unable_to_determine", "regulatory", "Coverage cannot be settled from the facts supplied; see missing_facts."))
        return "Unable To Determine"
    if "undetermined" in (agri, business):
        rules.append(rule("HMDA-COVERAGE", "review_required", "regulatory", "The primary agricultural or business purpose is undetermined; an exclusion under 1003.3(c)(9) or (10) may apply."))
        return "Potentially Covered"
    rules.append(rule("HMDA-COVERAGE", "applies", "regulatory", "No exclusion under 1003.3(c) applies; the transaction is a covered loan (1003.2(e))."))
    return "Covered"


def _reporting(case: dict[str, Any], pack: Pack, rules: list, facts: list, missing: list, ev: dict) -> None:
    t, action = pack.files["thresholds"], case["action_taken"]
    # Action taken and chronology (1003.4(a)(8))
    facts.append({"field": "action_taken", "value": action})
    action_date = as_date(case["action_taken_date"], "action_taken_date")
    app_raw = case.get("application_date")
    if action == "purchased":
        rules.append(rule("HMDA-ACTION", "satisfied", "regulatory", "Purchased loan; action taken recorded with its date (1003.4(a)(8))."))
    elif app_raw is None:
        missing.append({"field": "application_date", "reason": "required to validate the action chronology (1003.4(a)(1)(ii))"})
        rules.append(rule("HMDA-ACTION", "unable_to_determine", "regulatory", "Application date is missing, so the action chronology cannot be validated."))
    else:
        app = as_date(app_raw, "application_date")
        facts.append({"field": "application_date", "value": app_raw})
        ok = action_date >= app
        rules.append(rule("HMDA-ACTION", "satisfied" if ok else "not_satisfied", "regulatory",
                          f"Action ({action}) dated {action_date} {'is on or after' if ok else 'PRECEDES'} the application date {app} (1003.4(a)(8))."))
    # Rate spread (1003.4(a)(12)): APR - APOR, only for originated / approved-not-accepted loans subject to Regulation Z
    applicable = (action in RATE_SPREAD_ACTIONS and case.get("subject_to_reg_z", True)
                  and not case.get("assumption", False) and not case.get("reverse_mortgage", False))
    reported = case.get("reported_rate_spread")
    exempt, _ = partial_exemption_status(case, pack.files["lar_items"])
    if applicable and exempt and reported is None:
        rules.append(rule("HMDA-RATE-SPREAD", "does_not_apply", "regulatory", "Rate spread is optional data for a validly partially exempt institution and none was reported (1003.3(d)(1)(iii))."))
    elif not applicable:
        ok = reported is None
        rules.append(rule("HMDA-RATE-SPREAD", "does_not_apply" if ok else "not_satisfied", "regulatory",
                          "Rate spread is not applicable to this action or transaction type (1003.4(a)(12))." if ok else
                          f"A rate spread of {reported} was reported but is not applicable to this action or transaction type (1003.4(a)(12))."))
    elif case.get("apr") is None or case.get("apor") is None:
        missing.append({"field": "apr/apor", "reason": "APR and the APOR (with apor_reference) are required to compute the rate spread (1003.4(a)(12)); use `python -m intake.apor`"})
        rules.append(rule("HMDA-RATE-SPREAD", "unable_to_determine", "regulatory", "APR or APOR is missing, so the rate spread cannot be computed."))
    else:
        computed = (Decimal(str(case["apr"])) - Decimal(str(case["apor"]))).quantize(Decimal("0.001"))
        ev["rate_spread_computed"], ev["apor_reference"] = str(computed), case.get("apor_reference")
        facts.extend([{"field": "apr", "value": case["apr"]}, {"field": "apor", "value": case["apor"]}])
        if reported is None:
            missing.append({"field": "reported_rate_spread", "reason": "the LAR rate spread is not supplied; computed value shown"})
            rules.append(rule("HMDA-RATE-SPREAD", "unable_to_determine", "regulatory", f"No reported rate spread supplied; APR minus APOR is {computed}."))
        else:
            ok = Decimal(str(reported)).quantize(Decimal("0.001")) == computed
            rules.append(rule("HMDA-RATE-SPREAD", "satisfied" if ok else "not_satisfied", "regulatory",
                              f"Reported rate spread {reported} {'matches' if ok else 'DIFFERS FROM'} APR minus APOR = {computed} (1003.4(a)(12)).",
                              value=str(reported), threshold=str(computed), operator="eq"))
    # The 38 LAR items of 1003.4(a)
    rs_rule = next(r for r in rules if r["rule_id"] == "HMDA-RATE-SPREAD")
    items, exemption = evaluate_items(case, pack.files["lar_items"], pack.files["appendix_b"], rs_rule["outcome"], rs_rule["message"])
    if (case.get("lar_context") or {}).get("partial_exemption"):
        ok = exemption["partial_exemption_applied"]
        rules.append(rule("HMDA-PARTIAL-EXEMPTION", "satisfied" if ok else ("unable_to_determine" if "needed" in exemption["partial_exemption_note"] else "not_satisfied"), "regulatory",
                          "A valid partial exemption removes the optional data items (1003.3(d))." if ok else f"The claimed partial exemption is not valid: {exemption['partial_exemption_note']}."))
    names = {m["number"]: m for m in pack.files["lar_items"]["items"]}
    for item in items:
        if item.status in ("not_satisfied", "unable"):
            rules.append(rule(f"HMDA-LAR-{item.number:02d}", "not_satisfied" if item.status == "not_satisfied" else "unable_to_determine", "regulatory", item.message))
            for field in item.missing:
                missing.append({"field": field, "reason": f"needed for LAR item {item.number} ({names[item.number]['name']}) {names[item.number]['cite']}; absence from the input is not proof it is absent from the register"})
    counts = {k: sum(1 for i in items if i.status == k) for k in ("satisfied", "not_satisfied", "unable", "not_applicable", "exempt")}
    ev["lar_items"] = {str(i.number): i.status for i in items}
    ev["lar_summary"] = counts
    aggregate = "not_satisfied" if counts["not_satisfied"] else ("unable_to_determine" if counts["unable"] else "satisfied")
    rules.append(rule("HMDA-LAR-ITEMS", aggregate, "regulatory",
                      f"Of the 38 LAR items in 1003.4(a): {counts['satisfied']} satisfied, {counts['not_satisfied']} not satisfied, {counts['unable']} cannot be determined from the input, "
                      f"{counts['not_applicable']} not applicable, {counts['exempt']} exempt."))


def evaluate_hmda(case: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a canonical HMDA case without network or model calls."""
    if not isinstance(case, dict):
        raise EvaluatorValidationError("HMDA input must be an object")
    pack = _pack()
    validate_instance(case, pack.input_schema, "canonical HMDA input")
    t = pack.files["thresholds"]
    as_of = as_date(case["action_taken_date"], "action_taken_date")
    base = base_record("hmda", EVALUATOR_VERSION, pack, case, as_of)
    facts, missing, rules = base["facts_used"], base["missing_facts"], base["rule_results"]
    ev: dict[str, Any] = {}
    classification = _coverage(case, t, rules, facts, missing)
    if classification in ("Covered", "Potentially Covered"):    # reporting checks apply if coverage is confirmed
        _reporting(case, pack, rules, facts, missing, ev)
    outcomes = {r["outcome"] for r in rules}
    if classification == "Not Covered":
        status, result = "Determined", "Not Applicable"
    elif classification == "Potentially Covered":
        status, result = "Review Required", "Potential Issue"      # coverage must be settled first; reporting rule outcomes apply if covered
    elif classification == "Unable To Determine":
        status, result = "Unable To Determine", "Unable To Determine"
    else:
        status = "Determined"
        result = "Non-Compliant" if "not_satisfied" in outcomes else ("Potential Issue" if "unable_to_determine" in outcomes else "Compliant")
    base["hmda_evaluation"] = ev
    finalize(base, classification, status, result)
    validate_instance(base, pack.decision_schema, "HMDA decision record")
    return base

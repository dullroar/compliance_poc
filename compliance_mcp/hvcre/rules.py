"""Deterministic HVCRE evaluator (FCA capital rule, 12 CFR 628.2, definition of HVCRE exposure).

Follows the pinned text of the definition:
  (1) the three-prong test: primarily finances ADC, purpose of income-producing real property, repayment
      dependent on future income, sales proceeds or refinancing;
  (2) exclusions: (i)(A) 1-4 family residential with the dwelling >= 50% of collateral value (not pure land
      improvements), (i)(C) agricultural land for bona fide farmers (not farm construction / land development),
      (ii) acquisition or refinance of existing income-producing property with sufficient cash flow,
      (iii) improvements to existing income-producing property with sufficient cash flow,
      (iv) projects with LTV <= the Appendix A limit AND borrower capital >= 15% of the "as completed" value
      contributed before advances and contractually retained, (v) loans originated under $500,000;
  (3) loans made before 2025-01-01 are not HVCRE exposures; (4)/(6) reclassified credit facilities are not.
The Appendix A LTV limit is NOT pinned in this pack; it is a supplied input with its source, and the capital
exclusion is Unable To Determine without it. The evaluator does not assign capital or judge appraisals.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

from compliance_common.decision import base_record, finalize, rule
from compliance_common.pack import EvaluatorValidationError, Pack, as_date, load_pack, validate_instance

EVALUATOR_VERSION = "0.1.0"
PACK_DIR = Path(__file__).resolve().parent / "pack"
PRONGS = (
    ("primarily_finances_adc", "primarily finances, has financed or refinances the acquisition, development or construction of real property (1)(i)"),
    ("purpose_income_producing", "has the purpose of providing financing to acquire, develop or improve the property into income-producing real property (1)(ii)"),
    ("dependent_on_future_income_or_sales", "is dependent upon future income, sales proceeds or refinancing of the property for repayment (1)(iii)"),
)


def _pack() -> Pack:
    return load_pack("hvcre", PACK_DIR, ("thresholds",))


def validate_hvcre_rule_pack() -> None:
    _pack()


def validate_hvcre_decision_record(record: dict[str, Any]) -> None:
    validate_instance(record, _pack().decision_schema, "HVCRE decision record")


def _exclusions(case: dict[str, Any], t: dict[str, Any], missing: list, ev: dict) -> list[dict[str, Any]]:
    prop, cap = case.get("property") or {}, case.get("capital") or {}
    out = []

    def add(rid: str, state: str, text: str, **extra: Any) -> None:
        out.append(rule(rid, state, "regulatory", text, **extra))

    # (2)(i)(A) one- to four-family residential
    one4 = prop.get("one_to_four_family_residential")
    if one4 is None:
        missing.append({"field": "property.one_to_four_family_residential", "reason": "needed for exclusion (2)(i)(A)"})
        add("HVCRE-EXCL-RESIDENTIAL", "unable_to_determine", "Whether the property is one- to four-family residential is not recorded.")
    elif not one4:
        add("HVCRE-EXCL-RESIDENTIAL", "does_not_apply", "Not a one- to four-family residential property (2)(i)(A).")
    elif prop.get("finances_only_land_improvements"):
        add("HVCRE-EXCL-RESIDENTIAL", "does_not_apply", "The facility solely finances land improvements such as sewers and water pipes, which do not qualify for the residential exclusion (2)(i)(A).")
    elif prop.get("dwelling_percent_of_collateral_value") is None:
        missing.append({"field": "property.dwelling_percent_of_collateral_value", "reason": "the dwelling must be at least 50% of total appraised collateral value (2)(i)(A)"})
        add("HVCRE-EXCL-RESIDENTIAL", "unable_to_determine", "The dwelling's share of the appraised collateral value is not recorded.")
    else:
        pct = Decimal(str(prop["dwelling_percent_of_collateral_value"]))
        ok = pct >= t["dwelling_minimum_percent"]
        add("HVCRE-EXCL-RESIDENTIAL", "applies" if ok else "does_not_apply",
            f"Dwelling is {pct}% of appraised collateral value; the exclusion needs at least {t['dwelling_minimum_percent']}% (2)(i)(A).", value=str(pct), threshold=str(t["dwelling_minimum_percent"]), operator="gte")
    # (2)(i)(C) agricultural land
    agri = prop.get("agricultural_land_bona_fide_farmer")
    if agri is None:
        missing.append({"field": "property.agricultural_land_bona_fide_farmer", "reason": "needed for exclusion (2)(i)(C)"})
        add("HVCRE-EXCL-AGRICULTURAL", "unable_to_determine", "Whether this finances agricultural land for a bona fide farmer, rancher or producer is not recorded.")
    elif not agri:
        add("HVCRE-EXCL-AGRICULTURAL", "does_not_apply", "Not financing for the agricultural needs of a bona fide farmer (2)(i)(C).")
    elif prop.get("farm_property_construction_or_land_development"):
        add("HVCRE-EXCL-AGRICULTURAL", "does_not_apply", "The agricultural exclusion does not apply to loans for farm property construction and land development (2)(i)(C).")
    else:
        add("HVCRE-EXCL-AGRICULTURAL", "applies", "Financing for the agricultural needs of a bona fide farmer, not farm construction or land development (2)(i)(C).")
    # (2)(ii) / (iii) existing income-producing property
    for rid, key, cite, label in (("HVCRE-EXCL-EXISTING-INCOME", "existing_income_producing", "(2)(ii)", "acquisition or refinance of existing income-producing property"),
                                  ("HVCRE-EXCL-EXISTING-IMPROVEMENTS", "improvement_to_existing_income_producing", "(2)(iii)", "improvements to existing income-producing improved property")):
        flag, cash = prop.get(key), prop.get("cash_flow_sufficient_for_permanent")
        if flag is None:
            missing.append({"field": f"property.{key}", "reason": f"needed for exclusion {cite}"})
            add(rid, "unable_to_determine", f"Whether this is {label} is not recorded.")
        elif not flag:
            add(rid, "does_not_apply", f"Not {label} {cite}.")
        elif cash is None:
            missing.append({"field": "property.cash_flow_sufficient_for_permanent", "reason": f"exclusion {cite} needs cash flow sufficient under permanent-financing underwriting criteria"})
            add(rid, "unable_to_determine", f"This is {label} but cash-flow sufficiency is not recorded {cite}.")
        else:
            add(rid, "applies" if cash else "does_not_apply", f"{label.capitalize()}; cash flow {'is' if cash else 'is NOT'} sufficient to support debt service under permanent-financing criteria {cite}.")
    # (2)(iv) commercial real property project: LTV, 15% capital, timing, retention
    unknown, failed, notes = [], [], []
    ltv, limit = cap.get("ltv_ratio"), cap.get("ltv_limit")
    if ltv is None or limit is None:
        unknown.append("capital.ltv_ratio / capital.ltv_limit")
        missing.append({"field": "capital.ltv_ratio / capital.ltv_limit", "reason": "the Appendix A loan-to-value limit (with its source) is needed for exclusion (2)(iv)(A); it is not pinned in this pack"})
    elif Decimal(str(ltv)) > Decimal(str(limit)):
        failed.append(f"LTV {ltv}% exceeds the limit {limit}% (2)(iv)(A)")
    else:
        notes.append(f"LTV {ltv}% is within the limit {limit}%")
    value = cap.get("as_completed_value") if cap.get("as_completed_value") is not None else cap.get("as_is_value")
    contrib = cap.get("contributions") or {}
    if value is None or not contrib:
        unknown.append("capital.as_completed_value/contributions")
        missing.append({"field": "capital.as_completed_value / capital.contributions", "reason": "needed to test the 15% borrower capital contribution (2)(iv)(B)"})
    else:
        required = (Decimal(str(value)) * Decimal(str(t["minimum_capital_fraction"]))).quantize(Decimal("0.01"))
        actual = sum((Decimal(str(contrib.get(k, 0))) for k in ("cash", "marketable_assets", "paid_development_expenses", "contributed_real_property_appraised")), Decimal(0))
        ev["capital_required"], ev["capital_contributed"] = str(required), str(actual)
        if cap.get("as_completed_value") is None:
            notes.append("as-is value used because no as-completed value was supplied (permitted when unavailable)")
        if actual < required:
            failed.append(f"contributed capital {actual} is below 15% of value = {required} (2)(iv)(B)")
        else:
            notes.append(f"contributed capital {actual} meets 15% of value = {required}")
    for key, cite, text in (("contributed_before_advances", "(2)(iv)(C)", "capital was contributed before advances other than a nominal sum"),
                            ("contractually_retained_until_reclassified", "(2)(iv)(C)", "the minimum capital is contractually required to remain until reclassification")):
        if cap.get(key) is None:
            unknown.append(f"capital.{key}")
            missing.append({"field": f"capital.{key}", "reason": f"needed for exclusion {cite}"})
        elif not cap[key]:
            failed.append(f"not true that {text} {cite}")
    if failed:
        add("HVCRE-EXCL-CAPITAL", "does_not_apply", "Project exclusion (2)(iv) not met: " + "; ".join(failed) + ".")
    elif unknown:
        add("HVCRE-EXCL-CAPITAL", "unable_to_determine", "Project exclusion (2)(iv) cannot be tested; missing: " + ", ".join(unknown) + ".")
    else:
        add("HVCRE-EXCL-CAPITAL", "applies", "Project exclusion (2)(iv) met: " + "; ".join(notes) + ".")
    # (2)(v) small loans
    amount = case.get("credit_facility_amount")
    if amount is None:
        missing.append({"field": "credit_facility_amount", "reason": "needed for exclusion (2)(v)"})
        add("HVCRE-EXCL-SMALL-LOAN", "unable_to_determine", "The amount originated is not recorded.")
    else:
        small = Decimal(str(amount)) < t["small_loan_limit"]
        add("HVCRE-EXCL-SMALL-LOAN", "applies" if small else "does_not_apply",
            f"Loan originated for {amount}; loans under {t['small_loan_limit']} are excluded (2)(v).", value=str(amount), threshold=str(t["small_loan_limit"]), operator="lt")
    return out


def evaluate_hvcre(case: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a canonical HVCRE case without network or model calls."""
    if not isinstance(case, dict):
        raise EvaluatorValidationError("HVCRE input must be an object")
    pack = _pack()
    validate_instance(case, pack.input_schema, "canonical HVCRE input")
    t = pack.files["thresholds"]
    loan_date = as_date(case["loan_date"], "loan_date")
    base = base_record("hvcre", EVALUATOR_VERSION, pack, case, loan_date)
    facts, missing, rules = base["facts_used"], base["missing_facts"], base["rule_results"]
    ev: dict[str, Any] = {}

    def done(classification: str, status: str, result: str) -> dict[str, Any]:
        base["hvcre_evaluation"] = ev
        finalize(base, classification, status, result)
        validate_instance(base, pack.decision_schema, "HVCRE decision record")
        return base

    start = as_date(t["applies_to_loans_made_on_or_after"], "applies_to_loans_made_on_or_after")
    if loan_date < start:
        rules.append(rule("HVCRE-EFFECTIVE", "does_not_apply", "regulatory", f"Loan made {loan_date}: an HVCRE exposure does not include any loan made before {start} (definition paragraph (3)).", value=loan_date.isoformat(), threshold=start.isoformat(), operator="gte"))
        return done("Non-HVCRE", "Determined", "Compliant")
    rules.append(rule("HVCRE-EFFECTIVE", "applies", "regulatory", f"Loan made {loan_date}, on or after {start} (definition paragraph (3)).", value=loan_date.isoformat(), threshold=start.isoformat(), operator="gte"))
    if case.get("reclassified_to_non_hvcre"):
        rules.append(rule("HVCRE-RECLASSIFIED", "applies", "regulatory", "The credit facility was reclassified by the institution as a non-HVCRE exposure (definition paragraphs (4), (6))."))
        return done("Non-HVCRE", "Determined", "Compliant")
    prong_values = {key: case.get(key) for key, _ in PRONGS}
    for key, text in PRONGS:
        if prong_values[key] is None:
            missing.append({"field": key, "reason": "needed for the three-prong HVCRE test (1)"})
        else:
            facts.append({"field": key, "value": prong_values[key]})
    failed = [text for key, text in PRONGS if prong_values[key] is False]
    if failed:
        rules.append(rule("HVCRE-DEFINITION", "does_not_apply", "regulatory", "The facility does not meet the HVCRE definition: it does not satisfy: " + "; ".join(failed) + "."))
        return done("Non-HVCRE", "Determined", "Compliant")
    if any(v is None for v in prong_values.values()):
        rules.append(rule("HVCRE-DEFINITION", "unable_to_determine", "regulatory", "The three-prong test cannot be completed from the facts supplied."))
        return done("Unable To Determine", "Unable To Determine", "Unable To Determine")
    rules.append(rule("HVCRE-DEFINITION", "applies", "regulatory", "All three prongs of the HVCRE definition are met (1)."))
    exclusions = _exclusions(case, t, missing, ev)
    rules.extend(exclusions)
    states = {r["outcome"] for r in exclusions}
    if "applies" in states:
        names = ", ".join(r["rule_id"].replace("HVCRE-EXCL-", "") for r in exclusions if r["outcome"] == "applies")
        ev["exclusions_applied"] = names
        return done("Non-HVCRE", "Determined", "Compliant")
    if "unable_to_determine" in states:
        return done("Potential HVCRE", "Review Required", "Potential Issue")
    return done("HVCRE", "Determined", "Compliant")

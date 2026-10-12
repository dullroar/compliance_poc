"""HMDA loan/application register: all 38 items of 12 CFR 1003.4(a), item by item.

For each numbered item the evaluator decides, from the supplied `lar` values and `lar_context` flags, whether the item
applies to this action and loan, whether a value was supplied, and whether the value is valid:
  satisfied       applies, supplied and valid
  not_satisfied   applies but is missing a required piece, is reported "not applicable", or is invalid
  unable          applies (or may apply) but the input does not say enough to tell: an input that is absent is never
                  treated as proof that the fact is absent
  not_applicable  the item does not apply to this action or loan
  exempt          a valid partial exemption (1003.3(d)) removes the item (the "optional data" items)
Value domains come from the regulation text, Appendix B (ethnicity, race, sex) and Appendix C (ULI check digit) only. The
FFIEC Filing Instructions Guide code lists are not pinned in this pack, so free-form items (purchaser type, AUS name and
result, scoring model names) are checked for presence, not for membership in a code list.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

NA = "not_applicable"
NOT_PROVIDED = "information_not_provided"
ACTIONS_LOAN = ("originated", "purchased")
ACTIONS_PRICED = ("originated", "purchased", "approved_not_accepted")


# --------------------------------------------------------------------------------------------- ULI (Appendix C)
def uli_check_digits(base: str) -> str:
    """Two check digits for LEI + loan characters (ISO/IEC 7064 MOD 97-10, Appendix C steps 1-5)."""
    digits = "".join(str(int(c, 36)) if c.isalpha() else c for c in base.upper()) + "00"
    return f"{98 - int(digits) % 97:02d}"


def valid_uli(uli: str) -> list[str]:
    """Problems with a ULI under 1003.4(a)(1)(i) and Appendix C; empty when valid."""
    problems = []
    if not re.fullmatch(r"[A-Za-z0-9]+", uli):
        return ["a ULI may contain only letters and numerals"]
    if not 23 <= len(uli) <= 45:
        problems.append(f"a ULI is the 20-character LEI plus up to 23 characters plus a 2-digit check digit (23-45 characters); this one has {len(uli)}")
    elif int("".join(str(int(c, 36)) if c.isalpha() else c for c in uli.upper())) % 97 != 1:
        problems.append("the check digit is wrong (Appendix C validation does not yield 1)")
    return problems


# ----------------------------------------------------------------------------------------------- the engine
@dataclass
class Item:
    number: int
    status: str
    message: str = ""
    missing: list[str] = field(default_factory=list)


class Ctx:
    """`lar_context` flags; asking for an absent flag records that the answer is unknown."""

    def __init__(self, flags: dict[str, Any]) -> None:
        self.flags, self.unknown = flags, set()

    def get(self, name: str) -> bool | None:
        value = self.flags.get(name)
        if value is None:
            self.unknown.add(name)
        return value

    def decide(self, applies: Any) -> tuple[bool | None, list[str]]:
        """Evaluate an applicability (a bool, or a callable using need/get) and report which flags were unknown for it."""
        self.unknown = set()
        value = applies() if callable(applies) else applies
        return value, sorted(self.unknown)

    def need(self, *names: str) -> bool | None:
        """True if all flags are True; False if any is False; None if any is unknown (and none False)."""
        values = [self.get(n) for n in names]
        if any(v is False for v in values):
            return False
        return None if any(v is None for v in values) else True


def _absent(v: Any) -> bool:
    return v is None or v == "" or v == [] or v == {}


def _num(v: Any, minimum: float | None = None, exclusive: bool = False) -> bool:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return False
    return True if minimum is None else (v > minimum if exclusive else v >= minimum)


def _int(v: Any, minimum: int = 0) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= minimum


def _demographic_problems(person: Any, label: str, appendix: dict[str, Any], mode: str | None, purchased: bool) -> tuple[list[str], list[str]]:
    """Appendix B rules for one applicant's ethnicity / race / sex block: (invalid values, missing pieces)."""
    if person == NA:
        return ([] if purchased else [f"{label} was reported not applicable, which is allowed only for purchased loans or non-natural-person applicants (Appendix B, notes 6-7)"]), []
    if not isinstance(person, dict):
        return [f"{label} must be an object with ethnicity, race, sex and collected_by_visual_observation_or_surname"], []
    invalid, gaps = [], []
    observed = person.get("collected_by_visual_observation_or_surname")
    if observed is None:
        gaps.append(f"{label}.collected_by_visual_observation_or_surname")
    elif not isinstance(observed, bool):
        invalid.append(f"{label}: whether ethnicity, race and sex were collected by visual observation or surname must be true or false (1003.4(a)(10)(i))")
    families = {
        "ethnicity": (appendix["ethnicity_aggregate"], appendix["ethnicity_subcategories"], appendix["max_ethnicity_entries"]),
        "race": (appendix["race_aggregate"], appendix["race_subcategories"], appendix["max_race_entries"]),
    }
    for name, (aggregate, subs, maximum) in families.items():
        value = person.get(name)
        if _absent(value):
            gaps.append(f"{label}.{name}")
            continue
        entries = [value] if isinstance(value, str) else value
        if entries == [NOT_PROVIDED]:
            if mode == "in_person":
                invalid.append(f"{label}: {name} is 'information not provided', but an in-person application requires visual observation or surname (Appendix B, note 10)")
            continue
        if entries == [NA]:
            invalid.append(f"{label}: {name} is reported not applicable")
            continue
        for entry in entries:
            if isinstance(entry, dict):
                if not isinstance(entry.get("particular"), str) or not entry["particular"].strip():
                    invalid.append(f"{label}: a particular {name} entry needs its text (Appendix B, note 9)")
            elif entry not in aggregate + subs:
                invalid.append(f"{label}: '{entry}' is not an Appendix B {name} category or subcategory")
        if len(entries) > maximum:
            invalid.append(f"{label}: {len(entries)} {name} entries reported; no more than {maximum} categories and subcategories combined may be reported (Appendix B, note 9)")
        if observed is True and any(not isinstance(e, str) or e not in aggregate for e in entries):
            invalid.append(f"{label}: {name} collected by visual observation or surname must use the aggregate categories only (Appendix B, note 10)")
    sex = person.get("sex")
    sexes = [sex] if isinstance(sex, str) else (sex or [])
    if _absent(sex):
        gaps.append(f"{label}.sex")
    elif sexes == [NOT_PROVIDED]:
        if mode == "in_person":
            invalid.append(f"{label}: sex is 'information not provided', but an in-person application requires visual observation or surname (Appendix B, note 10)")
    elif not set(sexes) <= set(appendix["sex"]):
        invalid.append(f"{label}: sex must be male or female (or information not provided)")
    return invalid, gaps


def partial_exemption_status(case: dict[str, Any], items_meta: dict[str, Any]) -> tuple[bool, str]:
    """(valid, why-not). A claimed partial exemption (1003.3(d)) makes the 'optional data' items optional."""
    flags = case.get("lar_context") or {}
    if not flags.get("partial_exemption"):
        return False, ""
    originations = (case.get("prior_year_originations") or {}).get(case["credit_structure"])
    limit = items_meta["partial_exemption_origination_limit"]
    if flags.get("institution_type") not in ("insured_depository", "insured_credit_union"):
        return False, "only an insured depository institution or insured credit union may use the partial exemption (1003.3(d)(2)-(3))"
    if originations is None:
        return False, "prior-year origination counts are needed to confirm eligibility for the partial exemption"
    if max(originations) >= limit:
        return False, f"originations of {max(originations)} reach the {limit} limit, so the partial exemption is not available (1003.3(d)(2)-(3))"
    if flags.get("cra_poor_rating"):
        return False, "the CRA rating disqualifies the institution from the partial exemption (1003.3(d)(6))"
    return True, ""


def evaluate_items(case: dict[str, Any], items_meta: dict[str, Any], appendix: dict[str, Any], rate_spread_outcome: str | None,
                   rate_spread_message: str) -> tuple[list[Item], dict[str, Any]]:
    """Return the 38 item results and a summary of the context used."""
    lar, ctx = case.get("lar") or {}, Ctx(case.get("lar_context") or {})
    action = case["action_taken"]
    purchased, applicant_demographics_optional = action == "purchased", action == "purchased"
    meta = {m["number"]: m for m in items_meta["items"]}
    mode = ctx.flags.get("application_mode")

    exempt, exemption_note = partial_exemption_status(case, items_meta)
    results: list[Item] = []

    def put(number: int, status: str, message: str = "", missing: list[str] | None = None) -> None:
        results.append(Item(number, status, message, missing or []))

    def judge(number: int, applies_spec: Any, value: Any, problems: Callable[[Any], list[str]], *, field_name: str) -> None:
        m = meta[number]
        applies, names = ctx.decide(applies_spec)
        if m["optional"] is True and exempt:
            return put(number, "exempt", f"Item {number} ({m['name']}) is optional data for a partially exempt institution (1003.3(d)(1)(iii)).")
        if applies is False:
            return put(number, "not_applicable", f"Item {number} ({m['name']}) does not apply to this action or loan.")
        if applies is None:
            return put(number, "unable", f"Item {number} ({m['name']}): whether it applies depends on context flags not supplied: {', '.join(names)}.", [f"lar_context.{n}" for n in names])
        if _absent(value):
            return put(number, "unable", f"Item {number} ({m['name']}) applies but no value is supplied (absence from the input is not proof it is absent from the register) {m['cite']}.", [f"lar.{field_name}"])
        if value == NA:
            return put(number, "not_satisfied", f"Item {number} ({m['name']}) applies but was reported not applicable {m['cite']}.")
        bad = problems(value)
        put(number, "not_satisfied" if bad else "satisfied", "; ".join(bad) if bad else "")

    enum = lambda allowed: (lambda v: [] if v in allowed else [f"'{v}' is not one of {sorted(allowed)}"])  # noqa: E731
    number = lambda minimum=None, exclusive=False: (lambda v: [] if _num(v, minimum, exclusive) else ["must be a number" + ("" if minimum is None else f" {'greater than' if exclusive else 'at least'} {minimum}")])  # noqa: E731
    integer = lambda minimum=0: (lambda v: [] if _int(v, minimum) else [f"must be a whole number of at least {minimum}"])  # noqa: E731
    text = lambda v: [] if isinstance(v, str) and v.strip() else ["must be non-empty text"]  # noqa: E731
    flag = lambda v: [] if isinstance(v, bool) else ["must be true or false"]  # noqa: E731

    # 1 ULI (the identifier itself is optional data; a NULI may replace it when partially exempt)
    uli, nuli = lar.get("uli"), lar.get("nuli")
    if meta[1]["optional"] == "partial" and exempt and _absent(uli) and not _absent(nuli):
        bad = [] if isinstance(nuli, str) and re.fullmatch(r"[A-Za-z0-9]{1,22}", nuli) else ["a NULI is up to 22 letters and numerals (1003.3(d)(5))"]
        put(1, "not_satisfied" if bad else "satisfied", "; ".join(bad))
    else:
        judge(1, True, uli, lambda v: valid_uli(v) if isinstance(v, str) else ["must be text"], field_name="uli")
    # 2-6
    judge(2, True, lar.get("loan_type_government_program"), enum({"not_insured_or_guaranteed", "fha", "va", "rhs_fsa"}), field_name="loan_type_government_program")
    judge(3, True, lar.get("loan_purpose"), lambda v: enum({"home_purchase", "home_improvement", "refinance", "cash_out_refinance", "other"})(v)
          + ([f"differs from the case's loan_purpose '{case['loan_purpose']}'"] if case.get("loan_purpose") and v != case["loan_purpose"] else []), field_name="loan_purpose")
    judge(4, True, lar.get("preapproval"), lambda v: [] if v in ("requested", "not_requested") or (v == NA and case.get("loan_purpose") not in (None, "home_purchase")) else ["must be requested/not_requested (not applicable only for non-home-purchase loans)"], field_name="preapproval")
    judge(5, True, lar.get("construction_method"), enum({"site_built", "manufactured_home"}), field_name="construction_method")
    judge(6, True, lar.get("occupancy_type"), enum({"principal_residence", "second_residence", "investment_property"}), field_name="occupancy_type")
    # 7 amount equals the case amount
    judge(7, True, lar.get("loan_amount"), lambda v: [] if _num(v, 0, True) and float(v) == float(case["amount"]) else [f"must be the loan amount {case['amount']}"], field_name="loan_amount")
    # 8 action taken is validated by HMDA-ACTION; mirrored here
    put(8, "satisfied", "Action taken and its date are validated by HMDA-ACTION.")

    # 9 location: address (optional data), state/county (property in an MSA with an office), census tract (county over 30,000)
    m9 = meta[9]
    in_msa, names9 = ctx.decide(lambda: ctx.get("property_in_msa_with_office"))
    big_county = ctx.get("county_population_over_30000") if in_msa else None
    bad9, unknown9 = [], []
    address_exempt = exempt and m9["optional"] == "partial"
    if not address_exempt and _absent(lar.get("property_address")):
        unknown9.append("lar.property_address")
    if in_msa is None:
        unknown9.append("lar_context.property_in_msa_with_office")
    elif in_msa:
        if _absent(lar.get("property_state")) or _absent(lar.get("property_county")):
            unknown9 += [f"lar.{f}" for f in ("property_state", "property_county") if _absent(lar.get(f))]
        elif not re.fullmatch(r"[A-Za-z]{2}", str(lar["property_state"])):
            bad9.append("state must be a 2-letter code (1003.4(a)(9)(ii)(A))")
        if big_county is None:
            unknown9.append("lar_context.county_population_over_30000")
        elif big_county and not re.fullmatch(r"\d{11}", str(lar.get("property_census_tract") or "")):
            (bad9 if lar.get("property_census_tract") else unknown9).append("census tract must be an 11-digit code for a county over 30,000 population (1003.4(a)(9)(ii)(C))" if lar.get("property_census_tract") else "lar.property_census_tract")
    if bad9:
        put(9, "not_satisfied", "; ".join(bad9))
    elif unknown9:
        put(9, "unable", f"Item 9 ({m9['name']}): not enough supplied to confirm {m9['cite']}: {', '.join(unknown9)}.", unknown9)
    else:
        put(9, "satisfied")

    # 10 applicant demographics, age, income: invalid values fail; missing pieces cannot be determined
    if purchased and (_absent(lar.get("applicant")) or lar.get("applicant") == NA):
        put(10, "satisfied", "Purchased loan: ethnicity, race, sex, age and income may but need not be collected (1003.4(b)(2)).")
    else:
        mode_ = ctx.flags.get("application_mode")
        invalid, gaps = ([], [])
        if _absent(lar.get("applicant")):
            gaps.append("applicant")
        else:
            invalid, gaps = _demographic_problems(lar["applicant"], "applicant", appendix, mode_, purchased)
        has_co = ctx.get("co_applicant_present")
        co = lar.get("co_applicant")
        if has_co is None:
            gaps.append("lar_context.co_applicant_present")
        elif has_co:
            if co in (None, "none"):
                gaps.append("co_applicant")
            else:
                inv2, gaps2 = _demographic_problems(co, "co-applicant", appendix, mode_, purchased)
                invalid += inv2
                gaps += gaps2
        elif co not in (None, "none"):
            invalid.append("no co-applicant is present but a co-applicant block is reported (Appendix B, note 5)")
        age = lar.get("age")
        if _absent(age):
            gaps.append("age")
        elif not (age == NA and purchased) and not (_int(age, 0) and age <= 150):
            invalid.append("age must be a whole number of years (1003.4(a)(10)(ii))")
        income_considered, income = ctx.get("income_considered"), lar.get("income")
        if income_considered is None:
            gaps.append("lar_context.income_considered")
        elif income_considered and _absent(income):
            gaps.append("income")
        elif income_considered and not _num(income, 0):
            invalid.append("gross annual income relied on must be a number (1003.4(a)(10)(iii))")
        elif not income_considered and income not in (None, NA):
            invalid.append("income is reported although the credit decision did not consider income")
        if invalid:
            put(10, "not_satisfied", "; ".join(invalid))
        elif gaps:
            put(10, "unable", "Item 10 (Applicant ethnicity, race, sex, age and income) is incomplete in the input (absence is not proof it is absent from the register): " + ", ".join(gaps) + ".",
                [g if g.startswith("lar_context.") else f"lar.{g}" for g in gaps])
        else:
            put(10, "satisfied")
    # 11 purchaser type (loans sold in the same calendar year)
    judge(11, lambda: ctx.get("sold_same_year") if action in ACTIONS_LOAN else False, lar.get("purchaser_type"), text, field_name="purchaser_type")
    # 12 rate spread: mirrored from the rate-spread rule
    if meta[12]["optional"] is True and exempt:
        put(12, "exempt", "Rate spread is optional data for a partially exempt institution.")
    elif rate_spread_outcome in ("does_not_apply", None):
        put(12, "not_applicable", rate_spread_message or "Rate spread is not applicable to this action or loan.")
    else:
        put(12, {"satisfied": "satisfied", "not_satisfied": "not_satisfied"}.get(rate_spread_outcome, "unable"), rate_spread_message)
    # 13-14
    judge(13, lambda: ctx.need("subject_to_hoepa") if action in ACTIONS_LOAN else False, lar.get("hoepa_status"), enum({"high_cost_mortgage", "not_high_cost_mortgage"}), field_name="hoepa_status")
    judge(14, True, lar.get("lien_status"), enum({"first_lien", "subordinate_lien"}), field_name="lien_status")
    # 15-16
    def credit_scores(v: Any) -> list[str]:
        scores = v if isinstance(v, list) else []
        if not scores:
            return ["must list the credit score(s) with the scoring model name and version"]
        return [f"score entry {i + 1} needs a numeric score and the model name and version" for i, s in enumerate(scores)
                if not (isinstance(s, dict) and _num(s.get("score"), 0) and text(s.get("model")) == [] and text(s.get("version")) == [])]
    judge(15, lambda: ctx.need("credit_score_relied_on") if not purchased else False, lar.get("credit_scores"), credit_scores, field_name="credit_scores")
    judge(16, action in ("denied", "preapproval_denied"), lar.get("denial_reasons") or case.get("denial_reasons"), lambda v: [] if isinstance(v, list) and 1 <= len(v) <= 4 and all(isinstance(x, str) and x.strip() for x in v) else ["1 to 4 principal denial reasons are required"], field_name="denial_reasons")
    # 17-20 Regulation Z disclosure-based items
    def cost_item(v: Any) -> list[str]:
        if ctx.flags.get("subject_to_1026_19f"):
            return [] if _num(lar.get("total_loan_costs"), 0) else ["total loan costs (from the Closing Disclosure) must be a number (1003.4(a)(17)(i))"]
        if purchased:
            return [] if _num(lar.get("total_loan_costs"), 0) or _num(lar.get("total_points_and_fees"), 0) else ["a number is required"]
        return [] if _num(lar.get("total_points_and_fees"), 0) else ["total points and fees must be a number when no Closing Disclosure applies (1003.4(a)(17)(ii))"]
    judge(17, lambda: ctx.need("subject_to_1026_43c") if action in ACTIONS_LOAN else False, lar.get("total_loan_costs") if lar.get("total_loan_costs") is not None else lar.get("total_points_and_fees"), cost_item, field_name="total_loan_costs")
    in_19f = lambda: ctx.need("subject_to_1026_19f") if action in ACTIONS_LOAN else False   # noqa: E731
    judge(18, in_19f, lar.get("total_borrower_paid_charges"), number(0), field_name="total_borrower_paid_charges")
    judge(19, in_19f, lar.get("discount_points"), number(0), field_name="discount_points")
    judge(20, in_19f, lar.get("lender_credits"), number(0), field_name="lender_credits")
    # 21-28
    judge(21, action in ACTIONS_PRICED, lar.get("interest_rate"), lambda v: [] if _num(v, 0, True) and v < 100 else ["must be a percentage greater than 0 and less than 100"], field_name="interest_rate")
    judge(22, (not purchased) and bool(case.get("subject_to_reg_z", True)) and not case.get("reverse_mortgage", False), lar.get("prepayment_penalty_term_months"), integer(0), field_name="prepayment_penalty_term_months")
    judge(23, lambda: ctx.need("dti_relied_on") if not purchased else False, lar.get("debt_to_income_ratio"), number(0), field_name="debt_to_income_ratio")
    judge(24, lambda: ctx.need("cltv_relied_on") if not purchased else False, lar.get("combined_loan_to_value_ratio"), number(0), field_name="combined_loan_to_value_ratio")
    judge(25, True, lar.get("loan_term_months"), integer(1), field_name="loan_term_months")
    judge(26, lambda: ctx.need("rate_may_change"), lar.get("introductory_rate_period_months"), integer(1), field_name="introductory_rate_period_months")
    judge(27, True, lar.get("non_amortizing_features"), lambda v: [] if isinstance(v, dict) and all(isinstance(v.get(k), bool) for k in ("balloon_payment", "interest_only_payments", "negative_amortization", "other_non_fully_amortizing")) else ["balloon_payment, interest_only_payments, negative_amortization and other_non_fully_amortizing must each be true or false"], field_name="non_amortizing_features")
    judge(28, lambda: ctx.need("value_relied_on"), lar.get("property_value"), number(0, True), field_name="property_value")
    # 29-32
    def manufactured_home_only() -> bool | None:
        """Items 29-30 apply to a manufactured home that is not a multifamily dwelling."""
        manufactured, multifamily = ctx.get("is_manufactured_home"), ctx.get("is_multifamily")
        if manufactured is False or multifamily is True:
            return False
        return None if manufactured is None or multifamily is None else True
    judge(29, manufactured_home_only, lar.get("manufactured_home_secured_property_type"), enum({"manufactured_home_and_land", "manufactured_home_not_land"}), field_name="manufactured_home_secured_property_type")
    judge(30, manufactured_home_only, lar.get("manufactured_home_land_property_interest"), enum({"direct_ownership", "indirect_ownership", "paid_leasehold", "unpaid_leasehold"}), field_name="manufactured_home_land_property_interest")
    judge(31, True, lar.get("total_units"), integer(1), field_name="total_units")
    judge(32, lambda: ctx.need("is_multifamily"), lar.get("multifamily_affordable_units"), integer(0), field_name="multifamily_affordable_units")
    # 33-38
    judge(33, not purchased, lar.get("application_channel"), lambda v: [] if isinstance(v, dict) and all(isinstance(v.get(k), bool) for k in ("submitted_directly", "initially_payable_to_institution")) else ["submitted_directly and initially_payable_to_institution must each be true or false"], field_name="application_channel")
    judge(34, True, lar.get("nmls_identifier"), text, field_name="nmls_identifier")
    judge(35, lambda: ctx.need("aus_used") if not purchased else False, lar.get("automated_underwriting"), lambda v: [] if isinstance(v, dict) and text(v.get("system")) == [] and text(v.get("result")) == [] else ["the AUS name and the result it generated are required"], field_name="automated_underwriting")
    judge(36, True, lar.get("reverse_mortgage"), lambda v: flag(v) or ([] if bool(case.get("reverse_mortgage", False)) == v else ["differs from the case's reverse_mortgage fact"]), field_name="reverse_mortgage")
    judge(37, True, lar.get("open_end_line_of_credit"), lambda v: flag(v) or ([] if (case["credit_structure"] == "open_end") == v else ["differs from the case's credit_structure"]), field_name="open_end_line_of_credit")
    judge(38, True, lar.get("business_or_commercial_purpose"), lambda v: flag(v) or ([] if case.get("business_commercial_purpose") in (None, "undetermined") or (case["business_commercial_purpose"] == "primarily") == v else ["differs from the case's business_commercial_purpose"]), field_name="business_or_commercial_purpose")
    results.sort(key=lambda r: r.number)
    return results, {"partial_exemption_applied": exempt, "partial_exemption_note": exemption_note}

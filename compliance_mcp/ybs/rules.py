"""Deterministic YBS eligibility evaluator (12 CFR 614.4165 program).

The pack is explicit about what is regulatory authority and what is institution
policy. The evaluator never fills in missing facts or legal policy with model
reasoning. The pack is a reviewable pilot pack, not a claim that its attribution
policy is universally required by FCA regulation.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from compliance_common.decision import base_record, comparison, fact, finalize, rule
from compliance_common.pack import (
    EvaluatorValidationError, Pack, as_date, load_pack, threshold_record, validate_instance,
)

EVALUATOR_VERSION = "0.2.0"
PACK_DIR = Path(__file__).resolve().parent / "pack"
YBSValidationError = EvaluatorValidationError


def _age_on(dob, on_date) -> int:
    return on_date.year - dob.year - ((on_date.month, on_date.day) < (dob.month, dob.day))


def _pack() -> Pack:
    return load_pack("ybs", PACK_DIR, ("thresholds", "entity_policy"))


def validate_ybs_rule_pack() -> None:
    """Validate source provenance and both schemas for the YBS rule pack."""
    _pack()


def validate_ybs_decision_record(record: dict[str, Any]) -> None:
    """Validate an evaluator output against the pack's decision-record contract."""
    validate_instance(record, _pack().decision_schema, "YBS decision record")


def _person_categories(
    subject: dict[str, Any], threshold: dict[str, Any], evaluation_date: date,
    facts_used: list[dict[str, Any]], missing: list[dict[str, Any]],
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    rules: list[dict[str, Any]] = []
    categories: dict[str, str] = {}
    producer = fact(subject, "is_agricultural_producer", facts_used, missing)
    if producer is not True:
        outcome = "not_eligible" if producer is False else "unable_to_determine"
        for category in ("young", "beginning", "small"):
            categories[category] = outcome
            rules.append(rule(f"YBS-PERSON-{category.upper()}-PRODUCER", outcome, "regulatory", "Agricultural producer status is required."))
        return categories, rules

    dob_value = fact(subject, "date_of_birth", facts_used, missing)
    if dob_value is None:
        categories["young"] = "unable_to_determine"
        rules.append(rule("YBS-PERSON-YOUNG-DOB", "unable_to_determine", "institution_policy", "Date of birth is required for the age calculation."))
    else:
        age = _age_on(as_date(dob_value, "date_of_birth"), evaluation_date)
        facts_used.append({"subject_id": subject["id"], "field": "calculated_age", "value": age})
        passes = comparison(age, float(threshold["young_age_limit"]), threshold["young_operator"])
        categories["young"] = "eligible" if passes else "not_eligible"
        rules.append(rule("YBS-PERSON-YOUNG-AGE", categories["young"], "institution_policy", "Age comparison applied.", value=age, threshold=threshold["young_age_limit"], operator=threshold["young_operator"]))

    experience = fact(subject, "years_farming", facts_used, missing)
    if experience is None:
        categories["beginning"] = "unable_to_determine"
        rules.append(rule("YBS-PERSON-BEGINNING-EXPERIENCE", "unable_to_determine", "institution_policy", "Years farming is required."))
    else:
        passes = comparison(float(experience), float(threshold["beginning_years_limit"]), threshold["beginning_operator"])
        categories["beginning"] = "eligible" if passes else "not_eligible"
        rules.append(rule("YBS-PERSON-BEGINNING-EXPERIENCE", categories["beginning"], "institution_policy", "Farming-experience comparison applied.", value=experience, threshold=threshold["beginning_years_limit"], operator=threshold["beginning_operator"]))

    sales = fact(subject, "annual_gross_ag_sales", facts_used, missing)
    if sales is None:
        categories["small"] = "unable_to_determine"
        rules.append(rule("YBS-PERSON-SMALL-SALES", "unable_to_determine", "institution_policy", "Annual gross agricultural sales is required."))
    else:
        passes = comparison(float(sales), float(threshold["small_farmer_sales_limit"]), threshold["small_operator"])
        categories["small"] = "eligible" if passes else "not_eligible"
        rules.append(rule("YBS-PERSON-SMALL-SALES", categories["small"], "institution_policy", "Gross-sales comparison applied.", value=sales, threshold=threshold["small_farmer_sales_limit"], operator=threshold["small_operator"]))
    return categories, rules


def _entity_categories(
    subject: dict[str, Any], subject_results: dict[str, dict[str, Any]], policy: dict[str, Any],
    missing: list[dict[str, Any]],
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    rules: list[dict[str, Any]] = []
    entity_kind = subject.get("entity_kind", "organization")

    def attribution_review(reason: str, rule_suffix: str = "ATTRIBUTION") -> tuple[dict[str, str], list[dict[str, Any]]]:
        categories = {category: "review_required" for category in ("young", "beginning", "small")}
        missing.append({"subject_id": subject["id"], "field": "attribution", "reason": reason})
        return categories, [
            rule(f"YBS-ENTITY-{category.upper()}-{rule_suffix}", "review_required", "institution_policy", reason)
            for category in categories
        ]

    if subject.get("attribution_conflict"):
        return attribution_review("Conflicting ownership, control, or operating-responsibility evidence requires review.", "CONFLICT")
    if subject.get("attribution_documented") is False:
        return attribution_review("Required attribution documentation is absent or insufficient.")
    related = subject.get("attribution", [])
    relevant_roles = set(policy["attribution"]["required_roles"])
    attributable = [r for r in related if r.get("role") in relevant_roles]
    if not attributable:
        return attribution_review("No required ownership, control, or operator relationship was supplied.")
    roles = {relation.get("role") for relation in attributable}
    if entity_kind == "trust" and not {"trustee", "controlling_person"}.issubset(roles):
        return attribution_review("A trust requires explicit trustee and beneficial-control attribution.", "TRUST")
    if entity_kind in {"successor", "reorganization"} and subject.get("attribution_documented") is not True:
        return attribution_review("A successor or reorganization requires documented attribution.", "SUCCESSION")

    categories: dict[str, str] = {}
    for category in ("young", "beginning", "small"):
        outcomes: list[str] = []
        for relation in attributable:
            person = subject_results.get(str(relation.get("subject_id")))
            if person is None or person["subject_type"] != "person":
                outcomes.append("review_required")
                missing.append({"subject_id": subject["id"], "field": "attribution.subject_id", "reason": f"attributed subject {relation.get('subject_id')!r} is not a known person"})
            else:
                outcomes.append(person["categories"][category])
        if "review_required" in outcomes or "unable_to_determine" in outcomes:
            outcome = "review_required" if "review_required" in outcomes else "unable_to_determine"
        elif policy["attribution"]["entity_category_rule"] == "all_attributable_people_must_qualify":
            outcome = "eligible" if all(x == "eligible" for x in outcomes) else "not_eligible"
        else:
            raise EvaluatorValidationError("Unsupported entity attribution policy")
        categories[category] = outcome
        rules.append(rule(f"YBS-ENTITY-{category.upper()}-ATTRIBUTION", outcome, "institution_policy", "Entity category derived from all required attributable people.", attributable_outcomes=outcomes))
    return categories, rules


def _classification(categories: dict[str, str]) -> str:
    if any(value == "review_required" for value in categories.values()):
        return "Review Required"
    if any(value == "unable_to_determine" for value in categories.values()):
        return "Unable To Determine"
    eligible = [name.title() for name, value in categories.items() if value == "eligible"]
    return " + ".join(eligible) if eligible else "Not Eligible"


def _compliance_result(classification: str) -> str:
    """YBS is a program-eligibility classification, not a pass/fail test."""
    if classification == "Unable To Determine":
        return "Unable To Determine"
    if classification == "Review Required":
        return "Potential Issue"
    return "Not Applicable" if classification == "Not Eligible" else "Compliant"


def evaluate_ybs(case: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a canonical YBS case without making network or model calls.

    Required canonical fields are ``evaluation_date`` and ``subjects``. A subject
    is a person or entity. Entities carry ``attribution`` relationships to the
    relevant people. ``determination_subject_ids`` chooses the borrower/entity
    whose aggregate result is returned; it defaults to all subjects.
    """
    if not isinstance(case, dict):
        raise EvaluatorValidationError("YBS input must be an object")
    evaluation_date = as_date(case.get("evaluation_date"), "evaluation_date")
    subjects = case.get("subjects")
    if not isinstance(subjects, list) or not subjects:
        raise EvaluatorValidationError("subjects must be a non-empty list")

    pack = _pack()
    validate_instance(case, pack.input_schema, "canonical YBS input")
    threshold = threshold_record(pack.files["thresholds"], evaluation_date)
    policy = pack.files["entity_policy"]
    base = base_record("ybs", EVALUATOR_VERSION, pack, case, evaluation_date)
    if threshold is None:
        base.update({"threshold_record": None, "validation_errors": [{"field": "evaluation_date", "reason": "no effective threshold record"}]})
        finalize(base, "Unable To Determine", "Unable To Determine", "Unable To Determine", timestamp=False)
        validate_instance(base, pack.decision_schema, "YBS decision record")
        return base

    subject_results: dict[str, dict[str, Any]] = {}
    pending_entities: list[dict[str, Any]] = []
    for subject in subjects:
        if not isinstance(subject, dict) or not subject.get("id") or subject.get("type") not in {"person", "entity"}:
            raise EvaluatorValidationError("Every subject requires id and type of person or entity")
        if subject["type"] == "entity":
            pending_entities.append(subject)
            continue
        categories, rules = _person_categories(subject, threshold, evaluation_date, base["facts_used"], base["missing_facts"])
        subject_results[subject["id"]] = {"subject_id": subject["id"], "subject_type": "person", "categories": categories, "classification": _classification(categories), "rule_results": rules}

    for subject in pending_entities:
        categories, rules = _entity_categories(subject, subject_results, policy, base["missing_facts"])
        subject_results[subject["id"]] = {"subject_id": subject["id"], "subject_type": "entity", "categories": categories, "classification": _classification(categories), "rule_results": rules}

    requested_ids = case.get("determination_subject_ids") or [subject["id"] for subject in subjects]
    requested = [subject_results.get(subject_id) for subject_id in requested_ids]
    if any(result is None for result in requested):
        raise EvaluatorValidationError("determination_subject_ids contains an unknown subject")
    classifications = {result["classification"] for result in requested if result}
    final = next(iter(classifications)) if len(classifications) == 1 else "Review Required"
    base["subject_results"] = list(subject_results.values())
    base["rule_results"] = [r for result in base["subject_results"] for r in result["rule_results"]]
    base["threshold_record"] = threshold
    status = "Determined" if final not in {"Unable To Determine", "Review Required"} else final
    finalize(base, final, status, _compliance_result(final))
    validate_instance(base, pack.decision_schema, "YBS decision record")
    return base

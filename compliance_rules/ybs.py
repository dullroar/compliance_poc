"""Deterministic YBS eligibility evaluator.

The pack is intentionally explicit about what is regulatory authority and what
is institution policy.  It does not fill in missing facts or legal policy with
model reasoning.  The supplied v0.1 pack is a reviewable pilot pack, not a
claim that its attribution policy is universally required by FCA regulation.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACK = "ybs-v0.1"
_OUTCOMES = {"eligible", "not_eligible", "unable_to_determine", "review_required"}


class YBSValidationError(ValueError):
    """Raised only for malformed evaluator input or an invalid rule pack."""


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        value = yaml.safe_load(source)
    if not isinstance(value, dict):
        raise YBSValidationError(f"Expected an object in {path}")
    return value


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise YBSValidationError(f"Invalid JSON in {path}") from exc
    if not isinstance(value, dict):
        raise YBSValidationError(f"Expected an object in {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _as_date(value: Any, field: str) -> date:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise YBSValidationError(f"{field} must be an ISO-8601 date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise YBSValidationError(f"{field} must be an ISO-8601 date") from exc


def _age_on(dob: date, on_date: date) -> int:
    return on_date.year - dob.year - ((on_date.month, on_date.day) < (dob.month, dob.day))


def _fact(subject: dict[str, Any], field: str, facts_used: list[dict[str, Any]], missing: list[dict[str, Any]]) -> Any:
    if field in set(subject.get("conflicting_fields", [])):
        missing.append({"subject_id": subject.get("id"), "field": field, "reason": "conflicting evidence requires review"})
        return None
    value = subject.get(field)
    if value is None or value == "":
        missing.append({"subject_id": subject.get("id"), "field": field, "reason": "required fact is absent"})
        return None
    facts_used.append({"subject_id": subject.get("id"), "field": field, "value": value})
    return value


def _rule(rule_id: str, outcome: str, basis: str, message: str, **extra: Any) -> dict[str, Any]:
    if outcome not in _OUTCOMES:
        raise YBSValidationError(f"Invalid outcome {outcome!r}")
    return {"rule_id": rule_id, "outcome": outcome, "basis": basis, "message": message, **extra}


def _comparison(value: float, threshold: float, operator: str) -> bool:
    return {"lt": value < threshold, "lte": value <= threshold}[operator]


def _validate_instance(instance: Any, schema: dict[str, Any], label: str) -> None:
    """Validate a public contract and report a stable, actionable first error."""
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:  # jsonschema exposes several SchemaError subclasses.
        raise YBSValidationError(f"Invalid {label} schema: {exc.message}") from exc
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        raise YBSValidationError(f"Invalid {label} at {location}: {error.message}")


def _validated_local_path(root: Path, relative: str, label: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise YBSValidationError(f"{label} must remain under {root}") from exc
    if not candidate.is_file():
        raise YBSValidationError(f"Missing {label}: {relative}")
    return candidate


def _load_pack(rule_pack_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], Path, dict[str, Any], dict[str, Any]]:
    """Load and validate a pinned rule pack before it can affect a decision."""
    pack_dir = ROOT / "rulepacks" / "ybs" / rule_pack_id
    manifest_path = pack_dir / "manifest.yaml"
    if not manifest_path.exists():
        raise YBSValidationError(f"Unknown YBS rule pack: {rule_pack_id}")
    manifest = _load_yaml(manifest_path)
    required_manifest_keys = {"id", "version", "status", "files", "sources"}
    missing_manifest_keys = required_manifest_keys - manifest.keys()
    if missing_manifest_keys:
        raise YBSValidationError(f"Rule-pack manifest is missing {sorted(missing_manifest_keys)}")
    if manifest["id"] != rule_pack_id or not isinstance(manifest["files"], dict) or not isinstance(manifest["sources"], list):
        raise YBSValidationError("Rule-pack manifest has an invalid id, files, or sources contract")

    required_files = {"thresholds", "entity_policy", "input_schema", "decision_record_schema"}
    if required_files - manifest["files"].keys():
        raise YBSValidationError("Rule-pack manifest does not declare every required rule-pack file")
    files = {
        name: _validated_local_path(pack_dir, relative, f"rule-pack file {name}")
        for name, relative in manifest["files"].items()
    }
    thresholds = _load_yaml(files["thresholds"])
    policy = _load_yaml(files["entity_policy"])
    input_schema = _load_json(files["input_schema"])
    decision_schema = _load_json(files["decision_record_schema"])
    try:
        Draft202012Validator.check_schema(input_schema)
        Draft202012Validator.check_schema(decision_schema)
    except Exception as exc:
        raise YBSValidationError(f"Invalid rule-pack JSON schema: {exc.message}") from exc

    for source in manifest["sources"]:
        if not isinstance(source, dict) or not all(key in source for key in ("id", "local_path", "sha256")):
            raise YBSValidationError("Every source manifest entry requires id, local_path, and sha256")
        source_path = _validated_local_path(ROOT, source["local_path"], f"source {source.get('id', '<unknown>')}")
        if _sha256(source_path) != source["sha256"]:
            raise YBSValidationError(f"Source hash mismatch for {source['id']}")
    return manifest, thresholds, policy, pack_dir, input_schema, decision_schema


def validate_ybs_rule_pack(rule_pack_id: str = DEFAULT_PACK) -> None:
    """Validate source provenance and both schemas for a pinned YBS rule pack."""
    _load_pack(rule_pack_id)


def validate_ybs_decision_record(record: dict[str, Any], rule_pack_id: str = DEFAULT_PACK) -> None:
    """Validate an evaluator output against the pinned decision-record contract."""
    *_, decision_schema = _load_pack(rule_pack_id)
    _validate_instance(record, decision_schema, "YBS decision record")


def _threshold_record(thresholds: dict[str, Any], evaluation_date: date) -> dict[str, Any] | None:
    for record in thresholds.get("records", []):
        start = _as_date(record["effective_start"], "effective_start")
        end = _as_date(record["effective_end"], "effective_end") if record.get("effective_end") else None
        if evaluation_date >= start and (end is None or evaluation_date <= end):
            return record
    return None


def _person_categories(
    subject: dict[str, Any], threshold: dict[str, Any], evaluation_date: date,
    facts_used: list[dict[str, Any]], missing: list[dict[str, Any]],
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    rules: list[dict[str, Any]] = []
    categories: dict[str, str] = {}
    producer = _fact(subject, "is_agricultural_producer", facts_used, missing)
    if producer is not True:
        outcome = "not_eligible" if producer is False else "unable_to_determine"
        for category in ("young", "beginning", "small"):
            categories[category] = outcome
            rules.append(_rule(f"YBS-PERSON-{category.upper()}-PRODUCER", outcome, "regulatory", "Agricultural producer status is required."))
        return categories, rules

    dob_value = _fact(subject, "date_of_birth", facts_used, missing)
    if dob_value is None:
        categories["young"] = "unable_to_determine"
        rules.append(_rule("YBS-PERSON-YOUNG-DOB", "unable_to_determine", "policy", "Date of birth is required for the age calculation."))
    else:
        age = _age_on(_as_date(dob_value, "date_of_birth"), evaluation_date)
        facts_used.append({"subject_id": subject["id"], "field": "calculated_age", "value": age})
        passes = _comparison(age, float(threshold["young_age_limit"]), threshold["young_operator"])
        categories["young"] = "eligible" if passes else "not_eligible"
        rules.append(_rule("YBS-PERSON-YOUNG-AGE", categories["young"], "institution_policy", "Age comparison applied.", value=age, threshold=threshold["young_age_limit"], operator=threshold["young_operator"]))

    experience = _fact(subject, "years_farming", facts_used, missing)
    if experience is None:
        categories["beginning"] = "unable_to_determine"
        rules.append(_rule("YBS-PERSON-BEGINNING-EXPERIENCE", "unable_to_determine", "policy", "Years farming is required."))
    else:
        passes = _comparison(float(experience), float(threshold["beginning_years_limit"]), threshold["beginning_operator"])
        categories["beginning"] = "eligible" if passes else "not_eligible"
        rules.append(_rule("YBS-PERSON-BEGINNING-EXPERIENCE", categories["beginning"], "institution_policy", "Farming-experience comparison applied.", value=experience, threshold=threshold["beginning_years_limit"], operator=threshold["beginning_operator"]))

    sales = _fact(subject, "annual_gross_ag_sales", facts_used, missing)
    if sales is None:
        categories["small"] = "unable_to_determine"
        rules.append(_rule("YBS-PERSON-SMALL-SALES", "unable_to_determine", "policy", "Annual gross agricultural sales is required."))
    else:
        passes = _comparison(float(sales), float(threshold["small_farmer_sales_limit"]), threshold["small_operator"])
        categories["small"] = "eligible" if passes else "not_eligible"
        rules.append(_rule("YBS-PERSON-SMALL-SALES", categories["small"], "institution_policy", "Gross-sales comparison applied.", value=sales, threshold=threshold["small_farmer_sales_limit"], operator=threshold["small_operator"]))
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
            _rule(f"YBS-ENTITY-{category.upper()}-{rule_suffix}", "review_required", "institution_policy", reason)
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
            raise YBSValidationError("Unsupported entity attribution policy")
        categories[category] = outcome
        rules.append(_rule(f"YBS-ENTITY-{category.upper()}-ATTRIBUTION", outcome, "institution_policy", "Entity category derived from all required attributable people.", attributable_outcomes=outcomes))
    return categories, rules


def _classification(categories: dict[str, str]) -> str:
    if any(value == "review_required" for value in categories.values()):
        return "Review Required"
    if any(value == "unable_to_determine" for value in categories.values()):
        return "Unable To Determine"
    eligible = [name.title() for name, value in categories.items() if value == "eligible"]
    return " + ".join(eligible) if eligible else "Not Eligible"


def evaluate_ybs(case: dict[str, Any], rule_pack_id: str = DEFAULT_PACK) -> dict[str, Any]:
    """Evaluate a canonical YBS case without making network or model calls.

    Required canonical fields are ``evaluation_date`` and ``subjects``. A subject
    is a person or entity. Entities carry ``attribution`` relationships to the
    relevant people. ``determination_subject_ids`` chooses the borrower/entity
    whose aggregate result is returned; it defaults to all subjects.
    """
    if not isinstance(case, dict):
        raise YBSValidationError("YBS input must be an object")
    evaluation_date = _as_date(case.get("evaluation_date"), "evaluation_date")
    subjects = case.get("subjects")
    if not isinstance(subjects, list) or not subjects:
        raise YBSValidationError("subjects must be a non-empty list")

    manifest, thresholds, policy, pack_dir, input_schema, decision_schema = _load_pack(rule_pack_id)
    _validate_instance(case, input_schema, "canonical YBS input")
    threshold = _threshold_record(thresholds, evaluation_date)
    pack_files = {name: _sha256(pack_dir / relative) for name, relative in manifest["files"].items()}
    source_hashes = {item["id"]: item["sha256"] for item in manifest["sources"]}
    base = {
        "evaluator": {"name": "ybs", "version": "0.1.0", "network_accessed": False},
        "rule_pack": {"id": rule_pack_id, "version": manifest["version"], "status": manifest["status"], "git_revision": manifest.get("git_revision", "uncommitted"), "file_sha256": pack_files, "source_sha256": source_hashes},
        "case_id": case.get("case_id"),
        "evaluation_date": evaluation_date.isoformat(),
        "facts_used": [], "missing_facts": [], "rule_results": [], "subject_results": [],
        "evidence_references": case.get("evidence", []),
    }
    if threshold is None:
        base.update({"determination_status": "Unable To Determine", "final_classification": "Unable To Determine", "threshold_record": None, "validation_errors": [{"field": "evaluation_date", "reason": "no effective threshold record"}], "llm_contract": {"authoritative_classification": "Unable To Determine", "instruction": "The model may explain this decision record but must not change its classification, rule outcomes, thresholds, dates, or provenance."}, "decision_id": ""})
        base["decision_id"] = hashlib.sha256(json.dumps(base, sort_keys=True, default=str).encode()).hexdigest()
        _validate_instance(base, decision_schema, "YBS decision record")
        return base

    subject_results: dict[str, dict[str, Any]] = {}
    pending_entities: list[dict[str, Any]] = []
    for subject in subjects:
        if not isinstance(subject, dict) or not subject.get("id") or subject.get("type") not in {"person", "entity"}:
            raise YBSValidationError("Every subject requires id and type of person or entity")
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
        raise YBSValidationError("determination_subject_ids contains an unknown subject")
    classifications = {result["classification"] for result in requested if result}
    final = next(iter(classifications)) if len(classifications) == 1 else "Review Required"
    base["subject_results"] = list(subject_results.values())
    base["rule_results"] = [rule for result in base["subject_results"] for rule in result["rule_results"]]
    base["threshold_record"] = threshold
    base["final_classification"] = final
    base["determination_status"] = "Determined" if final not in {"Unable To Determine", "Review Required"} else final
    base["llm_contract"] = {"authoritative_classification": final, "instruction": "The model may explain this decision record but must not change its classification, rule outcomes, thresholds, dates, or provenance."}
    substantive = {key: value for key, value in base.items() if key not in {"evaluation_timestamp", "decision_id"}}
    base["decision_id"] = hashlib.sha256(json.dumps(substantive, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()
    base["evaluation_timestamp"] = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    _validate_instance(base, decision_schema, "YBS decision record")
    return base

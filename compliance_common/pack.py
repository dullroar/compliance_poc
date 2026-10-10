"""Rule-pack loading and validation shared by every deterministic evaluator.

A pack is a directory containing manifest.yaml plus the files it declares. Source
entries pin local snapshot files by sha256. Nothing here touches the network.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

REPO_ROOT = Path(__file__).resolve().parent.parent


class EvaluatorValidationError(ValueError):
    """Malformed evaluator input or an invalid rule pack."""


@dataclass(frozen=True)
class Pack:
    domain: str
    directory: Path
    manifest: dict[str, Any]
    files: dict[str, dict[str, Any]]  # parsed yaml/json by manifest file key
    input_schema: dict[str, Any]
    decision_schema: dict[str, Any]

    def file_hashes(self) -> dict[str, str]:
        return {name: sha256(self.directory / rel) for name, rel in self.manifest["files"].items()}

    def source_hashes(self) -> dict[str, str]:
        return {item["id"]: item["sha256"] for item in self.manifest["sources"]}


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        value = yaml.safe_load(source)
    if not isinstance(value, dict):
        raise EvaluatorValidationError(f"Expected an object in {path}")
    return value


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvaluatorValidationError(f"Invalid JSON in {path}") from exc
    if not isinstance(value, dict):
        raise EvaluatorValidationError(f"Expected an object in {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def as_date(value: Any, field: str) -> date:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise EvaluatorValidationError(f"{field} must be an ISO-8601 date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise EvaluatorValidationError(f"{field} must be an ISO-8601 date") from exc


def validate_instance(instance: Any, schema: dict[str, Any], label: str) -> None:
    """Validate a public contract and report a stable, actionable first error."""
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:  # jsonschema exposes several SchemaError subclasses.
        raise EvaluatorValidationError(f"Invalid {label} schema: {exc.message}") from exc
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        raise EvaluatorValidationError(f"Invalid {label} at {location}: {error.message}")


def _local_path(root: Path, relative: str, label: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise EvaluatorValidationError(f"{label} must remain under {root}") from exc
    if not candidate.is_file():
        raise EvaluatorValidationError(f"Missing {label}: {relative}")
    return candidate


def load_pack(domain: str, pack_dir: Path, data_files: tuple[str, ...]) -> Pack:
    """Load and validate a pack before it can affect a decision.

    `data_files` are the manifest `files` keys (yaml) the domain needs, in addition
    to the always-required input_schema and decision_record_schema.
    """
    manifest_path = pack_dir / "manifest.yaml"
    if not manifest_path.exists():
        raise EvaluatorValidationError(f"Unknown {domain} rule pack at {pack_dir}")
    manifest = load_yaml(manifest_path)
    missing_keys = {"id", "version", "status", "files", "sources"} - manifest.keys()
    if missing_keys:
        raise EvaluatorValidationError(f"Rule-pack manifest is missing {sorted(missing_keys)}")
    if manifest["id"] != domain or not isinstance(manifest["files"], dict) or not isinstance(manifest["sources"], list):
        raise EvaluatorValidationError("Rule-pack manifest has an invalid id, files, or sources contract")
    required = set(data_files) | {"input_schema", "decision_record_schema"}
    if required - manifest["files"].keys():
        raise EvaluatorValidationError("Rule-pack manifest does not declare every required rule-pack file")

    paths = {name: _local_path(pack_dir, rel, f"rule-pack file {name}") for name, rel in manifest["files"].items()}
    parsed = {name: load_yaml(paths[name]) for name in data_files}
    input_schema = load_json(paths["input_schema"])
    decision_schema = load_json(paths["decision_record_schema"])
    try:
        Draft202012Validator.check_schema(input_schema)
        Draft202012Validator.check_schema(decision_schema)
    except Exception as exc:
        raise EvaluatorValidationError(f"Invalid rule-pack JSON schema: {exc.message}") from exc

    for source in manifest["sources"]:
        if not isinstance(source, dict) or not all(key in source for key in ("id", "local_path", "sha256")):
            raise EvaluatorValidationError("Every source manifest entry requires id, local_path, and sha256")
        source_path = _local_path(REPO_ROOT, source["local_path"], f"source {source.get('id', '<unknown>')}")
        if sha256(source_path) != source["sha256"]:
            raise EvaluatorValidationError(f"Source hash mismatch for {source['id']}")
    return Pack(domain, pack_dir, manifest, parsed, input_schema, decision_schema)


def threshold_record(thresholds: dict[str, Any], evaluation_date: date) -> dict[str, Any] | None:
    """Pick the effective-dated record covering `evaluation_date`, else None."""
    for record in thresholds.get("records", []):
        start = as_date(record["effective_start"], "effective_start")
        end = as_date(record["effective_end"], "effective_end") if record.get("effective_end") else None
        if evaluation_date >= start and (end is None or evaluation_date <= end):
            return record
    return None

"""The template catalog: what each rule id and each missing-fact field means to a loan officer and to an examiner.

The catalog lives in `catalog/<domain>.yaml`, outside every rule `pack/`, so editing a sentence cannot change a `decision_id`
(`base_record` hashes pack files only). Entries are keyed by exact id or by a glob (`HMDA-LAR-*`, `monitoring.items.*`); the most
specific match wins. An id or field with no entry resolves to a generic entry whose `generic` flag is true, so callers and tests
can see and report the gap instead of inventing text.

Kinds (see plans/archive/response-templates/inventory.md): G information gap, V value or timing violation, R reviewer judgment,
P process or record fact (about what the institution did, never a request to the customer).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

CATALOG_DIR = Path(__file__).resolve().parent / "catalog"
KINDS = ("G", "V", "R", "P")
ROUTES = ("customer", "refer")
DOMAINS = ("ybs", "hpml", "trid", "hmda", "ecoa", "vmi", "fzd", "hvcre", "auditor")
_PREFIX = {"YBS": "ybs", "HPML": "hpml", "TRID": "trid", "HMDA": "hmda", "ECOA": "ecoa", "VMI": "vmi", "FZD": "fzd", "HVCRE": "hvcre", "AUD": "auditor"}
GENERIC_REFER = "A reviewer must check this item in the record."


class CatalogError(ValueError):
    pass


@dataclass(frozen=True)
class RuleEntry:
    domain: str
    match: str
    kind: str
    basis: str                 # "regulation" | "institution policy"
    cite: str
    requirement: str           # examiner part 1: the rule, in the regime's vocabulary
    action: str                # examiner part 5: what evidence or correction closes it
    who: str
    refer: str                 # one sentence for the "refer to compliance" list
    captures: tuple[str, ...] = ()
    generic: bool = False

    def text(self, value: str) -> str:
        return _fill(value, self.captures)


@dataclass(frozen=True)
class FieldEntry:
    domain: str
    match: str
    rule: str                  # the rule (id or glob) this missing fact belongs to; its kind decides the routing with `route`
    route: str                 # "customer" | "refer"
    label: str                 # a customer-facing name, never an internal path
    why: str                   # one or two short sentences
    decline: bool = False      # the applicant may decline; the decline is recorded
    captures: tuple[str, ...] = ()
    generic: bool = False

    def text(self, value: str) -> str:
        return _fill(value, self.captures)


def _fill(value: str, captures: tuple[str, ...]) -> str:
    return re.sub(r"\{(\d)\}", lambda m: captures[int(m.group(1)) - 1].replace("_", " ").replace("-", " ").lower(), value)


def _regex(pattern: str) -> re.Pattern[str]:
    """`*` matches one path segment (or one id segment); `**` matches anything, including dots and spaces."""
    segment = "([^.]+?)" if "." in pattern else "([A-Za-z0-9-]+?)"
    return re.compile("^" + "(.+?)".join(re.escape(part).replace(r"\*", segment) for part in pattern.split("**")) + "$")


def _specificity(pattern: str) -> tuple[int, int]:
    return (0 if "*" not in pattern else 1, -len(pattern.replace("*", "")))


def _check(entry: dict[str, Any], keys: tuple[str, ...], where: str) -> None:
    missing = [k for k in keys if not str(entry.get(k, "")).strip()]
    if missing:
        raise CatalogError(f"{where}: missing {', '.join(missing)}")


@lru_cache(maxsize=1)
def _load() -> dict[str, dict[str, list[tuple[re.Pattern[str], dict[str, Any]]]]]:
    loaded: dict[str, dict[str, list]] = {}
    for domain in DOMAINS:
        path = CATALOG_DIR / f"{domain}.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        rules, fields = data.get("rules") or [], data.get("fields") or []
        for entry in rules:
            where = f"{path.name} rule {entry.get('match')}"
            _check(entry, ("match", "kind", "basis", "cite", "requirement", "action", "who", "refer"), where)
            if entry["kind"] not in KINDS:
                raise CatalogError(f"{where}: kind must be one of {KINDS}")
        for entry in fields:
            where = f"{path.name} field {entry.get('match')}"
            _check(entry, ("match", "rule", "route", "label", "why"), where)
            if entry["route"] not in ROUTES:
                raise CatalogError(f"{where}: route must be one of {ROUTES}")
        loaded[domain] = {
            "rules": sorted(((_regex(e["match"]), e) for e in rules), key=lambda p: _specificity(p[1]["match"])),
            "fields": sorted(((_regex(e["match"]), e) for e in fields), key=lambda p: _specificity(p[1]["match"])),
        }
    return loaded


def domain_of(rule_id: str) -> str | None:
    return _PREFIX.get(rule_id.split("-", 1)[0])


def resolve_rule(rule_id: str) -> RuleEntry:
    """The entry for a rule id; a made-up id gets the generic entry (`generic` is true) and is never silently covered."""
    domain = domain_of(rule_id)
    for regex, entry in (_load().get(domain or "", {}).get("rules") or []):
        found = regex.match(rule_id)
        if found:
            return RuleEntry(domain=domain or "", match=entry["match"], kind=entry["kind"], basis=entry["basis"], cite=entry["cite"],
                             requirement=entry["requirement"], action=entry["action"], who=entry["who"], refer=entry["refer"],
                             captures=found.groups())
    return RuleEntry(domain=domain or "", match="*", kind="R", basis="regulation", cite="the rule pack", generic=True,
                     requirement=f"Rule {rule_id} applies to this case.", action="A reviewer checks the record for this rule.",
                     who="compliance reviewer", refer=GENERIC_REFER)


def resolve_field(domain: str, field_name: str) -> FieldEntry:
    """The entry for a missing-fact field in one regime; an unknown field is generic and routed to a reviewer, never to the customer."""
    for regex, entry in (_load().get(domain, {}).get("fields") or []):
        found = regex.match(field_name)
        if found:
            return FieldEntry(domain=domain, match=entry["match"], rule=entry["rule"], route=entry["route"], label=entry["label"],
                              why=entry["why"], decline=bool(entry.get("decline", False)), captures=found.groups())
    return FieldEntry(domain=domain, match="*", rule="", route="refer", label="an item in the record", why=GENERIC_REFER, generic=True)

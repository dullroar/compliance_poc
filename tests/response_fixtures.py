"""Decision records for the response-template tests, produced by the real evaluators.

`records()` returns {domain: [(label, decision)]}. The base cases are the ones the evaluator suites already use (the YBS
`scenarios.json` fixture, `sample_loan.json`, and each domain suite's `case()`); every leaf of a base case is also deleted
or flipped one at a time, so the sweep reaches the missing-fact and failure branches a single good case never takes.
Synthetic data only.
"""
from __future__ import annotations

import ast
import copy
import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))      # the evaluator suites import their siblings by bare name
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from compliance_common.pack import EvaluatorValidationError  # noqa: E402

DOMAINS = ("ybs", "hpml", "trid", "hmda", "ecoa", "vmi", "fzd", "hvcre", "auditor")


def _evaluators() -> dict[str, Any]:
    from compliance_mcp.ecoa import evaluate_ecoa
    from compliance_mcp.fzd import evaluate_fzd
    from compliance_mcp.hmda import evaluate_hmda
    from compliance_mcp.hpml import evaluate_hpml
    from compliance_mcp.hvcre import evaluate_hvcre
    from compliance_mcp.trid import evaluate_trid
    from compliance_mcp.vmi import evaluate_vmi
    from compliance_mcp.ybs import evaluate_ybs
    from compliance_mcp.auditor import evaluate_auditor
    return {"ybs": evaluate_ybs, "hpml": evaluate_hpml, "trid": evaluate_trid, "hmda": evaluate_hmda, "ecoa": evaluate_ecoa,
            "vmi": evaluate_vmi, "fzd": evaluate_fzd, "hvcre": evaluate_hvcre, "auditor": evaluate_auditor}


def _leaf_paths(value: Any, prefix: tuple = ()) -> list[tuple]:
    if isinstance(value, dict):
        out: list[tuple] = []
        for key, child in value.items():
            out.extend(_leaf_paths(child, prefix + (key,)))
        return out or [prefix]
    if isinstance(value, list):
        out = []
        for index, child in enumerate(value):
            out.extend(_leaf_paths(child, prefix + (index,)))
        return out or [prefix]
    return [prefix]


def _get(root: Any, path: tuple) -> Any:
    for key in path:
        root = root[key]
    return root


def _mutations(base: dict[str, Any]):
    """The base case, then each leaf deleted, then each boolean flipped."""
    yield "base", base
    for path in _leaf_paths(base):
        if not path:
            continue
        deleted = copy.deepcopy(base)
        parent = _get(deleted, path[:-1])
        if isinstance(parent, dict):
            del parent[path[-1]]
            yield "drop " + ".".join(map(str, path)), deleted
        value = _get(base, path)
        if isinstance(value, bool):
            flipped = copy.deepcopy(base)
            _get(flipped, path[:-1])[path[-1]] = not value
            yield "flip " + ".".join(map(str, path)), flipped


_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VALUE_DOMAINS = ("hpml", "trid", "ecoa", "vmi", "fzd", "hvcre", "auditor", "hmda")


def _value_mutations(base: dict[str, Any], hmda: bool):
    """Dates moved 45 days either way and numbers scaled, so rules that fail on a value (late notice, low coverage) are reached too."""
    from datetime import date, timedelta
    for path in _leaf_paths(base):
        if not path:
            continue
        value = _get(base, path)
        if hmda and path[0] not in ("action_taken_date", "application_date", "amount", "apr", "apor", "reported_rate_spread"):
            continue
        if isinstance(value, str) and _DATE.match(value):
            for days in (45, -45):
                changed = copy.deepcopy(base)
                _get(changed, path[:-1])[path[-1]] = (date.fromisoformat(value) + timedelta(days=days)).isoformat()
                yield f"shift {days:+d}d " + ".".join(map(str, path)), changed
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            for factor in (3, 0.2):
                changed = copy.deepcopy(base)
                _get(changed, path[:-1])[path[-1]] = round(value * factor, 4) if isinstance(value, float) else int(value * factor)
                yield f"scale {factor} " + ".".join(map(str, path)), changed


def _base_cases() -> dict[str, list[dict[str, Any]]]:
    import test_auditor_evaluator as auditor
    import test_ecoa_evaluator as ecoa
    import test_fzd_evaluator as fzd
    import test_hmda_evaluator as hmda
    import test_hpml_evaluator as hpml
    import test_hvcre_evaluator as hvcre
    import test_trid_evaluator as trid
    import test_vmi_evaluator as vmi

    sample = json.loads((ROOT / "sample_loan.json").read_text(encoding="utf-8"))
    scenarios = json.loads((ROOT / "tests/fixtures/ybs/scenarios.json").read_text(encoding="utf-8"))
    bases = {
        "ybs": [s["case"] for s in scenarios] + [sample["ybs_case"]],
        "hpml": [hpml.case(), sample["hpml_case"]], "trid": [trid.case(), sample["trid_case"]],
        "hmda": [hmda.case(), sample["hmda_case"]], "ecoa": [ecoa.case(), sample["ecoa_case"]],
        "vmi": [vmi.case(), sample["vmi_case"]], "fzd": [fzd.case(), sample["fzd_case"]],
        "hvcre": [hvcre.case(), sample["hvcre_case"]], "auditor": [auditor.good_case()],
    }
    return bases


@lru_cache(maxsize=1)
def records() -> dict[str, list[tuple[str, dict[str, Any]]]]:
    evaluators, out = _evaluators(), {}
    for domain, cases in _base_cases().items():
        seen: set[str] = set()
        found = []
        for number, base in enumerate(cases):
            variants = list(_mutations(base))
            if domain in VALUE_DOMAINS and number < 2:
                variants += list(_value_mutations(base, domain == "hmda"))
            for label, case in variants:
                try:
                    decision = evaluators[domain](case)
                except EvaluatorValidationError:
                    continue
                if decision["decision_id"] in seen:
                    continue
                seen.add(decision["decision_id"])
                found.append((f"{domain}#{number} {label}", decision))
        out[domain] = found
    return out


def failing_findings(decision: dict[str, Any]) -> list[dict[str, Any]]:
    return [r for r in decision.get("rule_results", []) if r.get("outcome") in ("not_satisfied", "unable_to_determine", "review_required")]


# --- ids and fields read from the evaluator source, so a rule no fixture happens to trigger is still covered --------------

_ID = re.compile(r"^(?:YBS|HPML|TRID|HMDA|ECOA|VMI|FZD|HVCRE|AUD)-[A-Z0-9]+(?:-[A-Z0-9]+)*$")
_PREFIXES = ("YBS-", "HPML-", "TRID-", "HMDA-", "ECOA-", "VMI-", "FZD-", "HVCRE-", "AUD-")


def _sources() -> list[Path]:
    return sorted((ROOT / "compliance_mcp").glob("*/rules.py")) + [ROOT / "compliance_mcp/hmda/lar.py"]


def static_rule_ids() -> set[str]:
    """Literal rule ids in the evaluators plus every member of the run-time families (LAR items, exclusions, VMI items, YBS categories)."""
    found: set[str] = set()
    suffixes = {"ATTRIBUTION"}
    for path in _sources():
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and _ID.match(node.value):
                found.add(node.value)
            elif isinstance(node, ast.Call) and getattr(node.func, "id", "") == "attribution_review" and len(node.args) > 1 \
                    and isinstance(node.args[1], ast.Constant):
                suffixes.add(node.args[1].value)
    from compliance_mcp.hmda.rules import _EXCLUSION_CITES
    from compliance_mcp.vmi.rules import ITEMS, OBSERVED
    lar = yaml.safe_load((ROOT / "compliance_mcp/hmda/pack/lar_items.yaml").read_text(encoding="utf-8"))
    found |= {f"HMDA-LAR-{item['number']:02d}" for item in lar["items"]}
    found |= {"HMDA-EXCL-" + key.upper().replace("_", "-") for key in _EXCLUSION_CITES}
    found |= {"VMI-REQUEST-" + name.upper().replace("_", "-") for name in ITEMS}
    found |= {"VMI-OBSERVATION-" + name.upper().replace("_", "-") for name in OBSERVED}
    for category in ("YOUNG", "BEGINNING", "SMALL"):
        found.add(f"YBS-PERSON-{category}-PRODUCER")
        found |= {f"YBS-ENTITY-{category}-{suffix}" for suffix in suffixes}
    return found


def static_fields() -> dict[str, set[str]]:
    """Missing-fact field names per regime, read from the evaluator source; each f-string substitution is shown as `x`.

    Sources: `missing.append({"field": ...})`, `fact(subject, "field", ...)`, and for HMDA the register fields (`lar.get("x")`)
    and context flags (`ctx.need("x")`) that the item judgments report as missing."""
    found: dict[str, set[str]] = {}
    for path in _sources():
        domain = "hmda" if path.name == "lar.py" else path.parent.name
        names = found.setdefault(domain, set())

        def take(node: ast.AST | None, prefix: str = "") -> None:
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                names.add(prefix + node.value)
            elif isinstance(node, ast.JoinedStr):
                names.add(prefix + "".join(v.value if isinstance(v, ast.Constant) else "x" for v in node.values))

        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call):
                continue
            attr = node.func.attr if isinstance(node.func, ast.Attribute) else ""
            owner = getattr(node.func.value, "id", "") if isinstance(node.func, ast.Attribute) else ""
            if attr == "append" and owner == "missing" and node.args and isinstance(node.args[0], ast.Dict):
                for key, value in zip(node.args[0].keys, node.args[0].values):
                    if isinstance(key, ast.Constant) and key.value == "field":
                        take(value)
            elif getattr(node.func, "id", "") == "fact" and len(node.args) > 1:
                take(node.args[1])
            elif path.name == "lar.py" and attr == "get" and owner == "lar" and node.args:
                take(node.args[0], "lar.")
            elif path.name == "lar.py" and attr == "need" and owner == "ctx" and node.args:
                take(node.args[0], "lar_context.")
    return found


def base_case(domain: str, index: int = 0) -> dict[str, Any]:
    return copy.deepcopy(_base_cases()[domain][index])


def evaluate(domain: str, case: dict[str, Any]) -> dict[str, Any]:
    return _evaluators()[domain](case)


def without(case: dict[str, Any], dotted: str) -> dict[str, Any]:
    """A copy of `case` with the leaf at `dotted` (keys separated by dots) removed."""
    changed = copy.deepcopy(case)
    *parents, leaf = dotted.split(".")
    node = changed
    for key in parents:
        node = node[int(key)] if isinstance(node, list) else node[key]
    del node[leaf]
    return changed


@lru_cache(maxsize=None)
def failing_case(domain: str) -> dict[str, Any]:
    """A case for `domain` (from the same mutations as the sweep) whose evaluation has at least one finding."""
    evaluate_ = _evaluators()[domain]
    for base in _base_cases()[domain][::-1]:
        for label, case in list(_mutations(base)) + list(_value_mutations(base, domain == "hmda")):
            try:
                decision = evaluate_(case)
            except EvaluatorValidationError:
                continue
            if failing_findings(decision):
                return copy.deepcopy(case)
    raise LookupError(f"no failing case found for {domain}")

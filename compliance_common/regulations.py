"""The regulation text an agent is given: the pinned snapshots from the domain's rule pack, nothing else.

Agents write narrative from (a) the tool's decision record and (b) this text. They do no research and rely on no
remembered law. The text comes from the same hashed files the evaluator was validated against, so the prompt can
never drift from the evaluator. A manifest source may carry `excerpt: {start, end}` markers to include only the
relevant part of a long section (for example the HVCRE definition inside 12 CFR 628.2).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .obs import get_logger
from .pack import REPO_ROOT
from .text import normalize

log = get_logger("regulations", "1")
DEFAULT_BUDGET = 60000


def _manifest(domain: str) -> dict[str, Any]:
    return yaml.safe_load((REPO_ROOT / "compliance_mcp" / domain / "pack" / "manifest.yaml").read_text(encoding="utf-8"))


def authorities(domain: str) -> list[dict[str, Any]]:
    """Regulatory sources of the pack: citation, issue date, url, sha256, local path."""
    return [s for s in _manifest(domain)["sources"] if s.get("type") == "regulatory"]


def _excerpt(text: str, marks: dict[str, str] | None, citation: str) -> str:
    if not marks:
        return text
    start = text.find(marks["start"])
    if start < 0:
        log.warning("excerpt start marker not found for %s; including the whole section", citation)
        return text
    end = text.find(marks["end"], start + len(marks["start"])) if marks.get("end") else -1
    return text[start:end if end > start else len(text)].strip()


@lru_cache(maxsize=64)
def regulation_text(domain: str, budget: int = DEFAULT_BUDGET) -> tuple[str, list[dict[str, str]]]:
    """Return (text, provenance). Text is "" when the pack has no regulatory sources (for example the auditor)."""
    parts, provenance, used = [], [], 0
    for source in authorities(domain):
        body = _excerpt(normalize((REPO_ROOT / source["local_path"]).read_bytes()), source.get("excerpt"), source["citation"])
        if used + len(body) > budget:
            body = body[: max(0, budget - used)]
            log.warning("regulation text for %s truncated at %d characters", domain, budget)
        if not body:
            continue
        parts.append(f"### {source['citation']} (eCFR text issued {source.get('issue_date', 'n/a')}; sha256 {source['sha256'][:12]})\n{body}")
        provenance.append({"citation": source["citation"], "issue_date": str(source.get("issue_date", "")), "sha256": source["sha256"], "characters": str(len(body))})
        used += len(body)
    return "\n\n".join(parts), provenance

"""Read, bump and write the versions that live inside artifacts (never in filenames)."""
from __future__ import annotations

import re
from pathlib import Path

_SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
_EVALUATOR = re.compile(r'^(EVALUATOR_VERSION\s*=\s*")([^"]+)(")', re.M)
_PACK = re.compile(r"^(version:\s*)(\S+)\s*$", re.M)
_PROMPT = re.compile(r"(\| Agent Version: )(\d+\.\d+\.\d+)")


def bump(version: str, part: str = "patch") -> str:
    match = _SEMVER.match(version)
    if not match:
        raise ValueError(f"not a semver: {version!r}")
    major, minor, patch = map(int, match.groups())
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"unknown part {part!r}")


def _read(pattern: re.Pattern, text: str, group: int = 2) -> str:
    match = pattern.search(text)
    if not match:
        raise ValueError("version marker not found")
    return match.group(group)


def evaluator_version(rules: Path) -> str:
    return _read(_EVALUATOR, rules.read_text(encoding="utf-8"))


def pack_version(manifest: Path) -> str:
    return _read(_PACK, manifest.read_text(encoding="utf-8"))


def prompt_version(prompt: Path) -> str:
    return _read(_PROMPT, prompt.read_text(encoding="utf-8").split("\n", 1)[0])


def _set(path: Path, pattern: re.Pattern, version: str, first_line_only: bool = False) -> None:
    text = path.read_text(encoding="utf-8")
    if first_line_only:
        head, _, rest = text.partition("\n")
        path.write_text(pattern.sub(lambda m: m.group(1) + version + (m.group(3) if m.lastindex and m.lastindex >= 3 else ""), head, count=1) + "\n" + rest, encoding="utf-8")
    else:
        path.write_text(pattern.sub(lambda m: m.group(1) + version + (m.group(3) if m.lastindex and m.lastindex >= 3 else ""), text, count=1), encoding="utf-8")


def set_evaluator_version(rules: Path, version: str) -> None:
    _set(rules, _EVALUATOR, version)


def set_pack_version(manifest: Path, version: str) -> None:
    _set(manifest, _PACK, version)


def set_prompt_version(prompt: Path, version: str) -> None:
    _set(prompt, _PROMPT, version, first_line_only=True)

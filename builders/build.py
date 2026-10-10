"""Deterministic build harness for the MCP-builder and agent-builder agents.

  python -m builders.build check [--domain D ...]      fetch sources, report what changed (writes nothing)
  python -m builders.build lock  [--domain D ...]      record current source hashes as reviewed/accepted
  python -m builders.build run   [--domain D ...] [--apply] [--provider P] [--model M]

`run` rebuilds ONLY domains whose sources changed (or are new). Without --apply it stages the
builders' proposed files under builds/<domain>/<run_id>/ for review. With --apply it also writes
snapshots, syncs the pack manifest's sources, writes the files, bumps only the versions of
components that changed, runs the domain's tests, and rolls everything back if they fail.
The LLM never decides whether something changed, which paths it may write, or what version
number results; code does.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable

import yaml

from agent_prompts import load_agent
from agents.runner import extract_json
from compliance_common.obs import get_logger
from compliance_common.versioning import (
    bump, evaluator_version, pack_version, prompt_version, set_evaluator_version, set_pack_version, set_prompt_version,
)

from .prompts import inject_tool_blocks
from .sourcing import (
    BUILDERS_DIR, DomainStatus, Fetcher, LiveFetcher, ManualSource, check, load_lock, load_registry, lock_entry, normalize, save_lock,
)

REPO = Path(__file__).resolve().parent.parent
MAX_SNAPSHOT_CHARS = 30000
MAX_DIFF_CHARS = 8000
EXAMPLE_DOMAINS = ("hpml", "trid")
log = get_logger("builder", "0.1.0")
TestRunner = Callable[[str, Path], tuple[bool, str]]


def allowed_mcp_path(domain: str, rel: str) -> bool:
    """Paths the MCP builder may write for a domain (never snapshots, never other domains)."""
    parts = Path(rel).parts
    if ".." in parts or Path(rel).is_absolute():
        return False
    posix = Path(rel).as_posix()
    if posix.startswith(f"compliance_mcp/{domain}/pack/sources/"):
        return False
    return bool(
        re.fullmatch(rf"compliance_mcp/{re.escape(domain)}/.+", posix)
        or posix == f"tests/test_{domain}_evaluator.py"
        or re.fullmatch(rf"tests/fixtures/{re.escape(domain)}/.+", posix)
    )


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def narrative_contract() -> str:
    return (BUILDERS_DIR / "narrative_contract.md").read_text(encoding="utf-8")


def assemble_prompt(header_fields: dict[str, str], body: str) -> str:
    header = (f"Agent: {header_fields['key']} | Name: {header_fields['name']} | Agent Version: {header_fields['version']} | "
              f"Track: {header_fields['track']} | Tool: {header_fields['tool']} | Output: json")
    text = header + "\n\n" + body.strip() + "\n\n" + narrative_contract()
    return inject_tool_blocks(text, header_fields["tool"], header_fields["case_key"] if "case_key" in header_fields else f"{header_fields['key']}_case")


def run_unittests(domain: str, repo: Path) -> tuple[bool, str]:
    proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", f"test_{domain}*.py"],
                          cwd=repo, capture_output=True, text=True, timeout=600)
    return proc.returncode == 0, (proc.stdout + proc.stderr)[-4000:]


@dataclass
class DomainReport:
    domain: str
    state: str = "skipped"          # skipped | staged | applied | failed
    changed_sources: list[str] = field(default_factory=list)
    manual_sources: list[str] = field(default_factory=list)
    rejected_paths: list[str] = field(default_factory=list)
    files_written: list[str] = field(default_factory=list)
    versions: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    needs_human_review: list[str] = field(default_factory=list)
    test_output: str = ""
    stage_dir: str = ""


def _context(repo: Path, domain: str, entry: dict, registry: dict, status: DomainStatus) -> dict[str, Any]:
    snapshots, diffs = {}, {}
    sources = {s["id"]: s for s in entry["sources"]}
    for item in status.changed:
        text = item.fetched.text
        snapshots[item.source_id] = text[:MAX_SNAPSHOT_CHARS]
        old_path = repo / sources[item.source_id].get("snapshot", "")
        if old_path.is_file():
            old = normalize(old_path.read_bytes(), sources[item.source_id].get("select_regex"))
            diff = "\n".join(difflib.unified_diff(re.split(r"(?<=[.;:]) ", old), re.split(r"(?<=[.;:]) ", text), "previous", "current", lineterm="", n=0))
            diffs[item.source_id] = diff[:MAX_DIFF_CHARS] or "(no textual difference in the stored snapshot)"
    existing = {}
    for path in sorted((repo / "compliance_mcp" / domain).rglob("*")) if (repo / "compliance_mcp" / domain).exists() else []:
        rel = path.relative_to(repo).as_posix()
        if path.is_file() and "/sources/" not in rel and "__pycache__" not in rel:
            existing[rel] = _read(path)
    test = repo / "tests" / f"test_{domain}_evaluator.py"
    if test.exists():
        existing[test.relative_to(repo).as_posix()] = _read(test)
    examples = {}
    for ex in EXAMPLE_DOMAINS:
        if ex == domain:
            continue
        for name in ("rules.py", "server.py", "adapter.py", "__init__.py"):
            p = repo / "compliance_mcp" / ex / name
            if p.exists():
                examples[p.relative_to(repo).as_posix()] = _read(p)
        for name in ("manifest.yaml", "input.schema.json"):
            p = repo / "compliance_mcp" / ex / "pack" / name
            if p.exists():
                examples[p.relative_to(repo).as_posix()] = _read(p)
    common = registry.get("common", {})
    return {"domain": domain, "agent_key": entry["agent_key"], "authority": entry["authority"], "registry_entry": entry,
            "spec_sites": {"mcp": entry.get("spec_sites", {}).get("mcp", []), "agent": entry.get("spec_sites", {}).get("agent", []), "common": common},
            "snapshots": snapshots, "diffs": diffs, "existing_files": existing, "reference_examples": examples}


def _ask(backend: Any, builder_file: str, payload: dict[str, Any]) -> dict[str, Any]:
    builder = load_agent(BUILDERS_DIR / builder_file)
    log.trace("builder system prompt", extra={"agent": builder["key"]}, payload=builder["system_prompt"])
    raw = backend.complete(builder["system_prompt"], [{"role": "user", "content": json.dumps(payload, indent=1)}], json_mode=True)
    log.trace("builder raw output", extra={"agent": builder["key"]}, payload=raw)
    parsed, error = extract_json(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f"{builder['key']} returned unparseable output: {error}")
    return parsed


def sync_manifest_sources(repo: Path, domain: str, entry: dict, fetched: dict[str, Any], today: str) -> None:
    """Deterministically update the pack manifest's source entries from the new snapshots."""
    path = repo / "compliance_mcp" / domain / "pack" / "manifest.yaml"
    manifest = yaml.safe_load(_read(path)) or {}
    sources = manifest.setdefault("sources", [])
    by_path = {s.get("local_path"): s for s in sources}
    import hashlib
    for src in entry["sources"]:
        if src["id"] not in fetched or not src.get("snapshot"):
            continue
        f = fetched[src["id"]]
        record = by_path.get(src["snapshot"])
        if record is None:
            record = {"id": f"{src['id']}-{f.as_of or today}", "type": src["type"], "citation": src["citation"]}
            sources.append(record)
        record.update({"id": f"{src['id']}-{f.as_of or today}", "url": f.url, "retrieved_date": today, "local_path": src["snapshot"],
                       "sha256": hashlib.sha256(f.raw).hexdigest()})
        if f.as_of:
            record["issue_date"] = f.as_of
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")


def build_domain(domain: str, status: DomainStatus, registry: dict, lock: dict, backend: Any, repo: Path = REPO,
                 apply: bool = False, test_runner: TestRunner = run_unittests, today: str | None = None) -> DomainReport:
    entry = registry["domains"][domain]
    today = today or date.today().isoformat()
    report = DomainReport(domain, changed_sources=[s.source_id for s in status.changed],
                          manual_sources=[s.source_id for s in status.sources if s.state == "manual"])
    errors = [s for s in status.sources if s.state == "error"]
    if errors:
        report.state, report.notes = "failed", [f"source fetch failed, domain not built: {s.source_id}: {s.detail}" for s in errors]
        return report
    if not status.needs_build:
        report.notes.append("no source changed; nothing to build")
        return report

    run_id = uuid.uuid4().hex[:8]
    stage = repo / "builds" / domain / run_id
    report.stage_dir = stage.relative_to(repo).as_posix()
    context = _context(repo, domain, entry, registry, status)
    mcp = _ask(backend, "mcp_builder.md", context)
    files: dict[str, str] = {}
    for rel, content in (mcp.get("files") or {}).items():
        if allowed_mcp_path(domain, rel) and isinstance(content, str):
            files[rel] = content
        else:
            report.rejected_paths.append(rel)
    report.notes += [str(n) for n in mcp.get("notes", [])]
    report.needs_human_review += [str(n) for n in mcp.get("needs_human_review", [])]

    # Agent prompt: needs the post-change schemas/rules, so stage the MCP files first.
    prompt_rel = f"prompts/{entry['agent_key']}.md"
    existing_prompt = _read(repo / prompt_rel)
    existing_header = load_agent(repo / prompt_rel) if existing_prompt else None
    overlay = lambda rel: files.get(rel) if rel in files else _read(repo / rel)  # noqa: E731
    pack_dir = f"compliance_mcp/{domain}/pack"
    agent_payload = {
        "domain": domain, "agent_key": entry["agent_key"], "authority": entry["authority"], "tool": f"{domain}_evaluate",
        "registry_entry": entry, "spec_sites": context["spec_sites"],
        "decision_schema": overlay(f"{pack_dir}/decision-record.schema.json"), "input_contract": overlay(f"{pack_dir}/input.schema.json"),
        "rules_source": overlay(f"compliance_mcp/{domain}/rules.py"), "adapter_source": overlay(f"compliance_mcp/{domain}/adapter.py"),
        "existing_prompt": existing_prompt, "long_form_spec": _read(repo / "specs" / f"{entry['agent_key']}.md")[:12000],
        "snapshots": context["snapshots"],
    }
    agent_out = _ask(backend, "agent_builder.md", agent_payload)
    body = agent_out.get("prompt_body")
    if not isinstance(body, str) or not body.strip():
        raise ValueError("agent_builder returned no prompt_body")
    report.notes += [str(n) for n in agent_out.get("notes", [])]
    report.needs_human_review += [str(n) for n in agent_out.get("needs_human_review", [])]
    header = {"key": entry["agent_key"], "name": entry.get("agent_name") or (existing_header or {}).get("name", entry["agent_key"]),
              "version": (existing_header or {}).get("version", "0.1.0"), "track": entry.get("agent_track") or (existing_header or {}).get("compliance_track", ""),
              "tool": f"{domain}_evaluate"}
    new_prompt = assemble_prompt(header, body)
    stage_files = dict(files)
    stage_files[prompt_rel] = new_prompt
    for rel, content in stage_files.items():
        target = stage / "files" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    (stage / "report.json").parent.mkdir(parents=True, exist_ok=True)
    report.state = "staged"
    if not apply:
        (stage / "report.json").write_text(json.dumps(report.__dict__, indent=2), encoding="utf-8")
        return report

    # ---- apply (with rollback) -------------------------------------------------------------
    touched: dict[Path, str | None] = {}

    def write(path: Path, content: str | bytes) -> None:
        touched.setdefault(path, path.read_bytes() if path.exists() else None)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))

    def rollback() -> None:
        for path, original in touched.items():
            if original is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(original)

    try:
        fetched = {s.source_id: s.fetched for s in status.changed}
        sources = {s["id"]: s for s in entry["sources"]}
        manifest_path = repo / pack_dir / "manifest.yaml"
        old_rules = _read(repo / f"compliance_mcp/{domain}/rules.py")
        old_pack_version = pack_version(manifest_path) if manifest_path.exists() else None
        old_eval_version = evaluator_version(repo / f"compliance_mcp/{domain}/rules.py") if old_rules else None
        for rel, content in stage_files.items():
            write(repo / rel, content)
        for sid, f in fetched.items():
            write(repo / sources[sid]["snapshot"], f.raw)
        touched.setdefault(manifest_path, manifest_path.read_bytes() if manifest_path.exists() else None)
        sync_manifest_sources(repo, domain, entry, fetched, today)
        # Version bumps: only components whose content changed, and only if the builder did not bump them.
        rules_path = repo / f"compliance_mcp/{domain}/rules.py"
        if old_eval_version and rules_path.exists() and _read(rules_path) != old_rules and evaluator_version(rules_path) == old_eval_version:
            set_evaluator_version(rules_path, bump(old_eval_version, "minor"))
        if old_pack_version and pack_version(manifest_path) == old_pack_version:
            set_pack_version(manifest_path, bump(old_pack_version, "patch"))
        prompt_path = repo / prompt_rel
        if existing_header and prompt_version(prompt_path) == existing_header["version"] and _read(prompt_path) != existing_prompt:
            set_prompt_version(prompt_path, bump(existing_header["version"], "patch"))
        report.versions = {"pack": pack_version(manifest_path) if manifest_path.exists() else "",
                           "evaluator": evaluator_version(rules_path) if rules_path.exists() else "",
                           "agent": prompt_version(prompt_path)}
        ok, output = test_runner(domain, repo)
        report.test_output = output
        if not ok:
            rollback()
            report.state, report.versions = "failed", {}
            report.notes.append("tests failed; every change was rolled back and the lock was not updated")
            return report
    except Exception:
        rollback()
        raise
    report.files_written = sorted(stage_files)
    for sid, f in fetched.items():
        lock.setdefault("sources", {})[sid] = lock_entry(sources[sid], f)
    report.state = "applied"
    (stage / "report.json").write_text(json.dumps(report.__dict__, indent=2), encoding="utf-8")
    return report


def run_builds(domains: list[str] | None, backend: Any, fetcher: Fetcher, apply: bool, registry: dict | None = None,
               lock: dict | None = None, repo: Path = REPO, test_runner: TestRunner = run_unittests,
               lock_path: Path | None = None) -> list[DomainReport]:
    registry = registry or load_registry()
    lock = lock if lock is not None else load_lock()
    reports = []
    for status in check(registry, lock, fetcher, domains):
        report = build_domain(status.domain, status, registry, lock, backend, repo, apply, test_runner)
        reports.append(report)
        log.info("%s: %s", status.domain, report.state)
        if report.state == "applied":
            save_lock(lock, lock_path) if lock_path else save_lock(lock)
    return reports


def rebuild_prompts(keys: list[str] | None = None, prompts_dir: Path | None = None) -> dict[str, str]:
    """Deterministically (re)apply the standard tool/role blocks to every tool-backed prompt. Returns {key: old->new version}
    for prompts whose text changed (their agent version gets a patch bump). No model is involved."""
    from agent_prompts import PROMPTS_DIR, load_agent
    directory = prompts_dir or PROMPTS_DIR
    changed: dict[str, str] = {}
    for path in sorted(directory.glob("*.md")):
        agent = load_agent(path)
        if not agent.get("tool") or (keys and agent["key"] not in keys):
            continue
        old = path.read_text(encoding="utf-8")
        case_key = None if agent["key"] == "auditor" else f"{agent['key']}_case"
        new = inject_tool_blocks(old, agent["tool"], case_key)
        if new != old:
            path.write_text(new, encoding="utf-8")
            before = prompt_version(path)
            set_prompt_version(path, bump(before, "patch"))
            changed[agent["key"]] = f"{before} -> {prompt_version(path)}"
    return changed


def _print_status(statuses: list[DomainStatus]) -> None:
    for status in statuses:
        print(f"{status.domain}: {'REBUILD' if status.needs_build else 'up to date'}")
        for s in status.sources:
            print(f"    {s.state:<9} {s.source_id}  {s.detail}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Source-driven builder for MCP evaluators and agent prompts")
    sub = parser.add_subparsers(dest="mode", required=True)
    for name in ("check", "lock", "run", "prompts"):
        p = sub.add_parser(name)
        p.add_argument("--domain", nargs="+")
    run_p = sub.choices["run"]
    run_p.add_argument("--apply", action="store_true")
    run_p.add_argument("--provider", choices=["anthropic", "ollama"])
    run_p.add_argument("--model")
    args = parser.parse_args(argv)

    if args.mode == "prompts":
        changed = rebuild_prompts(args.domain)
        print("\n".join(f"{k}: prompt updated ({v})" for k, v in changed.items()) or "prompts already up to date")
        return 0
    registry, lock, fetcher = load_registry(), load_lock(), LiveFetcher()
    if args.mode == "check":
        statuses = check(registry, lock, fetcher, args.domain)
        _print_status(statuses)
        return 1 if any(s.needs_build for s in statuses) else 0
    if args.mode == "lock":
        for status in check(registry, lock, fetcher, args.domain):
            if not (REPO / "compliance_mcp" / status.domain / "pack" / "manifest.yaml").exists():
                print(f"{status.domain}: not built yet; not locking (a build must create it)")
                continue
            src = {s["id"]: s for s in registry["domains"][status.domain]["sources"]}
            for item in status.sources:
                if item.fetched is not None and item.state in ("new", "changed"):
                    lock.setdefault("sources", {})[item.source_id] = lock_entry(src[item.source_id], item.fetched)
        save_lock(lock)
        print("lock updated: accepts the current upstream text as reviewed")
        return 0
    from agents.backends import Backend
    reports = run_builds(args.domain, Backend(args.provider, args.model), fetcher, args.apply, registry, lock)
    for r in reports:
        print(f"{r.domain}: {r.state}" + (f" -> {r.stage_dir}" if r.stage_dir else ""))
        for n in r.needs_human_review:
            print(f"    REVIEW: {n}")
    return 0 if all(r.state in ("skipped", "staged", "applied") for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())

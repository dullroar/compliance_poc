"""Write the boilerplate of a new evaluator domain: pack files, manifest with hashed sources, module stubs.

Used for hand-written and builder-generated domains alike, so every domain has the same layout:
  compliance_mcp/<domain>/{__init__,server,adapter}.py   (rules.py is the domain's own code)
  compliance_mcp/<domain>/pack/{manifest.yaml, input.schema.json, decision-record.schema.json, <data>.yaml, sources/}
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from compliance_common.schema import decision_record_schema

REPO = Path(__file__).resolve().parent.parent

INIT = '''from .rules import EVALUATOR_VERSION, evaluate_{d}, validate_{d}_decision_record, validate_{d}_rule_pack

__all__ = ["EVALUATOR_VERSION", "evaluate_{d}", "validate_{d}_decision_record", "validate_{d}_rule_pack"]
'''
SERVER = '''"""MCP stdio server: `python -m compliance_mcp.{d}.server`."""
from compliance_common.mcp_server import build_server

from .rules import EVALUATOR_VERSION, evaluate_{d}

server = build_server("{d}", EVALUATOR_VERSION, "{desc}", evaluate_{d})

if __name__ == "__main__":
    server.run()
'''
ADAPTER = '''"""Maps a loan payload to the {D} tool call and a decision record to report extras."""
from compliance_common.adapter import make_adapter

from .rules import EVALUATOR_VERSION

_adapter = make_adapter("{d}", EVALUATOR_VERSION)
TOOL, tool_arguments, unavailable, extras = _adapter.TOOL, _adapter.tool_arguments, _adapter.unavailable, _adapter.extras
'''


def _dump_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def scaffold_domain(domain: str, description: str, classifications: list[str], input_schema: dict[str, Any],
                    data_files: dict[str, dict[str, Any]], regulatory: list[dict[str, Any]], today: str,
                    version: str = "0.1.0", status: str = "draft_engineering_review", repo: Path = REPO) -> Path:
    """regulatory: [{id, citation, url, issue_date, snapshot (repo-relative), raw (bytes)}]; data_files become
    institution-policy/reference yaml files in the pack and are hashed into the manifest."""
    root = repo / "compliance_mcp" / domain
    pack = root / "pack"
    (pack / "sources").mkdir(parents=True, exist_ok=True)
    fmt = {"d": domain, "D": domain.upper(), "desc": description}
    for name, template in (("__init__.py", INIT), ("server.py", SERVER), ("adapter.py", ADAPTER)):
        (root / name).write_text(template.format(**fmt), encoding="utf-8")
    _dump_json(pack / "input.schema.json", input_schema)
    _dump_json(pack / "decision-record.schema.json", decision_record_schema(f"{domain.upper()} deterministic decision record", classifications))
    files = {"input_schema": "input.schema.json", "decision_record_schema": "decision-record.schema.json"}
    sources: list[dict[str, Any]] = []
    for name, content in data_files.items():
        text = yaml.safe_dump(content, sort_keys=False, allow_unicode=True, width=100)
        (pack / f"{name}.yaml").write_text(text, encoding="utf-8")
        files[name] = f"{name}.yaml"
        sources.append({"id": f"pack-{domain}-{name.replace('_', '-')}", "type": content.get("source_type", "institution_policy"),
                        "citation": content.get("citation", f"{domain.upper()} pack {name}"),
                        "local_path": f"compliance_mcp/{domain}/pack/{name}.yaml",
                        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()})
    reg_sources = []
    for item in regulatory:
        target = repo / item["snapshot"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(item["raw"])
        reg_sources.append({"id": f"{item['id']}-{item['issue_date']}", "type": "regulatory", "citation": item["citation"], "url": item["url"],
                            "retrieved_date": today, "issue_date": item["issue_date"], "local_path": item["snapshot"],
                            "sha256": hashlib.sha256(item["raw"]).hexdigest()})
    manifest = {"id": domain, "version": version, "status": status, "git_revision": "uncommitted", "effective_date": today,
                "files": files, "sources": reg_sources + sources}
    (pack / "manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False, width=120), encoding="utf-8")
    return root

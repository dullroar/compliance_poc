"""Shared logging for evaluators, MCP/A2A servers, the orchestrator and the builders.

Levels (stdlib `logging`, plus TRACE below DEBUG):
  INFO   stage summaries: decision_id, classification, versions
  DEBUG  inputs/outputs, tool arguments
  TRACE  full prompts, raw model text, thinking, tool results (CoT-level dumps)

Every record carries run_id, component, component_version and any extra context
(decision_id, task_id). Set COMPLIANCE_LOG_LEVEL (default INFO) and
COMPLIANCE_LOG_DIR (default ./logs); records go to stderr and <dir>/<component>.jsonl.
stdout is never used: MCP stdio servers own it.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

TRACE = 5
logging.addLevelName(TRACE, "TRACE")

_RUN_ID = os.environ.get("COMPLIANCE_RUN_ID") or uuid.uuid4().hex[:12]
os.environ.setdefault("COMPLIANCE_RUN_ID", _RUN_ID)  # child processes (MCP servers) share the run id
_CONTEXT_KEYS = ("decision_id", "task_id", "agent", "tool")


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "run_id": _RUN_ID,
            "component": getattr(record, "component", record.name),
            "component_version": getattr(record, "component_version", ""),
            "msg": record.getMessage(),
        }
        for key in _CONTEXT_KEYS:
            if hasattr(record, key):
                entry[key] = getattr(record, key)
        if hasattr(record, "payload"):
            entry["payload"] = record.payload
        return json.dumps(entry, default=str, sort_keys=True)


class ComponentLogger(logging.LoggerAdapter):
    """Logger bound to a component name/version; adds .trace() and structured context."""

    def process(self, msg, kwargs):
        extra = dict(self.extra)
        extra.update(kwargs.pop("extra", {}))
        payload = kwargs.pop("payload", None)
        if payload is not None:
            extra["payload"] = payload
        kwargs["extra"] = extra
        return msg, kwargs

    def trace(self, msg: str, *args, **kwargs) -> None:
        self.log(TRACE, msg, *args, **kwargs)


def get_logger(component: str, version: str) -> ComponentLogger:
    """Return a logger for `component` at `version`, configuring handlers once."""
    base = logging.getLogger(f"compliance.{component}")
    if not base.handlers:
        level_name = os.environ.get("COMPLIANCE_LOG_LEVEL", "INFO").upper()
        level = TRACE if level_name == "TRACE" else getattr(logging, level_name, logging.INFO)
        base.setLevel(level)
        base.propagate = False
        formatter = _JsonFormatter()
        stderr = logging.StreamHandler(sys.stderr)
        stderr.setFormatter(formatter)
        base.addHandler(stderr)
        log_dir = Path(os.environ.get("COMPLIANCE_LOG_DIR", "logs"))
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_dir / f"{component}.jsonl", encoding="utf-8")
            file_handler.setFormatter(formatter)
            base.addHandler(file_handler)
        except OSError:
            base.warning("log directory %s unavailable; logging to stderr only", log_dir)
    return ComponentLogger(base, {"component": component, "component_version": version})

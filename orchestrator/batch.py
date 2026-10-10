"""Fan-out over A2A: domain agents concurrently, then the auditor, then (optionally) narrative."""
from __future__ import annotations

import asyncio
import contextlib
import sys
import time
from typing import Any

from agent_prompts import AGENTS
from compliance_common.obs import get_logger

from .a2a_client import send

AUDITOR_KEYS = ("auditor", "narrative")
log = get_logger("orchestrator", "1")


def domain_keys(config: dict[str, dict]) -> list[str]:
    return [k for k in config if k in AGENTS and k not in AUDITOR_KEYS]


def _failed(key: str, error: Exception) -> dict[str, Any]:
    return {"agent_key": key, "agent_name": AGENTS[key]["name"], "raw_text": "", "parsed": None,
            "parse_error": f"{type(error).__name__}: {error}"}


async def _one(key: str, config: dict[str, dict], payload: Any, verbose: bool,
               gate: asyncio.Semaphore | None = None) -> dict[str, Any]:
    async with gate or contextlib.nullcontext():
        if verbose:
            print(f"  [{key}] running...", file=sys.stderr, flush=True)
        started = time.monotonic()
        try:
            result = await send(config[key]["url"], payload)
        except Exception as exc:  # one failing agent must not sink the batch
            log.error("agent %s failed: %s", key, exc)
            result = _failed(key, exc)
        seconds = time.monotonic() - started
        result.setdefault("elapsed_seconds", round(seconds, 1))
        log.info("agent %s finished in %.1fs", key, seconds)
        if verbose:
            ok = result.get("parsed") or (result.get("parse_error") is None and result.get("raw_text"))   # markdown agents have no parsed JSON
            status = "OK" if ok else f"FAILED: {result.get('parse_error')}"
            print(f"  [{key}] {status} ({seconds:.0f}s)", file=sys.stderr, flush=True)
    return result


def _as_text_or_parsed(results: dict[str, dict]) -> dict[str, Any]:
    return {k: v["parsed"] if v.get("parsed") is not None else v.get("raw_text", "") for k, v in results.items()}


async def run_batch(loan_data: Any, config: dict[str, dict], agents: list[str] | None = None,
                    verbose: bool = True, concurrency: int = 1) -> dict[str, dict]:
    """Run domain agents (at most `concurrency` at a time), then the auditor over their results."""
    keys = agents or domain_keys(config)
    unknown = [k for k in keys if k not in config or k not in AGENTS]
    if unknown:
        raise ValueError(f"Unknown or unconfigured agent keys: {unknown}. Configured: {list(config)}")
    gate = asyncio.Semaphore(concurrency)
    outcomes = await asyncio.gather(*(_one(k, config, loan_data, verbose, gate) for k in keys))
    results = dict(zip(keys, outcomes))
    auditor_input = {"loan_data": loan_data if isinstance(loan_data, dict) else {},
                     "agent_results": _as_text_or_parsed(results)}
    results["auditor"] = await _one("auditor", config, auditor_input, verbose)
    return results


async def run_narrative(results: dict[str, dict], config: dict[str, dict], verbose: bool = True) -> dict:
    return await _one("narrative", config, _as_text_or_parsed(results), verbose)

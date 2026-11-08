"""Fan-out over A2A: domain agents concurrently, then the auditor, then (optionally) narrative."""
from __future__ import annotations

import asyncio
import contextlib
import re
import sys
import time
from typing import Any

from agent_prompts import AGENTS
from agents.backends import default_provider
from compliance_common.obs import get_logger

from .a2a_client import send

AUDITOR_KEYS = ("auditor", "narrative")
DEFAULT_REMOTE_CONCURRENCY = 2
RATE_LIMIT = re.compile(r"rate.?limit|\b429\b|too many requests", re.IGNORECASE)
RETRY_AFTER = re.compile(r"retry-after\W+(\d+(?:\.\d+)?)", re.IGNORECASE)
log = get_logger("orchestrator", "1")


def domain_keys(config: dict[str, dict]) -> list[str]:
    return [k for k in config if k in AGENTS and k not in AUDITOR_KEYS]


def resolve_provider(entry: dict, provider: str | None = None) -> str:
    """An agent's provider: its own entry, else the CLI choice, else COMPLIANCE_PROVIDER, else anthropic."""
    return (entry.get("provider") or provider or default_provider()).lower()


def gate_class(provider: str) -> str:
    """Local Ollama calls share one gate; Anthropic and OpenAI calls share another."""
    return "local" if provider == "ollama" else "remote"


def retry_after(text: str) -> str | None:
    found = RETRY_AFTER.search(text or "")
    return found.group(1) if found else None


def rate_limited_roles(results: dict[str, dict]) -> list[str]:
    """Roles whose failure names a rate limit (a 429 that survived the SDK's own retries)."""
    return [k for k, v in results.items() if v.get("parsed") is None and RATE_LIMIT.search(v.get("parse_error") or "")]


def _failed(key: str, error: Exception) -> dict[str, Any]:
    return {"agent_key": key, "agent_name": AGENTS[key]["name"], "raw_text": "", "parsed": None,
            "parse_error": f"{type(error).__name__}: {error}"}


async def _one(key: str, config: dict[str, dict], payload: Any, verbose: bool,
               *gates: asyncio.Semaphore | None) -> dict[str, Any]:
    async with contextlib.AsyncExitStack() as stack:
        for gate in gates:      # the class gate first, then the overall cap, so a waiting agent never holds an overall slot
            if gate is not None:
                await stack.enter_async_context(gate)
        if verbose:
            print(f"  [{key}] running...", file=sys.stderr, flush=True)
        started = time.monotonic()
        try:
            result = await send(config[key]["url"], payload)
        except Exception as exc:  # one failing agent must not sink the batch
            hint = retry_after(str(exc))
            log.error("agent %s failed: %s%s", key, exc, f" (retry-after {hint}s)" if hint and RATE_LIMIT.search(str(exc)) else "")
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
    """What downstream stages see of each result: the parsed result, else the raw text, else the failure evidence.

    A failed agent is never an empty string: absence must not read as a pass. The failure record has no `domain_determination`,
    so the auditor still classes it as a failed agent."""
    return {k: v["parsed"] if v.get("parsed") is not None else v.get("raw_text")
            or {"agent_key": k, "status": "failed", "failure": v.get("parse_error") or "the agent returned no output"}
            for k, v in results.items()}


async def run_batch(loan_data: Any, config: dict[str, dict], agents: list[str] | None = None, verbose: bool = True,
                    concurrency: int | None = None, remote_concurrency: int | None = None, local_concurrency: int | None = None,
                    provider: str | None = None) -> dict[str, dict]:
    """Run domain agents concurrently, then the auditor over their results.

    Agents whose provider is ollama share one gate (`local_concurrency`); the others share a gate of `remote_concurrency`
    (default 2). An explicit `concurrency` is also an overall cap, and alone it sets both widths as it always did."""
    keys = agents or domain_keys(config)
    unknown = [k for k in keys if k not in config or k not in AGENTS]
    if unknown:
        raise ValueError(f"Unknown or unconfigured agent keys: {unknown}. Configured: {list(config)}")
    widths = {"local": local_concurrency or concurrency or 1,
              "remote": remote_concurrency or concurrency or DEFAULT_REMOTE_CONCURRENCY}
    gates = {kind: asyncio.Semaphore(width) for kind, width in widths.items()}
    overall = asyncio.Semaphore(concurrency) if concurrency else None
    outcomes = await asyncio.gather(*(_one(k, config, loan_data, verbose, gates[gate_class(resolve_provider(config[k], provider))], overall)
                                      for k in keys))
    results = dict(zip(keys, outcomes))
    limited = rate_limited_roles(results)
    if limited:
        print(f"  {len(limited)} {'role' if len(limited) == 1 else 'roles'} failed on rate limits: {', '.join(limited)}", file=sys.stderr, flush=True)
    auditor_input = {"loan_data": loan_data if isinstance(loan_data, dict) else {},
                     "agent_results": _as_text_or_parsed(results)}
    results["auditor"] = await _one("auditor", config, auditor_input, verbose)
    return results


async def run_narrative(results: dict[str, dict], config: dict[str, dict], verbose: bool = True) -> dict:
    return await _one("narrative", config, _as_text_or_parsed(results), verbose)

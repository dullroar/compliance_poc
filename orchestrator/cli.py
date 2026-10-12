"""
orchestrator.cli
----------------
Compliance agent orchestration for Farm Credit ACA loan review.

Every agent is an A2A server (see agents.yaml); batch mode fans a loan out to them
over A2A, concurrently, then runs the auditor (and optionally the narrative agent).
Chat mode talks to one agent in-process so the REPL can keep conversation history.

  python -m orchestrator.cli serve [--provider P] [--model M]      start all local agents
  python -m orchestrator.cli batch loan.json                        use already-running agents
  python -m orchestrator.cli batch loan.json --spawn-local          start local agents for this run
  python -m orchestrator.cli chat hmda

Environment:
  COMPLIANCE_PROVIDER optional, "anthropic" (default) or "ollama"
  COMPLIANCE_MODEL    optional, provider-specific model name
  OLLAMA_BASE_URL     optional, default http://localhost:11434
  OLLAMA_TIMEOUT      optional, request timeout in seconds, default 300
  ANTHROPIC_API_KEY   required only for the Anthropic provider
  COMPLIANCE_LOG_LEVEL / COMPLIANCE_LOG_DIR   INFO|DEBUG|TRACE, default ./logs
"""

import argparse
import asyncio
import json
import os
import sys
import textwrap
import time
from datetime import datetime, timezone
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False

from agent_prompts import AGENTS
from agents.backends import Backend, default_provider, model_name as _model_name
from agents.runner import run

from .batch import run_batch, run_narrative
from .config import DEFAULT_CONFIG, is_local, load_agents, load_settings
from .launcher import serve_one, spawn_local

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_PROVIDER = default_provider()
AGENT_KEYS: list[str] = list(AGENTS.keys())
DOMAIN_AGENT_KEYS: list[str] = [k for k in AGENT_KEYS if k not in ("auditor", "narrative")]


def _client(provider: str | None = None) -> Any:
    return Backend(provider or DEFAULT_PROVIDER).client


# ---------------------------------------------------------------------------
# Single-agent call (one loan payload → raw JSON string)
# ---------------------------------------------------------------------------

def call_agent(
    agent_key: str,
    loan_data: dict | str,
    conversation_history: list[dict] | None = None,
    client: Any | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> dict:
    """
    Send loan_data (dict or narrative string) to a single compliance agent.

    If conversation_history is provided, it is prepended so the agent has
    prior turn context (used by the REPL).

    Returns a dict with:
      {
        "agent_key":   str,
        "agent_name":  str,
        "raw_text":    str,          # full model response text
        "parsed":      dict | None,  # JSON-parsed result, or None on parse failure
        "parse_error": str | None,   # parse error message if parsing failed
        "timestamp":   str,          # ISO-8601
      }
    """
    if agent_key not in AGENTS:
        raise ValueError(
            f"Unknown agent '{agent_key}'. Valid keys: {AGENT_KEYS}"
        )

    backend = Backend((provider or DEFAULT_PROVIDER).lower(), model, client=client)
    return run(agent_key, loan_data, backend, conversation_history)


# ---------------------------------------------------------------------------
# REPL: interactive chat with a single agent
# ---------------------------------------------------------------------------

def repl(
    agent_key: str,
    provider: str | None = None,
    model: str | None = None,
) -> None:
    """
    Start an interactive REPL session with the named compliance agent.

    The conversation history is maintained in-memory for the session.
    Type 'exit' or 'quit' to end the session.
    Type 'reset' to clear history and start a new session with the same agent.
    Type 'history' to print the current conversation turn count.
    Type 'save <filename>' to write the full conversation + last parsed result to JSON.
    """
    if agent_key not in AGENTS:
        print(f"Unknown agent '{agent_key}'. Valid keys: {AGENT_KEYS}")
        sys.exit(1)

    agent = AGENTS[agent_key]
    selected_provider = (provider or DEFAULT_PROVIDER).lower()
    selected_model = _model_name(selected_provider, model)
    c = _client(selected_provider)
    history: list[dict] = []
    last_result: dict | None = None

    _banner(agent)

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSession ended.")
            break

        if not user_input:
            continue

        cmd = user_input.lower()

        if cmd in ("exit", "quit"):
            print("Session ended.")
            break

        if cmd == "reset":
            history = []
            last_result = None
            print("[Session reset. History cleared.]")
            continue

        if cmd == "history":
            turns = len(history) // 2
            print(f"[{turns} turn(s) in current session]")
            continue

        if cmd.startswith("save "):
            filename = user_input[5:].strip()
            _save_session(filename, agent_key, history, last_result)
            continue

        # Normal turn
        result = call_agent(
            agent_key,
            user_input,
            conversation_history=history,
            client=c,
            provider=selected_provider,
            model=selected_model,
        )
        last_result = result

        # Add this turn to history for continuity
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": result["raw_text"]})

        # Display output
        if result["parsed"]:
            _display_parsed(result["parsed"])
        else:
            print("\n[Warning: response did not parse as JSON]")
            print(result["raw_text"])
            if result["parse_error"]:
                print(f"[Parse error: {result['parse_error']}]")


def _banner(agent: dict) -> None:
    print()
    print("=" * 60)
    print(f"  {agent['name']} v{agent['version']}")
    print(f"  Track: {agent['compliance_track']}")
    print("=" * 60)
    print("Commands: exit | quit | reset | history | save <filename>")
    print("Input:    paste narrative text OR a JSON object")
    print()


def _display_parsed(parsed: dict) -> None:
    """Pretty-print the structured determination for interactive use."""
    ds = parsed.get("determination_status", {})
    result = ds.get("result", "—")
    confidence = ds.get("confidence", "—")
    ev = parsed.get("evidence_assessment", {})
    ev_rating = ev.get("rating", "—")

    summary = parsed.get("compliance_determination_summary", {})
    narrative = summary.get("examiner_narrative", "")
    gaps = summary.get("data_gaps_followups", [])

    print()
    print(f"  Determination : {result}  (confidence: {confidence})")
    print(f"  Evidence      : {ev_rating}")

    if narrative:
        print()
        print("  Examiner Narrative:")
        for line in textwrap.wrap(narrative, width=72):
            print(f"    {line}")

    if gaps:
        print()
        print("  Data Gaps / Follow-ups:")
        for gap in gaps:
            print(f"    • {gap}")

    print()
    print("  [Full JSON below]")
    print(json.dumps(parsed, indent=2))


def _save_session(
    filename: str,
    agent_key: str,
    history: list[dict],
    last_result: dict | None,
) -> None:
    payload = {
        "agent_key": agent_key,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "turn_count": len(history) // 2,
        "history": history,
        "last_result": last_result,
    }
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"[Session saved to {filename}]")
    except OSError as e:
        print(f"[Save failed: {e}]")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _print_usage() -> None:
    print(
        textwrap.dedent("""
        Usage:
          python -m orchestrator.cli serve [--config agents.yaml] [--provider P] [--model M]
          python -m orchestrator.cli batch <loan_json_file> [options]
          python -m orchestrator.cli chat <agent_key> [--provider P] [--model M]

        Domain agents: hmda ecoa hvcre hpml fzd ybs vmi
        Special agents (auto-run, not selectable via --agents):
          auditor   (runs after all domain agents)
          narrative (runs only when --narrative-out is given)

        Examples:
          python -m orchestrator.cli serve --provider ollama --model gemma4:26b
          python -m orchestrator.cli batch loan.json --json-out results.json --narrative-out report.md
          python -m orchestrator.cli batch loan.json --spawn-local --provider ollama --agents hpml ybs
          python -m orchestrator.cli chat hmda
        """).strip()
    )


def _batch(args: argparse.Namespace) -> None:
    try:
        with open(args.loan_file, encoding="utf-8") as f:
            loan_data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error reading {args.loan_file}: {e}")
        sys.exit(1)
    config = load_agents(args.config)
    concurrency = args.concurrency or load_settings(args.config)["concurrency"]

    async def go() -> tuple[dict, dict | None]:
        results = await run_batch(loan_data, config, agents=args.agents, concurrency=concurrency)
        narrative = await run_narrative(results, config) if args.narrative_out else None
        return results, narrative

    print("Running batch evaluation over A2A...", file=sys.stderr)
    if args.spawn_local:
        with spawn_local(config, str(args.config), args.provider, args.model):
            results, narrative = asyncio.run(go())
    else:
        results, narrative = asyncio.run(go())

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"[JSON results written to {args.json_out}]", file=sys.stderr)
    else:
        print(json.dumps(results, indent=2))
    if narrative is not None:
        with open(args.narrative_out, "w", encoding="utf-8") as f:
            f.write(narrative["raw_text"])
        print(f"[Narrative report written to {args.narrative_out}]", file=sys.stderr)


def _serve(args: argparse.Namespace) -> None:
    config = load_agents(args.config)
    with spawn_local(config, str(args.config), args.provider, args.model):
        print("Local agents ready:", ", ".join(k for k, e in config.items() if is_local(e)), file=sys.stderr)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            print("Stopping local agents.", file=sys.stderr)


def main() -> None:
    if len(sys.argv) == 1:
        _print_usage()
        sys.exit(0)

    parser = argparse.ArgumentParser(description="Compliance agent orchestrator")
    subparsers = parser.add_subparsers(dest="mode", required=True)
    providers = ["anthropic", "ollama"]

    def common(sub, config=True):
        if config:
            sub.add_argument("--config", default=DEFAULT_CONFIG, help="agents.yaml path")
        sub.add_argument("--provider", choices=providers, default=None)
        sub.add_argument("--model")

    chat_parser = subparsers.add_parser("chat")
    chat_parser.add_argument("agent_key", choices=AGENT_KEYS)
    common(chat_parser, config=False)

    batch_parser = subparsers.add_parser("batch")
    batch_parser.add_argument("loan_file")
    batch_parser.add_argument("--agents", nargs="+", choices=DOMAIN_AGENT_KEYS)
    batch_parser.add_argument("--concurrency", type=int, help="agent calls at once (default: agents.yaml, else 1)")
    batch_parser.add_argument("--spawn-local", action="store_true",
                              help="start the local agents for this run (--provider/--model apply to them)")
    batch_parser.add_argument("--json-out", metavar="PATH", help="Write full results JSON to this file (in addition to stdout)")
    batch_parser.add_argument("--narrative-out", metavar="PATH", help="Run narrative agent and write Markdown report to this file")
    common(batch_parser)

    serve_parser = subparsers.add_parser("serve")
    common(serve_parser)

    one_parser = subparsers.add_parser("serve-one")  # internal: one agent in the foreground
    one_parser.add_argument("agent_key")
    common(one_parser)

    args = parser.parse_args()
    if args.mode == "chat":
        repl(args.agent_key, provider=args.provider or DEFAULT_PROVIDER, model=args.model)
    elif args.mode == "batch":
        _batch(args)
    elif args.mode == "serve":
        _serve(args)
    elif args.mode == "serve-one":
        serve_one(args.agent_key, load_agents(args.config)[args.agent_key], args.provider, args.model)


if __name__ == "__main__":
    main()

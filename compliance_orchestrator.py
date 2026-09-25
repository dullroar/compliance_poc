"""
compliance_orchestrator.py
--------------------------
Sequential compliance agent orchestrator for Farm Credit ACA loan review.

Modes:
  1. Batch (programmatic): send one loan payload to all 7 agents, collect raw JSON results.
  2. Chat (REPL): interactive conversation with a single named agent.

Usage:
  # Batch mode (from Python)
  from compliance_orchestrator import run_batch
  results = run_batch(loan_data)          # dict keyed by agent key
  results = run_batch(loan_data, agents=["hmda", "ecoa"])  # subset

  # Chat mode (CLI)
  python compliance_orchestrator.py chat hmda
  python compliance_orchestrator.py chat ecoa

  # Batch mode (CLI, loan data from JSON file)
  python compliance_orchestrator.py batch loan.json
  python compliance_orchestrator.py batch loan.json --agents hmda ecoa hpml

Environment:
  COMPLIANCE_PROVIDER optional, "anthropic" (default) or "ollama"
  COMPLIANCE_MODEL    optional, provider-specific model name
  OLLAMA_BASE_URL     optional, default http://localhost:11434
  OLLAMA_TIMEOUT      optional, request timeout in seconds, default 300
  ANTHROPIC_API_KEY   required only for the Anthropic provider
"""

import argparse
import json
import os
import sys
import textwrap
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False

from agent_prompts import AGENTS

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_PROVIDER = os.getenv("COMPLIANCE_PROVIDER", "anthropic").lower()
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-20250514",
    "ollama": "gemma4:26b",
}
MODEL = os.getenv(
    "COMPLIANCE_MODEL",
    DEFAULT_MODELS.get(DEFAULT_PROVIDER, DEFAULT_MODELS["anthropic"]),
)
MAX_TOKENS = 8192
AGENT_KEYS: list[str] = list(AGENTS.keys())
DOMAIN_AGENT_KEYS: list[str] = [k for k in AGENT_KEYS if k not in ("auditor", "narrative")]


class OllamaClient:
    """Minimal client for Ollama's native chat API."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (
            base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ).rstrip("/")
        self.timeout = float(os.getenv("OLLAMA_TIMEOUT", "300"))

    def create_message(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict],
        max_tokens: int,
        json_mode: bool = True,
    ) -> str:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                *messages,
            ],
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        if json_mode:
            payload["format"] = "json"
        request = Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = json.load(response)
        except HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama returned HTTP {e.code}: {detail}") from e
        except URLError as e:
            raise RuntimeError(
                f"Could not connect to Ollama at {self.base_url}. "
                "Make sure `ollama serve` is running."
            ) from e

        try:
            return body["message"]["content"].strip()
        except (KeyError, TypeError) as e:
            raise RuntimeError(f"Unexpected Ollama response: {body}") from e


def _client(provider: str | None = None) -> Any:
    provider = (provider or DEFAULT_PROVIDER).lower()
    if provider == "ollama":
        return OllamaClient()
    if provider != "anthropic":
        raise ValueError("Unknown provider. Valid providers: anthropic, ollama")
    if anthropic is None:
        raise RuntimeError(
            "The Anthropic provider requires the `anthropic` package. "
            "Install it with `pip install -r requirements.txt`."
        )

    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Add it to your .env file or environment."
        )
    return anthropic.Anthropic(api_key=key)


def _model_name(provider: str, model: str | None = None) -> str:
    if provider not in DEFAULT_MODELS:
        raise ValueError("Unknown provider. Valid providers: anthropic, ollama")
    if model:
        return model
    if os.getenv("COMPLIANCE_MODEL"):
        return os.environ["COMPLIANCE_MODEL"]
    return DEFAULT_MODELS[provider]


def _call_model(
    client: Any,
    provider: str,
    model: str,
    system: str,
    messages: list[dict],
    json_mode: bool = True,
) -> str:
    if provider == "ollama":
        return client.create_message(
            model=model,
            system=system,
            messages=messages,
            max_tokens=MAX_TOKENS,
            json_mode=json_mode,
        )

    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=messages,
    )
    return response.content[0].text.strip()


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

    agent = AGENTS[agent_key]
    selected_provider = (provider or DEFAULT_PROVIDER).lower()
    selected_model = _model_name(selected_provider, model)
    c = client or _client(selected_provider)

    # Build user message content
    if isinstance(loan_data, dict):
        prefix = agent.get(
            "user_message_prefix",
            "Evaluate the following loan data and return your compliance determination "
            "as a JSON object per your output contract.",
        )
        user_content = prefix + "\n\n" + json.dumps(loan_data, indent=2)
    else:
        user_content = str(loan_data)

    messages = list(conversation_history or [])
    messages.append({"role": "user", "content": user_content})

    json_mode = agent.get("output_format") != "markdown"
    raw_text = _call_model(
        c,
        selected_provider,
        selected_model,
        agent["system_prompt"],
        messages,
        json_mode=json_mode,
    )

    # Markdown-output agents return raw text — skip JSON parse entirely
    if agent.get("output_format") == "markdown":
        return {
            "agent_key": agent_key,
            "agent_name": agent["name"],
            "provider": selected_provider,
            "model": selected_model,
            "raw_text": raw_text,
            "parsed": None,
            "parse_error": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Attempt JSON parse — strip markdown fences if the model forgot
    cleaned = raw_text
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        # drop first and last fence lines
        cleaned = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        ).strip()

    parsed = None
    parse_error = None
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        parse_error = str(e)

    return {
        "agent_key": agent_key,
        "agent_name": agent["name"],
        "provider": selected_provider,
        "model": selected_model,
        "raw_text": raw_text,
        "parsed": parsed,
        "parse_error": parse_error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Batch mode: sequential fan-out across all (or selected) agents
# ---------------------------------------------------------------------------

def run_batch(
    loan_data: dict | str,
    agents: list[str] | None = None,
    verbose: bool = True,
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, dict]:
    """
    Run loan_data through each agent sequentially.

    Args:
        loan_data:  Dict or narrative string describing the loan.
        agents:     List of agent keys to run. Default: all seven.
        verbose:    Print progress to stderr.

    Returns:
        Dict keyed by agent_key → result dict from call_agent().
    """
    keys = agents or DOMAIN_AGENT_KEYS
    unknown = [k for k in keys if k not in AGENTS]
    if unknown:
        raise ValueError(f"Unknown agent keys: {unknown}. Valid: {AGENT_KEYS}")

    selected_provider = (provider or DEFAULT_PROVIDER).lower()
    selected_model = _model_name(selected_provider, model)
    c = _client(selected_provider)
    results: dict[str, dict] = {}

    for key in keys:
        if verbose:
            print(f"  [{key}] running...", file=sys.stderr, flush=True)
        result = call_agent(
            key,
            loan_data,
            client=c,
            provider=selected_provider,
            model=selected_model,
        )
        results[key] = result
        if verbose:
            status = "OK" if result["parsed"] else f"PARSE ERROR: {result['parse_error']}"
            print(f"  [{key}] {status}", file=sys.stderr, flush=True)

    # Run auditor over all collected domain results
    auditor_input = {
        "loan_data": loan_data if isinstance(loan_data, dict) else {},
        "agent_results": {
            k: v["parsed"] if v["parsed"] is not None else v["raw_text"]
            for k, v in results.items()
        },
    }
    if verbose:
        print("  [auditor] running...", file=sys.stderr, flush=True)
    auditor_result = call_agent(
        "auditor",
        auditor_input,
        client=c,
        provider=selected_provider,
        model=selected_model,
    )
    results["auditor"] = auditor_result
    if verbose:
        status = "OK" if auditor_result["parsed"] else f"PARSE ERROR: {auditor_result['parse_error']}"
        print(f"  [auditor] {status}", file=sys.stderr, flush=True)

    return results


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
          python compliance_orchestrator.py chat <agent_key> [--provider PROVIDER] [--model MODEL]
          python compliance_orchestrator.py batch <loan_json_file> [options]

        Agent keys (domain):
          hmda  ecoa  hvcre  hpml  fzd  ybs  vmi
        Special agents (auto-run, not selectable via --agents):
          auditor   (runs after all domain agents)
          narrative (runs only when --narrative-out is given)

        Examples:
          python compliance_orchestrator.py chat hmda
          python compliance_orchestrator.py batch loan.json
          python compliance_orchestrator.py batch loan.json --agents hmda ecoa
          python compliance_orchestrator.py batch loan.json --provider ollama --model gemma4:26b
          python compliance_orchestrator.py batch loan.json --json-out results.json --narrative-out report.md
        """).strip()
    )


def main() -> None:
    if len(sys.argv) == 1:
        _print_usage()
        sys.exit(0)

    parser = argparse.ArgumentParser(description="Compliance agent orchestrator")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    chat_parser = subparsers.add_parser("chat")
    chat_parser.add_argument("agent_key", choices=AGENT_KEYS)  # includes "auditor"
    chat_parser.add_argument(
        "--provider", choices=["anthropic", "ollama"], default=DEFAULT_PROVIDER
    )
    chat_parser.add_argument("--model")

    batch_parser = subparsers.add_parser("batch")
    batch_parser.add_argument("loan_file")
    batch_parser.add_argument("--agents", nargs="+", choices=DOMAIN_AGENT_KEYS)
    batch_parser.add_argument(
        "--provider", choices=["anthropic", "ollama"], default=DEFAULT_PROVIDER
    )
    batch_parser.add_argument("--model")
    batch_parser.add_argument(
        "--json-out", metavar="PATH",
        help="Write full results JSON to this file (in addition to stdout)",
    )
    batch_parser.add_argument(
        "--narrative-out", metavar="PATH",
        help="Run narrative agent and write Markdown report to this file",
    )

    args = parser.parse_args()

    if args.mode == "chat":
        repl(args.agent_key, provider=args.provider, model=args.model)

    elif args.mode == "batch":
        try:
            with open(args.loan_file, encoding="utf-8") as f:
                loan_data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"Error reading {args.loan_file}: {e}")
            sys.exit(1)

        selected_model = _model_name(args.provider, args.model)
        print(
            f"Running batch evaluation ({args.provider}/{selected_model})...",
            file=sys.stderr,
        )
        results = run_batch(
            loan_data,
            agents=args.agents,
            verbose=True,
            provider=args.provider,
            model=selected_model,
        )

        # Write JSON results to file if requested, otherwise emit to stdout
        if args.json_out:
            with open(args.json_out, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            print(f"[JSON results written to {args.json_out}]", file=sys.stderr)
        else:
            print(json.dumps(results, indent=2))

        # Optionally run narrative agent and write Markdown report
        if args.narrative_out:
            narrative_input = {
                k: v["parsed"] if v["parsed"] is not None else v["raw_text"]
                for k, v in results.items()
            }
            print("  [narrative] running...", file=sys.stderr, flush=True)
            narrative_result = call_agent(
                "narrative",
                narrative_input,
                provider=args.provider,
                model=selected_model,
            )
            status = "OK" if narrative_result["parse_error"] is None else f"WARNING: {narrative_result['parse_error']}"
            print(f"  [narrative] {status}", file=sys.stderr, flush=True)
            with open(args.narrative_out, "w", encoding="utf-8") as f:
                f.write(narrative_result["raw_text"])
            print(f"[Narrative report written to {args.narrative_out}]", file=sys.stderr)


if __name__ == "__main__":
    main()

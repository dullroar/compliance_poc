"""Model backends (Anthropic remote, Ollama local) behind one interface.

complete(system, messages, json_mode)            -> text
complete_with_tool(system, messages, spec, execute, calls_made) -> text
"""
from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import anthropic
except ImportError:  # pragma: no cover
    anthropic = None

from compliance_common.obs import get_logger
from compliance_common.tools import run_anthropic_tool_loop, run_ollama_tool_loop, seed_anthropic, seed_ollama

log = get_logger("backend", "1")
DEFAULT_MODELS = {"anthropic": "claude-sonnet-4-20250514", "ollama": "gemma4:26b"}
MAX_TOKENS = 8192


def default_provider() -> str:
    return os.getenv("COMPLIANCE_PROVIDER", "anthropic").lower()


def model_name(provider: str, model: str | None = None) -> str:
    if provider not in DEFAULT_MODELS:
        raise ValueError("Unknown provider. Valid providers: anthropic, ollama")
    return model or os.getenv("COMPLIANCE_MODEL") or DEFAULT_MODELS[provider]


def _ollama_options(max_tokens: int) -> dict[str, Any]:
    """num_predict, sampling, and num_ctx when OLLAMA_NUM_CTX is set (Ollama silently truncates input beyond its window).

    Sampling is low-temperature with a fixed seed so a narrative is faithful and replays reproducibly (an audit
    property); override with OLLAMA_TEMPERATURE / OLLAMA_SEED."""
    options: dict[str, Any] = {"num_predict": max_tokens, "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.2")),
                               "seed": int(os.getenv("OLLAMA_SEED", "42"))}
    if os.getenv("OLLAMA_NUM_CTX"):
        options["num_ctx"] = int(os.environ["OLLAMA_NUM_CTX"])
    if os.getenv("OLLAMA_NUM_THREAD"):        # CPU threads; a GPU-resident model needs few, and fewer leaves the machine usable
        options["num_thread"] = int(os.environ["OLLAMA_NUM_THREAD"])
    return options


class OllamaClient:
    """Minimal client for Ollama's native chat API."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.timeout = float(os.getenv("OLLAMA_TIMEOUT", "300"))

    _thinking_support: dict[str, bool] = {}

    def supports_thinking(self, model: str) -> bool:
        """Does this model advertise the 'thinking' capability? (asked once per model)"""
        if model not in self._thinking_support:
            try:
                request = Request(f"{self.base_url}/api/show", data=json.dumps({"model": model}).encode("utf-8"),
                                  headers={"Content-Type": "application/json"}, method="POST")
                with urlopen(request, timeout=30) as response:
                    self._thinking_support[model] = "thinking" in (json.load(response).get("capabilities") or [])
            except (HTTPError, URLError, OSError, ValueError):
                self._thinking_support[model] = False
        return self._thinking_support[model]

    def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Thinking is OFF by default for models that have it (a narrator does not need hidden reasoning, and it multiplies
        latency); set OLLAMA_THINK=true to turn it on, in which case it is logged at TRACE."""
        if "think" not in payload and self.supports_thinking(payload.get("model", "")):
            payload = {**payload, "think": os.getenv("OLLAMA_THINK", "false").lower() == "true"}
        started = time.monotonic()
        body = self._chat(payload)
        thinking = (body.get("message") or {}).get("thinking")
        if thinking:
            log.trace("model thinking", payload=thinking)
        num_ctx = (payload.get("options") or {}).get("num_ctx")
        prompt_tokens = body.get("prompt_eval_count")
        log.info("ollama %s: prompt %s tok, output %s tok, %.1fs", payload.get("model"), prompt_tokens, body.get("eval_count"),
                 time.monotonic() - started)
        if num_ctx and prompt_tokens and prompt_tokens >= num_ctx - 8:
            log.warning("prompt used %s of num_ctx %s tokens: Ollama probably truncated the input; raise OLLAMA_NUM_CTX", prompt_tokens, num_ctx)
        return body

    def _chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(f"{self.base_url}/api/chat", data=json.dumps(payload).encode("utf-8"),
                          headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.load(response)
        except HTTPError as e:
            raise RuntimeError(f"Ollama returned HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}") from e
        except URLError as e:
            raise RuntimeError(f"Could not connect to Ollama at {self.base_url}. Make sure `ollama serve` is running.") from e

    def create_message(self, *, model: str, system: str, messages: list[dict], max_tokens: int, json_mode: bool = True, schema: dict | None = None) -> str:
        payload = {"model": model, "messages": [{"role": "system", "content": system}, *messages],
                   "stream": False, "options": _ollama_options(max_tokens)}
        if schema:
            payload["format"] = schema
        elif json_mode:
            payload["format"] = "json"
        body = self.chat(payload)
        try:
            return body["message"]["content"].strip()
        except (KeyError, TypeError) as e:
            raise RuntimeError(f"Unexpected Ollama response: {body}") from e


class Backend:
    """A provider + model + client. `client` is injectable for tests."""

    def __init__(self, provider: str | None = None, model: str | None = None, client: Any | None = None) -> None:
        self.provider = (provider or default_provider()).lower()
        self.model = model_name(self.provider, model)
        self.client = client or self._make_client()

    def _make_client(self) -> Any:
        if self.provider == "ollama":
            return OllamaClient()
        if anthropic is None:
            raise RuntimeError("The Anthropic provider requires the `anthropic` package.")
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set. Add it to your .env file or environment.")
        return anthropic.Anthropic(api_key=key)

    def complete(self, system: str, messages: list[dict], json_mode: bool = True, schema: dict | None = None) -> str:
        if self.provider == "ollama":
            return self.client.create_message(model=self.model, system=system, messages=messages,
                                              max_tokens=MAX_TOKENS, json_mode=json_mode, schema=schema)
        response = self.client.messages.create(model=self.model, max_tokens=MAX_TOKENS, system=system, messages=messages)
        return response.content[0].text.strip()

    def complete_with_tool(self, system: str, messages: list[dict], spec: dict, execute, calls_made: list,
                           force_first: bool = True) -> str:
        """The model is given the tool and is expected to call it. On Anthropic the first call is forced; Ollama has no
        equivalent, so a model that does not call the tool is handled by the runner (see agents.runner)."""
        if self.provider == "ollama":
            payload = {"model": self.model, "messages": [{"role": "system", "content": system}, *messages],
                       "options": _ollama_options(MAX_TOKENS)}
            response = run_ollama_tool_loop(self.client.chat, spec, execute, payload, calls_made)
            return response["message"].get("content", "").strip()
        response = run_anthropic_tool_loop(self.client, spec, execute, model=self.model, system=system,
                                           messages=messages, max_tokens=MAX_TOKENS, calls_made=calls_made, force_first=force_first)
        return "".join(getattr(b, "text", "") for b in response.content).strip()

    def complete_seeded(self, system: str, messages: list[dict], spec: dict, execute, calls_made: list,
                        arguments: dict, result: dict, schema: dict | None = None) -> str:
        """The tool exchange is already in the conversation, in the provider's native format, as the agent's own first step.

        On Ollama the final answer is requested with `format` = `schema` (constrained decoding), so a small model cannot reply in
        prose, with the wrong keys, or with inline reasoning; there is nothing left for it to call, so no tools are offered."""
        if self.provider == "ollama":
            seeded = [*messages, *seed_ollama(spec, arguments, result)]
            payload = {"model": self.model, "messages": [{"role": "system", "content": system}, *seeded], "stream": False,
                       "options": _ollama_options(MAX_TOKENS)}
            if schema:
                payload["format"] = schema
            return self.client.chat(payload)["message"].get("content", "").strip()
        seeded = [*messages, *seed_anthropic(spec, arguments, result)]
        response = run_anthropic_tool_loop(self.client, spec, execute, model=self.model, system=system, messages=seeded,
                                           max_tokens=MAX_TOKENS, calls_made=calls_made)
        return "".join(getattr(b, "text", "") for b in response.content).strip()

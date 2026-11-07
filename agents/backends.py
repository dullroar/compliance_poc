"""Model backends (Anthropic remote, Ollama local, OpenAI remote) behind one interface.

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

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

from compliance_common.obs import get_logger
from compliance_common.narrative_schema import NARRATIVE_SCHEMA
from compliance_common.tools import (anthropic_request_options, native_definition, run_anthropic_tool_loop, run_ollama_tool_loop,
                                     run_openai_tool_loop, seed_anthropic, seed_ollama, seed_openai)

log = get_logger("backend", "1")
DEFAULT_MODELS = {"anthropic": "claude-haiku-5-5", "ollama": "gemma4:26b"}
SUPPORTED_PROVIDERS = frozenset({*DEFAULT_MODELS, "openai"})
MAX_TOKENS = 8192
# Claude's tokenizer yields about 1.7x the tokens of OpenAI's for the same text, and the narrative report needs
# ~9k of them, so the shared 8192 cap truncated it. The Messages API bills only the tokens produced.
ANTHROPIC_MAX_TOKENS = 16384


def default_provider() -> str:
    return os.getenv("COMPLIANCE_PROVIDER", "anthropic").lower()


def model_name(provider: str, model: str | None = None) -> str:
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError("Unknown provider. Valid providers: anthropic, ollama, openai")
    selected = model or os.getenv("COMPLIANCE_MODEL")
    if selected:
        return selected
    if provider == "openai":
        raise ValueError("OpenAI requires an explicit model. Pass --model or set COMPLIANCE_MODEL.")
    return DEFAULT_MODELS[provider]


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
        if self.provider == "openai":
            if OpenAI is None:
                raise RuntimeError("The OpenAI provider requires the `openai` package.")
            key = os.getenv("OPENAI_API_KEY")
            if not key:
                raise RuntimeError("OPENAI_API_KEY not set. Add it to your .env file or environment.")
            return OpenAI(api_key=key, timeout=float(os.getenv("OPENAI_TIMEOUT", "60")),
                          max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "2")))
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
        if self.provider == "openai":
            request: dict[str, Any] = {"model": self.model, "instructions": system, "input": messages,
                                       "max_output_tokens": MAX_TOKENS, "store": False}
            if schema:
                request["text"] = {"format": {"type": "json_schema", "name": "compliance_narrative",
                                                "strict": True, "schema": schema}}
            elif json_mode:
                request["text"] = {"format": {"type": "json_object"}}
            return _openai_output_text(self.client.responses.create(**request))
        response = self.client.messages.create(model=self.model, max_tokens=ANTHROPIC_MAX_TOKENS, system=system, messages=messages,
                                               **anthropic_request_options(self.model))
        return _anthropic_output_text(response)

    def complete_with_tool(self, system: str, messages: list[dict], spec: dict, execute, calls_made: list,
                           force_first: bool = True) -> str:
        """The model is given the tool and is expected to call it. Anthropic and OpenAI force the first call; Ollama
        has no equivalent, so a model that does not call the tool is handled by the runner (see agents.runner)."""
        if self.provider == "ollama":
            payload = {"model": self.model, "messages": [{"role": "system", "content": system}, *messages],
                       "options": _ollama_options(MAX_TOKENS)}
            response = run_ollama_tool_loop(self.client.chat, spec, execute, payload, calls_made)
            return response["message"].get("content", "").strip()
        if self.provider == "openai":
            response = run_openai_tool_loop(self.client, spec, execute, model=self.model, system=system,
                                            messages=messages, max_tokens=MAX_TOKENS, calls_made=calls_made,
                                            force_first=force_first, schema=NARRATIVE_SCHEMA)
            return _openai_output_text(response)
        response = run_anthropic_tool_loop(self.client, spec, execute, model=self.model, system=system,
                                           messages=messages, max_tokens=ANTHROPIC_MAX_TOKENS, calls_made=calls_made, force_first=force_first)
        return _anthropic_output_text(response)

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
        if self.provider == "openai":
            seeded = [*messages, *seed_openai(spec, arguments, result)]
            request: dict[str, Any] = {"model": self.model, "instructions": system, "input": seeded,
                                       "max_output_tokens": MAX_TOKENS, "store": False,
                                       "tools": [native_definition(spec, "openai")],
                                       "tool_choice": "none", "parallel_tool_calls": False}
            if schema:
                request["text"] = {"format": {"type": "json_schema", "name": "compliance_narrative",
                                                "strict": True, "schema": schema}}
            return _openai_output_text(self.client.responses.create(**request))
        seeded = [*messages, *seed_anthropic(spec, arguments, result)]
        response = run_anthropic_tool_loop(self.client, spec, execute, model=self.model, system=system, messages=seeded,
                                           max_tokens=ANTHROPIC_MAX_TOKENS, calls_made=calls_made)
        return _anthropic_output_text(response)


def _anthropic_output_text(response: Any) -> str:
    """Select text blocks explicitly: newer models can return thinking first."""
    stop_reason = getattr(response, "stop_reason", None)
    if stop_reason in {"refusal", "model_context_window_exceeded"}:
        raise RuntimeError(f"Anthropic stopped without a usable response: {stop_reason}")
    text = "".join(getattr(block, "text", "") for block in response.content
                   if getattr(block, "type", None) == "text").strip()
    if not text:
        raise RuntimeError("Anthropic returned no output text")
    return text


def _openai_output_text(response: Any) -> str:
    """Read the SDK helper while making empty/refusal-only Responses observable failures."""
    text = getattr(response, "output_text", "")
    if isinstance(text, str) and text.strip():
        return text.strip()
    raise RuntimeError("OpenAI returned no output text")

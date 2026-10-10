"""Start the local A2A agent servers (those whose agents.yaml url is on this machine)."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from contextlib import contextmanager
from urllib.parse import urlparse
from urllib.request import urlopen

from agents.a2a_server import build_app

from .config import is_local


def serve_one(key: str, entry: dict, provider: str | None = None, model: str | None = None) -> None:
    """Run one agent server in the foreground (blocking)."""
    import uvicorn
    url = urlparse(entry["url"])
    options = {k: entry[k] for k in ("tool_mode", "include_regulations", "max_regulation_chars") if k in entry}
    app = build_app(key, entry["url"], provider=entry.get("provider") or provider, model=entry.get("model") or model, options=options or None)
    uvicorn.run(app, host=url.hostname, port=url.port, log_level="warning")


def _wait_ready(url: str, timeout: float = 60.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urlopen(url.rstrip("/") + "/.well-known/agent-card.json", timeout=2).close()
            return
        except OSError:
            time.sleep(0.3)
    raise RuntimeError(f"agent at {url} did not become ready within {timeout:.0f}s")


@contextmanager
def spawn_local(config: dict[str, dict], config_path: str | None = None, provider: str | None = None,
                model: str | None = None):
    """Start each local agent as a subprocess; stop them on exit."""
    env = dict(os.environ)
    if provider:
        env["COMPLIANCE_PROVIDER"] = provider
    if model:
        env["COMPLIANCE_MODEL"] = model
    procs = []
    try:
        for key, entry in config.items():
            if not is_local(entry):
                continue
            cmd = [sys.executable, "-m", "orchestrator.cli", "serve-one", key]
            if config_path:
                cmd += ["--config", config_path]
            procs.append(subprocess.Popen(cmd, env=env))
        for key, entry in config.items():
            if is_local(entry):
                _wait_ready(entry["url"])
        yield
    finally:
        for proc in procs:
            proc.terminate()
        for proc in procs:
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

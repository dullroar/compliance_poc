"""Load agents.yaml."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import yaml

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "agents.yaml"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def load_settings(path: Path | str | None = None) -> dict:
    """Top-level settings from agents.yaml. `concurrency` is how many agent calls run at once
    (default 1: a single local model can serve one request at a time)."""
    with open(path or DEFAULT_CONFIG, encoding="utf-8") as source:
        raw = yaml.safe_load(source) or {}
    concurrency = int(raw.get("concurrency", 1))
    if concurrency < 1:
        raise ValueError("agents.yaml: concurrency must be >= 1")
    return {"concurrency": concurrency}


def load_agents(path: Path | str | None = None) -> dict[str, dict]:
    with open(path or DEFAULT_CONFIG, encoding="utf-8") as source:
        agents = (yaml.safe_load(source) or {}).get("agents")
    if not isinstance(agents, dict) or not agents:
        raise ValueError("agents.yaml must define a non-empty 'agents' mapping")
    for key, entry in agents.items():
        if not isinstance(entry, dict) or "url" not in entry:
            raise ValueError(f"agents.yaml: {key} needs a url")
    return agents


def is_local(entry: dict) -> bool:
    return urlparse(entry["url"]).hostname in LOCAL_HOSTS

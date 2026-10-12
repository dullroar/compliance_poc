"""Runtime agent registry, loaded from prompts/<key>.md.

The prompt files are the single source of truth. Line 1 of each file is a header:

    Agent: <key> | Name: <name> | Agent Version: <semver> | Track: <track> | Output: json|markdown [| Tool: <mcp tool>]

The header is part of the prompt text sent to the model, so the version appears in
any prompt/CoT dump. `@@AGENT_VERSION@@` in the body is replaced with the header
version. An optional `---USER-MESSAGE-PREFIX---` line splits off a user-message prefix.
"""
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_PREFIX_MARK = "\n---USER-MESSAGE-PREFIX---\n"
_HEADER_FIELDS = {
    "Agent": "key",
    "Name": "name",
    "Agent Version": "version",
    "Track": "compliance_track",
    "Output": "output_format",
}
_OPTIONAL_FIELDS = {"Tool": "tool"}


def _parse_header(line: str, path: Path) -> dict:
    meta = {}
    for part in line.split(" | "):
        label, _, value = part.partition(": ")
        if label in _HEADER_FIELDS:
            meta[_HEADER_FIELDS[label]] = value.strip()
        elif label in _OPTIONAL_FIELDS:
            meta[_OPTIONAL_FIELDS[label]] = value.strip()
    missing = set(_HEADER_FIELDS.values()) - set(meta)
    if missing:
        raise ValueError(f"{path.name}: header missing {sorted(missing)}")
    return meta


def load_agent(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    prompt, _, prefix = text.partition(_PREFIX_MARK)
    meta = _parse_header(prompt.split("\n", 1)[0], path)
    if meta["key"] != path.stem:
        raise ValueError(f"{path.name}: header key {meta['key']!r} != filename")
    meta["system_prompt"] = prompt.strip().replace("@@AGENT_VERSION@@", meta["version"])
    if prefix:
        meta["user_message_prefix"] = prefix
    if meta["output_format"] == "json":
        del meta["output_format"]
    return meta


AGENTS: dict[str, dict] = {
    a["key"]: a for a in (load_agent(p) for p in sorted(PROMPTS_DIR.glob("*.md")))
}

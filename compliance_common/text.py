"""Text normalization shared by source hashing (builders) and regulation injection (agents)."""
from __future__ import annotations

import html
import re


def normalize(raw: bytes | str, select_regex: str | None = None) -> str:
    """Tags stripped, entities decoded, whitespace collapsed; optionally narrowed to a fragment."""
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", text, flags=re.S | re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    text = re.sub(r"\s+", " ", text).strip()
    if select_regex:
        match = re.search(select_regex, text)
        if not match:
            raise ValueError(f"select_regex {select_regex!r} matched nothing; the page layout may have changed")
        text = match.group(0)
    return text

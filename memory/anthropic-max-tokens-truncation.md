---
gist: "Read when: Anthropic domain-agent calls produce JSON parse errors, or an agent's output schema gains fields."
---

# Anthropic output truncation

- 2026-06-10 — With `MAX_TOKENS = 4096`, Anthropic domain-agent calls truncated mid-response on the full structured JSON output, producing JSON parse errors rather than a clean failure. Raised to 8192 (commit 760902e). If parse errors reappear (e.g. after adding fields to an agent's output schema), check `MAX_TOKENS` in `agents/backends.py` before assuming a prompt or provider problem — the failure mode looks like a parsing bug, not a token-limit bug.

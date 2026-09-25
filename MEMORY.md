# MEMORY.md

Non-obvious findings about this codebase and its operating environment, discovered during work but not designed for anywhere else — not in README.md (what it is and how to use it), DESIGN.md (architectural decisions), or agent-instruction files (rules). This is background context for whichever LLM works in this repository next, so it does not have to rediscover these findings the hard way.

If you (an LLM) make a finding like the ones below — a gotcha, an environment quirk, or a non-obvious reason one component reads or uses another — add it here rather than only mentioning it in chat. Keep entries factual and dated; note when something might have been fixed since.

## Findings

- 2026-06-10 — With `MAX_TOKENS = 4096`, Anthropic domain-agent calls truncated mid-response on the full structured JSON output, producing JSON parse errors rather than a clean failure. Raised to 8192 (commit 760902e). If parse errors reappear (e.g. after adding fields to an agent's output schema), check `MAX_TOKENS` in `compliance_orchestrator.py` before assuming a prompt or provider problem — the failure mode looks like a parsing bug, not a token-limit bug.

- 2026-09-25 — The Ollama default is `gemma4:26b`. A live `--agents hmda` batch against `sample_loan.json` completed with parsed HMDA and automatic auditor results (no parse errors) using that default. On the local 31 GiB RAM / 8 GiB VRAM WSL machine with a 65,536-token Ollama context, the two sequential calls took 6m24s total; a full seven-agent batch should be treated as a long-running, adequately provisioned-machine test.

---
id: 02-build-and-test
status: pending
depends_on: [01-adopt-context]
touches:
  - Dockerfile
  - .dockerignore
  - README.md
  - scripts/test_docker.sh
  - scripts/AGENTS.md
  - .github/workflows/context.yml
  - plans/ralphify/steps/02-build-and-test.md
lane: none
requirements: [R2]
gate: bash scripts/test_docker.sh && python3 scripts/check_context.py && git diff --check
evidence: ""
---

# 02-build-and-test

Depends on `01-adopt-context`. Add a project Dockerfile, an appropriate `.dockerignore`, and `scripts/test_docker.sh`. Use project dependencies and current lockfiles. Run project tests as a normal container user where supported. Use synthetic fixtures, a temporary output directory, and no developer credentials. Put any new operational or test artifacts under the repo's existing conventions. Document build, test, and any device or platform requirements in `README.md`. Keep existing host usage working. Arrange for CI to call the same entry point wherever the runner supports that gate.

The Docker test script builds the image from the current step worktree and runs the repo-specific gates inside it. For context checks, use a complete source snapshot or an appropriate read-only checkout that works with linked Git worktrees. A linked worktree's `.git` pointer alone does not provide its Git metadata in the container. Keep the image usable without a sibling checkout, host venv, or mutable shared volume. Use repo- and run-specific names for any image tags, container names, and writable paths. Build dependencies can use package registries. The default test runtime uses local fixtures and an isolated container network. The FUSE mount gate is required for the two FUSE lanes, with the host requirements in their repo briefs.

Touches `Dockerfile`, `.dockerignore`, `README.md`, `scripts/test_docker.sh`, generated indexes, any necessary workflow updates, focused test/support paths from the repo brief, and this step file. Gate: `bash scripts/test_docker.sh && python3 scripts/check_context.py && git diff --check`.

## Repository gate

Use the existing Python dependencies and `requirements-mcp.lock`. Preserve evaluator contracts, MCP transport checks, provider accounting, and protected suites. Run `python3 -m unittest discover -s tests -v` in Docker with live provider and local-model flags off. Check that the offline MCP stdio tests run. Preserve live opt-in instructions and repository spending rules. No credentials, provider API calls, or Ollama service are needed for the migration gate. Limit repo-specific edits to test environment and packaging support needed to reproduce the offline checks.

## Resume notes

- 2026-11-22 UTC. Docker built the image from the linked worktree. The
  container passed all four context checks. The image pins Anthropic
  `0.109.1`, the version recorded in the prior suite evidence. The latest
  Anthropic SDK rejected the suite's `httpx` test transport.
- The full suite discovered 656 tests. It reported 647 passes, eight
  expected live-test skips and one failure. The MCP stdio parity tests for
  all eight domains and the auditor passed. The bounded MCP lifecycle test
  also passed. The host context and whitespace checks passed separately.
- The gate is blocked by
  `ParityProfileTests.test_the_command_line_picks_parity_only_above_the_smoke_maximum`.
  The test runs the OpenAI estimator with the current date. The estimator
  rejects the recorded pricing date, 2026-11-08, as stale. The same estimator
  command reports the same error on the host.
- Resolve the date-dependent OpenAI CLI test in a separately authorized
  change, then rerun this step's gate. Preserve the live pricing check and
  the spending ledger.

---
id: 03-verify-integration
status: pending
depends_on: [02-build-and-test]
touches:
  - plans/ralphify/steps/03-verify-integration.md
lane: none
requirements: [R3]
gate: python3 scripts/check_context.py && bash scripts/test_docker.sh && git diff --check
evidence: ""
---

# 03-verify-integration

Depends on `02-build-and-test`. Update only the step file. Rerun the context and Docker gate from the integrated worktree as the driver would. Check the template and runner links in `AGENTS.md` and the structural-change rule. Verify README commands and the existing entry points. Record the worktree base commit, exact commands, build result, test counts or concrete smoke assertions, expected opt-in skips, real FUSE result where required, and UTC date. Keep logs outside Git. Gate: `python3 scripts/check_context.py && bash scripts/test_docker.sh && git diff --check`.

The driver writes its own `evidence` field. Put detailed test evidence in the body of the verification step and commit it. The parent verifies the final child commit and result. A green build alone cannot satisfy R2 or R3.

## Repository gate

Use the existing Python dependencies and `requirements-mcp.lock`. Preserve evaluator contracts, MCP transport checks, provider accounting, and protected suites. Run `python3 -m unittest discover -s tests -v` in Docker with live provider and local-model flags off. Check that the offline MCP stdio tests run. Preserve live opt-in instructions and repository spending rules. No credentials, provider API calls, or Ollama service are needed for the migration gate. Limit repo-specific edits to test environment and packaging support needed to reproduce the offline checks.

Run `git merge-base HEAD plan/ralphify` to identify the integrated base commit. Replace each pending value in the results below. For each passing check, put details after `PASS`. Include the actual Docker commands or image reference and test counts or concrete smoke results. Record `n/a` in the FUSE field for other repos. If a required test fails or skips, record that in resume notes and leave the result pending.

## Results

- Base commit: PASS. `git merge-base HEAD plan/ralphify` returned
  `945fc6b795a81ed0fa81c686000eaccb31f43bd8`.
- Commands: PASS. The gate exited with code 0.

  ```bash
  python3 scripts/check_context.py && bash scripts/test_docker.sh && git diff --check
  ```

  The host and container each passed the index, plan, link, and secret
  checks. The Docker script ran `python3 -m unittest discover -s tests -v`
  as a normal user in a read-only container with `--network none`.
- Docker build: PASS. The gate built `compliance-poc-test:puIepOMqdV`
  from the linked worktree. The standalone build also passed.

  ```bash
  docker build -t compliance-poc:verify-03-YRy29DG8 .
  ```

- Tests: PASS. The suite ran 657 tests in 312.109 seconds. It reported
  649 passes, eight skips, and zero failures or errors. The MCP stdio
  parity checks passed for all eight domains and the auditor. The YBS
  wire parity and bounded MCP lifecycle checks passed. The OpenAI pricing
  CLI parity test that previously failed also passed.
- Skips: PASS. All eight were expected opt-in checks. The disabled flags
  were `RUN_LIVE_ANTHROPIC_PARALLEL`, `RUN_LIVE_ANTHROPIC_PARITY`,
  `RUN_LIVE_APOR_TESTS`, `RUN_LIVE_EVERY_REGIME`,
  `RUN_LIVE_OPENAI_PARALLEL`, `RUN_LIVE_OPENAI_PARITY`,
  `RUN_LIVE_OPENAI_TESTS`, and `RUN_LIVE_OLLAMA_TESTS`.
- FUSE: n/a
- UTC date: 2026-11-22

## README and agent contract checks

- Both GitHub links in `AGENTS.md` returned HTTP 200. The structural
  change rule requires agents to read both projects and to account for
  the layout, plan format, generated indexes, worktree rules, and
  validation commands.
- The README build and test commands ran from the linked worktree. The
  standalone image used a temporary tag. The CLI printed help for
  `python -m orchestrator.cli` and for `serve`, `batch`, and `chat`
  in a container with its network disabled.
- The README's Ralph commands match the local runner's `--help` and the
  pinned template guide. The runner's plan summary reported two steps
  done and one pending. An invocation of `--status` from the step
  worktree failed because the runner uses the checkout name to locate
  its runtime directory. The README directs users to the base checkout.
  The active driver owns the migration run.

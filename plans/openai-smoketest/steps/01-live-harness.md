---
id: 01-live-harness
status: pending
depends_on: []
touches:
  - tests/test_openai_live_smoke.py
  - tests/test_openai_backend.py
  - tests/test_openai_smoke_accounting.py
lane: serial
gate: python3 -m unittest discover -s tests -p test_openai_live_smoke.py -v && python3 -m unittest discover -s tests -p test_openai_backend.py -v && python3 -m unittest discover -s tests -p test_openai_smoke_accounting.py -v
requirements: [R1, R2, R3, R4]
evidence: ""
---

# Build a bounded, opt-in live test harness

## Change

- `tests/test_openai_live_smoke.py`: implement a normal-discovery-skipped test using the real OpenAI backend and synthetic YBS case, local A2A ASGI transport, and real MCP tool path. Exercise seeded and model tool modes against `gpt-6-luna`. Assert direct decision ID and classification parity, canonical case pinning, real model-originated tool call in model mode, valid parsed grounded narration, and no guard fallback. Observe and report guard retries and errors.
- Count all Responses requests, including model/guard retries, and fail before request seven per cycle. Disable SDK retries, apply a finite timeout, and cleanly close clients and spawned processes. Ensure no live call occurs absent opt-in; verify the gate actually contacts OpenAI when enabled.
- Implement the R3 append-only request ledger and cumulative budget reservations, with per-request, per-mode and per-cycle usage and estimated cost. Persist reservation before submission; retain its bound on timeout, interruption or missing usage until reconciled. Capture both tool-mode exchanges and all retries, not merely final responses. Record pricing basis and never double count cached or reasoning tokens. Do not include raw requests or responses.
- `tests/test_openai_backend.py` and `tests/test_openai_smoke_accounting.py`: add offline tests for opt-in, accounting and the per-cycle and cumulative budget caps, including restarts, missing usage, retries, and failed requests; do not weaken existing coverage.

## Do not change

Domain rules, model defaults, protected assertions, real records or secrets. Do not call OpenAI in this step.

## Dependencies already satisfied

None.

## Completion criteria

Offline gate passes, with the live test skipped explicitly; the caps, ledger arithmetic, failure recovery, and no-opt-in behavior are verified offline. The live gate in step 02 exercises actual requests rather than a fake.

## Record

Record date, commands and results in `evidence:`; set `status: done` only after the gate and criteria pass.

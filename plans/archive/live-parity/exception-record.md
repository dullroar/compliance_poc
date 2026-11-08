---
gist: "Read when: recording an owner-approved, time-bounded violation under this plan."
---

# Tolerated violation record

## 1. Narrative report cut off at the output cap on claude-haiku-5-5

- Rule and source: R2 in [spec.md](spec.md) (every role completes in both phases with a usable model narrative), as strengthened by the executor's `not_truncated` check in `tests/test_anthropic_live_parity.py`: a reply that stops at `max_tokens` is not a finished narrative.
- Kind: tolerated violation (rule preserved, violation accepted). The check is not retired; it still applies to every role except `narrative`, and the `narrative` truncation is still detected, recorded and reported.
- Rationale: `prompts/narrative.md` asks for a multi-audience report (summary, findings, evidence, coaching notes, and four audience narratives). Haiku 5.5 writes the whole structure, over 16384 output tokens (about 37k characters measured), so the last audience section, the Examiner Narrative, ends mid-sentence. Reviewed by the owner on 2026-11-07: the text is coherent and grounded in the decision records (figures match, no ungrounded facts seen), with one miscount in the executive summary. OpenAI condenses the same prompt to about 5k tokens, so this is a difference in output length and not a runtime defect. A planned change replaces the free-form report with bounded per-audience templates (loan officer, examiner), which removes the cause.
- Decision owner: Jim Lehmer.
- Affected parties: operators and reviewers reading Anthropic narrative reports; the `narrative` role only. Domain roles, the auditor and every deterministic decision are unaffected.
- Status: CLOSED 2026-11-07 (outcome 4 ended because its cause was removed; the `not_truncated` check itself stays and now applies to every role). Closure evidence: [plans/archive/response-templates/results.md](../response-templates/results.md). The report is now assembled by code and the model writes one summary of at most 150 words; `TOLERATED_TRUNCATION` and its pinned test were removed; one live Anthropic run (run 04cf37c16a8a43649ad96ebc96efd55d) passed with the `narrative` role at 316 and 411 output tokens against the 16384 cap and no truncation. OpenAI was not run live.
- Was still observed (until closure): yes. Each Anthropic live run records the `narrative` role as tolerated truncation (`tolerated` in `runs-anthropic.jsonl`) and `results.md` lists it. Any other role stopping at `max_tokens` still fails the gate.
- Review by: when the audience-template plan lands, and no later than 2026-12-07. At that point remove the tolerance (`TOLERATED_TRUNCATION`) and rerun the gate.
- Decided: 2026-11-07

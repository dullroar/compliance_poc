---
gist: "Read when: planning or auditing the loan-officer and examiner response templates, their word limits, or the retirement of the free-form narrative report."
---

# Response templates - specification and execution agreement

Status: approved (by Jim Lehmer, 2026-11-07). Confirmed by Jim 2026-11-07: the five-part examiner order and the proposed word limits as the starting values (step 03 still calibrates and asks again), and that examiner paragraphs are written inside each domain agent's existing call (R5). Step 03 calibration, confirmed by Jim 2026-11-07: the word limits stay as proposed except VMI, raised from 80 to 100; and when one HMDA result has more than 20 findings, the HMDA LAR item findings are grouped by LAR section (one paragraph per section that has failing items; the section partition is the executor's inferred draft in the catalog and still needs Jim's or compliance's review). Other rules marked inferred still need confirmation.

See [goal.md](goal.md) for the goal command and [inventory.md](inventory.md) for what can fail in each regime and why.

## Goal and exclusions

Give every failing check two fixed, bounded explanations, both derived from the code-owned decision record:

1. A **loan-officer sheet**: what information the customer's file still needs, and one or two short sentences on why. Simplified Technical English.
2. An **examiner finding**: one paragraph per finding, in the regime's own vocabulary, in a standard order, under a word limit set per regime.

This also replaces the free-form multi-audience narrative report, so the cause of the tolerated `narrative` truncation (see [archived exception](../archive/live-parity/exception-record.md), review by 2026-12-07) is removed.

This work does NOT: change any rule, threshold, rule pack, `decision_id`, classification or compliance result; change a prompt's regulatory content; add a regime; reduce or switch models (plan `tune-ais`); change orchestration order or concurrency (plan `parallelize`); make a legal conclusion that discrimination or a violation occurred; or use real customer data. Live model runs happen only in step 06 and only within the approval stated under Delegated authority.

## Requirements

### R1. A catalog covers every rule and every missing fact the code can emit

- Basis: inferred. Rule ids are partly built at run time ([inventory](inventory.md)), so coverage must be proven by test, not by reading.
- Example: `HMDA-LAR-10`, `VMI-REQUEST-RACE`, `YBS-ENTITY-SMALL-TRUST` and `TRID-CD-REVISED-3DAY` each resolve to one entry. A made-up id resolves to the generic entry and is reported as uncovered.
- Acceptance check: `tests/test_response_catalog.py` enumerates the ids from the evaluators (pack-driven for LAR items and exclusions, scenario-driven for the rest, using `tests/fixtures/*/scenarios.json`) and fails if any id, or any `missing_facts` field seen in those fixtures, falls through to the generic entry.

### R2. Templates live outside the rule pack and never change a decision

- Basis: documented ([`base_record` hashes pack files into `decision_id`](../../compliance_common/decision.py); [code decides, agents narrate](../../docs/design/code-decides-agents-narrate.md)).
- Example: editing a template sentence leaves every `decision_id` and `rule_pack.file_sha256` unchanged.
- Acceptance check: a test that renders every fixture, edits the catalog in memory, and asserts equal `decision_id`; plus the existing evaluator suites unchanged.

### R3. The loan-officer sheet is short, plain and safe

- Basis: documented for style (LLMRC-lite "Plain Technical Language", ASD-STE100 in spirit); inferred for limits.
- Rules (inferred): at most 2 sentences per item; each sentence at most 20 words; one idea per sentence; active voice; the same word for the same thing; a customer-facing label, never an internal field path. Pattern: "To be classified as Young, we need the date of birth. We use it to check the age against the Farm Credit limit."
- Content rule (inferred): only information the customer can give goes on the customer list. Findings of kind P (process or record fact) and R (reviewer judgment) go on a separate "Refer to compliance, not a customer request" list with one sentence. Where the applicant may decline (VMI, HMDA item 10), the item says "ask; the applicant may decline; record the decline".
- Example: `YBS-PERSON-YOUNG-DOB` gives the pattern above. `ECOA-MARITAL-INQUIRY` unable_to_determine goes to the referral list and never says "obtain marital status".
- Acceptance check: `tests/test_loan_officer_sheet.py` asserts the sentence and word limits on every rendered item, no internal path tokens (`lar_context.`, `.`-joined field paths) in text, correct list routing for each kind, and that every field named in `missing_facts` appears exactly once across the two lists.

### R4. The examiner finding has a fixed order and a per-regime word limit

- Basis: inferred. Order follows the audit convention of criteria, condition, cause, effect, action, mapped to the record. Limits are set from the number of facts a finding must carry and from the density of the regime ([inventory](inventory.md)).
- Order: (1) **Requirement**: the rule and its citation. (2) **Condition**: what the record shows, with the record's own figures. (3) **Basis**: why this outcome (threshold test failed, fact absent, evidence conflicts, judgment needed). (4) **Effect**: classification and compliance result as the record states them. (5) **Action**: what evidence or correction closes it.
- Word limit per paragraph (inferred, to be confirmed or recalibrated in step 03 against rendered fixtures): YBS 70, VMI 100 (raised from 80 in step 03), HPML 90, FZD 90, HVCRE 90, ECOA 100, TRID 100, auditor 110, HMDA 130. HMDA is highest because one finding often combines a coverage condition, an Appendix B or C value test and a citation; YBS is lowest because it compares at most three figures to three policy limits. A paragraph also has a floor of 25 words so it cannot be a bare label.
- Example: a late Loan Estimate gives one paragraph of at most 100 words that cites 1026.19(e)(1)(iii), states the delivery date and the deadline from the record, says the result is Non-Compliant, and names the delivery record that would close it.
- Acceptance check: `tests/test_examiner_finding.py` asserts the five elements are present (rule id and citation, a figure or named missing fact from the record, outcome word, result word, an action clause), the floor and the regime limit, and one paragraph per finding with none omitted or merged.

### R5. Code can always write both templates; a model may only phrase the examiner paragraph

- Basis: documented ([deterministic fallback in `compliance_common/narrative.py`](../../compliance_common/narrative.py), `check_narrative`); inferred: where the model writes.
- Rule (inferred, recommended): each domain agent's existing narrative call also returns one paragraph per finding, keyed by rule id, in the schema constrained form. The call already runs in parallel with the other domains and already holds the record. `check_narrative` grounding (numbers, dates, ids), the contradiction check, the required elements and the word limit apply to each paragraph. One retry, then code renders that paragraph from the catalog. The loan-officer sheet is always rendered by code. `agents.yaml` gets `templates: model | code` (default `model`) so `tune-ais` can measure the no-model arm.
- Example: with `templates: code`, no extra model output is requested, and every paragraph still passes R4.
- Acceptance check: offline tests with fake clients cover accepted, over-limit, ungrounded and malformed replies per regime; the fallback paragraph passes R4; `templates: code` makes zero extra model requests.

### R6. The narrative role stops producing a free-form multi-audience report

- Basis: documented ([archived exception 1](../archive/live-parity/exception-record.md): the planned change replaces the report with bounded per-audience templates, and the tolerance is then removed).
- Rule (inferred): the report is assembled by code from domain results and the auditor result: a loan-officer section (R3), an examiner section (R4) and the auditor's cross-regime findings. The model writes at most one short summary of at most 150 words. The narrative role fits within the output cap with no truncation on both providers.
- Example: the narrative role's output tokens drop from about 16384 (cap reached) to a small fraction of that.
- Acceptance check: offline tests of report assembly; in step 06, remove `TOLERATED_TRUNCATION` and its pinned test, update the exception record to closed, and (with the approval below) rerun the Anthropic live gate with the narrative role passing `not_truncated` without tolerance.

### R7. Existing behavior and validation are undisturbed

- Basis: documented ([agent contract](../../AGENTS.md)).
- Acceptance check: `python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py`, all `RUN_LIVE_*` variables unset.

## Constraints and assumptions

- Word limits, sentence limits and the five-part order are inferred. Jim, or the compliance reviewer he names, confirms them. Examiner wording is a draft until compliance reviews it, the same as the packs (`draft_engineering_review`).
- Regulatory "why" text must come from the pinned eCFR snapshots and `builders/sources.yaml` references, not from memory. Where a regime's pinned text does not give a reason (YBS thresholds are institution policy), the template says "institution policy" and not "regulation".
- Catalog wording follows ASD-STE100 in spirit. Exact names (rule ids, form names, Appendix B, ULI, APOR, HVCRE) stay unchanged and are explained once where a loan officer may not know them.
- Fairness constraint (inferred): no loan-officer text may suggest asking a prohibited question or require information the regulation says the creditor may not require (see [inventory](inventory.md) point 3).

## Domain challenge

- *Suspicious - explain it:* the same missing fact can be a customer request in one regime and a record of an institution action in another (marital status: VMI requests it, ECOA records whether it was asked). Resolution (inferred): route by the rule id and kind, not by the field name. Confirm with: Jim or compliance.
- *Suspicious - explain it:* HMDA may produce dozens of findings for one loan (38 LAR items). One paragraph each could be long. Resolution: keep one paragraph per finding as asked; measured in step 03: an HMDA result with an empty register gives 29-36 findings. Jim decided on 2026-11-07 to group the LAR item findings by LAR section only when one result has more than 20 findings; never group silently below that, and never drop a finding (each rule id appears in exactly one paragraph).
- *Suspicious - explain it:* a paragraph that is correct but over the word limit. Resolution: it is rejected and rewritten by code from the catalog, never cut mid-sentence.
- *Suspicious - explain it:* YBS `Not Eligible` is `Not Applicable` and not a defect. Resolution: it is not a finding, so it produces no examiner paragraph and no customer request.
- *Contradicts a confirmed rule:* letting a model choose which findings exist, or alter an outcome. Resolution: findings come from the record; the model only phrases.

## Delegated authority

- The executor MAY: add `compliance_common/templates/` code and the catalog files outside every `pack/`; extend `NARRATIVE_SCHEMA`, `check_narrative`, `assemble` and the runner for per-finding paragraphs; change `prompts/narrative.md` and `builders/narrative_contract.md` for the new report shape (bumping the prompt version in its header) and rebuild prompts with `python -m builders.build prompts`; add `agents.yaml` option `templates`; add offline tests; update README operator notes; remove `TOLERATED_TRUNCATION` and close the exception in step 06.
- The executor MAY run ONE live Anthropic registry run (the existing gate, `claude-haiku-5-5`, synthetic data only) in step 06 to prove R6, after the spending preflight and a durable reservation under [AGENTS.md](../../AGENTS.md), within the existing USD 20 Anthropic budget and a bound of USD 0.50 for this plan. No OpenAI live run.
- The executor MUST NOT: change rules, packs, thresholds, evaluator versions or `decision_id` content; weaken or delete a protected check except as R6 states; use real data; change provider defaults; push, publish or commit.

## Acceptance and evidence

- Protected checks: the offline suites named in R1-R7, all existing evaluator, parity, agent-runner and live-accounting suites, and context and plan validation.
- Combined validation: `python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py`, plus the one live gate in step 06.
- Evidence: per step in its `evidence:` field. Step 03 also records rendered word counts per regime (min, median, p95, max) on the fixtures, and the final limits with Jim's confirmation.

## Escalate when

Word limits cannot be met without dropping a required element; a regime's pinned text gives no basis for a "why" a loan officer needs; a finding kind cannot be routed safely; a field can be both a customer request and a prohibited inquiry; the live run would exceed its bound; a protected check cannot pass. Bring the specific decision.

## Exceptions and retirements

This plan retires one tolerated violation: [archived exception 1](../archive/live-parity/exception-record.md), narrative truncation. That is outcome 4 ending because its cause is removed, not a retired test. The `not_truncated` check itself stays. Record the closure in step 06.

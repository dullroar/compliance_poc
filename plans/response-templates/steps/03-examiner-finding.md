---
id: 03-examiner-finding
status: done
depends_on: [01-catalog]
touches:
  - compliance_common/templates/examiner.py
  - tests/test_examiner_finding.py
lane: examiner
gate: python3 -m unittest tests.test_examiner_finding -v
requirements: [R4]
evidence: "2026-11-07: python3 -m unittest tests.test_examiner_finding -v -> 20 tests OK (about 32 s); with tests.test_loan_officer_sheet and tests.test_response_catalog 53 tests OK; full offline suite 481 tests OK before the grouping addition (5 skipped as before), check_context and check_plan ok, RUN_LIVE_* unset. examiner.py renders one paragraph per finding (Requirement, Condition, Basis, Effect, Action) from the record and catalog only; a paragraph over its limit is never cut: a compact form drops the requirement sentence and LimitError is raised if that still does not fit. Calibration on the fixture sweep (words per full-form paragraph; min, median, p95, max; limit): ybs n=233 49/58/64/64 (70); hpml n=4 61/64.5/67/68 (90); trid n=18 70/71/77/77 (100); hmda n=821 53/72/106/106 (130); ecoa n=25 54/80/82/84 (100); vmi n=101 63/71/79/90 (100); fzd n=73 63/74/81/82 (90); hvcre n=12 54/76.5/79/80 (90); auditor n=169 50/71/76/76 (110). Findings per loan (sweep, one fault at a time): median 0-2, max 11 (hmda), 6 (ybs), 3 (vmi, fzd, auditor). The sweep renders 96 distinct rule ids; rules the fixtures never fail are covered by the catalog tests, not by word counts. JIM'S ANSWER, 2026-11-07: (1) confirmed the proposed limits with VMI raised from 80 to 100 (ybs 70, vmi 100, hpml 90, fzd 90, hvcre 90, ecoa 100, trid 100, auditor 110, hmda 130); the starting values were otherwise unchanged. (2) For an HMDA result with more than 20 findings (an empty register gives 29-36), group the LAR item findings by LAR section. Implemented: GROUP_THRESHOLD=20; above it, items of one section with two or more failures become one grouped paragraph, with the failing item ids, the outcome words and the named missing facts; other findings keep their own paragraph; every finding id appears in exactly one paragraph. Empty register: 36 findings -> 6 paragraphs, 489 words (was about 2,900); 29 findings -> 6 paragraphs, 474 words. At 20 findings nothing is grouped (tested at 20 and 21). The five-section partition of the 38 items (identity, terms, property, applicant, pricing) is my inferred draft kept in examiner.py LAR_SECTIONS (the regulation lists the items flat, and step 03 may not change the catalog schema); compliance should review it. Step 04 must give a grouped paragraph a key such as HMDA-LAR-SECTION-TERMS (rule_ids lists its members) when a model phrases it. Wording was shortened in the catalog (YBS, FZD, ECOA, VMI, HVCRE, HMDA LAR template) to meet the starting limits without dropping a required element. Recorded decisions also written into spec.md. Mutation checks: an invented figure in the basis sentence fails the figures test (239 failures); a duplicated Condition label fails the order test."
---

# Render one examiner paragraph per finding and calibrate the word limits

Write for an agent with no chat history.

## Change

- `examiner.py`: `render(decision, domain) -> [paragraph per finding]` in the five-part order of R4, from the record and catalog only, with the per-regime ceiling and the 25-word floor as constants in one table.
- `tests/test_examiner_finding.py` (write first): five elements present, floor and ceiling, one paragraph per finding, figures quoted only from the record.
- Calibration: render every fixture and `sample_loan.json`; record min, median, p95 and max words per regime and the number of findings per loan in this step's evidence. Propose final limits. **Stop and ask Jim to confirm the limits before step 04.**

## Do not change

The catalog schema, evaluators, the loan-officer renderer.

## Dependencies already satisfied

- 01-catalog: resolver and entries.

## Completion criteria

Every fixture's paragraphs pass R4 at the proposed limits with margin. The evidence lists the numbers and the proposed table. Jim has confirmed or changed the limits (record his answer).

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.

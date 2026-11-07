---
id: 03-examiner-finding
status: pending
depends_on: [01-catalog]
touches:
  - compliance_common/templates/examiner.py
  - tests/test_examiner_finding.py
lane: examiner
gate: python3 -m unittest tests.test_examiner_finding -v
requirements: [R4]
evidence: ""
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

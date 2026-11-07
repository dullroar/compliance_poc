---
id: 02-loan-officer-sheet
status: pending
depends_on: [01-catalog]
touches:
  - compliance_common/templates/loan_officer.py
  - tests/test_loan_officer_sheet.py
lane: loan-officer
gate: python3 -m unittest tests.test_loan_officer_sheet -v
requirements: [R3]
evidence: ""
---

# Render the loan-officer sheet from a decision record

Write for an agent with no chat history.

## Change

- `loan_officer.py`: `render(decision) -> {needed_from_customer: [...], refer_to_compliance: [...]}` using only the record and the catalog. Group items by subject where the record has subjects (YBS). Apply the sentence and word limits of R3; the "applicant may decline; record the decline" wording for VMI and HMDA item 10; routing by kind.
- `tests/test_loan_officer_sheet.py` (write first): limits, no internal paths, routing for kinds P and R (marital-status inquiry never appears as a customer request), each `missing_facts` field exactly once, plain-language checks on a golden sample for every regime.

## Do not change

The catalog schema (step 01) beyond adding entries it lacks, evaluators, the examiner renderer.

## Dependencies already satisfied

- 01-catalog: resolver and entries.

## Completion criteria

Every fixture renders a sheet that passes the checks. A golden example reproduces the pattern in R3 for `YBS-PERSON-YOUNG-DOB`.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.

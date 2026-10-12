# APOR data for the HPML pack

**Where it comes from:** the FFIEC publishes the Average Prime Offer Rate (APOR) tables, which the CFPB
points to in 12 CFR 1026.35(a)(2).

- Tables page (download the weekly Fixed-rate and Adjustable-rate tables here):
  https://www.ffiec.gov/ratespread/aportables.htm
- APOR calculator (single lookup by product, rate-set date and term):
  https://www.ffiec.gov/ratespread/newcalc.aspx

**Why it is not fetched automatically:** FFIEC returns a CAPTCHA page (HTTP 403) to scripts
(verified 2026-10-09 for both URLs above and for the direct `.txt` table links). The builders
therefore treat this source as `manual` (`builders/sources.yaml`, id `ffiec-apor-tables`).

**What the evaluator does today:** it does not read APOR files. Each `hpml_case` supplies `apor`
plus `apor_reference` (`table_date`, `product`, `source`), and the evaluator refuses to decide
without them. Use the rate for the table in effect on the date the interest rate was set
(`rate_set_date`), for the matching product and term.

## What was downloaded (2026-10-09, by a person, in a browser)

Location: `compliance_mcp/hpml/sources/apor/` (note: no `pack/`; the manifest `local_path` can point anywhere in the repo).

| File | What it is |
|---|---|
| `YieldTableFixed.CSV` | Fixed-rate APOR by week (rows) and loan term in years 1-50 (columns). |
| `YieldTableAdjustable.CSV` | Adjustable-rate APOR by week and years to first adjustment 1-50. |
| `E8-16500.pdf` | Federal Register 73 FR 44522 (Jul 30 2008), Board of Governors, Regulation Z final rule (Docket R-1305), 93 pages. The origin of the HPML / APOR concept. |
| `Federal Register, Volume 73 Issue 207 (Friday, October 24, 2008).html` | Federal Register 73 FR 63329-63338 (Oct 24 2008), FR Doc E8-25320, Regulation Z rule text. |

Checked by script: both CSVs have 939 weekly rows (every Monday, no gaps), 50 numeric columns, no blanks.
**Coverage is 2000-01-03 through 2017-12-25 only.** These are FFIEC's legacy tables and stop there. They do
not cover any rate-set date after 2017-12-25, so they cannot serve current loans. The HPML pack window starts
2014-01-10, so only 2014-2017 rate-set dates are covered by this data.

Retrieval note: FFIEC's own link text uses `http://`; browsers warn on it. Use `https://www.ffiec.gov/ratespread/YieldTableFixed.CSV`
and `https://www.ffiec.gov/ratespread/YieldTableAdjustable.CSV`. From the build machine these still return the
FFIEC CAPTCHA page (HTTP 403, re-verified 2026-10-09), so a person has to download them.

## Is the FFIEC page current? No. What replaces it (verified 2026-10-09)

The page the CSVs come from (`https://www.ffiec.gov/ratespread/aportables.htm`, saved copy shows
"Last Modified 01/30/2013") carries only the four links above and describes the 2009 amendments. The rules
were not superseded: 12 CFR 1026.35(a)(1)-(2) and 12 CFR 1003.4(a)(12)(ii) still require the average prime
offer rate, and both say **"The Bureau publishes tables of average prime offer rates ... at least weekly"**
(text pinned in `pack/sources/12-cfr-1026-35.xml`). The tables did not stop; the legacy CSVs just stop at
2017-12-25.

The current official source is the CFPB-hosted FFIEC HMDA Platform:
- Rate Spread Calculator tool: https://ffiec.cfpb.gov/tools/rate-spread
- Rate Spread API documentation: https://ffiec.cfpb.gov/documentation/api/rate-spread/
- Single lookup: `POST https://ffiec.cfpb.gov/public/rateSpread` with JSON
  `{"actionTakenType":1,"loanTerm":30,"amortizationType":"FixedRate|VariableRate","apr":6.0,"lockInDate":"YYYY-MM-DD","reverseMortgage":2}`
  returns `{"rateSpread":"-1.420"}` (APR minus APOR, 3 decimals) or "NA". Responses may be gzip-compressed.
  `loanTerm` is 1-50 (for adjustable loans: years to first adjustment). No key is required and no CAPTCHA
  is shown to scripts (unlike www.ffiec.gov, which returns HTTP 403).

APOR can be backed out: `APOR = apr - rateSpread` (use an APR with at most 2 decimals so rounding is exact).

Observed behavior:
- Works for lock-in dates from 2017-01-02 through the current week (e.g. 30-year fixed, 2026-10-05: APOR 7.37).
  Returns HTTP 400 for 2016 dates and for future dates (2027-01-01). Same value for every day of a week.
- Overlap check against the legacy CSVs (2017, every Monday, fixed 7/15/30 and adjustable 3/5; 260 values):
  253 identical, **7 differ by 0.01-0.03** (e.g. 08/21/2017 fixed 30: CSV 3.92, API 3.89). Cause not
  determined (corrected tables, or a different week-to-date mapping). A 0.03 difference can flip an HPML result near
  the threshold, so the choice of authoritative source for overlapping dates needs a decision.

So the two sources together cover 2000 to the current week.

## Sample data warning
`sample_loan.json` uses APOR 7.02 for a 2024-04-10 30-year fixed, labeled "FFIEC APOR Table". The API gives
**6.86** for that date. The sample number is invented and should be replaced before the sample is used to demonstrate HPML.

## How APOR enters a case today (decision: per-case lookup recorded as evidence)

`python -m intake.apor loan.json [--write] [--force]` (`intake/apor.py`) fills `hpml_case.apor` and
`apor_reference` from the CFPB rate-spread API. It needs `rate_set_date`, `amortization_type` (fixed|adjustable)
and `apor_term_years` (loan term for fixed, years to first adjustment for adjustable) in the case.

- **No loan data is sent.** The request carries only a fixed probe APR (10.00), the rate-set date, the term and the
  amortization type; APOR = 10.00 - rateSpread.
- **Evidence recorded** in `apor_reference`: endpoint, retrieved_at, `response_sha256` (hash of the raw response),
  product, and `table_date` (the Monday of that week, *derived by us*: the API returns no table date).
- The evaluator stays offline and never calls the API; it only sees these fields.
- Not pinned: nothing stops the Bureau from revising a table, so re-running later can return a different value.
  The recorded hash lets a reviewer detect that. Pre-2017-01-02 dates are rejected (use the legacy CSVs by hand).
- Tests: `tests/test_apor_intake.py` (fake API); `RUN_LIVE_APOR_TESTS=1` also checks the live API against the legacy CSV.

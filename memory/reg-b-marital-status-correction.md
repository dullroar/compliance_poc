---
gist: "Read when: an agent flags missing marital status or other demographic data under HMDA or ECOA."
---

# Reg B marital status: HMDA versus ECOA

- 2026-10-09 — CORRECTION to an earlier note: the un-ported HMDA/ECOA agents (gemma) said missing marital status was a "failure to collect mandatory demographic data". I first judged that wrong; it is substantially RIGHT. 12 CFR 1002.13(a)(1) (Reg B) requires the creditor to *request* ethnicity, race, sex, marital status (married/unmarried/separated) and age for an application primarily to purchase or refinance a 1-4 unit dwelling that is the applicant's principal residence and secures the loan; the applicant may decline, and the declination must be noted on the form (1002.13(b)). What gemma got wrong was attributing it to HMDA, whose data (12 CFR 1003.4(a)(10)) has no marital status field. Lesson: verify against the pinned regulation text before calling a model wrong. Also: `hmda_fields.rate_spread` should be derived from the same APOR as HPML, not supplied (the sample's 2.37 vs the true 1.26 was caught by the auditor).

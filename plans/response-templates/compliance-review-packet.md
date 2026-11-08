---
gist: "Read when: a compliance reviewer is signing off the draft wording of the loan-officer sheet, the examiner paragraphs, the HMDA section grouping or the inferred rules of the response-templates plan."
---

# Response templates: compliance review packet

Generated from the catalog on 2026-11-08 (`compliance_common/templates/catalog/*.yaml` and `examiner.py`); if the catalog changes, regenerate it. Every sentence below is a draft written by the engineering team (status `draft_engineering_review`, the same as the rule packs). Nothing here changes a rule, a threshold or a decision.

## How to read this packet

Every finding a check can produce has two explanations, both written from fixed catalog text:

- **Loan-officer sheet**: what the customer file still needs and why, in two short sentences. A finding goes on the customer list only when the customer can supply the information. Process facts and reviewer judgments go on a separate "Refer to compliance" list.
- **Examiner paragraph**: one paragraph per finding in a fixed order (Requirement, Condition, Basis, Effect, Action) under a per-regime word limit.

For each entry please mark **OK**, **Change** (write the wording you want) or **Remove**. Wording that says "regulation" must trace to the cited section; wording that says "institution policy" is the institution's own rule.

Kinds: G = information the customer file lacks; V = a value that failed a test; R = reviewer judgment; P = process or record fact.

## Decisions that are still inferred (please confirm each)

| # | Decision | Current draft | Your answer |
|---|---|---|---|
| 1 | Loan-officer sentence limits | At most 2 sentences per item, at most 20 words per sentence, active voice, no internal field names | |
| 2 | Customer list versus referral | Only kinds G and V go on the customer list; kinds P and R are always referrals, never a customer request | |
| 3 | Marital status | The ECOA marital-status finding is only ever a referral and never says to obtain marital status from the customer; the VMI marital-status request is a customer request | |
| 4 | "May decline" wording | VMI items and HMDA item 10 (ethnicity, race, sex) say "Ask; the applicant may decline; record the decline." HMDA age and income say nothing about declining because no pinned source was found for a decline right | |
| 5 | Examiner paragraph order | Requirement, Condition, Basis, Effect, Action (confirmed as a starting point on 2026-11-07) | |
| 6 | Examiner word limits | YBS 70, HPML 90, FZD 90, HVCRE 90, VMI 100, ECOA 100, TRID 100, auditor 110, HMDA 130; floor 25 words (confirmed as starting values on 2026-11-07) | |
| 7 | Over-long HMDA results | When one HMDA result has more than 20 findings, loan-register item findings are grouped by section (table below); under 20 nothing is grouped; no finding is ever dropped | |
| 8 | YBS thresholds | Worded "institution policy", not "regulation", because 12 CFR 614.4165 requires the program but gives no thresholds | |


## HMDA section grouping (draft)

The regulation lists the 38 loan-register items flat. This five-way split is the engineering team's own guess; please confirm or redraw it.

| Section | Register items | Requirement sentence | Action sentence | Who acts |
|---|---|---|---|---|
| Loan identity and action | 1, 8, 33, 34 | The register must identify the loan and the action taken on it. | Record the identifier, the action and its date, the application channel and the NMLS identifier. | loan operations |
| Loan type, purpose and features | 2, 3, 4, 5, 6, 7, 11, 13, 14, 25, 26, 27, 36, 37, 38 | The register must describe the loan type, purpose, amount, lien, term and features. | Record each listed item from the loan file, or correct the value that was reported. | loan operations |
| Property | 9, 28, 29, 30, 31, 32 | The register must describe the property, its location, value and units. | Record each listed property item from the file, or correct the value that was reported. | loan officer |
| Applicant and credit decision | 10, 15, 16, 23, 24, 35 | The register must report the applicant data, credit score, ratios, underwriting result and denial reasons. | Record each listed item from the file, or correct the value that was reported. | credit analyst |
| Pricing and costs | 12, 17, 18, 19, 20, 21, 22 | The register must report the rate spread, costs, points, credits, rate and penalty. | Record each listed pricing item from the loan file, or correct the value that was reported. | closing staff |

## Young, Beginning and Small farmer (YBS)

Examiner word limit: 70.

### Findings (examiner wording and referral sentence)

| Rule id | Kind | Basis | Citation | Requirement (examiner) | Action | Who acts | Referral sentence | Review |
|---|---|---|---|---|---|---|---|---|
| YBS-PERSON-*-PRODUCER | G | institution policy | Institution YBS policy (12 CFR 614.4165) | Only an agricultural producer can be {1}. | Record producer status, with the application as evidence. | loan officer | The producer status of a person is not recorded. | |
| YBS-PERSON-YOUNG-DOB | G | institution policy | Institution YBS policy (12 CFR 614.4165) | Young means under the policy age limit, so the date of birth is required. | Record the date of birth from the signed application or an ID. | loan officer | The date of birth of a person is not recorded. | |
| YBS-PERSON-YOUNG-AGE | V | institution policy | Institution YBS policy (12 CFR 614.4165) | Young means under the policy age limit. | Confirm the date of birth; Young stays Not Eligible unless it changes. | loan officer | The recorded age does not meet the Young limit. | |
| YBS-PERSON-BEGINNING-EXPERIENCE | G | institution policy | Institution YBS policy (12 CFR 614.4165) | Beginning means farming years within the policy limit. | Record the years farmed, with the application as evidence. | loan officer | The years of farming experience are not recorded. | |
| YBS-PERSON-SMALL-SALES | G | institution policy | Institution YBS policy (12 CFR 614.4165) | Small means annual gross farm sales within the policy limit. | Record annual gross farm sales, with tax records as evidence. | loan officer | The annual gross agricultural sales are not recorded. | |
| YBS-ENTITY-*-CONFLICT | R | institution policy | Institution YBS policy (12 CFR 614.4165) | An entity is {1} only from documented, consistent ownership and control. | A reviewer resolves the conflict and records who the entity is attributed to. | compliance reviewer | The evidence about who owns or controls this entity conflicts. | |
| YBS-ENTITY-*-TRUST | R | institution policy | Institution YBS policy (12 CFR 614.4165) | A trust is {1} only when its trustee and controlling person are documented. | Obtain the trust document; record the trustee and controlling person. | compliance reviewer | The trustee or the controlling person of this trust is not documented. | |
| YBS-ENTITY-*-SUCCESSION | R | institution policy | Institution YBS policy (12 CFR 614.4165) | A successor entity is {1} only from documented attribution. | Obtain the succession documents; record the attributed people. | compliance reviewer | This successor or reorganized entity has no documented attribution. | |
| YBS-ENTITY-*-ATTRIBUTION | R | institution policy | Institution YBS policy (12 CFR 614.4165) | An entity is {1} only from the people who own, control or run it. | Document the entity's owners, controllers and operators. | compliance reviewer | The people who own, control or operate this entity are not documented. | |

### What the loan officer asks the customer for

| Missing fact | Label shown | Sentence shown | Review |
|---|---|---|---|
| is_agricultural_producer | producer status | To classify the person as Young, Beginning or Small, we need to know if they farm or ranch. We only test people who produce agricultural goods. | |
| date_of_birth | date of birth | To be classified as Young, we need the date of birth. We use it to check the age against the Farm Credit limit. | |
| years_farming | years of farming | To be classified as Beginning, we need the number of years farming. We use it to check the experience against the Farm Credit limit. | |
| annual_gross_ag_sales | annual gross farm sales | To be classified as Small, we need the yearly gross farm sales. We use them to check the sales against the Farm Credit limit. | |

### Facts routed to compliance, not the customer

| Missing fact | Label shown | Sentence shown | Review |
|---|---|---|---|
| attribution | who owns or controls the entity | The people who own, control or operate this entity are not documented or the evidence conflicts. | |
| attribution.subject_id | a person linked to the entity | The entity names a person who is not in the case file. | |

## Higher-priced mortgage loans (HPML, Reg Z 1026.35)

Examiner word limit: 90.

### Findings (examiner wording and referral sentence)

| Rule id | Kind | Basis | Citation | Requirement (examiner) | Action | Who acts | Referral sentence | Review |
|---|---|---|---|---|---|---|---|---|
| HPML-SCOPE | G | regulation | 12 CFR 1026.35(a) | Section 1026.35 covers closed-end consumer credit secured by the consumer's principal dwelling. | Record the credit type, the purpose and whether the principal dwelling secures the loan. | loan operations | The facts that show whether this loan is in scope are missing. | |
| HPML-SPREAD | G | regulation | 12 CFR 1026.35(a)(1) | A first-lien loan is higher-priced when the APR exceeds the APOR by the regulatory margin; the APOR and its source are needed. | Record the APOR with its table date, product and source, and the conforming loan limit when the amount is above the pinned baseline. | loan operations | The APOR or the conforming loan limit is missing. | |
| HPML-ESCROW | V | regulation | 12 CFR 1026.35(b)(1) | Escrow for property taxes and required insurance must be established before consummation on a first-lien higher-priced loan. | Record the escrow set-up date, or the exemption that applies under 1026.35(b)(2). | closing staff | Escrow for taxes and insurance is not shown as set up before closing. | |
| HPML-APPRAISAL | V | regulation | 12 CFR 1026.35(c) | A higher-priced loan needs an appraisal that meets 1026.35(c), unless an exemption in 1026.35(c)(2) applies. | Record the appraisal and the review that shows the 1026.35(c) requirements were met, or the exemption relied on. | closing staff | The appraisal requirements for a higher-priced loan are not shown as met. | |

### Facts routed to compliance, not the customer

| Missing fact | Label shown | Sentence shown | Review |
|---|---|---|---|
| apor | the APOR | The institution must look up the average prime offer rate and record its source. | |
| applicable_conforming_limit | the conforming loan limit | The institution must record the Freddie Mac loan limit for this loan amount. | |
| rate_set_date | the rate-set date | The institution must record a rate-set date that falls in a pinned threshold period. | |
| escrow_established_before_consummation | escrow set-up | Closing staff must record whether escrow was set up before closing. | |
| appraisal_requirements_met | appraisal review | Closing staff must record whether the appraisal rules for higher-priced loans were met. | |

## TILA-RESPA integrated disclosure (TRID)

Examiner word limit: 100.

### Findings (examiner wording and referral sentence)

| Rule id | Kind | Basis | Citation | Requirement (examiner) | Action | Who acts | Referral sentence | Review |
|---|---|---|---|---|---|---|---|---|
| TRID-SCOPE | G | regulation | 12 CFR 1026.19(e)(1)(i) | The integrated disclosure rules cover closed-end credit secured by real property or a cooperative unit. | Record the credit type, the collateral and the application date. | closing staff | The facts that show whether TRID applies are missing. | |
| TRID-LE-3DAY | V | regulation | 12 CFR 1026.19(e)(1)(iii)(A) | The creditor must deliver or place in the mail the Loan Estimate within 3 business days after receiving the application. | Record the Loan Estimate delivery date and method, or the evidence that shows it was timely. | closing staff | The Loan Estimate is not shown as delivered within 3 business days of the application. | |
| TRID-LE-7DAY | V | regulation | 12 CFR 1026.19(e)(1)(iii)(B) | The Loan Estimate must be delivered or mailed no later than 7 business days before consummation. | Record the Loan Estimate delivery date and method, or the documented emergency that waived the wait. | closing staff | The Loan Estimate is not shown as delivered 7 business days before closing. | |
| TRID-CD-3DAY | V | regulation | 12 CFR 1026.19(f)(1)(ii) | The consumer must receive the Closing Disclosure no later than 3 business days before consummation. | Record the Closing Disclosure delivery date and method, or move the closing date to restore the wait. | closing staff | The Closing Disclosure is not shown as received 3 business days before closing. | |
| TRID-CD-REVISED-3DAY | V | regulation | 12 CFR 1026.19(f)(2)(ii) | A change to the APR, the loan product or a prepayment penalty needs a corrected Closing Disclosure and a new 3-business-day wait. | Record the revised Closing Disclosure and its delivery date, or move the closing date to restore the wait. | closing staff | A change after the Closing Disclosure needs a new Closing Disclosure and a new 3-day wait. | |
| TRID-CD-CORRECTED | V | regulation | 12 CFR 1026.19(f)(2)(i) | A corrected Closing Disclosure for other changes must be received by consummation. | Record the corrected Closing Disclosure and its delivery date. | closing staff | The corrected Closing Disclosure is not shown as received by closing. | |
| TRID-TOLERANCE | V | regulation | 12 CFR 1026.19(e)(3); refund under (f)(2)(v) | Charges may not exceed the disclosed amount for zero-tolerance charges, or 10 percent in total for the 10-percent group, unless cured. | Record the charge amounts, and the refund made within 60 days of consummation if a tolerance was exceeded. | closing staff | Charges are above the tolerance limit, or the charge amounts are not recorded. | |

### Facts routed to compliance, not the customer

| Missing fact | Label shown | Sentence shown | Review |
|---|---|---|---|
| charges | charge amounts | Closing staff must record the disclosed and actual amount of each charge. | |
| loan_estimate | Loan Estimate delivery record | Closing staff must record when and how the Loan Estimate was delivered. | |
| closing_disclosure | Closing Disclosure delivery record | Closing staff must record when and how the Closing Disclosure was delivered. | |
| revised_closing_disclosure | revised Closing Disclosure record | Closing staff must record the revised Closing Disclosure that a change requires. | |
| application_received_date | application date | The application date falls before the TRID window in the rule pack. | |
| timeshare | timeshare timing | Timeshare timing is not tested here; a reviewer must apply it. | |

## Home Mortgage Disclosure Act (HMDA, Regulation C)

Examiner word limit: 130.

### Findings (examiner wording and referral sentence)

| Rule id | Kind | Basis | Citation | Requirement (examiner) | Action | Who acts | Referral sentence | Review |
|---|---|---|---|---|---|---|---|---|
| HMDA-INSTITUTION | G | regulation | 12 CFR 1003.2(g) | Regulation C applies only to a financial institution as defined in 1003.2(g). | Record whether the institution meets the financial institution definition. | loan operations | Whether the institution is a financial institution is not recorded. | |
| HMDA-DWELLING | G | regulation | 12 CFR 1003.2(d), (o) | A covered loan is a closed-end mortgage loan or open-end line of credit secured by a lien on a dwelling. | Record whether a lien on a dwelling secures the loan. | loan operations | Whether a dwelling secures the loan is not recorded. | |
| HMDA-COVERAGE | G | regulation | 12 CFR 1003.3(c) | A transaction is covered unless an exclusion in 1003.3(c) applies, so each exclusion must be tested and the purpose settled. | Record each exclusion flag, the farm or business purpose, and the prior-year origination counts. | loan officer | Coverage cannot be settled because an exclusion fact is missing or the purpose is not decided. | |
| HMDA-EXCL-VOLUME | G | regulation | 12 CFR 1003.3(c)(11), (12) | A loan is excluded when the institution made fewer than the minimum number of originations in one of the two preceding calendar years. | Record the origination counts for the two preceding calendar years. | loan operations | The origination counts for the two preceding years are missing. | |
| HMDA-EXCL-AMOUNT | G | regulation | 12 CFR 1003.3(c)(7) | A transaction with a total dollar amount under the pinned minimum is an excluded transaction. | Record the total dollar amount of the transaction. | loan operations | The total dollar amount of the transaction is missing. | |
| HMDA-EXCL-AGRICULTURAL | G | regulation | 12 CFR 1003.3(c)(9) | A loan used primarily for agricultural purposes is excluded from Regulation C. | Record whether the loan is used primarily for agricultural purposes. | loan officer | Whether the loan is used mainly for farm purposes is not decided. | |
| HMDA-EXCL-BUSINESS | G | regulation | 12 CFR 1003.3(c)(10) | A loan primarily for business or commercial purposes is excluded, unless it is a home purchase, home improvement or refinancing. | Record the business or commercial purpose and the loan purpose. | loan officer | Whether the loan is mainly for business purposes is not decided. | |
| HMDA-EXCL-* | G | regulation | 12 CFR 1003.3(c) | A transaction of the type "{1}" is an excluded transaction under 1003.3(c). | Record whether this excluded-transaction type applies. | loan operations | Whether this excluded-transaction type applies is not recorded. | |
| HMDA-ACTION | V | regulation | 12 CFR 1003.4(a)(8) | The action taken and its date must be recorded, and the action date may not come before the application date. | Correct the action date or the application date, and record both from the loan file. | loan operations | The action date comes before the application date, or the application date is missing. | |
| HMDA-RATE-SPREAD | V | regulation | 12 CFR 1003.4(a)(12) | The reported rate spread must equal the APR minus the APOR for a loan that is subject to Regulation Z. | Record the APR and the APOR, and report the rate spread they give. | loan operations | The reported rate spread differs from the APR minus the APOR, or an input is missing. | |
| HMDA-PARTIAL-EXEMPTION | R | regulation | 12 CFR 1003.3(d) | An institution may omit optional data only with a valid partial exemption, based on its type, its volume and its CRA rating. | Record the institution type, the origination volume and the CRA rating that support the exemption, or report the optional data. | compliance reviewer | The claimed partial exemption is not valid or cannot be checked. | |
| HMDA-LAR-ITEMS | G | regulation | 12 CFR 1003.4(a) | The register must report all 38 items of 1003.4(a) that apply; this roll-up counts the items that fail. | Resolve the failing items listed with this roll-up. | loan operations | Some register items fail; see each item. | |
| HMDA-LAR-01 | G | regulation | 12 CFR 1003.4(a)(1) | The register must report universal loan identifier and application date for a covered loan, with an allowed value. | Record universal loan identifier and application date from the file, or correct the value that was reported. | loan operations | The register value for universal loan identifier and application date is missing or not valid. | |
| HMDA-LAR-02 | G | regulation | 12 CFR 1003.4(a)(2) | The register must report government insurance or guarantee program for a covered loan, with an allowed value. | Record government insurance or guarantee program from the file, or correct the value that was reported. | loan operations | The register value for government insurance or guarantee program is missing or not valid. | |
| HMDA-LAR-03 | G | regulation | 12 CFR 1003.4(a)(3) | The register must report loan purpose for a covered loan, with an allowed value. | Record loan purpose from the file, or correct the value that was reported. | loan officer | The register value for loan purpose is missing or not valid. | |
| HMDA-LAR-04 | G | regulation | 12 CFR 1003.4(a)(4) | The register must report preapproval request for a covered loan, with an allowed value. | Record preapproval request from the file, or correct the value that was reported. | loan officer | The register value for preapproval request is missing or not valid. | |
| HMDA-LAR-05 | G | regulation | 12 CFR 1003.4(a)(5) | The register must report construction method for a covered loan, with an allowed value. | Record construction method from the file, or correct the value that was reported. | loan officer | The register value for construction method is missing or not valid. | |
| HMDA-LAR-06 | G | regulation | 12 CFR 1003.4(a)(6) | The register must report occupancy type for a covered loan, with an allowed value. | Record occupancy type from the file, or correct the value that was reported. | loan officer | The register value for occupancy type is missing or not valid. | |
| HMDA-LAR-07 | G | regulation | 12 CFR 1003.4(a)(7) | The register must report loan amount for a covered loan, with an allowed value. | Record loan amount from the file, or correct the value that was reported. | loan operations | The register value for loan amount is missing or not valid. | |
| HMDA-LAR-08 | G | regulation | 12 CFR 1003.4(a)(8) | The register must report action taken and date for a covered loan, with an allowed value. | Record action taken and date from the file, or correct the value that was reported. | loan operations | The register value for action taken and date is missing or not valid. | |
| HMDA-LAR-09 | G | regulation | 12 CFR 1003.4(a)(9) | The register must report property location for a covered loan, with an allowed value. | Record property location from the file, or correct the value that was reported. | loan officer | The register value for property location is missing or not valid. | |
| HMDA-LAR-10 | G | regulation | 12 CFR 1003.4(a)(10) | The register must report applicant ethnicity, race, sex, age and income for a covered loan, with an allowed value. | Record applicant ethnicity, race, sex, age and income from the file, or correct the value that was reported. | loan officer | The register value for applicant ethnicity, race, sex, age and income is missing or not valid. | |
| HMDA-LAR-11 | G | regulation | 12 CFR 1003.4(a)(11) | The register must report type of purchaser for a covered loan, with an allowed value. | Record type of purchaser from the file, or correct the value that was reported. | loan operations | The register value for type of purchaser is missing or not valid. | |
| HMDA-LAR-12 | G | regulation | 12 CFR 1003.4(a)(12) | The register must report rate spread for a covered loan, with an allowed value. | Record rate spread from the file, or correct the value that was reported. | loan operations | The register value for rate spread is missing or not valid. | |
| HMDA-LAR-13 | G | regulation | 12 CFR 1003.4(a)(13) | The register must report hOEPA status for a covered loan, with an allowed value. | Record hOEPA status from the file, or correct the value that was reported. | loan operations | The register value for hOEPA status is missing or not valid. | |
| HMDA-LAR-14 | G | regulation | 12 CFR 1003.4(a)(14) | The register must report lien status for a covered loan, with an allowed value. | Record lien status from the file, or correct the value that was reported. | loan operations | The register value for lien status is missing or not valid. | |
| HMDA-LAR-15 | G | regulation | 12 CFR 1003.4(a)(15) | The register must report credit score and scoring model for a covered loan, with an allowed value. | Record credit score and scoring model from the file, or correct the value that was reported. | credit analyst | The register value for credit score and scoring model is missing or not valid. | |
| HMDA-LAR-16 | G | regulation | 12 CFR 1003.4(a)(16) | The register must report denial reasons for a covered loan, with an allowed value. | Record denial reasons from the file, or correct the value that was reported. | credit operations | The register value for denial reasons is missing or not valid. | |
| HMDA-LAR-17 | G | regulation | 12 CFR 1003.4(a)(17) | The register must report total loan costs or total points and fees for a covered loan, with an allowed value. | Record total loan costs or total points and fees from the file, or correct the value that was reported. | closing staff | The register value for total loan costs or total points and fees is missing or not valid. | |
| HMDA-LAR-18 | G | regulation | 12 CFR 1003.4(a)(18) | The register must report total of borrower-paid itemized amounts at or before closing for a covered loan, with an allowed value. | Record total of borrower-paid itemized amounts at or before closing from the file, or correct the value that was reported. | closing staff | The register value for total of borrower-paid itemized amounts at or before closing is missing or not valid. | |
| HMDA-LAR-19 | G | regulation | 12 CFR 1003.4(a)(19) | The register must report discount points for a covered loan, with an allowed value. | Record discount points from the file, or correct the value that was reported. | closing staff | The register value for discount points is missing or not valid. | |
| HMDA-LAR-20 | G | regulation | 12 CFR 1003.4(a)(20) | The register must report lender credits for a covered loan, with an allowed value. | Record lender credits from the file, or correct the value that was reported. | closing staff | The register value for lender credits is missing or not valid. | |
| HMDA-LAR-21 | G | regulation | 12 CFR 1003.4(a)(21) | The register must report interest rate for a covered loan, with an allowed value. | Record interest rate from the file, or correct the value that was reported. | closing staff | The register value for interest rate is missing or not valid. | |
| HMDA-LAR-22 | G | regulation | 12 CFR 1003.4(a)(22) | The register must report prepayment penalty term for a covered loan, with an allowed value. | Record prepayment penalty term from the file, or correct the value that was reported. | closing staff | The register value for prepayment penalty term is missing or not valid. | |
| HMDA-LAR-23 | G | regulation | 12 CFR 1003.4(a)(23) | The register must report debt-to-income ratio for a covered loan, with an allowed value. | Record debt-to-income ratio from the file, or correct the value that was reported. | credit analyst | The register value for debt-to-income ratio is missing or not valid. | |
| HMDA-LAR-24 | G | regulation | 12 CFR 1003.4(a)(24) | The register must report combined loan-to-value ratio for a covered loan, with an allowed value. | Record combined loan-to-value ratio from the file, or correct the value that was reported. | credit analyst | The register value for combined loan-to-value ratio is missing or not valid. | |
| HMDA-LAR-25 | G | regulation | 12 CFR 1003.4(a)(25) | The register must report loan term for a covered loan, with an allowed value. | Record loan term from the file, or correct the value that was reported. | loan operations | The register value for loan term is missing or not valid. | |
| HMDA-LAR-26 | G | regulation | 12 CFR 1003.4(a)(26) | The register must report introductory rate period for a covered loan, with an allowed value. | Record introductory rate period from the file, or correct the value that was reported. | loan operations | The register value for introductory rate period is missing or not valid. | |
| HMDA-LAR-27 | G | regulation | 12 CFR 1003.4(a)(27) | The register must report non-amortizing features for a covered loan, with an allowed value. | Record non-amortizing features from the file, or correct the value that was reported. | loan operations | The register value for non-amortizing features is missing or not valid. | |
| HMDA-LAR-28 | G | regulation | 12 CFR 1003.4(a)(28) | The register must report property value for a covered loan, with an allowed value. | Record property value from the file, or correct the value that was reported. | credit analyst | The register value for property value is missing or not valid. | |
| HMDA-LAR-29 | G | regulation | 12 CFR 1003.4(a)(29) | The register must report manufactured home secured property type for a covered loan, with an allowed value. | Record manufactured home secured property type from the file, or correct the value that was reported. | loan officer | The register value for manufactured home secured property type is missing or not valid. | |
| HMDA-LAR-30 | G | regulation | 12 CFR 1003.4(a)(30) | The register must report manufactured home land property interest for a covered loan, with an allowed value. | Record manufactured home land property interest from the file, or correct the value that was reported. | loan officer | The register value for manufactured home land property interest is missing or not valid. | |
| HMDA-LAR-31 | G | regulation | 12 CFR 1003.4(a)(31) | The register must report total units for a covered loan, with an allowed value. | Record total units from the file, or correct the value that was reported. | loan officer | The register value for total units is missing or not valid. | |
| HMDA-LAR-32 | G | regulation | 12 CFR 1003.4(a)(32) | The register must report multifamily affordable units for a covered loan, with an allowed value. | Record multifamily affordable units from the file, or correct the value that was reported. | loan officer | The register value for multifamily affordable units is missing or not valid. | |
| HMDA-LAR-33 | G | regulation | 12 CFR 1003.4(a)(33) | The register must report application channel for a covered loan, with an allowed value. | Record application channel from the file, or correct the value that was reported. | loan operations | The register value for application channel is missing or not valid. | |
| HMDA-LAR-34 | G | regulation | 12 CFR 1003.4(a)(34) | The register must report nMLS identifier for a covered loan, with an allowed value. | Record nMLS identifier from the file, or correct the value that was reported. | loan operations | The register value for nMLS identifier is missing or not valid. | |
| HMDA-LAR-35 | G | regulation | 12 CFR 1003.4(a)(35) | The register must report automated underwriting system and result for a covered loan, with an allowed value. | Record automated underwriting system and result from the file, or correct the value that was reported. | credit analyst | The register value for automated underwriting system and result is missing or not valid. | |
| HMDA-LAR-36 | G | regulation | 12 CFR 1003.4(a)(36) | The register must report reverse mortgage flag for a covered loan, with an allowed value. | Record reverse mortgage flag from the file, or correct the value that was reported. | loan operations | The register value for reverse mortgage flag is missing or not valid. | |
| HMDA-LAR-37 | G | regulation | 12 CFR 1003.4(a)(37) | The register must report open-end line of credit flag for a covered loan, with an allowed value. | Record open-end line of credit flag from the file, or correct the value that was reported. | loan operations | The register value for open-end line of credit flag is missing or not valid. | |
| HMDA-LAR-38 | G | regulation | 12 CFR 1003.4(a)(38) | The register must report business or commercial purpose flag for a covered loan, with an allowed value. | Record business or commercial purpose flag from the file, or correct the value that was reported. | loan operations | The register value for business or commercial purpose flag is missing or not valid. | |

### What the loan officer asks the customer for

| Missing fact | Label shown | Sentence shown | Review |
|---|---|---|---|
| agricultural_purpose | farm use of the loan | Regulation C may not cover a farm loan. We need to know if the customer will use this loan mainly for farm purposes. | |
| business_commercial_purpose | business use of the loan | Regulation C may not cover a business loan. We need to know if the customer will use this loan mainly for business purposes. | |
| loan_purpose | loan purpose | A business loan is covered only if it buys a home, improves a home or refinances. We need the purpose of the loan. | |
| lar.applicant | applicant ethnicity, race and sex | The register needs the applicant's ethnicity, race and sex. Ask; the applicant may decline; record the decline. | |
| lar.co_applicant | co-applicant ethnicity, race and sex | The register needs the co-applicant's ethnicity, race and sex. Ask; the co-applicant may decline; record the decline. | |
| lar.age | age of the applicant | The register needs the applicant's age. We use the date of birth on the application. | |
| lar.income | gross annual income | The register needs the income that we used in the credit decision. We need the gross yearly income. | |
| lar.property_address | property address | The register needs the street address of the property. We need the full address, with city, state and ZIP code. | |
| lar.loan_purpose | purpose of the loan | The register needs the purpose of the loan, such as a home purchase. We need to know what the loan is for. | |
| lar.preapproval | preapproval request | For a home purchase, the register needs to know if the customer asked for a preapproval. We need their answer. | |
| lar.construction_method | construction method | The register needs to know if the home is site-built or a manufactured home. We need the type of home. | |
| lar.occupancy_type | how the home will be used | The register needs to know if the home is a main home, a second home or an investment. We need how the customer will use it. | |
| lar.total_units | number of units | The register needs the number of units in the property. We need how many units the property has. | |
| lar.manufactured_home_secured_property_type | manufactured home and land | For a manufactured home, the register needs to know if the loan covers the home and the land. We need what the loan secures. | |
| lar.manufactured_home_land_property_interest | land ownership | For a manufactured home, the register needs how the customer holds the land. We need whether they own it or lease it. | |

### Facts routed to compliance, not the customer

| Missing fact | Label shown | Sentence shown | Review |
|---|---|---|---|
| exclusions.* | excluded-transaction check | The institution must record whether the transaction type "{1}" applies. | |
| prior_year_originations.* | origination counts | The institution must record its {1} originations for the two preceding years. | |
| application_date | application date | Loan operations must record the application date to check the order of events. | |
| apr/apor | APR and APOR | Loan operations must record the APR and the APOR to compute the rate spread. | |
| reported_rate_spread | reported rate spread | Loan operations must record the rate spread that the register reports. | |
| lar.co-applicant.* | how the co-applicant's information was collected | The loan officer must record whether visual observation or surname was used. | |
| lar.applicant.* | how the applicant's information was collected | The loan officer must record whether visual observation or surname was used. | |
| lar.property_state | property state | Loan operations must record the state of the property. | |
| lar.property_county | property county | Loan operations must record the county of the property. | |
| lar.property_census_tract | census tract | Loan operations must record the 11-digit census tract of the property. | |
| lar.multifamily_affordable_units | affordable units | The loan officer must record the number of income-restricted units in the property. | |
| lar.loan_type_government_program | government program | Loan operations must record the government insurance or guarantee program, if any. | |
| lar.uli | universal loan identifier | Loan operations must record the universal loan identifier. | |
| lar.loan_amount | loan amount | Loan operations must record the amount of the loan. | |
| lar.purchaser_type | type of purchaser | Loan operations must record who bought the loan. | |
| lar.hoepa_status | high-cost status | Loan operations must record the HOEPA status of the loan. | |
| lar.lien_status | lien status | Loan operations must record whether the lien is first or subordinate. | |
| lar.credit_scores | credit score | The credit analyst must record the credit score and the scoring model. | |
| lar.total_loan_costs | total loan costs | Closing staff must record the total loan costs from the Closing Disclosure. | |
| lar.total_borrower_paid_charges | total borrower-paid charges | Closing staff must record the total of the charges the borrower paid. | |
| lar.discount_points | discount points | Closing staff must record the discount points. | |
| lar.lender_credits | lender credits | Closing staff must record the lender credits. | |
| lar.interest_rate | interest rate | Closing staff must record the interest rate. | |
| lar.prepayment_penalty_term_months | prepayment penalty term | Closing staff must record the prepayment penalty term in months. | |
| lar.debt_to_income_ratio | debt-to-income ratio | The credit analyst must record the debt-to-income ratio used in the decision. | |
| lar.combined_loan_to_value_ratio | combined loan-to-value ratio | The credit analyst must record the combined loan-to-value ratio used in the decision. | |
| lar.loan_term_months | loan term | Loan operations must record the loan term in months. | |
| lar.introductory_rate_period_months | introductory rate period | Loan operations must record the introductory rate period in months. | |
| lar.non_amortizing_features | non-amortizing features | Loan operations must record whether the loan has a balloon payment or similar features. | |
| lar.property_value | property value | The credit analyst must record the property value used in the decision. | |
| lar.application_channel | application channel | Loan operations must record how the application was submitted and to whom the note was payable. | |
| lar.nmls_identifier | NMLS identifier | Loan operations must record the NMLS identifier of the loan originator. | |
| lar.automated_underwriting | automated underwriting result | The credit analyst must record the automated underwriting system and its result. | |
| lar.reverse_mortgage | reverse mortgage flag | Loan operations must record whether the loan is a reverse mortgage. | |
| lar.open_end_line_of_credit | open-end line of credit flag | Loan operations must record whether the loan is an open-end line of credit. | |
| lar.business_or_commercial_purpose | business purpose flag | Loan operations must record whether the loan is for a business or commercial purpose. | |
| lar.denial_reasons | denial reasons | Credit operations must record one to four principal reasons for the denial. | |
| lar_context.* | register context flag | Loan operations must record the register context flag "{1}". | |
| lar.nuli | non-universal loan identifier | Loan operations must record the non-universal loan identifier when no universal identifier applies. | |
| lar.total_points_and_fees | total points and fees | Closing staff must record the total points and fees when no Closing Disclosure applies. | |

## Equal credit opportunity (ECOA, Regulation B)

Examiner word limit: 100.

### Findings (examiner wording and referral sentence)

| Rule id | Kind | Basis | Citation | Requirement (examiner) | Action | Who acts | Referral sentence | Review |
|---|---|---|---|---|---|---|---|---|
| ECOA-ADVERSE-ACTION | G | regulation | 12 CFR 1002.9(a)(1) | Adverse action starts the notice duties of 1002.9, so the decision type and the counteroffer outcome must be recorded. | Record the decision type, and for a counteroffer whether it was accepted or the response period passed. | credit operations | The decision type or the counteroffer result is not recorded. | |
| ECOA-NOTICE-TIMING-COUNTEROFFER | V | regulation | 12 CFR 1002.9(a)(1)(iv) | After an unaccepted counteroffer, adverse action notice is due within 90 days of the counteroffer notice. | Record the counteroffer notice date and the adverse action notice date, or send the late notice. | credit operations | The notice after the counteroffer is late or its dates are missing. | |
| ECOA-NOTICE-TIMING | V | regulation | 12 CFR 1002.9(a)(1), (c)(1) | The creditor must notify the applicant of the action taken, or of an incomplete application, within 30 days of the trigger date. | Record the notice date and the date the 30 days start, or send the late notice. | credit operations | The notice was sent after the 30-day limit, or a date is missing. | |
| ECOA-NOTICE-CONTENT | P | regulation | 12 CFR 1002.9(a)(2), (b)(1), (c)(2) | The notice must state the action, creditor, ECOA notice, agency address, and reasons or the right to them. | Record which required elements the notice has, and re-issue a notice that lacks one. | credit operations | The notice lacks a required element or the record of its content is incomplete. | |
| ECOA-REASONS-SPECIFIC | R | regulation | 12 CFR 1002.9(b)(2) | Statements of reasons for adverse action must be specific and indicate the principal reasons. | A reviewer checks the stated reasons against the decision and records whether they are specific. | compliance reviewer | A reviewer must decide if the stated reasons are specific enough. | |
| ECOA-NOTICE-RECIPIENT | P | regulation | 12 CFR 1002.9(f) | When there is more than one applicant, the notice goes to the primary applicant. | Record who received the notice, and send the notice to the primary applicant if it went elsewhere. | credit operations | The notice did not go to the primary applicant, or the recipient is not recorded. | |
| ECOA-MARITAL-INQUIRY | P | regulation | 12 CFR 1002.5(d)(1) | A creditor may not ask about marital status on individual unsecured credit outside community property; allowed terms are married, unmarried, separated. | Record whether marital status was asked in the credit decision process, and for what type of credit. | compliance reviewer | The record does not show whether marital status was asked; compliance must check this. | |
| ECOA-SPOUSE-SIGNATURE | P | regulation | 12 CFR 1002.7(d) | A creditor may not require the signature of a spouse or other person when the applicant qualifies alone, except as 1002.7(d) allows. | Record whether a signature was required, who signed, and whether the applicant qualified alone. | compliance reviewer | The record does not show if a spouse signature was required; compliance must check this. | |
| ECOA-AGE-PUBLIC-ASSISTANCE | P | regulation | 12 CFR 1002.6(b)(2) | Age and public-assistance income may be used only as 1002.6(b)(2) permits. | Record how age and public-assistance income were treated in the decision. | compliance reviewer | The record does not show how age or public-assistance income was used; compliance must check this. | |

### Facts routed to compliance, not the customer

| Missing fact | Label shown | Sentence shown | Review |
|---|---|---|---|
| marital_status_inquiry | whether marital status was asked | Compliance must record whether the institution asked about marital status. | |
| marital_status_inquiry.credit_type | credit type of the marital status question | Compliance must record the type of credit when marital status was asked. | |
| spouse_signature | whether a spouse signature was required | Compliance must record whether the institution required a spouse or other person to sign. | |
| spouse_signature.* | who signed and why | Compliance must record who signed and whether the applicant qualified alone. | |
| age_public_assistance | use of age and public-assistance income | Compliance must record how the decision treated age and public-assistance income. | |
| notice.date** | notice date | Credit operations must record the date the notice was sent and the date the 30 days start. | |
| counteroffer.notice_date** | counteroffer notice date | Credit operations must record the counteroffer notice date and the date the application was complete. | |
| counteroffer.accepted** | counteroffer result | Credit operations must record whether the counteroffer was accepted or the response period passed. | |
| notice.written | written notice | Credit operations must record whether a written notice was sent. | |
| notice.contents.* | notice content | Credit operations must record whether the notice has this element: {1}. | |
| incompleteness_notice.* | incompleteness notice content | Credit operations must record whether the incompleteness notice has this element: {1}. | |
| notice.specific_reasons | specific reasons | A reviewer must record whether the stated reasons are specific. | |
| notice.delivered_to | notice recipient | Credit operations must record who received the notice. | |

## Voluntary monitoring information (VMI)

Examiner word limit: 100.

### Findings (examiner wording and referral sentence)

| Rule id | Kind | Basis | Citation | Requirement (examiner) | Action | Who acts | Referral sentence | Review |
|---|---|---|---|---|---|---|---|---|
| VMI-COVERAGE | G | regulation | 12 CFR 1002.13(a)(1) | Monitoring information must be requested for a purchase or refinancing of a one- to four-unit principal residence secured by that dwelling. | Record the loan purpose, the occupancy, the lien and the number of dwelling units. | loan officer | The facts that show whether monitoring information must be requested are missing. | |
| VMI-PERMITTED | G | regulation | 12 CFR 1002.13(a)(1); 12 CFR 1003.4(a)(10) | Where collection is not required but the loan is reportable under Regulation C, collection is permitted. | Record whether the loan is reportable under Regulation C. | loan operations | Whether the loan is reportable under Regulation C is not recorded. | |
| VMI-PROHIBITED | P | regulation | 12 CFR 1002.5(d)(1) | A creditor may not request marital status for individual unsecured credit outside a community property context. | Stop requesting marital status for this credit type and record the correction. | compliance reviewer | Marital status was requested for credit where the rule forbids it. | |
| VMI-SUBSTITUTE | R | regulation | 12 CFR 1002.13(d) | A substitute monitoring program is allowed only when an agency required it. | A reviewer confirms the agency requirement and records it. | compliance reviewer | A reviewer must confirm that an agency required the substitute program. | |
| VMI-REQUEST | P | regulation | 12 CFR 1002.13(a)(1) | Where collection is required, the request for each item must be recorded. | Record the monitoring request for each item. | loan officer | No record of the monitoring request exists. | |
| VMI-REQUEST-* | G | regulation | 12 CFR 1002.13(a)(1), (b) | The creditor must request {1} as part of the application, and must note a declination. | Request {1}, record the answer or the declination, and note it on the form. | loan officer | The record does not show that {1} was requested, or the declination is not noted. | |
| VMI-OBSERVATION-* | P | regulation | 12 CFR 1002.13(b) | If the applicant declines to give {1}, the creditor must note it by visual observation or surname, to the extent possible. | Note {1} by visual observation or surname, and record that you did. | loan officer | The record does not show that {1} was noted by observation or surname. | |
| VMI-MARITAL-TERMS | P | regulation | 12 CFR 1002.13(a)(1)(iii) | Marital status must use only the terms married, unmarried and separated. | Correct the form to use only those terms. | loan officer | The form uses marital status terms that the rule does not allow. | |
| VMI-DISCLOSURE | P | regulation | 12 CFR 1002.13(c) | The applicant must be told why the information is requested, and that a declination is noted by observation or surname. | Record that the disclosure was given, and give it if it was not. | loan officer | The record does not show the monitoring disclosure was given. | |
| VMI-USE | P | institution policy | Institution policy; see 12 CFR 1002.4 and 1002.6 | Monitoring information must not be used in the credit decision. | Record whether the data was used in underwriting, and remove any use. | compliance reviewer | The record does not show that monitoring data stayed out of the credit decision. | |
| VMI-FIREWALL | P | institution policy | Institution policy; see 12 CFR 1002.4 and 1002.6 | Monitoring data must be kept apart from underwriting by restricted access, decision-makers without access, and access logging. | Record each firewall control, and put in place any that is missing. | compliance reviewer | A control that keeps monitoring data apart from underwriting is missing or not recorded. | |

### What the loan officer asks the customer for

| Missing fact | Label shown | Sentence shown | Review |
|---|---|---|---|
| primarily_purchase_or_refinance | purchase or refinance | We must ask for monitoring information on a purchase or refinance. We need to know which this loan is. | |
| principal_residence | main home | We must ask for monitoring information on a main home. We need to know if this is the customer's main home. | |
| dwelling_units | number of units | We must ask for monitoring information on a home with one to four units. We need the number of units. | |
| monitoring.items.* | {1} | We must ask for {1}. The applicant may decline; record the decline. | |

### Facts routed to compliance, not the customer

| Missing fact | Label shown | Sentence shown | Review |
|---|---|---|---|
| secured_by_dwelling | dwelling lien | Loan operations must record whether the home secures the loan. | |
| monitoring | monitoring request record | The loan officer must record whether the monitoring information was requested. | |
| monitoring.disclosure_given | monitoring disclosure | The loan officer must record whether the applicant was told why the information is requested. | |
| monitoring.items.*.requested | request record for {1} | The loan officer must record whether {1} was requested. | |
| monitoring.items.*.declination_noted | declination note for {1} | The loan officer must record whether the declination of {1} was noted on the form. | |
| monitoring.items.*.observation_or_surname_noted | observation note for {1} | The loan officer must record whether {1} was noted by observation or surname. | |
| data_use.used_in_underwriting | use of monitoring data | Compliance must record whether monitoring data was used in underwriting. | |
| firewall.* | firewall control | Compliance must record whether this control is in place: {1}. | |

## Flood zone determination (FZD)

Examiner word limit: 90.

### Findings (examiner wording and referral sentence)

| Rule id | Kind | Basis | Citation | Requirement (examiner) | Action | Who acts | Referral sentence | Review |
|---|---|---|---|---|---|---|---|---|
| FZD-APPLICABILITY | G | regulation | 12 CFR 614.4925 | The flood rules apply to a designated loan: a building or mobile home in a special flood hazard area where insurance is available. | Record the collateral structure, the SFHA status from the standard determination, and whether flood insurance is available. | loan officer | The facts that show whether the flood rules apply are missing or unreliable. | |
| FZD-DETERMINATION | V | regulation | 12 CFR 614.4940 | The institution must complete a standard flood hazard determination on the standard form before the transaction, and keep it. | Obtain or complete the standard determination form, date it, and retain it. | closing staff | The standard flood hazard determination is missing, incomplete or not retained. | |
| FZD-INSURANCE | V | regulation | 12 CFR 614.4930(a) | For a designated loan, flood insurance must cover the lesser of the loan balance and the maximum available, for the full term. | Record the policy, its amount and its term, and require coverage that meets the minimum. | loan officer | Flood coverage is missing, too low or does not cover the term. | |
| FZD-NOTICE | V | regulation | 12 CFR 614.4955 | The borrower must get a timely notice of special flood hazards with the required elements, and the lender must keep proof of receipt. | Send a complete notice, record its date and content, and retain proof of receipt. | closing staff | The flood hazard notice is late, incomplete or has no record of receipt. | |
| FZD-ESCROW | V | regulation | 12 CFR 614.4935(a) | A designated loan on residential improved real estate or a mobile home must escrow flood premiums, unless an exception applies. | Record whether premiums are escrowed and the credit purpose, or set up the escrow. | closing staff | Flood premiums are not escrowed, or the escrow facts are missing. | |
| FZD-FORCE-PLACEMENT | V | regulation | 12 CFR 614.4945(a) | If the borrower does not cure a lapse within 45 days of notice, the institution must force-place insurance. | Record the borrower notice date and the review date, and force-place coverage if the lapse is not cured. | servicing | A lapse in flood cover was not cured or force-placed, or its dates are missing. | |

### What the loan officer asks the customer for

| Missing fact | Label shown | Sentence shown | Review |
|---|---|---|---|
| collateral.structure | building on the property | To check flood rules, we need to know if a building or mobile home is on the property. | |
| insurance.coverage_amount | flood coverage amount | We need the amount of flood insurance coverage. Ask for the policy or the insurance declarations page. | |
| insurance.effective_date | flood policy start date | We need the date the flood insurance policy starts. Ask for the policy or the insurance declarations page. | |
| insurance.expiration_date | flood policy end date | We need the date the flood insurance policy ends. Ask for the policy or the insurance declarations page. | |
| credit_purpose | credit purpose | To check the escrow exception, we need to know if the loan is for business or farm use. | |

### Facts routed to compliance, not the customer

| Missing fact | Label shown | Sentence shown | Review |
|---|---|---|---|
| sfha.in_sfha | flood zone status | Closing staff must record the flood zone status from the standard determination form. | |
| sfha.flood_insurance_available | flood insurance availability | Closing staff must record whether flood insurance is available for this property. | |
| determination.* | flood determination record | Closing staff must record this item of the standard determination: {1}. | |
| insurance.max_available_coverage | maximum flood coverage available | Closing staff must record the maximum flood coverage available for this property. | |
| loan_balance | loan balance | Closing staff must record the loan balance to compare it with the coverage. | |
| notice.borrower_date | flood notice date | Closing staff must record the date the borrower got the flood hazard notice. | |
| notice.servicer_date | servicer notice date | Servicing must record the date the servicer was notified. | |
| notice.record_retained | notice receipt record | Closing staff must record whether a receipt record of the notice is kept. | |
| notice.contents.* | notice content | Closing staff must record whether the notice has this element: {1}. | |
| escrow.escrowed | flood premium escrow | Closing staff must record whether flood premiums are escrowed. | |
| monitoring.** | lapse follow-up dates | Servicing must record the borrower notice date and the review date for the lapse. | |

## High volatility commercial real estate (HVCRE)

Examiner word limit: 90.

### Findings (examiner wording and referral sentence)

| Rule id | Kind | Basis | Citation | Requirement (examiner) | Action | Who acts | Referral sentence | Review |
|---|---|---|---|---|---|---|---|---|
| HVCRE-EFFECTIVE | G | regulation | 12 CFR 628.2, HVCRE exposure paragraph (3) | An HVCRE exposure does not include a loan made before the effective date of the definition. | Record the date the loan was made. | credit analyst | The date the loan was made is missing. | |
| HVCRE-RECLASSIFIED | R | regulation | 12 CFR 628.2, HVCRE exposure paragraphs (4), (6) | A facility reclassified by the institution as a non-HVCRE exposure is no longer treated as HVCRE. | Record the reclassification and the evidence that supports it. | compliance reviewer | A reclassification of the facility needs a reviewer check. | |
| HVCRE-DEFINITION | G | regulation | 12 CFR 628.2, HVCRE exposure paragraph (1) | A facility is HVCRE when it finances acquisition, development or construction, aims at income-producing property, and depends on future income for repayment. | Record the answer to each of the three prongs. | credit analyst | One of the three prongs of the HVCRE test is not recorded. | |
| HVCRE-EXCL-RESIDENTIAL | G | regulation | 12 CFR 628.2, HVCRE exposure paragraph (2)(i)(A) | A loan for a one- to four-family residential property is excluded when the dwelling is at least 50 percent of the collateral value. | Record the property type and the dwelling share of the appraised collateral value. | credit analyst | The property type or the dwelling share of collateral value is not recorded. | |
| HVCRE-EXCL-AGRICULTURAL | G | regulation | 12 CFR 628.2, HVCRE exposure paragraph (2)(i)(C) | Financing for the agricultural needs of a bona fide farmer, rancher or producer is excluded. | Record whether the loan finances agricultural land for a bona fide farmer, rancher or producer. | loan officer | Whether the loan finances a bona fide farmer's needs is not recorded. | |
| HVCRE-EXCL-EXISTING-INCOME | G | regulation | 12 CFR 628.2, HVCRE exposure paragraph (2)(ii) | A loan to acquire or refinance existing income-producing property is excluded when cash flow supports permanent financing. | Record whether the property already produces income and whether cash flow meets permanent-financing criteria. | credit analyst | Whether the property already produces income, or its cash flow, is not recorded. | |
| HVCRE-EXCL-EXISTING-IMPROVEMENTS | G | regulation | 12 CFR 628.2, HVCRE exposure paragraph (2)(iii) | A loan for improvements to existing income-producing property is excluded when cash flow supports permanent financing. | Record whether this is an improvement to income-producing property and whether cash flow meets the criteria. | credit analyst | Whether this improves an income-producing property, or its cash flow, is not recorded. | |
| HVCRE-EXCL-CAPITAL | G | regulation | 12 CFR 628.2, HVCRE exposure paragraph (2)(iv) | A project is excluded when loan-to-value is within the limit and the borrower contributed and kept 15 percent capital. | Record the loan-to-value ratio and limit, the as-completed value, the contributions, and the timing and retention of the capital. | credit analyst | The capital test cannot be done because a value, a contribution or the loan-to-value limit is missing. | |
| HVCRE-EXCL-SMALL-LOAN | G | regulation | 12 CFR 628.2, HVCRE exposure paragraph (2)(v) | A loan under the pinned small-loan amount is excluded. | Record the amount of the credit facility. | credit analyst | The amount of the credit facility is missing. | |

### What the loan officer asks the customer for

| Missing fact | Label shown | Sentence shown | Review |
|---|---|---|---|
| property.agricultural_land_bona_fide_farmer | farm use of the land | To check an exclusion, we need to know if the land is for the farmer's own farm needs. | |

### Facts routed to compliance, not the customer

| Missing fact | Label shown | Sentence shown | Review |
|---|---|---|---|
| primarily_finances_adc | acquisition, development or construction purpose | The credit analyst must record whether the loan finances acquisition, development or construction. | |
| purpose_income_producing | income-producing purpose | The credit analyst must record whether the aim is income-producing property. | |
| dependent_on_future_income_or_sales | repayment from future income | The credit analyst must record whether repayment depends on future income or sales. | |
| credit_facility_amount | credit facility amount | The credit analyst must record the amount of the credit facility. | |
| property.* | property fact | The credit analyst must record this property fact: {1}. | |
| capital.* | capital contribution fact | The credit analyst must record this capital fact: {1}. | |
| capital.ltv_ratio** | loan-to-value ratio and limit | The credit analyst must record the loan-to-value ratio and the Appendix A limit with its source. | |
| capital.as_completed_value** | as-completed value and contributions | The credit analyst must record the as-completed value and the borrower's capital contributions. | |

## Cross-regime auditor

Examiner word limit: 110.

### Findings (examiner wording and referral sentence)

| Rule id | Kind | Basis | Citation | Requirement (examiner) | Action | Who acts | Referral sentence | Review |
|---|---|---|---|---|---|---|---|---|
| AUD-AGENTS | G | institution policy | Institution audit policy | Every expected regime must report a result; a missing agent is never assumed to pass. | Rerun or repair the regime whose result is missing. | loan operations | A regime did not report a result. | |
| AUD-RATE-SPREAD | V | institution policy | Institution audit policy; 12 CFR 1003.4(a)(12) | The rate spread reported for HMDA must agree with the spread computed from the APR minus the APOR. | Correct the reported rate spread or the APR or APOR input that differs. | loan operations | The HMDA rate spread differs from the spread computed from APR minus APOR. | |
| AUD-PRICING | V | institution policy | Institution audit policy | The APR, APOR and rate-set evidence must be the same in the HPML and HMDA cases. | Correct the pricing input that differs between the cases. | loan operations | The pricing figures differ between the HPML and HMDA cases. | |
| AUD-AMOUNT | V | institution policy | Institution audit policy | The loan amount must be the same in every case. | Correct the loan amount that differs between the cases. | loan operations | The loan amount differs between cases. | |
| AUD-DATES | V | institution policy | Institution audit policy | The application, decision and closing dates must be consistent across the cases. | Correct the date that differs between the cases. | loan operations | A date differs between cases. | |
| AUD-CASE-ID | V | institution policy | Institution audit policy | One loan must carry one case id in every case. | Correct the case id that differs. | loan operations | The case id differs between cases. | |
| AUD-DEMOGRAPHICS | V | institution policy | Institution audit policy; 12 CFR 1002.13, 12 CFR 1003.4(a)(10) | Demographic data recorded as provided or declined for monitoring must also appear in the HMDA register. | Carry the monitoring record into the HMDA register, or explain the difference. | loan operations | Monitoring data and the HMDA register disagree on demographic items. | |
| AUD-OCCUPANCY | V | institution policy | Institution audit policy | The principal-residence fact must agree across the VMI, HPML and HMDA cases. | Correct the occupancy fact that differs between the cases. | loan operations | The occupancy fact differs between cases. | |
| AUD-SCOPE | V | institution policy | Institution audit policy | The VMI reportability flag must agree with the HMDA coverage result. | Correct the reportability flag or the HMDA coverage input. | loan operations | VMI and HMDA disagree on whether the loan is reportable. | |
| AUD-SHARED-GAP | G | institution policy | Institution audit policy | A fact missing in more than one regime is one gap and is closed once. | Obtain the fact once and supply it to every regime that lists it. | loan operations | One missing fact blocks more than one regime. | |

### Facts routed to compliance, not the customer

| Missing fact | Label shown | Sentence shown | Review |
|---|---|---|---|
| agent:* | regime result | The {1} regime gave no result; loan operations must rerun it. | |

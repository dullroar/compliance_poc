# Compliance Review Summary

## Executive Summary

Case TEST-2024-001 (Loan LN-2024-001) involves a $425,000 fixed-rate, 30-year first-lien purchase-money mortgage originated by Example Farm Credit ACA on May 1, 2024, to joint borrowers John and Mary Smith. The collateral is a 240-acre farm with a site-built single-family principal residence in Shelby County, Illinois. Seven compliance domains were reviewed: HMDA, ECOA, HPML, HVCRE, Flood Zone Determination (FZD), YBS, and VMI. No domain returned a clean pass. HVCRE is Not Applicable with high confidence and no substantive deficiencies. FZD is Compliant with moderate confidence, subject to documentation gaps. HMDA, ECOA, YBS, and VMI each returned Potential Issue with moderate confidence. HPML returned Non-Compliant with moderate confidence based on a provisionally confirmed Higher-Priced Mortgage Loan classification.

The most consequential finding across the entire file is a single unresolved data contradiction: the HMDA-reported rate spread of 2.37 percentage points is arithmetically irreconcilable with the structured APR (8.12%) and APOR (7.02%) fields, which produce a calculated spread of 1.10 percentage points. This discrepancy simultaneously affects HMDA LAR accuracy, HPML classification under Regulation Z, and ECOA examination readiness. Resolving it is the single highest-priority action in the file, because its outcome determines whether HPML obligations attach — and if they do, additional documented violations in appraisal notice delivery and timing exist. Beyond the rate spread issue, the file exhibits three systemic patterns: demographic data is entirely absent from the record despite process flags indicating collection occurred; income, identity, and co-borrower documentation are missing across multiple regulatory domains; and the manual underwrite was completed without quality control sign-off or secondary review documentation.

The loan file in its current state is not examination-ready under FCA standards for any of the five regimes returning Potential Issue or Non-Compliant determinations. The primary closing instruments are present and the origination chronology is internally consistent and valid. However, the file was assembled around execution documents without a corresponding retention standard for the borrower-evidence, demographic-data, and regulatory-determination documentation required across the institution's full compliance footprint. Remediation is achievable through targeted file reconstruction and process improvements described throughout this report, but must be completed before HMDA LAR submission and before this file could withstand FCA examination scrutiny.

---

## Overall Compliance Posture

| Domain | Result | Confidence |
|---|---|---|
| HMDA / Regulation C | Potential Issue | Moderate |
| ECOA / Regulation B | Potential Issue | Moderate |
| HPML / Regulation Z | Non-Compliant (Provisional) | Moderate |
| HVCRE | Not Applicable | High |
| Flood Zone Determination | Compliant | Moderate |
| FCA YBS Eligibility | Potential Issue | Moderate |
| VMI / Demographic Data | Potential Issue | Moderate |
| Cross-Regime Audit | Multiple Cross-Regime Deficiencies | High |

**Summary:** No domain is fully clean. One domain (HPML) carries a provisional Non-Compliant designation contingent on resolution of the rate spread contradiction. Five domains carry Potential Issue designations driven by documentation gaps, missing evidence, and data quality deficiencies. Two domains (HVCRE and FZD) are substantively satisfactory, with remediation needs limited to file documentation and metadata completeness. The overall compliance posture is materially deficient for examination readiness purposes and requires prioritized remediation before LAR submission.

---

## Findings Requiring Action

### Finding 1: Rate Spread and APR/APOR Data Contradiction

**Description:** The HMDA rate spread field reports 2.37 percentage points. The structured APR field shows 8.12% and the APOR field shows 7.02%, which produces a calculated spread of only 1.10 percentage points (8.12 − 7.02 = 1.10). These two figures are arithmetically irreconcilable using the same inputs. A rate spread of 2.37 would imply either an effective APR of approximately 9.39% against the stated APOR, or a different APOR benchmark date than what is documented. No APR calculation worksheet, no FFIEC APOR weekly table entry for the lock date (April 10, 2024), and no rate lock confirmation are present in the file to resolve the contradiction.

**Impact:** This single data error has cascading consequences across three regulatory regimes. For HMDA, the rate spread is a required LAR field; an inaccurate value is a material data deficiency subject to resubmission requirements and FCA examination citation. For HPML, the spread determines whether the loan is a Higher-Priced Mortgage Loan under Regulation Z: if the correct spread is 1.10 percentage points, the first-lien HPML threshold of 1.50 percentage points is not met and HPML obligations do not attach; if the correct spread is at or above 1.50 percentage points, HPML status is confirmed and mandatory escrow, appraisal right-to-receive notice, appraisal delivery timing, flip-rule analysis, and ability-to-repay documentation requirements are all triggered. For ECOA, the HPML determination affects the scope of fair lending and Regulation Z obligations that must be demonstrated for examination readiness. This is the single most consequential unresolved item in the file.

**Evidence:** APR calculation worksheet is absent. FFIEC APOR weekly table for the week of April 10, 2024 is absent. Rate lock confirmation agreement is absent. The APOR source is identified as the FFIEC APOR Table but no source document is present. Closing Disclosure is present and supports a consummation date of May 1, 2024.

**Required Remediation:** (1) Retrieve the rate lock confirmation from the loan origination system and confirm the lock date. (2) Pull the FFIEC APOR weekly table for the week containing April 10, 2024, for a 30-year fixed-rate first-lien product. (3) Run the FFIEC Rate Spread Calculator using the confirmed APR from the Closing Disclosure and the verified APOR. (4) Compare the resulting spread against the HMDA LAR field (2.37); correct the LAR field to the verified figure. (5) If the corrected spread is at or above 1.50 percentage points, initiate a formal HPML compliance review (see Finding 3 below). (6) If the corrected spread is below 1.50 percentage points, document the Non-HPML determination in the file and update all downstream LAR fields accordingly. (7) File and retain the APR worksheet, APOR table page, and rate lock confirmation.

**Responsible Party:** Compliance Officer; Loan Origination System Administrator; Originating Loan Officer

**Priority:** Critical

**Supporting Agent(s):** HMDA Compliance Agent, ECOA Compliance Agent, HPML Compliance Agent, Compliance Auditor

---

### Finding 2: Demographic Data Entirely Absent Despite Confirmed VMI Collection

**Description:** The demographic information block — containing ethnicity, race, and sex for both the primary applicant (John Smith) and co-applicant (Mary Smith) — is completely empty in the case record. This is internally inconsistent: the process flags confirm that VMI was presented to the applicants, the applicants provided the information, visual observation was not needed, and demographic data was segregated. Yet no actual demographic values exist anywhere in the record for either borrower. Additionally, no VMI collection form identifier, no collection date, no applicant acknowledgment of the voluntary nature of collection, no refusal or non-refusal documentation, and no disaggregated ethnicity and race sub-categories (required under the 2018 HMDA rule) are present. The co-applicant Mary Smith has no demographic record of any kind despite the joint application requirement to collect separately from each applicant.

**Impact:** This deficiency simultaneously violates or creates examination risk under three regulatory regimes. Under HMDA/Regulation C (12 CFR 1003.4(a)(10)(i)–(ii)), ethnicity, race, and sex must be reported on the LAR for both applicants; the LAR cannot be submitted in a complete and accurate state without these values. Under Regulation B (12 CFR 1002.13), collected demographic data must be retained; the complete absence of values when collection is asserted to have occurred is a record-keeping deficiency. Under ECOA fair lending standards, the absence of demographic records prevents any consistency-of-treatment analysis by an examiner. The firewall and segregation controls are asserted by boolean flags only, with no corroborating audit log or access control report, which is insufficient for FCA examination purposes.

**Evidence:** Process flags confirm collection (vmi_collection_required, vmi_presented_to_applicant, applicant_provided_vmi all true). Demographic information block is empty for both applicants. No VMI form, form identifier, collection date, or applicant acknowledgment present. No audit log or system access report confirming firewall. No HMDA LAR demographic field extract confirming completeness.

**Required Remediation:** (1) Retrieve the original GMI/VMI collection form or LOS demographic screen for LN-2024-001. (2) Confirm whether demographic values (ethnicity, race, sex — including disaggregated sub-categories) were recorded for both John Smith and Mary Smith. (3) If values exist in the LOS but were not extracted into the case record, extract, document, and populate the HMDA LAR fields. (4) If values were never recorded despite the process flags indicating collection occurred, investigate whether a data entry failure occurred, remediate, and document the corrective action. (5) Ensure the VMI collection form is filed with form identifier, collection date, applicant acknowledgment of voluntary nature, and an explicit refusal or non-refusal notation for each applicant. (6) Pull the LOS audit log for LN-2024-001 confirming underwriting personnel did not access demographic data prior to the April 10, 2024 credit decision and retain in the compliance file. (7) Update the HMDA LAR entry to reflect complete demographic fields for both the primary applicant and co-applicant before submission.

**Responsible Party:** Compliance Officer; Loan Origination System Administrator; Originating Loan Officer

**Priority:** Critical

**Supporting Agent(s):** VMI Compliance Agent, HMDA Compliance Agent, ECOA Compliance Agent, Compliance Auditor

---

### Finding 3: HPML Appraisal Procedural Obligations — Right-to-Receive Notice and Pre-Consummation Delivery

**Description:** Under the provisional HPML classification (contingent on resolution of Finding 1), two appraisal-related procedural obligations under Regulation Z are not supported by any evidence in the file. First, the creditor was required to notify the applicants of their right to receive a copy of each written appraisal within three business days of receiving the application (application date: March 15, 2024; deadline: approximately March 20, 2024) under 12 CFR 1026.35(c)(5). No such notice is present in the file. Second, the creditor was required to provide a copy of each written appraisal to the applicants no later than three business days before consummation (consummation date: May 1, 2024; delivery deadline: approximately April 26, 2024) under 12 CFR 1026.35(c)(6)(i). The appraisal was received by the institution on March 28, 2024, making timely delivery entirely feasible, but no delivery log, borrower-signed receipt, transmittal letter, or email confirmation is present in the file.

**Impact:** If HPML status is confirmed upon resolution of Finding 1, the absence of evidence for either obligation is a documented regulatory deficiency under Regulation Z. The right-to-receive notice gap is a procedural HPML violation. The pre-consummation delivery gap — if the appraisal was not delivered until closing on May 1 — would be a timing violation. These findings are confined to HPML and do not parallel findings in other domains, but they compound the overall Non-Compliant HPML determination. If HPML status is not confirmed, these obligations do not attach and no violation exists.

**Evidence:** No appraisal right-to-receive notice is present in the supporting documents. No delivery log, borrower receipt, or transmittal evidence is present. Appraisal report is present (dated March 28, 2024, received by institution March 28, 2024). Consummation date confirmed May 1, 2024. Application date confirmed March 15, 2024.

**Required Remediation:** (1) This finding is contingent on resolution of Finding 1. Resolve the rate spread contradiction first. (2) If HPML status is confirmed: search the file and LOS for the appraisal right-to-receive notice required by March 20, 2024; if it was not issued or not documented, record as a regulatory violation and assess remediation options with counsel. (3) Search for evidence that the appraisal was delivered to the applicants by April 26, 2024; locate the delivery log, borrower-signed receipt, or transmittal evidence; if delivery occurred only at closing on May 1, document as a timing violation. (4) Document the flip-rule analysis under 12 CFR 1026.35(c)(4): review the title commitment for prior sale history, assess whether the seller acquired the property within 180 days and whether price-increase thresholds are met, and file a written conclusion. (5) If HPML status is not confirmed, document the Non-HPML determination and note these obligations did not attach.

**Responsible Party:** Compliance Officer; Originating Loan Officer

**Priority:** Critical (contingent on HPML confirmation)

**Supporting Agent(s):** HPML Compliance Agent, Compliance Auditor

---

### Finding 4: Loan Estimate Absent — TRID Disclosure Deficiency

**Description:** The Loan Estimate required under TRID (12 CFR 1026.19(e)) is not present in the supporting documents for this purchase transaction. For a consumer-purpose, dwelling-secured closed-end loan originated in 2024, the Loan Estimate must be delivered within three business days of application (deadline: March 20, 2024) and at least seven business days before consummation (deadline: April 22, 2024). The Closing Disclosure is present, but without the Loan Estimate, initial APR disclosure accuracy, waiting period compliance, and APR tolerance testing cannot be verified.

**Impact:** The absence of the Loan Estimate is a standalone TRID compliance concern independent of HPML status. It prevents APR tolerance verification — which is also directly relevant to resolving the rate spread contradiction identified in Finding 1. An examiner would request the Loan Estimate as a baseline document for any purchase transaction review. Failure to produce it creates examination risk regardless of whether a substantive violation occurred.

**Evidence:** Closing Disclosure is present in supporting documents. Loan Estimate is not listed in any supporting document category across any agent review. Application date is March 15, 2024. Consummation date is May 1, 2024.

**Required Remediation:** (1) Retrieve the Loan Estimate from the loan origination system. (2) Confirm the issuance date and delivery method relative to the March 15, 2024 application date (three-business-day deadline: March 20, 2024). (3) Confirm at least seven business days elapsed between Loan Estimate delivery and May 1, 2024 consummation (deadline: April 22, 2024). (4) Compare the APR disclosed on the Loan Estimate against the final APR on the Closing Disclosure for tolerance compliance under 12 CFR 1026.19(e)(3). (5) Add the Loan Estimate to the loan file. (6) If the Loan Estimate was not issued within the required period or is confirmed missing, document as a TRID compliance deficiency and assess remediation options.

**Responsible Party:** Compliance Officer; Originating Loan Officer

**Priority:** Critical

**Supporting Agent(s):** HPML Compliance Agent, Compliance Auditor

---

### Finding 5: Systemic Missing Income, Identity, and Co-Borrower Documentation

**Description:** Five independent compliance agents identified overlapping gaps in income documentation, applicant identity documentation, and co-borrower (Mary Smith) data. The HMDA income field (gross annual income relied on in the credit decision) is absent. Income verification documents — tax returns, Schedule F, farm financial statements — are not confirmed in the file, despite being required for HPML ability-to-repay compliance (12 CFR 1026.43) and YBS Small Farmer threshold confirmation. Government-issued identification confirming date of birth is absent for both John Smith and Mary Smith, preventing confirmed YBS Young Farmer age analysis. Individual credit reports for each joint applicant are not listed in the file, preventing independent creditworthiness verification for each borrower. Mary Smith's age, farming experience, demographic information, and YBS eligibility are entirely absent from any document or field across all reviewed domains.

**Impact:** This pattern of missing documentation simultaneously creates deficiencies across HMDA (income field required for LAR), HPML (ATR documentation for first-lien HPML), YBS (age and sales documentation required for confirmed classification and FCA Call Report submission), ECOA (individual credit reports support fair lending consistency review), and VMI (co-applicant demographic collection). The shared institutional root cause is the absence of a file assembly standard that requires retention of income verification, identity, and co-borrower documentation as a baseline for all covered transactions. An FCA examiner reviewing this file would find the borrower-evidence layer largely absent.

**Evidence:** No income figure in the HMDA submission. No Schedule F or tax returns referenced in any agent's supporting document inventory. No government-issued ID for either applicant referenced. No individual credit reports listed. Mary Smith has no age, farming experience, or demographic data in any field or document. Credit approval memorandum is present but its content is not confirmed to include income verification detail or individual credit report references.

**Required Remediation:** (1) Extract and document the gross annual income relied on in the credit decision from the credit approval memorandum or underwriting worksheet; populate the HMDA LAR income field and confirm the source. (2) Collect and file government-issued identification (driver's license or passport) confirming date of birth for both John Smith and Mary Smith; record exact ages as of the evaluation date. (3) Collect and file income verification documents used in underwriting (federal tax returns with Schedule F, farm financial statements) supporting both the HMDA income field and HPML ATR documentation. (4) Document farming start date and corroborating evidence (Schedule F history, FSA records) for both John Smith and Mary Smith to support YBS Beginning Farmer and Small Farmer determinations. (5) Confirm individual credit reports were pulled for each joint applicant and are present in the loan origination system; add to the physical or electronic file with pull date and score documentation. (6) Institutionally, implement a file assembly checklist requiring retention of these document categories at origination for all covered transactions.

**Responsible Party:** Compliance Officer; Originating Loan Officer; Credit Officer

**Priority:** Critical

**Supporting Agent(s):** HMDA Compliance Agent, ECOA Compliance Agent, HPML Compliance Agent, YBS Eligibility Compliance Agent, VMI Compliance Agent, Compliance Auditor

---

### Finding 6: HMDA LAR Incomplete — ULI, LEI, Total Loan Costs, AUS Coding, NMLS Role, Census Tract Verification

**Description:** Multiple required HMDA LAR fields are absent or unverified. The Universal Loan Identifier (ULI) is not present; a ULI is required for every covered loan on the LAR under 12 CFR 1003.4(a)(1)(i). The institution's Legal Entity Identifier (LEI) is absent; it is required on the LAR submission header and is the foundational component of ULI construction. Total loan costs or origination charges are not extracted from the Closing Disclosure, though the document is present. The AUS entry of "None / Manual underwrite" must be translated to FFIEC FIG 2024 code 1111 (Not Applicable) in the LAR. The NMLS identifier provided (987654) has not been confirmed as the individual loan originator's NMLS ID versus an institution-level identifier. Census tract 17173960200 has not been verified through the FFIEC Geocoding System for the rural route address.

**Impact:** Absent the ULI and LEI, the LAR entry cannot be submitted. An incorrect AUS code is a LAR data quality deficiency. An institution-level NMLS ID in the individual originator field is a reporting error. An unverified census tract carries geocoding accuracy risk. These gaps collectively prevent LAR submission in a form that would satisfy Regulation C accuracy requirements or withstand FCA examination scrutiny.

**Evidence:** ULI field absent from submission. LEI absent from submission. Total loan costs not extracted. AUS system documented as "None / Manual underwrite" with no FFIEC FIG code assigned. NMLS 987654 present but role unconfirmed. Census tract 17173960200 provided for rural route address but geocoding not verified. Closing Disclosure present in file as a source document.

**Required Remediation:** (1) Retrieve the institution's active LEI from the GLEIF registry and record in HMDA compliance records and the loan origination system. (2) Construct the ULI per FFIEC FIG 2024 specifications using the institution's LEI and internal loan number; record in the LOS and LAR. (3) Extract total loan costs from the Closing Disclosure (Page 2, Section A) and populate the LAR field per 12 CFR 1003.4(a)(17). (4) Confirm no AUS was used; code AUS name and result fields as 1111 (Not Applicable) per FFIEC FIG 2024; document the manual underwrite basis in the file. (5) Cross-reference NMLS 987654 in the NMLS Consumer Access registry to confirm it is the individual loan originator's ID; if it is an institution-level ID, obtain the individual originator's NMLS ID and update the LAR. (6) Submit the property address to the FFIEC Geocoding System to verify census tract 17173960200; document the geocoding methodology if the rural route address does not geocode precisely.

**Responsible Party:** Compliance Officer; HMDA Reporting Officer; Loan Origination System Administrator

**Priority:** Critical (LAR submission blocker)

**Supporting Agent(s):** HMDA Compliance Agent, Compliance Auditor

---

### Finding 7: YBS Designation Not Documented — Threshold Registry Unverified

**Description:** The primary borrower, John Smith (age 34, 4 years of farming experience, $185,000 gross farm sales), facially satisfies all three FCA YBS eligibility criteria simultaneously: Young (age under 35), Beginning (under 10 years of farming), and Small (gross sales under $250,000). Despite this, no YBS designation form, no cross-reference to the institution's FCA-required YBS plan, and no documentation of whether YBS-specific rates, terms, set-asides, or services were considered or offered is present in the file. Additionally, the YBS thresholds applied in this review were sourced from user-supplied input fields and have not been validated against a version-controlled, date-effective FCA Threshold Authority Registry record for the evaluation date of June 1, 2024. Co-borrower Mary Smith's YBS eligibility is entirely unaddressed.

**Impact:** FCA Regulation 4.20 and 12 CFR 614.4165 require Farm Credit ACAs to maintain YBS plans and to document YBS borrower status at origination. Failure to designate a qualifying borrower creates FCA Call Report data integrity risk and may indicate underservice of a statutorily protected class of agricultural borrowers. The use of age 34 for YBS favorable classification is permissible and distinct from the Regulation B prohibition on adverse age consideration, but this distinction must be explicitly documented to withstand ECOA examination scrutiny. Unverified thresholds prevent examination-defensible YBS reporting.

**Evidence:** No YBS designation form in file. No YBS plan reference. No documentation of YBS-specific terms offered or considered. Threshold values sourced from user-supplied fields only; no Threshold Authority Registry record supplied. Mary Smith's age and farming experience entirely absent. Government-issued ID, Schedule F, and tax returns not confirmed present.

**Required Remediation:** (1) Obtain and lock the FCA YBS Threshold Authority Registry record effective for the evaluation date of June 1, 2024. (2) Collect primary evidence: government-issued ID confirming dates of birth for both borrowers; tax returns with Schedule F confirming gross agricultural sales; farming start date documentation for both borrowers. (3) Complete a formal YBS eligibility determination for both John Smith and Mary Smith, covering Young, Beginning, and Small analyses individually. (4) Prepare and file a YBS eligibility determination memorandum referencing the locked threshold registry record and all primary evidence documents. (5) Cross-reference the institution's YBS plan; document whether any YBS-specific rates, terms, or services were considered or offered, and if not, document the basis. (6) Explicitly document the distinction between YBS favorable age use and the Regulation B adverse age consideration prohibition in the file. (7) Establish a YBS status change tracking record noting John Smith's proximity to the Young Farmer age threshold (one year to age 35) for annual reassessment.

**Responsible Party:** Compliance Officer; Originating Loan Officer; FCA Reporting Officer

**Priority:** Moderate

**Supporting Agent(s):** FCA YBS Eligibility Compliance Agent, ECOA Compliance Agent, Compliance Auditor

---

### Finding 8: Manual Underwrite Without Quality Control or Secondary Review Documentation

**Description:** The transaction was manually underwritten with no automated underwriting system result. No quality control review, secondary reviewer sign-off, or supervisor approval notation appears in the supporting documents. No rate lock confirmation is in the file. The credit approval memorandum references Agricultural Loan Policy Section 4.2 and documents decision factors (repayment capacity, collateral, credit history), but no documentation confirms a secondary reviewer evaluated the decision for policy consistency or fair lending compliance.

**Impact:** Manual underwrite files carry elevated disparate treatment risk under FCA fair lending examination guidance, particularly for joint applications involving YBS-classified borrowers. The absence of QC documentation reduces the institution's ability to demonstrate consistency of treatment across similarly situated applicants. For a provisionally classified HPML transaction, manual underwrite without QC sign-off also compounds the ability-to-repay documentation gap under 12 CFR 1026.43. The HMDA LAR AUS coding for manual underwrite (code 1111) must also be documented with a basis confirming no AUS was used.

**Evidence:** AUS system documented as "None / Manual underwrite." No QC checklist, second-reviewer sign-off, or supervisor approval referenced in any supporting document inventory. Rate lock agreement not listed in file. Credit approval memorandum present but secondary review notation absent.

**Required Remediation:** (1) Obtain retroactive QC or secondary review sign-off for this file, confirming the manual underwrite decision was consistent with Agricultural Loan Policy Section 4.2 and fair lending standards, if operationally feasible. (2) Retrieve the rate lock confirmation from the LOS and add to the file. (3) Confirm with the loan officer and LOS administrator that no AUS was used; document the basis in the file. (4) Institutionally, establish a documentation standard requiring that all manual underwrite approvals include a secondary reviewer sign-off, a documented rationale citing applicable policy provisions, and a QC checklist confirming fair lending consistency review prior to approval.

**Responsible Party:** Credit Officer; Compliance Officer; Originating Loan Officer

**Priority:** Moderate

**Supporting Agent(s):** HMDA Compliance Agent, ECOA Compliance Agent, HPML Compliance Agent, Compliance Auditor

---

### Finding 9: Flood Determination Documentation Gaps and Life-of-Loan Monitoring Not Confirmed

**Description:** The flood determination was completed on March 20, 2024, prior to consummation on May 1, 2024, and correctly identifies the collateral as Flood Zone X (non-SFHA). Flood insurance is not required. However, the flood determination certificate as presented is missing several metadata fields required for full examination validity: FEMA panel number, FEMA map effective date, NFIP community number, flood determination vendor name, and determination tracking number. Life-of-loan flood monitoring enrollment is not documented. Additionally, the 240-acre farm may contain agricultural structures beyond the principal dwelling; there is no evidence that all improved structures on the parcel were individually identified and evaluated for SFHA exposure.

**Impact:** Without the FEMA panel number and map effective date, the examiner cannot confirm the determination was made on a current, effective FIRM panel. Without the community number, NFIP participation status cannot be verified. Without life-of-loan monitoring documentation, the institution cannot demonstrate it is meeting its ongoing obligation to detect future map revisions that could trigger flood insurance, notice, and force-placement requirements. Multiple improved structures on a 240-acre farm may each constitute a "building" under the FDPA, each requiring separate evaluation.

**Evidence:** Flood Zone Determination Certificate listed in supporting documents. SFHA indicator false. Flood zone X. Determination date March 20, 2024. FEMA panel number, map effective date, community number, vendor name, and determination number all absent. Life-of-loan monitoring enrollment not documented.

**Required Remediation:** (1) Obtain and file the completed Standard Flood Hazard Determination Form or vendor-issued certificate confirming FEMA panel number, map effective date, NFIP community number, vendor name, and determination number. (2) Verify the FEMA map effective date against the current effective FIRM panel for Shelby County, Illinois, as of March 20, 2024. (3) Enroll the loan in a life-of-loan flood zone monitoring service and document enrollment in the loan file; if already enrolled, obtain and file enrollment confirmation. (4) Review the appraisal for a complete list of improvements on the 240-acre parcel; if structures beyond the principal dwelling are identified, confirm the flood determination covers all structures or obtain supplemental determinations. (5) Query the FEMA Flood Map Service Center to confirm no LOMA or LOMR is pending or recently effective for the subject parcel.

**Responsible Party:** Compliance Officer; Originating Loan Officer

**Priority:** Moderate

**Supporting Agent(s):** Flood Zone Determination Compliance Agent, Compliance Auditor

---

### Finding 10: HMDA Coverage Determination and Agricultural/Dwelling Edge Case Not Documented in File

**Description:** The transaction involves a 240-acre farm with an existing site-built single-family dwelling designated as the borrowers' principal residence. The HMDA coverage determination — that this agricultural-collateral transaction is a covered loan under Regulation C because the loan purpose is residential home purchase and the loan is secured by a principal-residence dwelling — has been made and supported by the HMDA agent but is not documented in the loan file itself. Similarly, the HPML agent noted the mixed-use property coverage determination is not documented in the file.

**Impact:** FCA examiners will scrutinize the basis for HMDA and HPML reporting of agricultural collateral transactions. The absence of a documented rationale for coverage creates examination risk and may require the institution to reconstruct its analysis under examination conditions. A brief written memorandum in the file creates a durable, examiner-defensible record.

**Evidence:** HMDA coverage confirmed based on 12 CFR 1003.2(f) dwelling definition, principal residence occupancy certification, and home purchase loan purpose. HPML coverage confirmed based on 12 CFR 1026.35(a)(1) and principal dwelling determination. No coverage memorandum present in any listed supporting document.

**Required Remediation:** Prepare and file a brief HMDA and HPML coverage determination memorandum in the loan file. The memorandum should cite: 12 CFR 1003.2(f) (dwelling definition including agricultural property), the principal residence designation supported by the occupancy certification, the home purchase loan purpose, and the 12 CFR 1026.35(a)(1) HPML coverage basis for the mixed-use collateral. This document need not be lengthy but must be retained for FCA examination purposes.

**Responsible Party:** Compliance Officer; Originating Loan Officer

**Priority:** Advisory

**Supporting Agent(s):** HMDA Compliance Agent, HPML Compliance Agent

---

### Finding 11: HVCRE File Documentation — Affirmative Non-Applicability Notation Absent

**Description:** The HVCRE evaluation confirmed this loan is Non-HVCRE with high confidence. No ADC activity is present or contemplated; the collateral is existing, improved agricultural real property. However, the capital contribution fields in the file are null without an affirmative notation explaining that ADC activity was evaluated and found absent, and no standardized HVCRE determination form or checklist is present.

**Impact:** Under FCA examination standards, blank fields may be interpreted as omissions rather than intentional non-applicability determinations. An affirmative notation creates a reproducible, examination-defensible record that the institution performed the required analysis. This is a documentation improvement, not a substantive compliance deficiency.

**Evidence:** HVCRE classification: Non-HVCRE, High confidence. adc_activity = false. construction_status = Not applicable. project_type = Existing farm. Capital contribution fields null. No HVCRE determination checklist referenced.

**Required Remediation:** (1) Add an affirmative notation to the credit approval memorandum or a standalone HVCRE determination form confirming that ADC activity was evaluated and found absent and that borrower capital contribution requirements are therefore not applicable. (2) Institutionally, implement a standardized HVCRE determination checklist for all agricultural real estate and commercial real estate loans at origination, capturing each FCA HVCRE Decision Tree step and the resulting classification.

**Responsible Party:** Credit Officer; Compliance Officer

**Priority:** Advisory

**Supporting Agent(s):** HVCRE Compliance Agent, Compliance Auditor

---

## Findings Requiring Monitoring

**YBS Age Threshold Proximity —
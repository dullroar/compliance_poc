# Farm Credit System — Conceptual Primer (v2)

## Purpose

This document provides **foundational context for understanding Farm Credit terminology**.

It is designed for:

- New employees or interns
- Analysts working across institutions
- Large Language Models (LLMs) requiring domain grounding

It prioritizes:

- Conceptual clarity over completeness
- Disambiguation of Farm Credit–specific usage
- Separation from system/tool-specific implementation details

## What is the Farm Credit System (FCS)?

The **Farm Credit System (FCS)** is a **nationwide network of borrower-owned, cooperative lending institutions** that provide credit and financial services to:

- Farmers and ranchers
- Agricultural cooperatives
- Agribusinesses
- Rural residents and communities

### Key structural characteristics

- **Cooperative ownership**  
  Borrowers are also owners (through required equity/stock participation)

- **Non-depository institutions**  
  FCS institutions **do not take deposits** (unlike commercial banks)

- **Capital markets funding model**  
  Funds are raised through **systemwide debt securities** issued via the Funding Corporation

- **Federal charter and oversight**  
  Governed by the **Farm Credit Act** and regulated by the **Farm Credit Administration (FCA)**

## Core Entity Model

At a high level:

    Capital Markets → Funding Corporation → Farm Credit Banks → Associations → Borrowers

### 1. Farm Credit Banks (FCBs / ACBs)

- Provide **wholesale funding** to associations
- Example: AgriBank, CoBank

### 2. Associations (ACA, PCA, FLCA)

- Provide **direct lending** to borrowers
- Customer-facing institutions

Key types:

- **ACA** – combined lending authority
- **PCA** – short/intermediate-term (now usually part of ACA)
- **FLCA** – long-term real estate lending

### 3. Borrowers

- Farmers, ranchers, agribusinesses, rural homeowners
- Also **member-owners**

## Loan Lifecycle (Simplified)

    Application → Underwriting → Approval → Funding → Servicing → Risk Monitoring → Resolution

### Key concepts

- **Collateral** – assets securing the loan
- **Repayment capacity** – ability to generate cash flow
- **Risk classification (UCS)** – standardized credit risk categories
- **Ongoing servicing** – monitoring financial condition and performance

## Risk & Capital Model

FCS institutions manage risk using:

### Credit Risk

- Probability of Default (PD)
- Loss Given Default (LGD)
- Uniform Classification System (UCS)

### Capital Adequacy

- Permanent Capital
- Regulatory capital ratios

### Accounting Frameworks

- GAAP + Regulatory overlays
- CECL (expected credit losses)

## Agricultural Context Layer

Unlike traditional banking, FCS lending is deeply tied to:

- Crop production cycles
- Commodity price volatility
- Weather risk
- Crop insurance programs

Examples:

- APH (Actual Production History)
- MPCI (Crop Insurance)
- Revenue-based insurance products

## Important Disambiguation Patterns

The following are places where "Farm Credit-ism" often trip up newcomers.

### 1. Common words with specialized meaning

| Term | Farm Credit Meaning |
|------|--------------------|
| Bank | Typically refers to the District Bank (e.g., AgriBank). The "wholesale" side. Contrast to "Commercial bank." |
| Association | Farm Credit lending cooperative. The "retail" side. |
| Stock | Required borrower equity, not publicly traded shares |

### 2. Acronyms with multiple meanings

Disambiguation depends on context:

| Acronym | Possible meanings |
|--------|-----------------|
| LO | Loan Officer / Loan Origination |
| NDA | Non-Disclosure Agreement / Non-Disturbance Agreement |
| CMO | Collateralized Mortgage Obligation / Commercial Mortgage Obligation |

**Note:** This is **not** an exhaustive list. If you are confused because it seems a term or acronym is being used in a strange way, look to see if there is a possible other meaning.

## What This Glossary Does (and Does Not Do)

### Included

- Core Farm Credit concepts
- Agricultural finance terminology
- Regulatory and risk terms
- Frequently used acronyms

### Excluded (or minimized)

- Internal system implementation details
- Vendor-specific tooling
- Step-by-step operational procedures
- General legal, financial or real estate terms

## How to Use This Document

- First-time readers:

  - Read this primer fully before referencing the glossary

- Experienced users:

  - Use glossary for lookup and disambiguation

- LLM usage:

  - Use this primer as **context injection layer**
  - Use tagged glossary entries selectively

## Concepts and Vocabulary

The following are terms, abbreviations and acronyms that are used in specific ways within lending in general and Farm Credit in particular.

### Acceptable

A UCS asset classification indicating that the loan or asset is of the highest quality, with no identified weaknesses and a high probability of full repayment according to contractual terms.

**See Also**

- Uniform Classification System (UCS)

### Acceptable or Accrual Earnings (ACC)

The earnings or income that are recognized on an accrual basis rather than a cash basis. This approach aligns with generally accepted accounting principles (GAAP) and is commonly used to assess the financial performance and stability of agricultural businesses.

**See Also**

- Generally Accepted Accounting Principles (GAAP)

### Acceptable Percent

UCS Credit Classification. Percentage of loan classified as Acceptable. Note that Fiserv DNA does not allow split credit classifications, so will always be 0% or 100% for DNA-based associations.

**See Also**

- Fiserv DNA Loan Accounting System (DNA)
- Uniform Classification System (UCS)

### Accredited Rural Appraiser (ARA)

A professional designation awarded by the American Society of Farm Managers and Rural Appraisers (ASFMRA) to individuals who have demonstrated competency in the appraisal of rural and agricultural properties.

**See Also**

- American Society of Farm Managers and Rural Appraisers (ASFMRA)

### Accrual Net Income

The excess of all revenues over all expenses calculated on an accrual basis, which recognizes revenue when earned and expenses when they are incurred, regardless of the timing of the cash receipt or payment.

### Accrued Interest

Unpaid interest accumulated on a debt.

### Accrued Interest Receivable (AIR)

The Accrued Interest Receivable represents fees and finance charges that have been accrued on receivables that the institution has securitized and sold to other investors.

**See Also**

- Accrued Interest

### Accruing Loan Volume

Total principal amount plus accrued interest of loans, notes, sale contracts, leases outstanding, and loan participations that are accruing interest.

### Acquired Agricultural Real Estate or Property

Agricultural real estate acquired by an institution as a result of a loan foreclosure or a voluntary conveyance by a borrower who, as determined by the institution, does not have the financial resources to avoid foreclosure.

- Also referred to as: Acquired Property

### Acreage Report (AR) [CROP INSURANCE]

Form used by insured and agent to report all acreage planted of the insured crops on the policy. It is combined with the approved APH form.

**See Also**

- Actual Production History (APH)

### Acreage Reporting Date (ARD) [CROP INSURANCE]

The date by which insured growers are required to submit acreage reports. Acreage reports must be filed not later than the acreage reporting date contained in the Special Provisions for the county for the insured crop or as provided in the basic policy provisions.

### Actual Production History (APH) [CROP INSURANCE]

APH is yield insurance covering yield losses from a farm or unit. APH is the longest running crop insurance, previously known as Multiple Peril Crop Insurance. APH makes payments when actual yield is below a yield guarantee. The APH establishes an average yield for the insured crop based on the grower's previous year's experience. The APH yield is used to set the insured grower's guarantee and determines the premium rate.

**See Also**

- Multiple Peril Crop Insurance (MPCI)

### Add-on Loan

A long-term mortgage/deed of trust loan that is subject to a prior mortgage/deed of trust to the same legal entity that will remain of record.

### Additional Advance (AA)

An additional loan disbursement or extra borrowing that a borrower can request beyond the original loan amount. This term is typically used in the context of operating loans or lines of credit, where a borrower may need additional funds after the initial loan has been extended. The additional funds are provided to meet increased needs or expenses, such as for seasonal fluctuations in the business or unexpected costs.

### Additional Security

Also called "secondary security." Additional security is supplementary collateral to the primary security taken in connection with the loan. It normally is first-lien security, but may be junior lien security in specific situations.

### Adequately Secured

The condition of a loan being secured by collateral in the form of properly perfected liens on, or pledges of, real or personal property (including securities) that have a net realizable value sufficient to discharge the contractual indebtedness of the borrower (including accrued but uncollected interest) or secured by the guarantee of a financially responsible third party.

### Adjustable Rate Loan

A loan having an interest rate that may change over the term of the loan.

### Adjustable Rate Mortgage (ARM)

A mortgage in which the interest rate is adjusted periodically based on a pre selected index. Also sometimes known as the renegotiable rate mortgage, the variable rate mortgage or the Canadian rollover mortgage.

### Adjusted and Verified Balance Sheet (Verified Balance Sheet)

A loan officer-evaluated and confirmed or adjusted statement of a borrower's asset values and liabilities. This process involves verification of the existence and quantity of assets and verification of types and amounts of liabilities owed to other creditors/ suppliers.

### Adjusted Gross Revenue (AGR)

The Adjusted Gross Revenue (AGR) product provides protection against low revenue due to unavoidable natural disasters and market fluctuations that occur during the insurance year.

### Adverse Credit Decision

A lender's decision not to make a loan to an applicant, approve a loan in an amount less than the applicant requested, or deny an application for restructuring.

### Adverse Possession

A method of acquiring ownership to property by use or possession. Requirements for acquiring ownership by adverse possession are set forth in each state's statutes.

### Adversely Classified Assets

Loans, notes, sale contracts, and leases classified as substandard, doubtful, or loss.

### AgCountry FCS
[www.agcountry.com](https://www.agcountry.com/)

A member-owned financial cooperative that provides a range of financial services to farmers, ranchers, and rural businesses. AgCountry FCS primarily operates in Minnesota, North Dakota, and Wisconsin. It is part of the AgriBank District.

**See Also**

- Agricultural Credit Association (ACA)

### Agency Bond (ABND)

A debt security issued by a U.S. government-sponsored enterprise or federal agency (such as Fannie Mae or the Federal Farm Credit Banks Funding Corporation) used to raise capital for specific lending or public purposes.

**See Also**

- Federal Farm Credit Banks Funding Corporation
- Fannie Mae (FNMA)

### AgHeritage FCS
[www.agheritagefcs.com](https://www.agheritagefcs.com/)

A financial cooperative that provides lending, insurance, and financial services to farmers, ranchers, and agribusinesses. AgHeritage FCS operates primarily in Arkansas. It is part of the AgriBank District.

**See Also**

- Agricultural Credit Association (ACA)

### Agri-Access

Agri-Access is a specialized agricultural lending program between Compeer Financial and partnering OFIs and supported by AgriBank funding.

**See Also**

- Compeer Financial

### AgriBank, FCB
[www.agribank.com](https://www.agribank.com/)

AgriBank is part of the customer-owned, nationwide Farm Credit System. Under Farm Credit's cooperative structure, AgriBank is primarily owned by local Farm Credit Associations, which provide financial products and services to rural communities and agriculture. AgriBank obtains funds and provides funding and financial solutions to our Association-owners. We call the territory AgriBank and our Association-owners serve the AgriBank District. In the District the unqualifed term "the bank" typically refers to AgriBank.

**See Also**

- Farm Credit Bank (FCB)

### AgriBank District Farm Credit Council (ADFCC)

A council representing the Farm Credit associations within the AgriBank District that serves as a forum for coordinating positions on legislative, regulatory, and policy matters affecting the District.

### Agribusiness

Any business that supports producers: implements, feed and seeds, fertilizer companies, etc.

### Agriconsumer

A market segment characterized by off-farm earnings and substantial demand for small loans. The total credit needs of borrowers in this segment generally are limited, so their off-farm income provides them the capacity to service debt as consumers.

### Agricultural Credit Association (ACA)

An ACA results from the merger of a Federal Land Bank Association or an FLCA and a PCA, and has the combined authority of the two institutions. An ACA borrows funds from an FCB or ACB to provide short-, intermediate-, and long term credit to farmers, ranchers, and producers and harvesters of aquatic products. It also makes loans to these borrowers for certain processing and marketing activities, to rural residents for housing, and to certain farm-related businesses.

**See Also**

- Federal Land Bank Association
- Federal Land Bank
- Federal Land Credit Association (FLCA)
- Agricultural Credit Bank (ACB)
- Farm Credit Bank (FCB)
- Production Credit Association (PCA)

### Agricultural Credit Bank (ACB)

An ACB results from the merger of an FCB and a Bank for Cooperatives, and has the combined authorities of those two institutions. An ACB is also authorized to finance U.S. agricultural exports and provide international banking services for farmer-owned cooperatives. CoBank is the only ACB in the FCS.

**See Also**

- Bank for Cooperatives (BC)
- Farm Credit Bank (FCB)

### Agriculture & Rural Community Bond Program (ARC)

A bond program authorized under the Farm Credit Act that allows FCS institutions to issue bonds to finance agriculture and rural community development projects. Also known as "ARC bonds."

**Disambiguation**

- Agriculture & Rural Community Bond Program — Farm Credit Act bond program
- Agriculture Risk Coverage (FSA program) — USDA Farm Service Agency revenue program

**See Also**

- Farm Credit Act

### Agriculture Risk Coverage (FSA program) (ARC)

A USDA Farm Service Agency program that provides revenue-based financial protection to producers when crop revenues fall below a benchmark level, calculated at either the county or individual farm level.

**Disambiguation**

- Agriculture & Rural Community Bond Program — Farm Credit Act bond program
- Agriculture Risk Coverage (FSA program) — USDA Farm Service Agency revenue program

**See Also**

- United States Department of Agriculture (USDA)

### AgSouth Farm Credit
[www.agsouthfc.com](https://www.agsouthfc.com/)

A financial cooperative that provides lending, insurance, and financial services to farmers, ranchers, and agribusinesses across the southeastern United States.

### Alabama AgCredit
[www.alabamaagcredit.com](https://www.alabamaagcredit.com/)

A financial cooperative that provides lending, insurance, and financial services to farmers, ranchers, and agribusinesses throughout Alabama.

### Aligned System (Integrator)

An agribusiness generally involved in producing farm products through producers in a contractual relationship and providing financing as part of its product bundle. This type of agribusiness operates a standardized production system and requires a standardized financing package to support it. The business has a direct financial interest in the producer's success.

### Allocated Insurances Reserves Account (AIRA)

An Allocated Insurance Reserves Account (AIRA) is a specialized financial liability account used by an insurance entity—frequently a captive insurance company or a self-insured organization—to set aside funds specifically earmarked for anticipated future claims and their associated settlement costs. Unlike general reserves, which may cover a broad range of potential liabilities, an "allocated" account is strictly tied to specific identified risks, policy periods, or individual claims.

### Allowance for Loan Losses

An estimate of the potential losses in an institution's loan portfolio at a point in time in accordance with Generally Accepted Accounting Principles (GAAP). In June 2016, the Financial Accounting Standards Board (FASB) issued a new accounting standard, Current Expected Credit Losses (CECL) methodology for estimating allowances for credit losses. The CECL methodology is based on expected losses rather than incurred losses. This new accounting standard allows a financial institution to leverage its current internal credit risk systems as a framework for estimating expected credit losses.

**See Also**

- Generally Accepted Accounting Principles (GAAP)
- Financial Accounting Standards Board (FASB)
- Current Expected Credit Losses (CECL)
- Financial Accounting Standards (FAS)

### American Bankers Association (ABA)
[www.aba.com](https://www.aba.com/)

A national trade and professional organization representing banks of all sizes across the United States, providing advocacy, education, and resources on banking policy and regulation.

### American Land Title Association (ALTA)
[www.alta.org](https://www.alta.org/)

A national association of title insurance companies, abstractors, and attorneys specializing in real property law. ALTA speaks for the title insurance and abstracting industry and establishes standard title policies and procedures. ALTA develops standard forms and endorsements used nationwide in real estate transactions, including the widely used ALTA/NSPS Land Title Survey standards.

### American Society of Farm Managers and Rural Appraisers (ASFMRA)
[www.asfmra.org](https://www.asfmra.org/)

A professional organization that provides education, accreditation, and advocacy for farm managers, rural appraisers, and agricultural consultants across the United States.

### Amortized Rate

The original interest rate for amortized payment type loans. This rate is used to calculate the principal portion of amortized payments. Also referred to as "Base" rate.

- On annual payment types, the base rate is used to calculate the principal portion of payments

### Annual Debt Service

The total annual demands on a borrower's capital debt repayment capacity (repayment of principal and interest on capital loans, capital asset replacement, and working capital deficiency coverage).

### Annual Percentage Rate (APR)

Actual cost of monies borrowed on an annual basis, including cost of interest and any other finance charges. This term is used for Truth-in-Lending disclosure purposes.

### Applicant

Any person who requests or who has received an extension of credit from a creditor and includes any person who is or may become contractually liable regarding an extension of credit.

### Application (Loan)

A complete oral or written request for an extension of credit made in accordance with a lender's procedures for the type of credit requested. An application is complete when the lender receives all of the information normally obtained and used in evaluating applications for credit. This information may include credit reports, supporting information for the credit requested, and reports by governmental agencies or other persons necessary to guarantee, insure, or provide security for the credit or collateral.

### Application for Restructuring

A written request from a borrower to restructure a distressed loan. The request must be submitted on the appropriate forms prescribed by the lender and accompanied by sufficient financial information and repayment projections, where appropriate, as required by the lender to support a sound credit decision.

### Appraisal Report

Any written or oral communication of an appraisal; the document that is transmitted to the client upon completion of an appraisal assignment. Document format may be form or narrative in nature.

### Appraised Value (AV)

The reasonably supported value as stated and precisely defined in an appraisal. Most typically, this is market value but can be modified by sale conditions such as in a liquidation value or a salvage value. Use of this term without a modifier (market, liquidation, or salvage) is potentially misleading and should be avoided.

### Approval Date

Date the loan application was approved. Important for retail compliance.

### Appurtenance

Anything so annexed to land or used with it that it passes with conveyance of the land.

### Asset Backed Securities (ABS)

Financial securities collateralized by a pool of underlying assets such as loans, leases, or receivables, which generate cash flows that are passed through to investors.

### Asset Pool Detail

Groups of loans sold to AgriBank through Asset Pool Programs. AgriBank creates these programs where the associations sell a percentage of the loan to AgriBank. It assists with return on assets and capital optimization.

### Asset/Liability Committee (ALCO)

Specialized committees that focus on managing an institution's assets (such as loans and investments) and liabilities (such as deposits and borrowings) to ensure financial stability and profitability. These committees play a critical role in the risk management and financial strategy of Farm Credit institutions, including credit bureaus or cooperatives, by overseeing the balance between the institution's assets and liabilities.

### Association

(Individually or Collectively) Federal land bank associations, Federal land credit associations, production credit associations and agricultural credit associations. The cooperative institutions that lend money to farmers, ranchers, and other eligible borrowers. The Farm Credit Administration (FCA) regulates and supervises the association and other service entities.

**See Also**

- Agricultural Credit Association (ACA)
- Farm Credit Administration (FCA)

### Association Investments

The financial assets and investment strategies used by local Farm Credit associations to manage liquidity, generate income, and support their lending operations. These investments help ensure financial stability, capital adequacy, and compliance with regulatory requirements.

### Association Loans

The loans AgriBank has information on made by associations to farmers, ranchers, and other eligible borrowers. This also includes any leases from the Associations which are financing arrangements where a borrower obtains the use of equipment, facilities, or land from a lender for a specified period in exchange for periodic payments.

### Attribute

In credit scoring, an item of information about, and provided by, an applicant in the application process, e.g., specific responses to age, time at address.

### Audited, Unqualified Statements

Financial statements that have been audited by a professional auditor who renders an unqualified opinion stating that the statements present fairly, in all material respects, the financial position, results of operations, and cash flows of the subject party in conformity with generally accepted accounting principles.

### Automated Clearing House (ACH)

ACH transactions are payment instructions to either debit or credit a deposit account. An ACH transaction is a batch-processed, value-dated electronic funds transfer between originating and receiving financial institutions. ACH payments can either be credits, originated by the accountholder sending funds (payer), or debits, originated by the accountholder receiving funds (payee).

### Automatic Territorial Concurrence (ATC)

A provision under Farm Credit regulations that allows a Farm Credit institution to make loans in another institution's territory under certain defined conditions without obtaining explicit approval, typically when a borrower's operations span multiple territories.

### Available Commitment

The amount not including stock, used to show the actual amount that a borrower could receive in cash.

### Average Daily Balance (ADB)

The average of a loan or account balance calculated by summing the balance for each day in a period and dividing by the total number of days in that period.

### Average Daily Balance Year-to-Date (ADB YTD)

The Average Daily Balance calculated by aggregating the Current Principal Balance each day and dividing it at the end of the period by the number of days year-to-date. The number of days year-to-date is determined by the reporting entity. FCB/FLCA: 30/360. PCA: Actual/365. The Current Principal Balance is not net of charge-offs on nonaccrual loans. The Principal Balance is reduced by balances in Funds Held, but is not reduced by balances in Farm Cash Management investment.

**See Also**

- Average Daily Balance (ADB)
- Farm Cash Management
- Current Principal
- Funds Held
- Federal Land Credit Association (FLCA)
- Farm Credit Bank (FCB)
- Production Credit Association (PCA)

### Average Gross Income (AGI)

The average total of value of farm production plus net non-farm income plus salary and wages over the earnings period analyzed.

### Balance Sheet (BS)

A report which provides a description of assets, liabilities, and capital on a specific date.

### Balloon Indicator

Indicator which allows users to identify amortized loans with balloon payments. This one-position alphanumeric field defaults to the value of a space. Associations can define a set of values to be used to denote various loan actions in process for loans that contain balloon amounts.

### Balloon Payment

Final payment on a partially amortized loan. Final payment is larger than the preceding principal payments.

### Bank

Farm Credit Banks, agricultural credit banks and bank for cooperatives.

### Bank for Cooperatives (BC)

A BC provides lending and other financial services to farmer-owned cooperatives, rural utilities (electric and telephone), and rural sewer and water systems. It is also authorized to finance U.S. agricultural exports and provide international banking services for farmer-owned cooperatives. The last remaining BC in the FCS, the St. Paul Bank for Cooperatives, merged with CoBank on July 1, 1999.

### Bank Management Information System (BMIS)

BMIS is a loan accounting system that tracks customers and the loans they have made with Farm Credit. It's a mainframe computer system that runs in St. Paul, MN and is managed by AgriBank FCB. Now branded Cornerstone.

**See Also**

- Core
- Cornerstone

### Bargain Purchase Option

An option given at lease inception allowing the lessee to purchase the leased asset at the end of the lease term at a price that is fixed sufficiently below the expected market value, so that at inception of the lease, purchase appears to be reasonably assured.

### Basel Capital Accord (banking supervision accords, Basel I, II, and III; issued by the Basel (BASEL)

A set of international banking supervision standards developed by the Basel Committee on Banking Supervision that establish minimum capital requirements and risk management frameworks for financial institutions; Basel III is the most current iteration.

### Basic Membership and Lending Relationship Agreement (BMLRA)

A foundational agreement between AgriBank and its affiliated associations that defines the terms, obligations, and governance structure of their lending and membership relationship within the Farm Credit System.

### Basis Point(s) (BP/BPS)

(100 points = 1%) A unit of measurement equal to one one-hundredth of a percentage point (0.01%), commonly used to express changes in interest rates, yields, and other financial percentages.

### Benchmark

Indexing system for land values that updates estimated market values. Once a year the Associations provide the "Benchmark Farms" where the appraisals are updated. The data is submitted to the system and certain pieces of collateral get tied to that benchmark.

### Bona Fide Farmer or Rancher

A person who owns agricultural land or is engaged in the production of agricultural products and livestock, including aquatic products under controlled conditions.

### Bona Fide Purchaser

A purchaser in good faith and without knowledge of prior unrecorded deeds or mortgages affecting the purchased property.

### Book Value (BV)

A company's common stock equity as it appears on a balance sheet, equal to total assets minus liabilities, preferred stock, and intangible assets such as goodwill.

### Booking (Loan)

In accounting, when a loan is processed and finalized, it is included in the books, or the financial statements of that organization. Booking the Loan means the loan is processed and "on the books".

### Borrower-Signed Income Statement

A statement of a borrower's income and expenses for a specified operating period, signed by the borrower to certify that the information is true and correct. An income statement may be in a lender-provided format, or IRS records or acceptable accounting records.

### Borrowers

Individual, business, or entity that seeks and receives financial assistance or loans from the Farm Credit System institution, to finance agricultural operations.

### Borrowing Entity

The individual(s), partnership, joint venture, trust, corporation, or other business entity, or any combination thereof, that is primarily obligated on the loan instrument.

### Branch

A branch is a physical location or office of an organization that provides services to customers or members. It also can mean a virtual business line such as Capital Markets or the Risk Asset Unit (RAU). It typically operates under the organization's main structure but serves a specific geographic area or community or business segment. Branches are identified in the District DB and elsewhere as a three-digit number. Branch assignment also controls the cost center for a loan.

**See Also**

- Risk Asset Unit (RAU)

### Branch Performance Differential (BPD)

A performance-based metric used to evaluate the financial performance of individual branches or offices within a Farm Credit institution. The BPD is designed to assess how well each branch is performing in terms of meeting its financial goals, loan production, customer service, and overall profitability compared to other branches within the same institution.

### Bridge Loans

Loans for which additional collateral is offered either in lieu of or in addition to a down payment on the construction loan. Most typically used when an applicant has an existing home that they plan to sell to realize equity to build the new home.

### Broker

An individual in the business of assisting in arranging funding or negotiating contracts for a client but who does not loan the money himself. Brokers usually charge a fee or receive a commission for their services.

### Builder's Risk Insurance

Insurance policy that protects the borrower and lender until completion of the required construction. Builder's risk policies should cover theft of materials from the building site, contractor's personal property (tools, etc.), theft on new construction while the dwelling is under construction, fire, vandalism and malicious intent. Some insurance agencies require a home owner's policy with a builder's risk insurance rider. Others may require a builder's risk policy which should roll over into a property/casualty policy when construction is completed. Coverage options are dependent upon whether there is a licensed contractor involved or a do-it-yourselfer. Policy names the lender as the mortgagee.

### Building Officials and Code Administrators (BOCA)

A former building standards organization founded in 1915 that merged into the International Code Council (ICC) in 2003. BOCA codes have been superseded by ICC International Building Codes (IBC). References to BOCA standards in older loan documents or appraisal reports may be encountered when reviewing legacy collateral.

### Bullet Bond (BB)

A bond that pays periodic interest but returns the entire principal in a single lump sum at maturity, with no scheduled amortization of principal prior to the maturity date.

### Business Loan

A loan or other extension of credit to any corporation, general or limited partnership, business trust, joint venture, sole proprietorship, or other business entity (including entities and individuals engaged in farming enterprises).

### Callable Bond (CBO)

(Issuer can call at par.) A bond that gives the issuer the right to redeem the bond at its par (face) value before its scheduled maturity date, typically exercised when interest rates have declined and the issuer can refinance at a lower cost.

### Capital

Shareholder investment and retained earnings.

### Capital Asset Replacement (CAR)

The amount of annual allowance necessary for machinery/facility replacement, less annual principal payments on loans financing depreciable assets (already included in total demands on CDRC).

### Capital Budget

The borrower's projected capital expenditure plans for the business cycle period. In some cases the borrower and credit staff may want to project more than one year.

### Capital Debt Repayment Capacity

Measurement of a borrower's ability to repay capital (intermediate and long-term) debt based on analysis of the operation's profitability. This analysis has three basic components: - CDRC. Net income from operations plus net non-farm income, depreciation and interest on capital debt, less family living, income and self-employment taxes. - CDRC Margin. CDRC minus total demands on CDRC (repayment of principal and interest on capital loans, capital asset replacement, and working capital deficiency coverage). - CDRC Percentage. CDRC divided by total demands on CDRC. Pro forma CDRC analysis must be reconciled with earnings performance over at least the past three operating years, which serve as the base for historic CDRC analysis.

**See Also**

- Pro forma

### Capital Debt Repayment Capacity Margin / Average Gross Income (CDRC Margin/AGI)

Capital Debt Repayment Capacity Margin divided by Average Gross Income. This relative percentage is a guideline indicating the adequacy of repayment capacity compared to the size of the business.

**See Also**

- Capital Debt Repayment Capacity
- Average Gross Income (AGI)

### Capital Debt Repayment Capacity Percent (CDRC Percent/%)

Capital Debt Repayment Capacity divided by total demands on CDRC. This relative percentage demonstrates the borrower's ability to generate sustainable earnings adequate to service debt on a continuing basis, and is the core underwriting standard.

**See Also**

- Capital Debt Repayment Capacity

### Capital Gain/Loss

The capital gain or loss from the sale of capital assets

### Capital, Assets, Management, Earnings, Liquidity [Sensitivity] (CAMEL[S])

A supervisory rating system used by U.S. financial regulators to assess the overall condition of financial institutions across six components: Capital adequacy, Asset quality, Management capability, Earnings, Liquidity, and Sensitivity to market risk; ratings range from 1 (best) to 5 (worst).

### Cash Rent (CR)

Acreage rented for cash is considered a cash lease. A lease containing provisions for either a minimum payment or a crop share will be considered a cash lease.

### Catastrophic Risk Protection (CAT)

Catastrophic Risk Protection (CAT) is an endorsement to the MPCI Policy that provides 50% Coverage Level and a 55% Price Election.

**See Also**

- Multiple Peril Crop Insurance (MPCI)

### Certificate Number

For Participation Sold records, this field contains the investor assigned loan number identifying the loan in the investor's system with which the participation is associated. For Participation Bought records, this field contains the Participation Sold assigned loan number. This field is used to link the bought loan to the sold loan.

### Charge-off

That portion of a loan, sale contract, interest, accounts receivable, or judgment deemed a loss and removed from the asset account with a concurrent reduction in the reserve established for loan losses.

### Chattels

Any article of movable or immovable property, except real estate and items connected with real property.

### Chief Credit Officer (CCO)

A senior executive responsible for overseeing the credit risk management and credit operations within an organization, particularly in financial institutions such as banks, credit unions, and the Farm Credit System. In the Farm Credit System, the CCO plays a crucial role in managing the risks associated with the institution's lending activities, ensuring that credit policies are adhered to, and maintaining the overall financial health of the organization.

### Classified Assets

Loans, notes, sale contracts, and leases designated acceptable, other assets especially mentioned (OAEM), substandard, doubtful or loss, under the Uniform Classification System; sometimes use d to refer only to adversely classified assets.

**See Also**

- Uniform Classification System (UCS)
- Other Assets Especially Mentioned (asset classification) (OAEM)

### Clean Air Act (CAA)
[www.epa.gov/laws-regulations/summary-clean-air-act](https://www.epa.gov/laws-regulations/summary-clean-air-act)

A law originally enacted by Congress in 1963 to place limits on air pollution sources. It establishes air quality and emission limitations and standards for noise abatement.

### Clean Water Act (CWA)
[www.epa.gov/laws-regulations/summary-clean-water-act](https://www.epa.gov/laws-regulations/summary-clean-water-act)

A U.S. federal environmental law that establishes permitting and regulatory requirements to protect surface waters by controlling pollutant discharges. In AgriBank business processes, the Clean Water Act is relevant to credit, collateral, and environmental risk assessment, as certain agricultural and rural facilities (such as waste holding pits, ponds, manure storage lagoons, and similar structures) may be subject to permitting, compliance obligations, or environmental liabilities that can affect loan approval, collateral value, and ongoing risk monitoring.

### Client Exposure

Total amount of potential risk; Total amount of potential risk

### Co-applicant

A second or joint applicant person who applies for a loan or credit jointly with the primary applicant. Both applicants share equal responsibility for repaying the debt and may also share ownership of the asset being financed.

**See Also**

- Co-maker
- Co-signer

### Co-maker

A party who signs an instrument on its face and thereby becomes, with the other signers, primarily liable, either jointly or severally, for its payment. For nonlegal use, a comaker is a joint applicant.

- Also spelled: Comaker

**See Also**

- Co-applicant
- Co-signer

### Co-signer

Person who signs another person's promissory note and becomes liable for its payment. For nonlegal use, a co-signer differs from a co-maker in that the co-signer executes the instrument evidencing indebtedness but not the application.

- Also spelled: Cosigner

**See Also**

- Co-applicant
- Co-maker

### Code of Federal Regulations (CFR)
[www.ecfr.gov](https://www.ecfr.gov/)

The Code of Federal Regulations (CFR) is the codification of the general and permanent rules published in the Federal Register by the executive departments and agencies of the Federal Government. It is divided into 50 titles that represent broad areas subject to Federal regulation.

### Collateral Analysis

Analysis involving three key areas collateral valuation, net realizable value, and security (lien) position, encompassing the following: - Real Estate Valuation; Chattel Valuation; Net Realizable Value. The net amount expected to be realized from the sale of an asset.

**See Also**

- Net Realizable Value
- Title Opinion
- Real Estate (RE)

### Collateral Value

Used generically, a reference to any definition of value; specifically, appraised value of property less prior liens.

### Collateralized Mortgage Obligation (CMO)

A type of mortgage-backed security that pools mortgage loans and divides them into tranches with different risk profiles, maturities, and payment priorities to appeal to different classes of investors.

**Disambiguation**

- Collateralized Mortgage Obligation — pool of residential mortgage loans
- Commercial Mortgage Obligation — pool of commercial real estate mortgages

**See Also**

- Commercial Mortgage Obligation (CMO)

### Commercial Bank

A financial institution that offers services like loans, deposits and overdrafts as they have a relationship with AgriBank. A non-Farm Credit System bank.

### Commercial Lending Participations

Large loans that that are purchased from Farm Credit Entities (Associations & Banks). AgriBank purchases a piece of the large loans, but part of this loan could also be sold to other associations or District Banks.

### Commercial Loan

A short- or intermediate-term loan originated and/or serviced by an ACA or PCA.

**See Also**

- Agricultural Credit Association (ACA)
- Production Credit Association (PCA)

### Commercial Mortgage Obligation (CMO)

A structured financial product backed by commercial real estate mortgages, divided into tranches with varying levels of risk and return to meet different investor needs.

**Disambiguation**

- Collateralized Mortgage Obligation — pool of residential mortgage loans
- Commercial Mortgage Obligation — pool of commercial real estate mortgages

**See Also**

- Collateralized Mortgage Obligation (CMO)

### Commitment

Any arrangement that legally obligates an institution to purchase loans or securities, to participate in loans or leases, to extend credit in the form of loans or leases, to pay the obligation of another, to provide overdraft, revolving credit or underwriting facilities, or to participate in similar transactions.

### Commitment Amount

The original commitment amount. This amount equal Note Amount.

### Commitment Number

A unique, system-generated number assigned to a commitment when it is entered.

### Commodity Credit Corporation (CCC)
[www.usda.gov/ccc](https://www.usda.gov/ccc)

The Commodity Credit Corporation (CCC) is a government-operated entity that provides financial services to carry forward public price support activities in certain agricultural commodities.

### Community Reinvestment Program (CRA)

The Community Reinvestment Act (CRA), enacted by the U.S. Congress in 1977, is a federal law designed to encourage commercial banks and savings associations to help meet the credit needs of the communities in which they do business, including low- and moderate-income (LMI) neighborhoods.

### Compeer Financial
[www.compeer.com](https://www.compeer.com/)

A member-owned cooperative that provides a wide range of financial services to farmers, ranchers, and rural communities. Compeer Financial operates primarily in Minnesota, Wisconsin, and Illinois. It is part of the AgriBank District.

**See Also**

- Agricultural Credit Association (ACA)

### Comprehensive Environmental Response Compensation and Liability Act (CERCLA)
[www.epa.gov/laws-regulations/summary-comprehensive-environmental-response-compensation-and-liability-act](https://www.epa.gov/laws-regulations/summary-comprehensive-environmental-response-compensation-and-liability-act)

A law enacted by Congress in 1980 and modified in 1986 by the Superfund Amendments and Reauthorization Act to: - Promote cleanup of hazardous waste sites by imposing strict, joint and several liability on potentially responsible parties; - Grant the Environmental Protection Agency (EPA) authority to compel responsible parties to clean up contaminated sites; - Establish a Superfund to pay for cleanup; and - Permit federal liens on properties subject to cleanup actions to compensate the Superfund for cleanup costs.

### Confirming Letters of Credit

A financial guarantee issued by a Farm Credit institution to ensure payment to a beneficiary when the original issuing bank's creditworthiness needs additional support. This is typically used in international and high-value domestic transactions where a seller requires an added layer of security. AgriBank does this internally for AgriBank, associations, and borrowers.

### Confirming/Standby Letters of Credit

AgriBank has established various lines of credit to accommodate both AgriBank confirmed and PNC Bank confirmed letters of credit determined by your need. Legal agreements are in place to accommodate the PNC Bank confirmations or AgriBank FCB.

**See Also**

- Farm Credit Bank (FCB)

### Constant Payment Rate (CPR)

A measure of the annualized rate at which a pool of loans is prepaid, expressed as a percentage of the outstanding principal balance; used in modeling prepayment risk on mortgage-backed and other asset-backed securities.

### Construction Agreement

The basic contract signed by the borrower, builder and lender establishing terms and conditions of the financing.

### Consumer Credit

Credit extended primarily for personal, family, or household purposes.

### Consumer Financial Protection Bureau (CFPB)
[www.consumerfinance.gov](https://www.consumerfinance.gov/)

An independent agency of the United States government responsible for consumer protection in the financial sector, established by the Dodd-Frank Wall Street Reform and Consumer Protection Act of 2010. CFPB jurisdiction includes banks, credit unions, securities firms, payday lenders, mortgage-servicing operations, foreclosure relief services, debt collectors, and other financial companies operating in the United States. The Bureau issues rules, supervises companies, and enforces federal consumer financial protection laws.

### Consumer Loan

Loan made primarily for a consumer purpose (i.e. family living expense, vehicles, personal needs, nonagricultural purpose).

### Contract for Deed (Land Contract)

An instrument for purchase of real estate over a specified amount of time. On full payment of the contract for deed, the buyer receives the deed for the property from the seller.

### Contract Producer

For purposes of credit analysis, those who produce commodities for an approved entity according to the terms of a contract that does not expose the producer to market risk.

### Contractual Interbank Performance Agreement (CIPA)

An agreement among Farm Credit System district banks that identifies asset quality standards (ratios) assisting in objectively measuring portfolio quality. The CIPA model also includes capital and earnings measures and considers interest rate sensitivity and liquidity deficiency. See Underwriting Guide 102, Exhibit A.

**See Also**

- Financial Institution Rating System (FIRS)
- Farm Credit Administration (FCA)

### Conversion

A change from one loan program or interest rate plan to another.

### Conveyance

Transfer of an interest in land from one party to another. This term is used generally for both deeds and mortgages/deeds of trust.

### Cooperative

Any association of farmers, ranchers, producers or harvesters of aquatic products, or any federation of such associations, or a combination of such associations and farmers, ranchers, or producers or harvesters of aquatic products that conducts business for the mutual benefit of its members has the power to: 1) Process, prepare for market, handle, or market farm or aquatic products; 2) Purchase, test, grade, process, distribute, or furnish farm or aquatic supplies; Furnish business and financially related services to its members.

### Core

In banking, a loan accounting system is called "the core." Fiserv DNA and Sunstream's Cornerstone are two examples of core, the former a commercial platform, the latter bespoke. Use "core" near loan accounting terms and ideas very precisely, and substitute "central" or similar synonyms for the normal English concept of "core."

**See Also**

- Cornerstone
- Fiserv DNA Loan Accounting System (DNA)
- Bank Management Information System (BMIS)

### Cornerstone

Legacy application used for loan accounting ("core") at AgriBank. The current branding of BMIS.

**See Also**

- Bank Management Information System (BMIS)
- Core

### Cornerstone Customer Correspondence Reports

Reports sent to our loan and investment customers to communicate information regarding their accounts, including billing (payment/payment reminder) notices, rate notices and statement of accounts. Data for these documents are extracted from the Cornerstone files and then merged with formatted templates to create the final document which is mailed to the customer and/or made available via an online banking or other web service option.

### Corporate Performance Differential (CPD)

A metric used to evaluate the overall financial and operational performance of an institution or corporation within the system. The CPD typically assesses how well an organization is performing against pre-established goals or benchmarks, with a focus on key financial indicators, risk management practices, operational efficiency, and overall effectiveness in achieving its strategic objectives.

### Cost Approach

A set of procedures in which an appraiser derives a value indication by estimating the current cost to reproduce or replace the existing structure, deducting for all accrued depreciation in the property, and adding the estimated land value.

### Cost Center

The four-digit Cost Center Code assigned to the account for General Ledger purposes. This number is used in the General Ledger interface process. For the PLANT ACAs this is based on the branch assigned to the loan.

**See Also**

- General Ledger (GL)

### Cost of Funds (COF)

A fixed wholesale rate assigned to a loan at booking.

### Country Home Mortgages (CHM)

Country Home Loans (CHM) are specialized financing products offered through Farm Credit institutions. These loans are specifically designed for rural residential properties, offering advantages over conventional mortgages for rural living.

### Country Living (CL) Loans

Loan program offered to qualified customers to purchase or construct housing. Also referred to as "Rural Home Loans" or "Residence Loans to Farmers".

**See Also**

- Rural Home (RH)

### Credit Analyst (CA)

A professional who evaluates the creditworthiness of individuals, businesses, or organizations applying for loans. In the Farm Credit System, credit analysts play a critical role in assessing the risk of lending to farmers, ranchers, and other rural businesses. Their goal is to ensure that loans are granted to financially sound borrowers who are capable of repaying their debts.

### Credit Bureau Score

The Credit Score (or FICO Score) provided by the Credit Bureau. This score is used in determining the credit score for the borrower. Contrast with Scorecard.

**See Also**

- Credit Bureau
- Credit Score
- Scorecard

### Credit Desk (CD)

Software that scores loans with Fair Isaac scorecards. It also contacts the credit bureau and pulls a credit report on an applicant.

### Credit Line Draft

Draft access to various loan types, with the ability to set up recurring ACH transactions using the MICR line on the draft. All transactions post to the client loan and statement. The system also handles all exception item processing and stop payments. The exception item processing system is online and integrates to Cornerstone associations as well as non-Cornerstone associations. Built into the system is a stop payment/watch list system.

**See Also**

- Automated Clearing House (ACH)

### Credit Report (CR)

A detailed record of an individual's or business's credit history, including past borrowing, repayment behavior, and current credit status. It is used by lenders, such as those in the Farm Credit System (FCS), to assess creditworthiness before approving loans.

### Credit Review Committee (CRC)

An internal committee within a Farm Credit institution responsible for independently reviewing loan decisions, credit quality, and compliance with underwriting standards, providing oversight separate from the originating loan officers.

**Disambiguation**

- Credit Review Committee — internal Farm Credit institution oversight committee
- Crop Revenue Coverage — county/farm-level revenue insurance plan

### Credit Score

For loans originated in an origination system environment, the score is from the origination system.

### Criticized Assets

Loans, notes, sale contracts, and leases classified OAEM, substandard, doubtful, or loss.

**See Also**

- Other Assets Especially Mentioned (asset classification) (OAEM)

### Crop Revenue Coverage (CRC)

A revenue plan of insurance that guarantees revenue per acre as opposed to MPCI that guarantees production per acre.

**Disambiguation**

- Credit Review Committee — internal Farm Credit institution oversight committee
- Crop Revenue Coverage — county/farm-level revenue insurance plan

**See Also**

- Multiple Peril Crop Insurance (MPCI)

### Cross Collateralize

Contractual language that allows lender to satisfy its interest from collateral of all loans with borrower.

### Cross Default

The condition permitted by contractual language that allows a default of one loan to create a default on all loans with the same borrower.

### Current (or Interim) Balance Sheet

A borrower-signed (and verified) and adjusted balance sheet reflecting the borrower's financial position within one year of a credit action. The need for current information is a function of differential analysis. It is based on the risk in the credit, familiarity with the borrower, and the quality of information available from the borrower. Some actions may require strictly up-to-date information. For others, information up to 12 months old may be sufficient. In addition, it may be preferable to analyze audited prior fiscal year-end statements, if available, than to accept more current, but less reliable, unaudited information.

### Current Assets (CA)

The assets that a business or organization expects to convert into cash or use up within one year or within the normal operating cycle of the business, whichever is longer. In the context of the Farm Credit System, current assets are important because they help assess the liquidity and financial health of the borrower. A balance sheet item which equals the sum of cash and cash equivalents, accounts receivable, inventory, marketable securities, prepaid expenses, and other assets that could be converted to cash in less than one year.

### Current Expected Credit Losses (CECL)

In June 2016, the Financial Accounting Standards Board (FASB) issued this new accounting standard, which introduces the current expected credit losses (CECL) methodology for estimating allowances for credit losses. The CECL methodology is based on expected losses rather than incurred losses. The new accounting standard allows a financial institution to leverage its current internal credit risk systems as a framework for estimating expected credit losses.

**See Also**

- Financial Accounting Standards Board (FASB)
- Financial Accounting Standards (FAS)

### Current Liabilities (CL)

A balance sheet item which equals the sum of all money owed by a company and due within one year. Also called payables or current debt.

### Current Payoff

The total amount currently required to pay the loan in full. The amount includes principal, interest, late charges and any other charges. The Funds Held Balance, Funds Held Interest, Tax/Insurance Escrow, and Tax/Insurance Interest Balances are included. Other Escrow and Other Escrow Interest aren't included in the Current Payoff. Current Payoff is reduced by the Protected Stock-Voting, Protected Stock-Nonvoting and Protected Certificates-Nonvoting balances, but isn't reduced by Risk Stock-Nonvoting, Risk Stock-Voting or Risk Certificates-Nonvoting balances. Retirement of these equity types requires Board approval.

**See Also**

- Other Escrow
- Funds Held

### Current Principal

Current Principal Balance. Current Principal includes the outstanding equity balances.

### Current Ratio

Current assets divided by current liabilities. Current ratio indicates the extent to which current assets, if liquidated, would cover current liabilities. Timing of a borrower's balance sheet can affect the ratio.

### Customer

From an AgriBank point of view, "customer" represents entities that have a relationship with AgriBank, including associations, commercial banks, other financial institutions (OFIs), borrowers, and vendors. From an association point of view, "customer" (or "client" or "member-owner") are the farmers, ranchers, agribusiness and Capital Market customers to whom loans, leases and financial services are provided.

- AgriBank member-owners are the associations
- Association member-owners are the actual loan, lease and financial services retail and Capital Markets customers

### Customer Attribution

Tool used to roll up attributed borrower relationships

### Customer Commitments

The total amount of credit or financial resources promised to a borrower, including both disbursed and undisbursed loan amounts. These commitments represent the financial obligations that an FCS institution has made to support agricultural producers, rural businesses, and other eligible borrowers.

### Customer Financials

The Customer Financials application lets authorized users add, view, and maintain customer financial information that has been associated with customer records. That customer financial information includes: Balance sheets Earning statements, and Debt servicing information. Sunstream provides a Customer Financials applications to ACAs in its District.

### Customer Information File (CIF)

Pronounced "sif." Main file for holding customer account data in Cornerstone. A "CIF number" is a ten-digit number used in Cornerstone and other systems, including the District DB, to identify a customer. It is assigned by the Sunstream Customer Number Generator to avoid collisions in the District.

**See Also**

- Number Generator
- Customer Number

### Customer Number

aka "CIF number." Ten-digit number used to uniquely identify customers across the AgriBank district.

**See Also**

- Customer Information File (CIF)

### Customer Probability of Default

The Customer Probability of Default is a rating from 00 to 14 assigned to a customer that reflects the level of risk associated with that customer's ability to repay all outstanding loans. Probability of Default ratings are used by management to gauge the quality of a loan portfolio. When a customer probability of default is entered, the Last Review Date is required. See Probability of Default for a list of valid combinations.

**See Also**

- Probability of Default (PD)

### Customer Service Representative (CSR)

Plays a critical role in assisting clients-primarily farmers, ranchers, and agribusinesses-by providing essential support and helping them navigate various services and products offered by the Farm Credit institution. CSRs are often the first point of contact for customers and serve as the face of the institution in day-to-day interactions.

### Cutoff Score

In credit scoring, the score below which applications are either automatically declined or are recommended to be declined. The score is set by the lender's data and objectives.

### Dairy Assignment

Assignment of dairy (milk) income by the borrower to the lender to reduce present indebtedness.

### Dairy Assignment Remittance Tracking (DART)

A system used to track and process the assignment of dairy milk income from borrowers to lenders, ensuring payments are accurately applied to outstanding loan balances.

### Date of Application

Date the application for the loan was received. Important for retail compliance.

### Debt Coverage Ratio

Generally, a measure of a company's ability to generate enough income in its operations to service its debt. Specifically in mortgage lending, a measure of a real estate property's ability to generate net income sufficient to repay the loan(s) it secures. DCR is calculated by dividing earnings capacity of the real estate collateral by annual debt service on a loan typical for the financing of similar type property. Additional considerations in determining loan amount include: - Type and expected life of the asset financed; - Repayment terms appropriate for the customer and asset financed; and - Customer loan structuring alternatives.

### Debts/System Bonds

The funding instruments issued by the Federal Farm Credit Banks Funding Corporation to raise capital for FCS institutions. These bonds and notes allow the FCS to secure low-cost funding, which is then used to provide loans to farmers, ranchers, and rural businesses.

**See Also**

- Federal Farm Credit Banks Funding Corporation

### Declining Balance Loan

A loan structure that provides for disbursements up to the note amount, but no additional disbursements after funds are drawn and repaid.

### Deferment

A loan servicing tool postponing principal payments until a future date.

### Delinquent Loans

For reporting purposes, loans in which all or any portion of a scheduled installment of principal or interest, including default interest, is due and unpaid for 30 days or more, or unpaid principal and interest is 30 days or more past maturity. Contractually due but unpaid amounts may be considered paid in full if no more than a combined total of $100 of contractually due principal and interest remains uncollected.

### Delinquent Payments

For reporting purposes, the unpaid portion of a scheduled installment of principal or interest that is 30 days or more past due, subject to the $100 tolerance limit identified for delinquent loans.

### Delinquent Volume

Total dollar volume of matured and unmatured principal plus unpaid interest on a delinquent loan.

### Department of Veterans Affairs (VA)
[www.va.gov](https://www.va.gov/)

An agency of the Federal government that guarantees residential mortgages made to eligible veterans of the military services. The guarantee protects the lender against loss and thus encourages lenders to make mortgages to veterans.

### Depository Financial Institution (DFI)

A bank, savings and loan association, savings bank, or credit union that is legally authorized to accept monetary deposits from individuals and businesses. These institutions are typically chartered at the state or federal level and their deposits are insured by a federal agency, such as the Federal Deposit Insurance Corporation (FDIC) or the National Credit Union Administration (NCUA).

**See Also**

- Federal Deposit Insurance Corporation (FDIC)

### Depreciation (DEPR)

A reasonable allowance for exhaustion, wear and tear, and obsolescence of equipment used in a trade or business. As a periodic item of expense, it allows the owner of the equipment to recover the cost of the equipment over its useful life. Depreciation deductions taken on the owner's tax return are sometimes referred to as "tax depreciation." Depreciation expenses listed in the owner's financial statements are sometimes referred to as "book depreciation."

### Depreciation Expense

Total amount of Depreciation Expenses

### Derivatives

Financial contracts used by FCS institutions to manage risk, particularly interest rate and credit risk. These instruments help stabilize funding costs, hedge against market fluctuations, and ensure financial stability for agricultural lending.

### Differential Analysis

A principle of administering individual loans based on the approach that the level of analysis performed is determined by loan size and the degree of risk present.

### Differential Interest Rates

Different rates of interest charged to individuals or classes of loans based on differences in risk, loan type or amount, servicing required, or a combination of these and other factors.

### Direct Lender

An institution that extends credit in the form of loans or leases to eligible borrowers in its own right and carries such loan or lease assets on its books.

### Disbursement

A transaction which establishes or increases the customer's indebtedness to the Association.

### Disclosures

This depends on the purpose of the funds which are loaned. An EIR is used for agricultural purposes and a TIL is used for consumer purposes.

**See Also**

- Truth-in-Lending (TIL)

### Discount Note Outstanding Reconciliation

This process reflects how AgriBank ensures that Discount Notes are balanced with the Funding Corp on a quarterly basis. The total PAR amount of Discount Notes to reconciled against the Treasury workstation.

**See Also**

- Funding Corp

### Distressed Loans

Loans that borrowers do not have the financial capacity to pay according to their terms, as determined by the lender, and that exhibit one or more of the following: Borrower is demonstrating adverse financial and repayment trends; Loan is delinquent or past due under loan contract terms. One or both of these factors, together with inadequate collateralization, present a high probability of loss to the lender.

### District

Typically the AgriBank District when used by itself.

### District Data

District Data or District DB is a governed, enterprise-level data product that provides a consolidated and standardized view of financial and operational data across the AgriBank District. It harmonizes data from AgriBank and affiliated associations to support consistent district-wide reporting, analysis, and regulatory use cases.

### Doubtful (asset classification) (D)

A UCS asset classification applied to loans that have all the weaknesses of a substandard asset plus additional characteristics that make full collection highly questionable and improbable based on currently existing facts, conditions, and values.

**See Also**

- Uniform Classification System (UCS)

### Doubtful Asset Quality

An asset classified doubtful has all the weaknesses inherent in one classified substandard with the added characteristic that the weaknesses make collection in full, on the basis of currently existing facts, conditions, and values, highly questionable and improbable. The possibility of a loss is extremely high, but because of certain important and reasonable specific pending factors that may work to the advantage and strengthening of the asset, its classification as an estimated loss is deferred until more exact status can be determined. Pending factors include proposed merger, acquisition, or liquidation procedures; capital injection; perfecting liens on additional collateral; and refinancing plans.

### Down Payment

Money paid to make up the difference between the purchase price and the mortgage amount.

### Draft

An order for payment of money drawn by one person or bank on another.

### Due on Sale

A clause in a mortgage contract requiring the borrower to pay the entire outstanding balance upon sale or transfer of the property.

### Earned Net Worth (ENW)

The cumulative amount of net earnings retained by AgriBank over time after expenses, dividends, and patronage distributions, representing the portion of total net worth generated through ongoing operations rather than contributed or allocated capital.

### Earned Net Worth Change

The earned net worth change calculated beginning and ending balance sheets for a given period

### Earnest Money

Advance payment of part of the purchase price to bind a contract for property.

### Earning Assets

Accrual loans and investments.

### Earnings before Interest, Tax, Depreciation and Amortization (EBITDA)

An approximate measure of a company's operating cash flow based on data from the company's income statement.

### Earnings on Equity (EOE)

A financial metric measuring the return generated on the equity capital invested in an institution, calculated by dividing net earnings by average equity.

### Earnings Reconcilement

The process of accounting for changes between two balance sheets covering a specified period to a borrower's earnings statement for that period. Reconciliation methods include: net worth change, working capital change, or cash reconciliation.

### Economic Value Added (EVA)

A measure of financial performance calculated as net operating profit after taxes minus the cost of capital employed, indicating whether value is being created or destroyed for equity holders.

### Economic Value of Equity (EVE)

A measure of interest rate risk representing the present value of all asset cash flows minus the present value of all liability cash flows; a decline in EVE signals that rising interest rates are reducing the institution's long-term net worth.

### Effective Interest Rate

A measure of the cost of credit, expressed as an annual percentage rate, that shows the effect of the following costs, if any, on the interest rate on a loan charged by a lender to a borrower: - The amount of any stock or participation certificates that a borrow is required to buy to obtain the loan; and - Any loan origination charges paid by a borrower to a lender to obtain the loan.

### Electronic Funds Transfer (EFT)

The electronic movement of money between accounts at financial institutions, including ACH transactions, wire transfers, and other digital payment methods, conducted without the exchange of paper currency.

**See Also**

- Automated Clearing House (ACH)

### Environmental Assessment

Evaluation of a property or business for the purpose of determining the elements of environ mental risk. The assessment can be done by the lender or an environmental professional. An assessment provides sufficient information to allow for an environmental risk classification of the property or business and enable the lender to recommend further action.

### Equal Credit Opportunity Act (ECOA)
[www.consumerfinance.gov/compliance/compliance-resources/other-applicable-requirements/equal-credit-opportunity-act](https://www.consumerfinance.gov/compliance/compliance-resources/other-applicable-requirements/equal-credit-opportunity-act/)

Federal legislation prohibiting creditors from discriminating against credit applicants on the basis of race, color, religion, national origin, sex, marital status, age (as long as the applicant is of legal age to contract), handicap, familial status, fact that part of income derived from a public assistance program, or fact that applicant exercised in good faith any right under the Consumer Protection Act. Lenders must complete certain procedures and forms to comply with this act.

### Equipment Data Association (EDA)
[ironsolutions.com/what-is-eda](https://ironsolutions.com/what-is-eda/)

Equipment Data Associates; vendor that provides list of UCC filings on equipment purchases, including purchaser data and lienholder.

**See Also**

- Uniform Commercial Code (UCC)

### Equity

The "valuation" that you own in your home, i.e. the property value less the mortgage loan outstanding.

### Equity or Owner's Equity/Interest

The difference between the fair market value and current indebtedness; also referred to as Owner's Equity or Owner's Interest.

### Escrow

Act of delivering a document, deed, or money to a third person to be held by that person until the happening of a contingency or performance of an obligation.

### Escrow Balance

The balance of escrow funds collected from the customer and not disbursed.

### Escrow Interest Balance

The balance of interest on escrow funds collected from the customer and not applied to the loan.

### Estate

Interest or Right that an individual has in property. This term also is used, as in probate proceedings, to mean all property of an individual.

### Estimated Market Value (EMV)

An estimate of market value based on the most recent real estate appraisal and value trends of the overall market. Estimated market value is not an appraisal. The property may or may not be inspected. As a part of an appraisal, the subject property is indexed to a specific comparable benchmark or to a benchmark region. Subsequent percentage changes in the benchmark or benchmark region values are applied to the subject property appraised values to estimate the current market value.

### Examiner In Charge (EIC)

The Farm Credit Administration examiner who leads and is responsible for the overall conduct and conclusions of a safety and soundness examination of a Farm Credit System institution.

### Executive Leadership Team (ELT)

The senior-most group of executives within an organization responsible for setting strategic direction, making major organizational decisions, and overseeing overall performance and culture. The "C-suite" in non-Farm Credit enterprises.

**See Also**

- Senior Leadership Team (SLT)
- Senior Management Team (SMT)

### Fair Credit Reporting Act (FCRA)
[www.consumerfinance.gov/learnmore](https://www.consumerfinance.gov/learnmore/)

A consumer protection law that regulates the disclosure of consumer credit reports by consumer/credit reporting agencies and establishes procedures for correcting mistakes on one's credit record.

### Family Living Expense

Total amount of Family Living expenses

### Fannie Mae (FNMA)
[www.fanniemae.com](https://www.fanniemae.com/)

The Federal National Mortgage Association, a government-sponsored enterprise that purchases and securitizes mortgage loans to provide liquidity to the secondary mortgage market and support homeownership.

**See Also**

- Federal National Mortgage Association (FNMA, a.k.a. Fannie Mae)

### Farm Cash Management

The Farm Cash Management® (FCM®) application is used to enroll customers and employees in the AgriBank Farm Cash Management program. Some functions vary by the type of FCM customer: Member association customers: Authorized association staff use the FCM application to establish an AgriBank investment account for association customers, either linked to an existing or new revolving line of credit (RLOC), or as a Stand Alone option. This, along with Funds Held, are two unique offerings in the portfolios for the associations to offer to Farm Credit customers.

**See Also**

- Funds Held
- Revolving Line of Credit (RLOC)

### Farm Credit Act
[www.fca.gov/about/farm-credit-act](https://www.fca.gov/about/farm-credit-act)

The Farm Credit Act of 1971, as amended, (12 U.S.C. §§ 2001-2279cc) is the statute under which the FCS operates. The Farm Credit Act recodified all previous acts governing the FCS.

### Farm Credit Administration (FCA)
[www.fca.gov](https://www.fca.gov/)

The Farm Credit Administration (FCA) is an independent agency in the executive branch of the U.S. Government. It is responsible for the regulation and examination of the banks, associations, and related entities that collectively comprise what is known as the Farm Credit System, including the Federal Agricultural Mortgage Corporation (Farmer Mac). Initially created by an Executive order of the President in 1933, the agency now derives its powers and authorities from the Farm Credit Act of 1971, as amended (Act). FCA's mission is to promote a safe, sound and competitive Farm Credit System.

**See Also**

- Federal Agricultural Mortgage Corporation (Farmer Mac)
- Farm Credit Act

### Farm Credit Administration Loan Type (FCA Loan Type)

The FCA Loan Type as determined for Funding Corporation loan type reporting. See Chapter 4 of applicable FCA reporting guidance for valid values.

**See Also**

- Farm Credit Administration (FCA)
- Federal Farm Credit Banks Funding Corporation
- Farm Credit Bank (FCB)

### Farm Credit Bank (FCB)

One of four Farm Credit Banks in the U.S. that provides wholesale funding and financial services to affiliated Farm Credit associations, which in turn lend to farmers, ranchers, and rural borrowers. FCBs were formed on July 6, 1988, when the Federal Land Bank and the Federal Intermediate Credit Bank in 11 of the 12 then-existing Farm Credit districts merged, as required by the Agricultural Credit Act of 1987. As of 2024, the four FCBs are: AgFirst Farm Credit Bank; AgriBank, FCB; Farm Credit Bank of Texas; and CoBank, ACB (which also functions as an Agricultural Credit Bank). Each FCB provides funds and services to local associations that in turn lend to farmers, ranchers, producers and harvesters of aquatic products, rural residents for housing, and certain agriculture-related businesses.

**See Also**

- Federal Intermediate Credit Bank (FICB)
- Agricultural Credit Bank (ACB)
- Federal Land Bank

### Farm Credit Council (FCC)
[www.fccouncil.com](https://www.fccouncil.com/)

A federated trade association located in Washington, D.C. The FCC consists of CoBank and six district councils and serves as a forum for determining public policy positions for the entire Farm Credit System.

**Disambiguation**

- Farm Credit Council (FCC) — federated trade association; determines public policy positions for the Farm Credit System
- Farm Credit Council Services (FCCS) — separate operational services and consulting firm affiliated with FCC

### Farm Credit Council Services (FCCS)

FCCS (formerly known as Farm Credit Council Services) is a professional services and consulting firm that provides specialized business solutions to the Farm Credit System (FCS), agricultural cooperatives, and self-insured organizations. While it is closely affiliated with the Farm Credit Council—the national trade association for the Farm Credit System—FCCS operates as a separate entity focused on operational support, risk management, and leadership development rather than legislative advocacy.

**See Also**

- Farm Credit Council (FCC)

### Farm Credit Financial Partners (FPI)
[www.financialpartners.com](https://www.financialpartners.com/)

FPI is a customer-owned company that provides technology services to the Farm Credit System. FPI's services include intranets, Customer MySites, CreditPro, and Collateral Web. FPI is a Farm Credit System 4.25 service corporation, like Sunstream.

**Disambiguation**

- Farm Credit Financial Partners — technology service corporation
- Financial Partners, Inc. — technology provider to Associations

### Farm Credit Foundations

Farm Credit Foundations is a Farm Credit System 4.25 service organization supporting education, outreach, and cooperative initiatives across Farm Credit institutions.

**See Also**

- FCS Service Corporation (4.25)

### Farm Credit Illinois (FCI, FCIL)

A member-owned cooperative that provides a variety of financial services to farmers, ranchers, and agribusinesses in Illinois. It is part of the AgriBank District.

**See Also**

- Agricultural Credit Association (ACA)

### Farm Credit Leasing Services Corporation

The Leasing Corporation is a service entity owned by CoBank, ACB. It provides equipment leasing and related services to eligible borrowers, including agricultural producers, cooperatives, and rural utilities.

**See Also**

- Agricultural Credit Bank (ACB)

### Farm Credit Mid-America (Mid-Am)
[www.fcma.com](https://www.fcma.com/)

A member-owned financial cooperative that provides financial services to farmers, ranchers, and agribusinesses in the Midwestern United States. Farm Credit Mid-America operates in Indiana, Kentucky, Ohio, and Tennessee. It is part of the AgriBank District.

**See Also**

- Agricultural Credit Association (ACA)

### Farm Credit of Southern Colorado
[http://www.aglending.com](http://www.aglending.com)

Farm Credit of Southern Colorado is a Farm Credit System Association serving agricultural producers and rural communities across southern Colorado.

**See Also**

- Agricultural Credit Association (ACA)

### Farm Credit of Western Oklahoma
[http://www.fcwestok.com](http://www.fcwestok.com)

Farm Credit of Western Oklahoma is a Farm Credit System Association serving agricultural producers and rural communities in western Oklahoma.

**See Also**

- Agricultural Credit Association (ACA)

### Farm Credit Services of America (FCSA)
[www.fcsamerica.com](https://www.fcsamerica.com/)

A member-owned financial cooperative that provides financial services to farmers, ranchers, and agribusinesses across portions of the western and central United States. Farm Credit Services of America primarily serves farmers and agribusinesses in Nebraska, Iowa, Kansas, and South Dakota. It is part of the AgriBank District.

### Farm Credit Services of Mandan (Mandan)
[http://www.farmcreditmandan.com](http://www.farmcreditmandan.com)

A member-owned financial cooperative that provides financial services and support to farmers, ranchers, and rural businesses. FCS of Mandan operates primarily in North Dakota. It is part of the AgriBank District.

**See Also**

- Agricultural Credit Association (ACA)

### Farm Credit Services of Western Arkansas (WEAR)
[http://www.myaglender.com](http://www.myaglender.com)

A member-owned financial cooperative that provides financial services to farmers, ranchers, and rural businesses in Western Arkansas. It is part of the AgriBank District.

**See Also**

- Agricultural Credit Association (ACA)

### Farm Credit Southeast Missouri
[www.farmcreditsemo.com](https://www.farmcreditsemo.com/)

A member-owned financial cooperative that provides financial services to farmers, ranchers, and rural communities in Southeast Missouri. It is part of the AgriBank District.

**See Also**

- Agricultural Credit Association (ACA)

### Farm Credit System (FCS)

The Farm Credit System (System) is a network of borrower-owned lending institutions and related service organizations serving all 50 states and the Commonwealth of Puerto Rico. These institutions specialize in providing credit and related services to farmers, ranchers, and producers or harvesters of aquatic products. Loans may also be made to finance the processing and marketing activities of these borrowers. In addition, loans may be made to rural homeowners, certain farm-related businesses, and agricultural, aquatic, and public utility cooperatives. All System banks and associations are governed by boards of directors elected by the stockholders who are borrowers of each institution. Additionally, Federal law requires that at least one member of the board be elected from outside the System by the other directors. System institutions, unlike commercial banks or thrifts, do not take deposits.

**See Also**

- Farm Credit Act
- Farm Credit Administration (FCA)
- Federal Farm Credit Banks Funding Corporation

**Disambiguation**

- Farm Credit Services — common label for the network of credit institutions
- Farm Credit System — the borrower-owned cooperative lending network at the regulatory level

### Farm Credit System Insurance Corporation (FCSIC)
[www.fcsic.gov](https://www.fcsic.gov/)

The FCSIC was established by the Agricultural Credit Act of 1987 as an independent U.S. government-controlled corporation. Its purpose is to ensure the timely payment of principal and interest on insured notes, bonds, and other obligations issued on behalf of FCS banks and to act as conservator or receiver of FCS institutions. The FCA Board serves ex officio as the Board of Directors for FCSIC; however, the Chairman of the FCA Board is not permitted to serve as the Chairman of the FCSIC Board.

**See Also**

- Farm Credit Administration (FCA)

### Farm Pay/Remote Payment Capture

Digital payment solutions used within the Farm Credit System (FCS) to provide secure, efficient, and remote methods for borrowers to make payments on their loans or financial transactions without visiting a physical office. Also known as Remote Deposit Capture (RDC).

**Disambiguation**

- FarmPay / RDC - Remote Deposit Capture — branch/association check scanning to deposit customer checks received in the office
- FarmPay(TM) - Client Remote Payment Capture (RDC) — borrower-facing accounts for remote payment posting directly to client loans

### Farm Serial Number (FSN)

Farm Serial Number. An identification number assigned to a farm by the FSA county committee. This number is unique to a farm and producer.

**See Also**

- Farm Services Agency (FSA)

### Farm Services Agency (FSA)
[www.fsa.usda.gov](https://www.fsa.usda.gov/)

The Farm Service Agency of the U.S. Department of Agriculture ensures the well being of American agriculture, the environment and the American public through efficient and equitable administration of farm commodity programs; farm ownership, operating and emergency loans; conservation and environmental programs; emergency and disaster assistance; domestic and international food assistance and international export credit programs.

### Farmer

A person owning agricultural land or engaged in the production of agricultural products, including aquatic products under controlled conditions.

### FCS Financial (FCSF)
[www.myfcsfinancial.com](https://www.myfcsfinancial.com/)

A financial cooperative that provides a range of financial services to farmers, ranchers, and rural businesses. FCS Financial primarily serves the state of Missouri. It is part of the AgriBank District.

**See Also**

- Agricultural Credit Association (ACA)

### FCS of Colusa-Glenn
[www.fcscolusaglenn.com](https://www.fcscolusaglenn.com/)

A financial cooperative that provides a range of financial services to farmers, ranchers, and rural businesses in northern California.

**See Also**

- Agricultural Credit Association (ACA)

### FCS Service Corporation (4.25)

A service entity authorized under Section 4.25 of the Farm Credit Act that is owned by Farm Credit System institutions and provides technology, operational, or other support services to FCS members on a cooperative basis. Sunstream, FPI and Foundations are examples.

**See Also**

- Farm Credit Act

### Federal Agricultural Mortgage Corporation (Farmer Mac)
[www.farmermac.com](https://www.farmermac.com/)

Farmer Mac was created with the enactment of the Agricultural Credit Act of 1987 to provide a secondary market for agricultural real estate and rural housing mortgage loans.

### Federal Crop Insurance Corporation (FCIC)

The Federal Crop Insurance Corporation (FCIC) promotes the national welfare by improving the economic stability of agriculture through a sound system of crop insurance and providing the means for the research and experience helpful in devising and establishing such insurance.

### Federal Deposit Insurance Corporation (FDIC)
[www.fdic.gov](https://www.fdic.gov/)

The Federal Deposit Insurance Corporation (FDIC) preserves and promotes public confidence in the U.S. financial system by insuring deposits in banks and thrift institutions for up to $250,000 (as of 2008); by identifying, monitoring and addressing risks to the deposit insurance funds; and by limiting the effect on the economy and the financial system when a bank or thrift institution fails.

### Federal Emergency Management Agency (FEMA)
[www.fema.gov](https://www.fema.gov/)

A U.S. government agency responsible for coordinating the federal government's response to natural and man-made disasters, including administering the National Flood Insurance Program relevant to FCS collateral evaluation.

**See Also**

- National Flood Insurance Program (NFIP)

### Federal Farm Credit Bank Funding Corporation (FFCBFC)

The entity, based in Jersey City, New Jersey, that issues and manages systemwide debt securities on behalf of Farm Credit System banks to raise capital for agricultural lending.

### Federal Farm Credit Banks Funding Corporation
[www.farmcreditfunding.com](https://www.farmcreditfunding.com/)

The Funding Corporation, based in Jersey City, New Jersey, manages the sale of Systemwide debt securities to finance the loans made by FCS institutions. It uses a network of bond dealers to market its securities.

### Federal Financial Institutions Examination Council (FFIEC)
[www.ffiec.gov](https://www.ffiec.gov/)

An interagency body of U.S. financial regulators that prescribes uniform principles, standards, and report forms for the federal examination of financial institutions and makes recommendations to promote uniformity in supervision.

### Federal Home Loan Bank (FHLB)

One of eleven regional cooperative banks established by Congress to provide liquidity and funding to member financial institutions for housing finance, community development, and other lending activities.

### Federal Home Loan Mortgage Corporation (FHLMC, a.k.a. Freddie Mac)
[www.freddiemac.com](https://www.freddiemac.com/)

The FHLMC (Freddie Mac) is a stockholder-owned corporation chartered by Congress in 1970 to keep money flowing to mortgage lenders in support of homeownership and rental housing. Freddie Mac purchases single-family and multifamily residential mortgages and mortgage-related securities, which it finances primarily by issuing mortgage pass through securities and debt instruments in the capital markets.

### Federal Housing Administration (FHA)
[www.hud.gov/program_offices/housing/fhahistory](https://www.hud.gov/program_offices/housing/fhahistory)

The Federal Housing Administration, generally known as "FHA", provides mortgage insurance on loans made by FHA-approved lenders throughout the United States and its territories. FHA insures mortgages on single family and multifamily homes including manufactured homes and hospitals. It is the largest insurer of mortgages in the world, insuring nearly 33 million properties since its inception in 1934.

### Federal Housing Administration Loan (FHA Loan)

A mortgage loan insured by the Federal Housing Administration (FHA), open to all qualified home purchasers. FHA loans allow lower down payments (as low as 3.5%) and more flexible credit requirements than conventional loans. The FHA insures lenders against losses, enabling them to offer more favorable terms, particularly to first-time and lower-income buyers.

**See Also**

- Federal Housing Administration (FHA)

### Federal Insurance and Mitigation Administration (FIMA)

A component of FEMA responsible for managing the National Flood Insurance Program and implementing hazard mitigation programs to reduce the long-term risk of flood and other disaster losses.

**See Also**

- National Flood Insurance Program (NFIP)
- Federal Emergency Management Agency (FEMA)

### Federal Intermediate Credit Bank (FICB)

he Agricultural Credits Act of 1923 provided for the creation of 12 FICBs to discount farmers' short-and intermediate-term notes made by commercial banks, livestock loan companies, and thrift institutions. The Farm Credit Act of 1933 authorized farmers to organize PCAs, which could discount notes with FICBs. As a result, PCAs became the primary entities for delivery of short-and intermediate-term credit to farmers and ranchers. The FICBs and the Federal Land Banks in all Farm Credit districts have merged to become FCBs or the ACB. Thus, no FICBs remain within the FCS.

**See Also**

- Farm Credit Act
- Agricultural Credit Bank (ACB)

### Federal Land Bank

The Federal Farm Loan Act of 1916 provided for the establishment of 12 Federal Land Banks to provide long-term mortgage credit to farmers and ranchers, and later to rural home buyers. All Federal Land Banks and FICBs have merged to become FCBs or part of the ACB. Thus, no Federal Land Banks remain. An FLBA was a lending agent for a Federal Land Bank and later the Farm Credit Bank. FLBAs made and serviced long-term mortgage loans to farmers and ranchers, and to rural residents for housing. FLBAs did not own the loan assets, but made loans on behalf of the Federal Land Bank/Farm Credit Bank with which they were affiliated. As of October 1, 2000, there are no longer any FLBAs in the Farm Credit System.

**See Also**

- Farm Credit Bank (FCB)
- Agricultural Credit Bank (ACB)

### Federal Land Bank Association

These associations were lending agents for FCBs. Federal Land Bank Associations made and serviced long-term mortgage loans to farmers, ranchers, and rural residents for housing. They did not own loan assets but made loans only on behalf of the FCB with which they were affiliated. As of October 1, 2000, there were no remaining Federal Land Bank Associations serving as lending agents for FCBs.

**See Also**

- Federal Land Bank
- Farm Credit Bank (FCB)

### Federal Land Credit Association (FLCA)

An FLCA is a Federal Land Bank Association that owns its loan assets. An FLCA borrows funds from an FCB to make and service long-term loans to farmers, ranchers, and producers and harvesters of aquatic products. It also makes and services housing loans for rural residents. The Agricultural Credit Act of 1987 authorized a Farm Credit Bank to transfer its direct lending authority for long-term mortgage loans to a Federal Land Bank Association. These Associations are designated as FLCAs. Unlike a Federal Land Bank Association, an FLCA owns its loan assets. An FLCA obtains funds from a Farm Credit Bank to make and service long-term mortgage loans to farmers and ranchers, and to rural residents for housing. An FLCA also makes loans to these borrowers for basic processing and marketing activities, and to farm-related businesses.

**See Also**

- Federal Land Bank Association
- Federal Land Bank
- Farm Credit Bank (FCB)

### Federal National Mortgage Association (FNMA, a.k.a. Fannie Mae)
[www.fanniemae.com](https://www.fanniemae.com/)

A tax paying corporation created by Congress that purchases and sells conventional residential mortgages as well as those insured by FHA or guaranteed by VA. This institution, which provides funds for one in seven mortgages, makes mortgage money more available and more affordable. FNMA is a secondary mortgage institution which is the largest single holder of home mortgages in the United States. FNMA buys VA, FHA, and conventional mortgages from primary lenders.

**See Also**

- Fannie Mae (FNMA)
- Federal Housing Administration (FHA)

### Federal Reserve Board (FRB)
[www.federalreserve.gov](https://www.federalreserve.gov/)

The governing body of the Federal Reserve System, the central bank of the United States, responsible for setting monetary policy, supervising banks, maintaining financial system stability, and providing financial services.

### Fee Appraiser

A state-certified or state-licensed appraiser who contracts to perform appraisal services.

### FFCB Funding Corp - Funds Request Application (FRA)

A process used by the Federal Farm Credit Banks (FFCB) Funding Corporation to manage and distribute funds to Farm Credit banks and to tracking issuances.

### Finaled Date

For Collateral Custodian use only. Date collateral pledging is completed by Legal Department. Important for being "first in line" in lien position for collateral.

### Finaling

Certification of loan closing documents ensuring the lender's mortgage/deed of trust lien position. This is completed after title evidence is updated and closing requirements are met.

### Financial Accounting Standards (FAS)

Pronouncements issued by the Financial Accounting Standards Board (FASB) establishing the rules and principles that govern how specific financial transactions and events are recognized, measured, and disclosed in financial statements prepared under U.S. GAAP.

**See Also**

- Financial Accounting Standards Board (FASB)
- Generally Accepted Accounting Principles (GAAP)

### Financial Accounting Standards Board (FASB)
[www.fasb.org](https://www.fasb.org/)

The independent, private-sector organization responsible for establishing and improving financial accounting and reporting standards (U.S. GAAP) for public and private companies and nonprofit organizations in the United States.

**See Also**

- Generally Accepted Accounting Principles (GAAP)

### Financial Assistance Corporation (FAC)

A federally chartered instrumentality created under the Agricultural Credit Act of 1987 to provide financial assistance to troubled Farm Credit System institutions through the issuance of government-guaranteed bonds.

### Financial Guaranty Insurance Company (FGIC)

A bond insurance company that guarantees the timely payment of principal and interest on municipal bonds and structured finance products, providing credit enhancement to lower borrowing costs for issuers.

### Financial Institution Rating System (FIRS)

The FIRS is similar to the Uniform Financial Institutions Rating System used by other Federal banking regulators. However, it has been modified by FCA to reflect the non-depository nature of FCS institutions. The FIRS provides a general framework for assimilating and evaluating all significant financial, asset quality, and management factors to assign a composite rating to each System institution. The ratings are described below.

**See Also**

- Farm Credit Administration (FCA)

### Financial Institution Recovery, Reform and Enforcement Act (FIRREA)
[www.congress.gov/bill/101st-congress/house-bill/1278](https://www.congress.gov/bill/101st-congress/house-bill/1278)

A 1989 federal law enacted in response to the savings and loan crisis that restructured federal bank regulatory agencies, established new capital standards, and strengthened enforcement authority over financial institutions.

### Financial Partners, Inc. - Technology provider to Associations (FPI)

Financial Partners, Inc. - Technology provider to Associations. A Farm Credit 4.25 service corporation.

**Disambiguation**

- Farm Credit Financial Partners — technology service corporation
- Financial Partners, Inc. — technology provider to Associations

**See Also**

- FCS Service Corporation (4.25)

### Financial Position (FP)

The overall financial health and standing of a borrower (such as a farmer, rancher, or agribusiness). It is a snapshot of the borrower's assets, liabilities, and equity, and it helps lenders assess the borrower's ability to meet financial obligations and repay loans.

### Financial Services Officer (FSO)

Loan Officer in some FCS associations.

**See Also**

- Loan Officer (LO)

### Financial Services Representative (FSR)

Customer Service Representative or CSR in some FCS associations. Sometimes a FSR has more responsibilities than a CSR in associations who use both titles.

**See Also**

- Customer Service Representative (CSR)

### Financial Services Specialist (FSS)

A professional who provides various financial services to agricultural clients, helping them navigate financial challenges and meet their operational and capital needs. An FSS may specialize in taxes, insurance or other areas.

### Financial Statement

Balance sheet and income statements provided in a loan application, which are used in credit analysis.

### Financing Lease

A financing device whereby a user can acquire use of an asset for most of its useful life. Rentals are net to the lessor; and the user is responsible for maintenance, taxes, and insurance. Rent payments over the life of the lease are sufficient to enable the lessor to recover the cost of the equipment plus a return on its investment. The term "financing lease" is most often used to describe a conditional sale lease that finances the purchase of an asset.

### Financing Statement

Written notice under the Uniform Commercial Code of a lender's security interest in personal property or fixtures, intended to be filed with the county or state records.

### First Mortgage (First Lien)

Mortgage on property that takes precedence over all other mortgages. Synonymous with a first lien.

### Fiscal Year End (FYE)

The conclusion of a company's financial year or fiscal year, which is a 12-month period used for financial reporting and budgeting. The Fiscal Year End is the point at which a company or organization closes its books, prepares its financial statements, and assesses its financial performance over the course of that period.

### Fiserv DNA Loan Accounting System (DNA)
[www.fiserv.com/en/solutions/banking/digital-banking/dna.html](https://www.fiserv.com/en/solutions/banking/digital-banking/dna.html)

The loan accounting application ("core") from Fiserv that replaced the legacy Cornerstone (BMIS) system in the AgriBank District. DNA serves as the primary system of record for loan and customer data for associations that have migrated to it. Note that Fiserv DNA does not support split credit classifications, so loan classifications will always be 0% or 100%.

**See Also**

- Bank Management Information System (BMIS)

### Fixed Adjustable Interest Rate

Rate of interest that remains the same for specified period of time, usually one, three, or five years. Also referred to as "Periodic" Interest Rate.

### Fixed Assets (FA)

Long-term, tangible assets held for business use and not expected to be converted to cash in the current or upcoming fiscal year, such as manufacturing equipment, real estate, and furniture. Also called plant.

### Fixed Dollar (FD)

A fixed amount of money that is determined at the outset of a loan or financial agreement. This could be part of the terms of a loan or other financial products where a fixed dollar amount is agreed upon, often relating to repayments, credit limits, or loan disbursements.

### Fixed Interest Rate

Rate of interest that does not change over the life of the loan.

### Fixed Rate

A loan where the initial payments are based on a certain interest rate for a stated period. The rate payable will not change during this period regardless of changes in the lender's standard variable rate.

### Fixed Rate Loan

Loan with an interest rate that does not fluctuate.

### Fixed Rate Mortgage

A mortgage with an interest rate that remains the same over the years.

### Flood Hazard Determination

Shows whether property to be mortgaged is located in a zone where flood insurance would be required. A flood determination must be obtained every time we extend, make, renew or increase credit to a customer and the loan is or will be secured by real estate on which a building is located.

### Forbearance

A creditor's action to refrain from enforcing contractual obligations, rights, or claims against borrowers when a default condition occurs. As a loan servicing remedy, forbearance does not reduce borrower liability for amount of obligation under the original loan contract. Forbearance is a non-FAS 15 restructuring action, if the loan is financially stressed, and the act of forbearance is supported by legally enforceable documentation.

**See Also**

- Financial Accounting Standards (FAS)

### Foreclosure

A legal proceeding to enforce a lien on property, whether real or personal, that secures a non-interest-earning asset or distressed loan; or the seizing of and realizing on non-real property collateral, to effect collection of a nonaccrual or distressed loan.

### Foreign Exchange Wire Processing (FX Wire Processing)

AgriBank's service enabling associations and clients to process international wire transfers in foreign currency. Associations submit international wire requests to AgriBank using proper signer authority procedures; AgriBank transmits the wire and debits the association's general ledger for the transaction.

### Formally Restructured Loans

Loans that are "troubled debt restructurings," as defined in Statement of Financial Accounting Standards No. 15, Accounting by Debtors and Creditors for Troubled Debt Restructurings of the Financial Accounting Standards Board. Such loans are reported as formally restructured unless, subsequent to restructuring, the loan is performing according to its modified terms and the effective interest rate is at least equal to the rate the lender was willing to accept for a new loan with comparable risk.

**See Also**

- Financial Accounting Standards Board (FASB)
- Financial Accounting Standards (FAS)

### Forward Contract

A contract in which a seller agrees to deliver a specified cash commodity to a buyer sometime in the future, in contrast to a futures contract in which terms of the con tract are not standard.

### Frontier Farm Credit
[www.frontierfarmcredit.com](https://www.frontierfarmcredit.com/)

A member-owned financial cooperative that provides a wide range of financial services to farmers, ranchers, and rural businesses. Frontier Farm Credit serves Kansas and surrounding regions. It is managed by but separate from FCS America.

### Full-Time Farmer

An individual whose primary business and vocation is farming. A full-time farmer may have nonagricultural assets and income from nonagricultural sources.

### Fully Adjustable Interest Rate

Interest rate which can change in accordance with the terms stated in the loan agreement, over the life of the loan. Also referred to as "30 Day Adjustable" or "Variable".

### Fully Amortized

A schedule of principal payments over the term of a loan that completely repays principal by maturity date with no balloon payment.

### Funding

(For Associations) Debt sources from Farm Credit Banks at a price (e.g., MCD) and with terms (e.g., maturity and repayment). (For Banks) Debt sources from capital markets at a price (rate) with terms (e.g., maturity).

**See Also**

- Marginal Cost of Debt (MCD)

### Funding Corp

The Farm Credit Funding Corporation supports the issuance and management of debt securities on behalf of the Farm Credit System to enable funding for AgriBank and other institutions.

### Funds Held

The total amount of funds collected from the customer to pay future installments plus interest earned on Funds Held, but not applied.

### Funds Held / Funds Held Interest (FH/FH Interest)

The combined balance of Funds Held and Funds Held Interest. Funds Held represents amounts collected from the customer to pay future installments, plus interest earned on those held funds but not yet applied to the loan.

**See Also**

- Funds Held

### Funds Held Differential Percent

The stated Funds Held rate for loans with a Funds Held Rate Indicator of F; for loans with a Funds Held Rate Indicator of V, the stated rate equals the billing rate minus the Funds Held Differential Percent.

**See Also**

- Funds Held

### Funds Pricing System (FPS)

A separate pricing system of AgriBank's Treasury department that is interfaced to Cornerstone and maintains pricing within the district by assigning a Marginal Cost of Debt (MCD) to each retail loan. FPS manages wholesale product pricing, rate assignments, and related fee calculations across the AgriBank District.

**See Also**

- Marginal Cost of Debt (MCD)

### General Intangibles

Any personal property, including things in action, other than accounts, certificates of deposit, chattel paper, commercial tort claims, deposit accounts, documents, goods, instruments, investment property, letter-of-credit rights, letters of credit, money, and oil, gas, or other minerals before extraction. The term includes payment intangibles and software.

### General Ledger (GL)

A book of final entry summarizing all of a company's financial transactions through offsetting debit and credit accounts.

### General Partnership

A legal entity in which two or more persons associate to carry on business as co-owners for profit and are personally liable for all debts of the entity.

### Generally Accepted Accounting Principles (GAAP)

That body of conventions, rules, and procedures necessary to define accepted accounting practice at a particular time. These principles come from the Financial Accounting Standards Board and other authoritative sources recognized as setting standards for the accounting profession in the United States. Generally accepted accounting principles include not only broad guidelines for general applications but also detailed procedures that become standards against which financial presentations are evaluated.

**See Also**

- Financial Accounting Standards Board (FASB)
- Financial Accounting Standards (FAS)

### Golden State Farm Credit
[www.goldenstatefarmcredit.com](https://www.goldenstatefarmcredit.com/)

Golden State Farm Credit is a Farm Credit System Association serving agricultural producers in California while utilizing AgriBank funding and financial services.

### Government Payments

Government Payments received as income divided by Gross Farm Income/Value of Farm Production

**See Also**

- Value of Farm Production (VFP)
- Gross Farm Income (GFI)

### Government Reporting

The mandatory submission of financial, regulatory, and compliance reports to government agencies and regulatory bodies. These reports ensure transparency, accountability, and adherence to federal regulations governing agricultural lending institutions.

### Government-sponsored enterprise (GSE)

A GSE is a federally chartered corporation that is privately owned, designed to provide a source of credit nationwide, and limited to servicing one economic sector. Each GSE has a public or social purpose: to improve the availability of credit to agriculture, education, or housing. GSEs are usually created because the private markets did not satisfy a purpose that Congress deems worthy-either to fill a credit gap or to enhance competitive behavior in the loan market. Each is given certain features or benefits (called GSE attributes) to allow it to overcome the barriers that prevented purely private markets from developing. In some cases, the GSE receives public assistance only to get started; in other cases, the assistance is ongoing. AgriBank is a GSE.

### Green Dollar Amount

Available commitment balance, not including stock, used to show the actual amount that a borrower could receive in cash. The Green Dollar amount is re-calculated daily. Green Dollar amounts are allowed to go negative.

### GreenStone FCS
[www.greenstonefcs.com](https://www.greenstonefcs.com/)

A member-owned financial cooperative that provides a wide range of financial services to farmers, ranchers, and rural businesses. GreenStone FCS serves agricultural clients primarily in Michigan, Wisconsin, and northern Indiana. It is part of the AgriBank District.

**See Also**

- Agricultural Credit Association (ACA)

### Gross Farm Income (GFI)

Income from sale of farm production before expense deductions

### Gross Loans

Total principal amount of accrual and nonaccrual loans, leases, notes and sale contracts outstanding, net of participations sold and charge-offs.

### Gross Loans Plus Accrued Interest

Total principal amount of gross loans plus any interest that has accrued.

### Gross Retail Spread

The difference between accrual retail loan rate and marginal cost of debt. This is comparable among institutions and time periods.

### Group Risk Income Policy (GRIP)

A county-based revenue insurance program that is a variation of GRP. GRIP pays a participating producer when the county revenue per acre for an insured crop falls below a trigger revenue selected by the insured producer, regardless of the actual revenue level of the individual producer. It is available on a limited basis where GRP is currently available.

**See Also**

- Group Risk Policy (GRP)

### Group Risk Policy (GRP)

A form of crop insurance available in certain parts of the country that makes an indemnity payment to all participating crop farmers in a particular area when the entire county's crop production is a certain percentage below the normal production level of the county. This differs from the basic crop insurance program that makes payments to participating farmers when the individual farmer's own crop yield is less than his normal yield. GRP protection involves less paperwork and costs less than MPCI, however, individual crop losses are not covered if the county yield does not suffer a similar level of loss.

**See Also**

- Multiple Peril Crop Insurance (MPCI)

### Growing Crop Investment (GCI)

The financial capital allocated to cultivate crops with the expectation of generating a return once the crops are harvested and sold. In the context of the Farm Credit System or agricultural finance, this term typically relates to loans, funding, or investments used to support the planting, care, and development of crops.

### Guarantor

One who signs an instrument pledging secondary liability for payment of a debt evidenced by another instrument. A guarantor agrees to pay the remaining indebtedness upon failure of payment by the primary obligor.

### Hazardous Substances

Substances defined primarily by reference to federal environmental statutes including CERCLA, RCRA, the Clean Air Act, the Clean Water Act, FIFRA and TSCA. The number of substances which can qualify as hazardous is virtually limitless. A partial list is included in the Code of Federal Regulations (40 CFR Part 302).

**See Also**

- Code of Federal Regulations (CFR)
- Clean Water Act (CWA)
- Clean Air Act (CAA)
- Comprehensive Environmental Response Compensation and Liability Act (CERCLA)
- Resource Conservation and Recovery Act (RCRA)
- Toxic Substance Control Act (TSCA)

### Hazardous Waste

Waste defined broadly in RCRA and EPA implementing regulations. The waste must first qualify as a solid waste, which includes "garbage, refuse, sludge... and other discarded material, including solid, liquid, semisolid or contained gaseous material..." Once it is determined that the waste is a solid waste, the next step is to determine whether it is hazardous. Two mechanisms are used for making this determination. One is a comparison of the waste with a list contained in the regulations. If the waste is listed, it is hazardous. The second method is to determine whether the waste exhibits any of the characteristics of corrosivity, reactivity, ignitability, or toxicity. Waste meeting any of these tests is considered hazardous.

**See Also**

- Resource Conservation and Recovery Act (RCRA)

### Hedge

A means of managing price or market risk by taking an opposite position in the futures market of that held in the cash market.

### High Plains Farm Credit
[highplainsfarmcredit.com](https://highplainsfarmcredit.com/)

A member-owned financial cooperative that provides a wide range of financial services to farmers, ranchers, and rural businesses. High Plains Farm Credit serves agricultural clients in Kansas and other states.

### High Priced Mortgage Loan Indicator (HPML Indicator)

A code used to designate a loan that meets the criteria of a High Priced Mortgage Loan, a reporting requirement of Regulation Z effective October 1, 2009. A loan is generally classified as HPML if its Annual Percentage Rate (APR) exceeds the Average Prime Offer Rate (APOR) by a defined threshold, triggering additional consumer protections including escrow requirements and appraisal rules. This is important for compliance monitoring.

**See Also**

- Annual Percentage Rate (APR)

### High Risk Asset Department (HRAD)

A financial institution, including those in the Farm Credit System, is typically responsible for managing and overseeing assets that are considered high-risk due to factors such as volatility, uncertainty, or a higher likelihood of default. These assets may include loans or investments with a higher probability of underperformance or loss, which require special attention, monitoring, and management strategies.

### High Risk Assets (or Accounting) (HRA)

Loans, investments, or other assets that carry an elevated probability of loss due to borrower financial weakness, collateral deficiencies, or adverse market conditions, typically requiring enhanced monitoring and management attention.

### Home Equity Loan

A loan that allows a customer to borrow money, using their home's equity as collateral. There are different regulations for home equity loans than for other loans, including requirements that the bills and statement information be combined into one document. A special statement frequency of H is used to identify loans in this program.

### Housing and Urban Development (HUD)

Federal agency responsible for encouraging housing development.

### HUD-1 Settlement Statement (HUD-1 Statement)

A document that provides an itemized listing of the funds payable at closing for real estate transactions. Items include real estate commissions, loan fees, points, and initial escrow amounts, each assigned a standardized number. The totals define the seller's net proceeds and the buyer's net payment at closing. Published by the Department of Housing and Urban Development (HUD). Also known as the closing statement or settlement sheet. Note: The HUD-1 was replaced by the Closing Disclosure (CD) for most residential mortgage transactions as of October 3, 2015 under TRID (TILA-RESPA Integrated Disclosure) rules, but may still be used for reverse mortgages and certain other transactions.

**See Also**

- Housing and Urban Development (HUD)
- Real Estate Settlement Procedures Act (RESPA)

### Identical Security / Identical Refinance

Security for a new loan that is the same as the security for the loan it refinances.

### Income and Expense Analysis

Analysis that reflects the borrower's most recent tax or fiscal year of operations (historic) and/or projected (pro forma) income and expense.

### Income and Expense Summary

A summary of only key operating information from the borrower's most recent income tax or other acceptable accounting records.

### Income Capitalization Approach

A set of procedures in which an appraiser derives a value indication for income-producing property by converting anticipated benefits into property value. This conversion is accomplished either by capitalizing a single year's income expectancy or an annual average of several years' income expectancies at a market derived capitalization rate that reflects a specific income pattern, return on investment, and change in the value of the investment; or discounting the annual cash flows for the holding period and the reversion at a specified yield rate or specified yield rates that reflect market behavior.

### Income Statement

An accounting of sales, expenses, and net profit for a given period. Also known as an earnings statement.

### Income Tax Expense

Total amount of Income Tax Expenses; annual income taxes paid

### Incoming ACH

The Incoming ACH process details how ACH transactions are received from the Federal Reserve, evaluated and processed within AgriBank

**See Also**

- Automated Clearing House (ACH)
- Outgoing (Originated) ACH

### Independent Appraisal

An appraisal conducted or administered by a qualified individual not associated with the credit administration, finance or marketing function applicable to the subject property.

### Independent Bankers Association of America (IBAA)
[www.icba.org](https://www.icba.org/)

A national trade association representing community banks across the United States that advocates for policies favorable to independent community banking; now known as the Independent Community Bankers of America (ICBA).

### Independent Evaluator

An individual who is a qualified evaluator and who satisfies regulatory standards and the standards set by the lender for the type of property to be evaluated. The independent evaluator may not be an employee or agent of a lender or have a relationship with the lender or any of its officers or directors in contravention of the regulatory standards of conduct.

### Index Margin Term

The total period (from original inception to end date) that an index margin will contractually be held constant on a contract.

### Index Marginal Term

The time period associated with an index-based rate that defines how long the indexed margin applies before repricing. In Retail Rates, this term supports products whose interest rates are calculated by adding an association-defined margin to an underlying index or marginal cost of debt.

**See Also**

- Retail Rates

### Indirect Liability (IDL)

The context of the Farm Credit System (FCS) refers to a situation where an individual, organization, or institution is responsible for a debt or obligation indirectly, rather than being the primary or direct borrower. It means that although the entity may not be the primary borrower, they may still be held responsible for the debt under certain conditions, such as through guarantees, co-signing agreements, or other forms of financial support.

### Information Data Workgroup (IDWG)

FCA-led data working group for the Farm Credit System.

**See Also**

- Farm Credit Administration (FCA)

### Insurance per Acre (IPA)

A type of crop insurance that provides financial protection to farmers by covering losses on a per-acre basis for eligible crops. This insurance is designed to mitigate the financial impact of crop damage or loss due to factors like weather-related events (e.g., drought, flood, hail), pests, or disease, helping farmers maintain income stability despite uncontrollable circumstances.

### Integrated Producer

For credit analysis purposes, those who produce self owned commodities in a large-scale operation under conditions of market risk exposure, which may be partially mitigated by production contracts.

### Interest Before Debt (IBD)

A financial metric or term that represents a company's ability to generate interest income before accounting for any debt-related expenses such as interest payments on loans or bonds. In simpler terms, Interest Before Debt indicates the earnings generated from the core operations of the institution (such as lending to farmers, agribusinesses, and rural communities) before considering the impact of debt obligations.

### Interest Expenses

Total amount of Interest Expenses

### Interest Rate Risk

The risk of loss resulting from the impact of interest rate fluctuations upon the net interest income and market value of equity of a bank.

### Interest Spread

The difference between rate earned on earning assets and rate paid on interest bearing liabilities.

### Interest Term Debt

Interest on Term Debt as a positive whole dollar amount. Interest on Term Debt, as opposed to total interest, is a component on capital debt repayment capacity. This term interest is added back to arrive at CDRC. Also, an equal amount of term interest must be a demand against CDRC.

### Interests in Leases

Ownership interests in any aspect of a lease transaction, including, but not limited to, servicing rights. AgriBank Underwriting Guide/Internal Use Only Glossary-22 Rev. 1/23

### Intermediate assets

Total value of intermediate assets: Breeding/dairy livestock Securities not readily marketable Personal vehicles Machinery, equipment, trucks, etc. Household goods PCA Stock

**See Also**

- Production Credit Association (PCA)

### Intermediate liabilities

Total value of intermediate term liabilities: Loans with maturities from one to ten years, generally to finance intermediate assets (principal balance due in next 12 months)

### Intermediate Term (IT) Loan

Term debt for equipment.

**Disambiguation**

- Intermediate Term (IT) Loan — Farm Credit equipment lending (typical usage)
- Intermediate Term (Liabilities) (ITL) — balance-sheet category for 1–10 year obligations

### Intermediate Term (Liabilities) (ITL)

Financial obligations or debts that a farm or agricultural business must repay over a medium-term period, typically between 1 to 10 years. These liabilities usually correspond to loans or credit extended for the purchase of intermediate-term assets, such as equipment, machinery, livestock, or infrastructure, that are expected to be useful for several years but not indefinitely.

**Disambiguation**

- Intermediate Term (IT) Loan — Farm Credit equipment lending (typical usage)
- Intermediate Term (Liabilities) (ITL) — balance-sheet category for 1–10 year obligations

### Internal Appraisal Review (IAR)

A formal evaluation conducted by a qualified reviewer within the institution to assess whether an appraisal meets applicable standards, guidelines, and regulatory requirements prior to being used in a credit decision.

### Internal Control Over Financial Reporting (ICFR)

A process consisting of policies and control procedures to ensure financial statement risk and provide reasonable assurance that a company prepares reliable financial statements.

### Internal Credit Review (ICR)

A process or mechanism used to evaluate the credit quality of loans and credit risk within the institution. It involves systematically reviewing loans that have been issued to ensure that they comply with the institution's credit policies, maintain sound credit quality, and meet regulatory and internal standards.

### International Check Processing

Branch locations can accept and process Canadian checks from clients using AgriBank's International check process with US Bank. The process consists of accepting checks that are drawn off a Canadian bank that contains a transit number or foreign dollar amount. Complete a excel template and email to AgriBank and overnight the check to US Bank for processing and the deposit credit. AgriBank cash desk provides the credit once the item is processed at US Bank.

### International Swaps and Derivatives Association (ISDA)
[www.isda.org](https://www.isda.org/)

A global trade organization representing participants in the over-the-counter derivatives market that develops standardized contracts, documentation, and best practices for derivatives transactions worldwide.

### Intervening Lien

Any lien placed of record between recording of a lien and subsequent advance or recording of another lien.

### Investment Percentage

Represents the amount of the Master Loan sold to the investor.

### Investor Commitment Number

A system generated number created for the purchased commitment when an investor is entered on the master commitment record.

### Investor Number

Investor Number of the investing entity, used to link a Participation Sold loan record to the Bank Control File. The Bank Control File stores the name and address of the investor.

### Irrigated (IRR)

Agricultural land that is supplied with water through artificial means-such as through irrigation systems-rather than relying solely on rainfall. Irrigation is commonly used in regions where natural precipitation is insufficient to support crops, or where consistent moisture is necessary for optimal growth.

### Joint Tenancy

Type of property ownership in which joint tenants each have an equal individual interest that, upon death of one joint tenant, succeeds to the benefit of the remaining joint tenant(s).

### Joint Venture

An operating or business arrangement between parties that creates potential liability.

### Junior Lien

A lien that is inferior and subordinate to other lien(s).

### Last 12 months (LTM)

The most recent 12-month period used for financial analysis, reporting, or performance evaluation. It is commonly used to assess trends, financial health, or the overall performance of a borrower, branch, or organization in the context of both operational and financial metrics. This period helps institutions track performance and make decisions based on recent data.

### Lead Lender/Agent

An investor number from the Bank Control File that identifies the entity/organization that has established a commitment with the borrower.

### Leaking Underground Storage Tank (LUST)

An underground tank that stores hazardous substances, such as petroleum products or chemicals, and is leaking or has leaked contaminants into the surrounding environment. These tanks are typically used for storing fuel, oil, or other hazardous materials, often at gas stations, farms, or industrial sites.

### Lease

A financing product option wherein the object of the financing is actually owned by the lender or a secured third party. The consumer gains use of the object for a defined period of time, at more attractive terms than if the consumer, via a loan, purchased the object.

### Leasehold

Interest in an estate that a real estate lessee has by virtue of the lease.

### Legal Description

Technical description of real property suitable for a mortgage/deed of trust and deed.

### Letter of Credit Amount

The amount of the letter of credit. The available commitment on the commitment record is reduced by the letter of credit amount.

### Liability

Represents AgriBank's financial obligations, including cash management programs, system bonds, and derivatives. It covers instruments used to raise capital, manage risk, and fulfill regulatory requirements.

### Lien

A charge by a creditor against real estate or personal property of the debtor. This allows the creditor to claim property as payment for the debt.

### Lien Waiver

A document from a contractor, subcontractor, or other party to a construction project stating that they have received payment and waive any future lien rights to the property. The waiver can be issued on an interim or final basis.

### Life Estate

An interest or right in property during the life of the holder.

### Limited Information (LI)

A situation or scenario in which only partial or insufficient details are available about a specific subject, event, or entity. This lack of complete information can impact decision-making, risk assessment, or problem-solving processes because not all relevant facts, data, or context are provided.

### Limited Information Credit Score (LICS)

A credit score or credit assessment that is based on partial or incomplete data about a borrower. This type of score is typically used in situations where there is insufficient credit history, financial activity, or other relevant data to generate a full or traditional credit score. It may be used to evaluate the creditworthiness of individuals or entities with limited credit histories, such as new borrowers, those with little or no credit activity, or people who are just beginning to build their credit.

### Limited Liability Company (LLC)

A hybrid business entity created by state statutes possessing characteristics of both a corporation and a partnership. The owners of an LLC are its "members" and have limited liability like corporate shareholders. Other key features are flexibility in structuring members' relative management and economic rights, "pass through" tax characteristics of a pure partnership, centralized management, and members' governance rights are not freely transferable.

### Limited Liability Limited Partnership (LLLP)

A legal entity that operates like a limited partnership, but all of the partners, including the general partner, have limited personal liability for the partnership's debts.

### Limited Liability Partnership (LLP)

A legal entity that operates like a limited partnership, but allows any of its limited partners to take an active role in the business of the partnership without exposing them to personal liability for the partnership's debts, except to the extent of their respective capital contributions to the partnership.

### Limited Warranty Deed

A deed by which the grantor guarantees only against claims arising by or through itself.

### Line of Credit (LOC)

An extension of credit that the customer can borrow and repay as long as the outstanding balance doesn't exceed note amount; also known as RLOC or Revolving Line of Credit.

**See Also**

- Revolving Line of Credit (RLOC)

### Liquidation Value

The price that an owner is compelled to accept when a property must be sold without reasonable market exposure.

### Liquidity

Ease in converting an asset into cash without a decrease in value. A broader definition is the ability of a business to meet its cash or short-term obligations when due without disrupting the normal operation of the business.

### Loan

An extension of credit made to a farmer, rancher, or producer or harvester of aquatic products, for any agricultural or aquatic purpose and other credit needs of the borrower, including financing for basic processing and marketing directly related to the borrower's operations and those of other eligible farmers, ranchers, and producers or harvesters of aquatic products.

### Loan (or Local) Service Area (LSA)

The defined geographic territory within which a Farm Credit association is authorized and expected to originate and service loans to eligible borrowers.

**See Also**

- Automatic Territorial Concurrence (ATC)

### Loan Agreement (LA)

A formal contract between a borrower and a lender that outlines the terms and conditions under which a loan is provided. It establishes the rights, obligations, and responsibilities of both the lender (usually an FCS institution) and the borrower. The agreement details the specifics of the loan, including the loan amount, interest rate, repayment schedule, collateral, and other important conditions that both parties must adhere to throughout the life of the loan.

### Loan Application

A complete oral or written request for an extension of credit made in accordance with a lender's procedures for the type of credit requested. An application is considered complete when the lender receives all of the information normally obtained and used in evaluating applications for credit.

### Loan Committee (LC)

A group of individuals, typically within an FCS institution, that is responsible for reviewing and approving or declining loan applications. The committee ensures that loans made to borrowers align with the financial institution's risk policies, underwriting standards, and regulatory requirements.

### Loan Deficiency Payment (LDP)

A payment made to a producer or farmer to compensate for a loss in the market value of their crop or commodity, typically when the market price falls below a certain level set by government programs, such as those managed by the U.S. Department of Agriculture (USDA).

**See Also**

- United States Department of Agriculture (USDA)

### Loan Detail

Provides granular information about individual loans, including rate locks, future commitments, interest rates, credit scorecards, fees, collateral, and land value benchmarks. This domain supports detailed analysis and reporting on loan performance and risk.

### Loan Disbursements Checks

Using a centralized controlled disbursement account, AgriBank district associations are able to issue loan disbursement checks, most through an automated disbursement system and provide an issues file to AgriBank for processing.

### Loan Level Stock (LL)

The stock issued by Farm Credit System institutions (such as cooperative banks or associations) that is tied directly to individual loans. It is a mechanism by which borrowers contribute capital to their lending institutions based on the size of the loan they have with the institution. This stock is a form of ownership interest in the institution and is typically required as part of the loan agreement.

### Loan Margin (LM)

For operating loans only, the margin by which pledged marketable inventories and other financed crop and livestock investments exceed short-term operating loan balance plus interest accruals, current payables, and current term debt commitments that will be financed prior to pledged inventory sales.

### Loan Number

A 13 digit account number assigned by the Sunstream Loan Number Generator to ensure uniqueness across the AgriBank District.

**See Also**

- Number Generator

### Loan Officer (LO)

A professional responsible for evaluating, authorizing, and recommending approval or denial of loans to individuals, businesses, or other organizations. In the Farm Credit System (FCS) or other financial institutions, a Loan Officer's role is critical in assessing borrowers' creditworthiness and ensuring that loans are granted in accordance with the institution's policies, procedures, and regulations.

**Disambiguation**

- Loan Officer (default in Farm Credit context)
- Loan Origination (process/system context)

**See Also**

- Relationship Manager

### Loan Officer Margin (LOM)

In the financial and lending industries, the term Loan Officer Margin (LOM) typically refers to a specific pricing component or profitability metric used to determine the final interest rate of a loan and the revenue generated from it.

**See Also**

- Loan Officer (LO)

### Loan Origination (LO)

The process of creating a new loan, encompassing application intake, underwriting, approval, documentation, and funding. In the AgriBank District, loan origination may be performed through a dedicated Loan Origination System (LOS).

**Disambiguation**

- Loan Officer (default in Farm Credit context)
- Loan Origination (process/system context)

**See Also**

- Loan Origination System (LOS)
- Loan Officer (LO)

### Loan Origination System (LOS)

A software application or platform used by financial institutions, including banks and lenders in systems like the Farm Credit System (FCS), to manage the process of loan origination, from the initial loan application to the final approval and disbursement of funds. The system streamlines and automates various steps in the loan process, making it more efficient and reducing the risk of errors.

### Loan Participation

A loan having two or more lenders. The originating lender makes the loan and sells an interest in the loan to one or more other lenders under a participation agreement.

### Loan Probability of Default

Probability of Default assigned to the loan on a scale of 1 (best) to 14 (loss), based on the loan officer's estimate of risk. See Probability of Default for more information.

**See Also**

- Probability of Default (PD)

### Loan Review Process (LRP)

A critical procedure used by financial institutions, including those in the Farm Credit System (FCS), to assess the quality and risk associated with their loan portfolios. The process involves regularly evaluating the performance of loans to ensure they are being managed properly, identifying potential risks or weaknesses in the loan portfolio, and ensuring compliance with institutional policies, regulations, and financial standards. This helps institutions maintain healthy lending practices, manage credit risk, and identify loans that may need corrective action.

### Loan Service Plan

Summary loan, collateral and financial information, background information, current status identification, and a specific action plan with accountabilities and time frames to resolve causes of an adverse classification over time. To avoid duplication of efforts, whenever possible the service plan is built from existing information. A Customer Service System, if utilized, may fulfill these requirements.

### Loan Servicing Action

Any action to revise an existing loan contract (i.e. modification of existing loan terms and conditions without refinancing the obligation).

### Loan Terms

The conditions that the customer agrees to in the loan contract. Examples are the interest rate, repayment schedule, maturity date, and default interest.

### Loan to Appraised Value (L/AV LTV)

A key financial metric used to assess the risk associated with a loan, particularly in relation to the collateral provided (e.g., real estate, machinery, or other assets). It represents the ratio of the loan amount to the appraised value of the collateral securing the loan.

### Loan to Collateral (L/C)

A financial ratio used to assess the relationship between the loan amount and the value of the collateral securing the loan. Similar to the Loan to Value (LTV) ratio, Loan to Collateral focuses specifically on the asset(s) pledged by the borrower to secure the loan, and it helps the lender determine how much of the collateral's value is being borrowed.

### Loan to value (LTV or LN/AV)

The ratio of the loan amount to the property valuation and expressed as a percentage, e.g. if a borrower is seeking a loan of $150,000 on a property worth $300,000, it has a 50% loan to value ratio. If the loan were $225,000, the LTV would be 75%. The higher the loan to value, the greater the lender's perceived risk.

### Loan/AV

The average loan amount/appraised value on which the loan decision was made.

### Loans2

The Loans2 file and data dictionary defines the structure, meaning, and usage of data elements contained within the Loans2 dataset. It documents loan-level attributes used for regulatory reporting, financial reporting, and risk management, including balances, classifications, credit metrics, and identifiers required for submission to the Farm Credit Administration (FCA) and Funding Corporation.

**See Also**

- Farm Credit Administration (FCA)

### Lock

The lender's guarantee that the mortgage rate quoted will be good for a specific number of days from day of application.

### Lockbox

Vendor service that collects and processes loan payments. Billing notices have the Lockbox address on them for sending payments in the mail.

### Lockbox - 5th 3rd Bank

Bank offering lockbox for AgriBank District associations.

### Lockout Term

A defined period during which a borrower is restricted from prepaying a loan without penalty. In Retail Rates, the lockout term is a product attribute that affects pricing and is used in conjunction with prepayment and conversion rules.

**See Also**

- Retail Rates

### London Interbank Offered Rate (LIBOR)

The United Kingdom's Financial Conduct Authority, which is the regulatory agency that supervises LIBOR. Ended in 2021. Replaced by SOFR.

**See Also**

- Secured Overnight Financing Rate (SOFR)

### Long Range Capital Debt Repayment Margin

A measurement of repayment capacity calculated by adding depreciation to the borrower's average 3 - to 5-year net earnings, and subtracting total annual term debt obligations and capital asset replacement allowance.

### Long Range Capital Repayment Program (LRCDRM)

The Long Range Capital Development and Repayment Model (LRCDRM)—often simply referred to as the "Capital Plan" or "Model"—is a sophisticated financial forecasting tool used by cooperative lending institutions, specifically those within the Farm Credit System (FCS). Its primary purpose is to help a cooperative's Board of Directors determine the optimal balance between keeping earnings to strengthen the bank’s "capital" (safety net) and returning those earnings to member-borrowers in the form of patronage distributions (dividends).

### Long Term (Assets) (LTA)

Assets that are expected to provide economic benefits to a business or financial institution, such as those in the Farm Credit System (FCS), for a period longer than one year. These assets are not intended to be converted into cash or used up within the short-term operational cycle of the business. Instead, they are typically used in the production of goods or services and contribute to the company's ability to generate revenue over an extended period.

### Loss Assets

Assets considered un collectible and of such little value that their continuance as bookable assets is not warranted. This classification does not mean that the loan or asset has absolutely no recovery or salvage value, but rather, it is not practical or desirable to defer writing off this basically worthless asset even though partial recovery may be effected in the future. Lenders should not be allowed to attempt long-term recoveries while the asset remains booked. Losses should be taken in the period in which they surface as uncollectible.

### Loss Given Default (LGD)

An estimate of the portion of the current Exposure at Default that is not recovered, used to support allowance for credit loss calculations. In AgriBank systems, LGD is assigned in categories ranging A through F. LGD is a key input in credit risk modeling under Basel II/III frameworks and is used alongside Probability of Default (PD) to calculate expected credit losses. See also Loss Given Default (LGD) for the full entry.

**See Also**

- Probability of Default (PD)

### Lot

Measured parcel of land having fixed boundaries.

### Machinery/Equipment (M/E)

Tangible assets used in agricultural operations that are eligible for financing. These typically include: Farm machinery, irrigation equipment, livestock equipment, grain handling/storage equipment, transportation equipment, and specialty equipment.

### Major Ag Code

See SIC.

**See Also**

- Standard Industry Code (SIC)

### Manufactured Home

Usually built to HUD specifications. It has a plate with a serial number indicating that it conforms to specifications/standards as of 1976 or later. It is built with a steel I-beam with an axle, wheels, brakes and a tongue that can be removed when it is set on a permanent foundation. The unit is normally titled and transferred to the new owner when purchased. Colloquially a "trailer" or "mobile home."

**See Also**

- Housing and Urban Development (HUD)
- Modular Home
- Spec Home

### Margin

The amount a lender adds to the index on an adjustable rate mortgage to establish the adjusted interest rate.

### Marginal Cost of Debt (MCD)

The cost of obtaining an additional unit of debt financing for agricultural operations. It represents the interest rate and other costs associated with securing new loans or borrowing additional funds.

**Disambiguation**

- Marginal Cost of Debt — general concept of the cost of the next unit of debt
- Marginal Cost of Debt Rate — interest rate AgriBank charges associations per loan

### Marginal Cost of Debt (MCD) Rate

The interest rate AgriBank charges the association for each loan based on the wholesale product assigned to it.

**Disambiguation**

- Marginal Cost of Debt — general concept of the cost of the next unit of debt
- Marginal Cost of Debt Rate — interest rate AgriBank charges associations per loan

### Market Value (MV)

The most probable price a property should bring in a competitive and open market under all conditions requisite to a fair sale, the buyer and seller each acting prudently, knowledgeably and assuming the price is not affected by undue stimulus.

### Maturity Date

The date on which a note or obligation is due and must either be paid in full, refinanced, or renewed.

### Member

Within each association, the customer-owners. Another term for customer, especially retail customers.

### Merged Credit Report

A credit report that contains information from three credit repositories. When the report is created, the information is compared for duplicate entries. Any duplicates are combined to provide a summary of your credit.

### Minority Farmer

For purposes of monitoring lender performance in marketing products to minority farmers and ranchers, a farmer who is among those comprising a smaller part of the farmer population, differing from the majority in some characteristic - typically race or color.

### Mission Related Investment (MRI)

An investment made by a Farm Credit institution that advances its statutory mission of supporting agriculture and rural communities, typically in addition to or alongside its financial return objectives.

### Modular Home

Built to State or IBC codes. It is set on a trailer to haul down the road. It is delivered on the trailer to the site and then removed from the trailer and set on a conventional foundation wall. It is built like a "stick-built" home with no axle underneath to be set on a post and beam structure in a basement. Contrast with Manufactured Home.

**See Also**

- Manufactured Home
- Spec Home

### Month-to-Date Average Daily Balance (MTD ADB)

The Average Daily Balance calculated from the first day of the current month through the current date. Used for financial reporting and performance tracking within a partial month period.

**See Also**

- Average Daily Balance (ADB)

### Mortgage

Legal instrument signed by the mortgagor, pledging real estate as security for payment of a debt. Mortgages are temporary and conditional in nature.

### Mortgage Backed Securities (MBS)

Financial instruments collateralized by a pool of mortgage loans whose principal and interest payments are passed through to investors, used to provide liquidity to the mortgage market.

### Mortgage Broker

An individual who represents numerous lenders and helps consumers find affordable mortgages; the broker charges a fee only if the consumer finds a loan.

### Mortgage Life Insurance

A type of term life insurance often bought by borrowers. The amount of coverage decreases as the principal balance declines. In the event that the borrower dies while the policy is in force, the debt is automatically satisfied by insurance proceeds.

### Multiple Peril Crop Insurance (MPCI)

This program is to insure against losses due to natural causes and to help protect farmers for loss of production below a predetermined yield, known as the unit guarantee, which can be calculated using the producer's actual production history. The farmer selects the amount of average yield to insure (from 50-85%) and the percent of the predicted price to insure (between 55-100% of the crop price established annually by the RMA). If the harvest is less than the yield insured, the farmer is paid an indemnity based on "the difference." The indemnity is calculated by multiplying "the difference" by the insured percentage of the established price selected when the crop insurance was purchased.

**See Also**

- Risk Management Agency (RMA)

### Named Peril (NP)

A type of insurance coverage that specifically protects against risks or perils that are explicitly listed in the policy. If a peril is not named, it is not covered under the policy.

### Narrative

A written loan summary developed differentially according to risk analysis needs. A short narrative for credit actions and periodic updates considers only the credit factors necessary to address pertinent credit weaknesses. The detailed narrative for credit actions concisely addresses each of the credit factors by analyzing their strengths, weaknesses, trends, and necessary improvements.

### National Bankers Association (NBA)
[www.nationalbankers.org](https://www.nationalbankers.org/)

A trade association representing minority-owned banks and financial institutions in the United States, advocating for policies that support minority depository institutions and the communities they serve.

### National Council of Farmer Cooperative (NCFC)
[ncfc.org](https://ncfc.org/)

A national trade association representing agricultural cooperatives that advocates for policies favorable to farmer-owned cooperatives and works to strengthen the cooperative business model in U.S. agriculture.

### National Crop Insurance Services (NCIS)
[ag-risk.org](https://ag-risk.org/)

An established organization which plays an active role in policy formation and education within the industry.

### National Flood Insurance Program (NFIP)
[www.floodsmart.gov](https://www.floodsmart.gov/)

The NFIP is a Federal program enabling property owners in participating communities to purchase insurance protection against losses from flooding. This insurance is designed to provide an insurance alternative to disaster assistance to meet the escalating costs of repairing damage to buildings and their contents caused by floods. Participation in the NFIP is based on an agreement between local communities and the Federal Government that states if a community will adopt and enforce a floodplain management ordinance to reduce future flood risks to new construction in Special Flood Hazard Areas, the Federal Government will make flood insurance available within the community as a financial protection against flood losses.

### National Recognized Statistical Rating Organization (NRSRO)

A credit rating agency registered with the U.S. Securities and Exchange Commission that is authorized to issue credit ratings used for regulatory purposes, such as Moody's, Standard & Poor's, and Fitch.

### National Rural Utilities Cooperative Finance Corporation (CFC)
[www.nrucfc.coop](https://www.nrucfc.coop/)

A cooperative lending institution owned by rural electric and telephone cooperatives that provides supplemental financing to rural utilities beyond what is available from the Rural Utilities Service.

### Net Asset Value (NAV)

The total value of an entity's assets minus its total liabilities, often used to determine the per-share value of a fund or the intrinsic value of an investment portfolio.

### Net Farm Earnings (NFE)

The residual income from farm operations after all farm expenses, including depreciation, have been deducted from gross farm revenues, representing the return to the operator's labor, management, and equity.

### Net Farm Income (NFI)

The value of farm production less total farm expenses plus gain or less loss on sale of capital assets.

**Disambiguation**

- Net Farm Income — value of farm production less total farm expenses ± gain/loss
- Non-Farm Income — income earned from sources outside agricultural operations

### Net Income (NI)

The total profit of an individual, business, or farm after all expenses, taxes, and costs have been deducted from total revenue. It is also known as the bottom line, profit, or earnings and is a key indicator of financial health.

### Net Interest Income (NII)

The difference between the interest income a financial institution earns on its loans and investments and the interest expense it pays on its borrowed funds and liabilities.

### Net Interest Margin (NIM)

Net interest income (interest income less interest expense) divided by average earning assets.

### Net Loans

Accrual loans (net of participations sold) plus nonaccrual loans, less allowance.

### Net Losses

A general term used to summarize the actual total of loan charge-offs, loan recoveries of previous chargeoffs, income (expense) on acquired property, provision for losses on acquired property, and gains (losses) on the sale of acquired property. It does not include the unspecified general reserve in the allowance for loan losses.

### Net New Money

The amount of credit newly extended by a lending entity to a borrower, representing either credit provided to a new borrower or incremental increases in credit to an existing borrower. Net New Money excludes the refinancing or renewal of existing loans, except for any portion of a renewed or refinanced operating loan that exceeds the borrower's prior peak balance or commitment.

### Net Operating Rate (NOR)

In the context of cooperative lending and the Farm Credit System, the Net Operating Rate (NOR) is a financial ratio that measures the efficiency of an institution by calculating its operating expenses as a percentage of its average earning assets. It essentially tells the organization: "How many cents does it cost us in 'overhead' to manage every dollar of our loan portfolio?"

### Net Other Property Owned

The amount of other property owned (net of depreciation) less any allowance for losses on the property.

### Net Present Value (NPV)

The present value of an investment's future net cash flows minus the initial investment.

### Net Realizable Value (NRV)

The net amount expected by the lender to be realized from the sale of an asset. Estimates of market value are based on the assumption that the property is free and clear of such encumbrances, unless they are specifically identified in the property valuation report and the estimated market value is adjusted in consideration thereof. In the Farm Credit System (FCS), NRV is often used in the valuation of collateral (such as farmland, equipment, or commodities) and distressed assets.

**See Also**

- Commodity Credit Corporation (CCC)

### Net Rental Income

For the purpose of calculating debt coverage ratio using the sharecrop approach, net rental income is the owner's share of crop receipts less real estate taxes, building insurance/repair/maintenance, crop input and harvesting expense share, and a labor and management charge. Using the cash rental approach, net farm income is cash rent less real estate taxes, building insurance/ repair/maintenance, and a labor and management charge. Based on the owner/operator approach, net farm income is the gross receipts less real estate and personal property taxes, building insurance/repair/maintenance, crop input and harvesting expenses, and a labor and management charge.

### Net Retail Spread

The difference between accrual retail loan rate and the institution's wholesale loan rate from AgriBank. This may not be comparable among institutions or time periods due to different risk differentials and/or changes in bank spread.

### Net Worth (NW)

Refers to the total value of an individual's or organization's assets minus the total value of its liabilities. It is a financial measure used to assess the financial health of an individual or entity.

### New Additional Lending

Credit extended to a new borrower or additional credit extended to an existing borrow er. Any refinance of a borrower's existing financing (loans or acquired property contracts) with the specific lending entity is excluded. With the renewal or refinance of operating loans, only the new loan or commitment in excess of the peak balance or commitment of prior operating loans is considered as new/additional lending. New additional lending also is referred to as "Net New Money."

**See Also**

- Net New Money

### New Borrower

An individual or entity who has had no financing (loans or acquired property contracts) with the specific lending entity for at least the prior 24 months.

### No Practice Specified (NPS)

A term commonly used in agriculture, insurance, and lending when a specific farming or operational practice is not designated in a policy, loan application, or financial report.

### No Type Specified (NTS)

A designation used in Farm Credit System (FCS) records, applications, and reports when a specific classification or category has not been assigned to a loan, asset, practice, or collateral.

### No-cash outrefinance

A refinance transaction in which the new mortgage amount is limited to the sum of the remaining balance of the existing first mortgage, closing costs (including prepaid items), points, the amount required to satisfy any mortgage liens that are more than one year old (if the borrower chooses to satisfy them), and other funds for the borrower's use (as long as the amount does not exceed 1 percent of the principal amount of the new mortgage).

### Non Performing Loan (NPL)

A loan on which the borrower is not making scheduled principal or interest payments according to the agreed terms, typically defined as being 90 or more days past due, and which may require placement on nonaccrual status.

### Non-Disclosure Agreement (NDA)

In a Farm Credit context, often participations across lenders require Non-Disclosure Agreements in place to protect customer and originating lender interests.

**Disambiguation**

- Non-Disclosure Agreement (default in general business context)
- Non-Disturbance Agreement (specific to mineral-rights / collateral context)

**See Also**

- Non-Disturbance Agreement (NDA)

### Non-Disturbance Agreement (NDA)

In the context of mineral rights, a Non-Disturbance Agreement ensures that the rights of a mineral interest holder or lessee remain intact if the surface owner's property is foreclosed or transferred due to lender action. This agreement protects the continuity of mineral operations and revenue streams by guaranteeing that existing mineral leases will not be disturbed by changes in property ownership. It is typically negotiated among the mineral rights holder, surface owner, and lender.

**Disambiguation**

- Non-Disclosure Agreement (default in general business context)
- Non-Disturbance Agreement (specific to mineral-rights / collateral context)

**See Also**

- Non-Disclosure Agreement (NDA)

### Non-Farm Income (NFI)

Income earned from sources outside of agricultural operations.

**Disambiguation**

- Net Farm Income — value of farm production less total farm expenses ± gain/loss
- Non-Farm Income — income earned from sources outside agricultural operations

### Non-participated Balance

In a commitment situation, the portion (dollar amount) of the Principal Balance owned by the lead lender.

### Non-participated Commitment

The portion (dollar amount) of the Commitment Amount currently owned by the lead lender (not participated to an investor).

**See Also**

- Commitment Amount

### Nonaccrual Asset

An asset on which accrual of interest is suspended for book purposes because: - Collection of any amount of outstanding principal and all past and future interest accruals, considered over the full term of the asset is not expected; or - Any portion of the loan has been charged off, except when a prior chargeoff was taken as part of a formal loan restructuring; or - The loan is 90 days past due and is not both adequately secured and in process o f collection. A loan is considered adequately secured only if: - It is secured by real or personal property having a net realizable value sufficient to discharge the debt in full; or - It is guaranteed by a financially responsible party in an amount sufficient to discharge the debt in full. A loan is considered in process of collection only if collection efforts are proceeding in due course and, based on a probable and specific event, are expected to result in prompt repayment of the debt or its restoration to current status. There must be documented evidence that collection in full of amounts due and unpaid is expected to occur within a reasonable time period, not exceeding 180 days from the date that payment was due. Commencement of collection efforts through legal action, including bankrupt cy or foreclosure, or through collection efforts not involving legal action, including ongoing workouts and reamortizations, do not, in and of themselves, provide sufficient cause to keep a loan out of nonaccrual status. If full collection of the debt or its restoration to current status depends on completion of any action by borrower, lender must obtain borrower's written agreement to complete all such action by specific dates set forth in the agreement.

### Nonaccrual Balance

Current Principal + Total Interest Due + Other Charges + Late Charges + Stop Accrual Interest - LC Stop - Net Charge offs (Total Charge offs - Total Recoveries).

**See Also**

- Current Principal
- Other Charges

### Nonviable Loan

A loan for which it is probable that ultimate payment in full can be accomplished only through liquidation, forced or otherwise, of assets other than that converted to cash in the normal course of business.

### North American Industry Classification System (NAICS)
[www.census.gov/naics](https://www.census.gov/naics/)

A standardized system used to classify business establishments by their primary economic activity across the United States, Canada, and Mexico. Slowly replacing SIC.

**See Also**

- Standard Industry Code (SIC)

### Note

A "Note" in lending is a promissory note - the primary legal instrument evidencing a debt. The note is signed.

### Notice of Commencement

A form filed when full documentation procedures are required. It starts the legal time period within which contractors, subcontractors or material suppliers must file their liens. It should be completed designating the lender to receive legal notices.

### Number of Extensions

Number of times the loan has been extended.

### Number Generator

The Number Generator allows users in the AgriBank District to obtain customer numbers and account numbers to be used when setting up new customer records and loans in the district's loan accounting system. This prevents duplication of customer and account numbers across the district.

### Off Balance Sheet

Formal financial commitments or instruments that do not appear on the balance sheet but are disclosed in the notes to financial statements. They are typically contingent liabilities or assets.

**See Also**

- On Balance Sheet

### Off Ledger

Refers to funds, transactions, or accounts that are not recorded in the General Ledger (GL) of AgriBank. They may be used for internal tracking, budgeting, or planning, but they don't appear in official financial statements.

**See Also**

- General Ledger (GL)
- On Ledger

### Off-System

Refers to associations who are not on specific applications that are not formally integrated into AgriBank's core systems or platforms. These entities operate independently of SBS support, meaning AgriBank does not provide back-end technology services, accounting system integration, or perform accounting work for them. Off-system entities may rely on manual processes, external systems, or localized tools, and are not part of the standardized enterprise service model.

**See Also**

- On-System

### Office of Foreign Asset Control (OFAC)
[ofac.treasury.gov](https://ofac.treasury.gov/)

A U.S. Department of the Treasury office responsible for administering and enforcing economic and trade sanctions against certain countries, entities, and individuals to support U.S. foreign policy and national security objectives. Financial institutions and businesses are required to screen transactions, customers, vendors, and employees to ensure compliance with OFAC sanctions requirements.

### Office Space

A darned good movie.

### Official Loan

Loan to a director or employee of AgriBank, or the lender, or a loan in which any of these individuals has an interest.

### OFI Demographics

The demographic information associated to OFIs (Other Financial Institutions) who have a relationship with AgriBank.

### OFI Loans

The loans where the OFIs are obligated to pay AgriBank, and not the loans where the Farmers are obligated to pay the OFIs.

### Oklahoma AgCredit
[www.okagcredit.com](https://www.okagcredit.com/)

A member-owned financial cooperative that provides a wide range of financial services to farmers, ranchers, and rural businesses. Oklahoma AgCredit serves Oklahoma.

### On Balance Sheet

Formally recorded in the bank's financial statements and reflect the institution's actual assets, liabilities, and equity on the balance sheet.

**See Also**

- Off Balance Sheet

### On Ledger

Refers to financial transactions or balances that are officially recorded in the General Ledger (GL). These transactions are considered settled and reconciled, meaning they are part of the official financial position of the bank. They may or may not be part of the balance sheet, depending on their nature.

**See Also**

- General Ledger (GL)
- Off Ledger

### On-System

Refers to associations who are on specific applications that are formally integrated into AgriBank's internal systems or platforms-especially those used for financial, operational, or governance purposes. When an entity is considered on-system, its technology back-end services are supported through SBS. This means AgriBank provides the service, posts transactions to the association's accounting system, and reconcile some accounts on their behalf.

**See Also**

- Off-System

### On-The-Spot (OTS)

Loan program that specializes in quick underwriting using a scorecard approach.

**See Also**

- On-The-Spot Plus (OTS+)

### On-The-Spot Plus (OTS+)

Loan program that specializes in quick underwriting using a scorecard approach with automated renewal processes.

**See Also**

- On-The-Spot (OTS)

### Open-End Loan

A loan structure that allows some revolving loan features, but limits them by specifying a maximum disbursement amount.

### Operating Lease

A lease whereby a user can acquire use of an asset for a fraction of the useful life of the asset. Also, a lease in which the lessor provides services, such as, maintenance, insurance, and payment of personal property taxes.

### Operating Loan

Provides financing to cover the normal expenses incurred during the production process.

### Option Adjusted Spreads (OAS)

A measure of the yield spread of a fixed-income security relative to a benchmark, adjusted for the value of embedded options (such as prepayment options), used to compare securities with different option characteristics on a consistent basis.

### Origination Process

Loan origination process.

### Other Assets Especially Mentioned (asset classification) (OAEM)

A UCS credit classification for assets that are currently protected but have potential weaknesses that, if uncorrected, may result in deterioration of repayment prospects; considered a criticized but not adversely classified category.

**See Also**

- Uniform Classification System (UCS)

### Other Assets Especially Mentioned Percent (OAEM Percent)

UCS Credit Classification - Percentage of loan classified as Other Assets Especially Mentioned Percent. Note that Fiserv DNA does not allow split credit classifications, so will always be 0% or 100% for DNA-based associations.

**See Also**

- Other Assets Especially Mentioned (asset classification) (OAEM)
- Uniform Classification System (UCS)

### Other Comprehensive Income (OCI)

Components of a financial institution's change in equity during a period that are excluded from net income under GAAP, such as unrealized gains or losses on available-for-sale securities or pension liability adjustments.

**See Also**

- Generally Accepted Accounting Principles (GAAP)

### Other Financial Intermediaries (OFI)

Non-bank financial institutions like financial leasing companies, venture capital firms, or holding companies that engage in financial activities but are not considered traditional banks; essentially, it's data about entities that facilitate financial transactions outside of the standard banking system.

**Disambiguation**

- Other Financial Intermediaries — non-bank financial institutions
- Other Financing Institutions — non-Farm Credit lenders with FCS funding agreements

### Other Financing Institutions (OFI)

Non-Farm Credit lenders that have agreements with Farm Credit System (FCS) institutions to access funding and provide agricultural loans to farmers, ranchers, and rural businesses. These institutions can include: Commercial Banks, Credit Unions, Agricultural Cooperatives, Rural Community Banks.

**Disambiguation**

- Other Financial Intermediaries — non-bank financial institutions
- Other Financing Institutions — non-Farm Credit lenders with FCS funding agreements

### Other Non-farm Income

Other Non-farm Income not included in combined gross salary

### Other Property Owned

Real or personal property acquired and held by AgriBank or a Farm Credit institution through foreclosure, deed in lieu of foreclosure, or other legal means as a result of loan default, and not obtained through normal lending or investment activities. Other Property Owned is held for management, liquidation, or sale to recover amounts owed on distressed or nonperforming loans.

### Other Than Temporary Investment Impairments (OTTI)

A write-down of the carrying value of an investment security when its fair value has declined below its amortized cost and the decline is determined to be other than temporary, requiring recognition of a loss in earnings.

### Out of District (OOD)

Farm Credit Institutions outside of the AgriBank district. This includes associations, service entities, etc.

### Outgoing (Originated) ACH

The Outgoing ACH process details how originated ACH Transactions are gathered, processed and submitted to Federal Reserve. These transactions are specific to loan and/or GL activity. This does NOT include lockbox payments or credit card transactions.

**See Also**

- Automated Clearing House (ACH)
- Incoming ACH

### Override

The act or choice of not using a scorecard decision as the final loan decision when the credit score does not address all risk factors.

### Override Rate

In credit scoring, the "high side" override rate is the number of declined applications scoring at or above cutoff divided by the number of applicants scoring at or above cutoff. The "low side" override rate is the number of accepted applications scoring below cutoff divided by the number of applicants scoring below cutoff.

### Owner Equity (OE)

Net worth of a borrower. Owner equity percent age is calculated by dividing net worth by total assets. This percentage measures the proportion of total assets financed by the borrower's equity capital. Owner equity provides a means to determine the borrower's ability to withstand periods of financial stress.

### Part-Time Farmer

Individuals whose primary business or vocation is essentially other than farming, or those who need to seek off-farm employment to supplement farm income, and who are conducting a valid agricultural operation. Part-time farmers have capability to generate farm income on a sustained basis. They have availability of credit for mortgages, other agricultural purposes, and family needs in the preferred position along with full-time farmers.

### Partial Charge-off (PCO)

That portion of the loan, sale contract, interest, account receivable, or judgment deemed uncollectible an d removed from the asset account.

### Partial Release (PR)

Release of part of land that is security for a mortgage.

### Partially Amortized

Partially amortized loan payments are scheduled to reduce the amount of principal owing; however, at maturity a principal balance remains (balloon payment).

### Participation

A loan participation is a large loan in which two or more lenders share in providing loan funds to a borrower to manage credit risk or overcome a legal lending limit for a single credit. One of the participating lenders originates, services, and documents the loan. Generally, the borrower deals with the institution originating the loan and is not aware of the other participating institutions.

### Participation Certificate

The customer's required investment in the association for a rural home loan.

### Participation Code

M = Master: Represents the total loan to the end customer. Master Loan records have Participation Sold records attached to the loan. P = Purchased: Participation Purchase Loan record. A loan set up on the investor's books. S = Sold: Participation Sold Loan record. Loan record to account for the Participation Sold balances. N = Not Participated: Loan records with no participation. Used in the District DB.

### Participation Loan

Loan having two or more lenders as creditors.

### Participation Method

Identifies the type of participation method on a Participation Sold.

### Past Due Loan

A loan for which any repayment of principal or payment of interest required by the lending agreement is not received by the lender on or before the expected contractual date. The entire outstanding principal and accrued interest is considered past due. Included are demand loans and loans on which a call provision has been activated or past due as of the date that any portion, or all of the outstanding principal and/or accrued interest has been demanded or otherwise called and payment has not been received by the lender.

### Past Due Times

Total number of times a loan has been past due in these categories 10 days 30 days 60 days 90 days 120 days

### Patronage

Patronage is how Farm Credit returns profits to its member‑owners—sharing earnings with borrowers based on their relationship and participation in the cooperative.

### Performance Above Customer Expectations (PACE)

Obsolete scoring system that still shows as a code ('P' for all scored loans, regardless of scoring system) in loan data.

### Permanent Capital

Retained earnings, allocated and unallocated earnings, all surplus (less allowances for losses), and stock issued by the institution, except stock that may be retired by the holder on repayment of the holder's loan, or otherwise at the option or request of the holder, and stock that is protected or otherwise is not at risk.

### Permanent Capital Ratio (PCR)

A regulatory capital adequacy measure used in the Farm Credit System calculated as permanent capital divided by risk-adjusted assets, used to assess whether an institution holds sufficient long-term capital to absorb losses.

### Point of Sale (POS)

A financing program making short-term credit available to farmers through agribusiness firms. Lenders facilitate the program by establishing agreements and providing documents for dealers and suppliers to obtain applications for credit at the time and place of the purchase. This program also is referred to as "point-of-purchase." Farm Credit entities such as AgDirect from FCS America and ProPartners from Compeer and Greenstone offer POS lending programs to equipment and input dealers.

### Points

A charge paid by the customer to obtain a lower interest rate.

### Positive Pay

Positive Pay is a fraud protection tool which mitigates the risk of draft fraud. Positive Pay allows the customer to manually or through an automated file enter drafts that were issues and as they drafts clear through the bank, the system will match them to the issues file and present the customer exceptions for decisioning Pay/Return daily. Reverse positive pay - with this option the customer does not enter any drafts issued and as drafts clear the bank they are presented to the customer daily for a pay or return decision.

### Post Review

Review of a loan, servicing action, or other credit acti on subsequent to approval or closing.

### Post-Closing

Adjustments to balance sheets and income statements that reflect changes to the borrower's financial position and repayment capacity resulting from or associated with the loan transaction. These adjustments are made on an "after closing" basis.

### Potentially Responsible Party (PRP)

An individual, firm, corporation, association, partnership, or state, or local government. PRPs are: - Previous owners or operators of a facility during the time hazardous substances were disposed of at the site.

### Practice/Type/Variety (P/T/V)

These terms are commonly used in crop insurance, agricultural financing, and farm management to classify farming methods, crop characteristics, and livestock.

### Present Value (PV)

The value today of a future payment or stream of payments, discounted at an appropriate discount rate. The concept of present value is used to compare returns on different investment opportunities. By discounting investment costs and returns to recognize "opportunity" costs, investment alternatives can be compared based on the current value of those alternatives.

### Prevented Planting (PP)

Failure to plant the insured crop by the final planting date designated in the Special Provisions for the insured crop. The farmer must have been prevented from planting because of drought, flood, or other natural disaster that is general in the surrounding area and that prevents other producers from planting acreage with similar characteristics.

### Price Loss Coverage (FSA program) (PLC)

A USDA Farm Service Agency commodity support program that provides payments to producers when the effective price for a covered commodity falls below its reference price, helping to protect against significant market price declines.

**See Also**

- United States Department of Agriculture (USDA)

### PricewaterhouseCoopers (PWC)

PricewaterhouseCoopers is the public accounting firm use by AgriBank and ACAs within the AgriBank District.

### Pricing Term

The length of time for which a specific retail interest rate or pricing structure is effective. In Retail Rates, the pricing term is used to define how long a rate, tier, or spread applies before it is eligible for repricing or change.

**See Also**

- Retail Rates

### Primary Borrower Customer Number

Enter the Customer Number of the borrower; Enter the Customer Number of the borrower; Enter the Customer Number of the borrower

**See Also**

- Customer Number

### Primary Security

The basic collateral securing a loan. A first lien on primary security is required for long-term mortgage loans and should be obtained for short-and intermediate-term loans. For operating loans, primary security is normally that collateral representing the source of liquidations on which repayment is based. For ACA/PCA intermediate term loans, primary security is normally the asset(s) being financed. For FCB/FLCA/ACA long-term mortgage loans, primary security is first mortgage real estate collateral that meets lender eligibility requirements.

**See Also**

- Federal Land Credit Association (FLCA)
- Agricultural Credit Association (ACA)
- Farm Credit Bank (FCB)
- Production Credit Association (PCA)

### Principal and Interest (P&I)

Principal and Interest (P&I) are the two primary components of a loan repayment: Principal - The original loan amount borrowed that needs to be repaid. Interest - The cost of borrowing money, calculated as a percentage of the principal, paid to the lender.

### Principal Term Debt

Principal on Term Debt (but not operating debt principal) is a demand against the customer's CDRC

### Principal, Interest, Taxes and Insurance (PITI)

The sum of a residential loan applicant's housing expenses and mortgage payment requirements, typically calculated on a monthly basis, including principal (P), interest (I), real estate taxes (T), and mortgage and home owner's insurance (I) premiums.

### Principal, Interest, Taxes and Insurance Ratio (PITI Ratio)

Principal, Interest, Taxes, and Insurance calculated on a monthly basis, divided by total gross income for the respective period. Also referred to as a housing ratio; it is a relative measure of housing expense to income used in residential mortgage underwriting. A commonly used benchmark is that PITI should not exceed 28% of gross monthly income.

**See Also**

- Principal, Interest, Taxes and Insurance (PITI)

### Prior Approvals

Associations use the Prior Approval Application to submit request to issue an official loan (i.e., a loan to an official party or a related person), to issue an excess loan (where the requested amount is over the authority delegated to the Association), or to put a loan into an asset pool (for certain types of pools and certain Associations).

### Private Mortgage Insurance (PMI)

Money paid to insure the mortgage when the down payment is less than 20 percent.

### Probability of Default (PD)

A numerical or categorical assessment of the level of risk associated with a borrower, loan, investment, or business activity. It helps lenders, investors, and financial institutions determine the likelihood of default, financial instability, or potential losses. A quantitative measure estimating the likelihood that a borrower will default on their obligations within a specific time frame. It's central to credit risk modeling and regulatory frameworks like Basel II/III.

### Production Credit Association (PCA)

PCAs are FCS entities that deliver only short-and intermediate-term loans to farmers and ranchers. A PCA borrows money from its FCB to lend to farmers. PCAs also own their loan assets. As of January 1, 2003, all PCAs were eliminated as independent, stand-alone, direct-lender associations. All PCAs are now subsidiaries of ACAs.

**See Also**

- Farm Credit Bank (FCB)

### Production Reporting Date (PRD)

The deadline by which a farmer must report their actual yield and production data to their crop insurance provider. This information is crucial for determining insurance coverage, premiums, and future guarantees.

### Promissory Note

Written promise from the borrower to repay certain sums of money to a certain person or bearer on demand or on a specified date; primary document in most credit transactions.

### ProPartners Financial
[ppfcredit.com](https://ppfcredit.com/)

ProPartners is a specialized agricultural input financing program associated with Compeer Financial and Greenstone and supported by AgriBank services.

**See Also**

- Compeer Financial

### Protected Stock Nonvoting

A class of member stock that represents an equity investment protected at face value under Farm Credit regulations and AgriBank policy, but does not confer voting rights to the holder. Protected Stock Nonvoting contributes to required borrower equity while limiting participation in governance voting.

### Purchase Money Mortgage

Mortgage given concurrently with transfer of title to obtain the unpaid balance of the purchase price of land.

### Purchase Money Security Interest

An interest that is taken or retained by the seller of an item to secure its price or taken by a person who advances funds to enable one to acquire rights in collateral.

### Purpose

Twenty-character personalized loan identification. Customers have the option to personalize their loans for easier identification on the year-end Statement of Account, etc.

### Quarter-to-Date Average Daily Balance (QTD ADB)

The Average Daily Balance calculated from the first day of the current fiscal quarter through the current date. Used for financial reporting and performance tracking within a partial quarter period.

**See Also**

- Average Daily Balance (ADB)

### Rate Change

Changes in customer interest rates over the life of the loan.

### Rate Change Notification

A written notice of an increase or decrease in the customer's interest rate. Includes the effective date of the interest rate change, states the current and new rates, and how the change was determined.

### Rate Effective Date (RED)

The specific date when a new interest rate, insurance rate, or financial policy goes into effect. It is commonly used in loans, mortgages, insurance, and investment agreements to indicate when a rate change or adjustment is applied.

### Rate Lock

Pipeline of future loans they have committed a retail rate and AgriBank has committed a wholesale rate.

### Rating 1

Institutions in this group are basically sound in every respect; any negative findings or comments are of a minor nature and are anticipated to be resolved in the normal course of business. Such institutions are well managed, resistant to external economic and financial disturbances, and more capable of withstanding the uncertainties of business conditions than institutions with lower ratings. Each institution in this category exhibits the best performance and risk management practices for its size, complexity, and risk profile. As a result, these institutions give no cause for regulatory concern.

### Rating 2

Institutions in this group are also fundamentally sound but may reflect modest weaknesses correctable in the normal course of business. The nature and severity of deficiencies are not considered material, therefore, such institutions are stable and able to withstand business fluctuations.

### Rating 3

Institutions in this category exhibit a combination of financial, management, operational, or compliance weaknesses ranging from moderately severe to unsatisfactory. When weaknesses relate to asset quality or financial condition, such institutions may be vulnerable to the onset of adverse business conditions and could easily deteriorate if concerted action is not effective in correcting the areas of weakness.

### Rating 4

Institutions in this group have an immoderate number of serious financial or operating weaknesses. Serious problems or unsafe and unsound conditions exist that are not being satisfactorily addressed or resolved. Unless effective actions are taken to correct these conditions, they are likely to develop into a situation that will impair future viability or constitute a threat to the interests of investors, borrowers, and stockholders.

### Rating 5

This category is reserved for institutions with an extremely high, immediate or near-term probability of failure. The number and severity of weaknesses or unsafe and unsound conditions are so critical as to require urgent external financial assistance.

### Real Estate (RE)

Land and any permanent structures attached to it, including buildings, homes, farms, and commercial properties. It encompasses buying, selling, leasing, and financing land and property for residential, agricultural, and commercial use.

### Real Estate Search

Abstracter's document certifying search of county records for liens, title transfers, name and tax searches since the date of the lender's last mortgage/deed of trust.

### Real Estate Settlement Procedures Act (RESPA)
[www.consumerfinance.gov/rules-policy/regulations/1024](https://www.consumerfinance.gov/rules-policy/regulations/1024/)

A federal consumer protection statute (12 U.S.C. § 2601 et seq.) administered by the Consumer Financial Protection Bureau (CFPB) that governs residential real estate settlement processes. RESPA requires lenders to provide borrowers with disclosures about settlement costs, prohibits kickbacks and referral fees, and mandates use of standard settlement forms. Disclosure requirements were significantly enhanced effective August 1, 2015. Also known as Regulation X. Note: RESPA generally does not apply to agricultural loans but does apply to country living and rural home loans made by FCS institutions.

**See Also**

- Consumer Financial Protection Bureau (CFPB)

### Reamortization

Assistance plan to provide for rescheduling of principal and interest payments. Also referred to as "Re-am." Outstanding elements of the loan are consolidated into the principal to arrive at a new face amount for the loan. The new face amount, new term in years, and the new interest rate are used to determine the new payment amount.

### Recorded Investment in the Loan

The amount at which a loan is carried on AgriBank's books, representing the borrower's contractual indebtedness outstanding, including principal and applicable accrued items, net of charge-offs and other required accounting adjustments. Recorded Investment in the Loan reflects the lender's accounting value of the loan for financial reporting, risk assessment, and regulatory purposes.

### Recourse

Usually related to Dealers in Trade Credit: The recognized ability of the dealer to provide alternative collateral to back credit exceptions - otherwise unacceptably risky loans.

### Recovery

The amount collected on a loan or other asset that previously had been charged off.

### Redeem

Literally, "to buy back." The act of buying back lands after mortgage foreclosure or tax foreclosure.

### Redemption

Right of a mortgagor to redeem property by paying the debt.

### Refinance

Obtaining a new loan on property already owned, often to replace existing loans on the property.

### Regional Vice President (RVP)

A senior leadership role responsible for overseeing agricultural lending, financial services, and customer relationships within a specific geographic region. The RVP plays a key role in business development, risk management, and strategic planning to support farmers, ranchers, and rural communities.

### Regulatory Accounting Practices (or Principles) (RAP)

Accounting methods and practices directed by statutory and regulatory requirements provided for in the Act and that are not in accordance with GAAP.

**See Also**

- Generally Accepted Accounting Principles (GAAP)

### Related Services (RS)

Financial and non-financial services offered to support farmers, ranchers, agribusinesses, and rural communities beyond traditional lending. These services help customers manage risk, improve financial health, and enhance agricultural operations.

### Relationship Manager

A loan officer who serves as the primary contact for a customer (typically large and/or complex) or Trade Credit dealer.

**See Also**

- Loan Officer (LO)

### Renewal

A loan with an unpaid balance paid by the proceeds of a new loan which may or may not provide funds for other purposes.

### Replacement Allowance (RA)

Funds set aside or provided to replace assets that have depreciated, worn out, or become obsolete over time. This concept is commonly used in finance, agriculture, and business planning to ensure continuous operations without financial strain. The amount of annual allowance necessary for machinery/facility replacement, less annual principal payments on loans financing depreciable assets (which is already included in total demands on CDRC)

### Replant Option (RO)

A feature in crop insurance policies that provides financial assistance to farmers who need to replant a crop due to early-season damage from factors like weather, pests, or disease. It helps cover part of the costs associated with replanting, ensuring farmers can recover from initial planting losses.

### Replevin (Claim and Delivery)

Action to recover possession of personal property; known as claim and delivery in some states.

### Residual Value

The value of a leased asset at the conclusion of the lease term. To qualify the lease as a true lease for tax purposes, the estimated residual value at the end of the lease term must equal at least 20 percent of the original cost of the asset.

### Resource Conservation and Recovery Act (RCRA)

A law enacted by Congress in 1976 to establish procedures for managing hazardous wastes, requiring safe and secure procedures to transport, store, and dispose of hazardous substances from generation to final disposition. RCRA was amended in 1984 to also regulate underground storage tanks (USTs). Under RCRA, the EPA can require tank owners or operators to clean up contamination from leaking US Ts or conduct the cleanup and sue for reimbursement.

### Restrictive Covenants (Conditions and Restrictions)

Restrictions that attach to land and bind all parties acquiring the land.

### Restructure

A reamortization, renewal, deferral of principal or interest, monetary concessions, or the taking of any other action to modify the terms of, or forbear on, a loan. A loan is coded as a restructure whenever there is a concession of principal, accrued interest or future interest. An FSA guarantee without buy down is not coded as a restructure, nor are reamortizations, deferments, or extensions when they involve concessions of time only.

**See Also**

- Farm Services Agency (FSA)

### Retail

Loans; leases; crop and credit life insurances; tax and other product offerings by the associations to non-Capital Markets customers. The "traditional" customer-facing activities for Farm Credit associations.

### Retail Bonds

This process reflects how AgriBank ensures that funds are paid to the Funding Corp for Retail Bonds. Retail bonds are not included in the Funding Corp Net Position number. Cash desk will need to send a separate wire for the amount on the day they are paying. Because of the extra steps, this process runs 2 business days before the 15th so Cash Desk has enough time to set up the wire.

**See Also**

- Funding Corp
- Federal Farm Credit Banks Funding Corporation

### Retail Rates

The Retail Rates application allows users in the AgriBank District to view and maintain product rates.

### Return on Assets (ROA)

Generally, profit from operations divided by average total assets. For credit analysis purposes, ROA is net farm income from operations plus salary/wages plus other non-farm income plus interest expense minus income tax expense minus family living expense, all divided by the average of beginning period total assets plus ending period total assets.

### Return on Equity (ROE)

Generally, profit from operations divided by average net worth. For credit analysis purposes, ROE is net farm income from operations plus salary/wages plus other non-farm income minus income tax expense minus family living expense, all divided by the average of beginning period net worth plus ending period net worth. Aka Return on Capital

### Returns and NOC (Incoming)

This process reflects how Returns and Notices of Change (NOC) are handled. Returns and NOC's originate when an ACH Transaction to another Financial Institution are returned.

**See Also**

- Incoming ACH
- Automated Clearing House (ACH)

### Revenue Assurance (RA)

A form of revenue insurance that protects a grower of an insurable crop whenever low prices, low yields, or a combination of both causes revenue to fall below a guaranteed level selected by the producer. It differs from other revenue insurance programs in that it allows a farmer to use the posted county price, rather than a national price, in determining a target level of revenue.

### Reviewed Loan Volume

Loans classified or graded through the institution's internal audit program, unless the program is considered unreliable by the AgriBank audit process, in which case loans reviewed represent the most reliable evaluation results available. This may be the results from the institution's internal audit program or the internal audit program adjusted for AgriBank audit results.

### Revolving Line of Credit (RLOC)

 A loan structure that allows flexible use of funds. This loan allows the repeated draw of funds, after repayment, up to the note amount.

**See Also**

- Line of Credit (LOC)

### Risk Asset Unit (RAU)

Often pronounced to rhyme with "ow." The unit or team within an Agricultural Credit Association responsible for managing and servicing nonaccrual and high-risk loans. Often operates as its own branch number within the loan accounting system. See also High Risk Assets (HRA).

**See Also**

- Agricultural Credit Association (ACA)
- High Risk Assets (or Accounting) (HRA)

### Risk Based Analysis (RBA)

A systematic approach used to assess, quantify, and manage risk in financial, business, or operational decision-making. It helps organizations prioritize risks based on their potential impact and likelihood, ensuring better resource allocation and strategic planning.

### Risk Funds

Permanent capital plus allowance for loan losses.

### Risk Index (RI)

A numerical or categorical measure used to assess the level of risk associated with a specific asset, investment, loan, or business activity. It helps organizations, lenders, and investors quantify risk exposure and make informed decisions.

### Risk Management Agency (RMA)
[www.rma.usda.gov](https://www.rma.usda.gov/)

An independent office within USDA that is responsible for the supervision of the Federal Crop Insurance Corporation; and the administration and oversight of the federal crop insurance program and any pilot or other programs involving revenue insurance.

**See Also**

- Federal Crop Insurance Corporation (FCIC)
- United States Department of Agriculture (USDA)

### Risk Rating (RR)

An internal credit risk assessment used to measure and track the expected credit risk of a borrower or loan by evaluating the likelihood of default and the potential financial impact if default occurs. Risk Rating supplements the Uniform Classification System by further segmenting acceptable assets for risk monitoring, loss estimation, and portfolio management.

**See Also**

- Uniform Classification System (UCS)

### Risk-Adjusted Return on Capital (RAROC)

A financial performance metric that adjusts return on capital for risk, enabling consistent comparison of profitability across business lines or loan products with different risk profiles. Calculated as: (Revenue − Costs − Expected Losses) / Economic Capital. In the AgriBank context, maintained as a risk-adjusted return on capital analytical tool.

### Rule of Aggregation

For purposes of determining performance status, all loans on which a borrowing entity, or component of a borrowing entity, is primarily obligated to the reporting institution are considered as one loan unless a review of all pertinent facts supports a reasonable determination that a particular loan constitutes an independent credit risk and such determination is adequately documented in the loan file.

### Rural Community Grant Fund (RCGF)

The Rural Community Grant Fund (RCGF) reporting process supports strategic community investment by identifying eligible projects and providing timely, accurate information to the Relationship Management Team. This process ensures that rural communities receive visibility for potential grant funding opportunities and that the organization's philanthropic contributions remain aligned with community needs and corporate priorities.

### Rural Home (RH)

Residential properties located in rural areas that are eligible for specialized financing options through FCS lenders. These homes are often outside urban centers and can be financed for primary residences, second homes, or country properties with acreage.

### Rural Residence (RR)

A single-family dwelling located in a rural area that is used as a permanent, year-round residence by the borrower. The property may include associated land and residential appurtenances (such as outbuildings or acreage) but is primarily intended for residential living rather than agricultural or commercial farming operations.

### Rural Resident

An individual residing in a rural area who is a citizen of the United States or who has been lawfully admitted into the United States for permanent residence and is so domiciled.

### Salary/Wages

Combined Gross Non-farm Salary income of all parties whose income is being used to determine repayment capacity

### Sale Comparison Approach

A set of procedures in which an appraiser derives a value indication by comparing the property being appraised to similar properties that have been sold, applying appropriate units of comparison, and making adjustments, based on the elements of comparison, to the sale prices of the comparable properties.

### Sale-Leaseback

A transaction involving the sale of property by the owner and a lease of the property back to the seller.

### Sales Closing Date (SCD)

The final date by which a farmer or producer must apply for crop insurance coverage for a specific growing season. After this date, new applications or changes to existing policies are generally not allowed.

### Salvage Value

A modified form of market value, reflecting the effect of a salvage sale where the market exposure period is restricted, the property is forced into the market, and buyers envisioned for the property would not continue to use it as it was intended to be used by design; rather, they would disassemble the property components (real estate holdings, fixtures and equipment) and utilize the components in a different setting or configuration.

### Sarbanes-Oxley (SOX) Section 404(b)

A provision of the Sarbanes-Oxley Act of 2002 requiring management of publicly held companies to assess and report on the effectiveness of internal controls over financial reporting, with Section 404(b) additionally requiring the external auditor to attest to that assessment.

### Satisfaction of Mortgage

Legal document issued by the mortgagee when a mortgage is paid in full.

### Scheduled Disbursement Balance (SDB)

The remaining amount of loan funds that are scheduled to be disbursed over time, based on an agreed-upon schedule between the borrower and lender. This balance represents funds that have been approved but not yet released to the borrower.

### Scorecard

A risk assessment tool that uses a statistical model to predict the creditworthiness of applicants. Credit scoring estimates repayment probability based on applicant information and a credit bureau report. NOTE: There is a difference between the "consumer" credit scores offered by Experian, TransUnion, and Equifax, and the custom-developed ag-centric scoring platforms used by the ACAs to score ag loans. Make sure you are talking about the correct one. Typical for Farm Credit it will be the latter, "ag scorecard" or similar terminology.

### Scores

The score data consists of input members which are loaded to the application by the Financial Reporting group on a monthly basis to calculate store CIPA and CPD scores

**See Also**

- Contractual Interbank Performance Agreement (CIPA)
- Corporate Performance Differential (CPD)

### Second Mortgage

A mortgage made subsequent to another mortgage and subordinate to the first one.

### Secondary Mortgage Market

The place where primary mortgage lenders sell the mortgages they make to obtain more funds to originate more new loans.

### Secondary Security

Collateral pledged to support a loan in addition to the primary security, providing an additional source of repayment or risk mitigation. Secondary security supplements, but does not replace, the primary collateral securing the loan and may consist of real or personal property subject to the lender's security interest.

### Secured Overnight Financing Rate (SOFR)
[www.newyorkfed.org/markets/reference-rates/sofr](https://www.newyorkfed.org/markets/reference-rates/sofr)

Following the United Kingdom's Financial Conduct Authority, regulatory agency that supervises LIBOR, announcement in July 2017 of their intention to phase-out LIBOR by the end of 2021, various industry workgroups began preparing for the phase-out, including publishing and promoting the Secured Overnight Financing Rate (SOFR) as a new alternative benchmark rate. The Federal Reserve Bank of New York began publishing SOFR in April 2018. SOFR is a measure of overnight secured borrowing, but the financial industry plans to create term reference rates based on a SOFR derivatives and futures market. If this market develops as planned, then SOFR (or a SOFR average) could become the predominant new reference rate used by U.S. financial institutions.

**See Also**

- London Interbank Offered Rate (LIBOR)

### Security

Collateral given by the debtor to ensure payment or performance of debt by furnishing the creditor with a resource to use in case of failure on the principal obligation.

### Security Agreement

Uniform Commercial Code document that identifies the rights and duties of both parties to a loan and gives the lender a security interest in the borrower's personal property described therein.

**See Also**

- Uniform Commercial Code (UCC)

### Security Interest

The creditor's rights in property given as collateral for the debt.

### Senior Leadership Team (SLT)

A group of top executives and key decision-makers who oversee the strategic direction, operations, and performance of an organization. In the Farm Credit System (FCS) and other financial institutions, the SLT plays a critical role in ensuring financial stability, risk management, and customer service excellence.

**See Also**

- Executive Leadership Team (ELT)
- Senior Management Team (SMT)

### Senior Management Team (SMT)

A group of high-level executives responsible for executing an organization's strategic plans and overseeing daily operations. In the Farm Credit System (FCS) and similar financial institutions, the SMT ensures that business goals align with financial performance, risk management, and customer service excellence.

**See Also**

- Executive Leadership Team (ELT)
- Senior Leadership Team (SLT)

### Sensitivity Analysis

Analysis of variations in a borrower's pro forma income and expenses representing different income and expense scenarios - especially worst case and most likely scenarios.

### Service Plan

A documented action plan developed for a loan or borrower that identifies credit weaknesses, outlines corrective actions, assigns responsibilities, and establishes timelines to improve credit quality or resolve adverse conditions. A Service Plan is used to monitor progress and guide ongoing loan servicing activities.

### Settlement Accounts

Equivalent of the wholesale loan for the associations and zeros out every night. If they are outside of district, we create same day ACH to collect funds and zero it out.

**See Also**

- Automated Clearing House (ACH)

### Severe Default

The loan condition in which the borrower does not perform in accordance with any term(s) or condition(s) or other obligation(s) set forth or incorporated by reference into the loan agreement; and the borrower's failure to perform in accordance with the loan agreement increases the lender's risk exposure on the loan to a level that reduces or threatens to reduce the current or prospective value of the loan as a financial asset.

### Severely Past Due

The loan condition in which principal and/or interest payment is contractually due and uncollected for a period of 90 days or more, subject to the $100 tolerance limit identified for "delinquent loans."

### Shared Asset Number (SAN)

Unique identifier used to track assets that are shared across multiple entities or associations. SANS do not change over time. It should be assigned by the System lead and communicated to participants. It must be 20 digits and start with the UNINUM (at the time) where it was issued.

### Short Term (Assets) (STA)

Business assets that are expected to be converted into cash, sold, or used up within one year. These assets are crucial for maintaining day-to-day operations and ensuring liquidity.

### Similar Entity

A party that is ineligible for a loan from a Farm Credit Bank, ACA, FLCA, or PCA, but has operations that are functionally similar to the activities of eligible borrowers in that a majority of its income is derived from, or a majority of its assets are invested in, the conduct of activities that are performed by eligible borrowers. Important for FCA compliance tracking.

**See Also**

- Farm Credit Bank (FCB)
- Federal Land Credit Association (FLCA)
- Agricultural Credit Association (ACA)
- Farm Credit Administration (FCA)
- Production Credit Association (PCA)

### Similar Entity Loans

Similar entity loans are loans that Farm Credit does not have the authority to make based on its charter individually, but is involved in via a participation.

### Similar Entity Pool (SEP)

In the Farm Credit System (FCS), a Similar Entity Pool refers to a specific segment of a lender's portfolio made up of loan participations in credits extended to borrowers who do not technically qualify for direct Farm Credit financing but perform "functionally similar" activities. Because the Farm Credit System is a Government-Sponsored Enterprise (GSE) with a specific mandate to serve agriculture and rural communities, its ability to lend to "non-eligible" entities is strictly regulated under Section 4.18A of the Farm Credit Act.

**See Also**

- Farm Credit Act
- Similar Entity
- Government-sponsored enterprise (GSE)

### Small Business Administration (SBA)
[www.sba.gov](https://www.sba.gov/)

In the Small Business Act of July 30, 1953, Congress created the Small Business Administration, whose function was to "aid, counsel, assist and protect, insofar as is possible, the interests of small business concerns." The charter also stipulated that the SBA would ensure small businesses a "fair proportion" of government contracts and sales of surplus property. Farm Credit often accepts SBA loan guarantees, such as the Payroll Protection Program (PPP) in 2021.

### Sole Proprietorship

The simplest and most common form of business structure in which one individual is in business by himself, contributing all the equity capital, taking all the risks, making all decisions, and taking all the profits or absorbing all the loss.

### Spec Home

A house built before it is sold. The builder speculates that he can sell it at a profit.

**See Also**

- Manufactured Home
- Mobile Home

### Special Flood Hazard Area (SFHA)

A land area identified by FEMA as having a significant risk of flooding, typically defined as areas with a 1% or greater annual chance of flooding (the 100-year floodplain), within which flood insurance is required for federally backed loans.

**See Also**

- Federal Emergency Management Agency (FEMA)

### Special Mention (SPM)

A credit classification applied to assets that are currently protected but exhibit potential weaknesses that warrant management attention. These assets present an undue or unwarranted level of credit risk, although not to the degree necessary for classification as substandard. Special Mention is used to identify emerging credit concerns and should not be applied as a compromise between adversely classified and non-adversely classified assets.

### Special Purpose Entity (SPE)

A legally separate entity created by an organization to isolate financial risk, hold specific assets, or facilitate securitization transactions, such that its assets and liabilities are distinct from those of the parent organization.

### Special Use Assets

Property that is appropriate for one use or a limited number of uses; an improved property that cannot be converted to another use without a large capital investment. Special use chattel properties are mobile and have very specific and limited use, such as tiling machines, potato diggers, and terracing machines.

### Specific Reserve (Spec Reserve)

The amount estimated to be a loss. This amount is recorded as a result of the classification process. When an actual charge-off is taken, this amount is reduced.

### Split Line of Credit

Loans to borrowers from different lenders that furnish portions of the short - and intermediate-term credit needs, possibly sharing collateral.

### Standard Appraisal Review Report (SARR)

A Standard Appraisal Review Report (SARR) is a formal, written document used by financial institutions and regulatory bodies to evaluate the quality, accuracy, and compliance of an existing appraisal report.

**See Also**

- Internal Appraisal Review

### Standard Industry Code (SIC)
[www.osha.gov/data/sic-manual](https://www.osha.gov/data/sic-manual)

Department of Labor codes for classifying businesses. Slowly being replaced by NAICS. May also be called "major ag code" in the AgriBank District due to reporting terminology.

**See Also**

- North American Industry Classification System (NAICS)

### Standard Industry Code Groups (SIC Groups)

Breakdown and groupings of Standard Industrial Classification (SIC) codes used to categorize agricultural and related businesses within AgriBank reporting systems. SIC codes are being gradually replaced by the North American Industry Classification System (NAICS). Also referred to as "Major Ag Code" within the AgriBank District.

**See Also**

- North American Industry Classification System (NAICS)
- Major Ag Code
- Standard Industry Code (SIC)

### Standards of Conduct (SOC)

The ethical rules and behavioral expectations established by the Farm Credit Administration and individual FCS institutions governing the professional conduct of directors, officers, and employees, including rules on conflicts of interest and insider transactions.

### State Equalized Value (SEV)

The assessed value of a property, as determined by the state, for taxation purposes. It is used in property tax calculations and is typically equal to 50% of the property's market value unless adjusted by state regulations.

### Statement Type

Type of Earnings Statement: Cash or Accrual

### Stock

To borrow from a Farm Credit association, the borrower must invest in the capital of the association. The investment can be in the form of stock or participation certificates. Borrowers are required to invest 2% of their outstanding principal loan balance or $1,000, whichever is less.

### Subject Property

As related to the appraisal function, the specific property being appraised.

### Subordination

A procedure by which one lender agrees that the lien position of its collateral is junior to that of another lender or lenders. In the case of default, creditors with subordinated lien positions are not paid until after more senior creditors are paid in full. Therefore, subordinated debt is more risky.

### Substandard Asset Quality

Assets that are inadequately protected by the borrower's current sound worth and paying capacity or of the collateral pledged, if any. Assets so classified must have a well-defined weakness or weaknesses that jeopardize the liquidation of the debt. They are characterized by the distinct possibility that the lender will sustain some loss if the deficiencies are not corrected. Loss potential, while existing in the aggregate amount of substandard loan assets, does not have to exist in individual loan assets.

### Substandard Nonviable (SNV)

A loan classification used in financial institutions, including the Farm Credit System (FCS), to categorize loans that are in poor condition with little to no chance of repayment. These loans have significant weaknesses that make full collection highly doubtful and may lead to losses for the lender.

### Substandard Viable (SV)

A loan classification used in financial institutions, including the Farm Credit System (FCS), to categorize loans that have identified weaknesses but still have a reasonable chance of repayment if the borrower's financial condition improves.

### Substantial Beneficial Interest (SBI)

A significant financial or ownership stake in an asset, business, or property, even if the individual does not hold direct legal title. It indicates that a person derives benefits (such as income, control, or influence) from the asset, despite it being registered under another name.

### Summary of Aggregated Deficiencies (SAD)

In the context of Internal Control over Financial Reporting (ICFR) and Sarbanes-Oxley (SOX) compliance, a Summary of Aggregated Deficiencies (SAD) is a master log or schedule used by auditors and management to track, categorize, and evaluate all control gaps identified during a testing cycle. The "Summary" aspect is a consolidated list of every deficiency found, while the "Aggregated" aspect refers to the critical process of looking at those deficiencies in groups to see if their combined impact creates a larger risk than each would individually.

**See Also**

- Internal Control Over Financial Reporting (ICFR)

### Summary of Unadjusted Differences (SUM)

An auditing document that accumulates and summarizes identified misstatements or differences between audited and recorded amounts that have not been corrected, used by auditors to evaluate the overall materiality of unadjusted items.

### SunStream
[www.sunstreamservices.com](https://www.sunstreamservices.com/)

SunStream Business Services is a third-party service provider delivering technology and operational services in support of AgriBank and Farm Credit Associations. It is a Farm Credit 4.25 service provider.

**See Also**

- FCS Service Corporation (4.25)

### Superfund Amendments Reauthorization Act (SARA)

A law enacted by Congress in 1986 to modify CERCLA. (See CERCLA.)

**See Also**

- Comprehensive Environmental Response Compensation and Liability Act (CERCLA)

### Syndication

A loan syndication (or "syndicated bank facility") is a large loan in which a group of banks work together to provide funds for a borrower. Usually one bank takes the lead, acting as an agent for all syndicate members and serving as the focal point between them and the borrower. All syndicate members are known at the outset to the borrower and they each have a contractual interest in the loan.

### Tax & Insurance (T/I)

The costs associated with property ownership, loans, and financial transactions, ensuring compliance with regulations and protection against risks. These expenses are often included in mortgage payments, loan agreements, and business financial planning.

### Tax and Insurance Escrow Balance (T/I Esc Bal)

The balance of Tax and Insurance Escrow funds collected from the customer but not yet disbursed for property taxes or insurance premiums. Maintained separately from principal and interest balances in the loan accounting system.

### Tax Deed

Deed given for land previously sold for taxes and not redeemed.

### Tax Sale

Sale of land for delinquent taxes.

### Taxpayer Identification Number (TIN)

Taxpayer Identification Number (TIN) is an identification number used by the Internal Revenue Service (IRS) in the administration of tax laws. It is issued either by the Social Security Administration (SSA) or by the IRS. A Social Security number (SSN) is issued by the SSA whereas all other TINs are issued by the IRS.

- Also referred to as: Tax Identification Number
- Used to track tax obligations, file returns, and conduct financial transactions

### Tenants by the Entireties

Interest created by conveyance to husband and wife who both have full interest in property and after the death of one, the survivor takes the whole. (A form of joint tenancy that exists in Arkansas, Kentucky, Michigan, Missouri, Illinois, Indiana, and Tennessee.)

### Tenants in Common

Interest in land held by two or more persons each having equal rights of possession and enjoyment, but without any right of survivorship between owners.

### Tenements

Anything on the land that is permanent, such as houses and other buildings.

### Term Transaction Lending

Individual lending transactions that generally result in limited credit exposure to a borrower. Each transaction results in a specific claim on a source of collateral or repayment. This may be collateral such as equipment securing a purchase transaction.

### Termination Statement

Used in conjunction with a financing statement, a signed statement by a secured party that no longer claims a security interest in the borrower's property under a certain financing statement, as identified by a filing number.

### Territorial Approval

Approval of Farm Credit System institutions providing similar financing that is required prior to closing for any loan where the headquarters and operations of the applicant are located partly outside the lender's territory, or the operation is located wholly outside of the lender's territory.

### Thomson File

A file containing Financial Institution information received monthly from Thomson Financial Publishing. Allows looking up bank names by routing number or vice versa.

### Throughput

The basic raw agricultural commodity processed and/or marketed in the processing and/or marketing activities of a farmer.

### Title Insurance Commitment

Report issued by title insurance company showing the condition of title and committing the title insurance company to issue a policy upon compliance with and satisfaction of the requirements set forth in the commitment.

### Title Opinion

Document prepared by an attorney that indicates the title holder to and any defects or encumbrances affecting the property in question. Usually based on examination of abstracts and/or Torrens certificates.

### Total Aggregate Liability

Borrower's total liability.

### Total Annual Capital Obligations (TACO)

The sum of all required financial commitments related to capital expenditures, debt repayments, and lease obligations that a business or individual must pay within a year. These obligations typically include loan principal and interest payments, lease payments, and other capital-related expenses.

### Total Annual Obligations (TAO)

The sum of a residential loan applicant's expenses and debt service requirements, typically calculated on an annual basis, including residential mortgage principal and interest, real estate taxes, mortgage insurance and home owner's insurance premiums; other scheduled debt service; other investments; and other obligations.

### Total Annual Obligations Ratio (TAO Ratio)

Also referred to as a payment ratio. The sum of the applicant's debt service requirements, typically calculated on a monthly basis, divided by total gross income for the respective period. It is a relative measure of an applicant's total debt payments to gross income. A commonly used benchmark is that total obligations should not exceed 36% of gross income.

### Total Assets (TA)

The sum of all resources owned by an individual, business, or financial institution that have economic value and can be converted into cash. It includes both short-term (current) and long-term (fixed) assets.

### Total Capital Ratio (TCR)

A regulatory capital measure that expresses an institution's total qualifying capital (Tier 1 plus Tier 2) as a percentage of its risk-weighted assets, used to assess overall capital adequacy.

### Total Farm Expenses

Total Farm Operating Expenses plus or minus expense accrual adjustment

### Total Gross Income (TGI)

The sum of a residential loan applicant's sources of income, typically calculated on a monthly basis, including salary, wages or self employment income; average commission; overtime pay; bonuses; net rental income; net farm income; and other income such as dividends and interest.

### Total Legal Obligations (TLO)

The total amount owed by a borrower on a loan. TLO consists of current principal balance, including borrower stock or participation certificates; total interest due; late payment charges; and other charges.

### Total Liabilities

Total liabilities of the customer (Current Liabilities plus Intermediate Term Liabilities plus Long Term Liabilities)

**See Also**

- Current Liabilities (CL)
- Long Term (Assets) (LTA)

### Total Monthly Obligations (TMO)

Calculated by taking the PITI calculated amount and adding in all other monthly debt payments the borrower is obligated to pay. The total of all monthly payments (including PITI) is then divided by the total gross monthly income of the borrower(s). The standard for this measurement is 36%.

**See Also**

- Principal, Interest, Taxes and Insurance (PITI)

### Total Monthly Payment to Gross Monthly Income (TMP/GMI)

A financial metric used by lenders to assess a borrower's ability to afford loan payments. It measures the percentage of a borrower's gross monthly income that goes toward monthly debt obligations, including principal, interest, taxes, and insurance (PITI).

**See Also**

- Principal, Interest, Taxes and Insurance (PITI)

### Total Times Past Due

Number of times the loan was past due.

### Total Weighted Production (TWP)

In agricultural circles, Total Weighted Production (TWP) is most commonly used in Ag Lending and Farm Productivity Analysis. It is a metric designed to normalize the output of a diversified farm into a single, comparable value. Because a farm may produce vastly different commodities (e.g., bushels of corn, tons of silage, and hundredweights of milk), the TWP allows lenders and farm managers to assess the total "earning power" or productivity of the land using a common denominator.

### Total Yearly Obligations (TYO)

The sum of all financial commitments that an individual or business must pay within a year. These obligations typically include loan payments, lease payments, insurance, taxes, and other fixed financial responsibilities.

### Toxic Substance Control Act (TSCA)
[www.epa.gov/laws-regulations/summary-toxic-substances-control-act](https://www.epa.gov/laws-regulations/summary-toxic-substances-control-act)

A law enacted by Congress to regulate the manufacture and distribution of chemical substances that may present an unreasonable risk of injury to health or the environment. It establishes handling procedures encompassing most agricultural chemicals.

### Trade Name

A trade name, also known as a business name, is a name different from its legal name that an individual, partnership, or corporation uses to conduct business.

### Transaction Gathering System (TG)

A financial data collection and processing system used by banks, financial institutions, and organizations like the Farm Credit System (FCS) to capture, track, and process financial transactions efficiently.

### Transaction Management (TM)

AgriBank-owned application providing one convenient tool to view and manage ACH and credit line draft processing. For ACH transactions, TM monitors for accuracy and adherence to NACHA rules in addition to fraud mitigation tools on received and originated transactions. In situations where borrowers upload NACHA files, TM mitigates fraud risk by pre-screening customers for approval prior to originating transactions. TM is being replaced by TG.

**See Also**

- Automated Clearing House (ACH)

### Treasury Index

An index that is used to determine interest rate changes for certain adjustable rate mortgage (ARM) plans. It is based on the results of auctions that the U.S. Treasury holds for its Treasury bills and securities or is derived from the U.S. Treasury's daily yield curve, which is based on the closing market bid yields on actively traded Treasury securities in the over-the counter market.

**See Also**

- Adjustable Rate Mortgage (ARM)

### True Lease

A transaction that qualifies as a lease under the Internal Revenue Code so the lessee can claim rental payments as tax deductions and the lessor can claim tax benefits of ownership such as depreciation.

### Trust

A property interest held by one individual for the benefit of another. This interest creates a fiduciary relationship between trustee and beneficiaries.

### Trustee

A person or entity in whom legal title to property is vested in trust for the benefit of another; the person charged with the proper administration of property or funds in accordance with the wishes of the trustor.

### Truth-in-Lending (TIL)

Federal regulations requiring all pertinent facts regarding a loan to be clearly disclosed and made clear to the borrower by way of special forms. Regulations also provide the borrower the right to rescind. Also known as Regulation Z.

### Unallocated Retained Earnings (URE)

Earnings retained by a Farm Credit institution that have not been distributed as patronage or allocated to member capital accounts, representing a component of permanent capital available to absorb losses.

### Unallocated Retained Earnings Equivalent (UREE)

A capital component in Farm Credit System accounting that represents amounts functionally equivalent to unallocated retained earnings, used in regulatory capital calculations for institutions with specific ownership structures.

### Unamortized Loan

Loan that has no regular principal payments until the final maturity date, when the full principal amount is due.

### Undersecured

The collateral condition of any loan that does not meet the definition of "adequately secured."

### Underwriting

The decision whether to make a loan to a potential borrower based on credit, employment, assets, and other factors and the matching of this risk to an appropriate rate and term or loan amount.

### Unharvested (UH)

Crops that have been planted but not yet gathered or harvested. This can have financial and risk management implications in agricultural lending, crop insurance, and farm financial planning.

### Unified Call Report

aka "call reports." The Uniform Call Report (UCR) is a comprehensive quarterly financial and statistical statement that all Farm Credit System (FCS) institutions are required to file with the Farm Credit Administration (FCA). It serves as the primary regulatory tool for monitoring the safety and soundness of the System. Much like the "Call Reports" filed by commercial banks with the FDIC, the UCR provides a standardized "snapshot" of an institution's financial health, risk profile, and operational performance.

**See Also**

- Federal Deposit Insurance Corporation (FDIC)
- Farm Credit Administration (FCA)

### Uniform Agricultural Appraisal Report (UAAR)

A standardized property appraisal document used to evaluate the value of agricultural land, farms, and rural properties. It is commonly used by lenders, such as those in the Farm Credit System (FCS), to assess collateral value for loans.

### Uniform Classification System (UCS)
[ww3.fca.gov/readingrm/exammanual/General%20Guidance/Classifying%20Assets%20Using%20the%20UCS.pdf](https://ww3.fca.gov/readingrm/exammanual/General%20Guidance/Classifying%20Assets%20Using%20the%20UCS.pdf)

The standardized credit classification system used across the Farm Credit System to categorize loan assets by risk level into five categories: Acceptable, Other Assets Especially Mentioned, Substandard, Doubtful, and Loss.

**See Also**

- Other Assets Especially Mentioned (asset classification) (OAEM)

### Uniform Classification System Credit Classification (UCS Credit Classification)

The standardized credit classification system predominantly used by Farm Credit System institutions to express the degree of risk of nonpayment in individual assets. UCS classifications are assigned on the basis of risk and include five categories: Acceptable, Other Assets Especially Mentioned (OAEM), Substandard, Doubtful, and Loss. Assets classified Substandard, Doubtful, and Loss are considered adversely classified; assets classified less than fully Acceptable are considered criticized. Assets may be assigned more than one classification when portions clearly meet different standards.

**See Also**

- Other Assets Especially Mentioned (asset classification) (OAEM)
- Uniform Classification System (UCS)

### Uniform Commercial Code (UCC)

Collection of laws dealing with various commercial business topics. Article 9 of the UCC deals with security interests in personal property collateral.

### Uniform Commercial Code - Amendment (UCC-A)

A filing used to modify a previously filed UCC financing statement, such as to update collateral descriptions, change party information, or extend the effectiveness of the original filing.

**See Also**

- Uniform Commercial Code (UCC)

### Uniform Loan Activity Report (ULAR)

The Uniform Loan Activity Report (ULAR) is a standardized data reporting format historically used by the Farm Credit Administration (FCA) and individual Farm Credit System (FCS) institutions to track and reconcile loan-level transactions. Replaced by the Uniform Call Report.

**See Also**

- Farm Credit Administration (FCA)

### Uniform Standards of Professional Appraisal Practice (USPAP)

The authoritative standards governing the ethical and competent practice of appraisal in the United States, developed and maintained by The Appraisal Foundation and required for state-licensed and state-certified appraisers.

### United States Department of Agriculture (USDA)
[www.usda.gov](https://www.usda.gov/)

The USDA was originally established in 1862 and raised to cabinet status in 1889. Farm Credit often originates loans with FSA guarantees (FSA is a department of the USDA).

**See Also**

- Farm Services Agency (FSA)

### Unpledged Collateral

Value of the collateral that isn't pledged.

### User Defined Field (UDF)

aka "user field." A customizable data field within a software system that allows users or administrators to capture institution-specific or loan-specific information not accommodated by standard system fields. A brilliant architectural escape hatch or a thorn in the side of system integrators everywhere, depending on your viewpoint.

### Validation

In credit scoring, a procedure comparing the rank ordering of the quality of accepted accounts to the rank ordering predicted by the system at development time. The scoring system remains valid if the rank orderings remain substantially the same.

### Valuation

The process of estimating a defined value of an identified interest or interests in a specific property or properties as of a given date.

### Value in Use

The value a specific property has for a specific use. This may be a valid substitute for "Market Value" when the current use is so specialized that it has no demonstrable market and when the use is economic and likely to continue.

**See Also**

- Market Value (MV)

### Value of Farm Production (VFP)

The dollar value of farm production, including that sold as well as inventory changes. VFP is the gross revenue of an operation less purchases of assets included in the calculation of gross revenues. Deductions from gross revenue to determine VFP include cost of purchased feed/grain and purchased livestock/poultry for resale.

### Variable Rate

An interest rate that will vary over the term of the loan.

### Variable Rate Mortgage

Mortgage containing a clause stating that interest may vary upward or downward during the life of the mortgage.

### Verification of Deposit (VOD)

A document signed by the borrower's financial institution verifying the status and balance of his/her financial accounts.

### Verification of Employment (VOE)

A document signed by the borrower's employer verifying his/her position and salary.

### Vertical Asset Pool (VAP)

An AgriBank asset pool program in which Associations contribute loan assets into a pooled structure held by AgriBank, with resulting asset-pool accounting records and balance movements reflected in District DB.

### Viable Loan

A loan to a borrower whose business operation is reasonably expected to be able to meet all operating expenses (including depreciation and/or a reasonable allowance for capital expenditures necessary to operations), to service all debt on a timely basis and to provide for personal living expenses.

### Weighted Average Life (WAL)

The average length of time until the principal of a debt security is expected to be repaid, weighted by the proportion of total principal repaid at each payment date, used to assess the duration and reinvestment risk of fixed-income instruments.

### Wholesale (Direct Notes)

District Associations borrow from AgriBank in order for district associations to lend for their customers. In order to loan to the farmers, AgriBank has to provide funding to district associations.

### Wholesale Fees

Fees charged to associations based on loan changes and wholesale product rules. (Pre-payment fee, Conversion Fee, Cancellation Fee, Undispersed fee)

### Wholesale Loan Rate

All-in rate charged by AgriBank to an institution, comprised of marginal cost of debt plus risk differential plus bank spread.

### Wholesale Pricing

The MCD AgriBank assigns and/or updated to wholesale products every day, along with rates some products are indexed to.

**See Also**

- Marginal Cost of Debt (MCD)

### Wholesale Product

Defines the attributes and pricing of wholesale financial products offered by AgriBank to associations, including rate schedules and daily pricing updates.

### Wire

A secure electronic transfer of funds between financial institutions used for loan disbursements, payments, and other financial transactions. Wire transfers provide fast, reliable, and real-time movement of funds for FCS institutions, borrowers, and business partners. AgriBank does this internally for AgriBank, associations, and borrowers.

### Work Down Credit

A loan that is not performing satisfactorily and for which a conscious decision has been made to reduce the risk exposure by working down the amount of financing provided.

### Working Capital

Current assets less current liabilities. Working capital is a measure of liquidity. Working capital provides the borrower a margin for operating loans and ability to with stand short-term adversity. The amount of working capital considered adequate is related to the size of the farm business.

### Working Capital Deficiency (WC Deficiency)

The difference between the working capital target and the current working capital position. This difference, if greater than zero, is divided by four and included in total demands on capital debt repayment capacity as if a working capital loan were made to correct the liquidity position. See also Working Capital Deficiency.

**See Also**

- Working Capital

### Working Capital Needs

The difference between working capital target and current working capital position, if greater than zero.

### Working Capital Target

The level of working capital considered to be appropriate for a borrower's operation. This determination is based on consideration of factors including stability of the earnings stream, frequency of inventory turnover, and peak level of current liabilities.

### Working Capital to Average Gross Income (WC/AGI)

Working Capital divided by Average Gross Income. A core underwriting standard and relative measure indicating the adequacy of working capital compared to the size of the business.

**See Also**

- Average Gross Income (AGI)
- Working Capital

### Workout Credit

A loan that is not performing satisfactorily and for which a conscious decision has been made to put in place one or more loan servicing actions or controls. These actions have specified time frames, so a borrower can work out of the present problem or refinance with another lender.

### Year Base

360 Actual 360 Days Calculates interest using the actual number of days in each month but assumes a year of 360 days. 365/366 Actual Days Refers to a day count convention used in financial calculations, specifically in the context of interest accrual. This method accounts for the actual number of days in a period, whether it's a regular year (365 days) or a leap year (366 days). Used to determine how interest is calculated, particularly in loans and investments. 30 Day Months A 30/360 interest calculation, each month is assumed to have 30 days, and a year is considered to have 360 days. This method is often used for corporate bonds and loan documents, and it simplifies the calculation by treating all months equally.

### Year Began Farming (YBF)

the year the individual or entity began farming operations, e.g., 1990.

### Year-over-Year Actual (Y/Y Actual)

Year-over-year comparison of actual performance, showing the absolute dollar or unit change from the same period in the prior year.

### Year-over-Year Actual Percent (Y/Y Actual%)

Year-over-year percentage change in actual performance, calculated as (Current Period − Prior Period) / Prior Period × 100.

### Young, Beginning or Small Farmer (YBS)

Young, Beginning, or Small farmers based on the following FCA criteria:

- **Young** - If the age of the borrower on the loan at the time the loan/lease was originated or renewed is equal to or less than 35 years, the loan/lease qualifies for Young farmer status.
- **Beginning** - If the length of time in farming for any borrower on the loan at the time the loan/lease was originated or renewed is equal to or less than 10 years, the loan/lease qualifies for Beginning farmer status.
- **Small** - If the most recent earnings statement at the time the loan/lease was originated or renewed shows gross farm income less than $250,000, the loan/lease qualifies for Small farmer status.

**See Also**

- Farm Credit Administration (FCA)
- Year Began Farming (YBF)

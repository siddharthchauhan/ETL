---
name: sdtm-mapping
description: Convert raw clinical trial data to SDTM (Study Data Tabulation Model) format following CDISC standards for regulatory submissions.
---

```markdown
# SDTM Mapping Skill

Convert raw clinical trial data to SDTM (Study Data Tabulation Model) format following CDISC standards for regulatory submissions.

## Quick Reference: Essential Documents

| Document | Purpose | Source |
|----------|---------|--------|
| SDTM IG 3.4 | Implementation Guide - domain structures | [CDISC Library](https://www.cdisc.org/standards/foundational/sdtm) |
| SDTMIG-MD | Medical Devices supplement | CDISC Library |
| CDASH | Source data collection standards | CDISC Library |
| CT (Controlled Terminology) | Standardized code lists | [NCI EVS](https://evs.nci.nih.gov/ftp1/CDISC/) |
| FDA Data Standards Catalog | Required standards per study type | [FDA.gov](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/data-standards-catalog) |
| Define-XML 2.1 | Metadata specification | CDISC Library |
| Validation Rules | Pinnacle 21 / OpenCDISC rules | Pinnacle 21 Community |

## Domain Reference Files

Read these files based on domain class needed:

| Domain Class | Reference File | Common Domains |
|--------------|----------------|----------------|
| Special Purpose | [references/special-purpose.md](references/special-purpose.md) | DM, CO, SE, SV |
| Interventions | [references/interventions.md](references/interventions.md) | CM, EX, EC, SU |
| Events | [references/events.md](references/events.md) | AE, DS, MH, CE, DV |
| Findings | [references/findings.md](references/findings.md) | LB, VS, EG, PE, QS, SC |
| Trial Design | [references/trial-design.md](references/trial-design.md) | TA, TE, TI, TS, TV, TD |
| Relationship | [references/relationships.md](references/relationships.md) | RELREC, SUPP--, CO |
| Associated Persons | [references/associated-persons.md](references/associated-persons.md) | APXX domains |

## End-to-End SDTM Conversion Process

### Phase 1: Study Setup & Planning

**1.1 Gather Source Documentation**
- Protocol (study design, visits, assessments)
- Annotated CRF (aCRF) or blank CRF
- Data transfer specifications
- Lab specifications and units
- External data specifications (ECG, PK, etc.)

**1.2 Determine Required Domains**
```
Standard Domains (most studies):
├── DM (Demographics) - ALWAYS REQUIRED
├── EX (Exposure) - Expected if investigational product administered
├── AE (Adverse Events) - Expected for safety studies (nearly universal)
├── CM (Concomitant Medications) - Expected if collected
├── MH (Medical History) - Expected if collected
├── DS (Disposition) - Expected (required for subject accountability)
├── LB (Laboratory Tests) - Expected if performed
├── VS (Vital Signs) - Expected if collected
├── EG (ECG) - Expected if performed
├── SV (Subject Visits) - Expected if visit-level data exists
├── SE (Subject Elements) - Expected for multi-period studies
└── SC (Subject Characteristics) - Expected if non-demographic characteristics collected

Trial Design (all studies):
├── TA (Trial Arms) - REQUIRED
├── TE (Trial Elements) - REQUIRED
├── TI (Trial Inclusion/Exclusion) - REQUIRED
├── TS (Trial Summary) - REQUIRED
├── TV (Trial Visits) - REQUIRED
└── TD (Trial Disease Assessments) - Expected if disease response criteria collected
```

**1.3 Obtain Controlled Terminology**
- Download latest CT package from NCI EVS
- Map sponsor terms to CDISC CT
- Document non-standard terms requiring extensible CT
- Note: CT is updated quarterly; use version appropriate for study start

### Phase 2: Mapping Specification Development

**2.1 Create Annotated CRF**
Map each CRF field to SDTM variable:
- Domain name
- Variable name
- Controlled terminology codelist
- Derivation logic (if applicable)

**2.2 Develop Domain Mapping Specifications**
For each domain, document → See [references/mapping-spec-template.md](references/mapping-spec-template.md):

| Source | Target Variable | Rule | CT Codelist |
|--------|-----------------|------|-------------|
| RAW.FIELD | XX.VARIABLE | Direct/Derived | C12345 |

**2.3 Standard Variable Derivations**

**Timing Variables (--DTC, --DY, --STDY, --ENDY):**
```
--DTC: ISO 8601 format (YYYY-MM-DDTHH:MM:SS)
       Partial dates allowed: YYYY-MM-DD, YYYY-MM, YYYY
       Time portion optional: include only if collected

--DY (Study Day) Derivation:
  If --DTC >= RFSTDTC: --DY = (--DTC date - RFSTDTC date) + 1
  If --DTC < RFSTDTC:  --DY = (--DTC date - RFSTDTC date)
  
  CRITICAL: Day 0 does not exist
  - Day -1 is the day before first dose
  - Day 1 is the day of first dose
  - Example: RFSTDTC = 2024-01-15
    • 2024-01-14 → Day -1
    • 2024-01-15 → Day 1
    • 2024-01-16 → Day 2

--STDY: Same logic as --DY using start date
--ENDY: Same logic as --DY using end date
```

**Sequence Variables (--SEQ):**
```
Sequential integer within subject per domain
Order by: --STDTC, --STDY, or logical order
Must be unique within USUBJID + Domain
Starts at 1 for each subject in each domain
No gaps in sequence (1, 2, 3... not 1, 3, 5)
```

**USUBJID:**
```
STUDYID + "-" + SITEID + "-" + SUBJID
Example: ABC-123-001-0001
Must be unique across entire submission
Must be consistent across all domains
Length and format should be consistent
```

**EPOCH Derivation:**
```
EPOCH: Trial period name derived from SE domain
- Maps to TE.ELEMENT via SE.ETCD
- Required when subject moves through defined trial periods
- Values from Trial Design: "SCREENING", "TREATMENT", "FOLLOW-UP"
- Must be consistent with TA (Trial Arms) and TE (Trial Elements)
- Derived based on --DTC relative to SE.SESTDTC/SE.SEENDTC
```

**VISITNUM Assignment:**
```
VISITNUM: Numeric version of planned visit
- Sequential integer for planned visits (1, 2, 3...)
- Unplanned visits: Use decimal convention (e.g., 2.1 for unplanned between V2 and V3)
- Must align with TV (Trial Visits) domain
- VISIT: Character description matching TV.VISIT
- VISITDY: Planned study day of visit from TV.VISITDY
```

**--BLFL (Baseline Flag) Derivation:**
```
--BLFL: Last non-missing value before or on RFSTDTC
- Set to "Y" for baseline record; null otherwise (not "N")
- Selection criteria defined per protocol/SAP
- Only one baseline per parameter per subject
- Algorithm: MAX(--DTC) WHERE --DTC <= RFSTDTC AND --STAT ≠ "NOT DONE"
- For LB: Consider LBTPT (timepoint) in selection
- Document baseline definition in define.xml
```

### Phase 3: Programming & Transformation

**3.1 Standard Programming Workflow**
```
1. Read raw/source data
2. Apply selection criteria (screen failures, randomized subjects, etc.)
3. Map to SDTM variables
4. Apply controlled terminology
5. Derive calculated variables (--SEQ, --DY, EPOCH, etc.)
6. Assign VISITNUM/VISIT based on TV domain
7. Sort per IG specification
8. Apply dataset attributes (labels, lengths)
9. Run pre-output validation checks
10. Output as XPT (SAS Transport v5)
```

**3.2 Dataset Requirements**
```
Structure:
- Maximum 200 variables per dataset
- Variable labels ≤40 characters
- Variable names ≤8 characters
- Character variable lengths defined per IG specification
- Most variables: ≤200 characters
- Lengths should match actual data (not padded excessively)
- Sort order documented in define.xml

Format:
- SAS Transport v5 (.xpt) format required
- One record per observation
- No duplicate records (same key variables)
- Dataset names lowercase (dm.xpt, ae.xpt)
```

**3.3 SUPPQUAL Handling**
Non-standard variables go to SUPP-- domains:

| Variable | Description | Required |
|----------|-------------|----------|
| STUDYID | Study Identifier | Yes |
| RDOMAIN | Related Domain | Yes |
| USUBJID | Unique Subject ID | Yes |
| IDVAR | Identifying Variable (e.g., "AESEQ") | Yes |
| IDVARVAL | Value of IDVAR | Yes |
| QNAM | Qualifier Variable Name (≤8 chars) | Yes |
| QLABEL | Qualifier Variable Label (≤40 chars) | Yes |
| QVAL | Data Value | Yes |
| QORIG | Origin (CRF, DERIVED, ASSIGNED) | Yes |
| QEVAL | Evaluator (if applicable) | Conditional |

**3.4 RELREC Domain Usage**
Used to link related records across domains:

| STUDYID | RDOMAIN | USUBJID | IDVAR | IDVARVAL | RELTYPE | RELID |
|---------|---------|---------|-------|----------|---------|-------|
| Study1 | AE | SUBJ001 | AESEQ | 1 | ONE | REL01 |
| Study1 | CM | SUBJ001 | CMSEQ | 3 | ONE | REL01 |

Common relationships:
- AE to CM (medication given for AE)
- AE to LB (lab confirming AE)
- CM to MH (medication for pre-existing condition)
- PE to EG (ECG finding related to physical exam)
- FA to parent domain (findings about specific records)

RELTYPE values: ONE (1:1), MANY (1:many)

### Phase 4: Quality Control & Validation

**4.1 Run Pinnacle 21 Validation**
```bash
# Standard validation command
p21 validate --data /path/to/datasets --define define.xml --version 3.4

# Check for:
# - SD (SDTM Domain) rules
# - CT (Controlled Terminology) compliance
# - Define.xml consistency
# - Cross-domain consistency
```

**4.2 Validation Categories**
| Category | Description | Action |
|----------|-------------|--------|
| Error | Blocks submission | Must fix |
| Warning | Potential issue | Evaluate, document if acceptable |
| Notice | Informational | Review |

**4.3 High-Priority Validation Rules (Pinnacle 21)**

| Rule ID | Domain | Issue | Resolution |
|---------|--------|-------|------------|
| SD0083 | All | Missing --SEQ | Ensure unique sequential numbering |
| SD1001 | DM | Missing RFSTDTC | Must have reference start date for treated subjects |
| SD0028 | DM | USUBJID not unique | Check concatenation logic |
| SD1015 | AE | AESTDTC after AEENDTC | Verify date logic |
| SD0026 | All | --SEQ not unique within USUBJID | Reset sequence per subject |
| SD1020 | DS | Invalid DSDECOD | Must use CT value from NCOMPLT codelist |
| CT2001 | All | Invalid CT value | Map to published terminology |
| DD0006 | All | --DTC format invalid | Use ISO 8601: YYYY-MM-DDTHH:MM:SS |
| SD1002 | DM | RFENDTC before RFSTDTC | Check reference date logic |
| SD0070 | All | Invalid --STAT value | Only "NOT DONE" allowed |

**4.4 Common Validation Issues**
See [references/common-issues.md](references/common-issues.md) for resolution guidance.

### Phase 5: Documentation & Submission

**5.1 Create Define.xml**
Metadata document describing all datasets:
- Dataset definitions (name, label, structure, class)
- Variable definitions with origins (CRF, Derived, Assigned, Protocol)
- Controlled terminology references (codelist OID, NCIt codes)
- Computational methods (derivation algorithms)
- Comments and annotations
- Value-level metadata where applicable

**5.2 Reviewer's Guide (cSDRG)**
- Study design overview
- Subject disposition summary
- Protocol deviations affecting data
- Non-standard mappings rationale
- SUPPQUAL justifications
- Controlled terminology extensions
- Split domain explanations
- Known issues for reviewer attention
- Validation report summary

**5.3 Submission Package Structure**
```
/submission
├── /m5
│   └── /datasets
│       └── /study-id
│           ├── /tabulations
│           │   └── /sdtm
│           │       ├── define.xml
│           │       ├── define2-1.xsl (stylesheet)
│           │       ├── dm.xpt
│           │       ├── ae.xpt
│           │       ├── suppdm.xpt
│           │       ├── suppae.xpt
│           │       ├── relrec.xpt
│           │       ├── ta.xpt
│           │       ├── te.xpt
│           │       ├── ti.xpt
│           │       ├── ts.xpt
│           │       ├── tv.xpt
│           │       └── [other domains].xpt
│           └── /analysis
│               └── /adam
│                   └── [ADaM datasets]
└── /util
    └── /style
        └── define2-1.xsl
```

## Domain Selection Quick Reference

| Data Type | Primary Domain | Key Identifier | Notes |
|-----------|---------------|----------------|-------|
| Drug administered by sponsor | EX (Exposure) | EXTRT | Investigational product as given |
| Drug administered per protocol | EC (Exposure as Collected) | ECTRT | What site recorded |
| Prior/concomitant meds | CM | CMTRT | Non-study medications |
| Medical history | MH | MHTERM | Pre-existing conditions |
| Adverse events | AE | AETERM | Verbatim term required |
| Lab results | LB | LBTESTCD | One record per test per timepoint |
| Vital signs | VS | VSTESTCD | Standard tests: SYSBP, DIABP, PULSE, etc. |
| ECG findings | EG | EGTESTCD | Machine-read and interpreted |
| Physical exam | PE | PETESTCD | By body system |
| Subject characteristics | SC | SCTESTCD | Non-demographic subject data |
| Questionnaire responses | QS | QSTESTCD | PRO/QoL instruments |
| Substance use | SU | SUTRT | Tobacco, alcohol, recreational drugs |
| Disease milestones/events | CE (Clinical Events) | CETERM | Disease-related events |
| Protocol deviations | DV | DVTERM | From deviation log |
| Tumor measurements | TU | TULOC | Oncology studies |
| Tumor response | RS | RSTEST | Oncology studies |
| PK concentrations | PC | PCTESTCD | Pharmacokinetic samples |
| PK parameters | PP | PPCAT | Derived PK parameters |

## Workflow Summary

```
┌──────────────────────────────────────────────────────────────────┐
│                     SDTM CONVERSION WORKFLOW                      │
└──────────────────────────────────────────────────────────────────┘

    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │   Protocol  │     │   Raw Data  │     │     CRF     │
    │   + Design  │     │   Sources   │     │  Annotation │
    └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
           │                   │                   │
           └───────────────────┼───────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │  Mapping            │
                    │  Specification      │
                    │  Development        │
                    └──────────┬──────────┘
                               │
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │   Apply     │     │   Derive    │     │   Apply     │
    │   CT        │     │   Variables │     │   Business  │
    │   Terms     │     │   --SEQ,DY  │     │   Rules     │
    └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
           │                   │                   │
           └───────────────────┼───────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │   SDTM Datasets     │
                    │   (.xpt format)     │
                    └──────────┬──────────┘
                               │
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │  Pinnacle   │     │  Define.xml │     │  Reviewer's │
    │  21 QC      │     │  Creation   │     │  Guide      │
    └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
           │                   │                   │
           └───────────────────┼───────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │   SUBMISSION        │
                    │   PACKAGE           │
                    └─────────────────────┘
```

## Commands & Scripts

```bash
# Validate SDTM datasets
python scripts/validate_sdtm.py --path /data/sdtm --ig 3.4

# Generate mapping spec template
python scripts/generate_mapping_template.py --domain DM --output dm_spec.xlsx

# Check CT compliance
python scripts/check_ct.py --dataset ae.xpt --version 2024-03-29

# Create define.xml shell
python scripts/create_define_shell.py --domains "DM,AE,CM,LB" --output define.xml

# Cross-domain consistency check
python scripts/cross_domain_check.py --path /data/sdtm --checks usubjid,dates,visits
```

## Quick Decision Guide

**Q: Which domain for this data?**
→ See Domain Selection Quick Reference above or [references/domain-selection.md](references/domain-selection.md)

**Q: Is this variable required?**
→ Check SDTM IG domain specification:
  - Required: Must be present, must have value
  - Expected: Must be present if data collected
  - Permissible: Include if useful for analysis

**Q: Should this be SUPP-- or custom domain?**
→ Use SUPP-- when:
  - Data is truly supplementary/qualifier to parent domain records
  - Non-standard variables don't fit existing domain structure
  - Data represents additional attributes, not independent observations
→ Use custom domain when:
  - Data represents distinct, structured, recurring observations
  - Information has its own timing/sequence independent of parent
  - A standard domain structure (Findings/Events/Interventions) fits
→ Decision factors: Data structure, reviewer findability, logical relationship to parent

**Q: How to handle missing dates?**
→ Use partial date format per ISO 8601:
  - Full date known: "2024-06-15"
  - Month/year known: "2024-06"
  - Year only known: "2024"
  - Document handling in define.xml
  - Consider imputation for ADaM (not SDTM)

**Q: Controlled terminology doesn't have my term?**
→ Check if codelist is extensible (CT specification indicates this)
  - If extensible: Use sponsor term, document in define.xml
  - If not extensible: Must use existing CT value
  - Request new term via CDISC CT submission process for future studies

**Q: How to handle multiple values for single variable?**
→ Options depending on data:
  - Multiple records (preferred if truly separate observations)
  - --MODIFY variable for modified/coded version
  - SUPP-- for additional qualifiers
  - Never concatenate with delimiters

**Q: When to split a domain?**
→ Split when:
  - Data comes from different sponsors/sources (e.g., AE vs. SUPPAE)
  - Logical separation needed (e.g., LB split by lab vendor)
  - Different collection methods
→ Document split rationale in cSDRG

## Regulatory Agency Specifics

| Agency | Key Requirements |
|--------|-----------------|
| FDA | Per FDA Data Standards Catalog (verify current version); SDTM IG 3.3+ for most new submissions; Define-XML 2.0 minimum, 2.1 recommended; Pinnacle 21 Community validation expected; Study Data Standardization Plan (SDSP) recommended |
| PMDA | SDTM required; Japanese CT extensions may apply; eCTD format; JP-specific guidance documents |
| EMA | SDTM strongly recommended (effectively required for new MAAs); Define-XML required; EMA-specific validation rules |
| Health Canada | Generally follows FDA standards; verify current HC guidance |
| TGA (Australia) | Follows ICH guidelines; SDTM accepted |
| NMPA (China) | SDTM accepted; local guidance emerging |

**Note:** Always verify current requirements:
- FDA: https://www.fda.gov/industry/fda-data-standards-advisory-board
- Data Standards Catalog updated periodically
- CDISC: https://www.cdisc.org/standards

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-01 | Initial version |
| 1.1 | 2024-XX | Added EPOCH, VISITNUM, BLFL derivations; Enhanced validation rules; Added RELREC guidance; Updated regulatory requirements |
```

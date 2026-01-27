---
name: sdtm-mapping
description: "End-to-end SDTM (Study Data Tabulation Model) conversion from raw clinical data. Supports all SDTM domain classes: Interventions, Events, Findings, Special Purpose, Trial Design, Relationship, and Associated Persons. Use when converting raw/source data to SDTM format, creating mapping specifications, validating SDTM datasets, or reviewing CDISC compliance. Aligned with SDTM IG 3.4, SDTMIG-MD 1.2, CDASH, and FDA/PMDA/EMA submission requirements. MANDATORY TRIGGERS: SDTM, CDISC, clinical data mapping, raw to SDTM, domain mapping, submission datasets, define.xml, controlled terminology, Study Data Standards."
---

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
| Trial Design | [references/trial-design.md](references/trial-design.md) | TA, TE, TI, TS, TV |
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
├── DM (Demographics) - REQUIRED
├── EX (Exposure) - if investigational product
├── AE (Adverse Events) - REQUIRED for safety
├── CM (Concomitant Medications)
├── MH (Medical History)
├── DS (Disposition) - REQUIRED
├── LB (Laboratory Tests)
├── VS (Vital Signs)
├── EG (ECG)
└── SV (Subject Visits) - REQUIRED

Trial Design (all studies):
├── TA (Trial Arms)
├── TE (Trial Elements)
├── TI (Trial Inclusion/Exclusion)
├── TS (Trial Summary)
└── TV (Trial Visits)
```

**1.3 Obtain Controlled Terminology**
- Download latest CT package from NCI EVS
- Map sponsor terms to CDISC CT
- Document non-standard terms requiring extensible CT

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
--DY: (--DTC - RFSTDTC) + 1 if --DTC >= RFSTDTC
      (--DTC - RFSTDTC) if --DTC < RFSTDTC
--STDY: Same logic using start date
--ENDY: Same logic using end date
```

**Sequence Variables (--SEQ):**
```
Sequential integer within subject per domain
Order by: --STDTC, --STDY, or logical order
Must be unique within USUBJID + Domain
```

**USUBJID:**
```
STUDYID + "-" + SITEID + "-" + SUBJID
Example: ABC-123-001-0001
Must be unique across entire submission
```

### Phase 3: Programming & Transformation

**3.1 Standard Programming Workflow**
```
1. Read raw/source data
2. Apply selection criteria
3. Map to SDTM variables
4. Apply controlled terminology
5. Derive calculated variables
6. Sort and sequence
7. Apply dataset attributes
8. Output as XPT (SAS Transport v5)
```

**3.2 Dataset Requirements**
- Maximum 200 variables per dataset
- Variable labels ≤40 characters
- Variable names ≤8 characters
- Character variables ≤200 characters (or 8000 for --VAL)
- Sort order documented in define.xml

**3.3 SUPPQUAL Handling**
Non-standard variables go to SUPP-- domains:
```
STUDYID, RDOMAIN, USUBJID, IDVAR, IDVARVAL, QNAM, QLABEL, QVAL, QORIG, QEVAL
```

### Phase 4: Quality Control & Validation

**4.1 Run Pinnacle 21 Validation**
```bash
# Standard validation command
p21 validate --data /path/to/datasets --define define.xml --version 3.4

# Check for:
# - SD (SDTM Domain) rules
# - CT (Controlled Terminology) compliance
# - Define.xml consistency
```

**4.2 Validation Categories**
| Category | Description | Action |
|----------|-------------|--------|
| Error | Blocks submission | Must fix |
| Warning | Potential issue | Evaluate, document if acceptable |
| Notice | Informational | Review |

**4.3 Common Validation Issues**
See [references/common-issues.md](references/common-issues.md) for resolution guidance.

### Phase 5: Documentation & Submission

**5.1 Create Define.xml**
Metadata document describing all datasets:
- Dataset definitions
- Variable definitions with origins
- Controlled terminology references
- Computational methods
- Comments and annotations

**5.2 Reviewer's Guide (cSDRG)**
- Study design overview
- Protocol deviations affecting data
- Non-standard mappings rationale
- SUPPQUAL justifications
- Issues for reviewer attention

**5.3 Submission Package Structure**
```
/submission
├── /m5
│   └── /datasets
│       └── /study-id
│           ├── /tabulations
│           │   └── /sdtm
│           │       ├── define.xml
│           │       ├── define-stylesheet.xsl
│           │       ├── dm.xpt
│           │       ├── ae.xpt
│           │       └── [other domains].xpt
│           └── /analysis
│               └── /adam
│                   └── [ADaM datasets]
└── /util
    └── /style
        └── define-stylesheet.xsl
```

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
```

## Quick Decision Guide

**Q: Which domain for this data?**
→ See [references/domain-selection.md](references/domain-selection.md)

**Q: Is this variable required?**
→ Check SDTM IG domain specification (Expected vs. Permissible)

**Q: Should this be SUPP-- or custom domain?**
→ SUPP-- for ≤20 variables; custom domain for structured recurring data

**Q: How to handle missing dates?**
→ Use partial date format: "2024-06" or "2024"; document in define.xml

**Q: Controlled terminology doesn't have my term?**
→ Check if extensible (C-codes ending in other/specify); if not, use sponsor term and document

## Regulatory Agency Specifics

| Agency | Key Requirements |
|--------|-----------------|
| FDA | SDTM IG 3.2+ mandatory; define.xml 2.0+; Pinnacle 21 validation |
| PMDA | SDTM required; Japanese CT may apply |
| EMA | SDTM recommended; define.xml required |
| Health Canada | Follows FDA standards |

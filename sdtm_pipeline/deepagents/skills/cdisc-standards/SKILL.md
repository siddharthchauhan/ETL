---
name: cdisc-standards
description: Use this skill for CDISC SDTM domain knowledge, controlled terminology, protocol interpretation, annotated CRF reading, and clinical data management principles. Essential for mapping EDC data to SDTM format.
---

# CDISC Clinical Data Standards Skill

## Overview

This skill provides comprehensive knowledge of CDISC (Clinical Data Interchange Standards Consortium) standards required for SDTM (Study Data Tabulation Model) transformations. Use this skill when you need to understand domain structures, apply controlled terminology, interpret protocols, or work with clinical trial data.

## Core Competencies

### 1. CDISC SDTM Implementation Guide (SDTM-IG)

**When to use**: Mapping source data to SDTM domains, understanding variable requirements, determining domain class structures.

#### Domain Classes

| Class | Domains | Description |
|-------|---------|-------------|
| **Special-Purpose** | DM, CO, SE, SV | Subject-level and study design data |
| **Interventions** | CM, EX, SU, EC, PR | Treatments and procedures administered |
| **Events** | AE, DS, DV, MH, HO, CE | Clinical events and subject status |
| **Findings** | VS, LB, EG, PE, QS, SC, FA | Observations and measurements |
| **Findings About** | FA | Findings about specific events/interventions |

#### Key Domain Structures

**DM (Demographics)** - Special-Purpose, one record per subject
- Required: STUDYID, DOMAIN, USUBJID, SUBJID, RFSTDTC, RFENDTC, SITEID, BRTHDTC, AGE, AGEU, SEX, RACE, ETHNIC, ARMCD, ARM, COUNTRY
- Timing: RFSTDTC, RFENDTC, RFXSTDTC, RFXENDTC

**AE (Adverse Events)** - Events class, multiple records per subject
- Required: STUDYID, DOMAIN, USUBJID, AESEQ, AETERM, AEDECOD, AESTDTC
- Outcome variables: AEOUT, AESER, AEACN, AEREL, AESCONG, AESDISAB, AESDTH, AESHOSP, AESLIFE, AESMIE

**VS (Vital Signs)** - Findings class, vertical structure
- Required: STUDYID, DOMAIN, USUBJID, VSSEQ, VSTESTCD, VSTEST, VSORRES, VSORRESU
- Result variables: VSORRES, VSSTRESC, VSSTRESN, VSSTRESU

**LB (Laboratory)** - Findings class, vertical structure
- Required: STUDYID, DOMAIN, USUBJID, LBSEQ, LBTESTCD, LBTEST, LBORRES, LBORRESU
- Reference ranges: LBSTNRLO, LBSTNRHI, LBNRIND

**CM (Concomitant Medications)** - Interventions class
- Required: STUDYID, DOMAIN, USUBJID, CMSEQ, CMTRT
- Timing: CMSTDTC, CMENDTC, CMONGO (ongoing flag)

**EX (Exposure)** - Interventions class, study drug administration
- Required: STUDYID, DOMAIN, USUBJID, EXSEQ, EXTRT, EXDOSE, EXDOSU, EXSTDTC, EXENDTC

### 2. CDISC Controlled Terminology (CT)

**When to use**: Validating and mapping raw data values to standardized codes.

#### Key Codelists

| Codelist | Valid Values | Usage |
|----------|--------------|-------|
| SEX | M, F, U, UNDIFFERENTIATED | DM.SEX |
| RACE | AMERICAN INDIAN OR ALASKA NATIVE, ASIAN, BLACK OR AFRICAN AMERICAN, NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER, WHITE, MULTIPLE, NOT REPORTED, UNKNOWN | DM.RACE |
| ETHNIC | HISPANIC OR LATINO, NOT HISPANIC OR LATINO, NOT REPORTED, UNKNOWN | DM.ETHNIC |
| NY (No Yes Response) | N, Y | AESER, AESDTH, AESHOSP, etc. |
| AESEV | MILD, MODERATE, SEVERE | AE.AESEV |
| AGEU | YEARS, MONTHS, WEEKS, DAYS, HOURS | DM.AGEU |
| OUT | RECOVERED/RESOLVED, RECOVERING/RESOLVING, NOT RECOVERED/NOT RESOLVED, RECOVERED/RESOLVED WITH SEQUELAE, FATAL, UNKNOWN | AE.AEOUT |

#### ISO 8601 Date/Time Formats

- Full datetime: `2024-01-15T14:30:00`
- Date only: `2024-01-15`
- Partial date (month/year): `2024-01`
- Year only: `2024`
- With timezone: `2024-01-15T14:30:00+05:30`

### 3. Protocol Interpretation

**When to use**: Understanding study-specific requirements, mapping visit schedules, deriving epoch/phase information.

#### Key Protocol Elements
- **Study Arms**: Treatment groups (ARMCD, ARM, ACTARMCD, ACTARM)
- **Visit Schedule**: Expected visits and timepoints (VISITNUM, VISIT, VISITDY)
- **Epochs**: Study periods like SCREENING, TREATMENT, FOLLOW-UP
- **Inclusion/Exclusion**: Eligibility criteria affecting DS domain

### 4. Annotated CRF (aCRF) Interpretation

**When to use**: Tracing source data to target SDTM variables at the field level.

#### aCRF Reading Guidelines
1. Each CRF field annotated with target SDTM domain.variable
2. Annotations show: DOMAIN.VARIABLE (e.g., DM.SEX, AE.AETERM)
3. Codelist references in brackets: [SEX], [NY]
4. Derivation notes indicated with special markers

### 5. Clinical Data Management Principles

**When to use**: Applying data quality checks during Raw Data Validation phase.

#### Standard Edit Checks
- **Range checks**: Numeric values within expected bounds
- **Consistency checks**: Related fields match (e.g., end date >= start date)
- **Completeness checks**: Required fields populated
- **Format checks**: Dates, codes match expected patterns

## Instructions for Agent

When the agent receives a prompt requiring clinical data standards knowledge:

1. **Domain Selection**: Identify the appropriate SDTM domain based on the data type
   - Patient demographics → DM
   - Adverse events → AE
   - Lab results → LB
   - Vital signs → VS
   - Medications → CM (concomitant) or EX (study drug)

2. **Variable Mapping**: Use the `lookup_sdtm_domain` tool to get required/expected variables

3. **Controlled Terminology**: Use `validate_controlled_terminology` tool to check values against CT

4. **Date Conversion**: Ensure all dates are converted to ISO 8601 format

5. **USUBJID Generation**: Always derive as STUDYID + "-" + SUBJID

6. **Sequence Variables**: Generate --SEQ as unique row number within subject-domain

## Reference Documentation

For detailed specifications, use these tools:
- `search_sdtm_guidelines` - Search SDTM knowledge base
- `fetch_sdtmig_specification` - Get SDTM-IG 3.4 specifications
- `fetch_controlled_terminology` - Get CT codelist values
- `get_mapping_guidance_from_web` - Get web-based mapping guidance

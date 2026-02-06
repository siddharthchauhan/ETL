---
name: cdisc-standards
description: Use this skill when you need to understand domain structures, apply controlled terminology, interpret protocols, or work with clinical trial data
---

# CDISC Clinical Data Standards Skill

## Overview

This skill provides comprehensive knowledge of CDISC (Clinical Data Interchange Standards Consortium) standards required for SDTM (Study Data Tabulation Model) transformations. Based on **SDTM-IG v3.4** and **CDISC Controlled Terminology (2024-03-29 or later)**.

Use this skill when you need to understand domain structures, apply controlled terminology, interpret protocols, or work with clinical trial data.

## Core Competencies

### 1. CDISC SDTM Implementation Guide (SDTM-IG)

**When to use**: Mapping source data to SDTM domains, understanding variable requirements, determining domain class structures.

#### Domain Classes

| Class | Domains | Description |
|-------|---------|-------------|
| **Special-Purpose** | DM, CO, SE, SV | Subject-level and study design data |
| **Trial Design** | TA, TE, TV, TI, TS, TD | Study structure and design parameters |
| **Interventions** | CM, EX, SU, EC, PR | Treatments and procedures administered |
| **Events** | AE, DS, DV, MH, HO, CE | Clinical events and subject status |
| **Findings** | VS, LB, EG, PE, QS, SC, MB, MS, MI, MO, PP, PC, IE | Observations and measurements |
| **Findings About** | FA | Findings about specific events/interventions |
| **Relationship** | RELREC | Records relationships |
| **Associated Persons** | AP-- | Data about non-subjects |

#### Variable Requirement Classifications

| Code | Meaning | Rule |
|------|---------|------|
| **R** | Required | MUST be populated for every record |
| **E** | Expected | SHOULD be populated when data is collected |
| **P** | Permissible | CAN be included when applicable |

#### Key Domain Structures

**DM (Demographics)** - Special-Purpose, ONE record per subject

| Variable | Requirement | Description |
|----------|-------------|-------------|
| STUDYID | R | Study Identifier |
| DOMAIN | R | Domain abbreviation (="DM") |
| USUBJID | R | Unique Subject Identifier |
| SUBJID | R | Subject Identifier for the Study |
| SITEID | R | Study Site Identifier |
| SEX | R | Sex |
| ARMCD | R | Planned Arm Code |
| ARM | R | Description of Planned Arm |
| RFSTDTC | E | Subject Reference Start Date/Time |
| RFENDTC | E | Subject Reference End Date/Time |
| RFXSTDTC | E | Date/Time of First Study Treatment |
| RFXENDTC | E | Date/Time of Last Study Treatment |
| RFICDTC | E | Date/Time of Informed Consent |
| BRTHDTC | E | Date/Time of Birth |
| AGE | E | Age |
| AGEU | E | Age Units |
| ETHNIC | E | Ethnicity |
| RACE | P | Race |
| COUNTRY | E | Country |
| ACTARMCD | P | Actual Arm Code |
| ACTARM | P | Description of Actual Arm |
| DTHFL | P | Subject Death Flag |
| DTHDTC | P | Date/Time of Death |

**AE (Adverse Events)** - Events class, multiple records per subject

| Variable | Requirement | Description |
|----------|-------------|-------------|
| STUDYID | R | Study Identifier |
| DOMAIN | R | Domain abbreviation (="AE") |
| USUBJID | R | Unique Subject Identifier |
| AESEQ | R | Sequence Number |
| AETERM | R | Reported Term for the Adverse Event |
| AEDECOD | E | Dictionary-Derived Term (MedDRA PT) |
| AEBODSYS | E | Body System or Organ Class (MedDRA SOC) |
| AESTDTC | E | Start Date/Time of Adverse Event |
| AEENDTC | E | End Date/Time of Adverse Event |
| AESEV | P | Severity/Intensity |
| AESER | E | Serious Event |
| AEACN | E | Action Taken with Study Treatment |
| AEREL | E | Causality |
| AEOUT | E | Outcome of Adverse Event |
| AESCONG | P | Congenital Anomaly or Birth Defect |
| AESDISAB | P | Persist or Signif Disability/Incapacity |
| AESDTH | P | Results in Death |
| AESHOSP | P | Requires or Prolongs Hospitalization |
| AESLIFE | P | Is Life Threatening |
| AESMIE | P | Other Medically Important Serious Event |
| AEENRF | P | End Relative to Reference Period |
| EPOCH | E | Epoch |

**VS (Vital Signs)** - Findings class, VERTICAL structure

| Variable | Requirement | Description |
|----------|-------------|-------------|
| STUDYID | R | Study Identifier |
| DOMAIN | R | Domain abbreviation (="VS") |
| USUBJID | R | Unique Subject Identifier |
| VSSEQ | R | Sequence Number |
| VSTESTCD | R | Vital Signs Test Short Name |
| VSTEST | R | Vital Signs Test Name |
| VSPOS | P | Vital Signs Position of Subject |
| VSORRES | E | Result or Finding in Original Units |
| VSORRESU | E | Original Units |
| VSSTRESC | E | Character Result/Finding in Std Format |
| VSSTRESN | E | Numeric Result/Finding in Std Units |
| VSSTRESU | E | Standard Units |
| VSSTAT | P | Completion Status |
| VSREASND | P | Reason Not Done |
| VSBLFL | E | Baseline Flag |
| VSDTC | E | Date/Time of Measurements |
| VSDY | E | Study Day of Vital Signs |
| VSTPT | P | Planned Time Point Name |
| VSTPTNUM | P | Planned Time Point Number |
| EPOCH | E | Epoch |
| VISITNUM | E | Visit Number |
| VISIT | E | Visit Name |

**LB (Laboratory)** - Findings class, VERTICAL structure

| Variable | Requirement | Description |
|----------|-------------|-------------|
| STUDYID | R | Study Identifier |
| DOMAIN | R | Domain abbreviation (="LB") |
| USUBJID | R | Unique Subject Identifier |
| LBSEQ | R | Sequence Number |
| LBTESTCD | R | Lab Test Short Name |
| LBTEST | R | Lab Test Name |
| LBCAT | E | Category for Lab Test |
| LBORRES | E | Result or Finding in Original Units |
| LBORRESU | E | Original Units |
| LBSTRESC | E | Character Result/Finding in Std Format |
| LBSTRESN | E | Numeric Result/Finding in Std Units |
| LBSTRESU | E | Standard Units |
| LBSTNRLO | E | Reference Range Lower Limit-Std Units |
| LBSTNRHI | E | Reference Range Upper Limit-Std Units |
| LBNRIND | E | Reference Range Indicator |
| LBSTAT | P | Completion Status |
| LBREASND | P | Reason Not Done |
| LBBLFL | E | Baseline Flag |
| LBDTC | E | Date/Time of Specimen Collection |
| LBDY | E | Study Day of Specimen Collection |
| EPOCH | E | Epoch |
| VISITNUM | E | Visit Number |
| VISIT | E | Visit Name |

**CM (Concomitant Medications)** - Interventions class

| Variable | Requirement | Description |
|----------|-------------|-------------|
| STUDYID | R | Study Identifier |
| DOMAIN | R | Domain abbreviation (="CM") |
| USUBJID | R | Unique Subject Identifier |
| CMSEQ | R | Sequence Number |
| CMTRT | R | Reported Name of Drug, Med, or Therapy |
| CMCAT | P | Category for Medication |
| CMDECOD | E | Standardized Medication Name (WHODrug) |
| CMDOSE | E | Dose per Administration |
| CMDOSU | E | Dose Units |
| CMDOSFRQ | E | Dosing Frequency per Interval |
| CMROUTE | E | Route of Administration |
| CMSTDTC | E | Start Date/Time of Medication |
| CMENDTC | E | End Date/Time of Medication |
| CMENRF | P | End Relative to Reference Period |
| CMENRTPT | P | End Relative to Reference Time Point |
| EPOCH | E | Epoch |

**EX (Exposure)** - Interventions class, study drug administration

| Variable | Requirement | Description |
|----------|-------------|-------------|
| STUDYID | R | Study Identifier |
| DOMAIN | R | Domain abbreviation (="EX") |
| USUBJID | R | Unique Subject Identifier |
| EXSEQ | R | Sequence Number |
| EXTRT | R | Name of Actual Treatment |
| EXDOSE | R | Dose per Administration |
| EXDOSU | R | Dose Units |
| EXDOSFRM | E | Dose Form |
| EXDOSFRQ | E | Dosing Frequency per Interval |
| EXROUTE | E | Route of Administration |
| EXSTDTC | E | Start Date/Time of Treatment |
| EXENDTC | E | End Date/Time of Treatment |
| EXDY | E | Study Day of Treatment |
| EPOCH | E | Epoch |
| VISITNUM | E | Visit Number |
| VISIT | E | Visit Name |

### 2. CDISC Controlled Terminology (CT)

**When to use**: Validating and mapping raw data values to standardized codes.

IMPORTANT:**CRITICAL**: Always use EXACT CT values. Case and spelling must match precisely.

#### Key Codelists

| Codelist | Code | Valid Values | Usage |
|----------|------|--------------|-------|
| SEX | C66731 | M, F, U, UNDIFFERENTIATED | DM.SEX |
| RACE | C74457 | AMERICAN INDIAN OR ALASKA NATIVE, ASIAN, BLACK OR AFRICAN AMERICAN, NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER, WHITE, MULTIPLE, NOT REPORTED, UNKNOWN, OTHER | DM.RACE |
| ETHNIC | C66790 | HISPANIC OR LATINO, NOT HISPANIC OR LATINO, NOT REPORTED, UNKNOWN | DM.ETHNIC |
| NY | C66742 | N, Y | AESER, AESDTH, AESHOSP, etc. |
| AESEV | C66769 | MILD, MODERATE, SEVERE | AE.AESEV |
| AGEU | C66781 | YEARS, MONTHS, WEEKS, DAYS, HOURS | DM.AGEU |
| OUT | C66768 | RECOVERED/RESOLVED, RECOVERING/RESOLVING, NOT RECOVERED/NOT RESOLVED, RECOVERED/RESOLVED WITH SEQUELAE, FATAL, UNKNOWN | AE.AEOUT |
| ACN | C66767 | DRUG WITHDRAWN, DOSE REDUCED, DOSE INCREASED, DOSE NOT CHANGED, NOT APPLICABLE, UNKNOWN | AE.AEACN |
| LOC | C74456 | LEFT, RIGHT, BILATERAL | --LOC variables |
| NRIND | C78736 | HIGH, LOW, NORMAL, ABNORMAL, ABNORMAL HIGH, ABNORMAL LOW | LB.LBNRIND |
| STENRF | C66728 | BEFORE, DURING, DURING/AFTER, AFTER, ONGOING, U | --ENRF, --STRF |
| EPOCH | C99079 | SCREENING, RUN-IN, TREATMENT, FOLLOW-UP | EPOCH |
| VSPOS | C71148 | SITTING, STANDING, SUPINE, PRONE | VS.VSPOS |
| ROUTE | C66729 | ORAL, INTRAVENOUS, SUBCUTANEOUS, INTRAMUSCULAR, TOPICAL, TRANSDERMAL, INHALATION, OPHTHALMIC, etc. | --ROUTE |

#### ISO 8601 Date/Time Formats

| Format | Example | When to Use |
|--------|---------|-------------|
| Full datetime | `2024-01-15T14:30:00` | Complete date and time known |
| Date only | `2024-01-15` | Time not collected |
| Partial - Month/Year | `2024-01` | Day unknown |
| Partial - Year only | `2024` | Month and day unknown |
| With UTC | `2024-01-15T14:30:00Z` | UTC timezone |
| With offset | `2024-01-15T14:30:00+05:30` | Specific timezone |

IMPORTANT:**CRITICAL**: 
- NEVER use placeholders (e.g., `2024-01-XX`, `2024-UN-15`)
- Omit unknown portions from the RIGHT
- Valid partial: `2024-01` (day unknown)
- INVALID partial: `2024-XX-15` (month unknown but day known)

### 3. Critical SDTM Derivation Rules

#### 3.1 USUBJID Construction

**Rule**: Must be UNIQUE across ALL studies in a submission.

**Format**: Sponsor-defined, typically:
```
{STUDYID}-{SITEID}-{SUBJID}
```

**Example**:
```
Study: ABC-001
Site: 101
Subject: 001
USUBJID: ABC-001-101-001
```

IMPORTANT:**CRITICAL**: Format varies by sponsor. Always verify organizational standards.

#### 3.2 --SEQ (Sequence Number) Generation

**Rule**: Must be unique, positive integer within USUBJID within domain.
```python
# CORRECT: Per-subject sequence
df['--SEQ'] = df.groupby('USUBJID').cumcount() + 1

# WRONG: Global row number
df['--SEQ'] = range(1, len(df) + 1)  # ❌ NOT per subject
```

#### 3.3 Study Day (--DY) Calculation

IMPORTANT:**CRITICAL: THERE IS NO DAY 0**
```python
def calculate_study_day(dtc: str, rfstdtc: str) -> int | None:
    """
    Calculate study day per SDTM rules.
    
    Rules:
    - DTC on/after RFSTDTC: DY = (DTC - RFSTDTC) + 1
    - DTC before RFSTDTC: DY = (DTC - RFSTDTC)
    - Day 0 DOES NOT EXIST
    """
    if not dtc or not rfstdtc:
        return None
    
    # Parse dates (handle partials)
    dtc_date = parse_date(dtc[:10])
    ref_date = parse_date(rfstdtc[:10])
    
    if dtc_date is None or ref_date is None:
        return None
    
    diff = (dtc_date - ref_date).days
    
    if diff >= 0:
        return diff + 1  # Day 1, 2, 3, ...
    else:
        return diff  # Day -1, -2, -3, ...
```

**Examples**:
| RFSTDTC | DTC | Calculation | --DY |
|---------|-----|-------------|------|
| 2024-01-15 | 2024-01-15 | (0) + 1 | 1 |
| 2024-01-15 | 2024-01-16 | (1) + 1 | 2 |
| 2024-01-15 | 2024-01-14 | (-1) | -1 |
| 2024-01-15 | 2024-01-10 | (-5) | -5 |

#### 3.4 Baseline Flag (--BLFL)

**Rules**:
- Values: `"Y"` or NULL only (NEVER `"N"`)
- One baseline per test/parameter per subject
- Typically last non-missing value before or on first dose
```python
def derive_baseline_flag(df: pd.DataFrame, 
                         testcd_var: str,
                         dtc_var: str,
                         rfxstdtc: str) -> pd.Series:
    """
    Derive baseline flag for findings domains.
    
    BLFL Rules:
    - Only "Y" or null (NEVER "N")
    - One baseline per test per subject
    - Last non-missing result at or before first treatment
    """
    blfl = pd.Series([None] * len(df), index=df.index)
    
    for (usubjid, testcd), group in df.groupby(['USUBJID', testcd_var]):
        # Get subject's first treatment date
        ref_date = rfxstdtc.get(usubjid)
        if not ref_date:
            continue
        
        # Filter to pre-treatment records with non-missing results
        pre_trt = group[
            (pd.to_datetime(group[dtc_var]) <= pd.to_datetime(ref_date)) &
            (group['--ORRES'].notna())
        ]
        
        if len(pre_trt) > 0:
            # Last pre-treatment record is baseline
            baseline_idx = pre_trt[dtc_var].idxmax()
            blfl.loc[baseline_idx] = "Y"
    
    return blfl
```

#### 3.5 EPOCH Derivation

**Rule**: Determined from SE (Subject Elements) domain or protocol-defined periods.
```python
def derive_epoch(dtc: str, se_data: pd.DataFrame, usubjid: str) -> str | None:
    """
    Derive EPOCH from Subject Elements domain.
    
    Logic: Find SE record where SESTDTC <= DTC < SEENDTC
    """
    if not dtc:
        return None
    
    subject_se = se_data[se_data['USUBJID'] == usubjid]
    
    for _, row in subject_se.iterrows():
        if (row['SESTDTC'] <= dtc and 
            (pd.isna(row['SEENDTC']) or dtc < row['SEENDTC'])):
            return row['EPOCH']
    
    return None
```

**Common EPOCH Values** (from CT):
- SCREENING
- RUN-IN
- TREATMENT
- FOLLOW-UP

### 4. Supplemental Qualifiers (SUPPQUAL)

**When to use**: Non-standard variables that don't fit in parent domain.

**Structure**:
| Variable | Description |
|----------|-------------|
| STUDYID | Study Identifier |
| RDOMAIN | Related Domain Abbreviation |
| USUBJID | Unique Subject Identifier |
| IDVAR | Identifying Variable (e.g., "--SEQ") |
| IDVARVAL | Value of Identifying Variable |
| QNAM | Qualifier Variable Name |
| QLABEL | Qualifier Variable Label |
| QVAL | Data Value |
| QORIG | Origin |
| QEVAL | Evaluator |

**Example**: SUPPAE for investigator's verbatim term
```
RDOMAIN: AE
IDVAR: AESEQ
IDVARVAL: 1
QNAM: AEVERBAT
QLABEL: Verbatim AE Term
QVAL: "headache, mild throbbing"
```

### 5. Protocol Interpretation

**When to use**: Understanding study-specific requirements, mapping visit schedules, deriving epoch/phase information.

#### Key Protocol Elements
- **Study Arms**: Treatment groups (ARMCD, ARM = planned; ACTARMCD, ACTARM = actual)
- **Visit Schedule**: Expected visits and timepoints (VISITNUM, VISIT, VISITDY)
- **Epochs**: Study periods defined in protocol
- **Inclusion/Exclusion**: Eligibility criteria (IE domain)
- **Screen Failures**: Subjects who fail screening get ARMCD = "SCRNFAIL", ARM = "Screen Failure"

### 6. Annotated CRF (aCRF) Interpretation

**When to use**: Tracing source data to target SDTM variables at the field level.

#### aCRF Reading Guidelines
1. Each CRF field annotated with target SDTM domain.variable
2. Annotations format: `DOMAIN.VARIABLE` (e.g., DM.SEX, AE.AETERM)
3. Codelist references in brackets: `[SEX]`, `[NY]`
4. Derivation notes marked with `*` or specific symbols
5. SUPP-- annotations indicate supplemental qualifiers

### 7. Clinical Data Management Principles

**When to use**: Applying data quality checks during Raw Data Validation phase.

#### Standard Edit Checks
- **Range checks**: Numeric values within expected bounds (e.g., Age 0-120)
- **Consistency checks**: Related fields match (e.g., AEENDTC >= AESTDTC)
- **Completeness checks**: Required fields populated
- **Format checks**: Dates in ISO 8601, codes match CT
- **Cross-domain checks**: USUBJID exists in DM, dates within study period

---

## Instructions for Agent

### Critical Workflow: Mapping Specification First

IMPORTANT:**MANDATORY**: Before writing ANY transformation code:

1. **Analyze** source data structure
2. **Generate mapping specification** documenting source→target mappings
3. **Save mapping spec** for review
4. **Then transform** data per approved spec
5. **Validate** output against SDTM rules

### Domain Selection Guide

| Data Type | Primary Domain | Notes |
|-----------|---------------|-------|
| Patient demographics | DM | One record per subject |
| Adverse events | AE | MedDRA coding required |
| Lab results | LB | Vertical structure, reference ranges |
| Vital signs | VS | Vertical structure, position may apply |
| Prior/concomitant meds | CM | WHODrug coding recommended |
| Study drug administration | EX | Actual treatment given |
| Medical history | MH | Pre-study conditions |
| Subject disposition | DS | Completion status, early termination |
| Protocol deviations | DV | Major/minor classification |
| ECG data | EG | Findings class structure |
| Physical exam | PE | Findings class structure |

### Critical SDTM Rules

1. **USUBJID**: Verify sponsor format standards; must be unique across submission
2. **--SEQ**: Generate per-subject, starting at 1
3. **--DY**: Use NO DAY 0 rule (see Section 3.3)
4. **--BLFL**: Only `"Y"` or null
5. **CT Mapping**: Exact match required (case-sensitive)
6. **Partial Dates**: Preserve per ISO 8601 rules
7. **EPOCH**: Derive from SE domain or protocol

### Code Quality Requirements

- All derivations logged with source→target mapping
- Validation checks after each transformation
- CT validation for all coded fields
- --SEQ uniqueness verification
- Date format validation
- Cross-reference validation (USUBJID in DM)

---

## Summary of Corrections Made

| # | Issue | Severity | Correction |
|---|-------|----------|------------|
| 1 | FA listed twice | Critical | Removed from Findings class |
| 2 | Variable requirements wrong | Critical | Added R/E/P classifications |
| 3 | CMONGO invalid | Critical | Replaced with CMENRF/CMENRTPT |
| 4 | USUBJID oversimplified | Critical | Added sponsor format note |
| 5 | Missing --DY rule | Critical | Added full calculation with examples |
| 6 | Missing --BLFL rule | Critical | Added with code example |
| 7 | Missing SUPPQUAL | High | Added full section |
| 8 | Missing Trial Design domains | Medium | Added TA, TE, TV, TI, TS |
| 9 | RACE codelist incomplete | Medium | Added OTHER, UNKNOWN |
| 10 | Undefined tools | Medium | Removed or need definition |
| 11 | No SDTM-IG version | Low | Added v3.4 reference |

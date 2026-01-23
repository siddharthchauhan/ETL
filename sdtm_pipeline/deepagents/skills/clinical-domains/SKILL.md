---
name: clinical-domains
description: Use this skill for detailed guidance on Events and Interventions SDTM domain classes. Covers AE, DS, DV, MH, HO, CE (Events) and CM, EX, SU, PR, EC, AG, ML (Interventions). Essential for transforming clinical event data and treatment records.
---

# Clinical Domains Skill (Events & Interventions)

## Overview

This skill provides detailed expertise on Events and Interventions class SDTM domains. These domains capture clinical events that happen to subjects and treatments administered during the study.

## Events Class Domains

Events domains capture clinical events or milestones that occur during the study. Records represent discrete events with start/end dates.

### AE - Adverse Events

**Purpose**: Capture adverse events experienced by subjects during the study.

**Structure**: Multiple records per subject (one per event)

#### Required Variables

| Variable | Label | Type | Description |
|----------|-------|------|-------------|
| STUDYID | Study Identifier | Char | Unique study identifier |
| DOMAIN | Domain Abbreviation | Char | "AE" |
| USUBJID | Unique Subject ID | Char | STUDYID + "-" + SUBJID |
| AESEQ | Sequence Number | Num | Unique within subject |
| AETERM | Reported Term | Char | Verbatim AE term as reported |
| AEDECOD | Dictionary-Derived Term | Char | MedDRA preferred term |
| AESTDTC | Start Date/Time | Char | ISO 8601 format |

#### Expected Variables

| Variable | Label | Controlled Term |
|----------|-------|-----------------|
| AEBODSYS | Body System | MedDRA SOC |
| AESEV | Severity | MILD, MODERATE, SEVERE |
| AESER | Serious Event | Y, N |
| AEACN | Action Taken | DOSE NOT CHANGED, DOSE REDUCED, ... |
| AEREL | Causality | NOT RELATED, UNLIKELY, POSSIBLE, PROBABLE, RELATED |
| AEOUT | Outcome | RECOVERED/RESOLVED, FATAL, ... |
| AEENDTC | End Date/Time | ISO 8601 |

#### Serious Event Flags

| Variable | Label | Values |
|----------|-------|--------|
| AESCONG | Congenital Anomaly | Y, N |
| AESDISAB | Disability | Y, N |
| AESDTH | Death | Y, N |
| AESHOSP | Hospitalization | Y, N |
| AESLIFE | Life Threatening | Y, N |
| AESMIE | Other Medically Important | Y, N |

#### Transformation Rules

```python
# AE Transformation Pattern
ae_mappings = {
    "AETERM": "UPCASE(AE_VERBATIM)",
    "AEDECOD": "set to PREFERRED_TERM",
    "AESTDTC": "ISO8601DATEFORMAT(AE_START_DATE, 'DD-MON-YYYY')",
    "AEENDTC": "ISO8601DATEFORMAT(AE_END_DATE, 'DD-MON-YYYY')",
    "AESEV": "FORMAT(SEVERITY_CODE, 'AESEV')",
    "AESER": "IF(SERIOUS == 'Yes', 'Y', 'N')",
}
```

---

### DS - Disposition

**Purpose**: Capture subject disposition events (enrollment, completion, discontinuation).

**Structure**: Multiple records per subject (one per disposition event)

#### Required Variables

| Variable | Label | Type |
|----------|-------|------|
| STUDYID | Study Identifier | Char |
| DOMAIN | Domain Abbreviation | Char |
| USUBJID | Unique Subject ID | Char |
| DSSEQ | Sequence Number | Num |
| DSTERM | Reported Term | Char |
| DSDECOD | Standardized Disposition Term | Char |

#### Expected Variables

| Variable | Label | CT |
|----------|-------|----|
| DSCAT | Category | Protocol Milestone |
| DSSCAT | Subcategory | INFORMED CONSENT, RANDOMIZATION, TREATMENT, STUDY |
| EPOCH | Epoch | SCREENING, TREATMENT, FOLLOW-UP |
| DSSTDTC | Start Date | ISO 8601 |

#### Common DSDECOD Values

| DSSCAT | DSDECOD Values |
|--------|----------------|
| INFORMED CONSENT | INFORMED CONSENT OBTAINED |
| RANDOMIZATION | RANDOMIZED |
| TREATMENT | COMPLETED, ADVERSE EVENT, DEATH, LACK OF EFFICACY, LOST TO FOLLOW-UP, PHYSICIAN DECISION, PROTOCOL VIOLATION, WITHDRAWAL BY SUBJECT |
| STUDY | COMPLETED, SCREEN FAILURE |

---

### MH - Medical History

**Purpose**: Capture subject's medical history prior to study entry.

**Structure**: Multiple records per subject (one per condition)

#### Required Variables

| Variable | Label | Type |
|----------|-------|------|
| STUDYID | Study Identifier | Char |
| DOMAIN | Domain Abbreviation | Char |
| USUBJID | Unique Subject ID | Char |
| MHSEQ | Sequence Number | Num |
| MHTERM | Reported Term | Char |

#### Expected Variables

| Variable | Label | Description |
|----------|-------|-------------|
| MHDECOD | Dictionary-Derived Term | MedDRA preferred term |
| MHBODSYS | Body System | MedDRA SOC |
| MHCAT | Category | GENERAL, PRIMARY DIAGNOSIS, etc. |
| MHSTDTC | Start Date | When condition started |
| MHENDTC | End Date | When condition resolved |
| MHONGO | Ongoing Event | Y, N |

---

### DV - Protocol Deviations

**Purpose**: Capture protocol deviations during the study.

#### Required Variables

| Variable | Label | Type |
|----------|-------|------|
| STUDYID | Study Identifier | Char |
| DOMAIN | Domain Abbreviation | Char |
| USUBJID | Unique Subject ID | Char |
| DVSEQ | Sequence Number | Num |
| DVTERM | Protocol Deviation Term | Char |

#### Expected Variables

| Variable | Label | CT |
|----------|-------|----|
| DVDECOD | Coded Deviation | (Protocol-specific) |
| DVCAT | Category | ELIGIBILITY, PROCEDURE, TREATMENT, ... |
| DVSCAT | Subcategory | |
| DVSTDTC | Start Date | ISO 8601 |

---

### HO - Healthcare Encounters

**Purpose**: Capture healthcare encounters (hospitalizations, ER visits).

#### Key Variables

| Variable | Label | Description |
|----------|-------|-------------|
| HOTERM | Healthcare Encounter Term | Type of encounter |
| HOSTDTC | Start Date/Time | Admission date |
| HOENDTC | End Date/Time | Discharge date |
| HODUR | Duration | Length of stay |

---

### CE - Clinical Events

**Purpose**: Capture clinical events that are not AEs (disease milestones).

#### Key Variables

| Variable | Label | Description |
|----------|-------|-------------|
| CETERM | Clinical Event Term | Event description |
| CECAT | Category | Disease progression, Response, etc. |
| CESTDTC | Start Date | Event date |

---

## Interventions Class Domains

Interventions domains capture treatments, therapies, and substances administered to or used by subjects.

### CM - Concomitant Medications

**Purpose**: Capture medications taken before or during the study (not study drug).

**Structure**: Multiple records per subject (one per medication)

#### Required Variables

| Variable | Label | Type |
|----------|-------|------|
| STUDYID | Study Identifier | Char |
| DOMAIN | Domain Abbreviation | Char |
| USUBJID | Unique Subject ID | Char |
| CMSEQ | Sequence Number | Num |
| CMTRT | Reported Treatment Name | Char |

#### Expected Variables

| Variable | Label | Description |
|----------|-------|-------------|
| CMDECOD | Standardized Treatment | WHO Drug Dictionary |
| CMCAT | Category | PRIOR, CONCOMITANT |
| CMDOSE | Dose | Numeric dose value |
| CMDOSU | Dose Units | mg, mL, etc. |
| CMDOSFRM | Dose Form | TABLET, CAPSULE, INJECTION |
| CMROUTE | Route | ORAL, INTRAVENOUS, TOPICAL |
| CMSTDTC | Start Date | ISO 8601 |
| CMENDTC | End Date | ISO 8601 |
| CMONGO | Ongoing | Y, N |
| CMINDC | Indication | Reason for taking |

#### Transformation Rules

```python
cm_mappings = {
    "CMTRT": "UPCASE(MEDICATION_NAME)",
    "CMDECOD": "set to WHO_DRUG_TERM",
    "CMCAT": "IF(TIMING == 'PRIOR', 'PRIOR', 'CONCOMITANT')",
    "CMDOSE": "set to DOSE_VALUE",
    "CMDOSU": "UPCASE(DOSE_UNIT)",
    "CMSTDTC": "ISO8601DATEFORMAT(MED_START_DATE, 'YYYYMMDD')",
    "CMONGO": "IF(MED_END_DATE is null, 'Y', 'N')",
}
```

---

### EX - Exposure

**Purpose**: Capture study drug administration (exposure).

**Structure**: Multiple records per subject (one per dosing event/interval)

#### Required Variables

| Variable | Label | Type |
|----------|-------|------|
| STUDYID | Study Identifier | Char |
| DOMAIN | Domain Abbreviation | Char |
| USUBJID | Unique Subject ID | Char |
| EXSEQ | Sequence Number | Num |
| EXTRT | Treatment Name | Char |
| EXDOSE | Dose | Num |
| EXDOSU | Dose Units | Char |
| EXSTDTC | Start Date/Time | Char |
| EXENDTC | End Date/Time | Char |

#### Expected Variables

| Variable | Label | Description |
|----------|-------|-------------|
| EXCAT | Category | Protocol-defined |
| EXDOSFRM | Dose Form | TABLET, CAPSULE, IV |
| EXDOSFRQ | Dosing Frequency | QD, BID, TID, etc. |
| EXROUTE | Route | ORAL, INTRAVENOUS |
| EXLOT | Lot Number | Drug lot identifier |
| EXADJ | Dose Adjustment Reason | |
| EPOCH | Epoch | SCREENING, TREATMENT, etc. |

#### Key Differences from CM

| Aspect | EX (Exposure) | CM (Concomitant Meds) |
|--------|---------------|----------------------|
| Purpose | Study drug only | Non-study medications |
| Timing | Treatment period only | Before and during study |
| Required | EXSTDTC, EXENDTC required | CMONGO for ongoing |

---

### SU - Substance Use

**Purpose**: Capture substance use history (tobacco, alcohol, drugs).

#### Key Variables

| Variable | Label | Description |
|----------|-------|-------------|
| SUTRT | Substance Name | Tobacco, Alcohol, etc. |
| SUCAT | Category | ALCOHOL, TOBACCO, CAFFEINE, etc. |
| SUSTAT | Status | CURRENT, FORMER, NEVER |
| SUSTDTC | Start Date | When use started |
| SUENDTC | End Date | When use stopped (if FORMER) |
| SUDOSE | Quantity | Amount used |
| SUDOSU | Units | CIGARETTES/DAY, DRINKS/WEEK |

---

### PR - Procedures

**Purpose**: Capture non-study procedures performed on subjects.

#### Key Variables

| Variable | Label | Description |
|----------|-------|-------------|
| PRTRT | Procedure Name | Procedure description |
| PRCAT | Category | SURGICAL, DIAGNOSTIC, etc. |
| PRSTDTC | Start Date | Procedure date |
| PRLOC | Location | Body location |

---

### EC - Exposure as Collected

**Purpose**: Capture exposure as collected on CRF (before derivations).

This domain stores raw exposure data before standardization to EX.

---

## Domain Transformation Patterns

### Events Class Pattern

```python
def transform_events_domain(df, domain, study_id):
    """Generic Events class transformation."""
    result = pd.DataFrame()

    # Identifiers
    result["STUDYID"] = study_id
    result["DOMAIN"] = domain
    result["USUBJID"] = study_id + "-" + df["SUBJECT_ID"].astype(str)
    result[f"{domain}SEQ"] = range(1, len(df) + 1)

    # Term variables
    result[f"{domain}TERM"] = df["TERM"].str.upper()
    result[f"{domain}DECOD"] = df["PREFERRED_TERM"]

    # Dates (ISO 8601)
    result[f"{domain}STDTC"] = df["START_DATE"].apply(to_iso8601)
    result[f"{domain}ENDTC"] = df["END_DATE"].apply(to_iso8601)

    return result
```

### Interventions Class Pattern

```python
def transform_interventions_domain(df, domain, study_id):
    """Generic Interventions class transformation."""
    result = pd.DataFrame()

    # Identifiers
    result["STUDYID"] = study_id
    result["DOMAIN"] = domain
    result["USUBJID"] = study_id + "-" + df["SUBJECT_ID"].astype(str)
    result[f"{domain}SEQ"] = range(1, len(df) + 1)

    # Treatment
    result[f"{domain}TRT"] = df["TREATMENT"].str.upper()

    # Dosing (for CM, EX)
    if "DOSE" in df.columns:
        result[f"{domain}DOSE"] = df["DOSE"]
        result[f"{domain}DOSU"] = df["DOSE_UNIT"].str.upper()

    # Dates
    result[f"{domain}STDTC"] = df["START_DATE"].apply(to_iso8601)
    result[f"{domain}ENDTC"] = df["END_DATE"].apply(to_iso8601)

    # Ongoing flag
    result[f"{domain}ONGO"] = df["END_DATE"].isna().map({True: "Y", False: "N"})

    return result
```

## Common Validation Rules

### Events Domains

| Rule ID | Domain | Check |
|---------|--------|-------|
| AE0001 | AE | AETERM is not null |
| AE0007 | AE | AESTDTC is ISO 8601 |
| AE0010 | AE | AESER in (Y, N) |
| DS0001 | DS | DSDECOD is from CT |
| MH0001 | MH | MHTERM is not null |

### Interventions Domains

| Rule ID | Domain | Check |
|---------|--------|-------|
| CM0001 | CM | CMTRT is not null |
| CM0005 | CM | CMSTDTC <= CMENDTC |
| EX0001 | EX | EXTRT is not null |
| EX0003 | EX | EXDOSE is numeric |
| EX0005 | EX | EXSTDTC <= EXENDTC |

## Instructions for Agent

When transforming Events and Interventions domains:

1. **Events**: Always populate --TERM and --DECOD (verbatim and coded)
2. **Interventions**: Always populate --TRT (treatment name)
3. **Dates**: Convert all dates to ISO 8601
4. **Ongoing**: Use --ONGO = "Y" when end date is missing
5. **Controlled Terms**: Apply CT for severity, outcome, route, etc.
6. **Sequence**: Generate --SEQ unique within subject-domain

## Available Tools

- `lookup_sdtm_domain` - Get domain structure
- `validate_controlled_terminology` - Check CT values
- `transform_adverse_events` - Transform AE domain
- `convert_domain` - High-level domain conversion

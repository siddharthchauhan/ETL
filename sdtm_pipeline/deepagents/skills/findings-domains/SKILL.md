---
name: findings-domains
description: Use this skill for Findings class SDTM domains (LB, VS, EG, PE, QS, SC, FA). Covers vertical data structures, test code standardization, result handling (original vs standardized), reference ranges, baseline flags, and the unique --TESTCD/--TEST/--ORRES/--STRESC pattern. Essential for laboratory and vital signs transformations.
---

# Findings Domains Skill (LB, VS, EG, PE, QS)

## Overview

This skill provides detailed expertise on Findings class SDTM domains. Findings domains have a unique vertical structure where each row represents a single test result, using standardized variable naming patterns for test identification and result values.

## The Vertical (Long) Structure

### Horizontal vs Vertical Format

**Source Data (Horizontal)**:
```
SUBJECT_ID | SYSBP | DIABP | PULSE | TEMP | WEIGHT
001        | 120   | 80    | 72    | 98.6 | 180
002        | 135   | 85    | 68    | 98.2 | 165
```

**SDTM VS (Vertical)**:
```
USUBJID     | VSTESTCD | VSTEST                    | VSORRES | VSORRESU
STUDY-001   | SYSBP    | Systolic Blood Pressure   | 120     | mmHg
STUDY-001   | DIABP    | Diastolic Blood Pressure  | 80      | mmHg
STUDY-001   | PULSE    | Pulse Rate                | 72      | BEATS/MIN
STUDY-001   | TEMP     | Temperature               | 98.6    | F
STUDY-001   | WEIGHT   | Weight                    | 180     | LB
STUDY-002   | SYSBP    | Systolic Blood Pressure   | 135     | mmHg
...
```

### Why Vertical Structure?

1. **Standardization**: Allows any test to use the same variable names
2. **Extensibility**: New tests don't require new variables
3. **Analysis**: Easier to filter and aggregate by test type
4. **Metadata**: Define.xml can document once for all tests

## Findings Variable Naming Pattern

All Findings domains use this naming convention (replace -- with domain prefix):

| Pattern | Name | Description |
|---------|------|-------------|
| --TESTCD | Test Code | Short standardized code (8 char max) |
| --TEST | Test Name | Full test name |
| --CAT | Category | Test category |
| --SCAT | Subcategory | Test subcategory |
| --ORRES | Original Result | Result as collected |
| --ORRESU | Original Units | Units as collected |
| --STRESC | Standardized Result (Char) | Standardized character result |
| --STRESN | Standardized Result (Num) | Standardized numeric result |
| --STRESU | Standardized Units | Standard units |
| --STAT | Completion Status | NOT DONE if missing |
| --REASND | Reason Not Done | Why test not performed |
| --LOC | Location | Body location/specimen |
| --METHOD | Method | Test method |
| --BLFL | Baseline Flag | Y if baseline record |
| --DRVFL | Derived Flag | Y if derived value |

## Core Findings Domains

### VS - Vital Signs

**Purpose**: Capture vital sign measurements.

**Structure**: Vertical, multiple records per subject per visit

#### Required Variables

| Variable | Label | Description |
|----------|-------|-------------|
| STUDYID | Study Identifier | |
| DOMAIN | Domain Abbreviation | "VS" |
| USUBJID | Unique Subject ID | |
| VSSEQ | Sequence Number | Unique within subject |
| VSTESTCD | Test Code | SYSBP, DIABP, PULSE, TEMP, etc. |
| VSTEST | Test Name | Full test name |
| VSORRES | Original Result | Collected value |
| VSORRESU | Original Units | Collected units |

#### Standard Test Codes (VSTESTCD)

| VSTESTCD | VSTEST | Typical Units |
|----------|--------|---------------|
| SYSBP | Systolic Blood Pressure | mmHg |
| DIABP | Diastolic Blood Pressure | mmHg |
| PULSE | Pulse Rate | BEATS/MIN |
| RESP | Respiratory Rate | BREATHS/MIN |
| TEMP | Temperature | C, F |
| HEIGHT | Height | cm, in |
| WEIGHT | Weight | kg, lb |
| BMI | Body Mass Index | kg/m2 |
| OXYSAT | Oxygen Saturation | % |

#### Expected Variables

| Variable | Label | Values |
|----------|-------|--------|
| VSCAT | Category | VITAL SIGNS |
| VSPOS | Position | STANDING, SITTING, SUPINE |
| VSLOC | Location | ARM, ORAL, etc. |
| VSBLFL | Baseline Flag | Y, null |
| VSDTC | Date/Time | ISO 8601 |
| VISITNUM | Visit Number | Numeric |
| VISIT | Visit Name | SCREENING, WEEK 1, etc. |

#### Transformation Example

```python
def transform_to_vs(source_df, study_id):
    """Transform horizontal vitals to vertical SDTM VS."""

    # Test code mapping
    test_map = {
        "SYSTOLIC_BP": ("SYSBP", "Systolic Blood Pressure", "mmHg"),
        "DIASTOLIC_BP": ("DIABP", "Diastolic Blood Pressure", "mmHg"),
        "PULSE_RATE": ("PULSE", "Pulse Rate", "BEATS/MIN"),
        "TEMPERATURE": ("TEMP", "Temperature", "C"),
        "WEIGHT_KG": ("WEIGHT", "Weight", "kg"),
        "HEIGHT_CM": ("HEIGHT", "Height", "cm"),
    }

    records = []
    for _, row in source_df.iterrows():
        usubjid = f"{study_id}-{row['SUBJECT_ID']}"

        for src_col, (testcd, test, unit) in test_map.items():
            if src_col in row and pd.notna(row[src_col]):
                records.append({
                    "STUDYID": study_id,
                    "DOMAIN": "VS",
                    "USUBJID": usubjid,
                    "VSTESTCD": testcd,
                    "VSTEST": test,
                    "VSORRES": str(row[src_col]),
                    "VSORRESU": unit,
                    "VSDTC": row.get("VISIT_DATE", ""),
                })

    vs = pd.DataFrame(records)
    vs["VSSEQ"] = vs.groupby("USUBJID").cumcount() + 1
    return vs
```

---

### LB - Laboratory Test Results

**Purpose**: Capture laboratory test results.

**Structure**: Vertical, multiple records per subject per specimen

#### Required Variables

| Variable | Label | Description |
|----------|-------|-------------|
| STUDYID | Study Identifier | |
| DOMAIN | Domain Abbreviation | "LB" |
| USUBJID | Unique Subject ID | |
| LBSEQ | Sequence Number | |
| LBTESTCD | Test Code | ALB, ALT, AST, BILI, CREAT, etc. |
| LBTEST | Test Name | Full test name |
| LBORRES | Original Result | Lab value as reported |
| LBORRESU | Original Units | Reported units |

#### Standard Test Codes (LBTESTCD)

| Category | LBTESTCD | LBTEST |
|----------|----------|--------|
| Chemistry | ALB | Albumin |
| Chemistry | ALT | Alanine Aminotransferase |
| Chemistry | AST | Aspartate Aminotransferase |
| Chemistry | BILI | Bilirubin |
| Chemistry | BUN | Blood Urea Nitrogen |
| Chemistry | CREAT | Creatinine |
| Chemistry | GLUC | Glucose |
| Hematology | HGB | Hemoglobin |
| Hematology | HCT | Hematocrit |
| Hematology | WBC | White Blood Cell Count |
| Hematology | RBC | Red Blood Cell Count |
| Hematology | PLAT | Platelet Count |
| Urinalysis | UROBILI | Urobilinogen |
| Urinalysis | UPROT | Urine Protein |

#### Reference Range Variables

| Variable | Label | Description |
|----------|-------|-------------|
| LBORNRLO | Original Low | Lower limit (as reported) |
| LBORNRHI | Original High | Upper limit (as reported) |
| LBSTNRLO | Standardized Low | Lower limit (standardized) |
| LBSTNRHI | Standardized High | Upper limit (standardized) |
| LBNRIND | Reference Range Indicator | NORMAL, LOW, HIGH |

#### Specimen Variables

| Variable | Label | Values |
|----------|-------|--------|
| LBSPEC | Specimen Type | BLOOD, SERUM, PLASMA, URINE |
| LBMETHOD | Method | Test methodology |
| LBFAST | Fasting Status | Y, N |

#### Result Standardization

```python
def standardize_lab_result(orres, orresu, target_unit):
    """
    Convert original result to standardized units.

    Examples:
    - mg/dL to mmol/L for glucose
    - g/dL to g/L for hemoglobin
    """
    conversion_factors = {
        ("mg/dL", "mmol/L", "GLUC"): 0.0555,  # Glucose
        ("g/dL", "g/L", "HGB"): 10.0,  # Hemoglobin
        ("mg/dL", "umol/L", "CREAT"): 88.4,  # Creatinine
    }

    key = (orresu.upper(), target_unit.upper(), testcd)
    if key in conversion_factors:
        return float(orres) * conversion_factors[key]
    return float(orres)
```

---

### EG - ECG Test Results

**Purpose**: Capture electrocardiogram measurements.

**Structure**: Vertical, multiple records per subject per timepoint

#### Standard Test Codes (EGTESTCD)

| EGTESTCD | EGTEST |
|----------|--------|
| INTP | Interpretation |
| HR | Heart Rate |
| RR | RR Interval |
| PR | PR Interval |
| QRS | QRS Duration |
| QT | QT Interval |
| QTCB | QTcB Interval |
| QTCF | QTcF Interval |

#### Expected Variables

| Variable | Label | Values |
|----------|-------|--------|
| EGPOS | Position | SUPINE, SITTING |
| EGLEAD | Lead | LEAD 1, LEAD 2, LEAD V1, etc. |
| EGMETHOD | Method | 12-LEAD ECG |
| EGBLFL | Baseline Flag | Y, null |

---

### PE - Physical Examination

**Purpose**: Capture physical examination findings.

#### Standard Test Codes (PETESTCD)

| PETESTCD | PETEST | Body System |
|----------|--------|-------------|
| GENERAL | General Appearance | General |
| HEENT | Head, Eyes, Ears, Nose, Throat | Head/Neck |
| LUNGS | Lungs | Respiratory |
| HEART | Heart | Cardiovascular |
| ABDOMEN | Abdomen | Gastrointestinal |
| EXTREM | Extremities | Musculoskeletal |
| NEURO | Neurological | Nervous System |
| SKIN | Skin | Integumentary |

#### Result Values

| PEORRES | Meaning |
|---------|---------|
| NORMAL | No abnormalities |
| ABNORMAL | Abnormality found |
| NOT EXAMINED | Test not performed |

---

### QS - Questionnaires

**Purpose**: Capture questionnaire/scale responses.

**Structure**: Vertical, one row per question

#### Key Variables

| Variable | Label | Description |
|----------|-------|-------------|
| QSCAT | Category | Questionnaire name (e.g., HAM-D, SF-36) |
| QSSCAT | Subcategory | Subscale |
| QSTESTCD | Question Code | Q01, Q02, etc. |
| QSTEST | Question Text | Full question |
| QSORRES | Response | Patient response |
| QSSTRESC | Standardized Response | Coded response |
| QSSTRESN | Numeric Score | Numeric value |

---

## Baseline Flag Logic

The baseline flag (--BLFL) identifies the record used as baseline for analysis.

### Baseline Rules

```python
def assign_baseline_flag(df, domain, date_col, baseline_visit="SCREENING"):
    """
    Assign baseline flag based on rules:
    1. Last non-missing value before/on treatment start
    2. Specific visit (e.g., SCREENING, DAY 1)
    3. Designated baseline record
    """
    blfl_col = f"{domain}BLFL"

    # Option 1: By visit
    df[blfl_col] = df["VISIT"].apply(
        lambda x: "Y" if x == baseline_visit else None
    )

    # Option 2: Last pre-treatment
    # Group by subject and test, find last pre-treatment record
    df[blfl_col] = df.groupby(["USUBJID", f"{domain}TESTCD"]).apply(
        lambda g: assign_last_pretreatment(g, date_col)
    )

    return df
```

### Derived Flag

The derived flag (--DRVFL) indicates calculated values:

```python
# BMI is typically derived from height and weight
df.loc[df["VSTESTCD"] == "BMI", "VSDRVFL"] = "Y"

# Calculated lab values
df.loc[df["LBTESTCD"].isin(["GFR", "LDL"]), "LBDRVFL"] = "Y"
```

## Transposition Techniques

### Pandas Melt for Vertical Transformation

```python
def transpose_horizontal_to_vertical(df, id_vars, value_vars, domain):
    """
    Convert horizontal source data to vertical SDTM format.

    Args:
        df: Source DataFrame with horizontal structure
        id_vars: Columns to keep as identifiers (SUBJECT_ID, VISIT_DATE)
        value_vars: Columns to transpose (test values)
        domain: Target domain (VS, LB, etc.)
    """
    # Melt to long format
    long_df = df.melt(
        id_vars=id_vars,
        value_vars=value_vars,
        var_name=f"{domain}TESTCD",
        value_name=f"{domain}ORRES"
    )

    # Remove null results
    long_df = long_df[long_df[f"{domain}ORRES"].notna()]

    return long_df
```

### Handling Multiple Specimens

```python
def transpose_lab_with_specimens(df, study_id):
    """Handle labs from multiple specimens (BLOOD, URINE)."""
    records = []

    specimen_cols = {
        "BLOOD": ["ALB", "ALT", "AST", "BILI", "CREAT", "GLUC"],
        "URINE": ["UPROT", "UGLUC", "UPH"],
    }

    for _, row in df.iterrows():
        for specimen, tests in specimen_cols.items():
            for test in tests:
                if test in row and pd.notna(row[test]):
                    records.append({
                        "STUDYID": study_id,
                        "DOMAIN": "LB",
                        "USUBJID": f"{study_id}-{row['SUBJECT_ID']}",
                        "LBTESTCD": test,
                        "LBORRES": str(row[test]),
                        "LBSPEC": specimen,
                        "LBDTC": row.get("COLLECTION_DATE", ""),
                    })

    return pd.DataFrame(records)
```

## Validation Rules for Findings

### Common Rules

| Rule ID | Check | Severity |
|---------|-------|----------|
| FD0001 | --TESTCD is not null | ERROR |
| FD0002 | --TEST is not null | ERROR |
| FD0003 | --ORRES or --STAT populated | ERROR |
| FD0004 | If --STAT = 'NOT DONE', --REASND populated | WARNING |
| FD0005 | --STRESN is numeric when populated | ERROR |
| FD0006 | --STRESU standardized units | WARNING |
| FD0007 | Only one --BLFL = 'Y' per subject/test | ERROR |

### Domain-Specific Rules

| Rule ID | Domain | Check |
|---------|--------|-------|
| LB0001 | LB | LBSPEC is from CT |
| LB0002 | LB | Reference ranges consistent |
| VS0001 | VS | VSTESTCD is from CT |
| VS0002 | VS | VSPOS populated for BP |
| EG0001 | EG | EGLEAD populated for measurements |

## Instructions for Agent

When transforming Findings domains:

1. **Transpose First**: Convert horizontal source to vertical format
2. **Standardize Test Codes**: Use CDISC CT for --TESTCD
3. **Handle Missing**: Use --STAT = 'NOT DONE' with --REASND
4. **Standardize Results**: Convert to standard units in --STRESN/--STRESU
5. **Assign Baseline**: Apply --BLFL logic consistently
6. **Mark Derived**: Flag calculated values with --DRVFL = 'Y'
7. **Include Reference Ranges**: Populate --STNRLO/--STNRHI for labs

## Available Tools

- `lookup_sdtm_domain` - Get domain structure for VS, LB, EG, etc.
- `validate_controlled_terminology` - Check test codes against CT
- `transform_to_sdtm` - Generic transformation
- `convert_domain` - High-level conversion
- `get_sdtm_guidance` - Get Findings domain guidance

---
name: mapping-scenarios
description: Use this skill to understand the 9 fundamental SDTM mapping scenarios that cover all transformation patterns. Master these scenarios (direct carry forward, rename, attribute change, combine, split, derivation, value map, structure transformation, supplemental qualifiers) and SDTM mapping becomes achievable. Based on industry best practices from PharmaSUG and CDISC guidance.
---

# The 9 Essential SDTM Mapping Scenarios

## Overview

According to PharmaSUG research and industry best practices, there are **9 possible scenarios** in the SDTM mapping process. If you master these, SDTM mapping becomes much more achievable.

**Source**: PharmaSUG papers, Formedix SDTM mapping research, industry consensus

## Scenario 1: Direct Carry Forward

**Definition**: Variables that are already SDTM-compliant can be directly carried forward without modification.

### When to Use
- Source variable name matches SDTM variable name
- Source values are already in correct format
- Source attributes (length, type) match SDTM

### Example

```python
# Source data already has SDTM-compliant variables
source_df = pd.DataFrame({
    "STUDYID": ["STUDY-001", "STUDY-001"],
    "USUBJID": ["STUDY-001-001", "STUDY-001-002"],
    "SUBJID": ["001", "002"],
})

# Direct carry forward
sdtm_df = source_df[["STUDYID", "USUBJID", "SUBJID"]].copy()
```

### Tips
- Validate that values truly are SDTM-compliant
- Check controlled terminology even if variable name matches
- Verify data types and lengths

---

## Scenario 2: Variable Rename

**Definition**: Variables need to be renamed to match SDTM variable names.

### When to Use
- Source variable has different name but same meaning
- Values and format are correct, only name differs

### Example

```python
# Source: GENDER → SDTM: SEX
# Source: BIRTH_DATE → SDTM: BRTHDTC
# Source: SUBJECT_ID → SDTM: SUBJID

source_df = pd.DataFrame({
    "SUBJECT_ID": ["001", "002"],
    "GENDER": ["M", "F"],
    "BIRTH_DATE": ["1980-05-15", "1975-11-22"],
})

# Rename to SDTM variables
sdtm_df = source_df.rename(columns={
    "SUBJECT_ID": "SUBJID",
    "GENDER": "SEX",
    "BIRTH_DATE": "BRTHDTC",
})
```

### Common Renamings

| Source | SDTM | Domain |
|--------|------|--------|
| SUBJECT_ID, PATIENT_ID | SUBJID | All |
| GENDER | SEX | DM |
| BIRTH_DATE, DOB | BRTHDTC | DM |
| SITE, SITE_NUMBER | SITEID | DM |
| VISIT_DATE | --DTC | All |
| ADVERSE_EVENT | AETERM | AE |
| MEDICATION_NAME | CMTRT | CM |

---

## Scenario 3: Variable Attribute Change

**Definition**: Variable attributes (label, type, length, format) must be changed to comply with SDTM standards.

### When to Use
- Variable name is correct but attributes differ
- Need to change data type (numeric to character, vice versa)
- Need to adjust length to SDTM specification

### Example

```python
# Change data types and lengths to match SDTM
source_df = pd.DataFrame({
    "SEX": ["Male", "Female"],  # Too long, should be "M" or "F"
    "AGE": ["45", "52"],  # String but should be numeric
})

# Apply attribute changes
sdtm_df = pd.DataFrame()
sdtm_df["SEX"] = source_df["SEX"].map({"Male": "M", "Female": "F"})  # Char(2)
sdtm_df["AGE"] = pd.to_numeric(source_df["AGE"])  # Numeric

# Set correct lengths and labels
# In practice, use XPT or Define.xml to enforce
```

### SDTM Attribute Standards

| Variable | Type | Length | Label |
|----------|------|--------|-------|
| STUDYID | Char | ≤ 20 | Study Identifier |
| DOMAIN | Char | 2 | Domain Abbreviation |
| USUBJID | Char | ≤ 40 | Unique Subject Identifier |
| --SEQ | Num | 8 | Sequence Number |
| --TESTCD | Char | 8 | Short Name of Test/Exam |
| --DTC | Char | ≤ 40 | Date/Time of Collection |

---

## Scenario 4: Combine

**Definition**: Multiple source variables must be combined to form a single SDTM variable.

### When to Use
- SDTM requires concatenated value
- Multiple source fields map to one SDTM variable
- Creating composite identifiers

### Example 1: USUBJID Creation

```python
# Combine STUDYID, SITEID, SUBJID → USUBJID
source_df = pd.DataFrame({
    "STUDY": ["PROTO-001", "PROTO-001"],
    "SITE": ["101", "102"],
    "PATIENT": ["0001", "0002"],
})

sdtm_df = pd.DataFrame()
sdtm_df["STUDYID"] = source_df["STUDY"]
sdtm_df["SITEID"] = source_df["SITE"]
sdtm_df["SUBJID"] = source_df["PATIENT"]

# Combine into USUBJID
sdtm_df["USUBJID"] = (
    sdtm_df["STUDYID"] + "-" +
    sdtm_df["SITEID"] + "-" +
    sdtm_df["SUBJID"]
)
# Result: "PROTO-001-101-0001"
```

### Example 2: Full Name from First/Last

```python
# Combine first and last name
source_df = pd.DataFrame({
    "FIRST_NAME": ["John", "Jane"],
    "LAST_NAME": ["Doe", "Smith"],
})

# Combine with space separator
sdtm_df["INVNAM"] = source_df["FIRST_NAME"] + " " + source_df["LAST_NAME"]
# Result: "John Doe", "Jane Smith"
```

### Common Combinations

| Source Fields | SDTM Variable | Separator |
|---------------|---------------|-----------|
| STUDYID, SITEID, SUBJID | USUBJID | "-" |
| DOSE, DOSE_UNIT | Dose description | " " |
| Year, Month, Day | --DTC (partial date) | "-" |

---

## Scenario 5: Split

**Definition**: A single source variable must be split into two or more SDTM variables.

### When to Use
- Source contains composite information
- SDTM requires separate components
- Parsing combined fields

### Example 1: Split Dose and Unit

```python
# Source: "10 mg" → EXDOSE = 10, EXDOSU = "mg"
source_df = pd.DataFrame({
    "DOSE_WITH_UNIT": ["10 mg", "20 mg", "5 mL"],
})

# Split into dose and unit
sdtm_df = pd.DataFrame()
sdtm_df[["EXDOSE", "EXDOSU"]] = source_df["DOSE_WITH_UNIT"].str.split(
    " ", n=1, expand=True
)
sdtm_df["EXDOSE"] = pd.to_numeric(sdtm_df["EXDOSE"])
# Result: EXDOSE=10, EXDOSU="mg"
```

### Example 2: Split Full Name

```python
# Source: "Doe, John" → Last="Doe", First="John"
source_df = pd.DataFrame({
    "FULL_NAME": ["Doe, John", "Smith, Jane"],
})

sdtm_df[["LAST_NAME", "FIRST_NAME"]] = source_df["FULL_NAME"].str.split(
    ", ", n=1, expand=True
)
```

### Example 3: Split Date Components

```python
# Source: "15-MAY-2024" → Year=2024, Month=05, Day=15
import datetime as dt

source_df = pd.DataFrame({
    "DATE_STR": ["15-MAY-2024", "22-JUN-2024"],
})

dates = pd.to_datetime(source_df["DATE_STR"], format="%d-%b-%Y")
sdtm_df["YEAR"] = dates.dt.year
sdtm_df["MONTH"] = dates.dt.month
sdtm_df["DAY"] = dates.dt.day
```

---

## Scenario 6: Derivation

**Definition**: SDTM variable values are derived/calculated from one or more source variables.

### When to Use
- SDTM requires calculated values
- Creating derived endpoints
- Computing from multiple sources

### Example 1: Age Derivation

```python
# Derive AGE from BRTHDTC and RFSTDTC
import pandas as pd
from datetime import datetime

def derive_age(birth_date, reference_date):
    """Derive age in years."""
    birth = pd.to_datetime(birth_date)
    ref = pd.to_datetime(reference_date)
    age_days = (ref - birth).dt.days
    age_years = (age_days / 365.25).round(0).astype('Int64')
    return age_years

source_df = pd.DataFrame({
    "BIRTH_DATE": ["1980-05-15", "1975-11-22"],
    "ENROLLMENT_DATE": ["2024-01-15", "2024-01-20"],
})

sdtm_df = pd.DataFrame()
sdtm_df["BRTHDTC"] = source_df["BIRTH_DATE"]
sdtm_df["RFSTDTC"] = source_df["ENROLLMENT_DATE"]
sdtm_df["AGE"] = derive_age(source_df["BIRTH_DATE"], source_df["ENROLLMENT_DATE"])
sdtm_df["AGEU"] = "YEARS"
```

### Example 2: BMI Derivation

```python
# Derive BMI from height and weight
def derive_bmi(weight_kg, height_cm):
    """Calculate BMI = weight(kg) / (height(m))^2"""
    height_m = height_cm / 100
    bmi = weight_kg / (height_m ** 2)
    return round(bmi, 1)

# In VS domain
vs_df.loc[vs_df["VSTESTCD"] == "BMI", "VSORRES"] = derive_bmi(
    weight=vs_df[vs_df["VSTESTCD"] == "WEIGHT"]["VSSTRESN"].values[0],
    height=vs_df[vs_df["VSTESTCD"] == "HEIGHT"]["VSSTRESN"].values[0]
)
vs_df.loc[vs_df["VSTESTCD"] == "BMI", "VSDRVFL"] = "Y"  # Mark as derived
```

### Example 3: Study Day Derivation

```python
# Derive --DY from --DTC and RFSTDTC
def derive_study_day(dtc, rfstdtc):
    """
    Calculate study day.
    Positive for on/after RFSTDTC, negative for before.
    No day 0.
    """
    dtc_date = pd.to_datetime(dtc)
    rf_date = pd.to_datetime(rfstdtc)

    diff_days = (dtc_date - rf_date).dt.days

    # Apply study day rules: no day 0
    study_day = diff_days.where(diff_days < 0, diff_days + 1)

    return study_day.astype('Int64')
```

### Common Derivations

| Derived Variable | Formula/Logic |
|------------------|---------------|
| AGE | (RFSTDTC - BRTHDTC) / 365.25 |
| BMI | WEIGHT(kg) / HEIGHT(m)² |
| --DY | Days from RFSTDTC (no day 0) |
| USUBJID | STUDYID + "-" + SUBJID |
| --STRESN | Numeric conversion of --ORRES |

---

## Scenario 7: Value Mapping

**Definition**: Source values need to be recoded or mapped to match SDTM controlled terminology or standard values.

### When to Use
- Applying controlled terminology
- Standardizing verbatim responses
- Recoding to CDISC CT values

### Example 1: SEX Mapping

```python
# Map various gender representations to SDTM SEX values
sex_map = {
    "M": "M",
    "Male": "M",
    "MALE": "M",
    "1": "M",
    "F": "F",
    "Female": "F",
    "FEMALE": "F",
    "2": "F",
    "U": "U",
    "Unknown": "U",
    "Not Reported": "U",
}

sdtm_df["SEX"] = source_df["GENDER"].map(sex_map)
```

### Example 2: RACE Mapping

```python
# Map source race codes to CDISC CT
race_map = {
    "1": "WHITE",
    "2": "BLACK OR AFRICAN AMERICAN",
    "3": "ASIAN",
    "4": "AMERICAN INDIAN OR ALASKA NATIVE",
    "5": "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER",
    "6": "MULTIPLE",
    "WHITE": "WHITE",
    "BLACK": "BLACK OR AFRICAN AMERICAN",
    "ASIAN": "ASIAN",
    "99": "NOT REPORTED",
}

sdtm_df["RACE"] = source_df["RACE_CODE"].map(race_map)
```

### Example 3: Adverse Event Outcome Mapping

```python
# Map AE outcomes to SDTM CT
outcome_map = {
    "RESOLVED": "RECOVERED/RESOLVED",
    "RECOVERED": "RECOVERED/RESOLVED",
    "RECOVERING": "RECOVERING/RESOLVING",
    "NOT RECOVERED": "NOT RECOVERED/NOT RESOLVED",
    "FATAL": "FATAL",
    "UNKNOWN": "UNKNOWN",
    "SEQUELAE": "RECOVERED/RESOLVED WITH SEQUELAE",
}

ae_df["AEOUT"] = source_df["OUTCOME"].map(outcome_map)
```

### Best Practices

1. **Map all possible values**: Include all CT values, not just those in current data
2. **Document unmapped values**: Log any source values that don't map
3. **Use extensible CT wisely**: Extend only when necessary
4. **Validate against CT**: Always check current CDISC CT version

---

## Scenario 8: Structure Transformation

**Definition**: The structure of the source dataset is completely different from SDTM and must be transformed (typically horizontal to vertical).

### When to Use
- Source data is in wide/horizontal format
- SDTM requires vertical/long format
- Findings domains (LB, VS, EG, etc.)

### Example: Horizontal to Vertical (Findings Domains)

```python
# Source: Horizontal (wide) format
source_df = pd.DataFrame({
    "SUBJECT_ID": ["001", "002"],
    "VISIT": ["WEEK 1", "WEEK 1"],
    "SYSBP": [120, 135],
    "DIABP": [80, 85],
    "PULSE": [72, 68],
    "TEMP": [98.6, 98.2],
})

# SDTM: Vertical (long) format
# Define test mapping
test_map = {
    "SYSBP": ("SYSBP", "Systolic Blood Pressure", "mmHg"),
    "DIABP": ("DIABP", "Diastolic Blood Pressure", "mmHg"),
    "PULSE": ("PULSE", "Pulse Rate", "BEATS/MIN"),
    "TEMP": ("TEMP", "Temperature", "F"),
}

# Melt to long format
id_vars = ["SUBJECT_ID", "VISIT"]
value_vars = ["SYSBP", "DIABP", "PULSE", "TEMP"]

vs_df = source_df.melt(
    id_vars=id_vars,
    value_vars=value_vars,
    var_name="TEST_CODE",
    value_name="VSORRES"
)

# Add SDTM variables
vs_df["VSTESTCD"] = vs_df["TEST_CODE"]
vs_df["VSTEST"] = vs_df["VSTESTCD"].map(lambda x: test_map[x][1])
vs_df["VSORRESU"] = vs_df["VSTESTCD"].map(lambda x: test_map[x][2])

# Add identifiers
vs_df["STUDYID"] = "STUDY-001"
vs_df["DOMAIN"] = "VS"
vs_df["USUBJID"] = "STUDY-001-" + vs_df["SUBJECT_ID"]
vs_df["VSSEQ"] = vs_df.groupby("USUBJID").cumcount() + 1

# Result: Vertical SDTM VS domain
```

### Tips for Structure Transformation

1. **Use pandas.melt()** for horizontal → vertical
2. **Use pandas.pivot()** for vertical → horizontal (rare in SDTM)
3. **Maintain all metadata** during transformation
4. **Create --SEQ** after transformation
5. **Drop null results** (or use --STAT = "NOT DONE")

---

## Scenario 9: Supplemental Qualifiers

**Definition**: Variables that cannot be mapped to standard SDTM variables go into SUPP-- (Supplemental Qualifiers) datasets.

### When to Use
- Source variable is study-specific
- No corresponding SDTM variable exists
- Variable is important but not in domain spec

### Example: SUPPAE (Supplemental AE Qualifiers)

```python
# Source AE data has study-specific fields
source_ae = pd.DataFrame({
    "SUBJECT_ID": ["001", "001"],
    "AE_TERM": ["Headache", "Nausea"],
    "AE_SEQ": [1, 2],
    # Study-specific fields ↓
    "INVESTIGATOR_COMMENT": ["Mild, resolved quickly", "Moderate"],
    "PRIOR_SAME_EVENT": ["N", "Y"],
    "HOSPITALIZED_DAYS": [0, 0],
})

# Main AE domain
ae_df = pd.DataFrame({
    "STUDYID": "STUDY-001",
    "DOMAIN": "AE",
    "USUBJID": ["STUDY-001-001", "STUDY-001-001"],
    "AESEQ": [1, 2],
    "AETERM": ["HEADACHE", "NAUSEA"],
})

# Create SUPPAE for study-specific variables
suppae_records = []

for _, row in source_ae.iterrows():
    usubjid = f"STUDY-001-{row['SUBJECT_ID']}"
    aeseq = row['AE_SEQ']

    # Add each supplemental qualifier as a record
    if pd.notna(row['INVESTIGATOR_COMMENT']):
        suppae_records.append({
            "STUDYID": "STUDY-001",
            "RDOMAIN": "AE",
            "USUBJID": usubjid,
            "IDVAR": "AESEQ",
            "IDVARVAL": str(aeseq),
            "QNAM": "INVCOMM",
            "QLABEL": "Investigator Comment",
            "QVAL": row['INVESTIGATOR_COMMENT'],
            "QORIG": "CRF",
        })

    if pd.notna(row['PRIOR_SAME_EVENT']):
        suppae_records.append({
            "STUDYID": "STUDY-001",
            "RDOMAIN": "AE",
            "USUBJID": usubjid,
            "IDVAR": "AESEQ",
            "IDVARVAL": str(aeseq),
            "QNAM": "PRIORAE",
            "QLABEL": "Prior Same Event",
            "QVAL": row['PRIOR_SAME_EVENT'],
            "QORIG": "CRF",
        })

suppae_df = pd.DataFrame(suppae_records)
suppae_df["QEVAL"] = ""  # Optional
```

### SUPP-- Structure

| Variable | Description |
|----------|-------------|
| STUDYID | Study Identifier |
| RDOMAIN | Related Domain (AE, DM, VS, etc.) |
| USUBJID | Unique Subject Identifier |
| IDVAR | Identifying Variable (--SEQ, USUBJID) |
| IDVARVAL | Value of IDVAR |
| QNAM | Qualifier Variable Name (8 char max) |
| QLABEL | Qualifier Variable Label |
| QVAL | Data Value |
| QORIG | Origin (CRF, DERIVED, ASSIGNED) |
| QEVAL | Evaluator (optional) |

### SUPP-- Rules

1. **QNAM must be ≤ 8 characters**
2. **Cannot start with a number**
3. **Use for truly study-specific variables only**
4. **Document in Define.xml**
5. **One SUPP-- record per qualifier per parent record**

---

## Summary: When to Use Each Scenario

| Scenario | Condition | Example |
|----------|-----------|---------|
| 1. Direct Carry Forward | Variable already SDTM-compliant | STUDYID, USUBJID |
| 2. Rename | Different name, same values | GENDER → SEX |
| 3. Attribute Change | Change type/length | SEX: "Male" → "M" (length 2) |
| 4. Combine | Multiple fields → one | STUDYID + SUBJID → USUBJID |
| 5. Split | One field → multiple | "10 mg" → EXDOSE=10, EXDOSU="mg" |
| 6. Derivation | Calculate from other variables | AGE from BRTHDTC |
| 7. Value Map | Recode to CT | "RESOLVED" → "RECOVERED/RESOLVED" |
| 8. Structure Transform | Wide → long format | Horizontal vitals → vertical VS |
| 9. Supplemental Qualifiers | No standard SDTM variable | Study-specific fields → SUPP-- |

## Instructions for Agent

When mapping source data to SDTM:

1. **Analyze each source variable** against the 9 scenarios
2. **Use mapping specification** to document which scenario applies
3. **Apply scenarios in order** (e.g., rename first, then derive)
4. **Validate results** after each transformation
5. **Document assumptions** for complex scenarios
6. **Use SUPP-- sparingly** - try to fit in standard variables first

## Available Tools

- `generate_mapping_spec` - Creates mapping specification with scenario identification
- `transform_to_sdtm` - Applies appropriate scenario transformations
- `validate_mapping` - Checks transformation results

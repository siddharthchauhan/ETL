---
name: findings-domains
description: Use this skill for Findings class SDTM domains (LB, VS, EG, PE, QS, SC, FA, PC, PP, MB, MS, MI, RP, DD, FT, GF, IS, CP). Covers vertical data structures, test code standardization, result handling (original vs standardized), reference ranges, baseline flags, specimen-based findings, and the unique --TESTCD/--TEST/--ORRES/--STRESC pattern. Essential for laboratory, vital signs, pharmacokinetics, and all observational data transformations. Based on CDISC SDTMIG v3.4 and v4.0 specifications.
---

# Findings Domains Skill - Complete Guide (LB, VS, EG, PE, QS, PC, PP, MB, MS, MI, and more)

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

### QS - Questionnaires (Covered in detail in questionnaires-pro skill)

**Purpose**: Capture questionnaire/scale responses and Patient-Reported Outcomes (PRO).

**Structure**: Vertical, one row per question

#### Key Variables

| Variable | Label | Description |
|----------|-------|-------------|
| QSCAT | Category | Questionnaire name (e.g., HAM-D, SF-36, EQ-5D) |
| QSSCAT | Subcategory | Subscale name |
| QSTESTCD | Question Code | Q01, Q02, etc. (8 char max) |
| QSTEST | Question Text | Full question text |
| QSORRES | Response | Patient response (original) |
| QSSTRESC | Standardized Response | Character representation |
| QSSTRESN | Numeric Score | Numeric value |
| QSEVLINT | Evaluation Interval | ISO 8601 recall period |

**Note**: Only collected data goes in QS domain. All scoring derivations must be done in ADaM. See questionnaires-pro skill for comprehensive guidance.

---

### PC - Pharmacokinetics Concentrations

**Purpose**: Capture drug concentration measurements in biological matrices.

**Structure**: Vertical, one record per specimen per time point per analyte

#### Required Variables

| Variable | Label | Description |
|----------|-------|-------------|
| STUDYID | Study Identifier | |
| DOMAIN | Domain Abbreviation | "PC" |
| USUBJID | Unique Subject ID | |
| PCSEQ | Sequence Number | |
| PCTESTCD | Analyte Code | Drug/metabolite code |
| PCTEST | Analyte Name | Full drug/metabolite name |
| PCORRES | Result | Concentration value |
| PCORRESU | Original Units | ng/mL, ug/mL, etc. |

#### Standard Test Codes

| PCTESTCD | PCTEST | Description |
|----------|--------|-------------|
| DRUGX | Drug X | Parent drug |
| DRUGXM1 | Drug X Metabolite 1 | Active metabolite |
| DRUGXM2 | Drug X Metabolite 2 | Inactive metabolite |

#### Expected Variables

| Variable | Label | Description |
|----------|-------|-------------|
| PCSPEC | Specimen Type | BLOOD, PLASMA, SERUM, URINE, CSF |
| PCMETHOD | Method | LC-MS/MS, HPLC, etc. |
| PCLLOQ | Lower Limit of Quantification | Assay sensitivity |
| PCSTRESC | Standardized Result | Character result |
| PCSTRESN | Numeric Result | Numeric concentration |
| PCSTRESU | Standard Units | Standardized units |
| PCDTC | Collection Date/Time | ISO 8601 |
| PCTPT | Planned Time Point | 0.5HR, 1HR, 2HR, etc. |
| PCTPTNUM | Planned Time Point Num | Numeric time |
| PCELTM | Elapsed Time | Time since dose (ISO 8601 duration) |
| PCNOMDY | Nominal Day | Study day |
| VISIT | Visit Name | |
| PCFAST | Fasting Status | Y, N |

#### BLQ (Below Limit of Quantification) Handling

```python
def handle_blq_values(df):
    """
    Handle BLQ (Below Limit of Quantification) values.

    Common approaches:
    - PCORRES = "BLQ" or "< LLOQ"
    - PCSTRESC = "BLQ"
    - PCSTRESN = null or LLOQ/2
    """
    # Identify BLQ records
    blq_mask = df["PCORRES"].str.contains("BLQ|< LLOQ|<LLOQ", case=False, na=False)

    df.loc[blq_mask, "PCSTRESC"] = "BLQ"
    df.loc[blq_mask, "PCSTRESN"] = pd.NA  # or use LLOQ/2 if specified

    return df
```

---

### PP - Pharmacokinetics Parameters

**Purpose**: Capture derived pharmacokinetic parameters.

**Structure**: Vertical, one record per parameter per subject (and possibly per time interval)

#### Standard Test Codes (PPTESTCD)

| PPTESTCD | PPTEST | Description |
|----------|--------|-------------|
| AUCALL | AUC All | Area Under Curve - all time points |
| AUCINF | AUC Infinity | AUC extrapolated to infinity |
| AUCLST | AUC Last | AUC to last measurable concentration |
| CMAX | Maximum Concentration | Peak concentration |
| TMAX | Time of CMAX | Time to peak |
| T12 | Half-Life | Terminal elimination half-life |
| CL | Clearance | Total body clearance |
| VDSS | Volume of Distribution | Volume at steady state |

#### Key Variables

| Variable | Label | Description |
|----------|-------|-------------|
| PPCAT | Category | Single Dose, Steady State |
| PPSCAT | Subcategory | Dose level |
| PPORRES | Result | Parameter value (as derived) |
| PPORRESU | Original Units | hr, hr*ng/mL, L, etc. |
| PPDRVFL | Derived Flag | Always "Y" |

**Note**: PP domain contains only derived parameters. All derivation details should be documented in the Analysis Data Reviewer's Guide (ADRG).

---

### MB - Microbiology Specimens

**Purpose**: Capture microbiology specimen results.

**Structure**: Vertical, one record per organism per specimen

#### Standard Test Codes

| MBTESTCD | MBTEST | Description |
|----------|--------|-------------|
| CULT | Culture | Specimen culture result |
| ORGANISM | Organism | Organism identified |
| COLCNT | Colony Count | Number of colonies |
| SENSIT | Sensitivity | Antibiotic sensitivity |

#### Expected Variables

| Variable | Label | Values |
|----------|-------|--------|
| MBSPEC | Specimen Type | BLOOD, URINE, SPUTUM, WOUND |
| MBMETHOD | Method | Culture method |
| MBORRES | Result | POSITIVE, NEGATIVE, organism name |
| MBMODIFY | Organism Modifier | e.g., RARE, MODERATE, HEAVY |

---

### MS - Microbiology Susceptibility

**Purpose**: Capture antibiotic susceptibility test results.

**Structure**: Vertical, one record per organism-antibiotic combination

#### Key Variables

| Variable | Label | Description |
|----------|-------|-------------|
| MSGRPID | Group ID | Links to parent MB record |
| MSTESTCD | Antibiotic Code | AMOX, CIPRO, GENT, etc. |
| MSTEST | Antibiotic Name | Amoxicillin, Ciprofloxacin |
| MSORRES | Result | SUSCEPTIBLE, INTERMEDIATE, RESISTANT |
| MSSTRESC | Standardized Result | S, I, R |

---

### MI - Microscopic Findings

**Purpose**: Capture microscopic examination findings (histopathology).

**Structure**: Vertical, one record per specimen per finding

#### Key Variables

| Variable | Label | Description |
|----------|-------|-------------|
| MISPEC | Specimen Type | Tissue type |
| MILOC | Specimen Location | Anatomical location |
| MITSTDTL | Tissue Detail | Additional specimen detail |
| MITESTCD | Test Code | Finding code |
| MITEST | Test Name | Finding description |
| MIORRES | Original Result | Severity, grade, etc. |

---

### DD - Death Details

**Purpose**: Capture detailed information about subject deaths.

**Structure**: Vertical, one record per death detail

#### Standard Test Codes

| DDTESTCD | DDTEST | Description |
|----------|--------|-------------|
| DTHCAUS | Primary Cause of Death | Main cause |
| DTHCAT | Death Category | Disease-related, AE, etc. |
| AUTOPSY | Autopsy Performed | Y, N |
| DTHDOM | Contributing Domain | AE, DS, etc. |

---

### FT - Fetal/Infant Findings

**Purpose**: Capture fetal assessments and infant findings.

**Structure**: Vertical findings structure

#### Common Test Codes

| FTTESTCD | FTTEST | Description |
|----------|--------|-------------|
| FTHT | Fetal Height | Crown-rump length |
| FTWT | Fetal Weight | Estimated weight |
| HR | Heart Rate | Fetal heart rate |
| LUNGMAT | Lung Maturity | Lung maturity indicator |

---

## Specimen-Based Findings Domains

**Reference**: SDTMIG v3.4 Section 6.3.5 groups specimen-based lab domains (CP, GF, IS, LB) with a generic specification.

### Common Specimen-Based Variables

All specimen-based findings domains share these variables:

| Variable | Label | Description |
|----------|-------|-------------|
| --SPEC | Specimen Type | BLOOD, PLASMA, SERUM, URINE, TISSUE |
| --SPCCND | Specimen Condition | HEMOLYZED, CLOTTED, LIPEMIC |
| --SPECX | Specimen Detail | Additional specimen details |
| --METHOD | Test Method | Assay or analysis method |
| --ANMETH | Analysis Method | Detailed analytical method |

### CP - Cell Phenotyping

**Purpose**: Capture flow cytometry and immunophenotyping results.

#### Example Test Codes

| CPTESTCD | CPTEST | Description |
|----------|--------|-------------|
| CD3 | CD3+ Cells | T-cell marker |
| CD4 | CD4+ Cells | Helper T-cells |
| CD8 | CD8+ Cells | Cytotoxic T-cells |
| CD19 | CD19+ Cells | B-cell marker |

---

### GF - Genetic Findings

**Purpose**: Capture genetic test results.

#### Common Test Codes

| GFTESTCD | GFTEST | Description |
|----------|--------|-------------|
| GENOTYPE | Genotype | Genetic variant |
| ALLELE | Allele | Specific allele |
| MUTATION | Mutation | Mutation presence/type |

---

### IS - Immunogenicity Specimens

**Purpose**: Capture anti-drug antibody (ADA) and immunogenicity test results.

#### Standard Test Codes

| ISTESTCD | ISTEST | Description |
|----------|--------|-------------|
| ADA | Anti-Drug Antibody | ADA screen result |
| ADATITR | ADA Titer | Antibody titer value |
| NADA | Neutralizing ADA | Neutralizing antibody |

#### Expected Variables

| Variable | Label | Values |
|----------|-------|--------|
| ISORRES | Result | POSITIVE, NEGATIVE, INDETERMINATE |
| ISSTRESC | Standardized Result | POSITIVE, NEGATIVE |
| ISSTRESN | Numeric Result | Titer value |

---

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

### Common Rules (All Findings Domains)

| Rule ID | Check | Severity | FDA/P21 Rule |
|---------|-------|----------|--------------|
| FD0001 | --TESTCD is not null | ERROR | SD1002 |
| FD0002 | --TEST is not null | ERROR | SD1002 |
| FD0003 | --ORRES or --STAT populated | ERROR | SD1073 |
| FD0004 | If --STAT = 'NOT DONE', --REASND populated | WARNING | SD1074 |
| FD0005 | --STRESN is numeric when populated | ERROR | SD1009 |
| FD0006 | --STRESU standardized units consistent | WARNING | SD1022 |
| FD0007 | Only one --BLFL = 'Y' per subject/test | ERROR | SD1229 |
| FD0008 | --TESTCD is 8 characters or less | ERROR | SD1001 |
| FD0009 | --TESTCD conforms to CT (if non-extensible) | ERROR | SD1091 |
| FD0010 | --DTC is valid ISO 8601 format | ERROR | SD1025 |
| FD0011 | --STRESC is populated when --ORRES exists | WARNING | SD1015 |
| FD0012 | --STRESN = null when --ORRES is non-numeric | INFO | - |

### Domain-Specific Rules

#### Laboratory (LB)

| Rule ID | Check | Severity | Rationale |
|---------|-------|----------|-----------|
| LB0001 | LBSPEC is from CT | ERROR | Standardization |
| LB0002 | LBSTNRLO <= LBSTRESN <= LBSTNRHI consistency | WARNING | Reference range logic |
| LB0003 | LBNRIND value matches numeric ranges | WARNING | Derived correctly |
| LB0004 | LBFAST populated for fasting tests | WARNING | Protocol requirement |
| LB0005 | LBMETHOD populated for central labs | INFO | Traceability |
| LB0006 | Unit conversion documented for STRESN | INFO | Reproducibility |
| LB0007 | LBSPEC consistent within LBGRPID | ERROR | Same collection |

#### Vital Signs (VS)

| Rule ID | Check | Severity | Rationale |
|---------|-------|----------|-----------|
| VS0001 | VSTESTCD is from CT | ERROR | Standardization |
| VS0002 | VSPOS populated for BP measurements | WARNING | Clinical requirement |
| VS0003 | VSLOC populated for temperature/BP | WARNING | Anatomical location |
| VS0004 | Reasonable value ranges (e.g., TEMP 35-42°C) | WARNING | Data quality |
| VS0005 | SYSBP > DIABP when both present | WARNING | Physiological validity |

#### ECG (EG)

| Rule ID | Check | Severity | Rationale |
|---------|-------|----------|-----------|
| EG0001 | EGLEAD populated for interval measurements | WARNING | Specificity |
| EG0002 | EGPOS populated | WARNING | Position affects results |
| EG0003 | EGMETHOD populated | INFO | Standardization |
| EG0004 | QT intervals have HR for QTc derivation | WARNING | Calculation requirement |

#### Pharmacokinetics (PC)

| Rule ID | Check | Severity | Rationale |
|---------|-------|----------|-----------|
| PC0001 | PCTPT or PCELTM populated | ERROR | Timing required |
| PC0002 | PCLLOQ populated | WARNING | Assay sensitivity |
| PC0003 | BLQ records handled consistently | WARNING | Analysis impact |
| PC0004 | PCSPEC is from CT | ERROR | Standardization |
| PC0005 | PCMETHOD describes assay | INFO | Reproducibility |

### Common FDA Conformance Issues (Based on Validation Reports)

#### Issue 1: USUBJID/VISIT/VISITNUM Inconsistency

**Problem**: Values in findings domains not matching SV (Subject Visits) domain

**Solution**:
```python
# Validate VISIT values against SV domain
def validate_visits_against_sv(findings_df, sv_df):
    """Ensure all visits in findings exist in SV."""
    findings_visits = set(zip(findings_df["USUBJID"], findings_df["VISITNUM"]))
    sv_visits = set(zip(sv_df["USUBJID"], sv_df["VISITNUM"]))

    missing = findings_visits - sv_visits
    if missing:
        print(f"WARNING: {len(missing)} visit records in findings not in SV")
    return missing
```

#### Issue 2: Controlled Terminology Violations

**Problem**: Values not found in CDISC CT when using non-extensible codelists

**Solution**: Always validate against current CT version
```python
# Check against CDISC CT
ct_valid_values = {
    "LBSPEC": ["BLOOD", "PLASMA", "SERUM", "URINE", "SALIVA"],
    "VSPOS": ["STANDING", "SITTING", "SUPINE", "TRENDELENBURG"],
    "PCSPEC": ["BLOOD", "PLASMA", "SERUM", "URINE", "CSF"],
}

def validate_ct(df, variable, domain):
    """Check values against CT."""
    if variable in ct_valid_values:
        invalid = ~df[variable].isin(ct_valid_values[variable])
        if invalid.any():
            print(f"ERROR: Invalid {variable} values:", df[invalid][variable].unique())
```

#### Issue 3: Missing Reference Ranges

**Problem**: LBSTNRLO/LBSTNRHI not populated when reference ranges exist

**Solution**: Always include reference ranges when available from lab
```python
# Populate reference ranges
def add_reference_ranges(df, ref_range_map):
    """
    Add standardized reference ranges.

    ref_range_map = {
        ("ALT", "U/L", "M"): (10, 40),
        ("ALT", "U/L", "F"): (7, 35),
    }
    """
    for idx, row in df.iterrows():
        key = (row["LBTESTCD"], row["LBSTRESU"], row["SEX"])
        if key in ref_range_map:
            df.loc[idx, "LBSTNRLO"] = ref_range_map[key][0]
            df.loc[idx, "LBSTNRHI"] = ref_range_map[key][1]
    return df
```

## Common Mistakes and How to Avoid Them

### Mistake 1: Not Dropping Null-Only Variables (Pre-SDTMIG 3.3)

**Issue**: Including variables with all null values in datasets submitted under SDTMIG 3.2 or earlier

**Solution**:
```python
def drop_null_variables(df, sdtmig_version="3.4"):
    """Drop variables with all null values for older SDTMIG versions."""
    if float(sdtmig_version) < 3.3:
        null_cols = df.columns[df.isnull().all()]
        df = df.drop(columns=null_cols)
        print(f"Dropped {len(null_cols)} null-only variables: {list(null_cols)}")
    return df
```

**Note**: Blank variables are allowed in SDTMIG 3.3 and later.

### Mistake 2: Incorrect Baseline Flag Assignment

**Issue**: Multiple baseline flags per subject-test OR no baseline when one exists

**Best Practice**:
- Last non-missing value on or before first treatment date
- If protocol specifies baseline visit, use that visit
- Only ONE --BLFL = 'Y' per subject per --TESTCD

```python
def assign_baseline_correctly(df, domain, treatment_start_col="RFSTDTC"):
    """Assign baseline flag using last pre-treatment value."""
    blfl_col = f"{domain}BLFL"
    date_col = f"{domain}DTC"
    test_col = f"{domain}TESTCD"

    # Sort by date
    df = df.sort_values([" USUBJID", test_col, date_col])

    def get_baseline(group):
        # Get treatment start date from DM or elsewhere
        # Select last record on or before treatment start
        baseline_idx = group[group[date_col] <= treatment_start].index[-1]
        group.loc[baseline_idx, blfl_col] = "Y"
        return group

    df = df.groupby(["USUBJID", test_col], group_keys=False).apply(get_baseline)
    return df
```

### Mistake 3: Inconsistent Unit Handling

**Issue**: Mixing original and standardized units; not converting consistently

**Best Practice**:
- Always populate --ORRESU (original units)
- Convert to standard units for --STRESU
- Document conversion factors
- Be consistent within each --TESTCD

```python
# Define standard units for each test
STANDARD_UNITS = {
    "GLUC": "mmol/L",
    "HGB": "g/L",
    "CREAT": "umol/L",
    "WEIGHT": "kg",
    "HEIGHT": "cm",
    "TEMP": "C",
}

def standardize_units(df, domain):
    """Convert to standard units consistently."""
    test_col = f"{domain}TESTCD"
    orres_col = f"{domain}ORRES"
    orresu_col = f"{domain}ORRESU"
    stresn_col = f"{domain}STRESN"
    stresu_col = f"{domain}STRESU"

    for testcd, std_unit in STANDARD_UNITS.items():
        mask = df[test_col] == testcd
        df.loc[mask, stresu_col] = std_unit
        # Apply conversion logic here
    return df
```

### Mistake 4: Not Handling "NOT DONE" Tests

**Issue**: Leaving --ORRES null without --STAT when test was not performed

**Correct Approach**:
```python
def handle_not_done(df, domain):
    """Properly handle tests not performed."""
    orres_col = f"{domain}ORRES"
    stat_col = f"{domain}STAT"
    reasnd_col = f"{domain}REASND"

    # When test was scheduled but not performed
    not_done_mask = df[orres_col].isnull() & df["TEST_SCHEDULED"]

    df.loc[not_done_mask, stat_col] = "NOT DONE"
    df.loc[not_done_mask, reasnd_col] = df.loc[not_done_mask, "REASON"]  # From source

    return df
```

### Mistake 5: Forgetting Derived Flag

**Issue**: Not marking calculated values with --DRVFL

**Derived Values to Flag**:
- BMI (derived from height and weight)
- BSA (body surface area)
- GFR/eGFR (estimated glomerular filtration rate)
- LDL (calculated from lipid panel)
- QTcB, QTcF (corrected QT intervals)

```python
# Mark derived tests
DERIVED_TESTS = ["BMI", "BSA", "GFR", "EGFR", "LDL", "QTCB", "QTCF"]

def mark_derived_flags(df, domain):
    """Set --DRVFL = 'Y' for calculated values."""
    drvfl_col = f"{domain}DRVFL"
    testcd_col = f"{domain}TESTCD"

    df.loc[df[testcd_col].isin(DERIVED_TESTS), drvfl_col] = "Y"
    return df
```

## Tips and Tricks from Industry Experts

### Tip 1: Use Mappings Dictionary for Test Codes

```python
# Comprehensive test code mapping
VS_TEST_MAP = {
    # Source column: (TESTCD, TEST, UNIT)
    "SBP": ("SYSBP", "Systolic Blood Pressure", "mmHg"),
    "DBP": ("DIABP", "Diastolic Blood Pressure", "mmHg"),
    "HR": ("PULSE", "Pulse Rate", "BEATS/MIN"),
    "BODY_TEMP": ("TEMP", "Temperature", "C"),
    "WT": ("WEIGHT", "Weight", "kg"),
    "HT": ("HEIGHT", "Height", "cm"),
}
```

### Tip 2: Validate Early and Often

**PharmaSUG Best Practice**: "Validate as soon as possible. The sooner you validate, the more likely you can fix issues."

```python
# Run Pinnacle 21 or custom validation after each transformation
def validate_findings_domain(df, domain):
    """Quick validation checks before full P21 run."""
    checks = {
        "Null TESTCD": df[f"{domain}TESTCD"].isnull().sum(),
        "Null TEST": df[f"{domain}TEST"].isnull().sum(),
        "ORRES and STAT both null": ((df[f"{domain}ORRES"].isnull()) &
                                       (df[f"{domain}STAT"].isnull())).sum(),
        "Multiple baselines": df[df[f"{domain}BLFL"] == "Y"].groupby(
            ["USUBJID", f"{domain}TESTCD"]).size().gt(1).sum(),
    }

    for check, count in checks.items():
        if count > 0:
            print(f"WARNING: {check}: {count} records")
```

### Tip 3: Document Your Assumptions

Keep a mapping specification document that includes:
- How you determined baseline
- Unit conversion factors
- Handling of "trace", "negative", "positive" text results
- How BLQ values were coded
- Reference range sources

### Tip 4: Handle Timing Variables Consistently

```python
def add_timing_variables(df, domain):
    """
    Add standard timing variables for findings.

    --DTC: Collection date/time (ISO 8601)
    --DY: Study day (integer)
    --TPT: Planned time point name
    --TPTNUM: Planned time point number
    --ELTM: Elapsed time from reference (ISO 8601 duration)
    """
    # Calculate study day
    df[f"{domain}DY"] = (pd.to_datetime(df[f"{domain}DTC"]) -
                         pd.to_datetime(df["RFSTDTC"])).dt.days + 1

    # Set negative for pre-treatment
    df.loc[df[f"{domain}DTC"] < df["RFSTDTC"], f"{domain}DY"] = (
        (pd.to_datetime(df[f"{domain}DTC"]) -
         pd.to_datetime(df["RFSTDTC"])).dt.days
    )

    return df
```

### Tip 5: Leverage Reusable Functions

Create domain-agnostic functions:

```python
def create_findings_domain(source_df, domain, study_id, test_map):
    """
    Generic findings domain creator.

    Args:
        source_df: Source DataFrame
        domain: Two-letter domain code (VS, LB, EG)
        study_id: Study identifier
        test_map: Dictionary mapping source to SDTM test codes
    """
    records = []

    for _, row in source_df.iterrows():
        usubjid = f"{study_id}-{row['SUBJECT_ID']}"

        for src_col, (testcd, test, unit) in test_map.items():
            if src_col in row and pd.notna(row[src_col]):
                records.append({
                    "STUDYID": study_id,
                    "DOMAIN": domain,
                    "USUBJID": usubjid,
                    f"{domain}TESTCD": testcd,
                    f"{domain}TEST": test,
                    f"{domain}ORRES": str(row[src_col]),
                    f"{domain}ORRESU": unit,
                    f"{domain}DTC": row.get("TEST_DATE", ""),
                    "VISITNUM": row.get("VISIT_NUM", ""),
                    "VISIT": row.get("VISIT", ""),
                })

    df = pd.DataFrame(records)
    df[f"{domain}SEQ"] = df.groupby("USUBJID").cumcount() + 1

    # Add standard processing
    df = standardize_results(df, domain)
    df = assign_baseline_flag(df, domain)
    df = mark_derived_flags(df, domain)

    return df
```

## Instructions for Agent

When transforming Findings domains:

1. **REQUIRED FIRST**: Generate mapping specification using `generate_mapping_spec`
2. **Transpose**: Convert horizontal source to vertical format using melt/unpivot
3. **Standardize Test Codes**: Use CDISC CT for --TESTCD (8 char max)
4. **Handle Missing**: Use --STAT = 'NOT DONE' with --REASND when test not performed
5. **Standardize Results**: Convert to standard units in --STRESN/--STRESU with conversion factor documentation
6. **Assign Baseline**: Apply --BLFL logic consistently (last pre-treatment value)
7. **Mark Derived**: Flag calculated values with --DRVFL = 'Y'
8. **Include Reference Ranges**: Populate --STNRLO/--STNRHI for labs (sex/age-specific when applicable)
9. **Validate Early**: Check against CDISC CT and FDA conformance rules before final submission
10. **Document**: Maintain clear mapping specifications and transformation rules

## Available Tools

- `lookup_sdtm_domain` - Get domain structure for VS, LB, EG, etc.
- `validate_controlled_terminology` - Check test codes against CT
- `transform_to_sdtm` - Generic transformation
- `convert_domain` - High-level conversion
- `get_sdtm_guidance` - Get Findings domain guidance

# VS Domain Mapping Specification - Quick Reference Guide

**Study:** MAXIS-08 | **Domain:** VS (Vital Signs) | **Source:** VITALS.csv

---

## Transformation Overview

| Metric | Value |
|--------|-------|
| Source Records | 536 |
| Target Records | 2,184 |
| Expansion Ratio | 4.07:1 (wide → long format) |
| SDTM Variables | 28 |
| SDTM-IG Version | 3.4 |
| Required Variables | 6/6 (100%) |
| Expected Variables | 12/12 (100%) |

---

## Quick Mapping Reference

### Core Identifier Mappings

| Target Variable | Source | Transformation | Example |
|----------------|--------|----------------|---------|
| STUDYID | STUDY | Direct copy | MAXIS-08 |
| DOMAIN | - | Constant 'VS' | VS |
| USUBJID | STUDY + INVSITE + PT | Concatenate with '-' | MAXIS-08-408-001 |
| VSSEQ | - | Row number per subject | 1, 2, 3, ... |

### Vital Sign Test Mappings

| Source Column | VSTESTCD | VSTEST | Unit | Example Value |
|--------------|----------|--------|------|---------------|
| VTBPS2 | SYSBP | Systolic Blood Pressure | mmHg | 120.0 |
| VTBPD2 | DIABP | Diastolic Blood Pressure | mmHg | 96.0 |
| VTRRT2 | RESP | Respiratory Rate | breaths/min | 16.0 |
| VTTP2 | TEMP | Temperature | C | 36.8 |
| GNNUM1 | WEIGHT | Weight | kg | 68.9 |
| GNNUM2 | HEIGHT | Height | cm | 185.0 |

### Result Variables

| Target Variable | Source | Description | Data Type |
|----------------|--------|-------------|-----------|
| VSORRES | [Test column] | Original result | Character |
| VSORRESU | Derived | Original unit | Character |
| VSSTRESC | VSORRES standardized | Standardized result (char) | Character |
| VSSTRESN | VSORRES numeric | Standardized result (num) | Numeric |
| VSSTRESU | Derived | Standard unit | Character |

### Timing Variables

| Target Variable | Source | Transformation | Example |
|----------------|--------|----------------|---------|
| VISITNUM | VISIT | Direct or derived | 1 |
| VISIT | VISIT | Convert to string | "1" |
| VSDTC | VTDT + VTTM | ISO 8601 format | 2008-08-26 |

---

## Key Transformation Rules

### 1. Wide-to-Long Conversion
```
1 source record with 6 vital signs → 6 VS records

Example:
Source: VTBPS2=120, VTBPD2=96, VTRRT2=16, VTTP2=36.8, GNNUM1=68.9, GNNUM2=185
Target: 6 separate records with VSTESTCD = SYSBP, DIABP, RESP, TEMP, WEIGHT, HEIGHT
```

### 2. USUBJID Construction
```
Format: STUDY-SITE-SUBJECT
Example: MAXIS-08-408-001

Algorithm:
1. STUDY from STUDY column
2. SITE from last part of INVSITE (after underscore)
3. SUBJECT from PT column
```

### 3. Sequence Numbering
```
Sort by: USUBJID → VSDTC → VSTESTCD
Number: 1, 2, 3, ... within each USUBJID
```

### 4. Date/Time Formatting
```
Source: VTDT (date), VTTM (time optional)
Target: ISO 8601 format

Examples:
VTDT='2008-08-26' → VSDTC='2008-08-26'
VTDT='2008-08-26', VTTM='10:30' → VSDTC='2008-08-26T10:30'
```

### 5. Unit Conversions

| Test | Original Unit | Conversion | Standard Unit |
|------|--------------|------------|---------------|
| TEMP | Fahrenheit (F) | (F - 32) × 5/9 | Celsius (C) |
| WEIGHT | Pounds (lbs) | lbs × 0.453592 | Kilograms (kg) |
| HEIGHT | Inches (in) | in × 2.54 | Centimeters (cm) |

---

## Data Quality Checks

### Critical Validations

✅ **Required Variables**
- STUDYID, DOMAIN, USUBJID, VSSEQ, VSTESTCD, VSTEST must not be null

✅ **Logical Consistency**
- SYSBP > DIABP (systolic > diastolic)
- Height should not change >2 cm between visits
- Weight change >10 kg should be reviewed

✅ **Range Checks**
| Test | Normal Range | Flag If |
|------|-------------|---------|
| SYSBP | 90-180 mmHg | <90 or >180 |
| DIABP | 50-120 mmHg | <50 or >120 |
| PULSE | 50-120 beats/min | <50 or >120 |
| RESP | 12-24 breaths/min | <12 or >24 |
| TEMP | 36.0-38.5 °C | <36.0 or >38.5 |

✅ **Unit Validation**
- All BP measurements must use mmHg
- All temperatures must be converted to °C
- All weights must be converted to kg
- All heights must be converted to cm

---

## Controlled Terminology

### VSTESTCD Values (Used in MAXIS-08)
- **SYSBP** - Systolic Blood Pressure
- **DIABP** - Diastolic Blood Pressure
- **RESP** - Respiratory Rate
- **TEMP** - Temperature
- **WEIGHT** - Weight
- **HEIGHT** - Height
- **PULSE** - Pulse Rate (if available)

### Standard Units
- Blood Pressure: **mmHg**
- Pulse/Heart Rate: **beats/min**
- Respiratory Rate: **breaths/min**
- Temperature: **C** (Celsius)
- Weight: **kg** (kilograms)
- Height: **cm** (centimeters)

---

## Example Transformation

### Input (1 source record)
```
STUDY      = 'MAXIS-08'
PT         = '001'
INVSITE    = 'MAXIS_08_408'
VISIT      = 1
VTDT       = '2008-08-26'
VTBPS2     = 120.0
VTBPD2     = 96.0
VTRRT2     = 16.0
VTTP2      = 36.8
GNNUM1     = 68.9
GNNUM2     = 185.0
```

### Output (6 VS records)
```
Record 1: VSSEQ=1, VSTESTCD='SYSBP',   VSORRES='120.0', VSORRESU='mmHg',        VSSTRESN=120.0
Record 2: VSSEQ=2, VSTESTCD='DIABP',   VSORRES='96.0',  VSORRESU='mmHg',        VSSTRESN=96.0
Record 3: VSSEQ=3, VSTESTCD='RESP',    VSORRES='16.0',  VSORRESU='breaths/min', VSSTRESN=16.0
Record 4: VSSEQ=4, VSTESTCD='TEMP',    VSORRES='36.8',  VSORRESU='C',           VSSTRESN=36.8
Record 5: VSSEQ=5, VSTESTCD='WEIGHT',  VSORRES='68.9',  VSORRESU='kg',          VSSTRESN=68.9
Record 6: VSSEQ=6, VSTESTCD='HEIGHT',  VSORRES='185.0', VSORRESU='cm',          VSSTRESN=185.0

All records share:
  STUDYID='MAXIS-08', DOMAIN='VS', USUBJID='MAXIS-08-408-001'
  VISITNUM=1, VISIT='1', VSDTC='2008-08-26'
```

---

## Implementation Notes

### Assumptions
1. **Position** - Blood pressure measurements assumed taken in SITTING position (not captured in source)
2. **Location** - Temperature assumed ORAL, blood pressure assumed ARM (not captured)
3. **Baseline** - Not currently derived; should be first measurement or protocol-defined visit
4. **Missing Values** - Source records with missing vital signs do not create VS records

### Special Handling
1. **Multiple Measurements** - REPEATSN indicates repeated measurements at same visit
2. **Height/Weight** - Only captured at select visits (~3% of records)
3. **Time Component** - Optional; included in VSDTC if VTTM populated

---

## SQL Query Examples

### Get all vitals for a subject
```sql
SELECT * FROM vs
WHERE USUBJID = 'MAXIS-08-408-001'
ORDER BY VSSEQ;
```

### Blood pressure summary by visit
```sql
SELECT USUBJID, VISITNUM,
       MAX(CASE WHEN VSTESTCD = 'SYSBP' THEN VSSTRESN END) as systolic,
       MAX(CASE WHEN VSTESTCD = 'DIABP' THEN VSSTRESN END) as diastolic
FROM vs
WHERE VSTESTCD IN ('SYSBP', 'DIABP')
GROUP BY USUBJID, VISITNUM;
```

### Find abnormal vital signs
```sql
SELECT USUBJID, VISITNUM, VSTESTCD, VSSTRESN
FROM vs
WHERE (VSTESTCD = 'SYSBP' AND (VSSTRESN < 90 OR VSSTRESN > 180))
   OR (VSTESTCD = 'DIABP' AND (VSSTRESN < 50 OR VSSTRESN > 120))
   OR (VSTESTCD = 'TEMP' AND (VSSTRESN < 36.0 OR VSSTRESN > 38.5));
```

---

## File Locations

| File | Location |
|------|----------|
| Source Data | EDC Data/VITALS.csv |
| Target Data | sdtm_data/vs.csv |
| Mapping Spec (Full) | VS_MAPPING_SPECIFICATION.md |
| R Program | r_programs/vs.R |
| SAS Program | sas_programs/vs.sas |
| Mapping JSON | mapping_specs/VS_mapping.json |

---

## Contact & Support

For questions about this mapping specification:
- Review full specification: VS_MAPPING_SPECIFICATION.md
- Check transformation code: domain_transformers.py (VSTransformer class)
- Validation reports: raw_validation/ and sdtm_validation/

---

**Generated:** 2026-01-22  
**Version:** 1.0  
**Status:** Production Ready  

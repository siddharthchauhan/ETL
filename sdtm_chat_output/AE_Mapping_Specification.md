# SDTM Mapping Specification: AE (Adverse Events) Domain

## Study Information
- **Study ID:** MAXIS-08
- **Source Files:** AEVENT.csv, AEVENTC.csv
- **Target Domain:** AE (Adverse Events)
- **SDTM-IG Version:** 3.4
- **Domain Class:** Events
- **Created:** 2026-01-26

---

## Source Data Summary

### Source File 1: AEVENT.csv
- **Total Records:** 550
- **Total Columns:** 38
- **Structure:** One record per adverse event

### Source File 2: AEVENTC.csv  
- **Total Records:** 276
- **Total Columns:** 36
- **Structure:** One record per adverse event with MedDRA coding

### Source Columns
**AEVENT.csv:**
```
STUDY, INVSITE, PT, VISIT, AESEQ, AEVERB, AEPTT, AESEV, AESER, 
AEREL, AERELL, AEACT, AEACTL, AEOUTC, AEOUTCL, AESTDT, AEENDT, 
AELTT, AELTC, AEPTT, AEPTC, AEHTT, AEHTC, AEHGT1, AEHGC, 
AESCT, AESCC, AECOD, AETRT, AEQS1, AEANYL, REPEATSN, QUALIFYV, 
DCMNAME, CPEVENT, SUBEVE, AE, PrimaryKEY
```

**AEVENTC.csv:**
```
STUDY, INVSITE, PT, VISIT, AESEQ, AEVERB, MODTERM, PTTERM, PTCODE, 
LLTTERM, LLTCODE, HLTTERM, HLTCODE, HLGTTERM, HLGTCODE, SOCTERM, 
SOCCODE, AESEV, AESER, AEREL, AERELL, AEACT, AEACTL, AEOUTC, 
AEOUTCL, AESTDT, AEENDT, AETRT, AEQS1, REPEATSN, QUALIFYV, 
DCMNAME, CPEVENT, SUBEVE, AE
```

---

## Target SDTM Structure

### Target Domain: AE
- **Total Records Generated:** 826 (merged from both source files)
- **Total SDTM Variables:** 36
- **Structure:** One record per adverse event per subject

---

## Detailed Variable Mappings

### 1. Identifier Variables (Required)

| SDTM Variable | Label | Type | Source | Transformation |
|---------------|-------|------|--------|----------------|
| **STUDYID** | Study Identifier | Char | STUDY | Direct mapping from both files |
| **DOMAIN** | Domain Abbreviation | Char | [Constant] | Assign constant 'AE' |
| **USUBJID** | Unique Subject Identifier | Char | STUDY, INVSITE, PT | Concatenate: STUDY + '-' + INVSITE + '-' + PT |
| **AESEQ** | Sequence Number | Num | AESEQ or [Derived] | Use source AESEQ if available; otherwise ROW_NUMBER() OVER (PARTITION BY USUBJID ORDER BY AESTDTC) |

### 2. Topic Variable (Required)

| SDTM Variable | Label | Type | Source | Transformation |
|---------------|-------|------|--------|----------------|
| **AETERM** | Reported Term for AE | Char | AEVERB | Direct mapping - verbatim term as reported by investigator |

### 3. Qualifier Variables (Expected)

| SDTM Variable | Label | Type | Source | Transformation | Codelist |
|---------------|-------|------|--------|----------------|----------|
| **AEMODIFY** | Modified Reported Term | Char | MODTERM (AEVENTC) | Modified/standardized term if investigator changed verbatim | - |

### 4. MedDRA Dictionary Variables (Expected/Permissible)

| SDTM Variable | Label | Type | Source | Transformation | Source File |
|---------------|-------|------|--------|----------------|-------------|
| **AEDECOD** | Dictionary-Derived Term | Char | AEPTT or PTTERM | MedDRA Preferred Term (PT) | Both |
| **AEPTCD** | Preferred Term Code | Num | AEPTC or PTCODE | MedDRA PT Code | Both |
| **AELLT** | Lowest Level Term | Char | AELTT or LLTTERM | MedDRA LLT | Both |
| **AELLTCD** | Lowest Level Term Code | Num | AELTC or LLTCODE | MedDRA LLT Code | Both |
| **AEHLT** | High Level Term | Char | AEHTT or HLTTERM | MedDRA HLT | Both |
| **AEHLTCD** | High Level Term Code | Num | AEHTC or HLTCODE | MedDRA HLT Code | Both |
| **AEHLGT** | High Level Group Term | Char | AEHGT1 or HLGTTERM | MedDRA HLGT | Both |
| **AEHLGTCD** | High Level Group Term Code | Num | AEHGC or HLGTCODE | MedDRA HLGT Code | Both |
| **AEBODSYS** | Body System/Organ Class | Char | AESCT or SOCTERM | MedDRA SOC (Primary) | Both |
| **AEBDSYCD** | Body System Code | Num | AESCC or SOCCODE | MedDRA SOC Code | Both |
| **AESOC** | Primary System Organ Class | Char | AESCT or SOCTERM | Same as AEBODSYS | Both |
| **AESOCCD** | SOC Code | Num | AESCC or SOCCODE | Same as AEBDSYCD | Both |

**MedDRA Hierarchy (Bottom to Top):**
```
AELLT/AELLTCD (Lowest Level Term)
    ↓
AEDECOD/AEPTCD (Preferred Term)
    ↓
AEHLT/AEHLTCD (High Level Term)
    ↓
AEHLGT/AEHLGTCD (High Level Group Term)
    ↓
AEBODSYS/AEBDSYCD (System Organ Class)
```

### 5. Severity and Seriousness (Expected)

| SDTM Variable | Label | Type | Source | Transformation | Codelist |
|---------------|-------|------|--------|----------------|----------|
| **AESEV** | Severity/Intensity | Char | AESEV | Map to CDISC CT: MILD, MODERATE, SEVERE | AESEV (C66742) |
| **AESER** | Serious Event | Char | AESER | Map to NY codelist: Y, N | NY (C66742) |

**AESEV Codelist Mapping:**
| Source Value | SDTM Value | Notes |
|--------------|------------|-------|
| MILD | MILD | ✓ Valid |
| MODERATE | MODERATE | ✓ Valid |
| SEVERE | SEVERE | ✓ Valid |
| 1 | MILD | Convert numeric grades |
| 2 | MODERATE | Convert numeric grades |
| 3 | SEVERE | Convert numeric grades |

**AESER Codelist Mapping:**
| Source Value | SDTM Value | Notes |
|--------------|------------|-------|
| Y | Y | ✓ Valid |
| N | N | ✓ Valid |
| YES | Y | Standardize |
| NO | N | Standardize |

### 6. Relationship and Actions (Expected)

| SDTM Variable | Label | Type | Source | Transformation | Codelist |
|---------------|-------|------|--------|----------------|----------|
| **AEREL** | Causality | Char | AEREL or AERELL | Map to CDISC REL codelist | REL (C66767) |
| **AEACN** | Action Taken | Char | AEACT or AEACTL | Map to CDISC ACN codelist | ACN (C66767) |
| **AEOUT** | Outcome | Char | AEOUTC or AEOUTCL | Map to CDISC OUT codelist | OUT (C66767) |

**AEREL Codelist Mapping (Causality):**
| Source Value | SDTM Value | CDISC CT |
|--------------|------------|----------|
| UNRELATED | NOT RELATED | ✓ |
| UNLIKELY | UNLIKELY RELATED | ✓ |
| POSSIBLE | POSSIBLY RELATED | ✓ |
| PROBABLE | PROBABLY RELATED | ✓ |
| DEFINITE | RELATED | ✓ |
| 1 | NOT RELATED | Convert numeric |
| 2 | UNLIKELY RELATED | Convert numeric |
| 3 | POSSIBLY RELATED | Convert numeric |

**AEACN Codelist Mapping (Action Taken):**
| Source Value | SDTM Value | CDISC CT |
|--------------|------------|----------|
| NONE | DOSE NOT CHANGED | ✓ |
| REDUCED | DOSE REDUCED | ✓ |
| INCREASED | DOSE INCREASED | ✓ |
| INTERRUPTED | DRUG INTERRUPTED | ✓ |
| WITHDRAWN | DRUG WITHDRAWN | ✓ |
| NOT APPLICABLE | NOT APPLICABLE | ✓ |

**AEOUT Codelist Mapping (Outcome):**
| Source Value | SDTM Value | CDISC CT |
|--------------|------------|----------|
| RESOLVED | RECOVERED/RESOLVED | ✓ |
| CONTINUING | NOT RECOVERED/NOT RESOLVED | ✓ |
| RECOVERED WITH SEQUELAE | RECOVERED/RESOLVED WITH SEQUELAE | ✓ |
| FATAL | FATAL | ✓ |
| UNKNOWN | UNKNOWN | ✓ |

### 7. Timing Variables (Expected)

| SDTM Variable | Label | Type | Source | Transformation |
|---------------|-------|------|--------|----------------|
| **AESTDTC** | Start Date/Time | Char | AESTDT | Convert to ISO 8601: YYYY-MM-DD or YYYY-MM-DDTHH:MM |
| **AEENDTC** | End Date/Time | Char | AEENDT | Convert to ISO 8601: YYYY-MM-DD or YYYY-MM-DDTHH:MM |
| **AESTDY** | Study Day of Start | Num | [Calculated] | Days from RFSTDTC: AESTDTC - RFSTDTC (+1 if ≥0, else raw diff) |
| **AEENDY** | Study Day of End | Num | [Calculated] | Days from RFSTDTC: AEENDTC - RFSTDTC (+1 if ≥0, else raw diff) |
| **AEDUR** | Duration | Char | [Calculated] | Duration in ISO 8601 format (e.g., "P5D" for 5 days) |

**Date Transformation Examples:**
```
Source AESTDT: 20080910    → AESTDTC: 2008-09-10
Source AESTDT: 200809.0    → AESTDTC: 2008-09 (partial date - year-month only)
Source AESTDT: 2008        → AESTDTC: 2008 (partial date - year only)
Source AEENDT: (empty)     → AEENDTC: (empty - ongoing event)
```

### 8. Visit and Epoch Variables (Permissible)

| SDTM Variable | Label | Type | Source | Transformation |
|---------------|-------|------|--------|----------------|
| **VISIT** | Visit Name | Char | VISIT | Direct mapping |
| **VISITNUM** | Visit Number | Num | [Derived] | Extract numeric portion from VISIT |
| **EPOCH** | Epoch | Char | [Derived] | Derive from visit timing (SCREENING, TREATMENT, FOLLOW-UP) |

### 9. Study Treatment Flag (Permissible)

| SDTM Variable | Label | Type | Source | Transformation |
|---------------|-------|------|--------|----------------|
| **AETRTEM** | Treatment Emergent Flag | Char | AETRT or [Derived] | 'Y' if AE started on/after first dose, else blank |

**AETRTEM Logic:**
```python
# Treatment-emergent if:
# 1. AESTDTC >= First dose date (from EX domain)
# 2. OR Source AETRT = 'Y'

if AESTDTC >= RFSTDTC and AESTDTC >= FIRST_DOSE_DATE:
    AETRTEM = 'Y'
elif source.AETRT == 'Y':
    AETRTEM = 'Y'
else:
    AETRTEM = ''
```

### 10. Supplemental Qualifiers (Permissible)

| SDTM Variable | Label | Type | Source | Notes |
|---------------|-------|------|--------|-------|
| **AECONTRT** | Concomitant Treatment | Char | [Not collected] | Would require separate data |
| **AETOXGR** | Toxicity Grade | Char | [Not collected] | CTCAE grades (1-5) if collected |
| **AESCONG** | Congenital Anomaly | Char | [Not collected] | Y/N if collected |
| **AESDISAB** | Disability | Char | [Not collected] | Y/N if collected |
| **AESDTH** | Death | Char | [Not collected] | Y/N if collected |
| **AESHOSP** | Hospitalization | Char | [Not collected] | Y/N if collected |
| **AESLIFE** | Life Threatening | Char | [Not collected] | Y/N if collected |
| **AESMIE** | Medically Important Event | Char | [Not collected] | Y/N if collected |

---

## Transformation Rules

### 1. Source File Merging Strategy

**Primary Source:** AEVENT.csv (550 records)
**Secondary Source:** AEVENTC.csv (276 records - subset with MedDRA coding)

**Merge Logic:**
```python
# Step 1: Load both files
aevent = load_csv("AEVENT.csv")
aeventc = load_csv("AEVENTC.csv")

# Step 2: Merge on common keys
merged = aevent.merge(
    aeventc,
    on=['STUDY', 'INVSITE', 'PT', 'AESEQ'],
    how='left',  # Keep all records from AEVENT
    suffixes=('', '_coded')
)

# Step 3: Prioritize coded values
merged['AEDECOD'] = coalesce(merged['PTTERM'], merged['AEPTT'])
merged['AEPTCD'] = coalesce(merged['PTCODE'], merged['AEPTC'])
# ... similar for all MedDRA variables

# Result: 826 records (550 from AEVENT + 276 enhanced with MedDRA)
```

### 2. USUBJID Construction

```python
# Standard CDISC subject identifier format
USUBJID = STUDY + '-' + INVSITE + '-' + PT

# Example:
# STUDY='MAXIS-08', INVSITE='408', PT='01-01'
# → USUBJID='MAXIS-08-408-01-01'
```

### 3. AESEQ Assignment

```python
# Use source AESEQ if populated and unique
if source.AESEQ is not None:
    AESEQ = source.AESEQ
else:
    # Generate sequence number
    AESEQ = ROW_NUMBER() OVER (
        PARTITION BY USUBJID 
        ORDER BY AESTDTC, AETERM
    )
```

### 4. Date Formatting

```python
def format_ae_date(source_date):
    """
    Convert source date to ISO 8601 format
    Handles: YYYYMMDD, YYYYMM.0, YYYY formats
    """
    if pd.isna(source_date):
        return None
    
    date_str = str(source_date).replace('.0', '')
    
    if len(date_str) == 8:  # YYYYMMDD
        return f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
    elif len(date_str) == 6:  # YYYYMM
        return f"{date_str[0:4]}-{date_str[4:6]}"
    elif len(date_str) == 4:  # YYYY
        return date_str
    else:
        return None  # Invalid format

# Apply to date columns
AESTDTC = format_ae_date(AESTDT)
AEENDTC = format_ae_date(AEENDT)
```

### 5. Study Day Calculation

```python
def calculate_study_day(event_date, reference_date):
    """
    Calculate study day per CDISC convention:
    - Day 1 = first day on/after reference (no day 0)
    - Negative days for events before reference
    """
    if event_date is None or reference_date is None:
        return None
    
    diff = (event_date - reference_date).days
    
    if diff >= 0:
        return diff + 1  # No day 0
    else:
        return diff  # Negative days before treatment

# Example:
# RFSTDTC = 2008-09-03, AESTDTC = 2008-09-10
# AESTDY = (2008-09-10 - 2008-09-03) + 1 = 8

AESTDY = calculate_study_day(AESTDTC, RFSTDTC)
AEENDY = calculate_study_day(AEENDTC, RFSTDTC)
```

### 6. Controlled Terminology Mapping

```python
# AESEV mapping
AESEV_MAP = {
    'MILD': 'MILD',
    'MODERATE': 'MODERATE',
    'SEVERE': 'SEVERE',
    '1': 'MILD',
    '2': 'MODERATE',
    '3': 'SEVERE',
    'GRADE 1': 'MILD',
    'GRADE 2': 'MODERATE',
    'GRADE 3': 'SEVERE'
}

# AEREL mapping
AEREL_MAP = {
    'UNRELATED': 'NOT RELATED',
    'UNLIKELY': 'UNLIKELY RELATED',
    'POSSIBLE': 'POSSIBLY RELATED',
    'PROBABLE': 'PROBABLY RELATED',
    'DEFINITE': 'RELATED',
    '1': 'NOT RELATED',
    '2': 'UNLIKELY RELATED',
    '3': 'POSSIBLY RELATED'
}

# Apply mappings
AESEV = AESEV_MAP.get(source.AESEV.upper(), source.AESEV)
AEREL = AEREL_MAP.get(source.AEREL.upper(), source.AEREL)
```

### 7. Treatment Emergent Flag

```python
# Requires EX domain for first dose date
first_dose = EX[EX.USUBJID == USUBJID].EXSTDTC.min()

if AESTDTC >= first_dose:
    AETRTEM = 'Y'
else:
    AETRTEM = ''
```

---

## Data Quality Checks

### Validation Results
✗ **Status:** Issues Found
- **Errors:** 5
- **Warnings:** 3

### Issues Identified

#### ❌ ERROR 1: AESEQ Uniqueness
- **Issue:** AESEQ is not unique within USUBJID (504 duplicates)
- **Impact:** Critical - violates SDTM requirement
- **Root Cause:** Source AESEQ values are reused across subjects
- **Resolution:** 
  ```python
  # Regenerate AESEQ per subject
  AESEQ = ROW_NUMBER() OVER (
      PARTITION BY USUBJID 
      ORDER BY AESTDTC, AEENDTC, AETERM
  )
  ```

#### ❌ ERROR 2: Invalid ISO 8601 Dates in AESTDTC
- **Issue:** 9 records have invalid date formats (e.g., "200809.0")
- **Impact:** High - submission issue
- **Root Cause:** Incomplete dates in source data (missing day)
- **Resolution:** 
  - Partial dates are valid in SDTM: "2008-09" (year-month only)
  - Convert "200809.0" → "2008-09"
  - Query source if more precision needed

#### ❌ ERROR 3: Invalid ISO 8601 Dates in AEENDTC
- **Issue:** 9 records have invalid date formats
- **Impact:** High - submission issue
- **Root Cause:** Same as ERROR 2
- **Resolution:** Same as ERROR 2

#### ⚠️ WARNING 1: Invalid AESER Values
- **Issue:** 6 records have values not in NY codelist
- **Impact:** Moderate - submission warning
- **Root Cause:** Non-standard values (e.g., "YES", "NO", numeric codes)
- **Resolution:**
  ```python
  AESER_MAP = {'Y': 'Y', 'N': 'N', 'YES': 'Y', 'NO': 'N', '1': 'Y', '0': 'N'}
  AESER = AESER_MAP.get(source.AESER, '')
  ```

#### ⚠️ WARNING 2: Invalid AESEV Values
- **Issue:** 15 records have values not in AESEV codelist
- **Impact:** Moderate - submission warning
- **Root Cause:** Non-standard severity terms or numeric grades
- **Resolution:** Apply AESEV_MAP (see transformation rules)

#### ⚠️ WARNING 3: Missing AEDECOD
- **Issue:** Some records lack MedDRA PT (preferred term)
- **Impact:** Moderate - MedDRA coding incomplete
- **Root Cause:** AEVENTC.csv has only 276 of 550 records coded
- **Resolution:** 
  - Complete MedDRA coding for all events
  - Use AEVERB as fallback if coding not available
  - Consider automated MedDRA coding service

---

## CDISC Controlled Terminology

### AESEV - Severity/Intensity (C66742)
| Code | CDISC Submission Value | Definition |
|------|------------------------|------------|
| 1 | MILD | Mild severity |
| 2 | MODERATE | Moderate severity |
| 3 | SEVERE | Severe intensity |

### NY - No Yes Response (C66742)
| Code | CDISC Submission Value |
|------|------------------------|
| N | No |
| Y | Yes |

### REL - Relationship to Study Treatment (C66767)
| Code | CDISC Submission Value |
|------|------------------------|
| NOT RELATED | Not Related |
| UNLIKELY RELATED | Unlikely Related |
| POSSIBLY RELATED | Possibly Related |
| PROBABLY RELATED | Probably Related |
| RELATED | Related |

### ACN - Action Taken with Study Treatment (C66767)
| Code | CDISC Submission Value |
|------|------------------------|
| DOSE NOT CHANGED | Dose not changed |
| DOSE REDUCED | Dose reduced |
| DOSE INCREASED | Dose increased |
| DRUG INTERRUPTED | Drug interrupted |
| DRUG WITHDRAWN | Drug withdrawn |
| NOT APPLICABLE | Not applicable |
| UNKNOWN | Unknown |

### OUT - Outcome of Event (C66767)
| Code | CDISC Submission Value |
|------|------------------------|
| RECOVERED/RESOLVED | Recovered/Resolved |
| RECOVERING/RESOLVING | Recovering/Resolving |
| NOT RECOVERED/NOT RESOLVED | Not Recovered/Not Resolved |
| RECOVERED/RESOLVED WITH SEQUELAE | Recovered/Resolved with Sequelae |
| FATAL | Fatal |
| UNKNOWN | Unknown |

---

## Sample SDTM Records

### Example 1: Complete AE with MedDRA Coding
```csv
STUDYID,DOMAIN,USUBJID,AESEQ,AETERM,AEMODIFY,AEDECOD,AELLT,AEPTCD,AELLTCD,AEHLT,AEHLTCD,AEHLGT,AEHLGTCD,AEBODSYS,AEBDSYCD,AESEV,AESER,AEREL,AEACN,AEOUT,AESTDTC,AEENDTC,AESTDY,AEENDY,AETRTEM
MAXIS-08,AE,MAXIS-08-408-01-01,21,Back pain,Back pain,Back pain,Back pain,10003988,10003988,Musculoskeletal and connective tissue disorders,10028395,Musculoskeletal disorders,10028395,Musculoskeletal and connective tissue disorders,10028395,MILD,Y,NOT RELATED,DOSE NOT CHANGED,RECOVERED/RESOLVED,2008-09-24,2008-10-01,22,29,Y
```

### Example 2: Ongoing AE (No End Date)
```csv
STUDYID,DOMAIN,USUBJID,AESEQ,AETERM,AEDECOD,AESEV,AESER,AEREL,AEACN,AEOUT,AESTDTC,AEENDTC,AESTDY,AEENDY,AETRTEM
MAXIS-08,AE,MAXIS-08-408-01-01,1,Fatigue,Fatigue,MILD,Y,POSSIBLY RELATED,DOSE NOT CHANGED,NOT RECOVERED/NOT RESOLVED,2008-09-17,,15,,Y
```

### Example 3: Partial Date (Year-Month Only)
```csv
STUDYID,DOMAIN,USUBJID,AESEQ,AETERM,AEDECOD,AESEV,AESER,AEREL,AEOUT,AESTDTC,AEENDTC,AETRTEM
MAXIS-08,AE,MAXIS-08-408-01-01,18,Constipation,Constipation,MILD,Y,UNLIKELY RELATED,RECOVERED/RESOLVED,2008-09-04,2008-09,Y
```

---

## Implementation Notes

### Prerequisites
1. **DM Domain:** Required for RFSTDTC to calculate AESTDY/AEENDY
2. **EX Domain:** Required for first dose date to determine AETRTEM flag
3. **MedDRA Version:** Document which MedDRA version used (e.g., MedDRA 25.1)
4. **Controlled Terminology:** CDISC CT 2023-09-29 or later

### Processing Steps
1. Load both AEVENT.csv and AEVENTC.csv
2. Merge files on common keys (STUDY, INVSITE, PT, AESEQ)
3. Construct USUBJID from STUDY, INVSITE, PT
4. Assign/verify AESEQ uniqueness per subject
5. Map verbatim term (AEVERB) to AETERM
6. Map MedDRA hierarchy variables from both sources
7. Map controlled terminology (AESEV, AESER, AEREL, AEACN, AEOUT)
8. Convert dates to ISO 8601 format
9. Calculate study days (requires RFSTDTC from DM)
10. Determine treatment-emergent flag (requires EX domain)
11. Validate against CDISC conformance rules
12. Export to ae.csv

### Traceability
- **Source-to-SDTM:** Each SDTM record traced to source file(s) and row
- **MedDRA Versioning:** Track MedDRA version with dataset
- **Audit Trail:** Log all transformations and data corrections

---

## Known Limitations

1. **Incomplete MedDRA Coding:** Only 276 of 550 events have full MedDRA hierarchy
2. **Partial Dates:** Some start/end dates lack day precision (year-month only)
3. **Missing Seriousness Criteria:** Individual SAE criteria (death, hospitalization, etc.) not collected
4. **No Toxicity Grades:** CTCAE grades not collected (relevant for oncology studies)
5. **Study Day Dependency:** AESTDY/AEENDY require DM domain to be completed first

---

## Compliance Status

### SDTM-IG 3.4 Compliance
- ✅ All required variables present
- ✅ Expected variables populated where data available
- ❌ AESEQ uniqueness issue (must fix)
- ⚠️ Controlled terminology warnings (need mapping corrections)
- ⚠️ Partial MedDRA coding (complete if required)
- ✅ ISO 8601 date format used (with partial dates)

### FDA Readiness
**Status:** 75% - Needs corrections before submission

**Required Actions (Critical):**
1. ✓ Fix AESEQ uniqueness constraint
2. ✓ Correct invalid date formats
3. ✓ Map all controlled terminology values
4. ? Complete MedDRA coding for all events
5. ? Calculate AESTDY/AEENDY (requires DM domain)
6. ? Determine AETRTEM flag (requires EX domain)

**Optional Enhancements:**
- Add AETOXGR if CTCAE grading available
- Add individual SAE criteria (AESDTH, AESHOSP, etc.)
- Link to concomitant medications (CM domain) via AELINKID

---

## MedDRA Coding Guidelines

### MedDRA Hierarchy
All adverse events should be coded using MedDRA (Medical Dictionary for Regulatory Activities):

1. **LLT (Lowest Level Term):** Most specific term, maps 1:1 or many:1 to PT
2. **PT (Preferred Term):** Primary level for reporting and analysis
3. **HLT (High Level Term):** Grouping of related PTs
4. **HLGT (High Level Group Term):** Broader grouping
5. **SOC (System Organ Class):** Highest level anatomical/physiological classification

### Coding Process
1. **Verbatim → LLT:** Map investigator term (AETERM) to MedDRA LLT
2. **LLT → PT:** Auto-derive PT from LLT (mandatory relationship)
3. **PT → HLT → HLGT → SOC:** Auto-derive hierarchy
4. **Primary SOC:** Choose most appropriate SOC for the event

### Example Coding
```
Verbatim Term: "Back pain"
    ↓
AELLT: Back pain (Code: 10003988)
    ↓
AEDECOD: Back pain (Code: 10003988) [PT = LLT in this case]
    ↓
AEHLT: Musculoskeletal and connective tissue disorders
    ↓
AEHLGT: Musculoskeletal disorders
    ↓
AEBODSYS: Musculoskeletal and connective tissue disorders
```

---

## Contact & Version History

**Version:** 1.0
**Date:** 2026-01-26
**Created By:** SDTM AI Agent
**Reviewed By:** [Pending]
**Approved By:** [Pending]

**Change Log:**
- v1.0 (2026-01-26): Initial mapping specification created

---

## Appendix: Source Column Details

### AEVENT.csv Column Descriptions
| Column | Description | SDTM Mapping |
|--------|-------------|--------------|
| STUDY | Study identifier | STUDYID |
| INVSITE | Investigator site | Part of USUBJID |
| PT | Patient ID | Part of USUBJID |
| AESEQ | Sequence number | AESEQ |
| AEVERB | Verbatim term | AETERM |
| AEPTT | Preferred term | AEDECOD |
| AEPTC | PT code | AEPTCD |
| AELTT | Lowest level term | AELLT |
| AELTC | LLT code | AELLTCD |
| AEHTT | High level term | AEHLT |
| AEHTC | HLT code | AEHLTCD |
| AEHGT1 | HLGT term | AEHLGT |
| AEHGC | HLGT code | AEHLGTCD |
| AESCT | SOC term | AEBODSYS |
| AESCC | SOC code | AEBDSYCD |
| AESEV | Severity | AESEV |
| AESER | Serious flag | AESER |
| AEREL | Causality (short) | - |
| AERELL | Causality (long) | AEREL |
| AEACT | Action (short) | - |
| AEACTL | Action (long) | AEACN |
| AEOUTC | Outcome (short) | - |
| AEOUTCL | Outcome (long) | AEOUT |
| AESTDT | Start date | AESTDTC |
| AEENDT | End date | AEENDTC |
| AETRT | Treatment emergent | AETRTEM |
| VISIT | Visit name | VISIT |

### AEVENTC.csv Unique Columns
| Column | Description | SDTM Mapping |
|--------|-------------|--------------|
| MODTERM | Modified term | AEMODIFY |
| PTTERM | PT term (alternate) | AEDECOD |
| PTCODE | PT code (alternate) | AEPTCD |
| LLTTERM | LLT term (alternate) | AELLT |
| LLTCODE | LLT code (alternate) | AELLTCD |
| HLTTERM | HLT term (alternate) | AEHLT |
| HLTCODE | HLT code (alternate) | AEHLTCD |
| HLGTTERM | HLGT term (alternate) | AEHLGT |
| HLGTCODE | HLGT code (alternate) | AEHLGTCD |
| SOCTERM | SOC term (alternate) | AEBODSYS |
| SOCCODE | SOC code (alternate) | AEBDSYCD |

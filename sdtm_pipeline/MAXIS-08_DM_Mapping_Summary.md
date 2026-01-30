# SDTM DM Mapping Specification Summary
## MAXIS-08 Study

---

## Executive Summary

This document provides a comprehensive mapping specification for transforming the MAXIS-08 study demographics source data (DEMO.csv) to CDISC SDTM DM (Demographics) domain format compliant with SDTM-IG v3.4.

**Status**: Ready for implementation with dependencies noted  
**Completion**: ~40% mappable from DEMO.csv alone, 60% requires integration with other domains  
**Critical Issues**: 2 (HISPANIC race mapping, ARM/ARMCD missing)  
**Warnings**: 15 variables require external data sources

---

## Source Data Profile

| Attribute | Details |
|-----------|---------|
| **Source File** | DEMO.csv |
| **Source System** | EDC (Electronic Data Capture) |
| **Record Structure** | One record per subject |
| **Data Quality** | ✅ 100% completeness |
| **Subjects** | Multiple subjects from site 408 |

### Source Columns (12 total)
- `STUDY` - Study identifier (MAXIS-08)
- `PT` - Patient/Subject ID (format: XX-YY)
- `INVSITE` - Investigator site (format: C008_XXX)
- `DOB` - Date of birth (YYYYMMDD format)
- `GENDER` - Gender (M/F)
- `RCE` - Race (BLACK/ASIAN/HISPANIC/WHITE)
- `DCMNAME`, `CPEVENT`, `VISIT`, `GENDRL`, `SUBEVE`, `REPEATSN` - Other fields

---

## Target Domain: DM (Demographics)

**Domain Class**: Special Purpose  
**Purpose**: One record per subject containing demographic characteristics and study participation summary  
**SDTM Version**: 3.4  
**Total Variables**: 29 mapped

### Variable Breakdown by Core Status
- **Required (Req)**: 8 variables - MUST be populated
- **Expected (Exp)**: 13 variables - SHOULD be populated when data available
- **Permissible (Perm)**: 8 variables - CAN be included when applicable

---

## Mapping Overview

### ✅ PHASE 1: Immediate Mappings (Available from DEMO.csv)

These variables can be populated directly from DEMO.csv:

| Variable | Source | Transformation | Status |
|----------|--------|----------------|--------|
| **STUDYID** | STUDY | `ASSIGN("MAXIS-08")` | ✅ Ready |
| **DOMAIN** | - | `ASSIGN("DM")` | ✅ Ready |
| **SUBJID** | PT | Direct mapping | ✅ Ready |
| **SITEID** | INVSITE | `SUBSTR(INVSITE, 6, 3)` → Extract '408' | ✅ Ready |
| **USUBJID** | Derived | `CONCAT(STUDY, "-", SITEID, "-", PT)` | ✅ Ready |
| **BRTHDTC** | DOB | `ISO8601DATEFORMAT(DOB, "YYYYMMDD")` | ✅ Ready |
| **SEX** | GENDER | Map M→M, F→F | ✅ Ready |
| **AGEU** | - | `ASSIGN("YEARS")` | ✅ Ready |

#### Example Transformations

```
Source PT: "01-01"
Source DOB: 19740918
Source GENDER: "M"
Source INVSITE: "C008_408"

→ SUBJID: "01-01"
→ BRTHDTC: "1974-09-18"
→ SEX: "M"
→ SITEID: "408"
→ USUBJID: "MAXIS-08-408-01-01"
```

---

### ⚠️ PHASE 2: Variables Requiring Other Domains

These variables require integration with visit, exposure, or disposition data:

#### Reference Dates (from SV or EX domains)
| Variable | Description | Source Domain | Derivation |
|----------|-------------|---------------|------------|
| **RFSTDTC** | Subject Reference Start Date | SV/EX | First visit or exposure date |
| **RFENDTC** | Subject Reference End Date | SV/EX | Last visit or exposure date |
| **RFXSTDTC** | First Study Treatment Date | EX | MIN(EXSTDTC) by subject |
| **RFXENDTC** | Last Study Treatment Date | EX | MAX(EXENDTC or EXSTDTC) by subject |
| **DMDTC** | Date Demographics Collected | SV | Screening/baseline visit date |

#### Treatment Arms (from Randomization or TA domain)
| Variable | Description | Source | Status |
|----------|-------------|--------|--------|
| **ARMCD** | Planned Arm Code | Randomization | 🔴 REQUIRED - Missing |
| **ARM** | Planned Arm Description | Randomization | 🔴 REQUIRED - Missing |
| **ACTARMCD** | Actual Arm Code | EX | Permissible |
| **ACTARM** | Actual Arm Description | EX | Permissible |

**CRITICAL**: ARMCD and ARM are REQUIRED variables. Must be populated from randomization data or use interim values:
- Screen failures: `ARMCD="SCRNFAIL"`, `ARM="Screen Failure"`
- Not yet assigned: `ARMCD="NOTASSGN"`, `ARM="Not Assigned"`

#### Disposition Dates (from DS domain)
| Variable | Description | Derivation |
|----------|-------------|------------|
| **RFICDTC** | Informed Consent Date | DS where DSDECOD='INFORMED CONSENT OBTAINED' |
| **RFPENDTC** | End of Participation Date | DS final disposition date |
| **DTHDTC** | Date of Death | DS where DSDECOD='DEATH' or AE where AEOUT='FATAL' |
| **DTHFL** | Death Flag | 'Y' if DTHDTC populated, else null |

#### Site Metadata (from external reference file)
| Variable | Description | Source |
|----------|-------------|--------|
| **INVID** | Investigator ID | Site metadata/roster |
| **INVNAM** | Investigator Name | Site metadata/roster |
| **COUNTRY** | Country Code (ISO 3166-1 alpha-3) | Site metadata/roster |

---

### 🔴 CRITICAL ISSUE: Race/Ethnicity Mapping

**Problem**: Source field `RCE` contains "HISPANIC" which is an ETHNICITY in CDISC, not a RACE.

#### Source Values & Mapping

| Source RCE | SDTM RACE | SDTM ETHNIC | Status |
|------------|-----------|-------------|--------|
| BLACK | BLACK OR AFRICAN AMERICAN | NOT REPORTED | ✅ OK |
| WHITE | WHITE | NOT REPORTED | ✅ OK |
| ASIAN | ASIAN | NOT REPORTED | ✅ OK |
| HISPANIC | **MANUAL REVIEW REQUIRED** | HISPANIC OR LATINO | 🔴 ISSUE |

#### Recommended Resolution

**Option 1 (Recommended)**: Request clinical review
1. Generate data quality report flagging all HISPANIC records
2. Request site to provide actual RACE for these subjects
3. Set `RACE` based on clinical input
4. Set `ETHNIC="HISPANIC OR LATINO"`

**Option 2**: Use interim values
1. Set `RACE="NOT REPORTED"` for HISPANIC subjects
2. Set `ETHNIC="HISPANIC OR LATINO"`
3. Document in data quality report

**Option 3**: Request source data correction
- EDC system should collect race and ethnicity separately

#### CDISC Controlled Terminology

**RACE (Extensible)**:
- AMERICAN INDIAN OR ALASKA NATIVE
- ASIAN
- BLACK OR AFRICAN AMERICAN
- NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER
- WHITE
- MULTIPLE
- NOT REPORTED
- UNKNOWN

**ETHNIC**:
- HISPANIC OR LATINO
- NOT HISPANIC OR LATINO
- NOT REPORTED
- UNKNOWN

---

### 🧮 Calculated Variables

#### AGE Calculation

```
Formula: FLOOR((RFSTDTC - BRTHDTC) / 365.25)

Challenge: RFSTDTC not available in DEMO.csv

Interim Solution:
- Calculate age at proxy date (e.g., current date)
- Document that recalculation needed once RFSTDTC available

Final Solution:
- Recalculate AGE once RFSTDTC populated from visit data
```

**Example**:
```
BRTHDTC: 1974-09-18
RFSTDTC: 2024-01-15 (from first visit)
AGE: FLOOR((2024-01-15 - 1974-09-18) / 365.25) = 49
AGEU: YEARS
```

#### AGEGR1 (Age Group 1)

Protocol-defined age grouping for analysis:

```
Common FDA grouping:
- IF AGE < 65 THEN "<65"
- IF AGE >= 65 THEN ">=65"

Alternative detailed grouping:
- 18-44
- 45-64
- 65-74
- >=75
```

#### DMDY (Study Day)

```
Study day calculation (CDISC convention):

If DMDTC >= RFSTDTC:
  DMDY = (DMDTC - RFSTDTC) + 1

If DMDTC < RFSTDTC:
  DMDY = (DMDTC - RFSTDTC)

Note: No day 0 in SDTM. Day before reference is -1, day of reference is 1.
```

---

## Transformation Functions (DSL)

### Assignment Functions

| Function | Purpose | Example |
|----------|---------|---------|
| `ASSIGN(value)` | Constant assignment | `ASSIGN("DM")` → "DM" |
| Direct reference | Column mapping | `PT` → value from PT column |

### String Functions

| Function | Purpose | Example |
|----------|---------|---------|
| `CONCAT(a, b, c)` | Concatenate values | `CONCAT(STUDY, "-", PT)` → "MAXIS-08-01-01" |
| `SUBSTR(field, start, len)` | Extract substring | `SUBSTR(INVSITE, 6, 3)` → "408" from "C008_408" |
| `UPCASE(field)` | Uppercase conversion | `UPCASE(field)` → "VALUE" |
| `TRIM(field)` | Remove whitespace | `TRIM(field)` → "value" |

### Date Functions

| Function | Purpose | Example |
|----------|---------|---------|
| `ISO8601DATEFORMAT(field, fmt)` | Convert to ISO 8601 | `ISO8601DATEFORMAT(DOB, "YYYYMMDD")` <br> 19740918 → 1974-09-18 |
| `ISO8601DATETIMEFORMATS(...)` | Try multiple formats | Attempts formats in sequence |

### Conditional Functions

| Function | Purpose | Example |
|----------|---------|---------|
| `IF(condition, true, false)` | Conditional logic | `IF(GENDER=="M", "M", "F")` |
| `MAP(field, codelist)` | Codelist mapping | `MAP(RCE, RACE_CODELIST)` |

---

## Implementation Roadmap

### Step 1: Initial DM Generation (DEMO.csv only)
**Deliverable**: Partial DM dataset with 8 core variables populated

```
Variables populated:
✅ STUDYID, DOMAIN, USUBJID, SUBJID, SITEID
✅ BRTHDTC, SEX, AGEU

Variables requiring external data:
⚠️ RFSTDTC, RFENDTC (need SV/EX)
⚠️ ARMCD, ARM (need randomization)
⚠️ AGE (needs RFSTDTC for accurate calculation)
⚠️ RACE (needs resolution of HISPANIC issue)
⚠️ ETHNIC (needs proper mapping)
```

### Step 2: Race/Ethnicity Resolution
**Deliverable**: DQ report + corrected RACE/ETHNIC values

1. Generate data quality report listing all subjects with RCE='HISPANIC'
2. Send to clinical team for review
3. Receive actual RACE values from sites
4. Update mapping logic
5. Populate RACE and ETHNIC variables

### Step 3: Visit Integration (SV domain)
**Deliverable**: Reference dates populated

```
Once SV domain available:
✅ RFSTDTC = MIN(SVSTDTC) or first study visit
✅ RFENDTC = MAX(SVENDTC) or last study visit
✅ DMDTC = SVSTDTC where VISIT='SCREENING'
✅ AGE = Recalculated using RFSTDTC
✅ DMDY = Calculated using DMDTC and RFSTDTC
```

### Step 4: Exposure Integration (EX domain)
**Deliverable**: Treatment dates populated

```
Once EX domain available:
✅ RFXSTDTC = MIN(EXSTDTC) per subject
✅ RFXENDTC = MAX(EXENDTC or EXSTDTC) per subject
✅ ACTARMCD = Derived from actual treatment
✅ ACTARM = Description of actual treatment
```

### Step 5: Randomization Integration
**Deliverable**: REQUIRED ARM variables populated

```
Once randomization data available:
✅ ARMCD = Planned treatment arm code
✅ ARM = Planned treatment arm description

If randomization not available, use interim:
⚠️ ARMCD = "NOTASSGN", ARM = "Not Assigned"
```

### Step 6: Disposition Integration (DS domain)
**Deliverable**: Consent and completion dates

```
Once DS domain available:
✅ RFICDTC = Date informed consent obtained
✅ RFPENDTC = Date of final disposition
✅ DTHDTC = Date of death (if applicable)
✅ DTHFL = Death flag ('Y' if died)
```

### Step 7: Site Metadata Integration
**Deliverable**: Investigator and country information

```
Once site metadata available:
✅ INVID = Investigator identifier
✅ INVNAM = Investigator name
✅ COUNTRY = ISO 3166-1 alpha-3 code (e.g., USA)
```

### Step 8: Final Validation
**Deliverable**: FDA-ready DM dataset

```
Validation checks:
✅ All REQUIRED variables populated (STUDYID, DOMAIN, USUBJID, SUBJID, SITEID, SEX, ARMCD, ARM)
✅ All EXPECTED variables populated where applicable
✅ All dates in ISO 8601 format
✅ Controlled terminology compliance (SEX, RACE, ETHNIC, AGEU)
✅ USUBJID uniqueness
✅ One record per subject
✅ Date logic consistency (BRTHDTC < RFSTDTC < RFENDTC)
✅ No critical data quality issues
```

---

## Validation Rules

### Required Field Validation

| Variable | Rule | Error Level |
|----------|------|-------------|
| STUDYID | Must not be null | Critical |
| DOMAIN | Must equal "DM" | Critical |
| USUBJID | Must be unique, not null | Critical |
| SUBJID | Must not be null | Critical |
| SITEID | Must not be null | Critical |
| SEX | Must be M/F/U/UNDIFFERENTIATED | Critical |
| ARMCD | Must not be null | Critical |
| ARM | Must not be null | Critical |

### Controlled Terminology Validation

| Variable | Codelist | Validation |
|----------|----------|------------|
| SEX | SEX | Must be: M, F, U, UNDIFFERENTIATED |
| RACE | RACE | Must be valid CDISC CT RACE value |
| ETHNIC | ETHNIC | Must be: HISPANIC OR LATINO, NOT HISPANIC OR LATINO, NOT REPORTED, UNKNOWN |
| AGEU | AGEU | Must be: YEARS, MONTHS, WEEKS, DAYS, HOURS |
| COUNTRY | ISO 3166-1 | Must be 3-character alpha-3 code |

### Date Format Validation

All DTC variables must comply with ISO 8601:

```
Valid formats:
✅ YYYY (2024)
✅ YYYY-MM (2024-01)
✅ YYYY-MM-DD (2024-01-15)
✅ YYYY-MM-DDTHH:MM (2024-01-15T14:30)
✅ YYYY-MM-DDTHH:MM:SS (2024-01-15T14:30:45)

Invalid formats:
❌ MM/DD/YYYY (01/15/2024)
❌ DD-MON-YYYY (15-JAN-2024)
❌ YYYYMMDD (20240115)
```

### Date Logic Validation

```
Expected relationships:
BRTHDTC < RFICDTC <= RFSTDTC <= RFXSTDTC <= RFXENDTC <= RFENDTC <= RFPENDTC

If subject died:
DTHDTC <= RFPENDTC
DTHFL = 'Y'
```

### Consistency Validation

| Check | Rule | Level |
|-------|------|-------|
| Record count | Exactly 1 record per USUBJID | Critical |
| USUBJID format | Matches pattern: STUDYID-SITEID-SUBJID | Warning |
| AGE vs BRTHDTC | AGE calculated correctly from BRTHDTC | Warning |
| DTHFL vs DTHDTC | If DTHFL='Y' then DTHDTC not null | Critical |
| ARM vs TA | ARMCD/ARM match TA domain | Warning |

---

## Output Specifications

### File Details

| Attribute | Specification |
|-----------|---------------|
| **File Name** | dm.xpt (primary) |
| **Format** | SAS V5 XPORT |
| **Alternative Formats** | dm.csv, dm.sas7bdat |
| **Character Encoding** | UTF-8 |
| **Sort Order** | STUDYID, USUBJID |
| **Variable Order** | As specified in mapping spec (1-29) |

### Missing Value Representation

| Data Type | Missing Representation |
|-----------|----------------------|
| Character | Empty string or null |
| Numeric | . (SAS missing) or null |

**Note**: In SDTM, absence of a value is typically represented by leaving the field blank/null, not by using special codes like "NA" or "UNKNOWN" (except where "UNKNOWN" is a valid CT term).

---

## Data Quality Report Template

### Summary Statistics

```
Total subjects in DEMO.csv: {count}
Successfully mapped subjects: {count}
Records with warnings: {count}
Records with errors: {count}
```

### Critical Issues

```
1. RACE/ETHNICITY MAPPING
   - Subjects with HISPANIC race: {count}
   - Action required: Clinical review
   - Priority: HIGH

2. MISSING REQUIRED VARIABLES
   - ARMCD/ARM not available: {count} subjects
   - Action required: Obtain randomization data
   - Priority: CRITICAL
```

### Warnings

```
1. REFERENCE DATES
   - RFSTDTC missing: {count} subjects
   - Source: Need SV or EX domain
   - Impact: AGE calculation delayed

2. SITE METADATA
   - COUNTRY missing: {count} subjects
   - Source: Need site metadata file
   - Impact: Required for multi-national trials
```

### Data Completeness Matrix

| Variable | Core | Available (%) | Source | Status |
|----------|------|---------------|--------|--------|
| STUDYID | Req | 100% | DEMO.csv | ✅ |
| DOMAIN | Req | 100% | Derived | ✅ |
| USUBJID | Req | 100% | Derived | ✅ |
| SUBJID | Req | 100% | DEMO.csv | ✅ |
| SITEID | Req | 100% | DEMO.csv | ✅ |
| SEX | Req | 100% | DEMO.csv | ✅ |
| ARMCD | Req | 0% | Missing | 🔴 |
| ARM | Req | 0% | Missing | 🔴 |
| RFSTDTC | Exp | 0% | Need SV/EX | ⚠️ |
| BRTHDTC | Exp | 100% | DEMO.csv | ✅ |
| AGE | Exp | Pending | Calc | ⚠️ |
| RACE | Perm | 75%* | DEMO.csv | ⚠️ |

*25% require manual review (HISPANIC values)

---

## Regulatory Considerations

### FDA Requirements

1. **Domain Requirement**: DM is REQUIRED for all FDA submissions
2. **Critical Variables**: RFSTDTC and RFENDTC define subject participation window - must be accurate
3. **Treatment Assignment**: ARM/ARMCD must reflect PLANNED treatment (from protocol), not actual treatment
4. **Multi-national Trials**: COUNTRY is required with ISO 3166-1 alpha-3 codes
5. **Date Compliance**: All dates MUST be ISO 8601 - most common FDA rejection reason

### Common FDA Deficiencies (to avoid)

| Issue | Description | Prevention |
|-------|-------------|------------|
| Incomplete DM | Missing RFSTDTC/RFENDTC for subjects | Ensure all subjects have reference dates |
| Inconsistent USUBJID | Different formats across domains | Use standardized USUBJID construction |
| Race/Ethnicity Confusion | HISPANIC in RACE instead of ETHNIC | Separate collection and proper mapping |
| AGE Errors | Wrong calculation or missing AGEU | Validate formula and always populate AGEU |
| ARM Inconsistency | ARM doesn't match trial design | Cross-reference with TA domain |
| Date Format Issues | Non-ISO 8601 dates | Validate all DTC variables |

---

## Technical Implementation Guide

### Python Transformation Example

```python
import pandas as pd
from datetime import datetime

def transform_demo_to_dm(demo_df):
    """
    Transform DEMO.csv to SDTM DM domain
    
    Args:
        demo_df: DataFrame with source data
    
    Returns:
        dm_df: SDTM DM DataFrame
    """
    
    dm = pd.DataFrame()
    
    # PHASE 1: Direct mappings
    dm['STUDYID'] = 'MAXIS-08'
    dm['DOMAIN'] = 'DM'
    dm['SUBJID'] = demo_df['PT']
    
    # Extract SITEID from INVSITE (C008_408 -> 408)
    dm['SITEID'] = demo_df['INVSITE'].str[5:8]
    
    # Construct USUBJID
    dm['USUBJID'] = dm['STUDYID'] + '-' + dm['SITEID'] + '-' + dm['SUBJID']
    
    # Convert DOB to ISO 8601
    dm['BRTHDTC'] = pd.to_datetime(
        demo_df['DOB'], 
        format='%Y%m%d'
    ).dt.strftime('%Y-%m-%d')
    
    # Map SEX
    dm['SEX'] = demo_df['GENDER'].map({'M': 'M', 'F': 'F'})
    
    # Map RACE with warning for HISPANIC
    race_map = {
        'BLACK': 'BLACK OR AFRICAN AMERICAN',
        'WHITE': 'WHITE',
        'ASIAN': 'ASIAN',
        'HISPANIC': 'MANUAL_REVIEW_REQUIRED'
    }
    dm['RACE'] = demo_df['RCE'].map(race_map)
    
    # Map ETHNIC
    dm['ETHNIC'] = demo_df['RCE'].apply(
        lambda x: 'HISPANIC OR LATINO' if x == 'HISPANIC' else 'NOT REPORTED'
    )
    
    # Constant assignments
    dm['AGEU'] = 'YEARS'
    
    # PHASE 2: Placeholders for variables requiring external data
    dm['RFSTDTC'] = None  # Need SV/EX domain
    dm['RFENDTC'] = None  # Need SV/EX domain
    dm['ARMCD'] = 'NOTASSGN'  # Interim value
    dm['ARM'] = 'Not Assigned'  # Interim value
    dm['COUNTRY'] = None  # Need site metadata
    
    # Sort by USUBJID
    dm = dm.sort_values('USUBJID').reset_index(drop=True)
    
    return dm

# Usage
demo_df = pd.read_csv('DEMO.csv')
dm_df = transform_demo_to_dm(demo_df)
dm_df.to_csv('dm.csv', index=False)
```

### SAS Transformation Example

```sas
/* Transform DEMO to SDTM DM */

data dm;
    set demo;
    
    /* Required variables - direct assignment */
    length STUDYID $20 DOMAIN $2 USUBJID $40 SUBJID $20 SITEID $10;
    STUDYID = "MAXIS-08";
    DOMAIN = "DM";
    SUBJID = PT;
    
    /* Extract SITEID from INVSITE */
    SITEID = substr(INVSITE, 6, 3);
    
    /* Construct USUBJID */
    USUBJID = catx('-', STUDYID, SITEID, SUBJID);
    
    /* Convert DOB to ISO 8601 */
    length BRTHDTC $10;
    birthdate = input(put(DOB, 8.), yymmdd8.);
    BRTHDTC = put(birthdate, yymmdd10.);
    
    /* Map SEX */
    length SEX $1;
    if GENDER = 'M' then SEX = 'M';
    else if GENDER = 'F' then SEX = 'F';
    else SEX = 'U';
    
    /* Map RACE */
    length RACE $50;
    select (RCE);
        when ('BLACK') RACE = 'BLACK OR AFRICAN AMERICAN';
        when ('WHITE') RACE = 'WHITE';
        when ('ASIAN') RACE = 'ASIAN';
        when ('HISPANIC') do;
            RACE = '';  /* Flag for review */
            put "WARNING: HISPANIC found in RACE for subject " USUBJID;
        end;
        otherwise RACE = '';
    end;
    
    /* Map ETHNIC */
    length ETHNIC $30;
    if RCE = 'HISPANIC' then ETHNIC = 'HISPANIC OR LATINO';
    else ETHNIC = 'NOT REPORTED';
    
    /* Age units */
    length AGEU $10;
    AGEU = 'YEARS';
    
    /* Interim values for required fields */
    length ARMCD $20 ARM $200;
    ARMCD = 'NOTASSGN';
    ARM = 'Not Assigned';
    
    /* Keep only DM variables */
    keep STUDYID DOMAIN USUBJID SUBJID SITEID BRTHDTC SEX RACE ETHNIC AGEU ARMCD ARM;
run;

/* Sort by USUBJID */
proc sort data=dm;
    by STUDYID USUBJID;
run;
```

---

## Testing & Validation Checklist

### Unit Testing

- [ ] USUBJID construction logic verified
- [ ] SITEID extraction from INVSITE correct
- [ ] DOB to BRTHDTC conversion accurate
- [ ] SEX mapping M/F correct
- [ ] RACE mapping (except HISPANIC) correct
- [ ] ETHNIC mapping for HISPANIC subjects correct

### Integration Testing

- [ ] USUBJID matches across DM, AE, CM, VS, LB, EX domains
- [ ] RFSTDTC derived correctly from SV/EX
- [ ] ARMCD/ARM matches TA domain
- [ ] DTHDTC matches DS or AE fatal outcomes
- [ ] COUNTRY matches site metadata

### Compliance Testing

- [ ] All REQUIRED variables populated
- [ ] All EXPECTED variables populated where data exists
- [ ] All dates in ISO 8601 format
- [ ] All CT variables match controlled terminology
- [ ] Define-XML validates without errors
- [ ] Pinnacle 21 validation clean (0 critical errors)

### Data Quality Testing

- [ ] No duplicate USUBJID
- [ ] Exactly 1 record per subject
- [ ] No missing values in REQUIRED fields
- [ ] Date logic consistency verified
- [ ] AGE calculation spot-checked
- [ ] Race/ethnicity manual review complete

---

## Contact & Support

**Specification Version**: 1.0  
**Last Updated**: 2024-01-15  
**Author**: SDTM Mapping Specification Expert  
**SDTM Version**: 3.4  

For questions or clarifications:
- Clinical data management team
- SDTM programming team
- Regulatory submissions team

---

## Appendix A: Complete Variable Reference

| # | Variable | Label | Type | Len | Core | Available | Notes |
|---|----------|-------|------|-----|------|-----------|-------|
| 1 | STUDYID | Study Identifier | Char | 20 | Req | ✅ | From DEMO.STUDY |
| 2 | DOMAIN | Domain Abbreviation | Char | 2 | Req | ✅ | Constant "DM" |
| 3 | USUBJID | Unique Subject Identifier | Char | 40 | Req | ✅ | Constructed |
| 4 | SUBJID | Subject Identifier for Study | Char | 20 | Req | ✅ | From DEMO.PT |
| 5 | RFSTDTC | Subject Reference Start Date | Char | 20 | Exp | ⚠️ | Need SV/EX |
| 6 | RFENDTC | Subject Reference End Date | Char | 20 | Exp | ⚠️ | Need SV/EX |
| 7 | RFXSTDTC | First Study Treatment Date | Char | 20 | Exp | ⚠️ | Need EX |
| 8 | RFXENDTC | Last Study Treatment Date | Char | 20 | Exp | ⚠️ | Need EX |
| 9 | RFICDTC | Informed Consent Date | Char | 20 | Exp | ⚠️ | Need DS |
| 10 | RFPENDTC | End of Participation Date | Char | 20 | Exp | ⚠️ | Need DS |
| 11 | DTHDTC | Date of Death | Char | 20 | Perm | ⚠️ | Need DS/AE |
| 12 | DTHFL | Subject Death Flag | Char | 1 | Perm | ⚠️ | Derived |
| 13 | SITEID | Study Site Identifier | Char | 10 | Req | ✅ | From INVSITE |
| 14 | INVID | Investigator Identifier | Char | 20 | Perm | ⚠️ | Need metadata |
| 15 | INVNAM | Investigator Name | Char | 200 | Perm | ⚠️ | Need metadata |
| 16 | BRTHDTC | Date of Birth | Char | 20 | Exp | ✅ | From DEMO.DOB |
| 17 | AGE | Age | Num | 8 | Exp | ⚠️ | Calculated |
| 18 | AGEU | Age Units | Char | 10 | Exp | ✅ | Constant "YEARS" |
| 19 | AGEGR1 | Age Group 1 | Char | 20 | Perm | ⚠️ | Derived from AGE |
| 20 | SEX | Sex | Char | 1 | Req | ✅ | From DEMO.GENDER |
| 21 | RACE | Race | Char | 100 | Perm | ⚠️ | HISPANIC issue |
| 22 | ETHNIC | Ethnicity | Char | 100 | Exp | ⚠️ | HISPANIC mapping |
| 23 | ARMCD | Planned Arm Code | Char | 20 | Req | 🔴 | Need randomization |
| 24 | ARM | Planned Arm Description | Char | 200 | Req | 🔴 | Need randomization |
| 25 | ACTARMCD | Actual Arm Code | Char | 20 | Perm | ⚠️ | Need EX |
| 26 | ACTARM | Actual Arm Description | Char | 200 | Perm | ⚠️ | Need EX |
| 27 | COUNTRY | Country | Char | 3 | Exp | ⚠️ | Need metadata |
| 28 | DMDTC | Date of Collection | Char | 20 | Perm | ⚠️ | Need SV |
| 29 | DMDY | Study Day of Collection | Num | 8 | Perm | ⚠️ | Calculated |

**Legend**:
- ✅ Available from DEMO.csv
- ⚠️ Requires external data
- 🔴 Critical - REQUIRED field missing

---

## Appendix B: CDISC Controlled Terminology Quick Reference

### SEX
```
M - Male
F - Female  
U - Unknown
UNDIFFERENTIATED
```

### RACE (Extensible)
```
AMERICAN INDIAN OR ALASKA NATIVE
ASIAN
BLACK OR AFRICAN AMERICAN
NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER
WHITE
MULTIPLE
NOT REPORTED
UNKNOWN
```

### ETHNIC
```
HISPANIC OR LATINO
NOT HISPANIC OR LATINO
NOT REPORTED
UNKNOWN
```

### AGEU
```
YEARS
MONTHS
WEEKS
DAYS
HOURS
```

### ISO 3166-1 alpha-3 Country Codes (Examples)
```
USA - United States
CAN - Canada
GBR - United Kingdom
DEU - Germany
FRA - France
ITA - Italy
ESP - Spain
JPN - Japan
CHN - China
IND - India
AUS - Australia
BRA - Brazil
MEX - Mexico
```

---

**END OF DOCUMENT**

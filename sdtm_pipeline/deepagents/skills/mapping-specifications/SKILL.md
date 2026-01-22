---
name: mapping-specifications
description: Use this skill when working with SDTM mapping specification files. Covers parsing Excel-based mapping specs, understanding transformation DSL functions (ASSIGN, CONCAT, IF, etc.), and executing specification-driven transformations for all 63 SDTM domains. Essential for dynamic, non-hardcoded SDTM conversions.
---

# SDTM Mapping Specification Skill

## Overview

This skill provides expertise in working with SDTM mapping specification files, which define the transformation rules for converting source data to SDTM format. The mapping engine supports all **63 SDTM domains** (SDTM-IG 3.4) and a Domain Specific Language (DSL) for expressing complex transformations declaratively.

## Supported SDTM Domains (63 Total)

### Special Purpose Domains (4)
| Code | Domain Name |
|------|-------------|
| CO | Comments |
| DM | Demographics |
| SE | Subject Elements |
| SV | Subject Visits |

### Interventions Domains (7)
| Code | Domain Name |
|------|-------------|
| AG | Procedure Agents |
| CM | Concomitant Medications |
| EC | Exposure as Collected |
| EX | Exposure |
| ML | Meals |
| PR | Procedures |
| SU | Substance Use |

### Events Domains (6)
| Code | Domain Name |
|------|-------------|
| AE | Adverse Events |
| CE | Clinical Events |
| DS | Disposition |
| DV | Protocol Deviations |
| HO | Healthcare Encounters |
| MH | Medical History |

### Findings Domains (37)
| Code | Domain Name |
|------|-------------|
| BE | Biospecimen Events |
| BM | Bone Measurements |
| BS | Biospecimen Findings |
| CP | Cell Phenotyping |
| CV | Cardiovascular System Findings |
| DA | Drug Accountability |
| DD | Death Details |
| EG | ECG Test Results |
| FA | Findings About Events or Interventions |
| FT | Functional Tests |
| GF | Genomics Findings |
| IE | Inclusion/Exclusion Criteria Not Met |
| IS | Immunogenicity Specimen Assessments |
| LB | Laboratory Test Results |
| MB | Microbiology Specimen |
| MI | Microscopic Findings |
| MK | Musculoskeletal System Findings |
| MO | Morphology |
| MS | Microbiology Susceptibility |
| NV | Nervous System Findings |
| OE | Ophthalmic Examinations |
| OX | Oxygen Saturation Measurements |
| PC | Pharmacokinetics Concentrations |
| PE | Physical Examination |
| PI | Principal Investigator |
| PP | Pharmacokinetics Parameters |
| QS | Questionnaires |
| RE | Respiratory System Findings |
| RP | Reproductive System Findings |
| RS | Disease Response and Clinical Classification |
| SC | Subject Characteristics |
| SK | Skin Findings |
| SS | Subject Status |
| TR | Tumor/Lesion Results |
| TU | Tumor/Lesion Identification |
| UR | Urinary System Findings |
| VS | Vital Signs |

### Trial Design Domains (7)
| Code | Domain Name |
|------|-------------|
| TA | Trial Arms |
| TD | Trial Disease Assessments |
| TE | Trial Elements |
| TI | Trial Inclusion/Exclusion Criteria |
| TM | Trial Disease Milestones |
| TS | Trial Summary |
| TV | Trial Visits |

### Device Domains (4)
| Code | Domain Name |
|------|-------------|
| DI | Device Identifiers |
| DO | Device Properties |
| DR | Device-Subject Relationships |
| DX | Device Events |

### Relationship Domain (1)
| Code | Domain Name |
|------|-------------|
| RELREC | Related Records |

### Supplemental Qualifier Domains (SUPP--)
All domains support supplemental qualifiers (e.g., SUPPAE, SUPPDM, SUPPLB, etc.)

## Mapping Specification Structure

### Excel File Format

Mapping specifications are typically Excel files (.xls, .xlsx) with:

1. **Title Page / Global Information** - Study metadata (sponsor, protocol, study ID)
2. **Raw Datasets** - Source dataset definitions and file references
3. **Domain Sheets** (DM, AE, CM, VS, LB, etc.) - Variable-by-variable mapping rules

### Domain Sheet Columns

| Column | Description | Example |
|--------|-------------|---------|
| Variable | Target SDTM variable name | USUBJID, AESTDTC, VSTEST |
| Variable Order | Display order (1, 2, 3, ...) | 1 |
| Label | Variable description | "Unique Subject Identifier" |
| Type | Data type (string, integer, float) | string |
| Length | Maximum character length | 40 |
| Controlled Terms or Formats | CT codelist or format name | ISO8601, (NY) |
| Origin | Data origin (CRF, Derived, Assigned) | CRF |
| Role | SDTM role | Identifier, Topic, Record Qualifier |
| Core | Requirement level (req, exp, perm) | req |
| Source Dataset | Source dataset name(s) | DEMO, AE_RAW |
| Source Variable | Source variable name(s) | SUBJID, AETERM |
| Source DataType | Source data type | Char |
| Rule/Conversion Details | Transformation rule | `set to STUDYID` |

## Transformation DSL Functions

### Basic Assignment

#### `set to VARIABLE`
Direct mapping from source to target variable.

```
Rule: set to SUBJID
Result: Copies value from SUBJID column
```

#### `ASSIGN("value")`
Assign a constant value.

```
Rule: ASSIGN("DM")
Result: Always returns "DM"

Rule: ASSIGN("MAXIS-08")
Result: Always returns "MAXIS-08"
```

### String Functions

#### `CONCAT(a, b, c, ...)`
Concatenate multiple values.

```
Rule: CONCAT(STUDYID, "-", SUBJID)
Source: STUDYID="MAXIS-08", SUBJID="001"
Result: "MAXIS-08-001"

Rule: CONCAT(DATASET.VAR1, DATASET.VAR2)
Result: Concatenates values from specific dataset
```

#### `SUBSTR(field, start, length)`
Extract substring (1-based indexing).

```
Rule: SUBSTR(USUBJID, 1, 8)
Source: USUBJID="MAXIS-08-001"
Result: "MAXIS-08"

Rule: SUBSTR(BIRTHDT, 1, 4)
Source: BIRTHDT="19850623"
Result: "1985"
```

#### `UPCASE(field)`
Convert to uppercase.

```
Rule: UPCASE(AETERM)
Source: AETERM="Headache"
Result: "HEADACHE"
```

#### `TRIM(field)`
Remove leading/trailing whitespace.

```
Rule: TRIM(CMTRT)
Source: CMTRT="  Aspirin  "
Result: "Aspirin"
```

#### `COMPRESS(field, pattern)`
Remove specified characters.

```
Rule: COMPRESS(PHONE, "-")
Source: PHONE="555-123-4567"
Result: "5551234567"
```

### Conditional Logic

#### `IF(condition, true_value, false_value)`
Conditional assignment.

```
Rule: IF(SEX == "M", "Male", "Female")
Source: SEX="M"
Result: "Male"

Rule: IF(AESER == "Y", "Yes", "No")
Source: AESER="N"
Result: "No"

# Nested conditions
Rule: IF(AESEV == "MILD", "1", IF(AESEV == "MODERATE", "2", "3"))
```

**Supported operators:** `==`, `!=`, `>`, `<`, `>=`, `<=`, `||` (OR), `&&` (AND)

### Date Functions

#### `ISO8601DATEFORMAT(field, format)`
Convert to ISO 8601 date format.

```
Rule: ISO8601DATEFORMAT(BIRTHDT, "YYYYMMDD")
Source: BIRTHDT="19850623"
Result: "1985-06-23"

Rule: ISO8601DATEFORMAT(AESTDT, "DD/MM/YYYY")
Source: AESTDT="15/01/2024"
Result: "2024-01-15"
```

**Supported input formats:**
- `YYYYMMDD` - 20240115
- `YYYY-MM-DD` - 2024-01-15
- `DD-MON-YYYY` - 15-Jan-2024
- `DD/MM/YYYY` - 15/01/2024
- `MM/DD/YYYY` - 01/15/2024

#### `ISO8601DATETIMEFORMATS(field, format1, format2, ...)`
Try multiple date formats until one parses.

```
Rule: ISO8601DATETIMEFORMATS(VISITDT, "YYYYMMDD", "DD-MON-YYYY", "MM/DD/YYYY")
# Tries each format in order until successful
```

### Codelist Functions

#### `FORMAT(field, codelist)`
Apply codelist mapping.

```
Rule: FORMAT(AESEV, "SEVERITY")
# Looks up value in SEVERITY codelist
# e.g., "1" -> "MILD", "2" -> "MODERATE", "3" -> "SEVERE"
```

### Dataset-Qualified References

Reference variables from specific datasets using dot notation:

```
Rule: DEMO.SUBJID
# Gets SUBJID from DEMO dataset specifically

Rule: CONCAT(DEMO.STUDYID, "-", DEMO.SUBJID)
# Explicitly references DEMO dataset for both variables
```

## Using the Mapping Engine

### Step 1: Load Specification

```python
# Use the tool to load a mapping specification
result = await load_mapping_specification("/path/to/mapping.xlsx")

# Returns:
# {
#     "success": True,
#     "domains_available": 15,
#     "domains": [
#         {"domain": "DM", "num_variables": 28, "source_datasets": ["DEMO"]},
#         {"domain": "AE", "num_variables": 43, "source_datasets": ["AE_RAW"]},
#         ...
#     ]
# }
```

### Step 2: Review Domain Mapping

```python
# Get details about a specific domain's mapping
details = await get_domain_mapping_details("DM")

# Returns variable-by-variable mapping rules
# {
#     "domain": "DM",
#     "variables": [
#         {"variable": "STUDYID", "rule": "ASSIGN(\"MAXIS-08\")", ...},
#         {"variable": "USUBJID", "rule": "CONCAT(STUDYID, \"-\", SUBJID)", ...},
#         ...
#     ]
# }
```

### Step 3: Transform Domain

```python
# Transform source data using the loaded specification
result = await transform_domain_with_spec(
    domain="DM",
    source_files={
        "DEMO": "/data/source/demographics.csv",
        "VISITS": "/data/source/visits.csv"
    },
    output_path="/data/sdtm/dm.csv",
    study_id="MAXIS-08"  # Optional override
)

# Returns:
# {
#     "success": True,
#     "domain": "DM",
#     "records_out": 150,
#     "columns_out": 28,
#     "output_path": "/data/sdtm/dm.csv"
# }
```

### Standalone Transformation

For one-off transformations without loading spec separately:

```python
result = await transform_domain_standalone(
    spec_path="/path/to/mapping.xlsx",
    domain="AE",
    source_files={"AE_RAW": "/data/source/adverse_events.csv"},
    output_path="/data/sdtm/ae.csv"
)
```

## Common Transformation Patterns

### Demographics (DM)

| Variable | Typical Rule |
|----------|--------------|
| STUDYID | `ASSIGN("STUDY-001")` |
| DOMAIN | `ASSIGN("DM")` |
| USUBJID | `CONCAT(STUDYID, "-", SUBJID)` |
| SUBJID | `set to SUBJECT_ID` |
| RFSTDTC | `ISO8601DATEFORMAT(FIRST_DOSE_DATE, "YYYYMMDD")` |
| AGE | `set to AGE` |
| SEX | `FORMAT(GENDER, "SEX")` or `IF(GENDER=="M", "M", "F")` |
| RACE | `UPCASE(RACE)` |
| ETHNIC | `IF(HISPANIC=="Y", "HISPANIC OR LATINO", "NOT HISPANIC OR LATINO")` |

### Adverse Events (AE)

| Variable | Typical Rule |
|----------|--------------|
| AETERM | `UPCASE(AE_TERM)` |
| AEDECOD | `set to PREFERRED_TERM` |
| AESTDTC | `ISO8601DATEFORMAT(AE_START_DATE, "DD-MON-YYYY")` |
| AESER | `IF(SERIOUS=="YES", "Y", "N")` |
| AESEV | `FORMAT(SEVERITY, "AESEV")` |
| AESEQ | Auto-generated sequence number |

### Lab Results (LB)

| Variable | Typical Rule |
|----------|--------------|
| LBTESTCD | `set to TEST_CODE` |
| LBTEST | `set to TEST_NAME` |
| LBORRES | `set to RESULT_VALUE` |
| LBORRESU | `set to RESULT_UNIT` |
| LBDTC | `ISO8601DATETIMEFORMATS(COLLECTION_DT, "YYYYMMDD", "DD/MM/YYYY")` |

## Instructions for Agent

When working with mapping specifications:

1. **Always Load First**: Use `load_mapping_specification` before transforming domains
2. **Review Before Transform**: Use `get_domain_mapping_details` to understand the mapping rules
3. **Match Source Dataset Names**: Ensure source file keys match dataset names in the spec
4. **Handle Missing Data**: The engine handles NULL/NaN values gracefully
5. **Check Output**: Verify column counts and null distributions after transformation

## Available Tools

- `load_mapping_specification` - Load an Excel mapping specification file
- `transform_domain_with_spec` - Transform a domain using loaded specification
- `get_domain_mapping_details` - Get detailed mapping info for a domain
- `transform_domain_standalone` - One-call transform (loads spec + transforms)
- `list_mapping_spec_domains` - List all domains available in a specification

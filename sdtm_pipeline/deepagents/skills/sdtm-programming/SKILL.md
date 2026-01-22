---
name: sdtm-programming
description: Use this skill for SDTM transformation programming in Python, SAS, and R. Covers data manipulation, SQL extraction, ETL design, date/time handling, and efficient transformation algorithms. Essential for Phase 4 (Transform) and Phase 5 (Target Data Generation).
---

# SDTM Programming and Technical Expertise Skill

## Overview

This skill provides technical programming expertise for implementing SDTM data transformations. It covers Python (Pandas/Polars), SAS, R, SQL, and ETL tool patterns commonly used in clinical data programming.

## Core Competencies

### 1. Python SDTM Programming (Primary Language)

**When to use**: Implementing transformations with Pandas/Polars, data analysis, validation scripts.

#### Standard Transformation Pattern

```python
import pandas as pd
from datetime import datetime

def transform_to_sdtm(source_df: pd.DataFrame, domain: str, study_id: str) -> pd.DataFrame:
    """Standard SDTM transformation pattern."""
    sdtm = pd.DataFrame()

    # 1. Set identifier variables
    sdtm["STUDYID"] = study_id
    sdtm["DOMAIN"] = domain

    # 2. Apply column mappings
    column_map = get_column_mappings(domain)
    for src, tgt in column_map.items():
        if src in source_df.columns:
            sdtm[tgt] = source_df[src]

    # 3. Generate USUBJID
    if "SUBJID" in sdtm.columns:
        sdtm["USUBJID"] = study_id + "-" + sdtm["SUBJID"].astype(str)

    # 4. Add sequence variable
    seq_var = f"{domain}SEQ"
    sdtm[seq_var] = range(1, len(sdtm) + 1)

    # 5. Reorder columns (identifiers first)
    id_cols = ["STUDYID", "DOMAIN", "USUBJID", seq_var]
    other_cols = [c for c in sdtm.columns if c not in id_cols]
    sdtm = sdtm[[c for c in id_cols if c in sdtm.columns] + other_cols]

    return sdtm
```

#### Vertical Transposition (Findings Domains)

```python
def transpose_to_vertical(df: pd.DataFrame, domain: str, id_cols: list) -> pd.DataFrame:
    """Convert horizontal lab/vital signs data to vertical SDTM format."""
    # Melt from wide to long format
    value_vars = [c for c in df.columns if c not in id_cols]

    long_df = df.melt(
        id_vars=id_cols,
        value_vars=value_vars,
        var_name=f"{domain}TESTCD",
        value_name=f"{domain}ORRES"
    )

    # Add test names
    test_names = {
        "SYSBP": "Systolic Blood Pressure",
        "DIABP": "Diastolic Blood Pressure",
        "PULSE": "Pulse Rate",
        "TEMP": "Temperature",
        "WEIGHT": "Weight",
        "HEIGHT": "Height"
    }
    long_df[f"{domain}TEST"] = long_df[f"{domain}TESTCD"].map(test_names)

    return long_df
```

### 2. SAS Programming Patterns

**When to use**: Generating regulatory-compliant SAS programs for validation and submission.

#### Standard SAS SDTM Program

```sas
/*******************************************************************************
* Program: dm.sas
* Purpose: Transform source demographics to SDTM DM domain
* Input: rawdata.demographics
* Output: sdtm.dm
* Assumptions: Source data contains one record per subject
*******************************************************************************/

%let studyid = MAXIS-08;
%let domain = DM;

/* Step 1: Read source and apply mappings */
data work.dm_temp;
    set rawdata.demographics;

    length STUDYID $20 DOMAIN $2 USUBJID $40 SUBJID $20;
    length SEX $2 RACE $60 ETHNIC $30;

    STUDYID = "&studyid";
    DOMAIN = "&domain";
    SUBJID = SUBJECT_ID;
    USUBJID = catx('-', STUDYID, SUBJID);

    /* Map controlled terminology */
    if upcase(GENDER) in ('M', 'MALE') then SEX = 'M';
    else if upcase(GENDER) in ('F', 'FEMALE') then SEX = 'F';
    else SEX = 'U';
run;

/* Step 2: Apply date conversions */
data work.dm_dates;
    set work.dm_temp;

    /* Convert to ISO 8601 */
    if not missing(BIRTH_DATE) then
        BRTHDTC = put(BIRTH_DATE, IS8601DA.);

    if not missing(FIRST_DOSE_DATE) then
        RFSTDTC = put(FIRST_DOSE_DATE, IS8601DA.);
run;

/* Step 3: Final dataset with standard variable order */
data sdtm.dm (label="Demographics");
    retain STUDYID DOMAIN USUBJID SUBJID RFSTDTC RFENDTC
           SITEID BRTHDTC AGE AGEU SEX RACE ETHNIC ARMCD ARM COUNTRY;
    set work.dm_dates;
run;
```

### 3. R Programming Patterns

**When to use**: Statistical analysis, data quality reports, alternative to SAS.

#### R tidyverse Pattern

```r
library(tidyverse)
library(lubridate)

transform_to_dm <- function(source_df, study_id) {
  source_df %>%
    mutate(
      STUDYID = study_id,
      DOMAIN = "DM",
      USUBJID = paste(study_id, SUBJECT_ID, sep = "-"),
      SUBJID = as.character(SUBJECT_ID),

      # Apply controlled terminology
      SEX = case_when(
        toupper(GENDER) %in% c("M", "MALE") ~ "M",
        toupper(GENDER) %in% c("F", "FEMALE") ~ "F",
        TRUE ~ "U"
      ),

      # ISO 8601 date conversion
      BRTHDTC = format(as.Date(BIRTH_DATE), "%Y-%m-%d"),
      RFSTDTC = format(as.Date(FIRST_DOSE_DATE), "%Y-%m-%d")
    ) %>%
    select(
      STUDYID, DOMAIN, USUBJID, SUBJID, RFSTDTC, RFENDTC,
      SITEID, BRTHDTC, AGE, AGEU, SEX, RACE, ETHNIC, ARMCD, ARM, COUNTRY
    )
}
```

### 4. SQL Data Extraction

**When to use**: Extracting data from EDC databases, data warehouse queries.

#### EDC Extraction Pattern

```sql
-- Extract subject demographics from EDC database
SELECT
    s.SUBJECT_NUMBER as SUBJECT_ID,
    s.SITE_ID as SITE,
    d.BIRTH_DATE,
    d.GENDER,
    d.RACE_CODE as RACE,
    d.ETHNIC_CODE as ETHNIC,
    d.COUNTRY_CODE as COUNTRY,
    e.FIRST_DOSE_DATE,
    e.LAST_DOSE_DATE,
    a.ARM_CODE as ARMCD,
    a.ARM_NAME as ARM
FROM
    SUBJECTS s
    LEFT JOIN DEMOGRAPHICS d ON s.SUBJECT_NUMBER = d.SUBJECT_NUMBER
    LEFT JOIN EXPOSURE e ON s.SUBJECT_NUMBER = e.SUBJECT_NUMBER
    LEFT JOIN RANDOMIZATION a ON s.SUBJECT_NUMBER = a.SUBJECT_NUMBER
WHERE
    s.STATUS = 'ENROLLED'
    AND s.STUDY_ID = 'MAXIS-08';
```

### 5. Date/Time Handling

**When to use**: Converting various date formats to ISO 8601, handling partial dates.

#### Python Date Conversion

```python
from datetime import datetime
import re

def convert_to_iso8601(date_value: str) -> str:
    """Convert various date formats to ISO 8601."""
    if pd.isna(date_value) or date_value == '':
        return ''

    date_str = str(date_value).strip()

    # Common patterns
    patterns = [
        (r'^\d{4}-\d{2}-\d{2}$', '%Y-%m-%d'),           # 2024-01-15
        (r'^\d{2}/\d{2}/\d{4}$', '%m/%d/%Y'),           # 01/15/2024
        (r'^\d{2}-[A-Za-z]{3}-\d{4}$', '%d-%b-%Y'),     # 15-Jan-2024
        (r'^\d{8}$', '%Y%m%d'),                          # 20240115
        (r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', None),      # Already ISO
    ]

    for pattern, fmt in patterns:
        if re.match(pattern, date_str):
            if fmt is None:
                return date_str  # Already ISO format
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

    return ''  # Unable to parse

def handle_partial_date(year: int, month: int = None, day: int = None) -> str:
    """Create ISO 8601 partial date."""
    if year is None:
        return ''
    if month is None:
        return str(year)
    if day is None:
        return f"{year}-{month:02d}"
    return f"{year}-{month:02d}-{day:02d}"
```

### 6. ETL Pipeline Design

**When to use**: Designing scalable transformation pipelines, parallel processing.

#### Parallel Domain Processing

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def transform_all_domains(source_files: dict, study_id: str) -> dict:
    """Transform multiple domains in parallel."""
    results = {}

    async def transform_domain(domain: str, file_path: str):
        # Each domain transformation runs in parallel
        df = pd.read_csv(file_path)
        transformed = transform_to_sdtm(df, domain, study_id)
        return domain, transformed

    tasks = [
        transform_domain(domain, path)
        for domain, path in source_files.items()
    ]

    for domain, result in await asyncio.gather(*tasks):
        results[domain] = result

    return results
```

## Instructions for Agent

When the agent receives a programming task:

### ⚠️ CRITICAL: Mapping Specification Requirement

**BEFORE any transformation, you MUST have a mapping specification that defines:**
- How source columns map to SDTM variables
- Transformation rules (date formats, controlled terminology, derivations)
- Domain-specific requirements

**The correct workflow is:**
1. Analyze source data structure (`analyze_source_file`)
2. **Generate mapping specification** (`generate_mapping_spec`) ← REQUIRED STEP
3. Save mapping specification (`save_mapping_spec`)
4. Execute transformation (`transform_to_sdtm`) with the mapping spec
5. Validate output

**Never skip the mapping generation step!** Without a mapping specification:
- Transformation will produce incorrect SDTM data
- Variables may be misaligned or missing
- Controlled terminology will not be applied correctly

### 1. Language Selection
   - Python (Pandas): Default for most transformations
   - SAS: When regulatory submission requires SAS programs
   - R: When statistical analysis is primary goal
   - SQL: When extracting from databases

### 2. Code Generation Tools
   - Use `generate_mapping_spec` FIRST to create mapping specification
   - Use `transform_to_sdtm` for Python transformations (requires mapping_spec)
   - Use `generate_sas_program` for SAS code
   - Use `generate_r_script` for R code

### 3. Date Handling
   - Always convert to ISO 8601
   - Handle partial dates appropriately
   - Document original format in derivation comments

### 4. Performance Considerations
   - Use Polars for large datasets (>1M rows)
   - Implement parallel processing for multiple domains
   - Profile memory usage for lab data

### 5. Code Quality
   - Include headers with program purpose
   - Add comments for complex derivations
   - Use meaningful variable names
   - Include error handling

## Available Tools

- `generate_mapping_spec` - **REQUIRED FIRST** - Create mapping specification from source
- `save_mapping_spec` - Save mapping specification to file
- `transform_to_sdtm` - Apply transformation with mapping spec (requires mapping_spec parameter)
- `generate_sas_program` - Generate SAS transformation program
- `generate_r_script` - Generate R transformation script
- `analyze_source_file` - Profile source data structure

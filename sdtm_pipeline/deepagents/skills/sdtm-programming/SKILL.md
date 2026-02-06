---
name: sdtm-programming
description: se this skill for SDTM transformation programming in Python, SAS, and R. Covers data manipulation, SQL extraction, ETL design, date/time handling, and efficient transformation algorithms. Essential for Phase 4 (Transform) and Phase 5 (Target Data Generation).
---

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

#### CDISC Controlled Terminology Reference
```python
# CDISC Controlled Terminology (common codelists)
# Source: CDISC CT Package (update version as needed)
CDISC_CT = {
    "SEX": ["M", "F", "U", "UNDIFFERENTIATED"],
    "NY": ["N", "Y"],
    "ETHNIC": [
        "HISPANIC OR LATINO", 
        "NOT HISPANIC OR LATINO", 
        "NOT REPORTED", 
        "UNKNOWN"
    ],
    "RACE": [
        "AMERICAN INDIAN OR ALASKA NATIVE",
        "ASIAN",
        "BLACK OR AFRICAN AMERICAN",
        "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER",
        "WHITE",
        "MULTIPLE",
        "OTHER",
        "UNKNOWN",
        "NOT REPORTED"
    ],
    "AESSION": [  # AE Action Taken with Study Treatment
        "DOSE INCREASED",
        "DOSE NOT CHANGED",
        "DOSE REDUCED",
        "DOSE RATE REDUCED",
        "DRUG INTERRUPTED",
        "DRUG WITHDRAWN",
        "NOT APPLICABLE",
        "UNKNOWN"
    ],
    "OUT": [  # Outcome of Event
        "FATAL",
        "NOT RECOVERED/NOT RESOLVED",
        "RECOVERED/RESOLVED",
        "RECOVERED/RESOLVED WITH SEQUELAE",
        "RECOVERING/RESOLVING",
        "UNKNOWN"
    ],
    "NCOMPLT": [  # Reason Not Completed
        "ADVERSE EVENT",
        "DEATH",
        "LACK OF EFFICACY",
        "LOST TO FOLLOW-UP",
        "PHYSICIAN DECISION",
        "PREGNANCY",
        "PROTOCOL VIOLATION",
        "RECOVERY",
        "STUDY TERMINATED BY SPONSOR",
        "WITHDRAWAL BY SUBJECT",
        "OTHER"
    ],
    "STENRF": [  # Start/End Relative to Reference Period
        "BEFORE",
        "DURING",
        "DURING/AFTER",
        "AFTER"
    ],
    "LOINC": {},  # Extensible - loaded from external reference
    "MEDDRA": {}, # Extensible - loaded from external reference
    "WHODRUG": {} # Extensible - loaded from external reference
}


def validate_controlled_terminology(
    value: str,
    codelist: str,
    extensible: bool = False
) -> tuple:
    """
    Validate value against CDISC Controlled Terminology.
    
    Args:
        value: Value to validate
        codelist: Name of CDISC codelist
        extensible: If True, allows values not in codelist
        
    Returns:
        tuple: (is_valid, mapped_value_or_error_message)
    """
    if pd.isna(value) or value == '':
        return True, ''
    
    value_upper = str(value).strip().upper()
    
    if codelist not in CDISC_CT:
        return False, f"Unknown codelist: {codelist}"
    
    valid_values = CDISC_CT[codelist]
    
    # Exact match (case-insensitive)
    for v in valid_values:
        if v.upper() == value_upper:
            return True, v  # Return properly cased value
    
    # Extensible codelists allow custom values
    if extensible:
        return True, value.strip()
    
    return False, f"Invalid value '{value}' for codelist {codelist}. Valid: {valid_values}"
```

#### Standard Transformation Pattern
```python
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Optional, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def transform_to_sdtm(
    source_df: pd.DataFrame,
    domain: str,
    study_id: str,
    mapping_spec: dict,
    reference_data: dict = None
) -> pd.DataFrame:
    """
    Standard SDTM transformation pattern.
    
    Args:
        source_df: Source data DataFrame
        domain: SDTM domain code (e.g., "DM", "AE", "LB")
        study_id: Study identifier
        mapping_spec: Mapping specification dictionary
        reference_data: Reference data from other domains (e.g., DM for RFSTDTC)
        
    Returns:
        pd.DataFrame: SDTM-compliant domain dataset
    """
    logger.info(f"Starting transformation for domain: {domain}")
    
    sdtm = pd.DataFrame()
    reference_data = reference_data or {}
    
    # 1. Set identifier variables
    sdtm["STUDYID"] = study_id
    sdtm["DOMAIN"] = domain
    
    # 2. Apply column mappings from specification
    column_map = mapping_spec.get("column_mappings", {})
    for src, tgt in column_map.items():
        if src in source_df.columns:
            sdtm[tgt] = source_df[src]
        else:
            logger.warning(f"Source column '{src}' not found")
    
    # 3. Generate USUBJID
    if "SUBJID" in sdtm.columns:
        sdtm["USUBJID"] = study_id + "-" + sdtm["SUBJID"].astype(str)
    elif "SUBJECT_ID" in source_df.columns:
        sdtm["SUBJID"] = source_df["SUBJECT_ID"].astype(str)
        sdtm["USUBJID"] = study_id + "-" + sdtm["SUBJID"]
    
    # 4. Generate --SEQ (CRITICAL: Must be unique WITHIN each USUBJID)
    seq_var = f"{domain}SEQ"
    sdtm[seq_var] = sdtm.groupby("USUBJID").cumcount() + 1
    
    # 5. Apply date conversions
    date_vars = mapping_spec.get("date_variables", [])
    for var in date_vars:
        if var in sdtm.columns:
            sdtm[var] = sdtm[var].apply(convert_to_iso8601)
    
    # 6. Calculate Study Day (--DY) if reference date available
    dtc_var = f"{domain}DTC"
    dy_var = f"{domain}DY"
    
    if dtc_var in sdtm.columns and "rfstdtc_map" in reference_data:
        rfstdtc_map = reference_data["rfstdtc_map"]
        sdtm[dy_var] = sdtm.apply(
            lambda row: calculate_study_day(
                row.get(dtc_var),
                rfstdtc_map.get(row.get("USUBJID"))
            ),
            axis=1
        )
    
    # 7. Derive EPOCH if SE domain available
    if "se_domain" in reference_data:
        sdtm["EPOCH"] = sdtm.apply(
            lambda row: derive_epoch(
                row.get(dtc_var),
                reference_data["se_domain"],
                row.get("USUBJID")
            ),
            axis=1
        )
    
    # 8. Apply controlled terminology mappings
    ct_mappings = mapping_spec.get("controlled_terminology", {})
    for var, codelist in ct_mappings.items():
        if var in sdtm.columns:
            sdtm[var] = sdtm[var].apply(
                lambda x: validate_controlled_terminology(x, codelist)[1]
            )
    
    # 9. Reorder columns (identifiers first per SDTMIG)
    id_cols = ["STUDYID", "DOMAIN", "USUBJID", seq_var]
    timing_cols = [c for c in sdtm.columns if c.endswith(("DTC", "DY", "DUR"))]
    other_cols = [c for c in sdtm.columns if c not in id_cols + timing_cols]
    
    ordered_cols = (
        [c for c in id_cols if c in sdtm.columns] +
        [c for c in other_cols if c in sdtm.columns] +
        [c for c in timing_cols if c in sdtm.columns]
    )
    sdtm = sdtm[ordered_cols]
    
    # 10. Sort per SDTM requirements
    sort_keys = mapping_spec.get("sort_keys", ["STUDYID", "USUBJID", seq_var])
    sort_keys = [k for k in sort_keys if k in sdtm.columns]
    if sort_keys:
        sdtm = sdtm.sort_values(sort_keys).reset_index(drop=True)
    
    logger.info(f"Completed {domain}: {len(sdtm)} records")
    return sdtm
```

#### Study Day Calculation (Critical: NO Day 0)
```python
def calculate_study_day(event_dtc: str, rfstdtc: str) -> Optional[int]:
    """
    Calculate study day per SDTM rules.
    
    CRITICAL RULE: There is NO Day 0 in SDTM.
    - Day 1 = Reference date (RFSTDTC)
    - Day 2 = Day after reference
    - Day -1 = Day before reference
    
    Args:
        event_dtc: Event date/time in ISO 8601 format
        rfstdtc: Reference start date/time (usually first dose)
        
    Returns:
        int: Study day, or None if calculation not possible
    """
    if pd.isna(event_dtc) or pd.isna(rfstdtc):
        return None
    
    if event_dtc == '' or rfstdtc == '':
        return None
    
    try:
        # Extract date portion (first 10 characters)
        event_date = pd.to_datetime(str(event_dtc)[:10])
        ref_date = pd.to_datetime(str(rfstdtc)[:10])
        
        diff = (event_date - ref_date).days
        
        # SDTM rule: No Day 0
        if diff >= 0:
            return diff + 1  # Day 1, 2, 3, ...
        else:
            return diff      # Day -1, -2, -3, ...
            
    except (ValueError, TypeError) as e:
        logger.warning(f"Study day calculation failed: {e}")
        return None
```

#### EPOCH Derivation
```python
def derive_epoch(
    event_dtc: str,
    se_domain: pd.DataFrame,
    usubjid: str
) -> Optional[str]:
    """
    Derive EPOCH from Subject Elements (SE) domain.
    
    Per SDTMIG: EPOCH is the period of the study during which
    the observation occurred.
    
    Args:
        event_dtc: Event date/time in ISO 8601 format
        se_domain: Subject Elements domain DataFrame
        usubjid: Unique subject identifier
        
    Returns:
        str: EPOCH value or None
    """
    if pd.isna(event_dtc) or event_dtc == '':
        return None
    
    if se_domain is None or se_domain.empty:
        return None
    
    try:
        event_date = pd.to_datetime(str(event_dtc)[:10])
        
        # Get subject's elements sorted by start date
        subj_se = se_domain[
            se_domain["USUBJID"] == usubjid
        ].sort_values("SESTDTC")
        
        if subj_se.empty:
            return None
        
        last_epoch = None
        
        for _, row in subj_se.iterrows():
            se_start = None
            se_end = None
            
            if pd.notna(row.get("SESTDTC")) and row["SESTDTC"] != '':
                se_start = pd.to_datetime(str(row["SESTDTC"])[:10])
            
            if pd.notna(row.get("SEENDTC")) and row["SEENDTC"] != '':
                se_end = pd.to_datetime(str(row["SEENDTC"])[:10])
            
            if se_start and se_end:
                if se_start <= event_date <= se_end:
                    return row["EPOCH"]
            elif se_start:
                if event_date >= se_start:
                    last_epoch = row["EPOCH"]
        
        return last_epoch
        
    except (ValueError, TypeError) as e:
        logger.warning(f"EPOCH derivation failed: {e}")
        return None
```

#### Date/Time Conversion Functions
```python
import re
from datetime import datetime
from typing import Optional, Tuple


def convert_to_iso8601(date_value: Any) -> str:
    """
    Convert various date formats to ISO 8601.
    
    Supports:
    - YYYY-MM-DD
    - YYYY-MM-DDTHH:MM:SS
    - MM/DD/YYYY
    - DD-Mon-YYYY
    - YYYYMMDD
    - Partial dates (YYYY, YYYY-MM)
    
    Args:
        date_value: Date value in various formats
        
    Returns:
        str: ISO 8601 formatted date or empty string
    """
    if pd.isna(date_value) or date_value == '':
        return ''
    
    date_str = str(date_value).strip()
    
    # Already ISO 8601 with time
    if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', date_str):
        return date_str
    
    # Already ISO 8601 date only
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    
    # Partial date: YYYY-MM
    if re.match(r'^\d{4}-\d{2}$', date_str):
        return date_str
    
    # Partial date: YYYY only
    if re.match(r'^\d{4}$', date_str):
        return date_str
    
    # Common patterns to convert
    patterns = [
        (r'^(\d{2})/(\d{2})/(\d{4})$', '%m/%d/%Y'),      # MM/DD/YYYY
        (r'^(\d{2})-(\d{2})-(\d{4})$', '%m-%d-%Y'),      # MM-DD-YYYY
        (r'^(\d{4})(\d{2})(\d{2})$', '%Y%m%d'),          # YYYYMMDD
        (r'^(\d{2})-([A-Za-z]{3})-(\d{4})$', '%d-%b-%Y'), # DD-Mon-YYYY
        (r'^(\d{2})([A-Za-z]{3})(\d{4})$', '%d%b%Y'),    # DDMonYYYY
    ]
    
    for pattern, fmt in patterns:
        if re.match(pattern, date_str):
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
    
    # Try pandas datetime parser as fallback
    try:
        dt = pd.to_datetime(date_str)
        if pd.notna(dt):
            return dt.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        pass
    
    logger.warning(f"Unable to parse date: {date_value}")
    return ''


def convert_to_iso8601_datetime(
    date_value: Any,
    time_value: Any = None
) -> str:
    """
    Convert date and optional time to ISO 8601 datetime.
    
    Args:
        date_value: Date value
        time_value: Optional time value (HH:MM, HH:MM:SS)
        
    Returns:
        str: ISO 8601 datetime or date string
    """
    date_iso = convert_to_iso8601(date_value)
    
    if not date_iso or len(date_iso) < 10:
        return date_iso  # Return partial date as-is
    
    if pd.isna(time_value) or time_value == '':
        return date_iso
    
    time_str = str(time_value).strip()
    
    # Validate and format time
    time_patterns = [
        (r'^(\d{2}):(\d{2}):(\d{2})$', lambda m: f"{m[0]}:{m[1]}:{m[2]}"),
        (r'^(\d{2}):(\d{2})$', lambda m: f"{m[0]}:{m[1]}"),
        (r'^(\d{2})(\d{2})(\d{2})$', lambda m: f"{m[0]}:{m[1]}:{m[2]}"),
        (r'^(\d{2})(\d{2})$', lambda m: f"{m[0]}:{m[1]}"),
    ]
    
    for pattern, formatter in time_patterns:
        match = re.match(pattern, time_str)
        if match:
            formatted_time = formatter(match.groups())
            return f"{date_iso}T{formatted_time}"
    
    return date_iso


def create_partial_date(
    year: Optional[int],
    month: Optional[int] = None,
    day: Optional[int] = None
) -> str:
    """
    Create ISO 8601 partial date string.
    
    Per SDTM: Partial dates are stored as-is, not imputed.
    Imputation is done in ADaM, not SDTM.
    
    Args:
        year: Year (required for any output)
        month: Month (optional)
        day: Day (optional, requires month)
        
    Returns:
        str: ISO 8601 partial date
    """
    if year is None:
        return ''
    
    if month is None:
        return str(year)
    
    if day is None:
        return f"{year}-{month:02d}"
    
    return f"{year}-{month:02d}-{day:02d}"
```

#### Vertical Transposition (Findings Domains)
```python
def transpose_to_vertical(
    df: pd.DataFrame,
    domain: str,
    id_cols: list,
    test_metadata: dict,
    reference_data: dict = None
) -> pd.DataFrame:
    """
    Convert horizontal lab/vital signs data to vertical SDTM format.
    
    Args:
        df: Source DataFrame in horizontal format
        domain: SDTM domain code (e.g., "VS", "LB", "EG")
        id_cols: Identifier columns to preserve
        test_metadata: Dictionary of test specifications
            {
                "SYSBP": {
                    "test": "Systolic Blood Pressure",
                    "unit": "mmHg",
                    "standard_unit": "mmHg",
                    "conversion_factor": 1.0
                }
            }
        reference_data: Reference data including rfstdtc_map and se_domain
        
    Returns:
        pd.DataFrame: Vertical SDTM format
    """
    reference_data = reference_data or {}
    
    # Identify value columns (not ID columns, not visit/date columns)
    preserved_cols = id_cols + ["VISIT", "VISITNUM", "VISIT_DATE", "VISITDY"]
    preserved_cols = [c for c in preserved_cols if c in df.columns]
    value_vars = [c for c in df.columns if c not in preserved_cols]
    
    # Define variable names
    testcd_var = f"{domain}TESTCD"
    test_var = f"{domain}TEST"
    orres_var = f"{domain}ORRES"
    orresu_var = f"{domain}ORRESU"
    stresc_var = f"{domain}STRESC"
    stresn_var = f"{domain}STRESN"
    stresu_var = f"{domain}STRESU"
    stat_var = f"{domain}STAT"
    dtc_var = f"{domain}DTC"
    dy_var = f"{domain}DY"
    blfl_var = f"{domain}BLFL"
    
    # Melt from wide to long format
    long_df = df.melt(
        id_vars=preserved_cols,
        value_vars=value_vars,
        var_name=testcd_var,
        value_name=orres_var
    )
    
    # Add test names from metadata
    long_df[test_var] = long_df[testcd_var].map(
        lambda x: test_metadata.get(x, {}).get("test", x)
    )
    
    # Add original result units
    long_df[orresu_var] = long_df[testcd_var].map(
        lambda x: test_metadata.get(x, {}).get("unit", "")
    )
    
    # Standardized character result
    long_df[stresc_var] = long_df[orres_var].apply(
        lambda x: str(x).strip() if pd.notna(x) and x != '' else ''
    )
    
    # Standardized numeric result with unit conversion
    def convert_to_standard(row):
        if pd.isna(row[orres_var]) or row[orres_var] == '':
            return np.nan
        try:
            value = float(row[orres_var])
            factor = test_metadata.get(row[testcd_var], {}).get("conversion_factor", 1.0)
            return value * factor
        except (ValueError, TypeError):
            return np.nan
    
    long_df[stresn_var] = long_df.apply(convert_to_standard, axis=1)
    
    # Standard units
    long_df[stresu_var] = long_df[testcd_var].map(
        lambda x: test_metadata.get(x, {}).get("standard_unit", "")
    )
    
    # Date/time conversion
    if "VISIT_DATE" in long_df.columns:
        long_df[dtc_var] = long_df["VISIT_DATE"].apply(convert_to_iso8601)
    
    # Study day calculation
    if dtc_var in long_df.columns and "rfstdtc_map" in reference_data:
        rfstdtc_map = reference_data["rfstdtc_map"]
        long_df[dy_var] = long_df.apply(
            lambda row: calculate_study_day(
                row.get(dtc_var),
                rfstdtc_map.get(row.get("USUBJID"))
            ),
            axis=1
        )
    
    # NOT DONE status (when result is missing)
    long_df[stat_var] = long_df[orres_var].apply(
        lambda x: "NOT DONE" if pd.isna(x) or x == '' else None
    )
    
    # Remove records where original result is empty (unless you want NOT DONE records)
    # Uncomment if NOT DONE records should be excluded:
    # long_df = long_df[long_df[stat_var] != "NOT DONE"]
    
    return long_df


def derive_baseline_flag(
    df: pd.DataFrame,
    domain: str,
    baseline_visits: list = None,
    use_last_pretreatment: bool = True
) -> pd.DataFrame:
    """
    Derive baseline flag (--BLFL) per SDTM rules.
    
    IMPORTANT: --BLFL = "Y" for baseline record, null otherwise.
    Never use "N" - only "Y" or null.
    
    Args:
        df: Domain DataFrame with findings data
        domain: Domain code
        baseline_visits: List of visit names considered baseline
        use_last_pretreatment: If True, use last pre-treatment record
        
    Returns:
        pd.DataFrame: DataFrame with BLFL added
    """
    baseline_visits = baseline_visits or ["SCREENING", "BASELINE", "DAY 1", "VISIT 1"]
    
    dtc_var = f"{domain}DTC"
    dy_var = f"{domain}DY"
    blfl_var = f"{domain}BLFL"
    testcd_var = f"{domain}TESTCD"
    
    df = df.copy()
    df[blfl_var] = None
    
    # Group by subject and test
    for (usubjid, testcd), group in df.groupby(["USUBJID", testcd_var]):
        group_idx = group.index
        
        if use_last_pretreatment and dy_var in df.columns:
            # Find last pre-treatment record (DY <= 1 or DY is null and visit is baseline)
            pretreat_mask = (
                (group[dy_var] <= 1) | 
                (group[dy_var].isna() & group["VISIT"].isin(baseline_visits))
            )
            pretreat_records = group[pretreat_mask]
            
            if not pretreat_records.empty:
                # Use record with latest date/time
                if dtc_var in pretreat_records.columns:
                    baseline_idx = pretreat_records[dtc_var].idxmax()
                else:
                    baseline_idx = pretreat_records.index[-1]
                df.loc[baseline_idx, blfl_var] = "Y"
        else:
            # Use visit-based logic
            baseline_records = group[group["VISIT"].isin(baseline_visits)]
            
            if not baseline_records.empty:
                # Use last baseline visit record
                baseline_idx = baseline_records.index[-1]
                df.loc[baseline_idx, blfl_var] = "Y"
    
    return df
```

### 2. SAS Programming Patterns

**When to use**: Generating regulatory-compliant SAS programs for validation and submission.

#### Standard SAS SDTM Program (Complete Example)
```sas
/*******************************************************************************
* Program:     dm.sas
* Purpose:     Transform source demographics to SDTM DM domain
* Input:       rawdata.demographics, rawdata.exposure, rawdata.randomization
* Output:      sdtm.dm
* SDTM IG:     Version 3.4
* CT Version:  2023-12-15
* Author:      [Programmer Name]
* Date:        [Date]
* 
* Modification History:
* Date        Author      Description
* ----------  ----------  --------------------------------------------------
* YYYY-MM-DD  [Name]      Initial creation
*******************************************************************************/

%let studyid = MAXIS-08;
%let domain = DM;

/*-----------------------------------------------------------------------------
  Step 1: Read source demographics and apply initial mappings
-----------------------------------------------------------------------------*/
data work.dm_temp;
    length STUDYID $20 DOMAIN $2 USUBJID $40 SUBJID $20
           SEX $2 RACE $100 ETHNIC $60 COUNTRY $3
           ARMCD $20 ARM $200 ACTARMCD $20 ACTARM $200;
    
    set rawdata.demographics;
    
    /* Identifier variables */
    STUDYID = "&studyid";
    DOMAIN = "&domain";
    SUBJID = strip(put(SUBJECT_ID, best.));
    USUBJID = catx('-', STUDYID, SUBJID);
    SITEID = strip(put(SITE_ID, best.));
    
    /* Map SEX - CDISC Controlled Terminology (C66731) */
    select (upcase(strip(GENDER)));
        when ('M', 'MALE')           SEX = 'M';
        when ('F', 'FEMALE')         SEX = 'F';
        when ('U', 'UNKNOWN', '')    SEX = 'U';
        otherwise                    SEX = 'U';
    end;
    
    /* Map RACE - CDISC Controlled Terminology (C74457) - Extensible */
    select (upcase(strip(RACE_CODE)));
        when ('WHITE', 'CAUCASIAN')           
            RACE = 'WHITE';
        when ('BLACK', 'AFRICAN AMERICAN', 'AFRICAN-AMERICAN')    
            RACE = 'BLACK OR AFRICAN AMERICAN';
        when ('ASIAN')                        
            RACE = 'ASIAN';
        when ('NATIVE', 'AMERICAN INDIAN', 'ALASKA NATIVE')    
            RACE = 'AMERICAN INDIAN OR ALASKA NATIVE';
        when ('PACIFIC', 'HAWAIIAN', 'PACIFIC ISLANDER')          
            RACE = 'NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER';
        when ('MULTIPLE', 'MIXED', 'MULTIRACIAL')            
            RACE = 'MULTIPLE';
        when ('UNKNOWN', 'UNK', '')           
            RACE = 'UNKNOWN';
        when ('NOT REPORTED')
            RACE = 'NOT REPORTED';
        otherwise                             
            RACE = 'OTHER';
    end;
    
    /* Map ETHNIC - CDISC Controlled Terminology (C66790) */
    select (upcase(strip(ETHNIC_CODE)));
        when ('HISPANIC', 'LATINO', 'HISPANIC OR LATINO')     
            ETHNIC = 'HISPANIC OR LATINO';
        when ('NOT HISPANIC', 'NOT HISPANIC OR LATINO', 'NON-HISPANIC')           
            ETHNIC = 'NOT HISPANIC OR LATINO';
        when ('NOT REPORTED')
            ETHNIC = 'NOT REPORTED';
        otherwise                       
            ETHNIC = 'UNKNOWN';
    end;
    
    /* Country - ISO 3166-1 alpha-3 */
    COUNTRY = upcase(strip(COUNTRY_CODE));
run;

/*-----------------------------------------------------------------------------
  Step 2: Date conversions and reference date hierarchy
-----------------------------------------------------------------------------*/
data work.dm_dates;
    set work.dm_temp;
    
    length BRTHDTC $20 RFSTDTC $20 RFENDTC $20 
           RFXSTDTC $20 RFXENDTC $20 RFICDTC $20 RFPENDTC $20
           DTHDTC $20 DTHFL $2;
    
    /* Birth date to ISO 8601 */
    if not missing(BIRTH_DATE) then
        BRTHDTC = put(BIRTH_DATE, IS8601DA.);
    
    /* Informed consent date */
    if not missing(CONSENT_DATE) then
        RFICDTC = put(CONSENT_DATE, IS8601DA.);
    
    /* Reference Start Date - First dose date */
    if not missing(FIRST_DOSE_DATE) then
        RFSTDTC = put(FIRST_DOSE_DATE, IS8601DA.);
    
    /* Reference End Date - Last contact/last dose + follow-up */
    if not missing(LAST_CONTACT_DATE) then
        RFENDTC = put(LAST_CONTACT_DATE, IS8601DA.);
    
    /* First/Last exposure to study treatment */
    if not missing(FIRST_DOSE_DATE) then
        RFXSTDTC = put(FIRST_DOSE_DATE, IS8601DA.);
    if not missing(LAST_DOSE_DATE) then
        RFXENDTC = put(LAST_DOSE_DATE, IS8601DA.);
    
    /* Death information */
    if not missing(DEATH_DATE) then do;
        DTHDTC = put(DEATH_DATE, IS8601DA.);
        DTHFL = 'Y';
        RFPENDTC = DTHDTC;  /* Reference period end = death for deceased subjects */
    end;
run;

/*-----------------------------------------------------------------------------
  Step 3: AGE derivation - at time of informed consent
-----------------------------------------------------------------------------*/
data work.dm_age;
    set work.dm_dates;
    
    length AGEU $10;
    
    /* Calculate AGE at informed consent (or first dose if consent date missing) */
    if not missing(BIRTH_DATE) then do;
        if not missing(CONSENT_DATE) then
            AGE = intck('YEAR', BIRTH_DATE, CONSENT_DATE, 'C');
        else if not missing(FIRST_DOSE_DATE) then
            AGE = intck('YEAR', BIRTH_DATE, FIRST_DOSE_DATE, 'C');
    end;
    
    /* Age units - always YEARS for adults */
    if not missing(AGE) then do;
        if AGE >= 18 then
            AGEU = 'YEARS';
        else if AGE >= 2 then
            AGEU = 'YEARS';
        else do;
            /* For infants, may need MONTHS or DAYS */
            AGEU = 'YEARS';
        end;
    end;
run;

/*-----------------------------------------------------------------------------
  Step 4: Merge randomization/treatment arm data
-----------------------------------------------------------------------------*/
proc sort data=work.dm_age; 
    by USUBJID; 
run;

proc sort data=rawdata.randomization out=work.rand (keep=SUBJECT_ID ARM_CODE ARM_NAME ACTUAL_ARM_CODE ACTUAL_ARM_NAME); 
    by SUBJECT_ID; 
run;

data work.dm_arm;
    merge work.dm_age (in=a)
          work.rand (in=b rename=(SUBJECT_ID=SUBJID_NUM));
    by USUBJID;
    if a;
    
    /* Planned arm */
    if not missing(ARM_CODE) then do;
        ARMCD = strip(ARM_CODE);
        ARM = strip(ARM_NAME);
    end;
    
    /* Actual arm (if different from planned, e.g., due to randomization error) */
    if not missing(ACTUAL_ARM_CODE) then do;
        ACTARMCD = strip(ACTUAL_ARM_CODE);
        ACTARM = strip(ACTUAL_ARM_NAME);
    end;
    else do;
        ACTARMCD = ARMCD;
        ACTARM = ARM;
    end;
    
    /* Handle screen failures and not treated subjects */
    if missing(ARMCD) then do;
        if missing(RFSTDTC) then do;
            /* Screen failure - never dosed */
            ARMCD = 'SCRNFAIL';
            ARM = 'Screen Failure';
            ACTARMCD = 'SCRNFAIL';
            ACTARM = 'Screen Failure';
        end;
        else do;
            /* Randomized but arm not recorded - data issue */
            ARMCD = 'UNASSIGNED';
            ARM = 'Unassigned';
        end;
    end;
    
    drop SUBJID_NUM;
run;

/*-----------------------------------------------------------------------------
  Step 5: Final dataset with CDISC-compliant variable order and labels
-----------------------------------------------------------------------------*/
data sdtm.dm (label="Demographics");
    retain 
        /* Identifier variables */
        STUDYID DOMAIN USUBJID SUBJID 
        /* Reference dates */
        RFSTDTC RFENDTC RFXSTDTC RFXENDTC RFICDTC RFPENDTC
        /* Death */
        DTHDTC DTHFL
        /* Site/Investigator */
        SITEID INVID INVNAM
        /* Demographics */
        BRTHDTC AGE AGEU SEX RACE ETHNIC
        /* Treatment */
        ARMCD ARM ACTARMCD ACTARM
        /* Country/Timing */
        COUNTRY DMDTC DMDY;
    
    set work.dm_arm;
    
    /* Keep only SDTM DM variables */
    keep STUDYID DOMAIN USUBJID SUBJID 
         RFSTDTC RFENDTC RFXSTDTC RFXENDTC RFICDTC RFPENDTC
         DTHDTC DTHFL
         SITEID 
         BRTHDTC AGE AGEU SEX RACE ETHNIC 
         ARMCD ARM ACTARMCD ACTARM 
         COUNTRY;
    
    /* Variable labels per SDTMIG */
    label
        STUDYID   = "Study Identifier"
        DOMAIN    = "Domain Abbreviation"
        USUBJID   = "Unique Subject Identifier"
        SUBJID    = "Subject Identifier for the Study"
        RFSTDTC   = "Subject Reference Start Date/Time"
        RFENDTC   = "Subject Reference End Date/Time"
        RFXSTDTC  = "Date/Time of First Study Treatment"
        RFXENDTC  = "Date/Time of Last Study Treatment"
        RFICDTC   = "Date/Time of Informed Consent"
        RFPENDTC  = "Date/Time of End of Participation"
        DTHDTC    = "Date/Time of Death"
        DTHFL     = "Subject Death Flag"
        SITEID    = "Study Site Identifier"
        BRTHDTC   = "Date/Time of Birth"
        AGE       = "Age"
        AGEU      = "Age Units"
        SEX       = "Sex"
        RACE      = "Race"
        ETHNIC    = "Ethnicity"
        ARMCD     = "Planned Arm Code"
        ARM       = "Description of Planned Arm"
        ACTARMCD  = "Actual Arm Code"
        ACTARM    = "Description of Actual Arm"
        COUNTRY   = "Country";
run;

/*-----------------------------------------------------------------------------
  Step 6: Sort per SDTM IG requirements
-----------------------------------------------------------------------------*/
proc sort data=sdtm.dm;
    by STUDYID USUBJID;
run;

/*-----------------------------------------------------------------------------
  Step 7: Generate dataset-level metadata for define.xml
-----------------------------------------------------------------------------*/
proc contents data=sdtm.dm out=work.dm_contents noprint;
run;

proc sql noprint;
    select count(*) into :dm_nobs trimmed from sdtm.dm;
quit;

%put NOTE: DM domain created with &dm_nobs observations;
```

#### SAS Macro for Study Day Calculation
```sas
/*******************************************************************************
* Macro:   %CALC_STUDY_DAY
* Purpose: Calculate study day per SDTM rules (NO Day 0)
* 
* Parameters:
*   inds     - Input dataset
*   outds    - Output dataset
*   dtcvar   - Date/time variable (ISO 8601)
*   rfstdtc  - Reference start date variable
*   dyvar    - Output study day variable name
*******************************************************************************/
%macro calc_study_day(inds=, outds=, dtcvar=, rfstdtc=RFSTDTC, dyvar=);

    data &outds;
        set &inds;
        
        length &dyvar 8;
        
        /* Only calculate if both dates available */
        if not missing(&dtcvar) and not missing(&rfstdtc) then do;
            /* Extract date portion (first 10 characters) */
            _evtdt = input(substr(&dtcvar, 1, 10), yymmdd10.);
            _refdt = input(substr(&rfstdtc, 1, 10), yymmdd10.);
            
            if not missing(_evtdt) and not missing(_refdt) then do;
                _diff = _evtdt - _refdt;
                
                /* CRITICAL: No Day 0 in SDTM */
                if _diff >= 0 then
                    &dyvar = _diff + 1;  /* Day 1, 2, 3... */
                else
                    &dyvar = _diff;      /* Day -1, -2, -3... */
            end;
        end;
        
        drop _evtdt _refdt _diff;
    run;

%mend calc_study_day;

/* Example usage */
%calc_study_day(inds=work.ae_temp, outds=work.ae_dy, dtcvar=AESTDTC, dyvar=AESTDY);
%calc_study_day(inds=work.ae_temp, outds=work.ae_dy, dtcvar=AEENDTC, dyvar=AEENDY);
```

### 3. R Programming Patterns

**When to use**: Statistical analysis, data quality reports, alternative to SAS.

#### R tidyverse Pattern (Complete Example)
```r
library(tidyverse)
library(lubridate)
library(haven)  # For reading/writing SAS datasets

#' Transform source data to SDTM DM domain
#'
#' @param source_df Source demographics data frame
#' @param study_id Study identifier
#' @param exposure_df Optional exposure data for reference dates
#' @param randomization_df Optional randomization data for arm assignment
#' @return SDTM-compliant DM data frame
transform_to_dm <- function(source_df, study_id, exposure_df = NULL, randomization_df = NULL) {
  
  dm <- source_df %>%
    mutate(
      # Identifier variables
      STUDYID = study_id,
      DOMAIN = "DM",
      SUBJID = as.character(SUBJECT_ID),
      USUBJID = paste(study_id, SUBJID, sep = "-"),
      SITEID = as.character(SITE_ID),
      
      # Sex - CDISC CT (C66731)
      SEX = case_when(
        toupper(GENDER) %in% c("M", "MALE") ~ "M",
        toupper(GENDER) %in% c("F", "FEMALE") ~ "F",
        TRUE ~ "U"
      ),
      
      # Race - CDISC CT (C74457) - Extensible
      RACE = case_when(
        toupper(RACE_CODE) %in% c("WHITE", "CAUCASIAN") ~ "WHITE",
        toupper(RACE_CODE) %in% c("BLACK", "AFRICAN AMERICAN") ~ "BLACK OR AFRICAN AMERICAN",
        toupper(RACE_CODE) == "ASIAN" ~ "ASIAN",
        toupper(RACE_CODE) %in% c("NATIVE", "AMERICAN INDIAN") ~ "AMERICAN INDIAN OR ALASKA NATIVE",
        toupper(RACE_CODE) %in% c("PACIFIC", "HAWAIIAN") ~ "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER",
        toupper(RACE_CODE) %in% c("MULTIPLE", "MIXED") ~ "MULTIPLE",
        toupper(RACE_CODE) %in% c("UNKNOWN", "UNK", "") ~ "UNKNOWN",
        TRUE ~ "OTHER"
      ),
      
      # Ethnicity - CDISC CT (C66790)
      ETHNIC = case_when(
        toupper(ETHNIC_CODE) %in% c("HISPANIC", "LATINO", "HISPANIC OR LATINO") ~ "HISPANIC OR LATINO",
        toupper(ETHNIC_CODE) %in% c("NOT HISPANIC", "NOT HISPANIC OR LATINO") ~ "NOT HISPANIC OR LATINO",
        TRUE ~ "UNKNOWN"
      ),
      
      # Date conversions to ISO 8601
      BRTHDTC = format_iso8601_date(BIRTH_DATE),
      RFICDTC = format_iso8601_date(CONSENT_DATE),
      
      # Country - ISO 3166-1 alpha-3
      COUNTRY = toupper(COUNTRY_CODE)
    )
  
  # Merge exposure data for reference dates
  if (!is.null(exposure_df)) {
    exposure_summary <- exposure_df %>%
      group_by(SUBJECT_ID) %>%
      summarise(
        FIRST_DOSE_DATE = min(DOSE_DATE, na.rm = TRUE),
        LAST_DOSE_DATE = max(DOSE_DATE, na.rm = TRUE),
        .groups = "drop"
      )
    
    dm <- dm %>%
      left_join(exposure_summary, by = c("SUBJID" = "SUBJECT_ID")) %>%
      mutate(
        RFSTDTC = format_iso8601_date(FIRST_DOSE_DATE),
        RFENDTC = format_iso8601_date(LAST_DOSE_DATE),
        RFXSTDTC = RFSTDTC,
        RFXENDTC = RFENDTC
      )
  }
  
  # Merge randomization data
  if (!is.null(randomization_df)) {
    dm <- dm %>%
      left_join(
        randomization_df %>% select(SUBJECT_ID, ARM_CODE, ARM_NAME),
        by = c("SUBJID" = "SUBJECT_ID")
      ) %>%
      mutate(
        ARMCD = coalesce(ARM_CODE, if_else(is.na(RFSTDTC), "SCRNFAIL", "UNASSIGNED")),
        ARM = coalesce(ARM_NAME, if_else(is.na(RFSTDTC), "Screen Failure", "Unassigned")),
        ACTARMCD = ARMCD,
        ACTARM = ARM
      )
  }
  
  # Calculate AGE
  dm <- dm %>%
    mutate(
      AGE = calculate_age(BIRTH_DATE, coalesce(CONSENT_DATE, FIRST_DOSE_DATE)),
      AGEU = if_else(!is.na(AGE), "YEARS", NA_character_)
    )
  
  # Select and order SDTM variables
  dm %>%
    select(
      STUDYID, DOMAIN, USUBJID, SUBJID,
      RFSTDTC, RFENDTC, RFXSTDTC, RFXENDTC, RFICDTC,
      SITEID, BRTHDTC, AGE, AGEU, SEX, RACE, ETHNIC,
      ARMCD, ARM, ACTARMCD, ACTARM, COUNTRY
    ) %>%
    arrange(STUDYID, USUBJID)
}


#' Format date to ISO 8601
#'
#' @param date_value Date value (various formats)
#' @return Character string in ISO 8601 format
format_iso8601_date <- function(date_value) {
  if (is.na(date_value)) return(NA_character_)
  
  # Handle different input types
  if (inherits(date_value, "Date")) {
    return(format(date_value, "%Y-%m-%d"))
  }
  
  if (inherits(date_value, "POSIXct") || inherits(date_value, "POSIXlt")) {
    return(format(date_value, "%Y-%m-%dT%H:%M:%S"))
  }
  
  # Try to parse character dates
  tryCatch({
    parsed <- parse_date_time(date_value, orders = c("ymd", "mdy", "dmy", "ymd HMS"))
    if (!is.na(parsed)) {
      return(format(parsed, "%Y-%m-%d"))
    }
  }, error = function(e) NULL)
  
  return(NA_character_)
}


#' Calculate age in years
#'
#' @param birth_date Birth date
#' @param reference_date Reference date for age calculation
#' @return Age in years
calculate_age <- function(birth_date, reference_date) {
  if (is.na(birth_date) || is.na(reference_date)) return(NA_integer_)
  
  birth <- as.Date(birth_date)
  ref <- as.Date(reference_date)
  
  age <- as.integer(floor(interval(birth, ref) / years(1)))
  return(age)
}


#' Calculate study day (NO Day 0)
#'
#' @param event_dtc Event date in ISO 8601 format
#' @param rfstdtc Reference start date in ISO 8601 format
#' @return Study day (integer)
calculate_study_day <- function(event_dtc, rfstdtc) {
  if (is.na(event_dtc) || is.na(rfstdtc)) return(NA_integer_)
  
  # Extract date portion
  event_date <- as.Date(substr(event_dtc, 1, 10))
  ref_date <- as.Date(substr(rfstdtc, 1, 10))
  
  diff <- as.integer(event_date - ref_date)
  
  # CRITICAL: No Day 0 in SDTM
  if (diff >= 0) {
    return(diff + 1L)  # Day 1, 2, 3...
  } else {
    return(diff)       # Day -1, -2, -3...
  }
}
```

### 4. SQL Data Extraction

**When to use**: Extracting data from EDC databases, data warehouse queries.

#### EDC Extraction Pattern with Data Quality
```sql
/*******************************************************************************
* Query:   Extract Demographics from EDC
* Purpose: Retrieve subject demographics with data quality validation
* Source:  EDC Database (Medidata Rave / Oracle Clinical / etc.)
* Output:  Demographics extract for SDTM transformation
*******************************************************************************/

-- CTE 1: Validate and deduplicate subjects
WITH validated_subjects AS (
    SELECT 
        s.SUBJECT_NUMBER,
        s.SITE_ID,
        s.STATUS,
        s.CREATED_DATE,
        s.MODIFIED_DATE,
        -- Flag duplicate subjects
        ROW_NUMBER() OVER (
            PARTITION BY s.SUBJECT_NUMBER 
            ORDER BY s.MODIFIED_DATE DESC
        ) as rn,
        -- Flag data quality issues
        CASE 
            WHEN s.STATUS IS NULL THEN 'MISSING_STATUS'
            WHEN s.STATUS NOT IN ('ENROLLED', 'COMPLETED', 'DISCONTINUED', 'SCREEN FAILURE') 
                THEN 'INVALID_STATUS'
            ELSE 'OK'
        END as status_check
    FROM SUBJECTS s
    WHERE s.STUDY_ID = 'MAXIS-08'
),

-- CTE 2: Clean demographics with validation
demographics_clean AS (
    SELECT 
        d.SUBJECT_NUMBER,
        d.BIRTH_DATE,
        d.GENDER,
        d.RACE_CODE,
        d.ETHNIC_CODE,
        d.COUNTRY_CODE,
        -- Validate birth date
        CASE 
            WHEN d.BIRTH_DATE > CURRENT_DATE THEN 'INVALID_FUTURE_DATE'
            WHEN d.BIRTH_DATE < DATE '1900-01-01' THEN 'INVALID_OLD_DATE'
            WHEN d.BIRTH_DATE IS NULL THEN 'MISSING_DATE'
            ELSE 'VALID'
        END as birth_date_status,
        -- Validate gender
        CASE
            WHEN UPPER(d.GENDER) IN ('M', 'MALE', 'F', 'FEMALE') THEN 'VALID'
            WHEN d.GENDER IS NULL OR d.GENDER = '' THEN 'MISSING'
            ELSE 'INVALID'
        END as gender_status
    FROM DEMOGRAPHICS d
),

-- CTE 3: Exposure summary for reference dates
exposure_summary AS (
    SELECT 
        e.SUBJECT_NUMBER,
        MIN(e.DOSE_START_DATE) as FIRST_DOSE_DATE,
        MAX(e.DOSE_END_DATE) as LAST_DOSE_DATE,
        MIN(e.DOSE_START_DATETIME) as FIRST_DOSE_DATETIME,
        MAX(e.DOSE_END_DATETIME) as LAST_DOSE_DATETIME,
        COUNT(*) as DOSE_COUNT
    FROM EXPOSURE e
    WHERE e.STUDY_ID = 'MAXIS-08'
      AND e.DOSE_AMOUNT > 0  -- Exclude zero doses
    GROUP BY e.SUBJECT_NUMBER
),

-- CTE 4: Consent dates
consent_info AS (
    SELECT 
        c.SUBJECT_NUMBER,
        MIN(c.CONSENT_DATE) as FIRST_CONSENT_DATE,
        MAX(c.CONSENT_DATE) as LATEST_CONSENT_DATE
    FROM INFORMED_CONSENT c
    WHERE c.STUDY_ID = 'MAXIS-08'
      AND c.CONSENT_TYPE = 'MAIN'
      AND c.CONSENT_STATUS = 'OBTAINED'
    GROUP BY c.SUBJECT_NUMBER
)

-- Main query: Combine all data
SELECT
    -- Subject identifiers
    vs.SUBJECT_NUMBER as SUBJECT_ID,
    vs.SITE_ID as SITE,
    vs.STATUS as SUBJECT_STATUS,
    
    -- Demographics
    dc.BIRTH_DATE,
    dc.GENDER,
    dc.RACE_CODE as RACE,
    dc.ETHNIC_CODE as ETHNIC,
    dc.COUNTRY_CODE as COUNTRY,
    
    -- Reference dates
    ci.FIRST_CONSENT_DATE as CONSENT_DATE,
    es.FIRST_DOSE_DATE,
    es.LAST_DOSE_DATE,
    es.FIRST_DOSE_DATETIME,
    es.LAST_DOSE_DATETIME,
    
    -- Randomization/Arm
    r.ARM_CODE as ARMCD,
    r.ARM_NAME as ARM,
    r.RANDOMIZATION_DATE,
    
    -- Death information (if applicable)
    dt.DEATH_DATE,
    dt.DEATH_CAUSE,
    
    -- Data quality flags (for downstream processing)
    dc.birth_date_status,
    dc.gender_status,
    vs.status_check as subject_status_check,
    CASE 
        WHEN es.FIRST_DOSE_DATE IS NULL AND vs.STATUS = 'ENROLLED' 
            THEN 'MISSING_DOSE_FOR_ENROLLED'
        ELSE 'OK' 
    END as dose_status,
    CASE
        WHEN ci.FIRST_CONSENT_DATE IS NULL THEN 'MISSING_CONSENT'
        WHEN ci.FIRST_CONSENT_DATE > COALESCE(es.FIRST_DOSE_DATE, CURRENT_DATE)
            THEN 'CONSENT_AFTER_DOSE'
        ELSE 'OK'
    END as consent_status

FROM validated_subjects vs

-- Demographics (required)
INNER JOIN demographics_clean dc 
    ON vs.SUBJECT_NUMBER = dc.SUBJECT_NUMBER

-- Consent (left join - may be missing for screen failures)
LEFT JOIN consent_info ci
    ON vs.SUBJECT_NUMBER = ci.SUBJECT_NUMBER

-- Exposure (left join - screen failures won't have exposure)
LEFT JOIN exposure_summary es 
    ON vs.SUBJECT_NUMBER = es.SUBJECT_NUMBER

-- Randomization (left join - screen failures won't be randomized)
LEFT JOIN RANDOMIZATION r 
    ON vs.SUBJECT_NUMBER = r.SUBJECT_NUMBER
    AND r.STUDY_ID = 'MAXIS-08'

-- Death (left join - only for deceased subjects)
LEFT JOIN DEATH dt
    ON vs.SUBJECT_NUMBER = dt.SUBJECT_NUMBER
    AND dt.STUDY_ID = 'MAXIS-08'

WHERE vs.rn = 1  -- Deduplicate - take most recent record

ORDER BY vs.SITE_ID, vs.SUBJECT_NUMBER;
```

### 5. ETL Pipeline Design

**When to use**: Designing scalable transformation pipelines, ensuring correct processing order.

#### Domain Dependencies and Processing Order
```python
from typing import Dict, List, Set
from collections import defaultdict
import asyncio
import logging
from datetime import datetime

# Configure audit logging
logging.basicConfig(
    filename=f"sdtm_transform_{datetime.now():%Y%m%d_%H%M%S}.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Domain processing dependencies
# Key = domain, Value = list of domains that must be processed first
DOMAIN_DEPENDENCIES = {
    # Special Purpose domains - no dependencies
    "DM": [],                           # Demographics - process first
    "CO": ["DM"],                       # Comments
    "SE": ["DM"],                       # Subject Elements
    "SV": ["DM"],                       # Subject Visits
    
    # Interventions - depend on DM for USUBJID and timing
    "EX": ["DM"],                       # Exposure - needs RFSTDTC
    "EC": ["DM"],                       # Exposure as Collected
    "CM": ["DM"],                       # Concomitant Medications - needs --DY
    "SU": ["DM"],                       # Substance Use
    
    # Events - depend on DM for timing calculations
    "AE": ["DM"],                       # Adverse Events - needs --DY
    "DS": ["DM"],                       # Disposition
    "MH": ["DM"],                       # Medical History
    "DV": ["DM"],                       # Protocol Deviations
    "CE": ["DM"],                       # Clinical Events
    
    # Findings - depend on DM (timing) and SE (EPOCH)
    "LB": ["DM", "SE"],                 # Laboratory - needs RFSTDTC and EPOCH
    "VS": ["DM", "SE"],                 # Vital Signs - needs RFSTDTC and EPOCH
    "EG": ["DM", "SE"],                 # ECG - needs RFSTDTC and EPOCH
    "PE": ["DM", "SE"],                 # Physical Examination
    "QS": ["DM", "SE"],                 # Questionnaires
    "SC": ["DM"],                       # Subject Characteristics
    "DA": ["DM", "SE"],                 # Drug Accountability
    "FA": ["DM", "SE"],                 # Findings About
    
    # Oncology domains - complex dependencies
    "TU": ["DM", "SE"],                 # Tumor Identification
    "TR": ["DM", "SE", "TU"],           # Tumor Results - needs TU for linking
    "RS": ["DM", "SE", "TU", "TR"],     # Disease Response - needs TU/TR
    
    # Pharmacokinetic domains
    "PC": ["DM", "EX"],                 # PK Concentrations - needs exposure timing
    "PP": ["DM", "EX", "PC"],           # PK Parameters - needs PC data
    
    # Relationship domains - process last
    "RELREC": ["AE", "CM", "LB", "EX", "MH", "DS"],  # Links other domains
    
    # Supplemental qualifiers - after parent domain
    "SUPPDM": ["DM"],
    "SUPPAE": ["AE"],
    "SUPPLB": ["LB"],
    "SUPPVS": ["VS"],
    "SUPPCM": ["CM"],
    "SUPPEX": ["EX"],
    "SUPPDS": ["DS"],
    "SUPPMH": ["MH"],
}


def get_processing_order(domains: List[str]) -> List[str]:
    """
    Determine correct processing order based on dependencies.
    Uses topological sort to respect dependencies.
    
    Args:
        domains: List of domains to process
        
    Returns:
        List of domains in correct processing order
        
    Raises:
        ValueError: If circular dependency detected
    """
    # Build dependency graph for requested domains only
    ordered = []
    remaining = set(domains)
    processed = set()
    
    max_iterations = len(domains) * 2  # Prevent infinite loops
    iteration = 0
    
    while remaining and iteration < max_iterations:
        iteration += 1
        
        # Find domains with all dependencies satisfied
        ready = []
        for domain in remaining:
            deps = DOMAIN_DEPENDENCIES.get(domain, [])
            # Check if all dependencies are either:
            # 1. Already processed, or
            # 2. Not in our list of domains to process
            if all(dep in processed or dep not in domains for dep in deps):
                ready.append(domain)
        
        if not ready:
            # No domains ready - circular dependency
            raise ValueError(
                f"Circular dependency detected. Remaining domains: {remaining}. "
                f"Check dependencies for these domains."
            )
        
        # Sort ready domains alphabetically for consistent ordering
        ready.sort()
        
        # Add to ordered list and mark as processed
        ordered.extend(ready)
        processed.update(ready)
        remaining -= set(ready)
    
    return ordered


async def transform_all_domains(
    source_files: Dict[str, str],
    study_id: str,
    mapping_specs: Dict[str, dict],
    output_dir: str
) -> Dict[str, pd.DataFrame]:
    """
    Transform all domains in correct dependency order.
    
    Args:
        source_files: Dictionary mapping domain to source file path
        study_id: Study identifier
        mapping_specs: Dictionary of mapping specifications per domain
        output_dir: Output directory for transformed datasets
        
    Returns:
        Dictionary of transformed DataFrames by domain
    """
    results = {}
    errors = []
    
    # Get correct processing order
    processing_order = get_processing_order(list(source_files.keys()))
    logger.info(f"Processing order determined: {processing_order}")
    
    # Process domains sequentially (respecting dependencies)
    for domain in processing_order:
        try:
            logger.info(f"=" * 60)
            logger.info(f"Starting transformation: {domain}")
            
            file_path = source_files.get(domain)
            mapping_spec = mapping_specs.get(domain)
            
            if not file_path:
                logger.error(f"No source file specified for {domain}")
                errors.append((domain, "Missing source file"))
                continue
            
            if not mapping_spec:
                logger.error(f"No mapping specification for {domain}")
                errors.append((domain, "Missing mapping specification"))
                continue
            
            # Read source data
            logger.info(f"Reading source file: {file_path}")
            df = pd.read_csv(file_path)
            logger.info(f"Source records: {len(df)}")
            
            # Build reference data from already-processed domains
            reference_data = {}
            
            if "DM" in results:
                # Extract RFSTDTC mapping for study day calculations
                dm_df = results["DM"]
                reference_data["rfstdtc_map"] = dict(
                    zip(dm_df["USUBJID"], dm_df.get("RFSTDTC", pd.Series()))
                )
                logger.info(f"Reference data: RFSTDTC map with {len(reference_data['rfstdtc_map'])} subjects")
            
            if "SE" in results:
                # SE domain for EPOCH derivation
                reference_data["se_domain"] = results["SE"]
                logger.info(f"Reference data: SE domain with {len(results['SE'])} records")
            
            if "TU" in results and domain in ["TR", "RS"]:
                # Tumor data for oncology domains
                reference_data["tu_domain"] = results["TU"]
            
            # Execute transformation
            transformed = transform_to_sdtm(
                source_df=df,
                domain=domain,
                study_id=study_id,
                mapping_spec=mapping_spec,
                reference_data=reference_data
            )
            
            # Store result
            results[domain] = transformed
            
            # Save to file
            output_path = f"{output_dir}/{domain.lower()}.csv"
            transformed.to_csv(output_path, index=False)
            logger.info(f"Saved {domain}: {len(transformed)} records to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to transform {domain}: {str(e)}", exc_info=True)
            errors.append((domain, str(e)))
    
    # Summary
    logger.info("=" * 60)
    logger.info("TRANSFORMATION SUMMARY")
    logger.info(f"Successful: {len(results)} domains")
    logger.info(f"Failed: {len(errors)} domains")
    
    if errors:
        logger.warning("Errors encountered:")
        for domain, error in errors:
            logger.warning(f"  {domain}: {error}")
    
    return results


# Synchronous wrapper for non-async environments
def transform_domains_sync(
    source_files: Dict[str, str],
    study_id: str,
    mapping_specs: Dict[str, dict],
    output_dir: str
) -> Dict[str, pd.DataFrame]:
    """Synchronous wrapper for transform_all_domains."""
    return asyncio.run(
        transform_all_domains(source_files, study_id, mapping_specs, output_dir)
    )
```

### 6. Supplemental Qualifiers (SUPP--) Generation
```python
def create_suppqual(
    parent_domain: str,
    parent_df: pd.DataFrame,
    supp_data: List[dict],
    study_id: str
) -> pd.DataFrame:
    """
    Create Supplemental Qualifiers dataset (SUPP--).
    
    Args:
        parent_domain: Parent domain code (e.g., "AE", "LB")
        parent_df: Parent domain DataFrame (to get USUBJID and --SEQ)
        supp_data: List of supplemental qualifier definitions
            [
                {
                    "QNAM": "AESSION",
                    "QLABEL": "AE Leading to Study Discontinuation",
                    "QVAL_COL": "source_ae_discon_flag",  # Column in source
                    "QORIG": "CRF"
                }
            ]
        study_id: Study identifier
        
    Returns:
        pd.DataFrame: SUPP-- dataset
    """
    supp_records = []
    seq_var = f"{parent_domain}SEQ"
    
    for _, parent_row in parent_df.iterrows():
        for supp_def in supp_data:
            qnam = supp_def["QNAM"]
            qlabel = supp_def["QLABEL"]
            qorig = supp_def.get("QORIG", "CRF")
            
            # Get value from source column
            qval_col = supp_def.get("QVAL_COL")
            if qval_col and qval_col in parent_row.index:
                qval = parent_row[qval_col]
            else:
                qval = supp_def.get("QVAL", "")
            
            # Skip if no value
            if pd.isna(qval) or qval == "":
                continue
            
            supp_records.append({
                "STUDYID": study_id,
                "RDOMAIN": parent_domain,
                "USUBJID": parent_row["USUBJID"],
                "IDVAR": seq_var,
                "IDVARVAL": str(parent_row.get(seq_var, "")),
                "QNAM": qnam,
                "QLABEL": qlabel,
                "QVAL": str(qval),
                "QORIG": qorig,
                "QEVAL": supp_def.get("QEVAL", "")
            })
    
    supp_df = pd.DataFrame(supp_records)
    
    if not supp_df.empty:
        # Order columns per SDTMIG
        col_order = [
            "STUDYID", "RDOMAIN", "USUBJID", "IDVAR", "IDVARVAL",
            "QNAM", "QLABEL", "QVAL", "QORIG", "QEVAL"
        ]
        supp_df = supp_df[[c for c in col_order if c in supp_df.columns]]
        
        # Sort
        supp_df = supp_df.sort_values(
            ["STUDYID", "USUBJID", "IDVARVAL", "QNAM"]
        ).reset_index(drop=True)
    
    return supp_df
```

## Instructions for Agent

When the agent receives a programming task:

### CRITICAL: Mapping Specification Requirement

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

### Critical SDTM Programming Rules

1. **--SEQ Must Be Unique Within USUBJID**
```python
   # CORRECT
   df[f"{domain}SEQ"] = df.groupby("USUBJID").cumcount() + 1
   
   # WRONG - creates global sequence
   df[f"{domain}SEQ"] = range(1, len(df) + 1)
```

2. **No Day 0 in Study Day Calculations**
```python
   # CORRECT
   if diff >= 0:
       study_day = diff + 1  # Day 1, 2, 3...
   else:
       study_day = diff      # Day -1, -2, -3...
   
   # WRONG
   study_day = diff  # Creates Day 0
```

3. **--BLFL Is Only "Y" or Null, Never "N"**
```python
   # CORRECT
   df["VSBLFL"] = df.apply(lambda r: "Y" if is_baseline(r) else None, axis=1)
   
   # WRONG
   df["VSBLFL"] = df.apply(lambda r: "Y" if is_baseline(r) else "N", axis=1)
```

4. **--STAT Is Only "NOT DONE" or Null**
```python
   # CORRECT
   df["LBSTAT"] = df["LBORRES"].apply(lambda x: "NOT DONE" if pd.isna(x) else None)
   
   # WRONG
   df["LBSTAT"] = df["LBORRES"].apply(lambda x: "NOT DONE" if pd.isna(x) else "DONE")
```

5. **Process Domains in Dependency Order**
   - DM must be processed first (provides RFSTDTC for --DY calculations)
   - SE should be processed before findings domains (provides EPOCH)
   - Parent domains before SUPP-- domains
   - RELREC processed last

### Language Selection Guide

| Scenario | Recommended Language |
|----------|---------------------|
| Most SDTM transformations | Python (Pandas) |
| Large datasets (>1M rows) | Python (Polars) |
| Regulatory submission programs | SAS |
| Statistical analysis integration | R |
| Database extraction | SQL |
| Parallel processing | Python (asyncio) |

### Code Quality Requirements

1. **Include headers** with program purpose, author, date, SDTM IG version
2. **Add comments** for complex derivations and controlled terminology mappings
3. **Use meaningful variable names** that match SDTMIG
4. **Include error handling** for data quality issues
5. **Log transformations** for audit trail
6. **Validate outputs** against SDTM requirements

## Available Tools

- `analyze_source_file` - Profile source data structure and quality
- `generate_mapping_spec` - **REQUIRED FIRST** - Create mapping specification from source
- `save_mapping_spec` - Save mapping specification to file
- `transform_to_sdtm` - Apply transformation with mapping spec (requires mapping_spec parameter)
- `validate_sdtm_domain` - Validate transformed domain against SDTM rules
- `generate_sas_program` - Generate SAS transformation program
- `generate_r_script` - Generate R transformation script
- `create_suppqual` - Generate supplemental qualifier dataset
- `create_relrec` - Generate relationship dataset

---
name: datetime-handling
description: Use this skill for ISO 8601 date/time handling in SDTM. Covers DTC variable formatting, partial date representation, date imputation strategies, study day calculations, and common date conversion patterns. Essential for all SDTM domains as dates must comply with ISO 8601 standard.
---

# Date/Time Handling in SDTM - ISO 8601 Complete Guide

## Overview

**CRITICAL**: All date/time variables in SDTM must be in ISO 8601 format and stored as **character type**.

**Source**: CDISC SDTMIG v3.4, FDA Technical Conformance Guide, ISO 8601:2004 standard

## ISO 8601 Format Basics

### Complete Dates

| Format | Example | Precision |
|--------|---------|-----------|
| YYYY-MM-DD | 2024-01-15 | Complete date |
| YYYY-MM-DDTHH:MM | 2024-01-15T14:30 | Date + time (hour:min) |
| YYYY-MM-DDTHH:MM:SS | 2024-01-15T14:30:45 | Date + time (seconds) |

### Partial Dates

**Key Rule**: Whatever is unknown is **not included**.

| Format | Example | Meaning |
|--------|---------|---------|
| YYYY | 2024 | Year only known |
| YYYY-MM | 2024-01 | Year and month known |
| YYYY-MM-DD | 2024-01-15 | Complete date |

**Example**: If a patient reports "sometime in March 2024" → use "2024-03"

## DTC Variables in SDTM

All date/time collection variables end in **--DTC** (Date/Time of Collection).

### Common DTC Variables

| Variable | Domain | Description |
|----------|--------|-------------|
| BRTHDTC | DM | Date/Time of Birth |
| RFSTDTC | DM | Subject Reference Start Date/Time |
| RFENDTC | DM | Subject Reference End Date/Time |
| --DTC | All | Date/Time of Assessment/Collection |
| AESTDTC | AE | Start Date/Time of Adverse Event |
| AEENDTC | AE | End Date/Time of Adverse Event |
| CMSTDTC | CM | Start Date/Time of Medication |
| EXSTDTC | EX | Start Date/Time of Exposure |

**Important**: DTC variables are **always character type**, not SAS date or Python datetime.

## Converting to ISO 8601

### Python Conversion Functions

```python
import pandas as pd
from datetime import datetime
import re

def to_iso8601_date(date_value):
    """
    Convert various date formats to ISO 8601 (YYYY-MM-DD).

    Handles:
    - 01/15/2024 (MM/DD/YYYY)
    - 15-JAN-2024 (DD-MON-YYYY)
    - 20240115 (YYYYMMDD)
    - 2024-01-15 (already ISO)
    """
    if pd.isna(date_value) or date_value == '':
        return ''

    date_str = str(date_value).strip()

    # Already ISO 8601
    if re.match(r'^\d{4}-\d{2}-\d{2}', date_str):
        return date_str

    # Try common formats
    formats = [
        '%m/%d/%Y',      # 01/15/2024
        '%d/%m/%Y',      # 15/01/2024
        '%d-%b-%Y',      # 15-JAN-2024
        '%d-%B-%Y',      # 15-January-2024
        '%Y%m%d',        # 20240115
        '%m-%d-%Y',      # 01-15-2024
        '%Y/%m/%d',      # 2024/01/15
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue

    return ''  # Unable to parse

def to_iso8601_datetime(datetime_value):
    """Convert to ISO 8601 datetime (YYYY-MM-DDTHH:MM:SS)."""
    if pd.isna(datetime_value) or datetime_value == '':
        return ''

    try:
        if isinstance(datetime_value, str):
            dt = pd.to_datetime(datetime_value)
        else:
            dt = datetime_value

        return dt.strftime('%Y-%m-%dT%H:%M:%S')
    except:
        return ''
```

### SAS Conversion

```sas
/* Convert SAS date to ISO 8601 */
data sdtm;
    set source;

    /* Complete date */
    if not missing(BIRTH_DATE) then
        BRTHDTC = put(BIRTH_DATE, IS8601DA.);

    /* Date with time */
    if not missing(EVENT_DATETIME) then
        AESTDTC = put(EVENT_DATETIME, IS8601DT.);

    /* Partial date handling */
    if missing(DAY) and not missing(MONTH) and not missing(YEAR) then
        AESTDTC = catx('-', put(YEAR, 4.), put(MONTH, Z2.));
run;
```

### R Conversion

```r
library(lubridate)

# Convert to ISO 8601
to_iso8601 <- function(date_value) {
  if (is.na(date_value)) return("")

  # Parse and format
  date_obj <- ymd(date_value)  # or mdy(), dmy() depending on source
  format(date_obj, "%Y-%m-%d")
}

# Example
df$BRTHDTC <- sapply(df$BIRTH_DATE, to_iso8601)
```

## Handling Partial Dates

### Creating Partial Dates

```python
def create_partial_date(year, month=None, day=None):
    """
    Create ISO 8601 partial date from components.

    Examples:
        create_partial_date(2024) → "2024"
        create_partial_date(2024, 3) → "2024-03"
        create_partial_date(2024, 3, 15) → "2024-03-15"
    """
    if year is None or pd.isna(year):
        return ''

    parts = [str(int(year)).zfill(4)]

    if month is not None and not pd.isna(month):
        parts.append(str(int(month)).zfill(2))

        if day is not None and not pd.isna(day):
            parts.append(str(int(day)).zfill(2))

    return '-'.join(parts)
```

### Imputation of Partial Dates

**FDA Guidance**: Document your imputation rules clearly in the ADRG (Analysis Data Reviewer's Guide).

**Common Imputation Strategies**:

| Missing Component | Conservative | Liberal | Neutral |
|-------------------|--------------|---------|---------|
| Day (Month known) | First of month | Last of month | 15th of month |
| Month (Year known) | January (01) | December (12) | July (07) |
| Full date | Conservative baseline | Liberal baseline | Mid-year estimate |

```python
def impute_partial_date(partial_dtc, strategy='conservative'):
    """
    Impute partial date for calculations.

    Args:
        partial_dtc: ISO 8601 partial date (e.g., "2024-03")
        strategy: 'conservative', 'liberal', or 'neutral'

    Returns:
        Complete ISO 8601 date
    """
    if not partial_dtc or pd.isna(partial_dtc):
        return ''

    parts = partial_dtc.split('-')

    if len(parts) == 1:  # Year only
        year = parts[0]
        if strategy == 'conservative':
            return f"{year}-01-01"
        elif strategy == 'liberal':
            return f"{year}-12-31"
        else:  # neutral
            return f"{year}-07-01"

    elif len(parts) == 2:  # Year-Month
        year, month = parts
        if strategy == 'conservative':
            return f"{year}-{month}-01"
        elif strategy == 'liberal':
            # Last day of month
            import calendar
            last_day = calendar.monthrange(int(year), int(month))[1]
            return f"{year}-{month}-{last_day:02d}"
        else:  # neutral
            return f"{year}-{month}-15"

    else:  # Complete date
        return partial_dtc
```

**IMPORTANT**: Create imputation flag variables in ADaM (not SDTM):
```python
# In ADaM
adam_df["BRTHDTF"] = "D"  # Day imputed
adam_df["ASTDTF"] = "M"  # Month imputed
```

## Study Day Calculations (--DY)

**CDISC Rule**: Study day is calculated from --DTC and RFSTDTC (reference start date).

**Key Rules**:
1. Day of RFSTDTC = **1** (not 0)
2. Days before RFSTDTC are **negative**
3. **No Day 0** exists

### Study Day Formula

```python
def calculate_study_day(dtc, rfstdtc):
    """
    Calculate SDTM study day (--DY).

    Rules:
    - Day of RFSTDTC = 1
    - Before RFSTDTC = negative
    - NO DAY 0

    Examples:
        RFSTDTC = 2024-01-15
        2024-01-14 → -1
        2024-01-15 → 1
        2024-01-16 → 2
    """
    if pd.isna(dtc) or pd.isna(rfstdtc):
        return pd.NA

    dtc_date = pd.to_datetime(dtc)
    rf_date = pd.to_datetime(rfstdtc)

    diff_days = (dtc_date - rf_date).days

    # Apply "no day 0" rule
    if diff_days >= 0:
        study_day = diff_days + 1
    else:
        study_day = diff_days

    return study_day

# Vectorized version
def add_study_days(df, dtc_col, rfstdtc_col, dy_col):
    """Add study day column to DataFrame."""
    dtc = pd.to_datetime(df[dtc_col])
    rf = pd.to_datetime(df[rfstdtc_col])

    diff = (dtc - rf).dt.days

    # No day 0 rule
    df[dy_col] = diff.where(diff < 0, diff + 1).astype('Int64')

    return df
```

### SAS Study Day Calculation

```sas
/* Calculate study day */
data with_study_day;
    set sdtm;

    if not missing(AESTDTC) and not missing(RFSTDTC) then do;
        /* Convert to SAS dates */
        AE_DATE = input(substr(AESTDTC, 1, 10), IS8601DA.);
        RF_DATE = input(substr(RFSTDTC, 1, 10), IS8601DA.);

        /* Calculate difference */
        DIFF_DAYS = AE_DATE - RF_DATE;

        /* Apply "no day 0" rule */
        if DIFF_DAYS >= 0 then AEDY = DIFF_DAYS + 1;
        else AEDY = DIFF_DAYS;
    end;
run;
```

## ISO 8601 Durations

Used in TE.TEDUR, --ELTM (elapsed time), and other duration fields.

### Duration Format

**Format**: `P[n]Y[n]M[n]DT[n]H[n]M[n]S`

- P = Period (required)
- [n]Y = Years
- [n]M = Months
- [n]D = Days
- T = Time separator (required before time components)
- [n]H = Hours
- [n]M = Minutes
- [n]S = Seconds

### Examples

| Duration | ISO 8601 | Meaning |
|----------|----------|---------|
| 7 days | P7D | 7 days |
| 4 weeks | P4W | 4 weeks |
| 12 weeks | P12W | 12 weeks |
| 3 months | P3M | 3 months |
| 1 year | P1Y | 1 year |
| 2 hours | PT2H | 2 hours |
| 30 minutes | PT30M | 30 minutes |
| 1 day 6 hours | P1DT6H | 1 day and 6 hours |

```python
def create_duration(days=0, weeks=0, months=0, years=0, hours=0, minutes=0):
    """Create ISO 8601 duration string."""
    duration = "P"

    if years:
        duration += f"{years}Y"
    if months:
        duration += f"{months}M"
    if weeks:
        duration += f"{weeks}W"
    if days:
        duration += f"{days}D"

    if hours or minutes:
        duration += "T"
        if hours:
            duration += f"{hours}H"
        if minutes:
            duration += f"{minutes}M"

    return duration if len(duration) > 1 else "P0D"

# Examples
create_duration(days=7) # "P7D"
create_duration(weeks=12) # "P12W"
create_duration(hours=2, minutes=30) # "PT2H30M"
```

## Common Date Validation Rules

| Rule | Check | Solution |
|------|-------|----------|
| SD1025 | --DTC is valid ISO 8601 | Use YYYY-MM-DD format |
| SD1046 | --STDTC <= --ENDTC | Validate date logic |
| SD1196 | --DY calculated correctly | Use study day formula |
| SD2092 | AGE matches BRTHDTC and RFSTDTC | Verify age calculation |

## Common Mistakes and Solutions

### Mistake 1: Using SAS/Python Date Types

**Wrong**:
```python
dm_df["BRTHDTC"] = pd.to_datetime(source["BIRTH_DATE"])  # Creates datetime object
```

**Correct**:
```python
dm_df["BRTHDTC"] = source["BIRTH_DATE"].apply(to_iso8601_date)  # Creates string
```

### Mistake 2: Including Unknown Components in Partial Dates

**Wrong**: `"2024-UN-UN"` or `"2024-99-99"`

**Correct**: `"2024"` (omit unknown parts)

### Mistake 3: Incorrect Study Day 0

**Wrong**:
```python
study_day = (dtc_date - rf_date).days  # Allows day 0
```

**Correct**:
```python
diff = (dtc_date - rf_date).days
study_day = diff + 1 if diff >= 0 else diff  # No day 0
```

### Mistake 4: Not Documenting Imputation

**Wrong**: Imputing dates without documentation

**Correct**: Document in ADRG:
```
"Partial dates were imputed conservatively using first day of month/year
for missing day/month components. Imputation flags are provided in ADaM."
```

## Best Practices

1. **Always Validate ISO 8601**: Use regex or parsing to verify format
2. **Document Imputation**: Clearly explain how partial dates were handled
3. **Use Flags in ADaM**: Mark imputed components (not in SDTM)
4. **Consistent Precision**: Use same precision within a domain/variable
5. **Test Edge Cases**: Leap years, month-end, time zones
6. **Character Type**: Never use date/datetime types for DTC variables
7. **Partial Dates**: Only include known components

## Instructions for Agent

When handling dates in SDTM:

1. **Convert to ISO 8601**: Use to_iso8601_date/datetime functions
2. **Character Type**: Always store as character/string
3. **Partial Dates**: Omit unknown components, document approach
4. **Study Day**: Calculate using formula (no day 0)
5. **Durations**: Use P#D, P#W format for ISO 8601 durations
6. **Validate**: Check ISO 8601 compliance before submission
7. **Imputation**: Only in ADaM, never in SDTM (except for calculations)

## Available Tools

- `to_iso8601_date` - Convert date to ISO 8601
- `to_iso8601_datetime` - Convert datetime to ISO 8601
- `create_partial_date` - Build partial date from components
- `calculate_study_day` - Calculate --DY from --DTC
- `validate_iso8601` - Check ISO 8601 compliance

# MAXIS-08 Raw Data Validation Guide

## Overview

This document provides comprehensive guidance on validating raw source data files before SDTM transformation. Raw data validation is a critical first step that ensures data quality and identifies issues that would block transformation.

## Table of Contents

1. [Purpose](#purpose)
2. [Validation Scope](#validation-scope)
3. [Prerequisites](#prerequisites)
4. [Quick Start](#quick-start)
5. [Validation Checks](#validation-checks)
6. [Understanding Results](#understanding-results)
7. [Quality Scoring](#quality-scoring)
8. [Common Issues](#common-issues)
9. [Recommendations](#recommendations)

---

## Purpose

Raw data validation serves multiple objectives:

- **Early Detection**: Identify data quality issues before investing time in SDTM transformation
- **Blocking Issues**: Flag critical errors that would prevent successful transformation
- **Data Profiling**: Understand the structure and content of source data
- **Quality Assurance**: Establish baseline quality metrics for source data
- **Compliance**: Ensure source data meets minimum standards for regulatory submissions

### When to Validate

✅ **Always validate before**:
- Beginning SDTM transformation
- Loading data into production pipeline
- Submitting data to sponsors or regulatory agencies

⚠️ **Re-validate after**:
- Receiving updated source data files
- Making corrections to source data
- Database lock changes

---

## Validation Scope

### Files Validated

The validation covers all 11 source files for Study MAXIS-08:

| File Name | Target Domain | Expected Records | Expected Columns |
|-----------|---------------|------------------|------------------|
| DEMO.csv | DM (Demographics) | 16 | 12 |
| AEVENT.csv | AE (Adverse Events) | 550 | 38 |
| AEVENTC.csv | AE (Adverse Events) | 276 | 36 |
| CONMEDS.csv | CM (Concomitant Meds) | 302 | 38 |
| CONMEDSC.csv | CM (Concomitant Meds) | 302 | 34 |
| VITALS.csv | VS (Vital Signs) | 536 | 21 |
| HEMLAB.csv | LB (Laboratory) | 1,726 | 14 |
| CHEMLAB.csv | LB (Laboratory) | 3,326 | 13 |
| DOSE.csv | EX (Exposure) | 271 | 21 |
| ECG.csv | EG (ECG) | 60 | 11 |
| PHYSEXAM.csv | PE (Physical Exam) | 2,169 | 14 |

**Total Expected**: 9,534 records across 11 files

---

## Prerequisites

### System Requirements

- **Python**: 3.8 or higher
- **Packages**: pandas, numpy
- **Storage**: ~50MB for validation results
- **Memory**: 2GB RAM minimum

### Data Requirements

Source data must be:
- CSV format with UTF-8 encoding
- Located in accessible directory
- Named exactly as shown in table above (case-sensitive on Linux/Mac)

### Installation

```bash
# Install required packages
pip install pandas numpy

# Make validation script executable
chmod +x /path/to/raw_data_validation.py
chmod +x /path/to/run_raw_data_validation.sh
```

---

## Quick Start

### Method 1: Shell Script (Recommended)

```bash
# Set data path (if not default location)
export DATA_PATH="/tmp/s3_data/extracted/Maxis-08 RAW DATA_CSV"

# Run validation
cd /Users/siddharthchauhan/Work/Projects/ETL/sdtm_pipeline
./run_raw_data_validation.sh
```

### Method 2: Python Script Directly

```bash
python3 raw_data_validation.py \
    --data-path "/tmp/s3_data/extracted/Maxis-08 RAW DATA_CSV" \
    --study-id "MAXIS-08" \
    --output "MAXIS-08_RAW_DATA_VALIDATION_REPORT.md" \
    --json-output "validation_results.json"
```

### Method 3: Python Import

```python
from pathlib import Path
from raw_data_validation import RawDataValidator

# Initialize validator
validator = RawDataValidator(
    data_path="/tmp/s3_data/extracted/Maxis-08 RAW DATA_CSV",
    study_id="MAXIS-08"
)

# Run validation
results = validator.validate_all_files()

# Generate report
report = validator.generate_report(
    results, 
    output_path="validation_report.md"
)

# Access results programmatically
print(f"Quality Score: {results['overall_quality_score']}")
print(f"Critical Errors: {results['total_errors']}")
print(f"Warnings: {results['total_warnings']}")
```

---

## Validation Checks

### 1. Required Identifiers (RDV-001 to RDV-006)

**Purpose**: Ensure every record can be linked to study, site, and subject.

**Checks**:
- ✅ Required fields present: `STUDY`, `INVSITE`, `PT`
- ✅ No missing values in identifier fields
- ✅ No empty strings in identifier fields
- ✅ STUDY value matches expected study ID
- ✅ Consistent STUDY values across all records

**Critical Errors**:
- Missing identifier column
- Null/empty identifier values

**Example Issues**:
```
RDV-001: Missing required identifier field 'INVSITE'
RDV-002: Identifier field 'PT' has 3 missing values (1.8%)
RDV-003: Identifier field 'STUDY' has 5 empty values (3.1%)
```

**Fix Recommendations**:
- Ensure all identifier columns are present in source data
- Query EDC system to fill missing subject IDs
- Use study-specific value for STUDY field (e.g., "MAXIS-08")

---

### 2. Date Format Validation (RDV-010 to RDV-013)

**Purpose**: Ensure dates are in recognizable, consistent formats.

**Checks**:
- ✅ Date fields identified by pattern matching
- ✅ Valid date formats detected
- ✅ Start dates before end dates
- ✅ Reasonable date ranges

**Supported Formats**:
- ISO 8601: `YYYY-MM-DD` (preferred)
- Slash format: `YYYY/MM/DD` or `MM/DD/YYYY`
- SAS format: `DD-MON-YYYY`
- Compact: `YYYYMMDD`
- Partial: `YYYY-MM` or `YYYY`

**Warning Conditions**:
- >50% missing dates in a date field
- Invalid date format
- End date before start date

**Example Issues**:
```
RDV-010: Date field 'AESTDAT' has 125 missing values (22.7%)
RDV-011: Invalid date format in 'BRTHDAT' at row 45: '12/32/1975'
RDV-013: 3 records have end date before start date (AESTDAT > AEENDAT)
```

**Fix Recommendations**:
- Standardize all dates to ISO 8601: `YYYY-MM-DD`
- Use partial dates for incomplete data: `2023-01` or `2023`
- Leave missing dates as empty/null (do not use placeholder values)
- Verify date logic (start before end)

---

### 3. Duplicate Record Detection (RDV-020 to RDV-022)

**Purpose**: Identify duplicate records that could cause issues in SDTM.

**Checks**:
- ✅ Completely duplicate rows
- ✅ Duplicates on key identifier combinations
- ✅ Duplicate subjects in Demographics (DM)

**Critical Errors**:
- Completely duplicate rows
- Duplicate subject IDs in DM domain

**Warning Conditions**:
- Duplicate key combinations (may be valid for events)

**Example Issues**:
```
RDV-020: 15 completely duplicate rows found (2.7%)
RDV-021: 8 duplicate records on key fields ['STUDY', 'INVSITE', 'PT', 'AESEQ']
RDV-022: 2 duplicate subject IDs (PT) in Demographics domain
```

**Fix Recommendations**:
- Remove completely duplicate rows (keep one copy)
- For DM domain: Investigate and resolve duplicate subjects
- For event domains: Ensure sequence numbers (AESEQ, CMSEQ, etc.) differentiate records
- Document if duplicates are intentional (e.g., multiple dosing events)

---

### 4. Missing Critical Data (RDV-030 to RDV-033)

**Purpose**: Identify missing data in fields critical for SDTM transformation.

**Critical Fields by Domain**:

| Domain | Critical Fields |
|--------|----------------|
| DM | PT, BRTHDAT, SEX, RACE |
| AE | PT, AETERM, AESTDAT |
| CM | PT, CMTRT, CMSTDAT |
| VS | PT, VSTESTCD, VSORRES, VSDAT |
| LB | PT, LBTESTCD, LBORRES, LBDAT |
| EX | PT, EXTRT, EXSTDAT, EXDOSE |
| EG | PT, EGTESTCD, EGORRES |
| PE | PT, PETESTCD, PEORRES |

**Warning Conditions**:
- >10% missing in critical field
- Expected field not present
- >20% overall missing data rate

**Example Issues**:
```
RDV-030: Expected critical field 'AETERM' not found in AE data
RDV-031: Critical field 'VSORRES' has 45 missing values (8.4%)
RDV-033: High overall missing data rate: 23.5% (1,250 / 5,320 cells)
```

**Fix Recommendations**:
- Query EDC system for missing critical data
- Document reasons for missing data (e.g., "not done", "not applicable")
- Consider if missing fields should be in different source table
- Acceptable missing rates vary by field type

---

### 5. Data Quality Checks (RDV-040 to RDV-043)

**Purpose**: Identify data quality issues that may indicate problems.

**Checks**:
- ✅ Columns with all null values
- ✅ Columns with no variance (single value)
- ✅ Control characters in text fields
- ✅ Statistical outliers in numeric fields

**Warning Conditions**:
- Columns that are completely empty
- Unexpected control characters
- Extreme outliers (>3 IQR from quartiles)

**Example Issues**:
```
RDV-040: 3 columns have all missing values: COMMENT, NOTES, SPARE1
RDV-041: Column 'STUDY' has only one unique value: 'MAXIS-08'
RDV-042: Column 'AETERM' contains control characters in 2 records
RDV-043: Column 'WEIGHT' has 4 potential outliers (2.5%)
```

**Fix Recommendations**:
- Remove completely empty columns or document purpose
- Verify single-value columns are correct (e.g., STUDY should be constant)
- Clean control characters from text fields
- Review outliers for data entry errors

---

## Understanding Results

### Report Structure

The validation report contains these sections:

1. **Executive Summary**
   - Overall quality score (0-100)
   - Total critical errors and warnings
   - Transformation readiness status

2. **Per-File Summary Table**
   - Quick overview of all files
   - Record counts, status, scores

3. **Detailed Results by File**
   - Full list of issues per file
   - Specific error messages with row numbers

4. **Recommendations**
   - Prioritized action items
   - Data cleaning guidance

### Status Indicators

| Status | Meaning | Action Required |
|--------|---------|-----------------|
| ✅ PASS | No critical errors, <5 warnings | Review warnings, proceed with caution |
| ⚠️ REVIEW | No critical errors, 5+ warnings | Address warnings before transformation |
| ❌ FAIL | 1+ critical errors | Must fix before transformation |
| 🔴 MISSING | File not found | Load file from source system |
| ⚠️ ERROR | Exception during validation | Check file format and encoding |

### Console Output

During validation, you'll see real-time progress:

```
================================================================================
RAW DATA VALIDATION - Study MAXIS-08
================================================================================
Data Path: /tmp/s3_data/extracted/Maxis-08 RAW DATA_CSV
Files to Validate: 11
Timestamp: 2025-02-02 14:30:15

────────────────────────────────────────────────────────────────────────────────
Validating: DEMO.csv → DM domain
────────────────────────────────────────────────────────────────────────────────

📊 Summary Statistics:
   Records: 16 (expected: 16, variance: 0 / +0.0%)
   Columns: 12 (expected: 12, variance: 0)
   Missing Cells: 8 (4.2%)
   Duplicate Rows: 0

🎯 Validation Results:
   Status: PASS
   Quality Score: 94.0/100
   Critical Errors: 0
   Warnings: 3
   Info Messages: 2

⚠️  Warnings (3):
   • RDV-010: Date field 'BRTHDAT' has 2 missing values (12.5%)
   • RDV-031: Critical field 'RACE' has 1 missing value (6.2%)
   • RDV-041: Column 'STUDY' has only one unique value: 'MAXIS-08'
```

---

## Quality Scoring

### Scoring Algorithm

Quality score starts at 100 and deductions are made:

| Issue Type | Deduction | Max Deduction |
|------------|-----------|---------------|
| Critical Error | -10 points each | No limit |
| Warning | -2 points each | No limit |
| Missing Data (>20%) | -20 points | -20 points |
| Missing Data (10-20%) | -10 points | -10 points |
| Missing Data (5-10%) | -5 points | -5 points |
| Duplicates (>5%) | -10 points | -10 points |
| Duplicates (1-5%) | -5 points | -5 points |

**Minimum Score**: 0  
**Maximum Score**: 100

### Score Interpretation

| Score Range | Quality Level | Recommendation |
|-------------|---------------|----------------|
| 95-100 | Excellent | Proceed with transformation |
| 85-94 | Good | Review warnings, then proceed |
| 70-84 | Acceptable | Address major warnings first |
| 50-69 | Poor | Significant cleanup required |
| 0-49 | Very Poor | Extensive data quality issues |

### Example Calculations

**Example 1: High Quality Data**
- Base: 100 points
- 0 critical errors: -0
- 3 warnings: -6
- 4.2% missing data: 0 (below threshold)
- 0 duplicates: -0
- **Final Score: 94/100** ✅

**Example 2: Moderate Issues**
- Base: 100 points
- 2 critical errors: -20
- 8 warnings: -16
- 12% missing data: -10
- 2% duplicates: -5
- **Final Score: 49/100** ⚠️

**Example 3: Poor Quality**
- Base: 100 points
- 5 critical errors: -50
- 15 warnings: -30
- 25% missing data: -20
- 8% duplicates: -10
- **Final Score: 0/100** ❌ (capped at 0)

---

## Common Issues

### Issue 1: File Not Found

**Error Message**:
```
❌ ERROR: File not found at /tmp/s3_data/extracted/Maxis-08 RAW DATA_CSV/DEMO.csv
```

**Causes**:
- Data not loaded from S3
- Wrong data path specified
- Incorrect file name (case sensitivity)

**Solutions**:
1. Load data from S3:
   ```bash
   aws s3 cp s3://s3dcri/Clinical_Studies/MAXIS-08/RAW_DATA/Maxis-08\ RAW\ DATA.zip /tmp/
   unzip /tmp/Maxis-08\ RAW\ DATA.zip -d /tmp/s3_data/extracted/
   ```

2. Verify file path:
   ```bash
   ls -la /tmp/s3_data/extracted/Maxis-08\ RAW\ DATA_CSV/
   ```

3. Update data path:
   ```bash
   export DATA_PATH="/correct/path/to/data"
   ./run_raw_data_validation.sh
   ```

---

### Issue 2: Missing Required Identifiers

**Error Message**:
```
RDV-001: Missing required identifier field 'INVSITE'
RDV-002: Identifier field 'PT' has 15 missing values (2.7%)
```

**Causes**:
- Column not exported from EDC system
- Column renamed during export
- Incomplete data extraction

**Solutions**:
1. Check source EDC system:
   - Verify field is present in case report form (CRF)
   - Ensure export includes all identifier fields
   - Re-export data if necessary

2. Map renamed columns:
   - If column has different name (e.g., "SITE_ID" instead of "INVSITE")
   - Rename column in source CSV before validation
   - Update mapping specification

3. Query for missing values:
   - Identify which subjects have missing identifiers
   - Query EDC database to fill gaps
   - Document if truly missing (e.g., screen failures)

---

### Issue 3: Invalid Date Formats

**Warning Message**:
```
RDV-011: Invalid date format in 'AESTDAT' at row 45: '2023/13/01'
RDV-013: 5 records have end date before start date
```

**Causes**:
- Inconsistent date formats in source system
- Manual data entry errors
- Excel date conversion issues

**Solutions**:
1. Standardize to ISO 8601 format:
   ```python
   import pandas as pd
   
   # Load data
   df = pd.read_csv('AEVENT.csv')
   
   # Convert dates to ISO 8601
   df['AESTDAT'] = pd.to_datetime(df['AESTDAT'], errors='coerce').dt.strftime('%Y-%m-%d')
   df['AEENDAT'] = pd.to_datetime(df['AEENDAT'], errors='coerce').dt.strftime('%Y-%m-%d')
   
   # Save corrected data
   df.to_csv('AEVENT_corrected.csv', index=False)
   ```

2. Fix date logic errors:
   ```python
   # Find records where end < start
   invalid_dates = df[df['AEENDAT'] < df['AESTDAT']]
   
   # Investigate and correct
   print(invalid_dates[['PT', 'AETERM', 'AESTDAT', 'AEENDAT']])
   ```

3. Use partial dates for incomplete data:
   - Unknown day: `2023-05` (year-month only)
   - Unknown month: `2023` (year only)
   - Completely unknown: leave blank

---

### Issue 4: Duplicate Records

**Error Message**:
```
RDV-020: 25 completely duplicate rows found (4.5%)
RDV-022: 2 duplicate subject IDs (PT) in Demographics domain
```

**Causes**:
- Duplicate data exports
- Multiple CRF submissions for same event
- Data entry errors

**Solutions**:
1. Remove exact duplicates:
   ```python
   import pandas as pd
   
   df = pd.read_csv('AEVENT.csv')
   
   # Show duplicates
   duplicates = df[df.duplicated(keep=False)]
   print(f"Found {len(duplicates)} duplicate rows")
   
   # Remove duplicates (keep first occurrence)
   df_clean = df.drop_duplicates(keep='first')
   
   # Save
   df_clean.to_csv('AEVENT_deduped.csv', index=False)
   ```

2. For Demographics duplicates:
   ```python
   # Find duplicate subjects
   dup_subjects = df[df.duplicated(subset=['PT'], keep=False)]
   print(dup_subjects.sort_values('PT'))
   
   # Investigate - should only be 1 row per subject
   # Determine which record is correct, remove others
   ```

3. Document legitimate duplicates:
   - If same subject had multiple events (AE, CM, VS, etc.) - this is expected
   - Ensure sequence numbers differentiate records
   - Should NOT have duplicates in DM (Demographics)

---

### Issue 5: High Missing Data Rate

**Warning Message**:
```
RDV-031: Critical field 'VSORRES' has 125 missing values (23.3%)
RDV-033: High overall missing data rate: 28.5%
```

**Causes**:
- Fields not applicable for all visits/subjects
- Data collection issues
- Optional fields in CRF

**Solutions**:
1. Determine if missing data is expected:
   - Visit not conducted (e.g., early termination)
   - Test not performed (e.g., pregnancy test for males)
   - Field not applicable (e.g., stop date for ongoing events)

2. Document missing data patterns:
   ```python
   # Analyze missing data by visit
   missing_by_visit = df.groupby('VISIT')['VSORRES'].apply(
       lambda x: x.isnull().sum() / len(x) * 100
   )
   print(missing_by_visit)
   ```

3. Query for recoverable data:
   - Check if data exists in EDC but wasn't exported
   - Verify with clinical operations team
   - Re-export if necessary

4. Use SDTM conventions for missing data:
   - Leave as null/empty (most common)
   - Will be handled during SDTM transformation
   - Do not use placeholder values like "N/A", "Unknown", "9999"

---

## Recommendations

### Pre-Validation Checklist

Before running validation, ensure:

- [ ] All source files downloaded from EDC system
- [ ] Files are in CSV format with UTF-8 encoding
- [ ] File names match expected naming convention
- [ ] Data has been extracted from latest database lock
- [ ] Any known data corrections have been applied
- [ ] Backup copies of original files exist

### Data Cleaning Priority

Address issues in this order:

**Priority 1 - Blockers (Must Fix)**:
1. Missing source files
2. Missing required identifier fields (STUDY, INVSITE, PT)
3. Null/empty values in identifier fields
4. Completely duplicate rows
5. Duplicate subjects in Demographics (DM)

**Priority 2 - Critical (Should Fix)**:
1. Invalid date formats
2. End dates before start dates
3. Missing critical data fields (e.g., AETERM, CMTRT)
4. >50% missing data in required fields
5. Control characters in text fields

**Priority 3 - Quality (Nice to Fix)**:
1. Inconsistent date formats
2. 10-50% missing data in important fields
3. Statistical outliers
4. Columns with no variance
5. Empty columns

### Best Practices

#### Data Standardization

1. **Dates**: Always use ISO 8601 (YYYY-MM-DD)
2. **Missing Data**: Leave as null/empty, never use placeholders
3. **Text**: Remove leading/trailing whitespace
4. **Encoding**: Use UTF-8 for all CSV files
5. **Delimiters**: Use comma (,) as field delimiter

#### Before Transformation

✅ **Requirements for SDTM transformation**:
- 0 critical errors in validation
- Overall quality score ≥ 85
- All required identifiers present and complete
- Date formats standardized
- Duplicate records resolved
- Critical missing data addressed

⚠️ **Warning signs to investigate**:
- Quality score < 85
- >10% missing data in critical fields
- Inconsistent identifier values
- Outliers or unusual values
- Completely empty columns

#### Documentation

Maintain documentation for:
- Source of each data file
- Known data quality issues
- Corrections applied to source data
- Reasons for missing data
- Decisions about duplicate records
- Communication with clinical operations team

### Post-Validation Actions

After successful validation:

1. **Review Report**: Read full validation report carefully
2. **Document Issues**: Log all issues in data management system
3. **Create Action Plan**: Prioritize and assign data cleaning tasks
4. **Fix and Re-validate**: After corrections, run validation again
5. **Archive Results**: Save validation report with date/version
6. **Proceed to Mapping**: Begin SDTM mapping specification (Phase 3)

---

## Support and Troubleshooting

### Getting Help

If you encounter issues not covered in this guide:

1. **Check Logs**: Review execution log file for detailed error messages
2. **Verify Environment**: Ensure Python packages are correctly installed
3. **Test with Sample**: Try validation on small sample file first
4. **Review Code**: Check validation script for specific error handling

### Contact Information

For questions about:
- **Validation script**: Contact SDTM Pipeline team
- **Source data issues**: Contact Clinical Data Management
- **SDTM requirements**: Contact CDISC standards team
- **Study-specific questions**: Contact Study Data Manager

### Useful Resources

- **CDISC SDTM**: https://www.cdisc.org/standards/foundational/sdtm
- **SDTM-IG 3.4**: https://www.cdisc.org/standards/foundational/sdtmig/sdtmig-v3-4
- **ISO 8601 Dates**: https://www.iso.org/iso-8601-date-and-time-format.html
- **Data Quality**: FDA Data Quality Guidelines

---

## Appendix: Error Code Reference

### RDV-001 to RDV-006: Identifier Issues
- **RDV-001**: Missing required identifier field
- **RDV-002**: Null values in identifier field
- **RDV-003**: Empty string values in identifier field
- **RDV-004**: STUDY field has no valid values
- **RDV-005**: Multiple STUDY values found
- **RDV-006**: STUDY value doesn't match expected

### RDV-010 to RDV-013: Date Issues
- **RDV-010**: High missing date rate
- **RDV-011**: Invalid date format
- **RDV-012**: Multiple invalid dates in field
- **RDV-013**: End date before start date

### RDV-020 to RDV-022: Duplicate Issues
- **RDV-020**: Completely duplicate rows
- **RDV-021**: Duplicates on key fields
- **RDV-022**: Duplicate subject IDs in DM

### RDV-030 to RDV-033: Missing Data Issues
- **RDV-030**: Expected critical field not found
- **RDV-031**: High missing rate in critical field
- **RDV-032**: Some missing values in field
- **RDV-033**: High overall missing data rate

### RDV-040 to RDV-043: Data Quality Issues
- **RDV-040**: Columns with all null values
- **RDV-041**: Column with no variance
- **RDV-042**: Control characters detected
- **RDV-043**: Potential outliers detected

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-02-02 | Validation Agent | Initial release |

---

**Document End**

For latest version of this guide, check: `/Users/siddharthchauhan/Work/Projects/ETL/sdtm_pipeline/RAW_DATA_VALIDATION_GUIDE.md`

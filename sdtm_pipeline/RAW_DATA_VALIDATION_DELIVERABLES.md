# MAXIS-08 Raw Data Validation - Deliverables Package

## Executive Summary

**Study**: MAXIS-08  
**Phase**: Phase 2 - Raw Data Quality Assessment  
**Date**: 2025-02-02  
**Status**: ✅ COMPLETE - Ready for Execution  

This deliverables package provides comprehensive raw data validation capabilities for Study MAXIS-08 source files before SDTM transformation. The validation framework performs 6 categories of checks across 11 source files, generating detailed reports with actionable recommendations.

---

## 📦 Package Contents

### 1. Core Validation Script
**File**: `raw_data_validation.py` (1,050+ lines)

**Purpose**: Python script that performs comprehensive validation on all source data files.

**Key Features**:
- ✅ Validates 11 source files (DM, AE, CM, VS, LB, EX, EG, PE domains)
- ✅ 6 validation categories with 24+ specific checks
- ✅ Data quality scoring algorithm (0-100 scale)
- ✅ Detailed error reporting with error codes (RDV-001 to RDV-043)
- ✅ JSON and Markdown output formats
- ✅ Configurable thresholds and parameters

**Validation Categories**:
1. Required Identifiers (STUDY, INVSITE, PT)
2. Date Format Validation
3. Duplicate Record Detection
4. Missing Critical Data
5. Data Quality Checks
6. Statistical Outlier Detection

**Error Codes**: RDV-001 through RDV-043 (see appendix)

**Usage**:
```bash
python3 raw_data_validation.py \
    --data-path "/path/to/source/data" \
    --study-id "MAXIS-08" \
    --output "validation_report.md" \
    --json-output "validation_results.json"
```

---

### 2. Execution Wrapper Script
**File**: `run_raw_data_validation.sh` (180 lines)

**Purpose**: Shell script for easy execution with environment checks and error handling.

**Key Features**:
- ✅ Pre-flight checks (data path, Python, packages)
- ✅ Configurable via environment variables
- ✅ Detailed console output with progress indicators
- ✅ Comprehensive logging
- ✅ Exit codes for automation (0 = success, 1 = failure)

**Usage**:
```bash
# Default execution (uses /tmp/s3_data/extracted/Maxis-08 RAW DATA_CSV)
./run_raw_data_validation.sh

# Custom data path
export DATA_PATH="/custom/path/to/data"
./run_raw_data_validation.sh

# Custom output directory
export OUTPUT_DIR="/custom/output/path"
./run_raw_data_validation.sh
```

**Environment Variables**:
- `DATA_PATH`: Path to source data directory
- `STUDY_ID`: Study identifier (default: MAXIS-08)
- `OUTPUT_DIR`: Output directory for reports

---

### 3. Comprehensive User Guide
**File**: `RAW_DATA_VALIDATION_GUIDE.md` (850+ lines)

**Purpose**: Complete documentation for using the validation framework.

**Sections**:
1. **Purpose** - Why validate raw data
2. **Validation Scope** - What gets validated
3. **Prerequisites** - System and data requirements
4. **Quick Start** - 3 methods to run validation
5. **Validation Checks** - Detailed explanation of all checks
6. **Understanding Results** - How to interpret reports
7. **Quality Scoring** - Scoring algorithm and interpretation
8. **Common Issues** - Troubleshooting guide with solutions
9. **Recommendations** - Best practices and guidelines
10. **Appendix** - Error code reference

**Key Highlights**:
- 📖 Step-by-step instructions with examples
- 🐛 Troubleshooting for 5 common issues
- 💡 Best practices for data cleaning
- 📊 Quality score interpretation guide
- 🔍 Complete error code reference (RDV-001 to RDV-043)

---

### 4. Sample Validation Report
**File**: `MAXIS-08_RAW_DATA_VALIDATION_SAMPLE_REPORT.md` (450+ lines)

**Purpose**: Example output showing what a validation report looks like.

**Report Sections**:
1. **Executive Summary**
   - Overall quality score
   - Total errors and warnings
   - Transformation readiness status

2. **Per-File Summary Table**
   - Quick overview of all 11 files
   - Status, score, error/warning counts

3. **Detailed Results by File**
   - Summary statistics (records, columns, missing data)
   - Complete list of errors and warnings
   - Quality score breakdown

4. **Recommendations for Data Cleaning**
   - Prioritized action items
   - Estimated effort for fixes
   - Risk assessment

5. **Transformation Readiness Assessment**
   - Pass/fail criteria
   - Required actions before transformation
   - Next steps

**Example Findings**:
- 5 critical errors across 4 files
- 28 warnings requiring review
- Overall quality score: 87.5/100
- Status: "Ready with Cautions"

---

## 🎯 Validation Framework Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Raw Data Validation Framework                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │      RawDataValidator Class             │
        │  (Main orchestrator and validator)      │
        └─────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  File Loading    │ │  Validation      │ │  Report          │
│  & Scanning      │ │  Execution       │ │  Generation      │
└──────────────────┘ └──────────────────┘ └──────────────────┘
          │                   │                   │
          │                   │                   │
          ▼                   ▼                   ▼
    11 CSV Files      24+ Validation       Markdown + JSON
    (DM, AE, CM,         Checks              Reports
     VS, LB, EX,      (RDV-001 to 
     EG, PE)            RDV-043)
```

### Validation Flow

```
Start
  │
  ├─► 1. Initialize Validator
  │      └─► Load file mappings
  │      └─► Define required identifiers
  │      └─► Set validation rules
  │
  ├─► 2. For Each File (11 files):
  │      │
  │      ├─► 2.1 Load CSV file
  │      │
  │      ├─► 2.2 Get Summary Statistics
  │      │      └─► Record counts
  │      │      └─► Column counts
  │      │      └─► Missing data rates
  │      │      └─► Duplicate counts
  │      │
  │      ├─► 2.3 Validate Identifiers
  │      │      └─► Check required fields present
  │      │      └─► Check for missing values
  │      │      └─► Check for empty strings
  │      │      └─► Validate STUDY field
  │      │
  │      ├─► 2.4 Validate Dates
  │      │      └─► Identify date columns
  │      │      └─► Check date formats
  │      │      └─► Check date logic (start < end)
  │      │      └─► Flag high missing rates
  │      │
  │      ├─► 2.5 Check Duplicates
  │      │      └─► Exact duplicate rows
  │      │      └─► Duplicate key combinations
  │      │      └─► Duplicate subjects (DM only)
  │      │
  │      ├─► 2.6 Check Missing Data
  │      │      └─► Critical fields by domain
  │      │      └─► Overall missing rate
  │      │      └─► Missing data patterns
  │      │
  │      ├─► 2.7 Data Quality Checks
  │      │      └─► Empty columns
  │      │      └─► No-variance columns
  │      │      └─► Control characters
  │      │      └─► Statistical outliers
  │      │
  │      ├─► 2.8 Calculate Quality Score
  │      │      └─► Start with 100 points
  │      │      └─► Deduct for errors (-10 each)
  │      │      └─► Deduct for warnings (-2 each)
  │      │      └─► Deduct for missing data
  │      │      └─► Deduct for duplicates
  │      │
  │      └─► 2.9 Determine Status
  │             └─► PASS, REVIEW, or FAIL
  │
  ├─► 3. Calculate Overall Score
  │      └─► Average of all file scores
  │
  ├─► 4. Generate Report
  │      └─► Markdown format with sections
  │      └─► JSON format for programmatic use
  │
  └─► 5. Return Results
         └─► Exit code 0 (success) or 1 (failure)
```

---

## 📊 Validation Checks Detail

### Category 1: Required Identifiers (RDV-001 to RDV-006)

| Check | Code | Severity | Description |
|-------|------|----------|-------------|
| Field Present | RDV-001 | CRITICAL | Required identifier field exists |
| Not Null | RDV-002 | CRITICAL | No null values in identifier |
| Not Empty | RDV-003 | CRITICAL | No empty strings in identifier |
| Has Values | RDV-004 | CRITICAL | Field has at least one valid value |
| Consistency | RDV-005 | WARNING | Multiple STUDY values detected |
| Correctness | RDV-006 | WARNING | STUDY value matches expected |

**Required Identifiers by Domain**:
- **All Domains**: STUDY, INVSITE, PT
- These form the basis for USUBJID: `{STUDY}-{INVSITE}-{PT}`

### Category 2: Date Validation (RDV-010 to RDV-013)

| Check | Code | Severity | Description |
|-------|------|----------|-------------|
| Missing Rate | RDV-010 | WARNING | >50% missing dates in field |
| Format Valid | RDV-011 | WARNING | Date format is recognizable |
| Multiple Invalid | RDV-012 | WARNING | Many invalid dates in field |
| Date Logic | RDV-013 | CRITICAL | End date after start date |

**Supported Date Formats**:
- ISO 8601: `YYYY-MM-DD` ✅ (preferred)
- Slash: `YYYY/MM/DD` or `MM/DD/YYYY`
- SAS: `DD-MON-YYYY`
- Compact: `YYYYMMDD`
- Partial: `YYYY-MM` or `YYYY`

### Category 3: Duplicates (RDV-020 to RDV-022)

| Check | Code | Severity | Description |
|-------|------|----------|-------------|
| Exact Duplicates | RDV-020 | CRITICAL | Completely duplicate rows |
| Key Duplicates | RDV-021 | WARNING | Duplicates on key fields |
| DM Duplicates | RDV-022 | CRITICAL | Duplicate subjects in DM |

### Category 4: Missing Data (RDV-030 to RDV-033)

| Check | Code | Severity | Description |
|-------|------|----------|-------------|
| Field Present | RDV-030 | WARNING | Expected critical field missing |
| High Missing | RDV-031 | WARNING | >10% missing in critical field |
| Some Missing | RDV-032 | INFO | <10% missing in field |
| Overall High | RDV-033 | WARNING | >20% overall missing data |

### Category 5: Data Quality (RDV-040 to RDV-043)

| Check | Code | Severity | Description |
|-------|------|----------|-------------|
| Empty Columns | RDV-040 | WARNING | Columns with all null values |
| No Variance | RDV-041 | INFO | Column has only one unique value |
| Control Chars | RDV-042 | WARNING | Control characters in text |
| Outliers | RDV-043 | INFO | Statistical outliers detected |

---

## 💯 Quality Scoring System

### Algorithm

```python
score = 100  # Start with perfect score

# Deduct for issues
score -= (critical_errors * 10)  # -10 points per error
score -= (warnings * 2)           # -2 points per warning

# Additional deductions
if missing_data_pct > 20:
    score -= 20
elif missing_data_pct > 10:
    score -= 10
elif missing_data_pct > 5:
    score -= 5

if duplicate_pct > 5:
    score -= 10
elif duplicate_pct > 1:
    score -= 5

# Ensure valid range
score = max(0, min(100, score))
```

### Score Interpretation

| Score | Quality | Status | Recommendation |
|-------|---------|--------|----------------|
| 95-100 | Excellent | ✅ PASS | Proceed with transformation |
| 85-94 | Good | ⚠️ REVIEW | Review warnings, then proceed |
| 70-84 | Acceptable | ⚠️ REVIEW | Address major warnings first |
| 50-69 | Poor | ❌ FAIL | Significant cleanup required |
| 0-49 | Very Poor | ❌ FAIL | Extensive issues - do not proceed |

### Example Score Calculations

**File 1: DEMO.csv**
- Critical errors: 0 → -0
- Warnings: 3 → -6
- Missing: 4.2% → -0
- Duplicates: 0% → -0
- **Score: 94/100** ✅

**File 2: HEMLAB.csv**
- Critical errors: 1 → -10
- Warnings: 12 → -24
- Missing: 5.2% → -10
- Duplicates: 1.4% → -5
- **Score: 51/100** ❌

---

## 🚀 Quick Start Guide

### Step 1: Prerequisites

```bash
# Check Python version (need 3.8+)
python3 --version

# Install required packages
pip install pandas numpy

# Make scripts executable
chmod +x raw_data_validation.py
chmod +x run_raw_data_validation.sh
```

### Step 2: Prepare Data

Ensure source data is in expected location:
```
/tmp/s3_data/extracted/Maxis-08 RAW DATA_CSV/
├── DEMO.csv
├── AEVENT.csv
├── AEVENTC.csv
├── CONMEDS.csv
├── CONMEDSC.csv
├── VITALS.csv
├── HEMLAB.csv
├── CHEMLAB.csv
├── DOSE.csv
├── ECG.csv
└── PHYSEXAM.csv
```

### Step 3: Run Validation

**Method A: Shell Script (Easiest)**
```bash
cd /Users/siddharthchauhan/Work/Projects/ETL/sdtm_pipeline
./run_raw_data_validation.sh
```

**Method B: Python Script**
```bash
python3 raw_data_validation.py \
    --data-path "/tmp/s3_data/extracted/Maxis-08 RAW DATA_CSV" \
    --study-id "MAXIS-08" \
    --output "MAXIS-08_RAW_DATA_VALIDATION_REPORT.md" \
    --json-output "validation_results.json"
```

**Method C: Python Import**
```python
from raw_data_validation import RawDataValidator

validator = RawDataValidator(
    data_path="/tmp/s3_data/extracted/Maxis-08 RAW DATA_CSV",
    study_id="MAXIS-08"
)
results = validator.validate_all_files()
report = validator.generate_report(results, "report.md")
```

### Step 4: Review Results

Check generated files:
- `MAXIS-08_RAW_DATA_VALIDATION_REPORT.md` - Human-readable report
- `validation_results_{timestamp}.json` - Machine-readable results
- `raw_data_validation_{timestamp}.log` - Execution log

### Step 5: Take Action

Based on report recommendations:
1. Fix critical errors (must fix)
2. Address warnings (should fix)
3. Document decisions (for auditing)
4. Re-run validation after fixes
5. Proceed to SDTM transformation when score ≥ 90

---

## 📋 Expected Outputs

### 1. Markdown Report

**File**: `MAXIS-08_RAW_DATA_VALIDATION_REPORT.md`

**Contents**:
- Executive summary with overall score
- Per-file summary table
- Detailed findings for each file
- Recommendations prioritized by severity
- Transformation readiness assessment

**Size**: ~50-100 KB depending on issue count

### 2. JSON Results

**File**: `validation_results_{timestamp}.json`

**Contents**:
```json
{
  "study_id": "MAXIS-08",
  "validation_date": "2025-02-02T14:30:15",
  "overall_quality_score": 87.5,
  "total_errors": 5,
  "total_warnings": 28,
  "files_validated": 11,
  "file_results": {
    "DEMO.csv": {
      "status": "PASS",
      "quality_score": 94.0,
      "critical_errors_count": 0,
      "warnings_count": 3,
      "summary_stats": {...},
      "critical_errors": [],
      "warnings": [...]
    },
    ...
  }
}
```

**Use Cases**:
- Programmatic analysis
- Integration with CI/CD pipelines
- Trend tracking over time
- Automated decision making

### 3. Execution Log

**File**: `raw_data_validation_{timestamp}.log`

**Contents**:
- Console output capture
- Timestamps for each operation
- Error messages and stack traces
- Performance metrics

---

## 🔧 Customization Options

### Configuration Parameters

The validation framework can be customized via code modifications:

```python
# Modify file mappings
self.file_mappings = {
    "DEMO.csv": {"domain": "DM", "expected_records": 16, ...},
    # Add or modify files
}

# Modify required identifiers
self.required_identifiers = {
    "DM": ["STUDY", "INVSITE", "PT"],
    # Add domain-specific requirements
}

# Modify date patterns
self.date_fields_patterns = [
    r'.*DATE.*', r'.*DT$', r'.*DTC$',
    # Add custom patterns
]

# Modify scoring thresholds
def _calculate_quality_score(self, result, df):
    # Customize deduction amounts
    score -= result["critical_errors_count"] * 10
    score -= result["warnings_count"] * 2
    # ...
```

### Environment Variables

```bash
# Data location
export DATA_PATH="/custom/path"

# Study identifier
export STUDY_ID="CUSTOM-STUDY-01"

# Output location
export OUTPUT_DIR="/custom/output"

# Then run
./run_raw_data_validation.sh
```

---

## 🎓 Best Practices

### Before Running Validation

✅ **Do**:
- Ensure data is from latest database lock
- Verify all files are present and complete
- Back up original files before any modifications
- Document any known data quality issues

❌ **Don't**:
- Run validation on incomplete data exports
- Modify source files without backup
- Ignore critical errors and proceed anyway
- Skip re-validation after making fixes

### Interpreting Results

✅ **Do**:
- Read the entire report carefully
- Prioritize critical errors over warnings
- Investigate all duplicate records
- Document decisions about data quality issues

❌ **Don't**:
- Focus only on the quality score
- Ignore warnings (they often indicate real problems)
- Assume all outliers are errors (may be valid)
- Proceed with transformation if critical errors exist

### Data Cleaning

✅ **Do**:
- Fix critical errors first (blocking issues)
- Standardize all dates to ISO 8601
- Remove true duplicate records
- Document all changes made

❌ **Don't**:
- Delete data without investigation
- Use placeholder values for missing data (e.g., "N/A", "9999")
- Change data values arbitrarily
- Skip re-validation after fixes

---

## 📞 Support and Troubleshooting

### Common Issues

#### Issue 1: "File not found"
**Solution**: Check data path and ensure files are loaded from S3

#### Issue 2: "Module pandas not found"
**Solution**: `pip install pandas numpy`

#### Issue 3: "Permission denied"
**Solution**: `chmod +x run_raw_data_validation.sh`

#### Issue 4: "Encoding error"
**Solution**: Ensure CSV files are UTF-8 encoded

### Getting Help

- **Technical Issues**: Review execution log file
- **Data Quality Questions**: Consult with Data Management team
- **SDTM Questions**: Refer to CDISC SDTM-IG 3.4

---

## 📚 Related Documents

1. **`raw_data_validation.py`** - Core validation script
2. **`run_raw_data_validation.sh`** - Execution wrapper
3. **`RAW_DATA_VALIDATION_GUIDE.md`** - Comprehensive user guide
4. **`MAXIS-08_RAW_DATA_VALIDATION_SAMPLE_REPORT.md`** - Example output

---

## 🎯 Success Criteria

### Validation is Successful When:

- ✅ All 11 source files are found and loaded
- ✅ 0 critical errors across all files
- ✅ Overall quality score ≥ 90/100
- ✅ All required identifiers present and complete
- ✅ Date formats standardized (ISO 8601)
- ✅ No duplicate records in any file
- ✅ Missing data rates within acceptable thresholds (<10% for critical fields)

### Ready for SDTM Transformation When:

- ✅ Validation success criteria met
- ✅ All warnings reviewed and documented
- ✅ Data quality sign-off obtained from Data Manager
- ✅ Validation report archived for audit trail

---

## 📈 Next Steps After Validation

### Immediate (Same Day):
1. Review validation report
2. Document critical errors
3. Create action plan for fixes

### Short-term (This Week):
1. Fix critical errors
2. Re-run validation
3. Address warnings
4. Obtain data quality sign-off

### Medium-term (Before Transformation):
1. Proceed to Phase 3: Mapping Specification
2. Begin SDTM transformation
3. Run CDISC conformance validation
4. Generate Define-XML 2.1

---

## 📝 Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-02-02 | Validation Agent | Initial release |

---

## 📄 License and Usage

This validation framework is part of the MAXIS-08 SDTM ETL Pipeline.

**Usage Rights**: Internal use for MAXIS-08 study data validation

**Support**: Contact SDTM Pipeline Team

---

**Package Created**: 2025-02-02  
**Last Updated**: 2025-02-02  
**Status**: ✅ Ready for Production Use

---

## Appendix: Complete File Listing

```
/Users/siddharthchauhan/Work/Projects/ETL/sdtm_pipeline/
│
├── raw_data_validation.py                           (1,050 lines)
│   └── Core validation script with RawDataValidator class
│
├── run_raw_data_validation.sh                       (180 lines)
│   └── Bash wrapper for easy execution
│
├── RAW_DATA_VALIDATION_GUIDE.md                     (850 lines)
│   └── Comprehensive user documentation
│
├── MAXIS-08_RAW_DATA_VALIDATION_SAMPLE_REPORT.md   (450 lines)
│   └── Example validation report output
│
└── RAW_DATA_VALIDATION_DELIVERABLES.md             (This file)
    └── Deliverables package overview

Total: 5 files, ~2,600 lines of code and documentation
```

---

**End of Deliverables Package Documentation**

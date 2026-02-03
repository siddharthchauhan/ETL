# MAXIS-08 Raw Data Validation - Quick Start Guide

**Last Updated**: 2025-02-02  
**Status**: ✅ Ready for Execution  
**Estimated Time**: 5 hours

---

## Purpose

This guide provides step-by-step instructions for executing comprehensive raw source data validation for Study MAXIS-08 before SDTM transformation.

---

## Prerequisites Checklist

- [ ] Python 3.8+ installed
- [ ] Required packages: `pandas`, `numpy`
- [ ] Source data files available (48 CSV files)
- [ ] ~50MB disk space for validation results
- [ ] Terminal/command line access

---

## Quick Start (3 Steps)

### Step 1: Install Requirements

```bash
# Install required Python packages
pip install pandas numpy

# Verify installation
python3 -c "import pandas, numpy; print('✅ Ready')"
```

### Step 2: Get Source Data

**Option A: Data already extracted**
```bash
# Verify files exist
ls -la /tmp/s3_data/extracted/Maxis-08\ RAW\ DATA_CSV/
# Should show 48 CSV files
```

**Option B: Download from S3**
```bash
# Download ZIP from S3
aws s3 cp s3://s3dcri/Clinical_Studies/MAXIS-08/RAW_DATA/Maxis-08\ RAW\ DATA.zip /tmp/

# Extract files
unzip "/tmp/Maxis-08 RAW DATA.zip" -d /tmp/s3_data/extracted/

# Verify extraction
ls -1 /tmp/s3_data/extracted/Maxis-08\ RAW\ DATA_CSV/*.csv | wc -l
# Should output: 48
```

### Step 3: Run Validation

```bash
cd /Users/siddharthchauhan/Work/Projects/ETL/sdtm_pipeline

# Make script executable
chmod +x run_comprehensive_validation.sh

# Run validation (default path)
./run_comprehensive_validation.sh

# Or specify custom data path
./run_comprehensive_validation.sh /path/to/your/data
```

---

## What Gets Validated

### ✅ Layer 1: Structural Validation (1 hour)
- File existence and accessibility
- Required columns present
- Data types consistent
- Record counts within expected ranges
- Null value patterns
- Duplicate detection

### ✅ Layer 2: Business Rules (2 hours)
- **DM Rules**: Subject uniqueness, SEX/RACE CT, age plausibility
- **AE Rules**: Required fields, severity CT, date consistency
- **VS Rules**: Test codes, physiological ranges, unit validation
- **LB Rules**: Test codes, categories, date presence
- **CM Rules**: Medication names, route CT, date validation
- **EX Rules**: Dose positivity, date presence
- **EG Rules**: ECG parameter ranges, QTc validation
- **PE Rules**: Finding documentation

### ✅ Layer 3: Cross-Domain Checks (1 hour)
- All subjects in event domains exist in DM
- Date consistency across domains
- Visit consistency
- Treatment consistency

### ✅ Layer 4: Data Quality Metrics (included)
- Completeness score
- Validity score
- Consistency score
- Accuracy score
- Uniqueness score

### ✅ Layer 5: CT Preview (included)
- CDISC CT conformance assessment
- Non-standard term identification

---

## Expected Output

### Files Created

```
validation_results/
├── structural_validation_YYYYMMDD_HHMMSS.json
├── enhanced_validation_YYYYMMDD_HHMMSS.json
└── README.txt
```

### Console Output

```
================================================================================
VALIDATION SUMMARY - MAXIS-08
================================================================================

Files Validated: 14
Total Records: 19,076
Quality Score: 92.5/100

Issues by Severity:
  Critical Errors:    0  ❌ MUST FIX
  Errors:            12  ⚠️  SHOULD FIX
  Warnings:          28  ⚠️  REVIEW
  Info:              45  ℹ️  INFORMATIONAL

Transformation Readiness:
  CONDITIONAL - Address errors and review warnings

================================================================================
```

---

## Understanding Results

### Quality Score Interpretation

| **Score** | **Grade** | **Meaning** | **Action** |
|-----------|-----------|------------|-----------|
| 95-100 | Excellent | Ready for transformation | Proceed |
| 90-94 | Good | Minor issues | Address before transformation |
| 80-89 | Fair | Moderate issues | Fix errors, review warnings |
| <80 | Poor | Significant issues | Must fix before transformation |

### Issue Severity Levels

| **Severity** | **Icon** | **Meaning** | **Action** |
|-------------|---------|------------|-----------|
| **CRITICAL** | ❌ | Blocks transformation | **MUST FIX** immediately |
| **ERROR** | ⚠️ | CDISC non-conformance | **SHOULD FIX** before submission |
| **WARNING** | ⚠️ | Quality concern | **REVIEW** and document |
| **INFO** | ℹ️ | Observation | Informational only |

### Transformation Readiness Status

- **READY**: All checks passed, proceed with transformation
- **CONDITIONAL**: Minor issues, can proceed with documentation
- **NOT READY**: Critical blockers must be resolved first

---

## Common Issues and Solutions

### Issue 1: Data Files Not Found

**Error**: `Data path not found: /tmp/s3_data/extracted/Maxis-08 RAW DATA_CSV`

**Solution**:
```bash
# Download and extract data (see Step 2 above)
aws s3 cp s3://s3dcri/Clinical_Studies/MAXIS-08/RAW_DATA/Maxis-08\ RAW\ DATA.zip /tmp/
unzip "/tmp/Maxis-08 RAW DATA.zip" -d /tmp/s3_data/extracted/
```

### Issue 2: Missing Python Packages

**Error**: `ModuleNotFoundError: No module named 'pandas'`

**Solution**:
```bash
pip install pandas numpy
# Or with specific versions
pip install pandas>=1.3.0 numpy>=1.21.0
```

### Issue 3: Critical Errors Found

**Result**: `Critical Errors: 5 ❌ MUST FIX`

**Solution**:
1. Open the JSON results file
2. Find all issues with `"severity": "CRITICAL"`
3. Address each based on recommendation
4. Common critical errors:
   - Missing required identifier fields → Query sites
   - Duplicate subject IDs → Data cleaning
   - File not found → Verify data extraction

### Issue 4: Permission Denied

**Error**: `Permission denied: ./run_comprehensive_validation.sh`

**Solution**:
```bash
chmod +x run_comprehensive_validation.sh
./run_comprehensive_validation.sh
```

---

## Manual Execution (Alternative)

If the shell script doesn't work, run Python scripts directly:

### Structural Validation
```bash
python3 raw_data_validation.py \
  --data-path "/tmp/s3_data/extracted/Maxis-08 RAW DATA_CSV" \
  --study-id "MAXIS-08" \
  --output "structural_validation_results.json"
```

### Enhanced Validation
```bash
python3 enhanced_raw_data_validation.py \
  --data-path "/tmp/s3_data/extracted/Maxis-08 RAW DATA_CSV" \
  --study-id "MAXIS-08" \
  --output "enhanced_validation_results.json"
```

### View Results
```bash
# Pretty-print JSON
python3 -m json.tool enhanced_validation_results.json

# Extract summary
python3 -c "
import json
with open('enhanced_validation_results.json') as f:
    r = json.load(f)
    print(f'Quality Score: {r[\"overall_quality_score\"]:.1f}/100')
    print(f'Readiness: {r[\"transformation_readiness\"]}')
"
```

---

## Next Steps After Validation

### If Status = READY ✅
1. ✅ Review validation report
2. ✅ Document any informational findings
3. ✅ Proceed to SDTM transformation
4. ✅ Begin mapping specification development

### If Status = CONDITIONAL ⚠️
1. 📋 Review all ERRORS and WARNINGS
2. 🔧 Fix critical data quality issues
3. 📝 Document known issues in SDRG
4. ✅ Obtain medical review for outliers
5. ✅ Proceed with transformation (issues documented)

### If Status = NOT READY ❌
1. 🔧 Fix all CRITICAL errors
2. 🔧 Address major ERRORS
3. 📋 Query sites for missing data
4. 🔄 Re-run validation
5. ⏸️ Hold transformation until READY

---

## Key Deliverables

After successful validation, you'll have:

1. **Validation Results (JSON)**
   - Detailed findings by domain
   - Issue list with recommendations
   - Data quality metrics

2. **Console Summary**
   - Overall quality score
   - Issue counts by severity
   - Transformation readiness assessment

3. **Comprehensive Report (Markdown)**
   - MAXIS-08_COMPREHENSIVE_RAW_DATA_VALIDATION_REPORT.md
   - Complete validation framework
   - Business rules catalog
   - Resolution guidance

---

## Validation Timeline

| **Phase** | **Duration** | **Can Parallelize?** |
|-----------|-------------|---------------------|
| Prerequisites | 30 min | No |
| Structural Validation | 1 hour | No |
| Business Rules Validation | 2 hours | No |
| Cross-Domain Validation | 1 hour | No |
| Report Generation | 30 min | No |
| **Total** | **5 hours** | Sequential execution required |

---

## Support and Troubleshooting

### Review These Documents

1. **Comprehensive Validation Report**  
   `MAXIS-08_COMPREHENSIVE_RAW_DATA_VALIDATION_REPORT.md`  
   Complete validation framework with all business rules

2. **Validation Guide**  
   `RAW_DATA_VALIDATION_GUIDE.md`  
   Detailed explanations of validation checks

3. **Validation Index**  
   `RAW_DATA_VALIDATION_INDEX.md`  
   Quick reference for validation rules

### Common Questions

**Q: How long does validation take?**  
A: Approximately 5 hours for all 48 files (19,076 records)

**Q: Can I validate a subset of domains?**  
A: Yes, modify the `file_mappings` dict in the Python scripts

**Q: What if I have different file names?**  
A: Update the `file_mappings` dictionary with your file names

**Q: Can validation run in parallel?**  
A: No, cross-domain checks require sequential processing

**Q: Is this validation FDA-compliant?**  
A: This is pre-transformation validation. FDA compliance validation (Pinnacle 21) runs post-transformation on SDTM datasets.

---

## Validation Checklist

Use this checklist to track your validation execution:

- [ ] Prerequisites verified (Python, packages, data)
- [ ] Source data files extracted (48 CSV files)
- [ ] Structural validation executed successfully
- [ ] Enhanced validation executed successfully
- [ ] Results reviewed and understood
- [ ] Critical errors addressed (if any)
- [ ] Errors documented and addressed
- [ ] Warnings reviewed by medical/data team
- [ ] Transformation readiness assessment completed
- [ ] Validation package delivered to sponsor
- [ ] Sign-off obtained to proceed with transformation

---

## Quick Commands Reference

```bash
# Check Python version
python3 --version

# Install packages
pip install pandas numpy

# Count source files
ls -1 /tmp/s3_data/extracted/Maxis-08\ RAW\ DATA_CSV/*.csv | wc -l

# Run validation
./run_comprehensive_validation.sh

# View results
cat validation_results/enhanced_validation_*.json | python3 -m json.tool | less

# Extract quality score
python3 -c "import json; r=json.load(open('validation_results/enhanced_validation_*.json')); print(r['overall_quality_score'])"
```

---

## Success Criteria

Validation is considered successful when:

✅ All 48 source files validated  
✅ Quality score ≥ 90/100  
✅ Zero CRITICAL errors  
✅ Errors < 10  
✅ All issues documented  
✅ Transformation readiness = READY or CONDITIONAL  
✅ Stakeholder sign-off obtained

---

## Document Control

| **Attribute** | **Value** |
|--------------|----------|
| **Version** | 1.0 |
| **Author** | Validation Agent |
| **Last Updated** | 2025-02-02 |
| **Review Date** | After each execution |
| **Approval** | Study Lead |

---

**Ready to start? Run this command:**

```bash
cd /Users/siddharthchauhan/Work/Projects/ETL/sdtm_pipeline && ./run_comprehensive_validation.sh
```

Good luck! 🚀

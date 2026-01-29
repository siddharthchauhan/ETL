# AE Domain Fix - Quick Start Guide

## 🚀 Quick Start (3 Steps)

### 1. Configure AWS
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```

### 2. Run the Fix
```bash
cd /Users/siddharth/Downloads/ETL/ETL/sdtm_pipeline
python ae_complete_fix.py
```

### 3. Check Results
```bash
# View the corrected AE domain
head workspace/AE.csv

# Read the validation report
cat workspace/AE_CORRECTION_REPORT.txt
```

---

## ✅ What Gets Fixed

| Issue | Before | After | Fix Applied |
|-------|--------|-------|-------------|
| **AESEQ Duplicates** | 504 duplicates | 0 duplicates | ROW_NUMBER() by USUBJID |
| **AESER Values** | YES, NO, 1, 0 | Y, N | Controlled terminology mapping |
| **AESEV Values** | 1, 2, 3, M | MILD, MODERATE, SEVERE | Controlled terminology mapping |
| **Date Format** | 20080910 | 2008-09-10 | ISO 8601 conversion |

---

## 📁 Output Files

After running, you'll find:

```
workspace/
├── AE.csv                        ← Corrected SDTM AE domain
└── AE_CORRECTION_REPORT.txt      ← Detailed validation report
```

---

## ✨ Expected Result

```
================================================================================
✅ AE DOMAIN FIX COMPLETED!
================================================================================

Output Files:
  - AE Domain: workspace/AE.csv
  - Report: workspace/AE_CORRECTION_REPORT.txt

✅ All 534 records passed validation!
================================================================================
```

---

## 📋 Validation Checks

The script automatically validates:

- ✅ **AESEQ Uniqueness**: No duplicates within USUBJID
- ✅ **AESER CT**: All values are Y, N, or blank
- ✅ **AESEV CT**: All values are MILD, MODERATE, SEVERE, or blank  
- ✅ **ISO 8601 Dates**: All dates in YYYY-MM-DD format

---

## 🔧 Troubleshooting

### AWS Credentials Error
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```

### Python Dependencies
```bash
pip install pandas numpy boto3 python-dotenv
```

### Source File Not Found
Verify S3 access:
```bash
aws s3 ls s3://s3dcri/incoming/
```

---

## 📚 More Information

- **Detailed Guide**: `AE_FIX_SUMMARY.md`
- **Instructions**: `RUN_AE_FIX.md`
- **Script**: `ae_complete_fix.py`

---

## ⚡ One-Liner

```bash
python ae_complete_fix.py && cat workspace/AE_CORRECTION_REPORT.txt
```

This will:
1. Load data from S3
2. Apply all 4 fixes
3. Validate corrections
4. Save AE.csv and report
5. Display the report

**Done!** 🎉

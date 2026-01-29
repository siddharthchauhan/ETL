# AE Domain Fix - Instructions

## Overview

This script fixes and regenerates the SDTM AE domain for study MAXIS-08 with the following corrections:

### Fixes Applied

1. **AESEQ Duplicates (504 duplicates)**
   - Regenerates AESEQ using: `ROW_NUMBER() OVER (PARTITION BY USUBJID ORDER BY AESTDTC, AETERM)`
   - Ensures AESEQ is unique within each USUBJID

2. **Invalid AESER Controlled Terminology (6 records)**
   - Maps to valid values: Y, N
   - Conversions: YES→Y, NO→N, 1→Y, 0→N

3. **Invalid AESEV Controlled Terminology (15 records)**
   - Maps to valid values: MILD, MODERATE, SEVERE
   - Conversions: 1→MILD, 2→MODERATE, 3→SEVERE, M→MILD

4. **Invalid ISO 8601 Dates (9 records)**
   - Converts: YYYYMMDD → YYYY-MM-DD
   - Handles partial dates: YYYYMM → YYYY-MM

## Requirements

```bash
pip install pandas numpy boto3 python-dotenv
```

## AWS Configuration

Ensure AWS credentials are configured:
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

Or use `~/.aws/credentials`:
```
[default]
aws_access_key_id = your_key
aws_secret_access_key = your_secret
```

## Running the Fix

```bash
cd /Users/siddharth/Downloads/ETL/ETL/sdtm_pipeline
python ae_complete_fix.py
```

## Output Files

The script generates:

1. **`workspace/AE.csv`** - Corrected SDTM AE domain
2. **`workspace/AE_CORRECTION_REPORT.txt`** - Detailed validation report

## Expected Results

```
✅ AESEQ: No duplicates - unique within USUBJID
✅ AESER: All values valid (Y/N)  
✅ AESEV: All values valid (MILD/MODERATE/SEVERE)
✅ Dates: All in ISO 8601 format (YYYY-MM-DD)
```

## Pipeline Steps

1. **Load EDC Data** - Downloads and extracts from s3://s3dcri/incoming/EDC Data.zip
2. **Transform with Fixes** - Applies all 4 corrections during transformation
3. **Validate** - Confirms all issues resolved
4. **Generate Report** - Creates detailed correction report

## Troubleshooting

### Issue: AWS credentials not found
```bash
# Set credentials
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```

### Issue: S3 bucket access denied
- Verify IAM permissions include `s3:GetObject` for `s3dcri` bucket
- Check bucket name and key are correct

### Issue: Source file not found
- Verify `AEVENT.csv` exists in the ZIP file
- Check ZIP structure with: `unzip -l "EDC Data.zip"`

## Validation Report

The report includes:

- Total records processed
- Confirmation of AESEQ uniqueness
- AESER and AESEV controlled terminology validation
- ISO 8601 date format validation
- Column-by-column population statistics
- Sample data for any remaining issues

## Contact

For issues or questions, refer to the SDTM pipeline documentation.

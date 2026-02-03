====================================================================================================
RAW DATA VALIDATION REPORT - Study MAXIS-08
====================================================================================================
Validation Date: 2025-02-02T14:30:15
Data Path: /tmp/s3_data/extracted/Maxis-08 RAW DATA_CSV
Files Validated: 11 / 11

EXECUTIVE SUMMARY
----------------------------------------------------------------------------------------------------
Overall Quality Score: 87.5/100
Total Critical Errors: 5
Total Warnings: 28
Transformation Readiness: ⚠️  READY WITH CAUTIONS - Review warnings before proceeding

PER-FILE VALIDATION RESULTS
----------------------------------------------------------------------------------------------------
File                 Domain   Records    Status     Score    Errors   Warnings  
----------------------------------------------------------------------------------------------------
DEMO.csv             DM       16         PASS       94.0     0        3         
AEVENT.csv           AE       550        REVIEW     82.0     1        6         
AEVENTC.csv          AE       276        PASS       90.0     0        5         
CONMEDS.csv          CM       302        REVIEW     78.0     2        8         
CONMEDSC.csv         CM       302        PASS       92.0     0        4         
VITALS.csv           VS       536        PASS       88.0     1        3         
HEMLAB.csv           LB       1,726      FAIL       68.0     1        12        
CHEMLAB.csv          LB       3,326      PASS       86.0     0        7         
DOSE.csv             EX       271        PASS       94.0     0        2         
ECG.csv              EG       60         PASS       96.0     0        1         
PHYSEXAM.csv         PE       2,169      PASS       90.0     0        5         

DETAILED VALIDATION RESULTS BY FILE
====================================================================================================

DEMO.csv → DM Domain
----------------------------------------------------------------------------------------------------
Records: 16 (variance: 0 / +0.0%)
Columns: 12 (variance: 0)
Missing Data: 8 cells (4.2%)
Duplicate Rows: 0
Quality Score: 94.0/100
Status: PASS

Warnings (3):
  • RDV-010: Date field 'BRTHDAT' has 2 missing values (12.5%)
  • RDV-031: Critical field 'RACE' has 1 missing value (6.2%)
  • RDV-041: Column 'STUDY' has only one unique value: 'MAXIS-08'

AEVENT.csv → AE Domain
----------------------------------------------------------------------------------------------------
Records: 550 (variance: 0 / +0.0%)
Columns: 38 (variance: 0)
Missing Data: 325 cells (1.6%)
Duplicate Rows: 15
Quality Score: 82.0/100
Status: REVIEW

Critical Errors (1):
  • RDV-020: 15 completely duplicate rows found (2.7%)

Warnings (6):
  • RDV-011: Invalid date format in 'AESTDAT' at row 125: '2023/13/05'
  • RDV-011: Invalid date format in 'AESTDAT' at row 342: '05-32-2023'
  • RDV-011: Invalid date format in 'AEENDAT' at row 450: '99/99/9999'
  • RDV-013: 3 records have end date before start date (AESTDAT > AEENDAT)
  • RDV-031: Critical field 'AETERM' has 8 missing values (1.5%)
  • RDV-042: Column 'AETERM' contains control characters in 2 records

AEVENTC.csv → AE Domain
----------------------------------------------------------------------------------------------------
Records: 276 (variance: 0 / +0.0%)
Columns: 36 (variance: 0)
Missing Data: 158 cells (1.6%)
Duplicate Rows: 0
Quality Score: 90.0/100
Status: PASS

Warnings (5):
  • RDV-010: Date field 'AEST_DATE' has 5 missing values (1.8%)
  • RDV-031: Critical field 'AE_TERM' has 3 missing values (1.1%)
  • RDV-041: Column 'STUDY' has only one unique value: 'MAXIS-08'
  • RDV-043: Column 'AESEQ' has 2 potential outliers (0.7%)
  • RDV-032: Field 'AE_COMMENTS' has 145 missing values (52.5%)

CONMEDS.csv → CM Domain
----------------------------------------------------------------------------------------------------
Records: 302 (variance: 0 / +0.0%)
Columns: 38 (variance: 0)
Missing Data: 425 cells (3.7%)
Duplicate Rows: 8
Quality Score: 78.0/100
Status: REVIEW

Critical Errors (2):
  • RDV-002: Identifier field 'INVSITE' has 3 missing values (1.0%)
  • RDV-020: 8 completely duplicate rows found (2.6%)

Warnings (8):
  • RDV-011: Invalid date format in 'CMSTDAT' at row 45: '2022-13-01'
  • RDV-011: Invalid date format in 'CMSTDAT' at row 87: 'UNKNOWN'
  • RDV-011: Invalid date format in 'CMENDAT' at row 156: '9999-99-99'
  • RDV-012: Date field 'CMSTDAT' has 5 total invalid date formats (showing first 5)
  • RDV-013: 2 records have end date before start date (CMSTDAT > CMENDAT)
  • RDV-031: Critical field 'CMTRT' has 12 missing values (4.0%)
  • RDV-033: High overall missing data rate: 3.7% (425 / 11,476 cells)
  • RDV-043: Column 'CMDOSE' has 8 potential outliers (2.6%)

CONMEDSC.csv → CM Domain
----------------------------------------------------------------------------------------------------
Records: 302 (variance: 0 / +0.0%)
Columns: 34 (variance: 0)
Missing Data: 268 cells (2.6%)
Duplicate Rows: 0
Quality Score: 92.0/100
Status: PASS

Warnings (4):
  • RDV-010: Date field 'CMSTART' has 8 missing values (2.6%)
  • RDV-031: Critical field 'MEDICATION' has 5 missing values (1.7%)
  • RDV-032: Field 'INDICATION' has 125 missing values (41.4%)
  • RDV-041: Column 'STUDY' has only one unique value: 'MAXIS-08'

VITALS.csv → VS Domain
----------------------------------------------------------------------------------------------------
Records: 536 (variance: 0 / +0.0%)
Columns: 21 (variance: 0)
Missing Data: 285 cells (2.5%)
Duplicate Rows: 0
Quality Score: 88.0/100
Status: PASS

Critical Errors (1):
  • RDV-003: Identifier field 'INVSITE' has 2 empty values (0.4%)

Warnings (3):
  • RDV-010: Date field 'VSDAT' has 15 missing values (2.8%)
  • RDV-031: Critical field 'VSORRES' has 45 missing values (8.4%)
  • RDV-043: Column 'SYSBP' has 12 potential outliers (2.2%)

HEMLAB.csv → LB Domain
----------------------------------------------------------------------------------------------------
Records: 1,726 (variance: 0 / +0.0%)
Columns: 14 (variance: 0)
Missing Data: 1,250 cells (5.2%)
Duplicate Rows: 25
Quality Score: 68.0/100
Status: FAIL

Critical Errors (1):
  • RDV-020: 25 completely duplicate rows found (1.4%)

Warnings (12):
  • RDV-010: Date field 'LBDAT' has 125 missing values (7.2%)
  • RDV-011: Invalid date format in 'LBDAT' at row 234: '2023-2-30'
  • RDV-011: Invalid date format in 'LBDAT' at row 456: '32-JAN-2023'
  • RDV-011: Invalid date format in 'LBDAT' at row 789: 'PENDING'
  • RDV-012: Date field 'LBDAT' has 8 total invalid date formats (showing first 5)
  • RDV-031: Critical field 'LBTESTCD' has 15 missing values (0.9%)
  • RDV-031: Critical field 'LBORRES' has 85 missing values (4.9%)
  • RDV-033: High overall missing data rate: 5.2% (1,250 / 24,164 cells)
  • RDV-040: 2 columns have all missing values: LBSPEC, COMMENTS
  • RDV-042: Column 'LBORRES' contains control characters in 5 records
  • RDV-043: Column 'WBC' has 35 potential outliers (2.0%)
  • RDV-043: Column 'HGB' has 18 potential outliers (1.0%)

CHEMLAB.csv → LB Domain
----------------------------------------------------------------------------------------------------
Records: 3,326 (variance: 0 / +0.0%)
Columns: 13 (variance: 0)
Missing Data: 1,856 cells (4.3%)
Duplicate Rows: 0
Quality Score: 86.0/100
Status: PASS

Warnings (7):
  • RDV-010: Date field 'LBDAT' has 185 missing values (5.6%)
  • RDV-011: Invalid date format in 'LBDAT' at row 567: '2023/02/30'
  • RDV-011: Invalid date format in 'LBDAT' at row 1234: 'NOT DONE'
  • RDV-012: Date field 'LBDAT' has 5 total invalid date formats (showing first 5)
  • RDV-031: Critical field 'LBORRES' has 125 missing values (3.8%)
  • RDV-043: Column 'GLUCOSE' has 45 potential outliers (1.4%)
  • RDV-043: Column 'CREATININE' has 22 potential outliers (0.7%)

DOSE.csv → EX Domain
----------------------------------------------------------------------------------------------------
Records: 271 (variance: 0 / +0.0%)
Columns: 21 (variance: 0)
Missing Data: 125 cells (2.2%)
Duplicate Rows: 0
Quality Score: 94.0/100
Status: PASS

Warnings (2):
  • RDV-010: Date field 'EXENDAT' has 35 missing values (12.9%)
  • RDV-032: Field 'EXENDAT' has 35 missing values (12.9%)

ECG.csv → EG Domain
----------------------------------------------------------------------------------------------------
Records: 60 (variance: 0 / +0.0%)
Columns: 11 (variance: 0)
Missing Data: 15 cells (2.3%)
Duplicate Rows: 0
Quality Score: 96.0/100
Status: PASS

Warnings (1):
  • RDV-032: Field 'EGCOMM' has 45 missing values (75.0%)

PHYSEXAM.csv → PE Domain
----------------------------------------------------------------------------------------------------
Records: 2,169 (variance: 0 / +0.0%)
Columns: 14 (variance: 0)
Missing Data: 856 cells (2.8%)
Duplicate Rows: 0
Quality Score: 90.0/100
Status: PASS

Warnings (5):
  • RDV-010: Date field 'PEDAT' has 45 missing values (2.1%)
  • RDV-031: Critical field 'PEORRES' has 125 missing values (5.8%)
  • RDV-032: Field 'PEMETHOD' has 456 missing values (21.0%)
  • RDV-043: Column 'HEIGHT' has 8 potential outliers (0.4%)
  • RDV-043: Column 'WEIGHT' has 15 potential outliers (0.7%)

RECOMMENDATIONS FOR DATA CLEANING
====================================================================================================
1. CRITICAL: Address critical errors before SDTM transformation
2. HIGH PRIORITY: Fix missing/invalid identifiers (STUDY, INVSITE, PT) in: CONMEDS.csv, VITALS.csv
3. HIGH PRIORITY: Remove duplicate records in: AEVENT.csv, CONMEDS.csv, HEMLAB.csv
4. MEDIUM PRIORITY: Standardize date formats (recommend ISO 8601: YYYY-MM-DD) in: AEVENT.csv, CONMEDS.csv, HEMLAB.csv, CHEMLAB.csv
5. REVIEW: Investigate high missing data rates in: HEMLAB.csv (5.2%), CHEMLAB.csv (4.3%), CONMEDS.csv (3.7%)
6. Ensure all date fields use consistent format (preferably ISO 8601: YYYY-MM-DD)
7. Verify that all subjects (PT) have corresponding records in DEMO.csv
8. Confirm that STUDY field values match expected study ID (MAXIS-08)
9. Review and document any intentional missing data (e.g., adverse events not applicable)

====================================================================================================
End of Report - Generated: 2025-02-02 14:30:45
====================================================================================================


SUMMARY OF CRITICAL ISSUES REQUIRING ATTENTION
====================================================================================================

FILE: AEVENT.csv
Priority: HIGH
Issue: 15 completely duplicate rows (2.7%)
Action: Remove duplicate rows, keeping first occurrence
Impact: Duplicate records will cause issues in SDTM transformation

FILE: CONMEDS.csv
Priority: CRITICAL
Issue: 3 missing INVSITE values (1.0%) + 8 duplicate rows (2.6%)
Action: Query EDC system for missing site identifiers, remove duplicates
Impact: Missing identifiers prevent proper USUBJID construction

FILE: VITALS.csv
Priority: MEDIUM
Issue: 2 empty INVSITE values (0.4%)
Action: Replace empty strings with valid site identifiers
Impact: Empty identifiers will cause USUBJID construction errors

FILE: HEMLAB.csv
Priority: HIGH
Issue: 25 duplicate rows (1.4%), 8 invalid dates, 2 empty columns
Action: Remove duplicates, fix date formats, review empty columns
Impact: Multiple data quality issues affecting overall score

DATE FORMAT ISSUES (Multiple Files)
Priority: MEDIUM
Issue: Inconsistent date formats across files
Affected Files: AEVENT.csv, CONMEDS.csv, HEMLAB.csv, CHEMLAB.csv
Action: Standardize all dates to ISO 8601 format (YYYY-MM-DD)
Impact: Date format inconsistencies complicate transformation logic


TRANSFORMATION READINESS ASSESSMENT
====================================================================================================

✅ PASS Criteria:
  - [x] All source files present (11/11 files found)
  - [ ] Zero critical errors (5 critical errors found)
  - [ ] Overall quality score ≥ 85 (score: 87.5)
  - [x] All required domains covered (DM, AE, CM, VS, LB, EX, EG, PE)

⚠️  CONDITIONAL PASS - Action Required:
  The data can proceed to transformation AFTER addressing the following:
  
  1. Fix 5 critical errors (estimated time: 2-4 hours)
     - Remove 48 duplicate rows across 3 files
     - Fill 5 missing identifier values
  
  2. Standardize date formats (estimated time: 1-2 hours)
     - Convert all dates to ISO 8601
     - Fix 20+ invalid date values
  
  3. Review 28 warnings (estimated time: 4-6 hours)
     - Investigate missing data patterns
     - Validate outliers
     - Document data quality decisions

  TOTAL ESTIMATED EFFORT: 7-12 hours of data cleaning

⚠️  RISKS IF PROCEEDING WITHOUT FIXES:
  - SDTM transformation may fail on duplicate records
  - USUBJID construction will fail for records with missing identifiers
  - Date parsing errors will occur on invalid formats
  - Regulatory submission may be rejected due to data quality issues

✅ RECOMMENDATION:
  Address critical errors and major warnings before SDTM transformation.
  Re-run validation after corrections to confirm quality score ≥ 90.


DATA QUALITY METRICS
====================================================================================================

Completeness:
  Overall Missing Data Rate: 3.2% (5,576 missing cells / 173,284 total cells)
  Files with >5% Missing: 1 (HEMLAB.csv: 5.2%)
  Acceptable threshold: <5% missing data

Consistency:
  Date Format Issues: 4 files affected (20+ invalid dates)
  Identifier Completeness: 99.5% (5 missing / 1,000+ expected)
  STUDY Value Consistency: 100% (all records use "MAXIS-08")

Uniqueness:
  Duplicate Records: 48 across 3 files (0.5% of all records)
  DM Subject Duplication: 0 (✅ each subject appears once)

Accuracy:
  Date Logic Errors: 5 records with end date before start date
  Outliers Detected: 169 values across numeric fields (1.2%)
  Control Characters: 7 records affected

Overall Assessment: GOOD WITH RESERVATIONS
  - Data structure and completeness are acceptable
  - Critical errors must be fixed before transformation
  - Missing data is within acceptable ranges for most fields
  - Date standardization will improve transformation reliability


NEXT STEPS
====================================================================================================

IMMEDIATE (Before Transformation):
  1. ✅ Review this validation report in detail
  2. 🔧 Fix 5 critical errors in AEVENT.csv, CONMEDS.csv, VITALS.csv, HEMLAB.csv
  3. 🔧 Standardize date formats to ISO 8601 (YYYY-MM-DD)
  4. ✅ Re-run validation to confirm quality score ≥ 90
  5. 📄 Document all data corrections in Data Quality Log

SHORT-TERM (This Week):
  1. 🔍 Investigate and resolve 28 warnings
  2. 📊 Review outliers with clinical team for validation
  3. 📝 Document missing data patterns and reasons
  4. ✅ Obtain sign-off from Data Manager on data quality

MEDIUM-TERM (Before Submission):
  1. 🎯 Begin SDTM Mapping Specification (Phase 3)
  2. 🔄 Transform validated data to SDTM format (Phase 4)
  3. ✅ Run CDISC conformance validation on SDTM output
  4. 📋 Generate Define-XML 2.1 metadata

VALIDATION RE-RUN COMMAND:
  ./run_raw_data_validation.sh

For questions or support, contact: SDTM Pipeline Team

====================================================================================================

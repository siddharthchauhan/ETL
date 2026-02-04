#!/usr/bin/env python3
"""
Comprehensive SDTM AE Domain Transformation
Following CDISC SDTM-IG 3.4 Standards
"""

import pandas as pd
import numpy as np
from datetime import datetime
import re

# ===========================
# Date Conversion Functions
# ===========================

def to_iso8601_date(date_value):
    """Convert various date formats to ISO 8601 (YYYY-MM-DD)."""
    if pd.isna(date_value) or date_value == '':
        return ''
    
    if isinstance(date_value, (pd.Timestamp, datetime)):
        return date_value.strftime('%Y-%m-%d')
    
    if isinstance(date_value, (int, float)):
        str_val = str(int(date_value))
        if len(str_val) == 8:  # YYYYMMDD
            try:
                return datetime.strptime(str_val, '%Y%m%d').strftime('%Y-%m-%d')
            except ValueError:
                return ''
        elif len(str_val) == 6:  # YYYYMM (partial date)
            try:
                return datetime.strptime(str_val, '%Y%m').strftime('%Y-%m')
            except ValueError:
                return ''
    
    date_str = str(date_value).strip()
    
    # Already ISO 8601
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    if re.match(r'^\d{4}-\d{2}$', date_str):
        return date_str
    if re.match(r'^\d{4}$', date_str):
        return date_str
    
    # YYYYMMDD format
    if re.match(r'^\d{8}$', date_str):
        try:
            return datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
        except ValueError:
            return ''
    
    # YYYYMM format (partial)
    if re.match(r'^\d{6}$', date_str):
        try:
            return datetime.strptime(date_str, '%Y%m').strftime('%Y-%m')
        except ValueError:
            return ''
    
    return ''

# ===========================
# Controlled Terminology
# ===========================

SEVERITY_MAP = {
    'MILD': 'MILD',
    'MODERATE': 'MODERATE',
    'SEVERE': 'SEVERE',
    'LIFE THREATENING': 'LIFE THREATENING',
    'FATAL': 'FATAL'
}

SERIOUS_MAP = {
    'NOT SERIOUS': 'N',
    'UNLIKELY': 'N',
    'HOSPITALIZATION/PROLONGATION': 'Y',
}

CAUSALITY_MAP = {
    'UNRELATED': 'NOT RELATED',
    'UNLIKELY': 'UNLIKELY RELATED',
    'POSSIBLE': 'POSSIBLY RELATED',
    'PROBABLE': 'PROBABLY RELATED',
    'RELATED': 'RELATED',
    '1': 'NOT RELATED',
    '2': 'UNLIKELY RELATED',
    '3': 'POSSIBLY RELATED',
    '4': 'PROBABLY RELATED',
}

OUTCOME_MAP = {
    'RESOLVED': 'RECOVERED/RESOLVED',
    'CONTINUING': 'NOT RECOVERED/NOT RESOLVED',
    'PATIENT DIED': 'FATAL',
    'RESOLVED, WITH RESIDUAL EFFECTS': 'RECOVERED/RESOLVED WITH SEQUELAE',
}

ACTION_MAP = {
    'NONE': 'DOSE NOT CHANGED',
    'INTERRUPTED': 'DRUG INTERRUPTED',
    'DISCONTINUED': 'DRUG WITHDRAWN',
    '1': 'DOSE NOT CHANGED',
    '2': 'DRUG INTERRUPTED',
    '3': 'DOSE NOT CHANGED',
    '5': 'DRUG WITHDRAWN',
}

def clean_text(text):
    if pd.isna(text) or text == '':
        return ''
    return str(text).strip().upper()

def map_ct(value, mapping):
    cleaned = clean_text(value)
    return mapping.get(cleaned, cleaned if cleaned else '')

# ===========================
# Main Transformation
# ===========================

# Read source data
print("=" * 90)
print("SDTM AE DOMAIN TRANSFORMATION - COMPREHENSIVE")
print("Following CDISC SDTM-IG 3.4")
print("=" * 90)

source_file = "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/source_data/Maxis-08 RAW DATA_CSV/AEVENT.csv"
output_file = "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_sdtm_transformed.csv"

print(f"\n📂 Reading source data: AEVENT.csv")
df_source = pd.read_csv(source_file, encoding='utf-8-sig')
print(f"   ✓ Source records: {len(df_source)}")
print(f"   ✓ Source columns: {len(df_source.columns)}")

# Initialize SDTM AE
df_ae = pd.DataFrame()

print(f"\n🔄 Transforming data to SDTM AE domain...")

# ===== REQUIRED VARIABLES =====
df_ae['STUDYID'] = df_source['STUDY'].apply(clean_text)
df_ae['DOMAIN'] = 'AE'
df_ae['USUBJID'] = df_source.apply(
    lambda row: f"{clean_text(row['STUDY'])}-{clean_text(row['INVSITE'])}", 
    axis=1
)
df_ae['AESEQ'] = df_source['AESEQ'].astype(int)
df_ae['AETERM'] = df_source['AEVERB'].apply(clean_text)

# ===== EXPECTED VARIABLES =====
df_ae['AEDECOD'] = df_source['AEPTT'].apply(clean_text)
df_ae['AEBODSYS'] = df_source['AESCT'].apply(clean_text)
df_ae['AESTDTC'] = df_source['AESTDT'].apply(to_iso8601_date)
df_ae['AEENDTC'] = df_source['AEENDT'].apply(to_iso8601_date)

# ===== PERMISSIBLE VARIABLES (with Controlled Terminology) =====
df_ae['AESEV'] = df_source['AESEV'].apply(lambda x: map_ct(x, SEVERITY_MAP))
df_ae['AESER'] = df_source['AESERL'].apply(lambda x: map_ct(x, SERIOUS_MAP))
df_ae['AEREL'] = df_source['AEREL'].apply(lambda x: map_ct(x, CAUSALITY_MAP))
df_ae['AEOUT'] = df_source['AEOUTCL'].apply(lambda x: map_ct(x, OUTCOME_MAP))
df_ae['AEACN'] = df_source['AEACTL'].apply(lambda x: map_ct(x, ACTION_MAP))

# ===== SERIOUS EVENT FLAGS =====
df_ae['AESCONG'] = ''
df_ae['AESDISAB'] = ''
df_ae['AESDTH'] = df_source['AEOUTCL'].apply(
    lambda x: 'Y' if 'DIED' in str(x).upper() else ''
)
df_ae['AESHOSP'] = df_source['AESERL'].apply(
    lambda x: 'Y' if 'HOSPITALIZATION' in str(x).upper() else ''
)
df_ae['AESLIFE'] = df_source['AESEV'].apply(
    lambda x: 'Y' if 'LIFE THREATENING' in str(x).upper() else ''
)
df_ae['AESMIE'] = ''

# Sort by USUBJID and AESEQ
df_ae = df_ae.sort_values(['USUBJID', 'AESEQ']).reset_index(drop=True)

# Save output
print(f"\n💾 Saving SDTM AE dataset...")
df_ae.to_csv(output_file, index=False, encoding='utf-8')
print(f"   ✓ Output saved: {output_file}")

# ===========================
# TRANSFORMATION SUMMARY
# ===========================

print("\n" + "=" * 90)
print("TRANSFORMATION SUMMARY")
print("=" * 90)

print(f"\n📊 RECORD COUNTS:")
print(f"   • Records transformed: {len(df_ae)}")
print(f"   • Unique subjects: {df_ae['USUBJID'].nunique()}")
print(f"   • Events per subject (avg): {len(df_ae) / df_ae['USUBJID'].nunique():.1f}")

subjects = df_ae['USUBJID'].unique()[:5]
print(f"\n   Sample subjects: {', '.join(subjects)}")

# ===========================
# CONTROLLED TERMINOLOGY MAPPINGS
# ===========================

print(f"\n📋 CONTROLLED TERMINOLOGY MAPPINGS APPLIED:")

print(f"\n   AESEV (Severity/Intensity):")
sev_counts = df_ae['AESEV'].value_counts().sort_index()
for val, count in sev_counts.items():
    pct = (count / len(df_ae)) * 100
    print(f"      • {val:20s} : {count:4d} ({pct:5.1f}%)")

print(f"\n   AESER (Serious Event Flag):")
ser_counts = df_ae['AESER'].value_counts().sort_index()
for val, count in ser_counts.items():
    pct = (count / len(df_ae)) * 100
    print(f"      • {val:20s} : {count:4d} ({pct:5.1f}%)")

print(f"\n   AEREL (Causality Assessment):")
rel_counts = df_ae['AEREL'].value_counts().sort_index()
for val, count in rel_counts.items():
    pct = (count / len(df_ae)) * 100
    print(f"      • {val:20s} : {count:4d} ({pct:5.1f}%)")

print(f"\n   AEOUT (Outcome):")
out_counts = df_ae['AEOUT'].value_counts().sort_index()
for val, count in out_counts.items():
    pct = (count / len(df_ae)) * 100
    print(f"      • {val:30s} : {count:4d} ({pct:5.1f}%)")

print(f"\n   AEACN (Action Taken with Study Treatment):")
acn_counts = df_ae['AEACN'].value_counts().sort_index()
for val, count in acn_counts.items():
    pct = (count / len(df_ae)) * 100
    print(f"      • {val:20s} : {count:4d} ({pct:5.1f}%)")

# ===========================
# SERIOUS EVENT FLAGS SUMMARY
# ===========================

print(f"\n🚨 SERIOUS EVENT FLAGS:")
serious_count = (df_ae['AESER'] == 'Y').sum()
print(f"   • Total serious events: {serious_count}")

if serious_count > 0:
    print(f"   • Deaths (AESDTH=Y): {(df_ae['AESDTH'] == 'Y').sum()}")
    print(f"   • Hospitalizations (AESHOSP=Y): {(df_ae['AESHOSP'] == 'Y').sum()}")
    print(f"   • Life threatening (AESLIFE=Y): {(df_ae['AESLIFE'] == 'Y').sum()}")

# ===========================
# DATA QUALITY CHECKS
# ===========================

print(f"\n✅ DATA QUALITY ASSESSMENT:")

issues = []

# Required variables check
required_vars = ['STUDYID', 'DOMAIN', 'USUBJID', 'AESEQ', 'AETERM']
print(f"\n   Required Variables:")
for var in required_vars:
    null_count = df_ae[var].isna().sum() + (df_ae[var] == '').sum()
    if null_count > 0:
        print(f"      ⚠️  {var}: {null_count} missing values (CRITICAL)")
        issues.append(f"{var} has {null_count} missing values")
    else:
        print(f"      ✓ {var}: Complete")

# Expected variables check
print(f"\n   Expected Variables:")
expected_vars = ['AEDECOD', 'AEBODSYS', 'AESTDTC']
for var in expected_vars:
    null_count = (df_ae[var] == '').sum()
    if null_count > 0:
        print(f"      ⚠️  {var}: {null_count} missing ({(null_count/len(df_ae)*100):.1f}%)")
        issues.append(f"{var} has {null_count} missing values")
    else:
        print(f"      ✓ {var}: Complete")

# Date format validation
print(f"\n   Date Format Validation (ISO 8601):")
invalid_start = df_ae[
    (df_ae['AESTDTC'] != '') & 
    ~df_ae['AESTDTC'].str.match(r'^\d{4}(-\d{2}(-\d{2})?)?$')
].shape[0]
if invalid_start > 0:
    print(f"      ⚠️  AESTDTC: {invalid_start} invalid formats")
    issues.append(f"AESTDTC has {invalid_start} invalid date formats")
else:
    print(f"      ✓ AESTDTC: All dates in ISO 8601 format")

invalid_end = df_ae[
    (df_ae['AEENDTC'] != '') & 
    ~df_ae['AEENDTC'].str.match(r'^\d{4}(-\d{2}(-\d{2})?)?$')
].shape[0]
if invalid_end > 0:
    print(f"      ⚠️  AEENDTC: {invalid_end} invalid formats")
    issues.append(f"AEENDTC has {invalid_end} invalid date formats")
else:
    print(f"      ✓ AEENDTC: All dates in ISO 8601 format")

# Serious event logic check
print(f"\n   Serious Event Logic:")
serious_no_flags = df_ae[
    (df_ae['AESER'] == 'Y') & 
    (df_ae['AESHOSP'] == '') &
    (df_ae['AESDTH'] == '') &
    (df_ae['AESLIFE'] == '') &
    (df_ae['AESDISAB'] == '') &
    (df_ae['AESCONG'] == '') &
    (df_ae['AESMIE'] == '')
].shape[0]
if serious_no_flags > 0:
    print(f"      ⚠️  {serious_no_flags} serious events without specific reason flags")
    issues.append(f"{serious_no_flags} serious events lack specific reason flags")
else:
    print(f"      ✓ All serious events have reason flags")

# ===========================
# FINAL STATUS
# ===========================

print("\n" + "=" * 90)
if len(issues) == 0:
    print("✅ TRANSFORMATION COMPLETED SUCCESSFULLY - NO ISSUES DETECTED")
else:
    print(f"⚠️  TRANSFORMATION COMPLETED WITH {len(issues)} DATA QUALITY ISSUE(S):")
    for i, issue in enumerate(issues, 1):
        print(f"   {i}. {issue}")

print("=" * 90)
print(f"\n📁 Output file: {output_file}")
print(f"📋 Total records: {len(df_ae)}")
print(f"👥 Total subjects: {df_ae['USUBJID'].nunique()}")
print("\n" + "=" * 90 + "\n")

# Write a summary report file
summary_file = "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_transformation_report.txt"
with open(summary_file, 'w') as f:
    f.write("=" * 90 + "\n")
    f.write("SDTM AE TRANSFORMATION REPORT\n")
    f.write("=" * 90 + "\n\n")
    f.write(f"Source File: {source_file}\n")
    f.write(f"Output File: {output_file}\n")
    f.write(f"Transformation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    f.write(f"Records Transformed: {len(df_ae)}\n")
    f.write(f"Unique Subjects: {df_ae['USUBJID'].nunique()}\n\n")
    f.write("=" * 90 + "\n")

print(f"📄 Summary report saved: {summary_file}\n")

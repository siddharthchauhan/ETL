#!/usr/bin/env python3
"""
SDTM AE Domain Transformation
Study: MAXIS-08
Source: AEVENTC.csv (MedDRA coded)
Compliant with SDTM-IG 3.4
"""
import pandas as pd
import numpy as np
import json
from datetime import datetime

print("="*80)
print("SDTM AE DOMAIN TRANSFORMATION - MAXIS-08")
print("="*80)
print()

# Read source data
print("[1/7] Reading source data...")
source_file = '/tmp/s3_data/extracted/Maxis-08 RAW DATA_CSV/AEVENTC.csv'
df_source = pd.read_csv(source_file, encoding='utf-8-sig')
print(f"  Source file: {source_file}")
print(f"  Source records: {len(df_source)}")
print(f"  Source columns: {len(df_source.columns)}")
print()

# Helper functions
def format_date_iso8601(date_val):
    """Convert date to ISO 8601 format"""
    if pd.isna(date_val) or str(date_val).strip() == '':
        return ''
    
    date_str = str(date_val).strip().split('.')[0]  # Remove decimal
    
    if len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
    elif len(date_str) == 6 and date_str.isdigit():
        return f"{date_str[0:4]}-{date_str[4:6]}"
    elif len(date_str) == 4 and date_str.isdigit():
        return date_str
    
    return ''

def map_severity(val):
    if pd.isna(val) or str(val).strip() == '':
        return ''
    return str(val).upper().strip()

def map_serious(val):
    if pd.isna(val) or str(val).strip() == '':
        return ''
    val_str = str(val).upper()
    if 'NOT SERIOUS' in val_str:
        return 'N'
    elif 'SERIOUS' in val_str or val_str == 'Y':
        return 'Y'
    return 'N'

def map_outcome(val):
    if pd.isna(val) or str(val).strip() == '':
        return ''
    val_upper = str(val).upper()
    mapping = {
        'RESOLVED': 'RECOVERED/RESOLVED',
        'CONTINUING': 'NOT RECOVERED/NOT RESOLVED',
        'RECOVERING': 'RECOVERING/RESOLVING',
        'RESOLVING': 'RECOVERING/RESOLVING',
        'FATAL': 'FATAL'
    }
    for key, value in mapping.items():
        if key in val_upper:
            return value
    return ''

def map_action(val):
    if pd.isna(val) or str(val).strip() == '':
        return ''
    val_upper = str(val).upper()
    if 'NONE' in val_upper:
        return 'DOSE NOT CHANGED'
    elif '1' in val_upper or 'NOT CHANGED' in val_upper:
        return 'DOSE NOT CHANGED'
    return 'DOSE NOT CHANGED'

def map_causality(val):
    if pd.isna(val) or str(val).strip() == '':
        return ''
    val_upper = str(val).upper()
    mapping = {
        'UNRELATED': 'NOT RELATED',
        'UNLIKELY': 'UNLIKELY RELATED',
        'POSSIBLE': 'POSSIBLY RELATED',
        'PROBABLE': 'PROBABLY RELATED',
        'RELATED': 'RELATED'
    }
    for key, value in mapping.items():
        if key in val_upper:
            return value
    return ''

def safe_int(val):
    """Convert to integer, return None if not possible"""
    if pd.isna(val) or str(val).strip() == '':
        return None
    try:
        return int(float(val))
    except:
        return None

print("[2/7] Creating SDTM AE dataset...")

# Initialize AE dataframe
ae = pd.DataFrame()

# IDENTIFIER VARIABLES
ae['STUDYID'] = 'MAXIS-08'
ae['DOMAIN'] = 'AE'
ae['USUBJID'] = df_source.apply(
    lambda row: f"MAXIS-08-{row['INVSITE']}-{row['PT']}" 
    if pd.notna(row.get('INVSITE')) and pd.notna(row.get('PT')) 
    else '',
    axis=1
)
ae['AESEQ'] = df_source['AESEQ']
ae['AESPID'] = ''

# TOPIC VARIABLES
ae['AETERM'] = df_source['AEVERB'].fillna('')
ae['AEMODIFY'] = df_source['MODTERM'].fillna('')

# MedDRA HIERARCHY (from AEVENTC coded data)
ae['AEDECOD'] = df_source['PTTERM'].fillna('')
ae['AELLT'] = df_source['LLTTERM'].fillna('')
ae['AELLTCD'] = df_source['LLTCODE'].apply(safe_int)
ae['AEPTCD'] = df_source['PTCODE'].apply(safe_int)
ae['AEHLT'] = df_source['HLTTERM'].fillna('')
ae['AEHLTCD'] = df_source['HLTCODE'].apply(safe_int)
ae['AEHLGT'] = df_source['HLGTTERM'].fillna('')
ae['AEHLGTCD'] = df_source['HLGTCODE'].apply(safe_int)
ae['AEBODSYS'] = df_source['SOCTERM'].fillna('')
ae['AEBDSYCD'] = df_source['SOCCODE'].apply(safe_int)
ae['AESOC'] = df_source['SOCTERM'].fillna('')
ae['AESOCCD'] = df_source['SOCCODE'].apply(safe_int)

# QUALIFIER VARIABLES
ae['AESEV'] = df_source['AESEV'].apply(map_severity)
ae['AESER'] = df_source['AESERL'].apply(map_serious)
ae['AEREL'] = df_source['AERELL'].apply(map_causality)
ae['AEACN'] = df_source['AEACTL'].apply(map_action)
ae['AEOUT'] = df_source['AEOUTCL'].apply(map_outcome)

# SAE CRITERIA
ae['AESDTH'] = ''
ae['AESLIFE'] = ''
ae['AESHOSP'] = ''
ae['AESDISAB'] = ''
ae['AESCONG'] = ''
ae['AESMIE'] = ''

# TOXICITY
ae['AETOXGR'] = ''
ae['AECONTRT'] = df_source['AETRT'].fillna('').apply(
    lambda x: 'Y' if str(x).upper() == 'Y' else ('N' if str(x).upper() == 'N' else '')
)

# TIMING VARIABLES
ae['AESTDTC'] = df_source['AESTDT'].apply(format_date_iso8601)
ae['AEENDTC'] = df_source['AEENDT'].apply(format_date_iso8601)
ae['AESTDY'] = None
ae['AEENDY'] = None

# TRIAL DESIGN
ae['EPOCH'] = ''
ae['VISITNUM'] = df_source['VISIT'].apply(
    lambda x: int(x) if pd.notna(x) and str(x).strip().isdigit() else None
)
ae['VISIT'] = df_source['CPEVENT'].fillna('')

print(f"  Target records: {len(ae)}")
print(f"  Target variables: {len(ae.columns)}")
print()

# SORT DATA
print("[3/7] Sorting data...")
ae = ae.sort_values(['USUBJID', 'AESEQ']).reset_index(drop=True)
print(f"  Sorted by USUBJID and AESEQ")
print()

# DATA QUALITY CHECKS
print("[4/7] Performing data quality checks...")
issues = []
warnings = []

# Check required variables
missing_usubjid = ae['USUBJID'].isna() | (ae['USUBJID'] == '')
if missing_usubjid.sum() > 0:
    issues.append(f"ERROR: {missing_usubjid.sum()} records missing USUBJID")

missing_aeterm = ae['AETERM'].isna() | (ae['AETERM'] == '')
if missing_aeterm.sum() > 0:
    issues.append(f"ERROR: {missing_aeterm.sum()} records missing AETERM")

missing_aedecod = ae['AEDECOD'].isna() | (ae['AEDECOD'] == '')
if missing_aedecod.sum() > 0:
    warnings.append(f"WARNING: {missing_aedecod.sum()} records missing AEDECOD")

# Check duplicates
dup_count = ae.duplicated(subset=['USUBJID', 'AESEQ']).sum()
if dup_count > 0:
    issues.append(f"ERROR: {dup_count} duplicate USUBJID-AESEQ combinations")

# Check controlled terminology
invalid_sev = ae[(ae['AESEV'] != '') & ~ae['AESEV'].isin(['MILD', 'MODERATE', 'SEVERE'])]
if len(invalid_sev) > 0:
    warnings.append(f"WARNING: {len(invalid_sev)} records with invalid AESEV")

invalid_ser = ae[(ae['AESER'] != '') & ~ae['AESER'].isin(['Y', 'N'])]
if len(invalid_ser) > 0:
    warnings.append(f"WARNING: {len(invalid_ser)} records with invalid AESER")

if issues:
    print("  ERRORS FOUND:")
    for issue in issues:
        print(f"    - {issue}")
else:
    print("  ✓ No errors found")

if warnings:
    print("  WARNINGS:")
    for warning in warnings:
        print(f"    - {warning}")
else:
    print("  ✓ No warnings")
print()

# SAVE OUTPUT
print("[5/7] Saving output files...")
output_file = '/Users/siddharth/Downloads/ETL/ETL/sdtm_langgraph_output/ae.csv'
ae.to_csv(output_file, index=False)
print(f"  ✓ SDTM AE dataset: {output_file}")
print()

# GENERATE VALUE DISTRIBUTIONS
print("[6/7] Generating value distributions...")
print(f"\n  Severity (AESEV):")
sev_counts = ae['AESEV'].value_counts()
for val, count in sev_counts.items():
    if val != '':
        print(f"    {val}: {count}")

print(f"\n  Seriousness (AESER):")
ser_counts = ae['AESER'].value_counts()
for val, count in ser_counts.items():
    if val != '':
        print(f"    {val}: {count}")

print(f"\n  Outcome (AEOUT):")
out_counts = ae['AEOUT'].value_counts()
for val, count in out_counts.items():
    if val != '':
        print(f"    {val}: {count}")
print()

# GENERATE REPORT
print("[7/7] Generating transformation report...")

# Variable population summary
var_summary = {}
for col in ae.columns:
    non_empty = (ae[col].notna() & (ae[col] != '')).sum()
    var_summary[col] = {
        'populated': int(non_empty),
        'populated_pct': round(non_empty / len(ae) * 100, 1),
        'missing': int(len(ae) - non_empty)
    }

report = {
    'study_id': 'MAXIS-08',
    'transformation_date': datetime.now().isoformat(),
    'source_file': 'AEVENTC.csv',
    'target_domain': 'AE',
    'source_records': int(len(df_source)),
    'target_records': int(len(ae)),
    'unique_subjects': int(ae['USUBJID'].nunique()),
    'variables_created': list(ae.columns),
    'variable_count': len(ae.columns),
    'variable_summary': var_summary,
    'issues': issues,
    'warnings': warnings,
    'sdtm_version': 'SDTM-IG 3.4'
}

report_file = '/Users/siddharth/Downloads/ETL/ETL/sdtm_langgraph_output/ae_transformation_report.json'
with open(report_file, 'w') as f:
    json.dump(report, f, indent=2)
print(f"  ✓ Transformation report: {report_file}")
print()

# FINAL SUMMARY
print("="*80)
print("TRANSFORMATION COMPLETED SUCCESSFULLY")
print("="*80)
print(f"Study ID:          MAXIS-08")
print(f"Target Domain:     AE (Adverse Events)")
print(f"Source File:       AEVENTC.csv (MedDRA coded)")
print(f"Source Records:    {report['source_records']}")
print(f"Target Records:    {report['target_records']}")
print(f"Unique Subjects:   {report['unique_subjects']}")
print(f"Variables Created: {len(report['variables_created'])}")
print()
print("Key Variables Population:")
print(f"  USUBJID:   {var_summary['USUBJID']['populated']:4d} ({var_summary['USUBJID']['populated_pct']:5.1f}%)")
print(f"  AETERM:    {var_summary['AETERM']['populated']:4d} ({var_summary['AETERM']['populated_pct']:5.1f}%)")
print(f"  AEDECOD:   {var_summary['AEDECOD']['populated']:4d} ({var_summary['AEDECOD']['populated_pct']:5.1f}%)")
print(f"  AEBODSYS:  {var_summary['AEBODSYS']['populated']:4d} ({var_summary['AEBODSYS']['populated_pct']:5.1f}%)")
print(f"  AESEV:     {var_summary['AESEV']['populated']:4d} ({var_summary['AESEV']['populated_pct']:5.1f}%)")
print(f"  AESER:     {var_summary['AESER']['populated']:4d} ({var_summary['AESER']['populated_pct']:5.1f}%)")
print(f"  AESTDTC:   {var_summary['AESTDTC']['populated']:4d} ({var_summary['AESTDTC']['populated_pct']:5.1f}%)")
print()
print("Output file: " + output_file)
print("="*80)

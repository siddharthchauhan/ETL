#!/usr/bin/env python3
"""
SDTM AE Domain Transformation - Final Version
Transforms source AEVENT.csv to SDTM AE domain following CDISC SDTM-IG 3.4
"""

import pandas as pd
import numpy as np
from datetime import datetime
import re
import sys

def to_iso8601_date(date_value):
    """Convert various date formats to ISO 8601 (YYYY-MM-DD)."""
    if pd.isna(date_value) or date_value == '':
        return ''
    
    if isinstance(date_value, (pd.Timestamp, datetime)):
        return date_value.strftime('%Y-%m-%d')
    
    if isinstance(date_value, (int, float)):
        str_val = str(int(date_value))
        if len(str_val) == 8:
            try:
                return datetime.strptime(str_val, '%Y%m%d').strftime('%Y-%m-%d')
            except ValueError:
                return ''
        elif len(str_val) == 6:
            try:
                return datetime.strptime(str_val, '%Y%m').strftime('%Y-%m')
            except ValueError:
                return ''
    
    date_str = str(date_value).strip()
    
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    if re.match(r'^\d{4}-\d{2}$', date_str):
        return date_str
    if re.match(r'^\d{4}$', date_str):
        return date_str
    
    if re.match(r'^\d{8}$', date_str):
        try:
            return datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
        except ValueError:
            return ''
    
    if re.match(r'^\d{6}$', date_str):
        try:
            return datetime.strptime(date_str, '%Y%m').strftime('%Y-%m')
        except ValueError:
            return ''
    
    return ''

# Controlled Terminology Mappings
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
    """Clean and standardize text values."""
    if pd.isna(text) or text == '':
        return ''
    return str(text).strip().upper()

def map_ct(value, mapping):
    """Map value using controlled terminology mapping."""
    cleaned = clean_text(value)
    return mapping.get(cleaned, cleaned if cleaned else '')

def main():
    source_file = "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/source_data/Maxis-08 RAW DATA_CSV/AEVENT.csv"
    output_file = "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_sdtm_transformed.csv"
    
    print("=" * 80)
    print("SDTM AE Domain Transformation")
    print("=" * 80)
    
    # Read source data
    print(f"\n1. Reading source data...")
    df_source = pd.read_csv(source_file, encoding='utf-8-sig')
    print(f"   Source records: {len(df_source)}")
    
    # Initialize SDTM AE dataframe
    df_ae = pd.DataFrame()
    
    print("\n2. Transforming to SDTM AE domain...")
    
    # Required Variables
    df_ae['STUDYID'] = df_source['STUDY'].apply(clean_text)
    df_ae['DOMAIN'] = 'AE'
    df_ae['USUBJID'] = df_source.apply(
        lambda row: f"{clean_text(row['STUDY'])}-{clean_text(row['INVSITE'])}", 
        axis=1
    )
    df_ae['AESEQ'] = df_source['AESEQ'].astype(int)
    df_ae['AETERM'] = df_source['AEVERB'].apply(clean_text)
    
    # Expected Variables
    df_ae['AEDECOD'] = df_source['AEPTT'].apply(clean_text)
    df_ae['AEBODSYS'] = df_source['AESCT'].apply(clean_text)
    df_ae['AESTDTC'] = df_source['AESTDT'].apply(to_iso8601_date)
    df_ae['AEENDTC'] = df_source['AEENDT'].apply(to_iso8601_date)
    
    # Permissible Variables with Controlled Terminology
    df_ae['AESEV'] = df_source['AESEV'].apply(lambda x: map_ct(x, SEVERITY_MAP))
    df_ae['AESER'] = df_source['AESERL'].apply(lambda x: map_ct(x, SERIOUS_MAP))
    df_ae['AEREL'] = df_source['AEREL'].apply(lambda x: map_ct(x, CAUSALITY_MAP))
    df_ae['AEOUT'] = df_source['AEOUTCL'].apply(lambda x: map_ct(x, OUTCOME_MAP))
    df_ae['AEACN'] = df_source['AEACTL'].apply(lambda x: map_ct(x, ACTION_MAP))
    
    # Serious Event Flags
    df_ae['AESCONG'] = ''
    df_ae['AESDISAB'] = ''
    df_ae['AESDTH'] = df_source['AEOUTCL'].apply(lambda x: 'Y' if 'DIED' in str(x).upper() else '')
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
    print(f"\n3. Saving SDTM AE dataset...")
    df_ae.to_csv(output_file, index=False, encoding='utf-8')
    
    # Summary Statistics
    print("\n" + "=" * 80)
    print("TRANSFORMATION SUMMARY")
    print("=" * 80)
    print(f"\n✓ Records transformed: {len(df_ae)}")
    print(f"✓ Unique subjects: {df_ae['USUBJID'].nunique()}")
    print(f"✓ Output file: {output_file}")
    
    print("\n--- Controlled Terminology Mappings Applied ---")
    
    print(f"\nAESEV (Severity) Distribution:")
    sev_counts = df_ae['AESEV'].value_counts()
    for val, count in sev_counts.items():
        print(f"  {val}: {count}")
    
    print(f"\nAESER (Serious Event) Distribution:")
    ser_counts = df_ae['AESER'].value_counts()
    for val, count in ser_counts.items():
        print(f"  {val}: {count}")
    
    print(f"\nAEREL (Causality) Distribution:")
    rel_counts = df_ae['AEREL'].value_counts()
    for val, count in rel_counts.items():
        print(f"  {val}: {count}")
    
    print(f"\nAEOUT (Outcome) Distribution:")
    out_counts = df_ae['AEOUT'].value_counts()
    for val, count in out_counts.items():
        print(f"  {val}: {count}")
    
    print(f"\nAEACN (Action Taken) Distribution:")
    acn_counts = df_ae['AEACN'].value_counts()
    for val, count in acn_counts.items():
        print(f"  {val}: {count}")
    
    # Data Quality Checks
    print("\n--- Data Quality Checks ---")
    
    issues = []
    
    # Check required variables
    required_vars = ['STUDYID', 'DOMAIN', 'USUBJID', 'AESEQ', 'AETERM']
    for var in required_vars:
        null_count = df_ae[var].isna().sum() + (df_ae[var] == '').sum()
        if null_count > 0:
            issues.append(f"  ⚠ {var}: {null_count} missing values")
    
    # Check AEDECOD (Expected variable)
    aedecod_missing = (df_ae['AEDECOD'] == '').sum()
    if aedecod_missing > 0:
        issues.append(f"  ⚠ AEDECOD: {aedecod_missing} missing (Expected variable)")
    
    # Check date formats
    invalid_start = df_ae[
        (df_ae['AESTDTC'] != '') & 
        ~df_ae['AESTDTC'].str.match(r'^\d{4}(-\d{2}(-\d{2})?)?$')
    ].shape[0]
    if invalid_start > 0:
        issues.append(f"  ⚠ AESTDTC: {invalid_start} invalid ISO 8601 formats")
    
    # Check serious event logic
    serious_no_flags = df_ae[
        (df_ae['AESER'] == 'Y') & 
        (df_ae['AESHOSP'] == '') &
        (df_ae['AESDTH'] == '') &
        (df_ae['AESLIFE'] == '')
    ].shape[0]
    if serious_no_flags > 0:
        issues.append(f"  ⚠ {serious_no_flags} serious events without specific flags")
    
    if issues:
        for issue in issues:
            print(issue)
    else:
        print("  ✓ No data quality issues detected")
    
    print("\n" + "=" * 80)
    print("Transformation completed successfully!")
    print("=" * 80 + "\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

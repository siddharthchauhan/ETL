"""
SDTM AE Domain Transformation Script
Transforms source AEVENT.csv to SDTM AE domain following CDISC SDTM-IG 3.4
"""

import pandas as pd
import numpy as np
from datetime import datetime
import re

# ===========================
# ISO 8601 Date Conversion
# ===========================

def to_iso8601_date(date_value):
    """
    Convert various date formats to ISO 8601 (YYYY-MM-DD).
    
    Handles:
    - 20240115 (YYYYMMDD)
    - 200809 (YYYYMM - partial date)
    - Already ISO format
    - Empty/NaN values
    """
    if pd.isna(date_value) or date_value == '':
        return ''
    
    # Handle pandas Timestamp / datetime objects
    if isinstance(date_value, (pd.Timestamp, datetime)):
        return date_value.strftime('%Y-%m-%d')
    
    # Handle numeric YYYYMMDD or YYYYMM
    if isinstance(date_value, (int, float)):
        str_val = str(int(date_value))
        if len(str_val) == 8:
            try:
                return datetime.strptime(str_val, '%Y%m%d').strftime('%Y-%m-%d')
            except ValueError:
                pass
        elif len(str_val) == 6:
            try:
                return datetime.strptime(str_val, '%Y%m').strftime('%Y-%m')
            except ValueError:
                pass
    
    date_str = str(date_value).strip()
    
    # Already ISO 8601 format
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    if re.match(r'^\d{4}-\d{2}$', date_str):
        return date_str
    if re.match(r'^\d{4}$', date_str):
        return date_str
    
    # Handle YYYYMMDD format
    if re.match(r'^\d{8}$', date_str):
        try:
            return datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
        except ValueError:
            pass
    
    # Handle YYYYMM format (partial date)
    if re.match(r'^\d{6}$', date_str):
        try:
            return datetime.strptime(date_str, '%Y%m').strftime('%Y-%m')
        except ValueError:
            pass
    
    return ''

# ===========================
# Controlled Terminology Mappings
# ===========================

# AESEV - Severity Mapping (CDISC CT)
SEVERITY_MAP = {
    'MILD': 'MILD',
    'MODERATE': 'MODERATE',
    'SEVERE': 'SEVERE',
    'LIFE THREATENING': 'LIFE THREATENING',
    'FATAL': 'FATAL'
}

# AESER - Serious Event Mapping
SERIOUS_MAP = {
    'NOT SERIOUS': 'N',
    'UNLIKELY': 'N',
    'HOSPITALIZATION/PROLONGATION': 'Y',
}

# AEREL - Causality Mapping (CDISC CT)
CAUSALITY_MAP = {
    'UNRELATED': 'NOT RELATED',
    'UNLIKELY': 'UNLIKELY RELATED',
    'POSSIBLE': 'POSSIBLY RELATED',
    'PROBABLE': 'PROBABLY RELATED',
    'RELATED': 'RELATED',
    'NOT RELATED': 'NOT RELATED',
    '1': 'NOT RELATED',
    '2': 'UNLIKELY RELATED',
    '3': 'POSSIBLY RELATED',
    '4': 'PROBABLY RELATED',
}

# AEOUT - Outcome Mapping (CDISC CT)
OUTCOME_MAP = {
    'RESOLVED': 'RECOVERED/RESOLVED',
    'CONTINUING': 'NOT RECOVERED/NOT RESOLVED',
    'PATIENT DIED': 'FATAL',
    'RESOLVED, WITH RESIDUAL EFFECTS': 'RECOVERED/RESOLVED WITH SEQUELAE',
    'FATAL': 'FATAL'
}

# AEACN - Action Taken Mapping (CDISC CT)
ACTION_MAP = {
    'NONE': 'DOSE NOT CHANGED',
    'INTERRUPTED': 'DRUG INTERRUPTED',
    'DISCONTINUED': 'DRUG WITHDRAWN',
    '1': 'DOSE NOT CHANGED',
    '2': 'DRUG INTERRUPTED',
    '3': 'DOSE NOT CHANGED',
    '4': 'DRUG WITHDRAWN',
    '5': 'DRUG WITHDRAWN',
}

# ===========================
# Helper Functions
# ===========================

def clean_text(text):
    """Clean and standardize text values."""
    if pd.isna(text) or text == '':
        return ''
    return str(text).strip().upper()

def map_severity(severity_raw):
    """Map source severity to CDISC CT AESEV."""
    severity = clean_text(severity_raw)
    return SEVERITY_MAP.get(severity, severity)

def map_serious(serious_raw):
    """Map source serious flag to Y/N."""
    serious = clean_text(serious_raw)
    return SERIOUS_MAP.get(serious, 'N')

def map_causality(causality_raw):
    """Map source causality to CDISC CT AEREL."""
    causality = clean_text(causality_raw)
    return CAUSALITY_MAP.get(causality, causality)

def map_outcome(outcome_raw):
    """Map source outcome to CDISC CT AEOUT."""
    outcome = clean_text(outcome_raw)
    return OUTCOME_MAP.get(outcome, outcome)

def map_action(action_raw):
    """Map source action taken to CDISC CT AEACN."""
    action = clean_text(action_raw)
    return ACTION_MAP.get(action, 'DOSE NOT CHANGED')

def derive_usubjid(study_id, subject_id):
    """Derive USUBJID from STUDYID and SUBJID."""
    return f"{study_id}-{subject_id}"

def determine_serious_flags(serious_code):
    """Determine individual serious event flags based on AESERL code."""
    # Initialize all flags to blank
    flags = {
        'AESCONG': '',
        'AESDISAB': '',
        'AESDTH': '',
        'AESHOSP': '',
        'AESLIFE': '',
        'AESMIE': ''
    }
    
    serious_code = str(serious_code).strip()
    
    if serious_code == '5':
        flags['AESHOSP'] = 'Y'
    
    return flags

# ===========================
# Main Transformation Function
# ===========================

def transform_ae_to_sdtm(source_file, output_file):
    """
    Transform source AEVENT.csv to SDTM AE domain.
    
    Args:
        source_file: Path to source AEVENT.csv
        output_file: Path to save transformed AE.csv
        
    Returns:
        dict: Transformation summary statistics
    """
    
    print("=" * 80)
    print("SDTM AE Domain Transformation")
    print("=" * 80)
    
    # Read source data
    print(f"\n1. Reading source data from: {source_file}")
    df_source = pd.read_csv(source_file, encoding='utf-8-sig')
    print(f"   Source records: {len(df_source)}")
    print(f"   Source columns: {list(df_source.columns)}")
    
    # Initialize SDTM AE dataframe
    df_ae = pd.DataFrame()
    
    # ===========================
    # REQUIRED VARIABLES
    # ===========================
    
    print("\n2. Mapping Required Variables...")
    
    # STUDYID - Study Identifier
    df_ae['STUDYID'] = df_source['STUDY'].apply(clean_text)
    
    # DOMAIN - Domain Abbreviation
    df_ae['DOMAIN'] = 'AE'
    
    # USUBJID - Unique Subject Identifier
    df_ae['USUBJID'] = df_source.apply(
        lambda row: derive_usubjid(clean_text(row['STUDY']), clean_text(row['INVSITE'])), 
        axis=1
    )
    
    # AESEQ - Sequence Number
    df_ae['AESEQ'] = df_source['AESEQ'].astype(int)
    
    # AETERM - Reported Term (verbatim)
    df_ae['AETERM'] = df_source['AEVERB'].apply(clean_text)
    
    # ===========================
    # EXPECTED VARIABLES
    # ===========================
    
    print("3. Mapping Expected Variables...")
    
    # AEDECOD - Dictionary-Derived Term (MedDRA PT)
    df_ae['AEDECOD'] = df_source['AEPTT'].apply(clean_text)
    
    # AEBODSYS - Body System or Organ Class (MedDRA SOC)
    df_ae['AEBODSYS'] = df_source['AESCT'].apply(clean_text)
    
    # AESTDTC - Start Date/Time (ISO 8601)
    df_ae['AESTDTC'] = df_source['AESTDT'].apply(to_iso8601_date)
    
    # AEENDTC - End Date/Time (ISO 8601)
    df_ae['AEENDTC'] = df_source['AEENDT'].apply(to_iso8601_date)
    
    # ===========================
    # PERMISSIBLE VARIABLES
    # ===========================
    
    print("4. Mapping Permissible Variables (Controlled Terminology)...")
    
    # AESEV - Severity/Intensity
    df_ae['AESEV'] = df_source['AESEV'].apply(map_severity)
    
    # AESER - Serious Event
    df_ae['AESER'] = df_source['AESERL'].apply(map_serious)
    
    # AEREL - Causality
    df_ae['AEREL'] = df_source['AEREL'].apply(map_causality)
    
    # AEOUT - Outcome
    df_ae['AEOUT'] = df_source['AEOUTCL'].apply(map_outcome)
    
    # AEACN - Action Taken with Study Treatment
    df_ae['AEACN'] = df_source['AEACTL'].apply(map_action)
    
    # ===========================
    # SERIOUS EVENT FLAGS
    # ===========================
    
    print("5. Deriving Serious Event Flags...")
    
    # Apply serious flags based on AESERL code
    serious_flags = df_source['AESERL'].apply(determine_serious_flags)
    df_ae['AESCONG'] = [flags['AESCONG'] for flags in serious_flags]
    df_ae['AESDISAB'] = [flags['AESDISAB'] for flags in serious_flags]
    df_ae['AESDTH'] = [flags['AESDTH'] for flags in serious_flags]
    df_ae['AESHOSP'] = [flags['AESHOSP'] for flags in serious_flags]
    df_ae['AESLIFE'] = [flags['AESLIFE'] for flags in serious_flags]
    df_ae['AESMIE'] = [flags['AESMIE'] for flags in serious_flags]
    
    # ===========================
    # VARIABLE ORDERING
    # ===========================
    
    # Standard SDTM AE variable order
    ae_vars = [
        'STUDYID', 'DOMAIN', 'USUBJID', 'AESEQ',
        'AETERM', 'AEDECOD', 'AEBODSYS',
        'AESEV', 'AESER', 'AEREL', 'AEACN', 'AEOUT',
        'AESTDTC', 'AEENDTC',
        'AESCONG', 'AESDISAB', 'AESDTH', 'AESHOSP', 'AESLIFE', 'AESMIE'
    ]
    
    df_ae = df_ae[ae_vars]
    
    # ===========================
    # DATA QUALITY CHECKS
    # ===========================
    
    print("\n6. Performing Data Quality Checks...")
    
    issues = []
    
    # Check required variables
    required_vars = ['STUDYID', 'DOMAIN', 'USUBJID', 'AESEQ', 'AETERM']
    for var in required_vars:
        null_count = df_ae[var].isna().sum() + (df_ae[var] == '').sum()
        if null_count > 0:
            issues.append(f"   - {var}: {null_count} missing values (REQUIRED)")
    
    # Check date formats
    invalid_dates = df_ae[~df_ae['AESTDTC'].str.match(r'^(\d{4}(-\d{2}(-\d{2})?)?)?$', na=False)]
    if len(invalid_dates) > 0:
        issues.append(f"   - AESTDTC: {len(invalid_dates)} invalid date formats")
    
    # Check AEDECOD population
    aedecod_missing = df_ae['AEDECOD'].isna().sum() + (df_ae['AEDECOD'] == '').sum()
    if aedecod_missing > 0:
        issues.append(f"   - AEDECOD: {aedecod_missing} missing (EXPECTED variable)")
    
    # Check controlled terminology
    invalid_sev = df_ae[~df_ae['AESEV'].isin(['MILD', 'MODERATE', 'SEVERE', 'LIFE THREATENING', 'FATAL', ''])].shape[0]
    if invalid_sev > 0:
        issues.append(f"   - AESEV: {invalid_sev} non-standard severity values")
    
    invalid_ser = df_ae[~df_ae['AESER'].isin(['Y', 'N', ''])].shape[0]
    if invalid_ser > 0:
        issues.append(f"   - AESER: {invalid_ser} non-standard serious flag values")
    
    # ===========================
    # SAVE OUTPUT
    # ===========================
    
    print(f"\n7. Saving SDTM AE dataset to: {output_file}")
    df_ae.to_csv(output_file, index=False, encoding='utf-8')
    
    # ===========================
    # TRANSFORMATION SUMMARY
    # ===========================
    
    print("\n" + "=" * 80)
    print("TRANSFORMATION SUMMARY")
    print("=" * 80)
    
    summary = {
        'records_transformed': len(df_ae),
        'source_records': len(df_source),
        'subjects': df_ae['USUBJID'].nunique(),
        'output_file': output_file,
        'issues': issues
    }
    
    print(f"\n✓ Records transformed: {summary['records_transformed']}")
    print(f"✓ Unique subjects: {summary['subjects']}")
    print(f"✓ Output file: {summary['output_file']}")
    
    # Controlled Terminology Mapping Counts
    print("\n--- Controlled Terminology Mappings ---")
    print(f"\nAESEV (Severity) Distribution:")
    print(df_ae['AESEV'].value_counts())
    
    print(f"\nAESER (Serious Event) Distribution:")
    print(df_ae['AESER'].value_counts())
    
    print(f"\nAEREL (Causality) Distribution:")
    print(df_ae['AEREL'].value_counts())
    
    print(f"\nAEOUT (Outcome) Distribution:")
    print(df_ae['AEOUT'].value_counts())
    
    print(f"\nAEACN (Action Taken) Distribution:")
    print(df_ae['AEACN'].value_counts())
    
    # Data Quality Issues
    if issues:
        print("\n--- Data Quality Issues ---")
        for issue in issues:
            print(issue)
    else:
        print("\n✓ No data quality issues detected")
    
    print("\n" + "=" * 80)
    
    return summary

# ===========================
# MAIN EXECUTION
# ===========================

if __name__ == "__main__":
    source_file = "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/source_data/Maxis-08 RAW DATA_CSV/AEVENT.csv"
    output_file = "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_sdtm_transformed.csv"
    
    summary = transform_ae_to_sdtm(source_file, output_file)

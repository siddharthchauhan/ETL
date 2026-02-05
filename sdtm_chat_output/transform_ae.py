#!/usr/bin/env python3
"""
SDTM AE Domain Transformation Script
Transforms AEVENT.csv and AEVENTC.csv to CDISC SDTM AE format
Following SDTM-IG 3.4 Standards
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from pathlib import Path

# Configuration
STUDY_ID = "MAXIS-08"
SOURCE_DIR = Path("/Users/siddharth/Downloads/ETL/ETL/edc_data_temp/Maxis-08 RAW DATA_CSV")
OUTPUT_DIR = Path("/Users/siddharth/Downloads/ETL/ETL/sdtm_chat_output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Controlled Terminology Mappings
SEVERITY_MAP = {
    'MILD': 'MILD',
    'MODERATE': 'MODERATE',
    'SEVERE': 'SEVERE',
    'LIFE THREATENING': 'LIFE THREATENING',
    'FATAL': 'FATAL'
}

SERIOUSNESS_MAP = {
    'NOT SERIOUS': 'N',
    'HOSPITALIZATION/PROLONGATION': 'Y',
    'SERIOUS': 'Y'
}

OUTCOME_MAP = {
    'RESOLVED': 'RECOVERED/RESOLVED',
    'CONTINUING': 'NOT RECOVERED/NOT RESOLVED',
    'PATIENT DIED': 'FATAL',
    'RESOLVED, WITH RESIDUAL EFFECTS': 'RECOVERED/RESOLVED WITH SEQUELAE'
}

ACTION_TAKEN_MAP = {
    'NONE': 'DOSE NOT CHANGED',
    'INTERRUPTED': 'DRUG INTERRUPTED',
    'DISCONTINUED': 'DRUG WITHDRAWN'
}

CAUSALITY_MAP = {
    'UNRELATED': 'NOT RELATED',
    'UNLIKELY': 'UNLIKELY RELATED',
    'POSSIBLE': 'POSSIBLY RELATED',
    'PROBABLE': 'PROBABLY RELATED',
    'DEFINITE': 'RELATED'
}

def convert_date_to_iso8601(date_str):
    """
    Convert various date formats to ISO 8601 format (YYYY-MM-DD or partial dates)
    Handles formats: YYYYMMDD, YYYYMM, YYYY
    """
    if pd.isna(date_str) or date_str == '':
        return ''
    
    date_str = str(date_str).strip()
    
    # Remove decimal points (Excel artifacts)
    if '.' in date_str:
        date_str = date_str.split('.')[0]
    
    # Handle YYYYMMDD format (8 digits)
    if len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
    
    # Handle YYYYMM format (6 digits) - partial date
    elif len(date_str) == 6 and date_str.isdigit():
        return f"{date_str[0:4]}-{date_str[4:6]}"
    
    # Handle YYYY format (4 digits) - partial date
    elif len(date_str) == 4 and date_str.isdigit():
        return date_str
    
    return date_str

def generate_usubjid(study_id, subjid):
    """Generate USUBJID from STUDYID and SUBJID"""
    return f"{study_id}-{subjid}"

def map_seriousness_flags(aeserl_value):
    """
    Map serious event category to individual seriousness flags
    AESDTH, AESHOSP, AESLIFE, AESDISAB, AESCONG, AESMIE
    """
    flags = {
        'AESDTH': '',
        'AESHOSP': '',
        'AESLIFE': '',
        'AESDISAB': '',
        'AESCONG': '',
        'AESMIE': ''
    }
    
    if pd.isna(aeserl_value):
        return flags
    
    aeserl_value = str(aeserl_value).upper()
    
    # Map based on the AESERL value from source
    if 'DEATH' in aeserl_value or 'DIED' in aeserl_value:
        flags['AESDTH'] = 'Y'
    if 'HOSPITALIZATION' in aeserl_value or 'PROLONGATION' in aeserl_value:
        flags['AESHOSP'] = 'Y'
    if 'LIFE THREATENING' in aeserl_value:
        flags['AESLIFE'] = 'Y'
    if 'DISAB' in aeserl_value:
        flags['AESDISAB'] = 'Y'
    if 'CONGENITAL' in aeserl_value:
        flags['AESCONG'] = 'Y'
    if 'MEDICALLY IMPORTANT' in aeserl_value:
        flags['AESMIE'] = 'Y'
    
    return flags

def transform_ae_data():
    """Main transformation function"""
    
    print("=" * 80)
    print("SDTM AE DOMAIN TRANSFORMATION")
    print("=" * 80)
    print(f"Study ID: {STUDY_ID}")
    print(f"Source Directory: {SOURCE_DIR}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print()
    
    # Load source data
    print("Loading source data...")
    aevent_file = SOURCE_DIR / "AEVENT.csv"
    aeventc_file = SOURCE_DIR / "AEVENTC.csv"
    
    if not aevent_file.exists():
        print(f"ERROR: {aevent_file} not found!")
        return None
    
    if not aeventc_file.exists():
        print(f"ERROR: {aeventc_file} not found!")
        return None
    
    # Read CSV files with encoding handling
    try:
        df_aevent = pd.read_csv(aevent_file, encoding='utf-8-sig')
    except:
        df_aevent = pd.read_csv(aevent_file, encoding='latin1')
    
    try:
        df_aeventc = pd.read_csv(aeventc_file, encoding='utf-8-sig')
    except:
        df_aeventc = pd.read_csv(aeventc_file, encoding='latin1')
    
    print(f"AEVENT records: {len(df_aevent)}")
    print(f"AEVENTC records: {len(df_aeventc)}")
    print()
    
    # Display source columns
    print("AEVENT columns:")
    print(", ".join(df_aevent.columns.tolist()))
    print()
    print("AEVENTC columns:")
    print(", ".join(df_aeventc.columns.tolist()))
    print()
    
    # Merge the two datasets if needed, or use primary one
    # For this transformation, we'll use AEVENT as primary source
    df_source = df_aevent.copy()
    
    print(f"Total source records to transform: {len(df_source)}")
    print()
    
    # Initialize SDTM AE dataset
    ae_data = []
    
    # Mapping specification
    mapping_spec = {
        "domain": "AE",
        "description": "Adverse Events Domain Mapping",
        "source_files": ["AEVENT.csv", "AEVENTC.csv"],
        "study_id": STUDY_ID,
        "transformation_date": datetime.now().isoformat(),
        "variable_mappings": [],
        "controlled_terminology": {
            "AESEV": SEVERITY_MAP,
            "AESER": SERIOUSNESS_MAP,
            "AEOUT": OUTCOME_MAP,
            "AEACN": ACTION_TAKEN_MAP,
            "AEREL": CAUSALITY_MAP
        }
    }
    
    # Track data quality issues
    data_quality_issues = []
    
    print("Transforming records...")
    for idx, row in df_source.iterrows():
        # Extract subject ID from INVSITE or SUBEVE
        subjid = str(row.get('INVSITE', '')).replace('C008_', '') if 'INVSITE' in row else ''
        if not subjid:
            subjid = str(row.get('SUBEVE', ''))
        
        # Generate USUBJID
        usubjid = generate_usubjid(STUDY_ID, subjid)
        
        # Map seriousness flags
        ser_flags = map_seriousness_flags(row.get('AESERL', ''))
        
        # Determine AESER (Overall seriousness)
        aeser_source = str(row.get('AESER', ''))
        aeser = 'Y' if aeser_source == '1' else 'N'
        
        # Alternative check based on AESERL
        if SERIOUSNESS_MAP.get(str(row.get('AESERL', '')).upper(), '') == 'Y':
            aeser = 'Y'
        
        # Check if outcome indicates death
        if row.get('AEOUTC', '') == '4' or 'DIED' in str(row.get('AEOUTCL', '')).upper():
            ser_flags['AESDTH'] = 'Y'
            aeser = 'Y'
        
        # Build AE record
        ae_record = {
            # Standard Required Variables
            'STUDYID': STUDY_ID,
            'DOMAIN': 'AE',
            'USUBJID': usubjid,
            'AESEQ': int(row.get('AESEQ', idx + 1)),
            
            # AE Specific Variables
            'AETERM': str(row.get('AEVERB', '')).strip() if pd.notna(row.get('AEVERB')) else '',
            'AEDECOD': str(row.get('AEPTT', '')).strip() if pd.notna(row.get('AEPTT')) else str(row.get('AEVERB', '')).strip(),
            'AELLT': str(row.get('AELTT', '')).strip() if pd.notna(row.get('AELTT')) else '',
            'AELLTCD': str(row.get('AELTC', '')).strip() if pd.notna(row.get('AELTC')) else '',
            'AEPTCD': str(row.get('AEPTC', '')).strip() if pd.notna(row.get('AEPTC')) else '',
            'AEHLT': str(row.get('AEHTT', '')).strip() if pd.notna(row.get('AEHTT')) else '',
            'AEHLTCD': str(row.get('AEHTC', '')).strip() if pd.notna(row.get('AEHTC')) else '',
            'AEHLGT': str(row.get('AEHGT1', '')).strip() if pd.notna(row.get('AEHGT1')) else '',
            'AEHLGTCD': str(row.get('AEHGC', '')).strip() if pd.notna(row.get('AEHGC')) else '',
            'AESOC': str(row.get('AESCT', '')).strip() if pd.notna(row.get('AESCT')) else '',
            'AESOCCD': str(row.get('AESCC', '')).strip() if pd.notna(row.get('AESCC')) else '',
            
            # Date/Time Variables
            'AESTDTC': convert_date_to_iso8601(row.get('AESTDT', '')),
            'AEENDTC': convert_date_to_iso8601(row.get('AEENDT', '')),
            
            # Severity
            'AESEV': SEVERITY_MAP.get(str(row.get('AESEV', '')).upper(), str(row.get('AESEV', ''))),
            
            # Seriousness
            'AESER': aeser,
            'AESDTH': ser_flags['AESDTH'],
            'AESHOSP': ser_flags['AESHOSP'],
            'AESLIFE': ser_flags['AESLIFE'],
            'AESDISAB': ser_flags['AESDISAB'],
            'AESCONG': ser_flags['AESCONG'],
            'AESMIE': ser_flags['AESMIE'],
            
            # Outcome
            'AEOUT': OUTCOME_MAP.get(str(row.get('AEOUTCL', '')).upper(), str(row.get('AEOUTCL', ''))),
            
            # Action Taken
            'AEACN': ACTION_TAKEN_MAP.get(str(row.get('AEACTL', '')).upper(), str(row.get('AEACTL', ''))),
            
            # Causality
            'AEREL': CAUSALITY_MAP.get(str(row.get('AERELL', '')).upper(), str(row.get('AERELL', ''))),
            
            # Supplemental Qualifiers
            'AECONTRT': str(row.get('AETRT', '')).upper() if pd.notna(row.get('AETRT')) else '',
        }
        
        # Data quality checks
        if not ae_record['AETERM']:
            data_quality_issues.append(f"Row {idx + 1}: Missing AETERM")
        
        if not ae_record['AESTDTC']:
            data_quality_issues.append(f"Row {idx + 1}: Missing start date")
        
        ae_data.append(ae_record)
    
    # Create DataFrame
    df_ae = pd.DataFrame(ae_data)
    
    # Reorder columns to match SDTM standard
    standard_order = [
        'STUDYID', 'DOMAIN', 'USUBJID', 'AESEQ', 'AETERM', 'AEDECOD',
        'AELLT', 'AELLTCD', 'AEPTCD', 'AEHLT', 'AEHLTCD', 'AEHLGT', 'AEHLGTCD',
        'AESOC', 'AESOCCD', 'AESTDTC', 'AEENDTC', 'AESEV', 'AESER',
        'AESDTH', 'AESHOSP', 'AESLIFE', 'AESDISAB', 'AESCONG', 'AESMIE',
        'AEOUT', 'AEACN', 'AEREL', 'AECONTRT'
    ]
    
    # Ensure all columns exist
    for col in standard_order:
        if col not in df_ae.columns:
            df_ae[col] = ''
    
    df_ae = df_ae[standard_order]
    
    # Save SDTM AE dataset
    output_file = OUTPUT_DIR / "ae.csv"
    df_ae.to_csv(output_file, index=False)
    print(f"SDTM AE dataset saved to: {output_file}")
    print()
    
    # Create detailed mapping specification
    for col in standard_order:
        var_map = {
            "sdtm_variable": col,
            "source_variable": "",
            "transformation": "",
            "controlled_terminology": ""
        }
        
        # Define source mappings
        source_map = {
            'STUDYID': 'Constant: MAXIS-08',
            'DOMAIN': 'Constant: AE',
            'USUBJID': 'Derived: STUDYID + "-" + SUBJID',
            'AESEQ': 'AESEQ',
            'AETERM': 'AEVERB',
            'AEDECOD': 'AEPTT (or AEVERB if missing)',
            'AELLT': 'AELTT',
            'AELLTCD': 'AELTC',
            'AEPTCD': 'AEPTC',
            'AEHLT': 'AEHTT',
            'AEHLTCD': 'AEHTC',
            'AEHLGT': 'AEHGT1',
            'AEHLGTCD': 'AEHGC',
            'AESOC': 'AESCT',
            'AESOCCD': 'AESCC',
            'AESTDTC': 'AESTDT (converted to ISO 8601)',
            'AEENDTC': 'AEENDT (converted to ISO 8601)',
            'AESEV': 'AESEV (mapped to controlled terminology)',
            'AESER': 'Derived from AESER and AESERL',
            'AESDTH': 'Derived from AESERL and AEOUTC',
            'AESHOSP': 'Derived from AESERL',
            'AESLIFE': 'Derived from AESERL',
            'AESDISAB': 'Derived from AESERL',
            'AESCONG': 'Derived from AESERL',
            'AESMIE': 'Derived from AESERL',
            'AEOUT': 'AEOUTCL (mapped to controlled terminology)',
            'AEACN': 'AEACTL (mapped to controlled terminology)',
            'AEREL': 'AERELL (mapped to controlled terminology)',
            'AECONTRT': 'AETRT'
        }
        
        var_map["source_variable"] = source_map.get(col, '')
        var_map["transformation"] = "Direct mapping" if col in ['AESEQ', 'AETERM'] else "Derived/Mapped"
        
        if col in ['AESEV', 'AESER', 'AEOUT', 'AEACN', 'AEREL']:
            var_map["controlled_terminology"] = "Yes"
        
        mapping_spec["variable_mappings"].append(var_map)
    
    # Save mapping specification
    spec_file = OUTPUT_DIR / "ae_mapping_specification.json"
    with open(spec_file, 'w') as f:
        json.dump(mapping_spec, f, indent=2)
    print(f"Mapping specification saved to: {spec_file}")
    print()
    
    # Generate summary
    print("=" * 80)
    print("TRANSFORMATION SUMMARY")
    print("=" * 80)
    print(f"Source Records Processed: {len(df_source)}")
    print(f"SDTM AE Records Created: {len(df_ae)}")
    print()
    
    print("SDTM Variables Generated:")
    for col in standard_order:
        non_empty = df_ae[col].notna().sum()
        print(f"  {col}: {non_empty} non-empty values")
    print()
    
    print("Controlled Terminology Mappings Applied:")
    print(f"  AESEV (Severity): {df_ae['AESEV'].value_counts().to_dict()}")
    print(f"  AESER (Serious): {df_ae['AESER'].value_counts().to_dict()}")
    print(f"  AEOUT (Outcome): {df_ae['AEOUT'].value_counts().to_dict()}")
    print(f"  AEACN (Action): {df_ae['AEACN'].value_counts().to_dict()}")
    print(f"  AEREL (Causality): {df_ae['AEREL'].value_counts().to_dict()}")
    print()
    
    print(f"Serious Events (AESER=Y): {(df_ae['AESER'] == 'Y').sum()}")
    print(f"  Deaths (AESDTH=Y): {(df_ae['AESDTH'] == 'Y').sum()}")
    print(f"  Hospitalizations (AESHOSP=Y): {(df_ae['AESHOSP'] == 'Y').sum()}")
    print(f"  Life-Threatening (AESLIFE=Y): {(df_ae['AESLIFE'] == 'Y').sum()}")
    print()
    
    if data_quality_issues:
        print("Data Quality Issues:")
        for issue in data_quality_issues[:10]:  # Show first 10
            print(f"  - {issue}")
        if len(data_quality_issues) > 10:
            print(f"  ... and {len(data_quality_issues) - 10} more issues")
    else:
        print("No data quality issues detected.")
    print()
    
    print("=" * 80)
    print("TRANSFORMATION COMPLETE")
    print("=" * 80)
    
    return df_ae

if __name__ == "__main__":
    result = transform_ae_data()
    if result is not None:
        print(f"\nFirst 5 records of transformed AE data:")
        print(result.head().to_string())

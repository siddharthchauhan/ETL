"""
VS (Vital Signs) SDTM Transformation with ISO 8601 Date Formatting
=================================================================

This script transforms raw EDC VITALS data to SDTM VS domain format:
- Horizontal to vertical structure (MELT operation)
- ISO 8601 date/time formatting for VSDTC
- Proper test code and test name mapping
- Handling of NOT DONE status

Author: SDTM Pipeline Agent
Date: 2025-02-02
SDTM Version: 3.4
"""

import pandas as pd
import numpy as np
from datetime import datetime
import re

# ============================================================================
# ISO 8601 Date/Time Conversion Functions
# ============================================================================

def to_iso8601_date(date_value):
    """
    Convert various date formats to ISO 8601 (YYYY-MM-DD).
    
    Handles:
    - 20080826.0 (YYYYMMDD numeric with decimal)
    - 20080826 (YYYYMMDD numeric)
    - pandas Timestamp objects
    - Already formatted ISO dates
    
    Returns:
        str: Date in YYYY-MM-DD format, or empty string if invalid
    """
    if pd.isna(date_value) or date_value == '':
        return ''
    
    # Handle pandas Timestamp / datetime objects
    if isinstance(date_value, (pd.Timestamp, datetime)):
        return date_value.strftime('%Y-%m-%d')
    
    # Handle numeric YYYYMMDD format (e.g., 20080826.0)
    if isinstance(date_value, (int, float)):
        str_val = str(int(date_value))
        if len(str_val) == 8:
            try:
                year = str_val[0:4]
                month = str_val[4:6]
                day = str_val[6:8]
                # Validate
                datetime.strptime(f"{year}-{month}-{day}", '%Y-%m-%d')
                return f"{year}-{month}-{day}"
            except ValueError:
                return ''
        elif len(str_val) == 6:  # Partial date YYYYMM
            try:
                year = str_val[0:4]
                month = str_val[4:6]
                datetime.strptime(f"{year}-{month}-01", '%Y-%m-%d')
                return f"{year}-{month}"
            except ValueError:
                return ''
    
    date_str = str(date_value).strip()
    
    # Already ISO 8601 (YYYY-MM-DD)
    if re.match(r'^\d{4}-\d{2}-\d{2}', date_str):
        return date_str[:10]
    
    # YYYYMMDD (8 digits)
    if len(date_str) == 8 and date_str.isdigit():
        try:
            year = date_str[0:4]
            month = date_str[4:6]
            day = date_str[6:8]
            datetime.strptime(f"{year}-{month}-{day}", '%Y-%m-%d')
            return f"{year}-{month}-{day}"
        except ValueError:
            return ''
    
    return ''


def format_time(time_value):
    """
    Convert numeric time to HH:MM format.
    
    Args:
        time_value: Numeric time in HHMM format (e.g., 1100.0, 2305.0, 45.0)
    
    Returns:
        str: Time in HH:MM format, or empty string if invalid
    """
    if pd.isna(time_value) or time_value == '':
        return ''
    
    try:
        # Convert to integer (removes decimal)
        time_int = int(float(time_value))
        
        # Extract hours and minutes
        hours = time_int // 100
        minutes = time_int % 100
        
        # Validate
        if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
            return ''
        
        # Format as HH:MM
        return f"{hours:02d}:{minutes:02d}"
    except (ValueError, TypeError):
        return ''


def to_iso8601_datetime(date_value, time_value):
    """
    Combine date and time to ISO 8601 YYYY-MM-DDTHH:MM format.
    
    Args:
        date_value: Date value (various formats)
        time_value: Time value (numeric HHMM)
    
    Returns:
        str: DateTime in ISO 8601 format, or date only if time missing
    """
    iso_date = to_iso8601_date(date_value)
    if not iso_date:
        return ''
    
    iso_time = format_time(time_value)
    if iso_time:
        return f"{iso_date}T{iso_time}"
    else:
        return iso_date


# ============================================================================
# VS Test Code Mapping
# ============================================================================

VS_TEST_MAPPING = {
    'VTBPS2': {
        'VSTESTCD': 'SYSBP',
        'VSTEST': 'Systolic Blood Pressure',
        'VSORRESU': 'mmHg'
    },
    'VTBPD2': {
        'VSTESTCD': 'DIABP',
        'VSTEST': 'Diastolic Blood Pressure',
        'VSORRESU': 'mmHg'
    },
    'VTPLS2': {
        'VSTESTCD': 'PULSE',
        'VSTEST': 'Pulse Rate',
        'VSORRESU': 'beats/min'
    },
    'VTRRT2': {
        'VSTESTCD': 'RESP',
        'VSTEST': 'Respiratory Rate',
        'VSORRESU': 'breaths/min'
    },
    'VTTP2': {
        'VSTESTCD': 'TEMP',
        'VSTEST': 'Temperature',
        'VSORRESU': 'C'
    },
    'GNNUM1': {
        'VSTESTCD': 'WEIGHT',
        'VSTEST': 'Weight',
        'VSORRESU': 'kg'
    },
    'GNNUM2': {
        'VSTESTCD': 'HEIGHT',
        'VSTEST': 'Height',
        'VSORRESU': 'cm'
    },
    'GNNUM3': {
        'VSTESTCD': 'BMI',
        'VSTEST': 'Body Mass Index',
        'VSORRESU': 'kg/m2'
    }
}


# ============================================================================
# VS Transformation Function
# ============================================================================

def transform_vitals_to_vs(source_file, output_file):
    """
    Transform VITALS.csv to SDTM VS domain.
    
    Args:
        source_file: Path to source VITALS.csv file
        output_file: Path to output VS.csv file
    
    Returns:
        dict: Transformation summary statistics
    """
    
    print("=" * 80)
    print("VS (Vital Signs) SDTM Transformation")
    print("=" * 80)
    
    # Read source data
    print(f"\n1. Reading source file: {source_file}")
    df_source = pd.read_csv(source_file, encoding='utf-8-sig')
    print(f"   Source records: {len(df_source)}")
    print(f"   Source columns: {list(df_source.columns)}")
    
    # Initialize output records list
    vs_records = []
    
    # Process each source record
    print(f"\n2. Processing records and applying MELT transformation...")
    for idx, row in df_source.iterrows():
        
        # Build USUBJID
        study = row['STUDY']
        site = str(row['INVSITE']).replace('C', '').replace('_', '-')  # C008_408 → 008-408
        pt = row['PT']
        usubjid = f"{study}-{site}-{pt}"
        
        # Convert date/time
        vsdtc = to_iso8601_datetime(row['VTDT'], row.get('VTTM', None))
        
        # Common fields
        visitnum = row['VISIT']
        visit = row['CPEVENT']
        vstpt = row.get('SUBEVE', '')
        vstptnum = row.get('QUALIFYV', '')
        
        # Baseline flag
        vsblfl = 'Y' if 'BASELINE' in str(visit).upper() else ''
        
        # NOT DONE handling
        gnanyl = row.get('GNANYL', '')
        is_not_done = str(gnanyl).strip().upper() == 'NOT DONE'
        
        # MELT: Create one record per vital sign measurement
        for source_col, test_info in VS_TEST_MAPPING.items():
            if source_col not in df_source.columns:
                continue
            
            value = row[source_col]
            
            # Skip if value is missing and not explicitly NOT DONE
            if pd.isna(value) and not is_not_done:
                continue
            
            # Create VS record
            vs_record = {
                'STUDYID': study,
                'DOMAIN': 'VS',
                'USUBJID': usubjid,
                'VSSEQ': None,  # Will assign later
                'VSTESTCD': test_info['VSTESTCD'],
                'VSTEST': test_info['VSTEST'],
                'VSCAT': '',
                'VSSCAT': '',
                'VSPOS': '',
                'VSORRES': str(value) if not pd.isna(value) else '',
                'VSORRESU': test_info['VSORRESU'] if not pd.isna(value) else '',
                'VSSTRESC': str(value) if not pd.isna(value) else '',
                'VSSTRESN': float(value) if not pd.isna(value) else np.nan,
                'VSSTRESU': test_info['VSORRESU'] if not pd.isna(value) else '',
                'VSSTAT': 'NOT DONE' if (pd.isna(value) or is_not_done) else '',
                'VSREASND': gnanyl if (pd.isna(value) or is_not_done) else '',
                'VSLOC': '',
                'VSLAT': '',
                'VSBLFL': vsblfl,
                'VSDRVFL': '',
                'VISITNUM': visitnum,
                'VISIT': visit,
                'VISITDY': '',
                'EPOCH': '',
                'VSDTC': vsdtc,
                'VSDY': '',
                'VSTPT': vstpt,
                'VSTPTNUM': vstptnum
            }
            
            vs_records.append(vs_record)
    
    # Create DataFrame
    print(f"\n3. Creating VS DataFrame...")
    df_vs = pd.DataFrame(vs_records)
    
    # Sort and assign sequence numbers
    print(f"   Sorting records by USUBJID, VSDTC, VSTPTNUM, VSTESTCD...")
    df_vs = df_vs.sort_values(['USUBJID', 'VSDTC', 'VSTPTNUM', 'VSTESTCD']).reset_index(drop=True)
    
    print(f"   Assigning VSSEQ sequence numbers per subject...")
    df_vs['VSSEQ'] = df_vs.groupby('USUBJID').cumcount() + 1
    
    # Reorder columns (SDTM standard order)
    column_order = [
        'STUDYID', 'DOMAIN', 'USUBJID', 'VSSEQ', 'VSTESTCD', 'VSTEST', 
        'VSCAT', 'VSSCAT', 'VSPOS', 'VSORRES', 'VSORRESU', 
        'VSSTRESC', 'VSSTRESN', 'VSSTRESU', 'VSSTAT', 'VSREASND', 
        'VSLOC', 'VSLAT', 'VSBLFL', 'VSDRVFL', 
        'VISITNUM', 'VISIT', 'VISITDY', 'EPOCH', 
        'VSDTC', 'VSDY', 'VSTPT', 'VSTPTNUM'
    ]
    df_vs = df_vs[column_order]
    
    # Save to CSV
    print(f"\n4. Writing output file: {output_file}")
    df_vs.to_csv(output_file, index=False)
    
    # Summary statistics
    print(f"\n" + "=" * 80)
    print("TRANSFORMATION SUMMARY")
    print("=" * 80)
    print(f"Source records:        {len(df_source)}")
    print(f"Target VS records:     {len(df_vs)}")
    print(f"Unique subjects:       {df_vs['USUBJID'].nunique()}")
    print(f"Date range:            {df_vs['VSDTC'].min()} to {df_vs['VSDTC'].max()}")
    print(f"\nTest Code Distribution:")
    print(df_vs['VSTESTCD'].value_counts().to_string())
    print(f"\nBaseline records:      {df_vs['VSBLFL'].eq('Y').sum()}")
    print(f"NOT DONE records:      {df_vs['VSSTAT'].eq('NOT DONE').sum()}")
    print(f"\nISO 8601 Dates Sample:")
    print(df_vs[['USUBJID', 'VSTESTCD', 'VSDTC', 'VSTPT']].head(10).to_string(index=False))
    
    return {
        'source_records': len(df_source),
        'target_records': len(df_vs),
        'unique_subjects': df_vs['USUBJID'].nunique(),
        'date_range': (df_vs['VSDTC'].min(), df_vs['VSDTC'].max()),
        'test_codes': df_vs['VSTESTCD'].value_counts().to_dict(),
        'baseline_records': df_vs['VSBLFL'].eq('Y').sum(),
        'not_done_records': df_vs['VSSTAT'].eq('NOT DONE').sum()
    }


# ============================================================================
# Main Execution
# ============================================================================

if __name__ == '__main__':
    
    # File paths
    source_file = '/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/source_data/Maxis-08 RAW DATA_CSV/VITALS.csv'
    output_file = '/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/mapping_specs/sdtm_data/vs_enhanced_iso8601.csv'
    
    # Execute transformation
    summary = transform_vitals_to_vs(source_file, output_file)
    
    print(f"\n{'=' * 80}")
    print("✅ VS TRANSFORMATION COMPLETE!")
    print(f"{'=' * 80}\n")

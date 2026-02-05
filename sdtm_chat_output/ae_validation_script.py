#!/usr/bin/env python3
"""
SDTM AE Domain Comprehensive Validation Script
Validates CDISC conformance and data quality
"""

import pandas as pd
import numpy as np
from datetime import datetime
import re
from collections import defaultdict

# Input file
AE_FILE = '/Users/siddharth/Downloads/ETL/ETL/sdtm_chat_output/ae.csv'

# CDISC Controlled Terminology
CT_AESEV = ['MILD', 'MODERATE', 'SEVERE', 'LIFE THREATENING', 'FATAL']
CT_AESER = ['Y', 'N']
CT_AEOUT = [
    'RECOVERED/RESOLVED',
    'RECOVERING/RESOLVING', 
    'NOT RECOVERED/NOT RESOLVED',
    'RECOVERED/RESOLVED WITH SEQUELAE',
    'FATAL',
    'UNKNOWN'
]
CT_AEACN = [
    'DOSE NOT CHANGED',
    'DOSE INCREASED',
    'DOSE REDUCED',
    'DRUG INTERRUPTED',
    'DRUG WITHDRAWN',
    'DOSE RATE REDUCED',
    'NOT APPLICABLE',
    'UNKNOWN',
    'NOT EVALUABLE',
    'DOSE REDUCED AND INTERRUPTED'
]
CT_AEREL = [
    'NOT RELATED',
    'UNLIKELY RELATED',
    'POSSIBLY RELATED',
    'PROBABLY RELATED',
    'DEFINITELY RELATED',
    'RELATED'
]

# Required AE variables (SDTMIG v3.4)
REQUIRED_VARS = ['STUDYID', 'DOMAIN', 'USUBJID', 'AESEQ', 'AETERM', 'AEDECOD', 'AESTDTC']

# Initialize validation results
validation_results = {
    'structural': {'errors': [], 'warnings': [], 'notes': []},
    'terminology': {'errors': [], 'warnings': [], 'notes': []},
    'datetime': {'errors': [], 'warnings': [], 'notes': []},
    'business_rules': {'errors': [], 'warnings': [], 'notes': []},
    'data_quality': {'errors': [], 'warnings': [], 'notes': []}
}

def validate_iso8601(date_str):
    """Validate ISO 8601 date format"""
    if pd.isna(date_str) or date_str == '':
        return True, None
    
    patterns = [
        r'^\d{4}$',                           # YYYY
        r'^\d{4}-\d{2}$',                     # YYYY-MM
        r'^\d{4}-\d{2}-\d{2}$',               # YYYY-MM-DD
        r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$',   # YYYY-MM-DDTHH:MM
        r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$'  # YYYY-MM-DDTHH:MM:SS
    ]
    
    for pattern in patterns:
        if re.match(pattern, str(date_str)):
            return True, None
    
    return False, f"Invalid ISO 8601 format: {date_str}"

def compare_dates(start_date, end_date):
    """Compare two ISO 8601 dates (returns True if end >= start or incomparable)"""
    if pd.isna(start_date) or pd.isna(end_date) or start_date == '' or end_date == '':
        return True, None
    
    try:
        # Convert to comparable format (pad partial dates)
        start_str = str(start_date).replace('T', '-').replace(':', '-')
        end_str = str(end_date).replace('T', '-').replace(':', '-')
        
        start_parts = start_str.split('-')
        end_parts = end_str.split('-')
        
        # Pad to same length for comparison
        max_len = max(len(start_parts), len(end_parts))
        start_parts += ['01'] * (max_len - len(start_parts))
        end_parts += ['01'] * (max_len - len(end_parts))
        
        start_cmp = '-'.join(start_parts[:3])
        end_cmp = '-'.join(end_parts[:3])
        
        if end_cmp < start_cmp:
            return False, f"End date ({end_date}) before start date ({start_date})"
        
        return True, None
    except:
        return True, None  # Cannot compare

def main():
    print("=" * 80)
    print("SDTM AE DOMAIN VALIDATION REPORT")
    print("=" * 80)
    print(f"\nStudy: MAXIS-08")
    print(f"Domain: AE (Adverse Events)")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Input File: {AE_FILE}")
    
    # Load data
    print("\n" + "=" * 80)
    print("LOADING DATA...")
    print("=" * 80)
    
    try:
        df = pd.read_csv(AE_FILE)
        print(f"✓ Successfully loaded {len(df)} records")
        print(f"✓ Found {len(df.columns)} variables")
        
        # Get actual record count (header is row 1, data starts row 2)
        actual_records = len(df)
        print(f"✓ Actual data records: {actual_records}")
        
    except Exception as e:
        print(f"✗ ERROR loading file: {e}")
        return
    
    # 1. STRUCTURAL VALIDATION
    print("\n" + "=" * 80)
    print("1. STRUCTURAL VALIDATION")
    print("=" * 80)
    
    # Check required variables
    print("\n1.1 Required Variables Check:")
    missing_vars = [var for var in REQUIRED_VARS if var not in df.columns]
    if missing_vars:
        for var in missing_vars:
            validation_results['structural']['errors'].append(
                f"Missing required variable: {var}"
            )
            print(f"  ✗ ERROR: Missing required variable {var}")
    else:
        print(f"  ✓ All {len(REQUIRED_VARS)} required variables present")
        validation_results['structural']['notes'].append(
            f"All required variables present: {', '.join(REQUIRED_VARS)}"
        )
    
    # Check variable naming conventions
    print("\n1.2 Variable Naming Convention Check:")
    invalid_names = []
    for col in df.columns:
        if not col.isupper():
            invalid_names.append(f"{col} (not uppercase)")
        if len(col) > 8:
            invalid_names.append(f"{col} (exceeds 8 characters)")
    
    if invalid_names:
        for name in invalid_names[:10]:  # Show first 10
            validation_results['structural']['warnings'].append(
                f"Variable naming issue: {name}"
            )
            print(f"  ⚠ WARNING: {name}")
        if len(invalid_names) > 10:
            print(f"  ... and {len(invalid_names) - 10} more")
    else:
        print(f"  ✓ All {len(df.columns)} variables follow naming convention")
    
    # Check DOMAIN value
    print("\n1.3 Domain Value Check:")
    if 'DOMAIN' in df.columns:
        domain_values = df['DOMAIN'].unique()
        if len(domain_values) == 1 and domain_values[0] == 'AE':
            print(f"  ✓ DOMAIN = 'AE' (correct)")
        else:
            validation_results['structural']['errors'].append(
                f"Invalid DOMAIN value(s): {list(domain_values)}"
            )
            print(f"  ✗ ERROR: Invalid DOMAIN value(s): {list(domain_values)}")
    
    # Check STUDYID
    print("\n1.4 Study ID Check:")
    if 'STUDYID' in df.columns:
        study_values = df['STUDYID'].unique()
        if len(study_values) == 1 and study_values[0] == 'MAXIS-08':
            print(f"  ✓ STUDYID = 'MAXIS-08' (correct)")
        else:
            validation_results['structural']['warnings'].append(
                f"Multiple STUDYID values: {list(study_values)}"
            )
            print(f"  ⚠ WARNING: Multiple STUDYID values: {list(study_values)}")
    
    # Check for duplicate AESEQ within subjects
    print("\n1.5 Sequence Number Uniqueness Check:")
    if 'USUBJID' in df.columns and 'AESEQ' in df.columns:
        duplicates = df.groupby('USUBJID')['AESEQ'].apply(
            lambda x: x[x.duplicated()].tolist()
        )
        duplicates = duplicates[duplicates.apply(len) > 0]
        
        if len(duplicates) > 0:
            for subj, seqs in duplicates.items():
                validation_results['structural']['errors'].append(
                    f"Duplicate AESEQ for {subj}: {seqs}"
                )
            print(f"  ✗ ERROR: Found {len(duplicates)} subjects with duplicate AESEQ")
            print(f"    First 5: {list(duplicates.head().items())}")
        else:
            print(f"  ✓ AESEQ is unique within each subject")
    
    # Data types check
    print("\n1.6 Data Type Check:")
    numeric_vars = ['AESEQ', 'AELLTCD', 'AEPTCD', 'AEHLTCD', 'AEHLGTCD', 'AESOCCD']
    char_vars = ['STUDYID', 'DOMAIN', 'USUBJID', 'AETERM', 'AEDECOD', 'AESEV', 'AESER']
    
    type_issues = 0
    for var in numeric_vars:
        if var in df.columns:
            non_numeric = df[var].apply(lambda x: not pd.isna(x) and x != '' and x != 'nan')
            non_numeric = non_numeric.sum()
            # Check if can convert to numeric
            try:
                pd.to_numeric(df[var], errors='coerce')
            except:
                type_issues += 1
                validation_results['structural']['warnings'].append(
                    f"Variable {var} contains non-numeric values"
                )
    
    if type_issues == 0:
        print(f"  ✓ Numeric variables have appropriate data types")
    else:
        print(f"  ⚠ WARNING: {type_issues} variables have data type issues")
    
    # 2. CONTROLLED TERMINOLOGY VALIDATION
    print("\n" + "=" * 80)
    print("2. CONTROLLED TERMINOLOGY VALIDATION")
    print("=" * 80)
    
    # AESEV validation
    print("\n2.1 AESEV (Severity) Validation:")
    if 'AESEV' in df.columns:
        invalid_sev = df[~df['AESEV'].isin(CT_AESEV) & df['AESEV'].notna()]
        if len(invalid_sev) > 0:
            unique_invalid = invalid_sev['AESEV'].unique()
            for val in unique_invalid:
                count = (invalid_sev['AESEV'] == val).sum()
                validation_results['terminology']['errors'].append(
                    f"Invalid AESEV value '{val}' ({count} records)"
                )
            print(f"  ✗ ERROR: {len(invalid_sev)} records with invalid AESEV")
            print(f"    Invalid values: {list(unique_invalid)[:5]}")
        else:
            print(f"  ✓ All AESEV values are valid ({df['AESEV'].notna().sum()} records checked)")
    
    # AESER validation
    print("\n2.2 AESER (Serious Event) Validation:")
    if 'AESER' in df.columns:
        invalid_ser = df[~df['AESER'].isin(CT_AESER) & df['AESER'].notna()]
        if len(invalid_ser) > 0:
            unique_invalid = invalid_ser['AESER'].unique()
            for val in unique_invalid:
                count = (invalid_ser['AESER'] == val).sum()
                validation_results['terminology']['errors'].append(
                    f"Invalid AESER value '{val}' ({count} records)"
                )
            print(f"  ✗ ERROR: {len(invalid_ser)} records with invalid AESER")
            print(f"    Invalid values: {list(unique_invalid)}")
        else:
            print(f"  ✓ All AESER values are valid ({df['AESER'].notna().sum()} records checked)")
    
    # AEOUT validation
    print("\n2.3 AEOUT (Outcome) Validation:")
    if 'AEOUT' in df.columns:
        invalid_out = df[~df['AEOUT'].isin(CT_AEOUT) & df['AEOUT'].notna()]
        if len(invalid_out) > 0:
            unique_invalid = invalid_out['AEOUT'].unique()
            for val in unique_invalid:
                count = (invalid_out['AEOUT'] == val).sum()
                validation_results['terminology']['errors'].append(
                    f"Invalid AEOUT value '{val}' ({count} records)"
                )
            print(f"  ✗ ERROR: {len(invalid_out)} records with invalid AEOUT")
            print(f"    Invalid values: {list(unique_invalid)[:5]}")
        else:
            print(f"  ✓ All AEOUT values are valid ({df['AEOUT'].notna().sum()} records checked)")
    
    # AEACN validation
    print("\n2.4 AEACN (Action Taken) Validation:")
    if 'AEACN' in df.columns:
        invalid_acn = df[~df['AEACN'].isin(CT_AEACN) & df['AEACN'].notna()]
        if len(invalid_acn) > 0:
            unique_invalid = invalid_acn['AEACN'].unique()
            for val in unique_invalid:
                count = (invalid_acn['AEACN'] == val).sum()
                validation_results['terminology']['errors'].append(
                    f"Invalid AEACN value '{val}' ({count} records)"
                )
            print(f"  ✗ ERROR: {len(invalid_acn)} records with invalid AEACN")
            print(f"    Invalid values: {list(unique_invalid)[:5]}")
        else:
            print(f"  ✓ All AEACN values are valid ({df['AEACN'].notna().sum()} records checked)")
    
    # AEREL validation
    print("\n2.5 AEREL (Relationship to Treatment) Validation:")
    if 'AEREL' in df.columns:
        invalid_rel = df[~df['AEREL'].isin(CT_AEREL) & df['AEREL'].notna()]
        if len(invalid_rel) > 0:
            unique_invalid = invalid_rel['AEREL'].unique()
            for val in unique_invalid:
                count = (invalid_rel['AEREL'] == val).sum()
                validation_results['terminology']['errors'].append(
                    f"Invalid AEREL value '{val}' ({count} records)"
                )
            print(f"  ✗ ERROR: {len(invalid_rel)} records with invalid AEREL")
            print(f"    Invalid values: {list(unique_invalid)[:5]}")
        else:
            print(f"  ✓ All AEREL values are valid ({df['AEREL'].notna().sum()} records checked)")
    
    # 3. DATE/TIME VALIDATION
    print("\n" + "=" * 80)
    print("3. DATE/TIME VALIDATION")
    print("=" * 80)
    
    # AESTDTC validation
    print("\n3.1 AESTDTC (Start Date) ISO 8601 Validation:")
    if 'AESTDTC' in df.columns:
        invalid_dates = []
        for idx, date_val in enumerate(df['AESTDTC']):
            if pd.notna(date_val) and date_val != '':
                valid, msg = validate_iso8601(date_val)
                if not valid:
                    invalid_dates.append((idx + 2, date_val, msg))  # +2 for header row
        
        if invalid_dates:
            for row, date, msg in invalid_dates[:10]:
                validation_results['datetime']['errors'].append(
                    f"Row {row}: {msg}"
                )
            print(f"  ✗ ERROR: {len(invalid_dates)} records with invalid AESTDTC format")
            print(f"    First 5 issues:")
            for row, date, msg in invalid_dates[:5]:
                print(f"      Row {row}: {date}")
        else:
            print(f"  ✓ All AESTDTC dates follow ISO 8601 format ({df['AESTDTC'].notna().sum()} checked)")
    
    # AEENDTC validation
    print("\n3.2 AEENDTC (End Date) ISO 8601 Validation:")
    if 'AEENDTC' in df.columns:
        invalid_dates = []
        for idx, date_val in enumerate(df['AEENDTC']):
            if pd.notna(date_val) and date_val != '':
                valid, msg = validate_iso8601(date_val)
                if not valid:
                    invalid_dates.append((idx + 2, date_val, msg))
        
        if invalid_dates:
            for row, date, msg in invalid_dates[:10]:
                validation_results['datetime']['errors'].append(
                    f"Row {row}: {msg}"
                )
            print(f"  ✗ ERROR: {len(invalid_dates)} records with invalid AEENDTC format")
        else:
            print(f"  ✓ All AEENDTC dates follow ISO 8601 format ({df['AEENDTC'].notna().sum()} checked)")
    
    # Date logic validation (end >= start)
    print("\n3.3 Date Logic Validation (AEENDTC >= AESTDTC):")
    if 'AESTDTC' in df.columns and 'AEENDTC' in df.columns:
        date_issues = []
        for idx, row in df.iterrows():
            valid, msg = compare_dates(row['AESTDTC'], row['AEENDTC'])
            if not valid:
                date_issues.append((idx + 2, row['USUBJID'], row['AESEQ'], msg))
        
        if date_issues:
            for row_num, subj, seq, msg in date_issues[:10]:
                validation_results['datetime']['errors'].append(
                    f"Row {row_num} (USUBJID={subj}, AESEQ={seq}): {msg}"
                )
            print(f"  ✗ ERROR: {len(date_issues)} records with end date before start date")
            print(f"    First 5 issues:")
            for row_num, subj, seq, msg in date_issues[:5]:
                print(f"      Row {row_num}: {subj} AESEQ={seq}")
        else:
            print(f"  ✓ All dates follow correct temporal logic")
    
    # 4. BUSINESS RULES VALIDATION
    print("\n" + "=" * 80)
    print("4. BUSINESS RULES VALIDATION")
    print("=" * 80)
    
    # Rule 1: If AESER=Y, at least one serious flag should be Y
    print("\n4.1 Serious Event Flag Consistency:")
    if 'AESER' in df.columns:
        ser_flags = ['AESDTH', 'AESHOSP', 'AESLIFE', 'AESDISAB', 'AESCONG', 'AESMIE']
        available_flags = [f for f in ser_flags if f in df.columns]
        
        serious_events = df[df['AESER'] == 'Y'].copy()
        if len(serious_events) > 0:
            issues = []
            for idx, row in serious_events.iterrows():
                has_flag = any(row[f] == 'Y' for f in available_flags if pd.notna(row[f]))
                if not has_flag:
                    issues.append((idx + 2, row['USUBJID'], row['AESEQ']))
            
            if issues:
                for row_num, subj, seq in issues[:10]:
                    validation_results['business_rules']['errors'].append(
                        f"Row {row_num} (USUBJID={subj}, AESEQ={seq}): AESER=Y but no serious flag set"
                    )
                print(f"  ✗ ERROR: {len(issues)} serious events missing specific serious flags")
            else:
                print(f"  ✓ All {len(serious_events)} serious events have appropriate flags")
        else:
            print(f"  ℹ No serious events in dataset")
    
    # Rule 2: If AESDTH=Y, then AESER must be Y
    print("\n4.2 Death Flag Consistency:")
    if 'AESDTH' in df.columns and 'AESER' in df.columns:
        death_events = df[df['AESDTH'] == 'Y'].copy()
        if len(death_events) > 0:
            issues = death_events[death_events['AESER'] != 'Y']
            if len(issues) > 0:
                for idx, row in issues.iterrows():
                    validation_results['business_rules']['errors'].append(
                        f"Row {idx + 2} (USUBJID={row['USUBJID']}, AESEQ={row['AESEQ']}): AESDTH=Y but AESER != Y"
                    )
                print(f"  ✗ ERROR: {len(issues)} death events where AESER != Y")
            else:
                print(f"  ✓ All {len(death_events)} death events have AESER=Y")
        else:
            print(f"  ℹ No death events in dataset")
    
    # Rule 3: If AESDTH=Y, AEOUT should be FATAL
    print("\n4.3 Death Outcome Consistency:")
    if 'AESDTH' in df.columns and 'AEOUT' in df.columns:
        death_events = df[df['AESDTH'] == 'Y'].copy()
        if len(death_events) > 0:
            issues = death_events[death_events['AEOUT'] != 'FATAL']
            if len(issues) > 0:
                for idx, row in issues.iterrows():
                    validation_results['business_rules']['warnings'].append(
                        f"Row {idx + 2} (USUBJID={row['USUBJID']}, AESEQ={row['AESEQ']}): AESDTH=Y but AEOUT != FATAL (is {row['AEOUT']})"
                    )
                print(f"  ⚠ WARNING: {len(issues)} death events where AEOUT != FATAL")
            else:
                print(f"  ✓ All {len(death_events)} death events have AEOUT=FATAL")
    
    # Rule 4: USUBJID format check
    print("\n4.4 USUBJID Format Validation:")
    if 'USUBJID' in df.columns:
        expected_pattern = r'^MAXIS-08-\d+$'
        invalid_usubjid = df[~df['USUBJID'].str.match(expected_pattern)]
        
        if len(invalid_usubjid) > 0:
            unique_invalid = invalid_usubjid['USUBJID'].unique()
            for val in unique_invalid[:5]:
                validation_results['business_rules']['warnings'].append(
                    f"USUBJID format warning: {val}"
                )
            print(f"  ⚠ WARNING: {len(invalid_usubjid)} records with unexpected USUBJID format")
            print(f"    Expected: MAXIS-08-XXX")
            print(f"    Found: {list(unique_invalid)[:3]}")
        else:
            print(f"  ✓ All USUBJID values follow expected format")
    
    # 5. DATA QUALITY CHECKS
    print("\n" + "=" * 80)
    print("5. DATA QUALITY CHECKS")
    print("=" * 80)
    
    # Missing required fields
    print("\n5.1 Missing Required Field Check:")
    missing_summary = {}
    for var in REQUIRED_VARS:
        if var in df.columns:
            missing_count = df[var].isna().sum() + (df[var] == '').sum()
            if missing_count > 0:
                missing_summary[var] = missing_count
                validation_results['data_quality']['errors'].append(
                    f"{var}: {missing_count} missing values"
                )
    
    if missing_summary:
        print(f"  ✗ ERROR: Missing values in required fields:")
        for var, count in missing_summary.items():
            pct = (count / len(df)) * 100
            print(f"    {var}: {count} records ({pct:.1f}%)")
    else:
        print(f"  ✓ No missing values in required fields")
    
    # Missing optional fields summary
    print("\n5.2 Optional Field Completeness:")
    optional_vars = ['AEENDTC', 'AESEV', 'AESER', 'AEOUT', 'AEACN', 'AEREL']
    completeness = {}
    for var in optional_vars:
        if var in df.columns:
            non_missing = df[var].notna().sum()
            pct = (non_missing / len(df)) * 100
            completeness[var] = pct
            print(f"  {var}: {pct:.1f}% complete ({non_missing}/{len(df)})")
    
    # Check for completely blank records
    print("\n5.3 Blank Record Check:")
    blank_records = df[df.isna().all(axis=1)]
    if len(blank_records) > 0:
        validation_results['data_quality']['errors'].append(
            f"Found {len(blank_records)} completely blank records"
        )
        print(f"  ✗ ERROR: {len(blank_records)} completely blank records")
    else:
        print(f"  ✓ No completely blank records")
    
    # Duplicate record check
    print("\n5.4 Duplicate Record Check:")
    if 'USUBJID' in df.columns and 'AESEQ' in df.columns:
        duplicates = df[df.duplicated(subset=['USUBJID', 'AESEQ'], keep=False)]
        if len(duplicates) > 0:
            validation_results['data_quality']['errors'].append(
                f"Found {len(duplicates)} duplicate records"
            )
            print(f"  ✗ ERROR: {len(duplicates)} duplicate records based on USUBJID+AESEQ")
        else:
            print(f"  ✓ No duplicate records")
    
    # Referential integrity
    print("\n5.5 Referential Integrity:")
    validation_results['data_quality']['notes'].append(
        "Referential integrity checks require additional domain data (DM, EX, etc.)"
    )
    print(f"  ℹ Note: Full referential integrity validation requires DM and EX domains")
    
    # SUMMARY REPORT
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    total_errors = sum(len(v['errors']) for v in validation_results.values())
    total_warnings = sum(len(v['warnings']) for v in validation_results.values())
    total_notes = sum(len(v['notes']) for v in validation_results.values())
    
    print(f"\nTotal Records Validated: {len(df)}")
    print(f"Total Variables: {len(df.columns)}")
    print(f"\nIssues Found:")
    print(f"  ✗ ERRORS: {total_errors}")
    print(f"  ⚠ WARNINGS: {total_warnings}")
    print(f"  ℹ NOTES: {total_notes}")
    
    print("\n\nBreakdown by Category:")
    categories = [
        ('1. Structural', 'structural'),
        ('2. Controlled Terminology', 'terminology'),
        ('3. Date/Time', 'datetime'),
        ('4. Business Rules', 'business_rules'),
        ('5. Data Quality', 'data_quality')
    ]
    
    for name, key in categories:
        errors = len(validation_results[key]['errors'])
        warnings = len(validation_results[key]['warnings'])
        notes = len(validation_results[key]['notes'])
        status = '✓ PASS' if errors == 0 else '✗ FAIL'
        print(f"\n{name}:")
        print(f"  Status: {status}")
        print(f"  Errors: {errors}, Warnings: {warnings}, Notes: {notes}")
    
    # Calculate compliance score
    print("\n" + "=" * 80)
    print("COMPLIANCE SCORE CALCULATION")
    print("=" * 80)
    
    # Scoring weights
    critical_checks = [
        ('Required variables present', 0 if missing_vars else 1),
        ('DOMAIN value correct', 1 if 'DOMAIN' in df.columns and df['DOMAIN'].iloc[0] == 'AE' else 0),
        ('AESEQ unique within subject', 1 if len(duplicates) == 0 else 0) if 'USUBJID' in df.columns and 'AESEQ' in df.columns else ('AESEQ unique within subject', 1),
        ('No missing required fields', 0 if missing_summary else 1),
        ('Valid controlled terminology', 1 if validation_results['terminology']['errors'] == [] else 0),
        ('ISO 8601 date formats', 1 if validation_results['datetime']['errors'] == [] else 0),
    ]
    
    score_achieved = sum(score for _, score in critical_checks)
    score_possible = len(critical_checks)
    compliance_score = (score_achieved / score_possible) * 100
    
    print(f"\nCritical Checks:")
    for check, score in critical_checks:
        status = '✓' if score == 1 else '✗'
        print(f"  {status} {check}")
    
    print(f"\n{'=' * 50}")
    print(f"COMPLIANCE SCORE: {compliance_score:.1f}%")
    print(f"{'=' * 50}")
    
    # Submission readiness
    print("\n" + "=" * 80)
    print("SUBMISSION READINESS ASSESSMENT")
    print("=" * 80)
    
    if compliance_score >= 95 and total_errors == 0:
        print("\n✓ STATUS: SUBMISSION READY")
        print("  • Compliance score >= 95%")
        print("  • Zero critical errors")
    else:
        print("\n✗ STATUS: NOT SUBMISSION READY")
        if compliance_score < 95:
            print(f"  • Compliance score below 95% (current: {compliance_score:.1f}%)")
        if total_errors > 0:
            print(f"  • {total_errors} critical errors must be resolved")
    
    print("\n" + "=" * 80)
    print("DETAILED FINDINGS")
    print("=" * 80)
    
    for name, key in categories:
        if validation_results[key]['errors'] or validation_results[key]['warnings']:
            print(f"\n{name}:")
            
            if validation_results[key]['errors']:
                print(f"\n  Errors ({len(validation_results[key]['errors'])}):")
                for i, error in enumerate(validation_results[key]['errors'][:20], 1):
                    print(f"    {i}. {error}")
                if len(validation_results[key]['errors']) > 20:
                    print(f"    ... and {len(validation_results[key]['errors']) - 20} more errors")
            
            if validation_results[key]['warnings']:
                print(f"\n  Warnings ({len(validation_results[key]['warnings'])}):")
                for i, warning in enumerate(validation_results[key]['warnings'][:10], 1):
                    print(f"    {i}. {warning}")
                if len(validation_results[key]['warnings']) > 10:
                    print(f"    ... and {len(validation_results[key]['warnings']) - 10} more warnings")
    
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    recommendations = []
    
    if total_errors > 0:
        recommendations.append("1. Address all critical errors before submission")
        if validation_results['terminology']['errors']:
            recommendations.append("   • Review and correct controlled terminology violations")
        if validation_results['datetime']['errors']:
            recommendations.append("   • Fix ISO 8601 date format issues")
        if validation_results['business_rules']['errors']:
            recommendations.append("   • Resolve business rule violations (serious event flags, death coding)")
        if missing_summary:
            recommendations.append("   • Populate missing required fields")
    
    if total_warnings > 0:
        recommendations.append(f"2. Review {total_warnings} warnings for data quality improvement")
    
    if compliance_score < 95:
        recommendations.append("3. Improve compliance score to meet 95% threshold")
    
    if not recommendations:
        recommendations.append("✓ No critical recommendations - dataset meets quality standards")
    
    for rec in recommendations:
        print(f"\n{rec}")
    
    print("\n" + "=" * 80)
    print("END OF VALIDATION REPORT")
    print("=" * 80)
    print()

if __name__ == '__main__':
    main()

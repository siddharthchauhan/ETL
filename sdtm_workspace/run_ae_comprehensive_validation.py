#!/usr/bin/env python3
"""
Execute comprehensive AE domain validation
"""

import pandas as pd
import json
from datetime import datetime
import re

# Load the dataset
df = pd.read_csv('/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_sdtm_complete_transform.csv')

print("\n" + "="*80)
print("🔬 SDTM AE DOMAIN COMPREHENSIVE VALIDATION")
print("   CDISC SDTM-IG 3.4 & FDA Standards")
print("="*80 + "\n")

print(f"📊 Dataset: ae_sdtm_complete_transform.csv")
print(f"📝 Total Records: {len(df)}")
print(f"📋 Total Variables: {len(df.columns)}")
print(f"🔢 Variables: {', '.join(df.columns.tolist())}\n")

# Initialize counters
errors = []
warnings = []
info = []

# CDISC CT definitions
CT_VALUES = {
    'AESEV': ['MILD', 'MODERATE', 'SEVERE'],
    'AESER': ['Y', 'N'],
    'AEREL': ['NOT RELATED', 'UNLIKELY RELATED', 'POSSIBLY RELATED', 'PROBABLY RELATED', 'RELATED'],
    'AEOUT': ['FATAL', 'NOT RECOVERED/NOT RESOLVED', 'RECOVERED/RESOLVED', 
              'RECOVERED/RESOLVED WITH SEQUELAE', 'RECOVERING/RESOLVING', 'UNKNOWN'],
    'AEACN': ['DOSE INCREASED', 'DOSE NOT CHANGED', 'DOSE REDUCED', 
              'DRUG INTERRUPTED', 'DRUG WITHDRAWN', 'NOT APPLICABLE', 'NOT EVALUABLE', 'UNKNOWN']
}

print("🔍 VALIDATION PHASE 1: STRUCTURAL CHECKS")
print("-" * 80)

# Check required variables
required_vars = ['STUDYID', 'DOMAIN', 'USUBJID', 'AESEQ', 'AETERM']
for var in required_vars:
    if var not in df.columns:
        errors.append(f"❌ Missing required variable: {var}")
    else:
        null_count = df[var].isna().sum()
        if null_count > 0:
            errors.append(f"❌ {var} has {null_count} missing values")
        else:
            print(f"  ✅ {var}: Complete ({len(df)} records)")

# Check DOMAIN value
if 'DOMAIN' in df.columns:
    domain_values = df['DOMAIN'].unique()
    if len(domain_values) == 1 and domain_values[0] == 'AE':
        print(f"  ✅ DOMAIN: Correct value 'AE'")
    else:
        errors.append(f"❌ DOMAIN has incorrect values: {domain_values}")

# Check for duplicate keys
if 'USUBJID' in df.columns and 'AESEQ' in df.columns:
    duplicates = df[df.duplicated(['USUBJID', 'AESEQ'], keep=False)]
    if len(duplicates) == 0:
        print(f"  ✅ Unique Keys: No duplicates (USUBJID + AESEQ)")
    else:
        errors.append(f"❌ Found {len(duplicates)} duplicate key combinations")

print(f"\n  Structure Status: {'✅ PASSED' if len(errors) == 0 else '❌ FAILED'}")

print("\n🔍 VALIDATION PHASE 2: CONTROLLED TERMINOLOGY")
print("-" * 80)

ct_errors = 0
for var, valid_values in CT_VALUES.items():
    if var in df.columns:
        actual = df[var].dropna()
        actual = actual[actual.astype(str).str.strip() != '']
        
        if len(actual) > 0:
            invalid = actual[~actual.isin(valid_values)]
            if len(invalid) > 0:
                unique_invalid = invalid.unique()
                errors.append(f"❌ {var}: {len(invalid)} invalid values - {unique_invalid}")
                ct_errors += len(invalid)
                print(f"  ❌ {var}: {len(invalid)} invalid values")
            else:
                print(f"  ✅ {var}: All values valid")
        else:
            info.append(f"ℹ️  {var}: No values to validate (all empty)")

print(f"\n  CT Status: {'✅ PASSED' if ct_errors == 0 else f'❌ FAILED ({ct_errors} issues)'}")

print("\n🔍 VALIDATION PHASE 3: ISO 8601 DATE VALIDATION")
print("-" * 80)

iso_patterns = [
    r'^\d{4}$',
    r'^\d{4}-\d{2}$',
    r'^\d{4}-\d{2}-\d{2}$',
    r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$',
    r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$',
]

date_errors = 0
for var in ['AESTDTC', 'AEENDTC']:
    if var in df.columns:
        dates = df[var].dropna()
        dates = dates[dates.astype(str).str.strip() != '']
        
        if len(dates) > 0:
            invalid_dates = []
            for idx, date_val in dates.items():
                date_str = str(date_val).strip()
                is_valid = any(re.match(pattern, date_str) for pattern in iso_patterns)
                if not is_valid:
                    invalid_dates.append(date_str)
            
            if invalid_dates:
                errors.append(f"❌ {var}: {len(invalid_dates)} non-ISO 8601 dates - {set(invalid_dates)}")
                date_errors += len(invalid_dates)
                print(f"  ❌ {var}: {len(invalid_dates)} invalid dates")
            else:
                print(f"  ✅ {var}: All dates ISO 8601 compliant ({len(dates)} dates)")
        else:
            print(f"  ℹ️  {var}: No dates to validate")

print(f"\n  Date Status: {'✅ PASSED' if date_errors == 0 else f'❌ FAILED ({date_errors} issues)'}")

print("\n🔍 VALIDATION PHASE 4: FDA BUSINESS RULES")
print("-" * 80)

business_errors = 0

# Check serious event logic
if 'AESER' in df.columns:
    serious = df[df['AESER'] == 'Y']
    sae_flags = ['AESDTH', 'AESLIFE', 'AESHOSP', 'AESDISAB', 'AESCONG', 'AESMIE']
    
    print(f"  Total SAEs: {len(serious)}")
    
    for idx, row in serious.iterrows():
        has_reason = False
        for flag in sae_flags:
            if flag in df.columns and row[flag] == 'Y':
                has_reason = True
                break
        
        if not has_reason:
            # Check if all flags are empty (not just N)
            all_empty = all(pd.isna(row.get(flag, None)) or str(row.get(flag, '')).strip() == '' 
                          for flag in sae_flags if flag in df.columns)
            if all_empty:
                warnings.append(f"⚠️  Row {idx+2}: AESER='Y' but no SAE reason flags set")
                business_errors += 1

# Check date consistency
if 'AESTDTC' in df.columns and 'AEENDTC' in df.columns:
    date_inconsistent = 0
    for idx, row in df.iterrows():
        start = str(row['AESTDTC']).strip()
        end = str(row['AEENDTC']).strip()
        
        if start not in ['', 'nan', 'None'] and end not in ['', 'nan', 'None']:
            if start > end:
                errors.append(f"❌ Row {idx+2}: End date before start date")
                date_inconsistent += 1
    
    if date_inconsistent == 0:
        print(f"  ✅ Date Consistency: All end dates >= start dates")
    else:
        print(f"  ❌ Date Consistency: {date_inconsistent} records with inconsistent dates")
        business_errors += date_inconsistent

# Check sequence integrity
if 'USUBJID' in df.columns and 'AESEQ' in df.columns:
    seq_issues = 0
    for usubjid, group in df.groupby('USUBJID'):
        seqs = sorted(group['AESEQ'].dropna().astype(int).tolist())
        if len(seqs) > 0:
            # Check if starts from 1
            if seqs[0] != 1:
                warnings.append(f"⚠️  {usubjid}: AESEQ doesn't start from 1 (starts from {seqs[0]})")
                seq_issues += 1
            
            # Check for duplicates
            if len(seqs) != len(set(seqs)):
                errors.append(f"❌ {usubjid}: Duplicate AESEQ values")
                seq_issues += 1
    
    if seq_issues == 0:
        print(f"  ✅ Sequence Integrity: All sequences valid")
    else:
        print(f"  ⚠️  Sequence Integrity: {seq_issues} issues found")

print(f"\n  Business Rules Status: {'✅ PASSED' if business_errors == 0 else f'⚠️  {business_errors} issues'}")

print("\n🔍 VALIDATION PHASE 5: DATA QUALITY CHECKS")
print("-" * 80)

# Check for trailing/leading spaces
space_issues = 0
for col in df.columns:
    if df[col].dtype == 'object':
        with_spaces = (df[col].astype(str).str.strip() != df[col].astype(str)).sum()
        if with_spaces > 0:
            warnings.append(f"⚠️  {col}: {with_spaces} values with trailing/leading spaces")
            space_issues += 1

if space_issues == 0:
    print(f"  ✅ No trailing/leading spaces")
else:
    print(f"  ⚠️  {space_issues} variables have spacing issues")

# Check variable name conventions
invalid_names = []
for col in df.columns:
    if not re.match(r'^[A-Z0-9]+$', col):
        invalid_names.append(col)

if len(invalid_names) == 0:
    print(f"  ✅ All variable names follow SDTM conventions")
else:
    warnings.append(f"⚠️  Non-standard variable names: {invalid_names}")
    print(f"  ⚠️  {len(invalid_names)} variables with naming issues")

print("\n" + "="*80)
print("📊 VALIDATION SUMMARY")
print("="*80 + "\n")

total_errors = len([e for e in errors])
total_warnings = len([w for w in warnings])
total_info = len([i for i in info])

print(f"❌ ERRORS: {total_errors}")
print(f"⚠️  WARNINGS: {total_warnings}")
print(f"ℹ️  INFO: {total_info}\n")

# Calculate compliance score
base_score = 100
error_deduction = total_errors * 5
warning_deduction = total_warnings * 2

compliance_score = max(0, base_score - error_deduction - warning_deduction)

print(f"🎯 OVERALL COMPLIANCE SCORE: {compliance_score}%")

if compliance_score >= 95 and total_errors == 0:
    status = "✅ READY FOR SUBMISSION"
    recommendation = "Dataset meets FDA submission standards"
elif total_errors == 0:
    status = "⚠️  ACCEPTABLE WITH REVIEW"
    recommendation = "Address warnings before submission recommended"
else:
    status = "❌ NOT READY FOR SUBMISSION"
    recommendation = "Fix all errors before submission"

print(f"📋 STATUS: {status}")
print(f"💡 RECOMMENDATION: {recommendation}\n")

# Top 5 issues
if errors or warnings:
    print("🔝 TOP 5 ISSUES:\n")
    all_issues = errors + warnings
    for i, issue in enumerate(all_issues[:5], 1):
        print(f"{i}. {issue}")
    print()

# Save results
results = {
    'validation_date': datetime.now().isoformat(),
    'dataset': 'ae_sdtm_complete_transform.csv',
    'total_records': len(df),
    'total_variables': len(df.columns),
    'compliance_score': compliance_score,
    'error_count': total_errors,
    'warning_count': total_warnings,
    'info_count': total_info,
    'submission_ready': compliance_score >= 95 and total_errors == 0,
    'status': status,
    'recommendation': recommendation,
    'errors': errors,
    'warnings': warnings,
    'info': info
}

with open('/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_validation_results_detailed.json', 'w') as f:
    json.dump(results, f, indent=2)

print("="*80)
print("✅ Validation complete! Results saved to ae_validation_results_detailed.json")
print("="*80 + "\n")

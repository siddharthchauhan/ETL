#!/usr/bin/env python3
"""
SDTM Validation Script
Performs basic structural and content validation of SDTM datasets.

Usage:
    python validate_sdtm.py --path /path/to/sdtm --ig 3.4
    python validate_sdtm.py --path /path/to/sdtm --domain DM --verbose
"""

import argparse
import os
import sys
from datetime import datetime
import re
from typing import Dict, List, Optional, Tuple

# Try to import pandas for XPT reading
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

# SDTM IG 3.4 Required Variables by Domain
REQUIRED_VARIABLES = {
    'DM': ['STUDYID', 'DOMAIN', 'USUBJID', 'SUBJID', 'SITEID', 'AGE', 'AGEU', 'SEX', 'RACE', 'ARMCD', 'ARM', 'COUNTRY'],
    'AE': ['STUDYID', 'DOMAIN', 'USUBJID', 'AESEQ', 'AETERM', 'AEDECOD', 'AESTDTC'],
    'CM': ['STUDYID', 'DOMAIN', 'USUBJID', 'CMSEQ', 'CMTRT', 'CMSTDTC'],
    'MH': ['STUDYID', 'DOMAIN', 'USUBJID', 'MHSEQ', 'MHTERM'],
    'EX': ['STUDYID', 'DOMAIN', 'USUBJID', 'EXSEQ', 'EXTRT', 'EXDOSE', 'EXDOSU', 'EXSTDTC'],
    'DS': ['STUDYID', 'DOMAIN', 'USUBJID', 'DSSEQ', 'DSTERM', 'DSDECOD', 'DSSTDTC'],
    'LB': ['STUDYID', 'DOMAIN', 'USUBJID', 'LBSEQ', 'LBTESTCD', 'LBTEST', 'LBORRES', 'LBORRESU', 'LBDTC'],
    'VS': ['STUDYID', 'DOMAIN', 'USUBJID', 'VSSEQ', 'VSTESTCD', 'VSTEST', 'VSORRES', 'VSORRESU', 'VSDTC'],
    'EG': ['STUDYID', 'DOMAIN', 'USUBJID', 'EGSEQ', 'EGTESTCD', 'EGTEST', 'EGORRES', 'EGDTC'],
    'PE': ['STUDYID', 'DOMAIN', 'USUBJID', 'PESEQ', 'PETESTCD', 'PETEST', 'PEORRES', 'PEDTC'],
    'QS': ['STUDYID', 'DOMAIN', 'USUBJID', 'QSSEQ', 'QSTESTCD', 'QSTEST', 'QSCAT', 'QSORRES', 'QSDTC'],
    'SV': ['STUDYID', 'DOMAIN', 'USUBJID', 'SVSEQ', 'VISITNUM', 'VISIT', 'SVSTDTC'],
    'SE': ['STUDYID', 'DOMAIN', 'USUBJID', 'SESEQ', 'ETCD', 'ELEMENT', 'SESTDTC'],
    'TA': ['STUDYID', 'DOMAIN', 'ARMCD', 'ARM', 'TAESSION', 'ETCD', 'ELEMENT', 'TABESSION', 'EPOCH'],
    'TE': ['STUDYID', 'DOMAIN', 'ETCD', 'ELEMENT'],
    'TI': ['STUDYID', 'DOMAIN', 'IETESTCD', 'IETEST', 'IECAT'],
    'TS': ['STUDYID', 'DOMAIN', 'TSSEQ', 'TSPARMCD', 'TSPARM', 'TSVAL'],
    'TV': ['STUDYID', 'DOMAIN', 'VISITNUM', 'VISIT'],
}

# Controlled Terminology Codelists (subset of common values)
CT_VALUES = {
    'SEX': ['M', 'F', 'U', 'UNDIFFERENTIATED'],
    'NY': ['Y', 'N'],
    'AGEU': ['YEARS', 'MONTHS', 'WEEKS', 'DAYS', 'HOURS'],
    'AESEV': ['MILD', 'MODERATE', 'SEVERE'],
    'OUT': ['RECOVERED/RESOLVED', 'RECOVERING/RESOLVING', 'NOT RECOVERED/NOT RESOLVED',
            'RECOVERED/RESOLVED WITH SEQUELAE', 'FATAL', 'UNKNOWN'],
    'ACN': ['DRUG WITHDRAWN', 'DOSE REDUCED', 'DOSE NOT CHANGED', 'DOSE INCREASED',
            'DRUG INTERRUPTED', 'NOT APPLICABLE', 'UNKNOWN'],
    'ROUTE': ['ORAL', 'INTRAVENOUS', 'SUBCUTANEOUS', 'INTRAMUSCULAR', 'TOPICAL',
              'TRANSDERMAL', 'INHALATION', 'NASAL', 'OPHTHALMIC', 'RECTAL', 'VAGINAL'],
    'EPOCH': ['SCREENING', 'RUN-IN', 'TREATMENT', 'FOLLOW-UP', 'NOT APPLICABLE'],
}

# ISO 8601 Date Patterns
ISO8601_PATTERNS = [
    r'^\d{4}$',                           # YYYY
    r'^\d{4}-\d{2}$',                     # YYYY-MM
    r'^\d{4}-\d{2}-\d{2}$',               # YYYY-MM-DD
    r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$',   # YYYY-MM-DDTHH:MM
    r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$',  # YYYY-MM-DDTHH:MM:SS
]


class ValidationResult:
    """Container for validation results"""
    def __init__(self):
        self.errors: List[Dict] = []
        self.warnings: List[Dict] = []
        self.notices: List[Dict] = []

    def add_error(self, domain: str, rule: str, message: str, details: str = ""):
        self.errors.append({
            'domain': domain,
            'rule': rule,
            'message': message,
            'details': details,
            'severity': 'ERROR'
        })

    def add_warning(self, domain: str, rule: str, message: str, details: str = ""):
        self.warnings.append({
            'domain': domain,
            'rule': rule,
            'message': message,
            'details': details,
            'severity': 'WARNING'
        })

    def add_notice(self, domain: str, rule: str, message: str, details: str = ""):
        self.notices.append({
            'domain': domain,
            'rule': rule,
            'message': message,
            'details': details,
            'severity': 'NOTICE'
        })

    def summary(self) -> str:
        return f"Errors: {len(self.errors)}, Warnings: {len(self.warnings)}, Notices: {len(self.notices)}"


def is_valid_iso8601(date_str: str) -> bool:
    """Check if string matches ISO 8601 date format"""
    if pd.isna(date_str) or date_str == '':
        return True  # Missing dates handled separately
    for pattern in ISO8601_PATTERNS:
        if re.match(pattern, str(date_str)):
            return True
    return False


def validate_usubjid_format(df: pd.DataFrame, domain: str, results: ValidationResult):
    """Validate USUBJID format consistency"""
    if 'USUBJID' not in df.columns:
        return

    usubjids = df['USUBJID'].dropna().unique()

    # Check for common format (STUDYID-SITEID-SUBJID)
    pattern = r'^[A-Za-z0-9\-]+$'
    for usubjid in usubjids:
        if not re.match(pattern, str(usubjid)):
            results.add_warning(domain, 'SD1001',
                f"USUBJID '{usubjid}' contains unexpected characters",
                "Expected format: STUDYID-SITEID-SUBJID")


def validate_sequence(df: pd.DataFrame, domain: str, results: ValidationResult):
    """Validate --SEQ uniqueness within USUBJID"""
    seq_var = f"{domain}SEQ"

    if seq_var not in df.columns or 'USUBJID' not in df.columns:
        return

    # Check for duplicates
    duplicates = df.groupby(['USUBJID', seq_var]).size()
    duplicates = duplicates[duplicates > 1]

    if len(duplicates) > 0:
        results.add_error(domain, 'SD1002',
            f"Duplicate {seq_var} values found within USUBJID",
            f"Count: {len(duplicates)} duplicate combinations")


def validate_required_variables(df: pd.DataFrame, domain: str, results: ValidationResult):
    """Check for required variables"""
    if domain not in REQUIRED_VARIABLES:
        return

    required = REQUIRED_VARIABLES[domain]
    missing = [var for var in required if var not in df.columns]

    for var in missing:
        results.add_error(domain, 'SD1000',
            f"Required variable {var} is missing from {domain}",
            "Add variable or verify domain structure")


def validate_controlled_terminology(df: pd.DataFrame, domain: str, results: ValidationResult):
    """Validate CT-controlled variables"""
    ct_mappings = {
        'SEX': 'SEX',
        'AGEU': 'AGEU',
        'AESER': 'NY',
        'AESEV': 'AESEV',
        'AEOUT': 'OUT',
        'AEACN': 'ACN',
        'EXROUTE': 'ROUTE',
        'CMROUTE': 'ROUTE',
        'EPOCH': 'EPOCH',
        'AESDTH': 'NY', 'AESHOSP': 'NY', 'AESLIFE': 'NY',
        'AESDISAB': 'NY', 'AESCONG': 'NY', 'AESMIE': 'NY',
    }

    for var, codelist in ct_mappings.items():
        if var not in df.columns:
            continue

        valid_values = CT_VALUES.get(codelist, [])
        if not valid_values:
            continue

        invalid = df[var].dropna().unique()
        invalid = [v for v in invalid if str(v).upper() not in valid_values]

        for val in invalid:
            results.add_warning(domain, 'CT0001',
                f"Value '{val}' for {var} not in codelist {codelist}",
                f"Valid values: {', '.join(valid_values[:5])}...")


def validate_dates(df: pd.DataFrame, domain: str, results: ValidationResult):
    """Validate ISO 8601 date formats"""
    date_vars = [col for col in df.columns if col.endswith('DTC')]

    for var in date_vars:
        invalid_dates = []
        for idx, val in df[var].items():
            if not is_valid_iso8601(val):
                invalid_dates.append(str(val))

        if invalid_dates:
            results.add_error(domain, 'DT0001',
                f"Invalid ISO 8601 format in {var}",
                f"Examples: {', '.join(invalid_dates[:3])}")


def validate_dm_specific(df: pd.DataFrame, results: ValidationResult):
    """DM-specific validation"""
    # Check RFSTDTC populated
    if 'RFSTDTC' in df.columns:
        missing = df['RFSTDTC'].isna().sum()
        if missing > 0:
            results.add_error('DM', 'DT0002',
                f"RFSTDTC missing for {missing} subjects",
                "Reference start date required for study day calculations")

    # Check ARM/ARMCD consistency
    if 'ARM' in df.columns and 'ARMCD' in df.columns:
        arm_map = df.groupby('ARMCD')['ARM'].nunique()
        inconsistent = arm_map[arm_map > 1]
        if len(inconsistent) > 0:
            results.add_error('DM', 'DM0001',
                "ARMCD maps to multiple ARM values",
                f"Inconsistent ARMCD: {list(inconsistent.index)}")


def validate_ae_specific(df: pd.DataFrame, results: ValidationResult):
    """AE-specific validation"""
    # Check seriousness criteria when AESER=Y
    if 'AESER' in df.columns:
        serious_vars = ['AESDTH', 'AESHOSP', 'AESLIFE', 'AESDISAB', 'AESCONG', 'AESMIE']
        available_vars = [v for v in serious_vars if v in df.columns]

        if available_vars:
            serious_aes = df[df['AESER'] == 'Y']
            for idx, row in serious_aes.iterrows():
                has_criteria = any(row.get(v) == 'Y' for v in available_vars)
                if not has_criteria:
                    results.add_warning('AE', 'AE0001',
                        f"AESER=Y but no seriousness criteria flagged",
                        f"AESEQ: {row.get('AESEQ', 'unknown')}")


def validate_dataset(filepath: str, domain: str, results: ValidationResult, verbose: bool = False):
    """Validate a single SDTM dataset"""
    if not HAS_PANDAS:
        results.add_error(domain, 'SYS001',
            "pandas not installed - cannot read datasets",
            "Install with: pip install pandas pyreadstat")
        return

    try:
        # Read XPT file
        if filepath.endswith('.xpt'):
            try:
                import pyreadstat
                df, meta = pyreadstat.read_xport(filepath)
            except ImportError:
                results.add_error(domain, 'SYS002',
                    "pyreadstat not installed - cannot read XPT files",
                    "Install with: pip install pyreadstat")
                return
        elif filepath.endswith('.csv'):
            df = pd.read_csv(filepath)
        elif filepath.endswith('.sas7bdat'):
            try:
                import pyreadstat
                df, meta = pyreadstat.read_sas7bdat(filepath)
            except ImportError:
                results.add_error(domain, 'SYS002',
                    "pyreadstat not installed",
                    "Install with: pip install pyreadstat")
                return
        else:
            results.add_warning(domain, 'SYS003',
                f"Unknown file format: {filepath}",
                "Supported: .xpt, .csv, .sas7bdat")
            return

        if verbose:
            print(f"  Validating {domain}: {len(df)} records, {len(df.columns)} variables")

        # Run validations
        validate_required_variables(df, domain, results)
        validate_usubjid_format(df, domain, results)
        validate_sequence(df, domain, results)
        validate_controlled_terminology(df, domain, results)
        validate_dates(df, domain, results)

        # Domain-specific validations
        if domain == 'DM':
            validate_dm_specific(df, results)
        elif domain == 'AE':
            validate_ae_specific(df, results)

    except Exception as e:
        results.add_error(domain, 'SYS999',
            f"Error reading {filepath}",
            str(e))


def find_datasets(path: str, domain: Optional[str] = None) -> List[Tuple[str, str]]:
    """Find SDTM datasets in directory"""
    datasets = []

    for ext in ['.xpt', '.csv', '.sas7bdat']:
        if domain:
            # Look for specific domain
            filepath = os.path.join(path, f"{domain.lower()}{ext}")
            if os.path.exists(filepath):
                datasets.append((filepath, domain.upper()))
        else:
            # Find all datasets
            for filename in os.listdir(path):
                if filename.endswith(ext):
                    dom = filename.replace(ext, '').upper()
                    # Skip SUPP-- domains for now
                    if not dom.startswith('SUPP'):
                        datasets.append((os.path.join(path, filename), dom))

    return datasets


def main():
    parser = argparse.ArgumentParser(description='Validate SDTM datasets')
    parser.add_argument('--path', required=True, help='Path to SDTM datasets')
    parser.add_argument('--ig', default='3.4', help='SDTM IG version (default: 3.4)')
    parser.add_argument('--domain', help='Validate specific domain only')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--output', '-o', help='Output file for results')

    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"Error: Path not found: {args.path}")
        sys.exit(1)

    print(f"SDTM Validation - IG {args.ig}")
    print(f"Path: {args.path}")
    print("-" * 50)

    results = ValidationResult()
    datasets = find_datasets(args.path, args.domain)

    if not datasets:
        print("No datasets found!")
        sys.exit(1)

    print(f"Found {len(datasets)} dataset(s)")

    for filepath, domain in datasets:
        validate_dataset(filepath, domain, results, args.verbose)

    # Print results
    print("\n" + "=" * 50)
    print("VALIDATION RESULTS")
    print("=" * 50)

    if results.errors:
        print(f"\nERRORS ({len(results.errors)}):")
        for err in results.errors:
            print(f"  [{err['domain']}] {err['rule']}: {err['message']}")
            if args.verbose and err['details']:
                print(f"    -> {err['details']}")

    if results.warnings:
        print(f"\nWARNINGS ({len(results.warnings)}):")
        for warn in results.warnings:
            print(f"  [{warn['domain']}] {warn['rule']}: {warn['message']}")
            if args.verbose and warn['details']:
                print(f"    -> {warn['details']}")

    if results.notices:
        print(f"\nNOTICES ({len(results.notices)}):")
        for notice in results.notices:
            print(f"  [{notice['domain']}] {notice['rule']}: {notice['message']}")

    print("\n" + "-" * 50)
    print(f"Summary: {results.summary()}")

    # Exit code based on errors
    sys.exit(1 if results.errors else 0)


if __name__ == '__main__':
    main()

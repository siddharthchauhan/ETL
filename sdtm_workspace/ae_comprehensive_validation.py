#!/usr/bin/env python3
"""
Comprehensive SDTM AE Domain Validation
Validates against CDISC SDTM-IG 3.4 and FDA standards
"""

import pandas as pd
import numpy as np
from datetime import datetime
import re
import json

class AEValidator:
    """Comprehensive AE domain validator"""
    
    def __init__(self, file_path):
        self.file_path = file_path
        self.df = pd.read_csv(file_path)
        self.issues = []
        self.error_count = 0
        self.warning_count = 0
        self.info_count = 0
        
        # CDISC Controlled Terminology for AE domain
        self.ct_values = {
            'AESEV': ['MILD', 'MODERATE', 'SEVERE'],
            'AESER': ['Y', 'N'],
            'AEREL': [
                'NOT RELATED', 'UNLIKELY RELATED', 'POSSIBLY RELATED',
                'PROBABLY RELATED', 'RELATED'
            ],
            'AEOUT': [
                'FATAL', 'NOT RECOVERED/NOT RESOLVED', 'RECOVERED/RESOLVED',
                'RECOVERED/RESOLVED WITH SEQUELAE', 'RECOVERING/RESOLVING',
                'UNKNOWN'
            ],
            'AEACN': [
                'DOSE INCREASED', 'DOSE NOT CHANGED', 'DOSE REDUCED',
                'DRUG INTERRUPTED', 'DRUG WITHDRAWN', 'NOT APPLICABLE',
                'NOT EVALUABLE', 'UNKNOWN'
            ],
            'AESCONG': ['Y', 'N'],
            'AESDISAB': ['Y', 'N'],
            'AESDTH': ['Y', 'N'],
            'AESHOSP': ['Y', 'N'],
            'AESLIFE': ['Y', 'N'],
            'AESMIE': ['Y', 'N']
        }
        
    def add_issue(self, rule_id, severity, message, affected_records=None, variable=None):
        """Add validation issue"""
        issue = {
            'rule_id': rule_id,
            'severity': severity,
            'message': message,
            'affected_records': affected_records,
            'variable': variable
        }
        self.issues.append(issue)
        
        if severity == 'error':
            self.error_count += 1
        elif severity == 'warning':
            self.warning_count += 1
        else:
            self.info_count += 1
            
    def validate_structure(self):
        """Validate structural requirements"""
        print("🔍 Phase 1: Structural Validation")
        
        # Required variables per SDTM-IG 3.4
        required_vars = ['STUDYID', 'DOMAIN', 'USUBJID', 'AESEQ', 'AETERM']
        expected_vars = required_vars + [
            'AEDECOD', 'AEBODSYS', 'AESEV', 'AESER', 'AEREL',
            'AEACN', 'AEOUT', 'AESTDTC', 'AEENDTC'
        ]
        
        # Check required variables
        missing_vars = [var for var in required_vars if var not in self.df.columns]
        if missing_vars:
            self.add_issue(
                'SD0006',
                'error',
                f"Missing required variables: {', '.join(missing_vars)}",
                variable=', '.join(missing_vars)
            )
        
        # Check DOMAIN value
        if 'DOMAIN' in self.df.columns:
            non_ae = self.df[self.df['DOMAIN'] != 'AE']
            if len(non_ae) > 0:
                self.add_issue(
                    'SD0004',
                    'error',
                    f"DOMAIN must be 'AE', found {len(non_ae)} records with incorrect domain",
                    affected_records=len(non_ae),
                    variable='DOMAIN'
                )
        
        # Check for duplicate keys (USUBJID + AESEQ)
        if 'USUBJID' in self.df.columns and 'AESEQ' in self.df.columns:
            duplicates = self.df[self.df.duplicated(['USUBJID', 'AESEQ'], keep=False)]
            if len(duplicates) > 0:
                self.add_issue(
                    'SD0026',
                    'error',
                    f"Found {len(duplicates)} duplicate records (USUBJID + AESEQ)",
                    affected_records=len(duplicates)
                )
        
        # Check AESEQ uniqueness within USUBJID
        if 'USUBJID' in self.df.columns and 'AESEQ' in self.df.columns:
            for usubjid, group in self.df.groupby('USUBJID'):
                if group['AESEQ'].duplicated().any():
                    dups = len(group[group['AESEQ'].duplicated()])
                    self.add_issue(
                        'SD0063',
                        'error',
                        f"AESEQ not unique for subject {usubjid}",
                        affected_records=dups,
                        variable='AESEQ'
                    )
        
        # Check for empty required values
        for var in required_vars:
            if var in self.df.columns:
                null_count = self.df[var].isna().sum()
                empty_count = (self.df[var].astype(str).str.strip() == '').sum()
                total_missing = null_count + empty_count
                
                if total_missing > 0:
                    self.add_issue(
                        f'SD0007-{var}',
                        'error',
                        f"Required variable {var} has {total_missing} missing values",
                        affected_records=total_missing,
                        variable=var
                    )
        
        print(f"  ✓ Structure check complete")
        
    def validate_controlled_terminology(self):
        """Validate CDISC controlled terminology"""
        print("🔍 Phase 2: Controlled Terminology Validation")
        
        for var, valid_values in self.ct_values.items():
            if var in self.df.columns:
                # Get non-null values
                actual_values = self.df[var].dropna()
                actual_values = actual_values[actual_values.astype(str).str.strip() != '']
                
                if len(actual_values) > 0:
                    invalid_mask = ~actual_values.isin(valid_values)
                    invalid_count = invalid_mask.sum()
                    
                    if invalid_count > 0:
                        invalid_vals = actual_values[invalid_mask].unique()
                        self.add_issue(
                            f'CT0001-{var}',
                            'error',
                            f"{var} has {invalid_count} invalid values: {', '.join(map(str, invalid_vals[:5]))}",
                            affected_records=invalid_count,
                            variable=var
                        )
        
        print(f"  ✓ Controlled terminology check complete")
        
    def validate_iso8601_dates(self):
        """Validate ISO 8601 date format"""
        print("🔍 Phase 3: ISO 8601 Date Validation")
        
        date_vars = ['AESTDTC', 'AEENDTC']
        
        # ISO 8601 patterns (full and partial dates)
        iso_patterns = [
            r'^\d{4}$',  # YYYY
            r'^\d{4}-\d{2}$',  # YYYY-MM
            r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$',  # YYYY-MM-DDTHH:MM
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$',  # YYYY-MM-DDTHH:MM:SS
        ]
        
        for var in date_vars:
            if var in self.df.columns:
                dates = self.df[var].dropna()
                dates = dates[dates.astype(str).str.strip() != '']
                
                if len(dates) > 0:
                    invalid_dates = []
                    for idx, date_val in dates.items():
                        date_str = str(date_val).strip()
                        is_valid = any(re.match(pattern, date_str) for pattern in iso_patterns)
                        if not is_valid:
                            invalid_dates.append((idx + 2, date_str))  # +2 for header and 0-index
                    
                    if invalid_dates:
                        self.add_issue(
                            f'SD0020-{var}',
                            'error',
                            f"{var} has {len(invalid_dates)} non-ISO 8601 dates. Examples: {invalid_dates[:3]}",
                            affected_records=len(invalid_dates),
                            variable=var
                        )
        
        print(f"  ✓ ISO 8601 date check complete")
        
    def validate_fda_serious_event_logic(self):
        """Validate FDA serious event requirements"""
        print("🔍 Phase 4: FDA Serious Event Logic Validation")
        
        if 'AESER' not in self.df.columns:
            return
        
        serious_flags = ['AESDTH', 'AESLIFE', 'AESHOSP', 'AESDISAB', 'AESCONG', 'AESMIE']
        
        # Check if AESER=Y has at least one reason flag
        serious_events = self.df[self.df['AESER'] == 'Y']
        
        if len(serious_events) > 0:
            for idx, row in serious_events.iterrows():
                has_reason = False
                for flag in serious_flags:
                    if flag in self.df.columns and row[flag] == 'Y':
                        has_reason = True
                        break
                
                if not has_reason:
                    self.add_issue(
                        'FDA0001',
                        'error',
                        f"Record {idx + 2}: AESER='Y' but no serious reason flag set (AESDTH/AESLIFE/AESHOSP/AESDISAB/AESCONG/AESMIE)",
                        affected_records=1,
                        variable='AESER'
                    )
        
        # Check if reason flags are Y but AESER is N
        for flag in serious_flags:
            if flag in self.df.columns:
                inconsistent = self.df[(self.df[flag] == 'Y') & (self.df['AESER'] == 'N')]
                if len(inconsistent) > 0:
                    self.add_issue(
                        f'FDA0002-{flag}',
                        'error',
                        f"{len(inconsistent)} records have {flag}='Y' but AESER='N'",
                        affected_records=len(inconsistent),
                        variable=flag
                    )
        
        print(f"  ✓ Serious event logic check complete")
        
    def validate_date_consistency(self):
        """Validate date consistency (start <= end)"""
        print("🔍 Phase 5: Date Consistency Validation")
        
        if 'AESTDTC' not in self.df.columns or 'AEENDTC' not in self.df.columns:
            return
        
        inconsistent_dates = 0
        
        for idx, row in self.df.iterrows():
            start = str(row['AESTDTC']).strip()
            end = str(row['AEENDTC']).strip()
            
            # Skip if either is missing
            if start in ['', 'nan', 'None'] or end in ['', 'nan', 'None']:
                continue
            
            # Compare dates (works for ISO 8601 string comparison)
            if start > end:
                inconsistent_dates += 1
                self.add_issue(
                    f'SM0001-{idx}',
                    'error',
                    f"Record {idx + 2}: AEENDTC ({end}) before AESTDTC ({start})",
                    affected_records=1,
                    variable='AESTDTC,AEENDTC'
                )
        
        print(f"  ✓ Date consistency check complete")
        
    def validate_sequence_integrity(self):
        """Validate AESEQ sequence numbering"""
        print("🔍 Phase 6: Sequence Integrity Validation")
        
        if 'USUBJID' not in self.df.columns or 'AESEQ' not in self.df.columns:
            return
        
        for usubjid, group in self.df.groupby('USUBJID'):
            sequences = sorted(group['AESEQ'].dropna().astype(int).unique())
            
            # Check for gaps
            if len(sequences) > 0:
                expected = list(range(1, max(sequences) + 1))
                missing = set(expected) - set(sequences)
                
                if missing:
                    self.add_issue(
                        f'SEQ0001-{usubjid}',
                        'warning',
                        f"Subject {usubjid} has gaps in AESEQ: missing {sorted(missing)}",
                        affected_records=len(missing),
                        variable='AESEQ'
                    )
            
            # Check for non-positive sequences
            if any(seq <= 0 for seq in sequences):
                self.add_issue(
                    f'SEQ0002-{usubjid}',
                    'error',
                    f"Subject {usubjid} has non-positive AESEQ values",
                    variable='AESEQ'
                )
        
        print(f"  ✓ Sequence integrity check complete")
        
    def validate_usubjid_format(self):
        """Validate USUBJID format compliance"""
        print("🔍 Phase 7: USUBJID Format Validation")
        
        if 'USUBJID' not in self.df.columns or 'STUDYID' not in self.df.columns:
            return
        
        for idx, row in self.df.iterrows():
            usubjid = str(row['USUBJID']).strip()
            studyid = str(row['STUDYID']).strip()
            
            # USUBJID should start with STUDYID
            if not usubjid.startswith(studyid):
                self.add_issue(
                    f'USR0001-{idx}',
                    'warning',
                    f"Record {idx + 2}: USUBJID '{usubjid}' does not start with STUDYID '{studyid}'",
                    affected_records=1,
                    variable='USUBJID'
                )
        
        print(f"  ✓ USUBJID format check complete")
        
    def validate_pinnacle21_rules(self):
        """Additional Pinnacle 21 style checks"""
        print("🔍 Phase 8: Pinnacle 21 Common Rules")
        
        # Check variable length (max 200 chars per SDTM)
        for col in self.df.columns:
            if self.df[col].dtype == 'object':
                max_len = self.df[col].astype(str).str.len().max()
                if max_len > 200:
                    self.add_issue(
                        f'SD0002-{col}',
                        'error',
                        f"{col} has values exceeding 200 characters (max: {max_len})",
                        variable=col
                    )
        
        # Check variable naming (uppercase alphanumeric + underscore)
        for col in self.df.columns:
            if not re.match(r'^[A-Z0-9_]+$', col):
                self.add_issue(
                    f'SD0001-{col}',
                    'warning',
                    f"Variable name '{col}' does not follow SDTM naming convention (uppercase alphanumeric)",
                    variable=col
                )
        
        # Check for trailing/leading spaces in character variables
        for col in self.df.columns:
            if self.df[col].dtype == 'object':
                with_spaces = self.df[col].astype(str).str.strip() != self.df[col].astype(str)
                count = with_spaces.sum()
                if count > 0:
                    self.add_issue(
                        f'DQ0001-{col}',
                        'warning',
                        f"{col} has {count} values with leading/trailing spaces",
                        affected_records=count,
                        variable=col
                    )
        
        print(f"  ✓ Pinnacle 21 rules check complete")
        
    def run_validation(self):
        """Run all validation checks"""
        print("\n" + "="*70)
        print("🔬 SDTM AE DOMAIN COMPREHENSIVE VALIDATION")
        print("   CDISC SDTM-IG 3.4 & FDA Standards")
        print("="*70 + "\n")
        
        print(f"📊 Dataset: {self.file_path}")
        print(f"📝 Total Records: {len(self.df)}")
        print(f"📋 Total Variables: {len(self.df.columns)}\n")
        
        # Run all validation phases
        self.validate_structure()
        self.validate_controlled_terminology()
        self.validate_iso8601_dates()
        self.validate_fda_serious_event_logic()
        self.validate_date_consistency()
        self.validate_sequence_integrity()
        self.validate_usubjid_format()
        self.validate_pinnacle21_rules()
        
        return self.generate_report()
        
    def calculate_compliance_score(self):
        """Calculate overall compliance score"""
        total_checks = len(self.issues) if len(self.issues) > 0 else 1
        
        # Weight by severity
        error_weight = 10
        warning_weight = 3
        info_weight = 1
        
        total_weight = (
            self.error_count * error_weight +
            self.warning_count * warning_weight +
            self.info_count * info_weight
        )
        
        # Calculate score (100% - penalty)
        max_possible_weight = total_checks * error_weight
        if max_possible_weight > 0:
            score = max(0, 100 - (total_weight / max_possible_weight * 100))
        else:
            score = 100
        
        # Critical errors mean automatic score reduction
        if self.error_count > 0:
            score = min(score, 85)
        
        return round(score, 2)
        
    def generate_report(self):
        """Generate comprehensive validation report"""
        print("\n" + "="*70)
        print("📊 VALIDATION RESULTS SUMMARY")
        print("="*70 + "\n")
        
        compliance_score = self.calculate_compliance_score()
        
        print(f"🎯 Overall Compliance Score: {compliance_score}%")
        print(f"❌ Critical Errors: {self.error_count}")
        print(f"⚠️  Warnings: {self.warning_count}")
        print(f"ℹ️  Info: {self.info_count}")
        print(f"📝 Total Issues: {len(self.issues)}\n")
        
        # Top 5 issues
        if self.issues:
            print("🔝 Top 5 Issues Found:\n")
            sorted_issues = sorted(self.issues, key=lambda x: (
                0 if x['severity'] == 'error' else 1 if x['severity'] == 'warning' else 2
            ))
            
            for i, issue in enumerate(sorted_issues[:5], 1):
                severity_icon = '❌' if issue['severity'] == 'error' else '⚠️' if issue['severity'] == 'warning' else 'ℹ️'
                print(f"{i}. {severity_icon} [{issue['rule_id']}] {issue['message']}")
                if issue['affected_records']:
                    print(f"   Affected Records: {issue['affected_records']}")
                print()
        else:
            print("✅ No issues found! Dataset is fully compliant.\n")
        
        # Submission readiness
        print("="*70)
        print("📋 SUBMISSION READINESS ASSESSMENT")
        print("="*70 + "\n")
        
        if compliance_score >= 95 and self.error_count == 0:
            print("✅ READY FOR SUBMISSION")
            print("   • Compliance score >= 95%")
            print("   • Zero critical errors")
            recommendation = "Dataset meets FDA submission standards"
        elif self.error_count == 0:
            print("⚠️  ACCEPTABLE WITH REVIEW")
            print(f"   • Compliance score: {compliance_score}%")
            print("   • No critical errors, but has warnings")
            recommendation = "Address warnings before submission"
        else:
            print("❌ NOT READY FOR SUBMISSION")
            print(f"   • Critical errors found: {self.error_count}")
            print(f"   • Compliance score: {compliance_score}%")
            recommendation = "Fix all critical errors before submission"
        
        print(f"\n💡 Recommendation: {recommendation}\n")
        
        # Return structured results
        return {
            'compliance_score': compliance_score,
            'total_records': len(self.df),
            'error_count': self.error_count,
            'warning_count': self.warning_count,
            'info_count': self.info_count,
            'total_issues': len(self.issues),
            'issues': self.issues,
            'recommendation': recommendation,
            'submission_ready': compliance_score >= 95 and self.error_count == 0
        }

if __name__ == '__main__':
    # Run validation
    validator = AEValidator('/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_sdtm_complete_transform.csv')
    results = validator.run_validation()
    
    # Save results
    output_file = '/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_validation_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"📁 Detailed results saved to: {output_file}\n")

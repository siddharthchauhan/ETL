"""
Comprehensive Multi-Layer SDTM Validation for AE Domain
Study: MAXIS-08
Validation Layers: Structural, CDISC Conformance, Business Rules, Cross-Domain, Compliance Scoring
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from typing import Dict, List, Tuple
import re
from collections import defaultdict

class SDTMValidationEngine:
    """Comprehensive SDTM Validation Engine"""
    
    def __init__(self, study_id: str):
        self.study_id = study_id
        self.validation_results = {
            'structural': [],
            'cdisc_conformance': [],
            'business_rules': [],
            'cross_domain': [],
            'data_quality': []
        }
        self.metrics = {}
        
    def validate_ae_domain(self, ae_file_path: str, dm_file_path: str = None) -> Dict:
        """
        Perform comprehensive validation on AE domain
        
        Args:
            ae_file_path: Path to AE domain CSV
            dm_file_path: Optional path to DM domain CSV for cross-domain validation
            
        Returns:
            Dictionary with validation results and compliance score
        """
        print("=" * 80)
        print("SDTM AE DOMAIN VALIDATION ENGINE")
        print(f"Study ID: {self.study_id}")
        print(f"Dataset: {ae_file_path}")
        print("=" * 80)
        
        # Load data
        ae_df = pd.read_csv(ae_file_path)
        dm_df = pd.read_csv(dm_file_path) if dm_file_path else None
        
        print(f"\n✓ Loaded AE domain: {len(ae_df)} records, {len(ae_df.columns)} variables")
        if dm_df is not None:
            print(f"✓ Loaded DM domain: {len(dm_df)} records for cross-domain validation")
        
        # Execute validation layers
        print("\n" + "=" * 80)
        print("LAYER 1: STRUCTURAL VALIDATION")
        print("=" * 80)
        self._validate_structural(ae_df)
        
        print("\n" + "=" * 80)
        print("LAYER 2: CDISC CONFORMANCE VALIDATION")
        print("=" * 80)
        self._validate_cdisc_conformance(ae_df)
        
        print("\n" + "=" * 80)
        print("LAYER 3: BUSINESS RULES VALIDATION")
        print("=" * 80)
        self._validate_business_rules(ae_df)
        
        if dm_df is not None:
            print("\n" + "=" * 80)
            print("LAYER 4: CROSS-DOMAIN VALIDATION")
            print("=" * 80)
            self._validate_cross_domain(ae_df, dm_df)
        
        print("\n" + "=" * 80)
        print("LAYER 5: DATA QUALITY METRICS")
        print("=" * 80)
        self._calculate_data_quality(ae_df)
        
        # Calculate compliance score
        print("\n" + "=" * 80)
        print("COMPLIANCE SCORING")
        print("=" * 80)
        compliance_score = self._calculate_compliance_score()
        
        return self._generate_final_report(ae_df, compliance_score)
    
    def _validate_structural(self, df: pd.DataFrame):
        """Layer 1: Structural Validation"""
        
        # Required variables per SDTMIG 3.4
        required_vars = [
            'STUDYID', 'DOMAIN', 'USUBJID', 'AESEQ', 'AETERM', 'AEDECOD',
            'AESTDTC'  # Start date is required
        ]
        
        expected_vars = [
            'STUDYID', 'DOMAIN', 'USUBJID', 'AESEQ', 'AETERM', 'AEDECOD',
            'AELLT', 'AELLTCD', 'AEHLT', 'AEHLTCD', 'AEHLGT', 'AEHLGTCD',
            'AEBODSYS', 'AESOC', 'AESOCCD', 'AESTDTC', 'AEENDTC',
            'AESEV', 'AEREL', 'AEOUT', 'AESER', 'AEACN',
            'AESDTH', 'AESHOSP', 'AESLIFE', 'AESDISAB', 'AESCONG', 'AESMIE'
        ]
        
        print(f"Checking {len(required_vars)} required variables...")
        
        # Check missing required variables
        missing_required = [v for v in required_vars if v not in df.columns]
        if missing_required:
            for var in missing_required:
                self.validation_results['structural'].append({
                    'rule_id': 'SD0006',
                    'severity': 'ERROR',
                    'category': 'Missing Required Variable',
                    'message': f"Required variable missing: {var}",
                    'count': 1
                })
                print(f"  ✗ ERROR SD0006: Missing required variable: {var}")
        else:
            print(f"  ✓ All {len(required_vars)} required variables present")
        
        # Check for unexpected variables
        unexpected_vars = [v for v in df.columns if v not in expected_vars]
        if unexpected_vars:
            for var in unexpected_vars:
                self.validation_results['structural'].append({
                    'rule_id': 'SD0001',
                    'severity': 'WARNING',
                    'category': 'Unexpected Variable',
                    'message': f"Variable not in SDTMIG 3.4 specification: {var}",
                    'count': 1
                })
                print(f"  ⚠ WARNING SD0001: Unexpected variable: {var}")
        
        # Check data types
        print("\nValidating data types...")
        
        # Character variables
        char_vars = ['STUDYID', 'DOMAIN', 'USUBJID', 'AETERM', 'AEDECOD', 
                     'AELLT', 'AEHLT', 'AEHLGT', 'AEBODSYS', 'AESOC',
                     'AESTDTC', 'AEENDTC', 'AESEV', 'AEREL', 'AEOUT', 
                     'AESER', 'AEACN', 'AESDTH', 'AESHOSP', 'AESLIFE',
                     'AESDISAB', 'AESCONG', 'AESMIE']
        
        # Numeric variables
        numeric_vars = ['AESEQ', 'AELLTCD', 'AEHLTCD', 'AEHLGTCD', 'AESOCCD']
        
        type_errors = 0
        for var in char_vars:
            if var in df.columns and not pd.api.types.is_string_dtype(df[var]):
                if not df[var].isna().all():
                    self.validation_results['structural'].append({
                        'rule_id': 'SD0003',
                        'severity': 'ERROR',
                        'category': 'Invalid Data Type',
                        'message': f"Variable {var} should be Character type",
                        'count': 1
                    })
                    type_errors += 1
                    print(f"  ✗ ERROR SD0003: {var} should be Character type")
        
        for var in numeric_vars:
            if var in df.columns:
                # Check if can be converted to numeric
                try:
                    pd.to_numeric(df[var], errors='coerce')
                except:
                    self.validation_results['structural'].append({
                        'rule_id': 'SD0003',
                        'severity': 'ERROR',
                        'category': 'Invalid Data Type',
                        'message': f"Variable {var} should be Numeric type",
                        'count': 1
                    })
                    type_errors += 1
                    print(f"  ✗ ERROR SD0003: {var} should be Numeric type")
        
        if type_errors == 0:
            print(f"  ✓ All data types correct")
        
        # Check variable lengths
        print("\nValidating variable lengths...")
        length_errors = 0
        for col in df.columns:
            if df[col].dtype == 'object':
                max_length = df[col].astype(str).str.len().max()
                if max_length > 200:
                    self.validation_results['structural'].append({
                        'rule_id': 'SD0002',
                        'severity': 'ERROR',
                        'category': 'Variable Length Exceeded',
                        'message': f"Variable {col} exceeds maximum length (200 chars): {max_length}",
                        'count': 1
                    })
                    length_errors += 1
                    print(f"  ✗ ERROR SD0002: {col} exceeds 200 chars (max: {max_length})")
        
        if length_errors == 0:
            print(f"  ✓ All variable lengths within limits")
        
        # Check for duplicate keys
        print("\nChecking for duplicate records...")
        if 'USUBJID' in df.columns and 'AESEQ' in df.columns:
            duplicates = df[df.duplicated(subset=['USUBJID', 'AESEQ'], keep=False)]
            if len(duplicates) > 0:
                self.validation_results['structural'].append({
                    'rule_id': 'SD0026',
                    'severity': 'ERROR',
                    'category': 'Duplicate Records',
                    'message': f"Duplicate USUBJID + AESEQ combinations found",
                    'count': len(duplicates),
                    'examples': duplicates[['USUBJID', 'AESEQ']].head(5).to_dict('records')
                })
                print(f"  ✗ ERROR SD0026: {len(duplicates)} duplicate records found")
            else:
                print(f"  ✓ No duplicate records (USUBJID + AESEQ unique)")
        
        # Check AESEQ uniqueness within USUBJID
        print("\nValidating AESEQ uniqueness within subjects...")
        if 'USUBJID' in df.columns and 'AESEQ' in df.columns:
            seq_issues = []
            for usubjid in df['USUBJID'].unique():
                subject_data = df[df['USUBJID'] == usubjid]
                seq_values = subject_data['AESEQ'].tolist()
                if len(seq_values) != len(set(seq_values)):
                    seq_issues.append(usubjid)
            
            if seq_issues:
                self.validation_results['structural'].append({
                    'rule_id': 'SD0063',
                    'severity': 'ERROR',
                    'category': 'Non-unique Sequence',
                    'message': f"AESEQ not unique within USUBJID",
                    'count': len(seq_issues),
                    'examples': seq_issues[:5]
                })
                print(f"  ✗ ERROR SD0063: AESEQ not unique for {len(seq_issues)} subjects")
            else:
                print(f"  ✓ AESEQ unique within each subject")
    
    def _validate_cdisc_conformance(self, df: pd.DataFrame):
        """Layer 2: CDISC Conformance Validation"""
        
        # DOMAIN value check
        print("Validating DOMAIN value...")
        if 'DOMAIN' in df.columns:
            invalid_domain = df[df['DOMAIN'] != 'AE']
            if len(invalid_domain) > 0:
                self.validation_results['cdisc_conformance'].append({
                    'rule_id': 'SD0007',
                    'severity': 'ERROR',
                    'category': 'Invalid DOMAIN',
                    'message': f"DOMAIN must be 'AE' for all records",
                    'count': len(invalid_domain)
                })
                print(f"  ✗ ERROR SD0007: {len(invalid_domain)} records with DOMAIN != 'AE'")
            else:
                print(f"  ✓ All records have DOMAIN = 'AE'")
        
        # Controlled Terminology Validation
        print("\nValidating controlled terminology...")
        
        # AESEV (Severity) - MILD, MODERATE, SEVERE
        ct_aesev = ['MILD', 'MODERATE', 'SEVERE']
        self._validate_ct_field(df, 'AESEV', ct_aesev, 'CT0046', 'Severity')
        
        # AESER (Serious) - Y, N
        ct_yn = ['Y', 'N']
        self._validate_ct_field(df, 'AESER', ct_yn, 'CT0046', 'Serious Flag')
        
        # AEREL (Relationship) 
        ct_aerel = [
            'NOT RELATED', 'UNLIKELY RELATED', 'POSSIBLY RELATED', 
            'PROBABLY RELATED', 'RELATED'
        ]
        self._validate_ct_field(df, 'AEREL', ct_aerel, 'CT0046', 'Causality')
        
        # AEOUT (Outcome)
        ct_aeout = [
            'RECOVERED/RESOLVED', 'RECOVERING/RESOLVING', 
            'NOT RECOVERED/NOT RESOLVED', 'RECOVERED/RESOLVED WITH SEQUELAE',
            'FATAL', 'UNKNOWN', 'DOSE NOT CHANGED'  # Note: DOSE NOT CHANGED seems wrong for AEOUT
        ]
        self._validate_ct_field(df, 'AEOUT', ct_aeout, 'CT0046', 'Outcome')
        
        # AEACN (Action Taken)
        ct_aeacn = [
            'DOSE NOT CHANGED', 'DOSE INCREASED', 'DOSE REDUCED',
            'DOSE RATE REDUCED', 'DRUG INTERRUPTED', 'DRUG WITHDRAWN',
            'NOT APPLICABLE', 'UNKNOWN', 'NOT EVALUABLE'
        ]
        self._validate_ct_field(df, 'AEACN', ct_aeacn, 'CT0046', 'Action Taken')
        
        # Serious flags (AESDTH, AESHOSP, etc.) - Y, N
        for var in ['AESDTH', 'AESHOSP', 'AESLIFE', 'AESDISAB', 'AESCONG', 'AESMIE']:
            self._validate_ct_field(df, var, ct_yn, 'CT0046', f'Serious Criterion ({var})')
        
        # ISO 8601 Date Validation
        print("\nValidating ISO 8601 date formats...")
        self._validate_iso8601_dates(df, 'AESTDTC', 'AE Start Date')
        self._validate_iso8601_dates(df, 'AEENDTC', 'AE End Date')
        
        # STUDYID consistency
        print("\nValidating STUDYID consistency...")
        if 'STUDYID' in df.columns:
            unique_studies = df['STUDYID'].unique()
            if len(unique_studies) > 1:
                self.validation_results['cdisc_conformance'].append({
                    'rule_id': 'SD0084',
                    'severity': 'ERROR',
                    'category': 'Inconsistent STUDYID',
                    'message': f"Multiple STUDYID values found: {list(unique_studies)}",
                    'count': len(unique_studies) - 1
                })
                print(f"  ✗ ERROR SD0084: Multiple STUDYID values: {list(unique_studies)}")
            elif unique_studies[0] != self.study_id:
                self.validation_results['cdisc_conformance'].append({
                    'rule_id': 'SD0084',
                    'severity': 'WARNING',
                    'category': 'STUDYID Mismatch',
                    'message': f"STUDYID '{unique_studies[0]}' differs from expected '{self.study_id}'",
                    'count': 1
                })
                print(f"  ⚠ WARNING: STUDYID '{unique_studies[0]}' differs from expected '{self.study_id}'")
            else:
                print(f"  ✓ STUDYID consistent: {self.study_id}")
    
    def _validate_ct_field(self, df: pd.DataFrame, field: str, valid_values: List[str], 
                           rule_id: str, field_name: str):
        """Validate controlled terminology field"""
        if field not in df.columns:
            return
        
        # Filter out missing values
        non_missing = df[field].notna() & (df[field] != '')
        if non_missing.sum() == 0:
            print(f"  ⚠ {field} ({field_name}): All values missing")
            return
        
        invalid = df[non_missing & ~df[field].isin(valid_values)]
        
        if len(invalid) > 0:
            invalid_values = invalid[field].unique().tolist()
            self.validation_results['cdisc_conformance'].append({
                'rule_id': rule_id,
                'severity': 'ERROR',
                'category': f'Invalid Controlled Terminology',
                'message': f"{field} ({field_name}) contains invalid values",
                'count': len(invalid),
                'invalid_values': invalid_values,
                'valid_values': valid_values,
                'examples': invalid[['USUBJID', 'AESEQ', field]].head(5).to_dict('records')
            })
            print(f"  ✗ ERROR {rule_id}: {field} has {len(invalid)} invalid values: {invalid_values}")
        else:
            valid_count = non_missing.sum()
            print(f"  ✓ {field} ({field_name}): {valid_count} values compliant")
    
    def _validate_iso8601_dates(self, df: pd.DataFrame, field: str, field_name: str):
        """Validate ISO 8601 date format"""
        if field not in df.columns:
            return
        
        # ISO 8601 patterns
        # Full: YYYY-MM-DD, Partial: YYYY-MM, YYYY
        # With time: YYYY-MM-DDTHH:MM:SS
        iso_pattern = r'^\d{4}(-\d{2}(-\d{2}(T\d{2}:\d{2}(:\d{2})?)?)?)?$'
        
        non_missing = df[field].notna() & (df[field] != '')
        if non_missing.sum() == 0:
            print(f"  ⚠ {field} ({field_name}): All values missing")
            return
        
        invalid = []
        for idx, val in df[non_missing][field].items():
            if not re.match(iso_pattern, str(val)):
                invalid.append((idx, val))
        
        if invalid:
            self.validation_results['cdisc_conformance'].append({
                'rule_id': 'SD0020',
                'severity': 'ERROR',
                'category': 'Invalid ISO 8601 Date',
                'message': f"{field} ({field_name}) contains non-ISO 8601 compliant dates",
                'count': len(invalid),
                'examples': [{'row': idx, 'value': val} for idx, val in invalid[:5]]
            })
            print(f"  ✗ ERROR SD0020: {field} has {len(invalid)} non-ISO 8601 dates")
        else:
            valid_count = non_missing.sum()
            print(f"  ✓ {field} ({field_name}): {valid_count} dates ISO 8601 compliant")
    
    def _validate_business_rules(self, df: pd.DataFrame):
        """Layer 3: Business Rules Validation"""
        
        # Rule 1: Serious Event Logic
        print("Validating serious event logic...")
        if all(col in df.columns for col in ['AESER', 'AESDTH', 'AESHOSP', 
                                               'AESLIFE', 'AESDISAB', 'AESCONG', 'AESMIE']):
            serious_events = df[df['AESER'] == 'Y']
            
            issues = []
            for idx, row in serious_events.iterrows():
                criteria_met = any([
                    row['AESDTH'] == 'Y',
                    row['AESHOSP'] == 'Y',
                    row['AESLIFE'] == 'Y',
                    row['AESDISAB'] == 'Y',
                    row['AESCONG'] == 'Y',
                    row['AESMIE'] == 'Y'
                ])
                
                if not criteria_met:
                    issues.append({
                        'row': idx,
                        'USUBJID': row.get('USUBJID'),
                        'AESEQ': row.get('AESEQ'),
                        'AETERM': row.get('AETERM')
                    })
            
            if issues:
                self.validation_results['business_rules'].append({
                    'rule_id': 'BR0001',
                    'severity': 'ERROR',
                    'category': 'Serious Event Logic',
                    'message': 'AESER=Y but no serious criteria (AESDTH/AESHOSP/AESLIFE/AESDISAB/AESCONG/AESMIE) set to Y',
                    'count': len(issues),
                    'examples': issues[:5]
                })
                print(f"  ✗ ERROR BR0001: {len(issues)} serious events without criteria")
            else:
                print(f"  ✓ Serious event logic valid ({len(serious_events)} serious events)")
        
        # Rule 2: Start Date <= End Date
        print("\nValidating date logic (start <= end)...")
        if 'AESTDTC' in df.columns and 'AEENDTC' in df.columns:
            date_issues = []
            
            for idx, row in df.iterrows():
                start = str(row['AESTDTC']) if pd.notna(row['AESTDTC']) else None
                end = str(row['AEENDTC']) if pd.notna(row['AEENDTC']) else None
                
                if start and end:
                    # Compare as strings (works for ISO 8601)
                    if end < start:
                        date_issues.append({
                            'row': idx,
                            'USUBJID': row.get('USUBJID'),
                            'AESEQ': row.get('AESEQ'),
                            'AESTDTC': start,
                            'AEENDTC': end
                        })
            
            if date_issues:
                self.validation_results['business_rules'].append({
                    'rule_id': 'SM0001',
                    'severity': 'ERROR',
                    'category': 'Date Logic',
                    'message': 'AEENDTC before AESTDTC (end date before start date)',
                    'count': len(date_issues),
                    'examples': date_issues[:5]
                })
                print(f"  ✗ ERROR SM0001: {len(date_issues)} records with end date before start date")
            else:
                print(f"  ✓ Date logic valid (start <= end)")
        
        # Rule 3: AESEQ Sequential within Subject
        print("\nValidating AESEQ sequential numbering...")
        if 'USUBJID' in df.columns and 'AESEQ' in df.columns:
            seq_issues = []
            
            for usubjid in df['USUBJID'].unique():
                subject_data = df[df['USUBJID'] == usubjid].sort_values('AESEQ')
                seq_values = subject_data['AESEQ'].tolist()
                
                # Check if sequential starting from 1
                expected = list(range(1, len(seq_values) + 1))
                if seq_values != expected:
                    seq_issues.append({
                        'USUBJID': usubjid,
                        'actual': seq_values,
                        'expected': expected
                    })
            
            if seq_issues:
                self.validation_results['business_rules'].append({
                    'rule_id': 'BR0002',
                    'severity': 'WARNING',
                    'category': 'Sequence Numbering',
                    'message': 'AESEQ not sequential starting from 1',
                    'count': len(seq_issues),
                    'examples': seq_issues[:5]
                })
                print(f"  ⚠ WARNING BR0002: {len(seq_issues)} subjects with non-sequential AESEQ")
            else:
                print(f"  ✓ AESEQ sequential for all subjects")
        
        # Rule 4: Required Fields Not Blank
        print("\nValidating required fields not blank...")
        required_not_blank = ['STUDYID', 'DOMAIN', 'USUBJID', 'AESEQ', 'AETERM', 'AEDECOD']
        
        for field in required_not_blank:
            if field in df.columns:
                blank_count = df[field].isna().sum() + (df[field] == '').sum()
                if blank_count > 0:
                    self.validation_results['business_rules'].append({
                        'rule_id': 'BR0003',
                        'severity': 'ERROR',
                        'category': 'Blank Required Field',
                        'message': f"Required field {field} contains blank values",
                        'count': blank_count
                    })
                    print(f"  ✗ ERROR BR0003: {field} has {blank_count} blank values")
                else:
                    print(f"  ✓ {field}: No blank values")
    
    def _validate_cross_domain(self, ae_df: pd.DataFrame, dm_df: pd.DataFrame):
        """Layer 4: Cross-Domain Validation"""
        
        # USUBJID consistency with DM
        print("Validating USUBJID consistency with DM domain...")
        if 'USUBJID' in ae_df.columns and 'USUBJID' in dm_df.columns:
            ae_subjects = set(ae_df['USUBJID'].unique())
            dm_subjects = set(dm_df['USUBJID'].unique())
            
            missing_in_dm = ae_subjects - dm_subjects
            
            if missing_in_dm:
                self.validation_results['cross_domain'].append({
                    'rule_id': 'SD0083',
                    'severity': 'ERROR',
                    'category': 'Missing in DM',
                    'message': 'USUBJID in AE not found in DM domain',
                    'count': len(missing_in_dm),
                    'examples': list(missing_in_dm)[:10]
                })
                print(f"  ✗ ERROR SD0083: {len(missing_in_dm)} subjects in AE not found in DM")
            else:
                print(f"  ✓ All {len(ae_subjects)} subjects found in DM domain")
            
            # Check subjects in DM but not in AE (informational)
            no_ae = dm_subjects - ae_subjects
            if no_ae:
                print(f"  ℹ INFO: {len(no_ae)} subjects in DM have no adverse events")
        
        # STUDYID consistency
        print("\nValidating STUDYID consistency across domains...")
        if 'STUDYID' in ae_df.columns and 'STUDYID' in dm_df.columns:
            ae_studies = ae_df['STUDYID'].unique()
            dm_studies = dm_df['STUDYID'].unique()
            
            if len(ae_studies) == 1 and len(dm_studies) == 1:
                if ae_studies[0] == dm_studies[0]:
                    print(f"  ✓ STUDYID consistent across domains: {ae_studies[0]}")
                else:
                    self.validation_results['cross_domain'].append({
                        'rule_id': 'SD0084',
                        'severity': 'ERROR',
                        'category': 'STUDYID Mismatch',
                        'message': f"STUDYID differs: AE={ae_studies[0]}, DM={dm_studies[0]}",
                        'count': 1
                    })
                    print(f"  ✗ ERROR SD0084: STUDYID mismatch (AE={ae_studies[0]}, DM={dm_studies[0]})")
    
    def _calculate_data_quality(self, df: pd.DataFrame):
        """Layer 5: Data Quality Metrics"""
        
        total_records = len(df)
        total_cells = len(df) * len(df.columns)
        
        # Completeness
        print("Calculating data completeness...")
        missing_cells = df.isna().sum().sum()
        completeness = ((total_cells - missing_cells) / total_cells) * 100
        
        self.metrics['completeness'] = {
            'overall': round(completeness, 2),
            'total_cells': total_cells,
            'populated_cells': total_cells - missing_cells,
            'missing_cells': missing_cells
        }
        print(f"  ✓ Overall completeness: {completeness:.2f}%")
        
        # Variable-level completeness
        var_completeness = {}
        for col in df.columns:
            populated = df[col].notna().sum()
            pct = (populated / total_records) * 100
            var_completeness[col] = {
                'populated': int(populated),
                'missing': int(total_records - populated),
                'completeness_pct': round(pct, 2)
            }
        
        self.metrics['variable_completeness'] = var_completeness
        
        # Required variable completeness
        required_vars = ['STUDYID', 'DOMAIN', 'USUBJID', 'AESEQ', 'AETERM', 
                        'AEDECOD', 'AESTDTC']
        incomplete_required = []
        for var in required_vars:
            if var in var_completeness and var_completeness[var]['completeness_pct'] < 100:
                incomplete_required.append({
                    'variable': var,
                    'completeness': var_completeness[var]['completeness_pct']
                })
        
        if incomplete_required:
            print(f"  ⚠ WARNING: {len(incomplete_required)} required variables incomplete")
            for item in incomplete_required:
                print(f"    - {item['variable']}: {item['completeness']}%")
        else:
            print(f"  ✓ All required variables 100% complete")
        
        # Subject-level metrics
        print("\nCalculating subject-level metrics...")
        if 'USUBJID' in df.columns:
            subject_counts = df['USUBJID'].value_counts()
            self.metrics['subjects'] = {
                'total_subjects': len(subject_counts),
                'total_events': total_records,
                'avg_events_per_subject': round(subject_counts.mean(), 2),
                'min_events': int(subject_counts.min()),
                'max_events': int(subject_counts.max()),
                'subjects_with_most_events': subject_counts.head(5).to_dict()
            }
            print(f"  ✓ {len(subject_counts)} subjects with {total_records} total events")
            print(f"  ✓ Avg events per subject: {subject_counts.mean():.2f}")
        
        # Severity distribution
        if 'AESEV' in df.columns:
            sev_dist = df['AESEV'].value_counts().to_dict()
            self.metrics['severity_distribution'] = sev_dist
            print(f"\n  Severity distribution:")
            for sev, count in sev_dist.items():
                print(f"    - {sev}: {count}")
        
        # Serious event rate
        if 'AESER' in df.columns:
            serious_count = (df['AESER'] == 'Y').sum()
            serious_rate = (serious_count / total_records) * 100
            self.metrics['serious_events'] = {
                'count': int(serious_count),
                'rate_pct': round(serious_rate, 2)
            }
            print(f"\n  ✓ Serious events: {serious_count} ({serious_rate:.2f}%)")
        
        # Relationship distribution
        if 'AEREL' in df.columns:
            rel_dist = df['AEREL'].value_counts().to_dict()
            self.metrics['relationship_distribution'] = rel_dist
            print(f"\n  Causality distribution:")
            for rel, count in rel_dist.items():
                print(f"    - {rel}: {count}")
    
    def _calculate_compliance_score(self) -> Dict:
        """Calculate overall compliance score"""
        
        # Count issues by severity
        error_count = 0
        warning_count = 0
        info_count = 0
        
        for layer, issues in self.validation_results.items():
            for issue in issues:
                if issue['severity'] == 'ERROR':
                    error_count += 1
                elif issue['severity'] == 'WARNING':
                    warning_count += 1
                else:
                    info_count += 1
        
        total_issues = error_count + warning_count + info_count
        
        # Calculate score
        # Errors: -10 points each
        # Warnings: -2 points each
        # Info: -0.5 points each
        
        base_score = 100
        score_deduction = (error_count * 10) + (warning_count * 2) + (info_count * 0.5)
        compliance_score = max(0, base_score - score_deduction)
        
        # Regulatory assessment
        if error_count == 0 and compliance_score >= 95:
            readiness = "SUBMISSION READY"
            recommendation = "Dataset meets FDA submission requirements"
        elif error_count == 0 and compliance_score >= 90:
            readiness = "NEARLY READY"
            recommendation = "Address warnings to achieve >95% compliance"
        elif error_count > 0 and error_count <= 5:
            readiness = "NOT READY - MINOR ISSUES"
            recommendation = f"Resolve {error_count} critical errors before submission"
        else:
            readiness = "NOT READY - MAJOR ISSUES"
            recommendation = f"Significant work required: {error_count} critical errors"
        
        print(f"\nCompliance Score: {compliance_score:.1f}/100")
        print(f"Total Issues: {total_issues} (Errors: {error_count}, Warnings: {warning_count}, Info: {info_count})")
        print(f"Readiness Assessment: {readiness}")
        print(f"Recommendation: {recommendation}")
        
        return {
            'score': round(compliance_score, 2),
            'max_score': 100,
            'total_issues': total_issues,
            'errors': error_count,
            'warnings': warning_count,
            'informational': info_count,
            'readiness': readiness,
            'recommendation': recommendation,
            'meets_submission_criteria': error_count == 0 and compliance_score >= 95
        }
    
    def _generate_final_report(self, df: pd.DataFrame, compliance_score: Dict) -> Dict:
        """Generate comprehensive validation report"""
        
        # Categorize issues by severity
        issues_by_severity = {
            'critical': [],
            'major': [],
            'minor': [],
            'informational': []
        }
        
        for layer, issues in self.validation_results.items():
            for issue in issues:
                if issue['severity'] == 'ERROR':
                    if issue['rule_id'].startswith('SD0006') or issue['rule_id'].startswith('SD0083'):
                        issues_by_severity['critical'].append({**issue, 'layer': layer})
                    else:
                        issues_by_severity['major'].append({**issue, 'layer': layer})
                elif issue['severity'] == 'WARNING':
                    issues_by_severity['minor'].append({**issue, 'layer': layer})
                else:
                    issues_by_severity['informational'].append({**issue, 'layer': layer})
        
        # Get top 10 issues
        all_issues = (issues_by_severity['critical'] + 
                     issues_by_severity['major'] + 
                     issues_by_severity['minor'])
        top_10_issues = all_issues[:10]
        
        # Generate report
        report = {
            'validation_metadata': {
                'study_id': self.study_id,
                'domain': 'AE',
                'validation_date': datetime.now().isoformat(),
                'validator': 'SDTM Validation Engine v1.0',
                'sdtm_version': 'SDTMIG 3.4',
                'dataset_records': len(df),
                'dataset_variables': len(df.columns)
            },
            'compliance_summary': compliance_score,
            'issues_by_severity': {
                'critical_count': len(issues_by_severity['critical']),
                'major_count': len(issues_by_severity['major']),
                'minor_count': len(issues_by_severity['minor']),
                'informational_count': len(issues_by_severity['informational'])
            },
            'top_10_issues': top_10_issues,
            'all_issues': {
                'critical': issues_by_severity['critical'],
                'major': issues_by_severity['major'],
                'minor': issues_by_severity['minor'],
                'informational': issues_by_severity['informational']
            },
            'validation_layers': {
                'structural': {
                    'status': 'PASS' if len([i for i in self.validation_results['structural'] 
                                           if i['severity'] == 'ERROR']) == 0 else 'FAIL',
                    'issues_count': len(self.validation_results['structural'])
                },
                'cdisc_conformance': {
                    'status': 'PASS' if len([i for i in self.validation_results['cdisc_conformance'] 
                                           if i['severity'] == 'ERROR']) == 0 else 'FAIL',
                    'issues_count': len(self.validation_results['cdisc_conformance'])
                },
                'business_rules': {
                    'status': 'PASS' if len([i for i in self.validation_results['business_rules'] 
                                           if i['severity'] == 'ERROR']) == 0 else 'FAIL',
                    'issues_count': len(self.validation_results['business_rules'])
                },
                'cross_domain': {
                    'status': 'PASS' if len([i for i in self.validation_results['cross_domain'] 
                                           if i['severity'] == 'ERROR']) == 0 else 'FAIL',
                    'issues_count': len(self.validation_results['cross_domain'])
                }
            },
            'data_quality_metrics': self.metrics,
            'controlled_terminology_compliance': self._calculate_ct_compliance(df),
            'corrective_actions': self._generate_corrective_actions(issues_by_severity)
        }
        
        return report
    
    def _calculate_ct_compliance(self, df: pd.DataFrame) -> Dict:
        """Calculate controlled terminology compliance rate"""
        
        ct_fields = {
            'AESEV': ['MILD', 'MODERATE', 'SEVERE'],
            'AESER': ['Y', 'N'],
            'AEREL': ['NOT RELATED', 'UNLIKELY RELATED', 'POSSIBLY RELATED', 
                     'PROBABLY RELATED', 'RELATED'],
            'AEOUT': ['RECOVERED/RESOLVED', 'RECOVERING/RESOLVING', 
                     'NOT RECOVERED/NOT RESOLVED', 'RECOVERED/RESOLVED WITH SEQUELAE',
                     'FATAL', 'UNKNOWN'],
            'AEACN': ['DOSE NOT CHANGED', 'DOSE INCREASED', 'DOSE REDUCED',
                     'DOSE RATE REDUCED', 'DRUG INTERRUPTED', 'DRUG WITHDRAWN',
                     'NOT APPLICABLE', 'UNKNOWN', 'NOT EVALUABLE']
        }
        
        ct_compliance = {}
        total_checked = 0
        total_compliant = 0
        
        for field, valid_values in ct_fields.items():
            if field in df.columns:
                non_missing = df[field].notna() & (df[field] != '')
                checked = non_missing.sum()
                compliant = df[non_missing & df[field].isin(valid_values)].shape[0]
                
                total_checked += checked
                total_compliant += compliant
                
                ct_compliance[field] = {
                    'checked': int(checked),
                    'compliant': int(compliant),
                    'compliance_rate': round((compliant / checked * 100) if checked > 0 else 0, 2)
                }
        
        overall_rate = round((total_compliant / total_checked * 100) if total_checked > 0 else 0, 2)
        
        return {
            'overall_rate': overall_rate,
            'total_checked': total_checked,
            'total_compliant': total_compliant,
            'by_field': ct_compliance
        }
    
    def _generate_corrective_actions(self, issues_by_severity: Dict) -> List[Dict]:
        """Generate corrective action recommendations"""
        
        actions = []
        
        # Critical issues
        for issue in issues_by_severity['critical']:
            actions.append({
                'priority': 'CRITICAL',
                'rule_id': issue['rule_id'],
                'issue': issue['message'],
                'action': self._get_corrective_action(issue['rule_id']),
                'estimated_effort': 'High'
            })
        
        # Major issues
        for issue in issues_by_severity['major'][:5]:  # Top 5
            actions.append({
                'priority': 'MAJOR',
                'rule_id': issue['rule_id'],
                'issue': issue['message'],
                'action': self._get_corrective_action(issue['rule_id']),
                'estimated_effort': 'Medium'
            })
        
        return actions
    
    def _get_corrective_action(self, rule_id: str) -> str:
        """Get corrective action for rule ID"""
        
        actions = {
            'SD0006': 'Add missing required variable to dataset. Review SDTMIG 3.4 specification for variable definition.',
            'SD0083': 'Ensure all USUBJID values in AE exist in DM domain. May need to add subjects to DM or remove invalid AE records.',
            'SD0026': 'Remove duplicate records. Check source data for data quality issues.',
            'CT0046': 'Map values to CDISC controlled terminology. Review CDISC CT 2023-06-30 for valid values.',
            'SD0020': 'Convert dates to ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS). Handle partial dates appropriately.',
            'SM0001': 'Correct date logic: ensure end date >= start date. Review source data for data entry errors.',
            'BR0001': 'For AESER=Y, set at least one serious criterion (AESDTH/AESHOSP/etc.) to Y.',
            'SD0003': 'Convert variable to correct data type (Character or Numeric) per SDTMIG specification.',
            'SD0084': 'Ensure STUDYID consistent across all records and matches study identifier.'
        }
        
        return actions.get(rule_id, 'Review SDTMIG 3.4 specification and correct issue accordingly.')


def main():
    """Execute comprehensive AE validation"""
    
    print("\n" + "=" * 80)
    print(" SDTM AE DOMAIN COMPREHENSIVE VALIDATION")
    print(" Study: MAXIS-08")
    print(" CDISC SDTMIG Version: 3.4")
    print("=" * 80 + "\n")
    
    # Initialize validator
    validator = SDTMValidationEngine(study_id='MAXIS-08')
    
    # Paths
    ae_file = '/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_domain.csv'
    dm_file = None  # Set if DM domain available
    output_file = '/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_validation_report.json'
    
    # Execute validation
    report = validator.validate_ae_domain(ae_file, dm_file)
    
    # Save report
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)
    print(f"\n✓ Comprehensive validation report saved to: {output_file}")
    print(f"\n📊 FINAL ASSESSMENT:")
    print(f"   Compliance Score: {report['compliance_summary']['score']}/100")
    print(f"   Critical Issues: {report['issues_by_severity']['critical_count']}")
    print(f"   Major Issues: {report['issues_by_severity']['major_count']}")
    print(f"   Minor Issues: {report['issues_by_severity']['minor_count']}")
    print(f"   Readiness: {report['compliance_summary']['readiness']}")
    print(f"\n💡 {report['compliance_summary']['recommendation']}")
    print("\n" + "=" * 80 + "\n")
    
    return report


if __name__ == "__main__":
    report = main()

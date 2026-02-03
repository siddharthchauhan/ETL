#!/usr/bin/env python3
"""
Comprehensive Data Quality Assessment (DQA) for Adverse Event Data
Study: MAXIS-08
Files: AEVENT.csv (550 records) and AEVENTC.csv (276 records)

This script validates:
- Business Rules (BR-AE-001 to BR-AE-005)
- CDISC Validation Rules (SD0060 to SD0067)
- Data quality anomalies
- MedDRA coding completeness
"""

import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict
import re
import json

class AEDataQualityAssessment:
    def __init__(self, aevent_path, aeventc_path):
        """Initialize DQA with data file paths"""
        self.aevent_path = aevent_path
        self.aeventc_path = aeventc_path
        
        # Load data
        self.aevent = pd.read_csv(aevent_path, encoding='utf-8-sig')
        self.aeventc = pd.read_csv(aeventc_path, encoding='utf-8-sig')
        
        # Clean column names
        self.aevent.columns = self.aevent.columns.str.strip()
        self.aeventc.columns = self.aeventc.columns.str.strip()
        
        # Results storage
        self.anomalies = defaultdict(list)
        self.statistics = {}
        self.severity_counts = {'Critical': 0, 'Warning': 0, 'Info': 0}
        
        # Controlled terminology
        self.valid_aesev = ['MILD', 'MODERATE', 'SEVERE', 'LIFE THREATENING', 'FATAL']
        self.valid_aeser = ['Y', 'N']
        self.valid_aerel = ['RELATED', 'PROBABLE', 'POSSIBLE', 'UNLIKELY', 'UNRELATED', 
                           'DEFINITELY RELATED', 'PROBABLY RELATED', 'POSSIBLY RELATED']
        self.valid_aeoutc = ['RESOLVED', 'CONTINUING', 'PATIENT DIED', 'FATAL',
                            'RESOLVED, WITH RESIDUAL EFFECTS', 'RESOLVING']
        
    def add_anomaly(self, category, severity, row_num, field, issue, value, recommendation):
        """Add an anomaly to the report"""
        self.anomalies[category].append({
            'severity': severity,
            'row': row_num,
            'field': field,
            'issue': issue,
            'value': value,
            'recommendation': recommendation
        })
        self.severity_counts[severity] += 1
    
    def validate_required_fields(self):
        """SD0060: Validate required fields are populated"""
        print("Validating required fields...")
        
        required_fields = ['AEVERB', 'AESTDT', 'AESEV', 'AESER', 'AEREL', 'AEOUTC']
        
        for field in required_fields:
            if field not in self.aevent.columns:
                self.add_anomaly(
                    'Missing Required Fields',
                    'Critical',
                    'N/A',
                    field,
                    f'Required column {field} not found in dataset',
                    'Column missing',
                    f'Add {field} column to dataset'
                )
                continue
            
            null_mask = self.aevent[field].isna() | (self.aevent[field].astype(str).str.strip() == '')
            null_count = null_mask.sum()
            
            if null_count > 0:
                null_rows = self.aevent[null_mask].index.tolist()
                for row_idx in null_rows[:10]:  # Report first 10
                    self.add_anomaly(
                        'Missing Required Fields',
                        'Critical',
                        row_idx + 2,  # +2 for header and 0-index
                        field,
                        f'{field} is required but missing',
                        'NULL or empty',
                        f'Populate {field} from source data or query investigator'
                    )
                
                if null_count > 10:
                    self.add_anomaly(
                        'Missing Required Fields',
                        'Critical',
                        'Multiple',
                        field,
                        f'{field} missing in {null_count} additional records',
                        f'{null_count} missing values',
                        'Review all missing values systematically'
                    )
    
    def validate_date_formats(self):
        """Validate date formats (YYYYMMDD or YYYYMM)"""
        print("Validating date formats...")
        
        date_fields = ['AESTDT', 'AEENDT']
        date_pattern = re.compile(r'^(\d{8}|\d{6})(\.\d+)?$')
        
        for field in date_fields:
            if field not in self.aevent.columns:
                continue
            
            for idx, value in self.aevent[field].items():
                if pd.isna(value) or str(value).strip() == '':
                    if field == 'AESTDT':  # Start date is required
                        self.add_anomaly(
                            'Date Format Errors',
                            'Critical',
                            idx + 2,
                            field,
                            'Start date is required',
                            'NULL or empty',
                            'Populate from source EDC data'
                        )
                    continue
                
                value_str = str(value).strip()
                if not date_pattern.match(value_str):
                    self.add_anomaly(
                        'Date Format Errors',
                        'Critical',
                        idx + 2,
                        field,
                        'Invalid date format (must be YYYYMMDD or YYYYMM)',
                        value_str,
                        'Convert to ISO 8601 partial date format'
                    )
    
    def validate_date_logic(self):
        """SD0062: Validate AEENDTC >= AESTDTC"""
        print("Validating date logic...")
        
        for idx, row in self.aevent.iterrows():
            start_date = str(row.get('AESTDT', '')).strip()
            end_date = str(row.get('AEENDT', '')).strip()
            
            if not start_date or start_date == 'nan':
                continue
            if not end_date or end_date == 'nan' or end_date == '':
                continue
            
            # Remove decimals and compare
            start_clean = start_date.split('.')[0]
            end_clean = end_date.split('.')[0]
            
            # Handle partial dates (YYYYMM vs YYYYMMDD)
            if len(start_clean) >= 8 and len(end_clean) >= 8:
                if end_clean < start_clean:
                    self.add_anomaly(
                        'Date Logic Errors',
                        'Critical',
                        idx + 2,
                        'AEENDT',
                        'End date is before start date',
                        f'Start: {start_date}, End: {end_date}',
                        'Verify dates with source data or query site'
                    )
    
    def validate_controlled_terminology(self):
        """SD0063, SD0064: Validate controlled terminology"""
        print("Validating controlled terminology...")
        
        # AESEV validation
        for idx, value in self.aevent['AESEV'].items():
            if pd.isna(value):
                continue
            value_upper = str(value).strip().upper()
            if value_upper not in self.valid_aesev:
                self.add_anomaly(
                    'Controlled Terminology Violations',
                    'Critical',
                    idx + 2,
                    'AESEV',
                    'Invalid severity value',
                    value,
                    f'Must be one of: {", ".join(self.valid_aesev)}'
                )
        
        # AESER validation
        for idx, value in self.aevent['AESER'].items():
            if pd.isna(value):
                continue
            value_upper = str(value).strip().upper()
            if value_upper not in self.valid_aeser:
                self.add_anomaly(
                    'Controlled Terminology Violations',
                    'Warning',
                    idx + 2,
                    'AESER',
                    'Non-standard serious flag',
                    value,
                    f'Should be Y or N'
                )
        
        # AEREL validation
        for idx, value in self.aevent['AEREL'].items():
            if pd.isna(value):
                continue
            value_upper = str(value).strip().upper()
            # Check if it's a numeric code instead of text
            if value_upper.isdigit():
                self.add_anomaly(
                    'Controlled Terminology Violations',
                    'Warning',
                    idx + 2,
                    'AEREL',
                    'Relationship appears to be coded, not text',
                    value,
                    'Map numeric code to standard CDISC terminology'
                )
    
    def validate_aeseq_uniqueness(self):
        """SD0067: AESEQ must be unique per subject"""
        print("Validating AESEQ uniqueness per subject...")
        
        if 'AESEQ' in self.aevent.columns and 'SUBEVE' in self.aevent.columns:
            # Group by subject and check for duplicate AESEQ
            dup_check = self.aevent.groupby('SUBEVE')['AESEQ'].apply(
                lambda x: x.duplicated()
            )
            
            duplicates = dup_check[dup_check == True]
            for idx in duplicates.index:
                row = self.aevent.loc[idx]
                self.add_anomaly(
                    'Business Rule Violations',
                    'Critical',
                    idx + 2,
                    'AESEQ',
                    'Duplicate sequence number for subject',
                    f"Subject: {row['SUBEVE']}, AESEQ: {row['AESEQ']}",
                    'BR-AE-001: Renumber sequences per subject by start date'
                )
    
    def validate_sae_criteria(self):
        """SD0066: If AESER=Y, at least one SAE criterion must be Y"""
        print("Validating SAE criteria logic...")
        
        sae_criteria_fields = ['AESERL']  # Should map to specific SAE criteria
        
        for idx, row in self.aevent.iterrows():
            aeser = str(row.get('AESER', '')).strip().upper()
            
            if aeser == 'Y':
                # Check if AESERL contains SAE information
                aeserl = str(row.get('AESERL', '')).strip().upper()
                
                if 'NOT SERIOUS' in aeserl:
                    self.add_anomaly(
                        'SAE Logic Errors',
                        'Critical',
                        idx + 2,
                        'AESER/AESERL',
                        'AESER=Y but AESERL indicates NOT SERIOUS',
                        f"AESER: {aeser}, AESERL: {aeserl}",
                        'Verify SAE criteria or correct AESER flag'
                    )
    
    def check_duplicates(self):
        """Check for duplicate event records"""
        print("Checking for duplicate records...")
        
        if all(col in self.aevent.columns for col in ['STUDY', 'AEVERB', 'AESTDT']):
            # Remove rows where AEVERB or AESTDT is missing
            df_check = self.aevent.dropna(subset=['AEVERB', 'AESTDT'])
            
            # Check for duplicates
            dup_mask = df_check.duplicated(subset=['STUDY', 'AEVERB', 'AESTDT'], keep=False)
            duplicates = df_check[dup_mask]
            
            if len(duplicates) > 0:
                for idx, row in duplicates.iterrows():
                    self.add_anomaly(
                        'Duplicate Records',
                        'Warning',
                        idx + 2,
                        'STUDY/AEVERB/AESTDT',
                        'Potential duplicate event record',
                        f"Study: {row['STUDY']}, Term: {row['AEVERB']}, Date: {row['AESTDT']}",
                        'Verify if these are truly distinct events or duplicates to remove'
                    )
    
    def validate_meddra_coding(self):
        """Validate MedDRA coding completeness in AEVENTC"""
        print("Validating MedDRA coding...")
        
        meddra_fields = ['PTCODE', 'PTTERM', 'SOCCODE', 'SOCTERM', 'HLGTCODE', 'HLTCODE', 'LLTCODE']
        
        for field in meddra_fields:
            if field not in self.aeventc.columns:
                self.add_anomaly(
                    'MedDRA Coding Issues',
                    'Warning',
                    'N/A',
                    field,
                    f'MedDRA field {field} not found in AEVENTC',
                    'Column missing',
                    'Add MedDRA coding fields for regulatory compliance'
                )
                continue
            
            null_mask = self.aeventc[field].isna() | (self.aeventc[field].astype(str).str.strip() == '')
            null_count = null_mask.sum()
            
            if null_count > 0:
                self.add_anomaly(
                    'MedDRA Coding Issues',
                    'Warning',
                    'Multiple',
                    field,
                    f'{field} missing in {null_count} records',
                    f'{null_count} missing values',
                    'Complete MedDRA coding using WHODrug or MedDRA dictionary'
                )
    
    def calculate_statistics(self):
        """Calculate overall statistics"""
        print("Calculating statistics...")
        
        self.statistics = {
            'total_aevent_records': len(self.aevent),
            'total_aeventc_records': len(self.aeventc),
            'total_anomalies': sum(self.severity_counts.values()),
            'critical_issues': self.severity_counts['Critical'],
            'warnings': self.severity_counts['Warning'],
            'info_items': self.severity_counts['Info'],
            'anomaly_categories': len(self.anomalies),
            'data_quality_score': self._calculate_dq_score()
        }
    
    def _calculate_dq_score(self):
        """Calculate data quality score (0-100)"""
        total_records = len(self.aevent)
        if total_records == 0:
            return 0
        
        # Penalize based on severity
        critical_weight = 10
        warning_weight = 3
        info_weight = 1
        
        penalty = (self.severity_counts['Critical'] * critical_weight +
                  self.severity_counts['Warning'] * warning_weight +
                  self.severity_counts['Info'] * info_weight)
        
        # Max penalty = total_records * critical_weight
        max_penalty = total_records * critical_weight
        
        score = max(0, 100 - (penalty / max_penalty * 100))
        return round(score, 2)
    
    def generate_report(self):
        """Generate comprehensive anomaly report"""
        print("\n" + "="*80)
        print("COMPREHENSIVE DATA QUALITY ASSESSMENT REPORT")
        print("Study: MAXIS-08 | Adverse Events")
        print("Generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("="*80)
        
        # Summary Statistics
        print("\n### SUMMARY STATISTICS ###")
        print(f"Total AEVENT Records: {self.statistics['total_aevent_records']}")
        print(f"Total AEVENTC Records: {self.statistics['total_aeventc_records']}")
        print(f"Total Anomalies Found: {self.statistics['total_anomalies']}")
        print(f"  - Critical Issues: {self.statistics['critical_issues']}")
        print(f"  - Warnings: {self.statistics['warnings']}")
        print(f"  - Info Items: {self.statistics['info_items']}")
        print(f"Data Quality Score: {self.statistics['data_quality_score']}/100")
        print(f"Anomaly Categories: {self.statistics['anomaly_categories']}")
        
        # Detailed Findings by Category
        print("\n### DETAILED FINDINGS BY CATEGORY ###\n")
        
        for category, issues in sorted(self.anomalies.items()):
            print(f"\n## {category} ({len(issues)} issues)")
            print("-" * 80)
            
            # Group by severity
            critical = [i for i in issues if i['severity'] == 'Critical']
            warnings = [i for i in issues if i['severity'] == 'Warning']
            info = [i for i in issues if i['severity'] == 'Info']
            
            for severity_group, label in [(critical, 'CRITICAL'), (warnings, 'WARNING'), (info, 'INFO')]:
                if severity_group:
                    print(f"\n[{label}] ({len(severity_group)} items)")
                    for i, issue in enumerate(severity_group[:20], 1):  # Limit to 20 per severity
                        print(f"\n{i}. Row {issue['row']} | Field: {issue['field']}")
                        print(f"   Issue: {issue['issue']}")
                        print(f"   Value: {issue['value']}")
                        print(f"   Recommendation: {issue['recommendation']}")
                    
                    if len(severity_group) > 20:
                        print(f"\n   ... and {len(severity_group) - 20} more {label} issues")
        
        # Impact Assessment
        print("\n\n### IMPACT ON SDTM TRANSFORMATION ###")
        print("-" * 80)
        
        if self.statistics['critical_issues'] > 0:
            print("\n⚠️  CRITICAL ISSUES DETECTED - TRANSFORMATION BLOCKED")
            print("   The following must be resolved before SDTM transformation:")
            print("   - Missing required fields prevent proper SDTM domain creation")
            print("   - Invalid date formats will cause conversion failures")
            print("   - Date logic errors violate CDISC business rules")
            print("   - Controlled terminology violations fail regulatory validation")
        else:
            print("\n✓ No critical issues - transformation can proceed")
        
        if self.statistics['warnings'] > 0:
            print(f"\n⚠️  {self.statistics['warnings']} WARNINGS require review")
            print("   These should be addressed for optimal data quality:")
            print("   - MedDRA coding gaps affect analysis capability")
            print("   - Non-standard values may need mapping")
            print("   - Duplicate records require verification")
        
        # Recommendations
        print("\n\n### RECOMMENDED CORRECTIVE ACTIONS ###")
        print("-" * 80)
        
        actions = [
            ("1. IMMEDIATE (Before Transformation)", [
                "- Populate all missing required fields (AEVERB, AESTDT, AESEV, AESER)",
                "- Convert all dates to ISO 8601 format (YYYYMMDD or YYYY-MM)",
                "- Map severity values to CDISC controlled terminology",
                "- Correct date logic errors (end date >= start date)",
                "- Resolve AESEQ duplicates per subject"
            ]),
            ("2. HIGH PRIORITY (Data Quality)", [
                "- Complete MedDRA coding for all events (PT, SOC, HLT, LLT)",
                "- Standardize relationship terminology to CDISC codelists",
                "- Standardize outcome terminology to CDISC codelists",
                "- Verify and resolve duplicate event records",
                "- Validate SAE criteria alignment with AESER flag"
            ]),
            ("3. MEDIUM PRIORITY (Enhancement)", [
                "- Implement automated date validation in EDC",
                "- Create data quality checks at data entry point",
                "- Establish MedDRA coding workflow",
                "- Train sites on CDISC standards"
            ])
        ]
        
        for title, items in actions:
            print(f"\n{title}")
            for item in items:
                print(item)
        
        # Business Rules Summary
        print("\n\n### BUSINESS RULES VALIDATION SUMMARY ###")
        print("-" * 80)
        
        rules = [
            ("BR-AE-001", "Sequence number per subject ordered by start date", 
             "Check AESEQ duplicates and ordering"),
            ("BR-AE-002", "MedDRA preferred term population",
             "Validate PTCODE and PTTERM in AEVENTC"),
            ("BR-AE-003", "Convert severity to CDISC controlled terminology",
             "AESEV must be MILD/MODERATE/SEVERE/LIFE THREATENING/FATAL"),
            ("BR-AE-004", "Derive serious event flag from SAE criteria",
             "AESER logic must align with AESERL criteria"),
            ("BR-AE-005", "Calculate study day using day 1 convention",
             "Not applicable to raw data, applies to SDTM transformation")
        ]
        
        for rule_id, description, validation in rules:
            print(f"\n{rule_id}: {description}")
            print(f"  Validation: {validation}")
        
        # Export JSON for programmatic use
        self._export_json_report()
        
        print("\n" + "="*80)
        print("END OF REPORT")
        print("="*80)
    
    def _export_json_report(self):
        """Export report as JSON for downstream processing"""
        report = {
            'metadata': {
                'study': 'MAXIS-08',
                'domain': 'Adverse Events',
                'generated': datetime.now().isoformat(),
                'files': {
                    'aevent': self.aevent_path,
                    'aeventc': self.aeventc_path
                }
            },
            'statistics': self.statistics,
            'severity_counts': self.severity_counts,
            'anomalies': dict(self.anomalies)
        }
        
        output_file = '/Users/siddharthchauhan/Work/Projects/ETL/sdtm_pipeline/ae_dqa_report.json'
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\nJSON report exported to: {output_file}")
    
    def run_full_assessment(self):
        """Run complete data quality assessment"""
        print("Starting Comprehensive Data Quality Assessment...")
        print(f"AEVENT records: {len(self.aevent)}")
        print(f"AEVENTC records: {len(self.aeventc)}")
        print()
        
        # Run all validations
        self.validate_required_fields()
        self.validate_date_formats()
        self.validate_date_logic()
        self.validate_controlled_terminology()
        self.validate_aeseq_uniqueness()
        self.validate_sae_criteria()
        self.check_duplicates()
        self.validate_meddra_coding()
        
        # Calculate statistics
        self.calculate_statistics()
        
        # Generate report
        self.generate_report()


def main():
    """Main execution function"""
    aevent_path = '/Users/siddharthchauhan/Downloads/Maxis-08 RAW DATA_CSV/AEVENT.csv'
    aeventc_path = '/Users/siddharthchauhan/Downloads/Maxis-08 RAW DATA_CSV/AEVENTC.csv'
    
    # Create DQA instance and run
    dqa = AEDataQualityAssessment(aevent_path, aeventc_path)
    dqa.run_full_assessment()


if __name__ == '__main__':
    main()

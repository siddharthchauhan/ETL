"""
Direct SDTM AE Domain Transformation
====================================
Transforms AEVENT.csv to SDTM AE format without complex dependencies.
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from typing import Dict, Any, List


class DirectAETransformer:
    """Direct transformation of AE source data to SDTM format."""
    
    # Controlled Terminology Mappings (CDISC CT)
    SEVERITY_MAP = {
        "MILD": "MILD",
        "MODERATE": "MODERATE",
        "SEVERE": "SEVERE",
        "LIFE THREATENING": "LIFE THREATENING",
        "FATAL": "FATAL"
    }
    
    CAUSALITY_MAP = {
        "UNRELATED": "NOT RELATED",
        "UNLIKELY": "UNLIKELY RELATED",
        "POSSIBLE": "POSSIBLY RELATED",
        "PROBABLE": "PROBABLY RELATED",
        "RELATED": "RELATED"
    }
    
    OUTCOME_MAP = {
        "RESOLVED": "RECOVERED/RESOLVED",
        "CONTINUING": "NOT RECOVERED/NOT RESOLVED",
        "RESOLVED, WITH RESIDUAL EFFECTS": "RECOVERED/RESOLVED WITH SEQUELAE",
        "PATIENT DIED": "FATAL"
    }
    
    SERIOUS_MAP = {
        "NOT SERIOUS": "N",
        "UNLIKELY": "N",
        "HOSPITALIZATION/PROLONGATION": "Y"
    }
    
    ACTION_MAP = {
        "NONE": "DOSE NOT CHANGED",
        "INTERRUPTED": "DRUG INTERRUPTED",
        "DISCONTINUED": "DRUG WITHDRAWN"
    }
    
    def __init__(self, source_path: str, study_id: str):
        self.source_path = source_path
        self.study_id = study_id
        self.source_df = None
        self.sdtm_df = None
        self.stats = {
            "ct_mappings": {},
            "warnings": [],
            "source_columns": [],
            "sdtm_variables": []
        }
        
    def load_source(self):
        """Load source AE data."""
        print(f"\n[1/5] Loading source data: {self.source_path}")
        self.source_df = pd.read_csv(self.source_path, encoding='utf-8-sig')
        print(f"  ✓ Loaded {len(self.source_df)} records with {len(self.source_df.columns)} columns")
        self.stats["source_columns"] = list(self.source_df.columns)
        self.stats["source_records"] = len(self.source_df)
        return self.source_df
    
    def transform(self):
        """Transform to SDTM AE format."""
        print("\n[2/5] Transforming to SDTM AE format...")
        
        df = self.source_df.copy()
        ae_records = []
        
        for idx, row in df.iterrows():
            ae_record = {}
            
            # ============ IDENTIFIERS ============
            ae_record['STUDYID'] = self.study_id
            ae_record['DOMAIN'] = 'AE'
            
            # Construct USUBJID: STUDYID-SITEID-SUBJID
            site_id = str(row.get('INVSITE', '')).strip()
            # Clean up scientific notation if present
            if 'E-' in site_id.upper() or 'E+' in site_id.upper():
                try:
                    site_id = f"{float(site_id):.0f}"
                except:
                    pass
            
            # Try different subject ID columns
            subject_id = str(row.get('SUBEVE', row.get('PrimaryKEY', idx+1))).strip()
            
            if site_id and site_id != 'nan':
                ae_record['USUBJID'] = f"{self.study_id}-{site_id}"
            else:
                ae_record['USUBJID'] = f"{self.study_id}-{idx+1:04d}"
            
            ae_record['AESEQ'] = int(row.get('AESEQ', idx + 1))
            
            # ============ TOPIC VARIABLES ============
            # Verbatim term (as reported)
            ae_record['AETERM'] = str(row.get('AEVERB', row.get('PT', ''))).upper()
            
            # Dictionary-derived term (preferred term)
            ae_record['AEDECOD'] = str(row.get('PT', row.get('AEPTT', '')))
            
            # MedDRA Hierarchy (if available)
            ae_record['AELLT'] = str(row.get('AELTT', '')) if pd.notna(row.get('AELTT')) else ''
            ae_record['AELLTCD'] = str(int(row['AELTC'])) if pd.notna(row.get('AELTC')) else ''
            
            ae_record['AEHLT'] = str(row.get('AEHTT', '')) if pd.notna(row.get('AEHTT')) else ''
            ae_record['AEHLTCD'] = str(int(row['AEHTC'])) if pd.notna(row.get('AEHTC')) else ''
            
            ae_record['AEHLGT'] = str(row.get('AEHGT1', '')) if pd.notna(row.get('AEHGT1')) else ''
            ae_record['AEHLGTCD'] = str(int(row['AEHGC'])) if pd.notna(row.get('AEHGC')) else ''
            
            # System Organ Class (SOC)
            ae_record['AEBODSYS'] = str(row.get('AESCT', ''))
            ae_record['AESOC'] = str(row.get('AESCT', ''))
            ae_record['AESOCCD'] = str(int(row['AESCC'])) if pd.notna(row.get('AESCC')) else ''
            
            # ============ TIMING VARIABLES ============
            ae_record['AESTDTC'] = self._convert_to_iso8601(row.get('AESTDT'))
            ae_record['AEENDTC'] = self._convert_to_iso8601(row.get('AEENDT'))
            
            # ============ QUALIFIER VARIABLES (with CT) ============
            
            # Severity
            severity_raw = str(row.get('AESEV', '')).upper().strip()
            ae_record['AESEV'] = self.SEVERITY_MAP.get(severity_raw, severity_raw) if severity_raw and severity_raw != 'NAN' else ''
            
            # Causality
            causality_raw = str(row.get('AEREL', row.get('AERELL', ''))).upper().strip()
            ae_record['AEREL'] = self.CAUSALITY_MAP.get(causality_raw, causality_raw) if causality_raw and causality_raw != 'NAN' else ''
            
            # Outcome
            outcome_raw = str(row.get('AEOUTC', row.get('AEOUTCL', ''))).strip()
            ae_record['AEOUT'] = self.OUTCOME_MAP.get(outcome_raw, outcome_raw) if outcome_raw and outcome_raw != 'nan' else ''
            
            # Serious Event (Y/N)
            serious_raw = str(row.get('AESERL', '')).strip()
            if 'HOSPITALIZATION' in serious_raw.upper() or 'PROLONGATION' in serious_raw.upper():
                ae_record['AESER'] = 'Y'
            elif 'NOT SERIOUS' in serious_raw.upper() or 'UNLIKELY' in serious_raw.upper():
                ae_record['AESER'] = 'N'
            else:
                ae_record['AESER'] = 'Y' if str(row.get('AESER', 'N')).upper() == 'Y' else 'N'
            
            # Action Taken
            action_raw = str(row.get('AEACT', row.get('AEACTL', ''))).strip()
            ae_record['AEACN'] = self.ACTION_MAP.get(action_raw, action_raw) if action_raw and action_raw != 'nan' else ''
            
            # ============ SERIOUS EVENT CRITERIA FLAGS ============
            ae_record['AESDTH'] = 'Y' if 'DIED' in str(row.get('AEOUTC', '')).upper() or 'DEATH' in str(row.get('AEOUTC', '')).upper() else 'N'
            ae_record['AESHOSP'] = 'Y' if 'HOSPITALIZATION' in serious_raw.upper() else 'N'
            ae_record['AESLIFE'] = 'Y' if 'LIFE THREATENING' in severity_raw else 'N'
            ae_record['AESDISAB'] = 'N'  # Not in source
            ae_record['AESCONG'] = 'N'   # Not in source
            ae_record['AESMIE'] = 'N'    # Not in source
            
            ae_records.append(ae_record)
        
        self.sdtm_df = pd.DataFrame(ae_records)
        
        # Track CT usage
        self.stats["ct_mappings"]["AESEV"] = self.sdtm_df['AESEV'].value_counts().to_dict()
        self.stats["ct_mappings"]["AEREL"] = self.sdtm_df['AEREL'].value_counts().to_dict()
        self.stats["ct_mappings"]["AEOUT"] = self.sdtm_df['AEOUT'].value_counts().to_dict()
        self.stats["ct_mappings"]["AESER"] = self.sdtm_df['AESER'].value_counts().to_dict()
        self.stats["ct_mappings"]["AEACN"] = self.sdtm_df['AEACN'].value_counts().to_dict()
        
        self.stats["sdtm_variables"] = list(self.sdtm_df.columns)
        self.stats["sdtm_records"] = len(self.sdtm_df)
        
        print(f"  ✓ Transformed {len(self.sdtm_df)} SDTM AE records")
        print(f"  ✓ Created {len(self.sdtm_df.columns)} SDTM variables")
        
        return self.sdtm_df
    
    def _convert_to_iso8601(self, date_val):
        """Convert various date formats to ISO 8601."""
        if pd.isna(date_val) or str(date_val).strip() == '' or str(date_val).strip().upper() == 'NAN':
            return ''
        
        date_str = str(date_val).strip()
        
        # Handle partial dates (YYYYMM)
        if len(date_str) == 6 and date_str.isdigit():
            return f"{date_str[:4]}-{date_str[4:6]}"
        
        # Handle full dates (YYYYMMDD)
        if len(date_str) == 8 and date_str.isdigit():
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        
        return date_str
    
    def validate(self):
        """Validate SDTM output."""
        print("\n[3/5] Validating SDTM output...")
        
        issues = []
        
        # Required variables check
        required_vars = ['STUDYID', 'DOMAIN', 'USUBJID', 'AESEQ', 'AETERM', 'AEDECOD']
        for var in required_vars:
            if var not in self.sdtm_df.columns:
                issues.append(f"Missing required variable: {var}")
            else:
                null_count = self.sdtm_df[var].isna().sum() + (self.sdtm_df[var] == '').sum()
                if null_count > 0:
                    issues.append(f"{var} has {null_count} null/empty values")
        
        # DOMAIN check
        if 'DOMAIN' in self.sdtm_df.columns:
            if not (self.sdtm_df['DOMAIN'] == 'AE').all():
                issues.append("DOMAIN must be 'AE' for all records")
        
        # Date format check (ISO 8601)
        date_vars = ['AESTDTC', 'AEENDTC']
        for var in date_vars:
            if var in self.sdtm_df.columns:
                non_empty = self.sdtm_df[self.sdtm_df[var].notna() & (self.sdtm_df[var] != '')][var]
                if len(non_empty) > 0:
                    invalid = non_empty[~non_empty.str.match(r'^\d{4}(-\d{2}(-\d{2})?)?$', na=False)]
                    if len(invalid) > 0:
                        issues.append(f"{var} has {len(invalid)} non-ISO 8601 dates (first: {invalid.iloc[0]})")
        
        # Controlled terminology check
        ct_checks = {
            'AESEV': ['MILD', 'MODERATE', 'SEVERE', 'LIFE THREATENING', 'FATAL', ''],
            'AESER': ['Y', 'N', ''],
            'AESDTH': ['Y', 'N'],
            'AESHOSP': ['Y', 'N'],
            'AESLIFE': ['Y', 'N'],
        }
        
        for var, valid_values in ct_checks.items():
            if var in self.sdtm_df.columns:
                invalid_vals = self.sdtm_df[~self.sdtm_df[var].isin(valid_values)][var].unique()
                if len(invalid_vals) > 0:
                    issues.append(f"{var} has invalid values: {invalid_vals[:3]}")
        
        self.stats["warnings"] = issues
        
        if issues:
            print("  ⚠ Validation warnings:")
            for issue in issues[:10]:  # Show first 10
                print(f"    - {issue}")
            if len(issues) > 10:
                print(f"    ... and {len(issues)-10} more")
        else:
            print("  ✓ All validation checks passed")
        
        return issues
    
    def save_outputs(self, ae_path: str, mapping_path: str):
        """Save outputs."""
        print("\n[4/5] Saving outputs...")
        
        # Save AE dataset
        self.sdtm_df.to_csv(ae_path, index=False)
        print(f"  ✓ Saved SDTM AE dataset: {ae_path}")
        
        # Save mapping specification
        mapping_spec = self._create_mapping_spec()
        with open(mapping_path, 'w') as f:
            json.dump(mapping_spec, f, indent=2)
        print(f"  ✓ Saved mapping specification: {mapping_path}")
    
    def _create_mapping_spec(self) -> Dict[str, Any]:
        """Create mapping specification."""
        mappings = [
            {"source": "STUDY", "target": "STUDYID", "rule": "ASSIGN", "ct": None},
            {"source": "DOMAIN", "target": "DOMAIN", "rule": "ASSIGN('AE')", "ct": None},
            {"source": "INVSITE + SUBEVE", "target": "USUBJID", "rule": "CONCAT(STUDYID, '-', INVSITE)", "ct": None},
            {"source": "AESEQ", "target": "AESEQ", "rule": "ASSIGN", "ct": None},
            {"source": "AEVERB/PT", "target": "AETERM", "rule": "UPCASE(AEVERB)", "ct": None},
            {"source": "PT/AEPTT", "target": "AEDECOD", "rule": "ASSIGN", "ct": "MedDRA Preferred Term"},
            {"source": "AELTT", "target": "AELLT", "rule": "ASSIGN", "ct": "MedDRA LLT"},
            {"source": "AEHTT", "target": "AEHLT", "rule": "ASSIGN", "ct": "MedDRA HLT"},
            {"source": "AESCT", "target": "AEBODSYS", "rule": "ASSIGN", "ct": "MedDRA SOC"},
            {"source": "AESCT", "target": "AESOC", "rule": "ASSIGN", "ct": "MedDRA SOC"},
            {"source": "AESTDT", "target": "AESTDTC", "rule": "ISO8601DATEFORMAT", "ct": None},
            {"source": "AEENDT", "target": "AEENDTC", "rule": "ISO8601DATEFORMAT", "ct": None},
            {"source": "AESEV", "target": "AESEV", "rule": "MAP(SEVERITY_MAP)", "ct": "CDISC AESEV"},
            {"source": "AEREL/AERELL", "target": "AEREL", "rule": "MAP(CAUSALITY_MAP)", "ct": "CDISC AEREL"},
            {"source": "AEOUTC/AEOUTCL", "target": "AEOUT", "rule": "MAP(OUTCOME_MAP)", "ct": "CDISC AEOUT"},
            {"source": "AESERL/AESER", "target": "AESER", "rule": "MAP(SERIOUS_MAP)", "ct": "CDISC AESER"},
            {"source": "AEACT/AEACTL", "target": "AEACN", "rule": "MAP(ACTION_MAP)", "ct": "CDISC AEACN"},
            {"source": "DERIVED", "target": "AESDTH", "rule": "IF(AEOUTC contains 'DIED', 'Y', 'N')", "ct": "CDISC NY"},
            {"source": "DERIVED", "target": "AESHOSP", "rule": "IF(AESERL contains 'HOSPITALIZATION', 'Y', 'N')", "ct": "CDISC NY"},
            {"source": "DERIVED", "target": "AESLIFE", "rule": "IF(AESEV='LIFE THREATENING', 'Y', 'N')", "ct": "CDISC NY"},
        ]
        
        return {
            "study_id": self.study_id,
            "source_domain": "AEVENT",
            "target_domain": "AE",
            "generated_date": datetime.now().isoformat(),
            "mappings": mappings,
            "controlled_terminology": {
                "AESEV": list(self.SEVERITY_MAP.values()),
                "AEREL": list(self.CAUSALITY_MAP.values()),
                "AEOUT": list(self.OUTCOME_MAP.values()),
                "AESER": ["Y", "N"],
                "AEACN": list(self.ACTION_MAP.values())
            }
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive report."""
        print("\n[5/5] Generating transformation report...")
        
        report = {
            "transformation_summary": {
                "study_id": self.study_id,
                "domain": "AE",
                "source_file": self.source_path,
                "source_records": self.stats["source_records"],
                "sdtm_records": self.stats["sdtm_records"],
                "transformation_date": datetime.now().isoformat(),
            },
            "controlled_terminology_mappings": self.stats["ct_mappings"],
            "data_quality": {
                "unique_subjects": self.sdtm_df['USUBJID'].nunique(),
                "null_counts": {
                    col: int(self.sdtm_df[col].isna().sum() + (self.sdtm_df[col] == '').sum())
                    for col in self.sdtm_df.columns
                },
                "date_range": {
                    "earliest_start": self.sdtm_df[self.sdtm_df['AESTDTC'] != '']['AESTDTC'].min() if len(self.sdtm_df[self.sdtm_df['AESTDTC'] != '']) > 0 else None,
                    "latest_end": self.sdtm_df[self.sdtm_df['AEENDTC'] != '']['AEENDTC'].max() if len(self.sdtm_df[self.sdtm_df['AEENDTC'] != '']) > 0 else None,
                }
            },
            "validation_issues": self.stats["warnings"],
            "sample_records": self.sdtm_df.head(5).to_dict(orient='records')
        }
        
        print("  ✓ Report generated successfully")
        
        return report


def main():
    """Main transformation workflow."""
    print("="*80)
    print("SDTM AE DOMAIN TRANSFORMATION")
    print("="*80)
    
    # Configuration
    SOURCE_PATH = "/Users/siddharth/Downloads/ETL/ETL/edc_data_temp/Maxis-08 RAW DATA_CSV/AEVENT.csv"
    STUDY_ID = "MAXIS-08"
    AE_OUTPUT = "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_domain.csv"
    MAPPING_OUTPUT = "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_mapping_spec.json"
    REPORT_OUTPUT = "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_transformation_report.json"
    
    try:
        # Execute transformation
        transformer = DirectAETransformer(SOURCE_PATH, STUDY_ID)
        transformer.load_source()
        transformer.transform()
        transformer.validate()
        transformer.save_outputs(AE_OUTPUT, MAPPING_OUTPUT)
        report = transformer.generate_report()
        
        # Save report
        with open(REPORT_OUTPUT, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\n" + "="*80)
        print("TRANSFORMATION COMPLETE")
        print("="*80)
        print(f"\n📊 SUMMARY:")
        print(f"  Source Records:      {report['transformation_summary']['source_records']}")
        print(f"  SDTM AE Records:     {report['transformation_summary']['sdtm_records']}")
        print(f"  Unique Subjects:     {report['data_quality']['unique_subjects']}")
        
        print(f"\n📋 CONTROLLED TERMINOLOGY APPLIED:")
        for var, values in report['controlled_terminology_mappings'].items():
            print(f"  {var}:")
            for val, count in list(values.items())[:5]:
                print(f"    {val}: {count}")
        
        print(f"\n📁 OUTPUT FILES:")
        print(f"  AE Dataset:          {AE_OUTPUT}")
        print(f"  Mapping Spec:        {MAPPING_OUTPUT}")
        print(f"  Report:              {REPORT_OUTPUT}")
        
        print(f"\n⚠  VALIDATION ISSUES:   {len(report['validation_issues'])}")
        for issue in report['validation_issues'][:5]:
            print(f"    - {issue}")
        
        print(f"\n📋 SAMPLE RECORDS (First 3):")
        print("-" * 80)
        for i, record in enumerate(report['sample_records'][:3], 1):
            print(f"\nRecord {i}:")
            for key, value in list(record.items())[:12]:
                print(f"  {key:12s}: {value}")
        
        print(f"\n✅ Transformation completed successfully!\n")
        
        return report
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()

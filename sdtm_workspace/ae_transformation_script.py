"""
SDTM AE Domain Transformation Script
=====================================
Transforms AEVENT.csv source data to SDTM AE domain format.

Requirements:
1. Intelligent mapping specification generation
2. Controlled terminology application
3. ISO 8601 date formatting
4. USUBJID construction
5. MedDRA term mapping
"""

import os
import sys
import pandas as pd
import numpy as np
import json
from datetime import datetime
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, '/Users/siddharth/Downloads/ETL/ETL')

from sdtm_pipeline.transformers.mapping_generator import MappingSpecificationGenerator
from sdtm_pipeline.transformers.intelligent_mapper import IntelligentMapper


class AETransformer:
    """Transform AE source data to SDTM format."""
    
    # Controlled Terminology Mappings
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
        self.mapping_spec = None
        self.transformation_log = []
        
    def load_source_data(self):
        """Load and validate source AE data."""
        print(f"\n[1/6] Loading source data: {self.source_path}")
        self.source_df = pd.read_csv(self.source_path, encoding='utf-8-sig')
        print(f"  ✓ Loaded {len(self.source_df)} records with {len(self.source_df.columns)} columns")
        self.log_event(f"Loaded {len(self.source_df)} source records")
        return self.source_df
    
    def generate_mapping_specification(self, api_key: str):
        """Generate intelligent mapping specification using Claude AI."""
        print("\n[2/6] Generating intelligent SDTM mapping specification...")
        
        generator = MappingSpecificationGenerator(
            api_key=api_key,
            study_id=self.study_id,
            use_knowledge_tools=True
        )
        
        # Generate mapping spec
        self.mapping_spec = generator.generate_mapping(
            df=self.source_df,
            source_name="AEVENT",
            target_domain="AE"
        )
        
        print(f"  ✓ Generated mapping for {len(self.mapping_spec.mappings)} variables")
        self.log_event(f"Generated {len(self.mapping_spec.mappings)} column mappings")
        
        return self.mapping_spec
    
    def transform_to_sdtm(self):
        """Transform source data to SDTM AE format."""
        print("\n[3/6] Transforming data to SDTM AE format...")
        
        df = self.source_df.copy()
        ae_records = []
        
        for idx, row in df.iterrows():
            ae_record = {}
            
            # IDENTIFIERS
            ae_record['STUDYID'] = self.study_id
            ae_record['DOMAIN'] = 'AE'
            
            # Construct USUBJID from INVSITE
            site_id = str(row.get('INVSITE', '')).replace('5.40E-79', '').strip()
            subject_id = str(row.get('SUBEVE', '')).replace('5.40E-79', '').strip()
            if site_id and subject_id:
                ae_record['USUBJID'] = f"{self.study_id}-{site_id}-{subject_id}"
            else:
                ae_record['USUBJID'] = f"{self.study_id}-{idx+1:04d}"
            
            ae_record['AESEQ'] = int(row.get('AESEQ', idx + 1))
            
            # TOPIC VARIABLES
            ae_record['AETERM'] = str(row.get('AEVERB', row.get('PT', ''))).upper()
            ae_record['AEDECOD'] = str(row.get('PT', row.get('AEPTT', '')))
            ae_record['AELLT'] = str(row.get('AELTT', '')) if pd.notna(row.get('AELTT')) else ''
            ae_record['AELLTCD'] = str(row.get('AELTC', '')) if pd.notna(row.get('AELTC')) else ''
            ae_record['AEHLT'] = str(row.get('AEHTT', '')) if pd.notna(row.get('AEHTT')) else ''
            ae_record['AEHLTCD'] = str(row.get('AEHTC', '')) if pd.notna(row.get('AEHTC')) else ''
            ae_record['AEHLGT'] = str(row.get('AEHGT1', '')) if pd.notna(row.get('AEHGT1')) else ''
            ae_record['AEHLGTCD'] = str(row.get('AEHGC', '')) if pd.notna(row.get('AEHGC')) else ''
            ae_record['AEBODSYS'] = str(row.get('AESCT', ''))
            ae_record['AESOC'] = str(row.get('AESCT', ''))
            ae_record['AESOCCD'] = str(row.get('AESCC', '')) if pd.notna(row.get('AESCC')) else ''
            
            # TIMING VARIABLES - Convert to ISO 8601
            ae_record['AESTDTC'] = self.convert_to_iso8601(row.get('AESTDT'))
            ae_record['AEENDTC'] = self.convert_to_iso8601(row.get('AEENDT'))
            
            # QUALIFIER VARIABLES - Apply Controlled Terminology
            severity = str(row.get('AESEV', '')).upper()
            ae_record['AESEV'] = self.SEVERITY_MAP.get(severity, severity)
            
            causality = str(row.get('AEREL', row.get('AERELL', ''))).upper()
            ae_record['AEREL'] = self.CAUSALITY_MAP.get(causality, causality)
            
            outcome = str(row.get('AEOUTC', row.get('AEOUTCL', '')))
            ae_record['AEOUT'] = self.OUTCOME_MAP.get(outcome, outcome)
            
            serious_val = str(row.get('AESERL', ''))
            ae_record['AESER'] = self.SERIOUS_MAP.get(serious_val, 'N' if 'NOT' in serious_val else 'Y')
            
            action = str(row.get('AEACT', row.get('AEACTL', '')))
            ae_record['AEACN'] = self.ACTION_MAP.get(action, action)
            
            # Serious Event Criteria Flags
            ae_record['AESDTH'] = 'Y' if 'DEATH' in str(row.get('AEOUT', '')).upper() or 'DIED' in str(row.get('AEOUTC', '')).upper() else 'N'
            ae_record['AESHOSP'] = 'Y' if 'HOSPITALIZATION' in str(row.get('AESERL', '')).upper() else 'N'
            ae_record['AESLIFE'] = 'Y' if 'LIFE THREATENING' in str(row.get('AESEV', '')).upper() else 'N'
            ae_record['AESDISAB'] = 'N'  # Not captured in source
            ae_record['AESCONG'] = 'N'   # Not captured in source
            ae_record['AESMIE'] = 'N'    # Not captured in source
            
            ae_records.append(ae_record)
        
        self.sdtm_df = pd.DataFrame(ae_records)
        print(f"  ✓ Transformed {len(self.sdtm_df)} SDTM AE records")
        self.log_event(f"Transformed {len(self.sdtm_df)} SDTM records")
        
        return self.sdtm_df
    
    def convert_to_iso8601(self, date_val):
        """Convert various date formats to ISO 8601."""
        if pd.isna(date_val) or str(date_val).strip() == '':
            return ''
        
        date_str = str(date_val).strip()
        
        # Handle partial dates (YYYYMM)
        if len(date_str) == 6 and date_str.isdigit():
            return f"{date_str[:4]}-{date_str[4:6]}"
        
        # Handle full dates (YYYYMMDD)
        if len(date_str) == 8 and date_str.isdigit():
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        
        return date_str
    
    def save_outputs(self, ae_path: str, mapping_path: str):
        """Save SDTM AE dataset and mapping specification."""
        print("\n[4/6] Saving outputs...")
        
        # Save AE dataset
        self.sdtm_df.to_csv(ae_path, index=False)
        print(f"  ✓ Saved SDTM AE dataset: {ae_path}")
        self.log_event(f"Saved AE dataset to {ae_path}")
        
        # Save mapping specification
        if self.mapping_spec:
            mapping_dict = {
                "domain": self.mapping_spec.domain,
                "source_name": self.mapping_spec.source_name,
                "study_id": self.mapping_spec.study_id,
                "generated_date": self.mapping_spec.generated_date,
                "mappings": [
                    {
                        "source_column": m.source_column,
                        "target_variable": m.target_variable,
                        "transformation_rule": m.transformation_rule,
                        "controlled_terminology": m.controlled_terminology
                    }
                    for m in self.mapping_spec.mappings
                ]
            }
            
            with open(mapping_path, 'w') as f:
                json.dump(mapping_dict, f, indent=2)
            print(f"  ✓ Saved mapping specification: {mapping_path}")
            self.log_event(f"Saved mapping spec to {mapping_path}")
    
    def validate_output(self):
        """Validate SDTM output."""
        print("\n[5/6] Validating SDTM output...")
        
        issues = []
        
        # Check required variables
        required_vars = ['STUDYID', 'DOMAIN', 'USUBJID', 'AESEQ', 'AETERM', 'AEDECOD']
        for var in required_vars:
            if var not in self.sdtm_df.columns:
                issues.append(f"Missing required variable: {var}")
            elif self.sdtm_df[var].isna().any():
                null_count = self.sdtm_df[var].isna().sum()
                issues.append(f"{var} has {null_count} null values")
        
        # Check DOMAIN value
        if not (self.sdtm_df['DOMAIN'] == 'AE').all():
            issues.append("DOMAIN must be 'AE' for all records")
        
        # Check date formats (should be ISO 8601)
        date_vars = ['AESTDTC', 'AEENDTC']
        for var in date_vars:
            if var in self.sdtm_df.columns:
                non_empty = self.sdtm_df[self.sdtm_df[var].notna() & (self.sdtm_df[var] != '')][var]
                if len(non_empty) > 0:
                    # Basic ISO 8601 check (YYYY-MM-DD or YYYY-MM)
                    invalid = non_empty[~non_empty.str.match(r'^\d{4}(-\d{2}(-\d{2})?)?$', na=False)]
                    if len(invalid) > 0:
                        issues.append(f"{var} has {len(invalid)} non-ISO 8601 dates")
        
        if issues:
            print("  ⚠ Validation warnings:")
            for issue in issues:
                print(f"    - {issue}")
                self.log_event(f"WARNING: {issue}")
        else:
            print("  ✓ All validation checks passed")
            self.log_event("Validation passed")
        
        return issues
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive transformation report."""
        print("\n[6/6] Generating transformation report...")
        
        # Controlled terminology statistics
        ct_stats = {}
        
        if 'AESEV' in self.sdtm_df.columns:
            ct_stats['AESEV'] = self.sdtm_df['AESEV'].value_counts().to_dict()
        
        if 'AEREL' in self.sdtm_df.columns:
            ct_stats['AEREL'] = self.sdtm_df['AEREL'].value_counts().to_dict()
        
        if 'AEOUT' in self.sdtm_df.columns:
            ct_stats['AEOUT'] = self.sdtm_df['AEOUT'].value_counts().to_dict()
        
        if 'AESER' in self.sdtm_df.columns:
            ct_stats['AESER'] = self.sdtm_df['AESER'].value_counts().to_dict()
        
        # Sample records
        sample_records = self.sdtm_df.head(5).to_dict(orient='records')
        
        report = {
            "transformation_summary": {
                "study_id": self.study_id,
                "domain": "AE",
                "source_file": self.source_path,
                "source_records": len(self.source_df),
                "sdtm_records": len(self.sdtm_df),
                "transformation_date": datetime.now().isoformat(),
            },
            "controlled_terminology_mappings": ct_stats,
            "data_quality": {
                "null_counts": self.sdtm_df.isnull().sum().to_dict(),
                "unique_subjects": self.sdtm_df['USUBJID'].nunique(),
                "date_range": {
                    "earliest_start": self.sdtm_df[self.sdtm_df['AESTDTC'] != '']['AESTDTC'].min() if 'AESTDTC' in self.sdtm_df.columns else None,
                    "latest_end": self.sdtm_df[self.sdtm_df['AEENDTC'] != '']['AEENDTC'].max() if 'AEENDTC' in self.sdtm_df.columns else None,
                }
            },
            "sample_records": sample_records,
            "transformation_log": self.transformation_log
        }
        
        print("  ✓ Report generated successfully")
        
        return report
    
    def log_event(self, message: str):
        """Log transformation event."""
        self.transformation_log.append({
            "timestamp": datetime.now().isoformat(),
            "message": message
        })


def main():
    """Main transformation workflow."""
    print("="*80)
    print("SDTM AE DOMAIN TRANSFORMATION")
    print("="*80)
    
    # Configuration
    SOURCE_PATH = "/Users/siddharth/Downloads/ETL/ETL/edc_data_temp/Maxis-08 RAW DATA_CSV/AEVENT.csv"
    STUDY_ID = "MAXIS-08"
    AE_OUTPUT_PATH = "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_domain.csv"
    MAPPING_SPEC_PATH = "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_mapping_spec.json"
    REPORT_PATH = "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_transformation_report.json"
    
    # Get API key
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not found in environment")
        return
    
    # Initialize transformer
    transformer = AETransformer(SOURCE_PATH, STUDY_ID)
    
    try:
        # Execute transformation pipeline
        transformer.load_source_data()
        transformer.generate_mapping_specification(api_key)
        transformer.transform_to_sdtm()
        transformer.save_outputs(AE_OUTPUT_PATH, MAPPING_SPEC_PATH)
        transformer.validate_output()
        report = transformer.generate_report()
        
        # Save report
        with open(REPORT_PATH, 'w') as f:
            json.dump(report, f, indent=2)
        
        print("\n" + "="*80)
        print("TRANSFORMATION COMPLETE")
        print("="*80)
        print(f"\n📊 SUMMARY:")
        print(f"  Source Records:      {report['transformation_summary']['source_records']}")
        print(f"  SDTM AE Records:     {report['transformation_summary']['sdtm_records']}")
        print(f"  Unique Subjects:     {report['data_quality']['unique_subjects']}")
        print(f"\n📁 OUTPUT FILES:")
        print(f"  AE Dataset:          {AE_OUTPUT_PATH}")
        print(f"  Mapping Spec:        {MAPPING_SPEC_PATH}")
        print(f"  Report:              {REPORT_PATH}")
        print(f"\n✅ Transformation completed successfully!\n")
        
        # Print sample records
        print("\n📋 SAMPLE RECORDS (First 3):")
        print("-" * 80)
        for i, record in enumerate(report['sample_records'][:3], 1):
            print(f"\nRecord {i}:")
            for key, value in list(record.items())[:10]:  # First 10 fields
                print(f"  {key:12s}: {value}")
        
        return report
        
    except Exception as e:
        print(f"\n❌ ERROR during transformation: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()

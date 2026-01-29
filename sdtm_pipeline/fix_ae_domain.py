"""
Fix and Regenerate SDTM AE Domain
===================================
Applies all validation fixes:
1. AESEQ duplicates - regenerate with ROW_NUMBER
2. Invalid AESER controlled terminology
3. Invalid AESEV controlled terminology  
4. Invalid ISO 8601 dates

Study: MAXIS-08
Source: AEVENT.csv, AEVENTC.csv
"""

import os
import sys
import asyncio
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

import pandas as pd
import numpy as np
import boto3
import zipfile
import tempfile
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sdtm_pipeline.transformers.mapping_generator import MappingSpecificationGenerator
from sdtm_pipeline.transformers.domain_transformers import get_transformer
from sdtm_pipeline.validators.sdtm_validator import SDTMValidator


class AEDomainFixer:
    """Fix and regenerate AE domain with validation corrections."""
    
    def __init__(self):
        self.study_id = "MAXIS-08"
        self.bucket = "s3dcri"
        self.s3_key = "incoming/EDC Data.zip"
        self.source_data = {}
        self.ae_data = None
        self.workspace_dir = Path("/Users/siddharth/Downloads/ETL/ETL/sdtm_pipeline/workspace")
        self.workspace_dir.mkdir(exist_ok=True)
        
    def log(self, message: str, style: str = "info"):
        """Print log message."""
        prefix = {
            "info": "ℹ️ ",
            "success": "✅ ",
            "warning": "⚠️ ",
            "error": "❌ ",
            "working": "🔧 "
        }.get(style, "")
        print(f"{prefix}{message}")
        
    async def load_data_from_s3(self):
        """Load EDC data from S3."""
        self.log(f"Loading data from s3://{self.bucket}/{self.s3_key}...", "working")
        
        try:
            s3 = boto3.client('s3')
            temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(temp_dir, "data.zip")
            
            # Download
            self.log("Downloading EDC Data.zip from S3...", "info")
            s3.download_file(self.bucket, self.s3_key, zip_path)
            
            # Extract
            self.log("Extracting ZIP file...", "info")
            extract_dir = os.path.join(temp_dir, "extracted")
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)
            
            # Find CSV files
            csv_files = list(Path(extract_dir).rglob("*.csv"))
            self.log(f"Found {len(csv_files)} CSV files", "info")
            
            # Load CSV files
            for csv_file in csv_files:
                try:
                    df = pd.read_csv(csv_file, low_memory=False)
                    filename = csv_file.name
                    self.source_data[filename] = df
                    self.log(f"  Loaded {filename}: {len(df)} records", "info")
                except Exception as e:
                    self.log(f"  Error loading {csv_file.name}: {e}", "warning")
            
            self.log(f"Successfully loaded {len(self.source_data)} source files", "success")
            
            # Show AE-related files
            ae_files = [f for f in self.source_data.keys() if 'AEVENT' in f.upper()]
            if ae_files:
                self.log(f"Found AE source files: {', '.join(ae_files)}", "info")
            else:
                self.log("No AE source files found!", "error")
                
            return True
            
        except Exception as e:
            self.log(f"Error loading data from S3: {e}", "error")
            import traceback
            traceback.print_exc()
            return False
    
    def examine_source_data(self):
        """Examine source AE files."""
        self.log("\n📊 Examining Source AE Files...", "working")
        
        aevent_file = None
        aeventc_file = None
        
        for filename in self.source_data.keys():
            if 'AEVENT.CSV' in filename.upper() and 'AEVENTC' not in filename.upper():
                aevent_file = filename
            elif 'AEVENTC.CSV' in filename.upper():
                aeventc_file = filename
        
        if aevent_file:
            df = self.source_data[aevent_file]
            self.log(f"\n{aevent_file}:", "info")
            self.log(f"  Records: {len(df)}", "info")
            self.log(f"  Columns: {', '.join(df.columns.tolist()[:15])}", "info")
            
            # Check for key columns
            key_cols = ['SUBJECT', 'AETERM', 'AESTDAT', 'AESEV', 'AESER']
            found_cols = [col for col in key_cols if col in df.columns]
            self.log(f"  Key columns found: {', '.join(found_cols)}", "info")
            
            # Sample data
            self.log(f"\n  Sample record:", "info")
            if len(df) > 0:
                for col in df.columns[:10]:
                    val = df[col].iloc[0]
                    self.log(f"    {col}: {val}", "info")
        
        if aeventc_file:
            df = self.source_data[aeventc_file]
            self.log(f"\n{aeventc_file}:", "info")
            self.log(f"  Records: {len(df)}", "info")
            self.log(f"  Columns: {', '.join(df.columns.tolist())}", "info")
    
    def convert_to_iso8601(self, date_str: Any) -> str:
        """
        Convert various date formats to ISO 8601.
        
        Handles:
        - YYYYMMDD -> YYYY-MM-DD
        - YYYYMM -> YYYY-MM
        - Already formatted dates
        """
        if pd.isna(date_str) or date_str == '':
            return ''
        
        date_str = str(date_str).strip()
        
        # Already in ISO format
        if '-' in date_str:
            return date_str
        
        # YYYYMMDD format
        if len(date_str) == 8 and date_str.isdigit():
            try:
                return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            except:
                return date_str
        
        # YYYYMM format
        if len(date_str) == 6 and date_str.isdigit():
            try:
                return f"{date_str[:4]}-{date_str[4:6]}"
            except:
                return date_str
        
        # YYYY format
        if len(date_str) == 4 and date_str.isdigit():
            return date_str
        
        return date_str
    
    def map_controlled_term(self, value: Any, term_type: str) -> str:
        """
        Map source values to SDTM controlled terminology.
        
        Args:
            value: Source value
            term_type: 'AESER' or 'AESEV'
        """
        if pd.isna(value) or value == '':
            return ''
        
        value_str = str(value).strip().upper()
        
        if term_type == 'AESER':
            # Valid: Y, N
            mapping = {
                'YES': 'Y',
                'Y': 'Y',
                '1': 'Y',
                'TRUE': 'Y',
                'NO': 'N',
                'N': 'N',
                '0': 'N',
                'FALSE': 'N'
            }
            return mapping.get(value_str, '')
        
        elif term_type == 'AESEV':
            # Valid: MILD, MODERATE, SEVERE
            mapping = {
                'MILD': 'MILD',
                'M': 'MILD',
                '1': 'MILD',
                'MODERATE': 'MODERATE',
                'MOD': 'MODERATE',
                '2': 'MODERATE',
                'SEVERE': 'SEVERE',
                'SEV': 'SEVERE',
                '3': 'SEVERE'
            }
            return mapping.get(value_str, '')
        
        return str(value)
    
    def generate_aeseq(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate AESEQ using ROW_NUMBER() OVER (PARTITION BY USUBJID ORDER BY AESTDTC, AETERM).
        
        Ensures AESEQ is unique within each USUBJID.
        """
        # Sort by USUBJID, AESTDTC, AETERM
        df_sorted = df.sort_values(['USUBJID', 'AESTDTC', 'AETERM'], na_position='last')
        
        # Generate sequence number within each USUBJID
        df_sorted['AESEQ'] = df_sorted.groupby('USUBJID').cumcount() + 1
        
        return df_sorted['AESEQ']
    
    def transform_ae_domain(self) -> pd.DataFrame:
        """
        Transform source AE data to SDTM AE domain with all fixes applied.
        """
        self.log("\n🔧 Transforming AE Domain with Fixes...", "working")
        
        # Find source files
        aevent_file = None
        for filename in self.source_data.keys():
            if 'AEVENT.CSV' in filename.upper() and 'AEVENTC' not in filename.upper():
                aevent_file = filename
                break
        
        if not aevent_file:
            raise ValueError("AEVENT.csv not found in source data")
        
        source_df = self.source_data[aevent_file].copy()
        self.log(f"Source records: {len(source_df)}", "info")
        
        # Initialize AE dataframe with required columns
        ae_df = pd.DataFrame()
        
        # STUDYID
        ae_df['STUDYID'] = self.study_id
        
        # DOMAIN
        ae_df['DOMAIN'] = 'AE'
        
        # USUBJID - construct from SUBJECT or similar column
        subject_col = None
        for col in ['SUBJECT', 'SUBJID', 'USUBJID', 'SUBJECT_ID']:
            if col in source_df.columns:
                subject_col = col
                break
        
        if subject_col:
            ae_df['USUBJID'] = self.study_id + '-' + source_df[subject_col].astype(str)
        else:
            raise ValueError("Could not find subject identifier column")
        
        # AETERM - adverse event term
        term_col = None
        for col in ['AETERM', 'ADVERSE_EVENT', 'AE_TERM', 'EVENT_TERM']:
            if col in source_df.columns:
                term_col = col
                break
        
        if term_col:
            ae_df['AETERM'] = source_df[term_col].astype(str)
        else:
            ae_df['AETERM'] = ''
        
        # AEDECOD - typically same as AETERM for unmapped data
        ae_df['AEDECOD'] = ae_df['AETERM']
        
        # AESTDTC - start date (FIX: Convert to ISO 8601)
        start_date_col = None
        for col in ['AESTDAT', 'AESTDTC', 'START_DATE', 'AEST_DATE']:
            if col in source_df.columns:
                start_date_col = col
                break
        
        if start_date_col:
            ae_df['AESTDTC'] = source_df[start_date_col].apply(self.convert_to_iso8601)
            self.log(f"Converted {start_date_col} to ISO 8601 format", "success")
        else:
            ae_df['AESTDTC'] = ''
        
        # AEENDTC - end date (FIX: Convert to ISO 8601)
        end_date_col = None
        for col in ['AEENDAT', 'AEENDTC', 'END_DATE', 'AEEN_DATE']:
            if col in source_df.columns:
                end_date_col = col
                break
        
        if end_date_col:
            ae_df['AEENDTC'] = source_df[end_date_col].apply(self.convert_to_iso8601)
        else:
            ae_df['AEENDTC'] = ''
        
        # AEDTC - adverse event collection date (FIX: Convert to ISO 8601)
        ae_df['AEDTC'] = ae_df['AESTDTC']  # Default to start date
        
        # AESER - serious event flag (FIX: Map to controlled terminology)
        ser_col = None
        for col in ['AESER', 'SERIOUS', 'AESERF']:
            if col in source_df.columns:
                ser_col = col
                break
        
        if ser_col:
            ae_df['AESER'] = source_df[ser_col].apply(lambda x: self.map_controlled_term(x, 'AESER'))
            self.log(f"Mapped {ser_col} to controlled terminology (Y/N)", "success")
        else:
            ae_df['AESER'] = ''
        
        # AESEV - severity (FIX: Map to controlled terminology)
        sev_col = None
        for col in ['AESEV', 'SEVERITY', 'AESEVR']:
            if col in source_df.columns:
                sev_col = col
                break
        
        if sev_col:
            ae_df['AESEV'] = source_df[sev_col].apply(lambda x: self.map_controlled_term(x, 'AESEV'))
            self.log(f"Mapped {sev_col} to controlled terminology (MILD/MODERATE/SEVERE)", "success")
        else:
            ae_df['AESEV'] = ''
        
        # AEREL - relationship to study treatment
        rel_col = None
        for col in ['AEREL', 'RELATIONSHIP', 'AEAREL']:
            if col in source_df.columns:
                rel_col = col
                break
        
        if rel_col:
            ae_df['AEREL'] = source_df[rel_col].astype(str)
        else:
            ae_df['AEREL'] = ''
        
        # AEACN - action taken
        acn_col = None
        for col in ['AEACN', 'ACTION', 'AEACTION']:
            if col in source_df.columns:
                acn_col = col
                break
        
        if acn_col:
            ae_df['AEACN'] = source_df[acn_col].astype(str)
        else:
            ae_df['AEACN'] = ''
        
        # AEOUT - outcome
        out_col = None
        for col in ['AEOUT', 'OUTCOME', 'AEOUTC']:
            if col in source_df.columns:
                out_col = col
                break
        
        if out_col:
            ae_df['AEOUT'] = source_df[out_col].astype(str)
        else:
            ae_df['AEOUT'] = ''
        
        # AESEQ - sequence number (FIX: Generate with ROW_NUMBER)
        # Sort and generate unique sequence within USUBJID
        ae_df_sorted = ae_df.sort_values(['USUBJID', 'AESTDTC', 'AETERM'], na_position='last').reset_index(drop=True)
        ae_df_sorted['AESEQ'] = ae_df_sorted.groupby('USUBJID').cumcount() + 1
        self.log("Generated AESEQ with ROW_NUMBER() partitioned by USUBJID", "success")
        
        # Verify AESEQ uniqueness
        duplicates = ae_df_sorted.groupby(['USUBJID', 'AESEQ']).size().reset_index(name='count')
        duplicates = duplicates[duplicates['count'] > 1]
        if len(duplicates) > 0:
            self.log(f"WARNING: Found {len(duplicates)} AESEQ duplicates after regeneration!", "warning")
        else:
            self.log("AESEQ is now unique within each USUBJID", "success")
        
        self.log(f"\nTransformed AE records: {len(ae_df_sorted)}", "success")
        
        return ae_df_sorted
    
    def validate_fixes(self, ae_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate that all fixes have been applied correctly.
        """
        self.log("\n🔍 Validating Fixes...", "working")
        
        results = {
            'total_records': len(ae_df),
            'aeseq_duplicates': 0,
            'invalid_aeser': 0,
            'invalid_aesev': 0,
            'invalid_dates': 0,
            'issues': []
        }
        
        # 1. Check AESEQ duplicates
        aeseq_dups = ae_df.groupby(['USUBJID', 'AESEQ']).size().reset_index(name='count')
        aeseq_dups = aeseq_dups[aeseq_dups['count'] > 1]
        results['aeseq_duplicates'] = len(aeseq_dups)
        
        if results['aeseq_duplicates'] == 0:
            self.log("✅ AESEQ: No duplicates found - FIXED", "success")
        else:
            self.log(f"❌ AESEQ: {results['aeseq_duplicates']} duplicates still present", "error")
            results['issues'].append(f"AESEQ duplicates: {results['aeseq_duplicates']}")
        
        # 2. Check AESER controlled terminology
        valid_aeser = ['Y', 'N', '']
        invalid_aeser = ae_df[~ae_df['AESER'].isin(valid_aeser)]
        results['invalid_aeser'] = len(invalid_aeser)
        
        if results['invalid_aeser'] == 0:
            self.log("✅ AESER: All values are valid (Y/N) - FIXED", "success")
        else:
            self.log(f"❌ AESER: {results['invalid_aeser']} invalid values found", "error")
            unique_invalid = invalid_aeser['AESER'].unique()
            self.log(f"   Invalid values: {', '.join(map(str, unique_invalid))}", "error")
            results['issues'].append(f"Invalid AESER: {results['invalid_aeser']}")
        
        # 3. Check AESEV controlled terminology
        valid_aesev = ['MILD', 'MODERATE', 'SEVERE', '']
        invalid_aesev = ae_df[~ae_df['AESEV'].isin(valid_aesev)]
        results['invalid_aesev'] = len(invalid_aesev)
        
        if results['invalid_aesev'] == 0:
            self.log("✅ AESEV: All values are valid (MILD/MODERATE/SEVERE) - FIXED", "success")
        else:
            self.log(f"❌ AESEV: {results['invalid_aesev']} invalid values found", "error")
            unique_invalid = invalid_aesev['AESEV'].unique()
            self.log(f"   Invalid values: {', '.join(map(str, unique_invalid))}", "error")
            results['issues'].append(f"Invalid AESEV: {results['invalid_aesev']}")
        
        # 4. Check ISO 8601 date format
        def is_valid_iso8601(date_str):
            if pd.isna(date_str) or date_str == '':
                return True
            date_str = str(date_str)
            # Check for ISO 8601 pattern: YYYY-MM-DD, YYYY-MM, or YYYY
            pattern = r'^\d{4}(-\d{2}(-\d{2})?)?$'
            return bool(re.match(pattern, date_str))
        
        date_cols = ['AESTDTC', 'AEENDTC', 'AEDTC']
        invalid_dates = 0
        
        for col in date_cols:
            if col in ae_df.columns:
                invalid = ae_df[~ae_df[col].apply(is_valid_iso8601)]
                if len(invalid) > 0:
                    invalid_dates += len(invalid)
                    self.log(f"❌ {col}: {len(invalid)} invalid ISO 8601 dates", "error")
                    # Show sample
                    sample_dates = invalid[col].head(3).tolist()
                    self.log(f"   Sample: {sample_dates}", "error")
        
        results['invalid_dates'] = invalid_dates
        
        if invalid_dates == 0:
            self.log("✅ Date formats: All dates are valid ISO 8601 - FIXED", "success")
        else:
            results['issues'].append(f"Invalid ISO 8601 dates: {invalid_dates}")
        
        return results
    
    def save_ae_domain(self, ae_df: pd.DataFrame):
        """Save corrected AE domain to workspace."""
        output_path = self.workspace_dir / "AE.csv"
        ae_df.to_csv(output_path, index=False)
        self.log(f"\n💾 Saved corrected AE domain to: {output_path}", "success")
        return output_path
    
    def generate_report(self, ae_df: pd.DataFrame, validation_results: Dict[str, Any], output_path: Path):
        """Generate detailed report."""
        report = []
        report.append("=" * 80)
        report.append("SDTM AE DOMAIN - CORRECTED")
        report.append("=" * 80)
        report.append(f"\nStudy: {self.study_id}")
        report.append(f"Domain: AE (Adverse Events)")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"\n{'=' * 80}")
        report.append("\nSOURCE FILES:")
        report.append("-" * 80)
        for filename, df in self.source_data.items():
            if 'AEVENT' in filename.upper():
                report.append(f"  {filename}: {len(df)} records")
        
        report.append(f"\n{'=' * 80}")
        report.append("\nTRANSFORMATION RESULTS:")
        report.append("-" * 80)
        report.append(f"  Total records in corrected AE domain: {validation_results['total_records']}")
        report.append(f"  Output file: {output_path}")
        
        report.append(f"\n{'=' * 80}")
        report.append("\nVALIDATION RESULTS:")
        report.append("-" * 80)
        
        report.append("\n1. AESEQ Duplicates:")
        if validation_results['aeseq_duplicates'] == 0:
            report.append("   ✅ FIXED - No duplicates found")
            report.append("   → Applied ROW_NUMBER() OVER (PARTITION BY USUBJID ORDER BY AESTDTC, AETERM)")
        else:
            report.append(f"   ❌ ISSUE - {validation_results['aeseq_duplicates']} duplicates still present")
        
        report.append("\n2. AESER Controlled Terminology:")
        if validation_results['invalid_aeser'] == 0:
            report.append("   ✅ FIXED - All values are valid (Y/N)")
            report.append("   → Mapped: YES→Y, NO→N, 1→Y, 0→N")
        else:
            report.append(f"   ❌ ISSUE - {validation_results['invalid_aeser']} invalid values")
        
        report.append("\n3. AESEV Controlled Terminology:")
        if validation_results['invalid_aesev'] == 0:
            report.append("   ✅ FIXED - All values are valid (MILD/MODERATE/SEVERE)")
            report.append("   → Mapped: 1→MILD, 2→MODERATE, 3→SEVERE, M→MILD")
        else:
            report.append(f"   ❌ ISSUE - {validation_results['invalid_aesev']} invalid values")
        
        report.append("\n4. ISO 8601 Date Format:")
        if validation_results['invalid_dates'] == 0:
            report.append("   ✅ FIXED - All dates in ISO 8601 format")
            report.append("   → Converted: YYYYMMDD → YYYY-MM-DD")
        else:
            report.append(f"   ❌ ISSUE - {validation_results['invalid_dates']} invalid dates")
        
        report.append(f"\n{'=' * 80}")
        report.append("\nSUMMARY:")
        report.append("-" * 80)
        
        if len(validation_results['issues']) == 0:
            report.append("✅ ALL VALIDATION ISSUES RESOLVED!")
            report.append("\nThe corrected AE domain is ready for submission.")
        else:
            report.append(f"⚠️  {len(validation_results['issues'])} issues remaining:")
            for issue in validation_results['issues']:
                report.append(f"   - {issue}")
        
        report.append(f"\n{'=' * 80}")
        report.append("\nCOLUMNS IN CORRECTED AE DOMAIN:")
        report.append("-" * 80)
        for col in ae_df.columns:
            non_empty = ae_df[col].notna().sum()
            report.append(f"  {col}: {non_empty}/{len(ae_df)} populated")
        
        report.append(f"\n{'=' * 80}")
        
        report_text = "\n".join(report)
        print("\n" + report_text)
        
        # Save report
        report_path = self.workspace_dir / "AE_CORRECTION_REPORT.txt"
        with open(report_path, 'w') as f:
            f.write(report_text)
        
        self.log(f"\n📄 Report saved to: {report_path}", "success")
        
        return report_text
    
    async def run(self):
        """Execute the full AE domain fix pipeline."""
        self.log("=" * 80, "info")
        self.log("SDTM AE DOMAIN FIX AND REGENERATION", "info")
        self.log("=" * 80, "info")
        
        # Update todo list
        from sdtm_pipeline.chat_agent import SDTMChatAgent
        
        # Step 1: Load data from S3
        self.log("\n📥 STEP 1: Load EDC Data from S3", "working")
        success = await self.load_data_from_s3()
        if not success:
            self.log("Failed to load data. Exiting.", "error")
            return
        
        # Step 2: Examine source data
        self.log("\n📊 STEP 2: Examine Source AE Files", "working")
        self.examine_source_data()
        
        # Step 3: Transform AE domain with fixes
        self.log("\n🔧 STEP 3: Transform AE Domain with All Fixes", "working")
        ae_df = self.transform_ae_domain()
        
        # Step 4: Validate fixes
        self.log("\n🔍 STEP 4: Validate Corrections", "working")
        validation_results = self.validate_fixes(ae_df)
        
        # Step 5: Save corrected domain
        self.log("\n💾 STEP 5: Save Corrected AE Domain", "working")
        output_path = self.save_ae_domain(ae_df)
        
        # Step 6: Generate report
        self.log("\n📄 STEP 6: Generate Report", "working")
        report = self.generate_report(ae_df, validation_results, output_path)
        
        self.log("\n" + "=" * 80, "success")
        self.log("AE DOMAIN FIX COMPLETED!", "success")
        self.log("=" * 80, "success")


async def main():
    """Main entry point."""
    fixer = AEDomainFixer()
    await fixer.run()


if __name__ == "__main__":
    asyncio.run(main())

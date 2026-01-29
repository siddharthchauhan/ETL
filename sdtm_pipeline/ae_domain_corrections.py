"""
SDTM AE Domain Corrections Script
==================================
Apply specific fixes to AE domain for MAXIS-08 study.

Fixes:
1. AESEQ duplicates - ROW_NUMBER() partition by USUBJID
2. Invalid AESER values - map to Y/N controlled terminology
3. Invalid AESEV values - map to MILD/MODERATE/SEVERE
4. Invalid ISO 8601 dates - convert YYYYMMDD to YYYY-MM-DD
"""

import pandas as pd
import numpy as np
import re
from pathlib import Path
from datetime import datetime


class AEDomainCorrector:
    """Apply corrections to SDTM AE domain."""
    
    def __init__(self, ae_file_path: str):
        """
        Initialize corrector with existing AE file.
        
        Args:
            ae_file_path: Path to existing AE.csv file
        """
        self.ae_file_path = Path(ae_file_path)
        self.ae_df = None
        self.original_count = 0
        self.corrections_applied = {}
        
    def load_ae_domain(self):
        """Load existing AE domain."""
        print(f"📂 Loading AE domain from: {self.ae_file_path}")
        self.ae_df = pd.read_csv(self.ae_file_path, low_memory=False)
        self.original_count = len(self.ae_df)
        print(f"   Loaded {self.original_count} records")
        print(f"   Columns: {', '.join(self.ae_df.columns.tolist())}\n")
        
    def fix_aeseq_duplicates(self):
        """
        Fix AESEQ duplicates by regenerating with ROW_NUMBER().
        AESEQ = ROW_NUMBER() OVER (PARTITION BY USUBJID ORDER BY AESTDTC, AETERM)
        """
        print("🔧 FIX 1: Regenerating AESEQ...")
        
        # Check for duplicates before fix
        before_dups = self.ae_df.groupby(['USUBJID', 'AESEQ']).size()
        before_dup_count = (before_dups > 1).sum()
        print(f"   Before: {before_dup_count} duplicate AESEQ values")
        
        # Sort by USUBJID, AESTDTC, AETERM
        self.ae_df = self.ae_df.sort_values(
            ['USUBJID', 'AESTDTC', 'AETERM'], 
            na_position='last'
        ).reset_index(drop=True)
        
        # Generate new AESEQ within each USUBJID
        self.ae_df['AESEQ'] = self.ae_df.groupby('USUBJID').cumcount() + 1
        
        # Check for duplicates after fix
        after_dups = self.ae_df.groupby(['USUBJID', 'AESEQ']).size()
        after_dup_count = (after_dups > 1).sum()
        print(f"   After: {after_dup_count} duplicate AESEQ values")
        
        if after_dup_count == 0:
            print("   ✅ AESEQ is now unique within each USUBJID\n")
        else:
            print("   ⚠️  Warning: Some duplicates remain\n")
        
        self.corrections_applied['aeseq_fixed'] = before_dup_count - after_dup_count
        
    def fix_aeser_controlled_terminology(self):
        """
        Fix AESER to use valid controlled terminology (Y, N).
        Map: YES→Y, NO→N, 1→Y, 0→N
        """
        print("🔧 FIX 2: Fixing AESER controlled terminology...")
        
        if 'AESER' not in self.ae_df.columns:
            print("   ⚠️  AESER column not found, skipping\n")
            return
        
        # Count invalid values before
        valid_values = ['Y', 'N', '', np.nan]
        before_invalid = self.ae_df[
            ~self.ae_df['AESER'].isin(valid_values) & 
            self.ae_df['AESER'].notna()
        ]
        print(f"   Before: {len(before_invalid)} invalid values")
        if len(before_invalid) > 0:
            print(f"   Invalid values: {before_invalid['AESER'].unique().tolist()}")
        
        # Apply mapping
        def map_aeser(value):
            if pd.isna(value) or value == '':
                return ''
            
            val_str = str(value).strip().upper()
            mapping = {
                'YES': 'Y', 'Y': 'Y', '1': 'Y', 'TRUE': 'Y',
                'NO': 'N', 'N': 'N', '0': 'N', 'FALSE': 'N'
            }
            return mapping.get(val_str, '')
        
        self.ae_df['AESER'] = self.ae_df['AESER'].apply(map_aeser)
        
        # Count invalid values after
        after_invalid = self.ae_df[
            ~self.ae_df['AESER'].isin(valid_values) & 
            self.ae_df['AESER'].notna()
        ]
        print(f"   After: {len(after_invalid)} invalid values")
        
        if len(after_invalid) == 0:
            print("   ✅ All AESER values are now valid (Y/N)\n")
        else:
            print(f"   ⚠️  {len(after_invalid)} invalid values remain\n")
        
        self.corrections_applied['aeser_fixed'] = len(before_invalid) - len(after_invalid)
        
    def fix_aesev_controlled_terminology(self):
        """
        Fix AESEV to use valid controlled terminology (MILD, MODERATE, SEVERE).
        Map: 1/M→MILD, 2→MODERATE, 3→SEVERE
        """
        print("🔧 FIX 3: Fixing AESEV controlled terminology...")
        
        if 'AESEV' not in self.ae_df.columns:
            print("   ⚠️  AESEV column not found, skipping\n")
            return
        
        # Count invalid values before
        valid_values = ['MILD', 'MODERATE', 'SEVERE', '', np.nan]
        before_invalid = self.ae_df[
            ~self.ae_df['AESEV'].isin(valid_values) & 
            self.ae_df['AESEV'].notna()
        ]
        print(f"   Before: {len(before_invalid)} invalid values")
        if len(before_invalid) > 0:
            print(f"   Invalid values: {before_invalid['AESEV'].unique().tolist()}")
        
        # Apply mapping
        def map_aesev(value):
            if pd.isna(value) or value == '':
                return ''
            
            val_str = str(value).strip().upper()
            mapping = {
                'MILD': 'MILD', 'M': 'MILD', '1': 'MILD',
                'MODERATE': 'MODERATE', 'MOD': 'MODERATE', '2': 'MODERATE',
                'SEVERE': 'SEVERE', 'SEV': 'SEVERE', '3': 'SEVERE'
            }
            return mapping.get(val_str, '')
        
        self.ae_df['AESEV'] = self.ae_df['AESEV'].apply(map_aesev)
        
        # Count invalid values after
        after_invalid = self.ae_df[
            ~self.ae_df['AESEV'].isin(valid_values) & 
            self.ae_df['AESEV'].notna()
        ]
        print(f"   After: {len(after_invalid)} invalid values")
        
        if len(after_invalid) == 0:
            print("   ✅ All AESEV values are now valid (MILD/MODERATE/SEVERE)\n")
        else:
            print(f"   ⚠️  {len(after_invalid)} invalid values remain\n")
        
        self.corrections_applied['aesev_fixed'] = len(before_invalid) - len(after_invalid)
        
    def fix_iso8601_dates(self):
        """
        Fix date columns to use ISO 8601 format.
        Convert: YYYYMMDD → YYYY-MM-DD
        """
        print("🔧 FIX 4: Converting dates to ISO 8601 format...")
        
        date_cols = [col for col in self.ae_df.columns if 'DTC' in col or 'DATE' in col.upper()]
        
        if not date_cols:
            date_cols = ['AESTDTC', 'AEENDTC', 'AEDTC']
            date_cols = [col for col in date_cols if col in self.ae_df.columns]
        
        print(f"   Processing date columns: {', '.join(date_cols)}")
        
        def convert_to_iso8601(date_val):
            """Convert date to ISO 8601 format."""
            if pd.isna(date_val) or date_val == '':
                return ''
            
            date_str = str(date_val).strip()
            
            # Already in ISO format (contains hyphen)
            if '-' in date_str:
                return date_str
            
            # YYYYMMDD format (8 digits)
            if len(date_str) == 8 and date_str.isdigit():
                try:
                    return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                except:
                    return date_str
            
            # YYYYMM format (6 digits)
            if len(date_str) == 6 and date_str.isdigit():
                try:
                    return f"{date_str[:4]}-{date_str[4:6]}"
                except:
                    return date_str
            
            # YYYY format (4 digits)
            if len(date_str) == 4 and date_str.isdigit():
                return date_str
            
            return date_str
        
        def is_valid_iso8601(date_str):
            """Check if date is in valid ISO 8601 format."""
            if pd.isna(date_str) or date_str == '':
                return True
            date_str = str(date_str)
            # Pattern: YYYY-MM-DD, YYYY-MM, or YYYY
            pattern = r'^\d{4}(-\d{2}(-\d{2})?)?$'
            return bool(re.match(pattern, date_str))
        
        total_fixed = 0
        
        for col in date_cols:
            # Count invalid before
            before_invalid = self.ae_df[
                ~self.ae_df[col].apply(is_valid_iso8601) & 
                self.ae_df[col].notna()
            ]
            
            if len(before_invalid) > 0:
                print(f"   {col}: {len(before_invalid)} invalid dates")
                # Show sample
                sample_dates = before_invalid[col].head(3).tolist()
                print(f"      Sample: {sample_dates}")
            
            # Apply conversion
            self.ae_df[col] = self.ae_df[col].apply(convert_to_iso8601)
            
            # Count invalid after
            after_invalid = self.ae_df[
                ~self.ae_df[col].apply(is_valid_iso8601) & 
                self.ae_df[col].notna()
            ]
            
            fixed_count = len(before_invalid) - len(after_invalid)
            if fixed_count > 0:
                print(f"      → Fixed {fixed_count} dates")
                total_fixed += fixed_count
        
        if total_fixed > 0:
            print(f"   ✅ Converted {total_fixed} dates to ISO 8601 format\n")
        else:
            print("   ✅ All dates are already in ISO 8601 format\n")
        
        self.corrections_applied['dates_fixed'] = total_fixed
        
    def validate_corrections(self):
        """Validate that all corrections have been applied successfully."""
        print("=" * 80)
        print("🔍 VALIDATION RESULTS")
        print("=" * 80)
        
        issues_found = []
        
        # 1. Check AESEQ uniqueness
        print("\n1. AESEQ Uniqueness:")
        aeseq_dups = self.ae_df.groupby(['USUBJID', 'AESEQ']).size()
        dup_count = (aeseq_dups > 1).sum()
        
        if dup_count == 0:
            print("   ✅ PASS - No duplicate AESEQ values within USUBJID")
        else:
            print(f"   ❌ FAIL - {dup_count} duplicate AESEQ values found")
            issues_found.append(f"AESEQ duplicates: {dup_count}")
        
        # 2. Check AESER controlled terminology
        print("\n2. AESER Controlled Terminology:")
        if 'AESER' in self.ae_df.columns:
            valid_aeser = ['Y', 'N', '', np.nan]
            invalid_aeser = self.ae_df[
                ~self.ae_df['AESER'].isin(valid_aeser) & 
                self.ae_df['AESER'].notna()
            ]
            
            if len(invalid_aeser) == 0:
                print("   ✅ PASS - All AESER values are valid (Y/N)")
            else:
                print(f"   ❌ FAIL - {len(invalid_aeser)} invalid AESER values")
                print(f"      Invalid: {invalid_aeser['AESER'].unique().tolist()}")
                issues_found.append(f"Invalid AESER: {len(invalid_aeser)}")
        
        # 3. Check AESEV controlled terminology
        print("\n3. AESEV Controlled Terminology:")
        if 'AESEV' in self.ae_df.columns:
            valid_aesev = ['MILD', 'MODERATE', 'SEVERE', '', np.nan]
            invalid_aesev = self.ae_df[
                ~self.ae_df['AESEV'].isin(valid_aesev) & 
                self.ae_df['AESEV'].notna()
            ]
            
            if len(invalid_aesev) == 0:
                print("   ✅ PASS - All AESEV values are valid (MILD/MODERATE/SEVERE)")
            else:
                print(f"   ❌ FAIL - {len(invalid_aesev)} invalid AESEV values")
                print(f"      Invalid: {invalid_aesev['AESEV'].unique().tolist()}")
                issues_found.append(f"Invalid AESEV: {len(invalid_aesev)}")
        
        # 4. Check ISO 8601 date format
        print("\n4. ISO 8601 Date Format:")
        
        def is_valid_iso8601(date_str):
            if pd.isna(date_str) or date_str == '':
                return True
            date_str = str(date_str)
            pattern = r'^\d{4}(-\d{2}(-\d{2})?)?$'
            return bool(re.match(pattern, date_str))
        
        date_cols = [col for col in self.ae_df.columns if 'DTC' in col]
        total_invalid_dates = 0
        
        for col in date_cols:
            invalid_dates = self.ae_df[
                ~self.ae_df[col].apply(is_valid_iso8601) & 
                self.ae_df[col].notna()
            ]
            
            if len(invalid_dates) > 0:
                print(f"   ❌ {col}: {len(invalid_dates)} invalid ISO 8601 dates")
                total_invalid_dates += len(invalid_dates)
        
        if total_invalid_dates == 0:
            print("   ✅ PASS - All dates are in ISO 8601 format")
        else:
            issues_found.append(f"Invalid dates: {total_invalid_dates}")
        
        print("\n" + "=" * 80)
        
        if len(issues_found) == 0:
            print("✅ ALL VALIDATION CHECKS PASSED!")
            print("=" * 80)
            return True
        else:
            print(f"❌ {len(issues_found)} VALIDATION ISSUES FOUND:")
            for issue in issues_found:
                print(f"   - {issue}")
            print("=" * 80)
            return False
        
    def save_corrected_domain(self, output_path: str = None):
        """Save corrected AE domain to file."""
        if output_path is None:
            output_path = self.ae_file_path.parent / "AE_CORRECTED.csv"
        else:
            output_path = Path(output_path)
        
        print(f"\n💾 Saving corrected AE domain to: {output_path}")
        self.ae_df.to_csv(output_path, index=False)
        print(f"   Saved {len(self.ae_df)} records\n")
        
        return output_path
        
    def generate_report(self, output_file_path: Path):
        """Generate detailed correction report."""
        report = []
        report.append("=" * 80)
        report.append("SDTM AE DOMAIN - CORRECTION REPORT")
        report.append("=" * 80)
        report.append(f"\nStudy: MAXIS-08")
        report.append(f"Domain: AE (Adverse Events)")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"\nSource File: {self.ae_file_path}")
        report.append(f"Output File: {output_file_path}")
        report.append(f"Total Records: {len(self.ae_df)}")
        
        report.append(f"\n{'=' * 80}")
        report.append("CORRECTIONS APPLIED")
        report.append("=" * 80)
        
        report.append("\n1. AESEQ Duplicates:")
        report.append(f"   - Fixed: {self.corrections_applied.get('aeseq_fixed', 0)} duplicates")
        report.append("   - Method: ROW_NUMBER() OVER (PARTITION BY USUBJID ORDER BY AESTDTC, AETERM)")
        
        report.append("\n2. AESER Controlled Terminology:")
        report.append(f"   - Fixed: {self.corrections_applied.get('aeser_fixed', 0)} invalid values")
        report.append("   - Mapping: YES→Y, NO→N, 1→Y, 0→N")
        
        report.append("\n3. AESEV Controlled Terminology:")
        report.append(f"   - Fixed: {self.corrections_applied.get('aesev_fixed', 0)} invalid values")
        report.append("   - Mapping: 1→MILD, 2→MODERATE, 3→SEVERE, M→MILD")
        
        report.append("\n4. ISO 8601 Date Format:")
        report.append(f"   - Fixed: {self.corrections_applied.get('dates_fixed', 0)} dates")
        report.append("   - Conversion: YYYYMMDD → YYYY-MM-DD")
        
        report.append(f"\n{'=' * 80}")
        report.append("COLUMN SUMMARY")
        report.append("=" * 80)
        
        for col in self.ae_df.columns:
            non_null = self.ae_df[col].notna().sum()
            pct = (non_null / len(self.ae_df)) * 100
            report.append(f"  {col}: {non_null}/{len(self.ae_df)} ({pct:.1f}%) populated")
        
        report.append(f"\n{'=' * 80}")
        
        report_text = "\n".join(report)
        print("\n" + report_text)
        
        # Save report
        report_path = output_file_path.parent / "AE_CORRECTION_REPORT.txt"
        with open(report_path, 'w') as f:
            f.write(report_text)
        
        print(f"\n📄 Report saved to: {report_path}")
        
        return report_path
        
    def run_all_corrections(self, output_path: str = None):
        """Run all corrections and save result."""
        print("=" * 80)
        print("SDTM AE DOMAIN - APPLYING CORRECTIONS")
        print("=" * 80)
        print()
        
        # Load data
        self.load_ae_domain()
        
        # Apply all fixes
        self.fix_aeseq_duplicates()
        self.fix_aeser_controlled_terminology()
        self.fix_aesev_controlled_terminology()
        self.fix_iso8601_dates()
        
        # Validate
        all_valid = self.validate_corrections()
        
        # Save
        output_file = self.save_corrected_domain(output_path)
        
        # Generate report
        self.generate_report(output_file)
        
        print("\n" + "=" * 80)
        if all_valid:
            print("✅ CORRECTIONS COMPLETED SUCCESSFULLY!")
        else:
            print("⚠️  CORRECTIONS COMPLETED WITH WARNINGS")
        print("=" * 80)
        
        return output_file, all_valid


def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python ae_domain_corrections.py <path_to_AE.csv> [output_path]")
        print("\nExample:")
        print("  python ae_domain_corrections.py /path/to/AE.csv")
        print("  python ae_domain_corrections.py /path/to/AE.csv /path/to/AE_CORRECTED.csv")
        sys.exit(1)
    
    ae_file = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    corrector = AEDomainCorrector(ae_file)
    corrector.run_all_corrections(output_path)


if __name__ == "__main__":
    main()

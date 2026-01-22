#!/usr/bin/env python3
"""
SDTM AE Domain Validation Script
=================================

Performs comprehensive validation of the transformed AE domain data
against CDISC SDTM-IG 3.4 specifications.

Author: SDTM Pipeline
Date: 2025-01-22
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import re

class AEValidator:
    """Validator for SDTM AE domain"""
    
    def __init__(self, ae_file):
        self.ae_file = ae_file
        self.ae_df = None
        self.errors = []
        self.warnings = []
        self.info = []
        
        # Required variables per SDTM-IG 3.4
        self.required_vars = ["STUDYID", "DOMAIN", "USUBJID", "AESEQ", "AETERM", "AESTDTC"]
        
        # Expected variables
        self.expected_vars = self.required_vars + [
            "AEDECOD", "AEENDTC", "AESEV", "AESER", "AEREL", 
            "AEACN", "AEOUT", "VISITNUM", "VISIT"
        ]
        
        # Controlled terminology
        self.ct = {
            "AESEV": ["MILD", "MODERATE", "SEVERE"],
            "AESER": ["Y", "N"],
            "NY": ["Y", "N"],
            "AEOUT": ["RECOVERED/RESOLVED", "RECOVERING/RESOLVING", 
                     "NOT RECOVERED/NOT RESOLVED", "RECOVERED/RESOLVED WITH SEQUELAE",
                     "FATAL", "UNKNOWN"]
        }
    
    def load_data(self):
        """Load the AE dataset"""
        try:
            self.ae_df = pd.read_csv(self.ae_file)
            self.info.append(f"Loaded {len(self.ae_df)} records from {self.ae_file}")
            return True
        except Exception as e:
            self.errors.append(f"Failed to load file: {str(e)}")
            return False
    
    def check_required_variables(self):
        """Check for presence of required variables"""
        missing_vars = [var for var in self.required_vars if var not in self.ae_df.columns]
        
        if missing_vars:
            self.errors.append(f"Missing required variables: {', '.join(missing_vars)}")
        else:
            self.info.append("✓ All required variables present")
        
        # Check for null values in required variables
        for var in self.required_vars:
            if var in self.ae_df.columns:
                null_count = self.ae_df[var].isna().sum()
                if null_count > 0:
                    self.errors.append(f"Variable {var} has {null_count} null values")
    
    def check_domain_values(self):
        """Validate DOMAIN and STUDYID values"""
        if "DOMAIN" in self.ae_df.columns:
            invalid_domain = self.ae_df[self.ae_df["DOMAIN"] != "AE"]
            if len(invalid_domain) > 0:
                self.errors.append(f"Found {len(invalid_domain)} records with DOMAIN != 'AE'")
            else:
                self.info.append("✓ DOMAIN = 'AE' for all records")
        
        if "STUDYID" in self.ae_df.columns:
            studies = self.ae_df["STUDYID"].unique()
            if len(studies) == 1:
                self.info.append(f"✓ Single study: {studies[0]}")
            else:
                self.warnings.append(f"Multiple study IDs found: {', '.join(studies)}")
    
    def check_uniqueness(self):
        """Check uniqueness of key combinations"""
        if all(var in self.ae_df.columns for var in ["USUBJID", "AESEQ"]):
            duplicates = self.ae_df.duplicated(subset=["USUBJID", "AESEQ"], keep=False)
            dup_count = duplicates.sum()
            
            if dup_count > 0:
                self.errors.append(f"Found {dup_count} duplicate USUBJID + AESEQ combinations")
            else:
                self.info.append("✓ USUBJID + AESEQ is unique")
    
    def check_date_formats(self):
        """Validate ISO 8601 date formats"""
        date_vars = ["AESTDTC", "AEENDTC", "AEDTC"]
        iso8601_pattern = r'^\d{4}(-\d{2}(-\d{2})?)?$'
        
        for var in date_vars:
            if var in self.ae_df.columns:
                # Filter out empty strings and nulls
                non_empty = self.ae_df[var].dropna()
                non_empty = non_empty[non_empty != ""]
                
                if len(non_empty) > 0:
                    invalid = non_empty[~non_empty.astype(str).str.match(iso8601_pattern)]
                    if len(invalid) > 0:
                        self.errors.append(f"Variable {var} has {len(invalid)} invalid ISO 8601 dates")
                        # Show examples
                        examples = invalid.head(3).tolist()
                        self.errors.append(f"  Examples: {examples}")
                    else:
                        self.info.append(f"✓ {var} dates are in ISO 8601 format")
    
    def check_date_consistency(self):
        """Check date logic consistency"""
        if all(var in self.ae_df.columns for var in ["AESTDTC", "AEENDTC"]):
            # Check end date >= start date
            both_present = self.ae_df[
                (self.ae_df["AESTDTC"].notna()) & 
                (self.ae_df["AESTDTC"] != "") &
                (self.ae_df["AEENDTC"].notna()) & 
                (self.ae_df["AEENDTC"] != "")
            ].copy()
            
            if len(both_present) > 0:
                invalid_dates = both_present[both_present["AEENDTC"] < both_present["AESTDTC"]]
                if len(invalid_dates) > 0:
                    self.warnings.append(f"Found {len(invalid_dates)} records where AEENDTC < AESTDTC")
    
    def check_controlled_terminology(self):
        """Validate controlled terminology values"""
        
        # Check AESEV
        if "AESEV" in self.ae_df.columns:
            non_empty = self.ae_df["AESEV"].dropna()
            non_empty = non_empty[non_empty != ""]
            invalid = non_empty[~non_empty.isin(self.ct["AESEV"])]
            
            if len(invalid) > 0:
                unique_invalid = invalid.unique()
                self.errors.append(f"AESEV has {len(invalid)} invalid values: {list(unique_invalid)}")
            else:
                self.info.append(f"✓ AESEV values conform to controlled terminology")
        
        # Check AESER
        if "AESER" in self.ae_df.columns:
            non_empty = self.ae_df["AESER"].dropna()
            non_empty = non_empty[non_empty != ""]
            invalid = non_empty[~non_empty.isin(self.ct["AESER"])]
            
            if len(invalid) > 0:
                unique_invalid = invalid.unique()
                self.errors.append(f"AESER has {len(invalid)} invalid values: {list(unique_invalid)}")
            else:
                self.info.append(f"✓ AESER values conform to controlled terminology")
        
        # Check AEOUT
        if "AEOUT" in self.ae_df.columns:
            non_empty = self.ae_df["AEOUT"].dropna()
            non_empty = non_empty[non_empty != ""]
            invalid = non_empty[~non_empty.isin(self.ct["AEOUT"])]
            
            if len(invalid) > 0:
                unique_invalid = invalid.unique()
                self.warnings.append(f"AEOUT has {len(invalid)} non-standard values: {list(unique_invalid)}")
    
    def check_serious_event_logic(self):
        """Validate serious event logic"""
        if "AESER" in self.ae_df.columns:
            serious_criteria = ["AESDTH", "AESHOSP", "AESDISAB", "AESCONG", "AESLIFE", "AESMIE"]
            available_criteria = [var for var in serious_criteria if var in self.ae_df.columns]
            
            if available_criteria:
                # Check if AESER='Y' has at least one criteria flag set
                serious_events = self.ae_df[self.ae_df["AESER"] == "Y"]
                
                if len(serious_events) > 0:
                    missing_criteria = 0
                    for idx, row in serious_events.iterrows():
                        has_criteria = any(row.get(var) == "Y" for var in available_criteria)
                        if not has_criteria:
                            missing_criteria += 1
                    
                    if missing_criteria > 0:
                        self.warnings.append(
                            f"{missing_criteria} serious events (AESER='Y') have no serious criteria flags set"
                        )
    
    def check_fatal_outcome_logic(self):
        """Check if FATAL outcome has AESDTH='Y'"""
        if all(var in self.ae_df.columns for var in ["AEOUT", "AESDTH"]):
            fatal_events = self.ae_df[self.ae_df["AEOUT"] == "FATAL"]
            
            if len(fatal_events) > 0:
                missing_death_flag = fatal_events[fatal_events["AESDTH"] != "Y"]
                if len(missing_death_flag) > 0:
                    self.warnings.append(
                        f"{len(missing_death_flag)} FATAL outcomes do not have AESDTH='Y'"
                    )
    
    def generate_statistics(self):
        """Generate descriptive statistics"""
        stats = {
            "total_records": len(self.ae_df),
            "total_subjects": self.ae_df["USUBJID"].nunique() if "USUBJID" in self.ae_df.columns else 0,
            "total_variables": len(self.ae_df.columns),
            "date_range": {},
            "severity_distribution": {},
            "serious_events": 0,
            "outcomes_distribution": {}
        }
        
        # Date range
        if "AESTDTC" in self.ae_df.columns:
            valid_dates = self.ae_df["AESTDTC"].dropna()
            valid_dates = valid_dates[valid_dates != ""]
            if len(valid_dates) > 0:
                stats["date_range"] = {
                    "min": valid_dates.min(),
                    "max": valid_dates.max()
                }
        
        # Severity distribution
        if "AESEV" in self.ae_df.columns:
            stats["severity_distribution"] = self.ae_df["AESEV"].value_counts().to_dict()
        
        # Serious events count
        if "AESER" in self.ae_df.columns:
            stats["serious_events"] = (self.ae_df["AESER"] == "Y").sum()
        
        # Outcomes distribution
        if "AEOUT" in self.ae_df.columns:
            stats["outcomes_distribution"] = self.ae_df["AEOUT"].value_counts().to_dict()
        
        return stats
    
    def calculate_compliance_score(self):
        """Calculate overall compliance score"""
        total_checks = 0
        passed_checks = 0
        
        # Count checks
        checks = [
            (len(self.errors) == 0, 10),  # No errors (weight: 10)
            (len(self.warnings) == 0, 5),  # No warnings (weight: 5)
            (len(self.required_vars) == sum(1 for v in self.required_vars if v in self.ae_df.columns), 20),  # Required vars
            (all(self.ae_df[v].notna().all() for v in self.required_vars if v in self.ae_df.columns), 15),  # No nulls
        ]
        
        for passed, weight in checks:
            total_checks += weight
            if passed:
                passed_checks += weight
        
        score = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        return round(score, 2)
    
    def run_validation(self):
        """Run all validation checks"""
        print("="*80)
        print("SDTM AE Domain Validation")
        print("="*80)
        
        if not self.load_data():
            return None
        
        print("\n[1/9] Checking required variables...")
        self.check_required_variables()
        
        print("[2/9] Checking domain values...")
        self.check_domain_values()
        
        print("[3/9] Checking uniqueness...")
        self.check_uniqueness()
        
        print("[4/9] Checking date formats...")
        self.check_date_formats()
        
        print("[5/9] Checking date consistency...")
        self.check_date_consistency()
        
        print("[6/9] Checking controlled terminology...")
        self.check_controlled_terminology()
        
        print("[7/9] Checking serious event logic...")
        self.check_serious_event_logic()
        
        print("[8/9] Checking fatal outcome logic...")
        self.check_fatal_outcome_logic()
        
        print("[9/9] Generating statistics...")
        stats = self.generate_statistics()
        
        # Calculate compliance score
        compliance_score = self.calculate_compliance_score()
        
        # Compile results
        results = {
            "validation_date": datetime.now().isoformat(),
            "file_validated": str(self.ae_file),
            "compliance_score": compliance_score,
            "statistics": stats,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "summary": {
                "total_errors": len(self.errors),
                "total_warnings": len(self.warnings),
                "total_info": len(self.info),
                "status": "PASS" if len(self.errors) == 0 else "FAIL"
            }
        }
        
        return results
    
    def print_report(self, results):
        """Print validation report"""
        print("\n" + "="*80)
        print("VALIDATION REPORT")
        print("="*80)
        
        print(f"\nCompliance Score: {results['compliance_score']}%")
        print(f"Status: {results['summary']['status']}")
        
        print(f"\n📊 STATISTICS:")
        stats = results['statistics']
        print(f"   - Total Records: {stats['total_records']}")
        print(f"   - Unique Subjects: {stats['total_subjects']}")
        print(f"   - Total Variables: {stats['total_variables']}")
        print(f"   - Serious Events: {stats['serious_events']}")
        
        if stats['date_range']:
            print(f"   - Date Range: {stats['date_range']['min']} to {stats['date_range']['max']}")
        
        if stats['severity_distribution']:
            print(f"\n   Severity Distribution:")
            for sev, count in stats['severity_distribution'].items():
                print(f"     • {sev}: {count}")
        
        if stats['outcomes_distribution']:
            print(f"\n   Outcomes Distribution:")
            for outcome, count in stats['outcomes_distribution'].items():
                print(f"     • {outcome}: {count}")
        
        print(f"\n❌ ERRORS ({len(results['errors'])}):")
        if results['errors']:
            for i, error in enumerate(results['errors'], 1):
                print(f"   {i}. {error}")
        else:
            print("   None")
        
        print(f"\n⚠️  WARNINGS ({len(results['warnings'])}):")
        if results['warnings']:
            for i, warning in enumerate(results['warnings'], 1):
                print(f"   {i}. {warning}")
        else:
            print("   None")
        
        print(f"\n✓ INFO ({len(results['info'])}):")
        for i, info in enumerate(results['info'], 1):
            print(f"   {i}. {info}")
        
        print("\n" + "="*80)

def main():
    """Main validation function"""
    ae_file = Path("/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae.csv")
    
    if not ae_file.exists():
        print(f"Error: File not found: {ae_file}")
        return
    
    validator = AEValidator(ae_file)
    results = validator.run_validation()
    
    if results:
        validator.print_report(results)
        
        # Save results to JSON
        output_file = ae_file.parent / "ae_validation_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✓ Validation results saved to: {output_file}")

if __name__ == "__main__":
    main()

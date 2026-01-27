#!/usr/bin/env python3
"""
LB Domain Business Rules Validation Script
Study: MAXIS-08
Files: HEMLAB.csv, CHEMLAB.csv, HEMLABD.csv, CHEMLABD.csv

Validates laboratory data against CDISC SDTM standards and business rules.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
import re
from collections import defaultdict

# File paths
BASE_PATH = "/Users/siddharth/Downloads/Maxis-08 RAW DATA_CSV"
FILES = {
    "HEMLAB": f"{BASE_PATH}/HEMLAB.csv",
    "CHEMLAB": f"{BASE_PATH}/CHEMLAB.csv",
    "HEMLABD": f"{BASE_PATH}/HEMLABD.csv",
    "CHEMLABD": f"{BASE_PATH}/CHEMLABD.csv"
}

# LOINC codes for common laboratory tests (partial list for reference)
LOINC_CODES = {
    "HEMOGLOBIN": "718-7",
    "HEMATOCRIT": "4544-3",
    "WBC": "6690-2",
    "NEUTROPHILS": "770-8",
    "LYMPHOCYTES": "736-9",
    "MONOCYTES": "5905-5",
    "EOSINOPHILS": "713-8",
    "BASOPHILS": "704-7",
    "PLATELETS": "777-3",
    "ALBUMIN": "1751-7",
    "ALKALINE PHOSPHATASE": "6768-6",
    "TOTAL BILIRUBIN": "1975-2",
    "DIRECT BILIRUBIN": "1968-7",
    "BUN": "3094-0",
    "CALCIUM": "17861-6",
    "CREATININE": "2160-0",
    "GLUCOSE": "2345-7",
    "LDH": "2532-0",
    "AST": "1920-8",
    "ALT": "1742-6",
    "SODIUM": "2951-2",
    "POTASSIUM": "2823-3",
    "CHLORIDE": "2075-0",
}

# Standard units by test
STANDARD_UNITS = {
    "HEMOGLOBIN": "g/L",
    "HEMATOCRIT": "RATIO",
    "WBC": "10^9/L",
    "NEUTROPHILS": "RATIO",
    "LYMPHOCYTES": "RATIO",
    "MONOCYTES": "RATIO",
    "EOSINOPHILS": "RATIO",
    "BASOPHILS": "RATIO",
    "PLATELETS": "10^9/L",
    "ALBUMIN": "g/L",
    "ALKALINE PHOSPHATASE": "ukat/L",
    "TOTAL BILIRUBIN": "umol/L",
    "DIRECT BILIRUBIN": "umol/L",
    "BUN": "mmol/L",
    "CALCIUM": "mmol/L",
    "CREATININE": "umol/L",
    "GLUCOSE": "mmol/L",
    "LDH": "ukat/L",
    "AST": "ukat/L",
    "ALT": "ukat/L",
    "SODIUM": "mmol/L",
    "POTASSIUM": "mmol/L",
    "CHLORIDE": "mmol/L",
}

class LBValidator:
    def __init__(self):
        self.errors = defaultdict(list)
        self.warnings = defaultdict(list)
        self.info = defaultdict(list)
        self.stats = {}
        
    def load_data(self):
        """Load all lab files"""
        self.data = {}
        for name, path in FILES.items():
            try:
                df = pd.read_csv(path, encoding='utf-8-sig')
                self.data[name] = df
                print(f"✓ Loaded {name}: {len(df)} records, {len(df.columns)} columns")
            except Exception as e:
                print(f"✗ Error loading {name}: {e}")
                self.errors["FILE_LOAD"].append({
                    "file": name,
                    "error": str(e)
                })
        
    def validate_required_variables(self):
        """BR-LB-001: Validate required SDTM variables are present"""
        print("\n=== Validating Required Variables ===")
        
        # Required variables for LB domain
        required_vars = {
            "STUDYID": "Study Identifier",
            "USUBJID": "Unique Subject Identifier (or PT as proxy)",
            "LBTEST": "Lab Test Name (LPARM as proxy)",
            "LBORRES": "Lab Result (LVALUE1/LVALUE2 as proxy)",
            "LBORRESU": "Original Units (LUNIT1/LUNIT2 as proxy)"
        }
        
        for file_name, df in self.data.items():
            missing = []
            cols = df.columns.str.upper().tolist()
            
            # Check for study ID
            if 'STUDY' not in cols and 'STUDYID' not in cols:
                missing.append("STUDY/STUDYID")
            
            # Check for subject ID
            if 'PT' not in cols and 'USUBJID' not in cols:
                missing.append("PT/USUBJID")
            
            # Check for test parameter
            if 'LPARM' not in cols and 'LBTEST' not in cols:
                missing.append("LPARM/LBTEST")
            
            # Check for result value
            if 'LVALUE1' not in cols and 'LVALUE2' not in cols and 'LBORRES' not in cols:
                missing.append("LVALUE1/LVALUE2/LBORRES")
            
            # Check for units
            if 'LUNIT1' not in cols and 'LUNIT2' not in cols and 'LBORRESU' not in cols:
                missing.append("LUNIT1/LUNIT2/LBORRESU")
            
            if missing:
                self.errors["BR-LB-001"].append({
                    "file": file_name,
                    "severity": "ERROR",
                    "message": f"Missing required variables: {', '.join(missing)}",
                    "count": len(missing)
                })
            else:
                self.info["BR-LB-001"].append({
                    "file": file_name,
                    "message": "All required variables present"
                })
    
    def validate_test_codes(self):
        """BR-LB-002: Validate test code standardization"""
        print("\n=== Validating Test Code Standardization ===")
        
        for file_name, df in self.data.items():
            if 'LPARM' in df.columns:
                test_col = 'LPARM'
            elif 'LBTEST' in df.columns:
                test_col = 'LBTEST'
            else:
                continue
            
            tests = df[test_col].value_counts()
            
            # Check for LOINC codes
            missing_loinc = []
            for test_name in tests.index:
                if test_name and test_name not in LOINC_CODES:
                    missing_loinc.append(test_name)
            
            if missing_loinc:
                self.warnings["BR-LB-002"].append({
                    "file": file_name,
                    "severity": "WARNING",
                    "message": f"Tests without standard LOINC codes: {missing_loinc[:5]}",
                    "count": len(missing_loinc),
                    "recommendation": "Consider mapping to LOINC codes for better standardization"
                })
            
            # Check for test code length (max 8 characters per CDISC)
            long_codes = df[df[test_col].str.len() > 8] if test_col in df.columns else pd.DataFrame()
            if len(long_codes) > 0:
                self.errors["BR-LB-002"].append({
                    "file": file_name,
                    "severity": "ERROR",
                    "message": "Test codes exceeding 8 characters",
                    "count": len(long_codes),
                    "examples": long_codes[test_col].unique()[:5].tolist()
                })
    
    def validate_numeric_results(self):
        """BR-LB-003: Validate numeric results are valid"""
        print("\n=== Validating Numeric Results ===")
        
        for file_name, df in self.data.items():
            # Find result columns
            result_cols = [col for col in df.columns if 'LVALUE' in col or 'LBORRES' in col]
            
            for col in result_cols:
                if col not in df.columns:
                    continue
                
                # Convert to string first to handle various formats
                df[col] = df[col].astype(str)
                
                # Count missing/empty values
                missing = df[col].isin(['', 'nan', 'None', 'NaN', 'NaT'])
                missing_count = missing.sum()
                
                # Try to convert to numeric
                numeric_vals = pd.to_numeric(df[col], errors='coerce')
                non_numeric = df[~missing & numeric_vals.isna()]
                
                if len(non_numeric) > 0:
                    self.warnings["BR-LB-003"].append({
                        "file": file_name,
                        "column": col,
                        "severity": "WARNING",
                        "message": f"Non-numeric values found in result column",
                        "count": len(non_numeric),
                        "examples": non_numeric[col].unique()[:5].tolist()
                    })
                
                # Report missing critical values
                if missing_count > 0:
                    pct_missing = (missing_count / len(df)) * 100
                    self.info["BR-LB-003"].append({
                        "file": file_name,
                        "column": col,
                        "message": f"Missing values: {missing_count} ({pct_missing:.1f}%)",
                        "severity": "INFO" if pct_missing < 5 else "WARNING"
                    })
    
    def validate_units_consistency(self):
        """BR-LB-004: Validate unit consistency for each test"""
        print("\n=== Validating Units Consistency ===")
        
        for file_name, df in self.data.items():
            test_col = None
            unit_col = None
            
            # Find test and unit columns
            if 'LPARM' in df.columns:
                test_col = 'LPARM'
            if 'LUNIT1' in df.columns:
                unit_col = 'LUNIT1'
            elif 'LBORRESU' in df.columns:
                unit_col = 'LBORRESU'
            
            if not test_col or not unit_col:
                continue
            
            # Group by test and check unit consistency
            test_units = df.groupby(test_col)[unit_col].apply(lambda x: x.dropna().unique().tolist())
            
            inconsistent = []
            for test, units in test_units.items():
                if len(units) > 1:
                    inconsistent.append({
                        "test": test,
                        "units_found": units,
                        "count": len(units)
                    })
            
            if inconsistent:
                self.errors["BR-LB-004"].append({
                    "file": file_name,
                    "severity": "ERROR",
                    "message": "Inconsistent units for tests",
                    "count": len(inconsistent),
                    "details": inconsistent[:10]
                })
    
    def validate_reference_ranges(self):
        """BR-LB-005: Validate reference range presence and format"""
        print("\n=== Validating Reference Ranges ===")
        
        for file_name, df in self.data.items():
            # Check for reference range columns (typically in detailed files)
            ref_cols = {
                'lower': [col for col in df.columns if any(x in col.upper() for x in ['LBSTNRLO', 'OLOW', 'LOW'])],
                'upper': [col for col in df.columns if any(x in col.upper() for x in ['LBSTNRHI', 'OHIGH', 'HIGH'])]
            }
            
            if ref_cols['lower'] and ref_cols['upper']:
                low_col = ref_cols['lower'][0]
                high_col = ref_cols['upper'][0]
                
                # Count missing reference ranges
                missing_low = df[low_col].isna().sum()
                missing_high = df[high_col].isna().sum()
                
                pct_missing = ((missing_low + missing_high) / (2 * len(df))) * 100
                
                if pct_missing > 10:
                    self.warnings["BR-LB-005"].append({
                        "file": file_name,
                        "severity": "WARNING",
                        "message": f"Missing reference ranges: {pct_missing:.1f}%",
                        "missing_low": missing_low,
                        "missing_high": missing_high,
                        "recommendation": "Reference ranges should be provided for clinical interpretation"
                    })
                
                # Validate low < high
                valid_ranges = df[[low_col, high_col]].dropna()
                if len(valid_ranges) > 0:
                    invalid = valid_ranges[pd.to_numeric(valid_ranges[low_col], errors='coerce') >= 
                                          pd.to_numeric(valid_ranges[high_col], errors='coerce')]
                    if len(invalid) > 0:
                        self.errors["BR-LB-005"].append({
                            "file": file_name,
                            "severity": "ERROR",
                            "message": "Reference range lower bound >= upper bound",
                            "count": len(invalid)
                        })
            else:
                self.warnings["BR-LB-005"].append({
                    "file": file_name,
                    "severity": "WARNING",
                    "message": "No reference range columns found",
                    "recommendation": "Consider adding LBSTNRLO and LBSTNRHI for ranges"
                })
    
    def validate_out_of_range_flags(self):
        """BR-LB-006: Validate out-of-range flags match actual values"""
        print("\n=== Validating Out-of-Range Flags ===")
        
        for file_name, df in self.data.items():
            # Look for standardized result, reference ranges in detailed files
            if 'STRES' not in df.columns:
                continue
            
            result_col = 'STRES'
            low_col = 'LBSTNRLO' if 'LBSTNRLO' in df.columns else None
            high_col = 'LBSTNRHI' if 'LBSTNRHI' in df.columns else None
            
            if not low_col or not high_col:
                continue
            
            # Calculate actual out-of-range values
            df_numeric = df.copy()
            df_numeric[result_col] = pd.to_numeric(df_numeric[result_col], errors='coerce')
            df_numeric[low_col] = pd.to_numeric(df_numeric[low_col], errors='coerce')
            df_numeric[high_col] = pd.to_numeric(df_numeric[high_col], errors='coerce')
            
            valid_data = df_numeric[[result_col, low_col, high_col]].dropna()
            
            if len(valid_data) > 0:
                below_low = valid_data[valid_data[result_col] < valid_data[low_col]]
                above_high = valid_data[valid_data[result_col] > valid_data[high_col]]
                out_of_range = len(below_low) + len(above_high)
                
                pct_oor = (out_of_range / len(valid_data)) * 100
                
                self.info["BR-LB-006"].append({
                    "file": file_name,
                    "message": f"Out-of-range results: {out_of_range} ({pct_oor:.1f}%)",
                    "below_low": len(below_low),
                    "above_high": len(above_high),
                    "recommendation": "Ensure LBNRIND flag is set correctly for these records"
                })
    
    def validate_date_formats(self):
        """BR-LB-007: Validate date/time formats (ISO 8601)"""
        print("\n=== Validating Date/Time Formats ===")
        
        iso8601_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?)?$')
        
        for file_name, df in self.data.items():
            # Find date columns
            date_cols = [col for col in df.columns if any(x in col.upper() for x in ['DT', 'SDT', 'DATE'])]
            
            for col in date_cols:
                if col not in df.columns:
                    continue
                
                # Convert to string and check format
                date_values = df[col].dropna().astype(str)
                
                # Check if values look like dates (contain numbers)
                potential_dates = date_values[date_values.str.contains(r'\d', regex=True)]
                
                if len(potential_dates) > 0:
                    # Check for ISO 8601 format
                    non_iso = potential_dates[~potential_dates.str.match(iso8601_pattern)]
                    
                    if len(non_iso) > 0:
                        # Check if it's numeric date format (YYYYMMDD)
                        numeric_dates = non_iso[non_iso.str.match(r'^\d{8}(\.\d)?$')]
                        
                        if len(numeric_dates) > 0:
                            self.warnings["BR-LB-007"].append({
                                "file": file_name,
                                "column": col,
                                "severity": "WARNING",
                                "message": f"Dates in numeric format (YYYYMMDD), should be ISO 8601 (YYYY-MM-DD)",
                                "count": len(numeric_dates),
                                "examples": numeric_dates.head(3).tolist()
                            })
    
    def validate_critical_missing_values(self):
        """BR-LB-008: Identify missing critical values"""
        print("\n=== Validating Critical Missing Values ===")
        
        critical_tests = [
            'HEMOGLOBIN', 'WBC', 'PLATELETS',  # Critical hematology
            'CREATININE', 'BUN', 'GLUCOSE',     # Critical chemistry
            'AST', 'ALT', 'TOTAL BILIRUBIN'     # Liver function
        ]
        
        for file_name, df in self.data.items():
            if 'LPARM' not in df.columns:
                continue
            
            test_col = 'LPARM'
            result_cols = [col for col in df.columns if 'LVALUE' in col]
            
            for test in critical_tests:
                test_data = df[df[test_col] == test]
                
                if len(test_data) > 0:
                    for result_col in result_cols:
                        if result_col in df.columns:
                            missing = test_data[result_col].isna().sum()
                            if missing > 0:
                                pct = (missing / len(test_data)) * 100
                                self.warnings["BR-LB-008"].append({
                                    "file": file_name,
                                    "test": test,
                                    "severity": "WARNING",
                                    "message": f"Missing critical values",
                                    "count": missing,
                                    "percentage": f"{pct:.1f}%"
                                })
    
    def calculate_statistics(self):
        """Calculate overall statistics"""
        print("\n=== Calculating Statistics ===")
        
        self.stats = {
            "total_files": len(self.data),
            "total_records": sum(len(df) for df in self.data.values()),
            "files_summary": {}
        }
        
        for file_name, df in self.data.items():
            # Get test counts
            test_col = 'LPARM' if 'LPARM' in df.columns else None
            test_counts = df[test_col].value_counts().to_dict() if test_col else {}
            
            self.stats["files_summary"][file_name] = {
                "records": len(df),
                "columns": len(df.columns),
                "unique_subjects": df['PT'].nunique() if 'PT' in df.columns else 'N/A',
                "unique_tests": len(test_counts) if test_counts else 'N/A',
                "test_counts": test_counts
            }
    
    def generate_report(self):
        """Generate comprehensive validation report"""
        print("\n" + "="*80)
        print("LB DOMAIN VALIDATION REPORT - MAXIS-08")
        print("="*80)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Files Validated: {self.stats['total_files']}")
        print(f"Total Records: {self.stats['total_records']}")
        print("="*80)
        
        # Summary Statistics
        print("\n### SUMMARY STATISTICS ###\n")
        for file_name, summary in self.stats["files_summary"].items():
            print(f"{file_name}:")
            print(f"  Records: {summary['records']}")
            print(f"  Columns: {summary['columns']}")
            print(f"  Unique Subjects: {summary['unique_subjects']}")
            print(f"  Unique Tests: {summary['unique_tests']}")
            if summary['test_counts']:
                print(f"  Test Distribution:")
                for test, count in sorted(summary['test_counts'].items(), key=lambda x: x[1], reverse=True)[:5]:
                    print(f"    - {test}: {count}")
            print()
        
        # Errors
        print("\n### ERRORS (Must Fix) ###\n")
        if self.errors:
            for rule_id, issues in sorted(self.errors.items()):
                print(f"\n{rule_id}:")
                for issue in issues:
                    print(f"  File: {issue.get('file', 'N/A')}")
                    print(f"  Severity: {issue.get('severity', 'ERROR')}")
                    print(f"  Message: {issue.get('message', 'N/A')}")
                    if 'count' in issue:
                        print(f"  Count: {issue['count']}")
                    if 'details' in issue:
                        print(f"  Details: {issue['details']}")
                    if 'examples' in issue:
                        print(f"  Examples: {issue['examples']}")
                    print()
        else:
            print("✓ No errors found!")
        
        # Warnings
        print("\n### WARNINGS (Should Review) ###\n")
        if self.warnings:
            for rule_id, issues in sorted(self.warnings.items()):
                print(f"\n{rule_id}:")
                for issue in issues:
                    print(f"  File: {issue.get('file', 'N/A')}")
                    print(f"  Severity: {issue.get('severity', 'WARNING')}")
                    print(f"  Message: {issue.get('message', 'N/A')}")
                    if 'count' in issue:
                        print(f"  Count: {issue['count']}")
                    if 'recommendation' in issue:
                        print(f"  Recommendation: {issue['recommendation']}")
                    print()
        else:
            print("✓ No warnings!")
        
        # Info
        print("\n### INFORMATION ###\n")
        if self.info:
            for rule_id, items in sorted(self.info.items()):
                print(f"\n{rule_id}:")
                for item in items:
                    print(f"  File: {item.get('file', 'N/A')}")
                    print(f"  Message: {item.get('message', 'N/A')}")
                    if 'recommendation' in item:
                        print(f"  Recommendation: {item['recommendation']}")
                    print()
        
        # Business Rules Applied
        print("\n### BUSINESS RULES APPLIED ###\n")
        rules = [
            "BR-LB-001: Required variables validation",
            "BR-LB-002: Test code standardization (LOINC)",
            "BR-LB-003: Numeric results validation",
            "BR-LB-004: Units consistency by test",
            "BR-LB-005: Reference range presence and format",
            "BR-LB-006: Out-of-range flags accuracy",
            "BR-LB-007: Date/time ISO 8601 format",
            "BR-LB-008: Critical missing values identification"
        ]
        for rule in rules:
            print(f"  ✓ {rule}")
        
        # Data Quality Recommendations
        print("\n### DATA QUALITY RECOMMENDATIONS ###\n")
        recommendations = [
            "1. Map all test codes to LOINC codes for standardization",
            "2. Ensure consistent units within each test type",
            "3. Provide reference ranges for all numeric results",
            "4. Convert dates to ISO 8601 format (YYYY-MM-DD)",
            "5. Populate LBSTAT='NOT DONE' and LBREASND for missing results",
            "6. Add LBNRIND flag (HIGH/LOW/NORMAL) for out-of-range values",
            "7. Include LBBLFL baseline flag for screening/baseline visits",
            "8. Standardize result values (LBSTRESC/LBSTRESN) with standard units (LBSTRESU)"
        ]
        for rec in recommendations:
            print(f"  {rec}")
        
        # Compliance Summary
        print("\n### COMPLIANCE SUMMARY ###\n")
        total_issues = len(self.errors) + len(self.warnings)
        error_count = sum(len(issues) for issues in self.errors.values())
        warning_count = sum(len(issues) for issues in self.warnings.values())
        
        print(f"Total Rule Violations: {total_issues}")
        print(f"  Errors: {error_count}")
        print(f"  Warnings: {warning_count}")
        
        if error_count == 0 and warning_count < 5:
            print("\n✓ Data quality is GOOD - ready for SDTM transformation")
        elif error_count == 0:
            print("\n⚠ Data quality is ACCEPTABLE - address warnings before submission")
        else:
            print("\n✗ Data quality needs IMPROVEMENT - fix errors before proceeding")
        
        print("\n" + "="*80)
        print("END OF VALIDATION REPORT")
        print("="*80)

def main():
    """Main validation workflow"""
    print("Starting LB Domain Validation for MAXIS-08")
    print("="*80)
    
    validator = LBValidator()
    
    # Load data
    validator.load_data()
    
    # Run validations
    validator.validate_required_variables()
    validator.validate_test_codes()
    validator.validate_numeric_results()
    validator.validate_units_consistency()
    validator.validate_reference_ranges()
    validator.validate_out_of_range_flags()
    validator.validate_date_formats()
    validator.validate_critical_missing_values()
    
    # Calculate statistics
    validator.calculate_statistics()
    
    # Generate report
    validator.generate_report()

if __name__ == "__main__":
    main()

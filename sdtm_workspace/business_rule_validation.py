"""
Business Rule Validation for SDTM Domains
Study: MAXIS-08
Domains: VS (Vital Signs), CM (Concomitant Medications), EX (Exposure)
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
import re
import json


class ValidationIssue:
    """Represents a validation issue"""
    def __init__(self, rule_id: str, severity: str, message: str, 
                 domain: str, variable: str = None, record_id: str = None, 
                 value: str = None, count: int = 1):
        self.rule_id = rule_id
        self.severity = severity
        self.message = message
        self.domain = domain
        self.variable = variable
        self.record_id = record_id
        self.value = value
        self.count = count
    
    def to_dict(self):
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "domain": self.domain,
            "variable": self.variable,
            "record_id": self.record_id,
            "value": self.value,
            "count": self.count
        }


class BusinessRuleValidator:
    """Validates SDTM domains against comprehensive business rules"""
    
    def __init__(self, study_id: str = "MAXIS-08"):
        self.study_id = study_id
        self.issues = []
        
        # VS Standard test codes and valid ranges
        self.vs_test_codes = {
            "SYSBP": {"test": "Systolic Blood Pressure", "unit": "mmHg", "min": 70, "max": 250},
            "DIABP": {"test": "Diastolic Blood Pressure", "unit": "mmHg", "min": 40, "max": 150},
            "PULSE": {"test": "Pulse Rate", "unit": "BEATS/MIN", "min": 30, "max": 200},
            "RESP": {"test": "Respiratory Rate", "unit": "BREATHS/MIN", "min": 8, "max": 60},
            "TEMP": {"test": "Temperature", "unit": "C", "min": 32, "max": 42},
            "HEIGHT": {"test": "Height", "unit": "cm", "min": 100, "max": 250},
            "WEIGHT": {"test": "Weight", "unit": "kg", "min": 30, "max": 300},
            "BMI": {"test": "Body Mass Index", "unit": "kg/m2", "min": 10, "max": 70},
        }
        
        # CM Route controlled terms
        self.cm_routes = ["ORAL", "INTRAVENOUS", "INTRAMUSCULAR", "SUBCUTANEOUS", 
                         "TOPICAL", "INHALATION", "NASAL", "OPHTHALMIC", "RECTAL"]
        
        # EX Dosing frequency controlled terms
        self.ex_dosfreq = ["QD", "BID", "TID", "QID", "Q12H", "Q8H", "Q6H", "Q4H", 
                          "ONCE", "PRN", "QOD", "WEEKLY"]
    
    def add_issue(self, rule_id: str, severity: str, message: str, domain: str, 
                  variable: str = None, record_id: str = None, value: str = None, count: int = 1):
        """Add a validation issue"""
        issue = ValidationIssue(rule_id, severity, message, domain, variable, record_id, value, count)
        self.issues.append(issue)
    
    def is_valid_iso8601(self, date_str) -> bool:
        """Check if date is in valid ISO 8601 format"""
        if pd.isna(date_str) or date_str == "":
            return True  # Missing dates are handled separately
        
        # ISO 8601 patterns: YYYY, YYYY-MM, YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS
        patterns = [
            r'^\d{4}$',
            r'^\d{4}-\d{2}$',
            r'^\d{4}-\d{2}-\d{2}$',
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$',
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$'
        ]
        
        return any(re.match(pattern, str(date_str)) for pattern in patterns)
    
    def validate_date_range(self, df: pd.DataFrame, domain: str, 
                           start_col: str, end_col: str) -> None:
        """BR-DATE-001: Start date should be before or equal to end date"""
        if start_col not in df.columns or end_col not in df.columns:
            return
        
        mask = (df[start_col].notna()) & (df[end_col].notna())
        invalid = df[mask][df[mask][start_col] > df[mask][end_col]]
        
        if len(invalid) > 0:
            for idx, row in invalid.iterrows():
                self.add_issue(
                    "BR-DATE-001",
                    "error",
                    f"End date ({row[end_col]}) is before start date ({row[start_col]})",
                    domain,
                    f"{start_col}, {end_col}",
                    str(row.get('USUBJID', idx))
                )
    
    def validate_required_fields(self, df: pd.DataFrame, domain: str, 
                                 required_fields: List[str]) -> None:
        """BR-REQ-001: Required fields must be populated"""
        for field in required_fields:
            if field not in df.columns:
                self.add_issue(
                    "BR-REQ-001",
                    "error",
                    f"Required field '{field}' is missing from dataset",
                    domain,
                    field
                )
            else:
                missing = df[field].isna().sum()
                if missing > 0:
                    self.add_issue(
                        "BR-REQ-002",
                        "error",
                        f"Required field '{field}' has {missing} missing values",
                        domain,
                        field,
                        count=missing
                    )
    
    def validate_vs_domain(self, df: pd.DataFrame) -> Dict:
        """Validate VS (Vital Signs) domain against business rules"""
        domain = "VS"
        print(f"\n{'='*80}")
        print(f"Validating {domain} Domain - {len(df)} records")
        print(f"{'='*80}")
        
        # BR-VS-001: Required variables
        required = ["STUDYID", "DOMAIN", "USUBJID", "VSSEQ", "VSTESTCD", 
                   "VSTEST", "VSORRES", "VSORRESU"]
        self.validate_required_fields(df, domain, required)
        
        # BR-VS-002: VSTESTCD should be from standard list
        if "VSTESTCD" in df.columns:
            invalid_codes = df[~df["VSTESTCD"].isin(self.vs_test_codes.keys())]
            if len(invalid_codes) > 0:
                unique_invalid = invalid_codes["VSTESTCD"].unique()
                self.add_issue(
                    "BR-VS-002",
                    "warning",
                    f"Non-standard vital sign test codes found: {', '.join(unique_invalid)}",
                    domain,
                    "VSTESTCD",
                    count=len(invalid_codes)
                )
        
        # BR-VS-003: Standard vital signs presence check
        if "VSTESTCD" in df.columns:
            required_tests = ["SYSBP", "DIABP", "PULSE", "TEMP", "WEIGHT"]
            present_tests = df["VSTESTCD"].unique()
            missing_tests = set(required_tests) - set(present_tests)
            
            if missing_tests:
                self.add_issue(
                    "BR-VS-003",
                    "warning",
                    f"Standard vital signs missing: {', '.join(missing_tests)}",
                    domain,
                    "VSTESTCD"
                )
        
        # BR-VS-004: Units consistency check
        if "VSTESTCD" in df.columns and "VSORRESU" in df.columns:
            for testcd, test_info in self.vs_test_codes.items():
                test_data = df[df["VSTESTCD"] == testcd]
                if len(test_data) > 0:
                    expected_unit = test_info["unit"]
                    actual_units = test_data["VSORRESU"].unique()
                    
                    # Check for inconsistent units
                    if len(actual_units) > 1:
                        self.add_issue(
                            "BR-VS-004",
                            "warning",
                            f"Inconsistent units for {testcd}: {', '.join(str(u) for u in actual_units)}. Expected: {expected_unit}",
                            domain,
                            "VSORRESU",
                            testcd
                        )
        
        # BR-VS-005: Physiologically plausible ranges
        if "VSTESTCD" in df.columns and "VSORRES" in df.columns:
            for testcd, test_info in self.vs_test_codes.items():
                test_data = df[df["VSTESTCD"] == testcd].copy()
                if len(test_data) > 0:
                    # Convert to numeric
                    test_data["VSORRES_NUM"] = pd.to_numeric(test_data["VSORRES"], errors='coerce')
                    
                    # Check ranges
                    out_of_range = test_data[
                        (test_data["VSORRES_NUM"] < test_info["min"]) | 
                        (test_data["VSORRES_NUM"] > test_info["max"])
                    ]
                    
                    if len(out_of_range) > 0:
                        self.add_issue(
                            "BR-VS-005",
                            "warning",
                            f"{testcd} values outside physiological range ({test_info['min']}-{test_info['max']}): {len(out_of_range)} records",
                            domain,
                            "VSORRES",
                            testcd,
                            count=len(out_of_range)
                        )
        
        # BR-VS-006: Date/time format validation
        if "VSDTC" in df.columns:
            invalid_dates = []
            for idx, val in df["VSDTC"].items():
                if pd.notna(val) and not self.is_valid_iso8601(val):
                    invalid_dates.append((idx, val))
            
            if invalid_dates:
                self.add_issue(
                    "BR-VS-006",
                    "error",
                    f"Invalid ISO 8601 date format in VSDTC: {len(invalid_dates)} records",
                    domain,
                    "VSDTC",
                    count=len(invalid_dates)
                )
        
        # BR-VS-007: VSSEQ uniqueness within subject
        if "USUBJID" in df.columns and "VSSEQ" in df.columns:
            duplicates = df.groupby(["USUBJID", "VSSEQ"]).size()
            duplicates = duplicates[duplicates > 1]
            
            if len(duplicates) > 0:
                self.add_issue(
                    "BR-VS-007",
                    "error",
                    f"Duplicate VSSEQ values within subject: {len(duplicates)} occurrences",
                    domain,
                    "VSSEQ",
                    count=len(duplicates)
                )
        
        # BR-VS-008: VSSTRESC should be populated when VSORRES exists
        if "VSORRES" in df.columns and "VSSTRESC" in df.columns:
            missing_stresc = df[(df["VSORRES"].notna()) & (df["VSSTRESC"].isna())]
            if len(missing_stresc) > 0:
                self.add_issue(
                    "BR-VS-008",
                    "warning",
                    f"VSSTRESC missing when VSORRES is populated: {len(missing_stresc)} records",
                    domain,
                    "VSSTRESC",
                    count=len(missing_stresc)
                )
        
        # Summary
        vs_issues = [i for i in self.issues if i.domain == domain]
        errors = [i for i in vs_issues if i.severity == "error"]
        warnings = [i for i in vs_issues if i.severity == "warning"]
        
        return {
            "domain": domain,
            "records": len(df),
            "errors": len(errors),
            "warnings": len(warnings),
            "is_valid": len(errors) == 0
        }
    
    def validate_cm_domain(self, df: pd.DataFrame) -> Dict:
        """Validate CM (Concomitant Medications) domain against business rules"""
        domain = "CM"
        print(f"\n{'='*80}")
        print(f"Validating {domain} Domain - {len(df)} records")
        print(f"{'='*80}")
        
        # BR-CM-001: Required variables
        required = ["STUDYID", "DOMAIN", "USUBJID", "CMSEQ", "CMTRT"]
        self.validate_required_fields(df, domain, required)
        
        # BR-CM-002: Date logic validation
        self.validate_date_range(df, domain, "CMSTDTC", "CMENDTC")
        
        # BR-CM-003: CMDECOD should be populated (WHO Drug coding)
        if "CMDECOD" in df.columns:
            missing_decod = df["CMDECOD"].isna().sum()
            if missing_decod > 0:
                self.add_issue(
                    "BR-CM-003",
                    "warning",
                    f"CMDECOD (standardized medication name) missing: {missing_decod} records. Recommended to use WHO Drug Dictionary.",
                    domain,
                    "CMDECOD",
                    count=missing_decod
                )
        
        # BR-CM-004: CMONGO flag consistency
        if "CMONGO" in df.columns and "CMENDTC" in df.columns:
            # If end date is missing, CMONGO should be Y
            inconsistent = df[(df["CMENDTC"].isna()) & (df["CMONGO"] != "Y")]
            if len(inconsistent) > 0:
                self.add_issue(
                    "BR-CM-004",
                    "warning",
                    f"CMONGO should be 'Y' when CMENDTC is missing: {len(inconsistent)} records",
                    domain,
                    "CMONGO",
                    count=len(inconsistent)
                )
            
            # If end date exists, CMONGO should not be Y
            inconsistent2 = df[(df["CMENDTC"].notna()) & (df["CMONGO"] == "Y")]
            if len(inconsistent2) > 0:
                self.add_issue(
                    "BR-CM-005",
                    "warning",
                    f"CMONGO is 'Y' but CMENDTC is populated: {len(inconsistent2)} records",
                    domain,
                    "CMONGO",
                    count=len(inconsistent2)
                )
        
        # BR-CM-006: Date format validation
        date_cols = ["CMSTDTC", "CMENDTC"]
        for col in date_cols:
            if col in df.columns:
                invalid_dates = []
                for idx, val in df[col].items():
                    if pd.notna(val) and not self.is_valid_iso8601(val):
                        invalid_dates.append((idx, val))
                
                if invalid_dates:
                    self.add_issue(
                        "BR-CM-006",
                        "error",
                        f"Invalid ISO 8601 date format in {col}: {len(invalid_dates)} records",
                        domain,
                        col,
                        count=len(invalid_dates)
                    )
        
        # BR-CM-007: Route should be from controlled terminology
        if "CMROUTE" in df.columns:
            invalid_routes = df[
                (df["CMROUTE"].notna()) & 
                (~df["CMROUTE"].str.upper().isin([r.upper() for r in self.cm_routes]))
            ]
            if len(invalid_routes) > 0:
                unique_invalid = invalid_routes["CMROUTE"].unique()
                self.add_issue(
                    "BR-CM-007",
                    "warning",
                    f"Non-standard route values: {', '.join(str(r) for r in unique_invalid[:5])}",
                    domain,
                    "CMROUTE",
                    count=len(invalid_routes)
                )
        
        # BR-CM-008: CMDOSE should have CMDOSU when populated
        if "CMDOSE" in df.columns and "CMDOSU" in df.columns:
            missing_unit = df[(df["CMDOSE"].notna()) & (df["CMDOSU"].isna())]
            if len(missing_unit) > 0:
                self.add_issue(
                    "BR-CM-008",
                    "warning",
                    f"CMDOSU missing when CMDOSE is populated: {len(missing_unit)} records",
                    domain,
                    "CMDOSU",
                    count=len(missing_unit)
                )
        
        # BR-CM-009: CMSEQ uniqueness within subject
        if "USUBJID" in df.columns and "CMSEQ" in df.columns:
            duplicates = df.groupby(["USUBJID", "CMSEQ"]).size()
            duplicates = duplicates[duplicates > 1]
            
            if len(duplicates) > 0:
                self.add_issue(
                    "BR-CM-009",
                    "error",
                    f"Duplicate CMSEQ values within subject: {len(duplicates)} occurrences",
                    domain,
                    "CMSEQ",
                    count=len(duplicates)
                )
        
        # BR-CM-010: CMTRT should not be empty
        if "CMTRT" in df.columns:
            empty_trt = df["CMTRT"].isna().sum()
            if empty_trt > 0:
                self.add_issue(
                    "BR-CM-010",
                    "error",
                    f"CMTRT (medication name) is missing: {empty_trt} records",
                    domain,
                    "CMTRT",
                    count=empty_trt
                )
        
        # Summary
        cm_issues = [i for i in self.issues if i.domain == domain]
        errors = [i for i in cm_issues if i.severity == "error"]
        warnings = [i for i in cm_issues if i.severity == "warning"]
        
        return {
            "domain": domain,
            "records": len(df),
            "errors": len(errors),
            "warnings": len(warnings),
            "is_valid": len(errors) == 0
        }
    
    def validate_ex_domain(self, df: pd.DataFrame) -> Dict:
        """Validate EX (Exposure) domain against business rules"""
        domain = "EX"
        print(f"\n{'='*80}")
        print(f"Validating {domain} Domain - {len(df)} records")
        print(f"{'='*80}")
        
        # BR-EX-001: Required variables
        required = ["STUDYID", "DOMAIN", "USUBJID", "EXSEQ", "EXTRT", 
                   "EXDOSE", "EXDOSU", "EXSTDTC"]
        self.validate_required_fields(df, domain, required)
        
        # BR-EX-002: Date logic validation
        self.validate_date_range(df, domain, "EXSTDTC", "EXENDTC")
        
        # BR-EX-003: EXDOSE must be numeric and positive
        if "EXDOSE" in df.columns:
            # Check for non-numeric values
            non_numeric = df[df["EXDOSE"].notna()].copy()
            non_numeric["EXDOSE_NUM"] = pd.to_numeric(non_numeric["EXDOSE"], errors='coerce')
            invalid = non_numeric[non_numeric["EXDOSE_NUM"].isna()]
            
            if len(invalid) > 0:
                self.add_issue(
                    "BR-EX-003",
                    "error",
                    f"Non-numeric EXDOSE values: {len(invalid)} records",
                    domain,
                    "EXDOSE",
                    count=len(invalid)
                )
            
            # Check for negative or zero doses
            negative = non_numeric[non_numeric["EXDOSE_NUM"] <= 0]
            if len(negative) > 0:
                self.add_issue(
                    "BR-EX-004",
                    "warning",
                    f"EXDOSE <= 0: {len(negative)} records",
                    domain,
                    "EXDOSE",
                    count=len(negative)
                )
        
        # BR-EX-005: EXDOSU must be populated when EXDOSE exists
        if "EXDOSE" in df.columns and "EXDOSU" in df.columns:
            missing_unit = df[(df["EXDOSE"].notna()) & (df["EXDOSU"].isna())]
            if len(missing_unit) > 0:
                self.add_issue(
                    "BR-EX-005",
                    "error",
                    f"EXDOSU missing when EXDOSE is populated: {len(missing_unit)} records",
                    domain,
                    "EXDOSU",
                    count=len(missing_unit)
                )
        
        # BR-EX-006: Date format validation
        date_cols = ["EXSTDTC", "EXENDTC"]
        for col in date_cols:
            if col in df.columns:
                invalid_dates = []
                for idx, val in df[col].items():
                    if pd.notna(val) and not self.is_valid_iso8601(val):
                        invalid_dates.append((idx, val))
                
                if invalid_dates:
                    self.add_issue(
                        "BR-EX-006",
                        "error",
                        f"Invalid ISO 8601 date format in {col}: {len(invalid_dates)} records",
                        domain,
                        col,
                        count=len(invalid_dates)
                    )
        
        # BR-EX-007: EXDOSFRQ should be from controlled terminology
        if "EXDOSFRQ" in df.columns:
            invalid_freq = df[
                (df["EXDOSFRQ"].notna()) & 
                (~df["EXDOSFRQ"].str.upper().isin([f.upper() for f in self.ex_dosfreq]))
            ]
            if len(invalid_freq) > 0:
                unique_invalid = invalid_freq["EXDOSFRQ"].unique()
                self.add_issue(
                    "BR-EX-007",
                    "warning",
                    f"Non-standard dosing frequency values: {', '.join(str(f) for f in unique_invalid[:5])}",
                    domain,
                    "EXDOSFRQ",
                    count=len(invalid_freq)
                )
        
        # BR-EX-008: EXSEQ uniqueness within subject
        if "USUBJID" in df.columns and "EXSEQ" in df.columns:
            duplicates = df.groupby(["USUBJID", "EXSEQ"]).size()
            duplicates = duplicates[duplicates > 1]
            
            if len(duplicates) > 0:
                self.add_issue(
                    "BR-EX-008",
                    "error",
                    f"Duplicate EXSEQ values within subject: {len(duplicates)} occurrences",
                    domain,
                    "EXSEQ",
                    count=len(duplicates)
                )
        
        # BR-EX-009: Study drug exposure continuity check
        if "USUBJID" in df.columns and "EXSTDTC" in df.columns and "EXENDTC" in df.columns:
            # Group by subject and check for gaps
            for usubjid in df["USUBJID"].unique():
                subject_data = df[df["USUBJID"] == usubjid].copy()
                subject_data = subject_data[
                    (subject_data["EXSTDTC"].notna()) & 
                    (subject_data["EXENDTC"].notna())
                ].sort_values("EXSTDTC")
                
                if len(subject_data) > 1:
                    # Check for gaps > 3 days
                    for i in range(len(subject_data) - 1):
                        current_end = pd.to_datetime(subject_data.iloc[i]["EXENDTC"], errors='coerce')
                        next_start = pd.to_datetime(subject_data.iloc[i+1]["EXSTDTC"], errors='coerce')
                        
                        if pd.notna(current_end) and pd.notna(next_start):
                            gap_days = (next_start - current_end).days
                            if gap_days > 3:
                                self.add_issue(
                                    "BR-EX-009",
                                    "warning",
                                    f"Exposure gap of {gap_days} days detected for subject {usubjid}",
                                    domain,
                                    "EXSTDTC, EXENDTC",
                                    usubjid
                                )
        
        # BR-EX-010: EXTRT consistency check within study
        if "EXTRT" in df.columns:
            unique_trts = df["EXTRT"].unique()
            if len(unique_trts) > 5:  # Typically, a study has limited number of treatments
                self.add_issue(
                    "BR-EX-010",
                    "info",
                    f"Multiple treatment names found ({len(unique_trts)}). Verify treatment naming consistency.",
                    domain,
                    "EXTRT"
                )
        
        # Summary
        ex_issues = [i for i in self.issues if i.domain == domain]
        errors = [i for i in ex_issues if i.severity == "error"]
        warnings = [i for i in ex_issues if i.severity == "warning"]
        
        return {
            "domain": domain,
            "records": len(df),
            "errors": len(errors),
            "warnings": len(warnings),
            "is_valid": len(errors) == 0
        }
    
    def generate_report(self, results: List[Dict]) -> Dict:
        """Generate comprehensive validation report"""
        
        # Calculate totals
        total_records = sum(r["records"] for r in results)
        total_errors = sum(r["errors"] for r in results)
        total_warnings = sum(r["warnings"] for r in results)
        
        # Group issues by domain
        issues_by_domain = {}
        for issue in self.issues:
            if issue.domain not in issues_by_domain:
                issues_by_domain[issue.domain] = {"errors": [], "warnings": [], "info": []}
            issues_by_domain[issue.domain][issue.severity + "s"].append(issue.to_dict())
        
        # Calculate compliance score
        total_checks = len(self.issues) if len(self.issues) > 0 else 1
        passed_checks = total_checks - total_errors
        compliance_score = (passed_checks / total_checks) * 100
        
        submission_ready = (compliance_score >= 95.0) and (total_errors == 0)
        
        report = {
            "study_id": self.study_id,
            "validation_date": datetime.now().isoformat(),
            "summary": {
                "total_records": total_records,
                "total_domains": len(results),
                "total_errors": total_errors,
                "total_warnings": total_warnings,
                "compliance_score": round(compliance_score, 1),
                "submission_ready": submission_ready
            },
            "domain_results": results,
            "issues_by_domain": issues_by_domain,
            "business_rules_applied": self.get_business_rules_list(),
            "recommendations": self.generate_recommendations(total_errors, total_warnings)
        }
        
        return report
    
    def get_business_rules_list(self) -> Dict:
        """Get list of business rules applied"""
        return {
            "VS": [
                "BR-VS-001: Required variables check",
                "BR-VS-002: Standard test code validation",
                "BR-VS-003: Standard vital signs presence",
                "BR-VS-004: Units consistency check",
                "BR-VS-005: Physiological range validation",
                "BR-VS-006: ISO 8601 date format validation",
                "BR-VS-007: VSSEQ uniqueness",
                "BR-VS-008: VSSTRESC population when VSORRES exists"
            ],
            "CM": [
                "BR-CM-001: Required variables check",
                "BR-CM-002: Date range logic (start <= end)",
                "BR-CM-003: CMDECOD (WHO Drug) population",
                "BR-CM-004: CMONGO flag consistency with end date",
                "BR-CM-005: CMONGO validation when end date present",
                "BR-CM-006: ISO 8601 date format validation",
                "BR-CM-007: Route controlled terminology",
                "BR-CM-008: Dose unit population",
                "BR-CM-009: CMSEQ uniqueness",
                "BR-CM-010: CMTRT population"
            ],
            "EX": [
                "BR-EX-001: Required variables check",
                "BR-EX-002: Date range logic (start <= end)",
                "BR-EX-003: Numeric dose validation",
                "BR-EX-004: Positive dose validation",
                "BR-EX-005: Dose unit population",
                "BR-EX-006: ISO 8601 date format validation",
                "BR-EX-007: Dosing frequency controlled terminology",
                "BR-EX-008: EXSEQ uniqueness",
                "BR-EX-009: Exposure continuity check",
                "BR-EX-010: Treatment name consistency"
            ]
        }
    
    def generate_recommendations(self, errors: int, warnings: int) -> List[str]:
        """Generate data quality recommendations"""
        recommendations = []
        
        if errors > 0:
            recommendations.append(
                f"CRITICAL: {errors} error(s) must be resolved before submission. "
                "Focus on required fields, date formats, and data type issues."
            )
        
        if warnings > 10:
            recommendations.append(
                f"Review {warnings} warning(s) to improve data quality. "
                "Address controlled terminology, unit consistency, and coding issues."
            )
        
        # Domain-specific recommendations
        vs_issues = [i for i in self.issues if i.domain == "VS"]
        if any(i.rule_id == "BR-VS-005" for i in vs_issues):
            recommendations.append(
                "VS: Review vital sign values outside physiological ranges. "
                "Verify source data or add comments for extreme values."
            )
        
        cm_issues = [i for i in self.issues if i.domain == "CM"]
        if any(i.rule_id == "BR-CM-003" for i in cm_issues):
            recommendations.append(
                "CM: Standardize medication names using WHO Drug Dictionary. "
                "Populate CMDECOD for regulatory compliance."
            )
        
        ex_issues = [i for i in self.issues if i.domain == "EX"]
        if any(i.rule_id == "BR-EX-009" for i in ex_issues):
            recommendations.append(
                "EX: Review exposure gaps. Ensure study drug administration "
                "is properly captured with continuous records."
            )
        
        if errors == 0 and warnings < 5:
            recommendations.append(
                "Data quality is excellent. Proceed with CDISC conformance validation "
                "and Define.xml generation."
            )
        
        return recommendations


def main():
    """Main validation function"""
    print("\n" + "="*80)
    print("SDTM BUSINESS RULE VALIDATION")
    print("Study: MAXIS-08")
    print("="*80)
    
    # Initialize validator
    validator = BusinessRuleValidator("MAXIS-08")
    
    # Note: This script is designed to work with actual CSV files
    # For demonstration, we'll show the structure and validation logic
    
    print("\nValidation Script Ready!")
    print("\nTo use this script with actual data:")
    print("1. Load CSV files: vs_df = pd.read_csv('VITALS.csv')")
    print("2. Call validators: validator.validate_vs_domain(vs_df)")
    print("3. Generate report: report = validator.generate_report(results)")
    print("\n" + "="*80)
    
    # Example of how to use with actual data (commented out)
    """
    # Load data
    vs_df = pd.read_csv('/path/to/VITALS.csv')
    cm_df = pd.read_csv('/path/to/CONMEDS.csv')
    ex_df = pd.read_csv('/path/to/DOSE.csv')
    
    # Validate domains
    vs_result = validator.validate_vs_domain(vs_df)
    cm_result = validator.validate_cm_domain(cm_df)
    ex_result = validator.validate_ex_domain(ex_df)
    
    # Generate report
    results = [vs_result, cm_result, ex_result]
    report = validator.generate_report(results)
    
    # Save report
    with open('validation_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✓ Validation complete!")
    print(f"  Total Records: {report['summary']['total_records']}")
    print(f"  Errors: {report['summary']['total_errors']}")
    print(f"  Warnings: {report['summary']['total_warnings']}")
    print(f"  Compliance Score: {report['summary']['compliance_score']}%")
    print(f"  Submission Ready: {report['summary']['submission_ready']}")
    """


if __name__ == "__main__":
    main()

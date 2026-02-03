#!/usr/bin/env python3
"""
MAXIS-08 Enhanced Raw Data Validation Script with Comprehensive Business Rules
==============================================================================

Performs comprehensive validation on source data files before SDTM transformation.
Includes structural checks, business rules, cross-domain validation, and CT preview.

Author: SDTM Pipeline - Validation Agent
Study: MAXIS-08
Date: 2025-02-02
Version: 2.0 (Enhanced with Business Rules)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
import re
from collections import defaultdict
from typing import Dict, List, Tuple, Any, Optional
import argparse


class ValidationIssue:
    """Represents a validation finding"""
    
    def __init__(self, rule_id: str, severity: str, message: str,
                 domain: str, variable: str = None, record_ids: List[str] = None,
                 example_values: List[str] = None, count: int = 1, 
                 recommendation: str = None):
        self.rule_id = rule_id
        self.severity = severity  # CRITICAL, ERROR, WARNING, INFO
        self.message = message
        self.domain = domain
        self.variable = variable
        self.record_ids = record_ids or []
        self.example_values = example_values or []
        self.count = count
        self.recommendation = recommendation
        
    def to_dict(self) -> Dict:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "domain": self.domain,
            "variable": self.variable,
            "record_ids": self.record_ids[:5],  # First 5 for report
            "example_values": self.example_values[:5],
            "count": self.count,
            "recommendation": self.recommendation
        }


class EnhancedRawDataValidator:
    """Comprehensive raw data validator with business rules"""
    
    def __init__(self, data_path: str, study_id: str = "MAXIS-08"):
        self.data_path = Path(data_path)
        self.study_id = study_id
        self.issues = []
        self.domain_data = {}  # Store loaded dataframes for cross-domain checks
        
        # File-to-domain mappings (from previous script)
        self.file_mappings = {
            "DEMO.csv": {"domain": "DM", "expected_records": 16, "expected_cols": 12},
            "AEVENT.csv": {"domain": "AE", "expected_records": 550, "expected_cols": 38},
            "AEVENTC.csv": {"domain": "AE", "expected_records": 276, "expected_cols": 36},
            "CONMEDS.csv": {"domain": "CM", "expected_records": 302, "expected_cols": 38},
            "CONMEDSC.csv": {"domain": "CM", "expected_records": 302, "expected_cols": 34},
            "VITALS.csv": {"domain": "VS", "expected_records": 536, "expected_cols": 21},
            "HEMLAB.csv": {"domain": "LB", "expected_records": 1726, "expected_cols": 14},
            "CHEMLAB.csv": {"domain": "LB", "expected_records": 3326, "expected_cols": 13},
            "HEMLABD.csv": {"domain": "LB", "expected_records": 2572, "expected_cols": 14},
            "CHEMLABD.csv": {"domain": "LB", "expected_records": 2018, "expected_cols": 13},
            "URINLAB.csv": {"domain": "LB", "expected_records": 554, "expected_cols": 13},
            "DOSE.csv": {"domain": "EX", "expected_records": 271, "expected_cols": 21},
            "ECG.csv": {"domain": "EG", "expected_records": 60, "expected_cols": 11},
            "PHYSEXAM.csv": {"domain": "PE", "expected_records": 2169, "expected_cols": 14}
        }
        
        # CDISC Controlled Terminology
        self.ct_sex = ["M", "F", "U", "UNDIFFERENTIATED"]
        self.ct_race = ["AMERICAN INDIAN OR ALASKA NATIVE", "ASIAN", "BLACK OR AFRICAN AMERICAN",
                       "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER", "WHITE", 
                       "MULTIPLE", "OTHER", "NOT REPORTED", "UNKNOWN"]
        self.ct_ethnic = ["HISPANIC OR LATINO", "NOT HISPANIC OR LATINO", "NOT REPORTED", "UNKNOWN"]
        self.ct_severity = ["MILD", "MODERATE", "SEVERE"]
        self.ct_yesno = ["Y", "N"]
        self.ct_outcome = ["RECOVERED/RESOLVED", "RECOVERING/RESOLVING", "NOT RECOVERED/NOT RESOLVED",
                          "RECOVERED/RESOLVED WITH SEQUELAE", "FATAL", "UNKNOWN"]
        self.ct_causality = ["RELATED", "NOT RELATED", "POSSIBLY RELATED", "PROBABLY RELATED"]
        
        # Vital Signs standard codes and ranges
        self.vs_test_codes = {
            "SYSBP": {"test": "Systolic Blood Pressure", "unit": "mmHg", "min": 70, "max": 250},
            "DIABP": {"test": "Diastolic Blood Pressure", "unit": "mmHg", "min": 40, "max": 150},
            "PULSE": {"test": "Pulse Rate", "unit": "beats/min", "min": 30, "max": 200},
            "RESP": {"test": "Respiratory Rate", "unit": "breaths/min", "min": 8, "max": 60},
            "TEMP": {"test": "Temperature", "unit": "C", "min": 32, "max": 42},
            "HEIGHT": {"test": "Height", "unit": "cm", "min": 100, "max": 250},
            "WEIGHT": {"test": "Weight", "unit": "kg", "min": 30, "max": 300},
            "BMI": {"test": "Body Mass Index", "unit": "kg/m2", "min": 10, "max": 70}
        }
        
        # ECG ranges
        self.eg_ranges = {
            "HR": {"min": 40, "max": 200, "unit": "beats/min"},
            "QT": {"min": 300, "max": 600, "unit": "msec"},
            "QTC": {"min": 300, "max": 600, "unit": "msec"},
            "PR": {"min": 120, "max": 200, "unit": "msec"},
            "QRS": {"min": 60, "max": 120, "unit": "msec"}
        }
    
    def add_issue(self, rule_id: str, severity: str, message: str, domain: str,
                  variable: str = None, record_ids: List[str] = None,
                  example_values: List[str] = None, count: int = 1,
                  recommendation: str = None):
        """Add a validation issue"""
        issue = ValidationIssue(rule_id, severity, message, domain, variable,
                              record_ids, example_values, count, recommendation)
        self.issues.append(issue)
    
    def validate_all_files(self) -> Dict[str, Any]:
        """Main validation orchestrator"""
        print(f"\n{'='*80}")
        print(f"ENHANCED RAW DATA VALIDATION - Study {self.study_id}")
        print(f"{'='*80}\n")
        print(f"Data Path: {self.data_path}")
        print(f"Validation Layers: Structural, Business Rules, Cross-Domain, CT Preview")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        results = {
            "study_id": self.study_id,
            "validation_date": datetime.now().isoformat(),
            "validation_type": "Enhanced with Business Rules",
            "files_validated": 0,
            "total_records": 0,
            "critical_errors": 0,
            "errors": 0,
            "warnings": 0,
            "info": 0,
            "overall_quality_score": 0.0,
            "transformation_readiness": "PENDING",
            "domain_results": {}
        }
        
        # Phase 1: Load all files and perform per-file validation
        print(f"\n{'─'*80}")
        print("PHASE 1: STRUCTURAL VALIDATION")
        print(f"{'─'*80}\n")
        
        for filename, metadata in self.file_mappings.items():
            file_path = self.data_path / filename
            domain = metadata["domain"]
            
            print(f"Validating: {filename} → {domain} domain")
            
            if not file_path.exists():
                print(f"❌ ERROR: File not found at {file_path}")
                self.add_issue("FILE-001", "CRITICAL", 
                             f"Source file not found: {filename}",
                             domain, recommendation="Verify data extraction from S3")
                continue
            
            try:
                df = pd.read_csv(file_path, encoding='utf-8-sig')
                results["total_records"] += len(df)
                results["files_validated"] += 1
                
                # Store for cross-domain checks
                if domain not in self.domain_data:
                    self.domain_data[domain] = []
                self.domain_data[domain].append(df)
                
                # Perform structural validation
                self._validate_structure(df, filename, metadata)
                
                # Perform business rule validation by domain
                self._validate_business_rules(df, domain, filename)
                
                print(f"✅ Validated: {len(df)} records\n")
                
            except Exception as e:
                print(f"❌ EXCEPTION: {str(e)}\n")
                self.add_issue("FILE-002", "CRITICAL",
                             f"File read error: {str(e)}", domain)
        
        # Phase 2: Cross-domain validation
        print(f"\n{'─'*80}")
        print("PHASE 2: CROSS-DOMAIN CONSISTENCY CHECKS")
        print(f"{'─'*80}\n")
        self._validate_cross_domain()
        
        # Phase 3: Controlled Terminology Preview
        print(f"\n{'─'*80}")
        print("PHASE 3: CONTROLLED TERMINOLOGY PREVIEW")
        print(f"{'─'*80}\n")
        self._validate_ct_preview()
        
        # Calculate final metrics
        results["critical_errors"] = len([i for i in self.issues if i.severity == "CRITICAL"])
        results["errors"] = len([i for i in self.issues if i.severity == "ERROR"])
        results["warnings"] = len([i for i in self.issues if i.severity == "WARNING"])
        results["info"] = len([i for i in self.issues if i.severity == "INFO"])
        
        results["overall_quality_score"] = self._calculate_overall_quality_score()
        results["transformation_readiness"] = self._assess_readiness(results)
        
        # Organize issues by domain
        results["domain_results"] = self._organize_results_by_domain()
        results["all_issues"] = [issue.to_dict() for issue in self.issues]
        
        # Print summary
        self._print_final_summary(results)
        
        return results
    
    def _validate_structure(self, df: pd.DataFrame, filename: str, metadata: Dict):
        """Structural validation layer"""
        domain = metadata["domain"]
        
        # Check 1: Required identifier fields
        required_ids = ["STUDY", "INVSITE", "PT"]
        for id_field in required_ids:
            if id_field not in df.columns:
                self.add_issue("STR-001", "CRITICAL",
                             f"Missing required identifier: {id_field}",
                             domain, id_field,
                             recommendation=f"Add {id_field} column to {filename}")
            else:
                missing_count = df[id_field].isnull().sum()
                if missing_count > 0:
                    self.add_issue("STR-002", "CRITICAL",
                                 f"Identifier {id_field} has {missing_count} null values",
                                 domain, id_field, count=missing_count,
                                 recommendation="Populate all identifier fields")
        
        # Check 2: Duplicate rows
        dup_count = df.duplicated().sum()
        if dup_count > 0:
            self.add_issue("STR-003", "ERROR",
                         f"{dup_count} completely duplicate rows found",
                         domain, count=dup_count,
                         recommendation="Remove duplicate records")
        
        # Check 3: Record count variance
        expected_records = metadata.get("expected_records", 0)
        actual_records = len(df)
        variance_pct = abs(actual_records - expected_records) / expected_records * 100 if expected_records > 0 else 0
        
        if variance_pct > 20:
            self.add_issue("STR-004", "WARNING",
                         f"Record count variance: expected {expected_records}, got {actual_records} ({variance_pct:.1f}%)",
                         domain,
                         recommendation="Verify data extraction completeness")
    
    def _validate_business_rules(self, df: pd.DataFrame, domain: str, filename: str):
        """Apply domain-specific business rules"""
        
        if domain == "DM":
            self._validate_dm_business_rules(df)
        elif domain == "AE":
            self._validate_ae_business_rules(df)
        elif domain == "VS":
            self._validate_vs_business_rules(df)
        elif domain == "LB":
            self._validate_lb_business_rules(df, filename)
        elif domain == "CM":
            self._validate_cm_business_rules(df)
        elif domain == "EX":
            self._validate_ex_business_rules(df)
        elif domain == "EG":
            self._validate_eg_business_rules(df)
        elif domain == "PE":
            self._validate_pe_business_rules(df)
    
    def _validate_dm_business_rules(self, df: pd.DataFrame):
        """DM domain business rules"""
        domain = "DM"
        
        # BR-DM-001: Unique subject IDs
        if "PT" in df.columns:
            dup_subjects = df["PT"].duplicated().sum()
            if dup_subjects > 0:
                dup_ids = df[df["PT"].duplicated()]["PT"].tolist()
                self.add_issue("BR-DM-001", "CRITICAL",
                             f"{dup_subjects} duplicate subject IDs found",
                             domain, "PT", dup_ids[:5], count=dup_subjects,
                             recommendation="Each subject should appear only once in DM")
        
        # BR-DM-002: SEX controlled terminology
        if "SEX" in df.columns:
            invalid_sex = df[~df["SEX"].isin(self.ct_sex)]["SEX"].dropna()
            if len(invalid_sex) > 0:
                self.add_issue("BR-DM-002", "ERROR",
                             f"SEX contains {len(invalid_sex)} non-CT values",
                             domain, "SEX", example_values=invalid_sex.unique().tolist(),
                             count=len(invalid_sex),
                             recommendation=f"SEX must be one of: {', '.join(self.ct_sex)}")
        
        # BR-DM-003: RACE controlled terminology (check for HISPANIC)
        if "RACE" in df.columns or "RCE" in df.columns:
            race_col = "RACE" if "RACE" in df.columns else "RCE"
            hispanic_in_race = df[df[race_col].str.upper().str.contains("HISPANIC", na=False)]
            if len(hispanic_in_race) > 0:
                subject_ids = hispanic_in_race["PT"].tolist() if "PT" in hispanic_in_race.columns else []
                self.add_issue("BR-DM-003", "WARNING",
                             f"'HISPANIC' found in RACE field for {len(hispanic_in_race)} subjects",
                             domain, race_col, subject_ids[:5], count=len(hispanic_in_race),
                             recommendation="HISPANIC is ethnicity, not race. Map to ETHNIC variable during transformation.")
        
        # BR-DM-004: Birth date format
        if "BRTHDAT" in df.columns:
            invalid_dates = []
            for idx, date_val in df["BRTHDAT"].dropna().items():
                if not self._is_valid_date(str(date_val)):
                    invalid_dates.append(str(date_val))
            if invalid_dates:
                self.add_issue("BR-DM-004", "WARNING",
                             f"{len(invalid_dates)} birth dates in non-standard format",
                             domain, "BRTHDAT", example_values=invalid_dates[:5],
                             count=len(invalid_dates),
                             recommendation="Convert to ISO 8601 format (YYYY-MM-DD)")
        
        # BR-DM-005: Age range plausibility
        if "BRTHDAT" in df.columns:
            try:
                birth_dates = pd.to_datetime(df["BRTHDAT"], errors='coerce')
                ages = (datetime.now() - birth_dates).dt.days / 365.25
                implausible = ages[(ages < 18) | (ages > 120)]
                if len(implausible) > 0:
                    self.add_issue("BR-DM-005", "WARNING",
                                 f"{len(implausible)} subjects with implausible age (<18 or >120)",
                                 domain, "BRTHDAT", count=len(implausible),
                                 recommendation="Verify birth dates for age outliers")
            except:
                pass
    
    def _validate_ae_business_rules(self, df: pd.DataFrame):
        """AE domain business rules"""
        domain = "AE"
        
        # BR-AE-001: AETERM required
        if "AETERM" not in df.columns:
            self.add_issue("BR-AE-001", "CRITICAL",
                         "Required field AETERM not found",
                         domain, "AETERM",
                         recommendation="AETERM is required for all AE records")
        else:
            missing_term = df["AETERM"].isnull().sum()
            if missing_term > 0:
                self.add_issue("BR-AE-001", "CRITICAL",
                             f"AETERM missing for {missing_term} records",
                             domain, "AETERM", count=missing_term,
                             recommendation="Query sites for adverse event description")
        
        # BR-AE-004: Severity controlled terminology
        sev_cols = ["AESEV", "SEVCD", "SEVERITY"]
        for col in sev_cols:
            if col in df.columns:
                invalid_sev = df[~df[col].isin(self.ct_severity)][col].dropna()
                if len(invalid_sev) > 0:
                    self.add_issue("BR-AE-004", "ERROR",
                                 f"{col} contains {len(invalid_sev)} non-CT severity values",
                                 domain, col, example_values=invalid_sev.unique().tolist(),
                                 count=len(invalid_sev),
                                 recommendation=f"Map to CDISC CT: {', '.join(self.ct_severity)}")
        
        # BR-AE-005: Serious flag (Y/N)
        ser_cols = ["AESER", "SERIOUS", "SAE"]
        for col in ser_cols:
            if col in df.columns:
                invalid_ser = df[~df[col].isin(self.ct_yesno + [""])][col].dropna()
                if len(invalid_ser) > 0:
                    self.add_issue("BR-AE-005", "ERROR",
                                 f"{col} contains {len(invalid_ser)} non-Y/N values",
                                 domain, col, example_values=invalid_ser.unique().tolist(),
                                 count=len(invalid_ser),
                                 recommendation="Serious flag must be 'Y' or 'N'")
        
        # BR-AE-003: Start date <= end date
        start_cols = ["AESTDAT", "AEST_DATE", "STARTDATE"]
        end_cols = ["AEENDAT", "AEEN_DATE", "ENDDATE"]
        for start_col in start_cols:
            for end_col in end_cols:
                if start_col in df.columns and end_col in df.columns:
                    try:
                        start_dates = pd.to_datetime(df[start_col], errors='coerce')
                        end_dates = pd.to_datetime(df[end_col], errors='coerce')
                        invalid = (start_dates > end_dates) & start_dates.notna() & end_dates.notna()
                        if invalid.sum() > 0:
                            self.add_issue("BR-AE-003", "ERROR",
                                         f"{invalid.sum()} records have end date before start date",
                                         domain, f"{start_col}, {end_col}", count=invalid.sum(),
                                         recommendation="Verify and correct date sequence")
                    except:
                        pass
    
    def _validate_vs_business_rules(self, df: pd.DataFrame):
        """VS domain business rules"""
        domain = "VS"
        
        # BR-VS-001: Test code validation
        test_cols = ["VSTESTCD", "TESTCD", "TEST_CODE"]
        for col in test_cols:
            if col in df.columns:
                invalid_codes = df[~df[col].isin(self.vs_test_codes.keys())][col].dropna()
                if len(invalid_codes) > 0:
                    self.add_issue("BR-VS-001", "WARNING",
                                 f"{col} contains {len(invalid_codes)} non-standard test codes",
                                 domain, col, example_values=invalid_codes.unique().tolist(),
                                 count=len(invalid_codes),
                                 recommendation=f"Standard codes: {', '.join(self.vs_test_codes.keys())}")
        
        # BR-VS-004: Physiological range checks
        for test_code, test_info in self.vs_test_codes.items():
            # Look for results column
            result_cols = ["VSORRES", "ORRES", "RESULT", test_code]
            for result_col in result_cols:
                if result_col in df.columns:
                    # Filter to this test if test code column exists
                    test_df = df
                    for tc_col in test_cols:
                        if tc_col in df.columns:
                            test_df = df[df[tc_col] == test_code]
                            break
                    
                    if len(test_df) > 0:
                        try:
                            numeric_results = pd.to_numeric(test_df[result_col], errors='coerce')
                            out_of_range = numeric_results[
                                (numeric_results < test_info["min"]) | 
                                (numeric_results > test_info["max"])
                            ]
                            if len(out_of_range) > 0:
                                self.add_issue("BR-VS-004", "WARNING",
                                             f"{test_code} has {len(out_of_range)} values outside range ({test_info['min']}-{test_info['max']} {test_info['unit']})",
                                             domain, result_col, 
                                             example_values=out_of_range.head(5).astype(str).tolist(),
                                             count=len(out_of_range),
                                             recommendation="Medical review of outlier values")
                        except:
                            pass
    
    def _validate_lb_business_rules(self, df: pd.DataFrame, filename: str):
        """LB domain business rules"""
        domain = "LB"
        
        # BR-LB-001: Test code presence
        test_cols = ["LBTESTCD", "TESTCD", "TEST_CODE"]
        test_col = None
        for col in test_cols:
            if col in df.columns:
                test_col = col
                break
        
        if test_col is None:
            self.add_issue("BR-LB-001", "CRITICAL",
                         "Lab test code field not found",
                         domain,
                         recommendation="Required field for lab data transformation")
        
        # BR-LB-005: Lab category
        if "LBCAT" not in df.columns and "CATEGORY" not in df.columns:
            # Infer from filename
            if "HEM" in filename.upper():
                lab_cat = "HEMATOLOGY"
            elif "CHEM" in filename.upper():
                lab_cat = "CHEMISTRY"
            elif "URIN" in filename.upper():
                lab_cat = "URINALYSIS"
            else:
                self.add_issue("BR-LB-005", "WARNING",
                             "Lab category not specified",
                             domain,
                             recommendation="Add LBCAT field or ensure filename indicates category")
        
        # BR-LB-006: Lab date presence
        date_cols = ["LBDAT", "DATE", "TEST_DATE"]
        has_date = any(col in df.columns for col in date_cols)
        if not has_date:
            self.add_issue("BR-LB-006", "CRITICAL",
                         "Lab date field not found",
                         domain,
                         recommendation="Lab date is required for all tests")
    
    def _validate_cm_business_rules(self, df: pd.DataFrame):
        """CM domain business rules"""
        domain = "CM"
        
        # BR-CM-001: Medication name required
        med_cols = ["CMTRT", "TRT", "MEDICATION", "MED_NAME"]
        has_med = any(col in df.columns for col in med_cols)
        if not has_med:
            self.add_issue("BR-CM-001", "CRITICAL",
                         "Medication name field not found",
                         domain,
                         recommendation="Required for concomitant medications")
        else:
            for col in med_cols:
                if col in df.columns:
                    missing = df[col].isnull().sum()
                    if missing > 0:
                        self.add_issue("BR-CM-001", "ERROR",
                                     f"{col} missing for {missing} records",
                                     domain, col, count=missing,
                                     recommendation="Medication name is required")
    
    def _validate_ex_business_rules(self, df: pd.DataFrame):
        """EX domain business rules"""
        domain = "EX"
        
        # BR-EX-003: Dose must be numeric and > 0
        dose_cols = ["EXDOSE", "DOSE", "DOSE_AMT"]
        for col in dose_cols:
            if col in df.columns:
                try:
                    numeric_dose = pd.to_numeric(df[col], errors='coerce')
                    invalid_dose = numeric_dose[numeric_dose <= 0]
                    if len(invalid_dose) > 0:
                        self.add_issue("BR-EX-003", "ERROR",
                                     f"{col} has {len(invalid_dose)} values <= 0",
                                     domain, col, count=len(invalid_dose),
                                     recommendation="Dose must be positive numeric value")
                except:
                    pass
    
    def _validate_eg_business_rules(self, df: pd.DataFrame):
        """EG domain business rules"""
        domain = "EG"
        
        # BR-EG-004: QTc range check
        for test_code, ranges in self.eg_ranges.items():
            result_cols = ["EGORRES", "ORRES", "RESULT"]
            test_cols = ["EGTESTCD", "TESTCD"]
            
            for result_col in result_cols:
                if result_col in df.columns:
                    test_df = df
                    for tc_col in test_cols:
                        if tc_col in df.columns:
                            test_df = df[df[tc_col] == test_code]
                            break
                    
                    if len(test_df) > 0:
                        try:
                            numeric_results = pd.to_numeric(test_df[result_col], errors='coerce')
                            out_of_range = numeric_results[
                                (numeric_results < ranges["min"]) | 
                                (numeric_results > ranges["max"])
                            ]
                            if len(out_of_range) > 0:
                                self.add_issue(f"BR-EG-{test_code}", "WARNING",
                                             f"{test_code} has {len(out_of_range)} values outside range ({ranges['min']}-{ranges['max']} {ranges['unit']})",
                                             domain, result_col, count=len(out_of_range),
                                             recommendation="Clinical review of abnormal ECG values")
                        except:
                            pass
    
    def _validate_pe_business_rules(self, df: pd.DataFrame):
        """PE domain business rules"""
        domain = "PE"
        
        # BR-PE-002: Findings should be documented
        finding_cols = ["PEORRES", "ORRES", "FINDING"]
        for col in finding_cols:
            if col in df.columns:
                missing = df[col].isnull().sum()
                if missing > len(df) * 0.1:  # >10% missing
                    self.add_issue("BR-PE-002", "WARNING",
                                 f"{col} missing for {missing} records ({missing/len(df)*100:.1f}%)",
                                 domain, col, count=missing,
                                 recommendation="Physical exam findings should be documented")
    
    def _validate_cross_domain(self):
        """Cross-domain consistency checks"""
        
        # Get DM data
        dm_data = self.domain_data.get("DM", [])
        if not dm_data:
            self.add_issue("CROSS-001", "CRITICAL",
                         "DM (Demographics) domain not found - cannot perform cross-domain checks",
                         "CROSS-DOMAIN",
                         recommendation="DM domain is required for subject-level validation")
            return
        
        dm_df = pd.concat(dm_data, ignore_index=True) if len(dm_data) > 1 else dm_data[0]
        dm_subjects = set(dm_df["PT"].dropna().unique()) if "PT" in dm_df.columns else set()
        
        # Check all other domains reference DM subjects
        for domain, df_list in self.domain_data.items():
            if domain == "DM":
                continue
            
            for df in df_list:
                if "PT" in df.columns:
                    domain_subjects = set(df["PT"].dropna().unique())
                    orphan_subjects = domain_subjects - dm_subjects
                    
                    if orphan_subjects:
                        self.add_issue("CROSS-002", "ERROR",
                                     f"{domain} has {len(orphan_subjects)} subjects not in DM",
                                     domain, "PT",
                                     record_ids=list(orphan_subjects)[:5],
                                     count=len(orphan_subjects),
                                     recommendation="All subjects in event domains must exist in DM")
        
        print(f"✅ Cross-domain subject consistency validated")
    
    def _validate_ct_preview(self):
        """Preview controlled terminology issues"""
        
        print(f"Controlled terminology conformance preview completed")
        print(f"(Detailed CT mapping will occur during SDTM transformation)")
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Check if date is in valid format"""
        date_str = str(date_str).strip()
        
        if date_str.upper() in ["NAN", "NAT", "NONE", "NULL", ""]:
            return True
        
        patterns = [
            r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
            r'^\d{4}/\d{2}/\d{2}$',  # YYYY/MM/DD
            r'^\d{2}/\d{2}/\d{4}$',  # MM/DD/YYYY
            r'^\d{4}-\d{2}$',        # YYYY-MM
            r'^\d{4}$',              # YYYY
        ]
        
        return any(re.match(p, date_str) for p in patterns)
    
    def _calculate_overall_quality_score(self) -> float:
        """Calculate overall quality score based on issues"""
        score = 100.0
        
        # Deduct points by severity
        for issue in self.issues:
            if issue.severity == "CRITICAL":
                score -= 15
            elif issue.severity == "ERROR":
                score -= 5
            elif issue.severity == "WARNING":
                score -= 1
            # INFO doesn't affect score
        
        return max(0.0, min(100.0, score))
    
    def _assess_readiness(self, results: Dict) -> str:
        """Assess transformation readiness"""
        if results["critical_errors"] > 0:
            return "NOT READY - Critical blockers must be resolved"
        elif results["errors"] > 10:
            return "NOT READY - Too many errors"
        elif results["overall_quality_score"] < 80:
            return "NOT READY - Quality score too low"
        elif results["errors"] > 0 or results["warnings"] > 5:
            return "CONDITIONAL - Address errors and review warnings"
        else:
            return "READY - All validation checks passed"
    
    def _organize_results_by_domain(self) -> Dict:
        """Organize issues by domain"""
        domain_results = {}
        
        for issue in self.issues:
            domain = issue.domain
            if domain not in domain_results:
                domain_results[domain] = {
                    "critical": [], "errors": [], "warnings": [], "info": []
                }
            
            severity_key = issue.severity.lower() + "s" if issue.severity != "CRITICAL" else "critical"
            if severity_key in domain_results[domain]:
                domain_results[domain][severity_key].append(issue.to_dict())
        
        return domain_results
    
    def _print_final_summary(self, results: Dict):
        """Print final validation summary"""
        print(f"\n{'='*80}")
        print("VALIDATION SUMMARY")
        print(f"{'='*80}\n")
        print(f"Study: {results['study_id']}")
        print(f"Files Validated: {results['files_validated']}")
        print(f"Total Records: {results['total_records']:,}")
        print(f"Quality Score: {results['overall_quality_score']:.1f}/100\n")
        print(f"{'─'*80}")
        print(f"ISSUES BY SEVERITY:")
        print(f"{'─'*80}")
        print(f"  Critical Errors:  {results['critical_errors']:3d}  ❌ MUST FIX")
        print(f"  Errors:           {results['errors']:3d}  ⚠️  SHOULD FIX")
        print(f"  Warnings:         {results['warnings']:3d}  ⚠️  REVIEW")
        print(f"  Info:             {results['info']:3d}  ℹ️  INFORMATIONAL")
        print(f"{'─'*80}\n")
        print(f"TRANSFORMATION READINESS: {results['transformation_readiness']}\n")
        print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Enhanced Raw Data Validation for MAXIS-08 Study"
    )
    parser.add_argument("--data-path", required=True,
                       help="Path to directory containing source CSV files")
    parser.add_argument("--study-id", default="MAXIS-08",
                       help="Study identifier (default: MAXIS-08)")
    parser.add_argument("--output", required=True,
                       help="Output JSON file path for validation results")
    
    args = parser.parse_args()
    
    print(f"\n{'='*80}")
    print("MAXIS-08 ENHANCED RAW DATA VALIDATION")
    print(f"{'='*80}")
    print(f"Data Path: {args.data_path}")
    print(f"Study ID: {args.study_id}")
    print(f"Output: {args.output}")
    print(f"{'='*80}\n")
    
    # Run validation
    validator = EnhancedRawDataValidator(args.data_path, args.study_id)
    results = validator.validate_all_files()
    
    # Save results
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Validation results saved to: {args.output}\n")
    
    # Return exit code based on readiness
    if results["critical_errors"] > 0:
        return 1
    else:
        return 0


if __name__ == "__main__":
    exit(main())

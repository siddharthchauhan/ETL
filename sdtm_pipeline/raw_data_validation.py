#!/usr/bin/env python3
"""
MAXIS-08 Raw Data Validation Script
====================================

Performs comprehensive validation on source data files before SDTM transformation.
Validates identifiers, date formats, duplicates, missing data, and data quality.

Author: SDTM Pipeline - Validation Agent
Study: MAXIS-08
Date: 2025-02-02
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
import re
from collections import defaultdict
from typing import Dict, List, Tuple, Any


class RawDataValidator:
    """Comprehensive raw data validation for clinical trial source files."""
    
    def __init__(self, data_path: str, study_id: str = "MAXIS-08"):
        """
        Initialize validator.
        
        Args:
            data_path: Path to directory containing source CSV files
            study_id: Study identifier
        """
        self.data_path = Path(data_path)
        self.study_id = study_id
        self.validation_results = {}
        self.summary_stats = {}
        
        # Define file-to-domain mappings
        self.file_mappings = {
            "DEMO.csv": {"domain": "DM", "expected_records": 16, "expected_cols": 12},
            "AEVENT.csv": {"domain": "AE", "expected_records": 550, "expected_cols": 38},
            "AEVENTC.csv": {"domain": "AE", "expected_records": 276, "expected_cols": 36},
            "CONMEDS.csv": {"domain": "CM", "expected_records": 302, "expected_cols": 38},
            "CONMEDSC.csv": {"domain": "CM", "expected_records": 302, "expected_cols": 34},
            "VITALS.csv": {"domain": "VS", "expected_records": 536, "expected_cols": 21},
            "HEMLAB.csv": {"domain": "LB", "expected_records": 1726, "expected_cols": 14},
            "CHEMLAB.csv": {"domain": "LB", "expected_records": 3326, "expected_cols": 13},
            "DOSE.csv": {"domain": "EX", "expected_records": 271, "expected_cols": 21},
            "ECG.csv": {"domain": "EG", "expected_records": 60, "expected_cols": 11},
            "PHYSEXAM.csv": {"domain": "PE", "expected_records": 2169, "expected_cols": 14}
        }
        
        # Required identifier fields by domain
        self.required_identifiers = {
            "DM": ["STUDY", "INVSITE", "PT"],
            "AE": ["STUDY", "INVSITE", "PT"],
            "CM": ["STUDY", "INVSITE", "PT"],
            "VS": ["STUDY", "INVSITE", "PT"],
            "LB": ["STUDY", "INVSITE", "PT"],
            "EX": ["STUDY", "INVSITE", "PT"],
            "EG": ["STUDY", "INVSITE", "PT"],
            "PE": ["STUDY", "INVSITE", "PT"]
        }
        
        # Date fields to validate by domain pattern
        self.date_fields_patterns = [
            r'.*DATE.*', r'.*DT$', r'.*DTC$', r'.*DAT$', 
            r'.*STDT.*', r'.*ENDT.*', r'.*BRTHDAT.*'
        ]
        
    def validate_all_files(self) -> Dict[str, Any]:
        """
        Validate all source files.
        
        Returns:
            Dictionary with validation results for all files
        """
        print(f"\n{'='*80}")
        print(f"RAW DATA VALIDATION - Study {self.study_id}")
        print(f"{'='*80}\n")
        print(f"Data Path: {self.data_path}")
        print(f"Files to Validate: {len(self.file_mappings)}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        overall_results = {
            "study_id": self.study_id,
            "validation_date": datetime.now().isoformat(),
            "data_path": str(self.data_path),
            "files_validated": 0,
            "total_errors": 0,
            "total_warnings": 0,
            "file_results": {},
            "overall_quality_score": 0.0
        }
        
        for filename, metadata in self.file_mappings.items():
            print(f"\n{'─'*80}")
            print(f"Validating: {filename} → {metadata['domain']} domain")
            print(f"{'─'*80}")
            
            file_path = self.data_path / filename
            
            if not file_path.exists():
                print(f"❌ ERROR: File not found at {file_path}")
                overall_results["file_results"][filename] = {
                    "status": "MISSING",
                    "error": f"File not found at {file_path}",
                    "quality_score": 0.0
                }
                overall_results["total_errors"] += 1
                continue
            
            try:
                # Load and validate file
                df = pd.read_csv(file_path, encoding='utf-8-sig')
                result = self.validate_file(df, filename, metadata)
                
                overall_results["file_results"][filename] = result
                overall_results["files_validated"] += 1
                overall_results["total_errors"] += result.get("critical_errors_count", 0)
                overall_results["total_warnings"] += result.get("warnings_count", 0)
                
                # Print summary
                self._print_file_summary(filename, result)
                
            except Exception as e:
                print(f"❌ EXCEPTION: {str(e)}")
                overall_results["file_results"][filename] = {
                    "status": "ERROR",
                    "error": str(e),
                    "quality_score": 0.0
                }
                overall_results["total_errors"] += 1
        
        # Calculate overall quality score
        quality_scores = [
            r.get("quality_score", 0.0) 
            for r in overall_results["file_results"].values()
            if isinstance(r, dict)
        ]
        overall_results["overall_quality_score"] = (
            sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        )
        
        return overall_results
    
    def validate_file(self, df: pd.DataFrame, filename: str, 
                     metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a single source file.
        
        Args:
            df: DataFrame containing file data
            filename: Name of the file
            metadata: Expected metadata (domain, record count, etc.)
            
        Returns:
            Validation results dictionary
        """
        result = {
            "filename": filename,
            "domain": metadata["domain"],
            "status": "PASS",
            "timestamp": datetime.now().isoformat(),
            "summary_stats": {},
            "critical_errors": [],
            "warnings": [],
            "info": [],
            "quality_score": 100.0
        }
        
        # 1. Summary Statistics
        result["summary_stats"] = self._get_summary_stats(df, metadata)
        
        # 2. Check Required Identifiers
        identifier_issues = self._validate_identifiers(df, metadata["domain"])
        result["critical_errors"].extend(identifier_issues["errors"])
        result["warnings"].extend(identifier_issues["warnings"])
        
        # 3. Validate Date Formats
        date_issues = self._validate_dates(df)
        result["critical_errors"].extend(date_issues["errors"])
        result["warnings"].extend(date_issues["warnings"])
        
        # 4. Check for Duplicates
        duplicate_issues = self._check_duplicates(df, metadata["domain"])
        result["critical_errors"].extend(duplicate_issues["errors"])
        result["warnings"].extend(duplicate_issues["warnings"])
        
        # 5. Check Missing Critical Data
        missing_data_issues = self._check_missing_data(df, metadata["domain"])
        result["warnings"].extend(missing_data_issues["warnings"])
        result["info"].extend(missing_data_issues["info"])
        
        # 6. Data Quality Checks
        quality_issues = self._check_data_quality(df, metadata["domain"])
        result["warnings"].extend(quality_issues["warnings"])
        result["info"].extend(quality_issues["info"])
        
        # Calculate counts
        result["critical_errors_count"] = len(result["critical_errors"])
        result["warnings_count"] = len(result["warnings"])
        result["info_count"] = len(result["info"])
        
        # Calculate quality score
        result["quality_score"] = self._calculate_quality_score(result, df)
        
        # Determine overall status
        if result["critical_errors_count"] > 0:
            result["status"] = "FAIL"
        elif result["warnings_count"] > 5:
            result["status"] = "REVIEW"
        else:
            result["status"] = "PASS"
        
        return result
    
    def _get_summary_stats(self, df: pd.DataFrame, 
                          metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary statistics for the file."""
        actual_records = len(df)
        actual_cols = len(df.columns)
        expected_records = metadata.get("expected_records", 0)
        expected_cols = metadata.get("expected_cols", 0)
        
        return {
            "actual_records": actual_records,
            "expected_records": expected_records,
            "record_variance": actual_records - expected_records,
            "record_variance_pct": round(
                ((actual_records - expected_records) / expected_records * 100) 
                if expected_records > 0 else 0, 2
            ),
            "actual_columns": actual_cols,
            "expected_columns": expected_cols,
            "column_variance": actual_cols - expected_cols,
            "columns": list(df.columns),
            "missing_cells": int(df.isnull().sum().sum()),
            "missing_cells_pct": round(
                (df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100), 2
            ),
            "duplicate_rows": int(df.duplicated().sum())
        }
    
    def _validate_identifiers(self, df: pd.DataFrame, 
                             domain: str) -> Dict[str, List[str]]:
        """Validate required identifier fields."""
        errors = []
        warnings = []
        
        required_ids = self.required_identifiers.get(domain, ["STUDY", "INVSITE", "PT"])
        
        for id_field in required_ids:
            if id_field not in df.columns:
                errors.append(
                    f"RDV-001: Missing required identifier field '{id_field}'"
                )
            else:
                # Check for missing values
                missing_count = df[id_field].isnull().sum()
                if missing_count > 0:
                    errors.append(
                        f"RDV-002: Identifier field '{id_field}' has {missing_count} "
                        f"missing values ({missing_count/len(df)*100:.1f}%)"
                    )
                
                # Check for empty strings
                empty_count = (df[id_field].astype(str).str.strip() == '').sum()
                if empty_count > 0:
                    errors.append(
                        f"RDV-003: Identifier field '{id_field}' has {empty_count} "
                        f"empty values ({empty_count/len(df)*100:.1f}%)"
                    )
        
        # Check STUDY field value if present
        if "STUDY" in df.columns:
            study_values = df["STUDY"].dropna().unique()
            if len(study_values) == 0:
                errors.append("RDV-004: STUDY field has no valid values")
            elif len(study_values) > 1:
                warnings.append(
                    f"RDV-005: Multiple STUDY values found: {', '.join(map(str, study_values))}"
                )
            elif study_values[0] != self.study_id:
                warnings.append(
                    f"RDV-006: STUDY value '{study_values[0]}' does not match "
                    f"expected '{self.study_id}'"
                )
        
        return {"errors": errors, "warnings": warnings}
    
    def _validate_dates(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """Validate date field formats and consistency."""
        errors = []
        warnings = []
        
        # Identify date columns
        date_cols = []
        for col in df.columns:
            for pattern in self.date_fields_patterns:
                if re.match(pattern, col, re.IGNORECASE):
                    date_cols.append(col)
                    break
        
        for col in date_cols:
            # Check for missing dates
            missing_count = df[col].isnull().sum()
            missing_pct = (missing_count / len(df) * 100)
            
            if missing_pct > 50:
                warnings.append(
                    f"RDV-010: Date field '{col}' has {missing_count} missing values "
                    f"({missing_pct:.1f}%)"
                )
            
            # Validate date formats
            non_null_dates = df[col].dropna()
            if len(non_null_dates) > 0:
                invalid_dates = []
                for idx, date_val in non_null_dates.items():
                    if not self._is_valid_date_format(str(date_val)):
                        invalid_dates.append((idx, date_val))
                        if len(invalid_dates) <= 5:  # Report first 5
                            warnings.append(
                                f"RDV-011: Invalid date format in '{col}' at row {idx}: '{date_val}'"
                            )
                
                if len(invalid_dates) > 5:
                    warnings.append(
                        f"RDV-012: Date field '{col}' has {len(invalid_dates)} total "
                        f"invalid date formats (showing first 5)"
                    )
        
        # Check for start/end date consistency
        self._check_date_consistency(df, errors, warnings)
        
        return {"errors": errors, "warnings": warnings}
    
    def _is_valid_date_format(self, date_str: str) -> bool:
        """Check if date string is in valid format."""
        date_str = str(date_str).strip()
        
        if date_str == "" or date_str.upper() in ["NAN", "NAT", "NONE", "NULL"]:
            return True  # Missing dates are handled separately
        
        # Common valid formats
        valid_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD (ISO 8601)
            r'^\d{4}/\d{2}/\d{2}$',  # YYYY/MM/DD
            r'^\d{2}/\d{2}/\d{4}$',  # MM/DD/YYYY
            r'^\d{2}-[A-Z]{3}-\d{4}$',  # DD-MON-YYYY
            r'^\d{8}$',  # YYYYMMDD
            r'^\d{4}-\d{2}$',  # YYYY-MM (partial)
            r'^\d{4}$',  # YYYY (partial)
        ]
        
        for pattern in valid_patterns:
            if re.match(pattern, date_str, re.IGNORECASE):
                return True
        
        return False
    
    def _check_date_consistency(self, df: pd.DataFrame, 
                               errors: List[str], warnings: List[str]) -> None:
        """Check start/end date consistency."""
        # Common start/end date pairs
        date_pairs = [
            ("AESTDAT", "AEENDAT"),
            ("AEST_DATE", "AEEN_DATE"),
            ("CMSTDAT", "CMENDAT"),
            ("EXSTDAT", "EXENDAT"),
            ("STARTDATE", "ENDDATE"),
            ("START_DATE", "END_DATE"),
        ]
        
        for start_col, end_col in date_pairs:
            if start_col in df.columns and end_col in df.columns:
                # Convert to datetime for comparison
                try:
                    start_dates = pd.to_datetime(df[start_col], errors='coerce')
                    end_dates = pd.to_datetime(df[end_col], errors='coerce')
                    
                    # Check where end < start
                    invalid_mask = (start_dates > end_dates) & start_dates.notna() & end_dates.notna()
                    invalid_count = invalid_mask.sum()
                    
                    if invalid_count > 0:
                        errors.append(
                            f"RDV-013: {invalid_count} records have end date before start date "
                            f"({start_col} > {end_col})"
                        )
                except:
                    pass  # Skip if date conversion fails
    
    def _check_duplicates(self, df: pd.DataFrame, domain: str) -> Dict[str, List[str]]:
        """Check for duplicate records."""
        errors = []
        warnings = []
        
        # Check for completely duplicate rows
        dup_count = df.duplicated().sum()
        if dup_count > 0:
            errors.append(
                f"RDV-020: {dup_count} completely duplicate rows found "
                f"({dup_count/len(df)*100:.1f}%)"
            )
        
        # Check for duplicates on key identifiers
        key_cols = []
        potential_keys = ["STUDY", "INVSITE", "PT", "AESEQ", "CMSEQ", "VSSEQ", 
                         "LBSEQ", "EXSEQ", "EGSEQ", "PESEQ"]
        for col in potential_keys:
            if col in df.columns:
                key_cols.append(col)
        
        if len(key_cols) >= 2:
            dup_on_keys = df.duplicated(subset=key_cols).sum()
            if dup_on_keys > 0:
                warnings.append(
                    f"RDV-021: {dup_on_keys} duplicate records on key fields "
                    f"{key_cols} ({dup_on_keys/len(df)*100:.1f}%)"
                )
        
        # Check for duplicate subject IDs in DM domain
        if domain == "DM" and "PT" in df.columns:
            dup_subjects = df["PT"].duplicated().sum()
            if dup_subjects > 0:
                errors.append(
                    f"RDV-022: {dup_subjects} duplicate subject IDs (PT) in Demographics "
                    f"domain - each subject should appear only once"
                )
        
        return {"errors": errors, "warnings": warnings}
    
    def _check_missing_data(self, df: pd.DataFrame, 
                           domain: str) -> Dict[str, List[str]]:
        """Check for missing critical data elements."""
        warnings = []
        info = []
        
        # Critical fields by domain
        critical_fields = {
            "DM": ["PT", "BRTHDAT", "SEX", "RACE"],
            "AE": ["PT", "AETERM", "AESTDAT"],
            "CM": ["PT", "CMTRT", "CMSTDAT"],
            "VS": ["PT", "VSTESTCD", "VSORRES", "VSDAT"],
            "LB": ["PT", "LBTESTCD", "LBORRES", "LBDAT"],
            "EX": ["PT", "EXTRT", "EXSTDAT", "EXDOSE"],
            "EG": ["PT", "EGTESTCD", "EGORRES"],
            "PE": ["PT", "PETESTCD", "PEORRES"]
        }
        
        critical_cols = critical_fields.get(domain, [])
        
        for col in critical_cols:
            if col not in df.columns:
                warnings.append(
                    f"RDV-030: Expected critical field '{col}' not found in {domain} data"
                )
            else:
                missing_count = df[col].isnull().sum()
                missing_pct = (missing_count / len(df) * 100)
                
                if missing_pct > 10:
                    warnings.append(
                        f"RDV-031: Critical field '{col}' has {missing_count} missing values "
                        f"({missing_pct:.1f}%)"
                    )
                elif missing_pct > 0:
                    info.append(
                        f"RDV-032: Field '{col}' has {missing_count} missing values "
                        f"({missing_pct:.1f}%)"
                    )
        
        # Check overall missing data pattern
        total_missing = df.isnull().sum().sum()
        total_cells = len(df) * len(df.columns)
        missing_pct = (total_missing / total_cells * 100)
        
        if missing_pct > 20:
            warnings.append(
                f"RDV-033: High overall missing data rate: {missing_pct:.1f}% "
                f"({total_missing:,} / {total_cells:,} cells)"
            )
        
        return {"warnings": warnings, "info": info}
    
    def _check_data_quality(self, df: pd.DataFrame, 
                           domain: str) -> Dict[str, List[str]]:
        """Check data quality issues."""
        warnings = []
        info = []
        
        # Check for columns with all missing values
        all_null_cols = df.columns[df.isnull().all()].tolist()
        if all_null_cols:
            warnings.append(
                f"RDV-040: {len(all_null_cols)} columns have all missing values: "
                f"{', '.join(all_null_cols[:5])}{'...' if len(all_null_cols) > 5 else ''}"
            )
        
        # Check for columns with single value (no variance)
        for col in df.columns:
            if df[col].dtype in ['object', 'string']:
                unique_vals = df[col].dropna().unique()
                if len(unique_vals) == 1:
                    info.append(
                        f"RDV-041: Column '{col}' has only one unique value: '{unique_vals[0]}'"
                    )
        
        # Check for unusual characters in text fields
        text_cols = df.select_dtypes(include=['object']).columns
        for col in text_cols:
            non_null_vals = df[col].dropna()
            if len(non_null_vals) > 0:
                # Check for control characters
                control_char_mask = non_null_vals.astype(str).str.contains(
                    r'[\x00-\x1F\x7F]', regex=True, na=False
                )
                if control_char_mask.any():
                    warnings.append(
                        f"RDV-042: Column '{col}' contains control characters "
                        f"in {control_char_mask.sum()} records"
                    )
        
        # Check numeric fields for outliers (simple check)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col.upper().endswith('SEQ'):
                continue  # Skip sequence numbers
            
            non_null_vals = df[col].dropna()
            if len(non_null_vals) > 10:  # Only check if enough data
                q1 = non_null_vals.quantile(0.25)
                q3 = non_null_vals.quantile(0.75)
                iqr = q3 - q1
                
                if iqr > 0:
                    outliers = ((non_null_vals < (q1 - 3 * iqr)) | 
                               (non_null_vals > (q3 + 3 * iqr))).sum()
                    if outliers > 0:
                        info.append(
                            f"RDV-043: Column '{col}' has {outliers} potential outliers "
                            f"({outliers/len(non_null_vals)*100:.1f}%)"
                        )
        
        return {"warnings": warnings, "info": info}
    
    def _calculate_quality_score(self, result: Dict[str, Any], 
                                 df: pd.DataFrame) -> float:
        """
        Calculate data quality score (0-100).
        
        Scoring:
        - Start with 100 points
        - Deduct points for issues:
          - Critical errors: -10 points each
          - Warnings: -2 points each
          - High missing data: up to -20 points
          - Duplicates: up to -10 points
        """
        score = 100.0
        
        # Deduct for errors and warnings
        score -= result["critical_errors_count"] * 10
        score -= result["warnings_count"] * 2
        
        # Deduct for missing data
        missing_pct = result["summary_stats"].get("missing_cells_pct", 0)
        if missing_pct > 20:
            score -= 20
        elif missing_pct > 10:
            score -= 10
        elif missing_pct > 5:
            score -= 5
        
        # Deduct for duplicates
        dup_count = result["summary_stats"].get("duplicate_rows", 0)
        if dup_count > 0:
            dup_pct = (dup_count / len(df) * 100) if len(df) > 0 else 0
            if dup_pct > 5:
                score -= 10
            elif dup_pct > 1:
                score -= 5
        
        # Ensure score is in valid range
        return max(0.0, min(100.0, score))
    
    def _print_file_summary(self, filename: str, result: Dict[str, Any]) -> None:
        """Print summary for a single file."""
        stats = result["summary_stats"]
        
        print(f"\n📊 Summary Statistics:")
        print(f"   Records: {stats['actual_records']:,} (expected: {stats['expected_records']:,}, "
              f"variance: {stats['record_variance']:+,} / {stats['record_variance_pct']:+.1f}%)")
        print(f"   Columns: {stats['actual_columns']} (expected: {stats['expected_columns']}, "
              f"variance: {stats['column_variance']:+})")
        print(f"   Missing Cells: {stats['missing_cells']:,} ({stats['missing_cells_pct']:.1f}%)")
        print(f"   Duplicate Rows: {stats['duplicate_rows']}")
        
        print(f"\n🎯 Validation Results:")
        print(f"   Status: {result['status']}")
        print(f"   Quality Score: {result['quality_score']:.1f}/100")
        print(f"   Critical Errors: {result['critical_errors_count']}")
        print(f"   Warnings: {result['warnings_count']}")
        print(f"   Info Messages: {result['info_count']}")
        
        # Print critical errors
        if result["critical_errors"]:
            print(f"\n❌ Critical Errors ({result['critical_errors_count']}):")
            for error in result["critical_errors"][:10]:  # Show first 10
                print(f"   • {error}")
            if result['critical_errors_count'] > 10:
                print(f"   ... and {result['critical_errors_count'] - 10} more")
        
        # Print warnings
        if result["warnings"]:
            print(f"\n⚠️  Warnings ({result['warnings_count']}):")
            for warning in result["warnings"][:10]:  # Show first 10
                print(f"   • {warning}")
            if result['warnings_count'] > 10:
                print(f"   ... and {result['warnings_count'] - 10} more")
    
    def generate_report(self, results: Dict[str, Any], 
                       output_path: str = None) -> str:
        """
        Generate comprehensive validation report.
        
        Args:
            results: Validation results from validate_all_files()
            output_path: Optional path to save report
            
        Returns:
            Report content as string
        """
        report_lines = []
        
        # Header
        report_lines.append("=" * 100)
        report_lines.append(f"RAW DATA VALIDATION REPORT - Study {results['study_id']}")
        report_lines.append("=" * 100)
        report_lines.append(f"Validation Date: {results['validation_date']}")
        report_lines.append(f"Data Path: {results['data_path']}")
        report_lines.append(f"Files Validated: {results['files_validated']} / {len(self.file_mappings)}")
        report_lines.append("")
        
        # Executive Summary
        report_lines.append("EXECUTIVE SUMMARY")
        report_lines.append("-" * 100)
        report_lines.append(f"Overall Quality Score: {results['overall_quality_score']:.1f}/100")
        report_lines.append(f"Total Critical Errors: {results['total_errors']}")
        report_lines.append(f"Total Warnings: {results['total_warnings']}")
        
        # Determine readiness
        if results['total_errors'] == 0 and results['overall_quality_score'] >= 85:
            readiness = "✅ READY FOR TRANSFORMATION"
        elif results['total_errors'] > 0:
            readiness = "❌ NOT READY - Critical errors must be resolved"
        else:
            readiness = "⚠️  READY WITH CAUTIONS - Review warnings before proceeding"
        
        report_lines.append(f"Transformation Readiness: {readiness}")
        report_lines.append("")
        
        # Per-File Results
        report_lines.append("PER-FILE VALIDATION RESULTS")
        report_lines.append("-" * 100)
        
        # Create summary table
        report_lines.append(f"{'File':<20} {'Domain':<8} {'Records':<10} {'Status':<10} {'Score':<8} {'Errors':<8} {'Warnings':<10}")
        report_lines.append("-" * 100)
        
        for filename, file_result in results["file_results"].items():
            if isinstance(file_result, dict) and "summary_stats" in file_result:
                stats = file_result["summary_stats"]
                report_lines.append(
                    f"{filename:<20} {file_result['domain']:<8} "
                    f"{stats['actual_records']:<10,} {file_result['status']:<10} "
                    f"{file_result['quality_score']:<8.1f} "
                    f"{file_result['critical_errors_count']:<8} "
                    f"{file_result['warnings_count']:<10}"
                )
            else:
                status = file_result.get("status", "ERROR")
                report_lines.append(
                    f"{filename:<20} {'N/A':<8} {'N/A':<10} {status:<10} "
                    f"{'0.0':<8} {'N/A':<8} {'N/A':<10}"
                )
        
        report_lines.append("")
        
        # Detailed Results by File
        report_lines.append("DETAILED VALIDATION RESULTS BY FILE")
        report_lines.append("=" * 100)
        
        for filename, file_result in results["file_results"].items():
            if not isinstance(file_result, dict) or "summary_stats" not in file_result:
                continue
            
            report_lines.append(f"\n{filename} → {file_result['domain']} Domain")
            report_lines.append("-" * 100)
            
            stats = file_result["summary_stats"]
            report_lines.append(f"Records: {stats['actual_records']:,} "
                              f"(variance: {stats['record_variance']:+,} / {stats['record_variance_pct']:+.1f}%)")
            report_lines.append(f"Columns: {stats['actual_columns']} "
                              f"(variance: {stats['column_variance']:+})")
            report_lines.append(f"Missing Data: {stats['missing_cells']:,} cells ({stats['missing_cells_pct']:.1f}%)")
            report_lines.append(f"Duplicate Rows: {stats['duplicate_rows']}")
            report_lines.append(f"Quality Score: {file_result['quality_score']:.1f}/100")
            report_lines.append(f"Status: {file_result['status']}")
            report_lines.append("")
            
            if file_result["critical_errors"]:
                report_lines.append(f"Critical Errors ({len(file_result['critical_errors'])}):")
                for error in file_result["critical_errors"]:
                    report_lines.append(f"  • {error}")
                report_lines.append("")
            
            if file_result["warnings"]:
                report_lines.append(f"Warnings ({len(file_result['warnings'])}):")
                for warning in file_result["warnings"][:15]:  # Limit to 15
                    report_lines.append(f"  • {warning}")
                if len(file_result["warnings"]) > 15:
                    report_lines.append(f"  ... and {len(file_result['warnings']) - 15} more warnings")
                report_lines.append("")
        
        # Recommendations
        report_lines.append("\nRECOMMENDATIONS FOR DATA CLEANING")
        report_lines.append("=" * 100)
        
        recommendations = self._generate_recommendations(results)
        for i, rec in enumerate(recommendations, 1):
            report_lines.append(f"{i}. {rec}")
        
        report_lines.append("")
        report_lines.append("=" * 100)
        report_lines.append(f"End of Report - Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("=" * 100)
        
        report_content = "\n".join(report_lines)
        
        # Save to file if path provided
        if output_path:
            Path(output_path).write_text(report_content, encoding='utf-8')
            print(f"\n✅ Report saved to: {output_path}")
        
        return report_content
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Check for missing files
        missing_files = [
            fname for fname, result in results["file_results"].items()
            if isinstance(result, dict) and result.get("status") == "MISSING"
        ]
        if missing_files:
            recommendations.append(
                f"CRITICAL: Locate and load missing files: {', '.join(missing_files)}"
            )
        
        # Check for identifier issues
        id_error_files = []
        for fname, result in results["file_results"].items():
            if isinstance(result, dict) and "critical_errors" in result:
                has_id_errors = any("RDV-00" in e for e in result["critical_errors"])
                if has_id_errors:
                    id_error_files.append(fname)
        
        if id_error_files:
            recommendations.append(
                f"HIGH PRIORITY: Fix missing/invalid identifiers (STUDY, INVSITE, PT) in: "
                f"{', '.join(id_error_files)}"
            )
        
        # Check for date format issues
        date_error_files = []
        for fname, result in results["file_results"].items():
            if isinstance(result, dict) and "warnings" in result:
                has_date_errors = any("RDV-01" in w for w in result["warnings"])
                if has_date_errors:
                    date_error_files.append(fname)
        
        if date_error_files:
            recommendations.append(
                f"MEDIUM PRIORITY: Standardize date formats (recommend ISO 8601: YYYY-MM-DD) in: "
                f"{', '.join(date_error_files)}"
            )
        
        # Check for duplicate issues
        dup_error_files = []
        for fname, result in results["file_results"].items():
            if isinstance(result, dict):
                has_dup_errors = any(
                    "RDV-02" in e for e in result.get("critical_errors", [])
                )
                if has_dup_errors:
                    dup_error_files.append(fname)
        
        if dup_error_files:
            recommendations.append(
                f"HIGH PRIORITY: Remove duplicate records in: {', '.join(dup_error_files)}"
            )
        
        # Check for high missing data
        high_missing_files = []
        for fname, result in results["file_results"].items():
            if isinstance(result, dict) and "summary_stats" in result:
                if result["summary_stats"].get("missing_cells_pct", 0) > 15:
                    high_missing_files.append(
                        f"{fname} ({result['summary_stats']['missing_cells_pct']:.1f}%)"
                    )
        
        if high_missing_files:
            recommendations.append(
                f"REVIEW: Investigate high missing data rates in: {', '.join(high_missing_files)}"
            )
        
        # Check overall quality
        if results["overall_quality_score"] < 70:
            recommendations.append(
                "CRITICAL: Overall data quality is low (< 70/100). "
                "Address critical errors and major warnings before SDTM transformation."
            )
        elif results["overall_quality_score"] < 85:
            recommendations.append(
                "CAUTION: Data quality is acceptable but could be improved. "
                "Review warnings to enhance data quality before transformation."
            )
        
        # General recommendations
        recommendations.append(
            "Ensure all date fields use consistent format (preferably ISO 8601: YYYY-MM-DD)"
        )
        recommendations.append(
            "Verify that all subjects (PT) have corresponding records in DEMO.csv"
        )
        recommendations.append(
            "Confirm that STUDY field values match expected study ID (MAXIS-08)"
        )
        recommendations.append(
            "Review and document any intentional missing data (e.g., adverse events not applicable)"
        )
        
        if results["total_errors"] == 0:
            recommendations.append(
                "✅ No critical errors found - Data is ready for SDTM transformation after "
                "addressing warnings"
            )
        
        return recommendations


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validate raw source data files for SDTM transformation"
    )
    parser.add_argument(
        "--data-path",
        default="/tmp/s3_data/extracted/Maxis-08 RAW DATA_CSV",
        help="Path to directory containing source CSV files"
    )
    parser.add_argument(
        "--study-id",
        default="MAXIS-08",
        help="Study identifier"
    )
    parser.add_argument(
        "--output",
        default="/Users/siddharthchauhan/Work/Projects/ETL/sdtm_pipeline/MAXIS-08_RAW_DATA_VALIDATION_REPORT.md",
        help="Output path for validation report"
    )
    parser.add_argument(
        "--json-output",
        help="Optional JSON output path for validation results"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("MAXIS-08 RAW DATA VALIDATION")
    print("="*80)
    print(f"Data Path: {args.data_path}")
    print(f"Study ID: {args.study_id}")
    print(f"Report Output: {args.output}")
    print("="*80 + "\n")
    
    # Initialize validator
    validator = RawDataValidator(args.data_path, args.study_id)
    
    # Run validation
    results = validator.validate_all_files()
    
    # Generate report
    print("\n" + "="*80)
    print("GENERATING VALIDATION REPORT")
    print("="*80)
    
    report = validator.generate_report(results, args.output)
    
    # Save JSON if requested
    if args.json_output:
        with open(args.json_output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"✅ JSON results saved to: {args.json_output}")
    
    # Print summary
    print("\n" + "="*80)
    print("VALIDATION COMPLETE")
    print("="*80)
    print(f"Overall Quality Score: {results['overall_quality_score']:.1f}/100")
    print(f"Critical Errors: {results['total_errors']}")
    print(f"Warnings: {results['total_warnings']}")
    print(f"Files Validated: {results['files_validated']}")
    
    if results['total_errors'] == 0:
        print("\n✅ SUCCESS: No critical errors found")
        print("   Data is ready for SDTM transformation after reviewing warnings")
    else:
        print("\n❌ FAILURE: Critical errors found")
        print("   Data is NOT ready for SDTM transformation")
        print("   Please address critical errors before proceeding")
    
    print("="*80 + "\n")
    
    return 0 if results['total_errors'] == 0 else 1


if __name__ == "__main__":
    exit(main())

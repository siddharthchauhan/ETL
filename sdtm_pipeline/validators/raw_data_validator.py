"""
Raw Data Validator
==================
Validates raw clinical trial data before SDTM transformation.
Checks data quality, completeness, and consistency.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re

from ..models.sdtm_models import (
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    ValidationRule
)


class RawDataValidator:
    """
    Validates raw clinical trial data for quality and completeness.

    Performs checks including:
    - Required fields presence
    - Data type validation
    - Date format validation
    - Value range checks
    - Cross-field consistency
    - Duplicate detection
    """

    def __init__(self, study_id: str = "UNKNOWN"):
        self.study_id = study_id
        self.validation_rules: List[ValidationRule] = []
        self._setup_default_rules()

    def _setup_default_rules(self):
        """Setup default validation rules for raw data."""
        self.validation_rules = [
            ValidationRule(
                rule_id="RAW001",
                rule_type="Data Quality",
                description="Subject ID must be present",
                severity=ValidationSeverity.ERROR,
                check_expression="PT is not null"
            ),
            ValidationRule(
                rule_id="RAW002",
                rule_type="Data Quality",
                description="Study identifier must be consistent",
                severity=ValidationSeverity.ERROR,
                check_expression="STUDY is consistent"
            ),
            ValidationRule(
                rule_id="RAW003",
                rule_type="Data Quality",
                description="Date values must be valid format",
                severity=ValidationSeverity.ERROR,
                check_expression="Date format YYYYMMDD"
            ),
            ValidationRule(
                rule_id="RAW004",
                rule_type="Data Quality",
                description="Numeric values must be within reasonable range",
                severity=ValidationSeverity.WARNING,
                check_expression="Numeric range check"
            ),
            ValidationRule(
                rule_id="RAW005",
                rule_type="Data Quality",
                description="No duplicate records",
                severity=ValidationSeverity.WARNING,
                check_expression="No exact duplicates"
            ),
        ]

    def validate_dataframe(self, df: pd.DataFrame, domain_name: str) -> ValidationResult:
        """
        Validate a pandas DataFrame containing raw clinical data.

        Args:
            df: DataFrame to validate
            domain_name: Name of the data domain (e.g., DEMO, AEVENT)

        Returns:
            ValidationResult with all identified issues
        """
        issues: List[ValidationIssue] = []

        # Check for empty dataframe
        if df.empty:
            issues.append(ValidationIssue(
                rule_id="RAW000",
                severity=ValidationSeverity.ERROR,
                message="Dataset is empty",
                domain=domain_name
            ))
            return ValidationResult(
                is_valid=False,
                domain=domain_name,
                total_records=0,
                issues=issues
            )

        # Run all validation checks
        issues.extend(self._check_required_fields(df, domain_name))
        issues.extend(self._check_subject_ids(df, domain_name))
        issues.extend(self._check_date_fields(df, domain_name))
        issues.extend(self._check_numeric_fields(df, domain_name))
        issues.extend(self._check_duplicates(df, domain_name))
        issues.extend(self._check_missing_values(df, domain_name))
        issues.extend(self._check_data_consistency(df, domain_name))

        # Determine if valid (no errors)
        error_count = sum(1 for i in issues if i.severity == ValidationSeverity.ERROR)
        is_valid = error_count == 0

        return ValidationResult(
            is_valid=is_valid,
            domain=domain_name,
            total_records=len(df),
            issues=issues
        )

    def _check_required_fields(self, df: pd.DataFrame, domain: str) -> List[ValidationIssue]:
        """Check for required fields based on domain type."""
        issues = []

        # Define required fields for each domain type
        required_fields = {
            "DEMO": ["PT", "STUDY"],
            "AEVENT": ["PT", "STUDY"],
            "VITALS": ["PT", "STUDY"],
            "CHEMLAB": ["PT", "STUDY"],
            "HEMLAB": ["PT", "STUDY"],
            "CONMEDS": ["PT", "STUDY"],
            "DOSE": ["PT", "STUDY"],
        }

        domain_key = domain.replace(".csv", "").upper()
        required = required_fields.get(domain_key, ["PT"])

        for field in required:
            if field not in df.columns:
                issues.append(ValidationIssue(
                    rule_id="RAW001",
                    severity=ValidationSeverity.ERROR,
                    message=f"Required field '{field}' is missing from dataset",
                    domain=domain,
                    variable=field
                ))

        return issues

    def _check_subject_ids(self, df: pd.DataFrame, domain: str) -> List[ValidationIssue]:
        """Validate subject identifier field."""
        issues = []

        if "PT" in df.columns:
            # Check for null subject IDs
            null_count = df["PT"].isna().sum()
            if null_count > 0:
                issues.append(ValidationIssue(
                    rule_id="RAW001",
                    severity=ValidationSeverity.ERROR,
                    message=f"Found {null_count} records with missing subject ID (PT)",
                    domain=domain,
                    variable="PT"
                ))

            # Check subject ID format (expecting pattern like XX-XX)
            if not df["PT"].isna().all():
                invalid_format = df[~df["PT"].isna()]["PT"].apply(
                    lambda x: not bool(re.match(r"^\d{2}-\d{2}$", str(x)))
                ).sum()
                if invalid_format > 0:
                    issues.append(ValidationIssue(
                        rule_id="RAW006",
                        severity=ValidationSeverity.WARNING,
                        message=f"Found {invalid_format} subject IDs with unexpected format",
                        domain=domain,
                        variable="PT"
                    ))

        return issues

    def _check_date_fields(self, df: pd.DataFrame, domain: str) -> List[ValidationIssue]:
        """Validate date field formats."""
        issues = []

        # Identify potential date columns
        date_columns = [col for col in df.columns if any(
            keyword in col.upper() for keyword in ["DATE", "DT", "DOB", "STDT", "ENDT"]
        )]

        for col in date_columns:
            if col not in df.columns:
                continue

            # Check for invalid dates
            invalid_dates = 0
            for idx, value in df[col].items():
                if pd.isna(value):
                    continue

                # Try to parse as YYYYMMDD format
                str_val = str(int(value)) if isinstance(value, (int, float)) else str(value)
                if len(str_val) == 8:
                    try:
                        datetime.strptime(str_val, "%Y%m%d")
                    except ValueError:
                        invalid_dates += 1
                        if invalid_dates <= 5:  # Only report first few
                            issues.append(ValidationIssue(
                                rule_id="RAW003",
                                severity=ValidationSeverity.ERROR,
                                message=f"Invalid date value: {value}",
                                domain=domain,
                                variable=col,
                                value=value
                            ))

            if invalid_dates > 5:
                issues.append(ValidationIssue(
                    rule_id="RAW003",
                    severity=ValidationSeverity.ERROR,
                    message=f"Found {invalid_dates} total invalid dates in column {col}",
                    domain=domain,
                    variable=col
                ))

        return issues

    def _check_numeric_fields(self, df: pd.DataFrame, domain: str) -> List[ValidationIssue]:
        """Validate numeric field ranges."""
        issues = []

        # Define expected ranges for common numeric fields
        numeric_ranges = {
            "AGE": (0, 120),
            "TEMP": (30, 45),  # Celsius
            "SYSBP": (50, 250),
            "DIABP": (30, 150),
            "PULSE": (30, 200),
            "RESP": (5, 60),
            "WEIGHT": (20, 300),
            "HEIGHT": (50, 250),
        }

        for col, (min_val, max_val) in numeric_ranges.items():
            if col in df.columns:
                numeric_col = pd.to_numeric(df[col], errors='coerce')
                out_of_range = ((numeric_col < min_val) | (numeric_col > max_val)).sum()

                if out_of_range > 0:
                    issues.append(ValidationIssue(
                        rule_id="RAW004",
                        severity=ValidationSeverity.WARNING,
                        message=f"Found {out_of_range} values outside expected range [{min_val}, {max_val}]",
                        domain=domain,
                        variable=col
                    ))

        return issues

    def _check_duplicates(self, df: pd.DataFrame, domain: str) -> List[ValidationIssue]:
        """Check for duplicate records."""
        issues = []

        # Check for exact duplicates
        duplicate_count = df.duplicated().sum()
        if duplicate_count > 0:
            issues.append(ValidationIssue(
                rule_id="RAW005",
                severity=ValidationSeverity.WARNING,
                message=f"Found {duplicate_count} exact duplicate records",
                domain=domain
            ))

        # Check for duplicate subject + visit combinations if applicable
        if "PT" in df.columns and "VISIT" in df.columns:
            key_cols = ["PT", "VISIT"]

            # For events domains, add sequence-like columns
            if any(col in df.columns for col in ["AESEQ", "SEQ", "REPEATSN"]):
                for seq_col in ["AESEQ", "SEQ", "REPEATSN"]:
                    if seq_col in df.columns:
                        key_cols.append(seq_col)
                        break

            dup_keys = df.duplicated(subset=key_cols, keep=False).sum()
            if dup_keys > 0 and len(key_cols) == 2:  # Only report if no sequence column
                issues.append(ValidationIssue(
                    rule_id="RAW005",
                    severity=ValidationSeverity.INFO,
                    message=f"Found {dup_keys} records with duplicate PT+VISIT combination",
                    domain=domain
                ))

        return issues

    def _check_missing_values(self, df: pd.DataFrame, domain: str) -> List[ValidationIssue]:
        """Check for excessive missing values."""
        issues = []

        total_records = len(df)
        if total_records == 0:
            return issues

        for col in df.columns:
            missing_count = df[col].isna().sum()
            missing_pct = (missing_count / total_records) * 100

            if missing_pct > 50:
                issues.append(ValidationIssue(
                    rule_id="RAW007",
                    severity=ValidationSeverity.WARNING,
                    message=f"Column has {missing_pct:.1f}% missing values ({missing_count}/{total_records})",
                    domain=domain,
                    variable=col
                ))
            elif missing_pct > 90:
                issues.append(ValidationIssue(
                    rule_id="RAW007",
                    severity=ValidationSeverity.INFO,
                    message=f"Column is mostly empty ({missing_pct:.1f}% missing)",
                    domain=domain,
                    variable=col
                ))

        return issues

    def _check_data_consistency(self, df: pd.DataFrame, domain: str) -> List[ValidationIssue]:
        """Check for data consistency issues."""
        issues = []

        # Check STUDY field consistency
        if "STUDY" in df.columns:
            unique_studies = df["STUDY"].dropna().unique()
            if len(unique_studies) > 1:
                issues.append(ValidationIssue(
                    rule_id="RAW002",
                    severity=ValidationSeverity.ERROR,
                    message=f"Multiple study identifiers found: {list(unique_studies)}",
                    domain=domain,
                    variable="STUDY"
                ))

        # Check gender consistency
        if "GENDER" in df.columns or "GENDRL" in df.columns:
            gender_col = "GENDER" if "GENDER" in df.columns else "GENDRL"
            valid_genders = ["M", "F", "MALE", "FEMALE", "U", "UNKNOWN"]
            invalid_genders = df[~df[gender_col].isna()][gender_col].apply(
                lambda x: str(x).upper() not in valid_genders
            ).sum()

            if invalid_genders > 0:
                issues.append(ValidationIssue(
                    rule_id="RAW008",
                    severity=ValidationSeverity.WARNING,
                    message=f"Found {invalid_genders} invalid gender values",
                    domain=domain,
                    variable=gender_col
                ))

        return issues

    def validate_file(self, filepath: str) -> ValidationResult:
        """
        Validate a CSV file.

        Args:
            filepath: Path to CSV file

        Returns:
            ValidationResult
        """
        import os

        domain_name = os.path.basename(filepath)

        try:
            df = pd.read_csv(filepath)
            return self.validate_dataframe(df, domain_name)
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                domain=domain_name,
                total_records=0,
                issues=[ValidationIssue(
                    rule_id="RAW999",
                    severity=ValidationSeverity.ERROR,
                    message=f"Failed to read file: {str(e)}",
                    domain=domain_name
                )]
            )

    def generate_report(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """
        Generate a summary validation report.

        Args:
            results: List of ValidationResult objects

        Returns:
            Summary report dictionary
        """
        total_errors = sum(r.error_count for r in results)
        total_warnings = sum(r.warning_count for r in results)
        total_info = sum(r.info_count for r in results)
        total_records = sum(r.total_records for r in results)

        all_valid = all(r.is_valid for r in results)

        return {
            "summary": {
                "overall_valid": all_valid,
                "domains_validated": len(results),
                "total_records": total_records,
                "total_errors": total_errors,
                "total_warnings": total_warnings,
                "total_info": total_info
            },
            "by_domain": {r.domain: r.to_dict() for r in results},
            "generated_at": datetime.now().isoformat()
        }

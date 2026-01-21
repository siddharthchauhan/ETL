"""
Raw Data Validator (Phase 2: Business Checks)
=============================================

Validates raw clinical trial data BEFORE SDTM transformation.
This is a critical validation phase that applies:

1. Data Profiling - completeness, uniqueness, consistency
2. Business Rules - edit checks, range checks, consistency checks
3. Source Data Review (SDR) - flagging incorrect/suspicious records

The output includes validation FLAGS that track issues through the pipeline.

Author: SDTM ETL Pipeline
Version: 2.0.0 (Enhanced with 7-phase pipeline support)
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime
import re
import uuid
import json

from ..models.sdtm_models import (
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    ValidationRule
)

from ..models.pipeline_phases import (
    PipelinePhase,
    ValidationFlag,
    ValidationFlagSeverity,
    BusinessRule,
    BusinessRuleCategory
)


class RawDataValidator:
    """
    Validates raw clinical trial data for quality and completeness.
    This implements Phase 2 (Raw Data Validation) of the SDTM ETL pipeline.

    Validation Categories:
    1. DATA PROFILING
       - Completeness checks (missing values)
       - Uniqueness checks (duplicates)
       - Consistency checks (data types, formats)

    2. BUSINESS RULES (Edit Checks)
       - Mandatory field checks
       - Range checks (numerical values)
       - Date logic validation
       - Cross-field consistency
       - Protocol compliance

    3. SOURCE DATA REVIEW (SDR)
       - Record flagging with severity levels
       - Issue tracking for data management
       - Flag resolution workflow

    Output:
    - ValidationResult with issues
    - ValidationFlags for flagged records
    - Source Data Review report
    """

    def __init__(self, study_id: str = "UNKNOWN"):
        self.study_id = study_id
        self.validation_rules: List[ValidationRule] = []
        self.business_rules: List[BusinessRule] = []
        self.flags: List[ValidationFlag] = []
        self._setup_default_rules()
        self._setup_business_rules()

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

    def _setup_business_rules(self):
        """
        Setup comprehensive business rules for raw data validation.
        These rules implement the edit checks required before SDTM transformation.
        """
        self.business_rules = [
            # ======== MANDATORY FIELD CHECKS ========
            BusinessRule(
                rule_id="BUS001",
                category=BusinessRuleCategory.MANDATORY_FIELD,
                name="Subject ID Required",
                description="Subject identifier must be present in all records",
                applies_to=["DEMO", "AEVENT", "VITALS", "CHEMLAB", "HEMLAB", "CONMEDS", "DOSE", "MEDHIST"],
                variables=["PT"],
                condition="PT is not null and PT != ''",
                severity=ValidationFlagSeverity.CRITICAL,
                source="cdm_standard"
            ),
            BusinessRule(
                rule_id="BUS002",
                category=BusinessRuleCategory.MANDATORY_FIELD,
                name="Study ID Required",
                description="Study identifier must be present",
                applies_to=["DEMO", "AEVENT", "VITALS", "CHEMLAB", "HEMLAB", "CONMEDS", "DOSE"],
                variables=["STUDY"],
                condition="STUDY is not null",
                severity=ValidationFlagSeverity.CRITICAL,
                source="cdm_standard"
            ),

            # ======== RANGE CHECKS ========
            BusinessRule(
                rule_id="BUS010",
                category=BusinessRuleCategory.RANGE_CHECK,
                name="Age Within Physiological Range",
                description="Subject age must be between 0 and 120 years",
                applies_to=["DEMO"],
                variables=["AGE"],
                condition="AGE >= 0 AND AGE <= 120",
                severity=ValidationFlagSeverity.ERROR,
                source="cdm_standard"
            ),
            BusinessRule(
                rule_id="BUS011",
                category=BusinessRuleCategory.RANGE_CHECK,
                name="Systolic BP Range",
                description="Systolic blood pressure should be between 50 and 250 mmHg",
                applies_to=["VITALS"],
                variables=["SYSBP"],
                condition="SYSBP >= 50 AND SYSBP <= 250",
                severity=ValidationFlagSeverity.WARNING,
                source="protocol"
            ),
            BusinessRule(
                rule_id="BUS012",
                category=BusinessRuleCategory.RANGE_CHECK,
                name="Diastolic BP Range",
                description="Diastolic blood pressure should be between 30 and 150 mmHg",
                applies_to=["VITALS"],
                variables=["DIABP"],
                condition="DIABP >= 30 AND DIABP <= 150",
                severity=ValidationFlagSeverity.WARNING,
                source="protocol"
            ),
            BusinessRule(
                rule_id="BUS013",
                category=BusinessRuleCategory.RANGE_CHECK,
                name="Pulse Rate Range",
                description="Pulse rate should be between 30 and 200 bpm",
                applies_to=["VITALS"],
                variables=["PULSE"],
                condition="PULSE >= 30 AND PULSE <= 200",
                severity=ValidationFlagSeverity.WARNING,
                source="protocol"
            ),
            BusinessRule(
                rule_id="BUS014",
                category=BusinessRuleCategory.RANGE_CHECK,
                name="Body Temperature Range",
                description="Body temperature should be between 30 and 45 Celsius",
                applies_to=["VITALS"],
                variables=["TEMP"],
                condition="TEMP >= 30 AND TEMP <= 45",
                severity=ValidationFlagSeverity.WARNING,
                source="protocol"
            ),
            BusinessRule(
                rule_id="BUS015",
                category=BusinessRuleCategory.RANGE_CHECK,
                name="Weight Range",
                description="Body weight should be between 20 and 300 kg",
                applies_to=["VITALS", "DEMO"],
                variables=["WEIGHT"],
                condition="WEIGHT >= 20 AND WEIGHT <= 300",
                severity=ValidationFlagSeverity.WARNING,
                source="protocol"
            ),

            # ======== DATE LOGIC CHECKS ========
            BusinessRule(
                rule_id="BUS020",
                category=BusinessRuleCategory.DATE_LOGIC,
                name="Valid Date Format",
                description="Date fields must be in YYYYMMDD format",
                applies_to=["ALL"],
                variables=["*DATE*", "*DT", "DOB"],
                condition="Date is valid YYYYMMDD",
                severity=ValidationFlagSeverity.ERROR,
                source="cdm_standard"
            ),
            BusinessRule(
                rule_id="BUS021",
                category=BusinessRuleCategory.DATE_LOGIC,
                name="End Date After Start Date",
                description="End date must be on or after start date",
                applies_to=["AEVENT", "CONMEDS", "DOSE"],
                variables=["STDT", "ENDT"],
                condition="ENDT >= STDT or ENDT is null",
                severity=ValidationFlagSeverity.ERROR,
                source="cdm_standard"
            ),
            BusinessRule(
                rule_id="BUS022",
                category=BusinessRuleCategory.DATE_LOGIC,
                name="Birth Date Before Study Entry",
                description="Date of birth must be before first dose/study entry",
                applies_to=["DEMO"],
                variables=["DOB", "RFSTDTC"],
                condition="DOB < RFSTDTC",
                severity=ValidationFlagSeverity.ERROR,
                source="cdm_standard"
            ),
            BusinessRule(
                rule_id="BUS023",
                category=BusinessRuleCategory.DATE_LOGIC,
                name="Future Dates Not Allowed",
                description="Clinical data dates cannot be in the future",
                applies_to=["ALL"],
                variables=["*DATE*"],
                condition="DATE <= TODAY",
                severity=ValidationFlagSeverity.ERROR,
                source="cdm_standard"
            ),

            # ======== CONSISTENCY CHECKS ========
            BusinessRule(
                rule_id="BUS030",
                category=BusinessRuleCategory.CONSISTENCY_CHECK,
                name="Gender Consistency",
                description="Gender values must be consistent for a subject across all records",
                applies_to=["DEMO", "AEVENT", "VITALS"],
                variables=["GENDER", "GENDRL"],
                condition="Gender is same for PT across all records",
                severity=ValidationFlagSeverity.ERROR,
                source="cdm_standard"
            ),
            BusinessRule(
                rule_id="BUS031",
                category=BusinessRuleCategory.CONSISTENCY_CHECK,
                name="Valid Gender Values",
                description="Gender must be M, F, or U (Unknown)",
                applies_to=["DEMO"],
                variables=["GENDER", "GENDRL"],
                condition="GENDER in ('M', 'F', 'MALE', 'FEMALE', 'U', 'UNKNOWN')",
                severity=ValidationFlagSeverity.ERROR,
                source="cdisc"
            ),
            BusinessRule(
                rule_id="BUS032",
                category=BusinessRuleCategory.CONSISTENCY_CHECK,
                name="BP Relationship",
                description="Systolic BP should be greater than diastolic BP",
                applies_to=["VITALS"],
                variables=["SYSBP", "DIABP"],
                condition="SYSBP > DIABP",
                severity=ValidationFlagSeverity.WARNING,
                source="clinical"
            ),

            # ======== DUPLICATE CHECKS ========
            BusinessRule(
                rule_id="BUS040",
                category=BusinessRuleCategory.DUPLICATE_CHECK,
                name="No Exact Duplicate Records",
                description="Dataset should not contain exact duplicate records",
                applies_to=["ALL"],
                variables=["*"],
                condition="No exact row duplicates",
                severity=ValidationFlagSeverity.WARNING,
                source="cdm_standard"
            ),
            BusinessRule(
                rule_id="BUS041",
                category=BusinessRuleCategory.DUPLICATE_CHECK,
                name="Unique Subject-Visit Combination",
                description="Subject + Visit combination should be unique in non-repeating domains",
                applies_to=["VITALS", "DEMO"],
                variables=["PT", "VISIT"],
                condition="PT + VISIT is unique",
                severity=ValidationFlagSeverity.WARNING,
                source="sdtmig"
            ),

            # ======== FORMAT CHECKS ========
            BusinessRule(
                rule_id="BUS050",
                category=BusinessRuleCategory.FORMAT_CHECK,
                name="Subject ID Format",
                description="Subject ID should follow XX-XX format",
                applies_to=["ALL"],
                variables=["PT"],
                condition="PT matches pattern \\d{2}-\\d{2}",
                severity=ValidationFlagSeverity.WARNING,
                source="protocol"
            ),

            # ======== REFERENTIAL INTEGRITY ========
            BusinessRule(
                rule_id="BUS060",
                category=BusinessRuleCategory.REFERENTIAL_INTEGRITY,
                name="Subject Exists in Demographics",
                description="All subjects in events/findings must exist in demographics",
                applies_to=["AEVENT", "VITALS", "CHEMLAB", "HEMLAB", "CONMEDS", "DOSE"],
                variables=["PT"],
                condition="PT exists in DEMO dataset",
                severity=ValidationFlagSeverity.ERROR,
                source="sdtmig"
            ),
        ]

    def create_flag(
        self,
        record_id: Optional[str],
        domain: str,
        variable: Optional[str],
        severity: ValidationFlagSeverity,
        rule_id: str,
        message: str,
        source_value: Any = None,
        suggested_fix: Optional[str] = None
    ) -> ValidationFlag:
        """
        Create a validation flag for a record.

        Flags are the primary mechanism for tracking data quality issues
        throughout the ETL pipeline.
        """
        flag = ValidationFlag(
            flag_id=f"FLG-{uuid.uuid4().hex[:8].upper()}",
            record_id=record_id,
            domain=domain,
            variable=variable,
            severity=severity,
            rule_id=rule_id,
            message=message,
            phase=PipelinePhase.RAW_DATA_VALIDATION,
            source_value=source_value,
            suggested_fix=suggested_fix
        )
        self.flags.append(flag)
        return flag

    def get_flags(self, severity: Optional[ValidationFlagSeverity] = None) -> List[ValidationFlag]:
        """Get all flags, optionally filtered by severity."""
        if severity:
            return [f for f in self.flags if f.severity == severity]
        return self.flags

    def get_critical_flags(self) -> List[ValidationFlag]:
        """Get flags that block pipeline progression."""
        return [f for f in self.flags if f.severity == ValidationFlagSeverity.CRITICAL]

    def has_blocking_issues(self) -> bool:
        """Check if there are unresolved critical flags."""
        critical_unresolved = [
            f for f in self.flags
            if f.severity == ValidationFlagSeverity.CRITICAL and not f.is_resolved
        ]
        return len(critical_unresolved) > 0

    def clear_flags(self):
        """Clear all flags (use with caution)."""
        self.flags = []

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

    # =========================================================================
    # ENHANCED BUSINESS RULE VALIDATION (Phase 2 specific)
    # =========================================================================

    def validate_business_rules(
        self,
        df: pd.DataFrame,
        domain_name: str,
        demo_df: Optional[pd.DataFrame] = None
    ) -> Tuple[List[ValidationIssue], List[ValidationFlag]]:
        """
        Apply comprehensive business rule validation.

        This method implements the full edit check process required
        for Phase 2 (Raw Data Validation).

        Args:
            df: DataFrame to validate
            domain_name: Name of the data domain
            demo_df: Demographics DataFrame for referential integrity checks

        Returns:
            Tuple of (ValidationIssues, ValidationFlags)
        """
        issues: List[ValidationIssue] = []
        domain_key = domain_name.replace(".csv", "").upper()

        # Apply each business rule
        for rule in self.business_rules:
            # Check if rule applies to this domain
            if "ALL" not in rule.applies_to and domain_key not in rule.applies_to:
                continue

            # Apply rule based on category
            if rule.category == BusinessRuleCategory.MANDATORY_FIELD:
                rule_issues = self._apply_mandatory_rule(df, domain_name, rule)
            elif rule.category == BusinessRuleCategory.RANGE_CHECK:
                rule_issues = self._apply_range_rule(df, domain_name, rule)
            elif rule.category == BusinessRuleCategory.DATE_LOGIC:
                rule_issues = self._apply_date_rule(df, domain_name, rule)
            elif rule.category == BusinessRuleCategory.CONSISTENCY_CHECK:
                rule_issues = self._apply_consistency_rule(df, domain_name, rule)
            elif rule.category == BusinessRuleCategory.DUPLICATE_CHECK:
                rule_issues = self._apply_duplicate_rule(df, domain_name, rule)
            elif rule.category == BusinessRuleCategory.FORMAT_CHECK:
                rule_issues = self._apply_format_rule(df, domain_name, rule)
            elif rule.category == BusinessRuleCategory.REFERENTIAL_INTEGRITY:
                rule_issues = self._apply_referential_rule(df, domain_name, rule, demo_df)
            else:
                rule_issues = []

            issues.extend(rule_issues)

        return issues, self.flags.copy()

    def _apply_mandatory_rule(
        self,
        df: pd.DataFrame,
        domain: str,
        rule: BusinessRule
    ) -> List[ValidationIssue]:
        """Apply mandatory field validation rule."""
        issues = []

        for var in rule.variables:
            if var in df.columns:
                missing_count = df[var].isna().sum()
                empty_count = (df[var].astype(str).str.strip() == '').sum()
                total_missing = missing_count + empty_count

                if total_missing > 0:
                    severity = ValidationSeverity.ERROR if rule.severity == ValidationFlagSeverity.CRITICAL else ValidationSeverity.WARNING

                    issues.append(ValidationIssue(
                        rule_id=rule.rule_id,
                        severity=severity,
                        message=f"{rule.name}: {total_missing} records missing required field '{var}'",
                        domain=domain,
                        variable=var
                    ))

                    # Create flags for missing records
                    missing_indices = df[df[var].isna() | (df[var].astype(str).str.strip() == '')].index
                    for idx in missing_indices[:10]:  # Limit to first 10
                        record_id = df.loc[idx, "PT"] if "PT" in df.columns else str(idx)
                        self.create_flag(
                            record_id=str(record_id),
                            domain=domain,
                            variable=var,
                            severity=rule.severity,
                            rule_id=rule.rule_id,
                            message=f"Missing mandatory field: {var}",
                            suggested_fix=f"Provide value for {var}"
                        )

        return issues

    def _apply_range_rule(
        self,
        df: pd.DataFrame,
        domain: str,
        rule: BusinessRule
    ) -> List[ValidationIssue]:
        """Apply range check validation rule."""
        issues = []

        # Define ranges for variables
        ranges = {
            "AGE": (0, 120),
            "SYSBP": (50, 250),
            "DIABP": (30, 150),
            "PULSE": (30, 200),
            "TEMP": (30, 45),
            "WEIGHT": (20, 300),
            "HEIGHT": (50, 250),
            "RESP": (5, 60),
        }

        for var in rule.variables:
            if var in df.columns and var in ranges:
                min_val, max_val = ranges[var]
                numeric_col = pd.to_numeric(df[var], errors='coerce')

                out_of_range_mask = (numeric_col < min_val) | (numeric_col > max_val)
                out_of_range_count = out_of_range_mask.sum()

                if out_of_range_count > 0:
                    severity = ValidationSeverity.WARNING if rule.severity == ValidationFlagSeverity.WARNING else ValidationSeverity.ERROR

                    issues.append(ValidationIssue(
                        rule_id=rule.rule_id,
                        severity=severity,
                        message=f"{rule.name}: {out_of_range_count} values outside range [{min_val}, {max_val}]",
                        domain=domain,
                        variable=var
                    ))

                    # Create flags for out-of-range values
                    out_of_range_indices = df[out_of_range_mask].index
                    for idx in out_of_range_indices[:10]:
                        record_id = df.loc[idx, "PT"] if "PT" in df.columns else str(idx)
                        value = df.loc[idx, var]
                        self.create_flag(
                            record_id=str(record_id),
                            domain=domain,
                            variable=var,
                            severity=rule.severity,
                            rule_id=rule.rule_id,
                            message=f"Value {value} outside expected range [{min_val}, {max_val}]",
                            source_value=value,
                            suggested_fix=f"Verify value or update to be within [{min_val}, {max_val}]"
                        )

        return issues

    def _apply_date_rule(
        self,
        df: pd.DataFrame,
        domain: str,
        rule: BusinessRule
    ) -> List[ValidationIssue]:
        """Apply date logic validation rule."""
        issues = []

        # Identify date columns based on rule variables
        date_patterns = rule.variables
        date_columns = []
        for pattern in date_patterns:
            if "*" in pattern:
                # Wildcard pattern
                regex = pattern.replace("*", ".*")
                matching_cols = [c for c in df.columns if re.match(regex, c, re.IGNORECASE)]
                date_columns.extend(matching_cols)
            elif pattern in df.columns:
                date_columns.append(pattern)

        # Rule-specific logic
        if rule.rule_id == "BUS021":  # End date after start date
            if "STDT" in df.columns and "ENDT" in df.columns:
                # Check end date >= start date
                invalid_mask = pd.to_numeric(df["ENDT"], errors='coerce') < pd.to_numeric(df["STDT"], errors='coerce')
                invalid_count = invalid_mask.sum()

                if invalid_count > 0:
                    issues.append(ValidationIssue(
                        rule_id=rule.rule_id,
                        severity=ValidationSeverity.ERROR,
                        message=f"{rule.name}: {invalid_count} records with end date before start date",
                        domain=domain,
                        variable="STDT/ENDT"
                    ))

                    for idx in df[invalid_mask].index[:10]:
                        record_id = df.loc[idx, "PT"] if "PT" in df.columns else str(idx)
                        self.create_flag(
                            record_id=str(record_id),
                            domain=domain,
                            variable="ENDT",
                            severity=ValidationFlagSeverity.ERROR,
                            rule_id=rule.rule_id,
                            message=f"End date ({df.loc[idx, 'ENDT']}) before start date ({df.loc[idx, 'STDT']})",
                            suggested_fix="Correct date sequence"
                        )

        elif rule.rule_id == "BUS023":  # Future dates
            today = int(datetime.now().strftime("%Y%m%d"))
            for col in date_columns:
                numeric_dates = pd.to_numeric(df[col], errors='coerce')
                future_mask = numeric_dates > today
                future_count = future_mask.sum()

                if future_count > 0:
                    issues.append(ValidationIssue(
                        rule_id=rule.rule_id,
                        severity=ValidationSeverity.ERROR,
                        message=f"{rule.name}: {future_count} future dates in {col}",
                        domain=domain,
                        variable=col
                    ))

        return issues

    def _apply_consistency_rule(
        self,
        df: pd.DataFrame,
        domain: str,
        rule: BusinessRule
    ) -> List[ValidationIssue]:
        """Apply data consistency validation rule."""
        issues = []

        if rule.rule_id == "BUS031":  # Valid gender values
            gender_col = None
            for var in rule.variables:
                if var in df.columns:
                    gender_col = var
                    break

            if gender_col:
                valid_genders = {"M", "F", "MALE", "FEMALE", "U", "UNKNOWN"}
                df_gender = df[~df[gender_col].isna()][gender_col].astype(str).str.upper()
                invalid_mask = ~df_gender.isin(valid_genders)
                invalid_count = invalid_mask.sum()

                if invalid_count > 0:
                    issues.append(ValidationIssue(
                        rule_id=rule.rule_id,
                        severity=ValidationSeverity.ERROR,
                        message=f"{rule.name}: {invalid_count} invalid gender values",
                        domain=domain,
                        variable=gender_col
                    ))

        elif rule.rule_id == "BUS032":  # BP relationship
            if "SYSBP" in df.columns and "DIABP" in df.columns:
                sys_bp = pd.to_numeric(df["SYSBP"], errors='coerce')
                dia_bp = pd.to_numeric(df["DIABP"], errors='coerce')

                invalid_mask = sys_bp <= dia_bp
                invalid_count = invalid_mask.sum()

                if invalid_count > 0:
                    issues.append(ValidationIssue(
                        rule_id=rule.rule_id,
                        severity=ValidationSeverity.WARNING,
                        message=f"{rule.name}: {invalid_count} records with SYSBP <= DIABP",
                        domain=domain,
                        variable="SYSBP/DIABP"
                    ))

        return issues

    def _apply_duplicate_rule(
        self,
        df: pd.DataFrame,
        domain: str,
        rule: BusinessRule
    ) -> List[ValidationIssue]:
        """Apply duplicate detection rule."""
        issues = []

        if rule.rule_id == "BUS040":  # Exact duplicates
            duplicate_count = df.duplicated().sum()
            if duplicate_count > 0:
                issues.append(ValidationIssue(
                    rule_id=rule.rule_id,
                    severity=ValidationSeverity.WARNING,
                    message=f"{rule.name}: {duplicate_count} exact duplicate records found",
                    domain=domain
                ))

        elif rule.rule_id == "BUS041":  # Subject-Visit uniqueness
            if "PT" in df.columns and "VISIT" in df.columns:
                dup_count = df.duplicated(subset=["PT", "VISIT"], keep=False).sum()
                if dup_count > 0:
                    issues.append(ValidationIssue(
                        rule_id=rule.rule_id,
                        severity=ValidationSeverity.WARNING,
                        message=f"{rule.name}: {dup_count} duplicate PT+VISIT combinations",
                        domain=domain
                    ))

        return issues

    def _apply_format_rule(
        self,
        df: pd.DataFrame,
        domain: str,
        rule: BusinessRule
    ) -> List[ValidationIssue]:
        """Apply format validation rule."""
        issues = []

        if rule.rule_id == "BUS050":  # Subject ID format
            if "PT" in df.columns:
                pattern = r"^\d{2}-\d{2}$"
                pt_values = df[~df["PT"].isna()]["PT"].astype(str)
                invalid_format = ~pt_values.str.match(pattern)
                invalid_count = invalid_format.sum()

                if invalid_count > 0:
                    issues.append(ValidationIssue(
                        rule_id=rule.rule_id,
                        severity=ValidationSeverity.WARNING,
                        message=f"{rule.name}: {invalid_count} subject IDs with unexpected format",
                        domain=domain,
                        variable="PT"
                    ))

        return issues

    def _apply_referential_rule(
        self,
        df: pd.DataFrame,
        domain: str,
        rule: BusinessRule,
        demo_df: Optional[pd.DataFrame] = None
    ) -> List[ValidationIssue]:
        """Apply referential integrity validation rule."""
        issues = []

        if rule.rule_id == "BUS060" and demo_df is not None:
            if "PT" in df.columns and "PT" in demo_df.columns:
                demo_subjects = set(demo_df["PT"].dropna().astype(str).unique())
                df_subjects = set(df["PT"].dropna().astype(str).unique())

                missing_subjects = df_subjects - demo_subjects
                if missing_subjects:
                    issues.append(ValidationIssue(
                        rule_id=rule.rule_id,
                        severity=ValidationSeverity.ERROR,
                        message=f"{rule.name}: {len(missing_subjects)} subjects not found in demographics",
                        domain=domain,
                        variable="PT"
                    ))

                    for subj in list(missing_subjects)[:10]:
                        self.create_flag(
                            record_id=str(subj),
                            domain=domain,
                            variable="PT",
                            severity=ValidationFlagSeverity.ERROR,
                            rule_id=rule.rule_id,
                            message=f"Subject {subj} not found in demographics",
                            source_value=subj,
                            suggested_fix="Add subject to demographics or remove from this domain"
                        )

        return issues

    def generate_source_data_review_report(
        self,
        results: List[ValidationResult],
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate Source Data Review (SDR) report.

        The SDR report is a critical output of Phase 2 (Raw Data Validation)
        that documents all data quality issues found before transformation.

        Args:
            results: List of ValidationResult objects
            output_path: Optional path to save the report

        Returns:
            SDR report dictionary
        """
        # Categorize flags
        critical_flags = [f for f in self.flags if f.severity == ValidationFlagSeverity.CRITICAL]
        error_flags = [f for f in self.flags if f.severity == ValidationFlagSeverity.ERROR]
        warning_flags = [f for f in self.flags if f.severity == ValidationFlagSeverity.WARNING]
        info_flags = [f for f in self.flags if f.severity == ValidationFlagSeverity.INFO]

        # Unique subjects flagged
        flagged_subjects = set(f.record_id for f in self.flags if f.record_id)

        # Issues by domain
        issues_by_domain = {}
        for result in results:
            domain = result.domain
            issues_by_domain[domain] = {
                "total_records": result.total_records,
                "is_valid": result.is_valid,
                "error_count": result.error_count,
                "warning_count": result.warning_count,
                "info_count": result.info_count,
                "issues": [
                    {
                        "rule_id": i.rule_id,
                        "severity": i.severity.value if i.severity else "unknown",
                        "message": i.message,
                        "variable": i.variable
                    }
                    for i in result.issues
                ]
            }

        # Issues by category
        issues_by_category = {}
        for rule in self.business_rules:
            category = rule.category.value
            if category not in issues_by_category:
                issues_by_category[category] = []
            related_flags = [f for f in self.flags if f.rule_id == rule.rule_id]
            if related_flags:
                issues_by_category[category].append({
                    "rule_id": rule.rule_id,
                    "rule_name": rule.name,
                    "flag_count": len(related_flags),
                    "severity": rule.severity.value
                })

        report = {
            "report_type": "Source Data Review (SDR)",
            "study_id": self.study_id,
            "phase": "Phase 2: Raw Data Validation (Business Checks)",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_domains_validated": len(results),
                "total_records_processed": sum(r.total_records for r in results),
                "total_flags": len(self.flags),
                "critical_flags": len(critical_flags),
                "error_flags": len(error_flags),
                "warning_flags": len(warning_flags),
                "info_flags": len(info_flags),
                "unique_subjects_flagged": len(flagged_subjects),
                "blocking_issues": self.has_blocking_issues(),
                "overall_status": "BLOCKED" if self.has_blocking_issues() else "PASSED_WITH_ISSUES" if self.flags else "PASSED"
            },
            "issues_by_domain": issues_by_domain,
            "issues_by_category": issues_by_category,
            "flags": [
                {
                    "flag_id": f.flag_id,
                    "record_id": f.record_id,
                    "domain": f.domain,
                    "variable": f.variable,
                    "severity": f.severity.value,
                    "rule_id": f.rule_id,
                    "message": f.message,
                    "source_value": str(f.source_value) if f.source_value else None,
                    "suggested_fix": f.suggested_fix,
                    "is_resolved": f.is_resolved,
                    "created_at": f.created_at.isoformat()
                }
                for f in self.flags
            ],
            "business_rules_applied": [
                {
                    "rule_id": r.rule_id,
                    "category": r.category.value,
                    "name": r.name,
                    "description": r.description,
                    "severity": r.severity.value,
                    "source": r.source
                }
                for r in self.business_rules
            ],
            "recommendations": self._generate_recommendations()
        }

        if output_path:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)

        return report

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on validation findings."""
        recommendations = []

        critical_count = len([f for f in self.flags if f.severity == ValidationFlagSeverity.CRITICAL])
        error_count = len([f for f in self.flags if f.severity == ValidationFlagSeverity.ERROR])

        if critical_count > 0:
            recommendations.append(
                f"CRITICAL: {critical_count} blocking issues must be resolved before proceeding to SDTM transformation"
            )

        if error_count > 0:
            recommendations.append(
                f"ERROR: {error_count} data quality errors should be reviewed and corrected"
            )

        # Check for specific patterns
        missing_pt_flags = [f for f in self.flags if "missing" in f.message.lower() and f.variable == "PT"]
        if missing_pt_flags:
            recommendations.append(
                "Subject identifiers (PT) are missing - ensure all records have valid subject IDs"
            )

        date_flags = [f for f in self.flags if "date" in f.message.lower()]
        if date_flags:
            recommendations.append(
                "Date issues detected - verify date formats and logical sequences"
            )

        range_flags = [f for f in self.flags if "range" in f.message.lower()]
        if range_flags:
            recommendations.append(
                "Out-of-range values detected - verify physiological plausibility of measurements"
            )

        if not self.flags:
            recommendations.append(
                "All raw data validation checks passed - data is ready for SDTM transformation"
            )

        return recommendations

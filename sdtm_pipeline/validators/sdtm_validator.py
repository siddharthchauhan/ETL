"""
SDTM Validator
==============
Validates SDTM datasets against CDISC standards and Pinnacle 21 rules.
Enhanced with Tavily (web search) and Pinecone (vector database) for
referencing business rules and CDISC guidelines.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

from ..models.sdtm_models import (
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    ValidationRule,
    SDTM_DOMAINS,
    CONTROLLED_TERMINOLOGY
)

# Import knowledge retriever for enhanced validation
try:
    from ..langgraph_agent.knowledge_tools import get_knowledge_retriever, SDTMKnowledgeRetriever
    KNOWLEDGE_TOOLS_AVAILABLE = True
except ImportError:
    KNOWLEDGE_TOOLS_AVAILABLE = False
    SDTMKnowledgeRetriever = None


class SDTMValidator:
    """
    Validates SDTM datasets against CDISC standards.

    Implements validation checks based on:
    - SDTM Implementation Guide 3.4
    - FDA Business Rules
    - Pinnacle 21 Community validation rules
    """

    def __init__(self, study_id: str = "UNKNOWN", use_knowledge_tools: bool = True):
        self.study_id = study_id
        self.validation_rules: List[ValidationRule] = []
        self._setup_cdisc_rules()
        self._setup_fda_rules()

        # Initialize knowledge retriever for enhanced validation
        self.knowledge_retriever: Optional[SDTMKnowledgeRetriever] = None
        self._kb_rules_cache: Dict[str, List[Dict]] = {}  # Cache retrieved rules by domain

        if use_knowledge_tools and KNOWLEDGE_TOOLS_AVAILABLE:
            try:
                self.knowledge_retriever = get_knowledge_retriever()
                print("  Knowledge tools (Tavily/Pinecone) enabled for validation")
            except Exception as e:
                print(f"  WARNING: Knowledge tools initialization failed: {e}")
                self.knowledge_retriever = None

    def _setup_cdisc_rules(self):
        """Setup CDISC SDTM validation rules."""
        cdisc_rules = [
            # Identifier Rules
            ValidationRule(
                rule_id="SD0001",
                rule_type="CDISC",
                description="STUDYID must be populated",
                severity=ValidationSeverity.ERROR,
                check_expression="STUDYID is not null",
                variable="STUDYID"
            ),
            ValidationRule(
                rule_id="SD0002",
                rule_type="CDISC",
                description="DOMAIN must match the two-character domain code",
                severity=ValidationSeverity.ERROR,
                check_expression="DOMAIN matches expected",
                variable="DOMAIN"
            ),
            ValidationRule(
                rule_id="SD0003",
                rule_type="CDISC",
                description="USUBJID must be unique subject identifier",
                severity=ValidationSeverity.ERROR,
                check_expression="USUBJID is not null",
                variable="USUBJID"
            ),
            # Sequence Rules
            ValidationRule(
                rule_id="SD0010",
                rule_type="CDISC",
                description="--SEQ must be unique within USUBJID",
                severity=ValidationSeverity.ERROR,
                check_expression="SEQ unique within USUBJID"
            ),
            # Controlled Terminology
            ValidationRule(
                rule_id="SD0020",
                rule_type="CDISC",
                description="SEX must use CDISC controlled terminology",
                severity=ValidationSeverity.ERROR,
                check_expression="SEX in CT",
                domain="DM",
                variable="SEX"
            ),
            ValidationRule(
                rule_id="SD0021",
                rule_type="CDISC",
                description="RACE must use CDISC controlled terminology",
                severity=ValidationSeverity.WARNING,
                check_expression="RACE in CT",
                domain="DM",
                variable="RACE"
            ),
            ValidationRule(
                rule_id="SD0022",
                rule_type="CDISC",
                description="ETHNIC must use CDISC controlled terminology",
                severity=ValidationSeverity.WARNING,
                check_expression="ETHNIC in CT",
                domain="DM",
                variable="ETHNIC"
            ),
            # Date Rules
            ValidationRule(
                rule_id="SD0030",
                rule_type="CDISC",
                description="Date variables must be in ISO 8601 format",
                severity=ValidationSeverity.ERROR,
                check_expression="Date is ISO 8601"
            ),
            ValidationRule(
                rule_id="SD0031",
                rule_type="CDISC",
                description="Start date must not be after end date",
                severity=ValidationSeverity.ERROR,
                check_expression="STDTC <= ENDTC"
            ),
        ]
        self.validation_rules.extend(cdisc_rules)

    def _setup_fda_rules(self):
        """Setup FDA business rules."""
        fda_rules = [
            ValidationRule(
                rule_id="FDA0001",
                rule_type="FDA",
                description="USUBJID format should follow sponsor conventions",
                severity=ValidationSeverity.WARNING,
                check_expression="USUBJID format",
                variable="USUBJID"
            ),
            ValidationRule(
                rule_id="FDA0010",
                rule_type="FDA",
                description="AE records should have AEDECOD populated",
                severity=ValidationSeverity.WARNING,
                check_expression="AEDECOD is not null",
                domain="AE",
                variable="AEDECOD"
            ),
            ValidationRule(
                rule_id="FDA0011",
                rule_type="FDA",
                description="Serious AE indicators should be consistent",
                severity=ValidationSeverity.ERROR,
                check_expression="SAE consistency",
                domain="AE"
            ),
            ValidationRule(
                rule_id="FDA0020",
                rule_type="FDA",
                description="Lab results should have standard units",
                severity=ValidationSeverity.WARNING,
                check_expression="LBSTRESU populated",
                domain="LB",
                variable="LBSTRESU"
            ),
        ]
        self.validation_rules.extend(fda_rules)

    def validate_domain(self, df: pd.DataFrame, domain_code: str) -> ValidationResult:
        """
        Validate an SDTM domain dataset.

        Args:
            df: DataFrame containing SDTM domain data
            domain_code: Two-letter domain code (e.g., DM, AE, VS)

        Returns:
            ValidationResult with all identified issues
        """
        issues: List[ValidationIssue] = []

        if df.empty:
            issues.append(ValidationIssue(
                rule_id="SD0000",
                severity=ValidationSeverity.ERROR,
                message="Dataset is empty",
                domain=domain_code
            ))
            return ValidationResult(
                is_valid=False,
                domain=domain_code,
                total_records=0,
                issues=issues
            )

        # Get domain specification
        domain_spec = SDTM_DOMAINS.get(domain_code)

        # Run structural validation
        issues.extend(self._validate_required_variables(df, domain_code, domain_spec))
        issues.extend(self._validate_identifiers(df, domain_code))
        issues.extend(self._validate_sequence(df, domain_code))
        issues.extend(self._validate_controlled_terminology(df, domain_code))
        issues.extend(self._validate_dates(df, domain_code))

        # Run knowledge-based validation (from Pinecone/Tavily)
        issues.extend(self._validate_with_knowledge_base(df, domain_code))

        # Run domain-specific validation
        domain_validators = {
            "DM": self._validate_dm_domain,
            "AE": self._validate_ae_domain,
            "VS": self._validate_vs_domain,
            "LB": self._validate_lb_domain,
            "CM": self._validate_cm_domain,
            "EX": self._validate_ex_domain,
            "DS": self._validate_ds_domain,
            "MH": self._validate_mh_domain,
            "EG": self._validate_eg_domain,
            "PE": self._validate_pe_domain,
            "PC": self._validate_pc_domain,
            "IE": self._validate_ie_domain,
            "QS": self._validate_qs_domain,
            "RS": self._validate_rs_domain,
            "TR": self._validate_tr_domain,
            "TU": self._validate_tu_domain,
            "CO": self._validate_co_domain,
        }

        validator = domain_validators.get(domain_code)
        if validator:
            issues.extend(validator(df))
        elif domain_code.startswith("SUPP"):
            issues.extend(self._validate_supp_domain(df, domain_code))

        # Determine validity
        error_count = sum(1 for i in issues if i.severity == ValidationSeverity.ERROR)
        is_valid = error_count == 0

        return ValidationResult(
            is_valid=is_valid,
            domain=domain_code,
            total_records=len(df),
            issues=issues
        )

    def _validate_required_variables(
        self, df: pd.DataFrame, domain_code: str, domain_spec
    ) -> List[ValidationIssue]:
        """Validate required variables are present."""
        issues = []

        if domain_spec:
            for var in domain_spec.required_variables:
                if var not in df.columns:
                    issues.append(ValidationIssue(
                        rule_id="SD0001",
                        severity=ValidationSeverity.ERROR,
                        message=f"Required variable '{var}' is missing",
                        domain=domain_code,
                        variable=var
                    ))
                elif df[var].isna().all():
                    issues.append(ValidationIssue(
                        rule_id="SD0001",
                        severity=ValidationSeverity.ERROR,
                        message=f"Required variable '{var}' is completely empty",
                        domain=domain_code,
                        variable=var
                    ))

        return issues

    def _validate_identifiers(self, df: pd.DataFrame, domain_code: str) -> List[ValidationIssue]:
        """Validate identifier variables."""
        issues = []

        # STUDYID
        if "STUDYID" in df.columns:
            null_studyid = df["STUDYID"].isna().sum()
            if null_studyid > 0:
                issues.append(ValidationIssue(
                    rule_id="SD0001",
                    severity=ValidationSeverity.ERROR,
                    message=f"{null_studyid} records have missing STUDYID",
                    domain=domain_code,
                    variable="STUDYID"
                ))

            # Check consistency
            unique_studies = df["STUDYID"].dropna().unique()
            if len(unique_studies) > 1:
                issues.append(ValidationIssue(
                    rule_id="SD0001",
                    severity=ValidationSeverity.ERROR,
                    message=f"Multiple STUDYID values found: {list(unique_studies)}",
                    domain=domain_code,
                    variable="STUDYID"
                ))

        # DOMAIN
        if "DOMAIN" in df.columns:
            incorrect_domain = (df["DOMAIN"] != domain_code).sum()
            if incorrect_domain > 0:
                issues.append(ValidationIssue(
                    rule_id="SD0002",
                    severity=ValidationSeverity.ERROR,
                    message=f"{incorrect_domain} records have incorrect DOMAIN value",
                    domain=domain_code,
                    variable="DOMAIN"
                ))

        # USUBJID
        if "USUBJID" in df.columns:
            null_usubjid = df["USUBJID"].isna().sum()
            if null_usubjid > 0:
                issues.append(ValidationIssue(
                    rule_id="SD0003",
                    severity=ValidationSeverity.ERROR,
                    message=f"{null_usubjid} records have missing USUBJID",
                    domain=domain_code,
                    variable="USUBJID"
                ))

        return issues

    def _validate_sequence(self, df: pd.DataFrame, domain_code: str) -> List[ValidationIssue]:
        """Validate sequence variable."""
        issues = []

        seq_var = f"{domain_code}SEQ"
        if seq_var in df.columns and "USUBJID" in df.columns:
            # Check uniqueness within USUBJID
            duplicates = df.groupby("USUBJID")[seq_var].apply(
                lambda x: x.dropna().duplicated().sum()
            ).sum()

            if duplicates > 0:
                issues.append(ValidationIssue(
                    rule_id="SD0010",
                    severity=ValidationSeverity.ERROR,
                    message=f"{seq_var} is not unique within USUBJID ({duplicates} duplicates)",
                    domain=domain_code,
                    variable=seq_var
                ))

        return issues

    def _validate_controlled_terminology(
        self, df: pd.DataFrame, domain_code: str
    ) -> List[ValidationIssue]:
        """Validate controlled terminology values."""
        issues = []

        ct_checks = {
            "SEX": ("SD0020", CONTROLLED_TERMINOLOGY.get("SEX", [])),
            "RACE": ("SD0021", CONTROLLED_TERMINOLOGY.get("RACE", [])),
            "ETHNIC": ("SD0022", CONTROLLED_TERMINOLOGY.get("ETHNIC", [])),
            "AGEU": ("SD0023", CONTROLLED_TERMINOLOGY.get("AGEU", [])),
            "AESER": ("SD0024", CONTROLLED_TERMINOLOGY.get("AESER", [])),
            "AESEV": ("SD0025", CONTROLLED_TERMINOLOGY.get("AESEV", [])),
            "VSPOS": ("SD0026", CONTROLLED_TERMINOLOGY.get("VSPOS", [])),
            "LBNRIND": ("SD0027", CONTROLLED_TERMINOLOGY.get("LBNRIND", [])),
        }

        for var, (rule_id, valid_values) in ct_checks.items():
            if var in df.columns and valid_values:
                invalid_count = df[~df[var].isna()][var].apply(
                    lambda x: str(x).upper() not in [v.upper() for v in valid_values]
                ).sum()

                if invalid_count > 0:
                    issues.append(ValidationIssue(
                        rule_id=rule_id,
                        severity=ValidationSeverity.WARNING,
                        message=f"{invalid_count} records have invalid {var} values (not in CT)",
                        domain=domain_code,
                        variable=var
                    ))

        return issues

    def _validate_dates(self, df: pd.DataFrame, domain_code: str) -> List[ValidationIssue]:
        """Validate date variables."""
        issues = []

        # Find date columns (ending in DTC)
        date_cols = [col for col in df.columns if col.endswith("DTC")]

        iso_pattern = re.compile(
            r"^\d{4}(-\d{2}(-\d{2}(T\d{2}(:\d{2}(:\d{2})?)?)?)?)?$"
        )

        for col in date_cols:
            invalid_dates = 0
            for value in df[col].dropna():
                str_val = str(value)
                if str_val and not iso_pattern.match(str_val):
                    invalid_dates += 1

            if invalid_dates > 0:
                issues.append(ValidationIssue(
                    rule_id="SD0030",
                    severity=ValidationSeverity.ERROR,
                    message=f"{invalid_dates} records have invalid ISO 8601 dates in {col}",
                    domain=domain_code,
                    variable=col
                ))

        # Check start/end date consistency
        start_end_pairs = [
            ("RFSTDTC", "RFENDTC"),
            ("AESTDTC", "AEENDTC"),
            ("CMSTDTC", "CMENDTC"),
            ("EXSTDTC", "EXENDTC"),
            ("VSDTC", None),
            ("LBDTC", None),
        ]

        for start_col, end_col in start_end_pairs:
            if start_col in df.columns and end_col and end_col in df.columns:
                # Compare dates where both are present
                both_present = df[~df[start_col].isna() & ~df[end_col].isna()]
                if len(both_present) > 0:
                    invalid_range = 0
                    for _, row in both_present.iterrows():
                        try:
                            start = str(row[start_col])[:10]
                            end = str(row[end_col])[:10]
                            if start > end:
                                invalid_range += 1
                        except Exception:
                            pass

                    if invalid_range > 0:
                        issues.append(ValidationIssue(
                            rule_id="SD0031",
                            severity=ValidationSeverity.ERROR,
                            message=f"{invalid_range} records have {start_col} after {end_col}",
                            domain=domain_code,
                            variable=f"{start_col}/{end_col}"
                        ))

        return issues

    def _validate_with_knowledge_base(
        self, df: pd.DataFrame, domain_code: str
    ) -> List[ValidationIssue]:
        """
        Validate dataset against business rules from knowledge base.

        Retrieves FDA, Pinnacle 21, and CDISC rules from Pinecone
        and applies them to flag non-compliant records.
        """
        issues = []

        if not self.knowledge_retriever:
            return issues

        try:
            # Check cache first
            if domain_code not in self._kb_rules_cache:
                rules = self.knowledge_retriever.get_business_rules(domain_code, rule_type="all")
                self._kb_rules_cache[domain_code] = rules
                if rules:
                    print(f"    Retrieved {len(rules)} business rules for {domain_code} from knowledge base")
            else:
                rules = self._kb_rules_cache[domain_code]

            # Apply each rule if it contains actionable check information
            for rule in rules:
                rule_issue = self._apply_knowledge_rule(df, domain_code, rule)
                if rule_issue:
                    issues.append(rule_issue)

        except Exception as e:
            # Log but don't fail validation if knowledge retrieval fails
            print(f"    Knowledge-based validation warning for {domain_code}: {e}")

        return issues

    def _apply_knowledge_rule(
        self, df: pd.DataFrame, domain_code: str, rule: Dict[str, Any]
    ) -> Optional[ValidationIssue]:
        """
        Apply a single knowledge-based rule to the dataset.

        Parses rule content and attempts to validate against it.
        """
        if not rule:
            return None

        # Extract rule information
        rule_id = rule.get("rule_id", rule.get("id", "KB001"))
        rule_desc = rule.get("description", rule.get("content", ""))
        rule_check = rule.get("check", rule.get("expression", ""))
        rule_var = rule.get("variable", "")

        # Only apply rules with clear variable targets
        if rule_var and rule_var in df.columns:
            # Check for null values if rule mentions "required" or "must be populated"
            if any(kw in rule_desc.lower() for kw in ["required", "must be populated", "cannot be null", "not null"]):
                null_count = df[rule_var].isna().sum()
                if null_count > 0:
                    return ValidationIssue(
                        rule_id=f"KB-{rule_id}",
                        severity=ValidationSeverity.WARNING,
                        message=f"[KB Rule] {null_count} records violate: {rule_desc[:100]}",
                        domain=domain_code,
                        variable=rule_var
                    )

            # Check for controlled terminology if rule mentions "CT" or "terminology"
            if any(kw in rule_desc.lower() for kw in ["controlled terminology", "ct values", "codelist"]):
                ct_values = self._get_ct_from_rule(rule)
                if ct_values:
                    invalid_count = df[~df[rule_var].isna()][rule_var].apply(
                        lambda x: str(x).upper() not in [v.upper() for v in ct_values]
                    ).sum()
                    if invalid_count > 0:
                        return ValidationIssue(
                            rule_id=f"KB-{rule_id}",
                            severity=ValidationSeverity.WARNING,
                            message=f"[KB Rule] {invalid_count} records have invalid {rule_var} per CT",
                            domain=domain_code,
                            variable=rule_var
                        )

        return None

    def _get_ct_from_rule(self, rule: Dict[str, Any]) -> Optional[List[str]]:
        """Extract controlled terminology values from a rule."""
        # Try to get CT values from the rule
        ct_values = rule.get("ct_values", rule.get("valid_values", []))
        if ct_values:
            return ct_values

        # Try to get from knowledge base
        codelist = rule.get("codelist", rule.get("ct_name", ""))
        if codelist and self.knowledge_retriever:
            try:
                return self.knowledge_retriever.get_controlled_terminology(codelist)
            except Exception:
                pass

        return None

    def _validate_dm_domain(self, df: pd.DataFrame) -> List[ValidationIssue]:
        """Domain-specific validation for Demographics."""
        issues = []

        # Check AGE calculation
        if "AGE" in df.columns:
            invalid_age = ((df["AGE"] < 0) | (df["AGE"] > 120)).sum()
            if invalid_age > 0:
                issues.append(ValidationIssue(
                    rule_id="DM0001",
                    severity=ValidationSeverity.WARNING,
                    message=f"{invalid_age} records have unusual AGE values",
                    domain="DM",
                    variable="AGE"
                ))

        # Check one record per subject
        if "USUBJID" in df.columns:
            dup_subjects = df["USUBJID"].duplicated().sum()
            if dup_subjects > 0:
                issues.append(ValidationIssue(
                    rule_id="DM0002",
                    severity=ValidationSeverity.ERROR,
                    message=f"DM should have one record per subject, found {dup_subjects} duplicates",
                    domain="DM",
                    variable="USUBJID"
                ))

        return issues

    def _validate_ae_domain(self, df: pd.DataFrame) -> List[ValidationIssue]:
        """Domain-specific validation for Adverse Events."""
        issues = []

        # Check AETERM is populated
        if "AETERM" in df.columns:
            null_aeterm = df["AETERM"].isna().sum()
            if null_aeterm > 0:
                issues.append(ValidationIssue(
                    rule_id="AE0001",
                    severity=ValidationSeverity.ERROR,
                    message=f"{null_aeterm} records have missing AETERM",
                    domain="AE",
                    variable="AETERM"
                ))

        # Check serious AE consistency
        sae_vars = ["AESCONG", "AESDISAB", "AESDTH", "AESHOSP", "AESLIFE", "AESMIE"]
        present_sae_vars = [v for v in sae_vars if v in df.columns]

        if "AESER" in df.columns and present_sae_vars:
            # If AESER=Y, at least one criterion should be Y
            serious_aes = df[df["AESER"] == "Y"]
            if len(serious_aes) > 0:
                no_criteria = 0
                for _, row in serious_aes.iterrows():
                    if not any(row.get(v) == "Y" for v in present_sae_vars):
                        no_criteria += 1

                if no_criteria > 0:
                    issues.append(ValidationIssue(
                        rule_id="FDA0011",
                        severity=ValidationSeverity.WARNING,
                        message=f"{no_criteria} serious AEs have no seriousness criteria flagged",
                        domain="AE",
                        variable="AESER"
                    ))

        return issues

    def _validate_vs_domain(self, df: pd.DataFrame) -> List[ValidationIssue]:
        """Domain-specific validation for Vital Signs."""
        issues = []

        # Check VSTESTCD is populated
        if "VSTESTCD" in df.columns:
            null_testcd = df["VSTESTCD"].isna().sum()
            if null_testcd > 0:
                issues.append(ValidationIssue(
                    rule_id="VS0001",
                    severity=ValidationSeverity.ERROR,
                    message=f"{null_testcd} records have missing VSTESTCD",
                    domain="VS",
                    variable="VSTESTCD"
                ))

        # Check VSORRES and VSSTRESC consistency
        if "VSORRES" in df.columns and "VSSTRESC" in df.columns:
            orres_populated = df["VSORRES"].notna().sum()
            stresc_populated = df["VSSTRESC"].notna().sum()

            if orres_populated > 0 and stresc_populated == 0:
                issues.append(ValidationIssue(
                    rule_id="VS0002",
                    severity=ValidationSeverity.WARNING,
                    message="VSORRES populated but VSSTRESC is empty",
                    domain="VS",
                    variable="VSSTRESC"
                ))

        return issues

    def _validate_lb_domain(self, df: pd.DataFrame) -> List[ValidationIssue]:
        """Domain-specific validation for Laboratory."""
        issues = []

        # Check LBTESTCD is populated
        if "LBTESTCD" in df.columns:
            null_testcd = df["LBTESTCD"].isna().sum()
            if null_testcd > 0:
                issues.append(ValidationIssue(
                    rule_id="LB0001",
                    severity=ValidationSeverity.ERROR,
                    message=f"{null_testcd} records have missing LBTESTCD",
                    domain="LB",
                    variable="LBTESTCD"
                ))

        # Check reference ranges
        if all(col in df.columns for col in ["LBSTRESN", "LBSTNRLO", "LBSTNRHI"]):
            # Check LBNRIND consistency
            if "LBNRIND" in df.columns:
                numeric_results = df[df["LBSTRESN"].notna() & df["LBSTNRLO"].notna()]
                inconsistent = 0
                for _, row in numeric_results.iterrows():
                    try:
                        result = float(row["LBSTRESN"])
                        low = float(row["LBSTNRLO"])
                        high = float(row["LBSTNRHI"]) if pd.notna(row.get("LBSTNRHI")) else float('inf')
                        nrind = str(row.get("LBNRIND", "")).upper()

                        if result < low and "LOW" not in nrind:
                            inconsistent += 1
                        elif result > high and "HIGH" not in nrind:
                            inconsistent += 1
                    except (ValueError, TypeError):
                        pass

                if inconsistent > 0:
                    issues.append(ValidationIssue(
                        rule_id="LB0002",
                        severity=ValidationSeverity.WARNING,
                        message=f"{inconsistent} records have inconsistent LBNRIND",
                        domain="LB",
                        variable="LBNRIND"
                    ))

        return issues

    def _validate_cm_domain(self, df: pd.DataFrame) -> List[ValidationIssue]:
        """Domain-specific validation for Concomitant Medications."""
        issues = []

        # Check CMTRT is populated
        if "CMTRT" in df.columns:
            null_cmtrt = df["CMTRT"].isna().sum()
            if null_cmtrt > 0:
                issues.append(ValidationIssue(
                    rule_id="CM0001",
                    severity=ValidationSeverity.ERROR,
                    message=f"{null_cmtrt} records have missing CMTRT",
                    domain="CM",
                    variable="CMTRT"
                ))

        return issues

    def _validate_ex_domain(self, df: pd.DataFrame) -> List[ValidationIssue]:
        """Domain-specific validation for Exposure."""
        issues = []

        if "EXTRT" in df.columns:
            null_extrt = df["EXTRT"].isna().sum()
            if null_extrt > 0:
                issues.append(ValidationIssue(
                    rule_id="EX0001",
                    severity=ValidationSeverity.ERROR,
                    message=f"{null_extrt} records have missing EXTRT",
                    domain="EX",
                    variable="EXTRT"
                ))

        return issues

    def _validate_ds_domain(self, df: pd.DataFrame) -> List[ValidationIssue]:
        """Domain-specific validation for Disposition."""
        issues = []

        if "DSTERM" in df.columns:
            null_dsterm = df["DSTERM"].isna().sum()
            if null_dsterm > 0:
                issues.append(ValidationIssue(
                    rule_id="DS0001",
                    severity=ValidationSeverity.ERROR,
                    message=f"{null_dsterm} records have missing DSTERM",
                    domain="DS",
                    variable="DSTERM"
                ))

        return issues

    def _validate_mh_domain(self, df: pd.DataFrame) -> List[ValidationIssue]:
        """Domain-specific validation for Medical History."""
        issues = []

        if "MHTERM" in df.columns:
            null_mhterm = df["MHTERM"].isna().sum()
            if null_mhterm > 0:
                issues.append(ValidationIssue(
                    rule_id="MH0001",
                    severity=ValidationSeverity.ERROR,
                    message=f"{null_mhterm} records have missing MHTERM",
                    domain="MH",
                    variable="MHTERM"
                ))

        return issues

    def _validate_eg_domain(self, df: pd.DataFrame) -> List[ValidationIssue]:
        """Domain-specific validation for ECG."""
        issues = []

        if "EGTESTCD" in df.columns:
            null_testcd = df["EGTESTCD"].isna().sum()
            if null_testcd > 0:
                issues.append(ValidationIssue(
                    rule_id="EG0001",
                    severity=ValidationSeverity.ERROR,
                    message=f"{null_testcd} records have missing EGTESTCD",
                    domain="EG",
                    variable="EGTESTCD"
                ))

        return issues

    def _validate_pe_domain(self, df: pd.DataFrame) -> List[ValidationIssue]:
        """Domain-specific validation for Physical Examination."""
        issues = []

        if "PETESTCD" in df.columns:
            null_testcd = df["PETESTCD"].isna().sum()
            if null_testcd > 0:
                issues.append(ValidationIssue(
                    rule_id="PE0001",
                    severity=ValidationSeverity.ERROR,
                    message=f"{null_testcd} records have missing PETESTCD",
                    domain="PE",
                    variable="PETESTCD"
                ))

        return issues

    def _validate_pc_domain(self, df: pd.DataFrame) -> List[ValidationIssue]:
        """Domain-specific validation for Pharmacokinetics Concentrations."""
        issues = []

        if "PCTESTCD" in df.columns:
            null_testcd = df["PCTESTCD"].isna().sum()
            if null_testcd > 0:
                issues.append(ValidationIssue(
                    rule_id="PC0001",
                    severity=ValidationSeverity.ERROR,
                    message=f"{null_testcd} records have missing PCTESTCD",
                    domain="PC",
                    variable="PCTESTCD"
                ))

        return issues

    def _validate_ie_domain(self, df: pd.DataFrame) -> List[ValidationIssue]:
        """Domain-specific validation for Inclusion/Exclusion."""
        issues = []

        if "IETEST" in df.columns:
            null_test = df["IETEST"].isna().sum()
            if null_test > 0:
                issues.append(ValidationIssue(
                    rule_id="IE0001",
                    severity=ValidationSeverity.ERROR,
                    message=f"{null_test} records have missing IETEST",
                    domain="IE",
                    variable="IETEST"
                ))

        if "IECAT" in df.columns:
            valid_cats = ["INCLUSION", "EXCLUSION"]
            invalid_cat = df[~df["IECAT"].isna()]["IECAT"].apply(
                lambda x: str(x).upper() not in valid_cats
            ).sum()
            if invalid_cat > 0:
                issues.append(ValidationIssue(
                    rule_id="IE0002",
                    severity=ValidationSeverity.WARNING,
                    message=f"{invalid_cat} records have invalid IECAT (should be INCLUSION or EXCLUSION)",
                    domain="IE",
                    variable="IECAT"
                ))

        return issues

    def _validate_qs_domain(self, df: pd.DataFrame) -> List[ValidationIssue]:
        """Domain-specific validation for Questionnaires."""
        issues = []

        if "QSTESTCD" in df.columns:
            null_testcd = df["QSTESTCD"].isna().sum()
            if null_testcd > 0:
                issues.append(ValidationIssue(
                    rule_id="QS0001",
                    severity=ValidationSeverity.ERROR,
                    message=f"{null_testcd} records have missing QSTESTCD",
                    domain="QS",
                    variable="QSTESTCD"
                ))

        if "QSCAT" in df.columns:
            null_cat = df["QSCAT"].isna().sum()
            if null_cat > 0:
                issues.append(ValidationIssue(
                    rule_id="QS0002",
                    severity=ValidationSeverity.WARNING,
                    message=f"{null_cat} records have missing QSCAT (questionnaire name)",
                    domain="QS",
                    variable="QSCAT"
                ))

        return issues

    def _validate_rs_domain(self, df: pd.DataFrame) -> List[ValidationIssue]:
        """Domain-specific validation for Disease Response."""
        issues = []

        if "RSTESTCD" in df.columns:
            null_testcd = df["RSTESTCD"].isna().sum()
            if null_testcd > 0:
                issues.append(ValidationIssue(
                    rule_id="RS0001",
                    severity=ValidationSeverity.ERROR,
                    message=f"{null_testcd} records have missing RSTESTCD",
                    domain="RS",
                    variable="RSTESTCD"
                ))

        return issues

    def _validate_tr_domain(self, df: pd.DataFrame) -> List[ValidationIssue]:
        """Domain-specific validation for Tumor Results."""
        issues = []

        if "TRTESTCD" in df.columns:
            null_testcd = df["TRTESTCD"].isna().sum()
            if null_testcd > 0:
                issues.append(ValidationIssue(
                    rule_id="TR0001",
                    severity=ValidationSeverity.ERROR,
                    message=f"{null_testcd} records have missing TRTESTCD",
                    domain="TR",
                    variable="TRTESTCD"
                ))

        if "TRLNKID" in df.columns:
            null_lnkid = df["TRLNKID"].isna().sum()
            if null_lnkid > 0:
                issues.append(ValidationIssue(
                    rule_id="TR0002",
                    severity=ValidationSeverity.WARNING,
                    message=f"{null_lnkid} records have missing TRLNKID (link to TU)",
                    domain="TR",
                    variable="TRLNKID"
                ))

        return issues

    def _validate_tu_domain(self, df: pd.DataFrame) -> List[ValidationIssue]:
        """Domain-specific validation for Tumor Identification."""
        issues = []

        if "TUTESTCD" in df.columns:
            null_testcd = df["TUTESTCD"].isna().sum()
            if null_testcd > 0:
                issues.append(ValidationIssue(
                    rule_id="TU0001",
                    severity=ValidationSeverity.ERROR,
                    message=f"{null_testcd} records have missing TUTESTCD",
                    domain="TU",
                    variable="TUTESTCD"
                ))

        if "TULNKID" in df.columns:
            null_lnkid = df["TULNKID"].isna().sum()
            if null_lnkid > 0:
                issues.append(ValidationIssue(
                    rule_id="TU0002",
                    severity=ValidationSeverity.WARNING,
                    message=f"{null_lnkid} records have missing TULNKID",
                    domain="TU",
                    variable="TULNKID"
                ))

        return issues

    def _validate_co_domain(self, df: pd.DataFrame) -> List[ValidationIssue]:
        """Domain-specific validation for Comments."""
        issues = []

        if "COVAL" in df.columns:
            null_coval = df["COVAL"].isna().sum()
            if null_coval > 0:
                issues.append(ValidationIssue(
                    rule_id="CO0001",
                    severity=ValidationSeverity.ERROR,
                    message=f"{null_coval} records have missing COVAL",
                    domain="CO",
                    variable="COVAL"
                ))

        return issues

    def _validate_supp_domain(self, df: pd.DataFrame, domain_code: str) -> List[ValidationIssue]:
        """Validate supplemental qualifier domains."""
        issues = []

        # SUPP domains require RDOMAIN, QNAM, QVAL
        for var in ["RDOMAIN", "QNAM", "QVAL"]:
            if var in df.columns:
                null_count = df[var].isna().sum()
                if null_count > 0:
                    issues.append(ValidationIssue(
                        rule_id=f"SUPP0001",
                        severity=ValidationSeverity.ERROR,
                        message=f"{null_count} records have missing {var}",
                        domain=domain_code,
                        variable=var
                    ))

        return issues

    def generate_report(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        total_errors = sum(r.error_count for r in results)
        total_warnings = sum(r.warning_count for r in results)
        total_records = sum(r.total_records for r in results)

        submission_ready = all(r.is_valid for r in results)

        # Count knowledge-based issues
        kb_issues = sum(
            1 for r in results
            for i in r.issues
            if i.rule_id.startswith("KB-")
        )

        return {
            "study_id": self.study_id,
            "submission_ready": submission_ready,
            "summary": {
                "domains_validated": len(results),
                "total_records": total_records,
                "total_errors": total_errors,
                "total_warnings": total_warnings,
                "knowledge_based_issues": kb_issues
            },
            "knowledge_tools": {
                "enabled": self.knowledge_retriever is not None,
                "rules_retrieved": sum(len(r) for r in self._kb_rules_cache.values()),
                "domains_with_kb_rules": list(self._kb_rules_cache.keys())
            },
            "by_domain": {r.domain: r.to_dict() for r in results},
            "rules_applied": len(self.validation_rules),
            "generated_at": datetime.now().isoformat()
        }

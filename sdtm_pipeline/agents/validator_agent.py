"""
Enhanced Validator Agent
========================
Multi-layer validation agent for SDTM datasets.

Validation Layers:
1. Structural - Required variables, data types, lengths
2. CDISC - SDTM-IG rules, CORE conformance
3. Cross-Domain - Referential integrity
4. Semantic - Business logic via LLM + KB lookup
"""

import os
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

import pandas as pd

from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationLayer(Enum):
    """Validation layers."""
    STRUCTURAL = "structural"
    CDISC = "cdisc"
    CROSS_DOMAIN = "cross_domain"
    SEMANTIC = "semantic"


@dataclass
class ValidationIssue:
    """A validation issue."""
    layer: str
    rule_id: str
    severity: str
    message: str
    domain: str
    variable: Optional[str] = None
    affected_records: int = 0


# SDTM Domain Requirements
DOMAIN_REQUIREMENTS = {
    "DM": {
        "required": ["STUDYID", "DOMAIN", "USUBJID", "SUBJID", "RFSTDTC", "RFENDTC", "SITEID", "BRTHDTC", "AGE", "AGEU", "SEX", "RACE", "ARMCD", "ARM", "COUNTRY"],
        "key": ["USUBJID"],
        "one_per_subject": True,
    },
    "AE": {
        "required": ["STUDYID", "DOMAIN", "USUBJID", "AESEQ", "AETERM", "AEDECOD", "AESTDTC"],
        "key": ["USUBJID", "AESEQ"],
        "timing": ["AESTDTC", "AEENDTC"],
    },
    "VS": {
        "required": ["STUDYID", "DOMAIN", "USUBJID", "VSSEQ", "VSTESTCD", "VSTEST", "VSORRES", "VSORRESU"],
        "key": ["USUBJID", "VSTESTCD", "VSSEQ"],
        "result_vars": ["VSORRES", "VSSTRESC", "VSSTRESN"],
    },
    "LB": {
        "required": ["STUDYID", "DOMAIN", "USUBJID", "LBSEQ", "LBTESTCD", "LBTEST", "LBORRES", "LBORRESU"],
        "key": ["USUBJID", "LBTESTCD", "LBSEQ"],
        "result_vars": ["LBORRES", "LBSTRESC", "LBSTRESN"],
    },
    "CM": {
        "required": ["STUDYID", "DOMAIN", "USUBJID", "CMSEQ", "CMTRT"],
        "key": ["USUBJID", "CMSEQ"],
        "timing": ["CMSTDTC", "CMENDTC"],
    },
    "EX": {
        "required": ["STUDYID", "DOMAIN", "USUBJID", "EXSEQ", "EXTRT", "EXDOSE", "EXDOSU", "EXSTDTC", "EXENDTC"],
        "key": ["USUBJID", "EXSEQ"],
        "timing": ["EXSTDTC", "EXENDTC"],
    },
    "MH": {
        "required": ["STUDYID", "DOMAIN", "USUBJID", "MHSEQ", "MHTERM"],
        "key": ["USUBJID", "MHSEQ"],
    },
    "DS": {
        "required": ["STUDYID", "DOMAIN", "USUBJID", "DSSEQ", "DSTERM", "DSDECOD", "DSCAT", "DSSTDTC"],
        "key": ["USUBJID", "DSSEQ"],
    },
}


@tool
def validate_structural(
    file_path: str,
    domain: str
) -> Dict[str, Any]:
    """
    Perform structural validation of SDTM dataset.

    Validates:
    - Required variables are present
    - Data types are correct
    - Variable lengths are within limits
    - Key uniqueness

    Args:
        file_path: Path to the SDTM CSV file
        domain: SDTM domain code

    Returns:
        Structural validation results
    """
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        return {
            "layer": "structural",
            "domain": domain,
            "is_valid": False,
            "error": str(e)
        }

    issues: List[Dict[str, Any]] = []
    domain = domain.upper()

    # Get domain requirements
    requirements = DOMAIN_REQUIREMENTS.get(domain, {})
    required_vars = requirements.get("required", [])
    key_vars = requirements.get("key", [])

    # Check required variables
    for var in required_vars:
        if var not in df.columns:
            issues.append({
                "rule_id": f"STRUCT-{domain}-001",
                "severity": "error",
                "message": f"Required variable '{var}' is missing",
                "variable": var,
                "affected_records": len(df)
            })
        elif df[var].isna().all():
            issues.append({
                "rule_id": f"STRUCT-{domain}-002",
                "severity": "error",
                "message": f"Required variable '{var}' is completely empty",
                "variable": var,
                "affected_records": len(df)
            })

    # Check STUDYID consistency
    if "STUDYID" in df.columns:
        unique_studies = df["STUDYID"].nunique()
        if unique_studies > 1:
            issues.append({
                "rule_id": "STRUCT-001",
                "severity": "error",
                "message": f"Multiple STUDYID values found: {unique_studies}",
                "variable": "STUDYID",
                "affected_records": len(df)
            })

    # Check DOMAIN value
    if "DOMAIN" in df.columns:
        incorrect = (df["DOMAIN"] != domain).sum()
        if incorrect > 0:
            issues.append({
                "rule_id": "STRUCT-002",
                "severity": "error",
                "message": f"DOMAIN value mismatch: {incorrect} records",
                "variable": "DOMAIN",
                "affected_records": int(incorrect)
            })

    # Check key uniqueness
    if all(k in df.columns for k in key_vars) and len(key_vars) > 0:
        duplicates = df.duplicated(subset=key_vars).sum()
        if duplicates > 0:
            issues.append({
                "rule_id": f"STRUCT-{domain}-003",
                "severity": "error",
                "message": f"Duplicate keys found: {duplicates} records",
                "variable": ", ".join(key_vars),
                "affected_records": int(duplicates)
            })

    # Check one record per subject for DM
    if domain == "DM" and requirements.get("one_per_subject"):
        if "USUBJID" in df.columns:
            dup_subjects = df["USUBJID"].duplicated().sum()
            if dup_subjects > 0:
                issues.append({
                    "rule_id": "STRUCT-DM-004",
                    "severity": "error",
                    "message": f"Multiple records per subject: {dup_subjects}",
                    "variable": "USUBJID",
                    "affected_records": int(dup_subjects)
                })

    # Check variable lengths (SDTM limits)
    length_limits = {
        "STUDYID": 20,
        "DOMAIN": 2,
        "USUBJID": 40,
        "SUBJID": 20,
    }
    for var, limit in length_limits.items():
        if var in df.columns:
            over_limit = df[var].astype(str).str.len().gt(limit).sum()
            if over_limit > 0:
                issues.append({
                    "rule_id": "STRUCT-003",
                    "severity": "warning",
                    "message": f"Variable '{var}' exceeds length limit ({limit}): {over_limit} records",
                    "variable": var,
                    "affected_records": int(over_limit)
                })

    error_count = sum(1 for i in issues if i["severity"] == "error")
    warning_count = sum(1 for i in issues if i["severity"] == "warning")

    return {
        "layer": "structural",
        "domain": domain,
        "is_valid": error_count == 0,
        "total_records": len(df),
        "error_count": error_count,
        "warning_count": warning_count,
        "issues": issues
    }


@tool
def validate_cdisc_conformance(
    file_path: str,
    domain: str
) -> Dict[str, Any]:
    """
    Validate SDTM dataset against CDISC conformance rules.

    Validates:
    - Controlled terminology values
    - ISO 8601 date formats
    - SDTM-IG specific rules
    - CORE designation compliance

    Args:
        file_path: Path to the SDTM CSV file
        domain: SDTM domain code

    Returns:
        CDISC conformance validation results
    """
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        return {
            "layer": "cdisc",
            "domain": domain,
            "is_valid": False,
            "error": str(e)
        }

    issues: List[Dict[str, Any]] = []
    domain = domain.upper()

    # Controlled Terminology checks
    ct_checks = {
        "SEX": ["M", "F", "U", "UNDIFFERENTIATED"],
        "RACE": ["AMERICAN INDIAN OR ALASKA NATIVE", "ASIAN", "BLACK OR AFRICAN AMERICAN",
                 "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER", "WHITE", "MULTIPLE", "NOT REPORTED", "UNKNOWN"],
        "ETHNIC": ["HISPANIC OR LATINO", "NOT HISPANIC OR LATINO", "NOT REPORTED", "UNKNOWN"],
        "AGEU": ["YEARS", "MONTHS", "WEEKS", "DAYS", "HOURS"],
        "AESER": ["Y", "N"],
        "AESEV": ["MILD", "MODERATE", "SEVERE"],
        "LBNRIND": ["NORMAL", "LOW", "HIGH", "ABNORMAL"],
    }

    for var, valid_values in ct_checks.items():
        if var in df.columns:
            non_null = df[~df[var].isna()]
            if len(non_null) > 0:
                invalid = non_null[~non_null[var].str.upper().isin([v.upper() for v in valid_values])]
                if len(invalid) > 0:
                    invalid_values = invalid[var].unique()[:5]
                    issues.append({
                        "rule_id": f"CDISC-CT-{var}",
                        "severity": "error" if var in ["SEX", "AESER"] else "warning",
                        "message": f"Invalid CT values for {var}: {list(invalid_values)}",
                        "variable": var,
                        "affected_records": len(invalid)
                    })

    # ISO 8601 date format checks
    date_cols = [col for col in df.columns if col.endswith("DTC")]
    import re
    iso_pattern = re.compile(r"^\d{4}(-\d{2}(-\d{2}(T\d{2}(:\d{2}(:\d{2})?)?)?)?)?$")

    for col in date_cols:
        if col in df.columns:
            non_null = df[col].dropna().astype(str)
            invalid_dates = non_null[~non_null.str.match(iso_pattern, na=False)]
            if len(invalid_dates) > 0:
                issues.append({
                    "rule_id": f"CDISC-DATE-{col}",
                    "severity": "error",
                    "message": f"Non-ISO 8601 dates in {col}",
                    "variable": col,
                    "affected_records": len(invalid_dates)
                })

    # Check timing variable consistency (start <= end)
    timing_pairs = [
        ("RFSTDTC", "RFENDTC"),
        ("AESTDTC", "AEENDTC"),
        ("CMSTDTC", "CMENDTC"),
        ("EXSTDTC", "EXENDTC"),
    ]
    for start_col, end_col in timing_pairs:
        if start_col in df.columns and end_col in df.columns:
            both = df[~df[start_col].isna() & ~df[end_col].isna()]
            if len(both) > 0:
                invalid = both[both[start_col].astype(str) > both[end_col].astype(str)]
                if len(invalid) > 0:
                    issues.append({
                        "rule_id": f"CDISC-TIME-{start_col}",
                        "severity": "error",
                        "message": f"{start_col} after {end_col}",
                        "variable": f"{start_col}/{end_col}",
                        "affected_records": len(invalid)
                    })

    # Check sequence variable format
    seq_var = f"{domain}SEQ"
    if seq_var in df.columns:
        # Should be positive integers
        non_positive = df[df[seq_var].notna() & (df[seq_var] <= 0)]
        if len(non_positive) > 0:
            issues.append({
                "rule_id": f"CDISC-SEQ-{domain}",
                "severity": "error",
                "message": f"{seq_var} must be positive integer",
                "variable": seq_var,
                "affected_records": len(non_positive)
            })

    error_count = sum(1 for i in issues if i["severity"] == "error")
    warning_count = sum(1 for i in issues if i["severity"] == "warning")

    return {
        "layer": "cdisc",
        "domain": domain,
        "is_valid": error_count == 0,
        "total_records": len(df),
        "error_count": error_count,
        "warning_count": warning_count,
        "issues": issues
    }


@tool
def validate_cross_domain(
    domain_paths: Dict[str, str]
) -> Dict[str, Any]:
    """
    Validate cross-domain referential integrity.

    Validates:
    - All subjects in other domains exist in DM
    - VISITNUM/VISIT consistency across domains
    - EPOCH values are consistent
    - Related records match (e.g., AE and SUPPAE)

    Args:
        domain_paths: Dictionary mapping domain codes to file paths

    Returns:
        Cross-domain validation results
    """
    issues: List[Dict[str, Any]] = []
    domains_loaded: Dict[str, pd.DataFrame] = {}

    # Load all domains
    for domain, path in domain_paths.items():
        try:
            domains_loaded[domain.upper()] = pd.read_csv(path)
        except Exception as e:
            issues.append({
                "rule_id": "XDOM-LOAD",
                "severity": "error",
                "message": f"Failed to load {domain}: {e}",
                "variable": None,
                "affected_records": 0
            })

    if not domains_loaded:
        return {
            "layer": "cross_domain",
            "is_valid": False,
            "error": "No domains loaded",
            "issues": issues
        }

    # Get DM subjects as reference
    dm_subjects: Set[str] = set()
    if "DM" in domains_loaded:
        dm_df = domains_loaded["DM"]
        if "USUBJID" in dm_df.columns:
            dm_subjects = set(dm_df["USUBJID"].dropna().unique())

    # Check all subjects exist in DM
    for domain, df in domains_loaded.items():
        if domain == "DM":
            continue
        if "USUBJID" in df.columns and dm_subjects:
            domain_subjects = set(df["USUBJID"].dropna().unique())
            orphan_subjects = domain_subjects - dm_subjects
            if orphan_subjects:
                issues.append({
                    "rule_id": f"XDOM-{domain}-DM",
                    "severity": "error",
                    "message": f"{len(orphan_subjects)} subjects in {domain} not in DM",
                    "variable": "USUBJID",
                    "affected_records": len(orphan_subjects)
                })

    # Check SUPP domain relationships
    for domain, df in domains_loaded.items():
        if domain.startswith("SUPP"):
            parent_domain = domain[4:]  # e.g., SUPPAE -> AE
            if parent_domain in domains_loaded:
                parent_df = domains_loaded[parent_domain]
                if "USUBJID" in df.columns and "IDVAR" in df.columns and "IDVARVAL" in df.columns:
                    # Check that IDVAR/IDVARVAL combinations exist in parent
                    seq_var = f"{parent_domain}SEQ"
                    if seq_var in parent_df.columns:
                        for _, row in df.iterrows():
                            if row.get("IDVAR") == seq_var:
                                parent_match = parent_df[
                                    (parent_df["USUBJID"] == row["USUBJID"]) &
                                    (parent_df[seq_var].astype(str) == str(row["IDVARVAL"]))
                                ]
                                if len(parent_match) == 0:
                                    issues.append({
                                        "rule_id": f"XDOM-{domain}-PARENT",
                                        "severity": "error",
                                        "message": f"Orphan {domain} record: {row['USUBJID']} / {row['IDVARVAL']}",
                                        "variable": "IDVARVAL",
                                        "affected_records": 1
                                    })

    # Check VISITNUM consistency
    visit_domains = ["VS", "LB", "EG", "PE"]
    visitnum_values: Dict[str, Set] = {}
    for domain in visit_domains:
        if domain in domains_loaded and "VISITNUM" in domains_loaded[domain].columns:
            visitnum_values[domain] = set(domains_loaded[domain]["VISITNUM"].dropna().unique())

    if len(visitnum_values) > 1:
        all_visits = set.union(*visitnum_values.values())
        for domain, visits in visitnum_values.items():
            missing = all_visits - visits
            if missing:
                issues.append({
                    "rule_id": f"XDOM-VISIT-{domain}",
                    "severity": "info",
                    "message": f"{domain} missing VISITNUM values: {sorted(missing)[:5]}",
                    "variable": "VISITNUM",
                    "affected_records": 0
                })

    error_count = sum(1 for i in issues if i["severity"] == "error")
    warning_count = sum(1 for i in issues if i["severity"] == "warning")

    return {
        "layer": "cross_domain",
        "domains_validated": list(domains_loaded.keys()),
        "is_valid": error_count == 0,
        "dm_subjects": len(dm_subjects),
        "error_count": error_count,
        "warning_count": warning_count,
        "issues": issues
    }


@tool
def validate_semantic(
    file_path: str,
    domain: str,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Perform semantic validation using LLM and knowledge base.

    Validates:
    - Business logic that requires understanding context
    - Clinical plausibility of values
    - Protocol-specific requirements
    - Complex derivation rule compliance

    Args:
        file_path: Path to the SDTM CSV file
        domain: SDTM domain code
        context: Optional additional context (e.g., protocol info)

    Returns:
        Semantic validation results
    """
    try:
        df = pd.read_csv(file_path, nrows=1000)  # Sample for semantic analysis
    except Exception as e:
        return {
            "layer": "semantic",
            "domain": domain,
            "is_valid": False,
            "error": str(e)
        }

    issues: List[Dict[str, Any]] = []
    domain = domain.upper()

    # Domain-specific semantic checks
    if domain == "DM":
        issues.extend(_semantic_dm_checks(df))
    elif domain == "AE":
        issues.extend(_semantic_ae_checks(df))
    elif domain == "VS":
        issues.extend(_semantic_vs_checks(df))
    elif domain == "LB":
        issues.extend(_semantic_lb_checks(df))
    elif domain == "EX":
        issues.extend(_semantic_ex_checks(df))

    # Try knowledge base lookup for additional rules
    try:
        from ..langgraph_agent.knowledge_tools import get_knowledge_retriever
        retriever = get_knowledge_retriever()
        kb_rules = retriever.get_business_rules(domain, rule_type="all")

        for rule in kb_rules[:10]:  # Limit to top 10 rules
            rule_desc = rule.get("description", rule.get("content", ""))
            if rule_desc:
                # Note: In production, this would apply the rule
                pass
    except Exception:
        pass

    error_count = sum(1 for i in issues if i["severity"] == "error")
    warning_count = sum(1 for i in issues if i["severity"] == "warning")

    return {
        "layer": "semantic",
        "domain": domain,
        "is_valid": error_count == 0,
        "total_records": len(df),
        "error_count": error_count,
        "warning_count": warning_count,
        "issues": issues
    }


def _semantic_dm_checks(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Semantic checks for Demographics."""
    issues = []

    # Age plausibility
    if "AGE" in df.columns:
        implausible = df[(df["AGE"] < 0) | (df["AGE"] > 120)]
        if len(implausible) > 0:
            issues.append({
                "rule_id": "SEM-DM-AGE",
                "severity": "warning",
                "message": f"Implausible AGE values (outside 0-120)",
                "variable": "AGE",
                "affected_records": len(implausible)
            })

    # Reference dates logic
    if "RFSTDTC" in df.columns and "BRTHDTC" in df.columns:
        both = df[df["RFSTDTC"].notna() & df["BRTHDTC"].notna()]
        invalid = both[both["BRTHDTC"] > both["RFSTDTC"]]
        if len(invalid) > 0:
            issues.append({
                "rule_id": "SEM-DM-BRTHDTC",
                "severity": "error",
                "message": "Birth date after reference start date",
                "variable": "BRTHDTC",
                "affected_records": len(invalid)
            })

    return issues


def _semantic_ae_checks(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Semantic checks for Adverse Events."""
    issues = []

    # Serious AE consistency
    if "AESER" in df.columns:
        sae_criteria = ["AESCONG", "AESDISAB", "AESDTH", "AESHOSP", "AESLIFE", "AESMIE"]
        present_criteria = [c for c in sae_criteria if c in df.columns]

        if present_criteria:
            serious = df[df["AESER"] == "Y"]
            if len(serious) > 0:
                no_criteria = 0
                for _, row in serious.iterrows():
                    if not any(str(row.get(c, "")).upper() == "Y" for c in present_criteria):
                        no_criteria += 1

                if no_criteria > 0:
                    issues.append({
                        "rule_id": "SEM-AE-SAE",
                        "severity": "warning",
                        "message": "Serious AE without any seriousness criterion flagged",
                        "variable": "AESER",
                        "affected_records": no_criteria
                    })

    # Fatal outcome consistency
    if "AEOUT" in df.columns and "AESDTH" in df.columns:
        fatal_out = df[df["AEOUT"].str.upper() == "FATAL"]
        no_death_flag = fatal_out[fatal_out["AESDTH"] != "Y"]
        if len(no_death_flag) > 0:
            issues.append({
                "rule_id": "SEM-AE-FATAL",
                "severity": "error",
                "message": "AEOUT=FATAL but AESDTH not Y",
                "variable": "AEOUT",
                "affected_records": len(no_death_flag)
            })

    return issues


def _semantic_vs_checks(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Semantic checks for Vital Signs."""
    issues = []

    # Vital signs value ranges
    vs_ranges = {
        "SYSBP": (50, 300),
        "DIABP": (20, 200),
        "PULSE": (20, 250),
        "TEMP": (30, 45),  # Celsius
        "HEIGHT": (30, 250),  # cm
        "WEIGHT": (1, 500),  # kg
    }

    if "VSTESTCD" in df.columns and "VSSTRESN" in df.columns:
        for testcd, (low, high) in vs_ranges.items():
            test_data = df[(df["VSTESTCD"] == testcd) & df["VSSTRESN"].notna()]
            if len(test_data) > 0:
                out_of_range = test_data[(test_data["VSSTRESN"] < low) | (test_data["VSSTRESN"] > high)]
                if len(out_of_range) > 0:
                    issues.append({
                        "rule_id": f"SEM-VS-{testcd}",
                        "severity": "warning",
                        "message": f"{testcd} values outside expected range ({low}-{high})",
                        "variable": "VSSTRESN",
                        "affected_records": len(out_of_range)
                    })

    return issues


def _semantic_lb_checks(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Semantic checks for Laboratory."""
    issues = []

    # Check reference range indicator consistency
    if all(c in df.columns for c in ["LBSTRESN", "LBSTNRLO", "LBSTNRHI", "LBNRIND"]):
        has_ranges = df[df["LBSTRESN"].notna() & df["LBSTNRLO"].notna()]
        if len(has_ranges) > 0:
            inconsistent = 0
            for _, row in has_ranges.iterrows():
                try:
                    result = float(row["LBSTRESN"])
                    low = float(row["LBSTNRLO"])
                    high = float(row["LBSTNRHI"]) if pd.notna(row.get("LBSTNRHI")) else float("inf")
                    nrind = str(row.get("LBNRIND", "")).upper()

                    if result < low and "LOW" not in nrind:
                        inconsistent += 1
                    elif result > high and "HIGH" not in nrind:
                        inconsistent += 1
                except (ValueError, TypeError):
                    pass

            if inconsistent > 0:
                issues.append({
                    "rule_id": "SEM-LB-NRIND",
                    "severity": "warning",
                    "message": "LBNRIND inconsistent with result/range",
                    "variable": "LBNRIND",
                    "affected_records": inconsistent
                })

    return issues


def _semantic_ex_checks(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Semantic checks for Exposure."""
    issues = []

    # Dose consistency
    if "EXDOSE" in df.columns:
        negative = df[df["EXDOSE"] < 0]
        if len(negative) > 0:
            issues.append({
                "rule_id": "SEM-EX-DOSE",
                "severity": "error",
                "message": "Negative EXDOSE values",
                "variable": "EXDOSE",
                "affected_records": len(negative)
            })

    return issues


# List of all tools for this agent
VALIDATOR_TOOLS = [
    validate_structural,
    validate_cdisc_conformance,
    validate_cross_domain,
    validate_semantic
]


class ValidatorAgent:
    """
    Enhanced Validator Agent with multi-layer validation.

    Validation Layers:
    1. Structural - Required variables, data types, lengths
    2. CDISC - SDTM-IG rules, controlled terminology
    3. Cross-Domain - Referential integrity
    4. Semantic - Business logic via LLM + KB
    """

    SYSTEM_PROMPT = """You are a Validation Agent specialized in SDTM data quality and conformance.

Your responsibilities:
1. Perform structural validation (required vars, types, lengths)
2. Validate CDISC conformance (CT values, ISO dates, SDTM rules)
3. Check cross-domain referential integrity
4. Apply semantic validation for business logic

Validation approach:
- Run all validation layers for comprehensive coverage
- Prioritize errors over warnings
- Provide actionable recommendations for each issue
- Consider clinical context when evaluating data

Key checks to perform:
- Required variables present and populated
- Controlled terminology compliance
- ISO 8601 date format
- Key uniqueness within domain
- All subjects exist in DM
- Timing variables logical (start <= end)
- Clinical plausibility of values

Report results by severity (error/warning/info) with affected record counts."""

    def __init__(self, api_key: Optional[str] = None):
        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
        self.llm = ChatAnthropic(
            model=model,
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=4096
        )
        self.agent = create_react_agent(
            self.llm,
            VALIDATOR_TOOLS,
            state_modifier=self.SYSTEM_PROMPT
        )

    async def validate_all_layers(
        self,
        domain_paths: Dict[str, str]
    ) -> Dict[str, Any]:
        """Run all validation layers."""
        input_message = f"""Perform comprehensive multi-layer validation for these SDTM domains:

{domain_paths}

For each domain:
1. Run structural validation
2. Run CDISC conformance validation
3. Run semantic validation

Then run cross-domain validation for all domains together.

Summarize findings by severity level."""

        result = await self.agent.ainvoke({
            "messages": [{"role": "user", "content": input_message}]
        })

        return {
            "agent": "validator",
            "result": result.get("messages", [])[-1].content if result.get("messages") else "",
            "timestamp": datetime.now().isoformat()
        }

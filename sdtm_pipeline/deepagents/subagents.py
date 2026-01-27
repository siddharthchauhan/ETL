"""
SDTM Specialized Subagents (Async)
===================================
DeepAgents subagent configurations for SDTM domain expertise.

All tools are async to prevent blocking the ASGI event loop in LangGraph.

Each subagent is a specialized agent that can be delegated to via the
built-in `task` tool. Subagents provide context isolation and domain
expertise for specific parts of the SDTM transformation pipeline.

Subagents:
- sdtm-expert: SDTM-IG specifications and mapping guidance
- validator: Multi-layer CDISC compliance validation
- transformer: Domain-specific SDTM transformations
- code-generator: SAS and R program generation
- data-loader: Neo4j and S3 data loading
"""

import os
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from langchain_core.tools import tool
import pandas as pd
import aiofiles
import aiofiles.os

# Async utilities
from .async_utils import (
    async_read_csv,
    async_to_csv,
    async_makedirs,
    async_s3_upload,
    async_neo4j_load_dataframe,
)


# =============================================================================
# EMBEDDED SDTM KNOWLEDGE
# =============================================================================

SDTM_DOMAINS = {
    "DM": {
        "label": "Demographics",
        "class": "Special-Purpose",
        "required": ["STUDYID", "DOMAIN", "USUBJID", "SUBJID", "RFSTDTC", "RFENDTC", "SITEID", "BRTHDTC", "AGE", "AGEU", "SEX", "RACE", "ETHNIC", "ARMCD", "ARM", "COUNTRY"],
        "expected": ["INVID", "INVNAM", "RFXSTDTC", "RFXENDTC", "RFICDTC", "RFPENDTC", "DTHDTC", "DTHFL", "ACTARMCD", "ACTARM"],
    },
    "AE": {
        "label": "Adverse Events",
        "class": "Events",
        "required": ["STUDYID", "DOMAIN", "USUBJID", "AESEQ", "AETERM", "AEDECOD", "AESTDTC"],
        "expected": ["AEBODSYS", "AESEV", "AESER", "AEACN", "AEREL", "AEOUT", "AESCONG", "AESDISAB", "AESDTH", "AESHOSP", "AESLIFE", "AESMIE", "AEENDTC"],
    },
    "VS": {
        "label": "Vital Signs",
        "class": "Findings",
        "required": ["STUDYID", "DOMAIN", "USUBJID", "VSSEQ", "VSTESTCD", "VSTEST", "VSORRES", "VSORRESU"],
        "expected": ["VSCAT", "VSPOS", "VSLOC", "VSMETHOD", "VSBLFL", "VSDRVFL", "VSSTRESC", "VSSTRESN", "VSSTRESU", "VSDTC", "VISITNUM", "VISIT"],
    },
    "LB": {
        "label": "Laboratory Test Results",
        "class": "Findings",
        "required": ["STUDYID", "DOMAIN", "USUBJID", "LBSEQ", "LBTESTCD", "LBTEST", "LBORRES", "LBORRESU"],
        "expected": ["LBCAT", "LBSCAT", "LBSPEC", "LBMETHOD", "LBBLFL", "LBDRVFL", "LBSTRESC", "LBSTRESN", "LBSTRESU", "LBSTNRLO", "LBSTNRHI", "LBNRIND", "LBDTC", "VISITNUM", "VISIT"],
    },
    "CM": {
        "label": "Concomitant Medications",
        "class": "Interventions",
        "required": ["STUDYID", "DOMAIN", "USUBJID", "CMSEQ", "CMTRT"],
        "expected": ["CMCAT", "CMSCAT", "CMDECOD", "CMDOSE", "CMDOSU", "CMDOSFRM", "CMROUTE", "CMSTDTC", "CMENDTC", "CMONGO", "CMINDC"],
    },
    "EX": {
        "label": "Exposure",
        "class": "Interventions",
        "required": ["STUDYID", "DOMAIN", "USUBJID", "EXSEQ", "EXTRT", "EXDOSE", "EXDOSU", "EXSTDTC", "EXENDTC"],
        "expected": ["EXCAT", "EXDOSFRM", "EXDOSFRQ", "EXROUTE", "EXLOT", "EXLOC", "EXFAST", "EXADJ", "EPOCH", "VISITNUM", "VISIT"],
    },
}

CONTROLLED_TERMINOLOGY = {
    "SEX": ["M", "F", "U", "UNDIFFERENTIATED"],
    "RACE": ["AMERICAN INDIAN OR ALASKA NATIVE", "ASIAN", "BLACK OR AFRICAN AMERICAN", "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER", "WHITE", "MULTIPLE", "NOT REPORTED", "UNKNOWN"],
    "ETHNIC": ["HISPANIC OR LATINO", "NOT HISPANIC OR LATINO", "NOT REPORTED", "UNKNOWN"],
    "AGEU": ["YEARS", "MONTHS", "WEEKS", "DAYS", "HOURS"],
    "AESER": ["Y", "N"],
    "AESEV": ["MILD", "MODERATE", "SEVERE"],
}


# =============================================================================
# SDTM EXPERT TOOLS (No I/O - can stay sync)
# =============================================================================

@tool
def lookup_sdtm_domain(domain: str) -> Dict[str, Any]:
    """
    Look up SDTM-IG domain specification.

    Args:
        domain: SDTM domain code (e.g., DM, AE, VS, LB, CM)

    Returns:
        Domain specification with required and expected variables
    """
    domain = domain.upper()
    if domain in SDTM_DOMAINS:
        return {
            "domain": domain,
            "label": SDTM_DOMAINS[domain]["label"],
            "class": SDTM_DOMAINS[domain]["class"],
            "required_variables": SDTM_DOMAINS[domain]["required"],
            "expected_variables": SDTM_DOMAINS[domain]["expected"],
        }
    return {"error": f"Unknown domain: {domain}", "available_domains": list(SDTM_DOMAINS.keys())}


@tool
def validate_controlled_terminology(codelist: str, value: str) -> Dict[str, Any]:
    """
    Validate a value against CDISC Controlled Terminology.

    Args:
        codelist: CT codelist name (e.g., SEX, RACE, AESER)
        value: Value to validate

    Returns:
        Validation result with valid values if invalid
    """
    codelist = codelist.upper()
    value = value.upper() if value else ""

    if codelist not in CONTROLLED_TERMINOLOGY:
        return {"error": f"Unknown codelist: {codelist}", "available": list(CONTROLLED_TERMINOLOGY.keys())}

    valid_values = CONTROLLED_TERMINOLOGY[codelist]
    is_valid = value in valid_values

    return {
        "codelist": codelist,
        "value": value,
        "is_valid": is_valid,
        "valid_values": valid_values if not is_valid else None,
    }


@tool
def get_mapping_recommendations(source_columns: List[str], target_domain: str) -> Dict[str, Any]:
    """
    Get mapping recommendations for source columns to SDTM variables.

    Args:
        source_columns: List of source column names
        target_domain: Target SDTM domain code

    Returns:
        Mapping recommendations with confidence scores
    """
    domain = target_domain.upper()
    recommendations = []

    patterns = {
        "subjid": "USUBJID", "subject": "USUBJID", "patient": "USUBJID",
        "age": "AGE", "sex": "SEX", "gender": "SEX", "race": "RACE",
        "ethnic": "ETHNIC", "country": "COUNTRY", "site": "SITEID",
        "birth": "BRTHDTC", "death": "DTHDTC",
        "start": f"{domain}STDTC" if domain not in ["DM"] else "RFSTDTC",
        "end": f"{domain}ENDTC" if domain not in ["DM"] else "RFENDTC",
        "term": f"{domain}TERM" if domain in ["AE", "MH", "CM", "DS"] else None,
        "dose": "EXDOSE" if domain == "EX" else "CMDOSE" if domain == "CM" else None,
    }

    for col in source_columns:
        col_lower = col.lower()
        for pattern, target in patterns.items():
            if target and pattern in col_lower:
                recommendations.append({
                    "source": col,
                    "target": target,
                    "confidence": "high" if pattern == col_lower else "medium",
                })
                break

    return {
        "target_domain": domain,
        "recommendations": recommendations,
        "domain_required": SDTM_DOMAINS.get(domain, {}).get("required", []),
    }


SDTM_EXPERT_TOOLS = [lookup_sdtm_domain, validate_controlled_terminology, get_mapping_recommendations]


# =============================================================================
# VALIDATOR TOOLS (Async)
# =============================================================================

@tool
async def validate_structural(file_path: str, domain: str) -> Dict[str, Any]:
    """
    Perform structural validation of SDTM dataset (async).

    Args:
        file_path: Path to SDTM CSV file
        domain: SDTM domain code

    Returns:
        Structural validation results
    """
    try:
        df = await async_read_csv(file_path)
    except Exception as e:
        return {"layer": "structural", "domain": domain, "is_valid": False, "error": str(e)}

    issues = []
    domain = domain.upper()
    requirements = SDTM_DOMAINS.get(domain, {})
    required_vars = requirements.get("required", [])

    for var in required_vars:
        if var not in df.columns:
            issues.append({"rule_id": f"STRUCT-{domain}-001", "severity": "error", "message": f"Required variable '{var}' is missing", "variable": var})
        elif df[var].isna().all():
            issues.append({"rule_id": f"STRUCT-{domain}-002", "severity": "error", "message": f"Required variable '{var}' is completely empty", "variable": var})

    error_count = sum(1 for i in issues if i["severity"] == "error")
    return {
        "layer": "structural",
        "domain": domain,
        "is_valid": error_count == 0,
        "total_records": len(df),
        "error_count": error_count,
        "issues": issues
    }


@tool
async def validate_cdisc_conformance(file_path: str, domain: str) -> Dict[str, Any]:
    """
    Validate SDTM dataset against CDISC conformance rules (async).

    Args:
        file_path: Path to SDTM CSV file
        domain: SDTM domain code

    Returns:
        CDISC conformance validation results
    """
    import re

    try:
        df = await async_read_csv(file_path)
    except Exception as e:
        return {"layer": "cdisc", "domain": domain, "is_valid": False, "error": str(e)}

    issues = []
    domain = domain.upper()

    # ISO 8601 date checks
    date_cols = [col for col in df.columns if col.endswith("DTC")]
    iso_pattern = re.compile(r"^\d{4}(-\d{2}(-\d{2}(T\d{2}(:\d{2}(:\d{2})?)?)?)?)?$")

    for col in date_cols:
        if col in df.columns:
            non_null = df[col].dropna().astype(str)
            invalid_dates = non_null[~non_null.str.match(iso_pattern, na=False)]
            if len(invalid_dates) > 0:
                issues.append({"rule_id": f"CDISC-DATE-{col}", "severity": "error", "message": f"Non-ISO 8601 dates in {col}", "affected_records": len(invalid_dates)})

    error_count = sum(1 for i in issues if i["severity"] == "error")
    return {
        "layer": "cdisc",
        "domain": domain,
        "is_valid": error_count == 0,
        "total_records": len(df),
        "error_count": error_count,
        "issues": issues
    }


@tool
def calculate_compliance_score(validation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate overall CDISC compliance score.

    Args:
        validation_results: List of validation results

    Returns:
        Compliance score and summary
    """
    total_checks = len(validation_results)
    passed_checks = sum(1 for r in validation_results if r.get("is_valid"))
    score = (passed_checks / total_checks * 100) if total_checks > 0 else 0

    return {
        "compliance_score": round(score, 1),
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "submission_ready": score >= 95,
    }


VALIDATOR_TOOLS = [validate_structural, validate_cdisc_conformance, calculate_compliance_score]


# =============================================================================
# TRANSFORMER TOOLS (Async)
# =============================================================================

@tool
async def transform_demographics(file_path: str, study_id: str, output_path: str) -> Dict[str, Any]:
    """
    Transform source demographics data to SDTM DM domain (async).

    Args:
        file_path: Path to source demographics CSV
        study_id: Study identifier
        output_path: Path to save transformed DM.csv

    Returns:
        Transformation result
    """
    try:
        df = await async_read_csv(file_path)
        records_in = len(df)

        dm = pd.DataFrame()
        dm["STUDYID"] = study_id
        dm["DOMAIN"] = "DM"

        col_map = {
            "SUBJECT_ID": "SUBJID", "SUBJID": "SUBJID",
            "AGE": "AGE", "SEX": "SEX", "GENDER": "SEX",
            "RACE": "RACE", "ETHNIC": "ETHNIC",
            "COUNTRY": "COUNTRY", "SITE": "SITEID",
        }

        for src, tgt in col_map.items():
            if src in df.columns:
                dm[tgt] = df[src]

        if "SUBJID" in dm.columns:
            dm["USUBJID"] = study_id + "-" + dm["SUBJID"].astype(str)

        if "AGEU" not in dm.columns:
            dm["AGEU"] = "YEARS"

        await async_to_csv(dm, output_path, index=False)

        return {"success": True, "domain": "DM", "records_in": records_in, "records_out": len(dm), "output_path": output_path}
    except Exception as e:
        return {"success": False, "domain": "DM", "error": str(e)}


@tool
async def transform_adverse_events(file_path: str, study_id: str, output_path: str) -> Dict[str, Any]:
    """
    Transform source adverse event data to SDTM AE domain (async).

    Args:
        file_path: Path to source AE CSV
        study_id: Study identifier
        output_path: Path to save transformed AE.csv

    Returns:
        Transformation result
    """
    try:
        df = await async_read_csv(file_path)
        records_in = len(df)

        ae = pd.DataFrame()
        ae["STUDYID"] = study_id
        ae["DOMAIN"] = "AE"
        ae["AESEQ"] = range(1, len(df) + 1)

        col_map = {
            "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID",
            "AETERM": "AETERM", "ADVERSE_EVENT": "AETERM",
            "AEDECOD": "AEDECOD", "PREFERRED_TERM": "AEDECOD",
            "AESTDTC": "AESTDTC", "START_DATE": "AESTDTC",
            "AEENDTC": "AEENDTC", "END_DATE": "AEENDTC",
            "AESEV": "AESEV", "SEVERITY": "AESEV",
            "AESER": "AESER", "SERIOUS": "AESER",
        }

        for src, tgt in col_map.items():
            if src in df.columns:
                ae[tgt] = df[src]

        if "USUBJID" in ae.columns and not ae["USUBJID"].astype(str).str.contains("-").any():
            ae["USUBJID"] = study_id + "-" + ae["USUBJID"].astype(str)

        await async_to_csv(ae, output_path, index=False)

        return {"success": True, "domain": "AE", "records_in": records_in, "records_out": len(ae), "output_path": output_path}
    except Exception as e:
        return {"success": False, "domain": "AE", "error": str(e)}


# Import the batch conversion tool from langgraph_chat
from sdtm_pipeline.langgraph_chat.tools import convert_domain, convert_all_domains

TRANSFORMER_TOOLS = [
    transform_demographics,
    transform_adverse_events,
    convert_domain,         # High-level tool for single domain
    convert_all_domains,    # Batch conversion for ALL domains - USE THIS!
]


# =============================================================================
# CODE GENERATOR TOOLS (Async)
# =============================================================================

@tool
async def generate_sas_program(domain: str, mapping_spec: Dict[str, Any], output_path: str) -> Dict[str, Any]:
    """
    Generate SAS program for SDTM transformation (async).

    Args:
        domain: Target SDTM domain code
        mapping_spec: Mapping specification
        output_path: Path to save SAS program

    Returns:
        Generation result
    """
    try:
        domain = domain.upper()
        sas_code = f"""/*******************************************************************************
* Program: {domain.lower()}.sas
* Purpose: Transform source data to SDTM {domain} domain
* Generated: {datetime.now().isoformat()}
*******************************************************************************/

%let domain = {domain};
%let study_id = &studyid;

data sdtm.{domain.lower()};
    set rawdata.source;
    STUDYID = "&study_id";
    DOMAIN = "&domain";
run;
"""
        await async_makedirs(os.path.dirname(output_path))
        async with aiofiles.open(output_path, 'w') as f:
            await f.write(sas_code)

        return {"success": True, "language": "SAS", "domain": domain, "output_path": output_path}
    except Exception as e:
        return {"success": False, "language": "SAS", "error": str(e)}


@tool
async def generate_r_script(domain: str, mapping_spec: Dict[str, Any], output_path: str) -> Dict[str, Any]:
    """
    Generate R script for SDTM transformation (async).

    Args:
        domain: Target SDTM domain code
        mapping_spec: Mapping specification
        output_path: Path to save R script

    Returns:
        Generation result
    """
    try:
        domain = domain.upper()
        r_code = f'''# ==============================================================================
# Script: {domain.lower()}.R
# Purpose: Transform source data to SDTM {domain} domain
# Generated: {datetime.now().isoformat()}
# ==============================================================================

library(tidyverse)

study_id <- Sys.getenv("STUDYID", "UNKNOWN")

{domain.lower()} <- source_data %>%
  mutate(
    STUDYID = study_id,
    DOMAIN = "{domain}"
  )

write_csv({domain.lower()}, "sdtm_data/{domain.lower()}.csv")
'''
        await async_makedirs(os.path.dirname(output_path))
        async with aiofiles.open(output_path, 'w') as f:
            await f.write(r_code)

        return {"success": True, "language": "R", "domain": domain, "output_path": output_path}
    except Exception as e:
        return {"success": False, "language": "R", "error": str(e)}


CODE_GENERATOR_TOOLS = [generate_sas_program, generate_r_script]


# =============================================================================
# DATA LOADER TOOLS (Async)
# =============================================================================

@tool
async def load_to_neo4j(domain: str, file_path: str) -> Dict[str, Any]:
    """
    Load SDTM domain data to Neo4j graph database (async).

    Args:
        domain: SDTM domain code
        file_path: Path to SDTM CSV file

    Returns:
        Load result with node count
    """
    try:
        df = await async_read_csv(file_path)

        uri = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "")

        result = await async_neo4j_load_dataframe(
            df=df,
            uri=uri,
            user=user,
            password=password,
            label=f"SDTM_{domain.upper()}",
        )

        return result
    except Exception as e:
        return {"success": False, "domain": domain, "error": str(e)}


@tool
async def upload_to_s3(file_path: str, s3_key: str) -> Dict[str, Any]:
    """
    Upload file to S3 bucket (async).

    Args:
        file_path: Local file path
        s3_key: S3 object key

    Returns:
        Upload result
    """
    try:
        bucket = os.getenv("S3_ETL_BUCKET", "s3dcri")
        result = await async_s3_upload(file_path, bucket, s3_key)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


DATA_LOADER_TOOLS = [load_to_neo4j, upload_to_s3]


# =============================================================================
# SUBAGENT CONFIGURATIONS (dict format for SubAgent class)
# =============================================================================

SDTM_EXPERT_SUBAGENT = {
    "name": "sdtm-expert",
    "description": "SDTM-IG specification expert. Use for domain lookups, controlled terminology validation, and mapping guidance.",
    "system_prompt": """You are an SDTM Expert Agent with deep knowledge of CDISC SDTM-IG 3.4 specifications.

Your expertise includes:
- SDTM domain structures (DM, AE, VS, LB, CM, EX, MH, DS, etc.)
- Required vs Expected vs Permissible variables
- CDISC Controlled Terminology codelists
- Variable naming conventions (--SEQ, --TESTCD, --ORRES, etc.)

When asked about mappings:
1. Look up the target domain specification
2. Check controlled terminology requirements
3. Provide specific recommendations with confidence levels""",
    "tools": SDTM_EXPERT_TOOLS,
}

VALIDATOR_SUBAGENT = {
    "name": "validator",
    "description": "Multi-layer SDTM validation expert. Use for structural validation, CDISC conformance checks, and compliance scoring.",
    "system_prompt": """You are a Validation Agent specialized in SDTM data quality and CDISC compliance.

Your validation approach follows layers:
1. Structural: Required variables, data types, lengths
2. CDISC: Controlled terminology, ISO 8601 dates
3. Compliance Scoring: Calculate overall score

Submission readiness requires:
- Compliance score >= 95%
- Zero critical errors""",
    "tools": VALIDATOR_TOOLS,
}

TRANSFORMER_SUBAGENT = {
    "name": "transformer",
    "description": "SDTM domain transformation specialist. Use to transform source EDC data to SDTM format. Can convert single domains or ALL domains at once.",
    "system_prompt": """You are a Transformation Agent specialized in converting EDC data to SDTM format.

## IMPORTANT: Tool Selection

**For "convert ALL domains" or "convert everything" requests:**
→ Use `convert_all_domains` (single call, converts ALL domains at once)

**For single domain conversion:**
→ Use `convert_domain("DM")` for that specific domain

**For low-level transformations (DM/AE only):**
→ Use `transform_demographics` or `transform_adverse_events`

## Transformation Approach

1. Data must be loaded first (via load_data_from_s3)
2. For batch conversion: use convert_all_domains
3. For single domain: use convert_domain with domain code
4. Tools handle mapping generation, transformation, and validation automatically
5. Results are stored in memory for subsequent upload

Always ensure STUDYID, DOMAIN, USUBJID are populated correctly.""",
    "tools": TRANSFORMER_TOOLS,
}

CODE_GENERATOR_SUBAGENT = {
    "name": "code-generator",
    "description": "SAS and R code generation specialist. Use to generate reproducible transformation programs.",
    "system_prompt": """You are a Code Generation Agent specialized in creating SDTM transformation programs.

Generate both SAS and R versions for reproducibility.
Include proper headers, comments, and error handling.""",
    "tools": CODE_GENERATOR_TOOLS,
}

DATA_LOADER_SUBAGENT = {
    "name": "data-loader",
    "description": "Data warehouse loading specialist. Use to load SDTM data to Neo4j and upload to S3.",
    "system_prompt": """You are a Data Loading Agent specialized in data warehouse operations.

Your responsibilities:
1. Load SDTM domains to Neo4j as labeled nodes
2. Create relationships between patients and clinical data
3. Upload processed files to S3""",
    "tools": DATA_LOADER_TOOLS,
}

"""
SDTM Pipeline Tools
===================
Unified tools for the SDTM Deep Agent.

Combines:
- DeepAgents-specific tools (download, scan, analyze, transform)
- SDTM Chat tools (convert_domain, validate, knowledge base, web search)

These tools are available to the main orchestrator agent (in addition to
built-in DeepAgents tools like write_todos, read_file, etc.) and provide
SDTM-specific capabilities.
"""

import os
import json
import zipfile
from typing import Dict, Any, List, Optional
from datetime import datetime

import pandas as pd
from langchain_core.tools import tool

# Import all tools from sdtm_chat
from sdtm_pipeline.langgraph_chat.tools import (
    # Data loading
    load_data_from_s3,
    list_available_domains,
    preview_source_file,
    # Conversion
    convert_domain,
    validate_domain,
    get_conversion_status,
    # Output/Storage
    upload_sdtm_to_s3,
    load_sdtm_to_neo4j,
    save_sdtm_locally,
    # Knowledge base (Pinecone)
    search_sdtm_guidelines,
    get_business_rules,
    get_mapping_specification,
    get_validation_rules,
    get_sdtm_guidance,
    search_knowledge_base,
    get_controlled_terminology,
    # SDTM-IG 3.4 Web Reference
    fetch_sdtmig_specification,
    fetch_controlled_terminology,
    get_mapping_guidance_from_web,
    # Internet search (Tavily)
    search_internet,
)


# =============================================================================
# DATA INGESTION TOOLS (DeepAgents-specific)
# =============================================================================

@tool
def download_edc_data(s3_bucket: str, s3_key: str, local_dir: str) -> Dict[str, Any]:
    """
    Download EDC data from S3 and extract if ZIP.

    Args:
        s3_bucket: S3 bucket name
        s3_key: S3 object key
        local_dir: Local directory to download to

    Returns:
        Download result with extracted file paths
    """
    import boto3

    try:
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, os.path.basename(s3_key))

        # Download from S3
        s3 = boto3.client('s3')
        s3.download_file(s3_bucket, s3_key, local_path)

        files = []

        # Extract if ZIP
        if local_path.endswith('.zip'):
            extract_dir = os.path.join(local_dir, 'extracted')
            os.makedirs(extract_dir, exist_ok=True)

            with zipfile.ZipFile(local_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # Find all CSV files
            for root, dirs, filenames in os.walk(extract_dir):
                for filename in filenames:
                    if filename.endswith('.csv'):
                        filepath = os.path.join(root, filename)
                        size_kb = os.path.getsize(filepath) / 1024
                        files.append({
                            "name": filename,
                            "path": filepath,
                            "size_kb": round(size_kb, 2),
                        })
        else:
            files.append({
                "name": os.path.basename(local_path),
                "path": local_path,
                "size_kb": round(os.path.getsize(local_path) / 1024, 2),
            })

        return {
            "success": True,
            "files": files,
            "count": len(files),
            "download_path": local_path,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def scan_source_files(directory: str) -> Dict[str, Any]:
    """
    Scan directory for source data files and determine SDTM domain mappings.

    Args:
        directory: Directory to scan

    Returns:
        List of files with suggested SDTM domain mappings
    """
    # Domain mapping patterns
    domain_patterns = {
        'DEMO': 'DM', 'DEMOGRAPHY': 'DM',
        'AEVENT': 'AE', 'AE': 'AE', 'ADVERSE': 'AE',
        'VITALS': 'VS', 'VS': 'VS', 'VITAL': 'VS',
        'CHEMLAB': 'LB', 'HEMLAB': 'LB', 'LAB': 'LB', 'URINLAB': 'LB',
        'CONMEDS': 'CM', 'CM': 'CM', 'MEDICATION': 'CM',
        'DOSE': 'EX', 'EXPOSURE': 'EX', 'EX': 'EX',
        'CMPL': 'DS', 'DISPOSITION': 'DS', 'DS': 'DS',
        'GMEDHX': 'MH', 'MEDHIST': 'MH', 'MH': 'MH',
        'ECG': 'EG', 'EG': 'EG',
        'PHYSEXAM': 'PE', 'PE': 'PE',
    }

    files = []
    try:
        for root, dirs, filenames in os.walk(directory):
            for filename in filenames:
                if filename.endswith('.csv'):
                    filepath = os.path.join(root, filename)
                    size_kb = os.path.getsize(filepath) / 1024

                    # Determine target domain
                    base_name = filename.upper().replace('.CSV', '')
                    target_domain = None
                    for pattern, domain in domain_patterns.items():
                        if pattern in base_name:
                            target_domain = domain
                            break

                    files.append({
                        "name": filename,
                        "path": filepath,
                        "size_kb": round(size_kb, 2),
                        "target_domain": target_domain,
                        "mapped": target_domain is not None,
                    })

        # Sort by size (largest first)
        files.sort(key=lambda x: x['size_kb'], reverse=True)

        mapped = [f for f in files if f['mapped']]
        unmapped = [f for f in files if not f['mapped']]

        return {
            "success": True,
            "total_files": len(files),
            "mapped_files": len(mapped),
            "unmapped_files": len(unmapped),
            "files": files,
            "domains_found": list(set(f['target_domain'] for f in mapped if f['target_domain'])),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def analyze_source_file(file_path: str) -> Dict[str, Any]:
    """
    Analyze a source data file to understand its structure.

    Args:
        file_path: Path to the CSV file

    Returns:
        File analysis with column info and sample data
    """
    try:
        df = pd.read_csv(file_path)

        columns = []
        for col in df.columns:
            col_info = {
                "name": col,
                "dtype": str(df[col].dtype),
                "non_null": int(df[col].notna().sum()),
                "null_count": int(df[col].isna().sum()),
                "unique_values": int(df[col].nunique()),
                "sample_values": [str(v) for v in df[col].dropna().head(3).tolist()],
            }
            columns.append(col_info)

        return {
            "success": True,
            "file_name": os.path.basename(file_path),
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": columns,
            "memory_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# MAPPING GENERATION TOOLS
# =============================================================================

@tool
def generate_mapping_spec(
    source_file: str,
    target_domain: str,
    study_id: str,
) -> Dict[str, Any]:
    """
    Generate SDTM mapping specification for a source file.

    Uses column name matching and domain knowledge to create mappings.

    Args:
        source_file: Path to source CSV
        target_domain: Target SDTM domain code
        study_id: Study identifier

    Returns:
        Mapping specification with column mappings
    """
    try:
        df = pd.read_csv(source_file)
        domain = target_domain.upper()

        # Common mapping patterns by domain
        domain_mappings = {
            "DM": {
                "SUBJECT_ID": "SUBJID", "SUBJID": "SUBJID", "SUBJECT": "SUBJID",
                "AGE": "AGE", "SEX": "SEX", "GENDER": "SEX",
                "RACE": "RACE", "ETHNIC": "ETHNIC", "ETHNICITY": "ETHNIC",
                "COUNTRY": "COUNTRY", "SITE": "SITEID", "SITEID": "SITEID",
                "BIRTH_DATE": "BRTHDTC", "DOB": "BRTHDTC", "BRTHDTC": "BRTHDTC",
            },
            "AE": {
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID",
                "AETERM": "AETERM", "ADVERSE_EVENT": "AETERM", "AE_TERM": "AETERM",
                "AEDECOD": "AEDECOD", "PREFERRED_TERM": "AEDECOD", "PT": "AEDECOD",
                "START_DATE": "AESTDTC", "AESTDTC": "AESTDTC",
                "END_DATE": "AEENDTC", "AEENDTC": "AEENDTC",
                "SEVERITY": "AESEV", "AESEV": "AESEV",
                "SERIOUS": "AESER", "AESER": "AESER",
            },
            "VS": {
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID",
                "TEST_CODE": "VSTESTCD", "VSTESTCD": "VSTESTCD",
                "TEST_NAME": "VSTEST", "VSTEST": "VSTEST",
                "RESULT": "VSORRES", "VSORRES": "VSORRES", "VALUE": "VSORRES",
                "UNIT": "VSORRESU", "VSORRESU": "VSORRESU",
                "DATE": "VSDTC", "VSDTC": "VSDTC",
            },
            "LB": {
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID",
                "TEST_CODE": "LBTESTCD", "LBTESTCD": "LBTESTCD",
                "TEST_NAME": "LBTEST", "LBTEST": "LBTEST",
                "RESULT": "LBORRES", "LBORRES": "LBORRES", "VALUE": "LBORRES",
                "UNIT": "LBORRESU", "LBORRESU": "LBORRESU",
                "NORMAL_LOW": "LBSTNRLO", "LBSTNRLO": "LBSTNRLO",
                "NORMAL_HIGH": "LBSTNRHI", "LBSTNRHI": "LBSTNRHI",
            },
            "CM": {
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID",
                "MEDICATION": "CMTRT", "CMTRT": "CMTRT", "DRUG": "CMTRT",
                "DOSE": "CMDOSE", "CMDOSE": "CMDOSE",
                "UNIT": "CMDOSU", "CMDOSU": "CMDOSU",
                "START_DATE": "CMSTDTC", "CMSTDTC": "CMSTDTC",
                "END_DATE": "CMENDTC", "CMENDTC": "CMENDTC",
            },
        }

        patterns = domain_mappings.get(domain, {})
        column_mappings = []
        mapped_targets = set()

        for col in df.columns:
            col_upper = col.upper()
            target = patterns.get(col_upper) or patterns.get(col)

            if target and target not in mapped_targets:
                column_mappings.append({
                    "source_column": col,
                    "target_variable": target,
                    "transformation": None,
                    "comments": f"Direct mapping from {col}",
                })
                mapped_targets.add(target)

        # Add derived variables
        derivations = {}
        if domain == "DM":
            derivations["USUBJID"] = f"concat('{study_id}', '-', SUBJID)"
            derivations["STUDYID"] = f"'{study_id}'"
            derivations["DOMAIN"] = "'DM'"
        else:
            derivations["STUDYID"] = f"'{study_id}'"
            derivations["DOMAIN"] = f"'{domain}'"
            derivations[f"{domain}SEQ"] = "row_number()"

        spec = {
            "study_id": study_id,
            "source_domain": os.path.basename(source_file),
            "target_domain": domain,
            "column_mappings": column_mappings,
            "derivation_rules": derivations,
            "source_columns": list(df.columns),
            "generated_at": datetime.now().isoformat(),
        }

        return {
            "success": True,
            "mapping_spec": spec,
            "columns_mapped": len(column_mappings),
            "columns_unmapped": len(df.columns) - len(column_mappings),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def save_mapping_spec(mapping_spec: Dict[str, Any], output_path: str) -> Dict[str, Any]:
    """
    Save mapping specification to JSON file.

    Args:
        mapping_spec: Mapping specification dictionary
        output_path: Path to save JSON file

    Returns:
        Save result
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(mapping_spec, f, indent=2)

        return {
            "success": True,
            "output_path": output_path,
            "size_kb": round(os.path.getsize(output_path) / 1024, 2),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# TRANSFORMATION TOOLS
# =============================================================================

@tool
def transform_to_sdtm(
    source_file: str,
    mapping_spec: Dict[str, Any],
    output_path: str,
) -> Dict[str, Any]:
    """
    Transform source data to SDTM format using mapping specification.

    Args:
        source_file: Path to source CSV
        mapping_spec: Mapping specification with column mappings
        output_path: Path to save SDTM CSV

    Returns:
        Transformation result
    """
    try:
        df = pd.read_csv(source_file)
        records_in = len(df)

        domain = mapping_spec.get("target_domain", "UNKNOWN")
        study_id = mapping_spec.get("study_id", "UNKNOWN")

        # Create output dataframe
        sdtm = pd.DataFrame()

        # Apply standard identifiers
        sdtm["STUDYID"] = study_id
        sdtm["DOMAIN"] = domain

        # Apply column mappings
        for mapping in mapping_spec.get("column_mappings", []):
            src = mapping.get("source_column")
            tgt = mapping.get("target_variable")
            if src and tgt and src in df.columns:
                sdtm[tgt] = df[src]

        # Generate USUBJID if SUBJID exists
        if "SUBJID" in sdtm.columns and "USUBJID" not in sdtm.columns:
            sdtm["USUBJID"] = study_id + "-" + sdtm["SUBJID"].astype(str)
        elif "USUBJID" in sdtm.columns:
            # Ensure proper format
            if not sdtm["USUBJID"].str.contains("-").any():
                sdtm["USUBJID"] = study_id + "-" + sdtm["USUBJID"].astype(str)

        # Add sequence variable
        seq_var = f"{domain}SEQ"
        if seq_var not in sdtm.columns:
            sdtm[seq_var] = range(1, len(sdtm) + 1)

        # Reorder columns (identifiers first)
        id_cols = ["STUDYID", "DOMAIN", "USUBJID", seq_var]
        other_cols = [c for c in sdtm.columns if c not in id_cols]
        sdtm = sdtm[[c for c in id_cols if c in sdtm.columns] + other_cols]

        # Save output
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        sdtm.to_csv(output_path, index=False)

        return {
            "success": True,
            "domain": domain,
            "records_in": records_in,
            "records_out": len(sdtm),
            "columns_out": len(sdtm.columns),
            "output_path": output_path,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# REPORTING TOOLS
# =============================================================================

@tool
def generate_pipeline_report(
    study_id: str,
    transformation_results: List[Dict[str, Any]],
    validation_results: List[Dict[str, Any]],
    output_path: str,
) -> Dict[str, Any]:
    """
    Generate comprehensive pipeline execution report.

    Args:
        study_id: Study identifier
        transformation_results: List of transformation results
        validation_results: List of validation results
        output_path: Path to save report JSON

    Returns:
        Report generation result
    """
    try:
        # Calculate statistics
        total_records_in = sum(r.get("records_in", 0) for r in transformation_results)
        total_records_out = sum(r.get("records_out", 0) for r in transformation_results)
        successful_transforms = sum(1 for r in transformation_results if r.get("success"))

        total_errors = sum(r.get("error_count", 0) for r in validation_results)
        total_warnings = sum(r.get("warning_count", 0) for r in validation_results)
        passed_validations = sum(1 for r in validation_results if r.get("is_valid"))

        compliance_score = (passed_validations / len(validation_results) * 100) if validation_results else 0

        report = {
            "study_id": study_id,
            "generated_at": datetime.now().isoformat(),
            "status": "success" if compliance_score >= 95 else "requires_review",
            "summary": {
                "domains_processed": len(transformation_results),
                "successful_transformations": successful_transforms,
                "total_records_in": total_records_in,
                "total_records_out": total_records_out,
                "validation_errors": total_errors,
                "validation_warnings": total_warnings,
                "compliance_score": round(compliance_score, 1),
                "submission_ready": compliance_score >= 95 and total_errors == 0,
            },
            "transformations": transformation_results,
            "validations": validation_results,
        }

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        return {
            "success": True,
            "output_path": output_path,
            "compliance_score": compliance_score,
            "submission_ready": report["summary"]["submission_ready"],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# EXPORT ALL TOOLS - Combined DeepAgents + SDTM Chat Tools
# =============================================================================

# DeepAgents-specific tools for pipeline orchestration
DEEPAGENT_TOOLS = [
    # Data Ingestion (low-level)
    download_edc_data,
    scan_source_files,
    analyze_source_file,
    # Mapping Generation
    generate_mapping_spec,
    save_mapping_spec,
    # Transformation
    transform_to_sdtm,
    # Reporting
    generate_pipeline_report,
]

# SDTM Chat tools for interactive operations
CHAT_TOOLS = [
    # Data loading
    load_data_from_s3,
    list_available_domains,
    preview_source_file,
    # Conversion (high-level)
    convert_domain,
    validate_domain,
    get_conversion_status,
    # Output/Storage
    upload_sdtm_to_s3,
    load_sdtm_to_neo4j,
    save_sdtm_locally,
    # Knowledge base (Pinecone)
    search_sdtm_guidelines,
    get_business_rules,
    get_mapping_specification,
    get_validation_rules,
    get_sdtm_guidance,
    search_knowledge_base,
    get_controlled_terminology,
    # SDTM-IG 3.4 Web Reference
    fetch_sdtmig_specification,
    fetch_controlled_terminology,
    get_mapping_guidance_from_web,
    # Internet search (Tavily)
    search_internet,
]

# Combined tools for unified agent
SDTM_TOOLS = DEEPAGENT_TOOLS + CHAT_TOOLS

"""
SDTM Pipeline Tools (Async)
===========================
Unified async tools for the SDTM Deep Agent.

All tools are async to prevent blocking the ASGI event loop in LangGraph.

Combines:
- DeepAgents-specific tools (download, scan, analyze, transform)
- SDTM Chat tools (convert_domain, validate, knowledge base, web search)

These tools are available to the main orchestrator agent (in addition to
built-in DeepAgents tools like write_todos, read_file, etc.) and provide
SDTM-specific capabilities.
"""

import os
import json
import asyncio
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime

import pandas as pd
import aiofiles
import aiofiles.os
from langchain_core.tools import tool

# Async utilities
from .async_utils import (
    async_read_csv,
    async_to_csv,
    async_write_json,
    async_makedirs,
    async_getsize,
    async_walk,
    async_s3_download,
    async_s3_upload,
)

# Mapping engine for specification-driven transformations
from .mapping_engine import (
    SDTMTransformationEngine,
    MappingSpecificationParser,
    load_mapping_spec,
    transform_with_spec,
    MappingSpecification,
)

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
# DATA INGESTION TOOLS (Async)
# =============================================================================

@tool
async def download_edc_data(s3_bucket: str, s3_key: str, local_dir: str) -> Dict[str, Any]:
    """
    Download EDC data from S3 and extract if ZIP (async).

    Args:
        s3_bucket: S3 bucket name
        s3_key: S3 object key
        local_dir: Local directory to download to

    Returns:
        Download result with extracted file paths
    """
    import zipfile

    try:
        await async_makedirs(local_dir)
        local_path = os.path.join(local_dir, os.path.basename(s3_key))

        # Download from S3 (async)
        await async_s3_download(s3_bucket, s3_key, local_path)

        files = []

        # Extract if ZIP (run in thread since zipfile is blocking)
        if local_path.endswith('.zip'):
            extract_dir = os.path.join(local_dir, 'extracted')
            await async_makedirs(extract_dir)

            def _extract_and_scan():
                with zipfile.ZipFile(local_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)

                result_files = []
                for root, dirs, filenames in os.walk(extract_dir):
                    for filename in filenames:
                        if filename.endswith('.csv'):
                            filepath = os.path.join(root, filename)
                            size_kb = os.path.getsize(filepath) / 1024
                            result_files.append({
                                "name": filename,
                                "path": filepath,
                                "size_kb": round(size_kb, 2),
                            })
                return result_files

            files = await asyncio.to_thread(_extract_and_scan)
        else:
            size = await async_getsize(local_path)
            files.append({
                "name": os.path.basename(local_path),
                "path": local_path,
                "size_kb": round(size / 1024, 2),
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
async def scan_source_files(directory: str) -> Dict[str, Any]:
    """
    Scan directory for source data files and determine SDTM domain mappings (async).

    Args:
        directory: Directory to scan

    Returns:
        List of files with suggested SDTM domain mappings
    """
    # Domain mapping patterns for all 63 SDTM domains
    domain_patterns = {
        # Special Purpose Domains
        'COMMENT': 'CO', 'CO': 'CO',
        'DEMO': 'DM', 'DEMOGRAPHY': 'DM', 'DM': 'DM', 'DEMOGRAPHICS': 'DM',
        'SUBJELEM': 'SE', 'SE': 'SE', 'ELEMENT': 'SE',
        'SUBJVISIT': 'SV', 'SV': 'SV', 'VISIT': 'SV',

        # Interventions Domains
        'AGENT': 'AG', 'AG': 'AG', 'PROCAGENT': 'AG',
        'CONMEDS': 'CM', 'CM': 'CM', 'MEDICATION': 'CM', 'CONMED': 'CM',
        'EXPCOLL': 'EC', 'EC': 'EC', 'EXPOCOLL': 'EC',
        'DOSE': 'EX', 'EXPOSURE': 'EX', 'EX': 'EX', 'DOSING': 'EX',
        'MEAL': 'ML', 'ML': 'ML', 'MEALS': 'ML',
        'PROCEDURE': 'PR', 'PR': 'PR', 'PROC': 'PR',
        'SUBUSE': 'SU', 'SU': 'SU', 'SUBSTANCE': 'SU', 'ALCOHOL': 'SU', 'TOBACCO': 'SU',

        # Events Domains
        'AEVENT': 'AE', 'AE': 'AE', 'ADVERSE': 'AE', 'ADVERSEEVENT': 'AE',
        'CLNEVENT': 'CE', 'CE': 'CE', 'CLINICAL': 'CE',
        'CMPL': 'DS', 'DISPOSITION': 'DS', 'DS': 'DS', 'DISP': 'DS',
        'DEVIATION': 'DV', 'DV': 'DV', 'PROTDEV': 'DV',
        'HEALTHCARE': 'HO', 'HO': 'HO', 'ENCOUNTER': 'HO',
        'GMEDHX': 'MH', 'MEDHIST': 'MH', 'MH': 'MH', 'MEDHX': 'MH', 'SURGHX': 'MH',

        # Findings Domains
        'BIOSPECEVENT': 'BE', 'BE': 'BE',
        'BONEMEAS': 'BM', 'BM': 'BM', 'BONE': 'BM', 'DEXA': 'BM',
        'BIOSPECFIND': 'BS', 'BS': 'BS',
        'CELLPHENO': 'CP', 'CP': 'CP',
        'CARDIO': 'CV', 'CV': 'CV', 'CARDIOVASC': 'CV',
        'DRUGACCT': 'DA', 'DA': 'DA', 'ACCOUNTABILITY': 'DA',
        'DEATHDET': 'DD', 'DD': 'DD', 'DEATH': 'DD', 'DEATHGEN': 'DD',
        'ECG': 'EG', 'EG': 'EG', 'ELECTROCARD': 'EG',
        'FINDABOUT': 'FA', 'FA': 'FA',
        'FUNCTEST': 'FT', 'FT': 'FT', 'FUNCTION': 'FT',
        'GENOMICS': 'GF', 'GF': 'GF', 'GENO': 'GF', 'GENOLAB': 'GF',
        'IETEST': 'IE', 'IE': 'IE', 'INCEXC': 'IE', 'ELIG': 'IE', 'INEXCRT': 'IE',
        'IMMUNOGEN': 'IS', 'IS': 'IS',
        'CHEMLAB': 'LB', 'HEMLAB': 'LB', 'LAB': 'LB', 'URINLAB': 'LB', 'LB': 'LB', 'BIOLAB': 'LB',
        'MICROBIO': 'MB', 'MB': 'MB', 'MICROSPEC': 'MB',
        'MICROSCOP': 'MI', 'MI': 'MI',
        'MUSCULO': 'MK', 'MK': 'MK', 'MUSCULOSKEL': 'MK',
        'MORPHO': 'MO', 'MO': 'MO', 'MORPHOLOGY': 'MO',
        'MICROSUSCEP': 'MS', 'MS': 'MS', 'SUSCEPT': 'MS',
        'NERVOUS': 'NV', 'NV': 'NV', 'NEURO': 'NV',
        'OPHTHALM': 'OE', 'OE': 'OE', 'EYE': 'OE', 'OPHTHALMIC': 'OE',
        'OXYGEN': 'OX', 'OX': 'OX', 'O2SAT': 'OX', 'SPO2': 'OX',
        'PKCRF': 'PC', 'PC': 'PC', 'PKCONC': 'PC', 'PHARMACOKINETIC': 'PC',
        'PHYSEXAM': 'PE', 'PE': 'PE', 'PHYSICAL': 'PE',
        'PRINVINV': 'PI', 'PI': 'PI',
        'PKPARAM': 'PP', 'PP': 'PP',
        'QUEST': 'QS', 'QS': 'QS', 'QUESTIONNAIRE': 'QS', 'QSQS': 'QS',
        'RESP': 'RE', 'RE': 'RE', 'RESPIRATORY': 'RE',
        'REPRO': 'RP', 'RP': 'RP', 'REPRODUCTIVE': 'RP',
        'RESPONSE': 'RS', 'RS': 'RS', 'DISEASERESPONSE': 'RS',
        'SUBJCHAR': 'SC', 'SC': 'SC', 'CHARACTERISTIC': 'SC',
        'SKIN': 'SK', 'SK': 'SK',
        'SUBJSTAT': 'SS', 'SS': 'SS', 'STATUS': 'SS',
        'TUMOR': 'TR', 'TR': 'TR', 'LESION': 'TR', 'TUMR': 'TR', 'TARTUMR': 'TR', 'NONTUMR': 'TR',
        'TUMORID': 'TU', 'TU': 'TU',
        'URINARY': 'UR', 'UR': 'UR',
        'VITALS': 'VS', 'VS': 'VS', 'VITAL': 'VS', 'VITALSIGN': 'VS',

        # Trial Design Domains
        'TRIALARM': 'TA', 'TA': 'TA', 'ARM': 'TA',
        'TRIALDISEASE': 'TD', 'TD': 'TD',
        'TRIALELEMENT': 'TE', 'TE': 'TE',
        'TRIALINEXC': 'TI', 'TI': 'TI',
        'TRIALMILESTONE': 'TM', 'TM': 'TM',
        'TRIALSUMM': 'TS', 'TS': 'TS', 'SUMMARY': 'TS',
        'TRIALVISIT': 'TV', 'TV': 'TV',

        # Device Domains
        'DEVICEID': 'DI', 'DI': 'DI',
        'DEVICEPROP': 'DO', 'DO': 'DO',
        'DEVICEREL': 'DR', 'DR': 'DR',
        'DEVICEEVENT': 'DX', 'DX': 'DX',

        # Relationship Domain
        'RELREC': 'RELREC', 'RELATEDRECORDS': 'RELREC',
    }

    files = []
    try:
        # Use async walk
        walk_results = await async_walk(directory)

        for root, dirs, filenames in walk_results:
            for filename in filenames:
                if filename.endswith('.csv'):
                    filepath = os.path.join(root, filename)
                    size = await async_getsize(filepath)
                    size_kb = size / 1024

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
async def analyze_source_file(file_path: str) -> Dict[str, Any]:
    """
    Analyze a source data file to understand its structure (async).

    Args:
        file_path: Path to the CSV file

    Returns:
        File analysis with column info and sample data
    """
    try:
        # Async CSV read
        df = await async_read_csv(file_path)

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
# MAPPING GENERATION TOOLS (Async)
# =============================================================================

@tool
async def generate_mapping_spec(
    source_file: str,
    target_domain: str,
    study_id: str,
) -> Dict[str, Any]:
    """
    Generate SDTM mapping specification for a source file (async).

    Uses column name matching and domain knowledge to create mappings.

    Args:
        source_file: Path to source CSV
        target_domain: Target SDTM domain code
        study_id: Study identifier

    Returns:
        Mapping specification with column mappings
    """
    try:
        # Async CSV read
        df = await async_read_csv(source_file)
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
async def save_mapping_spec(mapping_spec: Dict[str, Any], output_path: str) -> Dict[str, Any]:
    """
    Save mapping specification to JSON file (async).

    Args:
        mapping_spec: Mapping specification dictionary
        output_path: Path to save JSON file

    Returns:
        Save result
    """
    try:
        # Async JSON write
        await async_write_json(mapping_spec, output_path)

        size = await async_getsize(output_path)
        return {
            "success": True,
            "output_path": output_path,
            "size_kb": round(size / 1024, 2),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# TRANSFORMATION TOOLS (Async)
# =============================================================================

@tool
async def transform_to_sdtm(
    source_file: str,
    mapping_spec: Dict[str, Any],
    output_path: str,
) -> Dict[str, Any]:
    """
    Transform source data to SDTM format using mapping specification (async).

    Args:
        source_file: Path to source CSV
        mapping_spec: Mapping specification with column mappings
        output_path: Path to save SDTM CSV

    Returns:
        Transformation result
    """
    try:
        # Async CSV read
        df = await async_read_csv(source_file)
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

        # Async CSV write
        await async_to_csv(sdtm, output_path, index=False)

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
# MAPPING SPECIFICATION-DRIVEN TOOLS (Async)
# =============================================================================

# Global engine instance for multi-step operations
_mapping_engine: Optional[SDTMTransformationEngine] = None


@tool
async def load_mapping_specification(spec_path: str) -> Dict[str, Any]:
    """
    Load an SDTM mapping specification file (Excel format).

    The mapping specification defines transformation rules for converting
    source data to SDTM domains. It supports functions like:
    - ASSIGN("value") - Assign constant value
    - CONCAT(a, b, ...) - Concatenate values
    - SUBSTR(field, start, length) - Extract substring
    - IF(condition, true_val, false_val) - Conditional logic
    - ISO8601DATEFORMAT(field, format) - Date conversion
    - FORMAT(field, codelist) - Codelist lookup
    - UPCASE(field), TRIM(field), COMPRESS(field) - String manipulation
    - set to VARIABLE - Direct column mapping

    Args:
        spec_path: Path to the mapping specification file (.xls, .xlsx)

    Returns:
        Information about the loaded specification including available domains
    """
    global _mapping_engine

    try:
        _mapping_engine = SDTMTransformationEngine()
        spec = await _mapping_engine.load_specification(spec_path)

        domains_info = []
        for domain_code, domain_mapping in spec.domains.items():
            domains_info.append({
                "domain": domain_code,
                "label": domain_mapping.label,
                "num_variables": len(domain_mapping.variables),
                "source_datasets": domain_mapping.source_datasets,
                "required_vars": [v.variable for v in domain_mapping.variables if v.core == 'req'],
            })

        return {
            "success": True,
            "spec_path": spec_path,
            "study_id": spec.study_id,
            "sponsor": spec.sponsor,
            "protocol": spec.protocol,
            "domains_available": len(spec.domains),
            "domains": domains_info,
            "raw_datasets_defined": list(spec.raw_datasets.keys()),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
async def transform_domain_with_spec(
    domain: str,
    source_files: Dict[str, str],
    output_path: str,
    study_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Transform source data to an SDTM domain using the loaded mapping specification.

    Uses the transformation rules defined in the mapping spec to convert
    source data. The spec must be loaded first with load_mapping_specification.

    Args:
        domain: Target SDTM domain code (e.g., 'DM', 'AE', 'VS', 'LB')
        source_files: Dictionary mapping dataset names to file paths
                      e.g., {"DEMO": "/data/demo.csv", "VISITS": "/data/visits.csv"}
        output_path: Path to save the transformed SDTM CSV
        study_id: Optional study identifier (overrides value from spec)

    Returns:
        Transformation result with record counts and validation info
    """
    global _mapping_engine

    if _mapping_engine is None:
        return {
            "success": False,
            "error": "No mapping specification loaded. Call load_mapping_specification first."
        }

    try:
        # Load source data files
        source_data = {}
        total_source_records = 0

        for ds_name, file_path in source_files.items():
            df = await async_read_csv(file_path)
            source_data[ds_name] = df
            total_source_records += len(df)

        # Transform using the engine
        result_df = await _mapping_engine.transform_domain(
            domain=domain,
            source_data=source_data,
            study_id=study_id,
        )

        # Save output
        await async_to_csv(result_df, output_path, index=False)

        # Calculate statistics
        null_counts = result_df.isnull().sum().to_dict()
        columns_with_nulls = {k: v for k, v in null_counts.items() if v > 0}

        return {
            "success": True,
            "domain": domain.upper(),
            "source_datasets": list(source_files.keys()),
            "source_records": total_source_records,
            "records_out": len(result_df),
            "columns_out": len(result_df.columns),
            "output_columns": list(result_df.columns),
            "columns_with_nulls": columns_with_nulls,
            "output_path": output_path,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
async def get_domain_mapping_details(domain: str) -> Dict[str, Any]:
    """
    Get detailed mapping information for a specific SDTM domain.

    Shows all variable mappings, transformation rules, and source requirements
    for the specified domain. The spec must be loaded first.

    Args:
        domain: SDTM domain code (e.g., 'DM', 'AE', 'VS')

    Returns:
        Detailed mapping information for the domain
    """
    global _mapping_engine

    if _mapping_engine is None:
        return {
            "success": False,
            "error": "No mapping specification loaded. Call load_mapping_specification first."
        }

    try:
        info = _mapping_engine.get_domain_info(domain)
        if not info:
            return {
                "success": False,
                "error": f"Domain {domain} not found in loaded specification"
            }

        # Add more detail about variable mappings
        spec = _mapping_engine._spec
        domain_mapping = spec.domains[domain.upper()]

        variables_detail = []
        for v in domain_mapping.variables:
            variables_detail.append({
                "variable": v.variable,
                "label": v.label,
                "data_type": v.data_type,
                "length": v.length,
                "core": v.core,
                "role": v.role,
                "source_datasets": v.source_datasets,
                "source_variables": v.source_variables,
                "rule": v.rule,
                "controlled_terms": v.controlled_terms,
            })

        return {
            "success": True,
            "domain": domain.upper(),
            "label": info['label'],
            "num_variables": info['num_variables'],
            "source_datasets_required": info['source_datasets'],
            "variables": variables_detail,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
async def transform_domain_standalone(
    spec_path: str,
    domain: str,
    source_files: Dict[str, str],
    output_path: str,
    study_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Transform source data to SDTM using a mapping specification (standalone).

    This is a single-call version that loads the spec and transforms in one step.
    Use this for one-off transformations. For batch processing multiple domains,
    use load_mapping_specification + transform_domain_with_spec.

    Args:
        spec_path: Path to the mapping specification file (.xls, .xlsx)
        domain: Target SDTM domain code
        source_files: Dictionary mapping dataset names to file paths
        output_path: Path to save the transformed SDTM CSV
        study_id: Optional study identifier override

    Returns:
        Transformation result
    """
    try:
        # Load source data
        source_data = {}
        for ds_name, file_path in source_files.items():
            df = await async_read_csv(file_path)
            source_data[ds_name] = df

        # Transform using convenience function
        result_df = await transform_with_spec(
            spec_path=spec_path,
            domain=domain,
            source_data=source_data,
            study_id=study_id,
        )

        # Save output
        await async_to_csv(result_df, output_path, index=False)

        return {
            "success": True,
            "domain": domain.upper(),
            "records_out": len(result_df),
            "columns_out": len(result_df.columns),
            "output_columns": list(result_df.columns),
            "output_path": output_path,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
async def list_mapping_spec_domains(spec_path: Optional[str] = None) -> Dict[str, Any]:
    """
    List all domains available in a mapping specification.

    Either uses a loaded spec or loads from the provided path.

    Args:
        spec_path: Optional path to mapping spec file. If not provided,
                   uses the currently loaded specification.

    Returns:
        List of available domains with basic info
    """
    global _mapping_engine

    try:
        if spec_path:
            # Load a new spec temporarily
            parser = MappingSpecificationParser()
            spec = await parser.parse_excel(spec_path)
        elif _mapping_engine and _mapping_engine._spec:
            spec = _mapping_engine._spec
        else:
            return {
                "success": False,
                "error": "No spec_path provided and no specification loaded."
            }

        domains = []
        for domain_code, domain_mapping in spec.domains.items():
            required_vars = [v.variable for v in domain_mapping.variables if v.core.lower() == 'req']
            expected_vars = [v.variable for v in domain_mapping.variables if v.core.lower() == 'exp']

            domains.append({
                "domain": domain_code,
                "label": domain_mapping.label,
                "total_variables": len(domain_mapping.variables),
                "required_variables": len(required_vars),
                "expected_variables": len(expected_vars),
                "source_datasets": domain_mapping.source_datasets,
            })

        return {
            "success": True,
            "study_id": spec.study_id,
            "total_domains": len(domains),
            "domains": domains,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# REPORTING TOOLS (Async)
# =============================================================================

@tool
async def generate_pipeline_report(
    study_id: str,
    transformation_results: List[Dict[str, Any]],
    validation_results: List[Dict[str, Any]],
    output_path: str,
) -> Dict[str, Any]:
    """
    Generate comprehensive pipeline execution report (async).

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

        # Async JSON write
        await async_write_json(report, output_path)

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

# DeepAgents-specific tools for pipeline orchestration (now async)
DEEPAGENT_TOOLS = [
    # Data Ingestion (async)
    download_edc_data,
    scan_source_files,
    analyze_source_file,
    # Mapping Generation (async)
    generate_mapping_spec,
    save_mapping_spec,
    # Transformation (async) - Basic
    transform_to_sdtm,
    # Mapping Specification-Driven Transformation (async)
    load_mapping_specification,
    transform_domain_with_spec,
    get_domain_mapping_details,
    transform_domain_standalone,
    list_mapping_spec_domains,
    # Reporting (async)
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

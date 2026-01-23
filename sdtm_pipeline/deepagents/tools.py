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
# BASH EXECUTION TOOL (Async)
# =============================================================================

@tool
async def execute_bash(command: str, timeout: int = 120, working_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute a bash command asynchronously.

    Args:
        command: The bash command to execute
        timeout: Maximum execution time in seconds (default: 120)
        working_dir: Working directory for command execution (optional)

    Returns:
        Dict with stdout, stderr, return_code, and success status
    """
    import shlex

    # Safety checks - block dangerous commands
    dangerous_patterns = [
        "rm -rf /", "rm -rf /*", "mkfs", "dd if=", ":(){:|:&};:",
        "chmod -R 777 /", "chown -R", "> /dev/sda", "wget | sh",
        "curl | sh", "eval", "$(", "`",
    ]

    command_lower = command.lower()
    for pattern in dangerous_patterns:
        if pattern in command_lower:
            return {
                "success": False,
                "error": f"Blocked dangerous command pattern: {pattern}",
                "stdout": "",
                "stderr": "",
                "return_code": -1,
            }

    try:
        # Create subprocess
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir,
        )

        # Wait for completion with timeout
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds",
                "stdout": "",
                "stderr": "",
                "return_code": -1,
            }

        # Decode output
        stdout_str = stdout.decode("utf-8", errors="replace").strip()
        stderr_str = stderr.decode("utf-8", errors="replace").strip()

        # Truncate if too long
        max_output = 50000
        if len(stdout_str) > max_output:
            stdout_str = stdout_str[:max_output] + f"\n... (truncated, {len(stdout_str)} total chars)"
        if len(stderr_str) > max_output:
            stderr_str = stderr_str[:max_output] + f"\n... (truncated, {len(stderr_str)} total chars)"

        return {
            "success": process.returncode == 0,
            "stdout": stdout_str,
            "stderr": stderr_str,
            "return_code": process.returncode,
            "command": command,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "stdout": "",
            "stderr": "",
            "return_code": -1,
        }


# =============================================================================
# FRONTEND CHART TOOLS (Recharts-Compatible)
# =============================================================================
# These tools generate chart data in a format compatible with the frontend's
# Recharts-based ChartRenderer. The agent should include the returned
# "chart_markdown" in its response to display charts in the frontend.
#
# Frontend expects charts as markdown code blocks:
#   ```chart
#   {"type": "bar", "data": [...], "title": "...", ...}
#   ```

@tool
async def create_bar_chart(
    data: List[Dict[str, Any]],
    title: str,
    x_key: str = "name",
    y_key: str = "value",
    show_legend: bool = False,
    show_grid: bool = True,
    stacked: bool = False,
    colors: Optional[List[str]] = None,
    series: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Create a bar chart for display in the frontend.

    The returned chart_markdown should be included in your response to render
    the chart in the frontend.

    Args:
        data: List of data objects, e.g., [{"name": "DM", "value": 95}, {"name": "AE", "value": 87}]
        title: Chart title
        x_key: Key in data objects for x-axis categories (default: "name")
        y_key: Key in data objects for y-axis values (default: "value")
        show_legend: Whether to show legend
        show_grid: Whether to show grid lines
        stacked: Whether to stack bars (for multi-series)
        colors: Optional list of colors for the bars
        series: Optional list of series for multi-series charts
                e.g., [{"dataKey": "score", "name": "Score"}, {"dataKey": "errors", "name": "Errors"}]

    Returns:
        Dict with chart_markdown to include in response, and chart_data for reference

    Example:
        result = await create_bar_chart(
            data=[{"name": "DM", "value": 95}, {"name": "AE", "value": 87}],
            title="Domain Compliance Scores"
        )
        # Include result["chart_markdown"] in your response
    """
    chart_data = {
        "type": "bar",
        "title": title,
        "data": data,
        "xKey": x_key,
        "yKey": y_key,
        "showLegend": show_legend,
        "showGrid": show_grid,
        "stacked": stacked,
    }

    if colors:
        chart_data["colors"] = colors
    if series:
        chart_data["series"] = series

    # Return the chart data - agent should format as markdown code block
    return {
        "success": True,
        "type": "bar",
        "chart": chart_data,
        "instructions": "To display this chart, include a code block in your response with language 'chart' containing this JSON data."
    }


@tool
async def create_line_chart(
    data: List[Dict[str, Any]],
    title: str,
    x_key: str = "name",
    y_key: str = "value",
    show_legend: bool = True,
    show_grid: bool = True,
    colors: Optional[List[str]] = None,
    series: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Create a line chart for display in the frontend.

    Args:
        data: List of data objects with x and y values
              e.g., [{"week": "Week1", "score": 80}, {"week": "Week2", "score": 90}]
        title: Chart title
        x_key: Key for x-axis (default: "name")
        y_key: Key for y-axis (default: "value")
        show_legend: Whether to show legend
        show_grid: Whether to show grid lines
        colors: Optional list of colors
        series: For multi-line charts, list of series definitions
                e.g., [{"dataKey": "dm_score", "name": "DM"}, {"dataKey": "ae_score", "name": "AE"}]

    Returns:
        Dict with chart_markdown to include in response

    Example:
        result = await create_line_chart(
            data=[{"week": "W1", "dm": 80, "ae": 70}, {"week": "W2", "dm": 90, "ae": 85}],
            title="Compliance Over Time",
            x_key="week",
            series=[{"dataKey": "dm", "name": "DM"}, {"dataKey": "ae", "name": "AE"}]
        )
    """
    chart_data = {
        "type": "line",
        "title": title,
        "data": data,
        "xKey": x_key,
        "yKey": y_key,
        "showLegend": show_legend,
        "showGrid": show_grid,
    }

    if colors:
        chart_data["colors"] = colors
    if series:
        chart_data["series"] = series

    # Return the chart data - agent should format as markdown code block
    return {
        "success": True,
        "type": "line",
        "chart": chart_data,
        "instructions": "To display this chart, include a code block in your response with language 'chart' containing this JSON data."
    }


@tool
async def create_pie_chart(
    data: List[Dict[str, Any]],
    title: str,
    name_key: str = "name",
    value_key: str = "value",
    show_legend: bool = True,
    colors: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create a pie/donut chart for display in the frontend.

    Args:
        data: List of data objects with name and value
              e.g., [{"name": "Pass", "value": 85}, {"name": "Fail", "value": 10}, {"name": "Warning", "value": 5}]
        title: Chart title
        name_key: Key for segment names (default: "name")
        value_key: Key for segment values (default: "value")
        show_legend: Whether to show legend
        colors: Optional list of colors for segments

    Returns:
        Dict with chart_markdown to include in response

    Example:
        result = await create_pie_chart(
            data=[{"name": "Pass", "value": 85}, {"name": "Fail", "value": 15}],
            title="Validation Results"
        )
    """
    chart_data = {
        "type": "pie",
        "title": title,
        "data": data,
        "xKey": name_key,
        "yKey": value_key,
        "showLegend": show_legend,
    }

    if colors:
        chart_data["colors"] = colors

    # Return the chart data - agent should format as markdown code block
    return {
        "success": True,
        "type": "pie",
        "chart": chart_data,
        "instructions": "To display this chart, include a code block in your response with language 'chart' containing this JSON data."
    }


@tool
async def create_area_chart(
    data: List[Dict[str, Any]],
    title: str,
    x_key: str = "name",
    y_key: str = "value",
    show_legend: bool = True,
    show_grid: bool = True,
    stacked: bool = False,
    colors: Optional[List[str]] = None,
    series: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Create an area chart for display in the frontend.

    Args:
        data: List of data objects
        title: Chart title
        x_key: Key for x-axis (default: "name")
        y_key: Key for y-axis (default: "value")
        show_legend: Whether to show legend
        show_grid: Whether to show grid lines
        stacked: Whether to stack areas
        colors: Optional list of colors
        series: For multi-area charts, list of series definitions

    Returns:
        Dict with chart_markdown to include in response
    """
    chart_data = {
        "type": "area",
        "title": title,
        "data": data,
        "xKey": x_key,
        "yKey": y_key,
        "showLegend": show_legend,
        "showGrid": show_grid,
        "stacked": stacked,
    }

    if colors:
        chart_data["colors"] = colors
    if series:
        chart_data["series"] = series

    # Return the chart data - agent should format as markdown code block
    return {
        "success": True,
        "type": "area",
        "chart": chart_data,
        "instructions": "To display this chart, include a code block in your response with language 'chart' containing this JSON data."
    }


@tool
async def create_scatter_chart(
    data: List[Dict[str, Any]],
    title: str,
    x_key: str = "x",
    y_key: str = "y",
    show_legend: bool = True,
    show_grid: bool = True,
    colors: Optional[List[str]] = None,
    series: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Create a scatter plot for display in the frontend.

    Args:
        data: List of data objects with x, y values
              e.g., [{"x": 10, "y": 20}, {"x": 15, "y": 25}]
        title: Chart title
        x_key: Key for x values (default: "x")
        y_key: Key for y values (default: "y")
        show_legend: Whether to show legend
        show_grid: Whether to show grid lines
        colors: Optional list of colors
        series: For multi-series, categorize by a "category" field in data

    Returns:
        Dict with chart_markdown to include in response
    """
    chart_data = {
        "type": "scatter",
        "title": title,
        "data": data,
        "xKey": x_key,
        "yKey": y_key,
        "showLegend": show_legend,
        "showGrid": show_grid,
    }

    if colors:
        chart_data["colors"] = colors
    if series:
        chart_data["series"] = series

    # Return the chart data - agent should format as markdown code block
    return {
        "success": True,
        "type": "scatter",
        "chart": chart_data,
        "instructions": "To display this chart, include a code block in your response with language 'chart' containing this JSON data."
    }


@tool
async def create_radar_chart(
    data: List[Dict[str, Any]],
    title: str,
    name_key: str = "name",
    value_key: str = "value",
    show_legend: bool = True,
    colors: Optional[List[str]] = None,
    series: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Create a radar chart for display in the frontend.

    Args:
        data: List of data objects representing axes
              e.g., [{"name": "Accuracy", "value": 90}, {"name": "Speed", "value": 85}]
        title: Chart title
        name_key: Key for axis names (default: "name")
        value_key: Key for values (default: "value")
        show_legend: Whether to show legend
        colors: Optional list of colors
        series: For multi-series radar, define multiple value keys

    Returns:
        Dict with chart_markdown to include in response
    """
    chart_data = {
        "type": "radar",
        "title": title,
        "data": data,
        "xKey": name_key,
        "yKey": value_key,
        "showLegend": show_legend,
    }

    if colors:
        chart_data["colors"] = colors
    if series:
        chart_data["series"] = series

    # Return the chart data - agent should format as markdown code block
    return {
        "success": True,
        "type": "radar",
        "chart": chart_data,
        "instructions": "To display this chart, include a code block in your response with language 'chart' containing this JSON data."
    }


@tool
async def create_funnel_chart(
    data: List[Dict[str, Any]],
    title: str,
    name_key: str = "name",
    value_key: str = "value",
    show_legend: bool = True,
    colors: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create a funnel chart for display in the frontend.

    Args:
        data: List of data objects in funnel order (largest to smallest)
              e.g., [{"name": "Visits", "value": 1000}, {"name": "Clicks", "value": 500}]
        title: Chart title
        name_key: Key for stage names (default: "name")
        value_key: Key for values (default: "value")
        show_legend: Whether to show legend
        colors: Optional list of colors

    Returns:
        Dict with chart_markdown to include in response
    """
    chart_data = {
        "type": "funnel",
        "title": title,
        "data": data,
        "xKey": name_key,
        "yKey": value_key,
        "showLegend": show_legend,
    }

    if colors:
        chart_data["colors"] = colors

    # Return the chart data - agent should format as markdown code block
    return {
        "success": True,
        "type": "funnel",
        "chart": chart_data,
        "instructions": "To display this chart, include a code block in your response with language 'chart' containing this JSON data."
    }


@tool
async def create_composed_chart(
    data: List[Dict[str, Any]],
    title: str,
    x_key: str = "name",
    series: List[Dict[str, str]] = None,
    show_legend: bool = True,
    show_grid: bool = True,
    colors: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create a composed chart with multiple chart types (bar, line, area) in one.

    Args:
        data: List of data objects with all series values
        title: Chart title
        x_key: Key for x-axis (default: "name")
        series: List of series with type specification
                e.g., [
                    {"dataKey": "records", "name": "Records", "type": "bar"},
                    {"dataKey": "score", "name": "Score", "type": "line"},
                    {"dataKey": "trend", "name": "Trend", "type": "area"}
                ]
        show_legend: Whether to show legend
        show_grid: Whether to show grid lines
        colors: Optional list of colors

    Returns:
        Dict with chart_markdown to include in response

    Example:
        result = await create_composed_chart(
            data=[
                {"name": "DM", "records": 100, "score": 95},
                {"name": "AE", "records": 80, "score": 87}
            ],
            title="Domain Overview",
            series=[
                {"dataKey": "records", "name": "Records", "type": "bar"},
                {"dataKey": "score", "name": "Score (%)", "type": "line"}
            ]
        )
    """
    if not series:
        return {"success": False, "error": "series parameter is required for composed charts"}

    chart_data = {
        "type": "composed",
        "title": title,
        "data": data,
        "xKey": x_key,
        "series": series,
        "showLegend": show_legend,
        "showGrid": show_grid,
    }

    if colors:
        chart_data["colors"] = colors

    # Return the chart data - agent should format as markdown code block
    return {
        "success": True,
        "type": "composed",
        "chart": chart_data,
        "instructions": "To display this chart, include a code block in your response with language 'chart' containing this JSON data."
    }


@tool
async def create_sdtm_validation_dashboard(
    domains: Dict[str, Dict[str, Any]],
    overall_score: float,
    study_id: str = "STUDY"
) -> Dict[str, Any]:
    """
    Create a comprehensive SDTM validation dashboard with multiple charts.
    Returns multiple chart markdown blocks that can be included in the response.

    Args:
        domains: Dict of domain validation results
                 e.g., {"DM": {"score": 95, "errors": 2, "warnings": 5}, "AE": {"score": 87, "errors": 5, "warnings": 10}}
        overall_score: Overall compliance score (0-100)
        study_id: Study identifier for titles

    Returns:
        Dict with dashboard_markdown containing all charts

    Example:
        result = await create_sdtm_validation_dashboard(
            domains={
                "DM": {"score": 95, "errors": 2, "warnings": 5},
                "AE": {"score": 87, "errors": 5, "warnings": 10},
                "VS": {"score": 92, "errors": 3, "warnings": 8}
            },
            overall_score=91.3,
            study_id="ABC-001"
        )
    """
    if not domains:
        return {"success": False, "error": "No domain data provided"}

    # Prepare data for charts
    domain_names = list(domains.keys())
    scores_data = [{"name": d, "value": domains[d].get("score", 0)} for d in domain_names]

    issues_data = [
        {"name": d, "errors": domains[d].get("errors", 0), "warnings": domains[d].get("warnings", 0)}
        for d in domain_names
    ]

    total_errors = sum(d.get("errors", 0) for d in domains.values())
    total_warnings = sum(d.get("warnings", 0) for d in domains.values())
    total_pass = max(0, len(domains) * 100 - total_errors - total_warnings)

    distribution_data = [
        {"name": "Pass", "value": total_pass},
        {"name": "Errors", "value": total_errors},
        {"name": "Warnings", "value": total_warnings}
    ]

    # Create chart 1: Compliance Scores Bar Chart
    chart1 = {
        "type": "bar",
        "title": f"{study_id} - Compliance Score by Domain",
        "data": scores_data,
        "xKey": "name",
        "yKey": "value",
        "showGrid": True,
        "showLegend": False,
        "colors": ["#00CC96" if s["value"] >= 90 else "#FFA15A" if s["value"] >= 80 else "#EF553B" for s in scores_data]
    }

    # Create chart 2: Issues Stacked Bar Chart
    chart2 = {
        "type": "bar",
        "title": "Issues by Domain",
        "data": issues_data,
        "xKey": "name",
        "series": [
            {"dataKey": "errors", "name": "Errors"},
            {"dataKey": "warnings", "name": "Warnings"}
        ],
        "showGrid": True,
        "showLegend": True,
        "stacked": True,
        "colors": ["#EF553B", "#FFA15A"]
    }

    # Create chart 3: Distribution Pie Chart
    chart3 = {
        "type": "pie",
        "title": "Issue Distribution",
        "data": distribution_data,
        "xKey": "name",
        "yKey": "value",
        "showLegend": True,
        "colors": ["#00CC96", "#EF553B", "#FFA15A"]
    }

    # Return individual charts for the agent to format
    return {
        "success": True,
        "type": "dashboard",
        "study_id": study_id,
        "overall_score": overall_score,
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "domains_count": len(domains),
        "submission_ready": overall_score >= 90 and total_errors == 0,
        "charts": {
            "compliance_scores": chart1,
            "issues_by_domain": chart2,
            "issue_distribution": chart3
        },
        "instructions": "Create a dashboard with these 3 charts. For each chart, write a ```chart code block with the JSON data on a single line."
    }


# Visualization tools list (Frontend-compatible)
VISUALIZATION_TOOLS = [
    create_bar_chart,
    create_line_chart,
    create_pie_chart,
    create_area_chart,
    create_scatter_chart,
    create_radar_chart,
    create_funnel_chart,
    create_composed_chart,
    create_sdtm_validation_dashboard,
]


# =============================================================================
# WEB SCRAPING & CRAWLING TOOLS (Firecrawl - Async)
# =============================================================================

@tool
async def scrape_webpage(
    url: str,
    include_markdown: bool = True,
    include_html: bool = False,
    only_main_content: bool = True,
    wait_for: int = 0
) -> Dict[str, Any]:
    """
    Scrape a single webpage and extract its content using Firecrawl.

    Args:
        url: The URL to scrape
        include_markdown: Include markdown format in output (default: True)
        include_html: Include HTML format in output (default: False)
        only_main_content: If True, extract only main content (skip nav, footer, etc.)
        wait_for: Milliseconds to wait for dynamic content to load (0 for static pages)

    Returns:
        Dict with scraped content, metadata, and success status

    Example:
        result = await scrape_webpage("https://clinicaltrials.gov/study/NCT12345678")
    """
    try:
        from firecrawl import FirecrawlApp

        api_key = os.getenv("FIRECRAWL_API_KEY", "fc-4a39356cf081453f96726af430e24ae1")
        app = FirecrawlApp(api_key=api_key)

        # Build format list
        formats = []
        if include_markdown:
            formats.append("markdown")
        if include_html:
            formats.append("html")
        if not formats:
            formats = ["markdown"]

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: app.scrape(
                url,
                formats=formats,
                only_main_content=only_main_content,
                wait_for=wait_for if wait_for > 0 else None
            )
        )

        # Extract content from Document object
        content = {}
        if hasattr(result, 'markdown'):
            content["markdown"] = result.markdown or ""
        if hasattr(result, 'html'):
            content["html"] = result.html or ""

        metadata = {}
        if hasattr(result, 'metadata') and result.metadata:
            metadata = {
                "title": getattr(result.metadata, 'title', '') or '',
                "description": getattr(result.metadata, 'description', '') or '',
                "url": getattr(result.metadata, 'url', url) or url,
            }

        return {
            "success": True,
            "url": url,
            "title": metadata.get("title", ""),
            "description": metadata.get("description", ""),
            "content": content,
            "metadata": metadata,
            "content_length": len(content.get("markdown", "") or content.get("html", "")),
        }

    except ImportError:
        return {"success": False, "error": "Firecrawl not installed. Run: pip install firecrawl-py"}
    except Exception as e:
        return {"success": False, "url": url, "error": str(e)}


@tool
async def crawl_website(
    url: str,
    max_pages: int = 10,
    max_depth: int = 2,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Crawl a website starting from a URL, following links to scrape multiple pages.

    Args:
        url: Starting URL for the crawl
        max_pages: Maximum number of pages to crawl (default: 10)
        max_depth: Maximum link depth from start URL (default: 2)
        include_patterns: URL patterns to include (e.g., ["/docs/*", "/api/*"])
        exclude_patterns: URL patterns to exclude (e.g., ["/login", "/admin/*"])
        output_dir: Optional directory to save crawled content as files

    Returns:
        Dict with crawled pages, content, and statistics

    Example:
        result = await crawl_website(
            "https://cdisc.org/standards/foundational/sdtm",
            max_pages=20,
            include_patterns=["/standards/*"]
        )
    """
    try:
        from firecrawl import FirecrawlApp
        from firecrawl.v2.types import ScrapeOptions

        api_key = os.getenv("FIRECRAWL_API_KEY", "fc-4a39356cf081453f96726af430e24ae1")
        app = FirecrawlApp(api_key=api_key)

        # Build scrape options
        scrape_opts = ScrapeOptions(formats=["markdown"], only_main_content=True)

        # Start crawl (async crawl with polling)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: app.crawl(
                url,
                limit=max_pages,
                max_discovery_depth=max_depth,
                include_paths=include_patterns,
                exclude_paths=exclude_patterns,
                scrape_options=scrape_opts,
                poll_interval=5
            )
        )

        # Process results from CrawlJob
        pages = []
        total_content_length = 0

        # Get data from CrawlJob object
        crawl_data = result.data if hasattr(result, 'data') else []

        for page in crawl_data:
            markdown_content = page.markdown if hasattr(page, 'markdown') else ""
            page_url = ""
            page_title = ""

            if hasattr(page, 'metadata') and page.metadata:
                page_url = getattr(page.metadata, 'url', '') or getattr(page.metadata, 'sourceURL', '')
                page_title = getattr(page.metadata, 'title', '')

            page_info = {
                "url": page_url,
                "title": page_title,
                "content_length": len(markdown_content),
                "markdown": markdown_content[:2000] + "..." if len(markdown_content) > 2000 else markdown_content
            }
            pages.append(page_info)
            total_content_length += len(markdown_content)

        # Save to files if output_dir specified
        saved_files = []
        if output_dir and pages:
            await async_makedirs(output_dir)
            for i, page in enumerate(pages):
                filename = f"page_{i+1}.md"
                filepath = os.path.join(output_dir, filename)
                async with aiofiles.open(filepath, 'w') as f:
                    await f.write(f"# {page['title']}\n\nSource: {page['url']}\n\n---\n\n{page['markdown']}")
                saved_files.append(filepath)

        return {
            "success": True,
            "start_url": url,
            "pages_crawled": len(pages),
            "total_content_length": total_content_length,
            "pages": pages,
            "saved_files": saved_files if saved_files else None,
        }

    except ImportError:
        return {"success": False, "error": "Firecrawl not installed. Run: pip install firecrawl-py"}
    except Exception as e:
        return {"success": False, "url": url, "error": str(e)}


@tool
async def map_website(
    url: str,
    search_query: Optional[str] = None,
    include_subdomains: bool = False,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Map a website to discover all URLs/pages without scraping content.
    Useful for understanding site structure before targeted scraping.

    Args:
        url: Base URL to map
        search_query: Optional search term to filter URLs
        include_subdomains: Whether to include subdomains
        limit: Maximum number of URLs to return

    Returns:
        Dict with discovered URLs and site structure

    Example:
        result = await map_website("https://fda.gov", search_query="clinical trials")
    """
    try:
        from firecrawl import FirecrawlApp

        api_key = os.getenv("FIRECRAWL_API_KEY", "fc-4a39356cf081453f96726af430e24ae1")
        app = FirecrawlApp(api_key=api_key)

        # Run mapping
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: app.map(
                url,
                search=search_query,
                include_subdomains=include_subdomains,
                limit=limit
            )
        )

        # Process URLs from MapData object
        urls = []
        if hasattr(result, 'links'):
            urls = result.links or []
        elif isinstance(result, dict):
            urls = result.get("links", result.get("urls", []))
        elif isinstance(result, list):
            urls = result

        # Categorize URLs by path
        categories = {}
        for u in urls:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(u)
                path_parts = parsed.path.strip("/").split("/")
                category = path_parts[0] if path_parts and path_parts[0] else "root"
                if category not in categories:
                    categories[category] = []
                categories[category].append(u)
            except:
                pass

        return {
            "success": True,
            "base_url": url,
            "total_urls": len(urls),
            "urls": urls[:50],  # Return first 50 in response
            "all_urls_count": len(urls),
            "categories": {k: len(v) for k, v in categories.items()},
            "search_query": search_query,
        }

    except ImportError:
        return {"success": False, "error": "Firecrawl not installed. Run: pip install firecrawl-py"}
    except Exception as e:
        return {"success": False, "url": url, "error": str(e)}


@tool
async def search_and_scrape(
    query: str,
    num_results: int = 5,
    scrape_content: bool = True
) -> Dict[str, Any]:
    """
    Search the web and optionally scrape the content of search results.
    Combines search with scraping for comprehensive research.

    Args:
        query: Search query
        num_results: Number of search results to return
        scrape_content: Whether to scrape full content of each result

    Returns:
        Dict with search results and optionally scraped content

    Example:
        result = await search_and_scrape(
            "CDISC SDTM AE domain specification",
            num_results=3,
            scrape_content=True
        )
    """
    try:
        from firecrawl import FirecrawlApp

        api_key = os.getenv("FIRECRAWL_API_KEY", "fc-4a39356cf081453f96726af430e24ae1")
        app = FirecrawlApp(api_key=api_key)

        # Search
        loop = asyncio.get_event_loop()
        search_result = await loop.run_in_executor(
            None,
            lambda: app.search(query, limit=num_results)
        )

        results = []

        # Process search results from SearchData object
        search_data = []
        if hasattr(search_result, 'data'):
            search_data = search_result.data or []
        elif isinstance(search_result, list):
            search_data = search_result

        for item in search_data:
            # Handle both object and dict formats
            if hasattr(item, 'title'):
                result_item = {
                    "title": item.title or "",
                    "url": item.url or "",
                    "description": (item.description or "")[:500],
                }
            else:
                result_item = {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", item.get("content", ""))[:500],
                }

            # Optionally scrape full content
            if scrape_content and result_item["url"]:
                try:
                    scrape_result = await loop.run_in_executor(
                        None,
                        lambda url=result_item["url"]: app.scrape(
                            url,
                            formats=["markdown"],
                            only_main_content=True
                        )
                    )
                    markdown = scrape_result.markdown if hasattr(scrape_result, 'markdown') else ""
                    result_item["full_content"] = markdown[:5000]
                    result_item["content_length"] = len(markdown)
                except Exception as scrape_error:
                    result_item["scrape_error"] = str(scrape_error)

            results.append(result_item)

        return {
            "success": True,
            "query": query,
            "num_results": len(results),
            "results": results,
        }

    except ImportError:
        return {"success": False, "error": "Firecrawl not installed. Run: pip install firecrawl-py"}
    except Exception as e:
        return {"success": False, "query": query, "error": str(e)}


@tool
async def extract_structured_data(
    url: str,
    extraction_schema: Dict[str, Any],
    prompt: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract structured data from a webpage using AI-powered extraction.
    Define a schema and Firecrawl will extract matching data.

    Args:
        url: URL to extract data from
        extraction_schema: JSON schema defining the data structure to extract
        prompt: Optional prompt to guide extraction

    Returns:
        Dict with extracted structured data

    Example:
        result = await extract_structured_data(
            "https://clinicaltrials.gov/study/NCT12345678",
            extraction_schema={
                "type": "object",
                "properties": {
                    "trial_name": {"type": "string"},
                    "sponsor": {"type": "string"},
                    "phase": {"type": "string"},
                    "conditions": {"type": "array", "items": {"type": "string"}},
                    "enrollment": {"type": "number"}
                }
            },
            prompt="Extract clinical trial information"
        )
    """
    try:
        from firecrawl import FirecrawlApp

        api_key = os.getenv("FIRECRAWL_API_KEY", "fc-4a39356cf081453f96726af430e24ae1")
        app = FirecrawlApp(api_key=api_key)

        # Run extraction using the extract method
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: app.extract(
                urls=[url],
                schema=extraction_schema,
                prompt=prompt
            )
        )

        # Get extracted data from result
        extracted_data = {}
        if hasattr(result, 'data'):
            extracted_data = result.data
        elif isinstance(result, dict):
            extracted_data = result.get("data", result.get("extract", {}))

        metadata = {}
        if hasattr(result, 'metadata'):
            metadata = result.metadata or {}

        return {
            "success": True,
            "url": url,
            "extracted_data": extracted_data,
            "metadata": metadata,
        }

    except ImportError:
        return {"success": False, "error": "Firecrawl not installed. Run: pip install firecrawl-py"}
    except Exception as e:
        return {"success": False, "url": url, "error": str(e)}


# Web scraping tools list
WEB_SCRAPING_TOOLS = [
    scrape_webpage,
    crawl_website,
    map_website,
    search_and_scrape,
    extract_structured_data,
]


# =============================================================================
# EXPORT ALL TOOLS - Combined DeepAgents + SDTM Chat Tools
# =============================================================================

# DeepAgents-specific tools for pipeline orchestration (now async)
DEEPAGENT_TOOLS = [
    # Bash Execution (async)
    execute_bash,
    # Visualization (async) - Frontend-compatible Recharts
    create_bar_chart,
    create_line_chart,
    create_pie_chart,
    create_area_chart,
    create_scatter_chart,
    create_radar_chart,
    create_funnel_chart,
    create_composed_chart,
    create_sdtm_validation_dashboard,
    # Web Scraping & Crawling (Firecrawl - async)
    scrape_webpage,
    crawl_website,
    map_website,
    search_and_scrape,
    extract_structured_data,
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

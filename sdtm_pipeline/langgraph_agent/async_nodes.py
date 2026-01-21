"""
SDTM Pipeline Async Node Functions
==================================
Async LangGraph nodes with parallel execution support.
Downloads data from S3 and checks Neo4j for existing data.
"""

import os
import json
import asyncio
import zipfile
import pandas as pd
import boto3
from typing import Dict, Any, List, Tuple
from datetime import datetime
from langchain_core.runnables import RunnableConfig
from langsmith import traceable
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from .state import SDTMPipelineState
from .config import get_s3_config, get_neo4j_config

# Import SDTM pipeline components
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sdtm_pipeline.validators.raw_data_validator import RawDataValidator
from sdtm_pipeline.validators.sdtm_validator import SDTMValidator
from sdtm_pipeline.transformers.mapping_generator import MappingSpecificationGenerator
from sdtm_pipeline.transformers.domain_transformers import get_transformer
from sdtm_pipeline.generators.sas_generator import SASCodeGenerator
from sdtm_pipeline.generators.r_generator import RCodeGenerator


def convert_to_serializable(obj: Any) -> Any:
    """Convert objects to JSON-serializable format."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [convert_to_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    if hasattr(obj, 'to_dict'):
        return obj.to_dict()
    if hasattr(obj, '__dict__'):
        return convert_to_serializable(obj.__dict__)
    return str(obj)


# ============================================================================
# Async Node: Ingest Data (Downloads from S3)
# ============================================================================

@traceable(name="ingest_data")
async def ingest_data_node(state: SDTMPipelineState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Async Node: Download data from S3 and ingest raw data files.

    Steps:
    1. Download EDC Data.zip from S3 bucket
    2. Extract to local directory
    3. Scan for CSV files
    4. Select key clinical domains
    """
    print("\n" + "=" * 60)
    print("NODE: Ingest Data from S3 (Async)")
    print("=" * 60)

    study_id = state.get("study_id", "MAXIS-08")
    output_dir = state.get("output_dir", "./sdtm_langgraph_output")
    messages = []

    # Get S3 configuration
    s3_config = get_s3_config()
    bucket = s3_config.get("bucket", os.getenv("S3_ETL_BUCKET", "s3dcri"))

    # Setup directories
    download_dir = "/tmp/s3_data"
    extract_dir = f"{download_dir}/extracted"

    # Run blocking operations in executor to avoid blocking the event loop
    def setup_directories():
        os.makedirs(download_dir, exist_ok=True)
        os.makedirs(extract_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

    await asyncio.get_event_loop().run_in_executor(None, setup_directories)

    # Download from S3
    print(f"  Downloading from S3 bucket: {bucket}")
    messages.append(f"Downloading from S3 bucket: {bucket}")

    zip_path = f"{download_dir}/EDC_Data.zip"

    def download_from_s3():
        try:
            s3 = boto3.client(
                's3',
                aws_access_key_id=s3_config.get('access_key') or os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=s3_config.get('secret_key') or os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=s3_config.get('region', 'us-east-1')
            )
            s3_key = "incoming/EDC Data.zip"
            s3.download_file(bucket, s3_key, zip_path)
            return True, f"Downloaded {s3_key} from S3"
        except Exception as e:
            return False, f"S3 download error: {str(e)}"

    success, download_msg = await asyncio.get_event_loop().run_in_executor(None, download_from_s3)
    print(f"  {download_msg}")
    messages.append(download_msg)

    # Extract ZIP file
    def extract_zip():
        if os.path.exists(zip_path):
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            return True
        return False

    if success or os.path.exists(zip_path):
        await asyncio.get_event_loop().run_in_executor(None, extract_zip)
        print("  Extracted ZIP file")
        messages.append("Extracted EDC Data.zip")

    # Find data directory
    raw_data_dir = f"{extract_dir}/Maxis-08 RAW DATA_CSV"

    def find_data_dir():
        nonlocal raw_data_dir
        if not os.path.exists(raw_data_dir):
            # Search for directory with CSV files
            for root, dirs, files in os.walk(extract_dir):
                if files and any(f.endswith('.csv') for f in files):
                    return root
        return raw_data_dir

    raw_data_dir = await asyncio.get_event_loop().run_in_executor(None, find_data_dir)
    print(f"  Data directory: {raw_data_dir}")

    # Scan for CSV files
    source_files = []

    def scan_directory():
        files = []
        if os.path.exists(raw_data_dir):
            for filename in os.listdir(raw_data_dir):
                if filename.endswith('.csv'):
                    filepath = os.path.join(raw_data_dir, filename)
                    size_kb = os.path.getsize(filepath) / 1024
                    files.append({
                        "path": filepath,
                        "name": filename,
                        "size_kb": size_kb,
                        "target_domain": None
                    })
        return files

    source_files = await asyncio.get_event_loop().run_in_executor(None, scan_directory)
    source_files.sort(key=lambda x: x['size_kb'], reverse=True)

    # Comprehensive SDTM domain mapping for all source files
    # Maps source EDC files to their target SDTM domains
    domain_mapping = {
        # Demographics (DM)
        'DEMO.csv': 'DM',

        # Adverse Events (AE) and Supplemental
        'AEVENT.csv': 'AE',
        'AEVENTC.csv': 'SUPPAE',

        # Concomitant Medications (CM) and Supplemental
        'CONMEDS.csv': 'CM',
        'CONMEDSC.csv': 'SUPPCM',
        'CAMED19.csv': 'CM',      # Prior/concurrent medications
        'CAMED19C.csv': 'SUPPCM',
        'RADMEDS.csv': 'CM',      # Radiation therapy meds

        # Exposure (EX) and Supplemental
        'DOSE.csv': 'EX',

        # Disposition (DS) and Supplemental
        'CMPL.csv': 'DS',         # Completion/compliance
        'DEATHGEN.csv': 'DS',     # Death information

        # Medical History (MH) and Supplemental
        'GMEDHX.csv': 'MH',       # General medical history
        'GMEDHXC.csv': 'SUPPMH',
        'DISHX.csv': 'MH',        # Disease history
        'DISHXC.csv': 'SUPPMH',
        'SURGHX.csv': 'MH',       # Surgical history
        'SURGHXC.csv': 'SUPPMH',

        # Vital Signs (VS)
        'VITALS.csv': 'VS',

        # Laboratory (LB) - Chemistry, Hematology, Urinalysis, etc.
        'CHEMLAB.csv': 'LB',
        'CHEMLABD.csv': 'LB',     # Detailed chemistry
        'HEMLAB.csv': 'LB',
        'HEMLABD.csv': 'LB',      # Detailed hematology
        'URINLAB.csv': 'LB',
        'BIOLAB.csv': 'LB',
        'GENOLAB.csv': 'LB',      # Genomic laboratory

        # ECG (EG) and Supplemental
        'ECG.csv': 'EG',

        # Physical Examination (PE)
        'PHYSEXAM.csv': 'PE',

        # Pharmacokinetics Concentrations (PC)
        'PKCRF.csv': 'PC',

        # Inclusion/Exclusion (IE)
        'ELIG.csv': 'IE',
        'INEXCRT.csv': 'IE',      # Inclusion/exclusion criteria

        # Subject Visits (SV)
        # Note: Visit data often embedded in other files

        # Comments (CO)
        'COMGEN.csv': 'CO',

        # Questionnaires (QS)
        'QS.csv': 'QS',
        'QSQS.csv': 'QS',
        'ECOGSAMP.csv': 'QS',     # ECOG performance status

        # Disease Response (RS) and Supplemental
        'RESP.csv': 'RS',

        # Tumor Results (TR) and Tumor Identification (TU)
        'TARTUMR.csv': 'TR',      # Target tumor results
        'NONTUMR.csv': 'TU',      # Non-target tumor identification

        # Sample/Specimen files - map to relevant domains or skip
        'BIOSAMP.csv': 'PC',      # Biospecimen -> PK
        'CHEMSAMP.csv': 'LB',     # Chemistry samples
        'HEMSAMP.csv': 'LB',      # Hematology samples
        'URINSAMP.csv': 'LB',     # Urine samples
        'GENOSAMP.csv': 'LB',     # Genomic samples
        'PRGSAMP.csv': 'PC',      # PK samples
        'SOBSAMP.csv': 'PC',      # Specimen samples
        'XRAYSAMP.csv': 'PE',     # X-ray related -> PE

        # Other files
        'INV.csv': 'TA',          # Investigator -> Trial Arms (reference)
        'LABRANG.csv': 'LB',      # Lab ranges -> LB reference
        'PATICDO3.csv': 'DM',     # Patient ID -> Demographics
    }

    selected_files = []
    for f in source_files:
        if f['name'] in domain_mapping:
            f['target_domain'] = domain_mapping[f['name']]
            selected_files.append(f)

    # Count unique domains
    unique_domains = set(f['target_domain'] for f in selected_files)

    messages.append(f"Found {len(source_files)} CSV files")
    messages.append(f"Selected {len(selected_files)} files mapping to {len(unique_domains)} SDTM domains")

    print(f"  Found {len(source_files)} CSV files")
    print(f"  Selected {len(selected_files)} files -> {len(unique_domains)} SDTM domains")
    print(f"  Domains: {', '.join(sorted(unique_domains))}")
    for f in selected_files:
        print(f"    - {f['name']} -> {f['target_domain']}")

    return {
        "study_id": study_id,
        "raw_data_dir": raw_data_dir,
        "output_dir": output_dir,
        "current_phase": "data_ingested",
        "phase_history": ["data_ingested"],
        "source_files": source_files,
        "selected_files": selected_files,
        "messages": messages
    }


# ============================================================================
# Async Node: Validate Raw Data (Parallel)
# ============================================================================

@traceable(name="validate_raw_data_parallel")
async def validate_raw_data_parallel_node(state: SDTMPipelineState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Async Node: Validate raw data in parallel.
    """
    print("\n" + "=" * 60)
    print("NODE: Validate Raw Data (Parallel Async)")
    print("=" * 60)

    study_id = state.get("study_id", "UNKNOWN")
    selected_files = state.get("selected_files", [])
    output_dir = state.get("output_dir", "/tmp")

    validation_results = []
    raw_data_paths = {}
    raw_data_info = {}
    messages = []

    async def validate_single_file(file_info: Dict) -> Tuple[str, Dict]:
        """Validate a single file asynchronously."""
        filepath = file_info["path"]
        filename = file_info["name"]

        print(f"  Validating: {filename}")

        try:
            # Read file (I/O bound - good for async)
            df = await asyncio.get_event_loop().run_in_executor(
                None, pd.read_csv, filepath
            )

            validator = RawDataValidator(study_id)
            result = await asyncio.get_event_loop().run_in_executor(
                None, validator.validate_dataframe, df, filename
            )

            validation_result = {
                "is_valid": result.is_valid,
                "domain": result.domain,
                "total_records": result.total_records,
                "error_count": result.error_count,
                "warning_count": result.warning_count,
                "issues": [convert_to_serializable(i) for i in result.issues]
            }

            data_info = {
                "rows": len(df),
                "columns": list(df.columns),
                "target_domain": file_info.get("target_domain")
            }

            status = "PASS" if result.is_valid else "FAIL"
            print(f"    {filename}: {status} ({result.total_records} records)")

            return filename, {
                "validation": validation_result,
                "path": filepath,
                "info": data_info
            }

        except Exception as e:
            print(f"    {filename}: ERROR - {str(e)}")
            return filename, {
                "validation": {"is_valid": False, "error": str(e)},
                "path": filepath,
                "info": {}
            }

    # Run validations in parallel
    tasks = [validate_single_file(f) for f in selected_files]
    results = await asyncio.gather(*tasks)

    for filename, result in results:
        if "validation" in result:
            validation_results.append(result["validation"])
        raw_data_paths[filename] = result.get("path", "")
        raw_data_info[filename] = result.get("info", {})
        messages.append(f"Validated {filename}")

    # Save validation report (using executor to avoid blocking)
    validation_dir = os.path.join(output_dir, "raw_validation")
    report_path = os.path.join(validation_dir, "validation_report.json")

    def save_validation_report():
        os.makedirs(validation_dir, exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump({"results": validation_results}, f, indent=2)

    await asyncio.get_event_loop().run_in_executor(None, save_validation_report)

    messages.append(f"Validation report saved to {report_path}")

    return {
        "current_phase": "raw_validated",
        "phase_history": ["raw_validated"],
        "raw_validation_results": validation_results,
        "raw_data_paths": raw_data_paths,
        "raw_data_info": raw_data_info,
        "pending_review": "raw_validation",
        "messages": messages
    }


# ============================================================================
# Async Node: Generate Mappings (Parallel)
# ============================================================================

@traceable(name="generate_mappings_parallel")
async def generate_mappings_parallel_node(state: SDTMPipelineState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Async Node: Generate SDTM mappings in parallel using LLM.
    """
    print("\n" + "=" * 60)
    print("NODE: Generate Mappings (Parallel Async)")
    print("=" * 60)

    study_id = state.get("study_id", "UNKNOWN")
    api_key = state.get("api_key", "")
    selected_files = state.get("selected_files", [])
    output_dir = state.get("output_dir", "/tmp")

    mapping_specifications = []
    messages = []

    mapping_dir = os.path.join(output_dir, "mapping_specs")

    # Create directory in executor to avoid blocking
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: os.makedirs(mapping_dir, exist_ok=True)
    )

    async def generate_single_mapping(file_info: Dict) -> Dict:
        """Generate mapping for a single file."""
        filename = file_info["name"]
        filepath = file_info["path"]
        target_domain = file_info.get("target_domain")

        print(f"  Generating mapping: {filename} -> {target_domain}")

        try:
            df = await asyncio.get_event_loop().run_in_executor(
                None, pd.read_csv, filepath
            )

            mapping_generator = MappingSpecificationGenerator(api_key, study_id)
            spec = await asyncio.get_event_loop().run_in_executor(
                None, mapping_generator.generate_mapping, df, filename, target_domain
            )

            spec_dict = convert_to_serializable(spec.to_dict())

            # Save mapping spec (in executor to avoid blocking)
            spec_path = os.path.join(mapping_dir, f"{target_domain}_mapping.json")

            def save_spec():
                with open(spec_path, 'w') as f:
                    json.dump(spec_dict, f, indent=2)

            await asyncio.get_event_loop().run_in_executor(None, save_spec)

            print(f"    {filename}: {len(spec.column_mappings)} mappings")
            return spec_dict

        except Exception as e:
            print(f"    {filename}: ERROR - {str(e)}")
            return {"error": str(e), "source_domain": filename}

    # Run mapping generation in parallel (limit concurrency for API rate limits)
    semaphore = asyncio.Semaphore(3)  # Limit concurrent API calls

    async def limited_generate(file_info):
        async with semaphore:
            return await generate_single_mapping(file_info)

    tasks = [limited_generate(f) for f in selected_files]
    results = await asyncio.gather(*tasks)

    for spec_dict in results:
        if "error" not in spec_dict:
            mapping_specifications.append(spec_dict)
            messages.append(f"Generated mapping for {spec_dict.get('source_domain')} -> {spec_dict.get('target_domain')}")

    return {
        "current_phase": "mappings_generated",
        "phase_history": ["mappings_generated"],
        "mapping_specifications": mapping_specifications,
        "pending_review": "mapping_specs",
        "messages": messages
    }


# ============================================================================
# Async Node: Transform to SDTM (Parallel)
# ============================================================================

@traceable(name="transform_to_sdtm_parallel")
async def transform_to_sdtm_parallel_node(state: SDTMPipelineState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Async Node: Transform data to SDTM in parallel.
    """
    print("\n" + "=" * 60)
    print("NODE: Transform to SDTM (Parallel Async)")
    print("=" * 60)

    study_id = state.get("study_id", "UNKNOWN")
    selected_files = state.get("selected_files", [])
    output_dir = state.get("output_dir", "/tmp")

    sdtm_dir = os.path.join(output_dir, "sdtm_data")

    # Create directory in executor to avoid blocking
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: os.makedirs(sdtm_dir, exist_ok=True)
    )

    transformation_results = []
    sdtm_data_paths = {}
    messages = []
    total_in = 0
    total_out = 0

    async def transform_single_file(file_info: Dict) -> Dict:
        """Transform a single file to SDTM."""
        filename = file_info["name"]
        filepath = file_info["path"]
        target_domain = file_info.get("target_domain")

        if not target_domain:
            return {"success": False, "error": "No target domain"}

        print(f"  Transforming: {filename} -> {target_domain}")

        try:
            df = await asyncio.get_event_loop().run_in_executor(
                None, pd.read_csv, filepath
            )

            transformer = get_transformer(target_domain, study_id)

            # Execute transformation
            def do_transform():
                result = transformer.execute(df)
                if result.success:
                    sdtm_df = transformer.transform(df)
                    return result, sdtm_df
                return result, None

            result, sdtm_df = await asyncio.get_event_loop().run_in_executor(
                None, do_transform
            )

            if result.success and sdtm_df is not None:
                output_path = os.path.join(sdtm_dir, f"{target_domain.lower()}.csv")
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: sdtm_df.to_csv(output_path, index=False)
                )

                print(f"    {filename}: {len(df)} -> {len(sdtm_df)} records")

                return {
                    "success": True,
                    "source_domain": filename,
                    "target_domain": target_domain,
                    "records_processed": len(df),
                    "records_output": len(sdtm_df),
                    "output_path": output_path
                }
            else:
                return {
                    "success": False,
                    "source_domain": filename,
                    "target_domain": target_domain,
                    "errors": result.errors
                }

        except Exception as e:
            print(f"    {filename}: ERROR - {str(e)}")
            return {"success": False, "source_domain": filename, "error": str(e)}

    # Run transformations in parallel
    tasks = [transform_single_file(f) for f in selected_files]
    results = await asyncio.gather(*tasks)

    for result in results:
        transformation_results.append(result)
        if result.get("success"):
            sdtm_data_paths[result["target_domain"]] = result.get("output_path", "")
            total_in += result.get("records_processed", 0)
            total_out += result.get("records_output", 0)
            messages.append(f"Transformed {result['source_domain']} -> {result['target_domain']}")

    return {
        "current_phase": "transformed",
        "phase_history": ["transformed"],
        "transformation_results": transformation_results,
        "sdtm_data_paths": sdtm_data_paths,
        "processing_stats": {
            "total_records_in": total_in,
            "total_records_out": total_out,
            "domains_transformed": len(sdtm_data_paths)
        },
        "messages": messages
    }


# ============================================================================
# Async Node: Validate SDTM (Parallel)
# ============================================================================

@traceable(name="validate_sdtm_parallel")
async def validate_sdtm_parallel_node(state: SDTMPipelineState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Async Node: Validate SDTM datasets in parallel.
    """
    print("\n" + "=" * 60)
    print("NODE: Validate SDTM (Parallel Async)")
    print("=" * 60)

    study_id = state.get("study_id", "UNKNOWN")
    sdtm_data_paths = state.get("sdtm_data_paths", {})
    output_dir = state.get("output_dir", "/tmp")

    validation_results = []
    messages = []

    async def validate_single_domain(domain: str, filepath: str) -> Dict:
        """Validate a single SDTM domain."""
        print(f"  Validating SDTM: {domain}")

        try:
            df = await asyncio.get_event_loop().run_in_executor(
                None, pd.read_csv, filepath
            )

            validator = SDTMValidator(study_id)
            result = await asyncio.get_event_loop().run_in_executor(
                None, validator.validate_domain, df, domain
            )

            status = "PASS" if result.is_valid else "FAIL"
            print(f"    {domain}: {status} ({result.total_records} records)")

            return {
                "is_valid": result.is_valid,
                "domain": result.domain,
                "total_records": result.total_records,
                "error_count": result.error_count,
                "warning_count": result.warning_count,
                "issues": [convert_to_serializable(i) for i in result.issues]
            }

        except Exception as e:
            print(f"    {domain}: ERROR - {str(e)}")
            return {"is_valid": False, "domain": domain, "error": str(e)}

    # Run validations in parallel
    tasks = [validate_single_domain(d, p) for d, p in sdtm_data_paths.items()]
    results = await asyncio.gather(*tasks)

    for result in results:
        validation_results.append(result)
        status = "PASS" if result.get("is_valid") else "FAIL"
        messages.append(f"Validated SDTM {result.get('domain')}: {status}")

    # Save validation report (using executor to avoid blocking)
    validation_dir = os.path.join(output_dir, "sdtm_validation")
    report_path = os.path.join(validation_dir, "validation_report.json")

    def save_sdtm_validation_report():
        os.makedirs(validation_dir, exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump({"results": validation_results}, f, indent=2)

    await asyncio.get_event_loop().run_in_executor(None, save_sdtm_validation_report)

    submission_ready = all(r.get("is_valid", False) for r in validation_results)

    return {
        "current_phase": "sdtm_validated",
        "phase_history": ["sdtm_validated"],
        "sdtm_validation_results": validation_results,
        "pending_review": "sdtm_validation",
        "processing_stats": {
            **state.get("processing_stats", {}),
            "submission_ready": submission_ready
        },
        "messages": messages
    }


# ============================================================================
# Async Node: Generate Code (Parallel SAS + R)
# ============================================================================

@traceable(name="generate_code_parallel")
async def generate_code_parallel_node(state: SDTMPipelineState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Async Node: Generate SAS and R code in parallel.
    """
    print("\n" + "=" * 60)
    print("NODE: Generate Code (Parallel SAS + R)")
    print("=" * 60)

    study_id = state.get("study_id", "UNKNOWN")
    mapping_specifications = state.get("mapping_specifications", [])
    output_dir = state.get("output_dir", "/tmp")

    from sdtm_pipeline.models.sdtm_models import MappingSpecification, ColumnMapping

    # Convert dict specs to MappingSpecification objects
    specs = []
    for spec_dict in mapping_specifications:
        column_mappings = [
            ColumnMapping(
                source_column=m.get("source_column", ""),
                target_variable=m.get("target_variable", ""),
                transformation=m.get("transformation"),
                derivation_rule=m.get("derivation_rule"),
                comments=m.get("comments", "")
            )
            for m in spec_dict.get("column_mappings", [])
        ]

        spec = MappingSpecification(
            study_id=spec_dict.get("study_id", study_id),
            source_domain=spec_dict.get("source_domain", ""),
            target_domain=spec_dict.get("target_domain", ""),
            column_mappings=column_mappings,
            derivation_rules=spec_dict.get("derivation_rules", {})
        )
        specs.append(spec)

    messages = []

    async def generate_sas():
        """Generate SAS programs."""
        print("  Generating SAS programs...")
        sas_dir = os.path.join(output_dir, "sas_programs")
        sas_generator = SASCodeGenerator(study_id, sas_dir)
        return await asyncio.get_event_loop().run_in_executor(
            None, sas_generator.generate_all, specs
        )

    async def generate_r():
        """Generate R scripts."""
        print("  Generating R scripts...")
        r_dir = os.path.join(output_dir, "r_programs")
        r_generator = RCodeGenerator(study_id, r_dir)
        return await asyncio.get_event_loop().run_in_executor(
            None, r_generator.generate_all, specs
        )

    # Run SAS and R generation in parallel
    sas_files, r_files = await asyncio.gather(generate_sas(), generate_r())

    print(f"    Generated {len(sas_files)} SAS programs")
    print(f"    Generated {len(r_files)} R scripts")

    messages.append(f"Generated {len(sas_files)} SAS programs")
    messages.append(f"Generated {len(r_files)} R scripts")

    return {
        "current_phase": "code_generated",
        "phase_history": ["code_generated"],
        "generated_sas_files": sas_files,
        "generated_r_files": r_files,
        "messages": messages
    }


# ============================================================================
# Async Node: Load to Neo4j
# ============================================================================

@traceable(name="load_to_neo4j")
async def load_to_neo4j_node(state: SDTMPipelineState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Async Node: Load SDTM data to Neo4j graph database.

    Checks if data for the study already exists in Neo4j before loading.
    If data exists, skips loading. Otherwise, loads the transformed SDTM data.
    """
    print("\n" + "=" * 60)
    print("NODE: Load to Neo4j (Async)")
    print("=" * 60)

    from .config import get_neo4j_config

    neo4j_config = get_neo4j_config()
    sdtm_data_paths = state.get("sdtm_data_paths", {})
    study_id = state.get("study_id", "UNKNOWN")
    messages = []

    try:
        from etl_neo4j.neo4j_loader import create_loader

        loader = create_loader()

        if not loader.verify_connectivity():
            messages.append("WARNING: Could not connect to Neo4j")
            print("  WARNING: Neo4j connection failed")
            return {
                "current_phase": "neo4j_skipped",
                "phase_history": ["neo4j_skipped"],
                "messages": messages
            }

        print(f"  Connected to Neo4j at {neo4j_config['uri']}")

        # Check if data for this study already exists in Neo4j
        def check_existing_data():
            """Check if SDTM data for this study already exists."""
            success, records = loader.execute_cypher(
                "MATCH (n:SDTM_DM) WHERE n.STUDYID = $study_id RETURN count(n) as count",
                {"study_id": study_id}
            )
            if success and records and len(records) > 0:
                return records[0].get('count', 0)
            return 0

        existing_count = await asyncio.get_event_loop().run_in_executor(
            None, check_existing_data
        )

        if existing_count > 0:
            print(f"  Data for study {study_id} already exists in Neo4j ({existing_count} DM records)")
            print("  Skipping Neo4j load to avoid duplicates")
            messages.append(f"Data for study {study_id} already exists in Neo4j ({existing_count} records)")
            messages.append("Skipped Neo4j load - data already present")

            # Get current stats
            stats = await asyncio.get_event_loop().run_in_executor(
                None, loader.get_database_stats
            )
            loader.close()

            return {
                "current_phase": "neo4j_skipped_exists",
                "phase_history": ["neo4j_skipped_exists"],
                "processing_stats": {
                    **state.get("processing_stats", {}),
                    "neo4j_nodes": stats.get('node_count', existing_count),
                    "neo4j_loaded": False,
                    "neo4j_already_exists": True
                },
                "messages": messages
            }

        # Data doesn't exist, proceed with loading
        print(f"  No existing data for study {study_id}, proceeding with load...")

        total_nodes = 0

        # Load each domain
        for domain, filepath in sdtm_data_paths.items():
            print(f"  Loading {domain} to Neo4j...")

            def read_csv_safe(path):
                return pd.read_csv(path, on_bad_lines='skip')

            df = await asyncio.get_event_loop().run_in_executor(
                None, read_csv_safe, filepath
            )

            # Add domain label and clean records
            records = df.to_dict(orient='records')
            clean_records = []

            for i, rec in enumerate(records):
                clean_rec = {"id": f"{domain}_{i}"}
                for k, v in rec.items():
                    if pd.isna(v):
                        clean_rec[k] = None
                    elif hasattr(v, 'item'):
                        clean_rec[k] = v.item()
                    else:
                        clean_rec[k] = v
                clean_records.append(clean_rec)

            # Merge nodes with SDTM and domain labels
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: loader.merge_nodes(
                    label=f"SDTM_{domain}",
                    records=clean_records,
                    id_property='id',
                    batch_size=500
                )
            )

            total_nodes += result.nodes_created
            print(f"    Created {result.nodes_created} {domain} nodes")
            messages.append(f"Loaded {result.nodes_created} {domain} nodes to Neo4j")

        # Create relationships between patients and data
        print("  Creating relationships...")

        relationship_queries = [
            ("Patient -> AdverseEvent", """
                MATCH (p:SDTM_DM), (ae:SDTM_AE)
                WHERE p.USUBJID = ae.USUBJID
                MERGE (p)-[:HAS_ADVERSE_EVENT]->(ae)
            """),
            ("Patient -> VitalSign", """
                MATCH (p:SDTM_DM), (vs:SDTM_VS)
                WHERE p.USUBJID = vs.USUBJID
                MERGE (p)-[:HAS_VITAL_SIGN]->(vs)
            """),
            ("Patient -> Laboratory", """
                MATCH (p:SDTM_DM), (lb:SDTM_LB)
                WHERE p.USUBJID = lb.USUBJID
                MERGE (p)-[:HAS_LAB_RESULT]->(lb)
            """),
            ("Patient -> Medication", """
                MATCH (p:SDTM_DM), (cm:SDTM_CM)
                WHERE p.USUBJID = cm.USUBJID
                MERGE (p)-[:TAKES_MEDICATION]->(cm)
            """),
        ]

        for name, query in relationship_queries:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda q=query: loader.execute_cypher(q)
                )
                print(f"    Created {name} relationships")
            except Exception as e:
                print(f"    WARNING: {name} relationships failed: {e}")

        # Get final stats
        stats = loader.get_database_stats()
        print(f"\n  Neo4j Summary:")
        print(f"    Total Nodes: {stats.get('node_count', 0)}")
        print(f"    Total Relationships: {stats.get('relationship_count', 0)}")

        loader.close()

        messages.append(f"Total nodes created in Neo4j: {total_nodes}")

        return {
            "current_phase": "neo4j_loaded",
            "phase_history": ["neo4j_loaded"],
            "processing_stats": {
                **state.get("processing_stats", {}),
                "neo4j_nodes": total_nodes,
                "neo4j_loaded": True
            },
            "messages": messages
        }

    except Exception as e:
        print(f"  ERROR loading to Neo4j: {str(e)}")
        messages.append(f"Neo4j load error: {str(e)}")
        return {
            "current_phase": "neo4j_error",
            "phase_history": ["neo4j_error"],
            "errors": [f"Neo4j error: {str(e)}"],
            "messages": messages
        }


# ============================================================================
# Async Node: Upload to S3
# ============================================================================

@traceable(name="upload_to_s3")
async def upload_to_s3_node(state: SDTMPipelineState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Async Node: Upload processed data to S3.
    """
    print("\n" + "=" * 60)
    print("NODE: Upload to S3 (Async)")
    print("=" * 60)

    import boto3
    from .config import get_s3_config

    s3_config = get_s3_config()
    output_dir = state.get("output_dir", "/tmp")
    study_id = state.get("study_id", "UNKNOWN")
    messages = []

    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=s3_config['access_key'],
            aws_secret_access_key=s3_config['secret_key'],
            region_name=s3_config['region']
        )

        bucket = s3_config['bucket']
        prefix = f"{s3_config['processed_prefix']}/{study_id}"

        print(f"  Uploading to s3://{bucket}/{prefix}/")

        uploaded_files = []

        # Collect all files to upload (in executor to avoid blocking)
        def collect_files():
            files_to_upload = []
            for root, dirs, files in os.walk(output_dir):
                for filename in files:
                    local_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(local_path, output_dir)
                    s3_key = f"{prefix}/{relative_path}"
                    files_to_upload.append((local_path, s3_key, relative_path))
            return files_to_upload

        files_to_upload = await asyncio.get_event_loop().run_in_executor(
            None, collect_files
        )

        # Upload all files
        for local_path, s3_key, relative_path in files_to_upload:
            print(f"    Uploading: {relative_path}")

            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda lp=local_path, k=s3_key: s3.upload_file(lp, bucket, k)
            )

            uploaded_files.append(s3_key)

        print(f"\n  Uploaded {len(uploaded_files)} files to S3")
        messages.append(f"Uploaded {len(uploaded_files)} files to s3://{bucket}/{prefix}/")

        return {
            "current_phase": "s3_uploaded",
            "phase_history": ["s3_uploaded"],
            "processing_stats": {
                **state.get("processing_stats", {}),
                "s3_uploaded": True,
                "s3_files": len(uploaded_files),
                "s3_prefix": f"s3://{bucket}/{prefix}/"
            },
            "messages": messages
        }

    except Exception as e:
        print(f"  ERROR uploading to S3: {str(e)}")
        messages.append(f"S3 upload error: {str(e)}")
        return {
            "current_phase": "s3_error",
            "phase_history": ["s3_error"],
            "errors": [f"S3 error: {str(e)}"],
            "messages": messages
        }


# ============================================================================
# Async Node: Human Review
# ============================================================================

@traceable(name="human_review")
async def human_review_node(state: SDTMPipelineState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Async Node: Human review checkpoint.
    """
    print("\n" + "=" * 60)
    print(f"NODE: Human Review - {state.get('pending_review', 'unknown')}")
    print("=" * 60)

    pending_review = state.get("pending_review", "")
    human_decision = state.get("human_decision", "approve")

    print(f"  Checkpoint: {pending_review}")
    print(f"  Decision: {human_decision}")

    if human_decision.lower() == "approve":
        return {
            "current_phase": f"{pending_review}_approved",
            "phase_history": [f"{pending_review}_approved"],
            "pending_review": "",
            "messages": [f"Human approved: {pending_review}"]
        }
    else:
        return {
            "current_phase": f"{pending_review}_rejected",
            "phase_history": [f"{pending_review}_rejected"],
            "pending_review": "",
            "errors": [f"Pipeline rejected at {pending_review}"]
        }


# ============================================================================
# Async Node: Generate Final Report
# ============================================================================

@traceable(name="generate_report")
async def generate_report_node(state: SDTMPipelineState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Async Node: Generate final pipeline report.
    """
    print("\n" + "=" * 60)
    print("NODE: Generate Final Report")
    print("=" * 60)

    study_id = state.get("study_id", "UNKNOWN")
    output_dir = state.get("output_dir", "/tmp")
    processing_stats = state.get("processing_stats", {})
    transformation_results = state.get("transformation_results", [])
    sdtm_validation_results = state.get("sdtm_validation_results", [])
    mapping_specifications = state.get("mapping_specifications", [])

    total_sdtm_records = sum(r.get("total_records", 0) for r in sdtm_validation_results)
    sdtm_errors = sum(r.get("error_count", 0) for r in sdtm_validation_results)

    final_report = {
        "study_id": study_id,
        "status": "success",
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "sdtm_domains_created": len([t for t in transformation_results if t.get("success")]),
            "total_sdtm_records": total_sdtm_records,
            "sdtm_validation_errors": sdtm_errors,
            "submission_ready": sdtm_errors == 0,
            "neo4j_loaded": processing_stats.get("neo4j_loaded", False),
            "s3_uploaded": processing_stats.get("s3_uploaded", False)
        },
        "domains": [
            {
                "domain": spec.get("target_domain"),
                "source": spec.get("source_domain"),
                "mappings": len(spec.get("column_mappings", []))
            }
            for spec in mapping_specifications
        ],
        "output_directory": output_dir
    }

    # Save report (using executor to avoid blocking)
    reports_dir = os.path.join(output_dir, "reports")
    report_path = os.path.join(reports_dir, "pipeline_report.json")

    def save_report():
        os.makedirs(reports_dir, exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(final_report, f, indent=2)

    await asyncio.get_event_loop().run_in_executor(None, save_report)

    print(f"\n  Pipeline Summary:")
    print(f"    SDTM domains: {final_report['summary']['sdtm_domains_created']}")
    print(f"    Total records: {total_sdtm_records}")
    print(f"    Neo4j loaded: {processing_stats.get('neo4j_loaded', False)}")
    print(f"    S3 uploaded: {processing_stats.get('s3_uploaded', False)}")
    print(f"\n  Report saved to: {report_path}")

    return {
        "current_phase": "completed",
        "phase_history": ["completed"],
        "final_report": final_report,
        "messages": [f"Pipeline completed. Report saved to {report_path}"]
    }

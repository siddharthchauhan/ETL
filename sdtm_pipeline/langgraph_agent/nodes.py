"""
SDTM Pipeline Node Functions
============================
LangGraph node functions for each phase of the SDTM transformation pipeline.
"""

import os
import json
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime
from langchain_core.runnables import RunnableConfig

from .state import SDTMPipelineState

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
# Node: Ingest Data
# ============================================================================

def ingest_data_node(state: SDTMPipelineState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node: Ingest raw data files from source directory.

    Scans the raw data directory and identifies CSV files for processing.
    """
    print("\n" + "=" * 60)
    print("NODE: Ingest Data")
    print("=" * 60)

    raw_data_dir = state.get("raw_data_dir", "")
    messages = []

    # Find all CSV files
    source_files = []
    if os.path.exists(raw_data_dir):
        for filename in os.listdir(raw_data_dir):
            if filename.endswith('.csv'):
                filepath = os.path.join(raw_data_dir, filename)
                size_kb = os.path.getsize(filepath) / 1024
                source_files.append({
                    "path": filepath,
                    "name": filename,
                    "size_kb": size_kb,
                    "target_domain": None
                })

    # Sort by size
    source_files.sort(key=lambda x: x['size_kb'], reverse=True)

    # Select key clinical domains
    domain_mapping = {
        'DEMO.csv': 'DM',
        'AEVENT.csv': 'AE',
        'VITALS.csv': 'VS',
        'CHEMLAB.csv': 'LB',
        'HEMLAB.csv': 'LB',
        'CONMEDS.csv': 'CM',
    }

    selected_files = []
    for f in source_files:
        if f['name'] in domain_mapping:
            f['target_domain'] = domain_mapping[f['name']]
            selected_files.append(f)

    messages.append(f"Found {len(source_files)} CSV files in {raw_data_dir}")
    messages.append(f"Selected {len(selected_files)} key clinical domains for SDTM transformation")

    for f in selected_files:
        print(f"  - {f['name']} -> {f['target_domain']}")

    return {
        "current_phase": "data_ingested",
        "phase_history": ["data_ingested"],
        "source_files": source_files,
        "selected_files": selected_files,
        "messages": messages
    }


# ============================================================================
# Node: Validate Raw Data
# ============================================================================

def validate_raw_data_node(state: SDTMPipelineState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node: Validate raw data quality and completeness.

    Performs validation checks on each source file.
    """
    print("\n" + "=" * 60)
    print("NODE: Validate Raw Data")
    print("=" * 60)

    study_id = state.get("study_id", "UNKNOWN")
    selected_files = state.get("selected_files", [])
    output_dir = state.get("output_dir", "/tmp")

    validator = RawDataValidator(study_id)
    validation_results = []
    raw_data_paths = {}
    raw_data_info = {}
    messages = []

    for file_info in selected_files:
        filepath = file_info["path"]
        filename = file_info["name"]

        print(f"\nValidating: {filename}")

        # Read and validate
        try:
            df = pd.read_csv(filepath)
            result = validator.validate_dataframe(df, filename)

            raw_data_paths[filename] = filepath
            raw_data_info[filename] = {
                "rows": len(df),
                "columns": list(df.columns),
                "target_domain": file_info.get("target_domain")
            }

            validation_result = {
                "is_valid": result.is_valid,
                "domain": result.domain,
                "total_records": result.total_records,
                "error_count": result.error_count,
                "warning_count": result.warning_count,
                "issues": [convert_to_serializable(i) for i in result.issues]
            }
            validation_results.append(validation_result)

            status = "PASS" if result.is_valid else "FAIL"
            print(f"  Records: {result.total_records}, Status: {status}")
            print(f"  Errors: {result.error_count}, Warnings: {result.warning_count}")

            messages.append(f"Validated {filename}: {result.total_records} records, {result.error_count} errors")

        except Exception as e:
            messages.append(f"Error validating {filename}: {str(e)}")
            print(f"  ERROR: {str(e)}")

    # Save validation report
    validation_dir = os.path.join(output_dir, "raw_validation")
    os.makedirs(validation_dir, exist_ok=True)
    report_path = os.path.join(validation_dir, "validation_report.json")

    report = validator.generate_report(
        [RawDataValidator(study_id).validate_file(f["path"]) for f in selected_files]
    )
    with open(report_path, 'w') as f:
        json.dump(convert_to_serializable(report), f, indent=2)

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
# Node: Generate Mapping Specifications
# ============================================================================

def generate_mappings_node(state: SDTMPipelineState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node: Generate SDTM mapping specifications using LLM.

    Analyzes source data and creates mapping specifications for each domain.
    """
    print("\n" + "=" * 60)
    print("NODE: Generate Mapping Specifications")
    print("=" * 60)

    study_id = state.get("study_id", "UNKNOWN")
    api_key = state.get("api_key", "")
    selected_files = state.get("selected_files", [])
    raw_data_paths = state.get("raw_data_paths", {})
    output_dir = state.get("output_dir", "/tmp")

    mapping_generator = MappingSpecificationGenerator(api_key, study_id)
    mapping_specifications = []
    messages = []

    mapping_dir = os.path.join(output_dir, "mapping_specs")
    os.makedirs(mapping_dir, exist_ok=True)

    for file_info in selected_files:
        filename = file_info["name"]
        filepath = file_info["path"]
        target_domain = file_info.get("target_domain")

        print(f"\nGenerating mapping for: {filename} -> {target_domain}")

        try:
            df = pd.read_csv(filepath)

            # Generate mapping specification
            spec = mapping_generator.generate_mapping(df, filename, target_domain)

            # Convert to serializable dict
            spec_dict = convert_to_serializable(spec.to_dict())
            mapping_specifications.append(spec_dict)

            # Save mapping spec
            spec_path = os.path.join(mapping_dir, f"{target_domain}_mapping.json")
            with open(spec_path, 'w') as f:
                json.dump(spec_dict, f, indent=2)

            print(f"  Mappings: {len(spec.column_mappings)}")
            print(f"  Saved to: {spec_path}")

            messages.append(f"Generated mapping for {filename} -> {target_domain} ({len(spec.column_mappings)} mappings)")

        except Exception as e:
            messages.append(f"Error generating mapping for {filename}: {str(e)}")
            print(f"  ERROR: {str(e)}")

    return {
        "current_phase": "mappings_generated",
        "phase_history": ["mappings_generated"],
        "mapping_specifications": mapping_specifications,
        "pending_review": "mapping_specs",
        "messages": messages
    }


# ============================================================================
# Node: Transform to SDTM
# ============================================================================

def transform_to_sdtm_node(state: SDTMPipelineState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node: Transform raw data to SDTM format.

    Applies transformations based on mapping specifications.
    """
    print("\n" + "=" * 60)
    print("NODE: Transform to SDTM")
    print("=" * 60)

    study_id = state.get("study_id", "UNKNOWN")
    selected_files = state.get("selected_files", [])
    output_dir = state.get("output_dir", "/tmp")

    sdtm_dir = os.path.join(output_dir, "sdtm_data")
    os.makedirs(sdtm_dir, exist_ok=True)

    transformation_results = []
    sdtm_data_paths = {}
    messages = []
    total_records_in = 0
    total_records_out = 0

    for file_info in selected_files:
        filename = file_info["name"]
        filepath = file_info["path"]
        target_domain = file_info.get("target_domain")

        if not target_domain:
            continue

        print(f"\nTransforming: {filename} -> {target_domain}")

        try:
            df = pd.read_csv(filepath)
            total_records_in += len(df)

            # Get transformer
            transformer = get_transformer(target_domain, study_id)

            # Execute transformation
            result = transformer.execute(df)

            if result.success:
                sdtm_df = transformer.transform(df)
                total_records_out += len(sdtm_df)

                # Save output
                output_path = os.path.join(sdtm_dir, f"{target_domain.lower()}.csv")
                sdtm_df.to_csv(output_path, index=False)

                sdtm_data_paths[target_domain] = output_path

                print(f"  Records: {len(df)} -> {len(sdtm_df)}")
                print(f"  Saved to: {output_path}")

                transformation_results.append({
                    "success": True,
                    "source_domain": filename,
                    "target_domain": target_domain,
                    "records_processed": len(df),
                    "records_output": len(sdtm_df),
                    "output_path": output_path,
                    "errors": []
                })

                messages.append(f"Transformed {filename} -> {target_domain}: {len(df)} -> {len(sdtm_df)} records")

            else:
                transformation_results.append({
                    "success": False,
                    "source_domain": filename,
                    "target_domain": target_domain,
                    "records_processed": len(df),
                    "records_output": 0,
                    "output_path": None,
                    "errors": result.errors
                })
                messages.append(f"Transformation failed for {filename}: {result.errors}")

        except Exception as e:
            messages.append(f"Error transforming {filename}: {str(e)}")
            print(f"  ERROR: {str(e)}")

    return {
        "current_phase": "transformed",
        "phase_history": ["transformed"],
        "transformation_results": transformation_results,
        "sdtm_data_paths": sdtm_data_paths,
        "processing_stats": {
            "total_records_in": total_records_in,
            "total_records_out": total_records_out,
            "domains_transformed": len(sdtm_data_paths)
        },
        "messages": messages
    }


# ============================================================================
# Node: Validate SDTM Data
# ============================================================================

def validate_sdtm_node(state: SDTMPipelineState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node: Validate SDTM datasets against CDISC standards.

    Performs comprehensive validation including controlled terminology,
    required variables, and domain-specific rules.
    """
    print("\n" + "=" * 60)
    print("NODE: Validate SDTM Data")
    print("=" * 60)

    study_id = state.get("study_id", "UNKNOWN")
    sdtm_data_paths = state.get("sdtm_data_paths", {})
    output_dir = state.get("output_dir", "/tmp")

    validator = SDTMValidator(study_id)
    validation_results = []
    messages = []

    for domain, filepath in sdtm_data_paths.items():
        print(f"\nValidating SDTM {domain}")

        try:
            df = pd.read_csv(filepath)
            result = validator.validate_domain(df, domain)

            validation_result = {
                "is_valid": result.is_valid,
                "domain": result.domain,
                "total_records": result.total_records,
                "error_count": result.error_count,
                "warning_count": result.warning_count,
                "issues": [convert_to_serializable(i) for i in result.issues]
            }
            validation_results.append(validation_result)

            status = "PASS" if result.is_valid else "FAIL"
            print(f"  Records: {result.total_records}, Status: {status}")
            print(f"  Errors: {result.error_count}, Warnings: {result.warning_count}")

            messages.append(f"Validated SDTM {domain}: {status} ({result.error_count} errors)")

        except Exception as e:
            messages.append(f"Error validating SDTM {domain}: {str(e)}")
            print(f"  ERROR: {str(e)}")

    # Save validation report
    validation_dir = os.path.join(output_dir, "sdtm_validation")
    os.makedirs(validation_dir, exist_ok=True)

    report = validator.generate_report(
        [validator.validate_domain(pd.read_csv(p), d) for d, p in sdtm_data_paths.items()]
    )
    report_path = os.path.join(validation_dir, "validation_report.json")
    with open(report_path, 'w') as f:
        json.dump(convert_to_serializable(report), f, indent=2)

    messages.append(f"SDTM validation report saved to {report_path}")

    # Determine if submission ready
    submission_ready = all(r["is_valid"] for r in validation_results)

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
# Node: Generate Code
# ============================================================================

def generate_code_node(state: SDTMPipelineState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node: Generate SAS and R code for SDTM transformations.

    Creates production-ready code based on mapping specifications.
    """
    print("\n" + "=" * 60)
    print("NODE: Generate Code")
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

    # Generate SAS code
    print("\nGenerating SAS programs...")
    sas_dir = os.path.join(output_dir, "sas_programs")
    sas_generator = SASCodeGenerator(study_id, sas_dir)
    generated_sas_files = sas_generator.generate_all(specs)
    print(f"  Generated {len(generated_sas_files)} SAS programs")
    messages.append(f"Generated {len(generated_sas_files)} SAS programs")

    # Generate R code
    print("\nGenerating R scripts...")
    r_dir = os.path.join(output_dir, "r_programs")
    r_generator = RCodeGenerator(study_id, r_dir)
    generated_r_files = r_generator.generate_all(specs)
    print(f"  Generated {len(generated_r_files)} R scripts")
    messages.append(f"Generated {len(generated_r_files)} R scripts")

    return {
        "current_phase": "code_generated",
        "phase_history": ["code_generated"],
        "generated_sas_files": generated_sas_files,
        "generated_r_files": generated_r_files,
        "messages": messages
    }


# ============================================================================
# Node: Generate Final Report
# ============================================================================

def generate_report_node(state: SDTMPipelineState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node: Generate final pipeline execution report.

    Summarizes all processing results and creates comprehensive report.
    """
    print("\n" + "=" * 60)
    print("NODE: Generate Final Report")
    print("=" * 60)

    study_id = state.get("study_id", "UNKNOWN")
    output_dir = state.get("output_dir", "/tmp")
    selected_files = state.get("selected_files", [])
    transformation_results = state.get("transformation_results", [])
    sdtm_validation_results = state.get("sdtm_validation_results", [])
    mapping_specifications = state.get("mapping_specifications", [])
    generated_sas_files = state.get("generated_sas_files", {})
    generated_r_files = state.get("generated_r_files", {})
    processing_stats = state.get("processing_stats", {})

    # Calculate summary statistics
    total_raw_records = sum(
        r.get("total_records", 0) for r in state.get("raw_validation_results", [])
    )
    total_sdtm_records = sum(
        r.get("total_records", 0) for r in sdtm_validation_results
    )
    sdtm_errors = sum(
        r.get("error_count", 0) for r in sdtm_validation_results
    )

    submission_ready = sdtm_errors == 0

    final_report = {
        "study_id": study_id,
        "status": "success",
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "source_files_processed": len(selected_files),
            "sdtm_domains_created": len([t for t in transformation_results if t.get("success")]),
            "total_raw_records": total_raw_records,
            "total_sdtm_records": total_sdtm_records,
            "sdtm_validation_errors": sdtm_errors,
            "submission_ready": submission_ready
        },
        "domains": [
            {
                "domain": spec.get("target_domain"),
                "source": spec.get("source_domain"),
                "mappings": len(spec.get("column_mappings", []))
            }
            for spec in mapping_specifications
        ],
        "generated_code": {
            "sas_programs": len(generated_sas_files),
            "r_scripts": len(generated_r_files)
        },
        "output_directory": output_dir
    }

    # Save report
    reports_dir = os.path.join(output_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    report_path = os.path.join(reports_dir, "pipeline_report.json")

    with open(report_path, 'w') as f:
        json.dump(final_report, f, indent=2)

    print(f"\n Pipeline Summary:")
    print(f"  Source files: {final_report['summary']['source_files_processed']}")
    print(f"  SDTM domains: {final_report['summary']['sdtm_domains_created']}")
    print(f"  Records: {total_raw_records} -> {total_sdtm_records}")
    print(f"  Submission ready: {submission_ready}")
    print(f"\n Report saved to: {report_path}")

    return {
        "current_phase": "completed",
        "phase_history": ["completed"],
        "final_report": final_report,
        "messages": [f"Pipeline completed. Report saved to {report_path}"]
    }


# ============================================================================
# Node: Human Review
# ============================================================================

def human_review_node(state: SDTMPipelineState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node: Human review checkpoint.

    This node is used for interrupt_before in the graph to allow
    human review of results before proceeding.
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
            "messages": [f"Human rejected: {pending_review}"],
            "errors": [f"Pipeline rejected at {pending_review}"]
        }

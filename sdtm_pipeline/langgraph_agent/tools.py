"""
SDTM Pipeline Tools
===================
LangChain tools for SDTM transformation operations.
"""

import os
import json
import pandas as pd
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# Import SDTM pipeline components
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sdtm_pipeline.validators.raw_data_validator import RawDataValidator
from sdtm_pipeline.validators.sdtm_validator import SDTMValidator
from sdtm_pipeline.transformers.domain_transformers import get_transformer
from sdtm_pipeline.generators.sas_generator import SASCodeGenerator
from sdtm_pipeline.generators.r_generator import RCodeGenerator


# ============================================================================
# Tool Input Schemas
# ============================================================================

class ValidateRawDataInput(BaseModel):
    """Input for raw data validation tool."""
    file_path: str = Field(description="Path to the CSV file to validate")
    domain_name: str = Field(description="Name of the data domain")
    study_id: str = Field(default="UNKNOWN", description="Study identifier")


class TransformToSDTMInput(BaseModel):
    """Input for SDTM transformation tool."""
    file_path: str = Field(description="Path to the source CSV file")
    target_domain: str = Field(description="Target SDTM domain code (DM, AE, VS, LB, CM)")
    study_id: str = Field(description="Study identifier")
    output_dir: str = Field(description="Output directory for SDTM data")


class ValidateSDTMInput(BaseModel):
    """Input for SDTM validation tool."""
    file_path: str = Field(description="Path to the SDTM CSV file")
    domain_code: str = Field(description="SDTM domain code (DM, AE, VS, LB, CM)")
    study_id: str = Field(default="UNKNOWN", description="Study identifier")


class GenerateSASCodeInput(BaseModel):
    """Input for SAS code generation tool."""
    mapping_specs: List[Dict[str, Any]] = Field(description="List of mapping specifications")
    study_id: str = Field(description="Study identifier")
    output_dir: str = Field(description="Output directory for SAS programs")


class GenerateRCodeInput(BaseModel):
    """Input for R code generation tool."""
    mapping_specs: List[Dict[str, Any]] = Field(description="List of mapping specifications")
    study_id: str = Field(description="Study identifier")
    output_dir: str = Field(description="Output directory for R scripts")


class AnalyzeSourceDataInput(BaseModel):
    """Input for source data analysis tool."""
    file_path: str = Field(description="Path to the CSV file to analyze")


class DetermineSDTMDomainInput(BaseModel):
    """Input for SDTM domain determination tool."""
    file_name: str = Field(description="Name of the source file")
    columns: List[str] = Field(description="List of column names in the file")


# ============================================================================
# Tools
# ============================================================================

@tool(args_schema=ValidateRawDataInput)
def validate_raw_data(file_path: str, domain_name: str, study_id: str = "UNKNOWN") -> Dict[str, Any]:
    """
    Validate raw clinical trial data for quality and completeness.

    Performs checks including:
    - Required fields presence
    - Data type validation
    - Date format validation
    - Duplicate detection
    - Missing value analysis

    Returns validation result with issues found.
    """
    validator = RawDataValidator(study_id)
    result = validator.validate_file(file_path)

    return {
        "is_valid": result.is_valid,
        "domain": result.domain,
        "total_records": result.total_records,
        "error_count": result.error_count,
        "warning_count": result.warning_count,
        "issues": [issue.to_dict() for issue in result.issues]
    }


@tool(args_schema=TransformToSDTMInput)
def transform_to_sdtm(
    file_path: str,
    target_domain: str,
    study_id: str,
    output_dir: str
) -> Dict[str, Any]:
    """
    Transform raw clinical data to SDTM format.

    Supports domains: DM (Demographics), AE (Adverse Events),
    VS (Vital Signs), LB (Laboratory), CM (Concomitant Medications).

    Returns transformation result with output file path.
    """
    try:
        # Read source data
        df = pd.read_csv(file_path)

        # Get transformer for domain
        transformer = get_transformer(target_domain, study_id)

        # Execute transformation
        result = transformer.execute(df)

        if result.success:
            # Get transformed data
            sdtm_df = transformer.transform(df)

            # Save output
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{target_domain.lower()}.csv")
            sdtm_df.to_csv(output_path, index=False)

            return {
                "success": True,
                "source_domain": os.path.basename(file_path),
                "target_domain": target_domain,
                "records_processed": result.records_processed,
                "records_output": len(sdtm_df),
                "output_path": output_path,
                "transformation_log": result.transformation_log,
                "errors": []
            }
        else:
            return {
                "success": False,
                "source_domain": os.path.basename(file_path),
                "target_domain": target_domain,
                "records_processed": result.records_processed,
                "records_output": 0,
                "output_path": None,
                "transformation_log": result.transformation_log,
                "errors": result.errors
            }

    except Exception as e:
        return {
            "success": False,
            "source_domain": os.path.basename(file_path),
            "target_domain": target_domain,
            "records_processed": 0,
            "records_output": 0,
            "output_path": None,
            "errors": [str(e)]
        }


@tool(args_schema=ValidateSDTMInput)
def validate_sdtm_data(
    file_path: str,
    domain_code: str,
    study_id: str = "UNKNOWN"
) -> Dict[str, Any]:
    """
    Validate SDTM dataset against CDISC standards and FDA rules.

    Checks include:
    - Required variables presence
    - Controlled terminology compliance
    - Date format validation (ISO 8601)
    - Cross-variable consistency
    - Domain-specific rules

    Returns validation result with compliance issues.
    """
    validator = SDTMValidator(study_id)

    try:
        df = pd.read_csv(file_path)
        result = validator.validate_domain(df, domain_code)

        return {
            "is_valid": result.is_valid,
            "domain": result.domain,
            "total_records": result.total_records,
            "error_count": result.error_count,
            "warning_count": result.warning_count,
            "issues": [issue.to_dict() for issue in result.issues],
            "submission_ready": result.is_valid
        }

    except Exception as e:
        return {
            "is_valid": False,
            "domain": domain_code,
            "total_records": 0,
            "error_count": 1,
            "warning_count": 0,
            "issues": [{"rule_id": "ERROR", "severity": "error", "message": str(e)}],
            "submission_ready": False
        }


@tool(args_schema=GenerateSASCodeInput)
def generate_sas_code(
    mapping_specs: List[Dict[str, Any]],
    study_id: str,
    output_dir: str
) -> Dict[str, str]:
    """
    Generate production-ready SAS programs for SDTM transformations.

    Creates:
    - Setup program with macros and library definitions
    - Domain-specific transformation programs
    - Master driver program

    Returns dictionary of program names to file paths.
    """
    from sdtm_pipeline.models.sdtm_models import MappingSpecification, ColumnMapping

    # Convert dict specs to MappingSpecification objects
    specs = []
    for spec_dict in mapping_specs:
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

    generator = SASCodeGenerator(study_id, output_dir)
    return generator.generate_all(specs)


@tool(args_schema=GenerateRCodeInput)
def generate_r_code(
    mapping_specs: List[Dict[str, Any]],
    study_id: str,
    output_dir: str
) -> Dict[str, str]:
    """
    Generate R scripts for SDTM transformations using pharmaverse packages.

    Creates:
    - Setup script with package loading and utility functions
    - Domain-specific transformation scripts
    - Master driver script
    - Validation script

    Returns dictionary of script names to file paths.
    """
    from sdtm_pipeline.models.sdtm_models import MappingSpecification, ColumnMapping

    # Convert dict specs to MappingSpecification objects
    specs = []
    for spec_dict in mapping_specs:
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

    generator = RCodeGenerator(study_id, output_dir)
    return generator.generate_all(specs)


@tool(args_schema=AnalyzeSourceDataInput)
def analyze_source_data(file_path: str) -> Dict[str, Any]:
    """
    Analyze source data structure and content.

    Returns:
    - Column names and types
    - Record count
    - Sample values
    - Data quality indicators
    """
    try:
        df = pd.read_csv(file_path)

        analysis = {
            "file_name": os.path.basename(file_path),
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": []
        }

        for col in df.columns:
            col_info = {
                "name": col,
                "dtype": str(df[col].dtype),
                "non_null_count": int(df[col].notna().sum()),
                "null_count": int(df[col].isna().sum()),
                "unique_count": int(df[col].nunique()),
                "sample_values": [str(v) for v in df[col].dropna().head(3).tolist()]
            }
            analysis["columns"].append(col_info)

        return analysis

    except Exception as e:
        return {
            "file_name": os.path.basename(file_path),
            "error": str(e)
        }


@tool(args_schema=DetermineSDTMDomainInput)
def determine_sdtm_domain(file_name: str, columns: List[str]) -> Dict[str, Any]:
    """
    Determine the appropriate SDTM domain for source data.

    Analyzes file name and column names to suggest the best
    SDTM domain mapping (DM, AE, VS, LB, CM, EX, etc.).
    """
    file_upper = file_name.upper().replace(".CSV", "")

    # Domain mapping based on common EDC names
    domain_mapping = {
        "DEMO": ("DM", "Demographics"),
        "DEMOGRAPHY": ("DM", "Demographics"),
        "AEVENT": ("AE", "Adverse Events"),
        "AE": ("AE", "Adverse Events"),
        "ADVERSE": ("AE", "Adverse Events"),
        "VITALS": ("VS", "Vital Signs"),
        "VS": ("VS", "Vital Signs"),
        "VITAL": ("VS", "Vital Signs"),
        "CHEMLAB": ("LB", "Laboratory - Chemistry"),
        "HEMLAB": ("LB", "Laboratory - Hematology"),
        "LAB": ("LB", "Laboratory"),
        "CONMEDS": ("CM", "Concomitant Medications"),
        "CM": ("CM", "Concomitant Medications"),
        "DOSE": ("EX", "Exposure"),
        "EXPOSURE": ("EX", "Exposure"),
    }

    # Check file name
    for key, (domain, desc) in domain_mapping.items():
        if key in file_upper:
            return {
                "file_name": file_name,
                "suggested_domain": domain,
                "domain_description": desc,
                "confidence": "high",
                "reason": f"File name contains '{key}'"
            }

    # Check column names for hints
    columns_upper = [c.upper() for c in columns]

    if any("AETERM" in c or "ADVERSE" in c for c in columns_upper):
        return {
            "file_name": file_name,
            "suggested_domain": "AE",
            "domain_description": "Adverse Events",
            "confidence": "medium",
            "reason": "Contains adverse event related columns"
        }

    if any("VITAL" in c or "SYSBP" in c or "DIABP" in c for c in columns_upper):
        return {
            "file_name": file_name,
            "suggested_domain": "VS",
            "domain_description": "Vital Signs",
            "confidence": "medium",
            "reason": "Contains vital sign related columns"
        }

    if any("LAB" in c or "TEST" in c for c in columns_upper):
        return {
            "file_name": file_name,
            "suggested_domain": "LB",
            "domain_description": "Laboratory",
            "confidence": "medium",
            "reason": "Contains laboratory related columns"
        }

    # Default
    return {
        "file_name": file_name,
        "suggested_domain": "DM",
        "domain_description": "Demographics (default)",
        "confidence": "low",
        "reason": "Could not determine domain from file or columns"
    }


# List of all tools
ALL_TOOLS = [
    validate_raw_data,
    transform_to_sdtm,
    validate_sdtm_data,
    generate_sas_code,
    generate_r_code,
    analyze_source_data,
    determine_sdtm_domain,
]

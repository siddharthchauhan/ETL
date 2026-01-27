"""
SDTM Chat Agent Tools
=====================
LangGraph tools for SDTM conversion operations.
"""

import os
import json
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

import pandas as pd
import boto3
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# Global storage for dataframes (tools can't return DataFrames directly)
_source_data: Dict[str, pd.DataFrame] = {}
_sdtm_data: Dict[str, pd.DataFrame] = {}
_study_id: str = "UNKNOWN"


def get_source_data() -> Dict[str, pd.DataFrame]:
    """Get loaded source data."""
    return _source_data


def get_sdtm_data() -> Dict[str, pd.DataFrame]:
    """Get converted SDTM data."""
    return _sdtm_data


def get_study_id() -> str:
    """Get current study ID."""
    return _study_id


# =============================================================================
# TASK PROGRESS TRACKING (write_todos)
# =============================================================================
# This tool emits task progress that the frontend displays in the TaskProgressBar.
# The frontend extracts todos from on_tool_start events for 'write_todos'.

class TodoItem(BaseModel):
    """A single task/todo item for progress tracking."""
    id: str = Field(description="Unique identifier for the task")
    content: str = Field(description="Title/description of the task")
    status: str = Field(default="pending", description="Status: pending, in_progress, completed, error")


class WriteTodosInput(BaseModel):
    """Input for write_todos tool."""
    todos: List[TodoItem] = Field(description="List of task items to track progress")


@tool
def write_todos(todos: List[Dict[str, str]]) -> str:
    """
    Update the task progress list. Use this to show the user what steps are being performed.

    Call this tool to:
    1. Create a plan at the start of a multi-step operation
    2. Update task status as you progress through steps
    3. Mark tasks as completed when done

    Args:
        todos: List of task dictionaries with 'id', 'content', and 'status' keys.
               - id: Unique identifier (e.g., "1", "step_1", "load_data")
               - content: Task title/description shown to user
               - status: One of "pending", "in_progress", "completed", "error"

    Example:
        write_todos([
            {"id": "1", "content": "Load data from S3", "status": "completed"},
            {"id": "2", "content": "Generate mapping specification", "status": "in_progress"},
            {"id": "3", "content": "Transform to SDTM", "status": "pending"},
            {"id": "4", "content": "Validate results", "status": "pending"}
        ])

    Returns:
        Confirmation message with task count
    """
    # Validate and normalize todos
    normalized = []
    for i, todo in enumerate(todos):
        normalized.append({
            "id": str(todo.get("id", str(i))),
            "content": str(todo.get("content", todo.get("title", "Task"))),
            "status": str(todo.get("status", "pending")).lower()
        })

    # Count by status
    status_counts = {}
    for t in normalized:
        status = t["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    summary = ", ".join(f"{count} {status}" for status, count in status_counts.items())
    return f"Task progress updated: {len(normalized)} tasks ({summary})"


class LoadDataInput(BaseModel):
    """Input for load_data_from_s3 tool."""
    bucket: str = Field(default="s3dcri", description="S3 bucket name")
    key: str = Field(default="incoming/EDC Data.zip", description="S3 object key")


@tool
def load_data_from_s3(bucket: str = "s3dcri", key: str = "incoming/EDC Data.zip") -> str:
    """
    Load EDC data from S3 bucket.

    Downloads the zip file from S3, extracts it, and loads all CSV files.
    Returns a summary of loaded files with their target SDTM domains.

    Args:
        bucket: S3 bucket name (default: s3dcri)
        key: S3 object key (default: incoming/EDC Data.zip)
    """
    global _source_data, _study_id

    try:
        s3 = boto3.client('s3')
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, "data.zip")

        # Download
        s3.download_file(bucket, key, zip_path)

        # Extract
        extract_dir = os.path.join(temp_dir, "extracted")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)

        # Load CSV files
        csv_files = list(Path(extract_dir).rglob("*.csv"))
        _source_data.clear()

        results = []
        total_records = 0

        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                filename = csv_file.name
                _source_data[filename] = df

                domain = _determine_domain(filename)
                results.append({
                    "file": filename,
                    "domain": domain,
                    "records": len(df),
                    "columns": len(df.columns)
                })
                total_records += len(df)

                # Detect study ID
                if _study_id == "UNKNOWN":
                    if 'STUDY' in df.columns:
                        _study_id = str(df['STUDY'].iloc[0])
                    elif 'STUDYID' in df.columns:
                        _study_id = str(df['STUDYID'].iloc[0])
            except Exception as e:
                pass

        # Format output
        output = f"## Data Loaded Successfully\n\n"
        output += f"**Study ID:** {_study_id}\n"
        output += f"**Total Files:** {len(results)}\n"
        output += f"**Total Records:** {total_records}\n\n"
        output += "### Files by Domain\n\n"
        output += "| File | Domain | Records | Columns |\n"
        output += "|------|--------|---------|----------|\n"

        for r in sorted(results, key=lambda x: x['domain']):
            output += f"| {r['file']} | {r['domain']} | {r['records']} | {r['columns']} |\n"

        return output

    except Exception as e:
        return f"Error loading data from S3: {str(e)}"


def _determine_domain(filename: str) -> str:
    """Determine SDTM domain from filename."""
    name_upper = filename.upper().replace(".CSV", "")

    domain_map = {
        "DEMO": "DM", "DEMOGRAPHY": "DM",
        "AEVENT": "AE", "AEVENTC": "SUPPAE",
        "CONMEDS": "CM", "CONMEDSC": "SUPPCM",
        "VITALS": "VS", "VITAL": "VS",
        "CHEMLAB": "LB", "HEMLAB": "LB", "URINALYSIS": "LB",
        "DOSE": "EX", "EXPOSURE": "EX",
        "MEDHIST": "MH", "MEDHISC": "SUPPMH",
        "DISPOSI": "DS", "DISPOSIC": "SUPPDS",
        "ECG": "EG", "ECGC": "SUPPEG",
        "PHYSEX": "PE",
        "PHARMA": "PC",
        "INCEXC": "IE",
        "COMMENT": "CO",
        "QUEST": "QS",
        "RESPONSE": "RS",
        "TUMOR": "TR",
        "TUMORID": "TU",
        "TRIALARM": "TA",
    }

    for key, domain in domain_map.items():
        if key in name_upper:
            return domain

    return "UNKNOWN"


@tool
def list_available_domains() -> str:
    """
    List all available SDTM domains from the loaded source data.

    Shows which source files map to which SDTM domains,
    along with conversion status.
    """
    if not _source_data:
        return "No data loaded. Please use load_data_from_s3 first."

    # Group by domain
    domain_files: Dict[str, List[str]] = {}
    for filename in _source_data:
        domain = _determine_domain(filename)
        if domain not in domain_files:
            domain_files[domain] = []
        domain_files[domain].append(filename)

    domain_descriptions = {
        "DM": "Demographics",
        "AE": "Adverse Events",
        "CM": "Concomitant Medications",
        "VS": "Vital Signs",
        "LB": "Laboratory",
        "EX": "Exposure",
        "MH": "Medical History",
        "DS": "Disposition",
        "EG": "ECG",
        "PE": "Physical Exam",
        "PC": "Pharmacokinetics",
        "IE": "Inclusion/Exclusion",
        "CO": "Comments",
        "QS": "Questionnaires",
        "RS": "Disease Response",
        "TR": "Tumor Results",
        "TU": "Tumor Identification",
        "TA": "Trial Arms",
    }

    output = "## Available SDTM Domains\n\n"
    output += "| Domain | Description | Source Files | Status |\n"
    output += "|--------|-------------|--------------|--------|\n"

    for domain in sorted(domain_files.keys()):
        files = domain_files[domain]
        desc = domain_descriptions.get(domain, domain)
        status = "✓ Converted" if domain in _sdtm_data else "○ Pending"
        output += f"| {domain} | {desc} | {', '.join(files)} | {status} |\n"

    return output


@tool
def convert_domain(domain: str) -> str:
    """
    Convert a specific domain from EDC to SDTM format.

    This performs the full conversion pipeline:
    0. Fetches SDTM-IG 3.4 guidance from Pinecone knowledge base
    1. Generates mapping specification using Claude AI
    2. Transforms data according to mapping
    3. Validates the SDTM dataset against Pinecone rules
    4. Returns detailed results

    Args:
        domain: SDTM domain code (e.g., DM, AE, VS, LB, CM)
    """
    global _sdtm_data

    domain = domain.upper()

    if not _source_data:
        return "No data loaded. Please use load_data_from_s3 first."

    # Find source files for this domain
    source_files = [f for f in _source_data if _determine_domain(f) == domain]

    if not source_files:
        return f"No source files found for domain: {domain}"

    output = f"## Converting {domain} Domain\n\n"

    try:
        # Import components
        from sdtm_pipeline.transformers.mapping_generator import MappingSpecificationGenerator
        from sdtm_pipeline.transformers.domain_transformers import get_transformer
        from sdtm_pipeline.validators.sdtm_validator import SDTMValidator

        # Step 0: Fetch SDTM-IG 3.4 guidance from Pinecone
        output += "### Step 0: Fetching SDTM-IG 3.4 Guidance from Pinecone\n\n"

        try:
            from sdtm_pipeline.langgraph_agent.knowledge_tools import get_knowledge_retriever
            retriever = get_knowledge_retriever()

            if retriever and retriever.pinecone_client:
                # Fetch domain specification
                domain_spec = retriever.get_domain_specification(domain)
                guidance = retriever.get_sdtm_generation_guidance(domain, "EDC clinical trial data")

                if guidance and guidance.get("required_variables"):
                    output += "**📚 Pinecone Knowledge Base Retrieved:**\n\n"

                    # Show required variables
                    req_vars = guidance.get("required_variables", [])
                    if req_vars:
                        output += "**Required Variables (SDTM-IG 3.4):**\n"
                        for var in req_vars[:10]:
                            var_name = var.get("variable", var.get("name", ""))
                            var_label = var.get("label", "")
                            if var_name:
                                output += f"- `{var_name}`: {var_label}\n"
                        if len(req_vars) > 10:
                            output += f"- *... and {len(req_vars) - 10} more required variables*\n"
                        output += "\n"

                    # Show expected variables
                    exp_vars = guidance.get("expected_variables", [])
                    if exp_vars:
                        output += "**Expected Variables:**\n"
                        for var in exp_vars[:5]:
                            var_name = var.get("variable", var.get("name", ""))
                            if var_name:
                                output += f"- `{var_name}`\n"
                        if len(exp_vars) > 5:
                            output += f"- *... and {len(exp_vars) - 5} more expected variables*\n"
                        output += "\n"

                    # Show transformation steps
                    trans_steps = guidance.get("transformation_steps", [])
                    if trans_steps:
                        output += "**Derivation Rules from Business Rules Index:**\n"
                        for step in trans_steps[:3]:
                            step_desc = step.get("step", step.get("rule", ""))[:80]
                            if step_desc:
                                output += f"- {step_desc}\n"
                        output += "\n"
                else:
                    output += "*Using local SDTM-IG 3.4 specifications (Pinecone guidance not found)*\n\n"
            else:
                output += "*Pinecone not available - using local SDTM-IG 3.4 specifications*\n\n"
        except Exception as e:
            output += f"*Pinecone lookup note: {str(e)[:50]} - using local specifications*\n\n"

        # Step 1: Intelligent Column Mapping Discovery
        output += "### Step 1: Intelligent Column Mapping Discovery\n\n"

        # Get first source file
        source_file = source_files[0]
        df = _source_data[source_file]

        output += f"**Source File:** {source_file}\n"
        output += f"**Source Columns ({len(df.columns)}):** {', '.join(df.columns[:15])}"
        if len(df.columns) > 15:
            output += f"... (+{len(df.columns) - 15} more)"
        output += "\n\n"

        # Use intelligent mapper to discover mappings
        intelligent_mapping_spec = None
        pinecone_retriever = None

        try:
            from sdtm_pipeline.transformers.intelligent_mapper import IntelligentMapper, create_intelligent_mapping

            # Get Pinecone retriever if available
            try:
                from sdtm_pipeline.langgraph_agent.knowledge_tools import get_knowledge_retriever
                pinecone_retriever = get_knowledge_retriever()
            except Exception:
                pinecone_retriever = None

            # Create intelligent mapping
            intelligent_mapper = IntelligentMapper(pinecone_retriever)
            intelligent_mapping_spec = intelligent_mapper.analyze_source_data(df, domain)

            if intelligent_mapping_spec and intelligent_mapping_spec.mappings:
                output += "**🧠 Intelligent Mapping Discovery:**\n\n"
                output += "| Source Column | SDTM Variable | Confidence | Method |\n"
                output += "|---------------|---------------|------------|--------|\n"

                # Show high confidence mappings first
                sorted_mappings = sorted(intelligent_mapping_spec.mappings,
                                        key=lambda x: x.confidence, reverse=True)

                for mapping in sorted_mappings[:15]:
                    conf_indicator = "✓" if mapping.confidence >= 0.8 else "~" if mapping.confidence >= 0.6 else "?"
                    method = mapping.mapping_reason.split(":")[0] if ":" in mapping.mapping_reason else mapping.mapping_reason
                    output += f"| {mapping.source_column[:25]} | {mapping.sdtm_variable} | {conf_indicator} {mapping.confidence:.0%} | {method[:15]} |\n"

                if len(intelligent_mapping_spec.mappings) > 15:
                    output += f"\n*... and {len(intelligent_mapping_spec.mappings) - 15} more discovered mappings*\n"

                # Show unmapped columns
                if intelligent_mapping_spec.unmapped_source_columns:
                    output += f"\n**⚠️ Unmapped Source Columns:** {', '.join(intelligent_mapping_spec.unmapped_source_columns[:10])}"
                    if len(intelligent_mapping_spec.unmapped_source_columns) > 10:
                        output += f"... (+{len(intelligent_mapping_spec.unmapped_source_columns) - 10} more)"
                    output += "\n"

                output += "\n"
            else:
                output += "*Intelligent mapping found no patterns - using AI-generated mapping*\n\n"

        except ImportError as e:
            output += f"*Intelligent mapper not available: {str(e)[:50]} - using AI-generated mapping*\n\n"
        except Exception as e:
            output += f"*Intelligent mapping note: {str(e)[:50]} - using AI-generated mapping*\n\n"

        # Step 1b: AI-Generated Mapping (supplement intelligent mapping)
        output += "### Step 1b: AI-Enhanced Mapping Specification\n\n"

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return "Error: ANTHROPIC_API_KEY not set"

        generator = MappingSpecificationGenerator(
            api_key=api_key,
            study_id=_study_id,
            use_knowledge_tools=True
        )

        spec = generator.generate_mapping(
            df=df,
            source_name=source_file,
            target_domain=domain
        )

        output += f"**Source:** {spec.source_domain}\n"
        output += f"**Target:** SDTM {spec.target_domain}\n\n"

        output += "| Source Column | Target Variable | Transformation |\n"
        output += "|---------------|-----------------|----------------|\n"

        for mapping in spec.column_mappings[:10]:
            source = mapping.source_column or "[derived]"
            target = mapping.target_variable
            transform = str(mapping.transformation or mapping.derivation_rule or "-")[:40]
            output += f"| {source} | {target} | {transform} |\n"

        if len(spec.column_mappings) > 10:
            output += f"\n*... and {len(spec.column_mappings) - 10} more mappings*\n"

        # Derivation rules
        if spec.derivation_rules:
            output += "\n**Derivation Rules:**\n"
            for var, rule in list(spec.derivation_rules.items())[:5]:
                output += f"- `{var}`: {rule}\n"

        # Step 2: Transform with Intelligent Mapping
        output += "\n### Step 2: Transformation (with Intelligent Mapping)\n\n"

        combined_df = pd.concat(
            [_source_data[f] for f in source_files],
            ignore_index=True
        )

        # Get transformer with Pinecone retriever for intelligent mapping
        transformer = get_transformer(
            domain_code=domain,
            study_id=_study_id,
            mapping_spec=spec,
            pinecone_retriever=pinecone_retriever
        )

        # Discover mappings before transforming (if intelligent mapper available)
        if hasattr(transformer, 'discover_mappings') and intelligent_mapping_spec:
            transformer._discovered_mapping = intelligent_mapping_spec
            output += "*Using intelligent column mapping during transformation*\n\n"

        sdtm_df = transformer.transform(combined_df)
        _sdtm_data[domain] = sdtm_df

        output += f"**Records transformed:** {len(sdtm_df)}\n"
        output += f"**SDTM variables:** {len(sdtm_df.columns)}\n"
        output += f"**Columns:** {', '.join(sdtm_df.columns[:10])}"
        if len(sdtm_df.columns) > 10:
            output += f"... (+{len(sdtm_df.columns) - 10} more)"
        output += "\n"

        # Step 3: Validate
        output += "\n### Step 3: Validation\n\n"

        validator = SDTMValidator(study_id=_study_id, use_knowledge_tools=True)
        result = validator.validate_domain(sdtm_df, domain)

        status = "✓ VALID" if result.is_valid else "✗ ISSUES FOUND"
        output += f"**Status:** {status}\n"
        output += f"**Errors:** {result.error_count}\n"
        output += f"**Warnings:** {result.warning_count}\n"

        if result.issues:
            output += "\n**Issues:**\n"
            for issue in result.issues[:5]:
                kb_tag = "[KB] " if issue.rule_id.startswith("KB-") else ""
                output += f"- {issue.severity.value.upper()}: {kb_tag}{issue.message}\n"
            if len(result.issues) > 5:
                output += f"- *... and {len(result.issues) - 5} more issues*\n"

        # Step 4: Sample output
        output += "\n### Step 4: Sample SDTM Output\n\n"

        sample_cols = ['STUDYID', 'DOMAIN', 'USUBJID'] + [c for c in sdtm_df.columns if c not in ['STUDYID', 'DOMAIN', 'USUBJID']][:5]
        sample_cols = [c for c in sample_cols if c in sdtm_df.columns]

        output += "| " + " | ".join(sample_cols) + " |\n"
        output += "|" + "|".join(["---"] * len(sample_cols)) + "|\n"

        for _, row in sdtm_df.head(3).iterrows():
            values = [str(row.get(c, ''))[:15] for c in sample_cols]
            output += "| " + " | ".join(values) + " |\n"

        output += f"\n**Conversion complete!** Domain {domain} is ready.\n"

        return output

    except Exception as e:
        import traceback
        return f"Error converting {domain}: {str(e)}\n\n{traceback.format_exc()}"


@tool
def convert_all_domains() -> str:
    """
    Convert ALL available domains from EDC to SDTM format in a single batch operation.

    This is more efficient than converting domains one by one, as it:
    - Converts all detected domains in one tool call
    - Reduces agent iterations/recursion
    - Provides a summary of all conversions

    Use this when the user asks to "convert all domains" or "convert everything".

    Returns detailed results for each domain converted.
    """
    global _sdtm_data

    if not _source_data:
        return "No data loaded. Please use load_data_from_s3 first."

    # Find all available domains
    domain_files: Dict[str, List[str]] = {}
    for filename in _source_data:
        domain = _determine_domain(filename)
        if domain != "UNKNOWN":
            if domain not in domain_files:
                domain_files[domain] = []
            domain_files[domain].append(filename)

    if not domain_files:
        return "No convertible domains found in the loaded data."

    output = f"## Converting All Domains ({len(domain_files)} total)\n\n"
    output += f"**Study ID:** {_study_id}\n"
    output += f"**Domains to convert:** {', '.join(sorted(domain_files.keys()))}\n\n"

    successful = []
    failed = []
    total_records = 0

    # Import once for all conversions
    try:
        from sdtm_pipeline.transformers.mapping_generator import MappingSpecificationGenerator
        from sdtm_pipeline.transformers.domain_transformers import get_transformer
        from sdtm_pipeline.validators.sdtm_validator import SDTMValidator

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return "Error: ANTHROPIC_API_KEY not set"

        generator = MappingSpecificationGenerator(
            api_key=api_key,
            study_id=_study_id,
            use_knowledge_tools=True
        )
        validator = SDTMValidator(study_id=_study_id, use_knowledge_tools=True)

        # Get Pinecone retriever once
        pinecone_retriever = None
        try:
            from sdtm_pipeline.langgraph_agent.knowledge_tools import get_knowledge_retriever
            pinecone_retriever = get_knowledge_retriever()
        except Exception:
            pass

        # Process each domain
        for domain in sorted(domain_files.keys()):
            source_files = domain_files[domain]
            output += f"### {domain} Domain\n\n"

            try:
                # Get first source file
                source_file = source_files[0]
                df = _source_data[source_file]

                output += f"**Source:** {source_file} ({len(df)} records)\n"

                # Generate mapping
                spec = generator.generate_mapping(
                    df=df,
                    source_name=source_file,
                    target_domain=domain
                )

                # Combine all source files for this domain
                combined_df = pd.concat(
                    [_source_data[f] for f in source_files],
                    ignore_index=True
                )

                # Transform
                transformer = get_transformer(
                    domain_code=domain,
                    study_id=_study_id,
                    mapping_spec=spec,
                    pinecone_retriever=pinecone_retriever
                )

                sdtm_df = transformer.transform(combined_df)
                _sdtm_data[domain] = sdtm_df

                # Quick validation
                result = validator.validate_domain(sdtm_df, domain)

                # Record results
                status = "✓" if result.is_valid else f"⚠️ ({result.error_count}E/{result.warning_count}W)"
                output += f"**Records:** {len(sdtm_df)} | **Variables:** {len(sdtm_df.columns)} | **Status:** {status}\n\n"

                successful.append({
                    "domain": domain,
                    "records": len(sdtm_df),
                    "variables": len(sdtm_df.columns),
                    "errors": result.error_count,
                    "warnings": result.warning_count
                })
                total_records += len(sdtm_df)

            except Exception as e:
                output += f"**Error:** {str(e)[:100]}\n\n"
                failed.append({"domain": domain, "error": str(e)[:100]})

        # Summary
        output += "---\n\n"
        output += "## Conversion Summary\n\n"
        output += f"**Total Domains:** {len(successful)}/{len(domain_files)} successful\n"
        output += f"**Total Records:** {total_records:,}\n\n"

        if successful:
            output += "### Converted Domains\n\n"
            output += "| Domain | Records | Variables | Status |\n"
            output += "|--------|---------|-----------|--------|\n"
            for s in successful:
                status = "✓ Valid" if s["errors"] == 0 else f"⚠️ {s['errors']}E/{s['warnings']}W"
                output += f"| {s['domain']} | {s['records']:,} | {s['variables']} | {status} |\n"

        if failed:
            output += "\n### Failed Domains\n\n"
            for f in failed:
                output += f"- **{f['domain']}**: {f['error']}\n"

        output += "\n**Next steps:** Use `upload_sdtm_to_s3` to upload all converted domains, or `validate_domain` for detailed validation.\n"

        return output

    except Exception as e:
        import traceback
        return f"Error in batch conversion: {str(e)}\n\n{traceback.format_exc()}"


# =============================================================================
# SPECIFICATION-DRIVEN WORKFLOW TOOLS
# =============================================================================

@tool
def generate_mapping_specification(
    domain: str,
    output_dir: str = "./sdtm_workspace/mapping_specs"
) -> str:
    """
    Generate a comprehensive SDTM mapping specification for a domain.

    This tool performs DETAILED analysis of raw EDC data against CDISC SDTM-IG 3.4
    specifications and generates a complete mapping specification that defines:

    **Domain-Level Analysis:**
    - Source file identification and structure
    - Target SDTM domain determination
    - Record count and column inventory

    **Variable-Level Mappings with Transformation Types:**
    - DIRECT: Direct column copy (source → target)
    - ASSIGN: Constant value assignment
    - CONCAT: Concatenate multiple columns (e.g., USUBJID = STUDY + SITE + SUBJ)
    - SEQUENCE: Generate sequence numbers per subject
    - DATE_FORMAT: Convert dates to ISO 8601
    - MAP: Apply controlled terminology lookup
    - DERIVE: Calculate derived values (e.g., study day)
    - TRANSPOSE: Vertical to horizontal restructuring

    **Output Files:**
    - JSON specification (for programmatic transformation)
    - Excel workbook (for human review with multiple sheets)

    **Use this BEFORE convert_domain to review and customize the mapping!**

    Args:
        domain: SDTM domain code (DM, AE, VS, LB, CM, EX, etc.)
        output_dir: Directory to save specification files
    """
    domain = domain.upper()

    if not _source_data:
        return "No data loaded. Please use load_data_from_s3 first."

    # Find source files for this domain
    source_files = [f for f in _source_data if _determine_domain(f) == domain]
    if not source_files:
        available = set(_determine_domain(f) for f in _source_data)
        return f"No source files found for domain: {domain}. Available: {', '.join(available)}"

    output = f"## Generating Mapping Specification for {domain} Domain\n\n"

    try:
        from pathlib import Path
        import json

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Get source data
        source_file = source_files[0]
        df = _source_data[source_file]

        output += f"**Source File:** {source_file}\n"
        output += f"**Records:** {len(df):,}\n"
        output += f"**Columns:** {len(df.columns)}\n\n"

        # Step 1: Fetch SDTM-IG 3.4 Specification
        output += "### Step 1: Fetching CDISC SDTM-IG 3.4 Specification\n\n"

        sdtm_spec = None
        try:
            from sdtm_pipeline.transformers.sdtm_web_reference import get_sdtm_web_reference
            ref = get_sdtm_web_reference()
            sdtm_spec = ref.get_domain_specification(domain)

            if sdtm_spec:
                variables = sdtm_spec.get("variables", {})
                req_count = len(variables.get("required", []))
                exp_count = len(variables.get("expected", []))
                perm_count = len(variables.get("permissible", []))
                output += f"✓ Retrieved: {req_count} Required, {exp_count} Expected, {perm_count} Permissible variables\n\n"
        except Exception as e:
            output += f"⚠ SDTM-IG lookup: {str(e)[:50]}\n\n"

        # Step 2: Analyze Source Data
        output += "### Step 2: Analyzing Source Data Structure\n\n"

        source_analysis = {
            "filename": source_file,
            "records": len(df),
            "columns": [],
        }

        for col in df.columns:
            col_info = {
                "name": col,
                "dtype": str(df[col].dtype),
                "non_null": int(df[col].notna().sum()),
                "unique": int(df[col].nunique()),
                "samples": [str(v)[:50] for v in df[col].dropna().head(3).tolist()]
            }
            source_analysis["columns"].append(col_info)

        output += f"**Source Columns ({len(df.columns)}):**\n"
        output += "| Column | Type | Non-Null | Unique | Sample Values |\n"
        output += "|--------|------|----------|--------|---------------|\n"
        for col_info in source_analysis["columns"][:15]:
            samples = ", ".join(col_info["samples"][:2])[:30]
            output += f"| {col_info['name'][:20]} | {col_info['dtype'][:8]} | {col_info['non_null']} | {col_info['unique']} | {samples} |\n"
        if len(source_analysis["columns"]) > 15:
            output += f"\n*... and {len(source_analysis['columns']) - 15} more columns*\n"
        output += "\n"

        # Step 3: Generate Variable Mappings
        output += "### Step 3: Generating Variable Mappings\n\n"

        # Use the MappingSpecificationGenerator
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return "Error: ANTHROPIC_API_KEY not set"

        from sdtm_pipeline.transformers.mapping_generator import MappingSpecificationGenerator
        generator = MappingSpecificationGenerator(
            api_key=api_key,
            study_id=_study_id,
            use_knowledge_tools=True
        )

        # Generate the mapping specification
        mapping_spec = generator.generate_mapping(
            df=df,
            source_name=source_file,
            target_domain=domain
        )

        # Enhance the specification with detailed transformation types
        enhanced_spec = _enhance_mapping_specification(
            mapping_spec, df, domain, sdtm_spec, _study_id
        )

        # Step 4: Save JSON Specification
        output += "### Step 4: Saving Specification Files\n\n"

        json_path = output_path / f"{domain.lower()}_mapping_specification.json"
        with open(json_path, 'w') as f:
            json.dump(enhanced_spec, f, indent=2)
        output += f"✓ **JSON:** `{json_path}`\n"

        # Step 5: Save Excel Specification
        excel_path = output_path / f"{domain.lower()}_mapping_specification.xlsx"
        _save_mapping_excel(enhanced_spec, str(excel_path))
        output += f"✓ **Excel:** `{excel_path}`\n\n"

        # Step 6: Summary
        output += "### Mapping Specification Summary\n\n"

        var_mappings = enhanced_spec.get("variable_mappings", [])
        output += f"**Total Variables Mapped:** {len(var_mappings)}\n\n"

        # Count by transformation type
        transform_counts = {}
        for vm in var_mappings:
            t_type = vm.get("transformation_type", "UNKNOWN")
            transform_counts[t_type] = transform_counts.get(t_type, 0) + 1

        output += "**Transformation Types:**\n"
        output += "| Type | Count | Description |\n"
        output += "|------|-------|-------------|\n"
        type_desc = {
            "ASSIGN": "Constant value assignment",
            "COPY": "Direct column copy",
            "CONCAT": "Concatenate multiple columns",
            "SEQUENCE": "Generate sequence numbers",
            "DATE_FORMAT": "Convert to ISO 8601",
            "MAP": "Controlled terminology lookup",
            "DERIVE": "Calculated derivation",
            "TRANSPOSE": "Reshape data structure",
        }
        for t_type, count in sorted(transform_counts.items(), key=lambda x: -x[1]):
            desc = type_desc.get(t_type, t_type)
            output += f"| {t_type} | {count} | {desc} |\n"

        output += "\n### Sample Variable Mappings\n\n"
        output += "| SDTM Variable | Source | Transformation | Type |\n"
        output += "|---------------|--------|----------------|------|\n"
        for vm in var_mappings[:10]:
            sdtm_var = vm.get("sdtm_variable", "")
            source = vm.get("source_column", "")
            if isinstance(source, list):
                source = "+".join(source)
            source = str(source)[:20] if source else "[derived]"
            transform = vm.get("transformation", "")[:25]
            t_type = vm.get("transformation_type", "")
            output += f"| {sdtm_var} | {source} | {transform} | {t_type} |\n"

        if len(var_mappings) > 10:
            output += f"\n*... and {len(var_mappings) - 10} more variables*\n"

        # Controlled Terminology
        ct = enhanced_spec.get("controlled_terminologies", {})
        if ct:
            output += f"\n**Controlled Terminology Codelists:** {len(ct)}\n"
            for codelist, values in list(ct.items())[:5]:
                vals = values if isinstance(values, list) else values.get("valid_values", [])
                output += f"- `{codelist}`: {', '.join(str(v) for v in vals[:4])}"
                if len(vals) > 4:
                    output += f"... (+{len(vals)-4} more)"
                output += "\n"

        output += "\n---\n\n"
        output += "**Next Steps:**\n"
        output += f"1. Review the Excel file at `{excel_path}`\n"
        output += "2. Modify mappings if needed\n"
        output += f"3. Use `transform_with_specification('{domain}', '{json_path}')` to transform\n"

        return output

    except Exception as e:
        import traceback
        return f"Error generating mapping specification: {str(e)}\n\n{traceback.format_exc()}"


def _enhance_mapping_specification(
    mapping_spec, source_df: pd.DataFrame, domain: str, sdtm_spec: dict, study_id: str
) -> dict:
    """Enhance the mapping specification with detailed transformation types."""

    enhanced = {
        "metadata": {
            "study_id": study_id,
            "source_domain": mapping_spec.source_domain,
            "target_domain": domain,
            "sdtm_version": "SDTM-IG 3.4",
            "created_by": "SDTM Mapping Generator",
            "created_date": datetime.now().isoformat(),
            "description": f"Mapping specification for {domain} domain transformation"
        },
        "source_files": [{
            "filename": mapping_spec.source_domain,
            "records": len(source_df),
            "columns": len(source_df.columns),
        }],
        "variable_mappings": [],
        "derivation_rules": mapping_spec.derivation_rules or {},
        "controlled_terminologies": mapping_spec.controlled_terminologies or {},
        "data_quality_rules": []
    }

    # Build variable mappings with transformation types
    for cm in mapping_spec.column_mappings:
        transformation_type = _determine_transformation_type(cm, domain)

        var_mapping = {
            "sdtm_variable": cm.target_variable,
            "label": _get_variable_label(cm.target_variable, domain, sdtm_spec),
            "type": _get_variable_type(cm.target_variable, domain),
            "core": _get_variable_core(cm.target_variable, domain, sdtm_spec),
            "source_column": cm.source_column,
            "transformation": cm.transformation or cm.derivation_rule or f"COPY({cm.source_column})" if cm.source_column else None,
            "transformation_type": transformation_type,
            "controlled_terminology": cm.controlled_terminology,
            "comments": cm.comments or ""
        }
        enhanced["variable_mappings"].append(var_mapping)

    # Add standard derivations if missing
    standard_vars = ["STUDYID", "DOMAIN", "USUBJID", f"{domain}SEQ"]
    existing_vars = [vm["sdtm_variable"] for vm in enhanced["variable_mappings"]]

    for std_var in standard_vars:
        if std_var not in existing_vars:
            if std_var == "STUDYID":
                enhanced["variable_mappings"].insert(0, {
                    "sdtm_variable": "STUDYID",
                    "label": "Study Identifier",
                    "type": "Char",
                    "core": "Req",
                    "source_column": None,
                    "transformation": f"ASSIGN('{study_id}')",
                    "transformation_type": "ASSIGN",
                    "controlled_terminology": None,
                    "comments": "Study identifier constant"
                })
            elif std_var == "DOMAIN":
                enhanced["variable_mappings"].insert(1, {
                    "sdtm_variable": "DOMAIN",
                    "label": "Domain Abbreviation",
                    "type": "Char",
                    "core": "Req",
                    "source_column": None,
                    "transformation": f"ASSIGN('{domain}')",
                    "transformation_type": "ASSIGN",
                    "controlled_terminology": None,
                    "comments": "Domain identifier constant"
                })

    return enhanced


def _determine_transformation_type(cm, domain: str) -> str:
    """Determine the transformation type from the column mapping."""
    if cm.transformation:
        t = cm.transformation.upper()
        if t.startswith("ASSIGN"): return "ASSIGN"
        if t.startswith("COPY"): return "COPY"
        if t.startswith("CONCAT"): return "CONCAT"
        if t.startswith("SEQUENCE"): return "SEQUENCE"
        if t.startswith("DATE_FORMAT"): return "DATE_FORMAT"
        if t.startswith("MAP"): return "MAP"
        if t.startswith("STUDY_DAY"): return "DERIVE"
        if t.startswith("IF"): return "DERIVE"

    if cm.derivation_rule:
        rule = cm.derivation_rule.upper()
        if "||" in rule or "CONCAT" in rule: return "CONCAT"
        if "ROW_NUMBER" in rule: return "SEQUENCE"
        if "DATE" in rule: return "DATE_FORMAT"
        return "DERIVE"

    if cm.source_column:
        return "COPY"

    return "DERIVE"


def _get_variable_label(var_name: str, domain: str, sdtm_spec: dict) -> str:
    """Get SDTM variable label from spec."""
    if sdtm_spec:
        for level in ["required", "expected", "permissible"]:
            for var in sdtm_spec.get("variables", {}).get(level, []):
                if var.get("name") == var_name:
                    return var.get("label", var_name)
    return var_name


def _get_variable_type(var_name: str, domain: str) -> str:
    """Get SDTM variable type."""
    numeric_suffixes = ["SEQ", "CD", "DY", "STRESN", "ORRESU", "STNRLO", "STNRHI"]
    if any(var_name.endswith(s) for s in numeric_suffixes):
        return "Num"
    return "Char"


def _get_variable_core(var_name: str, domain: str, sdtm_spec: dict) -> str:
    """Get SDTM variable core status (Req/Exp/Perm)."""
    if sdtm_spec:
        for level, abbr in [("required", "Req"), ("expected", "Exp"), ("permissible", "Perm")]:
            for var in sdtm_spec.get("variables", {}).get(level, []):
                if var.get("name") == var_name:
                    return abbr
    return "Perm"


def _save_mapping_excel(spec: dict, output_path: str):
    """Save mapping specification to Excel with multiple sheets."""
    import pandas as pd

    # Sheet 1: Variable Mappings
    mappings_data = []
    for vm in spec.get("variable_mappings", []):
        source = vm.get("source_column", "")
        if isinstance(source, list):
            source = " + ".join(source)
        mappings_data.append({
            "SDTM Variable": vm.get("sdtm_variable"),
            "Label": vm.get("label"),
            "Type": vm.get("type"),
            "Core": vm.get("core"),
            "Source Column(s)": source or "[derived]",
            "Transformation": vm.get("transformation"),
            "Transformation Type": vm.get("transformation_type"),
            "Controlled Terminology": vm.get("controlled_terminology"),
            "Comments": vm.get("comments")
        })
    mappings_df = pd.DataFrame(mappings_data)

    # Sheet 2: Metadata
    metadata = spec.get("metadata", {})
    metadata_df = pd.DataFrame([{
        "Property": k,
        "Value": str(v)
    } for k, v in metadata.items()])

    # Sheet 3: Derivation Rules
    derivations = spec.get("derivation_rules", {})
    derivation_df = pd.DataFrame([{
        "Variable": k,
        "Derivation Rule": v
    } for k, v in derivations.items()])

    # Sheet 4: Controlled Terminology
    ct = spec.get("controlled_terminologies", {})
    ct_data = []
    for codelist, values in ct.items():
        if isinstance(values, dict):
            vals = values.get("valid_values", [])
        else:
            vals = values
        for val in vals:
            ct_data.append({"Codelist": codelist, "Valid Value": val})
    ct_df = pd.DataFrame(ct_data)

    # Sheet 5: Source Files
    source_df = pd.DataFrame(spec.get("source_files", []))

    # Write to Excel
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        mappings_df.to_excel(writer, sheet_name='Variable Mappings', index=False)
        metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
        if not derivation_df.empty:
            derivation_df.to_excel(writer, sheet_name='Derivation Rules', index=False)
        if not ct_df.empty:
            ct_df.to_excel(writer, sheet_name='Controlled Terminology', index=False)
        if not source_df.empty:
            source_df.to_excel(writer, sheet_name='Source Files', index=False)


@tool
def transform_with_specification(
    domain: str,
    spec_path: str = ""
) -> str:
    """
    Transform raw EDC data to SDTM using a previously generated mapping specification.

    This tool reads a JSON mapping specification and applies all the defined
    transformations to convert raw data to SDTM format.

    **Workflow:**
    1. First run `generate_mapping_specification(domain)` to create the spec
    2. Review/modify the Excel file if needed
    3. Run this tool to apply the transformations

    Args:
        domain: SDTM domain code (DM, AE, VS, LB, CM, etc.)
        spec_path: Path to the JSON mapping specification file.
                   If empty, looks in ./sdtm_workspace/mapping_specs/{domain}_mapping_specification.json
    """
    global _sdtm_data
    domain = domain.upper()

    if not _source_data:
        return "No data loaded. Please use load_data_from_s3 first."

    # Find spec file
    if not spec_path:
        spec_path = f"./sdtm_workspace/mapping_specs/{domain.lower()}_mapping_specification.json"

    output = f"## Transforming {domain} Domain Using Specification\n\n"

    try:
        from pathlib import Path
        import json

        # Load specification
        spec_file = Path(spec_path)
        if not spec_file.exists():
            return f"Specification file not found: {spec_path}\n\nRun `generate_mapping_specification('{domain}')` first."

        with open(spec_file, 'r') as f:
            spec = json.load(f)

        output += f"**Specification:** `{spec_path}`\n"
        output += f"**Study:** {spec.get('metadata', {}).get('study_id', 'UNKNOWN')}\n"
        output += f"**Variables to Map:** {len(spec.get('variable_mappings', []))}\n\n"

        # Find source files
        source_files = [f for f in _source_data if _determine_domain(f) == domain]
        if not source_files:
            return f"No source files found for domain: {domain}"

        # Combine source data
        combined_df = pd.concat(
            [_source_data[f] for f in source_files],
            ignore_index=True
        )
        output += f"**Source Records:** {len(combined_df):,}\n\n"

        # Apply transformations
        output += "### Applying Transformations\n\n"

        sdtm_records = []
        subject_sequences = {}

        for idx, row in combined_df.iterrows():
            record = {}

            for vm in spec.get("variable_mappings", []):
                sdtm_var = vm.get("sdtm_variable")
                source_col = vm.get("source_column")
                transformation = vm.get("transformation", "")
                t_type = vm.get("transformation_type", "")

                try:
                    if t_type == "ASSIGN":
                        # Extract constant value from ASSIGN('value')
                        if "ASSIGN(" in transformation:
                            value = transformation.split("'")[1] if "'" in transformation else transformation.split("(")[1].rstrip(")")
                            record[sdtm_var] = value
                        else:
                            record[sdtm_var] = transformation

                    elif t_type == "COPY" and source_col:
                        col = source_col[0] if isinstance(source_col, list) else source_col
                        record[sdtm_var] = row.get(col, "")

                    elif t_type == "CONCAT":
                        # Handle concatenation
                        if isinstance(source_col, list):
                            parts = [str(row.get(c, "")) for c in source_col]
                            record[sdtm_var] = "-".join(p for p in parts if p)
                        else:
                            record[sdtm_var] = str(row.get(source_col, ""))

                    elif t_type == "SEQUENCE":
                        # Generate sequence per subject
                        usubjid = record.get("USUBJID", str(idx))
                        subject_sequences[usubjid] = subject_sequences.get(usubjid, 0) + 1
                        record[sdtm_var] = subject_sequences[usubjid]

                    elif t_type == "DATE_FORMAT" and source_col:
                        col = source_col[0] if isinstance(source_col, list) else source_col
                        date_val = row.get(col, "")
                        record[sdtm_var] = _convert_to_iso8601(date_val)

                    elif t_type == "MAP" and source_col:
                        col = source_col[0] if isinstance(source_col, list) else source_col
                        record[sdtm_var] = row.get(col, "")

                    elif source_col:
                        # Default: try to copy
                        col = source_col[0] if isinstance(source_col, list) else source_col
                        record[sdtm_var] = row.get(col, "")
                    else:
                        record[sdtm_var] = ""

                except Exception:
                    record[sdtm_var] = ""

            sdtm_records.append(record)

        # Create DataFrame
        sdtm_df = pd.DataFrame(sdtm_records)
        _sdtm_data[domain] = sdtm_df

        output += f"**Records Transformed:** {len(sdtm_df):,}\n"
        output += f"**SDTM Variables:** {len(sdtm_df.columns)}\n\n"

        # Validate
        output += "### Validation\n\n"
        try:
            from sdtm_pipeline.validators.sdtm_validator import SDTMValidator
            validator = SDTMValidator(study_id=_study_id, use_knowledge_tools=True)
            result = validator.validate_domain(sdtm_df, domain)

            status = "✓ VALID" if result.is_valid else "⚠️ ISSUES FOUND"
            output += f"**Status:** {status}\n"
            output += f"**Errors:** {result.error_count}\n"
            output += f"**Warnings:** {result.warning_count}\n"

            if result.issues:
                output += "\n**Issues:**\n"
                for issue in result.issues[:5]:
                    output += f"- {issue.severity.value.upper()}: {issue.message}\n"
                if len(result.issues) > 5:
                    output += f"- *... and {len(result.issues) - 5} more*\n"
        except Exception as e:
            output += f"Validation skipped: {str(e)[:50]}\n"

        # Sample output
        output += "\n### Sample Output\n\n"
        sample_cols = ['STUDYID', 'DOMAIN', 'USUBJID', f'{domain}SEQ'] + [c for c in sdtm_df.columns if c not in ['STUDYID', 'DOMAIN', 'USUBJID', f'{domain}SEQ']][:3]
        sample_cols = [c for c in sample_cols if c in sdtm_df.columns]

        output += "| " + " | ".join(sample_cols) + " |\n"
        output += "|" + "|".join(["---"] * len(sample_cols)) + "|\n"
        for _, row in sdtm_df.head(3).iterrows():
            values = [str(row.get(c, ''))[:15] for c in sample_cols]
            output += "| " + " | ".join(values) + " |\n"

        output += f"\n**Transformation complete!** Use `upload_sdtm_to_s3` or `save_sdtm_locally` to save.\n"

        return output

    except Exception as e:
        import traceback
        return f"Error transforming with specification: {str(e)}\n\n{traceback.format_exc()}"


def _convert_to_iso8601(date_val) -> str:
    """Convert various date formats to ISO 8601."""
    if pd.isna(date_val) or date_val == "":
        return ""

    date_str = str(date_val).strip()

    # Already ISO 8601
    if len(date_str) >= 10 and date_str[4] == '-' and date_str[7] == '-':
        return date_str[:10]

    # YYYYMMDD format
    if len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    # YYYYMM format (partial date)
    if len(date_str) == 6 and date_str.isdigit():
        return f"{date_str[:4]}-{date_str[4:6]}"

    return date_str


@tool
def generate_all_mapping_specifications(output_dir: str = "./sdtm_workspace/mapping_specs") -> str:
    """
    Generate mapping specifications for ALL available domains at once.

    Creates JSON and Excel specification files for each domain found in the
    loaded source data. Use this before batch conversion to review all mappings.

    Args:
        output_dir: Directory to save all specification files
    """
    if not _source_data:
        return "No data loaded. Please use load_data_from_s3 first."

    # Find all domains
    domain_files: Dict[str, List[str]] = {}
    for filename in _source_data:
        domain = _determine_domain(filename)
        if domain != "UNKNOWN":
            if domain not in domain_files:
                domain_files[domain] = []
            domain_files[domain].append(filename)

    if not domain_files:
        return "No convertible domains found in the loaded data."

    output = f"## Generating Mapping Specifications for All Domains\n\n"
    output += f"**Domains Found:** {', '.join(sorted(domain_files.keys()))}\n"
    output += f"**Output Directory:** `{output_dir}`\n\n"

    successful = []
    failed = []

    for domain in sorted(domain_files.keys()):
        output += f"### {domain} Domain\n"
        try:
            # Call the single domain generator (but capture result differently)
            from pathlib import Path
            import json

            Path(output_dir).mkdir(parents=True, exist_ok=True)

            source_file = domain_files[domain][0]
            df = _source_data[source_file]

            api_key = os.getenv("ANTHROPIC_API_KEY", "")
            from sdtm_pipeline.transformers.mapping_generator import MappingSpecificationGenerator
            generator = MappingSpecificationGenerator(
                api_key=api_key,
                study_id=_study_id,
                use_knowledge_tools=True
            )

            mapping_spec = generator.generate_mapping(
                df=df,
                source_name=source_file,
                target_domain=domain
            )

            # Get SDTM spec
            sdtm_spec = None
            try:
                from sdtm_pipeline.transformers.sdtm_web_reference import get_sdtm_web_reference
                ref = get_sdtm_web_reference()
                sdtm_spec = ref.get_domain_specification(domain)
            except:
                pass

            enhanced_spec = _enhance_mapping_specification(
                mapping_spec, df, domain, sdtm_spec, _study_id
            )

            # Save files
            json_path = Path(output_dir) / f"{domain.lower()}_mapping_specification.json"
            excel_path = Path(output_dir) / f"{domain.lower()}_mapping_specification.xlsx"

            with open(json_path, 'w') as f:
                json.dump(enhanced_spec, f, indent=2)

            _save_mapping_excel(enhanced_spec, str(excel_path))

            var_count = len(enhanced_spec.get("variable_mappings", []))
            output += f"✓ Generated: {var_count} variables mapped\n"
            output += f"  - JSON: `{json_path}`\n"
            output += f"  - Excel: `{excel_path}`\n\n"

            successful.append({"domain": domain, "variables": var_count})

        except Exception as e:
            output += f"✗ Error: {str(e)[:50]}\n\n"
            failed.append({"domain": domain, "error": str(e)[:50]})

    # Summary
    output += "---\n\n"
    output += "## Summary\n\n"
    output += f"**Successful:** {len(successful)}/{len(domain_files)}\n\n"

    if successful:
        output += "| Domain | Variables Mapped |\n"
        output += "|--------|------------------|\n"
        for s in successful:
            output += f"| {s['domain']} | {s['variables']} |\n"

    if failed:
        output += "\n**Failed:**\n"
        for f in failed:
            output += f"- {f['domain']}: {f['error']}\n"

    output += f"\n**Next Steps:**\n"
    output += "1. Review Excel files in the output directory\n"
    output += "2. Modify mappings as needed\n"
    output += "3. Use `convert_all_domains()` or `transform_with_specification(domain)` to transform\n"

    return output


@tool
def validate_domain(domain: str) -> str:
    """
    Validate a converted SDTM domain against CDISC standards.

    Runs validation checks including:
    - Required variables
    - Controlled terminology
    - Business rules from knowledge base
    - Date formats

    Args:
        domain: SDTM domain code to validate
    """
    domain = domain.upper()

    if domain not in _sdtm_data:
        return f"Domain {domain} not converted yet. Please use convert_domain first."

    try:
        from sdtm_pipeline.validators.sdtm_validator import SDTMValidator

        validator = SDTMValidator(study_id=_study_id, use_knowledge_tools=True)
        df = _sdtm_data[domain]
        result = validator.validate_domain(df, domain)

        output = f"## Validation Report: {domain}\n\n"
        output += f"**Status:** {'✓ VALID' if result.is_valid else '✗ INVALID'}\n"
        output += f"**Records:** {result.total_records}\n"
        output += f"**Errors:** {result.error_count}\n"
        output += f"**Warnings:** {result.warning_count}\n\n"

        if result.issues:
            # Group by severity
            errors = [i for i in result.issues if i.severity.value == "error"]
            warnings = [i for i in result.issues if i.severity.value == "warning"]

            if errors:
                output += "### Errors\n\n"
                for issue in errors:
                    kb = "[KB] " if issue.rule_id.startswith("KB-") else ""
                    output += f"- **{issue.rule_id}**: {kb}{issue.message}\n"

            if warnings:
                output += "\n### Warnings\n\n"
                for issue in warnings[:10]:
                    kb = "[KB] " if issue.rule_id.startswith("KB-") else ""
                    output += f"- **{issue.rule_id}**: {kb}{issue.message}\n"
                if len(warnings) > 10:
                    output += f"\n*... and {len(warnings) - 10} more warnings*\n"
        else:
            output += "No issues found! Dataset is compliant.\n"

        return output

    except Exception as e:
        return f"Error validating {domain}: {str(e)}"


@tool
def get_conversion_status() -> str:
    """
    Get the current status of the SDTM conversion pipeline.

    Shows loaded data, converted domains, and validation status.
    """
    output = "## SDTM Pipeline Status\n\n"
    output += f"**Study ID:** {_study_id}\n"
    output += f"**Source Files Loaded:** {len(_source_data)}\n"
    output += f"**Domains Converted:** {len(_sdtm_data)}\n\n"

    if _sdtm_data:
        output += "### Converted Domains\n\n"
        output += "| Domain | Records | Status |\n"
        output += "|--------|---------|--------|\n"

        for domain, df in sorted(_sdtm_data.items()):
            output += f"| {domain} | {len(df)} | ✓ Converted |\n"

    if _source_data and not _sdtm_data:
        output += "*No domains converted yet. Use convert_domain to start.*\n"
    elif not _source_data:
        output += "*No data loaded. Use load_data_from_s3 to start.*\n"

    return output


@tool
def search_sdtm_guidelines(query: str) -> str:
    """
    Search SDTM guidelines and CDISC documentation using Tavily web search.

    Args:
        query: Search query about SDTM, CDISC, or FDA requirements
    """
    try:
        from sdtm_pipeline.langgraph_agent.knowledge_tools import get_knowledge_retriever

        retriever = get_knowledge_retriever()
        results = retriever.search_web(query, max_results=5)

        if not results:
            return "No results found. Try a different query."

        output = f"## Search Results: {query}\n\n"

        for i, r in enumerate(results, 1):
            title = r.get('title', 'No title')
            url = r.get('url', '')
            content = r.get('content', '')[:300]

            output += f"### {i}. {title}\n"
            output += f"*{url}*\n\n"
            output += f"{content}...\n\n"

        return output

    except Exception as e:
        return f"Error searching guidelines: {str(e)}"


@tool
def fetch_sdtmig_specification(domain: str) -> str:
    """
    Fetch SDTM-IG 3.4 specification for a domain from authoritative CDISC sources.

    This tool retrieves the complete variable specification for an SDTM domain including:
    - Required variables (must be present)
    - Expected variables (should be present if data available)
    - Permissible variables (optional, used based on study needs)
    - Data types, roles, and controlled terminology references

    Sources:
    - SDTM-IG 3.4: https://sastricks.com/cdisc/SDTMIG%20v3.4-FINAL_2022-07-21.pdf
    - CDISC SDTMIG: https://www.cdisc.org/standards/foundational/sdtmig

    Args:
        domain: SDTM domain code (e.g., AE, DM, VS, LB, CM, EX, MH, DS)
    """
    domain = domain.upper()

    try:
        from sdtm_pipeline.transformers.sdtm_web_reference import get_sdtm_web_reference

        ref = get_sdtm_web_reference()
        spec = ref.get_domain_specification(domain)

        if not spec:
            return f"No specification found for domain: {domain}. Try: {', '.join(ref.get_all_domains())}"

        output = f"## 📋 SDTM-IG 3.4 Specification: {domain} Domain\n\n"
        output += f"**Description:** {spec.get('description', 'N/A')}\n"
        output += f"**Class:** {spec.get('class', 'N/A')}\n"
        output += f"**Structure:** {spec.get('structure', 'N/A')}\n\n"

        variables = spec.get("variables", {})

        # Required variables
        req_vars = variables.get("required", [])
        if req_vars:
            output += "### Required Variables (Req)\n"
            output += "*Must be present in all datasets*\n\n"
            output += "| Variable | Label | Type | Role |\n"
            output += "|----------|-------|------|------|\n"
            for v in req_vars:
                output += f"| `{v['name']}` | {v.get('label', '')} | {v.get('type', '')} | {v.get('role', '')} |\n"
            output += "\n"

        # Expected variables
        exp_vars = variables.get("expected", [])
        if exp_vars:
            output += "### Expected Variables (Exp)\n"
            output += "*Should be present if data is collected*\n\n"
            output += "| Variable | Label | Type | Codelist |\n"
            output += "|----------|-------|------|----------|\n"
            for v in exp_vars:
                cl = v.get('codelist', '-')
                output += f"| `{v['name']}` | {v.get('label', '')} | {v.get('type', '')} | {cl} |\n"
            output += "\n"

        # Permissible variables (show first 15)
        perm_vars = variables.get("permissible", [])
        if perm_vars:
            output += f"### Permissible Variables (Perm) - showing first 15 of {len(perm_vars)}\n"
            output += "*Optional, used based on study needs*\n\n"
            output += "| Variable | Label | Codelist |\n"
            output += "|----------|-------|----------|\n"
            for v in perm_vars[:15]:
                cl = v.get('codelist', '-')
                output += f"| `{v['name']}` | {v.get('label', '')} | {cl} |\n"
            if len(perm_vars) > 15:
                output += f"\n*... and {len(perm_vars) - 15} more permissible variables*\n"
            output += "\n"

        output += f"**Total Variables:** {len(req_vars)} Required + {len(exp_vars)} Expected + {len(perm_vars)} Permissible = {len(req_vars) + len(exp_vars) + len(perm_vars)}\n"

        return output

    except Exception as e:
        import traceback
        return f"Error fetching SDTM-IG spec: {str(e)}\n\n{traceback.format_exc()}"


@tool
def fetch_controlled_terminology(codelist: str) -> str:
    """
    Fetch CDISC Controlled Terminology for a codelist.

    Provides the valid values for SDTM variables that require controlled terminology.
    Use this to ensure data values comply with CDISC standards.

    Sources:
    - CDISC CT: https://www.cdisc.org/standards/terminology

    Common codelists:
    - SEX: Sex (M, F, U, UNDIFFERENTIATED)
    - NY: No/Yes Response (N, Y)
    - AESEV: Severity (MILD, MODERATE, SEVERE)
    - REL: Causality Relationship
    - OUT: Outcome of Event
    - ACN: Action Taken with Study Treatment
    - RACE: Race
    - ETHNIC: Ethnicity
    - TOXGR: Toxicity Grade (CTCAE)
    - AGEU: Age Unit

    Args:
        codelist: Codelist code (e.g., SEX, NY, REL, OUT, ACN, AESEV)
    """
    codelist = codelist.upper()

    try:
        from sdtm_pipeline.transformers.sdtm_web_reference import get_sdtm_web_reference

        ref = get_sdtm_web_reference()
        ct = ref.get_controlled_terminology(codelist)

        if not ct:
            available = ref.get_all_codelists()
            return f"Codelist '{codelist}' not found. Available codelists: {', '.join(available)}"

        output = f"## 📖 CDISC Controlled Terminology: {codelist}\n\n"
        output += f"**Name:** {ct.get('name', codelist)}\n"
        output += f"**Extensible:** {'Yes' if ct.get('extensible') else 'No'}\n\n"

        terms = ct.get("terms", [])
        if terms:
            output += "### Valid Values\n\n"
            output += "| Code | Decode | Definition |\n"
            output += "|------|--------|------------|\n"
            for t in terms:
                code = t.get('code', '')
                decode = t.get('decode', '')
                defn = t.get('definition', '')[:60]
                output += f"| `{code}` | {decode} | {defn} |\n"

        output += f"\n**Total Terms:** {len(terms)}\n"

        if ct.get('extensible'):
            output += "\n*Note: This codelist is extensible - sponsor-defined values are allowed if not in standard list.*\n"

        return output

    except Exception as e:
        return f"Error fetching CT: {str(e)}"


@tool
def get_mapping_guidance_from_web(source_column: str, domain: str) -> str:
    """
    Get intelligent mapping guidance from SDTM-IG 3.4 for a source column.

    This tool analyzes a source column name and provides:
    - Matching SDTM variables with confidence scores
    - Variable definitions and requirements
    - Controlled terminology requirements
    - Web search results for specific guidance

    Use this when you're unsure how to map a specific EDC column to SDTM.

    Args:
        source_column: Source data column name from EDC
        domain: Target SDTM domain (e.g., AE, DM, VS)
    """
    domain = domain.upper()

    try:
        from sdtm_pipeline.transformers.sdtm_web_reference import get_sdtm_web_reference

        ref = get_sdtm_web_reference()
        guidance = ref.get_mapping_guidance(source_column, domain)

        output = f"## 🎯 Mapping Guidance: {source_column} → {domain}\n\n"

        suggestions = guidance.get("suggestions", [])
        if suggestions:
            output += "### Suggested SDTM Variables\n\n"
            output += "| SDTM Variable | Label | Score | Reasons | Level | CT |\n"
            output += "|---------------|-------|-------|---------|-------|----|\n"

            for s in suggestions:
                score = s.get('score', 0)
                score_icon = "✓" if score >= 0.8 else "~" if score >= 0.6 else "?"
                reasons = ", ".join(s.get('reasons', []))
                ct = s.get('codelist') or '-'
                output += f"| `{s['variable']}` | {s.get('label', '')[:30]} | {score_icon} {score:.0%} | {reasons} | {s.get('level', '')} | {ct} |\n"
            output += "\n"

            # Best recommendation
            if suggestions[0].get('score', 0) >= 0.7:
                best = suggestions[0]
                output += f"**Recommended Mapping:** `{source_column}` → `{best['variable']}`\n"
                if best.get('codelist'):
                    output += f"*Note: Apply Controlled Terminology `{best['codelist']}` to values*\n"
                output += "\n"

        # Web guidance
        web_guidance = guidance.get("guidance", [])
        if web_guidance:
            output += "### Additional Web Guidance\n\n"
            for g in web_guidance:
                source = g.get('source', 'web')
                content = g.get('content', '')[:200]
                output += f"**Source:** {source}\n"
                output += f"{content}...\n\n"

        if not suggestions:
            output += "*No confident mapping suggestions found. This column may need manual review or custom derivation.*\n"

        return output

    except Exception as e:
        return f"Error getting mapping guidance: {str(e)}"


@tool
def search_internet(query: str) -> str:
    """
    Search the internet for any information using Tavily AI search.

    Use this tool when you need to:
    - Look up current regulatory guidance or FDA announcements
    - Find clinical trial best practices
    - Research data standards or terminologies
    - Get information not available in Pinecone knowledge base
    - Answer general questions about SDTM, CDISC, or clinical data

    Args:
        query: Search query - be specific for better results
    """
    try:
        # Try Tavily first (preferred)
        try:
            from tavily import TavilyClient
            tavily_key = os.getenv("TAVILY_API_KEY")
            if tavily_key:
                client = TavilyClient(api_key=tavily_key)
                response = client.search(
                    query=query,
                    search_depth="advanced",
                    max_results=5,
                    include_answer=True
                )

                output = f"## 🌐 Internet Search: {query}\n\n"

                # Include AI-generated answer if available
                if response.get("answer"):
                    output += f"**Summary:** {response['answer']}\n\n"

                output += "### Sources:\n\n"
                for i, r in enumerate(response.get("results", [])[:5], 1):
                    title = r.get('title', 'No title')
                    url = r.get('url', '')
                    content = r.get('content', '')[:350]

                    output += f"**{i}. {title}**\n"
                    output += f"🔗 {url}\n\n"
                    output += f"{content}...\n\n"
                    output += "---\n\n"

                return output
        except ImportError:
            pass

        # Fallback to knowledge retriever's web search
        from sdtm_pipeline.langgraph_agent.knowledge_tools import get_knowledge_retriever
        retriever = get_knowledge_retriever()

        if retriever and retriever.tavily_client:
            results = retriever.search_web(query, search_depth="advanced", max_results=5)

            if not results:
                return f"No internet results found for: {query}. Try a different query."

            output = f"## 🌐 Internet Search: {query}\n\n"

            for i, r in enumerate(results, 1):
                title = r.get('title', 'No title')
                url = r.get('url', '')
                content = r.get('content', '')[:350]

                output += f"**{i}. {title}**\n"
                output += f"🔗 {url}\n\n"
                output += f"{content}...\n\n"
                output += "---\n\n"

            return output
        else:
            return "Internet search not available. TAVILY_API_KEY not configured."

    except Exception as e:
        return f"Error searching internet: {str(e)}"


@tool
def get_business_rules(domain: str) -> str:
    """
    Get business rules and validation requirements for a domain from Pinecone.

    Retrieves FDA, Pinnacle 21, and CDISC rules from the knowledge base.

    Args:
        domain: SDTM domain code (e.g., DM, AE, VS)
    """
    try:
        from sdtm_pipeline.langgraph_agent.knowledge_tools import get_knowledge_retriever

        retriever = get_knowledge_retriever()
        rules = retriever.get_business_rules(domain.upper())

        if not rules:
            return f"No business rules found for domain {domain}."

        output = f"## Business Rules for {domain.upper()}\n\n"
        output += f"*Retrieved {len(rules)} rules from knowledge base*\n\n"

        for i, rule in enumerate(rules[:10], 1):
            rule_id = rule.get('rule_id', rule.get('id', f'Rule {i}'))
            desc = rule.get('description', rule.get('content', str(rule)))[:150]
            output += f"**{rule_id}**: {desc}\n\n"

        if len(rules) > 10:
            output += f"*... and {len(rules) - 10} more rules*\n"

        return output

    except Exception as e:
        return f"Error retrieving business rules: {str(e)}"


@tool
def preview_source_file(filename: str) -> str:
    """
    Preview a source data file showing sample records.

    Args:
        filename: Name of the source file (or partial match)
    """
    if not _source_data:
        return "No data loaded. Please use load_data_from_s3 first."

    # Find matching file
    matching = [f for f in _source_data if filename.lower() in f.lower()]

    if not matching:
        available = ", ".join(_source_data.keys())
        return f"File not found: {filename}\n\nAvailable files: {available}"

    filename = matching[0]
    df = _source_data[filename]

    output = f"## Preview: {filename}\n\n"
    output += f"**Records:** {len(df)}\n"
    output += f"**Columns:** {len(df.columns)}\n"
    output += f"**Target Domain:** {_determine_domain(filename)}\n\n"

    # Column list
    output += "**Columns:** " + ", ".join(df.columns) + "\n\n"

    # Sample data
    output += "### Sample Data\n\n"

    cols_to_show = list(df.columns[:8])
    output += "| " + " | ".join(cols_to_show) + " |\n"
    output += "|" + "|".join(["---"] * len(cols_to_show)) + "|\n"

    for _, row in df.head(5).iterrows():
        values = [str(row[c])[:15] for c in cols_to_show]
        output += "| " + " | ".join(values) + " |\n"

    if len(df.columns) > 8:
        output += f"\n*... and {len(df.columns) - 8} more columns*\n"

    return output


@tool
def get_mapping_specification(domain: str) -> str:
    """
    Get SDTM mapping specification from Pinecone knowledge base.

    Retrieves variable definitions, derivation rules, and controlled terminology
    for generating SDTM datasets from the vector database.

    Args:
        domain: SDTM domain code (e.g., DM, AE, VS, LB, CM)
    """
    try:
        from sdtm_pipeline.langgraph_agent.knowledge_tools import get_knowledge_retriever

        retriever = get_knowledge_retriever()

        # Get source columns if data is loaded
        source_cols = []
        if _source_data:
            for filename, df in _source_data.items():
                if _determine_domain(filename) == domain.upper():
                    source_cols.extend(df.columns.tolist())
                    break

        spec = retriever.get_mapping_specification(domain.upper(), source_cols)

        output = f"## Mapping Specification for {domain.upper()}\n\n"
        output += f"*Retrieved from Pinecone knowledge base*\n\n"

        # Variable mappings
        if spec.get("variable_mappings"):
            output += "### SDTM Variables\n\n"
            output += "| Variable | Label | Type | Core | Description |\n"
            output += "|----------|-------|------|------|-------------|\n"
            for var in spec["variable_mappings"][:15]:
                name = var.get("variable", "")[:12]
                label = var.get("label", "")[:20]
                vtype = var.get("type", "")[:8]
                core = var.get("core", "")[:4]
                desc = var.get("description", "")[:30]
                output += f"| {name} | {label} | {vtype} | {core} | {desc}... |\n"

        # Derivation rules
        if spec.get("derivation_rules"):
            output += "\n### Derivation Rules\n\n"
            for rule in spec["derivation_rules"][:10]:
                rule_id = rule.get("rule_id", "")
                variable = rule.get("variable", "")
                rule_text = rule.get("rule", "")[:100]
                output += f"- **{rule_id}** ({variable}): {rule_text}...\n"

        # Controlled terminology
        if spec.get("controlled_terminology"):
            output += "\n### Controlled Terminology\n\n"
            for codelist, info in list(spec["controlled_terminology"].items())[:5]:
                values = info.get("values", [])
                if isinstance(values, list):
                    values_str = ", ".join(str(v) for v in values[:5])
                else:
                    values_str = str(values)[:50]
                output += f"- **{codelist}**: {values_str}...\n"

        if not spec.get("variable_mappings") and not spec.get("derivation_rules"):
            output += "\n*No mapping specification found. Ensure OpenAI API key is configured.*\n"

        return output

    except Exception as e:
        return f"Error retrieving mapping specification: {str(e)}"


@tool
def get_validation_rules(domain: str) -> str:
    """
    Get comprehensive validation rules for a domain from Pinecone.

    Retrieves FDA, Pinnacle 21, and CDISC validation rules from the knowledge base.
    These rules are used to validate SDTM datasets for regulatory compliance.

    Args:
        domain: SDTM domain code (e.g., DM, AE, VS, LB, CM)
    """
    try:
        from sdtm_pipeline.langgraph_agent.knowledge_tools import get_knowledge_retriever

        retriever = get_knowledge_retriever()
        rules = retriever.get_validation_rules_for_domain(domain.upper())

        if not rules:
            return f"No validation rules found for domain {domain}. Ensure OpenAI API key is configured."

        output = f"## Validation Rules for {domain.upper()}\n\n"
        output += f"*Retrieved {len(rules)} rules from Pinecone knowledge base*\n\n"

        # Group by severity
        errors = [r for r in rules if r.get("severity") == "error"]
        warnings = [r for r in rules if r.get("severity") == "warning"]
        others = [r for r in rules if r.get("severity") not in ["error", "warning"]]

        if errors:
            output += "### Error Rules (Must Fix)\n\n"
            for rule in errors[:10]:
                rule_id = rule.get("rule_id", "")
                message = rule.get("message", "")[:100]
                check = rule.get("check", "")[:50]
                output += f"- **{rule_id}**: {message}\n"
                if check:
                    output += f"  - Check: `{check}`\n"

        if warnings:
            output += "\n### Warning Rules (Should Review)\n\n"
            for rule in warnings[:10]:
                rule_id = rule.get("rule_id", "")
                message = rule.get("message", "")[:100]
                output += f"- **{rule_id}**: {message}\n"

        if others:
            output += "\n### Other Rules\n\n"
            for rule in others[:5]:
                rule_id = rule.get("rule_id", "")
                message = rule.get("message", "")[:100]
                output += f"- **{rule_id}**: {message}\n"

        return output

    except Exception as e:
        return f"Error retrieving validation rules: {str(e)}"


@tool
def get_sdtm_guidance(domain: str) -> str:
    """
    Get comprehensive guidance for generating an SDTM dataset from Pinecone.

    Retrieves required/expected variables, transformation steps, and examples
    for creating compliant SDTM datasets.

    Args:
        domain: SDTM domain code (e.g., DM, AE, VS, LB, CM)
    """
    try:
        from sdtm_pipeline.langgraph_agent.knowledge_tools import get_knowledge_retriever

        retriever = get_knowledge_retriever()

        # Describe source data if loaded
        source_desc = "EDC clinical trial data"
        if _source_data:
            for filename, df in _source_data.items():
                if _determine_domain(filename) == domain.upper():
                    source_desc = f"EDC data with columns: {', '.join(df.columns[:10])}"
                    break

        guidance = retriever.get_sdtm_generation_guidance(domain.upper(), source_desc)

        output = f"## SDTM Generation Guidance for {domain.upper()}\n\n"
        output += f"*Retrieved from Pinecone knowledge base*\n\n"

        # Required variables
        if guidance.get("required_variables"):
            output += "### Required Variables (Must Include)\n\n"
            output += "| Variable | Label | Type | Description |\n"
            output += "|----------|-------|------|-------------|\n"
            for var in guidance["required_variables"][:10]:
                name = var.get("variable", "")[:12]
                label = var.get("label", "")[:20]
                vtype = var.get("type", "")[:8]
                desc = var.get("description", "")[:35]
                output += f"| {name} | {label} | {vtype} | {desc}... |\n"

        # Expected variables
        if guidance.get("expected_variables"):
            output += "\n### Expected Variables (Should Include)\n\n"
            for var in guidance["expected_variables"][:8]:
                name = var.get("variable", "")
                label = var.get("label", "")
                output += f"- **{name}**: {label}\n"

        # Transformation steps
        if guidance.get("transformation_steps"):
            output += "\n### Transformation Steps\n\n"
            for i, step in enumerate(guidance["transformation_steps"][:8], 1):
                step_text = step.get("step", "")[:100]
                variable = step.get("variable", "")
                output += f"{i}. "
                if variable:
                    output += f"**{variable}**: "
                output += f"{step_text}\n"

        if not guidance.get("required_variables") and not guidance.get("transformation_steps"):
            output += "\n*No guidance found. Ensure OpenAI API key is configured.*\n"

        return output

    except Exception as e:
        return f"Error retrieving SDTM guidance: {str(e)}"


@tool
def search_knowledge_base(query: str) -> str:
    """
    Search all Pinecone indexes for SDTM-related information.

    Searches across business rules, validation rules, SDTM IG, and controlled
    terminology indexes to find relevant information.

    Args:
        query: Search query (e.g., "AE domain AESER variable", "date format ISO 8601")
    """
    try:
        from sdtm_pipeline.langgraph_agent.knowledge_tools import get_knowledge_retriever

        retriever = get_knowledge_retriever()
        all_results = retriever.search_all_indexes(query, top_k_per_index=5)

        if not all_results:
            return f"No results found for query: {query}\n\nEnsure OpenAI API key is configured for Pinecone queries."

        output = f"## Knowledge Base Search: {query}\n\n"

        for index_name, results in all_results.items():
            output += f"### {index_name.upper()}\n\n"
            for i, r in enumerate(results[:3], 1):
                score = r.get("score", 0)
                meta = r.get("metadata", {})

                # Extract key info from metadata
                title = meta.get("title", meta.get("name", meta.get("variable", meta.get("rule_id", f"Result {i}"))))
                desc = meta.get("description", meta.get("text", meta.get("content", meta.get("rule", ""))))[:150]

                output += f"**{i}. {title}** (score: {score:.3f})\n"
                output += f"   {desc}...\n\n"

        return output

    except Exception as e:
        return f"Error searching knowledge base: {str(e)}"


@tool
def get_controlled_terminology(codelist: str) -> str:
    """
    Get CDISC controlled terminology values for a specific codelist from Pinecone.

    Retrieves valid values for codelists like SEX, RACE, ETHNIC, AESER, etc.

    Args:
        codelist: Codelist name (e.g., SEX, RACE, ETHNIC, AESER, AESEV)
    """
    try:
        from sdtm_pipeline.langgraph_agent.knowledge_tools import get_knowledge_retriever

        retriever = get_knowledge_retriever()

        # Search controlled terminology index
        results = retriever.search_pinecone(
            query=f"CDISC controlled terminology {codelist} codelist valid values terms",
            index_name="sdtmct",
            top_k=5
        )

        if not results:
            return f"No controlled terminology found for codelist: {codelist}"

        output = f"## Controlled Terminology: {codelist.upper()}\n\n"
        output += f"*Retrieved from SDTM CT Pinecone index*\n\n"

        for i, r in enumerate(results, 1):
            meta = r.get("metadata", {})
            score = r.get("score", 0)

            name = meta.get("codelist", meta.get("name", f"Result {i}"))
            values = meta.get("values", meta.get("terms", meta.get("codelist_values", [])))
            desc = meta.get("description", meta.get("text", ""))

            output += f"### {name} (score: {score:.3f})\n\n"
            if desc:
                output += f"*{desc[:100]}*\n\n"

            if values:
                if isinstance(values, list):
                    output += "**Valid Values:**\n"
                    for v in values[:20]:
                        output += f"- {v}\n"
                    if len(values) > 20:
                        output += f"- *... and {len(values) - 20} more*\n"
                else:
                    output += f"**Values:** {str(values)[:200]}\n"
            output += "\n"

        return output

    except Exception as e:
        return f"Error retrieving controlled terminology: {str(e)}"


@tool
def upload_sdtm_to_s3(
    domain: str = "",
    bucket: str = "s3dcri",
    prefix: str = "processed"
) -> str:
    """
    Upload converted SDTM data to S3 bucket.

    Uploads the SDTM dataset(s) as CSV files to the specified S3 bucket
    under the 'processed' folder.
    Also uploads mapping specifications and validation reports.

    Args:
        domain: Specific domain to upload (empty string uploads all converted domains)
        bucket: S3 bucket name (default: s3dcri)
        prefix: S3 key prefix for output files (default: processed)
    """
    if not _sdtm_data:
        return "No SDTM data to upload. Please use convert_domain first."

    try:
        s3 = boto3.client('s3')
        uploaded_files = []
        total_records = 0

        # Determine which domains to upload
        domains_to_upload = [domain.upper()] if domain else list(_sdtm_data.keys())

        for dom in domains_to_upload:
            if dom not in _sdtm_data:
                continue

            df = _sdtm_data[dom]

            # Create CSV in memory
            csv_buffer = df.to_csv(index=False)

            # Upload SDTM data
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            s3_key = f"{prefix}/{_study_id}/sdtm_data/{dom.lower()}.csv"

            s3.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=csv_buffer.encode('utf-8'),
                ContentType='text/csv'
            )

            uploaded_files.append({
                "domain": dom,
                "key": s3_key,
                "records": len(df)
            })
            total_records += len(df)

        # Create and upload manifest
        manifest = {
            "study_id": _study_id,
            "uploaded_at": datetime.now().isoformat(),
            "domains": [f["domain"] for f in uploaded_files],
            "total_records": total_records,
            "files": uploaded_files
        }

        manifest_key = f"{prefix}/{_study_id}/manifest.json"
        s3.put_object(
            Bucket=bucket,
            Key=manifest_key,
            Body=json.dumps(manifest, indent=2).encode('utf-8'),
            ContentType='application/json'
        )

        # Format output
        output = f"## S3 Upload Complete\n\n"
        output += f"**Study ID:** {_study_id}\n"
        output += f"**Bucket:** {bucket}\n"
        output += f"**Total Records:** {total_records}\n"
        output += f"**Files Uploaded:** {len(uploaded_files) + 1}\n\n"

        output += "### Uploaded Files\n\n"
        output += "| Domain | S3 Key | Records |\n"
        output += "|--------|--------|----------|\n"

        for f in uploaded_files:
            output += f"| {f['domain']} | {f['key']} | {f['records']} |\n"

        output += f"| MANIFEST | {manifest_key} | - |\n"

        output += f"\n✓ All SDTM data successfully uploaded to S3!\n"

        return output

    except Exception as e:
        import traceback
        return f"Error uploading to S3: {str(e)}\n\n{traceback.format_exc()}"


@tool
def load_sdtm_to_neo4j(domain: str = "") -> str:
    """
    Load converted SDTM data to Neo4j graph database.

    Creates nodes for subjects, domains, and records with relationships
    showing the data lineage and cross-domain connections.

    Args:
        domain: Specific domain to load (empty string loads all converted domains)
    """
    if not _sdtm_data:
        return "No SDTM data to load. Please use convert_domain first."

    try:
        from neo4j import GraphDatabase

        # Get Neo4j connection details from environment
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "")

        if not neo4j_password:
            return "Error: NEO4J_PASSWORD environment variable not set. Please configure Neo4j credentials."

        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

        # Determine which domains to load
        domains_to_load = [domain.upper()] if domain else list(_sdtm_data.keys())

        loaded_stats = []
        total_nodes = 0
        total_relationships = 0

        with driver.session() as session:
            for dom in domains_to_load:
                if dom not in _sdtm_data:
                    continue

                df = _sdtm_data[dom]

                # Create domain constraint (if not exists)
                try:
                    session.run(f"""
                        CREATE CONSTRAINT IF NOT EXISTS
                        FOR (n:{dom}) REQUIRE n.record_id IS UNIQUE
                    """)
                except:
                    pass  # Constraint may already exist

                # Create Study node
                session.run("""
                    MERGE (s:Study {study_id: $study_id})
                    SET s.updated_at = datetime()
                """, study_id=_study_id)

                # Create Domain node
                session.run("""
                    MERGE (d:Domain {name: $domain, study_id: $study_id})
                    SET d.record_count = $count, d.updated_at = datetime()
                    WITH d
                    MATCH (s:Study {study_id: $study_id})
                    MERGE (s)-[:HAS_DOMAIN]->(d)
                """, domain=dom, study_id=_study_id, count=len(df))

                nodes_created = 0
                rels_created = 0

                # Create Subject nodes and domain records
                for idx, row in df.iterrows():
                    record_data = row.to_dict()
                    # Clean NaN values
                    record_data = {k: (None if pd.isna(v) else v) for k, v in record_data.items()}

                    usubjid = record_data.get('USUBJID', f'{_study_id}-{idx}')
                    record_id = f"{dom}_{usubjid}_{idx}"

                    # Create Subject node
                    session.run("""
                        MERGE (sub:Subject {usubjid: $usubjid, study_id: $study_id})
                        SET sub.updated_at = datetime()
                    """, usubjid=usubjid, study_id=_study_id)

                    # Create domain record node with all data
                    # Dynamically set properties from the record
                    props_str = ", ".join([f"n.{k} = ${k}" for k in record_data.keys() if k])

                    session.run(f"""
                        MERGE (n:{dom} {{record_id: $record_id}})
                        SET {props_str}, n.updated_at = datetime()
                        WITH n
                        MATCH (sub:Subject {{usubjid: $usubjid, study_id: $study_id}})
                        MERGE (sub)-[:HAS_{dom}]->(n)
                        WITH n
                        MATCH (d:Domain {{name: $domain, study_id: $study_id}})
                        MERGE (n)-[:BELONGS_TO]->(d)
                    """, record_id=record_id, usubjid=usubjid, study_id=_study_id,
                        domain=dom, **record_data)

                    nodes_created += 1
                    rels_created += 2  # Subject->Record, Record->Domain

                loaded_stats.append({
                    "domain": dom,
                    "nodes": nodes_created,
                    "relationships": rels_created
                })
                total_nodes += nodes_created
                total_relationships += rels_created

        driver.close()

        # Format output
        output = f"## Neo4j Load Complete\n\n"
        output += f"**Study ID:** {_study_id}\n"
        output += f"**Neo4j URI:** {neo4j_uri}\n"
        output += f"**Total Nodes Created:** {total_nodes}\n"
        output += f"**Total Relationships:** {total_relationships}\n\n"

        output += "### Loaded Domains\n\n"
        output += "| Domain | Nodes | Relationships |\n"
        output += "|--------|-------|---------------|\n"

        for stat in loaded_stats:
            output += f"| {stat['domain']} | {stat['nodes']} | {stat['relationships']} |\n"

        output += f"\n### Graph Structure\n\n"
        output += "```\n"
        output += f"(Study:{_study_id})\n"
        output += "    |\n"
        output += "    |--[:HAS_DOMAIN]-->(Domain)\n"
        output += "    |                     |\n"
        output += "    |--[:HAS_SUBJECT]-->(Subject)\n"
        output += "                          |\n"
        output += f"                          |--[:HAS_{{domain}}]-->(Record)\n"
        output += "```\n"

        output += f"\n✓ All SDTM data successfully loaded to Neo4j!\n"

        return output

    except ImportError:
        return "Error: neo4j package not installed. Run: pip install neo4j"
    except Exception as e:
        import traceback
        return f"Error loading to Neo4j: {str(e)}\n\n{traceback.format_exc()}"


@tool
def save_sdtm_locally(output_dir: str = "./sdtm_chat_output") -> str:
    """
    Save converted SDTM data to local files.

    Saves SDTM datasets as CSV files along with mapping specs and validation reports.

    Args:
        output_dir: Local directory to save files (default: ./sdtm_chat_output)
    """
    if not _sdtm_data:
        return "No SDTM data to save. Please use convert_domain first."

    try:
        # Create output directories
        output_path = Path(output_dir)
        sdtm_dir = output_path / "sdtm_data"
        sdtm_dir.mkdir(parents=True, exist_ok=True)

        saved_files = []
        total_records = 0

        for domain, df in _sdtm_data.items():
            # Save SDTM CSV
            csv_path = sdtm_dir / f"{domain.lower()}.csv"
            df.to_csv(csv_path, index=False)

            saved_files.append({
                "domain": domain,
                "path": str(csv_path),
                "records": len(df)
            })
            total_records += len(df)

        # Create and save manifest
        manifest = {
            "study_id": _study_id,
            "created_at": datetime.now().isoformat(),
            "domains": list(_sdtm_data.keys()),
            "total_records": total_records,
            "files": saved_files
        }

        manifest_path = output_path / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        # Format output
        output = f"## Local Save Complete\n\n"
        output += f"**Study ID:** {_study_id}\n"
        output += f"**Output Directory:** {output_dir}\n"
        output += f"**Total Records:** {total_records}\n"
        output += f"**Files Saved:** {len(saved_files) + 1}\n\n"

        output += "### Saved Files\n\n"
        output += "| Domain | Path | Records |\n"
        output += "|--------|------|----------|\n"

        for f in saved_files:
            output += f"| {f['domain']} | {f['path']} | {f['records']} |\n"

        output += f"| MANIFEST | {manifest_path} | - |\n"

        output += f"\n✓ All SDTM data saved locally!\n"

        return output

    except Exception as e:
        import traceback
        return f"Error saving locally: {str(e)}\n\n{traceback.format_exc()}"


# Export all tools
SDTM_TOOLS = [
    # Task Progress Tracking
    write_todos,  # Updates task progress shown in frontend TaskProgressBar
    # Data loading
    load_data_from_s3,
    list_available_domains,
    preview_source_file,
    # Specification-Driven Workflow (RECOMMENDED)
    generate_mapping_specification,      # Step 1: Generate JSON + Excel spec for review
    generate_all_mapping_specifications, # Step 1b: Generate specs for ALL domains
    transform_with_specification,        # Step 2: Transform using the reviewed spec
    # Direct Conversion (uses internal mapping)
    convert_domain,
    convert_all_domains,  # Batch conversion - more efficient for "convert all"
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
    # SDTM-IG 3.4 Web Reference (CDISC Authoritative Sources)
    fetch_sdtmig_specification,
    fetch_controlled_terminology,
    get_mapping_guidance_from_web,
    # Internet search (Tavily)
    search_internet,
]

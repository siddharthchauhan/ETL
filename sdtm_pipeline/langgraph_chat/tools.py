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
    1. Generates mapping specification using Claude AI
    2. Transforms data according to mapping
    3. Validates the SDTM dataset
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

        # Step 1: Generate mapping
        output += "### Step 1: Mapping Specification\n\n"

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return "Error: ANTHROPIC_API_KEY not set"

        generator = MappingSpecificationGenerator(
            api_key=api_key,
            study_id=_study_id,
            use_knowledge_tools=True
        )

        # Get first source file
        source_file = source_files[0]
        df = _source_data[source_file]

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

        # Step 2: Transform
        output += "\n### Step 2: Transformation\n\n"

        combined_df = pd.concat(
            [_source_data[f] for f in source_files],
            ignore_index=True
        )

        transformer = get_transformer(
            domain_code=domain,
            study_id=_study_id,
            mapping_spec=spec
        )

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


# Export all tools
SDTM_TOOLS = [
    load_data_from_s3,
    list_available_domains,
    convert_domain,
    validate_domain,
    get_conversion_status,
    search_sdtm_guidelines,
    get_business_rules,
    preview_source_file,
]

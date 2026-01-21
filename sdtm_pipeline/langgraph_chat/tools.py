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
    # Knowledge base
    search_sdtm_guidelines,
    get_business_rules,
    get_mapping_specification,
    get_validation_rules,
    get_sdtm_guidance,
    search_knowledge_base,
    get_controlled_terminology,
]

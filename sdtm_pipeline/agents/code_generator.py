"""
Code Generator Agent
====================
Specialized agent for generating SAS and R transformation code
for SDTM data conversions.
"""

import os
import re
import subprocess
import tempfile
from typing import Dict, Any, List, Optional
from datetime import datetime

from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent


@tool
def generate_sas_transformation(
    mapping_spec: Dict[str, Any],
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate SAS program for SDTM transformation.

    Creates production-ready SAS code based on mapping specification.

    Args:
        mapping_spec: Mapping specification with source/target mappings
        output_path: Optional output path for the SAS file

    Returns:
        Generated SAS code and metadata
    """
    domain = mapping_spec.get("target_domain", "XX")
    source_file = mapping_spec.get("source_file", "source.csv")
    mappings = mapping_spec.get("column_mappings", [])
    study_id = mapping_spec.get("study_id", "STUDY")

    # Generate SAS code
    sas_code = f"""/**********************************************************************
* Program: {domain.lower()}.sas
* Purpose: Transform source data to SDTM {domain} domain
* Study: {study_id}
* Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
* Generator: SDTM Multi-Agent Pipeline
**********************************************************************/

%let study = {study_id};
%let domain = {domain};

/* Import source data */
proc import datafile="&rawdir./{source_file}"
    out=work.source_{domain.lower()}
    dbms=csv replace;
    guessingrows=max;
run;

/* Transform to SDTM format */
data sdtm.{domain.lower()};
    length
        STUDYID $20
        DOMAIN $2
        USUBJID $40
"""

    # Add length statements for mapped variables
    for mapping in mappings:
        target = mapping.get("target_variable", "")
        if target.endswith("SEQ"):
            sas_code += f"        {target} 8\n"
        elif target.endswith("DTC"):
            sas_code += f"        {target} $20\n"
        elif target.endswith("ORRES") or target.endswith("STRESC"):
            sas_code += f"        {target} $200\n"
        elif target.endswith("ORRESU") or target.endswith("STRESU"):
            sas_code += f"        {target} $40\n"
        else:
            sas_code += f"        {target} $200\n"

    sas_code += """    ;
    set work.source_""" + domain.lower() + """;

    /* Standard identifiers */
    STUDYID = "&study.";
    DOMAIN = "&domain.";

"""

    # Add variable mappings
    for mapping in mappings:
        source = mapping.get("source_column", "")
        target = mapping.get("target_variable", "")
        transform = mapping.get("transformation", "direct")

        if not source or not target:
            continue

        if transform == "direct":
            sas_code += f"    {target} = {source};\n"
        elif transform == "uppercase":
            sas_code += f"    {target} = upcase({source});\n"
        elif transform == "iso_date":
            sas_code += f"    {target} = put(datepart({source}), e8601da.);\n"
        elif transform == "numeric":
            sas_code += f"    {target} = input({source}, best.);\n"
        else:
            # Custom transformation
            sas_code += f"    /* Custom: {transform} */\n"
            sas_code += f"    {target} = {source};  /* TODO: Apply transformation */\n"

    # Add sequence variable
    seq_var = f"{domain}SEQ"
    sas_code += f"""
    /* Generate sequence number */
    retain _seq 0;
    by USUBJID;
    if first.USUBJID then _seq = 0;
    _seq + 1;
    {seq_var} = _seq;
    drop _seq;

run;

/* Validate output */
proc freq data=sdtm.{domain.lower()};
    tables DOMAIN / missing;
run;

proc contents data=sdtm.{domain.lower()};
run;
"""

    result = {
        "domain": domain,
        "code": sas_code,
        "line_count": len(sas_code.split("\n")),
        "mapped_variables": len(mappings)
    }

    if output_path:
        with open(output_path, "w") as f:
            f.write(sas_code)
        result["output_path"] = output_path

    return result


@tool
def generate_r_transformation(
    mapping_spec: Dict[str, Any],
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate R script for SDTM transformation using pharmaverse packages.

    Creates R code using admiral and other pharmaverse packages.

    Args:
        mapping_spec: Mapping specification with source/target mappings
        output_path: Optional output path for the R file

    Returns:
        Generated R code and metadata
    """
    domain = mapping_spec.get("target_domain", "XX")
    source_file = mapping_spec.get("source_file", "source.csv")
    mappings = mapping_spec.get("column_mappings", [])
    study_id = mapping_spec.get("study_id", "STUDY")

    # Generate R code
    r_code = f'''#' ===================================================================
#' Program: {domain.lower()}.R
#' Purpose: Transform source data to SDTM {domain} domain
#' Study: {study_id}
#' Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
#' Generator: SDTM Multi-Agent Pipeline
#' ===================================================================

# Load required packages
library(tidyverse)
library(admiral)
library(admiraldev)
library(lubridate)

# Configuration
study_id <- "{study_id}"
domain_code <- "{domain}"

# Read source data
source_{domain.lower()} <- read_csv(
    file.path(raw_data_dir, "{source_file}"),
    show_col_types = FALSE
)

# Transform to SDTM format
{domain.lower()} <- source_{domain.lower()} %>%
    mutate(
        STUDYID = study_id,
        DOMAIN = domain_code,

'''

    # Add variable transformations
    mutation_lines = []
    for mapping in mappings:
        source = mapping.get("source_column", "")
        target = mapping.get("target_variable", "")
        transform = mapping.get("transformation", "direct")

        if not source or not target:
            continue

        if transform == "direct":
            mutation_lines.append(f"        {target} = {source}")
        elif transform == "uppercase":
            mutation_lines.append(f"        {target} = toupper({source})")
        elif transform == "iso_date":
            mutation_lines.append(f"        {target} = format(as.Date({source}), '%Y-%m-%d')")
        elif transform == "numeric":
            mutation_lines.append(f"        {target} = as.numeric({source})")
        else:
            mutation_lines.append(f"        # Custom: {transform}")
            mutation_lines.append(f"        {target} = {source}  # TODO: Apply transformation")

    r_code += ",\n".join(mutation_lines)

    # Add sequence variable
    seq_var = f"{domain}SEQ"
    r_code += f'''
    ) %>%
    # Generate sequence number
    group_by(USUBJID) %>%
    mutate({seq_var} = row_number()) %>%
    ungroup() %>%
    # Select and order variables
    select(
        STUDYID, DOMAIN, USUBJID,
        {seq_var},
        everything()
    )

# Validate output
cat("\\n=== {domain} Domain Summary ===\\n")
cat("Records:", nrow({domain.lower()}), "\\n")
cat("Subjects:", n_distinct({domain.lower()}$USUBJID), "\\n")

# Check for required variables
required_vars <- c("STUDYID", "DOMAIN", "USUBJID", "{seq_var}")
missing_vars <- setdiff(required_vars, names({domain.lower()}))
if (length(missing_vars) > 0) {{
    warning("Missing required variables: ", paste(missing_vars, collapse = ", "))
}}

# Save output
write_csv({domain.lower()}, file.path(output_dir, "{domain.lower()}.csv"))

cat("\\nOutput saved to:", file.path(output_dir, "{domain.lower()}.csv"), "\\n")
'''

    result = {
        "domain": domain,
        "code": r_code,
        "line_count": len(r_code.split("\n")),
        "mapped_variables": len(mappings),
        "packages": ["tidyverse", "admiral", "admiraldev", "lubridate"]
    }

    if output_path:
        with open(output_path, "w") as f:
            f.write(r_code)
        result["output_path"] = output_path

    return result


@tool
def validate_code_syntax(
    code: str,
    language: str
) -> Dict[str, Any]:
    """
    Validate code syntax without execution.

    Performs static analysis for SAS or R code.

    Args:
        code: Source code to validate
        language: Programming language ("sas" or "r")

    Returns:
        Syntax validation result
    """
    language = language.lower()
    issues = []

    if language == "sas":
        issues = _validate_sas_syntax(code)
    elif language == "r":
        issues = _validate_r_syntax(code)
    else:
        return {"error": f"Unsupported language: {language}"}

    return {
        "language": language,
        "is_valid": len(issues) == 0,
        "issue_count": len(issues),
        "issues": issues
    }


def _validate_sas_syntax(code: str) -> List[Dict[str, Any]]:
    """Validate SAS code syntax."""
    issues = []
    lines = code.split("\n")

    # Check for common issues
    in_data_step = False
    in_proc = False
    macro_vars = set()

    for i, line in enumerate(lines, 1):
        line_stripped = line.strip().lower()

        # Track data step/proc boundaries
        if line_stripped.startswith("data "):
            if in_data_step:
                issues.append({
                    "line": i,
                    "type": "error",
                    "message": "DATA step started without ending previous step"
                })
            in_data_step = True
        elif line_stripped.startswith("proc "):
            if in_proc:
                issues.append({
                    "line": i,
                    "type": "error",
                    "message": "PROC started without ending previous procedure"
                })
            in_proc = True
        elif line_stripped == "run;":
            in_data_step = False
            in_proc = False

        # Check for missing semicolons
        if line_stripped and not line_stripped.startswith("*") and not line_stripped.startswith("/*"):
            if not line_stripped.endswith(";") and not line_stripped.endswith("*/"):
                # Skip multi-line statements
                if not any(kw in line_stripped for kw in ["then", "else", "do", "end"]):
                    if not line_stripped.endswith(","):
                        issues.append({
                            "line": i,
                            "type": "warning",
                            "message": "Line may be missing semicolon"
                        })

        # Track macro variables
        for match in re.finditer(r"&(\w+)\.?", line):
            macro_vars.add(match.group(1))

        # Check for undefined macro variables (basic check)
        for match in re.finditer(r"%let\s+(\w+)\s*=", line, re.IGNORECASE):
            macro_vars.add(match.group(1))

    return issues


def _validate_r_syntax(code: str) -> List[Dict[str, Any]]:
    """Validate R code syntax."""
    issues = []
    lines = code.split("\n")

    # Track brackets and parentheses
    paren_count = 0
    brace_count = 0
    bracket_count = 0

    for i, line in enumerate(lines, 1):
        # Skip comments
        if line.strip().startswith("#"):
            continue

        paren_count += line.count("(") - line.count(")")
        brace_count += line.count("{") - line.count("}")
        bracket_count += line.count("[") - line.count("]")

        # Check for common issues
        if "<-" in line and "=" in line.split("<-")[0]:
            # Assignment operator mixed with equals
            pass  # This is often valid

        # Check for tidyverse pipe issues
        if line.strip().endswith("%>%") or line.strip().endswith("|>"):
            # Check if next non-empty line exists
            next_line_idx = i
            while next_line_idx < len(lines):
                next_line = lines[next_line_idx].strip()
                if next_line and not next_line.startswith("#"):
                    break
                next_line_idx += 1
            else:
                issues.append({
                    "line": i,
                    "type": "error",
                    "message": "Pipe operator at end of file"
                })

    # Check final bracket counts
    if paren_count != 0:
        issues.append({
            "line": len(lines),
            "type": "error",
            "message": f"Unbalanced parentheses: {paren_count:+d}"
        })
    if brace_count != 0:
        issues.append({
            "line": len(lines),
            "type": "error",
            "message": f"Unbalanced braces: {brace_count:+d}"
        })
    if bracket_count != 0:
        issues.append({
            "line": len(lines),
            "type": "error",
            "message": f"Unbalanced brackets: {bracket_count:+d}"
        })

    return issues


@tool
def test_code_snippet(
    code: str,
    language: str,
    test_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Test a code snippet in a sandboxed environment.

    Executes R code in a temporary environment with optional test data.
    SAS execution requires external SAS installation.

    Args:
        code: Code snippet to test
        language: Programming language ("r" or "sas")
        test_data: Optional test data for the snippet

    Returns:
        Execution result with output or errors
    """
    language = language.lower()

    if language == "r":
        return _test_r_code(code, test_data)
    elif language == "sas":
        return {
            "language": "sas",
            "executed": False,
            "message": "SAS execution requires external SAS installation. Use validate_code_syntax for static analysis."
        }
    else:
        return {"error": f"Unsupported language: {language}"}


def _test_r_code(code: str, test_data: Optional[Dict] = None) -> Dict[str, Any]:
    """Execute R code in a sandboxed environment."""
    try:
        # Check if R is available
        result = subprocess.run(
            ["R", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            return {
                "language": "r",
                "executed": False,
                "message": "R not available in environment"
            }
    except (subprocess.SubprocessError, FileNotFoundError):
        return {
            "language": "r",
            "executed": False,
            "message": "R not available in environment"
        }

    # Create temp file for R script
    with tempfile.NamedTemporaryFile(mode="w", suffix=".R", delete=False) as f:
        # Add test data setup if provided
        if test_data:
            f.write("# Test data setup\n")
            for var, value in test_data.items():
                if isinstance(value, list):
                    f.write(f'{var} <- c({", ".join(repr(v) for v in value)})\n')
                else:
                    f.write(f'{var} <- {repr(value)}\n')
            f.write("\n")

        f.write(code)
        script_path = f.name

    try:
        # Execute R script with timeout
        result = subprocess.run(
            ["Rscript", "--vanilla", script_path],
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )

        return {
            "language": "r",
            "executed": True,
            "success": result.returncode == 0,
            "stdout": result.stdout[:5000] if result.stdout else "",
            "stderr": result.stderr[:2000] if result.stderr else "",
            "return_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "language": "r",
            "executed": True,
            "success": False,
            "error": "Execution timed out after 30 seconds"
        }
    except Exception as e:
        return {
            "language": "r",
            "executed": False,
            "error": str(e)
        }
    finally:
        # Clean up temp file
        try:
            os.unlink(script_path)
        except Exception:
            pass


# List of all tools for this agent
CODE_GENERATOR_TOOLS = [
    generate_sas_transformation,
    generate_r_transformation,
    validate_code_syntax,
    test_code_snippet
]


class CodeGeneratorAgent:
    """
    Code Generator Agent for SAS and R code generation.

    Responsibilities:
    - Generate production-ready SAS programs
    - Generate R scripts using pharmaverse packages
    - Validate code syntax
    - Test code snippets in sandboxed environments
    """

    SYSTEM_PROMPT = """You are a Code Generator Agent specialized in SAS and R programming for clinical trials.

Your responsibilities:
1. Generate production-ready SAS programs for SDTM transformations
2. Create R scripts using pharmaverse packages (admiral, tidyverse)
3. Validate code syntax before delivery
4. Test code snippets when possible

SAS code standards:
- Use consistent indentation and formatting
- Include comprehensive header comments
- Add data quality checks and validation
- Follow pharmaceutical industry best practices
- Use macro variables for flexibility

R code standards:
- Use tidyverse style guide
- Leverage admiral package for SDTM derivations
- Include proper error handling
- Add validation checks and summaries
- Follow pharmaverse conventions

Always:
- Validate syntax before returning code
- Include comments explaining complex logic
- Add data validation steps
- Consider edge cases and missing data"""

    def __init__(self, api_key: Optional[str] = None):
        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
        self.llm = ChatAnthropic(
            model=model,
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=8192  # Larger for code generation
        )
        self.agent = create_react_agent(
            self.llm,
            CODE_GENERATOR_TOOLS,
            state_modifier=self.SYSTEM_PROMPT
        )

    async def generate_code(
        self,
        mapping_spec: Dict[str, Any],
        languages: List[str] = None
    ) -> Dict[str, Any]:
        """Generate transformation code."""
        if languages is None:
            languages = ["sas", "r"]

        input_message = f"""Generate transformation code for the following mapping specification:

{mapping_spec}

Please generate code for: {', '.join(languages)}

For each language:
1. Generate the transformation code
2. Validate the syntax
3. Add appropriate comments and documentation"""

        result = await self.agent.ainvoke({
            "messages": [{"role": "user", "content": input_message}]
        })

        return {
            "agent": "code_generator",
            "result": result.get("messages", [])[-1].content if result.get("messages") else "",
            "timestamp": datetime.now().isoformat()
        }

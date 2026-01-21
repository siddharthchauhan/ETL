"""
Source Data Analyst Agent
=========================
Specialized agent for source data schema analysis, profiling,
and data quality assessment.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from dataclasses import dataclass

from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent


@dataclass
class ColumnProfile:
    """Profile information for a single column."""
    name: str
    dtype: str
    null_count: int
    null_pct: float
    unique_count: int
    unique_pct: float
    min_value: Optional[Any]
    max_value: Optional[Any]
    mean_value: Optional[float]
    sample_values: List[Any]


@dataclass
class DataQualityIssue:
    """A data quality issue found in source data."""
    column: str
    issue_type: str
    severity: str  # 'error', 'warning', 'info'
    message: str
    affected_rows: int


@tool
def analyze_source_schema(
    file_path: str
) -> Dict[str, Any]:
    """
    Analyze the schema of a source data file.

    Extracts column names, data types, and basic statistics.

    Args:
        file_path: Path to the source CSV file

    Returns:
        Schema analysis with column details
    """
    try:
        df = pd.read_csv(file_path, nrows=1000)  # Sample first 1000 rows
    except Exception as e:
        return {"error": str(e)}

    columns = []
    for col in df.columns:
        col_info = {
            "name": col,
            "dtype": str(df[col].dtype),
            "nullable": bool(df[col].isna().any()),
            "sample_values": df[col].dropna().head(5).tolist(),
        }

        # Infer semantic type
        col_lower = col.lower()
        if any(x in col_lower for x in ["date", "dt", "dtc"]):
            col_info["semantic_type"] = "date"
        elif any(x in col_lower for x in ["id", "num", "no"]):
            col_info["semantic_type"] = "identifier"
        elif any(x in col_lower for x in ["name", "term", "txt"]):
            col_info["semantic_type"] = "text"
        elif df[col].dtype in ["float64", "int64"]:
            col_info["semantic_type"] = "numeric"
        else:
            col_info["semantic_type"] = "categorical"

        columns.append(col_info)

    return {
        "file": os.path.basename(file_path),
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": columns,
        "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024 / 1024
    }


@tool
def detect_data_relationships(
    file_paths: List[str]
) -> Dict[str, Any]:
    """
    Detect relationships between multiple source data files.

    Identifies common columns that could be used as join keys.

    Args:
        file_paths: List of paths to source CSV files

    Returns:
        Detected relationships between files
    """
    # Load column info from each file
    file_columns: Dict[str, set] = {}
    for path in file_paths:
        try:
            df = pd.read_csv(path, nrows=1)
            file_columns[os.path.basename(path)] = set(df.columns)
        except Exception:
            continue

    # Find common columns
    relationships = []
    files = list(file_columns.keys())

    for i, file1 in enumerate(files):
        for file2 in files[i+1:]:
            common = file_columns[file1] & file_columns[file2]
            if common:
                # Check for key columns
                key_cols = [c for c in common if any(
                    k in c.lower() for k in ["id", "subj", "visit", "seq"]
                )]
                relationships.append({
                    "file1": file1,
                    "file2": file2,
                    "common_columns": list(common),
                    "likely_keys": key_cols
                })

    return {
        "file_count": len(files),
        "relationships": relationships,
        "suggested_subject_key": _find_subject_key(file_columns)
    }


def _find_subject_key(file_columns: Dict[str, set]) -> Optional[str]:
    """Find the most likely subject identifier column."""
    all_columns = set()
    for cols in file_columns.values():
        all_columns.update(cols)

    # Check for common subject ID patterns
    for pattern in ["USUBJID", "SUBJID", "SUBJECT", "SUBJECTID", "PATIENTID"]:
        matches = [c for c in all_columns if pattern.lower() in c.lower()]
        if matches:
            return matches[0]

    return None


@tool
def profile_source_data(
    file_path: str,
    sample_size: int = 10000
) -> Dict[str, Any]:
    """
    Generate detailed profiling statistics for source data.

    Includes distribution analysis, outlier detection, and pattern recognition.

    Args:
        file_path: Path to the source CSV file
        sample_size: Maximum rows to analyze

    Returns:
        Detailed profiling report
    """
    try:
        df = pd.read_csv(file_path, nrows=sample_size)
    except Exception as e:
        return {"error": str(e)}

    profiles = []
    for col in df.columns:
        profile = {
            "column": col,
            "dtype": str(df[col].dtype),
            "null_count": int(df[col].isna().sum()),
            "null_pct": round(df[col].isna().mean() * 100, 2),
            "unique_count": int(df[col].nunique()),
            "unique_pct": round(df[col].nunique() / len(df) * 100, 2) if len(df) > 0 else 0,
        }

        # Numeric statistics
        if df[col].dtype in ["float64", "int64"]:
            profile.update({
                "min": float(df[col].min()) if pd.notna(df[col].min()) else None,
                "max": float(df[col].max()) if pd.notna(df[col].max()) else None,
                "mean": round(float(df[col].mean()), 4) if pd.notna(df[col].mean()) else None,
                "std": round(float(df[col].std()), 4) if pd.notna(df[col].std()) else None,
                "median": float(df[col].median()) if pd.notna(df[col].median()) else None,
            })

            # Detect outliers using IQR
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            outliers = ((df[col] < Q1 - 1.5 * IQR) | (df[col] > Q3 + 1.5 * IQR)).sum()
            profile["outlier_count"] = int(outliers)

        # Categorical statistics
        else:
            value_counts = df[col].value_counts().head(10)
            profile["top_values"] = [
                {"value": str(v), "count": int(c)}
                for v, c in value_counts.items()
            ]

            # Check for patterns
            if df[col].dtype == "object":
                sample = df[col].dropna().astype(str).head(100)
                if len(sample) > 0:
                    # Date pattern check
                    date_pattern = sample.str.match(r"\d{4}[-/]\d{2}[-/]\d{2}")
                    if date_pattern.mean() > 0.8:
                        profile["likely_date"] = True

        profiles.append(profile)

    return {
        "file": os.path.basename(file_path),
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "memory_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
        "column_profiles": profiles
    }


@tool
def assess_data_quality(
    file_path: str
) -> Dict[str, Any]:
    """
    Assess data quality issues in source data.

    Identifies missing values, duplicates, format issues, and outliers.

    Args:
        file_path: Path to the source CSV file

    Returns:
        Data quality assessment report
    """
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        return {"error": str(e)}

    issues: List[Dict[str, Any]] = []
    quality_score = 100.0

    # Check for duplicate rows
    duplicates = df.duplicated().sum()
    if duplicates > 0:
        issues.append({
            "type": "duplicate_rows",
            "severity": "warning",
            "message": f"Found {duplicates} duplicate rows",
            "affected_rows": int(duplicates)
        })
        quality_score -= min(10, duplicates / len(df) * 100)

    # Check each column
    for col in df.columns:
        # Missing values
        null_count = df[col].isna().sum()
        null_pct = null_count / len(df) * 100

        if null_pct == 100:
            issues.append({
                "type": "empty_column",
                "severity": "error",
                "column": col,
                "message": f"Column '{col}' is completely empty",
                "affected_rows": int(null_count)
            })
            quality_score -= 5
        elif null_pct > 50:
            issues.append({
                "type": "high_missing",
                "severity": "warning",
                "column": col,
                "message": f"Column '{col}' has {null_pct:.1f}% missing values",
                "affected_rows": int(null_count)
            })
            quality_score -= 2
        elif null_pct > 10:
            issues.append({
                "type": "moderate_missing",
                "severity": "info",
                "column": col,
                "message": f"Column '{col}' has {null_pct:.1f}% missing values",
                "affected_rows": int(null_count)
            })
            quality_score -= 1

        # Check for inconsistent date formats
        if "date" in col.lower() or col.endswith("DTC"):
            non_null = df[col].dropna().astype(str)
            if len(non_null) > 0:
                # Check if all follow ISO 8601
                iso_pattern = non_null.str.match(r"^\d{4}(-\d{2}(-\d{2}(T\d{2}(:\d{2}(:\d{2})?)?)?)?)?$")
                non_iso = (~iso_pattern).sum()
                if non_iso > 0:
                    issues.append({
                        "type": "date_format",
                        "severity": "warning",
                        "column": col,
                        "message": f"Column '{col}' has {non_iso} non-ISO 8601 dates",
                        "affected_rows": int(non_iso)
                    })
                    quality_score -= 2

        # Check for whitespace issues
        if df[col].dtype == "object":
            with_space = df[col].astype(str).str.contains(r"^\s|\s$", na=False).sum()
            if with_space > 0:
                issues.append({
                    "type": "whitespace",
                    "severity": "info",
                    "column": col,
                    "message": f"Column '{col}' has {with_space} values with leading/trailing spaces",
                    "affected_rows": int(with_space)
                })

    # Calculate summary
    error_count = sum(1 for i in issues if i["severity"] == "error")
    warning_count = sum(1 for i in issues if i["severity"] == "warning")
    info_count = sum(1 for i in issues if i["severity"] == "info")

    return {
        "file": os.path.basename(file_path),
        "total_rows": len(df),
        "quality_score": max(0, round(quality_score, 1)),
        "summary": {
            "errors": error_count,
            "warnings": warning_count,
            "info": info_count
        },
        "issues": issues,
        "recommendation": _get_quality_recommendation(quality_score)
    }


def _get_quality_recommendation(score: float) -> str:
    """Get recommendation based on quality score."""
    if score >= 95:
        return "Data quality is excellent. Ready for SDTM transformation."
    elif score >= 85:
        return "Data quality is good. Minor issues should be reviewed."
    elif score >= 70:
        return "Data quality needs attention. Address warnings before transformation."
    else:
        return "Data quality is poor. Significant issues must be resolved."


# List of all tools for this agent
SOURCE_ANALYST_TOOLS = [
    analyze_source_schema,
    detect_data_relationships,
    profile_source_data,
    assess_data_quality
]


class SourceDataAnalystAgent:
    """
    Source Data Analyst Agent for schema analysis and data profiling.

    Responsibilities:
    - Analyze source data schema and structure
    - Detect relationships between source files
    - Profile data distributions and patterns
    - Assess data quality issues
    """

    SYSTEM_PROMPT = """You are a Source Data Analyst Agent specialized in clinical trial data analysis.

Your responsibilities:
1. Analyze source data schemas to understand structure and content
2. Detect relationships between multiple source datasets
3. Profile data to understand distributions, patterns, and anomalies
4. Assess data quality and identify issues that need resolution

When analyzing source data:
- Identify potential SDTM domain targets based on column names
- Look for subject identifiers (SUBJID, USUBJID patterns)
- Check for date columns that need ISO 8601 conversion
- Flag data quality issues that could impact SDTM transformation

Always provide clear, actionable recommendations based on your analysis."""

    def __init__(self, api_key: Optional[str] = None):
        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
        self.llm = ChatAnthropic(
            model=model,
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=4096
        )
        self.agent = create_react_agent(
            self.llm,
            SOURCE_ANALYST_TOOLS,
            state_modifier=self.SYSTEM_PROMPT
        )

    async def analyze(self, file_paths: List[str]) -> Dict[str, Any]:
        """Analyze source data files."""
        input_message = f"""Analyze the following source data files for SDTM transformation:
{chr(10).join(file_paths)}

Please:
1. Analyze the schema of each file
2. Detect relationships between files
3. Profile the data quality
4. Provide recommendations for SDTM domain mapping"""

        result = await self.agent.ainvoke({
            "messages": [{"role": "user", "content": input_message}]
        })

        return {
            "agent": "source_data_analyst",
            "result": result.get("messages", [])[-1].content if result.get("messages") else "",
            "timestamp": datetime.now().isoformat()
        }

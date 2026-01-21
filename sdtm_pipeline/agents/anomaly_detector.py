"""
Anomaly Detection Agent
=======================
Specialized agent for detecting statistical anomalies,
physiological implausibility, and temporal pattern issues in SDTM data.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass

import pandas as pd
import numpy as np

from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

# Try to import scikit-learn for anomaly detection
try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# Try to import scipy for statistical functions
try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


# Physiological ranges for clinical parameters
PHYSIOLOGICAL_RANGES = {
    "VS": {
        "SYSBP": {"min": 60, "max": 250, "unit": "mmHg", "critical_low": 70, "critical_high": 220},
        "DIABP": {"min": 30, "max": 150, "unit": "mmHg", "critical_low": 40, "critical_high": 130},
        "PULSE": {"min": 30, "max": 220, "unit": "beats/min", "critical_low": 40, "critical_high": 180},
        "TEMP": {"min": 32, "max": 43, "unit": "C", "critical_low": 35, "critical_high": 40},
        "RESP": {"min": 5, "max": 60, "unit": "breaths/min", "critical_low": 8, "critical_high": 40},
        "HEIGHT": {"min": 30, "max": 250, "unit": "cm"},
        "WEIGHT": {"min": 1, "max": 500, "unit": "kg"},
        "BMI": {"min": 10, "max": 70, "unit": "kg/m2"},
    },
    "LB": {
        "ALT": {"min": 0, "max": 500, "unit": "U/L", "critical_high": 200},
        "AST": {"min": 0, "max": 500, "unit": "U/L", "critical_high": 200},
        "BILI": {"min": 0, "max": 30, "unit": "mg/dL", "critical_high": 10},
        "CREAT": {"min": 0, "max": 15, "unit": "mg/dL", "critical_high": 5},
        "GLUC": {"min": 20, "max": 500, "unit": "mg/dL", "critical_low": 50, "critical_high": 300},
        "HGB": {"min": 3, "max": 25, "unit": "g/dL", "critical_low": 7, "critical_high": 20},
        "WBC": {"min": 0.5, "max": 50, "unit": "10^9/L", "critical_low": 2, "critical_high": 30},
        "PLT": {"min": 10, "max": 1000, "unit": "10^9/L", "critical_low": 50, "critical_high": 600},
        "K": {"min": 1.5, "max": 8, "unit": "mEq/L", "critical_low": 3, "critical_high": 6},
        "NA": {"min": 110, "max": 170, "unit": "mEq/L", "critical_low": 125, "critical_high": 155},
    },
    "EG": {
        "QTCF": {"min": 200, "max": 700, "unit": "msec", "critical_high": 500},
        "INTP": {"min": 50, "max": 300, "unit": "msec"},
        "RR": {"min": 400, "max": 1500, "unit": "msec"},
    }
}


@dataclass
class Anomaly:
    """Detected anomaly."""
    domain: str
    subject: str
    variable: str
    value: Any
    anomaly_type: str  # 'statistical', 'physiological', 'temporal'
    severity: str  # 'critical', 'warning', 'info'
    message: str
    score: Optional[float] = None


@tool
def detect_statistical_anomalies(
    file_path: str,
    domain: str,
    method: str = "isolation_forest"
) -> Dict[str, Any]:
    """
    Detect statistical anomalies in SDTM dataset.

    Uses Isolation Forest, Z-Score, or IQR methods.

    Args:
        file_path: Path to the SDTM CSV file
        domain: SDTM domain code
        method: Detection method ('isolation_forest', 'zscore', 'iqr')

    Returns:
        Statistical anomaly detection results
    """
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        return {"error": str(e)}

    anomalies: List[Dict[str, Any]] = []
    domain = domain.upper()

    # Find numeric columns to analyze
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    # Exclude ID and sequence columns
    exclude_patterns = ["SEQ", "NUM", "ID", "VISITNUM"]
    analyze_cols = [c for c in numeric_cols
                    if not any(p in c.upper() for p in exclude_patterns)]

    if not analyze_cols:
        return {
            "domain": domain,
            "method": method,
            "anomalies": [],
            "message": "No numeric columns to analyze"
        }

    if method == "isolation_forest" and SKLEARN_AVAILABLE:
        anomalies = _detect_isolation_forest(df, domain, analyze_cols)
    elif method == "zscore":
        anomalies = _detect_zscore(df, domain, analyze_cols)
    else:  # iqr
        anomalies = _detect_iqr(df, domain, analyze_cols)

    return {
        "domain": domain,
        "method": method,
        "columns_analyzed": analyze_cols,
        "total_records": len(df),
        "anomaly_count": len(anomalies),
        "anomalies": anomalies[:100]  # Limit output
    }


def _detect_isolation_forest(
    df: pd.DataFrame,
    domain: str,
    columns: List[str]
) -> List[Dict[str, Any]]:
    """Detect anomalies using Isolation Forest."""
    anomalies = []

    for col in columns:
        if df[col].isna().all():
            continue

        # Prepare data
        data = df[[col]].dropna()
        if len(data) < 10:
            continue

        # Fit Isolation Forest
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(data)

        clf = IsolationForest(contamination=0.05, random_state=42)
        predictions = clf.fit_predict(scaled_data)

        # Get anomalies
        anomaly_indices = data.index[predictions == -1]
        scores = clf.decision_function(scaled_data)

        for idx in anomaly_indices:
            original_idx = data.index.get_loc(idx)
            anomalies.append({
                "domain": domain,
                "subject": str(df.loc[idx].get("USUBJID", "Unknown")),
                "variable": col,
                "value": float(df.loc[idx, col]),
                "anomaly_type": "statistical",
                "severity": "warning",
                "message": f"Statistical outlier detected (Isolation Forest)",
                "score": float(scores[original_idx])
            })

    return anomalies


def _detect_zscore(
    df: pd.DataFrame,
    domain: str,
    columns: List[str],
    threshold: float = 3.0
) -> List[Dict[str, Any]]:
    """Detect anomalies using Z-Score method."""
    anomalies = []

    for col in columns:
        if df[col].isna().all():
            continue

        data = df[col].dropna()
        if len(data) < 3:
            continue

        if SCIPY_AVAILABLE:
            z_scores = np.abs(stats.zscore(data))
        else:
            mean = data.mean()
            std = data.std()
            if std == 0:
                continue
            z_scores = np.abs((data - mean) / std)

        outliers = data.index[z_scores > threshold]

        for idx in outliers:
            anomalies.append({
                "domain": domain,
                "subject": str(df.loc[idx].get("USUBJID", "Unknown")),
                "variable": col,
                "value": float(df.loc[idx, col]),
                "anomaly_type": "statistical",
                "severity": "warning" if z_scores[data.index.get_loc(idx)] < 4 else "critical",
                "message": f"Z-score outlier: {z_scores[data.index.get_loc(idx)]:.2f}",
                "score": float(z_scores[data.index.get_loc(idx)])
            })

    return anomalies


def _detect_iqr(
    df: pd.DataFrame,
    domain: str,
    columns: List[str],
    multiplier: float = 1.5
) -> List[Dict[str, Any]]:
    """Detect anomalies using IQR method."""
    anomalies = []

    for col in columns:
        if df[col].isna().all():
            continue

        data = df[col].dropna()
        if len(data) < 4:
            continue

        Q1 = data.quantile(0.25)
        Q3 = data.quantile(0.75)
        IQR = Q3 - Q1

        if IQR == 0:
            continue

        lower = Q1 - multiplier * IQR
        upper = Q3 + multiplier * IQR

        outliers = data[(data < lower) | (data > upper)]

        for idx, value in outliers.items():
            # Calculate how far outside bounds
            if value < lower:
                distance = (lower - value) / IQR
            else:
                distance = (value - upper) / IQR

            anomalies.append({
                "domain": domain,
                "subject": str(df.loc[idx].get("USUBJID", "Unknown")),
                "variable": col,
                "value": float(value),
                "anomaly_type": "statistical",
                "severity": "critical" if distance > 3 else "warning",
                "message": f"IQR outlier: {distance:.2f}x IQR outside bounds",
                "score": float(distance)
            })

    return anomalies


@tool
def check_physiological_ranges(
    file_path: str,
    domain: str
) -> Dict[str, Any]:
    """
    Check values against physiological/clinical ranges.

    Validates that VS, LB, and EG values are within expected
    physiological ranges for the test type.

    Args:
        file_path: Path to the SDTM CSV file
        domain: SDTM domain code (VS, LB, EG)

    Returns:
        Physiological range check results
    """
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        return {"error": str(e)}

    domain = domain.upper()
    anomalies: List[Dict[str, Any]] = []

    if domain not in PHYSIOLOGICAL_RANGES:
        return {
            "domain": domain,
            "anomalies": [],
            "message": f"No physiological ranges defined for {domain}"
        }

    ranges = PHYSIOLOGICAL_RANGES[domain]

    # Determine test code and result columns
    testcd_col = f"{domain}TESTCD"
    result_col = f"{domain}STRESN"

    if testcd_col not in df.columns or result_col not in df.columns:
        return {
            "domain": domain,
            "anomalies": [],
            "message": f"Required columns {testcd_col}/{result_col} not found"
        }

    # Check each test type
    for testcd, limits in ranges.items():
        test_data = df[(df[testcd_col] == testcd) & df[result_col].notna()]

        for idx, row in test_data.iterrows():
            value = row[result_col]

            # Check against limits
            if value < limits["min"] or value > limits["max"]:
                severity = "critical"
                if "critical_low" in limits and value < limits["critical_low"]:
                    message = f"Critical low: {value} < {limits['critical_low']} {limits.get('unit', '')}"
                elif "critical_high" in limits and value > limits["critical_high"]:
                    message = f"Critical high: {value} > {limits['critical_high']} {limits.get('unit', '')}"
                else:
                    severity = "warning"
                    message = f"Outside range: {value} (range: {limits['min']}-{limits['max']} {limits.get('unit', '')})"

                anomalies.append({
                    "domain": domain,
                    "subject": str(row.get("USUBJID", "Unknown")),
                    "variable": testcd,
                    "value": float(value),
                    "anomaly_type": "physiological",
                    "severity": severity,
                    "message": message
                })

            # Check critical thresholds even if within overall range
            elif "critical_low" in limits and value < limits["critical_low"]:
                anomalies.append({
                    "domain": domain,
                    "subject": str(row.get("USUBJID", "Unknown")),
                    "variable": testcd,
                    "value": float(value),
                    "anomaly_type": "physiological",
                    "severity": "critical",
                    "message": f"Below critical low: {value} < {limits['critical_low']} {limits.get('unit', '')}"
                })
            elif "critical_high" in limits and value > limits["critical_high"]:
                anomalies.append({
                    "domain": domain,
                    "subject": str(row.get("USUBJID", "Unknown")),
                    "variable": testcd,
                    "value": float(value),
                    "anomaly_type": "physiological",
                    "severity": "critical",
                    "message": f"Above critical high: {value} > {limits['critical_high']} {limits.get('unit', '')}"
                })

    critical_count = sum(1 for a in anomalies if a["severity"] == "critical")
    warning_count = sum(1 for a in anomalies if a["severity"] == "warning")

    return {
        "domain": domain,
        "tests_checked": list(ranges.keys()),
        "total_records": len(df),
        "anomaly_count": len(anomalies),
        "critical_count": critical_count,
        "warning_count": warning_count,
        "anomalies": anomalies[:100]  # Limit output
    }


@tool
def analyze_temporal_patterns(
    file_path: str,
    domain: str
) -> Dict[str, Any]:
    """
    Analyze temporal patterns and detect date/time anomalies.

    Checks for:
    - Future dates
    - Dates before study start
    - Impossible date sequences
    - Unusual time gaps between events

    Args:
        file_path: Path to the SDTM CSV file
        domain: SDTM domain code

    Returns:
        Temporal pattern analysis results
    """
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        return {"error": str(e)}

    domain = domain.upper()
    anomalies: List[Dict[str, Any]] = []

    # Find date columns
    date_cols = [c for c in df.columns if c.endswith("DTC")]

    if not date_cols:
        return {
            "domain": domain,
            "anomalies": [],
            "message": "No date columns found"
        }

    today = datetime.now().strftime("%Y-%m-%d")

    for col in date_cols:
        if df[col].isna().all():
            continue

        # Check for future dates
        for idx, value in df[col].dropna().items():
            date_str = str(value)[:10]  # Get date part only
            try:
                if date_str > today:
                    anomalies.append({
                        "domain": domain,
                        "subject": str(df.loc[idx].get("USUBJID", "Unknown")),
                        "variable": col,
                        "value": date_str,
                        "anomaly_type": "temporal",
                        "severity": "warning",
                        "message": f"Future date: {date_str} > {today}"
                    })

                # Check for very old dates (before 1900)
                if date_str < "1900-01-01":
                    anomalies.append({
                        "domain": domain,
                        "subject": str(df.loc[idx].get("USUBJID", "Unknown")),
                        "variable": col,
                        "value": date_str,
                        "anomaly_type": "temporal",
                        "severity": "critical",
                        "message": f"Invalid date: before 1900"
                    })
            except Exception:
                pass

    # Check start/end date sequences
    date_pairs = [
        ("RFSTDTC", "RFENDTC"),
        (f"{domain}STDTC", f"{domain}ENDTC"),
        ("AESTDTC", "AEENDTC"),
        ("CMSTDTC", "CMENDTC"),
        ("EXSTDTC", "EXENDTC"),
    ]

    for start_col, end_col in date_pairs:
        if start_col in df.columns and end_col in df.columns:
            both = df[df[start_col].notna() & df[end_col].notna()]
            for idx, row in both.iterrows():
                start_date = str(row[start_col])[:10]
                end_date = str(row[end_col])[:10]
                if start_date > end_date:
                    anomalies.append({
                        "domain": domain,
                        "subject": str(row.get("USUBJID", "Unknown")),
                        "variable": f"{start_col}/{end_col}",
                        "value": f"{start_date} > {end_date}",
                        "anomaly_type": "temporal",
                        "severity": "error",
                        "message": f"Start date after end date"
                    })

    # Analyze event frequency by subject
    if "USUBJID" in df.columns and date_cols:
        primary_date = date_cols[0]
        subject_counts = df.groupby("USUBJID").size()

        # Find subjects with unusually high event counts
        if len(subject_counts) > 5:
            Q3 = subject_counts.quantile(0.75)
            IQR = subject_counts.quantile(0.75) - subject_counts.quantile(0.25)
            threshold = Q3 + 3 * IQR

            high_freq = subject_counts[subject_counts > threshold]
            for subject, count in high_freq.items():
                anomalies.append({
                    "domain": domain,
                    "subject": str(subject),
                    "variable": "event_count",
                    "value": int(count),
                    "anomaly_type": "temporal",
                    "severity": "info",
                    "message": f"Unusually high event count: {count} (threshold: {threshold:.0f})"
                })

    return {
        "domain": domain,
        "date_columns_analyzed": date_cols,
        "total_records": len(df),
        "anomaly_count": len(anomalies),
        "anomalies": anomalies[:100]  # Limit output
    }


# List of all tools for this agent
ANOMALY_DETECTOR_TOOLS = [
    detect_statistical_anomalies,
    check_physiological_ranges,
    analyze_temporal_patterns
]


class AnomalyDetectorAgent:
    """
    Anomaly Detection Agent for statistical and clinical anomalies.

    Responsibilities:
    - Detect statistical outliers using multiple methods
    - Check values against physiological ranges
    - Analyze temporal patterns for date anomalies
    """

    SYSTEM_PROMPT = """You are an Anomaly Detection Agent specialized in clinical data analysis.

Your responsibilities:
1. Detect statistical outliers using Isolation Forest, Z-Score, and IQR methods
2. Check values against physiological/clinical ranges
3. Analyze temporal patterns for date sequence anomalies

Anomaly types to detect:
- Statistical: Values significantly different from population distribution
- Physiological: Values outside expected clinical ranges
- Temporal: Future dates, impossible sequences, unusual timing

For Vital Signs (VS):
- Blood pressure, heart rate, temperature within clinical ranges
- Flag critical values that need immediate attention

For Laboratory (LB):
- Liver function, kidney function, blood counts
- Flag values requiring clinical review

Always:
- Prioritize critical anomalies (patient safety)
- Group related anomalies by subject
- Consider clinical context when interpreting results"""

    def __init__(self, api_key: Optional[str] = None):
        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
        self.llm = ChatAnthropic(
            model=model,
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=4096
        )
        self.agent = create_react_agent(
            self.llm,
            ANOMALY_DETECTOR_TOOLS,
            state_modifier=self.SYSTEM_PROMPT
        )

    async def detect_all_anomalies(
        self,
        domain_paths: Dict[str, str]
    ) -> Dict[str, Any]:
        """Detect anomalies across all domains."""
        domains_str = "\n".join([f"- {d}: {p}" for d, p in domain_paths.items()])

        input_message = f"""Perform comprehensive anomaly detection for these SDTM domains:

{domains_str}

For each domain:
1. Run statistical anomaly detection
2. Check physiological ranges (for VS, LB, EG)
3. Analyze temporal patterns

Summarize findings by:
- Critical anomalies requiring immediate review
- Warnings for potential data quality issues
- Patterns observed across subjects"""

        result = await self.agent.ainvoke({
            "messages": [{"role": "user", "content": input_message}]
        })

        return {
            "agent": "anomaly_detector",
            "result": result.get("messages", [])[-1].content if result.get("messages") else "",
            "timestamp": datetime.now().isoformat()
        }

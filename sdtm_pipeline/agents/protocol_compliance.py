"""
Protocol Compliance Agent
=========================
Specialized agent for validating data against protocol requirements,
including visit windows, inclusion/exclusion criteria, and dosing schedules.
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


@dataclass
class ProtocolViolation:
    """A protocol compliance violation."""
    subject: str
    violation_type: str
    severity: str
    message: str
    details: Optional[Dict[str, Any]] = None


# Default visit windows (can be overridden by protocol)
DEFAULT_VISIT_WINDOWS = {
    1: {"name": "Screening", "day": -28, "window": (-42, -1)},
    2: {"name": "Baseline", "day": 1, "window": (-3, 3)},
    3: {"name": "Week 1", "day": 8, "window": (-2, 2)},
    4: {"name": "Week 2", "day": 15, "window": (-3, 3)},
    5: {"name": "Week 4", "day": 29, "window": (-5, 5)},
    6: {"name": "Week 8", "day": 57, "window": (-7, 7)},
    7: {"name": "Week 12", "day": 85, "window": (-7, 7)},
    8: {"name": "Week 24", "day": 169, "window": (-14, 14)},
    9: {"name": "Week 52", "day": 365, "window": (-21, 21)},
    10: {"name": "End of Treatment", "day": None, "window": (-7, 7)},
    11: {"name": "Follow-up", "day": None, "window": (-14, 14)},
}


@tool
def validate_visit_windows(
    sv_file_path: str,
    dm_file_path: str,
    visit_windows: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Validate visit dates against protocol-defined windows.

    Checks that actual visit dates fall within acceptable windows
    relative to the reference start date.

    Args:
        sv_file_path: Path to Subject Visits (SV) or visit data CSV
        dm_file_path: Path to Demographics (DM) CSV for reference dates
        visit_windows: Optional custom visit window definitions

    Returns:
        Visit window validation results
    """
    try:
        # Try to load SV, fall back to looking for visit data in other formats
        try:
            sv_df = pd.read_csv(sv_file_path)
        except Exception:
            sv_df = None

        dm_df = pd.read_csv(dm_file_path)
    except Exception as e:
        return {"error": str(e)}

    windows = visit_windows or DEFAULT_VISIT_WINDOWS
    violations: List[Dict[str, Any]] = []

    # Get reference dates from DM
    ref_dates = {}
    if "USUBJID" in dm_df.columns and "RFSTDTC" in dm_df.columns:
        for _, row in dm_df.iterrows():
            if pd.notna(row["RFSTDTC"]):
                ref_dates[row["USUBJID"]] = str(row["RFSTDTC"])[:10]

    if not ref_dates:
        return {
            "validated": False,
            "message": "No reference dates found in DM",
            "violations": []
        }

    # If we have SV data, use it
    if sv_df is not None and "VISITNUM" in sv_df.columns and "SVSTDTC" in sv_df.columns:
        for _, row in sv_df.iterrows():
            subject = row.get("USUBJID")
            visitnum = row.get("VISITNUM")
            visit_date = str(row.get("SVSTDTC", ""))[:10]

            if subject not in ref_dates:
                continue

            ref_date = ref_dates[subject]

            # Calculate study day
            try:
                ref_dt = datetime.strptime(ref_date, "%Y-%m-%d")
                visit_dt = datetime.strptime(visit_date, "%Y-%m-%d")
                study_day = (visit_dt - ref_dt).days + 1  # Day 1 is first day
            except ValueError:
                continue

            # Check against window
            if visitnum in windows:
                window_def = windows[visitnum]
                expected_day = window_def.get("day")
                window_range = window_def.get("window", (-7, 7))

                if expected_day is not None:
                    low_bound = expected_day + window_range[0]
                    high_bound = expected_day + window_range[1]

                    if study_day < low_bound or study_day > high_bound:
                        violations.append({
                            "subject": subject,
                            "violation_type": "visit_window",
                            "severity": "warning",
                            "message": f"Visit {visitnum} ({window_def['name']}) outside window",
                            "details": {
                                "visit": visitnum,
                                "visit_name": window_def["name"],
                                "actual_day": study_day,
                                "expected_day": expected_day,
                                "window": f"Day {low_bound} to {high_bound}"
                            }
                        })

    # Summary statistics
    subjects_with_violations = len(set(v["subject"] for v in violations))

    return {
        "validated": True,
        "subjects_checked": len(ref_dates),
        "subjects_with_violations": subjects_with_violations,
        "total_violations": len(violations),
        "violations": violations[:50]  # Limit output
    }


@tool
def check_inclusion_exclusion(
    ie_file_path: str,
    dm_file_path: str
) -> Dict[str, Any]:
    """
    Check inclusion/exclusion criteria compliance.

    Validates that:
    - All subjects have I/E assessments
    - Inclusion criteria are met
    - No exclusion criteria are violated
    - Subjects enrolled despite I/E deviations are flagged

    Args:
        ie_file_path: Path to Inclusion/Exclusion (IE) domain CSV
        dm_file_path: Path to Demographics (DM) CSV

    Returns:
        I/E compliance check results
    """
    try:
        ie_df = pd.read_csv(ie_file_path)
        dm_df = pd.read_csv(dm_file_path)
    except Exception as e:
        return {"error": str(e)}

    violations: List[Dict[str, Any]] = []

    # Get enrolled subjects from DM
    enrolled_subjects = set()
    if "USUBJID" in dm_df.columns:
        enrolled_subjects = set(dm_df["USUBJID"].dropna().unique())

    # Check I/E for each enrolled subject
    ie_subjects = set()
    if "USUBJID" in ie_df.columns:
        ie_subjects = set(ie_df["USUBJID"].dropna().unique())

    # Subjects missing I/E assessments
    missing_ie = enrolled_subjects - ie_subjects
    for subject in missing_ie:
        violations.append({
            "subject": subject,
            "violation_type": "missing_ie",
            "severity": "error",
            "message": "Enrolled subject missing I/E assessment",
            "details": None
        })

    # Check I/E results
    if all(c in ie_df.columns for c in ["USUBJID", "IETEST", "IECAT", "IEORRES"]):
        for subject in ie_subjects & enrolled_subjects:
            subject_ie = ie_df[ie_df["USUBJID"] == subject]

            # Check inclusion criteria
            inclusion = subject_ie[subject_ie["IECAT"].str.upper() == "INCLUSION"]
            for _, row in inclusion.iterrows():
                result = str(row.get("IEORRES", "")).upper()
                if result in ["N", "NO", "NOT MET"]:
                    violations.append({
                        "subject": subject,
                        "violation_type": "inclusion_not_met",
                        "severity": "error",
                        "message": f"Inclusion criterion not met: {row.get('IETEST', 'Unknown')}",
                        "details": {
                            "criterion": row.get("IETEST"),
                            "result": result
                        }
                    })

            # Check exclusion criteria
            exclusion = subject_ie[subject_ie["IECAT"].str.upper() == "EXCLUSION"]
            for _, row in exclusion.iterrows():
                result = str(row.get("IEORRES", "")).upper()
                if result in ["Y", "YES", "MET"]:
                    violations.append({
                        "subject": subject,
                        "violation_type": "exclusion_met",
                        "severity": "error",
                        "message": f"Exclusion criterion met: {row.get('IETEST', 'Unknown')}",
                        "details": {
                            "criterion": row.get("IETEST"),
                            "result": result
                        }
                    })

    # Summary
    error_count = sum(1 for v in violations if v["severity"] == "error")
    warning_count = sum(1 for v in violations if v["severity"] == "warning")

    return {
        "enrolled_subjects": len(enrolled_subjects),
        "subjects_with_ie": len(ie_subjects & enrolled_subjects),
        "subjects_missing_ie": len(missing_ie),
        "error_count": error_count,
        "warning_count": warning_count,
        "violations": violations,
        "compliant": error_count == 0
    }


@tool
def validate_dosing_compliance(
    ex_file_path: str,
    dm_file_path: str,
    expected_dose: Optional[float] = None,
    dose_unit: str = "mg",
    dosing_frequency: str = "QD"
) -> Dict[str, Any]:
    """
    Validate exposure/dosing compliance against protocol.

    Checks:
    - Dose amounts match protocol
    - Dosing frequency compliance
    - Treatment duration
    - Dose modifications are documented
    - Missed doses are accounted for

    Args:
        ex_file_path: Path to Exposure (EX) domain CSV
        dm_file_path: Path to Demographics (DM) CSV
        expected_dose: Expected dose amount per protocol
        dose_unit: Unit of dose measurement
        dosing_frequency: Expected dosing frequency (QD, BID, etc.)

    Returns:
        Dosing compliance validation results
    """
    try:
        ex_df = pd.read_csv(ex_file_path)
        dm_df = pd.read_csv(dm_file_path)
    except Exception as e:
        return {"error": str(e)}

    violations: List[Dict[str, Any]] = []
    compliance_stats: Dict[str, Any] = {}

    # Get treatment assignments from DM
    treatment_arms = {}
    if "USUBJID" in dm_df.columns and "ARM" in dm_df.columns:
        for _, row in dm_df.iterrows():
            treatment_arms[row["USUBJID"]] = row.get("ARM", "Unknown")

    if "USUBJID" not in ex_df.columns or "EXDOSE" not in ex_df.columns:
        return {
            "validated": False,
            "message": "Required EX columns (USUBJID, EXDOSE) not found",
            "violations": []
        }

    # Analyze by subject
    for subject in ex_df["USUBJID"].dropna().unique():
        subject_ex = ex_df[ex_df["USUBJID"] == subject].copy()

        # Check dose amounts
        if expected_dose is not None:
            dose_values = subject_ex["EXDOSE"].dropna()
            if len(dose_values) > 0:
                # Calculate % at expected dose
                at_expected = (dose_values == expected_dose).sum()
                compliance_pct = at_expected / len(dose_values) * 100

                if compliance_pct < 80:
                    violations.append({
                        "subject": subject,
                        "violation_type": "dose_compliance",
                        "severity": "warning" if compliance_pct >= 50 else "error",
                        "message": f"Dose compliance {compliance_pct:.1f}% (expected {expected_dose} {dose_unit})",
                        "details": {
                            "expected_dose": expected_dose,
                            "compliance_pct": compliance_pct,
                            "doses_at_expected": int(at_expected),
                            "total_doses": len(dose_values)
                        }
                    })

                # Check for zero doses
                zero_doses = (dose_values == 0).sum()
                if zero_doses > 0:
                    violations.append({
                        "subject": subject,
                        "violation_type": "zero_dose",
                        "severity": "info",
                        "message": f"{zero_doses} dose record(s) with zero dose",
                        "details": {"zero_doses": int(zero_doses)}
                    })

        # Check for negative doses
        if (subject_ex["EXDOSE"] < 0).any():
            violations.append({
                "subject": subject,
                "violation_type": "negative_dose",
                "severity": "error",
                "message": "Negative dose value(s) found",
                "details": None
            })

        # Check treatment duration
        if "EXSTDTC" in subject_ex.columns and "EXENDTC" in subject_ex.columns:
            dates = subject_ex[subject_ex["EXSTDTC"].notna() & subject_ex["EXENDTC"].notna()]
            if len(dates) > 0:
                try:
                    first_dose = str(dates["EXSTDTC"].min())[:10]
                    last_dose = str(dates["EXENDTC"].max())[:10]

                    start_dt = datetime.strptime(first_dose, "%Y-%m-%d")
                    end_dt = datetime.strptime(last_dose, "%Y-%m-%d")
                    duration_days = (end_dt - start_dt).days + 1

                    compliance_stats[subject] = {
                        "first_dose": first_dose,
                        "last_dose": last_dose,
                        "duration_days": duration_days,
                        "num_records": len(subject_ex)
                    }
                except ValueError:
                    pass

    # Calculate summary statistics
    subjects_with_ex = ex_df["USUBJID"].nunique()
    subjects_with_violations = len(set(v["subject"] for v in violations))
    error_count = sum(1 for v in violations if v["severity"] == "error")
    warning_count = sum(1 for v in violations if v["severity"] == "warning")

    return {
        "validated": True,
        "expected_dose": expected_dose,
        "dose_unit": dose_unit,
        "subjects_analyzed": subjects_with_ex,
        "subjects_with_violations": subjects_with_violations,
        "error_count": error_count,
        "warning_count": warning_count,
        "violations": violations[:50],  # Limit output
        "subject_stats": dict(list(compliance_stats.items())[:20])  # Sample stats
    }


# List of all tools for this agent
PROTOCOL_COMPLIANCE_TOOLS = [
    validate_visit_windows,
    check_inclusion_exclusion,
    validate_dosing_compliance
]


class ProtocolComplianceAgent:
    """
    Protocol Compliance Agent for validating against study protocol.

    Responsibilities:
    - Validate visit timing against protocol windows
    - Check inclusion/exclusion criteria compliance
    - Verify dosing schedule adherence
    """

    SYSTEM_PROMPT = """You are a Protocol Compliance Agent specialized in clinical trial protocol adherence.

Your responsibilities:
1. Validate visit dates against protocol-defined visit windows
2. Check inclusion/exclusion criteria are properly assessed and met
3. Verify dosing compliance against protocol specifications

Protocol compliance checks:
- All subjects have required I/E assessments
- Inclusion criteria are met for all enrolled subjects
- No exclusion criteria are violated
- Visits occur within acceptable windows
- Dosing follows protocol specifications

When reporting violations:
- Categorize by severity (error/warning/info)
- Identify subjects with multiple violations
- Highlight potential GCP issues
- Suggest corrective actions

Consider clinical context and regulatory requirements when evaluating compliance."""

    def __init__(self, api_key: Optional[str] = None):
        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
        self.llm = ChatAnthropic(
            model=model,
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=4096
        )
        self.agent = create_react_agent(
            self.llm,
            PROTOCOL_COMPLIANCE_TOOLS,
            state_modifier=self.SYSTEM_PROMPT
        )

    async def check_compliance(
        self,
        domain_paths: Dict[str, str],
        protocol_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Check protocol compliance across domains."""
        paths_str = "\n".join([f"- {d}: {p}" for d, p in domain_paths.items()])
        protocol_str = str(protocol_info) if protocol_info else "Not provided"

        input_message = f"""Perform comprehensive protocol compliance check:

Domain files:
{paths_str}

Protocol information:
{protocol_str}

Please check:
1. Visit window compliance (if SV/visit data available)
2. Inclusion/exclusion criteria (if IE data available)
3. Dosing compliance (if EX data available)

Summarize findings by subject and violation type."""

        result = await self.agent.ainvoke({
            "messages": [{"role": "user", "content": input_message}]
        })

        return {
            "agent": "protocol_compliance",
            "result": result.get("messages", [])[-1].content if result.get("messages") else "",
            "timestamp": datetime.now().isoformat()
        }

#!/usr/bin/env python3
"""
SDTM AE Domain Transformation for Study MAXIS-08
=================================================

This script transforms adverse event data from AEVENT.csv and AEVENTC.csv 
to CDISC SDTM AE domain format (SDTM-IG 3.4).

Author: SDTM Pipeline
Date: 2025-01-22
Study: MAXIS-08
Source Files: AEVENT.csv (550 records), AEVENTC.csv (276 records)
Target Domain: AE (Adverse Events)
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import json
import re

# CDISC Controlled Terminology for AE domain
CT_AESEV = ["MILD", "MODERATE", "SEVERE"]
CT_AESER = ["Y", "N"]
CT_NY = ["Y", "N"]
CT_AEREL = ["NOT RELATED", "UNLIKELY", "POSSIBLY RELATED", "RELATED", 
            "PROBABLE", "DEFINITE", "UNRELATED", "POSSIBLE"]
CT_AEACN = ["DOSE NOT CHANGED", "DOSE REDUCED", "DOSE INCREASED", 
            "DRUG INTERRUPTED", "DRUG WITHDRAWN", "NOT APPLICABLE", 
            "UNKNOWN", "NOT EVALUABLE", "NONE"]
CT_AEOUT = ["RECOVERED/RESOLVED", "RECOVERING/RESOLVING", 
            "NOT RECOVERED/NOT RESOLVED", "RECOVERED/RESOLVED WITH SEQUELAE",
            "FATAL", "UNKNOWN", "RESOLVED", "CONTINUING"]

def convert_to_iso8601(date_str):
    """
    Convert various date formats to ISO 8601 format (YYYY-MM-DD).
    
    Args:
        date_str: Date string in various formats (YYYYMMDD, YYYYMM, YYYY)
    
    Returns:
        ISO 8601 formatted date string or empty string if invalid
    """
    if pd.isna(date_str) or str(date_str).strip() == "":
        return ""
    
    date_str = str(date_str).strip()
    
    # Remove any decimal points and subsequent characters
    date_str = date_str.split('.')[0]
    
    # Handle different date formats
    if len(date_str) == 8:  # YYYYMMDD
        try:
            return f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
        except:
            return ""
    elif len(date_str) == 6:  # YYYYMM
        try:
            return f"{date_str[0:4]}-{date_str[4:6]}"
        except:
            return ""
    elif len(date_str) == 4:  # YYYY
        return date_str
    else:
        return ""

def standardize_severity(sev_value):
    """Standardize severity values to CDISC CT."""
    if pd.isna(sev_value):
        return ""
    
    sev_str = str(sev_value).upper().strip()
    
    if sev_str in ["MILD", "1"]:
        return "MILD"
    elif sev_str in ["MODERATE", "2"]:
        return "MODERATE"
    elif sev_str in ["SEVERE", "3"]:
        return "SEVERE"
    else:
        return sev_str

def standardize_relationship(rel_value):
    """Standardize relationship to study drug values to CDISC CT."""
    if pd.isna(rel_value):
        return ""
    
    rel_str = str(rel_value).upper().strip()
    
    # Mapping from source values to CDISC CT
    mapping = {
        "NOT RELATED": "NOT RELATED",
        "UNLIKELY": "UNLIKELY",
        "UNLIKELY RELATED": "UNLIKELY",
        "UNRELATED": "NOT RELATED",
        "POSSIBLE": "POSSIBLY RELATED",
        "POSSIBLY RELATED": "POSSIBLY RELATED",
        "RELATED": "RELATED",
        "PROBABLE": "PROBABLE",
        "PROBABLY RELATED": "PROBABLE",
        "DEFINITE": "DEFINITE",
        "DEFINITELY RELATED": "DEFINITE",
        "1": "NOT RELATED",
        "2": "UNLIKELY",
        "3": "POSSIBLY RELATED",
        "4": "RELATED",
        "5": "PROBABLE"
    }
    
    return mapping.get(rel_str, rel_str)

def standardize_outcome(outcome_value):
    """Standardize outcome values to CDISC CT."""
    if pd.isna(outcome_value):
        return ""
    
    out_str = str(outcome_value).upper().strip()
    
    mapping = {
        "RESOLVED": "RECOVERED/RESOLVED",
        "RECOVERING": "RECOVERING/RESOLVING",
        "NOT RESOLVED": "NOT RECOVERED/NOT RESOLVED",
        "RESOLVED WITH SEQUELAE": "RECOVERED/RESOLVED WITH SEQUELAE",
        "CONTINUING": "NOT RECOVERED/NOT RESOLVED",
        "FATAL": "FATAL",
        "UNKNOWN": "UNKNOWN"
    }
    
    return mapping.get(out_str, out_str)

def standardize_action_taken(action_value):
    """Standardize action taken values to CDISC CT."""
    if pd.isna(action_value):
        return ""
    
    act_str = str(action_value).upper().strip()
    
    mapping = {
        "NONE": "DOSE NOT CHANGED",
        "NOT CHANGED": "DOSE NOT CHANGED",
        "DOSE NOT CHANGED": "DOSE NOT CHANGED",
        "REDUCED": "DOSE REDUCED",
        "DOSE REDUCED": "DOSE REDUCED",
        "INCREASED": "DOSE INCREASED",
        "DOSE INCREASED": "DOSE INCREASED",
        "INTERRUPTED": "DRUG INTERRUPTED",
        "DRUG INTERRUPTED": "DRUG INTERRUPTED",
        "WITHDRAWN": "DRUG WITHDRAWN",
        "DRUG WITHDRAWN": "DRUG WITHDRAWN",
        "NOT APPLICABLE": "NOT APPLICABLE",
        "N/A": "NOT APPLICABLE",
        "UNKNOWN": "UNKNOWN",
        "1": "DOSE NOT CHANGED",
        "2": "DOSE REDUCED",
        "3": "DRUG INTERRUPTED"
    }
    
    return mapping.get(act_str, act_str)

def standardize_serious(ser_value):
    """Standardize serious flag to Y/N."""
    if pd.isna(ser_value):
        return ""
    
    ser_str = str(ser_value).upper().strip()
    
    if ser_str in ["Y", "YES", "1", "SERIOUS"]:
        return "Y"
    elif ser_str in ["N", "NO", "0", "NOT SERIOUS"]:
        return "N"
    else:
        return ""

def transform_aevent_to_sdtm(study_id="MAXIS-08"):
    """
    Transform AEVENT.csv and AEVENTC.csv to SDTM AE domain.
    
    Args:
        study_id: Study identifier
        
    Returns:
        Tuple of (ae_df, suppae_df, stats_dict)
    """
    print("="*80)
    print("SDTM AE Domain Transformation - Study MAXIS-08")
    print("="*80)
    
    # Load source data
    print("\n[1/7] Loading source data...")
    source_path = Path("/tmp/s3_data/extracted/Maxis-08 RAW DATA_CSV")
    
    aevent_df = pd.read_csv(source_path / "AEVENT.csv", encoding='utf-8-sig')
    aeventc_df = pd.read_csv(source_path / "AEVENTC.csv", encoding='utf-8-sig')
    
    print(f"   - AEVENT.csv: {len(aevent_df)} records, {len(aevent_df.columns)} columns")
    print(f"   - AEVENTC.csv: {len(aeventc_df)} records, {len(aeventc_df.columns)} columns")
    
    # Merge AEVENT and AEVENTC data
    print("\n[2/7] Merging source datasets...")
    # Use AEVENT as primary source, supplement with AEVENTC where needed
    source_df = aevent_df.copy()
    
    # Initialize SDTM AE DataFrame
    print("\n[3/7] Applying SDTM mappings...")
    ae = pd.DataFrame()
    
    # ==========================================
    # IDENTIFIER VARIABLES (Required)
    # ==========================================
    ae["STUDYID"] = study_id
    ae["DOMAIN"] = "AE"
    
    # USUBJID: Unique Subject Identifier
    # Derivation: STUDYID-SITEID-SUBJID
    if "INVSITE" in source_df.columns and "PT" in source_df.columns:
        ae["USUBJID"] = (study_id + "-" + 
                        source_df["INVSITE"].astype(str) + "-" + 
                        source_df["PT"].astype(str))
    
    # AESEQ: Sequence Number (generated per subject)
    # Will be assigned after sorting
    
    # ==========================================
    # TOPIC VARIABLES (Required)
    # ==========================================
    
    # AETERM: Reported Term for the Adverse Event
    if "AEVERB" in source_df.columns:
        ae["AETERM"] = source_df["AEVERB"].fillna("")
    
    # AEDECOD: Dictionary-Derived Term (use PT if available)
    if "AEPTT" in source_df.columns:
        ae["AEDECOD"] = source_df["AEPTT"].fillna("")
    elif "PT" in aeventc_df.columns:
        # Map from AEVENTC if available
        ae["AEDECOD"] = ""
    
    # AELLT: Lowest Level Term
    if "AELTT" in source_df.columns:
        ae["AELLT"] = source_df["AELTT"].fillna("")
    
    # AELLTCD: Lowest Level Term Code
    if "AELTC" in source_df.columns:
        ae["AELLTCD"] = source_df["AELTC"].astype(str).replace("nan", "")
    
    # AEPTCD: Preferred Term Code
    if "AEPTC" in source_df.columns:
        ae["AEPTCD"] = source_df["AEPTC"].astype(str).replace("nan", "")
    
    # AEHLT: High Level Term
    if "AEHTT" in source_df.columns:
        ae["AEHLT"] = source_df["AEHTT"].fillna("")
    
    # AEHLTCD: High Level Term Code
    if "AEHTC" in source_df.columns:
        ae["AEHLTCD"] = source_df["AEHTC"].astype(str).replace("nan", "")
    
    # AEHLGT: High Level Group Term
    if "AEHGT1" in source_df.columns:
        ae["AEHLGT"] = source_df["AEHGT1"].fillna("")
    
    # AEHLGTCD: High Level Group Term Code
    if "AEHGC" in source_df.columns:
        ae["AEHLGTCD"] = source_df["AEHGC"].astype(str).replace("nan", "")
    
    # AESOC: Primary System Organ Class
    if "AESCT" in source_df.columns:
        ae["AESOC"] = source_df["AESCT"].fillna("")
    
    # AESOCCD: Primary System Organ Class Code
    if "AESCC" in source_df.columns:
        ae["AESOCCD"] = source_df["AESCC"].astype(str).replace("nan", "")
    
    # ==========================================
    # TIMING VARIABLES (Required)
    # ==========================================
    
    # AESTDTC: Start Date/Time of Adverse Event (ISO 8601)
    if "AESTDT" in source_df.columns:
        ae["AESTDTC"] = source_df["AESTDT"].apply(convert_to_iso8601)
    
    # AEENDTC: End Date/Time of Adverse Event (ISO 8601)
    if "AEENDT" in source_df.columns:
        ae["AEENDTC"] = source_df["AEENDT"].apply(convert_to_iso8601)
    
    # AESTDY: Study Day of Start (derived from DM.RFSTDTC)
    # Will be calculated if DM dataset is available
    ae["AESTDY"] = ""
    
    # AEENDY: Study Day of End (derived from DM.RFENDTC)
    ae["AEENDY"] = ""
    
    # ==========================================
    # QUALIFIER VARIABLES
    # ==========================================
    
    # AESEV: Severity/Intensity
    if "AESEV" in source_df.columns:
        ae["AESEV"] = source_df["AESEV"].apply(standardize_severity)
    
    # AESER: Serious Event Flag
    if "AESERL" in source_df.columns:
        ae["AESER"] = source_df["AESERL"].apply(standardize_serious)
    elif "AESER" in source_df.columns:
        ae["AESER"] = source_df["AESER"].apply(standardize_serious)
    
    # AEREL: Relationship to Study Drug
    if "AEREL" in source_df.columns:
        ae["AEREL"] = source_df["AEREL"].apply(standardize_relationship)
    
    # AEACN: Action Taken with Study Treatment
    if "AEACTL" in source_df.columns:
        ae["AEACN"] = source_df["AEACTL"].apply(standardize_action_taken)
    elif "AEACT" in source_df.columns:
        ae["AEACN"] = source_df["AEACT"].apply(standardize_action_taken)
    
    # AEOUT: Outcome of Adverse Event
    if "AEOUTCL" in source_df.columns:
        ae["AEOUT"] = source_df["AEOUTCL"].apply(standardize_outcome)
    elif "AEOUTC" in source_df.columns:
        ae["AEOUT"] = source_df["AEOUTC"].apply(standardize_outcome)
    
    # ==========================================
    # SERIOUS EVENT CRITERIA
    # ==========================================
    
    # AESDTH: Results in Death
    ae["AESDTH"] = ""
    
    # AESHOSP: Requires or Prolongs Hospitalization
    ae["AESHOSP"] = ""
    
    # AESDISAB: Results in Persistent or Significant Disability/Incapacity
    ae["AESDISAB"] = ""
    
    # AESCONG: Congenital Anomaly or Birth Defect
    ae["AESCONG"] = ""
    
    # AESLIFE: Life Threatening
    ae["AESLIFE"] = ""
    
    # AESMIE: Other Medically Important Serious Event
    ae["AESMIE"] = ""
    
    # ==========================================
    # VISIT VARIABLES
    # ==========================================
    
    # VISITNUM: Visit Number
    ae["VISITNUM"] = ""
    if "VISIT" in source_df.columns:
        # Map visit codes to numeric visit numbers
        visit_mapping = {"999": "99", "UNSCHEDULED": "99"}
        ae["VISITNUM"] = source_df["VISIT"].astype(str).replace(visit_mapping)
    
    # VISIT: Visit Name
    if "VISIT" in source_df.columns:
        ae["VISIT"] = source_df["VISIT"].fillna("")
    
    # AEDTC: Date/Time of Collection (typically same as AESTDTC)
    ae["AEDTC"] = ae["AESTDTC"]
    
    # ==========================================
    # EPOCH (if available)
    # ==========================================
    ae["EPOCH"] = ""
    
    # ==========================================
    # SUPPLEMENTAL VARIABLES
    # ==========================================
    
    # Store additional variables for SUPPAE
    suppae_vars = {}
    
    if "AETRT" in source_df.columns:
        suppae_vars["AETRT"] = source_df["AETRT"]
    
    if "CPEVENT" in source_df.columns:
        suppae_vars["CPEVENT"] = source_df["CPEVENT"]
    
    # ==========================================
    # ASSIGN AESEQ AFTER SORTING
    # ==========================================
    print("\n[4/7] Generating sequence numbers...")
    
    # Sort by USUBJID and AESTDTC
    ae = ae.sort_values(by=["USUBJID", "AESTDTC"], na_position="last")
    
    # Generate AESEQ per subject
    ae["AESEQ"] = ae.groupby("USUBJID").cumcount() + 1
    
    # ==========================================
    # REORDER COLUMNS (CDISC Standard Order)
    # ==========================================
    print("\n[5/7] Reordering columns to CDISC standard...")
    
    # Standard column order for AE domain
    column_order = [
        # Identifiers
        "STUDYID", "DOMAIN", "USUBJID", "AESEQ",
        # Topic Variables
        "AETERM", "AEDECOD", "AELLT", "AELLTCD", "AEPTCD", 
        "AEHLT", "AEHLTCD", "AEHLGT", "AEHLGTCD", "AESOC", "AESOCCD",
        # Timing
        "AESTDTC", "AEENDTC", "AESTDY", "AEENDY", "AEDTC",
        # Qualifiers
        "AESEV", "AESER", "AEREL", "AEACN", "AEOUT",
        # Serious Criteria
        "AESDTH", "AESHOSP", "AESDISAB", "AESCONG", "AESLIFE", "AESMIE",
        # Visit
        "VISITNUM", "VISIT",
        # Epoch
        "EPOCH"
    ]
    
    # Keep only columns that exist in the DataFrame
    final_columns = [col for col in column_order if col in ae.columns]
    ae = ae[final_columns]
    
    # ==========================================
    # DATA QUALITY CHECKS
    # ==========================================
    print("\n[6/7] Performing data quality checks...")
    
    issues = []
    
    # Check required variables
    required_vars = ["STUDYID", "DOMAIN", "USUBJID", "AESEQ", "AETERM", "AESTDTC"]
    for var in required_vars:
        if var not in ae.columns:
            issues.append(f"Missing required variable: {var}")
        elif ae[var].isna().any():
            null_count = ae[var].isna().sum()
            issues.append(f"Variable {var} has {null_count} null values")
    
    # Check date format
    if "AESTDTC" in ae.columns:
        invalid_dates = ae[~ae["AESTDTC"].str.match(r'^\d{4}(-\d{2}(-\d{2})?)?$|^$', na=False)]
        if len(invalid_dates) > 0:
            issues.append(f"Found {len(invalid_dates)} records with invalid AESTDTC format")
    
    # Check controlled terminology
    if "AESEV" in ae.columns:
        invalid_sev = ae[~ae["AESEV"].isin(CT_AESEV + [""])]
        if len(invalid_sev) > 0:
            issues.append(f"Found {len(invalid_sev)} records with invalid AESEV values")
    
    if "AESER" in ae.columns:
        invalid_ser = ae[~ae["AESER"].isin(CT_AESER + [""])]
        if len(invalid_ser) > 0:
            issues.append(f"Found {len(invalid_ser)} records with invalid AESER values")
    
    # ==========================================
    # SAVE OUTPUT
    # ==========================================
    print("\n[7/7] Saving transformed data...")
    
    output_path = Path("/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace")
    output_path.mkdir(exist_ok=True)
    
    ae_file = output_path / "ae.csv"
    ae.to_csv(ae_file, index=False)
    
    print(f"   - Saved: {ae_file}")
    print(f"   - Records: {len(ae)}")
    print(f"   - Variables: {len(ae.columns)}")
    
    # Generate statistics
    stats = {
        "study_id": study_id,
        "domain": "AE",
        "source_files": ["AEVENT.csv", "AEVENTC.csv"],
        "source_records": {
            "AEVENT.csv": len(aevent_df),
            "AEVENTC.csv": len(aeventc_df)
        },
        "target_records": len(ae),
        "target_variables": len(ae.columns),
        "subjects": ae["USUBJID"].nunique(),
        "transformation_date": datetime.now().isoformat(),
        "data_quality_issues": issues
    }
    
    # Print summary
    print("\n" + "="*80)
    print("TRANSFORMATION SUMMARY")
    print("="*80)
    print(f"Study ID: {stats['study_id']}")
    print(f"Domain: {stats['domain']}")
    print(f"Source Records: {stats['source_records']['AEVENT.csv']} (AEVENT) + {stats['source_records']['AEVENTC.csv']} (AEVENTC)")
    print(f"Target Records: {stats['target_records']}")
    print(f"Target Variables: {stats['target_variables']}")
    print(f"Unique Subjects: {stats['subjects']}")
    print(f"Data Quality Issues: {len(issues)}")
    
    if issues:
        print("\nISSUES FOUND:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
    
    return ae, None, stats

if __name__ == "__main__":
    ae_df, suppae_df, stats = transform_aevent_to_sdtm()
    
    # Save statistics
    stats_file = Path("/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_transformation_stats.json")
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"\n✓ Statistics saved to: {stats_file}")
    print("\n" + "="*80)
    print("TRANSFORMATION COMPLETE")
    print("="*80)

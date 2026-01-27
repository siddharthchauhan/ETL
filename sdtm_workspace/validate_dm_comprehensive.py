#!/usr/bin/env python3
"""
Comprehensive DM Domain Validation Script
Study: MAXIS-08
Domain: DM (Demographics)

Validation Layers:
1. Structural validation (required variables, data types)
2. Controlled terminology compliance
3. Date format and consistency
4. Business rules
5. Data quality checks
"""

import pandas as pd
import re
from datetime import datetime
from collections import defaultdict

# File path
DM_FILE = "/Users/siddharth/Downloads/ETL/ETL/sdtm_chat_output/sdtm_data/dm.csv"
STUDY_ID = "MAXIS-08"

# CDISC Controlled Terminology (based on SDTM-CT 2025-09-26)
CT_SEX = ["M", "F", "U", "UNDIFFERENTIATED"]
CT_AGEU = ["YEARS", "MONTHS", "WEEKS", "DAYS", "HOURS"]
CT_RACE = [
    "AMERICAN INDIAN OR ALASKA NATIVE",
    "ASIAN",
    "BLACK OR AFRICAN AMERICAN",
    "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER",
    "WHITE",
    "MULTIPLE",
    "NOT REPORTED",
    "UNKNOWN"
]
CT_ETHNIC = [
    "HISPANIC OR LATINO",
    "NOT HISPANIC OR LATINO",
    "NOT REPORTED",
    "UNKNOWN"
]
CT_DTHFL = ["Y", None, ""]  # Only Y or null/empty allowed

# DM Required Variables (SDTM-IG 3.4)
REQUIRED_VARS = [
    "STUDYID", "DOMAIN", "USUBJID", "SUBJID", "RFSTDTC", "RFENDTC",
    "SITEID", "BRTHDTC", "AGE", "AGEU", "SEX", "RACE", "ETHNIC",
    "ARMCD", "ARM", "COUNTRY"
]

# Expected/Permissible Variables
EXPECTED_VARS = [
    "RFXSTDTC", "RFXENDTC", "RFICDTC", "RFPENDTC", "DTHDTC", "DTHFL",
    "ACTARMCD", "ACTARM", "INVID", "INVNAM", "DMDTC", "DMDY"
]

class ValidationReport:
    """Stores validation findings."""
    
    def __init__(self):
        self.critical_errors = []
        self.major_errors = []
        self.minor_errors = []
        self.warnings = []
        self.info = []
        
    def add_critical(self, rule_id, message, records=None):
        self.critical_errors.append({
            "rule_id": rule_id,
            "severity": "CRITICAL",
            "message": message,
            "records": records or []
        })
    
    def add_major(self, rule_id, message, records=None):
        self.major_errors.append({
            "rule_id": rule_id,
            "severity": "MAJOR",
            "message": message,
            "records": records or []
        })
    
    def add_minor(self, rule_id, message, records=None):
        self.minor_errors.append({
            "rule_id": rule_id,
            "severity": "MINOR",
            "message": message,
            "records": records or []
        })
    
    def add_warning(self, rule_id, message, records=None):
        self.warnings.append({
            "rule_id": rule_id,
            "severity": "WARNING",
            "message": message,
            "records": records or []
        })
    
    def add_info(self, message):
        self.info.append(message)
    
    def total_errors(self):
        return len(self.critical_errors) + len(self.major_errors) + len(self.minor_errors)
    
    def summary(self):
        return {
            "critical": len(self.critical_errors),
            "major": len(self.major_errors),
            "minor": len(self.minor_errors),
            "warnings": len(self.warnings),
            "total_errors": self.total_errors()
        }


def validate_dm_domain(file_path):
    """Main validation function."""
    
    report = ValidationReport()
    
    # Load data
    try:
        df = pd.read_csv(file_path)
        report.add_info(f"✓ Successfully loaded {len(df)} records from {file_path}")
    except Exception as e:
        report.add_critical("FILE001", f"Failed to load file: {str(e)}")
        return report, None
    
    report.add_info(f"✓ Dataset contains {len(df)} records and {len(df.columns)} columns")
    
    # ========== LAYER 1: STRUCTURAL VALIDATION ==========
    
    # Check required variables
    missing_required = [var for var in REQUIRED_VARS if var not in df.columns]
    if missing_required:
        report.add_critical(
            "SD1002",
            f"Missing required variables: {', '.join(missing_required)}",
            []
        )
    else:
        report.add_info(f"✓ All {len(REQUIRED_VARS)} required variables present")
    
    # Check DOMAIN value
    if "DOMAIN" in df.columns:
        invalid_domain = df[df["DOMAIN"] != "DM"]
        if len(invalid_domain) > 0:
            report.add_critical(
                "SD1003",
                f"DOMAIN must be 'DM', found {len(invalid_domain)} records with invalid values",
                invalid_domain["USUBJID"].tolist() if "USUBJID" in df.columns else []
            )
    
    # Check STUDYID consistency
    if "STUDYID" in df.columns:
        unique_studies = df["STUDYID"].unique()
        if len(unique_studies) > 1:
            report.add_major(
                "SD1004",
                f"Multiple STUDYID values found: {unique_studies.tolist()}",
                []
            )
        elif unique_studies[0] != STUDY_ID:
            report.add_warning(
                "BR001",
                f"STUDYID is '{unique_studies[0]}', expected '{STUDY_ID}'",
                []
            )
    
    # ========== LAYER 2: DATA TYPE VALIDATION ==========
    
    # AGE should be numeric
    if "AGE" in df.columns:
        non_numeric_age = df[df["AGE"].notna() & ~df["AGE"].astype(str).str.match(r'^\d+\.?\d*$')]
        if len(non_numeric_age) > 0:
            report.add_critical(
                "SD1009",
                f"AGE must be numeric, found {len(non_numeric_age)} invalid values",
                non_numeric_age["USUBJID"].tolist() if "USUBJID" in df.columns else []
            )
        else:
            report.add_info("✓ AGE data type is valid (numeric)")
    
    # ========== LAYER 3: CONTROLLED TERMINOLOGY VALIDATION ==========
    
    # Validate SEX
    if "SEX" in df.columns:
        invalid_sex = df[df["SEX"].notna() & ~df["SEX"].isin(CT_SEX)]
        if len(invalid_sex) > 0:
            report.add_critical(
                "SD1091",
                f"Invalid SEX values (not in CDISC CT): {invalid_sex['SEX'].unique().tolist()}. Expected: {CT_SEX}",
                invalid_sex["USUBJID"].tolist() if "USUBJID" in df.columns else []
            )
        else:
            report.add_info("✓ SEX values comply with controlled terminology")
    
    # Validate RACE
    if "RACE" in df.columns:
        invalid_race = df[df["RACE"].notna() & ~df["RACE"].isin(CT_RACE)]
        if len(invalid_race) > 0:
            report.add_major(
                "SD1091",
                f"Invalid RACE values (not in CDISC CT): {invalid_race['RACE'].unique().tolist()}",
                invalid_race["USUBJID"].tolist() if "USUBJID" in df.columns else []
            )
        else:
            report.add_info("✓ RACE values comply with controlled terminology")
    
    # Validate ETHNIC
    if "ETHNIC" in df.columns:
        invalid_ethnic = df[df["ETHNIC"].notna() & ~df["ETHNIC"].isin(CT_ETHNIC)]
        if len(invalid_ethnic) > 0:
            report.add_major(
                "SD1091",
                f"Invalid ETHNIC values (not in CDISC CT): {invalid_ethnic['ETHNIC'].unique().tolist()}",
                invalid_ethnic["USUBJID"].tolist() if "USUBJID" in df.columns else []
            )
        else:
            report.add_info("✓ ETHNIC values comply with controlled terminology")
    
    # Validate AGEU
    if "AGEU" in df.columns:
        invalid_ageu = df[df["AGEU"].notna() & ~df["AGEU"].isin(CT_AGEU)]
        if len(invalid_ageu) > 0:
            report.add_critical(
                "SD1091",
                f"Invalid AGEU values (not in CDISC CT): {invalid_ageu['AGEU'].unique().tolist()}. Expected: {CT_AGEU}",
                invalid_ageu["USUBJID"].tolist() if "USUBJID" in df.columns else []
            )
        else:
            report.add_info("✓ AGEU values comply with controlled terminology")
    
    # Validate DTHFL
    if "DTHFL" in df.columns:
        invalid_dthfl = df[df["DTHFL"].notna() & (df["DTHFL"] != "Y")]
        if len(invalid_dthfl) > 0:
            report.add_major(
                "SD1091",
                f"DTHFL must be 'Y' or null, found {len(invalid_dthfl)} invalid values",
                invalid_dthfl["USUBJID"].tolist() if "USUBJID" in df.columns else []
            )
    
    # ========== LAYER 4: DATE VALIDATION ==========
    
    # ISO 8601 pattern
    iso_pattern = r'^\d{4}(-\d{2}(-\d{2}(T\d{2}:\d{2}(:\d{2})?)?)?)?$'
    
    # Check all DTC variables
    dtc_vars = [col for col in df.columns if col.endswith("DTC")]
    for dtc_var in dtc_vars:
        invalid_dates = df[df[dtc_var].notna() & ~df[dtc_var].astype(str).str.match(iso_pattern)]
        if len(invalid_dates) > 0:
            report.add_critical(
                "SD1025",
                f"{dtc_var} contains {len(invalid_dates)} invalid ISO 8601 dates: {invalid_dates[dtc_var].unique().tolist()[:5]}",
                invalid_dates["USUBJID"].tolist() if "USUBJID" in df.columns else []
            )
        else:
            if df[dtc_var].notna().sum() > 0:
                report.add_info(f"✓ {dtc_var} values are in valid ISO 8601 format")
    
    # Check date logic: RFSTDTC <= RFENDTC
    if "RFSTDTC" in df.columns and "RFENDTC" in df.columns:
        both_present = df[df["RFSTDTC"].notna() & df["RFENDTC"].notna()]
        if len(both_present) > 0:
            try:
                invalid_date_logic = both_present[both_present["RFSTDTC"] > both_present["RFENDTC"]]
                if len(invalid_date_logic) > 0:
                    report.add_critical(
                        "SD1046",
                        f"RFSTDTC after RFENDTC for {len(invalid_date_logic)} records",
                        invalid_date_logic["USUBJID"].tolist() if "USUBJID" in df.columns else []
                    )
            except:
                pass  # Skip if comparison fails
    
    # Check RFXSTDTC <= RFXENDTC
    if "RFXSTDTC" in df.columns and "RFXENDTC" in df.columns:
        both_present = df[df["RFXSTDTC"].notna() & df["RFXENDTC"].notna()]
        if len(both_present) > 0:
            try:
                invalid_date_logic = both_present[both_present["RFXSTDTC"] > both_present["RFXENDTC"]]
                if len(invalid_date_logic) > 0:
                    report.add_critical(
                        "SD1047",
                        f"RFXSTDTC after RFXENDTC for {len(invalid_date_logic)} records",
                        invalid_date_logic["USUBJID"].tolist() if "USUBJID" in df.columns else []
                    )
            except:
                pass
    
    # ========== LAYER 5: BUSINESS RULES ==========
    
    # BR: USUBJID must be unique (one record per subject)
    if "USUBJID" in df.columns:
        duplicate_subjects = df[df.duplicated(subset=["USUBJID"], keep=False)]
        if len(duplicate_subjects) > 0:
            report.add_critical(
                "SD1198",
                f"Duplicate USUBJID found: {len(duplicate_subjects)} records with {len(duplicate_subjects['USUBJID'].unique())} duplicate subjects",
                duplicate_subjects["USUBJID"].unique().tolist()
            )
        else:
            report.add_info(f"✓ All {len(df)} USUBJID values are unique")
    
    # BR: USUBJID format check (should follow pattern STUDYID-SITEID-SUBJID)
    if "USUBJID" in df.columns:
        expected_pattern = r'^[A-Z0-9]+-\d+-\d+-\d+$'
        invalid_usubjid_format = df[~df["USUBJID"].astype(str).str.match(expected_pattern, na=False)]
        if len(invalid_usubjid_format) > 0:
            report.add_warning(
                "BR002",
                f"USUBJID format may not follow standard pattern (STUDYID-SITEID-SUBJID): {len(invalid_usubjid_format)} records",
                invalid_usubjid_format["USUBJID"].tolist()[:5]
            )
    
    # BR: Missing required subject identifiers
    if "USUBJID" in df.columns:
        missing_usubjid = df[df["USUBJID"].isna() | (df["USUBJID"] == "")]
        if len(missing_usubjid) > 0:
            report.add_critical(
                "SD1001",
                f"Missing USUBJID for {len(missing_usubjid)} records",
                []
            )
    
    if "SUBJID" in df.columns:
        missing_subjid = df[df["SUBJID"].isna() | (df["SUBJID"] == "")]
        if len(missing_subjid) > 0:
            report.add_critical(
                "SD1001",
                f"Missing SUBJID for {len(missing_subjid)} records",
                missing_subjid["USUBJID"].tolist() if "USUBJID" in df.columns else []
            )
    
    # BR: Missing critical demographics
    for var in ["SEX", "AGE", "RACE"]:
        if var in df.columns:
            missing = df[df[var].isna() | (df[var] == "")]
            if len(missing) > 0:
                report.add_major(
                    "SD1001",
                    f"Missing {var} for {len(missing)} records ({len(missing)/len(df)*100:.1f}%)",
                    missing["USUBJID"].tolist() if "USUBJID" in df.columns else []
                )
    
    # BR: AGEU must be present when AGE is present
    if "AGE" in df.columns and "AGEU" in df.columns:
        age_without_unit = df[df["AGE"].notna() & df["AGEU"].isna()]
        if len(age_without_unit) > 0:
            report.add_major(
                "SD1012",
                f"AGEU missing when AGE is present: {len(age_without_unit)} records",
                age_without_unit["USUBJID"].tolist() if "USUBJID" in df.columns else []
            )
    
    # BR: ARM must be present when ARMCD is present
    if "ARMCD" in df.columns and "ARM" in df.columns:
        armcd_without_arm = df[df["ARMCD"].notna() & (df["ARMCD"] != "") & (df["ARM"].isna() | (df["ARM"] == ""))]
        if len(armcd_without_arm) > 0:
            report.add_warning(
                "SD1010",
                f"ARM missing when ARMCD is present: {len(armcd_without_arm)} records",
                armcd_without_arm["USUBJID"].tolist() if "USUBJID" in df.columns else []
            )
    
    # BR: DTHDTC should be present when DTHFL='Y'
    if "DTHFL" in df.columns and "DTHDTC" in df.columns:
        death_without_date = df[(df["DTHFL"] == "Y") & (df["DTHDTC"].isna() | (df["DTHDTC"] == ""))]
        if len(death_without_date) > 0:
            report.add_major(
                "BR003",
                f"DTHDTC missing when DTHFL='Y': {len(death_without_date)} records",
                death_without_date["USUBJID"].tolist() if "USUBJID" in df.columns else []
            )
    
    # BR: Age calculation check (if BRTHDTC and RFSTDTC present)
    if all(col in df.columns for col in ["BRTHDTC", "RFSTDTC", "AGE"]):
        age_check = df[df["BRTHDTC"].notna() & df["RFSTDTC"].notna() & df["AGE"].notna()]
        if len(age_check) > 0:
            # This is a simplified check - full implementation would calculate exact age
            report.add_warning(
                "SD2092",
                "AGE calculation should be verified against BRTHDTC and RFSTDTC",
                []
            )
    
    # ========== LAYER 6: DATA QUALITY CHECKS ==========
    
    # Check for ARM/ARMCD = "UNKNOWN"
    if "ARM" in df.columns:
        unknown_arm = df[df["ARM"] == "UNKNOWN"]
        if len(unknown_arm) > 0:
            report.add_warning(
                "DQ001",
                f"ARM is 'UNKNOWN' for all {len(unknown_arm)} records - treatment assignment may be missing",
                []
            )
    
    # Check for missing reference dates
    for ref_var in ["RFSTDTC", "RFENDTC"]:
        if ref_var in df.columns:
            missing_ref = df[df[ref_var].isna() | (df[ref_var] == "")]
            if len(missing_ref) > 0:
                report.add_warning(
                    "DQ002",
                    f"{ref_var} missing for all {len(missing_ref)} records - reference dates are critical for study day calculations",
                    []
                )
    
    # Age distribution check
    if "AGE" in df.columns:
        age_values = df[df["AGE"].notna()]["AGE"]
        if len(age_values) > 0:
            try:
                age_numeric = pd.to_numeric(age_values, errors='coerce')
                report.add_info(f"Age statistics: Mean={age_numeric.mean():.1f}, Min={age_numeric.min():.0f}, Max={age_numeric.max():.0f}, Median={age_numeric.median():.0f}")
                
                # Flag unusual ages
                if age_numeric.min() < 18:
                    report.add_warning("DQ003", f"Subjects under 18 years old found (min age: {age_numeric.min():.0f})", [])
                if age_numeric.max() > 100:
                    report.add_warning("DQ004", f"Subjects over 100 years old found (max age: {age_numeric.max():.0f})", [])
            except:
                pass
    
    # Sex distribution
    if "SEX" in df.columns:
        sex_counts = df["SEX"].value_counts()
        report.add_info(f"Sex distribution: {sex_counts.to_dict()}")
    
    # Race distribution
    if "RACE" in df.columns:
        race_counts = df["RACE"].value_counts()
        report.add_info(f"Race distribution: {race_counts.to_dict()}")
    
    return report, df


def print_validation_report(report, df):
    """Print formatted validation report."""
    
    print("\n" + "="*80)
    print("DM DOMAIN VALIDATION REPORT")
    print("="*80)
    print(f"\nStudy: {STUDY_ID}")
    print(f"Domain: DM (Demographics)")
    print(f"File: {DM_FILE}")
    print(f"Validation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Summary
    summary = report.summary()
    print("\n" + "-"*80)
    print("VALIDATION SUMMARY")
    print("-"*80)
    
    if df is not None:
        print(f"Total Records: {len(df)}")
        print(f"Total Variables: {len(df.columns)}")
    
    print(f"\nCritical Errors: {summary['critical']} ❌")
    print(f"Major Errors: {summary['major']} ⚠️")
    print(f"Minor Errors: {summary['minor']} ⚠️")
    print(f"Warnings: {summary['warnings']} 💡")
    print(f"Total Issues: {summary['total_errors'] + summary['warnings']}")
    
    # Submission readiness
    print("\n" + "-"*80)
    print("SUBMISSION READINESS")
    print("-"*80)
    
    if summary['critical'] == 0 and summary['major'] == 0:
        print("✅ PASS - Dataset is submission-ready")
        print("   (No critical or major errors found)")
    elif summary['critical'] == 0:
        print("⚠️  CONDITIONAL PASS - Dataset has major errors that should be resolved")
        print(f"   ({summary['major']} major errors found)")
    else:
        print("❌ FAIL - Dataset is NOT submission-ready")
        print(f"   ({summary['critical']} critical errors must be fixed)")
    
    # Business rules applied
    print("\n" + "-"*80)
    print("BUSINESS RULES APPLIED")
    print("-"*80)
    print("1. USUBJID uniqueness (one record per subject)")
    print("2. USUBJID format check (STUDYID-SITEID-SUBJID pattern)")
    print("3. Required variable completeness")
    print("4. Controlled terminology compliance (SEX, RACE, ETHNIC, AGEU)")
    print("5. ISO 8601 date format validation")
    print("6. Date logic consistency (start <= end dates)")
    print("7. Age-unit association (AGEU required when AGE present)")
    print("8. Death flag-date association (DTHDTC when DTHFL='Y')")
    print("9. ARM-ARMCD association")
    print("10. Data type validation (numeric AGE)")
    
    # Critical errors
    if report.critical_errors:
        print("\n" + "-"*80)
        print("CRITICAL ERRORS (Must Fix)")
        print("-"*80)
        for i, error in enumerate(report.critical_errors, 1):
            print(f"\n{i}. [{error['rule_id']}] {error['message']}")
            if error['records']:
                print(f"   Affected records: {', '.join(map(str, error['records'][:10]))}")
                if len(error['records']) > 10:
                    print(f"   ... and {len(error['records']) - 10} more")
    
    # Major errors
    if report.major_errors:
        print("\n" + "-"*80)
        print("MAJOR ERRORS (Should Fix)")
        print("-"*80)
        for i, error in enumerate(report.major_errors, 1):
            print(f"\n{i}. [{error['rule_id']}] {error['message']}")
            if error['records']:
                print(f"   Affected records: {', '.join(map(str, error['records'][:10]))}")
                if len(error['records']) > 10:
                    print(f"   ... and {len(error['records']) - 10} more")
    
    # Minor errors
    if report.minor_errors:
        print("\n" + "-"*80)
        print("MINOR ERRORS")
        print("-"*80)
        for i, error in enumerate(report.minor_errors, 1):
            print(f"\n{i}. [{error['rule_id']}] {error['message']}")
            if error['records']:
                print(f"   Affected records: {', '.join(map(str, error['records'][:10]))}")
    
    # Warnings
    if report.warnings:
        print("\n" + "-"*80)
        print("WARNINGS")
        print("-"*80)
        for i, warning in enumerate(report.warnings, 1):
            print(f"\n{i}. [{warning['rule_id']}] {warning['message']}")
            if warning['records']:
                print(f"   Affected records: {', '.join(map(str, warning['records'][:10]))}")
    
    # Info messages
    if report.info:
        print("\n" + "-"*80)
        print("VALIDATION CHECKS PASSED")
        print("-"*80)
        for msg in report.info:
            print(f"  {msg}")
    
    # Recommendations
    print("\n" + "-"*80)
    print("RECOMMENDATIONS FOR DATA CLEANING")
    print("-"*80)
    
    recommendations = []
    
    if summary['critical'] > 0:
        recommendations.append("1. Fix all CRITICAL errors before submission (required)")
    
    if summary['major'] > 0:
        recommendations.append("2. Resolve MAJOR errors to improve data quality")
    
    # Specific recommendations based on errors found
    has_ct_errors = any("SD1091" in e['rule_id'] for e in report.critical_errors + report.major_errors)
    if has_ct_errors:
        recommendations.append("3. Map all values to CDISC controlled terminology")
        recommendations.append("   - Use exact codelist values (e.g., 'M' not 'Male')")
        recommendations.append("   - Reference SDTM Controlled Terminology 2025-09-26")
    
    has_date_errors = any("SD1025" in e['rule_id'] or "SD1046" in e['rule_id'] for e in report.critical_errors)
    if has_date_errors:
        recommendations.append("4. Convert all dates to ISO 8601 format (YYYY-MM-DD)")
        recommendations.append("   - Use partial dates for missing components (e.g., 2024-01 for unknown day)")
    
    has_missing_data = any("SD1001" in e['rule_id'] for e in report.critical_errors + report.major_errors)
    if has_missing_data:
        recommendations.append("5. Investigate missing required data")
        recommendations.append("   - Query source data for SEX, AGE, RACE values")
        recommendations.append("   - Use 'UNKNOWN' or 'NOT REPORTED' for truly missing data")
    
    if any("UNKNOWN" in w['message'] for w in report.warnings):
        recommendations.append("6. Resolve treatment arm assignments (currently 'UNKNOWN')")
        recommendations.append("   - Link to randomization data or treatment exposure records")
    
    if not recommendations:
        recommendations.append("✅ No critical issues found - dataset is in good shape!")
        recommendations.append("   Consider addressing any warnings to further improve data quality")
    
    for rec in recommendations:
        print(rec)
    
    print("\n" + "="*80)
    print("END OF VALIDATION REPORT")
    print("="*80 + "\n")


if __name__ == "__main__":
    print("Starting DM domain validation...")
    print(f"File: {DM_FILE}")
    print(f"Study: {STUDY_ID}\n")
    
    report, df = validate_dm_domain(DM_FILE)
    print_validation_report(report, df)
    
    # Return exit code based on validation result
    summary = report.summary()
    if summary['critical'] > 0:
        exit(1)  # Critical errors
    elif summary['major'] > 0:
        exit(2)  # Major errors
    else:
        exit(0)  # Pass

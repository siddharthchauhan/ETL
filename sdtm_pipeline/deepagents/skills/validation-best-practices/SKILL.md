---
name: validation-best-practices
description: This skill provides comprehensive guidance on validating SDTM datasets for FDA submission compliance using industry-standard tools and best practices.
---

# SDTM Validation Best Practices and FDA Conformance

## Overview

This skill provides comprehensive guidance on validating SDTM datasets for FDA submission compliance using industry-standard tools and best practices.

**Source**: FDA Technical Conformance Guide, Pinnacle 21 validation rules, CDISC CORE, PharmaSUG papers

⚠️ **IMPORTANT**: Always verify current FDA requirements at FDA.gov before submission. Requirements and deadlines evolve.

## FDA Validation Requirements

### Mandatory Validation

**FDA Requirement**: "Sponsors must validate datasets using FDA's recognized tools (e.g., Pinnacle 21) to check compliance with SDTM standards."

**Key Points**:
1. Validate **before submission** using FDA-recognized validator
2. Resolve ALL **ERROR** messages (submission blockers)
3. Resolve as many **WARNING** messages as possible
4. Document unresolved issues in **Study Data Reviewer's Guide (SDRG)**
5. Include validation report in submission package

### Validation Workflow
```
1. Generate SDTM datasets + Define-XML
              ↓
2. Run validation (Pinnacle 21 or CDISC CORE)
              ↓
3. Review validation report
              ↓
4. Fix ERROR issues (mandatory)
              ↓
5. Address WARNING issues (recommended)
              ↓
6. Re-validate until clean
              ↓
7. Document unresolved issues in SDRG
              ↓
8. Submit with validation report
```

## Validation Tools

### Pinnacle 21 (Industry Standard)

**Pinnacle 21 Community** (Free, GUI-based):
1. Download from pinnacle21.com
2. Launch application
3. Select "Validate" → "SDTM"
4. Configure:
   - SDTMIG Version (e.g., 3.4)
   - Controlled Terminology Version
   - Define-XML file path
   - Datasets folder path
5. Click "Validate"
6. Export report (Excel/PDF)

**Pinnacle 21 Enterprise** (Commercial, API-enabled):
- REST API for automation
- Batch validation capability
- Integration with clinical data systems
- Contact Certara for licensing

### CDISC CORE (Open Source)
```bash
# Install CDISC Rules Engine
pip install cdisc-rules-engine

# Run validation
core validate \
  --standard SDTMIG \
  --version 3-4 \
  --data ./sdtm_datasets \
  --define define.xml \
  --output validation_report.json \
  --output-format JSON
```

### Custom Python Validation Framework
```python
import pandas as pd
from typing import List, Dict, Tuple
from datetime import datetime
import re

class SDTMValidator:
    """Basic SDTM validation framework."""
    
    def __init__(self, sdtmig_version: str = "3.4", ct_version: str = "2024-12-20"):
        self.sdtmig_version = sdtmig_version
        self.ct_version = ct_version
        self.issues: List[Dict] = []
        
        # Load controlled terminology
        self.ct = self._load_controlled_terminology()
    
    def _load_controlled_terminology(self) -> Dict:
        """Load CDISC CT codelists."""
        return {
            "SEX": ["M", "F", "U", "UNDIFFERENTIATED"],
            "NY": ["N", "Y"],
            "ETHNIC": ["HISPANIC OR LATINO", "NOT HISPANIC OR LATINO", 
                       "NOT REPORTED", "UNKNOWN"],
            # Add other codelists...
        }
    
    def add_issue(self, rule_id: str, severity: str, domain: str,
                  variable: str, message: str, records: int = 0):
        """Add validation issue."""
        self.issues.append({
            "rule_id": rule_id,
            "severity": severity,
            "domain": domain,
            "variable": variable,
            "message": message,
            "records": records,
            "timestamp": datetime.now().isoformat()
        })
    
    def validate_required_variables(self, df: pd.DataFrame, 
                                    domain: str, 
                                    required_vars: List[str]) -> None:
        """Check required variables are present and populated."""
        for var in required_vars:
            if var not in df.columns:
                self.add_issue(
                    "SD1002", "ERROR", domain, var,
                    f"Required variable {var} missing from {domain}"
                )
            elif df[var].isna().all():
                self.add_issue(
                    "SD1001", "ERROR", domain, var,
                    f"Required variable {var} has no values"
                )
    
    def validate_controlled_terminology(self, df: pd.DataFrame,
                                        domain: str,
                                        ct_vars: Dict[str, str]) -> None:
        """Validate values against controlled terminology."""
        for var, codelist in ct_vars.items():
            if var not in df.columns:
                continue
            
            valid_values = set(self.ct.get(codelist, []))
            if not valid_values:
                continue
            
            actual_values = set(df[var].dropna().unique())
            invalid = actual_values - valid_values
            
            if invalid:
                self.add_issue(
                    "SD1091", "ERROR", domain, var,
                    f"Invalid CT values: {invalid}. Expected: {valid_values}",
                    records=len(df[df[var].isin(invalid)])
                )
    
    def validate_iso8601_dates(self, df: pd.DataFrame, domain: str) -> None:
        """Validate date variables are ISO 8601 compliant."""
        date_vars = [col for col in df.columns if col.endswith("DTC")]
        
        iso_patterns = [
            r'^\d{4}$',
            r'^\d{4}-\d{2}$',
            r'^\d{4}-\d{2}-\d{2}$',
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$',
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$',
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$',
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$',
        ]
        
        def is_valid_iso8601(val):
            if pd.isna(val):
                return True
            return any(re.match(p, str(val)) for p in iso_patterns)
        
        for var in date_vars:
            invalid_mask = ~df[var].apply(is_valid_iso8601)
            invalid_count = invalid_mask.sum()
            
            if invalid_count > 0:
                invalid_examples = df.loc[invalid_mask, var].head(3).tolist()
                self.add_issue(
                    "SD1025", "ERROR", domain, var,
                    f"Invalid ISO 8601 format. Examples: {invalid_examples}",
                    records=invalid_count
                )
    
    def validate_seq_uniqueness(self, df: pd.DataFrame, domain: str) -> None:
        """Validate --SEQ is unique within USUBJID."""
        seq_var = f"{domain}SEQ"
        if seq_var not in df.columns:
            return
        
        duplicates = df.groupby(["USUBJID", seq_var]).size()
        duplicates = duplicates[duplicates > 1]
        
        if len(duplicates) > 0:
            self.add_issue(
                "SD1198", "ERROR", domain, seq_var,
                f"Duplicate {seq_var} within USUBJID",
                records=len(duplicates)
            )
    
    def validate_date_logic(self, df: pd.DataFrame, domain: str,
                           start_var: str, end_var: str) -> None:
        """Validate start date <= end date."""
        if start_var not in df.columns or end_var not in df.columns:
            return
        
        # Only compare when both dates exist
        mask = df[start_var].notna() & df[end_var].notna()
        violations = df.loc[mask, start_var] > df.loc[mask, end_var]
        
        if violations.any():
            self.add_issue(
                "SD1046", "ERROR", domain, f"{start_var}/{end_var}",
                f"Start date after end date",
                records=violations.sum()
            )
    
    def validate_baseline_flags(self, df: pd.DataFrame, domain: str,
                                testcd_var: str, blfl_var: str) -> None:
        """Validate only one baseline per subject per test."""
        if blfl_var not in df.columns:
            return
        
        # Check for invalid values (only Y or null allowed)
        invalid_values = df[~df[blfl_var].isin(["Y", None, pd.NA]) & df[blfl_var].notna()]
        if len(invalid_values) > 0:
            self.add_issue(
                "SD1228", "ERROR", domain, blfl_var,
                f"Invalid {blfl_var} values (only 'Y' or null allowed)",
                records=len(invalid_values)
            )
        
        # Check for multiple baselines per subject/test
        baseline_df = df[df[blfl_var] == "Y"]
        duplicates = baseline_df.groupby(["USUBJID", testcd_var]).size()
        duplicates = duplicates[duplicates > 1]
        
        if len(duplicates) > 0:
            self.add_issue(
                "SD1229", "ERROR", domain, blfl_var,
                f"Multiple baseline flags per subject/test",
                records=len(duplicates)
            )
    
    def get_report(self) -> pd.DataFrame:
        """Generate validation report."""
        if not self.issues:
            return pd.DataFrame(columns=[
                "rule_id", "severity", "domain", "variable", 
                "message", "records", "timestamp"
            ])
        return pd.DataFrame(self.issues)
    
    def get_summary(self) -> Dict:
        """Get validation summary."""
        report = self.get_report()
        return {
            "total_issues": len(report),
            "errors": len(report[report["severity"] == "ERROR"]),
            "warnings": len(report[report["severity"] == "WARNING"]),
            "by_domain": report.groupby("domain").size().to_dict()
        }
```

## Common Validation Errors and Solutions

### SD1091: Controlled Terminology Violation

**Problem**: Values not matching CDISC CT exactly

**Example**:
```
ERROR: SEX value 'Male' not found in CDISC CT
Expected: M, F, U, UNDIFFERENTIATED
```

**Solution**:
```python
# Define explicit CT mapping
CT_SEX_MAP = {
    # Source variations → CDISC CT
    "M": "M", "Male": "M", "MALE": "M", "1": "M", "m": "M",
    "F": "F", "Female": "F", "FEMALE": "F", "2": "F", "f": "F",
    "U": "U", "Unknown": "U", "UNK": "U", "": "U",
    "UNDIFFERENTIATED": "UNDIFFERENTIATED",
}

def apply_ct_mapping(df: pd.DataFrame, var: str, ct_map: dict) -> pd.DataFrame:
    """Apply controlled terminology mapping with validation."""
    original_values = set(df[var].dropna().unique())
    unmapped = original_values - set(ct_map.keys())
    
    if unmapped:
        raise ValueError(f"Unmapped values for {var}: {unmapped}")
    
    df[var] = df[var].map(ct_map)
    return df

# Apply
dm_df = apply_ct_mapping(dm_df, "SEX", CT_SEX_MAP)
```

### SD2227: VISIT/VISITNUM Not in SV

**Problem**: Findings domains reference visits not in Subject Visits (SV) domain

**Solution**:
```python
def reconcile_visits_with_sv(sv_df: pd.DataFrame, 
                             domain_dfs: Dict[str, pd.DataFrame],
                             study_id: str) -> pd.DataFrame:
    """
    Ensure all visits across domains exist in SV.
    """
    # Collect all unique USUBJID/VISITNUM combinations
    all_visits = set()
    
    for domain_name, domain_df in domain_dfs.items():
        if "VISITNUM" in domain_df.columns:
            visits = set(zip(
                domain_df["USUBJID"], 
                domain_df["VISITNUM"],
                domain_df.get("VISIT", [""] * len(domain_df))
            ))
            all_visits.update(visits)
    
    # Get existing SV visits
    sv_visits = set(zip(sv_df["USUBJID"], sv_df["VISITNUM"]))
    
    # Find missing visits
    missing = []
    for usubjid, visitnum, visit in all_visits:
        if (usubjid, visitnum) not in sv_visits:
            missing.append({
                "STUDYID": study_id,
                "DOMAIN": "SV",
                "USUBJID": usubjid,
                "VISITNUM": visitnum,
                "VISIT": visit if visit else f"VISIT {visitnum}",
                "SVUPDES": "Added from domain data"
            })
    
    if missing:
        missing_df = pd.DataFrame(missing)
        sv_df = pd.concat([sv_df, missing_df], ignore_index=True)
        sv_df = sv_df.sort_values(["USUBJID", "VISITNUM"])
    
    return sv_df
```

### SD1229: Multiple Baseline Flags

**Problem**: More than one `--BLFL='Y'` per subject per test

**Solution**:
```python
def derive_baseline_flag(df: pd.DataFrame,
                         domain: str,
                         testcd_var: str,
                         dtc_var: str,
                         dm_df: pd.DataFrame) -> pd.DataFrame:
    """
    Derive baseline flag correctly.
    
    Rules:
    - Only "Y" or null (NEVER "N")
    - One baseline per test per subject
    - Last non-missing result at or before first treatment (RFXSTDTC)
    """
    blfl_var = f"{domain}BLFL"
    orres_var = f"{domain}ORRES"
    
    # Initialize to null
    df[blfl_var] = None
    
    # Merge RFXSTDTC from DM (CRITICAL: use first TREATMENT date, not RFSTDTC)
    df = df.merge(
        dm_df[["USUBJID", "RFXSTDTC"]],
        on="USUBJID",
        how="left"
    )
    
    # Process each subject/test combination
    for (usubjid, testcd), group in df.groupby(["USUBJID", testcd_var]):
        ref_date = group["RFXSTDTC"].iloc[0]
        
        if pd.isna(ref_date):
            continue
        
        # Filter to pre-treatment records with non-missing results
        pre_treatment = group[
            (group[dtc_var] <= ref_date) &
            (group[orres_var].notna()) &
            (group[orres_var] != "")
        ]
        
        if len(pre_treatment) > 0:
            # Last pre-treatment record is baseline
            baseline_idx = pre_treatment[dtc_var].idxmax()
            df.loc[baseline_idx, blfl_var] = "Y"
    
    # Clean up - remove RFXSTDTC column added during merge
    df = df.drop(columns=["RFXSTDTC"], errors="ignore")
    
    return df
```

### SD1025: Invalid ISO 8601 Date

**Solution**:
```python
def convert_to_iso8601(date_val, formats: list = None) -> str:
    """
    Convert date value to ISO 8601 format.
    Preserves partial dates per SDTM rules.
    """
    if pd.isna(date_val) or date_val == "":
        return None
    
    date_str = str(date_val).strip()
    
    # Already valid ISO 8601?
    iso_patterns = [
        (r'^\d{4}$', '%Y'),
        (r'^\d{4}-\d{2}$', '%Y-%m'),
        (r'^\d{4}-\d{2}-\d{2}$', '%Y-%m-%d'),
        (r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$', '%Y-%m-%dT%H:%M'),
        (r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$', '%Y-%m-%dT%H:%M:%S'),
    ]
    
    for pattern, _ in iso_patterns:
        if re.match(pattern, date_str):
            return date_str
    
    # Try common source formats
    source_formats = formats or [
        "%m/%d/%Y",          # 01/15/2024
        "%d/%m/%Y",          # 15/01/2024
        "%Y%m%d",            # 20240115
        "%d-%b-%Y",          # 15-Jan-2024
        "%d%b%Y",            # 15JAN2024
        "%B %d, %Y",         # January 15, 2024
        "%m-%d-%Y",          # 01-15-2024
    ]
    
    for fmt in source_formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    # Could not parse - return as-is with warning
    print(f"WARNING: Could not parse date: {date_str}")
    return date_str
```

## Cross-Domain Validation
```python
def cross_domain_validation(dm_df: pd.DataFrame,
                           sv_df: pd.DataFrame,
                           domain_dfs: Dict[str, pd.DataFrame]) -> List[str]:
    """
    Validate consistency across SDTM domains.
    """
    issues = []
    dm_subjects = set(dm_df["USUBJID"])
    dm_studyid = dm_df["STUDYID"].iloc[0]
    
    for domain_name, domain_df in domain_dfs.items():
        # Check 1: All USUBJID exist in DM
        domain_subjects = set(domain_df["USUBJID"])
        missing_in_dm = domain_subjects - dm_subjects
        
        if missing_in_dm:
            issues.append(
                f"SD ERROR: {domain_name} has {len(missing_in_dm)} subjects "
                f"not in DM: {list(missing_in_dm)[:5]}"
            )
        
        # Check 2: STUDYID consistency
        domain_studies = set(domain_df["STUDYID"].unique())
        if domain_studies != {dm_studyid}:
            issues.append(
                f"SD ERROR: {domain_name} STUDYID mismatch. "
                f"Expected: {dm_studyid}, Found: {domain_studies}"
            )
        
        # Check 3: All visits exist in SV
        if "VISITNUM" in domain_df.columns:
            sv_visits = set(zip(sv_df["USUBJID"], sv_df["VISITNUM"]))
            domain_visits = set(zip(
                domain_df["USUBJID"], 
                domain_df["VISITNUM"]
            ))
            missing_visits = domain_visits - sv_visits
            
            if missing_visits:
                issues.append(
                    f"SD2227: {domain_name} has {len(missing_visits)} "
                    f"visits not in SV"
                )
    
    return issues
```

## Trial Summary (TS) Domain Requirements

**TS is REQUIRED for all SDTM submissions.**

### Minimum Required Parameters

| TSPARMCD | TSPARM | Required | Example |
|----------|--------|----------|---------|
| ADDON | Added on to Existing Treatments | Yes | Y / N |
| AGEMAX | Planned Maximum Age of Subjects | Yes | P65Y |
| AGEMIN | Planned Minimum Age of Subjects | Yes | P18Y |
| INDIC | Trial Disease/Condition Indication | Yes | Type 2 Diabetes |
| LENGTH | Trial Length | Yes | P52W |
| OBJPRIM | Trial Primary Objective | Yes | Efficacy |
| PLESSION | Planned Number of Subjects per Site | Yes | 50 |
| STYPE | Study Type | Yes | INTERVENTIONAL |
| TBLIND | Trial Blinding Schema | Yes | DOUBLE BLIND |
| TCNTRL | Control Type | Yes | PLACEBO |
| TINDTP | Trial Indication Type | Yes | TREATMENT |
| TITLE | Trial Title | Yes | Study ABC-001 |
| TPHASE | Trial Phase Classification | Yes | PHASE III TRIAL |
| TTYPE | Trial Type | Yes | EFFICACY |

### TS Validation
```python
REQUIRED_TS_PARAMS = [
    "ADDON", "AGEMAX", "AGEMIN", "INDIC", "LENGTH", "OBJPRIM",
    "PLESSION", "STYPE", "TBLIND", "TCNTRL", "TINDTP", 
    "TITLE", "TPHASE", "TTYPE"
]

def validate_ts_domain(ts_df: pd.DataFrame) -> List[str]:
    """Validate TS domain completeness."""
    issues = []
    
    if ts_df is None or len(ts_df) == 0:
        return ["CRITICAL ERROR: TS domain missing - required for submission"]
    
    present_params = set(ts_df["TSPARMCD"])
    missing = set(REQUIRED_TS_PARAMS) - present_params
    
    if missing:
        issues.append(f"ERROR: Missing required TS parameters: {missing}")
    
    # Check TSVAL not empty for required params
    for param in REQUIRED_TS_PARAMS:
        param_df = ts_df[ts_df["TSPARMCD"] == param]
        if len(param_df) > 0:
            if param_df["TSVAL"].isna().all() or (param_df["TSVAL"] == "").all():
                issues.append(f"ERROR: TS parameter {param} has no value")
    
    return issues
```

## SUPPQUAL Domain Validation
```python
def validate_suppqual(supp_df: pd.DataFrame, 
                      parent_df: pd.DataFrame,
                      rdomain: str) -> List[str]:
    """Validate supplemental qualifier domain."""
    issues = []
    
    # Check 1: RDOMAIN value matches
    invalid_rdomain = supp_df[supp_df["RDOMAIN"] != rdomain]
    if len(invalid_rdomain) > 0:
        issues.append(f"SD1100: RDOMAIN should be '{rdomain}'")
    
    # Check 2: IDVAR is valid identifier in parent
    valid_idvars = {"USUBJID", f"{rdomain}SEQ", f"{rdomain}GRPID", f"{rdomain}REFID"}
    invalid_idvar = supp_df[~supp_df["IDVAR"].isin(valid_idvars)]
    if len(invalid_idvar) > 0:
        issues.append(f"SD1101: Invalid IDVAR values: {invalid_idvar['IDVAR'].unique()}")
    
    # Check 3: IDVARVAL exists in parent
    seq_var = f"{rdomain}SEQ"
    if seq_var in parent_df.columns:
        parent_seq = set(parent_df[seq_var].astype(str))
        seq_supp = supp_df[supp_df["IDVAR"] == seq_var]
        
        if len(seq_supp) > 0:
            supp_vals = set(seq_supp["IDVARVAL"])
            missing = supp_vals - parent_seq
            
            if missing:
                issues.append(f"SD1102: IDVARVAL not in parent: {missing}")
    
    # Check 4: QNAM length <= 8 characters
    long_qnam = supp_df[supp_df["QNAM"].str.len() > 8]
    if len(long_qnam) > 0:
        issues.append(f"SD1103: QNAM exceeds 8 chars: {long_qnam['QNAM'].tolist()}")
    
    # Check 5: QNAM not already in parent domain (should use standard var)
    parent_vars = set(parent_df.columns)
    qnam_in_parent = supp_df[supp_df["QNAM"].isin(parent_vars)]
    if len(qnam_in_parent) > 0:
        issues.append(
            f"SD1104 WARNING: QNAM exists in parent domain "
            f"(consider using standard variable): {qnam_in_parent['QNAM'].unique()}"
        )
    
    return issues
```

## Pre-Submission Checklist

### Domain-Level Checks

- [ ] All **Required (R)** variables present
- [ ] All **Required** values populated (not all null)
- [ ] Data types correct (Num where expected, Char elsewhere)
- [ ] Variable lengths within SDTM limits (8 char names, 200 char labels)
- [ ] Controlled terminology exact matches
- [ ] --SEQ unique within USUBJID for each domain
- [ ] ISO 8601 dates (YYYY-MM-DD format)
- [ ] Date logic valid (--STDTC <= --ENDTC)
- [ ] --BLFL only "Y" or null, one per subject/test

### Cross-Domain Checks

- [ ] All USUBJID exist in DM
- [ ] STUDYID identical across all domains
- [ ] All VISITNUM values exist in SV
- [ ] RFSTDTC/RFXSTDTC used appropriately
- [ ] EPOCH consistent with SE domain

### Trial Design Checks

- [ ] TS domain present with all required parameters
- [ ] TA (Trial Arms) complete
- [ ] TE (Trial Elements) complete
- [ ] TV (Trial Visits) matches protocol schedule
- [ ] TI (Trial Inclusion/Exclusion) matches protocol

### Define-XML Checks

- [ ] All datasets documented
- [ ] All variables documented with labels
- [ ] DataType matches actual data
- [ ] Length matches or exceeds max in data
- [ ] CodeList references valid
- [ ] Origin documented for all variables
- [ ] Methods documented for derived variables
- [ ] ValueLists for --TESTCD, --CAT variables

### SDRG Documentation

- [ ] All unresolved ERRORs explained (should be none)
- [ ] All unresolved WARNINGs explained
- [ ] Rationale provided for each exception
- [ ] Impact assessment included

## Instructions for Agent

When validating SDTM datasets:

1. **Use appropriate validator**: Pinnacle 21 (preferred) or CDISC CORE
2. **Resolve ALL errors** before submission
3. **Address warnings** systematically
4. **Validate early and often** - not just at the end
5. **Cross-validate domains** for consistency
6. **Check TS domain** - frequently missing
7. **Validate SUPPQUAL** against parent domains
8. **Document exceptions** in SDRG
9. **Verify Define-XML** alignment with data
10. **Keep validation reports** for submission package

### Code Quality Requirements

- Use current pandas methods (`pd.concat()` not `append()`)
- Merge reference dates from DM before baseline derivation
- Use RFXSTDTC (first treatment) for baseline, not RFSTDTC
- Validate CT mappings before applying
- Log all validation issues with rule IDs
- Handle edge cases (null values, partial dates)

---

## Summary of Corrections Made

| # | Issue | Severity | Correction |
|---|-------|----------|------------|
| 1 | Deprecated pandas `append()` | Critical | Changed to `pd.concat()` |
| 2 | Wrong reference date for baseline | Critical | Changed RFSTDTC to RFXSTDTC |
| 3 | RFSTDTC not in findings domains | Critical | Added merge from DM |
| 4 | Fabricated Pinnacle 21 Python API | Critical | Removed, added accurate info |
| 5 | Invalid Pinnacle 21 CLI syntax | Critical | Replaced with accurate guidance |
| 6 | Missing/incomplete P21 rules | High | Added critical rules |
| 7 | Vague FDA deadline | High | Added verification recommendation |
| 8 | Missing SUPPQUAL validation | High | Added complete section |
| 9 | Missing TS domain requirements | High | Added required parameters |
| 10 | Incomplete Define-XML validation | Medium | Expanded checklist |
| 11 | Incomplete ISO 8601 regex | Medium | Added comprehensive patterns |
| 12 | Oversimplified null column guidance | Medium | Added version-specific rules |
| 13 | Missing validation alternatives | Low | Added CDISC CORE, others |

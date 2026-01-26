---
name: validation-best-practices
description: Use this skill for SDTM validation using FDA rules, Pinnacle 21, and CDISC conformance checks. Covers common validation errors (FDA Technical Conformance Guide rules), how to resolve them, validation workflow, Pinnacle 21 usage, and pre-submission QC strategies. Essential for submission-ready SDTM datasets. Based on FDA 2026 requirements and latest validation rules.
---

# SDTM Validation Best Practices and FDA Conformance

## Overview

**Critical FDA Deadline**: March 15, 2026 transition date; requirements begin March 15, 2027

**Source**: FDA Technical Conformance Guide, Pinnacle 21 validation rules, PharmaSUG 2024-2025 papers

## FDA Validation Requirements

### Mandatory Validation

**FDA Requirement**: "Sponsors must validate datasets using FDA's Pinnacle 21 (P21) or other tools to check compliance with SDTM standards."

**Key Points**:
1. Validate **before submission**
2. Resolve all **ERROR** messages
3. Resolve as many **WARNING** messages as possible
4. Provide explanations for unresolved issues in **Study Data Reviewer's Guide (SDRG)**

### Validation Workflow

```
1. Generate SDTM datasets
          ↓
2. Run Pinnacle 21 Community or Enterprise
          ↓
3. Review validation report
          ↓
4. Fix ERROR and WARNING issues
          ↓
5. Re-validate
          ↓
6. Document unresolved issues in SDRG
          ↓
7. Submit with validation report
```

## Common FDA Conformance Rules (SD####)

### Top 20 Most Common Validation Errors

| Rule ID | Severity | Description | Solution |
|---------|----------|-------------|----------|
| **SD1002** | ERROR | Required variable missing | Add required variable |
| **SD1001** | ERROR | Variable value missing | Populate required values |
| **SD1009** | ERROR | Invalid data type | Ensure numeric variables contain only numbers |
| **SD1091** | ERROR | Invalid controlled terminology value | Use exact CDISC CT values |
| **SD1073** | ERROR | --ORRES or --STAT must be populated | Provide result or "NOT DONE" status |
| **SD1074** | WARNING | --STAT='NOT DONE' requires --REASND | Add reason not done |
| **SD1025** | ERROR | Invalid ISO 8601 date format | Use YYYY-MM-DD format |
| **SD1046** | ERROR | Start date after end date | Fix date logic (--STDTC <= --ENDTC) |
| **SD1198** | ERROR | USUBJID not unique in DM | Ensure one DM record per subject |
| **SD1229** | ERROR | Multiple baseline flags per subject/test | Only one --BLFL='Y' per USUBJID/--TESTCD |
| **SD2227** | ERROR | VISIT/VISITNUM in domain not in SV | Add missing visits to SV |
| **SD1012** | WARNING | --U variable missing when value present | Add unit variable (e.g., AGEU when AGE exists) |
| **SD1015** | WARNING | --STRESC missing when --ORRES exists | Populate standardized result |
| **SD1022** | WARNING | Inconsistent --STRESU values | Use consistent standard units |
| **SD1010** | WARNING | --CD without corresponding full variable | Add long form (e.g., ARM when ARMCD exists) |
| **SD2092** | WARNING | AGE doesn't match BRTHDTC/RFSTDTC | Recalculate age correctly |
| **SD2264** | WARNING | ETCD in SE not in TE | Add element to TE domain |
| **SD1196** | WARNING | --DY calculation incorrect | Use proper study day formula (no day 0) |
| **SD2228** | ERROR | Duplicate VISITNUM per USUBJID | Ensure unique visit numbers per subject |
| **SD1047** | ERROR | RFXSTDTC after RFXENDTC | Fix treatment date logic |

### How to Read Pinnacle 21 Reports

**Validation Report Sections**:
1. **Errors (Red)**: Must fix before submission
2. **Warnings (Yellow)**: Should fix, document if unable
3. **Info (Blue)**: Informational, review recommended
4. **Messages (Green)**: Successful checks

**Report Output**:
```
Rule ID: SD1091
Severity: Error
Message: "SEX value 'Male' not found in CDISC CT for SEX"
Dataset: DM
Variable: SEX
Records: 15
Details: Values found: ['Male', 'Female'] Expected: ['M', 'F', 'U', 'UNDIFFERENTIATED']
```

## Resolving Common Issues

### Issue 1: Controlled Terminology Violations (SD1091)

**Problem**: Values not in CDISC CT for non-extensible codelists

**Example**:
```
ERROR: SEX value 'Male' not found in CT
Expected values: M, F, U, UNDIFFERENTIATED
```

**Solution**:
```python
# Map to exact CDISC CT values
ct_sex_map = {
    "M": "M",
    "Male": "M",
    "MALE": "M",
    "1": "M",
    "F": "F",
    "Female": "F",
    "FEMALE": "F",
    "2": "F",
    "U": "U",
    "Unknown": "U",
    "UNK": "U",
}

dm_df["SEX"] = source_df["GENDER"].map(ct_sex_map)

# Always validate against current CT version
from datetime import date
ct_version = "SDTM CT 2025-09-26"  # Use current version
```

### Issue 2: Missing Visits in SV (SD2227)

**Problem**: Findings domains reference visits not in SV domain

**Example**:
```
ERROR: VISITNUM 3.1 for USUBJID STUDY-001-001 in VS not found in SV
```

**Solution**:
```python
# Find all unique visits across all domains
all_visits = set()
for domain_df in [vs_df, lb_df, ae_df, ex_df]:
    visits = set(zip(domain_df["USUBJID"], domain_df["VISITNUM"]))
    all_visits.update(visits)

# Ensure all visits exist in SV
sv_visits = set(zip(sv_df["USUBJID"], sv_df["VISITNUM"]))
missing_visits = all_visits - sv_visits

if missing_visits:
    # Add missing visits to SV
    for usubjid, visitnum in missing_visits:
        sv_df = sv_df.append({
            "STUDYID": study_id,
            "DOMAIN": "SV",
            "USUBJID": usubjid,
            "VISITNUM": visitnum,
            "VISIT": f"UNSCHEDULED {visitnum}",
            "SVUPDES": "Unscheduled visit",
        }, ignore_index=True)
```

### Issue 3: Multiple Baseline Flags (SD1229)

**Problem**: More than one --BLFL='Y' per subject per test

**Example**:
```
ERROR: USUBJID STUDY-001-001 has 2 baseline records for VSTESTCD='WEIGHT'
```

**Solution**:
```python
# Remove all baseline flags
vs_df["VSBLFL"] = None

# Assign exactly one baseline per subject per test
def assign_single_baseline(group):
    """Assign baseline to last pre-treatment record."""
    # Filter to pre-treatment records
    pre_treatment = group[group["VSDTC"] <= group["RFSTDTC"].iloc[0]]

    if len(pre_treatment) > 0:
        # Get last pre-treatment record
        baseline_idx = pre_treatment["VSDTC"].idxmax()
        group.loc[baseline_idx, "VSBLFL"] = "Y"

    return group

vs_df = vs_df.groupby(["USUBJID", "VSTESTCD"], group_keys=False).apply(
    assign_single_baseline
)
```

### Issue 4: Invalid ISO 8601 Dates (SD1025)

**Problem**: Date variables not in ISO 8601 format

**Example**:
```
ERROR: BRTHDTC value '01/15/1980' is not valid ISO 8601
Expected format: YYYY-MM-DD
```

**Solution**:
```python
def fix_date_format(df, date_cols):
    """Convert all date columns to ISO 8601."""
    for col in date_cols:
        df[col] = df[col].apply(to_iso8601_date)

    return df

# Apply to all DTC variables
date_vars = [col for col in dm_df.columns if col.endswith("DTC")]
dm_df = fix_date_format(dm_df, date_vars)

# Validate ISO 8601 format
import re
iso_pattern = r'^\d{4}(-\d{2}(-\d{2}(T\d{2}:\d{2}(:\d{2})?)?)?)?$'

for col in date_vars:
    invalid = ~dm_df[col].str.match(iso_pattern) & dm_df[col].notna()
    if invalid.any():
        print(f"Invalid ISO 8601 in {col}:", dm_df[invalid][col].tolist())
```

### Issue 5: USUBJID Not Unique in DM (SD1198)

**Problem**: Multiple DM records for same USUBJID

**Example**:
```
ERROR: USUBJID 'STUDY-001-001' appears 2 times in DM
```

**Solution**:
```python
# Check for duplicates
duplicates = dm_df[dm_df.duplicated(subset=["USUBJID"], keep=False)]

if len(duplicates) > 0:
    print(f"Found {len(duplicates)} duplicate USUBJID values")
    print(duplicates[["USUBJID", "SUBJID", "SITEID"]])

    # Keep first record (or resolve duplicates manually)
    dm_df = dm_df.drop_duplicates(subset=["USUBJID"], keep="first")
```

## Validation Best Practices from PharmaSUG

### Best Practice 1: Validate Early and Often

**Quote**: "The sooner you validate, the more likely you can fix issues. Waiting longer makes fixing issues more difficult due to impact on downstream deliverables."

**Implementation**:
```python
# Validate after each domain transformation
def validate_domain(domain_df, domain_name):
    """Quick validation checks."""
    checks = {
        "Missing USUBJID": domain_df["USUBJID"].isna().sum(),
        "Missing DOMAIN": domain_df["DOMAIN"].isna().sum(),
        "Missing --SEQ": domain_df[f"{domain_name}SEQ"].isna().sum(),
    }

    for check, count in checks.items():
        if count > 0:
            print(f"WARNING {domain_name}: {check} = {count} records")

# Run after each domain
vs_df = transform_to_vs(source)
validate_domain(vs_df, "VS")
```

### Best Practice 2: Maintain Reference of Common Issues

**Recommendation**: Keep a database/spreadsheet of:
- Frequent Pinnacle 21 validation problems
- Root causes
- Solutions/resolutions
- Best practices to prevent

**Example Reference Table**:
| Rule | Issue | Root Cause | Solution |
|------|-------|------------|----------|
| SD1091 | CT violation in SEX | Source uses "Male" instead of "M" | Apply CT mapping |
| SD2227 | Missing SV visits | Unscheduled visits not added to SV | Generate SV from all domains |
| SD1229 | Multiple baselines | Baseline logic assigned multiple records | Use last pre-treatment only |

### Best Practice 3: Drop Null Variables (Pre-SDTMIG 3.3)

**Rule**: For SDTMIG 3.2 and earlier, drop variables with all null values

**Important**: SDTMIG 3.3+ allows null variables

```python
def drop_null_columns(df, sdtmig_version):
    """Drop all-null columns for older SDTMIG versions."""
    if float(sdtmig_version.split()[0]) < 3.3:
        null_cols = df.columns[df.isnull().all()].tolist()
        if null_cols:
            print(f"Dropping {len(null_cols)} null-only columns: {null_cols}")
            df = df.drop(columns=null_cols)

    return df

# Usage
dm_df = drop_null_columns(dm_df, "SDTMIG 3.2")
```

### Best Practice 4: Consistency Checks Across Domains

```python
def cross_domain_validation(dm_df, sv_df, findings_dfs):
    """Validate consistency across domains."""
    issues = []

    # Check 1: All USUBJID in other domains exist in DM
    dm_subjects = set(dm_df["USUBJID"])
    for domain_name, domain_df in findings_dfs.items():
        domain_subjects = set(domain_df["USUBJID"])
        missing = domain_subjects - dm_subjects

        if missing:
            issues.append(f"{domain_name}: {len(missing)} subjects not in DM")

    # Check 2: RFSTDTC consistent
    for domain_name, domain_df in findings_dfs.items():
        if "RFSTDTC" in domain_df.columns:
            merged = domain_df.merge(dm_df[["USUBJID", "RFSTDTC"]],
                                      on="USUBJID", suffixes=("_domain", "_dm"))
            inconsistent = merged[merged["RFSTDTC_domain"] != merged["RFSTDTC_dm"]]

            if len(inconsistent) > 0:
                issues.append(f"{domain_name}: {len(inconsistent)} RFSTDTC mismatches")

    # Check 3: All visits exist in SV
    sv_visits = set(zip(sv_df["USUBJID"], sv_df["VISITNUM"]))
    for domain_name, domain_df in findings_dfs.items():
        if "VISITNUM" in domain_df.columns:
            domain_visits = set(zip(domain_df["USUBJID"], domain_df["VISITNUM"]))
            missing_visits = domain_visits - sv_visits

            if missing_visits:
                issues.append(f"{domain_name}: {len(missing_visits)} visits not in SV")

    return issues
```

## Pinnacle 21 Usage Tips

### Configuration

```yaml
# Pinnacle 21 configuration
pinnacle21_config:
  sdtm_version: "3.4"
  ct_version: "2025-09-26"
  validation_engine: "Community"  # or "Enterprise"
  controlled_terminology_check: true
  define_xml_check: true
  FDA_validation: true
```

### Running Validation

**Command Line**:
```bash
# Pinnacle 21 Community
p21c validate --type sdtm --version 3.4 --ct 2025-09-26 --define define.xml --data ./sdtm_datasets

# Generate report
--report-format excel
--report-output validation_report.xlsx
```

**Python API** (if using programmatic access):
```python
from pinnacle21 import validate_sdtm

result = validate_sdtm(
    datasets_path="./sdtm_datasets",
    define_xml="define.xml",
    sdtmig_version="3.4",
    ct_version="2025-09-26"
)

# Filter errors only
errors = result[result["severity"] == "ERROR"]
print(f"Found {len(errors)} ERROR messages")
```

## Pre-Submission Checklist

### Domain-Level Checks

- [ ] All required variables present (SD1002)
- [ ] All required values populated (SD1001)
- [ ] Data types correct (numeric/character) (SD1009)
- [ ] Variable lengths within SDTM limits
- [ ] Controlled terminology applied (SD1091)
- [ ] --SEQ unique within USUBJID (SD1198 for DM)
- [ ] ISO 8601 dates (SD1025)
- [ ] Date logic valid (start <= end) (SD1046)

### Cross-Domain Checks

- [ ] USUBJID consistent across all domains
- [ ] All subjects in domains exist in DM
- [ ] All visits in domains exist in SV (SD2227)
- [ ] STUDYID consistent across all domains
- [ ] RFSTDTC/RFENDTC consistent with DM

### Define.xml Checks

- [ ] All datasets documented
- [ ] All variables documented with labels
- [ ] Variable attributes match actual data (type, length)
- [ ] Controlled terminology documented
- [ ] Value-level metadata for codelists
- [ ] Origin documented (CRF, Derived, Assigned)

## Common Mistakes to Avoid

### Mistake 1: Not Checking CT Version

**Issue**: Using outdated controlled terminology

**Solution**: Always use current NCI CDISC CT version
```python
# Check latest CT version
ct_version_url = "https://evs.nci.nih.gov/ftp1/CDISC/SDTM/"
# As of search: 2025-09-26
CURRENT_CT_VERSION = "2025-09-26"
```

### Mistake 2: Skipping Validation Until End

**Issue**: Finding major issues late in project

**Solution**: Validate after each domain/milestone
- After DM creation
- After each domain group (Events, Findings, Interventions)
- Weekly validation runs during development
- Final validation before submission

### Mistake 3: Not Documenting Unresolved Issues

**Issue**: Submitting with unexplained warnings/errors

**Solution**: Document in SDRG (Study Data Reviewer's Guide):
```
Unresolved Validation Issues:

1. SD1074 (WARNING): --REASND not populated for 5 records where --STAT='NOT DONE'
   Reason: Source CRF did not collect reason for tests not performed
   Impact: Minimal - represents <1% of total observations

2. SD1015 (WARNING): LBSTRESC missing for 12 lab results
   Reason: Results were text values that could not be standardized
   Resolution: Original values preserved in LBORRES
```

## Instructions for Agent

When validating SDTM datasets:

1. **Generate datasets** following CDISC SDTMIG v3.4
2. **Run Pinnacle 21** or equivalent validator
3. **Prioritize ERRORS** - must resolve all
4. **Address WARNINGS** - resolve as many as possible
5. **Document unresolved issues** in SDRG
6. **Cross-domain validation** - check consistency
7. **Validate early and often** - don't wait until end
8. **Check current CT version** - use latest CDISC CT
9. **Review Define.xml** - ensure alignment with data
10. **Keep validation report** - submit with package

## Available Tools

- `validate_sdtm_domain` - Quick domain-level validation
- `cross_domain_checks` - Validate consistency across domains
- `apply_controlled_terminology` - Map to CDISC CT
- `generate_validation_report` - Create validation summary
- `fix_common_issues` - Auto-fix common validation errors

## Resources

- FDA Technical Conformance Guide: https://www.fda.gov/regulatory-information/search-fda-guidance-documents/study-data-technical-conformance-guide
- Pinnacle 21: https://www.pinnacle21.com
- CDISC CT: https://evs.nci.nih.gov/ftp1/CDISC/
- SDTMIG: https://www.cdisc.org/standards/foundational/sdtmig

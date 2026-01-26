---
name: special-purpose-domains
description: Use this skill for Special Purpose SDTM domains (DM, CO, SE, SV). These domains have unique structures unlike the standard observation classes. DM is one-record-per-subject and contains demographics and trial summary info. SV tracks visit data. SE captures actual study elements. CO stores comments. Essential for subject-level data and visit tracking.
---

# Special Purpose Domains Skill (DM, CO, SE, SV)

## Overview

Special Purpose domains have unique structures that don't follow the standard observation class patterns. They are foundational domains that other domains reference.

**Based on**: CDISC SDTMIG v3.4 and SDTM v2.0

## DM - Demographics

**Purpose**: One record per subject containing demographic characteristics and study participation summary.

**Structure**: Horizontal (one record per subject)

### Required Variables

| Variable | Label | Type | Role |
|----------|-------|------|------|
| STUDYID | Study Identifier | Char | Identifier |
| DOMAIN | Domain Abbreviation | Char | Identifier |
| USUBJID | Unique Subject Identifier | Char | Identifier |
| SUBJID | Subject Identifier for the Study | Char | Topic |
| RFSTDTC | Subject Reference Start Date/Time | Char | Record Qualifier |
| RFENDTC | Subject Reference End Date/Time | Char | Record Qualifier |
| SITEID | Study Site Identifier | Char | Record Qualifier |
| BRTHDTC | Date/Time of Birth | Char | Record Qualifier |
| AGE | Age | Num | Record Qualifier |
| AGEU | Age Units | Char | Variable Qualifier |
| SEX | Sex | Char | Record Qualifier |
| RACE | Race | Char | Record Qualifier |
| ETHNIC | Ethnicity | Char | Record Qualifier |
| ARMCD | Planned Arm Code | Char | Synonym Qualifier |
| ARM | Description of Planned Arm | Char | Synonym Qualifier |
| COUNTRY | Country | Char | Record Qualifier |

### Expected/Permissible Variables

| Variable | Label | Description | Controlled Terminology |
|----------|-------|-------------|------------------------|
| RFXSTDTC | Date/Time of First Study Treatment | First dose date | - |
| RFXENDTC | Date/Time of Last Study Treatment | Last dose date | - |
| RFICDTC | Date/Time of Informed Consent | Consent date | - |
| RFPENDTC | Date/Time of End of Participation | Last contact | - |
| DTHDTC | Date/Time of Death | If subject died | - |
| DTHFL | Subject Death Flag | Y if subject died | Y, null |
| ACTARMCD | Actual Arm Code | Actual treatment arm | - |
| ACTARM | Description of Actual Arm | Actual treatment description | - |
| SETCD | Set Code | For multi-arm studies | - |
| INVID | Investigator Identifier | Principal investigator | - |
| INVNAM | Investigator Name | PI name | - |
| DMDTC | Date/Time of Collection | DM collection date | - |
| DMDY | Study Day of Collection | Calculated study day | - |

### Controlled Terminology Values

#### SEX
- M: Male
- F: Female
- U: Unknown
- UNDIFFERENTIATED

#### AGEU (Age Units)
- YEARS
- MONTHS
- WEEKS
- DAYS
- HOURS

#### RACE (Extensible)
- AMERICAN INDIAN OR ALASKA NATIVE
- ASIAN
- BLACK OR AFRICAN AMERICAN
- NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER
- WHITE
- MULTIPLE
- NOT REPORTED
- UNKNOWN

#### ETHNIC
- HISPANIC OR LATINO
- NOT HISPANIC OR LATINO
- NOT REPORTED
- UNKNOWN

### Transformation Example

```python
def transform_to_dm(source_df, study_id):
    """
    Transform demographics source to SDTM DM domain.

    Key rules:
    - One record per subject
    - USUBJID = STUDYID + "-" + SITEID + "-" + SUBJID (common pattern)
    - All dates in ISO 8601 format
    - Apply controlled terminology
    """
    dm = pd.DataFrame()

    # Identifiers
    dm["STUDYID"] = study_id
    dm["DOMAIN"] = "DM"
    dm["SUBJID"] = source_df["SUBJECT_ID"].astype(str)
    dm["SITEID"] = source_df["SITE_ID"].astype(str)

    # Create USUBJID (must match across all domains)
    dm["USUBJID"] = dm["STUDYID"] + "-" + dm["SITEID"] + "-" + dm["SUBJID"]

    # Demographics with CT application
    dm["SEX"] = source_df["GENDER"].map({
        "M": "M", "MALE": "M", "Male": "M",
        "F": "F", "FEMALE": "F", "Female": "F",
        "U": "U", "UNKNOWN": "U"
    }).fillna("U")

    dm["RACE"] = source_df["RACE"].str.upper()
    dm["ETHNIC"] = source_df["ETHNICITY"].map({
        "HISPANIC": "HISPANIC OR LATINO",
        "NON-HISPANIC": "NOT HISPANIC OR LATINO",
        "NOT REPORTED": "NOT REPORTED",
    })

    # Age calculation
    dm["BRTHDTC"] = source_df["BIRTH_DATE"].apply(to_iso8601)

    # Calculate age at enrollment
    dm["AGE"] = calculate_age(
        source_df["BIRTH_DATE"],
        source_df["ENROLLMENT_DATE"]
    )
    dm["AGEU"] = "YEARS"

    # Study participation dates
    dm["RFICDTC"] = source_df["CONSENT_DATE"].apply(to_iso8601)
    dm["RFSTDTC"] = source_df["FIRST_VISIT_DATE"].apply(to_iso8601)
    dm["RFENDTC"] = source_df["LAST_VISIT_DATE"].apply(to_iso8601)
    dm["RFXSTDTC"] = source_df["FIRST_DOSE_DATE"].apply(to_iso8601)
    dm["RFXENDTC"] = source_df["LAST_DOSE_DATE"].apply(to_iso8601)

    # Treatment arms
    dm["ARMCD"] = source_df["PLANNED_ARM_CODE"]
    dm["ARM"] = source_df["PLANNED_ARM_DESC"]
    dm["ACTARMCD"] = source_df["ACTUAL_ARM_CODE"]
    dm["ACTARM"] = source_df["ACTUAL_ARM_DESC"]

    # Geographic
    dm["COUNTRY"] = source_df["COUNTRY_CODE"]

    # Death information
    if "DEATH_DATE" in source_df.columns:
        dm["DTHFL"] = source_df["DEATH_DATE"].notna().map({True: "Y", False: None})
        dm["DTHDTC"] = source_df["DEATH_DATE"].apply(to_iso8601)

    # Set variable order (CDISC standard order)
    column_order = [
        "STUDYID", "DOMAIN", "USUBJID", "SUBJID",
        "RFSTDTC", "RFENDTC", "RFXSTDTC", "RFXENDTC",
        "RFICDTC", "RFPENDTC",
        "DTHDTC", "DTHFL",
        "SITEID", "INVID", "INVNAM",
        "BRTHDTC", "AGE", "AGEU",
        "SEX", "RACE", "ETHNIC",
        "ARMCD", "ARM", "ACTARMCD", "ACTARM",
        "COUNTRY", "DMDTC", "DMDY"
    ]

    # Reorder, keeping only columns that exist
    dm = dm[[col for col in column_order if col in dm.columns]]

    return dm

def calculate_age(birth_date, reference_date):
    """Calculate age in years at reference date."""
    birth = pd.to_datetime(birth_date)
    ref = pd.to_datetime(reference_date)
    age = (ref - birth).dt.days / 365.25
    return age.round(0).astype('Int64')
```

### Common DM Validation Issues

| Issue | FDA Rule | Solution |
|-------|----------|----------|
| USUBJID not unique | SD1001 | Ensure one record per subject |
| SEX not from CT | SD1091 | Map to M, F, U, UNDIFFERENTIATED |
| AGE without AGEU | SD1012 | Always provide AGEU when AGE exists |
| RFSTDTC after RFENDTC | SD1046 | Validate date logic |
| ARMCD without ARM | SD1010 | Provide ARM description |
| Missing RFSTDTC | SD1002 | Required for all subjects |

---

## SV - Subject Visits

**Purpose**: One record per subject per visit, defining all planned and unplanned visits.

**Structure**: One record per subject per visit (may include unscheduled visits)

### Required Variables

| Variable | Label | Type |
|----------|-------|------|
| STUDYID | Study Identifier | Char |
| DOMAIN | Domain Abbreviation | Char |
| USUBJID | Unique Subject Identifier | Char |
| VISITNUM | Visit Number | Num |
| VISIT | Visit Name | Char |
| VISITDY | Planned Study Day of Visit | Num |
| SVSTDTC | Start Date/Time of Visit | Char |

### Expected Variables

| Variable | Label | Description |
|----------|-------|-------------|
| SVUPDES | Description of Unplanned Visit | For unscheduled visits |
| SVENDTC | End Date/Time of Visit | Visit end |
| SVSTDY | Study Day of Start of Visit | Calculated |
| SVENDY | Study Day of End of Visit | Calculated |

### Transformation Example

```python
def transform_to_sv(source_df, study_id, tv_df):
    """
    Transform visit data to SDTM SV domain.

    Args:
        source_df: Source visit data (actual visits)
        study_id: Study identifier
        tv_df: Trial Visits (TV) domain for planned visits
    """
    sv = pd.DataFrame()

    # Identifiers
    sv["STUDYID"] = study_id
    sv["DOMAIN"] = "SV"
    sv["USUBJID"] = study_id + "-" + source_df["SUBJECT_ID"].astype(str)

    # Visit identification
    sv["VISITNUM"] = source_df["VISIT_NUMBER"]
    sv["VISIT"] = source_df["VISIT_NAME"].str.upper()

    # Planned study day from TV domain
    sv = sv.merge(
        tv_df[["VISITNUM", "VISITDY"]],
        on="VISITNUM",
        how="left"
    )

    # Actual visit dates
    sv["SVSTDTC"] = source_df["VISIT_START_DATE"].apply(to_iso8601)
    sv["SVENDTC"] = source_df["VISIT_END_DATE"].apply(to_iso8601)

    # Calculate actual study days
    # Get RFSTDTC from DM domain for each subject
    sv = calculate_study_days(sv, "SVSTDTC", "SVSTDY")
    sv = calculate_study_days(sv, "SVENDTC", "SVENDY")

    # Unplanned visits
    sv.loc[sv["VISIT"].str.contains("UNSCHEDULED|UNPLANNED", na=False),
           "SVUPDES"] = source_df["UNPLANNED_REASON"]

    return sv
```

### SV Domain Tips

1. **Every visit in other domains must exist in SV**: This is a common FDA validation error
2. **VISITNUM must be consistent across all domains**
3. **Unscheduled visits**: Use decimal VISITNUM (e.g., 3.1 for unscheduled between visits 3 and 4)
4. **Window visits**: Document actual visit windows in protocol

---

## SE - Subject Elements

**Purpose**: Describes the actual study elements (treatment periods, epochs) a subject experienced.

**Structure**: One record per subject per element

### Required Variables

| Variable | Label | Type |
|----------|-------|------|
| STUDYID | Study Identifier | Char |
| DOMAIN | Domain Abbreviation | Char |
| USUBJID | Unique Subject Identifier | Char |
| SESEQ | Sequence Number | Num |
| ETCD | Element Code | Char |
| ELEMENT | Description of Element | Char |
| SESTDTC | Start Date/Time of Element | Char |
| SEENDTC | End Date/Time of Element | Char |

### Expected Variables

| Variable | Label | Description |
|----------|-------|-------------|
| TAETORD | Planned Order of Element | Links to TA/TE |
| EPOCH | Epoch | SCREENING, TREATMENT, FOLLOW-UP |
| SEUPDES | Description of Unplanned Element | For protocol deviations |

### Relationship to Trial Design

SE describes **actual** elements, while TE (Trial Elements) describes **planned** elements.

```python
def transform_to_se(source_df, study_id, te_df):
    """
    Transform to SE domain.

    SE must align with TE (Trial Elements) domain.
    """
    se = pd.DataFrame()

    se["STUDYID"] = study_id
    se["DOMAIN"] = "SE"
    se["USUBJID"] = study_id + "-" + source_df["SUBJECT_ID"].astype(str)

    # Element identification (from TE)
    se["ETCD"] = source_df["ELEMENT_CODE"]
    se["ELEMENT"] = source_df["ELEMENT_NAME"]
    se["EPOCH"] = source_df["EPOCH"]

    # Actual dates
    se["SESTDTC"] = source_df["ELEMENT_START"].apply(to_iso8601)
    se["SEENDTC"] = source_df["ELEMENT_END"].apply(to_iso8601)

    # Link to planned element order
    se = se.merge(
        te_df[["ETCD", "TAETORD"]],
        on="ETCD",
        how="left"
    )

    # Sequence number
    se["SESEQ"] = se.groupby("USUBJID").cumcount() + 1

    return se
```

---

## CO - Comments

**Purpose**: Store comments that apply to a specific domain, subject, or record.

**Structure**: One record per comment

### Required Variables

| Variable | Label | Type |
|----------|-------|------|
| STUDYID | Study Identifier | Char |
| DOMAIN | Domain Abbreviation | Char |
| USUBJID | Unique Subject Identifier | Char |
| COSEQ | Sequence Number | Num |
| IDVAR | Identifying Variable | Char |
| IDVARVAL | Identifying Variable Value | Char |
| COREF | Comment Reference | Char |
| COEVAL | Evaluator | Char |
| COVAL | Comment | Char |

### Use Cases

1. **General subject comments**: Comments about overall subject participation
2. **Domain-specific comments**: Comments about specific AE, CM, etc.
3. **Data clarifications**: Explanations for unusual values

### Transformation Example

```python
def create_co_record(study_id, usubjid, comment, ref_domain=None, ref_seq=None):
    """
    Create a CO domain record.

    Args:
        study_id: Study identifier
        usubjid: Subject ID
        comment: Comment text
        ref_domain: Referenced domain (e.g., "AE")
        ref_seq: Sequence number in referenced domain
    """
    co_record = {
        "STUDYID": study_id,
        "DOMAIN": "CO",
        "USUBJID": usubjid,
        "COVAL": comment,
    }

    if ref_domain and ref_seq:
        co_record["IDVAR"] = f"{ref_domain}SEQ"
        co_record["IDVARVAL"] = str(ref_seq)
        co_record["COREF"] = ref_domain

    return co_record

# Example: Comment on specific AE record
co_records = []
co_records.append(create_co_record(
    "STUDY-001",
    "STUDY-001-001",
    "Subject reported headache resolved with acetaminophen",
    ref_domain="AE",
    ref_seq=3
))
```

---

## Key Validation Rules for Special Purpose Domains

### DM Validation

| Rule | Check | Severity |
|------|-------|----------|
| SD1198 | USUBJID is unique | ERROR |
| SD1001 | Required variables populated | ERROR |
| SD1091 | CT values valid (SEX, RACE, ETHNIC) | ERROR |
| SD1046 | RFSTDTC <= RFENDTC | ERROR |
| SD1047 | RFXSTDTC <= RFXENDTC | ERROR |
| SD1048 | RFICDTC <= RFSTDTC | WARNING |
| SD2092 | AGE calculated correctly from BRTHDTC | WARNING |

### SV Validation

| Rule | Check | Severity |
|------|-------|----------|
| SD2227 | All VISIT/VISITNUM in findings domains exist in SV | ERROR |
| SD1046 | SVSTDTC <= SVENDTC | ERROR |
| SD2228 | VISITNUM is unique per USUBJID | ERROR |

### SE Validation

| Rule | Check | Severity |
|------|-------|----------|
| SD1046 | SESTDTC <= SEENDTC | ERROR |
| SD2264 | ETCD exists in TE domain | WARNING |
| SD2265 | Element sequence logical | WARNING |

## Common Mistakes

### Mistake 1: Inconsistent USUBJID Construction

**Issue**: Different USUBJID patterns across domains

**Solution**: Define USUBJID construction once and use consistently:
```python
# Define this ONCE in a configuration
def create_usubjid(study_id, site_id, subject_id):
    """Standard USUBJID constructor."""
    return f"{study_id}-{site_id}-{subject_id}"

# Use everywhere
dm["USUBJID"] = create_usubjid(STUDY_ID, dm["SITEID"], dm["SUBJID"])
ae["USUBJID"] = create_usubjid(STUDY_ID, ae_source["SITE"], ae_source["SUBJECT"])
```

### Mistake 2: Missing Visits in SV

**Issue**: Findings domains reference visits not in SV

**Solution**: Create SV records for ALL visits (even if just planned):
```python
# Validate all visits exist in SV
def validate_visits_in_sv(findings_df, sv_df):
    """Check all visits in findings are in SV."""
    findings_visits = set(zip(findings_df["USUBJID"], findings_df["VISITNUM"]))
    sv_visits = set(zip(sv_df["USUBJID"], sv_df["VISITNUM"]))

    missing = findings_visits - sv_visits
    if missing:
        print(f"ERROR: {len(missing)} visits in findings not in SV")
        print("Missing (USUBJID, VISITNUM):", list(missing)[:10])
```

### Mistake 3: Incorrect Age Calculation

**Issue**: Age doesn't match BRTHDTC and RFSTDTC

**Solution**: Calculate age precisely:
```python
def calculate_age_correctly(birth_dtc, reference_dtc):
    """
    Calculate age per CDISC standard.

    Returns age in YEARS (most common) rounded down.
    """
    birth = pd.to_datetime(birth_dtc)
    ref = pd.to_datetime(reference_dtc)

    # Calculate age in days, then convert to years
    age_days = (ref - birth).dt.days
    age_years = np.floor(age_days / 365.25).astype('Int64')

    return age_years
```

## Instructions for Agent

When working with Special Purpose domains:

1. **DM First**: Always create DM domain first as it defines USUBJID and reference dates
2. **Consistent USUBJID**: Use the same construction pattern across ALL domains
3. **SV Completeness**: Ensure SV contains ALL visits referenced in any domain
4. **Date Logic**: Validate all date relationships (RFSTDTC <= RFENDTC, etc.)
5. **Controlled Terminology**: Apply CT strictly for SEX, RACE, ETHNIC
6. **One Record Per Subject**: DM must have exactly one record per USUBJID
7. **Reference Dates**: RFSTDTC is typically first exposure/first visit; document your decision
8. **Arms**: Differentiate between planned (ARMCD/ARM) and actual (ACTARMCD/ACTARM)

## Available Tools

- `generate_mapping_spec` - Create mapping specification
- `transform_to_sdtm` - Generic transformation
- `validate_controlled_terminology` - Verify CT compliance
- `lookup_sdtm_domain` - Get DM, SV, SE, CO structure
- `convert_domain` - High-level conversion

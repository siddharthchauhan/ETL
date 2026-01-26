---
name: trial-design-domains
description: Use this skill for Trial Design SDTM domains (TA, TE, TV, TI, TS). These domains describe the planned structure of the trial including arms, elements, visits, and inclusion criteria. TA/TE/TV work together to define the protocol design. TS provides trial summary information. Essential for protocol-driven mapping and understanding planned vs actual data.
---

# Trial Design Domains Skill (TA, TE, TV, TI, TS)

## Overview

Trial Design domains describe the **planned** structure of the clinical trial. They are protocol-driven and typically do not vary by subject (except for TI which is subject-specific).

**Key Principle**: Trial Design domains describe PLANNED structure; Special Purpose domains (SE, SV) describe ACTUAL subject experience.

## TS - Trial Summary

**Purpose**: Provides trial-level metadata (one record per trial characteristic).

**Structure**: Vertical (one record per summary parameter)

### Required Variables

| Variable | Label |
|----------|-------|
| STUDYID | Study Identifier |
| DOMAIN | Domain Abbreviation ("TS") |
| TSSEQ | Sequence Number |
| TSPARMCD | Trial Summary Parameter Short Name |
| TSPARM | Trial Summary Parameter |
| TSVAL | Parameter Value |

### Common TSPARMCD Values

| TSPARMCD | TSPARM | Example TSVAL |
|----------|--------|---------------|
| AGEMIN | Planned Minimum Age of Subjects | 18 |
| AGEMAX | Planned Maximum Age of Subjects | 65 |
| AGEU | Age Unit | YEARS |
| TTYPE | Trial Type | INTERVENTIONAL |
| TPHASE | Trial Phase Classification | PHASE 3 |
| TITLE | Trial Title | Safety and Efficacy Study of Drug X |
| STYPE | Trial Set Type | SINGLE |
| INDIC | Trial Disease/Condition Being Studied | HYPERTENSION |
| OBJPRIM | Trial Primary Objective | Evaluate efficacy... |
| OBJSEC | Trial Secondary Objective | Assess safety... |
| PCLAS | Trial Product Class | ANTIHYPERTENSIVE AGENT |
| TRT | Investigational Therapy/Treatment | DRUG X 10 MG |
| RANDOM | Trial is Randomized | Y |
| PLANSUB | Planned Number of Subjects | 500 |
| LENGTH | Trial Length | 52 |
| LENU | Trial Length Unit | WEEKS |

### Example TS Domain

```python
def create_ts_domain(study_id, protocol_metadata):
    """
    Create TS domain from protocol information.

    Args:
        study_id: Study identifier
        protocol_metadata: Dict of protocol parameters
    """
    ts_records = []

    # Define TS parameters
    ts_params = [
        ("AGEMIN", "Planned Minimum Age of Subjects", "18"),
        ("AGEMAX", "Planned Maximum Age of Subjects", "75"),
        ("AGEU", "Age Unit", "YEARS"),
        ("TTYPE", "Trial Type", "INTERVENTIONAL"),
        ("TPHASE", "Trial Phase Classification", "PHASE 3"),
        ("TITLE", "Trial Title", protocol_metadata["title"]),
        ("INDIC", "Trial Indication", protocol_metadata["indication"]),
        ("PLANSUB", "Planned Number of Subjects", str(protocol_metadata["planned_n"])),
        ("RANDOM", "Trial is Randomized", "Y"),
        ("BLIND", "Trial Blinding Schema", "DOUBLE BLIND"),
        ("STYPE", "Trial Set Type", "SINGLE"),
    ]

    for seq, (parmcd, parm, val) in enumerate(ts_params, 1):
        ts_records.append({
            "STUDYID": study_id,
            "DOMAIN": "TS",
            "TSSEQ": seq,
            "TSPARMCD": parmcd,
            "TSPARM": parm,
            "TSVAL": val,
        })

    return pd.DataFrame(ts_records)
```

---

## TV - Trial Visits

**Purpose**: Defines all planned visits in the trial protocol.

**Structure**: One record per planned visit

### Required Variables

| Variable | Label | Description |
|----------|-------|-------------|
| STUDYID | Study Identifier | |
| DOMAIN | Domain Abbreviation | "TV" |
| VISITNUM | Visit Number | Numeric visit identifier |
| VISIT | Visit Name | Visit description |
| VISITDY | Planned Study Day of Visit | Nominal day |
| ARMCD | Planned Arm Code | Which arm(s) this visit applies to |
| ARM | Description of Planned Arm | Arm description |

### Expected Variables

| Variable | Label | Description |
|----------|-------|-------------|
| TVSTRL | Visit Start Rule | Rule for visit window start |
| TVENRL | Visit End Rule | Rule for visit window end |

### Example TV Domain

```python
def create_tv_domain(study_id):
    """
    Create TV domain from protocol visit schedule.

    Visit windows are typically defined in the protocol.
    """
    visits = [
        # VISITNUM, VISIT, VISITDY, Window Start, Window End
        (-1, "SCREENING", -14, "-28 to -1 days", None),
        (1, "BASELINE", 1, "Day 1", None),
        (2, "WEEK 2", 14, "Day 10 to Day 18", None),
        (3, "WEEK 4", 28, "Day 24 to Day 32", None),
        (4, "WEEK 8", 56, "Day 52 to Day 60", None),
        (5, "WEEK 12", 84, "Day 80 to Day 88", None),
        (6, "WEEK 16/ET", 112, "Day 108 to Day 116", None),
        (7, "FOLLOW-UP", 140, "Day 136 to Day 144", None),
    ]

    tv_records = []
    for visitnum, visit, visitdy, start_rule, end_rule in visits:
        tv_records.append({
            "STUDYID": study_id,
            "DOMAIN": "TV",
            "VISITNUM": visitnum,
            "VISIT": visit,
            "VISITDY": visitdy,
            "TVSTRL": start_rule,
            "TVENRL": end_rule,
        })

    return pd.DataFrame(tv_records)
```

---

## TA - Trial Arms

**Purpose**: Describes planned treatment arms and their sequence/transition rules.

**Structure**: One record per arm per element

### Required Variables

| Variable | Label | Description |
|----------|-------|-------------|
| STUDYID | Study Identifier | |
| DOMAIN | Domain Abbreviation | "TA" |
| ARMCD | Planned Arm Code | Unique arm identifier |
| ARM | Description of Planned Arm | Full arm description |
| TAETORD | Planned Order of Element within Arm | Sequence number |
| ETCD | Element Code | Element identifier |
| ELEMENT | Description of Element | Element description |
| TABRANCH | Branch | Branching logic |
| TATRANS | Transition Rule | Rule for transitioning |
| EPOCH | Epoch | SCREENING, TREATMENT, etc. |

### Example TA Domain

```python
def create_ta_domain(study_id):
    """
    Create TA domain for a simple 2-arm trial.

    Structure shows planned progression through trial elements.
    """
    ta_records = [
        # Arm 1: Drug X
        {"STUDYID": study_id, "DOMAIN": "TA", "ARMCD": "DRUGX",
         "ARM": "Drug X 10 mg", "TAETORD": 1, "ETCD": "SCRN",
         "ELEMENT": "Screening", "EPOCH": "SCREENING"},
        {"STUDYID": study_id, "DOMAIN": "TA", "ARMCD": "DRUGX",
         "ARM": "Drug X 10 mg", "TAETORD": 2, "ETCD": "TREAT",
         "ELEMENT": "Treatment", "EPOCH": "TREATMENT"},
        {"STUDYID": study_id, "DOMAIN": "TA", "ARMCD": "DRUGX",
         "ARM": "Drug X 10 mg", "TAETORD": 3, "ETCD": "FU",
         "ELEMENT": "Follow-up", "EPOCH": "FOLLOW-UP"},

        # Arm 2: Placebo
        {"STUDYID": study_id, "DOMAIN": "TA", "ARMCD": "PLCBO",
         "ARM": "Placebo", "TAETORD": 1, "ETCD": "SCRN",
         "ELEMENT": "Screening", "EPOCH": "SCREENING"},
        {"STUDYID": study_id, "DOMAIN": "TA", "ARMCD": "PLCBO",
         "ARM": "Placebo", "TAETORD": 2, "ETCD": "TREAT",
         "ELEMENT": "Treatment", "EPOCH": "TREATMENT"},
        {"STUDYID": study_id, "DOMAIN": "TA", "ARMCD": "PLCBO",
         "ARM": "Placebo", "TAETORD": 3, "ETCD": "FU",
         "ELEMENT": "Follow-up", "EPOCH": "FOLLOW-UP"},
    ]

    return pd.DataFrame(ta_records)
```

---

## TE - Trial Elements

**Purpose**: Defines all trial elements (treatment periods, epochs) in the protocol.

**Structure**: One record per element

### Required Variables

| Variable | Label | Description |
|----------|-------|-------------|
| STUDYID | Study Identifier | |
| DOMAIN | Domain Abbreviation | "TE" |
| ETCD | Element Code | Unique element code |
| ELEMENT | Description of Element | Element name/description |
| TESTRL | Start Rule | Rule for element start |
| TEENRL | End Rule | Rule for element end |
| TEDUR | Planned Duration of Element | Duration value |

### Example TE Domain

```python
def create_te_domain(study_id):
    """
    Create TE domain defining trial elements.

    Each element has start/end rules and duration.
    """
    te_records = [
        {
            "STUDYID": study_id,
            "DOMAIN": "TE",
            "ETCD": "SCRN",
            "ELEMENT": "Screening",
            "TESTRL": "Informed consent signed",
            "TEENRL": "Randomization",
            "TEDUR": "P28D",  # ISO 8601 duration: 28 days
        },
        {
            "STUDYID": study_id,
            "DOMAIN": "TE",
            "ETCD": "TREAT",
            "ELEMENT": "Treatment",
            "TESTRL": "First dose of study drug",
            "TEENRL": "Last dose of study drug + 24 hours",
            "TEDUR": "P12W",  # 12 weeks
        },
        {
            "STUDYID": study_id,
            "DOMAIN": "TE",
            "ETCD": "FU",
            "ELEMENT": "Follow-up",
            "TESTRL": "End of treatment + 1 day",
            "TEENRL": "Final study visit",
            "TEDUR": "P4W",  # 4 weeks
        },
    ]

    return pd.DataFrame(te_records)
```

---

## TI - Trial Inclusion/Exclusion Criteria

**Purpose**: Documents which inclusion/exclusion criteria each subject met or failed.

**Structure**: One record per subject per criterion (if collected)

### Required Variables

| Variable | Label | Description |
|----------|-------|-------------|
| STUDYID | Study Identifier | |
| DOMAIN | Domain Abbreviation | "TI" |
| USUBJID | Unique Subject Identifier | |
| TISEQ | Sequence Number | |
| TICAT | Category | INCLUSION, EXCLUSION |
| TITEST | Criterion Short Name | Short description |
| TIEVAL | Evaluator | INVESTIGATOR, etc. |
| TIVERS | Criterion Version | Protocol version |

### Example TI Domain

```python
def create_ti_domain(study_id, subjects_df):
    """
    Create TI domain documenting I/E criteria assessment.

    Note: TI is often not collected in practice.
    If inclusion/exclusion data is available, document it here.
    """
    ti_records = []

    # Example inclusion criteria
    inclusion_criteria = [
        "Age >= 18 and <= 65 years",
        "Diagnosis of hypertension",
        "Willing to provide informed consent",
    ]

    # Example exclusion criteria
    exclusion_criteria = [
        "Pregnant or nursing",
        "Severe hepatic impairment",
        "Allergy to study drug",
    ]

    for _, subject in subjects_df.iterrows():
        usubjid = f"{study_id}-{subject['SUBJID']}"
        seq = 1

        # Inclusion criteria
        for criterion in inclusion_criteria:
            ti_records.append({
                "STUDYID": study_id,
                "DOMAIN": "TI",
                "USUBJID": usubjid,
                "TISEQ": seq,
                "TICAT": "INCLUSION",
                "TITEST": criterion,
                "TIEVAL": "INVESTIGATOR",
                "TIVERS": "Protocol v2.0",
            })
            seq += 1

    return pd.DataFrame(ti_records)
```

---

## Relationships Between Trial Design Domains

```
TS (Trial Summary)
  - Provides overall trial metadata
  - One per trial

TV (Trial Visits)
  - Defines planned visits
  - Referenced by SV (Subject Visits)

TA (Trial Arms) + TE (Trial Elements)
  - TA: Links arms to elements in order
  - TE: Defines each element's rules
  - Together they define the protocol flow
  - Referenced by SE (Subject Elements)

TI (Trial Inclusion/Exclusion)
  - Subject-specific
  - Documents which I/E criteria were assessed
```

### Linking to Subject Data

| Trial Design | → | Subject Data |
|--------------|---|--------------|
| TV (planned visits) | → | SV (actual visits) |
| TE (planned elements) | → | SE (actual elements) |
| TA (planned arms) | → | DM (actual arms: ARMCD/ACTARMCD) |

---

## Validation Rules

| Rule | Check | Severity |
|------|-------|----------|
| TD0001 | TS has all required TSPARMCD values | WARNING |
| TD0002 | VISITNUM is unique in TV | ERROR |
| TD0003 | ETCD in TA exists in TE | ERROR |
| TD0004 | ARMCD in TA matches DM.ARMCD values | WARNING |
| TD0005 | TEDUR is valid ISO 8601 duration | ERROR |
| TD0006 | VISITDY is unique per VISITNUM in TV | ERROR |

## Common Mistakes

### Mistake 1: Missing Visit in TV but Used in Protocol

**Issue**: Protocol references visits not in TV domain

**Solution**: Include ALL protocol-defined visits, even if not all subjects attend

### Mistake 2: Inconsistent ARM/ARMCD

**Issue**: ARMCD in TA doesn't match DM.ARMCD

**Solution**: Ensure exact match between trial design and subject assignments
```python
# Validate consistency
dm_arms = set(dm_df["ARMCD"].unique())
ta_arms = set(ta_df["ARMCD"].unique())

if dm_arms != ta_arms:
    print("ERROR: ARM codes mismatch between DM and TA")
    print(f"In DM but not TA: {dm_arms - ta_arms}")
    print(f"In TA but not DM: {ta_arms - dm_arms}")
```

### Mistake 3: Invalid ISO 8601 Duration in TEDUR

**Issue**: TEDUR not in ISO 8601 format

**Correct Formats**:
- P7D = 7 days
- P4W = 4 weeks
- P12M = 12 months
- P1Y = 1 year

```python
def validate_iso8601_duration(duration_str):
    """Validate ISO 8601 duration format."""
    import re
    pattern = r'^P(?:\d+Y)?(?:\d+M)?(?:\d+W)?(?:\d+D)?(?:T(?:\d+H)?(?:\d+M)?(?:\d+S)?)?$'
    return bool(re.match(pattern, duration_str))
```

## Instructions for Agent

When creating Trial Design domains:

1. **Start with TS**: Document trial-level metadata from protocol
2. **Create TV**: Define ALL planned visits from protocol schedule
3. **Create TE**: Define ALL trial elements (periods/epochs)
4. **Create TA**: Link arms to elements in sequence
5. **Consistency**: Ensure ARMCD, ETCD, VISITNUM match across domains
6. **ISO 8601**: Use proper duration format (P#D, P#W, P#M)
7. **Completeness**: Include all protocol-defined structures
8. **TI Optional**: Only create if I/E criterion data was collected

## Available Tools

- `generate_trial_design_domains` - Create TS, TV, TA, TE from protocol
- `validate_trial_design` - Check consistency across domains
- `lookup_sdtm_domain` - Get domain specifications

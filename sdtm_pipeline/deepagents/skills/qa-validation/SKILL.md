---
name: qa-validation
description: Use this skill for SDTM validation, Pinnacle 21 conformance checks, Define.xml generation, quality control procedures, regulatory submission requirements, and debugging data quality issues. Essential for Phase 2 (Raw Validation), Phase 6 (Target Validation), and submission readiness.
---

# Quality Assurance and Validation Skill

## Overview

This skill provides expertise in validating SDTM datasets for CDISC conformance, generating regulatory-compliant metadata (Define.xml), and ensuring data quality throughout the ETL pipeline. Critical for achieving submission-ready data with >= 95% compliance score.

## Core Competencies

### 1. Multi-Layer Validation Framework

**When to use**: Comprehensive validation across all ETL phases.

#### Validation Layers

| Layer | Phase | Description | Tools |
|-------|-------|-------------|-------|
| **Structural** | Phase 2, 6 | Required variables, data types, lengths | `validate_structural` |
| **CDISC Conformance** | Phase 6 | CT values, ISO dates, naming conventions | `validate_cdisc_conformance` |
| **Cross-Domain** | Phase 6 | Referential integrity between domains | Custom validation |
| **Semantic** | Phase 6 | Business logic, clinical plausibility | Custom validation |
| **Anomaly Detection** | Phase 2, 6 | Statistical outliers, data quality | Isolation Forest |
| **Protocol Compliance** | Phase 6 | Study-specific requirements | Custom validation |

#### Validation Rule Categories

```python
VALIDATION_RULES = {
    "structural": {
        "SD0001": "Required variable missing",
        "SD0002": "Variable exceeds maximum length",
        "SD0003": "Invalid data type",
        "SD0004": "Duplicate records detected",
    },
    "cdisc": {
        "CT0001": "Value not in controlled terminology",
        "CT0002": "Invalid ISO 8601 date format",
        "CT0003": "Invalid variable naming convention",
        "CT0004": "Missing codelist reference",
    },
    "cross_domain": {
        "XD0001": "USUBJID not found in DM",
        "XD0002": "Reference date before study start",
        "XD0003": "Orphan record in child domain",
    },
    "semantic": {
        "SM0001": "End date before start date",
        "SM0002": "Age outside plausible range",
        "SM0003": "Deceased subject with ongoing events",
    }
}
```

### 2. Pinnacle 21 (OpenCDISC) Validation Rules

**When to use**: Validating against FDA-accepted conformance rules.

#### Rule Severity Levels

| Severity | Impact | Action Required |
|----------|--------|-----------------|
| **ERROR** | Submission blocker | Must fix before submission |
| **WARNING** | Potential issue | Review and document rationale |
| **NOTICE** | Best practice | Consider improvement |

#### Common Pinnacle 21 Rules

**DM Domain Rules**
- `SD1001`: STUDYID value is empty
- `SD1002`: DOMAIN value does not match dataset name
- `SD1003`: USUBJID must be unique within study
- `DM0001`: Required variable RFSTDTC is missing
- `DM0006`: RACE value not in controlled terminology

**AE Domain Rules**
- `AE0004`: AEDECOD should be populated
- `AE0007`: AESTDTC must be in ISO 8601 format
- `AE0010`: AESER should be Y or N
- `AE0015`: AEOUT should be from controlled terminology

**Cross-Domain Rules**
- `USUBJID not in DM`: Subject not found in Demographics
- `Date before RFSTDTC`: Event occurred before study start
- `Date after RFENDTC`: Event occurred after study end

### 3. Conformance Score Calculation

**When to use**: Determining submission readiness.

#### Scoring Algorithm

```python
def calculate_conformance_score(validation_results: dict) -> float:
    """
    Calculate weighted conformance score.

    Weights:
    - Structural: 25%
    - CDISC: 30%
    - Cross-Domain: 20%
    - Semantic: 15%
    - Anomaly: 10%
    """
    weights = {
        "structural": 0.25,
        "cdisc": 0.30,
        "cross_domain": 0.20,
        "semantic": 0.15,
        "anomaly": 0.10
    }

    layer_scores = {}
    for layer, weight in weights.items():
        result = validation_results.get(layer, {})
        total = result.get("total_checks", 1)
        passed = result.get("passed_checks", 0)
        layer_scores[layer] = (passed / total) * 100

    overall = sum(
        layer_scores[layer] * weight
        for layer, weight in weights.items()
    )

    return round(overall, 1)
```

#### Submission Readiness Criteria

| Criteria | Threshold | Status |
|----------|-----------|--------|
| Overall Score | >= 95% | Required |
| Critical Errors | 0 | Required |
| Structural Score | >= 100% | Required |
| CDISC Score | >= 95% | Required |

### 4. Define.xml Generation

**When to use**: Phase 5 - Creating machine-readable metadata for submission.

#### Define.xml Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ODM xmlns="http://www.cdisc.org/ns/odm/v1.3"
     xmlns:def="http://www.cdisc.org/ns/def/v2.1"
     FileOID="STUDY.DEFINE"
     FileType="Snapshot">

  <Study OID="STUDY.MAXIS-08">
    <MetaDataVersion OID="CDISC.SDTM.3.4"
                     Name="Study MAXIS-08 SDTM"
                     def:DefineVersion="2.1.0"
                     def:StandardName="SDTMIG"
                     def:StandardVersion="3.4">

      <!-- ItemGroupDef for each dataset -->
      <ItemGroupDef OID="IG.DM"
                    Name="DM"
                    Repeating="No"
                    def:Structure="One record per subject"
                    def:Class="Special-Purpose">
        <!-- ItemRef for each variable -->
        <ItemRef ItemOID="IT.DM.STUDYID" OrderNumber="1" Mandatory="Yes"/>
        <ItemRef ItemOID="IT.DM.DOMAIN" OrderNumber="2" Mandatory="Yes"/>
        <!-- ... -->
      </ItemGroupDef>

      <!-- CodeList definitions -->
      <CodeList OID="CL.SEX" Name="Sex" DataType="text">
        <CodeListItem CodedValue="M">
          <Decode><TranslatedText>Male</TranslatedText></Decode>
        </CodeListItem>
        <CodeListItem CodedValue="F">
          <Decode><TranslatedText>Female</TranslatedText></Decode>
        </CodeListItem>
      </CodeList>

    </MetaDataVersion>
  </Study>
</ODM>
```

#### Required Define.xml Elements

| Element | Description | Source |
|---------|-------------|--------|
| **Study OID** | Unique study identifier | Protocol |
| **MetaDataVersion** | SDTM-IG version | Configuration |
| **ItemGroupDef** | Dataset definitions | SDTM datasets |
| **ItemDef** | Variable definitions | Data specifications |
| **CodeList** | Controlled terminology | CDISC CT |
| **MethodDef** | Derivation algorithms | Mapping specifications |
| **CommentDef** | Additional annotations | Documentation |

### 5. Quality Control Procedures

**When to use**: Verifying transformation accuracy.

#### QC Checklist

**Pre-Transformation QC (Phase 2)**
- [ ] Source file row counts documented
- [ ] All expected source files present
- [ ] No unexpected null values in key fields
- [ ] Date formats identified and documented
- [ ] Duplicate records identified

**Post-Transformation QC (Phase 6)**
- [ ] Row count reconciliation (source vs target)
- [ ] Key variable population rates
- [ ] CT value mapping accuracy
- [ ] Date conversion validation
- [ ] USUBJID uniqueness verification
- [ ] Cross-domain referential integrity

#### QC Report Template

```json
{
  "qc_report": {
    "study_id": "MAXIS-08",
    "domain": "DM",
    "executed_at": "2024-01-15T14:30:00",
    "checks": [
      {
        "check_id": "QC001",
        "description": "Row count reconciliation",
        "source_count": 150,
        "target_count": 150,
        "status": "PASS"
      },
      {
        "check_id": "QC002",
        "description": "USUBJID uniqueness",
        "total_records": 150,
        "unique_records": 150,
        "status": "PASS"
      }
    ],
    "overall_status": "PASS"
  }
}
```

### 6. Regulatory Submission Requirements

**When to use**: Preparing data for FDA/EMA submission.

#### FDA eCTD Requirements

| Component | Format | Location |
|-----------|--------|----------|
| SDTM Datasets | SAS XPT v5 | m5/datasets/tabulations/sdtm |
| Define.xml | XML v2.1 | m5/datasets/tabulations/sdtm |
| Reviewer's Guide | PDF | m5/datasets/tabulations/sdtm |
| aCRF | PDF | m5/datasets/tabulations/sdtm |

#### Dataset Naming Conventions

- Dataset names: lowercase, 8 characters max (dm.xpt, ae.xpt)
- Variable names: uppercase, 8 characters max
- Character variable length: 200 characters max
- File size: 5GB max per dataset

### 7. Problem Solving and Debugging

**When to use**: Resolving validation errors and data quality issues.

#### Common Error Resolution

| Error | Root Cause | Resolution |
|-------|-----------|------------|
| CT value not found | Raw data uses non-standard values | Create mapping table to CT values |
| Invalid date format | Multiple date formats in source | Apply date parsing logic |
| Missing USUBJID | Join failed | Verify subject ID matching |
| Duplicate --SEQ | Incorrect sequence generation | Reset sequence per subject |
| Referential integrity | Parent record missing | Add to parent domain or exclude |

#### Debugging Workflow

1. **Identify**: Read validation report, note rule ID
2. **Isolate**: Find affected records using filters
3. **Trace**: Check source data and mapping logic
4. **Fix**: Update transformation or mapping spec
5. **Verify**: Re-run validation on affected domain
6. **Document**: Record issue and resolution

## Instructions for Agent

When the agent receives a validation task:

1. **Phase 2 (Raw Data Validation)**
   - Run structural checks on source files
   - Identify missing required fields
   - Flag data quality issues
   - Generate raw data quality report

2. **Phase 6 (Target Data Validation)**
   - Run multi-layer validation
   - Calculate conformance score
   - Identify submission blockers
   - Generate validation report

3. **Self-Correction Loop**
   - If score < 95%: analyze failed rules
   - Generate correction feedback
   - Retry transformation (max 3 iterations)
   - Escalate to human review if unresolved

4. **Define.xml Generation**
   - Create from dataset metadata
   - Include all variable definitions
   - Reference controlled terminology
   - Validate against schema

## Available Tools

- `validate_structural` - Check required variables and types
- `validate_cdisc_conformance` - Check CT and date formats
- `calculate_compliance_score` - Calculate overall score
- `validate_domain` - High-level domain validation
- `get_validation_rules` - Get business rules from KB

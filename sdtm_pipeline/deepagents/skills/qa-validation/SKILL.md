---
name: qa-validation
description: This skill provides expertise in validating SDTM datasets for CDISC conformance, generating regulatory-compliant metadata (Define-XML 2.1), and ensuring data quality throughout the ETL pipeline. Critical for achieving submission-ready data with zero critical errors and documented resolution of all warnings
---

# Quality Assurance and Validation Skill (Corrected)

## Overview

This skill provides expertise in validating SDTM datasets for CDISC conformance, generating regulatory-compliant metadata (Define-XML 2.1), and ensuring data quality throughout the ETL pipeline. Critical for achieving submission-ready data with zero critical errors and documented resolution of all warnings.

## Core Competencies

### 1. Multi-Layer Validation Framework

**When to use**: Comprehensive validation across all ETL phases.

#### Validation Layers

| Layer | Phase | Description | Tools |
|-------|-------|-------------|-------|
| **Structural** | Phase 2, 6 | Required variables, data types, lengths | `validate_structural` |
| **CDISC Conformance** | Phase 6 | CT values, ISO dates, naming conventions | `validate_cdisc_conformance` |
| **Cross-Domain** | Phase 6 | Referential integrity between domains | `validate_cross_domain` |
| **Trial Design** | Phase 6 | TS, TA, TE, TV, TI domain requirements | `validate_trial_design` |
| **Semantic** | Phase 6 | Business logic, clinical plausibility | Custom validation |
| **Anomaly Detection** | Phase 2, 6 | Statistical outliers, data quality | Isolation Forest |
| **Protocol Compliance** | Phase 6 | Study-specific requirements | Custom validation |

#### Validation Rule Categories

```python
VALIDATION_RULES = {
    "structural": {
        "SD0001": "Invalid variable name (not in SDTMIG)",
        "SD0002": "Variable exceeds maximum length (200 chars)",
        "SD0003": "Invalid data type for variable",
        "SD0006": "Missing required variable",
        "SD0026": "Duplicate records in domain",
        "SD0063": "--SEQ values not unique within USUBJID",
    },
    "cdisc_conformance": {
        "CT0001": "Value not in CDISC Controlled Terminology",
        "CT0046": "Invalid extensible codelist value not in CT",
        "CT2001": "CT version not specified in Define-XML",
        "SD0020": "Date/time format not ISO 8601 compliant",
        "SD0022": "Invalid partial date format",
    },
    "cross_domain": {
        "SD0083": "USUBJID not found in DM domain",
        "SD0084": "STUDYID inconsistent across domains",
        "SD0020": "Date/time precedes RFSTDTC (study reference start)",
        "SD0021": "Date/time after RFENDTC (study reference end)",
        "SD0048": "VISITNUM not found in TV domain",
    },
    "trial_design": {
        "SD1050": "Required TS parameter missing",
        "SD1051": "TS TSPARMCD not in controlled terminology",
        "SD1052": "Trial design domain missing required variable",
        "SD1053": "TA/TE/TV inconsistency detected",
    },
    "suppqual": {
        "SD1100": "SUPPQUAL RDOMAIN not a valid domain",
        "SD1101": "SUPPQUAL IDVAR not valid for parent domain",
        "SD1102": "SUPPQUAL IDVARVAL not found in parent domain",
        "SD1103": "SUPPQUAL QNAM exceeds 8 characters",
        "SD1104": "SUPPQUAL variable conflicts with parent domain",
    },
    "semantic": {
        "SM0001": "End date/time before start date/time",
        "SM0002": "Calculated age outside plausible range (0-120)",
        "SM0003": "Deceased subject has events after death date",
        "SM0004": "Baseline flag set for multiple records per test",
        "SM0005": "Study day calculation inconsistent with dates",
    },
    "define_xml": {
        "DD0006": "Dataset referenced in Define-XML not found",
        "DD0012": "Variable label mismatch between data and Define-XML",
        "DD0015": "Variable length mismatch between data and Define-XML",
        "DD0020": "Missing ValueListDef for variable with value-level metadata",
        "DD0025": "CodeList referenced but not defined",
    }
}
```

### 2. Pinnacle 21 Validation Integration

**When to use**: Validating against FDA-accepted conformance rules.

#### Important Note on Pinnacle 21 Versions

| Version | Interface | Usage |
|---------|-----------|-------|
| **P21 Community** | GUI-based | Manual validation, free download from pinnacle21.com |
| **P21 Enterprise** | REST API | Automated pipelines, requires license |
| **CDISC CORE** | CLI/Python | Open-source alternative (rules.cdisc.org) |

#### Rule Severity Levels

| Severity | Impact | Action Required |
|----------|--------|-----------------|
| **ERROR** | Submission blocker | Must fix before submission |
| **WARNING** | Potential issue | Review and document in SDRG |
| **NOTICE** | Best practice | Consider improvement |

#### Critical Pinnacle 21 Rules by Domain

**DM Domain (Demographics)**
| Rule ID | Description | Severity |
|---------|-------------|----------|
| SD0006 | Missing required variable (STUDYID, DOMAIN, USUBJID, etc.) | ERROR |
| SD0083 | USUBJID values should be unique | ERROR |
| CT0046 | SEX value not in controlled terminology | ERROR |
| CT0046 | RACE value not in controlled terminology | ERROR |
| SD0020 | RFSTDTC not in ISO 8601 format | ERROR |
| SD0020 | RFENDTC not in ISO 8601 format | ERROR |

**AE Domain (Adverse Events)**
| Rule ID | Description | Severity |
|---------|-------------|----------|
| SD0006 | Missing required variable (AETERM, AEDECOD, etc.) | ERROR |
| CT0046 | AESEV not in controlled terminology | ERROR |
| CT0046 | AESER not in controlled terminology (Y/N) | ERROR |
| CT0046 | AEREL not in controlled terminology | ERROR |
| CT0046 | AEOUT not in controlled terminology | ERROR |
| SD0020 | AESTDTC not in ISO 8601 format | ERROR |
| SD1003 | AEDECOD should match MedDRA Preferred Term | WARNING |

**LB Domain (Laboratory)**
| Rule ID | Description | Severity |
|---------|-------------|----------|
| SD0006 | Missing required variable (LBTESTCD, LBTEST, etc.) | ERROR |
| SD0063 | LBSEQ not unique within USUBJID | ERROR |
| CT0046 | LBTESTCD not in controlled terminology | ERROR |
| SM0004 | Multiple LBBLFL='Y' for same test per subject | ERROR |
| SD0048 | VISITNUM not consistent with TV domain | WARNING |

**VS Domain (Vital Signs)**
| Rule ID | Description | Severity |
|---------|-------------|----------|
| SD0006 | Missing required variable (VSTESTCD, VSTEST, etc.) | ERROR |
| CT0046 | VSTESTCD not in controlled terminology | ERROR |
| SD0022 | VSDTC contains invalid partial date | ERROR |
| SM0004 | Multiple VSBLFL='Y' for same test per subject | ERROR |

**TS Domain (Trial Summary) - REQUIRED**
| Rule ID | Description | Severity |
|---------|-------------|----------|
| SD1050 | Required TS parameter missing | ERROR |
| CT0046 | TSPARMCD not in controlled terminology | ERROR |
| SD0006 | Missing TSVAL for required parameter | ERROR |

**Cross-Domain Validation**
| Rule ID | Description | Severity |
|---------|-------------|----------|
| SD0083 | USUBJID not in DM domain | ERROR |
| SD0084 | STUDYID inconsistent with DM.STUDYID | ERROR |
| SD0020 | Date/time before DM.RFSTDTC | WARNING |
| SD0021 | Date/time after DM.RFENDTC | WARNING |
| SD0060 | STUDYID value differs from dataset filename | ERROR |

### 3. Trial Summary (TS) Domain Requirements

**CRITICAL**: TS domain is REQUIRED for all FDA submissions.

#### Required TS Parameters

```python
REQUIRED_TS_PARAMETERS = [
    "ADDON",      # Added on to Existing Treatments
    "AGEMAX",     # Planned Maximum Age of Subjects
    "AGEMIN",     # Planned Minimum Age of Subjects
    "INDIC",      # Trial Disease/Condition Indication
    "LENGTH",     # Trial Length
    "OBJPRIM",    # Trial Primary Objective
    "PLESSION",   # Planned Number of Subjects per Site
    "STYPE",      # Study Type
    "TBLIND",     # Trial Blinding Schema
    "TCNTRL",     # Control Type
    "TINDTP",     # Trial Indication Type
    "TITLE",      # Trial Title
    "TPHASE",     # Trial Phase Classification
    "TTYPE",      # Trial Type
]

def validate_ts_domain(ts_df: pd.DataFrame) -> dict:
    """
    Validate Trial Summary domain for required parameters.
    
    Args:
        ts_df: Trial Summary dataframe
        
    Returns:
        Dictionary with validation results
    """
    issues = []
    
    if ts_df.empty:
        return {"valid": False, "issues": ["TS domain is empty - SUBMISSION BLOCKER"]}
    
    # Check required variables exist
    required_vars = ["STUDYID", "DOMAIN", "TSSEQ", "TSPARMCD", "TSPARM", "TSVAL"]
    missing_vars = [v for v in required_vars if v not in ts_df.columns]
    if missing_vars:
        issues.append(f"SD0006: Missing required variables: {missing_vars}")
    
    # Check required parameters present
    present_params = ts_df["TSPARMCD"].unique().tolist() if "TSPARMCD" in ts_df.columns else []
    missing_params = [p for p in REQUIRED_TS_PARAMETERS if p not in present_params]
    
    for param in missing_params:
        issues.append(f"SD1050: Required TS parameter missing: {param}")
    
    # Check TSVAL not empty for required parameters
    if "TSPARMCD" in ts_df.columns and "TSVAL" in ts_df.columns:
        for param in REQUIRED_TS_PARAMETERS:
            param_rows = ts_df[ts_df["TSPARMCD"] == param]
            if not param_rows.empty:
                if param_rows["TSVAL"].isna().all() or (param_rows["TSVAL"] == "").all():
                    issues.append(f"SD0006: TSVAL empty for required parameter: {param}")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "required_count": len(REQUIRED_TS_PARAMETERS),
        "present_count": len([p for p in REQUIRED_TS_PARAMETERS if p in present_params])
    }
```

### 4. SUPPQUAL Domain Validation

**When to use**: Validating Supplemental Qualifier domains (SUPPAE, SUPPLB, etc.)

```python
def validate_suppqual(supp_df: pd.DataFrame, parent_df: pd.DataFrame, 
                       parent_domain: str) -> dict:
    """
    Validate Supplemental Qualifier domain against parent.
    
    Args:
        supp_df: SUPPQUAL dataframe (e.g., SUPPAE)
        parent_df: Parent domain dataframe (e.g., AE)
        parent_domain: Parent domain name (e.g., "AE")
        
    Returns:
        Dictionary with validation results
    """
    issues = []
    
    # SD1100: Check RDOMAIN matches parent
    if "RDOMAIN" in supp_df.columns:
        invalid_rdomain = supp_df[supp_df["RDOMAIN"] != parent_domain]
        if not invalid_rdomain.empty:
            issues.append(f"SD1100: RDOMAIN '{invalid_rdomain['RDOMAIN'].iloc[0]}' "
                         f"does not match parent domain '{parent_domain}'")
    
    # SD1101: Check IDVAR is valid for parent domain
    valid_idvars = [f"{parent_domain}SEQ", "USUBJID"]
    if "IDVAR" in supp_df.columns:
        invalid_idvar = supp_df[~supp_df["IDVAR"].isin(valid_idvars)]
        if not invalid_idvar.empty:
            for idvar in invalid_idvar["IDVAR"].unique():
                issues.append(f"SD1101: IDVAR '{idvar}' not valid for {parent_domain}")
    
    # SD1102: Check IDVARVAL exists in parent domain
    if "IDVAR" in supp_df.columns and "IDVARVAL" in supp_df.columns:
        seq_var = f"{parent_domain}SEQ"
        if seq_var in parent_df.columns:
            supp_seq_refs = supp_df[supp_df["IDVAR"] == seq_var]
            if not supp_seq_refs.empty:
                parent_seqs = parent_df[seq_var].astype(str).unique()
                orphan_refs = supp_seq_refs[~supp_seq_refs["IDVARVAL"].isin(parent_seqs)]
                if not orphan_refs.empty:
                    issues.append(f"SD1102: {len(orphan_refs)} IDVARVAL references "
                                 f"not found in parent {seq_var}")
    
    # SD1103: Check QNAM length <= 8
    if "QNAM" in supp_df.columns:
        long_qnam = supp_df[supp_df["QNAM"].str.len() > 8]
        if not long_qnam.empty:
            for qnam in long_qnam["QNAM"].unique():
                issues.append(f"SD1103: QNAM '{qnam}' exceeds 8 characters")
    
    # SD1104: Check QNAM doesn't conflict with parent domain variables
    if "QNAM" in supp_df.columns:
        parent_vars = set(parent_df.columns)
        conflicting = supp_df[supp_df["QNAM"].isin(parent_vars)]
        if not conflicting.empty:
            for qnam in conflicting["QNAM"].unique():
                issues.append(f"SD1104: QNAM '{qnam}' conflicts with parent domain variable")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "records_checked": len(supp_df)
    }
```

### 5. Conformance Score Calculation

**When to use**: Determining submission readiness.

#### Scoring Algorithm (Regulatory Focus)

```python
def calculate_conformance_score(validation_results: dict) -> dict:
    """
    Calculate weighted conformance score with regulatory focus.
    
    Weights reflect FDA submission priorities:
    - Structural: 20% (required variables, types)
    - CDISC Conformance: 25% (CT, dates, naming)
    - Cross-Domain: 15% (referential integrity)
    - Trial Design: 15% (TS, TA, TE, TV, TI)
    - Semantic: 15% (business logic)
    - Define-XML: 10% (metadata consistency)
    
    Returns:
        Dictionary with scores and submission readiness
    """
    weights = {
        "structural": 0.20,
        "cdisc_conformance": 0.25,
        "cross_domain": 0.15,
        "trial_design": 0.15,
        "semantic": 0.15,
        "define_xml": 0.10,
    }
    
    layer_scores = {}
    critical_errors = 0
    
    for layer, weight in weights.items():
        result = validation_results.get(layer, {})
        total = result.get("total_checks", 1)
        passed = result.get("passed_checks", 0)
        errors = result.get("error_count", 0)
        
        layer_scores[layer] = {
            "score": round((passed / total) * 100, 1) if total > 0 else 0,
            "errors": errors,
            "warnings": result.get("warning_count", 0)
        }
        critical_errors += errors
    
    overall = sum(
        layer_scores[layer]["score"] * weight
        for layer, weight in weights.items()
    )
    
    # Submission readiness criteria
    submission_ready = (
        overall >= 95.0 and
        critical_errors == 0 and
        layer_scores["structural"]["score"] == 100 and
        layer_scores["trial_design"]["score"] >= 95
    )
    
    return {
        "overall_score": round(overall, 1),
        "layer_scores": layer_scores,
        "critical_errors": critical_errors,
        "submission_ready": submission_ready,
        "blockers": _identify_blockers(layer_scores, critical_errors)
    }

def _identify_blockers(layer_scores: dict, critical_errors: int) -> list:
    """Identify submission blockers."""
    blockers = []
    
    if critical_errors > 0:
        blockers.append(f"{critical_errors} critical error(s) must be resolved")
    
    if layer_scores["structural"]["score"] < 100:
        blockers.append("Structural validation must be 100%")
    
    if layer_scores["trial_design"]["score"] < 95:
        blockers.append("Trial design validation (TS domain) must be >= 95%")
    
    return blockers
```

#### Submission Readiness Criteria

| Criteria | Threshold | Rationale |
|----------|-----------|-----------|
| Overall Score | >= 95% | Industry standard |
| Critical Errors | 0 | FDA requirement |
| Structural Score | 100% | Required variables mandatory |
| Trial Design Score | >= 95% | TS domain required |
| CDISC Conformance | >= 95% | CT compliance required |

### 6. Define-XML 2.1 Generation

**When to use**: Phase 5 - Creating machine-readable metadata for submission.

#### Complete Define-XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ODM xmlns="http://www.cdisc.org/ns/odm/v1.3"
     xmlns:def="http://www.cdisc.org/ns/def/v2.1"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     xmlns:arm="http://www.cdisc.org/ns/arm/v1.0"
     FileOID="DEF.STUDY-001.SDTM"
     FileType="Snapshot"
     CreationDateTime="2024-01-15T10:30:00"
     Originator="Sponsor Name"
     SourceSystem="ETL System"
     SourceSystemVersion="1.0">

  <Study OID="STUDY-001">
    <GlobalVariables>
      <StudyName>Study 001</StudyName>
      <StudyDescription>Phase 3 Clinical Trial</StudyDescription>
      <ProtocolName>Protocol 001</ProtocolName>
    </GlobalVariables>

    <MetaDataVersion OID="MDV.STUDY-001.SDTM"
                     Name="Study 001 SDTM Metadata"
                     Description="SDTM datasets for Study 001"
                     def:DefineVersion="2.1.0"
                     def:StandardName="SDTMIG"
                     def:StandardVersion="3.4">

      <!-- Annotated CRF Reference -->
      <def:AnnotatedCRF>
        <def:DocumentRef leafID="LF.ACRF"/>
      </def:AnnotatedCRF>

      <!-- Supplemental Documents -->
      <def:SupplementalDoc>
        <def:DocumentRef leafID="LF.SDRG"/>
      </def:SupplementalDoc>

      <!-- Value Level Metadata (for variables like LBORRES, LBSTRESC) -->
      <def:ValueListDef OID="VL.LB.LBORRES">
        <ItemRef ItemOID="IT.LB.LBORRES.ALT" OrderNumber="1" Mandatory="No">
          <def:WhereClauseRef WhereClauseOID="WC.LB.ALT"/>
        </ItemRef>
        <ItemRef ItemOID="IT.LB.LBORRES.AST" OrderNumber="2" Mandatory="No">
          <def:WhereClauseRef WhereClauseOID="WC.LB.AST"/>
        </ItemRef>
      </def:ValueListDef>

      <!-- Where Clause Definitions -->
      <def:WhereClauseDef OID="WC.LB.ALT">
        <RangeCheck SoftHard="Soft" def:ItemOID="IT.LB.LBTESTCD" Comparator="EQ">
          <CheckValue>ALT</CheckValue>
        </RangeCheck>
      </def:WhereClauseDef>

      <!-- Dataset Definition (ItemGroupDef) -->
      <ItemGroupDef OID="IG.DM"
                    Name="DM"
                    Repeating="No"
                    IsReferenceData="No"
                    Purpose="Tabulation"
                    def:Structure="One record per subject"
                    def:Class="Special-Purpose"
                    def:ArchiveLocationID="LF.DM">

        <Description>
          <TranslatedText xml:lang="en">Demographics</TranslatedText>
        </Description>

        <!-- Variable References -->
        <ItemRef ItemOID="IT.DM.STUDYID" OrderNumber="1" Mandatory="Yes" KeySequence="1"/>
        <ItemRef ItemOID="IT.DM.DOMAIN" OrderNumber="2" Mandatory="Yes"/>
        <ItemRef ItemOID="IT.DM.USUBJID" OrderNumber="3" Mandatory="Yes" KeySequence="2"/>
        <ItemRef ItemOID="IT.DM.SUBJID" OrderNumber="4" Mandatory="No"/>
        <ItemRef ItemOID="IT.DM.RFSTDTC" OrderNumber="5" Mandatory="No"/>
        <ItemRef ItemOID="IT.DM.RFENDTC" OrderNumber="6" Mandatory="No"/>
        <ItemRef ItemOID="IT.DM.RFXSTDTC" OrderNumber="7" Mandatory="No"/>
        <ItemRef ItemOID="IT.DM.RFXENDTC" OrderNumber="8" Mandatory="No"/>
        <ItemRef ItemOID="IT.DM.SITEID" OrderNumber="9" Mandatory="No"/>
        <ItemRef ItemOID="IT.DM.AGE" OrderNumber="10" Mandatory="No"/>
        <ItemRef ItemOID="IT.DM.AGEU" OrderNumber="11" Mandatory="No"/>
        <ItemRef ItemOID="IT.DM.SEX" OrderNumber="12" Mandatory="No"/>
        <ItemRef ItemOID="IT.DM.RACE" OrderNumber="13" Mandatory="No"/>
        <ItemRef ItemOID="IT.DM.ARMCD" OrderNumber="14" Mandatory="No"/>
        <ItemRef ItemOID="IT.DM.ARM" OrderNumber="15" Mandatory="No"/>
        <ItemRef ItemOID="IT.DM.ACTARMCD" OrderNumber="16" Mandatory="No"/>
        <ItemRef ItemOID="IT.DM.ACTARM" OrderNumber="17" Mandatory="No"/>
        <ItemRef ItemOID="IT.DM.COUNTRY" OrderNumber="18" Mandatory="No"/>
        <ItemRef ItemOID="IT.DM.DMDTC" OrderNumber="19" Mandatory="No"/>
        <ItemRef ItemOID="IT.DM.DMDY" OrderNumber="20" Mandatory="No"/>

        <!-- Dataset-level Comments -->
        <def:leaf ID="LF.DM" xlink:href="dm.xpt">
          <def:title>dm.xpt</def:title>
        </def:leaf>
      </ItemGroupDef>

      <!-- Variable Definition (ItemDef) -->
      <ItemDef OID="IT.DM.STUDYID"
               Name="STUDYID"
               DataType="text"
               Length="20"
               SASFieldName="STUDYID">
        <Description>
          <TranslatedText xml:lang="en">Study Identifier</TranslatedText>
        </Description>
        <def:Origin Type="Assigned"/>
      </ItemDef>

      <ItemDef OID="IT.DM.USUBJID"
               Name="USUBJID"
               DataType="text"
               Length="50"
               SASFieldName="USUBJID">
        <Description>
          <TranslatedText xml:lang="en">Unique Subject Identifier</TranslatedText>
        </Description>
        <def:Origin Type="Derived">
          <Description>
            <TranslatedText xml:lang="en">Concatenation of STUDYID, SITEID, and SUBJID</TranslatedText>
          </Description>
        </def:Origin>
      </ItemDef>

      <ItemDef OID="IT.DM.SEX"
               Name="SEX"
               DataType="text"
               Length="1"
               SASFieldName="SEX">
        <Description>
          <TranslatedText xml:lang="en">Sex</TranslatedText>
        </Description>
        <CodeListRef CodeListOID="CL.SEX"/>
        <def:Origin Type="CRF">
          <def:DocumentRef leafID="LF.ACRF">
            <def:PDFPageRef PageRefs="12" Type="PhysicalRef"/>
          </def:DocumentRef>
        </def:Origin>
      </ItemDef>

      <!-- CodeList Definition -->
      <CodeList OID="CL.SEX"
                Name="Sex"
                DataType="text"
                def:ExtensibleCodeListID="C66731">
        <CodeListItem CodedValue="M" def:ExtendedValue="No">
          <Decode>
            <TranslatedText xml:lang="en">Male</TranslatedText>
          </Decode>
        </CodeListItem>
        <CodeListItem CodedValue="F" def:ExtendedValue="No">
          <Decode>
            <TranslatedText xml:lang="en">Female</TranslatedText>
          </Decode>
        </CodeListItem>
        <CodeListItem CodedValue="U" def:ExtendedValue="No">
          <Decode>
            <TranslatedText xml:lang="en">Unknown</TranslatedText>
          </Decode>
        </CodeListItem>
        <def:CodeListRef CodeListOID="CL.NCIt.C66731"/>
      </CodeList>

      <!-- External CodeList Reference (CDISC CT) -->
      <CodeList OID="CL.NCIt.C66731"
                Name="Sex"
                DataType="text"
                def:ExtensibleCodeListID="C66731">
        <ExternalCodeList Dictionary="NCI Thesaurus"
                          Version="2024-03-29"
                          ref="https://evs.nci.nih.gov/ftp1/CDISC"/>
      </CodeList>

      <!-- Method Definition (Derivation) -->
      <MethodDef OID="MT.DM.AGE"
                 Name="Algorithm for AGE"
                 Type="Computation">
        <Description>
          <TranslatedText xml:lang="en">
            AGE = floor((RFSTDTC - BRTHDTC) / 365.25)
            Age calculated as years between birth date and reference start date
          </TranslatedText>
        </Description>
      </MethodDef>

      <!-- Comment Definition -->
      <def:CommentDef OID="COM.DM.RACE">
        <Description>
          <TranslatedText xml:lang="en">
            RACE collected using multiple selection; primary race mapped per 
            FDA guidance. Additional races captured in SUPPDM.RACE2, RACE3.
          </TranslatedText>
        </Description>
      </def:CommentDef>

      <!-- Leaf (External File References) -->
      <def:leaf ID="LF.ACRF" xlink:href="acrf.pdf">
        <def:title>Annotated Case Report Form</def:title>
      </def:leaf>
      <def:leaf ID="LF.SDRG" xlink:href="sdrg.pdf">
        <def:title>Study Data Reviewer's Guide</def:title>
      </def:leaf>

    </MetaDataVersion>
  </Study>
</ODM>
```

#### Required Define-XML Elements Checklist

| Element | Description | Required |
|---------|-------------|----------|
| **GlobalVariables** | Study name, description, protocol | Yes |
| **MetaDataVersion** | SDTMIG version, Define version | Yes |
| **ItemGroupDef** | One per dataset with structure, class | Yes |
| **ItemDef** | One per variable with type, length | Yes |
| **def:Origin** | Source of each variable (CRF, Derived, Assigned) | Yes |
| **CodeList** | All controlled terminology with decode values | Yes |
| **def:leaf** | File references for all datasets | Yes |
| **MethodDef** | Derivation logic for computed variables | When applicable |
| **def:ValueListDef** | Value-level metadata (e.g., lab tests) | When applicable |
| **def:WhereClauseDef** | Conditions for value-level metadata | When applicable |
| **def:CommentDef** | Additional annotations | Recommended |
| **def:AnnotatedCRF** | Reference to aCRF PDF | Yes |
| **def:SupplementalDoc** | Reference to SDRG | Yes |

### 7. ISO 8601 Date/Time Validation

**When to use**: Validating all date/time variables in SDTM.

```python
import re
from typing import Optional, Tuple

def validate_iso8601(date_string: str) -> Tuple[bool, Optional[str]]:
    """
    Validate ISO 8601 date/time format per SDTM requirements.
    
    Valid formats:
    - Full date: YYYY-MM-DD
    - Partial date: YYYY-MM, YYYY
    - Full datetime: YYYY-MM-DDTHH:MM:SS
    - With timezone: YYYY-MM-DDTHH:MM:SS+HH:MM or YYYY-MM-DDTHH:MM:SSZ
    - With fractional seconds: YYYY-MM-DDTHH:MM:SS.sss
    
    Args:
        date_string: Date/time string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not date_string or pd.isna(date_string):
        return True, None  # Empty dates are valid (completeness is separate check)
    
    # Pattern for complete and partial dates/times
    patterns = [
        # Full date: YYYY-MM-DD
        r'^(\d{4})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$',
        # Partial date: YYYY-MM
        r'^(\d{4})-(0[1-9]|1[0-2])$',
        # Year only: YYYY
        r'^(\d{4})$',
        # Full datetime without timezone: YYYY-MM-DDTHH:MM:SS
        r'^(\d{4})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])T([01]\d|2[0-3]):([0-5]\d):([0-5]\d)$',
        # Datetime with fractional seconds: YYYY-MM-DDTHH:MM:SS.sss
        r'^(\d{4})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])T([01]\d|2[0-3]):([0-5]\d):([0-5]\d)\.\d{1,6}$',
        # Datetime with UTC (Z): YYYY-MM-DDTHH:MM:SSZ
        r'^(\d{4})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])T([01]\d|2[0-3]):([0-5]\d):([0-5]\d)Z$',
        # Datetime with timezone offset: YYYY-MM-DDTHH:MM:SS[+-]HH:MM
        r'^(\d{4})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])T([01]\d|2[0-3]):([0-5]\d):([0-5]\d)[+-]([01]\d|2[0-3]):([0-5]\d)$',
        # Partial datetime (no seconds): YYYY-MM-DDTHH:MM
        r'^(\d{4})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])T([01]\d|2[0-3]):([0-5]\d)$',
    ]
    
    for pattern in patterns:
        if re.match(pattern, date_string):
            return True, None
    
    return False, f"SD0020: Invalid ISO 8601 format: '{date_string}'"

def validate_date_variables(df: pd.DataFrame, date_vars: list) -> dict:
    """
    Validate all date variables in a dataframe.
    
    Args:
        df: Dataframe to validate
        date_vars: List of date variable names ending in DTC
        
    Returns:
        Dictionary with validation results
    """
    issues = []
    total_checks = 0
    passed_checks = 0
    
    for var in date_vars:
        if var not in df.columns:
            continue
            
        for idx, value in df[var].items():
            total_checks += 1
            is_valid, error = validate_iso8601(str(value) if pd.notna(value) else "")
            
            if is_valid:
                passed_checks += 1
            else:
                issues.append({
                    "rule": "SD0020",
                    "variable": var,
                    "row": idx,
                    "value": value,
                    "message": error
                })
    
    return {
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "issues": issues,
        "pass_rate": round((passed_checks / total_checks) * 100, 1) if total_checks > 0 else 100
    }
```

### 8. Baseline Flag Validation

**When to use**: Validating --BLFL variables in findings domains (LB, VS, EG, etc.)

```python
def validate_baseline_flags(findings_df: pd.DataFrame, dm_df: pd.DataFrame,
                            domain: str) -> dict:
    """
    Validate baseline flag assignment per SDTM requirements.
    
    Rules:
    1. Only one BLFL='Y' per subject per test
    2. Baseline must be BEFORE first treatment (RFXSTDTC), not before RFSTDTC
    3. Baseline is typically last non-missing value before treatment
    
    Args:
        findings_df: Findings domain dataframe (LB, VS, etc.)
        dm_df: Demographics dataframe (contains RFXSTDTC)
        domain: Domain name (e.g., "LB", "VS")
        
    Returns:
        Dictionary with validation results
    """
    issues = []
    blfl_var = f"{domain}BLFL" if f"{domain}BLFL" in findings_df.columns else "BLFL"
    testcd_var = f"{domain}TESTCD"
    dtc_var = f"{domain}DTC"
    
    # Merge reference dates from DM (MUST use DM - dates not in findings domains)
    if "RFXSTDTC" not in dm_df.columns:
        issues.append("WARNING: RFXSTDTC not in DM - cannot validate baseline timing")
        rfxstdtc_available = False
    else:
        findings_df = findings_df.merge(
            dm_df[["USUBJID", "RFXSTDTC"]], 
            on="USUBJID", 
            how="left"
        )
        rfxstdtc_available = True
    
    if blfl_var not in findings_df.columns:
        return {"valid": True, "issues": [], "message": f"No {blfl_var} variable in domain"}
    
    # Check 1: Only one BLFL='Y' per subject per test
    baseline_records = findings_df[findings_df[blfl_var] == "Y"]
    
    if testcd_var in findings_df.columns:
        baseline_counts = baseline_records.groupby(["USUBJID", testcd_var]).size()
        multiple_baselines = baseline_counts[baseline_counts > 1]
        
        for (usubjid, testcd), count in multiple_baselines.items():
            issues.append({
                "rule": "SM0004",
                "severity": "ERROR",
                "message": f"Multiple baseline flags for {testcd} in subject {usubjid} (count: {count})"
            })
    
    # Check 2: Baseline must be before first treatment date (RFXSTDTC)
    if rfxstdtc_available and dtc_var in findings_df.columns:
        baseline_after_treatment = baseline_records[
            (baseline_records[dtc_var] > baseline_records["RFXSTDTC"]) &
            (baseline_records["RFXSTDTC"].notna())
        ]
        
        for _, row in baseline_after_treatment.iterrows():
            issues.append({
                "rule": "SM0006",
                "severity": "WARNING",
                "message": f"Baseline flag set AFTER first treatment for {row.get(testcd_var, 'unknown')} "
                          f"in subject {row['USUBJID']} ({row[dtc_var]} > {row['RFXSTDTC']})"
            })
    
    return {
        "valid": len([i for i in issues if i.get("severity") == "ERROR"]) == 0,
        "issues": issues,
        "baseline_count": len(baseline_records),
        "error_count": len([i for i in issues if i.get("severity") == "ERROR"]),
        "warning_count": len([i for i in issues if i.get("severity") == "WARNING"])
    }
```

### 9. Cross-Domain Validation

**When to use**: Ensuring referential integrity across all domains.

```python
def validate_cross_domain_integrity(datasets: dict) -> dict:
    """
    Validate referential integrity across all SDTM domains.
    
    Args:
        datasets: Dictionary of domain_name: dataframe
        
    Returns:
        Dictionary with validation results
    """
    issues = []
    dm_df = datasets.get("DM")
    
    if dm_df is None:
        return {"valid": False, "issues": ["DM domain not found - cannot validate cross-domain"]}
    
    dm_usubjids = set(dm_df["USUBJID"].unique())
    dm_studyid = dm_df["STUDYID"].iloc[0] if "STUDYID" in dm_df.columns else None
    
    tv_df = datasets.get("TV")
    tv_visitnums = set(tv_df["VISITNUM"].unique()) if tv_df is not None and "VISITNUM" in tv_df.columns else None
    
    for domain_name, domain_df in datasets.items():
        if domain_name == "DM" or domain_df is None:
            continue
        
        # SD0083: Check USUBJID exists in DM
        if "USUBJID" in domain_df.columns:
            domain_usubjids = set(domain_df["USUBJID"].unique())
            orphan_subjects = domain_usubjids - dm_usubjids
            
            if orphan_subjects:
                issues.append({
                    "rule": "SD0083",
                    "severity": "ERROR",
                    "domain": domain_name,
                    "message": f"{len(orphan_subjects)} USUBJID(s) not in DM: {list(orphan_subjects)[:5]}..."
                })
        
        # SD0084: Check STUDYID consistency
        if "STUDYID" in domain_df.columns and dm_studyid:
            inconsistent_studyid = domain_df[domain_df["STUDYID"] != dm_studyid]
            if not inconsistent_studyid.empty:
                issues.append({
                    "rule": "SD0084",
                    "severity": "ERROR",
                    "domain": domain_name,
                    "message": f"STUDYID inconsistent with DM ({inconsistent_studyid['STUDYID'].iloc[0]} vs {dm_studyid})"
                })
        
        # SD0048: Check VISITNUM exists in TV (if TV exists)
        if tv_visitnums and "VISITNUM" in domain_df.columns:
            domain_visitnums = set(domain_df["VISITNUM"].dropna().unique())
            orphan_visits = domain_visitnums - tv_visitnums
            
            if orphan_visits:
                issues.append({
                    "rule": "SD0048",
                    "severity": "WARNING",
                    "domain": domain_name,
                    "message": f"{len(orphan_visits)} VISITNUM(s) not in TV: {list(orphan_visits)[:5]}..."
                })
        
        # Check date logic against DM reference dates
        dtc_vars = [c for c in domain_df.columns if c.endswith("DTC")]
        if dtc_vars and "RFSTDTC" in dm_df.columns:
            domain_with_ref = domain_df.merge(
                dm_df[["USUBJID", "RFSTDTC", "RFENDTC"]], 
                on="USUBJID", 
                how="left"
            )
            
            for dtc_var in dtc_vars:
                # SD0020: Date before RFSTDTC
                before_start = domain_with_ref[
                    (domain_with_ref[dtc_var] < domain_with_ref["RFSTDTC"]) &
                    (domain_with_ref[dtc_var].notna()) &
                    (domain_with_ref["RFSTDTC"].notna())
                ]
                
                if not before_start.empty and domain_name not in ["MH", "SU"]:  # MH/SU can be before
                    issues.append({
                        "rule": "SD0020",
                        "severity": "WARNING",
                        "domain": domain_name,
                        "message": f"{len(before_start)} {dtc_var} values before RFSTDTC"
                    })
    
    return {
        "valid": len([i for i in issues if i.get("severity") == "ERROR"]) == 0,
        "issues": issues,
        "domains_checked": len(datasets),
        "error_count": len([i for i in issues if i.get("severity") == "ERROR"]),
        "warning_count": len([i for i in issues if i.get("severity") == "WARNING"])
    }
```

### 10. Controlled Terminology Validation

**When to use**: Validating all CT-controlled variables.

```python
def validate_controlled_terminology(df: pd.DataFrame, domain: str, 
                                     ct_package: dict) -> dict:
    """
    Validate controlled terminology values.
    
    Args:
        df: Domain dataframe
        domain: Domain name
        ct_package: Dictionary of variable_name: list of valid values
        
    Returns:
        Dictionary with validation results
    """
    issues = []
    ct_variables = {
        "DM": {"SEX": "C66731", "RACE": "C74457", "ETHNIC": "C66790", "ARMCD": None, "COUNTRY": "C66729"},
        "AE": {"AESEV": "C66769", "AESER": "C66742", "AEREL": "C66768", "AEOUT": "C66768", "AEACN": "C66767"},
        "VS": {"VSTESTCD": "C66741", "VSPOS": "C71148", "VSLOC": "C74456"},
        "LB": {"LBTESTCD": "C65047", "LBSPEC": "C78734", "LBMETHOD": "C85492"},
        "EX": {"EXTRT": None, "EXDOSFRM": "C66726", "EXDOSFRQ": "C71113", "EXROUTE": "C66729"},
        "CM": {"CMDOSFRM": "C66726", "CMROUTE": "C66729"},
        "MH": {"MHPRESP": "C66742", "MHOCCUR": "C66742"},
    }
    
    domain_ct = ct_variables.get(domain, {})
    
    for var, codelist_id in domain_ct.items():
        if var not in df.columns:
            continue
        
        valid_values = ct_package.get(var, ct_package.get(codelist_id, []))
        
        if not valid_values:
            issues.append({
                "rule": "CT2001",
                "severity": "WARNING",
                "variable": var,
                "message": f"No CT values loaded for {var} (codelist {codelist_id})"
            })
            continue
        
        # Check for invalid values
        domain_values = df[var].dropna().unique()
        invalid_values = [v for v in domain_values if v not in valid_values]
        
        for invalid in invalid_values:
            # Check if this is an extensible codelist
            extensible = codelist_id in EXTENSIBLE_CODELISTS if codelist_id else False
            
            if extensible:
                issues.append({
                    "rule": "CT0046",
                    "severity": "WARNING",
                    "variable": var,
                    "value": invalid,
                    "message": f"Value '{invalid}' not in standard CT (extensible codelist - document in SDRG)"
                })
            else:
                issues.append({
                    "rule": "CT0001",
                    "severity": "ERROR",
                    "variable": var,
                    "value": invalid,
                    "message": f"Value '{invalid}' not in controlled terminology for {var}"
                })
    
    return {
        "valid": len([i for i in issues if i.get("severity") == "ERROR"]) == 0,
        "issues": issues,
        "variables_checked": len(domain_ct),
        "error_count": len([i for i in issues if i.get("severity") == "ERROR"]),
        "warning_count": len([i for i in issues if i.get("severity") == "WARNING"])
    }

# Extensible codelists that allow sponsor-defined values
EXTENSIBLE_CODELISTS = {
    "C66729",  # Country
    "C66768",  # Outcome
    "C71113",  # Frequency
    # Add other extensible codelists
}
```

### 11. Quality Control Procedures

**When to use**: Verifying transformation accuracy.

#### QC Checklist

**Pre-Transformation QC (Phase 2)**
- [ ] Source file row counts documented
- [ ] All expected source files present
- [ ] No unexpected null values in key fields
- [ ] Date formats identified and documented
- [ ] Duplicate records identified
- [ ] Character encoding verified (UTF-8)

**Post-Transformation QC (Phase 6)**
- [ ] Row count reconciliation (source vs target)
- [ ] Key variable population rates >= 95%
- [ ] CT value mapping accuracy verified
- [ ] ISO 8601 date conversion validated
- [ ] USUBJID uniqueness verified per domain
- [ ] --SEQ uniqueness verified within USUBJID
- [ ] Cross-domain referential integrity confirmed
- [ ] Baseline flag logic verified (one per test per subject)
- [ ] Study day calculations verified (--DY, --STDY, --ENDY)
- [ ] EPOCH derivation accuracy confirmed

**Trial Design QC**
- [ ] TS domain has all 14 required parameters
- [ ] TA/TE/TV/TI domains consistent with protocol
- [ ] ARMCD/ARM values consistent across domains
- [ ] VISITNUM values consistent with TV domain

**Define-XML QC**
- [ ] All datasets have ItemGroupDef
- [ ] All variables have ItemDef with Origin
- [ ] All CT variables have CodeList reference
- [ ] def:leaf elements link to actual files
- [ ] Schema validation passes (define.xsd)

**Pre-Submission QC**
- [ ] Pinnacle 21 (or CDISC CORE) validation: 0 errors
- [ ] All warnings documented in SDRG
- [ ] Define-XML validates against datasets
- [ ] SDRG complete with all discrepancies explained
- [ ] aCRF complete and linked in Define-XML
- [ ] Dataset file sizes within FDA limits

#### QC Report Template

```json
{
  "qc_report": {
    "study_id": "STUDY-001",
    "domain": "DM",
    "executed_at": "2024-01-15T14:30:00Z",
    "executed_by": "ETL System v1.0",
    "checks": [
      {
        "check_id": "QC001",
        "category": "Reconciliation",
        "description": "Row count reconciliation",
        "source_count": 150,
        "target_count": 150,
        "difference": 0,
        "status": "PASS"
      },
      {
        "check_id": "QC002",
        "category": "Uniqueness",
        "description": "USUBJID uniqueness",
        "total_records": 150,
        "unique_records": 150,
        "duplicates": 0,
        "status": "PASS"
      },
      {
        "check_id": "QC003",
        "category": "Completeness",
        "description": "Required variable population",
        "variable": "RFSTDTC",
        "population_rate": 98.7,
        "threshold": 95.0,
        "status": "PASS"
      },
      {
        "check_id": "QC004",
        "category": "Conformance",
        "description": "SEX controlled terminology",
        "valid_values": ["M", "F", "U"],
        "invalid_found": [],
        "status": "PASS"
      }
    ],
    "summary": {
      "total_checks": 4,
      "passed": 4,
      "failed": 0,
      "warnings": 0
    },
    "overall_status": "PASS"
  }
}
```

### 12. Regulatory Submission Requirements

**When to use**: Preparing data for FDA/EMA submission.

#### FDA eCTD Requirements

| Component | Format | Location | Required |
|-----------|--------|----------|----------|
| SDTM Datasets | SAS XPT v5 | m5/datasets/tabulations/sdtm | Yes |
| Define-XML | XML 2.1 | m5/datasets/tabulations/sdtm | Yes |
| Study Data Reviewer's Guide (SDRG) | PDF | m5/datasets/tabulations/sdtm | Yes |
| Annotated CRF (aCRF) | PDF | m5/datasets/tabulations/sdtm | Yes |

#### Dataset Technical Requirements

| Requirement | Specification | Notes |
|-------------|---------------|-------|
| File format | SAS Transport (XPT) v5 | Created by SAS XPORT engine |
| Dataset names | Lowercase, ≤8 characters | e.g., dm.xpt, ae.xpt |
| Variable names | Uppercase, ≤8 characters | Per SDTMIG |
| Character length | ≤200 characters | SDTMIG 3.2+ requirement |
| File size | No hard limit; split if >5GB | FDA recommends splitting large datasets |
| Encoding | ASCII | SAS Transport limitation |

#### SDRG Requirements for Unresolved Warnings

All Pinnacle 21 warnings that are not resolved MUST be documented in SDRG with:
1. Rule ID and description
2. Affected domain(s) and record count
3. Justification for not resolving
4. Impact assessment

Example SDRG entry:
```
Rule SD0020 - Date/time precedes RFSTDTC
Domain: MH (Medical History)
Records: 45 of 320 (14%)
Justification: Medical history events are expected to occur before study 
start (RFSTDTC). These represent pre-existing conditions collected at 
screening that occurred prior to study enrollment.
Impact: No impact on data integrity. Expected behavior for MH domain.
```

### 13. Validation Tools

#### Available Tools

| Tool | Type | Use Case |
|------|------|----------|
| Pinnacle 21 Community | GUI | Manual validation, free |
| Pinnacle 21 Enterprise | API | Automated pipelines, licensed |
| CDISC CORE | CLI/Python | Open-source alternative |
| SAS Clinical Standards Toolkit | SAS | SAS environments |

#### CDISC CORE (Open Source Alternative)

```bash
# Install CDISC CORE
pip install cdisc-rules-engine

# Run validation
core validate \
  --standard SDTMIG \
  --version 3.4 \
  --data ./sdtm_datasets/ \
  --define ./define.xml \
  --output ./validation_report.json
```

#### Custom Validation Framework

```python
class SDTMValidator:
    """
    Comprehensive SDTM validation framework.
    """
    
    def __init__(self, datasets: dict, define_xml: str = None, 
                 ct_package: dict = None):
        self.datasets = datasets
        self.define_xml = define_xml
        self.ct_package = ct_package or {}
        self.results = {}
    
    def run_full_validation(self) -> dict:
        """Run all validation layers."""
        
        # Layer 1: Structural
        self.results["structural"] = self._validate_structural()
        
        # Layer 2: CDISC Conformance
        self.results["cdisc_conformance"] = self._validate_cdisc()
        
        # Layer 3: Cross-Domain
        self.results["cross_domain"] = validate_cross_domain_integrity(self.datasets)
        
        # Layer 4: Trial Design
        self.results["trial_design"] = self._validate_trial_design()
        
        # Layer 5: Semantic
        self.results["semantic"] = self._validate_semantic()
        
        # Layer 6: Define-XML
        if self.define_xml:
            self.results["define_xml"] = self._validate_define_xml()
        
        # Calculate overall score
        self.results["score"] = calculate_conformance_score(self.results)
        
        return self.results
    
    def _validate_structural(self) -> dict:
        """Validate required variables and data types."""
        issues = []
        
        required_vars = {
            "DM": ["STUDYID", "DOMAIN", "USUBJID", "SUBJID", "RFSTDTC"],
            "AE": ["STUDYID", "DOMAIN", "USUBJID", "AESEQ", "AETERM", "AEDECOD", "AESTDTC"],
            "LB": ["STUDYID", "DOMAIN", "USUBJID", "LBSEQ", "LBTESTCD", "LBTEST", "LBORRES"],
            "VS": ["STUDYID", "DOMAIN", "USUBJID", "VSSEQ", "VSTESTCD", "VSTEST", "VSORRES"],
            "EX": ["STUDYID", "DOMAIN", "USUBJID", "EXSEQ", "EXTRT", "EXDOSE", "EXSTDTC"],
            "TS": ["STUDYID", "DOMAIN", "TSSEQ", "TSPARMCD", "TSPARM", "TSVAL"],
        }
        
        for domain_name, domain_df in self.datasets.items():
            domain_required = required_vars.get(domain_name, [])
            
            for var in domain_required:
                if var not in domain_df.columns:
                    issues.append({
                        "rule": "SD0006",
                        "severity": "ERROR",
                        "domain": domain_name,
                        "variable": var,
                        "message": f"Required variable {var} missing from {domain_name}"
                    })
            
            # Check --SEQ uniqueness
            seq_var = f"{domain_name}SEQ"
            if seq_var in domain_df.columns and "USUBJID" in domain_df.columns:
                dup_seq = domain_df.groupby(["USUBJID", seq_var]).size()
                dups = dup_seq[dup_seq > 1]
                if not dups.empty:
                    issues.append({
                        "rule": "SD0063",
                        "severity": "ERROR",
                        "domain": domain_name,
                        "message": f"{len(dups)} duplicate {seq_var} values within USUBJID"
                    })
        
        total = sum(len(v) for v in required_vars.values())
        errors = len([i for i in issues if i.get("severity") == "ERROR"])
        
        return {
            "total_checks": total,
            "passed_checks": total - errors,
            "error_count": errors,
            "warning_count": len([i for i in issues if i.get("severity") == "WARNING"]),
            "issues": issues
        }
    
    def _validate_trial_design(self) -> dict:
        """Validate trial design domains, especially TS."""
        issues = []
        
        ts_df = self.datasets.get("TS")
        if ts_df is None:
            issues.append({
                "rule": "SD1050",
                "severity": "ERROR",
                "domain": "TS",
                "message": "TS domain is REQUIRED but not found - SUBMISSION BLOCKER"
            })
            return {
                "total_checks": 1,
                "passed_checks": 0,
                "error_count": 1,
                "warning_count": 0,
                "issues": issues
            }
        
        # Validate TS domain
        ts_result = validate_ts_domain(ts_df)
        issues.extend([{"rule": "SD1050", "severity": "ERROR", "domain": "TS", 
                       "message": i} for i in ts_result.get("issues", [])])
        
        total = ts_result.get("required_count", 14)
        passed = ts_result.get("present_count", 0)
        
        return {
            "total_checks": total,
            "passed_checks": passed,
            "error_count": len([i for i in issues if i.get("severity") == "ERROR"]),
            "warning_count": len([i for i in issues if i.get("severity") == "WARNING"]),
            "issues": issues
        }
    
    def _validate_cdisc(self) -> dict:
        """Validate CDISC conformance (CT, dates, naming)."""
        issues = []
        total_checks = 0
        passed_checks = 0
        
        for domain_name, domain_df in self.datasets.items():
            # Validate controlled terminology
            ct_result = validate_controlled_terminology(
                domain_df, domain_name, self.ct_package
            )
            issues.extend(ct_result.get("issues", []))
            
            # Validate ISO 8601 dates
            date_vars = [c for c in domain_df.columns if c.endswith("DTC")]
            date_result = validate_date_variables(domain_df, date_vars)
            issues.extend(date_result.get("issues", []))
            
            total_checks += date_result.get("total_checks", 0)
            passed_checks += date_result.get("passed_checks", 0)
        
        return {
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "error_count": len([i for i in issues if i.get("severity") == "ERROR"]),
            "warning_count": len([i for i in issues if i.get("severity") == "WARNING"]),
            "issues": issues
        }
    
    def _validate_semantic(self) -> dict:
        """Validate business logic and clinical plausibility."""
        issues = []
        
        dm_df = self.datasets.get("DM")
        
        # Validate baseline flags in findings domains
        for domain_name in ["LB", "VS", "EG"]:
            domain_df = self.datasets.get(domain_name)
            if domain_df is not None and dm_df is not None:
                bl_result = validate_baseline_flags(domain_df, dm_df, domain_name)
                issues.extend(bl_result.get("issues", []))
        
        # SM0001: End date before start date
        for domain_name, domain_df in self.datasets.items():
            stdtc = f"{domain_name}STDTC" if f"{domain_name}STDTC" in domain_df.columns else None
            endtc = f"{domain_name}ENDTC" if f"{domain_name}ENDTC" in domain_df.columns else None
            
            if stdtc and endtc:
                invalid_dates = domain_df[
                    (domain_df[endtc] < domain_df[stdtc]) &
                    (domain_df[stdtc].notna()) &
                    (domain_df[endtc].notna())
                ]
                
                if not invalid_dates.empty:
                    issues.append({
                        "rule": "SM0001",
                        "severity": "ERROR",
                        "domain": domain_name,
                        "message": f"{len(invalid_dates)} records with end date before start date"
                    })
        
        return {
            "total_checks": len(self.datasets) * 3,  # Approximate
            "passed_checks": len(self.datasets) * 3 - len(issues),
            "error_count": len([i for i in issues if i.get("severity") == "ERROR"]),
            "warning_count": len([i for i in issues if i.get("severity") == "WARNING"]),
            "issues": issues
        }
    
    def _validate_define_xml(self) -> dict:
        """Validate Define-XML against actual datasets."""
        # Implementation would parse Define-XML and cross-reference
        # This is a placeholder for the structure
        return {
            "total_checks": 0,
            "passed_checks": 0,
            "error_count": 0,
            "warning_count": 0,
            "issues": []
        }
    
    def generate_report(self, output_path: str = None) -> dict:
        """Generate validation report."""
        report = {
            "validation_report": {
                "generated_at": datetime.now().isoformat(),
                "overall_score": self.results.get("score", {}).get("overall_score", 0),
                "submission_ready": self.results.get("score", {}).get("submission_ready", False),
                "blockers": self.results.get("score", {}).get("blockers", []),
                "layers": {}
            }
        }
        
        for layer, result in self.results.items():
            if layer != "score":
                report["validation_report"]["layers"][layer] = {
                    "error_count": result.get("error_count", 0),
                    "warning_count": result.get("warning_count", 0),
                    "issues": result.get("issues", [])
                }
        
        if output_path:
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)
        
        return report
```

### 14. Problem Solving and Debugging

**When to use**: Resolving validation errors and data quality issues.

#### Common Error Resolution

| Error | Rule ID | Root Cause | Resolution |
|-------|---------|-----------|------------|
| CT value not found | CT0001/CT0046 | Raw data uses non-standard values | Create mapping table to CT values; document extensions in SDRG |
| Invalid date format | SD0020 | Multiple date formats in source | Apply date parsing with format detection; validate partial dates |
| Missing USUBJID | SD0083 | Join failed | Verify USUBJID derivation; check source ID mapping |
| Duplicate --SEQ | SD0063 | Incorrect sequence generation | Reset sequence per USUBJID; sort before sequencing |
| Referential integrity | SD0048/SD0083 | Parent record missing | Add to parent domain; exclude orphan records with documentation |
| Multiple baselines | SM0004 | Incorrect BLFL derivation | Apply last-value-before-treatment logic per test |
| Missing TS parameter | SD1050 | Protocol information not mapped | Extract from protocol; create TS records |

#### Debugging Workflow

```
1. IDENTIFY
   └── Read Pinnacle 21/CORE report
   └── Note rule ID, severity, domain, record count

2. CLASSIFY
   └── ERROR → Must fix (submission blocker)
   └── WARNING → Evaluate and document
   └── NOTICE → Best practice consideration

3. ISOLATE
   └── Filter dataset to affected records
   └── Export sample for analysis
   └── Check source data for root cause

4. TRACE
   └── Review transformation logic
   └── Check mapping specifications
   └── Verify CT version alignment

5. FIX
   └── Update transformation code
   └── Adjust mapping table
   └── Correct source data (if applicable)

6. VERIFY
   └── Re-run validation on affected domain
   └── Confirm error count reduced to 0
   └── Document fix in change log

7. DOCUMENT
   └── For unresolved WARNINGs: Add SDRG entry
   └── Include: Rule ID, justification, impact assessment
```

## Instructions for Agent

When the agent receives a validation task:

### 1. Phase 2 (Raw Data Validation)
- Run structural checks on source files
- Identify missing required fields per target SDTM domain
- Flag data quality issues (nulls, duplicates, format issues)
- Document date formats present in source
- Generate raw data quality report

### 2. Phase 6 (Target Data Validation)
- Run multi-layer validation framework
- Execute ALL validation layers:
  1. Structural validation
  2. CDISC conformance (CT, ISO 8601)
  3. Cross-domain referential integrity
  4. Trial design (TS domain required)
  5. Semantic (baseline flags, date logic)
  6. Define-XML consistency
- Calculate conformance score
- Identify submission blockers (errors)
- Generate comprehensive validation report

### 3. Self-Correction Loop
```
IF score < 95% OR critical_errors > 0:
    1. Analyze failed rules by severity
    2. Prioritize: ERRORS first, then WARNINGS
    3. Generate correction feedback
    4. Retry transformation (max 3 iterations)
    5. IF still failing after 3 attempts:
       → Flag specific issues for human review
       → Do NOT proceed with submission
```

### 4. Define-XML Generation
- Create from dataset metadata (variables, types, lengths)
- Include ALL required elements:
  - ItemGroupDef with def:leaf for each dataset
  - ItemDef with def:Origin for each variable
  - CodeList for all CT-controlled variables
  - MethodDef for derived variables
  - def:ValueListDef for value-level metadata
- Reference CDISC CT version explicitly
- Validate against Define-XML 2.1 schema

### 5. Pre-Submission Checklist
- [ ] Conformance score >= 95%
- [ ] Zero critical errors
- [ ] TS domain complete with all required parameters
- [ ] All WARNINGS documented in SDRG
- [ ] Define-XML validates against datasets
- [ ] SDRG includes discrepancy explanations
- [ ] aCRF linked in Define-XML
- [ ] Dataset files in correct location

### 6. Code Quality Requirements
- Use `pd.concat()` instead of deprecated `df.append()`
- Merge reference dates from DM before using RFSTDTC/RFXSTDTC
- Use RFXSTDTC (first treatment) for baseline determination, not RFSTDTC
- Handle pandas SettingWithCopyWarning appropriately
- Include proper error handling for missing variables

## Available Tools

| Tool | Function | Phase |
|------|----------|-------|
| `validate_structural` | Check required variables, types, lengths | 2, 6 |
| `validate_cdisc_conformance` | Check CT values, ISO 8601 dates | 6 |
| `validate_cross_domain` | Check referential integrity | 6 |
| `validate_trial_design` | Validate TS, TA, TE, TV, TI domains | 6 |
| `calculate_compliance_score` | Calculate weighted overall score | 6 |
| `validate_domain` | High-level domain validation wrapper | 6 |
| `get_validation_rules` | Retrieve rules from knowledge base | All |
| `generate_define_xml` | Create Define-XML 2.1 from metadata | 5 |
| `validate_define_xml` | Validate Define-XML against datasets | 6 |

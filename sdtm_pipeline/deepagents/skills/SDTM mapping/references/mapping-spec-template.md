# SDTM Mapping Specification Template

## Overview

This document provides templates for creating SDTM mapping specifications - the critical documentation that defines how source/raw data transforms into SDTM datasets.

---

## Mapping Specification Components

### 1. Dataset-Level Specification
| Field | Description | Example |
|-------|-------------|---------|
| Domain | SDTM domain code | AE |
| Description | Dataset description | Adverse Events |
| Class | Observation class | Events |
| Structure | One record per... | One record per adverse event per subject |
| Keys | Sorting variables | STUDYID, USUBJID, AESEQ |
| Location | Output file path | /sdtm/ae.xpt |
| IG Version | SDTM IG version | 3.4 |

### 2. Variable-Level Specification

**Template Columns:**
| Column | Description |
|--------|-------------|
| Variable | SDTM variable name (--TESTCD) |
| Label | Variable label (40 char max) |
| Type | Char or Num |
| Length | Maximum character length |
| Core | Req/Exp/Perm |
| Origin | CRF/Derived/Assigned/Protocol |
| Source | Source dataset.variable |
| Derivation | Mapping rule/logic |
| Codelist | CT codelist if applicable |
| Comments | Additional notes |

---

## Example: AE Domain Mapping Specification

### Dataset Metadata
```yaml
Domain: AE
Description: Adverse Events
Class: Events
Structure: One record per adverse event per subject
Keys: STUDYID, USUBJID, AEDTC, AETERM, AESEQ
SDTM IG Version: 3.4
```

### Variable Mappings

| Variable | Label | Type | Len | Core | Origin | Source | Derivation | Codelist |
|----------|-------|------|-----|------|--------|--------|------------|----------|
| STUDYID | Study Identifier | Char | 12 | Req | Assigned | - | "ABC-123" constant | - |
| DOMAIN | Domain Abbreviation | Char | 2 | Req | Assigned | - | "AE" constant | - |
| USUBJID | Unique Subject ID | Char | 20 | Req | Derived | DM.USUBJID | Join on SUBJID | - |
| AESEQ | Sequence Number | Num | 8 | Req | Derived | - | Monotonically increasing integer per USUBJID ordered by AESTDTC | - |
| AETERM | Reported Term | Char | 200 | Req | CRF | raw_ae.ae_term | Direct mapping, uppercase | - |
| AELLT | Lowest Level Term | Char | 200 | Perm | Derived | MedDRA | MedDRA coding of AETERM | MedDRA |
| AELLTCD | Lowest Level Term Code | Num | 8 | Perm | Derived | MedDRA | LLT code from MedDRA | MedDRA |
| AEDECOD | Dictionary-Derived Term | Char | 200 | Req | Derived | MedDRA | MedDRA Preferred Term | MedDRA |
| AEPTCD | Preferred Term Code | Num | 8 | Perm | Derived | MedDRA | PT code from MedDRA | MedDRA |
| AEHLT | High Level Term | Char | 200 | Perm | Derived | MedDRA | MedDRA HLT | MedDRA |
| AEHLTCD | High Level Term Code | Num | 8 | Perm | Derived | MedDRA | HLT code from MedDRA | MedDRA |
| AEHLGT | High Level Group Term | Char | 200 | Perm | Derived | MedDRA | MedDRA HLGT | MedDRA |
| AEHLGTCD | High Level Group Term Code | Num | 8 | Perm | Derived | MedDRA | HLGT code from MedDRA | MedDRA |
| AEBODSYS | Body System or Organ Class | Char | 200 | Exp | Derived | MedDRA | MedDRA System Organ Class | MedDRA |
| AESOC | Primary SOC | Char | 200 | Perm | Derived | MedDRA | Primary SOC for PT | MedDRA |
| AESOCCD | SOC Code | Num | 8 | Perm | Derived | MedDRA | SOC code from MedDRA | MedDRA |
| AESEV | Severity/Intensity | Char | 20 | Perm | CRF | raw_ae.severity | Map: 1="MILD", 2="MODERATE", 3="SEVERE" | (AESEV) |
| AESER | Serious Event | Char | 1 | Exp | CRF | raw_ae.serious_yn | Map: Yes="Y", No="N" | (NY) |
| AEACN | Action Taken | Char | 50 | Exp | CRF | raw_ae.action | Map to ACN codelist | (ACN) |
| AEREL | Causality | Char | 50 | Perm | CRF | raw_ae.relationship | Direct mapping, uppercase | - |
| AEOUT | Outcome | Char | 50 | Perm | CRF | raw_ae.outcome | Map to OUT codelist | (OUT) |
| AESTDTC | Start Date/Time | Char | 19 | Exp | CRF | raw_ae.start_date | Convert to ISO 8601: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS | - |
| AEENDTC | End Date/Time | Char | 19 | Perm | CRF | raw_ae.end_date | Convert to ISO 8601 | - |
| AESTDY | Study Day of Start | Num | 8 | Perm | Derived | AESTDTC, DM.RFSTDTC | (AESTDTC - RFSTDTC) + 1 if >= RFSTDTC, else (AESTDTC - RFSTDTC) | - |
| AEENDY | Study Day of End | Num | 8 | Perm | Derived | AEENDTC, DM.RFSTDTC | Same logic as AESTDY | - |
| AESDTH | Results in Death | Char | 1 | Perm | CRF | raw_ae.death_yn | Map: Yes="Y", No="N" | (NY) |
| AESHOSP | Requires Hospitalization | Char | 1 | Perm | CRF | raw_ae.hosp_yn | Map: Yes="Y", No="N" | (NY) |
| AESLIFE | Life Threatening | Char | 1 | Perm | CRF | raw_ae.life_threat_yn | Map: Yes="Y", No="N" | (NY) |
| AESDISAB | Disability | Char | 1 | Perm | CRF | raw_ae.disability_yn | Map: Yes="Y", No="N" | (NY) |
| AESCONG | Congenital Anomaly | Char | 1 | Perm | CRF | raw_ae.congenital_yn | Map: Yes="Y", No="N" | (NY) |
| AESMIE | Medically Important | Char | 1 | Perm | CRF | raw_ae.med_imp_yn | Map: Yes="Y", No="N" | (NY) |
| AECONTRT | Concom Trt Given | Char | 1 | Perm | CRF | raw_ae.treatment_yn | Map: Yes="Y", No="N" | (NY) |
| AETOXGR | Toxicity Grade | Char | 5 | Perm | CRF | raw_ae.ctcae_grade | Direct mapping | - |

---

## Derivation Rule Documentation

### Standard Derivation Patterns

**1. Date Conversion (ISO 8601):**
```
Input: 15-Jan-2024 or 01/15/2024 or 2024-01-15
Output: 2024-01-15

Rule:
- Parse source date format
- Output as YYYY-MM-DD
- For datetime: YYYY-MM-DDTHH:MM:SS
- For partial dates:
  - Year only: YYYY
  - Year-Month: YYYY-MM
```

**2. Study Day Calculation:**
```
IF AESTDTC >= RFSTDTC THEN
  AESTDY = (AESTDTC - RFSTDTC) + 1
ELSE
  AESTDY = (AESTDTC - RFSTDTC)

Note: Day 0 does not exist. Dates before RFSTDTC are negative.
```

**3. Sequence Number:**
```
AESEQ = Monotonically increasing integer
  - Within USUBJID
  - Ordered by: AESTDTC, AETERM (secondary)
  - Starting at 1
```

**4. Controlled Terminology Mapping:**
```
Source Value    → SDTM Value (Codelist)
-------------------------------------
1, Mild        → MILD (AESEV)
2, Moderate    → MODERATE (AESEV)
3, Severe      → SEVERE (AESEV)
Yes, Y, 1      → Y (NY)
No, N, 0       → N (NY)
```

---

## Mapping Specification Best Practices

### 1. Document All Mappings
- Every variable needs documented origin
- Complex derivations need pseudocode
- Include edge case handling

### 2. Version Control
- Include spec version and date
- Track changes from protocol amendments
- Link to source IG version

### 3. Source Traceability
- Exact source field names
- CRF page/form reference
- External data transfer spec reference

### 4. Validation Rules
- Expected vs. Permissible designation
- Required format patterns
- Acceptable value ranges

---

## Annotated CRF Guidance

### aCRF Purpose
Visual mapping of CRF fields to SDTM variables

### Annotation Format
```
[Domain.Variable]
Example: [AE.AETERM]
         [AE.AESTDTC]
```

### Best Practices
1. One annotation per field
2. Include SUPPQUAL annotations
3. Note when multiple domains use same field
4. Mark derived variables with "DERIVED"

---

## Quality Control Checklist

### Mapping Spec Review
- [ ] All required variables mapped
- [ ] Variable lengths appropriate
- [ ] CT codelists identified
- [ ] Derivation rules clear and testable
- [ ] Source documentation complete
- [ ] Define.xml alignment verified

### Programming Review
- [ ] Mapping matches specification
- [ ] Derivations produce expected results
- [ ] CT values validated
- [ ] Missing value handling correct
- [ ] Sort order correct

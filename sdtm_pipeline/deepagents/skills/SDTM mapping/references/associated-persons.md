# Associated Persons Domains

## Overview

Associated Persons (AP) domains capture data about individuals related to the study subject but who are not subjects themselves. Common examples include:
- Family members in genetics studies
- Healthcare providers
- Caregivers providing assessments

---

## AP Domain Structure

### Naming Convention
- APXX where XX is the parent domain abbreviation
- APDM = Associated Persons Demographics
- APFA = Associated Persons Findings About
- APMH = Associated Persons Medical History
- APSC = Associated Persons Subject Characteristics

### Key Identifier Variables
| Variable | Label | Description |
|----------|-------|-------------|
| STUDYID | Study Identifier | Standard |
| DOMAIN | Domain Abbreviation | "APXX" |
| USUBJID | Subject Unique ID | The study subject (not the AP) |
| APID | Associated Person ID | Unique ID for the associated person |
| RSUBJID | Related Subject ID | Optional: links to another subject |
| SREL | Subject Relationship | Relationship to USUBJID |

---

## APDM - Associated Persons Demographics

**Purpose:** Demographic information about associated persons.

### Structure
| Variable | Label | Type | Core |
|----------|-------|------|------|
| STUDYID | Study Identifier | Char | Req |
| DOMAIN | Domain Abbreviation | Char | Req |
| USUBJID | Subject Unique ID | Char | Req |
| APID | Associated Person ID | Char | Req |
| SREL | Subject Relationship | Char | Req |
| RSUBJID | Related Subject ID | Char | Perm |
| APSEX | Sex of Associated Person | Char | Perm |
| APBRTHDTC | Birth Date of AP | Char | Perm |
| APAGE | Age of Associated Person | Num | Perm |
| APAGEU | Age Units | Char | Perm |
| APRACE | Race | Char | Perm |
| APETHNIC | Ethnicity | Char | Perm |

### Relationship Values (SREL)
| Value | Description |
|-------|-------------|
| PARENT | Parent of subject |
| MOTHER | Biological mother |
| FATHER | Biological father |
| SIBLING | Brother or sister |
| CHILD | Offspring of subject |
| SPOUSE | Married partner |
| PARTNER | Unmarried partner |
| CAREGIVER | Person providing care |
| HEALTHCARE PROVIDER | Physician, nurse, etc. |
| LEGAL GUARDIAN | Legal guardian |
| OTHER | Other relationship |

### Example
```
USUBJID         APID    SREL      APSEX  APAGE  APAGEU
ABC123-001-001  AP001   MOTHER    F      65     YEARS
ABC123-001-001  AP002   FATHER    M      68     YEARS
ABC123-001-001  AP003   SIBLING   M      42     YEARS
```

---

## APMH - Associated Persons Medical History

**Purpose:** Medical history of associated persons (genetics, family history studies).

### Structure
| Variable | Label | Type | Core |
|----------|-------|------|------|
| STUDYID | Study Identifier | Char | Req |
| DOMAIN | Domain Abbreviation | Char | Req |
| USUBJID | Subject Unique ID | Char | Req |
| APID | Associated Person ID | Char | Req |
| APMHSEQ | Sequence Number | Num | Req |
| SREL | Subject Relationship | Char | Req |
| APMHTERM | Reported Term | Char | Req |
| APMHDECOD | Dictionary-Derived Term | Char | Perm |
| APMHBODSYS | Body System or Organ Class | Char | Perm |
| APMHSTDTC | Start Date/Time | Char | Perm |
| APMHENDTC | End Date/Time | Char | Perm |
| APMHSEV | Severity | Char | Perm |

### Example: Family History Study
```
USUBJID         APID    SREL     APMHTERM             APMHDECOD
ABC123-001-001  AP001   MOTHER   Breast cancer        BREAST CANCER
ABC123-001-001  AP001   MOTHER   Diabetes             DIABETES MELLITUS
ABC123-001-001  AP002   FATHER   Heart attack         MYOCARDIAL INFARCTION
ABC123-001-001  AP003   SIBLING  Colorectal cancer    COLORECTAL CANCER
```

---

## APSC - Associated Persons Subject Characteristics

**Purpose:** Characteristics of associated persons not captured elsewhere.

### Structure
| Variable | Label | Type |
|----------|-------|------|
| STUDYID | Study Identifier | Char |
| DOMAIN | Domain Abbreviation | Char |
| USUBJID | Subject Unique ID | Char |
| APID | Associated Person ID | Char |
| APSCSEQ | Sequence Number | Num |
| SREL | Subject Relationship | Char |
| APSCTESTCD | Characteristic Short Name | Char |
| APSCTEST | Characteristic Name | Char |
| APSCORRES | Result (Original) | Char |
| APSCSTRESC | Result (Standardized) | Char |

---

## APFA - Associated Persons Findings About

**Purpose:** Findings about associated persons related to events or interventions.

### Common Uses
- Caregiver assessments of patient function
- Healthcare provider evaluations
- Family member reports

---

## When to Use AP Domains

### Use AP Domains When:
1. **Family history studies** - Genetic predisposition research
2. **Caregiver studies** - Assessments by non-subjects
3. **Pediatric studies** - Parent-reported outcomes
4. **Observational studies** - Family member data collection

### Do NOT Use AP Domains When:
- Data belongs in APDM but is about the subject (use DM)
- Family history is simple checklist (consider MH with MHCAT="FAMILY HISTORY")
- Associated person is also enrolled as subject (use RSUBJID for linking)

---

## Linking AP to Subject Data

### Using RSUBJID
When an associated person is also a study subject:
```
USUBJID         APID    SREL     RSUBJID
ABC123-001-001  AP001   MOTHER   ABC123-001-010
```
This links subject 001's mother to subject 010 in the same study.

### Using RELREC
For complex relationships not captured by RSUBJID:
```
RDOMAIN  USUBJID         IDVAR     IDVARVAL  RELID
DM       ABC123-001-001  USUBJID   ABC123-001-001  GENETIC01
APDM     ABC123-001-001  APID      AP001           GENETIC01
APMH     ABC123-001-001  APMHSEQ   1               GENETIC01
```

---

## Controlled Terminology for AP Domains

AP domains use the same controlled terminology as their parent domains:
- APSEX uses SEX codelist (C66731)
- APRACE uses RACE codelist (C74457)
- APETHNIC uses ETHNIC codelist (C66790)
- APMHDECOD uses MedDRA (when applicable)

---

## Validation Considerations

1. **APID Uniqueness**: APID must be unique within USUBJID
2. **SREL Required**: Relationship must be specified
3. **Consistent APID**: Same associated person should have same APID across domains
4. **RSUBJID Validity**: If used, must exist in DM.USUBJID

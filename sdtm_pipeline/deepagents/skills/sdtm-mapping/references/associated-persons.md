# Associated Persons Domains

Associated Persons domains capture data about people related to but not enrolled in the study (e.g., partners, family members in reproductive studies).

## General Structure

Associated Persons domains follow the same structure as subject domains but:
- Use APID (Associated Person Identifier) instead of USUBJID
- Link to subjects via RSUBJID (Related Subject ID)
- Domain names prefixed with "AP" (e.g., APDM, APAE)

---

## APDM - Associated Persons Demographics

**Purpose:** Demographics for persons associated with study subjects.

**Key Variables:**

| Variable | Label | Type | Required | Notes |
|----------|-------|------|----------|-------|
| STUDYID | Study Identifier | Char | Req | |
| DOMAIN | Domain Abbreviation | Char | Req | APDM |
| APID | Associated Person Identifier | Char | Req | Unique within study |
| RSUBJID | Related Subject Identifier | Char | Req | Links to USUBJID |
| SREL | Subject Relationship | Char | Req | SPOUSE, PARTNER, etc. |
| BRTHDTC | Date of Birth | Char | Perm | |
| AGE | Age | Num | Exp | |
| AGEU | Age Units | Char | Exp | YEARS, MONTHS |
| SEX | Sex | Char | Req | |
| RACE | Race | Char | Perm | |
| ETHNIC | Ethnicity | Char | Perm | |

**SREL Values:**
- SPOUSE
- PARTNER
- BIOLOGICAL FATHER
- BIOLOGICAL MOTHER
- OFFSPRING
- SIBLING
- OTHER FAMILY MEMBER

---

## APAE - Associated Persons Adverse Events

**Purpose:** Adverse events for associated persons (e.g., birth defects in offspring).

**Key Variables:**

| Variable | Label | Type | Required |
|----------|-------|------|----------|
| STUDYID | Study Identifier | Char | Req |
| DOMAIN | Domain Abbreviation | Char | Req |
| APID | Associated Person Identifier | Char | Req |
| AESEQ | Sequence Number | Num | Req |
| AETERM | Reported Term for AE | Char | Req |
| AEDECOD | Dictionary-Derived Term | Char | Perm |
| AESER | Serious Event | Char | Exp |
| AESTDTC | Start Date/Time | Char | Exp |
| AEENDTC | End Date/Time | Char | Perm |

---

## APSC - Associated Persons Subject Characteristics

**Purpose:** Characteristics of associated persons.

---

## APMH - Associated Persons Medical History

**Purpose:** Medical history for associated persons.

---

## Use Cases

**Reproductive Toxicology Studies:**
- Partner exposure history
- Pregnancy outcomes
- Infant/offspring follow-up

**Genetic Studies:**
- Family member genotypes
- Pedigree data

**Caregiver Studies:**
- Caregiver burden assessments
- Caregiver-reported outcomes

---

## Linking Strategy
```
DM (Subject)
  └── USUBJID
        ↓
APDM (Associated Person)
  └── RSUBJID → links to DM.USUBJID
  └── APID → unique identifier for associated person
        ↓
APAE, APSC, APMH, etc.
  └── APID → links to APDM.APID
```
# Relationship Domains

Relationship domains link records across different domains.

---

## RELREC - Related Records

**Purpose:** Establish relationships between records in different domains.

**Key Variables:**

| Variable | Label | Type | Required | Notes |
|----------|-------|------|----------|-------|
| STUDYID | Study Identifier | Char | Req | |
| RDOMAIN | Related Domain Abbreviation | Char | Req | Domain containing record |
| USUBJID | Unique Subject Identifier | Char | Req | Subject |
| IDVAR | Identifying Variable | Char | Req | Variable linking record |
| IDVARVAL | Identifying Variable Value | Char | Req | Value of IDVAR |
| RELTYPE | Relationship Type | Char | Req | ONE, MANY |
| RELID | Relationship Identifier | Char | Req | Groups related records |

**Sort Order:** STUDYID, RELID, RDOMAIN, USUBJID, IDVAR, IDVARVAL

**RELTYPE Values:**
- ONE: One-to-one relationship
- MANY: One-to-many or many-to-many

**Example - AE Treated by CM:**
| RDOMAIN | USUBJID | IDVAR | IDVARVAL | RELTYPE | RELID |
|---------|---------|-------|----------|---------|-------|
| AE | SUBJ001 | AESEQ | 1 | ONE | REL001 |
| CM | SUBJ001 | CMSEQ | 5 | ONE | REL001 |

**Example - AE Confirmed by Multiple LB:**
| RDOMAIN | USUBJID | IDVAR | IDVARVAL | RELTYPE | RELID |
|---------|---------|-------|----------|---------|-------|
| AE | SUBJ001 | AESEQ | 2 | ONE | REL002 |
| LB | SUBJ001 | LBSEQ | 10 | MANY | REL002 |
| LB | SUBJ001 | LBSEQ | 11 | MANY | REL002 |

**Common Relationship Types:**

| Relationship | Description |
|--------------|-------------|
| AE-CM | Medication given to treat AE |
| AE-LB | Lab test confirming AE |
| AE-PR | Procedure performed for AE |
| CM-MH | Medication for medical history condition |
| DS-AE | Disposition due to AE |
| EX-AE | Exposure change due to AE |
| LB-PR | Lab sample collected during procedure |
| TU-TR-RS | Tumor-assessment-response linkage |

---

## SUPP-- - Supplemental Qualifiers

**Purpose:** Store non-standard variables as qualifiers to parent domain records.

**Structure:**

| Variable | Label | Type | Required | Notes |
|----------|-------|------|----------|-------|
| STUDYID | Study Identifier | Char | Req | |
| RDOMAIN | Related Domain Abbreviation | Char | Req | Parent domain (e.g., AE, CM) |
| USUBJID | Unique Subject Identifier | Char | Req | |
| IDVAR | Identifying Variable | Char | Req | Usually --SEQ |
| IDVARVAL | Identifying Variable Value | Char | Req | Sequence value |
| QNAM | Qualifier Variable Name | Char | Req | ≤8 characters |
| QLABEL | Qualifier Variable Label | Char | Req | ≤40 characters |
| QVAL | Data Value | Char | Req | The actual value |
| QORIG | Origin | Char | Req | CRF, DERIVED, ASSIGNED |
| QEVAL | Evaluator | Char | Perm | If multiple evaluators |

**Sort Order:** STUDYID, RDOMAIN, USUBJID, IDVAR, IDVARVAL, QNAM

**Example - SUPPAE:**
| RDOMAIN | USUBJID | IDVAR | IDVARVAL | QNAM | QLABEL | QVAL | QORIG |
|---------|---------|-------|----------|------|--------|------|-------|
| AE | SUBJ001 | AESEQ | 1 | AESOSP | AE Source Sponsor | Y | CRF |
| AE | SUBJ001 | AESEQ | 1 | AESSION | AE Led to Dose Reduction | Y | CRF |
| AE | SUBJ001 | AESEQ | 2 | AETRTEM | Treatment Emergent | Y | DERIVED |

**When to Use SUPP--:**
- Non-standard qualifiers for existing records
- Additional attributes not in standard model
- Sponsor-specific data elements

**When NOT to Use SUPP--:**
- Data fitting existing domain structure
- Independent observations (use separate domain)
- Multiple related values (consider custom domain)

**QNAM Naming Rules:**
- Maximum 8 characters
- Must be unique within RDOMAIN
- Should be meaningful abbreviation
- Use --prefix convention where applicable (e.g., AETRTEM for AE treatment emergent)

---

## CO - Comments (Relationship Use)

**Purpose:** Link free-text comments to specific domain records.

**Relationship Variables:**

| Variable | Label | Type | Notes |
|----------|-------|------|-------|
| RDOMAIN | Related Domain Abbreviation | Char | Parent domain |
| IDVAR | Identifying Variable | Char | Links to parent |
| IDVARVAL | Identifying Variable Value | Char | Value of IDVAR |

**Example - Comment on AE:**
| USUBJID | COSEQ | RDOMAIN | IDVAR | IDVARVAL | COVAL |
|---------|-------|---------|-------|----------|-------|
| SUBJ001 | 1 | AE | AESEQ | 1 | Patient reported improvement after treatment |
| SUBJ001 | 2 | CM | CMSEQ | 3 | Medication stopped early per physician |

---

## FA - Findings About (Relationship)

**Purpose:** Findings that describe another domain's records.

**Common Uses:**
- AE severity at different time points
- Tumor assessments linked to TU records
- Additional qualifiers requiring own timing

**Relationship Variables:**

| Variable | Label | Type |
|----------|-------|------|
| FAOBJ | Object of Finding | Char |
| FALNKID | Link ID | Char |
| FALNKGRP | Link Group ID | Char |

**Example - Findings About AE:**
| USUBJID | FASEQ | FATESTCD | FATEST | FAORRES | FAOBJ | FALNKID |
|---------|-------|----------|--------|---------|-------|---------|
| SUBJ001 | 1 | AESSION | Severity at Onset | MODERATE | HEADACHE | AE.SUBJ001.1 |
| SUBJ001 | 2 | AEMXSEV | Maximum Severity | SEVERE | HEADACHE | AE.SUBJ001.1 |
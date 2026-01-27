# Relationship Domains

## Table of Contents
1. [RELREC - Related Records](#relrec---related-records)
2. [SUPPQUAL - Supplemental Qualifiers](#suppqual---supplemental-qualifiers)
3. [CO - Comments](#co---comments)

---

## RELREC - Related Records

**Purpose:** Document relationships between records in different domains.

### Structure
| Variable | Label | Type | Core |
|----------|-------|------|------|
| STUDYID | Study Identifier | Char | Req |
| RDOMAIN | Related Domain | Char | Req |
| USUBJID | Unique Subject ID | Char | Exp |
| IDVAR | Identifying Variable | Char | Req |
| IDVARVAL | Identifying Variable Value | Char | Req |
| RELTYPE | Relationship Type | Char | Exp |
| RELID | Relationship Identifier | Char | Req |

### Relationship Types (RELTYPE)
| Value | Description | Example |
|-------|-------------|---------|
| ONE | One-to-one relationship | AE linked to single DS |
| MANY | Many-to-many relationship | Multiple CMs for single AE |

### Common Relationship Scenarios

**AE to CM (Concomitant medication for AE):**
```
RDOMAIN  USUBJID         IDVAR   IDVARVAL  RELTYPE  RELID
AE       ABC123-001-001  AESEQ   3         MANY     REL01
CM       ABC123-001-001  CMSEQ   7         MANY     REL01
CM       ABC123-001-001  CMSEQ   8         MANY     REL01
```

**AE to DS (AE leading to discontinuation):**
```
RDOMAIN  USUBJID         IDVAR   IDVARVAL  RELTYPE  RELID
AE       ABC123-001-001  AESEQ   5         ONE      REL02
DS       ABC123-001-001  DSSEQ   2         ONE      REL02
```

**AE to PR (Procedure for AE):**
```
RDOMAIN  USUBJID         IDVAR   IDVARVAL  RELTYPE  RELID
AE       ABC123-001-001  AESEQ   10        ONE      REL03
PR       ABC123-001-001  PRSEQ   4         ONE      REL03
```

### Rules
- Same RELID groups related records
- IDVAR = the sequence variable (--SEQ)
- IDVARVAL = the sequence number value
- One RELREC dataset per study
- All relationships in single dataset

---

## SUPPQUAL - Supplemental Qualifiers

**Purpose:** Store non-standard variables that don't fit in main domain.

### Structure
| Variable | Label | Type | Core |
|----------|-------|------|------|
| STUDYID | Study Identifier | Char | Req |
| RDOMAIN | Related Domain | Char | Req |
| USUBJID | Unique Subject ID | Char | Req |
| IDVAR | Identifying Variable | Char | Exp |
| IDVARVAL | Identifying Variable Value | Char | Exp |
| QNAM | Qualifier Variable Name | Char | Req |
| QLABEL | Qualifier Variable Label | Char | Req |
| QVAL | Data Value | Char | Req |
| QORIG | Origin | Char | Req |
| QEVAL | Evaluator | Char | Perm |

### Naming Convention
- SUPPAE for AE supplemental qualifiers
- SUPPDM for DM supplemental qualifiers
- SUPPLB for LB supplemental qualifiers
- etc.

### QORIG Values
| Value | Description |
|-------|-------------|
| CRF | Data collected on CRF |
| DERIVED | Calculated/derived value |
| ASSIGNED | Assigned by sponsor |
| PROTOCOL | From protocol |
| eDT | Electronic data transfer |

### QEVAL Values
| Value | Description |
|-------|-------------|
| INVESTIGATOR | Assessed by investigator |
| SPONSOR | Assessed by sponsor |
| ADJUDICATION COMMITTEE | Assessed by committee |
| INDEPENDENT ASSESSOR | Assessed by independent assessor |

### Example: SUPPAE
```
RDOMAIN  USUBJID         IDVAR   IDVARVAL  QNAM      QLABEL                    QVAL       QORIG
AE       ABC123-001-001  AESEQ   1         AESOSP    AE Source of Suspicion    PATIENT    CRF
AE       ABC123-001-001  AESEQ   1         AEONGO    AE Ongoing                Y          CRF
AE       ABC123-001-001  AESEQ   2         AESOSP    AE Source of Suspicion    PHYSICIAN  CRF
```

### When to Use SUPPQUAL
Use supplemental qualifiers when:
- Variable is not in SDTM IG for that domain
- Variable cannot be mapped to existing permissible variable
- Sponsor-specific data needed for analysis
- Maximum 20 QNAM values per domain (guideline)

### When NOT to Use SUPPQUAL
- Data fits existing SDTM variable
- Data can be derived for ADaM (derive there instead)
- Data is truly not needed for regulatory review

---

## CO - Comments

**Purpose:** Free-text comments linked to records in other domains.

### Structure
| Variable | Label | Type | Core |
|----------|-------|------|------|
| STUDYID | Study Identifier | Char | Req |
| DOMAIN | Domain Abbreviation | Char | Req |
| RDOMAIN | Related Domain | Char | Exp |
| USUBJID | Unique Subject ID | Char | Req |
| COSEQ | Sequence Number | Num | Req |
| IDVAR | Identifying Variable | Char | Exp |
| IDVARVAL | Identifying Variable Value | Char | Exp |
| COREF | Comment Reference | Char | Perm |
| CODTC | Date/Time of Comment | Char | Perm |
| COVAL | Comment | Char | Req |

### Linking Comments to Parent Records
```
RDOMAIN  USUBJID         IDVAR   IDVARVAL  COVAL
AE       ABC123-001-001  AESEQ   3         Subject reported improvement after dose reduction
CM       ABC123-001-001  CMSEQ   5         Medication prescribed by external physician
```

### Unlinked Comments
If RDOMAIN/IDVAR/IDVARVAL are blank, comment is general/not linked to specific record.

---

## Relationship Best Practices

### Documentation in Define.xml
All relationships must be documented in define.xml:
- RELREC relationships in metadata
- SUPPQUAL variable definitions
- Comment domain relationships

### Consistency Rules
1. IDVAR must be a variable in the related domain
2. IDVARVAL must match actual values in that variable
3. RELID must be unique across study
4. QNAM must be valid SAS variable name (≤8 chars, A-Z, 0-9, _)

### Validation Checks
- Orphan records (SUPPQUAL without parent)
- Invalid IDVAR/IDVARVAL combinations
- Duplicate QNAM within domain
- QVAL length exceeds 200 characters

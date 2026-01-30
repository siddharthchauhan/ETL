# Special Purpose Domains

Special Purpose domains contain subject-level and study-level data that don't fit the standard Findings, Events, or Interventions class structure.

## DM - Demographics

**Purpose:** One record per subject containing demographic and baseline information.

**Key Variables:**

| Variable | Label | Type | Required | Controlled Terminology |
|----------|-------|------|----------|------------------------|
| STUDYID | Study Identifier | Char | Req | - |
| DOMAIN | Domain Abbreviation | Char | Req | DM |
| USUBJID | Unique Subject Identifier | Char | Req | - |
| SUBJID | Subject Identifier for the Study | Char | Req | - |
| RFSTDTC | Subject Reference Start Date/Time | Char | Exp | - |
| RFENDTC | Subject Reference End Date/Time | Char | Exp | - |
| RFXSTDTC | Date/Time of First Study Treatment | Char | Exp | - |
| RFXENDTC | Date/Time of Last Study Treatment | Char | Exp | - |
| RFICDTC | Date/Time of Informed Consent | Char | Exp | - |
| RFPENDTC | Date/Time of End of Participation | Char | Exp | - |
| DTHDTC | Date/Time of Death | Char | Exp | - |
| DTHFL | Subject Death Flag | Char | Exp | NY (Y only) |
| SITEID | Study Site Identifier | Char | Req | - |
| BRTHDTC | Date/Time of Birth | Char | Perm | - |
| AGE | Age | Num | Exp | - |
| AGEU | Age Units | Char | Exp | AGEU |
| SEX | Sex | Char | Req | SEX |
| RACE | Race | Char | Exp | RACE |
| ETHNIC | Ethnicity | Char | Perm | ETHNIC |
| ARMCD | Planned Arm Code | Char | Req | - |
| ARM | Description of Planned Arm | Char | Req | - |
| ACTARMCD | Actual Arm Code | Char | Req | - |
| ACTARM | Description of Actual Arm | Char | Req | - |
| COUNTRY | Country | Char | Req | ISO 3166-1 Alpha-3 |
| DMDTC | Date/Time of Collection | Char | Perm | - |
| DMDY | Study Day of Collection | Num | Perm | - |

**Sort Order:** STUDYID, USUBJID

**Reference Date Hierarchy:**
```
RFICDTC: Informed consent date
    ↓
RFSTDTC: Reference start (usually first dose for treated; randomization for ITT)
    ↓
RFXSTDTC: First exposure to study treatment
    ↓
RFXENDTC: Last exposure to study treatment
    ↓
RFENDTC: Reference end (last contact/observation)
    ↓
RFPENDTC: End of participation (includes follow-up)
```

**Common Issues:**
- RFSTDTC missing for screen failures: Acceptable, document in define.xml
- Multiple races: Use SUPPDM with QNAM="RACEn" for additional races
- Age calculation: Calculate as of RFSTDTC, not enrollment date

---

## CO - Comments

**Purpose:** Free-text comments collected during study that don't fit elsewhere.

**Key Variables:**

| Variable | Label | Type | Required |
|----------|-------|------|----------|
| STUDYID | Study Identifier | Char | Req |
| DOMAIN | Domain Abbreviation | Char | Req |
| RDOMAIN | Related Domain Abbreviation | Char | Perm |
| USUBJID | Unique Subject Identifier | Char | Req |
| COSEQ | Sequence Number | Num | Req |
| IDVAR | Identifying Variable | Char | Perm |
| IDVARVAL | Identifying Variable Value | Char | Perm |
| COREF | Comment Reference | Char | Perm |
| CODTC | Date/Time of Comment | Char | Perm |
| CODY | Study Day of Comment | Num | Perm |
| COEVAL | Evaluator | Char | Perm |
| COVAL | Comment | Char | Req |

**Usage Notes:**
- Link to parent record using RDOMAIN, IDVAR, IDVARVAL
- COREF can categorize comments (e.g., "GENERAL", "DOSING")
- Don't use for data that belongs in specific domains

---

## SE - Subject Elements

**Purpose:** Subject's actual experience of study elements (periods).

**Key Variables:**

| Variable | Label | Type | Required |
|----------|-------|------|----------|
| STUDYID | Study Identifier | Char | Req |
| DOMAIN | Domain Abbreviation | Char | Req |
| USUBJID | Unique Subject Identifier | Char | Req |
| SESEQ | Sequence Number | Num | Req |
| ETCD | Element Code | Char | Req |
| ELEMENT | Description of Element | Char | Req |
| SESTDTC | Start Date/Time of Element | Char | Exp |
| SEENDTC | End Date/Time of Element | Char | Exp |
| SEUPDES | Description of Unplanned Element | Char | Perm |
| EPOCH | Epoch | Char | Req |

**Relationship to Trial Design:**
- ETCD must match TE.ETCD
- ELEMENT must match TE.ELEMENT
- EPOCH derived from TE based on ETCD

**Example:**
| USUBJID | SESEQ | ETCD | ELEMENT | SESTDTC | SEENDTC | EPOCH |
|---------|-------|------|---------|---------|---------|-------|
| SUBJ001 | 1 | SCRN | Screening | 2024-01-01 | 2024-01-14 | SCREENING |
| SUBJ001 | 2 | TRT | Treatment | 2024-01-15 | 2024-04-15 | TREATMENT |
| SUBJ001 | 3 | FU | Follow-up | 2024-04-16 | 2024-05-15 | FOLLOW-UP |

---

## SV - Subject Visits

**Purpose:** Actual visits/contacts for each subject.

**Key Variables:**

| Variable | Label | Type | Required |
|----------|-------|------|----------|
| STUDYID | Study Identifier | Char | Req |
| DOMAIN | Domain Abbreviation | Char | Req |
| USUBJID | Unique Subject Identifier | Char | Req |
| VISITNUM | Visit Number | Num | Exp |
| VISIT | Visit Name | Char | Exp |
| VISITDY | Planned Study Day of Visit | Num | Perm |
| SVSTDTC | Start Date/Time of Visit | Char | Exp |
| SVENDTC | End Date/Time of Visit | Char | Exp |
| SVUPDES | Description of Unplanned Visit | Char | Perm |
| EPOCH | Epoch | Char | Perm |

**Visit Numbering Convention:**
- Planned visits: Integer (1, 2, 3...)
- Unplanned visits: Decimal (2.1, 2.2 for unplanned between V2 and V3)
- Early termination: Often 999 or designated number

**Sort Order:** STUDYID, USUBJID, SVSTDTC, VISITNUM
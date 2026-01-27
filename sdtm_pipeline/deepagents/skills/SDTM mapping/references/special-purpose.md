# Special Purpose Domains

## Table of Contents
1. [DM - Demographics](#dm---demographics)
2. [CO - Comments](#co---comments)
3. [SE - Subject Elements](#se---subject-elements)
4. [SV - Subject Visits](#sv---subject-visits)

---

## DM - Demographics

**Purpose:** One record per subject containing demographic and baseline information.

### Required Variables
| Variable | Label | Type | CT Codelist |
|----------|-------|------|-------------|
| STUDYID | Study Identifier | Char | - |
| DOMAIN | Domain Abbreviation | Char | "DM" |
| USUBJID | Unique Subject ID | Char | - |
| SUBJID | Subject ID for Study | Char | - |
| RFSTDTC | Subject Reference Start Date | Char | ISO 8601 |
| RFENDTC | Subject Reference End Date | Char | ISO 8601 |
| SITEID | Study Site Identifier | Char | - |
| AGE | Age | Num | - |
| AGEU | Age Units | Char | AGEU (C66781) |
| SEX | Sex | Char | SEX (C66731) |
| RACE | Race | Char | RACE (C74457) |
| ETHNIC | Ethnicity | Char | ETHNIC (C66790) |
| ARMCD | Planned Arm Code | Char | - |
| ARM | Description of Planned Arm | Char | - |
| COUNTRY | Country | Char | ISO 3166-1 alpha-3 |

### Key Derivations

**USUBJID:**
```
USUBJID = STUDYID || "-" || SITEID || "-" || SUBJID
```

**RFSTDTC (Reference Start Date):**
- Usually first dose date for drug studies
- First treatment date for device studies
- Must be documented in protocol/SAP

**RFENDTC (Reference End Date):**
- Last dose date + protocol-defined follow-up
- Study completion/discontinuation date

**AGE Calculation:**
```
AGE = floor((RFSTDTC - BRTHDTC) / 365.25)
-- or use collected age if birth date not collected
```

### Controlled Terminology

**SEX (C66731):**
| Code | Submission Value | Definition |
|------|------------------|------------|
| C16576 | M | Male |
| C16577 | F | Female |
| C17998 | U | Unknown |
| C38046 | UNDIFFERENTIATED | Undifferentiated |

**RACE (C74457):**
| Submission Value | Definition |
|------------------|------------|
| AMERICAN INDIAN OR ALASKA NATIVE | A person having origins in any of the original peoples of North and South America |
| ASIAN | A person having origins in any of the original peoples of the Far East, Southeast Asia, or the Indian subcontinent |
| BLACK OR AFRICAN AMERICAN | A person having origins in any of the Black racial groups of Africa |
| NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER | A person having origins in any of the original peoples of Hawaii, Guam, Samoa, or other Pacific Islands |
| WHITE | A person having origins in any of the original peoples of Europe, the Middle East, or North Africa |
| MULTIPLE | More than one race reported |
| NOT REPORTED | Subject declined to provide |
| UNKNOWN | Race not known |
| OTHER | Not classifiable in above categories |

**ETHNIC (C66790):**
| Submission Value | Definition |
|------------------|------------|
| HISPANIC OR LATINO | Cuban, Mexican, Puerto Rican, South/Central American, or other Spanish culture |
| NOT HISPANIC OR LATINO | Not of Spanish culture origin |
| NOT REPORTED | Subject declined to provide |
| UNKNOWN | Ethnicity not known |

---

## CO - Comments

**Purpose:** Free-text comments collected during study.

### Structure
| Variable | Label | Type | Core |
|----------|-------|------|------|
| STUDYID | Study Identifier | Char | Req |
| DOMAIN | Domain Abbreviation | Char | Req |
| USUBJID | Unique Subject ID | Char | Req |
| COSEQ | Sequence Number | Num | Req |
| IDVAR | Identifying Variable | Char | Exp |
| IDVARVAL | Identifying Variable Value | Char | Exp |
| COREF | Comment Reference | Char | Perm |
| CODTC | Date/Time of Comment | Char | Perm |
| COVAL | Comment | Char | Req |

### Usage Notes
- Link to parent record using IDVAR/IDVARVAL
- IDVAR = variable name (e.g., "AESEQ")
- IDVARVAL = value (e.g., "5")

---

## SE - Subject Elements

**Purpose:** Subject-level trial element timing (Epochs).

### Required Variables
| Variable | Label | Type |
|----------|-------|------|
| STUDYID | Study Identifier | Char |
| DOMAIN | Domain Abbreviation | Char |
| USUBJID | Unique Subject ID | Char |
| SESEQ | Sequence Number | Num |
| ETCD | Element Code | Char |
| ELEMENT | Description of Element | Char |
| SESTDTC | Start Date/Time of Element | Char |
| SEENDTC | End Date/Time of Element | Char |
| TAESSION | Planned Element | Char |

### Common Elements
- SCREENING
- RUN-IN
- TREATMENT
- FOLLOW-UP
- WASHOUT

---

## SV - Subject Visits

**Purpose:** Actual visit dates and timing for subjects.

### Required Variables
| Variable | Label | Type |
|----------|-------|------|
| STUDYID | Study Identifier | Char |
| DOMAIN | Domain Abbreviation | Char |
| USUBJID | Unique Subject ID | Char |
| SVSEQ | Sequence Number | Num |
| VISITNUM | Visit Number | Num |
| VISIT | Visit Name | Char |
| VISITDY | Planned Study Day of Visit | Num |
| SVSTDTC | Start Date/Time of Visit | Char |
| SVENDTC | End Date/Time of Visit | Char |

### Key Points
- One record per actual visit
- VISITNUM should match planned visits from TV domain
- Unscheduled visits use decimals (e.g., 5.1, 5.2)

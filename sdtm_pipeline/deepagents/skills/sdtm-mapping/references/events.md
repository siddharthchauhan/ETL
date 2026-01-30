# Events Class Domains

Events describe occurrences, incidents, or findings about subjects that happen during the study.

## General Events Structure

| Variable | Label | Role | Notes |
|----------|-------|------|-------|
| --TERM | Reported Term | Topic | Verbatim as reported |
| --MODIFY | Modified Reported Term | Synonym | Cleaned/modified verbatim |
| --DECOD | Dictionary-Derived Term | Synonym | MedDRA PT or equivalent |
| --CAT | Category | Grouping | Sponsor-defined |
| --SCAT | Subcategory | Grouping | Sponsor-defined |
| --PRESP | Pre-specified | Record Qualifier | Y if on CRF checklist |
| --OCCUR | Occurrence | Record Qualifier | Y/N for pre-specified |
| --BODSYS | Body System | Record Qualifier | MedDRA SOC |
| --SEV | Severity | Record Qualifier | MILD/MODERATE/SEVERE |
| --SER | Serious | Record Qualifier | Y/N |
| --STDTC | Start Date/Time | Timing | ISO 8601 |
| --ENDTC | End Date/Time | Timing | ISO 8601 |
| --STDY | Study Day of Start | Timing | Derived |
| --ENDY | Study Day of End | Timing | Derived |

---

## AE - Adverse Events

**Purpose:** All adverse events occurring during study participation.

**Key Variables:**

| Variable | Label | Type | Required | CT |
|----------|-------|------|----------|-----|
| STUDYID | Study Identifier | Char | Req | - |
| DOMAIN | Domain Abbreviation | Char | Req | AE |
| USUBJID | Unique Subject Identifier | Char | Req | - |
| AESEQ | Sequence Number | Num | Req | - |
| AESPID | Sponsor-Defined Identifier | Char | Perm | - |
| AETERM | Reported Term for AE | Char | Req | - |
| AEMODIFY | Modified Reported Term | Char | Perm | - |
| AEDECOD | Dictionary-Derived Term | Char | Perm | MedDRA |
| AEBODSYS | Body System or Organ Class | Char | Perm | MedDRA SOC |
| AEBDSYCD | Body System or Organ Class Code | Num | Perm | MedDRA SOC Code |
| AESOC | Primary System Organ Class | Char | Perm | MedDRA SOC |
| AESOCCD | Primary System Organ Class Code | Num | Perm | MedDRA SOC Code |
| AEHLGT | High Level Group Term | Char | Perm | MedDRA HLGT |
| AEHLGTCD | High Level Group Term Code | Num | Perm | MedDRA HLGT Code |
| AEHLT | High Level Term | Char | Perm | MedDRA HLT |
| AEHLTCD | High Level Term Code | Num | Perm | MedDRA HLT Code |
| AELLTCD | Lowest Level Term Code | Num | Perm | MedDRA LLT Code |
| AELOC | Location of Event | Char | Perm | LOC |
| AESEV | Severity/Intensity | Char | Perm | AESEV |
| AESER | Serious Event | Char | Exp | NY |
| AEACN | Action Taken with Study Treatment | Char | Exp | ACN |
| AEACNOTH | Other Action Taken | Char | Perm | - |
| AEACNDEV | Action Taken with Device | Char | Perm | DEVACN |
| AEREL | Causality | Char | Perm | REL |
| AERELNST | Relationship to Non-Study Treatment | Char | Perm | - |
| AEPATT | Pattern of AE | Char | Perm | - |
| AEOUT | Outcome of AE | Char | Exp | OUT |
| AESCAN | Involves Cancer | Char | Perm | NY |
| AESCONG | Congenital Anomaly or Birth Defect | Char | Perm | NY |
| AESDISAB | Persist or Signif Disability | Char | Perm | NY |
| AESDTH | Results in Death | Char | Perm | NY |
| AESHOSP | Requires Hospitalization | Char | Perm | NY |
| AESLIFE | Is Life Threatening | Char | Perm | NY |
| AESMIE | Other Medically Important Event | Char | Perm | NY |
| AECONTRT | Concomitant Treatment Given | Char | Perm | NY |
| AETOXGR | Standard Toxicity Grade | Char | Perm | - |
| EPOCH | Epoch | Char | Perm | EPOCH |
| AESTDTC | Start Date/Time of AE | Char | Exp | - |
| AEENDTC | End Date/Time of AE | Char | Perm | - |
| AESTDY | Study Day of Start | Num | Perm | - |
| AEENDY | Study Day of End | Num | Perm | - |
| AEDUR | Duration of AE | Char | Perm | - |
| AEENRF | End Relative to Reference Period | Char | Perm | STENRF |
| AEENTPT | End Reference Time Point | Char | Perm | - |

**Sort Order:** STUDYID, USUBJID, AEDECOD, AESTDTC, AESEQ

**Seriousness Criteria (AESER = "Y" if any):**
- AESDTH = Y (Results in death)
- AESLIFE = Y (Life-threatening)
- AESHOSP = Y (Hospitalization required/prolonged)
- AESDISAB = Y (Persistent disability)
- AESCONG = Y (Congenital anomaly)
- AESMIE = Y (Other medically important)

**AEACN Values:**
- DOSE NOT CHANGED
- DOSE REDUCED
- DRUG INTERRUPTED
- DRUG WITHDRAWN
- NOT APPLICABLE
- DOSE INCREASED (less common)

**MedDRA Hierarchy:**
```
SOC (System Organ Class)
  └── HLGT (High Level Group Term)
        └── HLT (High Level Term)
              └── PT (Preferred Term) ← AEDECOD
                    └── LLT (Lowest Level Term)
```

---

## DS - Disposition

**Purpose:** Subject's disposition at major milestones (screening, treatment, study).

**Key Variables:**

| Variable | Label | Type | Required | CT |
|----------|-------|------|----------|-----|
| STUDYID | Study Identifier | Char | Req | - |
| DOMAIN | Domain Abbreviation | Char | Req | DS |
| USUBJID | Unique Subject Identifier | Char | Req | - |
| DSSEQ | Sequence Number | Num | Req | - |
| DSTERM | Reported Term for Disposition | Char | Req | - |
| DSDECOD | Standardized Disposition Term | Char | Req | NCOMPLT |
| DSCAT | Category for Disposition | Char | Exp | - |
| DSSCAT | Subcategory for Disposition | Char | Perm | - |
| EPOCH | Epoch | Char | Perm | EPOCH |
| DSSTDTC | Start Date/Time of Disposition | Char | Exp | - |
| DSSTDY | Study Day of Start | Num | Perm | - |

**Sort Order:** STUDYID, USUBJID, DSCAT, DSSTDTC, DSSEQ

**DSCAT Values:**
- PROTOCOL MILESTONE
- DISPOSITION EVENT
- OTHER EVENT

**Common DSDECOD Values (from NCOMPLT codelist):**
- COMPLETED
- ADVERSE EVENT
- DEATH
- LACK OF EFFICACY
- LOST TO FOLLOW-UP
- PHYSICIAN DECISION
- PREGNANCY
- PROTOCOL DEVIATION
- PROTOCOL VIOLATION
- SCREEN FAILURE
- STUDY TERMINATED BY SPONSOR
- WITHDRAWAL BY SUBJECT

**Example Disposition Records:**
| USUBJID | DSSEQ | DSTERM | DSDECOD | DSCAT | DSSTDTC |
|---------|-------|--------|---------|-------|---------|
| SUBJ001 | 1 | INFORMED CONSENT | INFORMED CONSENT OBTAINED | PROTOCOL MILESTONE | 2024-01-01 |
| SUBJ001 | 2 | RANDOMIZED | RANDOMIZED | PROTOCOL MILESTONE | 2024-01-15 |
| SUBJ001 | 3 | COMPLETED | COMPLETED | DISPOSITION EVENT | 2024-04-15 |

---

## MH - Medical History

**Purpose:** Pre-existing conditions and medical history prior to study.

**Key Variables:**

| Variable | Label | Type | Required | CT |
|----------|-------|------|----------|-----|
| STUDYID | Study Identifier | Char | Req | - |
| DOMAIN | Domain Abbreviation | Char | Req | MH |
| USUBJID | Unique Subject Identifier | Char | Req | - |
| MHSEQ | Sequence Number | Num | Req | - |
| MHTERM | Reported Term for Medical History | Char | Req | - |
| MHMODIFY | Modified Reported Term | Char | Perm | - |
| MHDECOD | Dictionary-Derived Term | Char | Perm | MedDRA |
| MHCAT | Category for Medical History | Char | Perm | - |
| MHSCAT | Subcategory | Char | Perm | - |
| MHPRESP | Pre-specified | Char | Perm | NY |
| MHOCCUR | Occurrence | Char | Perm | NY |
| MHBODSYS | Body System or Organ Class | Char | Perm | MedDRA SOC |
| MHSTAT | Completion Status | Char | Perm | ND |
| MHREASND | Reason Not Done | Char | Perm | - |
| MHSTDTC | Start Date/Time | Char | Perm | - |
| MHENDTC | End Date/Time | Char | Perm | - |
| MHENRF | End Relative to Reference Period | Char | Perm | STENRF |
| MHENTPT | End Reference Time Point | Char | Perm | - |

**Sort Order:** STUDYID, USUBJID, MHCAT, MHSTDTC, MHSEQ

**MHENRF Usage:**
- BEFORE: Condition resolved before study
- BEFORE/DURING: Started before, ongoing at study start
- DURING: Would be unusual for MH (should be in AE)

---

## CE - Clinical Events

**Purpose:** Disease milestones, clinical outcomes not fitting other event domains.

**Use Cases:**
- Disease progression events
- Clinical milestones (e.g., first seizure in epilepsy study)
- Outcomes not meeting AE definition

**Key Variables:**

| Variable | Label | Type | Required |
|----------|-------|------|----------|
| STUDYID | Study Identifier | Char | Req |
| DOMAIN | Domain Abbreviation | Char | Req |
| USUBJID | Unique Subject Identifier | Char | Req |
| CESEQ | Sequence Number | Num | Req |
| CETERM | Reported Term for Clinical Event | Char | Req |
| CEDECOD | Dictionary-Derived Term | Char | Perm |
| CECAT | Category | Char | Perm |
| CESCAT | Subcategory | Char | Perm |
| CEPRESP | Pre-specified | Char | Perm |
| CEOCCUR | Occurrence | Char | Perm |
| CESTDTC | Start Date/Time of Event | Char | Perm |
| CEENDTC | End Date/Time of Event | Char | Perm |

---

## DV - Protocol Deviations

**Purpose:** Protocol deviations and violations.

**Key Variables:**

| Variable | Label | Type | Required | CT |
|----------|-------|------|----------|-----|
| STUDYID | Study Identifier | Char | Req | - |
| DOMAIN | Domain Abbreviation | Char | Req | DV |
| USUBJID | Unique Subject Identifier | Char | Req | - |
| DVSEQ | Sequence Number | Num | Req | - |
| DVTERM | Protocol Deviation Term | Char | Req | - |
| DVDECOD | Standardized Deviation Term | Char | Perm | DVDECOD |
| DVCAT | Category | Char | Perm | DVCAT |
| DVSCAT | Subcategory | Char | Perm | - |
| EPOCH | Epoch | Char | Perm | EPOCH |
| DVSTDTC | Start Date/Time | Char | Perm | - |
| DVENDTC | End Date/Time | Char | Perm | - |

**DVCAT Values:**
- ELIGIBILITY CRITERIA
- STUDY PROCEDURES
- DOSING
- VISIT SCHEDULE
- CONCOMITANT MEDICATION
- INFORMED CONSENT
- LABORATORY
- OTHER
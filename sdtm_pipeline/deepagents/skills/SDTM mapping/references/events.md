# Events Domain Class

## Table of Contents
1. [AE - Adverse Events](#ae---adverse-events)
2. [DS - Disposition](#ds---disposition)
3. [MH - Medical History](#mh---medical-history)
4. [DV - Protocol Deviations](#dv---protocol-deviations)
5. [CE - Clinical Events](#ce---clinical-events)

---

## AE - Adverse Events

**Purpose:** All adverse events reported during study participation.

### Required Variables
| Variable | Label | Type | CT Codelist |
|----------|-------|------|-------------|
| STUDYID | Study Identifier | Char | - |
| DOMAIN | Domain Abbreviation | Char | "AE" |
| USUBJID | Unique Subject ID | Char | - |
| AESEQ | Sequence Number | Num | - |
| AETERM | Reported Term for AE | Char | - |
| AEDECOD | Dictionary-Derived Term | Char | MedDRA PT |
| AESTDTC | Start Date/Time of AE | Char | ISO 8601 |

### Expected Variables
| Variable | Label | Type | CT Codelist |
|----------|-------|------|-------------|
| AEBODSYS | Body System or Organ Class | Char | MedDRA SOC |
| AEENDTC | End Date/Time of AE | Char | ISO 8601 |
| AESER | Serious Event | Char | NY (C66742) |
| AESEV | Severity/Intensity | Char | AESEV |
| AEREL | Causality | Char | Sponsor CT |
| AEACN | Action Taken with Study Trt | Char | ACN (C66767) |
| AEOUT | Outcome of AE | Char | OUT (C66768) |
| AESCAN | Involves Cancer | Char | NY |
| AESCONG | Congenital Anomaly | Char | NY |
| AESDISAB | Persist/Signif Disability | Char | NY |
| AESDTH | Results in Death | Char | NY |
| AESHOSP | Requires Hospitalization | Char | NY |
| AESLIFE | Life Threatening | Char | NY |
| AESMIE | Medically Important Event | Char | NY |
| AECONTRT | Concomitant Treatment Given | Char | NY |
| AETOXGR | Toxicity Grade | Char | CTCAE grade |

### MedDRA Coding
```
AETERM    = Verbatim from CRF (as reported)
AEDECOD   = MedDRA Preferred Term (PT)
AEBODSYS  = MedDRA System Organ Class (SOC)
AELLTCD   = Lowest Level Term Code (optional)
AELLTCD   = Low Level Term Code (optional)
AEPTCD    = Preferred Term Code (optional)
AESOCCD   = SOC Code (optional)
AEHLGTCD  = High Level Group Term Code (optional)
AEHLGT    = High Level Group Term (optional)
AEHLTCD   = High Level Term Code (optional)
AEHLT     = High Level Term (optional)
```

### Key Controlled Terminology

**AESER (C66742 - NY):**
| Code | Value |
|------|-------|
| Y | Yes |
| N | No |

**AESEV (Severity):**
| Value | Definition |
|-------|------------|
| MILD | Awareness of sign/symptom, easily tolerated |
| MODERATE | Discomfort enough to cause interference with usual activity |
| SEVERE | Incapacitating, inability to work or do usual activity |

**AEREL (Causality) - Sponsor-defined, examples:**
| Value | Definition |
|-------|------------|
| NOT RELATED | No reasonable possibility of relationship |
| UNLIKELY | Unlikely but cannot be ruled out |
| POSSIBLE | Could be related |
| PROBABLE | Likely related |
| DEFINITE | Clearly related |

**AEACN (C66767 - Action Taken):**
| Value | Definition |
|-------|------------|
| DRUG WITHDRAWN | Study drug permanently discontinued |
| DOSE REDUCED | Dose decreased |
| DOSE NOT CHANGED | No change to dosing |
| DOSE INCREASED | Dose increased |
| DRUG INTERRUPTED | Temporary discontinuation |
| NOT APPLICABLE | Not applicable |
| UNKNOWN | Unknown |

**AEOUT (C66768 - Outcome):**
| Value | Definition |
|-------|------------|
| RECOVERED/RESOLVED | AE has resolved |
| RECOVERING/RESOLVING | AE is improving |
| NOT RECOVERED/NOT RESOLVED | AE ongoing, not improving |
| RECOVERED/RESOLVED WITH SEQUELAE | Resolved with lasting effects |
| FATAL | Subject died |
| UNKNOWN | Unknown outcome |

### Seriousness Criteria
An AE is SERIOUS (AESER = "Y") if it:
- Results in death (AESDTH = "Y")
- Is life-threatening (AESLIFE = "Y")
- Requires inpatient hospitalization or prolongation (AESHOSP = "Y")
- Results in persistent or significant disability (AESDISAB = "Y")
- Is a congenital anomaly/birth defect (AESCONG = "Y")
- Is medically important (AESMIE = "Y")

---

## DS - Disposition

**Purpose:** Subject status/milestones through study participation.

### Required Variables
| Variable | Label | Type | CT Codelist |
|----------|-------|------|-------------|
| STUDYID | Study Identifier | Char | - |
| DOMAIN | Domain Abbreviation | Char | "DS" |
| USUBJID | Unique Subject ID | Char | - |
| DSSEQ | Sequence Number | Num | - |
| DSTERM | Reported Term | Char | - |
| DSDECOD | Standardized Disposition Term | Char | NCOMPLT (C66727) |
| DSSTDTC | Start Date/Time | Char | ISO 8601 |

### Expected Variables
| Variable | Label | Type | CT |
|----------|-------|------|-----|
| DSCAT | Category of Disposition Event | Char | - |
| DSSCAT | Subcategory | Char | - |
| EPOCH | Epoch | Char | EPOCH |

### Common DSCAT/DSDECOD Values

**DISPOSITION EVENT (DSCAT):**
| DSDECOD | DSCAT | Description |
|---------|-------|-------------|
| INFORMED CONSENT OBTAINED | PROTOCOL MILESTONE | Subject consented |
| RANDOMIZED | PROTOCOL MILESTONE | Subject randomized |
| COMPLETED | DISPOSITION EVENT | Completed study |
| SCREEN FAILURE | DISPOSITION EVENT | Failed screening |
| ADVERSE EVENT | DISPOSITION EVENT | Discontinued due to AE |
| DEATH | DISPOSITION EVENT | Subject died |
| WITHDRAWAL BY SUBJECT | DISPOSITION EVENT | Voluntary withdrawal |
| LOST TO FOLLOW-UP | DISPOSITION EVENT | Cannot contact subject |
| PROTOCOL VIOLATION | DISPOSITION EVENT | Discontinued for violation |
| LACK OF EFFICACY | DISPOSITION EVENT | No therapeutic benefit |
| PHYSICIAN DECISION | DISPOSITION EVENT | Investigator withdrew subject |

### Multiple Disposition Records
Subjects can have multiple DS records for different events:
1. INFORMED CONSENT OBTAINED
2. RANDOMIZED
3. COMPLETED (or discontinuation reason)

---

## MH - Medical History

**Purpose:** Pre-existing conditions and medical history.

### Required Variables
| Variable | Label | Type |
|----------|-------|------|
| STUDYID | Study Identifier | Char |
| DOMAIN | Domain Abbreviation | Char |
| USUBJID | Unique Subject ID | Char |
| MHSEQ | Sequence Number | Num |
| MHTERM | Reported Term | Char |
| MHDECOD | Dictionary-Derived Term | Char |
| MHSTDTC | Start Date/Time | Char |

### Expected Variables
| Variable | Label | Type |
|----------|-------|------|
| MHBODSYS | Body System (SOC) | Char |
| MHENDTC | End Date/Time | Char |
| MHCAT | Category | Char |
| MHPRESP | Pre-Specified | Char |
| MHOCCUR | Occurrence | Char |
| MHENRF | End Relative to Ref Period | Char |

### Categories (MHCAT)
- GENERAL MEDICAL HISTORY
- SURGICAL HISTORY
- FAMILY HISTORY
- DISEASE UNDER STUDY
- PRIMARY DIAGNOSIS

### Pre-specified vs. Free Text
- MHPRESP = "Y" if from pre-specified checklist on CRF
- MHOCCUR used with pre-specified to indicate Y/N response

---

## DV - Protocol Deviations

**Purpose:** Protocol deviations documented during study.

### Required Variables
| Variable | Label | Type |
|----------|-------|------|
| STUDYID | Study Identifier | Char |
| DOMAIN | Domain Abbreviation | Char |
| USUBJID | Unique Subject ID | Char |
| DVSEQ | Sequence Number | Num |
| DVTERM | Protocol Deviation Term | Char |
| DVSTDTC | Start Date/Time | Char |

### Expected Variables
| Variable | Label | Type |
|----------|-------|------|
| DVDECOD | Coded Deviation Term | Char |
| DVCAT | Category of Deviation | Char |
| DVSCAT | Subcategory | Char |

### Common Categories (DVCAT)
- INCLUSION/EXCLUSION CRITERIA
- DOSING
- VISIT SCHEDULE
- CONCOMITANT MEDICATION
- ASSESSMENT/PROCEDURE
- INFORMED CONSENT

---

## CE - Clinical Events

**Purpose:** Clinical events not captured in AE (outcomes, hospitalizations).

### Structure
Follows Events general observation class with:
- CETERM / CEDECOD for event terms
- CESTDTC / CEENDTC for timing
- CECAT / CESCAT for categorization

### Common Uses
- Hospitalizations not captured as AEs
- Disease progression events
- Efficacy-related clinical events

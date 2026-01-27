# Interventions Domain Class

## Table of Contents
1. [EX - Exposure](#ex---exposure)
2. [EC - Exposure as Collected](#ec---exposure-as-collected)
3. [CM - Concomitant Medications](#cm---concomitant-medications)
4. [SU - Substance Use](#su---substance-use)
5. [PR - Procedures](#pr---procedures)

---

## EX - Exposure

**Purpose:** Records of investigational product administration (derived/normalized).

### Required Variables
| Variable | Label | Type | CT Codelist |
|----------|-------|------|-------------|
| STUDYID | Study Identifier | Char | - |
| DOMAIN | Domain Abbreviation | Char | "EX" |
| USUBJID | Unique Subject ID | Char | - |
| EXSEQ | Sequence Number | Num | - |
| EXTRT | Name of Treatment | Char | - |
| EXDOSE | Dose | Num | - |
| EXDOSU | Dose Units | Char | UNIT (C71620) |
| EXDOSFRM | Dose Form | Char | FRM (C66726) |
| EXROUTE | Route of Administration | Char | ROUTE (C66729) |
| EXSTDTC | Start Date/Time | Char | ISO 8601 |
| EXENDTC | End Date/Time | Char | ISO 8601 |

### Expected Variables
| Variable | Label | Type | CT Codelist |
|----------|-------|------|-------------|
| EXDOSFRQ | Dosing Frequency per Interval | Char | FREQ (C71113) |
| EPOCH | Epoch | Char | EPOCH (C99079) |
| EXLOT | Lot Number | Char | - |

### Key Derivations

**EXSTDY / EXENDY:**
```
EXSTDY = (EXSTDTC - RFSTDTC) + 1 if EXSTDTC >= RFSTDTC
       = (EXSTDTC - RFSTDTC) if EXSTDTC < RFSTDTC
```

**One record per constant dosing interval:**
- Dose change = new record
- Treatment interruption = gap in records (or EXOCCUR = "N")

### Common CT Values

**EXDOSU (C71620):**
mg, g, mcg, mL, mg/kg, unit, IU

**EXDOSFRM (C66726):**
TABLET, CAPSULE, INJECTION, SOLUTION, SUSPENSION, CREAM, PATCH

**EXROUTE (C66729):**
ORAL, INTRAVENOUS, SUBCUTANEOUS, INTRAMUSCULAR, TOPICAL, TRANSDERMAL

**EXDOSFRQ (C71113):**
QD, BID, TID, QID, Q12H, Q8H, Q6H, QW, Q2W, QM, ONCE, PRN

---

## EC - Exposure as Collected

**Purpose:** Raw exposure data as recorded on CRF (before normalization).

### Distinction from EX
| Aspect | EC (Collected) | EX (Derived) |
|--------|----------------|--------------|
| Data Source | Direct from CRF | Derived/normalized |
| Granularity | As collected | Protocol-defined intervals |
| Dose Units | Collected units | Standardized units |
| Required | When different from EX | Always |

### When to Use EC
- Collected data differs from derived
- Complex dosing requiring normalization
- Need audit trail of collected vs. derived

---

## CM - Concomitant Medications

**Purpose:** Medications (other than study drug) taken during study.

### Required Variables
| Variable | Label | Type | CT Codelist |
|----------|-------|------|-------------|
| STUDYID | Study Identifier | Char | - |
| DOMAIN | Domain Abbreviation | Char | "CM" |
| USUBJID | Unique Subject ID | Char | - |
| CMSEQ | Sequence Number | Num | - |
| CMTRT | Reported Name of Drug | Char | - |
| CMDECOD | Standardized Medication Name | Char | WHODrug |
| CMSTDTC | Start Date/Time | Char | ISO 8601 |

### Expected Variables
| Variable | Label | Type | Notes |
|----------|-------|------|-------|
| CMINDC | Indication | Char | MedDRA PT or text |
| CMDOSE | Dose per Administration | Num | - |
| CMDOSU | Dose Units | Char | UNIT (C71620) |
| CMDOSFRQ | Dosing Frequency | Char | FREQ (C71113) |
| CMROUTE | Route | Char | ROUTE (C66729) |
| CMENDTC | End Date/Time | Char | ISO 8601 |
| CMCAT | Category | Char | PRIOR, CONCOMITANT |
| CMSCAT | Subcategory | Char | Sponsor-defined |
| CMCLAS | Medication Class | Char | ATC Class |
| CMCLASCD | Medication Class Code | Char | ATC Code |

### WHODrug Coding
- CMTRT = Verbatim term from CRF
- CMDECOD = WHODrug Preferred Name
- CMCLAS = ATC Level 2 text
- CMCLASCD = ATC code

### Timing Variables

**CMSTDY / CMENDY:**
```
Relative to RFSTDTC from DM
```

**CMSTRF / CMENRF (relative to reference period):**
- BEFORE = Started before RFSTDTC
- DURING = Started during reference period
- AFTER = Started after RFENDTC
- ONGOING = Continuing at data cutoff
- U = Unknown

**CMSTTPT / CMSTRTPT (timing relative to reference):**
- Use when dates unavailable but timing relative to event known

---

## SU - Substance Use

**Purpose:** Tobacco, alcohol, caffeine, recreational drug use.

### Required Variables
| Variable | Label | Type |
|----------|-------|------|
| STUDYID | Study Identifier | Char |
| DOMAIN | Domain Abbreviation | Char |
| USUBJID | Unique Subject ID | Char |
| SUSEQ | Sequence Number | Num |
| SUTRT | Reported Name of Substance | Char |
| SUSTDTC | Start Date/Time | Char |

### Common Categories (SUCAT)
- TOBACCO
- ALCOHOL
- CAFFEINE
- RECREATIONAL DRUG

### Usage Pattern Variables
| Variable | Label | Example |
|----------|-------|---------|
| SUDOSE | Dose | 10 |
| SUDOSU | Units | CIGARETTES/DAY |
| SUOCCUR | Occurrence | Y/N |
| SUSTATUS | Status | CURRENT, FORMER, NEVER |

---

## PR - Procedures

**Purpose:** Therapeutic or diagnostic procedures performed.

### Required Variables
| Variable | Label | Type |
|----------|-------|------|
| STUDYID | Study Identifier | Char |
| DOMAIN | Domain Abbreviation | Char |
| USUBJID | Unique Subject ID | Char |
| PRSEQ | Sequence Number | Num |
| PRTRT | Reported Name of Procedure | Char |
| PRSTDTC | Start Date/Time | Char |

### Coding
- PRDECOD = MedDRA Preferred Term (if diagnosis-related)
- Or use procedure-specific dictionary

### Relationship to AE
- Use RELREC to link procedure to AE if procedure performed due to AE

# Trial Design Domains

## Table of Contents
1. [TA - Trial Arms](#ta---trial-arms)
2. [TE - Trial Elements](#te---trial-elements)
3. [TI - Trial Inclusion/Exclusion](#ti---trial-inclusionexclusion)
4. [TS - Trial Summary](#ts---trial-summary)
5. [TV - Trial Visits](#tv---trial-visits)

---

## Overview

Trial Design Model (TDM) domains describe the study design and are:
- **One record per study** (not per subject)
- Created from protocol, not CRF data
- Required for all studies
- Located in SDTM package (not subject-level)

---

## TA - Trial Arms

**Purpose:** Describe each arm/treatment sequence in the trial.

### Structure
| Variable | Label | Type | Core |
|----------|-------|------|------|
| STUDYID | Study Identifier | Char | Req |
| DOMAIN | Domain Abbreviation | Char | Req |
| ARMCD | Planned Arm Code | Char | Req |
| ARM | Description of Planned Arm | Char | Req |
| TAESSION | Planned Arm Number | Num | Req |
| ETCD | Element Code | Char | Req |
| ELEMENT | Description of Element | Char | Req |
| TABESSION | Order of Element in Arm | Num | Req |
| EPOCH | Epoch | Char | Req |

### Example
```
STUDYID  ARMCD    ARM                TAESSION  ETCD      ELEMENT      TABESSION  EPOCH
ABC123   TRT-A    Drug A 100mg       1         SCRN      Screening    1          SCREENING
ABC123   TRT-A    Drug A 100mg       1         TRT-A     Drug A       2          TREATMENT
ABC123   TRT-A    Drug A 100mg       1         FU        Follow-up    3          FOLLOW-UP
ABC123   PBO      Placebo            2         SCRN      Screening    1          SCREENING
ABC123   PBO      Placebo            2         PBO       Placebo      2          TREATMENT
ABC123   PBO      Placebo            2         FU        Follow-up    3          FOLLOW-UP
```

### Rules
- One record per element per arm
- TAESSION = arm number (sequential)
- TABESSION = element order within arm
- ARMCD/ARM must match values used in DM

---

## TE - Trial Elements

**Purpose:** Define each unique element (building block) of the trial.

### Structure
| Variable | Label | Type | Core |
|----------|-------|------|------|
| STUDYID | Study Identifier | Char | Req |
| DOMAIN | Domain Abbreviation | Char | Req |
| ETCD | Element Code | Char | Req |
| ELEMENT | Description of Element | Char | Req |
| TESTRL | Rule for Start of Element | Char | Perm |
| TEENRL | Rule for End of Element | Char | Perm |
| TEDUR | Planned Duration | Char | Perm |

### Example
```
STUDYID  ETCD   ELEMENT      TESTRL                    TEENRL                      TEDUR
ABC123   SCRN   Screening    Informed consent signed   Day -1                      P28D
ABC123   TRT-A  Drug A       Randomization             Completion of Week 12       P84D
ABC123   PBO    Placebo      Randomization             Completion of Week 12       P84D
ABC123   FU     Follow-up    End of treatment          Day 30 post last dose       P30D
```

### Duration Format (ISO 8601)
- PnD = n days (e.g., P28D = 28 days)
- PnW = n weeks (e.g., P12W = 12 weeks)
- PnM = n months
- PnY = n years

---

## TI - Trial Inclusion/Exclusion Criteria

**Purpose:** Document eligibility criteria from protocol.

### Structure
| Variable | Label | Type | Core |
|----------|-------|------|------|
| STUDYID | Study Identifier | Char | Req |
| DOMAIN | Domain Abbreviation | Char | Req |
| IETESTCD | Inclusion/Exclusion Criterion Short Name | Char | Req |
| IETEST | Inclusion/Exclusion Criterion | Char | Req |
| IECAT | Inclusion/Exclusion Category | Char | Req |
| IESCAT | Subcategory | Char | Perm |
| TIRL | Criterion Rule | Char | Perm |
| TIVERS | Protocol Version | Char | Perm |

### Example
```
STUDYID  IETESTCD  IETEST                                      IECAT
ABC123   INCL01    Age >= 18 years                             INCLUSION
ABC123   INCL02    Diagnosis of Type 2 Diabetes                INCLUSION
ABC123   INCL03    HbA1c between 7.0% and 10.0%               INCLUSION
ABC123   EXCL01    Pregnancy or lactation                      EXCLUSION
ABC123   EXCL02    Hypersensitivity to study drug             EXCLUSION
ABC123   EXCL03    Participation in another study in 30 days  EXCLUSION
```

### IECAT Values
- INCLUSION
- EXCLUSION

---

## TS - Trial Summary

**Purpose:** Key protocol parameters in name-value pair format.

### Structure
| Variable | Label | Type | Core |
|----------|-------|------|------|
| STUDYID | Study Identifier | Char | Req |
| DOMAIN | Domain Abbreviation | Char | Req |
| TSSEQ | Sequence Number | Num | Req |
| TSGRPID | Group ID | Char | Perm |
| TSPARMCD | Trial Summary Parameter Code | Char | Req |
| TSPARM | Trial Summary Parameter | Char | Req |
| TSVAL | Parameter Value | Char | Req |
| TSVALNF | Parameter Null Flavor | Char | Perm |
| TSVALCD | Parameter Value Code | Char | Perm |
| TSVCDREF | Code Reference | Char | Perm |
| TSVCDVER | Code Version | Char | Perm |

### Required TS Parameters
| TSPARMCD | TSPARM | Example TSVAL |
|----------|--------|---------------|
| ADDON | Added on to Existing Treatments | Y |
| AGEMAX | Planned Maximum Age of Subjects | P65Y |
| AGEMIN | Planned Minimum Age of Subjects | P18Y |
| LENGTH | Trial Length | P52W |
| OBJPRIM | Trial Primary Objective | Evaluate efficacy of Drug A |
| OUTMSPRI | Primary Outcome Measure | Change from baseline in HbA1c |
| PCLAS | Pharmacologic Class | SGLT2 Inhibitor |
| PLESSION | Planned Number of Subjects | 300 |
| RANDOM | Trial is Randomized | Y |
| REGID | Registry Identifier | NCT12345678 |
| SPONSOR | Clinical Study Sponsor | ABC Pharma |
| STYPE | Study Type | INTERVENTIONAL |
| TITLE | Trial Title | Phase 3 Study of Drug A in T2DM |
| TTYPE | Trial Type | EFFICACY |
| TPHASE | Trial Phase Title | PHASE III TRIAL |
| INDIC | Trial Disease/Condition Indication | Type 2 Diabetes Mellitus |
| TRT | Investigational Therapy or Treatment | Drug A 100 mg |
| COMPTRT | Comparator Treatment | Placebo |
| STOESSION | Stop Rules | See protocol Section 5.4 |

### Age Format (ISO 8601)
- P18Y = 18 years
- P6M = 6 months
- P999Y = no maximum

---

## TV - Trial Visits

**Purpose:** Planned visits/timepoints defined in protocol.

### Structure
| Variable | Label | Type | Core |
|----------|-------|------|------|
| STUDYID | Study Identifier | Char | Req |
| DOMAIN | Domain Abbreviation | Char | Req |
| VISITNUM | Visit Number | Num | Req |
| VISIT | Visit Name | Char | Req |
| VISITDY | Planned Study Day of Visit | Num | Perm |
| ARMCD | Planned Arm Code | Char | Perm |
| ARM | Description of Planned Arm | Char | Perm |
| TVSTRL | Visit Start Rule | Char | Perm |
| TVENRL | Visit End Rule | Char | Perm |

### Example
```
VISITNUM  VISIT        VISITDY  ARMCD   TVSTRL
1         SCREENING    -28
2         BASELINE     1                First dose
3         WEEK 2       15               14 days after first dose ± 3 days
4         WEEK 4       29               28 days after first dose ± 3 days
5         WEEK 8       57               56 days after first dose ± 5 days
6         WEEK 12      85               84 days after first dose ± 5 days
7         FOLLOW-UP    115              30 days after last dose ± 7 days
```

### Visit Numbering Convention
- Integers for scheduled visits (1, 2, 3...)
- Decimals for unscheduled (2.1, 2.2...)
- Consistent across study

### Arm-Specific Visits
If visits differ by arm, include ARMCD/ARM columns to specify which arm the visit applies to.

---

## Creating Trial Design Datasets

### Source Documents
1. **Protocol** - Primary source for all TDM domains
2. **Schedule of Assessments** - Visit structure (TV)
3. **Study Synopsis** - Summary parameters (TS)
4. **Statistical Analysis Plan** - Analysis populations, endpoints

### Order of Creation
1. TE (Elements) - Basic building blocks
2. TA (Arms) - How elements combine into arms
3. TV (Visits) - Visit schedule
4. TI (Inclusion/Exclusion) - Eligibility criteria
5. TS (Summary) - Protocol parameters

### Validation
- ARMCD/ARM in TA must match DM values
- VISITNUM in TV should match SV values
- TS must include all required parameters
- TI must cover all protocol I/E criteria

# Interventions Class Domains

Interventions describe investigational treatments, therapeutic procedures, and substances administered to subjects.

## General Interventions Structure

| Variable | Label | Role | Notes |
|----------|-------|------|-------|
| --TRT | Reported Name of Treatment | Topic | Verbatim/reported name |
| --DECOD | Standardized Treatment Name | Synonym | Coded/dictionary term |
| --CAT | Category | Grouping | Sponsor-defined category |
| --SCAT | Subcategory | Grouping | Sponsor-defined subcategory |
| --PRESP | Pre-specified | Record Qualifier | Y if collected per CRF design |
| --OCCUR | Occurrence | Record Qualifier | Y/N if pre-specified |
| --DOSE | Dose | Record Qualifier | Numeric dose amount |
| --DOSU | Dose Units | Variable Qualifier | Units for dose |
| --DOSFRM | Dose Form | Variable Qualifier | Tablet, injection, etc. |
| --DOSFRQ | Dosing Frequency | Variable Qualifier | QD, BID, etc. |
| --ROUTE | Route of Administration | Variable Qualifier | ORAL, IV, etc. |
| --STDTC | Start Date/Time | Timing | ISO 8601 format |
| --ENDTC | End Date/Time | Timing | ISO 8601 format |
| --STDY | Study Day of Start | Timing | Derived from RFSTDTC |
| --ENDY | Study Day of End | Timing | Derived from RFSTDTC |

---

## EX - Exposure

**Purpose:** Record of investigational product administration as protocol-specified.

**Key Variables:**

| Variable | Label | Type | Required | CT |
|----------|-------|------|----------|-----|
| STUDYID | Study Identifier | Char | Req | - |
| DOMAIN | Domain Abbreviation | Char | Req | EX |
| USUBJID | Unique Subject Identifier | Char | Req | - |
| EXSEQ | Sequence Number | Num | Req | - |
| EXTRT | Name of Treatment | Char | Req | - |
| EXCAT | Category of Treatment | Char | Perm | - |
| EXDOSE | Dose | Num | Exp | - |
| EXDOSU | Dose Units | Char | Exp | UNIT |
| EXDOSFRM | Dose Form | Char | Exp | FRM |
| EXDOSFRQ | Dosing Frequency per Interval | Char | Perm | FREQ |
| EXROUTE | Route of Administration | Char | Exp | ROUTE |
| EXLOT | Lot Number | Char | Perm | - |
| EXLOC | Location of Dose Administration | Char | Perm | LOC |
| EXLAT | Laterality | Char | Perm | LAT |
| EXDIR | Directionality | Char | Perm | DIR |
| EXFAST | Fasting Status | Char | Perm | NY |
| EXADJ | Reason for Dose Adjustment | Char | Perm | - |
| EPOCH | Epoch | Char | Perm | EPOCH |
| EXSTDTC | Start Date/Time of Treatment | Char | Exp | - |
| EXENDTC | End Date/Time of Treatment | Char | Exp | - |
| EXSTDY | Study Day of Start | Num | Perm | - |
| EXENDY | Study Day of End | Num | Perm | - |
| EXDUR | Duration | Char | Perm | - |

**Sort Order:** STUDYID, USUBJID, EXTRT, EXSTDTC, EXSEQ

**EX vs EC:**
- EX: Protocol-specified exposure as intended
- EC: Exposure as collected/recorded by site

---

## EC - Exposure as Collected

**Purpose:** Exposure data as recorded by site (before deriving EX).

**Use When:**
- Raw collection differs from protocol-specified recording
- Need to preserve original site entries
- Complex dosing regimens

**Additional Variables vs EX:**

| Variable | Label | Type |
|----------|-------|------|
| ECDOSE | Collected Dose | Num |
| ECDOSTXT | Dose Description | Char |
| ECDOSU | Collected Dose Units | Char |
| ECMOOD | Mood | Char |

**ECMOOD Values:**
- SCHEDULED: Planned per protocol
- PERFORMED: Actually administered
- NOT DONE: Scheduled but not done

---

## CM - Concomitant/Prior Medications

**Purpose:** All non-study medications taken before or during study.

**Key Variables:**

| Variable | Label | Type | Required | CT |
|----------|-------|------|----------|-----|
| STUDYID | Study Identifier | Char | Req | - |
| DOMAIN | Domain Abbreviation | Char | Req | CM |
| USUBJID | Unique Subject Identifier | Char | Req | - |
| CMSEQ | Sequence Number | Num | Req | - |
| CMTRT | Reported Name of Drug | Char | Req | - |
| CMMODIFY | Modified Reported Name | Char | Perm | - |
| CMDECOD | Standardized Medication Name | Char | Perm | WHODrug/MedDRA |
| CMCAT | Category | Char | Perm | - |
| CMSCAT | Subcategory | Char | Perm | - |
| CMPRESP | Pre-specified | Char | Perm | NY |
| CMOCCUR | Occurrence | Char | Perm | NY |
| CMSTAT | Completion Status | Char | Perm | ND |
| CMREASND | Reason Not Done | Char | Perm | - |
| CMINDC | Indication | Char | Perm | - |
| CMCLAS | Medication Class | Char | Perm | - |
| CMCLASCD | Medication Class Code | Char | Perm | - |
| CMDOSE | Dose | Num | Perm | - |
| CMDOSTXT | Dose Description | Char | Perm | - |
| CMDOSU | Dose Units | Char | Perm | UNIT |
| CMDOSFRM | Dose Form | Char | Perm | FRM |
| CMDOSFRQ | Dosing Frequency | Char | Perm | FREQ |
| CMROUTE | Route of Administration | Char | Perm | ROUTE |
| CMSTDTC | Start Date/Time | Char | Perm | - |
| CMENDTC | End Date/Time | Char | Perm | - |
| CMSTDY | Study Day of Start | Num | Perm | - |
| CMENDY | Study Day of End | Num | Perm | - |
| CMENRF | End Relative to Reference Period | Char | Perm | STENRF |
| CMSTRF | Start Relative to Reference Period | Char | Perm | STENRF |

**Sort Order:** STUDYID, USUBJID, CMTRT, CMSTDTC, CMSEQ

**CMSTRF/CMENRF Values:**
- BEFORE: Before reference period (prior medication)
- DURING: During reference period (concomitant)
- AFTER: After reference period
- DURING/AFTER: Started during, continued after
- BEFORE/DURING: Started before, continued during

**Coding Notes:**
- CMTRT: Verbatim as reported
- CMDECOD: WHODrug Preferred Name or equivalent
- CMCLAS: ATC Class or equivalent
- CMINDC: Can link to AE via RELREC

---

## SU - Substance Use

**Purpose:** Tobacco, alcohol, caffeine, recreational drug use.

**Key Variables:**

| Variable | Label | Type | Required | CT |
|----------|-------|------|----------|-----|
| STUDYID | Study Identifier | Char | Req | - |
| DOMAIN | Domain Abbreviation | Char | Req | SU |
| USUBJID | Unique Subject Identifier | Char | Req | - |
| SUSEQ | Sequence Number | Num | Req | - |
| SUTRT | Reported Name of Substance | Char | Req | - |
| SUCAT | Category | Char | Perm | - |
| SUSCAT | Subcategory | Char | Perm | - |
| SUPRESP | Pre-specified | Char | Perm | NY |
| SUOCCUR | Occurrence | Char | Perm | NY |
| SUSTAT | Completion Status | Char | Perm | ND |
| SUDOSE | Substance Use Consumption | Num | Perm | - |
| SUDOSTXT | Substance Use Consumption Text | Char | Perm | - |
| SUDOSU | Consumption Units | Char | Perm | UNIT |
| SUDOSFRQ | Use Frequency | Char | Perm | FREQ |
| SUROUTE | Route of Administration | Char | Perm | ROUTE |
| SUSTDTC | Start Date/Time | Char | Perm | - |
| SUENDTC | End Date/Time | Char | Perm | - |
| SUSTRF | Start Relative to Reference | Char | Perm | STENRF |
| SUENRF | End Relative to Reference | Char | Perm | STENRF |

**Common Categories:**
- TOBACCO: Cigarettes, cigars, pipes, smokeless
- ALCOHOL: Beer, wine, spirits
- CAFFEINE: Coffee, tea, energy drinks
- RECREATIONAL DRUGS: By specific substance

**Example:**
| USUBJID | SUSEQ | SUTRT | SUCAT | SUDOSE | SUDOSU | SUDOSFRQ |
|---------|-------|-------|-------|--------|--------|----------|
| SUBJ001 | 1 | CIGARETTES | TOBACCO | 10 | CIGARETTES | QD |
| SUBJ001 | 2 | BEER | ALCOHOL | 2 | DRINKS | PER WEEK |
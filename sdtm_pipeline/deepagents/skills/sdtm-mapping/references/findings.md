# Findings Class Domains

Findings record observations and measurements about subjects during study conduct.

## General Findings Structure

| Variable | Label | Role | Notes |
|----------|-------|------|-------|
| --TESTCD | Test Short Name | Topic | ≤8 characters, controlled |
| --TEST | Test Name | Synonym | Full name of test |
| --CAT | Category | Grouping | Sponsor-defined |
| --SCAT | Subcategory | Grouping | Sponsor-defined |
| --POS | Position | Record Qualifier | SITTING, STANDING, SUPINE |
| --ORRES | Result or Finding | Result Qualifier | Original result |
| --ORRESU | Original Units | Variable Qualifier | Units as collected |
| --ORNRLO | Reference Range Lower | Variable Qualifier | Normal range low |
| --ORNRHI | Reference Range Upper | Variable Qualifier | Normal range high |
| --STRESC | Standardized Result (Char) | Result Qualifier | Standardized character |
| --STRESN | Standardized Result (Num) | Result Qualifier | Standardized numeric |
| --STRESU | Standard Units | Variable Qualifier | Standard units |
| --STNRLO | Standard Reference Low | Variable Qualifier | Standardized normal low |
| --STNRHI | Standard Reference High | Variable Qualifier | Standardized normal high |
| --STNRC | Reference Range for Char | Variable Qualifier | For character results |
| --NRIND | Reference Range Indicator | Variable Qualifier | NORMAL, HIGH, LOW |
| --STAT | Completion Status | Record Qualifier | NOT DONE only |
| --REASND | Reason Not Done | Record Qualifier | Reason for --STAT |
| --LOC | Location | Record Qualifier | Anatomical location |
| --LAT | Laterality | Variable Qualifier | LEFT, RIGHT, BILATERAL |
| --METHOD | Method | Record Qualifier | Test method |
| --BLFL | Baseline Flag | Record Qualifier | Y for baseline record |
| --DRVFL | Derived Flag | Record Qualifier | Y if derived |
| --EXCLFL | Exclusion Flag | Record Qualifier | Y if excluded |
| --DTC | Date/Time | Timing | ISO 8601 |
| --DY | Study Day | Timing | Derived from RFSTDTC |

---

## LB - Laboratory Test Results

**Purpose:** All laboratory measurements performed during study.

**Key Variables:**

| Variable | Label | Type | Required | CT |
|----------|-------|------|----------|-----|
| STUDYID | Study Identifier | Char | Req | - |
| DOMAIN | Domain Abbreviation | Char | Req | LB |
| USUBJID | Unique Subject Identifier | Char | Req | - |
| LBSEQ | Sequence Number | Num | Req | - |
| LBREFID | Specimen ID | Char | Perm | - |
| LBSPID | Sponsor-Defined Identifier | Char | Perm | - |
| LBTESTCD | Lab Test Short Name | Char | Req | LBTESTCD |
| LBTEST | Lab Test Name | Char | Req | LBTEST |
| LBCAT | Category | Char | Perm | - |
| LBSCAT | Subcategory | Char | Perm | - |
| LBORRES | Result or Finding | Char | Exp | - |
| LBORRESU | Original Units | Char | Exp | UNIT |
| LBORNRLO | Reference Range Lower Limit | Char | Exp | - |
| LBORNRHI | Reference Range Upper Limit | Char | Exp | - |
| LBSTRESC | Character Result | Char | Exp | - |
| LBSTRESN | Numeric Result | Num | Exp | - |
| LBSTRESU | Standard Units | Char | Exp | UNIT |
| LBSTNRLO | Standard Reference Lower | Num | Exp | - |
| LBSTNRHI | Standard Reference Upper | Num | Exp | - |
| LBSTNRC | Reference Range for Char Result | Char | Perm | - |
| LBNRIND | Reference Range Indicator | Char | Perm | NRIND |
| LBSTAT | Completion Status | Char | Perm | ND |
| LBREASND | Reason Not Done | Char | Perm | - |
| LBNAM | Vendor Name | Char | Perm | - |
| LBLOINC | LOINC Code | Char | Perm | - |
| LBSPEC | Specimen Type | Char | Perm | SPEC |
| LBSPCCND | Specimen Condition | Char | Perm | SPCCND |
| LBMETHOD | Method of Test | Char | Perm | METHOD |
| LBBLFL | Baseline Flag | Char | Perm | NY |
| LBFAST | Fasting Status | Char | Perm | NY |
| LBDRVFL | Derived Flag | Char | Perm | NY |
| LBTOX | Toxicity | Char | Perm | - |
| LBTOXGR | Standard Toxicity Grade | Char | Perm | - |
| VISITNUM | Visit Number | Num | Exp | - |
| VISIT | Visit Name | Char | Perm | - |
| VISITDY | Planned Study Day of Visit | Num | Perm | - |
| EPOCH | Epoch | Char | Perm | EPOCH |
| LBDTC | Date/Time of Specimen | Char | Exp | - |
| LBDY | Study Day of Specimen | Num | Perm | - |
| LBTPT | Planned Time Point Name | Char | Perm | - |
| LBTPTNUM | Planned Time Point Number | Num | Perm | - |
| LBELTM | Planned Elapsed Time from TPTREF | Char | Perm | - |
| LBTPTREF | Time Point Reference | Char | Perm | - |
| LBRFTDTC | Date/Time of Reference Time Point | Char | Perm | - |

**Sort Order:** STUDYID, USUBJID, LBTESTCD, LBDTC, LBSEQ

**Common LBTESTCD Values:**
- HEMATOLOGY: WBC, RBC, HGB, HCT, PLAT, NEUT, LYMPH, MONO, EOS, BASO
- CHEMISTRY: ALT, AST, ALP, BILI, BUN, CREAT, GLUC, SODIUM, POTASSIUM
- COAGULATION: PT, APTT, INR
- URINALYSIS: URPROT, URGLUC, UROBIL, URPH

**Unit Standardization:**
| Original | Standard | Conversion |
|----------|----------|------------|
| g/dL | g/L | × 10 |
| mg/dL | mmol/L | varies by analyte |
| μmol/L | mg/dL | varies by analyte |
| 10^9/L | GI/L | 1:1 |

---

## VS - Vital Signs

**Purpose:** Vital sign measurements.

**Key Variables:**

| Variable | Label | Type | Required | CT |
|----------|-------|------|----------|-----|
| STUDYID | Study Identifier | Char | Req | - |
| DOMAIN | Domain Abbreviation | Char | Req | VS |
| USUBJID | Unique Subject Identifier | Char | Req | - |
| VSSEQ | Sequence Number | Num | Req | - |
| VSTESTCD | Vital Signs Test Short Name | Char | Req | VSTESTCD |
| VSTEST | Vital Signs Test Name | Char | Req | VSTEST |
| VSCAT | Category | Char | Perm | - |
| VSSCAT | Subcategory | Char | Perm | - |
| VSPOS | Position of Subject | Char | Perm | POSITION |
| VSORRES | Result or Finding | Char | Exp | - |
| VSORRESU | Original Units | Char | Exp | UNIT |
| VSSTRESC | Character Result | Char | Exp | - |
| VSSTRESN | Numeric Result | Num | Exp | - |
| VSSTRESU | Standard Units | Char | Exp | UNIT |
| VSSTAT | Completion Status | Char | Perm | ND |
| VSREASND | Reason Not Done | Char | Perm | - |
| VSLOC | Location of Measurement | Char | Perm | LOC |
| VSLAT | Laterality | Char | Perm | LAT |
| VSBLFL | Baseline Flag | Char | Perm | NY |
| VISITNUM | Visit Number | Num | Exp | - |
| VISIT | Visit Name | Char | Perm | - |
| EPOCH | Epoch | Char | Perm | EPOCH |
| VSDTC | Date/Time | Char | Exp | - |
| VSDY | Study Day | Num | Perm | - |
| VSTPT | Planned Time Point | Char | Perm | - |
| VSTPTNUM | Planned Time Point Number | Num | Perm | - |

**Sort Order:** STUDYID, USUBJID, VSTESTCD, VSDTC, VSSEQ

**Standard VSTESTCD Values:**
| VSTESTCD | VSTEST | VSSTRESU |
|----------|--------|----------|
| SYSBP | Systolic Blood Pressure | mmHg |
| DIABP | Diastolic Blood Pressure | mmHg |
| PULSE | Pulse Rate | beats/min |
| RESP | Respiratory Rate | breaths/min |
| TEMP | Temperature | C |
| HEIGHT | Height | cm |
| WEIGHT | Weight | kg |
| BMI | Body Mass Index | kg/m2 |

---

## EG - ECG Test Results

**Purpose:** Electrocardiogram measurements.

**Key Variables:**

| Variable | Label | Type | Required | CT |
|----------|-------|------|----------|-----|
| STUDYID | Study Identifier | Char | Req | - |
| DOMAIN | Domain Abbreviation | Char | Req | EG |
| USUBJID | Unique Subject Identifier | Char | Req | - |
| EGSEQ | Sequence Number | Num | Req | - |
| EGTESTCD | ECG Test Short Name | Char | Req | EGTESTCD |
| EGTEST | ECG Test Name | Char | Req | EGTEST |
| EGCAT | Category | Char | Perm | - |
| EGPOS | Position of Subject | Char | Perm | POSITION |
| EGORRES | Result or Finding | Char | Exp | - |
| EGORRESU | Original Units | Char | Exp | UNIT |
| EGSTRESC | Character Result | Char | Exp | - |
| EGSTRESN | Numeric Result | Num | Exp | - |
| EGSTRESU | Standard Units | Char | Exp | UNIT |
| EGSTAT | Completion Status | Char | Perm | ND |
| EGREASND | Reason Not Done | Char | Perm | - |
| EGMETHOD | Method of Test | Char | Perm | METHOD |
| EGLEAD | Lead Location | Char | Perm | - |
| EGBLFL | Baseline Flag | Char | Perm | NY |
| EGEVAL | Evaluator | Char | Perm | - |
| VISITNUM | Visit Number | Num | Exp | - |
| VISIT | Visit Name | Char | Perm | - |
| EPOCH | Epoch | Char | Perm | EPOCH |
| EGDTC | Date/Time | Char | Exp | - |
| EGDY | Study Day | Num | Perm | - |
| EGTPT | Planned Time Point | Char | Perm | - |

**Standard EGTESTCD Values:**
| EGTESTCD | EGTEST | EGSTRESU |
|----------|--------|----------|
| HRMEAN | Mean Heart Rate | beats/min |
| PRMEAN | Mean PR Interval | msec |
| QRSMEAN | Mean QRS Duration | msec |
| QTMEAN | Mean QT Interval | msec |
| QTCFMEA | Mean QTcF Interval | msec |
| RRMEAN | Mean RR Interval | msec |
| INTP | Interpretation | - |

---

## PE - Physical Examination

**Purpose:** Physical examination findings by body system.

**Key Variables:**

| Variable | Label | Type | Required |
|----------|-------|------|----------|
| STUDYID | Study Identifier | Char | Req |
| DOMAIN | Domain Abbreviation | Char | Req |
| USUBJID | Unique Subject Identifier | Char | Req |
| PESEQ | Sequence Number | Num | Req |
| PETESTCD | PE Test Short Name | Char | Req |
| PETEST | PE Test Name | Char | Req |
| PECAT | Category | Char | Perm |
| PEBODSYS | Body System Examined | Char | Exp |
| PEORRES | Result or Finding | Char | Exp |
| PESTRESC | Character Result | Char | Exp |
| PESTAT | Completion Status | Char | Perm |
| PEREASND | Reason Not Done | Char | Perm |
| PELOC | Location of Finding | Char | Perm |
| PEMETHOD | Method of Examination | Char | Perm |
| VISITNUM | Visit Number | Num | Exp |
| PEDTC | Date/Time of Examination | Char | Exp |

---

## QS - Questionnaires

**Purpose:** Subject-reported outcomes, quality of life, other questionnaires.

**Key Variables:**

| Variable | Label | Type | Required |
|----------|-------|------|----------|
| STUDYID | Study Identifier | Char | Req |
| DOMAIN | Domain Abbreviation | Char | Req |
| USUBJID | Unique Subject Identifier | Char | Req |
| QSSEQ | Sequence Number | Num | Req |
| QSTESTCD | Question Short Name | Char | Req |
| QSTEST | Question Name | Char | Req |
| QSCAT | Category of Question | Char | Req |
| QSSCAT | Subcategory | Char | Perm |
| QSORRES | Finding in Original Units | Char | Exp |
| QSORRESU | Original Units | Char | Perm |
| QSSTRESC | Character Result | Char | Exp |
| QSSTRESN | Numeric Result | Num | Perm |
| QSSTRESU | Standard Units | Char | Perm |
| QSSTAT | Completion Status | Char | Perm |
| QSREASND | Reason Not Done | Char | Perm |
| QSBLFL | Baseline Flag | Char | Perm |
| QSEVAL | Evaluator | Char | Perm |
| VISITNUM | Visit Number | Num | Exp |
| QSDTC | Date/Time of Finding | Char | Exp |

**QSCAT Usage:**
- Use standardized questionnaire name (e.g., "SF-36", "EQ-5D", "HAMD-17")
- QSTESTCD/QSTEST should match SDTM Terminology for standard instruments

---

## SC - Subject Characteristics

**Purpose:** Subject attributes not fitting DM or other domains.

**Key Variables:**

| Variable | Label | Type | Required |
|----------|-------|------|----------|
| STUDYID | Study Identifier | Char | Req |
| DOMAIN | Domain Abbreviation | Char | Req |
| USUBJID | Unique Subject Identifier | Char | Req |
| SCSEQ | Sequence Number | Num | Req |
| SCTESTCD | Subject Characteristic Short Name | Char | Req |
| SCTEST | Subject Characteristic Name | Char | Req |
| SCCAT | Category | Char | Perm |
| SCORRES | Result or Finding | Char | Exp |
| SCORRESU | Original Units | Char | Perm |
| SCSTRESC | Character Result | Char | Exp |
| SCSTRESN | Numeric Result | Num | Perm |
| SCSTRESU | Standard Units | Char | Perm |
| SCDTC | Date/Time | Char | Perm |

**Common SC Data:**
- Educational level
- Employment status
- Handedness
- Skin phototype
- Reproductive status
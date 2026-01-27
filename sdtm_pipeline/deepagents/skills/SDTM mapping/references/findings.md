# Findings Domain Class

## Table of Contents
1. [LB - Laboratory Test Results](#lb---laboratory-test-results)
2. [VS - Vital Signs](#vs---vital-signs)
3. [EG - ECG Test Results](#eg---ecg-test-results)
4. [PE - Physical Examination](#pe---physical-examination)
5. [QS - Questionnaires](#qs---questionnaires)
6. [SC - Subject Characteristics](#sc---subject-characteristics)
7. [FA - Findings About Events/Interventions](#fa---findings-about)

---

## LB - Laboratory Test Results

**Purpose:** Laboratory test results including hematology, chemistry, urinalysis.

### Required Variables
| Variable | Label | Type | CT Codelist |
|----------|-------|------|-------------|
| STUDYID | Study Identifier | Char | - |
| DOMAIN | Domain Abbreviation | Char | "LB" |
| USUBJID | Unique Subject ID | Char | - |
| LBSEQ | Sequence Number | Num | - |
| LBTESTCD | Lab Test Short Name | Char | LBTESTCD (C65047) |
| LBTEST | Lab Test Name | Char | LBTEST |
| LBORRES | Result or Finding Original | Char | - |
| LBORRESU | Original Units | Char | UNIT (C71620) |
| LBSTRESC | Standardized Result (Char) | Char | - |
| LBSTRESN | Standardized Result (Num) | Num | - |
| LBSTRESU | Standardized Units | Char | UNIT (C71620) |
| LBDTC | Date/Time of Specimen | Char | ISO 8601 |

### Expected Variables
| Variable | Label | Type | Notes |
|----------|-------|------|-------|
| LBCAT | Category of Lab Test | Char | HEMATOLOGY, CHEMISTRY, URINALYSIS |
| LBSCAT | Subcategory | Char | - |
| LBSPEC | Specimen Type | Char | SPECTYPE (C78734) |
| LBMETHOD | Method of Test | Char | METHOD |
| LBORNRLO | Reference Range Lower (Orig) | Char | - |
| LBORNRHI | Reference Range Upper (Orig) | Char | - |
| LBSTNRLO | Reference Range Lower (Std) | Num | - |
| LBSTNRHI | Reference Range Upper (Std) | Num | - |
| LBNRIND | Reference Range Indicator | Char | NRIND (C78736) |
| LBBLFL | Baseline Flag | Char | NY |
| VISITNUM | Visit Number | Num | - |
| VISIT | Visit Name | Char | - |
| EPOCH | Epoch | Char | EPOCH |
| LBFAST | Fasting Status | Char | NY |
| LBTOX | Toxicity | Char | - |
| LBTOXGR | Toxicity Grade | Char | CTCAE grade |

### Key Derivations

**Unit Standardization:**
```
Original → Standard conversions:
g/dL → g/L: multiply by 10
mg/dL → mmol/L: divide by molecular weight factor
U/L → μkat/L: divide by 60
```

**Baseline Flag (LBBLFL):**
```
Set LBBLFL = "Y" for:
- Last non-missing value before first dose (RFSTDTC)
- Per test (LBTESTCD)
- One baseline per test per subject
```

**Reference Range Indicator (LBNRIND):**
```
If LBSTRESN < LBSTNRLO then LBNRIND = "LOW"
If LBSTRESN > LBSTNRHI then LBNRIND = "HIGH"
If LBSTNRLO <= LBSTRESN <= LBSTNRHI then LBNRIND = "NORMAL"
If ranges missing then LBNRIND = null
```

### Common Lab Tests (LBTESTCD)
| LBTESTCD | LBTEST | LBCAT |
|----------|--------|-------|
| ALB | Albumin | CHEMISTRY |
| ALP | Alkaline Phosphatase | CHEMISTRY |
| ALT | Alanine Aminotransferase | CHEMISTRY |
| AST | Aspartate Aminotransferase | CHEMISTRY |
| BILI | Bilirubin | CHEMISTRY |
| BUN | Blood Urea Nitrogen | CHEMISTRY |
| CREAT | Creatinine | CHEMISTRY |
| GLUC | Glucose | CHEMISTRY |
| HBA1C | Hemoglobin A1C | CHEMISTRY |
| SODIUM | Sodium | CHEMISTRY |
| POTASSIUM | Potassium | CHEMISTRY |
| HGB | Hemoglobin | HEMATOLOGY |
| HCT | Hematocrit | HEMATOLOGY |
| WBC | Leukocytes | HEMATOLOGY |
| RBC | Erythrocytes | HEMATOLOGY |
| PLAT | Platelets | HEMATOLOGY |
| NEUT | Neutrophils | HEMATOLOGY |
| LYMPH | Lymphocytes | HEMATOLOGY |

---

## VS - Vital Signs

**Purpose:** Vital sign measurements (blood pressure, heart rate, temperature, etc.).

### Required Variables
| Variable | Label | Type | CT Codelist |
|----------|-------|------|-------------|
| STUDYID | Study Identifier | Char | - |
| DOMAIN | Domain Abbreviation | Char | "VS" |
| USUBJID | Unique Subject ID | Char | - |
| VSSEQ | Sequence Number | Num | - |
| VSTESTCD | Vital Signs Test Short Name | Char | VSTESTCD (C66741) |
| VSTEST | Vital Signs Test Name | Char | VSTEST |
| VSORRES | Result or Finding Original | Char | - |
| VSORRESU | Original Units | Char | UNIT |
| VSSTRESC | Standardized Result (Char) | Char | - |
| VSSTRESN | Standardized Result (Num) | Num | - |
| VSSTRESU | Standardized Units | Char | UNIT |
| VSDTC | Date/Time of Measurements | Char | ISO 8601 |

### Expected Variables
| Variable | Label | Type |
|----------|-------|------|
| VSPOS | Position of Subject | Char |
| VSLOC | Location of Measurement | Char |
| VSBLFL | Baseline Flag | Char |
| VISITNUM | Visit Number | Num |
| VISIT | Visit Name | Char |
| VSTPT | Planned Time Point Name | Char |
| VSTPTNUM | Planned Time Point Number | Num |

### Standard Vital Signs (VSTESTCD)
| VSTESTCD | VSTEST | Standard Unit |
|----------|--------|---------------|
| SYSBP | Systolic Blood Pressure | mmHg |
| DIABP | Diastolic Blood Pressure | mmHg |
| PULSE | Pulse Rate | beats/min |
| HR | Heart Rate | beats/min |
| RESP | Respiratory Rate | breaths/min |
| TEMP | Temperature | C |
| HEIGHT | Height | cm |
| WEIGHT | Weight | kg |
| BMI | Body Mass Index | kg/m2 |

### Position (VSPOS)
- STANDING
- SITTING
- SUPINE
- PRONE

### Location (VSLOC)
- LEFT ARM
- RIGHT ARM
- ORAL
- AXILLA
- TYMPANIC

---

## EG - ECG Test Results

**Purpose:** Electrocardiogram measurements and interpretations.

### Required Variables
| Variable | Label | Type |
|----------|-------|------|
| STUDYID | Study Identifier | Char |
| DOMAIN | Domain Abbreviation | Char |
| USUBJID | Unique Subject ID | Char |
| EGSEQ | Sequence Number | Num |
| EGTESTCD | ECG Test Short Name | Char |
| EGTEST | ECG Test Name | Char |
| EGORRES | Result or Finding Original | Char |
| EGSTRESC | Standardized Result (Char) | Char |
| EGDTC | Date/Time of ECG | Char |

### Common ECG Tests (EGTESTCD)
| EGTESTCD | EGTEST | Unit |
|----------|--------|------|
| HRMEAN | Mean Heart Rate | beats/min |
| PRMEAN | Mean PR Interval | msec |
| QRSDUR | QRS Duration | msec |
| QTMEAN | Mean QT Interval | msec |
| QTCB | QTc Bazett | msec |
| QTCF | QTc Fridericia | msec |
| INTP | Interpretation | - |

### ECG Interpretation (EGORRES for INTP)
- NORMAL
- ABNORMAL - NOT CLINICALLY SIGNIFICANT
- ABNORMAL - CLINICALLY SIGNIFICANT

---

## PE - Physical Examination

**Purpose:** Physical examination findings.

### Structure
| Variable | Label | Type |
|----------|-------|------|
| STUDYID | Study Identifier | Char |
| DOMAIN | Domain Abbreviation | Char |
| USUBJID | Unique Subject ID | Char |
| PESEQ | Sequence Number | Num |
| PETESTCD | PE Test Short Name | Char |
| PETEST | PE Test Name | Char |
| PEORRES | Result or Finding Original | Char |
| PESTRESC | Standardized Result | Char |
| PEBODSYS | Body System Examined | Char |
| PELOC | Location Examined | Char |
| PEDTC | Date/Time of Examination | Char |

### Common PE Body Systems
- HEAD
- EYES
- EARS
- NOSE
- THROAT
- NECK
- CARDIOVASCULAR
- RESPIRATORY
- GASTROINTESTINAL
- MUSCULOSKELETAL
- NEUROLOGICAL
- SKIN
- LYMPH NODES

### Common Results (PESTRESC)
- NORMAL
- ABNORMAL

---

## QS - Questionnaires

**Purpose:** Questionnaire/scale/rating scores.

### Required Variables
| Variable | Label | Type |
|----------|-------|------|
| STUDYID | Study Identifier | Char |
| DOMAIN | Domain Abbreviation | Char |
| USUBJID | Unique Subject ID | Char |
| QSSEQ | Sequence Number | Num |
| QSTESTCD | Question Short Name | Char |
| QSTEST | Question Name | Char |
| QSCAT | Category of Question | Char |
| QSORRES | Result or Finding Original | Char |
| QSSTRESC | Standardized Result (Char) | Char |
| QSSTRESN | Standardized Result (Num) | Num |
| QSDTC | Date/Time of Finding | Char |

### QSCAT Examples
- SF-36
- EQ-5D
- HADS
- PHQ-9
- WOMAC
- ADAS-COG

### Structure Notes
- One record per question per visit
- Include individual items AND total/subscale scores
- QSTESTCD should be unique within QSCAT

---

## SC - Subject Characteristics

**Purpose:** Subject characteristics not in DM (baseline characteristics).

### Common Uses
- Menopausal status
- Smoking status (if not in SU)
- Childbearing potential
- Disease-specific characteristics

### Structure
| Variable | Label | Type |
|----------|-------|------|
| STUDYID | Study Identifier | Char |
| DOMAIN | Domain Abbreviation | Char |
| USUBJID | Unique Subject ID | Char |
| SCSEQ | Sequence Number | Num |
| SCTESTCD | Subject Char Short Name | Char |
| SCTEST | Subject Characteristic | Char |
| SCORRES | Result or Finding Original | Char |
| SCSTRESC | Standardized Result | Char |
| SCDTC | Date/Time | Char |

---

## FA - Findings About Events or Interventions

**Purpose:** Findings/measurements about records in other domains.

### When to Use
- Severity of an AE (if not using AESEV)
- Lab test circumstances
- Additional characterization of events

### Key Variables
| Variable | Label | Notes |
|----------|-------|-------|
| FAOBJ | Object of Finding | What is being characterized |
| FATESTCD | Test Short Name | What is measured |
| FAORRES | Result | The finding |
| FALNKID | Link ID | Links to parent record |

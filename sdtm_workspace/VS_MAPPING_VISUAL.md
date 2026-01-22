# VS Domain Mapping - Visual Guide

## 1. Data Flow Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    VITALS.csv (Source)                       │
│                      536 Records                              │
│                    Wide Format                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Transform
                       │ (Wide → Long)
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                    vs.csv (Target)                           │
│                    2,184 Records                             │
│                    Long Format                               │
│                    SDTM VS Domain                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Record Expansion - Wide to Long

```
SOURCE VITALS.csv (1 record):
┌─────────────────────────────────────────────────────────────────────┐
│ STUDY   │ PT  │ INVSITE │ VISIT │ VTDT       │ VTBPS2│ VTBPD2│ ... │
│ MAXIS-08│ 001 │ 408     │ 1     │ 2008-08-26 │ 120   │ 96    │     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼──────────────┐
                    │               │              │
                    ↓               ↓              ↓
TARGET vs.csv (6+ records):
┌────────────────────────────────────────────────────────────────────┐
│USUBJID           │VSSEQ│VSTESTCD│VSTEST                │VSORRES│...│
├────────────────────────────────────────────────────────────────────┤
│MAXIS-08-408-001  │  1  │ SYSBP  │Systolic BP           │120.0  │   │
├────────────────────────────────────────────────────────────────────┤
│MAXIS-08-408-001  │  2  │ DIABP  │Diastolic BP          │96.0   │   │
├────────────────────────────────────────────────────────────────────┤
│MAXIS-08-408-001  │  3  │ RESP   │Respiratory Rate      │16.0   │   │
├────────────────────────────────────────────────────────────────────┤
│MAXIS-08-408-001  │  4  │ TEMP   │Temperature           │36.8   │   │
├────────────────────────────────────────────────────────────────────┤
│MAXIS-08-408-001  │  5  │ WEIGHT │Weight                │68.9   │   │
├────────────────────────────────────────────────────────────────────┤
│MAXIS-08-408-001  │  6  │ HEIGHT │Height                │185.0  │   │
└────────────────────────────────────────────────────────────────────┘
```

---

## 3. Source Column → Target Variable Flow

### Identifier Variables
```
┌─────────────┐
│   STUDY     │────────────────────────────────────► STUDYID
└─────────────┘

┌─────────────┐
│  INVSITE    │──┐
└─────────────┘  │
┌─────────────┐  │
│   STUDY     │──┼─── Concatenate with '-' ──────► USUBJID
└─────────────┘  │     (STUDY-SITE-SUBJECT)
┌─────────────┐  │
│     PT      │──┘
└─────────────┘

                 ─── Constant value ──────────────► DOMAIN = 'VS'

                 ─── Sequential numbering ────────► VSSEQ
                     (within USUBJID)
```

### Test Identification
```
┌─────────────┐
│   VTBPS2    │─────► VSTESTCD = 'SYSBP'  ──────► VSTEST = 'Systolic Blood Pressure'
└─────────────┘       VSORRESU = 'mmHg'

┌─────────────┐
│   VTBPD2    │─────► VSTESTCD = 'DIABP'  ──────► VSTEST = 'Diastolic Blood Pressure'
└─────────────┘       VSORRESU = 'mmHg'

┌─────────────┐
│   VTRRT2    │─────► VSTESTCD = 'RESP'   ──────► VSTEST = 'Respiratory Rate'
└─────────────┘       VSORRESU = 'breaths/min'

┌─────────────┐
│   VTTP2     │─────► VSTESTCD = 'TEMP'   ──────► VSTEST = 'Temperature'
└─────────────┘       VSORRESU = 'C'

┌─────────────┐
│   GNNUM1    │─────► VSTESTCD = 'WEIGHT' ──────► VSTEST = 'Weight'
└─────────────┘       VSORRESU = 'kg'

┌─────────────┐
│   GNNUM2    │─────► VSTESTCD = 'HEIGHT' ──────► VSTEST = 'Height'
└─────────────┘       VSORRESU = 'cm'
```

### Result Variables
```
┌──────────────┐
│ Test Column  │────────────────────────────────────────┐
│ (e.g.VTBPS2) │                                        │
└──────────────┘                                        │
                                                         │
        ┌────────────────────────────────────────────────┤
        │                                                │
        ↓                                                ↓
   ┌─────────┐                                      ┌─────────┐
   │ VSORRES │ (Original Result as Character)       │VSORRESU │ (Original Unit)
   └─────────┘                                      └─────────┘
        │                                                │
        │ Standardize                                    │
        │ Convert Units                                  │
        ↓                                                ↓
   ┌─────────┐                                      ┌─────────┐
   │VSSTRESC │ (Standard Result - Character)        │VSSTRESU │ (Standard Unit)
   └─────────┘                                      └─────────┘
        │                                                │
        │ Parse to Numeric                               │
        ↓                                                │
   ┌─────────┐                                          │
   │VSSTRESN │ (Standard Result - Numeric) ◄────────────┘
   └─────────┘
```

### Timing Variables
```
┌─────────────┐
│    VISIT    │────────────────────────────────────► VISITNUM (numeric)
└─────────────┘                                      VISIT (character)

┌─────────────┐
│    VTDT     │──┐
└─────────────┘  │
                 ├─── ISO 8601 format ─────────────► VSDTC
┌─────────────┐  │    (YYYY-MM-DD or
│    VTTM     │──┘     YYYY-MM-DDTHH:MM:SS)
└─────────────┘
```

---

## 4. USUBJID Construction Detail

```
Step 1: Extract Components
┌──────────────────────────────────────────────────────────┐
│  STUDY        PT           INVSITE                       │
│  ↓            ↓            ↓                             │
│  'MAXIS-08'   '001'        'MAXIS_08_408'               │
│                            Split by '_'                  │
│                            Take last segment: '408'      │
└──────────────────────────────────────────────────────────┘

Step 2: Concatenate with Hyphens
┌──────────────────────────────────────────────────────────┐
│  'MAXIS-08'  +  '-'  +  '408'  +  '-'  +  '001'        │
│                                                          │
│  Result: 'MAXIS-08-408-001'                            │
└──────────────────────────────────────────────────────────┘

Step 3: Assign to USUBJID
┌──────────────────────────────────────────────────────────┐
│  USUBJID = 'MAXIS-08-408-001'                          │
└──────────────────────────────────────────────────────────┘
```

---

## 5. VSSEQ Generation Logic

```
All VS Records Sorted by:
  1. USUBJID
  2. VSDTC (Date/Time)
  3. VSTESTCD (Test Code)

Subject: MAXIS-08-408-001
┌──────────────────────────────────────────────────────────────┐
│ VSDTC      │ VSTESTCD │ VSSEQ │ Notes                       │
├──────────────────────────────────────────────────────────────┤
│ 2008-08-26 │ DIABP    │   1   │ Visit 1                     │
│ 2008-08-26 │ HEIGHT   │   2   │ Visit 1                     │
│ 2008-08-26 │ PULSE    │   3   │ Visit 1                     │
│ 2008-08-26 │ RESP     │   4   │ Visit 1                     │
│ 2008-08-26 │ SYSBP    │   5   │ Visit 1                     │
│ 2008-08-26 │ TEMP     │   6   │ Visit 1                     │
│ 2008-08-26 │ WEIGHT   │   7   │ Visit 1                     │
├──────────────────────────────────────────────────────────────┤
│ 2008-09-03 │ DIABP    │   8   │ Visit 2, Measurement 1      │
│ 2008-09-03 │ PULSE    │   9   │ Visit 2, Measurement 1      │
│ 2008-09-03 │ RESP     │  10   │ Visit 2, Measurement 1      │
│ 2008-09-03 │ SYSBP    │  11   │ Visit 2, Measurement 1      │
│ 2008-09-03 │ TEMP     │  12   │ Visit 2, Measurement 1      │
├──────────────────────────────────────────────────────────────┤
│ 2008-09-03 │ DIABP    │  13   │ Visit 2, Measurement 2      │
│ 2008-09-03 │ PULSE    │  14   │ Visit 2, Measurement 2      │
│ 2008-09-03 │ RESP     │  15   │ Visit 2, Measurement 2      │
│ 2008-09-03 │ SYSBP    │  16   │ Visit 2, Measurement 2      │
│ 2008-09-03 │ TEMP     │  17   │ Visit 2, Measurement 2      │
└──────────────────────────────────────────────────────────────┘

Note: VSSEQ continues sequentially across all visits for each subject
```

---

## 6. Unit Conversion Examples

### Temperature: Fahrenheit → Celsius
```
┌─────────────────────────────────────────────────────────┐
│  VSORRES = '98.6'    VSORRESU = 'F'                    │
└─────────────────────────────────────────────────────────┘
                         │
                         │ Apply formula:
                         │ (F - 32) × 5/9
                         ↓
┌─────────────────────────────────────────────────────────┐
│  VSSTRESC = '37.0'   VSSTRESN = 37.0   VSSTRESU = 'C' │
└─────────────────────────────────────────────────────────┘

Example:
  98.6°F → (98.6 - 32) × 5/9 = 37.0°C
```

### Weight: Pounds → Kilograms
```
┌─────────────────────────────────────────────────────────┐
│  VSORRES = '152'     VSORRESU = 'lbs'                  │
└─────────────────────────────────────────────────────────┘
                         │
                         │ Apply formula:
                         │ lbs × 0.453592
                         ↓
┌─────────────────────────────────────────────────────────┐
│  VSSTRESC = '68.9'   VSSTRESN = 68.9   VSSTRESU = 'kg'│
└─────────────────────────────────────────────────────────┘

Example:
  152 lbs → 152 × 0.453592 = 68.9 kg
```

### Height: Inches → Centimeters
```
┌─────────────────────────────────────────────────────────┐
│  VSORRES = '72.8'    VSORRESU = 'in'                   │
└─────────────────────────────────────────────────────────┘
                         │
                         │ Apply formula:
                         │ inches × 2.54
                         ↓
┌─────────────────────────────────────────────────────────┐
│  VSSTRESC = '185.0'  VSSTRESN = 185.0  VSSTRESU = 'cm'│
└─────────────────────────────────────────────────────────┘

Example:
  72.8 inches → 72.8 × 2.54 = 185.0 cm
```

---

## 7. Date/Time Formatting

### Scenario 1: Date Only
```
┌─────────────────────────────────┐
│  VTDT = '2008-08-26'           │
│  VTTM = NULL                    │
└─────────────────────────────────┘
            │
            │ Parse & Convert
            ↓
┌─────────────────────────────────┐
│  VSDTC = '2008-08-26'          │
└─────────────────────────────────┘
```

### Scenario 2: Date + Time
```
┌─────────────────────────────────┐
│  VTDT = '2008-08-26'           │
│  VTTM = '10:30:00'             │
└─────────────────────────────────┘
            │
            │ Combine & Format
            ↓
┌─────────────────────────────────┐
│  VSDTC = '2008-08-26T10:30:00' │
└─────────────────────────────────┘
```

### Scenario 3: Different Date Formats
```
Input Formats              →    Output Format (ISO 8601)
────────────────────────────────────────────────────────
'2008-08-26'              →    '2008-08-26'
'08/26/2008'              →    '2008-08-26'
'26-AUG-2008'             →    '2008-08-26'
'2008-08-26 10:30'        →    '2008-08-26T10:30'
```

---

## 8. Data Quality Check Flow

```
                  ┌─────────────────────┐
                  │  VS Records Created │
                  └──────────┬──────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ↓                    ↓                    ↓
┌───────────────┐   ┌────────────────┐   ┌────────────────┐
│  Required     │   │    Logical     │   │  Range Checks  │
│  Variables    │   │  Consistency   │   │                │
└───────┬───────┘   └────────┬───────┘   └────────┬───────┘
        │                    │                    │
        ↓                    ↓                    ↓
    All 6 must          SYSBP > DIABP         Normal ranges:
    be populated        Height consistent     SYSBP: 90-180
    ✓ STUDYID          Weight reasonable     DIABP: 50-120
    ✓ DOMAIN           Units correct         TEMP: 36.0-38.5
    ✓ USUBJID                                etc.
    ✓ VSSEQ
    ✓ VSTESTCD
    ✓ VSTEST
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                             ↓
                  ┌─────────────────────┐
                  │  Validation Report  │
                  │  - Passed: X        │
                  │  - Warnings: Y      │
                  │  - Errors: Z        │
                  └─────────────────────┘
```

---

## 9. Blood Pressure Consistency Check

```
For each Subject-Visit-DateTime combination:

┌──────────────────────────────────────────────────────┐
│  Record 1: VSTESTCD='SYSBP', VSSTRESN=120 mmHg     │
│  Record 2: VSTESTCD='DIABP', VSSTRESN=96 mmHg      │
└──────────────────────────────────────────────────────┘
                         │
                         ↓
               ┌─────────────────┐
               │ Validate:       │
               │ SYSBP > DIABP?  │
               └─────────────────┘
                         │
            ┌────────────┴────────────┐
            ↓                         ↓
      ┌──────────┐              ┌──────────┐
      │   PASS   │              │   FAIL   │
      │ 120 > 96 │              │ Flag for │
      │    ✓     │              │  Review  │
      └──────────┘              └──────────┘

Additional Check: Pulse Pressure
┌────────────────────────────────────┐
│ PP = SYSBP - DIABP                │
│ PP = 120 - 96 = 24 mmHg           │
│                                    │
│ Normal range: 30-50 mmHg          │
│ Flag if < 20 or > 100             │
└────────────────────────────────────┘
```

---

## 10. Variable Type Summary

```
VS Domain Variables (28 total)

┌──────────────────────────────────────────────────────────┐
│                    Required (6)                          │
├──────────────────────────────────────────────────────────┤
│  STUDYID  │ DOMAIN  │ USUBJID  │ VSSEQ  │ VSTESTCD │ ... │
│  Char(20) │ Char(2) │ Char(40) │ Num(8) │ Char(8)  │     │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                    Expected (12)                         │
├──────────────────────────────────────────────────────────┤
│  VSORRES  │ VSORRESU │ VSSTRESC │ VSSTRESN │ VSSTRESU│..│
│  Char(200)│ Char(40) │ Char(200)│ Num(8)   │ Char(40)│  │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                   Permissible (10)                       │
├──────────────────────────────────────────────────────────┤
│  VSSTAT  │ VSREASND │ VSLOC  │ EPOCH │ VSDY │ VSTPT│ ..│
│  Char(8) │ Char(200)│Char(200)│Char(200)│Num(8)│Char()│  │
└──────────────────────────────────────────────────────────┘

Character Variables: 19
Numeric Variables:    9
Total:               28
```

---

## 11. Transformation Pipeline

```
┌────────────────────────────────────────────────────────────┐
│ Phase 1: Read Source Data                                  │
│ ► Read VITALS.csv (536 records)                           │
└─────────────────────────┬──────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│ Phase 2: Data Validation                                   │
│ ► Check required fields                                    │
│ ► Validate date formats                                    │
│ ► Check data types                                         │
└─────────────────────────┬──────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│ Phase 3: Identifier Generation                             │
│ ► Generate USUBJID (STUDY-SITE-SUBJECT)                   │
│ ► Set DOMAIN = 'VS'                                        │
└─────────────────────────┬──────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│ Phase 4: Wide-to-Long Transformation                       │
│ ► Iterate through vital sign columns                      │
│ ► Create one record per non-null vital sign               │
│ ► Assign VSTESTCD and VSTEST                              │
└─────────────────────────┬──────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│ Phase 5: Result Standardization                            │
│ ► Populate VSORRES, VSORRESU                               │
│ ► Apply unit conversions                                   │
│ ► Generate VSSTRESC, VSSTRESN, VSSTRESU                   │
└─────────────────────────┬──────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│ Phase 6: Timing Variables                                  │
│ ► Convert dates to ISO 8601 (VSDTC)                       │
│ ► Assign VISITNUM and VISIT                                │
└─────────────────────────┬──────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│ Phase 7: Sequence Number Generation                        │
│ ► Sort by USUBJID, VSDTC, VSTESTCD                        │
│ ► Assign sequential VSSEQ within subject                   │
└─────────────────────────┬──────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│ Phase 8: Variable Ordering                                 │
│ ► Order columns per SDTM-IG 3.4 specification             │
│ ► Select final 28 variables                                │
└─────────────────────────┬──────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│ Phase 9: Quality Checks                                    │
│ ► Validate required variables                              │
│ ► Check logical consistency                                │
│ ► Verify ranges                                            │
└─────────────────────────┬──────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│ Phase 10: Write Output                                     │
│ ► Write vs.csv (2,184 records)                            │
│ ► Generate validation report                               │
└────────────────────────────────────────────────────────────┘
```

---

## 12. Record Count Verification

```
Source Analysis:
┌─────────────────────────────────────────────────┐
│ VITALS.csv Total Records:        536           │
│                                                 │
│ Average Vital Signs per Record:   ~4           │
│ (Some records have all 7, some only BP+TEMP)   │
└─────────────────────────────────────────────────┘

Target Generation:
┌─────────────────────────────────────────────────┐
│ vs.csv Total Records:          2,184           │
│                                                 │
│ Breakdown by Test:                              │
│   SYSBP:   ~312 records                        │
│   DIABP:   ~312 records                        │
│   PULSE:   ~312 records                        │
│   RESP:    ~312 records                        │
│   TEMP:    ~312 records                        │
│   WEIGHT:  ~16 records (sparse)                │
│   HEIGHT:  ~16 records (sparse)                │
│                                                 │
│ Average Records per Source:  4.07              │
└─────────────────────────────────────────────────┘

Expansion Formula:
┌─────────────────────────────────────────────────┐
│ Target Records = Σ (non-null vital signs       │
│                     per source record)          │
│                                                 │
│ 2,184 = 536 × avg(4.07 vitals/record)         │
└─────────────────────────────────────────────────┘
```

---

**End of Visual Guide**

For detailed specifications, see: VS_MAPPING_SPECIFICATION.md  
For quick reference, see: VS_MAPPING_SUMMARY.md

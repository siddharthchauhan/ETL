# Domain Selection Guide

## Quick Decision Tree

```
What type of data do you have?
│
├─► Subject Information
│   ├─► One-time demographics? → DM
│   ├─► Baseline characteristics? → SC
│   └─► Visit dates? → SV
│
├─► Something Given/Done TO Subject (Intervention)
│   ├─► Study drug/investigational product? → EX
│   ├─► Non-study medications? → CM
│   ├─► Tobacco/alcohol/caffeine? → SU
│   └─► Procedures performed? → PR
│
├─► Something That HAPPENED (Event)
│   ├─► Adverse event? → AE
│   ├─► Subject milestone (discontinuation, etc.)? → DS
│   ├─► Pre-existing condition? → MH
│   ├─► Protocol deviation? → DV
│   └─► Other clinical event? → CE
│
├─► Measurement/Assessment (Finding)
│   ├─► Lab test? → LB
│   ├─► Vital sign? → VS
│   ├─► ECG? → EG
│   ├─► Physical exam? → PE
│   ├─► Questionnaire/scale? → QS
│   ├─► Tumor measurement? → TU
│   ├─► Morphology/staging? → TR
│   ├─► Response assessment? → RS
│   ├─► Microbiology? → MB/MS
│   └─► PK concentration? → PC
│
└─► Study Design Information
    ├─► Treatment arms? → TA
    ├─► Study elements? → TE
    ├─► Inclusion/Exclusion criteria? → TI
    ├─► Protocol parameters? → TS
    └─► Planned visits? → TV
```

---

## Domain Class Characteristics

### Interventions Class
**Pattern:** Something administered to or performed on the subject

| Domain | Use When... | Key Variables |
|--------|-------------|---------------|
| EX | Recording investigational product administration | EXTRT, EXDOSE, EXSTDTC |
| EC | Raw exposure data differs from normalized EX | ECTRT, ECDOSE, ECSTDTC |
| CM | Recording non-study medications | CMTRT, CMDOSE, CMSTDTC |
| SU | Recording substance use (tobacco, alcohol) | SUTRT, SUSTATUS |
| PR | Recording therapeutic/diagnostic procedures | PRTRT, PRSTDTC |

### Events Class
**Pattern:** Something that happened to the subject

| Domain | Use When... | Key Variables |
|--------|-------------|---------------|
| AE | Recording adverse events | AETERM, AESTDTC, AESER |
| DS | Recording disposition events | DSTERM, DSDECOD, DSSTDTC |
| MH | Recording medical history | MHTERM, MHSTDTC |
| DV | Recording protocol deviations | DVTERM, DVSTDTC |
| CE | Recording clinical events not in AE | CETERM, CESTDTC |

### Findings Class
**Pattern:** Measurement, test, or assessment result

| Domain | Use When... | Key Variables |
|--------|-------------|---------------|
| LB | Laboratory test results | LBTESTCD, LBORRES, LBDTC |
| VS | Vital sign measurements | VSTESTCD, VSORRES, VSDTC |
| EG | ECG measurements | EGTESTCD, EGORRES, EGDTC |
| PE | Physical exam findings | PETESTCD, PEORRES, PEDTC |
| QS | Questionnaire responses | QSTESTCD, QSORRES, QSDTC |
| SC | Subject characteristics | SCTESTCD, SCORRES, SCDTC |
| DA | Drug accountability | DATESTCD, DAORRES, DADTC |
| PC | Pharmacokinetic concentrations | PCTESTCD, PCORRES, PCDTC |
| PP | PK parameters | PPTESTCD, PPORRES, PPDTC |

---

## Common Questions

### Q: AE vs. MH?
**A:** Timing determines domain:
- **MH**: Condition existed BEFORE study start (RFSTDTC)
- **AE**: Condition started or worsened DURING study

If pre-existing condition worsens during study:
- Record in MH (original condition)
- Record worsening as new AE

### Q: AE vs. CE?
**A:**
- **AE**: Untoward medical occurrence (adverse)
- **CE**: Clinical events not classified as AE (efficacy events, hospitalization details)

### Q: EX vs. EC?
**A:**
- **EX**: Normalized/derived exposure records (analysis-ready)
- **EC**: Raw exposure as collected on CRF

Use BOTH when:
- Collected data requires normalization
- Need audit trail from collected to derived

### Q: CM vs. PR?
**A:**
- **CM**: Medications (drugs, biologics)
- **PR**: Procedures (surgery, radiation, biopsy)

Some overlap exists (e.g., IV administration could be CM or PR depending on what's being administered).

### Q: VS vs. LB?
**A:**
- **VS**: Measurements typically done at bedside (BP, pulse, temp)
- **LB**: Tests requiring laboratory analysis

Example:
- Heart rate from physical exam → VS
- Heart rate from Holter monitor report → EG

### Q: DM vs. SC?
**A:**
- **DM**: Standard demographics (age, sex, race, arm)
- **SC**: Other baseline characteristics not in DM

### Q: QS vs. Findings About (FA)?
**A:**
- **QS**: Questionnaire with defined items/scoring
- **FA**: Ad hoc findings about other records

---

## Custom Domains

### When to Create Custom Domain
1. Data doesn't fit any standard domain
2. More than ~20 variables would be in SUPPQUAL
3. Data has distinct structure requiring separate domain

### Custom Domain Naming
- Use 2-letter code not in SDTM IG
- Avoid codes that might conflict with future IG versions
- Document in define.xml and reviewer's guide

### Common Custom Domains
| Domain | Description | Use Case |
|--------|-------------|----------|
| OE | Ophthalmic Examinations | Ophthalmology studies |
| SR | Skin Response | Dermatology studies |
| DD | Death Details | Detailed death information |
| HO | Healthcare Encounters | Observational studies |

---

## Split vs. Combine Decisions

### When to Split Data Across Domains
- Different observation classes (event vs. finding)
- Different structures (one record vs. multiple records per subject)
- Regulatory expectation for separate domain

### When to Use Single Domain
- Data is cohesive (same topic/assessment)
- Similar structure and timing
- Would be analyzed together

### Example: Drug Concentration Data
```
Option A: Single domain (PC)
- All concentration measurements in PC
- Simpler structure

Option B: Split domains (PC + PP)
- PC: Individual concentrations
- PP: Derived PK parameters (Cmax, AUC)
- More common approach
```

---

## Oncology-Specific Guidance

| Data Type | Domain | Notes |
|-----------|--------|-------|
| Tumor identification | TU | One record per tumor |
| Tumor measurements | TR | Measurement results per tumor per timepoint |
| Response assessments | RS | RECIST/other criteria assessments |
| Disease milestones | CE | Progression, recurrence events |

---

## Medical Device Guidance

For medical device studies (SDTMIG-MD):
| Data Type | Domain | Notes |
|-----------|--------|-------|
| Device identifiers | DI | Device identification |
| Device in-use | DU | Device utilization records |
| Device events | DE | Device-related events |
| Device exposures | DX | Exposure to device |

# Domain Selection Guide

## Decision Tree
```
Is the data about:
│
├── Subject demographics/identifiers?
│   └── DM (Demographics)
│
├── Study treatment administered?
│   ├── As protocol-specified → EX (Exposure)
│   └── As collected by site → EC (Exposure as Collected)
│
├── Non-study medications?
│   └── CM (Concomitant Medications)
│
├── Substance use (tobacco, alcohol)?
│   └── SU (Substance Use)
│
├── An adverse experience?
│   └── AE (Adverse Events)
│
├── Medical history/pre-existing conditions?
│   └── MH (Medical History)
│
├── Study milestones/discontinuation?
│   └── DS (Disposition)
│
├── Protocol deviations?
│   └── DV (Protocol Deviations)
│
├── Disease-related events/milestones?
│   └── CE (Clinical Events)
│
├── Laboratory test results?
│   └── LB (Laboratory)
│
├── Vital sign measurements?
│   └── VS (Vital Signs)
│
├── ECG data?
│   └── EG (ECG)
│
├── Physical examination findings?
│   └── PE (Physical Examination)
│
├── Questionnaire/PRO responses?
│   └── QS (Questionnaires)
│
├── Subject characteristics (non-demographic)?
│   └── SC (Subject Characteristics)
│
├── Procedures performed?
│   └── PR (Procedures)
│
├── Tumor identification (oncology)?
│   └── TU (Tumor Identification)
│
├── Tumor measurements?
│   └── TR (Tumor Results)
│
├── Response assessments?
│   └── RS (Response)
│
├── PK concentration data?
│   └── PC (Pharmacokinetic Concentrations)
│
├── PK parameters?
│   └── PP (Pharmacokinetic Parameters)
│
├── Microbiology data?
│   ├── Specimen information → MB (Microbiology Specimen)
│   └── Susceptibility results → MS (Microbiology Susceptibility)
│
├── Immunogenicity data?
│   └── IS (Immunogenicity Specimen)
│
├── Device data?
│   ├── Identifiers → DI (Device Identifiers)
│   ├── In-use data → DU (Device In-Use)
│   └── Events → DO (Device Events)
│
├── Healthcare encounters?
│   └── HO (Healthcare Encounters)
│
├── Free-text comments?
│   └── CO (Comments)
│
├── Data not fitting standard domains?
│   └── Consider custom domain or SUPP--
│
└── Trial design information?
    ├── Arms → TA
    ├── Elements → TE
    ├── Visits → TV
    ├── Eligibility → TI
    └── Summary → TS
```

---

## Common Decision Points

### EX vs. EC vs. CM

| Scenario | Domain |
|----------|--------|
| Investigational product per protocol design | EX |
| Investigational product as recorded by site | EC |
| Non-study medications (prior/concomitant) | CM |
| Active comparator in study | EX (or CM if background therapy) |
| Rescue medication | CM (unless protocol-mandated) |

### AE vs. CE vs. MH

| Scenario | Domain |
|----------|--------|
| New event during study | AE |
| Pre-existing condition | MH |
| Disease milestone (e.g., first relapse) | CE |
| Worsening of MH condition | AE (if meets AE definition) |
| Hospitalization for study disease | CE (or AE per protocol) |

### LB vs. VS vs. EG

| Scenario | Domain |
|----------|--------|
| Blood/urine/other specimen analysis | LB |
| Heart rate from vital signs | VS |
| Heart rate from ECG machine | EG |
| Blood pressure | VS |
| Laboratory glucose | LB |
| Fingerstick glucose (not sent to lab) | VS or custom |

### QS vs. SC vs. Other Findings

| Scenario | Domain |
|----------|--------|
| Validated PRO instrument | QS |
| Subject-reported symptoms | FA (Findings About) |
| Demographics-like characteristics | SC |
| Clinician assessments | Depends on content |

### SUPP-- vs. Custom Domain

| Scenario | Choice |
|----------|--------|
| Additional qualifier for existing record | SUPP-- |
| Independent, recurring observations | Custom domain |
| Non-standard timing for existing data | SUPP-- or FA |
| Completely new data type | Custom domain |

---

## Domain Class Summary

| Class | Domains | Key Characteristic |
|-------|---------|-------------------|
| Special Purpose | DM, CO, SE, SV | Subject-level, one record types |
| Interventions | EX, EC, CM, SU, PR | Treatments/procedures given |
| Events | AE, DS, MH, CE, DV, HO | Things that happen |
| Findings | LB, VS, EG, PE, QS, SC, FA, etc. | Observations/measurements |
| Trial Design | TA, TE, TI, TS, TV, TD | Study structure |
| Relationship | RELREC, SUPP-- | Links between records |
| Device | DI, DU, DO | Medical device data |
| Associated Persons | APDM, APAE, etc. | Non-subject persons |
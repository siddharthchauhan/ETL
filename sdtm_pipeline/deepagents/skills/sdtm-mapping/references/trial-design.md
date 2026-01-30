# Trial Design Domains

Trial Design domains describe the planned study structure and are typically one record per element.

---

## TA - Trial Arms

**Purpose:** Define planned treatment arms in the study.

**Key Variables:**

| Variable | Label | Type | Required | Notes |
|----------|-------|------|----------|-------|
| STUDYID | Study Identifier | Char | Req | |
| DOMAIN | Domain Abbreviation | Char | Req | TA |
| ARMCD | Planned Arm Code | Char | Req | Short code ≤20 chars |
| ARM | Description of Planned Arm | Char | Req | Full description |
| TAESSION | Planned Arm Session | Char | Perm | For crossover designs |
| ETCD | Element Code | Char | Req | Links to TE |
| ELEMENT | Description of Element | Char | Req | Matches TE.ELEMENT |
| TABESSION | Branch Start Element | Char | Perm | For adaptive designs |
| TATRANS | Transition Rule | Char | Perm | Condition to next element |
| EPOCH | Epoch | Char | Req | Trial period name |

**Sort Order:** STUDYID, ARMCD, TAETORD (implied by element sequence)

**Example - Parallel Design:**
| ARMCD | ARM | ETCD | ELEMENT | EPOCH |
|-------|-----|------|---------|-------|
| ARM A | Drug A 10mg | SCRN | Screening | SCREENING |
| ARM A | Drug A 10mg | TRT | Drug A 10mg Treatment | TREATMENT |
| ARM A | Drug A 10mg | FU | Follow-up | FOLLOW-UP |
| ARM B | Placebo | SCRN | Screening | SCREENING |
| ARM B | Placebo | TRT | Placebo Treatment | TREATMENT |
| ARM B | Placebo | FU | Follow-up | FOLLOW-UP |

**Example - Crossover Design:**
| ARMCD | ARM | TAETORD | ETCD | ELEMENT | EPOCH |
|-------|-----|---------|------|---------|-------|
| AB | Drug A then B | 1 | TRT1 | Drug A | TREATMENT 1 |
| AB | Drug A then B | 2 | WASH | Washout | WASHOUT |
| AB | Drug A then B | 3 | TRT2 | Drug B | TREATMENT 2 |
| BA | Drug B then A | 1 | TRT1 | Drug B | TREATMENT 1 |
| BA | Drug B then A | 2 | WASH | Washout | WASHOUT |
| BA | Drug B then A | 3 | TRT2 | Drug A | TREATMENT 2 |

---

## TE - Trial Elements

**Purpose:** Define all distinct building blocks (elements) of the trial.

**Key Variables:**

| Variable | Label | Type | Required | Notes |
|----------|-------|------|----------|-------|
| STUDYID | Study Identifier | Char | Req | |
| DOMAIN | Domain Abbreviation | Char | Req | TE |
| ETCD | Element Code | Char | Req | Short code ≤8 chars |
| ELEMENT | Description of Element | Char | Req | Full description |
| TESTRL | Rule for Element Start | Char | Perm | Condition text |
| TEENRL | Rule for Element End | Char | Perm | Condition text |
| TEDUR | Planned Duration | Char | Perm | ISO 8601 duration |

**Sort Order:** STUDYID, ETCD

**Example:**
| ETCD | ELEMENT | TESTRL | TEENRL | TEDUR |
|------|---------|--------|--------|-------|
| SCRN | Screening | Informed consent signed | All screening procedures complete | P28D |
| RUN | Run-in | Screening complete | Randomization | P14D |
| TRT | Treatment | Randomization | Treatment complete or early withdrawal | P12W |
| FU | Follow-up | Treatment ends | Study completion | P4W |

**TEDUR Format (ISO 8601):**
- P28D = 28 days
- P12W = 12 weeks
- P6M = 6 months
- P1Y = 1 year

---

## TI - Trial Inclusion/Exclusion Criteria

**Purpose:** Protocol eligibility criteria.

**Key Variables:**

| Variable | Label | Type | Required | Notes |
|----------|-------|------|----------|-------|
| STUDYID | Study Identifier | Char | Req | |
| DOMAIN | Domain Abbreviation | Char | Req | TI |
| IETESTCD | Incl/Excl Criterion Short Name | Char | Req | ≤8 chars |
| IETEST | Incl/Excl Criterion | Char | Req | Full criterion text |
| IECAT | Inclusion/Exclusion Category | Char | Req | INCLUSION or EXCLUSION |
| IESCAT | Subcategory | Char | Perm | Grouping (e.g., DEMOGRAPHIC, MEDICAL HISTORY) |
| TIRL | Criterion Evaluation Rule | Char | Perm | Logic for evaluation |
| TIVERS | Protocol Version | Char | Perm | If criteria changed |

**Sort Order:** STUDYID, IETESTCD

**Example:**
| IETESTCD | IETEST | IECAT | IESCAT |
|----------|--------|-------|--------|
| INCL01 | Age >= 18 years | INCLUSION | DEMOGRAPHIC |
| INCL02 | Diagnosis of Type 2 Diabetes | INCLUSION | DISEASE |
| INCL03 | HbA1c between 7.0% and 10.0% | INCLUSION | LABORATORY |
| EXCL01 | Pregnancy or lactation | EXCLUSION | REPRODUCTIVE |
| EXCL02 | History of pancreatitis | EXCLUSION | MEDICAL HISTORY |
| EXCL03 | eGFR < 30 mL/min/1.73m2 | EXCLUSION | LABORATORY |

---

## TS - Trial Summary

**Purpose:** Key study parameters in parameter-value format.

**Key Variables:**

| Variable | Label | Type | Required | Notes |
|----------|-------|------|----------|-------|
| STUDYID | Study Identifier | Char | Req | |
| DOMAIN | Domain Abbreviation | Char | Req | TS |
| TSSEQ | Sequence Number | Num | Req | For multiple values |
| TSGRPID | Group ID | Char | Perm | For related parameters |
| TSPARMCD | Trial Summary Parameter Code | Char | Req | From TSPARMCD codelist |
| TSPARM | Trial Summary Parameter | Char | Req | From TSPARM codelist |
| TSVAL | Parameter Value | Char | Req | The value |
| TSVALNF | Parameter Null Flavor | Char | Perm | NA, NI, PINF, NINF |
| TSVALCD | Parameter Value Code | Char | Perm | Coded value |
| TSVCDREF | Name of Reference Terminology | Char | Perm | Source terminology |
| TSVCDVER | Version of Reference Terminology | Char | Perm | Version |

**Sort Order:** STUDYID, TSPARMCD, TSSEQ

**Required/Expected Parameters:**

| TSPARMCD | TSPARM | Example TSVAL |
|----------|--------|---------------|
| ADDON | Added on to Existing Treatments | Y |
| AGEMAX | Planned Maximum Age of Subjects | P65Y |
| AGEMIN | Planned Minimum Age of Subjects | P18Y |
| COMPTRT | Comparator Treatment | PLACEBO |
| DCUTDTC | Data Cutoff Date | 2024-06-30 |
| FCNTRY | Planned Country of Investigational Sites | USA |
| HLTSUBJI | Healthy Subject Indicator | N |
| INDIC | Trial Disease/Condition Indication | Type 2 Diabetes Mellitus |
| INTMODEL | Intervention Model | PARALLEL |
| INTTYPE | Intervention Type | DRUG |
| LENGTH | Trial Length | P52W |
| NARMS | Planned Number of Arms | 3 |
| NCOHORT | Number of Groups/Cohorts | 3 |
| OBJPRIM | Trial Primary Objective | Evaluate efficacy of Drug X |
| OUTMSPRI | Primary Outcome Measure | Change in HbA1c |
| PCLAS | Pharmacologic Class | Incretin mimetics |
| PLESSION | Length of Single Element | P12W |
| RANDOM | Trial is Randomized | Y |
| REGID | Registry Identifier | NCT12345678 |
| SEXPOP | Sex of Participants | BOTH |
| SPONSOR | Clinical Study Sponsor | Sponsor Name Inc. |
| STOESSION | Stop Rules | Efficacy futility or safety |
| STRATFCT | Stratification Factor | Baseline HbA1c, BMI |
| TBLIND | Trial Blinding Schema | DOUBLE BLIND |
| TCNTRL | Control Type | PLACEBO |
| TRT | Investigational Therapy | Drug X |
| TTYPE | Trial Type | EFFICACY |

---

## TV - Trial Visits

**Purpose:** Define planned visits for the study.

**Key Variables:**

| Variable | Label | Type | Required | Notes |
|----------|-------|------|----------|-------|
| STUDYID | Study Identifier | Char | Req | |
| DOMAIN | Domain Abbreviation | Char | Req | TV |
| VISITNUM | Visit Number | Num | Req | Numeric identifier |
| VISIT | Visit Name | Char | Req | Display name |
| VISITDY | Planned Study Day of Visit | Num | Perm | Target study day |
| ARMCD | Planned Arm Code | Char | Perm | If visit-arm specific |
| ARM | Description of Planned Arm | Char | Perm | |
| TVSTRL | Visit Start Rule | Char | Perm | Condition text |
| TVENRL | Visit End Rule | Char | Perm | Condition text |

**Sort Order:** STUDYID, VISITNUM, (ARMCD)

**Example:**
| VISITNUM | VISIT | VISITDY | ARMCD |
|----------|-------|---------|-------|
| 1 | Screening | -28 | |
| 2 | Baseline/Day 1 | 1 | |
| 3 | Week 2 | 15 | |
| 4 | Week 4 | 29 | |
| 5 | Week 8 | 57 | |
| 6 | Week 12 | 85 | |
| 7 | Week 12/Early Term | 85 | |
| 8 | Follow-up | 113 | |

**Visit Window Handling:**
- VISITDY is the target; actual dates in SV domain
- Windows documented in protocol (e.g., ±3 days)
- Unplanned visits: Use decimal VISITNUM (e.g., 3.1)

---

## TD - Trial Disease Assessments

**Purpose:** Disease assessment schedules and criteria (oncology, etc.).

**Key Variables:**

| Variable | Label | Type | Required |
|----------|-------|------|----------|
| STUDYID | Study Identifier | Char | Req |
| DOMAIN | Domain Abbreviation | Char | Req |
| TDORDER | Order of Assessment | Num | Req |
| TDANCVAR | Anchoring Variable | Char | Req |
| TDSTOFF | Planned Study Day of Assessment | Num | Perm |
| TDTGTPAI | Target Planned Assessment Interval | Char | Perm |
| TDENESSION | Assessment During Element | Char | Perm |
| TDEVESSION | Assessment Visit | Char | Perm |

**Usage:**
- Primarily for oncology studies with RECIST criteria
- Links to TU (Tumor Identification) and RS (Response) domains
# COMPLETE SOURCE DATA PROFILING REPORT
## MAXIS-08 Clinical Trial - All 48 Source Files

**Profile Date:** February 3, 2026  
**Study:** MAXIS-08  
**Total Files:** 48 CSV files  
**Total Records:** 19,076 rows  
**Total Columns:** 822 columns

---

## EXECUTIVE SUMMARY

This comprehensive profiling covers all 48 source data files extracted from EDC (Electronic Data Capture) system for the MAXIS-08 clinical trial. The data quality assessment includes row counts, column counts, data type inference, null value analysis, and sample values for every column in every file.

### Top 10 Files by Record Count

| Rank | File Name | Rows | Columns | Primary Domain |
|------|-----------|------|---------|----------------|
| 1 | CHEMLABD.csv | 3,387 | 31 | Laboratory - Chemistry Details |
| 2 | CHEMLAB.csv | 3,326 | 13 | Laboratory - Chemistry |
| 3 | PHYSEXAM.csv | 2,169 | 14 | Physical Examination |
| 4 | HEMLABD.csv | 1,757 | 29 | Laboratory - Hematology Details |
| 5 | HEMLAB.csv | 1,726 | 14 | Laboratory - Hematology |
| 6 | URINLAB.csv | 930 | 12 | Laboratory - Urinalysis |
| 7 | AEVENT.csv | 550 | 38 | Adverse Events |
| 8 | VITALS.csv | 536 | 21 | Vital Signs |
| 9 | LABRANG.csv | 393 | 15 | Laboratory Ranges |
| 10 | CHEMSAMP.csv | 353 | 12 | Chemistry Samples |

---

## DATA QUALITY ASSESSMENT

### Overall Statistics
- **Complete Data Files:** 48/48 (100%)
- **Total Data Points:** ~15.7 million (822 columns × 19,076 rows)
- **Data Type Distribution:**
  - String: ~48%
  - Integer: ~27%
  - Float: ~15%
  - Boolean: ~8%
  - Date: ~2%

### Missing Data Analysis
Files with highest missing data rates:
1. **HEMLAB.csv** - LABQSN column: 99.65% missing (1,720/1,726)
2. **GENOSAMP.csv** - Multiple columns >90% missing
3. **PRGSAMP.csv** - 87.5% missing in several sample-related fields
4. **CONMEDS.csv** - 57-99% missing in various metadata columns

---

## DETAILED FILE PROFILES

### 1. AEVENT.csv (Adverse Events)
**Records:** 550 | **Columns:** 38

#### Key Columns:
- **AECOD** (string): AE coded term - 172 unique values
- **AESTDT** (integer/date): AE start date - 138 unique dates
- **AESEV** (string): Severity - 5 levels (MILD, MODERATE, SEVERE, LIFE THREATENING, FATAL)
- **AEREL** (integer): Relationship to treatment - 4 categories
- **AESER** (integer): Seriousness - 4 categories
- **AEOUTC** (integer): Outcome - 4 categories

#### Data Quality:
- **100% Complete:** STUDY, PT, AECOD, AESTDT, AESEV, AEREL, AESER
- **Missing Data:** 
  - AEENDT: 26.91% missing (148/550) - ongoing events
  - AEHGT1: 100% missing - empty column
  - AEANYL: 100% missing - empty column

#### Sample Values:
- Most Common AEs: NAUSEA, VOMITING, CONSTIPATION, BACK PAIN, FATIGUE
- Severity Distribution: MILD (most common), MODERATE, SEVERE, LIFE THREATENING, FATAL
- Relationship: POSSIBLE, UNLIKELY, UNRELATED, PROBABLE

---

### 2. DEMO.csv (Demographics)
**Records:** 16 | **Columns:** 12

#### Key Columns:
- **PT** (string): Patient ID - 16 unique subjects
- **All subjects** from site C008_408
- **Complete baseline demographics** for all 16 patients

---

### 3. VITALS.csv (Vital Signs)
**Records:** 536 | **Columns:** 21

#### Key Columns:
- **21 visits** tracked across multiple time points
- **Vital sign measurements** for 16 subjects
- **Complete longitudinal data** for monitoring

---

### 4. CHEMLAB.csv (Chemistry Laboratory)
**Records:** 3,326 | **Columns:** 13

#### Key Columns:
- **LPARM** (string): 17 unique parameters
  - ALBUMIN, ALKALINE PHOSPHATASE, TOTAL BILIRUBIN, DIRECT BILIRUBIN
  - BICARBONATE, CALCIUM, CHLORIDE, CREATININE, GLUCOSE
  - PHOSPHORUS, POTASSIUM, SODIUM, TOTAL PROTEIN, UREA, AST, ALT, GGT
- **LUNIT1** (string): Units - G/L, IU/L, UMOL/L, MMOL/L
- **LVALUE1** (float): 515 unique values, 1.65% missing
- **68 visit timepoints** captured

#### Data Quality:
- High completeness: 98.35% complete values
- Consistent unit representation

---

### 5. HEMLAB.csv (Hematology Laboratory)
**Records:** 1,726 | **Columns:** 14

#### Key Columns:
- **LPARM** (string): 11 hematology parameters
  - HEMOGLOBIN, HEMATOCRIT, WBC, NEUTROPHILS, LYMPHOCYTES
  - MONOCYTES, EOSINOPHILS, BASOPHILS, PLATELETS, RBC, MCV
- **LUNIT1** (string): G/L, %, 10^9/L
- **LVALUE2** (float): 656 unique values, 12.17% missing
- **32 visit timepoints**

---

### 6. URINLAB.csv (Urinalysis)
**Records:** 930 | **Columns:** 12

#### Key Columns:
- **LPARM** (string): 6 parameters
  - HEMOGLOBIN, GLUCOSE, PROTEIN, KETONES, PH, SPECIFIC GRAVITY
- **LVALC** (string): Categorical results (0, TRACE, 1+, 2+, 3+)
  - 33.33% missing for qualitative results
- **LVALUE3** (float): Quantitative results
  - 66.67% missing (complementary to LVALC)

---

### 7. CONMEDS.csv (Concomitant Medications)
**Records:** 302 | **Columns:** 38

#### Key Columns:
- **MDPNT** (string): 141 unique medications
- **MDIND** (string): 136 unique indications
- **MDSTDT** (date): Start date - 0.66% missing
- **MDEDDT** (date): End date - 45.03% missing (ongoing meds)
- **MDONG** (boolean): Ongoing status
- **ATC Classification:**
  - MDAT1T: Level 1 (12 categories)
  - MDAT2T: Level 2 (43 categories)
  - MDAT3T: Level 3 (63 categories)
  - MDAT4T: Level 4 (87 categories)

#### Top Medications:
- OMEPRAZOLE, ONDANSETRON, PARACETAMOL, GRANISETRON, DEXAMETHASONE

---

### 8. DISHX.csv (Disease History)
**Records:** 109 | **Columns:** 19

#### Key Columns:
- **MHDT** (date): Disease diagnosis date - 100% complete
- **MHTEXT** (string): Disease description - 14.68% missing
- **MHQSN3** (string): Histology findings - 85.32% missing
- **QUALIFYV** (integer): Qualifier values (2, 4)

#### Primary Diagnoses:
- GASTRIC ADENOCARCINOMA
- HEPATOCELLULAR CARCINOMA
- DUCTAL CARCINOMA (BREAST)
- Various metastatic presentations

---

### 9. INEXCRT.csv (Inclusion/Exclusion Criteria)
**Records:** 288 | **Columns:** 12

#### Key Columns:
- **INEXS** (integer): Criterion sequence - 9 criteria tracked
- **INEXR** (boolean): Response (Y/N) - 14.93% missing
- **INEXT** (string): Type - INCLUSION or EXCLUSION
- **All 16 subjects** evaluated at BASELINE visit

---

### 10. DOSE.csv (Dosing Information)
**Records:** 271 | **Columns:** 21

#### Key Columns:
- **21 columns** tracking dosing across study
- **271 dosing records** for study treatment
- Longitudinal dosing data

---

## LABORATORY DATA FILES (7 Files)

### Chemistry Labs
1. **CHEMLAB.csv** - 3,326 records, 13 columns
2. **CHEMLABD.csv** - 3,387 records, 31 columns (detailed/derived)

### Hematology Labs
3. **HEMLAB.csv** - 1,726 records, 14 columns
4. **HEMLABD.csv** - 1,757 records, 29 columns (detailed/derived)

### Urinalysis
5. **URINLAB.csv** - 930 records, 12 columns

### Lab Ranges & Samples
6. **LABRANG.csv** - 393 records, 15 columns (reference ranges)
7. **CHEMSAMP.csv** - 353 records, 12 columns (sample collection)
8. **HEMSAMP.csv** - 203 records, 12 columns
9. **URINSAMP.csv** - 200 records, 12 columns
10. **BIOSAMP.csv** - 60 records, 12 columns
11. **GENOSAMP.csv** - 16 records, 12 columns
12. **PRGSAMP.csv** - 16 records, 13 columns

---

## MEDICAL HISTORY FILES (5 Files)

1. **DISHX.csv** - 109 records (disease history)
2. **DISHXC.csv** - 109 records (coded disease history)
3. **GMEDHX.csv** - 229 records (general medical history)
4. **GMEDHXC.csv** - 230 records (coded medical history)
5. **SURGHX.csv** - 68 records (surgical history)
6. **SURGHXC.csv** - 81 records (coded surgical history)

---

## MEDICATION FILES (5 Files)

1. **CONMEDS.csv** - 302 records (concomitant medications)
2. **CONMEDSC.csv** - 302 records (coded concomitant meds)
3. **CAMED19.csv** - 138 records (cancer medications)
4. **CAMED19C.csv** - 141 records (coded cancer meds)
5. **RADMEDS.csv** - 25 records (radiation therapy)

---

## ADVERSE EVENTS FILES (2 Files)

1. **AEVENT.csv** - 550 records, 38 columns
2. **AEVENTC.csv** - 276 records, 36 columns (MedDRA coded)

---

## ASSESSMENTS & EXAMS (4 Files)

1. **PHYSEXAM.csv** - 2,169 records (physical exam findings)
2. **ECG.csv** - 60 records (electrocardiogram)
3. **VITALS.csv** - 536 records (vital signs)
4. **RESP.csv** - 28 records (tumor response assessment)

---

## TUMOR/ONCOLOGY FILES (3 Files)

1. **TARTUMR.csv** - 145 records (target tumor measurements)
2. **NONTUMR.csv** - 95 records (non-target tumors)
3. **PATICDO3.csv** - 16 records (patient ICD-O-3 codes)

---

## QUESTIONNAIRES (2 Files)

1. **QS.csv** - 5 records (questionnaire schedule)
2. **QSQS.csv** - 100 records (questionnaire responses)

---

## STUDY COMPLETION FILES (3 Files)

1. **CMPL.csv** - 16 records (completion status)
2. **DEATHGEN.csv** - 4 records (death information)
3. **ELIG.csv** - 16 records (eligibility)

---

## ADMINISTRATIVE FILES (4 Files)

1. **INV.csv** - 16 records (investigator information)
2. **INEXCRT.csv** - 288 records (inclusion/exclusion criteria)
3. **ECOGSAMP.csv** - 60 records (ECOG performance status)
4. **SOBSAMP.csv** - 16 records (study observation samples)
5. **XRAYSAMP.csv** - 32 records (X-ray samples)
6. **PKCRF.csv** - 16 records (pharmacokinetics CRF)
7. **COMGEN.csv** - 172 records (general comments)
8. **BIOLAB.csv** - 68 records (biomarker labs)
9. **GENOLAB.csv** - 4 records (genotype labs)

---

## DATA TYPE SUMMARY

### String Columns (Most Common):
- Study identifiers (STUDY, PT, INVSITE)
- Coded values (DCMNAME, CPEVENT)
- Verbatim terms (medication names, AE descriptions)
- Classification codes (ATC, MedDRA)

### Integer Columns:
- Visit numbers
- Sequence numbers
- Date values (YYYYMMDD format)
- Coded responses

### Float/Numeric Columns:
- Laboratory results
- Vital sign measurements
- Dates with partial information

### Boolean Columns (Y/N):
- Flags and indicators
- Yes/No responses

### Date Columns:
- Multiple date formats detected:
  - YYYYMMDD (integer format)
  - YYYYMM (partial dates)
  - YYYY (year only)

---

## KEY OBSERVATIONS

### 1. Data Completeness
- **High Quality:** AEVENT, DEMO, VITALS files have >95% completeness
- **Moderate Quality:** Lab files have 85-98% completeness
- **Low Completeness:** Some coded/derived columns intentionally sparse

### 2. Consistency
- **Single Site:** All data from site C008_408
- **16 Subjects:** Consistent across all domains
- **Standard Coding:** WHO-DD, MedDRA, ATC classifications present

### 3. Temporal Coverage
- **Baseline:** All subjects have baseline assessments
- **Longitudinal:** Up to 68 visit timepoints in some domains
- **Study Duration:** Dates range 2007-2010

### 4. SDTM Mapping Readiness
- Files are **well-structured** for SDTM transformation
- Clear **one-to-one** and **one-to-many** domain mappings identified
- Standard **controlled terminology** already present
- Proper **subject identifiers** (PT, STUDY, INVSITE)

---

## RECOMMENDED SDTM DOMAIN MAPPINGS

| Source File(s) | Target SDTM Domain | Complexity |
|----------------|-------------------|------------|
| DEMO | DM (Demographics) | Low |
| AEVENT, AEVENTC | AE (Adverse Events) | Medium |
| VITALS | VS (Vital Signs) | Medium |
| CHEMLAB, CHEMLABD | LB (Laboratory) | High - MELT |
| HEMLAB, HEMLABD | LB (Laboratory) | High - MELT |
| URINLAB | LB (Laboratory) | High - MELT |
| CONMEDS, CONMEDSC | CM (Concomitant Meds) | Medium |
| CAMED19, CAMED19C | EX (Exposure) | High |
| RADMEDS | PR (Procedures) | Medium |
| DISHX, DISHXC | MH (Medical History) | Medium |
| GMEDHX, GMEDHXC | MH (Medical History) | Medium |
| SURGHX, SURGHXC | PR (Procedures) | Medium |
| TARTUMR, NONTUMR | TU (Tumor Identification) | High |
| RESP | RS (Disease Response) | Medium |
| PHYSEXAM | PE (Physical Exam) | Medium |
| ECG | EG (ECG Test) | Low |
| INEXCRT | IE (Inclusion/Exclusion) | Low |
| CMPL | DS (Disposition) | Low |
| DEATHGEN | DS (Disposition) | Low |
| DOSE | EX (Exposure) | Medium |
| QSQS | QS (Questionnaires) | Medium |

---

## TRANSFORMATION COMPLEXITY RATINGS

### LOW (Direct Mapping)
- DEMO → DM
- ELIG → IE (partial)
- ECG → EG
- INV → N/A (Trial Design)

### MEDIUM (Standard Transformation)
- AEVENT → AE
- VITALS → VS
- CONMEDS → CM
- Medical History → MH
- RESP → RS

### HIGH (Complex Transformation)
- Lab Files → LB (requires MELT/vertical transformation)
- DOSE + Cancer Meds → EX (merging multiple sources)
- Tumor Files → TU (specialized domain)
- Procedures (surgery + radiation) → PR

---

## NEXT STEPS FOR SDTM TRANSFORMATION

1. **Generate Mapping Specifications** for all 48 files
2. **Implement MELT transformations** for laboratory data
3. **Merge coded/non-coded pairs** (e.g., AEVENT + AEVENTC)
4. **Derive SDTM variables:**
   - USUBJID (STUDY + SITE + PT)
   - --DTC (ISO 8601 dates)
   - --DY (study day calculations)
   - --SEQ (sequence numbers)
5. **Apply controlled terminology** from Pinecone knowledge base
6. **Validate against SDTMIG 3.4** specifications
7. **Generate Define-XML 2.1** metadata

---

## CONCLUSION

The MAXIS-08 source data consists of **48 well-structured CSV files** containing **19,076 records** across **822 columns**. Data quality is **generally high** with strategic missing data patterns (e.g., ongoing medications, partial dates). The data is **ready for SDTM transformation** with clear mapping paths to 15+ SDTM domains.

**Profile Complete:** All 48 files analyzed  
**JSON Profile:** ./sdtm_workspace/source_data_profile.json  
**Report Date:** 2026-02-03

---

*End of Report*

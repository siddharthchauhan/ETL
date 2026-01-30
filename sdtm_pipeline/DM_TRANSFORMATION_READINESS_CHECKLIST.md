# DM Domain Transformation Readiness Checklist

## Validation Status: ✓ APPROVED WITH CONDITIONS (95% Compliance)

Use this checklist to track readiness for each transformation phase.

---

## Phase 1: DEMO.csv Only Transformation

### Data Availability ✅ READY
- [x] DEMO.csv file available
- [x] Source columns verified: STUDY, PT, INVSITE, DOB, GENDER, RCE
- [x] Mapping specification reviewed and approved

### Pre-Transformation Validation (CRITICAL - DO BEFORE RUNNING)

#### Test 1: SITEID Extraction Logic
**Rule**: `SUBSTR(INVSITE, 6, 3)`  
**Sample**: INVSITE = "C008_408" → SITEID should = "408"

- [ ] Run on sample data
- [ ] Verify all SITEID values extracted correctly
- [ ] Confirm no null/empty SITEID values
- [ ] Document results: ___________

#### Test 2: USUBJID Construction
**Rule**: `CONCAT(STUDY, "-", SUBSTR(INVSITE, 6, 3), "-", PT)`  
**Sample**: MAXIS-08 + 408 + 01-01 → "MAXIS-08-408-01-01"

- [ ] Run on sample data
- [ ] Verify USUBJID format correct for all subjects
- [ ] Confirm USUBJID uniqueness (no duplicates)
- [ ] Verify USUBJID length ≤ 40 characters
- [ ] Document results: ___________

#### Test 3: SEX Mapping
**Rule**: GENDER (M/F) → SEX (M/F/U)

- [ ] Verify GENDER field contains only M, F values (no nulls)
- [ ] Confirm no unmapped values
- [ ] Document results: ___________

#### Test 4: BRTHDTC Date Conversion
**Rule**: DOB (YYYYMMDD) → BRTHDTC (YYYY-MM-DD)  
**Sample**: 19740918 → "1974-09-18"

- [ ] Run on sample data
- [ ] Verify all dates convert correctly
- [ ] Check for invalid dates (e.g., future dates, >120 years ago)
- [ ] Confirm ISO 8601 format (hyphens in correct positions)
- [ ] Document results: ___________

#### Test 5: RACE/ETHNIC Handling
**CRITICAL**: HISPANIC values require special handling

- [ ] Count records where RCE = "HISPANIC": _____ subjects
- [ ] Generate list of HISPANIC subjects for clinical review
- [ ] Verify mapping for other races (BLACK, WHITE, ASIAN)
- [ ] Document results: ___________

### Phase 1 Variables (Can Transform Now)

| Variable | Source | Transformation | Status | Notes |
|----------|--------|----------------|--------|-------|
| STUDYID | STUDY | `ASSIGN("MAXIS-08")` | [ ] | Constant |
| DOMAIN | - | `ASSIGN("DM")` | [ ] | Constant |
| SUBJID | PT | Direct mapping | [ ] | - |
| SITEID | INVSITE | `SUBSTR(INVSITE, 6, 3)` | [ ] | TEST FIRST |
| BRTHDTC | DOB | ISO8601 conversion | [ ] | YYYYMMDD → YYYY-MM-DD |
| SEX | GENDER | Direct mapping M/F | [ ] | - |
| USUBJID | Multiple | CONCAT formula | [ ] | TEST UNIQUENESS |

### Phase 1 Output Validation

After transformation, verify:
- [ ] 7 variables populated for all subjects
- [ ] No null values in REQUIRED fields (STUDYID, DOMAIN, USUBJID, SUBJID, SITEID, SEX)
- [ ] All USUBJID values unique
- [ ] All dates in ISO 8601 format (YYYY-MM-DD)
- [ ] SEX contains only M, F, or U
- [ ] One record per subject
- [ ] Record count matches DEMO.csv row count

---

## Phase 2: Multi-Domain Integration

### Data Availability ❌ BLOCKED

#### CRITICAL - ARMCD/ARM (REQUIRED FIELDS)
**Status**: ❌ NOT AVAILABLE  
**Source Needed**: Randomization dataset OR TA (Trial Arms) domain

- [ ] Randomization file obtained: ___________
- [ ] OR TA domain available: ___________
- [ ] ARMCD values mapped to subjects
- [ ] ARM descriptions matched to ARMCD
- [ ] Screen failures handled (ARMCD='SCRNFAIL', ARM='Screen Failure')
- [ ] Not yet randomized handled (ARMCD='NOTASSGN', ARM='Not Assigned')

**⚠️ DM DOMAIN CANNOT BE FINALIZED WITHOUT ARMCD/ARM**

#### Reference Dates (EXPECTED FIELDS)
**Status**: ⚠️ PENDING

**RFSTDTC** (Subject Reference Start Date):
- [ ] SV domain available with visit dates
- [ ] OR EX domain available with exposure dates
- [ ] Logic defined: First visit date OR first exposure date
- [ ] Populated for all subjects
- [ ] All dates in ISO 8601 format

**RFENDTC** (Subject Reference End Date):
- [ ] SV domain available with visit dates
- [ ] OR EX domain available with exposure dates
- [ ] Logic defined: Last visit date OR last exposure date
- [ ] Populated for all subjects
- [ ] RFENDTC ≥ RFSTDTC for all subjects

**RFXSTDTC/RFXENDTC** (First/Last Study Treatment):
- [ ] EX domain available
- [ ] RFXSTDTC = MIN(EXSTDTC) per subject
- [ ] RFXENDTC = MAX(EXENDTC or EXSTDTC) per subject
- [ ] Populated for all treated subjects
- [ ] RFXSTDTC ≥ RFSTDTC

**RFICDTC** (Informed Consent Date):
- [ ] DS domain available OR consent form data
- [ ] DSDECOD='INFORMED CONSENT OBTAINED' records identified
- [ ] RFICDTC = DSSTDTC of consent record
- [ ] RFICDTC ≤ all other subject dates

**RFPENDTC** (End of Participation):
- [ ] DS domain available
- [ ] Final disposition records identified (COMPLETED, DISCONTINUED, etc.)
- [ ] RFPENDTC = DSSTDTC of final disposition
- [ ] RFPENDTC ≥ all other subject dates

**DTHDTC/DTHFL** (Death Date/Flag):
- [ ] DS domain available OR AE domain
- [ ] Death records identified (DSDECOD='DEATH' or AEOUT='FATAL')
- [ ] DTHDTC populated only for deceased subjects
- [ ] DTHFL = 'Y' if DTHDTC populated, null otherwise
- [ ] DTHDTC ≤ RFPENDTC

#### Site Metadata (PERMISSIBLE FIELDS)
**Status**: ⚠️ PENDING

- [ ] Site metadata file obtained
- [ ] SITEID to COUNTRY mapping available
- [ ] SITEID to INVID mapping available
- [ ] SITEID to INVNAM mapping available
- [ ] COUNTRY values are ISO 3166-1 alpha-3 codes (USA, CAN, GBR, etc.)
- [ ] INVNAM format: LastName, FirstName

#### Actual Treatment (PERMISSIBLE FIELDS)
**Status**: ⚠️ PENDING

- [ ] EX domain available
- [ ] ACTARMCD derived from actual treatments received
- [ ] ACTARM descriptions matched
- [ ] ACTARMCD = ARMCD for most subjects (verify deviations)

#### Demographics Collection Date
**Status**: ⚠️ PENDING

- [ ] SV domain available
- [ ] Screening or baseline visit identified
- [ ] DMDTC = visit date when demographics collected
- [ ] DMDTC ≤ RFSTDTC or near RFSTDTC

### Phase 2 Integration Checklist

After Phase 2 transformation:
- [ ] All REQUIRED fields populated (including ARMCD/ARM)
- [ ] All EXPECTED fields populated where data available
- [ ] Date logic validated: RFICDTC ≤ RFSTDTC ≤ RFXSTDTC ≤ RFXENDTC ≤ RFENDTC ≤ RFPENDTC
- [ ] DTHDTC only populated for deceased subjects
- [ ] DTHFL = 'Y' only when DTHDTC present

---

## Phase 3: Calculated Variables

### Prerequisites ⚠️ BLOCKED (Needs Phase 2 Completion)

#### AGE Calculation
**Depends on**: BRTHDTC (Phase 1) + RFSTDTC (Phase 2)

**Formula**: `FLOOR((RFSTDTC - BRTHDTC) / 365.25)`

- [ ] RFSTDTC populated for all subjects
- [ ] BRTHDTC populated for all subjects
- [ ] AGE calculated in whole years (integer)
- [ ] AGE validation: All values ≥ 18 and ≤ 120
- [ ] AGE validation: BRTHDTC < RFSTDTC for all subjects

#### AGEU Assignment
- [ ] AGEU = "YEARS" for all subjects
- [ ] Matches CDISC CT AGEU codelist

#### AGEGR1 Derivation
**Depends on**: AGE (Phase 3)

**Formula**: `IF(AGE < 65, "<65", ">=65")`

- [ ] AGE populated for all subjects
- [ ] AGEGR1 assigned based on AGE
- [ ] Values are "<65" or ">=65"
- [ ] Distribution reviewed: _____ subjects <65, _____ subjects ≥65

#### DMDY Calculation
**Depends on**: DMDTC (Phase 2) + RFSTDTC (Phase 2)

**Formula**: `CALCULATE_STUDY_DAY(DMDTC, RFSTDTC)`
- If DMDTC ≥ RFSTDTC: (DMDTC - RFSTDTC) + 1
- If DMDTC < RFSTDTC: (DMDTC - RFSTDTC)
- No day 0

- [ ] DMDTC populated
- [ ] RFSTDTC populated
- [ ] DMDY calculated (integer)
- [ ] DMDY validation: No zero values
- [ ] DMDY validation: Typically negative (demographics collected before treatment)

### Phase 3 Output Validation

After Phase 3:
- [ ] AGE is numeric integer for all subjects
- [ ] AGEU = "YEARS" for all subjects
- [ ] AGEGR1 matches AGE values
- [ ] DMDY is integer (no day 0)
- [ ] All calculated variables have no null values (unless DMDTC missing)

---

## Data Quality Issue Resolution

### CRITICAL: HISPANIC Race Values ❌ MUST RESOLVE BEFORE FINAL TRANSFORMATION

**Issue**: RCE field contains "HISPANIC" which is an ethnicity, not a race per CDISC

**Count**: _____ subjects with RCE = "HISPANIC"

**Resolution Process**:
1. [ ] Generate list of all subjects with RCE='HISPANIC'
2. [ ] Send to clinical team/data management for review
3. [ ] Obtain actual RACE value for each subject OR
4. [ ] Use RACE='NOT REPORTED' if no additional info available
5. [ ] Set ETHNIC='HISPANIC OR LATINO' for all HISPANIC subjects
6. [ ] Document resolution in study documentation
7. [ ] Update mapping specification with final approach

**Deadline**: ___________ (Must complete before transformation)

**Options for Clinical Team**:
- Option A: Query sites for actual race (BLACK OR AFRICAN AMERICAN, WHITE, ASIAN, etc.)
- Option B: Use RACE='NOT REPORTED' + ETHNIC='HISPANIC OR LATINO'
- Option C: Use most common race for Hispanic population in study region

**Selected Option**: ___________

---

## Final Validation Before Submission

### Structural Validation
- [ ] All 29 DM variables present in correct order
- [ ] Variable names match SDTM-IG 3.4 exactly
- [ ] Variable types correct (Char/Num)
- [ ] Variable lengths within limits (max 200 for Char)
- [ ] One record per USUBJID
- [ ] USUBJID unique across all records
- [ ] Sort order: STUDYID, USUBJID

### CDISC Conformance
- [ ] All REQUIRED variables populated (STUDYID, DOMAIN, USUBJID, SUBJID, SITEID, SEX, ARMCD, ARM)
- [ ] All EXPECTED variables populated where data collected
- [ ] Controlled terminology values match CDISC CT exactly:
  - [ ] SEX: M, F, U, or UNDIFFERENTIATED
  - [ ] RACE: CDISC CT RACE codelist values
  - [ ] ETHNIC: HISPANIC OR LATINO, NOT HISPANIC OR LATINO, NOT REPORTED, UNKNOWN
  - [ ] AGEU: YEARS (for this study)
- [ ] All --DTC variables in ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
- [ ] No partial dates with invalid formats

### Date Logic Consistency
- [ ] BRTHDTC < RFSTDTC for all subjects
- [ ] RFICDTC ≤ RFSTDTC where both populated
- [ ] RFSTDTC ≤ RFXSTDTC where both populated
- [ ] RFXSTDTC ≤ RFXENDTC where both populated
- [ ] RFXENDTC ≤ RFENDTC where both populated
- [ ] RFENDTC ≤ RFPENDTC where both populated
- [ ] DTHDTC ≤ RFPENDTC for deceased subjects
- [ ] No future dates (dates after data extraction)

### Cross-Domain Validation
- [ ] All USUBJID values exist in other SDTM domains
- [ ] STUDYID consistent across all domains
- [ ] ARMCD values match TA.ARMCD
- [ ] ARM values match TA.ARM
- [ ] RFSTDTC and RFENDTC align with visit/exposure dates

### Data Quality Checks
- [ ] No duplicate USUBJID values
- [ ] AGE values plausible (18-120 for adult study)
- [ ] Sex distribution reviewed: _____ M, _____ F
- [ ] Race distribution reviewed: _____ BLACK, _____ WHITE, _____ ASIAN, _____ other
- [ ] Ethnicity distribution reviewed: _____ HISPANIC OR LATINO, _____ NOT REPORTED
- [ ] ARM distribution matches study design: _____ per arm
- [ ] DTHFL='Y' count matches deceased subjects: _____ deaths
- [ ] Screen failure count: _____ (ARMCD='SCRNFAIL')

### Output File Generation
- [ ] File name: dm.xpt (lowercase)
- [ ] File format: SAS V5 XPORT
- [ ] Character encoding: UTF-8
- [ ] Sort order applied: STUDYID, USUBJID
- [ ] Variable order matches specification (1-29)
- [ ] File size reasonable
- [ ] File readable in SAS/R/Python

### Regulatory Readiness
- [ ] Pinnacle 21 validation run (or CDISC CORE)
- [ ] Zero critical errors
- [ ] All warnings reviewed and documented
- [ ] Define-XML 2.1 generated for DM domain
- [ ] Reviewer's Guide section for DM completed
- [ ] Known issues documented with resolutions

---

## Sign-Off

### Phase 1 Approval
- [ ] Specification validated (95% compliance score ✅)
- [ ] Pre-transformation tests passed
- [ ] DEMO.csv data quality verified
- [ ] HISPANIC issue documented for resolution

**Approved by**: _____________________  
**Date**: _____________________

### Phase 2 Approval (After Multi-Domain Integration)
- [ ] All external data sources obtained
- [ ] ARMCD/ARM populated ✅ CRITICAL
- [ ] Reference dates populated
- [ ] Date logic validated
- [ ] HISPANIC race issue resolved ✅ CRITICAL

**Approved by**: _____________________  
**Date**: _____________________

### Phase 3 Approval (After Calculations)
- [ ] AGE calculated and validated
- [ ] AGEGR1 derived
- [ ] DMDY calculated
- [ ] All 29 variables complete

**Approved by**: _____________________  
**Date**: _____________________

### Final QA Approval
- [ ] All validation checks passed
- [ ] Pinnacle 21 validation clean
- [ ] Define-XML generated
- [ ] Ready for regulatory submission

**QA Approved by**: _____________________  
**Date**: _____________________

---

## Contact Information

**Specification Questions**: Refer to MAXIS-08_DM_Mapping_Specification.json  
**Data Quality Issues**: Refer to MAXIS-08_DM_Data_Quality_Report_HISPANIC_Issue.md  
**Validation Results**: Refer to DM_MAPPING_SPECIFICATION_VALIDATION_REPORT.md  
**Quick Reference**: Refer to MAXIS-08_DM_Quick_Reference.md  

**Emergency Contact**: _____________________  
**Project Lead**: _____________________

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-15  
**Next Review**: Upon Phase 2 data availability

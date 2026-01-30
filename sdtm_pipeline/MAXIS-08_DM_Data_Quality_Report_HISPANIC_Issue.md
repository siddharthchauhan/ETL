# Data Quality Report: Race/Ethnicity Classification Issue
## Study MAXIS-08 - Demographics Domain (DM)

---

**Report Date**: 2024-01-15  
**Report Type**: Critical Data Quality Issue  
**Priority**: HIGH  
**Issue ID**: DQ-MAXIS08-DM-001  
**Domain**: DM (Demographics)  
**Source File**: DEMO.csv  
**SDTM Version**: 3.4  

---

## Executive Summary

A critical data quality issue has been identified in the demographics source data (DEMO.csv) where **"HISPANIC" is recorded in the RACE field (RCE)**. According to CDISC SDTM controlled terminology standards, **HISPANIC represents ETHNICITY, not RACE**.

This issue prevents compliant SDTM DM domain generation and requires **immediate clinical review and correction**.

---

## Issue Description

### Problem Statement

The source field `RCE` (Race) contains the value "HISPANIC" for some subjects. However:

- **CDISC Definition**: "Hispanic or Latino" is an **ETHNICITY** classification (ETHNIC variable in SDTM)
- **CDISC RACE**: Should be one of: AMERICAN INDIAN OR ALASKA NATIVE, ASIAN, BLACK OR AFRICAN AMERICAN, NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER, WHITE, MULTIPLE, NOT REPORTED, or UNKNOWN

### CDISC Standards Reference

**From CDISC Controlled Terminology (RACE)**:
- ✅ AMERICAN INDIAN OR ALASKA NATIVE
- ✅ ASIAN
- ✅ BLACK OR AFRICAN AMERICAN
- ✅ NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER
- ✅ WHITE
- ✅ MULTIPLE
- ✅ NOT REPORTED
- ✅ UNKNOWN

❌ **HISPANIC** is NOT a valid RACE value

**From CDISC Controlled Terminology (ETHNIC)**:
- ✅ HISPANIC OR LATINO
- ✅ NOT HISPANIC OR LATINO
- ✅ NOT REPORTED
- ✅ UNKNOWN

✅ **HISPANIC OR LATINO** is the correct ETHNICITY value

---

## Impact Assessment

### Regulatory Impact
- **FDA Submission**: DM domain will NOT pass FDA validation with non-compliant RACE values
- **Pinnacle 21 Validation**: Will flag as critical error (controlled terminology violation)
- **Define-XML**: Will not validate against CDISC CT standards

### Data Impact
- **Affected Records**: All subjects with `RCE='HISPANIC'`
- **Affected Variables**: 
  - `RACE` - Cannot be populated with compliant value
  - `ETHNIC` - Can be set to "HISPANIC OR LATINO" but RACE still needs correction

### Timeline Impact
- **Estimated Delay**: 2-3 days for clinical review and correction
- **Critical Path**: BLOCKS final DM domain generation and downstream domain processing

---

## Affected Subjects

**Query to identify affected subjects**:

```sql
SELECT USUBJID, PT, RCE
FROM DEMO
WHERE RCE = 'HISPANIC'
ORDER BY PT;
```

**Example affected records** (based on provided sample data):

| USUBJID | SUBJID | Site | Source RCE | Current RACE | Target RACE | Target ETHNIC |
|---------|--------|------|------------|--------------|-------------|---------------|
| *TBD* | *TBD* | 408 | HISPANIC | *INVALID* | **NEEDS REVIEW** | HISPANIC OR LATINO |

**Action Required**: Generate full list from actual data and send to clinical team for review.

---

## Root Cause Analysis

### Why This Happened

1. **Source System Design Issue**: EDC/CRF form likely combined race and ethnicity into a single field
2. **Data Entry Practice**: Sites may have been instructed to select "HISPANIC" when subjects identified as Hispanic/Latino
3. **Missing Ethnicity Field**: Source data does not appear to have a separate ethnicity collection field

### Correct Data Collection Practice

Race and ethnicity should be collected **separately** per FDA and CDISC guidelines:

**Two separate questions**:
1. **Ethnicity**: "Are you Hispanic or Latino?" 
   - Hispanic or Latino
   - Not Hispanic or Latino
   - Not Reported
   - Unknown

2. **Race**: "What is your race?" (check all that apply)
   - American Indian or Alaska Native
   - Asian
   - Black or African American
   - Native Hawaiian or Other Pacific Islander
   - White
   - Not Reported
   - Unknown

---

## Proposed Resolution Options

### Option 1: Query Sites for Actual Race (RECOMMENDED)

**Process**:
1. Generate data clarification form (DCF) for each affected subject
2. Request sites provide actual RACE value from source documentation
3. Update SDTM mapping with corrected values
4. Set `ETHNIC = "HISPANIC OR LATINO"` for these subjects

**Advantages**:
- ✅ Most accurate and compliant solution
- ✅ Provides true race data for analysis
- ✅ FDA-acceptable approach

**Disadvantages**:
- ⏱️ Takes 2-3 days for site response
- 📄 Requires DCF generation and tracking

**Recommended Mapping**:
```
For subjects where RCE='HISPANIC':
  RACE = [Value provided by site: WHITE, BLACK OR AFRICAN AMERICAN, ASIAN, etc.]
  ETHNIC = "HISPANIC OR LATINO"
```

---

### Option 2: Use "NOT REPORTED" for Race (INTERIM SOLUTION)

**Process**:
1. For subjects with `RCE='HISPANIC'`, set `RACE = "NOT REPORTED"`
2. Set `ETHNIC = "HISPANIC OR LATINO"`
3. Document in data quality tracking that actual race was not collected
4. Include note in Define-XML comment for RACE variable

**Advantages**:
- ⏱️ Immediate - no delay
- ✅ Compliant with CDISC CT (NOT REPORTED is valid value)

**Disadvantages**:
- ❌ Loss of race data for analysis
- ❌ May raise FDA questions about data collection quality

**Recommended Mapping**:
```
For subjects where RCE='HISPANIC':
  RACE = "NOT REPORTED"
  ETHNIC = "HISPANIC OR LATINO"
```

---

### Option 3: Assume Race Based on Demographics (NOT RECOMMENDED)

**Process**:
Make assumptions about race based on other demographic data or geography

**Why NOT Recommended**:
- ❌ Scientifically invalid
- ❌ Introduces bias
- ❌ Violates data integrity principles
- ❌ FDA may reject as data fabrication

**Conclusion**: **DO NOT USE THIS APPROACH**

---

## Recommended Action Plan

### Immediate Actions (Day 1)

**Step 1: Generate Subject List**
```python
# Generate list of affected subjects
affected_subjects = demo_df[demo_df['RCE'] == 'HISPANIC'][['USUBJID', 'PT', 'INVSITE', 'RCE']]
affected_subjects.to_csv('HISPANIC_Race_Query_List.csv', index=False)
print(f"Total affected subjects: {len(affected_subjects)}")
```

**Step 2: Create Data Clarification Form (DCF)**

**DCF Template**:

```
═══════════════════════════════════════════════════════════════════════
DATA CLARIFICATION FORM
Study: MAXIS-08
Issue: Race Value Clarification for Hispanic/Latino Subjects
═══════════════════════════════════════════════════════════════════════

Site Number: ___________
Subject ID: ___________
Current Race Value in Database: HISPANIC

ISSUE: 
The database currently lists "HISPANIC" as the race for this subject. 
Per FDA and CDISC standards, Hispanic/Latino is an ETHNICITY, not a race.

CLARIFICATION NEEDED:
Please provide the subject's RACE from source documentation (check one):

☐ American Indian or Alaska Native
☐ Asian
☐ Black or African American
☐ Native Hawaiian or Other Pacific Islander
☐ White
☐ Multiple (please specify): _______________________________
☐ Not Reported (subject declined to provide race)
☐ Unknown (race information not available)

Ethnicity will be recorded as: Hispanic or Latino ✓

Source Document Reference: _________________________________
Site Signature: _________________ Date: _______________

Please return completed form within 48 hours.
═══════════════════════════════════════════════════════════════════════
```

**Step 3: Send Queries to Clinical Team**

**Email Template**:

```
Subject: URGENT - Data Query: Race Classification for Hispanic Subjects - MAXIS-08

Dear Clinical Data Management Team,

We have identified a critical data quality issue in study MAXIS-08 that requires 
immediate site query:

ISSUE: Multiple subjects have "HISPANIC" recorded in the RACE field. Per CDISC 
standards required for FDA submission, Hispanic is an ethnicity, not a race.

IMPACT: Cannot generate compliant SDTM data for FDA submission without resolution.

ACTION REQUIRED: 
1. Review attached subject list (XX affected subjects)
2. Issue DCFs to sites requesting actual race information
3. Target completion: 48 hours

ATTACHED:
- HISPANIC_Race_Query_List.csv (list of affected subjects)
- DCF_Template_Race_Clarification.pdf (query form for sites)
- CDISC_Race_Ethnicity_Standards.pdf (reference document)

PRIORITY: HIGH - Blocks SDTM submission

Please confirm receipt and expected timeline for resolution.

Thank you,
SDTM Programming Team
```

---

### Short-Term Actions (Day 2-3)

**Step 4: Track Query Responses**

Create tracking spreadsheet:

| Subject ID | Site | Query Sent | Response Received | Corrected Race | Status |
|------------|------|------------|-------------------|----------------|--------|
| 01-01 | 408 | 2024-01-15 | | | Open |
| 01-02 | 408 | 2024-01-15 | | | Open |

**Step 5: Update Mapping Specification**

Once corrected race values received, update mapping logic:

```python
# Create correction lookup table
race_corrections = {
    '01-01': 'WHITE',
    '01-02': 'BLACK OR AFRICAN AMERICAN',
    # etc.
}

# Apply corrections
def correct_race(row):
    if row['RCE'] == 'HISPANIC':
        if row['SUBJID'] in race_corrections:
            return race_corrections[row['SUBJID']]
        else:
            return 'NOT REPORTED'  # Interim value
    else:
        return race_map.get(row['RCE'], '')

dm['RACE'] = demo_df.apply(correct_race, axis=1)
dm['ETHNIC'] = demo_df['RCE'].apply(
    lambda x: 'HISPANIC OR LATINO' if x == 'HISPANIC' else 'NOT REPORTED'
)
```

---

### Long-Term Actions (Post-Study)

**Step 6: Prevent Future Occurrence**

**Recommendations for future studies**:

1. **EDC Design**: Separate race and ethnicity fields in CRF
   ```
   CRF Page: Demographics
   
   Question 1: Ethnicity
   Are you Hispanic or Latino?
   ○ Yes
   ○ No
   ○ Declined to answer
   ○ Unknown
   
   Question 2: Race (select all that apply)
   ☐ American Indian or Alaska Native
   ☐ Asian
   ☐ Black or African American
   ☐ Native Hawaiian or Other Pacific Islander
   ☐ White
   ☐ Declined to answer
   ☐ Unknown
   ```

2. **Edit Checks**: Add EDC edit check that prevents "HISPANIC" in race field

3. **Site Training**: Train sites on proper race/ethnicity data collection per FDA guidelines

4. **Data Review**: Include race/ethnicity compliance check in standard data review procedures

---

## Validation After Resolution

Once race corrections are received and mapped, validate:

### Validation Checklist

- [ ] All RACE values are from CDISC CT RACE codelist
- [ ] No "HISPANIC" values remain in RACE variable
- [ ] ETHNIC properly populated for all subjects
- [ ] No subjects with both RACE and ETHNIC as "NOT REPORTED" (if possible)
- [ ] Pinnacle 21 validation passes (no CT violations)
- [ ] Define-XML validates successfully

### Validation Queries

```sql
-- Check for invalid RACE values
SELECT DISTINCT RACE
FROM DM
WHERE RACE NOT IN (
    'AMERICAN INDIAN OR ALASKA NATIVE',
    'ASIAN',
    'BLACK OR AFRICAN AMERICAN',
    'NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER',
    'WHITE',
    'MULTIPLE',
    'NOT REPORTED',
    'UNKNOWN'
);
-- Should return 0 rows

-- Check ETHNIC values
SELECT DISTINCT ETHNIC
FROM DM
WHERE ETHNIC NOT IN (
    'HISPANIC OR LATINO',
    'NOT HISPANIC OR LATINO',
    'NOT REPORTED',
    'UNKNOWN'
);
-- Should return 0 rows

-- Cross-tabulation of RACE and ETHNIC
SELECT RACE, ETHNIC, COUNT(*) as N
FROM DM
GROUP BY RACE, ETHNIC
ORDER BY RACE, ETHNIC;
```

---

## Communication Plan

### Stakeholders to Notify

| Stakeholder | Timing | Message |
|------------|--------|---------|
| Clinical Data Management | Immediate | Issue identification + action required |
| Site Management | Day 1 | DCF issuance and 48-hour turnaround |
| Study Manager | Day 1 | Issue summary + timeline impact |
| Biostatistics | Day 1 | Potential impact on demographic analyses |
| Medical Monitor | Day 2 | If clinical interpretation needed |
| Regulatory Affairs | Day 3 | If resolution delayed beyond 72 hours |

---

## Risk Mitigation

### If Sites Cannot Provide Race Information

**Fallback Plan**:
1. Use `RACE = "NOT REPORTED"` for unresolved subjects
2. Document in study data clarification log
3. Include explanatory comment in Define-XML:
   ```
   Comment for RACE variable:
   "For subjects who identified as Hispanic or Latino, race information was 
   not separately collected in the source system. These subjects have RACE 
   recorded as 'NOT REPORTED' and ETHNIC as 'HISPANIC OR LATINO'."
   ```
4. Prepare response to potential FDA question during submission review

### If Timeline Pressure is Critical

**Expedited Resolution**:
1. Escalate to study manager for site prioritization
2. Request direct site contact (phone call) instead of email query
3. Accept verbal confirmation with follow-up written documentation
4. Consider using "NOT REPORTED" for any subjects with >48 hour delay

---

## Appendix A: CDISC Standards Reference

### Race Controlled Terminology (RACE)

**CDISC Submission Value**: RACE  
**CDISC Preferred Term**: Race  
**Definition**: A classification based on common ancestry and genetics  

**Valid Values (SDTM-IG 3.4)**:
- AMERICAN INDIAN OR ALASKA NATIVE
- ASIAN
- BLACK OR AFRICAN AMERICAN
- NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER
- WHITE
- MULTIPLE (when subject indicates more than one race)
- NOT REPORTED (subject declined to provide)
- UNKNOWN (information not available)

### Ethnicity Controlled Terminology (ETHNIC)

**CDISC Submission Value**: ETHNIC  
**CDISC Preferred Term**: Ethnicity  
**Definition**: Classification based on cultural characteristics  

**Valid Values (SDTM-IG 3.4)**:
- HISPANIC OR LATINO
- NOT HISPANIC OR LATINO
- NOT REPORTED
- UNKNOWN

---

## Appendix B: FDA Guidance

### FDA Guidance for Industry: Collection of Race and Ethnicity Data (2005)

**Key Points**:
1. Race and ethnicity should be collected as **two separate questions**
2. Ethnicity question should be asked **first**:
   - "Are you Hispanic or Latino?"
3. Race question should allow **multiple selections**
4. "Hispanic or Latino" is an **ethnic category**, not a racial category
5. Hispanic/Latino individuals may be of **any race**

**FDA Minimum Standard**:
- Collect ethnicity: Hispanic/Latino vs Not Hispanic/Latino
- Collect race: per OMB standards (5 minimum categories)

---

## Appendix C: Mapping Logic

### Current (Incorrect) Mapping

```
Source RCE → SDTM RACE
BLACK → BLACK OR AFRICAN AMERICAN ✓
WHITE → WHITE ✓
ASIAN → ASIAN ✓
HISPANIC → ??? ✗ (INVALID)
```

### Corrected Mapping (Option 1 - Recommended)

```
Source RCE → SDTM RACE + ETHNIC
BLACK → RACE: BLACK OR AFRICAN AMERICAN, ETHNIC: NOT REPORTED
WHITE → RACE: WHITE, ETHNIC: NOT REPORTED
ASIAN → RACE: ASIAN, ETHNIC: NOT REPORTED
HISPANIC → RACE: [FROM SITE QUERY], ETHNIC: HISPANIC OR LATINO
```

### Corrected Mapping (Option 2 - Interim)

```
Source RCE → SDTM RACE + ETHNIC
BLACK → RACE: BLACK OR AFRICAN AMERICAN, ETHNIC: NOT REPORTED
WHITE → RACE: WHITE, ETHNIC: NOT REPORTED
ASIAN → RACE: ASIAN, ETHNIC: NOT REPORTED
HISPANIC → RACE: NOT REPORTED, ETHNIC: HISPANIC OR LATINO
```

---

## Document Control

**Version History**:

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-01-15 | SDTM Mapping Expert | Initial issue identification and resolution plan |

**Approval**:

| Role | Name | Signature | Date |
|------|------|-----------|------|
| SDTM Lead Programmer | | | |
| Clinical Data Manager | | | |
| Study Manager | | | |

**Next Review**: Upon resolution of all queries (estimated Day 4)

---

**END OF REPORT**

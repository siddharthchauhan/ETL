# SDTM Mapping Specification for AE Domain

## Metadata

| Property | Value |
|----------|-------|
| **Study ID** | MAXIS-08 |
| **Source Domain** | AEVENT.csv + AEVENTC.csv |
| **Target Domain** | AE (Adverse Events) |
| **SDTM Version** | SDTM-IG 3.4 |
| **Created By** | SDTM Transformation Agent |
| **Created Date** | 2025-01-22 |

## Description

This comprehensive mapping specification defines the transformation rules for converting raw adverse event data from the EDC system into CDISC-compliant SDTM AE domain format. The specification covers all required, expected, and permissible variables according to SDTM-IG 3.4.

---

## Source Files

### Primary Source: AEVENT.csv
- **Records:** 550
- **Columns:** 38
- **Description:** Primary adverse event data with verbatim terms and clinical assessments

### Secondary Source: AEVENTC.csv
- **Records:** 276
- **Columns:** 36
- **Description:** Coded adverse event data with MedDRA dictionary terms

---

## Variable Mappings

### 1. Required Identifier Variables

#### STUDYID - Study Identifier
- **Type:** Char (Length: 20)
- **Core:** Required
- **Source Column:** None
- **Derivation:** Constant: 'MAXIS-08'
- **Transformation:** `ASSIGN('MAXIS-08')`
- **Comments:** Study identifier constant for all records

#### DOMAIN - Domain Abbreviation
- **Type:** Char (Length: 2)
- **Core:** Required
- **Source Column:** None
- **Derivation:** Constant: 'AE'
- **Transformation:** `ASSIGN('AE')`
- **Comments:** Domain identifier constant

#### USUBJID - Unique Subject Identifier
- **Type:** Char (Length: 40)
- **Core:** Required
- **Source Columns:** STUDY, INVSITE, PT
- **Derivation:** STUDYID || '-' || SITEID || '-' || SUBJID
- **Transformation:** `CONCAT(STUDY, '-', INVSITE, '-', PT)`
- **Example:** MAXIS-08-101-001
- **Comments:** Concatenation of study, site, and subject identifiers

#### AESEQ - Sequence Number
- **Type:** Num (Length: 8)
- **Core:** Required
- **Source Column:** None
- **Derivation:** ROW_NUMBER() OVER (PARTITION BY USUBJID ORDER BY AESTDTC)
- **Transformation:** `SEQUENCE(USUBJID, AESTDTC)`
- **Comments:** Unique sequence number per subject, ordered by start date

---

### 2. Adverse Event Term Variables

#### AETERM - Reported Term for the Adverse Event
- **Type:** Char (Length: 200)
- **Core:** Required
- **Source Column:** AEVERB
- **Derivation:** Direct copy
- **Transformation:** `COPY(AEVERB)`
- **Comments:** Verbatim adverse event term as reported by investigator

#### AEDECOD - Dictionary-Derived Term
- **Type:** Char (Length: 200)
- **Core:** Required
- **Source Column:** AEPTT
- **Derivation:** MedDRA Preferred Term from coding
- **Transformation:** `COPY(AEPTT)`
- **Controlled Terminology:** MedDRA PT
- **Comments:** Preferred Term from MedDRA dictionary coding

---

### 3. MedDRA Coding Hierarchy Variables

#### AELLT - Lowest Level Term
- **Type:** Char (Length: 200)
- **Core:** Permissible
- **Source Column:** AELTT
- **Transformation:** `COPY(AELTT)`
- **Controlled Terminology:** MedDRA LLT

#### AELLTCD - Lowest Level Term Code
- **Type:** Num (Length: 8)
- **Core:** Permissible
- **Source Column:** AELTC
- **Transformation:** `COPY(AELTC)`
- **Controlled Terminology:** MedDRA

#### AEPTCD - Preferred Term Code
- **Type:** Num (Length: 8)
- **Core:** Permissible
- **Source Column:** AEPTC
- **Transformation:** `COPY(AEPTC)`
- **Controlled Terminology:** MedDRA

#### AEHLT - High Level Term
- **Type:** Char (Length: 200)
- **Core:** Permissible
- **Source Column:** AEHTT
- **Transformation:** `COPY(AEHTT)`
- **Controlled Terminology:** MedDRA HLT

#### AEHLTCD - High Level Term Code
- **Type:** Num (Length: 8)
- **Core:** Permissible
- **Source Column:** AEHTC
- **Transformation:** `COPY(AEHTC)`
- **Controlled Terminology:** MedDRA

#### AEHLGT - High Level Group Term
- **Type:** Char (Length: 200)
- **Core:** Permissible
- **Source Column:** AEHGT1
- **Transformation:** `COPY(AEHGT1)`
- **Controlled Terminology:** MedDRA HLGT

#### AEHLGTCD - High Level Group Term Code
- **Type:** Num (Length: 8)
- **Core:** Permissible
- **Source Column:** AEHGC
- **Transformation:** `COPY(AEHGC)`
- **Controlled Terminology:** MedDRA

#### AESOC - Primary System Organ Class
- **Type:** Char (Length: 200)
- **Core:** Permissible
- **Source Column:** AESCT
- **Transformation:** `COPY(AESCT)`
- **Controlled Terminology:** MedDRA SOC

#### AESOCCD - Primary System Organ Class Code
- **Type:** Num (Length: 8)
- **Core:** Permissible
- **Source Column:** AESCC
- **Transformation:** `COPY(AESCC)`
- **Controlled Terminology:** MedDRA

---

### 4. Timing Variables

#### AESTDTC - Start Date/Time of Adverse Event
- **Type:** Char (Length: 20)
- **Core:** Expected
- **Source Column:** AESTDT
- **Derivation:** Convert from YYYYMMDD to ISO 8601 format
- **Transformation:** `DATE_FORMAT(AESTDT, 'YYYYMMDD', 'YYYY-MM-DD')`
- **Controlled Terminology:** ISO 8601
- **Example:** 20080910 → 2008-09-10
- **Comments:** Handles both complete dates (YYYYMMDD) and partial dates (YYYYMM)

#### AEENDTC - End Date/Time of Adverse Event
- **Type:** Char (Length: 20)
- **Core:** Permissible
- **Source Column:** AEENDT
- **Derivation:** Convert from YYYYMMDD to ISO 8601 format
- **Transformation:** `DATE_FORMAT(AEENDT, 'YYYYMMDD', 'YYYY-MM-DD')`
- **Controlled Terminology:** ISO 8601
- **Example:** 20080911 → 2008-09-11

#### AESTDY - Study Day of Start of Adverse Event
- **Type:** Num (Length: 8)
- **Core:** Permissible
- **Source Column:** None (Derived)
- **Derivation:** 
  - IF(AESTDTC >= RFSTDTC, DAYS(AESTDTC - RFSTDTC) + 1, DAYS(AESTDTC - RFSTDTC))
- **Transformation:** `STUDY_DAY(AESTDTC, RFSTDTC)`
- **Comments:** Calculated from DM.RFSTDTC. Positive values ≥ reference date, negative values < reference date

#### AEENDY - Study Day of End of Adverse Event
- **Type:** Num (Length: 8)
- **Core:** Permissible
- **Source Column:** None (Derived)
- **Derivation:** IF(AEENDTC >= RFSTDTC, DAYS(AEENDTC - RFSTDTC) + 1, DAYS(AEENDTC - RFSTDTC))
- **Transformation:** `STUDY_DAY(AEENDTC, RFSTDTC)`

#### AEDTC - Date/Time of Collection
- **Type:** Char (Length: 20)
- **Core:** Permissible
- **Source Column:** AESTDT
- **Derivation:** Same as AESTDTC
- **Transformation:** `COPY(AESTDTC)`
- **Controlled Terminology:** ISO 8601
- **Comments:** Collection date typically same as event start date

---

### 5. Clinical Assessment Variables

#### AESEV - Severity/Intensity
- **Type:** Char (Length: 20)
- **Core:** Expected
- **Source Column:** AESEV
- **Derivation:** Map to CDISC Controlled Terminology
- **Transformation:** `MAP(AESEV, {'MILD': 'MILD', 'MODERATE': 'MODERATE', 'SEVERE': 'SEVERE'})`
- **Controlled Terminology:** AESEV (C66769)
- **Valid Values:** MILD, MODERATE, SEVERE
- **Extensible:** No

#### AESER - Serious Event
- **Type:** Char (Length: 1)
- **Core:** Expected
- **Source Column:** AESERL
- **Derivation:** Map to Y/N format
- **Transformation:** `MAP(AESERL, {'SERIOUS': 'Y', 'NOT SERIOUS': 'N', '1': 'Y', '0': 'N'})`
- **Controlled Terminology:** NY (C66742)
- **Valid Values:** Y (Yes), N (No)
- **Extensible:** No

#### AEREL - Causality
- **Type:** Char (Length: 40)
- **Core:** Expected
- **Source Column:** AEREL
- **Derivation:** Standardize relationship terminology
- **Transformation:** 
```
MAP(AEREL, {
  'UNRELATED': 'NOT RELATED',
  'UNLIKELY': 'UNLIKELY',
  'POSSIBLE': 'POSSIBLY RELATED',
  'RELATED': 'RELATED',
  'PROBABLE': 'PROBABLE',
  'DEFINITE': 'DEFINITE'
})
```
- **Controlled Terminology:** Study-specific
- **Comments:** Relationship of adverse event to study drug

#### AEACN - Action Taken with Study Treatment
- **Type:** Char (Length: 40)
- **Core:** Expected
- **Source Column:** AEACTL
- **Derivation:** Map to CDISC Controlled Terminology
- **Transformation:** 
```
MAP(AEACTL, {
  'NONE': 'DOSE NOT CHANGED',
  'REDUCED': 'DOSE REDUCED',
  'INTERRUPTED': 'DRUG INTERRUPTED',
  'WITHDRAWN': 'DRUG WITHDRAWN'
})
```
- **Controlled Terminology:** ACN (C66767)
- **Valid Values:** DOSE NOT CHANGED, DOSE REDUCED, DRUG INTERRUPTED, DRUG WITHDRAWN, NOT APPLICABLE
- **Extensible:** Yes

#### AEOUT - Outcome of Adverse Event
- **Type:** Char (Length: 40)
- **Core:** Expected
- **Source Column:** AEOUTCL
- **Derivation:** Map to CDISC Controlled Terminology
- **Transformation:** 
```
MAP(AEOUTCL, {
  'RESOLVED': 'RECOVERED/RESOLVED',
  'RECOVERING': 'RECOVERING/RESOLVING',
  'NOT RESOLVED': 'NOT RECOVERED/NOT RESOLVED',
  'CONTINUING': 'NOT RECOVERED/NOT RESOLVED',
  'FATAL': 'FATAL'
})
```
- **Controlled Terminology:** OUT (C66768)
- **Valid Values:** FATAL, NOT RECOVERED/NOT RESOLVED, RECOVERED/RESOLVED, RECOVERING/RESOLVING, RECOVERED WITH SEQUELAE, UNKNOWN
- **Extensible:** No

---

### 6. Serious Event Criteria Variables

#### AESDTH - Results in Death
- **Type:** Char (Length: 1)
- **Core:** Expected
- **Source Column:** None (Derived)
- **Derivation:** Derived from outcome
- **Transformation:** `IF(AEOUT == 'FATAL', 'Y', 'N')`
- **Controlled Terminology:** NY (C66742)
- **Valid Values:** Y, N
- **Comments:** Y if adverse event resulted in death

#### AESHOSP - Requires or Prolongs Hospitalization
- **Type:** Char (Length: 1)
- **Core:** Expected
- **Source Column:** None (Derived)
- **Derivation:** From serious event criteria
- **Transformation:** `CHECK_SERIOUSNESS_CRITERIA(source, 'HOSPITALIZATION')`
- **Controlled Terminology:** NY (C66742)
- **Valid Values:** Y, N

#### AESDISAB - Results in Disability
- **Type:** Char (Length: 1)
- **Core:** Expected
- **Source Column:** None (Derived)
- **Derivation:** From serious event criteria
- **Transformation:** `CHECK_SERIOUSNESS_CRITERIA(source, 'DISABILITY')`
- **Controlled Terminology:** NY (C66742)
- **Valid Values:** Y, N

#### AESCONG - Congenital Anomaly or Birth Defect
- **Type:** Char (Length: 1)
- **Core:** Expected
- **Source Column:** None (Derived)
- **Derivation:** From serious event criteria
- **Transformation:** `CHECK_SERIOUSNESS_CRITERIA(source, 'CONGENITAL')`
- **Controlled Terminology:** NY (C66742)
- **Valid Values:** Y, N

#### AESLIFE - Is Life Threatening
- **Type:** Char (Length: 1)
- **Core:** Expected
- **Source Column:** None (Derived)
- **Derivation:** From serious event criteria
- **Transformation:** `CHECK_SERIOUSNESS_CRITERIA(source, 'LIFE_THREATENING')`
- **Controlled Terminology:** NY (C66742)
- **Valid Values:** Y, N

#### AESMIE - Other Medically Important Serious Event
- **Type:** Char (Length: 1)
- **Core:** Expected
- **Source Column:** None (Derived)
- **Derivation:** From serious event criteria
- **Transformation:** `CHECK_SERIOUSNESS_CRITERIA(source, 'MEDICALLY_IMPORTANT')`
- **Controlled Terminology:** NY (C66742)
- **Valid Values:** Y, N

---

### 7. Visit and Epoch Variables

#### VISITNUM - Visit Number
- **Type:** Num (Length: 8)
- **Core:** Expected
- **Source Column:** VISIT
- **Derivation:** Map visit codes to numeric values
- **Transformation:** `VISIT_NUMBER(VISIT)`
- **Comments:** Numeric visit identifier; use 99 for unscheduled visits

#### VISIT - Visit Name
- **Type:** Char (Length: 40)
- **Core:** Permissible
- **Source Column:** VISIT
- **Transformation:** `COPY(VISIT)`
- **Controlled Terminology:** Study-specific
- **Comments:** Protocol-defined visit name

#### EPOCH - Epoch
- **Type:** Char (Length: 40)
- **Core:** Permissible
- **Source Column:** None (Derived)
- **Derivation:** Derived from visit or study day
- **Transformation:** `DERIVE_EPOCH(VISITNUM, AESTDY)`
- **Controlled Terminology:** Study-specific
- **Examples:** SCREENING, TREATMENT, FOLLOW-UP
- **Comments:** Trial epoch assigned based on visit or timing

---

## Controlled Terminology Reference

### AESEV - Severity/Intensity Scale for Adverse Events (C66769)
- **Valid Values:** MILD, MODERATE, SEVERE
- **Extensible:** No
- **Description:** Standardized severity grading for adverse events

### NY - No Yes Response (C66742)
- **Valid Values:** N (No), Y (Yes)
- **Extensible:** No
- **Used For:** AESER, AESDTH, AESHOSP, AESDISAB, AESCONG, AESLIFE, AESMIE

### ACN - Action Taken with Study Treatment (C66767)
- **Valid Values:**
  - DOSE NOT CHANGED
  - DOSE REDUCED
  - DOSE INCREASED
  - DRUG INTERRUPTED
  - DRUG WITHDRAWN
  - NOT APPLICABLE
  - NOT EVALUABLE
  - UNKNOWN
- **Extensible:** Yes

### OUT - Outcome of Event (C66768)
- **Valid Values:**
  - FATAL
  - NOT RECOVERED/NOT RESOLVED
  - RECOVERED/RESOLVED
  - RECOVERING/RESOLVING
  - RECOVERED WITH SEQUELAE
  - UNKNOWN
- **Extensible:** No

### MedDRA Dictionary (Medical Dictionary for Regulatory Activities)
- **Used For:** AETERM coding hierarchy
- **Levels:** LLT → PT → HLT → HLGT → SOC
- **Version:** Document the MedDRA version used for coding

---

## Transformation Rules Summary

### 1. Direct Copy (COPY)
Variables copied directly from source without transformation:
- AEVERB → AETERM
- AEPTT → AEDECOD
- AELTT → AELLT
- MedDRA codes and terms

### 2. Constant Assignment (ASSIGN)
Fixed values assigned to all records:
- STUDYID = 'MAXIS-08'
- DOMAIN = 'AE'

### 3. Concatenation (CONCAT)
Multiple source fields combined:
- USUBJID = STUDY + '-' + INVSITE + '-' + PT

### 4. Date Formatting (DATE_FORMAT)
Convert EDC dates to ISO 8601:
- YYYYMMDD → YYYY-MM-DD
- YYYYMM → YYYY-MM
- Handle partial dates appropriately

### 5. Value Mapping (MAP)
Standardize categorical values to CDISC CT:
- AESEV: Source severity → MILD/MODERATE/SEVERE
- AESER: Source serious flag → Y/N
- AEREL: Source causality → Standardized relationship
- AEACN: Source action → CDISC action terms
- AEOUT: Source outcome → CDISC outcome terms

### 6. Derivation Functions
Calculate new values:
- AESEQ: Generate sequence per subject
- AESTDY/AEENDY: Calculate study days from reference date
- AESDTH: Derive from outcome
- Serious criteria: Extract from seriousness assessments

---

## Data Quality Rules

### Required Variable Checks
1. ✓ STUDYID must be present for all records
2. ✓ DOMAIN must equal 'AE' for all records
3. ✓ USUBJID must be present and valid
4. ✓ AESEQ must be unique within subject
5. ✓ AETERM must be non-null
6. ✓ AEDECOD must be non-null

### Expected Variable Checks
1. ⚠ AESTDTC should be present (expected for all events)
2. ⚠ AESEV should be present (expected clinical assessment)
3. ⚠ AESER should be present (required for regulatory reporting)
4. ⚠ AEREL should be present (causality assessment required)

### Controlled Terminology Validation
1. AESEV must be one of: MILD, MODERATE, SEVERE
2. AESER must be Y or N
3. All NY variables must be Y or N (or null if not applicable)
4. AEACN must match CDISC CT values
5. AEOUT must match CDISC CT values

### Date Format Validation
1. All --DTC variables must follow ISO 8601 format
2. AESTDTC ≤ AEENDTC (if both present)
3. Partial dates properly formatted (YYYY-MM or YYYY)

### Cross-Domain Dependencies
1. USUBJID must exist in DM domain
2. RFSTDTC from DM required for study day calculations
3. VISITNUM should align with SV domain visits

### Business Rules
1. If AESER = 'Y', at least one serious criteria variable should = 'Y'
2. If AEOUT = 'FATAL', then AESDTH should = 'Y'
3. If AEENDTC is null and AEOUT indicates resolution, data may be incomplete
4. AESEQ must be sequential within subject without gaps

---

## Implementation Notes

### Source File Handling
- **Primary Source (AEVENT.csv):** Contains the verbatim terms and initial clinical assessments
- **Secondary Source (AEVENTC.csv):** Contains MedDRA coded terms
- **Merge Strategy:** Left join AEVENT with AEVENTC on common key (PrimaryKEY or AESEQ)
- **Duplicate Handling:** If duplicates exist, keep most recent coded version

### Date Conversion Strategy
```python
def convert_date_to_iso8601(date_value):
    """
    Convert various date formats to ISO 8601
    - YYYYMMDD → YYYY-MM-DD
    - YYYYMM → YYYY-MM
    - YYYY → YYYY
    - Handle missing/partial dates
    """
    if pd.isna(date_value):
        return None
    date_str = str(date_value).strip()
    if len(date_str) == 8:  # YYYYMMDD
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    elif len(date_str) == 6:  # YYYYMM
        return f"{date_str[:4]}-{date_str[4:6]}"
    elif len(date_str) == 4:  # YYYY
        return date_str
    return None
```

### Study Day Calculation
```python
def calculate_study_day(event_date, reference_date):
    """
    Calculate study day according to CDISC rules:
    - Day 1 = first day on/after reference date
    - Day -1 = day before reference date
    - No Day 0
    """
    if pd.isna(event_date) or pd.isna(reference_date):
        return None
    days_diff = (event_date - reference_date).days
    if days_diff >= 0:
        return days_diff + 1
    else:
        return days_diff
```

### Sequence Number Generation
```python
def generate_aeseq(df):
    """
    Generate AESEQ per subject, ordered by AESTDTC
    Handle ties with secondary sort on AETERM
    """
    df = df.sort_values(['USUBJID', 'AESTDTC', 'AETERM'])
    df['AESEQ'] = df.groupby('USUBJID').cumcount() + 1
    return df
```

---

## Validation Checklist

### Pre-Transformation
- [ ] Source files loaded and accessible
- [ ] Source column names verified
- [ ] Sample data reviewed for format understanding
- [ ] DM domain available for RFSTDTC lookup

### Post-Transformation
- [ ] All required variables present and non-null
- [ ] AESEQ unique within subject
- [ ] Date formats comply with ISO 8601
- [ ] Controlled terminology values validated
- [ ] Study day calculations verified against sample records
- [ ] Cross-domain keys (USUBJID) validated against DM
- [ ] Serious event logic verified (AESER vs. criteria variables)
- [ ] Record counts match source expectations
- [ ] No unexpected null values in expected variables

### Regulatory Compliance
- [ ] CDISC SDTM-IG 3.4 conformance
- [ ] MedDRA version documented
- [ ] Controlled terminology versions documented
- [ ] Define.xml ready for generation
- [ ] Pinnacle 21 validation passed

---

## Example Transformation

### Source Record (AEVENT.csv)
```
STUDY: MAXIS-08
INVSITE: 101
PT: 001
AESEQ: 1
AEVERB: NAUSEA
AESEV: MILD
AESERL: NOT SERIOUS
AEREL: POSSIBLE
AESTDT: 20080910
AEENDT: 20080911
AEOUTCL: RESOLVED
AEACTL: NONE
VISIT: WEEK 2
```

### Target Record (AE.csv - SDTM)
```
STUDYID: MAXIS-08
DOMAIN: AE
USUBJID: MAXIS-08-101-001
AESEQ: 1
AETERM: NAUSEA
AEDECOD: Nausea
AESTDTC: 2008-09-10
AEENDTC: 2008-09-11
AESTDY: 8
AEENDY: 9
AESEV: MILD
AESER: N
AEREL: POSSIBLY RELATED
AEACN: DOSE NOT CHANGED
AEOUT: RECOVERED/RESOLVED
AESDTH: N
AESHOSP: N
AESDISAB: N
AESCONG: N
AESLIFE: N
AESMIE: N
VISITNUM: 2
VISIT: WEEK 2
EPOCH: TREATMENT
```

---

## References

1. **CDISC SDTM-IG 3.4** - Study Data Tabulation Model Implementation Guide Version 3.4
2. **CDISC Controlled Terminology** - Latest published version
3. **MedDRA Dictionary** - Medical Dictionary for Regulatory Activities (version used in study)
4. **FDA Study Data Technical Conformance Guide** - Version 5.3 or latest
5. **ICH E2A** - Clinical Safety Data Management: Definitions and Standards for Expedited Reporting
6. **21 CFR Part 11** - Electronic Records; Electronic Signatures

---

## Contact & Support

For questions about this mapping specification:
- Contact: SDTM Transformation Team
- Study: MAXIS-08
- Version Control: Track changes in mapping specification updates
- Review Cycle: Periodic review and validation against updated CDISC standards

---

*Document Generated: 2025-01-27*
*Specification Version: 1.0*
*Status: Ready for Implementation*

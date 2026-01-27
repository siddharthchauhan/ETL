# Common SDTM Validation Issues & Resolutions

## Table of Contents
1. [Critical Errors](#critical-errors)
2. [Controlled Terminology Issues](#controlled-terminology-issues)
3. [Date/Time Issues](#datetime-issues)
4. [Variable-Specific Issues](#variable-specific-issues)
5. [Domain-Specific Issues](#domain-specific-issues)
6. [Define.xml Issues](#definexml-issues)

---

## Critical Errors

### SD1000: Missing Required Variable
**Message:** Required variable [VARIABLE] is missing from [DOMAIN]
**Cause:** Domain missing a Core="Required" variable
**Resolution:**
- Add the missing variable
- Verify against SDTM IG domain specification
- If data not collected, discuss with medical team

### SD1001: Invalid USUBJID
**Message:** USUBJID format is inconsistent across domains
**Cause:** USUBJID constructed differently in different datasets
**Resolution:**
```
Standard format: STUDYID-SITEID-SUBJID
- Ensure same format in all domains
- Derive from DM.USUBJID using merge
```

### SD1002: Duplicate Records
**Message:** Duplicate records found based on [KEY VARIABLES]
**Cause:** Same --SEQ or key values for multiple records
**Resolution:**
- Review source data for true duplicates
- Adjust --SEQ derivation
- Verify sort order logic

### SD1003: Invalid Variable Length
**Message:** Variable [VAR] exceeds maximum length of [N]
**Cause:** Character variable too long for SDTM limits
**Resolution:**
- Truncate to 200 characters (standard max)
- Move full text to SUPPQUAL if truncation loses meaning
- For --VAL variables, 8000 char limit applies

---

## Controlled Terminology Issues

### CT0001: Value Not in Codelist
**Message:** Value "[VALUE]" for [VARIABLE] not found in codelist [CODELIST]
**Cause:** Non-standard term used where CT required
**Resolution:**
1. Check CT version (use latest)
2. Map source value to CDISC CT submission value
3. If extensible codelist, sponsor term acceptable (document)
4. If non-extensible, map to closest CT value

**Common Mapping Fixes:**
| Variable | Common Source Value | Correct CT Value |
|----------|--------------------|--------------------|
| SEX | Male, 1, M | M |
| SEX | Female, 2, F | F |
| AESER | Yes, TRUE, 1 | Y |
| AESER | No, FALSE, 0 | N |
| EXROUTE | Mouth, PO | ORAL |
| EXROUTE | IV | INTRAVENOUS |

### CT0002: Case Mismatch
**Message:** Value "[value]" should be uppercase "[VALUE]"
**Cause:** CT values must be uppercase
**Resolution:** Apply UPCASE() function to CT-controlled variables

### CT0003: Deprecated Code
**Message:** Code "[CODE]" is deprecated in current CT version
**Cause:** Using outdated CT version
**Resolution:**
- Update to current CT package
- Map deprecated values to current equivalents

---

## Date/Time Issues

### DT0001: Invalid ISO 8601 Format
**Message:** Date/Time value "[VALUE]" is not valid ISO 8601
**Cause:** Non-standard date format
**Resolution:**
```
Valid formats:
- YYYY-MM-DD (complete date)
- YYYY-MM-DDTHH:MM:SS (datetime)
- YYYY-MM (partial - month precision)
- YYYY (partial - year precision)
- YYYY-MM-DDTHH:MM (datetime without seconds)

Invalid formats:
- DD-MMM-YYYY (common source format)
- MM/DD/YYYY (US format)
- YYYY/MM/DD (slash separator)
```

### DT0002: RFSTDTC Missing or Invalid
**Message:** RFSTDTC missing or incomplete for subject [USUBJID]
**Cause:** Reference start date not properly set
**Resolution:**
- Verify first dose/treatment date in DM
- Must be complete date (YYYY-MM-DD minimum)
- Cannot derive study days without valid RFSTDTC

### DT0003: Study Day Calculation Error
**Message:** --STDY/--ENDY calculation appears incorrect
**Cause:** Wrong algorithm for study day
**Resolution:**
```python
# Correct algorithm:
if date >= RFSTDTC:
    study_day = (date - RFSTDTC).days + 1
else:
    study_day = (date - RFSTDTC).days  # No +1 for pre-dose
# Note: Day 0 does not exist
```

### DT0004: End Date Before Start Date
**Message:** --ENDTC is before --STDTC
**Cause:** Data entry error or incorrect derivation
**Resolution:**
- Verify source data
- Query site if genuine error
- If ongoing, --ENDTC should be null

---

## Variable-Specific Issues

### VAR0001: --SEQ Not Unique
**Message:** --SEQ values not unique within USUBJID
**Cause:** Sequence number duplicated
**Resolution:**
```
--SEQ must be:
- Integer
- Unique within USUBJID within domain
- Sequential (gaps allowed but not recommended)
```

### VAR0002: EPOCH Inconsistent
**Message:** EPOCH value not consistent with timing
**Cause:** EPOCH doesn't match visit/date
**Resolution:**
- Derive EPOCH from SE domain or protocol timing
- Common values: SCREENING, TREATMENT, FOLLOW-UP
- Must use EPOCH codelist values

### VAR0003: --BLFL Not Unique
**Message:** Multiple baseline flags for same test/subject
**Cause:** More than one record flagged as baseline
**Resolution:**
```
Baseline rules:
- Only ONE --BLFL="Y" per test per subject
- Typically last non-missing value before RFSTDTC
- Null if no baseline, never "N"
```

### VAR0004: --STAT/--REASND Mismatch
**Message:** --STAT="NOT DONE" but --REASND is missing (or vice versa)
**Cause:** Inconsistent status/reason population
**Resolution:**
```
If --STAT = "NOT DONE" then --REASND required
If --STAT is null, --REASND must be null
If result exists, --STAT must be null
```

---

## Domain-Specific Issues

### DM Issues
| Issue | Message | Resolution |
|-------|---------|------------|
| DM0001 | ARM/ARMCD not matching TA domain | Sync with TA domain values |
| DM0002 | Missing RFSTDTC | Add first treatment date |
| DM0003 | AGE not matching BRTHDTC calculation | Verify calculation or use collected AGE |

### AE Issues
| Issue | Message | Resolution |
|-------|---------|------------|
| AE0001 | AESER=Y but no seriousness criteria | Set at least one AESxxx=Y |
| AE0002 | AEDECOD missing | Complete MedDRA coding |
| AE0003 | AEOUT=FATAL but AESDTH≠Y | Align death indicators |

### LB Issues
| Issue | Message | Resolution |
|-------|---------|------------|
| LB0001 | --STRESN missing for numeric result | Convert --ORRES to numeric |
| LB0002 | --STRESU different from --ORRESU but no conversion | Apply unit conversion formula |
| LB0003 | Reference ranges incomplete | Add --STNRLO/--STNRHI |

### EX Issues
| Issue | Message | Resolution |
|-------|---------|------------|
| EX0001 | EXDOSE=0 but EXDOSTXT missing | Add EXDOSTXT for zero dose explanation |
| EX0002 | Gaps in exposure records | Verify intentional gaps or add EXADJ records |

---

## Define.xml Issues

### DEF0001: Missing Computational Method
**Message:** Derived variable [VAR] missing computational method
**Cause:** Origin=Derived but no method documented
**Resolution:**
- Add ComputationalMethod element
- Describe derivation algorithm clearly

### DEF0002: Codelist Reference Missing
**Message:** Variable uses codelist but no CodeListRef in define
**Cause:** CT-controlled variable not linked to codelist
**Resolution:**
- Add CodeListRef to ItemDef
- Include CodeList definition for the codelist

### DEF0003: Origin Mismatch
**Message:** Variable origin doesn't match actual data source
**Cause:** Origin metadata incorrect
**Resolution:**
```
Valid Origins:
- CRF (collected on case report form)
- Derived (calculated/transformed)
- Assigned (sponsor-assigned constant)
- Protocol (from protocol document)
- eDT (electronic data transfer)
- Predecessor (from previous submission)
```

### DEF0004: Comment Too Long
**Message:** Comment exceeds maximum length
**Cause:** Comment text too verbose
**Resolution:**
- Shorten comment
- Move detailed explanation to reviewer's guide

---

## Resolution Workflow

### For Each Validation Issue:

1. **Classify** - Error/Warning/Notice
2. **Investigate** - Understand root cause
3. **Resolve or Document**
   - Errors: Must fix
   - Warnings: Fix if possible, document if acceptable
   - Notices: Review, usually no action needed

4. **Re-validate** - Confirm resolution
5. **Document** - Update reviewer's guide with explanations

### Acceptable Warning Documentation
```
Issue: SD1234 - [Description]
Justification: [Why this is acceptable]
Reference: [Protocol section, SAP, etc.]
```

---

## Validation Tools

### Pinnacle 21 Community
- Standard FDA validation
- Free for individual use
- Rules updated quarterly

### OpenCDISC/Pinnacle 21 Enterprise
- Commercial version
- Custom rules support
- Integrated reporting

### SAS Clinical Standards Toolkit
- SAS-based validation
- Customizable
- Requires SAS license

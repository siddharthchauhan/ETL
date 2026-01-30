# Common SDTM Validation Issues and Resolutions

## Error-Level Issues (Must Fix)

### SD0028: USUBJID is not unique within domain

**Cause:** Duplicate records with same USUBJID
**Resolution:**
- Check for true duplicates in source data
- Verify --SEQ derivation is working correctly
- Ensure one record per observation per subject

### SD1001: RFSTDTC is null for a treated subject

**Cause:** Missing reference start date in DM for subjects with exposure records
**Resolution:**
- Set RFSTDTC = first dose date (EXSTDTC) for treated subjects
- Screen failures may have null RFSTDTC (acceptable)
- Document in define.xml if intentionally null

### SD0083: --SEQ variable is not populated

**Cause:** Missing sequence numbers
**Resolution:**
- Derive --SEQ as sequential integer within USUBJID + domain
- Start at 1 for each subject
- No gaps in sequence

### CT2001: Value not found in codelist

**Cause:** Non-standard controlled terminology value
**Resolution:**
- Map source value to correct CT term
- If codelist is extensible, sponsor term acceptable with documentation
- If not extensible, must use existing CT value

### DD0006: Invalid ISO 8601 date format

**Cause:** Incorrect date format in --DTC variables
**Resolution:**
- Use format: YYYY-MM-DDTHH:MM:SS
- Partial dates: YYYY-MM-DD, YYYY-MM, or YYYY
- No other formats acceptable

---

## Warning-Level Issues (Evaluate)

### SD1015: Start date is after end date

**Cause:** --STDTC > --ENDTC
**Resolution:**
- Verify dates in source data
- May be data entry error - query site
- If same day event with times unknown, acceptable

### SD0066: Value for --STAT not 'NOT DONE'

**Cause:** Invalid completion status value
**Resolution:**
- Only "NOT DONE" is valid for --STAT
- Blank if procedure was done
- Don't use "DONE", "COMPLETED", etc.

### SD1020: DSDECOD value not from NCOMPLT codelist

**Cause:** Non-standard disposition term
**Resolution:**
- Map to standard NCOMPLT term
- Add DSTERM for verbatim if needed
- Common valid values: COMPLETED, ADVERSE EVENT, DEATH, LOST TO FOLLOW-UP, WITHDRAWAL BY SUBJECT

### SD0009: Variable value exceeds defined length

**Cause:** Character value longer than variable length in define.xml
**Resolution:**
- Increase length in define.xml
- Truncate value (not recommended)
- Split into multiple variables if appropriate

### SD1028: EPOCH is null

**Cause:** Missing epoch assignment
**Resolution:**
- Derive EPOCH from SE domain based on --DTC
- Must match TE.ELEMENT epoch
- Document algorithm in define.xml

---

## Notice-Level Issues (Review)

### SD0059: Variable not in expected order

**Cause:** Variables not sorted per IG specification
**Resolution:**
- Reorder variables per SDTM IG order
- Required/Expected before Permissible
- Timing variables typically last

### SD0048: Subject has no records in DM

**Cause:** Data in other domains but no DM record
**Resolution:**
- Ensure all subjects have DM record
- May indicate data merge issue
- Check USUBJID derivation consistency

### DD0063: Records not sorted correctly

**Cause:** Dataset not sorted per specification
**Resolution:**
- Sort per keys in domain specification
- Document sort order in define.xml
- Typical: STUDYID, USUBJID, --DTC, --SEQ

---

## Acceptable Exceptions

| Issue | When Acceptable | Documentation Required |
|-------|-----------------|------------------------|
| Null RFSTDTC | Screen failures | Define.xml comment |
| Partial dates | Date components unknown | Define.xml origin |
| Extensible CT terms | No standard term exists | Define.xml, cSDRG |
| Missing expected variable | Data not collected | Define.xml comment |
| Split domains | Complex data structure | cSDRG explanation |

---

## Pre-Submission Checklist

- [ ] All Error-level issues resolved
- [ ] Warning-level issues evaluated and documented
- [ ] Notice-level issues reviewed
- [ ] Define.xml matches dataset contents
- [ ] All CT values valid or documented
- [ ] USUBJID consistent across domains
- [ ] Reference dates (RFSTDTC) populated appropriately
- [ ] Sequence variables complete and unique
- [ ] Sort orders correct
- [ ] Variable lengths match actual data
# MAXIS-08 DM Mapping Quick Reference Card
**For Programmers & Data Managers**

---

## 🎯 Quick Start: 3 Things You Need to Know

1. **40% Complete**: DEMO.csv gives us 8 core variables immediately
2. **Critical Blocker**: Need randomization data for ARMCD/ARM (REQUIRED fields)
3. **Data Quality Issue**: HISPANIC in race field needs clinical review

---

## ✅ Variables You Can Map RIGHT NOW (from DEMO.csv)

| Variable | Formula | Example |
|----------|---------|---------|
| **STUDYID** | `"MAXIS-08"` | MAXIS-08 |
| **DOMAIN** | `"DM"` | DM |
| **SUBJID** | `PT` | 01-01 |
| **SITEID** | `INVSITE[5:8]` | 408 (from C008_408) |
| **USUBJID** | `STUDYID + "-" + SITEID + "-" + SUBJID` | MAXIS-08-408-01-01 |
| **BRTHDTC** | `format(DOB, "YYYY-MM-DD")` | 1974-09-18 |
| **SEX** | `GENDER` (M→M, F→F) | M |
| **AGEU** | `"YEARS"` | YEARS |

### One-Liner Transformations

**Python**:
```python
dm['USUBJID'] = demo['STUDY'] + '-' + demo['INVSITE'].str[5:8] + '-' + demo['PT']
dm['BRTHDTC'] = pd.to_datetime(demo['DOB'], format='%Y%m%d').dt.strftime('%Y-%m-%d')
```

**SAS**:
```sas
USUBJID = catx('-', STUDY, substr(INVSITE,6,3), PT);
BRTHDTC = put(input(put(DOB,8.), yymmdd8.), yymmdd10.);
```

---

## 🔴 Critical Issues (BLOCKERS)

### Issue #1: Missing ARMCD/ARM (REQUIRED!)
**Status**: 🔴 BLOCKER - Cannot produce compliant DM without this  
**Need**: Randomization dataset or treatment assignment file  
**Interim Fix**: Use `ARMCD="NOTASSGN"`, `ARM="Not Assigned"`  
**Action**: Contact clinical operations for randomization data

### Issue #2: HISPANIC = Ethnicity, Not Race
**Status**: 🔴 DATA QUALITY ISSUE  
**Problem**: Source RCE field has "HISPANIC" but CDISC defines this as ETHNIC, not RACE  
**Need**: Clinical review to determine actual race for these subjects

**Quick Fix for Now**:
```python
# Temporary mapping until resolved
if RCE == 'HISPANIC':
    RACE = None  # or 'NOT REPORTED'
    ETHNIC = 'HISPANIC OR LATINO'
    # Flag for manual review
```

**Affected Subjects**: All with `RCE='HISPANIC'`

---

## ⚠️ Variables Requiring Other Domains

### Need SV (Subject Visits) Domain
- `RFSTDTC` ← MIN(SVSTDTC) or first visit date
- `RFENDTC` ← MAX(SVENDTC) or last visit date
- `DMDTC` ← SVSTDTC where VISIT='SCREENING'

### Need EX (Exposure) Domain
- `RFXSTDTC` ← MIN(EXSTDTC) per subject
- `RFXENDTC` ← MAX(EXENDTC) per subject
- `ACTARMCD`, `ACTARM` ← actual treatment received

### Need DS (Disposition) Domain
- `RFICDTC` ← Date consent signed
- `RFPENDTC` ← Final study disposition date
- `DTHDTC`, `DTHFL` ← Death date/flag if applicable

### Need Site Metadata File
- `INVID`, `INVNAM` ← Investigator info
- `COUNTRY` ← ISO country code (e.g., USA)

---

## 🧮 Calculated Variables

### AGE (Years)
**Wait for**: RFSTDTC from visits  
**Formula**: `FLOOR((RFSTDTC - BRTHDTC) / 365.25)`

```python
# Interim calculation (will need update)
from datetime import datetime
ref_date = datetime.now()  # Replace with RFSTDTC later
age = (ref_date - birth_date).days // 365
```

**⚠️ Remember**: Must recalculate once RFSTDTC available!

### DMDY (Study Day)
**Formula**: 
- If DMDTC ≥ RFSTDTC: `(DMDTC - RFSTDTC) + 1`
- If DMDTC < RFSTDTC: `(DMDTC - RFSTDTC)`
- **No day 0!**

---

## 📋 Race/Ethnicity Mapping Cheat Sheet

### Source → SDTM Mappings

| Source RCE | → | RACE | ETHNIC |
|------------|---|------|--------|
| BLACK | → | BLACK OR AFRICAN AMERICAN | NOT REPORTED |
| WHITE | → | WHITE | NOT REPORTED |
| ASIAN | → | ASIAN | NOT REPORTED |
| **HISPANIC** | → | **🔴 NEEDS REVIEW** | HISPANIC OR LATINO |

### Code Implementation

**Python**:
```python
race_map = {
    'BLACK': 'BLACK OR AFRICAN AMERICAN',
    'WHITE': 'WHITE',
    'ASIAN': 'ASIAN'
}
dm['RACE'] = demo['RCE'].map(race_map)
dm['ETHNIC'] = demo['RCE'].apply(
    lambda x: 'HISPANIC OR LATINO' if x == 'HISPANIC' else 'NOT REPORTED'
)

# Flag HISPANIC for review
hispanic_subjects = dm[demo['RCE'] == 'HISPANIC']['USUBJID']
print(f"⚠️ {len(hispanic_subjects)} subjects need race review")
```

**SAS**:
```sas
select (RCE);
    when ('BLACK') RACE = 'BLACK OR AFRICAN AMERICAN';
    when ('WHITE') RACE = 'WHITE';
    when ('ASIAN') RACE = 'ASIAN';
    when ('HISPANIC') do;
        RACE = '';
        ETHNIC = 'HISPANIC OR LATINO';
        put "REVIEW: " USUBJID "HISPANIC in race field";
    end;
    otherwise do;
        RACE = '';
        ETHNIC = 'NOT REPORTED';
    end;
end;
```

---

## 📝 Validation Quick Checks

### Before You Submit

```python
# Python validation checks
assert dm['DOMAIN'].eq('DM').all(), "DOMAIN must be DM"
assert dm['USUBJID'].is_unique, "USUBJID must be unique"
assert dm['USUBJID'].notna().all(), "USUBJID cannot be null"
assert dm.groupby('USUBJID').size().eq(1).all(), "One record per subject"
assert dm['SEX'].isin(['M', 'F', 'U', 'UNDIFFERENTIATED']).all(), "Invalid SEX"
assert dm['AGEU'].eq('YEARS').all(), "AGEU must be YEARS"

# Check date format
import re
iso_pattern = r'^\d{4}(-\d{2}(-\d{2})?)?$'
assert dm['BRTHDTC'].str.match(iso_pattern).all(), "Invalid date format"
```

**SAS**:
```sas
/* Validation checks */
proc sql;
    /* Check for duplicates */
    create table dup_check as
    select USUBJID, count(*) as n
    from dm
    group by USUBJID
    having n > 1;
    
    /* Check required fields */
    select count(*) as missing_usubjid from dm where missing(USUBJID);
    select count(*) as missing_sex from dm where missing(SEX);
    select count(*) as missing_armcd from dm where missing(ARMCD);
quit;
```

---

## 🚀 Implementation Workflow

### Step 1: Initial Load (Day 1)
```
Input: DEMO.csv
Output: dm_v1.csv (partial)
Status: 8 variables populated
Duration: 1 hour
```

### Step 2: Race Review (Day 2-3)
```
Action: Generate DQ report for HISPANIC subjects
Contact: Clinical team
Deliverable: Race corrections
Duration: 1-2 days (clinical review)
```

### Step 3: Get External Data (Day 3-5)
```
Need from data management:
☐ Randomization dataset (ARMCD/ARM)
☐ Visit data (SV domain or dates)
☐ Site metadata (COUNTRY, INVID)
```

### Step 4: Integration (Day 5-6)
```
Merge reference dates from SV/EX
Calculate AGE using RFSTDTC
Populate all derived variables
```

### Step 5: Final QC (Day 7)
```
☐ All REQUIRED fields populated
☐ Validation checks pass
☐ Pinnacle 21 clean
☐ Ready for submission
```

---

## 💡 Pro Tips

### Tip #1: USUBJID Construction
Always use the same logic across ALL domains:
```
USUBJID = STUDYID + "-" + SITEID + "-" + SUBJID
```
If DM uses different logic than AE, you'll have orphan records!

### Tip #2: Date Conversion
DOB comes as 8-digit integer (19740918). Convert carefully:
```python
# ✅ CORRECT
pd.to_datetime(dob, format='%Y%m%d').dt.strftime('%Y-%m-%d')

# ❌ WRONG - loses leading zeros if stored as number
str(dob)  # 19740918 → "19740918" but 19700101 might become "1.9700101e7"
```

### Tip #3: ARMCD Interim Values
Can't leave ARMCD null (it's Required). Use standard placeholders:
- `SCRNFAIL` = Screen Failure
- `NOTASSGN` = Not Yet Assigned
- `NOTTRT` = Not Treated

### Tip #4: Age Units
If AGE is populated, AGEU MUST be populated. Never have:
```
AGE: 45
AGEU: [blank]  ← ❌ WRONG!
```

### Tip #5: Missing vs Empty
For character variables:
- Use empty string `""` or null for missing
- Don't use "N/A", "UNK", "Missing" unless they're valid CT terms

---

## 📞 Who to Contact

| Issue | Contact |
|-------|---------|
| Missing randomization data | **Clinical Operations** |
| HISPANIC race review | **Clinical Data Management** |
| Site metadata (COUNTRY, INVID) | **Site Management Team** |
| Visit dates (RFSTDTC) | **Visit Tracking / EDC Team** |
| Validation errors | **SDTM Lead Programmer** |
| Define-XML issues | **Regulatory Submissions** |

---

## 🎯 Success Criteria

Your DM dataset is ready when:

- [ ] Zero duplicate USUBJID
- [ ] All 8 REQUIRED variables populated (including ARMCD/ARM)
- [ ] BRTHDTC in YYYY-MM-DD format
- [ ] SEX is M/F/U/UNDIFFERENTIATED (from CT)
- [ ] RACE mapped to CDISC CT (HISPANIC resolved)
- [ ] ETHNIC properly populated
- [ ] RFSTDTC ≤ RFENDTC for all subjects
- [ ] AGE calculated and matches BRTHDTC
- [ ] Pinnacle 21 validation: 0 critical errors
- [ ] Define-XML validates successfully

---

## 📚 Key Documents

1. **Full Specification**: `MAXIS-08_DM_Mapping_Specification.json`
2. **Detailed Guide**: `MAXIS-08_DM_Mapping_Summary.md`
3. **This Card**: `MAXIS-08_DM_Quick_Reference.md`

---

## 🆘 Common Errors & Fixes

### Error: "USUBJID not unique"
**Fix**: Check SITEID extraction logic. Should be `INVSITE[5:8]` not `INVSITE[6:9]`

### Error: "Invalid SEX value"
**Fix**: Use GENDER field, not GENDRL. GENDER has M/F, GENDRL has descriptions.

### Error: "Invalid date format"
**Fix**: Must be YYYY-MM-DD, not YYYYMMDD. Add hyphens!

### Error: "ARMCD is null"
**Fix**: Use interim value `"NOTASSGN"` until randomization data available.

### Warning: "RACE not in CT"
**Fix**: Check spelling. Must be "BLACK OR AFRICAN AMERICAN" not "BLACK".

---

**Last Updated**: 2024-01-15  
**Version**: 1.0  
**Next Review**: After Phase 1 completion

---

**Need help?** → Check the detailed guide or contact the SDTM programming team!

# DTA VALIDATION QUICK REFERENCE CARD
## MAXIS-08 AE Domain - One-Page Summary

---

## 🎯 SNAPSHOT

| **Study** | MAXIS-08 | **Domain** | AE (Adverse Events) |
|-----------|----------|------------|---------------------|
| **Source Records** | 826 (550+276) | **Transformed** | 276 records |
| **Compliance Score** | **88.0%** ❌ | **Target** | ≥95% ✅ |
| **Status** | **NOT READY** | **Est. Fix Time** | 3 days |

---

## 🚨 CRITICAL ISSUES (Fix First!)

### C-001: Duplicate AESEQ 🔴
```python
# ~100 records | 30 min fix
ae['AESEQ'] = ae.groupby('USUBJID').cumcount() + 1
```

### C-002: Fatal/Life-Threatening Not Serious 🔴
```sql
-- 2 records | 15 min fix
UPDATE ae SET AESER='Y' WHERE AESEV IN ('FATAL','LIFE THREATENING');
```

---

## ⚠️ TOP 5 MAJOR FIXES

### 1. AEREL: "UNLIKELY RELATED" → "UNLIKELY"
```sql
-- 18 records | 15 min
UPDATE ae SET AEREL='UNLIKELY' WHERE AEREL='UNLIKELY RELATED';
UPDATE ae SET AEREL='PROBABLE' WHERE AEREL='PROBABLY RELATED';
```

### 2. AEOUT: "RESOLVED" → "RECOVERED/RESOLVED"
```sql
-- 12 records | 15 min
UPDATE ae SET AEOUT='RECOVERED/RESOLVED' WHERE AEOUT='RESOLVED';
```

### 3. Fix ISO 8601 Dates
```python
# 8 records | 15 min
ae['AESTDTC'] = ae['AESTDTC'].str.replace(r'^(\d{4})(\d{2})$', r'\1-\2')
ae['AEENDTC'] = ae['AEENDTC'].str.replace('.0','').str.replace(r'^(\d{4})(\d{2})$', r'\1-\2')
```

### 4. AESDTH Flag for Fatal SAE
```sql
-- 1 record | 5 min
UPDATE ae SET AESDTH='Y' WHERE AETERM='DISEASE PROGRESSION' AND AEOUT='FATAL';
```

### 5. AESLIFE Flag for Life-Threatening SAE
```sql
-- 1 record | 5 min
UPDATE ae SET AESLIFE='Y' WHERE AETERM='HYPERBILIRUBINEMIA' AND AESEV='LIFE THREATENING';
```

---

## 📊 ISSUE BREAKDOWN

```
Total Issues: 47
├─ Critical:  2 🔴 (BLOCKS SUBMISSION)
├─ Major:    15 ⚠️  (FDA REJECTION RISK)
├─ Minor:    22 ⚠️  (QUALITY ISSUES)
└─ Warning:   8 ℹ️  (RECOMMENDATIONS)
```

### By Category
```
Controlled Terminology:  30 issues (64%)
Business Rules:          8 issues (17%)
Date Format:             8 issues (17%)
Completeness:            1 issue (2%)
```

---

## 📅 3-PHASE FIX PLAN

### 📍 PHASE 1 - Day 1 (4 hours)
**Goal:** Fix critical & CT violations  
**Result:** 93% compliance

- [ ] Re-sequence AESEQ (30 min)
- [ ] Update serious flags (15 min)
- [ ] Fix AEREL CT (30 min)
- [ ] Fix AEOUT CT (30 min)
- [ ] Fix date formats (30 min)
- **Owner:** Programming Lead

### 📍 PHASE 2 - Day 2 (3 hours)
**Goal:** Complete SAE data  
**Result:** 96% compliance

- [ ] Set AESDTH='Y' (15 min)
- [ ] Set AESLIFE='Y' (15 min)
- [ ] Populate all SAE flags (2 hrs)
- [ ] Document ongoing SAEs (30 min)
- **Owner:** Clinical DM + Safety

### 📍 PHASE 3 - Day 3 (2 hours)
**Goal:** Final validation  
**Result:** ✅ SUBMISSION READY

- [ ] Re-run validation (1 hr)
- [ ] Cross-domain checks (30 min)
- [ ] Generate Define-XML (30 min)
- [ ] Obtain sign-offs
- **Owner:** QA Team

---

## 👥 WHO DOES WHAT

| Role | Hours | Key Tasks |
|------|-------|-----------|
| 👨‍💻 **Programming Lead** | 4h | Scripts, CT fixes, AESEQ |
| 👨‍⚕️ **Clinical DM** | 3h | SAE review, flags, docs |
| 🏥 **Safety Team** | 2h | SAE flags, criterion |
| ✅ **QA Team** | 2h | Validation, sign-offs |

---

## 📈 PROGRESS TRACKER

### Before Fixes
```
█████░░░░░░░░░░░░░░░ 88% (NOT READY)
Critical: 2  Major: 15  Minor: 22  Warnings: 8
```

### After Phase 1
```
███████████████░░░░░ 93% (IMPROVING)
Critical: 0  Major: 7  Minor: 22  Warnings: 8
```

### After Phase 2
```
█████████████████░░░ 96% (ALMOST READY)
Critical: 0  Major: 2  Minor: 22  Warnings: 8
```

### After Phase 3
```
████████████████████ 96% (READY ✅)
Critical: 0  Major: 2  Minor: 10  Warnings: 3
```

---

## 🎯 SUCCESS CHECKLIST

### Must Have (Blocking)
- [ ] ✅ Zero critical errors
- [ ] ✅ Compliance ≥95%
- [ ] ✅ All SAE flags populated
- [ ] ✅ 100% CT compliance
- [ ] ✅ 100% ISO 8601 dates

### Should Have (Quality)
- [ ] ⭐ Define-XML generated
- [ ] ⭐ Cross-domain validated
- [ ] ⭐ All sign-offs obtained
- [ ] ⭐ Audit trail complete

---

## 🔥 MOST COMMON ISSUES

| Issue | Count | Fix Time | Script? |
|-------|-------|----------|---------|
| UNLIKELY RELATED → UNLIKELY | 18 | 15 min | ✅ Yes |
| PROBABLY RELATED → PROBABLE | 18 | 15 min | ✅ Yes |
| RESOLVED → RECOVERED/RESOLVED | 12 | 15 min | ✅ Yes |
| Duplicate AESEQ | 100 | 30 min | ✅ Yes |
| Missing SAE flags | 7 | 2 hrs | ❌ Manual |

---

## 📞 QUICK CONTACTS

| Issue Type | Contact |
|------------|---------|
| 🔧 **Scripts/Tech** | Programming Lead |
| 🏥 **Clinical/SAE** | Clinical Data Manager |
| ⚖️ **Regulatory** | Regulatory Affairs |
| 📊 **Validation** | QA Manager |

---

## 🚦 STATUS INDICATORS

### Current: 🔴 RED
- Compliance: 88%
- Critical errors: 2
- **Cannot submit**

### Target: 🟢 GREEN
- Compliance: ≥95%
- Critical errors: 0
- **Ready to submit**

---

## 📦 DELIVERABLES

1. ✅ **Executive Summary** - Management overview
2. ✅ **Comprehensive Report** - 35-page technical report
3. ✅ **Issues List CSV** - 47 tracked issues
4. ✅ **Remediation Tracker** - Project management tool
5. ✅ **Python Scripts** - Automated validation

---

## 💡 KEY INSIGHTS

### What's Good ✅
- 100% core field completeness
- 100% date logic (start ≤ end)
- 100% MedDRA coding
- Clean data types

### What Needs Work ⚠️
- Controlled terminology (89%)
- ISO 8601 dates (97%)
- SAE criterion flags (0%)
- Duplicate sequences

### What's Critical 🔴
- AESEQ uniqueness violation
- Fatal/life-threatening not marked serious

---

## ⏱️ TIMELINE

```
Day 1 Morning:   Fix critical issues (2h)
Day 1 Afternoon: Fix CT violations (2h)
Day 2 Morning:   SAE data completion (2h)
Day 2 Afternoon: SAE documentation (1h)
Day 3 Morning:   Final validation (2h)
Day 3 Afternoon: Sign-offs & delivery
```

**Total:** 3 days, ~12 hours effort

---

## 🎓 REMEMBER

1. **Fix duplicates first** - blocks everything else
2. **Use provided scripts** - saves time, reduces errors
3. **Document SAEs carefully** - regulatory scrutiny
4. **Validate after each phase** - catch new issues early
5. **Get all sign-offs** - required for submission

---

## 📱 MOBILE-FRIENDLY SUMMARY

**MAXIS-08 AE Domain**
- 88% compliant (need 95%)
- 2 critical errors ❌
- 3-day fix plan
- ~12 hours work
- Scripts provided ✅

**Top 2 Fixes:**
1. Re-sequence AESEQ
2. Mark fatal/life-threatening as serious

**Contact:** See full package for details

---

**Version:** 1.0 | **Date:** 2026-01-30 | **Status:** Draft

**Full Package:** See `DTA_VALIDATION_PACKAGE_README.md`

---

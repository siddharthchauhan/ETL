# VS Domain Mapping Specification - Complete Package

**Study:** MAXIS-08  
**Domain:** VS (Vital Signs)  
**Source:** VITALS.csv  
**Version:** 1.0  
**Date:** 2026-01-22  
**Status:** Production Ready

---

## 📋 Document Overview

This package contains comprehensive documentation for the SDTM VS (Vital Signs) domain mapping specification. The documentation is organized into multiple files for different audiences and use cases.

---

## 📁 Document Inventory

### 1. VS_MAPPING_SPECIFICATION.md (Main Document)
**Audience:** Data managers, programmers, validators, auditors  
**Length:** ~60 pages  
**Purpose:** Complete technical specification

**Contents:**
- Executive Summary
- Source file structure (VITALS.csv)
- Target SDTM VS structure (28 variables)
- Comprehensive variable-by-variable mappings
- Vital sign test mappings (7 tests)
- Derivation rules with algorithms
- Controlled terminology codelists
- Data quality validation rules
- Business rules and assumptions
- Detailed transformation examples
- SQL query examples
- Appendices and references

**When to use:**
- Implementing the transformation
- Validating SDTM data
- Auditing compliance
- Understanding complex derivations
- Regulatory submission preparation

---

### 2. VS_MAPPING_SUMMARY.md (Quick Reference)
**Audience:** Project managers, quick lookup, daily reference  
**Length:** ~8 pages  
**Purpose:** Quick reference guide

**Contents:**
- Transformation overview (metrics)
- Quick mapping reference tables
- Core identifier mappings
- Vital sign test mappings
- Key transformation rules (5 rules)
- Data quality checks summary
- Controlled terminology values
- Example transformation
- SQL query snippets
- File locations

**When to use:**
- Quick lookups during programming
- Daily reference while working
- Team meetings and discussions
- Initial understanding of transformation
- Finding specific mappings quickly

---

### 3. VS_MAPPING_VISUAL.md (Visual Guide)
**Audience:** Visual learners, training, presentations  
**Length:** ~15 pages  
**Purpose:** Visual representation of mappings

**Contents:**
- Data flow diagrams
- Record expansion visualization (wide→long)
- Source-to-target mapping flows
- USUBJID construction diagram
- VSSEQ generation logic
- Unit conversion examples
- Date/time formatting scenarios
- Data quality check flow
- Blood pressure consistency checks
- Transformation pipeline flowchart
- Record count verification

**When to use:**
- Training new team members
- Presentations to stakeholders
- Understanding data flow
- Explaining transformations visually
- Troubleshooting issues

---

### 4. VS_MAPPING_INDEX.md (This Document)
**Audience:** All users  
**Length:** 2-3 pages  
**Purpose:** Navigation and overview

**Contents:**
- Document inventory
- How to use each document
- Quick start guide
- Common scenarios
- Support resources

**When to use:**
- First time accessing documentation
- Deciding which document to read
- Finding specific information
- Understanding document structure

---

## 🚀 Quick Start Guide

### Scenario 1: I Need to Implement the VS Transformation
**Path:**
1. Start with **VS_MAPPING_SUMMARY.md** (overview)
2. Review **VS_MAPPING_VISUAL.md** (understand flow)
3. Reference **VS_MAPPING_SPECIFICATION.md** (detailed implementation)
4. Check existing code: `domain_transformers.py` (VSTransformer class)

### Scenario 2: I Need to Understand a Specific Variable
**Path:**
1. Open **VS_MAPPING_SUMMARY.md** → Quick Mapping Reference
2. If more detail needed → **VS_MAPPING_SPECIFICATION.md** → Section 3 (Variable Mappings)

### Scenario 3: I Need to Validate VS Data
**Path:**
1. **VS_MAPPING_SPECIFICATION.md** → Section 7 (Data Quality Rules)
2. Review Section 8 (Business Rules)
3. Use SQL queries from Section 10

### Scenario 4: I Need to Explain the Mapping to Someone
**Path:**
1. Use **VS_MAPPING_VISUAL.md** (diagrams)
2. Reference **VS_MAPPING_SUMMARY.md** (quick examples)
3. Show example from Section 9 of **VS_MAPPING_SPECIFICATION.md**

### Scenario 5: I Found a Data Issue
**Path:**
1. **VS_MAPPING_SPECIFICATION.md** → Section 9 (Examples)
2. Check Section 7 (Data Quality Rules)
3. Review Section 8 (Business Rules & Assumptions)
4. Cross-reference with source data using Visual Guide

---

## 📊 Transformation Quick Facts

```
Source:        VITALS.csv (536 records)
               Wide format, 21 columns

Transform:     Wide → Long conversion
               7 vital signs per record
               Unit standardization
               ISO 8601 date formatting

Target:        vs.csv (2,184 records)
               Long format, 28 variables
               SDTM-IG 3.4 compliant
               
Expansion:     4.07:1 ratio
               
Tests:         SYSBP, DIABP, PULSE, RESP, 
               TEMP, WEIGHT, HEIGHT
               
Compliance:    ✓ 6/6 Required variables
               ✓ 12/12 Expected variables
               ✓ 10 Permissible variables
               ✓ Controlled terminology
               ✓ Standard units
```

---

## 🗺️ Document Navigation Map

```
START HERE → VS_MAPPING_INDEX.md (You are here!)
    │
    ├─► Need Overview? → VS_MAPPING_SUMMARY.md
    │
    ├─► Need Visual Understanding? → VS_MAPPING_VISUAL.md
    │
    └─► Need Complete Details? → VS_MAPPING_SPECIFICATION.md
            │
            ├─► Variable Mappings → Section 3
            ├─► Test Mappings → Section 4
            ├─► Derivation Rules → Section 5
            ├─► Controlled Terminology → Section 6
            ├─► Quality Rules → Section 7
            ├─► Business Rules → Section 8
            └─► Examples → Section 9
```

---

## 🔍 Finding Specific Information

| What You Need | Where to Find It |
|---------------|------------------|
| **Quick mapping table** | VS_MAPPING_SUMMARY.md → Quick Mapping Reference |
| **USUBJID construction** | VS_MAPPING_VISUAL.md → Section 4 (diagram)<br>VS_MAPPING_SPECIFICATION.md → Section 5.1 |
| **Unit conversions** | VS_MAPPING_VISUAL.md → Section 6<br>VS_MAPPING_SPECIFICATION.md → Section 5.4 |
| **VSSEQ logic** | VS_MAPPING_VISUAL.md → Section 5<br>VS_MAPPING_SPECIFICATION.md → Section 5.2 |
| **Date formatting** | VS_MAPPING_VISUAL.md → Section 7<br>VS_MAPPING_SPECIFICATION.md → Section 5.3 |
| **Test code mappings** | VS_MAPPING_SUMMARY.md → Vital Sign Test Mappings<br>VS_MAPPING_SPECIFICATION.md → Section 4 |
| **Validation rules** | VS_MAPPING_SPECIFICATION.md → Section 7 |
| **Controlled terminology** | VS_MAPPING_SUMMARY.md → Controlled Terminology<br>VS_MAPPING_SPECIFICATION.md → Section 6 |
| **Examples** | VS_MAPPING_SUMMARY.md → Example Transformation<br>VS_MAPPING_SPECIFICATION.md → Section 9 |
| **SQL queries** | VS_MAPPING_SUMMARY.md → SQL Query Examples<br>VS_MAPPING_SPECIFICATION.md → Section 10 |
| **Data flow** | VS_MAPPING_VISUAL.md → Sections 1-3 |
| **Assumptions** | VS_MAPPING_SPECIFICATION.md → Section 8 |
| **Source file structure** | VS_MAPPING_SPECIFICATION.md → Section 1 |
| **Target file structure** | VS_MAPPING_SPECIFICATION.md → Section 2 |

---

## 💡 Tips for Using This Documentation

### For Programmers
1. Start with VS_MAPPING_SUMMARY.md to understand the overall approach
2. Use VS_MAPPING_VISUAL.md to understand data flows
3. Reference VS_MAPPING_SPECIFICATION.md for exact implementation details
4. Check the existing code in `domain_transformers.py` (VSTransformer class)
5. Use SQL queries from Section 10 for validation

### For Validators
1. Review VS_MAPPING_SPECIFICATION.md Section 7 (Data Quality Rules)
2. Use SQL queries from Section 10 for systematic checks
3. Reference Section 8 (Business Rules) for edge cases
4. Check Section 6 (Controlled Terminology) for valid values

### For Project Managers
1. Use VS_MAPPING_SUMMARY.md for status updates
2. Reference transformation metrics (536 → 2,184 records)
3. Check compliance status (all required/expected variables populated)
4. Use VS_MAPPING_VISUAL.md for presentations

### For Training
1. Present VS_MAPPING_VISUAL.md first (visual understanding)
2. Walk through VS_MAPPING_SUMMARY.md (quick reference)
3. Deep dive into specific sections of VS_MAPPING_SPECIFICATION.md as needed
4. Show practical examples from Section 9

---

## 📂 Related Files and Resources

### Transformation Code
```
Location: /sdtm_pipeline/transformers/domain_transformers.py
Class: VSTransformer
Methods: transform(), _generate_usubjid(), _convert_date_to_iso()
```

### Source Data
```
Location: EDC Data/VITALS.csv
Records: 536
Format: Wide (multiple vitals per row)
```

### Target Data
```
Location: sdtm_data/vs.csv
Records: 2,184
Format: Long (one vital per row)
Columns: 28 SDTM variables
```

### Mapping Specification (JSON)
```
Location: mapping_specs/VS_mapping.json
Format: JSON
Purpose: Machine-readable mapping rules
```

### Generated Programs
```
R Program: r_programs/vs.R
SAS Program: sas_programs/vs.sas
Python: domain_transformers.py (VSTransformer)
```

### Validation Reports
```
Raw Data: raw_validation/validation_report.json
SDTM Data: sdtm_validation/vs_validation_report.json
```

---

## ✅ Document Checklist

Use this checklist to ensure you've reviewed all necessary documentation:

**Initial Understanding:**
- [ ] Read VS_MAPPING_INDEX.md (this document)
- [ ] Review VS_MAPPING_SUMMARY.md for overview
- [ ] Study VS_MAPPING_VISUAL.md for data flow

**Implementation:**
- [ ] Review all variable mappings (Specification Section 3)
- [ ] Understand test mappings (Specification Section 4)
- [ ] Learn derivation rules (Specification Section 5)
- [ ] Check controlled terminology (Specification Section 6)

**Quality & Validation:**
- [ ] Review data quality rules (Specification Section 7)
- [ ] Understand business rules (Specification Section 8)
- [ ] Study examples (Specification Section 9)
- [ ] Test SQL queries (Specification Section 10)

**Compliance:**
- [ ] Verify all required variables mapped
- [ ] Confirm controlled terminology usage
- [ ] Check SDTM-IG 3.4 compliance
- [ ] Review regulatory considerations

---

## 🆘 Support and Questions

### For Technical Questions
- Review the appropriate section in VS_MAPPING_SPECIFICATION.md
- Check the visual diagram in VS_MAPPING_VISUAL.md
- Reference the transformation code in `domain_transformers.py`

### For Data Issues
- Check VS_MAPPING_SPECIFICATION.md Section 7 (Data Quality Rules)
- Review Section 8 (Business Rules & Assumptions)
- Cross-reference with examples in Section 9

### For Validation Issues
- Run SQL queries from VS_MAPPING_SPECIFICATION.md Section 10
- Review data quality rules in Section 7
- Check controlled terminology in Section 6

### For Clarifications
- Consult the detailed specification (VS_MAPPING_SPECIFICATION.md)
- Review assumptions in Section 8
- Check examples in Section 9

---

## 📝 Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-22 | SDTM Pipeline | Initial creation of complete documentation package |

---

## 📌 Key Takeaways

1. **Three-Document System**: Specification (complete), Summary (quick reference), Visual (diagrams)

2. **Transformation Type**: Wide-to-long conversion (1 source record → 6+ target records)

3. **Core Logic**: Each vital sign measurement becomes a separate VS record

4. **Critical Derivations**: USUBJID, VSSEQ, VSDTC, VSSTRESN

5. **Compliance**: Full SDTM-IG 3.4 compliance with all required and expected variables

6. **Quality**: Comprehensive validation rules and data quality checks

7. **Traceability**: Clear audit trail from source to target with documented assumptions

---

## 🎯 Success Criteria

Your implementation is successful when:

✅ All 536 source records are processed  
✅ 2,184 VS records are created (or appropriate count)  
✅ All 6 required variables are populated  
✅ All 12 expected variables are included  
✅ Controlled terminology is correctly applied  
✅ Standard units are used (mmHg, C, kg, cm, etc.)  
✅ ISO 8601 date format is enforced  
✅ USUBJID is correctly constructed  
✅ VSSEQ is sequential within subjects  
✅ Data quality checks all pass  
✅ No validation errors in Pinnacle 21  

---

**Navigation:**
- 📖 Full Specification → [VS_MAPPING_SPECIFICATION.md](VS_MAPPING_SPECIFICATION.md)
- ⚡ Quick Reference → [VS_MAPPING_SUMMARY.md](VS_MAPPING_SUMMARY.md)
- 📊 Visual Guide → [VS_MAPPING_VISUAL.md](VS_MAPPING_VISUAL.md)

---

**End of Index**

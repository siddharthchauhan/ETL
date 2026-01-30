# MAXIS-08 DM Mapping Specification - Complete Documentation Package

---

## 📦 Package Contents

This package contains comprehensive SDTM DM (Demographics) mapping specification and supporting documentation for the **MAXIS-08** clinical study.

### Generated Files (5 Documents)

| # | Document | File Type | Purpose | Audience |
|---|----------|-----------|---------|----------|
| 1 | **Mapping Specification** | JSON | Machine-readable transformation rules | Programmers, ETL Systems |
| 2 | **Mapping Summary** | Markdown | Detailed implementation guide | All stakeholders |
| 3 | **Quick Reference** | Markdown | Fast lookup for programmers | Programmers, Data Managers |
| 4 | **Data Availability Matrix** | Text | Visual status of all variables | Project Managers, Leadership |
| 5 | **Data Quality Report** | Markdown | Critical HISPANIC race issue | Clinical DM, QC Team |

---

## 📄 Document Descriptions

### 1. MAXIS-08_DM_Mapping_Specification.json
**Comprehensive JSON Mapping Specification**

- **Format**: JSON (machine-readable)
- **Size**: ~30 KB
- **Purpose**: Complete transformation specification with all rules, mappings, and metadata
- **Use Cases**:
  - Input for automated transformation engines
  - API integration with ETL pipelines
  - Version control and change tracking
  - Audit trail for regulatory submissions

**Contents**:
- ✅ All 29 DM variables with transformation rules
- ✅ Source-to-target mappings with examples
- ✅ CDISC Controlled Terminology mappings
- ✅ Derivation algorithms and formulas
- ✅ Data quality notes and validation rules
- ✅ Dependency tracking (other domains required)
- ✅ Implementation notes and phasing

**Who Should Use This**:
- SDTM programmers implementing transformations
- ETL tool administrators
- QC reviewers verifying mapping logic
- Regulatory reviewers during audits

---

### 2. MAXIS-08_DM_Mapping_Summary.md
**Human-Readable Comprehensive Guide (25+ pages)**

- **Format**: Markdown (renders beautifully on GitHub/GitLab)
- **Size**: ~50 KB
- **Purpose**: Complete reference manual for DM domain transformation
- **Use Cases**:
  - Onboarding new team members
  - Understanding transformation logic
  - Implementation planning
  - Regulatory documentation

**Contents**:
- 📊 Executive summary with status overview
- 🗂️ Source data profile and column inventory
- 🎯 Target SDTM DM structure (29 variables)
- ✅ Phase 1: Immediate mappings (available now)
- ⚠️ Phase 2: Variables requiring integration
- 🔴 Critical issue: HISPANIC race mapping
- 🧮 Calculated variables (AGE, DMDY, AGEGR1)
- 📝 Transformation DSL function reference
- 🚀 8-step implementation roadmap
- ✔️ Validation rules and checklists
- 💻 Python and SAS code examples
- 📋 Testing & validation procedures
- 📚 Complete variable reference table
- 🔤 CDISC CT quick reference

**Who Should Use This**:
- SDTM programmers (primary reference)
- Clinical data managers
- Study managers
- QC reviewers
- Regulatory affairs team
- New team members learning SDTM

---

### 3. MAXIS-08_DM_Quick_Reference.md
**Programmer's Cheat Sheet (Fast Lookup)**

- **Format**: Markdown
- **Size**: ~15 KB
- **Purpose**: Quick lookup for common tasks and mappings
- **Use Cases**:
  - Daily programming reference
  - Quick problem solving
  - Code snippet library
  - Validation quick checks

**Contents**:
- 🎯 "3 Things You Need to Know" summary
- ✅ Variables mappable RIGHT NOW (8 vars)
- 🔴 Critical blockers (ARMCD/ARM, HISPANIC)
- ⚠️ Variables requiring other domains
- 🧮 Calculated variables with formulas
- 📋 Race/ethnicity mapping cheat sheet
- 💡 Pro tips and best practices
- 🆘 Common errors and fixes
- ✔️ Validation quick checks (Python/SAS)
- 🚀 Implementation workflow (7 days)
- 📞 Who to contact for what

**Who Should Use This**:
- Programmers during active development
- Data managers needing quick answers
- QC reviewers during validation
- Anyone needing quick reference

---

### 4. MAXIS-08_DM_Data_Availability_Matrix.txt
**Visual Status Dashboard (ASCII Art)**

- **Format**: Plain Text (ASCII tables)
- **Size**: ~20 KB
- **Purpose**: At-a-glance status of all variables
- **Use Cases**:
  - Project status meetings
  - Management reporting
  - Gap analysis
  - Resource planning

**Contents**:
- 📊 Complete variable inventory (29 vars)
- 🎨 Color-coded status (✅🟢⚠️🔴🟡)
- 📈 Summary statistics (completion %)
- 🔴 Critical blockers highlighted
- 🟡 Data quality issues flagged
- 📅 Phased implementation plan
- 📋 Data sources needed
- ⏱️ Estimated timeline (7 days)
- 📞 Contact information
- ✔️ Validation requirements

**Visual Elements**:
- Beautiful ASCII table formatting
- Progress bars and percentages
- Risk assessment matrix
- Transformation complexity breakdown

**Who Should Use This**:
- Project managers
- Study directors
- Management/leadership
- Clinical operations
- Anyone needing high-level overview

---

### 5. MAXIS-08_DM_Data_Quality_Report_HISPANIC_Issue.md
**Critical Data Quality Issue Report**

- **Format**: Markdown
- **Size**: ~18 KB
- **Priority**: HIGH
- **Purpose**: Document and resolve HISPANIC race classification issue
- **Use Cases**:
  - Issue tracking and resolution
  - Site query generation
  - Regulatory justification
  - Process improvement

**Contents**:
- 🚨 Executive summary (critical issue)
- 📝 Detailed issue description
- 📊 Impact assessment (regulatory/data/timeline)
- 🔍 Root cause analysis
- ✅ 3 resolution options (recommended: Option 1)
- 📋 Action plan (immediate, short-term, long-term)
- 📄 DCF template for sites
- 📧 Email templates for queries
- ✔️ Validation after resolution
- 📞 Communication plan
- 🛡️ Risk mitigation strategies
- 📚 Appendices (CDISC standards, FDA guidance, mapping logic)

**Who Should Use This**:
- Clinical data managers (primary audience)
- Site coordinators
- Medical monitors
- QC reviewers
- Regulatory affairs
- Study management

---

## 🚀 Quick Start Guide

### For Programmers
**"I need to start coding NOW"**

1. Read: **Quick Reference** (15 min)
2. Scan: **Data Availability Matrix** (5 min)
3. Code: Use **Mapping Specification JSON** (automation)
4. Reference: **Mapping Summary** (as needed)

---

### For Clinical Data Managers
**"I need to resolve data issues"**

1. Read: **Data Quality Report** (20 min)
2. Generate: Subject list with HISPANIC race
3. Issue: DCFs to sites (use provided template)
4. Track: Query responses
5. Update: Mapping specification once resolved

---

### For Project Managers
**"I need to report status"**

1. Open: **Data Availability Matrix** (quick overview)
2. Key Metrics:
   - 40% complete (8/29 variables from DEMO.csv)
   - 2 critical blockers (ARMCD/ARM, HISPANIC)
   - 7-day timeline (includes 2-3 days external data)
3. Share: Matrix with leadership
4. Track: Critical blockers in project plan

---

### For Study Managers
**"I need the big picture"**

1. Read: **Mapping Summary Executive Summary** (10 min)
2. Review: **Data Quality Report** (understand HISPANIC issue)
3. Check: **Data Availability Matrix** for dependencies
4. Action: Facilitate data requests to clinical ops

---

### For QC Reviewers
**"I need to validate the work"**

1. Reference: **Mapping Specification** (source of truth)
2. Use: **Quick Reference** validation checks
3. Run: Pinnacle 21 validation
4. Verify: All items in **Mapping Summary** validation checklist

---

## 📋 Implementation Checklist

### Phase 1: Initial Setup (Day 1)
- [ ] Read all documentation (1-2 hours)
- [ ] Set up development environment
- [ ] Load DEMO.csv source data
- [ ] Implement 8 immediate mappings
- [ ] Generate dm_phase1.csv (partial)
- [ ] Run initial validation checks

### Phase 2: Issue Resolution (Day 2-3)
- [ ] Generate HISPANIC subject list
- [ ] Create and send DCFs to sites
- [ ] Request randomization data from clinical ops
- [ ] Request site metadata file
- [ ] Track query responses

### Phase 3: Data Integration (Day 4-5)
- [ ] Receive and load SV domain (visit dates)
- [ ] Receive and load EX domain (exposure dates)
- [ ] Receive and load DS domain (disposition)
- [ ] Receive randomization data
- [ ] Update RFSTDTC, RFENDTC
- [ ] Populate ARMCD, ARM

### Phase 4: Calculations (Day 5-6)
- [ ] Calculate AGE using RFSTDTC
- [ ] Derive AGEGR1 from AGE
- [ ] Calculate DMDY using DMDTC and RFSTDTC
- [ ] Validate all date logic

### Phase 5: Final QC (Day 6-7)
- [ ] Complete all 29 variable mappings
- [ ] Run Pinnacle 21 validation
- [ ] Fix any critical errors
- [ ] Verify USUBJID uniqueness
- [ ] Check one-record-per-subject
- [ ] Validate ISO 8601 date formats
- [ ] Verify CT compliance
- [ ] Generate final dm.xpt

### Phase 6: Documentation (Day 7)
- [ ] Document any deviations
- [ ] Update mapping spec if changed
- [ ] Create validation report
- [ ] Archive source data and code
- [ ] Deliver dm.xpt to submission folder

---

## 🔧 Technical Requirements

### Software Requirements
- **Python** 3.8+ (with pandas, numpy, datetime) OR
- **SAS** 9.4+ OR
- **R** 4.0+ (with dplyr, lubridate)
- **Validation Tools**: Pinnacle 21 Community 4.0+
- **Excel/CSV Reader**: For source data loading

### Input Files Required
1. ✅ **DEMO.csv** (available now)
2. ⚠️ **Randomization dataset** (need to request)
3. ⚠️ **SV domain** or visit tracking data (need to create)
4. ⚠️ **EX domain** or exposure data (need to create)
5. ⚠️ **DS domain** or disposition data (need to create)
6. ⚠️ **Site metadata file** (need to request)

### Output Files
- **dm.xpt** (SAS V5 XPORT for submission)
- **dm.csv** (for internal use/QC)
- **dm_validation_report.pdf** (Pinnacle 21 output)
- **define.xml** (metadata for submission)

---

## ⚠️ Critical Dependencies

### External Data Required (BLOCKERS)

| Data Source | Variables Enabled | Priority | Contact |
|-------------|------------------|----------|---------|
| **Randomization** | ARMCD, ARM | 🔴 CRITICAL | Clinical Ops |
| **Visit Data (SV)** | RFSTDTC, RFENDTC, AGE | 🟠 HIGH | Visit Tracking |
| **Exposure (EX)** | RFXSTDTC, RFXENDTC | 🟠 HIGH | Drug Accountability |
| **Disposition (DS)** | RFICDTC, RFPENDTC | 🟡 MEDIUM | EDC Team |
| **Site Metadata** | COUNTRY, INVID | 🟡 MEDIUM | Site Mgmt |

### Data Quality Issues (Must Resolve)

| Issue | Impact | Priority | Resolution Time |
|-------|--------|----------|-----------------|
| **HISPANIC in RACE** | Blocks compliant DM | 🔴 HIGH | 2-3 days |
| Missing ARMCD/ARM | Blocks Required vars | 🔴 CRITICAL | 1-2 days |
| Missing RFSTDTC | Blocks AGE calculation | 🟠 HIGH | 3-5 days |

---

## 📊 Success Metrics

### Completion Criteria
- [x] All 5 specification documents created
- [ ] All Required variables (8) populated
- [ ] All Expected variables (13) populated where applicable
- [ ] Zero Pinnacle 21 critical errors
- [ ] Define-XML validates successfully
- [ ] QC review passed
- [ ] Final dm.xpt delivered

### Quality Gates
✅ **Gate 1**: Specification complete and reviewed  
⏳ **Gate 2**: Phase 1 mappings implemented (pending)  
⏳ **Gate 3**: HISPANIC issue resolved (pending)  
⏳ **Gate 4**: All external data received (pending)  
⏳ **Gate 5**: QC validation passed (pending)  
⏳ **Gate 6**: Final delivery (pending)  

---

## 📞 Support & Contact

### For Questions About...

| Topic | Contact | Method |
|-------|---------|--------|
| Specification content | SDTM Lead Programmer | Email/Teams |
| Missing data | Clinical Data Manager | Email |
| HISPANIC issue | Clinical DM + Medical Monitor | Email + DCF |
| Randomization | Clinical Operations | Email/Phone |
| Timeline/priorities | Study Manager | Meeting |
| Validation errors | QC Lead | Teams/Email |

---

## 📚 Additional Resources

### CDISC Resources
- SDTM Implementation Guide 3.4: https://www.cdisc.org/standards/foundational/sdtm
- CDISC Controlled Terminology: https://evs.nci.nih.gov/ftp1/CDISC/
- SDTM Conformance Rules: https://www.cdisc.org/standards/foundational/sdtm/sdtmig-v3-4

### FDA Resources
- FDA Study Data Standards: https://www.fda.gov/industry/fda-data-standards-advisory-board/study-data-standards-resources
- FDA Technical Conformance Guide: https://www.fda.gov/regulatory-information/search-fda-guidance-documents

### Tools
- Pinnacle 21 Community: https://www.pinnacle21.com/products/pinnacle-21-community
- SAS Clinical Standards Toolkit: https://www.sas.com/en_us/software/clinical-standards-toolkit.html

---

## 📝 Document Versions

| Document | Version | Date | Status |
|----------|---------|------|--------|
| Mapping Specification (JSON) | 1.0 | 2024-01-15 | ✅ Final |
| Mapping Summary (MD) | 1.0 | 2024-01-15 | ✅ Final |
| Quick Reference (MD) | 1.0 | 2024-01-15 | ✅ Final |
| Data Availability Matrix (TXT) | 1.0 | 2024-01-15 | ✅ Final |
| Data Quality Report (MD) | 1.0 | 2024-01-15 | ✅ Final |

**Next Review**: After Phase 1 completion or upon receipt of external data

---

## 🎯 Expected Outcomes

### After Using This Package

**Programmers** will:
- ✅ Understand exactly what to map and how
- ✅ Have working code examples (Python/SAS)
- ✅ Know which data is available vs. needed
- ✅ Implement transformations efficiently

**Clinical Teams** will:
- ✅ Understand the HISPANIC data quality issue
- ✅ Have templates to query sites
- ✅ Know what data is needed and when
- ✅ Track resolution of critical issues

**Project Managers** will:
- ✅ Have clear status of DM domain completion
- ✅ Understand critical blockers
- ✅ Know realistic timeline (7 days)
- ✅ Track dependencies on other teams

**QC Reviewers** will:
- ✅ Have source of truth for validation
- ✅ Know validation criteria
- ✅ Have SQL/code for validation checks
- ✅ Verify regulatory compliance

---

## ⏱️ Estimated Timeline Summary

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Documentation review | 2 hours | None |
| Phase 1 mappings | 2 hours | DEMO.csv only |
| Issue resolution | 2-3 days | Clinical team, sites |
| Data integration | 4 hours | SV, EX, DS domains |
| Final calculations | 2 hours | RFSTDTC available |
| QC & validation | 4 hours | Complete dataset |
| **TOTAL** | **7 days** | **External data on Day 3** |

*Actual programming: 14 hours  
*Waiting for external data: 2-3 days

---

## 🎓 Training & Onboarding

### New Team Members
**Day 1 Onboarding**:
1. Read this README (15 min)
2. Read Quick Reference (30 min)
3. Scan Mapping Summary Executive Summary (15 min)
4. Review Data Availability Matrix (10 min)
5. Total: 70 minutes to understand project

### Knowledge Transfer
All documents designed for:
- ✅ Self-service learning
- ✅ Minimal training required
- ✅ Progressive disclosure (start simple, dig deeper as needed)
- ✅ Multiple formats (JSON, Markdown, Text) for different tools

---

## 🔐 Document Control

**Package Version**: 1.0  
**Created**: 2024-01-15  
**Study**: MAXIS-08  
**Domain**: DM (Demographics)  
**SDTM Version**: 3.4  
**Author**: SDTM Mapping Specification Expert  

**Change Log**:
- 2024-01-15: Initial package creation (v1.0)

**Review Schedule**:
- After Phase 1 completion
- Upon receipt of external data
- After HISPANIC issue resolution
- Before final submission

---

## ✅ Package Validation

This package has been verified to include:
- ✅ Machine-readable specification (JSON)
- ✅ Human-readable guide (Markdown)
- ✅ Quick reference card (Markdown)
- ✅ Visual status dashboard (Text)
- ✅ Data quality report (Markdown)
- ✅ Code examples (Python, SAS)
- ✅ Validation queries (SQL, Python, SAS)
- ✅ Email templates
- ✅ DCF templates
- ✅ CDISC CT references
- ✅ FDA guidance citations
- ✅ Complete variable reference
- ✅ Implementation roadmap
- ✅ Timeline estimates
- ✅ Contact information

**Package Status**: ✅ **COMPLETE AND READY FOR USE**

---

## 🚀 Next Steps

1. **Review** this README completely (you are here!)
2. **Choose** your role's Quick Start path (see above)
3. **Read** the relevant documents for your role
4. **Begin** Phase 1 implementation
5. **Track** progress using Data Availability Matrix
6. **Resolve** critical blockers (ARMCD/ARM, HISPANIC)
7. **Complete** remaining phases
8. **Validate** using QC checklists
9. **Deliver** final dm.xpt

---

**Questions?** Contact the SDTM programming team or your study manager.

**Ready to begin?** Start with the Quick Reference for your role!

---

**END OF README**

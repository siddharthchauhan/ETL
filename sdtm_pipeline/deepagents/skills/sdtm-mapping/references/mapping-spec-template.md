# SDTM Mapping Specification Template

## Domain: [XX]

### Dataset Information

| Attribute | Value |
|-----------|-------|
| Dataset Name | [XX] |
| Dataset Label | [Full Domain Name] |
| Class | [Findings/Events/Interventions/Special Purpose] |
| Structure | One record per [description] |
| Sort Order | STUDYID, USUBJID, [additional keys] |
| Source Datasets | [List raw datasets] |

---

### Variable Mapping

| # | Variable | Label | Type | Length | Required | CT Codelist | Source | Derivation Rule |
|---|----------|-------|------|--------|----------|-------------|--------|-----------------|
| 1 | STUDYID | Study Identifier | Char | 20 | Req | - | Constant | "STUDY001" |
| 2 | DOMAIN | Domain Abbreviation | Char | 2 | Req | - | Constant | "XX" |
| 3 | USUBJID | Unique Subject ID | Char | 40 | Req | - | Derived | STUDYID \|\| "-" \|\| SITEID \|\| "-" \|\| SUBJID |
| 4 | [XXSEQ] | Sequence Number | Num | 8 | Req | - | Derived | Sequential within USUBJID |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |

---

### Selection Criteria
```
Include records where:
  - [Condition 1]
  - [Condition 2]
  
Exclude records where:
  - [Condition 1]
```

---

### Derivation Details

#### Variable: [VARIABLE NAME]

**Rule:** [Brief description]

**Algorithm:**
```
IF condition1 THEN
  variable = value1
ELSE IF condition2 THEN
  variable = value2
ELSE
  variable = value3
END IF
```

**Source Variables:**
- RAW.FIELD1
- RAW.FIELD2

**Controlled Terminology:**
- Source Value → CDISC CT Value

| Source | Target |
|--------|--------|
| "Mild" | "MILD" |
| "Moderate" | "MODERATE" |
| "Severe" | "SEVERE" |

---

### Controlled Terminology Mapping

| Variable | CT Codelist | Non-Standard Terms |
|----------|-------------|--------------------|
| XXSEV | AESEV | None |
| XXROUTE | ROUTE | "By mouth" → "ORAL" |

---

### SUPPXX Variables

| QNAM | QLABEL | Source | Derivation |
|------|--------|--------|------------|
| XXABC | [Label] | RAW.FIELD | Direct map |

---

### Comments/Assumptions

1. [Assumption 1]
2. [Assumption 2]
3. [Known issue or limitation]

---

### Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | YYYY-MM-DD | [Name] | Initial version |
| 1.1 | YYYY-MM-DD | [Name] | [Change description] |
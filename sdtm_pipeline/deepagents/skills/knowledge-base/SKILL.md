---
name: knowledge-base
description: Use this skill for searching the SDTM knowledge base (Pinecone), retrieving CDISC guidance, validation rules, business rules, controlled terminology, and performing web-based lookups from authoritative CDISC sources. Essential for accurate mapping decisions and compliance verification.
---

# Knowledge Base and Reference Lookup Skill

## Overview

This skill provides expertise in querying the SDTM knowledge base powered by Pinecone vector search, retrieving guidance from authoritative CDISC sources, and performing web-based lookups for the latest specifications and controlled terminology.

## Knowledge Base Architecture

### Pinecone Indexes

The knowledge base consists of multiple specialized indexes:

| Index | Content | Use Case |
|-------|---------|----------|
| `sdtm-guidelines` | SDTM-IG specifications, domain structures | Domain structure questions |
| `business-rules` | Transformation business rules | Mapping logic |
| `validation-rules` | Pinnacle 21 / FDA validation rules | Compliance checks |
| `controlled-terminology` | CDISC CT codelists | Value standardization |
| `mapping-specs` | Historical mapping specifications | Pattern matching |

### Embedding Model

Documents are embedded using OpenAI's text-embedding-ada-002 model for semantic similarity search.

## Core Competencies

### 1. SDTM Guidance Lookup

**When to use**: Understanding how to generate SDTM datasets, domain requirements, variable definitions.

#### Tool: `get_sdtm_guidance`

```python
# Get guidance for a specific domain
result = await get_sdtm_guidance(
    domain="AE",
    query="What are the required variables for adverse events?"
)

# Returns:
# {
#     "domain": "AE",
#     "guidance": "The AE domain requires the following core variables:\n- STUDYID (Req)\n- DOMAIN (Req)\n- USUBJID (Req)\n- AESEQ (Req)\n- AETERM (Req)...",
#     "sources": ["SDTM-IG 3.4 Section 6.2.1", "FDA SDTM Technical Conformance Guide"],
#     "confidence": 0.95
# }
```

#### Common Queries

| Query Type | Example |
|------------|---------|
| Variable requirements | "What variables are required in DM?" |
| Domain purpose | "What is the purpose of the FA domain?" |
| Variable definition | "What is the definition of AEDECOD?" |
| Class structure | "What domains are in the Findings class?" |

### 2. Mapping Specification Lookup

**When to use**: Finding existing mappings for source-to-target variable conversions.

#### Tool: `get_mapping_specification`

```python
# Get mapping guidance for a source column
result = await get_mapping_specification(
    source_column="ADVERSE_EVENT_TERM",
    target_domain="AE"
)

# Returns:
# {
#     "source_column": "ADVERSE_EVENT_TERM",
#     "target_domain": "AE",
#     "recommended_target": "AETERM",
#     "transformation": "UPCASE(ADVERSE_EVENT_TERM)",
#     "confidence": 0.92,
#     "similar_mappings": [
#         {"source": "AE_TERM", "target": "AETERM", "study": "STUDY-001"},
#         {"source": "VERBATIM_TERM", "target": "AETERM", "study": "STUDY-002"}
#     ]
# }
```

### 3. Validation Rules Lookup

**When to use**: Understanding what validation rules apply to a domain or variable.

#### Tool: `get_validation_rules`

```python
# Get validation rules for a domain
result = await get_validation_rules(
    domain="DM",
    severity="ERROR"  # Optional: filter by severity
)

# Returns:
# {
#     "domain": "DM",
#     "rules": [
#         {
#             "rule_id": "SD1001",
#             "severity": "ERROR",
#             "description": "STUDYID value is empty",
#             "check": "STUDYID is not null and not empty"
#         },
#         {
#             "rule_id": "SD1003",
#             "severity": "ERROR",
#             "description": "USUBJID must be unique within study",
#             "check": "count(distinct USUBJID) = count(*)"
#         },
#         ...
#     ],
#     "total_rules": 25
# }
```

### 4. Business Rules Lookup

**When to use**: Understanding domain-specific business logic for transformations.

#### Tool: `get_business_rules`

```python
# Get business rules for a domain
result = await get_business_rules(domain="VS")

# Returns:
# {
#     "domain": "VS",
#     "rules": [
#         {
#             "rule_id": "VS-BR-001",
#             "description": "VSTESTCD must use standardized test codes",
#             "logic": "VSTESTCD in ('SYSBP', 'DIABP', 'PULSE', 'TEMP', 'WEIGHT', 'HEIGHT', 'BMI')"
#         },
#         {
#             "rule_id": "VS-BR-002",
#             "description": "VSORRES numeric values should have units",
#             "logic": "If VSORRES is numeric, VSORRESU must not be null"
#         },
#         ...
#     ]
# }
```

### 5. Controlled Terminology Lookup

**When to use**: Finding valid values for CDISC controlled terminology codelists.

#### Tool: `get_controlled_terminology`

```python
# Get CT values for a codelist
result = await get_controlled_terminology(codelist="AESEV")

# Returns:
# {
#     "codelist": "AESEV",
#     "codelist_name": "Severity/Intensity Scale for Adverse Events",
#     "values": [
#         {"code": "MILD", "decode": "Mild", "definition": "..."},
#         {"code": "MODERATE", "decode": "Moderate", "definition": "..."},
#         {"code": "SEVERE", "decode": "Severe", "definition": "..."}
#     ],
#     "version": "2024-03-29"
# }
```

#### Common Codelists

| Codelist | Domain.Variable | Values |
|----------|-----------------|--------|
| SEX | DM.SEX | M, F, U, UNDIFFERENTIATED |
| RACE | DM.RACE | AMERICAN INDIAN OR ALASKA NATIVE, ASIAN, ... |
| ETHNIC | DM.ETHNIC | HISPANIC OR LATINO, NOT HISPANIC OR LATINO, ... |
| NY | Various | Y, N |
| AESEV | AE.AESEV | MILD, MODERATE, SEVERE |
| AESER | AE.AESER | Y, N |
| OUT | AE.AEOUT | RECOVERED/RESOLVED, RECOVERING/RESOLVING, ... |
| AGEU | DM.AGEU | YEARS, MONTHS, WEEKS, DAYS, HOURS |

### 6. General Knowledge Base Search

**When to use**: Broad searches across all knowledge base indexes.

#### Tool: `search_knowledge_base`

```python
# Search across all indexes
result = await search_knowledge_base(
    query="How to handle partial dates in SDTM",
    top_k=5
)

# Returns:
# {
#     "query": "How to handle partial dates in SDTM",
#     "results": [
#         {
#             "content": "Partial dates in SDTM should follow ISO 8601 format...",
#             "source": "SDTM-IG 3.4 Section 4.1.4",
#             "relevance_score": 0.94
#         },
#         ...
#     ]
# }
```

### 7. SDTM Guidelines Search

**When to use**: Searching for specific SDTM implementation guidance.

#### Tool: `search_sdtm_guidelines`

```python
# Search SDTM guidelines
result = await search_sdtm_guidelines(
    query="USUBJID construction rules"
)

# Returns guidance from SDTM-IG with source citations
```

## Web-Based Reference Lookups

### SDTM-IG 3.4 Specification Fetch

**When to use**: Getting authoritative domain specifications from CDISC website.

#### Tool: `fetch_sdtmig_specification`

```python
# Fetch domain specification from CDISC
result = await fetch_sdtmig_specification(domain="LB")

# Returns:
# {
#     "domain": "LB",
#     "domain_label": "Laboratory Test Results",
#     "domain_class": "Findings",
#     "description": "The LB domain captures laboratory test results...",
#     "variables": [
#         {"variable": "STUDYID", "label": "Study Identifier", "type": "Char", "core": "Req"},
#         {"variable": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "core": "Req"},
#         ...
#     ],
#     "source": "CDISC SDTM-IG 3.4"
# }
```

### Controlled Terminology Web Fetch

**When to use**: Getting the latest CT codelist values from CDISC.

#### Tool: `fetch_controlled_terminology`

```python
# Fetch CT from CDISC website
result = await fetch_controlled_terminology(codelist="VSTEST")

# Returns latest codelist values with full definitions
```

### Web Mapping Guidance

**When to use**: Getting mapping recommendations for source columns.

#### Tool: `get_mapping_guidance_from_web`

```python
# Get web-based mapping guidance
result = await get_mapping_guidance_from_web(
    source_columns=["PATIENT_ID", "BIRTH_DATE", "SEX_CODE"],
    target_domain="DM"
)

# Returns mapping recommendations based on web resources
```

### General Internet Search

**When to use**: Searching for additional context, regulatory guidance, or troubleshooting.

#### Tool: `search_internet`

```python
# Search internet using Tavily
result = await search_internet(
    query="FDA SDTM submission requirements 2024"
)

# Returns relevant web results with summaries
```

## Query Patterns and Best Practices

### Pattern 1: Domain Requirements

```python
# Get complete domain picture
guidance = await get_sdtm_guidance(domain="AE", query="domain structure")
rules = await get_validation_rules(domain="AE")
business = await get_business_rules(domain="AE")
```

### Pattern 2: Variable Mapping

```python
# Find best mapping for source column
mapping = await get_mapping_specification(
    source_column="ADVERSE_EVENT",
    target_domain="AE"
)

# Verify controlled terminology
if mapping["recommended_target"] in ["AESEV", "AESER", "AEOUT"]:
    ct = await get_controlled_terminology(codelist=mapping["recommended_target"])
```

### Pattern 3: Validation Preparation

```python
# Before validation, understand rules
error_rules = await get_validation_rules(domain="DM", severity="ERROR")
warning_rules = await get_validation_rules(domain="DM", severity="WARNING")

# Proactively check data against rules
```

### Pattern 4: Terminology Standardization

```python
# Map raw values to CT
raw_value = "Male"
ct = await get_controlled_terminology(codelist="SEX")

# Find matching CT value
standardized = next(
    (v["code"] for v in ct["values"] if raw_value.upper() in v["decode"].upper()),
    None
)
# Result: "M"
```

## Hybrid Search Strategy

For best results, combine knowledge base and web lookups:

```python
# 1. Try knowledge base first (faster, verified)
kb_result = await get_sdtm_guidance(domain, query)

# 2. If insufficient, fetch from web (authoritative but slower)
if kb_result["confidence"] < 0.8:
    web_result = await fetch_sdtmig_specification(domain)

# 3. For edge cases, search internet
if not kb_result and not web_result:
    internet_result = await search_internet(f"CDISC SDTM {query}")
```

## Instructions for Agent

When using the knowledge base:

1. **Start with Knowledge Base**: Use Pinecone-backed tools first for speed
2. **Verify with Web**: Use web fetch for authoritative confirmation
3. **Check CT Always**: Validate categorical values against controlled terminology
4. **Cite Sources**: Include source references in outputs
5. **Handle Missing Data**: Fall back to internet search for edge cases

## Available Tools

### Pinecone Knowledge Base
- `get_sdtm_guidance` - Domain guidance and variable definitions
- `get_mapping_specification` - Source-to-target mapping patterns
- `get_validation_rules` - Pinnacle 21 / FDA rules
- `get_business_rules` - Domain business logic
- `get_controlled_terminology` - CT codelist values
- `search_knowledge_base` - General semantic search
- `search_sdtm_guidelines` - SDTM-IG specific search

### Web Reference
- `fetch_sdtmig_specification` - CDISC domain specifications
- `fetch_controlled_terminology` - Latest CT from CDISC
- `get_mapping_guidance_from_web` - Web-based mapping help

### Internet Search
- `search_internet` - Tavily-powered web search

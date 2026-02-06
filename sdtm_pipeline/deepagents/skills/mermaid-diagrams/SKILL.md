---
name: mermaid-diagrams
description: Use this skill when you need to create visual diagrams, flowcharts, process flows, data lineage, domain relationships, pipeline architectures, or any workflow visualization. Always output diagrams as mermaid code blocks.
---

# Mermaid Diagrams Skill

## Overview

This skill enables the agent to generate visual diagrams rendered directly in the chat window.
When describing processes, workflows, relationships, or architectures, generate a Mermaid diagram
using a fenced code block with the `mermaid` language tag.

## When to Use

Generate a Mermaid diagram whenever the user asks about or you need to illustrate:

- **Pipeline flows**: ETL pipeline phases, data transformation steps
- **Domain relationships**: How SDTM domains relate to each other
- **Data lineage**: Source-to-target data flow and transformations
- **Validation workflows**: How validation rules are applied
- **Process architectures**: System architecture, agent orchestration
- **Decision trees**: Mapping logic, conditional transformations
- **Sequence diagrams**: API interactions, tool call flows
- **State diagrams**: Pipeline states, domain conversion lifecycle

## Code Block Format

Always output Mermaid diagrams using this exact format:

```
```mermaid
graph TD
    A[Start] --> B[Process]
    B --> C[End]
```
```

IMPORTANT: The code block MUST use the language tag `mermaid`. The frontend will detect this
and render an interactive SVG diagram.

## Supported Diagram Types

### Flowchart (graph TD / graph LR)

Use for process flows, pipelines, and decision trees.

```
```mermaid
graph TD
    A[Data Ingestion] --> B[Raw Validation]
    B --> C{Valid?}
    C -->|Yes| D[Mapping Generation]
    C -->|No| E[Fix Errors]
    E --> B
    D --> F[SDTM Transformation]
    F --> G[Compliance Validation]
    G --> H[Data Warehouse]
```
```

- `graph TD` = top-down flow
- `graph LR` = left-to-right flow
- `[text]` = rectangle node
- `{text}` = diamond (decision) node
- `([text])` = rounded rectangle
- `((text))` = circle
- `-->` = arrow
- `-->|label|` = labeled arrow
- `---` = line without arrow

### Sequence Diagram

Use for API interactions, tool call flows, and agent communication.

```
```mermaid
sequenceDiagram
    participant U as User
    participant A as Agent
    participant T as Transformer
    participant V as Validator

    U->>A: Convert AE domain
    A->>T: Transform source data
    T-->>A: SDTM dataset
    A->>V: Validate compliance
    V-->>A: Validation report
    A-->>U: Results + report
```
```

### Class Diagram

Use for data models, domain structures, and schema relationships.

```
```mermaid
classDiagram
    class DM {
        +STUDYID: Char
        +DOMAIN: Char
        +USUBJID: Char
        +SUBJID: Char
        +SEX: Char
        +AGE: Num
        +RACE: Char
    }
    class AE {
        +STUDYID: Char
        +DOMAIN: Char
        +USUBJID: Char
        +AETERM: Char
        +AEDECOD: Char
        +AESEV: Char
    }
    DM "1" --> "*" AE : USUBJID
```
```

### State Diagram

Use for pipeline states and domain conversion lifecycle.

```
```mermaid
stateDiagram-v2
    [*] --> Pending
    Pending --> Ingesting: Start Pipeline
    Ingesting --> Validating: Data Loaded
    Validating --> Mapping: Validation Passed
    Validating --> Error: Validation Failed
    Error --> Validating: Fix & Retry
    Mapping --> Transforming: Specs Generated
    Transforming --> Compliance: Domains Converted
    Compliance --> Loading: Compliant
    Compliance --> Transforming: Fix Issues
    Loading --> [*]: Complete
```
```

### Entity Relationship Diagram

Use for database schemas and domain relationships.

```
```mermaid
erDiagram
    DM ||--o{ AE : "has adverse events"
    DM ||--o{ VS : "has vital signs"
    DM ||--o{ LB : "has lab results"
    DM ||--o{ CM : "takes medications"
    DM ||--o{ MH : "has medical history"
    DM ||--o{ DS : "has disposition"
    DM ||--o{ EX : "receives exposure"
```
```

## SDTM-Specific Templates

### 7-Phase ETL Pipeline

When asked about the SDTM pipeline, use this template:

```
```mermaid
graph TD
    P1[Phase 1: Data Ingestion] --> P2[Phase 2: Raw Data Validation]
    P2 --> P3[Phase 3: Mapping Specification]
    P3 --> P4[Phase 4: SDTM Transformation]
    P4 --> P5[Phase 5: Target Data Generation]
    P5 --> P6[Phase 6: Compliance Validation]
    P6 --> P7[Phase 7: Data Warehouse Loading]

    P1 ---|S3 Download| P1
    P2 ---|Business Rules| P2
    P3 ---|AI-Powered| P3
    P4 ---|Domain Convert| P4
    P6 ---|CDISC/FDA Rules| P6
    P7 ---|Neo4j + S3| P7
```
```

### Domain Transformation Flow

When explaining how a domain is transformed:

```
```mermaid
graph LR
    A[Source EDC Data] --> B[Analyze Structure]
    B --> C[Generate Mapping Spec]
    C --> D[Apply Transformations]
    D --> E[Derive Variables]
    E --> F[Apply CT Values]
    F --> G[Validate SDTM]
    G --> H[Output Dataset]
```
```

### Validation Hierarchy

When explaining validation:

```
```mermaid
graph TD
    V[Validation Engine] --> S[Structural Checks]
    V --> C[CDISC Conformance]
    V --> X[Cross-Domain]
    V --> F[FDA Business Rules]

    S --> S1[Required Variables]
    S --> S2[Data Types]
    S --> S3[Controlled Terminology]

    C --> C1[Variable Metadata]
    C --> C2[Domain Structure]

    X --> X1[USUBJID Consistency]
    X --> X2[Date Ranges]

    F --> F1[Pinnacle 21 Rules]
    F --> F2[Submission Readiness]
```
```

## Rules

1. **Always use mermaid code blocks** - Never describe a flow as plain text when a diagram would be clearer
2. **Keep diagrams focused** - Show the most relevant nodes; avoid cluttering with too many details
3. **Use descriptive labels** - Node text should be clear and concise
4. **Choose the right diagram type** - Flowcharts for processes, sequence diagrams for interactions, ER diagrams for data models
5. **Use consistent styling** - Follow the templates above for SDTM-specific diagrams
6. **Combine with text** - Always include a brief explanation alongside the diagram

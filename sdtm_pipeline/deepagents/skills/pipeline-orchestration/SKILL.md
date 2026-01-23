---
name: pipeline-orchestration
description: Use this skill for orchestrating the complete 7-phase SDTM ETL pipeline, managing subagent delegation, handling human review checkpoints, self-correction loops, and pipeline state management. Essential for end-to-end clinical data transformation workflows.
---

# Pipeline Orchestration Skill

## Overview

This skill provides expertise in orchestrating the complete SDTM transformation pipeline. It covers the 7-phase ETL process, subagent delegation strategies, checkpoint management, self-correction loops, and ensuring submission-ready data quality.

## The 7-Phase SDTM ETL Pipeline

### Phase Overview

```
Phase 1: Data Ingestion (Extract)
    ↓
Phase 2: Raw Data Validation (Business Checks)
    ↓ [Checkpoint if critical errors]
Phase 3: Metadata and Specification Preparation
    ↓
Phase 4: SDTM Transformation (Transform)
    ↓
Phase 5: Target Data Generation (Load + Define.xml)
    ↓
Phase 6: Target Data Validation (Compliance Checks)
    ↓ [Self-correction loop up to 3x | Human review if needed]
Phase 7: Data Warehouse Loading
    ↓
[Pipeline Complete]
```

### Phase 1: Data Ingestion (Extract)

**Purpose**: Download and catalog source EDC data from S3.

**Key Activities**:
- Download ZIP files from S3
- Extract CSV files to local workspace
- Scan and catalog available source files
- Map filenames to target SDTM domains

**Tools**: `load_data_from_s3`, `download_edc_data`, `scan_source_files`

**Success Criteria**:
- All expected source files downloaded
- Files mapped to target domains
- No extraction errors

### Phase 2: Raw Data Validation (Business Checks)

**Purpose**: Validate source data quality before transformation.

**Key Activities**:
- Check required fields are populated
- Validate data formats (dates, numeric ranges)
- Identify duplicate records
- Flag data quality issues

**Tools**: `analyze_source_file`, `validate_structural`

**Checkpoint Trigger**:
- Critical errors found → Human review required
- No critical errors → Continue to Phase 3

### Phase 3: Metadata and Specification Preparation

**Purpose**: Generate or load SDTM mapping specifications.

**Key Activities**:
- Analyze source data structure
- Generate mapping specifications (AI-powered or load from Excel)
- Define column-to-variable mappings
- Specify derivation rules

**Tools**: `generate_mapping_spec`, `load_mapping_specification`, `save_mapping_spec`

**Output**: Mapping specification with:
- Column mappings
- Derivation rules
- Controlled terminology mappings

### Phase 4: SDTM Transformation (Transform)

**Purpose**: Transform source data to SDTM format.

**Key Activities**:
- Apply column mappings per specification
- Generate USUBJID, --SEQ variables
- Convert dates to ISO 8601
- Apply controlled terminology

**Tools**: `transform_to_sdtm`, `transform_domain_with_spec`, `convert_domain`

**Delegation**: Use `transformer` subagent for domain-specific transformations

### Phase 5: Target Data Generation (Load)

**Purpose**: Generate SDTM datasets and Define.xml metadata.

**Key Activities**:
- Finalize SDTM datasets
- Generate Define.xml (machine-readable metadata)
- Create define_metadata.json

**Output**:
- SDTM CSV/XPT files
- Define.xml (v2.1)
- Metadata JSON

### Phase 6: Target Data Validation (Compliance Checks)

**Purpose**: Validate SDTM data for CDISC conformance.

**Key Activities**:
- Multi-layer validation (structural, CDISC, cross-domain, semantic)
- Calculate conformance score
- Identify submission blockers

**Tools**: `validate_structural`, `validate_cdisc_conformance`, `calculate_compliance_score`, `validate_domain`

**Delegation**: Use `validator` subagent for comprehensive validation

**Decision Points**:
- Score >= 95% → Continue to Phase 7
- Score < 95% AND iterations < 3 → Self-correction loop
- Score < 95% AND iterations >= 3 → Human review

### Phase 7: Data Warehouse Loading

**Purpose**: Load validated data to data warehouse and storage.

**Key Activities**:
- Generate SAS/R programs
- Load to Neo4j graph database
- Upload to S3
- Generate pipeline report

**Tools**: `generate_sas_program`, `generate_r_script`, `load_sdtm_to_neo4j`, `upload_sdtm_to_s3`, `generate_pipeline_report`

**Delegation**: Use `code-generator` and `data-loader` subagents

## Subagent Delegation Strategy

### Available Subagents

| Subagent | Expertise | When to Delegate |
|----------|-----------|------------------|
| `sdtm-expert` | SDTM-IG specs, CT, mapping | Domain lookups, terminology validation |
| `validator` | Multi-layer validation | Phase 2 and Phase 6 validation |
| `transformer` | Domain transformations | Phase 4 data conversion |
| `code-generator` | SAS/R programs | Phase 7 program generation |
| `data-loader` | Neo4j, S3 operations | Phase 7 data loading |

### Delegation Patterns

#### Pattern 1: Domain-Specific Transformation

```
User: "Transform demographics to SDTM"

Orchestrator:
1. Load source data (self)
2. Delegate to transformer subagent: "Transform DEMO.csv to DM domain"
3. Delegate to validator subagent: "Validate DM.csv"
4. Report results
```

#### Pattern 2: Full Pipeline Execution

```
User: "Run complete pipeline for study MAXIS-08"

Orchestrator:
1. Plan with write_todos
2. Phase 1-2: Load and validate (self + validator)
3. Phase 3: Generate mappings (self + sdtm-expert)
4. Phase 4: Transform all domains (parallel transformer calls)
5. Phase 5: Generate Define.xml (self)
6. Phase 6: Validate all (parallel validator calls)
7. Phase 7: Generate code + load (code-generator + data-loader)
```

#### Pattern 3: Validation-Only

```
User: "Validate my SDTM datasets"

Orchestrator:
1. Delegate to validator: "Run multi-layer validation on all domains"
2. Calculate conformance score
3. Report results with actionable feedback
```

## Self-Correction Loop

### Trigger Conditions

Self-correction activates when:
- Conformance score < 95% (submission threshold)
- Iteration count < 3 (max iterations)
- Issues are correctable (not fundamental data problems)

### Self-Correction Process

```
1. Analyze validation results
2. Identify weak areas (layer scores < 80%)
3. Generate correction feedback:
   - Structural issues → "Check required variables and data types"
   - CDISC issues → "Verify controlled terminology and date formats"
   - Cross-domain issues → "Ensure referential integrity across domains"
   - Semantic issues → "Review business logic and clinical plausibility"
4. Increment iteration counter
5. Re-run mapping generation with feedback
6. Re-transform affected domains
7. Re-validate
```

### Feedback Categories

| Weak Area | Feedback | Actions |
|-----------|----------|---------|
| Structural (< 80%) | Check required variables | Add missing variables, fix types |
| CDISC (< 80%) | Verify CT and dates | Fix terminology, date formats |
| Cross-domain (< 80%) | Ensure referential integrity | Fix USUBJID references |
| Semantic (< 80%) | Review business logic | Fix date ordering, plausibility |

## Human Review Checkpoints

### Checkpoint 1: After Raw Data Validation (Phase 2)

**Trigger**: Critical errors in source data

**Review Items**:
- Missing required fields
- Data format issues
- Duplicate records

**Actions**:
- Approve: Continue with warnings documented
- Reject: Stop pipeline, fix source data
- Modify: Update validation rules

### Checkpoint 2: After Target Validation (Phase 6)

**Trigger**: Score < 95% after max iterations

**Review Items**:
- Unresolved validation errors
- Conformance score breakdown
- Submission blockers

**Actions**:
- Approve: Accept data quality, document rationale
- Reject: Return to mapping phase
- Modify: Adjust thresholds or rules

## Pipeline State Management

### State Variables

```python
SDTMPipelineState = {
    # Study Identification
    "study_id": str,
    "raw_data_dir": str,
    "output_dir": str,

    # Phase Tracking
    "current_phase": str,  # "data_ingestion", "raw_validation", etc.
    "phase_history": List[str],

    # Data
    "source_files": Dict[str, str],  # domain -> path
    "sdtm_data_paths": Dict[str, str],  # domain -> output path
    "mapping_specs": Dict[str, Dict],  # domain -> spec

    # Validation
    "raw_validation_results": List[Dict],
    "sdtm_validation_results": List[Dict],
    "conformance_score": float,
    "submission_ready": bool,

    # Self-Correction
    "iteration_count": int,
    "max_iterations": int,  # default: 3
    "needs_correction": bool,
    "correction_feedback": str,

    # Human Review
    "pending_review": str,  # What triggered review
    "human_decision": str,  # "approve", "reject", "modify"

    # Output
    "define_xml_path": str,
    "neo4j_loaded": bool,
    "s3_uploaded": bool,
}
```

### State Transitions

```
INITIAL → data_ingestion (Phase 1)
data_ingestion → raw_validation (Phase 2)
raw_validation → [human_review | mapping_generation] (Phase 3)
mapping_generation → transformation (Phase 4)
transformation → target_generation (Phase 5)
target_generation → sdtm_validation (Phase 6)
sdtm_validation → [generate_code | self_correction | human_review]
self_correction → mapping_generation (loop back)
generate_code → data_loading (Phase 7)
data_loading → COMPLETE
```

## Pipeline Execution Examples

### Example 1: Simple Single-Domain Conversion

```python
# User: "Convert demographics to SDTM"

# 1. Load data
await load_data_from_s3(study_id="MAXIS-08")

# 2. Convert single domain (high-level tool)
result = await convert_domain("DM")

# 3. Report
print(f"DM domain created: {result['records_out']} records")
```

### Example 2: Full Pipeline with Todos

```python
# User: "Run complete SDTM pipeline for MAXIS-08"

# 1. Plan the work
todos = [
    "Download EDC data from S3",
    "Validate raw data quality",
    "Generate mapping specifications for all domains",
    "Transform to SDTM format",
    "Generate Define.xml",
    "Validate SDTM compliance",
    "Generate SAS/R programs",
    "Load to Neo4j and S3"
]
await write_todos(todos)

# 2. Execute each phase with progress updates
await update_todo(0, "in_progress")
await load_data_from_s3(study_id="MAXIS-08")
await update_todo(0, "completed")

# ... continue through all phases
```

### Example 3: Handling Self-Correction

```python
# After Phase 6 validation returns score < 95%

# 1. Analyze issues
validation_results = get_validation_results()
weak_layers = [layer for layer, score in layer_scores.items() if score < 80]

# 2. Generate feedback
if "structural" in weak_layers:
    feedback = "Add missing required variables: RFSTDTC, RFENDTC"
elif "cdisc" in weak_layers:
    feedback = "Fix controlled terminology for SEX, RACE variables"

# 3. Re-run with feedback
await generate_mapping_spec(source_file, domain, study_id, feedback=feedback)
await transform_to_sdtm(source_file, mapping_spec, output_path)

# 4. Re-validate
new_score = await calculate_compliance_score(validation_results)
```

## Instructions for Agent

When orchestrating pipelines:

1. **Always Plan First**: Use `write_todos` to break down complex tasks
2. **Execute Sequentially**: Follow the 7-phase order
3. **Delegate Appropriately**: Use subagents for specialized tasks
4. **Monitor Progress**: Update todos as phases complete
5. **Handle Checkpoints**: Pause for human review when triggered
6. **Implement Self-Correction**: Retry up to 3 times before escalating
7. **Report Results**: Provide clear status and metrics

## Available Tools

### Data Loading (Phase 1)
- `load_data_from_s3`, `download_edc_data`, `scan_source_files`

### Validation (Phase 2, 6)
- `validate_structural`, `validate_cdisc_conformance`, `calculate_compliance_score`

### Mapping (Phase 3)
- `generate_mapping_spec`, `load_mapping_specification`, `save_mapping_spec`

### Transformation (Phase 4)
- `transform_to_sdtm`, `transform_domain_with_spec`, `convert_domain`

### Output (Phase 5, 7)
- `generate_sas_program`, `generate_r_script`, `load_sdtm_to_neo4j`, `upload_sdtm_to_s3`

### Reporting
- `generate_pipeline_report`, `get_conversion_status`

---
name: data-loading
description: Use this skill for loading clinical trial data from AWS S3, downloading and extracting EDC (Electronic Data Capture) data, scanning source files, and analyzing data structures. Essential for Phase 1 (Data Ingestion) of the SDTM pipeline.
---

# Data Loading and Source Analysis Skill

## Overview

This skill provides expertise in loading clinical trial data from various sources, primarily AWS S3. It covers EDC data extraction, source file scanning, structure analysis, and domain mapping detection. This is the foundation for all SDTM transformations.

## Core Competencies

### 1. S3 Data Loading

**When to use**: Loading raw EDC data from AWS S3 buckets at the start of a pipeline.

#### S3 Bucket Structure

Clinical trial data in S3 typically follows this structure:

```
s3://s3dcri/
  └── Clinical_Studies/
      └── MAXIS-08/
          └── RAW_DATA/
              ├── Maxis-08 RAW DATA.zip
              └── extracted/
                  ├── DEMO.csv
                  ├── AE.csv
                  ├── VS.csv
                  ├── LB.csv
                  └── ...
```

#### Loading Workflow

```python
# Step 1: Load data from S3
result = await load_data_from_s3(
    study_id="MAXIS-08",
    s3_bucket="s3dcri",
    s3_prefix="Clinical_Studies/MAXIS-08/RAW_DATA"
)

# Returns:
# {
#     "success": True,
#     "study_id": "MAXIS-08",
#     "files_loaded": 12,
#     "total_records": 15420,
#     "domains": ["DM", "AE", "VS", "LB", "CM", "EX", ...]
# }
```

#### Download and Extract ZIP Files

```python
# For ZIP archives containing multiple CSV files
result = await download_edc_data(
    s3_bucket="s3dcri",
    s3_key="Clinical_Studies/MAXIS-08/RAW_DATA/Maxis-08 RAW DATA.zip",
    local_dir="/tmp/s3_data"
)

# Returns:
# {
#     "success": True,
#     "files": [
#         {"name": "DEMO.csv", "path": "/tmp/s3_data/extracted/DEMO.csv", "size_kb": 125.5},
#         {"name": "AE.csv", "path": "/tmp/s3_data/extracted/AE.csv", "size_kb": 342.1},
#         ...
#     ],
#     "count": 12
# }
```

### 2. Source File Scanning

**When to use**: Understanding what data files are available and determining SDTM domain mappings.

#### Domain Pattern Recognition

The scanner automatically detects target SDTM domains based on filename patterns:

| Filename Pattern | Target Domain | Description |
|------------------|---------------|-------------|
| DEMO*, DEMOGRAPHY* | DM | Demographics |
| AE*, AEVENT*, ADVERSE* | AE | Adverse Events |
| VS*, VITAL* | VS | Vital Signs |
| LB*, LAB*, CHEM*, HEM*, URIN* | LB | Laboratory |
| CM*, CONMED*, MEDICATION* | CM | Concomitant Medications |
| EX*, EXPOSURE*, DOSE* | EX | Exposure |
| MH*, MEDHIST*, MEDHX* | MH | Medical History |
| DS*, DISPOSITION* | DS | Disposition |
| PE*, PHYSEXAM*, PHYSICAL* | PE | Physical Examination |
| EG*, ECG*, ELECTROCARD* | EG | ECG Test Results |
| QS*, QUEST* | QS | Questionnaires |
| IE*, INCEXC*, ELIG* | IE | Inclusion/Exclusion |

#### Scanning Files

```python
# Scan a directory for source files
result = await scan_source_files("/tmp/s3_data/extracted")

# Returns:
# {
#     "success": True,
#     "total_files": 15,
#     "mapped_files": 12,
#     "unmapped_files": 3,
#     "domains_found": ["DM", "AE", "VS", "LB", "CM", "EX", "MH", "DS"],
#     "files": [
#         {"name": "DEMO.csv", "path": "...", "size_kb": 125.5, "target_domain": "DM", "mapped": True},
#         {"name": "VITALS.csv", "path": "...", "size_kb": 890.2, "target_domain": "VS", "mapped": True},
#         {"name": "CUSTOM_DATA.csv", "path": "...", "size_kb": 45.0, "target_domain": null, "mapped": False},
#         ...
#     ]
# }
```

### 3. Source File Analysis

**When to use**: Understanding the structure and content of a specific source file before transformation.

#### Column Analysis

```python
# Analyze a source file's structure
result = await analyze_source_file("/tmp/s3_data/extracted/DEMO.csv")

# Returns:
# {
#     "success": True,
#     "file_name": "DEMO.csv",
#     "row_count": 150,
#     "column_count": 25,
#     "memory_mb": 0.85,
#     "columns": [
#         {
#             "name": "SUBJECT_ID",
#             "dtype": "object",
#             "non_null": 150,
#             "null_count": 0,
#             "unique_values": 150,
#             "sample_values": ["001", "002", "003"]
#         },
#         {
#             "name": "BIRTH_DATE",
#             "dtype": "object",
#             "non_null": 148,
#             "null_count": 2,
#             "unique_values": 120,
#             "sample_values": ["1985-06-23", "1972-11-15", "1990-03-08"]
#         },
#         ...
#     ]
# }
```

### 4. Data Preview

**When to use**: Quick inspection of source data before processing.

```python
# Preview first few records of a source file
result = await preview_source_file("/tmp/s3_data/extracted/DEMO.csv", n_rows=5)

# Returns preview with column headers and first 5 rows
```

### 5. Domain Detection Logic

The domain detection uses a comprehensive pattern dictionary supporting all 63 SDTM domains:

#### Special Purpose Domains
- `CO` - COMMENT, CO
- `DM` - DEMO, DEMOGRAPHY, DM, DEMOGRAPHICS
- `SE` - SUBJELEM, SE, ELEMENT
- `SV` - SUBJVISIT, SV, VISIT

#### Interventions Domains
- `CM` - CONMEDS, CM, MEDICATION, CONMED
- `EX` - DOSE, EXPOSURE, EX, DOSING
- `PR` - PROCEDURE, PR, PROC
- `SU` - SUBUSE, SU, SUBSTANCE, ALCOHOL, TOBACCO

#### Events Domains
- `AE` - AEVENT, AE, ADVERSE, ADVERSEEVENT
- `DS` - CMPL, DISPOSITION, DS, DISP
- `DV` - DEVIATION, DV, PROTDEV
- `MH` - GMEDHX, MEDHIST, MH, MEDHX, SURGHX

#### Findings Domains
- `VS` - VITALS, VS, VITAL, VITALSIGN
- `LB` - CHEMLAB, HEMLAB, LAB, URINLAB, LB, BIOLAB
- `EG` - ECG, EG, ELECTROCARD
- `PE` - PHYSEXAM, PE, PHYSICAL
- `QS` - QUEST, QS, QUESTIONNAIRE

## Common Workflows

### Workflow 1: Full Study Load

```python
# 1. Load from S3
await load_data_from_s3(study_id="MAXIS-08")

# 2. List available domains
domains = await list_available_domains()

# 3. Preview specific domain
await preview_source_file(domains["VS"]["path"])
```

### Workflow 2: Analyze Before Transform

```python
# 1. Download EDC data
await download_edc_data(
    s3_bucket="s3dcri",
    s3_key="Clinical_Studies/MAXIS-08/RAW_DATA.zip",
    local_dir="/tmp/maxis08"
)

# 2. Scan for files
scan = await scan_source_files("/tmp/maxis08/extracted")

# 3. Analyze each mapped file
for file in scan["files"]:
    if file["mapped"]:
        analysis = await analyze_source_file(file["path"])
        print(f"Domain {file['target_domain']}: {analysis['row_count']} records, {analysis['column_count']} columns")
```

### Workflow 3: Custom File Mapping

For files that don't match standard patterns:

```python
# 1. Scan to find unmapped files
scan = await scan_source_files(directory)
unmapped = [f for f in scan["files"] if not f["mapped"]]

# 2. Analyze each unmapped file
for file in unmapped:
    analysis = await analyze_source_file(file["path"])

    # Review columns to determine target domain
    print(f"File: {file['name']}")
    print(f"Columns: {[c['name'] for c in analysis['columns']]}")

    # Manually assign domain based on content
```

## Data Quality Checks During Loading

### Check 1: Required Files Present

```python
required_domains = ["DM", "AE", "VS", "EX"]
scan = await scan_source_files(directory)
found_domains = set(scan["domains_found"])

missing = [d for d in required_domains if d not in found_domains]
if missing:
    print(f"WARNING: Missing required domains: {missing}")
```

### Check 2: File Size Validation

```python
# Flag very large files that may need chunked processing
large_files = [f for f in scan["files"] if f["size_kb"] > 100000]  # > 100MB
if large_files:
    print(f"Large files detected: {[f['name'] for f in large_files]}")
```

### Check 3: Column Completeness

```python
# Check for files with high null rates
analysis = await analyze_source_file(file_path)
for col in analysis["columns"]:
    null_rate = col["null_count"] / analysis["row_count"] * 100
    if null_rate > 50:
        print(f"WARNING: {col['name']} has {null_rate:.1f}% null values")
```

## Instructions for Agent

When loading data:

1. **Always Load First**: Use `load_data_from_s3` or `download_edc_data` before any transformations
2. **Scan Before Processing**: Use `scan_source_files` to understand available data
3. **Analyze Critical Files**: Use `analyze_source_file` for files that will be transformed
4. **Handle Unmapped Files**: Review and manually map files that don't match patterns
5. **Document Data Issues**: Note any quality issues discovered during loading

## Available Tools

- `load_data_from_s3` - Load EDC data from S3 bucket
- `download_edc_data` - Download and extract ZIP files from S3
- `scan_source_files` - Scan directory for source files and detect domains
- `analyze_source_file` - Analyze file structure and content
- `preview_source_file` - Preview first N rows of a file
- `list_available_domains` - List domains available after loading

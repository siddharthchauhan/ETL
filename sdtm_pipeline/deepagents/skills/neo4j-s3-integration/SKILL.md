---
name: neo4j-s3-integration
description: Use this skill for loading SDTM data to Neo4j graph database, uploading files to AWS S3, managing data warehouse operations, and creating clinical data graphs. Essential for Phase 7 (Data Warehouse Loading) and data persistence.
---

# Neo4j and S3 Integration Skill

## Overview

This skill provides expertise in loading validated SDTM datasets to Neo4j graph database and uploading files to AWS S3. It covers graph data modeling for clinical trials, relationship creation between domains, and cloud storage patterns for regulatory submissions.

## Neo4j Graph Database Integration

### Why Graph Database for SDTM?

Clinical trial data has inherent relationships:
- Subjects (DM) have adverse events (AE)
- Subjects receive medications (CM, EX)
- Subjects have lab results (LB), vital signs (VS)
- Events relate to treatments

A graph database naturally models these relationships, enabling:
- Efficient traversal of patient journeys
- Cross-domain analysis
- Signal detection
- Timeline visualization

### Neo4j Data Model for SDTM

#### Node Types (Labels)

Each SDTM domain becomes a node label:

```cypher
// Demographics node
(:SDTM_DM {
    STUDYID: "MAXIS-08",
    USUBJID: "MAXIS-08-001",
    SUBJID: "001",
    AGE: 45,
    SEX: "M",
    RACE: "WHITE",
    ...
})

// Adverse Event node
(:SDTM_AE {
    STUDYID: "MAXIS-08",
    USUBJID: "MAXIS-08-001",
    AESEQ: 1,
    AETERM: "HEADACHE",
    AESEV: "MILD",
    ...
})
```

#### Relationships

```cypher
// Subject has adverse event
(dm:SDTM_DM)-[:HAS_ADVERSE_EVENT]->(ae:SDTM_AE)
WHERE dm.USUBJID = ae.USUBJID

// Subject took medication
(dm:SDTM_DM)-[:TOOK_MEDICATION]->(cm:SDTM_CM)
WHERE dm.USUBJID = cm.USUBJID

// Subject was exposed to study drug
(dm:SDTM_DM)-[:RECEIVED_EXPOSURE]->(ex:SDTM_EX)
WHERE dm.USUBJID = ex.USUBJID

// Subject has lab result
(dm:SDTM_DM)-[:HAS_LAB_RESULT]->(lb:SDTM_LB)
WHERE dm.USUBJID = lb.USUBJID

// Subject has vital sign measurement
(dm:SDTM_DM)-[:HAS_VITAL_SIGN]->(vs:SDTM_VS)
WHERE dm.USUBJID = vs.USUBJID
```

### Loading SDTM to Neo4j

#### Tool: `load_sdtm_to_neo4j`

```python
# Load a single domain to Neo4j
result = await load_sdtm_to_neo4j(domain="DM")

# Returns:
# {
#     "success": True,
#     "domain": "DM",
#     "nodes_created": 150,
#     "relationships_created": 0,
#     "label": "SDTM_DM"
# }
```

#### Tool: `load_to_neo4j` (subagent tool)

```python
# Load from specific file path
result = await load_to_neo4j(
    domain="AE",
    file_path="/output/sdtm/ae.csv"
)

# Returns:
# {
#     "success": True,
#     "domain": "AE",
#     "nodes_created": 342,
#     "label": "SDTM_AE"
# }
```

### Neo4j Configuration

#### Environment Variables

```bash
NEO4J_URI=neo4j://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

#### Connection Pattern

```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)

async def load_domain_to_neo4j(df: pd.DataFrame, domain: str):
    """Load DataFrame to Neo4j as nodes."""
    label = f"SDTM_{domain.upper()}"

    async with driver.session() as session:
        # Create nodes from records
        for record in df.to_dict('records'):
            await session.run(
                f"CREATE (n:{label} $props)",
                props=record
            )
```

### Graph Query Examples

#### Find All Events for a Subject

```cypher
MATCH (dm:SDTM_DM {USUBJID: "MAXIS-08-001"})-[r]->(event)
RETURN dm, r, event
```

#### Find Subjects with Serious AEs

```cypher
MATCH (dm:SDTM_DM)-[:HAS_ADVERSE_EVENT]->(ae:SDTM_AE)
WHERE ae.AESER = "Y"
RETURN dm.USUBJID, ae.AETERM, ae.AESTDTC
```

#### Timeline of Events for Subject

```cypher
MATCH (dm:SDTM_DM {USUBJID: "MAXIS-08-001"})
OPTIONAL MATCH (dm)-[:HAS_ADVERSE_EVENT]->(ae:SDTM_AE)
OPTIONAL MATCH (dm)-[:TOOK_MEDICATION]->(cm:SDTM_CM)
OPTIONAL MATCH (dm)-[:HAS_LAB_RESULT]->(lb:SDTM_LB)
RETURN ae, cm, lb
ORDER BY coalesce(ae.AESTDTC, cm.CMSTDTC, lb.LBDTC)
```

#### Cross-Domain Analysis

```cypher
// Find subjects who had AE after starting medication
MATCH (dm:SDTM_DM)-[:TOOK_MEDICATION]->(cm:SDTM_CM),
      (dm)-[:HAS_ADVERSE_EVENT]->(ae:SDTM_AE)
WHERE ae.AESTDTC > cm.CMSTDTC
RETURN dm.USUBJID, cm.CMTRT, ae.AETERM, cm.CMSTDTC, ae.AESTDTC
```

## AWS S3 Integration

### S3 Bucket Structure for SDTM

```
s3://s3dcri/
  └── Clinical_Studies/
      └── MAXIS-08/
          ├── RAW_DATA/
          │   ├── Maxis-08 RAW DATA.zip
          │   └── extracted/
          │       ├── DEMO.csv
          │       ├── AE.csv
          │       └── ...
          ├── SDTM_OUTPUT/
          │   ├── dm.csv
          │   ├── ae.csv
          │   ├── vs.csv
          │   ├── lb.csv
          │   ├── define.xml
          │   └── ...
          ├── PROGRAMS/
          │   ├── dm.sas
          │   ├── ae.sas
          │   └── dm.R
          └── REPORTS/
              └── pipeline_report.json
```

### Uploading SDTM to S3

#### Tool: `upload_sdtm_to_s3`

```python
# Upload SDTM domain to S3
result = await upload_sdtm_to_s3(domain="DM")

# Returns:
# {
#     "success": True,
#     "domain": "DM",
#     "s3_uri": "s3://s3dcri/Clinical_Studies/MAXIS-08/SDTM_OUTPUT/dm.csv",
#     "size_kb": 125.5
# }
```

#### Tool: `upload_to_s3` (subagent tool)

```python
# Upload any file to S3
result = await upload_to_s3(
    file_path="/output/sdtm/dm.csv",
    s3_key="Clinical_Studies/MAXIS-08/SDTM_OUTPUT/dm.csv"
)

# Returns:
# {
#     "success": True,
#     "s3_uri": "s3://s3dcri/Clinical_Studies/MAXIS-08/SDTM_OUTPUT/dm.csv"
# }
```

### S3 Configuration

#### Environment Variables

```bash
S3_ETL_BUCKET=s3dcri
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
```

#### Upload Pattern

```python
import boto3
from botocore.exceptions import ClientError

s3_client = boto3.client('s3')

async def upload_file_to_s3(file_path: str, bucket: str, key: str) -> dict:
    """Upload file to S3 bucket."""
    try:
        await asyncio.to_thread(
            s3_client.upload_file,
            file_path,
            bucket,
            key
        )
        return {
            "success": True,
            "s3_uri": f"s3://{bucket}/{key}"
        }
    except ClientError as e:
        return {"success": False, "error": str(e)}
```

## Complete Loading Workflow

### Workflow: Load All Domains

```python
# 1. Load all SDTM domains to Neo4j
domains = ["DM", "AE", "VS", "LB", "CM", "EX", "MH", "DS"]

for domain in domains:
    result = await load_sdtm_to_neo4j(domain)
    print(f"Loaded {domain}: {result['nodes_created']} nodes")

# 2. Create relationships (done automatically by loader)
# Relationships are created based on USUBJID joins

# 3. Upload all to S3
for domain in domains:
    result = await upload_sdtm_to_s3(domain)
    print(f"Uploaded {domain}: {result['s3_uri']}")
```

### Workflow: Load with Validation

```python
# 1. Validate before loading
validation = await validate_domain(domain)
if not validation["is_valid"]:
    print(f"Validation failed: {validation['errors']}")
    return

# 2. Load to Neo4j
neo4j_result = await load_sdtm_to_neo4j(domain)

# 3. Upload to S3
s3_result = await upload_sdtm_to_s3(domain)

# 4. Generate report
report = {
    "domain": domain,
    "validation": validation,
    "neo4j": neo4j_result,
    "s3": s3_result
}
```

## Data Loader Subagent

The `data-loader` subagent specializes in warehouse operations:

### Capabilities

- Load SDTM domains to Neo4j as labeled nodes
- Create relationships between patient and clinical data
- Upload files to S3 with proper key structure
- Handle large datasets with chunked processing

### Delegation Pattern

```python
# Delegate to data-loader subagent
await task(
    agent="data-loader",
    prompt=f"""
    Load the following SDTM domains to Neo4j and S3:
    - DM (Demographics)
    - AE (Adverse Events)
    - VS (Vital Signs)

    Study ID: MAXIS-08
    Output directory: /tmp/sdtm_output
    S3 prefix: Clinical_Studies/MAXIS-08/SDTM_OUTPUT
    """
)
```

## Error Handling

### Neo4j Connection Errors

```python
try:
    result = await load_sdtm_to_neo4j(domain)
except ConnectionError:
    print("Neo4j connection failed. Check NEO4J_URI and credentials.")
except AuthError:
    print("Neo4j authentication failed. Check NEO4J_USER and NEO4J_PASSWORD.")
```

### S3 Upload Errors

```python
try:
    result = await upload_sdtm_to_s3(domain)
except NoCredentialsError:
    print("AWS credentials not found. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.")
except BucketNotFoundError:
    print(f"S3 bucket not found. Check S3_ETL_BUCKET configuration.")
```

## Performance Considerations

### Neo4j Bulk Loading

For large datasets (>100K records):

```python
# Use UNWIND for batch inserts
UNWIND $records AS record
CREATE (n:SDTM_LB)
SET n = record
```

### S3 Multipart Upload

For large files (>100MB):

```python
# Configure multipart threshold
config = TransferConfig(
    multipart_threshold=100 * 1024 * 1024,  # 100MB
    max_concurrency=10
)
s3_client.upload_file(file_path, bucket, key, Config=config)
```

## Instructions for Agent

When loading data to Neo4j and S3:

1. **Validate First**: Always validate SDTM data before loading
2. **Load DM First**: Demographics should be loaded first (parent nodes)
3. **Check Connections**: Verify Neo4j and S3 connectivity before batch operations
4. **Handle Errors**: Gracefully handle connection failures
5. **Report Results**: Provide node/relationship counts and S3 URIs

## Available Tools

### Neo4j Operations
- `load_sdtm_to_neo4j` - High-level domain loading
- `load_to_neo4j` - Load from specific file path

### S3 Operations
- `upload_sdtm_to_s3` - High-level domain upload
- `upload_to_s3` - Upload any file to S3

### Batch Operations
- `save_sdtm_locally` - Save to local filesystem first
- `generate_pipeline_report` - Generate comprehensive report

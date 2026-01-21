# SDTM Clinical Trial Data Transformation Pipeline

A production-ready LangGraph-based pipeline for transforming raw clinical trial data into CDISC SDTM (Study Data Tabulation Model) format with AI-powered mapping generation, automated validation, and code generation.

## Features

| Feature | Description |
|---------|-------------|
| **LangGraph Architecture** | Async parallel node execution with state management |
| **AI-Powered Mapping** | Claude generates SDTM mapping specifications from source data |
| **Parallel Processing** | Concurrent validation, transformation, and code generation |
| **LangSmith Observability** | Full tracing and monitoring at smith.langchain.com |
| **Human-in-the-Loop** | Review checkpoints for quality control |
| **Neo4j Integration** | Graph database storage with patient relationships |
| **S3 Integration** | Cloud storage for processed outputs |
| **Code Generation** | Auto-generated SAS and R programs |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SDTM LANGGRAPH PIPELINE                             │
│                                                                             │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐   │
│  │  Ingest  │───►│   Validate   │───►│  Generate   │───►│   Human      │   │
│  │   Data   │    │   Raw Data   │    │  Mappings   │    │   Review     │   │
│  └──────────┘    │  (Parallel)  │    │  (Parallel) │    │ (Checkpoint) │   │
│                  └──────────────┘    └─────────────┘    └──────┬───────┘   │
│                                                                 │           │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────┐           │           │
│  │ Generate │◄───│   Validate   │◄───│  Transform  │◄──────────┘           │
│  │   Code   │    │  SDTM Data   │    │  to SDTM    │                       │
│  │(SAS + R) │    │  (Parallel)  │    │  (Parallel) │                       │
│  └────┬─────┘    └──────────────┘    └─────────────┘                       │
│       │                                                                     │
│       ▼                                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────┐                       │
│  │  Neo4j   │───►│   S3 Upload  │───►│   Report    │───► COMPLETE          │
│  │  Load    │    │  (Processed) │    │ Generation  │                       │
│  └──────────┘    └──────────────┘    └─────────────┘                       │
│                                                                             │
│  [All nodes traced with LangSmith @traceable decorator]                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Supported SDTM Domains

| Source File | Target Domain | Description |
|-------------|---------------|-------------|
| DEMO.csv | DM | Demographics |
| AEVENT.csv | AE | Adverse Events |
| VITALS.csv | VS | Vital Signs |
| CONMEDS.csv | CM | Concomitant Medications |
| CHEMLAB.csv | LB | Laboratory (Chemistry) |
| HEMLAB.csv | LB | Laboratory (Hematology) |

---

## Prerequisites

- **Python** 3.11+
- **Docker** (for Neo4j)
- **AWS Account** (for S3 access)
- **Anthropic API Key** (for Claude AI)
- **LangSmith Account** (optional, for observability)

---

## Installation

### 1. Clone and Setup Virtual Environment

```bash
cd /path/to/ETL

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file (copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# =============================================================================
# ANTHROPIC API (Required)
# =============================================================================
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# =============================================================================
# AWS S3 Configuration (Required for S3 upload)
# =============================================================================
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
S3_ETL_BUCKET=your-bucket-name

# =============================================================================
# NEO4J Configuration (Required for graph database)
# =============================================================================
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123
NEO4J_DATABASE=neo4j

# =============================================================================
# LANGSMITH Configuration (Optional - for observability)
# =============================================================================
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=sdtm-pipeline
LANGCHAIN_API_KEY=lsv2_pt_your-langsmith-key
```

### 3. Start Neo4j (Docker)

```bash
docker run -d \
    --name neo4j \
    -p 7474:7474 \
    -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/password123 \
    -e NEO4J_PLUGINS='["apoc"]' \
    neo4j:5.27-community

# Verify Neo4j is running
docker ps | grep neo4j

# Access Neo4j Browser at http://localhost:7474
```

---

## Running the Pipeline

### Option 1: LangGraph Dev Server (Recommended)

Run the pipeline with the LangGraph development server and Studio UI:

```bash
# Activate virtual environment
source venv/bin/activate

# Install package in editable mode (first time only)
pip install -e .

# Start the LangGraph dev server
langgraph dev
```

This will start the server and open LangGraph Studio in your browser:
- **API**: http://127.0.0.1:2024
- **Studio UI**: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
- **API Docs**: http://127.0.0.1:2024/docs

In Studio, you can:
1. View the pipeline graph visualization
2. Create new threads and invoke the pipeline
3. Monitor execution in real-time
4. Inspect state at each node

**Example Input** (in Studio):
```json
{
  "study_id": "MAXIS-08",
  "raw_data_dir": "/tmp/s3_data/extracted/Maxis-08 RAW DATA_CSV",
  "output_dir": "./sdtm_langgraph_output",
  "human_decision": "approve"
}
```

### Option 2: Python Script

Run the pipeline directly with Python:

```bash
# Activate virtual environment
source venv/bin/activate

# Run the pipeline
python3 run_sdtm_langgraph.py
```

### What Happens

1. **Downloads data from S3** - Fetches `EDC Data.zip` from your S3 bucket
2. **Selects key clinical domains** - Identifies DEMO, AEVENT, VITALS, etc.
3. **Runs LangGraph pipeline** with these async parallel nodes:
   - **Ingest**: Scans and catalogs source files
   - **Validate Raw**: Parallel validation of all source files
   - **Generate Mappings**: AI generates SDTM mapping specs using Claude
   - **Human Review**: Checkpoint for approval (auto-approved by default)
   - **Transform**: Parallel transformation to SDTM format
   - **Validate SDTM**: Parallel CDISC compliance checking
   - **Generate Code**: Parallel SAS and R code generation
   - **Load Neo4j**: Creates graph nodes and relationships
   - **Upload S3**: Uploads all outputs to `processed/sdtm/{study_id}/`
   - **Report**: Generates final pipeline report

### Expected Output

```
======================================================================
   SDTM LANGGRAPH AGENT PIPELINE
   Study: MAXIS-08
======================================================================
LangSmith configured:
  Project: sdtm-pipeline
  Tracing: enabled

NODE: Ingest Data (Async)
  - DEMO.csv -> DM
  - AEVENT.csv -> AE
  - VITALS.csv -> VS
  ...

NODE: Validate Raw Data (Parallel Async)
  DEMO.csv: PASS (16 records)
  AEVENT.csv: PASS (550 records)
  ...

NODE: Generate Mappings (Parallel Async)
  DEMO.csv: 9 mappings
  AEVENT.csv: 20 mappings
  ...

NODE: Transform to SDTM (Parallel Async)
  DEMO.csv: 16 -> 16 records
  VITALS.csv: 536 -> 2,184 records
  ...

NODE: Load to Neo4j (Async)
  Created 6,378 nodes
  Created 12,252 relationships

NODE: Upload to S3 (Async)
  Uploaded 28 files to s3://bucket/processed/sdtm/MAXIS-08/

======================================================================
   SDTM LANGGRAPH PIPELINE COMPLETE
======================================================================
Results:
  SDTM domains: 6
  Records transformed: 6,378
  Neo4j loaded: True
  S3 uploaded: True
```

---

## Output Structure

After running the pipeline, outputs are saved to `sdtm_langgraph_output/`:

```
sdtm_langgraph_output/
├── sdtm_data/                    # SDTM domain CSV files
│   ├── dm.csv                    # Demographics
│   ├── ae.csv                    # Adverse Events
│   ├── vs.csv                    # Vital Signs
│   ├── cm.csv                    # Concomitant Medications
│   └── lb.csv                    # Laboratory Results
│
├── sas_programs/                 # Generated SAS code
│   ├── setup.sas                 # Library setup and macros
│   ├── driver.sas                # Main execution driver
│   ├── dm.sas                    # DM domain program
│   ├── ae.sas                    # AE domain program
│   ├── vs.sas                    # VS domain program
│   ├── cm.sas                    # CM domain program
│   └── lb.sas                    # LB domain program
│
├── r_programs/                   # Generated R scripts (pharmaverse)
│   ├── setup.R                   # Environment setup
│   ├── driver.R                  # Main execution driver
│   ├── dm.R                      # DM domain script
│   ├── ae.R                      # AE domain script
│   ├── vs.R                      # VS domain script
│   ├── cm.R                      # CM domain script
│   ├── lb.R                      # LB domain script
│   └── validation.R              # SDTM validation script
│
├── mapping_specs/                # JSON mapping specifications
│   ├── DM_mapping.json
│   ├── AE_mapping.json
│   ├── VS_mapping.json
│   ├── CM_mapping.json
│   └── LB_mapping.json
│
├── raw_validation/               # Raw data validation reports
│   └── validation_report.json
│
├── sdtm_validation/              # SDTM compliance reports
│   └── validation_report.json
│
└── reports/                      # Final pipeline report
    └── pipeline_report.json
```

---

## LangSmith Observability

The pipeline integrates with LangSmith for full observability. View traces at:

**https://smith.langchain.com** (Project: `sdtm-pipeline`)

Each node is decorated with `@traceable` providing:
- Execution timing per node
- Input/output state tracking
- Error tracing and debugging
- Parallel execution visualization

---

## Neo4j Graph Structure

The pipeline creates the following graph structure:

```
(:SDTM_DM {USUBJID, SUBJID, AGE, SEX, RACE, ...})
    │
    ├──[:HAS_ADVERSE_EVENT]──► (:SDTM_AE {AETERM, AESTDTC, AESEV, ...})
    │
    ├──[:HAS_VITAL_SIGN]──► (:SDTM_VS {VSTESTCD, VSORRES, VSDTC, ...})
    │
    ├──[:HAS_LAB_RESULT]──► (:SDTM_LB {LBTESTCD, LBORRES, LBDTC, ...})
    │
    └──[:TAKES_MEDICATION]──► (:SDTM_CM {CMTRT, CMDOSE, CMSTDTC, ...})
```

### Query Examples

```cypher
-- Count nodes by domain
MATCH (n)
WHERE any(label IN labels(n) WHERE label STARTS WITH 'SDTM_')
RETURN labels(n)[0] AS domain, count(n) AS count
ORDER BY count DESC;

-- Find all adverse events for a patient
MATCH (p:SDTM_DM)-[:HAS_ADVERSE_EVENT]->(ae:SDTM_AE)
WHERE p.USUBJID = 'MAXIS-08-408-01-01'
RETURN ae.AETERM, ae.AESEV, ae.AESTDTC;

-- Patients with both AEs and abnormal labs
MATCH (p:SDTM_DM)-[:HAS_ADVERSE_EVENT]->(ae:SDTM_AE)
MATCH (p)-[:HAS_LAB_RESULT]->(lb:SDTM_LB)
WHERE lb.LBNRIND = 'HIGH'
RETURN DISTINCT p.USUBJID, count(DISTINCT ae) AS ae_count;
```

---

## Project Structure

```
ETL/
├── run_sdtm_langgraph.py         # Main pipeline entry point
├── requirements.txt              # Python dependencies
├── .env                          # Environment configuration
├── .env.example                  # Example configuration template
├── README.md                     # This documentation
│
├── sdtm_pipeline/                # Core SDTM pipeline package
│   ├── __init__.py
│   │
│   ├── langgraph_agent/          # LangGraph async agent
│   │   ├── __init__.py
│   │   ├── agent.py              # Main graph definition
│   │   ├── state.py              # Pipeline state schema
│   │   ├── async_nodes.py        # Async parallel node functions
│   │   ├── supervisor.py         # Supervisor hierarchy pattern
│   │   ├── tools.py              # LangChain tools
│   │   └── config.py             # LangSmith/Neo4j/S3 config
│   │
│   ├── models/                   # Data models
│   │   └── sdtm_models.py        # SDTM domain models
│   │
│   ├── validators/               # Validation components
│   │   ├── raw_data_validator.py # Raw data quality checks
│   │   └── sdtm_validator.py     # CDISC SDTM compliance
│   │
│   ├── transformers/             # Transformation components
│   │   ├── mapping_generator.py  # AI mapping generation
│   │   └── domain_transformers.py # Domain-specific transforms
│   │
│   └── generators/               # Code generation
│       ├── sas_generator.py      # SAS program generation
│       └── r_generator.py        # R script generation
│
├── etl_neo4j/                    # Neo4j loader module
│   ├── __init__.py
│   └── neo4j_loader.py           # Graph database operations
│
├── sdtm_langgraph_output/        # Pipeline outputs (generated)
│
└── venv/                         # Python virtual environment
```

---

## Configuration Options

### Pipeline Flags

In `run_sdtm_langgraph.py`, you can configure:

```python
result = await run_sdtm_agent_pipeline(
    study_id="MAXIS-08",           # Study identifier
    raw_data_dir=data_dir,          # Source data directory
    output_dir=output_dir,          # Output directory
    api_key=api_key,                # Anthropic API key
    source_files=selected_files,    # Files to process
    human_decision="approve",       # Auto-approve or "reject"
    enable_human_review=True,       # Enable review checkpoints
    enable_neo4j=True,              # Enable Neo4j loading
    enable_s3=True                  # Enable S3 upload
)
```

### Disabling Features

```python
# Run without Neo4j
enable_neo4j=False

# Run without S3 upload
enable_s3=False

# Run without human review checkpoints (faster)
enable_human_review=False
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ANTHROPIC_API_KEY not set` | Add key to `.env` file |
| `Neo4j connection failed` | Ensure Docker container is running |
| `S3 upload error` | Verify AWS credentials and bucket permissions |
| `No data files found` | Check S3 bucket contains `EDC Data.zip` |
| `VS domain 0 records` | Source file may have different column names |
| `LangSmith traces not showing` | Verify `LANGCHAIN_API_KEY` is correct |

### View Logs

```bash
# Run with verbose output
python3 run_sdtm_langgraph.py 2>&1 | tee pipeline.log
```

### Check Neo4j

```bash
# Connect to Neo4j container
docker exec -it neo4j cypher-shell -u neo4j -p password123

# Count nodes
MATCH (n) RETURN labels(n)[0], count(n);
```

---

## Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| **Orchestration** | LangGraph | 0.2.x |
| **LLM** | Claude (Anthropic) | claude-sonnet-4-5-20250929 (configurable via ANTHROPIC_MODEL) |
| **Observability** | LangSmith | - |
| **Graph Database** | Neo4j | 5.27 |
| **Cloud Storage** | AWS S3 | - |
| **Language** | Python | 3.11+ |

---

## References

- [CDISC SDTM Implementation Guide](https://www.cdisc.org/standards/foundational/sdtm)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)

"""
Run SDTM Pipeline with LangGraph Agent
======================================
This script runs the complete SDTM transformation pipeline using LangGraph.

Features:
- State management with checkpointing
- Human-in-the-loop review checkpoints
- Multi-node graph execution
- Async streaming support

Usage:
    python run_sdtm_langgraph.py
"""

import asyncio
import os
import sys
import zipfile
import boto3
from datetime import datetime
from dotenv import load_dotenv

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Import LangGraph SDTM agent
from sdtm_pipeline.langgraph_agent import run_sdtm_agent_pipeline


def download_s3_data():
    """Download and extract data from S3."""
    print("\n" + "=" * 70)
    print("STEP 1: Downloading Data from S3")
    print("=" * 70)

    s3 = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    )

    bucket = os.getenv('S3_ETL_BUCKET', 's3dcri')
    download_dir = "/tmp/s3_data"
    os.makedirs(download_dir, exist_ok=True)

    # Download the zip file
    print(f"Downloading from S3 bucket: {bucket}")
    zip_path = f"{download_dir}/EDC_Data.zip"

    try:
        incoming_prefix = os.getenv('S3_INCOMING_PREFIX', 'incoming')
        s3_key = f"{incoming_prefix}/EDC Data.zip"
        s3.download_file(bucket, s3_key, zip_path)
        print(f"  Downloaded: {s3_key}")
    except Exception as e:
        print(f"  Note: Could not download from S3: {e}")
        print("  Using existing data if available...")

    # Extract
    extract_dir = f"{download_dir}/extracted"
    os.makedirs(extract_dir, exist_ok=True)

    if os.path.exists(zip_path):
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

    # Find data directory
    data_dir = f"{extract_dir}/Maxis-08 RAW DATA_CSV"

    if not os.path.exists(data_dir):
        for root, dirs, files in os.walk(extract_dir):
            if files and any(f.endswith('.csv') for f in files):
                data_dir = root
                break

    # Find all CSV files
    files = []
    if os.path.exists(data_dir):
        for filename in os.listdir(data_dir):
            if filename.endswith('.csv'):
                filepath = os.path.join(data_dir, filename)
                size_kb = os.path.getsize(filepath) / 1024
                files.append({
                    "path": filepath,
                    "name": filename,
                    "size_kb": size_kb
                })

        files.sort(key=lambda x: x['size_kb'], reverse=True)

    print(f"\nFound {len(files)} CSV files")
    return files, data_dir


def select_key_domains(files):
    """Select key clinical trial domains for SDTM transformation."""
    domain_mapping = {
        'DEMO.csv': 'DM',
        'AEVENT.csv': 'AE',
        'VITALS.csv': 'VS',
        'CHEMLAB.csv': 'LB',
        'HEMLAB.csv': 'LB',
        'CONMEDS.csv': 'CM',
    }

    selected = []
    for f in files:
        if f['name'] in domain_mapping:
            f['target_domain'] = domain_mapping[f['name']]
            selected.append(f)

    print(f"\nSelected {len(selected)} key clinical domains:")
    for f in selected:
        print(f"  - {f['name']} -> {f['target_domain']}")

    return selected


async def main():
    """Run the complete SDTM LangGraph pipeline."""
    print("\n" + "=" * 70)
    print("   CLINICAL TRIAL SDTM LANGGRAPH PIPELINE")
    print(f"   Started at: {datetime.now().isoformat()}")
    print("=" * 70)

    # Get configuration
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set!")
        return

    # Step 1: Download S3 data
    all_files, data_dir = download_s3_data()

    if not all_files:
        print("ERROR: No data files found!")
        return

    # Step 2: Select key domains
    selected_files = select_key_domains(all_files)

    # Step 3: Run SDTM LangGraph pipeline
    output_dir = os.path.join(os.path.dirname(__file__), "sdtm_langgraph_output")

    print("\n" + "=" * 70)
    print("STARTING SDTM LANGGRAPH AGENT PIPELINE")
    print("=" * 70)

    try:
        result = await run_sdtm_agent_pipeline(
            study_id="MAXIS-08",
            raw_data_dir=data_dir,
            output_dir=output_dir,
            api_key=api_key,
            source_files=selected_files,
            human_decision="approve",
            enable_human_review=True
        )

        # Print final summary
        print("\n" + "=" * 70)
        print("   SDTM LANGGRAPH PIPELINE COMPLETE")
        print("=" * 70)

        if isinstance(result, dict):
            if result.get('status') == 'success' or result.get('summary'):
                summary = result.get('summary', {})
                print(f"\nResults:")
                print(f"  Source files: {summary.get('source_files_processed', 'N/A')}")
                print(f"  SDTM domains: {summary.get('sdtm_domains_created', 'N/A')}")
                print(f"  Records transformed: {summary.get('total_sdtm_records', 'N/A')}")
                print(f"  Submission ready: {summary.get('submission_ready', 'N/A')}")

                print(f"\nOutput files:")
                print(f"  SDTM data: {output_dir}/sdtm_data/")
                print(f"  SAS programs: {output_dir}/sas_programs/")
                print(f"  R scripts: {output_dir}/r_programs/")
                print(f"  Mapping specs: {output_dir}/mapping_specs/")

                if result.get('domains'):
                    print(f"\nGenerated SDTM Domains:")
                    for domain in result.get('domains', []):
                        print(f"  - {domain.get('domain')}: from {domain.get('source')}")
            else:
                print(f"\nPipeline result: {result}")

    except Exception as e:
        print(f"\nERROR: Pipeline failed: {str(e)}")
        import traceback
        traceback.print_exc()

    print(f"\nCompleted at: {datetime.now().isoformat()}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

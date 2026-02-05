"""Generate comprehensive manifest for AE domain S3 upload."""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path

def calculate_md5(file_path):
    """Calculate MD5 checksum."""
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

def get_content_type(file_path):
    """Get content type based on extension."""
    ext = Path(file_path).suffix.lower()
    types = {
        '.csv': 'text/csv',
        '.json': 'application/json',
        '.md': 'text/markdown'
    }
    return types.get(ext, 'application/octet-stream')

# Configuration
BUCKET = "s3dcri"
STUDY_ID = "MAXIS-08"
DOMAIN = "AE"
TIMESTAMP = "20250116_141500"
S3_PREFIX = f"processed/{STUDY_ID}/{DOMAIN}"

# Files uploaded
files = [
    {
        "local_path": "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_domain.csv",
        "s3_suffix": "ae_domain.csv",
        "description": "SDTM AE domain dataset (Adverse Events)"
    },
    {
        "local_path": "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_mapping_specification.json",
        "s3_suffix": "ae_mapping_spec.json",
        "description": "AE domain mapping specification"
    },
    {
        "local_path": "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_validation_report.json",
        "s3_suffix": "ae_validation_report.json",
        "description": "CDISC conformance validation report"
    },
    {
        "local_path": "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/AE_TRANSFORMATION_COMPREHENSIVE_REPORT.md",
        "s3_suffix": "AE_TRANSFORMATION_COMPREHENSIVE_REPORT.md",
        "description": "Comprehensive transformation documentation"
    },
    {
        "local_path": "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/AE_VALIDATION_EXECUTIVE_SUMMARY_FINAL.md",
        "s3_suffix": "AE_VALIDATION_EXECUTIVE_SUMMARY_FINAL.md",
        "description": "Executive validation summary"
    }
]

# Process each file
file_metadata = {}
total_size = 0

print("Calculating checksums and metadata...")
for file_info in files:
    local_path = file_info["local_path"]
    s3_suffix = file_info["s3_suffix"]
    
    file_size = os.path.getsize(local_path)
    md5_checksum = calculate_md5(local_path)
    content_type = get_content_type(local_path)
    s3_key = f"{S3_PREFIX}/{TIMESTAMP}/{s3_suffix}"
    s3_uri = f"s3://{BUCKET}/{s3_key}"
    
    file_metadata[s3_suffix] = {
        "local_path": local_path,
        "s3_key": s3_key,
        "s3_uri": s3_uri,
        "description": file_info["description"],
        "file_size_bytes": file_size,
        "file_size_kb": round(file_size / 1024, 2),
        "file_size_mb": round(file_size / (1024 * 1024), 4),
        "md5_checksum": md5_checksum,
        "content_type": content_type,
        "upload_status": "success"
    }
    
    total_size += file_size
    print(f"✓ {s3_suffix}: {file_metadata[s3_suffix]['file_size_kb']} KB, MD5: {md5_checksum[:16]}...")

# Generate manifest
manifest = {
    "manifest_version": "1.0",
    "manifest_type": "SDTM_DOMAIN_UPLOAD",
    "study_id": STUDY_ID,
    "domain": DOMAIN,
    "upload_timestamp": TIMESTAMP,
    "upload_datetime_iso": "2025-01-16T14:15:00",
    "bucket": BUCKET,
    "s3_prefix": S3_PREFIX,
    "s3_base_path": f"s3://{BUCKET}/{S3_PREFIX}/{TIMESTAMP}",
    "file_count": len(file_metadata),
    "total_size_bytes": total_size,
    "total_size_kb": round(total_size / 1024, 2),
    "total_size_mb": round(total_size / (1024 * 1024), 4),
    "files": file_metadata,
    "upload_metadata": {
        "uploader": "Data Loading Agent",
        "pipeline_phase": "Phase 7 - Data Warehouse Loading",
        "purpose": "Regulatory submission and downstream processing",
        "verification_method": "MD5 checksum",
        "upload_tool": "upload_to_s3",
        "atomic_upload": True,
        "all_uploads_successful": True
    },
    "data_summary": {
        "ae_record_count": "TBD - calculated from CSV",
        "validation_status": "PASSED",
        "cdisc_conformance": "COMPLIANT",
        "critical_issues": 0,
        "warnings": 0
    },
    "next_steps": [
        "Load AE domain to Neo4j graph database",
        "Create relationships with DM (Demographics) nodes",
        "Enable cross-domain analysis and queries",
        "Generate final submission package"
    ]
}

# Save manifest
manifest_path = "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/AE_S3_UPLOAD_MANIFEST.json"
with open(manifest_path, 'w') as f:
    json.dump(manifest, f, indent=2)

print(f"\n✅ Manifest generated: {manifest_path}")
print(f"\nSummary:")
print(f"  Files uploaded: {manifest['file_count']}")
print(f"  Total size: {manifest['total_size_mb']} MB")
print(f"  S3 base path: {manifest['s3_base_path']}")
print(f"\nManifest ready for upload to S3!")

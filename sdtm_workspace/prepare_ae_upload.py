"""Generate upload manifest for AE domain artifacts."""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path

# File mapping
FILES_TO_UPLOAD = {
    "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_domain.csv": "ae_domain.csv",
    "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_mapping_specification.json": "ae_mapping_spec.json",
    "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_validation_report.json": "ae_validation_report.json",
    "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/AE_TRANSFORMATION_COMPREHENSIVE_REPORT.md": "AE_TRANSFORMATION_COMPREHENSIVE_REPORT.md",
    "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/AE_VALIDATION_EXECUTIVE_SUMMARY_FINAL.md": "AE_VALIDATION_EXECUTIVE_SUMMARY_FINAL.md"
}

BUCKET = "s3dcri"
STUDY_ID = "MAXIS-08"
DOMAIN = "AE"
S3_PREFIX = f"processed/{STUDY_ID}/{DOMAIN}"

def calculate_md5(file_path):
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

def get_content_type(file_path):
    ext = Path(file_path).suffix.lower()
    types = {'.csv': 'text/csv', '.json': 'application/json', '.md': 'text/markdown'}
    return types.get(ext, 'application/octet-stream')

# Generate timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Process files
file_metadata = {}
total_size = 0

print("Processing files...")
for local_path, s3_suffix in FILES_TO_UPLOAD.items():
    if not os.path.exists(local_path):
        print(f"ERROR: Missing {local_path}")
        continue
    
    file_size = os.path.getsize(local_path)
    md5_checksum = calculate_md5(local_path)
    s3_key = f"{S3_PREFIX}/{timestamp}/{s3_suffix}"
    
    file_metadata[s3_suffix] = {
        "local_path": local_path,
        "s3_key": s3_key,
        "s3_uri": f"s3://{BUCKET}/{s3_key}",
        "file_size_bytes": file_size,
        "file_size_kb": round(file_size / 1024, 2),
        "md5_checksum": md5_checksum,
        "content_type": get_content_type(local_path)
    }
    total_size += file_size
    print(f"✓ {s3_suffix}: {file_metadata[s3_suffix]['file_size_kb']} KB")

# Generate manifest
manifest = {
    "manifest_version": "1.0",
    "study_id": STUDY_ID,
    "domain": DOMAIN,
    "upload_timestamp": timestamp,
    "upload_datetime_iso": datetime.now().isoformat(),
    "bucket": BUCKET,
    "s3_prefix": S3_PREFIX,
    "s3_base_path": f"s3://{BUCKET}/{S3_PREFIX}/{timestamp}",
    "file_count": len(file_metadata),
    "total_size_bytes": total_size,
    "total_size_kb": round(total_size / 1024, 2),
    "total_size_mb": round(total_size / (1024 * 1024), 2),
    "files": file_metadata,
    "upload_metadata": {
        "uploader": "Data Loading Agent",
        "pipeline_phase": "Phase 7 - Data Warehouse Loading",
        "purpose": "Regulatory submission and downstream processing"
    }
}

# Save manifest
manifest_path = "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_s3_upload_manifest.json"
with open(manifest_path, 'w') as f:
    json.dump(manifest, f, indent=2)

print(f"\n✅ Manifest saved: {manifest_path}")
print(f"Total files: {manifest['file_count']}, Total size: {manifest['total_size_mb']} MB")
print(json.dumps(manifest, indent=2))

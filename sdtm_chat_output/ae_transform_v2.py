#!/usr/bin/env python3
"""
SDTM AE Domain Transformation - Simplified Version
Transforms AEVENT.csv to CDISC SDTM AE format
"""

import pandas as pd
import json
from datetime import datetime
from pathlib import Path

# Configuration
STUDY_ID = "MAXIS-08"
SOURCE_FILE = "/Users/siddharth/Downloads/ETL/ETL/edc_data_temp/Maxis-08 RAW DATA_CSV/AEVENT.csv"
OUTPUT_DIR = Path("/Users/siddharth/Downloads/ETL/ETL/sdtm_chat_output")

# Controlled Terminology Mappings
CT_MAPS = {
    'SEVERITY': {
        'MILD': 'MILD', 'MODERATE': 'MODERATE', 'SEVERE': 'SEVERE',
        'LIFE THREATENING': 'LIFE THREATENING', 'FATAL': 'FATAL'
    },
    'OUTCOME': {
        'RESOLVED': 'RECOVERED/RESOLVED',
        'CONTINUING': 'NOT RECOVERED/NOT RESOLVED',
        'PATIENT DIED': 'FATAL',
        'RESOLVED, WITH RESIDUAL EFFECTS': 'RECOVERED/RESOLVED WITH SEQUELAE'
    },
    'ACTION': {
        'NONE': 'DOSE NOT CHANGED',
        'INTERRUPTED': 'DRUG INTERRUPTED',
        'DISCONTINUED': 'DRUG WITHDRAWN'
    },
    'CAUSALITY': {
        'UNRELATED': 'NOT RELATED',
        'UNLIKELY': 'UNLIKELY RELATED',
        'POSSIBLE': 'POSSIBLY RELATED',
        'PROBABLE': 'PROBABLY RELATED',
        'DEFINITE': 'RELATED'
    }
}

def convert_date(date_str):
    """Convert date to ISO 8601 format"""
    if pd.isna(date_str) or str(date_str).strip() == '':
        return ''
    
    date_str = str(date_str).strip().split('.')[0]  # Remove decimals
    
    if len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
    elif len(date_str) == 6 and date_str.isdigit():
        return f"{date_str[0:4]}-{date_str[4:6]}"
    elif len(date_str) == 4 and date_str.isdigit():
        return date_str
    
    return date_str

print("Loading source data...")
try:
    df = pd.read_csv(SOURCE_FILE, encoding='utf-8-sig')
except:
    df = pd.read_csv(SOURCE_FILE, encoding='latin1')

print(f"Source records: {len(df)}")
print(f"Columns: {', '.join(df.columns.tolist()[:10])}...")

# Initialize result
ae_list = []

print("\nTransforming records...")
for idx, row in df.iterrows():
    # Extract subject ID
    subjid = str(row.get('INVSITE', '')).replace('C008_', '') if pd.notna(row.get('INVSITE')) else str(idx)
    
    # Determine seriousness
    aeserl = str(row.get('AESERL', '')).upper()
    aeser = 'Y' if 'HOSPITALIZATION' in aeserl or 'DEATH' in aeserl or 'LIFE THREATENING' in aeserl else 'N'
    
    # Seriousness flags
    aesdth = 'Y' if 'DIED' in str(row.get('AEOUTCL', '')).upper() or aeser=='1' else ''
    aeshosp = 'Y' if 'HOSPITALIZATION' in aeserl else ''
    aeslife = 'Y' if 'LIFE THREATENING' in str(row.get('AESEV', '')).upper() else ''
    
    # Build record
    ae_rec = {
        'STUDYID': STUDY_ID,
        'DOMAIN': 'AE',
        'USUBJID': f"{STUDY_ID}-{subjid}",
        'AESEQ': int(row.get('AESEQ', idx + 1)),
        'AETERM': str(row.get('AEVERB', '')).strip(),
        'AEDECOD': str(row.get('AEPTT', str(row.get('AEVERB', '')))).strip(),
        'AELLT': str(row.get('AELTT', '')).strip(),
        'AELLTCD': str(row.get('AELTC', '')).strip(),
        'AEPTCD': str(row.get('AEPTC', '')).strip(),
        'AEHLT': str(row.get('AEHTT', '')).strip(),
        'AEHLTCD': str(row.get('AEHTC', '')).strip(),
        'AEHLGT': str(row.get('AEHGT1', '')).strip(),
        'AEHLGTCD': str(row.get('AEHGC', '')).strip(),
        'AESOC': str(row.get('AESCT', '')).strip(),
        'AESOCCD': str(row.get('AESCC', '')).strip(),
        'AESTDTC': convert_date(row.get('AESTDT', '')),
        'AEENDTC': convert_date(row.get('AEENDT', '')),
        'AESEV': CT_MAPS['SEVERITY'].get(str(row.get('AESEV', '')).upper(), str(row.get('AESEV', ''))),
        'AESER': aeser,
        'AESDTH': aesdth,
        'AESHOSP': aeshosp,
        'AESLIFE': aeslife,
        'AESDISAB': '',
        'AESCONG': '',
        'AESMIE': '',
        'AEOUT': CT_MAPS['OUTCOME'].get(str(row.get('AEOUTCL', '')).upper(), str(row.get('AEOUTCL', ''))),
        'AEACN': CT_MAPS['ACTION'].get(str(row.get('AEACTL', '')).upper(), str(row.get('AEACTL', ''))),
        'AEREL': CT_MAPS['CAUSALITY'].get(str(row.get('AERELL', '')).upper(), str(row.get('AERELL', ''))),
        'AECONTRT': str(row.get('AETRT', '')).upper() if pd.notna(row.get('AETRT')) else ''
    }
    
    ae_list.append(ae_rec)

# Create DataFrame
df_ae = pd.DataFrame(ae_list)

# Save output
output_file = OUTPUT_DIR / "ae.csv"
df_ae.to_csv(output_file, index=False)

print(f"\nSDTM AE dataset saved: {output_file}")
print(f"Records created: {len(df_ae)}")
print(f"\nColumns: {', '.join(df_ae.columns.tolist())}")

# Statistics
print(f"\nSummary Statistics:")
print(f"  Severity: {df_ae['AESEV'].value_counts().to_dict()}")
print(f"  Serious (Y): {(df_ae['AESER'] == 'Y').sum()}")
print(f"  Deaths: {(df_ae['AESDTH'] == 'Y').sum()}")
print(f"  Hospitalizations: {(df_ae['AESHOSP'] == 'Y').sum()}")

# Mapping spec
spec = {
    "domain": "AE",
    "study_id": STUDY_ID,
    "date": datetime.now().isoformat(),
    "source_file": "AEVENT.csv",
    "records": len(df_ae),
    "controlled_terminology": CT_MAPS
}

spec_file = OUTPUT_DIR / "ae_mapping_specification.json"
with open(spec_file, 'w') as f:
    json.dump(spec, f, indent=2)

print(f"\nMapping specification saved: {spec_file}")
print("\n✓ Transformation complete!")

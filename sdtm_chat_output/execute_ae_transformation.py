#!/usr/bin/env python3
"""
SDTM AE Domain Transformation - Final Executable Version
Transforms AEVENT.csv to CDISC SDTM AE format following SDTM-IG 3.4
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from pathlib import Path
import sys

def main():
    # Configuration
    STUDY_ID = "MAXIS-08"
    SOURCE_FILE = "/Users/siddharth/Downloads/ETL/ETL/edc_data_temp/Maxis-08 RAW DATA_CSV/AEVENT.csv"
    OUTPUT_DIR = Path("/Users/siddharth/Downloads/ETL/ETL/sdtm_chat_output")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("SDTM AE DOMAIN TRANSFORMATION")
    print("=" * 80)
    print(f"Study ID: {STUDY_ID}")
    print(f"Source File: {SOURCE_FILE}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print()
    
    # Controlled Terminology Mappings (CDISC SDTM-IG 3.4)
    CT_SEVERITY = {
        'MILD': 'MILD',
        'MODERATE': 'MODERATE',
        'SEVERE': 'SEVERE',
        'LIFE THREATENING': 'LIFE THREATENING',
        'FATAL': 'FATAL'
    }
    
    CT_OUTCOME = {
        'RESOLVED': 'RECOVERED/RESOLVED',
        'CONTINUING': 'NOT RECOVERED/NOT RESOLVED',
        'PATIENT DIED': 'FATAL',
        'RESOLVED, WITH RESIDUAL EFFECTS': 'RECOVERED/RESOLVED WITH SEQUELAE'
    }
    
    CT_ACTION = {
        'NONE': 'DOSE NOT CHANGED',
        'INTERRUPTED': 'DRUG INTERRUPTED',
        'DISCONTINUED': 'DRUG WITHDRAWN'
    }
    
    CT_CAUSALITY = {
        'UNRELATED': 'NOT RELATED',
        'UNLIKELY': 'UNLIKELY RELATED',
        'POSSIBLE': 'POSSIBLY RELATED',
        'PROBABLE': 'PROBABLY RELATED',
        'DEFINITE': 'RELATED'
    }
    
    def convert_date_to_iso8601(date_val):
        """Convert various date formats to ISO 8601 (YYYY-MM-DD or partial)"""
        if pd.isna(date_val) or str(date_val).strip() == '':
            return ''
        
        date_str = str(date_val).strip()
        
        # Remove decimal points (Excel artifacts)
        if '.' in date_str:
            date_str = date_str.split('.')[0]
        
        # YYYYMMDD format (8 digits)
        if len(date_str) == 8 and date_str.isdigit():
            return f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
        
        # YYYYMM format (6 digits) - partial date
        elif len(date_str) == 6 and date_str.isdigit():
            return f"{date_str[0:4]}-{date_str[4:6]}"
        
        # YYYY format (4 digits) - partial date
        elif len(date_str) == 4 and date_str.isdigit():
            return date_str
        
        return date_str
    
    # Load source data
    print("Loading source data...")
    try:
        df_source = pd.read_csv(SOURCE_FILE, encoding='utf-8-sig')
    except:
        try:
            df_source = pd.read_csv(SOURCE_FILE, encoding='latin1')
        except Exception as e:
            print(f"ERROR loading file: {e}")
            return None
    
    print(f"Source records loaded: {len(df_source)}")
    print(f"Source columns: {len(df_source.columns)}")
    print()
    
    # Display first few column names
    print("Source columns (first 15):")
    for i, col in enumerate(df_source.columns[:15], 1):
        print(f"  {i}. {col}")
    print()
    
    # Transformation
    print("Transforming records to SDTM AE format...")
    ae_records = []
    data_quality_issues = []
    
    for idx, row in df_source.iterrows():
        # Extract Subject ID from INVSITE (e.g., "C008_408" -> "408")
        invsite = str(row.get('INVSITE', ''))
        if '_' in invsite:
            subjid = invsite.split('_')[1]
        else:
            subjid = str(idx + 1).zfill(3)  # Fallback
        
        usubjid = f"{STUDY_ID}-{subjid}"
        
        # Seriousness determination
        aeserl = str(row.get('AESERL', '')).upper()
        aeser = 'N'
        aesdth = ''
        aeshosp = ''
        aeslife = ''
        aesdisab = ''
        aescong = ''
        aesmie = ''
        
        # Check serious event category
        if 'HOSPITALIZATION' in aeserl or 'PROLONGATION' in aeserl:
            aeser = 'Y'
            aeshosp = 'Y'
        
        # Check for death
        aeoutcl = str(row.get('AEOUTCL', '')).upper()
        if 'DIED' in aeoutcl or 'DEATH' in aeoutcl:
            aeser = 'Y'
            aesdth = 'Y'
        
        # Check severity for life-threatening
        aesev_val = str(row.get('AESEV', '')).upper()
        if 'LIFE THREATENING' in aesev_val:
            aeser = 'Y'
            aeslife = 'Y'
        
        # Map severity
        aesev_mapped = CT_SEVERITY.get(aesev_val, aesev_val)
        
        # Map outcome
        aeout_mapped = CT_OUTCOME.get(aeoutcl, aeoutcl)
        
        # Map action taken
        aeactl = str(row.get('AEACTL', '')).upper()
        aeacn_mapped = CT_ACTION.get(aeactl, aeactl)
        
        # Map causality
        aerell = str(row.get('AERELL', '')).upper()
        aerel_mapped = CT_CAUSALITY.get(aerell, aerell)
        
        # Convert dates to ISO 8601
        aestdtc = convert_date_to_iso8601(row.get('AESTDT', ''))
        aeendtc = convert_date_to_iso8601(row.get('AEENDT', ''))
        
        # Get verbatim and preferred terms
        aeterm = str(row.get('AEVERB', '')).strip()
        aedecod = str(row.get('AEPTT', '')).strip()
        
        # If no preferred term, use verbatim
        if not aedecod or aedecod == 'nan':
            aedecod = aeterm
        
        # Data quality checks
        if not aeterm or aeterm == 'nan':
            data_quality_issues.append(f"Row {idx + 1} (AESEQ {row.get('AESEQ', '')}): Missing AETERM")
        
        if not aestdtc:
            data_quality_issues.append(f"Row {idx + 1} (AESEQ {row.get('AESEQ', '')}): Missing start date")
        
        # Build SDTM AE record
        ae_record = {
            # Required Variables
            'STUDYID': STUDY_ID,
            'DOMAIN': 'AE',
            'USUBJID': usubjid,
            'AESEQ': int(row.get('AESEQ', idx + 1)),
            
            # AE Terms (MedDRA Hierarchy)
            'AETERM': aeterm,
            'AEDECOD': aedecod,
            'AELLT': str(row.get('AELTT', '')).strip(),
            'AELLTCD': str(row.get('AELTC', '')).strip(),
            'AEPTCD': str(row.get('AEPTC', '')).strip(),
            'AEHLT': str(row.get('AEHTT', '')).strip(),
            'AEHLTCD': str(row.get('AEHTC', '')).strip(),
            'AEHLGT': str(row.get('AEHGT1', '')).strip(),
            'AEHLGTCD': str(row.get('AEHGC', '')).strip(),
            'AESOC': str(row.get('AESCT', '')).strip(),
            'AESOCCD': str(row.get('AESCC', '')).strip(),
            
            # Date/Time Variables
            'AESTDTC': aestdtc,
            'AEENDTC': aeendtc,
            
            # Severity and Seriousness
            'AESEV': aesev_mapped,
            'AESER': aeser,
            'AESDTH': aesdth,
            'AESHOSP': aeshosp,
            'AESLIFE': aeslife,
            'AESDISAB': aesdisab,
            'AESCONG': aescong,
            'AESMIE': aesmie,
            
            # Outcome and Actions
            'AEOUT': aeout_mapped,
            'AEACN': aeacn_mapped,
            'AEREL': aerel_mapped,
            
            # Concomitant Treatment Flag
            'AECONTRT': str(row.get('AETRT', '')).upper() if pd.notna(row.get('AETRT')) else ''
        }
        
        ae_records.append(ae_record)
    
    # Create DataFrame
    df_ae = pd.DataFrame(ae_records)
    
    # Reorder columns to SDTM standard order
    standard_columns = [
        'STUDYID', 'DOMAIN', 'USUBJID', 'AESEQ',
        'AETERM', 'AEDECOD', 'AELLT', 'AELLTCD', 'AEPTCD',
        'AEHLT', 'AEHLTCD', 'AEHLGT', 'AEHLGTCD', 'AESOC', 'AESOCCD',
        'AESTDTC', 'AEENDTC', 'AESEV', 'AESER',
        'AESDTH', 'AESHOSP', 'AESLIFE', 'AESDISAB', 'AESCONG', 'AESMIE',
        'AEOUT', 'AEACN', 'AEREL', 'AECONTRT'
    ]
    
    df_ae = df_ae[standard_columns]
    
    # Save SDTM AE dataset
    output_file = OUTPUT_DIR / "ae.csv"
    df_ae.to_csv(output_file, index=False)
    
    print(f"✓ SDTM AE dataset saved: {output_file}")
    print(f"  Records created: {len(df_ae)}")
    print()
    
    # Create mapping specification
    mapping_spec = {
        "domain": "AE",
        "description": "Adverse Events Domain Mapping Specification",
        "study_id": STUDY_ID,
        "source_file": "AEVENT.csv",
        "transformation_date": datetime.now().isoformat(),
        "sdtm_version": "3.4",
        "records_transformed": len(df_ae),
        
        "variable_mappings": [
            {"sdtm_var": "STUDYID", "source": "Constant", "value": STUDY_ID},
            {"sdtm_var": "DOMAIN", "source": "Constant", "value": "AE"},
            {"sdtm_var": "USUBJID", "source": "Derived", "logic": "STUDYID + '-' + SUBJID (from INVSITE)"},
            {"sdtm_var": "AESEQ", "source": "AESEQ", "transformation": "Direct"},
            {"sdtm_var": "AETERM", "source": "AEVERB", "transformation": "Direct"},
            {"sdtm_var": "AEDECOD", "source": "AEPTT", "transformation": "Dictionary-derived term"},
            {"sdtm_var": "AELLT", "source": "AELTT", "transformation": "MedDRA LLT"},
            {"sdtm_var": "AELLTCD", "source": "AELTC", "transformation": "MedDRA LLT Code"},
            {"sdtm_var": "AEPTCD", "source": "AEPTC", "transformation": "MedDRA PT Code"},
            {"sdtm_var": "AEHLT", "source": "AEHTT", "transformation": "MedDRA HLT"},
            {"sdtm_var": "AEHLTCD", "source": "AEHTC", "transformation": "MedDRA HLT Code"},
            {"sdtm_var": "AEHLGT", "source": "AEHGT1", "transformation": "MedDRA HLGT"},
            {"sdtm_var": "AEHLGTCD", "source": "AEHGC", "transformation": "MedDRA HLGT Code"},
            {"sdtm_var": "AESOC", "source": "AESCT", "transformation": "MedDRA SOC"},
            {"sdtm_var": "AESOCCD", "source": "AESCC", "transformation": "MedDRA SOC Code"},
            {"sdtm_var": "AESTDTC", "source": "AESTDT", "transformation": "ISO 8601 conversion"},
            {"sdtm_var": "AEENDTC", "source": "AEENDT", "transformation": "ISO 8601 conversion"},
            {"sdtm_var": "AESEV", "source": "AESEV", "transformation": "Controlled terminology mapping"},
            {"sdtm_var": "AESER", "source": "AESERL", "transformation": "Derived from serious event category"},
            {"sdtm_var": "AESDTH", "source": "AEOUTCL", "transformation": "Derived: Y if outcome=death"},
            {"sdtm_var": "AESHOSP", "source": "AESERL", "transformation": "Derived: Y if hospitalization"},
            {"sdtm_var": "AESLIFE", "source": "AESEV", "transformation": "Derived: Y if life-threatening"},
            {"sdtm_var": "AEOUT", "source": "AEOUTCL", "transformation": "Controlled terminology mapping"},
            {"sdtm_var": "AEACN", "source": "AEACTL", "transformation": "Controlled terminology mapping"},
            {"sdtm_var": "AEREL", "source": "AERELL", "transformation": "Controlled terminology mapping"},
            {"sdtm_var": "AECONTRT", "source": "AETRT", "transformation": "Direct"}
        ],
        
        "controlled_terminology": {
            "AESEV": CT_SEVERITY,
            "AEOUT": CT_OUTCOME,
            "AEACN": CT_ACTION,
            "AEREL": CT_CAUSALITY
        }
    }
    
    spec_file = OUTPUT_DIR / "ae_mapping_specification.json"
    with open(spec_file, 'w', encoding='utf-8') as f:
        json.dump(mapping_spec, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Mapping specification saved: {spec_file}")
    print()
    
    # Generate summary report
    print("=" * 80)
    print("TRANSFORMATION SUMMARY")
    print("=" * 80)
    print(f"Source Records Processed: {len(df_source)}")
    print(f"SDTM AE Records Created: {len(df_ae)}")
    print()
    
    print("SDTM Variables Generated:")
    print(f"  Total variables: {len(standard_columns)}")
    for col in standard_columns:
        non_empty = (df_ae[col] != '').sum()
        print(f"    {col}: {non_empty} non-empty values ({non_empty/len(df_ae)*100:.1f}%)")
    print()
    
    print("Controlled Terminology Mappings Applied:")
    print(f"\n  AESEV (Severity):")
    for val, count in df_ae['AESEV'].value_counts().items():
        if val:
            print(f"    {val}: {count}")
    
    print(f"\n  AESER (Serious Event):")
    for val, count in df_ae['AESER'].value_counts().items():
        print(f"    {val}: {count}")
    
    print(f"\n  AEOUT (Outcome):")
    for val, count in df_ae['AEOUT'].value_counts().items():
        if val:
            print(f"    {val}: {count}")
    
    print(f"\n  AEACN (Action Taken):")
    for val, count in df_ae['AEACN'].value_counts().items():
        if val:
            print(f"    {val}: {count}")
    
    print(f"\n  AEREL (Causality):")
    for val, count in df_ae['AEREL'].value_counts().items():
        if val:
            print(f"    {val}: {count}")
    print()
    
    print("Serious Event Analysis:")
    print(f"  Total Serious Events (AESER=Y): {(df_ae['AESER'] == 'Y').sum()}")
    print(f"    Deaths (AESDTH=Y): {(df_ae['AESDTH'] == 'Y').sum()}")
    print(f"    Hospitalizations (AESHOSP=Y): {(df_ae['AESHOSP'] == 'Y').sum()}")
    print(f"    Life-Threatening (AESLIFE=Y): {(df_ae['AESLIFE'] == 'Y').sum()}")
    print(f"    Disability (AESDISAB=Y): {(df_ae['AESDISAB'] == 'Y').sum()}")
    print(f"    Congenital Anomaly (AESCONG=Y): {(df_ae['AESCONG'] == 'Y').sum()}")
    print(f"    Medically Important (AESMIE=Y): {(df_ae['AESMIE'] == 'Y').sum()}")
    print()
    
    print("Date/Time Quality:")
    print(f"  Records with start date: {(df_ae['AESTDTC'] != '').sum()} ({(df_ae['AESTDTC'] != '').sum()/len(df_ae)*100:.1f}%)")
    print(f"  Records with end date: {(df_ae['AEENDTC'] != '').sum()} ({(df_ae['AEENDTC'] != '').sum()/len(df_ae)*100:.1f}%)")
    print(f"  Ongoing events (no end date): {(df_ae['AEENDTC'] == '').sum()}")
    print()
    
    if data_quality_issues:
        print("Data Quality Issues:")
        for i, issue in enumerate(data_quality_issues[:10], 1):
            print(f"  {i}. {issue}")
        if len(data_quality_issues) > 10:
            print(f"  ... and {len(data_quality_issues) - 10} more issues")
    else:
        print("✓ No data quality issues detected")
    print()
    
    print("=" * 80)
    print("✓ TRANSFORMATION COMPLETE")
    print("=" * 80)
    print()
    
    print("Output Files:")
    print(f"  1. {output_file}")
    print(f"  2. {spec_file}")
    print()
    
    print("Sample Data (First 3 records):")
    print(df_ae.head(3).to_string())
    print()
    
    return df_ae

if __name__ == "__main__":
    try:
        result = main()
        sys.exit(0 if result is not None else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

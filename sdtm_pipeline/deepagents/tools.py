"""
SDTM Pipeline Tools (Async)
===========================
Unified async tools for the SDTM Deep Agent.

All tools are async to prevent blocking the ASGI event loop in LangGraph.

Combines:
- DeepAgents-specific tools (download, scan, analyze, transform)
- SDTM Chat tools (convert_domain, validate, knowledge base, web search)

These tools are available to the main orchestrator agent (in addition to
built-in DeepAgents tools like write_todos, read_file, etc.) and provide
SDTM-specific capabilities.
"""

import os
import json
import asyncio
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime

import pandas as pd
import aiofiles
import aiofiles.os
from langchain_core.tools import tool

# Async utilities
from .async_utils import (
    async_read_csv,
    async_to_csv,
    async_write_json,
    async_makedirs,
    async_getsize,
    async_walk,
    async_s3_download,
    async_s3_upload,
)

# Mapping engine for specification-driven transformations
from .mapping_engine import (
    SDTMTransformationEngine,
    MappingSpecificationParser,
    load_mapping_spec,
    transform_with_spec,
    MappingSpecification,
)

# Import all tools from sdtm_chat
from sdtm_pipeline.langgraph_chat.tools import (
    # Data loading
    load_data_from_s3,
    list_available_domains,
    preview_source_file,
    # Conversion
    convert_domain,
    validate_domain,
    get_conversion_status,
    # Output/Storage
    upload_sdtm_to_s3,
    load_sdtm_to_neo4j,
    save_sdtm_locally,
    # Knowledge base (Pinecone)
    search_sdtm_guidelines,
    get_business_rules,
    get_mapping_specification,
    get_validation_rules,
    get_sdtm_guidance,
    search_knowledge_base,
    get_controlled_terminology,
    # SDTM-IG 3.4 Web Reference
    fetch_sdtmig_specification,
    fetch_controlled_terminology,
    get_mapping_guidance_from_web,
    # Internet search (Tavily)
    search_internet,
)


# =============================================================================
# DATA INGESTION TOOLS (Async)
# =============================================================================

@tool
async def download_edc_data(s3_bucket: str, s3_key: str, local_dir: str) -> Dict[str, Any]:
    """
    Download EDC data from S3 and extract if ZIP (async).

    Args:
        s3_bucket: S3 bucket name
        s3_key: S3 object key
        local_dir: Local directory to download to

    Returns:
        Download result with extracted file paths
    """
    import zipfile

    try:
        await async_makedirs(local_dir)
        local_path = os.path.join(local_dir, os.path.basename(s3_key))

        # Download from S3 (async)
        await async_s3_download(s3_bucket, s3_key, local_path)

        files = []

        # Extract if ZIP (run in thread since zipfile is blocking)
        if local_path.endswith('.zip'):
            extract_dir = os.path.join(local_dir, 'extracted')
            await async_makedirs(extract_dir)

            def _extract_and_scan():
                with zipfile.ZipFile(local_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)

                result_files = []
                for root, dirs, filenames in os.walk(extract_dir):
                    for filename in filenames:
                        if filename.endswith('.csv'):
                            filepath = os.path.join(root, filename)
                            size_kb = os.path.getsize(filepath) / 1024
                            result_files.append({
                                "name": filename,
                                "path": filepath,
                                "size_kb": round(size_kb, 2),
                            })
                return result_files

            files = await asyncio.to_thread(_extract_and_scan)
        else:
            size = await async_getsize(local_path)
            files.append({
                "name": os.path.basename(local_path),
                "path": local_path,
                "size_kb": round(size / 1024, 2),
            })

        return {
            "success": True,
            "files": files,
            "count": len(files),
            "download_path": local_path,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
async def scan_source_files(directory: str) -> Dict[str, Any]:
    """
    Scan directory for source data files and determine SDTM domain mappings (async).

    Args:
        directory: Directory to scan

    Returns:
        List of files with suggested SDTM domain mappings
    """
    # Domain mapping patterns for all 63 SDTM domains
    domain_patterns = {
        # Special Purpose Domains
        'COMMENT': 'CO', 'CO': 'CO',
        'DEMO': 'DM', 'DEMOGRAPHY': 'DM', 'DM': 'DM', 'DEMOGRAPHICS': 'DM',
        'SUBJELEM': 'SE', 'SE': 'SE', 'ELEMENT': 'SE',
        'SUBJVISIT': 'SV', 'SV': 'SV', 'VISIT': 'SV',

        # Interventions Domains
        'AGENT': 'AG', 'AG': 'AG', 'PROCAGENT': 'AG',
        'CONMEDS': 'CM', 'CM': 'CM', 'MEDICATION': 'CM', 'CONMED': 'CM',
        'EXPCOLL': 'EC', 'EC': 'EC', 'EXPOCOLL': 'EC',
        'DOSE': 'EX', 'EXPOSURE': 'EX', 'EX': 'EX', 'DOSING': 'EX',
        'MEAL': 'ML', 'ML': 'ML', 'MEALS': 'ML',
        'PROCEDURE': 'PR', 'PR': 'PR', 'PROC': 'PR',
        'SUBUSE': 'SU', 'SU': 'SU', 'SUBSTANCE': 'SU', 'ALCOHOL': 'SU', 'TOBACCO': 'SU',

        # Events Domains
        'AEVENT': 'AE', 'AE': 'AE', 'ADVERSE': 'AE', 'ADVERSEEVENT': 'AE',
        'CLNEVENT': 'CE', 'CE': 'CE', 'CLINICAL': 'CE',
        'CMPL': 'DS', 'DISPOSITION': 'DS', 'DS': 'DS', 'DISP': 'DS',
        'DEVIATION': 'DV', 'DV': 'DV', 'PROTDEV': 'DV',
        'HEALTHCARE': 'HO', 'HO': 'HO', 'ENCOUNTER': 'HO',
        'GMEDHX': 'MH', 'MEDHIST': 'MH', 'MH': 'MH', 'MEDHX': 'MH', 'SURGHX': 'MH',

        # Findings Domains
        'BIOSPECEVENT': 'BE', 'BE': 'BE',
        'BONEMEAS': 'BM', 'BM': 'BM', 'BONE': 'BM', 'DEXA': 'BM',
        'BIOSPECFIND': 'BS', 'BS': 'BS',
        'CELLPHENO': 'CP', 'CP': 'CP',
        'CARDIO': 'CV', 'CV': 'CV', 'CARDIOVASC': 'CV',
        'DRUGACCT': 'DA', 'DA': 'DA', 'ACCOUNTABILITY': 'DA',
        'DEATHDET': 'DD', 'DD': 'DD', 'DEATH': 'DD', 'DEATHGEN': 'DD',
        'ECG': 'EG', 'EG': 'EG', 'ELECTROCARD': 'EG',
        'FINDABOUT': 'FA', 'FA': 'FA',
        'FUNCTEST': 'FT', 'FT': 'FT', 'FUNCTION': 'FT',
        'GENOMICS': 'GF', 'GF': 'GF', 'GENO': 'GF', 'GENOLAB': 'GF',
        'IETEST': 'IE', 'IE': 'IE', 'INCEXC': 'IE', 'ELIG': 'IE', 'INEXCRT': 'IE',
        'IMMUNOGEN': 'IS', 'IS': 'IS',
        'CHEMLAB': 'LB', 'HEMLAB': 'LB', 'LAB': 'LB', 'URINLAB': 'LB', 'LB': 'LB', 'BIOLAB': 'LB',
        'MICROBIO': 'MB', 'MB': 'MB', 'MICROSPEC': 'MB',
        'MICROSCOP': 'MI', 'MI': 'MI',
        'MUSCULO': 'MK', 'MK': 'MK', 'MUSCULOSKEL': 'MK',
        'MORPHO': 'MO', 'MO': 'MO', 'MORPHOLOGY': 'MO',
        'MICROSUSCEP': 'MS', 'MS': 'MS', 'SUSCEPT': 'MS',
        'NERVOUS': 'NV', 'NV': 'NV', 'NEURO': 'NV',
        'OPHTHALM': 'OE', 'OE': 'OE', 'EYE': 'OE', 'OPHTHALMIC': 'OE',
        'OXYGEN': 'OX', 'OX': 'OX', 'O2SAT': 'OX', 'SPO2': 'OX',
        'PKCRF': 'PC', 'PC': 'PC', 'PKCONC': 'PC', 'PHARMACOKINETIC': 'PC',
        'PHYSEXAM': 'PE', 'PE': 'PE', 'PHYSICAL': 'PE',
        'PRINVINV': 'PI', 'PI': 'PI',
        'PKPARAM': 'PP', 'PP': 'PP',
        'QUEST': 'QS', 'QS': 'QS', 'QUESTIONNAIRE': 'QS', 'QSQS': 'QS',
        'RESP': 'RE', 'RE': 'RE', 'RESPIRATORY': 'RE',
        'REPRO': 'RP', 'RP': 'RP', 'REPRODUCTIVE': 'RP',
        'RESPONSE': 'RS', 'RS': 'RS', 'DISEASERESPONSE': 'RS',
        'SUBJCHAR': 'SC', 'SC': 'SC', 'CHARACTERISTIC': 'SC',
        'SKIN': 'SK', 'SK': 'SK',
        'SUBJSTAT': 'SS', 'SS': 'SS', 'STATUS': 'SS',
        'TUMOR': 'TR', 'TR': 'TR', 'LESION': 'TR', 'TUMR': 'TR', 'TARTUMR': 'TR', 'NONTUMR': 'TR',
        'TUMORID': 'TU', 'TU': 'TU',
        'URINARY': 'UR', 'UR': 'UR',
        'VITALS': 'VS', 'VS': 'VS', 'VITAL': 'VS', 'VITALSIGN': 'VS',

        # Trial Design Domains
        'TRIALARM': 'TA', 'TA': 'TA', 'ARM': 'TA',
        'TRIALDISEASE': 'TD', 'TD': 'TD',
        'TRIALELEMENT': 'TE', 'TE': 'TE',
        'TRIALINEXC': 'TI', 'TI': 'TI',
        'TRIALMILESTONE': 'TM', 'TM': 'TM',
        'TRIALSUMM': 'TS', 'TS': 'TS', 'SUMMARY': 'TS',
        'TRIALVISIT': 'TV', 'TV': 'TV',

        # Device Domains
        'DEVICEID': 'DI', 'DI': 'DI',
        'DEVICEPROP': 'DO', 'DO': 'DO',
        'DEVICEREL': 'DR', 'DR': 'DR',
        'DEVICEEVENT': 'DX', 'DX': 'DX',

        # Relationship Domain
        'RELREC': 'RELREC', 'RELATEDRECORDS': 'RELREC',
    }

    files = []
    try:
        # Use async walk
        walk_results = await async_walk(directory)

        for root, dirs, filenames in walk_results:
            for filename in filenames:
                if filename.endswith('.csv'):
                    filepath = os.path.join(root, filename)
                    size = await async_getsize(filepath)
                    size_kb = size / 1024

                    # Determine target domain
                    base_name = filename.upper().replace('.CSV', '')
                    target_domain = None
                    for pattern, domain in domain_patterns.items():
                        if pattern in base_name:
                            target_domain = domain
                            break

                    files.append({
                        "name": filename,
                        "path": filepath,
                        "size_kb": round(size_kb, 2),
                        "target_domain": target_domain,
                        "mapped": target_domain is not None,
                    })

        # Sort by size (largest first)
        files.sort(key=lambda x: x['size_kb'], reverse=True)

        mapped = [f for f in files if f['mapped']]
        unmapped = [f for f in files if not f['mapped']]

        return {
            "success": True,
            "total_files": len(files),
            "mapped_files": len(mapped),
            "unmapped_files": len(unmapped),
            "files": files,
            "domains_found": list(set(f['target_domain'] for f in mapped if f['target_domain'])),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
async def analyze_source_file(file_path: str) -> Dict[str, Any]:
    """
    Analyze a source data file to understand its structure (async).

    Args:
        file_path: Path to the CSV file

    Returns:
        File analysis with column info and sample data
    """
    try:
        # Async CSV read
        df = await async_read_csv(file_path)

        columns = []
        for col in df.columns:
            col_info = {
                "name": col,
                "dtype": str(df[col].dtype),
                "non_null": int(df[col].notna().sum()),
                "null_count": int(df[col].isna().sum()),
                "unique_values": int(df[col].nunique()),
                "sample_values": [str(v) for v in df[col].dropna().head(3).tolist()],
            }
            columns.append(col_info)

        return {
            "success": True,
            "file_name": os.path.basename(file_path),
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": columns,
            "memory_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# SDTM VARIABLE DEFINITIONS (Labels & Descriptions for Intelligent Mapping)
# =============================================================================

SDTM_VARIABLE_DEFINITIONS = {
    "DM": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "SUBJID": {"label": "Subject Identifier for the Study", "type": "Char", "core": "Req"},
        "RFSTDTC": {"label": "Subject Reference Start Date/Time", "type": "Char", "core": "Exp"},
        "RFENDTC": {"label": "Subject Reference End Date/Time", "type": "Char", "core": "Exp"},
        "RFXSTDTC": {"label": "Date/Time of First Study Treatment", "type": "Char", "core": "Exp"},
        "RFXENDTC": {"label": "Date/Time of Last Study Treatment", "type": "Char", "core": "Exp"},
        "RFICDTC": {"label": "Date/Time of Informed Consent", "type": "Char", "core": "Perm"},
        "RFPENDTC": {"label": "Date/Time of End of Participation", "type": "Char", "core": "Perm"},
        "DTHDTC": {"label": "Date/Time of Death", "type": "Char", "core": "Perm"},
        "DTHFL": {"label": "Subject Death Flag", "type": "Char", "core": "Perm"},
        "SITEID": {"label": "Study Site Identifier", "type": "Char", "core": "Req"},
        "INVID": {"label": "Investigator Identifier", "type": "Char", "core": "Perm"},
        "INVNAM": {"label": "Investigator Name", "type": "Char", "core": "Perm"},
        "BRTHDTC": {"label": "Date/Time of Birth", "type": "Char", "core": "Perm"},
        "AGE": {"label": "Age", "type": "Num", "core": "Exp"},
        "AGEU": {"label": "Age Units", "type": "Char", "core": "Exp"},
        "SEX": {"label": "Sex", "type": "Char", "core": "Req"},
        "RACE": {"label": "Race", "type": "Char", "core": "Exp"},
        "ETHNIC": {"label": "Ethnicity", "type": "Char", "core": "Perm"},
        "ARMCD": {"label": "Planned Arm Code", "type": "Char", "core": "Req"},
        "ARM": {"label": "Description of Planned Arm", "type": "Char", "core": "Req"},
        "ACTARMCD": {"label": "Actual Arm Code", "type": "Char", "core": "Perm"},
        "ACTARM": {"label": "Description of Actual Arm", "type": "Char", "core": "Perm"},
        "COUNTRY": {"label": "Country", "type": "Char", "core": "Req"},
        "DMDTC": {"label": "Date/Time of Collection", "type": "Char", "core": "Perm"},
        "DMDY": {"label": "Study Day of Collection", "type": "Num", "core": "Perm"},
    },
    "AE": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "AESEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "AESPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "AETERM": {"label": "Reported Term for the Adverse Event", "type": "Char", "core": "Req"},
        "AEMODIFY": {"label": "Modified Reported Term", "type": "Char", "core": "Perm"},
        "AEDECOD": {"label": "Dictionary-Derived Term", "type": "Char", "core": "Req"},
        "AELLT": {"label": "Lowest Level Term", "type": "Char", "core": "Perm"},
        "AELLTCD": {"label": "Lowest Level Term Code", "type": "Num", "core": "Perm"},
        "AEPTCD": {"label": "Preferred Term Code", "type": "Num", "core": "Perm"},
        "AEHLT": {"label": "High Level Term", "type": "Char", "core": "Perm"},
        "AEHLTCD": {"label": "High Level Term Code", "type": "Num", "core": "Perm"},
        "AEHLGT": {"label": "High Level Group Term", "type": "Char", "core": "Perm"},
        "AEHLGTCD": {"label": "High Level Group Term Code", "type": "Num", "core": "Perm"},
        "AEBODSYS": {"label": "Body System or Organ Class", "type": "Char", "core": "Exp"},
        "AEBDSYCD": {"label": "Body System or Organ Class Code", "type": "Num", "core": "Perm"},
        "AESOC": {"label": "Primary System Organ Class", "type": "Char", "core": "Perm"},
        "AESOCCD": {"label": "Primary System Organ Class Code", "type": "Num", "core": "Perm"},
        "AECAT": {"label": "Category for Adverse Event", "type": "Char", "core": "Perm"},
        "AESCAT": {"label": "Subcategory for Adverse Event", "type": "Char", "core": "Perm"},
        "AEPRESP": {"label": "Pre-Specified Adverse Event", "type": "Char", "core": "Perm"},
        "AEBODSYS": {"label": "Body System or Organ Class", "type": "Char", "core": "Exp"},
        "AESEV": {"label": "Severity/Intensity", "type": "Char", "core": "Perm"},
        "AETOXGR": {"label": "Standard Toxicity Grade", "type": "Char", "core": "Perm"},
        "AESER": {"label": "Serious Event", "type": "Char", "core": "Exp"},
        "AEACN": {"label": "Action Taken with Study Treatment", "type": "Char", "core": "Exp"},
        "AEACNOTH": {"label": "Other Action Taken", "type": "Char", "core": "Perm"},
        "AEREL": {"label": "Causality", "type": "Char", "core": "Exp"},
        "AEPATT": {"label": "Pattern of Adverse Event", "type": "Char", "core": "Perm"},
        "AEOUT": {"label": "Outcome of Adverse Event", "type": "Char", "core": "Exp"},
        "AESCAN": {"label": "Involves Cancer", "type": "Char", "core": "Perm"},
        "AESCONG": {"label": "Congenital Anomaly or Birth Defect", "type": "Char", "core": "Perm"},
        "AESDISAB": {"label": "Persist or Signif Disability/Incapacity", "type": "Char", "core": "Perm"},
        "AESDTH": {"label": "Results in Death", "type": "Char", "core": "Perm"},
        "AESHOSP": {"label": "Requires or Prolongs Hospitalization", "type": "Char", "core": "Perm"},
        "AESLIFE": {"label": "Is Life Threatening", "type": "Char", "core": "Perm"},
        "AESMIE": {"label": "Other Medically Important Serious Event", "type": "Char", "core": "Perm"},
        "AECONTRT": {"label": "Concomitant or Additional Trtmnt Given", "type": "Char", "core": "Perm"},
        "AESTDTC": {"label": "Start Date/Time of Adverse Event", "type": "Char", "core": "Exp"},
        "AEENDTC": {"label": "End Date/Time of Adverse Event", "type": "Char", "core": "Exp"},
        "AESTDY": {"label": "Study Day of Start of Adverse Event", "type": "Num", "core": "Perm"},
        "AEENDY": {"label": "Study Day of End of Adverse Event", "type": "Num", "core": "Perm"},
        "AEDUR": {"label": "Duration of Adverse Event", "type": "Char", "core": "Perm"},
        "AEENRF": {"label": "End Relative to Reference Period", "type": "Char", "core": "Perm"},
        "AESTRF": {"label": "Start Relative to Reference Period", "type": "Char", "core": "Perm"},
    },
    "CM": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "CMSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "CMSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "CMTRT": {"label": "Reported Name of Drug, Med, or Therapy", "type": "Char", "core": "Req"},
        "CMMODIFY": {"label": "Modified Reported Name", "type": "Char", "core": "Perm"},
        "CMDECOD": {"label": "Standardized Medication Name", "type": "Char", "core": "Perm"},
        "CMCAT": {"label": "Category for Medication", "type": "Char", "core": "Perm"},
        "CMSCAT": {"label": "Subcategory for Medication", "type": "Char", "core": "Perm"},
        "CMPRESP": {"label": "Pre-Specified", "type": "Char", "core": "Perm"},
        "CMOCCUR": {"label": "Occurrence", "type": "Char", "core": "Perm"},
        "CMINDC": {"label": "Indication", "type": "Char", "core": "Exp"},
        "CMCLAS": {"label": "Medication Class", "type": "Char", "core": "Perm"},
        "CMCLASCD": {"label": "Medication Class Code", "type": "Char", "core": "Perm"},
        "CMDOSE": {"label": "Dose per Administration", "type": "Num", "core": "Exp"},
        "CMDOSTXT": {"label": "Dose Description", "type": "Char", "core": "Perm"},
        "CMDOSU": {"label": "Dose Units", "type": "Char", "core": "Exp"},
        "CMDOSFRM": {"label": "Dose Form", "type": "Char", "core": "Perm"},
        "CMDOSFRQ": {"label": "Dosing Frequency per Interval", "type": "Char", "core": "Exp"},
        "CMDOSTOT": {"label": "Total Daily Dose", "type": "Num", "core": "Perm"},
        "CMROUTE": {"label": "Route of Administration", "type": "Char", "core": "Perm"},
        "CMSTDTC": {"label": "Start Date/Time of Medication", "type": "Char", "core": "Exp"},
        "CMENDTC": {"label": "End Date/Time of Medication", "type": "Char", "core": "Exp"},
        "CMSTDY": {"label": "Study Day of Start of Medication", "type": "Num", "core": "Perm"},
        "CMENDY": {"label": "Study Day of End of Medication", "type": "Num", "core": "Perm"},
        "CMDUR": {"label": "Duration of Medication", "type": "Char", "core": "Perm"},
        "CMSTRF": {"label": "Start Relative to Reference Period", "type": "Char", "core": "Perm"},
        "CMENRF": {"label": "End Relative to Reference Period", "type": "Char", "core": "Perm"},
    },
    "VS": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "VSSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "VSSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "VSTESTCD": {"label": "Vital Signs Test Short Name", "type": "Char", "core": "Req"},
        "VSTEST": {"label": "Vital Signs Test Name", "type": "Char", "core": "Req"},
        "VSCAT": {"label": "Category for Vital Signs", "type": "Char", "core": "Perm"},
        "VSSCAT": {"label": "Subcategory for Vital Signs", "type": "Char", "core": "Perm"},
        "VSPOS": {"label": "Vital Signs Position of Subject", "type": "Char", "core": "Perm"},
        "VSORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "VSORRESU": {"label": "Original Units", "type": "Char", "core": "Exp"},
        "VSSTRESC": {"label": "Character Result/Finding in Std Format", "type": "Char", "core": "Exp"},
        "VSSTRESN": {"label": "Numeric Result/Finding in Std Units", "type": "Num", "core": "Exp"},
        "VSSTRESU": {"label": "Standard Units", "type": "Char", "core": "Exp"},
        "VSSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "VSREASND": {"label": "Reason Not Performed", "type": "Char", "core": "Perm"},
        "VSLOC": {"label": "Location of Vital Signs Measurement", "type": "Char", "core": "Perm"},
        "VSBLFL": {"label": "Baseline Flag", "type": "Char", "core": "Perm"},
        "VSDRVFL": {"label": "Derived Flag", "type": "Char", "core": "Perm"},
        "VISITNUM": {"label": "Visit Number", "type": "Num", "core": "Exp"},
        "VISIT": {"label": "Visit Name", "type": "Char", "core": "Perm"},
        "VSDTC": {"label": "Date/Time of Measurements", "type": "Char", "core": "Exp"},
        "VSDY": {"label": "Study Day of Vital Signs", "type": "Num", "core": "Perm"},
        "VSTPT": {"label": "Planned Time Point Name", "type": "Char", "core": "Perm"},
        "VSTPTNUM": {"label": "Planned Time Point Number", "type": "Num", "core": "Perm"},
        "VSELTM": {"label": "Planned Elapsed Time from Ref Point", "type": "Char", "core": "Perm"},
        "VSTPTREF": {"label": "Time Point Reference", "type": "Char", "core": "Perm"},
    },
    "LB": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "LBSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "LBSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "LBTESTCD": {"label": "Lab Test or Examination Short Name", "type": "Char", "core": "Req"},
        "LBTEST": {"label": "Lab Test or Examination Name", "type": "Char", "core": "Req"},
        "LBCAT": {"label": "Category for Lab Test", "type": "Char", "core": "Perm"},
        "LBSCAT": {"label": "Subcategory for Lab Test", "type": "Char", "core": "Perm"},
        "LBORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "LBORRESU": {"label": "Original Units", "type": "Char", "core": "Exp"},
        "LBORNRLO": {"label": "Reference Range Lower Limit in Orig Unit", "type": "Char", "core": "Perm"},
        "LBORNRHI": {"label": "Reference Range Upper Limit in Orig Unit", "type": "Char", "core": "Perm"},
        "LBSTRESC": {"label": "Character Result/Finding in Std Format", "type": "Char", "core": "Exp"},
        "LBSTRESN": {"label": "Numeric Result/Finding in Std Units", "type": "Num", "core": "Exp"},
        "LBSTRESU": {"label": "Standard Units", "type": "Char", "core": "Exp"},
        "LBSTNRLO": {"label": "Reference Range Lower Limit-Std Units", "type": "Num", "core": "Perm"},
        "LBSTNRHI": {"label": "Reference Range Upper Limit-Std Units", "type": "Num", "core": "Perm"},
        "LBNRIND": {"label": "Reference Range Indicator", "type": "Char", "core": "Exp"},
        "LBSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "LBREASND": {"label": "Reason Not Performed", "type": "Char", "core": "Perm"},
        "LBNAM": {"label": "Vendor Name", "type": "Char", "core": "Perm"},
        "LBLOINC": {"label": "LOINC Code", "type": "Char", "core": "Perm"},
        "LBSPEC": {"label": "Specimen Type", "type": "Char", "core": "Perm"},
        "LBSPCCND": {"label": "Specimen Condition", "type": "Char", "core": "Perm"},
        "LBMETHOD": {"label": "Method of Test or Examination", "type": "Char", "core": "Perm"},
        "LBBLFL": {"label": "Baseline Flag", "type": "Char", "core": "Perm"},
        "LBFAST": {"label": "Fasting Status", "type": "Char", "core": "Perm"},
        "VISITNUM": {"label": "Visit Number", "type": "Num", "core": "Exp"},
        "VISIT": {"label": "Visit Name", "type": "Char", "core": "Perm"},
        "LBDTC": {"label": "Date/Time of Specimen Collection", "type": "Char", "core": "Exp"},
        "LBDY": {"label": "Study Day of Specimen Collection", "type": "Num", "core": "Perm"},
        "LBTPT": {"label": "Planned Time Point Name", "type": "Char", "core": "Perm"},
    },
    "EX": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "EXSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "EXSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "EXTRT": {"label": "Name of Treatment", "type": "Char", "core": "Req"},
        "EXCAT": {"label": "Category of Treatment", "type": "Char", "core": "Perm"},
        "EXSCAT": {"label": "Subcategory of Treatment", "type": "Char", "core": "Perm"},
        "EXDOSE": {"label": "Dose", "type": "Num", "core": "Exp"},
        "EXDOSTXT": {"label": "Dose Description", "type": "Char", "core": "Perm"},
        "EXDOSU": {"label": "Dose Units", "type": "Char", "core": "Exp"},
        "EXDOSFRM": {"label": "Dose Form", "type": "Char", "core": "Exp"},
        "EXDOSFRQ": {"label": "Dosing Frequency per Interval", "type": "Char", "core": "Perm"},
        "EXDOSTOT": {"label": "Total Daily Dose", "type": "Num", "core": "Perm"},
        "EXROUTE": {"label": "Route of Administration", "type": "Char", "core": "Exp"},
        "EXLOT": {"label": "Lot Number", "type": "Char", "core": "Perm"},
        "EXLOC": {"label": "Location of Dose Administration", "type": "Char", "core": "Perm"},
        "EXLAT": {"label": "Laterality", "type": "Char", "core": "Perm"},
        "EXFAST": {"label": "Fasting Status", "type": "Char", "core": "Perm"},
        "EXADJ": {"label": "Reason for Dose Adjustment", "type": "Char", "core": "Perm"},
        "EPOCH": {"label": "Epoch", "type": "Char", "core": "Perm"},
        "EXSTDTC": {"label": "Start Date/Time of Treatment", "type": "Char", "core": "Exp"},
        "EXENDTC": {"label": "End Date/Time of Treatment", "type": "Char", "core": "Exp"},
        "EXSTDY": {"label": "Study Day of Start of Treatment", "type": "Num", "core": "Perm"},
        "EXENDY": {"label": "Study Day of End of Treatment", "type": "Num", "core": "Perm"},
        "EXDUR": {"label": "Duration of Treatment", "type": "Char", "core": "Perm"},
    },
    "MH": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "MHSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "MHSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "MHTERM": {"label": "Reported Term for the Medical History", "type": "Char", "core": "Req"},
        "MHMODIFY": {"label": "Modified Reported Term", "type": "Char", "core": "Perm"},
        "MHDECOD": {"label": "Dictionary-Derived Term", "type": "Char", "core": "Perm"},
        "MHCAT": {"label": "Category for Medical History", "type": "Char", "core": "Perm"},
        "MHSCAT": {"label": "Subcategory for Medical History", "type": "Char", "core": "Perm"},
        "MHPRESP": {"label": "Pre-Specified", "type": "Char", "core": "Perm"},
        "MHOCCUR": {"label": "Occurrence", "type": "Char", "core": "Perm"},
        "MHBODSYS": {"label": "Body System or Organ Class", "type": "Char", "core": "Perm"},
        "MHSEV": {"label": "Severity/Intensity", "type": "Char", "core": "Perm"},
        "VISITNUM": {"label": "Visit Number", "type": "Num", "core": "Perm"},
        "VISIT": {"label": "Visit Name", "type": "Char", "core": "Perm"},
        "MHSTDTC": {"label": "Start Date/Time of Medical History Event", "type": "Char", "core": "Perm"},
        "MHENDTC": {"label": "End Date/Time of Medical History Event", "type": "Char", "core": "Perm"},
        "MHSTDY": {"label": "Study Day of Start of Medical History", "type": "Num", "core": "Perm"},
        "MHENDY": {"label": "Study Day of End of Medical History", "type": "Num", "core": "Perm"},
        "MHDUR": {"label": "Duration of Medical History Event", "type": "Char", "core": "Perm"},
        "MHENRF": {"label": "End Relative to Reference Period", "type": "Char", "core": "Perm"},
        "MHSTRF": {"label": "Start Relative to Reference Period", "type": "Char", "core": "Perm"},
    },
    "DS": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "DSSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "DSSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "DSTERM": {"label": "Reported Term for the Disposition Event", "type": "Char", "core": "Req"},
        "DSDECOD": {"label": "Standardized Disposition Term", "type": "Char", "core": "Req"},
        "DSCAT": {"label": "Category for Disposition Event", "type": "Char", "core": "Exp"},
        "DSSCAT": {"label": "Subcategory for Disposition Event", "type": "Char", "core": "Perm"},
        "EPOCH": {"label": "Epoch", "type": "Char", "core": "Perm"},
        "DSSTDTC": {"label": "Start Date/Time of Disposition Event", "type": "Char", "core": "Exp"},
        "DSSTDY": {"label": "Study Day of Start of Disposition Event", "type": "Num", "core": "Perm"},
    },
    "EG": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "EGSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "EGTESTCD": {"label": "ECG Test or Examination Short Name", "type": "Char", "core": "Req"},
        "EGTEST": {"label": "ECG Test or Examination Name", "type": "Char", "core": "Req"},
        "EGCAT": {"label": "Category for ECG", "type": "Char", "core": "Perm"},
        "EGORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "EGORRESU": {"label": "Original Units", "type": "Char", "core": "Exp"},
        "EGSTRESC": {"label": "Character Result/Finding in Std Format", "type": "Char", "core": "Exp"},
        "EGSTRESN": {"label": "Numeric Result/Finding in Std Units", "type": "Num", "core": "Exp"},
        "EGSTRESU": {"label": "Standard Units", "type": "Char", "core": "Exp"},
        "EGSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "EGREASND": {"label": "Reason Not Performed", "type": "Char", "core": "Perm"},
        "EGXFN": {"label": "ECG External File Name", "type": "Char", "core": "Perm"},
        "EGNAM": {"label": "Vendor Name", "type": "Char", "core": "Perm"},
        "EGLEAD": {"label": "Lead Location Used for Measurement", "type": "Char", "core": "Perm"},
        "EGMETHOD": {"label": "Method of ECG Test", "type": "Char", "core": "Perm"},
        "EGBLFL": {"label": "Baseline Flag", "type": "Char", "core": "Perm"},
        "EGEVAL": {"label": "Evaluator", "type": "Char", "core": "Perm"},
        "VISITNUM": {"label": "Visit Number", "type": "Num", "core": "Exp"},
        "VISIT": {"label": "Visit Name", "type": "Char", "core": "Perm"},
        "EGDTC": {"label": "Date/Time of ECG", "type": "Char", "core": "Exp"},
        "EGDY": {"label": "Study Day of ECG", "type": "Num", "core": "Perm"},
        "EGTPT": {"label": "Planned Time Point Name", "type": "Char", "core": "Perm"},
    },
    "PE": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "PESEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "PETESTCD": {"label": "Body System Examined Short Name", "type": "Char", "core": "Req"},
        "PETEST": {"label": "Body System Examined", "type": "Char", "core": "Req"},
        "PECAT": {"label": "Category for Physical Examination", "type": "Char", "core": "Perm"},
        "PEBODSYS": {"label": "Body System or Organ Class", "type": "Char", "core": "Perm"},
        "PEORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "PESTRESC": {"label": "Character Result/Finding in Std Format", "type": "Char", "core": "Exp"},
        "PESTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "PEREASND": {"label": "Reason Not Performed", "type": "Char", "core": "Perm"},
        "PELOC": {"label": "Location of a Finding", "type": "Char", "core": "Perm"},
        "PELAT": {"label": "Laterality", "type": "Char", "core": "Perm"},
        "VISITNUM": {"label": "Visit Number", "type": "Num", "core": "Exp"},
        "VISIT": {"label": "Visit Name", "type": "Char", "core": "Perm"},
        "PEDTC": {"label": "Date/Time of Physical Examination", "type": "Char", "core": "Exp"},
        "PEDY": {"label": "Study Day of Physical Examination", "type": "Num", "core": "Perm"},
    },
    "PC": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "PCSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "PCTESTCD": {"label": "Pharmacokinetic Test Short Name", "type": "Char", "core": "Req"},
        "PCTEST": {"label": "Pharmacokinetic Test Name", "type": "Char", "core": "Req"},
        "PCCAT": {"label": "Category for PK Concentration", "type": "Char", "core": "Perm"},
        "PCORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "PCORRESU": {"label": "Original Units", "type": "Char", "core": "Exp"},
        "PCSTRESC": {"label": "Character Result/Finding in Std Format", "type": "Char", "core": "Exp"},
        "PCSTRESN": {"label": "Numeric Result/Finding in Std Units", "type": "Num", "core": "Exp"},
        "PCSTRESU": {"label": "Standard Units", "type": "Char", "core": "Exp"},
        "PCSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "PCREASND": {"label": "Reason Not Performed", "type": "Char", "core": "Perm"},
        "PCSPEC": {"label": "Specimen Material Type", "type": "Char", "core": "Exp"},
        "PCMETHOD": {"label": "Method of Test or Examination", "type": "Char", "core": "Perm"},
        "VISITNUM": {"label": "Visit Number", "type": "Num", "core": "Exp"},
        "VISIT": {"label": "Visit Name", "type": "Char", "core": "Perm"},
        "PCDTC": {"label": "Date/Time of Specimen Collection", "type": "Char", "core": "Exp"},
        "PCDY": {"label": "Study Day of Specimen Collection", "type": "Num", "core": "Perm"},
        "PCTPT": {"label": "Planned Time Point Name", "type": "Char", "core": "Exp"},
        "PCTPTNUM": {"label": "Planned Time Point Number", "type": "Num", "core": "Perm"},
        "PCELTM": {"label": "Planned Elapsed Time from Time Point Ref", "type": "Char", "core": "Perm"},
    },
    # =========================================================================
    # PP - Pharmacokinetic Parameters
    # =========================================================================
    "PP": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "PPSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "PPGRPID": {"label": "Group ID", "type": "Char", "core": "Perm"},
        "PPTESTCD": {"label": "Parameter Short Name", "type": "Char", "core": "Req"},
        "PPTEST": {"label": "Parameter Name", "type": "Char", "core": "Req"},
        "PPCAT": {"label": "Parameter Category", "type": "Char", "core": "Perm"},
        "PPSCAT": {"label": "Parameter Subcategory", "type": "Char", "core": "Perm"},
        "PPORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "PPORRESU": {"label": "Original Units", "type": "Char", "core": "Exp"},
        "PPSTRESC": {"label": "Character Result/Finding in Std Format", "type": "Char", "core": "Exp"},
        "PPSTRESN": {"label": "Numeric Result/Finding in Standard Units", "type": "Num", "core": "Exp"},
        "PPSTRESU": {"label": "Standard Units", "type": "Char", "core": "Exp"},
        "PPSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "PPREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "PPSPEC": {"label": "Specimen Material Type", "type": "Char", "core": "Perm"},
        "VISITNUM": {"label": "Visit Number", "type": "Num", "core": "Perm"},
        "VISIT": {"label": "Visit Name", "type": "Char", "core": "Perm"},
        "PPDTC": {"label": "Date/Time of Parameter Collection", "type": "Char", "core": "Perm"},
        "PPDY": {"label": "Study Day of Parameter Collection", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # QS - Questionnaires
    # =========================================================================
    "QS": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "QSSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "QSSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "QSTESTCD": {"label": "Question Short Name", "type": "Char", "core": "Req"},
        "QSTEST": {"label": "Question Name", "type": "Char", "core": "Req"},
        "QSCAT": {"label": "Category of Question", "type": "Char", "core": "Exp"},
        "QSSCAT": {"label": "Subcategory for Question", "type": "Char", "core": "Perm"},
        "QSORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "QSORRESU": {"label": "Original Units", "type": "Char", "core": "Perm"},
        "QSSTRESC": {"label": "Character Result/Finding in Std Format", "type": "Char", "core": "Exp"},
        "QSSTRESN": {"label": "Numeric Result/Finding in Standard Units", "type": "Num", "core": "Exp"},
        "QSSTRESU": {"label": "Standard Units", "type": "Char", "core": "Perm"},
        "QSSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "QSREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "QSEVAL": {"label": "Evaluator", "type": "Char", "core": "Perm"},
        "VISITNUM": {"label": "Visit Number", "type": "Num", "core": "Exp"},
        "VISIT": {"label": "Visit Name", "type": "Char", "core": "Perm"},
        "QSDTC": {"label": "Date/Time of Finding", "type": "Char", "core": "Exp"},
        "QSDY": {"label": "Study Day of Finding", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # IE - Inclusion/Exclusion Criteria Not Met
    # =========================================================================
    "IE": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "IESEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "IESPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "IETESTCD": {"label": "Incl/Excl Criterion Short Name", "type": "Char", "core": "Req"},
        "IETEST": {"label": "Inclusion/Exclusion Criterion", "type": "Char", "core": "Req"},
        "IECAT": {"label": "Inclusion/Exclusion Category", "type": "Char", "core": "Req"},
        "IESCAT": {"label": "Inclusion/Exclusion Subcategory", "type": "Char", "core": "Perm"},
        "IEORRES": {"label": "I/E Criterion Original Result", "type": "Char", "core": "Exp"},
        "IESTRESC": {"label": "Character Result/Finding in Std Format", "type": "Char", "core": "Exp"},
        "IESTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "IEREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "VISITNUM": {"label": "Visit Number", "type": "Num", "core": "Perm"},
        "VISIT": {"label": "Visit Name", "type": "Char", "core": "Perm"},
        "IEDTC": {"label": "Date/Time of Collection", "type": "Char", "core": "Exp"},
        "IEDY": {"label": "Study Day of Collection", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # SU - Substance Use
    # =========================================================================
    "SU": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "SUSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "SUSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "SUTRT": {"label": "Reported Name of Substance", "type": "Char", "core": "Req"},
        "SUMODIFY": {"label": "Modified Substance Name", "type": "Char", "core": "Perm"},
        "SUDECOD": {"label": "Standardized Substance Name", "type": "Char", "core": "Perm"},
        "SUCAT": {"label": "Category of Substance", "type": "Char", "core": "Perm"},
        "SUSCAT": {"label": "Subcategory of Substance", "type": "Char", "core": "Perm"},
        "SUPRESP": {"label": "Pre-Specified", "type": "Char", "core": "Perm"},
        "SUOCCUR": {"label": "Occurrence", "type": "Char", "core": "Perm"},
        "SUDOSE": {"label": "Substance Use Consumption", "type": "Num", "core": "Perm"},
        "SUDOSTXT": {"label": "Substance Use Consumption Text", "type": "Char", "core": "Perm"},
        "SUDOSU": {"label": "Consumption Units", "type": "Char", "core": "Perm"},
        "SUDOSFRQ": {"label": "Use Frequency Per Interval", "type": "Char", "core": "Perm"},
        "SUROUTE": {"label": "Route of Administration", "type": "Char", "core": "Perm"},
        "SUSTDTC": {"label": "Start Date/Time of Substance Use", "type": "Char", "core": "Perm"},
        "SUENDTC": {"label": "End Date/Time of Substance Use", "type": "Char", "core": "Perm"},
        "SUSTDY": {"label": "Study Day of Start of Substance Use", "type": "Num", "core": "Perm"},
        "SUENDY": {"label": "Study Day of End of Substance Use", "type": "Num", "core": "Perm"},
        "SUSTRF": {"label": "Start Relative to Reference Period", "type": "Char", "core": "Perm"},
        "SUENRF": {"label": "End Relative to Reference Period", "type": "Char", "core": "Perm"},
    },
    # =========================================================================
    # FA - Findings About Events or Interventions
    # =========================================================================
    "FA": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "FASEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "FASPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "FATESTCD": {"label": "Findings About Test Short Name", "type": "Char", "core": "Req"},
        "FATEST": {"label": "Findings About Test Name", "type": "Char", "core": "Req"},
        "FAOBJ": {"label": "Object of the Observation", "type": "Char", "core": "Req"},
        "FACAT": {"label": "Category for Findings About", "type": "Char", "core": "Perm"},
        "FASCAT": {"label": "Subcategory for Findings About", "type": "Char", "core": "Perm"},
        "FAORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "FAORRESU": {"label": "Original Units", "type": "Char", "core": "Perm"},
        "FASTRESC": {"label": "Character Result/Finding in Std Format", "type": "Char", "core": "Exp"},
        "FASTRESN": {"label": "Numeric Result/Finding in Std Units", "type": "Num", "core": "Perm"},
        "FASTRESU": {"label": "Standard Units", "type": "Char", "core": "Perm"},
        "FASTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "FAREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "FALOC": {"label": "Location of Finding", "type": "Char", "core": "Perm"},
        "FAEVAL": {"label": "Evaluator", "type": "Char", "core": "Perm"},
        "VISITNUM": {"label": "Visit Number", "type": "Num", "core": "Perm"},
        "VISIT": {"label": "Visit Name", "type": "Char", "core": "Perm"},
        "FADTC": {"label": "Date/Time of Collection", "type": "Char", "core": "Exp"},
        "FADY": {"label": "Study Day of Collection", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # PR - Procedures
    # =========================================================================
    "PR": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "PRSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "PRSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "PRTRT": {"label": "Reported Name of Procedure", "type": "Char", "core": "Req"},
        "PRMODIFY": {"label": "Modified Procedure Name", "type": "Char", "core": "Perm"},
        "PRDECOD": {"label": "Standardized Procedure Name", "type": "Char", "core": "Perm"},
        "PRCAT": {"label": "Category for Procedure", "type": "Char", "core": "Perm"},
        "PRSCAT": {"label": "Subcategory for Procedure", "type": "Char", "core": "Perm"},
        "PRPRESP": {"label": "Pre-Specified", "type": "Char", "core": "Perm"},
        "PROCCUR": {"label": "Occurrence", "type": "Char", "core": "Perm"},
        "PRINDC": {"label": "Indication", "type": "Char", "core": "Perm"},
        "PRLOC": {"label": "Location of Procedure", "type": "Char", "core": "Perm"},
        "PRLAT": {"label": "Laterality", "type": "Char", "core": "Perm"},
        "PRSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "PRREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "PRSTDTC": {"label": "Start Date/Time of Procedure", "type": "Char", "core": "Exp"},
        "PRENDTC": {"label": "End Date/Time of Procedure", "type": "Char", "core": "Perm"},
        "PRSTDY": {"label": "Study Day of Start of Procedure", "type": "Num", "core": "Perm"},
        "PRENDY": {"label": "Study Day of End of Procedure", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # DV - Protocol Deviations
    # =========================================================================
    "DV": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "DVSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "DVSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "DVTERM": {"label": "Protocol Deviation Term", "type": "Char", "core": "Req"},
        "DVDECOD": {"label": "Standardized Protocol Deviation Term", "type": "Char", "core": "Perm"},
        "DVCAT": {"label": "Category for Protocol Deviation", "type": "Char", "core": "Perm"},
        "DVSCAT": {"label": "Subcategory for Protocol Deviation", "type": "Char", "core": "Perm"},
        "EPOCH": {"label": "Epoch", "type": "Char", "core": "Perm"},
        "DVSTDTC": {"label": "Start Date/Time of Deviation", "type": "Char", "core": "Exp"},
        "DVENDTC": {"label": "End Date/Time of Deviation", "type": "Char", "core": "Perm"},
        "DVSTDY": {"label": "Study Day of Start of Deviation", "type": "Num", "core": "Perm"},
        "DVENDY": {"label": "Study Day of End of Deviation", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # CE - Clinical Events
    # =========================================================================
    "CE": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "CESEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "CESPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "CETERM": {"label": "Reported Term for the Clinical Event", "type": "Char", "core": "Req"},
        "CEMODIFY": {"label": "Modified Reported Term", "type": "Char", "core": "Perm"},
        "CEDECOD": {"label": "Dictionary-Derived Term", "type": "Char", "core": "Perm"},
        "CECAT": {"label": "Category for Clinical Event", "type": "Char", "core": "Perm"},
        "CESCAT": {"label": "Subcategory for Clinical Event", "type": "Char", "core": "Perm"},
        "CEPRESP": {"label": "Pre-Specified", "type": "Char", "core": "Perm"},
        "CEOCCUR": {"label": "Occurrence", "type": "Char", "core": "Perm"},
        "CEBODSYS": {"label": "Body System or Organ Class", "type": "Char", "core": "Perm"},
        "CESEV": {"label": "Severity/Intensity", "type": "Char", "core": "Perm"},
        "CESTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "CEREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "CESTDTC": {"label": "Start Date/Time of Clinical Event", "type": "Char", "core": "Exp"},
        "CEENDTC": {"label": "End Date/Time of Clinical Event", "type": "Char", "core": "Perm"},
        "CESTDY": {"label": "Study Day of Start of Event", "type": "Num", "core": "Perm"},
        "CEENDY": {"label": "Study Day of End of Event", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # HO - Healthcare Encounters
    # =========================================================================
    "HO": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "HOSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "HOSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "HOTERM": {"label": "Reported Term for Healthcare Encounter", "type": "Char", "core": "Req"},
        "HODECOD": {"label": "Standardized Encounter Term", "type": "Char", "core": "Perm"},
        "HOCAT": {"label": "Category for Healthcare Encounter", "type": "Char", "core": "Perm"},
        "HOSCAT": {"label": "Subcategory for Encounter", "type": "Char", "core": "Perm"},
        "HOPRESP": {"label": "Pre-Specified", "type": "Char", "core": "Perm"},
        "HOOCCUR": {"label": "Occurrence", "type": "Char", "core": "Perm"},
        "HOSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "HOREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "HOSTDTC": {"label": "Start Date/Time of Encounter", "type": "Char", "core": "Exp"},
        "HOENDTC": {"label": "End Date/Time of Encounter", "type": "Char", "core": "Perm"},
        "HOSTDY": {"label": "Study Day of Start of Encounter", "type": "Num", "core": "Perm"},
        "HOENDY": {"label": "Study Day of End of Encounter", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # CO - Comments
    # =========================================================================
    "CO": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "RDOMAIN": {"label": "Related Domain Abbreviation", "type": "Char", "core": "Perm"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Perm"},
        "COSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "IDVAR": {"label": "Identifying Variable", "type": "Char", "core": "Perm"},
        "IDVARVAL": {"label": "Identifying Variable Value", "type": "Char", "core": "Perm"},
        "COREF": {"label": "Comment Reference", "type": "Char", "core": "Perm"},
        "COVAL": {"label": "Comment", "type": "Char", "core": "Req"},
        "COEVAL": {"label": "Evaluator", "type": "Char", "core": "Perm"},
        "CODTC": {"label": "Date/Time of Comment", "type": "Char", "core": "Perm"},
        "CODY": {"label": "Study Day of Comment", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # SV - Subject Visits
    # =========================================================================
    "SV": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "VISITNUM": {"label": "Visit Number", "type": "Num", "core": "Req"},
        "VISIT": {"label": "Visit Name", "type": "Char", "core": "Perm"},
        "VISITDY": {"label": "Planned Study Day of Visit", "type": "Num", "core": "Perm"},
        "SVSTDTC": {"label": "Start Date/Time of Visit", "type": "Char", "core": "Exp"},
        "SVENDTC": {"label": "End Date/Time of Visit", "type": "Char", "core": "Perm"},
        "SVSTDY": {"label": "Study Day of Start of Visit", "type": "Num", "core": "Perm"},
        "SVENDY": {"label": "Study Day of End of Visit", "type": "Num", "core": "Perm"},
        "SVUPDES": {"label": "Description of Unplanned Visit", "type": "Char", "core": "Perm"},
        "EPOCH": {"label": "Epoch", "type": "Char", "core": "Perm"},
    },
    # =========================================================================
    # SE - Subject Elements
    # =========================================================================
    "SE": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "SESEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "ETCD": {"label": "Element Code", "type": "Char", "core": "Req"},
        "ELEMENT": {"label": "Description of Element", "type": "Char", "core": "Req"},
        "SESTDTC": {"label": "Start Date/Time of Element", "type": "Char", "core": "Exp"},
        "SEENDTC": {"label": "End Date/Time of Element", "type": "Char", "core": "Exp"},
        "SESTDY": {"label": "Study Day of Start of Element", "type": "Num", "core": "Perm"},
        "SEENDY": {"label": "Study Day of End of Element", "type": "Num", "core": "Perm"},
        "EPOCH": {"label": "Epoch", "type": "Char", "core": "Req"},
        "TAESSION": {"label": "Planned Element Session ID", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # SM - Subject Medical/Surgical History (alternate to MH)
    # =========================================================================
    "SM": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "SMSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "SMSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "SMTERM": {"label": "Reported Term for Med/Surg History", "type": "Char", "core": "Req"},
        "SMMODIFY": {"label": "Modified Reported Term", "type": "Char", "core": "Perm"},
        "SMDECOD": {"label": "Dictionary-Derived Term", "type": "Char", "core": "Perm"},
        "SMCAT": {"label": "Category", "type": "Char", "core": "Perm"},
        "SMSCAT": {"label": "Subcategory", "type": "Char", "core": "Perm"},
        "SMPRESP": {"label": "Pre-Specified", "type": "Char", "core": "Perm"},
        "SMOCCUR": {"label": "Occurrence", "type": "Char", "core": "Perm"},
        "SMBODSYS": {"label": "Body System or Organ Class", "type": "Char", "core": "Perm"},
        "SMSTDTC": {"label": "Start Date/Time", "type": "Char", "core": "Perm"},
        "SMENDTC": {"label": "End Date/Time", "type": "Char", "core": "Perm"},
        "SMENRF": {"label": "End Relative to Reference Period", "type": "Char", "core": "Perm"},
    },
    # =========================================================================
    # AG - Procedure Agents
    # =========================================================================
    "AG": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "AGSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "AGSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "AGTRT": {"label": "Reported Agent Name", "type": "Char", "core": "Req"},
        "AGMODIFY": {"label": "Modified Agent Name", "type": "Char", "core": "Perm"},
        "AGDECOD": {"label": "Standardized Agent Name", "type": "Char", "core": "Perm"},
        "AGCAT": {"label": "Category for Agent", "type": "Char", "core": "Perm"},
        "AGSCAT": {"label": "Subcategory for Agent", "type": "Char", "core": "Perm"},
        "AGDOSE": {"label": "Dose per Administration", "type": "Num", "core": "Perm"},
        "AGDOSU": {"label": "Dose Units", "type": "Char", "core": "Perm"},
        "AGROUTE": {"label": "Route of Administration", "type": "Char", "core": "Perm"},
        "AGSTDTC": {"label": "Start Date/Time of Agent", "type": "Char", "core": "Exp"},
        "AGENDTC": {"label": "End Date/Time of Agent", "type": "Char", "core": "Perm"},
        "AGSTDY": {"label": "Study Day of Start of Agent", "type": "Num", "core": "Perm"},
        "AGENDY": {"label": "Study Day of End of Agent", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # EC - Exposure as Collected
    # =========================================================================
    "EC": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "ECSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "ECSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "ECTRT": {"label": "Name of Treatment", "type": "Char", "core": "Req"},
        "ECCAT": {"label": "Category of Treatment", "type": "Char", "core": "Perm"},
        "ECSCAT": {"label": "Subcategory of Treatment", "type": "Char", "core": "Perm"},
        "ECPRESP": {"label": "Pre-Specified", "type": "Char", "core": "Perm"},
        "ECOCCUR": {"label": "Occurrence", "type": "Char", "core": "Perm"},
        "ECDOSE": {"label": "Dose", "type": "Num", "core": "Exp"},
        "ECDOSTXT": {"label": "Dose Description", "type": "Char", "core": "Perm"},
        "ECDOSU": {"label": "Dose Units", "type": "Char", "core": "Exp"},
        "ECDOSFRM": {"label": "Dose Form", "type": "Char", "core": "Exp"},
        "ECDOSFRQ": {"label": "Dosing Frequency per Interval", "type": "Char", "core": "Perm"},
        "ECROUTE": {"label": "Route of Administration", "type": "Char", "core": "Exp"},
        "ECSTDTC": {"label": "Start Date/Time of Treatment", "type": "Char", "core": "Exp"},
        "ECENDTC": {"label": "End Date/Time of Treatment", "type": "Char", "core": "Exp"},
        "ECSTDY": {"label": "Study Day of Start of Treatment", "type": "Num", "core": "Perm"},
        "ECENDY": {"label": "Study Day of End of Treatment", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # ML - Meals
    # =========================================================================
    "ML": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "MLSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "MLSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "MLTRT": {"label": "Name of Meal", "type": "Char", "core": "Req"},
        "MLCAT": {"label": "Category for Meal", "type": "Char", "core": "Perm"},
        "MLSCAT": {"label": "Subcategory for Meal", "type": "Char", "core": "Perm"},
        "MLSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "MLREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "EPOCH": {"label": "Epoch", "type": "Char", "core": "Perm"},
        "MLSTDTC": {"label": "Start Date/Time of Meal", "type": "Char", "core": "Exp"},
        "MLENDTC": {"label": "End Date/Time of Meal", "type": "Char", "core": "Perm"},
        "MLSTDY": {"label": "Study Day of Start of Meal", "type": "Num", "core": "Perm"},
        "MLENDY": {"label": "Study Day of End of Meal", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # DA - Drug Accountability
    # =========================================================================
    "DA": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "DASEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "DASPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "DATESTCD": {"label": "Drug Accountability Test Short Name", "type": "Char", "core": "Req"},
        "DATEST": {"label": "Drug Accountability Test Name", "type": "Char", "core": "Req"},
        "DACAT": {"label": "Category for Drug Accountability", "type": "Char", "core": "Perm"},
        "DASCAT": {"label": "Subcategory for Drug Accountability", "type": "Char", "core": "Perm"},
        "DAORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "DAORRESU": {"label": "Original Units", "type": "Char", "core": "Perm"},
        "DASTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "DASTRESN": {"label": "Numeric Result in Standard Units", "type": "Num", "core": "Perm"},
        "DASTRESU": {"label": "Standard Units", "type": "Char", "core": "Perm"},
        "DASTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "DAREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "DALOT": {"label": "Lot Number", "type": "Char", "core": "Perm"},
        "VISITNUM": {"label": "Visit Number", "type": "Num", "core": "Exp"},
        "VISIT": {"label": "Visit Name", "type": "Char", "core": "Perm"},
        "DADTC": {"label": "Date/Time of Collection", "type": "Char", "core": "Exp"},
        "DADY": {"label": "Study Day of Collection", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # DD - Death Details
    # =========================================================================
    "DD": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "DDSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "DDSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "DDTESTCD": {"label": "Death Detail Assessment Short Name", "type": "Char", "core": "Req"},
        "DDTEST": {"label": "Death Detail Assessment Name", "type": "Char", "core": "Req"},
        "DDCAT": {"label": "Category for Death Details", "type": "Char", "core": "Perm"},
        "DDSCAT": {"label": "Subcategory for Death Details", "type": "Char", "core": "Perm"},
        "DDORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "DDSTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "DDSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "DDREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "DDDTC": {"label": "Date/Time of Assessment", "type": "Char", "core": "Exp"},
        "DDDY": {"label": "Study Day of Assessment", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # SC - Subject Characteristics
    # =========================================================================
    "SC": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "SCSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "SCSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "SCTESTCD": {"label": "Subject Characteristic Short Name", "type": "Char", "core": "Req"},
        "SCTEST": {"label": "Subject Characteristic Name", "type": "Char", "core": "Req"},
        "SCCAT": {"label": "Category for Subject Characteristic", "type": "Char", "core": "Perm"},
        "SCSCAT": {"label": "Subcategory for Subject Characteristic", "type": "Char", "core": "Perm"},
        "SCORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "SCORRESU": {"label": "Original Units", "type": "Char", "core": "Perm"},
        "SCSTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "SCSTRESN": {"label": "Numeric Result in Standard Units", "type": "Num", "core": "Perm"},
        "SCSTRESU": {"label": "Standard Units", "type": "Char", "core": "Perm"},
        "SCSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "SCREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "SCDTC": {"label": "Date/Time of Collection", "type": "Char", "core": "Perm"},
        "SCDY": {"label": "Study Day of Collection", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # SS - Subject Status
    # =========================================================================
    "SS": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "SSSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "SSSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "SSTESTCD": {"label": "Subject Status Short Name", "type": "Char", "core": "Req"},
        "SSTEST": {"label": "Subject Status Name", "type": "Char", "core": "Req"},
        "SSCAT": {"label": "Category for Subject Status", "type": "Char", "core": "Perm"},
        "SSSCAT": {"label": "Subcategory for Subject Status", "type": "Char", "core": "Perm"},
        "SSORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "SSSTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "SSSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "SSREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "SSDTC": {"label": "Date/Time of Assessment", "type": "Char", "core": "Exp"},
        "SSDY": {"label": "Study Day of Assessment", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # MB - Microbiology Specimen
    # =========================================================================
    "MB": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "MBSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "MBSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "MBTESTCD": {"label": "Microbiology Test Short Name", "type": "Char", "core": "Req"},
        "MBTEST": {"label": "Microbiology Test Name", "type": "Char", "core": "Req"},
        "MBCAT": {"label": "Category for Microbiology", "type": "Char", "core": "Perm"},
        "MBSCAT": {"label": "Subcategory for Microbiology", "type": "Char", "core": "Perm"},
        "MBORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "MBORRESU": {"label": "Original Units", "type": "Char", "core": "Perm"},
        "MBSTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "MBSTRESN": {"label": "Numeric Result in Standard Units", "type": "Num", "core": "Perm"},
        "MBSTRESU": {"label": "Standard Units", "type": "Char", "core": "Perm"},
        "MBSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "MBREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "MBSPEC": {"label": "Specimen Material Type", "type": "Char", "core": "Exp"},
        "MBMETHOD": {"label": "Method of Test", "type": "Char", "core": "Perm"},
        "VISITNUM": {"label": "Visit Number", "type": "Num", "core": "Exp"},
        "VISIT": {"label": "Visit Name", "type": "Char", "core": "Perm"},
        "MBDTC": {"label": "Date/Time of Specimen Collection", "type": "Char", "core": "Exp"},
        "MBDY": {"label": "Study Day of Specimen Collection", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # MS - Microbiology Susceptibility
    # =========================================================================
    "MS": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "MSSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "MSSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "MSTESTCD": {"label": "Susceptibility Test Short Name", "type": "Char", "core": "Req"},
        "MSTEST": {"label": "Susceptibility Test Name", "type": "Char", "core": "Req"},
        "MSCAT": {"label": "Category for Susceptibility", "type": "Char", "core": "Perm"},
        "MSSCAT": {"label": "Subcategory for Susceptibility", "type": "Char", "core": "Perm"},
        "MSORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "MSORRESU": {"label": "Original Units", "type": "Char", "core": "Perm"},
        "MSSTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "MSSTRESN": {"label": "Numeric Result in Standard Units", "type": "Num", "core": "Perm"},
        "MSSTRESU": {"label": "Standard Units", "type": "Char", "core": "Perm"},
        "MSSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "MSREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "MSLNKID": {"label": "Link ID", "type": "Char", "core": "Perm"},
        "MSDTC": {"label": "Date/Time of Collection", "type": "Char", "core": "Exp"},
        "MSDY": {"label": "Study Day of Collection", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # MI - Microscopic Findings
    # =========================================================================
    "MI": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "MISEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "MISPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "MITESTCD": {"label": "Microscopic Finding Short Name", "type": "Char", "core": "Req"},
        "MITEST": {"label": "Microscopic Finding Name", "type": "Char", "core": "Req"},
        "MICAT": {"label": "Category for Microscopic Finding", "type": "Char", "core": "Perm"},
        "MISCAT": {"label": "Subcategory for Microscopic Finding", "type": "Char", "core": "Perm"},
        "MIORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "MISTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "MISTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "MIREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "MISPEC": {"label": "Specimen Material Type", "type": "Char", "core": "Exp"},
        "MILOC": {"label": "Location of Specimen", "type": "Char", "core": "Perm"},
        "MILAT": {"label": "Laterality", "type": "Char", "core": "Perm"},
        "MIMETHOD": {"label": "Method of Test", "type": "Char", "core": "Perm"},
        "VISITNUM": {"label": "Visit Number", "type": "Num", "core": "Perm"},
        "VISIT": {"label": "Visit Name", "type": "Char", "core": "Perm"},
        "MIDTC": {"label": "Date/Time of Collection", "type": "Char", "core": "Exp"},
        "MIDY": {"label": "Study Day of Collection", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # MO - Morphology (Sperm)
    # =========================================================================
    "MO": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "MOSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "MOSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "MOTESTCD": {"label": "Morphology Test Short Name", "type": "Char", "core": "Req"},
        "MOTEST": {"label": "Morphology Test Name", "type": "Char", "core": "Req"},
        "MOCAT": {"label": "Category for Morphology", "type": "Char", "core": "Perm"},
        "MOSCAT": {"label": "Subcategory for Morphology", "type": "Char", "core": "Perm"},
        "MOORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "MOORRESU": {"label": "Original Units", "type": "Char", "core": "Perm"},
        "MOSTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "MOSTRESN": {"label": "Numeric Result in Standard Units", "type": "Num", "core": "Perm"},
        "MOSTRESU": {"label": "Standard Units", "type": "Char", "core": "Perm"},
        "MOSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "MOREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "MOSPEC": {"label": "Specimen Material Type", "type": "Char", "core": "Exp"},
        "MOMETHOD": {"label": "Method of Test", "type": "Char", "core": "Perm"},
        "MODTC": {"label": "Date/Time of Collection", "type": "Char", "core": "Exp"},
        "MODY": {"label": "Study Day of Collection", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # RP - Reproductive System Findings
    # =========================================================================
    "RP": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "RPSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "RPSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "RPTESTCD": {"label": "Reproductive Finding Short Name", "type": "Char", "core": "Req"},
        "RPTEST": {"label": "Reproductive Finding Name", "type": "Char", "core": "Req"},
        "RPCAT": {"label": "Category for Reproductive Finding", "type": "Char", "core": "Perm"},
        "RPSCAT": {"label": "Subcategory for Reproductive Finding", "type": "Char", "core": "Perm"},
        "RPORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "RPORRESU": {"label": "Original Units", "type": "Char", "core": "Perm"},
        "RPSTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "RPSTRESN": {"label": "Numeric Result in Standard Units", "type": "Num", "core": "Perm"},
        "RPSTRESU": {"label": "Standard Units", "type": "Char", "core": "Perm"},
        "RPSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "RPREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "VISITNUM": {"label": "Visit Number", "type": "Num", "core": "Perm"},
        "VISIT": {"label": "Visit Name", "type": "Char", "core": "Perm"},
        "RPDTC": {"label": "Date/Time of Collection", "type": "Char", "core": "Exp"},
        "RPDY": {"label": "Study Day of Collection", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # Oncology Domains: RS, TR, TU
    # =========================================================================
    "RS": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "RSSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "RSSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "RSTESTCD": {"label": "Disease Response Short Name", "type": "Char", "core": "Req"},
        "RSTEST": {"label": "Disease Response Name", "type": "Char", "core": "Req"},
        "RSCAT": {"label": "Category for Response", "type": "Char", "core": "Perm"},
        "RSSCAT": {"label": "Subcategory for Response", "type": "Char", "core": "Perm"},
        "RSORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "RSSTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "RSSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "RSREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "RSEVAL": {"label": "Evaluator", "type": "Char", "core": "Perm"},
        "VISITNUM": {"label": "Visit Number", "type": "Num", "core": "Exp"},
        "VISIT": {"label": "Visit Name", "type": "Char", "core": "Perm"},
        "RSDTC": {"label": "Date/Time of Assessment", "type": "Char", "core": "Exp"},
        "RSDY": {"label": "Study Day of Assessment", "type": "Num", "core": "Perm"},
    },
    "TR": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "TRSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "TRSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "TRLNKID": {"label": "Link ID", "type": "Char", "core": "Exp"},
        "TRTESTCD": {"label": "Tumor Assessment Short Name", "type": "Char", "core": "Req"},
        "TRTEST": {"label": "Tumor Assessment Name", "type": "Char", "core": "Req"},
        "TRORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "TRORRESU": {"label": "Original Units", "type": "Char", "core": "Perm"},
        "TRSTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "TRSTRESN": {"label": "Numeric Result in Standard Units", "type": "Num", "core": "Perm"},
        "TRSTRESU": {"label": "Standard Units", "type": "Char", "core": "Perm"},
        "TRSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "TRREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "TRLOC": {"label": "Location of Tumor", "type": "Char", "core": "Exp"},
        "TRLAT": {"label": "Laterality", "type": "Char", "core": "Perm"},
        "TRMETHOD": {"label": "Method of Measurement", "type": "Char", "core": "Perm"},
        "TREVAL": {"label": "Evaluator", "type": "Char", "core": "Perm"},
        "VISITNUM": {"label": "Visit Number", "type": "Num", "core": "Exp"},
        "VISIT": {"label": "Visit Name", "type": "Char", "core": "Perm"},
        "TRDTC": {"label": "Date/Time of Tumor Measurement", "type": "Char", "core": "Exp"},
        "TRDY": {"label": "Study Day of Measurement", "type": "Num", "core": "Perm"},
    },
    "TU": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "TUSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "TUSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "TULNKID": {"label": "Link ID", "type": "Char", "core": "Req"},
        "TUTESTCD": {"label": "Tumor Identification Short Name", "type": "Char", "core": "Req"},
        "TUTEST": {"label": "Tumor Identification Name", "type": "Char", "core": "Req"},
        "TUORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "TUSTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "TUSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "TUREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "TULOC": {"label": "Location of Tumor", "type": "Char", "core": "Exp"},
        "TULAT": {"label": "Laterality", "type": "Char", "core": "Perm"},
        "TUMETHOD": {"label": "Method of Identification", "type": "Char", "core": "Perm"},
        "TUEVAL": {"label": "Evaluator", "type": "Char", "core": "Perm"},
        "VISITNUM": {"label": "Visit Number", "type": "Num", "core": "Exp"},
        "VISIT": {"label": "Visit Name", "type": "Char", "core": "Perm"},
        "TUDTC": {"label": "Date/Time of Identification", "type": "Char", "core": "Exp"},
        "TUDY": {"label": "Study Day of Identification", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # Additional Findings Domains: FT, CV, NV, OE, RE, SR, UR, GF, IS, BE, BS, CP, BM
    # =========================================================================
    "FT": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "FTSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "FTTESTCD": {"label": "Functional Test Short Name", "type": "Char", "core": "Req"},
        "FTTEST": {"label": "Functional Test Name", "type": "Char", "core": "Req"},
        "FTCAT": {"label": "Category for Functional Test", "type": "Char", "core": "Perm"},
        "FTSCAT": {"label": "Subcategory for Functional Test", "type": "Char", "core": "Perm"},
        "FTORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "FTORRESU": {"label": "Original Units", "type": "Char", "core": "Perm"},
        "FTSTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "FTSTRESN": {"label": "Numeric Result in Standard Units", "type": "Num", "core": "Perm"},
        "FTSTRESU": {"label": "Standard Units", "type": "Char", "core": "Perm"},
        "FTSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "FTREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "FTDTC": {"label": "Date/Time of Collection", "type": "Char", "core": "Exp"},
        "FTDY": {"label": "Study Day of Collection", "type": "Num", "core": "Perm"},
    },
    "CV": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "CVSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "CVTESTCD": {"label": "CV Test Short Name", "type": "Char", "core": "Req"},
        "CVTEST": {"label": "CV Test Name", "type": "Char", "core": "Req"},
        "CVCAT": {"label": "Category for CV Test", "type": "Char", "core": "Perm"},
        "CVSCAT": {"label": "Subcategory for CV Test", "type": "Char", "core": "Perm"},
        "CVORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "CVORRESU": {"label": "Original Units", "type": "Char", "core": "Perm"},
        "CVSTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "CVSTRESN": {"label": "Numeric Result in Standard Units", "type": "Num", "core": "Perm"},
        "CVSTRESU": {"label": "Standard Units", "type": "Char", "core": "Perm"},
        "CVSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "CVREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "CVMETHOD": {"label": "Method of Measurement", "type": "Char", "core": "Perm"},
        "CVDTC": {"label": "Date/Time of Collection", "type": "Char", "core": "Exp"},
        "CVDY": {"label": "Study Day of Collection", "type": "Num", "core": "Perm"},
    },
    "NV": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "NVSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "NVTESTCD": {"label": "Nervous System Test Short Name", "type": "Char", "core": "Req"},
        "NVTEST": {"label": "Nervous System Test Name", "type": "Char", "core": "Req"},
        "NVCAT": {"label": "Category", "type": "Char", "core": "Perm"},
        "NVSCAT": {"label": "Subcategory", "type": "Char", "core": "Perm"},
        "NVORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "NVSTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "NVSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "NVREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "NVLOC": {"label": "Location", "type": "Char", "core": "Perm"},
        "NVLAT": {"label": "Laterality", "type": "Char", "core": "Perm"},
        "NVDTC": {"label": "Date/Time of Collection", "type": "Char", "core": "Exp"},
        "NVDY": {"label": "Study Day of Collection", "type": "Num", "core": "Perm"},
    },
    "OE": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "OESEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "OETESTCD": {"label": "Ophthalmic Exam Short Name", "type": "Char", "core": "Req"},
        "OETEST": {"label": "Ophthalmic Exam Name", "type": "Char", "core": "Req"},
        "OECAT": {"label": "Category", "type": "Char", "core": "Perm"},
        "OESCAT": {"label": "Subcategory", "type": "Char", "core": "Perm"},
        "OEORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "OEORRESU": {"label": "Original Units", "type": "Char", "core": "Perm"},
        "OESTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "OESTRESN": {"label": "Numeric Result in Standard Units", "type": "Num", "core": "Perm"},
        "OESTRESU": {"label": "Standard Units", "type": "Char", "core": "Perm"},
        "OESTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "OEREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "OELOC": {"label": "Location", "type": "Char", "core": "Exp"},
        "OELAT": {"label": "Laterality (Eye)", "type": "Char", "core": "Exp"},
        "OEMETHOD": {"label": "Method of Examination", "type": "Char", "core": "Perm"},
        "OEDTC": {"label": "Date/Time of Examination", "type": "Char", "core": "Exp"},
        "OEDY": {"label": "Study Day of Examination", "type": "Num", "core": "Perm"},
    },
    "RE": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "RESEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "RETESTCD": {"label": "Respiratory Test Short Name", "type": "Char", "core": "Req"},
        "RETEST": {"label": "Respiratory Test Name", "type": "Char", "core": "Req"},
        "RECAT": {"label": "Category", "type": "Char", "core": "Perm"},
        "RESCAT": {"label": "Subcategory", "type": "Char", "core": "Perm"},
        "REORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "RESTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "RESTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "REREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "RELOC": {"label": "Location", "type": "Char", "core": "Perm"},
        "RELAT": {"label": "Laterality", "type": "Char", "core": "Perm"},
        "REDTC": {"label": "Date/Time of Collection", "type": "Char", "core": "Exp"},
        "REDY": {"label": "Study Day of Collection", "type": "Num", "core": "Perm"},
    },
    "SR": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "SRSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "SRTESTCD": {"label": "Skin Response Test Short Name", "type": "Char", "core": "Req"},
        "SRTEST": {"label": "Skin Response Test Name", "type": "Char", "core": "Req"},
        "SRCAT": {"label": "Category", "type": "Char", "core": "Perm"},
        "SRSCAT": {"label": "Subcategory", "type": "Char", "core": "Perm"},
        "SRORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "SRORRESU": {"label": "Original Units", "type": "Char", "core": "Perm"},
        "SRSTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "SRSTRESN": {"label": "Numeric Result in Standard Units", "type": "Num", "core": "Perm"},
        "SRSTRESU": {"label": "Standard Units", "type": "Char", "core": "Perm"},
        "SRSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "SRREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "SRLOC": {"label": "Location of Response", "type": "Char", "core": "Perm"},
        "SRLAT": {"label": "Laterality", "type": "Char", "core": "Perm"},
        "SRDTC": {"label": "Date/Time of Collection", "type": "Char", "core": "Exp"},
        "SRDY": {"label": "Study Day of Collection", "type": "Num", "core": "Perm"},
        "SRTPT": {"label": "Planned Time Point Name", "type": "Char", "core": "Perm"},
    },
    "UR": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "URSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "URTESTCD": {"label": "Urinary System Test Short Name", "type": "Char", "core": "Req"},
        "URTEST": {"label": "Urinary System Test Name", "type": "Char", "core": "Req"},
        "URCAT": {"label": "Category", "type": "Char", "core": "Perm"},
        "URSCAT": {"label": "Subcategory", "type": "Char", "core": "Perm"},
        "URORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "URORRESU": {"label": "Original Units", "type": "Char", "core": "Perm"},
        "URSTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "URSTRESN": {"label": "Numeric Result in Standard Units", "type": "Num", "core": "Perm"},
        "URSTRESU": {"label": "Standard Units", "type": "Char", "core": "Perm"},
        "URSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "URREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "URDTC": {"label": "Date/Time of Collection", "type": "Char", "core": "Exp"},
        "URDY": {"label": "Study Day of Collection", "type": "Num", "core": "Perm"},
    },
    "GF": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "GFSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "GFTESTCD": {"label": "Genomics Test Short Name", "type": "Char", "core": "Req"},
        "GFTEST": {"label": "Genomics Test Name", "type": "Char", "core": "Req"},
        "GFCAT": {"label": "Category", "type": "Char", "core": "Perm"},
        "GFSCAT": {"label": "Subcategory", "type": "Char", "core": "Perm"},
        "GFORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "GFSTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "GFSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "GFREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "GFSPEC": {"label": "Specimen Material Type", "type": "Char", "core": "Exp"},
        "GFMETHOD": {"label": "Method of Test", "type": "Char", "core": "Perm"},
        "GFDTC": {"label": "Date/Time of Collection", "type": "Char", "core": "Exp"},
        "GFDY": {"label": "Study Day of Collection", "type": "Num", "core": "Perm"},
    },
    "IS": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "ISSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "ISTESTCD": {"label": "Immunogenicity Test Short Name", "type": "Char", "core": "Req"},
        "ISTEST": {"label": "Immunogenicity Test Name", "type": "Char", "core": "Req"},
        "ISCAT": {"label": "Category", "type": "Char", "core": "Perm"},
        "ISSCAT": {"label": "Subcategory", "type": "Char", "core": "Perm"},
        "ISORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "ISORRESU": {"label": "Original Units", "type": "Char", "core": "Perm"},
        "ISSTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "ISSTRESN": {"label": "Numeric Result in Standard Units", "type": "Num", "core": "Perm"},
        "ISSTRESU": {"label": "Standard Units", "type": "Char", "core": "Perm"},
        "ISSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "ISREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "ISSPEC": {"label": "Specimen Material Type", "type": "Char", "core": "Exp"},
        "ISMETHOD": {"label": "Method of Test", "type": "Char", "core": "Perm"},
        "ISDTC": {"label": "Date/Time of Collection", "type": "Char", "core": "Exp"},
        "ISDY": {"label": "Study Day of Collection", "type": "Num", "core": "Perm"},
        "ISTPT": {"label": "Planned Time Point Name", "type": "Char", "core": "Perm"},
    },
    "BE": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "BESEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "BESPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "BETERM": {"label": "Biospecimen Event Term", "type": "Char", "core": "Req"},
        "BECAT": {"label": "Category for Biospecimen Event", "type": "Char", "core": "Perm"},
        "BESCAT": {"label": "Subcategory for Biospecimen Event", "type": "Char", "core": "Perm"},
        "BESTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "BEREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "BESTDTC": {"label": "Start Date/Time of Event", "type": "Char", "core": "Exp"},
        "BEENDTC": {"label": "End Date/Time of Event", "type": "Char", "core": "Perm"},
        "BESTDY": {"label": "Study Day of Start of Event", "type": "Num", "core": "Perm"},
        "BEENDY": {"label": "Study Day of End of Event", "type": "Num", "core": "Perm"},
    },
    "BS": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "BSSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "BSTESTCD": {"label": "Biospecimen Finding Short Name", "type": "Char", "core": "Req"},
        "BSTEST": {"label": "Biospecimen Finding Name", "type": "Char", "core": "Req"},
        "BSCAT": {"label": "Category", "type": "Char", "core": "Perm"},
        "BSSCAT": {"label": "Subcategory", "type": "Char", "core": "Perm"},
        "BSORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "BSSTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "BSSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "BSREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "BSSPEC": {"label": "Specimen Material Type", "type": "Char", "core": "Exp"},
        "BSDTC": {"label": "Date/Time of Collection", "type": "Char", "core": "Exp"},
        "BSDY": {"label": "Study Day of Collection", "type": "Num", "core": "Perm"},
    },
    "CP": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "CPSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "CPTESTCD": {"label": "Cell Phenotype Test Short Name", "type": "Char", "core": "Req"},
        "CPTEST": {"label": "Cell Phenotype Test Name", "type": "Char", "core": "Req"},
        "CPCAT": {"label": "Category", "type": "Char", "core": "Perm"},
        "CPSCAT": {"label": "Subcategory", "type": "Char", "core": "Perm"},
        "CPORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "CPORRESU": {"label": "Original Units", "type": "Char", "core": "Perm"},
        "CPSTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "CPSTRESN": {"label": "Numeric Result in Standard Units", "type": "Num", "core": "Perm"},
        "CPSTRESU": {"label": "Standard Units", "type": "Char", "core": "Perm"},
        "CPSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "CPREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "CPSPEC": {"label": "Specimen Material Type", "type": "Char", "core": "Exp"},
        "CPMETHOD": {"label": "Method of Test", "type": "Char", "core": "Perm"},
        "CPDTC": {"label": "Date/Time of Collection", "type": "Char", "core": "Exp"},
        "CPDY": {"label": "Study Day of Collection", "type": "Num", "core": "Perm"},
    },
    "BM": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "USUBJID": {"label": "Unique Subject Identifier", "type": "Char", "core": "Req"},
        "BMSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "BMTESTCD": {"label": "Bone Measurement Test Short Name", "type": "Char", "core": "Req"},
        "BMTEST": {"label": "Bone Measurement Test Name", "type": "Char", "core": "Req"},
        "BMCAT": {"label": "Category", "type": "Char", "core": "Perm"},
        "BMSCAT": {"label": "Subcategory", "type": "Char", "core": "Perm"},
        "BMORRES": {"label": "Result or Finding in Original Units", "type": "Char", "core": "Exp"},
        "BMORRESU": {"label": "Original Units", "type": "Char", "core": "Perm"},
        "BMSTRESC": {"label": "Character Result in Standard Format", "type": "Char", "core": "Exp"},
        "BMSTRESN": {"label": "Numeric Result in Standard Units", "type": "Num", "core": "Perm"},
        "BMSTRESU": {"label": "Standard Units", "type": "Char", "core": "Perm"},
        "BMSTAT": {"label": "Completion Status", "type": "Char", "core": "Perm"},
        "BMREASND": {"label": "Reason Not Done", "type": "Char", "core": "Perm"},
        "BMLOC": {"label": "Location of Measurement", "type": "Char", "core": "Exp"},
        "BMLAT": {"label": "Laterality", "type": "Char", "core": "Perm"},
        "BMMETHOD": {"label": "Method of Measurement", "type": "Char", "core": "Perm"},
        "BMDTC": {"label": "Date/Time of Measurement", "type": "Char", "core": "Exp"},
        "BMDY": {"label": "Study Day of Measurement", "type": "Num", "core": "Perm"},
    },
    # =========================================================================
    # Trial Design Domains: TA, TE, TI, TS, TV, TD
    # =========================================================================
    "TA": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "ARMCD": {"label": "Planned Arm Code", "type": "Char", "core": "Req"},
        "ARM": {"label": "Description of Planned Arm", "type": "Char", "core": "Req"},
        "TAESSION": {"label": "Planned Element Session", "type": "Num", "core": "Req"},
        "ETCD": {"label": "Element Code", "type": "Char", "core": "Req"},
        "ELEMENT": {"label": "Description of Element", "type": "Char", "core": "Req"},
        "TABESSION": {"label": "Branch Element Session", "type": "Num", "core": "Perm"},
        "TATRANS": {"label": "Transition Rule", "type": "Char", "core": "Perm"},
        "EPOCH": {"label": "Epoch", "type": "Char", "core": "Perm"},
    },
    "TE": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "ETCD": {"label": "Element Code", "type": "Char", "core": "Req"},
        "ELEMENT": {"label": "Description of Element", "type": "Char", "core": "Req"},
        "TESTRL": {"label": "Rule for Start of Element", "type": "Char", "core": "Perm"},
        "TEENRL": {"label": "Rule for End of Element", "type": "Char", "core": "Perm"},
        "TEDUR": {"label": "Planned Duration of Element", "type": "Char", "core": "Perm"},
    },
    "TI": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "IETESTCD": {"label": "Incl/Excl Criterion Short Name", "type": "Char", "core": "Req"},
        "IETEST": {"label": "Inclusion/Exclusion Criterion", "type": "Char", "core": "Req"},
        "IECAT": {"label": "Inclusion/Exclusion Category", "type": "Char", "core": "Req"},
        "IESCAT": {"label": "Inclusion/Exclusion Subcategory", "type": "Char", "core": "Perm"},
        "TIRL": {"label": "Criterion Evaluation Rule", "type": "Char", "core": "Perm"},
        "TIVERS": {"label": "Protocol Criteria Version", "type": "Char", "core": "Perm"},
    },
    "TS": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "TSSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "TSGRPID": {"label": "Group ID", "type": "Char", "core": "Perm"},
        "TSPARMCD": {"label": "Trial Summary Parameter Short Name", "type": "Char", "core": "Req"},
        "TSPARM": {"label": "Trial Summary Parameter", "type": "Char", "core": "Req"},
        "TSVAL": {"label": "Parameter Value", "type": "Char", "core": "Req"},
        "TSVALNF": {"label": "Parameter Null Flavor", "type": "Char", "core": "Perm"},
        "TSVALCD": {"label": "Parameter Value Code", "type": "Char", "core": "Perm"},
        "TSVCDREF": {"label": "Value Code Reference", "type": "Char", "core": "Perm"},
        "TSVCDVER": {"label": "Value Code Version", "type": "Char", "core": "Perm"},
    },
    "TV": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "VISITNUM": {"label": "Visit Number", "type": "Num", "core": "Req"},
        "VISIT": {"label": "Visit Name", "type": "Char", "core": "Perm"},
        "VISITDY": {"label": "Planned Study Day of Visit", "type": "Num", "core": "Perm"},
        "ARMCD": {"label": "Planned Arm Code", "type": "Char", "core": "Perm"},
        "ARM": {"label": "Description of Planned Arm", "type": "Char", "core": "Perm"},
        "TVSTRL": {"label": "Visit Start Rule", "type": "Char", "core": "Perm"},
        "TVENRL": {"label": "Visit End Rule", "type": "Char", "core": "Perm"},
    },
    "TD": {
        "STUDYID": {"label": "Study Identifier", "type": "Char", "core": "Req"},
        "DOMAIN": {"label": "Domain Abbreviation", "type": "Char", "core": "Req"},
        "TDSEQ": {"label": "Sequence Number", "type": "Num", "core": "Req"},
        "TDSPID": {"label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm"},
        "TDDOMAIN": {"label": "Target Domain for Assessment", "type": "Char", "core": "Req"},
        "TDPARMCD": {"label": "Assessment Parameter Short Name", "type": "Char", "core": "Req"},
        "TDPARM": {"label": "Assessment Parameter Name", "type": "Char", "core": "Req"},
        "TDVAL": {"label": "Assessment Parameter Value", "type": "Char", "core": "Req"},
    },
}


# =============================================================================
# INTELLIGENT MAPPING TOOL (LLM-Based Semantic Mapping)
# =============================================================================

@tool
async def generate_intelligent_mapping(
    source_file: str,
    target_domain: str,
    study_id: str,
) -> Dict[str, Any]:
    """
    Generate SDTM mapping using LLM-based semantic understanding.

    This tool analyzes source column metadata (names, labels, sample values,
    data types) and uses semantic understanding to map them to appropriate
    SDTM variables based on meaning, not just string patterns.

    The mapping considers:
    - Source column names and their likely meanings
    - Sample data values to infer content type
    - SDTM variable definitions, labels, and expected content
    - Data type compatibility (Char vs Num)
    - Core requirements (Required, Expected, Permissible)

    Args:
        source_file: Path to source CSV file
        target_domain: Target SDTM domain code (e.g., 'DM', 'AE', 'CM')
        study_id: Study identifier for the transformation

    Returns:
        Intelligent mapping specification with confidence scores and reasoning
    """
    try:
        # Read source file
        df = await async_read_csv(source_file)
        domain = target_domain.upper()

        # Get SDTM variable definitions for target domain
        sdtm_vars = SDTM_VARIABLE_DEFINITIONS.get(domain, {})

        # Extract comprehensive source metadata
        source_metadata = []
        for col in df.columns:
            col_info = {
                "name": col,
                "dtype": str(df[col].dtype),
                "null_count": int(df[col].isna().sum()),
                "null_pct": round(df[col].isna().sum() / len(df) * 100, 1),
                "unique_values": int(df[col].nunique()),
                "sample_values": [str(v) for v in df[col].dropna().head(5).tolist()],
            }

            # Infer content type from sample values
            sample_str = " ".join(col_info["sample_values"])
            if any(d in sample_str for d in ['-', '/', 'T', ':']):
                if len(sample_str) > 8 and any(c.isdigit() for c in sample_str):
                    col_info["inferred_type"] = "datetime"
            elif col_info["dtype"].startswith("float") or col_info["dtype"].startswith("int"):
                col_info["inferred_type"] = "numeric"
            else:
                col_info["inferred_type"] = "text"

            source_metadata.append(col_info)

        # Build target variable info with labels
        target_variables = []
        for var_name, var_info in sdtm_vars.items():
            target_variables.append({
                "variable": var_name,
                "label": var_info["label"],
                "type": var_info["type"],
                "core": var_info["core"],
            })

        # Create mapping prompt for LLM
        # This will be used by the agent to perform intelligent mapping
        mapping_context = {
            "source_file": os.path.basename(source_file),
            "source_columns": source_metadata,
            "target_domain": domain,
            "target_variables": target_variables,
            "study_id": study_id,
        }

        # Perform pattern-based mapping as baseline
        # The agent can enhance this with LLM understanding
        column_mappings = []
        mapped_targets = set()

        # Semantic hints based on common EDC naming
        semantic_hints = {
            # Subject identifiers
            "subject": "USUBJID", "subj": "USUBJID", "patient": "USUBJID",
            "ptno": "USUBJID", "patno": "USUBJID", "scrno": "USUBJID",

            # Dates/Times
            "date": "DTC", "dt": "DTC", "datetime": "DTC",
            "startdate": "STDTC", "enddate": "ENDTC",
            "onset": "STDTC", "resolution": "ENDTC",

            # Results/Values
            "result": "ORRES", "value": "ORRES", "finding": "ORRES",
            "score": "STRESN", "measurement": "ORRES",

            # Units
            "unit": "ORRESU", "units": "ORRESU", "uom": "ORRESU",

            # Status/Flags
            "status": "STAT", "flag": "FL", "baseline": "BLFL",

            # Categories
            "category": "CAT", "type": "CAT", "class": "CAT",
            "subcategory": "SCAT", "subtype": "SCAT",
        }

        for src_col in source_metadata:
            col_name = src_col["name"]
            col_lower = col_name.lower().replace("_", "").replace(" ", "")

            # Try to find semantic match
            best_match = None
            best_score = 0

            for var in target_variables:
                var_name = var["variable"]
                var_label = var["label"].lower()

                # Calculate match score based on multiple factors
                score = 0

                # Exact name match (highest priority)
                if col_name.upper() == var_name:
                    score = 100

                # Label contains column name
                elif col_lower in var_label.replace(" ", ""):
                    score = 80

                # Column name contains key parts of variable label
                else:
                    label_words = var_label.split()
                    for word in label_words:
                        if len(word) > 3 and word.lower() in col_lower:
                            score = max(score, 60)

                # Type compatibility bonus
                if var["type"] == "Num" and src_col["inferred_type"] == "numeric":
                    score += 10
                elif var["type"] == "Char" and src_col["inferred_type"] == "text":
                    score += 5

                if score > best_score and var_name not in mapped_targets:
                    best_score = score
                    best_match = {
                        "source_column": col_name,
                        "target_variable": var_name,
                        "target_label": var["label"],
                        "confidence": score,
                        "reasoning": f"Matched based on semantic similarity (score={score})",
                        "source_type": src_col["inferred_type"],
                        "target_type": var["type"],
                        "target_core": var["core"],
                    }

            if best_match and best_match["confidence"] >= 40:
                column_mappings.append(best_match)
                mapped_targets.add(best_match["target_variable"])

        # Identify unmapped required variables
        unmapped_required = []
        for var in target_variables:
            if var["variable"] not in mapped_targets and var["core"] == "Req":
                unmapped_required.append({
                    "variable": var["variable"],
                    "label": var["label"],
                    "note": "Required variable - needs derivation or manual mapping"
                })

        # Identify unmapped source columns
        mapped_sources = {m["source_column"] for m in column_mappings}
        unmapped_sources = []
        for src in source_metadata:
            if src["name"] not in mapped_sources:
                unmapped_sources.append({
                    "column": src["name"],
                    "inferred_type": src["inferred_type"],
                    "sample": src["sample_values"][:2],
                })

        # Build derivation rules for standard variables
        derivations = {
            "STUDYID": f"ASSIGN('{study_id}')",
            "DOMAIN": f"ASSIGN('{domain}')",
        }

        if "USUBJID" not in mapped_targets:
            if any("SUBJID" in m["target_variable"] for m in column_mappings):
                derivations["USUBJID"] = f"CONCAT('{study_id}', '-', SUBJID)"

        if f"{domain}SEQ" not in mapped_targets:
            derivations[f"{domain}SEQ"] = "ROW_NUMBER()"

        spec = {
            "study_id": study_id,
            "source_file": os.path.basename(source_file),
            "target_domain": domain,
            "mapping_method": "intelligent_semantic",
            "column_mappings": column_mappings,
            "derivation_rules": derivations,
            "unmapped_required": unmapped_required,
            "unmapped_sources": unmapped_sources,
            "source_columns_count": len(df.columns),
            "target_variables_count": len(target_variables),
            "mapped_count": len(column_mappings),
            "mapping_coverage_pct": round(len(column_mappings) / len(df.columns) * 100, 1),
            "generated_at": datetime.now().isoformat(),
            "llm_context_for_review": {
                "source_metadata": source_metadata,
                "target_variables": target_variables,
                "note": "Agent can use this context to refine mappings using semantic understanding"
            }
        }

        return {
            "success": True,
            "mapping_spec": spec,
            "summary": {
                "columns_mapped": len(column_mappings),
                "high_confidence": len([m for m in column_mappings if m["confidence"] >= 80]),
                "medium_confidence": len([m for m in column_mappings if 60 <= m["confidence"] < 80]),
                "low_confidence": len([m for m in column_mappings if m["confidence"] < 60]),
                "unmapped_required": len(unmapped_required),
                "unmapped_sources": len(unmapped_sources),
            },
            "recommendation": "Review mappings with confidence < 80. Agent should analyze unmapped columns and required variables."
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
async def get_sdtm_variable_definitions(domain: str) -> Dict[str, Any]:
    """
    Get SDTM variable definitions with labels for a domain.

    Returns comprehensive variable information including:
    - Variable name
    - Label/description
    - Data type (Char/Num)
    - Core requirement (Req/Exp/Perm)

    Use this to understand what each SDTM variable represents
    and make informed mapping decisions.

    Args:
        domain: SDTM domain code (e.g., 'DM', 'AE', 'CM', 'VS', 'LB')

    Returns:
        Variable definitions with labels and metadata
    """
    domain = domain.upper()

    if domain not in SDTM_VARIABLE_DEFINITIONS:
        # Return generic findings domain structure
        return {
            "success": True,
            "domain": domain,
            "variables": [],
            "note": f"No predefined structure for {domain}. Use SDTM-IG 3.4 for reference.",
            "generic_structure": {
                "identifiers": ["STUDYID", "DOMAIN", "USUBJID", f"{domain}SEQ"],
                "test_vars": [f"{domain}TESTCD", f"{domain}TEST"],
                "result_vars": [f"{domain}ORRES", f"{domain}ORRESU", f"{domain}STRESC", f"{domain}STRESN", f"{domain}STRESU"],
                "timing_vars": ["VISITNUM", "VISIT", f"{domain}DTC", f"{domain}DY"],
                "status_vars": [f"{domain}STAT", f"{domain}REASND"],
            }
        }

    vars_info = SDTM_VARIABLE_DEFINITIONS[domain]

    # Categorize variables
    identifiers = []
    topic_vars = []
    result_vars = []
    timing_vars = []
    other_vars = []

    for var_name, var_info in vars_info.items():
        var_entry = {
            "variable": var_name,
            "label": var_info["label"],
            "type": var_info["type"],
            "core": var_info["core"],
        }

        if var_name in ["STUDYID", "DOMAIN", "USUBJID"] or var_name.endswith("SEQ"):
            identifiers.append(var_entry)
        elif "TESTCD" in var_name or "TEST" in var_name or "TRT" in var_name or "TERM" in var_name:
            topic_vars.append(var_entry)
        elif "ORRES" in var_name or "STRES" in var_name or "NR" in var_name:
            result_vars.append(var_entry)
        elif "DTC" in var_name or "DY" in var_name or "VISIT" in var_name or "TPT" in var_name:
            timing_vars.append(var_entry)
        else:
            other_vars.append(var_entry)

    return {
        "success": True,
        "domain": domain,
        "total_variables": len(vars_info),
        "categories": {
            "identifiers": identifiers,
            "topic_variables": topic_vars,
            "result_variables": result_vars,
            "timing_variables": timing_vars,
            "other_variables": other_vars,
        },
        "required_variables": [v for v in identifiers + topic_vars + result_vars + timing_vars + other_vars if v["core"] == "Req"],
        "expected_variables": [v for v in identifiers + topic_vars + result_vars + timing_vars + other_vars if v["core"] == "Exp"],
    }


@tool
async def analyze_source_for_sdtm(
    source_file: str,
    target_domain: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze source file metadata to prepare for SDTM mapping.

    Extracts comprehensive metadata about source columns including:
    - Column names and inferred meanings
    - Data types and sample values
    - Null percentages and unique counts
    - Suggested SDTM variable mappings based on content analysis

    Use this tool BEFORE mapping to understand the source data structure.
    The output provides context for intelligent mapping decisions.

    Args:
        source_file: Path to source CSV file
        target_domain: Optional target domain for focused analysis

    Returns:
        Detailed source metadata with mapping suggestions
    """
    try:
        df = await async_read_csv(source_file)

        columns_analysis = []
        for col in df.columns:
            # Get sample values
            non_null = df[col].dropna()
            samples = non_null.head(10).tolist() if len(non_null) > 0 else []

            # Analyze content patterns
            content_analysis = {
                "appears_to_be_id": any(kw in col.lower() for kw in ["id", "no", "num", "code", "cd"]),
                "appears_to_be_date": any(kw in col.lower() for kw in ["date", "dt", "time", "dtc"]),
                "appears_to_be_name": any(kw in col.lower() for kw in ["name", "term", "desc", "txt", "text"]),
                "appears_to_be_result": any(kw in col.lower() for kw in ["result", "value", "val", "res", "score"]),
                "appears_to_be_unit": any(kw in col.lower() for kw in ["unit", "uom", "u"]),
                "appears_to_be_flag": any(kw in col.lower() for kw in ["flag", "fl", "ind", "yn"]),
            }

            # Infer data nature from samples
            if len(samples) > 0:
                sample_str = str(samples[0])
                if any(c in sample_str for c in ['-', '/', 'T']) and len(sample_str) >= 8:
                    content_analysis["likely_content"] = "date/datetime"
                elif all(str(s).replace('.','').replace('-','').isdigit() for s in samples[:5] if pd.notna(s)):
                    content_analysis["likely_content"] = "numeric"
                elif all(str(s).upper() in ['Y', 'N', 'YES', 'NO', 'TRUE', 'FALSE', '1', '0'] for s in samples[:5] if pd.notna(s)):
                    content_analysis["likely_content"] = "boolean/flag"
                else:
                    content_analysis["likely_content"] = "text"

            # Suggest SDTM variable type
            sdtm_suggestions = []
            col_lower = col.lower()

            if "subj" in col_lower or "patient" in col_lower:
                sdtm_suggestions.append({"var": "USUBJID/SUBJID", "reason": "Subject identifier pattern"})
            if "site" in col_lower or "center" in col_lower:
                sdtm_suggestions.append({"var": "SITEID", "reason": "Site identifier pattern"})
            if "visit" in col_lower:
                sdtm_suggestions.append({"var": "VISIT/VISITNUM", "reason": "Visit pattern"})
            if content_analysis.get("appears_to_be_date"):
                sdtm_suggestions.append({"var": "--DTC", "reason": "Date pattern in name"})
            if content_analysis.get("appears_to_be_result"):
                sdtm_suggestions.append({"var": "--ORRES", "reason": "Result pattern in name"})
            if content_analysis.get("appears_to_be_unit"):
                sdtm_suggestions.append({"var": "--ORRESU", "reason": "Unit pattern in name"})

            columns_analysis.append({
                "column": col,
                "dtype": str(df[col].dtype),
                "null_count": int(df[col].isna().sum()),
                "null_pct": round(df[col].isna().sum() / len(df) * 100, 1),
                "unique_values": int(df[col].nunique()),
                "sample_values": [str(v) for v in samples[:5]],
                "content_analysis": content_analysis,
                "sdtm_suggestions": sdtm_suggestions,
            })

        # Suggest target domain if not provided
        domain_suggestions = []
        col_names_lower = " ".join(c.lower() for c in df.columns)

        if any(kw in col_names_lower for kw in ["adverse", "aeterm", "ae_"]):
            domain_suggestions.append({"domain": "AE", "reason": "Adverse event patterns found"})
        if any(kw in col_names_lower for kw in ["medication", "drug", "conmed", "cm_"]):
            domain_suggestions.append({"domain": "CM", "reason": "Concomitant medication patterns found"})
        if any(kw in col_names_lower for kw in ["vital", "bp", "pulse", "temp", "vs_"]):
            domain_suggestions.append({"domain": "VS", "reason": "Vital signs patterns found"})
        if any(kw in col_names_lower for kw in ["lab", "test", "result", "specimen", "lb_"]):
            domain_suggestions.append({"domain": "LB", "reason": "Lab test patterns found"})
        if any(kw in col_names_lower for kw in ["demog", "age", "sex", "race", "dm_"]):
            domain_suggestions.append({"domain": "DM", "reason": "Demographics patterns found"})
        if any(kw in col_names_lower for kw in ["medical", "history", "mh_", "medhist"]):
            domain_suggestions.append({"domain": "MH", "reason": "Medical history patterns found"})
        if any(kw in col_names_lower for kw in ["exposure", "dose", "ex_", "treatment"]):
            domain_suggestions.append({"domain": "EX", "reason": "Exposure patterns found"})
        if any(kw in col_names_lower for kw in ["ecg", "eg_", "qt", "pr_interval"]):
            domain_suggestions.append({"domain": "EG", "reason": "ECG patterns found"})

        return {
            "success": True,
            "file_name": os.path.basename(source_file),
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns_analysis": columns_analysis,
            "domain_suggestions": domain_suggestions if not target_domain else [],
            "target_domain": target_domain,
            "recommendation": "Use generate_intelligent_mapping with this analysis context to create SDTM mappings."
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# MAPPING GENERATION TOOLS (Async) - Pattern-Based (Original)
# =============================================================================

@tool
async def generate_mapping_spec(
    source_file: str,
    target_domain: str,
    study_id: str,
) -> Dict[str, Any]:
    """
    Generate SDTM mapping specification for a source file (async).

    Uses column name matching and domain knowledge to create mappings.

    Args:
        source_file: Path to source CSV
        target_domain: Target SDTM domain code
        study_id: Study identifier

    Returns:
        Mapping specification with column mappings
    """
    try:
        # Async CSV read
        df = await async_read_csv(source_file)
        domain = target_domain.upper()

        # Common mapping patterns by domain
        domain_mappings = {
            "DM": {
                # Subject identifier patterns
                "SUBJECT_ID": "SUBJID", "SUBJID": "SUBJID", "SUBJECT": "SUBJID",
                "SUBJECTID": "SUBJID", "PATIENTID": "SUBJID", "PATIENT_ID": "SUBJID",
                "PT_ID": "SUBJID", "PAT_ID": "SUBJID", "SUBJ": "SUBJID",
                "SUBJECT_NUMBER": "SUBJID", "SUBJECTNO": "SUBJID",
                "USUBJID": "USUBJID", "UNIQUE_SUBJ": "USUBJID",

                # Site patterns
                "SITE": "SITEID", "SITEID": "SITEID", "SITE_ID": "SITEID",
                "CENTER": "SITEID", "CENTERID": "SITEID", "CENTER_ID": "SITEID",
                "SITE_NO": "SITEID", "SITENO": "SITEID", "SITE_NUMBER": "SITEID",
                "INVSITE": "SITEID", "INVESTIGATOR_SITE": "SITEID",

                # Investigator patterns
                "INVID": "INVID", "INV_ID": "INVID", "INVESTIGATOR_ID": "INVID",
                "INVNAM": "INVNAM", "INV_NAME": "INVNAM", "INVESTIGATOR_NAME": "INVNAM",
                "INVESTIGATOR": "INVNAM", "PI": "INVNAM", "PI_NAME": "INVNAM",

                # Demographics patterns
                "AGE": "AGE", "PATIENT_AGE": "AGE", "SUBJECT_AGE": "AGE",
                "AGEU": "AGEU", "AGE_UNIT": "AGEU", "AGEUNIT": "AGEU",

                "SEX": "SEX", "GENDER": "SEX", "PATIENT_SEX": "SEX",
                "SUBJECT_SEX": "SEX", "SUBJECT_GENDER": "SEX",

                "RACE": "RACE", "PATIENT_RACE": "RACE", "SUBJECT_RACE": "RACE",

                "ETHNIC": "ETHNIC", "ETHNICITY": "ETHNIC", "PATIENT_ETHNICITY": "ETHNIC",
                "SUBJECT_ETHNICITY": "ETHNIC",

                "COUNTRY": "COUNTRY", "PATIENT_COUNTRY": "COUNTRY",
                "STUDY_COUNTRY": "COUNTRY", "NATION": "COUNTRY",

                # Birth date patterns
                "BIRTH_DATE": "BRTHDTC", "DOB": "BRTHDTC", "BRTHDTC": "BRTHDTC",
                "BIRTHDATE": "BRTHDTC", "DATE_OF_BIRTH": "BRTHDTC",
                "DATEOFBIRTH": "BRTHDTC", "BIRTHDAY": "BRTHDTC",

                # Arm/treatment patterns
                "ARM": "ARM", "TREATMENT_ARM": "ARM", "TREATMENT": "ARM",
                "TREATMENTARM": "ARM", "TRT_ARM": "ARM", "TRTARM": "ARM",
                "ARMCD": "ARMCD", "ARM_CODE": "ARMCD", "TREATMENTCD": "ARMCD",
                "ACTARM": "ACTARM", "ACTUAL_ARM": "ACTARM", "ACTUALARM": "ACTARM",
                "ACTARMCD": "ACTARMCD", "ACTUAL_ARM_CODE": "ACTARMCD",

                # Reference date patterns
                "RFSTDTC": "RFSTDTC", "REF_START_DATE": "RFSTDTC", "REFSTARTDATE": "RFSTDTC",
                "FIRST_DOSE_DATE": "RFSTDTC", "FIRSTDOSEDATE": "RFSTDTC",
                "RFENDTC": "RFENDTC", "REF_END_DATE": "RFENDTC", "REFENDDATE": "RFENDTC",
                "LAST_DOSE_DATE": "RFENDTC", "LASTDOSEDATE": "RFENDTC",
                "RFXSTDTC": "RFXSTDTC", "FIRST_EXPOSURE_DATE": "RFXSTDTC",
                "RFXENDTC": "RFXENDTC", "LAST_EXPOSURE_DATE": "RFXENDTC",
                "RFICDTC": "RFICDTC", "INFORMED_CONSENT_DATE": "RFICDTC",
                "CONSENT_DATE": "RFICDTC", "CONSENTDATE": "RFICDTC", "IC_DATE": "RFICDTC",
                "RFPENDTC": "RFPENDTC", "PARTICIPATION_END_DATE": "RFPENDTC",

                # Death patterns
                "DTHDTC": "DTHDTC", "DEATH_DATE": "DTHDTC", "DEATHDATE": "DTHDTC",
                "DATE_OF_DEATH": "DTHDTC", "DEATHDTC": "DTHDTC",
                "DTHFL": "DTHFL", "DEATH_FLAG": "DTHFL", "DEATHFLAG": "DTHFL",
                "DECEASED": "DTHFL", "DIED": "DTHFL",

                # DM-specific date/time
                "DMDTC": "DMDTC", "DM_DATE": "DMDTC", "DMDATE": "DMDTC",
                "DMDY": "DMDY", "DM_DAY": "DMDY", "DMDAY": "DMDY",
            },
            "AE": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",
                "SUBJECTID": "USUBJID", "PATIENTID": "USUBJID", "PATIENT_ID": "USUBJID",

                # AE Term patterns (AETERM)
                "AETERM": "AETERM", "ADVERSE_EVENT": "AETERM", "AE_TERM": "AETERM",
                "AE_VERBATIM": "AETERM", "VERBATIM": "AETERM", "AEVERBATIM": "AETERM",
                "AE_DESC": "AETERM", "AEDESC": "AETERM", "EVENT_TERM": "AETERM",
                "AE_NAME": "AETERM", "AENAME": "AETERM", "AE_TEXT": "AETERM",

                # Modified term patterns (AEMODIFY)
                "AEMODIFY": "AEMODIFY", "MODIFIED_TERM": "AEMODIFY", "MOD_TERM": "AEMODIFY",

                # Decoded term patterns (AEDECOD - MedDRA PT)
                "AEDECOD": "AEDECOD", "PREFERRED_TERM": "AEDECOD", "PT": "AEDECOD",
                "MEDDRA_PT": "AEDECOD", "MEDDRAPT": "AEDECOD", "DECOD": "AEDECOD",
                "AE_PT": "AEDECOD", "AEPT": "AEDECOD", "CODED_TERM": "AEDECOD",

                # MedDRA hierarchy patterns
                "AELLT": "AELLT", "LLT": "AELLT", "LOW_LEVEL_TERM": "AELLT",
                "AELLTCD": "AELLTCD", "LLTCD": "AELLTCD", "LLT_CODE": "AELLTCD",
                "AEPTCD": "AEPTCD", "PTCD": "AEPTCD", "PT_CODE": "AEPTCD",
                "AEHLT": "AEHLT", "HLT": "AEHLT", "HIGH_LEVEL_TERM": "AEHLT",
                "AEHLTCD": "AEHLTCD", "HLTCD": "AEHLTCD", "HLT_CODE": "AEHLTCD",
                "AEHLGT": "AEHLGT", "HLGT": "AEHLGT", "HIGH_LEVEL_GROUP_TERM": "AEHLGT",
                "AEHLGTCD": "AEHLGTCD", "HLGTCD": "AEHLGTCD",
                "AEBODSYS": "AEBODSYS", "BODSYS": "AEBODSYS", "BODY_SYSTEM": "AEBODSYS",
                "SOC": "AEBODSYS", "SYSTEM_ORGAN_CLASS": "AEBODSYS",
                "AEBDSYCD": "AEBDSYCD", "BODSYSCD": "AEBDSYCD", "SOC_CODE": "AEBDSYCD",
                "AESOC": "AESOC", "AESOCCD": "AESOCCD",

                # Category patterns
                "AECAT": "AECAT", "CATEGORY": "AECAT", "AE_CATEGORY": "AECAT",
                "AESCAT": "AESCAT", "SUBCATEGORY": "AESCAT", "AE_SUBCATEGORY": "AESCAT",

                # Severity patterns (AESEV)
                "SEVERITY": "AESEV", "AESEV": "AESEV", "SEV": "AESEV",
                "AE_SEVERITY": "AESEV", "GRADE": "AESEV", "AE_GRADE": "AESEV",
                "CTCAE_GRADE": "AESEV", "TOXICITY_GRADE": "AESEV",
                "AETOXGR": "AETOXGR", "TOX_GRADE": "AETOXGR", "TOXGR": "AETOXGR",

                # Serious patterns (AESER)
                "SERIOUS": "AESER", "AESER": "AESER", "SER": "AESER",
                "AE_SERIOUS": "AESER", "SAE": "AESER", "IS_SERIOUS": "AESER",
                "SERIOUS_AE": "AESER", "SERIOUSAE": "AESER",

                # Serious criteria patterns
                "AESDTH": "AESDTH", "DEATH": "AESDTH", "RESULTED_DEATH": "AESDTH",
                "AESLIFE": "AESLIFE", "LIFE_THREAT": "AESLIFE", "LIFETHREAT": "AESLIFE",
                "AESHOSP": "AESHOSP", "HOSPITALIZATION": "AESHOSP", "HOSP": "AESHOSP",
                "AESDISAB": "AESDISAB", "DISABILITY": "AESDISAB", "DISAB": "AESDISAB",
                "AESCONG": "AESCONG", "CONGENITAL": "AESCONG", "CONG_ANOMALY": "AESCONG",
                "AESMIE": "AESMIE", "MED_IMPORTANT": "AESMIE", "IMPORTANT_EVENT": "AESMIE",

                # Causality/relatedness patterns (AEREL)
                "AEREL": "AEREL", "RELATEDNESS": "AEREL", "RELATED": "AEREL",
                "CAUSALITY": "AEREL", "AE_RELATIONSHIP": "AEREL", "RELATIONSHIP": "AEREL",
                "DRUG_RELATED": "AEREL", "DRUGRELATED": "AEREL",
                "AERELNST": "AERELNST", "REL_STUDY_DRUG": "AERELNST",

                # Action taken patterns (AEACN)
                "AEACN": "AEACN", "ACTION": "AEACN", "ACTION_TAKEN": "AEACN",
                "AE_ACTION": "AEACN", "AEACTION": "AEACN", "DRUG_ACTION": "AEACN",
                "AEACNOTH": "AEACNOTH", "OTHER_ACTION": "AEACNOTH",
                "AECONTRT": "AECONTRT", "CONCOM_TRT": "AECONTRT", "TREAT_AE": "AECONTRT",

                # Outcome patterns (AEOUT)
                "AEOUT": "AEOUT", "OUTCOME": "AEOUT", "AE_OUTCOME": "AEOUT",
                "RESOLUTION": "AEOUT", "RESOLVED": "AEOUT",

                # Pattern patterns (AEPATT)
                "AEPATT": "AEPATT", "PATTERN": "AEPATT", "AE_PATTERN": "AEPATT",

                # Date patterns
                "START_DATE": "AESTDTC", "AESTDTC": "AESTDTC", "STARTDATE": "AESTDTC",
                "ONSET_DATE": "AESTDTC", "ONSETDATE": "AESTDTC", "AE_START": "AESTDTC",
                "AESTART": "AESTDTC", "BEGIN_DATE": "AESTDTC", "AEONSET": "AESTDTC",
                "END_DATE": "AEENDTC", "AEENDTC": "AEENDTC", "ENDDATE": "AEENDTC",
                "RESOLVE_DATE": "AEENDTC", "RESOLUTION_DATE": "AEENDTC",
                "AE_END": "AEENDTC", "AEEND": "AEENDTC", "STOP_DATE": "AEENDTC",
                "AEDTC": "AEDTC", "AE_DATE": "AEDTC", "AEDATE": "AEDTC",

                # Study day patterns
                "AESTDY": "AESTDY", "START_DAY": "AESTDY", "STARTDAY": "AESTDY",
                "ONSET_DAY": "AESTDY", "STDY": "AESTDY",
                "AEENDY": "AEENDY", "END_DAY": "AEENDY", "ENDDAY": "AEENDY",
                "RESOLUTION_DAY": "AEENDY", "ENDY": "AEENDY",

                # Duration patterns (AEDUR)
                "AEDUR": "AEDUR", "DURATION": "AEDUR", "AE_DURATION": "AEDUR",

                # Reference time patterns
                "AESTRF": "AESTRF", "START_REF": "AESTRF", "STRF": "AESTRF",
                "AEENRF": "AEENRF", "END_REF": "AEENRF", "ENRF": "AEENRF",
                "ONGOING": "AEENRF", "CONTINUING": "AEENRF",

                # Pre-specified patterns
                "AEPRESP": "AEPRESP", "PRESPECIFIED": "AEPRESP", "PRESP": "AEPRESP",

                # Occurrence patterns
                "AEOCCUR": "AEOCCUR", "OCCURRED": "AEOCCUR", "OCCUR": "AEOCCUR",

                # Status patterns
                "AESTAT": "AESTAT", "STATUS": "AESTAT", "AE_STATUS": "AESTAT",
                "AEREASND": "AEREASND", "REASON_NOT_DONE": "AEREASND",

                # Visit patterns
                "VISITNUM": "VISITNUM", "VISIT_NUMBER": "VISITNUM", "VISITNO": "VISITNUM",
                "VISIT": "VISIT", "VISITNAME": "VISIT", "VISIT_NAME": "VISIT",

                # Epoch
                "EPOCH": "EPOCH", "STUDY_EPOCH": "EPOCH", "PHASE": "EPOCH",
            },
            "VS": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",
                "SUBJECTID": "USUBJID", "PATIENTID": "USUBJID", "PATIENT_ID": "USUBJID",

                # Test code patterns (VSTESTCD)
                "TEST_CODE": "VSTESTCD", "VSTESTCD": "VSTESTCD", "TESTCD": "VSTESTCD",
                "VITAL_CODE": "VSTESTCD", "VITALCODE": "VSTESTCD", "PARAM": "VSTESTCD",
                "PARAMCD": "VSTESTCD", "PARAMETER_CODE": "VSTESTCD", "VSCD": "VSTESTCD",

                # Test name patterns (VSTEST)
                "TEST_NAME": "VSTEST", "VSTEST": "VSTEST", "TEST": "VSTEST",
                "VITAL_SIGN": "VSTEST", "VITALSIGN": "VSTEST", "VITAL": "VSTEST",
                "PARAMETER": "VSTEST", "PARAM_NAME": "VSTEST", "PARAMNAME": "VSTEST",
                "MEASUREMENT": "VSTEST", "MEASURE": "VSTEST",

                # Category patterns (VSCAT)
                "VSCAT": "VSCAT", "CATEGORY": "VSCAT", "CAT": "VSCAT",
                "VS_CATEGORY": "VSCAT", "VITAL_CATEGORY": "VSCAT",

                # Original result patterns (VSORRES)
                "RESULT": "VSORRES", "VSORRES": "VSORRES", "VALUE": "VSORRES",
                "ORRES": "VSORRES", "ORIGINAL_RESULT": "VSORRES", "ORIG_RESULT": "VSORRES",
                "MEASUREMENT_VALUE": "VSORRES", "READING": "VSORRES",
                "SYSTOLIC": "VSORRES", "DIASTOLIC": "VSORRES", "PULSE": "VSORRES",
                "TEMP": "VSORRES", "TEMPERATURE": "VSORRES", "WEIGHT": "VSORRES",
                "HEIGHT": "VSORRES", "BMI": "VSORRES", "RESP": "VSORRES",

                # Original unit patterns (VSORRESU)
                "UNIT": "VSORRESU", "VSORRESU": "VSORRESU", "UNITS": "VSORRESU",
                "ORRESU": "VSORRESU", "ORIGINAL_UNIT": "VSORRESU", "UOM": "VSORRESU",

                # Standard result patterns (VSSTRESC, VSSTRESN)
                "VSSTRESC": "VSSTRESC", "STRESC": "VSSTRESC", "STD_RESULT_C": "VSSTRESC",
                "VSSTRESN": "VSSTRESN", "STRESN": "VSSTRESN", "STD_RESULT_N": "VSSTRESN",
                "NUMERIC_RESULT": "VSSTRESN", "NUM_RESULT": "VSSTRESN",

                # Standard unit patterns (VSSTRESU)
                "VSSTRESU": "VSSTRESU", "STRESU": "VSSTRESU", "STD_UNIT": "VSSTRESU",

                # Position patterns (VSPOS)
                "VSPOS": "VSPOS", "POSITION": "VSPOS", "POS": "VSPOS",
                "BODY_POSITION": "VSPOS", "PATIENT_POSITION": "VSPOS",

                # Location patterns (VSLOC)
                "VSLOC": "VSLOC", "LOCATION": "VSLOC", "LOC": "VSLOC",
                "BODY_LOCATION": "VSLOC", "SITE": "VSLOC", "ANATOMIC_LOCATION": "VSLOC",

                # Date/time patterns (VSDTC)
                "DATE": "VSDTC", "VSDTC": "VSDTC", "DATETIME": "VSDTC",
                "VISIT_DATE": "VSDTC", "VISITDATE": "VSDTC", "COLLECTION_DATE": "VSDTC",
                "COLLECTIONDATE": "VSDTC", "ASSESS_DATE": "VSDTC", "ASSESSDATE": "VSDTC",
                "MEASUREMENT_DATE": "VSDTC", "DT": "VSDTC", "VSDATUM": "VSDTC",

                # Study day patterns (VSDY)
                "VSDY": "VSDY", "STUDY_DAY": "VSDY", "STUDYDAY": "VSDY",
                "DAY": "VSDY", "VISIT_DAY": "VSDY",

                # Visit patterns
                "VISITNUM": "VISITNUM", "VISIT_NUMBER": "VISITNUM", "VISITNO": "VISITNUM",
                "VISIT": "VISIT", "VISITNAME": "VISIT", "VISIT_NAME": "VISIT",

                # Timepoint patterns (VSTPT)
                "VSTPT": "VSTPT", "TIMEPOINT": "VSTPT", "TPT": "VSTPT",
                "TIME_POINT": "VSTPT", "PLANNED_TIME": "VSTPT",

                # Baseline flag (VSBLFL)
                "VSBLFL": "VSBLFL", "BASELINE": "VSBLFL", "BLFL": "VSBLFL",
                "BASELINE_FLAG": "VSBLFL", "IS_BASELINE": "VSBLFL",

                # Status patterns (VSSTAT)
                "VSSTAT": "VSSTAT", "STATUS": "VSSTAT", "STAT": "VSSTAT",

                # Reason not done (VSREASND)
                "VSREASND": "VSREASND", "REASON_NOT_DONE": "VSREASND",
                "REASONND": "VSREASND", "REASON": "VSREASND",

                # Epoch
                "EPOCH": "EPOCH", "STUDY_EPOCH": "EPOCH", "PHASE": "EPOCH",
            },
            "LB": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",
                "SUBJECTID": "USUBJID", "PATIENTID": "USUBJID", "PATIENT_ID": "USUBJID",

                # Test code patterns (LBTESTCD)
                "TEST_CODE": "LBTESTCD", "LBTESTCD": "LBTESTCD", "TESTCD": "LBTESTCD",
                "LAB_CODE": "LBTESTCD", "LABCODE": "LBTESTCD", "PARAM": "LBTESTCD",
                "PARAMCD": "LBTESTCD", "PARAMETER_CODE": "LBTESTCD", "LBCD": "LBTESTCD",
                "ANALYTE_CODE": "LBTESTCD", "ANALYTECODE": "LBTESTCD",

                # Test name patterns (LBTEST)
                "TEST_NAME": "LBTEST", "LBTEST": "LBTEST", "TEST": "LBTEST",
                "LAB_TEST": "LBTEST", "LABTEST": "LBTEST", "LAB": "LBTEST",
                "PARAMETER": "LBTEST", "PARAM_NAME": "LBTEST", "PARAMNAME": "LBTEST",
                "ANALYTE": "LBTEST", "ANALYTE_NAME": "LBTEST",

                # Category patterns (LBCAT)
                "LBCAT": "LBCAT", "CATEGORY": "LBCAT", "CAT": "LBCAT",
                "LAB_CATEGORY": "LBCAT", "TEST_CATEGORY": "LBCAT",
                "PANEL": "LBCAT", "LAB_PANEL": "LBCAT",

                # Original result patterns (LBORRES)
                "RESULT": "LBORRES", "LBORRES": "LBORRES", "VALUE": "LBORRES",
                "ORRES": "LBORRES", "ORIGINAL_RESULT": "LBORRES", "ORIG_RESULT": "LBORRES",
                "LAB_RESULT": "LBORRES", "LABRESULT": "LBORRES", "AVAL": "LBORRES",

                # Original unit patterns (LBORRESU)
                "UNIT": "LBORRESU", "LBORRESU": "LBORRESU", "UNITS": "LBORRESU",
                "ORRESU": "LBORRESU", "ORIGINAL_UNIT": "LBORRESU", "UOM": "LBORRESU",

                # Standard result patterns (LBSTRESC, LBSTRESN)
                "LBSTRESC": "LBSTRESC", "STRESC": "LBSTRESC", "STD_RESULT_C": "LBSTRESC",
                "LBSTRESN": "LBSTRESN", "STRESN": "LBSTRESN", "STD_RESULT_N": "LBSTRESN",
                "NUMERIC_RESULT": "LBSTRESN", "NUM_RESULT": "LBSTRESN",

                # Standard unit patterns (LBSTRESU)
                "LBSTRESU": "LBSTRESU", "STRESU": "LBSTRESU", "STD_UNIT": "LBSTRESU",

                # Reference range patterns
                "NORMAL_LOW": "LBSTNRLO", "LBSTNRLO": "LBSTNRLO", "LOW_NORMAL": "LBSTNRLO",
                "REF_LOW": "LBSTNRLO", "REFLOW": "LBSTNRLO", "LOWER_LIMIT": "LBSTNRLO",
                "NORMAL_HIGH": "LBSTNRHI", "LBSTNRHI": "LBSTNRHI", "HIGH_NORMAL": "LBSTNRHI",
                "REF_HIGH": "LBSTNRHI", "REFHIGH": "LBSTNRHI", "UPPER_LIMIT": "LBSTNRHI",
                "LBORNRLO": "LBORNRLO", "ORIG_REF_LOW": "LBORNRLO",
                "LBORNRHI": "LBORNRHI", "ORIG_REF_HIGH": "LBORNRHI",

                # Normal range indicator (LBNRIND)
                "LBNRIND": "LBNRIND", "NRIND": "LBNRIND", "NORMAL_INDICATOR": "LBNRIND",
                "ABNORMAL": "LBNRIND", "ABNORMAL_FLAG": "LBNRIND", "FLAG": "LBNRIND",
                "HIGH_LOW": "LBNRIND", "HIGHLOW": "LBNRIND",

                # Specimen patterns (LBSPEC)
                "LBSPEC": "LBSPEC", "SPECIMEN": "LBSPEC", "SPEC": "LBSPEC",
                "SAMPLE_TYPE": "LBSPEC", "SAMPLETYPE": "LBSPEC", "MATRIX": "LBSPEC",

                # Method patterns (LBMETHOD)
                "LBMETHOD": "LBMETHOD", "METHOD": "LBMETHOD", "TEST_METHOD": "LBMETHOD",
                "ANALYSIS_METHOD": "LBMETHOD",

                # Lab name patterns (LBNAM)
                "LBNAM": "LBNAM", "LAB_NAME": "LBNAM", "LABNAME": "LBNAM",
                "LABORATORY": "LBNAM", "LAB_FACILITY": "LBNAM",

                # Date/time patterns (LBDTC)
                "DATE": "LBDTC", "LBDTC": "LBDTC", "DATETIME": "LBDTC",
                "COLLECTION_DATE": "LBDTC", "COLLECTIONDATE": "LBDTC",
                "SAMPLE_DATE": "LBDTC", "SAMPLEDATE": "LBDTC",
                "LAB_DATE": "LBDTC", "LABDATE": "LBDTC", "DT": "LBDTC",

                # Study day patterns (LBDY)
                "LBDY": "LBDY", "STUDY_DAY": "LBDY", "STUDYDAY": "LBDY",
                "DAY": "LBDY", "COLLECTION_DAY": "LBDY",

                # Visit patterns
                "VISITNUM": "VISITNUM", "VISIT_NUMBER": "VISITNUM", "VISITNO": "VISITNUM",
                "VISIT": "VISIT", "VISITNAME": "VISIT", "VISIT_NAME": "VISIT",

                # Timepoint patterns (LBTPT)
                "LBTPT": "LBTPT", "TIMEPOINT": "LBTPT", "TPT": "LBTPT",
                "TIME_POINT": "LBTPT", "PLANNED_TIME": "LBTPT",

                # Baseline flag (LBLFL)
                "LBBLFL": "LBBLFL", "BASELINE": "LBBLFL", "BLFL": "LBBLFL",
                "BASELINE_FLAG": "LBBLFL", "IS_BASELINE": "LBBLFL",

                # Fasting status (LBFAST)
                "LBFAST": "LBFAST", "FASTING": "LBFAST", "FAST": "LBFAST",
                "FASTING_STATUS": "LBFAST",

                # Status patterns (LBSTAT)
                "LBSTAT": "LBSTAT", "STATUS": "LBSTAT", "STAT": "LBSTAT",

                # Reason not done (LBREASND)
                "LBREASND": "LBREASND", "REASON_NOT_DONE": "LBREASND",
                "REASONND": "LBREASND", "REASON": "LBREASND",

                # LOINC code
                "LBLOINC": "LBLOINC", "LOINC": "LBLOINC", "LOINC_CODE": "LBLOINC",

                # Epoch
                "EPOCH": "EPOCH", "STUDY_EPOCH": "EPOCH", "PHASE": "EPOCH",
            },
            "CM": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",
                "SUBJECTID": "USUBJID", "PATIENTID": "USUBJID", "PATIENT_ID": "USUBJID",
                "PT_ID": "USUBJID", "PAT_ID": "USUBJID", "SUBJ": "USUBJID",

                # Medication name patterns (CMTRT)
                "MEDICATION": "CMTRT", "CMTRT": "CMTRT", "DRUG": "CMTRT",
                "DRUG_NAME": "CMTRT", "DRUGNAME": "CMTRT", "MED_NAME": "CMTRT",
                "MEDNAME": "CMTRT", "MEDICINE": "CMTRT", "TREATMENT": "CMTRT",
                "TRT": "CMTRT", "CONMED": "CMTRT", "CONMEDICATION": "CMTRT",
                "CMTERM": "CMTRT", "MEDTERM": "CMTRT", "DRUGTERM": "CMTRT",
                "MEDICATION_NAME": "CMTRT", "MEDICATIONNAME": "CMTRT",
                "CON_MED": "CMTRT", "CONCOM_MED": "CMTRT", "CMED": "CMTRT",

                # Modified medication name (CMMODIFY)
                "CMMODIFY": "CMMODIFY", "MODIFIED_NAME": "CMMODIFY",
                "MOD_NAME": "CMMODIFY", "MODNAME": "CMMODIFY",

                # Decoded medication name (CMDECOD)
                "CMDECOD": "CMDECOD", "DECODED": "CMDECOD", "DECOD": "CMDECOD",
                "WHODRUG": "CMDECOD", "ATC_CODE": "CMDECOD", "ATCCODE": "CMDECOD",
                "GENERIC_NAME": "CMDECOD", "GENERICNAME": "CMDECOD",

                # Category patterns (CMCAT)
                "CMCAT": "CMCAT", "CATEGORY": "CMCAT", "CAT": "CMCAT",
                "MED_CATEGORY": "CMCAT", "MEDCAT": "CMCAT", "DRUG_CAT": "CMCAT",
                "MEDICATION_CATEGORY": "CMCAT", "MEDTYPE": "CMCAT",

                # Subcategory patterns (CMSCAT)
                "CMSCAT": "CMSCAT", "SUBCATEGORY": "CMSCAT", "SUBCAT": "CMSCAT",
                "SUB_CATEGORY": "CMSCAT", "SCAT": "CMSCAT",

                # Indication patterns (CMINDC)
                "CMINDC": "CMINDC", "INDICATION": "CMINDC", "INDC": "CMINDC",
                "REASON": "CMINDC", "MED_REASON": "CMINDC", "REASON_FOR_USE": "CMINDC",
                "PURPOSE": "CMINDC", "USE_FOR": "CMINDC", "DIAGNOSIS": "CMINDC",
                "CONDITION": "CMINDC", "TREATMENT_FOR": "CMINDC",

                # ATC Class patterns (CMCLAS, CMCLASCD)
                "CMCLAS": "CMCLAS", "CLASS": "CMCLAS", "DRUG_CLASS": "CMCLAS",
                "MED_CLASS": "CMCLAS", "ATC_CLASS": "CMCLAS", "THERAPEUTIC_CLASS": "CMCLAS",
                "CMCLASCD": "CMCLASCD", "CLASS_CODE": "CMCLASCD", "CLASSCD": "CMCLASCD",
                "ATC": "CMCLASCD", "ATC_CD": "CMCLASCD",

                # Dose patterns (CMDOSE)
                "DOSE": "CMDOSE", "CMDOSE": "CMDOSE", "DOSAGE": "CMDOSE",
                "DOSE_AMT": "CMDOSE", "DOSEAMT": "CMDOSE", "DOSE_AMOUNT": "CMDOSE",
                "AMT": "CMDOSE", "AMOUNT": "CMDOSE", "STRENGTH": "CMDOSE",
                "DOSE_STRENGTH": "CMDOSE", "DOSESTRENGTH": "CMDOSE",

                # Dose text patterns (CMDOSTXT)
                "CMDOSTXT": "CMDOSTXT", "DOSE_TEXT": "CMDOSTXT", "DOSETXT": "CMDOSTXT",
                "DOSE_DESC": "CMDOSTXT", "DOSEDESC": "CMDOSTXT",

                # Dose unit patterns (CMDOSU)
                "UNIT": "CMDOSU", "CMDOSU": "CMDOSU", "DOSE_UNIT": "CMDOSU",
                "DOSEUNIT": "CMDOSU", "UNITS": "CMDOSU", "DOSEUNITS": "CMDOSU",
                "UOM": "CMDOSU", "DOSE_UOM": "CMDOSU",

                # Dose form patterns (CMDOSFRM)
                "CMDOSFRM": "CMDOSFRM", "FORM": "CMDOSFRM", "DOSE_FORM": "CMDOSFRM",
                "DOSEFORM": "CMDOSFRM", "DOSAGE_FORM": "CMDOSFRM", "FORMULATION": "CMDOSFRM",
                "DRUG_FORM": "CMDOSFRM", "MEDFORM": "CMDOSFRM",

                # Dose frequency patterns (CMDOSFRQ)
                "CMDOSFRQ": "CMDOSFRQ", "FREQUENCY": "CMDOSFRQ", "FREQ": "CMDOSFRQ",
                "DOSE_FREQ": "CMDOSFRQ", "DOSEFREQ": "CMDOSFRQ", "DOSING_FREQ": "CMDOSFRQ",
                "SCHEDULE": "CMDOSFRQ", "REGIMEN": "CMDOSFRQ", "HOW_OFTEN": "CMDOSFRQ",

                # Total daily dose patterns (CMDOSTOT)
                "CMDOSTOT": "CMDOSTOT", "TOTAL_DOSE": "CMDOSTOT", "TOTALDOSE": "CMDOSTOT",
                "DAILY_DOSE": "CMDOSTOT", "DAILYDOSE": "CMDOSTOT", "TOT_DOSE": "CMDOSTOT",

                # Route patterns (CMROUTE)
                "CMROUTE": "CMROUTE", "ROUTE": "CMROUTE", "ADMIN_ROUTE": "CMROUTE",
                "ADMINROUTE": "CMROUTE", "ROUTE_OF_ADMIN": "CMROUTE",
                "ADMINISTRATION_ROUTE": "CMROUTE", "ROA": "CMROUTE",

                # Status patterns (CMSTAT)
                "CMSTAT": "CMSTAT", "STATUS": "CMSTAT", "MED_STATUS": "CMSTAT",

                # Reason not done patterns (CMREASND)
                "CMREASND": "CMREASND", "REASON_NOT_DONE": "CMREASND",
                "REASONND": "CMREASND", "NOT_DONE_REASON": "CMREASND",

                # Date patterns (CMSTDTC, CMENDTC)
                "START_DATE": "CMSTDTC", "CMSTDTC": "CMSTDTC", "STARTDATE": "CMSTDTC",
                "BEGIN_DATE": "CMSTDTC", "BEGINDATE": "CMSTDTC", "STDT": "CMSTDTC",
                "MED_START": "CMSTDTC", "MEDSTART": "CMSTDTC", "CMSTDT": "CMSTDTC",
                "START_DT": "CMSTDTC", "STARTDT": "CMSTDTC", "CMSTART": "CMSTDTC",
                "END_DATE": "CMENDTC", "CMENDTC": "CMENDTC", "ENDDATE": "CMENDTC",
                "STOP_DATE": "CMENDTC", "STOPDATE": "CMENDTC", "ENDT": "CMENDTC",
                "MED_END": "CMENDTC", "MEDEND": "CMENDTC", "CMENDT": "CMENDTC",
                "END_DT": "CMENDTC", "ENDDT": "CMENDTC", "CMSTOP": "CMENDTC",

                # Study day patterns (CMSTDY, CMENDY)
                "CMSTDY": "CMSTDY", "START_DAY": "CMSTDY", "STARTDAY": "CMSTDY",
                "STDY": "CMSTDY", "BEGIN_DAY": "CMSTDY",
                "CMENDY": "CMENDY", "END_DAY": "CMENDY", "ENDDAY": "CMENDY",
                "ENDY": "CMENDY", "STOP_DAY": "CMENDY",

                # Timeframe patterns (CMSTRF, CMENRF)
                "CMSTRF": "CMSTRF", "START_REF": "CMSTRF", "STARTREF": "CMSTRF",
                "CMENRF": "CMENRF", "END_REF": "CMENRF", "ENDREF": "CMENRF",

                # Ongoing patterns
                "ONGOING": "CMENRF", "CONTINUING": "CMENRF", "CURRENT": "CMENRF",

                # Epoch patterns
                "EPOCH": "EPOCH", "STUDY_EPOCH": "EPOCH", "PHASE": "EPOCH",

                # Pre-specified patterns
                "CMPRESP": "CMPRESP", "PRESPECIFIED": "CMPRESP", "PRESP": "CMPRESP",

                # Occurrence patterns
                "CMOCCUR": "CMOCCUR", "OCCURRED": "CMOCCUR", "OCCUR": "CMOCCUR",
            },
            # =====================================================================
            # EX - Exposure Domain
            # =====================================================================
            "EX": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",
                "SUBJECTID": "USUBJID", "PATIENTID": "USUBJID", "PATIENT_ID": "USUBJID",

                # Treatment patterns (EXTRT)
                "EXTRT": "EXTRT", "TREATMENT": "EXTRT", "TRT": "EXTRT",
                "DRUG": "EXTRT", "DRUG_NAME": "EXTRT", "STUDY_DRUG": "EXTRT",
                "STUDYDRUG": "EXTRT", "INTERVENTION": "EXTRT", "EXPOSURE": "EXTRT",

                # Category patterns
                "EXCAT": "EXCAT", "CATEGORY": "EXCAT", "CAT": "EXCAT",
                "EXSCAT": "EXSCAT", "SUBCATEGORY": "EXSCAT", "SUBCAT": "EXSCAT",

                # Dose patterns
                "EXDOSE": "EXDOSE", "DOSE": "EXDOSE", "DOSAGE": "EXDOSE",
                "DOSE_AMT": "EXDOSE", "DOSEAMT": "EXDOSE", "AMOUNT": "EXDOSE",
                "EXDOSTXT": "EXDOSTXT", "DOSE_TEXT": "EXDOSTXT", "DOSETXT": "EXDOSTXT",
                "EXDOSU": "EXDOSU", "DOSE_UNIT": "EXDOSU", "UNIT": "EXDOSU",
                "EXDOSFRM": "EXDOSFRM", "DOSE_FORM": "EXDOSFRM", "FORM": "EXDOSFRM",
                "EXDOSFRQ": "EXDOSFRQ", "FREQUENCY": "EXDOSFRQ", "FREQ": "EXDOSFRQ",
                "EXDOSTOT": "EXDOSTOT", "TOTAL_DOSE": "EXDOSTOT", "TOTALDOSE": "EXDOSTOT",

                # Route patterns
                "EXROUTE": "EXROUTE", "ROUTE": "EXROUTE", "ADMIN_ROUTE": "EXROUTE",

                # Lot number
                "EXLOT": "EXLOT", "LOT": "EXLOT", "LOT_NUMBER": "EXLOT", "BATCH": "EXLOT",

                # Location patterns
                "EXLOC": "EXLOC", "LOCATION": "EXLOC", "LOC": "EXLOC",
                "EXLAT": "EXLAT", "LATERALITY": "EXLAT", "LAT": "EXLAT",

                # Adjustment patterns
                "EXADJ": "EXADJ", "ADJUSTMENT": "EXADJ", "ADJ": "EXADJ",
                "DOSE_ADJUSTMENT": "EXADJ", "DOSEADJ": "EXADJ",

                # Status patterns
                "EXSTAT": "EXSTAT", "STATUS": "EXSTAT", "STAT": "EXSTAT",
                "EXREASND": "EXREASND", "REASON_NOT_DONE": "EXREASND",

                # Date patterns
                "EXSTDTC": "EXSTDTC", "START_DATE": "EXSTDTC", "STARTDATE": "EXSTDTC",
                "FIRST_DOSE": "EXSTDTC", "FIRSTDOSE": "EXSTDTC",
                "EXENDTC": "EXENDTC", "END_DATE": "EXENDTC", "ENDDATE": "EXENDTC",
                "LAST_DOSE": "EXENDTC", "LASTDOSE": "EXENDTC",
                "EXDTC": "EXDTC", "EX_DATE": "EXDTC", "EXDATE": "EXDTC",

                # Study day patterns
                "EXSTDY": "EXSTDY", "START_DAY": "EXSTDY", "STDY": "EXSTDY",
                "EXENDY": "EXENDY", "END_DAY": "EXENDY", "ENDY": "EXENDY",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # DS - Disposition Domain
            # =====================================================================
            "DS": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Term patterns (DSTERM)
                "DSTERM": "DSTERM", "DISPOSITION": "DSTERM", "DISP": "DSTERM",
                "DISP_TERM": "DSTERM", "DISPTERM": "DSTERM", "STATUS": "DSTERM",
                "COMPLETION_STATUS": "DSTERM", "COMPLETIONSTATUS": "DSTERM",
                "REASON": "DSTERM", "DISCONTINUATION": "DSTERM",

                # Decoded term (DSDECOD)
                "DSDECOD": "DSDECOD", "DECOD": "DSDECOD", "DECODED": "DSDECOD",
                "STANDARD_TERM": "DSDECOD", "STANDARDTERM": "DSDECOD",

                # Category patterns
                "DSCAT": "DSCAT", "CATEGORY": "DSCAT", "CAT": "DSCAT",
                "DISP_CATEGORY": "DSCAT", "DISPCAT": "DSCAT",
                "DSSCAT": "DSSCAT", "SUBCATEGORY": "DSSCAT", "SUBCAT": "DSSCAT",

                # Date patterns
                "DSSTDTC": "DSSTDTC", "START_DATE": "DSSTDTC", "STARTDATE": "DSSTDTC",
                "DISP_DATE": "DSSTDTC", "DISPDATE": "DSSTDTC",
                "COMPLETION_DATE": "DSSTDTC", "COMPLETIONDATE": "DSSTDTC",
                "DISCONTINUATION_DATE": "DSSTDTC", "DISCDATE": "DSSTDTC",
                "DSDTC": "DSDTC", "DS_DATE": "DSDTC", "DSDATE": "DSDTC",

                # Study day patterns
                "DSSTDY": "DSSTDY", "STUDY_DAY": "DSSTDY", "STDY": "DSSTDY",
                "DSDY": "DSDY", "DAY": "DSDY",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # MH - Medical History Domain
            # =====================================================================
            "MH": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Term patterns (MHTERM)
                "MHTERM": "MHTERM", "MEDICAL_HISTORY": "MHTERM", "MEDHIST": "MHTERM",
                "HISTORY": "MHTERM", "CONDITION": "MHTERM", "DIAGNOSIS": "MHTERM",
                "DISEASE": "MHTERM", "ILLNESS": "MHTERM", "PAST_ILLNESS": "MHTERM",
                "PRIOR_CONDITION": "MHTERM", "PRIORCONDITION": "MHTERM",

                # Modified term (MHMODIFY)
                "MHMODIFY": "MHMODIFY", "MODIFIED_TERM": "MHMODIFY", "MODTERM": "MHMODIFY",

                # Decoded term (MHDECOD)
                "MHDECOD": "MHDECOD", "DECOD": "MHDECOD", "DECODED": "MHDECOD",
                "MEDDRA_PT": "MHDECOD", "MEDDRAPT": "MHDECOD", "PT": "MHDECOD",

                # Body system (MHBODSYS)
                "MHBODSYS": "MHBODSYS", "BODY_SYSTEM": "MHBODSYS", "BODSYS": "MHBODSYS",
                "SOC": "MHBODSYS", "SYSTEM_ORGAN_CLASS": "MHBODSYS",

                # Category patterns
                "MHCAT": "MHCAT", "CATEGORY": "MHCAT", "CAT": "MHCAT",
                "MH_CATEGORY": "MHCAT", "MHCAT": "MHCAT",
                "MHSCAT": "MHSCAT", "SUBCATEGORY": "MHSCAT", "SUBCAT": "MHSCAT",

                # Severity patterns
                "MHSEV": "MHSEV", "SEVERITY": "MHSEV", "SEV": "MHSEV",

                # Pre-specified and occurrence
                "MHPRESP": "MHPRESP", "PRESPECIFIED": "MHPRESP", "PRESP": "MHPRESP",
                "MHOCCUR": "MHOCCUR", "OCCURRED": "MHOCCUR", "OCCUR": "MHOCCUR",

                # Status patterns
                "MHSTAT": "MHSTAT", "STATUS": "MHSTAT", "STAT": "MHSTAT",
                "MHREASND": "MHREASND", "REASON_NOT_DONE": "MHREASND",

                # Date patterns
                "MHSTDTC": "MHSTDTC", "START_DATE": "MHSTDTC", "STARTDATE": "MHSTDTC",
                "ONSET_DATE": "MHSTDTC", "ONSETDATE": "MHSTDTC",
                "MHENDTC": "MHENDTC", "END_DATE": "MHENDTC", "ENDDATE": "MHENDTC",
                "RESOLVE_DATE": "MHENDTC", "RESOLVEDATE": "MHENDTC",
                "MHDTC": "MHDTC", "MH_DATE": "MHDTC", "MHDATE": "MHDTC",

                # Study day patterns
                "MHSTDY": "MHSTDY", "START_DAY": "MHSTDY", "STDY": "MHSTDY",
                "MHENDY": "MHENDY", "END_DAY": "MHENDY", "ENDY": "MHENDY",

                # Ongoing/continuing
                "MHENRF": "MHENRF", "END_REF": "MHENRF", "ONGOING": "MHENRF",
                "CONTINUING": "MHENRF", "CURRENT": "MHENRF",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # SU - Substance Use Domain
            # =====================================================================
            "SU": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Substance patterns (SUTRT)
                "SUTRT": "SUTRT", "SUBSTANCE": "SUTRT", "SUBST": "SUTRT",
                "TOBACCO": "SUTRT", "ALCOHOL": "SUTRT", "CAFFEINE": "SUTRT",
                "SMOKING": "SUTRT", "DRINKING": "SUTRT",

                # Category patterns
                "SUCAT": "SUCAT", "CATEGORY": "SUCAT", "CAT": "SUCAT",
                "SUSCAT": "SUSCAT", "SUBCATEGORY": "SUSCAT", "SUBCAT": "SUSCAT",

                # Dose/amount patterns
                "SUDOSE": "SUDOSE", "DOSE": "SUDOSE", "AMOUNT": "SUDOSE",
                "SUDOSU": "SUDOSU", "DOSE_UNIT": "SUDOSU", "UNIT": "SUDOSU",
                "SUDOSFRQ": "SUDOSFRQ", "FREQUENCY": "SUDOSFRQ", "FREQ": "SUDOSFRQ",
                "PACKS_PER_DAY": "SUDOSFRQ", "DRINKS_PER_DAY": "SUDOSFRQ",

                # Status patterns
                "SUSTAT": "SUSTAT", "STATUS": "SUSTAT", "STAT": "SUSTAT",
                "CURRENT_USER": "SUSTAT", "CURRENTUSER": "SUSTAT",
                "FORMER_USER": "SUSTAT", "FORMERUSER": "SUSTAT",
                "NEVER_USED": "SUSTAT", "NEVERUSED": "SUSTAT",

                # Date patterns
                "SUSTDTC": "SUSTDTC", "START_DATE": "SUSTDTC", "STARTDATE": "SUSTDTC",
                "SUENDTC": "SUENDTC", "END_DATE": "SUENDTC", "ENDDATE": "SUENDTC",
                "QUIT_DATE": "SUENDTC", "QUITDATE": "SUENDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # EG - ECG Test Results Domain
            # =====================================================================
            "EG": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (EGTESTCD)
                "EGTESTCD": "EGTESTCD", "TEST_CODE": "EGTESTCD", "TESTCD": "EGTESTCD",
                "ECG_CODE": "EGTESTCD", "ECGCODE": "EGTESTCD", "PARAM": "EGTESTCD",

                # Test name patterns (EGTEST)
                "EGTEST": "EGTEST", "TEST_NAME": "EGTEST", "TEST": "EGTEST",
                "ECG_TEST": "EGTEST", "ECGTEST": "EGTEST", "PARAMETER": "EGTEST",
                "ECG_PARAMETER": "EGTEST", "ECGPARAM": "EGTEST",

                # Category patterns
                "EGCAT": "EGCAT", "CATEGORY": "EGCAT", "CAT": "EGCAT",
                "EGSCAT": "EGSCAT", "SUBCATEGORY": "EGSCAT", "SUBCAT": "EGSCAT",

                # Result patterns
                "EGORRES": "EGORRES", "RESULT": "EGORRES", "ORRES": "EGORRES",
                "ECG_RESULT": "EGORRES", "ECGRESULT": "EGORRES", "VALUE": "EGORRES",
                "EGORRESU": "EGORRESU", "UNIT": "EGORRESU", "UNITS": "EGORRESU",
                "EGSTRESC": "EGSTRESC", "STD_RESULT_C": "EGSTRESC",
                "EGSTRESN": "EGSTRESN", "STD_RESULT_N": "EGSTRESN",
                "EGSTRESU": "EGSTRESU", "STD_UNIT": "EGSTRESU",

                # Interpretation
                "EGEVAL": "EGEVAL", "EVALUATOR": "EGEVAL", "EVAL": "EGEVAL",
                "EGREASND": "EGREASND", "REASON_NOT_DONE": "EGREASND",

                # ECG specific measurements
                "HR": "EGORRES", "HEART_RATE": "EGORRES", "HEARTRATE": "EGORRES",
                "QT": "EGORRES", "QTC": "EGORRES", "QTCF": "EGORRES", "QTCB": "EGORRES",
                "PR": "EGORRES", "PR_INTERVAL": "EGORRES", "PRINTERVAL": "EGORRES",
                "QRS": "EGORRES", "QRS_DURATION": "EGORRES", "QRSDURATION": "EGORRES",
                "RR": "EGORRES", "RR_INTERVAL": "EGORRES", "RRINTERVAL": "EGORRES",

                # Date patterns
                "EGDTC": "EGDTC", "ECG_DATE": "EGDTC", "ECGDATE": "EGDTC",
                "DATE": "EGDTC", "DATETIME": "EGDTC",

                # Study day patterns
                "EGDY": "EGDY", "STUDY_DAY": "EGDY", "DAY": "EGDY",

                # Baseline flag
                "EGBLFL": "EGBLFL", "BASELINE": "EGBLFL", "BLFL": "EGBLFL",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # PE - Physical Examination Domain
            # =====================================================================
            "PE": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (PETESTCD)
                "PETESTCD": "PETESTCD", "TEST_CODE": "PETESTCD", "TESTCD": "PETESTCD",
                "EXAM_CODE": "PETESTCD", "EXAMCODE": "PETESTCD",

                # Test name patterns (PETEST)
                "PETEST": "PETEST", "TEST_NAME": "PETEST", "TEST": "PETEST",
                "EXAM": "PETEST", "EXAMINATION": "PETEST", "PE_EXAM": "PETEST",
                "PHYSICAL_EXAM": "PETEST", "PHYSICALEXAM": "PETEST",
                "BODY_SYSTEM": "PETEST", "BODYSYSTEM": "PETEST",

                # Category patterns
                "PECAT": "PECAT", "CATEGORY": "PECAT", "CAT": "PECAT",
                "PESCAT": "PESCAT", "SUBCATEGORY": "PESCAT", "SUBCAT": "PESCAT",

                # Result patterns
                "PEORRES": "PEORRES", "RESULT": "PEORRES", "ORRES": "PEORRES",
                "FINDING": "PEORRES", "PE_FINDING": "PEORRES", "PEFINDING": "PEORRES",
                "NORMAL": "PEORRES", "ABNORMAL": "PEORRES",
                "PESTRESC": "PESTRESC", "STD_RESULT": "PESTRESC",

                # Location patterns
                "PELOC": "PELOC", "LOCATION": "PELOC", "LOC": "PELOC",
                "BODY_LOCATION": "PELOC", "BODYLOC": "PELOC",
                "PELAT": "PELAT", "LATERALITY": "PELAT", "LAT": "PELAT",
                "LEFT": "PELAT", "RIGHT": "PELAT", "BILATERAL": "PELAT",
                "PEDIR": "PEDIR", "DIRECTION": "PEDIR", "DIR": "PEDIR",

                # Status patterns
                "PESTAT": "PESTAT", "STATUS": "PESTAT", "STAT": "PESTAT",
                "PEREASND": "PEREASND", "REASON_NOT_DONE": "PEREASND",

                # Date patterns
                "PEDTC": "PEDTC", "PE_DATE": "PEDTC", "PEDATE": "PEDTC",
                "EXAM_DATE": "PEDTC", "EXAMDATE": "PEDTC", "DATE": "PEDTC",

                # Study day patterns
                "PEDY": "PEDY", "STUDY_DAY": "PEDY", "DAY": "PEDY",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # QS - Questionnaires Domain
            # =====================================================================
            "QS": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (QSTESTCD)
                "QSTESTCD": "QSTESTCD", "TEST_CODE": "QSTESTCD", "TESTCD": "QSTESTCD",
                "QUESTION_CODE": "QSTESTCD", "QUESTIONCD": "QSTESTCD",
                "ITEM_CODE": "QSTESTCD", "ITEMCD": "QSTESTCD",

                # Test name patterns (QSTEST)
                "QSTEST": "QSTEST", "TEST_NAME": "QSTEST", "TEST": "QSTEST",
                "QUESTION": "QSTEST", "ITEM": "QSTEST", "QUESTIONNAIRE_ITEM": "QSTEST",

                # Category patterns (questionnaire name)
                "QSCAT": "QSCAT", "CATEGORY": "QSCAT", "CAT": "QSCAT",
                "QUESTIONNAIRE": "QSCAT", "FORM": "QSCAT", "SCALE": "QSCAT",
                "SURVEY": "QSCAT", "INSTRUMENT": "QSCAT",
                "QSSCAT": "QSSCAT", "SUBCATEGORY": "QSSCAT", "SUBCAT": "QSSCAT",
                "SUBSCALE": "QSSCAT", "DOMAIN": "QSSCAT",

                # Result patterns
                "QSORRES": "QSORRES", "RESULT": "QSORRES", "ORRES": "QSORRES",
                "RESPONSE": "QSORRES", "ANSWER": "QSORRES", "VALUE": "QSORRES",
                "SCORE": "QSORRES", "QSSCORE": "QSORRES",
                "QSSTRESC": "QSSTRESC", "STD_RESULT_C": "QSSTRESC",
                "QSSTRESN": "QSSTRESN", "STD_RESULT_N": "QSSTRESN", "NUMERIC_SCORE": "QSSTRESN",

                # Evaluator
                "QSEVAL": "QSEVAL", "EVALUATOR": "QSEVAL", "EVAL": "QSEVAL",
                "RATER": "QSEVAL", "ASSESSOR": "QSEVAL",

                # Status patterns
                "QSSTAT": "QSSTAT", "STATUS": "QSSTAT", "STAT": "QSSTAT",
                "QSREASND": "QSREASND", "REASON_NOT_DONE": "QSREASND",

                # Date patterns
                "QSDTC": "QSDTC", "QS_DATE": "QSDTC", "QSDATE": "QSDTC",
                "ASSESSMENT_DATE": "QSDTC", "ASSESSDATE": "QSDTC", "DATE": "QSDTC",

                # Study day patterns
                "QSDY": "QSDY", "STUDY_DAY": "QSDY", "DAY": "QSDY",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # IE - Inclusion/Exclusion Criteria Domain
            # =====================================================================
            "IE": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (IETESTCD)
                "IETESTCD": "IETESTCD", "TEST_CODE": "IETESTCD", "TESTCD": "IETESTCD",
                "CRITERIA_CODE": "IETESTCD", "CRITERIACD": "IETESTCD",
                "IE_CODE": "IETESTCD", "IECODE": "IETESTCD",

                # Test name patterns (IETEST)
                "IETEST": "IETEST", "TEST_NAME": "IETEST", "TEST": "IETEST",
                "CRITERIA": "IETEST", "CRITERION": "IETEST",
                "IE_CRITERIA": "IETEST", "IECRITERIA": "IETEST",

                # Category patterns
                "IECAT": "IECAT", "CATEGORY": "IECAT", "CAT": "IECAT",
                "INCLUSION": "IECAT", "EXCLUSION": "IECAT",
                "IESCAT": "IESCAT", "SUBCATEGORY": "IESCAT", "SUBCAT": "IESCAT",

                # Result patterns
                "IEORRES": "IEORRES", "RESULT": "IEORRES", "ORRES": "IEORRES",
                "MET": "IEORRES", "NOT_MET": "IEORRES", "YES": "IEORRES", "NO": "IEORRES",
                "IESTRESC": "IESTRESC", "STD_RESULT": "IESTRESC",

                # Status patterns
                "IESTAT": "IESTAT", "STATUS": "IESTAT", "STAT": "IESTAT",
                "IEREASND": "IEREASND", "REASON_NOT_DONE": "IEREASND",

                # Date patterns
                "IEDTC": "IEDTC", "IE_DATE": "IEDTC", "IEDATE": "IEDTC",
                "ASSESSMENT_DATE": "IEDTC", "DATE": "IEDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # PC - Pharmacokinetics Concentrations Domain
            # =====================================================================
            "PC": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (PCTESTCD)
                "PCTESTCD": "PCTESTCD", "TEST_CODE": "PCTESTCD", "TESTCD": "PCTESTCD",
                "ANALYTE_CODE": "PCTESTCD", "ANALYTECD": "PCTESTCD",

                # Test name patterns (PCTEST)
                "PCTEST": "PCTEST", "TEST_NAME": "PCTEST", "TEST": "PCTEST",
                "ANALYTE": "PCTEST", "COMPOUND": "PCTEST", "DRUG": "PCTEST",

                # Category patterns
                "PCCAT": "PCCAT", "CATEGORY": "PCCAT", "CAT": "PCCAT",
                "PCSCAT": "PCSCAT", "SUBCATEGORY": "PCSCAT", "SUBCAT": "PCSCAT",

                # Result patterns
                "PCORRES": "PCORRES", "RESULT": "PCORRES", "ORRES": "PCORRES",
                "CONCENTRATION": "PCORRES", "CONC": "PCORRES", "VALUE": "PCORRES",
                "PCORRESU": "PCORRESU", "UNIT": "PCORRESU", "UNITS": "PCORRESU",
                "PCSTRESC": "PCSTRESC", "STD_RESULT_C": "PCSTRESC",
                "PCSTRESN": "PCSTRESN", "STD_RESULT_N": "PCSTRESN",
                "PCSTRESU": "PCSTRESU", "STD_UNIT": "PCSTRESU",

                # Specimen patterns
                "PCSPEC": "PCSPEC", "SPECIMEN": "PCSPEC", "SPEC": "PCSPEC",
                "MATRIX": "PCSPEC", "SAMPLE_TYPE": "PCSPEC",

                # Method patterns
                "PCMETHOD": "PCMETHOD", "METHOD": "PCMETHOD", "ANALYSIS_METHOD": "PCMETHOD",

                # Status patterns
                "PCSTAT": "PCSTAT", "STATUS": "PCSTAT", "STAT": "PCSTAT",
                "PCREASND": "PCREASND", "REASON_NOT_DONE": "PCREASND",
                "BLQ": "PCSTAT", "BELOW_LOQ": "PCSTAT",

                # Date patterns
                "PCDTC": "PCDTC", "PC_DATE": "PCDTC", "PCDATE": "PCDTC",
                "SAMPLE_DATE": "PCDTC", "SAMPLEDATE": "PCDTC", "DATE": "PCDTC",

                # Timepoint patterns
                "PCTPT": "PCTPT", "TIMEPOINT": "PCTPT", "TPT": "PCTPT",
                "NOMINAL_TIME": "PCTPT", "NOMINALTIME": "PCTPT",
                "PCTPTNUM": "PCTPTNUM", "TIMEPOINT_NUM": "PCTPTNUM",
                "PCELTM": "PCELTM", "ELAPSED_TIME": "PCELTM", "ELAPSEDTIME": "PCELTM",

                # Study day patterns
                "PCDY": "PCDY", "STUDY_DAY": "PCDY", "DAY": "PCDY",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # PR - Procedures Domain
            # =====================================================================
            "PR": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Term patterns (PRTRT)
                "PRTRT": "PRTRT", "PROCEDURE": "PRTRT", "PROC": "PRTRT",
                "SURGERY": "PRTRT", "OPERATION": "PRTRT", "INTERVENTION": "PRTRT",

                # Decoded term (PRDECOD)
                "PRDECOD": "PRDECOD", "DECOD": "PRDECOD", "DECODED": "PRDECOD",

                # Category patterns
                "PRCAT": "PRCAT", "CATEGORY": "PRCAT", "CAT": "PRCAT",
                "PRSCAT": "PRSCAT", "SUBCATEGORY": "PRSCAT", "SUBCAT": "PRSCAT",

                # Indication
                "PRINDC": "PRINDC", "INDICATION": "PRINDC", "REASON": "PRINDC",

                # Location patterns
                "PRLOC": "PRLOC", "LOCATION": "PRLOC", "LOC": "PRLOC",
                "BODY_LOCATION": "PRLOC", "SITE": "PRLOC",
                "PRLAT": "PRLAT", "LATERALITY": "PRLAT", "LAT": "PRLAT",

                # Status patterns
                "PRSTAT": "PRSTAT", "STATUS": "PRSTAT", "STAT": "PRSTAT",
                "PRREASND": "PRREASND", "REASON_NOT_DONE": "PRREASND",

                # Date patterns
                "PRSTDTC": "PRSTDTC", "START_DATE": "PRSTDTC", "STARTDATE": "PRSTDTC",
                "PROCEDURE_DATE": "PRSTDTC", "PROCDATE": "PRSTDTC",
                "PRENDTC": "PRENDTC", "END_DATE": "PRENDTC", "ENDDATE": "PRENDTC",

                # Study day patterns
                "PRSTDY": "PRSTDY", "START_DAY": "PRSTDY", "STDY": "PRSTDY",
                "PRENDY": "PRENDY", "END_DAY": "PRENDY", "ENDY": "PRENDY",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # FA - Findings About Domain
            # =====================================================================
            "FA": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (FATESTCD)
                "FATESTCD": "FATESTCD", "TEST_CODE": "FATESTCD", "TESTCD": "FATESTCD",

                # Test name patterns (FATEST)
                "FATEST": "FATEST", "TEST_NAME": "FATEST", "TEST": "FATEST",
                "FINDING": "FATEST", "ASSESSMENT": "FATEST",

                # Object patterns (what the finding is about)
                "FAOBJ": "FAOBJ", "OBJECT": "FAOBJ", "OBJ": "FAOBJ",

                # Category patterns
                "FACAT": "FACAT", "CATEGORY": "FACAT", "CAT": "FACAT",
                "FASCAT": "FASCAT", "SUBCATEGORY": "FASCAT", "SUBCAT": "FASCAT",

                # Result patterns
                "FAORRES": "FAORRES", "RESULT": "FAORRES", "ORRES": "FAORRES",
                "VALUE": "FAORRES", "FINDING_RESULT": "FAORRES",
                "FASTRESC": "FASTRESC", "STD_RESULT_C": "FASTRESC",
                "FASTRESN": "FASTRESN", "STD_RESULT_N": "FASTRESN",

                # Status patterns
                "FASTAT": "FASTAT", "STATUS": "FASTAT", "STAT": "FASTAT",
                "FAREASND": "FAREASND", "REASON_NOT_DONE": "FAREASND",

                # Date patterns
                "FADTC": "FADTC", "FA_DATE": "FADTC", "FADATE": "FADTC", "DATE": "FADTC",

                # Study day patterns
                "FADY": "FADY", "STUDY_DAY": "FADY", "DAY": "FADY",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # CO - Comments Domain
            # =====================================================================
            "CO": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Comment patterns (COVAL)
                "COVAL": "COVAL", "COMMENT": "COVAL", "COMMENTS": "COVAL",
                "NOTE": "COVAL", "NOTES": "COVAL", "REMARK": "COVAL",
                "REMARKS": "COVAL", "TEXT": "COVAL", "DESCRIPTION": "COVAL",

                # Reference patterns
                "COREF": "COREF", "REFERENCE": "COREF", "REF": "COREF",
                "REFERS_TO": "COREF", "REFERTO": "COREF",

                # Date patterns
                "CODTC": "CODTC", "CO_DATE": "CODTC", "CODATE": "CODTC",
                "COMMENT_DATE": "CODTC", "DATE": "CODTC",

                # Study day patterns
                "CODY": "CODY", "STUDY_DAY": "CODY", "DAY": "CODY",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # SV - Subject Visits Domain
            # =====================================================================
            "SV": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Visit patterns
                "VISITNUM": "VISITNUM", "VISIT_NUMBER": "VISITNUM", "VISITNO": "VISITNUM",
                "VISIT": "VISIT", "VISIT_NAME": "VISIT", "VISITNAME": "VISIT",

                # Date patterns
                "SVSTDTC": "SVSTDTC", "START_DATE": "SVSTDTC", "STARTDATE": "SVSTDTC",
                "VISIT_START": "SVSTDTC", "VISITSTART": "SVSTDTC",
                "SVENDTC": "SVENDTC", "END_DATE": "SVENDTC", "ENDDATE": "SVENDTC",
                "VISIT_END": "SVENDTC", "VISITEND": "SVENDTC",

                # Study day patterns
                "SVSTDY": "SVSTDY", "START_DAY": "SVSTDY", "STDY": "SVSTDY",
                "SVENDY": "SVENDY", "END_DAY": "SVENDY", "ENDY": "SVENDY",

                # Upversioned visit
                "SVUPDES": "SVUPDES", "UNPLANNED_DESC": "SVUPDES",

                # Epoch
                "EPOCH": "EPOCH", "STUDY_EPOCH": "EPOCH",
            },
            # =====================================================================
            # SE - Subject Elements Domain
            # =====================================================================
            "SE": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Element patterns
                "ETCD": "ETCD", "ELEMENT_CODE": "ETCD", "ELEMENTCD": "ETCD",
                "ELEMENT": "ELEMENT", "STUDY_ELEMENT": "ELEMENT",
                "TAESSION": "TAESSION", "ELEMENT_SESSION": "TAESSION",

                # Date patterns
                "SESTDTC": "SESTDTC", "START_DATE": "SESTDTC", "STARTDATE": "SESTDTC",
                "ELEMENT_START": "SESTDTC", "ELEMENTSTART": "SESTDTC",
                "SEENDTC": "SEENDTC", "END_DATE": "SEENDTC", "ENDDATE": "SEENDTC",
                "ELEMENT_END": "SEENDTC", "ELEMENTEND": "SEENDTC",

                # Study day patterns
                "SESTDY": "SESTDY", "START_DAY": "SESTDY", "STDY": "SESTDY",
                "SEENDY": "SEENDY", "END_DAY": "SEENDY", "ENDY": "SEENDY",

                # Epoch
                "EPOCH": "EPOCH", "STUDY_EPOCH": "EPOCH",
            },
            # =====================================================================
            # DV - Protocol Deviations Domain
            # =====================================================================
            "DV": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Term patterns (DVTERM)
                "DVTERM": "DVTERM", "DEVIATION": "DVTERM", "DEV": "DVTERM",
                "PROTOCOL_DEVIATION": "DVTERM", "PROTOCOLDEV": "DVTERM",
                "VIOLATION": "DVTERM",

                # Decoded term (DVDECOD)
                "DVDECOD": "DVDECOD", "DECOD": "DVDECOD", "DECODED": "DVDECOD",

                # Category patterns
                "DVCAT": "DVCAT", "CATEGORY": "DVCAT", "CAT": "DVCAT",
                "DEVIATION_CATEGORY": "DVCAT", "DEVIATIONCAT": "DVCAT",
                "DVSCAT": "DVSCAT", "SUBCATEGORY": "DVSCAT", "SUBCAT": "DVSCAT",

                # Date patterns
                "DVSTDTC": "DVSTDTC", "START_DATE": "DVSTDTC", "STARTDATE": "DVSTDTC",
                "DEVIATION_DATE": "DVSTDTC", "DEVIATIONDATE": "DVSTDTC",
                "DVENDTC": "DVENDTC", "END_DATE": "DVENDTC", "ENDDATE": "DVENDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # RS - Disease Response Domain (Oncology)
            # =====================================================================
            "RS": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (RSTESTCD)
                "RSTESTCD": "RSTESTCD", "TEST_CODE": "RSTESTCD", "TESTCD": "RSTESTCD",
                "RESPONSE_CODE": "RSTESTCD", "RESPONSECD": "RSTESTCD",

                # Test name patterns (RSTEST)
                "RSTEST": "RSTEST", "TEST_NAME": "RSTEST", "TEST": "RSTEST",
                "RESPONSE": "RSTEST", "TUMOR_RESPONSE": "RSTEST",

                # Category patterns
                "RSCAT": "RSCAT", "CATEGORY": "RSCAT", "CAT": "RSCAT",
                "RSSCAT": "RSSCAT", "SUBCATEGORY": "RSSCAT", "SUBCAT": "RSSCAT",

                # Result patterns
                "RSORRES": "RSORRES", "RESULT": "RSORRES", "ORRES": "RSORRES",
                "CR": "RSORRES", "PR": "RSORRES", "SD": "RSORRES", "PD": "RSORRES",
                "COMPLETE_RESPONSE": "RSORRES", "PARTIAL_RESPONSE": "RSORRES",
                "STABLE_DISEASE": "RSORRES", "PROGRESSIVE_DISEASE": "RSORRES",
                "RSSTRESC": "RSSTRESC", "STD_RESULT": "RSSTRESC",

                # Evaluator
                "RSEVAL": "RSEVAL", "EVALUATOR": "RSEVAL", "EVAL": "RSEVAL",

                # Date patterns
                "RSDTC": "RSDTC", "RS_DATE": "RSDTC", "RSDATE": "RSDTC",
                "RESPONSE_DATE": "RSDTC", "DATE": "RSDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # TR - Tumor Results Domain (Oncology)
            # =====================================================================
            "TR": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (TRTESTCD)
                "TRTESTCD": "TRTESTCD", "TEST_CODE": "TRTESTCD", "TESTCD": "TRTESTCD",
                "TUMOR_CODE": "TRTESTCD", "TUMORCD": "TRTESTCD",

                # Test name patterns (TRTEST)
                "TRTEST": "TRTEST", "TEST_NAME": "TRTEST", "TEST": "TRTEST",
                "TUMOR_MEASUREMENT": "TRTEST", "MEASUREMENT": "TRTEST",
                "DIAMETER": "TRTEST", "SIZE": "TRTEST",

                # Result patterns
                "TRORRES": "TRORRES", "RESULT": "TRORRES", "ORRES": "TRORRES",
                "TUMOR_SIZE": "TRORRES", "TUMORSIZE": "TRORRES", "VALUE": "TRORRES",
                "TRORRESU": "TRORRESU", "UNIT": "TRORRESU", "UNITS": "TRORRESU",
                "TRSTRESC": "TRSTRESC", "STD_RESULT_C": "TRSTRESC",
                "TRSTRESN": "TRSTRESN", "STD_RESULT_N": "TRSTRESN",

                # Link to tumor identification
                "TRLNKID": "TRLNKID", "LINK_ID": "TRLNKID", "LINKID": "TRLNKID",
                "TUMOR_ID": "TRLNKID", "TUMORID": "TRLNKID",

                # Location patterns
                "TRLOC": "TRLOC", "LOCATION": "TRLOC", "LOC": "TRLOC",
                "TUMOR_LOCATION": "TRLOC", "TUMORLOC": "TRLOC",
                "TRLAT": "TRLAT", "LATERALITY": "TRLAT", "LAT": "TRLAT",

                # Method
                "TRMETHOD": "TRMETHOD", "METHOD": "TRMETHOD", "IMAGING_METHOD": "TRMETHOD",

                # Evaluator
                "TREVAL": "TREVAL", "EVALUATOR": "TREVAL", "EVAL": "TREVAL",

                # Date patterns
                "TRDTC": "TRDTC", "TR_DATE": "TRDTC", "TRDATE": "TRDTC",
                "SCAN_DATE": "TRDTC", "SCANDATE": "TRDTC", "DATE": "TRDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # TU - Tumor Identification Domain (Oncology)
            # =====================================================================
            "TU": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (TUTESTCD)
                "TUTESTCD": "TUTESTCD", "TEST_CODE": "TUTESTCD", "TESTCD": "TUTESTCD",
                "TUMOR_CODE": "TUTESTCD",

                # Test name patterns (TUTEST)
                "TUTEST": "TUTEST", "TEST_NAME": "TUTEST", "TEST": "TUTEST",
                "TUMOR_IDENTIFICATION": "TUTEST", "TUMORID": "TUTEST",

                # Result patterns
                "TUORRES": "TUORRES", "RESULT": "TUORRES", "ORRES": "TUORRES",
                "TUMOR_TYPE": "TUORRES", "TUMORTYPE": "TUORRES",

                # Link ID
                "TULNKID": "TULNKID", "LINK_ID": "TULNKID", "LINKID": "TULNKID",

                # Location patterns
                "TULOC": "TULOC", "LOCATION": "TULOC", "LOC": "TULOC",
                "TUMOR_LOCATION": "TULOC", "TUMORLOC": "TULOC",
                "TULAT": "TULAT", "LATERALITY": "TULAT", "LAT": "TULAT",

                # Method
                "TUMETHOD": "TUMETHOD", "METHOD": "TUMETHOD",

                # Evaluator
                "TUEVAL": "TUEVAL", "EVALUATOR": "TUEVAL", "EVAL": "TUEVAL",

                # Date patterns
                "TUDTC": "TUDTC", "TU_DATE": "TUDTC", "TUDATE": "TUDTC", "DATE": "TUDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # SC - Subject Characteristics Domain
            # =====================================================================
            "SC": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (SCTESTCD)
                "SCTESTCD": "SCTESTCD", "TEST_CODE": "SCTESTCD", "TESTCD": "SCTESTCD",
                "CHARACTERISTIC_CODE": "SCTESTCD", "CHARCD": "SCTESTCD",

                # Test name patterns (SCTEST)
                "SCTEST": "SCTEST", "TEST_NAME": "SCTEST", "TEST": "SCTEST",
                "CHARACTERISTIC": "SCTEST", "CHAR": "SCTEST",

                # Category patterns
                "SCCAT": "SCCAT", "CATEGORY": "SCCAT", "CAT": "SCCAT",
                "SCSCAT": "SCSCAT", "SUBCATEGORY": "SCSCAT", "SUBCAT": "SCSCAT",

                # Result patterns
                "SCORRES": "SCORRES", "RESULT": "SCORRES", "ORRES": "SCORRES",
                "VALUE": "SCORRES", "CHARACTERISTIC_VALUE": "SCORRES",
                "SCSTRESC": "SCSTRESC", "STD_RESULT_C": "SCSTRESC",
                "SCSTRESN": "SCSTRESN", "STD_RESULT_N": "SCSTRESN",

                # Date patterns
                "SCDTC": "SCDTC", "SC_DATE": "SCDTC", "SCDATE": "SCDTC", "DATE": "SCDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # DA - Drug Accountability Domain
            # =====================================================================
            "DA": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (DATESTCD)
                "DATESTCD": "DATESTCD", "TEST_CODE": "DATESTCD", "TESTCD": "DATESTCD",

                # Test name patterns (DATEST)
                "DATEST": "DATEST", "TEST_NAME": "DATEST", "TEST": "DATEST",
                "ACCOUNTABILITY": "DATEST", "DISPENSED": "DATEST", "RETURNED": "DATEST",

                # Category patterns
                "DACAT": "DACAT", "CATEGORY": "DACAT", "CAT": "DACAT",
                "DASCAT": "DASCAT", "SUBCATEGORY": "DASCAT", "SUBCAT": "DASCAT",

                # Result patterns
                "DAORRES": "DAORRES", "RESULT": "DAORRES", "ORRES": "DAORRES",
                "QUANTITY": "DAORRES", "COUNT": "DAORRES", "AMOUNT": "DAORRES",
                "DAORRESU": "DAORRESU", "UNIT": "DAORRESU", "UNITS": "DAORRESU",

                # Lot number
                "DALOT": "DALOT", "LOT": "DALOT", "LOT_NUMBER": "DALOT", "BATCH": "DALOT",

                # Date patterns
                "DADTC": "DADTC", "DA_DATE": "DADTC", "DADATE": "DADTC",
                "DISPENSE_DATE": "DADTC", "DATE": "DADTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # MB - Microbiology Specimen Domain
            # =====================================================================
            "MB": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (MBTESTCD)
                "MBTESTCD": "MBTESTCD", "TEST_CODE": "MBTESTCD", "TESTCD": "MBTESTCD",
                "ORGANISM_CODE": "MBTESTCD", "ORGANISMCD": "MBTESTCD",

                # Test name patterns (MBTEST)
                "MBTEST": "MBTEST", "TEST_NAME": "MBTEST", "TEST": "MBTEST",
                "ORGANISM": "MBTEST", "MICROORGANISM": "MBTEST", "BACTERIA": "MBTEST",
                "PATHOGEN": "MBTEST", "CULTURE": "MBTEST",

                # Category patterns
                "MBCAT": "MBCAT", "CATEGORY": "MBCAT", "CAT": "MBCAT",
                "MBSCAT": "MBSCAT", "SUBCATEGORY": "MBSCAT", "SUBCAT": "MBSCAT",

                # Result patterns
                "MBORRES": "MBORRES", "RESULT": "MBORRES", "ORRES": "MBORRES",
                "CULTURE_RESULT": "MBORRES", "CULTURERESULT": "MBORRES",
                "POSITIVE": "MBORRES", "NEGATIVE": "MBORRES",
                "MBSTRESC": "MBSTRESC", "STD_RESULT": "MBSTRESC",

                # Specimen patterns
                "MBSPEC": "MBSPEC", "SPECIMEN": "MBSPEC", "SPEC": "MBSPEC",
                "SAMPLE_TYPE": "MBSPEC", "SAMPLETYPE": "MBSPEC",

                # Method patterns
                "MBMETHOD": "MBMETHOD", "METHOD": "MBMETHOD", "CULTURE_METHOD": "MBMETHOD",

                # Date patterns
                "MBDTC": "MBDTC", "MB_DATE": "MBDTC", "MBDATE": "MBDTC",
                "COLLECTION_DATE": "MBDTC", "DATE": "MBDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # MS - Microbiology Susceptibility Domain
            # =====================================================================
            "MS": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (MSTESTCD)
                "MSTESTCD": "MSTESTCD", "TEST_CODE": "MSTESTCD", "TESTCD": "MSTESTCD",
                "ANTIBIOTIC_CODE": "MSTESTCD", "ANTIBIOTICCD": "MSTESTCD",

                # Test name patterns (MSTEST)
                "MSTEST": "MSTEST", "TEST_NAME": "MSTEST", "TEST": "MSTEST",
                "ANTIBIOTIC": "MSTEST", "ANTIMICROBIAL": "MSTEST",

                # Result patterns
                "MSORRES": "MSORRES", "RESULT": "MSORRES", "ORRES": "MSORRES",
                "SUSCEPTIBILITY": "MSORRES", "SENSITIVE": "MSORRES",
                "RESISTANT": "MSORRES", "INTERMEDIATE": "MSORRES",
                "MIC": "MSORRES", "MIC_VALUE": "MSORRES",
                "MSORRESU": "MSORRESU", "UNIT": "MSORRESU", "UNITS": "MSORRESU",
                "MSSTRESC": "MSSTRESC", "STD_RESULT": "MSSTRESC",

                # Link to MB
                "MSLNKID": "MSLNKID", "LINK_ID": "MSLNKID", "LINKID": "MSLNKID",

                # Date patterns
                "MSDTC": "MSDTC", "MS_DATE": "MSDTC", "MSDATE": "MSDTC", "DATE": "MSDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # MI - Microscopic Findings Domain
            # =====================================================================
            "MI": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (MITESTCD)
                "MITESTCD": "MITESTCD", "TEST_CODE": "MITESTCD", "TESTCD": "MITESTCD",

                # Test name patterns (MITEST)
                "MITEST": "MITEST", "TEST_NAME": "MITEST", "TEST": "MITEST",
                "MICROSCOPIC": "MITEST", "HISTOLOGY": "MITEST", "PATHOLOGY": "MITEST",

                # Result patterns
                "MIORRES": "MIORRES", "RESULT": "MIORRES", "ORRES": "MIORRES",
                "FINDING": "MIORRES", "MICROSCOPIC_FINDING": "MIORRES",
                "MISTRESC": "MISTRESC", "STD_RESULT": "MISTRESC",

                # Specimen patterns
                "MISPEC": "MISPEC", "SPECIMEN": "MISPEC", "SPEC": "MISPEC",
                "TISSUE": "MISPEC", "BIOPSY": "MISPEC",

                # Location patterns
                "MILOC": "MILOC", "LOCATION": "MILOC", "LOC": "MILOC",
                "MILAT": "MILAT", "LATERALITY": "MILAT", "LAT": "MILAT",

                # Date patterns
                "MIDTC": "MIDTC", "MI_DATE": "MIDTC", "MIDATE": "MIDTC", "DATE": "MIDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # PP - Pharmacokinetic Parameters Domain
            # =====================================================================
            "PP": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (PPTESTCD)
                "PPTESTCD": "PPTESTCD", "TEST_CODE": "PPTESTCD", "TESTCD": "PPTESTCD",
                "PARAM_CODE": "PPTESTCD", "PARAMCD": "PPTESTCD",

                # Test name patterns (PPTEST)
                "PPTEST": "PPTEST", "TEST_NAME": "PPTEST", "TEST": "PPTEST",
                "PARAMETER": "PPTEST", "PK_PARAMETER": "PPTEST",
                "CMAX": "PPTEST", "TMAX": "PPTEST", "AUC": "PPTEST",
                "AUCLAST": "PPTEST", "AUCINF": "PPTEST", "HALF_LIFE": "PPTEST",
                "CL": "PPTEST", "CLEARANCE": "PPTEST", "VD": "PPTEST",

                # Category patterns
                "PPCAT": "PPCAT", "CATEGORY": "PPCAT", "CAT": "PPCAT",
                "PPSCAT": "PPSCAT", "SUBCATEGORY": "PPSCAT", "SUBCAT": "PPSCAT",

                # Result patterns
                "PPORRES": "PPORRES", "RESULT": "PPORRES", "ORRES": "PPORRES",
                "VALUE": "PPORRES", "PK_VALUE": "PPORRES",
                "PPORRESU": "PPORRESU", "UNIT": "PPORRESU", "UNITS": "PPORRESU",
                "PPSTRESC": "PPSTRESC", "STD_RESULT_C": "PPSTRESC",
                "PPSTRESN": "PPSTRESN", "STD_RESULT_N": "PPSTRESN",
                "PPSTRESU": "PPSTRESU", "STD_UNIT": "PPSTRESU",

                # Date patterns
                "PPDTC": "PPDTC", "PP_DATE": "PPDTC", "PPDATE": "PPDTC", "DATE": "PPDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # CE - Clinical Events Domain
            # =====================================================================
            "CE": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Term patterns (CETERM)
                "CETERM": "CETERM", "CLINICAL_EVENT": "CETERM", "EVENT": "CETERM",
                "EVENT_TERM": "CETERM", "EVENTTERM": "CETERM",

                # Decoded term (CEDECOD)
                "CEDECOD": "CEDECOD", "DECOD": "CEDECOD", "DECODED": "CEDECOD",

                # Category patterns
                "CECAT": "CECAT", "CATEGORY": "CECAT", "CAT": "CECAT",
                "CESCAT": "CESCAT", "SUBCATEGORY": "CESCAT", "SUBCAT": "CESCAT",

                # Pre-specified and occurrence
                "CEPRESP": "CEPRESP", "PRESPECIFIED": "CEPRESP", "PRESP": "CEPRESP",
                "CEOCCUR": "CEOCCUR", "OCCURRED": "CEOCCUR", "OCCUR": "CEOCCUR",

                # Date patterns
                "CESTDTC": "CESTDTC", "START_DATE": "CESTDTC", "STARTDATE": "CESTDTC",
                "CEENDTC": "CEENDTC", "END_DATE": "CEENDTC", "ENDDATE": "CEENDTC",
                "CEDTC": "CEDTC", "CE_DATE": "CEDTC", "CEDATE": "CEDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # HO - Healthcare Encounters Domain
            # =====================================================================
            "HO": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Term patterns (HOTERM)
                "HOTERM": "HOTERM", "ENCOUNTER": "HOTERM", "HEALTHCARE": "HOTERM",
                "VISIT_TYPE": "HOTERM", "VISITTYPE": "HOTERM",
                "HOSPITALIZATION": "HOTERM", "HOSP": "HOTERM",
                "ER_VISIT": "HOTERM", "ERVISIT": "HOTERM",

                # Decoded term (HODECOD)
                "HODECOD": "HODECOD", "DECOD": "HODECOD", "DECODED": "HODECOD",

                # Category patterns
                "HOCAT": "HOCAT", "CATEGORY": "HOCAT", "CAT": "HOCAT",
                "HOSCAT": "HOSCAT", "SUBCATEGORY": "HOSCAT", "SUBCAT": "HOSCAT",

                # Pre-specified and occurrence
                "HOPRESP": "HOPRESP", "PRESPECIFIED": "HOPRESP", "PRESP": "HOPRESP",
                "HOOCCUR": "HOOCCUR", "OCCURRED": "HOOCCUR", "OCCUR": "HOOCCUR",

                # Date patterns
                "HOSTDTC": "HOSTDTC", "START_DATE": "HOSTDTC", "STARTDATE": "HOSTDTC",
                "ADMIT_DATE": "HOSTDTC", "ADMITDATE": "HOSTDTC",
                "HOENDTC": "HOENDTC", "END_DATE": "HOENDTC", "ENDDATE": "HOENDTC",
                "DISCHARGE_DATE": "HOENDTC", "DISCHARGEDATE": "HOENDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # AG - Procedure Agents Domain
            # =====================================================================
            "AG": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Treatment patterns (AGTRT)
                "AGTRT": "AGTRT", "AGENT": "AGTRT", "PROC_AGENT": "AGTRT",
                "PROCEDURE_AGENT": "AGTRT", "CONTRAST": "AGTRT",
                "ANESTHETIC": "AGTRT", "SEDATIVE": "AGTRT",

                # Category patterns
                "AGCAT": "AGCAT", "CATEGORY": "AGCAT", "CAT": "AGCAT",
                "AGSCAT": "AGSCAT", "SUBCATEGORY": "AGSCAT", "SUBCAT": "AGSCAT",

                # Dose patterns
                "AGDOSE": "AGDOSE", "DOSE": "AGDOSE", "AMOUNT": "AGDOSE",
                "AGDOSU": "AGDOSU", "DOSE_UNIT": "AGDOSU", "UNIT": "AGDOSU",

                # Route patterns
                "AGROUTE": "AGROUTE", "ROUTE": "AGROUTE", "ADMIN_ROUTE": "AGROUTE",

                # Date patterns
                "AGSTDTC": "AGSTDTC", "START_DATE": "AGSTDTC", "STARTDATE": "AGSTDTC",
                "AGENDTC": "AGENDTC", "END_DATE": "AGENDTC", "ENDDATE": "AGENDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # EC - Exposure as Collected Domain
            # =====================================================================
            "EC": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Treatment patterns (ECTRT)
                "ECTRT": "ECTRT", "TREATMENT": "ECTRT", "TRT": "ECTRT",
                "DRUG": "ECTRT", "COLLECTED_DOSE": "ECTRT",

                # Category patterns
                "ECCAT": "ECCAT", "CATEGORY": "ECCAT", "CAT": "ECCAT",
                "ECSCAT": "ECSCAT", "SUBCATEGORY": "ECSCAT", "SUBCAT": "ECSCAT",

                # Dose patterns
                "ECDOSE": "ECDOSE", "DOSE": "ECDOSE", "DOSAGE": "ECDOSE",
                "ECDOSU": "ECDOSU", "DOSE_UNIT": "ECDOSU", "UNIT": "ECDOSU",
                "ECDOSFRM": "ECDOSFRM", "DOSE_FORM": "ECDOSFRM", "FORM": "ECDOSFRM",
                "ECDOSFRQ": "ECDOSFRQ", "FREQUENCY": "ECDOSFRQ", "FREQ": "ECDOSFRQ",

                # Route patterns
                "ECROUTE": "ECROUTE", "ROUTE": "ECROUTE", "ADMIN_ROUTE": "ECROUTE",

                # Date patterns
                "ECSTDTC": "ECSTDTC", "START_DATE": "ECSTDTC", "STARTDATE": "ECSTDTC",
                "ECENDTC": "ECENDTC", "END_DATE": "ECENDTC", "ENDDATE": "ECENDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # ML - Meals Domain
            # =====================================================================
            "ML": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Treatment patterns (MLTRT)
                "MLTRT": "MLTRT", "MEAL": "MLTRT", "MEALS": "MLTRT",
                "FOOD": "MLTRT", "DIETARY": "MLTRT",

                # Category patterns
                "MLCAT": "MLCAT", "CATEGORY": "MLCAT", "CAT": "MLCAT",
                "MLSCAT": "MLSCAT", "SUBCATEGORY": "MLSCAT", "SUBCAT": "MLSCAT",

                # Date patterns
                "MLSTDTC": "MLSTDTC", "START_DATE": "MLSTDTC", "STARTDATE": "MLSTDTC",
                "MEAL_TIME": "MLSTDTC", "MEALTIME": "MLSTDTC",
                "MLENDTC": "MLENDTC", "END_DATE": "MLENDTC", "ENDDATE": "MLENDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # DD - Death Details Domain
            # =====================================================================
            "DD": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (DDTESTCD)
                "DDTESTCD": "DDTESTCD", "TEST_CODE": "DDTESTCD", "TESTCD": "DDTESTCD",

                # Test name patterns (DDTEST)
                "DDTEST": "DDTEST", "TEST_NAME": "DDTEST", "TEST": "DDTEST",
                "DEATH_DETAIL": "DDTEST", "DEATHDETAIL": "DDTEST",
                "CAUSE_OF_DEATH": "DDTEST", "CAUSEOFDEATH": "DDTEST",

                # Category patterns
                "DDCAT": "DDCAT", "CATEGORY": "DDCAT", "CAT": "DDCAT",

                # Result patterns
                "DDORRES": "DDORRES", "RESULT": "DDORRES", "ORRES": "DDORRES",
                "CAUSE": "DDORRES", "DEATH_CAUSE": "DDORRES",
                "DDSTRESC": "DDSTRESC", "STD_RESULT": "DDSTRESC",

                # Date patterns
                "DDDTC": "DDDTC", "DD_DATE": "DDDTC", "DDDATE": "DDDTC",
                "DEATH_DATE": "DDDTC", "DEATHDATE": "DDDTC", "DATE": "DDDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # SS - Subject Status Domain
            # =====================================================================
            "SS": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (SSTESTCD)
                "SSTESTCD": "SSTESTCD", "TEST_CODE": "SSTESTCD", "TESTCD": "SSTESTCD",

                # Test name patterns (SSTEST)
                "SSTEST": "SSTEST", "TEST_NAME": "SSTEST", "TEST": "SSTEST",
                "STATUS": "SSTEST", "SUBJECT_STATUS": "SSTEST",
                "SURVIVAL_STATUS": "SSTEST", "SURVIVALSTATUS": "SSTEST",

                # Category patterns
                "SSCAT": "SSCAT", "CATEGORY": "SSCAT", "CAT": "SSCAT",
                "SSSCAT": "SSSCAT", "SUBCATEGORY": "SSSCAT", "SUBCAT": "SSSCAT",

                # Result patterns
                "SSORRES": "SSORRES", "RESULT": "SSORRES", "ORRES": "SSORRES",
                "ALIVE": "SSORRES", "DEAD": "SSORRES", "LOST": "SSORRES",
                "SSSTRESC": "SSSTRESC", "STD_RESULT": "SSSTRESC",

                # Date patterns
                "SSDTC": "SSDTC", "SS_DATE": "SSDTC", "SSDATE": "SSDTC",
                "STATUS_DATE": "SSDTC", "STATUSDATE": "SSDTC", "DATE": "SSDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # FT - Functional Tests Domain
            # =====================================================================
            "FT": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (FTTESTCD)
                "FTTESTCD": "FTTESTCD", "TEST_CODE": "FTTESTCD", "TESTCD": "FTTESTCD",

                # Test name patterns (FTTEST)
                "FTTEST": "FTTEST", "TEST_NAME": "FTTEST", "TEST": "FTTEST",
                "FUNCTIONAL_TEST": "FTTEST", "FUNCTIONALTEST": "FTTEST",
                "SPIROMETRY": "FTTEST", "PULMONARY": "FTTEST",
                "FEV1": "FTTEST", "FVC": "FTTEST", "DLCO": "FTTEST",

                # Category patterns
                "FTCAT": "FTCAT", "CATEGORY": "FTCAT", "CAT": "FTCAT",
                "FTSCAT": "FTSCAT", "SUBCATEGORY": "FTSCAT", "SUBCAT": "FTSCAT",

                # Result patterns
                "FTORRES": "FTORRES", "RESULT": "FTORRES", "ORRES": "FTORRES",
                "VALUE": "FTORRES", "MEASUREMENT": "FTORRES",
                "FTORRESU": "FTORRESU", "UNIT": "FTORRESU", "UNITS": "FTORRESU",
                "FTSTRESC": "FTSTRESC", "STD_RESULT_C": "FTSTRESC",
                "FTSTRESN": "FTSTRESN", "STD_RESULT_N": "FTSTRESN",

                # Date patterns
                "FTDTC": "FTDTC", "FT_DATE": "FTDTC", "FTDATE": "FTDTC", "DATE": "FTDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # OE - Ophthalmic Examinations Domain
            # =====================================================================
            "OE": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (OETESTCD)
                "OETESTCD": "OETESTCD", "TEST_CODE": "OETESTCD", "TESTCD": "OETESTCD",

                # Test name patterns (OETEST)
                "OETEST": "OETEST", "TEST_NAME": "OETEST", "TEST": "OETEST",
                "OPHTHALMIC": "OETEST", "EYE_EXAM": "OETEST", "EYEEXAM": "OETEST",
                "VISUAL_ACUITY": "OETEST", "VISUALACUITY": "OETEST",
                "IOP": "OETEST", "INTRAOCULAR": "OETEST",

                # Category patterns
                "OECAT": "OECAT", "CATEGORY": "OECAT", "CAT": "OECAT",
                "OESCAT": "OESCAT", "SUBCATEGORY": "OESCAT", "SUBCAT": "OESCAT",

                # Result patterns
                "OEORRES": "OEORRES", "RESULT": "OEORRES", "ORRES": "OEORRES",
                "VALUE": "OEORRES", "FINDING": "OEORRES",
                "OEORRESU": "OEORRESU", "UNIT": "OEORRESU", "UNITS": "OEORRESU",
                "OESTRESC": "OESTRESC", "STD_RESULT_C": "OESTRESC",
                "OESTRESN": "OESTRESN", "STD_RESULT_N": "OESTRESN",

                # Location (laterality for eyes)
                "OELOC": "OELOC", "LOCATION": "OELOC", "LOC": "OELOC",
                "OELAT": "OELAT", "LATERALITY": "OELAT", "LAT": "OELAT",
                "LEFT_EYE": "OELAT", "RIGHT_EYE": "OELAT", "OS": "OELAT", "OD": "OELAT",

                # Date patterns
                "OEDTC": "OEDTC", "OE_DATE": "OEDTC", "OEDATE": "OEDTC", "DATE": "OEDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # NV - Nervous System Findings Domain
            # =====================================================================
            "NV": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (NVTESTCD)
                "NVTESTCD": "NVTESTCD", "TEST_CODE": "NVTESTCD", "TESTCD": "NVTESTCD",

                # Test name patterns (NVTEST)
                "NVTEST": "NVTEST", "TEST_NAME": "NVTEST", "TEST": "NVTEST",
                "NERVOUS_SYSTEM": "NVTEST", "NEUROLOGICAL": "NVTEST",
                "NEURO_EXAM": "NVTEST", "NEUROEXAM": "NVTEST",

                # Category patterns
                "NVCAT": "NVCAT", "CATEGORY": "NVCAT", "CAT": "NVCAT",
                "NVSCAT": "NVSCAT", "SUBCATEGORY": "NVSCAT", "SUBCAT": "NVSCAT",

                # Result patterns
                "NVORRES": "NVORRES", "RESULT": "NVORRES", "ORRES": "NVORRES",
                "FINDING": "NVORRES", "VALUE": "NVORRES",
                "NVSTRESC": "NVSTRESC", "STD_RESULT": "NVSTRESC",

                # Location patterns
                "NVLOC": "NVLOC", "LOCATION": "NVLOC", "LOC": "NVLOC",
                "NVLAT": "NVLAT", "LATERALITY": "NVLAT", "LAT": "NVLAT",

                # Date patterns
                "NVDTC": "NVDTC", "NV_DATE": "NVDTC", "NVDATE": "NVDTC", "DATE": "NVDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # CV - Cardiovascular System Findings Domain
            # =====================================================================
            "CV": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (CVTESTCD)
                "CVTESTCD": "CVTESTCD", "TEST_CODE": "CVTESTCD", "TESTCD": "CVTESTCD",

                # Test name patterns (CVTEST)
                "CVTEST": "CVTEST", "TEST_NAME": "CVTEST", "TEST": "CVTEST",
                "CARDIOVASCULAR": "CVTEST", "CARDIO": "CVTEST",
                "ECHO": "CVTEST", "ECHOCARDIOGRAM": "CVTEST",
                "EJECTION_FRACTION": "CVTEST", "EF": "CVTEST",

                # Category patterns
                "CVCAT": "CVCAT", "CATEGORY": "CVCAT", "CAT": "CVCAT",
                "CVSCAT": "CVSCAT", "SUBCATEGORY": "CVSCAT", "SUBCAT": "CVSCAT",

                # Result patterns
                "CVORRES": "CVORRES", "RESULT": "CVORRES", "ORRES": "CVORRES",
                "VALUE": "CVORRES", "MEASUREMENT": "CVORRES",
                "CVORRESU": "CVORRESU", "UNIT": "CVORRESU", "UNITS": "CVORRESU",
                "CVSTRESC": "CVSTRESC", "STD_RESULT_C": "CVSTRESC",
                "CVSTRESN": "CVSTRESN", "STD_RESULT_N": "CVSTRESN",

                # Method
                "CVMETHOD": "CVMETHOD", "METHOD": "CVMETHOD", "IMAGING_METHOD": "CVMETHOD",

                # Date patterns
                "CVDTC": "CVDTC", "CV_DATE": "CVDTC", "CVDATE": "CVDTC", "DATE": "CVDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # RE - Respiratory System Findings Domain
            # =====================================================================
            "RE": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (RETESTCD)
                "RETESTCD": "RETESTCD", "TEST_CODE": "RETESTCD", "TESTCD": "RETESTCD",

                # Test name patterns (RETEST)
                "RETEST": "RETEST", "TEST_NAME": "RETEST", "TEST": "RETEST",
                "RESPIRATORY": "RETEST", "PULMONARY_EXAM": "RETEST",
                "LUNG": "RETEST", "LUNGS": "RETEST",

                # Category patterns
                "RECAT": "RECAT", "CATEGORY": "RECAT", "CAT": "RECAT",
                "RESCAT": "RESCAT", "SUBCATEGORY": "RESCAT", "SUBCAT": "RESCAT",

                # Result patterns
                "REORRES": "REORRES", "RESULT": "REORRES", "ORRES": "REORRES",
                "FINDING": "REORRES", "VALUE": "REORRES",
                "RESTRAESC": "RESTRAESC", "STD_RESULT": "RESTRAESC",

                # Location patterns
                "RELOC": "RELOC", "LOCATION": "RELOC", "LOC": "RELOC",
                "RELAT": "RELAT", "LATERALITY": "RELAT", "LAT": "RELAT",

                # Date patterns
                "REDTC": "REDTC", "RE_DATE": "REDTC", "REDATE": "REDTC", "DATE": "REDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # SR - Skin Response Domain
            # =====================================================================
            "SR": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (SRTESTCD)
                "SRTESTCD": "SRTESTCD", "TEST_CODE": "SRTESTCD", "TESTCD": "SRTESTCD",

                # Test name patterns (SRTEST)
                "SRTEST": "SRTEST", "TEST_NAME": "SRTEST", "TEST": "SRTEST",
                "SKIN_RESPONSE": "SRTEST", "SKINRESPONSE": "SRTEST",
                "WHEAL": "SRTEST", "FLARE": "SRTEST", "ERYTHEMA": "SRTEST",
                "INJECTION_SITE": "SRTEST", "INJECTIONSITE": "SRTEST",

                # Category patterns
                "SRCAT": "SRCAT", "CATEGORY": "SRCAT", "CAT": "SRCAT",
                "SRSCAT": "SRSCAT", "SUBCATEGORY": "SRSCAT", "SUBCAT": "SRSCAT",

                # Result patterns
                "SRORRES": "SRORRES", "RESULT": "SRORRES", "ORRES": "SRORRES",
                "VALUE": "SRORRES", "DIAMETER": "SRORRES", "SIZE": "SRORRES",
                "SRORRESU": "SRORRESU", "UNIT": "SRORRESU", "UNITS": "SRORRESU",
                "SRSTRESC": "SRSTRESC", "STD_RESULT_C": "SRSTRESC",
                "SRSTRESN": "SRSTRESN", "STD_RESULT_N": "SRSTRESN",

                # Location patterns
                "SRLOC": "SRLOC", "LOCATION": "SRLOC", "LOC": "SRLOC",
                "SRLAT": "SRLAT", "LATERALITY": "SRLAT", "LAT": "SRLAT",

                # Date patterns
                "SRDTC": "SRDTC", "SR_DATE": "SRDTC", "SRDATE": "SRDTC", "DATE": "SRDTC",

                # Timepoint patterns
                "SRTPT": "SRTPT", "TIMEPOINT": "SRTPT", "TPT": "SRTPT",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # UR - Urinary System Findings Domain
            # =====================================================================
            "UR": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (URTESTCD)
                "URTESTCD": "URTESTCD", "TEST_CODE": "URTESTCD", "TESTCD": "URTESTCD",

                # Test name patterns (URTEST)
                "URTEST": "URTEST", "TEST_NAME": "URTEST", "TEST": "URTEST",
                "URINARY": "URTEST", "RENAL": "URTEST", "KIDNEY": "URTEST",
                "URINALYSIS": "URTEST", "URINE": "URTEST",

                # Category patterns
                "URCAT": "URCAT", "CATEGORY": "URCAT", "CAT": "URCAT",
                "URSCAT": "URSCAT", "SUBCATEGORY": "URSCAT", "SUBCAT": "URSCAT",

                # Result patterns
                "URORRES": "URORRES", "RESULT": "URORRES", "ORRES": "URORRES",
                "VALUE": "URORRES", "FINDING": "URORRES",
                "URORRESU": "URORRESU", "UNIT": "URORRESU", "UNITS": "URORRESU",
                "URSTRESC": "URSTRESC", "STD_RESULT_C": "URSTRESC",
                "URSTRESN": "URSTRESN", "STD_RESULT_N": "URSTRESN",

                # Date patterns
                "URDTC": "URDTC", "UR_DATE": "URDTC", "URDATE": "URDTC", "DATE": "URDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # GF - Genomics Findings Domain
            # =====================================================================
            "GF": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (GFTESTCD)
                "GFTESTCD": "GFTESTCD", "TEST_CODE": "GFTESTCD", "TESTCD": "GFTESTCD",
                "GENE_CODE": "GFTESTCD", "GENECODE": "GFTESTCD",

                # Test name patterns (GFTEST)
                "GFTEST": "GFTEST", "TEST_NAME": "GFTEST", "TEST": "GFTEST",
                "GENOMICS": "GFTEST", "GENETIC": "GFTEST", "GENE": "GFTEST",
                "MUTATION": "GFTEST", "SNP": "GFTEST", "VARIANT": "GFTEST",

                # Category patterns
                "GFCAT": "GFCAT", "CATEGORY": "GFCAT", "CAT": "GFCAT",
                "GFSCAT": "GFSCAT", "SUBCATEGORY": "GFSCAT", "SUBCAT": "GFSCAT",

                # Result patterns
                "GFORRES": "GFORRES", "RESULT": "GFORRES", "ORRES": "GFORRES",
                "GENOTYPE": "GFORRES", "ALLELE": "GFORRES", "VALUE": "GFORRES",
                "GFSTRESC": "GFSTRESC", "STD_RESULT": "GFSTRESC",

                # Specimen patterns
                "GFSPEC": "GFSPEC", "SPECIMEN": "GFSPEC", "SPEC": "GFSPEC",
                "DNA": "GFSPEC", "RNA": "GFSPEC",

                # Method patterns
                "GFMETHOD": "GFMETHOD", "METHOD": "GFMETHOD", "ASSAY": "GFMETHOD",
                "PCR": "GFMETHOD", "SEQUENCING": "GFMETHOD",

                # Date patterns
                "GFDTC": "GFDTC", "GF_DATE": "GFDTC", "GFDATE": "GFDTC", "DATE": "GFDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # IS - Immunogenicity Specimen Domain
            # =====================================================================
            "IS": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (ISTESTCD)
                "ISTESTCD": "ISTESTCD", "TEST_CODE": "ISTESTCD", "TESTCD": "ISTESTCD",

                # Test name patterns (ISTEST)
                "ISTEST": "ISTEST", "TEST_NAME": "ISTEST", "TEST": "ISTEST",
                "IMMUNOGENICITY": "ISTEST", "ANTIBODY": "ISTEST",
                "ADA": "ISTEST", "ANTI_DRUG_ANTIBODY": "ISTEST",
                "NAB": "ISTEST", "NEUTRALIZING": "ISTEST",

                # Category patterns
                "ISCAT": "ISCAT", "CATEGORY": "ISCAT", "CAT": "ISCAT",
                "ISSCAT": "ISSCAT", "SUBCATEGORY": "ISSCAT", "SUBCAT": "ISSCAT",

                # Result patterns
                "ISORRES": "ISORRES", "RESULT": "ISORRES", "ORRES": "ISORRES",
                "POSITIVE": "ISORRES", "NEGATIVE": "ISORRES", "TITER": "ISORRES",
                "ISORRESU": "ISORRESU", "UNIT": "ISORRESU", "UNITS": "ISORRESU",
                "ISSTRESC": "ISSTRESC", "STD_RESULT_C": "ISSTRESC",
                "ISSTRESN": "ISSTRESN", "STD_RESULT_N": "ISSTRESN",

                # Specimen patterns
                "ISSPEC": "ISSPEC", "SPECIMEN": "ISSPEC", "SPEC": "ISSPEC",

                # Method patterns
                "ISMETHOD": "ISMETHOD", "METHOD": "ISMETHOD", "ASSAY": "ISMETHOD",

                # Date patterns
                "ISDTC": "ISDTC", "IS_DATE": "ISDTC", "ISDATE": "ISDTC", "DATE": "ISDTC",

                # Timepoint patterns
                "ISTPT": "ISTPT", "TIMEPOINT": "ISTPT", "TPT": "ISTPT",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # Trial Design Domains: TA, TE, TI, TS, TV, TD
            # =====================================================================
            "TA": {
                # Trial Arms - no subject identifiers
                "ARMCD": "ARMCD", "ARM_CODE": "ARMCD", "ARMCODE": "ARMCD",
                "ARM": "ARM", "ARM_NAME": "ARM", "ARMNAME": "ARM",
                "TAESSION": "TAESSION", "SESSION": "TAESSION",
                "ETCD": "ETCD", "ELEMENT_CODE": "ETCD", "ELEMENTCD": "ETCD",
                "ELEMENT": "ELEMENT", "STUDY_ELEMENT": "ELEMENT",
                "TABESSION": "TABESSION", "BRANCH_SESSION": "TABESSION",
                "TATRANS": "TATRANS", "TRANSITION": "TATRANS",
                "EPOCH": "EPOCH", "STUDY_EPOCH": "EPOCH",
            },
            "TE": {
                # Trial Elements - no subject identifiers
                "ETCD": "ETCD", "ELEMENT_CODE": "ETCD", "ELEMENTCD": "ETCD",
                "ELEMENT": "ELEMENT", "STUDY_ELEMENT": "ELEMENT",
                "TESTRL": "TESTRL", "RULE": "TESTRL", "START_RULE": "TESTRL",
                "TEENRL": "TEENRL", "END_RULE": "TEENRL",
                "TEDUR": "TEDUR", "DURATION": "TEDUR", "ELEMENT_DURATION": "TEDUR",
            },
            "TI": {
                # Trial Inclusion/Exclusion - no subject identifiers
                "IETESTCD": "IETESTCD", "CRITERIA_CODE": "IETESTCD",
                "IETEST": "IETEST", "CRITERIA": "IETEST", "CRITERION": "IETEST",
                "IECAT": "IECAT", "CATEGORY": "IECAT", "INCLUSION": "IECAT", "EXCLUSION": "IECAT",
                "TIRL": "TIRL", "RULE": "TIRL", "CRITERIA_RULE": "TIRL",
            },
            "TS": {
                # Trial Summary - no subject identifiers
                "TSPARMCD": "TSPARMCD", "PARAM_CODE": "TSPARMCD", "PARAMCD": "TSPARMCD",
                "TSPARM": "TSPARM", "PARAMETER": "TSPARM", "PARAM": "TSPARM",
                "TSVAL": "TSVAL", "VALUE": "TSVAL", "PARAM_VALUE": "TSVAL",
                "TSVALNF": "TSVALNF", "VALUE_NF": "TSVALNF",
                "TSVALCD": "TSVALCD", "VALUE_CODE": "TSVALCD",
            },
            "TV": {
                # Trial Visits - no subject identifiers
                "VISITNUM": "VISITNUM", "VISIT_NUMBER": "VISITNUM", "VISITNO": "VISITNUM",
                "VISIT": "VISIT", "VISIT_NAME": "VISIT", "VISITNAME": "VISIT",
                "TVSTRL": "TVSTRL", "START_RULE": "TVSTRL",
                "TVENRL": "TVENRL", "END_RULE": "TVENRL",
                "ARMCD": "ARMCD", "ARM_CODE": "ARMCD",
            },
            "TD": {
                # Trial Disease Assessments - no subject identifiers
                "TDTESTCD": "TDTESTCD", "TEST_CODE": "TDTESTCD", "TESTCD": "TDTESTCD",
                "TDTEST": "TDTEST", "TEST_NAME": "TDTEST", "TEST": "TDTEST",
                "TDDOMAIN": "TDDOMAIN", "DOMAIN": "TDDOMAIN",
                "TDPARMCD": "TDPARMCD", "PARAM_CODE": "TDPARMCD",
                "TDPARM": "TDPARM", "PARAMETER": "TDPARM",
            },
            # =====================================================================
            # BE - Biospecimen Events Domain
            # =====================================================================
            "BE": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Term patterns
                "BETERM": "BETERM", "BIOSPECIMEN": "BETERM", "SPECIMEN_EVENT": "BETERM",

                # Category patterns
                "BECAT": "BECAT", "CATEGORY": "BECAT", "CAT": "BECAT",
                "BESCAT": "BESCAT", "SUBCATEGORY": "BESCAT", "SUBCAT": "BESCAT",

                # Date patterns
                "BESTDTC": "BESTDTC", "START_DATE": "BESTDTC", "STARTDATE": "BESTDTC",
                "BEENDTC": "BEENDTC", "END_DATE": "BEENDTC", "ENDDATE": "BEENDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # BS - Biospecimen Findings Domain
            # =====================================================================
            "BS": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns
                "BSTESTCD": "BSTESTCD", "TEST_CODE": "BSTESTCD", "TESTCD": "BSTESTCD",

                # Test name patterns
                "BSTEST": "BSTEST", "TEST_NAME": "BSTEST", "TEST": "BSTEST",
                "BIOSPECIMEN_FINDING": "BSTEST", "SPECIMENFINDING": "BSTEST",

                # Result patterns
                "BSORRES": "BSORRES", "RESULT": "BSORRES", "ORRES": "BSORRES",
                "BSSTRESC": "BSSTRESC", "STD_RESULT": "BSSTRESC",

                # Specimen patterns
                "BSSPEC": "BSSPEC", "SPECIMEN": "BSSPEC", "SPEC": "BSSPEC",

                # Date patterns
                "BSDTC": "BSDTC", "BS_DATE": "BSDTC", "BSDATE": "BSDTC", "DATE": "BSDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # CP - Cell Phenotyping Domain
            # =====================================================================
            "CP": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns
                "CPTESTCD": "CPTESTCD", "TEST_CODE": "CPTESTCD", "TESTCD": "CPTESTCD",

                # Test name patterns
                "CPTEST": "CPTEST", "TEST_NAME": "CPTEST", "TEST": "CPTEST",
                "CELL_PHENOTYPE": "CPTEST", "CELLPHENOTYPE": "CPTEST",
                "FLOW_CYTOMETRY": "CPTEST", "FLOWCYTOMETRY": "CPTEST",

                # Result patterns
                "CPORRES": "CPORRES", "RESULT": "CPORRES", "ORRES": "CPORRES",
                "VALUE": "CPORRES", "PERCENTAGE": "CPORRES", "COUNT": "CPORRES",
                "CPORRESU": "CPORRESU", "UNIT": "CPORRESU", "UNITS": "CPORRESU",
                "CPSTRESC": "CPSTRESC", "STD_RESULT_C": "CPSTRESC",
                "CPSTRESN": "CPSTRESN", "STD_RESULT_N": "CPSTRESN",

                # Specimen patterns
                "CPSPEC": "CPSPEC", "SPECIMEN": "CPSPEC", "SPEC": "CPSPEC",

                # Method patterns
                "CPMETHOD": "CPMETHOD", "METHOD": "CPMETHOD",

                # Date patterns
                "CPDTC": "CPDTC", "CP_DATE": "CPDTC", "CPDATE": "CPDTC", "DATE": "CPDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # BM - Bone Measurements (DEXA) Domain
            # =====================================================================
            "BM": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns
                "BMTESTCD": "BMTESTCD", "TEST_CODE": "BMTESTCD", "TESTCD": "BMTESTCD",

                # Test name patterns
                "BMTEST": "BMTEST", "TEST_NAME": "BMTEST", "TEST": "BMTEST",
                "BONE_MEASUREMENT": "BMTEST", "BONEMEASUREMENT": "BMTEST",
                "DEXA": "BMTEST", "DXA": "BMTEST", "BONE_DENSITY": "BMTEST",
                "BMD": "BMTEST", "T_SCORE": "BMTEST", "TSCORE": "BMTEST",

                # Result patterns
                "BMORRES": "BMORRES", "RESULT": "BMORRES", "ORRES": "BMORRES",
                "VALUE": "BMORRES", "DENSITY": "BMORRES",
                "BMORRESU": "BMORRESU", "UNIT": "BMORRESU", "UNITS": "BMORRESU",
                "BMSTRESC": "BMSTRESC", "STD_RESULT_C": "BMSTRESC",
                "BMSTRESN": "BMSTRESN", "STD_RESULT_N": "BMSTRESN",

                # Location patterns
                "BMLOC": "BMLOC", "LOCATION": "BMLOC", "LOC": "BMLOC",
                "SPINE": "BMLOC", "HIP": "BMLOC", "FEMUR": "BMLOC",
                "BMLAT": "BMLAT", "LATERALITY": "BMLAT", "LAT": "BMLAT",

                # Method patterns
                "BMMETHOD": "BMMETHOD", "METHOD": "BMMETHOD",

                # Date patterns
                "BMDTC": "BMDTC", "BM_DATE": "BMDTC", "BMDATE": "BMDTC", "DATE": "BMDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # MO - Morphology (Sperm) Domain
            # =====================================================================
            "MO": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (MOTESTCD)
                "MOTESTCD": "MOTESTCD", "TEST_CODE": "MOTESTCD", "TESTCD": "MOTESTCD",

                # Test name patterns (MOTEST)
                "MOTEST": "MOTEST", "TEST_NAME": "MOTEST", "TEST": "MOTEST",
                "MORPHOLOGY": "MOTEST", "SPERM_MORPHOLOGY": "MOTEST",
                "SPERM": "MOTEST", "SPERMATOZOA": "MOTEST",
                "MOTILITY": "MOTEST", "CONCENTRATION": "MOTEST",

                # Category patterns
                "MOCAT": "MOCAT", "CATEGORY": "MOCAT", "CAT": "MOCAT",
                "MOSCAT": "MOSCAT", "SUBCATEGORY": "MOSCAT", "SUBCAT": "MOSCAT",

                # Result patterns
                "MOORRES": "MOORRES", "RESULT": "MOORRES", "ORRES": "MOORRES",
                "VALUE": "MOORRES", "PERCENTAGE": "MOORRES", "COUNT": "MOORRES",
                "MOORRESU": "MOORRESU", "UNIT": "MOORRESU", "UNITS": "MOORRESU",
                "MOSTRESC": "MOSTRESC", "STD_RESULT_C": "MOSTRESC",
                "MOSTRESN": "MOSTRESN", "STD_RESULT_N": "MOSTRESN",

                # Specimen patterns
                "MOSPEC": "MOSPEC", "SPECIMEN": "MOSPEC", "SPEC": "MOSPEC",
                "SEMEN": "MOSPEC", "EJACULATE": "MOSPEC",

                # Method patterns
                "MOMETHOD": "MOMETHOD", "METHOD": "MOMETHOD",

                # Date patterns
                "MODTC": "MODTC", "MO_DATE": "MODTC", "MODATE": "MODTC", "DATE": "MODTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # RP - Reproductive System Findings Domain
            # =====================================================================
            "RP": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Test code patterns (RPTESTCD)
                "RPTESTCD": "RPTESTCD", "TEST_CODE": "RPTESTCD", "TESTCD": "RPTESTCD",

                # Test name patterns (RPTEST)
                "RPTEST": "RPTEST", "TEST_NAME": "RPTEST", "TEST": "RPTEST",
                "REPRODUCTIVE": "RPTEST", "REPRO_FINDING": "RPTEST",
                "PREGNANCY": "RPTEST", "FERTILITY": "RPTEST",
                "MENSTRUAL": "RPTEST", "OVULATION": "RPTEST",

                # Category patterns
                "RPCAT": "RPCAT", "CATEGORY": "RPCAT", "CAT": "RPCAT",
                "RPSCAT": "RPSCAT", "SUBCATEGORY": "RPSCAT", "SUBCAT": "RPSCAT",

                # Result patterns
                "RPORRES": "RPORRES", "RESULT": "RPORRES", "ORRES": "RPORRES",
                "VALUE": "RPORRES", "FINDING": "RPORRES",
                "RPSTRESC": "RPSTRESC", "STD_RESULT_C": "RPSTRESC",
                "RPSTRESN": "RPSTRESN", "STD_RESULT_N": "RPSTRESN",

                # Date patterns
                "RPDTC": "RPDTC", "RP_DATE": "RPDTC", "RPDATE": "RPDTC", "DATE": "RPDTC",
                "LMP": "RPDTC", "LAST_MENSTRUAL": "RPDTC",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
            # =====================================================================
            # SM - Subject Medical/Surgical History Domain
            # =====================================================================
            "SM": {
                # Subject identifier patterns
                "SUBJECT_ID": "USUBJID", "USUBJID": "USUBJID", "SUBJID": "USUBJID",

                # Term patterns (SMTERM)
                "SMTERM": "SMTERM", "SURGERY": "SMTERM", "SURGICAL_HISTORY": "SMTERM",
                "SURGHX": "SMTERM", "OPERATION": "SMTERM", "PROCEDURE_HX": "SMTERM",

                # Decoded term (SMDECOD)
                "SMDECOD": "SMDECOD", "DECOD": "SMDECOD", "DECODED": "SMDECOD",

                # Category patterns
                "SMCAT": "SMCAT", "CATEGORY": "SMCAT", "CAT": "SMCAT",
                "SMSCAT": "SMSCAT", "SUBCATEGORY": "SMSCAT", "SUBCAT": "SMSCAT",

                # Pre-specified and occurrence
                "SMPRESP": "SMPRESP", "PRESPECIFIED": "SMPRESP", "PRESP": "SMPRESP",
                "SMOCCUR": "SMOCCUR", "OCCURRED": "SMOCCUR", "OCCUR": "SMOCCUR",

                # Body system (SMBODSYS)
                "SMBODSYS": "SMBODSYS", "BODY_SYSTEM": "SMBODSYS", "BODSYS": "SMBODSYS",

                # Status patterns
                "SMSTAT": "SMSTAT", "STATUS": "SMSTAT", "STAT": "SMSTAT",

                # Date patterns
                "SMSTDTC": "SMSTDTC", "START_DATE": "SMSTDTC", "STARTDATE": "SMSTDTC",
                "SURGERY_DATE": "SMSTDTC", "SURGERYDATE": "SMSTDTC",
                "SMENDTC": "SMENDTC", "END_DATE": "SMENDTC", "ENDDATE": "SMENDTC",
                "SMDTC": "SMDTC", "SM_DATE": "SMDTC", "SMDATE": "SMDTC",

                # Ongoing/continuing
                "SMENRF": "SMENRF", "END_REF": "SMENRF", "ONGOING": "SMENRF",

                # Visit and epoch
                "VISITNUM": "VISITNUM", "VISIT": "VISIT", "EPOCH": "EPOCH",
            },
        }

        patterns = domain_mappings.get(domain, {})
        column_mappings = []
        mapped_targets = set()

        def normalize_col(name: str) -> str:
            """Normalize column name for matching."""
            return name.upper().replace("_", "").replace(" ", "").replace("-", "")

        def find_match(col: str, patterns: dict) -> Optional[str]:
            """Find a matching SDTM variable for a source column."""
            col_upper = col.upper()
            col_normalized = normalize_col(col)

            # 1. Exact match (case-insensitive)
            if col_upper in patterns:
                return patterns[col_upper]

            # 2. Normalized match (remove underscores/spaces)
            for pattern_key, target in patterns.items():
                if normalize_col(pattern_key) == col_normalized:
                    return target

            # 3. Contains match - source column contains pattern
            for pattern_key, target in patterns.items():
                pattern_normalized = normalize_col(pattern_key)
                if len(pattern_normalized) >= 3 and pattern_normalized in col_normalized:
                    return target

            # 4. Contains match - pattern contains source column
            for pattern_key, target in patterns.items():
                pattern_normalized = normalize_col(pattern_key)
                if len(col_normalized) >= 3 and col_normalized in pattern_normalized:
                    return target

            return None

        for col in df.columns:
            target = find_match(col, patterns)

            if target and target not in mapped_targets:
                column_mappings.append({
                    "source_column": col,
                    "target_variable": target,
                    "transformation": None,
                    "comments": f"Direct mapping from {col}",
                })
                mapped_targets.add(target)

        # Add derived variables
        derivations = {}
        if domain == "DM":
            derivations["USUBJID"] = f"concat('{study_id}', '-', SUBJID)"
            derivations["STUDYID"] = f"'{study_id}'"
            derivations["DOMAIN"] = "'DM'"
        else:
            derivations["STUDYID"] = f"'{study_id}'"
            derivations["DOMAIN"] = f"'{domain}'"
            derivations[f"{domain}SEQ"] = "row_number()"

        spec = {
            "study_id": study_id,
            "source_domain": os.path.basename(source_file),
            "target_domain": domain,
            "column_mappings": column_mappings,
            "derivation_rules": derivations,
            "source_columns": list(df.columns),
            "generated_at": datetime.now().isoformat(),
        }

        return {
            "success": True,
            "mapping_spec": spec,
            "columns_mapped": len(column_mappings),
            "columns_unmapped": len(df.columns) - len(column_mappings),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
async def save_mapping_spec(mapping_spec: Dict[str, Any], output_path: str) -> Dict[str, Any]:
    """
    Save mapping specification to JSON file (async).

    Args:
        mapping_spec: Mapping specification dictionary
        output_path: Path to save JSON file

    Returns:
        Save result
    """
    try:
        # Async JSON write
        await async_write_json(mapping_spec, output_path)

        size = await async_getsize(output_path)
        return {
            "success": True,
            "output_path": output_path,
            "size_kb": round(size / 1024, 2),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# TRANSFORMATION TOOLS (Async)
# =============================================================================

@tool
async def transform_to_sdtm(
    source_file: str,
    mapping_spec: Dict[str, Any],
    output_path: str,
) -> Dict[str, Any]:
    """
    Transform source data to SDTM format using mapping specification (async).

    Args:
        source_file: Path to source CSV
        mapping_spec: Mapping specification with column mappings
        output_path: Path to save SDTM CSV

    Returns:
        Transformation result
    """
    try:
        # Async CSV read
        df = await async_read_csv(source_file)
        records_in = len(df)

        domain = mapping_spec.get("target_domain", "UNKNOWN")
        study_id = mapping_spec.get("study_id", "UNKNOWN")

        # Create output dataframe
        sdtm = pd.DataFrame()

        # Apply standard identifiers
        sdtm["STUDYID"] = study_id
        sdtm["DOMAIN"] = domain

        # Apply column mappings
        for mapping in mapping_spec.get("column_mappings", []):
            src = mapping.get("source_column")
            tgt = mapping.get("target_variable")
            if src and tgt and src in df.columns:
                sdtm[tgt] = df[src]

        # Generate USUBJID if SUBJID exists
        if "SUBJID" in sdtm.columns and "USUBJID" not in sdtm.columns:
            sdtm["USUBJID"] = study_id + "-" + sdtm["SUBJID"].astype(str)
        elif "USUBJID" in sdtm.columns:
            # Ensure proper format
            if not sdtm["USUBJID"].str.contains("-").any():
                sdtm["USUBJID"] = study_id + "-" + sdtm["USUBJID"].astype(str)

        # Add sequence variable
        seq_var = f"{domain}SEQ"
        if seq_var not in sdtm.columns:
            sdtm[seq_var] = range(1, len(sdtm) + 1)

        # Reorder columns (identifiers first)
        id_cols = ["STUDYID", "DOMAIN", "USUBJID", seq_var]
        other_cols = [c for c in sdtm.columns if c not in id_cols]
        sdtm = sdtm[[c for c in id_cols if c in sdtm.columns] + other_cols]

        # Async CSV write
        await async_to_csv(sdtm, output_path, index=False)

        return {
            "success": True,
            "domain": domain,
            "records_in": records_in,
            "records_out": len(sdtm),
            "columns_out": len(sdtm.columns),
            "output_path": output_path,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# MAPPING SPECIFICATION-DRIVEN TOOLS (Async)
# =============================================================================

# Global engine instance for multi-step operations
_mapping_engine: Optional[SDTMTransformationEngine] = None


@tool
async def load_mapping_specification(spec_path: str) -> Dict[str, Any]:
    """
    Load an SDTM mapping specification file (Excel format).

    The mapping specification defines transformation rules for converting
    source data to SDTM domains. It supports functions like:
    - ASSIGN("value") - Assign constant value
    - CONCAT(a, b, ...) - Concatenate values
    - SUBSTR(field, start, length) - Extract substring
    - IF(condition, true_val, false_val) - Conditional logic
    - ISO8601DATEFORMAT(field, format) - Date conversion
    - FORMAT(field, codelist) - Codelist lookup
    - UPCASE(field), TRIM(field), COMPRESS(field) - String manipulation
    - set to VARIABLE - Direct column mapping

    Args:
        spec_path: Path to the mapping specification file (.xls, .xlsx)

    Returns:
        Information about the loaded specification including available domains
    """
    global _mapping_engine

    try:
        _mapping_engine = SDTMTransformationEngine()
        spec = await _mapping_engine.load_specification(spec_path)

        domains_info = []
        for domain_code, domain_mapping in spec.domains.items():
            domains_info.append({
                "domain": domain_code,
                "label": domain_mapping.label,
                "num_variables": len(domain_mapping.variables),
                "source_datasets": domain_mapping.source_datasets,
                "required_vars": [v.variable for v in domain_mapping.variables if v.core == 'req'],
            })

        return {
            "success": True,
            "spec_path": spec_path,
            "study_id": spec.study_id,
            "sponsor": spec.sponsor,
            "protocol": spec.protocol,
            "domains_available": len(spec.domains),
            "domains": domains_info,
            "raw_datasets_defined": list(spec.raw_datasets.keys()),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
async def transform_domain_with_spec(
    domain: str,
    source_files: Dict[str, str],
    output_path: str,
    study_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Transform source data to an SDTM domain using the loaded mapping specification.

    Uses the transformation rules defined in the mapping spec to convert
    source data. The spec must be loaded first with load_mapping_specification.

    Args:
        domain: Target SDTM domain code (e.g., 'DM', 'AE', 'VS', 'LB')
        source_files: Dictionary mapping dataset names to file paths
                      e.g., {"DEMO": "/data/demo.csv", "VISITS": "/data/visits.csv"}
        output_path: Path to save the transformed SDTM CSV
        study_id: Optional study identifier (overrides value from spec)

    Returns:
        Transformation result with record counts and validation info
    """
    global _mapping_engine

    if _mapping_engine is None:
        return {
            "success": False,
            "error": "No mapping specification loaded. Call load_mapping_specification first."
        }

    try:
        # Load source data files
        source_data = {}
        total_source_records = 0

        for ds_name, file_path in source_files.items():
            df = await async_read_csv(file_path)
            source_data[ds_name] = df
            total_source_records += len(df)

        # Transform using the engine
        result_df = await _mapping_engine.transform_domain(
            domain=domain,
            source_data=source_data,
            study_id=study_id,
        )

        # Save output
        await async_to_csv(result_df, output_path, index=False)

        # Calculate statistics
        null_counts = result_df.isnull().sum().to_dict()
        columns_with_nulls = {k: v for k, v in null_counts.items() if v > 0}

        return {
            "success": True,
            "domain": domain.upper(),
            "source_datasets": list(source_files.keys()),
            "source_records": total_source_records,
            "records_out": len(result_df),
            "columns_out": len(result_df.columns),
            "output_columns": list(result_df.columns),
            "columns_with_nulls": columns_with_nulls,
            "output_path": output_path,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
async def get_domain_mapping_details(domain: str) -> Dict[str, Any]:
    """
    Get detailed mapping information for a specific SDTM domain.

    Shows all variable mappings, transformation rules, and source requirements
    for the specified domain. The spec must be loaded first.

    Args:
        domain: SDTM domain code (e.g., 'DM', 'AE', 'VS')

    Returns:
        Detailed mapping information for the domain
    """
    global _mapping_engine

    if _mapping_engine is None:
        return {
            "success": False,
            "error": "No mapping specification loaded. Call load_mapping_specification first."
        }

    try:
        info = _mapping_engine.get_domain_info(domain)
        if not info:
            return {
                "success": False,
                "error": f"Domain {domain} not found in loaded specification"
            }

        # Add more detail about variable mappings
        spec = _mapping_engine._spec
        domain_mapping = spec.domains[domain.upper()]

        variables_detail = []
        for v in domain_mapping.variables:
            variables_detail.append({
                "variable": v.variable,
                "label": v.label,
                "data_type": v.data_type,
                "length": v.length,
                "core": v.core,
                "role": v.role,
                "source_datasets": v.source_datasets,
                "source_variables": v.source_variables,
                "rule": v.rule,
                "controlled_terms": v.controlled_terms,
            })

        return {
            "success": True,
            "domain": domain.upper(),
            "label": info['label'],
            "num_variables": info['num_variables'],
            "source_datasets_required": info['source_datasets'],
            "variables": variables_detail,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
async def transform_domain_standalone(
    spec_path: str,
    domain: str,
    source_files: Dict[str, str],
    output_path: str,
    study_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Transform source data to SDTM using a mapping specification (standalone).

    This is a single-call version that loads the spec and transforms in one step.
    Use this for one-off transformations. For batch processing multiple domains,
    use load_mapping_specification + transform_domain_with_spec.

    Args:
        spec_path: Path to the mapping specification file (.xls, .xlsx)
        domain: Target SDTM domain code
        source_files: Dictionary mapping dataset names to file paths
        output_path: Path to save the transformed SDTM CSV
        study_id: Optional study identifier override

    Returns:
        Transformation result
    """
    try:
        # Load source data
        source_data = {}
        for ds_name, file_path in source_files.items():
            df = await async_read_csv(file_path)
            source_data[ds_name] = df

        # Transform using convenience function
        result_df = await transform_with_spec(
            spec_path=spec_path,
            domain=domain,
            source_data=source_data,
            study_id=study_id,
        )

        # Save output
        await async_to_csv(result_df, output_path, index=False)

        return {
            "success": True,
            "domain": domain.upper(),
            "records_out": len(result_df),
            "columns_out": len(result_df.columns),
            "output_columns": list(result_df.columns),
            "output_path": output_path,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
async def list_mapping_spec_domains(spec_path: Optional[str] = None) -> Dict[str, Any]:
    """
    List all domains available in a mapping specification.

    Either uses a loaded spec or loads from the provided path.

    Args:
        spec_path: Optional path to mapping spec file. If not provided,
                   uses the currently loaded specification.

    Returns:
        List of available domains with basic info
    """
    global _mapping_engine

    try:
        if spec_path:
            # Load a new spec temporarily
            parser = MappingSpecificationParser()
            spec = await parser.parse_excel(spec_path)
        elif _mapping_engine and _mapping_engine._spec:
            spec = _mapping_engine._spec
        else:
            return {
                "success": False,
                "error": "No spec_path provided and no specification loaded."
            }

        domains = []
        for domain_code, domain_mapping in spec.domains.items():
            required_vars = [v.variable for v in domain_mapping.variables if v.core.lower() == 'req']
            expected_vars = [v.variable for v in domain_mapping.variables if v.core.lower() == 'exp']

            domains.append({
                "domain": domain_code,
                "label": domain_mapping.label,
                "total_variables": len(domain_mapping.variables),
                "required_variables": len(required_vars),
                "expected_variables": len(expected_vars),
                "source_datasets": domain_mapping.source_datasets,
            })

        return {
            "success": True,
            "study_id": spec.study_id,
            "total_domains": len(domains),
            "domains": domains,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# REPORTING TOOLS (Async)
# =============================================================================

@tool
async def generate_pipeline_report(
    study_id: str,
    transformation_results: List[Dict[str, Any]],
    validation_results: List[Dict[str, Any]],
    output_path: str,
) -> Dict[str, Any]:
    """
    Generate comprehensive pipeline execution report (async).

    Args:
        study_id: Study identifier
        transformation_results: List of transformation results
        validation_results: List of validation results
        output_path: Path to save report JSON

    Returns:
        Report generation result
    """
    try:
        # Calculate statistics
        total_records_in = sum(r.get("records_in", 0) for r in transformation_results)
        total_records_out = sum(r.get("records_out", 0) for r in transformation_results)
        successful_transforms = sum(1 for r in transformation_results if r.get("success"))

        total_errors = sum(r.get("error_count", 0) for r in validation_results)
        total_warnings = sum(r.get("warning_count", 0) for r in validation_results)
        passed_validations = sum(1 for r in validation_results if r.get("is_valid"))

        compliance_score = (passed_validations / len(validation_results) * 100) if validation_results else 0

        report = {
            "study_id": study_id,
            "generated_at": datetime.now().isoformat(),
            "status": "success" if compliance_score >= 95 else "requires_review",
            "summary": {
                "domains_processed": len(transformation_results),
                "successful_transformations": successful_transforms,
                "total_records_in": total_records_in,
                "total_records_out": total_records_out,
                "validation_errors": total_errors,
                "validation_warnings": total_warnings,
                "compliance_score": round(compliance_score, 1),
                "submission_ready": compliance_score >= 95 and total_errors == 0,
            },
            "transformations": transformation_results,
            "validations": validation_results,
        }

        # Async JSON write
        await async_write_json(report, output_path)

        return {
            "success": True,
            "output_path": output_path,
            "compliance_score": compliance_score,
            "submission_ready": report["summary"]["submission_ready"],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# BASH EXECUTION TOOL (Async)
# =============================================================================

@tool
async def execute_bash(command: str, timeout: int = 120, working_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute a bash command asynchronously.

    Args:
        command: The bash command to execute
        timeout: Maximum execution time in seconds (default: 120)
        working_dir: Working directory for command execution (optional)

    Returns:
        Dict with stdout, stderr, return_code, and success status
    """
    import shlex

    # Safety checks - block dangerous commands
    dangerous_patterns = [
        "rm -rf /", "rm -rf /*", "mkfs", "dd if=", ":(){:|:&};:",
        "chmod -R 777 /", "chown -R", "> /dev/sda", "wget | sh",
        "curl | sh", "eval", "$(", "`",
    ]

    command_lower = command.lower()
    for pattern in dangerous_patterns:
        if pattern in command_lower:
            return {
                "success": False,
                "error": f"Blocked dangerous command pattern: {pattern}",
                "stdout": "",
                "stderr": "",
                "return_code": -1,
            }

    try:
        # Create subprocess
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir,
        )

        # Wait for completion with timeout
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds",
                "stdout": "",
                "stderr": "",
                "return_code": -1,
            }

        # Decode output
        stdout_str = stdout.decode("utf-8", errors="replace").strip()
        stderr_str = stderr.decode("utf-8", errors="replace").strip()

        # Truncate if too long
        max_output = 50000
        if len(stdout_str) > max_output:
            stdout_str = stdout_str[:max_output] + f"\n... (truncated, {len(stdout_str)} total chars)"
        if len(stderr_str) > max_output:
            stderr_str = stderr_str[:max_output] + f"\n... (truncated, {len(stderr_str)} total chars)"

        return {
            "success": process.returncode == 0,
            "stdout": stdout_str,
            "stderr": stderr_str,
            "return_code": process.returncode,
            "command": command,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "stdout": "",
            "stderr": "",
            "return_code": -1,
        }


# =============================================================================
# FRONTEND CHART TOOLS (Recharts-Compatible)
# =============================================================================
# These tools generate chart data in a format compatible with the frontend's
# Recharts-based ChartRenderer. The agent should include the returned
# "chart_markdown" in its response to display charts in the frontend.
#
# Frontend expects charts as markdown code blocks:
#   ```chart
#   {"type": "bar", "data": [...], "title": "...", ...}
#   ```

@tool
async def create_bar_chart(
    data: List[Dict[str, Any]],
    title: str,
    x_key: str = "name",
    y_key: str = "value",
    show_legend: bool = False,
    show_grid: bool = True,
    stacked: bool = False,
    colors: Optional[List[str]] = None,
    series: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Create a bar chart for display in the frontend.

    The returned chart_markdown should be included in your response to render
    the chart in the frontend.

    Args:
        data: List of data objects, e.g., [{"name": "DM", "value": 95}, {"name": "AE", "value": 87}]
        title: Chart title
        x_key: Key in data objects for x-axis categories (default: "name")
        y_key: Key in data objects for y-axis values (default: "value")
        show_legend: Whether to show legend
        show_grid: Whether to show grid lines
        stacked: Whether to stack bars (for multi-series)
        colors: Optional list of colors for the bars
        series: Optional list of series for multi-series charts
                e.g., [{"dataKey": "score", "name": "Score"}, {"dataKey": "errors", "name": "Errors"}]

    Returns:
        Dict with chart_markdown to include in response, and chart_data for reference

    Example:
        result = await create_bar_chart(
            data=[{"name": "DM", "value": 95}, {"name": "AE", "value": 87}],
            title="Domain Compliance Scores"
        )
        # Include result["chart_markdown"] in your response
    """
    chart_data = {
        "type": "bar",
        "title": title,
        "data": data,
        "xKey": x_key,
        "yKey": y_key,
        "showLegend": show_legend,
        "showGrid": show_grid,
        "stacked": stacked,
    }

    if colors:
        chart_data["colors"] = colors
    if series:
        chart_data["series"] = series

    # Return the chart data - agent should format as markdown code block
    return {
        "success": True,
        "type": "bar",
        "chart": chart_data,
        "instructions": "To display this chart, include a code block in your response with language 'chart' containing this JSON data."
    }


@tool
async def create_line_chart(
    data: List[Dict[str, Any]],
    title: str,
    x_key: str = "name",
    y_key: str = "value",
    show_legend: bool = True,
    show_grid: bool = True,
    colors: Optional[List[str]] = None,
    series: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Create a line chart for display in the frontend.

    Args:
        data: List of data objects with x and y values
              e.g., [{"week": "Week1", "score": 80}, {"week": "Week2", "score": 90}]
        title: Chart title
        x_key: Key for x-axis (default: "name")
        y_key: Key for y-axis (default: "value")
        show_legend: Whether to show legend
        show_grid: Whether to show grid lines
        colors: Optional list of colors
        series: For multi-line charts, list of series definitions
                e.g., [{"dataKey": "dm_score", "name": "DM"}, {"dataKey": "ae_score", "name": "AE"}]

    Returns:
        Dict with chart_markdown to include in response

    Example:
        result = await create_line_chart(
            data=[{"week": "W1", "dm": 80, "ae": 70}, {"week": "W2", "dm": 90, "ae": 85}],
            title="Compliance Over Time",
            x_key="week",
            series=[{"dataKey": "dm", "name": "DM"}, {"dataKey": "ae", "name": "AE"}]
        )
    """
    chart_data = {
        "type": "line",
        "title": title,
        "data": data,
        "xKey": x_key,
        "yKey": y_key,
        "showLegend": show_legend,
        "showGrid": show_grid,
    }

    if colors:
        chart_data["colors"] = colors
    if series:
        chart_data["series"] = series

    # Return the chart data - agent should format as markdown code block
    return {
        "success": True,
        "type": "line",
        "chart": chart_data,
        "instructions": "To display this chart, include a code block in your response with language 'chart' containing this JSON data."
    }


@tool
async def create_pie_chart(
    data: List[Dict[str, Any]],
    title: str,
    name_key: str = "name",
    value_key: str = "value",
    show_legend: bool = True,
    colors: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create a pie/donut chart for display in the frontend.

    Args:
        data: List of data objects with name and value
              e.g., [{"name": "Pass", "value": 85}, {"name": "Fail", "value": 10}, {"name": "Warning", "value": 5}]
        title: Chart title
        name_key: Key for segment names (default: "name")
        value_key: Key for segment values (default: "value")
        show_legend: Whether to show legend
        colors: Optional list of colors for segments

    Returns:
        Dict with chart_markdown to include in response

    Example:
        result = await create_pie_chart(
            data=[{"name": "Pass", "value": 85}, {"name": "Fail", "value": 15}],
            title="Validation Results"
        )
    """
    chart_data = {
        "type": "pie",
        "title": title,
        "data": data,
        "xKey": name_key,
        "yKey": value_key,
        "showLegend": show_legend,
    }

    if colors:
        chart_data["colors"] = colors

    # Return the chart data - agent should format as markdown code block
    return {
        "success": True,
        "type": "pie",
        "chart": chart_data,
        "instructions": "To display this chart, include a code block in your response with language 'chart' containing this JSON data."
    }


@tool
async def create_area_chart(
    data: List[Dict[str, Any]],
    title: str,
    x_key: str = "name",
    y_key: str = "value",
    show_legend: bool = True,
    show_grid: bool = True,
    stacked: bool = False,
    colors: Optional[List[str]] = None,
    series: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Create an area chart for display in the frontend.

    Args:
        data: List of data objects
        title: Chart title
        x_key: Key for x-axis (default: "name")
        y_key: Key for y-axis (default: "value")
        show_legend: Whether to show legend
        show_grid: Whether to show grid lines
        stacked: Whether to stack areas
        colors: Optional list of colors
        series: For multi-area charts, list of series definitions

    Returns:
        Dict with chart_markdown to include in response
    """
    chart_data = {
        "type": "area",
        "title": title,
        "data": data,
        "xKey": x_key,
        "yKey": y_key,
        "showLegend": show_legend,
        "showGrid": show_grid,
        "stacked": stacked,
    }

    if colors:
        chart_data["colors"] = colors
    if series:
        chart_data["series"] = series

    # Return the chart data - agent should format as markdown code block
    return {
        "success": True,
        "type": "area",
        "chart": chart_data,
        "instructions": "To display this chart, include a code block in your response with language 'chart' containing this JSON data."
    }


@tool
async def create_scatter_chart(
    data: List[Dict[str, Any]],
    title: str,
    x_key: str = "x",
    y_key: str = "y",
    show_legend: bool = True,
    show_grid: bool = True,
    colors: Optional[List[str]] = None,
    series: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Create a scatter plot for display in the frontend.

    Args:
        data: List of data objects with x, y values
              e.g., [{"x": 10, "y": 20}, {"x": 15, "y": 25}]
        title: Chart title
        x_key: Key for x values (default: "x")
        y_key: Key for y values (default: "y")
        show_legend: Whether to show legend
        show_grid: Whether to show grid lines
        colors: Optional list of colors
        series: For multi-series, categorize by a "category" field in data

    Returns:
        Dict with chart_markdown to include in response
    """
    chart_data = {
        "type": "scatter",
        "title": title,
        "data": data,
        "xKey": x_key,
        "yKey": y_key,
        "showLegend": show_legend,
        "showGrid": show_grid,
    }

    if colors:
        chart_data["colors"] = colors
    if series:
        chart_data["series"] = series

    # Return the chart data - agent should format as markdown code block
    return {
        "success": True,
        "type": "scatter",
        "chart": chart_data,
        "instructions": "To display this chart, include a code block in your response with language 'chart' containing this JSON data."
    }


@tool
async def create_radar_chart(
    data: List[Dict[str, Any]],
    title: str,
    name_key: str = "name",
    value_key: str = "value",
    show_legend: bool = True,
    colors: Optional[List[str]] = None,
    series: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Create a radar chart for display in the frontend.

    Args:
        data: List of data objects representing axes
              e.g., [{"name": "Accuracy", "value": 90}, {"name": "Speed", "value": 85}]
        title: Chart title
        name_key: Key for axis names (default: "name")
        value_key: Key for values (default: "value")
        show_legend: Whether to show legend
        colors: Optional list of colors
        series: For multi-series radar, define multiple value keys

    Returns:
        Dict with chart_markdown to include in response
    """
    chart_data = {
        "type": "radar",
        "title": title,
        "data": data,
        "xKey": name_key,
        "yKey": value_key,
        "showLegend": show_legend,
    }

    if colors:
        chart_data["colors"] = colors
    if series:
        chart_data["series"] = series

    # Return the chart data - agent should format as markdown code block
    return {
        "success": True,
        "type": "radar",
        "chart": chart_data,
        "instructions": "To display this chart, include a code block in your response with language 'chart' containing this JSON data."
    }


@tool
async def create_funnel_chart(
    data: List[Dict[str, Any]],
    title: str,
    name_key: str = "name",
    value_key: str = "value",
    show_legend: bool = True,
    colors: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create a funnel chart for display in the frontend.

    Args:
        data: List of data objects in funnel order (largest to smallest)
              e.g., [{"name": "Visits", "value": 1000}, {"name": "Clicks", "value": 500}]
        title: Chart title
        name_key: Key for stage names (default: "name")
        value_key: Key for values (default: "value")
        show_legend: Whether to show legend
        colors: Optional list of colors

    Returns:
        Dict with chart_markdown to include in response
    """
    chart_data = {
        "type": "funnel",
        "title": title,
        "data": data,
        "xKey": name_key,
        "yKey": value_key,
        "showLegend": show_legend,
    }

    if colors:
        chart_data["colors"] = colors

    # Return the chart data - agent should format as markdown code block
    return {
        "success": True,
        "type": "funnel",
        "chart": chart_data,
        "instructions": "To display this chart, include a code block in your response with language 'chart' containing this JSON data."
    }


@tool
async def create_composed_chart(
    data: List[Dict[str, Any]],
    title: str,
    x_key: str = "name",
    series: List[Dict[str, str]] = None,
    show_legend: bool = True,
    show_grid: bool = True,
    colors: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create a composed chart with multiple chart types (bar, line, area) in one.

    Args:
        data: List of data objects with all series values
        title: Chart title
        x_key: Key for x-axis (default: "name")
        series: List of series with type specification
                e.g., [
                    {"dataKey": "records", "name": "Records", "type": "bar"},
                    {"dataKey": "score", "name": "Score", "type": "line"},
                    {"dataKey": "trend", "name": "Trend", "type": "area"}
                ]
        show_legend: Whether to show legend
        show_grid: Whether to show grid lines
        colors: Optional list of colors

    Returns:
        Dict with chart_markdown to include in response

    Example:
        result = await create_composed_chart(
            data=[
                {"name": "DM", "records": 100, "score": 95},
                {"name": "AE", "records": 80, "score": 87}
            ],
            title="Domain Overview",
            series=[
                {"dataKey": "records", "name": "Records", "type": "bar"},
                {"dataKey": "score", "name": "Score (%)", "type": "line"}
            ]
        )
    """
    if not series:
        return {"success": False, "error": "series parameter is required for composed charts"}

    chart_data = {
        "type": "composed",
        "title": title,
        "data": data,
        "xKey": x_key,
        "series": series,
        "showLegend": show_legend,
        "showGrid": show_grid,
    }

    if colors:
        chart_data["colors"] = colors

    # Return the chart data - agent should format as markdown code block
    return {
        "success": True,
        "type": "composed",
        "chart": chart_data,
        "instructions": "To display this chart, include a code block in your response with language 'chart' containing this JSON data."
    }


@tool
async def create_sdtm_validation_dashboard(
    domains: Dict[str, Dict[str, Any]],
    overall_score: float,
    study_id: str = "STUDY"
) -> Dict[str, Any]:
    """
    Create a comprehensive SDTM validation dashboard with multiple charts.
    Returns multiple chart markdown blocks that can be included in the response.

    Args:
        domains: Dict of domain validation results
                 e.g., {"DM": {"score": 95, "errors": 2, "warnings": 5}, "AE": {"score": 87, "errors": 5, "warnings": 10}}
        overall_score: Overall compliance score (0-100)
        study_id: Study identifier for titles

    Returns:
        Dict with dashboard_markdown containing all charts

    Example:
        result = await create_sdtm_validation_dashboard(
            domains={
                "DM": {"score": 95, "errors": 2, "warnings": 5},
                "AE": {"score": 87, "errors": 5, "warnings": 10},
                "VS": {"score": 92, "errors": 3, "warnings": 8}
            },
            overall_score=91.3,
            study_id="ABC-001"
        )
    """
    if not domains:
        return {"success": False, "error": "No domain data provided"}

    # Prepare data for charts
    domain_names = list(domains.keys())
    scores_data = [{"name": d, "value": domains[d].get("score", 0)} for d in domain_names]

    issues_data = [
        {"name": d, "errors": domains[d].get("errors", 0), "warnings": domains[d].get("warnings", 0)}
        for d in domain_names
    ]

    total_errors = sum(d.get("errors", 0) for d in domains.values())
    total_warnings = sum(d.get("warnings", 0) for d in domains.values())
    total_pass = max(0, len(domains) * 100 - total_errors - total_warnings)

    distribution_data = [
        {"name": "Pass", "value": total_pass},
        {"name": "Errors", "value": total_errors},
        {"name": "Warnings", "value": total_warnings}
    ]

    # Create chart 1: Compliance Scores Bar Chart
    chart1 = {
        "type": "bar",
        "title": f"{study_id} - Compliance Score by Domain",
        "data": scores_data,
        "xKey": "name",
        "yKey": "value",
        "showGrid": True,
        "showLegend": False,
        "colors": ["#00CC96" if s["value"] >= 90 else "#FFA15A" if s["value"] >= 80 else "#EF553B" for s in scores_data]
    }

    # Create chart 2: Issues Stacked Bar Chart
    chart2 = {
        "type": "bar",
        "title": "Issues by Domain",
        "data": issues_data,
        "xKey": "name",
        "series": [
            {"dataKey": "errors", "name": "Errors"},
            {"dataKey": "warnings", "name": "Warnings"}
        ],
        "showGrid": True,
        "showLegend": True,
        "stacked": True,
        "colors": ["#EF553B", "#FFA15A"]
    }

    # Create chart 3: Distribution Pie Chart
    chart3 = {
        "type": "pie",
        "title": "Issue Distribution",
        "data": distribution_data,
        "xKey": "name",
        "yKey": "value",
        "showLegend": True,
        "colors": ["#00CC96", "#EF553B", "#FFA15A"]
    }

    # Return individual charts for the agent to format
    return {
        "success": True,
        "type": "dashboard",
        "study_id": study_id,
        "overall_score": overall_score,
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "domains_count": len(domains),
        "submission_ready": overall_score >= 90 and total_errors == 0,
        "charts": {
            "compliance_scores": chart1,
            "issues_by_domain": chart2,
            "issue_distribution": chart3
        },
        "instructions": "Create a dashboard with these 3 charts. For each chart, write a ```chart code block with the JSON data on a single line."
    }


# Visualization tools list (Frontend-compatible)
VISUALIZATION_TOOLS = [
    create_bar_chart,
    create_line_chart,
    create_pie_chart,
    create_area_chart,
    create_scatter_chart,
    create_radar_chart,
    create_funnel_chart,
    create_composed_chart,
    create_sdtm_validation_dashboard,
]


# =============================================================================
# WEB SCRAPING & CRAWLING TOOLS (Firecrawl - Async)
# =============================================================================

@tool
async def scrape_webpage(
    url: str,
    include_markdown: bool = True,
    include_html: bool = False,
    only_main_content: bool = True,
    wait_for: int = 0
) -> Dict[str, Any]:
    """
    Scrape a single webpage and extract its content using Firecrawl.

    Args:
        url: The URL to scrape
        include_markdown: Include markdown format in output (default: True)
        include_html: Include HTML format in output (default: False)
        only_main_content: If True, extract only main content (skip nav, footer, etc.)
        wait_for: Milliseconds to wait for dynamic content to load (0 for static pages)

    Returns:
        Dict with scraped content, metadata, and success status

    Example:
        result = await scrape_webpage("https://clinicaltrials.gov/study/NCT12345678")
    """
    try:
        from firecrawl import FirecrawlApp

        api_key = os.getenv("FIRECRAWL_API_KEY", "fc-4a39356cf081453f96726af430e24ae1")
        app = FirecrawlApp(api_key=api_key)

        # Build format list
        formats = []
        if include_markdown:
            formats.append("markdown")
        if include_html:
            formats.append("html")
        if not formats:
            formats = ["markdown"]

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: app.scrape(
                url,
                formats=formats,
                only_main_content=only_main_content,
                wait_for=wait_for if wait_for > 0 else None
            )
        )

        # Extract content from Document object
        content = {}
        if hasattr(result, 'markdown'):
            content["markdown"] = result.markdown or ""
        if hasattr(result, 'html'):
            content["html"] = result.html or ""

        metadata = {}
        if hasattr(result, 'metadata') and result.metadata:
            metadata = {
                "title": getattr(result.metadata, 'title', '') or '',
                "description": getattr(result.metadata, 'description', '') or '',
                "url": getattr(result.metadata, 'url', url) or url,
            }

        return {
            "success": True,
            "url": url,
            "title": metadata.get("title", ""),
            "description": metadata.get("description", ""),
            "content": content,
            "metadata": metadata,
            "content_length": len(content.get("markdown", "") or content.get("html", "")),
        }

    except ImportError:
        return {"success": False, "error": "Firecrawl not installed. Run: pip install firecrawl-py"}
    except Exception as e:
        return {"success": False, "url": url, "error": str(e)}


@tool
async def crawl_website(
    url: str,
    max_pages: int = 10,
    max_depth: int = 2,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Crawl a website starting from a URL, following links to scrape multiple pages.

    Args:
        url: Starting URL for the crawl
        max_pages: Maximum number of pages to crawl (default: 10)
        max_depth: Maximum link depth from start URL (default: 2)
        include_patterns: URL patterns to include (e.g., ["/docs/*", "/api/*"])
        exclude_patterns: URL patterns to exclude (e.g., ["/login", "/admin/*"])
        output_dir: Optional directory to save crawled content as files

    Returns:
        Dict with crawled pages, content, and statistics

    Example:
        result = await crawl_website(
            "https://cdisc.org/standards/foundational/sdtm",
            max_pages=20,
            include_patterns=["/standards/*"]
        )
    """
    try:
        from firecrawl import FirecrawlApp
        from firecrawl.v2.types import ScrapeOptions

        api_key = os.getenv("FIRECRAWL_API_KEY", "fc-4a39356cf081453f96726af430e24ae1")
        app = FirecrawlApp(api_key=api_key)

        # Build scrape options
        scrape_opts = ScrapeOptions(formats=["markdown"], only_main_content=True)

        # Start crawl (async crawl with polling)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: app.crawl(
                url,
                limit=max_pages,
                max_discovery_depth=max_depth,
                include_paths=include_patterns,
                exclude_paths=exclude_patterns,
                scrape_options=scrape_opts,
                poll_interval=5
            )
        )

        # Process results from CrawlJob
        pages = []
        total_content_length = 0

        # Get data from CrawlJob object
        crawl_data = result.data if hasattr(result, 'data') else []

        for page in crawl_data:
            markdown_content = page.markdown if hasattr(page, 'markdown') else ""
            page_url = ""
            page_title = ""

            if hasattr(page, 'metadata') and page.metadata:
                page_url = getattr(page.metadata, 'url', '') or getattr(page.metadata, 'sourceURL', '')
                page_title = getattr(page.metadata, 'title', '')

            page_info = {
                "url": page_url,
                "title": page_title,
                "content_length": len(markdown_content),
                "markdown": markdown_content[:2000] + "..." if len(markdown_content) > 2000 else markdown_content
            }
            pages.append(page_info)
            total_content_length += len(markdown_content)

        # Save to files if output_dir specified
        saved_files = []
        if output_dir and pages:
            await async_makedirs(output_dir)
            for i, page in enumerate(pages):
                filename = f"page_{i+1}.md"
                filepath = os.path.join(output_dir, filename)
                async with aiofiles.open(filepath, 'w') as f:
                    await f.write(f"# {page['title']}\n\nSource: {page['url']}\n\n---\n\n{page['markdown']}")
                saved_files.append(filepath)

        return {
            "success": True,
            "start_url": url,
            "pages_crawled": len(pages),
            "total_content_length": total_content_length,
            "pages": pages,
            "saved_files": saved_files if saved_files else None,
        }

    except ImportError:
        return {"success": False, "error": "Firecrawl not installed. Run: pip install firecrawl-py"}
    except Exception as e:
        return {"success": False, "url": url, "error": str(e)}


@tool
async def map_website(
    url: str,
    search_query: Optional[str] = None,
    include_subdomains: bool = False,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Map a website to discover all URLs/pages without scraping content.
    Useful for understanding site structure before targeted scraping.

    Args:
        url: Base URL to map
        search_query: Optional search term to filter URLs
        include_subdomains: Whether to include subdomains
        limit: Maximum number of URLs to return

    Returns:
        Dict with discovered URLs and site structure

    Example:
        result = await map_website("https://fda.gov", search_query="clinical trials")
    """
    try:
        from firecrawl import FirecrawlApp

        api_key = os.getenv("FIRECRAWL_API_KEY", "fc-4a39356cf081453f96726af430e24ae1")
        app = FirecrawlApp(api_key=api_key)

        # Run mapping
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: app.map(
                url,
                search=search_query,
                include_subdomains=include_subdomains,
                limit=limit
            )
        )

        # Process URLs from MapData object
        urls = []
        if hasattr(result, 'links'):
            urls = result.links or []
        elif isinstance(result, dict):
            urls = result.get("links", result.get("urls", []))
        elif isinstance(result, list):
            urls = result

        # Categorize URLs by path
        categories = {}
        for u in urls:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(u)
                path_parts = parsed.path.strip("/").split("/")
                category = path_parts[0] if path_parts and path_parts[0] else "root"
                if category not in categories:
                    categories[category] = []
                categories[category].append(u)
            except:
                pass

        return {
            "success": True,
            "base_url": url,
            "total_urls": len(urls),
            "urls": urls[:50],  # Return first 50 in response
            "all_urls_count": len(urls),
            "categories": {k: len(v) for k, v in categories.items()},
            "search_query": search_query,
        }

    except ImportError:
        return {"success": False, "error": "Firecrawl not installed. Run: pip install firecrawl-py"}
    except Exception as e:
        return {"success": False, "url": url, "error": str(e)}


@tool
async def search_and_scrape(
    query: str,
    num_results: int = 5,
    scrape_content: bool = True
) -> Dict[str, Any]:
    """
    Search the web and optionally scrape the content of search results.
    Combines search with scraping for comprehensive research.

    Args:
        query: Search query
        num_results: Number of search results to return
        scrape_content: Whether to scrape full content of each result

    Returns:
        Dict with search results and optionally scraped content

    Example:
        result = await search_and_scrape(
            "CDISC SDTM AE domain specification",
            num_results=3,
            scrape_content=True
        )
    """
    try:
        from firecrawl import FirecrawlApp

        api_key = os.getenv("FIRECRAWL_API_KEY", "fc-4a39356cf081453f96726af430e24ae1")
        app = FirecrawlApp(api_key=api_key)

        # Search
        loop = asyncio.get_event_loop()
        search_result = await loop.run_in_executor(
            None,
            lambda: app.search(query, limit=num_results)
        )

        results = []

        # Process search results from SearchData object
        search_data = []
        if hasattr(search_result, 'data'):
            search_data = search_result.data or []
        elif isinstance(search_result, list):
            search_data = search_result

        for item in search_data:
            # Handle both object and dict formats
            if hasattr(item, 'title'):
                result_item = {
                    "title": item.title or "",
                    "url": item.url or "",
                    "description": (item.description or "")[:500],
                }
            else:
                result_item = {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", item.get("content", ""))[:500],
                }

            # Optionally scrape full content
            if scrape_content and result_item["url"]:
                try:
                    scrape_result = await loop.run_in_executor(
                        None,
                        lambda url=result_item["url"]: app.scrape(
                            url,
                            formats=["markdown"],
                            only_main_content=True
                        )
                    )
                    markdown = scrape_result.markdown if hasattr(scrape_result, 'markdown') else ""
                    result_item["full_content"] = markdown[:5000]
                    result_item["content_length"] = len(markdown)
                except Exception as scrape_error:
                    result_item["scrape_error"] = str(scrape_error)

            results.append(result_item)

        return {
            "success": True,
            "query": query,
            "num_results": len(results),
            "results": results,
        }

    except ImportError:
        return {"success": False, "error": "Firecrawl not installed. Run: pip install firecrawl-py"}
    except Exception as e:
        return {"success": False, "query": query, "error": str(e)}


@tool
async def extract_structured_data(
    url: str,
    extraction_schema: Dict[str, Any],
    prompt: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract structured data from a webpage using AI-powered extraction.
    Define a schema and Firecrawl will extract matching data.

    Args:
        url: URL to extract data from
        extraction_schema: JSON schema defining the data structure to extract
        prompt: Optional prompt to guide extraction

    Returns:
        Dict with extracted structured data

    Example:
        result = await extract_structured_data(
            "https://clinicaltrials.gov/study/NCT12345678",
            extraction_schema={
                "type": "object",
                "properties": {
                    "trial_name": {"type": "string"},
                    "sponsor": {"type": "string"},
                    "phase": {"type": "string"},
                    "conditions": {"type": "array", "items": {"type": "string"}},
                    "enrollment": {"type": "number"}
                }
            },
            prompt="Extract clinical trial information"
        )
    """
    try:
        from firecrawl import FirecrawlApp

        api_key = os.getenv("FIRECRAWL_API_KEY", "fc-4a39356cf081453f96726af430e24ae1")
        app = FirecrawlApp(api_key=api_key)

        # Run extraction using the extract method
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: app.extract(
                urls=[url],
                schema=extraction_schema,
                prompt=prompt
            )
        )

        # Get extracted data from result
        extracted_data = {}
        if hasattr(result, 'data'):
            extracted_data = result.data
        elif isinstance(result, dict):
            extracted_data = result.get("data", result.get("extract", {}))

        metadata = {}
        if hasattr(result, 'metadata'):
            metadata = result.metadata or {}

        return {
            "success": True,
            "url": url,
            "extracted_data": extracted_data,
            "metadata": metadata,
        }

    except ImportError:
        return {"success": False, "error": "Firecrawl not installed. Run: pip install firecrawl-py"}
    except Exception as e:
        return {"success": False, "url": url, "error": str(e)}


# Web scraping tools list
WEB_SCRAPING_TOOLS = [
    scrape_webpage,
    crawl_website,
    map_website,
    search_and_scrape,
    extract_structured_data,
]


# =============================================================================
# EXPORT ALL TOOLS - Combined DeepAgents + SDTM Chat Tools
# =============================================================================

# DeepAgents-specific tools for pipeline orchestration (now async)
DEEPAGENT_TOOLS = [
    # Bash Execution (async)
    execute_bash,
    # Visualization (async) - Frontend-compatible Recharts
    create_bar_chart,
    create_line_chart,
    create_pie_chart,
    create_area_chart,
    create_scatter_chart,
    create_radar_chart,
    create_funnel_chart,
    create_composed_chart,
    create_sdtm_validation_dashboard,
    # Web Scraping & Crawling (Firecrawl - async)
    scrape_webpage,
    crawl_website,
    map_website,
    search_and_scrape,
    extract_structured_data,
    # Data Ingestion (async)
    download_edc_data,
    scan_source_files,
    analyze_source_file,
    # Mapping Generation (async) - Pattern-Based
    generate_mapping_spec,
    save_mapping_spec,
    # Intelligent Mapping (async) - LLM-Based Semantic Mapping
    generate_intelligent_mapping,
    get_sdtm_variable_definitions,
    analyze_source_for_sdtm,
    # Transformation (async) - Basic
    transform_to_sdtm,
    # Mapping Specification-Driven Transformation (async)
    load_mapping_specification,
    transform_domain_with_spec,
    get_domain_mapping_details,
    transform_domain_standalone,
    list_mapping_spec_domains,
    # Reporting (async)
    generate_pipeline_report,
]

# SDTM Chat tools for interactive operations
CHAT_TOOLS = [
    # Data loading
    load_data_from_s3,
    list_available_domains,
    preview_source_file,
    # Conversion (high-level)
    convert_domain,
    validate_domain,
    get_conversion_status,
    # Output/Storage
    upload_sdtm_to_s3,
    load_sdtm_to_neo4j,
    save_sdtm_locally,
    # Knowledge base (Pinecone)
    search_sdtm_guidelines,
    get_business_rules,
    get_mapping_specification,
    get_validation_rules,
    get_sdtm_guidance,
    search_knowledge_base,
    get_controlled_terminology,
    # SDTM-IG 3.4 Web Reference
    fetch_sdtmig_specification,
    fetch_controlled_terminology,
    get_mapping_guidance_from_web,
    # Internet search (Tavily)
    search_internet,
]

# Combined tools for unified agent
SDTM_TOOLS = DEEPAGENT_TOOLS + CHAT_TOOLS

#!/usr/bin/env python3
"""
Pinecone Knowledge Base Setup
=============================
Populates Pinecone vector indexes with SDTM knowledge for the ETL pipeline.

Indexes created:
- sdtmig: SDTM Implementation Guide domain specifications
- sdtmct: CDISC Controlled Terminology codelists
- businessrules: Domain transformation rules
- validationrules: Pinnacle 21 and FDA validation rules
- sdtmmetadata: Variable metadata

Usage:
    python -m sdtm_pipeline.knowledge_base.setup_pinecone

API keys are automatically loaded from .env file in the project root.
"""

import os
import json
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

# Load environment variables from .env file FIRST
from dotenv import load_dotenv

# Find the project root (where .env is located)
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
    print(f"[Pinecone Setup] Loaded environment from {ENV_FILE}")
else:
    # Try current directory
    load_dotenv()
    print("[Pinecone Setup] Loaded environment from current directory")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import required packages
try:
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    logger.warning("Pinecone not installed. Run: pip install pinecone-client")

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not installed. Run: pip install openai")


@dataclass
class KnowledgeDocument:
    """Represents a document to be indexed in Pinecone."""
    id: str
    text: str
    metadata: Dict[str, Any]


class PineconeKnowledgeBase:
    """Sets up and populates Pinecone indexes for SDTM knowledge."""

    # Index configurations
    INDEXES = {
        "sdtmig": {
            "description": "SDTM Implementation Guide domain specifications",
            "dimension": 3072,  # text-embedding-3-large
            "metric": "cosine"
        },
        "sdtmct": {
            "description": "CDISC Controlled Terminology codelists",
            "dimension": 3072,
            "metric": "cosine"
        },
        "businessrules": {
            "description": "Domain transformation business rules",
            "dimension": 3072,
            "metric": "cosine"
        },
        "validationrules": {
            "description": "Pinnacle 21 and FDA validation rules",
            "dimension": 3072,
            "metric": "cosine"
        },
        "sdtmmetadata": {
            "description": "SDTM variable metadata",
            "dimension": 3072,
            "metric": "cosine"
        },
        "derivationrules": {
            "description": "Variable derivation rules with cross-domain dependencies and source patterns",
            "dimension": 3072,
            "metric": "cosine"
        },
        "dta": {
            "description": "Data Transfer Agreement specifications, clauses, and quality requirements",
            "dimension": 3072,
            "metric": "cosine"
        }
    }

    def __init__(self, api_key: Optional[str] = None, openai_key: Optional[str] = None):
        """Initialize with API keys."""
        self.pinecone_key = api_key or os.getenv("PINECONE_API_KEY")
        self.openai_key = openai_key or os.getenv("OPENAI_API_KEY")

        if not self.pinecone_key:
            raise ValueError("PINECONE_API_KEY environment variable required")
        if not self.openai_key:
            raise ValueError("OPENAI_API_KEY environment variable required")

        self.pc = Pinecone(api_key=self.pinecone_key) if PINECONE_AVAILABLE else None
        self.openai = OpenAI(api_key=self.openai_key) if OPENAI_AVAILABLE else None
        self.embedding_model = "text-embedding-3-large"

    def create_indexes(self) -> Dict[str, bool]:
        """Create all required Pinecone indexes."""
        if not self.pc:
            raise RuntimeError("Pinecone client not available")

        results = {}
        existing_indexes = [idx.name for idx in self.pc.list_indexes()]

        for index_name, config in self.INDEXES.items():
            if index_name in existing_indexes:
                logger.info(f"Index '{index_name}' already exists")
                results[index_name] = True
            else:
                logger.info(f"Creating index '{index_name}'...")
                try:
                    self.pc.create_index(
                        name=index_name,
                        dimension=config["dimension"],
                        metric=config["metric"],
                        spec=ServerlessSpec(
                            cloud="aws",
                            region="us-east-1"
                        )
                    )
                    # Wait for index to be ready
                    time.sleep(5)
                    logger.info(f"Index '{index_name}' created successfully")
                    results[index_name] = True
                except Exception as e:
                    logger.error(f"Failed to create index '{index_name}': {e}")
                    results[index_name] = False

        return results

    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI."""
        if not self.openai:
            raise RuntimeError("OpenAI client not available")

        response = self.openai.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding

    def upsert_documents(self, index_name: str, documents: List[KnowledgeDocument],
                         batch_size: int = 100) -> int:
        """Upsert documents to a Pinecone index."""
        if not self.pc:
            raise RuntimeError("Pinecone client not available")

        index = self.pc.Index(index_name)
        total_upserted = 0

        # Process in batches
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            vectors = []

            for doc in batch:
                try:
                    embedding = self.get_embedding(doc.text)

                    # Clean metadata - Pinecone doesn't accept None values
                    clean_metadata = {}
                    for k, v in doc.metadata.items():
                        if v is not None:
                            # Convert lists to strings if needed
                            if isinstance(v, list):
                                clean_metadata[k] = ", ".join(str(item) for item in v)
                            else:
                                clean_metadata[k] = v

                    # Add truncated text
                    clean_metadata["text"] = doc.text[:1000]

                    vectors.append({
                        "id": doc.id,
                        "values": embedding,
                        "metadata": clean_metadata
                    })
                except Exception as e:
                    logger.error(f"Failed to embed document {doc.id}: {e}")
                    continue

            if vectors:
                index.upsert(vectors=vectors)
                total_upserted += len(vectors)
                logger.info(f"Upserted batch {i // batch_size + 1}: {len(vectors)} documents")

            # Rate limiting
            time.sleep(0.5)

        return total_upserted

    def populate_sdtmig_index(self) -> int:
        """Populate the SDTM-IG index with domain specifications."""
        documents = []

        # SDTM-IG 3.4 Domain Specifications
        SDTM_DOMAINS = {
            "DM": {
                "name": "Demographics",
                "class": "Special-Purpose",
                "description": "Demographics domain contains subject-level data that does not change over the course of the study.",
                "structure": "One record per subject",
                "variables": {
                    "required": [
                        {"name": "STUDYID", "label": "Study Identifier", "type": "Char", "role": "Identifier"},
                        {"name": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "role": "Identifier"},
                        {"name": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "role": "Identifier"},
                        {"name": "SUBJID", "label": "Subject Identifier for the Study", "type": "Char", "role": "Topic"},
                        {"name": "RFSTDTC", "label": "Subject Reference Start Date/Time", "type": "Char", "role": "Record Qualifier"},
                        {"name": "RFENDTC", "label": "Subject Reference End Date/Time", "type": "Char", "role": "Record Qualifier"},
                        {"name": "SITEID", "label": "Study Site Identifier", "type": "Char", "role": "Record Qualifier"},
                        {"name": "AGE", "label": "Age", "type": "Num", "role": "Record Qualifier"},
                        {"name": "AGEU", "label": "Age Units", "type": "Char", "role": "Variable Qualifier", "codelist": "AGEU"},
                        {"name": "SEX", "label": "Sex", "type": "Char", "role": "Record Qualifier", "codelist": "SEX"},
                        {"name": "RACE", "label": "Race", "type": "Char", "role": "Record Qualifier", "codelist": "RACE"},
                        {"name": "ETHNIC", "label": "Ethnicity", "type": "Char", "role": "Record Qualifier", "codelist": "ETHNIC"},
                        {"name": "ARMCD", "label": "Planned Arm Code", "type": "Char", "role": "Record Qualifier"},
                        {"name": "ARM", "label": "Description of Planned Arm", "type": "Char", "role": "Synonym Qualifier"},
                        {"name": "COUNTRY", "label": "Country", "type": "Char", "role": "Record Qualifier", "codelist": "COUNTRY"}
                    ],
                    "expected": [
                        {"name": "BRTHDTC", "label": "Date/Time of Birth", "type": "Char", "role": "Record Qualifier"},
                        {"name": "RFXSTDTC", "label": "Date/Time of First Study Treatment", "type": "Char", "role": "Record Qualifier"},
                        {"name": "RFXENDTC", "label": "Date/Time of Last Study Treatment", "type": "Char", "role": "Record Qualifier"},
                        {"name": "RFICDTC", "label": "Date/Time of Informed Consent", "type": "Char", "role": "Record Qualifier"},
                        {"name": "RFPENDTC", "label": "Date/Time of End of Participation", "type": "Char", "role": "Record Qualifier"},
                        {"name": "DTHDTC", "label": "Date/Time of Death", "type": "Char", "role": "Record Qualifier"},
                        {"name": "DTHFL", "label": "Subject Death Flag", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                        {"name": "ACTARMCD", "label": "Actual Arm Code", "type": "Char", "role": "Record Qualifier"},
                        {"name": "ACTARM", "label": "Description of Actual Arm", "type": "Char", "role": "Synonym Qualifier"}
                    ]
                }
            },
            "AE": {
                "name": "Adverse Events",
                "class": "Events",
                "description": "Adverse Events domain captures data describing untoward medical occurrences in subjects.",
                "structure": "One record per adverse event per subject",
                "variables": {
                    "required": [
                        {"name": "STUDYID", "label": "Study Identifier", "type": "Char", "role": "Identifier"},
                        {"name": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "role": "Identifier"},
                        {"name": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "role": "Identifier"},
                        {"name": "AESEQ", "label": "Sequence Number", "type": "Num", "role": "Identifier"},
                        {"name": "AETERM", "label": "Reported Term for the Adverse Event", "type": "Char", "role": "Topic"},
                        {"name": "AEDECOD", "label": "Dictionary-Derived Term", "type": "Char", "role": "Synonym Qualifier"},
                        {"name": "AESTDTC", "label": "Start Date/Time of Adverse Event", "type": "Char", "role": "Timing"}
                    ],
                    "expected": [
                        {"name": "AEBODSYS", "label": "Body System or Organ Class", "type": "Char", "role": "Record Qualifier"},
                        {"name": "AESEV", "label": "Severity/Intensity", "type": "Char", "role": "Record Qualifier", "codelist": "AESEV"},
                        {"name": "AESER", "label": "Serious Event", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                        {"name": "AEACN", "label": "Action Taken with Study Treatment", "type": "Char", "role": "Record Qualifier", "codelist": "ACN"},
                        {"name": "AEREL", "label": "Causality", "type": "Char", "role": "Record Qualifier", "codelist": "REL"},
                        {"name": "AEOUT", "label": "Outcome of Adverse Event", "type": "Char", "role": "Record Qualifier", "codelist": "OUT"},
                        {"name": "AEENDTC", "label": "End Date/Time of Adverse Event", "type": "Char", "role": "Timing"},
                        {"name": "AESDTH", "label": "Results in Death", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                        {"name": "AESHOSP", "label": "Requires or Prolongs Hospitalization", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                        {"name": "AESLIFE", "label": "Is Life Threatening", "type": "Char", "role": "Record Qualifier", "codelist": "NY"}
                    ]
                }
            },
            "VS": {
                "name": "Vital Signs",
                "class": "Findings",
                "description": "Vital Signs domain captures measurements including blood pressure, heart rate, temperature, respiratory rate, and other vital measurements.",
                "structure": "One record per vital sign measurement per time point per subject",
                "variables": {
                    "required": [
                        {"name": "STUDYID", "label": "Study Identifier", "type": "Char", "role": "Identifier"},
                        {"name": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "role": "Identifier"},
                        {"name": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "role": "Identifier"},
                        {"name": "VSSEQ", "label": "Sequence Number", "type": "Num", "role": "Identifier"},
                        {"name": "VSTESTCD", "label": "Vital Signs Test Short Name", "type": "Char", "role": "Topic", "codelist": "VSTESTCD"},
                        {"name": "VSTEST", "label": "Vital Signs Test Name", "type": "Char", "role": "Synonym Qualifier", "codelist": "VSTEST"},
                        {"name": "VSORRES", "label": "Result or Finding in Original Units", "type": "Char", "role": "Result Qualifier"},
                        {"name": "VSORRESU", "label": "Original Units", "type": "Char", "role": "Variable Qualifier", "codelist": "UNIT"}
                    ],
                    "expected": [
                        {"name": "VSSTRESC", "label": "Character Result/Finding in Std Format", "type": "Char", "role": "Result Qualifier"},
                        {"name": "VSSTRESN", "label": "Numeric Result/Finding in Standard Units", "type": "Num", "role": "Result Qualifier"},
                        {"name": "VSSTRESU", "label": "Standard Units", "type": "Char", "role": "Variable Qualifier", "codelist": "UNIT"},
                        {"name": "VSSTAT", "label": "Completion Status", "type": "Char", "role": "Record Qualifier", "codelist": "ND"},
                        {"name": "VSDTC", "label": "Date/Time of Measurements", "type": "Char", "role": "Timing"},
                        {"name": "VSDY", "label": "Study Day of Vital Signs", "type": "Num", "role": "Timing"},
                        {"name": "VISITNUM", "label": "Visit Number", "type": "Num", "role": "Timing"},
                        {"name": "VISIT", "label": "Visit Name", "type": "Char", "role": "Timing"},
                        {"name": "VSPOS", "label": "Vital Signs Position of Subject", "type": "Char", "role": "Record Qualifier", "codelist": "POSITION"},
                        {"name": "VSLOC", "label": "Location of Vital Signs Measurement", "type": "Char", "role": "Record Qualifier", "codelist": "LOC"}
                    ]
                }
            },
            "LB": {
                "name": "Laboratory",
                "class": "Findings",
                "description": "Laboratory domain captures laboratory test results for samples collected from subjects.",
                "structure": "One record per lab test per time point per subject",
                "variables": {
                    "required": [
                        {"name": "STUDYID", "label": "Study Identifier", "type": "Char", "role": "Identifier"},
                        {"name": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "role": "Identifier"},
                        {"name": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "role": "Identifier"},
                        {"name": "LBSEQ", "label": "Sequence Number", "type": "Num", "role": "Identifier"},
                        {"name": "LBTESTCD", "label": "Lab Test or Examination Short Name", "type": "Char", "role": "Topic", "codelist": "LBTESTCD"},
                        {"name": "LBTEST", "label": "Lab Test or Examination Name", "type": "Char", "role": "Synonym Qualifier", "codelist": "LBTEST"},
                        {"name": "LBORRES", "label": "Result or Finding in Original Units", "type": "Char", "role": "Result Qualifier"},
                        {"name": "LBORRESU", "label": "Original Units", "type": "Char", "role": "Variable Qualifier", "codelist": "UNIT"}
                    ],
                    "expected": [
                        {"name": "LBCAT", "label": "Category for Lab Test", "type": "Char", "role": "Grouping Qualifier"},
                        {"name": "LBSTRESC", "label": "Character Result/Finding in Std Format", "type": "Char", "role": "Result Qualifier"},
                        {"name": "LBSTRESN", "label": "Numeric Result/Finding in Standard Units", "type": "Num", "role": "Result Qualifier"},
                        {"name": "LBSTRESU", "label": "Standard Units", "type": "Char", "role": "Variable Qualifier", "codelist": "UNIT"},
                        {"name": "LBSTNRLO", "label": "Reference Range Lower Limit-Std Units", "type": "Num", "role": "Variable Qualifier"},
                        {"name": "LBSTNRHI", "label": "Reference Range Upper Limit-Std Units", "type": "Num", "role": "Variable Qualifier"},
                        {"name": "LBNRIND", "label": "Reference Range Indicator", "type": "Char", "role": "Variable Qualifier", "codelist": "NRIND"},
                        {"name": "LBSPEC", "label": "Specimen Type", "type": "Char", "role": "Record Qualifier", "codelist": "SPECTYPE"},
                        {"name": "LBDTC", "label": "Date/Time of Specimen Collection", "type": "Char", "role": "Timing"},
                        {"name": "LBDY", "label": "Study Day of Specimen Collection", "type": "Num", "role": "Timing"}
                    ]
                }
            },
            "CM": {
                "name": "Concomitant Medications",
                "class": "Interventions",
                "description": "Concomitant Medications captures medications taken by the subject during the study other than study treatment.",
                "structure": "One record per medication per subject",
                "variables": {
                    "required": [
                        {"name": "STUDYID", "label": "Study Identifier", "type": "Char", "role": "Identifier"},
                        {"name": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "role": "Identifier"},
                        {"name": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "role": "Identifier"},
                        {"name": "CMSEQ", "label": "Sequence Number", "type": "Num", "role": "Identifier"},
                        {"name": "CMTRT", "label": "Reported Name of Drug, Med, or Therapy", "type": "Char", "role": "Topic"}
                    ],
                    "expected": [
                        {"name": "CMDECOD", "label": "Standardized Medication Name", "type": "Char", "role": "Synonym Qualifier"},
                        {"name": "CMCAT", "label": "Category for Medication", "type": "Char", "role": "Grouping Qualifier"},
                        {"name": "CMINDC", "label": "Indication", "type": "Char", "role": "Record Qualifier"},
                        {"name": "CMDOSE", "label": "Dose per Administration", "type": "Num", "role": "Record Qualifier"},
                        {"name": "CMDOSU", "label": "Dose Units", "type": "Char", "role": "Variable Qualifier", "codelist": "UNIT"},
                        {"name": "CMDOSFRQ", "label": "Dosing Frequency per Interval", "type": "Char", "role": "Variable Qualifier", "codelist": "FREQ"},
                        {"name": "CMROUTE", "label": "Route of Administration", "type": "Char", "role": "Variable Qualifier", "codelist": "ROUTE"},
                        {"name": "CMSTDTC", "label": "Start Date/Time of Medication", "type": "Char", "role": "Timing"},
                        {"name": "CMENDTC", "label": "End Date/Time of Medication", "type": "Char", "role": "Timing"},
                        {"name": "CMONGO", "label": "Concomitant Meds Ongoing", "type": "Char", "role": "Record Qualifier", "codelist": "NY"}
                    ]
                }
            },
            "EX": {
                "name": "Exposure",
                "class": "Interventions",
                "description": "Exposure domain captures study treatment administrations, including dose, dose form, and route.",
                "structure": "One record per constant-dosing interval per subject",
                "variables": {
                    "required": [
                        {"name": "STUDYID", "label": "Study Identifier", "type": "Char", "role": "Identifier"},
                        {"name": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "role": "Identifier"},
                        {"name": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "role": "Identifier"},
                        {"name": "EXSEQ", "label": "Sequence Number", "type": "Num", "role": "Identifier"},
                        {"name": "EXTRT", "label": "Name of Actual Treatment", "type": "Char", "role": "Topic"}
                    ],
                    "expected": [
                        {"name": "EXDOSE", "label": "Dose per Administration", "type": "Num", "role": "Record Qualifier"},
                        {"name": "EXDOSU", "label": "Dose Units", "type": "Char", "role": "Variable Qualifier", "codelist": "UNIT"},
                        {"name": "EXDOSFRM", "label": "Dose Form", "type": "Char", "role": "Variable Qualifier", "codelist": "FRM"},
                        {"name": "EXDOSFRQ", "label": "Dosing Frequency per Interval", "type": "Char", "role": "Variable Qualifier", "codelist": "FREQ"},
                        {"name": "EXROUTE", "label": "Route of Administration", "type": "Char", "role": "Variable Qualifier", "codelist": "ROUTE"},
                        {"name": "EXSTDTC", "label": "Start Date/Time of Treatment", "type": "Char", "role": "Timing"},
                        {"name": "EXENDTC", "label": "End Date/Time of Treatment", "type": "Char", "role": "Timing"},
                        {"name": "EXSTDY", "label": "Study Day of Start of Treatment", "type": "Num", "role": "Timing"},
                        {"name": "EXENDY", "label": "Study Day of End of Treatment", "type": "Num", "role": "Timing"}
                    ]
                }
            },
            "MH": {
                "name": "Medical History",
                "class": "Events",
                "description": "Medical History domain captures subject's prior medical history and conditions.",
                "structure": "One record per medical history event per subject",
                "variables": {
                    "required": [
                        {"name": "STUDYID", "label": "Study Identifier", "type": "Char", "role": "Identifier"},
                        {"name": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "role": "Identifier"},
                        {"name": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "role": "Identifier"},
                        {"name": "MHSEQ", "label": "Sequence Number", "type": "Num", "role": "Identifier"},
                        {"name": "MHTERM", "label": "Reported Term for the Medical History", "type": "Char", "role": "Topic"}
                    ],
                    "expected": [
                        {"name": "MHDECOD", "label": "Dictionary-Derived Term", "type": "Char", "role": "Synonym Qualifier"},
                        {"name": "MHCAT", "label": "Category for Medical History", "type": "Char", "role": "Grouping Qualifier"},
                        {"name": "MHBODSYS", "label": "Body System or Organ Class", "type": "Char", "role": "Record Qualifier"},
                        {"name": "MHSTDTC", "label": "Start Date/Time of Medical History Event", "type": "Char", "role": "Timing"},
                        {"name": "MHENDTC", "label": "End Date/Time of Medical History Event", "type": "Char", "role": "Timing"},
                        {"name": "MHENRF", "label": "End Relative to Reference Period", "type": "Char", "role": "Timing", "codelist": "STENRF"},
                        {"name": "MHONGO", "label": "Medical History Event Ongoing", "type": "Char", "role": "Record Qualifier", "codelist": "NY"}
                    ]
                }
            },
            "DS": {
                "name": "Disposition",
                "class": "Events",
                "description": "Disposition domain captures subject disposition including study completion and discontinuation reasons.",
                "structure": "One record per disposition event per subject",
                "variables": {
                    "required": [
                        {"name": "STUDYID", "label": "Study Identifier", "type": "Char", "role": "Identifier"},
                        {"name": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "role": "Identifier"},
                        {"name": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "role": "Identifier"},
                        {"name": "DSSEQ", "label": "Sequence Number", "type": "Num", "role": "Identifier"},
                        {"name": "DSTERM", "label": "Reported Term for the Disposition Event", "type": "Char", "role": "Topic"},
                        {"name": "DSDECOD", "label": "Standardized Disposition Term", "type": "Char", "role": "Synonym Qualifier", "codelist": "NCOMPLT"}
                    ],
                    "expected": [
                        {"name": "DSCAT", "label": "Category for Disposition Event", "type": "Char", "role": "Grouping Qualifier"},
                        {"name": "DSSCAT", "label": "Subcategory for Disposition Event", "type": "Char", "role": "Grouping Qualifier"},
                        {"name": "DSSTDTC", "label": "Start Date/Time of Disposition Event", "type": "Char", "role": "Timing"},
                        {"name": "EPOCH", "label": "Epoch", "type": "Char", "role": "Timing"}
                    ]
                }
            }
        }

        # Create documents for each domain
        for domain_code, domain_info in SDTM_DOMAINS.items():
            # Main domain document
            domain_text = f"""
            SDTM Domain: {domain_code} - {domain_info['name']}
            Class: {domain_info['class']}
            Description: {domain_info['description']}
            Structure: {domain_info['structure']}

            Required Variables: {', '.join([v['name'] for v in domain_info['variables'].get('required', [])])}
            Expected Variables: {', '.join([v['name'] for v in domain_info['variables'].get('expected', [])])}
            """

            documents.append(KnowledgeDocument(
                id=f"sdtmig-{domain_code}-overview",
                text=domain_text.strip(),
                metadata={
                    "domain": domain_code,
                    "domain_name": domain_info['name'],
                    "domain_class": domain_info['class'],
                    "type": "domain_overview"
                }
            ))

            # Individual variable documents
            for var_type in ['required', 'expected']:
                for var in domain_info['variables'].get(var_type, []):
                    var_text = f"""
                    SDTM Variable: {var['name']}
                    Domain: {domain_code}
                    Label: {var['label']}
                    Type: {var['type']}
                    Role: {var['role']}
                    Core: {var_type.capitalize()}
                    Codelist: {var.get('codelist', 'N/A')}

                    The {var['name']} variable in the {domain_code} domain represents {var['label'].lower()}.
                    It is a {var_type} variable of type {var['type']} with role {var['role']}.
                    """

                    documents.append(KnowledgeDocument(
                        id=f"sdtmig-{domain_code}-{var['name']}",
                        text=var_text.strip(),
                        metadata={
                            "domain": domain_code,
                            "variable": var['name'],
                            "label": var['label'],
                            "type": var['type'],
                            "role": var['role'],
                            "core": var_type,
                            "codelist": var.get('codelist'),
                            "doc_type": "variable_specification"
                        }
                    ))

        logger.info(f"Prepared {len(documents)} SDTM-IG documents")
        return self.upsert_documents("sdtmig", documents)

    def populate_controlled_terminology_index(self) -> int:
        """Populate the controlled terminology index."""
        documents = []

        # CDISC Controlled Terminology
        CONTROLLED_TERMINOLOGY = {
            "SEX": {
                "name": "Sex",
                "extensible": False,
                "terms": [
                    {"code": "F", "decode": "FEMALE", "definition": "A person who belongs to the sex that normally produces ova"},
                    {"code": "M", "decode": "MALE", "definition": "A person who belongs to the sex that normally produces sperm"},
                    {"code": "U", "decode": "UNKNOWN", "definition": "Not known, not observed, not recorded, or refused"},
                    {"code": "UNDIFFERENTIATED", "decode": "UNDIFFERENTIATED", "definition": "Genitalia are not clearly defined as either male or female"}
                ]
            },
            "RACE": {
                "name": "Race",
                "extensible": True,
                "terms": [
                    {"code": "AMERICAN INDIAN OR ALASKA NATIVE", "decode": "AMERICAN INDIAN OR ALASKA NATIVE", "definition": "A person having origins in any of the original peoples of North, Central, or South America"},
                    {"code": "ASIAN", "decode": "ASIAN", "definition": "A person having origins in any of the original peoples of the Far East, Southeast Asia, or the Indian subcontinent"},
                    {"code": "BLACK OR AFRICAN AMERICAN", "decode": "BLACK OR AFRICAN AMERICAN", "definition": "A person having origins in any of the black racial groups of Africa"},
                    {"code": "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER", "decode": "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER", "definition": "A person having origins in any of the original peoples of Hawaii, Guam, Samoa, or other Pacific Islands"},
                    {"code": "WHITE", "decode": "WHITE", "definition": "A person having origins in any of the original peoples of Europe, the Middle East, or North Africa"},
                    {"code": "MULTIPLE", "decode": "MULTIPLE", "definition": "A person identifying with more than one race"},
                    {"code": "OTHER", "decode": "OTHER", "definition": "A person identifying with a race not listed"},
                    {"code": "UNKNOWN", "decode": "UNKNOWN", "definition": "Not known or not recorded"}
                ]
            },
            "ETHNIC": {
                "name": "Ethnicity",
                "extensible": False,
                "terms": [
                    {"code": "HISPANIC OR LATINO", "decode": "HISPANIC OR LATINO", "definition": "A person of Mexican, Puerto Rican, Cuban, Central or South American, or other Spanish culture or origin"},
                    {"code": "NOT HISPANIC OR LATINO", "decode": "NOT HISPANIC OR LATINO", "definition": "A person not of Hispanic or Latino origin"},
                    {"code": "NOT REPORTED", "decode": "NOT REPORTED", "definition": "Subject did not report ethnicity"},
                    {"code": "UNKNOWN", "decode": "UNKNOWN", "definition": "Not known or not recorded"}
                ]
            },
            "NY": {
                "name": "No Yes Response",
                "extensible": False,
                "terms": [
                    {"code": "N", "decode": "NO", "definition": "Specifies that something is not the case or is not so"},
                    {"code": "Y", "decode": "YES", "definition": "Specifies that something is the case or is so"}
                ]
            },
            "AESEV": {
                "name": "Severity/Intensity Scale for Adverse Events",
                "extensible": False,
                "terms": [
                    {"code": "MILD", "decode": "MILD", "definition": "Awareness of sign or symptom, but easily tolerated"},
                    {"code": "MODERATE", "decode": "MODERATE", "definition": "Discomfort sufficient to cause interference with normal activities"},
                    {"code": "SEVERE", "decode": "SEVERE", "definition": "Incapacitating with inability to perform normal activities"}
                ]
            },
            "REL": {
                "name": "Relationship to Treatment",
                "extensible": True,
                "terms": [
                    {"code": "NOT RELATED", "decode": "NOT RELATED", "definition": "There is no relationship to the study treatment"},
                    {"code": "UNLIKELY RELATED", "decode": "UNLIKELY RELATED", "definition": "It is unlikely there is a relationship to the study treatment"},
                    {"code": "POSSIBLY RELATED", "decode": "POSSIBLY RELATED", "definition": "There is a possibility of a relationship to the study treatment"},
                    {"code": "PROBABLY RELATED", "decode": "PROBABLY RELATED", "definition": "There is probably a relationship to the study treatment"},
                    {"code": "DEFINITELY RELATED", "decode": "DEFINITELY RELATED", "definition": "There is definitely a relationship to the study treatment"}
                ]
            },
            "OUT": {
                "name": "Outcome of Event",
                "extensible": False,
                "terms": [
                    {"code": "RECOVERED/RESOLVED", "decode": "RECOVERED/RESOLVED", "definition": "The subject has fully recovered or the event has resolved"},
                    {"code": "RECOVERING/RESOLVING", "decode": "RECOVERING/RESOLVING", "definition": "The subject is recovering or the event is resolving"},
                    {"code": "NOT RECOVERED/NOT RESOLVED", "decode": "NOT RECOVERED/NOT RESOLVED", "definition": "The subject has not recovered or the event has not resolved"},
                    {"code": "RECOVERED/RESOLVED WITH SEQUELAE", "decode": "RECOVERED/RESOLVED WITH SEQUELAE", "definition": "The subject has recovered or the event has resolved but with lasting effects"},
                    {"code": "FATAL", "decode": "FATAL", "definition": "The event resulted in death"},
                    {"code": "UNKNOWN", "decode": "UNKNOWN", "definition": "Outcome is unknown"}
                ]
            },
            "ACN": {
                "name": "Action Taken with Study Treatment",
                "extensible": True,
                "terms": [
                    {"code": "DOSE NOT CHANGED", "decode": "DOSE NOT CHANGED", "definition": "The dose of study treatment was not changed"},
                    {"code": "DOSE REDUCED", "decode": "DOSE REDUCED", "definition": "The dose of study treatment was reduced"},
                    {"code": "DRUG INTERRUPTED", "decode": "DRUG INTERRUPTED", "definition": "Study treatment was temporarily stopped"},
                    {"code": "DRUG WITHDRAWN", "decode": "DRUG WITHDRAWN", "definition": "Study treatment was permanently discontinued"},
                    {"code": "NOT APPLICABLE", "decode": "NOT APPLICABLE", "definition": "Action taken is not applicable"}
                ]
            },
            "NRIND": {
                "name": "Reference Range Indicator",
                "extensible": False,
                "terms": [
                    {"code": "NORMAL", "decode": "NORMAL", "definition": "Value is within normal reference range"},
                    {"code": "ABNORMAL", "decode": "ABNORMAL", "definition": "Value is outside normal reference range"},
                    {"code": "LOW", "decode": "LOW", "definition": "Value is below the lower limit of normal"},
                    {"code": "HIGH", "decode": "HIGH", "definition": "Value is above the upper limit of normal"}
                ]
            },
            "AGEU": {
                "name": "Age Unit",
                "extensible": False,
                "terms": [
                    {"code": "YEARS", "decode": "YEARS", "definition": "Age measured in years"},
                    {"code": "MONTHS", "decode": "MONTHS", "definition": "Age measured in months"},
                    {"code": "WEEKS", "decode": "WEEKS", "definition": "Age measured in weeks"},
                    {"code": "DAYS", "decode": "DAYS", "definition": "Age measured in days"},
                    {"code": "HOURS", "decode": "HOURS", "definition": "Age measured in hours"}
                ]
            },
            "POSITION": {
                "name": "Position",
                "extensible": True,
                "terms": [
                    {"code": "STANDING", "decode": "STANDING", "definition": "Subject in standing position"},
                    {"code": "SITTING", "decode": "SITTING", "definition": "Subject in sitting position"},
                    {"code": "SUPINE", "decode": "SUPINE", "definition": "Subject lying face up"},
                    {"code": "PRONE", "decode": "PRONE", "definition": "Subject lying face down"}
                ]
            }
        }

        for codelist_code, codelist_info in CONTROLLED_TERMINOLOGY.items():
            # Main codelist document
            terms_text = "\n".join([f"- {t['code']}: {t['decode']} - {t['definition']}" for t in codelist_info['terms']])
            codelist_text = f"""
            CDISC Controlled Terminology Codelist: {codelist_code}
            Name: {codelist_info['name']}
            Extensible: {'Yes' if codelist_info['extensible'] else 'No'}

            Valid Terms:
            {terms_text}

            This codelist is used in SDTM for {codelist_info['name'].lower()} values.
            """

            documents.append(KnowledgeDocument(
                id=f"sdtmct-{codelist_code}",
                text=codelist_text.strip(),
                metadata={
                    "codelist": codelist_code,
                    "name": codelist_info['name'],
                    "extensible": codelist_info['extensible'],
                    "terms": [t['code'] for t in codelist_info['terms']],
                    "type": "controlled_terminology"
                }
            ))

            # Individual term documents
            for term in codelist_info['terms']:
                term_text = f"""
                CDISC Controlled Terminology Term
                Codelist: {codelist_code} ({codelist_info['name']})
                Code: {term['code']}
                Decode: {term['decode']}
                Definition: {term['definition']}

                The term "{term['code']}" in the {codelist_code} codelist means {term['definition'].lower()}.
                """

                documents.append(KnowledgeDocument(
                    id=f"sdtmct-{codelist_code}-{term['code'].replace(' ', '_')}",
                    text=term_text.strip(),
                    metadata={
                        "codelist": codelist_code,
                        "code": term['code'],
                        "decode": term['decode'],
                        "type": "ct_term"
                    }
                ))

        logger.info(f"Prepared {len(documents)} controlled terminology documents")
        return self.upsert_documents("sdtmct", documents)

    def populate_validation_rules_index(self) -> int:
        """Populate validation rules index with Pinnacle 21 and FDA rules."""
        documents = []

        # Pinnacle 21 / FDA Validation Rules
        VALIDATION_RULES = [
            # DM Domain Rules
            {"rule_id": "SD0028", "domain": "DM", "severity": "error", "message": "RFSTDTC must be populated for all subjects", "check": "RFSTDTC not null"},
            {"rule_id": "SD0029", "domain": "DM", "severity": "error", "message": "RFENDTC must be on or after RFSTDTC", "check": "RFENDTC >= RFSTDTC"},
            {"rule_id": "SD0030", "domain": "DM", "severity": "error", "message": "AGE must be non-negative", "check": "AGE >= 0"},
            {"rule_id": "SD0031", "domain": "DM", "severity": "error", "message": "SEX must use CDISC controlled terminology", "check": "SEX in ('M', 'F', 'U', 'UNDIFFERENTIATED')"},
            {"rule_id": "SD0032", "domain": "DM", "severity": "warning", "message": "ETHNIC should be populated", "check": "ETHNIC not null"},
            {"rule_id": "SD0033", "domain": "DM", "severity": "error", "message": "COUNTRY must be a valid ISO 3166-1 alpha-3 code", "check": "COUNTRY matches ISO standard"},
            {"rule_id": "SD0034", "domain": "DM", "severity": "error", "message": "USUBJID must be unique across all subjects", "check": "USUBJID is unique"},
            {"rule_id": "SD0035", "domain": "DM", "severity": "warning", "message": "BRTHDTC should be populated for age calculation verification", "check": "BRTHDTC not null"},

            # AE Domain Rules
            {"rule_id": "SD0060", "domain": "AE", "severity": "error", "message": "AETERM must be populated for all adverse events", "check": "AETERM not null"},
            {"rule_id": "SD0061", "domain": "AE", "severity": "error", "message": "AESTDTC must be populated", "check": "AESTDTC not null"},
            {"rule_id": "SD0062", "domain": "AE", "severity": "error", "message": "AEENDTC must be on or after AESTDTC", "check": "AEENDTC >= AESTDTC"},
            {"rule_id": "SD0063", "domain": "AE", "severity": "error", "message": "AESEV must use CDISC controlled terminology", "check": "AESEV in ('MILD', 'MODERATE', 'SEVERE')"},
            {"rule_id": "SD0064", "domain": "AE", "severity": "error", "message": "AESER must use NY codelist", "check": "AESER in ('Y', 'N')"},
            {"rule_id": "SD0065", "domain": "AE", "severity": "warning", "message": "AEDECOD should be populated for MedDRA coding", "check": "AEDECOD not null"},
            {"rule_id": "SD0066", "domain": "AE", "severity": "error", "message": "If AESER=Y, at least one SAE criterion must be Y", "check": "AESER=Y implies AESDTH or AESHOSP or AESLIFE = Y"},
            {"rule_id": "SD0067", "domain": "AE", "severity": "error", "message": "AESEQ must be unique per subject", "check": "AESEQ unique within USUBJID"},

            # VS Domain Rules
            {"rule_id": "SD0080", "domain": "VS", "severity": "error", "message": "VSTESTCD must use CDISC controlled terminology", "check": "VSTESTCD in standard codelist"},
            {"rule_id": "SD0081", "domain": "VS", "severity": "error", "message": "VSORRES or VSSTAT must be populated", "check": "VSORRES or VSSTAT not null"},
            {"rule_id": "SD0082", "domain": "VS", "severity": "error", "message": "VSORRESU must be populated when VSORRES is numeric", "check": "numeric VSORRES implies VSORRESU not null"},
            {"rule_id": "SD0083", "domain": "VS", "severity": "warning", "message": "VSSTRESN should be populated for numeric results", "check": "VSSTRESN populated for numeric values"},
            {"rule_id": "SD0084", "domain": "VS", "severity": "error", "message": "VSDTC must be in ISO 8601 format", "check": "VSDTC matches YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS"},

            # LB Domain Rules
            {"rule_id": "SD0090", "domain": "LB", "severity": "error", "message": "LBTESTCD must use CDISC controlled terminology", "check": "LBTESTCD in standard codelist"},
            {"rule_id": "SD0091", "domain": "LB", "severity": "error", "message": "LBORRES or LBSTAT must be populated", "check": "LBORRES or LBSTAT not null"},
            {"rule_id": "SD0092", "domain": "LB", "severity": "warning", "message": "Reference range variables should be populated", "check": "LBSTNRLO and LBSTNRHI populated"},
            {"rule_id": "SD0093", "domain": "LB", "severity": "error", "message": "LBNRIND must be consistent with reference ranges", "check": "LBNRIND matches LBSTRESN vs ranges"},

            # Cross-Domain Rules
            {"rule_id": "SD0100", "domain": "ALL", "severity": "error", "message": "STUDYID must be consistent across all domains", "check": "STUDYID same in all domains"},
            {"rule_id": "SD0101", "domain": "ALL", "severity": "error", "message": "USUBJID must exist in DM domain", "check": "All USUBJIDs present in DM"},
            {"rule_id": "SD0102", "domain": "ALL", "severity": "error", "message": "All --DTC variables must be in ISO 8601 format", "check": "--DTC matches ISO 8601"},
            {"rule_id": "SD0103", "domain": "ALL", "severity": "error", "message": "Sequence variables must be unique within subject", "check": "--SEQ unique per USUBJID"},
            {"rule_id": "SD0104", "domain": "ALL", "severity": "warning", "message": "VISITNUM should be numeric and correspond to VISIT", "check": "VISITNUM is numeric"},
        ]

        for rule in VALIDATION_RULES:
            rule_text = f"""
            SDTM Validation Rule: {rule['rule_id']}
            Domain: {rule['domain']}
            Severity: {rule['severity'].upper()}
            Message: {rule['message']}
            Check: {rule['check']}

            This is a {rule['severity']} level validation rule for the {rule['domain']} domain.
            The rule checks that: {rule['message']}
            Technical check: {rule['check']}
            """

            documents.append(KnowledgeDocument(
                id=f"valrule-{rule['rule_id']}",
                text=rule_text.strip(),
                metadata={
                    "rule_id": rule['rule_id'],
                    "domain": rule['domain'],
                    "severity": rule['severity'],
                    "message": rule['message'],
                    "check": rule['check'],
                    "type": "validation_rule"
                }
            ))

        logger.info(f"Prepared {len(documents)} validation rule documents")
        return self.upsert_documents("validationrules", documents)

    def populate_business_rules_index(self) -> int:
        """Populate business rules index with transformation rules."""
        documents = []

        # Business Rules for SDTM Transformations
        BUSINESS_RULES = [
            # DM Domain Rules
            {
                "rule_id": "BR-DM-001",
                "domain": "DM",
                "variable": "USUBJID",
                "rule": "USUBJID = STUDYID + '-' + SITEID + '-' + SUBJID",
                "description": "Generate unique subject identifier by concatenating study, site, and subject IDs"
            },
            {
                "rule_id": "BR-DM-002",
                "domain": "DM",
                "variable": "AGE",
                "rule": "AGE = FLOOR((RFSTDTC - BRTHDTC) / 365.25)",
                "description": "Calculate age in years from birth date and reference start date"
            },
            {
                "rule_id": "BR-DM-003",
                "domain": "DM",
                "variable": "SEX",
                "rule": "Map source gender values to CDISC CT: MALE/M -> M, FEMALE/F -> F, else U",
                "description": "Convert gender values to CDISC controlled terminology for SEX"
            },
            {
                "rule_id": "BR-DM-004",
                "domain": "DM",
                "variable": "RACE",
                "rule": "Map source race values to CDISC CT race codelist",
                "description": "Standardize race values using CDISC controlled terminology"
            },
            {
                "rule_id": "BR-DM-005",
                "domain": "DM",
                "variable": "ETHNIC",
                "rule": "Default to 'NOT HISPANIC OR LATINO' if not Hispanic indicator in source",
                "description": "Derive ethnicity based on Hispanic/Latino indicators"
            },

            # AE Domain Rules
            {
                "rule_id": "BR-AE-001",
                "domain": "AE",
                "variable": "AESEQ",
                "rule": "AESEQ = Row number within subject ordered by AESTDTC",
                "description": "Generate sequence number per subject ordered by start date"
            },
            {
                "rule_id": "BR-AE-002",
                "domain": "AE",
                "variable": "AEDECOD",
                "rule": "AEDECOD = MedDRA Preferred Term from dictionary coding",
                "description": "Populate with MedDRA preferred term from dictionary-coded value"
            },
            {
                "rule_id": "BR-AE-003",
                "domain": "AE",
                "variable": "AESEV",
                "rule": "Map: 1/MILD -> MILD, 2/MODERATE -> MODERATE, 3/SEVERE -> SEVERE",
                "description": "Convert numeric or text severity to CDISC controlled terminology"
            },
            {
                "rule_id": "BR-AE-004",
                "domain": "AE",
                "variable": "AESER",
                "rule": "AESER = 'Y' if any SAE criterion is Yes, else 'N'",
                "description": "Derive serious event flag from SAE criteria variables"
            },
            {
                "rule_id": "BR-AE-005",
                "domain": "AE",
                "variable": "AESTDY",
                "rule": "AESTDY = AESTDTC - RFSTDTC + 1 (if >= 0), else AESTDTC - RFSTDTC",
                "description": "Calculate study day using day 1 convention (no day 0)"
            },

            # VS Domain Rules
            {
                "rule_id": "BR-VS-001",
                "domain": "VS",
                "variable": "VSSEQ",
                "rule": "VSSEQ = Row number within subject ordered by VSDTC, VSTESTCD",
                "description": "Generate sequence number per subject ordered by date and test"
            },
            {
                "rule_id": "BR-VS-002",
                "domain": "VS",
                "variable": "VSTESTCD",
                "rule": "Map source test names to CDISC VSTESTCD codelist",
                "description": "Standardize test codes using CDISC controlled terminology"
            },
            {
                "rule_id": "BR-VS-003",
                "domain": "VS",
                "variable": "VSSTRESN",
                "rule": "VSSTRESN = Numeric conversion of VSORRES with unit standardization",
                "description": "Convert original result to numeric standard units"
            },
            {
                "rule_id": "BR-VS-004",
                "domain": "VS",
                "variable": "VSSTRESU",
                "rule": "VSSTRESU = Standard unit based on VSTESTCD (e.g., mmHg for BP, beats/min for HR)",
                "description": "Assign standard unit based on test code"
            },

            # LB Domain Rules
            {
                "rule_id": "BR-LB-001",
                "domain": "LB",
                "variable": "LBSEQ",
                "rule": "LBSEQ = Row number within subject ordered by LBDTC, LBTESTCD",
                "description": "Generate sequence number per subject ordered by date and test"
            },
            {
                "rule_id": "BR-LB-002",
                "domain": "LB",
                "variable": "LBNRIND",
                "rule": "LBNRIND = 'LOW' if LBSTRESN < LBSTNRLO, 'HIGH' if LBSTRESN > LBSTNRHI, else 'NORMAL'",
                "description": "Derive reference range indicator from result and ranges"
            },
            {
                "rule_id": "BR-LB-003",
                "domain": "LB",
                "variable": "LBCAT",
                "rule": "LBCAT based on specimen type: CHEMISTRY, HEMATOLOGY, URINALYSIS",
                "description": "Assign lab category based on specimen type or test panel"
            },

            # Date Handling Rules
            {
                "rule_id": "BR-DATE-001",
                "domain": "ALL",
                "variable": "--DTC",
                "rule": "Convert all dates to ISO 8601 format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS",
                "description": "Standardize all date/time variables to ISO 8601 format"
            },
            {
                "rule_id": "BR-DATE-002",
                "domain": "ALL",
                "variable": "--DY",
                "rule": "--DY = --DTC - RFSTDTC + 1 if --DTC >= RFSTDTC, else --DTC - RFSTDTC",
                "description": "Calculate study day with no day 0 convention"
            },
            {
                "rule_id": "BR-DATE-003",
                "domain": "ALL",
                "variable": "--DTC",
                "rule": "Partial dates: Use format YYYY-MM or YYYY if day/month unknown",
                "description": "Handle partial dates according to SDTM conventions"
            },
        ]

        for rule in BUSINESS_RULES:
            rule_text = f"""
            SDTM Business Rule: {rule['rule_id']}
            Domain: {rule['domain']}
            Variable: {rule['variable']}
            Rule: {rule['rule']}
            Description: {rule['description']}

            This business rule defines how to derive or transform the {rule['variable']} variable
            in the {rule['domain']} domain. {rule['description']}

            Implementation: {rule['rule']}
            """

            documents.append(KnowledgeDocument(
                id=f"busrule-{rule['rule_id']}",
                text=rule_text.strip(),
                metadata={
                    "rule_id": rule['rule_id'],
                    "domain": rule['domain'],
                    "variable": rule['variable'],
                    "rule": rule['rule'],
                    "description": rule['description'],
                    "type": "business_rule"
                }
            ))

        logger.info(f"Prepared {len(documents)} business rule documents")
        return self.upsert_documents("businessrules", documents)

    def populate_derivation_rules_index(self) -> int:
        """Populate derivation rules index with comprehensive variable derivation logic."""
        documents = []

        # Import derivation rules
        try:
            from .derivation_rules import DERIVATION_RULES, CROSS_DOMAIN_DEPENDENCIES, SOURCE_COLUMN_PATTERNS
        except ImportError:
            from sdtm_pipeline.knowledge_base.derivation_rules import (
                DERIVATION_RULES, CROSS_DOMAIN_DEPENDENCIES, SOURCE_COLUMN_PATTERNS
            )

        # Create documents for each variable's derivation rule
        for domain, variables in DERIVATION_RULES.items():
            for var_name, rule in variables.items():
                # Build comprehensive text for semantic search
                cross_domain_text = ""
                if rule.get("cross_domain_sources"):
                    sources = rule["cross_domain_sources"]
                    cross_domain_text = "Cross-domain sources: " + ", ".join(
                        f"{s['domain']}.{s['variable']} ({s['condition']})" for s in sources
                    )

                source_patterns_text = ""
                if rule.get("source_patterns"):
                    patterns = [p["pattern"] for p in rule["source_patterns"]]
                    source_patterns_text = f"Source column patterns: {', '.join(patterns)}"

                value_mappings_text = ""
                if rule.get("value_mappings"):
                    mappings = rule["value_mappings"]
                    value_mappings_text = "Value mappings: " + "; ".join(
                        f"{target} <- {', '.join(sources)}" for target, sources in mappings.items()
                    )

                examples_text = ""
                if rule.get("examples"):
                    examples_text = "Examples: " + "; ".join(
                        f"{ex['inputs']} -> {ex['output']}" for ex in rule["examples"]
                    )

                rule_text = f"""
SDTM Variable Derivation Rule
=============================
Domain: {domain}
Variable: {var_name}
Label: {rule.get('label', '')}
Derivation Type: {rule.get('derivation_type', 'direct')}

Description: {rule.get('description', '')}

Derivation Formula: {rule.get('derivation_formula', 'Direct mapping')}

Source Variables Required: {', '.join(rule.get('source_variables', [])) or 'None (direct from source)'}

{source_patterns_text}

{cross_domain_text}

{value_mappings_text}

{examples_text}

Notes: {rule.get('notes', '')}

This derivation rule explains how to populate {domain}.{var_name} ({rule.get('label', '')}).
The derivation type is {rule.get('derivation_type', 'direct')}, meaning:
- 'direct': Simple 1:1 mapping from source column
- 'derived': Calculated from other SDTM variables
- 'cross-domain': Value comes from another SDTM domain
- 'many-to-one': Multiple source columns combined
- 'coded': Value mapping to controlled terminology
- 'lookup': Dictionary or reference table lookup
"""

                # Clean metadata
                clean_source_patterns = []
                if rule.get("source_patterns"):
                    clean_source_patterns = [p["pattern"] for p in rule["source_patterns"]]

                clean_cross_domain = []
                if rule.get("cross_domain_sources"):
                    clean_cross_domain = [
                        f"{s['domain']}.{s['variable']}" for s in rule["cross_domain_sources"]
                    ]

                documents.append(KnowledgeDocument(
                    id=f"derivation-{domain}-{var_name}",
                    text=rule_text.strip(),
                    metadata={
                        "domain": domain,
                        "variable": var_name,
                        "label": rule.get("label", ""),
                        "derivation_type": rule.get("derivation_type", "direct"),
                        "derivation_formula": rule.get("derivation_formula", "")[:200],
                        "source_patterns": ", ".join(clean_source_patterns) if clean_source_patterns else "",
                        "cross_domain_sources": ", ".join(clean_cross_domain) if clean_cross_domain else "",
                        "has_value_mappings": "yes" if rule.get("value_mappings") else "no",
                        "type": "derivation_rule"
                    }
                ))

        # Add cross-domain dependency documents
        for source_var, dependent_vars in CROSS_DOMAIN_DEPENDENCIES.items():
            dep_text = f"""
Cross-Domain Dependency
=======================
Source Variable: {source_var}

Variables that depend on {source_var}:
{chr(10).join('- ' + v for v in dependent_vars)}

When {source_var} changes or is derived, these dependent variables need to be recalculated:
{', '.join(dependent_vars)}

This is a many-to-one relationship where one source variable ({source_var})
is used in the derivation of multiple target variables across different domains.

IMPORTANT: {source_var} must be populated before any of its dependent variables can be calculated.
For example, DM.RFSTDTC (reference start date) must exist before any --DY (study day)
variables can be derived in AE, VS, LB, EX, CM, or MH domains.
"""
            documents.append(KnowledgeDocument(
                id=f"crossdomain-dep-{source_var.replace('.', '-')}",
                text=dep_text.strip(),
                metadata={
                    "source_variable": source_var,
                    "dependent_variables": ", ".join(dependent_vars),
                    "dependency_count": len(dependent_vars),
                    "type": "cross_domain_dependency"
                }
            ))

        # Add source column pattern documents
        for pattern_name, pattern_info in SOURCE_COLUMN_PATTERNS.items():
            pattern_text = f"""
Source Column Pattern Recognition
=================================
Pattern Name: {pattern_name}

Common EDC Column Names:
{chr(10).join('- ' + p for p in pattern_info['patterns'])}

Maps to SDTM Variables:
{chr(10).join('- ' + v for v in pattern_info['target_variables'])}

When you see any of these column names in source EDC data:
{', '.join(pattern_info['patterns'])}

They should map to these SDTM target variables:
{', '.join(pattern_info['target_variables'])}

This is a many-to-one pattern where multiple possible source column names
all map to the same SDTM target variable(s).
"""
            documents.append(KnowledgeDocument(
                id=f"sourcepattern-{pattern_name}",
                text=pattern_text.strip(),
                metadata={
                    "pattern_name": pattern_name,
                    "source_patterns": ", ".join(pattern_info["patterns"]),
                    "target_variables": ", ".join(pattern_info["target_variables"]),
                    "priority": pattern_info["priority"],
                    "type": "source_column_pattern"
                }
            ))

        logger.info(f"Prepared {len(documents)} derivation rule documents")
        return self.upsert_documents("derivationrules", documents)

    def populate_dta_index(self, dta_text: str, dta_id: str = "DTA-001") -> int:
        """Populate the DTA index from a Data Transfer Agreement document.

        The text is split on markdown headings (## or ###) to produce one
        Pinecone record per section.  If no headings are found the whole
        document is indexed as a single chunk.

        Args:
            dta_text: Full text of the DTA document (plain text or markdown).
            dta_id:   Identifier for this agreement (used as a record-ID prefix).

        Returns:
            Number of documents indexed.
        """
        import re

        # Split on markdown headings while keeping the heading text
        sections: list[tuple[str, str]] = []
        pattern = re.compile(r'^(#{2,4})\s+(.+)', re.MULTILINE)
        matches = list(pattern.finditer(dta_text))

        if matches:
            for i, m in enumerate(matches):
                title = m.group(2).strip()
                start = m.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(dta_text)
                body = dta_text[start:end].strip()
                sections.append((title, body))
        else:
            # No headings — index as a single chunk
            sections.append(("Full Document", dta_text.strip()))

        # Detect which SDTM domains a section might reference
        KNOWN_DOMAINS = {
            "DM", "AE", "CM", "MH", "VS", "LB", "EX", "DS", "SV", "SE",
            "TA", "TE", "TI", "TV", "TS", "CO", "SU", "PR", "DV", "HO",
            "CE", "FA", "QS", "SC", "EC", "AG", "ML", "EG", "IE", "PE",
            "PP", "PC", "IS", "MB", "MS", "MI",
        }

        documents: list[KnowledgeDocument] = []
        for idx, (title, body) in enumerate(sections):
            clause_id = f"{dta_id}-S{idx + 1:03d}"
            # Find referenced domains
            found_domains = sorted(
                d for d in KNOWN_DOMAINS
                if re.search(rf'\b{d}\b', body)
            )
            # Determine requirement type from keywords
            req_type = "general"
            lower_body = body.lower()
            if any(kw in lower_body for kw in ("completeness", "missing", "null", "population rate")):
                req_type = "completeness"
            elif any(kw in lower_body for kw in ("format", "iso 8601", "date format", "character length")):
                req_type = "format"
            elif any(kw in lower_body for kw in ("range", "min", "max", "threshold", "limit")):
                req_type = "range"
            elif any(kw in lower_body for kw in ("terminology", "codelist", "controlled", "ct value")):
                req_type = "terminology"

            documents.append(KnowledgeDocument(
                id=clause_id,
                text=body,
                metadata={
                    "dta_id": dta_id,
                    "clause_id": clause_id,
                    "section_title": title[:200],
                    "applicable_domains": ", ".join(found_domains) if found_domains else "ALL",
                    "requirement_type": req_type,
                    "type": "dta_clause",
                }
            ))

        logger.info(f"Prepared {len(documents)} DTA clause documents")
        return self.upsert_documents("dta", documents)

    def populate_all_indexes(self) -> Dict[str, int]:
        """Populate all knowledge base indexes."""
        logger.info("Starting full knowledge base population...")

        # Create indexes first
        self.create_indexes()

        results = {}

        # Populate each index
        logger.info("Populating SDTM-IG index...")
        results["sdtmig"] = self.populate_sdtmig_index()

        logger.info("Populating Controlled Terminology index...")
        results["sdtmct"] = self.populate_controlled_terminology_index()

        logger.info("Populating Validation Rules index...")
        results["validationrules"] = self.populate_validation_rules_index()

        logger.info("Populating Business Rules index...")
        results["businessrules"] = self.populate_business_rules_index()

        logger.info("Populating Derivation Rules index...")
        results["derivationrules"] = self.populate_derivation_rules_index()

        # Summary
        total = sum(results.values())
        logger.info(f"Knowledge base population complete!")
        logger.info(f"Total documents indexed: {total}")
        for index_name, count in results.items():
            logger.info(f"  {index_name}: {count} documents")

        return results


def main():
    """Main entry point for knowledge base setup."""
    print("=" * 60)
    print("SDTM Knowledge Base Setup")
    print("=" * 60)

    if not PINECONE_AVAILABLE:
        print("ERROR: Pinecone package not installed.")
        print("Run: pip install pinecone-client")
        return

    if not OPENAI_AVAILABLE:
        print("ERROR: OpenAI package not installed.")
        print("Run: pip install openai")
        return

    # Check environment variables (loaded from .env)
    pinecone_key = os.getenv("PINECONE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not pinecone_key:
        print("ERROR: PINECONE_API_KEY not found in .env file")
        print(f"Expected .env location: {ENV_FILE}")
        return

    if not openai_key:
        print("ERROR: OPENAI_API_KEY not found in .env file")
        print(f"Expected .env location: {ENV_FILE}")
        return

    # Show loaded keys (masked)
    print(f"\nAPI Keys loaded from .env:")
    print(f"  PINECONE_API_KEY: {pinecone_key[:10]}...{pinecone_key[-4:]}")
    print(f"  OPENAI_API_KEY: {openai_key[:10]}...{openai_key[-4:]}")
    print(f"  PINECONE_ENVIRONMENT: {os.getenv('PINECONE_ENVIRONMENT', 'us-east-1')}")
    print()

    try:
        kb = PineconeKnowledgeBase()
        results = kb.populate_all_indexes()

        print("\n" + "=" * 60)
        print("Setup Complete!")
        print("=" * 60)
        print(f"Total documents indexed: {sum(results.values())}")
        for index_name, count in results.items():
            print(f"  {index_name}: {count} documents")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

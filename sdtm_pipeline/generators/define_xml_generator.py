"""
Define.xml Generator (Phase 5: SDTM Target Data Generation)
============================================================

Generates the Define.xml metadata file required for FDA submissions.
Define.xml is a machine-readable metadata file that describes:

1. Study-level metadata
2. Dataset (domain) definitions
3. Variable definitions with:
   - Labels and descriptions
   - Data types and lengths
   - Controlled terminology references
   - Derivation algorithms
4. Codelists (controlled terminology)
5. Computational methods (derivations)
6. Value-level metadata (for normalized domains)

References:
- CDISC Define-XML 2.1 Specification
- FDA Data Standards Catalog

Author: SDTM ETL Pipeline
Version: 2.0.0
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.dom import minidom
import json

from pydantic import BaseModel, Field


# =============================================================================
# DATA MODELS
# =============================================================================

class VariableMetadata(BaseModel):
    """Metadata for a single SDTM variable."""
    name: str
    label: str
    data_type: str = "text"  # text, integer, float, date, datetime
    length: Optional[int] = None
    significant_digits: Optional[int] = None
    sas_format: Optional[str] = None
    core: str = "Exp"  # Req, Exp, Perm
    origin: str = "CRF"  # CRF, Derived, Assigned, Protocol
    role: Optional[str] = None  # Identifier, Topic, Timing, etc.
    codelist: Optional[str] = None
    comment: Optional[str] = None
    derivation_method: Optional[str] = None


class DatasetMetadata(BaseModel):
    """Metadata for an SDTM domain/dataset."""
    name: str
    label: str
    domain: str
    class_name: str  # Events, Interventions, Findings, Special Purpose
    structure: str = "One record per subject"
    purpose: str = "Tabulation"
    keys: List[str] = Field(default_factory=list)
    repeating: bool = False
    is_reference: bool = False
    variables: List[VariableMetadata] = Field(default_factory=list)


class CodelistItem(BaseModel):
    """An item in a codelist."""
    coded_value: str
    decode: str
    rank: Optional[int] = None


class Codelist(BaseModel):
    """A controlled terminology codelist."""
    oid: str
    name: str
    data_type: str = "text"
    items: List[CodelistItem] = Field(default_factory=list)
    is_extensible: bool = False
    source: str = "CDISC"


class ComputationMethod(BaseModel):
    """A computational method (derivation algorithm)."""
    oid: str
    name: str
    description: str


class StudyMetadata(BaseModel):
    """Study-level metadata."""
    study_oid: str
    study_name: str
    study_description: Optional[str] = None
    protocol_name: Optional[str] = None
    metadata_version_oid: str = "MDV.SDTM.1"
    define_version: str = "2.1.0"
    standard_name: str = "CDISC-SDTM"
    standard_version: str = "3.4"
    originator: str = "Sponsor"
    file_oid: str = "DEF.SDTM"


# =============================================================================
# SDTM DOMAIN TEMPLATES
# =============================================================================

SDTM_DOMAIN_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "DM": {
        "label": "Demographics",
        "class_name": "Special Purpose",
        "structure": "One record per subject",
        "repeating": False,
        "keys": ["STUDYID", "USUBJID"],
        "variables": [
            {"name": "STUDYID", "label": "Study Identifier", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "DOMAIN", "label": "Domain Abbreviation", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "USUBJID", "label": "Unique Subject Identifier", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "SUBJID", "label": "Subject Identifier for the Study", "core": "Req", "role": "Topic", "data_type": "text"},
            {"name": "RFSTDTC", "label": "Subject Reference Start Date/Time", "core": "Exp", "role": "Timing", "data_type": "datetime"},
            {"name": "RFENDTC", "label": "Subject Reference End Date/Time", "core": "Exp", "role": "Timing", "data_type": "datetime"},
            {"name": "SITEID", "label": "Study Site Identifier", "core": "Req", "role": "Record Qualifier", "data_type": "text"},
            {"name": "BRTHDTC", "label": "Date/Time of Birth", "core": "Perm", "role": "Record Qualifier", "data_type": "datetime"},
            {"name": "AGE", "label": "Age", "core": "Exp", "role": "Record Qualifier", "data_type": "integer"},
            {"name": "AGEU", "label": "Age Units", "core": "Exp", "role": "Variable Qualifier", "data_type": "text", "codelist": "AGEU"},
            {"name": "SEX", "label": "Sex", "core": "Req", "role": "Record Qualifier", "data_type": "text", "codelist": "SEX"},
            {"name": "RACE", "label": "Race", "core": "Exp", "role": "Record Qualifier", "data_type": "text", "codelist": "RACE"},
            {"name": "ETHNIC", "label": "Ethnicity", "core": "Perm", "role": "Record Qualifier", "data_type": "text", "codelist": "ETHNIC"},
            {"name": "ARMCD", "label": "Planned Arm Code", "core": "Req", "role": "Record Qualifier", "data_type": "text"},
            {"name": "ARM", "label": "Description of Planned Arm", "core": "Req", "role": "Synonym Qualifier", "data_type": "text"},
            {"name": "COUNTRY", "label": "Country", "core": "Req", "role": "Record Qualifier", "data_type": "text", "codelist": "COUNTRY"},
        ]
    },
    "AE": {
        "label": "Adverse Events",
        "class_name": "Events",
        "structure": "One record per adverse event per subject",
        "repeating": True,
        "keys": ["STUDYID", "USUBJID", "AESEQ"],
        "variables": [
            {"name": "STUDYID", "label": "Study Identifier", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "DOMAIN", "label": "Domain Abbreviation", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "USUBJID", "label": "Unique Subject Identifier", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "AESEQ", "label": "Sequence Number", "core": "Req", "role": "Identifier", "data_type": "integer"},
            {"name": "AETERM", "label": "Reported Term for the Adverse Event", "core": "Req", "role": "Topic", "data_type": "text"},
            {"name": "AEDECOD", "label": "Dictionary-Derived Term", "core": "Req", "role": "Synonym Qualifier", "data_type": "text"},
            {"name": "AEBODSYS", "label": "Body System or Organ Class", "core": "Exp", "role": "Record Qualifier", "data_type": "text"},
            {"name": "AESEV", "label": "Severity/Intensity", "core": "Perm", "role": "Record Qualifier", "data_type": "text", "codelist": "AESEV"},
            {"name": "AESER", "label": "Serious Event", "core": "Exp", "role": "Record Qualifier", "data_type": "text", "codelist": "NY"},
            {"name": "AEREL", "label": "Causality", "core": "Perm", "role": "Record Qualifier", "data_type": "text"},
            {"name": "AEACN", "label": "Action Taken with Study Treatment", "core": "Exp", "role": "Record Qualifier", "data_type": "text", "codelist": "ACN"},
            {"name": "AEOUT", "label": "Outcome of Adverse Event", "core": "Exp", "role": "Record Qualifier", "data_type": "text", "codelist": "OUT"},
            {"name": "AESTDTC", "label": "Start Date/Time of Adverse Event", "core": "Exp", "role": "Timing", "data_type": "datetime"},
            {"name": "AEENDTC", "label": "End Date/Time of Adverse Event", "core": "Exp", "role": "Timing", "data_type": "datetime"},
        ]
    },
    "VS": {
        "label": "Vital Signs",
        "class_name": "Findings",
        "structure": "One record per vital sign measurement per time point per subject",
        "repeating": True,
        "keys": ["STUDYID", "USUBJID", "VSTESTCD", "VISITNUM", "VSTPTNUM"],
        "variables": [
            {"name": "STUDYID", "label": "Study Identifier", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "DOMAIN", "label": "Domain Abbreviation", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "USUBJID", "label": "Unique Subject Identifier", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "VSSEQ", "label": "Sequence Number", "core": "Req", "role": "Identifier", "data_type": "integer"},
            {"name": "VSTESTCD", "label": "Vital Signs Test Short Name", "core": "Req", "role": "Topic", "data_type": "text", "codelist": "VSTESTCD"},
            {"name": "VSTEST", "label": "Vital Signs Test Name", "core": "Req", "role": "Synonym Qualifier", "data_type": "text", "codelist": "VSTEST"},
            {"name": "VSORRES", "label": "Result or Finding in Original Units", "core": "Exp", "role": "Result Qualifier", "data_type": "text"},
            {"name": "VSORRESU", "label": "Original Units", "core": "Exp", "role": "Variable Qualifier", "data_type": "text", "codelist": "VSRESU"},
            {"name": "VSSTRESC", "label": "Character Result/Finding in Std Format", "core": "Exp", "role": "Result Qualifier", "data_type": "text"},
            {"name": "VSSTRESN", "label": "Numeric Result/Finding in Standard Units", "core": "Exp", "role": "Result Qualifier", "data_type": "float"},
            {"name": "VSSTRESU", "label": "Standard Units", "core": "Exp", "role": "Variable Qualifier", "data_type": "text", "codelist": "VSRESU"},
            {"name": "VSSTAT", "label": "Completion Status", "core": "Perm", "role": "Record Qualifier", "data_type": "text", "codelist": "STAT"},
            {"name": "VISITNUM", "label": "Visit Number", "core": "Exp", "role": "Timing", "data_type": "float"},
            {"name": "VISIT", "label": "Visit Name", "core": "Exp", "role": "Timing", "data_type": "text"},
            {"name": "VSDTC", "label": "Date/Time of Measurements", "core": "Exp", "role": "Timing", "data_type": "datetime"},
        ]
    },
    "LB": {
        "label": "Laboratory Test Results",
        "class_name": "Findings",
        "structure": "One record per lab test per time point per subject",
        "repeating": True,
        "keys": ["STUDYID", "USUBJID", "LBTESTCD", "VISITNUM", "LBSPEC"],
        "variables": [
            {"name": "STUDYID", "label": "Study Identifier", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "DOMAIN", "label": "Domain Abbreviation", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "USUBJID", "label": "Unique Subject Identifier", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "LBSEQ", "label": "Sequence Number", "core": "Req", "role": "Identifier", "data_type": "integer"},
            {"name": "LBTESTCD", "label": "Lab Test or Examination Short Name", "core": "Req", "role": "Topic", "data_type": "text", "codelist": "LBTESTCD"},
            {"name": "LBTEST", "label": "Lab Test or Examination Name", "core": "Req", "role": "Synonym Qualifier", "data_type": "text", "codelist": "LBTEST"},
            {"name": "LBCAT", "label": "Category for Lab Test", "core": "Exp", "role": "Grouping Qualifier", "data_type": "text"},
            {"name": "LBORRES", "label": "Result or Finding in Original Units", "core": "Exp", "role": "Result Qualifier", "data_type": "text"},
            {"name": "LBORRESU", "label": "Original Units", "core": "Exp", "role": "Variable Qualifier", "data_type": "text", "codelist": "UNIT"},
            {"name": "LBSTRESC", "label": "Character Result/Finding in Std Format", "core": "Exp", "role": "Result Qualifier", "data_type": "text"},
            {"name": "LBSTRESN", "label": "Numeric Result/Finding in Standard Units", "core": "Exp", "role": "Result Qualifier", "data_type": "float"},
            {"name": "LBSTRESU", "label": "Standard Units", "core": "Exp", "role": "Variable Qualifier", "data_type": "text", "codelist": "UNIT"},
            {"name": "LBNRIND", "label": "Reference Range Indicator", "core": "Exp", "role": "Variable Qualifier", "data_type": "text", "codelist": "NRIND"},
            {"name": "LBSPEC", "label": "Specimen Type", "core": "Exp", "role": "Record Qualifier", "data_type": "text", "codelist": "SPEC"},
            {"name": "VISITNUM", "label": "Visit Number", "core": "Exp", "role": "Timing", "data_type": "float"},
            {"name": "VISIT", "label": "Visit Name", "core": "Exp", "role": "Timing", "data_type": "text"},
            {"name": "LBDTC", "label": "Date/Time of Specimen Collection", "core": "Exp", "role": "Timing", "data_type": "datetime"},
        ]
    },
    "CM": {
        "label": "Concomitant Medications",
        "class_name": "Interventions",
        "structure": "One record per recorded medication occurrence per subject",
        "repeating": True,
        "keys": ["STUDYID", "USUBJID", "CMSEQ"],
        "variables": [
            {"name": "STUDYID", "label": "Study Identifier", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "DOMAIN", "label": "Domain Abbreviation", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "USUBJID", "label": "Unique Subject Identifier", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "CMSEQ", "label": "Sequence Number", "core": "Req", "role": "Identifier", "data_type": "integer"},
            {"name": "CMTRT", "label": "Reported Name of Drug, Med, or Therapy", "core": "Req", "role": "Topic", "data_type": "text"},
            {"name": "CMDECOD", "label": "Standardized Medication Name", "core": "Exp", "role": "Synonym Qualifier", "data_type": "text"},
            {"name": "CMCAT", "label": "Category for Medication", "core": "Perm", "role": "Grouping Qualifier", "data_type": "text"},
            {"name": "CMDOSE", "label": "Dose per Administration", "core": "Exp", "role": "Record Qualifier", "data_type": "float"},
            {"name": "CMDOSU", "label": "Dose Units", "core": "Exp", "role": "Variable Qualifier", "data_type": "text", "codelist": "UNIT"},
            {"name": "CMROUTE", "label": "Route of Administration", "core": "Exp", "role": "Record Qualifier", "data_type": "text", "codelist": "ROUTE"},
            {"name": "CMSTDTC", "label": "Start Date/Time of Medication", "core": "Exp", "role": "Timing", "data_type": "datetime"},
            {"name": "CMENDTC", "label": "End Date/Time of Medication", "core": "Exp", "role": "Timing", "data_type": "datetime"},
        ]
    },
    "EX": {
        "label": "Exposure",
        "class_name": "Interventions",
        "structure": "One record per protocol-specified study treatment per subject",
        "repeating": True,
        "keys": ["STUDYID", "USUBJID", "EXSEQ"],
        "variables": [
            {"name": "STUDYID", "label": "Study Identifier", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "DOMAIN", "label": "Domain Abbreviation", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "USUBJID", "label": "Unique Subject Identifier", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "EXSEQ", "label": "Sequence Number", "core": "Req", "role": "Identifier", "data_type": "integer"},
            {"name": "EXTRT", "label": "Name of Treatment", "core": "Req", "role": "Topic", "data_type": "text"},
            {"name": "EXDOSE", "label": "Dose", "core": "Exp", "role": "Record Qualifier", "data_type": "float"},
            {"name": "EXDOSU", "label": "Dose Units", "core": "Exp", "role": "Variable Qualifier", "data_type": "text", "codelist": "UNIT"},
            {"name": "EXDOSFRM", "label": "Dose Form", "core": "Exp", "role": "Variable Qualifier", "data_type": "text", "codelist": "FRM"},
            {"name": "EXROUTE", "label": "Route of Administration", "core": "Exp", "role": "Record Qualifier", "data_type": "text", "codelist": "ROUTE"},
            {"name": "EXSTDTC", "label": "Start Date/Time of Treatment", "core": "Exp", "role": "Timing", "data_type": "datetime"},
            {"name": "EXENDTC", "label": "End Date/Time of Treatment", "core": "Exp", "role": "Timing", "data_type": "datetime"},
            {"name": "VISITNUM", "label": "Visit Number", "core": "Exp", "role": "Timing", "data_type": "float"},
            {"name": "VISIT", "label": "Visit Name", "core": "Exp", "role": "Timing", "data_type": "text"},
        ]
    },
    "MH": {
        "label": "Medical History",
        "class_name": "Events",
        "structure": "One record per medical history event per subject",
        "repeating": True,
        "keys": ["STUDYID", "USUBJID", "MHSEQ"],
        "variables": [
            {"name": "STUDYID", "label": "Study Identifier", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "DOMAIN", "label": "Domain Abbreviation", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "USUBJID", "label": "Unique Subject Identifier", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "MHSEQ", "label": "Sequence Number", "core": "Req", "role": "Identifier", "data_type": "integer"},
            {"name": "MHTERM", "label": "Reported Term for the Medical History", "core": "Req", "role": "Topic", "data_type": "text"},
            {"name": "MHDECOD", "label": "Dictionary-Derived Term", "core": "Exp", "role": "Synonym Qualifier", "data_type": "text"},
            {"name": "MHCAT", "label": "Category for Medical History", "core": "Perm", "role": "Grouping Qualifier", "data_type": "text"},
            {"name": "MHBODSYS", "label": "Body System or Organ Class", "core": "Exp", "role": "Record Qualifier", "data_type": "text"},
            {"name": "MHSTDTC", "label": "Start Date/Time of Medical History Event", "core": "Exp", "role": "Timing", "data_type": "datetime"},
            {"name": "MHENDTC", "label": "End Date/Time of Medical History Event", "core": "Perm", "role": "Timing", "data_type": "datetime"},
        ]
    },
    "DS": {
        "label": "Disposition",
        "class_name": "Events",
        "structure": "One record per disposition status per subject",
        "repeating": True,
        "keys": ["STUDYID", "USUBJID", "DSSEQ"],
        "variables": [
            {"name": "STUDYID", "label": "Study Identifier", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "DOMAIN", "label": "Domain Abbreviation", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "USUBJID", "label": "Unique Subject Identifier", "core": "Req", "role": "Identifier", "data_type": "text"},
            {"name": "DSSEQ", "label": "Sequence Number", "core": "Req", "role": "Identifier", "data_type": "integer"},
            {"name": "DSTERM", "label": "Reported Term for the Disposition Event", "core": "Req", "role": "Topic", "data_type": "text"},
            {"name": "DSDECOD", "label": "Standardized Disposition Term", "core": "Req", "role": "Synonym Qualifier", "data_type": "text", "codelist": "NCOMPLT"},
            {"name": "DSCAT", "label": "Category for Disposition Event", "core": "Exp", "role": "Grouping Qualifier", "data_type": "text"},
            {"name": "DSSTDTC", "label": "Start Date/Time of Disposition Event", "core": "Exp", "role": "Timing", "data_type": "datetime"},
        ]
    }
}


# Standard Codelists
STANDARD_CODELISTS: Dict[str, Dict[str, Any]] = {
    "SEX": {
        "name": "Sex",
        "items": [
            {"coded_value": "M", "decode": "Male"},
            {"coded_value": "F", "decode": "Female"},
            {"coded_value": "U", "decode": "Unknown"},
        ]
    },
    "RACE": {
        "name": "Race",
        "items": [
            {"coded_value": "WHITE", "decode": "White"},
            {"coded_value": "BLACK OR AFRICAN AMERICAN", "decode": "Black or African American"},
            {"coded_value": "ASIAN", "decode": "Asian"},
            {"coded_value": "AMERICAN INDIAN OR ALASKA NATIVE", "decode": "American Indian or Alaska Native"},
            {"coded_value": "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER", "decode": "Native Hawaiian or Other Pacific Islander"},
            {"coded_value": "OTHER", "decode": "Other"},
            {"coded_value": "MULTIPLE", "decode": "Multiple"},
        ]
    },
    "ETHNIC": {
        "name": "Ethnicity",
        "items": [
            {"coded_value": "HISPANIC OR LATINO", "decode": "Hispanic or Latino"},
            {"coded_value": "NOT HISPANIC OR LATINO", "decode": "Not Hispanic or Latino"},
            {"coded_value": "NOT REPORTED", "decode": "Not Reported"},
            {"coded_value": "UNKNOWN", "decode": "Unknown"},
        ]
    },
    "NY": {
        "name": "No Yes Response",
        "items": [
            {"coded_value": "N", "decode": "No"},
            {"coded_value": "Y", "decode": "Yes"},
        ]
    },
    "AGEU": {
        "name": "Age Unit",
        "items": [
            {"coded_value": "YEARS", "decode": "Years"},
            {"coded_value": "MONTHS", "decode": "Months"},
            {"coded_value": "WEEKS", "decode": "Weeks"},
            {"coded_value": "DAYS", "decode": "Days"},
            {"coded_value": "HOURS", "decode": "Hours"},
        ]
    },
}


# =============================================================================
# DEFINE.XML GENERATOR
# =============================================================================

class DefineXMLGenerator:
    """
    Generates Define.xml metadata file for SDTM datasets.

    Define.xml is required for FDA submissions and describes:
    - Study metadata
    - Dataset definitions
    - Variable definitions
    - Controlled terminology (codelists)
    - Derivation methods
    """

    # XML Namespaces
    NS_ODM = "http://www.cdisc.org/ns/odm/v1.3"
    NS_DEF = "http://www.cdisc.org/ns/def/v2.1"
    NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"
    NS_XLINK = "http://www.w3.org/1999/xlink"

    def __init__(self, study_metadata: StudyMetadata):
        self.study_metadata = study_metadata
        self.datasets: List[DatasetMetadata] = []
        self.codelists: Dict[str, Codelist] = {}
        self.methods: Dict[str, ComputationMethod] = {}

    def add_dataset(self, dataset: DatasetMetadata):
        """Add a dataset definition."""
        self.datasets.append(dataset)

    def add_dataset_from_template(self, domain_code: str, actual_variables: Optional[List[str]] = None):
        """Add a dataset from the standard template."""
        if domain_code not in SDTM_DOMAIN_TEMPLATES:
            raise ValueError(f"Unknown domain: {domain_code}")

        template = SDTM_DOMAIN_TEMPLATES[domain_code]

        # Create variable metadata
        variables = []
        for var_def in template["variables"]:
            # If actual_variables provided, only include those
            if actual_variables and var_def["name"] not in actual_variables:
                continue

            var_meta = VariableMetadata(
                name=var_def["name"],
                label=var_def["label"],
                data_type=var_def.get("data_type", "text"),
                core=var_def.get("core", "Exp"),
                role=var_def.get("role"),
                codelist=var_def.get("codelist"),
                origin=var_def.get("origin", "CRF")
            )
            variables.append(var_meta)

        dataset = DatasetMetadata(
            name=domain_code,
            label=template["label"],
            domain=domain_code,
            class_name=template["class_name"],
            structure=template["structure"],
            repeating=template["repeating"],
            keys=template["keys"],
            variables=variables
        )

        self.datasets.append(dataset)
        return dataset

    def add_codelist(self, codelist: Codelist):
        """Add a codelist."""
        self.codelists[codelist.oid] = codelist

    def add_standard_codelists(self):
        """Add standard CDISC codelists."""
        for code, data in STANDARD_CODELISTS.items():
            codelist = Codelist(
                oid=f"CL.{code}",
                name=data["name"],
                items=[CodelistItem(**item) for item in data["items"]]
            )
            self.codelists[codelist.oid] = codelist

    def add_method(self, method: ComputationMethod):
        """Add a computational method."""
        self.methods[method.oid] = method

    def generate(self, output_path: Optional[str] = None) -> str:
        """
        Generate the Define.xml file.

        Args:
            output_path: Path to save the XML file

        Returns:
            XML string
        """
        # Create root element with namespaces
        root = ET.Element("ODM")
        root.set("xmlns", self.NS_ODM)
        root.set("xmlns:def", self.NS_DEF)
        root.set("xmlns:xsi", self.NS_XSI)
        root.set("xmlns:xlink", self.NS_XLINK)
        root.set("ODMVersion", "1.3.2")
        root.set("FileOID", self.study_metadata.file_oid)
        root.set("FileType", "Snapshot")
        root.set("CreationDateTime", datetime.utcnow().isoformat())
        root.set("Originator", self.study_metadata.originator)

        # Add Study element
        study = ET.SubElement(root, "Study")
        study.set("OID", self.study_metadata.study_oid)

        # GlobalVariables
        global_vars = ET.SubElement(study, "GlobalVariables")
        study_name = ET.SubElement(global_vars, "StudyName")
        study_name.text = self.study_metadata.study_name
        study_desc = ET.SubElement(global_vars, "StudyDescription")
        study_desc.text = self.study_metadata.study_description or self.study_metadata.study_name
        protocol_name = ET.SubElement(global_vars, "ProtocolName")
        protocol_name.text = self.study_metadata.protocol_name or self.study_metadata.study_name

        # MetaDataVersion
        mdv = ET.SubElement(study, "MetaDataVersion")
        mdv.set("OID", self.study_metadata.metadata_version_oid)
        mdv.set("Name", f"SDTM metadata for {self.study_metadata.study_name}")
        mdv.set("def:DefineVersion", self.study_metadata.define_version)
        mdv.set("def:StandardName", self.study_metadata.standard_name)
        mdv.set("def:StandardVersion", self.study_metadata.standard_version)

        # Add Codelists
        for codelist in self.codelists.values():
            self._add_codelist_element(mdv, codelist)

        # Add Methods
        for method in self.methods.values():
            self._add_method_element(mdv, method)

        # Add ItemGroupDef (datasets)
        for dataset in self.datasets:
            self._add_dataset_element(mdv, dataset)

        # Add ItemDef (variables)
        for dataset in self.datasets:
            for var in dataset.variables:
                self._add_variable_element(mdv, dataset.name, var)

        # Convert to string with pretty printing
        xml_string = ET.tostring(root, encoding='unicode')
        dom = minidom.parseString(xml_string)
        pretty_xml = dom.toprettyxml(indent="  ")

        # Remove extra blank lines
        lines = [line for line in pretty_xml.split('\n') if line.strip()]
        pretty_xml = '\n'.join(lines)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(pretty_xml)

        return pretty_xml

    def _add_codelist_element(self, parent: ET.Element, codelist: Codelist):
        """Add CodeList element to MetaDataVersion."""
        cl_elem = ET.SubElement(parent, "CodeList")
        cl_elem.set("OID", codelist.oid)
        cl_elem.set("Name", codelist.name)
        cl_elem.set("DataType", codelist.data_type)

        for item in codelist.items:
            item_elem = ET.SubElement(cl_elem, "CodeListItem")
            item_elem.set("CodedValue", item.coded_value)
            if item.rank:
                item_elem.set("Rank", str(item.rank))
            decode = ET.SubElement(item_elem, "Decode")
            trans = ET.SubElement(decode, "TranslatedText")
            trans.set("xml:lang", "en")
            trans.text = item.decode

    def _add_method_element(self, parent: ET.Element, method: ComputationMethod):
        """Add MethodDef element to MetaDataVersion."""
        method_elem = ET.SubElement(parent, "MethodDef")
        method_elem.set("OID", method.oid)
        method_elem.set("Name", method.name)
        method_elem.set("Type", "Computation")

        desc = ET.SubElement(method_elem, "Description")
        trans = ET.SubElement(desc, "TranslatedText")
        trans.set("xml:lang", "en")
        trans.text = method.description

    def _add_dataset_element(self, parent: ET.Element, dataset: DatasetMetadata):
        """Add ItemGroupDef element for a dataset."""
        ig_elem = ET.SubElement(parent, "ItemGroupDef")
        ig_elem.set("OID", f"IG.{dataset.name}")
        ig_elem.set("Name", dataset.name)
        ig_elem.set("Repeating", "Yes" if dataset.repeating else "No")
        ig_elem.set("IsReferenceData", "Yes" if dataset.is_reference else "No")
        ig_elem.set("Purpose", dataset.purpose)
        ig_elem.set("def:Structure", dataset.structure)
        ig_elem.set("def:Class", dataset.class_name)

        # Add description
        desc = ET.SubElement(ig_elem, "Description")
        trans = ET.SubElement(desc, "TranslatedText")
        trans.set("xml:lang", "en")
        trans.text = dataset.label

        # Add ItemRef for each variable
        for idx, var in enumerate(dataset.variables, 1):
            item_ref = ET.SubElement(ig_elem, "ItemRef")
            item_ref.set("ItemOID", f"IT.{dataset.name}.{var.name}")
            item_ref.set("OrderNumber", str(idx))
            item_ref.set("Mandatory", "Yes" if var.core == "Req" else "No")

            if var.name in dataset.keys:
                item_ref.set("KeySequence", str(dataset.keys.index(var.name) + 1))

            if var.role:
                item_ref.set("Role", var.role)

    def _add_variable_element(self, parent: ET.Element, dataset_name: str, var: VariableMetadata):
        """Add ItemDef element for a variable."""
        item_elem = ET.SubElement(parent, "ItemDef")
        item_elem.set("OID", f"IT.{dataset_name}.{var.name}")
        item_elem.set("Name", var.name)
        item_elem.set("DataType", var.data_type)

        if var.length:
            item_elem.set("Length", str(var.length))
        if var.significant_digits:
            item_elem.set("SignificantDigits", str(var.significant_digits))
        if var.sas_format:
            item_elem.set("SASFieldName", var.name)

        # Add description (label)
        desc = ET.SubElement(item_elem, "Description")
        trans = ET.SubElement(desc, "TranslatedText")
        trans.set("xml:lang", "en")
        trans.text = var.label

        # Add codelist reference if applicable
        if var.codelist:
            cl_ref = ET.SubElement(item_elem, "CodeListRef")
            cl_ref.set("CodeListOID", f"CL.{var.codelist}")

        # Add origin
        origin = ET.SubElement(item_elem, "def:Origin")
        origin.set("Type", var.origin)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "study_metadata": self.study_metadata.model_dump(),
            "datasets": [d.model_dump() for d in self.datasets],
            "codelists": {k: v.model_dump() for k, v in self.codelists.items()},
            "methods": {k: v.model_dump() for k, v in self.methods.items()}
        }

    def save_metadata_json(self, output_path: str):
        """Save metadata as JSON for inspection."""
        with open(output_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_define_xml_generator(
    study_id: str,
    study_name: str,
    protocol_name: Optional[str] = None,
    sdtmig_version: str = "3.4",
    domains: Optional[List[str]] = None
) -> DefineXMLGenerator:
    """
    Factory function to create a Define.xml generator.

    Args:
        study_id: Study identifier
        study_name: Study name
        protocol_name: Protocol name
        sdtmig_version: SDTM-IG version
        domains: List of domain codes to include

    Returns:
        Configured DefineXMLGenerator instance
    """
    study_meta = StudyMetadata(
        study_oid=f"STUDY.{study_id}",
        study_name=study_name,
        protocol_name=protocol_name or study_name,
        standard_version=sdtmig_version
    )

    generator = DefineXMLGenerator(study_meta)

    # Add standard codelists
    generator.add_standard_codelists()

    # Add domain templates if specified
    if domains:
        for domain in domains:
            if domain in SDTM_DOMAIN_TEMPLATES:
                generator.add_dataset_from_template(domain)

    return generator


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Example: Generate Define.xml for a study
    generator = create_define_xml_generator(
        study_id="DCRI001",
        study_name="Example Clinical Trial",
        protocol_name="DCRI-001",
        domains=["DM", "AE", "VS", "LB", "CM", "EX"]
    )

    # Generate and save
    xml_content = generator.generate("define.xml")
    generator.save_metadata_json("define_metadata.json")

    print("Define.xml generated successfully!")
    print(f"Datasets: {len(generator.datasets)}")
    print(f"Codelists: {len(generator.codelists)}")

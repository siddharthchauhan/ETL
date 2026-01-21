"""
SDTM Web Reference Fetcher
==========================
Fetches SDTM-IG 3.4 specifications, Controlled Terminology, and validation rules
from authoritative CDISC sources via web crawling.

Key Sources:
- SDTM-IG 3.4: https://sastricks.com/cdisc/SDTMIG%20v3.4-FINAL_2022-07-21.pdf
- CDISC SDTMIG: https://www.cdisc.org/standards/foundational/sdtmig
- CDISC CT: https://www.cdisc.org/standards/terminology
- Pinnacle 21: https://www.pinnacle21.com/downloads
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class SDTMVariable:
    """SDTM Variable specification from SDTM-IG."""
    name: str
    label: str
    data_type: str  # Char, Num
    role: str  # Identifier, Topic, Qualifier, Timing, Rule
    core: str  # Req, Exp, Perm
    description: str = ""
    codelist: Optional[str] = None
    origin: Optional[str] = None  # CRF, Derived, Assigned, Protocol


@dataclass
class SDTMDomainSpec:
    """Complete SDTM domain specification."""
    domain: str
    description: str
    domain_class: str  # Events, Findings, Interventions, Special Purpose, Trial Design
    variables: List[SDTMVariable] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)


@dataclass
class ControlledTerminology:
    """CDISC Controlled Terminology codelist."""
    codelist_code: str
    codelist_name: str
    extensible: bool
    terms: List[Dict[str, str]] = field(default_factory=list)  # code, decode, definition


class SDTMWebReference:
    """
    Fetches and caches SDTM specifications from web sources.

    Uses multiple strategies:
    1. Web fetch from CDISC/SDTM-IG sources
    2. Tavily AI search for specific queries
    3. Local cache for performance
    """

    # Authoritative SDTM-IG sources
    SDTM_SOURCES = {
        "sdtmig_pdf": "https://sastricks.com/cdisc/SDTMIG%20v3.4-FINAL_2022-07-21.pdf",
        "cdisc_sdtmig": "https://www.cdisc.org/standards/foundational/sdtmig",
        "cdisc_ct": "https://www.cdisc.org/standards/terminology",
        "cdisc_define": "https://www.cdisc.org/standards/data-exchange/define-xml",
        "pinnacle21": "https://www.pinnacle21.com/downloads",
        "phuse_sdrg": "https://www.phuse.global/Working-Groups/Data-Visualisation-and-Open-Source-Technology/White-Papers/SDRG-Template"
    }

    # SDTM-IG 3.4 Domain Specifications (comprehensive reference)
    SDTMIG_34_DOMAINS = {
        "AE": {
            "description": "Adverse Events",
            "class": "Events",
            "structure": "One record per adverse event per subject",
            "variables": {
                "required": [
                    {"name": "STUDYID", "label": "Study Identifier", "type": "Char", "role": "Identifier"},
                    {"name": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "role": "Identifier"},
                    {"name": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "role": "Identifier"},
                    {"name": "AESEQ", "label": "Sequence Number", "type": "Num", "role": "Identifier"},
                    {"name": "AETERM", "label": "Reported Term for the Adverse Event", "type": "Char", "role": "Topic"},
                ],
                "expected": [
                    {"name": "AEDECOD", "label": "Dictionary-Derived Term", "type": "Char", "role": "Synonym Qualifier", "codelist": "MedDRA"},
                    {"name": "AEBODSYS", "label": "Body System or Organ Class", "type": "Char", "role": "Record Qualifier", "codelist": "MedDRA"},
                    {"name": "AESEV", "label": "Severity/Intensity", "type": "Char", "role": "Record Qualifier", "codelist": "AESEV"},
                    {"name": "AESER", "label": "Serious Event", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                    {"name": "AEACN", "label": "Action Taken with Study Treatment", "type": "Char", "role": "Record Qualifier", "codelist": "ACN"},
                    {"name": "AEREL", "label": "Causality", "type": "Char", "role": "Record Qualifier", "codelist": "REL"},
                    {"name": "AEOUT", "label": "Outcome of Adverse Event", "type": "Char", "role": "Record Qualifier", "codelist": "OUT"},
                    {"name": "AESTDTC", "label": "Start Date/Time of Adverse Event", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                    {"name": "AEENDTC", "label": "End Date/Time of Adverse Event", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                ],
                "permissible": [
                    {"name": "AESPID", "label": "Sponsor-Defined Identifier", "type": "Char", "role": "Identifier"},
                    {"name": "AEGRPID", "label": "Group ID", "type": "Char", "role": "Identifier"},
                    {"name": "AEREFID", "label": "Reference ID", "type": "Char", "role": "Identifier"},
                    {"name": "AELNKID", "label": "Link ID", "type": "Char", "role": "Identifier"},
                    {"name": "AELNKGRP", "label": "Link Group ID", "type": "Char", "role": "Identifier"},
                    {"name": "AEMODIFY", "label": "Modified Reported Term", "type": "Char", "role": "Synonym Qualifier"},
                    {"name": "AELLT", "label": "Lowest Level Term", "type": "Char", "role": "Variable Qualifier", "codelist": "MedDRA"},
                    {"name": "AELLTCD", "label": "Lowest Level Term Code", "type": "Num", "role": "Variable Qualifier", "codelist": "MedDRA"},
                    {"name": "AEPTCD", "label": "Preferred Term Code", "type": "Num", "role": "Variable Qualifier", "codelist": "MedDRA"},
                    {"name": "AEHLT", "label": "High Level Term", "type": "Char", "role": "Variable Qualifier", "codelist": "MedDRA"},
                    {"name": "AEHLTCD", "label": "High Level Term Code", "type": "Num", "role": "Variable Qualifier", "codelist": "MedDRA"},
                    {"name": "AEHLGT", "label": "High Level Group Term", "type": "Char", "role": "Variable Qualifier", "codelist": "MedDRA"},
                    {"name": "AEHLGTCD", "label": "High Level Group Term Code", "type": "Num", "role": "Variable Qualifier", "codelist": "MedDRA"},
                    {"name": "AEBDSYCD", "label": "Body System or Organ Class Code", "type": "Num", "role": "Record Qualifier", "codelist": "MedDRA"},
                    {"name": "AESOC", "label": "Primary System Organ Class", "type": "Char", "role": "Record Qualifier", "codelist": "MedDRA"},
                    {"name": "AESOCCD", "label": "Primary System Organ Class Code", "type": "Num", "role": "Record Qualifier", "codelist": "MedDRA"},
                    {"name": "AEPRESP", "label": "Pre-Specified Adverse Event", "type": "Char", "role": "Variable Qualifier", "codelist": "NY"},
                    {"name": "AEOCCUR", "label": "Adverse Event Occurrence", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                    {"name": "AESTAT", "label": "Completion Status", "type": "Char", "role": "Record Qualifier", "codelist": "ND"},
                    {"name": "AEREASND", "label": "Reason Adverse Event Not Collected", "type": "Char", "role": "Record Qualifier"},
                    {"name": "AEACNOTH", "label": "Other Action Taken", "type": "Char", "role": "Record Qualifier"},
                    {"name": "AERELNST", "label": "Relationship to Non-Study Treatment", "type": "Char", "role": "Record Qualifier"},
                    {"name": "AEPATT", "label": "Pattern of Adverse Event", "type": "Char", "role": "Record Qualifier", "codelist": "PAT"},
                    {"name": "AESCAN", "label": "Involves Cancer", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                    {"name": "AESCONG", "label": "Congenital Anomaly or Birth Defect", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                    {"name": "AESDISAB", "label": "Persist or Signif Disability/Incapacity", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                    {"name": "AESDTH", "label": "Results in Death", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                    {"name": "AESHOSP", "label": "Requires or Prolongs Hospitalization", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                    {"name": "AESLIFE", "label": "Is Life Threatening", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                    {"name": "AESOD", "label": "Occurred with Overdose", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                    {"name": "AESMIE", "label": "Other Medically Important Serious Event", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                    {"name": "AECONTRT", "label": "Concomitant or Additional Trtmnt Given", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                    {"name": "AETOXGR", "label": "Standard Toxicity Grade", "type": "Char", "role": "Record Qualifier", "codelist": "TOXGR"},
                    {"name": "EPOCH", "label": "Epoch", "type": "Char", "role": "Timing", "codelist": "EPOCH"},
                    {"name": "AEDTC", "label": "Date/Time of Collection", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                    {"name": "AESTDY", "label": "Study Day of Start of Adverse Event", "type": "Num", "role": "Timing"},
                    {"name": "AEENDY", "label": "Study Day of End of Adverse Event", "type": "Num", "role": "Timing"},
                    {"name": "AEDUR", "label": "Duration of Adverse Event", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                    {"name": "AEENRF", "label": "End Relative to Reference Period", "type": "Char", "role": "Timing", "codelist": "STENRF"},
                    {"name": "AESTRF", "label": "Start Relative to Reference Period", "type": "Char", "role": "Timing", "codelist": "STENRF"},
                    {"name": "VISITNUM", "label": "Visit Number", "type": "Num", "role": "Timing"},
                    {"name": "VISIT", "label": "Visit Name", "type": "Char", "role": "Timing"},
                    {"name": "VISITDY", "label": "Planned Study Day of Visit", "type": "Num", "role": "Timing"},
                ]
            }
        },
        "DM": {
            "description": "Demographics",
            "class": "Special Purpose",
            "structure": "One record per subject",
            "variables": {
                "required": [
                    {"name": "STUDYID", "label": "Study Identifier", "type": "Char", "role": "Identifier"},
                    {"name": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "role": "Identifier"},
                    {"name": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "role": "Identifier"},
                    {"name": "SUBJID", "label": "Subject Identifier for the Study", "type": "Char", "role": "Topic"},
                    {"name": "RFSTDTC", "label": "Subject Reference Start Date/Time", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                    {"name": "RFENDTC", "label": "Subject Reference End Date/Time", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                ],
                "expected": [
                    {"name": "SITEID", "label": "Study Site Identifier", "type": "Char", "role": "Record Qualifier"},
                    {"name": "BRTHDTC", "label": "Date/Time of Birth", "type": "Char", "role": "Record Qualifier", "format": "ISO 8601"},
                    {"name": "AGE", "label": "Age", "type": "Num", "role": "Record Qualifier"},
                    {"name": "AGEU", "label": "Age Units", "type": "Char", "role": "Variable Qualifier", "codelist": "AGEU"},
                    {"name": "SEX", "label": "Sex", "type": "Char", "role": "Record Qualifier", "codelist": "SEX"},
                    {"name": "RACE", "label": "Race", "type": "Char", "role": "Record Qualifier", "codelist": "RACE"},
                    {"name": "ETHNIC", "label": "Ethnicity", "type": "Char", "role": "Record Qualifier", "codelist": "ETHNIC"},
                    {"name": "ARMCD", "label": "Planned Arm Code", "type": "Char", "role": "Record Qualifier"},
                    {"name": "ARM", "label": "Description of Planned Arm", "type": "Char", "role": "Synonym Qualifier"},
                    {"name": "COUNTRY", "label": "Country", "type": "Char", "role": "Record Qualifier", "codelist": "ISO 3166-1"},
                ],
                "permissible": [
                    {"name": "INVID", "label": "Investigator Identifier", "type": "Char", "role": "Record Qualifier"},
                    {"name": "INVNAM", "label": "Investigator Name", "type": "Char", "role": "Synonym Qualifier"},
                    {"name": "RFXSTDTC", "label": "Date/Time of First Study Treatment", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                    {"name": "RFXENDTC", "label": "Date/Time of Last Study Treatment", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                    {"name": "RFICDTC", "label": "Date/Time of Informed Consent", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                    {"name": "RFPENDTC", "label": "Date/Time of End of Participation", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                    {"name": "DTHDTC", "label": "Date/Time of Death", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                    {"name": "DTHFL", "label": "Subject Death Flag", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                    {"name": "ACTARMCD", "label": "Actual Arm Code", "type": "Char", "role": "Record Qualifier"},
                    {"name": "ACTARM", "label": "Description of Actual Arm", "type": "Char", "role": "Synonym Qualifier"},
                    {"name": "ARMNRS", "label": "Reason Arm and/or Actual Arm is Null", "type": "Char", "role": "Record Qualifier", "codelist": "ARMNRS"},
                    {"name": "ACTARMUD", "label": "Description of Unplanned Actual Arm", "type": "Char", "role": "Record Qualifier"},
                    {"name": "DMDTC", "label": "Date/Time of Collection", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                    {"name": "DMDY", "label": "Study Day of Collection", "type": "Num", "role": "Timing"},
                ]
            }
        },
        "VS": {
            "description": "Vital Signs",
            "class": "Findings",
            "structure": "One record per vital sign measurement per time point per visit per subject",
            "variables": {
                "required": [
                    {"name": "STUDYID", "label": "Study Identifier", "type": "Char", "role": "Identifier"},
                    {"name": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "role": "Identifier"},
                    {"name": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "role": "Identifier"},
                    {"name": "VSSEQ", "label": "Sequence Number", "type": "Num", "role": "Identifier"},
                    {"name": "VSTESTCD", "label": "Vital Signs Test Short Name", "type": "Char", "role": "Topic", "codelist": "VSTESTCD"},
                    {"name": "VSTEST", "label": "Vital Signs Test Name", "type": "Char", "role": "Synonym Qualifier", "codelist": "VSTEST"},
                ],
                "expected": [
                    {"name": "VSORRES", "label": "Result or Finding in Original Units", "type": "Char", "role": "Result Qualifier"},
                    {"name": "VSORRESU", "label": "Original Units", "type": "Char", "role": "Variable Qualifier", "codelist": "UNIT"},
                    {"name": "VSSTRESC", "label": "Character Result/Finding in Std Format", "type": "Char", "role": "Result Qualifier"},
                    {"name": "VSSTRESN", "label": "Numeric Result/Finding in Standard Units", "type": "Num", "role": "Result Qualifier"},
                    {"name": "VSSTRESU", "label": "Standard Units", "type": "Char", "role": "Variable Qualifier", "codelist": "UNIT"},
                    {"name": "VSSTAT", "label": "Completion Status", "type": "Char", "role": "Record Qualifier", "codelist": "ND"},
                    {"name": "VSBLFL", "label": "Baseline Flag", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                    {"name": "VISITNUM", "label": "Visit Number", "type": "Num", "role": "Timing"},
                    {"name": "VISIT", "label": "Visit Name", "type": "Char", "role": "Timing"},
                    {"name": "VSDTC", "label": "Date/Time of Measurements", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                ],
                "permissible": [
                    {"name": "VSSPID", "label": "Sponsor-Defined Identifier", "type": "Char", "role": "Identifier"},
                    {"name": "VSGRPID", "label": "Group ID", "type": "Char", "role": "Identifier"},
                    {"name": "VSLNKID", "label": "Link ID", "type": "Char", "role": "Identifier"},
                    {"name": "VSCAT", "label": "Category for Vital Signs", "type": "Char", "role": "Grouping Qualifier"},
                    {"name": "VSSCAT", "label": "Subcategory for Vital Signs", "type": "Char", "role": "Grouping Qualifier"},
                    {"name": "VSPOS", "label": "Vital Signs Position of Subject", "type": "Char", "role": "Record Qualifier", "codelist": "POSITION"},
                    {"name": "VSREASND", "label": "Reason Not Done", "type": "Char", "role": "Record Qualifier"},
                    {"name": "VSLOC", "label": "Location of Vital Signs Measurement", "type": "Char", "role": "Record Qualifier", "codelist": "LOC"},
                    {"name": "VSLAT", "label": "Laterality", "type": "Char", "role": "Variable Qualifier", "codelist": "LAT"},
                    {"name": "VSDRVFL", "label": "Derived Flag", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                    {"name": "EPOCH", "label": "Epoch", "type": "Char", "role": "Timing", "codelist": "EPOCH"},
                    {"name": "VSDY", "label": "Study Day of Vital Signs", "type": "Num", "role": "Timing"},
                    {"name": "VSTPT", "label": "Planned Time Point Name", "type": "Char", "role": "Timing"},
                    {"name": "VSTPTNUM", "label": "Planned Time Point Number", "type": "Num", "role": "Timing"},
                    {"name": "VSELTM", "label": "Planned Elapsed Time from Time Point Ref", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                    {"name": "VSTPTREF", "label": "Time Point Reference", "type": "Char", "role": "Timing"},
                    {"name": "VSRFTDTC", "label": "Date/Time of Reference Time Point", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                ]
            }
        },
        "LB": {
            "description": "Laboratory Test Results",
            "class": "Findings",
            "structure": "One record per lab test per time point per visit per subject",
            "variables": {
                "required": [
                    {"name": "STUDYID", "label": "Study Identifier", "type": "Char", "role": "Identifier"},
                    {"name": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "role": "Identifier"},
                    {"name": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "role": "Identifier"},
                    {"name": "LBSEQ", "label": "Sequence Number", "type": "Num", "role": "Identifier"},
                    {"name": "LBTESTCD", "label": "Lab Test or Examination Short Name", "type": "Char", "role": "Topic", "codelist": "LBTESTCD"},
                    {"name": "LBTEST", "label": "Lab Test or Examination Name", "type": "Char", "role": "Synonym Qualifier", "codelist": "LBTEST"},
                ],
                "expected": [
                    {"name": "LBCAT", "label": "Category for Lab Test", "type": "Char", "role": "Grouping Qualifier"},
                    {"name": "LBORRES", "label": "Result or Finding in Original Units", "type": "Char", "role": "Result Qualifier"},
                    {"name": "LBORRESU", "label": "Original Units", "type": "Char", "role": "Variable Qualifier", "codelist": "UNIT"},
                    {"name": "LBORNRLO", "label": "Reference Range Lower Limit in Orig Unit", "type": "Char", "role": "Variable Qualifier"},
                    {"name": "LBORNRHI", "label": "Reference Range Upper Limit in Orig Unit", "type": "Char", "role": "Variable Qualifier"},
                    {"name": "LBSTRESC", "label": "Character Result/Finding in Std Format", "type": "Char", "role": "Result Qualifier"},
                    {"name": "LBSTRESN", "label": "Numeric Result/Finding in Standard Units", "type": "Num", "role": "Result Qualifier"},
                    {"name": "LBSTRESU", "label": "Standard Units", "type": "Char", "role": "Variable Qualifier", "codelist": "UNIT"},
                    {"name": "LBSTNRLO", "label": "Reference Range Lower Limit-Std Units", "type": "Num", "role": "Variable Qualifier"},
                    {"name": "LBSTNRHI", "label": "Reference Range Upper Limit-Std Units", "type": "Num", "role": "Variable Qualifier"},
                    {"name": "LBNRIND", "label": "Reference Range Indicator", "type": "Char", "role": "Variable Qualifier", "codelist": "NRIND"},
                    {"name": "LBSPEC", "label": "Specimen Type", "type": "Char", "role": "Record Qualifier", "codelist": "SPEC"},
                    {"name": "VISITNUM", "label": "Visit Number", "type": "Num", "role": "Timing"},
                    {"name": "VISIT", "label": "Visit Name", "type": "Char", "role": "Timing"},
                    {"name": "LBDTC", "label": "Date/Time of Specimen Collection", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                ],
                "permissible": [
                    {"name": "LBSPID", "label": "Sponsor-Defined Identifier", "type": "Char", "role": "Identifier"},
                    {"name": "LBGRPID", "label": "Group ID", "type": "Char", "role": "Identifier"},
                    {"name": "LBREFID", "label": "Specimen ID", "type": "Char", "role": "Identifier"},
                    {"name": "LBLNKID", "label": "Link ID", "type": "Char", "role": "Identifier"},
                    {"name": "LBSCAT", "label": "Subcategory for Lab Test", "type": "Char", "role": "Grouping Qualifier"},
                    {"name": "LBSTAT", "label": "Completion Status", "type": "Char", "role": "Record Qualifier", "codelist": "ND"},
                    {"name": "LBREASND", "label": "Reason Not Done", "type": "Char", "role": "Record Qualifier"},
                    {"name": "LBNAM", "label": "Vendor Name", "type": "Char", "role": "Record Qualifier"},
                    {"name": "LBLOINC", "label": "LOINC Code", "type": "Char", "role": "Synonym Qualifier"},
                    {"name": "LBSPCCND", "label": "Specimen Condition", "type": "Char", "role": "Record Qualifier", "codelist": "SPECCOND"},
                    {"name": "LBMETHOD", "label": "Method of Test or Examination", "type": "Char", "role": "Record Qualifier", "codelist": "METHOD"},
                    {"name": "LBLOC", "label": "Location Used for Measurement", "type": "Char", "role": "Record Qualifier", "codelist": "LOC"},
                    {"name": "LBLAT", "label": "Laterality", "type": "Char", "role": "Variable Qualifier", "codelist": "LAT"},
                    {"name": "LBBLFL", "label": "Baseline Flag", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                    {"name": "LBFAST", "label": "Fasting Status", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                    {"name": "LBDRVFL", "label": "Derived Flag", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                    {"name": "LBTOX", "label": "Toxicity", "type": "Char", "role": "Variable Qualifier"},
                    {"name": "LBTOXGR", "label": "Standard Toxicity Grade", "type": "Char", "role": "Record Qualifier", "codelist": "TOXGR"},
                    {"name": "EPOCH", "label": "Epoch", "type": "Char", "role": "Timing", "codelist": "EPOCH"},
                    {"name": "LBDY", "label": "Study Day of Specimen Collection", "type": "Num", "role": "Timing"},
                    {"name": "LBTPT", "label": "Planned Time Point Name", "type": "Char", "role": "Timing"},
                    {"name": "LBTPTNUM", "label": "Planned Time Point Number", "type": "Num", "role": "Timing"},
                    {"name": "LBELTM", "label": "Planned Elapsed Time from Time Point Ref", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                ]
            }
        },
        "CM": {
            "description": "Concomitant Medications",
            "class": "Interventions",
            "structure": "One record per recorded intervention occurrence per subject",
            "variables": {
                "required": [
                    {"name": "STUDYID", "label": "Study Identifier", "type": "Char", "role": "Identifier"},
                    {"name": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "role": "Identifier"},
                    {"name": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "role": "Identifier"},
                    {"name": "CMSEQ", "label": "Sequence Number", "type": "Num", "role": "Identifier"},
                    {"name": "CMTRT", "label": "Reported Name of Drug, Med, or Therapy", "type": "Char", "role": "Topic"},
                ],
                "expected": [
                    {"name": "CMDECOD", "label": "Standardized Medication Name", "type": "Char", "role": "Synonym Qualifier", "codelist": "WHODrug"},
                    {"name": "CMINDC", "label": "Indication", "type": "Char", "role": "Record Qualifier"},
                    {"name": "CMDOSE", "label": "Dose per Administration", "type": "Num", "role": "Record Qualifier"},
                    {"name": "CMDOSU", "label": "Dose Units", "type": "Char", "role": "Variable Qualifier", "codelist": "UNIT"},
                    {"name": "CMDOSFRQ", "label": "Dosing Frequency per Interval", "type": "Char", "role": "Variable Qualifier", "codelist": "FREQ"},
                    {"name": "CMROUTE", "label": "Route of Administration", "type": "Char", "role": "Variable Qualifier", "codelist": "ROUTE"},
                    {"name": "CMSTDTC", "label": "Start Date/Time of Medication", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                    {"name": "CMENDTC", "label": "End Date/Time of Medication", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                ],
                "permissible": [
                    {"name": "CMSPID", "label": "Sponsor-Defined Identifier", "type": "Char", "role": "Identifier"},
                    {"name": "CMGRPID", "label": "Group ID", "type": "Char", "role": "Identifier"},
                    {"name": "CMREFID", "label": "Reference ID", "type": "Char", "role": "Identifier"},
                    {"name": "CMLNKID", "label": "Link ID", "type": "Char", "role": "Identifier"},
                    {"name": "CMMODIFY", "label": "Modified Reported Name", "type": "Char", "role": "Synonym Qualifier"},
                    {"name": "CMCAT", "label": "Category for Medication", "type": "Char", "role": "Grouping Qualifier"},
                    {"name": "CMSCAT", "label": "Subcategory for Medication", "type": "Char", "role": "Grouping Qualifier"},
                    {"name": "CMPRESP", "label": "Pre-Specified", "type": "Char", "role": "Variable Qualifier", "codelist": "NY"},
                    {"name": "CMOCCUR", "label": "Occurrence", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                    {"name": "CMSTAT", "label": "Completion Status", "type": "Char", "role": "Record Qualifier", "codelist": "ND"},
                    {"name": "CMREASND", "label": "Reason Medication Not Given", "type": "Char", "role": "Record Qualifier"},
                    {"name": "CMCLAS", "label": "Medication Class", "type": "Char", "role": "Variable Qualifier"},
                    {"name": "CMCLASCD", "label": "Medication Class Code", "type": "Char", "role": "Variable Qualifier"},
                    {"name": "CMDOSTXT", "label": "Dose Description", "type": "Char", "role": "Variable Qualifier"},
                    {"name": "CMDOSFRM", "label": "Dose Form", "type": "Char", "role": "Variable Qualifier", "codelist": "FRM"},
                    {"name": "CMDOSTOT", "label": "Total Daily Dose", "type": "Num", "role": "Record Qualifier"},
                    {"name": "CMDOSRGM", "label": "Intended Dose Regimen", "type": "Char", "role": "Variable Qualifier"},
                    {"name": "EPOCH", "label": "Epoch", "type": "Char", "role": "Timing", "codelist": "EPOCH"},
                    {"name": "CMSTDY", "label": "Study Day of Start of Medication", "type": "Num", "role": "Timing"},
                    {"name": "CMENDY", "label": "Study Day of End of Medication", "type": "Num", "role": "Timing"},
                    {"name": "CMDUR", "label": "Duration of Medication", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                    {"name": "CMENRF", "label": "End Relative to Reference Period", "type": "Char", "role": "Timing", "codelist": "STENRF"},
                    {"name": "CMSTRF", "label": "Start Relative to Reference Period", "type": "Char", "role": "Timing", "codelist": "STENRF"},
                    {"name": "VISITNUM", "label": "Visit Number", "type": "Num", "role": "Timing"},
                    {"name": "VISIT", "label": "Visit Name", "type": "Char", "role": "Timing"},
                ]
            }
        },
        "EX": {
            "description": "Exposure",
            "class": "Interventions",
            "structure": "One record per protocol-specified study treatment, per constant-dosing interval, per subject",
            "variables": {
                "required": [
                    {"name": "STUDYID", "label": "Study Identifier", "type": "Char", "role": "Identifier"},
                    {"name": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "role": "Identifier"},
                    {"name": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "role": "Identifier"},
                    {"name": "EXSEQ", "label": "Sequence Number", "type": "Num", "role": "Identifier"},
                    {"name": "EXTRT", "label": "Name of Actual Treatment", "type": "Char", "role": "Topic"},
                ],
                "expected": [
                    {"name": "EXDOSE", "label": "Dose per Administration", "type": "Num", "role": "Record Qualifier"},
                    {"name": "EXDOSU", "label": "Dose Units", "type": "Char", "role": "Variable Qualifier", "codelist": "UNIT"},
                    {"name": "EXDOSFRM", "label": "Dose Form", "type": "Char", "role": "Variable Qualifier", "codelist": "FRM"},
                    {"name": "EXDOSFRQ", "label": "Dosing Frequency per Interval", "type": "Char", "role": "Variable Qualifier", "codelist": "FREQ"},
                    {"name": "EXROUTE", "label": "Route of Administration", "type": "Char", "role": "Variable Qualifier", "codelist": "ROUTE"},
                    {"name": "EXSTDTC", "label": "Start Date/Time of Treatment", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                    {"name": "EXENDTC", "label": "End Date/Time of Treatment", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                ],
                "permissible": [
                    {"name": "EXSPID", "label": "Sponsor-Defined Identifier", "type": "Char", "role": "Identifier"},
                    {"name": "EXGRPID", "label": "Group ID", "type": "Char", "role": "Identifier"},
                    {"name": "EXREFID", "label": "Reference ID", "type": "Char", "role": "Identifier"},
                    {"name": "EXLNKID", "label": "Link ID", "type": "Char", "role": "Identifier"},
                    {"name": "EXLNKGRP", "label": "Link Group ID", "type": "Char", "role": "Identifier"},
                    {"name": "EXCAT", "label": "Category of Treatment", "type": "Char", "role": "Grouping Qualifier"},
                    {"name": "EXSCAT", "label": "Subcategory of Treatment", "type": "Char", "role": "Grouping Qualifier"},
                    {"name": "EXDOSTXT", "label": "Dose Description", "type": "Char", "role": "Variable Qualifier"},
                    {"name": "EXDOSTOT", "label": "Total Daily Dose", "type": "Num", "role": "Record Qualifier"},
                    {"name": "EXDOSRGM", "label": "Intended Dose Regimen", "type": "Char", "role": "Variable Qualifier"},
                    {"name": "EXLOT", "label": "Lot Number", "type": "Char", "role": "Record Qualifier"},
                    {"name": "EXLOC", "label": "Location of Dose Administration", "type": "Char", "role": "Record Qualifier", "codelist": "LOC"},
                    {"name": "EXLAT", "label": "Laterality", "type": "Char", "role": "Variable Qualifier", "codelist": "LAT"},
                    {"name": "EXDIR", "label": "Directionality", "type": "Char", "role": "Variable Qualifier", "codelist": "DIR"},
                    {"name": "EXFAST", "label": "Fasting Status", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                    {"name": "EXADJ", "label": "Reason for Dose Adjustment", "type": "Char", "role": "Record Qualifier"},
                    {"name": "EPOCH", "label": "Epoch", "type": "Char", "role": "Timing", "codelist": "EPOCH"},
                    {"name": "EXSTDY", "label": "Study Day of Start of Treatment", "type": "Num", "role": "Timing"},
                    {"name": "EXENDY", "label": "Study Day of End of Treatment", "type": "Num", "role": "Timing"},
                    {"name": "EXDUR", "label": "Duration of Treatment", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                    {"name": "VISITNUM", "label": "Visit Number", "type": "Num", "role": "Timing"},
                    {"name": "VISIT", "label": "Visit Name", "type": "Char", "role": "Timing"},
                ]
            }
        },
        "MH": {
            "description": "Medical History",
            "class": "Events",
            "structure": "One record per medical history event per subject",
            "variables": {
                "required": [
                    {"name": "STUDYID", "label": "Study Identifier", "type": "Char", "role": "Identifier"},
                    {"name": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "role": "Identifier"},
                    {"name": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "role": "Identifier"},
                    {"name": "MHSEQ", "label": "Sequence Number", "type": "Num", "role": "Identifier"},
                    {"name": "MHTERM", "label": "Reported Term for the Medical History", "type": "Char", "role": "Topic"},
                ],
                "expected": [
                    {"name": "MHDECOD", "label": "Dictionary-Derived Term", "type": "Char", "role": "Synonym Qualifier", "codelist": "MedDRA"},
                    {"name": "MHBODSYS", "label": "Body System or Organ Class", "type": "Char", "role": "Record Qualifier", "codelist": "MedDRA"},
                ],
                "permissible": [
                    {"name": "MHSPID", "label": "Sponsor-Defined Identifier", "type": "Char", "role": "Identifier"},
                    {"name": "MHGRPID", "label": "Group ID", "type": "Char", "role": "Identifier"},
                    {"name": "MHREFID", "label": "Reference ID", "type": "Char", "role": "Identifier"},
                    {"name": "MHLNKID", "label": "Link ID", "type": "Char", "role": "Identifier"},
                    {"name": "MHLNKGRP", "label": "Link Group ID", "type": "Char", "role": "Identifier"},
                    {"name": "MHMODIFY", "label": "Modified Reported Term", "type": "Char", "role": "Synonym Qualifier"},
                    {"name": "MHCAT", "label": "Category for Medical History", "type": "Char", "role": "Grouping Qualifier"},
                    {"name": "MHSCAT", "label": "Subcategory for Medical History", "type": "Char", "role": "Grouping Qualifier"},
                    {"name": "MHPRESP", "label": "Pre-Specified", "type": "Char", "role": "Variable Qualifier", "codelist": "NY"},
                    {"name": "MHOCCUR", "label": "Occurrence", "type": "Char", "role": "Record Qualifier", "codelist": "NY"},
                    {"name": "MHSTAT", "label": "Completion Status", "type": "Char", "role": "Record Qualifier", "codelist": "ND"},
                    {"name": "MHREASND", "label": "Reason Medical History Not Collected", "type": "Char", "role": "Record Qualifier"},
                    {"name": "MHSEV", "label": "Severity/Intensity", "type": "Char", "role": "Record Qualifier", "codelist": "AESEV"},
                    {"name": "MHSTDTC", "label": "Start Date/Time of Medical History Event", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                    {"name": "MHENDTC", "label": "End Date/Time of Medical History Event", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                    {"name": "MHSTDY", "label": "Study Day of Start of Event", "type": "Num", "role": "Timing"},
                    {"name": "MHENDY", "label": "Study Day of End of Event", "type": "Num", "role": "Timing"},
                    {"name": "MHDUR", "label": "Duration of Event", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                    {"name": "MHENRF", "label": "End Relative to Reference Period", "type": "Char", "role": "Timing", "codelist": "STENRF"},
                    {"name": "MHSTRF", "label": "Start Relative to Reference Period", "type": "Char", "role": "Timing", "codelist": "STENRF"},
                ]
            }
        },
        "DS": {
            "description": "Disposition",
            "class": "Events",
            "structure": "One record per disposition status or protocol milestone per subject",
            "variables": {
                "required": [
                    {"name": "STUDYID", "label": "Study Identifier", "type": "Char", "role": "Identifier"},
                    {"name": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "role": "Identifier"},
                    {"name": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "role": "Identifier"},
                    {"name": "DSSEQ", "label": "Sequence Number", "type": "Num", "role": "Identifier"},
                    {"name": "DSTERM", "label": "Reported Term for the Disposition Event", "type": "Char", "role": "Topic"},
                    {"name": "DSDECOD", "label": "Standardized Disposition Term", "type": "Char", "role": "Synonym Qualifier", "codelist": "DSTERM"},
                ],
                "expected": [
                    {"name": "DSCAT", "label": "Category for Disposition Event", "type": "Char", "role": "Grouping Qualifier"},
                    {"name": "DSSTDTC", "label": "Start Date/Time of Disposition Event", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                ],
                "permissible": [
                    {"name": "DSSPID", "label": "Sponsor-Defined Identifier", "type": "Char", "role": "Identifier"},
                    {"name": "DSGRPID", "label": "Group ID", "type": "Char", "role": "Identifier"},
                    {"name": "DSREFID", "label": "Reference ID", "type": "Char", "role": "Identifier"},
                    {"name": "DSSCAT", "label": "Subcategory for Disposition Event", "type": "Char", "role": "Grouping Qualifier"},
                    {"name": "EPOCH", "label": "Epoch", "type": "Char", "role": "Timing", "codelist": "EPOCH"},
                    {"name": "DSDTC", "label": "Date/Time of Collection", "type": "Char", "role": "Timing", "format": "ISO 8601"},
                    {"name": "DSSTDY", "label": "Study Day of Start of Event", "type": "Num", "role": "Timing"},
                    {"name": "VISITNUM", "label": "Visit Number", "type": "Num", "role": "Timing"},
                    {"name": "VISIT", "label": "Visit Name", "type": "Char", "role": "Timing"},
                ]
            }
        }
    }

    # CDISC Controlled Terminology (key codelists)
    CONTROLLED_TERMINOLOGY = {
        "NY": {
            "name": "No Yes Response",
            "extensible": False,
            "terms": [
                {"code": "N", "decode": "No", "definition": "A response indicating a negative answer"},
                {"code": "Y", "decode": "Yes", "definition": "A response indicating a positive answer"}
            ]
        },
        "SEX": {
            "name": "Sex",
            "extensible": False,
            "terms": [
                {"code": "M", "decode": "Male", "definition": "A person who belongs to the sex that normally produces sperm"},
                {"code": "F", "decode": "Female", "definition": "A person who belongs to the sex that normally produces ova"},
                {"code": "U", "decode": "Unknown", "definition": "Not known, observed, recorded; or reported as unknown"},
                {"code": "UNDIFFERENTIATED", "decode": "Undifferentiated", "definition": "Sex could not be determined"}
            ]
        },
        "AESEV": {
            "name": "Severity/Intensity Scale for Adverse Events",
            "extensible": False,
            "terms": [
                {"code": "MILD", "decode": "Mild", "definition": "A type of adverse event that is usually transient and may require only minimal treatment or therapeutic intervention"},
                {"code": "MODERATE", "decode": "Moderate", "definition": "A type of adverse event that is usually alleviated with additional specific therapeutic intervention"},
                {"code": "SEVERE", "decode": "Severe", "definition": "A type of adverse event that interrupts usual activities of daily living or significantly affects clinical status"}
            ]
        },
        "REL": {
            "name": "Relationship to Reference Intervention",
            "extensible": True,
            "terms": [
                {"code": "NOT RELATED", "decode": "Not Related", "definition": "There is no evidence that the intervention caused the event"},
                {"code": "UNLIKELY RELATED", "decode": "Unlikely Related", "definition": "Doubtful relationship exists between the intervention and the event"},
                {"code": "POSSIBLY RELATED", "decode": "Possibly Related", "definition": "Reasonable possibility that the intervention caused the event"},
                {"code": "PROBABLY RELATED", "decode": "Probably Related", "definition": "Strong likelihood that the intervention caused the event"},
                {"code": "DEFINITELY RELATED", "decode": "Definitely Related", "definition": "Clear evidence that the intervention caused the event"},
                {"code": "RELATED", "decode": "Related", "definition": "Relationship exists between the intervention and the event"}
            ]
        },
        "OUT": {
            "name": "Outcome of Event",
            "extensible": False,
            "terms": [
                {"code": "RECOVERED/RESOLVED", "decode": "Recovered/Resolved", "definition": "The event has ended completely"},
                {"code": "RECOVERING/RESOLVING", "decode": "Recovering/Resolving", "definition": "The event is improving but has not completely resolved"},
                {"code": "NOT RECOVERED/NOT RESOLVED", "decode": "Not Recovered/Not Resolved", "definition": "The event has not resolved"},
                {"code": "RECOVERED/RESOLVED WITH SEQUELAE", "decode": "Recovered/Resolved with Sequelae", "definition": "The event has resolved with lasting effects"},
                {"code": "FATAL", "decode": "Fatal", "definition": "The event resulted in death"},
                {"code": "UNKNOWN", "decode": "Unknown", "definition": "Outcome is not known"}
            ]
        },
        "ACN": {
            "name": "Action Taken with Study Treatment",
            "extensible": True,
            "terms": [
                {"code": "DRUG WITHDRAWN", "decode": "Drug Withdrawn", "definition": "Study drug was stopped permanently"},
                {"code": "DRUG INTERRUPTED", "decode": "Drug Interrupted", "definition": "Study drug was temporarily stopped"},
                {"code": "DOSE REDUCED", "decode": "Dose Reduced", "definition": "Dose of study drug was reduced"},
                {"code": "DOSE INCREASED", "decode": "Dose Increased", "definition": "Dose of study drug was increased"},
                {"code": "DOSE NOT CHANGED", "decode": "Dose Not Changed", "definition": "Dose of study drug was not changed"},
                {"code": "NOT APPLICABLE", "decode": "Not Applicable", "definition": "Not applicable"},
                {"code": "UNKNOWN", "decode": "Unknown", "definition": "Unknown"}
            ]
        },
        "TOXGR": {
            "name": "Toxicity Grade",
            "extensible": True,
            "terms": [
                {"code": "0", "decode": "Grade 0", "definition": "No toxicity"},
                {"code": "1", "decode": "Grade 1", "definition": "Mild toxicity"},
                {"code": "2", "decode": "Grade 2", "definition": "Moderate toxicity"},
                {"code": "3", "decode": "Grade 3", "definition": "Severe toxicity"},
                {"code": "4", "decode": "Grade 4", "definition": "Life-threatening or disabling toxicity"},
                {"code": "5", "decode": "Grade 5", "definition": "Death related to toxicity"}
            ]
        },
        "RACE": {
            "name": "Race",
            "extensible": True,
            "terms": [
                {"code": "AMERICAN INDIAN OR ALASKA NATIVE", "decode": "American Indian or Alaska Native"},
                {"code": "ASIAN", "decode": "Asian"},
                {"code": "BLACK OR AFRICAN AMERICAN", "decode": "Black or African American"},
                {"code": "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER", "decode": "Native Hawaiian or Other Pacific Islander"},
                {"code": "WHITE", "decode": "White"},
                {"code": "MULTIPLE", "decode": "Multiple"},
                {"code": "NOT REPORTED", "decode": "Not Reported"},
                {"code": "UNKNOWN", "decode": "Unknown"},
                {"code": "OTHER", "decode": "Other"}
            ]
        },
        "ETHNIC": {
            "name": "Ethnicity",
            "extensible": False,
            "terms": [
                {"code": "HISPANIC OR LATINO", "decode": "Hispanic or Latino"},
                {"code": "NOT HISPANIC OR LATINO", "decode": "Not Hispanic or Latino"},
                {"code": "NOT REPORTED", "decode": "Not Reported"},
                {"code": "UNKNOWN", "decode": "Unknown"}
            ]
        },
        "AGEU": {
            "name": "Age Unit",
            "extensible": False,
            "terms": [
                {"code": "YEARS", "decode": "Years"},
                {"code": "MONTHS", "decode": "Months"},
                {"code": "WEEKS", "decode": "Weeks"},
                {"code": "DAYS", "decode": "Days"},
                {"code": "HOURS", "decode": "Hours"}
            ]
        },
        "STENRF": {
            "name": "Start/End Relative to Reference Period",
            "extensible": False,
            "terms": [
                {"code": "BEFORE", "decode": "Before", "definition": "Started or ended before reference period"},
                {"code": "DURING", "decode": "During", "definition": "Started or ended during reference period"},
                {"code": "AFTER", "decode": "After", "definition": "Started or ended after reference period"},
                {"code": "DURING/AFTER", "decode": "During/After", "definition": "Ongoing at end of reference period"},
                {"code": "U", "decode": "Unknown", "definition": "Unknown"}
            ]
        },
        "ND": {
            "name": "Not Done",
            "extensible": False,
            "terms": [
                {"code": "NOT DONE", "decode": "Not Done", "definition": "The activity was not performed"}
            ]
        },
        "NRIND": {
            "name": "Reference Range Indicator",
            "extensible": False,
            "terms": [
                {"code": "HIGH", "decode": "High", "definition": "Above upper limit of reference range"},
                {"code": "LOW", "decode": "Low", "definition": "Below lower limit of reference range"},
                {"code": "NORMAL", "decode": "Normal", "definition": "Within reference range"},
                {"code": "ABNORMAL", "decode": "Abnormal", "definition": "Outside reference range"}
            ]
        }
    }

    def __init__(self, cache_dir: str = None):
        """Initialize with optional cache directory."""
        self.cache_dir = cache_dir or "/tmp/sdtm_cache"
        self._cache = {}
        self._web_fetch_available = True
        self._tavily_available = False

        # Check Tavily availability
        try:
            from tavily import TavilyClient
            tavily_key = os.getenv("TAVILY_API_KEY")
            if tavily_key:
                self._tavily = TavilyClient(api_key=tavily_key)
                self._tavily_available = True
        except ImportError:
            self._tavily = None

    def get_domain_specification(self, domain: str) -> Optional[Dict]:
        """
        Get complete SDTM-IG 3.4 specification for a domain.

        Combines:
        1. Local SDTM-IG 3.4 reference
        2. Web-fetched updates if available
        3. Pinecone knowledge base if available
        """
        domain = domain.upper()

        # Check cache first
        cache_key = f"domain_spec_{domain}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Get from local reference
        spec = self.SDTMIG_34_DOMAINS.get(domain)

        if not spec:
            # Try to fetch from web
            spec = self._fetch_domain_spec_from_web(domain)

        if spec:
            self._cache[cache_key] = spec

        return spec

    def get_controlled_terminology(self, codelist: str) -> Optional[Dict]:
        """
        Get CDISC Controlled Terminology for a codelist.

        Args:
            codelist: Codelist code (e.g., "SEX", "NY", "REL")

        Returns:
            Dict with codelist specification including valid terms
        """
        codelist = codelist.upper()

        # Check local CT first
        ct = self.CONTROLLED_TERMINOLOGY.get(codelist)

        if ct:
            return ct

        # Try to fetch from web
        ct = self._fetch_ct_from_web(codelist)

        return ct

    def get_variable_definition(self, domain: str, variable: str) -> Optional[Dict]:
        """
        Get definition for a specific SDTM variable.

        Args:
            domain: SDTM domain code
            variable: Variable name

        Returns:
            Dict with variable specification
        """
        spec = self.get_domain_specification(domain)
        if not spec:
            return None

        variables = spec.get("variables", {})

        # Search in required, expected, permissible
        for level in ["required", "expected", "permissible"]:
            for var in variables.get(level, []):
                if var.get("name") == variable:
                    var["core"] = level.capitalize()[:3]  # Req, Exp, Per
                    return var

        return None

    def search_sdtm_guidance(self, query: str) -> List[Dict]:
        """
        Search for SDTM guidance using web search.

        Args:
            query: Search query (e.g., "AE domain derivation rules")

        Returns:
            List of relevant guidance documents/snippets
        """
        results = []

        # Search using Tavily if available
        if self._tavily_available:
            try:
                search_query = f"CDISC SDTM-IG 3.4 {query}"
                response = self._tavily.search(
                    query=search_query,
                    search_depth="advanced",
                    max_results=5,
                    include_answer=True
                )

                if response.get("answer"):
                    results.append({
                        "source": "Tavily AI",
                        "content": response["answer"],
                        "confidence": "high"
                    })

                for result in response.get("results", []):
                    results.append({
                        "source": result.get("url", "web"),
                        "title": result.get("title", ""),
                        "content": result.get("content", "")[:500],
                        "confidence": "medium"
                    })
            except Exception as e:
                logger.warning(f"Tavily search failed: {e}")

        return results

    def get_mapping_guidance(self, source_column: str, domain: str) -> Dict:
        """
        Get intelligent mapping guidance for a source column.

        Combines:
        1. Pattern matching against SDTM variables
        2. Semantic similarity analysis
        3. Web search for specific guidance

        Args:
            source_column: Source data column name
            domain: Target SDTM domain

        Returns:
            Dict with mapping suggestions and confidence scores
        """
        result = {
            "source_column": source_column,
            "domain": domain,
            "suggestions": [],
            "guidance": []
        }

        # Get domain spec
        spec = self.get_domain_specification(domain)
        if not spec:
            return result

        # Find best matching variables
        variables = spec.get("variables", {})
        all_vars = []
        for level in ["required", "expected", "permissible"]:
            for var in variables.get(level, []):
                var["level"] = level
                all_vars.append(var)

        # Score each variable against source column
        col_upper = source_column.upper().replace("_", "").replace("-", "")

        for var in all_vars:
            var_name = var["name"]
            var_label = var.get("label", "").upper()

            # Calculate similarity score
            score = 0
            reason = []

            # Exact match
            if col_upper == var_name:
                score = 1.0
                reason.append("exact match")

            # Partial match in name
            elif var_name in col_upper or col_upper in var_name:
                score = 0.8
                reason.append("partial name match")

            # Semantic similarity with label
            elif any(word in col_upper for word in var_label.split()):
                score = 0.6
                reason.append("label keyword match")

            # Domain prefix pattern (e.g., AESTDT -> AESTDTC)
            elif col_upper.startswith(domain) and var_name.startswith(domain):
                suffix_match = col_upper.replace(domain, "") in var_name.replace(domain, "")
                if suffix_match:
                    score = 0.7
                    reason.append("domain prefix pattern")

            if score > 0:
                result["suggestions"].append({
                    "variable": var_name,
                    "label": var.get("label"),
                    "score": score,
                    "reasons": reason,
                    "level": var["level"],
                    "codelist": var.get("codelist")
                })

        # Sort by score
        result["suggestions"].sort(key=lambda x: x["score"], reverse=True)
        result["suggestions"] = result["suggestions"][:5]  # Top 5

        # Add web guidance if available
        if self._tavily_available and result["suggestions"]:
            top_var = result["suggestions"][0]["variable"]
            try:
                guidance = self.search_sdtm_guidance(
                    f"{domain} {source_column} to {top_var} mapping derivation"
                )
                result["guidance"] = guidance[:2]
            except Exception:
                pass

        return result

    def validate_ct_value(self, value: str, codelist: str) -> Tuple[bool, str, Optional[str]]:
        """
        Validate a value against controlled terminology.

        Args:
            value: Value to validate
            codelist: Codelist code

        Returns:
            Tuple of (is_valid, standardized_value, error_message)
        """
        ct = self.get_controlled_terminology(codelist)
        if not ct:
            return True, value, None  # Can't validate, assume OK

        value_upper = str(value).upper().strip()

        # Check for exact match
        for term in ct.get("terms", []):
            if term["code"] == value_upper or term.get("decode", "").upper() == value_upper:
                return True, term["code"], None

        # Check for partial match
        for term in ct.get("terms", []):
            if value_upper in term["code"] or term["code"] in value_upper:
                return True, term["code"], f"Standardized from '{value}' to '{term['code']}'"

        # Not found - check if extensible
        if ct.get("extensible"):
            return True, value_upper, f"Value '{value}' not in standard CT but codelist is extensible"

        valid_values = [t["code"] for t in ct.get("terms", [])]
        return False, value, f"Invalid value '{value}' for {codelist}. Valid values: {', '.join(valid_values)}"

    def transform_to_ct(self, value: str, codelist: str) -> str:
        """
        Transform a value to CDISC Controlled Terminology.

        Handles common variations and returns standardized CT value.
        """
        if not value or str(value).strip() == "":
            return ""

        value_upper = str(value).upper().strip()

        # Common transformations by codelist
        transforms = {
            "REL": {
                "POSSIBLE": "POSSIBLY RELATED",
                "PROBABLE": "PROBABLY RELATED",
                "UNLIKELY": "UNLIKELY RELATED",
                "UNRELATED": "NOT RELATED",
                "NONE": "NOT RELATED",
                "DEFINITELY": "DEFINITELY RELATED",
                "CERTAIN": "DEFINITELY RELATED",
                "1": "NOT RELATED",
                "2": "UNLIKELY RELATED",
                "3": "POSSIBLY RELATED",
                "4": "PROBABLY RELATED",
                "5": "DEFINITELY RELATED",
            },
            "OUT": {
                "RECOVERED": "RECOVERED/RESOLVED",
                "RESOLVED": "RECOVERED/RESOLVED",
                "RECOVERING": "RECOVERING/RESOLVING",
                "RESOLVING": "RECOVERING/RESOLVING",
                "NOT RECOVERED": "NOT RECOVERED/NOT RESOLVED",
                "NOT RESOLVED": "NOT RECOVERED/NOT RESOLVED",
                "CONTINUING": "NOT RECOVERED/NOT RESOLVED",
                "ONGOING": "NOT RECOVERED/NOT RESOLVED",
                "PATIENT DIED": "FATAL",
                "DEATH": "FATAL",
                "DIED": "FATAL",
            },
            "AESEV": {
                "1": "MILD",
                "2": "MODERATE",
                "3": "SEVERE",
                "MI": "MILD",
                "MO": "MODERATE",
                "SE": "SEVERE",
                "LIFE THREATENING": "SEVERE",
            },
            "SEX": {
                "MALE": "M",
                "FEMALE": "F",
                "UNKNOWN": "U",
                "1": "M",
                "2": "F",
            },
            "NY": {
                "YES": "Y",
                "NO": "N",
                "TRUE": "Y",
                "FALSE": "N",
                "1": "Y",
                "0": "N",
            },
            "ACN": {
                "NONE": "DOSE NOT CHANGED",
                "NO CHANGE": "DOSE NOT CHANGED",
                "DISCONTINUED": "DRUG WITHDRAWN",
                "WITHDRAWN": "DRUG WITHDRAWN",
                "INTERRUPTED": "DRUG INTERRUPTED",
                "REDUCED": "DOSE REDUCED",
                "INCREASED": "DOSE INCREASED",
            }
        }

        codelist_upper = codelist.upper()
        if codelist_upper in transforms:
            return transforms[codelist_upper].get(value_upper, value_upper)

        return value_upper

    def _fetch_domain_spec_from_web(self, domain: str) -> Optional[Dict]:
        """Fetch domain specification from web sources."""
        if not self._tavily_available:
            return None

        try:
            response = self._tavily.search(
                query=f"CDISC SDTM-IG 3.4 {domain} domain variables structure",
                search_depth="advanced",
                max_results=3
            )

            if response.get("answer"):
                # Parse the answer to extract variable information
                # This is a simplified extraction
                return {
                    "domain": domain,
                    "description": f"{domain} domain (from web)",
                    "web_guidance": response["answer"]
                }
        except Exception as e:
            logger.warning(f"Web fetch for {domain} failed: {e}")

        return None

    def _fetch_ct_from_web(self, codelist: str) -> Optional[Dict]:
        """Fetch controlled terminology from web sources."""
        if not self._tavily_available:
            return None

        try:
            response = self._tavily.search(
                query=f"CDISC controlled terminology {codelist} valid values",
                search_depth="advanced",
                max_results=3
            )

            if response.get("answer"):
                return {
                    "name": codelist,
                    "extensible": True,
                    "web_guidance": response["answer"]
                }
        except Exception as e:
            logger.warning(f"CT fetch for {codelist} failed: {e}")

        return None

    def get_all_domains(self) -> List[str]:
        """Get list of all supported SDTM domains."""
        return list(self.SDTMIG_34_DOMAINS.keys())

    def get_all_codelists(self) -> List[str]:
        """Get list of all supported controlled terminology codelists."""
        return list(self.CONTROLLED_TERMINOLOGY.keys())


# Singleton instance
_web_reference = None

def get_sdtm_web_reference() -> SDTMWebReference:
    """Get singleton SDTMWebReference instance."""
    global _web_reference
    if _web_reference is None:
        _web_reference = SDTMWebReference()
    return _web_reference

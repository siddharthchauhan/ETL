"""
SDTMIG Reference Module
=======================
Retrieves comprehensive SDTM Implementation Guide specifications from Pinecone.
Provides domain-specific variable definitions, derivation rules, and transformation guidance.
"""

import os
from typing import Dict, Any, List, Optional
from functools import lru_cache
from dotenv import load_dotenv
load_dotenv()

# Import clients
try:
    from pinecone import Pinecone
    from openai import OpenAI
    CLIENTS_AVAILABLE = True
except ImportError:
    CLIENTS_AVAILABLE = False


# Complete SDTMIG Domain Specifications based on SDTM IG 3.4
SDTMIG_DOMAIN_SPECS = {
    "DM": {
        "name": "Demographics",
        "description": "Demographics domain contains subject-level demographic information",
        "class": "Special Purpose",
        "structure": "One record per subject",
        "variables": [
            {"name": "STUDYID", "label": "Study Identifier", "type": "Char", "core": "Req", "role": "Identifier"},
            {"name": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "core": "Req", "role": "Identifier", "value": "DM"},
            {"name": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "core": "Req", "role": "Identifier", "derivation": "STUDYID || '-' || SITEID || '-' || SUBJID"},
            {"name": "SUBJID", "label": "Subject Identifier for the Study", "type": "Char", "core": "Req", "role": "Topic"},
            {"name": "RFSTDTC", "label": "Subject Reference Start Date/Time", "type": "Char", "core": "Exp", "role": "Record Qualifier", "format": "ISO 8601"},
            {"name": "RFENDTC", "label": "Subject Reference End Date/Time", "type": "Char", "core": "Exp", "role": "Record Qualifier", "format": "ISO 8601"},
            {"name": "RFXSTDTC", "label": "Date/Time of First Study Treatment", "type": "Char", "core": "Exp", "role": "Record Qualifier", "format": "ISO 8601"},
            {"name": "RFXENDTC", "label": "Date/Time of Last Study Treatment", "type": "Char", "core": "Exp", "role": "Record Qualifier", "format": "ISO 8601"},
            {"name": "RFICDTC", "label": "Date/Time of Informed Consent", "type": "Char", "core": "Exp", "role": "Record Qualifier", "format": "ISO 8601"},
            {"name": "RFPENDTC", "label": "Date/Time of End of Participation", "type": "Char", "core": "Exp", "role": "Record Qualifier", "format": "ISO 8601"},
            {"name": "DTHDTC", "label": "Date/Time of Death", "type": "Char", "core": "Exp", "role": "Record Qualifier", "format": "ISO 8601"},
            {"name": "DTHFL", "label": "Subject Death Flag", "type": "Char", "core": "Exp", "role": "Record Qualifier", "codelist": "NY"},
            {"name": "SITEID", "label": "Study Site Identifier", "type": "Char", "core": "Req", "role": "Record Qualifier"},
            {"name": "INVID", "label": "Investigator Identifier", "type": "Char", "core": "Perm", "role": "Record Qualifier"},
            {"name": "INVNAM", "label": "Investigator Name", "type": "Char", "core": "Perm", "role": "Synonym Qualifier"},
            {"name": "BRTHDTC", "label": "Date/Time of Birth", "type": "Char", "core": "Perm", "role": "Record Qualifier", "format": "ISO 8601"},
            {"name": "AGE", "label": "Age", "type": "Num", "core": "Exp", "role": "Record Qualifier", "derivation": "floor((RFSTDTC - BRTHDTC) / 365.25)"},
            {"name": "AGEU", "label": "Age Units", "type": "Char", "core": "Exp", "role": "Variable Qualifier", "codelist": "AGEU"},
            {"name": "SEX", "label": "Sex", "type": "Char", "core": "Req", "role": "Record Qualifier", "codelist": "SEX"},
            {"name": "RACE", "label": "Race", "type": "Char", "core": "Exp", "role": "Record Qualifier", "codelist": "RACE"},
            {"name": "ETHNIC", "label": "Ethnicity", "type": "Char", "core": "Exp", "role": "Record Qualifier", "codelist": "ETHNIC"},
            {"name": "ARMCD", "label": "Planned Arm Code", "type": "Char", "core": "Req", "role": "Record Qualifier"},
            {"name": "ARM", "label": "Description of Planned Arm", "type": "Char", "core": "Req", "role": "Synonym Qualifier"},
            {"name": "ACTARMCD", "label": "Actual Arm Code", "type": "Char", "core": "Exp", "role": "Record Qualifier"},
            {"name": "ACTARM", "label": "Description of Actual Arm", "type": "Char", "core": "Exp", "role": "Synonym Qualifier"},
            {"name": "COUNTRY", "label": "Country", "type": "Char", "core": "Req", "role": "Record Qualifier", "codelist": "ISO 3166"},
            {"name": "DMDTC", "label": "Date/Time of Collection", "type": "Char", "core": "Perm", "role": "Timing", "format": "ISO 8601"},
            {"name": "DMDY", "label": "Study Day of Collection", "type": "Num", "core": "Perm", "role": "Timing"},
        ]
    },
    "AE": {
        "name": "Adverse Events",
        "description": "Adverse Events domain captures adverse event data",
        "class": "Events",
        "structure": "One record per adverse event per subject",
        "variables": [
            {"name": "STUDYID", "label": "Study Identifier", "type": "Char", "core": "Req", "role": "Identifier"},
            {"name": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "core": "Req", "role": "Identifier", "value": "AE"},
            {"name": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "core": "Req", "role": "Identifier"},
            {"name": "AESEQ", "label": "Sequence Number", "type": "Num", "core": "Req", "role": "Identifier", "derivation": "ROW_NUMBER() per USUBJID"},
            {"name": "AESPID", "label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm", "role": "Identifier"},
            {"name": "AETERM", "label": "Reported Term for the Adverse Event", "type": "Char", "core": "Req", "role": "Topic"},
            {"name": "AEMODIFY", "label": "Modified Reported Term", "type": "Char", "core": "Perm", "role": "Synonym Qualifier"},
            {"name": "AEDECOD", "label": "Dictionary-Derived Term", "type": "Char", "core": "Exp", "role": "Synonym Qualifier"},
            {"name": "AEBODSYS", "label": "Body System or Organ Class", "type": "Char", "core": "Exp", "role": "Record Qualifier"},
            {"name": "AEBDSYCD", "label": "Body System or Organ Class Code", "type": "Num", "core": "Perm", "role": "Record Qualifier"},
            {"name": "AESOC", "label": "Primary System Organ Class", "type": "Char", "core": "Perm", "role": "Record Qualifier"},
            {"name": "AESOCCD", "label": "Primary System Organ Class Code", "type": "Num", "core": "Perm", "role": "Record Qualifier"},
            {"name": "AEHLGT", "label": "High Level Group Term", "type": "Char", "core": "Perm", "role": "Record Qualifier"},
            {"name": "AEHLGTCD", "label": "High Level Group Term Code", "type": "Num", "core": "Perm", "role": "Record Qualifier"},
            {"name": "AEHLT", "label": "High Level Term", "type": "Char", "core": "Perm", "role": "Record Qualifier"},
            {"name": "AEHLTCD", "label": "High Level Term Code", "type": "Num", "core": "Perm", "role": "Record Qualifier"},
            {"name": "AELLTCD", "label": "Lowest Level Term Code", "type": "Num", "core": "Perm", "role": "Record Qualifier"},
            {"name": "AELLT", "label": "Lowest Level Term", "type": "Char", "core": "Perm", "role": "Record Qualifier"},
            {"name": "AEPTCD", "label": "Preferred Term Code", "type": "Num", "core": "Perm", "role": "Record Qualifier"},
            {"name": "AESEV", "label": "Severity/Intensity", "type": "Char", "core": "Exp", "role": "Record Qualifier", "codelist": "AESEV"},
            {"name": "AESER", "label": "Serious Event", "type": "Char", "core": "Exp", "role": "Record Qualifier", "codelist": "NY"},
            {"name": "AEACN", "label": "Action Taken with Study Treatment", "type": "Char", "core": "Exp", "role": "Record Qualifier", "codelist": "ACN"},
            {"name": "AEACNOTH", "label": "Other Action Taken", "type": "Char", "core": "Perm", "role": "Record Qualifier"},
            {"name": "AEREL", "label": "Causality", "type": "Char", "core": "Exp", "role": "Record Qualifier", "codelist": "AEREL"},
            {"name": "AEPATT", "label": "Pattern of Adverse Event", "type": "Char", "core": "Perm", "role": "Record Qualifier"},
            {"name": "AEOUT", "label": "Outcome of Adverse Event", "type": "Char", "core": "Exp", "role": "Record Qualifier", "codelist": "OUT"},
            {"name": "AESCAN", "label": "Involves Cancer", "type": "Char", "core": "Perm", "role": "Record Qualifier", "codelist": "NY"},
            {"name": "AESCONG", "label": "Congenital Anomaly or Birth Defect", "type": "Char", "core": "Perm", "role": "Record Qualifier", "codelist": "NY"},
            {"name": "AESDISAB", "label": "Persist or Signif Disability/Incapacity", "type": "Char", "core": "Perm", "role": "Record Qualifier", "codelist": "NY"},
            {"name": "AESDTH", "label": "Results in Death", "type": "Char", "core": "Perm", "role": "Record Qualifier", "codelist": "NY"},
            {"name": "AESHOSP", "label": "Requires or Prolongs Hospitalization", "type": "Char", "core": "Perm", "role": "Record Qualifier", "codelist": "NY"},
            {"name": "AESLIFE", "label": "Is Life Threatening", "type": "Char", "core": "Perm", "role": "Record Qualifier", "codelist": "NY"},
            {"name": "AESOD", "label": "Occurred with Overdose", "type": "Char", "core": "Perm", "role": "Record Qualifier", "codelist": "NY"},
            {"name": "AESMIE", "label": "Other Medically Important Serious Event", "type": "Char", "core": "Perm", "role": "Record Qualifier", "codelist": "NY"},
            {"name": "AECONTRT", "label": "Concomitant or Additional Trtmnt Given", "type": "Char", "core": "Perm", "role": "Record Qualifier", "codelist": "NY"},
            {"name": "AETOXGR", "label": "Standard Toxicity Grade", "type": "Char", "core": "Perm", "role": "Record Qualifier"},
            {"name": "EPOCH", "label": "Epoch", "type": "Char", "core": "Perm", "role": "Timing"},
            {"name": "AESTDTC", "label": "Start Date/Time of Adverse Event", "type": "Char", "core": "Exp", "role": "Timing", "format": "ISO 8601"},
            {"name": "AEENDTC", "label": "End Date/Time of Adverse Event", "type": "Char", "core": "Exp", "role": "Timing", "format": "ISO 8601"},
            {"name": "AESTDY", "label": "Study Day of Start of Adverse Event", "type": "Num", "core": "Perm", "role": "Timing"},
            {"name": "AEENDY", "label": "Study Day of End of Adverse Event", "type": "Num", "core": "Perm", "role": "Timing"},
            {"name": "AEDUR", "label": "Duration of Adverse Event", "type": "Char", "core": "Perm", "role": "Timing", "format": "ISO 8601 duration"},
            {"name": "AEENRF", "label": "End Relative to Reference Period", "type": "Char", "core": "Perm", "role": "Timing"},
            {"name": "AESTRF", "label": "Start Relative to Reference Period", "type": "Char", "core": "Perm", "role": "Timing"},
        ]
    },
    "VS": {
        "name": "Vital Signs",
        "description": "Vital Signs domain contains measurements of vital signs",
        "class": "Findings",
        "structure": "One record per vital sign measurement per time point per visit per subject",
        "variables": [
            {"name": "STUDYID", "label": "Study Identifier", "type": "Char", "core": "Req", "role": "Identifier"},
            {"name": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "core": "Req", "role": "Identifier", "value": "VS"},
            {"name": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "core": "Req", "role": "Identifier"},
            {"name": "VSSEQ", "label": "Sequence Number", "type": "Num", "core": "Req", "role": "Identifier"},
            {"name": "VSSPID", "label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm", "role": "Identifier"},
            {"name": "VSTESTCD", "label": "Vital Signs Test Short Name", "type": "Char", "core": "Req", "role": "Topic", "codelist": "VSTESTCD"},
            {"name": "VSTEST", "label": "Vital Signs Test Name", "type": "Char", "core": "Req", "role": "Synonym Qualifier", "codelist": "VSTEST"},
            {"name": "VSCAT", "label": "Category for Vital Signs", "type": "Char", "core": "Perm", "role": "Grouping Qualifier"},
            {"name": "VSSCAT", "label": "Subcategory for Vital Signs", "type": "Char", "core": "Perm", "role": "Grouping Qualifier"},
            {"name": "VSPOS", "label": "Vital Signs Position of Subject", "type": "Char", "core": "Exp", "role": "Record Qualifier", "codelist": "POSITION"},
            {"name": "VSORRES", "label": "Result or Finding in Original Units", "type": "Char", "core": "Exp", "role": "Result Qualifier"},
            {"name": "VSORRESU", "label": "Original Units", "type": "Char", "core": "Exp", "role": "Variable Qualifier", "codelist": "UNIT"},
            {"name": "VSSTRESC", "label": "Character Result/Finding in Std Format", "type": "Char", "core": "Exp", "role": "Result Qualifier"},
            {"name": "VSSTRESN", "label": "Numeric Result/Finding in Standard Units", "type": "Num", "core": "Exp", "role": "Result Qualifier"},
            {"name": "VSSTRESU", "label": "Standard Units", "type": "Char", "core": "Exp", "role": "Variable Qualifier", "codelist": "UNIT"},
            {"name": "VSSTAT", "label": "Completion Status", "type": "Char", "core": "Perm", "role": "Record Qualifier", "codelist": "ND"},
            {"name": "VSREASND", "label": "Reason Not Done", "type": "Char", "core": "Perm", "role": "Record Qualifier"},
            {"name": "VSLOC", "label": "Location of Vital Signs Measurement", "type": "Char", "core": "Perm", "role": "Record Qualifier", "codelist": "LOC"},
            {"name": "VSLAT", "label": "Laterality", "type": "Char", "core": "Perm", "role": "Variable Qualifier", "codelist": "LAT"},
            {"name": "VSBLFL", "label": "Baseline Flag", "type": "Char", "core": "Exp", "role": "Record Qualifier", "codelist": "NY"},
            {"name": "VSDRVFL", "label": "Derived Flag", "type": "Char", "core": "Perm", "role": "Record Qualifier", "codelist": "NY"},
            {"name": "VISITNUM", "label": "Visit Number", "type": "Num", "core": "Exp", "role": "Timing"},
            {"name": "VISIT", "label": "Visit Name", "type": "Char", "core": "Perm", "role": "Timing"},
            {"name": "VISITDY", "label": "Planned Study Day of Visit", "type": "Num", "core": "Perm", "role": "Timing"},
            {"name": "EPOCH", "label": "Epoch", "type": "Char", "core": "Perm", "role": "Timing"},
            {"name": "VSDTC", "label": "Date/Time of Measurements", "type": "Char", "core": "Exp", "role": "Timing", "format": "ISO 8601"},
            {"name": "VSDY", "label": "Study Day of Vital Signs", "type": "Num", "core": "Perm", "role": "Timing"},
            {"name": "VSTPT", "label": "Planned Time Point Name", "type": "Char", "core": "Perm", "role": "Timing"},
            {"name": "VSTPTNUM", "label": "Planned Time Point Number", "type": "Num", "core": "Perm", "role": "Timing"},
            {"name": "VSELTM", "label": "Planned Elapsed Time from Time Point Ref", "type": "Char", "core": "Perm", "role": "Timing"},
            {"name": "VSTPTREF", "label": "Time Point Reference", "type": "Char", "core": "Perm", "role": "Timing"},
        ]
    },
    "LB": {
        "name": "Laboratory Test Results",
        "description": "Laboratory Test Results domain contains laboratory test data",
        "class": "Findings",
        "structure": "One record per lab test per time point per visit per subject",
        "variables": [
            {"name": "STUDYID", "label": "Study Identifier", "type": "Char", "core": "Req", "role": "Identifier"},
            {"name": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "core": "Req", "role": "Identifier", "value": "LB"},
            {"name": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "core": "Req", "role": "Identifier"},
            {"name": "LBSEQ", "label": "Sequence Number", "type": "Num", "core": "Req", "role": "Identifier"},
            {"name": "LBSPID", "label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm", "role": "Identifier"},
            {"name": "LBTESTCD", "label": "Lab Test or Examination Short Name", "type": "Char", "core": "Req", "role": "Topic", "codelist": "LBTESTCD"},
            {"name": "LBTEST", "label": "Lab Test or Examination Name", "type": "Char", "core": "Req", "role": "Synonym Qualifier", "codelist": "LBTEST"},
            {"name": "LBCAT", "label": "Category for Lab Test", "type": "Char", "core": "Exp", "role": "Grouping Qualifier"},
            {"name": "LBSCAT", "label": "Subcategory for Lab Test", "type": "Char", "core": "Perm", "role": "Grouping Qualifier"},
            {"name": "LBORRES", "label": "Result or Finding in Original Units", "type": "Char", "core": "Exp", "role": "Result Qualifier"},
            {"name": "LBORRESU", "label": "Original Units", "type": "Char", "core": "Exp", "role": "Variable Qualifier", "codelist": "UNIT"},
            {"name": "LBORNRLO", "label": "Reference Range Lower Limit in Orig Unit", "type": "Char", "core": "Exp", "role": "Variable Qualifier"},
            {"name": "LBORNRHI", "label": "Reference Range Upper Limit in Orig Unit", "type": "Char", "core": "Exp", "role": "Variable Qualifier"},
            {"name": "LBSTRESC", "label": "Character Result/Finding in Std Format", "type": "Char", "core": "Exp", "role": "Result Qualifier"},
            {"name": "LBSTRESN", "label": "Numeric Result/Finding in Standard Units", "type": "Num", "core": "Exp", "role": "Result Qualifier"},
            {"name": "LBSTRESU", "label": "Standard Units", "type": "Char", "core": "Exp", "role": "Variable Qualifier", "codelist": "UNIT"},
            {"name": "LBSTNRLO", "label": "Reference Range Lower Limit-Std Units", "type": "Num", "core": "Exp", "role": "Variable Qualifier"},
            {"name": "LBSTNRHI", "label": "Reference Range Upper Limit-Std Units", "type": "Num", "core": "Exp", "role": "Variable Qualifier"},
            {"name": "LBSTNRC", "label": "Reference Range for Char Rslt-Std Units", "type": "Char", "core": "Perm", "role": "Variable Qualifier"},
            {"name": "LBNRIND", "label": "Reference Range Indicator", "type": "Char", "core": "Exp", "role": "Variable Qualifier", "codelist": "NRIND"},
            {"name": "LBSTAT", "label": "Completion Status", "type": "Char", "core": "Perm", "role": "Record Qualifier", "codelist": "ND"},
            {"name": "LBREASND", "label": "Reason Not Done", "type": "Char", "core": "Perm", "role": "Record Qualifier"},
            {"name": "LBNAM", "label": "Vendor Name", "type": "Char", "core": "Perm", "role": "Record Qualifier"},
            {"name": "LBSPEC", "label": "Specimen Type", "type": "Char", "core": "Exp", "role": "Record Qualifier", "codelist": "SPECTYPE"},
            {"name": "LBSPCCND", "label": "Specimen Condition", "type": "Char", "core": "Perm", "role": "Record Qualifier"},
            {"name": "LBMETHOD", "label": "Method of Test or Examination", "type": "Char", "core": "Perm", "role": "Record Qualifier", "codelist": "METHOD"},
            {"name": "LBBLFL", "label": "Baseline Flag", "type": "Char", "core": "Exp", "role": "Record Qualifier", "codelist": "NY"},
            {"name": "LBFAST", "label": "Fasting Status", "type": "Char", "core": "Perm", "role": "Record Qualifier", "codelist": "NY"},
            {"name": "LBDRVFL", "label": "Derived Flag", "type": "Char", "core": "Perm", "role": "Record Qualifier", "codelist": "NY"},
            {"name": "LBTOX", "label": "Toxicity", "type": "Char", "core": "Perm", "role": "Variable Qualifier"},
            {"name": "LBTOXGR", "label": "Standard Toxicity Grade", "type": "Char", "core": "Perm", "role": "Record Qualifier"},
            {"name": "VISITNUM", "label": "Visit Number", "type": "Num", "core": "Exp", "role": "Timing"},
            {"name": "VISIT", "label": "Visit Name", "type": "Char", "core": "Perm", "role": "Timing"},
            {"name": "VISITDY", "label": "Planned Study Day of Visit", "type": "Num", "core": "Perm", "role": "Timing"},
            {"name": "EPOCH", "label": "Epoch", "type": "Char", "core": "Perm", "role": "Timing"},
            {"name": "LBDTC", "label": "Date/Time of Specimen Collection", "type": "Char", "core": "Exp", "role": "Timing", "format": "ISO 8601"},
            {"name": "LBENDTC", "label": "End Date/Time of Specimen Collection", "type": "Char", "core": "Perm", "role": "Timing", "format": "ISO 8601"},
            {"name": "LBDY", "label": "Study Day of Specimen Collection", "type": "Num", "core": "Perm", "role": "Timing"},
            {"name": "LBTPT", "label": "Planned Time Point Name", "type": "Char", "core": "Perm", "role": "Timing"},
            {"name": "LBTPTNUM", "label": "Planned Time Point Number", "type": "Num", "core": "Perm", "role": "Timing"},
            {"name": "LBELTM", "label": "Planned Elapsed Time from Time Point Ref", "type": "Char", "core": "Perm", "role": "Timing"},
            {"name": "LBTPTREF", "label": "Time Point Reference", "type": "Char", "core": "Perm", "role": "Timing"},
        ]
    },
    "CM": {
        "name": "Concomitant Medications",
        "description": "Concomitant/Prior Medications domain contains concomitant and prior medication data",
        "class": "Interventions",
        "structure": "One record per recorded intervention occurrence per subject",
        "variables": [
            {"name": "STUDYID", "label": "Study Identifier", "type": "Char", "core": "Req", "role": "Identifier"},
            {"name": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "core": "Req", "role": "Identifier", "value": "CM"},
            {"name": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "core": "Req", "role": "Identifier"},
            {"name": "CMSEQ", "label": "Sequence Number", "type": "Num", "core": "Req", "role": "Identifier"},
            {"name": "CMSPID", "label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm", "role": "Identifier"},
            {"name": "CMTRT", "label": "Reported Name of Drug, Med, or Therapy", "type": "Char", "core": "Req", "role": "Topic"},
            {"name": "CMMODIFY", "label": "Modified Reported Name", "type": "Char", "core": "Perm", "role": "Synonym Qualifier"},
            {"name": "CMDECOD", "label": "Standardized Medication Name", "type": "Char", "core": "Exp", "role": "Synonym Qualifier"},
            {"name": "CMCAT", "label": "Category for Medication", "type": "Char", "core": "Perm", "role": "Grouping Qualifier"},
            {"name": "CMSCAT", "label": "Subcategory for Medication", "type": "Char", "core": "Perm", "role": "Grouping Qualifier"},
            {"name": "CMPRESP", "label": "CM Pre-Specified", "type": "Char", "core": "Perm", "role": "Variable Qualifier", "codelist": "NY"},
            {"name": "CMOCCUR", "label": "CM Occurrence", "type": "Char", "core": "Perm", "role": "Record Qualifier", "codelist": "NY"},
            {"name": "CMSTAT", "label": "Completion Status", "type": "Char", "core": "Perm", "role": "Record Qualifier", "codelist": "ND"},
            {"name": "CMREASND", "label": "Reason Medication Not Collected", "type": "Char", "core": "Perm", "role": "Record Qualifier"},
            {"name": "CMINDC", "label": "Indication", "type": "Char", "core": "Exp", "role": "Record Qualifier"},
            {"name": "CMCLAS", "label": "Medication Class", "type": "Char", "core": "Perm", "role": "Variable Qualifier"},
            {"name": "CMCLASCD", "label": "Medication Class Code", "type": "Char", "core": "Perm", "role": "Variable Qualifier"},
            {"name": "CMDOSE", "label": "Dose per Administration", "type": "Num", "core": "Exp", "role": "Record Qualifier"},
            {"name": "CMDOSTXT", "label": "Dose Description", "type": "Char", "core": "Perm", "role": "Record Qualifier"},
            {"name": "CMDOSU", "label": "Dose Units", "type": "Char", "core": "Exp", "role": "Variable Qualifier", "codelist": "UNIT"},
            {"name": "CMDOSFRM", "label": "Dose Form", "type": "Char", "core": "Exp", "role": "Variable Qualifier", "codelist": "FRM"},
            {"name": "CMDOSFRQ", "label": "Dosing Frequency per Interval", "type": "Char", "core": "Exp", "role": "Variable Qualifier", "codelist": "FREQ"},
            {"name": "CMDOSTOT", "label": "Total Daily Dose", "type": "Num", "core": "Perm", "role": "Record Qualifier"},
            {"name": "CMDOSRGM", "label": "Intended Dose Regimen", "type": "Char", "core": "Perm", "role": "Variable Qualifier"},
            {"name": "CMROUTE", "label": "Route of Administration", "type": "Char", "core": "Exp", "role": "Variable Qualifier", "codelist": "ROUTE"},
            {"name": "EPOCH", "label": "Epoch", "type": "Char", "core": "Perm", "role": "Timing"},
            {"name": "CMSTDTC", "label": "Start Date/Time of Medication", "type": "Char", "core": "Exp", "role": "Timing", "format": "ISO 8601"},
            {"name": "CMENDTC", "label": "End Date/Time of Medication", "type": "Char", "core": "Exp", "role": "Timing", "format": "ISO 8601"},
            {"name": "CMSTDY", "label": "Study Day of Start of Medication", "type": "Num", "core": "Perm", "role": "Timing"},
            {"name": "CMENDY", "label": "Study Day of End of Medication", "type": "Num", "core": "Perm", "role": "Timing"},
            {"name": "CMDUR", "label": "Duration of Medication", "type": "Char", "core": "Perm", "role": "Timing", "format": "ISO 8601 duration"},
            {"name": "CMSTRF", "label": "Start Relative to Reference Period", "type": "Char", "core": "Perm", "role": "Timing"},
            {"name": "CMENRF", "label": "End Relative to Reference Period", "type": "Char", "core": "Perm", "role": "Timing"},
        ]
    },
    "EX": {
        "name": "Exposure",
        "description": "Exposure domain contains study treatment exposure data",
        "class": "Interventions",
        "structure": "One record per constant-dosing interval per subject",
        "variables": [
            {"name": "STUDYID", "label": "Study Identifier", "type": "Char", "core": "Req", "role": "Identifier"},
            {"name": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "core": "Req", "role": "Identifier", "value": "EX"},
            {"name": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "core": "Req", "role": "Identifier"},
            {"name": "EXSEQ", "label": "Sequence Number", "type": "Num", "core": "Req", "role": "Identifier"},
            {"name": "EXSPID", "label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm", "role": "Identifier"},
            {"name": "EXTRT", "label": "Name of Actual Treatment", "type": "Char", "core": "Req", "role": "Topic"},
            {"name": "EXCAT", "label": "Category for Exposure", "type": "Char", "core": "Perm", "role": "Grouping Qualifier"},
            {"name": "EXSCAT", "label": "Subcategory for Exposure", "type": "Char", "core": "Perm", "role": "Grouping Qualifier"},
            {"name": "EXDOSE", "label": "Dose per Administration", "type": "Num", "core": "Exp", "role": "Record Qualifier"},
            {"name": "EXDOSTXT", "label": "Dose Description", "type": "Char", "core": "Perm", "role": "Record Qualifier"},
            {"name": "EXDOSU", "label": "Dose Units", "type": "Char", "core": "Exp", "role": "Variable Qualifier", "codelist": "UNIT"},
            {"name": "EXDOSFRM", "label": "Dose Form", "type": "Char", "core": "Exp", "role": "Variable Qualifier", "codelist": "FRM"},
            {"name": "EXDOSFRQ", "label": "Dosing Frequency per Interval", "type": "Char", "core": "Exp", "role": "Variable Qualifier", "codelist": "FREQ"},
            {"name": "EXDOSTOT", "label": "Total Daily Dose", "type": "Num", "core": "Perm", "role": "Record Qualifier"},
            {"name": "EXDOSRGM", "label": "Intended Dose Regimen", "type": "Char", "core": "Perm", "role": "Variable Qualifier"},
            {"name": "EXROUTE", "label": "Route of Administration", "type": "Char", "core": "Exp", "role": "Variable Qualifier", "codelist": "ROUTE"},
            {"name": "EXLOT", "label": "Lot Number", "type": "Char", "core": "Perm", "role": "Record Qualifier"},
            {"name": "EXLOC", "label": "Location of Dose Administration", "type": "Char", "core": "Perm", "role": "Record Qualifier", "codelist": "LOC"},
            {"name": "EXLAT", "label": "Laterality", "type": "Char", "core": "Perm", "role": "Variable Qualifier", "codelist": "LAT"},
            {"name": "EXDIR", "label": "Directionality", "type": "Char", "core": "Perm", "role": "Variable Qualifier", "codelist": "DIR"},
            {"name": "EXFAST", "label": "Fasting Status", "type": "Char", "core": "Perm", "role": "Record Qualifier", "codelist": "NY"},
            {"name": "EXADJ", "label": "Reason for Dose Adjustment", "type": "Char", "core": "Perm", "role": "Record Qualifier"},
            {"name": "EPOCH", "label": "Epoch", "type": "Char", "core": "Perm", "role": "Timing"},
            {"name": "EXSTDTC", "label": "Start Date/Time of Treatment", "type": "Char", "core": "Exp", "role": "Timing", "format": "ISO 8601"},
            {"name": "EXENDTC", "label": "End Date/Time of Treatment", "type": "Char", "core": "Exp", "role": "Timing", "format": "ISO 8601"},
            {"name": "EXSTDY", "label": "Study Day of Start of Treatment", "type": "Num", "core": "Perm", "role": "Timing"},
            {"name": "EXENDY", "label": "Study Day of End of Treatment", "type": "Num", "core": "Perm", "role": "Timing"},
            {"name": "EXDUR", "label": "Duration of Treatment", "type": "Char", "core": "Perm", "role": "Timing", "format": "ISO 8601 duration"},
        ]
    },
    "MH": {
        "name": "Medical History",
        "description": "Medical History domain contains medical history and related data",
        "class": "Events",
        "structure": "One record per medical history event per subject",
        "variables": [
            {"name": "STUDYID", "label": "Study Identifier", "type": "Char", "core": "Req", "role": "Identifier"},
            {"name": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "core": "Req", "role": "Identifier", "value": "MH"},
            {"name": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "core": "Req", "role": "Identifier"},
            {"name": "MHSEQ", "label": "Sequence Number", "type": "Num", "core": "Req", "role": "Identifier"},
            {"name": "MHSPID", "label": "Sponsor-Defined Identifier", "type": "Char", "core": "Perm", "role": "Identifier"},
            {"name": "MHTERM", "label": "Reported Term for the Medical History", "type": "Char", "core": "Req", "role": "Topic"},
            {"name": "MHMODIFY", "label": "Modified Reported Term", "type": "Char", "core": "Perm", "role": "Synonym Qualifier"},
            {"name": "MHDECOD", "label": "Dictionary-Derived Term", "type": "Char", "core": "Exp", "role": "Synonym Qualifier"},
            {"name": "MHCAT", "label": "Category for Medical History", "type": "Char", "core": "Perm", "role": "Grouping Qualifier"},
            {"name": "MHSCAT", "label": "Subcategory for Medical History", "type": "Char", "core": "Perm", "role": "Grouping Qualifier"},
            {"name": "MHPRESP", "label": "Medical History Pre-Specified", "type": "Char", "core": "Perm", "role": "Variable Qualifier", "codelist": "NY"},
            {"name": "MHOCCUR", "label": "Medical History Occurrence", "type": "Char", "core": "Perm", "role": "Record Qualifier", "codelist": "NY"},
            {"name": "MHSTAT", "label": "Completion Status", "type": "Char", "core": "Perm", "role": "Record Qualifier", "codelist": "ND"},
            {"name": "MHREASND", "label": "Reason Not Done", "type": "Char", "core": "Perm", "role": "Record Qualifier"},
            {"name": "MHBODSYS", "label": "Body System or Organ Class", "type": "Char", "core": "Exp", "role": "Record Qualifier"},
            {"name": "MHENRF", "label": "End Relative to Reference Period", "type": "Char", "core": "Perm", "role": "Record Qualifier"},
            {"name": "MHSTDTC", "label": "Start Date/Time of Medical History", "type": "Char", "core": "Perm", "role": "Timing", "format": "ISO 8601"},
            {"name": "MHENDTC", "label": "End Date/Time of Medical History", "type": "Char", "core": "Perm", "role": "Timing", "format": "ISO 8601"},
            {"name": "MHDY", "label": "Study Day of History Collection", "type": "Num", "core": "Perm", "role": "Timing"},
        ]
    },
}


class SDTMIGReference:
    """
    SDTMIG Reference class that combines local specifications with Pinecone knowledge base.
    """

    def __init__(self):
        self.pinecone_client = None
        self.openai_client = None
        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize Pinecone and OpenAI clients."""
        if not CLIENTS_AVAILABLE:
            return

        try:
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key and openai_key != "your_openai_api_key_here":
                self.openai_client = OpenAI(api_key=openai_key)

            pinecone_key = os.getenv("PINECONE_API_KEY")
            if pinecone_key:
                self.pinecone_client = Pinecone(api_key=pinecone_key)
        except Exception as e:
            print(f"  SDTMIG Reference initialization warning: {e}")

    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI."""
        if not self.openai_client:
            return []
        try:
            embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
            response = self.openai_client.embeddings.create(
                input=text,
                model=embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"  Embedding error: {e}")
            return []

    def get_domain_specification(self, domain: str) -> Dict[str, Any]:
        """
        Get comprehensive domain specification from local specs and Pinecone.

        Args:
            domain: SDTM domain code (e.g., DM, AE, VS)

        Returns:
            Complete domain specification with all variables
        """
        domain = domain.upper()

        # Start with local specification
        spec = SDTMIG_DOMAIN_SPECS.get(domain, {}).copy()

        if not spec:
            # Try to get from Pinecone
            spec = self._query_pinecone_for_domain(domain)

        return spec

    def _query_pinecone_for_domain(self, domain: str) -> Dict[str, Any]:
        """Query Pinecone for domain specification."""
        if not self.pinecone_client or not self.openai_client:
            return {}

        try:
            index = self.pinecone_client.Index("sdtmig")
            query = f"SDTM {domain} domain specification variables required expected permissible"
            embedding = self._get_embedding(query)

            if not embedding:
                return {}

            results = index.query(
                vector=embedding,
                top_k=20,
                include_metadata=True
            )

            # Parse results into domain spec
            spec = {
                "name": domain,
                "description": f"SDTM {domain} Domain",
                "variables": [],
                "source": "pinecone"
            }

            for match in results.matches:
                text = match.metadata.get("text", "")
                # Extract variable information from text
                # This is a simplified extraction - could be enhanced with NLP
                if text:
                    spec["pinecone_context"] = spec.get("pinecone_context", [])
                    spec["pinecone_context"].append({
                        "score": match.score,
                        "text": text[:500]
                    })

            return spec

        except Exception as e:
            print(f"  Pinecone query error: {e}")
            return {}

    def get_domain_variables(self, domain: str, core_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get all variables for a domain.

        Args:
            domain: SDTM domain code
            core_only: If True, return only Required and Expected variables

        Returns:
            List of variable specifications
        """
        spec = self.get_domain_specification(domain)
        variables = spec.get("variables", [])

        if core_only:
            variables = [v for v in variables if v.get("core") in ["Req", "Exp"]]

        return variables

    def get_required_variables(self, domain: str) -> List[str]:
        """Get list of required variable names for a domain."""
        variables = self.get_domain_variables(domain)
        return [v["name"] for v in variables if v.get("core") == "Req"]

    def get_expected_variables(self, domain: str) -> List[str]:
        """Get list of expected variable names for a domain."""
        variables = self.get_domain_variables(domain)
        return [v["name"] for v in variables if v.get("core") == "Exp"]

    def get_variable_definition(self, domain: str, variable: str) -> Optional[Dict[str, Any]]:
        """
        Get definition for a specific variable.

        Args:
            domain: SDTM domain code
            variable: Variable name

        Returns:
            Variable definition or None
        """
        variables = self.get_domain_variables(domain)
        for var in variables:
            if var.get("name", "").upper() == variable.upper():
                return var
        return None

    def get_derivation_rules(self, domain: str) -> Dict[str, str]:
        """
        Get derivation rules for a domain.

        Args:
            domain: SDTM domain code

        Returns:
            Dictionary of variable -> derivation rule
        """
        variables = self.get_domain_variables(domain)
        rules = {}

        for var in variables:
            if var.get("derivation"):
                rules[var["name"]] = var["derivation"]

        # Add standard derivations
        if domain != "DM":
            rules[f"{domain}SEQ"] = f"ROW_NUMBER() OVER (PARTITION BY USUBJID ORDER BY {domain}DTC)"

        rules["USUBJID"] = "STUDYID || '-' || SITEID || '-' || SUBJID"
        rules["DOMAIN"] = f"'{domain}'"

        return rules

    def get_controlled_terminology_variables(self, domain: str) -> Dict[str, str]:
        """
        Get variables that require controlled terminology.

        Args:
            domain: SDTM domain code

        Returns:
            Dictionary of variable -> codelist name
        """
        variables = self.get_domain_variables(domain)
        ct_vars = {}

        for var in variables:
            if var.get("codelist"):
                ct_vars[var["name"]] = var["codelist"]

        return ct_vars

    def get_date_variables(self, domain: str) -> List[str]:
        """Get variables that should be in ISO 8601 date format."""
        variables = self.get_domain_variables(domain)
        return [v["name"] for v in variables if v.get("format") == "ISO 8601"]

    def generate_mapping_prompt_context(self, domain: str) -> str:
        """
        Generate comprehensive context for LLM mapping generation.

        Args:
            domain: SDTM domain code

        Returns:
            Formatted context string for LLM prompt
        """
        spec = self.get_domain_specification(domain)

        if not spec:
            return f"No specification found for domain {domain}"

        context = f"""
SDTM Implementation Guide Reference for {domain} Domain
{'=' * 60}

Domain: {spec.get('name', domain)}
Description: {spec.get('description', '')}
Class: {spec.get('class', '')}
Structure: {spec.get('structure', '')}

VARIABLES (per SDTMIG 3.4):
{'=' * 60}
"""
        variables = spec.get("variables", [])

        # Group by core status
        required = [v for v in variables if v.get("core") == "Req"]
        expected = [v for v in variables if v.get("core") == "Exp"]
        permissible = [v for v in variables if v.get("core") == "Perm"]

        context += "\nREQUIRED Variables (must be present):\n"
        context += "-" * 40 + "\n"
        for var in required:
            context += f"  {var['name']}: {var['label']} ({var['type']})"
            if var.get("codelist"):
                context += f" [Codelist: {var['codelist']}]"
            if var.get("derivation"):
                context += f" [Derivation: {var['derivation']}]"
            if var.get("format"):
                context += f" [Format: {var['format']}]"
            context += "\n"

        context += "\nEXPECTED Variables (should be present if applicable):\n"
        context += "-" * 40 + "\n"
        for var in expected:
            context += f"  {var['name']}: {var['label']} ({var['type']})"
            if var.get("codelist"):
                context += f" [Codelist: {var['codelist']}]"
            if var.get("derivation"):
                context += f" [Derivation: {var['derivation']}]"
            if var.get("format"):
                context += f" [Format: {var['format']}]"
            context += "\n"

        context += "\nPERMISSIBLE Variables (optional):\n"
        context += "-" * 40 + "\n"
        for var in permissible[:15]:  # Limit to avoid too long context
            context += f"  {var['name']}: {var['label']} ({var['type']})"
            if var.get("codelist"):
                context += f" [Codelist: {var['codelist']}]"
            context += "\n"

        if len(permissible) > 15:
            context += f"  ... and {len(permissible) - 15} more permissible variables\n"

        # Add derivation rules
        derivations = self.get_derivation_rules(domain)
        if derivations:
            context += "\nSTANDARD DERIVATION RULES:\n"
            context += "-" * 40 + "\n"
            for var, rule in derivations.items():
                context += f"  {var}: {rule}\n"

        # Add controlled terminology
        ct_vars = self.get_controlled_terminology_variables(domain)
        if ct_vars:
            context += "\nCONTROLLED TERMINOLOGY REQUIREMENTS:\n"
            context += "-" * 40 + "\n"
            for var, codelist in ct_vars.items():
                context += f"  {var}: Use codelist {codelist}\n"

        return context


# Singleton instance
_sdtmig_reference = None


def get_sdtmig_reference() -> SDTMIGReference:
    """Get or create the SDTMIG reference singleton."""
    global _sdtmig_reference
    if _sdtmig_reference is None:
        _sdtmig_reference = SDTMIGReference()
    return _sdtmig_reference

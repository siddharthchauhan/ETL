"""
SDTM Variable Derivation Rules
==============================
Comprehensive derivation rules for SDTM variables including:
- Cross-domain dependencies (values from other domains)
- Many-to-one mappings (multiple sources → single target)
- Source column patterns (common EDC naming conventions)
- Derivation formulas and logic

This module provides the knowledge needed for intelligent SDTM mapping.
"""

from typing import List, Dict, Any


# =============================================================================
# VARIABLE DERIVATION RULES
# Each rule specifies HOW to derive a variable, not just WHAT it is
# =============================================================================

DERIVATION_RULES = {
    # =========================================================================
    # DM (Demographics) Domain - Special Purpose
    # =========================================================================
    "DM": {
        "USUBJID": {
            "label": "Unique Subject Identifier",
            "derivation_type": "many-to-one",
            "description": "Unique identifier for each subject across all studies",
            "derivation_formula": "STUDYID || '-' || SITEID || '-' || SUBJID",
            "source_variables": ["STUDYID", "SITEID", "SUBJID"],
            "source_patterns": [
                {"pattern": "SUBJECT_ID", "priority": 1},
                {"pattern": "SUBJ_ID", "priority": 2},
                {"pattern": "PATIENT_ID", "priority": 3},
                {"pattern": "PATNO", "priority": 4},
                {"pattern": "SUBJID", "priority": 5},
            ],
            "cross_domain_sources": [],
            "examples": [
                {"inputs": {"STUDYID": "MAXIS-08", "SITEID": "001", "SUBJID": "101"}, "output": "MAXIS-08-001-101"}
            ],
            "notes": "Must be globally unique. Never reused across studies."
        },

        "RFSTDTC": {
            "label": "Subject Reference Start Date/Time",
            "derivation_type": "cross-domain",
            "description": "Date of first study treatment or first dose. Used as Day 1 for study day calculations.",
            "derivation_formula": "MIN(EX.EXSTDTC) where EXDOSE > 0",
            "source_variables": [],
            "source_patterns": [
                {"pattern": "FIRST_DOSE_DATE", "priority": 1},
                {"pattern": "FIRSTDOSEDT", "priority": 2},
                {"pattern": "TREATMENT_START", "priority": 3},
                {"pattern": "RFSTDTC", "priority": 4},
            ],
            "cross_domain_sources": [
                {"domain": "EX", "variable": "EXSTDTC", "condition": "MIN where EXDOSE > 0"},
                {"domain": "DS", "variable": "DSSTDTC", "condition": "WHERE DSDECOD = 'RANDOMIZED'"},
            ],
            "examples": [
                {"inputs": {"EX.EXSTDTC": ["2024-01-15", "2024-01-22"]}, "output": "2024-01-15"}
            ],
            "notes": "Critical for --DY calculations. Usually first non-zero dose date from EX domain."
        },

        "RFENDTC": {
            "label": "Subject Reference End Date/Time",
            "derivation_type": "cross-domain",
            "description": "Date of last study treatment or last dose",
            "derivation_formula": "MAX(EX.EXENDTC) where EXDOSE > 0",
            "source_variables": [],
            "source_patterns": [
                {"pattern": "LAST_DOSE_DATE", "priority": 1},
                {"pattern": "LASTDOSEDT", "priority": 2},
                {"pattern": "TREATMENT_END", "priority": 3},
            ],
            "cross_domain_sources": [
                {"domain": "EX", "variable": "EXENDTC", "condition": "MAX where EXDOSE > 0"},
            ],
            "examples": [
                {"inputs": {"EX.EXENDTC": ["2024-01-15", "2024-03-15"]}, "output": "2024-03-15"}
            ],
            "notes": "Usually last non-zero dose date from EX domain."
        },

        "RFXSTDTC": {
            "label": "Date/Time of First Study Treatment",
            "derivation_type": "cross-domain",
            "description": "First date of exposure to study drug",
            "derivation_formula": "MIN(EX.EXSTDTC)",
            "source_variables": [],
            "source_patterns": [],
            "cross_domain_sources": [
                {"domain": "EX", "variable": "EXSTDTC", "condition": "MIN"}
            ],
            "examples": [],
            "notes": "May differ from RFSTDTC if non-drug treatments recorded"
        },

        "RFXENDTC": {
            "label": "Date/Time of Last Study Treatment",
            "derivation_type": "cross-domain",
            "description": "Last date of exposure to study drug",
            "derivation_formula": "MAX(EX.EXENDTC)",
            "source_variables": [],
            "source_patterns": [],
            "cross_domain_sources": [
                {"domain": "EX", "variable": "EXENDTC", "condition": "MAX"}
            ],
            "examples": [],
            "notes": "May differ from RFENDTC if non-drug treatments recorded"
        },

        "RFICDTC": {
            "label": "Date/Time of Informed Consent",
            "derivation_type": "direct",
            "description": "Date subject signed informed consent",
            "derivation_formula": "Direct map from source consent date",
            "source_variables": [],
            "source_patterns": [
                {"pattern": "CONSENT_DATE", "priority": 1},
                {"pattern": "IC_DATE", "priority": 2},
                {"pattern": "ICDATE", "priority": 3},
                {"pattern": "INFORM_CONSENT_DT", "priority": 4},
                {"pattern": "SIGNED_ICF_DATE", "priority": 5},
            ],
            "cross_domain_sources": [],
            "examples": [],
            "notes": "First date in study timeline for most subjects"
        },

        "RFPENDTC": {
            "label": "Date/Time of End of Participation",
            "derivation_type": "cross-domain",
            "description": "Last date of participation including follow-up",
            "derivation_formula": "MAX of (last visit date, last AE date, death date, disposition date)",
            "source_variables": [],
            "source_patterns": [
                {"pattern": "LAST_VISIT_DATE", "priority": 1},
                {"pattern": "END_OF_STUDY", "priority": 2},
            ],
            "cross_domain_sources": [
                {"domain": "DS", "variable": "DSSTDTC", "condition": "MAX"},
                {"domain": "AE", "variable": "AEENDTC", "condition": "MAX"},
                {"domain": "SV", "variable": "SVENDTC", "condition": "MAX for last visit"},
            ],
            "examples": [],
            "notes": "Latest date across all domains for subject"
        },

        "DTHDTC": {
            "label": "Date/Time of Death",
            "derivation_type": "cross-domain",
            "description": "Date of subject death",
            "derivation_formula": "Death date from DS or AE domain",
            "source_variables": [],
            "source_patterns": [
                {"pattern": "DEATH_DATE", "priority": 1},
                {"pattern": "DEATHDT", "priority": 2},
                {"pattern": "DATE_OF_DEATH", "priority": 3},
            ],
            "cross_domain_sources": [
                {"domain": "DS", "variable": "DSSTDTC", "condition": "WHERE DSDECOD = 'DEATH'"},
                {"domain": "AE", "variable": "AEENDTC", "condition": "WHERE AEOUT = 'FATAL'"},
            ],
            "examples": [],
            "notes": "Must be consistent across domains if present"
        },

        "DTHFL": {
            "label": "Subject Death Flag",
            "derivation_type": "derived",
            "description": "Flag indicating if subject died",
            "derivation_formula": "'Y' if DTHDTC is not null, else null",
            "source_variables": ["DTHDTC"],
            "source_patterns": [
                {"pattern": "DEATH_FLAG", "priority": 1},
                {"pattern": "DIED", "priority": 2},
            ],
            "cross_domain_sources": [],
            "examples": [
                {"inputs": {"DTHDTC": "2024-03-15"}, "output": "Y"},
                {"inputs": {"DTHDTC": None}, "output": None}
            ],
            "notes": "Derived from DTHDTC presence"
        },

        "AGE": {
            "label": "Age",
            "derivation_type": "derived",
            "description": "Age at reference start date (RFSTDTC)",
            "derivation_formula": "FLOOR((RFSTDTC - BRTHDTC) / 365.25)",
            "source_variables": ["BRTHDTC", "RFSTDTC"],
            "source_patterns": [
                {"pattern": "AGE", "priority": 1},
                {"pattern": "SUBJECT_AGE", "priority": 2},
                {"pattern": "AGE_AT_CONSENT", "priority": 3},
            ],
            "cross_domain_sources": [],
            "examples": [
                {"inputs": {"BRTHDTC": "1980-05-15", "RFSTDTC": "2024-01-15"}, "output": 43}
            ],
            "notes": "If source AGE provided, use it; else calculate from BRTHDTC"
        },

        "BRTHDTC": {
            "label": "Date/Time of Birth",
            "derivation_type": "direct",
            "description": "Subject's date of birth",
            "derivation_formula": "Direct map from source birth date, convert to ISO 8601",
            "source_variables": [],
            "source_patterns": [
                {"pattern": "BIRTH_DATE", "priority": 1},
                {"pattern": "DOB", "priority": 2},
                {"pattern": "DATE_OF_BIRTH", "priority": 3},
                {"pattern": "BIRTHDT", "priority": 4},
                {"pattern": "BRTHDT", "priority": 5},
            ],
            "cross_domain_sources": [],
            "examples": [
                {"inputs": {"DOB": "15-MAY-1980"}, "output": "1980-05-15"},
                {"inputs": {"DOB": "1980"}, "output": "1980"}  # Partial date OK
            ],
            "notes": "May be partial (year only) for privacy"
        },

        "SEX": {
            "label": "Sex",
            "derivation_type": "coded",
            "description": "Subject's biological sex",
            "derivation_formula": "Map source to CDISC CT: MALE/M/1 -> M, FEMALE/F/2 -> F, else U",
            "source_variables": [],
            "source_patterns": [
                {"pattern": "SEX", "priority": 1},
                {"pattern": "GENDER", "priority": 2},
                {"pattern": "GENDRL", "priority": 3},
                {"pattern": "GNDR", "priority": 4},
            ],
            "cross_domain_sources": [],
            "value_mappings": {
                "M": ["M", "MALE", "1", "MASCULINO"],
                "F": ["F", "FEMALE", "2", "FEMENINO"],
                "U": ["U", "UNKNOWN", "UNK", "3"],
                "UNDIFFERENTIATED": ["UNDIFFERENTIATED", "INTERSEX"]
            },
            "examples": [
                {"inputs": {"GENDER": "MALE"}, "output": "M"},
                {"inputs": {"GENDER": "Female"}, "output": "F"},
                {"inputs": {"GENDRL": "1"}, "output": "M"}
            ],
            "notes": "Case-insensitive matching"
        },

        "RACE": {
            "label": "Race",
            "derivation_type": "coded",
            "description": "Subject's race per regulatory definitions",
            "derivation_formula": "Map source race values to CDISC CT RACE codelist",
            "source_variables": [],
            "source_patterns": [
                {"pattern": "RACE", "priority": 1},
                {"pattern": "RCE", "priority": 2},
                {"pattern": "ETHNIC_RACE", "priority": 3},
            ],
            "cross_domain_sources": [],
            "value_mappings": {
                "WHITE": ["WHITE", "CAUCASIAN", "W", "1"],
                "BLACK OR AFRICAN AMERICAN": ["BLACK", "AFRICAN AMERICAN", "B", "2"],
                "ASIAN": ["ASIAN", "A", "3"],
                "AMERICAN INDIAN OR ALASKA NATIVE": ["NATIVE AMERICAN", "AMERICAN INDIAN", "4"],
                "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER": ["PACIFIC ISLANDER", "HAWAIIAN", "5"],
                "MULTIPLE": ["MULTIPLE", "MIXED", "MULTIRACIAL"],
                "OTHER": ["OTHER"],
                "UNKNOWN": ["UNKNOWN", "UNK", "NOT REPORTED"]
            },
            "examples": [
                {"inputs": {"RACE": "CAUCASIAN"}, "output": "WHITE"}
            ],
            "notes": "Extensible codelist - other values allowed"
        },

        "ETHNIC": {
            "label": "Ethnicity",
            "derivation_type": "coded",
            "description": "Hispanic or Latino ethnicity",
            "derivation_formula": "Map source to CDISC CT ETHNIC codelist",
            "source_variables": [],
            "source_patterns": [
                {"pattern": "ETHNIC", "priority": 1},
                {"pattern": "ETHNICITY", "priority": 2},
                {"pattern": "HISPANIC", "priority": 3},
            ],
            "cross_domain_sources": [],
            "value_mappings": {
                "HISPANIC OR LATINO": ["HISPANIC", "LATINO", "LATINA", "YES", "Y", "1"],
                "NOT HISPANIC OR LATINO": ["NOT HISPANIC", "NO", "N", "0", "NON-HISPANIC"],
                "NOT REPORTED": ["NOT REPORTED", "UNKNOWN", "UNK"],
                "UNKNOWN": ["UNKNOWN"]
            },
            "examples": [
                {"inputs": {"HISPANIC": "Y"}, "output": "HISPANIC OR LATINO"}
            ],
            "notes": "Separate from RACE per FDA requirements"
        },

        "ARMCD": {
            "label": "Planned Arm Code",
            "derivation_type": "lookup",
            "description": "Short code for planned treatment arm",
            "derivation_formula": "Lookup from TA domain or derive from ARM",
            "source_variables": [],
            "source_patterns": [
                {"pattern": "ARM_CODE", "priority": 1},
                {"pattern": "ARMCD", "priority": 2},
                {"pattern": "TREATMENT_ARM", "priority": 3},
                {"pattern": "TRT_GRP", "priority": 4},
            ],
            "cross_domain_sources": [
                {"domain": "TA", "variable": "ARMCD", "condition": "Lookup by ARM value"}
            ],
            "examples": [
                {"inputs": {"ARM": "Placebo"}, "output": "PLACEBO"},
                {"inputs": {"ARM": "Drug A 10mg"}, "output": "DRUGA10"}
            ],
            "notes": "Short unique code, no spaces"
        },

        "ARM": {
            "label": "Description of Planned Arm",
            "derivation_type": "direct",
            "description": "Full description of planned treatment arm",
            "derivation_formula": "Direct from source or lookup from TA domain",
            "source_variables": [],
            "source_patterns": [
                {"pattern": "ARM", "priority": 1},
                {"pattern": "TREATMENT_ARM", "priority": 2},
                {"pattern": "PLANNED_TREATMENT", "priority": 3},
                {"pattern": "TREATMENT_GROUP", "priority": 4},
                {"pattern": "TRT", "priority": 5},
            ],
            "cross_domain_sources": [
                {"domain": "TA", "variable": "ARM", "condition": "Lookup by ARMCD"}
            ],
            "examples": [],
            "notes": "Full descriptive name"
        },

        "ACTARMCD": {
            "label": "Actual Arm Code",
            "derivation_type": "derived",
            "description": "Actual treatment arm (may differ from planned)",
            "derivation_formula": "If actual differs from planned, use actual; else copy ARMCD",
            "source_variables": ["ARMCD"],
            "source_patterns": [
                {"pattern": "ACTUAL_ARM_CODE", "priority": 1},
                {"pattern": "ACTARMCD", "priority": 2},
            ],
            "cross_domain_sources": [],
            "examples": [],
            "notes": "Usually equals ARMCD unless protocol deviation"
        },

        "COUNTRY": {
            "label": "Country",
            "derivation_type": "coded",
            "description": "Country of study site",
            "derivation_formula": "Map to ISO 3166-1 alpha-3 code",
            "source_variables": [],
            "source_patterns": [
                {"pattern": "COUNTRY", "priority": 1},
                {"pattern": "CTRY", "priority": 2},
                {"pattern": "SITE_COUNTRY", "priority": 3},
            ],
            "cross_domain_sources": [],
            "value_mappings": {
                "USA": ["USA", "US", "UNITED STATES", "AMERICA"],
                "GBR": ["UK", "GBR", "UNITED KINGDOM", "ENGLAND"],
                "CAN": ["CANADA", "CAN"],
                "DEU": ["GERMANY", "DEU"],
                "FRA": ["FRANCE", "FRA"],
                "JPN": ["JAPAN", "JPN"],
            },
            "examples": [
                {"inputs": {"COUNTRY": "United States"}, "output": "USA"}
            ],
            "notes": "Use ISO 3166-1 alpha-3 codes"
        },
    },

    # =========================================================================
    # AE (Adverse Events) Domain
    # =========================================================================
    "AE": {
        "AESEQ": {
            "label": "Sequence Number",
            "derivation_type": "derived",
            "description": "Unique sequence number per subject",
            "derivation_formula": "ROW_NUMBER() OVER (PARTITION BY USUBJID ORDER BY AESTDTC, AETERM)",
            "source_variables": ["USUBJID", "AESTDTC", "AETERM"],
            "source_patterns": [],
            "cross_domain_sources": [],
            "examples": [
                {"inputs": {"records": 3}, "output": "1, 2, 3"}
            ],
            "notes": "Always derived, not from source"
        },

        "AESTDY": {
            "label": "Study Day of Start of Adverse Event",
            "derivation_type": "cross-domain",
            "description": "Study day relative to reference start date",
            "derivation_formula": "IF AESTDTC >= DM.RFSTDTC THEN AESTDTC - DM.RFSTDTC + 1 ELSE AESTDTC - DM.RFSTDTC",
            "source_variables": ["AESTDTC"],
            "source_patterns": [],
            "cross_domain_sources": [
                {"domain": "DM", "variable": "RFSTDTC", "condition": "Same USUBJID"}
            ],
            "examples": [
                {"inputs": {"AESTDTC": "2024-01-20", "DM.RFSTDTC": "2024-01-15"}, "output": 6},
                {"inputs": {"AESTDTC": "2024-01-10", "DM.RFSTDTC": "2024-01-15"}, "output": -5}
            ],
            "notes": "No Day 0 - Day 1 is first treatment day"
        },

        "AEENDY": {
            "label": "Study Day of End of Adverse Event",
            "derivation_type": "cross-domain",
            "description": "Study day of AE resolution",
            "derivation_formula": "IF AEENDTC >= DM.RFSTDTC THEN AEENDTC - DM.RFSTDTC + 1 ELSE AEENDTC - DM.RFSTDTC",
            "source_variables": ["AEENDTC"],
            "source_patterns": [],
            "cross_domain_sources": [
                {"domain": "DM", "variable": "RFSTDTC", "condition": "Same USUBJID"}
            ],
            "examples": [],
            "notes": "Null if AE ongoing"
        },

        "AESTDTC": {
            "label": "Start Date/Time of Adverse Event",
            "derivation_type": "direct",
            "description": "Date AE started",
            "derivation_formula": "Convert source date to ISO 8601",
            "source_variables": [],
            "source_patterns": [
                {"pattern": "AE_START_DATE", "priority": 1},
                {"pattern": "AESTDT", "priority": 2},
                {"pattern": "ONSET_DATE", "priority": 3},
                {"pattern": "AEONSETDT", "priority": 4},
            ],
            "cross_domain_sources": [],
            "examples": [],
            "notes": "May be partial date"
        },

        "AEENDTC": {
            "label": "End Date/Time of Adverse Event",
            "derivation_type": "direct",
            "description": "Date AE resolved",
            "derivation_formula": "Convert source date to ISO 8601; null if ongoing",
            "source_variables": [],
            "source_patterns": [
                {"pattern": "AE_END_DATE", "priority": 1},
                {"pattern": "AEENDT", "priority": 2},
                {"pattern": "RESOLUTION_DATE", "priority": 3},
                {"pattern": "AERESDT", "priority": 4},
            ],
            "cross_domain_sources": [],
            "examples": [],
            "notes": "Null if AEONGO = 'Y'"
        },

        "AETERM": {
            "label": "Reported Term for the Adverse Event",
            "derivation_type": "direct",
            "description": "Verbatim AE term as reported",
            "derivation_formula": "Direct from source, uppercase",
            "source_variables": [],
            "source_patterns": [
                {"pattern": "AE_TERM", "priority": 1},
                {"pattern": "AETERM", "priority": 2},
                {"pattern": "ADVERSE_EVENT", "priority": 3},
                {"pattern": "AE_VERBATIM", "priority": 4},
                {"pattern": "AEVERB", "priority": 5},
                {"pattern": "AEPTT", "priority": 6},
            ],
            "cross_domain_sources": [],
            "examples": [
                {"inputs": {"AE_TERM": "headache"}, "output": "HEADACHE"}
            ],
            "notes": "Verbatim - not dictionary coded"
        },

        "AEDECOD": {
            "label": "Dictionary-Derived Term",
            "derivation_type": "lookup",
            "description": "MedDRA Preferred Term",
            "derivation_formula": "Lookup from medical dictionary (MedDRA)",
            "source_variables": ["AETERM"],
            "source_patterns": [
                {"pattern": "AEDECOD", "priority": 1},
                {"pattern": "AE_PREFERRED_TERM", "priority": 2},
                {"pattern": "MEDDRA_PT", "priority": 3},
                {"pattern": "AEPT", "priority": 4},
            ],
            "cross_domain_sources": [],
            "examples": [
                {"inputs": {"AETERM": "HEADACHE"}, "output": "Headache"}
            ],
            "notes": "Comes from MedDRA dictionary coding"
        },

        "AEBODSYS": {
            "label": "Body System or Organ Class",
            "derivation_type": "lookup",
            "description": "MedDRA System Organ Class",
            "derivation_formula": "Lookup SOC from MedDRA based on AEDECOD",
            "source_variables": ["AEDECOD"],
            "source_patterns": [
                {"pattern": "AEBODSYS", "priority": 1},
                {"pattern": "AE_SOC", "priority": 2},
                {"pattern": "SYSTEM_ORGAN_CLASS", "priority": 3},
                {"pattern": "AESOC", "priority": 4},
            ],
            "cross_domain_sources": [],
            "examples": [
                {"inputs": {"AEDECOD": "Headache"}, "output": "Nervous system disorders"}
            ],
            "notes": "From MedDRA hierarchy"
        },

        "AESEV": {
            "label": "Severity/Intensity",
            "derivation_type": "coded",
            "description": "Severity grade of AE",
            "derivation_formula": "Map to CDISC CT AESEV",
            "source_variables": [],
            "source_patterns": [
                {"pattern": "AE_SEVERITY", "priority": 1},
                {"pattern": "AESEV", "priority": 2},
                {"pattern": "SEVERITY", "priority": 3},
                {"pattern": "AEINTENS", "priority": 4},
            ],
            "cross_domain_sources": [],
            "value_mappings": {
                "MILD": ["MILD", "1", "GRADE 1"],
                "MODERATE": ["MODERATE", "2", "GRADE 2"],
                "SEVERE": ["SEVERE", "3", "GRADE 3", "GRADE 4", "GRADE 5"]
            },
            "examples": [
                {"inputs": {"SEVERITY": "1"}, "output": "MILD"}
            ],
            "notes": "CTCAE grades 4-5 may also map to SEVERE"
        },

        "AESER": {
            "label": "Serious Event",
            "derivation_type": "derived",
            "description": "Flag for serious adverse event",
            "derivation_formula": "'Y' if ANY(AESDTH, AESLIFE, AESHOSP, AESDISAB, AESCONG, AESMIE) = 'Y' else 'N'",
            "source_variables": ["AESDTH", "AESLIFE", "AESHOSP", "AESDISAB", "AESCONG", "AESMIE"],
            "source_patterns": [
                {"pattern": "AE_SERIOUS", "priority": 1},
                {"pattern": "AESER", "priority": 2},
                {"pattern": "SAE_FLAG", "priority": 3},
                {"pattern": "SERIOUS", "priority": 4},
            ],
            "cross_domain_sources": [],
            "value_mappings": {
                "Y": ["Y", "YES", "1", "TRUE", "SAE"],
                "N": ["N", "NO", "0", "FALSE"]
            },
            "examples": [
                {"inputs": {"AESDTH": "N", "AESHOSP": "Y"}, "output": "Y"}
            ],
            "notes": "Derived from SAE criteria if not directly provided"
        },

        "AEREL": {
            "label": "Causality",
            "derivation_type": "coded",
            "description": "Relationship to study treatment",
            "derivation_formula": "Map to CDISC CT REL codelist",
            "source_variables": [],
            "source_patterns": [
                {"pattern": "AE_RELATIONSHIP", "priority": 1},
                {"pattern": "AEREL", "priority": 2},
                {"pattern": "CAUSALITY", "priority": 3},
                {"pattern": "RELATED", "priority": 4},
            ],
            "cross_domain_sources": [],
            "value_mappings": {
                "NOT RELATED": ["NOT RELATED", "UNRELATED", "NONE", "0"],
                "UNLIKELY RELATED": ["UNLIKELY", "DOUBTFUL", "1"],
                "POSSIBLY RELATED": ["POSSIBLE", "POSSIBLY", "2"],
                "PROBABLY RELATED": ["PROBABLE", "PROBABLY", "3"],
                "DEFINITELY RELATED": ["DEFINITE", "DEFINITELY", "RELATED", "4", "YES"]
            },
            "examples": [
                {"inputs": {"CAUSALITY": "POSSIBLE"}, "output": "POSSIBLY RELATED"}
            ],
            "notes": "Investigator assessment"
        },

        "AEOUT": {
            "label": "Outcome of Adverse Event",
            "derivation_type": "coded",
            "description": "AE resolution status",
            "derivation_formula": "Map to CDISC CT OUT codelist",
            "source_variables": [],
            "source_patterns": [
                {"pattern": "AE_OUTCOME", "priority": 1},
                {"pattern": "AEOUT", "priority": 2},
                {"pattern": "OUTCOME", "priority": 3},
            ],
            "cross_domain_sources": [],
            "value_mappings": {
                "RECOVERED/RESOLVED": ["RECOVERED", "RESOLVED", "1"],
                "RECOVERING/RESOLVING": ["RECOVERING", "RESOLVING", "IMPROVING", "2"],
                "NOT RECOVERED/NOT RESOLVED": ["NOT RECOVERED", "ONGOING", "CONTINUING", "3"],
                "RECOVERED/RESOLVED WITH SEQUELAE": ["WITH SEQUELAE", "SEQUELAE", "4"],
                "FATAL": ["FATAL", "DEATH", "DIED", "5"],
                "UNKNOWN": ["UNKNOWN", "UNK"]
            },
            "examples": [],
            "notes": "Standard outcome categories"
        },

        "AEACN": {
            "label": "Action Taken with Study Treatment",
            "derivation_type": "coded",
            "description": "What action was taken with study drug",
            "derivation_formula": "Map to CDISC CT ACN codelist",
            "source_variables": [],
            "source_patterns": [
                {"pattern": "AE_ACTION", "priority": 1},
                {"pattern": "AEACN", "priority": 2},
                {"pattern": "ACTION_TAKEN", "priority": 3},
            ],
            "cross_domain_sources": [],
            "value_mappings": {
                "DOSE NOT CHANGED": ["NOT CHANGED", "NONE", "NO ACTION"],
                "DOSE REDUCED": ["REDUCED", "DECREASE"],
                "DRUG INTERRUPTED": ["INTERRUPTED", "TEMPORARILY STOPPED"],
                "DRUG WITHDRAWN": ["WITHDRAWN", "DISCONTINUED", "STOPPED"],
                "NOT APPLICABLE": ["N/A", "NOT APPLICABLE"]
            },
            "examples": [],
            "notes": "Action on study treatment due to AE"
        },
    },

    # =========================================================================
    # VS (Vital Signs) Domain - Findings
    # =========================================================================
    "VS": {
        "VSSEQ": {
            "label": "Sequence Number",
            "derivation_type": "derived",
            "description": "Unique sequence per subject",
            "derivation_formula": "ROW_NUMBER() OVER (PARTITION BY USUBJID ORDER BY VSDTC, VSTESTCD)",
            "source_variables": ["USUBJID", "VSDTC", "VSTESTCD"],
            "source_patterns": [],
            "cross_domain_sources": [],
            "examples": [],
            "notes": "Always derived"
        },

        "VSDY": {
            "label": "Study Day of Vital Signs",
            "derivation_type": "cross-domain",
            "description": "Study day of measurement",
            "derivation_formula": "IF VSDTC >= DM.RFSTDTC THEN VSDTC - DM.RFSTDTC + 1 ELSE VSDTC - DM.RFSTDTC",
            "source_variables": ["VSDTC"],
            "source_patterns": [],
            "cross_domain_sources": [
                {"domain": "DM", "variable": "RFSTDTC", "condition": "Same USUBJID"}
            ],
            "examples": [],
            "notes": "Standard study day calculation"
        },

        "VSTESTCD": {
            "label": "Vital Signs Test Short Name",
            "derivation_type": "coded",
            "description": "Standard test code",
            "derivation_formula": "Map source test name to CDISC VSTESTCD codelist",
            "source_variables": [],
            "source_patterns": [
                {"pattern": "VS_TEST", "priority": 1},
                {"pattern": "TEST_CODE", "priority": 2},
                {"pattern": "PARAMETER", "priority": 3},
            ],
            "cross_domain_sources": [],
            "value_mappings": {
                "SYSBP": ["SYSTOLIC", "SYS BP", "SYSTOLIC BP", "SBP"],
                "DIABP": ["DIASTOLIC", "DIA BP", "DIASTOLIC BP", "DBP"],
                "PULSE": ["PULSE", "HEART RATE", "HR"],
                "RESP": ["RESPIRATION", "RESPIRATORY RATE", "RR", "RESP RATE"],
                "TEMP": ["TEMPERATURE", "TEMP", "BODY TEMP"],
                "HEIGHT": ["HEIGHT", "HT", "BODY HEIGHT"],
                "WEIGHT": ["WEIGHT", "WT", "BODY WEIGHT"],
                "BMI": ["BMI", "BODY MASS INDEX"]
            },
            "examples": [
                {"inputs": {"VS_TEST": "Systolic Blood Pressure"}, "output": "SYSBP"}
            ],
            "notes": "Use CDISC controlled terminology"
        },

        "VSSTRESN": {
            "label": "Numeric Result/Finding in Standard Units",
            "derivation_type": "derived",
            "description": "Standardized numeric result",
            "derivation_formula": "Convert VSORRES to numeric and standardize units",
            "source_variables": ["VSORRES", "VSORRESU"],
            "source_patterns": [],
            "cross_domain_sources": [],
            "examples": [
                {"inputs": {"VSORRES": "98.6", "VSORRESU": "F"}, "output": 37.0},  # Convert F to C
            ],
            "notes": "Apply unit conversions as needed"
        },

        "VSSTRESU": {
            "label": "Standard Units",
            "derivation_type": "lookup",
            "description": "Standard unit for the test",
            "derivation_formula": "Lookup standard unit by VSTESTCD",
            "source_variables": ["VSTESTCD"],
            "source_patterns": [],
            "cross_domain_sources": [],
            "value_mappings": {
                "SYSBP": "mmHg",
                "DIABP": "mmHg",
                "PULSE": "beats/min",
                "RESP": "breaths/min",
                "TEMP": "C",
                "HEIGHT": "cm",
                "WEIGHT": "kg",
                "BMI": "kg/m2"
            },
            "examples": [],
            "notes": "Standard units by test type"
        },
    },

    # =========================================================================
    # LB (Laboratory) Domain - Findings
    # =========================================================================
    "LB": {
        "LBSEQ": {
            "label": "Sequence Number",
            "derivation_type": "derived",
            "description": "Unique sequence per subject",
            "derivation_formula": "ROW_NUMBER() OVER (PARTITION BY USUBJID ORDER BY LBDTC, LBTESTCD)",
            "source_variables": ["USUBJID", "LBDTC", "LBTESTCD"],
            "source_patterns": [],
            "cross_domain_sources": [],
            "examples": [],
            "notes": "Always derived"
        },

        "LBDY": {
            "label": "Study Day of Specimen Collection",
            "derivation_type": "cross-domain",
            "description": "Study day of lab collection",
            "derivation_formula": "IF LBDTC >= DM.RFSTDTC THEN LBDTC - DM.RFSTDTC + 1 ELSE LBDTC - DM.RFSTDTC",
            "source_variables": ["LBDTC"],
            "source_patterns": [],
            "cross_domain_sources": [
                {"domain": "DM", "variable": "RFSTDTC", "condition": "Same USUBJID"}
            ],
            "examples": [],
            "notes": "Standard study day calculation"
        },

        "LBNRIND": {
            "label": "Reference Range Indicator",
            "derivation_type": "derived",
            "description": "Indicates if result is within normal range",
            "derivation_formula": "IF LBSTRESN < LBSTNRLO THEN 'LOW' ELSE IF LBSTRESN > LBSTNRHI THEN 'HIGH' ELSE 'NORMAL'",
            "source_variables": ["LBSTRESN", "LBSTNRLO", "LBSTNRHI"],
            "source_patterns": [
                {"pattern": "LB_NORMAL_FLAG", "priority": 1},
                {"pattern": "LBNRIND", "priority": 2},
                {"pattern": "ABNORMAL_FLAG", "priority": 3},
            ],
            "cross_domain_sources": [],
            "value_mappings": {
                "NORMAL": ["NORMAL", "N", "WNL"],
                "LOW": ["LOW", "L", "BELOW"],
                "HIGH": ["HIGH", "H", "ABOVE"],
                "ABNORMAL": ["ABNORMAL", "A"]
            },
            "examples": [
                {"inputs": {"LBSTRESN": 3.5, "LBSTNRLO": 4.0, "LBSTNRHI": 6.0}, "output": "LOW"}
            ],
            "notes": "Derived from result and reference ranges if not provided"
        },
    },

    # =========================================================================
    # EX (Exposure) Domain - Interventions
    # =========================================================================
    "EX": {
        "EXSEQ": {
            "label": "Sequence Number",
            "derivation_type": "derived",
            "description": "Unique sequence per subject",
            "derivation_formula": "ROW_NUMBER() OVER (PARTITION BY USUBJID ORDER BY EXSTDTC)",
            "source_variables": ["USUBJID", "EXSTDTC"],
            "source_patterns": [],
            "cross_domain_sources": [],
            "examples": [],
            "notes": "Always derived"
        },

        "EXSTDY": {
            "label": "Study Day of Start of Treatment",
            "derivation_type": "cross-domain",
            "description": "Study day treatment started",
            "derivation_formula": "IF EXSTDTC >= DM.RFSTDTC THEN EXSTDTC - DM.RFSTDTC + 1 ELSE EXSTDTC - DM.RFSTDTC",
            "source_variables": ["EXSTDTC"],
            "source_patterns": [],
            "cross_domain_sources": [
                {"domain": "DM", "variable": "RFSTDTC", "condition": "Same USUBJID"}
            ],
            "examples": [],
            "notes": "Standard study day calculation"
        },

        "EXENDY": {
            "label": "Study Day of End of Treatment",
            "derivation_type": "cross-domain",
            "description": "Study day treatment ended",
            "derivation_formula": "IF EXENDTC >= DM.RFSTDTC THEN EXENDTC - DM.RFSTDTC + 1 ELSE EXENDTC - DM.RFSTDTC",
            "source_variables": ["EXENDTC"],
            "source_patterns": [],
            "cross_domain_sources": [
                {"domain": "DM", "variable": "RFSTDTC", "condition": "Same USUBJID"}
            ],
            "examples": [],
            "notes": "Standard study day calculation"
        },
    },

    # =========================================================================
    # CM (Concomitant Medications) Domain - Interventions
    # =========================================================================
    "CM": {
        "CMSEQ": {
            "label": "Sequence Number",
            "derivation_type": "derived",
            "description": "Unique sequence per subject",
            "derivation_formula": "ROW_NUMBER() OVER (PARTITION BY USUBJID ORDER BY CMSTDTC, CMTRT)",
            "source_variables": ["USUBJID", "CMSTDTC", "CMTRT"],
            "source_patterns": [],
            "cross_domain_sources": [],
            "examples": [],
            "notes": "Always derived"
        },

        "CMSTDY": {
            "label": "Study Day of Start of Medication",
            "derivation_type": "cross-domain",
            "description": "Study day medication started",
            "derivation_formula": "IF CMSTDTC >= DM.RFSTDTC THEN CMSTDTC - DM.RFSTDTC + 1 ELSE CMSTDTC - DM.RFSTDTC",
            "source_variables": ["CMSTDTC"],
            "source_patterns": [],
            "cross_domain_sources": [
                {"domain": "DM", "variable": "RFSTDTC", "condition": "Same USUBJID"}
            ],
            "examples": [],
            "notes": "Standard study day calculation"
        },

        "CMDECOD": {
            "label": "Standardized Medication Name",
            "derivation_type": "lookup",
            "description": "WHO Drug or other dictionary term",
            "derivation_formula": "Lookup from WHO Drug dictionary",
            "source_variables": ["CMTRT"],
            "source_patterns": [
                {"pattern": "CM_STANDARD", "priority": 1},
                {"pattern": "CMDECOD", "priority": 2},
                {"pattern": "WHO_DRUG", "priority": 3},
            ],
            "cross_domain_sources": [],
            "examples": [],
            "notes": "From WHO Drug dictionary coding"
        },
    },
}


# =============================================================================
# CROSS-DOMAIN DEPENDENCY MAP
# Shows which variables depend on other domains
# =============================================================================

CROSS_DOMAIN_DEPENDENCIES = {
    # Variables that depend on DM.RFSTDTC for study day calculations
    "DM.RFSTDTC": [
        "AE.AESTDY",
        "AE.AEENDY",
        "VS.VSDY",
        "LB.LBDY",
        "EX.EXSTDY",
        "EX.EXENDY",
        "CM.CMSTDY",
        "CM.CMENDY",
        "MH.MHSTDY",
        "MH.MHENDY",
    ],

    # Variables derived from EX domain
    "EX.EXSTDTC": [
        "DM.RFSTDTC",
        "DM.RFXSTDTC",
    ],
    "EX.EXENDTC": [
        "DM.RFENDTC",
        "DM.RFXENDTC",
    ],

    # Variables derived from DS domain
    "DS.DSSTDTC": [
        "DM.RFPENDTC",
        "DM.DTHDTC",
    ],

    # Variables that use DM.BRTHDTC
    "DM.BRTHDTC": [
        "DM.AGE",
    ],
}


# =============================================================================
# SOURCE COLUMN PATTERN LIBRARY
# Common EDC column naming patterns
# =============================================================================

SOURCE_COLUMN_PATTERNS = {
    # Subject identifiers
    "SUBJECT_ID": {
        "patterns": ["SUBJECT_ID", "SUBJ_ID", "SUBJID", "PATIENT_ID", "PATNO", "PATID", "PT_ID", "SCREENID"],
        "target_variables": ["DM.SUBJID"],
        "priority": 1
    },
    "SITE_ID": {
        "patterns": ["SITE_ID", "SITEID", "SITE", "SITENO", "CENTER", "CENTRE", "CENTER_ID"],
        "target_variables": ["DM.SITEID"],
        "priority": 1
    },

    # Demographics
    "BIRTH_DATE": {
        "patterns": ["BIRTH_DATE", "DOB", "DATE_OF_BIRTH", "BIRTHDT", "BRTHDT", "BDATE"],
        "target_variables": ["DM.BRTHDTC"],
        "priority": 1
    },
    "GENDER": {
        "patterns": ["SEX", "GENDER", "GENDRL", "GNDR", "GEND"],
        "target_variables": ["DM.SEX"],
        "priority": 1
    },
    "RACE_FIELD": {
        "patterns": ["RACE", "RCE", "ETHNIC_RACE", "RACIAL"],
        "target_variables": ["DM.RACE"],
        "priority": 1
    },

    # Dates
    "CONSENT_DATE": {
        "patterns": ["CONSENT_DATE", "IC_DATE", "ICDATE", "INFORM_CONSENT_DT", "SIGNED_ICF_DATE", "ICF_DATE"],
        "target_variables": ["DM.RFICDTC"],
        "priority": 1
    },
    "FIRST_DOSE": {
        "patterns": ["FIRST_DOSE_DATE", "FIRSTDOSEDT", "TREATMENT_START", "TRTSTART", "FIRST_TRT_DATE"],
        "target_variables": ["DM.RFSTDTC", "DM.RFXSTDTC"],
        "priority": 1
    },

    # Adverse Events
    "AE_TERM": {
        "patterns": ["AE_TERM", "AETERM", "ADVERSE_EVENT", "AE_VERBATIM", "AEVERB", "AEPTT", "AE_REPORTED"],
        "target_variables": ["AE.AETERM"],
        "priority": 1
    },
    "AE_START": {
        "patterns": ["AE_START_DATE", "AESTDT", "ONSET_DATE", "AEONSETDT", "AE_ONSET"],
        "target_variables": ["AE.AESTDTC"],
        "priority": 1
    },
    "AE_SEVERITY": {
        "patterns": ["AE_SEVERITY", "AESEV", "SEVERITY", "AEINTENS", "GRADE"],
        "target_variables": ["AE.AESEV"],
        "priority": 1
    },
}


def get_derivation_rule(domain: str, variable: str) -> Dict[str, Any]:
    """Get derivation rule for a specific variable."""
    domain_rules = DERIVATION_RULES.get(domain, {})
    return domain_rules.get(variable, {})


def get_cross_domain_dependencies(variable: str) -> List[str]:
    """Get list of variables that depend on this variable."""
    return CROSS_DOMAIN_DEPENDENCIES.get(variable, [])


def find_source_pattern(source_column: str) -> Dict[str, Any]:
    """Find matching source pattern for a column name."""
    source_upper = source_column.upper()

    for pattern_name, pattern_info in SOURCE_COLUMN_PATTERNS.items():
        for pattern in pattern_info["patterns"]:
            if pattern.upper() in source_upper or source_upper in pattern.upper():
                return {
                    "pattern_name": pattern_name,
                    "matched_pattern": pattern,
                    "target_variables": pattern_info["target_variables"],
                    "priority": pattern_info["priority"]
                }

    return {}


def get_all_derivation_rules() -> Dict[str, Dict]:
    """Get all derivation rules for all domains."""
    return DERIVATION_RULES

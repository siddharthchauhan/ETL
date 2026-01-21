"""
Intelligent Column Mapper for EDC to SDTM Transformation
=========================================================
Dynamically analyzes raw EDC data and intelligently maps columns to SDTM variables.

This module uses:
1. SDTM-IG 3.4 specifications (from web reference and local cache)
2. Semantic/fuzzy matching of column names
3. Value pattern analysis to infer column purpose
4. Pinecone knowledge base for SDTM specifications
5. CDISC Controlled terminology lookups
6. Web search for additional guidance

Key Sources:
- SDTM-IG 3.4: https://sastricks.com/cdisc/SDTMIG%20v3.4-FINAL_2022-07-21.pdf
- CDISC SDTMIG: https://www.cdisc.org/standards/foundational/sdtmig
- CDISC CT: https://www.cdisc.org/standards/terminology
"""

import re
import os
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)

# Import web reference for SDTM-IG 3.4 specifications
try:
    from .sdtm_web_reference import SDTMWebReference, get_sdtm_web_reference
    SDTM_WEB_REFERENCE_AVAILABLE = True
except ImportError:
    SDTM_WEB_REFERENCE_AVAILABLE = False
    SDTMWebReference = None
    get_sdtm_web_reference = None


@dataclass
class ColumnMapping:
    """Represents a mapping from source column to SDTM variable."""
    source_column: str
    sdtm_variable: str
    confidence: float  # 0.0 to 1.0
    mapping_reason: str
    value_transform: Optional[str] = None  # e.g., "controlled_terminology", "date_format", "numeric"
    ct_codelist: Optional[str] = None  # Controlled terminology codelist name


@dataclass
class DomainMappingSpec:
    """Complete mapping specification for a domain."""
    domain: str
    mappings: List[ColumnMapping] = field(default_factory=list)
    unmapped_source_columns: List[str] = field(default_factory=list)
    unmapped_sdtm_variables: List[str] = field(default_factory=list)


class IntelligentMapper:
    """
    Intelligently maps EDC source columns to SDTM variables using multiple strategies.
    """

    # Common SDTM variable patterns by domain
    SDTM_VARIABLE_PATTERNS = {
        "AE": {
            "identifiers": ["STUDYID", "DOMAIN", "USUBJID", "AESEQ", "AESPID", "AEGRPID", "AEREFID", "AELNKID", "AELNKGRP"],
            "topic": ["AETERM", "AEMODIFY", "AEDECOD", "AELLT", "AELLTCD", "AEPTCD", "AEHLT", "AEHLTCD",
                     "AEHLGT", "AEHLGTCD", "AEBODSYS", "AEBDSYCD", "AESOC", "AESOCCD"],
            "qualifier": ["AEPRESP", "AEOCCUR", "AESTAT", "AEREASND", "AESEV", "AESER", "AEACN", "AEACNOTH",
                         "AEREL", "AERELNST", "AEPATT", "AEOUT", "AESCAN", "AESCONG", "AESDISAB", "AESDTH",
                         "AESHOSP", "AESLIFE", "AESOD", "AESMIE", "AECONTRT", "AETOXGR"],
            "timing": ["EPOCH", "AEDTC", "AESTDTC", "AEENDTC", "AESTDY", "AEENDY", "AEDUR", "AEENRF",
                      "AESTRF", "AEENRTPT", "AESTRTPT", "VISITNUM", "VISIT", "VISITDY"]
        },
        "DM": {
            "identifiers": ["STUDYID", "DOMAIN", "USUBJID", "SUBJID", "SITEID", "INVID", "INVNAM"],
            "topic": ["RFSTDTC", "RFENDTC", "RFXSTDTC", "RFXENDTC", "RFICDTC", "RFPENDTC", "DTHDTC", "DTHFL"],
            "qualifier": ["AGE", "AGEU", "SEX", "RACE", "ETHNIC", "ARMCD", "ARM", "ACTARMCD", "ACTARM",
                         "COUNTRY", "DMDTC", "DMDY"],
            "timing": ["BRTHDTC"]
        },
        "VS": {
            "identifiers": ["STUDYID", "DOMAIN", "USUBJID", "VSSEQ", "VSSPID", "VSGRPID", "VSREFID", "VSLNKID", "VSLNKGRP"],
            "topic": ["VSTESTCD", "VSTEST"],
            "qualifier": ["VSCAT", "VSSCAT", "VSPOS", "VSORRES", "VSORRESU", "VSSTRESC", "VSSTRESN",
                         "VSSTRESU", "VSSTAT", "VSREASND", "VSLOC", "VSLAT", "VSBLFL", "VSDRVFL"],
            "timing": ["EPOCH", "VSDTC", "VSDY", "VSTPT", "VSTPTNUM", "VSELTM", "VSTPTREF",
                      "VSRFTDTC", "VISITNUM", "VISIT", "VISITDY"]
        },
        "LB": {
            "identifiers": ["STUDYID", "DOMAIN", "USUBJID", "LBSEQ", "LBSPID", "LBGRPID", "LBREFID", "LBLNKID", "LBLNKGRP"],
            "topic": ["LBTESTCD", "LBTEST"],
            "qualifier": ["LBCAT", "LBSCAT", "LBORRES", "LBORRESU", "LBORNRLO", "LBORNRHI", "LBSTRESC",
                         "LBSTRESN", "LBSTRESU", "LBSTNRLO", "LBSTNRHI", "LBNRIND", "LBSTAT", "LBREASND",
                         "LBNAM", "LBLOINC", "LBSPEC", "LBSPCCND", "LBMETHOD", "LBLOC", "LBLAT",
                         "LBBLFL", "LBFAST", "LBDRVFL"],
            "timing": ["EPOCH", "LBDTC", "LBENDTC", "LBDY", "LBENDY", "LBTPT", "LBTPTNUM", "LBELTM",
                      "LBTPTREF", "LBRFTDTC", "VISITNUM", "VISIT", "VISITDY"]
        },
        "CM": {
            "identifiers": ["STUDYID", "DOMAIN", "USUBJID", "CMSEQ", "CMSPID", "CMGRPID", "CMREFID", "CMLNKID", "CMLNKGRP"],
            "topic": ["CMTRT", "CMMODIFY", "CMDECOD", "CMCAT", "CMSCAT", "CMPRESP", "CMOCCUR"],
            "qualifier": ["CMINDC", "CMCLAS", "CMCLASCD", "CMDOSE", "CMDOSTXT", "CMDOSU", "CMDOSFRM",
                         "CMDOSFRQ", "CMDOSTOT", "CMDOSRGM", "CMROUTE", "CMSTAT", "CMREASND"],
            "timing": ["EPOCH", "CMDTC", "CMSTDTC", "CMENDTC", "CMSTDY", "CMENDY", "CMDUR",
                      "CMENRF", "CMSTRF", "VISITNUM", "VISIT", "VISITDY"]
        },
        "EX": {
            "identifiers": ["STUDYID", "DOMAIN", "USUBJID", "EXSEQ", "EXSPID", "EXGRPID", "EXREFID", "EXLNKID", "EXLNKGRP"],
            "topic": ["EXTRT", "EXCAT", "EXSCAT"],
            "qualifier": ["EXDOSE", "EXDOSTXT", "EXDOSU", "EXDOSFRM", "EXDOSFRQ", "EXDOSTOT",
                         "EXDOSRGM", "EXROUTE", "EXLOT", "EXLOC", "EXLAT", "EXDIR", "EXFAST",
                         "EXADJ", "EXSTAT", "EXREASND"],
            "timing": ["EPOCH", "EXDTC", "EXSTDTC", "EXENDTC", "EXSTDY", "EXENDY", "EXDUR",
                      "EXENRF", "EXSTRF", "VISITNUM", "VISIT", "VISITDY"]
        },
        "MH": {
            "identifiers": ["STUDYID", "DOMAIN", "USUBJID", "MHSEQ", "MHSPID", "MHGRPID", "MHREFID", "MHLNKID", "MHLNKGRP"],
            "topic": ["MHTERM", "MHMODIFY", "MHDECOD", "MHCAT", "MHSCAT", "MHPRESP", "MHOCCUR"],
            "qualifier": ["MHBODSYS", "MHSTAT", "MHREASND", "MHSEV"],
            "timing": ["EPOCH", "MHDTC", "MHSTDTC", "MHENDTC", "MHSTDY", "MHENDY", "MHDUR",
                      "MHENRF", "MHSTRF", "VISITNUM", "VISIT", "VISITDY"]
        },
        "DS": {
            "identifiers": ["STUDYID", "DOMAIN", "USUBJID", "DSSEQ", "DSSPID", "DSGRPID", "DSREFID", "DSLNKID", "DSLNKGRP"],
            "topic": ["DSTERM", "DSDECOD", "DSCAT", "DSSCAT"],
            "qualifier": ["EPOCH", "DSSTDTC", "DSSTDY"],
            "timing": ["DSDTC", "DSDY", "VISITNUM", "VISIT", "VISITDY"]
        }
    }

    # Common source column name patterns and their likely SDTM mappings
    SOURCE_PATTERNS = {
        # Subject/Patient identifiers
        r"(?i)^(PT|PAT|PATIENT|SUBJ|SUBJECT)(_?ID|_?NUM|_?NO)?$": ("SUBJID", 0.9),
        r"(?i)^(USUBJID|UNIQUE.*SUBJ)": ("USUBJID", 0.95),
        r"(?i)^(INVSITE|SITE|CENTER)(_?ID|_?NUM|_?CODE)?$": ("SITEID", 0.95),
        r"(?i)^(INV)(_?ID|_?NUM|_?CODE)?$": ("INVID", 0.85),
        r"(?i)^(STUDY|PROTOCOL)(_?ID|_?NUM|_?CODE)?$": ("STUDYID", 0.9),

        # AE specific patterns
        r"(?i)^AE(VERB|VERBATIM|TEXT|DESC|NAME)": ("AETERM", 0.9),
        r"(?i)^AE(COD|CODE)$": ("AETERM", 0.85),  # Often the coded verbatim
        r"(?i)^AEPTC$": ("AEPTCD", 0.95),  # Exact match for AEPTC -> AEPTCD (before generic PT pattern)
        r"(?i)^AE(PTT|PREF.*TERM)": ("AEDECOD", 0.9),  # PT text, not PT code
        r"(?i)^AE(HTT|HLT|HIGH.*LEVEL.*TERM)": ("AEHLT", 0.9),
        r"(?i)^AE(HGT|HLGT|HIGH.*LEVEL.*GROUP)": ("AEHLGT", 0.85),
        r"(?i)^AE(SCT|SOC|SYSTEM.*ORGAN)": ("AEBODSYS", 0.9),
        r"(?i)^AE(LTT|LLT|LOW.*LEVEL)": ("AELLT", 0.9),
        r"(?i)^AE(PTCD|PT.*CODE)$": ("AEPTCD", 0.9),
        r"(?i)^AE(HTC|HLTCD|HLT.*CODE)": ("AEHLTCD", 0.9),
        r"(?i)^AE(HGC|HLGTCD|HLGT.*CODE)": ("AEHLGTCD", 0.9),
        r"(?i)^AE(SCC|SOCCD|SOC.*CODE)": ("AEBDSYCD", 0.9),
        r"(?i)^AE(LTC|LLTCD|LLT.*CODE)": ("AELLTCD", 0.9),
        r"(?i)^AE(REL|RELL|RELAT|CAUS)": ("AEREL", 0.9),
        r"(?i)^AE(OUT|OUTC|OUTCOME)": ("AEOUT", 0.9),
        r"(?i)^AE(SEV|SEVER|INTENS)": ("AESEV", 0.9),
        r"(?i)^AESER$": ("AESER", 0.95),  # Exact match for AESER
        r"(?i)^AE(SERL|SERIOUS)": ("AESER", 0.85),  # Seriousness label derives AESER
        r"(?i)^AE(ACT|ACTION)": ("AEACN", 0.85),
        r"(?i)^AE(STDT|START|ONSET)": ("AESTDTC", 0.9),
        r"(?i)^AE(ENDT|END|RESOL)": ("AEENDTC", 0.9),
        r"(?i)^AE(TOX|GRADE|CTCAE)": ("AETOXGR", 0.85),

        # Date patterns (generic)
        r"(?i)(ST|START|BEGIN|ONSET)(DT|DATE|DTC)": ("--STDTC", 0.85),
        r"(?i)(EN|END|STOP|RESOL)(DT|DATE|DTC)": ("--ENDTC", 0.85),
        r"(?i)^(DT|DATE|DTC)$": ("--DTC", 0.7),

        # Demographics
        r"(?i)^(AGE|AGEY|AGE_?YEARS?)$": ("AGE", 0.95),
        r"(?i)^(SEX|GENDER)$": ("SEX", 0.95),
        r"(?i)^(RACE|ETHNIC)": ("RACE", 0.9),
        r"(?i)^(ARM|TRT|TREAT|GROUP)": ("ARM", 0.8),
        r"(?i)^(COUNTRY|CTRY)$": ("COUNTRY", 0.95),
        r"(?i)^(BRTH|BIRTH|DOB)": ("BRTHDTC", 0.9),

        # Vital Signs
        r"(?i)(SYS|SYSTOLIC|SBP)": ("SYSBP", 0.9),
        r"(?i)(DIA|DIASTOLIC|DBP)": ("DIABP", 0.9),
        r"(?i)(HR|HEART|PULSE)": ("HR", 0.85),
        r"(?i)(TEMP|TEMPER)": ("TEMP", 0.85),
        r"(?i)(WT|WEIGHT|BODY.*WT)": ("WEIGHT", 0.9),
        r"(?i)(HT|HEIGHT|BODY.*HT)": ("HEIGHT", 0.9),
        r"(?i)(BMI|BODY.*MASS)": ("BMI", 0.9),
        r"(?i)(RESP|RESPIR)": ("RESP", 0.85),

        # Lab
        r"(?i)^(TEST|PARAM|ANALYTE)$": ("LBTEST", 0.7),
        r"(?i)^(RESULT|VALUE|ORRES)$": ("LBORRES", 0.7),
        r"(?i)^(UNIT|UNITS|ORRESU)$": ("LBORRESU", 0.7),
        r"(?i)^(SPEC|SPECIMEN|MATRIX)$": ("LBSPEC", 0.8),

        # Concomitant Medications
        r"(?i)^(MED|DRUG|TRT|TREAT|MEDICATION)(_?NAME)?$": ("CMTRT", 0.85),
        r"(?i)^(DOSE|DOSAGE)$": ("CMDOSE", 0.8),
        r"(?i)^(ROUTE|ADMIN.*ROUTE)$": ("CMROUTE", 0.85),
        r"(?i)^(FREQ|FREQUENCY)$": ("CMDOSFRQ", 0.8),
        r"(?i)^(IND|INDICATION|REASON)$": ("CMINDC", 0.8),

        # Medical History
        r"(?i)^(COND|CONDITION|DIAGNOSIS|DX)$": ("MHTERM", 0.8),
        r"(?i)^(ONGOING|CURRENT|ACTIVE)$": ("MHENRF", 0.7),

        # Visit/Timing
        r"(?i)^(VISIT|VIS)(_?NAME|_?NUM)?$": ("VISIT", 0.9),
        r"(?i)^(VISITNUM|VIS.*NUM)$": ("VISITNUM", 0.95),
        r"(?i)^(EPOCH|PHASE|PERIOD)$": ("EPOCH", 0.85),
    }

    # Value patterns to infer column purpose
    VALUE_PATTERNS = {
        "date_yyyymmdd": (r"^\d{8}$", "date"),
        "date_iso": (r"^\d{4}-\d{2}-\d{2}", "date"),
        "date_slash": (r"^\d{1,2}/\d{1,2}/\d{2,4}$", "date"),
        "yes_no": (r"^[YN]$|^YES$|^NO$", "boolean"),
        "severity": (r"^(MILD|MODERATE|SEVERE|LIFE.?THREATENING|FATAL)$", "severity"),
        "causality": (r"^(RELATED|UNRELATED|POSSIBLE|PROBABLE|UNLIKELY|DEFINITE)", "causality"),
        "outcome": (r"^(RESOLVED|RECOVERED|CONTINUING|FATAL|UNKNOWN|ONGOING)", "outcome"),
        "sex": (r"^[MFU]$|^MALE$|^FEMALE$|^UNKNOWN$", "sex"),
        "numeric": (r"^-?\d+\.?\d*$", "numeric"),
        "meddra_code": (r"^\d{8}$", "meddra_code"),  # 8-digit MedDRA codes
    }

    # Controlled terminology codelists
    CT_CODELISTS = {
        "AEREL": ["RELATED", "NOT RELATED", "POSSIBLY RELATED", "PROBABLY RELATED",
                  "UNLIKELY RELATED", "DEFINITELY RELATED"],
        "AEOUT": ["RECOVERED/RESOLVED", "RECOVERING/RESOLVING", "NOT RECOVERED/NOT RESOLVED",
                  "RECOVERED/RESOLVED WITH SEQUELAE", "FATAL", "UNKNOWN"],
        "AESEV": ["MILD", "MODERATE", "SEVERE"],
        "AEACN": ["DRUG WITHDRAWN", "DRUG INTERRUPTED", "DOSE REDUCED", "DOSE INCREASED",
                  "DOSE NOT CHANGED", "NOT APPLICABLE", "UNKNOWN"],
        "SEX": ["M", "F", "U", "UNDIFFERENTIATED"],
        "NY": ["N", "Y"],
        "RACE": ["AMERICAN INDIAN OR ALASKA NATIVE", "ASIAN", "BLACK OR AFRICAN AMERICAN",
                 "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER", "WHITE", "MULTIPLE",
                 "NOT REPORTED", "UNKNOWN", "OTHER"],
        "ETHNIC": ["HISPANIC OR LATINO", "NOT HISPANIC OR LATINO", "NOT REPORTED", "UNKNOWN"],
    }

    def __init__(self, pinecone_retriever=None, use_web_reference: bool = True):
        """
        Initialize intelligent mapper with multiple knowledge sources.

        Args:
            pinecone_retriever: Optional Pinecone retriever for knowledge base lookups
            use_web_reference: Whether to use SDTM-IG 3.4 web reference (default: True)
        """
        self.pinecone_retriever = pinecone_retriever
        self._sdtm_specs_cache = {}

        # Initialize SDTM web reference for SDTM-IG 3.4 specifications and CT
        self.web_reference = None
        if use_web_reference and SDTM_WEB_REFERENCE_AVAILABLE:
            try:
                self.web_reference = get_sdtm_web_reference()
                logger.info("SDTM-IG 3.4 web reference initialized")
            except Exception as e:
                logger.warning(f"Could not initialize web reference: {e}")

    def analyze_source_data(self, df: pd.DataFrame, domain: str) -> DomainMappingSpec:
        """
        Analyze source DataFrame and create intelligent mapping to SDTM variables.

        Args:
            df: Source DataFrame with raw EDC data
            domain: Target SDTM domain (e.g., "AE", "DM", "VS")

        Returns:
            DomainMappingSpec with discovered mappings
        """
        logger.info(f"Analyzing source data for {domain} domain mapping")
        logger.info(f"Source columns: {list(df.columns)}")

        mappings = []
        mapped_source_cols = set()
        mapped_sdtm_vars = set()

        # Get SDTM variable list for this domain
        sdtm_vars = self._get_sdtm_variables(domain)

        # Strategy 1: Pattern-based column name matching
        for col in df.columns:
            mapping = self._match_by_pattern(col, domain)
            if mapping and mapping.confidence >= 0.7:
                mappings.append(mapping)
                mapped_source_cols.add(col)
                mapped_sdtm_vars.add(mapping.sdtm_variable)
                logger.info(f"Pattern match: {col} -> {mapping.sdtm_variable} ({mapping.confidence:.0%})")

        # Strategy 2: Fuzzy name matching for unmapped columns
        for col in df.columns:
            if col in mapped_source_cols:
                continue
            mapping = self._match_by_fuzzy(col, sdtm_vars, mapped_sdtm_vars)
            if mapping and mapping.confidence >= 0.6:
                mappings.append(mapping)
                mapped_source_cols.add(col)
                mapped_sdtm_vars.add(mapping.sdtm_variable)
                logger.info(f"Fuzzy match: {col} -> {mapping.sdtm_variable} ({mapping.confidence:.0%})")

        # Strategy 3: Value-based inference for unmapped columns
        for col in df.columns:
            if col in mapped_source_cols:
                continue
            mapping = self._match_by_values(col, df[col], domain, mapped_sdtm_vars)
            if mapping and mapping.confidence >= 0.5:
                mappings.append(mapping)
                mapped_source_cols.add(col)
                mapped_sdtm_vars.add(mapping.sdtm_variable)
                logger.info(f"Value inference: {col} -> {mapping.sdtm_variable} ({mapping.confidence:.0%})")

        # Strategy 4: Query Pinecone for additional guidance (if available)
        if self.pinecone_retriever and len(mapped_source_cols) < len(df.columns):
            unmapped = [c for c in df.columns if c not in mapped_source_cols]
            pinecone_mappings = self._match_by_pinecone(unmapped, domain, df)
            for mapping in pinecone_mappings:
                if mapping.sdtm_variable not in mapped_sdtm_vars:
                    mappings.append(mapping)
                    mapped_source_cols.add(mapping.source_column)
                    mapped_sdtm_vars.add(mapping.sdtm_variable)
                    logger.info(f"Pinecone match: {mapping.source_column} -> {mapping.sdtm_variable}")

        # Identify unmapped columns and variables
        unmapped_source = [c for c in df.columns if c not in mapped_source_cols]
        unmapped_sdtm = [v for v in sdtm_vars if v not in mapped_sdtm_vars]

        spec = DomainMappingSpec(
            domain=domain,
            mappings=mappings,
            unmapped_source_columns=unmapped_source,
            unmapped_sdtm_variables=unmapped_sdtm
        )

        logger.info(f"Mapping complete: {len(mappings)} mappings, "
                   f"{len(unmapped_source)} unmapped source cols, "
                   f"{len(unmapped_sdtm)} unmapped SDTM vars")

        return spec

    def _get_sdtm_variables(self, domain: str) -> List[str]:
        """
        Get list of SDTM variables for a domain from SDTM-IG 3.4.

        Sources (in priority order):
        1. SDTM-IG 3.4 web reference (authoritative)
        2. Local SDTM_VARIABLE_PATTERNS cache
        3. Pinecone knowledge base
        """
        # First try SDTM-IG 3.4 web reference (most authoritative)
        if self.web_reference:
            try:
                spec = self.web_reference.get_domain_specification(domain)
                if spec and "variables" in spec:
                    all_vars = []
                    for level in ["required", "expected", "permissible"]:
                        for var in spec["variables"].get(level, []):
                            if var.get("name"):
                                all_vars.append(var["name"])
                    if all_vars:
                        logger.info(f"Got {len(all_vars)} variables for {domain} from SDTM-IG 3.4 web reference")
                        return all_vars
            except Exception as e:
                logger.warning(f"Web reference query failed: {e}")

        # Fallback to local patterns
        if domain in self.SDTM_VARIABLE_PATTERNS:
            vars_dict = self.SDTM_VARIABLE_PATTERNS[domain]
            all_vars = []
            for category in vars_dict.values():
                all_vars.extend(category)
            return all_vars

        # Query Pinecone if available
        if self.pinecone_retriever:
            try:
                spec = self.pinecone_retriever.get_domain_specification(domain)
                if spec and "variables" in spec:
                    return [v.get("name") for v in spec["variables"] if v.get("name")]
            except Exception as e:
                logger.warning(f"Pinecone query failed: {e}")

        # Return generic pattern
        prefix = domain
        return [f"{prefix}SEQ", f"{prefix}TERM", f"{prefix}DTC", f"{prefix}STDY"]

    def _match_by_pattern(self, col_name: str, domain: str) -> Optional[ColumnMapping]:
        """Match column name against known patterns."""
        col_upper = col_name.upper()

        for pattern, (sdtm_var, confidence) in self.SOURCE_PATTERNS.items():
            if re.match(pattern, col_name, re.IGNORECASE):
                # Replace domain placeholder
                actual_var = sdtm_var.replace("--", domain) if "--" in sdtm_var else sdtm_var

                # Detect if value transformation needed
                transform = self._detect_transform(actual_var)
                ct_list = self._get_ct_codelist(actual_var)

                return ColumnMapping(
                    source_column=col_name,
                    sdtm_variable=actual_var,
                    confidence=confidence,
                    mapping_reason=f"Pattern match: {pattern}",
                    value_transform=transform,
                    ct_codelist=ct_list
                )

        return None

    def _match_by_fuzzy(self, col_name: str, sdtm_vars: List[str],
                        already_mapped: set) -> Optional[ColumnMapping]:
        """Fuzzy match column name to SDTM variables."""
        col_upper = col_name.upper().replace("_", "").replace("-", "")

        best_match = None
        best_score = 0

        for sdtm_var in sdtm_vars:
            if sdtm_var in already_mapped:
                continue

            var_clean = sdtm_var.upper().replace("_", "")

            # Direct substring match
            if col_upper in var_clean or var_clean in col_upper:
                score = 0.8
            else:
                # Sequence matcher
                score = SequenceMatcher(None, col_upper, var_clean).ratio()

            if score > best_score and score >= 0.6:
                best_score = score
                best_match = sdtm_var

        if best_match:
            return ColumnMapping(
                source_column=col_name,
                sdtm_variable=best_match,
                confidence=best_score,
                mapping_reason=f"Fuzzy match (score: {best_score:.2f})",
                value_transform=self._detect_transform(best_match),
                ct_codelist=self._get_ct_codelist(best_match)
            )

        return None

    def _match_by_values(self, col_name: str, values: pd.Series, domain: str,
                         already_mapped: set) -> Optional[ColumnMapping]:
        """Infer column purpose from actual values."""
        # Get sample of non-null values
        sample = values.dropna().head(100)
        if len(sample) == 0:
            return None

        # Convert to strings for pattern matching
        str_values = sample.astype(str).str.upper().str.strip()
        unique_vals = str_values.unique()

        # Check against value patterns
        for pattern_name, (pattern, value_type) in self.VALUE_PATTERNS.items():
            match_count = sum(1 for v in unique_vals if re.match(pattern, v, re.IGNORECASE))
            match_ratio = match_count / len(unique_vals) if len(unique_vals) > 0 else 0

            if match_ratio >= 0.5:
                # Infer SDTM variable from value type
                sdtm_var = self._infer_var_from_value_type(value_type, domain, col_name, already_mapped)
                if sdtm_var:
                    return ColumnMapping(
                        source_column=col_name,
                        sdtm_variable=sdtm_var,
                        confidence=0.6 * match_ratio + 0.2,
                        mapping_reason=f"Value pattern: {pattern_name} ({match_ratio:.0%} match)",
                        value_transform=value_type,
                        ct_codelist=self._get_ct_codelist(sdtm_var)
                    )

        return None

    def _infer_var_from_value_type(self, value_type: str, domain: str, col_name: str,
                                    already_mapped: set) -> Optional[str]:
        """Infer SDTM variable from detected value type."""
        col_upper = col_name.upper()

        type_to_var = {
            "severity": f"{domain}SEV" if domain in ["AE"] else None,
            "causality": "AEREL" if domain == "AE" else None,
            "outcome": f"{domain}OUT" if domain in ["AE"] else None,
            "sex": "SEX" if domain == "DM" else None,
            "boolean": None,  # Too generic
            "date": None,  # Need more context from column name
        }

        var = type_to_var.get(value_type)
        if var and var not in already_mapped:
            return var

        # For dates, try to infer from column name
        if value_type == "date":
            if "START" in col_upper or "ST" in col_upper or "ONSET" in col_upper:
                return f"{domain}STDTC" if f"{domain}STDTC" not in already_mapped else None
            if "END" in col_upper or "EN" in col_upper or "RESOL" in col_upper:
                return f"{domain}ENDTC" if f"{domain}ENDTC" not in already_mapped else None
            return f"{domain}DTC" if f"{domain}DTC" not in already_mapped else None

        return None

    def _match_by_pinecone(self, unmapped_cols: List[str], domain: str,
                           df: pd.DataFrame) -> List[ColumnMapping]:
        """Query Pinecone knowledge base for mapping suggestions."""
        mappings = []

        if not self.pinecone_retriever:
            return mappings

        try:
            # Get domain specification from Pinecone
            spec = self.pinecone_retriever.get_domain_specification(domain)
            if not spec:
                return mappings

            # Get SDTM variable definitions
            var_definitions = {}
            for var_info in spec.get("variables", []):
                var_name = var_info.get("name", "")
                var_label = var_info.get("label", "")
                var_definitions[var_name] = var_label.lower()

            # Try to match unmapped columns
            for col in unmapped_cols:
                col_lower = col.lower().replace("_", " ").replace("-", " ")

                best_match = None
                best_score = 0

                for var_name, var_label in var_definitions.items():
                    # Check if column name appears in label or vice versa
                    score = SequenceMatcher(None, col_lower, var_label).ratio()

                    if col_lower in var_label or var_label in col_lower:
                        score = max(score, 0.7)

                    if score > best_score and score >= 0.5:
                        best_score = score
                        best_match = var_name

                if best_match:
                    mappings.append(ColumnMapping(
                        source_column=col,
                        sdtm_variable=best_match,
                        confidence=best_score * 0.9,  # Slightly lower confidence for KB matches
                        mapping_reason=f"Pinecone KB match",
                        value_transform=self._detect_transform(best_match),
                        ct_codelist=self._get_ct_codelist(best_match)
                    ))

        except Exception as e:
            logger.warning(f"Pinecone matching failed: {e}")

        return mappings

    def _detect_transform(self, sdtm_var: str) -> Optional[str]:
        """Detect what transformation is needed for a variable."""
        var_upper = sdtm_var.upper()

        if var_upper.endswith("DTC") or var_upper.endswith("DT"):
            return "date"
        if var_upper in ["AEREL", "AEOUT", "AESEV", "AEACN", "SEX", "AESER"]:
            return "controlled_terminology"
        if var_upper.endswith("CD") or var_upper.endswith("NUM") or var_upper.endswith("SEQ"):
            return "numeric"
        if var_upper.endswith("FL"):
            return "boolean"

        return None

    def _get_ct_codelist(self, sdtm_var: str) -> Optional[str]:
        """Get controlled terminology codelist for a variable."""
        var_upper = sdtm_var.upper()

        if var_upper in self.CT_CODELISTS:
            return var_upper
        if var_upper.endswith("SER") or var_upper.endswith("FL"):
            return "NY"

        return None

    def get_mapping_dict(self, spec: DomainMappingSpec) -> Dict[str, str]:
        """Convert mapping spec to simple source->target dictionary."""
        return {m.source_column: m.sdtm_variable for m in spec.mappings}

    def get_value_transformer(self, sdtm_var: str, ct_codelist: Optional[str] = None):
        """
        Get a function to transform values to CDISC Controlled Terminology.

        Uses SDTM-IG 3.4 web reference for authoritative CT values.
        """
        var_upper = sdtm_var.upper()

        # Try to use web reference for CT transformation
        if self.web_reference and ct_codelist:
            def web_transformer(value):
                if pd.isna(value):
                    return ""
                return self.web_reference.transform_to_ct(str(value), ct_codelist)
            return web_transformer

        # Fallback to local controlled terminology transformations
        ct_transforms = {
            "AEREL": {
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
            "AEOUT": {
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

        if var_upper in ct_transforms:
            transform_map = ct_transforms[var_upper]
            def transformer(value):
                if pd.isna(value):
                    return ""
                str_val = str(value).upper().strip()
                return transform_map.get(str_val, str_val)
            return transformer

        return None

    def get_web_mapping_guidance(self, source_column: str, domain: str) -> Optional[Dict]:
        """
        Get mapping guidance from SDTM-IG 3.4 web reference.

        This method provides intelligent mapping suggestions based on:
        1. SDTM-IG 3.4 variable definitions
        2. Pattern matching
        3. Web search for specific guidance

        Args:
            source_column: Source data column name
            domain: Target SDTM domain

        Returns:
            Dict with mapping suggestions or None
        """
        if not self.web_reference:
            return None

        try:
            guidance = self.web_reference.get_mapping_guidance(source_column, domain)
            return guidance
        except Exception as e:
            logger.warning(f"Web mapping guidance failed: {e}")
            return None

    def print_mapping_report(self, spec: DomainMappingSpec) -> str:
        """Generate a human-readable mapping report."""
        lines = [
            f"\n{'='*60}",
            f"INTELLIGENT MAPPING REPORT - {spec.domain} Domain",
            f"{'='*60}\n",
            f"## Discovered Mappings ({len(spec.mappings)} total)\n"
        ]

        # Group by confidence
        high_conf = [m for m in spec.mappings if m.confidence >= 0.8]
        med_conf = [m for m in spec.mappings if 0.6 <= m.confidence < 0.8]
        low_conf = [m for m in spec.mappings if m.confidence < 0.6]

        if high_conf:
            lines.append("### High Confidence (>=80%)")
            for m in high_conf:
                lines.append(f"  {m.source_column:30} -> {m.sdtm_variable:15} ({m.confidence:.0%}) [{m.mapping_reason}]")

        if med_conf:
            lines.append("\n### Medium Confidence (60-80%)")
            for m in med_conf:
                lines.append(f"  {m.source_column:30} -> {m.sdtm_variable:15} ({m.confidence:.0%}) [{m.mapping_reason}]")

        if low_conf:
            lines.append("\n### Low Confidence (<60%)")
            for m in low_conf:
                lines.append(f"  {m.source_column:30} -> {m.sdtm_variable:15} ({m.confidence:.0%}) [{m.mapping_reason}]")

        if spec.unmapped_source_columns:
            lines.append(f"\n## Unmapped Source Columns ({len(spec.unmapped_source_columns)})")
            for col in spec.unmapped_source_columns:
                lines.append(f"  - {col}")

        if spec.unmapped_sdtm_variables:
            lines.append(f"\n## Missing SDTM Variables ({len(spec.unmapped_sdtm_variables)})")
            for var in spec.unmapped_sdtm_variables[:20]:  # Limit output
                lines.append(f"  - {var}")
            if len(spec.unmapped_sdtm_variables) > 20:
                lines.append(f"  ... and {len(spec.unmapped_sdtm_variables) - 20} more")

        lines.append(f"\n{'='*60}\n")

        return "\n".join(lines)


# Convenience function for quick mapping
def create_intelligent_mapping(df: pd.DataFrame, domain: str,
                               pinecone_retriever=None) -> DomainMappingSpec:
    """
    Create intelligent mapping from source DataFrame to SDTM domain.

    Args:
        df: Source DataFrame
        domain: Target SDTM domain
        pinecone_retriever: Optional Pinecone retriever for knowledge base

    Returns:
        DomainMappingSpec with discovered mappings
    """
    mapper = IntelligentMapper(pinecone_retriever)
    return mapper.analyze_source_data(df, domain)

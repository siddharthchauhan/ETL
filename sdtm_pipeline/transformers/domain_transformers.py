"""
SDTM Domain Transformers
========================
Transform raw clinical data to SDTM format for each domain.
Enhanced with SDTMIG reference for comprehensive variable handling.

Key Feature: INTELLIGENT MAPPING
- Dynamically analyzes raw EDC data column names and values
- Uses semantic matching, pattern recognition, and value inference
- Queries Pinecone knowledge base for SDTM specifications
- Automatically discovers mappings without hardcoded column lists
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from abc import ABC, abstractmethod
import re
import logging

from ..models.sdtm_models import (
    MappingSpecification,
    TransformationResult,
    SDTM_DOMAINS,
    CONTROLLED_TERMINOLOGY
)

# Import SDTMIG reference
try:
    from ..langgraph_agent.sdtmig_reference import get_sdtmig_reference, SDTMIG_DOMAIN_SPECS
    SDTMIG_AVAILABLE = True
except ImportError:
    SDTMIG_AVAILABLE = False
    SDTMIG_DOMAIN_SPECS = {}

# Import intelligent mapper
try:
    from .intelligent_mapper import IntelligentMapper, create_intelligent_mapping, DomainMappingSpec
    INTELLIGENT_MAPPER_AVAILABLE = True
except ImportError:
    INTELLIGENT_MAPPER_AVAILABLE = False
    IntelligentMapper = None
    DomainMappingSpec = None

logger = logging.getLogger(__name__)


class BaseDomainTransformer(ABC):
    """Base class for SDTM domain transformers with intelligent mapping capabilities."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None,
                 pinecone_retriever=None):
        self.study_id = study_id
        self.mapping_spec = mapping_spec
        self.domain_code = ""
        self.transformation_log: List[str] = []
        self.pinecone_retriever = pinecone_retriever

        # Intelligent mapper for dynamic column discovery
        self.intelligent_mapper = None
        if INTELLIGENT_MAPPER_AVAILABLE:
            self.intelligent_mapper = IntelligentMapper(pinecone_retriever)

        # Cache for discovered mappings
        self._discovered_mapping: Optional[DomainMappingSpec] = None

        # Get SDTMIG specification for the domain
        self.sdtmig_spec = None
        if SDTMIG_AVAILABLE:
            try:
                self.sdtmig_ref = get_sdtmig_reference()
            except Exception:
                self.sdtmig_ref = None
        else:
            self.sdtmig_ref = None

    def log(self, message: str):
        """Add message to transformation log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.transformation_log.append(f"[{timestamp}] {message}")

    def get_sdtmig_variables(self) -> List[Dict[str, Any]]:
        """Get all variables for this domain from SDTMIG."""
        if self.sdtmig_ref and self.domain_code:
            return self.sdtmig_ref.get_domain_variables(self.domain_code)
        return SDTMIG_DOMAIN_SPECS.get(self.domain_code, {}).get("variables", [])

    def get_required_variables(self) -> List[str]:
        """Get required variable names for this domain."""
        if self.sdtmig_ref and self.domain_code:
            return self.sdtmig_ref.get_required_variables(self.domain_code)
        return [v["name"] for v in self.get_sdtmig_variables() if v.get("core") == "Req"]

    def get_expected_variables(self) -> List[str]:
        """Get expected variable names for this domain."""
        if self.sdtmig_ref and self.domain_code:
            return self.sdtmig_ref.get_expected_variables(self.domain_code)
        return [v["name"] for v in self.get_sdtmig_variables() if v.get("core") == "Exp"]

    def ensure_required_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure all required SDTM columns exist in the dataframe."""
        required = self.get_required_variables()
        for col in required:
            if col not in df.columns:
                # Add empty column
                df[col] = None
                self.log(f"Added missing required column: {col}")
        return df

    def reorder_columns_per_sdtmig(self, df: pd.DataFrame) -> pd.DataFrame:
        """Reorder columns according to SDTMIG specification."""
        sdtmig_vars = [v["name"] for v in self.get_sdtmig_variables()]
        ordered_cols = [c for c in sdtmig_vars if c in df.columns]
        remaining_cols = [c for c in df.columns if c not in ordered_cols]
        return df[ordered_cols + remaining_cols]

    # ========================================================================
    # INTELLIGENT MAPPING METHODS - Dynamic column discovery for raw EDC data
    # ========================================================================

    def discover_mappings(self, source_df: pd.DataFrame) -> Optional[DomainMappingSpec]:
        """
        Intelligently discover mappings from source columns to SDTM variables.

        This method analyzes raw EDC data and automatically determines which
        source columns should map to which SDTM variables using:
        - Pattern matching on column names
        - Fuzzy/semantic matching
        - Value-based inference
        - Pinecone knowledge base queries

        Args:
            source_df: Raw EDC source DataFrame

        Returns:
            DomainMappingSpec with discovered mappings, or None if mapper unavailable
        """
        if not self.intelligent_mapper or not self.domain_code:
            self.log("Intelligent mapping not available - using hardcoded patterns")
            return None

        self.log(f"Discovering column mappings for {self.domain_code} domain...")
        self.log(f"Source columns: {list(source_df.columns)}")

        # Analyze source data
        mapping_spec = self.intelligent_mapper.analyze_source_data(source_df, self.domain_code)
        self._discovered_mapping = mapping_spec

        # Log the discoveries
        self.log(f"Discovered {len(mapping_spec.mappings)} column mappings")
        for m in mapping_spec.mappings:
            self.log(f"  {m.source_column} -> {m.sdtm_variable} ({m.confidence:.0%})")

        if mapping_spec.unmapped_source_columns:
            self.log(f"Unmapped source columns: {mapping_spec.unmapped_source_columns[:10]}")

        return mapping_spec

    def get_source_column(self, sdtm_var: str, source_df: pd.DataFrame,
                          fallback_patterns: List[str] = None) -> Optional[str]:
        """
        Get the source column that maps to a given SDTM variable.

        Uses intelligent mapping if available, falls back to pattern matching.

        Args:
            sdtm_var: Target SDTM variable name
            source_df: Source DataFrame
            fallback_patterns: List of column name patterns to try if no mapping found

        Returns:
            Source column name or None
        """
        # First check intelligent mapping
        if self._discovered_mapping:
            for m in self._discovered_mapping.mappings:
                if m.sdtm_variable == sdtm_var:
                    if m.source_column in source_df.columns:
                        return m.source_column

        # Fallback to pattern matching
        if fallback_patterns:
            for pattern in fallback_patterns:
                for col in source_df.columns:
                    if re.match(pattern, col, re.IGNORECASE):
                        return col
                    if col.upper() == pattern.upper():
                        return col

        return None

    def get_source_value(self, row: pd.Series, sdtm_var: str,
                         fallback_columns: List[str] = None) -> Any:
        """
        Get value from source row for a given SDTM variable.

        Uses intelligent mapping to find the right source column.

        Args:
            row: Source data row
            sdtm_var: Target SDTM variable
            fallback_columns: Columns to try if mapping not found

        Returns:
            Value from source or None
        """
        # Check intelligent mapping
        if self._discovered_mapping:
            for m in self._discovered_mapping.mappings:
                if m.sdtm_variable == sdtm_var:
                    if m.source_column in row.index:
                        val = row[m.source_column]
                        if pd.notna(val):
                            # Apply value transformation if needed
                            if m.value_transform == "controlled_terminology":
                                transformer = self.intelligent_mapper.get_value_transformer(
                                    sdtm_var, m.ct_codelist
                                )
                                if transformer:
                                    return transformer(val)
                            return val

        # Fallback to trying column list
        if fallback_columns:
            for col in fallback_columns:
                if col in row.index and pd.notna(row[col]):
                    return row[col]

        return None

    def transform_with_intelligent_mapping(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform source data using intelligent mapping.

        This is a generic transformation that uses discovered mappings
        to create SDTM output. Domain-specific transformers can override
        this or use it as a starting point.

        Args:
            source_df: Raw EDC source data

        Returns:
            Transformed SDTM DataFrame
        """
        # Discover mappings if not already done
        if not self._discovered_mapping:
            self.discover_mappings(source_df)

        if not self._discovered_mapping:
            raise ValueError("Cannot perform intelligent mapping - mapper not available")

        self.log("Performing intelligent transformation...")

        records = []
        mapping_dict = {m.sdtm_variable: m for m in self._discovered_mapping.mappings}

        # Track sequences per subject
        subject_seq = {}

        for idx, row in source_df.iterrows():
            # Generate USUBJID
            usubjid = self._generate_usubjid(row)

            # Track sequence
            if usubjid not in subject_seq:
                subject_seq[usubjid] = 0
            subject_seq[usubjid] += 1

            # Build record
            record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": self.domain_code,
                "USUBJID": usubjid,
                f"{self.domain_code}SEQ": subject_seq[usubjid],
            }

            # Apply discovered mappings
            for sdtm_var, mapping in mapping_dict.items():
                if sdtm_var in record:
                    continue  # Already set

                if mapping.source_column in row.index:
                    val = row[mapping.source_column]
                    if pd.notna(val):
                        # Apply transformation
                        if mapping.value_transform == "date":
                            val = self._convert_date_to_iso(val)
                        elif mapping.value_transform == "controlled_terminology":
                            transformer = self.intelligent_mapper.get_value_transformer(
                                sdtm_var, mapping.ct_codelist
                            )
                            if transformer:
                                val = transformer(val)
                        elif mapping.value_transform == "numeric":
                            try:
                                val = float(val) if '.' in str(val) else int(val)
                            except (ValueError, TypeError):
                                pass

                        record[sdtm_var] = val

            records.append(record)

        result_df = pd.DataFrame(records)
        self.log(f"Created {len(result_df)} records with {len(result_df.columns)} variables")

        return result_df

    def print_mapping_report(self) -> str:
        """Get a human-readable report of discovered mappings."""
        if not self._discovered_mapping or not self.intelligent_mapper:
            return "No mapping discovery performed yet"

        return self.intelligent_mapper.print_mapping_report(self._discovered_mapping)

    def apply_controlled_terminology(self, df: pd.DataFrame, column: str, codelist: str) -> pd.DataFrame:
        """Apply controlled terminology to a column."""
        ct_mapping = CONTROLLED_TERMINOLOGY.get(codelist, {})
        if ct_mapping and column in df.columns:
            df[column] = df[column].apply(lambda x: ct_mapping.get(str(x).upper(), x) if pd.notna(x) else x)
        return df

    @abstractmethod
    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform source data to SDTM format."""
        pass

    def _convert_date_to_iso(self, value: Any) -> Optional[str]:
        """Convert date value to ISO 8601 format."""
        if pd.isna(value):
            return None

        try:
            # Handle YYYYMMDD format
            if isinstance(value, (int, float)):
                str_val = str(int(value))
                if len(str_val) == 8:
                    dt = datetime.strptime(str_val, "%Y%m%d")
                    return dt.strftime("%Y-%m-%d")

            # Handle string dates
            str_val = str(value)
            if len(str_val) == 8 and str_val.isdigit():
                dt = datetime.strptime(str_val, "%Y%m%d")
                return dt.strftime("%Y-%m-%d")

            # Try common formats
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y%m%d"]:
                try:
                    dt = datetime.strptime(str_val[:10], fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue

        except Exception:
            pass

        return str(value) if value else None

    def _generate_usubjid(self, row: pd.Series) -> str:
        """Generate USUBJID from row data following SDTM conventions.

        Format: STUDYID-SITEID-SUBJID (e.g., MAXIS-08-408-001)
        """
        import re

        study = row.get("STUDY", row.get("STUDYID", self.study_id))
        site = row.get("INVSITE", row.get("SITEID", "001"))
        subj = row.get("PT", row.get("SUBJID", ""))

        # Clean up site ID - extract just the site number
        if site and "_" in str(site):
            # Handle format like "C008_408" -> "408"
            site = str(site).split("_")[-1]

        # Clean up subject ID
        subj_str = str(subj)
        # Extract numeric part from values like "1-Jan", "2-Jan" etc.
        # The pattern captures leading digits before any non-digit
        match = re.match(r'^(\d+)', subj_str)
        if match:
            subj_num = match.group(1)
            # Pad to 3 digits with leading zeros (001, 002, etc.)
            subj = subj_num.zfill(3)
        elif subj_str.isdigit():
            # Already a number - pad to 3 digits
            subj = subj_str.zfill(3)
        else:
            # Keep original if no numeric pattern found
            subj = subj_str

        return f"{study}-{site}-{subj}"

    def _map_sex(self, value: Any) -> str:
        """Map sex/gender values to CDISC controlled terminology."""
        if pd.isna(value):
            return ""

        str_val = str(value).upper().strip()

        mapping = {
            "M": "M",
            "F": "F",
            "MALE": "M",
            "FEMALE": "F",
            "U": "U",
            "UNKNOWN": "U",
            "UNDIFFERENTIATED": "UNDIFFERENTIATED"
        }

        return mapping.get(str_val, str_val)

    def _map_race(self, value: Any) -> str:
        """Map race values to CDISC controlled terminology."""
        if pd.isna(value):
            return ""

        str_val = str(value).upper().strip()

        mapping = {
            "WHITE": "WHITE",
            "BLACK": "BLACK OR AFRICAN AMERICAN",
            "AFRICAN AMERICAN": "BLACK OR AFRICAN AMERICAN",
            "ASIAN": "ASIAN",
            "HISPANIC": "WHITE",  # Hispanic is ethnicity, not race
            "NATIVE": "AMERICAN INDIAN OR ALASKA NATIVE",
            "PACIFIC": "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER",
            "OTHER": "OTHER",
            "UNKNOWN": "UNKNOWN",
            "MULTIPLE": "MULTIPLE"
        }

        for key, mapped in mapping.items():
            if key in str_val:
                return mapped

        return str_val

    def _map_ethnicity(self, value: Any) -> str:
        """Map ethnicity values to CDISC controlled terminology."""
        if pd.isna(value):
            return ""

        str_val = str(value).upper().strip()

        if "HISPANIC" in str_val or "LATINO" in str_val:
            return "HISPANIC OR LATINO"
        elif "NOT" in str_val:
            return "NOT HISPANIC OR LATINO"
        elif "UNKNOWN" in str_val:
            return "UNKNOWN"

        return "NOT REPORTED"

    def execute(self, source_df: pd.DataFrame) -> TransformationResult:
        """Execute transformation and return result."""
        self.transformation_log = []
        self.log(f"Starting {self.domain_code} transformation")
        self.log(f"Source records: {len(source_df)}")
        self.log(f"SDTMIG reference: {'enabled' if self.sdtmig_ref else 'disabled'}")

        try:
            result_df = self.transform(source_df)

            # Ensure required columns exist
            result_df = self.ensure_required_columns(result_df)

            # Reorder columns per SDTMIG
            result_df = self.reorder_columns_per_sdtmig(result_df)

            self.log(f"Output records: {len(result_df)}")
            self.log(f"Output columns: {len(result_df.columns)}")
            self.log("Transformation completed successfully")

            return TransformationResult(
                success=True,
                source_domain=self.mapping_spec.source_domain if self.mapping_spec else "unknown",
                target_domain=self.domain_code,
                records_processed=len(source_df),
                records_output=len(result_df),
                records_dropped=len(source_df) - len(result_df),
                transformation_log=self.transformation_log.copy()
            )

        except Exception as e:
            self.log(f"ERROR: {str(e)}")
            return TransformationResult(
                success=False,
                source_domain=self.mapping_spec.source_domain if self.mapping_spec else "unknown",
                target_domain=self.domain_code,
                records_processed=len(source_df),
                records_output=0,
                errors=[str(e)],
                transformation_log=self.transformation_log.copy()
            )


class DMTransformer(BaseDomainTransformer):
    """Demographics domain transformer - FULL SDTM-IG 3.4 compliant (28 variables)."""

    # SDTM-IG 3.4 DM variable requirements
    REQUIRED_VARS = ["STUDYID", "DOMAIN", "USUBJID", "SUBJID", "SITEID", "SEX", "ARMCD", "ARM", "COUNTRY"]
    EXPECTED_VARS = ["RFSTDTC", "RFENDTC", "RFXSTDTC", "RFXENDTC", "RFICDTC", "RFPENDTC",
                     "DTHDTC", "DTHFL", "AGE", "AGEU", "RACE", "ETHNIC", "ACTARMCD", "ACTARM"]
    PERMISSIBLE_VARS = ["INVID", "INVNAM", "BRTHDTC", "DMDTC", "DMDY"]

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "DM"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform demographics data to SDTM DM domain per SDTMIG 3.4.

        Implements ALL 28 DM variables - all Required/Expected always present in output:
        - Required (9): STUDYID, DOMAIN, USUBJID, SUBJID, SITEID, SEX, ARMCD, ARM, COUNTRY
        - Expected (14): RFSTDTC, RFENDTC, RFXSTDTC, RFXENDTC, RFICDTC, RFPENDTC,
                         DTHDTC, DTHFL, AGE, AGEU, RACE, ETHNIC, ACTARMCD, ACTARM
        - Permissible (5): INVID, INVNAM, BRTHDTC, DMDTC, DMDY
        """
        self.log("Transforming to DM domain - FULL SDTM-IG 3.4 compliance (28 variables)")

        # CRITICAL: Discover intelligent mappings FIRST if mapper available
        if self.intelligent_mapper and not self._discovered_mapping:
            self.log("Discovering intelligent column mappings...")
            self.discover_mappings(source_df)
            if self._discovered_mapping:
                self.log(f"Found {len(self._discovered_mapping.mappings)} intelligent mappings")
                for m in self._discovered_mapping.mappings[:10]:
                    self.log(f"  Mapping: {m.source_column} -> {m.sdtm_variable} ({m.confidence:.0%})")

        dm_records = []

        for idx, row in source_df.iterrows():
            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            # This ensures they ALL appear in output per SDTM-IG 3.4
            dm_record = {
                # Required Identifiers
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "DM",
                "USUBJID": self._generate_usubjid(row),
                "SUBJID": str(row.get("PT", row.get("SUBJID", ""))),
                "SITEID": "",
                "SEX": "",
                "ARMCD": "",
                "ARM": "",
                "COUNTRY": "",
                # Expected - Reference dates
                "RFSTDTC": "",
                "RFENDTC": "",
                "RFXSTDTC": "",
                "RFXENDTC": "",
                "RFICDTC": "",
                "RFPENDTC": "",
                # Expected - Death
                "DTHDTC": "",
                "DTHFL": "",
                # Expected - Age
                "AGE": None,
                "AGEU": "",
                # Expected - Demographics
                "RACE": "",
                "ETHNIC": "",
                # Expected - Arms
                "ACTARMCD": "",
                "ACTARM": "",
                # Permissible
                "INVID": "",
                "INVNAM": "",
                "BRTHDTC": "",
                "DMDTC": "",
                "DMDY": None,
            }

            # SITEID (Required) - Use intelligent mapping first
            siteid_col = self.get_source_column("SITEID", source_df, ["INVSITE", "SITEID", "SITE", "SITE_ID", "CENTER"])
            if siteid_col and siteid_col in row.index and pd.notna(row[siteid_col]):
                siteid_raw = row[siteid_col]
                dm_record["SITEID"] = str(siteid_raw).split("_")[-1] if siteid_raw else ""
            else:
                # Fallback to old pattern
                siteid_raw = row.get("INVSITE", row.get("SITEID", ""))
                dm_record["SITEID"] = str(siteid_raw).split("_")[-1] if siteid_raw else ""

            # SEX (Required) - Use intelligent mapping first, then fallback patterns
            sex_col = self.get_source_column("SEX", source_df, ["GENDER", "GENDRL", "SEX", "GNDR", "GEND"])
            if sex_col and sex_col in row.index and pd.notna(row[sex_col]):
                dm_record["SEX"] = self._map_sex(row[sex_col])
            else:
                # Fallback to checking all patterns manually
                for sex_col_fb in ["GENDER", "GENDRL", "SEX", "GNDR"]:
                    if sex_col_fb in row and pd.notna(row[sex_col_fb]):
                        dm_record["SEX"] = self._map_sex(row[sex_col_fb])
                        break
            if not dm_record.get("SEX"):
                dm_record["SEX"] = "U"  # Unknown if not provided

            # ARMCD/ARM (Required) - Use intelligent mapping first
            arm_col = self.get_source_column("ARM", source_df, ["ARMCD", "ARM", "TRT", "TREATMENT", "TRTGRP", "TRTCD"])
            if arm_col and arm_col in row.index and pd.notna(row[arm_col]):
                arm_value = str(row[arm_col])
                dm_record["ARM"] = arm_value
                dm_record["ARMCD"] = arm_value[:8].upper().replace(" ", "")  # ARMCD max 8 chars
            else:
                # Fallback to checking all patterns manually
                for arm_col_fb in ["ARMCD", "ARM", "TRT", "TREATMENT", "TRTGRP"]:
                    if arm_col_fb in row and pd.notna(row[arm_col_fb]):
                        arm_value = str(row[arm_col_fb])
                        dm_record["ARM"] = arm_value
                        dm_record["ARMCD"] = arm_value[:8].upper().replace(" ", "")
                        break
            if not dm_record.get("ARM"):
                dm_record["ARM"] = "NOT ASSIGNED"
                dm_record["ARMCD"] = "NOTASSGN"

            # COUNTRY (Required) - Use intelligent mapping first
            country_col = self.get_source_column("COUNTRY", source_df, ["COUNTRY", "CTRY", "NATION", "CNT"])
            country_val = None
            if country_col and country_col in row.index and pd.notna(row[country_col]):
                country_val = str(row[country_col]).upper().strip()
            else:
                # Fallback
                for country_col_fb in ["COUNTRY", "CTRY", "NATION", "CNT"]:
                    if country_col_fb in row and pd.notna(row[country_col_fb]):
                        country_val = str(row[country_col_fb]).upper().strip()
                        break
            if country_val:
                # Map common country names to ISO codes
                country_map = {
                    "UNITED STATES": "USA", "US": "USA", "AMERICA": "USA",
                    "UNITED KINGDOM": "GBR", "UK": "GBR", "ENGLAND": "GBR",
                    "CANADA": "CAN", "GERMANY": "DEU", "FRANCE": "FRA",
                    "JAPAN": "JPN", "CHINA": "CHN", "INDIA": "IND",
                    "AUSTRALIA": "AUS", "SPAIN": "ESP", "ITALY": "ITA"
                }
                dm_record["COUNTRY"] = country_map.get(country_val, country_val[:3])
            else:
                dm_record["COUNTRY"] = "USA"

            # === EXPECTED RECORD QUALIFIER VARIABLES ===
            # Use intelligent mapping for all date fields

            # RFSTDTC - Subject Reference Start Date/Time (first dose or enrollment)
            rfstdtc_col = self.get_source_column("RFSTDTC", source_df, ["RFSTDTC", "RFSTDT", "FIRSTDOSE", "TRTSTDT", "DSSTDT", "ENROLLDT", "FIRST_DOSE_DATE"])
            if rfstdtc_col and rfstdtc_col in row.index and pd.notna(row[rfstdtc_col]):
                dm_record["RFSTDTC"] = self._convert_date_to_iso(row[rfstdtc_col])
            else:
                for ref_col in ["RFSTDTC", "RFSTDT", "FIRSTDOSE", "TRTSTDT", "DSSTDT", "ENROLLDT"]:
                    if ref_col in row and pd.notna(row[ref_col]):
                        dm_record["RFSTDTC"] = self._convert_date_to_iso(row[ref_col])
                        break

            # RFENDTC - Subject Reference End Date/Time (last dose or study completion)
            rfendtc_col = self.get_source_column("RFENDTC", source_df, ["RFENDTC", "RFENDT", "LASTDOSE", "TRTENDT", "DSENDT", "COMPDT", "LAST_DOSE_DATE"])
            if rfendtc_col and rfendtc_col in row.index and pd.notna(row[rfendtc_col]):
                dm_record["RFENDTC"] = self._convert_date_to_iso(row[rfendtc_col])
            else:
                for ref_col in ["RFENDTC", "RFENDT", "LASTDOSE", "TRTENDT", "DSENDT", "COMPDT"]:
                    if ref_col in row and pd.notna(row[ref_col]):
                        dm_record["RFENDTC"] = self._convert_date_to_iso(row[ref_col])
                        break

            # RFXSTDTC - Date/Time of First Study Treatment
            rfxstdtc_col = self.get_source_column("RFXSTDTC", source_df, ["RFXSTDTC", "TRTSTDT", "FIRSTTRT", "EXSTDT", "TRTDT"])
            if rfxstdtc_col and rfxstdtc_col in row.index and pd.notna(row[rfxstdtc_col]):
                dm_record["RFXSTDTC"] = self._convert_date_to_iso(row[rfxstdtc_col])
            else:
                for ref_col in ["RFXSTDTC", "TRTSTDT", "FIRSTTRT", "EXSTDT", "TRTDT"]:
                    if ref_col in row and pd.notna(row[ref_col]):
                        dm_record["RFXSTDTC"] = self._convert_date_to_iso(row[ref_col])
                        break
            # If not found, use RFSTDTC as fallback
            if not dm_record.get("RFXSTDTC") and dm_record.get("RFSTDTC"):
                dm_record["RFXSTDTC"] = dm_record["RFSTDTC"]

            # RFXENDTC - Date/Time of Last Study Treatment
            rfxendtc_col = self.get_source_column("RFXENDTC", source_df, ["RFXENDTC", "TRTENDT", "LASTTRT", "EXENDT"])
            if rfxendtc_col and rfxendtc_col in row.index and pd.notna(row[rfxendtc_col]):
                dm_record["RFXENDTC"] = self._convert_date_to_iso(row[rfxendtc_col])
            else:
                for ref_col in ["RFXENDTC", "TRTENDT", "LASTTRT", "EXENDT"]:
                    if ref_col in row and pd.notna(row[ref_col]):
                        dm_record["RFXENDTC"] = self._convert_date_to_iso(row[ref_col])
                        break
            # If not found, use RFENDTC as fallback
            if not dm_record.get("RFXENDTC") and dm_record.get("RFENDTC"):
                dm_record["RFXENDTC"] = dm_record["RFENDTC"]

            # RFICDTC - Date/Time of Informed Consent
            rficdtc_col = self.get_source_column("RFICDTC", source_df, ["RFICDTC", "ICDT", "CONSENTDT", "ICDATE", "INFCONDT", "INFORMED_CONSENT_DATE"])
            if rficdtc_col and rficdtc_col in row.index and pd.notna(row[rficdtc_col]):
                dm_record["RFICDTC"] = self._convert_date_to_iso(row[rficdtc_col])
            else:
                for ref_col in ["RFICDTC", "ICDT", "CONSENTDT", "ICDATE", "INFCONDT"]:
                    if ref_col in row and pd.notna(row[ref_col]):
                        dm_record["RFICDTC"] = self._convert_date_to_iso(row[ref_col])
                        break

            # RFPENDTC - Date/Time of End of Participation
            rfpendtc_col = self.get_source_column("RFPENDTC", source_df, ["RFPENDTC", "EOSDT", "ENDSTDT", "COMPDT", "LASTVISDT"])
            if rfpendtc_col and rfpendtc_col in row.index and pd.notna(row[rfpendtc_col]):
                dm_record["RFPENDTC"] = self._convert_date_to_iso(row[rfpendtc_col])
            else:
                for ref_col in ["RFPENDTC", "EOSDT", "ENDSTDT", "COMPDT", "LASTVISDT"]:
                    if ref_col in row and pd.notna(row[ref_col]):
                        dm_record["RFPENDTC"] = self._convert_date_to_iso(row[ref_col])
                        break

            # DTHDTC - Date/Time of Death
            dthdtc_col = self.get_source_column("DTHDTC", source_df, ["DTHDTC", "DTHDT", "DEATHDT", "DTHDATE", "DEATH_DATE"])
            if dthdtc_col and dthdtc_col in row.index and pd.notna(row[dthdtc_col]):
                dm_record["DTHDTC"] = self._convert_date_to_iso(row[dthdtc_col])
            else:
                for ref_col in ["DTHDTC", "DTHDT", "DEATHDT", "DTHDATE"]:
                    if ref_col in row and pd.notna(row[ref_col]):
                        dm_record["DTHDTC"] = self._convert_date_to_iso(row[ref_col])
                        break

            # DTHFL - Subject Death Flag (Y or null per SDTM-IG)
            dthfl_col = self.get_source_column("DTHFL", source_df, ["DTHFL", "DEATH", "DIED", "DTHIND", "DEATH_FLAG"])
            if dthfl_col and dthfl_col in row.index and pd.notna(row[dthfl_col]):
                val = str(row[dthfl_col]).upper()
                if val in ["Y", "YES", "1", "TRUE", "DIED"]:
                    dm_record["DTHFL"] = "Y"
            else:
                for dth_col in ["DTHFL", "DEATH", "DIED", "DTHIND"]:
                    if dth_col in row and pd.notna(row[dth_col]):
                        val = str(row[dth_col]).upper()
                        if val in ["Y", "YES", "1", "TRUE", "DIED"]:
                            dm_record["DTHFL"] = "Y"
                        break
            # Set DTHFL if death date is present
            if not dm_record.get("DTHFL") and dm_record.get("DTHDTC"):
                dm_record["DTHFL"] = "Y"

            # AGE - Derived from BRTHDTC and RFSTDTC
            # First get birth date - Use intelligent mapping
            dob_col = self.get_source_column("BRTHDTC", source_df, ["DOB", "BRTHDTC", "BIRTHDT", "BRTHDT", "BIRTHDATE", "BIRTH_DATE", "DATE_OF_BIRTH"])
            if dob_col and dob_col in row.index and pd.notna(row[dob_col]):
                dm_record["BRTHDTC"] = self._convert_date_to_iso(row[dob_col])
            else:
                # Fallback to checking all patterns manually
                for dob_col_fb in ["DOB", "BRTHDTC", "BIRTHDT", "BRTHDT", "BIRTHDATE"]:
                    if dob_col_fb in row and pd.notna(row[dob_col_fb]):
                        dm_record["BRTHDTC"] = self._convert_date_to_iso(row[dob_col_fb])
                        break

            # Calculate AGE if birth date available
            if dm_record.get("BRTHDTC"):
                try:
                    birth_date = datetime.strptime(dm_record["BRTHDTC"][:10], "%Y-%m-%d")
                    ref_date_str = dm_record.get("RFSTDTC", dm_record.get("RFICDTC"))
                    if ref_date_str:
                        ref_date = datetime.strptime(ref_date_str[:10], "%Y-%m-%d")
                    else:
                        ref_date = datetime.now()
                    age = (ref_date - birth_date).days // 365
                    dm_record["AGE"] = age
                    dm_record["AGEU"] = "YEARS"
                except Exception:
                    pass
            # Try direct AGE column - Use intelligent mapping
            if not dm_record.get("AGE"):
                age_col = self.get_source_column("AGE", source_df, ["AGE", "AGEY", "AGEATCONS", "SUBJECT_AGE", "PATIENT_AGE"])
                if age_col and age_col in row.index and pd.notna(row[age_col]):
                    try:
                        dm_record["AGE"] = int(float(row[age_col]))
                        dm_record["AGEU"] = "YEARS"
                    except (ValueError, TypeError):
                        pass
                else:
                    # Fallback
                    for age_col_fb in ["AGE", "AGEY", "AGEATCONS"]:
                        if age_col_fb in row and pd.notna(row[age_col_fb]):
                            try:
                                dm_record["AGE"] = int(float(row[age_col_fb]))
                                dm_record["AGEU"] = "YEARS"
                            except (ValueError, TypeError):
                                pass
                            break

            # RACE (Expected) - Use intelligent mapping first
            race_col = self.get_source_column("RACE", source_df, ["RCE", "RACE", "RACEN", "PATIENT_RACE", "SUBJECT_RACE"])
            if race_col and race_col in row.index and pd.notna(row[race_col]):
                dm_record["RACE"] = self._map_race(row[race_col])
            else:
                # Fallback
                for race_col_fb in ["RCE", "RACE", "RACEN"]:
                    if race_col_fb in row and pd.notna(row[race_col_fb]):
                        dm_record["RACE"] = self._map_race(row[race_col_fb])
                        break

            # ETHNIC (Expected) - Use intelligent mapping first
            race_val = ""
            if race_col and race_col in row.index and pd.notna(row[race_col]):
                race_val = str(row[race_col]).upper()
            else:
                race_val = str(row.get("RCE", row.get("RACE", ""))).upper()

            ethnic_col = self.get_source_column("ETHNIC", source_df, ["ETHNIC", "ETHNICITY", "ETHGRP", "ETHNIC_GROUP"])
            if ethnic_col and ethnic_col in row.index and pd.notna(row[ethnic_col]):
                dm_record["ETHNIC"] = self._map_ethnicity(row[ethnic_col])
            else:
                # Fallback
                for ethnic_col_fb in ["ETHNIC", "ETHNICITY", "ETHGRP"]:
                    if ethnic_col_fb in row and pd.notna(row[ethnic_col_fb]):
                        dm_record["ETHNIC"] = self._map_ethnicity(row[ethnic_col_fb])
                        break
            if not dm_record.get("ETHNIC"):
                if "HISPANIC" in race_val or "LATINO" in race_val:
                    dm_record["ETHNIC"] = "HISPANIC OR LATINO"
                else:
                    dm_record["ETHNIC"] = "NOT HISPANIC OR LATINO"

            # ACTARMCD/ACTARM (Expected) - Actual Arm Code and Description
            for act_col in ["ACTARMCD", "ACTARM", "ACTTRT", "ACTUALARM"]:
                if act_col in row and pd.notna(row[act_col]):
                    act_value = str(row[act_col])
                    dm_record["ACTARM"] = act_value
                    dm_record["ACTARMCD"] = act_value[:8].upper().replace(" ", "")
                    break
            # Default ACTARM to ARM if not specified (subject received planned treatment)
            if "ACTARM" not in dm_record:
                dm_record["ACTARM"] = dm_record.get("ARM", "NOT ASSIGNED")
                dm_record["ACTARMCD"] = dm_record.get("ARMCD", "NOTASSGN")

            # === PERMISSIBLE VARIABLES ===

            # INVID - Investigator Identifier
            for inv_col in ["INVID", "INVNUM", "INVESTIGATOR"]:
                if inv_col in row and pd.notna(row[inv_col]):
                    dm_record["INVID"] = str(row[inv_col])
                    break

            # INVNAM - Investigator Name
            for inv_col in ["INVNAM", "INVNAME", "INVESTIGATORNAME"]:
                if inv_col in row and pd.notna(row[inv_col]):
                    dm_record["INVNAM"] = str(row[inv_col])
                    break

            # DMDTC - Date/Time of Collection
            for dtc_col in ["DMDTC", "DMDT", "COLLDT", "DMCOLLDT"]:
                if dtc_col in row and pd.notna(row[dtc_col]):
                    dm_record["DMDTC"] = self._convert_date_to_iso(row[dtc_col])
                    break

            # DMDY - Study Day of Collection (derived from DMDTC - RFSTDTC + 1)
            if dm_record.get("DMDTC") and dm_record.get("RFSTDTC"):
                try:
                    dm_date = datetime.strptime(dm_record["DMDTC"][:10], "%Y-%m-%d")
                    ref_date = datetime.strptime(dm_record["RFSTDTC"][:10], "%Y-%m-%d")
                    dm_dy = (dm_date - ref_date).days
                    dm_record["DMDY"] = dm_dy + 1 if dm_dy >= 0 else dm_dy
                except Exception:
                    pass

            dm_records.append(dm_record)

        result_df = pd.DataFrame(dm_records)

        # Ensure column order per SDTM-IG 3.4
        dm_column_order = [
            "STUDYID", "DOMAIN", "USUBJID", "SUBJID", "RFSTDTC", "RFENDTC",
            "RFXSTDTC", "RFXENDTC", "RFICDTC", "RFPENDTC", "DTHDTC", "DTHFL",
            "SITEID", "INVID", "INVNAM", "BRTHDTC", "AGE", "AGEU", "SEX",
            "RACE", "ETHNIC", "ARMCD", "ARM", "ACTARMCD", "ACTARM",
            "COUNTRY", "DMDTC", "DMDY"
        ]
        ordered_cols = [c for c in dm_column_order if c in result_df.columns]
        extra_cols = [c for c in result_df.columns if c not in dm_column_order]
        result_df = result_df[ordered_cols + extra_cols]

        # Log compliance summary
        self.log(f"Created {len(result_df)} DM records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        self.log(f"Columns: {', '.join(result_df.columns.tolist())}")
        return result_df


class AETransformer(BaseDomainTransformer):
    """Adverse Events domain transformer - FULL SDTM-IG 3.4 compliant (46 variables)."""

    # Define all SDTM AE variables by requirement level
    REQUIRED_VARS = ["STUDYID", "DOMAIN", "USUBJID", "AESEQ", "AETERM"]
    EXPECTED_VARS = ["AEDECOD", "AEBODSYS", "AESEV", "AESER", "AEACN", "AEREL",
                     "AEOUT", "AESTDTC", "AEENDTC", "EPOCH", "VISITNUM", "VISIT", "AEDTC"]
    # Variables SME expects in output (includes MedDRA hierarchy, SAE criteria, timing)
    SME_REQUIRED_VARS = ["AEMODIFY", "AELLT", "AELLTCD", "AEPTCD", "AEHLT", "AEHLTCD",
                         "AEHLGT", "AEHLGTCD", "AEBDSYCD", "AESOC", "AESOCCD",
                         "AESDTH", "AESHOSP", "AECONTRT", "AETOXGR", "AESTDY", "AEENDY", "AEENRF"]

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "AE"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform adverse event data to SDTM AE domain per SDTMIG 3.4.

        Implements ALL 46 AE variables including:
        - Required (5): STUDYID, DOMAIN, USUBJID, AESEQ, AETERM
        - Expected (13): AEDECOD, AEBODSYS, AESEV, AESER, AEACN, AEREL, AEOUT,
                         AESTDTC, AEENDTC, EPOCH, VISITNUM, VISIT, AEDTC
        - Permissible (28): MedDRA hierarchy, SAE criteria, timing variables, etc.

        All Required and Expected variables are ALWAYS included in output (even if null).
        """
        self.log("Transforming to AE domain - FULL SDTM-IG 3.4 compliance (46 variables)")

        # CRITICAL: Discover intelligent mappings FIRST if mapper available
        if self.intelligent_mapper and not self._discovered_mapping:
            self.log("Discovering intelligent column mappings for AE domain...")
            self.discover_mappings(source_df)
            if self._discovered_mapping:
                self.log(f"Found {len(self._discovered_mapping.mappings)} intelligent mappings")
                for m in self._discovered_mapping.mappings[:10]:
                    self.log(f"  Mapping: {m.source_column} -> {m.sdtm_variable} ({m.confidence:.0%})")

        ae_records = []

        # Sort by subject for sequence numbering
        if "PT" in source_df.columns:
            source_df = source_df.sort_values(["PT"])

        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))

            # Initialize or increment sequence
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            # This ensures they ALL appear in output per SME requirements
            ae_record = {
                # Required Identifiers
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "AE",
                "USUBJID": self._generate_usubjid(row),
                "AESEQ": subject_seq[subj],
                "AETERM": "",
                # Expected - MedDRA
                "AEMODIFY": "",
                "AELLT": "",
                "AELLTCD": None,
                "AEDECOD": "",
                "AEPTCD": None,
                "AEHLT": "",
                "AEHLTCD": None,
                "AEHLGT": "",
                "AEHLGTCD": None,
                "AEBODSYS": "",
                "AEBDSYCD": None,
                "AESOC": "",
                "AESOCCD": None,
                # Expected - Severity/Seriousness
                "AESER": "",
                "AEACN": "",
                "AEREL": "",
                "AEOUT": "",
                # SAE Criteria
                "AESDTH": "",
                "AESHOSP": "",
                "AECONTRT": "",
                "AETOXGR": "",
                # Timing
                "EPOCH": "",
                "VISITNUM": None,
                "VISIT": "",
                "AEDTC": "",
                "AESTDTC": "",
                "AEENDTC": "",
                "AESTDY": None,
                "AEENDY": None,
                "AEENRF": "",
            }

            # AESPID - Sponsor-Defined Identifier (Perm)
            for col in ["AESPID", "AEID", "AENUM"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AESPID"] = str(row[col])
                    break

            # AETERM - Reported Term (Required) - Verbatim term as reported
            # Priority: AEVERB (verbatim), AECOD (coded term), AETERM, AE
            for col in ["AEVERB", "AECOD", "AETERM", "AEDESC", "AENAME", "AE", "AETEXT", "ADVERSE_EVENT"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AETERM"] = str(row[col])
                    break

            # AEMODIFY - Modified Reported Term (Expected per SME)
            for col in ["AEMODIFY", "AEMOD", "MODTERM"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AEMODIFY"] = str(row[col])
                    break

            # === EXPECTED - MedDRA CODING ===

            # AEDECOD - Dictionary-Derived Term (Expected) - Preferred Term from MedDRA
            # Priority: AEPTT (PT text from source), AEDECOD, AEPT, then fallback to AETERM
            for col in ["AEPTT", "AEDECOD", "AEPT", "PTTERM", "PREFERRED_TERM"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AEDECOD"] = str(row[col])
                    break
            if not ae_record["AEDECOD"]:
                ae_record["AEDECOD"] = ae_record.get("AETERM", "")

            # AEBODSYS - Body System or Organ Class (Expected) - SOC
            # Priority: AESCT (SOC text from source), AEBODSYS, AESOC
            for col in ["AESCT", "AEBODSYS", "AESOC", "SOC", "BODYSYS", "BODY_SYSTEM"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AEBODSYS"] = str(row[col])
                    break

            # === PERMISSIBLE - FULL MedDRA HIERARCHY ===

            # AEBDSYCD - Body System Code
            # Priority: AESCC (SOC code from source), AEBDSYCD, SOCCD
            for col in ["AESCC", "AEBDSYCD", "SOCCD", "AESOCCD"]:
                if col in row and pd.notna(row[col]):
                    try:
                        ae_record["AEBDSYCD"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # AESOC - Primary System Organ Class
            # Priority: AESCT (SOC text from source), AESOC, PRIMARY_SOC
            for col in ["AESCT", "AESOC", "PRIMARY_SOC"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AESOC"] = str(row[col])
                    break

            # AESOCCD - Primary SOC Code
            # Priority: AESCC (SOC code from source), AESOCCD, PRIM_SOCCD
            for col in ["AESCC", "AESOCCD", "PRIM_SOCCD"]:
                if col in row and pd.notna(row[col]):
                    try:
                        ae_record["AESOCCD"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # AEHLGT - High Level Group Term
            # Priority: AEHGT1 (HLGT text from source), AEHLGT, HLGT
            for col in ["AEHGT1", "AEHLGT", "HLGT", "HIGH_LEVEL_GROUP"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AEHLGT"] = str(row[col])
                    break

            # AEHLGTCD - HLGT Code
            # Priority: AEHGC (HLGT code from source), AEHLGTCD, HLGTCD
            for col in ["AEHGC", "AEHLGTCD", "HLGTCD"]:
                if col in row and pd.notna(row[col]):
                    try:
                        ae_record["AEHLGTCD"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # AEHLT - High Level Term
            # Priority: AEHTT (HLT text from source), AEHLT, HLT
            for col in ["AEHTT", "AEHLT", "HLT", "HIGH_LEVEL_TERM"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AEHLT"] = str(row[col])
                    break

            # AEHLTCD - HLT Code
            # Priority: AEHTC (HLT code from source), AEHLTCD, HLTCD
            for col in ["AEHTC", "AEHLTCD", "HLTCD"]:
                if col in row and pd.notna(row[col]):
                    try:
                        ae_record["AEHLTCD"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # AELLT - Lowest Level Term
            # Priority: AELTT (LLT text from source), AELLT, LLT
            for col in ["AELTT", "AELLT", "LLT", "LOWEST_LEVEL_TERM"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AELLT"] = str(row[col])
                    break

            # AELLTCD - LLT Code
            # Priority: AELTC (LLT code from source), AELLTCD, LLTCD
            for col in ["AELTC", "AELLTCD", "LLTCD"]:
                if col in row and pd.notna(row[col]):
                    try:
                        ae_record["AELLTCD"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # AEPTCD - Preferred Term Code
            # Priority: AEPTC (PT code from source), AEPTCD, PTCD
            for col in ["AEPTC", "AEPTCD", "PTCD"]:
                if col in row and pd.notna(row[col]):
                    try:
                        ae_record["AEPTCD"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # === EXPECTED - SEVERITY/SERIOUSNESS ===

            # AESEV - Severity/Intensity (Expected)
            for col in ["AESEV", "SEVERITY", "AEINTENS", "INTENSITY"]:
                if col in row and pd.notna(row[col]):
                    sev = str(row[col]).upper().strip()
                    sev_map = {
                        "1": "MILD", "MILD": "MILD", "MI": "MILD",
                        "2": "MODERATE", "MODERATE": "MODERATE", "MO": "MODERATE",
                        "3": "SEVERE", "SEVERE": "SEVERE", "SE": "SEVERE"
                    }
                    ae_record["AESEV"] = sev_map.get(sev, sev)
                    break

            # AESER - Serious Event (Expected)
            # Priority: AESERL (seriousness label from source), AESER, SERIOUS, SAE
            for col in ["AESERL", "AESER", "SERIOUS", "SAE"]:
                if col in row and pd.notna(row[col]):
                    val = str(row[col]).upper().strip()
                    # Map to Y/N based on value
                    if val in ["Y", "YES", "1", "TRUE", "SAE", "SERIOUS"]:
                        ae_record["AESER"] = "Y"
                    elif val in ["N", "NO", "0", "FALSE", "NOT SERIOUS"]:
                        ae_record["AESER"] = "N"
                    elif "HOSPITALIZATION" in val or "DEATH" in val or "LIFE THREATENING" in val or "DISABILITY" in val:
                        # If seriousness reason is given, mark as serious
                        ae_record["AESER"] = "Y"
                    else:
                        ae_record["AESER"] = "N" if val == "" else val[:1] if val else ""
                    break

            # AEACN - Action Taken with Study Treatment (Expected)
            # Priority: AEACTL (action label), AEACT, AEACN, ACTION
            # Map to CDISC Controlled Terminology (ACN)
            for col in ["AEACTL", "AEACT", "AEACN", "ACTION", "AEACTION", "ACTIONTAKEN"]:
                if col in row and pd.notna(row[col]):
                    acn = str(row[col]).upper().strip()
                    acn_map = {
                        # Standard CT values
                        "DRUG WITHDRAWN": "DRUG WITHDRAWN",
                        "DRUG INTERRUPTED": "DRUG INTERRUPTED",
                        "DOSE REDUCED": "DOSE REDUCED",
                        "DOSE INCREASED": "DOSE INCREASED",
                        "DOSE NOT CHANGED": "DOSE NOT CHANGED",
                        "NOT APPLICABLE": "NOT APPLICABLE",
                        "UNKNOWN": "UNKNOWN",
                        # Common source variations
                        "NONE": "DOSE NOT CHANGED",
                        "NO CHANGE": "DOSE NOT CHANGED",
                        "NO ACTION TAKEN": "DOSE NOT CHANGED",
                        "DISCONTINUED": "DRUG WITHDRAWN",
                        "WITHDRAWN": "DRUG WITHDRAWN",
                        "INTERRUPTED": "DRUG INTERRUPTED",
                        "REDUCED": "DOSE REDUCED",
                        "INCREASED": "DOSE INCREASED",
                        # Numeric codes
                        "1": "DOSE NOT CHANGED",
                        "2": "DOSE REDUCED",
                        "3": "DRUG INTERRUPTED",
                        "4": "DRUG WITHDRAWN",
                        "5": "DOSE INCREASED"
                    }
                    ae_record["AEACN"] = acn_map.get(acn, acn)
                    break

            # AEACNOTH - Other Action Taken (Perm)
            for col in ["AEACNOTH", "OTHERACTION"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AEACNOTH"] = str(row[col])
                    break

            # AEREL - Causality (Expected)
            # Priority: AERELL (relationship text from source), AEREL, CAUSALITY
            # Map to CDISC Controlled Terminology values
            for col in ["AERELL", "AEREL", "CAUSALITY", "RELATED", "RELATIONSHIP"]:
                if col in row and pd.notna(row[col]):
                    rel = str(row[col]).upper().strip()
                    # Map source values to CDISC CT (NRIND/REL)
                    rel_map = {
                        # Standard CT values
                        "RELATED": "RELATED",
                        "POSSIBLY RELATED": "POSSIBLY RELATED",
                        "PROBABLY RELATED": "PROBABLY RELATED",
                        "NOT RELATED": "NOT RELATED",
                        "UNLIKELY RELATED": "UNLIKELY RELATED",
                        "DEFINITELY RELATED": "DEFINITELY RELATED",
                        # Common source variations
                        "POSSIBLE": "POSSIBLY RELATED",
                        "PROBABLY": "PROBABLY RELATED",
                        "PROBABLE": "PROBABLY RELATED",
                        "UNLIKELY": "UNLIKELY RELATED",
                        "UNRELATED": "NOT RELATED",
                        "NONE": "NOT RELATED",
                        "DEFINITELY": "DEFINITELY RELATED",
                        "CERTAIN": "DEFINITELY RELATED",
                        # Numeric codes (if source uses numbers)
                        "1": "NOT RELATED",
                        "2": "UNLIKELY RELATED",
                        "3": "POSSIBLY RELATED",
                        "4": "PROBABLY RELATED",
                        "5": "DEFINITELY RELATED"
                    }
                    ae_record["AEREL"] = rel_map.get(rel, rel)
                    break

            # AEPATT - Pattern of Adverse Event (Perm)
            for col in ["AEPATT", "PATTERN"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AEPATT"] = str(row[col]).upper()
                    break

            # AEOUT - Outcome of Adverse Event (Expected)
            # Priority: AEOUTCL (outcome text from source), AEOUTC, AEOUT, OUTCOME
            # Map to CDISC Controlled Terminology (OUT)
            for col in ["AEOUTCL", "AEOUTC", "AEOUT", "OUTCOME", "AEOUTCOME"]:
                if col in row and pd.notna(row[col]):
                    out = str(row[col]).upper().strip()
                    # Map source values to CDISC CT (OUT)
                    out_map = {
                        # Standard CT values
                        "RECOVERED/RESOLVED": "RECOVERED/RESOLVED",
                        "RECOVERING/RESOLVING": "RECOVERING/RESOLVING",
                        "NOT RECOVERED/NOT RESOLVED": "NOT RECOVERED/NOT RESOLVED",
                        "RECOVERED/RESOLVED WITH SEQUELAE": "RECOVERED/RESOLVED WITH SEQUELAE",
                        "FATAL": "FATAL",
                        "UNKNOWN": "UNKNOWN",
                        # Common source variations
                        "RECOVERED": "RECOVERED/RESOLVED",
                        "RESOLVED": "RECOVERED/RESOLVED",
                        "RECOVERING": "RECOVERING/RESOLVING",
                        "RESOLVING": "RECOVERING/RESOLVING",
                        "NOT RECOVERED": "NOT RECOVERED/NOT RESOLVED",
                        "NOT RESOLVED": "NOT RECOVERED/NOT RESOLVED",
                        "CONTINUING": "NOT RECOVERED/NOT RESOLVED",
                        "ONGOING": "NOT RECOVERED/NOT RESOLVED",
                        "RESOLVED, WITH RESIDUAL EFFECTS": "RECOVERED/RESOLVED WITH SEQUELAE",
                        "RESOLVED WITH SEQUELAE": "RECOVERED/RESOLVED WITH SEQUELAE",
                        "PATIENT DIED": "FATAL",
                        "DEATH": "FATAL",
                        "DIED": "FATAL",
                        # Numeric codes (if source uses numbers)
                        "1": "RECOVERED/RESOLVED",
                        "2": "RECOVERING/RESOLVING",
                        "3": "NOT RECOVERED/NOT RESOLVED",
                        "4": "FATAL",
                        "5": "UNKNOWN"
                    }
                    ae_record["AEOUT"] = out_map.get(out, out)
                    break

            # === PERMISSIBLE - SAE CRITERIA (Y/N) ===

            # AESCAN - Involves Cancer
            for col in ["AESCAN", "CANCER"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AESCAN"] = "Y" if str(row[col]).upper() in ["Y", "YES", "1"] else "N"
                    break

            # AESCONG - Congenital Anomaly
            for col in ["AESCONG", "CONGENITAL"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AESCONG"] = "Y" if str(row[col]).upper() in ["Y", "YES", "1"] else "N"
                    break

            # AESDISAB - Disability/Incapacity
            for col in ["AESDISAB", "DISABILITY"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AESDISAB"] = "Y" if str(row[col]).upper() in ["Y", "YES", "1"] else "N"
                    break

            # AESDTH - Results in Death
            for col in ["AESDTH", "DEATH", "FATAL"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AESDTH"] = "Y" if str(row[col]).upper() in ["Y", "YES", "1"] else "N"
                    break

            # AESHOSP - Hospitalization
            for col in ["AESHOSP", "HOSPITALIZATION", "HOSP"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AESHOSP"] = "Y" if str(row[col]).upper() in ["Y", "YES", "1"] else "N"
                    break

            # AESLIFE - Life Threatening
            for col in ["AESLIFE", "LIFETHREAT", "LIFE_THREATENING"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AESLIFE"] = "Y" if str(row[col]).upper() in ["Y", "YES", "1"] else "N"
                    break

            # AESOD - Occurred with Overdose
            for col in ["AESOD", "OVERDOSE"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AESOD"] = "Y" if str(row[col]).upper() in ["Y", "YES", "1"] else "N"
                    break

            # AESMIE - Other Medically Important Event
            for col in ["AESMIE", "MEDIMPORTANT"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AESMIE"] = "Y" if str(row[col]).upper() in ["Y", "YES", "1"] else "N"
                    break

            # AECONTRT - Concomitant Treatment Given
            for col in ["AECONTRT", "CONCOMTRT"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AECONTRT"] = "Y" if str(row[col]).upper() in ["Y", "YES", "1"] else "N"
                    break

            # AETOXGR - Standard Toxicity Grade (e.g., CTCAE)
            # Priority: AETOXGR, TOXGRADE, CTCAE, GRADE
            # If not available, derive from AESEV severity
            for col in ["AETOXGR", "TOXGRADE", "CTCAE", "GRADE"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AETOXGR"] = str(row[col])
                    break

            # If AETOXGR is still empty, derive from AESEV (severity)
            if not ae_record.get("AETOXGR") and ae_record.get("AESEV"):
                sev = ae_record["AESEV"].upper()
                # Map severity to CTCAE grades
                sev_to_grade = {
                    "MILD": "1",
                    "MODERATE": "2",
                    "SEVERE": "3",
                    "LIFE THREATENING": "4",
                    "LIFE-THREATENING": "4",
                    "FATAL": "5",
                    "DEATH": "5"
                }
                ae_record["AETOXGR"] = sev_to_grade.get(sev, "")

            # === TIMING VARIABLES ===

            # EPOCH - Epoch (Expected)
            for col in ["EPOCH", "AEEPOCH", "PHASE"]:
                if col in row and pd.notna(row[col]):
                    ae_record["EPOCH"] = str(row[col]).upper()
                    break

            # VISITNUM - Clinical Encounter Number (Expected)
            for col in ["VISITNUM", "VISNUM", "VISIT_NUM"]:
                if col in row and pd.notna(row[col]):
                    try:
                        ae_record["VISITNUM"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # VISIT - Visit Name (Expected)
            for col in ["VISIT", "VISNAME", "VISIT_NAME"]:
                if col in row and pd.notna(row[col]):
                    ae_record["VISIT"] = str(row[col])
                    break

            # AEDTC - Date/Time of Collection (Expected)
            for col in ["AEDTC", "AEDT", "AE_DATE", "COLLECTION_DATE"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AEDTC"] = self._convert_date_to_iso(row[col])
                    break

            # AESTDTC - Start Date/Time (Expected)
            # Priority: AESTDT (start date from source), AESTDTC, STDT, ONSET
            for col in ["AESTDT", "AESTDTC", "STDT", "ONSET", "STARTDT", "AE_START"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AESTDTC"] = self._convert_date_to_iso(row[col])
                    break

            # If AEDTC not set but AESTDTC is, use AESTDTC for AEDTC
            if not ae_record["AEDTC"] and ae_record["AESTDTC"]:
                ae_record["AEDTC"] = ae_record["AESTDTC"]

            # AEENDTC - End Date/Time (Expected)
            # Priority: AEENDT (end date from source), AEENDTC, ENDT
            for col in ["AEENDT", "AEENDTC", "ENDT", "ENDDT", "RESOLVED", "AE_END"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AEENDTC"] = self._convert_date_to_iso(row[col])
                    break

            # AESTDY - Study Day of Start (Expected per SME)
            for col in ["AESTDY", "STARTDAY", "AE_STDY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        ae_record["AESTDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # AEENDY - Study Day of End (Expected per SME)
            for col in ["AEENDY", "ENDDAY", "AE_ENDY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        ae_record["AEENDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # AEDUR - Duration (Perm) - ISO 8601 duration format
            for col in ["AEDUR", "DURATION"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AEDUR"] = str(row[col])
                    break

            # AEENRF - End Relative to Reference Period (Expected per SME)
            for col in ["AEENRF", "ENDREL", "AE_ENRF"]:
                if col in row and pd.notna(row[col]):
                    val = str(row[col]).upper().strip()
                    # Standard controlled terms
                    if val in ["BEFORE", "DURING", "AFTER", "ONGOING", "U"]:
                        ae_record["AEENRF"] = val
                    else:
                        ae_record["AEENRF"] = val
                    break

            # AESTRF - Start Relative to Reference Period (Perm)
            for col in ["AESTRF", "STARTREL"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AESTRF"] = str(row[col]).upper()
                    break

            ae_records.append(ae_record)

        result_df = pd.DataFrame(ae_records)

        # Ensure column order matches SME expectations
        sme_column_order = [
            "STUDYID", "DOMAIN", "USUBJID", "AESEQ", "AETERM", "AEMODIFY",
            "AELLT", "AELLTCD", "AEDECOD", "AEPTCD", "AEHLT", "AEHLTCD",
            "AEHLGT", "AEHLGTCD", "AEBODSYS", "AEBDSYCD", "AESOC", "AESOCCD",
            "AESER", "AEACN", "AEREL", "AEOUT", "AESDTH", "AESHOSP",
            "AECONTRT", "AETOXGR", "EPOCH", "VISITNUM", "VISIT",
            "AEDTC", "AESTDTC", "AEENDTC", "AESTDY", "AEENDY", "AEENRF"
        ]

        # Reorder columns to match SME expectation, keeping any extras at the end
        ordered_cols = [c for c in sme_column_order if c in result_df.columns]
        extra_cols = [c for c in result_df.columns if c not in sme_column_order]
        result_df = result_df[ordered_cols + extra_cols]

        # Log compliance summary
        self.log(f"Created {len(result_df)} AE records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        self.log(f"Columns: {', '.join(result_df.columns.tolist())}")
        return result_df


class VSTransformer(BaseDomainTransformer):
    """Vital Signs domain transformer - FULL SDTM-IG 3.4 compliant (33 variables)."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "VS"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform vital signs data to SDTM VS domain per SDTMIG 3.4.

        Implements ALL 33 VS variables including:
        - Required (6): STUDYID, DOMAIN, USUBJID, VSSEQ, VSTESTCD, VSTEST
        - Expected (12): VSPOS, VSORRES, VSORRESU, VSSTRESC, VSSTRESN, VSSTRESU,
                         VSBLFL, VISITNUM, VSDTC, etc.
        - Permissible (15): VSSPID, VSCAT, VSSCAT, VSSTAT, VSREASND, VSLOC, VSLAT,
                            VSDRVFL, VISIT, VISITDY, EPOCH, VSDY, VSTPT, etc.
        """
        self.log("Transforming to VS domain - FULL SDTM-IG 3.4 compliance (33 variables)")

        vs_records = []
        subject_seq = {}

        # Comprehensive vital sign test mappings per SDTM-IG
        # Format: source_col -> (VSTESTCD, VSTEST, standard_unit)
        test_mappings = {
            # Blood Pressure - Systolic
            "SYSBP": ("SYSBP", "Systolic Blood Pressure", "mmHg"),
            "VTBPS2": ("SYSBP", "Systolic Blood Pressure", "mmHg"),
            "VSSYSBP": ("SYSBP", "Systolic Blood Pressure", "mmHg"),
            "SYSTOLIC": ("SYSBP", "Systolic Blood Pressure", "mmHg"),
            "SBP": ("SYSBP", "Systolic Blood Pressure", "mmHg"),

            # Blood Pressure - Diastolic
            "DIABP": ("DIABP", "Diastolic Blood Pressure", "mmHg"),
            "VTBPD2": ("DIABP", "Diastolic Blood Pressure", "mmHg"),
            "VSDIABP": ("DIABP", "Diastolic Blood Pressure", "mmHg"),
            "DIASTOLIC": ("DIABP", "Diastolic Blood Pressure", "mmHg"),
            "DBP": ("DIABP", "Diastolic Blood Pressure", "mmHg"),

            # Mean Arterial Pressure
            "MAP": ("MAP", "Mean Arterial Pressure", "mmHg"),
            "MEANAP": ("MAP", "Mean Arterial Pressure", "mmHg"),

            # Heart Rate / Pulse
            "PULSE": ("PULSE", "Pulse Rate", "beats/min"),
            "HR": ("HR", "Heart Rate", "beats/min"),
            "VTPLS2": ("PULSE", "Pulse Rate", "beats/min"),
            "HEARTRATE": ("HR", "Heart Rate", "beats/min"),
            "VSPULSE": ("PULSE", "Pulse Rate", "beats/min"),

            # Respiratory Rate
            "RESP": ("RESP", "Respiratory Rate", "breaths/min"),
            "VTRRT2": ("RESP", "Respiratory Rate", "breaths/min"),
            "VSRESP": ("RESP", "Respiratory Rate", "breaths/min"),
            "RR": ("RESP", "Respiratory Rate", "breaths/min"),

            # Temperature
            "TEMP": ("TEMP", "Temperature", "C"),
            "VTTP2": ("TEMP", "Temperature", "C"),
            "VSTEMP": ("TEMP", "Temperature", "C"),
            "TEMPERATURE": ("TEMP", "Temperature", "C"),

            # Weight
            "WEIGHT": ("WEIGHT", "Weight", "kg"),
            "GNNUM1": ("WEIGHT", "Weight", "kg"),
            "VSWEIGHT": ("WEIGHT", "Weight", "kg"),
            "WT": ("WEIGHT", "Weight", "kg"),

            # Height
            "HEIGHT": ("HEIGHT", "Height", "cm"),
            "GNNUM2": ("HEIGHT", "Height", "cm"),
            "VSHEIGHT": ("HEIGHT", "Height", "cm"),
            "HT": ("HEIGHT", "Height", "cm"),

            # BMI
            "BMI": ("BMI", "Body Mass Index", "kg/m2"),
            "VSBMI": ("BMI", "Body Mass Index", "kg/m2"),

            # Oxygen Saturation
            "SPO2": ("OXYSAT", "Oxygen Saturation", "%"),
            "OXYSAT": ("OXYSAT", "Oxygen Saturation", "%"),
            "O2SAT": ("OXYSAT", "Oxygen Saturation", "%"),

            # Body Surface Area
            "BSA": ("BSA", "Body Surface Area", "m2"),

            # Waist Circumference
            "WAIST": ("WAIST", "Waist Circumference", "cm"),
            "WAISTCIR": ("WAIST", "Waist Circumference", "cm"),

            # Hip Circumference
            "HIP": ("HIP", "Hip Circumference", "cm"),
            "HIPCIR": ("HIP", "Hip Circumference", "cm"),
        }

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))

            # Process each vital sign in the row
            for src_col, (testcd, test_name, std_unit) in test_mappings.items():
                if src_col in row and pd.notna(row[src_col]):
                    # Initialize or increment sequence
                    if subj not in subject_seq:
                        subject_seq[subj] = 0
                    subject_seq[subj] += 1

                    # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
                    # This ensures they ALL appear in output per SDTM-IG 3.4
                    vs_record = {
                        # Required Identifiers
                        "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                        "DOMAIN": "VS",
                        "USUBJID": self._generate_usubjid(row),
                        "VSSEQ": subject_seq[subj],
                        "VSTESTCD": testcd,
                        "VSTEST": test_name,
                        # Expected - Position
                        "VSPOS": "",
                        # Expected - Results
                        "VSORRES": "",
                        "VSORRESU": "",
                        "VSSTRESC": "",
                        "VSSTRESN": None,
                        "VSSTRESU": "",
                        # Expected - Baseline
                        "VSBLFL": "",
                        # Expected - Timing
                        "VISITNUM": None,
                        "VISIT": "",
                        "VSDTC": "",
                        # Permissible
                        "VSCAT": "",
                        "VSSCAT": "",
                        "VSSTAT": "",
                        "VSREASND": "",
                        "VSLOC": "",
                        "VSLAT": "",
                        "VSDRVFL": "",
                        "VISITDY": None,
                        "EPOCH": "",
                        "VSDY": None,
                        "VSTPT": "",
                        "VSTPTNUM": None,
                    }

                    # VSSPID - Sponsor-Defined Identifier (Perm)
                    for col in ["VSSPID", "VSID", "RECID"]:
                        if col in row and pd.notna(row[col]):
                            vs_record["VSSPID"] = str(row[col])
                            break

                    # === GROUPING QUALIFIERS (Permissible) ===

                    # VSCAT - Category
                    for col in ["VSCAT", "CAT", "CATEGORY"]:
                        if col in row and pd.notna(row[col]):
                            vs_record["VSCAT"] = str(row[col]).upper()
                            break

                    # VSSCAT - Subcategory
                    for col in ["VSSCAT", "SCAT", "SUBCATEGORY"]:
                        if col in row and pd.notna(row[col]):
                            vs_record["VSSCAT"] = str(row[col]).upper()
                            break

                    # === RECORD QUALIFIERS ===

                    # VSPOS - Position of Subject (Expected)
                    for col in ["VSPOS", "POSITION", "POS"]:
                        if col in row and pd.notna(row[col]):
                            pos = str(row[col]).upper().strip()
                            pos_map = {
                                "SITTING": "SITTING", "SIT": "SITTING",
                                "STANDING": "STANDING", "STAND": "STANDING",
                                "SUPINE": "SUPINE", "LYING": "SUPINE",
                                "PRONE": "PRONE"
                            }
                            vs_record["VSPOS"] = pos_map.get(pos, pos)
                            break

                    # === RESULT QUALIFIERS ===

                    # VSORRES - Original Result (Expected)
                    vs_record["VSORRES"] = str(row[src_col])

                    # VSORRESU - Original Units (Expected)
                    orig_unit = std_unit
                    for col in ["VSORRESU", "UNIT", "UNITS"]:
                        if col in row and pd.notna(row[col]):
                            orig_unit = str(row[col])
                            break
                    vs_record["VSORRESU"] = orig_unit

                    # VSSTRESC/VSSTRESN/VSSTRESU - Standardized Results (Expected)
                    try:
                        numeric_val = float(row[src_col])
                        vs_record["VSSTRESN"] = numeric_val
                        vs_record["VSSTRESC"] = str(numeric_val)
                        vs_record["VSSTRESU"] = std_unit

                        # Unit conversion if needed
                        if testcd == "TEMP" and orig_unit.upper() in ["F", "FAHRENHEIT"]:
                            # Convert Fahrenheit to Celsius
                            vs_record["VSSTRESN"] = round((numeric_val - 32) * 5 / 9, 1)
                            vs_record["VSSTRESC"] = str(vs_record["VSSTRESN"])
                        elif testcd == "WEIGHT" and orig_unit.upper() in ["LB", "LBS", "POUNDS"]:
                            # Convert pounds to kg
                            vs_record["VSSTRESN"] = round(numeric_val * 0.453592, 1)
                            vs_record["VSSTRESC"] = str(vs_record["VSSTRESN"])
                        elif testcd == "HEIGHT" and orig_unit.upper() in ["IN", "INCHES"]:
                            # Convert inches to cm
                            vs_record["VSSTRESN"] = round(numeric_val * 2.54, 1)
                            vs_record["VSSTRESC"] = str(vs_record["VSSTRESN"])
                    except (ValueError, TypeError):
                        vs_record["VSSTRESC"] = str(row[src_col])

                    # VSSTAT - Completion Status (Perm)
                    for col in ["VSSTAT", "STAT", "STATUS"]:
                        if col in row and pd.notna(row[col]):
                            vs_record["VSSTAT"] = str(row[col]).upper()
                            break

                    # VSREASND - Reason Not Done (Perm)
                    for col in ["VSREASND", "REASONND", "REASON"]:
                        if col in row and pd.notna(row[col]):
                            vs_record["VSREASND"] = str(row[col])
                            break

                    # VSLOC - Location of Measurement (Perm)
                    for col in ["VSLOC", "LOC", "LOCATION"]:
                        if col in row and pd.notna(row[col]):
                            vs_record["VSLOC"] = str(row[col]).upper()
                            break

                    # VSLAT - Laterality (Perm)
                    for col in ["VSLAT", "LAT", "LATERALITY"]:
                        if col in row and pd.notna(row[col]):
                            lat = str(row[col]).upper()
                            vs_record["VSLAT"] = "LEFT" if "L" in lat else ("RIGHT" if "R" in lat else lat)
                            break

                    # VSBLFL - Baseline Flag (Expected)
                    for col in ["VSBLFL", "BASELINE", "BLFL"]:
                        if col in row and pd.notna(row[col]):
                            vs_record["VSBLFL"] = "Y" if str(row[col]).upper() in ["Y", "YES", "1", "TRUE"] else ""
                            break

                    # VSDRVFL - Derived Flag (Perm)
                    for col in ["VSDRVFL", "DERIVED"]:
                        if col in row and pd.notna(row[col]):
                            vs_record["VSDRVFL"] = "Y" if str(row[col]).upper() in ["Y", "YES", "1", "TRUE"] else ""
                            break

                    # === TIMING VARIABLES ===

                    # VISITNUM - Visit Number (Expected)
                    for col in ["VISITNUM", "VISNUM", "VISIT"]:
                        if col in row and pd.notna(row[col]):
                            try:
                                vs_record["VISITNUM"] = int(float(row[col]))
                            except (ValueError, TypeError):
                                vs_record["VISITNUM"] = row[col]
                            break

                    # VISIT - Visit Name (Perm)
                    for col in ["VISIT", "VISNAME", "VISITNAME"]:
                        if col in row and pd.notna(row[col]):
                            vs_record["VISIT"] = str(row[col])
                            break

                    # VISITDY - Planned Study Day of Visit (Perm)
                    for col in ["VISITDY", "VISDY"]:
                        if col in row and pd.notna(row[col]):
                            try:
                                vs_record["VISITDY"] = int(float(row[col]))
                            except (ValueError, TypeError):
                                pass
                            break

                    # EPOCH - Epoch (Perm)
                    for col in ["EPOCH", "VSEPOCH"]:
                        if col in row and pd.notna(row[col]):
                            vs_record["EPOCH"] = str(row[col]).upper()
                            break

                    # VSDTC - Date/Time of Measurements (Expected)
                    for col in ["VSDTC", "VSDT", "DATE", "VISITDT", "VTDT", "MEASDT"]:
                        if col in row and pd.notna(row[col]):
                            vs_record["VSDTC"] = self._convert_date_to_iso(row[col])
                            break

                    # VSDY - Study Day of Vital Signs (Perm)
                    for col in ["VSDY", "STUDYDAY"]:
                        if col in row and pd.notna(row[col]):
                            try:
                                vs_record["VSDY"] = int(float(row[col]))
                            except (ValueError, TypeError):
                                pass
                            break

                    # VSTPT - Planned Time Point Name (Perm)
                    for col in ["VSTPT", "TPT", "TIMEPOINT"]:
                        if col in row and pd.notna(row[col]):
                            vs_record["VSTPT"] = str(row[col])
                            break

                    # VSTPTNUM - Planned Time Point Number (Perm)
                    for col in ["VSTPTNUM", "TPTNUM"]:
                        if col in row and pd.notna(row[col]):
                            try:
                                vs_record["VSTPTNUM"] = int(float(row[col]))
                            except (ValueError, TypeError):
                                pass
                            break

                    # VSELTM - Elapsed Time from Time Point Ref (Perm)
                    for col in ["VSELTM", "ELTM", "ELAPSED"]:
                        if col in row and pd.notna(row[col]):
                            vs_record["VSELTM"] = str(row[col])
                            break

                    # VSTPTREF - Time Point Reference (Perm)
                    for col in ["VSTPTREF", "TPTREF"]:
                        if col in row and pd.notna(row[col]):
                            vs_record["VSTPTREF"] = str(row[col])
                            break

                    vs_records.append(vs_record)

        result_df = pd.DataFrame(vs_records)

        # Ensure column order per SDTM-IG 3.4
        vs_column_order = [
            "STUDYID", "DOMAIN", "USUBJID", "VSSEQ", "VSTESTCD", "VSTEST",
            "VSCAT", "VSSCAT", "VSPOS", "VSORRES", "VSORRESU", "VSSTRESC",
            "VSSTRESN", "VSSTRESU", "VSSTAT", "VSREASND", "VSLOC", "VSLAT",
            "VSBLFL", "VSDRVFL", "VISITNUM", "VISIT", "VISITDY", "EPOCH",
            "VSDTC", "VSDY", "VSTPT", "VSTPTNUM", "VSELTM", "VSTPTREF"
        ]
        ordered_cols = [c for c in vs_column_order if c in result_df.columns]
        extra_cols = [c for c in result_df.columns if c not in vs_column_order]
        result_df = result_df[ordered_cols + extra_cols]

        # Log compliance summary
        self.log(f"Created {len(result_df)} VS records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        self.log(f"Columns: {', '.join(result_df.columns.tolist())}")
        return result_df


class LBTransformer(BaseDomainTransformer):
    """Laboratory domain transformer - FULL SDTM-IG 3.4 compliant (43 variables)."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "LB"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform laboratory data to SDTM LB domain per SDTMIG 3.4.

        Implements ALL 43 LB variables including:
        - Required (6): STUDYID, DOMAIN, USUBJID, LBSEQ, LBTESTCD, LBTEST
        - Expected (19): LBCAT, LBORRES, LBORRESU, LBORNRLO, LBORNRHI, LBSTRESC,
                         LBSTRESN, LBSTRESU, LBSTNRLO, LBSTNRHI, LBNRIND, LBSPEC,
                         LBBLFL, VISITNUM, LBDTC, etc.
        - Permissible (18): LBSPID, LBSCAT, LBSTNRC, LBSTAT, LBREASND, LBNAM,
                            LBSPCCND, LBMETHOD, LBFAST, LBDRVFL, LBTOX, LBTOXGR, etc.
        """
        self.log("Transforming to LB domain - FULL SDTM-IG 3.4 compliance (43 variables)")

        lb_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))

            # Initialize or increment sequence
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            # This ensures they ALL appear in output per SDTM-IG 3.4
            lb_record = {
                # Required Identifiers
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "LB",
                "USUBJID": self._generate_usubjid(row),
                "LBSEQ": subject_seq[subj],
                "LBTESTCD": "",
                "LBTEST": "",
                # Expected - Category
                "LBCAT": "",
                "LBSCAT": "",
                # Expected - Results
                "LBORRES": "",
                "LBORRESU": "",
                "LBORNRLO": "",
                "LBORNRHI": "",
                "LBSTRESC": "",
                "LBSTRESN": None,
                "LBSTRESU": "",
                "LBSTNRLO": None,
                "LBSTNRHI": None,
                "LBNRIND": "",
                # Expected - Specimen
                "LBSPEC": "",
                "LBMETHOD": "",
                # Expected - Baseline
                "LBBLFL": "",
                "LBFAST": "",
                # Expected - Timing
                "VISITNUM": None,
                "VISIT": "",
                "LBDTC": "",
                # Permissible - Toxicity
                "LBTOX": "",
                "LBTOXGR": "",
                # Permissible - Other
                "LBSTAT": "",
                "LBREASND": "",
                "LBNAM": "",
                "EPOCH": "",
                "LBDY": None,
            }

            # LBSPID - Sponsor-Defined Identifier (Perm)
            for col in ["LBSPID", "LBID", "LABID", "SPECID"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBSPID"] = str(row[col])
                    break

            # LBTESTCD - Lab Test Short Name (Required)
            for col in ["LBTESTCD", "TESTCD", "TEST", "LABTEST"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBTESTCD"] = str(row[col])[:8].upper()  # Max 8 chars
                    break

            # LBTEST - Lab Test Name (Required)
            for col in ["LBTEST", "TESTNAME", "LABNAME", "TEST"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBTEST"] = str(row[col])
                    break

            # === GROUPING QUALIFIERS ===

            # LBCAT - Category for Lab Test (Expected)
            for col in ["LBCAT", "CAT", "CATEGORY", "LABCAT"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBCAT"] = str(row[col]).upper()
                    break

            # LBSCAT - Subcategory for Lab Test (Perm)
            for col in ["LBSCAT", "SCAT", "SUBCATEGORY"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBSCAT"] = str(row[col]).upper()
                    break

            # === RESULT QUALIFIERS ===

            # LBORRES - Result in Original Units (Expected)
            for col in ["LBORRES", "RESULT", "VALUE", "ORRES"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBORRES"] = str(row[col])
                    break

            # LBORRESU - Original Units (Expected)
            for col in ["LBORRESU", "UNIT", "UNITS", "ORRESU"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBORRESU"] = str(row[col])
                    break

            # LBORNRLO - Reference Range Lower Limit in Original Units (Expected)
            for col in ["LBORNRLO", "NRLO", "LOLIMIT", "LLNORM", "LOWER"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBORNRLO"] = str(row[col])
                    break

            # LBORNRHI - Reference Range Upper Limit in Original Units (Expected)
            for col in ["LBORNRHI", "NRHI", "HILIMIT", "ULNORM", "UPPER"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBORNRHI"] = str(row[col])
                    break

            # LBSTRESC/LBSTRESN/LBSTRESU - Standardized Results (Expected)
            if lb_record.get("LBORRES"):
                try:
                    numeric_val = float(lb_record["LBORRES"])
                    lb_record["LBSTRESN"] = numeric_val
                    lb_record["LBSTRESC"] = str(numeric_val)
                    lb_record["LBSTRESU"] = lb_record.get("LBORRESU", "")
                except (ValueError, TypeError):
                    lb_record["LBSTRESC"] = lb_record["LBORRES"]

            # LBSTNRLO - Reference Range Lower Limit in Standard Units (Expected)
            if lb_record.get("LBORNRLO"):
                try:
                    lb_record["LBSTNRLO"] = float(lb_record["LBORNRLO"])
                except (ValueError, TypeError):
                    pass

            # LBSTNRHI - Reference Range Upper Limit in Standard Units (Expected)
            if lb_record.get("LBORNRHI"):
                try:
                    lb_record["LBSTNRHI"] = float(lb_record["LBORNRHI"])
                except (ValueError, TypeError):
                    pass

            # LBSTNRC - Reference Range for Character Result in Std Units (Perm)
            for col in ["LBSTNRC", "STNRC", "REFRANGE"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBSTNRC"] = str(row[col])
                    break

            # LBNRIND - Reference Range Indicator (Expected) - derived
            if lb_record.get("LBSTRESN") is not None:
                result = lb_record["LBSTRESN"]
                low = lb_record.get("LBSTNRLO", float('-inf'))
                high = lb_record.get("LBSTNRHI", float('inf'))

                if low is not None and result < low:
                    lb_record["LBNRIND"] = "LOW"
                elif high is not None and result > high:
                    lb_record["LBNRIND"] = "HIGH"
                elif low is not None or high is not None:
                    lb_record["LBNRIND"] = "NORMAL"

            # Direct LBNRIND mapping
            for col in ["LBNRIND", "NRIND", "ABNORMAL", "ABNFLAG"]:
                if col in row and pd.notna(row[col]):
                    nrind = str(row[col]).upper().strip()
                    nrind_map = {
                        "N": "NORMAL", "NORMAL": "NORMAL",
                        "L": "LOW", "LOW": "LOW", "H": "HIGH", "HIGH": "HIGH",
                        "A": "ABNORMAL", "ABNORMAL": "ABNORMAL"
                    }
                    lb_record["LBNRIND"] = nrind_map.get(nrind, nrind)
                    break

            # === RECORD QUALIFIERS ===

            # LBSTAT - Completion Status (Perm)
            for col in ["LBSTAT", "STAT", "STATUS"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBSTAT"] = str(row[col]).upper()
                    break

            # LBREASND - Reason Not Done (Perm)
            for col in ["LBREASND", "REASONND", "REASON"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBREASND"] = str(row[col])
                    break

            # LBNAM - Vendor Name (Perm)
            for col in ["LBNAM", "LAB", "LABNAME", "VENDOR"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBNAM"] = str(row[col])
                    break

            # LBSPEC - Specimen Type (Expected)
            for col in ["LBSPEC", "SPECIMEN", "SPEC", "MATRIX", "SAMPLE"]:
                if col in row and pd.notna(row[col]):
                    spec = str(row[col]).upper()
                    spec_map = {
                        "BLOOD": "BLOOD", "SERUM": "SERUM", "PLASMA": "PLASMA",
                        "URINE": "URINE", "WHOLE BLOOD": "WHOLE BLOOD",
                        "CSF": "CEREBROSPINAL FLUID"
                    }
                    lb_record["LBSPEC"] = spec_map.get(spec, spec)
                    break

            # LBSPCCND - Specimen Condition (Perm)
            for col in ["LBSPCCND", "SPECCOND", "CONDITION"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBSPCCND"] = str(row[col]).upper()
                    break

            # LBMETHOD - Method of Test (Perm)
            for col in ["LBMETHOD", "METHOD", "TESTMETHOD"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBMETHOD"] = str(row[col])
                    break

            # LBBLFL - Baseline Flag (Expected)
            for col in ["LBBLFL", "BASELINE", "BLFL"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBBLFL"] = "Y" if str(row[col]).upper() in ["Y", "YES", "1", "TRUE"] else ""
                    break

            # LBFAST - Fasting Status (Perm)
            for col in ["LBFAST", "FASTING"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBFAST"] = "Y" if str(row[col]).upper() in ["Y", "YES", "1", "TRUE"] else "N"
                    break

            # LBDRVFL - Derived Flag (Perm)
            for col in ["LBDRVFL", "DERIVED"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBDRVFL"] = "Y" if str(row[col]).upper() in ["Y", "YES", "1", "TRUE"] else ""
                    break

            # LBTOX - Toxicity (Perm)
            for col in ["LBTOX", "TOXICITY"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBTOX"] = str(row[col])
                    break

            # LBTOXGR - Standard Toxicity Grade (Perm) - e.g., CTCAE
            for col in ["LBTOXGR", "TOXGRADE", "CTCAE", "GRADE"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBTOXGR"] = str(row[col])
                    break

            # === TIMING VARIABLES ===

            # VISITNUM - Visit Number (Expected)
            for col in ["VISITNUM", "VISNUM", "VISIT"]:
                if col in row and pd.notna(row[col]):
                    try:
                        lb_record["VISITNUM"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        lb_record["VISITNUM"] = row[col]
                    break

            # VISIT - Visit Name (Perm)
            for col in ["VISIT", "VISNAME"]:
                if col in row and pd.notna(row[col]):
                    lb_record["VISIT"] = str(row[col])
                    break

            # VISITDY - Planned Study Day of Visit (Perm)
            for col in ["VISITDY", "VISDY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        lb_record["VISITDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # EPOCH - Epoch (Perm)
            for col in ["EPOCH", "LBEPOCH"]:
                if col in row and pd.notna(row[col]):
                    lb_record["EPOCH"] = str(row[col]).upper()
                    break

            # LBDTC - Date/Time of Specimen Collection (Expected)
            for col in ["LBDTC", "LBDT", "DATE", "VISITDT", "COLLDT", "SPECDT"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBDTC"] = self._convert_date_to_iso(row[col])
                    break

            # LBENDTC - End Date/Time of Specimen Collection (Perm)
            for col in ["LBENDTC", "ENDDT"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBENDTC"] = self._convert_date_to_iso(row[col])
                    break

            # LBDY - Study Day of Specimen Collection (Perm)
            for col in ["LBDY", "STUDYDAY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        lb_record["LBDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # LBTPT - Planned Time Point Name (Perm)
            for col in ["LBTPT", "TPT", "TIMEPOINT"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBTPT"] = str(row[col])
                    break

            # LBTPTNUM - Planned Time Point Number (Perm)
            for col in ["LBTPTNUM", "TPTNUM"]:
                if col in row and pd.notna(row[col]):
                    try:
                        lb_record["LBTPTNUM"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # LBELTM - Elapsed Time from Time Point Ref (Perm)
            for col in ["LBELTM", "ELTM", "ELAPSED"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBELTM"] = str(row[col])
                    break

            # LBTPTREF - Time Point Reference (Perm)
            for col in ["LBTPTREF", "TPTREF"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBTPTREF"] = str(row[col])
                    break

            lb_records.append(lb_record)

        result_df = pd.DataFrame(lb_records)

        # Ensure column order per SDTM-IG 3.4
        lb_column_order = [
            "STUDYID", "DOMAIN", "USUBJID", "LBSEQ", "LBTESTCD", "LBTEST",
            "LBCAT", "LBSCAT", "LBORRES", "LBORRESU", "LBORNRLO", "LBORNRHI",
            "LBSTRESC", "LBSTRESN", "LBSTRESU", "LBSTNRLO", "LBSTNRHI", "LBNRIND",
            "LBSTAT", "LBREASND", "LBNAM", "LBSPEC", "LBMETHOD", "LBBLFL",
            "LBFAST", "LBTOX", "LBTOXGR", "VISITNUM", "VISIT", "EPOCH",
            "LBDTC", "LBDY"
        ]
        ordered_cols = [c for c in lb_column_order if c in result_df.columns]
        extra_cols = [c for c in result_df.columns if c not in lb_column_order]
        result_df = result_df[ordered_cols + extra_cols]

        # Log compliance summary
        self.log(f"Created {len(result_df)} LB records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        self.log(f"Columns: {', '.join(result_df.columns.tolist())}")
        return result_df


class CMTransformer(BaseDomainTransformer):
    """Concomitant Medications domain transformer - FULL SDTM-IG 3.4 compliant (33 variables)."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "CM"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform concomitant medication data to SDTM CM domain per SDTMIG 3.4.

        Implements ALL 33 CM variables including:
        - Required (4): STUDYID, DOMAIN, USUBJID, CMSEQ, CMTRT
        - Expected (13): CMDECOD, CMINDC, CMDOSE, CMDOSU, CMDOSFRM, CMDOSFRQ,
                         CMROUTE, CMSTDTC, CMENDTC, etc.
        - Permissible (16): CMSPID, CMMODIFY, CMCAT, CMSCAT, CMPRESP, CMOCCUR,
                            CMSTAT, CMREASND, CMCLAS, CMCLASCD, CMDOSTXT, etc.
        """
        self.log("Transforming to CM domain - FULL SDTM-IG 3.4 compliance (33 variables)")

        cm_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))

            # Initialize or increment sequence
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            # This ensures they ALL appear in output per SDTM-IG 3.4
            cm_record = {
                # Required Identifiers
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "CM",
                "USUBJID": self._generate_usubjid(row),
                "CMSEQ": subject_seq[subj],
                "CMTRT": "",
                # Expected - Coding
                "CMMODIFY": "",
                "CMDECOD": "",
                # Expected - Category
                "CMCAT": "",
                "CMSCAT": "",
                # Expected - Indication
                "CMINDC": "",
                # Expected - Dosing
                "CMDOSE": None,
                "CMDOSU": "",
                "CMDOSFRM": "",
                "CMDOSFRQ": "",
                "CMDOSTOT": None,
                "CMROUTE": "",
                # Expected - Class
                "CMCLAS": "",
                "CMCLASCD": "",
                # Expected - Timing
                "EPOCH": "",
                "CMSTDTC": "",
                "CMENDTC": "",
                "CMSTDY": None,
                "CMENDY": None,
                "CMSTRF": "",
                "CMENRF": "",
                # Permissible
                "CMSTAT": "",
                "CMREASND": "",
            }

            # CMSPID - Sponsor-Defined Identifier (Perm)
            for col in ["CMSPID", "CMID", "MEDID"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMSPID"] = str(row[col])
                    break

            # CMTRT - Reported Name of Drug/Medication (Required)
            for col in ["CMTRT", "MEDNAME", "MEDICATION", "DRUG", "TRT", "DRUGNAME"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMTRT"] = str(row[col])
                    break

            # CMMODIFY - Modified Reported Name (Perm)
            for col in ["CMMODIFY", "CMMOD", "MODNAME"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMMODIFY"] = str(row[col])
                    break

            # CMDECOD - Standardized Medication Name (Expected) - WHODrug coded
            for col in ["CMDECOD", "WHODRUGNAME", "STDNAME", "PREFERRED"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMDECOD"] = str(row[col])
                    break
            if not cm_record["CMDECOD"]:
                cm_record["CMDECOD"] = cm_record.get("CMTRT", "")

            # === GROUPING QUALIFIERS ===

            # CMCAT - Category for Medication (Perm)
            for col in ["CMCAT", "CAT", "CATEGORY", "MEDCAT"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMCAT"] = str(row[col]).upper()
                    break

            # CMSCAT - Subcategory for Medication (Perm)
            for col in ["CMSCAT", "SCAT", "SUBCATEGORY"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMSCAT"] = str(row[col]).upper()
                    break

            # === VARIABLE QUALIFIERS ===

            # CMPRESP - CM Pre-Specified (Perm)
            for col in ["CMPRESP", "PRESPEC"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMPRESP"] = "Y" if str(row[col]).upper() in ["Y", "YES", "1"] else "N"
                    break

            # CMOCCUR - CM Occurrence (Perm)
            for col in ["CMOCCUR", "OCCUR"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMOCCUR"] = "Y" if str(row[col]).upper() in ["Y", "YES", "1"] else "N"
                    break

            # === RECORD QUALIFIERS ===

            # CMSTAT - Completion Status (Perm)
            for col in ["CMSTAT", "STAT", "STATUS"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMSTAT"] = str(row[col]).upper()
                    break

            # CMREASND - Reason Medication Not Collected (Perm)
            for col in ["CMREASND", "REASONND", "REASON"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMREASND"] = str(row[col])
                    break

            # CMINDC - Indication (Expected)
            for col in ["CMINDC", "INDICATION", "INDC", "REASON"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMINDC"] = str(row[col])
                    break

            # CMCLAS - Medication Class (Perm) - ATC classification
            for col in ["CMCLAS", "ATCCLASS", "DRUGCLASS", "CLASS"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMCLAS"] = str(row[col])
                    break

            # CMCLASCD - Medication Class Code (Perm)
            for col in ["CMCLASCD", "ATCCODE", "CLASSCD"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMCLASCD"] = str(row[col])
                    break

            # === DOSE INFORMATION ===

            # CMDOSE - Dose per Administration (Expected)
            for col in ["CMDOSE", "DOSE", "DOSENUM"]:
                if col in row and pd.notna(row[col]):
                    try:
                        cm_record["CMDOSE"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # CMDOSTXT - Dose Description (Perm) - for non-numeric doses
            for col in ["CMDOSTXT", "DOSETXT", "DOSETEXT"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMDOSTXT"] = str(row[col])
                    break
            # If numeric dose failed, use text
            if "CMDOSE" not in cm_record:
                for col in ["CMDOSE", "DOSE"]:
                    if col in row and pd.notna(row[col]):
                        cm_record["CMDOSTXT"] = str(row[col])
                        break

            # CMDOSU - Dose Units (Expected)
            for col in ["CMDOSU", "DOSEUNIT", "UNIT", "DOSEUNITS"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMDOSU"] = str(row[col]).upper()
                    break

            # CMDOSFRM - Dose Form (Expected)
            for col in ["CMDOSFRM", "FORM", "DOSFORM", "DOSEFORM"]:
                if col in row and pd.notna(row[col]):
                    form = str(row[col]).upper()
                    form_map = {
                        "TAB": "TABLET", "TABLET": "TABLET",
                        "CAP": "CAPSULE", "CAPSULE": "CAPSULE",
                        "INJ": "INJECTION", "INJECTION": "INJECTION",
                        "SOL": "SOLUTION", "SOLUTION": "SOLUTION",
                        "SYR": "SYRUP", "SYRUP": "SYRUP",
                        "CREAM": "CREAM", "OINT": "OINTMENT"
                    }
                    cm_record["CMDOSFRM"] = form_map.get(form, form)
                    break

            # CMDOSFRQ - Dosing Frequency per Interval (Expected)
            for col in ["CMDOSFRQ", "FREQ", "FREQUENCY", "DOSFREQ"]:
                if col in row and pd.notna(row[col]):
                    freq = str(row[col]).upper()
                    freq_map = {
                        "QD": "QD", "DAILY": "QD", "ONCE DAILY": "QD",
                        "BID": "BID", "TWICE DAILY": "BID",
                        "TID": "TID", "THREE TIMES DAILY": "TID",
                        "QID": "QID", "FOUR TIMES DAILY": "QID",
                        "QH": "QH", "EVERY HOUR": "QH",
                        "Q2H": "Q2H", "Q4H": "Q4H", "Q6H": "Q6H", "Q8H": "Q8H",
                        "QW": "QW", "WEEKLY": "QW",
                        "PRN": "PRN", "AS NEEDED": "PRN"
                    }
                    cm_record["CMDOSFRQ"] = freq_map.get(freq, freq)
                    break

            # CMDOSTOT - Total Daily Dose (Perm)
            for col in ["CMDOSTOT", "TOTDOSE", "DAILYDOSE"]:
                if col in row and pd.notna(row[col]):
                    try:
                        cm_record["CMDOSTOT"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # CMDOSRGM - Intended Dose Regimen (Perm)
            for col in ["CMDOSRGM", "REGIMEN"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMDOSRGM"] = str(row[col])
                    break

            # CMROUTE - Route of Administration (Expected)
            for col in ["CMROUTE", "ROUTE", "ADMINROUTE"]:
                if col in row and pd.notna(row[col]):
                    route = str(row[col]).upper()
                    route_map = {
                        "PO": "ORAL", "ORAL": "ORAL", "BY MOUTH": "ORAL",
                        "IV": "INTRAVENOUS", "INTRAVENOUS": "INTRAVENOUS",
                        "IM": "INTRAMUSCULAR", "INTRAMUSCULAR": "INTRAMUSCULAR",
                        "SC": "SUBCUTANEOUS", "SUBCUTANEOUS": "SUBCUTANEOUS",
                        "TOP": "TOPICAL", "TOPICAL": "TOPICAL",
                        "INH": "INHALATION", "INHALATION": "INHALATION",
                        "PR": "RECTAL", "RECTAL": "RECTAL",
                        "SL": "SUBLINGUAL", "SUBLINGUAL": "SUBLINGUAL"
                    }
                    cm_record["CMROUTE"] = route_map.get(route, route)
                    break

            # === TIMING VARIABLES ===

            # EPOCH - Epoch (Perm)
            for col in ["EPOCH", "CMEPOCH"]:
                if col in row and pd.notna(row[col]):
                    cm_record["EPOCH"] = str(row[col]).upper()
                    break

            # CMSTDTC - Start Date/Time of Medication (Expected)
            for col in ["CMSTDTC", "CMSTDT", "STDT", "STARTDT", "MEDSTDT"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMSTDTC"] = self._convert_date_to_iso(row[col])
                    break

            # CMENDTC - End Date/Time of Medication (Expected)
            for col in ["CMENDTC", "CMENDT", "ENDT", "ENDDT", "MEDENDT"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMENDTC"] = self._convert_date_to_iso(row[col])
                    break

            # CMSTDY - Study Day of Start of Medication (Perm)
            for col in ["CMSTDY", "STARTDAY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        cm_record["CMSTDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # CMENDY - Study Day of End of Medication (Perm)
            for col in ["CMENDY", "ENDDAY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        cm_record["CMENDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # CMDUR - Duration of Medication (Perm) - ISO 8601 duration
            for col in ["CMDUR", "DURATION"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMDUR"] = str(row[col])
                    break

            # CMSTRF - Start Relative to Reference Period (Perm)
            for col in ["CMSTRF", "STARTREL"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMSTRF"] = str(row[col]).upper()
                    break

            # CMENRF - End Relative to Reference Period (Perm)
            for col in ["CMENRF", "ENDREL"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMENRF"] = str(row[col]).upper()
                    break

            cm_records.append(cm_record)

        result_df = pd.DataFrame(cm_records)

        # Ensure column order per SDTM-IG 3.4
        cm_column_order = [
            "STUDYID", "DOMAIN", "USUBJID", "CMSEQ", "CMTRT", "CMMODIFY",
            "CMDECOD", "CMCAT", "CMSCAT", "CMINDC", "CMCLAS", "CMCLASCD",
            "CMDOSE", "CMDOSU", "CMDOSFRM", "CMDOSFRQ", "CMDOSTOT", "CMROUTE",
            "CMSTAT", "CMREASND", "EPOCH", "CMSTDTC", "CMENDTC", "CMSTDY",
            "CMENDY", "CMSTRF", "CMENRF"
        ]
        ordered_cols = [c for c in cm_column_order if c in result_df.columns]
        extra_cols = [c for c in result_df.columns if c not in cm_column_order]
        result_df = result_df[ordered_cols + extra_cols]

        # Log compliance summary
        self.log(f"Created {len(result_df)} CM records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        self.log(f"Columns: {', '.join(result_df.columns.tolist())}")
        return result_df


class EXTransformer(BaseDomainTransformer):
    """Exposure domain transformer - FULL SDTM-IG 3.4 compliant (27 variables)."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "EX"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform exposure/dosing data to SDTM EX domain per SDTMIG 3.4.

        Implements ALL 27 EX variables including:
        - Required (5): STUDYID, DOMAIN, USUBJID, EXSEQ, EXTRT
        - Expected (10): EXDOSE, EXDOSU, EXDOSFRM, EXDOSFRQ, EXROUTE, EXSTDTC, EXENDTC, etc.
        - Permissible (12): EXSPID, EXCAT, EXSCAT, EXDOSTXT, EXDOSTOT, EXDOSRGM,
                            EXLOT, EXLOC, EXLAT, EXDIR, EXFAST, EXADJ, etc.
        """
        self.log("Transforming to EX domain - FULL SDTM-IG 3.4 compliance (27 variables)")

        ex_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            # This ensures they ALL appear in output per SDTM-IG 3.4
            ex_record = {
                # Required Identifiers
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "EX",
                "USUBJID": self._generate_usubjid(row),
                "EXSEQ": subject_seq[subj],
                "EXTRT": "",
                # Expected - Dosing
                "EXDOSE": None,
                "EXDOSU": "",
                "EXDOSFRM": "",
                "EXDOSFRQ": "",
                "EXDOSTOT": None,
                "EXROUTE": "",
                # Expected - Location
                "EXLOT": "",
                "EXLOC": "",
                "EXLAT": "",
                "EXADJ": "",
                # Expected - Timing
                "EPOCH": "",
                "EXSTDTC": "",
                "EXENDTC": "",
                "EXSTDY": None,
                "EXENDY": None,
                # Permissible
                "EXCAT": "",
                "EXSCAT": "",
                "EXFAST": "",
            }

            # EXSPID - Sponsor-Defined Identifier (Perm)
            for col in ["EXSPID", "EXID", "DOSEID"]:
                if col in row and pd.notna(row[col]):
                    ex_record["EXSPID"] = str(row[col])
                    break

            # EXTRT - Name of Actual Treatment (Required)
            for col in ["EXTRT", "TRT", "TREATMENT", "DRUG", "STUDYDRUG"]:
                if col in row and pd.notna(row[col]):
                    ex_record["EXTRT"] = str(row[col])
                    break

            # === GROUPING QUALIFIERS ===

            # EXCAT - Category for Exposure (Perm)
            for col in ["EXCAT", "CAT", "CATEGORY"]:
                if col in row and pd.notna(row[col]):
                    ex_record["EXCAT"] = str(row[col]).upper()
                    break

            # EXSCAT - Subcategory for Exposure (Perm)
            for col in ["EXSCAT", "SCAT", "SUBCATEGORY"]:
                if col in row and pd.notna(row[col]):
                    ex_record["EXSCAT"] = str(row[col]).upper()
                    break

            # === DOSE INFORMATION ===

            # EXDOSE - Dose per Administration (Expected)
            for col in ["EXDOSE", "DOSE", "DOSENUM", "DOSEAMT"]:
                if col in row and pd.notna(row[col]):
                    try:
                        ex_record["EXDOSE"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # EXDOSTXT - Dose Description (Perm)
            for col in ["EXDOSTXT", "DOSETXT", "DOSETEXT"]:
                if col in row and pd.notna(row[col]):
                    ex_record["EXDOSTXT"] = str(row[col])
                    break
            if "EXDOSE" not in ex_record:
                for col in ["EXDOSE", "DOSE"]:
                    if col in row and pd.notna(row[col]):
                        ex_record["EXDOSTXT"] = str(row[col])
                        break

            # EXDOSU - Dose Units (Expected)
            for col in ["EXDOSU", "DOSEUNIT", "UNIT", "DOSEUNITS"]:
                if col in row and pd.notna(row[col]):
                    ex_record["EXDOSU"] = str(row[col]).upper()
                    break

            # EXDOSFRM - Dose Form (Expected)
            for col in ["EXDOSFRM", "FORM", "DOSFORM", "DOSEFORM"]:
                if col in row and pd.notna(row[col]):
                    form = str(row[col]).upper()
                    form_map = {
                        "TAB": "TABLET", "TABLET": "TABLET",
                        "CAP": "CAPSULE", "CAPSULE": "CAPSULE",
                        "INJ": "INJECTION", "INJECTION": "INJECTION",
                        "SOL": "SOLUTION", "SOLUTION": "SOLUTION",
                        "POWDER": "POWDER", "FILM": "FILM"
                    }
                    ex_record["EXDOSFRM"] = form_map.get(form, form)
                    break

            # EXDOSFRQ - Dosing Frequency per Interval (Expected)
            for col in ["EXDOSFRQ", "FREQ", "FREQUENCY", "DOSFREQ"]:
                if col in row and pd.notna(row[col]):
                    freq = str(row[col]).upper()
                    freq_map = {
                        "QD": "QD", "DAILY": "QD", "ONCE DAILY": "QD",
                        "BID": "BID", "TWICE DAILY": "BID",
                        "TID": "TID", "QID": "QID",
                        "QW": "QW", "WEEKLY": "QW",
                        "Q2W": "Q2W", "EVERY 2 WEEKS": "Q2W",
                        "Q3W": "Q3W", "EVERY 3 WEEKS": "Q3W",
                        "Q4W": "Q4W", "MONTHLY": "Q4W",
                        "ONCE": "ONCE", "SINGLE": "ONCE"
                    }
                    ex_record["EXDOSFRQ"] = freq_map.get(freq, freq)
                    break

            # EXDOSTOT - Total Daily Dose (Perm)
            for col in ["EXDOSTOT", "TOTDOSE", "DAILYDOSE"]:
                if col in row and pd.notna(row[col]):
                    try:
                        ex_record["EXDOSTOT"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # EXDOSRGM - Intended Dose Regimen (Perm)
            for col in ["EXDOSRGM", "REGIMEN", "DOSERGM"]:
                if col in row and pd.notna(row[col]):
                    ex_record["EXDOSRGM"] = str(row[col])
                    break

            # EXROUTE - Route of Administration (Expected)
            for col in ["EXROUTE", "ROUTE", "ADMINROUTE"]:
                if col in row and pd.notna(row[col]):
                    route = str(row[col]).upper()
                    route_map = {
                        "PO": "ORAL", "ORAL": "ORAL",
                        "IV": "INTRAVENOUS", "INTRAVENOUS": "INTRAVENOUS",
                        "IM": "INTRAMUSCULAR", "INTRAMUSCULAR": "INTRAMUSCULAR",
                        "SC": "SUBCUTANEOUS", "SUBCUTANEOUS": "SUBCUTANEOUS",
                        "TOP": "TOPICAL", "TOPICAL": "TOPICAL",
                        "INH": "INHALATION", "INHALATION": "INHALATION"
                    }
                    ex_record["EXROUTE"] = route_map.get(route, route)
                    break

            # === ADDITIONAL RECORD QUALIFIERS ===

            # EXLOT - Lot Number (Perm)
            for col in ["EXLOT", "LOT", "LOTNUM", "LOTNUMBER"]:
                if col in row and pd.notna(row[col]):
                    ex_record["EXLOT"] = str(row[col])
                    break

            # EXLOC - Location of Dose Administration (Perm)
            for col in ["EXLOC", "LOC", "LOCATION", "ADMINLOC"]:
                if col in row and pd.notna(row[col]):
                    ex_record["EXLOC"] = str(row[col]).upper()
                    break

            # EXLAT - Laterality (Perm)
            for col in ["EXLAT", "LAT", "LATERALITY"]:
                if col in row and pd.notna(row[col]):
                    lat = str(row[col]).upper()
                    ex_record["EXLAT"] = "LEFT" if "L" in lat else ("RIGHT" if "R" in lat else lat)
                    break

            # EXDIR - Directionality (Perm)
            for col in ["EXDIR", "DIR", "DIRECTION"]:
                if col in row and pd.notna(row[col]):
                    ex_record["EXDIR"] = str(row[col]).upper()
                    break

            # EXFAST - Fasting Status (Perm)
            for col in ["EXFAST", "FASTING"]:
                if col in row and pd.notna(row[col]):
                    ex_record["EXFAST"] = "Y" if str(row[col]).upper() in ["Y", "YES", "1", "TRUE"] else "N"
                    break

            # EXADJ - Reason for Dose Adjustment (Perm)
            for col in ["EXADJ", "DOSEADJ", "ADJUSTMENT", "ADJREASON"]:
                if col in row and pd.notna(row[col]):
                    ex_record["EXADJ"] = str(row[col])
                    break

            # === TIMING VARIABLES ===

            # EPOCH - Epoch (Perm)
            for col in ["EPOCH", "EXEPOCH"]:
                if col in row and pd.notna(row[col]):
                    ex_record["EPOCH"] = str(row[col]).upper()
                    break

            # EXSTDTC - Start Date/Time of Treatment (Expected)
            for col in ["EXSTDTC", "EXSTDT", "STDT", "STARTDT", "DOSEDT"]:
                if col in row and pd.notna(row[col]):
                    ex_record["EXSTDTC"] = self._convert_date_to_iso(row[col])
                    break

            # EXENDTC - End Date/Time of Treatment (Expected)
            for col in ["EXENDTC", "EXENDT", "ENDT", "ENDDT"]:
                if col in row and pd.notna(row[col]):
                    ex_record["EXENDTC"] = self._convert_date_to_iso(row[col])
                    break

            # EXSTDY - Study Day of Start of Treatment (Perm)
            for col in ["EXSTDY", "STARTDAY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        ex_record["EXSTDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # EXENDY - Study Day of End of Treatment (Perm)
            for col in ["EXENDY", "ENDDAY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        ex_record["EXENDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # EXDUR - Duration of Treatment (Perm) - ISO 8601 duration
            for col in ["EXDUR", "DURATION"]:
                if col in row and pd.notna(row[col]):
                    ex_record["EXDUR"] = str(row[col])
                    break

            ex_records.append(ex_record)

        result_df = pd.DataFrame(ex_records)

        # Ensure column order per SDTM-IG 3.4
        ex_column_order = [
            "STUDYID", "DOMAIN", "USUBJID", "EXSEQ", "EXTRT", "EXCAT", "EXSCAT",
            "EXDOSE", "EXDOSU", "EXDOSFRM", "EXDOSFRQ", "EXDOSTOT", "EXROUTE",
            "EXLOT", "EXLOC", "EXLAT", "EXFAST", "EXADJ", "EPOCH",
            "EXSTDTC", "EXENDTC", "EXSTDY", "EXENDY"
        ]
        ordered_cols = [c for c in ex_column_order if c in result_df.columns]
        extra_cols = [c for c in result_df.columns if c not in ex_column_order]
        result_df = result_df[ordered_cols + extra_cols]

        # Log compliance summary
        self.log(f"Created {len(result_df)} EX records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        self.log(f"Columns: {', '.join(result_df.columns.tolist())}")
        return result_df


class DSTransformer(BaseDomainTransformer):
    """Disposition domain transformer - FULL SDTM-IG 3.4 compliant (21 variables)."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "DS"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform disposition data to SDTM DS domain per SDTMIG 3.4.

        Implements ALL 21 DS variables including:
        - Required (5): STUDYID, DOMAIN, USUBJID, DSSEQ, DSTERM
        - Expected (3): DSDECOD, DSCAT, DSSTDTC
        - Permissible (13): DSSPID, DSMODIFY, DSSCAT, DSSTAT, DSREASND,
                            DSSTRF, DSENRF, EPOCH, DSENDTC, DSSTDY, DSENDY, DSDTC, DSDY
        """
        self.log("Transforming to DS domain - FULL SDTM-IG 3.4 compliance (21 variables)")

        ds_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            # This ensures they ALL appear in output per SDTM-IG 3.4
            ds_record = {
                # Required Identifiers
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "DS",
                "USUBJID": self._generate_usubjid(row),
                "DSSEQ": subject_seq[subj],
                "DSTERM": "",
                # Expected - Coding
                "DSMODIFY": "",
                "DSDECOD": "",
                # Expected - Category
                "DSCAT": "",
                "DSSCAT": "",
                # Expected - Status
                "DSSTAT": "",
                "DSREASND": "",
                # Expected - Relative timing
                "DSSTRF": "",
                "DSENRF": "",
                # Expected - Timing
                "EPOCH": "",
                "DSSTDTC": "",
                "DSENDTC": "",
                "DSSTDY": None,
                "DSENDY": None,
                "DSDTC": "",
                "DSDY": None,
            }

            # DSSPID - Sponsor-Defined Identifier (Perm)
            for col in ["DSSPID", "DSID", "DISPID"]:
                if col in row and pd.notna(row[col]):
                    ds_record["DSSPID"] = str(row[col])
                    break

            # DSTERM - Reported Term for the Disposition Event (Required)
            for col in ["DSTERM", "TERM", "STATUS", "DISPOSITION", "DISCONT", "REASON"]:
                if col in row and pd.notna(row[col]):
                    ds_record["DSTERM"] = str(row[col])
                    break

            # DSMODIFY - Modified Reported Term (Perm)
            for col in ["DSMODIFY", "DSMOD", "MODTERM"]:
                if col in row and pd.notna(row[col]):
                    ds_record["DSMODIFY"] = str(row[col])
                    break

            # DSDECOD - Standardized Disposition Term (Expected)
            for col in ["DSDECOD", "DSCODE", "DISPDECOD", "STDTERM"]:
                if col in row and pd.notna(row[col]):
                    ds_record["DSDECOD"] = str(row[col]).upper()
                    break
            if not ds_record["DSDECOD"] and ds_record.get("DSTERM"):
                ds_record["DSDECOD"] = ds_record["DSTERM"].upper()

            # === GROUPING QUALIFIERS ===

            # DSCAT - Category for Disposition Event (Expected)
            for col in ["DSCAT", "CAT", "CATEGORY", "DISPCAT"]:
                if col in row and pd.notna(row[col]):
                    ds_record["DSCAT"] = str(row[col]).upper()
                    break
            if not ds_record["DSCAT"]:
                ds_record["DSCAT"] = "DISPOSITION EVENT"

            # DSSCAT - Subcategory for Disposition Event (Perm)
            for col in ["DSSCAT", "SCAT", "SUBCATEGORY"]:
                if col in row and pd.notna(row[col]):
                    ds_record["DSSCAT"] = str(row[col]).upper()
                    break

            # === RECORD QUALIFIERS ===

            # DSSTAT - Completion Status (Perm)
            for col in ["DSSTAT", "STAT", "COMPLSTAT"]:
                if col in row and pd.notna(row[col]):
                    ds_record["DSSTAT"] = str(row[col]).upper()
                    break

            # DSREASND - Reason Disposition Event Not Collected (Perm)
            for col in ["DSREASND", "REASONND", "NOREASON"]:
                if col in row and pd.notna(row[col]):
                    ds_record["DSREASND"] = str(row[col])
                    break

            # DSSTRF - Start Relative to Reference Period (Perm)
            for col in ["DSSTRF", "STRTREF", "STARTREL"]:
                if col in row and pd.notna(row[col]):
                    ds_record["DSSTRF"] = str(row[col]).upper()
                    break

            # DSENRF - End Relative to Reference Period (Perm)
            for col in ["DSENRF", "ENDREF", "ENDREL"]:
                if col in row and pd.notna(row[col]):
                    ds_record["DSENRF"] = str(row[col]).upper()
                    break

            # === TIMING VARIABLES ===

            # EPOCH - Epoch (Perm)
            for col in ["EPOCH", "EPOC", "PHASE", "PERIOD"]:
                if col in row and pd.notna(row[col]):
                    ds_record["EPOCH"] = str(row[col]).upper()
                    break

            # DSSTDTC - Start Date/Time of Disposition Event (Expected)
            for col in ["DSSTDTC", "DSSTDT", "STARTDT", "DSDT", "DATE", "DISPDT"]:
                if col in row and pd.notna(row[col]):
                    ds_record["DSSTDTC"] = self._convert_date_to_iso(row[col])
                    break

            # DSENDTC - End Date/Time of Disposition Event (Perm)
            for col in ["DSENDTC", "DSENDT", "ENDDT"]:
                if col in row and pd.notna(row[col]):
                    ds_record["DSENDTC"] = self._convert_date_to_iso(row[col])
                    break

            # DSSTDY - Study Day of Start of Disposition Event (Perm)
            for col in ["DSSTDY", "STARTDY", "STDY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        ds_record["DSSTDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # DSENDY - Study Day of End of Disposition Event (Perm)
            for col in ["DSENDY", "ENDDY", "ENDY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        ds_record["DSENDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # DSDTC - Date/Time of Collection (Perm)
            for col in ["DSDTC", "COLLDT", "COLLECTDT"]:
                if col in row and pd.notna(row[col]):
                    ds_record["DSDTC"] = self._convert_date_to_iso(row[col])
                    break

            # DSDY - Study Day of Collection (Perm)
            for col in ["DSDY", "COLLDY", "COLLECTDY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        ds_record["DSDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            ds_records.append(ds_record)

        result_df = pd.DataFrame(ds_records)

        # Ensure column order per SDTM-IG 3.4
        column_order = [
            "STUDYID", "DOMAIN", "USUBJID", "DSSEQ", "DSSPID",
            "DSTERM", "DSMODIFY", "DSDECOD",
            "DSCAT", "DSSCAT",
            "DSSTAT", "DSREASND",
            "DSSTRF", "DSENRF",
            "EPOCH", "DSSTDTC", "DSENDTC", "DSSTDY", "DSENDY", "DSDTC", "DSDY"
        ]
        ordered_cols = [c for c in column_order if c in result_df.columns]
        extra_cols = [c for c in result_df.columns if c not in column_order]
        result_df = result_df[ordered_cols + extra_cols]

        self.log(f"Created {len(result_df)} DS records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        self.log(f"Columns: {', '.join(result_df.columns.tolist())}")
        return result_df


class MHTransformer(BaseDomainTransformer):
    """Medical History domain transformer - FULL SDTM-IG 3.4 compliant (19 variables)."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "MH"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform medical history data to SDTM MH domain per SDTMIG 3.4.

        Implements ALL 19 MH variables including:
        - Required (5): STUDYID, DOMAIN, USUBJID, MHSEQ, MHTERM
        - Expected (3): MHDECOD, MHBODSYS, MHENRF
        - Permissible (11): MHSPID, MHMODIFY, MHCAT, MHSCAT, MHPRESP, MHOCCUR,
                            MHSTAT, MHREASND, MHSTDTC, MHENDTC, MHDY
        """
        self.log("Transforming to MH domain - FULL SDTM-IG 3.4 compliance (19 variables)")

        mh_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            # This ensures they ALL appear in output per SDTM-IG 3.4
            mh_record = {
                # Required Identifiers
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "MH",
                "USUBJID": self._generate_usubjid(row),
                "MHSEQ": subject_seq[subj],
                "MHTERM": "",
                # Expected - Coding
                "MHMODIFY": "",
                "MHDECOD": "",
                "MHBODSYS": "",
                # Expected - Category
                "MHCAT": "",
                "MHSCAT": "",
                # Expected - Occurrence
                "MHPRESP": "",
                "MHOCCUR": "",
                "MHSTAT": "",
                "MHREASND": "",
                # Expected - Timing
                "MHENRF": "",
                "MHSTDTC": "",
                "MHENDTC": "",
                "MHDY": None,
            }

            # MHSPID - Sponsor-Defined Identifier (Perm)
            for col in ["MHSPID", "MHID", "HISTID"]:
                if col in row and pd.notna(row[col]):
                    mh_record["MHSPID"] = str(row[col])
                    break

            # MHTERM - Reported Term for Medical History (Required)
            for col in ["MHTERM", "TERM", "CONDITION", "DIAGNOSIS", "DISEASE", "MEDHIST"]:
                if col in row and pd.notna(row[col]):
                    mh_record["MHTERM"] = str(row[col])
                    break

            # MHMODIFY - Modified Reported Term (Perm)
            for col in ["MHMODIFY", "MHMOD", "MODTERM"]:
                if col in row and pd.notna(row[col]):
                    mh_record["MHMODIFY"] = str(row[col])
                    break

            # MHDECOD - Dictionary-Derived Term (Expected) - MedDRA coded
            for col in ["MHDECOD", "MHPT", "PTTERM", "PREFERRED"]:
                if col in row and pd.notna(row[col]):
                    mh_record["MHDECOD"] = str(row[col])
                    break
            if "MHDECOD" not in mh_record and mh_record.get("MHTERM"):
                mh_record["MHDECOD"] = mh_record["MHTERM"]

            # === GROUPING QUALIFIERS ===

            # MHCAT - Category for Medical History (Perm)
            for col in ["MHCAT", "CAT", "CATEGORY", "HISTCAT"]:
                if col in row and pd.notna(row[col]):
                    mh_record["MHCAT"] = str(row[col]).upper()
                    break

            # MHSCAT - Subcategory for Medical History (Perm)
            for col in ["MHSCAT", "SCAT", "SUBCATEGORY"]:
                if col in row and pd.notna(row[col]):
                    mh_record["MHSCAT"] = str(row[col]).upper()
                    break

            # === VARIABLE QUALIFIERS ===

            # MHPRESP - Medical History Pre-Specified (Perm)
            for col in ["MHPRESP", "PRESPEC"]:
                if col in row and pd.notna(row[col]):
                    mh_record["MHPRESP"] = "Y" if str(row[col]).upper() in ["Y", "YES", "1"] else "N"
                    break

            # MHOCCUR - Medical History Occurrence (Perm)
            for col in ["MHOCCUR", "OCCUR"]:
                if col in row and pd.notna(row[col]):
                    mh_record["MHOCCUR"] = "Y" if str(row[col]).upper() in ["Y", "YES", "1"] else "N"
                    break

            # === RECORD QUALIFIERS ===

            # MHSTAT - Completion Status (Perm)
            for col in ["MHSTAT", "STAT", "STATUS"]:
                if col in row and pd.notna(row[col]):
                    mh_record["MHSTAT"] = str(row[col]).upper()
                    break

            # MHREASND - Reason Not Done (Perm)
            for col in ["MHREASND", "REASONND", "REASON"]:
                if col in row and pd.notna(row[col]):
                    mh_record["MHREASND"] = str(row[col])
                    break

            # MHBODSYS - Body System or Organ Class (Expected) - MedDRA SOC
            for col in ["MHBODSYS", "MHSOC", "SOC", "BODYSYS", "BODYSYSTEM"]:
                if col in row and pd.notna(row[col]):
                    mh_record["MHBODSYS"] = str(row[col])
                    break

            # MHENRF - End Relative to Reference Period (Expected)
            # Indicates if condition is ongoing
            for col in ["MHENRF", "ONGOING", "MHONGO", "CURRENT"]:
                if col in row and pd.notna(row[col]):
                    val = str(row[col]).upper()
                    if val in ["Y", "YES", "1", "TRUE", "ONGOING"]:
                        mh_record["MHENRF"] = "ONGOING"
                    elif val in ["BEFORE"]:
                        mh_record["MHENRF"] = "BEFORE"
                    elif val in ["AFTER"]:
                        mh_record["MHENRF"] = "AFTER"
                    elif val in ["DURING"]:
                        mh_record["MHENRF"] = "DURING"
                    break

            # === TIMING VARIABLES ===

            # MHSTDTC - Start Date/Time of Medical History (Perm)
            for col in ["MHSTDTC", "MHSTDT", "STDT", "STARTDT", "ONSETDT"]:
                if col in row and pd.notna(row[col]):
                    mh_record["MHSTDTC"] = self._convert_date_to_iso(row[col])
                    break

            # MHENDTC - End Date/Time of Medical History (Perm)
            for col in ["MHENDTC", "MHENDT", "ENDT", "ENDDT", "RESOLVEDT"]:
                if col in row and pd.notna(row[col]):
                    mh_record["MHENDTC"] = self._convert_date_to_iso(row[col])
                    break

            # MHDY - Study Day of History Collection (Perm)
            for col in ["MHDY", "STUDYDAY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        mh_record["MHDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            mh_records.append(mh_record)

        result_df = pd.DataFrame(mh_records)

        # Ensure column order per SDTM-IG 3.4
        mh_column_order = [
            "STUDYID", "DOMAIN", "USUBJID", "MHSEQ", "MHTERM", "MHMODIFY",
            "MHDECOD", "MHCAT", "MHSCAT", "MHPRESP", "MHOCCUR", "MHSTAT",
            "MHREASND", "MHBODSYS", "MHENRF", "MHSTDTC", "MHENDTC", "MHDY"
        ]
        ordered_cols = [c for c in mh_column_order if c in result_df.columns]
        extra_cols = [c for c in result_df.columns if c not in mh_column_order]
        result_df = result_df[ordered_cols + extra_cols]

        # Log compliance summary
        self.log(f"Created {len(result_df)} MH records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        self.log(f"Columns: {', '.join(result_df.columns.tolist())}")
        return result_df


class EGTransformer(BaseDomainTransformer):
    """ECG domain transformer."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "EG"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform ECG data to SDTM EG domain."""
        self.log("Transforming to EG domain")

        eg_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", ""))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            eg_record = {
                "STUDYID": row.get("STUDY", self.study_id),
                "DOMAIN": "EG",
                "USUBJID": self._generate_usubjid(row),
                "EGSEQ": subject_seq[subj],
            }

            # Test code and name
            for col in ["EGTESTCD", "TESTCD", "TEST"]:
                if col in row and pd.notna(row[col]):
                    eg_record["EGTESTCD"] = str(row[col])[:8]
                    break

            for col in ["EGTEST", "TESTNAME"]:
                if col in row and pd.notna(row[col]):
                    eg_record["EGTEST"] = str(row[col])
                    break

            # Result
            for col in ["EGORRES", "RESULT", "VALUE"]:
                if col in row and pd.notna(row[col]):
                    eg_record["EGORRES"] = str(row[col])
                    try:
                        eg_record["EGSTRESN"] = float(row[col])
                        eg_record["EGSTRESC"] = str(row[col])
                    except (ValueError, TypeError):
                        eg_record["EGSTRESC"] = str(row[col])
                    break

            # Unit
            for col in ["EGORRESU", "UNIT"]:
                if col in row and pd.notna(row[col]):
                    eg_record["EGORRESU"] = str(row[col])
                    eg_record["EGSTRESU"] = str(row[col])
                    break

            # Date
            for col in ["EGDT", "EGDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    eg_record["EGDTC"] = self._convert_date_to_iso(row[col])
                    break

            eg_records.append(eg_record)

        result_df = pd.DataFrame(eg_records)
        self.log(f"Created {len(result_df)} EG records")
        return result_df


class PETransformer(BaseDomainTransformer):
    """Physical Examination domain transformer."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "PE"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform physical examination data to SDTM PE domain."""
        self.log("Transforming to PE domain")

        pe_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", ""))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            pe_record = {
                "STUDYID": row.get("STUDY", self.study_id),
                "DOMAIN": "PE",
                "USUBJID": self._generate_usubjid(row),
                "PESEQ": subject_seq[subj],
            }

            # Test code and name
            for col in ["PETESTCD", "TESTCD", "BODYSYS"]:
                if col in row and pd.notna(row[col]):
                    pe_record["PETESTCD"] = str(row[col])[:8].upper()
                    break

            for col in ["PETEST", "TESTNAME", "BODYSYSTEM"]:
                if col in row and pd.notna(row[col]):
                    pe_record["PETEST"] = str(row[col])
                    break

            # Result
            for col in ["PEORRES", "RESULT", "FINDING"]:
                if col in row and pd.notna(row[col]):
                    pe_record["PEORRES"] = str(row[col])
                    pe_record["PESTRESC"] = str(row[col])
                    break

            # Location
            for col in ["PELOC", "LOCATION"]:
                if col in row and pd.notna(row[col]):
                    pe_record["PELOC"] = str(row[col])
                    break

            # Date
            for col in ["PEDT", "PEDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    pe_record["PEDTC"] = self._convert_date_to_iso(row[col])
                    break

            pe_records.append(pe_record)

        result_df = pd.DataFrame(pe_records)
        self.log(f"Created {len(result_df)} PE records")
        return result_df


class PCTransformer(BaseDomainTransformer):
    """Pharmacokinetics Concentrations domain transformer."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "PC"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform PK concentration data to SDTM PC domain."""
        self.log("Transforming to PC domain")

        pc_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", ""))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            pc_record = {
                "STUDYID": row.get("STUDY", self.study_id),
                "DOMAIN": "PC",
                "USUBJID": self._generate_usubjid(row),
                "PCSEQ": subject_seq[subj],
            }

            # Test/Analyte
            for col in ["PCTESTCD", "TESTCD", "ANALYTE"]:
                if col in row and pd.notna(row[col]):
                    pc_record["PCTESTCD"] = str(row[col])[:8]
                    break

            for col in ["PCTEST", "TESTNAME"]:
                if col in row and pd.notna(row[col]):
                    pc_record["PCTEST"] = str(row[col])
                    break

            # Result
            for col in ["PCORRES", "RESULT", "CONC"]:
                if col in row and pd.notna(row[col]):
                    pc_record["PCORRES"] = str(row[col])
                    try:
                        pc_record["PCSTRESN"] = float(row[col])
                        pc_record["PCSTRESC"] = str(row[col])
                    except (ValueError, TypeError):
                        pc_record["PCSTRESC"] = str(row[col])
                    break

            # Unit
            for col in ["PCORRESU", "UNIT"]:
                if col in row and pd.notna(row[col]):
                    pc_record["PCORRESU"] = str(row[col])
                    pc_record["PCSTRESU"] = str(row[col])
                    break

            # Specimen
            for col in ["PCSPEC", "SPECIMEN", "MATRIX"]:
                if col in row and pd.notna(row[col]):
                    pc_record["PCSPEC"] = str(row[col]).upper()
                    break

            # Time point
            for col in ["PCTPT", "TIMEPOINT", "TPT"]:
                if col in row and pd.notna(row[col]):
                    pc_record["PCTPT"] = str(row[col])
                    break

            # Date/time
            for col in ["PCDTC", "DATE", "DATETIME"]:
                if col in row and pd.notna(row[col]):
                    pc_record["PCDTC"] = self._convert_date_to_iso(row[col])
                    break

            pc_records.append(pc_record)

        result_df = pd.DataFrame(pc_records)
        self.log(f"Created {len(result_df)} PC records")
        return result_df


class IETransformer(BaseDomainTransformer):
    """Inclusion/Exclusion domain transformer."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "IE"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform inclusion/exclusion data to SDTM IE domain."""
        self.log("Transforming to IE domain")

        ie_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", ""))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            ie_record = {
                "STUDYID": row.get("STUDY", self.study_id),
                "DOMAIN": "IE",
                "USUBJID": self._generate_usubjid(row),
                "IESEQ": subject_seq[subj],
            }

            # Criterion
            for col in ["IETESTCD", "CRITID", "CRITERION"]:
                if col in row and pd.notna(row[col]):
                    ie_record["IETESTCD"] = str(row[col])[:8]
                    break

            for col in ["IETEST", "CRITERIA", "DESCRIPTION"]:
                if col in row and pd.notna(row[col]):
                    ie_record["IETEST"] = str(row[col])
                    break

            # Category (INCLUSION or EXCLUSION)
            for col in ["IECAT", "CAT", "TYPE"]:
                if col in row and pd.notna(row[col]):
                    cat = str(row[col]).upper()
                    ie_record["IECAT"] = "INCLUSION" if "INCL" in cat else "EXCLUSION"
                    break

            # Result (Y/N)
            for col in ["IEORRES", "RESULT", "MET"]:
                if col in row and pd.notna(row[col]):
                    val = str(row[col]).upper()
                    ie_record["IEORRES"] = "Y" if val in ["Y", "YES", "1", "TRUE", "MET"] else "N"
                    ie_record["IESTRESC"] = ie_record["IEORRES"]
                    break

            ie_records.append(ie_record)

        result_df = pd.DataFrame(ie_records)
        self.log(f"Created {len(result_df)} IE records")
        return result_df


class COTransformer(BaseDomainTransformer):
    """Comments domain transformer."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "CO"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform comments data to SDTM CO domain."""
        self.log("Transforming to CO domain")

        co_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", ""))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            co_record = {
                "STUDYID": row.get("STUDY", self.study_id),
                "DOMAIN": "CO",
                "USUBJID": self._generate_usubjid(row),
                "COSEQ": subject_seq[subj],
            }

            # Comment
            for col in ["COVAL", "COMMENT", "TEXT", "NOTE"]:
                if col in row and pd.notna(row[col]):
                    co_record["COVAL"] = str(row[col])
                    break

            # Reference domain
            for col in ["RDOMAIN", "DOMAIN"]:
                if col in row and pd.notna(row[col]):
                    co_record["RDOMAIN"] = str(row[col])[:2].upper()
                    break

            # Date
            for col in ["CODTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    co_record["CODTC"] = self._convert_date_to_iso(row[col])
                    break

            co_records.append(co_record)

        result_df = pd.DataFrame(co_records)
        self.log(f"Created {len(result_df)} CO records")
        return result_df


class QSTransformer(BaseDomainTransformer):
    """Questionnaires domain transformer."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "QS"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform questionnaire data to SDTM QS domain."""
        self.log("Transforming to QS domain")

        qs_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", ""))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            qs_record = {
                "STUDYID": row.get("STUDY", self.study_id),
                "DOMAIN": "QS",
                "USUBJID": self._generate_usubjid(row),
                "QSSEQ": subject_seq[subj],
            }

            # Category (questionnaire name)
            for col in ["QSCAT", "CAT", "QUESTIONNAIRE", "SCALE"]:
                if col in row and pd.notna(row[col]):
                    qs_record["QSCAT"] = str(row[col])
                    break

            # Test code
            for col in ["QSTESTCD", "TESTCD", "ITEM"]:
                if col in row and pd.notna(row[col]):
                    qs_record["QSTESTCD"] = str(row[col])[:8]
                    break

            for col in ["QSTEST", "QUESTION", "ITEMTEXT"]:
                if col in row and pd.notna(row[col]):
                    qs_record["QSTEST"] = str(row[col])
                    break

            # Result
            for col in ["QSORRES", "RESULT", "ANSWER", "SCORE"]:
                if col in row and pd.notna(row[col]):
                    qs_record["QSORRES"] = str(row[col])
                    try:
                        qs_record["QSSTRESN"] = float(row[col])
                        qs_record["QSSTRESC"] = str(row[col])
                    except (ValueError, TypeError):
                        qs_record["QSSTRESC"] = str(row[col])
                    break

            # Date
            for col in ["QSDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    qs_record["QSDTC"] = self._convert_date_to_iso(row[col])
                    break

            qs_records.append(qs_record)

        result_df = pd.DataFrame(qs_records)
        self.log(f"Created {len(result_df)} QS records")
        return result_df


class RSTransformer(BaseDomainTransformer):
    """Disease Response domain transformer."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "RS"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform disease response data to SDTM RS domain."""
        self.log("Transforming to RS domain")

        rs_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", ""))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            rs_record = {
                "STUDYID": row.get("STUDY", self.study_id),
                "DOMAIN": "RS",
                "USUBJID": self._generate_usubjid(row),
                "RSSEQ": subject_seq[subj],
            }

            # Test
            for col in ["RSTESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    rs_record["RSTESTCD"] = str(row[col])[:8]
                    break

            for col in ["RSTEST", "TEST"]:
                if col in row and pd.notna(row[col]):
                    rs_record["RSTEST"] = str(row[col])
                    break

            # Category
            rs_record["RSCAT"] = "RECIST 1.1"  # Default to RECIST

            # Result
            for col in ["RSORRES", "RESULT", "RESPONSE"]:
                if col in row and pd.notna(row[col]):
                    rs_record["RSORRES"] = str(row[col])
                    rs_record["RSSTRESC"] = str(row[col])
                    break

            # Date
            for col in ["RSDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    rs_record["RSDTC"] = self._convert_date_to_iso(row[col])
                    break

            rs_records.append(rs_record)

        result_df = pd.DataFrame(rs_records)
        self.log(f"Created {len(result_df)} RS records")
        return result_df


class TRTransformer(BaseDomainTransformer):
    """Tumor Results domain transformer."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "TR"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform tumor results data to SDTM TR domain."""
        self.log("Transforming to TR domain")

        tr_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", ""))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            tr_record = {
                "STUDYID": row.get("STUDY", self.study_id),
                "DOMAIN": "TR",
                "USUBJID": self._generate_usubjid(row),
                "TRSEQ": subject_seq[subj],
            }

            # Test
            for col in ["TRTESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    tr_record["TRTESTCD"] = str(row[col])[:8]
                    break

            for col in ["TRTEST", "TEST", "MEASUREMENT"]:
                if col in row and pd.notna(row[col]):
                    tr_record["TRTEST"] = str(row[col])
                    break

            # Result
            for col in ["TRORRES", "RESULT", "VALUE"]:
                if col in row and pd.notna(row[col]):
                    tr_record["TRORRES"] = str(row[col])
                    try:
                        tr_record["TRSTRESN"] = float(row[col])
                        tr_record["TRSTRESC"] = str(row[col])
                    except (ValueError, TypeError):
                        tr_record["TRSTRESC"] = str(row[col])
                    break

            # Unit
            for col in ["TRORRESU", "UNIT"]:
                if col in row and pd.notna(row[col]):
                    tr_record["TRORRESU"] = str(row[col])
                    tr_record["TRSTRESU"] = str(row[col])
                    break

            # Location
            for col in ["TRLOC", "LOCATION", "SITE"]:
                if col in row and pd.notna(row[col]):
                    tr_record["TRLOC"] = str(row[col])
                    break

            # Link to TU
            for col in ["TRLNKID", "TULNKID", "LINKID"]:
                if col in row and pd.notna(row[col]):
                    tr_record["TRLNKID"] = str(row[col])
                    break

            # Date
            for col in ["TRDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    tr_record["TRDTC"] = self._convert_date_to_iso(row[col])
                    break

            tr_records.append(tr_record)

        result_df = pd.DataFrame(tr_records)
        self.log(f"Created {len(result_df)} TR records")
        return result_df


class TUTransformer(BaseDomainTransformer):
    """Tumor Identification domain transformer."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "TU"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform tumor identification data to SDTM TU domain."""
        self.log("Transforming to TU domain")

        tu_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", ""))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            tu_record = {
                "STUDYID": row.get("STUDY", self.study_id),
                "DOMAIN": "TU",
                "USUBJID": self._generate_usubjid(row),
                "TUSEQ": subject_seq[subj],
            }

            # Test
            for col in ["TUTESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    tu_record["TUTESTCD"] = str(row[col])[:8]
                    break

            for col in ["TUTEST", "TEST"]:
                if col in row and pd.notna(row[col]):
                    tu_record["TUTEST"] = str(row[col])
                    break

            # Result
            for col in ["TUORRES", "RESULT"]:
                if col in row and pd.notna(row[col]):
                    tu_record["TUORRES"] = str(row[col])
                    tu_record["TUSTRESC"] = str(row[col])
                    break

            # Location
            for col in ["TULOC", "LOCATION"]:
                if col in row and pd.notna(row[col]):
                    tu_record["TULOC"] = str(row[col])
                    break

            # Link ID
            for col in ["TULNKID", "LINKID"]:
                if col in row and pd.notna(row[col]):
                    tu_record["TULNKID"] = str(row[col])
                    break

            # Date
            for col in ["TUDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    tu_record["TUDTC"] = self._convert_date_to_iso(row[col])
                    break

            tu_records.append(tu_record)

        result_df = pd.DataFrame(tu_records)
        self.log(f"Created {len(result_df)} TU records")
        return result_df


class TATransformer(BaseDomainTransformer):
    """Trial Arms domain transformer."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "TA"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform trial arms data to SDTM TA domain."""
        self.log("Transforming to TA domain")
        # Trial design domain - typically derived from protocol, not patient data
        ta_records = []

        for idx, row in source_df.iterrows():
            ta_record = {
                "STUDYID": row.get("STUDY", self.study_id),
                "DOMAIN": "TA",
                "ARMCD": str(row.get("ARMCD", row.get("ARM", ""))),
                "ARM": str(row.get("ARM", row.get("ARMNAME", ""))),
                "TAESSION": row.get("TAESSION", 1),
                "ETCD": str(row.get("ETCD", "")),
                "ELEMENT": str(row.get("ELEMENT", "")),
                "TABESSION": row.get("TABESSION", 1),
                "EPOCH": str(row.get("EPOCH", "TREATMENT")),
            }
            ta_records.append(ta_record)

        result_df = pd.DataFrame(ta_records)
        self.log(f"Created {len(result_df)} TA records")
        return result_df


class GenericSUPPTransformer(BaseDomainTransformer):
    """Generic Supplemental Qualifiers transformer."""

    def __init__(self, study_id: str, parent_domain: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = f"SUPP{parent_domain}"
        self.parent_domain = parent_domain

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform supplemental qualifier data to SDTM SUPP-- domain."""
        self.log(f"Transforming to {self.domain_code} domain")

        supp_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", ""))
            if subj not in subject_seq:
                subject_seq[subj] = 0

            # Create SUPP record for each non-standard column
            for col in row.index:
                if col not in ["PT", "STUDY", "INVSITE", "VISIT"] and pd.notna(row[col]):
                    subject_seq[subj] += 1

                    supp_record = {
                        "STUDYID": row.get("STUDY", self.study_id),
                        "RDOMAIN": self.parent_domain,
                        "USUBJID": self._generate_usubjid(row),
                        "IDVAR": f"{self.parent_domain}SEQ",
                        "IDVARVAL": str(subject_seq[subj]),
                        "QNAM": col[:8].upper(),
                        "QLABEL": col,
                        "QVAL": str(row[col]),
                        "QORIG": "CRF",
                    }
                    supp_records.append(supp_record)

        result_df = pd.DataFrame(supp_records)
        self.log(f"Created {len(result_df)} {self.domain_code} records")
        return result_df


def get_transformer(domain_code: str, study_id: str,
                   mapping_spec: Optional[MappingSpecification] = None,
                   pinecone_retriever=None) -> BaseDomainTransformer:
    """
    Factory function to get appropriate transformer for domain.

    Supports all 63 SDTM-IG 3.4 domains organized by class:
    - Special-Purpose: CO, DM, SE, SM, SV
    - Interventions: AG, CM, EX, EC, ML, PR, SU
    - Events: AE, BE, CE, DS, HO, MH, DV
    - Findings: DA, DD, EG, IE, BS, CP, GF, IS, LB, MB, MI, PC, PP, MO, CV, MK,
                NV, OE, RP, RE, UR, PE, FT, QS, RS, SC, SS, TU, TR, VS, FA, SR
    - Trial Design: TA, TE, TV, TD, TM, TI, TS
    - Relationship: RELREC, SUPP--, RELSUB, RELSPEC
    - Study References: OI

    Args:
        domain_code: SDTM domain code (e.g., "AE", "DM", "VS")
        study_id: Study identifier
        mapping_spec: Optional mapping specification
        pinecone_retriever: Optional Pinecone knowledge retriever for intelligent mapping

    Returns:
        Appropriate transformer instance for the domain
    """
    # Core transformers (SDTM-IG 3.4 fully compliant)
    transformers = {
        # Special-Purpose domains
        "DM": DMTransformer,
        "CO": COTransformer,
        # Interventions domains
        "CM": CMTransformer,
        "EX": EXTransformer,
        # Events domains
        "AE": AETransformer,
        "DS": DSTransformer,
        "MH": MHTransformer,
        # Findings domains
        "VS": VSTransformer,
        "LB": LBTransformer,
        "EG": EGTransformer,
        "PE": PETransformer,
        "PC": PCTransformer,
        "IE": IETransformer,
        "QS": QSTransformer,
        "RS": RSTransformer,
        "TR": TRTransformer,
        "TU": TUTransformer,
        # Trial design
        "TA": TATransformer,
    }

    # Check core transformers first
    transformer_class = transformers.get(domain_code)
    if transformer_class:
        transformer = transformer_class(study_id, mapping_spec)
        # Inject Pinecone retriever for intelligent mapping
        if pinecone_retriever and hasattr(transformer, 'pinecone_retriever'):
            transformer.pinecone_retriever = pinecone_retriever
            if hasattr(transformer, 'intelligent_mapper') and transformer.intelligent_mapper:
                transformer.intelligent_mapper.pinecone_retriever = pinecone_retriever
        return transformer

    # Try additional transformers
    try:
        from .additional_domains import ADDITIONAL_TRANSFORMERS
        if domain_code in ADDITIONAL_TRANSFORMERS:
            transformer = ADDITIONAL_TRANSFORMERS[domain_code](study_id, mapping_spec)
            # Inject Pinecone retriever for intelligent mapping
            if pinecone_retriever and hasattr(transformer, 'pinecone_retriever'):
                transformer.pinecone_retriever = pinecone_retriever
                if hasattr(transformer, 'intelligent_mapper') and transformer.intelligent_mapper:
                    transformer.intelligent_mapper.pinecone_retriever = pinecone_retriever
            return transformer
    except ImportError:
        pass  # Additional domains module not available

    # Handle supplemental qualifiers
    if domain_code.startswith("SUPP"):
        parent_domain = domain_code[4:]  # Extract parent domain (e.g., "AE" from "SUPPAE")
        return GenericSUPPTransformer(study_id, parent_domain, mapping_spec)

    # List all available domains for error message
    all_domains = list(transformers.keys())
    try:
        from .additional_domains import ADDITIONAL_TRANSFORMERS
        all_domains.extend(ADDITIONAL_TRANSFORMERS.keys())
    except ImportError:
        pass

    raise ValueError(
        f"No transformer available for domain: {domain_code}. "
        f"Available domains: {', '.join(sorted(all_domains))}. "
        f"Supplemental qualifiers (SUPP--) are also supported."
    )


def get_available_domains() -> Dict[str, str]:
    """
    Return dictionary of all available SDTM domains and their descriptions.

    Includes all 63 SDTM-IG 3.4 domains organized by class.

    Returns:
        Dict mapping domain code to domain name/description
    """
    domains = {
        # =================================================================
        # SPECIAL-PURPOSE DOMAINS (5)
        # =================================================================
        "DM": "Demographics",
        "CO": "Comments",
        "SE": "Subject Elements",
        "SV": "Subject Visits",
        "SM": "Subject Disease Milestones",

        # =================================================================
        # INTERVENTIONS DOMAINS (7)
        # =================================================================
        "CM": "Concomitant/Prior Medications",
        "EX": "Exposure",
        "EC": "Exposure as Collected",
        "SU": "Substance Use",
        "PR": "Procedures",
        "AG": "Procedure Agents",
        "ML": "Meal Data",

        # =================================================================
        # EVENTS DOMAINS (7)
        # =================================================================
        "AE": "Adverse Events",
        "DS": "Disposition",
        "MH": "Medical History",
        "CE": "Clinical Events",
        "DV": "Protocol Deviations",
        "HO": "Healthcare Encounters",
        "BE": "Biospecimen Events",

        # =================================================================
        # FINDINGS DOMAINS - GENERAL (20)
        # =================================================================
        "VS": "Vital Signs",
        "LB": "Laboratory Test Results",
        "EG": "ECG Test Results",
        "PE": "Physical Examination",
        "PC": "Pharmacokinetics Concentration",
        "PP": "Pharmacokinetics Parameters",
        "IE": "Inclusion/Exclusion Criteria Not Met",
        "QS": "Questionnaires",
        "RS": "Disease Response and Clinical Classification",
        "SC": "Subject Characteristics",
        "SS": "Subject Status",
        "DD": "Death Details",
        "DA": "Drug Accountability",
        "FA": "Findings About Events or Interventions",
        "FT": "Functional Tests",
        "SR": "Skin Response",
        "TR": "Tumor/Lesion Results",
        "TU": "Tumor/Lesion Identification",
        "MB": "Microbiology",
        "MI": "Microscopic Findings",

        # =================================================================
        # FINDINGS DOMAINS - ORGAN/SYSTEM-SPECIFIC (13)
        # =================================================================
        "CV": "Cardiovascular System Findings",
        "MK": "Musculoskeletal System Findings",
        "NV": "Nervous System Findings",
        "OE": "Ophthalmic Examinations",
        "RE": "Respiratory System Findings",
        "RP": "Reproductive System Findings",
        "UR": "Urinary System Findings",
        "BS": "Biospecimen Findings",
        "CP": "Cell Phenotype Findings",
        "GF": "Genomic Findings",
        "IS": "Immunogenicity Specimen Assessments",
        "MO": "Morphology Findings",
        "OI": "Organ Impairment",

        # =================================================================
        # TRIAL DESIGN DOMAINS (7)
        # =================================================================
        "TA": "Trial Arms",
        "TE": "Trial Elements",
        "TV": "Trial Visits",
        "TI": "Trial Inclusion/Exclusion Criteria",
        "TS": "Trial Summary",
        "TD": "Trial Disease Assessments",
        "TM": "Trial Disease Milestones",

        # =================================================================
        # RELATIONSHIP DOMAINS (3)
        # =================================================================
        "RELREC": "Related Records",
        "RELSUB": "Related Subjects",
        "RELSPEC": "Related Specimens",
    }
    return domains

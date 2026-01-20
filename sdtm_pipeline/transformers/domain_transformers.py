"""
SDTM Domain Transformers
========================
Transform raw clinical data to SDTM format for each domain.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod

from ..models.sdtm_models import (
    MappingSpecification,
    TransformationResult,
    SDTM_DOMAINS,
    CONTROLLED_TERMINOLOGY
)


class BaseDomainTransformer(ABC):
    """Base class for SDTM domain transformers."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        self.study_id = study_id
        self.mapping_spec = mapping_spec
        self.domain_code = ""
        self.transformation_log: List[str] = []

    def log(self, message: str):
        """Add message to transformation log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.transformation_log.append(f"[{timestamp}] {message}")

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
        """Generate USUBJID from row data."""
        study = row.get("STUDY", row.get("STUDYID", self.study_id))
        site = row.get("INVSITE", row.get("SITEID", "001"))
        subj = row.get("PT", row.get("SUBJID", ""))

        # Clean up site ID
        if site and "_" in str(site):
            site = str(site).split("_")[-1]

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

        try:
            result_df = self.transform(source_df)

            self.log(f"Output records: {len(result_df)}")
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
    """Demographics domain transformer."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "DM"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform demographics data to SDTM DM domain."""
        self.log("Transforming to DM domain")

        dm_records = []

        for idx, row in source_df.iterrows():
            dm_record = {
                "STUDYID": row.get("STUDY", self.study_id),
                "DOMAIN": "DM",
                "USUBJID": self._generate_usubjid(row),
                "SUBJID": str(row.get("PT", "")),
                "SITEID": str(row.get("INVSITE", "")).split("_")[-1] if row.get("INVSITE") else "",
            }

            # Birth date
            if "DOB" in row:
                dm_record["BRTHDTC"] = self._convert_date_to_iso(row["DOB"])

            # Sex
            sex_col = "GENDER" if "GENDER" in source_df.columns else "GENDRL"
            if sex_col in row:
                dm_record["SEX"] = self._map_sex(row[sex_col])

            # Race
            if "RCE" in row:
                dm_record["RACE"] = self._map_race(row["RCE"])

            # Derive ethnicity from race if Hispanic
            race_val = str(row.get("RCE", "")).upper()
            if "HISPANIC" in race_val:
                dm_record["ETHNIC"] = "HISPANIC OR LATINO"
            else:
                dm_record["ETHNIC"] = "NOT HISPANIC OR LATINO"

            # Age (would need reference date in real implementation)
            # For now, calculate from birth date if available
            if dm_record.get("BRTHDTC"):
                try:
                    birth_date = datetime.strptime(dm_record["BRTHDTC"][:10], "%Y-%m-%d")
                    ref_date = datetime.now()  # Would use RFSTDTC in production
                    age = (ref_date - birth_date).days // 365
                    dm_record["AGE"] = age
                    dm_record["AGEU"] = "YEARS"
                except Exception:
                    pass

            dm_records.append(dm_record)

        result_df = pd.DataFrame(dm_records)

        # Reorder columns
        dm_cols = ["STUDYID", "DOMAIN", "USUBJID", "SUBJID", "SITEID",
                   "BRTHDTC", "AGE", "AGEU", "SEX", "RACE", "ETHNIC"]
        existing_cols = [c for c in dm_cols if c in result_df.columns]
        result_df = result_df[existing_cols]

        self.log(f"Created {len(result_df)} DM records")
        return result_df


class AETransformer(BaseDomainTransformer):
    """Adverse Events domain transformer."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "AE"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform adverse event data to SDTM AE domain."""
        self.log("Transforming to AE domain")

        ae_records = []

        # Group by subject for sequence numbering
        if "PT" in source_df.columns:
            source_df = source_df.sort_values(["PT"])

        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", ""))

            # Initialize or increment sequence
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            ae_record = {
                "STUDYID": row.get("STUDY", self.study_id),
                "DOMAIN": "AE",
                "USUBJID": self._generate_usubjid(row),
                "AESEQ": subject_seq[subj],
            }

            # Adverse event term
            for col in ["AETERM", "AEDESC", "AENAME", "AE"]:
                if col in row and pd.notna(row[col]):
                    ae_record["AETERM"] = str(row[col])
                    break

            # Coded term (would use MedDRA in production)
            ae_record["AEDECOD"] = ae_record.get("AETERM", "")

            # Dates
            for src, tgt in [("AESTDT", "AESTDTC"), ("AEENDT", "AEENDTC"),
                             ("STDT", "AESTDTC"), ("ENDT", "AEENDTC")]:
                if src in row and pd.notna(row[src]):
                    ae_record[tgt] = self._convert_date_to_iso(row[src])

            # Severity
            if "AESEV" in row and pd.notna(row["AESEV"]):
                sev = str(row["AESEV"]).upper()
                ae_record["AESEV"] = sev if sev in ["MILD", "MODERATE", "SEVERE"] else "MODERATE"

            # Relationship
            if "AEREL" in row and pd.notna(row["AEREL"]):
                ae_record["AEREL"] = str(row["AEREL"]).upper()

            # Seriousness
            if "AESER" in row:
                ae_record["AESER"] = "Y" if str(row["AESER"]).upper() in ["Y", "YES", "1", "TRUE"] else "N"

            # Outcome
            if "AEOUT" in row and pd.notna(row["AEOUT"]):
                ae_record["AEOUT"] = str(row["AEOUT"])

            # Action taken
            if "AEACN" in row and pd.notna(row["AEACN"]):
                ae_record["AEACN"] = str(row["AEACN"])

            ae_records.append(ae_record)

        result_df = pd.DataFrame(ae_records)

        # Reorder columns
        ae_cols = ["STUDYID", "DOMAIN", "USUBJID", "AESEQ", "AETERM", "AEDECOD",
                   "AESTDTC", "AEENDTC", "AESEV", "AESER", "AEREL", "AEOUT", "AEACN"]
        existing_cols = [c for c in ae_cols if c in result_df.columns]
        result_df = result_df[existing_cols]

        self.log(f"Created {len(result_df)} AE records")
        return result_df


class VSTransformer(BaseDomainTransformer):
    """Vital Signs domain transformer."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "VS"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform vital signs data to SDTM VS domain."""
        self.log("Transforming to VS domain")

        vs_records = []
        subject_seq = {}

        # Define vital sign test mappings
        # Support both standard names and Maxis-08 specific column names
        test_mappings = {
            # Standard names
            "SYSBP": ("SYSBP", "Systolic Blood Pressure", "mmHg"),
            "DIABP": ("DIABP", "Diastolic Blood Pressure", "mmHg"),
            "PULSE": ("PULSE", "Pulse Rate", "beats/min"),
            "RESP": ("RESP", "Respiratory Rate", "breaths/min"),
            "TEMP": ("TEMP", "Temperature", "C"),
            "WEIGHT": ("WEIGHT", "Weight", "kg"),
            "HEIGHT": ("HEIGHT", "Height", "cm"),
            # Maxis-08 specific column names
            "VTBPS2": ("SYSBP", "Systolic Blood Pressure", "mmHg"),
            "VTBPD2": ("DIABP", "Diastolic Blood Pressure", "mmHg"),
            "VTPLS2": ("PULSE", "Pulse Rate", "beats/min"),
            "VTRRT2": ("RESP", "Respiratory Rate", "breaths/min"),
            "VTTP2": ("TEMP", "Temperature", "C"),
            "GNNUM1": ("WEIGHT", "Weight", "kg"),
            "GNNUM2": ("HEIGHT", "Height", "cm"),
        }

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", ""))

            # Process each vital sign in the row
            for src_col, (testcd, test_name, unit) in test_mappings.items():
                if src_col in row and pd.notna(row[src_col]):
                    # Initialize or increment sequence
                    if subj not in subject_seq:
                        subject_seq[subj] = 0
                    subject_seq[subj] += 1

                    vs_record = {
                        "STUDYID": row.get("STUDY", self.study_id),
                        "DOMAIN": "VS",
                        "USUBJID": self._generate_usubjid(row),
                        "VSSEQ": subject_seq[subj],
                        "VSTESTCD": testcd,
                        "VSTEST": test_name,
                        "VSORRES": str(row[src_col]),
                        "VSORRESU": unit,
                    }

                    # Standard result
                    try:
                        vs_record["VSSTRESN"] = float(row[src_col])
                        vs_record["VSSTRESC"] = str(row[src_col])
                        vs_record["VSSTRESU"] = unit
                    except (ValueError, TypeError):
                        vs_record["VSSTRESC"] = str(row[src_col])

                    # Date
                    for date_col in ["VSDT", "VSDTC", "DATE", "VISITDT", "VTDT"]:
                        if date_col in row and pd.notna(row[date_col]):
                            vs_record["VSDTC"] = self._convert_date_to_iso(row[date_col])
                            break

                    # Visit
                    if "VISIT" in row:
                        vs_record["VISIT"] = str(row["VISIT"])
                        vs_record["VISITNUM"] = row["VISIT"]

                    # Position
                    if "VSPOS" in row and pd.notna(row["VSPOS"]):
                        vs_record["VSPOS"] = str(row["VSPOS"]).upper()

                    vs_records.append(vs_record)

        result_df = pd.DataFrame(vs_records)

        # Reorder columns
        vs_cols = ["STUDYID", "DOMAIN", "USUBJID", "VSSEQ", "VSTESTCD", "VSTEST",
                   "VSORRES", "VSORRESU", "VSSTRESC", "VSSTRESN", "VSSTRESU",
                   "VSDTC", "VISIT", "VISITNUM", "VSPOS"]
        existing_cols = [c for c in vs_cols if c in result_df.columns]
        result_df = result_df[existing_cols]

        self.log(f"Created {len(result_df)} VS records")
        return result_df


class LBTransformer(BaseDomainTransformer):
    """Laboratory domain transformer."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "LB"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform laboratory data to SDTM LB domain."""
        self.log("Transforming to LB domain")

        lb_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", ""))

            # Initialize or increment sequence
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            lb_record = {
                "STUDYID": row.get("STUDY", self.study_id),
                "DOMAIN": "LB",
                "USUBJID": self._generate_usubjid(row),
                "LBSEQ": subject_seq[subj],
            }

            # Test identification
            for col in ["LBTESTCD", "TESTCD", "TEST"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBTESTCD"] = str(row[col])[:8]  # TESTCD max 8 chars
                    break

            for col in ["LBTEST", "TESTNAME", "TEST"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBTEST"] = str(row[col])
                    break

            # Category
            for col in ["LBCAT", "CAT", "CATEGORY"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBCAT"] = str(row[col])
                    break

            # Result
            for col in ["LBORRES", "RESULT", "VALUE"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBORRES"] = str(row[col])
                    try:
                        lb_record["LBSTRESN"] = float(row[col])
                        lb_record["LBSTRESC"] = str(row[col])
                    except (ValueError, TypeError):
                        lb_record["LBSTRESC"] = str(row[col])
                    break

            # Units
            for col in ["LBORRESU", "UNIT", "UNITS"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBORRESU"] = str(row[col])
                    lb_record["LBSTRESU"] = str(row[col])
                    break

            # Reference ranges
            for col in ["LBORNRLO", "NRLO", "LOLIMIT"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBORNRLO"] = str(row[col])
                    try:
                        lb_record["LBSTNRLO"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            for col in ["LBORNRHI", "NRHI", "HILIMIT"]:
                if col in row and pd.notna(row[col]):
                    lb_record["LBORNRHI"] = str(row[col])
                    try:
                        lb_record["LBSTNRHI"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # Normal range indicator
            if "LBSTRESN" in lb_record and "LBSTNRLO" in lb_record:
                result = lb_record["LBSTRESN"]
                low = lb_record.get("LBSTNRLO", float('-inf'))
                high = lb_record.get("LBSTNRHI", float('inf'))

                if result < low:
                    lb_record["LBNRIND"] = "LOW"
                elif result > high:
                    lb_record["LBNRIND"] = "HIGH"
                else:
                    lb_record["LBNRIND"] = "NORMAL"

            # Date
            for date_col in ["LBDT", "LBDTC", "DATE", "VISITDT"]:
                if date_col in row and pd.notna(row[date_col]):
                    lb_record["LBDTC"] = self._convert_date_to_iso(row[date_col])
                    break

            # Visit
            if "VISIT" in row:
                lb_record["VISIT"] = str(row["VISIT"])
                lb_record["VISITNUM"] = row["VISIT"]

            lb_records.append(lb_record)

        result_df = pd.DataFrame(lb_records)

        # Reorder columns
        lb_cols = ["STUDYID", "DOMAIN", "USUBJID", "LBSEQ", "LBTESTCD", "LBTEST",
                   "LBCAT", "LBORRES", "LBORRESU", "LBORNRLO", "LBORNRHI",
                   "LBSTRESC", "LBSTRESN", "LBSTRESU", "LBSTNRLO", "LBSTNRHI",
                   "LBNRIND", "LBDTC", "VISIT", "VISITNUM"]
        existing_cols = [c for c in lb_cols if c in result_df.columns]
        if existing_cols:
            result_df = result_df[existing_cols]

        self.log(f"Created {len(result_df)} LB records")
        return result_df


class CMTransformer(BaseDomainTransformer):
    """Concomitant Medications domain transformer."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "CM"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform concomitant medication data to SDTM CM domain."""
        self.log("Transforming to CM domain")

        cm_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", ""))

            # Initialize or increment sequence
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            cm_record = {
                "STUDYID": row.get("STUDY", self.study_id),
                "DOMAIN": "CM",
                "USUBJID": self._generate_usubjid(row),
                "CMSEQ": subject_seq[subj],
            }

            # Treatment name
            for col in ["CMTRT", "MEDNAME", "MEDICATION", "DRUG", "TRT"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMTRT"] = str(row[col])
                    break

            # Coded term (would use WHODrug in production)
            cm_record["CMDECOD"] = cm_record.get("CMTRT", "")

            # Dose
            for col in ["CMDOSE", "DOSE"]:
                if col in row and pd.notna(row[col]):
                    try:
                        cm_record["CMDOSE"] = float(row[col])
                    except (ValueError, TypeError):
                        cm_record["CMDOSTXT"] = str(row[col])
                    break

            # Dose unit
            for col in ["CMDOSU", "DOSEUNIT", "UNIT"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMDOSU"] = str(row[col])
                    break

            # Route
            for col in ["CMROUTE", "ROUTE"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMROUTE"] = str(row[col]).upper()
                    break

            # Frequency
            for col in ["CMDOSFRQ", "FREQ", "FREQUENCY"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMDOSFRQ"] = str(row[col]).upper()
                    break

            # Dates
            for src, tgt in [("CMSTDT", "CMSTDTC"), ("CMENDT", "CMENDTC"),
                             ("STDT", "CMSTDTC"), ("ENDT", "CMENDTC")]:
                if src in row and pd.notna(row[src]):
                    cm_record[tgt] = self._convert_date_to_iso(row[src])

            # Indication
            for col in ["CMINDC", "INDICATION", "INDC"]:
                if col in row and pd.notna(row[col]):
                    cm_record["CMINDC"] = str(row[col])
                    break

            cm_records.append(cm_record)

        result_df = pd.DataFrame(cm_records)

        # Reorder columns
        cm_cols = ["STUDYID", "DOMAIN", "USUBJID", "CMSEQ", "CMTRT", "CMDECOD",
                   "CMDOSE", "CMDOSTXT", "CMDOSU", "CMDOSFRQ", "CMROUTE",
                   "CMSTDTC", "CMENDTC", "CMINDC"]
        existing_cols = [c for c in cm_cols if c in result_df.columns]
        if existing_cols:
            result_df = result_df[existing_cols]

        self.log(f"Created {len(result_df)} CM records")
        return result_df


class EXTransformer(BaseDomainTransformer):
    """Exposure domain transformer."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "EX"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform exposure/dosing data to SDTM EX domain."""
        self.log("Transforming to EX domain")

        ex_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", ""))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            ex_record = {
                "STUDYID": row.get("STUDY", self.study_id),
                "DOMAIN": "EX",
                "USUBJID": self._generate_usubjid(row),
                "EXSEQ": subject_seq[subj],
            }

            # Treatment
            for col in ["EXTRT", "TRT", "TREATMENT", "DRUG"]:
                if col in row and pd.notna(row[col]):
                    ex_record["EXTRT"] = str(row[col])
                    break

            # Dose
            for col in ["EXDOSE", "DOSE", "DOSENUM"]:
                if col in row and pd.notna(row[col]):
                    try:
                        ex_record["EXDOSE"] = float(row[col])
                    except (ValueError, TypeError):
                        ex_record["EXDOSTXT"] = str(row[col])
                    break

            # Dose unit
            for col in ["EXDOSU", "DOSEUNIT", "UNIT"]:
                if col in row and pd.notna(row[col]):
                    ex_record["EXDOSU"] = str(row[col])
                    break

            # Route
            for col in ["EXROUTE", "ROUTE"]:
                if col in row and pd.notna(row[col]):
                    ex_record["EXROUTE"] = str(row[col]).upper()
                    break

            # Dates
            for src, tgt in [("EXSTDT", "EXSTDTC"), ("EXENDT", "EXENDTC"),
                             ("STDT", "EXSTDTC"), ("ENDT", "EXENDTC")]:
                if src in row and pd.notna(row[src]):
                    ex_record[tgt] = self._convert_date_to_iso(row[src])

            ex_records.append(ex_record)

        result_df = pd.DataFrame(ex_records)
        self.log(f"Created {len(result_df)} EX records")
        return result_df


class DSTransformer(BaseDomainTransformer):
    """Disposition domain transformer."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "DS"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform disposition data to SDTM DS domain."""
        self.log("Transforming to DS domain")

        ds_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", ""))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            ds_record = {
                "STUDYID": row.get("STUDY", self.study_id),
                "DOMAIN": "DS",
                "USUBJID": self._generate_usubjid(row),
                "DSSEQ": subject_seq[subj],
            }

            # Disposition term
            for col in ["DSTERM", "TERM", "STATUS", "DISPOSITION"]:
                if col in row and pd.notna(row[col]):
                    ds_record["DSTERM"] = str(row[col])
                    ds_record["DSDECOD"] = str(row[col]).upper()
                    break

            # Category
            ds_record["DSCAT"] = "DISPOSITION EVENT"

            # Date
            for col in ["DSSTDT", "DSDT", "DATE", "DSDTC"]:
                if col in row and pd.notna(row[col]):
                    ds_record["DSSTDTC"] = self._convert_date_to_iso(row[col])
                    break

            ds_records.append(ds_record)

        result_df = pd.DataFrame(ds_records)
        self.log(f"Created {len(result_df)} DS records")
        return result_df


class MHTransformer(BaseDomainTransformer):
    """Medical History domain transformer."""

    def __init__(self, study_id: str, mapping_spec: Optional[MappingSpecification] = None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "MH"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform medical history data to SDTM MH domain."""
        self.log("Transforming to MH domain")

        mh_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", ""))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            mh_record = {
                "STUDYID": row.get("STUDY", self.study_id),
                "DOMAIN": "MH",
                "USUBJID": self._generate_usubjid(row),
                "MHSEQ": subject_seq[subj],
            }

            # Medical history term
            for col in ["MHTERM", "TERM", "CONDITION", "DIAGNOSIS", "DISEASE"]:
                if col in row and pd.notna(row[col]):
                    mh_record["MHTERM"] = str(row[col])
                    mh_record["MHDECOD"] = str(row[col])
                    break

            # Category
            for col in ["MHCAT", "CAT", "CATEGORY"]:
                if col in row and pd.notna(row[col]):
                    mh_record["MHCAT"] = str(row[col])
                    break

            # Dates
            for src, tgt in [("MHSTDT", "MHSTDTC"), ("MHENDT", "MHENDTC"),
                             ("STDT", "MHSTDTC"), ("ENDT", "MHENDTC")]:
                if src in row and pd.notna(row[src]):
                    mh_record[tgt] = self._convert_date_to_iso(row[src])

            # Ongoing
            if "MHONGO" in row:
                mh_record["MHENRF"] = "ONGOING" if str(row["MHONGO"]).upper() in ["Y", "YES"] else ""

            mh_records.append(mh_record)

        result_df = pd.DataFrame(mh_records)
        self.log(f"Created {len(result_df)} MH records")
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
                   mapping_spec: Optional[MappingSpecification] = None) -> BaseDomainTransformer:
    """Factory function to get appropriate transformer for domain."""
    transformers = {
        # Core domains
        "DM": DMTransformer,
        "AE": AETransformer,
        "VS": VSTransformer,
        "LB": LBTransformer,
        "CM": CMTransformer,
        "EX": EXTransformer,
        "DS": DSTransformer,
        "MH": MHTransformer,
        "EG": EGTransformer,
        "PE": PETransformer,
        "PC": PCTransformer,
        "IE": IETransformer,
        "CO": COTransformer,
        "QS": QSTransformer,
        "RS": RSTransformer,
        "TR": TRTransformer,
        "TU": TUTransformer,
        # Trial design
        "TA": TATransformer,
    }

    transformer_class = transformers.get(domain_code)
    if transformer_class:
        return transformer_class(study_id, mapping_spec)

    # Handle supplemental qualifiers
    if domain_code.startswith("SUPP"):
        parent_domain = domain_code[4:]  # Extract parent domain (e.g., "AE" from "SUPPAE")
        return GenericSUPPTransformer(study_id, parent_domain, mapping_spec)

    # For unsupported domains, use a generic transformer that passes through data
    raise ValueError(f"No transformer available for domain: {domain_code}")

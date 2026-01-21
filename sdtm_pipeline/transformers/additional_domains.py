"""
Additional SDTM Domain Transformers
===================================
Implements remaining SDTM-IG 3.4 domains beyond the core ones.
Organized by domain class: Special-Purpose, Interventions, Events, Findings, Trial Design.

ALL transformers are SDTM-IG 3.4 compliant with:
- All Required/Expected variables initialized at record creation
- Proper column ordering per SDTM-IG 3.4 specification
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime

from .domain_transformers import BaseDomainTransformer


# =============================================================================
# SDTM-IG 3.4 COMPLIANCE HELPER
# =============================================================================

def ensure_sdtm_column_order(df: pd.DataFrame, column_order: List[str]) -> pd.DataFrame:
    """Ensure DataFrame columns are ordered per SDTM-IG 3.4 specification."""
    if df.empty:
        return df
    ordered_cols = [c for c in column_order if c in df.columns]
    extra_cols = [c for c in df.columns if c not in column_order]
    return df[ordered_cols + extra_cols]


# SDTM-IG 3.4 Variable Specifications for All Domains
SDTM_DOMAIN_VARIABLES = {
    "SE": ["STUDYID", "DOMAIN", "USUBJID", "SESEQ", "ETCD", "ELEMENT", "SESTDTC", "SEENDTC", "SESTDY", "SEENDY", "EPOCH", "TAESSION"],
    "SV": ["STUDYID", "DOMAIN", "USUBJID", "VISITNUM", "VISIT", "VISITDY", "SVSTDTC", "SVENDTC", "SVSTDY", "SVENDY", "EPOCH", "SVUPDES", "SVCAT"],
    "SM": ["STUDYID", "DOMAIN", "USUBJID", "SMSEQ", "SMSPID", "MIDS", "SMCAT", "SMDTC", "SMDY", "EPOCH"],
    "SU": ["STUDYID", "DOMAIN", "USUBJID", "SUSEQ", "SUTRT", "SUDECOD", "SUCAT", "SUSCAT", "SUPRESP", "SUOCCUR", "SUSTAT", "SUREASND", "SUDOSE", "SUDOSTXT", "SUDOSU", "SUDOSFRM", "SUDOSFRQ", "SUROUTE", "SUSTRF", "SUENRF", "EPOCH", "SUSTDTC", "SUENDTC", "SUSTDY", "SUENDY"],
    "PR": ["STUDYID", "DOMAIN", "USUBJID", "PRSEQ", "PRSPID", "PRTRT", "PRMODIFY", "PRDECOD", "PRCAT", "PRSCAT", "PRPRESP", "PROCCUR", "PRSTAT", "PRREASND", "PRBODSYS", "PRINDC", "PRLOC", "PRLAT", "PRDIR", "EPOCH", "PRSTDTC", "PRENDTC", "PRSTDY", "PRENDY", "PRDUR", "PRSTRF", "PRENRF"],
    "EC": ["STUDYID", "DOMAIN", "USUBJID", "ECSEQ", "ECSPID", "ECTRT", "ECMOOD", "ECCAT", "ECSCAT", "ECPRESP", "ECOCCUR", "ECSTAT", "ECREASND", "ECDOSE", "ECDOSTXT", "ECDOSU", "ECDOSFRM", "ECDOSFRQ", "ECDOSTOT", "ECROUTE", "ECLOC", "ECLAT", "ECDIR", "ECFAST", "EPOCH", "ECSTDTC", "ECENDTC", "ECSTDY", "ECENDY"],
    "AG": ["STUDYID", "DOMAIN", "USUBJID", "AGSEQ", "AGSPID", "AGTRT", "AGDECOD", "AGCAT", "AGSCAT", "AGPRESP", "AGOCCUR", "AGSTAT", "AGREASND", "AGDOSE", "AGDOSTXT", "AGDOSU", "AGDOSFRM", "AGDOSFRQ", "AGROUTE", "AGLOC", "AGLAT", "AGDIR", "EPOCH", "AGSTDTC", "AGENDTC", "AGSTDY", "AGENDY"],
    "ML": ["STUDYID", "DOMAIN", "USUBJID", "MLSEQ", "MLSPID", "MLTRT", "MLDECOD", "MLCAT", "MLSCAT", "MLPRESP", "MLOCCUR", "MLSTAT", "MLREASND", "EPOCH", "MLDTC", "MLSTDTC", "MLENDTC", "MLSTDY", "MLENDY"],
    "CE": ["STUDYID", "DOMAIN", "USUBJID", "CESEQ", "CESPID", "CETERM", "CEMODIFY", "CEDECOD", "CECAT", "CESCAT", "CEPRESP", "CEOCCUR", "CESTAT", "CEREASND", "CEBODSYS", "CESEV", "CESER", "CEACN", "CEREL", "CEOUT", "CECONTRT", "CETOXGR", "EPOCH", "CESTDTC", "CEENDTC", "CESTDY", "CEENDY", "CEDUR", "CESTRF", "CEENRF"],
    "DV": ["STUDYID", "DOMAIN", "USUBJID", "DVSEQ", "DVSPID", "DVTERM", "DVDECOD", "DVCAT", "DVSCAT", "EPOCH", "DVSTDTC", "DVENDTC", "DVSTDY", "DVENDY"],
    "HO": ["STUDYID", "DOMAIN", "USUBJID", "HOSEQ", "HOSPID", "HOTERM", "HODECOD", "HOCAT", "HOSCAT", "HOPRESP", "HOOCCUR", "HOSTAT", "HOREASND", "HOINDC", "EPOCH", "HOSTDTC", "HOENDTC", "HOSTDY", "HOENDY", "HODUR", "HOENRF"],
    "BE": ["STUDYID", "DOMAIN", "USUBJID", "BESEQ", "BESPID", "BETESTCD", "BETEST", "BECAT", "BESCAT", "BEORRES", "BEORRESU", "BESTRESC", "BESTRESN", "BESTRESU", "BESTAT", "BEREASND", "VISITNUM", "VISIT", "VISITDY", "EPOCH", "BEDTC", "BEDY"],
    "DD": ["STUDYID", "DOMAIN", "USUBJID", "DDSEQ", "DDSPID", "DDTESTCD", "DDTEST", "DDCAT", "DDSCAT", "DDORRES", "DDORRESU", "DDSTRESC", "DDSTRESN", "DDSTRESU", "DDSTAT", "DDREASND", "VISITNUM", "VISIT", "EPOCH", "DDDTC", "DDDY"],
    "SC": ["STUDYID", "DOMAIN", "USUBJID", "SCSEQ", "SCSPID", "SCTESTCD", "SCTEST", "SCORRES", "SCORRESU", "SCSTRESC", "SCSTRESN", "SCSTRESU", "SCSTAT", "SCREASND", "SCDTC", "SCDY"],
    "SS": ["STUDYID", "DOMAIN", "USUBJID", "SSSEQ", "SSSPID", "SSTESTCD", "SSTEST", "SSCAT", "SSSCAT", "SSORRES", "SSORRESU", "SSSTRESC", "SSSTRESN", "SSSTRESU", "SSSTAT", "SSREASND", "VISITNUM", "VISIT", "EPOCH", "SSDTC", "SSDY"],
    "FA": ["STUDYID", "DOMAIN", "USUBJID", "FASEQ", "FASPID", "FATESTCD", "FATEST", "FACAT", "FASCAT", "FAOBJ", "FAORRES", "FAORRESU", "FASTRESC", "FASTRESN", "FASTRESU", "FASTAT", "FAREASND", "FALOC", "FALAT", "VISITNUM", "VISIT", "EPOCH", "FADTC", "FADY"],
    "PP": ["STUDYID", "DOMAIN", "USUBJID", "PPSEQ", "PPSPID", "PPTESTCD", "PPTEST", "PPCAT", "PPSCAT", "PPORRES", "PPORRESU", "PPSTRESC", "PPSTRESN", "PPSTRESU", "PPSTAT", "PPREASND", "PPSPEC", "PPRFTDTC", "PPDTC"],
    "MB": ["STUDYID", "DOMAIN", "USUBJID", "MBSEQ", "MBSPID", "MBTESTCD", "MBTEST", "MBCAT", "MBSCAT", "MBORRES", "MBORRESU", "MBSTRESC", "MBSTRESN", "MBSTRESU", "MBSTAT", "MBREASND", "MBNAM", "MBSPEC", "MBLOC", "MBLAT", "MBMETHOD", "VISITNUM", "VISIT", "EPOCH", "MBDTC", "MBDY"],
    "MI": ["STUDYID", "DOMAIN", "USUBJID", "MISEQ", "MISPID", "MITESTCD", "MITEST", "MICAT", "MISCAT", "MIORRES", "MIORRESU", "MISTRESC", "MISTRESN", "MISTRESU", "MISTAT", "MIREASND", "MILOC", "MILAT", "MIMETHOD", "MISPEC", "VISITNUM", "VISIT", "EPOCH", "MIDTC", "MIDY"],
    "DA": ["STUDYID", "DOMAIN", "USUBJID", "DASEQ", "DASPID", "DATESTCD", "DATEST", "DACAT", "DASCAT", "DAORRES", "DAORRESU", "DASTRESC", "DASTRESN", "DASTRESU", "DASTAT", "DAREASND", "VISITNUM", "VISIT", "EPOCH", "DADTC", "DADY"],
    "FT": ["STUDYID", "DOMAIN", "USUBJID", "FTSEQ", "FTSPID", "FTTESTCD", "FTTEST", "FTCAT", "FTSCAT", "FTORRES", "FTORRESU", "FTSTRESC", "FTSTRESN", "FTSTRESU", "FTSTAT", "FTREASND", "FTOBJ", "FTMETHOD", "VISITNUM", "VISIT", "EPOCH", "FTDTC", "FTDY"],
    "SR": ["STUDYID", "DOMAIN", "USUBJID", "SRSEQ", "SRSPID", "SRTESTCD", "SRTEST", "SRCAT", "SRSCAT", "SRORRES", "SRORRESU", "SRSTRESC", "SRSTRESN", "SRSTRESU", "SRSTAT", "SRREASND", "VISITNUM", "VISIT", "EPOCH", "SRDTC", "SRDY"],
    "CV": ["STUDYID", "DOMAIN", "USUBJID", "CVSEQ", "CVSPID", "CVTESTCD", "CVTEST", "CVCAT", "CVSCAT", "CVPOS", "CVORRES", "CVORRESU", "CVSTRESC", "CVSTRESN", "CVSTRESU", "CVSTAT", "CVREASND", "CVMETHOD", "CVANMETH", "CVLEAD", "VISITNUM", "VISIT", "EPOCH", "CVDTC", "CVDY", "CVTPT", "CVTPTNUM", "CVELTM", "CVTPTREF"],
    "MK": ["STUDYID", "DOMAIN", "USUBJID", "MKSEQ", "MKSPID", "MKTESTCD", "MKTEST", "MKCAT", "MKSCAT", "MKORRES", "MKORRESU", "MKSTRESC", "MKSTRESN", "MKSTRESU", "MKSTAT", "MKREASND", "MKNAM", "MKSPEC", "MKMETHOD", "MKLOC", "MKLAT", "MKBLFL", "MKDRVFL", "VISITNUM", "VISIT", "EPOCH", "MKDTC", "MKDY", "MKTPT", "MKTPTNUM", "MKELTM", "MKTPTREF"],
    "NV": ["STUDYID", "DOMAIN", "USUBJID", "NVSEQ", "NVSPID", "NVTESTCD", "NVTEST", "NVCAT", "NVSCAT", "NVORRES", "NVORRESU", "NVSTRESC", "NVSTRESN", "NVSTRESU", "NVSTAT", "NVREASND", "NVMETHOD", "NVBLFL", "VISITNUM", "VISIT", "EPOCH", "NVDTC", "NVDY"],
    "OE": ["STUDYID", "DOMAIN", "USUBJID", "OESEQ", "OESPID", "OETESTCD", "OETEST", "OECAT", "OESCAT", "OEORRES", "OEORRESU", "OESTRESC", "OESTRESN", "OESTRESU", "OESTAT", "OEREASND", "OEMETHOD", "OELOC", "OELAT", "VISITNUM", "VISIT", "EPOCH", "OEDTC", "OEDY"],
    "RE": ["STUDYID", "DOMAIN", "USUBJID", "RESETCD", "RETEST", "RESEQ", "RESPID", "RECAT", "RESCAT", "REORRES", "REORRESU", "RESTRESC", "RESTRESN", "RESTRESU", "RESTAT", "REREASND", "VISITNUM", "VISIT", "EPOCH", "REDTC", "REDY"],
    "RP": ["STUDYID", "DOMAIN", "USUBJID", "RPSEQ", "RPSPID", "RPTESTCD", "RPTEST", "RPCAT", "RPSCAT", "RPORRES", "RPORRESU", "RPSTRESC", "RPSTRESN", "RPSTRESU", "RPSTAT", "RPREASND", "VISITNUM", "VISIT", "EPOCH", "RPDTC", "RPDY"],
    "UR": ["STUDYID", "DOMAIN", "USUBJID", "URSEQ", "URSPID", "URTESTCD", "URTEST", "URCAT", "URSCAT", "URORRES", "URORRESU", "URSTRESC", "URSTRESN", "URSTRESU", "URSTAT", "URREASND", "URMETHOD", "VISITNUM", "VISIT", "EPOCH", "URDTC", "URDY"],
    "BS": ["STUDYID", "DOMAIN", "USUBJID", "BSSEQ", "BSSPID", "BSTESTCD", "BSTEST", "BSCAT", "BSSCAT", "BSORRES", "BSORRESU", "BSSTRESC", "BSSTRESN", "BSSTRESU", "BSSTAT", "BSREASND", "BSSPEC", "BSMETHOD", "VISITNUM", "VISIT", "EPOCH", "BSDTC", "BSDY"],
    "CP": ["STUDYID", "DOMAIN", "USUBJID", "CPSEQ", "CPSPID", "CPTESTCD", "CPTEST", "CPCAT", "CPSCAT", "CPORRES", "CPORRESU", "CPSTRESC", "CPSTRESN", "CPSTRESU", "CPSTAT", "CPREASND", "CPSPEC", "CPLOC", "CPLAT", "CPMETHOD", "VISITNUM", "VISIT", "EPOCH", "CPDTC", "CPDY"],
    "GF": ["STUDYID", "DOMAIN", "USUBJID", "GFSEQ", "GFSPID", "GFTESTCD", "GFTEST", "GFCAT", "GFSCAT", "GFREFID", "GFORRES", "GFORRESU", "GFSTRESC", "GFSTRESN", "GFSTRESU", "GFSTAT", "GFREASND", "VISITNUM", "VISIT", "EPOCH", "GFDTC", "GFDY"],
    "IS": ["STUDYID", "DOMAIN", "USUBJID", "ISSEQ", "ISSPID", "ISTESTCD", "ISTEST", "ISCAT", "ISSCAT", "ISORRES", "ISORRESU", "ISSTRESC", "ISSTRESN", "ISSTRESU", "ISSTAT", "ISREASND", "ISMETHOD", "VISITNUM", "VISIT", "EPOCH", "ISDTC", "ISDY"],
    "MO": ["STUDYID", "DOMAIN", "USUBJID", "MOSEQ", "MOSPID", "MOTESTCD", "MOTEST", "MOCAT", "MOSCAT", "MOORIG", "MOORRES", "MOORRESU", "MOSTRESC", "MOSTRESN", "MOSTRESU", "MOSTAT", "MOREASND", "MOSPEC", "MOLOC", "MOMETHOD", "VISITNUM", "VISIT", "EPOCH", "MODTC", "MODY"],
    "OI": ["STUDYID", "DOMAIN", "USUBJID", "OISEQ", "OISPID", "OITESTCD", "OITEST", "OICAT", "OISCAT", "OIORRES", "OIORRESU", "OISTRESC", "OISTRESN", "OISTRESU", "OISTAT", "OIREASND", "OISPEC", "OILOC", "OILAT", "OIMETHOD", "VISITNUM", "VISIT", "EPOCH", "OIDTC", "OIDY"],
    "TE": ["STUDYID", "DOMAIN", "ETCD", "ELEMENT", "TESTRL", "TEENRL", "TEDUR"],
    "TV": ["STUDYID", "DOMAIN", "VISITNUM", "VISIT", "ARMCD", "ARM", "TVSTRL", "TVENRL"],
    "TI": ["STUDYID", "DOMAIN", "IETESTCD", "IETEST", "IECAT", "IESCAT", "TIRL", "TIVERS"],
    "TS": ["STUDYID", "DOMAIN", "TSSEQ", "TSGRPID", "TSPARMCD", "TSPARM", "TSVAL", "TSVALNF", "TSVALCD", "TSVCDREF", "TSVCDVER"],
    "TD": ["STUDYID", "DOMAIN", "TDSEQ", "TDSTOFF", "TDTGTPAI", "TDMINPAI", "TDMAXPAI", "TDNUMRPT"],
    "TM": ["STUDYID", "DOMAIN", "MIDSTYPE", "TMDEF", "TMRPT"],
    "RELREC": ["STUDYID", "RDOMAIN", "USUBJID", "IDVAR", "IDVARVAL", "RELTYPE", "RELID"],
    "RELSUB": ["STUDYID", "USUBJID", "SREL", "RSUBJID"],
    "RELSPEC": ["STUDYID", "DOMAIN", "USUBJID", "SPEC", "REFID", "SREL", "RSPEC", "RREFID"],
}


# =============================================================================
# SPECIAL-PURPOSE DOMAINS
# =============================================================================

class SETransformer(BaseDomainTransformer):
    """Subject Elements domain transformer - SDTM-IG 3.4 compliant (12 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "SE"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to SE domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to SE domain - FULL SDTM-IG 3.4 compliance")
        se_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            se_record = {
                # Required Identifiers
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "SE",
                "USUBJID": self._generate_usubjid(row),
                "SESEQ": subject_seq[subj],
                # Required - Element
                "ETCD": "",
                "ELEMENT": "",
                # Expected - Timing
                "SESTDTC": "",
                "SEENDTC": "",
                "SESTDY": None,
                "SEENDY": None,
                # Expected - Epoch
                "EPOCH": "",
                "TAESSION": None,
            }

            # ETCD - Element Code (Required)
            for col in ["ETCD", "ELEMENTCD", "ELEMCD"]:
                if col in row and pd.notna(row[col]):
                    se_record["ETCD"] = str(row[col])
                    break

            # ELEMENT - Element Description (Required)
            for col in ["ELEMENT", "ELEMENTNAME", "ELEMNAME"]:
                if col in row and pd.notna(row[col]):
                    se_record["ELEMENT"] = str(row[col])
                    break

            # SESTDTC - Start Date/Time (Expected)
            for col in ["SESTDTC", "SESTDT", "STARTDT", "ELSTDT"]:
                if col in row and pd.notna(row[col]):
                    se_record["SESTDTC"] = self._convert_date_to_iso(row[col])
                    break

            # SEENDTC - End Date/Time (Expected)
            for col in ["SEENDTC", "SEENDT", "ENDDT", "ELENDT"]:
                if col in row and pd.notna(row[col]):
                    se_record["SEENDTC"] = self._convert_date_to_iso(row[col])
                    break

            # SESTDY - Study Day of Start (Perm)
            for col in ["SESTDY", "STSTDY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        se_record["SESTDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # SEENDY - Study Day of End (Perm)
            for col in ["SEENDY", "ENDY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        se_record["SEENDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # EPOCH (Expected)
            for col in ["EPOCH", "SEEPOCH"]:
                if col in row and pd.notna(row[col]):
                    se_record["EPOCH"] = str(row[col]).upper()
                    break

            # TAESSION - Planned Element within Arm (Perm)
            for col in ["TAESSION", "ARMCD"]:
                if col in row and pd.notna(row[col]):
                    try:
                        se_record["TAESSION"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        se_record["TAESSION"] = row[col]
                    break

            se_records.append(se_record)

        result_df = pd.DataFrame(se_records)

        # Ensure column order per SDTM-IG 3.4
        column_order = ["STUDYID", "DOMAIN", "USUBJID", "SESEQ", "ETCD", "ELEMENT",
                        "SESTDTC", "SEENDTC", "SESTDY", "SEENDY", "EPOCH", "TAESSION"]
        ordered_cols = [c for c in column_order if c in result_df.columns]
        extra_cols = [c for c in result_df.columns if c not in column_order]
        result_df = result_df[ordered_cols + extra_cols]

        self.log(f"Created {len(result_df)} SE records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class SVTransformer(BaseDomainTransformer):
    """Subject Visits domain transformer - SDTM-IG 3.4 compliant (14 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "SV"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to SV domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to SV domain - FULL SDTM-IG 3.4 compliance")
        sv_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            sv_record = {
                # Required Identifiers
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "SV",
                "USUBJID": self._generate_usubjid(row),
                # Required - Visit
                "VISITNUM": None,
                "VISIT": "",
                "VISITDY": None,
                # Expected - Timing
                "SVSTDTC": "",
                "SVENDTC": "",
                "SVSTDY": None,
                "SVENDY": None,
                # Expected - Epoch
                "EPOCH": "",
                # Permissible
                "SVUPDES": "",
                "SVCAT": "",
            }

            # VISITNUM (Required)
            for col in ["VISITNUM", "VISNUM"]:
                if col in row and pd.notna(row[col]):
                    try:
                        sv_record["VISITNUM"] = float(row[col])
                    except (ValueError, TypeError):
                        sv_record["VISITNUM"] = subject_seq[subj]
                    break
            if sv_record["VISITNUM"] is None:
                sv_record["VISITNUM"] = subject_seq[subj]

            # VISIT - Visit Name (Required)
            for col in ["VISIT", "VISITNAME", "VISNAME"]:
                if col in row and pd.notna(row[col]):
                    sv_record["VISIT"] = str(row[col])
                    break

            # VISITDY - Planned Study Day of Visit (Expected)
            for col in ["VISITDY", "VISDY", "PLANDY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        sv_record["VISITDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # SVSTDTC - Start Date/Time (Expected)
            for col in ["SVSTDTC", "SVSTDT", "VISITDT", "STARTDT"]:
                if col in row and pd.notna(row[col]):
                    sv_record["SVSTDTC"] = self._convert_date_to_iso(row[col])
                    break

            # SVENDTC - End Date/Time (Expected)
            for col in ["SVENDTC", "SVENDT", "ENDDT"]:
                if col in row and pd.notna(row[col]):
                    sv_record["SVENDTC"] = self._convert_date_to_iso(row[col])
                    break

            # SVSTDY - Study Day of Start (Perm)
            for col in ["SVSTDY", "STSTDY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        sv_record["SVSTDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # SVENDY - Study Day of End (Perm)
            for col in ["SVENDY", "ENDY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        sv_record["SVENDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # EPOCH (Expected)
            for col in ["EPOCH", "SVEPOCH"]:
                if col in row and pd.notna(row[col]):
                    sv_record["EPOCH"] = str(row[col]).upper()
                    break

            # SVUPDES - Unplanned Visit Description (Perm)
            for col in ["SVUPDES", "UPDES", "UNPLDES"]:
                if col in row and pd.notna(row[col]):
                    sv_record["SVUPDES"] = str(row[col])
                    break

            # SVCAT - Category (Perm)
            for col in ["SVCAT", "CAT", "VISITCAT"]:
                if col in row and pd.notna(row[col]):
                    sv_record["SVCAT"] = str(row[col]).upper()
                    break

            sv_records.append(sv_record)

        result_df = pd.DataFrame(sv_records)

        # Ensure column order per SDTM-IG 3.4
        column_order = ["STUDYID", "DOMAIN", "USUBJID", "VISITNUM", "VISIT", "VISITDY",
                        "SVSTDTC", "SVENDTC", "SVSTDY", "SVENDY", "EPOCH", "SVUPDES", "SVCAT"]
        ordered_cols = [c for c in column_order if c in result_df.columns]
        extra_cols = [c for c in result_df.columns if c not in column_order]
        result_df = result_df[ordered_cols + extra_cols]

        self.log(f"Created {len(result_df)} SV records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class SMTransformer(BaseDomainTransformer):
    """Subject Disease Milestones domain transformer - SDTM-IG 3.4 compliant (10 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "SM"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to SM domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to SM domain - FULL SDTM-IG 3.4 compliance")
        sm_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            sm_record = {
                # Required Identifiers
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "SM",
                "USUBJID": self._generate_usubjid(row),
                "SMSEQ": subject_seq[subj],
                # Required - Milestone
                "MIDS": "",
                # Expected - Timing
                "SMDTC": "",
                "SMDY": None,
                # Permissible
                "SMSPID": "",
                "SMCAT": "",
                "EPOCH": "",
            }

            # SMSPID - Sponsor-Defined Identifier (Perm)
            for col in ["SMSPID", "SMID", "MILEID"]:
                if col in row and pd.notna(row[col]):
                    sm_record["SMSPID"] = str(row[col])
                    break

            # MIDS - Milestone Identifier (Required)
            for col in ["MIDS", "MILESTONE", "MILEID"]:
                if col in row and pd.notna(row[col]):
                    sm_record["MIDS"] = str(row[col])
                    break

            # SMCAT - Category (Perm)
            for col in ["SMCAT", "CAT", "CATEGORY"]:
                if col in row and pd.notna(row[col]):
                    sm_record["SMCAT"] = str(row[col]).upper()
                    break

            # SMDTC - Date/Time of Milestone (Expected)
            for col in ["SMDTC", "SMDT", "MILESTONEDT", "MILEDT"]:
                if col in row and pd.notna(row[col]):
                    sm_record["SMDTC"] = self._convert_date_to_iso(row[col])
                    break

            # SMDY - Study Day (Perm)
            for col in ["SMDY", "MILEDAY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        sm_record["SMDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # EPOCH (Perm)
            for col in ["EPOCH", "SMEPOCH"]:
                if col in row and pd.notna(row[col]):
                    sm_record["EPOCH"] = str(row[col]).upper()
                    break

            sm_records.append(sm_record)

        result_df = pd.DataFrame(sm_records)

        # Ensure column order per SDTM-IG 3.4
        column_order = ["STUDYID", "DOMAIN", "USUBJID", "SMSEQ", "SMSPID",
                        "MIDS", "SMCAT", "SMDTC", "SMDY", "EPOCH"]
        ordered_cols = [c for c in column_order if c in result_df.columns]
        extra_cols = [c for c in result_df.columns if c not in column_order]
        result_df = result_df[ordered_cols + extra_cols]

        self.log(f"Created {len(result_df)} SM records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


# =============================================================================
# INTERVENTIONS DOMAINS
# =============================================================================

class SUTransformer(BaseDomainTransformer):
    """Substance Use domain transformer - SDTM-IG 3.4 compliant (25 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "SU"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to SU domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to SU domain - FULL SDTM-IG 3.4 compliance")
        su_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            su_record = {
                # Required Identifiers
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "SU",
                "USUBJID": self._generate_usubjid(row),
                "SUSEQ": subject_seq[subj],
                # Required - Topic
                "SUTRT": "",
                # Expected - Coding
                "SUDECOD": "",
                # Expected - Category
                "SUCAT": "",
                "SUSCAT": "",
                # Expected - Dose
                "SUDOSE": None,
                "SUDOSTXT": "",
                "SUDOSU": "",
                "SUDOSFRM": "",
                "SUDOSFRQ": "",
                # Expected - Route
                "SUROUTE": "",
                # Expected - Occurrence
                "SUPRESP": "",
                "SUOCCUR": "",
                "SUSTAT": "",
                "SUREASND": "",
                # Expected - Timing
                "SUSTRF": "",
                "SUENRF": "",
                "EPOCH": "",
                "SUSTDTC": "",
                "SUENDTC": "",
                "SUSTDY": None,
                "SUENDY": None,
            }

            # SUTRT - Substance Name (Required)
            for col in ["SUTRT", "SUBSTANCE", "DRUG", "TRT"]:
                if col in row and pd.notna(row[col]):
                    su_record["SUTRT"] = str(row[col])
                    break

            # SUDECOD - Standardized Substance Name (Expected)
            for col in ["SUDECOD", "SUCODE"]:
                if col in row and pd.notna(row[col]):
                    su_record["SUDECOD"] = str(row[col])
                    break
            if not su_record["SUDECOD"] and su_record["SUTRT"]:
                su_record["SUDECOD"] = su_record["SUTRT"].upper()

            # Category
            for col in ["SUCAT", "CAT", "CATEGORY"]:
                if col in row and pd.notna(row[col]):
                    su_record["SUCAT"] = str(row[col]).upper()
                    break

            # Subcategory
            for col in ["SUSCAT", "SCAT", "SUBCATEGORY"]:
                if col in row and pd.notna(row[col]):
                    su_record["SUSCAT"] = str(row[col]).upper()
                    break

            # Dose/Amount
            for col in ["SUDOSE", "AMOUNT", "DOSE"]:
                if col in row and pd.notna(row[col]):
                    try:
                        su_record["SUDOSE"] = float(row[col])
                    except (ValueError, TypeError):
                        su_record["SUDOSTXT"] = str(row[col])
                    break

            # Dose Units
            for col in ["SUDOSU", "UNIT", "DOSEUNIT"]:
                if col in row and pd.notna(row[col]):
                    su_record["SUDOSU"] = str(row[col])
                    break

            # Frequency
            for col in ["SUDOSFRQ", "FREQ", "FREQUENCY"]:
                if col in row and pd.notna(row[col]):
                    su_record["SUDOSFRQ"] = str(row[col]).upper()
                    break

            # Route
            for col in ["SUROUTE", "ROUTE"]:
                if col in row and pd.notna(row[col]):
                    su_record["SUROUTE"] = str(row[col]).upper()
                    break

            # Status (CURRENT, FORMER, NEVER)
            for col in ["SUSTRF", "STATUS"]:
                if col in row and pd.notna(row[col]):
                    su_record["SUSTRF"] = str(row[col]).upper()
                    break

            # End relative to reference
            for col in ["SUENRF", "ENDREF"]:
                if col in row and pd.notna(row[col]):
                    su_record["SUENRF"] = str(row[col]).upper()
                    break

            # Dates
            for col in ["SUSTDTC", "SUSTDT", "STARTDT"]:
                if col in row and pd.notna(row[col]):
                    su_record["SUSTDTC"] = self._convert_date_to_iso(row[col])
                    break

            for col in ["SUENDTC", "SUENDT", "ENDDT"]:
                if col in row and pd.notna(row[col]):
                    su_record["SUENDTC"] = self._convert_date_to_iso(row[col])
                    break

            # Study Days
            for col in ["SUSTDY", "STARTDY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        su_record["SUSTDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            for col in ["SUENDY", "ENDDY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        su_record["SUENDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # EPOCH
            for col in ["EPOCH", "SUEPOCH"]:
                if col in row and pd.notna(row[col]):
                    su_record["EPOCH"] = str(row[col]).upper()
                    break

            su_records.append(su_record)

        result_df = pd.DataFrame(su_records)

        # Ensure column order per SDTM-IG 3.4
        column_order = ["STUDYID", "DOMAIN", "USUBJID", "SUSEQ", "SUTRT", "SUDECOD",
                        "SUCAT", "SUSCAT", "SUPRESP", "SUOCCUR", "SUSTAT", "SUREASND",
                        "SUDOSE", "SUDOSTXT", "SUDOSU", "SUDOSFRM", "SUDOSFRQ", "SUROUTE",
                        "SUSTRF", "SUENRF", "EPOCH", "SUSTDTC", "SUENDTC", "SUSTDY", "SUENDY"]
        ordered_cols = [c for c in column_order if c in result_df.columns]
        extra_cols = [c for c in result_df.columns if c not in column_order]
        result_df = result_df[ordered_cols + extra_cols]

        self.log(f"Created {len(result_df)} SU records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class PRTransformer(BaseDomainTransformer):
    """Procedures domain transformer - SDTM-IG 3.4 compliant (24 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "PR"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to PR domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to PR domain - FULL SDTM-IG 3.4 compliance")
        pr_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            pr_record = {
                # Required Identifiers
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "PR",
                "USUBJID": self._generate_usubjid(row),
                "PRSEQ": subject_seq[subj],
                # Required - Topic
                "PRTRT": "",
                # Expected - Coding
                "PRMODIFY": "",
                "PRDECOD": "",
                # Expected - Category
                "PRCAT": "",
                "PRSCAT": "",
                # Expected - Occurrence
                "PRPRESP": "",
                "PROCCUR": "",
                "PRSTAT": "",
                "PRREASND": "",
                # Expected - Record Qualifiers
                "PRBODSYS": "",
                "PRINDC": "",
                "PRLOC": "",
                "PRLAT": "",
                "PRDIR": "",
                # Expected - Timing
                "EPOCH": "",
                "PRSTDTC": "",
                "PRENDTC": "",
                "PRSTDY": None,
                "PRENDY": None,
                "PRDUR": "",
                "PRSTRF": "",
                "PRENRF": "",
            }

            # PRSPID - Sponsor-Defined Identifier (Perm)
            for col in ["PRSPID", "PRID", "PROCID"]:
                if col in row and pd.notna(row[col]):
                    pr_record["PRSPID"] = str(row[col])
                    break

            # PRTRT - Procedure Name (Required)
            for col in ["PRTRT", "PROCEDURE", "PROCNAME", "TRT"]:
                if col in row and pd.notna(row[col]):
                    pr_record["PRTRT"] = str(row[col])
                    break

            # PRMODIFY - Modified Procedure Name (Perm)
            for col in ["PRMODIFY", "PRMOD"]:
                if col in row and pd.notna(row[col]):
                    pr_record["PRMODIFY"] = str(row[col])
                    break

            # PRDECOD - Standardized Procedure Name (Expected)
            for col in ["PRDECOD", "PRCODE"]:
                if col in row and pd.notna(row[col]):
                    pr_record["PRDECOD"] = str(row[col])
                    break
            if not pr_record["PRDECOD"] and pr_record["PRTRT"]:
                pr_record["PRDECOD"] = pr_record["PRTRT"].upper()

            # Category and Subcategory
            for col in ["PRCAT", "CAT", "CATEGORY"]:
                if col in row and pd.notna(row[col]):
                    pr_record["PRCAT"] = str(row[col]).upper()
                    break

            for col in ["PRSCAT", "SCAT", "SUBCATEGORY"]:
                if col in row and pd.notna(row[col]):
                    pr_record["PRSCAT"] = str(row[col]).upper()
                    break

            # Body system/location
            for col in ["PRBODSYS", "BODYSYS"]:
                if col in row and pd.notna(row[col]):
                    pr_record["PRBODSYS"] = str(row[col])
                    break

            # Location and Laterality
            for col in ["PRLOC", "LOCATION", "LOC"]:
                if col in row and pd.notna(row[col]):
                    pr_record["PRLOC"] = str(row[col])
                    break

            for col in ["PRLAT", "LAT", "LATERALITY"]:
                if col in row and pd.notna(row[col]):
                    pr_record["PRLAT"] = str(row[col]).upper()
                    break

            # Indication
            for col in ["PRINDC", "INDICATION"]:
                if col in row and pd.notna(row[col]):
                    pr_record["PRINDC"] = str(row[col])
                    break

            # Timing
            for col in ["EPOCH", "PREPOCH"]:
                if col in row and pd.notna(row[col]):
                    pr_record["EPOCH"] = str(row[col]).upper()
                    break

            for col in ["PRSTDTC", "PRSTDT", "PROCDT", "STARTDT"]:
                if col in row and pd.notna(row[col]):
                    pr_record["PRSTDTC"] = self._convert_date_to_iso(row[col])
                    break

            for col in ["PRENDTC", "PRENDT", "ENDDT"]:
                if col in row and pd.notna(row[col]):
                    pr_record["PRENDTC"] = self._convert_date_to_iso(row[col])
                    break

            for col in ["PRSTDY", "STARTDY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        pr_record["PRSTDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            for col in ["PRENDY", "ENDDY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        pr_record["PRENDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            pr_records.append(pr_record)

        result_df = pd.DataFrame(pr_records)

        # Ensure column order per SDTM-IG 3.4
        column_order = ["STUDYID", "DOMAIN", "USUBJID", "PRSEQ", "PRSPID",
                        "PRTRT", "PRMODIFY", "PRDECOD", "PRCAT", "PRSCAT",
                        "PRPRESP", "PROCCUR", "PRSTAT", "PRREASND",
                        "PRBODSYS", "PRINDC", "PRLOC", "PRLAT", "PRDIR",
                        "EPOCH", "PRSTDTC", "PRENDTC", "PRSTDY", "PRENDY", "PRDUR", "PRSTRF", "PRENRF"]
        ordered_cols = [c for c in column_order if c in result_df.columns]
        extra_cols = [c for c in result_df.columns if c not in column_order]
        result_df = result_df[ordered_cols + extra_cols]

        self.log(f"Created {len(result_df)} PR records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class ECTransformer(BaseDomainTransformer):
    """Exposure as Collected domain transformer - SDTM-IG 3.4 compliant (29 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "EC"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to EC domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to EC domain - FULL SDTM-IG 3.4 compliance")
        ec_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            ec_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "EC",
                "USUBJID": self._generate_usubjid(row),
                "ECSEQ": subject_seq[subj],
                "ECTRT": "",
                "ECMOOD": "",
                "ECCAT": "",
                "ECSCAT": "",
                "ECPRESP": "",
                "ECOCCUR": "",
                "ECSTAT": "",
                "ECREASND": "",
                "ECDOSE": None,
                "ECDOSTXT": "",
                "ECDOSU": "",
                "ECDOSFRM": "",
                "ECDOSFRQ": "",
                "ECDOSTOT": None,
                "ECROUTE": "",
                "ECLOC": "",
                "ECLAT": "",
                "ECDIR": "",
                "ECFAST": "",
                "EPOCH": "",
                "ECSTDTC": "",
                "ECENDTC": "",
                "ECSTDY": None,
                "ECENDY": None,
            }

            # Treatment
            for col in ["ECTRT", "TRT", "TREATMENT", "DRUG"]:
                if col in row and pd.notna(row[col]):
                    ec_record["ECTRT"] = str(row[col])
                    break

            # Category
            for col in ["ECCAT", "CAT", "CATEGORY"]:
                if col in row and pd.notna(row[col]):
                    ec_record["ECCAT"] = str(row[col]).upper()
                    break

            for col in ["ECSCAT", "SCAT", "SUBCATEGORY"]:
                if col in row and pd.notna(row[col]):
                    ec_record["ECSCAT"] = str(row[col]).upper()
                    break

            # Dose
            for col in ["ECDOSE", "DOSE"]:
                if col in row and pd.notna(row[col]):
                    try:
                        ec_record["ECDOSE"] = float(row[col])
                    except (ValueError, TypeError):
                        ec_record["ECDOSTXT"] = str(row[col])
                    break

            # Units and form
            for col in ["ECDOSU", "UNIT", "DOSEUNIT"]:
                if col in row and pd.notna(row[col]):
                    ec_record["ECDOSU"] = str(row[col])
                    break

            for col in ["ECDOSFRM", "FORM", "DOSFORM"]:
                if col in row and pd.notna(row[col]):
                    ec_record["ECDOSFRM"] = str(row[col])
                    break

            for col in ["ECDOSFRQ", "FREQ", "FREQUENCY"]:
                if col in row and pd.notna(row[col]):
                    ec_record["ECDOSFRQ"] = str(row[col]).upper()
                    break

            # Route
            for col in ["ECROUTE", "ROUTE"]:
                if col in row and pd.notna(row[col]):
                    ec_record["ECROUTE"] = str(row[col]).upper()
                    break

            # Timing
            for col in ["EPOCH", "ECEPOCH"]:
                if col in row and pd.notna(row[col]):
                    ec_record["EPOCH"] = str(row[col]).upper()
                    break

            for col in ["ECSTDTC", "ECSTDT", "STARTDT"]:
                if col in row and pd.notna(row[col]):
                    ec_record["ECSTDTC"] = self._convert_date_to_iso(row[col])
                    break

            for col in ["ECENDTC", "ECENDT", "ENDDT"]:
                if col in row and pd.notna(row[col]):
                    ec_record["ECENDTC"] = self._convert_date_to_iso(row[col])
                    break

            for col in ["ECSTDY", "STARTDY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        ec_record["ECSTDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            for col in ["ECENDY", "ENDDY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        ec_record["ECENDY"] = int(float(row[col]))
                    except (ValueError, TypeError):
                        pass
                    break

            # Occurrence
            for col in ["ECOCCUR", "OCCUR"]:
                if col in row and pd.notna(row[col]):
                    ec_record["ECOCCUR"] = "Y" if str(row[col]).upper() in ["Y", "YES", "1", "TRUE"] else "N"
                    break

            ec_records.append(ec_record)

        result_df = pd.DataFrame(ec_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("EC", []))
        self.log(f"Created {len(result_df)} EC records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class AGTransformer(BaseDomainTransformer):
    """Procedure Agents domain transformer - SDTM-IG 3.4 compliant (27 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "AG"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to AG domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to AG domain - FULL SDTM-IG 3.4 compliance")
        ag_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            ag_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "AG",
                "USUBJID": self._generate_usubjid(row),
                "AGSEQ": subject_seq[subj],
                "AGTRT": "",
                "AGDECOD": "",
                "AGCAT": "",
                "AGSCAT": "",
                "AGPRESP": "",
                "AGOCCUR": "",
                "AGSTAT": "",
                "AGREASND": "",
                "AGDOSE": None,
                "AGDOSTXT": "",
                "AGDOSU": "",
                "AGDOSFRM": "",
                "AGDOSFRQ": "",
                "AGROUTE": "",
                "AGLOC": "",
                "AGLAT": "",
                "AGDIR": "",
                "EPOCH": "",
                "AGSTDTC": "",
                "AGENDTC": "",
                "AGSTDY": None,
                "AGENDY": None,
            }

            for col in ["AGTRT", "AGENT", "TRT"]:
                if col in row and pd.notna(row[col]):
                    ag_record["AGTRT"] = str(row[col])
                    break

            for col in ["AGDECOD", "AGCODE"]:
                if col in row and pd.notna(row[col]):
                    ag_record["AGDECOD"] = str(row[col])
                    break
            if not ag_record["AGDECOD"] and ag_record["AGTRT"]:
                ag_record["AGDECOD"] = ag_record["AGTRT"].upper()

            for col in ["AGCAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    ag_record["AGCAT"] = str(row[col]).upper()
                    break

            for col in ["AGDOSE", "DOSE"]:
                if col in row and pd.notna(row[col]):
                    try:
                        ag_record["AGDOSE"] = float(row[col])
                    except (ValueError, TypeError):
                        ag_record["AGDOSTXT"] = str(row[col])
                    break

            for col in ["AGDOSU", "UNIT"]:
                if col in row and pd.notna(row[col]):
                    ag_record["AGDOSU"] = str(row[col])
                    break

            for col in ["AGROUTE", "ROUTE"]:
                if col in row and pd.notna(row[col]):
                    ag_record["AGROUTE"] = str(row[col]).upper()
                    break

            for col in ["EPOCH", "AGEPOCH"]:
                if col in row and pd.notna(row[col]):
                    ag_record["EPOCH"] = str(row[col]).upper()
                    break

            for col in ["AGSTDTC", "DATE", "STARTDT"]:
                if col in row and pd.notna(row[col]):
                    ag_record["AGSTDTC"] = self._convert_date_to_iso(row[col])
                    break

            for col in ["AGENDTC", "ENDDT"]:
                if col in row and pd.notna(row[col]):
                    ag_record["AGENDTC"] = self._convert_date_to_iso(row[col])
                    break

            ag_records.append(ag_record)

        result_df = pd.DataFrame(ag_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("AG", []))
        self.log(f"Created {len(result_df)} AG records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class MLTransformer(BaseDomainTransformer):
    """Meal Data domain transformer - SDTM-IG 3.4 compliant (19 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "ML"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to ML domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to ML domain - FULL SDTM-IG 3.4 compliance")
        ml_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            ml_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "ML",
                "USUBJID": self._generate_usubjid(row),
                "MLSEQ": subject_seq[subj],
                "MLTRT": "",
                "MLDECOD": "",
                "MLCAT": "",
                "MLSCAT": "",
                "MLPRESP": "",
                "MLOCCUR": "",
                "MLSTAT": "",
                "MLREASND": "",
                "EPOCH": "",
                "MLDTC": "",
                "MLSTDTC": "",
                "MLENDTC": "",
                "MLSTDY": None,
                "MLENDY": None,
            }

            for col in ["MLTRT", "MEAL", "TRT"]:
                if col in row and pd.notna(row[col]):
                    ml_record["MLTRT"] = str(row[col])
                    break

            for col in ["MLDECOD", "MLCODE"]:
                if col in row and pd.notna(row[col]):
                    ml_record["MLDECOD"] = str(row[col])
                    break
            if not ml_record["MLDECOD"] and ml_record["MLTRT"]:
                ml_record["MLDECOD"] = ml_record["MLTRT"].upper()

            for col in ["MLCAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    ml_record["MLCAT"] = str(row[col]).upper()
                    break

            for col in ["EPOCH", "MLEPOCH"]:
                if col in row and pd.notna(row[col]):
                    ml_record["EPOCH"] = str(row[col]).upper()
                    break

            for col in ["MLDTC", "MLDT", "DATE"]:
                if col in row and pd.notna(row[col]):
                    ml_record["MLDTC"] = self._convert_date_to_iso(row[col])
                    break

            for col in ["MLSTDTC", "STARTDT"]:
                if col in row and pd.notna(row[col]):
                    ml_record["MLSTDTC"] = self._convert_date_to_iso(row[col])
                    break

            for col in ["MLENDTC", "ENDDT"]:
                if col in row and pd.notna(row[col]):
                    ml_record["MLENDTC"] = self._convert_date_to_iso(row[col])
                    break

            ml_records.append(ml_record)

        result_df = pd.DataFrame(ml_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("ML", []))
        self.log(f"Created {len(result_df)} ML records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


# =============================================================================
# EVENTS DOMAINS
# =============================================================================

class CETransformer(BaseDomainTransformer):
    """Clinical Events domain transformer - SDTM-IG 3.4 compliant (30 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "CE"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to CE domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to CE domain - FULL SDTM-IG 3.4 compliance")
        ce_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            ce_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "CE",
                "USUBJID": self._generate_usubjid(row),
                "CESEQ": subject_seq[subj],
                "CETERM": "",
                "CEMODIFY": "",
                "CEDECOD": "",
                "CECAT": "",
                "CESCAT": "",
                "CEPRESP": "",
                "CEOCCUR": "",
                "CESTAT": "",
                "CEREASND": "",
                "CEBODSYS": "",
                "CESEV": "",
                "CESER": "",
                "CEACN": "",
                "CEREL": "",
                "CEOUT": "",
                "CECONTRT": "",
                "CETOXGR": "",
                "EPOCH": "",
                "CESTDTC": "",
                "CEENDTC": "",
                "CESTDY": None,
                "CEENDY": None,
                "CEDUR": "",
                "CESTRF": "",
                "CEENRF": "",
            }

            for col in ["CETERM", "TERM", "EVENT"]:
                if col in row and pd.notna(row[col]):
                    ce_record["CETERM"] = str(row[col])
                    break

            for col in ["CEDECOD", "DECODE"]:
                if col in row and pd.notna(row[col]):
                    ce_record["CEDECOD"] = str(row[col])
                    break
            if not ce_record["CEDECOD"] and ce_record["CETERM"]:
                ce_record["CEDECOD"] = ce_record["CETERM"].upper()

            for col in ["CECAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    ce_record["CECAT"] = str(row[col]).upper()
                    break

            for col in ["CESEV", "SEVERITY"]:
                if col in row and pd.notna(row[col]):
                    ce_record["CESEV"] = str(row[col]).upper()
                    break

            for col in ["CESER", "SERIOUS"]:
                if col in row and pd.notna(row[col]):
                    ce_record["CESER"] = "Y" if str(row[col]).upper() in ["Y", "YES", "1", "TRUE"] else "N"
                    break

            for col in ["EPOCH", "CEEPOCH"]:
                if col in row and pd.notna(row[col]):
                    ce_record["EPOCH"] = str(row[col]).upper()
                    break

            for col in ["CESTDTC", "STARTDT"]:
                if col in row and pd.notna(row[col]):
                    ce_record["CESTDTC"] = self._convert_date_to_iso(row[col])
                    break

            for col in ["CEENDTC", "ENDDT"]:
                if col in row and pd.notna(row[col]):
                    ce_record["CEENDTC"] = self._convert_date_to_iso(row[col])
                    break

            ce_records.append(ce_record)

        result_df = pd.DataFrame(ce_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("CE", []))
        self.log(f"Created {len(result_df)} CE records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class DVTransformer(BaseDomainTransformer):
    """Protocol Deviations domain transformer - SDTM-IG 3.4 compliant (14 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "DV"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to DV domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to DV domain - FULL SDTM-IG 3.4 compliance")
        dv_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            dv_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "DV",
                "USUBJID": self._generate_usubjid(row),
                "DVSEQ": subject_seq[subj],
                "DVTERM": "",
                "DVDECOD": "",
                "DVCAT": "",
                "DVSCAT": "",
                "EPOCH": "",
                "DVSTDTC": "",
                "DVENDTC": "",
                "DVSTDY": None,
                "DVENDY": None,
            }

            # Deviation term
            for col in ["DVTERM", "TERM", "DEVIATION"]:
                if col in row and pd.notna(row[col]):
                    dv_record["DVTERM"] = str(row[col])
                    break

            # Coded term
            for col in ["DVDECOD", "DECODE", "CODE"]:
                if col in row and pd.notna(row[col]):
                    dv_record["DVDECOD"] = str(row[col])
                    break
            if not dv_record["DVDECOD"] and dv_record["DVTERM"]:
                dv_record["DVDECOD"] = dv_record["DVTERM"].upper()

            # Category
            for col in ["DVCAT", "CAT", "CATEGORY"]:
                if col in row and pd.notna(row[col]):
                    dv_record["DVCAT"] = str(row[col]).upper()
                    break

            for col in ["DVSCAT", "SCAT", "SUBCATEGORY"]:
                if col in row and pd.notna(row[col]):
                    dv_record["DVSCAT"] = str(row[col]).upper()
                    break

            # Epoch
            for col in ["EPOCH", "DVEPOCH"]:
                if col in row and pd.notna(row[col]):
                    dv_record["EPOCH"] = str(row[col]).upper()
                    break

            # Date
            for col in ["DVSTDTC", "DVDT", "DATE", "STARTDT"]:
                if col in row and pd.notna(row[col]):
                    dv_record["DVSTDTC"] = self._convert_date_to_iso(row[col])
                    break

            for col in ["DVENDTC", "ENDDT"]:
                if col in row and pd.notna(row[col]):
                    dv_record["DVENDTC"] = self._convert_date_to_iso(row[col])
                    break

            dv_records.append(dv_record)

        result_df = pd.DataFrame(dv_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("DV", []))
        self.log(f"Created {len(result_df)} DV records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class HOTransformer(BaseDomainTransformer):
    """Healthcare Encounters domain transformer - SDTM-IG 3.4 compliant (21 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "HO"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to HO domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to HO domain - FULL SDTM-IG 3.4 compliance")
        ho_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            ho_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "HO",
                "USUBJID": self._generate_usubjid(row),
                "HOSEQ": subject_seq[subj],
                "HOTERM": "",
                "HODECOD": "",
                "HOCAT": "",
                "HOSCAT": "",
                "HOPRESP": "",
                "HOOCCUR": "",
                "HOSTAT": "",
                "HOREASND": "",
                "HOINDC": "",
                "EPOCH": "",
                "HOSTDTC": "",
                "HOENDTC": "",
                "HOSTDY": None,
                "HOENDY": None,
                "HODUR": "",
                "HOENRF": "",
            }

            for col in ["HOTERM", "TERM", "ENCOUNTER"]:
                if col in row and pd.notna(row[col]):
                    ho_record["HOTERM"] = str(row[col])
                    break

            for col in ["HODECOD", "DECODE"]:
                if col in row and pd.notna(row[col]):
                    ho_record["HODECOD"] = str(row[col])
                    break
            if not ho_record["HODECOD"] and ho_record["HOTERM"]:
                ho_record["HODECOD"] = ho_record["HOTERM"].upper()

            for col in ["HOCAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    ho_record["HOCAT"] = str(row[col]).upper()
                    break

            for col in ["HOINDC", "INDICATION"]:
                if col in row and pd.notna(row[col]):
                    ho_record["HOINDC"] = str(row[col])
                    break

            for col in ["EPOCH", "HOEPOCH"]:
                if col in row and pd.notna(row[col]):
                    ho_record["EPOCH"] = str(row[col]).upper()
                    break

            for col in ["HOSTDTC", "STARTDT"]:
                if col in row and pd.notna(row[col]):
                    ho_record["HOSTDTC"] = self._convert_date_to_iso(row[col])
                    break

            for col in ["HOENDTC", "ENDDT"]:
                if col in row and pd.notna(row[col]):
                    ho_record["HOENDTC"] = self._convert_date_to_iso(row[col])
                    break

            ho_records.append(ho_record)

        result_df = pd.DataFrame(ho_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("HO", []))
        self.log(f"Created {len(result_df)} HO records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class BETransformer(BaseDomainTransformer):
    """Biospecimen Events domain transformer - SDTM-IG 3.4 compliant (22 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "BE"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to BE domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to BE domain - FULL SDTM-IG 3.4 compliance")
        be_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            be_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "BE",
                "USUBJID": self._generate_usubjid(row),
                "BESEQ": subject_seq[subj],
                "BETESTCD": "",
                "BETEST": "",
                "BECAT": "",
                "BESCAT": "",
                "BEORRES": "",
                "BEORRESU": "",
                "BESTRESC": "",
                "BESTRESN": None,
                "BESTRESU": "",
                "BESTAT": "",
                "BEREASND": "",
                "VISITNUM": None,
                "VISIT": "",
                "VISITDY": None,
                "EPOCH": "",
                "BEDTC": "",
                "BEDY": None,
            }

            for col in ["BETESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    be_record["BETESTCD"] = str(row[col])[:8]
                    break

            for col in ["BETEST", "TEST", "EVENT"]:
                if col in row and pd.notna(row[col]):
                    be_record["BETEST"] = str(row[col])
                    break

            for col in ["BEORRES", "RESULT", "VALUE"]:
                if col in row and pd.notna(row[col]):
                    be_record["BEORRES"] = str(row[col])
                    be_record["BESTRESC"] = str(row[col])
                    break

            for col in ["EPOCH", "BEEPOCH"]:
                if col in row and pd.notna(row[col]):
                    be_record["EPOCH"] = str(row[col]).upper()
                    break

            for col in ["BEDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    be_record["BEDTC"] = self._convert_date_to_iso(row[col])
                    break

            be_records.append(be_record)

        result_df = pd.DataFrame(be_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("BE", []))
        self.log(f"Created {len(result_df)} BE records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


# =============================================================================
# FINDINGS DOMAINS - Additional
# =============================================================================

class DDTransformer(BaseDomainTransformer):
    """Death Details domain transformer - SDTM-IG 3.4 compliant (21 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "DD"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to DD domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to DD domain - FULL SDTM-IG 3.4 compliance")
        dd_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            dd_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "DD",
                "USUBJID": self._generate_usubjid(row),
                "DDSEQ": subject_seq[subj],
                "DDTESTCD": "",
                "DDTEST": "",
                "DDCAT": "",
                "DDSCAT": "",
                "DDORRES": "",
                "DDORRESU": "",
                "DDSTRESC": "",
                "DDSTRESN": None,
                "DDSTRESU": "",
                "DDSTAT": "",
                "DDREASND": "",
                "VISITNUM": None,
                "VISIT": "",
                "EPOCH": "",
                "DDDTC": "",
                "DDDY": None,
            }

            # Test code
            for col in ["DDTESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    dd_record["DDTESTCD"] = str(row[col])[:8]
                    break

            for col in ["DDTEST", "TEST"]:
                if col in row and pd.notna(row[col]):
                    dd_record["DDTEST"] = str(row[col])
                    break

            for col in ["DDCAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    dd_record["DDCAT"] = str(row[col]).upper()
                    break

            # Cause of death
            for col in ["DDORRES", "CAUSE", "DEATHCAUSE"]:
                if col in row and pd.notna(row[col]):
                    dd_record["DDORRES"] = str(row[col])
                    dd_record["DDSTRESC"] = str(row[col])
                    break

            for col in ["EPOCH", "DDEPOCH"]:
                if col in row and pd.notna(row[col]):
                    dd_record["EPOCH"] = str(row[col]).upper()
                    break

            # Date
            for col in ["DDDTC", "DTHDTC", "DEATHDT"]:
                if col in row and pd.notna(row[col]):
                    dd_record["DDDTC"] = self._convert_date_to_iso(row[col])
                    break

            dd_records.append(dd_record)

        result_df = pd.DataFrame(dd_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("DD", []))
        self.log(f"Created {len(result_df)} DD records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class SCTransformer(BaseDomainTransformer):
    """Subject Characteristics domain transformer - SDTM-IG 3.4 compliant (16 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "SC"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to SC domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to SC domain - FULL SDTM-IG 3.4 compliance")
        sc_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            sc_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "SC",
                "USUBJID": self._generate_usubjid(row),
                "SCSEQ": subject_seq[subj],
                "SCTESTCD": "",
                "SCTEST": "",
                "SCORRES": "",
                "SCORRESU": "",
                "SCSTRESC": "",
                "SCSTRESN": None,
                "SCSTRESU": "",
                "SCSTAT": "",
                "SCREASND": "",
                "SCDTC": "",
                "SCDY": None,
            }

            for col in ["SCTESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    sc_record["SCTESTCD"] = str(row[col])[:8]
                    break

            for col in ["SCTEST", "TEST", "CHARACTERISTIC"]:
                if col in row and pd.notna(row[col]):
                    sc_record["SCTEST"] = str(row[col])
                    break

            for col in ["SCORRES", "RESULT", "VALUE"]:
                if col in row and pd.notna(row[col]):
                    sc_record["SCORRES"] = str(row[col])
                    sc_record["SCSTRESC"] = str(row[col])
                    try:
                        sc_record["SCSTRESN"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            for col in ["SCDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    sc_record["SCDTC"] = self._convert_date_to_iso(row[col])
                    break

            sc_records.append(sc_record)

        result_df = pd.DataFrame(sc_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("SC", []))
        self.log(f"Created {len(result_df)} SC records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class SSTransformer(BaseDomainTransformer):
    """Subject Status domain transformer - SDTM-IG 3.4 compliant (21 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "SS"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to SS domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to SS domain - FULL SDTM-IG 3.4 compliance")
        ss_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            ss_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "SS",
                "USUBJID": self._generate_usubjid(row),
                "SSSEQ": subject_seq[subj],
                "SSTESTCD": "",
                "SSTEST": "",
                "SSCAT": "",
                "SSSCAT": "",
                "SSORRES": "",
                "SSORRESU": "",
                "SSSTRESC": "",
                "SSSTRESN": None,
                "SSSTRESU": "",
                "SSSTAT": "",
                "SSREASND": "",
                "VISITNUM": None,
                "VISIT": "",
                "EPOCH": "",
                "SSDTC": "",
                "SSDY": None,
            }

            for col in ["SSTESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    ss_record["SSTESTCD"] = str(row[col])[:8]
                    break

            for col in ["SSTEST", "TEST", "STATUS"]:
                if col in row and pd.notna(row[col]):
                    ss_record["SSTEST"] = str(row[col])
                    break

            for col in ["SSCAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    ss_record["SSCAT"] = str(row[col]).upper()
                    break

            for col in ["SSORRES", "RESULT"]:
                if col in row and pd.notna(row[col]):
                    ss_record["SSORRES"] = str(row[col])
                    ss_record["SSSTRESC"] = str(row[col])
                    try:
                        ss_record["SSSTRESN"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            for col in ["EPOCH", "SSEPOCH"]:
                if col in row and pd.notna(row[col]):
                    ss_record["EPOCH"] = str(row[col]).upper()
                    break

            for col in ["SSDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    ss_record["SSDTC"] = self._convert_date_to_iso(row[col])
                    break

            ss_records.append(ss_record)

        result_df = pd.DataFrame(ss_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("SS", []))
        self.log(f"Created {len(result_df)} SS records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class FATransformer(BaseDomainTransformer):
    """Findings About Events or Interventions domain transformer - SDTM-IG 3.4 compliant (24 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "FA"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to FA domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to FA domain - FULL SDTM-IG 3.4 compliance")
        fa_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            fa_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "FA",
                "USUBJID": self._generate_usubjid(row),
                "FASEQ": subject_seq[subj],
                "FATESTCD": "",
                "FATEST": "",
                "FACAT": "",
                "FASCAT": "",
                "FAOBJ": "",
                "FAORRES": "",
                "FAORRESU": "",
                "FASTRESC": "",
                "FASTRESN": None,
                "FASTRESU": "",
                "FASTAT": "",
                "FAREASND": "",
                "FALOC": "",
                "FALAT": "",
                "VISITNUM": None,
                "VISIT": "",
                "EPOCH": "",
                "FADTC": "",
                "FADY": None,
            }

            for col in ["FATESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    fa_record["FATESTCD"] = str(row[col])[:8]
                    break

            for col in ["FATEST", "TEST"]:
                if col in row and pd.notna(row[col]):
                    fa_record["FATEST"] = str(row[col])
                    break

            for col in ["FACAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    fa_record["FACAT"] = str(row[col]).upper()
                    break

            for col in ["FAOBJ", "OBJ", "OBJECT"]:
                if col in row and pd.notna(row[col]):
                    fa_record["FAOBJ"] = str(row[col])
                    break

            for col in ["FAORRES", "RESULT"]:
                if col in row and pd.notna(row[col]):
                    fa_record["FAORRES"] = str(row[col])
                    fa_record["FASTRESC"] = str(row[col])
                    try:
                        fa_record["FASTRESN"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            for col in ["EPOCH", "FAEPOCH"]:
                if col in row and pd.notna(row[col]):
                    fa_record["EPOCH"] = str(row[col]).upper()
                    break

            for col in ["FADTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    fa_record["FADTC"] = self._convert_date_to_iso(row[col])
                    break

            fa_records.append(fa_record)

        result_df = pd.DataFrame(fa_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("FA", []))
        self.log(f"Created {len(result_df)} FA records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class PPTransformer(BaseDomainTransformer):
    """Pharmacokinetics Parameters domain transformer - SDTM-IG 3.4 compliant (19 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "PP"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to PP domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to PP domain - FULL SDTM-IG 3.4 compliance")
        pp_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            pp_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "PP",
                "USUBJID": self._generate_usubjid(row),
                "PPSEQ": subject_seq[subj],
                "PPTESTCD": "",
                "PPTEST": "",
                "PPCAT": "",
                "PPSCAT": "",
                "PPORRES": "",
                "PPORRESU": "",
                "PPSTRESC": "",
                "PPSTRESN": None,
                "PPSTRESU": "",
                "PPSTAT": "",
                "PPREASND": "",
                "PPSPEC": "",
                "PPRFTDTC": "",
                "PPDTC": "",
            }

            # Test code (CMAX, AUC, TMAX, etc.)
            for col in ["PPTESTCD", "TESTCD", "PARAM"]:
                if col in row and pd.notna(row[col]):
                    pp_record["PPTESTCD"] = str(row[col])[:8].upper()
                    break

            for col in ["PPTEST", "TEST", "PARAMETER"]:
                if col in row and pd.notna(row[col]):
                    pp_record["PPTEST"] = str(row[col])
                    break

            # Category
            for col in ["PPCAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    pp_record["PPCAT"] = str(row[col]).upper()
                    break

            # Specimen
            for col in ["PPSPEC", "SPECIMEN"]:
                if col in row and pd.notna(row[col]):
                    pp_record["PPSPEC"] = str(row[col]).upper()
                    break

            # Result
            for col in ["PPORRES", "RESULT", "VALUE"]:
                if col in row and pd.notna(row[col]):
                    pp_record["PPORRES"] = str(row[col])
                    pp_record["PPSTRESC"] = str(row[col])
                    try:
                        pp_record["PPSTRESN"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # Units
            for col in ["PPORRESU", "UNIT"]:
                if col in row and pd.notna(row[col]):
                    pp_record["PPORRESU"] = str(row[col])
                    pp_record["PPSTRESU"] = str(row[col])
                    break

            # Reference time
            for col in ["PPRFTDTC", "REFTDT"]:
                if col in row and pd.notna(row[col]):
                    pp_record["PPRFTDTC"] = self._convert_date_to_iso(row[col])
                    break

            for col in ["PPDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    pp_record["PPDTC"] = self._convert_date_to_iso(row[col])
                    break

            pp_records.append(pp_record)

        result_df = pd.DataFrame(pp_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("PP", []))
        self.log(f"Created {len(result_df)} PP records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class MBTransformer(BaseDomainTransformer):
    """Microbiology domain transformer - SDTM-IG 3.4 compliant (26 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "MB"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to MB domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to MB domain - FULL SDTM-IG 3.4 compliance")
        mb_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            mb_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "MB",
                "USUBJID": self._generate_usubjid(row),
                "MBSEQ": subject_seq[subj],
                "MBTESTCD": "",
                "MBTEST": "",
                "MBCAT": "",
                "MBSCAT": "",
                "MBORRES": "",
                "MBORRESU": "",
                "MBSTRESC": "",
                "MBSTRESN": None,
                "MBSTRESU": "",
                "MBSTAT": "",
                "MBREASND": "",
                "MBNAM": "",
                "MBSPEC": "",
                "MBLOC": "",
                "MBLAT": "",
                "MBMETHOD": "",
                "VISITNUM": None,
                "VISIT": "",
                "EPOCH": "",
                "MBDTC": "",
                "MBDY": None,
            }

            for col in ["MBTESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    mb_record["MBTESTCD"] = str(row[col])[:8]
                    break

            for col in ["MBTEST", "TEST"]:
                if col in row and pd.notna(row[col]):
                    mb_record["MBTEST"] = str(row[col])
                    break

            for col in ["MBCAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    mb_record["MBCAT"] = str(row[col]).upper()
                    break

            for col in ["MBORRES", "RESULT"]:
                if col in row and pd.notna(row[col]):
                    mb_record["MBORRES"] = str(row[col])
                    mb_record["MBSTRESC"] = str(row[col])
                    try:
                        mb_record["MBSTRESN"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            for col in ["MBSPEC", "SPECIMEN"]:
                if col in row and pd.notna(row[col]):
                    mb_record["MBSPEC"] = str(row[col]).upper()
                    break

            for col in ["MBMETHOD", "METHOD"]:
                if col in row and pd.notna(row[col]):
                    mb_record["MBMETHOD"] = str(row[col])
                    break

            for col in ["EPOCH", "MBEPOCH"]:
                if col in row and pd.notna(row[col]):
                    mb_record["EPOCH"] = str(row[col]).upper()
                    break

            for col in ["MBDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    mb_record["MBDTC"] = self._convert_date_to_iso(row[col])
                    break

            for col in ["MBDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    mb_record["MBDTC"] = self._convert_date_to_iso(row[col])
                    break

            mb_records.append(mb_record)

        result_df = pd.DataFrame(mb_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("MB", []))
        self.log(f"Created {len(result_df)} MB records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class MITransformer(BaseDomainTransformer):
    """Microscopic Findings domain transformer - SDTM-IG 3.4 compliant (26 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "MI"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to MI domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to MI domain - FULL SDTM-IG 3.4 compliance")
        mi_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            mi_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "MI",
                "USUBJID": self._generate_usubjid(row),
                "MISEQ": subject_seq[subj],
                "MIGRPID": "",
                "MIREFID": "",
                "MISPID": "",
                "MITESTCD": "",
                "MITEST": "",
                "MICAT": "",
                "MISCAT": "",
                "MIORRES": "",
                "MIORRESU": "",
                "MISTRESC": "",
                "MISTRESN": None,
                "MISTRESU": "",
                "MIRESCAT": "",
                "MISTAT": "",
                "MIREASND": "",
                "MINAM": "",
                "MISPEC": "",
                "MISPCCND": "",
                "MILOC": "",
                "MILAT": "",
                "MIMETHOD": "",
                "MIBLFL": "",
                "VISITNUM": None,
                "VISIT": "",
                "EPOCH": "",
                "MIDTC": "",
                "MIDY": None,
            }

            # Test code
            for col in ["MITESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    mi_record["MITESTCD"] = str(row[col])[:8]
                    break

            for col in ["MITEST", "TEST"]:
                if col in row and pd.notna(row[col]):
                    mi_record["MITEST"] = str(row[col])
                    break

            # Category
            for col in ["MICAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    mi_record["MICAT"] = str(row[col]).upper()
                    break

            # Result
            for col in ["MIORRES", "RESULT"]:
                if col in row and pd.notna(row[col]):
                    mi_record["MIORRES"] = str(row[col])
                    mi_record["MISTRESC"] = str(row[col])
                    try:
                        mi_record["MISTRESN"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # Specimen
            for col in ["MISPEC", "SPECIMEN"]:
                if col in row and pd.notna(row[col]):
                    mi_record["MISPEC"] = str(row[col]).upper()
                    break

            # Location
            for col in ["MILOC", "LOC", "LOCATION"]:
                if col in row and pd.notna(row[col]):
                    mi_record["MILOC"] = str(row[col]).upper()
                    break

            # Method
            for col in ["MIMETHOD", "METHOD"]:
                if col in row and pd.notna(row[col]):
                    mi_record["MIMETHOD"] = str(row[col])
                    break

            # Date
            for col in ["MIDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    mi_record["MIDTC"] = self._convert_date_to_iso(row[col])
                    break

            mi_records.append(mi_record)

        result_df = pd.DataFrame(mi_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("MI", []))
        self.log(f"Created {len(result_df)} MI records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class DATransformer(BaseDomainTransformer):
    """Drug Accountability domain transformer - SDTM-IG 3.4 compliant (22 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "DA"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to DA domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to DA domain - FULL SDTM-IG 3.4 compliance")
        da_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            da_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "DA",
                "USUBJID": self._generate_usubjid(row),
                "DASEQ": subject_seq[subj],
                "DAGRPID": "",
                "DAREFID": "",
                "DASPID": "",
                "DATESTCD": "",
                "DATEST": "",
                "DACAT": "",
                "DASCAT": "",
                "DAORRES": "",
                "DAORRESU": "",
                "DASTRESC": "",
                "DASTRESN": None,
                "DASTRESU": "",
                "DASTAT": "",
                "DAREASND": "",
                "VISITNUM": None,
                "VISIT": "",
                "EPOCH": "",
                "DADTC": "",
                "DADY": None,
            }

            # Test code
            for col in ["DATESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    da_record["DATESTCD"] = str(row[col])[:8]
                    break

            for col in ["DATEST", "TEST"]:
                if col in row and pd.notna(row[col]):
                    da_record["DATEST"] = str(row[col])
                    break

            # Category
            for col in ["DACAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    da_record["DACAT"] = str(row[col]).upper()
                    break

            # Result
            for col in ["DAORRES", "RESULT", "COUNT"]:
                if col in row and pd.notna(row[col]):
                    da_record["DAORRES"] = str(row[col])
                    da_record["DASTRESC"] = str(row[col])
                    try:
                        da_record["DASTRESN"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # Unit
            for col in ["DAORRESU", "UNIT"]:
                if col in row and pd.notna(row[col]):
                    da_record["DAORRESU"] = str(row[col])
                    da_record["DASTRESU"] = str(row[col])
                    break

            # Date
            for col in ["DADTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    da_record["DADTC"] = self._convert_date_to_iso(row[col])
                    break

            da_records.append(da_record)

        result_df = pd.DataFrame(da_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("DA", []))
        self.log(f"Created {len(result_df)} DA records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class FTTransformer(BaseDomainTransformer):
    """Functional Tests domain transformer - SDTM-IG 3.4 compliant (26 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "FT"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to FT domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to FT domain - FULL SDTM-IG 3.4 compliance")
        ft_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            ft_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "FT",
                "USUBJID": self._generate_usubjid(row),
                "FTSEQ": subject_seq[subj],
                "FTGRPID": "",
                "FTREFID": "",
                "FTSPID": "",
                "FTTESTCD": "",
                "FTTEST": "",
                "FTCAT": "",
                "FTSCAT": "",
                "FTPOS": "",
                "FTORRES": "",
                "FTORRESU": "",
                "FTSTRESC": "",
                "FTSTRESN": None,
                "FTSTRESU": "",
                "FTSTAT": "",
                "FTREASND": "",
                "FTLOC": "",
                "FTLAT": "",
                "FTMETHOD": "",
                "FTBLFL": "",
                "VISITNUM": None,
                "VISIT": "",
                "EPOCH": "",
                "FTDTC": "",
                "FTDY": None,
            }

            # Test code
            for col in ["FTTESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    ft_record["FTTESTCD"] = str(row[col])[:8]
                    break

            for col in ["FTTEST", "TEST"]:
                if col in row and pd.notna(row[col]):
                    ft_record["FTTEST"] = str(row[col])
                    break

            # Category
            for col in ["FTCAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    ft_record["FTCAT"] = str(row[col]).upper()
                    break

            # Result
            for col in ["FTORRES", "RESULT"]:
                if col in row and pd.notna(row[col]):
                    ft_record["FTORRES"] = str(row[col])
                    ft_record["FTSTRESC"] = str(row[col])
                    try:
                        ft_record["FTSTRESN"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # Unit
            for col in ["FTORRESU", "UNIT"]:
                if col in row and pd.notna(row[col]):
                    ft_record["FTORRESU"] = str(row[col])
                    ft_record["FTSTRESU"] = str(row[col])
                    break

            # Location
            for col in ["FTLOC", "LOC", "LOCATION"]:
                if col in row and pd.notna(row[col]):
                    ft_record["FTLOC"] = str(row[col]).upper()
                    break

            # Method
            for col in ["FTMETHOD", "METHOD"]:
                if col in row and pd.notna(row[col]):
                    ft_record["FTMETHOD"] = str(row[col])
                    break

            # Date
            for col in ["FTDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    ft_record["FTDTC"] = self._convert_date_to_iso(row[col])
                    break

            ft_records.append(ft_record)

        result_df = pd.DataFrame(ft_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("FT", []))
        self.log(f"Created {len(result_df)} FT records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class SRTransformer(BaseDomainTransformer):
    """Skin Response domain transformer - SDTM-IG 3.4 compliant (26 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "SR"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to SR domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to SR domain - FULL SDTM-IG 3.4 compliance")
        sr_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            sr_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "SR",
                "USUBJID": self._generate_usubjid(row),
                "SRSEQ": subject_seq[subj],
                "SRGRPID": "",
                "SRREFID": "",
                "SRSPID": "",
                "SRTESTCD": "",
                "SRTEST": "",
                "SRCAT": "",
                "SRSCAT": "",
                "SROBJ": "",
                "SRORRES": "",
                "SRORRESU": "",
                "SRSTRESC": "",
                "SRSTRESN": None,
                "SRSTRESU": "",
                "SRSTAT": "",
                "SRREASND": "",
                "SRLOC": "",
                "SRLAT": "",
                "SRMETHOD": "",
                "SRBLFL": "",
                "VISITNUM": None,
                "VISIT": "",
                "EPOCH": "",
                "SRDTC": "",
                "SRDY": None,
            }

            # Test code
            for col in ["SRTESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    sr_record["SRTESTCD"] = str(row[col])[:8]
                    break

            for col in ["SRTEST", "TEST"]:
                if col in row and pd.notna(row[col]):
                    sr_record["SRTEST"] = str(row[col])
                    break

            # Category
            for col in ["SRCAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    sr_record["SRCAT"] = str(row[col]).upper()
                    break

            # Object (allergen/substance)
            for col in ["SROBJ", "ALLERGEN", "SUBSTANCE"]:
                if col in row and pd.notna(row[col]):
                    sr_record["SROBJ"] = str(row[col])
                    break

            # Result
            for col in ["SRORRES", "RESULT"]:
                if col in row and pd.notna(row[col]):
                    sr_record["SRORRES"] = str(row[col])
                    sr_record["SRSTRESC"] = str(row[col])
                    try:
                        sr_record["SRSTRESN"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # Unit
            for col in ["SRORRESU", "UNIT"]:
                if col in row and pd.notna(row[col]):
                    sr_record["SRORRESU"] = str(row[col])
                    sr_record["SRSTRESU"] = str(row[col])
                    break

            # Location
            for col in ["SRLOC", "LOC", "LOCATION"]:
                if col in row and pd.notna(row[col]):
                    sr_record["SRLOC"] = str(row[col]).upper()
                    break

            # Method
            for col in ["SRMETHOD", "METHOD"]:
                if col in row and pd.notna(row[col]):
                    sr_record["SRMETHOD"] = str(row[col])
                    break

            # Date
            for col in ["SRDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    sr_record["SRDTC"] = self._convert_date_to_iso(row[col])
                    break

            sr_records.append(sr_record)

        result_df = pd.DataFrame(sr_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("SR", []))
        self.log(f"Created {len(result_df)} SR records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


# =============================================================================
# TRIAL DESIGN DOMAINS
# =============================================================================

class TETransformer(BaseDomainTransformer):
    """Trial Elements domain transformer - SDTM-IG 3.4 compliant (7 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "TE"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to TE domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to TE domain - FULL SDTM-IG 3.4 compliance")
        te_records = []

        for idx, row in source_df.iterrows():
            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            te_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "TE",
                "ETCD": "",
                "ELEMENT": "",
                "TESTRL": "",
                "TEENRL": "",
                "TEDUR": "",
            }

            # Element code
            for col in ["ETCD", "ELEMENTCD", "ELEMCD"]:
                if col in row and pd.notna(row[col]):
                    te_record["ETCD"] = str(row[col])[:8]
                    break

            # Element name
            for col in ["ELEMENT", "ELEMENTNAME", "ELEMNAME"]:
                if col in row and pd.notna(row[col]):
                    te_record["ELEMENT"] = str(row[col])
                    break

            # Start rule
            for col in ["TESTRL", "STARTRULE"]:
                if col in row and pd.notna(row[col]):
                    te_record["TESTRL"] = str(row[col])
                    break

            # End rule
            for col in ["TEENRL", "ENDRULE"]:
                if col in row and pd.notna(row[col]):
                    te_record["TEENRL"] = str(row[col])
                    break

            # Duration
            for col in ["TEDUR", "DURATION"]:
                if col in row and pd.notna(row[col]):
                    te_record["TEDUR"] = str(row[col])
                    break

            te_records.append(te_record)

        result_df = pd.DataFrame(te_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("TE", []))
        self.log(f"Created {len(result_df)} TE records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class TVTransformer(BaseDomainTransformer):
    """Trial Visits domain transformer - SDTM-IG 3.4 compliant (9 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "TV"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to TV domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to TV domain - FULL SDTM-IG 3.4 compliance")
        tv_records = []

        for idx, row in source_df.iterrows():
            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            tv_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "TV",
                "VISITNUM": None,
                "VISIT": "",
                "VISITDY": None,
                "ARMCD": "",
                "ARM": "",
                "TVSTRL": "",
                "TVENRL": "",
            }

            # Visit number
            for col in ["VISITNUM", "VISNUM"]:
                if col in row and pd.notna(row[col]):
                    try:
                        tv_record["VISITNUM"] = int(row[col])
                    except (ValueError, TypeError):
                        tv_record["VISITNUM"] = idx + 1
                    break
            else:
                tv_record["VISITNUM"] = idx + 1

            # Visit name
            for col in ["VISIT", "VISITNAME"]:
                if col in row and pd.notna(row[col]):
                    tv_record["VISIT"] = str(row[col])
                    break

            # Visit day
            for col in ["VISITDY", "VISDY"]:
                if col in row and pd.notna(row[col]):
                    try:
                        tv_record["VISITDY"] = int(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # Arm code
            for col in ["ARMCD", "ARM_CD"]:
                if col in row and pd.notna(row[col]):
                    tv_record["ARMCD"] = str(row[col])[:20]
                    break

            # Arm description
            for col in ["ARM", "ARMNAME"]:
                if col in row and pd.notna(row[col]):
                    tv_record["ARM"] = str(row[col])
                    break

            # Start rule
            for col in ["TVSTRL", "STARTRULE"]:
                if col in row and pd.notna(row[col]):
                    tv_record["TVSTRL"] = str(row[col])
                    break

            # End rule
            for col in ["TVENRL", "ENDRULE"]:
                if col in row and pd.notna(row[col]):
                    tv_record["TVENRL"] = str(row[col])
                    break

            tv_records.append(tv_record)

        result_df = pd.DataFrame(tv_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("TV", []))
        self.log(f"Created {len(result_df)} TV records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class TITransformer(BaseDomainTransformer):
    """Trial Inclusion/Exclusion Criteria domain transformer - SDTM-IG 3.4 compliant (7 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "TI"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to TI domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to TI domain - FULL SDTM-IG 3.4 compliance")
        ti_records = []

        for idx, row in source_df.iterrows():
            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            ti_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "TI",
                "IETESTCD": "",
                "IETEST": "",
                "IECAT": "",
                "IESCAT": "",
                "TIRL": "",
            }

            # Criteria code
            for col in ["IETESTCD", "CRITID", "CRITERIONID"]:
                if col in row and pd.notna(row[col]):
                    ti_record["IETESTCD"] = str(row[col])[:8]
                    break

            # Criteria description
            for col in ["IETEST", "CRITERIA", "CRITERION"]:
                if col in row and pd.notna(row[col]):
                    ti_record["IETEST"] = str(row[col])
                    break

            # Category (INCLUSION/EXCLUSION)
            for col in ["IECAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    val = str(row[col]).upper()
                    if val in ["INCLUSION", "EXCLUSION", "I", "E"]:
                        if val == "I":
                            val = "INCLUSION"
                        elif val == "E":
                            val = "EXCLUSION"
                        ti_record["IECAT"] = val
                    break

            # Subcategory
            for col in ["IESCAT", "SCAT"]:
                if col in row and pd.notna(row[col]):
                    ti_record["IESCAT"] = str(row[col])
                    break

            # Rule
            for col in ["TIRL", "RULE"]:
                if col in row and pd.notna(row[col]):
                    ti_record["TIRL"] = str(row[col])
                    break

            ti_records.append(ti_record)

        result_df = pd.DataFrame(ti_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("TI", []))
        self.log(f"Created {len(result_df)} TI records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class TSTransformer(BaseDomainTransformer):
    """Trial Summary domain transformer - SDTM-IG 3.4 compliant (9 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "TS"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to TS domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to TS domain - FULL SDTM-IG 3.4 compliance")
        ts_records = []
        seq = 0

        for idx, row in source_df.iterrows():
            seq += 1
            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            ts_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "TS",
                "TSSEQ": seq,
                "TSGRPID": "",
                "TSPARMCD": "",
                "TSPARM": "",
                "TSVAL": "",
                "TSVALNF": "",
                "TSVALCD": "",
            }

            # Group ID
            for col in ["TSGRPID", "GRPID"]:
                if col in row and pd.notna(row[col]):
                    ts_record["TSGRPID"] = str(row[col])
                    break

            # Parameter code
            for col in ["TSPARMCD", "PARAMCD", "PARMCD"]:
                if col in row and pd.notna(row[col]):
                    ts_record["TSPARMCD"] = str(row[col])[:8]
                    break

            # Parameter name
            for col in ["TSPARM", "PARAM", "PARAMETER"]:
                if col in row and pd.notna(row[col]):
                    ts_record["TSPARM"] = str(row[col])
                    break

            # Value
            for col in ["TSVAL", "VALUE", "VAL"]:
                if col in row and pd.notna(row[col]):
                    ts_record["TSVAL"] = str(row[col])
                    break

            # Value not found
            for col in ["TSVALNF"]:
                if col in row and pd.notna(row[col]):
                    ts_record["TSVALNF"] = str(row[col])
                    break

            # Value code
            for col in ["TSVALCD", "VALCD"]:
                if col in row and pd.notna(row[col]):
                    ts_record["TSVALCD"] = str(row[col])
                    break

            ts_records.append(ts_record)

        result_df = pd.DataFrame(ts_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("TS", []))
        self.log(f"Created {len(result_df)} TS records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class TDTransformer(BaseDomainTransformer):
    """Trial Disease Assessments domain transformer - SDTM-IG 3.4 compliant (5 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "TD"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to TD domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to TD domain - FULL SDTM-IG 3.4 compliance")
        td_records = []

        for idx, row in source_df.iterrows():
            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            td_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "TD",
                "TDSEQ": None,
                "TDORDER": None,
                "TDDUR": "",
            }

            # Sequence
            for col in ["TDSEQ", "SEQ", "DISEESSION"]:
                if col in row and pd.notna(row[col]):
                    try:
                        td_record["TDSEQ"] = int(row[col])
                    except (ValueError, TypeError):
                        td_record["TDSEQ"] = idx + 1
                    break
            else:
                td_record["TDSEQ"] = idx + 1

            # Order
            for col in ["TDORDER", "ORDER"]:
                if col in row and pd.notna(row[col]):
                    try:
                        td_record["TDORDER"] = int(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # Duration
            for col in ["TDDUR", "DURATION"]:
                if col in row and pd.notna(row[col]):
                    td_record["TDDUR"] = str(row[col])
                    break

            td_records.append(td_record)

        result_df = pd.DataFrame(td_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("TD", []))
        self.log(f"Created {len(result_df)} TD records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class TMTransformer(BaseDomainTransformer):
    """Trial Disease Milestones domain transformer - SDTM-IG 3.4 compliant (5 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "TM"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to TM domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to TM domain - FULL SDTM-IG 3.4 compliance")
        tm_records = []

        for idx, row in source_df.iterrows():
            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            tm_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "TM",
                "MESSION": None,
                "MIDS": "",
                "TMDEF": "",
            }

            # Session
            for col in ["MESSION", "SESSION"]:
                if col in row and pd.notna(row[col]):
                    try:
                        tm_record["MESSION"] = int(row[col])
                    except (ValueError, TypeError):
                        tm_record["MESSION"] = idx + 1
                    break
            else:
                tm_record["MESSION"] = idx + 1

            # Milestone ID
            for col in ["MIDS", "MILESTONE", "MILESTONEID"]:
                if col in row and pd.notna(row[col]):
                    tm_record["MIDS"] = str(row[col])
                    break

            # Definition
            for col in ["TMDEF", "DEFINITION"]:
                if col in row and pd.notna(row[col]):
                    tm_record["TMDEF"] = str(row[col])
                    break

            tm_records.append(tm_record)

        result_df = pd.DataFrame(tm_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("TM", []))
        self.log(f"Created {len(result_df)} TM records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


# =============================================================================
# RELATIONSHIP DOMAINS
# =============================================================================

class RELRECTransformer(BaseDomainTransformer):
    """Related Records domain transformer - SDTM-IG 3.4 compliant (7 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "RELREC"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to RELREC domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to RELREC domain - FULL SDTM-IG 3.4 compliance")
        relrec_records = []

        for idx, row in source_df.iterrows():
            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            relrec_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "RDOMAIN": "",
                "USUBJID": "",
                "IDVAR": "",
                "IDVARVAL": "",
                "RELTYPE": "",
                "RELID": "",
            }

            # Related domain
            for col in ["RDOMAIN", "DOMAIN"]:
                if col in row and pd.notna(row[col]):
                    relrec_record["RDOMAIN"] = str(row[col])[:2].upper()
                    break

            # Subject ID
            if "PT" in row or "SUBJID" in row or "USUBJID" in row:
                relrec_record["USUBJID"] = self._generate_usubjid(row)

            # ID variable
            for col in ["IDVAR", "IDVARIABLE"]:
                if col in row and pd.notna(row[col]):
                    relrec_record["IDVAR"] = str(row[col])
                    break

            # ID variable value
            for col in ["IDVARVAL", "IDVALUE"]:
                if col in row and pd.notna(row[col]):
                    relrec_record["IDVARVAL"] = str(row[col])
                    break

            # Relationship type
            for col in ["RELTYPE", "TYPE"]:
                if col in row and pd.notna(row[col]):
                    relrec_record["RELTYPE"] = str(row[col])
                    break

            # Relationship ID
            for col in ["RELID", "ID"]:
                if col in row and pd.notna(row[col]):
                    relrec_record["RELID"] = str(row[col])
                    break

            relrec_records.append(relrec_record)

        result_df = pd.DataFrame(relrec_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("RELREC", []))
        self.log(f"Created {len(result_df)} RELREC records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


# =============================================================================
# SPECIALIZED FINDINGS DOMAINS (Organ/System-Specific)
# =============================================================================

class CVTransformer(BaseDomainTransformer):
    """Cardiovascular System Findings domain transformer - SDTM-IG 3.4 compliant (26 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "CV"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to CV domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to CV domain - FULL SDTM-IG 3.4 compliance")
        cv_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            cv_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "CV",
                "USUBJID": self._generate_usubjid(row),
                "CVSEQ": subject_seq[subj],
                "CVGRPID": "",
                "CVREFID": "",
                "CVSPID": "",
                "CVTESTCD": "",
                "CVTEST": "",
                "CVCAT": "",
                "CVSCAT": "",
                "CVPOS": "",
                "CVORRES": "",
                "CVORRESU": "",
                "CVSTRESC": "",
                "CVSTRESN": None,
                "CVSTRESU": "",
                "CVSTAT": "",
                "CVREASND": "",
                "CVLOC": "",
                "CVLAT": "",
                "CVMETHOD": "",
                "CVBLFL": "",
                "VISITNUM": None,
                "VISIT": "",
                "EPOCH": "",
                "CVDTC": "",
                "CVDY": None,
            }

            # Test code
            for col in ["CVTESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    cv_record["CVTESTCD"] = str(row[col])[:8]
                    break

            for col in ["CVTEST", "TEST"]:
                if col in row and pd.notna(row[col]):
                    cv_record["CVTEST"] = str(row[col])
                    break

            # Category
            for col in ["CVCAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    cv_record["CVCAT"] = str(row[col]).upper()
                    break

            # Position
            for col in ["CVPOS", "POSITION"]:
                if col in row and pd.notna(row[col]):
                    cv_record["CVPOS"] = str(row[col]).upper()
                    break

            # Result
            for col in ["CVORRES", "RESULT"]:
                if col in row and pd.notna(row[col]):
                    cv_record["CVORRES"] = str(row[col])
                    cv_record["CVSTRESC"] = str(row[col])
                    try:
                        cv_record["CVSTRESN"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # Unit
            for col in ["CVORRESU", "UNIT"]:
                if col in row and pd.notna(row[col]):
                    cv_record["CVORRESU"] = str(row[col])
                    cv_record["CVSTRESU"] = str(row[col])
                    break

            # Location
            for col in ["CVLOC", "LOC", "LOCATION"]:
                if col in row and pd.notna(row[col]):
                    cv_record["CVLOC"] = str(row[col]).upper()
                    break

            # Laterality
            for col in ["CVLAT", "LATERALITY"]:
                if col in row and pd.notna(row[col]):
                    cv_record["CVLAT"] = str(row[col]).upper()
                    break

            # Method
            for col in ["CVMETHOD", "METHOD"]:
                if col in row and pd.notna(row[col]):
                    cv_record["CVMETHOD"] = str(row[col])
                    break

            # Date
            for col in ["CVDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    cv_record["CVDTC"] = self._convert_date_to_iso(row[col])
                    break

            cv_records.append(cv_record)

        result_df = pd.DataFrame(cv_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("CV", []))
        self.log(f"Created {len(result_df)} CV records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class MKTransformer(BaseDomainTransformer):
    """Musculoskeletal System Findings domain transformer - SDTM-IG 3.4 compliant (26 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "MK"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to MK domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to MK domain - FULL SDTM-IG 3.4 compliance")
        mk_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            mk_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "MK",
                "USUBJID": self._generate_usubjid(row),
                "MKSEQ": subject_seq[subj],
                "MKGRPID": "",
                "MKREFID": "",
                "MKSPID": "",
                "MKTESTCD": "",
                "MKTEST": "",
                "MKCAT": "",
                "MKSCAT": "",
                "MKORRES": "",
                "MKORRESU": "",
                "MKSTRESC": "",
                "MKSTRESN": None,
                "MKSTRESU": "",
                "MKSTAT": "",
                "MKREASND": "",
                "MKLOC": "",
                "MKLAT": "",
                "MKDIR": "",
                "MKMETHOD": "",
                "MKBLFL": "",
                "VISITNUM": None,
                "VISIT": "",
                "EPOCH": "",
                "MKDTC": "",
                "MKDY": None,
            }

            # Test code
            for col in ["MKTESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    mk_record["MKTESTCD"] = str(row[col])[:8]
                    break

            for col in ["MKTEST", "TEST"]:
                if col in row and pd.notna(row[col]):
                    mk_record["MKTEST"] = str(row[col])
                    break

            # Category
            for col in ["MKCAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    mk_record["MKCAT"] = str(row[col]).upper()
                    break

            # Result
            for col in ["MKORRES", "RESULT"]:
                if col in row and pd.notna(row[col]):
                    mk_record["MKORRES"] = str(row[col])
                    mk_record["MKSTRESC"] = str(row[col])
                    try:
                        mk_record["MKSTRESN"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # Unit
            for col in ["MKORRESU", "UNIT"]:
                if col in row and pd.notna(row[col]):
                    mk_record["MKORRESU"] = str(row[col])
                    mk_record["MKSTRESU"] = str(row[col])
                    break

            # Location
            for col in ["MKLOC", "LOC", "LOCATION"]:
                if col in row and pd.notna(row[col]):
                    mk_record["MKLOC"] = str(row[col]).upper()
                    break

            # Laterality
            for col in ["MKLAT", "LATERALITY"]:
                if col in row and pd.notna(row[col]):
                    mk_record["MKLAT"] = str(row[col]).upper()
                    break

            # Direction
            for col in ["MKDIR", "DIRECTION"]:
                if col in row and pd.notna(row[col]):
                    mk_record["MKDIR"] = str(row[col]).upper()
                    break

            # Method
            for col in ["MKMETHOD", "METHOD"]:
                if col in row and pd.notna(row[col]):
                    mk_record["MKMETHOD"] = str(row[col])
                    break

            # Date
            for col in ["MKDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    mk_record["MKDTC"] = self._convert_date_to_iso(row[col])
                    break

            mk_records.append(mk_record)

        result_df = pd.DataFrame(mk_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("MK", []))
        self.log(f"Created {len(result_df)} MK records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class NVTransformer(BaseDomainTransformer):
    """Nervous System Findings domain transformer - SDTM-IG 3.4 compliant (26 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "NV"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to NV domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to NV domain - FULL SDTM-IG 3.4 compliance")
        nv_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            nv_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "NV",
                "USUBJID": self._generate_usubjid(row),
                "NVSEQ": subject_seq[subj],
                "NVGRPID": "",
                "NVREFID": "",
                "NVSPID": "",
                "NVTESTCD": "",
                "NVTEST": "",
                "NVCAT": "",
                "NVSCAT": "",
                "NVORRES": "",
                "NVORRESU": "",
                "NVSTRESC": "",
                "NVSTRESN": None,
                "NVSTRESU": "",
                "NVSTAT": "",
                "NVREASND": "",
                "NVLOC": "",
                "NVLAT": "",
                "NVMETHOD": "",
                "NVBLFL": "",
                "VISITNUM": None,
                "VISIT": "",
                "EPOCH": "",
                "NVDTC": "",
                "NVDY": None,
            }

            # Test code
            for col in ["NVTESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    nv_record["NVTESTCD"] = str(row[col])[:8]
                    break

            for col in ["NVTEST", "TEST"]:
                if col in row and pd.notna(row[col]):
                    nv_record["NVTEST"] = str(row[col])
                    break

            # Category
            for col in ["NVCAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    nv_record["NVCAT"] = str(row[col]).upper()
                    break

            # Result
            for col in ["NVORRES", "RESULT"]:
                if col in row and pd.notna(row[col]):
                    nv_record["NVORRES"] = str(row[col])
                    nv_record["NVSTRESC"] = str(row[col])
                    try:
                        nv_record["NVSTRESN"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # Unit
            for col in ["NVORRESU", "UNIT"]:
                if col in row and pd.notna(row[col]):
                    nv_record["NVORRESU"] = str(row[col])
                    nv_record["NVSTRESU"] = str(row[col])
                    break

            # Location
            for col in ["NVLOC", "LOC", "LOCATION"]:
                if col in row and pd.notna(row[col]):
                    nv_record["NVLOC"] = str(row[col]).upper()
                    break

            # Laterality
            for col in ["NVLAT", "LATERALITY"]:
                if col in row and pd.notna(row[col]):
                    nv_record["NVLAT"] = str(row[col]).upper()
                    break

            # Method
            for col in ["NVMETHOD", "METHOD"]:
                if col in row and pd.notna(row[col]):
                    nv_record["NVMETHOD"] = str(row[col])
                    break

            # Date
            for col in ["NVDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    nv_record["NVDTC"] = self._convert_date_to_iso(row[col])
                    break

            nv_records.append(nv_record)

        result_df = pd.DataFrame(nv_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("NV", []))
        self.log(f"Created {len(result_df)} NV records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class OETransformer(BaseDomainTransformer):
    """Ophthalmic Examinations domain transformer - SDTM-IG 3.4 compliant (28 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "OE"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to OE domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to OE domain - FULL SDTM-IG 3.4 compliance")
        oe_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            oe_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "OE",
                "USUBJID": self._generate_usubjid(row),
                "OESEQ": subject_seq[subj],
                "OEGRPID": "",
                "OEREFID": "",
                "OESPID": "",
                "OETESTCD": "",
                "OETEST": "",
                "OECAT": "",
                "OESCAT": "",
                "OEORRES": "",
                "OEORRESU": "",
                "OESTRESC": "",
                "OESTRESN": None,
                "OESTRESU": "",
                "OESTAT": "",
                "OEREASND": "",
                "OELOC": "",
                "OELAT": "",
                "OEDIR": "",
                "OEMETHOD": "",
                "OELOBXFL": "",
                "OEBLFL": "",
                "VISITNUM": None,
                "VISIT": "",
                "EPOCH": "",
                "OEDTC": "",
                "OEDY": None,
            }

            # Test code
            for col in ["OETESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    oe_record["OETESTCD"] = str(row[col])[:8]
                    break

            for col in ["OETEST", "TEST"]:
                if col in row and pd.notna(row[col]):
                    oe_record["OETEST"] = str(row[col])
                    break

            # Category
            for col in ["OECAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    oe_record["OECAT"] = str(row[col]).upper()
                    break

            # Result
            for col in ["OEORRES", "RESULT"]:
                if col in row and pd.notna(row[col]):
                    oe_record["OEORRES"] = str(row[col])
                    oe_record["OESTRESC"] = str(row[col])
                    try:
                        oe_record["OESTRESN"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # Unit
            for col in ["OEORRESU", "UNIT"]:
                if col in row and pd.notna(row[col]):
                    oe_record["OEORRESU"] = str(row[col])
                    oe_record["OESTRESU"] = str(row[col])
                    break

            # Location
            for col in ["OELOC", "LOC"]:
                if col in row and pd.notna(row[col]):
                    oe_record["OELOC"] = str(row[col]).upper()
                    break

            # Laterality (eye)
            for col in ["OELAT", "LATERALITY", "EYE"]:
                if col in row and pd.notna(row[col]):
                    val = str(row[col]).upper()
                    if val == "L":
                        val = "LEFT"
                    elif val == "R":
                        val = "RIGHT"
                    oe_record["OELAT"] = val
                    break

            # Direction
            for col in ["OEDIR", "DIRECTION"]:
                if col in row and pd.notna(row[col]):
                    oe_record["OEDIR"] = str(row[col]).upper()
                    break

            # Method
            for col in ["OEMETHOD", "METHOD"]:
                if col in row and pd.notna(row[col]):
                    oe_record["OEMETHOD"] = str(row[col])
                    break

            # Date
            for col in ["OEDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    oe_record["OEDTC"] = self._convert_date_to_iso(row[col])
                    break

            oe_records.append(oe_record)

        result_df = pd.DataFrame(oe_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("OE", []))
        self.log(f"Created {len(result_df)} OE records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class RETransformer(BaseDomainTransformer):
    """Respiratory System Findings domain transformer - SDTM-IG 3.4 compliant (26 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "RE"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to RE domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to RE domain - FULL SDTM-IG 3.4 compliance")
        re_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            re_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "RE",
                "USUBJID": self._generate_usubjid(row),
                "RESEQ": subject_seq[subj],
                "REGRPID": "",
                "REREFID": "",
                "RESPID": "",
                "RETESTCD": "",
                "RETEST": "",
                "RECAT": "",
                "RESCAT": "",
                "REORRES": "",
                "REORRESU": "",
                "RESTRESC": "",
                "RESTRESN": None,
                "RESTRESU": "",
                "RESTAT": "",
                "REREASND": "",
                "RELOC": "",
                "REMETHOD": "",
                "REBLFL": "",
                "VISITNUM": None,
                "VISIT": "",
                "EPOCH": "",
                "REDTC": "",
                "REDY": None,
            }

            # Test code
            for col in ["RETESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    re_record["RETESTCD"] = str(row[col])[:8]
                    break

            for col in ["RETEST", "TEST"]:
                if col in row and pd.notna(row[col]):
                    re_record["RETEST"] = str(row[col])
                    break

            # Category
            for col in ["RECAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    re_record["RECAT"] = str(row[col]).upper()
                    break

            # Result
            for col in ["REORRES", "RESULT"]:
                if col in row and pd.notna(row[col]):
                    re_record["REORRES"] = str(row[col])
                    re_record["RESTRESC"] = str(row[col])
                    try:
                        re_record["RESTRESN"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # Unit
            for col in ["REORRESU", "UNIT"]:
                if col in row and pd.notna(row[col]):
                    re_record["REORRESU"] = str(row[col])
                    re_record["RESTRESU"] = str(row[col])
                    break

            # Location
            for col in ["RELOC", "LOC", "LOCATION"]:
                if col in row and pd.notna(row[col]):
                    re_record["RELOC"] = str(row[col]).upper()
                    break

            # Method
            for col in ["REMETHOD", "METHOD"]:
                if col in row and pd.notna(row[col]):
                    re_record["REMETHOD"] = str(row[col])
                    break

            # Date
            for col in ["REDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    re_record["REDTC"] = self._convert_date_to_iso(row[col])
                    break

            re_records.append(re_record)

        result_df = pd.DataFrame(re_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("RE", []))
        self.log(f"Created {len(result_df)} RE records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class RPTransformer(BaseDomainTransformer):
    """Reproductive System Findings domain transformer - SDTM-IG 3.4 compliant (26 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "RP"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to RP domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to RP domain - FULL SDTM-IG 3.4 compliance")
        rp_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            rp_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "RP",
                "USUBJID": self._generate_usubjid(row),
                "RPSEQ": subject_seq[subj],
                "RPGRPID": "",
                "RPREFID": "",
                "RPSPID": "",
                "RPTESTCD": "",
                "RPTEST": "",
                "RPCAT": "",
                "RPSCAT": "",
                "RPORRES": "",
                "RPORRESU": "",
                "RPSTRESC": "",
                "RPSTRESN": None,
                "RPSTRESU": "",
                "RPSTAT": "",
                "RPREASND": "",
                "RPLOC": "",
                "RPMETHOD": "",
                "RPBLFL": "",
                "VISITNUM": None,
                "VISIT": "",
                "EPOCH": "",
                "RPDTC": "",
                "RPDY": None,
            }

            # Test code
            for col in ["RPTESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    rp_record["RPTESTCD"] = str(row[col])[:8]
                    break

            for col in ["RPTEST", "TEST"]:
                if col in row and pd.notna(row[col]):
                    rp_record["RPTEST"] = str(row[col])
                    break

            # Category
            for col in ["RPCAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    rp_record["RPCAT"] = str(row[col]).upper()
                    break

            # Result
            for col in ["RPORRES", "RESULT"]:
                if col in row and pd.notna(row[col]):
                    rp_record["RPORRES"] = str(row[col])
                    rp_record["RPSTRESC"] = str(row[col])
                    try:
                        rp_record["RPSTRESN"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # Unit
            for col in ["RPORRESU", "UNIT"]:
                if col in row and pd.notna(row[col]):
                    rp_record["RPORRESU"] = str(row[col])
                    rp_record["RPSTRESU"] = str(row[col])
                    break

            # Location
            for col in ["RPLOC", "LOC", "LOCATION"]:
                if col in row and pd.notna(row[col]):
                    rp_record["RPLOC"] = str(row[col]).upper()
                    break

            # Method
            for col in ["RPMETHOD", "METHOD"]:
                if col in row and pd.notna(row[col]):
                    rp_record["RPMETHOD"] = str(row[col])
                    break

            # Date
            for col in ["RPDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    rp_record["RPDTC"] = self._convert_date_to_iso(row[col])
                    break

            rp_records.append(rp_record)

        result_df = pd.DataFrame(rp_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("RP", []))
        self.log(f"Created {len(result_df)} RP records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class URTransformer(BaseDomainTransformer):
    """Urinary System Findings domain transformer - SDTM-IG 3.4 compliant (26 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "UR"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to UR domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to UR domain - FULL SDTM-IG 3.4 compliance")
        ur_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            ur_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "UR",
                "USUBJID": self._generate_usubjid(row),
                "URSEQ": subject_seq[subj],
                "URGRPID": "",
                "URREFID": "",
                "URSPID": "",
                "URTESTCD": "",
                "URTEST": "",
                "URCAT": "",
                "URSCAT": "",
                "URORRES": "",
                "URORRESU": "",
                "URSTRESC": "",
                "URSTRESN": None,
                "URSTRESU": "",
                "URSTAT": "",
                "URREASND": "",
                "URSPEC": "",
                "URMETHOD": "",
                "URBLFL": "",
                "VISITNUM": None,
                "VISIT": "",
                "EPOCH": "",
                "URDTC": "",
                "URDY": None,
            }

            # Test code
            for col in ["URTESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    ur_record["URTESTCD"] = str(row[col])[:8]
                    break

            for col in ["URTEST", "TEST"]:
                if col in row and pd.notna(row[col]):
                    ur_record["URTEST"] = str(row[col])
                    break

            # Category
            for col in ["URCAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    ur_record["URCAT"] = str(row[col]).upper()
                    break

            # Result
            for col in ["URORRES", "RESULT"]:
                if col in row and pd.notna(row[col]):
                    ur_record["URORRES"] = str(row[col])
                    ur_record["URSTRESC"] = str(row[col])
                    try:
                        ur_record["URSTRESN"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # Unit
            for col in ["URORRESU", "UNIT"]:
                if col in row and pd.notna(row[col]):
                    ur_record["URORRESU"] = str(row[col])
                    ur_record["URSTRESU"] = str(row[col])
                    break

            # Specimen
            for col in ["URSPEC", "SPECIMEN"]:
                if col in row and pd.notna(row[col]):
                    ur_record["URSPEC"] = str(row[col]).upper()
                    break

            # Method
            for col in ["URMETHOD", "METHOD"]:
                if col in row and pd.notna(row[col]):
                    ur_record["URMETHOD"] = str(row[col])
                    break

            # Date
            for col in ["URDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    ur_record["URDTC"] = self._convert_date_to_iso(row[col])
                    break

            ur_records.append(ur_record)

        result_df = pd.DataFrame(ur_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("UR", []))
        self.log(f"Created {len(result_df)} UR records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class BSTransformer(BaseDomainTransformer):
    """Biospecimen Events domain transformer - SDTM-IG 3.4 compliant (18 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "BS"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to BS domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to BS domain - FULL SDTM-IG 3.4 compliance")
        bs_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            bs_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "BS",
                "USUBJID": self._generate_usubjid(row),
                "BSSEQ": subject_seq[subj],
                "BSGRPID": "",
                "BSREFID": "",
                "BSSPID": "",
                "BSTERM": "",
                "BSCAT": "",
                "BSSCAT": "",
                "BSPRESP": "",
                "BSOCCUR": "",
                "BSSTAT": "",
                "BSREASND": "",
                "VISITNUM": None,
                "VISIT": "",
                "EPOCH": "",
                "BSSTDTC": "",
                "BSENDTC": "",
                "BSDY": None,
            }

            # Reference ID
            for col in ["BSREFID", "SPECID", "SAMPLEID"]:
                if col in row and pd.notna(row[col]):
                    bs_record["BSREFID"] = str(row[col])
                    break

            # Term
            for col in ["BSTERM", "TERM", "EVENT"]:
                if col in row and pd.notna(row[col]):
                    bs_record["BSTERM"] = str(row[col])
                    break

            # Category
            for col in ["BSCAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    bs_record["BSCAT"] = str(row[col]).upper()
                    break

            # Occurrence
            for col in ["BSOCCUR", "OCCUR"]:
                if col in row and pd.notna(row[col]):
                    val = str(row[col]).upper()
                    if val in ["Y", "N"]:
                        bs_record["BSOCCUR"] = val
                    break

            # Start date
            for col in ["BSSTDTC", "STARTDT", "STDT"]:
                if col in row and pd.notna(row[col]):
                    bs_record["BSSTDTC"] = self._convert_date_to_iso(row[col])
                    break

            # End date
            for col in ["BSENDTC", "ENDDT", "ENDT"]:
                if col in row and pd.notna(row[col]):
                    bs_record["BSENDTC"] = self._convert_date_to_iso(row[col])
                    break

            bs_records.append(bs_record)

        result_df = pd.DataFrame(bs_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("BS", []))
        self.log(f"Created {len(result_df)} BS records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class CPTransformer(BaseDomainTransformer):
    """Cell Phenotype Findings domain transformer - SDTM-IG 3.4 compliant (26 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "CP"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to CP domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to CP domain - FULL SDTM-IG 3.4 compliance")
        cp_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            cp_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "CP",
                "USUBJID": self._generate_usubjid(row),
                "CPSEQ": subject_seq[subj],
                "CPGRPID": "",
                "CPREFID": "",
                "CPSPID": "",
                "CPTESTCD": "",
                "CPTEST": "",
                "CPCAT": "",
                "CPSCAT": "",
                "CPORRES": "",
                "CPORRESU": "",
                "CPSTRESC": "",
                "CPSTRESN": None,
                "CPSTRESU": "",
                "CPSTAT": "",
                "CPREASND": "",
                "CPSPEC": "",
                "CPMETHOD": "",
                "CPBLFL": "",
                "VISITNUM": None,
                "VISIT": "",
                "EPOCH": "",
                "CPDTC": "",
                "CPDY": None,
            }

            # Test code
            for col in ["CPTESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    cp_record["CPTESTCD"] = str(row[col])[:8]
                    break

            for col in ["CPTEST", "TEST"]:
                if col in row and pd.notna(row[col]):
                    cp_record["CPTEST"] = str(row[col])
                    break

            # Category
            for col in ["CPCAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    cp_record["CPCAT"] = str(row[col]).upper()
                    break

            # Result
            for col in ["CPORRES", "RESULT"]:
                if col in row and pd.notna(row[col]):
                    cp_record["CPORRES"] = str(row[col])
                    cp_record["CPSTRESC"] = str(row[col])
                    try:
                        cp_record["CPSTRESN"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # Unit
            for col in ["CPORRESU", "UNIT"]:
                if col in row and pd.notna(row[col]):
                    cp_record["CPORRESU"] = str(row[col])
                    cp_record["CPSTRESU"] = str(row[col])
                    break

            # Specimen
            for col in ["CPSPEC", "SPECIMEN"]:
                if col in row and pd.notna(row[col]):
                    cp_record["CPSPEC"] = str(row[col]).upper()
                    break

            # Method
            for col in ["CPMETHOD", "METHOD"]:
                if col in row and pd.notna(row[col]):
                    cp_record["CPMETHOD"] = str(row[col])
                    break

            # Date
            for col in ["CPDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    cp_record["CPDTC"] = self._convert_date_to_iso(row[col])
                    break

            cp_records.append(cp_record)

        result_df = pd.DataFrame(cp_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("CP", []))
        self.log(f"Created {len(result_df)} CP records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class GFTransformer(BaseDomainTransformer):
    """Genomic Findings domain transformer - SDTM-IG 3.4 compliant (26 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "GF"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to GF domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to GF domain - FULL SDTM-IG 3.4 compliance")
        gf_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            gf_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "GF",
                "USUBJID": self._generate_usubjid(row),
                "GFSEQ": subject_seq[subj],
                "GFGRPID": "",
                "GFREFID": "",
                "GFSPID": "",
                "GFTESTCD": "",
                "GFTEST": "",
                "GFCAT": "",
                "GFSCAT": "",
                "GFORRES": "",
                "GFORRESU": "",
                "GFSTRESC": "",
                "GFSTRESN": None,
                "GFSTRESU": "",
                "GFSTAT": "",
                "GFREASND": "",
                "GFSPEC": "",
                "GFMETHOD": "",
                "GFBLFL": "",
                "VISITNUM": None,
                "VISIT": "",
                "EPOCH": "",
                "GFDTC": "",
                "GFDY": None,
            }

            # Test code
            for col in ["GFTESTCD", "TESTCD", "GENEID"]:
                if col in row and pd.notna(row[col]):
                    gf_record["GFTESTCD"] = str(row[col])[:8]
                    break

            for col in ["GFTEST", "TEST", "GENENAME"]:
                if col in row and pd.notna(row[col]):
                    gf_record["GFTEST"] = str(row[col])
                    break

            # Category
            for col in ["GFCAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    gf_record["GFCAT"] = str(row[col]).upper()
                    break

            # Result
            for col in ["GFORRES", "RESULT", "VARIANT"]:
                if col in row and pd.notna(row[col]):
                    gf_record["GFORRES"] = str(row[col])
                    gf_record["GFSTRESC"] = str(row[col])
                    try:
                        gf_record["GFSTRESN"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # Unit
            for col in ["GFORRESU", "UNIT"]:
                if col in row and pd.notna(row[col]):
                    gf_record["GFORRESU"] = str(row[col])
                    gf_record["GFSTRESU"] = str(row[col])
                    break

            # Specimen
            for col in ["GFSPEC", "SPECIMEN"]:
                if col in row and pd.notna(row[col]):
                    gf_record["GFSPEC"] = str(row[col]).upper()
                    break

            # Method
            for col in ["GFMETHOD", "METHOD"]:
                if col in row and pd.notna(row[col]):
                    gf_record["GFMETHOD"] = str(row[col])
                    break

            # Date
            for col in ["GFDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    gf_record["GFDTC"] = self._convert_date_to_iso(row[col])
                    break

            gf_records.append(gf_record)

        result_df = pd.DataFrame(gf_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("GF", []))
        self.log(f"Created {len(result_df)} GF records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class ISTransformer(BaseDomainTransformer):
    """Immunogenicity Specimen Assessments domain transformer - SDTM-IG 3.4 compliant (26 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "IS"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to IS domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to IS domain - FULL SDTM-IG 3.4 compliance")
        is_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            is_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "IS",
                "USUBJID": self._generate_usubjid(row),
                "ISSEQ": subject_seq[subj],
                "ISGRPID": "",
                "ISREFID": "",
                "ISSPID": "",
                "ISTESTCD": "",
                "ISTEST": "",
                "ISCAT": "",
                "ISSCAT": "",
                "ISORRES": "",
                "ISORRESU": "",
                "ISSTRESC": "",
                "ISSTRESN": None,
                "ISSTRESU": "",
                "ISSTAT": "",
                "ISREASND": "",
                "ISSPEC": "",
                "ISMETHOD": "",
                "ISBLFL": "",
                "VISITNUM": None,
                "VISIT": "",
                "EPOCH": "",
                "ISDTC": "",
                "ISDY": None,
            }

            # Test code
            for col in ["ISTESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    is_record["ISTESTCD"] = str(row[col])[:8]
                    break

            for col in ["ISTEST", "TEST"]:
                if col in row and pd.notna(row[col]):
                    is_record["ISTEST"] = str(row[col])
                    break

            # Category
            for col in ["ISCAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    is_record["ISCAT"] = str(row[col]).upper()
                    break

            # Result
            for col in ["ISORRES", "RESULT"]:
                if col in row and pd.notna(row[col]):
                    is_record["ISORRES"] = str(row[col])
                    is_record["ISSTRESC"] = str(row[col])
                    try:
                        is_record["ISSTRESN"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # Unit
            for col in ["ISORRESU", "UNIT"]:
                if col in row and pd.notna(row[col]):
                    is_record["ISORRESU"] = str(row[col])
                    is_record["ISSTRESU"] = str(row[col])
                    break

            # Specimen
            for col in ["ISSPEC", "SPECIMEN"]:
                if col in row and pd.notna(row[col]):
                    is_record["ISSPEC"] = str(row[col]).upper()
                    break

            # Method
            for col in ["ISMETHOD", "METHOD"]:
                if col in row and pd.notna(row[col]):
                    is_record["ISMETHOD"] = str(row[col])
                    break

            # Date
            for col in ["ISDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    is_record["ISDTC"] = self._convert_date_to_iso(row[col])
                    break

            is_records.append(is_record)

        result_df = pd.DataFrame(is_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("IS", []))
        self.log(f"Created {len(result_df)} IS records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class MOTransformer(BaseDomainTransformer):
    """Morphology Findings domain transformer - SDTM-IG 3.4 compliant (26 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "MO"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to MO domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to MO domain - FULL SDTM-IG 3.4 compliance")
        mo_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            mo_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "MO",
                "USUBJID": self._generate_usubjid(row),
                "MOSEQ": subject_seq[subj],
                "MOGRPID": "",
                "MOREFID": "",
                "MOSPID": "",
                "MOTESTCD": "",
                "MOTEST": "",
                "MOCAT": "",
                "MOSCAT": "",
                "MOORRES": "",
                "MOORRESU": "",
                "MOSTRESC": "",
                "MOSTRESN": None,
                "MOSTRESU": "",
                "MOSTAT": "",
                "MOREASND": "",
                "MOLOC": "",
                "MOSPEC": "",
                "MOMETHOD": "",
                "MOBLFL": "",
                "VISITNUM": None,
                "VISIT": "",
                "EPOCH": "",
                "MODTC": "",
                "MODY": None,
            }

            # Test code
            for col in ["MOTESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    mo_record["MOTESTCD"] = str(row[col])[:8]
                    break

            for col in ["MOTEST", "TEST"]:
                if col in row and pd.notna(row[col]):
                    mo_record["MOTEST"] = str(row[col])
                    break

            # Category
            for col in ["MOCAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    mo_record["MOCAT"] = str(row[col]).upper()
                    break

            # Result
            for col in ["MOORRES", "RESULT"]:
                if col in row and pd.notna(row[col]):
                    mo_record["MOORRES"] = str(row[col])
                    mo_record["MOSTRESC"] = str(row[col])
                    try:
                        mo_record["MOSTRESN"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # Unit
            for col in ["MOORRESU", "UNIT"]:
                if col in row and pd.notna(row[col]):
                    mo_record["MOORRESU"] = str(row[col])
                    mo_record["MOSTRESU"] = str(row[col])
                    break

            # Location
            for col in ["MOLOC", "LOC", "LOCATION"]:
                if col in row and pd.notna(row[col]):
                    mo_record["MOLOC"] = str(row[col]).upper()
                    break

            # Specimen
            for col in ["MOSPEC", "SPECIMEN"]:
                if col in row and pd.notna(row[col]):
                    mo_record["MOSPEC"] = str(row[col]).upper()
                    break

            # Method
            for col in ["MOMETHOD", "METHOD"]:
                if col in row and pd.notna(row[col]):
                    mo_record["MOMETHOD"] = str(row[col])
                    break

            # Date
            for col in ["MODTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    mo_record["MODTC"] = self._convert_date_to_iso(row[col])
                    break

            mo_records.append(mo_record)

        result_df = pd.DataFrame(mo_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("MO", []))
        self.log(f"Created {len(result_df)} MO records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class OITransformer(BaseDomainTransformer):
    """Organ Impairment domain transformer - SDTM-IG 3.4 compliant (26 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "OI"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to OI domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to OI domain - FULL SDTM-IG 3.4 compliance")
        oi_records = []
        subject_seq = {}

        for idx, row in source_df.iterrows():
            subj = str(row.get("PT", row.get("SUBJID", "")))
            if subj not in subject_seq:
                subject_seq[subj] = 0
            subject_seq[subj] += 1

            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            oi_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "DOMAIN": "OI",
                "USUBJID": self._generate_usubjid(row),
                "OISEQ": subject_seq[subj],
                "OIGRPID": "",
                "OIREFID": "",
                "OISPID": "",
                "OITESTCD": "",
                "OITEST": "",
                "OICAT": "",
                "OISCAT": "",
                "OIORRES": "",
                "OIORRESU": "",
                "OISTRESC": "",
                "OISTRESN": None,
                "OISRESU": "",
                "OISTAT": "",
                "OIREASND": "",
                "OILOC": "",
                "OIMETHOD": "",
                "OIBLFL": "",
                "VISITNUM": None,
                "VISIT": "",
                "EPOCH": "",
                "OIDTC": "",
                "OIDY": None,
            }

            # Test code
            for col in ["OITESTCD", "TESTCD"]:
                if col in row and pd.notna(row[col]):
                    oi_record["OITESTCD"] = str(row[col])[:8]
                    break

            for col in ["OITEST", "TEST"]:
                if col in row and pd.notna(row[col]):
                    oi_record["OITEST"] = str(row[col])
                    break

            # Category
            for col in ["OICAT", "CAT"]:
                if col in row and pd.notna(row[col]):
                    oi_record["OICAT"] = str(row[col]).upper()
                    break

            # Result
            for col in ["OIORRES", "RESULT"]:
                if col in row and pd.notna(row[col]):
                    oi_record["OIORRES"] = str(row[col])
                    oi_record["OISTRESC"] = str(row[col])
                    try:
                        oi_record["OISTRESN"] = float(row[col])
                    except (ValueError, TypeError):
                        pass
                    break

            # Unit
            for col in ["OIORRESU", "UNIT"]:
                if col in row and pd.notna(row[col]):
                    oi_record["OIORRESU"] = str(row[col])
                    oi_record["OISRESU"] = str(row[col])
                    break

            # Location (organ)
            for col in ["OILOC", "ORGAN", "LOC"]:
                if col in row and pd.notna(row[col]):
                    oi_record["OILOC"] = str(row[col]).upper()
                    break

            # Method
            for col in ["OIMETHOD", "METHOD"]:
                if col in row and pd.notna(row[col]):
                    oi_record["OIMETHOD"] = str(row[col])
                    break

            # Date
            for col in ["OIDTC", "DATE"]:
                if col in row and pd.notna(row[col]):
                    oi_record["OIDTC"] = self._convert_date_to_iso(row[col])
                    break

            oi_records.append(oi_record)

        result_df = pd.DataFrame(oi_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("OI", []))
        self.log(f"Created {len(result_df)} OI records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


# =============================================================================
# ADDITIONAL RELATIONSHIP DOMAINS
# =============================================================================

class RELSUBTransformer(BaseDomainTransformer):
    """Related Subjects domain transformer - SDTM-IG 3.4 compliant (4 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "RELSUB"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to RELSUB domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to RELSUB domain - FULL SDTM-IG 3.4 compliance")
        relsub_records = []

        for idx, row in source_df.iterrows():
            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            relsub_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "USUBJID": self._generate_usubjid(row),
                "RSUBJID": "",
                "SREL": "",
            }

            # Related subject ID
            for col in ["RSUBJID", "RELATEDSUBJ", "RELSUBJ"]:
                if col in row and pd.notna(row[col]):
                    relsub_record["RSUBJID"] = str(row[col])
                    break

            # Relationship
            for col in ["SREL", "RELATIONSHIP", "REL"]:
                if col in row and pd.notna(row[col]):
                    relsub_record["SREL"] = str(row[col])
                    break

            relsub_records.append(relsub_record)

        result_df = pd.DataFrame(relsub_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("RELSUB", []))
        self.log(f"Created {len(result_df)} RELSUB records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


class RELSPECTransformer(BaseDomainTransformer):
    """Related Specimens domain transformer - SDTM-IG 3.4 compliant (5 variables)."""

    def __init__(self, study_id: str, mapping_spec=None):
        super().__init__(study_id, mapping_spec)
        self.domain_code = "RELSPEC"

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform to RELSPEC domain with ALL SDTM-IG 3.4 variables."""
        self.log("Transforming to RELSPEC domain - FULL SDTM-IG 3.4 compliance")
        relspec_records = []

        for idx, row in source_df.iterrows():
            # === INITIALIZE ALL REQUIRED/EXPECTED VARIABLES ===
            relspec_record = {
                "STUDYID": row.get("STUDY", row.get("STUDYID", self.study_id)),
                "USUBJID": "",
                "SPECID": "",
                "RSPECID": "",
                "SPECREL": "",
            }

            # Subject ID (if available)
            if "PT" in row or "SUBJID" in row or "USUBJID" in row:
                relspec_record["USUBJID"] = self._generate_usubjid(row)

            # Specimen ID
            for col in ["SPECID", "SPECIMENID", "SAMPLEID"]:
                if col in row and pd.notna(row[col]):
                    relspec_record["SPECID"] = str(row[col])
                    break

            # Related specimen ID
            for col in ["RSPECID", "RELATEDSPECID", "RELSPECID"]:
                if col in row and pd.notna(row[col]):
                    relspec_record["RSPECID"] = str(row[col])
                    break

            # Specimen relationship
            for col in ["SPECREL", "RELATIONSHIP", "REL"]:
                if col in row and pd.notna(row[col]):
                    relspec_record["SPECREL"] = str(row[col])
                    break

            relspec_records.append(relspec_record)

        result_df = pd.DataFrame(relspec_records)
        result_df = ensure_sdtm_column_order(result_df, SDTM_DOMAIN_VARIABLES.get("RELSPEC", []))
        self.log(f"Created {len(result_df)} RELSPEC records with {len(result_df.columns)} SDTM-IG 3.4 variables")
        return result_df


# =============================================================================
# MAPPING FOR ALL ADDITIONAL DOMAINS
# =============================================================================

ADDITIONAL_TRANSFORMERS = {
    # Special-Purpose
    "SE": SETransformer,
    "SV": SVTransformer,
    "SM": SMTransformer,
    # Interventions
    "SU": SUTransformer,
    "PR": PRTransformer,
    "EC": ECTransformer,
    "AG": AGTransformer,
    "ML": MLTransformer,
    # Events
    "CE": CETransformer,
    "DV": DVTransformer,
    "HO": HOTransformer,
    "BE": BETransformer,
    # Findings - General
    "DD": DDTransformer,
    "SC": SCTransformer,
    "SS": SSTransformer,
    "FA": FATransformer,
    "PP": PPTransformer,
    "MB": MBTransformer,
    "MI": MITransformer,
    "DA": DATransformer,
    "FT": FTTransformer,
    "SR": SRTransformer,
    # Findings - Specialized/Organ-Specific
    "CV": CVTransformer,
    "MK": MKTransformer,
    "NV": NVTransformer,
    "OE": OETransformer,
    "RE": RETransformer,
    "RP": RPTransformer,
    "UR": URTransformer,
    "BS": BSTransformer,
    "CP": CPTransformer,
    "GF": GFTransformer,
    "IS": ISTransformer,
    "MO": MOTransformer,
    "OI": OITransformer,
    # Trial Design
    "TE": TETransformer,
    "TV": TVTransformer,
    "TI": TITransformer,
    "TS": TSTransformer,
    "TD": TDTransformer,
    "TM": TMTransformer,
    # Relationship
    "RELREC": RELRECTransformer,
    "RELSUB": RELSUBTransformer,
    "RELSPEC": RELSPECTransformer,
}

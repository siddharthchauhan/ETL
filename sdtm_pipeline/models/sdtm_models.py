"""
SDTM Data Models
================
Core data structures for SDTM transformation pipeline.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class SDTMDomainType(Enum):
    """Standard SDTM Domain Types"""
    DM = "Demographics"
    AE = "Adverse Events"
    VS = "Vital Signs"
    LB = "Laboratory Test Results"
    CM = "Concomitant Medications"
    EX = "Exposure"
    MH = "Medical History"
    DS = "Disposition"
    SV = "Subject Visits"
    PE = "Physical Examination"


class ValidationSeverity(Enum):
    """Validation issue severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ColumnMapping:
    """Mapping from source column to SDTM variable"""
    source_column: str
    target_variable: str
    transformation: Optional[str] = None
    derivation_rule: Optional[str] = None
    controlled_terminology: Optional[str] = None
    comments: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_column": self.source_column,
            "target_variable": self.target_variable,
            "transformation": self.transformation,
            "derivation_rule": self.derivation_rule,
            "controlled_terminology": self.controlled_terminology,
            "comments": self.comments
        }


@dataclass
class ValidationRule:
    """SDTM Validation Rule"""
    rule_id: str
    rule_type: str  # CDISC, FDA, Custom
    description: str
    severity: ValidationSeverity
    check_expression: str
    domain: Optional[str] = None
    variable: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_type": self.rule_type,
            "description": self.description,
            "severity": self.severity.value,
            "check_expression": self.check_expression,
            "domain": self.domain,
            "variable": self.variable
        }


@dataclass
class ValidationIssue:
    """A single validation issue found in data"""
    rule_id: str
    severity: ValidationSeverity
    message: str
    domain: str
    variable: Optional[str] = None
    record_id: Optional[str] = None
    value: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "domain": self.domain,
            "variable": self.variable,
            "record_id": self.record_id,
            "value": self.value
        }


@dataclass
class ValidationResult:
    """Result of validation check"""
    is_valid: bool
    domain: str
    total_records: int
    issues: List[ValidationIssue] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    validated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        self.error_count = sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)
        self.warning_count = sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)
        self.info_count = sum(1 for i in self.issues if i.severity == ValidationSeverity.INFO)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "domain": self.domain,
            "total_records": self.total_records,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "issues": [i.to_dict() for i in self.issues],
            "validated_at": self.validated_at
        }


@dataclass
class SDTMDomain:
    """SDTM Domain definition"""
    domain_code: str
    domain_name: str
    domain_type: str  # Findings, Events, Interventions, Special Purpose
    description: str
    required_variables: List[str]
    expected_variables: List[str]
    permissible_variables: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain_code": self.domain_code,
            "domain_name": self.domain_name,
            "domain_type": self.domain_type,
            "description": self.description,
            "required_variables": self.required_variables,
            "expected_variables": self.expected_variables,
            "permissible_variables": self.permissible_variables
        }


@dataclass
class MappingSpecification:
    """Complete SDTM mapping specification"""
    study_id: str
    source_domain: str
    target_domain: str
    column_mappings: List[ColumnMapping]
    derivation_rules: Dict[str, str] = field(default_factory=dict)
    controlled_terminologies: Dict[str, List[str]] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    created_by: str = "SDTM Pipeline"
    version: str = "1.0"
    comments: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "study_id": self.study_id,
            "source_domain": self.source_domain,
            "target_domain": self.target_domain,
            "column_mappings": [m.to_dict() for m in self.column_mappings],
            "derivation_rules": self.derivation_rules,
            "controlled_terminologies": self.controlled_terminologies,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "version": self.version,
            "comments": self.comments
        }


@dataclass
class TransformationResult:
    """Result of SDTM transformation"""
    success: bool
    source_domain: str
    target_domain: str
    records_processed: int
    records_output: int
    records_dropped: int = 0
    transformation_log: List[str] = field(default_factory=list)
    output_path: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    transformed_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "source_domain": self.source_domain,
            "target_domain": self.target_domain,
            "records_processed": self.records_processed,
            "records_output": self.records_output,
            "records_dropped": self.records_dropped,
            "transformation_log": self.transformation_log,
            "output_path": self.output_path,
            "errors": self.errors,
            "transformed_at": self.transformed_at
        }


# SDTM Domain Definitions (CDISC SDTM IG 3.4)
SDTM_DOMAINS = {
    "DM": SDTMDomain(
        domain_code="DM",
        domain_name="Demographics",
        domain_type="Special Purpose",
        description="Demographics domain containing subject-level demographic information",
        required_variables=["STUDYID", "DOMAIN", "USUBJID"],
        expected_variables=["SUBJID", "RFSTDTC", "RFENDTC", "SITEID", "BRTHDTC", "AGE",
                          "AGEU", "SEX", "RACE", "ETHNIC", "ARMCD", "ARM", "COUNTRY"]
    ),
    "AE": SDTMDomain(
        domain_code="AE",
        domain_name="Adverse Events",
        domain_type="Events",
        description="Adverse Events domain capturing adverse event data",
        required_variables=["STUDYID", "DOMAIN", "USUBJID", "AESEQ", "AETERM"],
        expected_variables=["AEDECOD", "AEBODSYS", "AESTDTC", "AEENDTC", "AESER",
                          "AESEV", "AEREL", "AEACN", "AEOUT", "AESCONG", "AESDISAB",
                          "AESDTH", "AESHOSP", "AESLIFE", "AESMIE"]
    ),
    "VS": SDTMDomain(
        domain_code="VS",
        domain_name="Vital Signs",
        domain_type="Findings",
        description="Vital Signs domain containing measurements of vital signs",
        required_variables=["STUDYID", "DOMAIN", "USUBJID", "VSSEQ", "VSTESTCD", "VSTEST"],
        expected_variables=["VSORRES", "VSORRESU", "VSSTRESC", "VSSTRESN", "VSSTRESU",
                          "VSSTAT", "VSREASND", "VSLOC", "VSPOS", "VSDTC", "VSDY",
                          "VSTPT", "VSTPTNUM", "VSELTM", "VSTPTREF"]
    ),
    "LB": SDTMDomain(
        domain_code="LB",
        domain_name="Laboratory Test Results",
        domain_type="Findings",
        description="Laboratory domain containing laboratory test results",
        required_variables=["STUDYID", "DOMAIN", "USUBJID", "LBSEQ", "LBTESTCD", "LBTEST"],
        expected_variables=["LBCAT", "LBSCAT", "LBORRES", "LBORRESU", "LBORNRLO",
                          "LBORNRHI", "LBSTRESC", "LBSTRESN", "LBSTRESU", "LBSTNRLO",
                          "LBSTNRHI", "LBNRIND", "LBSTAT", "LBREASND", "LBSPEC",
                          "LBMETHOD", "LBBLFL", "LBFAST", "LBDTC", "LBDY"]
    ),
    "CM": SDTMDomain(
        domain_code="CM",
        domain_name="Concomitant Medications",
        domain_type="Interventions",
        description="Concomitant Medications domain capturing medication usage",
        required_variables=["STUDYID", "DOMAIN", "USUBJID", "CMSEQ", "CMTRT"],
        expected_variables=["CMMODIFY", "CMDECOD", "CMCAT", "CMSCAT", "CMPRESP",
                          "CMOCCUR", "CMDOSE", "CMDOSTXT", "CMDOSU", "CMDOSFRM",
                          "CMDOSFRQ", "CMROUTE", "CMSTDTC", "CMENDTC", "CMSTDY",
                          "CMENDY", "CMINDC"]
    ),
    "EX": SDTMDomain(
        domain_code="EX",
        domain_name="Exposure",
        domain_type="Interventions",
        description="Exposure domain containing study treatment administration",
        required_variables=["STUDYID", "DOMAIN", "USUBJID", "EXSEQ", "EXTRT"],
        expected_variables=["EXCAT", "EXDOSE", "EXDOSU", "EXDOSFRM", "EXDOSFRQ",
                          "EXROUTE", "EXSTDTC", "EXENDTC", "EXSTDY", "EXENDY"]
    ),
    "DS": SDTMDomain(
        domain_code="DS",
        domain_name="Disposition",
        domain_type="Events",
        description="Disposition domain capturing subject disposition events",
        required_variables=["STUDYID", "DOMAIN", "USUBJID", "DSSEQ", "DSTERM", "DSDECOD"],
        expected_variables=["DSCAT", "DSSCAT", "DSSTDTC", "DSENDTC"]
    ),
    "MH": SDTMDomain(
        domain_code="MH",
        domain_name="Medical History",
        domain_type="Events",
        description="Medical History domain capturing medical conditions",
        required_variables=["STUDYID", "DOMAIN", "USUBJID", "MHSEQ", "MHTERM"],
        expected_variables=["MHDECOD", "MHCAT", "MHSCAT", "MHSTDTC", "MHENDTC", "MHENRF"]
    ),
    "EG": SDTMDomain(
        domain_code="EG",
        domain_name="ECG Test Results",
        domain_type="Findings",
        description="ECG domain containing electrocardiogram test results",
        required_variables=["STUDYID", "DOMAIN", "USUBJID", "EGSEQ", "EGTESTCD", "EGTEST"],
        expected_variables=["EGORRES", "EGORRESU", "EGSTRESC", "EGSTRESN", "EGSTRESU", "EGDTC"]
    ),
    "PE": SDTMDomain(
        domain_code="PE",
        domain_name="Physical Examination",
        domain_type="Findings",
        description="Physical Examination domain containing physical exam findings",
        required_variables=["STUDYID", "DOMAIN", "USUBJID", "PESEQ", "PETESTCD", "PETEST"],
        expected_variables=["PEORRES", "PESTRESC", "PELOC", "PEDTC"]
    ),
    "PC": SDTMDomain(
        domain_code="PC",
        domain_name="Pharmacokinetics Concentrations",
        domain_type="Findings",
        description="PK Concentrations domain containing drug concentration data",
        required_variables=["STUDYID", "DOMAIN", "USUBJID", "PCSEQ", "PCTESTCD", "PCTEST"],
        expected_variables=["PCORRES", "PCORRESU", "PCSTRESC", "PCSTRESN", "PCSTRESU", "PCSPEC", "PCDTC"]
    ),
    "IE": SDTMDomain(
        domain_code="IE",
        domain_name="Inclusion/Exclusion Criteria Not Met",
        domain_type="Events",
        description="Inclusion/Exclusion domain capturing eligibility criteria",
        required_variables=["STUDYID", "DOMAIN", "USUBJID", "IESEQ", "IETEST"],
        expected_variables=["IETESTCD", "IECAT", "IEORRES", "IESTRESC"]
    ),
    "CO": SDTMDomain(
        domain_code="CO",
        domain_name="Comments",
        domain_type="Special Purpose",
        description="Comments domain capturing free-text comments",
        required_variables=["STUDYID", "DOMAIN", "COSEQ", "COVAL"],
        expected_variables=["USUBJID", "RDOMAIN", "IDVAR", "IDVARVAL", "CODTC"]
    ),
    "QS": SDTMDomain(
        domain_code="QS",
        domain_name="Questionnaires",
        domain_type="Findings",
        description="Questionnaires domain containing questionnaire responses",
        required_variables=["STUDYID", "DOMAIN", "USUBJID", "QSSEQ", "QSTESTCD", "QSTEST"],
        expected_variables=["QSCAT", "QSSCAT", "QSORRES", "QSSTRESC", "QSSTRESN", "QSDTC"]
    ),
    "RS": SDTMDomain(
        domain_code="RS",
        domain_name="Disease Response",
        domain_type="Findings",
        description="Disease Response domain containing tumor response assessments",
        required_variables=["STUDYID", "DOMAIN", "USUBJID", "RSSEQ", "RSTESTCD", "RSTEST"],
        expected_variables=["RSCAT", "RSORRES", "RSSTRESC", "RSDTC"]
    ),
    "TR": SDTMDomain(
        domain_code="TR",
        domain_name="Tumor Results",
        domain_type="Findings",
        description="Tumor Results domain containing tumor measurement data",
        required_variables=["STUDYID", "DOMAIN", "USUBJID", "TRSEQ", "TRTESTCD", "TRTEST"],
        expected_variables=["TRORRES", "TRORRESU", "TRSTRESC", "TRSTRESN", "TRSTRESU", "TRLOC", "TRLNKID", "TRDTC"]
    ),
    "TU": SDTMDomain(
        domain_code="TU",
        domain_name="Tumor Identification",
        domain_type="Findings",
        description="Tumor Identification domain containing tumor identification data",
        required_variables=["STUDYID", "DOMAIN", "USUBJID", "TUSEQ", "TUTESTCD", "TUTEST"],
        expected_variables=["TUORRES", "TUSTRESC", "TULOC", "TULNKID", "TUDTC"]
    ),
    "TA": SDTMDomain(
        domain_code="TA",
        domain_name="Trial Arms",
        domain_type="Trial Design",
        description="Trial Arms domain describing study arms",
        required_variables=["STUDYID", "DOMAIN", "ARMCD", "ARM"],
        expected_variables=["TAESSION", "ETCD", "ELEMENT", "TABESSION", "EPOCH"]
    ),
}

# Controlled Terminology for key variables
CONTROLLED_TERMINOLOGY = {
    "SEX": ["M", "F", "U", "UNDIFFERENTIATED"],
    "RACE": ["AMERICAN INDIAN OR ALASKA NATIVE", "ASIAN", "BLACK OR AFRICAN AMERICAN",
             "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER", "WHITE", "MULTIPLE",
             "NOT REPORTED", "UNKNOWN", "OTHER"],
    "ETHNIC": ["HISPANIC OR LATINO", "NOT HISPANIC OR LATINO", "NOT REPORTED", "UNKNOWN"],
    "AGEU": ["YEARS", "MONTHS", "WEEKS", "DAYS", "HOURS"],
    "AESER": ["Y", "N"],
    "AESEV": ["MILD", "MODERATE", "SEVERE"],
    "AEREL": ["NOT RELATED", "UNLIKELY RELATED", "POSSIBLY RELATED",
              "RELATED", "PROBABLY RELATED", "DEFINITELY RELATED"],
    "AEOUT": ["RECOVERED/RESOLVED", "RECOVERING/RESOLVING", "NOT RECOVERED/NOT RESOLVED",
              "RECOVERED/RESOLVED WITH SEQUELAE", "FATAL", "UNKNOWN"],
    "VSPOS": ["SITTING", "STANDING", "SUPINE", "PRONE"],
    "LBNRIND": ["NORMAL", "ABNORMAL", "LOW", "HIGH", "ABNORMAL LOW", "ABNORMAL HIGH"],
}

"""
SDTM ETL Pipeline Phases
========================

Defines the 7 sequential phases of the SDTM ETL pipeline according to
CDISC standards and FDA submission requirements.

Phase Flow:
1. Data Ingestion (Extract)
2. Raw Data Validation (Business Checks)
3. Metadata and Specification Preparation
4. SDTM Transformation (Transform)
5. SDTM Target Data Generation (Load)
6. Target Data Validation (Compliance Checks)
7. Data Warehouse Loading

Author: SDTM ETL Pipeline
Version: 2.0.0
"""

from enum import Enum, auto
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class PipelinePhase(str, Enum):
    """
    The 7 sequential phases of the SDTM ETL pipeline.
    """
    # Phase 1: Acquiring raw data from all source systems
    DATA_INGESTION = "data_ingestion"

    # Phase 2: Applying study-specific and general data quality checks
    RAW_DATA_VALIDATION = "raw_data_validation"

    # Phase 3: Defining the rules for transformation
    METADATA_PREPARATION = "metadata_preparation"

    # Phase 4: Applying the defined mapping logic
    SDTM_TRANSFORMATION = "sdtm_transformation"

    # Phase 5: Creating the final SDTM datasets
    TARGET_DATA_GENERATION = "target_data_generation"

    # Phase 6: Verifying SDTM compliance
    TARGET_DATA_VALIDATION = "target_data_validation"

    # Phase 7: Storing the final validated datasets
    DATA_WAREHOUSE_LOADING = "data_warehouse_loading"


class PhaseStatus(str, Enum):
    """Status of a pipeline phase."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    REQUIRES_REVIEW = "requires_review"


class ValidationFlagSeverity(str, Enum):
    """Severity levels for validation flags."""
    CRITICAL = "critical"      # Blocks progression
    ERROR = "error"            # Must be resolved before submission
    WARNING = "warning"        # Should be reviewed
    INFO = "info"              # Informational only


class ValidationFlag(BaseModel):
    """
    A validation flag attached to a record.

    Flags are used to track data quality issues throughout the pipeline.
    """
    flag_id: str = Field(..., description="Unique identifier for the flag")
    record_id: Optional[str] = Field(None, description="ID of the flagged record")
    domain: Optional[str] = Field(None, description="SDTM domain if applicable")
    variable: Optional[str] = Field(None, description="Variable name if applicable")
    severity: ValidationFlagSeverity = Field(default=ValidationFlagSeverity.WARNING)
    rule_id: str = Field(..., description="Validation rule that triggered the flag")
    message: str = Field(..., description="Human-readable description of the issue")
    phase: PipelinePhase = Field(..., description="Phase where flag was raised")
    source_value: Optional[Any] = Field(None, description="Original value that caused the flag")
    suggested_fix: Optional[str] = Field(None, description="Suggested resolution")
    is_resolved: bool = Field(default=False)
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PhaseResult(BaseModel):
    """Result of executing a pipeline phase."""
    phase: PipelinePhase
    status: PhaseStatus
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    # Metrics
    records_processed: int = 0
    records_passed: int = 0
    records_flagged: int = 0

    # Validation flags raised in this phase
    flags: List[ValidationFlag] = Field(default_factory=list)

    # Phase-specific outputs
    outputs: Dict[str, Any] = Field(default_factory=dict)

    # Error information if failed
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None

    def complete(self, status: PhaseStatus = PhaseStatus.COMPLETED):
        """Mark the phase as complete."""
        self.completed_at = datetime.utcnow()
        self.status = status
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()


# Phase descriptions and key activities
PHASE_DETAILS: Dict[PipelinePhase, Dict[str, Any]] = {
    PipelinePhase.DATA_INGESTION: {
        "name": "Data Ingestion (Extract)",
        "description": "Acquiring raw data from all source systems",
        "key_activities": [
            "Extracting data from EDC, central labs, external vendors",
            "Consolidating data into staging area",
            "File format validation",
            "Source data inventory"
        ],
        "inputs": ["EDC exports", "Lab data files", "Vendor data transfers"],
        "outputs": ["Staged raw data files", "Source data inventory"]
    },
    PipelinePhase.RAW_DATA_VALIDATION: {
        "name": "Raw Data Validation (Business Checks)",
        "description": "Applying study-specific and general data quality checks to source data",
        "key_activities": [
            "Data profiling (completeness, uniqueness, consistency)",
            "Business rule validation (edit checks)",
            "Mandatory field checks",
            "Range checks for numerical values",
            "Date logic validation",
            "Cross-form consistency checks",
            "Flagging incorrect/suspicious records"
        ],
        "inputs": ["Staged raw data files"],
        "outputs": ["Validated raw data", "Validation flags", "Source Data Review report"]
    },
    PipelinePhase.METADATA_PREPARATION: {
        "name": "Metadata and Specification Preparation",
        "description": "Defining the rules for transformation",
        "key_activities": [
            "Gathering EDC Data Dictionary (source metadata)",
            "Loading SDTM Implementation Guide (SDTMIG)",
            "Loading CDISC Controlled Terminology (CT)",
            "Creating SDTM Mapping Specification",
            "Defining derivation rules",
            "Identifying source-to-target mappings"
        ],
        "inputs": ["EDC Data Dictionary", "SDTMIG", "CDISC CT", "Protocol"],
        "outputs": ["SDTM Mapping Specification", "Variable derivation rules"]
    },
    PipelinePhase.SDTM_TRANSFORMATION: {
        "name": "SDTM Transformation (Transform)",
        "description": "Applying the defined mapping logic to convert raw data to SDTM structure",
        "key_activities": [
            "Direct carry-forward of variables",
            "Variable renaming",
            "Date reformatting to ISO 8601",
            "Combining/splitting variables",
            "Deriving new variables (e.g., VISITNUM)",
            "Transposing data (wide to long format)",
            "Applying controlled terminology"
        ],
        "inputs": ["Validated raw data", "SDTM Mapping Specification"],
        "outputs": ["Transformed SDTM domain datasets"]
    },
    PipelinePhase.TARGET_DATA_GENERATION: {
        "name": "SDTM Target Data Generation (Load)",
        "description": "Creating the final SDTM datasets based on the transformation",
        "key_activities": [
            "Generating final SDTM domain datasets (DM, AE, VS, LB, etc.)",
            "Creating Define.xml metadata file",
            "Generating dataset labels and variable metadata",
            "Creating Annotated CRF mappings"
        ],
        "inputs": ["Transformed SDTM data"],
        "outputs": ["SDTM domain datasets", "Define.xml", "Dataset metadata"]
    },
    PipelinePhase.TARGET_DATA_VALIDATION: {
        "name": "Target Data Validation (Compliance Checks)",
        "description": "Verifying SDTM datasets comply with CDISC standards",
        "key_activities": [
            "CDISC conformance validation (Pinnacle 21 rules)",
            "SDTMIG structural compliance",
            "Controlled terminology verification",
            "Define.xml validation",
            "Mapping logic verification (QC)",
            "Flagging non-compliant records"
        ],
        "inputs": ["SDTM datasets", "Define.xml"],
        "outputs": ["Validation report", "Compliance flags", "Error/warning summary"]
    },
    PipelinePhase.DATA_WAREHOUSE_LOADING: {
        "name": "Data Warehouse Loading",
        "description": "Storing the final validated SDTM datasets",
        "key_activities": [
            "Loading SDTM datasets to Clinical Data Warehouse",
            "Loading Define.xml to repository",
            "Creating audit trail",
            "Archiving source data",
            "Generating submission package"
        ],
        "inputs": ["Validated SDTM datasets", "Define.xml"],
        "outputs": ["CDW entries", "Archived submission package", "Audit logs"]
    }
}


class PipelinePhaseTracker:
    """
    Tracks the progress of a pipeline execution through all 7 phases.
    """

    def __init__(self, study_id: str):
        self.study_id = study_id
        self.current_phase: Optional[PipelinePhase] = None
        self.phase_results: Dict[PipelinePhase, PhaseResult] = {}
        self.all_flags: List[ValidationFlag] = []
        self.started_at: datetime = datetime.utcnow()
        self.completed_at: Optional[datetime] = None

    def start_phase(self, phase: PipelinePhase) -> PhaseResult:
        """Start a new phase."""
        self.current_phase = phase
        result = PhaseResult(phase=phase, status=PhaseStatus.IN_PROGRESS)
        self.phase_results[phase] = result
        return result

    def complete_phase(
        self,
        phase: PipelinePhase,
        status: PhaseStatus = PhaseStatus.COMPLETED,
        outputs: Optional[Dict[str, Any]] = None
    ) -> PhaseResult:
        """Complete a phase."""
        result = self.phase_results.get(phase)
        if result:
            result.complete(status)
            if outputs:
                result.outputs = outputs
        return result

    def add_flag(self, flag: ValidationFlag):
        """Add a validation flag."""
        self.all_flags.append(flag)
        if self.current_phase and self.current_phase in self.phase_results:
            self.phase_results[self.current_phase].flags.append(flag)
            self.phase_results[self.current_phase].records_flagged += 1

    def get_phase_order(self) -> List[PipelinePhase]:
        """Get the ordered list of pipeline phases."""
        return [
            PipelinePhase.DATA_INGESTION,
            PipelinePhase.RAW_DATA_VALIDATION,
            PipelinePhase.METADATA_PREPARATION,
            PipelinePhase.SDTM_TRANSFORMATION,
            PipelinePhase.TARGET_DATA_GENERATION,
            PipelinePhase.TARGET_DATA_VALIDATION,
            PipelinePhase.DATA_WAREHOUSE_LOADING
        ]

    def get_next_phase(self) -> Optional[PipelinePhase]:
        """Get the next phase in the pipeline."""
        phases = self.get_phase_order()
        if self.current_phase is None:
            return phases[0]

        try:
            current_idx = phases.index(self.current_phase)
            if current_idx < len(phases) - 1:
                return phases[current_idx + 1]
        except ValueError:
            pass
        return None

    def can_proceed_to_next_phase(self) -> bool:
        """Check if we can proceed to the next phase."""
        if self.current_phase is None:
            return True

        result = self.phase_results.get(self.current_phase)
        if not result:
            return False

        # Check for blocking flags
        blocking_flags = [
            f for f in result.flags
            if f.severity == ValidationFlagSeverity.CRITICAL and not f.is_resolved
        ]

        return result.status == PhaseStatus.COMPLETED and len(blocking_flags) == 0

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of pipeline progress."""
        total_flags = len(self.all_flags)
        critical_flags = len([f for f in self.all_flags if f.severity == ValidationFlagSeverity.CRITICAL])
        error_flags = len([f for f in self.all_flags if f.severity == ValidationFlagSeverity.ERROR])
        resolved_flags = len([f for f in self.all_flags if f.is_resolved])

        phases_completed = sum(
            1 for r in self.phase_results.values()
            if r.status == PhaseStatus.COMPLETED
        )

        return {
            "study_id": self.study_id,
            "current_phase": self.current_phase.value if self.current_phase else None,
            "phases_completed": phases_completed,
            "total_phases": len(self.get_phase_order()),
            "total_flags": total_flags,
            "critical_flags": critical_flags,
            "error_flags": error_flags,
            "resolved_flags": resolved_flags,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


# Business rule categories for raw data validation
class BusinessRuleCategory(str, Enum):
    """Categories of business rules for raw data validation."""
    MANDATORY_FIELD = "mandatory_field"
    RANGE_CHECK = "range_check"
    DATE_LOGIC = "date_logic"
    CONSISTENCY_CHECK = "consistency_check"
    FORMAT_CHECK = "format_check"
    DUPLICATE_CHECK = "duplicate_check"
    REFERENTIAL_INTEGRITY = "referential_integrity"
    PROTOCOL_COMPLIANCE = "protocol_compliance"


class BusinessRule(BaseModel):
    """
    A business rule for raw data validation.
    """
    rule_id: str
    category: BusinessRuleCategory
    name: str
    description: str

    # Rule specification
    applies_to: List[str] = Field(default_factory=list, description="Source files/forms this rule applies to")
    variables: List[str] = Field(default_factory=list, description="Variables involved in the rule")
    condition: str = Field(..., description="Rule condition expression")

    # Severity and handling
    severity: ValidationFlagSeverity = ValidationFlagSeverity.ERROR
    auto_resolvable: bool = False

    # Metadata
    source: str = Field(default="custom", description="Rule source: protocol, cdm_standard, custom")
    created_at: datetime = Field(default_factory=datetime.utcnow)

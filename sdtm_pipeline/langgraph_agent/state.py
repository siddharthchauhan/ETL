"""
SDTM Pipeline State Schema (7-Phase ETL Pipeline)
=================================================

Defines the state structure for the LangGraph SDTM transformation pipeline.

This state schema aligns with the 7-phase SDTM ETL process:
1. Data Ingestion (Extract)
2. Raw Data Validation (Business Checks)
3. Metadata and Specification Preparation
4. SDTM Transformation (Transform)
5. SDTM Target Data Generation (Load)
6. Target Data Validation (Compliance Checks)
7. Data Warehouse Loading

Author: SDTM ETL Pipeline
Version: 2.0.0 (Enhanced with 7-phase pipeline support)
"""

from typing import List, Dict, Any, Optional, Annotated
from typing_extensions import TypedDict, Required
import operator


def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two dictionaries, with b taking precedence."""
    result = a.copy()
    result.update(b)
    return result


def append_list(a: List[Any], b: List[Any]) -> List[Any]:
    """Append list b to list a."""
    return a + b


# =============================================================================
# PHASE ENUMERATION (matches pipeline_phases.py)
# =============================================================================

PIPELINE_PHASES = [
    "data_ingestion",           # Phase 1
    "raw_data_validation",      # Phase 2
    "metadata_preparation",     # Phase 3
    "sdtm_transformation",      # Phase 4
    "target_data_generation",   # Phase 5
    "target_data_validation",   # Phase 6
    "data_warehouse_loading",   # Phase 7
]


class FileInfo(TypedDict):
    """Information about a source file."""
    path: str
    name: str
    size_kb: float
    target_domain: Optional[str]


class ValidationIssue(TypedDict):
    """A validation issue found in data."""
    rule_id: str
    severity: str
    message: str
    domain: str
    variable: Optional[str]


class ValidationResult(TypedDict):
    """Result of a validation check."""
    is_valid: bool
    domain: str
    total_records: int
    error_count: int
    warning_count: int
    issues: List[ValidationIssue]


class ColumnMapping(TypedDict):
    """Mapping from source column to SDTM variable."""
    source_column: str
    target_variable: str
    transformation: Optional[str]
    derivation_rule: Optional[str]
    comments: str


class MappingSpec(TypedDict):
    """SDTM mapping specification."""
    study_id: str
    source_domain: str
    target_domain: str
    column_mappings: List[ColumnMapping]
    derivation_rules: Dict[str, str]


class TransformationResult(TypedDict):
    """Result of SDTM transformation."""
    success: bool
    source_domain: str
    target_domain: str
    records_processed: int
    records_output: int
    output_path: Optional[str]
    errors: List[str]


# =============================================================================
# NEW: 7-PHASE PIPELINE TYPES
# =============================================================================

class ValidationFlag(TypedDict):
    """A validation flag attached to a record (Phase 2 & 6)."""
    flag_id: str
    record_id: Optional[str]
    domain: Optional[str]
    variable: Optional[str]
    severity: str  # critical, error, warning, info
    rule_id: str
    message: str
    phase: str
    source_value: Optional[str]
    suggested_fix: Optional[str]
    is_resolved: bool
    created_at: str


class PhaseResult(TypedDict):
    """Result of executing a pipeline phase."""
    phase: str
    status: str  # not_started, in_progress, completed, failed, requires_review
    started_at: str
    completed_at: Optional[str]
    duration_seconds: Optional[float]
    records_processed: int
    records_passed: int
    records_flagged: int
    flags: List[ValidationFlag]
    outputs: Dict[str, Any]
    error_message: Optional[str]


class DocumentInfo(TypedDict):
    """Information about a required document."""
    document_type: str
    name: str
    version: Optional[str]
    status: str  # not_available, draft, under_review, approved, final
    file_path: Optional[str]
    is_available: bool
    is_generated: bool


class SourceDataReviewReport(TypedDict):
    """Source Data Review report from Phase 2."""
    report_type: str
    study_id: str
    phase: str
    generated_at: str
    total_domains_validated: int
    total_records_processed: int
    total_flags: int
    critical_flags: int
    error_flags: int
    warning_flags: int
    overall_status: str  # BLOCKED, PASSED_WITH_ISSUES, PASSED
    blocking_issues: bool
    recommendations: List[str]


class DefineXMLInfo(TypedDict):
    """Information about generated Define.xml (Phase 5)."""
    file_path: str
    study_oid: str
    datasets_count: int
    codelists_count: int
    generated_at: str
    sdtmig_version: str
    define_version: str


class SDTMPipelineState(TypedDict, total=False):
    """
    State schema for the SDTM transformation pipeline.

    This state is passed through all nodes in the LangGraph pipeline.
    Enhanced with 7-phase ETL pipeline support.

    Phases:
    1. Data Ingestion (Extract)
    2. Raw Data Validation (Business Checks)
    3. Metadata and Specification Preparation
    4. SDTM Transformation (Transform)
    5. SDTM Target Data Generation (Load)
    6. Target Data Validation (Compliance Checks)
    7. Data Warehouse Loading
    """
    # Configuration
    study_id: Required[str]
    raw_data_dir: Required[str]
    output_dir: Required[str]
    api_key: str
    target_domains: Optional[List[str]]  # Filter to specific SDTM domains (e.g., ['VS', 'DM'])

    # ==========================================================================
    # 7-PHASE PIPELINE TRACKING
    # ==========================================================================
    current_phase: str  # One of PIPELINE_PHASES
    phase_history: Annotated[List[str], append_list]
    phase_results: Dict[str, PhaseResult]  # phase -> PhaseResult

    # Phase-specific status
    phase_1_complete: bool  # Data Ingestion
    phase_2_complete: bool  # Raw Data Validation
    phase_3_complete: bool  # Metadata Preparation
    phase_4_complete: bool  # SDTM Transformation
    phase_5_complete: bool  # Target Data Generation
    phase_6_complete: bool  # Target Data Validation
    phase_7_complete: bool  # Data Warehouse Loading

    # ==========================================================================
    # DOCUMENT REGISTRY (Required documents for each phase)
    # ==========================================================================
    documents: Dict[str, DocumentInfo]  # document_type -> DocumentInfo
    document_registry_path: str  # Path to saved registry

    # ==========================================================================
    # PHASE 1: DATA INGESTION
    # ==========================================================================
    source_files: List[FileInfo]
    selected_files: List[FileInfo]
    raw_data_paths: Dict[str, str]  # filename -> path
    raw_data_info: Dict[str, Dict[str, Any]]  # filename -> metadata
    data_sources: Dict[str, str]  # Source type -> count (EDC, Labs, Vendors)
    staging_area_path: str

    # ==========================================================================
    # PHASE 2: RAW DATA VALIDATION (Business Checks)
    # ==========================================================================
    raw_validation_results: List[ValidationResult]
    validation_flags: List[ValidationFlag]  # NEW: All flags from validation
    source_data_review: SourceDataReviewReport  # NEW: SDR report
    business_rules_applied: List[str]  # List of rule IDs applied
    raw_validation_blocking: bool  # True if critical flags exist

    # ==========================================================================
    # PHASE 3: METADATA AND SPECIFICATION PREPARATION
    # ==========================================================================
    edc_data_dictionary: Dict[str, Any]  # NEW: EDC metadata
    sdtmig_version: str  # NEW: SDTMIG version used
    ct_version: str  # NEW: Controlled Terminology version
    mapping_specifications: List[MappingSpec]
    derivation_rules: Dict[str, str]  # NEW: Variable derivation rules

    # ==========================================================================
    # PHASE 4: SDTM TRANSFORMATION
    # ==========================================================================
    transformation_results: List[TransformationResult]
    sdtm_data_paths: Dict[str, str]  # domain -> path
    transformation_logs: Dict[str, List[str]]  # domain -> log messages

    # ==========================================================================
    # PHASE 5: TARGET DATA GENERATION
    # ==========================================================================
    define_xml_info: DefineXMLInfo  # NEW: Define.xml information
    define_xml_path: str  # NEW: Path to generated Define.xml
    sdtm_datasets: Dict[str, Dict[str, Any]]  # NEW: Generated dataset info
    acrf_mapping: Dict[str, str]  # NEW: aCRF to SDTM mapping

    # ==========================================================================
    # PHASE 6: TARGET DATA VALIDATION (Compliance Checks)
    # ==========================================================================
    sdtm_validation_results: List[ValidationResult]
    target_validation_flags: List[ValidationFlag]  # NEW: SDTM validation flags
    pinnacle21_report: Dict[str, Any]  # NEW: Pinnacle 21 style report
    compliance_score: float  # NEW: CDISC compliance score

    # Multi-layer validation results
    structural_validation: Dict[str, Any]
    cdisc_validation: Dict[str, Any]
    cross_domain_validation: Dict[str, Any]
    semantic_validation: Dict[str, Any]
    anomaly_detection: Dict[str, Any]
    protocol_compliance: Dict[str, Any]

    # Conformance scoring details
    conformance_score: float  # Overall score 0-100
    layer_scores: Dict[str, float]  # Per-layer scores
    submission_ready: bool  # True if score >= 95%
    validation_report_path: str  # NEW: Path to validation report

    # ==========================================================================
    # PHASE 7: DATA WAREHOUSE LOADING
    # ==========================================================================
    neo4j_loaded: bool
    neo4j_load_result: Dict[str, Any]  # NEW: Neo4j load statistics
    s3_uploaded: bool
    s3_paths: Dict[str, str]  # NEW: S3 paths for uploaded files
    audit_trail: List[Dict[str, Any]]  # NEW: Audit log entries

    # ==========================================================================
    # CODE GENERATION (SAS/R)
    # ==========================================================================
    generated_sas_files: Dict[str, str]  # name -> path
    generated_r_files: Dict[str, str]  # name -> path

    # ==========================================================================
    # HUMAN REVIEW / CHECKPOINTS
    # ==========================================================================
    human_decision: str  # "approve", "reject", "modify"
    human_feedback: str
    pending_review: str  # Which checkpoint needs review
    checkpoints: Dict[str, Dict[str, Any]]  # NEW: Checkpoint status by phase

    # ==========================================================================
    # SELF-CORRECTION LOOP
    # ==========================================================================
    iteration_count: int  # Current iteration (max 3)
    needs_correction: bool  # Whether self-correction is needed
    correction_feedback: str  # Feedback for correction
    max_iterations: int  # Maximum allowed iterations (default 3)

    # ==========================================================================
    # PROCESSING STATS AND OUTPUTS
    # ==========================================================================
    processing_stats: Dict[str, Any]
    errors: Annotated[List[str], append_list]
    messages: Annotated[List[str], append_list]
    final_report: Dict[str, Any]


def create_initial_state(
    study_id: str,
    raw_data_dir: str,
    output_dir: str,
    api_key: str = "",
    max_iterations: int = 3,
    sdtmig_version: str = "3.4",
    ct_version: str = "2024-12-20",
    target_domains: Optional[List[str]] = None
) -> SDTMPipelineState:
    """
    Create initial pipeline state for the 7-phase SDTM ETL process.

    Args:
        study_id: Study identifier
        raw_data_dir: Directory containing raw source data
        output_dir: Directory for output files
        api_key: API key for external services
        max_iterations: Maximum self-correction iterations
        sdtmig_version: SDTM-IG version to use
        ct_version: Controlled Terminology version to use
        target_domains: Optional list of SDTM domains to process (e.g., ['VS', 'DM'])

    Returns:
        Initialized SDTMPipelineState
    """
    return SDTMPipelineState(
        # Configuration
        study_id=study_id,
        raw_data_dir=raw_data_dir,
        output_dir=output_dir,
        api_key=api_key,
        target_domains=target_domains,

        # 7-Phase pipeline tracking
        current_phase="initialized",
        phase_history=["initialized"],
        phase_results={},
        phase_1_complete=False,
        phase_2_complete=False,
        phase_3_complete=False,
        phase_4_complete=False,
        phase_5_complete=False,
        phase_6_complete=False,
        phase_7_complete=False,

        # Document registry
        documents={},
        document_registry_path="",

        # Phase 1: Data Ingestion
        source_files=[],
        selected_files=[],
        raw_data_paths={},
        raw_data_info={},
        data_sources={},
        staging_area_path="",

        # Phase 2: Raw Data Validation
        raw_validation_results=[],
        validation_flags=[],
        source_data_review={},
        business_rules_applied=[],
        raw_validation_blocking=False,

        # Phase 3: Metadata Preparation
        edc_data_dictionary={},
        sdtmig_version=sdtmig_version,
        ct_version=ct_version,
        mapping_specifications=[],
        derivation_rules={},

        # Phase 4: SDTM Transformation
        transformation_results=[],
        sdtm_data_paths={},
        transformation_logs={},

        # Phase 5: Target Data Generation
        define_xml_info={},
        define_xml_path="",
        sdtm_datasets={},
        acrf_mapping={},

        # Phase 6: Target Data Validation
        sdtm_validation_results=[],
        target_validation_flags=[],
        pinnacle21_report={},
        compliance_score=0.0,
        structural_validation={},
        cdisc_validation={},
        cross_domain_validation={},
        semantic_validation={},
        anomaly_detection={},
        protocol_compliance={},
        conformance_score=0.0,
        layer_scores={},
        submission_ready=False,
        validation_report_path="",

        # Phase 7: Data Warehouse Loading
        neo4j_loaded=False,
        neo4j_load_result={},
        s3_uploaded=False,
        s3_paths={},
        audit_trail=[],

        # Code generation
        generated_sas_files={},
        generated_r_files={},

        # Human review
        human_decision="",
        human_feedback="",
        pending_review="",
        checkpoints={},

        # Self-correction
        iteration_count=0,
        needs_correction=False,
        correction_feedback="",
        max_iterations=max_iterations,

        # Processing stats
        processing_stats={},
        errors=[],
        messages=[],
        final_report={}
    )


def get_phase_number(phase_name: str) -> int:
    """Get the phase number (1-7) for a phase name."""
    if phase_name in PIPELINE_PHASES:
        return PIPELINE_PHASES.index(phase_name) + 1
    return 0


def get_next_phase(current_phase: str) -> Optional[str]:
    """Get the next phase after the current one."""
    if current_phase == "initialized":
        return PIPELINE_PHASES[0]
    if current_phase in PIPELINE_PHASES:
        idx = PIPELINE_PHASES.index(current_phase)
        if idx < len(PIPELINE_PHASES) - 1:
            return PIPELINE_PHASES[idx + 1]
    return None


def is_phase_complete(state: SDTMPipelineState, phase: str) -> bool:
    """Check if a phase is complete based on state."""
    phase_num = get_phase_number(phase)
    if phase_num == 1:
        return state.get("phase_1_complete", False)
    elif phase_num == 2:
        return state.get("phase_2_complete", False)
    elif phase_num == 3:
        return state.get("phase_3_complete", False)
    elif phase_num == 4:
        return state.get("phase_4_complete", False)
    elif phase_num == 5:
        return state.get("phase_5_complete", False)
    elif phase_num == 6:
        return state.get("phase_6_complete", False)
    elif phase_num == 7:
        return state.get("phase_7_complete", False)
    return False


def get_pipeline_progress(state: SDTMPipelineState) -> Dict[str, Any]:
    """Get overall pipeline progress."""
    completed = sum([
        state.get("phase_1_complete", False),
        state.get("phase_2_complete", False),
        state.get("phase_3_complete", False),
        state.get("phase_4_complete", False),
        state.get("phase_5_complete", False),
        state.get("phase_6_complete", False),
        state.get("phase_7_complete", False),
    ])

    total_flags = len(state.get("validation_flags", [])) + len(state.get("target_validation_flags", []))
    critical_flags = sum(
        1 for f in state.get("validation_flags", [])
        if f.get("severity") == "critical" and not f.get("is_resolved")
    )

    return {
        "study_id": state["study_id"],
        "current_phase": state.get("current_phase", "initialized"),
        "phases_completed": completed,
        "total_phases": 7,
        "progress_percentage": round((completed / 7) * 100, 1),
        "total_flags": total_flags,
        "critical_flags": critical_flags,
        "submission_ready": state.get("submission_ready", False),
        "conformance_score": state.get("conformance_score", 0.0)
    }

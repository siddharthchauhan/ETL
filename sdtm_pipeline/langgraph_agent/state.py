"""
SDTM Pipeline State Schema
==========================
Defines the state structure for the LangGraph SDTM transformation pipeline.
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from typing_extensions import Required
import operator


def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two dictionaries, with b taking precedence."""
    result = a.copy()
    result.update(b)
    return result


def append_list(a: List[Any], b: List[Any]) -> List[Any]:
    """Append list b to list a."""
    return a + b


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


class SDTMPipelineState(TypedDict, total=False):
    """
    State schema for the SDTM transformation pipeline.

    This state is passed through all nodes in the LangGraph pipeline.
    """
    # Configuration
    study_id: Required[str]
    raw_data_dir: Required[str]
    output_dir: Required[str]
    api_key: str

    # Pipeline phase tracking
    current_phase: str
    phase_history: Annotated[List[str], append_list]

    # Source files
    source_files: List[FileInfo]
    selected_files: List[FileInfo]

    # Raw data (stored as serializable format)
    raw_data_paths: Dict[str, str]  # filename -> path
    raw_data_info: Dict[str, Dict[str, Any]]  # filename -> metadata

    # Validation results
    raw_validation_results: List[ValidationResult]
    sdtm_validation_results: List[ValidationResult]

    # Multi-layer validation results (new for multi-agent architecture)
    structural_validation: Dict[str, Any]
    cdisc_validation: Dict[str, Any]
    cross_domain_validation: Dict[str, Any]
    semantic_validation: Dict[str, Any]
    anomaly_detection: Dict[str, Any]
    protocol_compliance: Dict[str, Any]

    # Mapping specifications
    mapping_specifications: List[MappingSpec]

    # Transformation results
    transformation_results: List[TransformationResult]
    sdtm_data_paths: Dict[str, str]  # domain -> path

    # Code generation
    generated_sas_files: Dict[str, str]  # name -> path
    generated_r_files: Dict[str, str]  # name -> path

    # Human review
    human_decision: str  # "approve", "reject", "modify"
    human_feedback: str
    pending_review: str  # Which checkpoint needs review

    # Self-correction loop (new for multi-agent architecture)
    iteration_count: int  # Current iteration (max 3)
    conformance_score: float  # Overall score 0-100
    needs_correction: bool  # Whether self-correction is needed
    correction_feedback: str  # Feedback for correction
    max_iterations: int  # Maximum allowed iterations (default 3)

    # Conformance scoring details
    layer_scores: Dict[str, float]  # Per-layer scores
    submission_ready: bool  # True if score >= 95%

    # Processing stats
    processing_stats: Dict[str, Any]

    # Errors and messages
    errors: Annotated[List[str], append_list]
    messages: Annotated[List[str], append_list]

    # Final report
    final_report: Dict[str, Any]


def create_initial_state(
    study_id: str,
    raw_data_dir: str,
    output_dir: str,
    api_key: str = "",
    max_iterations: int = 3
) -> SDTMPipelineState:
    """Create initial pipeline state."""
    return SDTMPipelineState(
        study_id=study_id,
        raw_data_dir=raw_data_dir,
        output_dir=output_dir,
        api_key=api_key,
        current_phase="initialized",
        phase_history=["initialized"],
        source_files=[],
        selected_files=[],
        raw_data_paths={},
        raw_data_info={},
        raw_validation_results=[],
        sdtm_validation_results=[],
        # Multi-layer validation (new)
        structural_validation={},
        cdisc_validation={},
        cross_domain_validation={},
        semantic_validation={},
        anomaly_detection={},
        protocol_compliance={},
        mapping_specifications=[],
        transformation_results=[],
        sdtm_data_paths={},
        generated_sas_files={},
        generated_r_files={},
        human_decision="",
        human_feedback="",
        pending_review="",
        # Self-correction loop (new)
        iteration_count=0,
        conformance_score=0.0,
        needs_correction=False,
        correction_feedback="",
        max_iterations=max_iterations,
        layer_scores={},
        submission_ready=False,
        processing_stats={},
        errors=[],
        messages=[],
        final_report={}
    )

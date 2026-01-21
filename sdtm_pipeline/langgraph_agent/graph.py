"""
SDTM Pipeline Graph Export
==========================
Exports the compiled LangGraph for use with `langgraph dev`.

Multi-Agent Architecture:
- 6 specialized agents (Source Analyst, SDTM Expert, Code Generator, Validator, Anomaly Detector, Protocol Compliance)
- Hybrid RAG (BM25 + Semantic search)
- Multi-layer validation
- Conformance scoring
- Self-correction loop (up to 3 iterations)
- Human-in-the-loop checkpoints

Usage:
    langgraph dev
    # Then open http://localhost:2024 in your browser
    # Studio UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024

Input Schema (when invoking via Studio):
    {
        "study_id": "MAXIS-08",
        "raw_data_dir": "/tmp/s3_data/extracted/Maxis-08 RAW DATA_CSV",
        "output_dir": "./sdtm_langgraph_output",
        "human_decision": "approve"
    }
"""

import os
import sys
from typing import Dict, Any, List, Literal, Optional
from typing_extensions import TypedDict
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Ensure the package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Use absolute imports
from sdtm_pipeline.langgraph_agent.state import SDTMPipelineState, create_initial_state
from sdtm_pipeline.langgraph_agent.async_nodes import (
    ingest_data_node,
    validate_raw_data_parallel_node,
    generate_mappings_parallel_node,
    transform_to_sdtm_parallel_node,
    validate_sdtm_parallel_node,
    generate_code_parallel_node,
    load_to_neo4j_node,
    upload_to_s3_node,
    generate_report_node,
    human_review_node
)
from sdtm_pipeline.langgraph_agent.config import configure_langsmith

# Import scoring system
try:
    from sdtm_pipeline.scoring import calculate_conformance_score, is_submission_ready, SUBMISSION_THRESHOLD
    SCORING_AVAILABLE = True
except ImportError:
    SCORING_AVAILABLE = False
    SUBMISSION_THRESHOLD = 95.0

# Import checkpoint system
try:
    from sdtm_pipeline.review import HumanCheckpoint, CheckpointManager
    CHECKPOINT_AVAILABLE = True
except ImportError:
    CHECKPOINT_AVAILABLE = False


# Load environment variables
load_dotenv()

# Configure LangSmith
configure_langsmith()

# Self-correction constants
MAX_ITERATIONS = 3


# ============================================================================
# Input/Output Schemas for LangGraph Studio
# ============================================================================

class PipelineInput(BaseModel):
    """Input schema for the SDTM pipeline."""
    study_id: str = Field(
        default="MAXIS-08",
        description="Clinical study identifier"
    )
    raw_data_dir: str = Field(
        default="/tmp/s3_data/extracted/Maxis-08 RAW DATA_CSV",
        description="Directory containing raw CSV files"
    )
    output_dir: str = Field(
        default="./sdtm_langgraph_output",
        description="Output directory for SDTM data and reports"
    )
    human_decision: str = Field(
        default="approve",
        description="Default decision for human review checkpoints (approve/reject/modify)"
    )
    max_iterations: int = Field(
        default=3,
        description="Maximum self-correction iterations before human review"
    )


class PipelineOutput(BaseModel):
    """Output schema for the SDTM pipeline."""
    study_id: str = Field(description="Study identifier")
    status: str = Field(description="Pipeline completion status")
    sdtm_domains_created: int = Field(description="Number of SDTM domains created")
    total_records: int = Field(description="Total SDTM records transformed")
    conformance_score: float = Field(description="Overall conformance score (0-100)")
    submission_ready: bool = Field(description="Whether data meets submission threshold (>= 95%)")
    iterations_used: int = Field(description="Number of self-correction iterations used")
    neo4j_loaded: bool = Field(description="Whether data was loaded to Neo4j")
    s3_uploaded: bool = Field(description="Whether data was uploaded to S3")
    output_directory: str = Field(description="Path to output files")


# ============================================================================
# Conditional Edge Functions
# ============================================================================

def should_continue_after_raw_validation(
    state: SDTMPipelineState
) -> Literal["human_review", "generate_mappings"]:
    """Determine if human review is needed after raw validation."""
    raw_results = state.get("raw_validation_results", [])
    critical_errors = sum(r.get("error_count", 0) for r in raw_results)

    if critical_errors > 0:
        return "human_review"
    return "generate_mappings"


def should_continue_after_sdtm_validation(
    state: SDTMPipelineState
) -> Literal["human_review", "generate_code"]:
    """Determine if human review is needed after SDTM validation."""
    sdtm_results = state.get("sdtm_validation_results", [])
    errors = sum(r.get("error_count", 0) for r in sdtm_results)

    if errors > 0:
        return "human_review"
    return "generate_code"


def route_after_human_review(
    state: SDTMPipelineState
) -> Literal["generate_mappings", "transform", "generate_code", "end"]:
    """Route to next node after human review."""
    decision = state.get("human_decision", "approve")
    if decision.lower() != "approve":
        return "end"

    pending = state.get("pending_review", "")
    current_phase = state.get("current_phase", "")

    if "raw_validation" in pending or "raw_validation" in current_phase:
        return "generate_mappings"
    elif "mapping" in pending or "mapping" in current_phase:
        return "transform"
    elif "sdtm_validation" in pending or "sdtm_validation" in current_phase:
        return "generate_code"

    return "generate_mappings"


def route_after_conformance_scoring(
    state: SDTMPipelineState
) -> Literal["generate_code", "self_correction", "human_review"]:
    """
    Route based on conformance score and iteration count.

    Logic:
    - IF score >= 95%: Continue to code generation
    - ELIF iteration < max_iterations: Self-correction loop
    - ELSE: Human review required
    """
    score = state.get("conformance_score", 0)
    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", MAX_ITERATIONS)

    if score >= SUBMISSION_THRESHOLD:
        return "generate_code"
    elif iteration < max_iter:
        return "self_correction"
    else:
        return "human_review"


def route_after_self_correction(
    state: SDTMPipelineState
) -> Literal["generate_mappings", "human_review"]:
    """Route after self-correction analysis."""
    needs_correction = state.get("needs_correction", False)

    if needs_correction:
        return "generate_mappings"  # Retry with feedback
    else:
        return "human_review"  # Max iterations or other issue


def route_after_final_scoring(
    state: SDTMPipelineState
) -> Literal["load_neo4j", "human_review"]:
    """Route after final conformance scoring."""
    score = state.get("conformance_score", 0)
    submission_ready = state.get("submission_ready", False)

    if score >= SUBMISSION_THRESHOLD or submission_ready:
        return "load_neo4j"
    else:
        return "human_review"


# ============================================================================
# Conformance Scoring Node
# ============================================================================

async def conformance_scoring_node(
    state: SDTMPipelineState,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Calculate conformance score from multi-layer validation."""

    print("\n  Calculating conformance score...")

    if not SCORING_AVAILABLE:
        # Fallback when scoring module not available
        return {
            "conformance_score": 80.0,
            "submission_ready": False,
            "layer_scores": {},
            "current_phase": "conformance_scoring"
        }

    # Gather validation results
    validation_results = {
        "structural": state.get("structural_validation", {}),
        "cdisc": state.get("cdisc_validation", {}),
        "cross_domain": state.get("cross_domain_validation", {}),
        "semantic": state.get("semantic_validation", {}),
        "anomaly": state.get("anomaly_detection", {}),
        "protocol": state.get("protocol_compliance", {})
    }

    # Also include legacy validation results
    sdtm_results = state.get("sdtm_validation_results", [])
    if sdtm_results:
        total_errors = sum(r.get("error_count", 0) for r in sdtm_results)
        total_warnings = sum(r.get("warning_count", 0) for r in sdtm_results)
        total_records = sum(r.get("total_records", 0) for r in sdtm_results)

        # Merge into CDISC validation
        validation_results["cdisc"] = {
            "error_count": validation_results.get("cdisc", {}).get("error_count", 0) + total_errors,
            "warning_count": validation_results.get("cdisc", {}).get("warning_count", 0) + total_warnings,
            "total_records": max(validation_results.get("cdisc", {}).get("total_records", 0), total_records),
            "is_valid": total_errors == 0
        }

    score = calculate_conformance_score(validation_results)
    ready, _ = is_submission_ready(validation_results)

    print(f"  Conformance Score: {score.overall_score:.1f}%")
    print(f"  Submission Ready: {ready}")

    return {
        "conformance_score": score.overall_score,
        "submission_ready": ready,
        "layer_scores": {k: v.raw_score for k, v in score.layer_scores.items()},
        "needs_correction": not ready,
        "current_phase": "conformance_scoring"
    }


# ============================================================================
# Self-Correction Node
# ============================================================================

async def self_correction_node(
    state: SDTMPipelineState,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate feedback for self-correction loop.

    Analyzes validation issues and generates actionable feedback
    for improving the data quality in the next iteration.
    """
    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", MAX_ITERATIONS)
    score = state.get("conformance_score", 0)

    print(f"\n  Self-correction iteration {iteration + 1}/{max_iter}")
    print(f"  Current score: {score:.1f}%")

    if iteration >= max_iter:
        return {
            "needs_correction": False,
            "pending_review": "max_iterations",
            "iteration_count": iteration,
            "current_phase": "self_correction"
        }

    # Identify areas needing improvement
    layer_scores = state.get("layer_scores", {})
    weak_areas = [
        layer for layer, layer_score in layer_scores.items()
        if layer_score < 80
    ]

    # Generate feedback
    feedback_parts = []
    if "structural" in weak_areas:
        feedback_parts.append("Check required variables and data types")
    if "cdisc" in weak_areas:
        feedback_parts.append("Verify controlled terminology and date formats")
    if "cross_domain" in weak_areas:
        feedback_parts.append("Ensure referential integrity across domains")
    if "semantic" in weak_areas:
        feedback_parts.append("Review business logic and clinical plausibility")

    feedback = ". ".join(feedback_parts) if feedback_parts else "Review all validation issues"

    print(f"  Feedback: {feedback}")

    return {
        "needs_correction": True,
        "correction_feedback": feedback,
        "iteration_count": iteration + 1,
        "current_phase": "self_correction"
    }


# ============================================================================
# Build the Graph
# ============================================================================

def build_sdtm_graph() -> StateGraph:
    """
    Build the SDTM transformation pipeline graph.

    Multi-Agent Architecture Flow:
    1. ingest_data → validate_raw_data
    2. validate_raw_data → [human_review | generate_mappings]
    3. generate_mappings → transform
    4. transform → validate_sdtm
    5. validate_sdtm → conformance_scoring
    6. conformance_scoring → [generate_code | self_correction | human_review]
    7. self_correction → [generate_mappings | human_review]
    8. generate_code → load_neo4j → upload_s3 → generate_report → END
    """

    # Create the graph with state schema
    workflow = StateGraph(SDTMPipelineState)

    # Add all nodes
    workflow.add_node("ingest_data", ingest_data_node)
    workflow.add_node("validate_raw_data", validate_raw_data_parallel_node)
    workflow.add_node("generate_mappings", generate_mappings_parallel_node)
    workflow.add_node("transform", transform_to_sdtm_parallel_node)
    workflow.add_node("validate_sdtm", validate_sdtm_parallel_node)
    workflow.add_node("conformance_scoring", conformance_scoring_node)
    workflow.add_node("self_correction", self_correction_node)
    workflow.add_node("generate_code", generate_code_parallel_node)
    workflow.add_node("load_neo4j", load_to_neo4j_node)
    workflow.add_node("upload_s3", upload_to_s3_node)
    workflow.add_node("generate_report", generate_report_node)
    workflow.add_node("human_review", human_review_node)

    # Set entry point
    workflow.set_entry_point("ingest_data")

    # Add edges - Main flow
    workflow.add_edge("ingest_data", "validate_raw_data")

    # Conditional: After raw validation
    workflow.add_conditional_edges(
        "validate_raw_data",
        should_continue_after_raw_validation,
        {
            "human_review": "human_review",
            "generate_mappings": "generate_mappings"
        }
    )

    # Mappings -> Transform (removed mandatory human review for faster iteration)
    workflow.add_edge("generate_mappings", "transform")

    # Transform -> Validate SDTM
    workflow.add_edge("transform", "validate_sdtm")

    # Validate SDTM -> Conformance Scoring
    workflow.add_edge("validate_sdtm", "conformance_scoring")

    # Conformance Scoring routing (self-correction loop)
    workflow.add_conditional_edges(
        "conformance_scoring",
        route_after_conformance_scoring,
        {
            "generate_code": "generate_code",
            "self_correction": "self_correction",
            "human_review": "human_review"
        }
    )

    # Self-correction routing
    workflow.add_conditional_edges(
        "self_correction",
        route_after_self_correction,
        {
            "generate_mappings": "generate_mappings",  # Retry loop
            "human_review": "human_review"
        }
    )

    # Human review routing (updated)
    def route_after_human_review_v2(
        state: SDTMPipelineState
    ) -> Literal["generate_mappings", "transform", "generate_code", "load_neo4j", "end"]:
        """Enhanced routing after human review."""
        decision = state.get("human_decision", "approve")
        if decision.lower() == "reject":
            return "end"

        pending = state.get("pending_review", "")
        current_phase = state.get("current_phase", "")

        # If approved after max iterations, continue to code generation
        if "max_iterations" in pending:
            return "generate_code"

        if "raw_validation" in pending or "raw_validation" in current_phase:
            return "generate_mappings"
        elif "mapping" in pending or "mapping" in current_phase:
            return "transform"
        elif "sdtm_validation" in pending or "sdtm_validation" in current_phase:
            return "generate_code"
        elif "final" in pending:
            return "load_neo4j"

        return "generate_mappings"

    workflow.add_conditional_edges(
        "human_review",
        route_after_human_review_v2,
        {
            "generate_mappings": "generate_mappings",
            "transform": "transform",
            "generate_code": "generate_code",
            "load_neo4j": "load_neo4j",
            "end": END
        }
    )

    # Code generation -> Neo4j -> S3 -> Report
    workflow.add_edge("generate_code", "load_neo4j")
    workflow.add_edge("load_neo4j", "upload_s3")
    workflow.add_edge("upload_s3", "generate_report")
    workflow.add_edge("generate_report", END)

    return workflow


# ============================================================================
# Compiled Graph Export (for langgraph dev)
# ============================================================================

# Build and compile the graph
# Note: Do NOT pass checkpointer here - langgraph dev handles persistence automatically
_workflow = build_sdtm_graph()
graph = _workflow.compile()

# Export graph info
__all__ = ["graph", "build_sdtm_graph", "SDTMPipelineState", "PipelineInput", "PipelineOutput"]

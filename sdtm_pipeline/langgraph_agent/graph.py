"""
SDTM Pipeline Graph Export (7-Phase ETL Pipeline)
=================================================

Exports the compiled LangGraph for use with `langgraph dev`.

This implements the 7-phase SDTM ETL process:
1. Data Ingestion (Extract) - Phase 1
2. Raw Data Validation (Business Checks) - Phase 2
3. Metadata and Specification Preparation - Phase 3
4. SDTM Transformation (Transform) - Phase 4
5. SDTM Target Data Generation (Load) - Phase 5
6. Target Data Validation (Compliance Checks) - Phase 6
7. Data Warehouse Loading - Phase 7

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

Author: SDTM ETL Pipeline
Version: 2.0.0 (Enhanced with 7-phase pipeline support)
"""

import os
import sys
from typing import Dict, Any, List, Literal, Optional
from typing_extensions import TypedDict
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig

# Ensure the package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Use absolute imports
from sdtm_pipeline.langgraph_agent.state import (
    SDTMPipelineState,
    create_initial_state,
    PIPELINE_PHASES,
    get_next_phase,
    get_pipeline_progress
)
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
    config: RunnableConfig
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
    config: RunnableConfig
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
# Phase 5: Target Data Generation (Define.xml)
# ============================================================================

async def generate_define_xml_node(
    state: SDTMPipelineState,
    config: RunnableConfig
) -> Dict[str, Any]:
    """
    Phase 5: Generate Define.xml and finalize SDTM datasets.

    Define.xml is the machine-readable metadata file required for FDA submissions.
    """
    from datetime import datetime
    import os

    print("\n" + "=" * 60)
    print("PHASE 5: TARGET DATA GENERATION")
    print("=" * 60)

    study_id = state.get("study_id", "UNKNOWN")
    output_dir = state.get("output_dir", "./output")
    sdtm_data_paths = state.get("sdtm_data_paths", {})

    # Import Define.xml generator
    try:
        from sdtm_pipeline.generators.define_xml_generator import (
            create_define_xml_generator,
            DefineXMLGenerator
        )
        DEFINE_AVAILABLE = True
    except ImportError:
        DEFINE_AVAILABLE = False
        print("  Warning: Define.xml generator not available")

    define_xml_info = {}
    define_xml_path = ""

    if DEFINE_AVAILABLE and sdtm_data_paths:
        try:
            # Get list of domains created
            domains = list(sdtm_data_paths.keys())
            print(f"  Generating Define.xml for domains: {domains}")

            # Create Define.xml generator
            generator = create_define_xml_generator(
                study_id=study_id,
                study_name=f"Study {study_id}",
                protocol_name=study_id,
                sdtmig_version=state.get("sdtmig_version", "3.4"),
                domains=domains
            )

            # Generate Define.xml
            define_path = os.path.join(output_dir, "define.xml")
            os.makedirs(output_dir, exist_ok=True)

            xml_content = generator.generate(define_path)
            define_xml_path = define_path

            # Save metadata JSON
            metadata_path = os.path.join(output_dir, "define_metadata.json")
            generator.save_metadata_json(metadata_path)

            define_xml_info = {
                "file_path": define_path,
                "study_oid": f"STUDY.{study_id}",
                "datasets_count": len(generator.datasets),
                "codelists_count": len(generator.codelists),
                "generated_at": datetime.utcnow().isoformat(),
                "sdtmig_version": state.get("sdtmig_version", "3.4"),
                "define_version": "2.1.0"
            }

            print(f"  Define.xml generated: {define_path}")
            print(f"    - Datasets: {define_xml_info['datasets_count']}")
            print(f"    - Codelists: {define_xml_info['codelists_count']}")

        except Exception as e:
            print(f"  Error generating Define.xml: {e}")
            define_xml_info = {"error": str(e)}

    # Build SDTM datasets info
    sdtm_datasets = {}
    for domain, path in sdtm_data_paths.items():
        sdtm_datasets[domain] = {
            "path": path,
            "domain": domain,
            "generated_at": datetime.utcnow().isoformat()
        }

    print(f"  Phase 5 complete: {len(sdtm_datasets)} datasets finalized")

    return {
        "current_phase": "target_data_generation",
        "phase_5_complete": True,
        "define_xml_info": define_xml_info,
        "define_xml_path": define_xml_path,
        "sdtm_datasets": sdtm_datasets,
        "phase_history": ["target_data_generation"],
        "messages": [f"Phase 5 complete: Define.xml generated for {len(sdtm_datasets)} domains"]
    }


# ============================================================================
# Build the Graph
# ============================================================================

def build_sdtm_graph() -> StateGraph:
    """
    Build the SDTM transformation pipeline graph.

    7-Phase SDTM ETL Pipeline Flow:
    ==============================
    Phase 1: Data Ingestion (Extract)
        → ingest_data node

    Phase 2: Raw Data Validation (Business Checks)
        → validate_raw_data node
        → If critical errors: human_review checkpoint

    Phase 3: Metadata and Specification Preparation
        → generate_mappings node (creates SDTM Mapping Specification)

    Phase 4: SDTM Transformation (Transform)
        → transform node (applies mapping logic)

    Phase 5: SDTM Target Data Generation (Load)
        → generate_define_xml node (creates Define.xml)
        → validate_sdtm node

    Phase 6: Target Data Validation (Compliance Checks)
        → conformance_scoring node
        → Self-correction loop (up to 3 iterations)
        → If score < 95%: human_review checkpoint

    Phase 7: Data Warehouse Loading
        → generate_code node (SAS/R programs)
        → load_neo4j node
        → upload_s3 node
        → generate_report node
    """

    # Create the graph with state schema
    workflow = StateGraph(SDTMPipelineState)

    # =========================================================================
    # Phase 1: Data Ingestion
    # =========================================================================
    workflow.add_node("ingest_data", ingest_data_node)

    # =========================================================================
    # Phase 2: Raw Data Validation (Business Checks)
    # =========================================================================
    workflow.add_node("validate_raw_data", validate_raw_data_parallel_node)

    # =========================================================================
    # Phase 3: Metadata and Specification Preparation
    # =========================================================================
    workflow.add_node("generate_mappings", generate_mappings_parallel_node)

    # =========================================================================
    # Phase 4: SDTM Transformation
    # =========================================================================
    workflow.add_node("transform", transform_to_sdtm_parallel_node)

    # =========================================================================
    # Phase 5: Target Data Generation (Define.xml)
    # =========================================================================
    workflow.add_node("generate_define_xml", generate_define_xml_node)

    # =========================================================================
    # Phase 6: Target Data Validation (Compliance Checks)
    # =========================================================================
    workflow.add_node("validate_sdtm", validate_sdtm_parallel_node)
    workflow.add_node("conformance_scoring", conformance_scoring_node)
    workflow.add_node("self_correction", self_correction_node)

    # =========================================================================
    # Phase 7: Data Warehouse Loading
    # =========================================================================
    workflow.add_node("generate_code", generate_code_parallel_node)
    workflow.add_node("load_neo4j", load_to_neo4j_node)
    workflow.add_node("upload_s3", upload_to_s3_node)
    workflow.add_node("generate_report", generate_report_node)

    # Human Review (used at multiple checkpoints)
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

    # Phase 3 -> Phase 4: Mappings -> Transform
    workflow.add_edge("generate_mappings", "transform")

    # Phase 4 -> Phase 5: Transform -> Generate Define.xml
    workflow.add_edge("transform", "generate_define_xml")

    # Phase 5 -> Phase 6: Generate Define.xml -> Validate SDTM
    workflow.add_edge("generate_define_xml", "validate_sdtm")

    # Phase 6: Validate SDTM -> Conformance Scoring
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

"""
SDTM Pipeline Graph Export
==========================
Exports the compiled LangGraph for use with `langgraph dev`.

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


# Load environment variables
load_dotenv()

# Configure LangSmith
configure_langsmith()


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
        description="Default decision for human review checkpoints (approve/reject)"
    )


class PipelineOutput(BaseModel):
    """Output schema for the SDTM pipeline."""
    study_id: str = Field(description="Study identifier")
    status: str = Field(description="Pipeline completion status")
    sdtm_domains_created: int = Field(description="Number of SDTM domains created")
    total_records: int = Field(description="Total SDTM records transformed")
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


# ============================================================================
# Build the Graph
# ============================================================================

def build_sdtm_graph() -> StateGraph:
    """Build the SDTM transformation pipeline graph."""

    # Create the graph with state schema
    workflow = StateGraph(SDTMPipelineState)

    # Add all nodes
    workflow.add_node("ingest_data", ingest_data_node)
    workflow.add_node("validate_raw_data", validate_raw_data_parallel_node)
    workflow.add_node("generate_mappings", generate_mappings_parallel_node)
    workflow.add_node("transform", transform_to_sdtm_parallel_node)
    workflow.add_node("validate_sdtm", validate_sdtm_parallel_node)
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

    # Mappings always go to human review
    workflow.add_edge("generate_mappings", "human_review")

    # Human review routing
    workflow.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            "generate_mappings": "generate_mappings",
            "transform": "transform",
            "generate_code": "generate_code",
            "end": END
        }
    )

    # Transform -> Validate SDTM
    workflow.add_edge("transform", "validate_sdtm")

    # Conditional: After SDTM validation
    workflow.add_conditional_edges(
        "validate_sdtm",
        should_continue_after_sdtm_validation,
        {
            "human_review": "human_review",
            "generate_code": "generate_code"
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

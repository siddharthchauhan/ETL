"""
SDTM LangGraph Agent
====================
Main LangGraph agent for SDTM transformation pipeline with:
- Async parallel execution
- LangSmith observability
- Supervisor hierarchy pattern
- Neo4j and S3 integration
"""

import os
from typing import Dict, Any, List, Literal, Optional
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import traceable

from .state import SDTMPipelineState, create_initial_state
from .async_nodes import (
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
from .config import configure_langsmith
from .tools import ALL_TOOLS


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


def should_continue_after_mapping(
    state: SDTMPipelineState
) -> Literal["human_review", "transform"]:
    """Determine if human review is needed after mapping generation."""
    return "human_review"


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
# Create the Full Async LangGraph
# ============================================================================

def create_sdtm_agent(
    checkpointer: Optional[MemorySaver] = None,
    enable_human_review: bool = True,
    enable_neo4j: bool = True,
    enable_s3: bool = True
) -> StateGraph:
    """
    Create the SDTM transformation pipeline as a LangGraph.

    Features:
    - Async parallel node execution
    - LangSmith tracing integration
    - Human-in-the-loop checkpoints
    - Neo4j graph database loading
    - S3 upload for processed data

    Args:
        checkpointer: Optional checkpointer for state persistence
        enable_human_review: Enable human-in-the-loop checkpoints
        enable_neo4j: Enable Neo4j data loading
        enable_s3: Enable S3 upload

    Returns:
        Compiled LangGraph
    """
    # Create the graph
    workflow = StateGraph(SDTMPipelineState)

    # Add async nodes
    workflow.add_node("ingest_data", ingest_data_node)
    workflow.add_node("validate_raw_data", validate_raw_data_parallel_node)
    workflow.add_node("generate_mappings", generate_mappings_parallel_node)
    workflow.add_node("transform", transform_to_sdtm_parallel_node)
    workflow.add_node("validate_sdtm", validate_sdtm_parallel_node)
    workflow.add_node("generate_code", generate_code_parallel_node)

    if enable_neo4j:
        workflow.add_node("load_neo4j", load_to_neo4j_node)

    if enable_s3:
        workflow.add_node("upload_s3", upload_to_s3_node)

    workflow.add_node("generate_report", generate_report_node)

    if enable_human_review:
        workflow.add_node("human_review", human_review_node)

    # Set entry point
    workflow.set_entry_point("ingest_data")

    # Add edges
    workflow.add_edge("ingest_data", "validate_raw_data")

    if enable_human_review:
        # With human review checkpoints
        workflow.add_conditional_edges(
            "validate_raw_data",
            should_continue_after_raw_validation,
            {
                "human_review": "human_review",
                "generate_mappings": "generate_mappings"
            }
        )

        workflow.add_edge("generate_mappings", "human_review")

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

        workflow.add_edge("transform", "validate_sdtm")

        workflow.add_conditional_edges(
            "validate_sdtm",
            should_continue_after_sdtm_validation,
            {
                "human_review": "human_review",
                "generate_code": "generate_code"
            }
        )
    else:
        # Direct flow without human review
        workflow.add_edge("validate_raw_data", "generate_mappings")
        workflow.add_edge("generate_mappings", "transform")
        workflow.add_edge("transform", "validate_sdtm")
        workflow.add_edge("validate_sdtm", "generate_code")

    # Code generation to Neo4j/S3/Report
    if enable_neo4j and enable_s3:
        workflow.add_edge("generate_code", "load_neo4j")
        workflow.add_edge("load_neo4j", "upload_s3")
        workflow.add_edge("upload_s3", "generate_report")
    elif enable_neo4j:
        workflow.add_edge("generate_code", "load_neo4j")
        workflow.add_edge("load_neo4j", "generate_report")
    elif enable_s3:
        workflow.add_edge("generate_code", "upload_s3")
        workflow.add_edge("upload_s3", "generate_report")
    else:
        workflow.add_edge("generate_code", "generate_report")

    workflow.add_edge("generate_report", END)

    # Compile the graph
    if checkpointer:
        return workflow.compile(checkpointer=checkpointer)
    else:
        return workflow.compile(checkpointer=MemorySaver())


# ============================================================================
# Run Pipeline Function
# ============================================================================

@traceable(name="sdtm_pipeline")
async def run_sdtm_agent_pipeline(
    study_id: str,
    raw_data_dir: str,
    output_dir: str,
    api_key: str,
    source_files: List[Dict[str, Any]],
    human_decision: str = "approve",
    enable_human_review: bool = True,
    enable_neo4j: bool = True,
    enable_s3: bool = True
) -> Dict[str, Any]:
    """
    Run the complete SDTM transformation pipeline with async execution.

    Args:
        study_id: Study identifier
        raw_data_dir: Directory containing raw data files
        output_dir: Output directory for results
        api_key: Anthropic API key
        source_files: List of source file information
        human_decision: Default human decision for review checkpoints
        enable_human_review: Enable human-in-the-loop checkpoints
        enable_neo4j: Enable Neo4j loading
        enable_s3: Enable S3 upload

    Returns:
        Final pipeline state
    """
    print("\n" + "=" * 70)
    print("   SDTM LANGGRAPH AGENT PIPELINE")
    print(f"   Study: {study_id}")
    print(f"   Started: {datetime.now().isoformat()}")
    print("=" * 70)

    # Configure LangSmith for observability
    configure_langsmith()

    print("\n LangSmith tracing enabled - view at https://smith.langchain.com")

    # Create checkpointer for state persistence
    checkpointer = MemorySaver()

    # Create the agent
    agent = create_sdtm_agent(
        checkpointer=checkpointer,
        enable_human_review=enable_human_review,
        enable_neo4j=enable_neo4j,
        enable_s3=enable_s3
    )

    # Create initial state
    initial_state = create_initial_state(
        study_id=study_id,
        raw_data_dir=raw_data_dir,
        output_dir=output_dir,
        api_key=api_key
    )

    # Add source files and human decision
    initial_state["selected_files"] = source_files
    initial_state["human_decision"] = human_decision

    # Run the pipeline with async streaming
    config = {"configurable": {"thread_id": f"sdtm_pipeline_{study_id}"}}

    final_state = None
    async for event in agent.astream(initial_state, config):
        for node_name, node_output in event.items():
            if node_name != "__end__":
                print(f"\n[Event] Node: {node_name}")
                if isinstance(node_output, dict):
                    phase = node_output.get("current_phase", "")
                    if phase:
                        print(f"  Phase: {phase}")
                    messages = node_output.get("messages", [])
                    for msg in messages[-3:]:
                        print(f"  > {msg}")

        final_state = event

    # Extract final report
    if final_state and "generate_report" in final_state:
        return final_state["generate_report"].get("final_report", {})
    elif final_state:
        for key, value in final_state.items():
            if isinstance(value, dict) and "final_report" in value:
                return value["final_report"]

    return {"status": "completed", "state": final_state}


# ============================================================================
# Synchronous Wrapper
# ============================================================================

def run_sdtm_pipeline_sync(
    study_id: str,
    raw_data_dir: str,
    output_dir: str,
    api_key: str,
    source_files: List[Dict[str, Any]],
    human_decision: str = "approve",
    enable_human_review: bool = True,
    enable_neo4j: bool = True,
    enable_s3: bool = True
) -> Dict[str, Any]:
    """
    Synchronous wrapper for running the SDTM pipeline.
    """
    import asyncio

    return asyncio.run(run_sdtm_agent_pipeline(
        study_id=study_id,
        raw_data_dir=raw_data_dir,
        output_dir=output_dir,
        api_key=api_key,
        source_files=source_files,
        human_decision=human_decision,
        enable_human_review=enable_human_review,
        enable_neo4j=enable_neo4j,
        enable_s3=enable_s3
    ))


# ============================================================================
# Visualize Graph
# ============================================================================

def visualize_sdtm_graph(output_path: str = "sdtm_pipeline_graph"):
    """Generate a visualization of the SDTM pipeline graph."""
    agent = create_sdtm_agent(enable_human_review=True, enable_neo4j=True, enable_s3=True)

    try:
        # Generate PNG
        png_data = agent.get_graph().draw_mermaid_png()
        with open(f"{output_path}.png", "wb") as f:
            f.write(png_data)
        print(f"Graph visualization saved to {output_path}.png")
    except Exception as e:
        # Fallback to mermaid text
        print("Graph visualization (Mermaid format):")
        mermaid = agent.get_graph().draw_mermaid()
        print(mermaid)
        with open(f"{output_path}.md", "w") as f:
            f.write(f"```mermaid\n{mermaid}\n```")
        print(f"Mermaid saved to {output_path}.md")


# ============================================================================
# Get Graph Info
# ============================================================================

def get_graph_info() -> Dict[str, Any]:
    """Get information about the pipeline graph structure."""
    agent = create_sdtm_agent(enable_human_review=True, enable_neo4j=True, enable_s3=True)
    graph = agent.get_graph()

    return {
        "nodes": list(graph.nodes.keys()),
        "edges": [(e[0], e[1]) for e in graph.edges],
        "entry_point": "ingest_data",
        "features": {
            "async_execution": True,
            "parallel_processing": True,
            "human_in_the_loop": True,
            "langsmith_tracing": True,
            "neo4j_integration": True,
            "s3_integration": True
        }
    }

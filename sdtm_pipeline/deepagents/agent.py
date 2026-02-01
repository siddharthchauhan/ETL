"""
SDTM Deep Agent
===============
Main DeepAgent implementation for SDTM transformation pipeline.

This is the unified SDTM agent that combines:
- DeepAgents architecture (planning, subagent delegation, filesystem backend)
- SDTM Chat capabilities (interactive conversion, knowledge base, web search)
- 18 Skills for progressive disclosure of domain expertise

Architecture:
- Main orchestrator agent with planning capabilities
- Specialized subagents for domain-specific tasks
- Filesystem backend for context management
- 27 tools for complete SDTM pipeline operations
- 18 skills for progressive disclosure of domain expertise

Skills (18 total - automatically loaded based on task context):
- cdisc-standards: SDTM domain knowledge, controlled terminology, protocols
- sdtm-programming: Python/SAS/R transformation patterns, ETL design
- qa-validation: Pinnacle 21 rules, Define.xml, conformance scoring
- mapping-specifications: Transformation DSL, mapping spec parsing
- mapping-scenarios: 9 fundamental SDTM mapping patterns
- sdtm-mapping: End-to-end raw-to-SDTM conversion following CDISC standards
- clinical-domains: AE, DS, MH, CM, EX event/intervention domains
- special-purpose-domains: DM, CO, SE, SV one-record domains
- findings-domains: VS, LB, EG, PE vertical data structures
- lb-domain-transformation: LB horizontal-to-vertical MELT, test code mapping
- trial-design-domains: TA, TE, TV, TI, TS study design
- datetime-handling: ISO 8601, partial dates, study day calculations
- data-loading: S3 ingestion, EDC extraction, file scanning
- neo4j-s3-integration: Graph loading, S3 uploads
- knowledge-base: Pinecone queries, CDISC guidance retrieval
- pipeline-orchestration: 7-phase ETL flow, subagent delegation
- validation-best-practices: Error resolution, compliance strategies
- document-generation: PowerPoint, Excel, Word, CSV, PDF creation
"""

import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from deepagents import create_deep_agent, SubAgent
from deepagents.backends import FilesystemBackend
from dotenv import load_dotenv

load_dotenv()

from .subagents import (
    SDTM_EXPERT_SUBAGENT,
    VALIDATOR_SUBAGENT,
    TRANSFORMER_SUBAGENT,
    CODE_GENERATOR_SUBAGENT,
    DATA_LOADER_SUBAGENT,
)
from .tools import SDTM_TOOLS
from .prompts import SDTM_SYSTEM_PROMPT


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class SDTMAgentConfig:
    """Configuration for SDTM Deep Agent."""

    # Study information
    study_id: str = "UNKNOWN"

    # Model configuration
    model: str = field(default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "anthropic:claude-sonnet-4-5-20250929"))

    # Paths
    workspace_dir: str = "./sdtm_workspace"
    output_dir: str = "./sdtm_deepagent_output"
    skills_dir: str = field(default_factory=lambda: str(Path(__file__).parent / "skills"))

    # S3 configuration
    s3_bucket: str = field(default_factory=lambda: os.getenv("S3_ETL_BUCKET", "s3dcri"))
    s3_incoming_prefix: str = "incoming"
    s3_processed_prefix: str = "processed/sdtm"

    # Neo4j configuration
    neo4j_uri: str = field(default_factory=lambda: os.getenv("NEO4J_URI", "neo4j://localhost:7687"))
    neo4j_user: str = field(default_factory=lambda: os.getenv("NEO4J_USER", "neo4j"))
    neo4j_password: str = field(default_factory=lambda: os.getenv("NEO4J_PASSWORD", ""))

    # Feature flags
    enable_human_review: bool = True
    enable_neo4j: bool = True
    enable_s3: bool = True

    # Validation thresholds
    min_compliance_score: float = 95.0
    max_critical_errors: int = 0

    # LangGraph configuration
    recursion_limit: int = field(default_factory=lambda: int(os.getenv("LANGGRAPH_RECURSION_LIMIT", "50")))


# =============================================================================
# HUMAN-IN-THE-LOOP CONFIGURATION
# =============================================================================

HITL_CONFIG = {
    # Require approval for destructive operations
    "transform_to_sdtm": True,
    "load_to_neo4j": True,
    "upload_to_s3": True,
}


# =============================================================================
# CREATE DEEP AGENT
# =============================================================================

def create_sdtm_deep_agent(
    config: Optional[SDTMAgentConfig] = None,
) -> Any:
    """
    Create the SDTM Deep Agent with full pipeline capabilities.

    Architecture:
    - Main orchestrator agent with planning (write_todos)
    - Filesystem backend for context management
    - 5 specialized subagents for domain expertise
    - 18 skills for progressive disclosure of domain knowledge

    Skills (18 total - loaded from skills_dir, automatically discovered):

    Args:
        config: Agent configuration options

    Returns:
        Compiled DeepAgent ready for invocation
    """
    config = config or SDTMAgentConfig()

    # Setup filesystem backend
    os.makedirs(config.workspace_dir, exist_ok=True)
    os.makedirs(config.output_dir, exist_ok=True)

    # Use FilesystemBackend for real file operations
    backend = FilesystemBackend(root_dir=config.workspace_dir)

    # Collect subagents
    subagents = [
        SubAgent(SDTM_EXPERT_SUBAGENT),
        SubAgent(VALIDATOR_SUBAGENT),
        SubAgent(TRANSFORMER_SUBAGENT),
        SubAgent(CODE_GENERATOR_SUBAGENT),
    ]

    # Add data loader subagent if Neo4j/S3 enabled
    if config.enable_neo4j or config.enable_s3:
        subagents.append(SubAgent(DATA_LOADER_SUBAGENT))

    # Configure HITL if enabled
    interrupt_config = HITL_CONFIG if config.enable_human_review else None

    # Setup skills directory - skills provide progressive disclosure of domain expertise
    # The agent will only load skill content when relevant to the current task
    skills_paths = [config.skills_dir] if os.path.isdir(config.skills_dir) else []

    # Create the deep agent with skills
    agent = create_deep_agent(
        model=config.model,
        tools=SDTM_TOOLS,
        system_prompt=SDTM_SYSTEM_PROMPT,
        subagents=subagents,
        backend=backend,
        skills=skills_paths,
        interrupt_on=interrupt_config,
    )

    # Apply recursion limit for complex SDTM pipelines
    # Default LangGraph limit is 25, but SDTM transformations with
    # subagents, skills, and multiple tool calls often need more steps
    agent = agent.with_config(recursion_limit=config.recursion_limit)

    return agent


# =============================================================================
# RUN PIPELINE
# =============================================================================

async def run_sdtm_pipeline(
    study_id: str,
    source_files: List[Dict[str, Any]],
    config: Optional[SDTMAgentConfig] = None,
) -> Dict[str, Any]:
    """
    Run the complete SDTM transformation pipeline using DeepAgents.

    The agent will:
    1. Plan the transformation using write_todos
    2. Delegate to specialized subagents
    3. Use filesystem for context management
    4. Request human approval for critical operations
    5. Generate comprehensive final report

    Args:
        study_id: Study identifier
        source_files: List of source file information
        config: Agent configuration

    Returns:
        Pipeline execution results
    """
    config = config or SDTMAgentConfig()
    config.study_id = study_id

    print("\n" + "=" * 70)
    print("   SDTM DEEP AGENT PIPELINE")
    print(f"   Study: {study_id}")
    print(f"   Started: {datetime.now().isoformat()}")
    print("=" * 70)

    # Create the agent
    agent = create_sdtm_deep_agent(config)

    # Prepare initial message with task description
    source_file_summary = "\n".join([
        f"  - {f['name']} -> {f.get('target_domain', 'TBD')} ({f.get('size_kb', 0):.1f} KB)"
        for f in source_files[:10]
    ])
    if len(source_files) > 10:
        source_file_summary += f"\n  ... and {len(source_files) - 10} more files"

    initial_message = f"""Create a todo list plan for SDTM transformation of study {study_id}.

Source files to process:
{source_file_summary}

Create a brief plan with write_todos listing the key steps needed."""

    # Run the agent
    print("\nSending task to agent...")

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": initial_message}]}
    )

    # Extract final report from agent response
    final_message = result.get("messages", [])[-1] if result.get("messages") else None

    final_report = {
        "study_id": study_id,
        "status": "completed",
        "generated_at": datetime.now().isoformat(),
        "agent_response": final_message.content if final_message else "",
        "config": {
            "model": config.model,
            "enable_human_review": config.enable_human_review,
            "enable_neo4j": config.enable_neo4j,
            "enable_s3": config.enable_s3,
        }
    }

    print("\n" + "=" * 70)
    print("   PIPELINE COMPLETED")
    print("=" * 70)

    return final_report


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_sdtm_agent(
    study_id: str = "UNKNOWN",
    enable_hitl: bool = False,
) -> Any:
    """
    Create a simplified SDTM agent for quick tasks.

    Args:
        study_id: Study identifier
        enable_hitl: Enable human-in-the-loop

    Returns:
        Compiled DeepAgent
    """
    config = SDTMAgentConfig(
        study_id=study_id,
        enable_human_review=enable_hitl,
        enable_neo4j=False,
        enable_s3=False,
    )
    return create_sdtm_deep_agent(config)


def get_agent_info() -> Dict[str, Any]:
    """Get information about the SDTM Deep Agent architecture."""
    return {
        "name": "SDTM Deep Agent",
        "version": "3.0.0",
        "architecture": "DeepAgents",
        "features": {
            "planning": "Built-in write_todos/read_todos",
            "filesystem": "Context management via ls/read_file/write_file/edit_file",
            "subagents": ["sdtm-expert", "validator", "transformer", "code-generator", "data-loader"],
            "hitl": "Configurable approval workflows",
        },
        "supported_domains": ["DM", "AE", "VS", "LB", "CM", "EX", "MH", "DS", "EG", "PE", "PC", "IE"],
    }

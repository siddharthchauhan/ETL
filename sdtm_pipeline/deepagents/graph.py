"""
SDTM DeepAgents Graph - Unified Agent
======================================
Entry point for LangGraph Studio (langgraph dev).

This module exports a unified SDTM agent that combines:
- DeepAgents architecture (planning, subagent delegation, filesystem backend)
- SDTM Chat capabilities (interactive conversion, knowledge base, web search)
- Skills for progressive disclosure of domain expertise

Skills:
- cdisc-standards: SDTM domain knowledge, controlled terminology, protocols
- sdtm-programming: Python/SAS/R transformation patterns, ETL design
- qa-validation: Pinnacle 21 rules, Define.xml, conformance scoring

Use with:
- langgraph dev (local development UI)
- LangGraph Cloud deployment
- LangSmith tracing and debugging
"""

import os
from pathlib import Path
from typing import Any, Optional
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# =============================================================================
# RECURSION LIMIT CONFIGURATION
# =============================================================================
RECURSION_LIMIT = int(os.getenv("LANGGRAPH_RECURSION_LIMIT", "250"))
print(f"[SDTM Graph] Using recursion_limit={RECURSION_LIMIT}")

from deepagents import create_deep_agent, SubAgent
from deepagents.backends import FilesystemBackend
from langgraph.graph.state import CompiledStateGraph

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
# SKILLS CONFIGURATION
# =============================================================================

# Skills directory - contains SDTM domain expertise
SKILLS_DIR = Path(__file__).parent / "skills"


# =============================================================================
# CREATE GRAPH FOR LANGGRAPH DEV
# =============================================================================


def create_graph() -> CompiledStateGraph:
    """
    Create the SDTM DeepAgent graph for LangGraph Studio.

    The agent is equipped with:
    - 27 SDTM-specific tools
    - 5 specialized subagents
    - 3 skills for domain expertise (progressive disclosure)
    - Filesystem backend for context management
    - Recursion limit of 250 (configurable via LANGGRAPH_RECURSION_LIMIT env var)

    Returns:
        Compiled StateGraph ready for langgraph dev
    """
    # Setup workspace
    workspace_dir = os.getenv("SDTM_WORKSPACE", "./sdtm_workspace")
    os.makedirs(workspace_dir, exist_ok=True)

    # Use FilesystemBackend for real file operations
    backend = FilesystemBackend(root_dir=workspace_dir)

    # Collect subagents
    subagents = [
        SubAgent(SDTM_EXPERT_SUBAGENT),
        SubAgent(VALIDATOR_SUBAGENT),
        SubAgent(TRANSFORMER_SUBAGENT),
        SubAgent(CODE_GENERATOR_SUBAGENT),
        SubAgent(DATA_LOADER_SUBAGENT),
    ]

    # Get model from environment
    model = os.getenv("ANTHROPIC_MODEL", "anthropic:claude-sonnet-4-5-20250929")

    # Setup skills - provides progressive disclosure of domain expertise
    # Skills are only loaded when relevant to the current task
    skills_paths = [str(SKILLS_DIR)] if SKILLS_DIR.is_dir() else []

    # Create the deep agent with skills
    agent = create_deep_agent(
        model=model,
        tools=SDTM_TOOLS,
        system_prompt=SDTM_SYSTEM_PROMPT,
        subagents=subagents,
        backend=backend,
        skills=skills_paths,
    )

    # Apply recursion limit - CRITICAL for complex SDTM pipelines
    # Default LangGraph limit is 25, but SDTM transformations with
    # subagents, skills, and multiple tool calls often need more steps
    agent = agent.with_config(recursion_limit=RECURSION_LIMIT)

    print(f"[SDTM Graph] Created agent with model={model}, recursion_limit={RECURSION_LIMIT}")
    return agent


# Export the graph for langgraph dev
# This is what langgraph.json points to
# Recursion limit is applied via .with_config() in create_graph()
graph = create_graph()
print(f"[SDTM Graph] Graph exported with recursion_limit={RECURSION_LIMIT}")

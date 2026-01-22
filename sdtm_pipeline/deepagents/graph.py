"""
SDTM DeepAgents Graph - Unified Agent
======================================
Entry point for LangGraph Studio (langgraph dev).

This module exports a unified SDTM agent that combines:
- DeepAgents architecture (planning, subagent delegation, filesystem backend)
- SDTM Chat capabilities (interactive conversion, knowledge base, web search)

Use with:
- langgraph dev (local development UI)
- LangGraph Cloud deployment
- LangSmith tracing and debugging
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from deepagents import create_deep_agent, SubAgent
from deepagents.backends import FilesystemBackend

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
# CREATE GRAPH FOR LANGGRAPH DEV
# =============================================================================

def create_graph():
    """
    Create the SDTM DeepAgent graph for LangGraph Studio.

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

    # Create the deep agent
    agent = create_deep_agent(
        model=model,
        tools=SDTM_TOOLS,
        system_prompt=SDTM_SYSTEM_PROMPT,
        subagents=subagents,
        backend=backend,
    )

    return agent


# Export the graph for langgraph dev
# This is what langgraph.json points to
graph = create_graph()

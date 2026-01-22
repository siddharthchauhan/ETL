"""
SDTM DeepAgents Pipeline - Unified Agent
=========================================
DeepAgents-based architecture for SDTM transformation pipeline.

This module implements a unified SDTM agent that combines:
- DeepAgents architecture (planning, subagent delegation, filesystem backend)
- SDTM Chat capabilities (interactive conversion, knowledge base, web search)

Features:
- Planning with built-in todo tools
- Filesystem-based context management
- 5 specialized subagents for domain expertise
- 27 tools for complete SDTM pipeline operations
- Human-in-the-loop workflows
- Automatic context summarization

Author: SDTM ETL Pipeline
Version: 4.0.0 (Unified Agent Architecture)
"""

from .agent import (
    create_sdtm_deep_agent,
    run_sdtm_pipeline,
    SDTMAgentConfig,
    get_agent_info,
)

from .subagents import (
    SDTM_EXPERT_SUBAGENT,
    VALIDATOR_SUBAGENT,
    TRANSFORMER_SUBAGENT,
    CODE_GENERATOR_SUBAGENT,
    DATA_LOADER_SUBAGENT,
)

from .tools import SDTM_TOOLS, DEEPAGENT_TOOLS, CHAT_TOOLS
from .prompts import SDTM_SYSTEM_PROMPT

__all__ = [
    # Agent creation
    "create_sdtm_deep_agent",
    "run_sdtm_pipeline",
    "SDTMAgentConfig",
    "get_agent_info",
    # Subagents
    "SDTM_EXPERT_SUBAGENT",
    "VALIDATOR_SUBAGENT",
    "TRANSFORMER_SUBAGENT",
    "CODE_GENERATOR_SUBAGENT",
    "DATA_LOADER_SUBAGENT",
    # Tools
    "SDTM_TOOLS",
    "DEEPAGENT_TOOLS",
    "CHAT_TOOLS",
    # Prompts
    "SDTM_SYSTEM_PROMPT",
]

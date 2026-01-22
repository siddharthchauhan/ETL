"""
SDTM DeepAgents Pipeline - Unified Agent with Skills
=====================================================
DeepAgents-based architecture for SDTM transformation pipeline.

This module implements a unified SDTM agent that combines:
- DeepAgents architecture (planning, subagent delegation, filesystem backend)
- SDTM Chat capabilities (interactive conversion, knowledge base, web search)
- Skills for progressive disclosure of domain expertise

Features:
- Planning with built-in todo tools
- Filesystem-based context management
- 5 specialized subagents for domain expertise
- 27 tools for complete SDTM pipeline operations
- 3 skills for clinical data standards, programming, and validation
- Human-in-the-loop workflows
- Automatic context summarization

Skills:
- cdisc-standards: SDTM domain knowledge, controlled terminology, protocols
- sdtm-programming: Python/SAS/R patterns, date handling, ETL design
- qa-validation: Pinnacle 21 rules, Define.xml, conformance scoring

Author: SDTM ETL Pipeline
Version: 5.0.0 (Skills Architecture)
"""

from pathlib import Path

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

# Skills directory path for external access
SKILLS_DIR = Path(__file__).parent / "skills"

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
    # Skills
    "SKILLS_DIR",
]

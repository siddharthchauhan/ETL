"""
SDTM DeepAgents Pipeline - Unified Agent with Skills
=====================================================
DeepAgents-based architecture for SDTM transformation pipeline.

This module implements a unified SDTM agent that combines:
- DeepAgents architecture (planning, subagent delegation, filesystem backend)
- SDTM Chat capabilities (interactive conversion, knowledge base, web search)
- Skills for progressive disclosure of domain expertise
- Production-ready features: reasoning streams, reconnection, time travel

Features:
- Planning with built-in todo tools
- Filesystem-based context management
- 5 specialized subagents for domain expertise
- 27 tools for complete SDTM pipeline operations
- 15 skills for clinical data standards, programming, and validation
- Human-in-the-loop workflows
- Automatic context summarization

Production-Ready Features:
- Reasoning Agents: Stream thinking/reasoning separately from output
- Session Reconnection: Resume interrupted sessions seamlessly
- Branching & Time Travel: Fork conversations and navigate history

Skills:
- cdisc-standards: SDTM domain knowledge, controlled terminology, protocols
- sdtm-programming: Python/SAS/R patterns, date handling, ETL design
- qa-validation: Pinnacle 21 rules, Define.xml, conformance scoring
- mapping-specifications: Transformation DSL, mapping spec parsing
- mapping-scenarios: 9 fundamental SDTM mapping patterns
- clinical-domains: AE, DS, MH, CM, EX event/intervention domains
- special-purpose-domains: DM, CO, SE, SV one-record domains
- findings-domains: VS, LB, EG, PE vertical data structures
- trial-design-domains: TA, TE, TV, TI, TS study design
- datetime-handling: ISO 8601, partial dates, study day calculations
- data-loading: S3 ingestion, EDC extraction, file scanning
- neo4j-s3-integration: Graph loading, S3 uploads
- knowledge-base: Pinecone queries, CDISC guidance retrieval
- pipeline-orchestration: 7-phase ETL flow, subagent delegation
- validation-best-practices: Error resolution, compliance strategies

Author: SDTM ETL Pipeline
Version: 6.0.0 (Production-Ready Architecture)
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

# Production-ready session management
from .session_manager import (
    SessionManager,
    Session,
    SessionStatus,
    StreamChunk,
    StreamContentType,
    Checkpoint,
    ThinkingBlock,
    get_session_manager,
    create_session,
    get_session,
    create_checkpoint,
    time_travel,
    create_branch,
    switch_branch,
)

# Production graph
from .production_graph import (
    ProductionGraph,
    get_production_graph,
    stream_with_reasoning,
    reconnect_session,
    create_session_checkpoint,
    session_time_travel,
    create_session_branch,
)

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
    # Production-ready session management
    "SessionManager",
    "Session",
    "SessionStatus",
    "StreamChunk",
    "StreamContentType",
    "Checkpoint",
    "ThinkingBlock",
    "get_session_manager",
    "create_session",
    "get_session",
    "create_checkpoint",
    "time_travel",
    "create_branch",
    "switch_branch",
    # Production graph
    "ProductionGraph",
    "get_production_graph",
    "stream_with_reasoning",
    "reconnect_session",
    "create_session_checkpoint",
    "session_time_travel",
    "create_session_branch",
]

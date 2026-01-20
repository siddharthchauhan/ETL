"""
SDTM Chat Agent State
=====================
State definitions for the LangGraph-based SDTM conversion agent.
"""

from typing import Dict, List, Any, Optional, Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
import pandas as pd


class SDTMDataset(BaseModel):
    """Represents an SDTM dataset."""
    domain: str
    records: int
    columns: List[str]
    is_valid: bool = False
    errors: int = 0
    warnings: int = 0


class MappingInfo(BaseModel):
    """Mapping specification summary."""
    source: str
    target_domain: str
    mappings_count: int
    derivations: List[str] = []


class ValidationIssue(BaseModel):
    """A validation issue."""
    rule_id: str
    severity: str
    message: str
    variable: Optional[str] = None


class SDTMChatState(TypedDict):
    """
    State for the SDTM Chat Agent.

    This state is persisted across conversation turns and tracks:
    - Conversation messages
    - Loaded source data
    - Generated SDTM datasets
    - Mapping specifications
    - Validation results
    """
    # Conversation messages (automatically accumulated)
    messages: Annotated[list, add_messages]

    # Study information
    study_id: str

    # Source data status
    source_files: Dict[str, Dict[str, Any]]  # filename -> {domain, records, columns}
    data_loaded: bool

    # SDTM conversion status
    sdtm_datasets: Dict[str, Dict[str, Any]]  # domain -> {records, columns, is_valid}
    mapping_specs: Dict[str, Dict[str, Any]]  # domain -> mapping info

    # Validation status
    validation_results: Dict[str, Dict[str, Any]]  # domain -> validation result

    # Current operation tracking
    current_operation: Optional[str]
    operation_progress: List[str]  # Step-by-step progress messages

    # Knowledge retrieval cache
    retrieved_rules: Dict[str, List[Dict]]  # domain -> rules


def get_initial_state() -> SDTMChatState:
    """Get initial state for a new conversation."""
    return SDTMChatState(
        messages=[],
        study_id="UNKNOWN",
        source_files={},
        data_loaded=False,
        sdtm_datasets={},
        mapping_specs={},
        validation_results={},
        current_operation=None,
        operation_progress=[],
        retrieved_rules={}
    )

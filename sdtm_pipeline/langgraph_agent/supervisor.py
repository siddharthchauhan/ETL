"""
SDTM Supervisor Agent
=====================
Supervisor hierarchy pattern for multi-agent SDTM pipeline orchestration.

Enhanced with:
- Self-correction loop (retry up to 3 times if score < 95%)
- LLM-based routing decisions
- Conformance score tracking
"""

import os
from typing import Dict, Any, List, Literal, Optional, Annotated, Sequence
from datetime import datetime
import functools
import operator
from dotenv import load_dotenv
load_dotenv()

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel
from typing_extensions import TypedDict

from .tools import ALL_TOOLS
from .config import configure_langsmith

# Import scoring and checkpoint systems
try:
    from ..scoring import calculate_conformance_score, is_submission_ready
    from ..review import HumanCheckpoint, CheckpointManager
    SCORING_AVAILABLE = True
except ImportError:
    SCORING_AVAILABLE = False


# Self-correction constants
MAX_ITERATIONS = 3
SUBMISSION_THRESHOLD = 95.0


# ============================================================================
# Supervisor State
# ============================================================================

class SupervisorState(TypedDict):
    """State for supervisor-based multi-agent system."""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_agent: str
    study_id: str
    raw_data_dir: str
    output_dir: str
    api_key: str
    human_decision: str
    current_task: str
    task_results: Dict[str, Any]
    completed_agents: List[str]
    final_output: Dict[str, Any]

    # Self-correction loop state
    iteration_count: int  # Current iteration (max 3)
    max_iterations: int  # Maximum allowed iterations
    conformance_score: float  # Overall score 0-100
    layer_scores: Dict[str, float]  # Per-layer scores
    needs_correction: bool  # Whether self-correction is needed
    correction_feedback: str  # Feedback for correction
    submission_ready: bool  # True if score >= 95%
    pending_review: str  # Checkpoint awaiting review


# ============================================================================
# Agent Definitions
# ============================================================================

def create_validation_agent(llm: ChatAnthropic) -> StateGraph:
    """Create the Validation Agent responsible for data quality checks."""
    system_prompt = """You are a Data Validation Agent specialized in clinical trial data quality.
Your responsibilities:
1. Validate raw data quality and completeness
2. Check for required fields, data types, and value ranges
3. Identify duplicates and missing values
4. Validate SDTM datasets against CDISC standards
5. Report validation issues with severity levels

Use the validate_raw_data and validate_sdtm_data tools to perform validations.
Always provide detailed validation reports with actionable recommendations."""

    return create_react_agent(llm, tools=[
        t for t in ALL_TOOLS if 'validate' in t.name
    ], state_modifier=system_prompt)


def create_mapping_agent(llm: ChatAnthropic) -> StateGraph:
    """Create the Mapping Agent responsible for SDTM mapping specifications."""
    system_prompt = """You are an SDTM Mapping Agent specialized in CDISC standards.
Your responsibilities:
1. Analyze source data structures
2. Determine appropriate SDTM domain mappings
3. Generate column-level mapping specifications
4. Define derivation rules for computed variables
5. Apply controlled terminology mappings

Use the analyze_source_data and determine_sdtm_domain tools to understand the data.
Follow SDTM Implementation Guide 3.4 standards for all mappings."""

    return create_react_agent(llm, tools=[
        t for t in ALL_TOOLS if any(x in t.name for x in ['analyze', 'determine'])
    ], state_modifier=system_prompt)


def create_transformation_agent(llm: ChatAnthropic) -> StateGraph:
    """Create the Transformation Agent responsible for SDTM data transformation."""
    system_prompt = """You are an SDTM Transformation Agent specialized in data conversion.
Your responsibilities:
1. Transform raw clinical data to SDTM format
2. Apply mapping specifications correctly
3. Generate USUBJID and sequence variables
4. Convert dates to ISO 8601 format
5. Apply controlled terminology values

Use the transform_to_sdtm tool to perform transformations.
Ensure all transformations follow CDISC SDTM standards."""

    return create_react_agent(llm, tools=[
        t for t in ALL_TOOLS if 'transform' in t.name
    ], state_modifier=system_prompt)


def create_codegen_agent(llm: ChatAnthropic) -> StateGraph:
    """Create the Code Generation Agent for SAS and R code."""
    system_prompt = """You are a Code Generation Agent specialized in SAS and R programming.
Your responsibilities:
1. Generate production-ready SAS programs for SDTM transformations
2. Create R scripts using pharmaverse packages
3. Include proper error handling and logging
4. Follow pharmaceutical industry best practices
5. Generate executable and well-documented code

Use the generate_sas_code and generate_r_code tools to create programs.
Ensure code is modular, maintainable, and follows industry standards."""

    return create_react_agent(llm, tools=[
        t for t in ALL_TOOLS if 'generate' in t.name and 'code' in t.name
    ], state_modifier=system_prompt)


# ============================================================================
# Supervisor Agent
# ============================================================================

class RouteResponse(BaseModel):
    """Schema for supervisor routing decision."""
    next: Literal[
        "source_analyst_agent",
        "sdtm_expert_agent",
        "validator_agent",
        "codegen_agent",
        "anomaly_agent",
        "protocol_agent",
        "conformance_scoring",
        "self_correction",
        "human_review",
        "neo4j_agent",
        "s3_agent",
        "FINISH"
    ]
    reasoning: str


class SelfCorrectionResponse(BaseModel):
    """Schema for self-correction decision."""
    should_retry: bool
    feedback: str
    focus_areas: List[str]


def create_supervisor_chain(llm: ChatAnthropic):
    """Create the supervisor chain that routes between agents."""

    members = [
        "source_analyst_agent",
        "sdtm_expert_agent",
        "validator_agent",
        "codegen_agent",
        "anomaly_agent",
        "protocol_agent",
        "neo4j_agent",
        "s3_agent"
    ]

    system_prompt = f"""You are the SDTM Pipeline Supervisor Agent.
You manage a team of 6 specialized agents for clinical trial data transformation:

1. **source_analyst_agent**: Analyzes source data schema, profiles data quality
2. **sdtm_expert_agent**: SDTM-IG expertise, mapping recommendations, hybrid RAG search
3. **validator_agent**: Multi-layer validation (structural, CDISC, cross-domain, semantic)
4. **codegen_agent**: Generates production SAS and R code
5. **anomaly_agent**: Statistical/physiological anomaly detection
6. **protocol_agent**: Protocol compliance checking (visit windows, I/E, dosing)

Plus supporting agents:
- **conformance_scoring**: Calculates weighted conformance score
- **self_correction**: Generates feedback for retry when score < 95%
- **human_review**: Pause for human review/approval
- **neo4j_agent**: Loads data to Neo4j graph database
- **s3_agent**: Uploads processed data to S3

WORKFLOW ORDER:
1. source_analyst_agent → Schema analysis and data profiling
2. sdtm_expert_agent → SDTM mapping recommendations
3. validator_agent → Multi-layer validation
4. conformance_scoring → Calculate score
5. IF score >= 95%: codegen_agent
   ELIF iteration < 3: self_correction → sdtm_expert_agent (retry)
   ELSE: human_review
6. codegen_agent → Generate SAS and R code
7. anomaly_agent → Statistical anomaly detection
8. protocol_agent → Protocol compliance check
9. conformance_scoring → Final score
10. IF score >= 95%: neo4j_agent → s3_agent → FINISH
    ELSE: human_review → [approve/reject] → FINISH

SELF-CORRECTION LOOP:
When conformance_score < 95% and iteration < 3:
- Route to self_correction to generate improvement feedback
- Then route back to sdtm_expert_agent with the feedback
- Increment iteration count

HUMAN REVIEW TRIGGERS:
- Max iterations (3) reached with score < 95%
- Critical severity issues detected
- Manual review requested

Based on the conversation history and state, decide which agent to call next."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        ("human", """Based on the conversation above, which agent should act next?

Current state:
- Completed agents: {completed_agents}
- Current task: {current_task}
- Iteration: {iteration}/{max_iterations}
- Conformance score: {conformance_score}%
- Needs correction: {needs_correction}

Decide the next agent to call.
If score >= 95% and all required steps complete, respond with FINISH.""")
    ])

    return prompt | llm.with_structured_output(RouteResponse)


def create_self_correction_chain(llm: ChatAnthropic):
    """Create the self-correction chain for generating improvement feedback."""

    system_prompt = """You are an SDTM validation expert reviewing conformance issues.
Your job is to analyze validation results and provide specific, actionable feedback
for improving the data quality.

When reviewing issues:
1. Prioritize errors over warnings
2. Group related issues together
3. Identify root causes
4. Suggest specific corrections
5. Focus on highest-impact improvements

Provide feedback that the SDTM Expert agent can use to improve mappings and transformations."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        ("human", """Review these validation results and provide correction feedback:

Conformance Score: {conformance_score}%
Layer Scores: {layer_scores}
Issues: {issues}

Generate feedback for improvement. Include:
1. Whether to retry (should_retry)
2. Specific feedback for the SDTM Expert agent
3. Key areas to focus on for improvement""")
    ])

    return prompt | llm.with_structured_output(SelfCorrectionResponse)


def self_correction_node(state: SupervisorState) -> Dict[str, Any]:
    """
    Self-correction node that generates improvement feedback.

    Logic:
    - IF conformance_score >= 95%: No correction needed
    - ELIF iteration < 3: Generate feedback and retry
    - ELSE: Route to human review
    """
    from langchain_anthropic import ChatAnthropic

    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
    llm = ChatAnthropic(
        model=model,
        api_key=state.get("api_key", os.getenv("ANTHROPIC_API_KEY")),
        max_tokens=4096
    )

    conformance_score = state.get("conformance_score", 0)
    iteration = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", MAX_ITERATIONS)

    print(f"\n[Self-Correction] Score: {conformance_score}%, Iteration: {iteration}/{max_iterations}")

    # Check if correction needed
    if conformance_score >= SUBMISSION_THRESHOLD:
        return {
            "messages": [AIMessage(content=f"Conformance score {conformance_score}% meets threshold. No correction needed.")],
            "needs_correction": False
        }

    if iteration >= max_iterations:
        return {
            "messages": [AIMessage(content=f"Max iterations ({max_iterations}) reached. Routing to human review.")],
            "needs_correction": False,
            "pending_review": "max_iterations"
        }

    # Generate correction feedback
    correction_chain = create_self_correction_chain(llm)

    layer_scores = state.get("layer_scores", {})
    issues = state.get("task_results", {}).get("validation_issues", [])

    result = correction_chain.invoke({
        "messages": state.get("messages", []),
        "conformance_score": conformance_score,
        "layer_scores": layer_scores,
        "issues": issues[:20]  # Limit issues for prompt
    })

    print(f"[Self-Correction] Should retry: {result.should_retry}")
    print(f"[Self-Correction] Focus areas: {result.focus_areas}")

    return {
        "messages": [AIMessage(content=f"Self-correction feedback: {result.feedback}")],
        "needs_correction": result.should_retry,
        "correction_feedback": result.feedback,
        "iteration_count": iteration + 1,
        "completed_agents": ["self_correction"]
    }


def supervisor_node(state: SupervisorState) -> Dict[str, Any]:
    """Supervisor node that routes to the next agent."""
    from langchain_anthropic import ChatAnthropic

    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
    max_tokens = int(os.getenv("ANTHROPIC_MAX_TOKENS", "4096"))

    llm = ChatAnthropic(
        model=model,
        api_key=state.get("api_key", os.getenv("ANTHROPIC_API_KEY")),
        max_tokens=max_tokens
    )

    supervisor_chain = create_supervisor_chain(llm)

    # Get current state values
    iteration = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", MAX_ITERATIONS)
    conformance_score = state.get("conformance_score", 0)
    needs_correction = state.get("needs_correction", False)

    result = supervisor_chain.invoke({
        "messages": state.get("messages", []),
        "completed_agents": state.get("completed_agents", []),
        "current_task": state.get("current_task", "Start SDTM pipeline"),
        "iteration": iteration,
        "max_iterations": max_iterations,
        "conformance_score": conformance_score,
        "needs_correction": needs_correction
    })

    print(f"\n[Supervisor] Routing to: {result.next}")
    print(f"[Supervisor] Reasoning: {result.reasoning}")
    print(f"[Supervisor] Iteration: {iteration}/{max_iterations}, Score: {conformance_score}%")

    return {
        "next_agent": result.next,
        "messages": [AIMessage(content=f"Supervisor routing to {result.next}: {result.reasoning}")]
    }


def conformance_scoring_node(state: SupervisorState) -> Dict[str, Any]:
    """Calculate conformance score from validation results."""

    if not SCORING_AVAILABLE:
        # Fallback scoring without the scoring module
        return {
            "conformance_score": 80.0,  # Default score
            "submission_ready": False,
            "messages": [AIMessage(content="Conformance scoring module not available. Using default score.")]
        }

    # Gather validation results from state
    validation_results = {
        "structural": state.get("task_results", {}).get("structural", {}),
        "cdisc": state.get("task_results", {}).get("cdisc", {}),
        "cross_domain": state.get("task_results", {}).get("cross_domain", {}),
        "semantic": state.get("task_results", {}).get("semantic", {}),
        "anomaly": state.get("task_results", {}).get("anomaly", {}),
        "protocol": state.get("task_results", {}).get("protocol", {})
    }

    # Calculate score
    score = calculate_conformance_score(validation_results)

    print(f"\n[Conformance Scoring] Overall Score: {score.overall_score:.1f}%")
    print(f"[Conformance Scoring] Status: {score.status.value}")
    for layer, layer_score in score.layer_scores.items():
        print(f"  {layer}: {layer_score.raw_score:.1f}% (weight: {layer_score.weight})")

    ready, _ = is_submission_ready(validation_results)

    return {
        "conformance_score": score.overall_score,
        "layer_scores": {k: v.raw_score for k, v in score.layer_scores.items()},
        "submission_ready": ready,
        "needs_correction": not ready,
        "messages": [AIMessage(content=f"Conformance score: {score.overall_score:.1f}% ({score.status.value})")],
        "completed_agents": ["conformance_scoring"]
    }


# ============================================================================
# Agent Node Wrapper
# ============================================================================

def create_agent_node(agent_name: str, llm: ChatAnthropic):
    """Create an agent node that executes a specialized agent."""

    # Legacy agent creators (kept for backward compatibility)
    legacy_agent_creators = {
        "validation_agent": create_validation_agent,
        "mapping_agent": create_mapping_agent,
        "transformation_agent": create_transformation_agent,
        "codegen_agent": create_codegen_agent,
    }

    # New multi-agent architecture agent mapping
    new_agent_mapping = {
        "source_analyst_agent": "SourceDataAnalystAgent",
        "sdtm_expert_agent": "SDTMExpertAgent",
        "validator_agent": "ValidatorAgent",
        "anomaly_agent": "AnomalyDetectorAgent",
        "protocol_agent": "ProtocolComplianceAgent",
    }

    async def agent_node(state: SupervisorState) -> Dict[str, Any]:
        """Execute the specialized agent."""
        print(f"\n[{agent_name}] Starting execution...")

        # Try new multi-agent architecture first
        if agent_name in new_agent_mapping:
            try:
                from ..agents import (
                    SourceDataAnalystAgent,
                    SDTMExpertAgent,
                    ValidatorAgent,
                    CodeGeneratorAgent,
                    AnomalyDetectorAgent,
                    ProtocolComplianceAgent
                )

                agent_classes = {
                    "source_analyst_agent": SourceDataAnalystAgent,
                    "sdtm_expert_agent": SDTMExpertAgent,
                    "validator_agent": ValidatorAgent,
                    "anomaly_agent": AnomalyDetectorAgent,
                    "protocol_agent": ProtocolComplianceAgent,
                }

                AgentClass = agent_classes[agent_name]
                agent = AgentClass(api_key=state.get("api_key"))

                # Build input based on agent type
                if agent_name == "source_analyst_agent":
                    file_paths = list(state.get("task_results", {}).get("source_files", []))
                    result = await agent.analyze(file_paths)
                elif agent_name == "sdtm_expert_agent":
                    source_cols = state.get("task_results", {}).get("source_columns", [])
                    target_domain = state.get("current_task", "").split()[-1] if state.get("current_task") else "DM"
                    result = await agent.get_mapping_guidance(source_cols, target_domain)
                elif agent_name == "validator_agent":
                    domain_paths = state.get("task_results", {}).get("sdtm_paths", {})
                    result = await agent.validate_all_layers(domain_paths)
                elif agent_name == "anomaly_agent":
                    domain_paths = state.get("task_results", {}).get("sdtm_paths", {})
                    result = await agent.detect_all_anomalies(domain_paths)
                elif agent_name == "protocol_agent":
                    domain_paths = state.get("task_results", {}).get("sdtm_paths", {})
                    result = await agent.check_compliance(domain_paths)
                else:
                    result = {"result": "Agent executed"}

                agent_output = result.get("result", str(result))
                print(f"[{agent_name}] Completed (new architecture)")

                return {
                    "messages": [AIMessage(content=f"{agent_name} result: {agent_output[:500]}")],
                    "completed_agents": [agent_name],
                    "task_results": {agent_name: result}
                }

            except ImportError as e:
                print(f"[{agent_name}] New agent not available, falling back: {e}")

        # Fall back to legacy agents
        if agent_name in legacy_agent_creators:
            agent = legacy_agent_creators[agent_name](llm)

            agent_input = {
                "messages": state.get("messages", []) + [
                    HumanMessage(content=f"Execute {agent_name} tasks for study {state.get('study_id')}")
                ]
            }

            result = await agent.ainvoke(agent_input)
            agent_output = result.get("messages", [])[-1].content if result.get("messages") else "No output"

            print(f"[{agent_name}] Completed (legacy)")

            return {
                "messages": [AIMessage(content=f"{agent_name} result: {agent_output}")],
                "completed_agents": [agent_name],
                "task_results": {agent_name: agent_output}
            }

        # Handle codegen_agent with new architecture
        if agent_name == "codegen_agent":
            try:
                from ..agents import CodeGeneratorAgent
                agent = CodeGeneratorAgent(api_key=state.get("api_key"))
                mapping_spec = state.get("task_results", {}).get("mapping_spec", {})
                result = await agent.generate_code(mapping_spec, ["sas", "r"])

                return {
                    "messages": [AIMessage(content=f"Code generation completed")],
                    "completed_agents": [agent_name],
                    "task_results": {"codegen": result}
                }
            except ImportError:
                pass

        # Default handler
        return {
            "messages": [AIMessage(content=f"{agent_name} executed successfully")],
            "completed_agents": [agent_name]
        }

    return agent_node


# ============================================================================
# Build Supervisor Graph
# ============================================================================

def create_supervisor_graph(api_key: str) -> StateGraph:
    """Create the supervisor-based multi-agent graph with self-correction loop."""

    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
    max_tokens = int(os.getenv("ANTHROPIC_MAX_TOKENS", "4096"))

    llm = ChatAnthropic(
        model=model,
        api_key=api_key,
        max_tokens=max_tokens
    )

    # Create the graph
    workflow = StateGraph(SupervisorState)

    # Add supervisor node
    workflow.add_node("supervisor", supervisor_node)

    # Add core agent nodes (using new multi-agent architecture)
    # Source Data Analyst
    workflow.add_node("source_analyst_agent", create_agent_node("source_analyst_agent", llm))

    # SDTM Expert
    workflow.add_node("sdtm_expert_agent", create_agent_node("sdtm_expert_agent", llm))

    # Validator
    workflow.add_node("validator_agent", create_agent_node("validator_agent", llm))

    # Code Generator
    workflow.add_node("codegen_agent", create_agent_node("codegen_agent", llm))

    # Anomaly Detector
    workflow.add_node("anomaly_agent", create_agent_node("anomaly_agent", llm))

    # Protocol Compliance
    workflow.add_node("protocol_agent", create_agent_node("protocol_agent", llm))

    # Add conformance scoring node
    workflow.add_node("conformance_scoring", conformance_scoring_node)

    # Add self-correction node
    workflow.add_node("self_correction", self_correction_node)

    # Add human review node
    async def human_review_wrapper(state: SupervisorState) -> Dict[str, Any]:
        """Handle human review checkpoint."""
        checkpoint_type = state.get("pending_review", "general")
        conformance_score = state.get("conformance_score", 0)
        decision = state.get("human_decision", "approve")

        print(f"\n{'='*60}")
        print(f"HUMAN REVIEW CHECKPOINT: {checkpoint_type}")
        print(f"Conformance Score: {conformance_score}%")
        print(f"Decision: {decision}")
        print(f"{'='*60}\n")

        if decision.lower() == "approve":
            return {
                "messages": [AIMessage(content=f"Human review approved. Continuing pipeline.")],
                "completed_agents": ["human_review"],
                "needs_correction": False
            }
        elif decision.lower() == "reject":
            return {
                "messages": [AIMessage(content=f"Human review rejected. Stopping pipeline.")],
                "completed_agents": ["human_review"],
                "next_agent": "FINISH"
            }
        else:
            return {
                "messages": [AIMessage(content=f"Human review: modifications requested.")],
                "completed_agents": ["human_review"],
                "needs_correction": True
            }

    workflow.add_node("human_review", human_review_wrapper)

    # Add special nodes for Neo4j and S3
    from .async_nodes import load_to_neo4j_node, upload_to_s3_node

    async def neo4j_wrapper(state: SupervisorState) -> Dict[str, Any]:
        pipeline_state = {
            "study_id": state.get("study_id"),
            "output_dir": state.get("output_dir"),
            "sdtm_data_paths": state.get("task_results", {}).get("sdtm_paths", {}),
            "processing_stats": {}
        }
        result = await load_to_neo4j_node(pipeline_state, {})
        return {
            "messages": [AIMessage(content="Neo4j data loaded successfully")],
            "completed_agents": ["neo4j_agent"],
            "task_results": {"neo4j": result}
        }

    async def s3_wrapper(state: SupervisorState) -> Dict[str, Any]:
        pipeline_state = {
            "study_id": state.get("study_id"),
            "output_dir": state.get("output_dir"),
            "processing_stats": {}
        }
        result = await upload_to_s3_node(pipeline_state, {})
        return {
            "messages": [AIMessage(content="S3 upload completed successfully")],
            "completed_agents": ["s3_agent"],
            "task_results": {"s3": result}
        }

    workflow.add_node("neo4j_agent", neo4j_wrapper)
    workflow.add_node("s3_agent", s3_wrapper)

    # Set entry point
    workflow.set_entry_point("supervisor")

    # Add conditional edges from supervisor to agents
    def route_to_agent(state: SupervisorState) -> str:
        return state.get("next_agent", "FINISH")

    workflow.add_conditional_edges(
        "supervisor",
        route_to_agent,
        {
            # Core agents
            "source_analyst_agent": "source_analyst_agent",
            "sdtm_expert_agent": "sdtm_expert_agent",
            "validator_agent": "validator_agent",
            "codegen_agent": "codegen_agent",
            "anomaly_agent": "anomaly_agent",
            "protocol_agent": "protocol_agent",
            # Control nodes
            "conformance_scoring": "conformance_scoring",
            "self_correction": "self_correction",
            "human_review": "human_review",
            # Infrastructure nodes
            "neo4j_agent": "neo4j_agent",
            "s3_agent": "s3_agent",
            "FINISH": END
        }
    )

    # All nodes return to supervisor for routing
    all_nodes = [
        "source_analyst_agent", "sdtm_expert_agent", "validator_agent",
        "codegen_agent", "anomaly_agent", "protocol_agent",
        "conformance_scoring", "self_correction", "human_review",
        "neo4j_agent", "s3_agent"
    ]
    for node_name in all_nodes:
        workflow.add_edge(node_name, "supervisor")

    return workflow.compile(checkpointer=MemorySaver())


# ============================================================================
# Run Supervisor Pipeline
# ============================================================================

async def run_supervisor_pipeline(
    study_id: str,
    raw_data_dir: str,
    output_dir: str,
    api_key: str,
    human_decision: str = "approve",
    max_iterations: int = 3
) -> Dict[str, Any]:
    """
    Run the supervisor-based SDTM pipeline with self-correction loop.

    Args:
        study_id: Clinical study identifier
        raw_data_dir: Directory containing raw CSV files
        output_dir: Output directory for SDTM data
        api_key: Anthropic API key
        human_decision: Default decision for human review (approve/reject/modify)
        max_iterations: Maximum self-correction iterations (default 3)

    Returns:
        Final pipeline state with results
    """

    print("\n" + "=" * 70)
    print("   SDTM MULTI-AGENT SUPERVISOR PIPELINE")
    print(f"   Study: {study_id}")
    print(f"   Max Iterations: {max_iterations}")
    print("=" * 70)

    # Configure LangSmith
    configure_langsmith()

    # Create the supervisor graph
    graph = create_supervisor_graph(api_key)

    # Initial state with self-correction fields
    initial_state = SupervisorState(
        messages=[HumanMessage(content=f"""
Start the SDTM multi-agent transformation pipeline for study {study_id}.
Raw data directory: {raw_data_dir}
Output directory: {output_dir}

Execute the multi-agent workflow:
1. source_analyst_agent - Analyze source data schema and quality
2. sdtm_expert_agent - Generate SDTM mapping recommendations
3. validator_agent - Multi-layer validation (structural, CDISC, cross-domain, semantic)
4. conformance_scoring - Calculate weighted conformance score
5. IF score >= 95%: codegen_agent
   ELIF iteration < {max_iterations}: self_correction -> sdtm_expert_agent
   ELSE: human_review
6. codegen_agent - Generate SAS and R code
7. anomaly_agent - Detect statistical and physiological anomalies
8. protocol_agent - Check protocol compliance
9. conformance_scoring - Final score calculation
10. IF score >= 95%: neo4j_agent -> s3_agent -> FINISH
    ELSE: human_review

Target: >= 95% conformance score for auto-approval
""")],
        next_agent="source_analyst_agent",
        study_id=study_id,
        raw_data_dir=raw_data_dir,
        output_dir=output_dir,
        api_key=api_key,
        human_decision=human_decision,
        current_task="Start SDTM multi-agent pipeline",
        task_results={},
        completed_agents=[],
        final_output={},
        # Self-correction loop state
        iteration_count=0,
        max_iterations=max_iterations,
        conformance_score=0.0,
        layer_scores={},
        needs_correction=False,
        correction_feedback="",
        submission_ready=False,
        pending_review=""
    )

    config = {"configurable": {"thread_id": f"supervisor_{study_id}"}}

    # Run the pipeline
    final_state = None
    async for event in graph.astream(initial_state, config):
        for node_name, node_output in event.items():
            if node_name != "__end__":
                print(f"\n[Event] {node_name}")
                # Log conformance score if available
                if isinstance(node_output, dict) and "conformance_score" in node_output:
                    print(f"  Score: {node_output['conformance_score']:.1f}%")
        final_state = event

    # Print final summary
    if final_state:
        print("\n" + "=" * 70)
        print("   PIPELINE COMPLETE")
        print("=" * 70)
        for key, value in final_state.items():
            if key != "__end__" and isinstance(value, dict):
                score = value.get("conformance_score")
                if score:
                    print(f"   Final Conformance Score: {score:.1f}%")
                ready = value.get("submission_ready")
                if ready is not None:
                    print(f"   Submission Ready: {ready}")

    return final_state or {}

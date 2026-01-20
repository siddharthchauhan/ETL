"""
SDTM Supervisor Agent
=====================
Supervisor hierarchy pattern for multi-agent SDTM pipeline orchestration.
"""

import os
from typing import Dict, Any, List, Literal, Optional, Annotated, Sequence
from datetime import datetime
import functools
import operator

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
    next: Literal["validation_agent", "mapping_agent", "transformation_agent",
                  "codegen_agent", "neo4j_agent", "s3_agent", "FINISH"]
    reasoning: str


def create_supervisor_chain(llm: ChatAnthropic):
    """Create the supervisor chain that routes between agents."""

    members = ["validation_agent", "mapping_agent", "transformation_agent",
               "codegen_agent", "neo4j_agent", "s3_agent"]

    system_prompt = f"""You are the SDTM Pipeline Supervisor Agent.
You manage a team of specialized agents for clinical trial data transformation:

1. **validation_agent**: Validates raw data quality and SDTM compliance
2. **mapping_agent**: Creates SDTM mapping specifications
3. **transformation_agent**: Transforms data to SDTM format
4. **codegen_agent**: Generates SAS and R code
5. **neo4j_agent**: Loads data to Neo4j graph database
6. **s3_agent**: Uploads processed data to S3

Your job is to coordinate the SDTM transformation pipeline:

WORKFLOW ORDER:
1. First, call validation_agent to validate raw data
2. Then, call mapping_agent to generate SDTM mappings
3. Next, call transformation_agent to transform data
4. Then, call validation_agent again to validate SDTM output
5. Call codegen_agent to generate SAS and R code
6. Call neo4j_agent to load data to Neo4j
7. Call s3_agent to upload to S3
8. Finally, respond with FINISH when complete

Based on the conversation history and current task, decide which agent to call next.
If all tasks are complete, respond with FINISH."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        ("human", """Based on the conversation above, which agent should act next?
Current completed agents: {completed_agents}
Current task: {current_task}

Respond with the next agent to call, or FINISH if the pipeline is complete.""")
    ])

    return prompt | llm.with_structured_output(RouteResponse)


def supervisor_node(state: SupervisorState) -> Dict[str, Any]:
    """Supervisor node that routes to the next agent."""
    from langchain_anthropic import ChatAnthropic

    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        api_key=state.get("api_key", os.getenv("ANTHROPIC_API_KEY")),
        max_tokens=1000
    )

    supervisor_chain = create_supervisor_chain(llm)

    result = supervisor_chain.invoke({
        "messages": state.get("messages", []),
        "completed_agents": state.get("completed_agents", []),
        "current_task": state.get("current_task", "Start SDTM pipeline")
    })

    print(f"\n[Supervisor] Routing to: {result.next}")
    print(f"[Supervisor] Reasoning: {result.reasoning}")

    return {
        "next_agent": result.next,
        "messages": [AIMessage(content=f"Supervisor routing to {result.next}: {result.reasoning}")]
    }


# ============================================================================
# Agent Node Wrapper
# ============================================================================

def create_agent_node(agent_name: str, llm: ChatAnthropic):
    """Create an agent node that executes a specialized agent."""

    agent_creators = {
        "validation_agent": create_validation_agent,
        "mapping_agent": create_mapping_agent,
        "transformation_agent": create_transformation_agent,
        "codegen_agent": create_codegen_agent,
    }

    async def agent_node(state: SupervisorState) -> Dict[str, Any]:
        """Execute the specialized agent."""
        print(f"\n[{agent_name}] Starting execution...")

        if agent_name in agent_creators:
            agent = agent_creators[agent_name](llm)

            # Prepare agent input
            agent_input = {
                "messages": state.get("messages", []) + [
                    HumanMessage(content=f"Execute {agent_name} tasks for study {state.get('study_id')}")
                ]
            }

            # Run agent
            result = await agent.ainvoke(agent_input)

            # Extract result
            agent_output = result.get("messages", [])[-1].content if result.get("messages") else "No output"

            print(f"[{agent_name}] Completed")

            return {
                "messages": [AIMessage(content=f"{agent_name} result: {agent_output}")],
                "completed_agents": [agent_name],
                "task_results": {agent_name: agent_output}
            }

        else:
            # Handle special agents (neo4j, s3)
            return {
                "messages": [AIMessage(content=f"{agent_name} executed successfully")],
                "completed_agents": [agent_name]
            }

    return agent_node


# ============================================================================
# Build Supervisor Graph
# ============================================================================

def create_supervisor_graph(api_key: str) -> StateGraph:
    """Create the supervisor-based multi-agent graph."""

    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        api_key=api_key,
        max_tokens=4096
    )

    # Create the graph
    workflow = StateGraph(SupervisorState)

    # Add supervisor node
    workflow.add_node("supervisor", supervisor_node)

    # Add agent nodes
    for agent_name in ["validation_agent", "mapping_agent",
                       "transformation_agent", "codegen_agent"]:
        workflow.add_node(agent_name, create_agent_node(agent_name, llm))

    # Add special nodes for Neo4j and S3
    from .async_nodes import load_to_neo4j_node, upload_to_s3_node

    async def neo4j_wrapper(state: SupervisorState) -> Dict[str, Any]:
        # Convert supervisor state to pipeline state
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
            "validation_agent": "validation_agent",
            "mapping_agent": "mapping_agent",
            "transformation_agent": "transformation_agent",
            "codegen_agent": "codegen_agent",
            "neo4j_agent": "neo4j_agent",
            "s3_agent": "s3_agent",
            "FINISH": END
        }
    )

    # All agents return to supervisor
    for agent_name in ["validation_agent", "mapping_agent",
                       "transformation_agent", "codegen_agent",
                       "neo4j_agent", "s3_agent"]:
        workflow.add_edge(agent_name, "supervisor")

    return workflow.compile(checkpointer=MemorySaver())


# ============================================================================
# Run Supervisor Pipeline
# ============================================================================

async def run_supervisor_pipeline(
    study_id: str,
    raw_data_dir: str,
    output_dir: str,
    api_key: str,
    human_decision: str = "approve"
) -> Dict[str, Any]:
    """Run the supervisor-based SDTM pipeline."""

    print("\n" + "=" * 70)
    print("   SDTM SUPERVISOR AGENT PIPELINE")
    print(f"   Study: {study_id}")
    print("=" * 70)

    # Configure LangSmith
    configure_langsmith()

    # Create the supervisor graph
    graph = create_supervisor_graph(api_key)

    # Initial state
    initial_state = SupervisorState(
        messages=[HumanMessage(content=f"""
Start the SDTM transformation pipeline for study {study_id}.
Raw data directory: {raw_data_dir}
Output directory: {output_dir}

Execute the following workflow:
1. Validate raw data
2. Generate SDTM mappings
3. Transform to SDTM format
4. Validate SDTM data
5. Generate SAS and R code
6. Load to Neo4j
7. Upload to S3
""")],
        next_agent="validation_agent",
        study_id=study_id,
        raw_data_dir=raw_data_dir,
        output_dir=output_dir,
        api_key=api_key,
        human_decision=human_decision,
        current_task="Start SDTM pipeline",
        task_results={},
        completed_agents=[],
        final_output={}
    )

    config = {"configurable": {"thread_id": f"supervisor_{study_id}"}}

    # Run the pipeline
    final_state = None
    async for event in graph.astream(initial_state, config):
        for node_name, node_output in event.items():
            if node_name != "__end__":
                print(f"\n[Event] {node_name}")
        final_state = event

    return final_state or {}

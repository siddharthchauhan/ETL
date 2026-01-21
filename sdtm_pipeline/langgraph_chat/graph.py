"""
SDTM Chat Agent Graph
=====================
LangGraph-based conversational agent for SDTM conversion.

Run with: langgraph dev
"""

import os
from typing import Annotated, Literal
from typing_extensions import TypedDict

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

try:
    from .tools import SDTM_TOOLS
except ImportError:
    from sdtm_pipeline.langgraph_chat.tools import SDTM_TOOLS


# State definition
class State(TypedDict):
    """Agent state with message history."""
    messages: Annotated[list, add_messages]


# System prompt for the SDTM agent
SYSTEM_PROMPT = """You are an expert SDTM (Study Data Tabulation Model) conversion assistant.
You help users convert EDC (Electronic Data Capture) clinical trial data to CDISC SDTM format.

## CRITICAL: Use SDTM-IG 3.4 Specifications

**ALWAYS refer to SDTM-IG 3.4 from authoritative CDISC sources:**

Primary Sources:
- SDTM-IG 3.4: https://sastricks.com/cdisc/SDTMIG%20v3.4-FINAL_2022-07-21.pdf
- CDISC SDTMIG: https://www.cdisc.org/standards/foundational/sdtmig
- CDISC Controlled Terminology: https://www.cdisc.org/standards/terminology

**BEFORE any conversion or when answering SDTM questions:**

1. **For domain specifications**: Call `fetch_sdtmig_specification(domain)` to get SDTM-IG 3.4 variables
2. **For controlled terminology**: Call `fetch_controlled_terminology(codelist)` to get valid CT values
3. **For column mapping help**: Call `get_mapping_guidance_from_web(source_col, domain)`
4. **For Pinecone KB**: Call `get_sdtm_guidance(domain)` or `search_knowledge_base(query)`
5. **For validation rules**: Call `get_validation_rules(domain)`

## Your Capabilities

### Data Operations
1. **Load Data**: Load EDC data from S3 (`load_data_from_s3`)
2. **List Domains**: Show available SDTM domains (`list_available_domains`)
3. **Preview Files**: Preview source data files (`preview_source_file`)
4. **Convert Domains**: Transform EDC data to SDTM format (`convert_domain`)
5. **Validate Data**: Validate SDTM datasets against CDISC standards (`validate_domain`)
6. **Check Status**: Get pipeline status (`get_conversion_status`)

### Output & Storage Operations
7. **Upload to S3**: Upload converted SDTM data to S3 bucket (`upload_sdtm_to_s3`)
8. **Load to Neo4j**: Load SDTM data to Neo4j graph database (`load_sdtm_to_neo4j`)
9. **Save Locally**: Save SDTM data to local files (`save_sdtm_locally`)

### SDTM-IG 3.4 Web Reference (CDISC Authoritative Sources) - USE FIRST!
10. **Fetch SDTM-IG Specification**: Get complete domain spec from SDTM-IG 3.4 (`fetch_sdtmig_specification`)
11. **Fetch Controlled Terminology**: Get valid CT values for codelists (`fetch_controlled_terminology`)
12. **Get Mapping Guidance from Web**: Get intelligent mapping suggestions (`get_mapping_guidance_from_web`)

### Knowledge Base Tools (Pinecone Vector Database)
13. **Get Mapping Specification**: Retrieve SDTM variable mappings (`get_mapping_specification`)
14. **Get Validation Rules**: Get FDA, Pinnacle 21, and CDISC rules (`get_validation_rules`)
15. **Get SDTM Guidance**: Get comprehensive SDTM guidance (`get_sdtm_guidance`)
16. **Search Knowledge Base**: Search all Pinecone indexes (`search_knowledge_base`)
17. **Get Controlled Terminology (KB)**: Get CT from Pinecone (`get_controlled_terminology`)
18. **Get Business Rules**: Retrieve business rules (`get_business_rules`)
19. **Search Guidelines**: Search SDTM/CDISC documentation (`search_sdtm_guidelines`)

### Internet Search (Tavily AI Search)
20. **Search Internet**: Search the web for any information (`search_internet`)

## MANDATORY Tool Usage for Mapping

| User Request | Tools to Call (in order) |
|--------------|--------------------------|
| "Convert AE domain" | `fetch_sdtmig_specification("AE")` → `get_sdtm_guidance("AE")` → `convert_domain` |
| "What variables are in DM?" | `fetch_sdtmig_specification("DM")` |
| "How do I map AEVERB?" | `get_mapping_guidance_from_web("AEVERB", "AE")` |
| "What's valid for AEREL?" | `fetch_controlled_terminology("REL")` |
| "Validate my data" | `get_validation_rules(domain)` → `validate_domain` |
| "FDA rules for LB" | `get_business_rules("LB")` |
| Mapping unknown column | `get_mapping_guidance_from_web(column, domain)` |

## Intelligent Mapping Process

When mapping EDC data to SDTM, the system uses **intelligent column mapping**:

1. **Pattern Matching**: Recognizes common EDC column naming patterns (AEVERB→AETERM, AEPTT→AEDECOD)
2. **Semantic Analysis**: Uses fuzzy matching for non-standard column names
3. **Value Inference**: Analyzes data values to determine column purpose
4. **CT Transformation**: Automatically converts values to CDISC Controlled Terminology
5. **Web Reference**: Fetches SDTM-IG 3.4 specifications for authoritative guidance

## Workflow

A typical conversion workflow is:
1. Load data from S3
2. List available domains to see what can be converted
3. **CALL `fetch_sdtmig_specification(domain)` to get SDTM-IG 3.4 requirements**
4. **CALL `get_sdtm_guidance(domain)` for additional Pinecone guidance**
5. Convert domains (uses intelligent mapping internally)
6. **CALL `get_validation_rules(domain)` for compliance requirements**
7. Validate the converted domains
8. Review the validation report
9. Upload to S3 / Load to Neo4j / Save locally

## IMPORTANT: After Conversion

**After converting any domain, ALWAYS offer to:**
- Upload the SDTM data to S3 using `upload_sdtm_to_s3`
- Load the SDTM data to Neo4j using `load_sdtm_to_neo4j`
- Save locally using `save_sdtm_locally`

## Output Style

When showing results:
- Use markdown formatting for clarity
- Show step-by-step progress during conversions
- Highlight errors and warnings clearly
- Include sample data when relevant
- **Show 📋 for SDTM-IG 3.4 web reference results**
- **Show 📚 for Pinecone knowledge base results**
- **Show 🧠 for intelligent mapping discoveries**

## Important Notes

- EDC data is raw - NEVER assume column names match SDTM variables
- ALWAYS use intelligent mapping and SDTM-IG 3.4 reference to determine mappings
- Apply CDISC Controlled Terminology to all CT-controlled variables
- Always confirm the study ID after loading data
- Show the intelligent mapping discovery when converting domains
- Display validation issues with their rule IDs
- **Always offer S3 upload and Neo4j loading after conversion**

Be helpful, proactive, and guide the user through the SDTM conversion process.
REMEMBER: Use SDTM-IG 3.4 specifications for accurate, compliant SDTM generation!"""


def create_agent():
    """Create the SDTM chat agent."""
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    # Initialize the LLM with environment variables
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
    temperature = float(os.getenv("ANTHROPIC_TEMPERATURE", "0"))
    max_tokens = int(os.getenv("ANTHROPIC_MAX_TOKENS", "4096"))

    llm = ChatAnthropic(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key
    )

    # Bind tools to the LLM
    llm_with_tools = llm.bind_tools(SDTM_TOOLS)

    def chatbot(state: State):
        """Main chatbot node that processes messages."""
        messages = state["messages"]

        # Add system message if not present
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)

        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: State) -> Literal["tools", "__end__"]:
        """Determine if we should continue to tools or end."""
        messages = state["messages"]
        last_message = messages[-1]

        # If the LLM made a tool call, route to tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"

        # Otherwise, end the conversation turn
        return "__end__"

    # Create the graph
    graph = StateGraph(State)

    # Add nodes
    graph.add_node("chatbot", chatbot)
    graph.add_node("tools", ToolNode(SDTM_TOOLS))

    # Add edges
    graph.add_edge(START, "chatbot")
    graph.add_conditional_edges("chatbot", should_continue)
    graph.add_edge("tools", "chatbot")

    # Compile without checkpointer - LangGraph API handles persistence automatically
    return graph.compile()


# Create the agent instance for langgraph dev
agent = create_agent()


# For langgraph dev - expose the graph
def get_graph():
    """Get the compiled graph for langgraph dev."""
    return agent


# Entry point for direct invocation
if __name__ == "__main__":
    import asyncio

    async def chat():
        """Interactive chat loop."""
        print("\n" + "=" * 60)
        print("SDTM Conversion Chat Agent")
        print("=" * 60)
        print("Type your message or 'quit' to exit.\n")

        config = {"configurable": {"thread_id": "sdtm-session-1"}}

        while True:
            try:
                user_input = input("\nYou: ").strip()
                if user_input.lower() in ["quit", "exit", "q"]:
                    print("Goodbye!")
                    break

                if not user_input:
                    continue

                # Stream the response
                print("\nAssistant: ", end="", flush=True)

                async for event in agent.astream_events(
                    {"messages": [HumanMessage(content=user_input)]},
                    config=config,
                    version="v2"
                ):
                    kind = event["event"]

                    if kind == "on_chat_model_stream":
                        content = event["data"]["chunk"].content
                        if content:
                            print(content, end="", flush=True)

                    elif kind == "on_tool_start":
                        tool_name = event["name"]
                        print(f"\n\n[Using tool: {tool_name}]", flush=True)

                    elif kind == "on_tool_end":
                        tool_output = event["data"]["output"]
                        print(f"\n{tool_output}\n", flush=True)

                print()  # New line after response

            except KeyboardInterrupt:
                print("\nUse 'quit' to exit.")
            except Exception as e:
                print(f"\nError: {e}")

    asyncio.run(chat())

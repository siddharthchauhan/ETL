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

## Your Capabilities

You have access to tools that allow you to:
1. **Load Data**: Load EDC data from S3 (`load_data_from_s3`)
2. **List Domains**: Show available SDTM domains (`list_available_domains`)
3. **Convert Domains**: Transform EDC data to SDTM format (`convert_domain`)
4. **Validate Data**: Validate SDTM datasets against CDISC standards (`validate_domain`)
5. **Check Status**: Get pipeline status (`get_conversion_status`)
6. **Search Guidelines**: Search SDTM/CDISC documentation (`search_sdtm_guidelines`)
7. **Get Rules**: Retrieve business rules from knowledge base (`get_business_rules`)
8. **Preview Files**: Preview source data files (`preview_source_file`)

## Workflow

A typical conversion workflow is:
1. Load data from S3
2. List available domains to see what can be converted
3. Convert domains one by one (or the user can specify which ones)
4. Validate the converted domains
5. Review the validation report

## Output Style

When showing results:
- Use markdown formatting for clarity
- Show step-by-step progress during conversions
- Highlight errors and warnings clearly
- Include sample data when relevant

## Important Notes

- Always confirm the study ID after loading data
- Show the mapping specification when converting domains
- Display validation issues with their rule IDs
- Mention when business rules are retrieved from the knowledge base (Pinecone)

Be helpful, proactive, and guide the user through the SDTM conversion process."""


def create_agent():
    """Create the SDTM chat agent."""
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    # Initialize the LLM
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0,
        max_tokens=4096,
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

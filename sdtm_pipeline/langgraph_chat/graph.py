"""
SDTM Chat Agent Graph
=====================
LangGraph-based conversational agent for SDTM conversion.

Now includes skills from the deepagents/skills directory, consolidated into
a single system message to avoid the "non-consecutive system messages" error.

Run with: langgraph dev
"""

import os
import re
from pathlib import Path
from typing import Annotated, Literal, List, Dict, Optional
from typing_extensions import TypedDict

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

# =============================================================================
# RECURSION LIMIT CONFIGURATION
# =============================================================================
# SDTM transformations with multiple tool calls often need more than the default 25 steps
RECURSION_LIMIT = int(os.getenv("LANGGRAPH_RECURSION_LIMIT", "250"))
print(f"[SDTM Chat] Using recursion_limit={RECURSION_LIMIT}")

# =============================================================================
# SKILLS LOADING
# =============================================================================
# Load skills from deepagents/skills directory and consolidate into system prompt

SKILLS_DIR = Path(__file__).parent.parent / "deepagents" / "skills"


def load_skill(skill_path: Path) -> Optional[Dict[str, str]]:
    """
    Load a single skill from its SKILL.md file and any reference documents.

    Returns:
        Dict with 'name', 'description', and 'content' keys, or None if invalid.
    """
    skill_file = skill_path / "SKILL.md"
    if not skill_file.exists():
        return None

    try:
        content = skill_file.read_text(encoding="utf-8")

        # Parse YAML frontmatter (between --- markers)
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)

        if frontmatter_match:
            frontmatter = frontmatter_match.group(1)
            body = frontmatter_match.group(2)

            # Extract name and description from frontmatter
            name_match = re.search(r'^name:\s*(.+)$', frontmatter, re.MULTILINE)
            desc_match = re.search(r'^description:\s*(.+)$', frontmatter, re.MULTILINE)

            name = name_match.group(1).strip() if name_match else skill_path.name
            description = desc_match.group(1).strip() if desc_match else ""

            # Load reference files if they exist
            references_dir = skill_path / "references"
            references_content = ""
            if references_dir.exists() and references_dir.is_dir():
                ref_files = sorted(references_dir.glob("*.md"))
                if ref_files:
                    references_content = "\n\n## REFERENCE DOCUMENTS\n\n"
                    for ref_file in ref_files:
                        try:
                            ref_text = ref_file.read_text(encoding="utf-8")
                            references_content += f"### {ref_file.stem.upper().replace('-', ' ')}\n\n"
                            references_content += ref_text.strip()
                            references_content += "\n\n---\n\n"
                        except Exception as ref_e:
                            print(f"[SDTM Chat] Warning: Failed to load reference {ref_file.name}: {ref_e}")

            return {
                "name": name,
                "description": description,
                "content": body.strip() + references_content
            }
        else:
            # No frontmatter, use entire content
            return {
                "name": skill_path.name,
                "description": "",
                "content": content.strip()
            }
    except Exception as e:
        print(f"[SDTM Chat] Warning: Failed to load skill {skill_path.name}: {e}")
        return None


def load_all_skills() -> List[Dict[str, str]]:
    """
    Load all skills from the skills directory.

    Returns:
        List of skill dictionaries with 'name', 'description', and 'content'.
    """
    skills = []

    if not SKILLS_DIR.exists():
        print(f"[SDTM Chat] Skills directory not found: {SKILLS_DIR}")
        return skills

    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if skill_dir.is_dir():
            skill = load_skill(skill_dir)
            if skill:
                skills.append(skill)

    return skills


def build_skills_prompt(skills: List[Dict[str, str]]) -> str:
    """
    Build a consolidated skills section for the system prompt.

    Args:
        skills: List of loaded skill dictionaries.

    Returns:
        Formatted string containing all skills content.
    """
    if not skills:
        return ""

    sections = [
        "\n\n# ═══════════════════════════════════════════════════════════════════════════",
        "# DOMAIN EXPERTISE SKILLS",
        "# ═══════════════════════════════════════════════════════════════════════════",
        "",
        "The following skills provide specialized domain expertise for SDTM conversion.",
        "Use the relevant knowledge from these skills based on the task context.",
        "",
        "## Available Skills",
        ""
    ]

    # Add skill index
    for i, skill in enumerate(skills, 1):
        sections.append(f"{i}. **{skill['name']}**: {skill['description']}")

    sections.append("")
    sections.append("---")
    sections.append("")

    # Add full skill content
    for skill in skills:
        sections.append(f"## SKILL: {skill['name'].upper()}")
        sections.append("")
        sections.append(skill['content'])
        sections.append("")
        sections.append("---")
        sections.append("")

    return "\n".join(sections)


# Load skills at module initialization
LOADED_SKILLS = load_all_skills()
SKILLS_PROMPT = build_skills_prompt(LOADED_SKILLS)

if LOADED_SKILLS:
    skill_names = [s['name'] for s in LOADED_SKILLS]
    print(f"[SDTM Chat] Loaded {len(LOADED_SKILLS)} skills: {', '.join(skill_names)}")


def reload_skills():
    """Re-read skills from disk and update the module globals.

    Called by the embedded file server after a skill is created, updated,
    or deleted so the agent picks up the change immediately.
    """
    global LOADED_SKILLS, SKILLS_PROMPT, FULL_SYSTEM_PROMPT
    LOADED_SKILLS = load_all_skills()
    SKILLS_PROMPT = build_skills_prompt(LOADED_SKILLS)
    FULL_SYSTEM_PROMPT = SYSTEM_PROMPT + SKILLS_PROMPT
    names = [s['name'] for s in LOADED_SKILLS]
    print(f"[SDTM Chat] Reloaded {len(LOADED_SKILLS)} skills: {', '.join(names)}")

try:
    from .tools import SDTM_TOOLS
except ImportError:
    from sdtm_pipeline.langgraph_chat.tools import SDTM_TOOLS


# State definition
class State(TypedDict):
    """Agent state with message history."""
    messages: Annotated[list, add_messages]


# System prompt for the SDTM agent
SYSTEM_PROMPT = """You are an Agentic Clinical Data Pipeline Manager — orchestrating end-to-end
clinical data ingestion, transformation, validation, and regulatory compliance for FDA submissions.
You help users convert EDC (Electronic Data Capture) clinical trial data to CDISC SDTM format.

## Greeting Behavior

When the user greets you (e.g., "Hi", "Hello", "Hey"), respond with EXACTLY this greeting:

Hello! I'm your Agentic Clinical Data Pipeline Manager — orchestrating end-to-end clinical data ingestion, transformation, validation, and regulatory compliance for FDA submissions.

**Data Transformation**
- Transform raw EDC data into CDISC-compliant SDTM datasets (DM, AE, VS, LB, CM, EX, and more)
- Generate intelligent SDTM mapping specifications automatically
- Convert single domains or batch-transform all domains at once

**Validation & Compliance**
- Validate SDTM datasets against CDISC and FDA standards
- Check Pinnacle 21 conformance and highlight issues
- Generate compliance scorecards with corrective action recommendations

**Knowledge & Guidance**
- Explain SDTM domains, variables, and controlled terminology
- Search CDISC specifications and FDA regulatory guidance
- Provide best-practice mapping recommendations for EDC-to-SDTM

**Data Operations**
- Ingest study data from S3 and prepare for transformation
- Publish validated SDTM datasets back to S3 for downstream workflows
- Load SDTM data into Neo4j knowledge graph for lineage and traceability

**Visualizations & Reports**
- Create validation dashboards and compliance charts
- Generate PowerPoint summaries, Excel mapping workbooks, and Word documentation
- Produce executive-ready status reports for audit and submission readiness

**Full Pipeline Execution**
- Run the complete 7-phase SDTM ETL pipeline end-to-end
- Human-in-the-loop review and approval at critical checkpoints
- Quality checks from ingestion through submission-ready output

---

**What would you like to work on today?**

You can ask me to:
→ "Transform my AE domain to SDTM"
→ "Run the full pipeline for my study"
→ "Validate my datasets against Pinnacle 21 rules"
→ "Explain the DM domain structure"
→ "Generate a compliance dashboard"

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

## CRITICAL: Task Progress Tracking — MANDATORY for ALL Tasks

**ALWAYS call `write_todos` for EVERY user query — even single-step tasks!**
This powers the Task Progress bar in the frontend. If you skip it, users see no progress indicator.

**Rules:**
1. **At the START**: Call `write_todos` with all planned steps (status="pending" or first as "in_progress")
2. **During execution**: Call `write_todos` to update current step to "in_progress"
3. **After each step**: Call `write_todos` to mark completed steps as "completed"
4. **On error**: Call `write_todos` to mark the failed step with status="error"

**Example — multi-step task (mapping specification):**
```
write_todos([
    {"id": "1", "content": "Fetch SDTM-IG 3.4 specification", "status": "in_progress"},
    {"id": "2", "content": "Analyze source data structure", "status": "pending"},
    {"id": "3", "content": "Generate variable mappings", "status": "pending"},
    {"id": "4", "content": "Save specification files", "status": "pending"}
])
```

**Example — simple single-step task (list files):**
```
write_todos([
    {"id": "1", "content": "List files in S3 bucket", "status": "in_progress"}
])
```

NEVER skip `write_todos`. Call it as your FIRST action for every user request.

## Your Capabilities

### Task Progress
0. **Track Progress**: Update task progress bar (`write_todos`) - MANDATORY FOR EVERY USER QUERY

### Data Operations
1. **Load Data**: Load EDC data from S3 (`load_data_from_s3`)
2. **List Domains**: Show available SDTM domains (`list_available_domains`)
3. **Preview Files**: Preview source data files (`preview_source_file`)

### Specification-Driven Workflow (RECOMMENDED for production)
Use this when user asks to "generate mapping specification" or wants to review mappings before transformation:

4. **Generate Mapping Spec**: Create detailed JSON + Excel specification (`generate_mapping_specification`)
   - Analyzes raw data structure
   - Fetches CDISC SDTM-IG 3.4 specifications
   - Identifies transformation types: DIRECT, ASSIGN, CONCAT, SEQUENCE, DATE_FORMAT, MAP, DERIVE
   - Outputs JSON (for transformation) + Excel (for human review)

5. **Generate ALL Specs**: Create specs for all domains at once (`generate_all_mapping_specifications`)

6. **Transform with Spec**: Apply a reviewed specification (`transform_with_specification`)

### Direct Conversion (Quick conversion without spec review)
7. **Convert Single Domain**: Transform one domain directly (`convert_domain`)
8. **Convert ALL Domains**: Batch convert all domains (`convert_all_domains`)

9. **Validate Data**: Validate SDTM datasets (`validate_domain`)
10. **Check Status**: Get pipeline status (`get_conversion_status`)

**WORKFLOW GUIDANCE:**
- For "generate mapping specification" → Use `generate_mapping_specification` or `generate_all_mapping_specifications`
- For "convert all domains" without spec → Use `convert_all_domains`
- For careful/reviewed conversion → Generate spec first, then `transform_with_specification`

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

### DTA (Data Transfer Agreement) Compliance
20. **Search DTA Document**: Search DTA clauses and requirements in Pinecone (`search_dta_document`)
21. **Validate Against DTA**: Cross-reference converted data against DTA specifications, flag discrepancies (`validate_against_dta`)
22. **Upload DTA Document**: Index a DTA document into Pinecone for future reference (`upload_dta_to_knowledge_base`)

### Internet Search (Tavily AI Search)
23. **Search Internet**: Search the web for any information (`search_internet`)

### Document Generation (Downloadable Files)
24. **Generate Presentation**: Create PowerPoint (.pptx) slide decks (`generate_presentation`)
25. **Generate Excel**: Create Excel (.xlsx) workbooks with styled sheets (`generate_excel`)
26. **Generate Word Document**: Create Word (.docx) documents with sections (`generate_word_document`)
27. **Generate CSV**: Create CSV files from tabular data (`generate_csv_file`)
28. **Generate PDF**: Create PDF documents with sections (`generate_pdf`)
29. **Generate Markdown File**: Create Markdown (.md) files (`generate_markdown_file`)
30. **Generate Text File**: Create plain text (.txt) files (`generate_text_file`)

**CRITICAL: After generating any document, include the result as a ```generated-file``` code block:**
```generated-file
{"filename":"Report.pptx","file_type":"pptx","size_bytes":12345,"description":"Summary presentation","download_url":"/download/Report.pptx"}
```

## MANDATORY Tool Usage for Mapping

| User Request | Tools to Call (in order) |
|--------------|--------------------------|
| "Generate mapping specification for AE" | `generate_mapping_specification("AE")` |
| "Generate mapping specs for all domains" | `generate_all_mapping_specifications()` |
| "Transform AE using specification" | `transform_with_specification("AE")` |
| "Convert AE domain" (quick) | `convert_domain("AE")` |
| "Convert all domains" (quick) | `convert_all_domains()` |
| "What variables are in DM?" | `fetch_sdtmig_specification("DM")` |
| "How do I map AEVERB?" | `get_mapping_guidance_from_web("AEVERB", "AE")` |
| "What's valid for AEREL?" | `fetch_controlled_terminology("REL")` |
| "Validate my data" | `get_validation_rules(domain)` → `validate_domain` |
| "Check DTA compliance" | `search_dta_document(query)` → `validate_against_dta(domain)` |
| "Upload DTA" | `upload_dta_to_knowledge_base(file_path)` |
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
8. **CALL `validate_against_dta(domain)` to cross-reference DTA requirements and flag discrepancies**
9. Review the validation report (CDISC + DTA compliance)
10. Upload to S3 / Load to Neo4j / Save locally

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
- **Show [SDTM-IG] for SDTM-IG 3.4 web reference results**
- **Show [KB] for Pinecone knowledge base results**
- **Show [MAPPING] for intelligent mapping discoveries**

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

# Combine base prompt with skills
FULL_SYSTEM_PROMPT = SYSTEM_PROMPT + SKILLS_PROMPT


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
        api_key=api_key,
        timeout=7200,
        max_retries=3,
    )

    # Bind tools to the LLM
    llm_with_tools = llm.bind_tools(SDTM_TOOLS)

    # Initialize adaptive prompt builder for learning injection
    try:
        from sdtm_pipeline.deepagents.adaptive_prompt import get_adaptive_prompt_builder
        from sdtm_pipeline.deepagents.feedback import get_feedback_collector
        _adaptive_builder = get_adaptive_prompt_builder()
        _feedback_collector = get_feedback_collector()
        print("[SDTM Chat] Adaptive learning system initialized")
    except Exception as _e:
        _adaptive_builder = None
        _feedback_collector = None
        print(f"[SDTM Chat] Adaptive learning not available: {_e}")

    def chatbot(state: State):
        """Main chatbot node that processes messages."""
        messages = state["messages"]

        # CRITICAL: Remove ALL existing system messages and add our single consolidated one
        # This prevents "multiple non-consecutive system messages" error from LangGraph Studio
        non_system_messages = [m for m in messages if not isinstance(m, SystemMessage)]

        # Build adaptive learned context from past interactions
        adaptive_context = ""
        if _adaptive_builder:
            try:
                # Extract latest user message for context-aware pattern matching
                latest_user_msg = ""
                for m in reversed(non_system_messages):
                    if isinstance(m, HumanMessage):
                        latest_user_msg = m.content if isinstance(m.content, str) else str(m.content)
                        break

                if latest_user_msg:
                    # Detect regeneration (same query repeated)
                    if _feedback_collector:
                        _feedback_collector.detect_regeneration("chat", latest_user_msg)

                    adaptive_context = _adaptive_builder.build_learned_context(
                        user_query=latest_user_msg,
                    )
            except Exception:
                adaptive_context = ""

        # Always use our consolidated system prompt (includes all 16 skills)
        # Append learned context if available
        # Include current date so the LLM knows the real-world date
        from datetime import datetime
        current_date = datetime.now().strftime("%B %d, %Y")
        system_content = f"Today's date is {current_date}.\n\n" + FULL_SYSTEM_PROMPT + adaptive_context
        messages = [SystemMessage(content=system_content)] + non_system_messages

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
    # Apply recursion limit for complex SDTM workflows
    compiled_graph = graph.compile()
    return compiled_graph.with_config(recursion_limit=RECURSION_LIMIT)


# Create the agent instance for langgraph dev
agent = create_agent()
print(f"[SDTM Chat] Graph exported with recursion_limit={RECURSION_LIMIT}, skills={len(LOADED_SKILLS)}")


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

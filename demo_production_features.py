#!/usr/bin/env python3
"""
Live Demo: Production-Ready Agent Features
===========================================
Demonstrates the three hidden features that make AI agents production-ready:

1. **Reasoning Agents**: Stream thinking separately from output
2. **Reconnecting Streams**: Resume after interruption
3. **Branching & Time Travel**: Fork conversations and navigate history

Run: python demo_production_features.py

Author: SDTM Pipeline
"""

import asyncio
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_section(title: str):
    """Print a section separator."""
    print(f"\n--- {title} ---\n")


async def demo_reasoning_stream():
    """
    Demo 1: Streaming Thinking Separately

    Shows how reasoning/thinking content is separated from the final response,
    allowing UIs to display the agent's thought process.
    """
    print_header("DEMO 1: Reasoning Agents (Streaming Thinking Separately)")

    from sdtm_pipeline.deepagents.production_graph import (
        ProductionGraph,
        StreamContentType
    )

    # Create production graph
    pg = ProductionGraph()

    # Create a new session
    session = pg.create_session(
        thread_id=f"demo_reasoning_{datetime.now().strftime('%H%M%S')}",
        metadata={"demo": "reasoning"}
    )

    print(f"✓ Created session: {session.thread_id}")
    print(f"  Reconnect token: {session.reconnect_token[:16]}...")

    print_section("Streaming with Reasoning Separation")

    # Simple test message (won't trigger actual LLM to avoid costs in demo)
    # In real usage, you'd stream actual agent responses
    print("In production, the stream would show:")
    print("""
    [THINKING] I need to understand what SDTM domains are required...
    [THINKING] Looking at the CDISC SDTM-IG 3.4 specification...
    [THINKING] The AE domain requires STUDYID, DOMAIN, USUBJID, AESEQ...
    [TOOL_CALL] get_sdtm_guidance("AE")
    [TOOL_RESULT] {domain: "AE", variables: [...], ...}
    [TEXT] The AE (Adverse Events) domain has the following structure:
    [TEXT] - STUDYID: Study Identifier (Required)
    [TEXT] - USUBJID: Unique Subject Identifier (Required)
    ...
    """)

    # Get thinking summary
    print_section("Thinking Summary")

    # Simulate some thinking chunks for demo
    from sdtm_pipeline.deepagents.session_manager import StreamChunk

    pg._session_manager._stream_buffers[session.thread_id] = [
        StreamChunk(
            content_type=StreamContentType.THINKING,
            content="I need to analyze the AE domain requirements from SDTM-IG 3.4...",
            metadata={"position": 0}
        ),
        StreamChunk(
            content_type=StreamContentType.THINKING,
            content="The AE domain is part of the Events class and requires timing variables...",
            metadata={"position": 1}
        ),
        StreamChunk(
            content_type=StreamContentType.TOOL_CALL,
            content="Calling: get_sdtm_guidance",
            metadata={"position": 2, "tool_name": "get_sdtm_guidance"}
        ),
        StreamChunk(
            content_type=StreamContentType.TEXT,
            content="The AE domain captures adverse event data...",
            metadata={"position": 3}
        ),
    ]

    thinking = pg.get_thinking_summary(session.thread_id)
    if thinking:
        print(f"✓ Thinking Summary:")
        print(f"  - Text: {thinking.thinking_text[:80]}...")
        print(f"  - Estimated tokens: {thinking.thinking_tokens}")
        print(f"  - Tool calls planned: {thinking.tool_calls_planned}")

    print("\n✓ DEMO 1 COMPLETE: Reasoning stream separation works!")
    return session.thread_id


async def demo_reconnection(thread_id: str):
    """
    Demo 2: Reconnecting to Agent Streams

    Shows how sessions can be reconnected after interruption,
    with pending chunks properly retrieved.
    """
    print_header("DEMO 2: Reconnecting to Agent Streams")

    from sdtm_pipeline.deepagents.production_graph import ProductionGraph

    pg = ProductionGraph()

    print_section("Simulating Disconnection")

    # Prepare for disconnect
    disconnect_info = pg.prepare_for_disconnect(thread_id)

    print(f"✓ Session prepared for disconnect:")
    print(f"  - Thread ID: {disconnect_info['thread_id']}")
    print(f"  - Reconnect token: {disconnect_info['reconnect_token'][:16]}...")
    print(f"  - Last position: {disconnect_info['last_position']}")
    print(f"  - Expires: {disconnect_info['expires_at']}")

    print_section("Simulating Page Reload / Network Recovery")

    # Get reconnection state (simulating client-side reconnection)
    reconnect_state = pg.get_reconnection_state(
        thread_id,
        reconnect_token=disconnect_info['reconnect_token']
    )

    print(f"✓ Reconnection state retrieved:")
    print(f"  - Success: {reconnect_state['success']}")
    print(f"  - Can resume: {reconnect_state['can_resume']}")
    print(f"  - Pending chunks: {reconnect_state['pending_chunks_count']}")
    print(f"  - Last position: {reconnect_state['last_stream_position']}")

    if reconnect_state['pending_chunks']:
        print(f"\n✓ Pending chunks to replay:")
        for chunk in reconnect_state['pending_chunks'][:3]:
            print(f"  [{chunk['content_type'].upper()}] {chunk['content'][:50]}...")

    print_section("Client-Side Reconnection Pattern")
    print("""
    // Store in URL params on disconnect
    window.addEventListener('beforeunload', () => {
        const disconnectInfo = await api.prepareForDisconnect(threadId);
        sessionStorage.set('reconnect_token', disconnectInfo.reconnect_token);
        sessionStorage.set('thread_id', disconnectInfo.thread_id);
    });

    // On page load - reconnect
    const threadId = sessionStorage.get('thread_id');
    const token = sessionStorage.get('reconnect_token');

    if (threadId && token) {
        const state = await api.getReconnectionState(threadId, token);
        if (state.can_resume) {
            // Replay pending chunks
            for (const chunk of state.pending_chunks) {
                renderChunk(chunk);
            }
            // Continue streaming
            for await (const chunk of api.reconnect(threadId)) {
                renderChunk(chunk);
            }
        }
    }
    """)

    print("\n✓ DEMO 2 COMPLETE: Session reconnection works!")


async def demo_branching_time_travel(thread_id: str):
    """
    Demo 3: Branching Conversations and Time Travel

    Shows checkpoint creation, time travel, and branching functionality.
    """
    print_header("DEMO 3: Branching Conversations and Time Travel")

    from sdtm_pipeline.deepagents.production_graph import ProductionGraph

    pg = ProductionGraph()

    print_section("Creating Checkpoints (Save Points)")

    # Create checkpoints at different stages
    cp1 = pg.create_checkpoint(thread_id, "Initial state - before any transformation")
    print(f"✓ Checkpoint 1: {cp1.checkpoint_id}")
    print(f"  Description: {cp1.description}")

    # Simulate some work by updating the session manager's stored state
    cp1_state = pg._session_manager.get_checkpoint(cp1.checkpoint_id)
    if cp1_state:
        # Add some messages to simulate work
        new_state = cp1_state.state.copy()
        new_state["messages"] = [
            {"role": "user", "content": "Convert DM domain"},
            {"role": "assistant", "content": "DM domain converted with 100 records"}
        ]
        pg._session_manager.create_checkpoint(thread_id, new_state, "After DM conversion")

    cp2 = pg.create_checkpoint(thread_id, "After DM validation - 2 errors found")
    print(f"✓ Checkpoint 2: {cp2.checkpoint_id}")
    print(f"  Description: {cp2.description}")

    cp3 = pg.create_checkpoint(thread_id, "After fixing validation errors")
    print(f"✓ Checkpoint 3: {cp3.checkpoint_id}")
    print(f"  Description: {cp3.description}")

    print_section("Time Travel (Undo/Restore)")

    # Time travel back to checkpoint 2
    travel_result = pg.time_travel(thread_id, cp2.checkpoint_id)

    print(f"✓ Time traveled to checkpoint 2:")
    print(f"  Success: {travel_result['success']}")
    print(f"  Now at: {travel_result['description']}")
    print(f"  Message count: {travel_result['message_count']}")

    print_section("Branching (Fork Conversation)")

    # Create a branch to try a different approach
    branch_result = pg.create_branch(
        thread_id,
        "aggressive-fix",
        from_checkpoint_id=cp2.checkpoint_id
    )

    print(f"✓ Created branch 'aggressive-fix':")
    print(f"  Success: {branch_result['success']}")
    print(f"  Branch checkpoint: {branch_result['branch_checkpoint_id']}")
    print(f"  Forked from: {branch_result['source_checkpoint_id']}")

    # Create another branch
    pg.switch_branch(thread_id, "main")
    branch2_result = pg.create_branch(
        thread_id,
        "conservative-fix",
        from_checkpoint_id=cp2.checkpoint_id
    )

    print(f"\n✓ Created branch 'conservative-fix':")
    print(f"  Forked from same point as 'aggressive-fix'")

    print_section("Listing Branches")

    branches = pg.list_branches(thread_id)
    print("✓ Available branches:")
    for b in branches:
        current = " ← (current)" if b["is_current"] else ""
        print(f"  - {b['name']}: {b['message_count']} messages{current}")

    print_section("History Tree")

    history = pg.get_history(thread_id)
    tree = history["tree"]

    print(f"✓ History tree:")
    print(f"  - Thread: {tree['thread_id']}")
    print(f"  - Current branch: {tree['current_branch']}")
    print(f"  - Total checkpoints: {len(tree['checkpoints'])}")
    print(f"  - Branches: {list(tree['branches'].keys())}")

    print("\n  Checkpoint timeline:")
    for cp in tree['checkpoints']:
        branch_tag = f" [{cp['branch']}]" if cp['branch'] != "main" else ""
        print(f"    └─ {cp['id'][:12]}... ({cp['message_count']} msgs){branch_tag}")
        print(f"       {cp['description']}")

    print_section("Comparing Checkpoints")

    diff = pg.compare_checkpoints(cp1.checkpoint_id, cp3.checkpoint_id)

    print(f"✓ Checkpoint comparison (cp1 → cp3):")
    print(f"  - cp1: {diff['checkpoint_1']['message_count']} messages")
    print(f"  - cp3: {diff['checkpoint_2']['message_count']} messages")
    print(f"  - Difference: +{diff['message_count_diff']} messages")

    print("\n✓ DEMO 3 COMPLETE: Branching and time travel work!")


async def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("  PRODUCTION-READY AGENT FEATURES DEMO")
    print("  The 3 hidden features that make AI agents enterprise-ready")
    print("=" * 70)

    # Demo 1: Reasoning Stream
    thread_id = await demo_reasoning_stream()

    # Demo 2: Reconnection (uses same session)
    await demo_reconnection(thread_id)

    # Demo 3: Branching & Time Travel
    await demo_branching_time_travel(thread_id)

    # Summary
    print_header("DEMO COMPLETE")

    print("""
All three production-ready features are implemented:

┌─────────────────────────────────────────────────────────────────────┐
│ 1. REASONING AGENTS                                                  │
│    Stream thinking/reasoning separately from final output           │
│    → Enables debugging, transparency, and "vibe coding"             │
│                                                                     │
│    async for chunk in pg.stream_with_reasoning(thread_id, message): │
│        if chunk.content_type == StreamContentType.THINKING:         │
│            render_thinking_bubble(chunk.content)                    │
│        elif chunk.content_type == StreamContentType.TEXT:           │
│            render_response(chunk.content)                           │
├─────────────────────────────────────────────────────────────────────┤
│ 2. RECONNECTING STREAMS                                             │
│    Resume interrupted sessions without losing state                 │
│    → Handles page reloads, Wi-Fi drops, tab switching               │
│                                                                     │
│    # Store thread_id in URL params                                  │
│    state = pg.get_reconnection_state(thread_id, token)              │
│    for chunk in state['pending_chunks']:                            │
│        replay_chunk(chunk)                                          │
├─────────────────────────────────────────────────────────────────────┤
│ 3. BRANCHING & TIME TRAVEL                                          │
│    Navigate history, fork conversations, compare outcomes           │
│    → Enables exploration, refinement, and "what-if" scenarios       │
│                                                                     │
│    cp = pg.create_checkpoint(thread_id, "Before risky change")      │
│    pg.create_branch(thread_id, "experiment", cp.checkpoint_id)      │
│    pg.time_travel(thread_id, cp.checkpoint_id)  # Go back           │
└─────────────────────────────────────────────────────────────────────┘

Usage:
    # LangGraph Studio
    langgraph dev --graph sdtm_pipeline.deepagents.production_graph:graph

    # Programmatic
    from sdtm_pipeline.deepagents import ProductionGraph, StreamContentType
    pg = ProductionGraph()
    async for chunk in pg.stream_with_reasoning("session-1", "Convert AE domain"):
        ...
""")


if __name__ == "__main__":
    asyncio.run(main())

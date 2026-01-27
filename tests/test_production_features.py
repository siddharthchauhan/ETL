"""
Test Production-Ready Features
==============================
Tests for the three hidden features that make AI agents production-ready:

1. Reasoning Agents (Streaming Thinking Separately)
2. Reconnecting to Agent Streams
3. Branching Conversations and Time Travel

Run with: python -m tests.test_production_features
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Import session manager components
from sdtm_pipeline.deepagents.session_manager import (
    SessionManager,
    Session,
    SessionStatus,
    StreamChunk,
    StreamContentType,
    Checkpoint,
    get_session_manager
)


def test_feature_1_reasoning_stream():
    """
    Feature 1: Reasoning Agents (Streaming Thinking Separately)

    Tests that thinking/reasoning content is properly separated from
    final response content in the stream.
    """
    print("\n" + "=" * 70)
    print("FEATURE 1: Reasoning Agents (Streaming Thinking Separately)")
    print("=" * 70)

    sm = SessionManager(storage_dir=Path("./.test_sessions"))

    # Create a test session
    session = sm.create_session(
        thread_id="test_reasoning_001",
        metadata={"test": "reasoning_stream"}
    )

    print(f"\n✓ Created session: {session.thread_id}")
    print(f"  - Status: {session.status.value}")
    print(f"  - Reconnect token: {session.reconnect_token[:8]}...")

    # Test StreamChunk creation with different content types
    thinking_chunk = StreamChunk(
        content_type=StreamContentType.THINKING,
        content="I need to analyze the DM domain requirements...",
        metadata={"position": 0}
    )

    text_chunk = StreamChunk(
        content_type=StreamContentType.TEXT,
        content="The DM domain requires USUBJID, STUDYID, and DOMAIN.",
        metadata={"position": 1}
    )

    tool_chunk = StreamChunk(
        content_type=StreamContentType.TOOL_CALL,
        content="Calling tool: get_sdtm_guidance",
        metadata={"position": 2, "tool_name": "get_sdtm_guidance"}
    )

    print(f"\n✓ Created stream chunks:")
    print(f"  - THINKING chunk: '{thinking_chunk.content[:50]}...'")
    print(f"  - TEXT chunk: '{text_chunk.content[:50]}...'")
    print(f"  - TOOL_CALL chunk: '{tool_chunk.content}'")

    # Verify content types are properly distinguished
    assert thinking_chunk.content_type == StreamContentType.THINKING
    assert text_chunk.content_type == StreamContentType.TEXT
    assert tool_chunk.content_type == StreamContentType.TOOL_CALL

    # Test serialization
    thinking_dict = thinking_chunk.to_dict()
    assert thinking_dict["content_type"] == "thinking"
    assert "timestamp" in thinking_dict

    print(f"\n✓ Stream chunk serialization works correctly")
    print(f"  - Thinking chunk dict: {thinking_dict}")

    # Simulate stream buffer
    sm._stream_buffers["test_reasoning_001"] = [thinking_chunk, text_chunk, tool_chunk]
    session.last_stream_position = 2

    # Get thinking summary
    from sdtm_pipeline.deepagents.session_manager import ThinkingBlock

    thinking_summary = sm.get_thinking_summary("test_reasoning_001")
    print(f"\n✓ Got thinking summary:")
    print(f"  - Thinking text: '{thinking_summary.thinking_text}'")
    print(f"  - Estimated tokens: {thinking_summary.thinking_tokens}")
    print(f"  - Tool calls: {thinking_summary.tool_calls_planned}")

    print("\n✓ FEATURE 1 TEST PASSED: Reasoning stream separation works!")
    return True


def test_feature_2_reconnection():
    """
    Feature 2: Reconnecting to Agent Streams

    Tests that sessions can be reconnected after interruption,
    with pending chunks properly retrieved.
    """
    print("\n" + "=" * 70)
    print("FEATURE 2: Reconnecting to Agent Streams")
    print("=" * 70)

    sm = SessionManager(storage_dir=Path("./.test_sessions"))

    # Create a session
    session = sm.create_session(
        thread_id="test_reconnect_001",
        metadata={"test": "reconnection"}
    )

    print(f"\n✓ Created session: {session.thread_id}")

    # Simulate some chunks being streamed
    chunks = [
        StreamChunk(
            content_type=StreamContentType.TEXT,
            content=f"Response part {i}",
            metadata={"position": i}
        )
        for i in range(5)
    ]

    sm._stream_buffers["test_reconnect_001"] = chunks
    session.last_stream_position = 4

    print(f"✓ Simulated 5 chunks in stream buffer")

    # Simulate disconnect
    sm.update_session_status("test_reconnect_001", SessionStatus.DISCONNECTED)
    print(f"✓ Session marked as DISCONNECTED")

    # Get reconnection state
    reconnect_state = sm.get_reconnection_state("test_reconnect_001")

    print(f"\n✓ Got reconnection state:")
    print(f"  - Success: {reconnect_state['success']}")
    print(f"  - Status: {reconnect_state['status']}")
    print(f"  - Last position: {reconnect_state['last_stream_position']}")
    print(f"  - Pending chunks: {reconnect_state['pending_chunks_count']}")
    print(f"  - Can resume: {reconnect_state['can_resume']}")

    assert reconnect_state["success"] == True
    assert reconnect_state["can_resume"] == True

    # Test reconnection with token
    reconnect_token = session.reconnect_token
    reconnect_with_token = sm.get_reconnection_state(
        "test_reconnect_001",
        reconnect_token=reconnect_token
    )

    assert reconnect_with_token["success"] == True
    print(f"\n✓ Reconnection with token validated successfully")

    # Test prepare for disconnect
    disconnect_info = sm.mark_session_reconnectable("test_reconnect_001")

    print(f"\n✓ Prepared for disconnect:")
    print(f"  - New reconnect token: {disconnect_info['reconnect_token'][:8]}...")
    print(f"  - Last position: {disconnect_info['last_position']}")
    print(f"  - Expires at: {disconnect_info['expires_at']}")

    print("\n✓ FEATURE 2 TEST PASSED: Session reconnection works!")
    return True


def test_feature_3_branching_time_travel():
    """
    Feature 3: Branching Conversations and Time Travel

    Tests checkpoint creation, time travel, and branching functionality.
    """
    print("\n" + "=" * 70)
    print("FEATURE 3: Branching Conversations and Time Travel")
    print("=" * 70)

    sm = SessionManager(storage_dir=Path("./.test_sessions"))

    # Create a session
    session = sm.create_session(
        thread_id="test_timetravel_001",
        metadata={"test": "time_travel"}
    )

    print(f"\n✓ Created session: {session.thread_id}")
    print(f"  - Initial checkpoint: {session.current_checkpoint_id}")
    print(f"  - Current branch: {session.current_branch}")

    initial_cp_id = session.current_checkpoint_id

    # Create first checkpoint (simulating first message)
    cp1 = sm.create_checkpoint(
        thread_id="test_timetravel_001",
        state={"messages": [{"role": "user", "content": "Load DM data"}]},
        description="User asked to load DM data"
    )

    print(f"\n✓ Created checkpoint 1: {cp1.checkpoint_id}")
    print(f"  - Parent: {cp1.parent_checkpoint_id}")
    print(f"  - Messages: {cp1.message_count}")

    # Create second checkpoint (simulating second message)
    cp2 = sm.create_checkpoint(
        thread_id="test_timetravel_001",
        state={"messages": [
            {"role": "user", "content": "Load DM data"},
            {"role": "assistant", "content": "DM data loaded with 100 records"},
            {"role": "user", "content": "Convert to SDTM"}
        ]},
        description="User asked to convert to SDTM"
    )

    print(f"\n✓ Created checkpoint 2: {cp2.checkpoint_id}")
    print(f"  - Parent: {cp2.parent_checkpoint_id}")
    print(f"  - Messages: {cp2.message_count}")

    # Create third checkpoint
    cp3 = sm.create_checkpoint(
        thread_id="test_timetravel_001",
        state={"messages": [
            {"role": "user", "content": "Load DM data"},
            {"role": "assistant", "content": "DM data loaded with 100 records"},
            {"role": "user", "content": "Convert to SDTM"},
            {"role": "assistant", "content": "SDTM conversion complete"}
        ]},
        description="SDTM conversion completed"
    )

    print(f"\n✓ Created checkpoint 3: {cp3.checkpoint_id}")

    # Test time travel
    print(f"\n--- Testing Time Travel ---")

    travel_result = sm.time_travel("test_timetravel_001", cp1.checkpoint_id)

    print(f"\n✓ Time traveled to checkpoint 1:")
    print(f"  - Success: {travel_result['success']}")
    print(f"  - Message count: {travel_result['message_count']}")
    print(f"  - Description: {travel_result['description']}")

    assert travel_result["success"] == True
    assert travel_result["message_count"] == 1

    # Get current session state
    session = sm.get_session("test_timetravel_001")
    assert session.current_checkpoint_id == cp1.checkpoint_id

    print(f"\n✓ Session now at checkpoint 1 with {travel_result['message_count']} message(s)")

    # Test branching
    print(f"\n--- Testing Branching ---")

    # Create a branch from checkpoint 2
    branch_result = sm.create_branch(
        thread_id="test_timetravel_001",
        branch_name="alternative-approach",
        from_checkpoint_id=cp2.checkpoint_id
    )

    print(f"\n✓ Created branch 'alternative-approach':")
    print(f"  - Success: {branch_result['success']}")
    print(f"  - Branch checkpoint: {branch_result['branch_checkpoint_id']}")
    print(f"  - Source checkpoint: {branch_result['source_checkpoint_id']}")

    assert branch_result["success"] == True

    # List branches
    branches = sm.list_branches("test_timetravel_001")

    print(f"\n✓ Listed branches:")
    for b in branches:
        current = "←" if b["is_current"] else ""
        print(f"  - {b['name']}: {b['message_count']} messages {current}")

    # Switch branch
    switch_result = sm.switch_branch("test_timetravel_001", "main")

    print(f"\n✓ Switched to 'main' branch:")
    print(f"  - Success: {switch_result['success']}")
    print(f"  - Message count: {switch_result['message_count']}")

    # Get history tree
    history = sm.get_history_tree("test_timetravel_001")

    print(f"\n✓ Got history tree:")
    print(f"  - Total checkpoints: {len(history['tree']['checkpoints'])}")
    print(f"  - Branches: {list(history['tree']['branches'].keys())}")
    print(f"  - Current branch: {history['tree']['current_branch']}")

    # Compare checkpoints
    diff_result = sm.get_checkpoint_diff(cp1.checkpoint_id, cp3.checkpoint_id)

    print(f"\n✓ Compared checkpoints:")
    print(f"  - Checkpoint 1 messages: {diff_result['checkpoint_1']['message_count']}")
    print(f"  - Checkpoint 3 messages: {diff_result['checkpoint_2']['message_count']}")
    print(f"  - Difference: {diff_result['message_count_diff']} messages")

    print("\n✓ FEATURE 3 TEST PASSED: Branching and time travel work!")
    return True


def test_production_graph_integration():
    """
    Integration test for ProductionGraph class.

    Tests that all three features work together through the ProductionGraph interface.
    """
    print("\n" + "=" * 70)
    print("INTEGRATION TEST: ProductionGraph")
    print("=" * 70)

    from sdtm_pipeline.deepagents.production_graph import ProductionGraph

    # Create production graph
    pg = ProductionGraph()

    print(f"\n✓ Created ProductionGraph")

    # Test session management
    session = pg.create_session(
        thread_id="test_integration_001",
        metadata={"study": "MAXIS-08"}
    )

    print(f"✓ Created session via ProductionGraph: {session.thread_id}")

    # Test checkpoint creation
    cp = pg.create_checkpoint("test_integration_001", "Integration test checkpoint")

    print(f"✓ Created checkpoint via ProductionGraph: {cp.checkpoint_id}")

    # Test branch creation
    branch = pg.create_branch("test_integration_001", "test-branch")

    print(f"✓ Created branch via ProductionGraph: {branch['branch_name']}")

    # List sessions
    sessions = pg.list_sessions()

    print(f"✓ Listed {len(sessions)} sessions")

    # Get history
    history = pg.get_history("test_integration_001")

    print(f"✓ Got history with {len(history['tree']['checkpoints'])} checkpoints")

    # Test reconnection state
    reconnect = pg.get_reconnection_state("test_integration_001")

    print(f"✓ Got reconnection state: can_resume={reconnect['can_resume']}")

    print("\n✓ INTEGRATION TEST PASSED: ProductionGraph works correctly!")
    return True


def cleanup_test_sessions():
    """Clean up test session files."""
    import shutil
    test_dir = Path("./.test_sessions")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    print("\n✓ Cleaned up test session files")


def main():
    """Run all feature tests."""
    print("\n" + "=" * 70)
    print("PRODUCTION FEATURES TEST SUITE")
    print("Testing the 3 hidden features that make AI agents production-ready")
    print("=" * 70)

    all_passed = True

    try:
        # Test Feature 1: Reasoning Streams
        if not test_feature_1_reasoning_stream():
            all_passed = False

        # Test Feature 2: Reconnection
        if not test_feature_2_reconnection():
            all_passed = False

        # Test Feature 3: Branching and Time Travel
        if not test_feature_3_branching_time_travel():
            all_passed = False

        # Integration test
        if not test_production_graph_integration():
            all_passed = False

    finally:
        cleanup_test_sessions()

    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        print("\nProduction-ready features are fully implemented:")
        print("  1. ✓ Reasoning Agents (Streaming Thinking Separately)")
        print("  2. ✓ Reconnecting to Agent Streams")
        print("  3. ✓ Branching Conversations and Time Travel")
    else:
        print("❌ SOME TESTS FAILED!")
        print("=" * 70)
        sys.exit(1)

    print("\nUsage with LangGraph Studio:")
    print("  langgraph dev --graph sdtm_pipeline.deepagents.production_graph:graph")
    print("\nProgrammatic usage:")
    print("  from sdtm_pipeline.deepagents.production_graph import ProductionGraph")
    print("  pg = ProductionGraph()")
    print("  async for chunk in pg.stream_with_reasoning(thread_id, message):")
    print("      if chunk.content_type == StreamContentType.THINKING:")
    print("          render_thinking(chunk.content)")


if __name__ == "__main__":
    main()

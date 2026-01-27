"""
Production-Ready SDTM DeepAgent Graph
=====================================
Enhanced graph with three production-ready features:

1. **Reasoning Agents**: Stream thinking/reasoning separately from final output
2. **Reconnecting Streams**: Resume interrupted sessions seamlessly
3. **Branching & Time Travel**: Fork conversations and navigate history

This wraps the base SDTM graph with enterprise-grade session management.

Usage with LangGraph Studio:
    langgraph dev --graph sdtm_pipeline.deepagents.production_graph:graph

Usage programmatically:
    from sdtm_pipeline.deepagents.production_graph import (
        ProductionGraph,
        stream_with_reasoning,
        reconnect_session,
        create_branch,
        time_travel
    )

    # Create production graph
    pg = ProductionGraph()

    # Stream with reasoning separation
    async for chunk in pg.stream_with_reasoning(thread_id, message):
        if chunk.content_type == StreamContentType.THINKING:
            render_thinking(chunk.content)
        else:
            render_response(chunk.content)

    # Reconnect after disconnect
    async for chunk in pg.reconnect(thread_id):
        process_missed_chunk(chunk)

    # Branch the conversation
    branch_result = pg.create_branch(thread_id, "alternative-approach")

    # Time travel to previous state
    state = pg.time_travel(thread_id, checkpoint_id)
"""

import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, AsyncGenerator, Union
from dataclasses import dataclass

from dotenv import load_dotenv
load_dotenv()

from langgraph.graph.state import CompiledStateGraph

from .session_manager import (
    SessionManager,
    Session,
    SessionStatus,
    StreamChunk,
    StreamContentType,
    Checkpoint,
    ThinkingBlock,
    get_session_manager
)

# Import base graph creation
from .graph import create_graph, RECURSION_LIMIT


# =============================================================================
# PRODUCTION GRAPH WRAPPER
# =============================================================================

class ProductionGraph:
    """
    Production-ready wrapper around the SDTM DeepAgent graph.

    Provides three key features for enterprise deployment:

    1. **Reasoning Streams**: Separate thinking from output for debugging/transparency
    2. **Reconnection**: Resume interrupted sessions without losing context
    3. **Time Travel**: Navigate and branch conversation history

    Example:
        pg = ProductionGraph()

        # Start a new session
        session = pg.create_session("study-001-dm-conversion")

        # Stream with reasoning visible
        async for chunk in pg.stream_with_reasoning(session.thread_id, user_message):
            if chunk.content_type == StreamContentType.THINKING:
                print(f"[Thinking] {chunk.content}")
            elif chunk.content_type == StreamContentType.TEXT:
                print(chunk.content, end="")
            elif chunk.content_type == StreamContentType.TOOL_CALL:
                print(f"\\n[Tool] {chunk.metadata['tool_name']}")

        # Create a checkpoint before trying something risky
        checkpoint = pg.create_checkpoint(session.thread_id, "Before validation fix")

        # If it goes wrong, time travel back
        pg.time_travel(session.thread_id, checkpoint.checkpoint_id)

        # Or branch to try a different approach
        pg.create_branch(session.thread_id, "alternative-fix", checkpoint.checkpoint_id)
    """

    def __init__(self, graph: Optional[CompiledStateGraph] = None):
        """
        Initialize the production graph.

        Args:
            graph: Optional pre-compiled graph. If not provided, creates the standard SDTM graph.
        """
        self._graph = graph or create_graph()
        self._session_manager = get_session_manager()
        print(f"[ProductionGraph] Initialized with recursion_limit={RECURSION_LIMIT}")

    @property
    def graph(self) -> CompiledStateGraph:
        """Access the underlying LangGraph."""
        return self._graph

    @property
    def session_manager(self) -> SessionManager:
        """Access the session manager."""
        return self._session_manager

    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================

    def create_session(
        self,
        thread_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Session:
        """
        Create a new session for a conversation.

        Args:
            thread_id: Optional thread ID. Auto-generated if not provided.
            metadata: Optional metadata to attach to the session.

        Returns:
            Session object with thread_id and reconnect_token.
        """
        return self._session_manager.create_session(thread_id, metadata)

    def get_session(self, thread_id: str) -> Optional[Session]:
        """Get an existing session by thread ID."""
        return self._session_manager.get_session(thread_id)

    def list_sessions(
        self,
        status: Optional[SessionStatus] = None,
        limit: int = 50
    ) -> List[Session]:
        """List sessions, optionally filtered by status."""
        return self._session_manager.list_sessions(status, limit)

    # =========================================================================
    # FEATURE 1: REASONING/THINKING STREAM
    # =========================================================================

    async def stream_with_reasoning(
        self,
        thread_id: str,
        input_message: Union[str, Dict[str, Any]],
        create_checkpoint: bool = True
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream agent response with thinking/reasoning separated from output.

        This is the primary method for interacting with the agent in production.
        It yields StreamChunk objects that distinguish between:
        - THINKING: Internal reasoning (useful for debugging/transparency)
        - TEXT: Final response text
        - TOOL_CALL: Tool invocations
        - TOOL_RESULT: Tool outputs

        Args:
            thread_id: Session thread ID
            input_message: User message (string or dict with 'messages' key)
            create_checkpoint: Whether to create a checkpoint after the interaction

        Yields:
            StreamChunk objects with typed content

        Example:
            async for chunk in pg.stream_with_reasoning(thread_id, "Convert DM domain"):
                if chunk.content_type == StreamContentType.THINKING:
                    # Show in a collapsible "thinking" bubble
                    thinking_ui.append(chunk.content)
                elif chunk.content_type == StreamContentType.TEXT:
                    # Show in main response area
                    response_ui.append(chunk.content)
                elif chunk.content_type == StreamContentType.TOOL_CALL:
                    # Show tool indicator
                    tool_ui.show(chunk.metadata['tool_name'])
        """
        # Ensure session exists
        session = self._session_manager.get_session(thread_id)
        if not session:
            session = self._session_manager.create_session(thread_id)

        # Prepare input
        if isinstance(input_message, str):
            from langchain_core.messages import HumanMessage
            input_data = {"messages": [HumanMessage(content=input_message)]}
        else:
            input_data = input_message

        # Get current state for checkpoint
        current_state = None
        if create_checkpoint and session.current_checkpoint_id:
            cp = self._session_manager.get_checkpoint(session.current_checkpoint_id)
            if cp:
                current_state = cp.state.copy()

        # Stream with reasoning separation
        collected_content = []
        async for chunk in self._session_manager.stream_with_reasoning(
            self._graph,
            thread_id,
            input_data
        ):
            collected_content.append(chunk)
            yield chunk

        # Create checkpoint after successful interaction
        if create_checkpoint:
            new_state = current_state or {"messages": []}
            # Add new messages to state
            new_messages = []
            text_content = ""
            for chunk in collected_content:
                if chunk.content_type == StreamContentType.TEXT:
                    text_content += chunk.content
            if text_content:
                from langchain_core.messages import AIMessage
                new_messages.append({"role": "assistant", "content": text_content})

            new_state["messages"] = new_state.get("messages", []) + new_messages

            self._session_manager.create_checkpoint(
                thread_id=thread_id,
                state=new_state,
                description=f"After interaction at {datetime.utcnow().isoformat()}"
            )

    def get_thinking_summary(self, thread_id: str) -> Optional[ThinkingBlock]:
        """
        Get a summary of the thinking/reasoning from the last interaction.

        Returns:
            ThinkingBlock with aggregated thinking text, token estimate, and duration
        """
        return self._session_manager.get_thinking_summary(thread_id)

    # =========================================================================
    # FEATURE 2: RECONNECTION
    # =========================================================================

    def get_reconnection_state(
        self,
        thread_id: str,
        reconnect_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get the state needed to reconnect to a session.

        This is useful when:
        - Page is reloaded
        - Network connection is restored
        - Tab is reopened

        Args:
            thread_id: Session thread ID
            reconnect_token: Optional token for authentication

        Returns:
            Dict with reconnection info including:
            - pending_chunks: Missed content since disconnect
            - last_stream_position: Position to resume from
            - reconnect_config: LangGraph config to resume

        Example (client-side):
            # Store in URL params on disconnect
            url_params.set('thread_id', thread_id)
            url_params.set('reconnect_token', reconnect_token)

            # On page load
            thread_id = url_params.get('thread_id')
            if thread_id:
                state = api.get_reconnection_state(thread_id)
                for chunk in state['pending_chunks']:
                    render_chunk(chunk)
        """
        return self._session_manager.get_reconnection_state(thread_id, reconnect_token)

    async def reconnect(
        self,
        thread_id: str,
        from_position: int = 0
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Reconnect to a session and receive any missed chunks.

        This allows clients to resume where they left off after:
        - Page reload
        - Network interruption
        - Tab switching

        Args:
            thread_id: Session thread ID
            from_position: Stream position to resume from

        Yields:
            StreamChunk objects that were missed during disconnect

        Example:
            # On reconnection
            last_position = localStorage.get('last_position', 0)
            async for chunk in pg.reconnect(thread_id, last_position):
                render_missed_chunk(chunk)
                localStorage.set('last_position', chunk.metadata['position'])
        """
        async for chunk in self._session_manager.reconnect_stream(
            self._graph,
            thread_id,
            from_position
        ):
            yield chunk

    def prepare_for_disconnect(self, thread_id: str) -> Dict[str, Any]:
        """
        Prepare a session for potential disconnect.

        Call this before the client might disconnect (e.g., on beforeunload).

        Returns:
            Dict with reconnection info to store client-side
        """
        return self._session_manager.mark_session_reconnectable(thread_id)

    # =========================================================================
    # FEATURE 3: BRANCHING AND TIME TRAVEL
    # =========================================================================

    def create_checkpoint(
        self,
        thread_id: str,
        description: str = ""
    ) -> Checkpoint:
        """
        Create a checkpoint of the current conversation state.

        Checkpoints allow you to:
        - Save important states
        - Branch from specific points
        - Navigate back if something goes wrong

        Args:
            thread_id: Session thread ID
            description: Human-readable description of this checkpoint

        Returns:
            Checkpoint object with ID and metadata

        Example:
            # Before making a risky change
            cp = pg.create_checkpoint(thread_id, "Before validation experiment")

            # Try something
            await pg.stream_with_reasoning(thread_id, "Fix all validation errors")

            # If it failed, go back
            if not satisfied:
                pg.time_travel(thread_id, cp.checkpoint_id)
        """
        session = self._session_manager.get_session(thread_id)
        current_state = {}

        if session and session.current_checkpoint_id:
            cp = self._session_manager.get_checkpoint(session.current_checkpoint_id)
            if cp:
                current_state = cp.state.copy()

        return self._session_manager.create_checkpoint(
            thread_id=thread_id,
            state=current_state,
            description=description
        )

    def time_travel(
        self,
        thread_id: str,
        checkpoint_id: str
    ) -> Dict[str, Any]:
        """
        Navigate to a previous checkpoint (time travel).

        This restores the conversation to the state at that checkpoint.

        Args:
            thread_id: Session thread ID
            checkpoint_id: ID of checkpoint to travel to

        Returns:
            Dict with success status and state at that checkpoint

        Example:
            # Get history
            history = pg.get_history(thread_id)

            # Find a good checkpoint
            target = history['checkpoints'][3]  # Go back 3 steps

            # Time travel
            result = pg.time_travel(thread_id, target['id'])
            if result['success']:
                print(f"Restored to {result['message_count']} messages")
        """
        return self._session_manager.time_travel(thread_id, checkpoint_id)

    def create_branch(
        self,
        thread_id: str,
        branch_name: str,
        from_checkpoint_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new branch from a checkpoint.

        Branching allows exploring alternative paths without losing
        the original conversation.

        Args:
            thread_id: Session thread ID
            branch_name: Name for the new branch
            from_checkpoint_id: Checkpoint to branch from (default: current)

        Returns:
            Dict with success status and branch info

        Example:
            # Create a branch to try a different approach
            result = pg.create_branch(thread_id, "aggressive-fix")

            # Work on the branch
            await pg.stream_with_reasoning(thread_id, "Use aggressive validation fixing")

            # Switch back to main if needed
            pg.switch_branch(thread_id, "main")
        """
        return self._session_manager.create_branch(thread_id, branch_name, from_checkpoint_id)

    def switch_branch(
        self,
        thread_id: str,
        branch_name: str
    ) -> Dict[str, Any]:
        """
        Switch to a different branch.

        Args:
            thread_id: Session thread ID
            branch_name: Name of branch to switch to

        Returns:
            Dict with success status and branch state
        """
        return self._session_manager.switch_branch(thread_id, branch_name)

    def list_branches(self, thread_id: str) -> List[Dict[str, Any]]:
        """
        List all branches for a session.

        Returns:
            List of branch info dicts with name, checkpoint_id, is_current
        """
        return self._session_manager.list_branches(thread_id)

    def get_history(self, thread_id: str) -> Dict[str, Any]:
        """
        Get the full conversation history tree.

        Returns:
            Dict with checkpoints, branches, and current position
        """
        return self._session_manager.get_history_tree(thread_id)

    def compare_checkpoints(
        self,
        checkpoint_id_1: str,
        checkpoint_id_2: str
    ) -> Dict[str, Any]:
        """
        Compare two checkpoints to see what changed.

        Args:
            checkpoint_id_1: First checkpoint ID
            checkpoint_id_2: Second checkpoint ID

        Returns:
            Dict with diff information
        """
        return self._session_manager.get_checkpoint_diff(checkpoint_id_1, checkpoint_id_2)

    # =========================================================================
    # DIRECT INVOCATION
    # =========================================================================

    async def invoke(
        self,
        input_message: Union[str, Dict[str, Any]],
        thread_id: Optional[str] = None,
        config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Invoke the graph directly (non-streaming).

        For production use, prefer stream_with_reasoning for better UX.

        Args:
            input_message: User message
            thread_id: Optional thread ID
            config: Optional LangGraph config

        Returns:
            Graph output state
        """
        if isinstance(input_message, str):
            from langchain_core.messages import HumanMessage
            input_data = {"messages": [HumanMessage(content=input_message)]}
        else:
            input_data = input_message

        invoke_config = config or {}
        if thread_id:
            invoke_config["configurable"] = invoke_config.get("configurable", {})
            invoke_config["configurable"]["thread_id"] = thread_id

        return await self._graph.ainvoke(input_data, config=invoke_config)


# =============================================================================
# CONVENIENCE FUNCTIONS FOR DIRECT IMPORT
# =============================================================================

# Create default production graph instance
_production_graph: Optional[ProductionGraph] = None


def get_production_graph() -> ProductionGraph:
    """Get the global production graph instance."""
    global _production_graph
    if _production_graph is None:
        _production_graph = ProductionGraph()
    return _production_graph


async def stream_with_reasoning(
    thread_id: str,
    message: Union[str, Dict],
    create_checkpoint: bool = True
) -> AsyncGenerator[StreamChunk, None]:
    """Stream with reasoning separation."""
    pg = get_production_graph()
    async for chunk in pg.stream_with_reasoning(thread_id, message, create_checkpoint):
        yield chunk


async def reconnect_session(
    thread_id: str,
    from_position: int = 0
) -> AsyncGenerator[StreamChunk, None]:
    """Reconnect to a session."""
    pg = get_production_graph()
    async for chunk in pg.reconnect(thread_id, from_position):
        yield chunk


def create_session_checkpoint(thread_id: str, description: str = "") -> Checkpoint:
    """Create a checkpoint."""
    return get_production_graph().create_checkpoint(thread_id, description)


def session_time_travel(thread_id: str, checkpoint_id: str) -> Dict[str, Any]:
    """Time travel to a checkpoint."""
    return get_production_graph().time_travel(thread_id, checkpoint_id)


def create_session_branch(
    thread_id: str,
    branch_name: str,
    from_checkpoint_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a branch."""
    return get_production_graph().create_branch(thread_id, branch_name, from_checkpoint_id)


# =============================================================================
# GRAPH EXPORT FOR LANGGRAPH DEV
# =============================================================================

def create_production_graph() -> CompiledStateGraph:
    """Create the production graph for LangGraph dev."""
    pg = ProductionGraph()
    return pg.graph


# Export the graph for langgraph dev
graph = create_production_graph()
print(f"[ProductionGraph] Graph exported for LangGraph dev with recursion_limit={RECURSION_LIMIT}")

"""
Session Manager for SDTM DeepAgents
===================================
Production-ready session management with:
1. Reasoning/Thinking stream separation
2. Reconnection to agent streams
3. Branching conversations and time travel

This module provides enterprise-grade session handling for AI agents.
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, AsyncGenerator, Literal
from dataclasses import dataclass, field, asdict
from enum import Enum
import pickle
import hashlib
from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# RECURSION LIMIT CONFIGURATION
# =============================================================================
# SDTM transformations with subagents, skills, and multiple tool calls often need more steps
RECURSION_LIMIT = int(os.getenv("LANGGRAPH_RECURSION_LIMIT", "250"))


# =============================================================================
# SESSION STORAGE CONFIGURATION
# =============================================================================

SESSION_STORAGE_DIR = Path(os.getenv("SESSION_STORAGE_DIR", "./.sessions"))
CHECKPOINT_DIR = SESSION_STORAGE_DIR / "checkpoints"
SESSION_METADATA_FILE = SESSION_STORAGE_DIR / "sessions.json"

# Ensure directories exist
SESSION_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# DATA CLASSES
# =============================================================================

class SessionStatus(str, Enum):
    """Session lifecycle states."""
    ACTIVE = "active"
    PAUSED = "paused"
    DISCONNECTED = "disconnected"
    COMPLETED = "completed"
    BRANCHED = "branched"


class StreamContentType(str, Enum):
    """Types of content in streamed responses."""
    THINKING = "thinking"          # Internal reasoning (extended thinking)
    TEXT = "text"                  # Final response text
    TOOL_CALL = "tool_call"        # Tool invocation
    TOOL_RESULT = "tool_result"    # Tool response
    ERROR = "error"                # Error message


@dataclass
class StreamChunk:
    """A chunk of streamed content with type information."""
    content_type: StreamContentType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content_type": self.content_type.value,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


@dataclass
class Checkpoint:
    """A snapshot of conversation state at a point in time."""
    checkpoint_id: str
    parent_checkpoint_id: Optional[str]
    thread_id: str
    timestamp: str
    state: Dict[str, Any]
    message_count: int
    description: str = ""
    branch_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        return cls(**data)


@dataclass
class Session:
    """
    A session represents a continuous agent interaction with:
    - Thread ID for message continuity
    - Checkpoints for time travel
    - Branch history for forking
    """
    thread_id: str
    created_at: str
    updated_at: str
    status: SessionStatus
    checkpoints: List[str] = field(default_factory=list)  # List of checkpoint IDs
    branches: Dict[str, str] = field(default_factory=dict)  # branch_name -> checkpoint_id
    current_branch: str = "main"
    current_checkpoint_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Reconnection state
    last_stream_position: int = 0
    pending_chunks: List[Dict] = field(default_factory=list)
    reconnect_token: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status.value,
            "checkpoints": self.checkpoints,
            "branches": self.branches,
            "current_branch": self.current_branch,
            "current_checkpoint_id": self.current_checkpoint_id,
            "metadata": self.metadata,
            "last_stream_position": self.last_stream_position,
            "pending_chunks": self.pending_chunks,
            "reconnect_token": self.reconnect_token
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        data["status"] = SessionStatus(data["status"])
        return cls(**data)


@dataclass
class ThinkingBlock:
    """Structured thinking/reasoning content from the agent."""
    thinking_text: str
    thinking_tokens: int
    duration_ms: int
    tool_calls_planned: List[str] = field(default_factory=list)
    confidence_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# SESSION MANAGER
# =============================================================================

class SessionManager:
    """
    Manages agent sessions with production-ready features:

    1. **Reasoning Streams**: Separates thinking from final output
    2. **Reconnection**: Allows resuming interrupted sessions
    3. **Time Travel**: Supports branching and checkpoint navigation
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or SESSION_STORAGE_DIR
        self.checkpoint_dir = self.storage_dir / "checkpoints"
        self.sessions_file = self.storage_dir / "sessions.json"

        # Ensure directories exist
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache
        self._sessions: Dict[str, Session] = {}
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._stream_buffers: Dict[str, List[StreamChunk]] = {}

        # Load existing sessions
        self._load_sessions()

    # =========================================================================
    # SESSION LIFECYCLE
    # =========================================================================

    def create_session(
        self,
        thread_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Session:
        """Create a new session with optional thread ID."""
        now = datetime.utcnow().isoformat()

        if thread_id is None:
            thread_id = f"session_{hashlib.md5(now.encode()).hexdigest()[:12]}"

        # Generate reconnect token
        reconnect_token = hashlib.sha256(f"{thread_id}:{now}".encode()).hexdigest()[:32]

        session = Session(
            thread_id=thread_id,
            created_at=now,
            updated_at=now,
            status=SessionStatus.ACTIVE,
            metadata=metadata or {},
            reconnect_token=reconnect_token
        )

        # Create initial checkpoint
        initial_checkpoint = self.create_checkpoint(
            thread_id=thread_id,
            state={"messages": []},
            description="Session start"
        )
        session.checkpoints.append(initial_checkpoint.checkpoint_id)
        session.current_checkpoint_id = initial_checkpoint.checkpoint_id
        session.branches["main"] = initial_checkpoint.checkpoint_id

        self._sessions[thread_id] = session
        self._save_sessions()

        print(f"[SessionManager] Created session: {thread_id}")
        return session

    def get_session(self, thread_id: str) -> Optional[Session]:
        """Retrieve a session by thread ID."""
        return self._sessions.get(thread_id)

    def list_sessions(
        self,
        status: Optional[SessionStatus] = None,
        limit: int = 50
    ) -> List[Session]:
        """List sessions with optional status filter."""
        sessions = list(self._sessions.values())

        if status:
            sessions = [s for s in sessions if s.status == status]

        # Sort by updated_at descending
        sessions.sort(key=lambda s: s.updated_at, reverse=True)

        return sessions[:limit]

    def update_session_status(
        self,
        thread_id: str,
        status: SessionStatus
    ) -> Optional[Session]:
        """Update session status."""
        session = self._sessions.get(thread_id)
        if session:
            session.status = status
            session.updated_at = datetime.utcnow().isoformat()
            self._save_sessions()
        return session

    # =========================================================================
    # FEATURE 1: REASONING/THINKING STREAM SEPARATION
    # =========================================================================

    async def stream_with_reasoning(
        self,
        graph,
        thread_id: str,
        input_message: Dict[str, Any],
        config: Optional[Dict] = None
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream agent response with thinking/reasoning separated from final output.

        This generator yields StreamChunk objects with content_type indicating
        whether the content is THINKING (internal reasoning) or TEXT (final response).

        Usage:
            async for chunk in session_manager.stream_with_reasoning(graph, thread_id, input):
                if chunk.content_type == StreamContentType.THINKING:
                    render_thinking_bubble(chunk.content)
                elif chunk.content_type == StreamContentType.TEXT:
                    render_response(chunk.content)
        """
        session = self._sessions.get(thread_id)
        if not session:
            session = self.create_session(thread_id)

        # Update session status
        session.status = SessionStatus.ACTIVE
        session.updated_at = datetime.utcnow().isoformat()

        # Initialize stream buffer for reconnection
        if thread_id not in self._stream_buffers:
            self._stream_buffers[thread_id] = []

        stream_config = config or {}
        stream_config["configurable"] = stream_config.get("configurable", {})
        stream_config["configurable"]["thread_id"] = thread_id
        # Apply recursion limit for complex SDTM workflows
        stream_config["recursion_limit"] = stream_config.get("recursion_limit", RECURSION_LIMIT)

        position = 0
        current_thinking = []
        thinking_complete = False

        try:
            async for event in graph.astream_events(
                input_message,
                config=stream_config,
                version="v2"
            ):
                kind = event.get("event", "")

                # Handle extended thinking blocks (Claude's internal reasoning)
                if kind == "on_chat_model_stream":
                    chunk_data = event.get("data", {}).get("chunk", {})

                    # Check for thinking/reasoning content blocks
                    content = getattr(chunk_data, "content", None)

                    if content:
                        # Handle different content block types
                        if isinstance(content, list):
                            for block in content:
                                block_type = getattr(block, "type", None) or block.get("type") if isinstance(block, dict) else None

                                if block_type == "thinking":
                                    # Extended thinking block
                                    thinking_text = getattr(block, "thinking", "") or block.get("thinking", "")
                                    if thinking_text:
                                        chunk = StreamChunk(
                                            content_type=StreamContentType.THINKING,
                                            content=thinking_text,
                                            metadata={"position": position, "block_type": "thinking"}
                                        )
                                        self._stream_buffers[thread_id].append(chunk)
                                        session.last_stream_position = position
                                        position += 1
                                        yield chunk

                                elif block_type == "text":
                                    # Regular text content
                                    text = getattr(block, "text", "") or block.get("text", "")
                                    if text:
                                        chunk = StreamChunk(
                                            content_type=StreamContentType.TEXT,
                                            content=text,
                                            metadata={"position": position, "block_type": "text"}
                                        )
                                        self._stream_buffers[thread_id].append(chunk)
                                        session.last_stream_position = position
                                        position += 1
                                        yield chunk

                        elif isinstance(content, str) and content:
                            # Simple string content (final response)
                            chunk = StreamChunk(
                                content_type=StreamContentType.TEXT,
                                content=content,
                                metadata={"position": position}
                            )
                            self._stream_buffers[thread_id].append(chunk)
                            session.last_stream_position = position
                            position += 1
                            yield chunk

                # Handle tool calls
                elif kind == "on_tool_start":
                    tool_name = event.get("name", "unknown")
                    tool_input = event.get("data", {}).get("input", {})

                    chunk = StreamChunk(
                        content_type=StreamContentType.TOOL_CALL,
                        content=f"Calling tool: {tool_name}",
                        metadata={
                            "position": position,
                            "tool_name": tool_name,
                            "tool_input": tool_input
                        }
                    )
                    self._stream_buffers[thread_id].append(chunk)
                    session.last_stream_position = position
                    position += 1
                    yield chunk

                # Handle tool results
                elif kind == "on_tool_end":
                    tool_output = event.get("data", {}).get("output", "")

                    chunk = StreamChunk(
                        content_type=StreamContentType.TOOL_RESULT,
                        content=str(tool_output)[:500],  # Truncate long outputs
                        metadata={"position": position, "full_output_length": len(str(tool_output))}
                    )
                    self._stream_buffers[thread_id].append(chunk)
                    session.last_stream_position = position
                    position += 1
                    yield chunk

        except Exception as e:
            # Handle errors gracefully
            error_chunk = StreamChunk(
                content_type=StreamContentType.ERROR,
                content=str(e),
                metadata={"position": position, "error_type": type(e).__name__}
            )
            self._stream_buffers[thread_id].append(error_chunk)
            session.status = SessionStatus.DISCONNECTED
            yield error_chunk

        finally:
            # Update session
            session.updated_at = datetime.utcnow().isoformat()
            self._save_sessions()

    def get_thinking_summary(self, thread_id: str) -> Optional[ThinkingBlock]:
        """
        Get a summary of the thinking/reasoning from the last interaction.

        Returns aggregated thinking content with token count estimation.
        """
        buffer = self._stream_buffers.get(thread_id, [])

        thinking_chunks = [
            c for c in buffer
            if c.content_type == StreamContentType.THINKING
        ]

        if not thinking_chunks:
            return None

        # Aggregate thinking text
        thinking_text = "\n".join(c.content for c in thinking_chunks)

        # Estimate tokens (rough approximation: 4 chars per token)
        thinking_tokens = len(thinking_text) // 4

        # Extract tool calls from thinking
        tool_calls = [
            c.metadata.get("tool_name")
            for c in buffer
            if c.content_type == StreamContentType.TOOL_CALL
        ]

        # Calculate duration
        if thinking_chunks:
            first_ts = datetime.fromisoformat(thinking_chunks[0].timestamp)
            last_ts = datetime.fromisoformat(thinking_chunks[-1].timestamp)
            duration_ms = int((last_ts - first_ts).total_seconds() * 1000)
        else:
            duration_ms = 0

        return ThinkingBlock(
            thinking_text=thinking_text,
            thinking_tokens=thinking_tokens,
            duration_ms=duration_ms,
            tool_calls_planned=tool_calls
        )

    # =========================================================================
    # FEATURE 2: RECONNECTION TO AGENT STREAMS
    # =========================================================================

    def get_reconnection_state(
        self,
        thread_id: str,
        reconnect_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get the state needed to reconnect to an interrupted session.

        Returns:
            - Session metadata
            - Last known position in stream
            - Pending chunks that weren't processed
            - Reconnect configuration
        """
        session = self._sessions.get(thread_id)

        if not session:
            return {
                "success": False,
                "error": f"Session not found: {thread_id}"
            }

        # Validate reconnect token if provided
        if reconnect_token and session.reconnect_token != reconnect_token:
            return {
                "success": False,
                "error": "Invalid reconnect token"
            }

        # Get buffered chunks since last position
        buffer = self._stream_buffers.get(thread_id, [])
        pending_from_position = session.last_stream_position

        pending_chunks = [
            c.to_dict() for c in buffer
            if c.metadata.get("position", 0) >= pending_from_position
        ]

        return {
            "success": True,
            "thread_id": thread_id,
            "status": session.status.value,
            "last_stream_position": session.last_stream_position,
            "pending_chunks": pending_chunks,
            "pending_chunks_count": len(pending_chunks),
            "current_checkpoint_id": session.current_checkpoint_id,
            "current_branch": session.current_branch,
            "reconnect_config": {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_id": session.current_checkpoint_id
                }
            },
            "can_resume": session.status in [SessionStatus.ACTIVE, SessionStatus.PAUSED, SessionStatus.DISCONNECTED]
        }

    async def reconnect_stream(
        self,
        graph,
        thread_id: str,
        from_position: int = 0
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Reconnect to an existing stream and continue from last position.

        This allows clients to:
        1. Catch up on missed chunks from the buffer
        2. Continue receiving new chunks if the agent is still processing

        Usage:
            # On page reload or reconnection
            async for chunk in session_manager.reconnect_stream(graph, thread_id):
                process_chunk(chunk)
        """
        session = self._sessions.get(thread_id)

        if not session:
            yield StreamChunk(
                content_type=StreamContentType.ERROR,
                content=f"Session not found: {thread_id}"
            )
            return

        # Update session status
        session.status = SessionStatus.ACTIVE
        session.updated_at = datetime.utcnow().isoformat()

        # First, yield any buffered chunks from the last position
        buffer = self._stream_buffers.get(thread_id, [])

        for chunk in buffer:
            chunk_position = chunk.metadata.get("position", 0)
            if chunk_position >= from_position:
                yield chunk

        # Update the session's stream position
        if buffer:
            session.last_stream_position = max(
                c.metadata.get("position", 0) for c in buffer
            )

        self._save_sessions()

    def mark_session_reconnectable(self, thread_id: str) -> Dict[str, Any]:
        """
        Prepare a session for reconnection after disconnect.

        Returns reconnection information that can be stored client-side.
        """
        session = self._sessions.get(thread_id)

        if not session:
            return {"success": False, "error": "Session not found"}

        # Generate new reconnect token
        new_token = hashlib.sha256(
            f"{thread_id}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:32]

        session.reconnect_token = new_token
        session.status = SessionStatus.PAUSED
        session.updated_at = datetime.utcnow().isoformat()

        self._save_sessions()

        return {
            "success": True,
            "thread_id": thread_id,
            "reconnect_token": new_token,
            "last_position": session.last_stream_position,
            "current_checkpoint_id": session.current_checkpoint_id,
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }

    # =========================================================================
    # FEATURE 3: BRANCHING AND TIME TRAVEL
    # =========================================================================

    def create_checkpoint(
        self,
        thread_id: str,
        state: Dict[str, Any],
        description: str = "",
        branch_name: Optional[str] = None
    ) -> Checkpoint:
        """
        Create a checkpoint (snapshot) of the current conversation state.

        Checkpoints enable:
        - Time travel: Navigate back to previous states
        - Branching: Fork the conversation from any point
        - Comparison: Diff between checkpoints
        """
        session = self._sessions.get(thread_id)
        parent_checkpoint_id = session.current_checkpoint_id if session else None

        checkpoint_id = f"cp_{hashlib.md5(f'{thread_id}:{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:12]}"

        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            parent_checkpoint_id=parent_checkpoint_id,
            thread_id=thread_id,
            timestamp=datetime.utcnow().isoformat(),
            state=state,
            message_count=len(state.get("messages", [])),
            description=description,
            branch_name=branch_name or (session.current_branch if session else "main")
        )

        # Save checkpoint to disk
        self._save_checkpoint(checkpoint)
        self._checkpoints[checkpoint_id] = checkpoint

        # Update session
        if session:
            session.checkpoints.append(checkpoint_id)
            session.current_checkpoint_id = checkpoint_id
            session.updated_at = datetime.utcnow().isoformat()
            self._save_sessions()

        print(f"[SessionManager] Created checkpoint: {checkpoint_id} (parent: {parent_checkpoint_id})")
        return checkpoint

    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Retrieve a checkpoint by ID."""
        # Check cache first
        if checkpoint_id in self._checkpoints:
            return self._checkpoints[checkpoint_id]

        # Load from disk
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        if checkpoint_file.exists():
            with open(checkpoint_file, "r") as f:
                data = json.load(f)
                checkpoint = Checkpoint.from_dict(data)
                self._checkpoints[checkpoint_id] = checkpoint
                return checkpoint

        return None

    def list_checkpoints(
        self,
        thread_id: str,
        branch_name: Optional[str] = None
    ) -> List[Checkpoint]:
        """
        List all checkpoints for a thread, optionally filtered by branch.

        Returns checkpoints in chronological order.
        """
        session = self._sessions.get(thread_id)
        if not session:
            return []

        checkpoints = []
        for cp_id in session.checkpoints:
            cp = self.get_checkpoint(cp_id)
            if cp:
                if branch_name is None or cp.branch_name == branch_name:
                    checkpoints.append(cp)

        # Sort by timestamp
        checkpoints.sort(key=lambda c: c.timestamp)
        return checkpoints

    def time_travel(
        self,
        thread_id: str,
        checkpoint_id: str
    ) -> Dict[str, Any]:
        """
        Navigate to a specific checkpoint (time travel).

        This restores the conversation state to the point when
        the checkpoint was created.

        Returns the state at that checkpoint.
        """
        session = self._sessions.get(thread_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        checkpoint = self.get_checkpoint(checkpoint_id)
        if not checkpoint:
            return {"success": False, "error": f"Checkpoint not found: {checkpoint_id}"}

        if checkpoint.thread_id != thread_id:
            return {"success": False, "error": "Checkpoint belongs to different thread"}

        # Update session to point to this checkpoint
        session.current_checkpoint_id = checkpoint_id
        session.updated_at = datetime.utcnow().isoformat()

        # Clear stream buffer (we're going back in time)
        self._stream_buffers[thread_id] = []
        session.last_stream_position = 0

        self._save_sessions()

        return {
            "success": True,
            "checkpoint_id": checkpoint_id,
            "timestamp": checkpoint.timestamp,
            "description": checkpoint.description,
            "message_count": checkpoint.message_count,
            "state": checkpoint.state,
            "branch_name": checkpoint.branch_name
        }

    def create_branch(
        self,
        thread_id: str,
        branch_name: str,
        from_checkpoint_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new branch from a checkpoint.

        This allows exploring alternative conversation paths without
        losing the original conversation.

        Args:
            thread_id: The session thread ID
            branch_name: Name for the new branch
            from_checkpoint_id: Checkpoint to branch from (default: current)

        Returns:
            Branch creation result with new checkpoint info
        """
        session = self._sessions.get(thread_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        if branch_name in session.branches:
            return {"success": False, "error": f"Branch already exists: {branch_name}"}

        # Use current checkpoint if not specified
        source_cp_id = from_checkpoint_id or session.current_checkpoint_id

        if not source_cp_id:
            return {"success": False, "error": "No checkpoint to branch from"}

        source_checkpoint = self.get_checkpoint(source_cp_id)
        if not source_checkpoint:
            return {"success": False, "error": f"Source checkpoint not found: {source_cp_id}"}

        # Create new checkpoint for the branch
        branch_checkpoint = self.create_checkpoint(
            thread_id=thread_id,
            state=source_checkpoint.state.copy(),
            description=f"Branch '{branch_name}' from {source_cp_id}",
            branch_name=branch_name
        )

        # Update branch to point to the parent correctly
        branch_checkpoint.parent_checkpoint_id = source_cp_id
        self._save_checkpoint(branch_checkpoint)

        # Register the branch
        session.branches[branch_name] = branch_checkpoint.checkpoint_id
        session.current_branch = branch_name
        session.current_checkpoint_id = branch_checkpoint.checkpoint_id
        session.updated_at = datetime.utcnow().isoformat()

        self._save_sessions()

        return {
            "success": True,
            "branch_name": branch_name,
            "branch_checkpoint_id": branch_checkpoint.checkpoint_id,
            "source_checkpoint_id": source_cp_id,
            "message_count": branch_checkpoint.message_count
        }

    def switch_branch(
        self,
        thread_id: str,
        branch_name: str
    ) -> Dict[str, Any]:
        """Switch to a different branch."""
        session = self._sessions.get(thread_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        if branch_name not in session.branches:
            return {"success": False, "error": f"Branch not found: {branch_name}"}

        checkpoint_id = session.branches[branch_name]
        session.current_branch = branch_name
        session.current_checkpoint_id = checkpoint_id
        session.updated_at = datetime.utcnow().isoformat()

        # Clear stream buffer
        self._stream_buffers[thread_id] = []
        session.last_stream_position = 0

        self._save_sessions()

        checkpoint = self.get_checkpoint(checkpoint_id)

        return {
            "success": True,
            "branch_name": branch_name,
            "checkpoint_id": checkpoint_id,
            "message_count": checkpoint.message_count if checkpoint else 0,
            "state": checkpoint.state if checkpoint else {}
        }

    def list_branches(self, thread_id: str) -> List[Dict[str, Any]]:
        """List all branches for a thread."""
        session = self._sessions.get(thread_id)
        if not session:
            return []

        branches = []
        for name, cp_id in session.branches.items():
            checkpoint = self.get_checkpoint(cp_id)
            branches.append({
                "name": name,
                "checkpoint_id": cp_id,
                "is_current": name == session.current_branch,
                "message_count": checkpoint.message_count if checkpoint else 0,
                "created_at": checkpoint.timestamp if checkpoint else None
            })

        return branches

    def get_checkpoint_diff(
        self,
        checkpoint_id_1: str,
        checkpoint_id_2: str
    ) -> Dict[str, Any]:
        """
        Compare two checkpoints and return their differences.

        Useful for understanding what changed between points in time.
        """
        cp1 = self.get_checkpoint(checkpoint_id_1)
        cp2 = self.get_checkpoint(checkpoint_id_2)

        if not cp1 or not cp2:
            return {"success": False, "error": "One or both checkpoints not found"}

        messages1 = cp1.state.get("messages", [])
        messages2 = cp2.state.get("messages", [])

        # Find message differences
        added_messages = messages2[len(messages1):] if len(messages2) > len(messages1) else []
        removed_messages = messages1[len(messages2):] if len(messages1) > len(messages2) else []

        return {
            "success": True,
            "checkpoint_1": {
                "id": checkpoint_id_1,
                "timestamp": cp1.timestamp,
                "message_count": cp1.message_count,
                "branch": cp1.branch_name
            },
            "checkpoint_2": {
                "id": checkpoint_id_2,
                "timestamp": cp2.timestamp,
                "message_count": cp2.message_count,
                "branch": cp2.branch_name
            },
            "message_count_diff": cp2.message_count - cp1.message_count,
            "added_messages_count": len(added_messages),
            "removed_messages_count": len(removed_messages)
        }

    def get_history_tree(self, thread_id: str) -> Dict[str, Any]:
        """
        Get the full checkpoint history tree for a thread.

        Returns a tree structure showing all checkpoints and branches.
        """
        session = self._sessions.get(thread_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        checkpoints = self.list_checkpoints(thread_id)

        # Build tree structure
        tree = {
            "thread_id": thread_id,
            "current_branch": session.current_branch,
            "current_checkpoint": session.current_checkpoint_id,
            "branches": session.branches,
            "checkpoints": [
                {
                    "id": cp.checkpoint_id,
                    "parent_id": cp.parent_checkpoint_id,
                    "timestamp": cp.timestamp,
                    "description": cp.description,
                    "branch": cp.branch_name,
                    "message_count": cp.message_count
                }
                for cp in checkpoints
            ]
        }

        return {"success": True, "tree": tree}

    # =========================================================================
    # PERSISTENCE
    # =========================================================================

    def _load_sessions(self):
        """Load sessions from disk."""
        if self.sessions_file.exists():
            try:
                with open(self.sessions_file, "r") as f:
                    data = json.load(f)
                    for thread_id, session_data in data.items():
                        self._sessions[thread_id] = Session.from_dict(session_data)
                print(f"[SessionManager] Loaded {len(self._sessions)} sessions")
            except Exception as e:
                print(f"[SessionManager] Error loading sessions: {e}")

    def _save_sessions(self):
        """Save sessions to disk."""
        try:
            data = {
                thread_id: session.to_dict()
                for thread_id, session in self._sessions.items()
            }
            with open(self.sessions_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[SessionManager] Error saving sessions: {e}")

    def _save_checkpoint(self, checkpoint: Checkpoint):
        """Save a checkpoint to disk."""
        checkpoint_file = self.checkpoint_dir / f"{checkpoint.checkpoint_id}.json"
        try:
            with open(checkpoint_file, "w") as f:
                json.dump(checkpoint.to_dict(), f, indent=2)
        except Exception as e:
            print(f"[SessionManager] Error saving checkpoint: {e}")

    def cleanup_old_sessions(self, max_age_hours: int = 72):
        """Clean up sessions older than max_age_hours."""
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        cutoff_str = cutoff.isoformat()

        to_remove = []
        for thread_id, session in self._sessions.items():
            if session.updated_at < cutoff_str and session.status != SessionStatus.ACTIVE:
                to_remove.append(thread_id)

        for thread_id in to_remove:
            # Remove checkpoints
            session = self._sessions[thread_id]
            for cp_id in session.checkpoints:
                cp_file = self.checkpoint_dir / f"{cp_id}.json"
                if cp_file.exists():
                    cp_file.unlink()
                if cp_id in self._checkpoints:
                    del self._checkpoints[cp_id]

            # Remove session
            del self._sessions[thread_id]

            # Remove stream buffer
            if thread_id in self._stream_buffers:
                del self._stream_buffers[thread_id]

        if to_remove:
            print(f"[SessionManager] Cleaned up {len(to_remove)} old sessions")
            self._save_sessions()


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_session(thread_id: Optional[str] = None, **kwargs) -> Session:
    """Create a new session."""
    return get_session_manager().create_session(thread_id, **kwargs)


def get_session(thread_id: str) -> Optional[Session]:
    """Get a session by thread ID."""
    return get_session_manager().get_session(thread_id)


def create_checkpoint(thread_id: str, state: Dict, description: str = "") -> Checkpoint:
    """Create a checkpoint for a session."""
    return get_session_manager().create_checkpoint(thread_id, state, description)


def time_travel(thread_id: str, checkpoint_id: str) -> Dict[str, Any]:
    """Navigate to a specific checkpoint."""
    return get_session_manager().time_travel(thread_id, checkpoint_id)


def create_branch(thread_id: str, branch_name: str, from_checkpoint_id: Optional[str] = None) -> Dict[str, Any]:
    """Create a new branch from a checkpoint."""
    return get_session_manager().create_branch(thread_id, branch_name, from_checkpoint_id)


def switch_branch(thread_id: str, branch_name: str) -> Dict[str, Any]:
    """Switch to a different branch."""
    return get_session_manager().switch_branch(thread_id, branch_name)

"""
Feedback Collector for SDTM Agent Learning
===========================================
Collects implicit and explicit feedback signals from user interactions
to enable continuous agent improvement.

Signals tracked:
- Explicit: thumbs up/down (via API)
- Implicit: response copied, regenerated, dwell time, edited output
- Automatic: pipeline success/failure, validation scores, HITL approval/rejection
- Session: branching, time travel (negative signals)

Usage:
    from sdtm_pipeline.deepagents.feedback import get_feedback_collector, FeedbackSignal

    collector = get_feedback_collector()
    collector.record(
        signal=FeedbackSignal.THUMBS_UP,
        thread_id="session_abc123",
        user_query="Convert DM domain",
        agent_response_summary="Successfully converted 150 records...",
        domain="DM",
        tool_chain=["load_data_from_s3", "convert_domain"],
    )
"""

import hashlib
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Any, List, Optional


# =============================================================================
# ENUMS
# =============================================================================

class FeedbackSignal(str, Enum):
    """Types of feedback signals collected from user interactions."""
    # Explicit signals (user-initiated)
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"

    # Implicit signals (behavior-based)
    RESPONSE_COPIED = "response_copied"
    RESPONSE_REGENERATED = "response_regenerated"
    USER_EDITED_OUTPUT = "user_edited_output"
    FOLLOWUP_QUESTION = "followup_question"
    DWELL_TIME = "dwell_time"

    # Automatic signals (system-detected)
    PIPELINE_COMPLETED = "pipeline_completed"
    PIPELINE_FAILED = "pipeline_failed"
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    HITL_APPROVED = "hitl_approved"
    HITL_REJECTED = "hitl_rejected"

    # Session signals
    SESSION_BRANCHED = "session_branched"
    TIME_TRAVELED = "time_traveled"


class FeedbackSentiment(str, Enum):
    """Sentiment classification for feedback signals."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


# Signal -> Sentiment mapping
SIGNAL_SENTIMENT: Dict[FeedbackSignal, FeedbackSentiment] = {
    FeedbackSignal.THUMBS_UP: FeedbackSentiment.POSITIVE,
    FeedbackSignal.THUMBS_DOWN: FeedbackSentiment.NEGATIVE,
    FeedbackSignal.RESPONSE_COPIED: FeedbackSentiment.POSITIVE,
    FeedbackSignal.RESPONSE_REGENERATED: FeedbackSentiment.NEGATIVE,
    FeedbackSignal.USER_EDITED_OUTPUT: FeedbackSentiment.NEUTRAL,
    FeedbackSignal.FOLLOWUP_QUESTION: FeedbackSentiment.NEUTRAL,
    FeedbackSignal.DWELL_TIME: FeedbackSentiment.NEUTRAL,
    FeedbackSignal.PIPELINE_COMPLETED: FeedbackSentiment.POSITIVE,
    FeedbackSignal.PIPELINE_FAILED: FeedbackSentiment.NEGATIVE,
    FeedbackSignal.VALIDATION_PASSED: FeedbackSentiment.POSITIVE,
    FeedbackSignal.VALIDATION_FAILED: FeedbackSentiment.NEGATIVE,
    FeedbackSignal.HITL_APPROVED: FeedbackSentiment.POSITIVE,
    FeedbackSignal.HITL_REJECTED: FeedbackSentiment.NEGATIVE,
    FeedbackSignal.SESSION_BRANCHED: FeedbackSentiment.NEGATIVE,
    FeedbackSignal.TIME_TRAVELED: FeedbackSentiment.NEGATIVE,
}

# Scoring weights for each signal (used in pattern extraction)
SIGNAL_WEIGHTS: Dict[FeedbackSignal, float] = {
    FeedbackSignal.THUMBS_UP: 0.30,
    FeedbackSignal.THUMBS_DOWN: -0.30,
    FeedbackSignal.RESPONSE_COPIED: 0.20,
    FeedbackSignal.RESPONSE_REGENERATED: -0.10,
    FeedbackSignal.USER_EDITED_OUTPUT: 0.05,
    FeedbackSignal.FOLLOWUP_QUESTION: -0.05,
    FeedbackSignal.DWELL_TIME: 0.0,  # Scored separately based on duration
    FeedbackSignal.PIPELINE_COMPLETED: 0.15,
    FeedbackSignal.PIPELINE_FAILED: -0.15,
    FeedbackSignal.VALIDATION_PASSED: 0.15,
    FeedbackSignal.VALIDATION_FAILED: -0.15,
    FeedbackSignal.HITL_APPROVED: 0.05,
    FeedbackSignal.HITL_REJECTED: -0.05,
    FeedbackSignal.SESSION_BRANCHED: -0.05,
    FeedbackSignal.TIME_TRAVELED: -0.05,
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class FeedbackEvent:
    """A single feedback event captured from a user interaction."""
    event_id: str
    thread_id: str
    signal: FeedbackSignal
    sentiment: FeedbackSentiment
    timestamp: str

    # Context about the interaction
    message_index: int = -1
    user_query: str = ""
    agent_response_summary: str = ""

    # Domain-specific context
    domain: Optional[str] = None
    tool_chain: List[str] = field(default_factory=list)
    validation_score: Optional[float] = None

    # Signal-specific metadata
    # e.g., dwell_time_seconds, edited_text, compliance_score, error_message
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["signal"] = self.signal.value
        data["sentiment"] = self.sentiment.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeedbackEvent":
        data["signal"] = FeedbackSignal(data["signal"])
        data["sentiment"] = FeedbackSentiment(data["sentiment"])
        return cls(**data)


@dataclass
class InteractionPattern:
    """
    An extracted pattern from successful interactions.
    Stored in the learning store and used to enhance future prompts.
    """
    pattern_id: str
    source: str  # "positive_feedback" | "successful_pipeline" | "high_validation"
    query_type: str  # e.g., "domain_conversion", "validation_query", "mapping_question"
    domain: Optional[str] = None

    # The successful interaction pattern
    user_query_example: str = ""
    effective_tool_chain: List[str] = field(default_factory=list)
    effective_prompt_context: str = ""  # Insight from this pattern

    # Quality metrics
    feedback_score: float = 0.0  # 0.0 to 1.0
    times_reinforced: int = 1
    last_reinforced: str = ""
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InteractionPattern":
        return cls(**data)


# =============================================================================
# FEEDBACK COLLECTOR
# =============================================================================

class FeedbackCollector:
    """
    Centralized feedback collector that receives signals from all sources
    and writes them to the learning store.

    Sources:
    - API endpoints (POST /feedback) for explicit/implicit signals
    - Session manager hooks for branch/time-travel signals
    - Tool wrappers for pipeline/validation signals
    - Agent tools for self-reported signals
    """

    def __init__(self):
        self._store = None  # Lazy initialization to avoid circular imports
        self._event_count = 0
        self._last_queries: Dict[str, str] = {}  # thread_id -> last user query

    @property
    def store(self):
        """Lazy import of LearningStore to avoid circular imports."""
        if self._store is None:
            from .learning_store import get_learning_store
            self._store = get_learning_store()
        return self._store

    def record(
        self,
        signal: FeedbackSignal,
        thread_id: str,
        user_query: str = "",
        agent_response_summary: str = "",
        domain: Optional[str] = None,
        tool_chain: Optional[List[str]] = None,
        validation_score: Optional[float] = None,
        message_index: int = -1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FeedbackEvent:
        """
        Record a feedback event.

        Args:
            signal: The type of feedback signal
            thread_id: Session thread ID
            user_query: The user's original query
            agent_response_summary: First 200 chars of agent response
            domain: SDTM domain being worked on (DM, AE, etc.)
            tool_chain: Tools used in this interaction turn
            validation_score: If validation was performed
            message_index: Position in the conversation
            metadata: Additional signal-specific data

        Returns:
            The created FeedbackEvent
        """
        now = datetime.utcnow().isoformat() + "Z"
        event_id = f"fb_{hashlib.md5(f'{thread_id}:{now}:{signal.value}'.encode()).hexdigest()[:12]}"

        sentiment = SIGNAL_SENTIMENT.get(signal, FeedbackSentiment.NEUTRAL)

        event = FeedbackEvent(
            event_id=event_id,
            thread_id=thread_id,
            signal=signal,
            sentiment=sentiment,
            timestamp=now,
            message_index=message_index,
            user_query=user_query[:500],  # Truncate long queries
            agent_response_summary=agent_response_summary[:200],
            domain=domain,
            tool_chain=tool_chain or [],
            validation_score=validation_score,
            metadata=metadata or {},
        )

        # Persist to learning store
        self.store.record_event(event)
        self._event_count += 1

        # Track last query for regeneration detection
        if user_query:
            self._last_queries[thread_id] = user_query

        # Trigger pattern extraction every 50 events
        if self._event_count % 50 == 0:
            try:
                self.store.extract_patterns()
            except Exception as e:
                print(f"[FeedbackCollector] Pattern extraction failed: {e}")

        return event

    def record_pipeline_result(
        self,
        thread_id: str,
        success: bool,
        domain: Optional[str] = None,
        tool_chain: Optional[List[str]] = None,
        validation_score: Optional[float] = None,
        user_query: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FeedbackEvent:
        """Record a pipeline completion or failure."""
        signal = FeedbackSignal.PIPELINE_COMPLETED if success else FeedbackSignal.PIPELINE_FAILED

        # Also record validation result if score is provided
        events = []
        event = self.record(
            signal=signal,
            thread_id=thread_id,
            domain=domain,
            tool_chain=tool_chain,
            validation_score=validation_score,
            user_query=user_query,
            metadata=metadata,
        )
        events.append(event)

        if validation_score is not None:
            val_signal = (
                FeedbackSignal.VALIDATION_PASSED
                if validation_score >= 95.0
                else FeedbackSignal.VALIDATION_FAILED
            )
            val_event = self.record(
                signal=val_signal,
                thread_id=thread_id,
                domain=domain,
                validation_score=validation_score,
                user_query=user_query,
                metadata={"compliance_score": validation_score},
            )
            events.append(val_event)

        return event

    def detect_regeneration(self, thread_id: str, user_query: str) -> bool:
        """
        Detect if the user is regenerating (re-asking the same/similar query).
        Returns True if regeneration is detected.
        """
        last_query = self._last_queries.get(thread_id, "")
        if not last_query:
            return False

        # Simple check: exact match or high overlap
        if user_query.strip().lower() == last_query.strip().lower():
            self.record(
                signal=FeedbackSignal.RESPONSE_REGENERATED,
                thread_id=thread_id,
                user_query=user_query,
                metadata={"previous_query": last_query},
            )
            return True

        return False

    def get_event_count(self) -> int:
        """Return total events recorded this session."""
        return self._event_count


# =============================================================================
# SINGLETON
# =============================================================================

_feedback_collector: Optional[FeedbackCollector] = None


def get_feedback_collector() -> FeedbackCollector:
    """Get the global FeedbackCollector instance."""
    global _feedback_collector
    if _feedback_collector is None:
        _feedback_collector = FeedbackCollector()
    return _feedback_collector

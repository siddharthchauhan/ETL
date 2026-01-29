"""
Feedback Tools for SDTM Agent
===============================
LangGraph tools that allow the agent to:
1. Record user feedback about interactions
2. Retrieve learned patterns from past successes
3. Display a learning dashboard with metrics

These tools are added to SDTM_TOOLS and are callable by the agent during conversations.

Usage by the agent:
    - After completing a task: call record_user_feedback with the user's signal
    - When approaching a familiar task: call get_learned_patterns to check past successes
    - When user asks about performance: call show_learning_dashboard
"""

from typing import Dict, Any, Optional
from langchain_core.tools import tool

from .feedback import FeedbackSignal, get_feedback_collector
from .learning_store import get_learning_store, detect_query_type
from .adaptive_prompt import get_adaptive_prompt_builder


# =============================================================================
# TOOL 1: RECORD FEEDBACK
# =============================================================================

@tool
async def record_user_feedback(
    signal: str,
    thread_id: str = "",
    context: str = "",
    domain: str = "",
) -> Dict[str, Any]:
    """Record user feedback about an agent interaction.

    Use this tool to capture user satisfaction signals after completing a task.
    This helps the agent learn and improve over time.

    Args:
        signal: Feedback signal type. One of:
            - "thumbs_up" - User explicitly liked the response
            - "thumbs_down" - User explicitly disliked the response
            - "response_copied" - User copied the response (positive signal)
            - "followup_question" - User asked a follow-up (may indicate incomplete answer)
        thread_id: Session thread ID (auto-detected if empty)
        context: Additional context about the feedback (e.g., what the user said)
        domain: SDTM domain being worked on (DM, AE, VS, LB, etc.)

    Returns:
        Confirmation with event_id and signal recorded
    """
    # Validate signal
    valid_signals = {
        "thumbs_up": FeedbackSignal.THUMBS_UP,
        "thumbs_down": FeedbackSignal.THUMBS_DOWN,
        "response_copied": FeedbackSignal.RESPONSE_COPIED,
        "followup_question": FeedbackSignal.FOLLOWUP_QUESTION,
        "pipeline_completed": FeedbackSignal.PIPELINE_COMPLETED,
        "pipeline_failed": FeedbackSignal.PIPELINE_FAILED,
    }

    if signal not in valid_signals:
        return {
            "success": False,
            "error": f"Invalid signal: {signal}. Valid signals: {list(valid_signals.keys())}",
        }

    collector = get_feedback_collector()
    event = collector.record(
        signal=valid_signals[signal],
        thread_id=thread_id or "unknown",
        user_query=context,
        domain=domain.upper() if domain else None,
    )

    return {
        "success": True,
        "event_id": event.event_id,
        "signal": signal,
        "sentiment": event.sentiment.value,
        "message": f"Feedback recorded: {signal} for {domain or 'general'} interaction",
    }


# =============================================================================
# TOOL 2: GET LEARNED PATTERNS
# =============================================================================

@tool
async def get_learned_patterns(
    query_type: str = "",
    domain: str = "",
    query: str = "",
) -> Dict[str, Any]:
    """Retrieve learned patterns from past successful interactions.

    Use this tool when approaching a task that the agent may have handled
    successfully before. Returns insights about effective tool chains,
    approaches, and tips from past interactions.

    Args:
        query_type: Type of query (e.g., "domain_conversion", "validation_query",
                    "mapping_question", "knowledge_lookup", "pipeline_execution")
        domain: SDTM domain to get patterns for (DM, AE, VS, LB, etc.)
        query: The current user query for semantic matching

    Returns:
        List of learned patterns with tool chains, insights, and confidence scores
    """
    store = get_learning_store()

    # Use query for matching if provided
    search_query = query or query_type
    patterns = store.get_relevant_patterns(
        query=search_query,
        domain=domain.upper() if domain else None,
        top_k=5,
    )

    if not patterns:
        return {
            "success": True,
            "patterns": [],
            "message": "No learned patterns found yet. The agent will learn from future interactions.",
        }

    pattern_list = []
    for p in patterns:
        pattern_list.append({
            "pattern_id": p.pattern_id,
            "query_type": p.query_type,
            "domain": p.domain,
            "insight": p.effective_prompt_context,
            "tool_chain": p.effective_tool_chain,
            "confidence": round(p.feedback_score, 2),
            "times_reinforced": p.times_reinforced,
            "source": p.source,
        })

    # Also get domain insights if available
    domain_insights = {}
    if domain:
        domain_insights = store.get_domain_insights(domain.upper())

    return {
        "success": True,
        "patterns": pattern_list,
        "domain_insights": domain_insights,
        "message": f"Found {len(pattern_list)} learned patterns",
    }


# =============================================================================
# TOOL 3: LEARNING DASHBOARD
# =============================================================================

@tool
async def show_learning_dashboard() -> Dict[str, Any]:
    """Show the agent's learning metrics and feedback dashboard.

    Displays comprehensive metrics about agent performance including:
    - Overall positive/negative feedback rates
    - Response copy rate (user satisfaction proxy)
    - Pipeline success rates by domain
    - Validation score averages
    - Tool effectiveness rankings
    - Number of learned patterns
    - Improvement trends

    Returns:
        Dashboard data with metrics and chart-ready data
    """
    store = get_learning_store()
    builder = get_adaptive_prompt_builder()

    # Compute fresh metrics
    metrics = store.compute_metrics()
    learning_summary = builder.get_learning_summary()

    # Build chart-ready data for domain performance
    domain_chart_data = []
    for domain, d_metrics in metrics.get("domain_metrics", {}).items():
        domain_chart_data.append({
            "name": domain,
            "positive_rate": round(d_metrics.get("positive_rate", 0) * 100, 1),
            "avg_validation": round(d_metrics.get("avg_validation_score", 0), 1),
            "events": d_metrics.get("event_count", 0),
        })

    # Build chart-ready data for tool effectiveness
    tool_chart_data = []
    for tool_name, success_rate in sorted(
        metrics.get("tool_success_rates", {}).items(),
        key=lambda x: x[1],
        reverse=True,
    )[:10]:
        tool_chart_data.append({
            "name": tool_name,
            "success_rate": round(success_rate * 100, 1),
        })

    # Build chart-ready data for signal distribution
    signal_chart_data = []
    for signal_name, count in metrics.get("signal_counts", {}).items():
        signal_chart_data.append({
            "name": signal_name,
            "count": count,
        })

    return {
        "success": True,
        "overview": {
            "total_interactions": metrics.get("total_interactions", 0),
            "total_feedback_events": metrics.get("total_feedback_events", 0),
            "positive_rate": round(metrics.get("positive_rate", 0) * 100, 1),
            "negative_rate": round(metrics.get("negative_rate", 0) * 100, 1),
            "copy_rate": round(metrics.get("copy_rate", 0) * 100, 1),
            "regeneration_rate": round(metrics.get("regeneration_rate", 0) * 100, 1),
            "pipeline_success_rate": round(metrics.get("pipeline_success_rate", 0) * 100, 1),
            "avg_validation_score": round(metrics.get("avg_validation_score", 0), 1),
            "hitl_approval_rate": round(metrics.get("hitl_approval_rate", 0) * 100, 1),
        },
        "learning": {
            "patterns_learned": learning_summary.get("total_patterns_learned", 0),
            "patterns_by_domain": learning_summary.get("patterns_by_domain", {}),
            "top_performing_tools": learning_summary.get("top_performing_tools", {}),
        },
        "charts": {
            "domain_performance": domain_chart_data,
            "tool_effectiveness": tool_chart_data,
            "signal_distribution": signal_chart_data,
        },
        "computed_at": metrics.get("computed_at", ""),
    }


# =============================================================================
# TOOL LIST (for import into tools.py)
# =============================================================================

FEEDBACK_TOOLS = [
    record_user_feedback,
    get_learned_patterns,
    show_learning_dashboard,
]

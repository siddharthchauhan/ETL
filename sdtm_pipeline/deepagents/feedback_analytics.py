"""
Feedback Analytics for SDTM Agent
==================================
Computes aggregated metrics and time-series trends from feedback events.
Used by the learning dashboard tool and the file server API endpoints.

Metrics computed:
- Overall: positive/negative rates, copy rate, regeneration rate
- Pipeline: success rate, avg validation score, HITL approval rate
- Per-domain: event counts, positive rates, validation scores
- Tool: success rates per tool
- Trends: daily metrics over last 30 days
- Learning: pattern count, reinforcement counts, improvement delta

Usage:
    from sdtm_pipeline.deepagents.feedback_analytics import compute_analytics

    analytics = compute_analytics()
    print(f"Positive rate: {analytics.positive_rate:.0%}")
    print(f"Pipeline success: {analytics.pipeline_success_rate:.0%}")
"""

from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from .feedback import FeedbackEvent, FeedbackSignal, FeedbackSentiment
from .learning_store import get_learning_store


# =============================================================================
# METRICS DATA CLASS
# =============================================================================

@dataclass
class FeedbackMetrics:
    """Aggregated feedback metrics for dashboard display."""

    # Overall
    total_interactions: int = 0
    total_feedback_events: int = 0
    positive_rate: float = 0.0
    negative_rate: float = 0.0

    # Response quality
    copy_rate: float = 0.0
    regeneration_rate: float = 0.0
    avg_dwell_time_seconds: float = 0.0

    # Pipeline quality
    pipeline_success_rate: float = 0.0
    avg_validation_score: float = 0.0
    hitl_approval_rate: float = 0.0

    # Per-domain breakdown
    domain_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Tool effectiveness
    tool_success_rates: Dict[str, float] = field(default_factory=dict)

    # Learning metrics
    patterns_extracted: int = 0
    patterns_used: int = 0
    learning_improvement: float = 0.0  # Delta in positive rate over time

    # Time series
    daily_metrics: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    computed_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# ANALYTICS FUNCTIONS
# =============================================================================

def compute_analytics(days: int = 30) -> FeedbackMetrics:
    """
    Compute comprehensive feedback analytics.

    Args:
        days: Number of days to include in time-series data

    Returns:
        FeedbackMetrics with all computed values
    """
    store = get_learning_store()

    # Get all events
    events = store.read_events(limit=10000)
    if not events:
        return FeedbackMetrics(computed_at=datetime.utcnow().isoformat())

    metrics = FeedbackMetrics()
    metrics.total_feedback_events = len(events)
    metrics.computed_at = datetime.utcnow().isoformat()

    # Count unique interactions
    interactions = set()
    for e in events:
        if e.user_query:
            interactions.add(f"{e.thread_id}:{e.user_query[:50]}")
    metrics.total_interactions = max(len(interactions), 1)

    # Signal counts
    signal_counts: Dict[FeedbackSignal, int] = defaultdict(int)
    sentiment_counts: Dict[FeedbackSentiment, int] = defaultdict(int)
    for e in events:
        signal_counts[e.signal] += 1
        sentiment_counts[e.sentiment] += 1

    total = len(events)
    metrics.positive_rate = sentiment_counts.get(FeedbackSentiment.POSITIVE, 0) / total
    metrics.negative_rate = sentiment_counts.get(FeedbackSentiment.NEGATIVE, 0) / total

    # Response quality
    metrics.copy_rate = (
        signal_counts.get(FeedbackSignal.RESPONSE_COPIED, 0) / metrics.total_interactions
    )
    metrics.regeneration_rate = (
        signal_counts.get(FeedbackSignal.RESPONSE_REGENERATED, 0) / metrics.total_interactions
    )

    # Dwell time
    dwell_events = [
        e for e in events
        if e.signal == FeedbackSignal.DWELL_TIME
        and "dwell_time_seconds" in e.metadata
    ]
    if dwell_events:
        metrics.avg_dwell_time_seconds = sum(
            e.metadata["dwell_time_seconds"] for e in dwell_events
        ) / len(dwell_events)

    # Pipeline quality
    pipeline_success = signal_counts.get(FeedbackSignal.PIPELINE_COMPLETED, 0)
    pipeline_fail = signal_counts.get(FeedbackSignal.PIPELINE_FAILED, 0)
    pipeline_total = pipeline_success + pipeline_fail
    metrics.pipeline_success_rate = pipeline_success / pipeline_total if pipeline_total > 0 else 0.0

    # Validation scores
    val_scores = [e.validation_score for e in events if e.validation_score is not None]
    metrics.avg_validation_score = sum(val_scores) / len(val_scores) if val_scores else 0.0

    # HITL
    hitl_approved = signal_counts.get(FeedbackSignal.HITL_APPROVED, 0)
    hitl_rejected = signal_counts.get(FeedbackSignal.HITL_REJECTED, 0)
    hitl_total = hitl_approved + hitl_rejected
    metrics.hitl_approval_rate = hitl_approved / hitl_total if hitl_total > 0 else 0.0

    # Per-domain metrics
    metrics.domain_metrics = _compute_domain_metrics(events)

    # Tool effectiveness
    metrics.tool_success_rates = _compute_tool_success_rates(events)

    # Learning metrics
    all_patterns = store._load_all_patterns()
    metrics.patterns_extracted = len(all_patterns)

    # Daily trend
    metrics.daily_metrics = _compute_daily_trend(events, days)

    # Learning improvement (compare first half vs second half positive rates)
    metrics.learning_improvement = _compute_improvement(events)

    return metrics


def _compute_domain_metrics(events: List[FeedbackEvent]) -> Dict[str, Dict[str, float]]:
    """Compute per-domain metrics."""
    domain_events: Dict[str, List[FeedbackEvent]] = defaultdict(list)
    for e in events:
        if e.domain:
            domain_events[e.domain].append(e)

    result = {}
    for domain, d_events in domain_events.items():
        d_total = len(d_events)
        d_positive = sum(1 for e in d_events if e.sentiment == FeedbackSentiment.POSITIVE)
        d_val_scores = [e.validation_score for e in d_events if e.validation_score is not None]
        d_pipeline_ok = sum(1 for e in d_events if e.signal == FeedbackSignal.PIPELINE_COMPLETED)
        d_pipeline_fail = sum(1 for e in d_events if e.signal == FeedbackSignal.PIPELINE_FAILED)
        d_pipeline_total = d_pipeline_ok + d_pipeline_fail

        result[domain] = {
            "event_count": d_total,
            "positive_rate": d_positive / d_total if d_total > 0 else 0.0,
            "avg_validation_score": sum(d_val_scores) / len(d_val_scores) if d_val_scores else 0.0,
            "pipeline_success_rate": d_pipeline_ok / d_pipeline_total if d_pipeline_total > 0 else 0.0,
        }

    return result


def _compute_tool_success_rates(events: List[FeedbackEvent]) -> Dict[str, float]:
    """Compute success rates per tool."""
    tool_outcomes: Dict[str, Dict[str, int]] = defaultdict(lambda: {"success": 0, "fail": 0})

    for e in events:
        if not e.tool_chain:
            continue
        is_success = e.sentiment == FeedbackSentiment.POSITIVE
        for tool_name in e.tool_chain:
            if is_success:
                tool_outcomes[tool_name]["success"] += 1
            else:
                tool_outcomes[tool_name]["fail"] += 1

    rates = {}
    for tool_name, outcomes in tool_outcomes.items():
        total = outcomes["success"] + outcomes["fail"]
        if total > 0:
            rates[tool_name] = outcomes["success"] / total

    return dict(sorted(rates.items(), key=lambda x: x[1], reverse=True))


def _compute_daily_trend(
    events: List[FeedbackEvent], days: int = 30
) -> List[Dict[str, Any]]:
    """Compute daily metrics for trend charts."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

    # Group events by day
    daily: Dict[str, List[FeedbackEvent]] = defaultdict(list)
    for e in events:
        if e.timestamp >= cutoff:
            day = e.timestamp[:10]  # YYYY-MM-DD
            daily[day].append(e)

    trend = []
    for day in sorted(daily.keys()):
        day_events = daily[day]
        d_total = len(day_events)
        d_positive = sum(1 for e in day_events if e.sentiment == FeedbackSentiment.POSITIVE)
        d_negative = sum(1 for e in day_events if e.sentiment == FeedbackSentiment.NEGATIVE)

        trend.append({
            "date": day,
            "total_events": d_total,
            "positive": d_positive,
            "negative": d_negative,
            "positive_rate": d_positive / d_total if d_total > 0 else 0.0,
        })

    return trend


def _compute_improvement(events: List[FeedbackEvent]) -> float:
    """
    Compute learning improvement by comparing positive rates
    between the first half and second half of events.

    Returns delta (positive = improving, negative = regressing).
    """
    if len(events) < 20:
        return 0.0

    mid = len(events) // 2
    first_half = events[:mid]
    second_half = events[mid:]

    first_positive = sum(1 for e in first_half if e.sentiment == FeedbackSentiment.POSITIVE)
    second_positive = sum(1 for e in second_half if e.sentiment == FeedbackSentiment.POSITIVE)

    first_rate = first_positive / len(first_half)
    second_rate = second_positive / len(second_half)

    return second_rate - first_rate

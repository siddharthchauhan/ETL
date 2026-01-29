"""
Learning Store for SDTM Agent
==============================
Persists feedback events and extracts successful interaction patterns
that are used to enhance future agent responses.

Storage Architecture:
    .sessions/feedback/
        events.jsonl          - Append-only raw event log
        patterns.json         - Extracted successful patterns (local cache)
        metrics.json          - Aggregated metrics for dashboard
        domain_insights.json  - Per-domain learning insights

Pattern Extraction:
    1. Read recent events from JSONL
    2. Group by (thread_id, message_index) into interaction bundles
    3. Score each bundle using weighted signal composition
    4. Extract tool chains and context from high-scoring bundles
    5. Deduplicate similar patterns
    6. Save to local cache (and optionally to Pinecone)

Usage:
    from sdtm_pipeline.deepagents.learning_store import get_learning_store

    store = get_learning_store()
    store.record_event(event)
    patterns = store.get_relevant_patterns("Convert DM domain", domain="DM")
"""

import json
import os
import hashlib
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

from .feedback import (
    FeedbackEvent,
    FeedbackSignal,
    FeedbackSentiment,
    InteractionPattern,
    SIGNAL_WEIGHTS,
    SIGNAL_SENTIMENT,
)


# =============================================================================
# CONFIGURATION
# =============================================================================

FEEDBACK_STORAGE_DIR = Path(os.getenv("FEEDBACK_STORAGE_DIR", "./.sessions/feedback"))
MIN_PATTERN_SCORE = 0.6  # Minimum score to extract as a pattern
MAX_EVENTS_FOR_EXTRACTION = 500  # Last N events to consider
PATTERN_REFRESH_INTERVAL = 50  # Re-extract patterns every N events


# =============================================================================
# QUERY TYPE DETECTION
# =============================================================================

QUERY_TYPE_KEYWORDS = {
    "domain_conversion": ["convert", "transform", "sdtm", "generate"],
    "validation_query": ["validate", "validation", "compliance", "check", "verify"],
    "mapping_question": ["mapping", "map", "specification", "spec"],
    "knowledge_lookup": ["what is", "how to", "explain", "guidance", "rules"],
    "data_loading": ["load", "download", "s3", "ingest", "scan"],
    "code_generation": ["sas", "r script", "program", "code"],
    "pipeline_execution": ["pipeline", "run", "execute", "all domains"],
    "visualization": ["chart", "dashboard", "graph", "visuali"],
    "export": ["export", "upload", "save", "neo4j"],
}


def detect_query_type(query: str) -> str:
    """Detect the type of query based on keywords."""
    query_lower = query.lower()
    for query_type, keywords in QUERY_TYPE_KEYWORDS.items():
        if any(kw in query_lower for kw in keywords):
            return query_type
    return "general"


def detect_domain_from_query(query: str) -> Optional[str]:
    """Extract SDTM domain from a user query."""
    query_upper = query.upper()
    domains = ["DM", "AE", "VS", "LB", "CM", "EX", "MH", "DS", "EG", "PE", "PC", "IE"]
    domain_names = {
        "DEMOGRAPHICS": "DM", "ADVERSE": "AE", "VITAL": "VS",
        "LAB": "LB", "CONCOMITANT": "CM", "EXPOSURE": "EX",
        "MEDICAL HISTORY": "MH", "DISPOSITION": "DS", "ECG": "EG",
        "PHYSICAL": "PE", "PHARMACOKINETIC": "PC", "INCLUSION": "IE",
    }

    # Check exact domain codes
    for domain in domains:
        if f" {domain} " in f" {query_upper} " or query_upper.endswith(f" {domain}"):
            return domain

    # Check domain names
    for name, domain in domain_names.items():
        if name in query_upper:
            return domain

    return None


# =============================================================================
# LEARNING STORE
# =============================================================================

class LearningStore:
    """
    Manages persistence of feedback events and extraction of learning patterns.

    Data flow:
        FeedbackEvent -> events.jsonl -> extract_patterns() -> patterns.json
                                                             -> domain_insights.json
                                                             -> metrics.json
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or FEEDBACK_STORAGE_DIR
        self.events_file = self.storage_dir / "events.jsonl"
        self.patterns_file = self.storage_dir / "patterns.json"
        self.metrics_file = self.storage_dir / "metrics.json"
        self.domain_insights_file = self.storage_dir / "domain_insights.json"

        # Ensure directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # In-memory caches
        self._patterns_cache: Dict[str, List[InteractionPattern]] = {}
        self._events_since_extraction = 0

        # Load existing patterns into cache
        self._load_patterns_cache()

    # =========================================================================
    # EVENT PERSISTENCE
    # =========================================================================

    def record_event(self, event: FeedbackEvent) -> None:
        """Append a feedback event to the JSONL log."""
        try:
            with open(self.events_file, "a") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
            self._events_since_extraction += 1
        except Exception as e:
            print(f"[LearningStore] Error recording event: {e}")

    def read_events(
        self,
        limit: int = MAX_EVENTS_FOR_EXTRACTION,
        thread_id: Optional[str] = None,
        signal: Optional[FeedbackSignal] = None,
        since: Optional[str] = None,
    ) -> List[FeedbackEvent]:
        """Read events from the JSONL log with optional filters."""
        events = []

        if not self.events_file.exists():
            return events

        try:
            with open(self.events_file, "r") as f:
                lines = f.readlines()

            # Read from the end for most recent events
            for line in reversed(lines):
                if len(events) >= limit:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    event = FeedbackEvent.from_dict(data)

                    # Apply filters
                    if thread_id and event.thread_id != thread_id:
                        continue
                    if signal and event.signal != signal:
                        continue
                    if since and event.timestamp < since:
                        break  # Events are chronological, can stop early

                    events.append(event)
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue

        except Exception as e:
            print(f"[LearningStore] Error reading events: {e}")

        events.reverse()  # Return in chronological order
        return events

    def get_event_count(self) -> int:
        """Count total events in the log."""
        if not self.events_file.exists():
            return 0
        try:
            with open(self.events_file, "r") as f:
                return sum(1 for line in f if line.strip())
        except Exception:
            return 0

    # =========================================================================
    # PATTERN EXTRACTION
    # =========================================================================

    def extract_patterns(self, min_score: float = MIN_PATTERN_SCORE) -> List[InteractionPattern]:
        """
        Extract successful interaction patterns from recent feedback events.

        Algorithm:
        1. Read last N events
        2. Group by (thread_id, message_index) into interaction bundles
        3. Score each bundle using weighted signal composition
        4. Extract patterns from bundles scoring above min_score
        5. Merge with existing patterns (reinforce duplicates)
        6. Save to local cache
        """
        events = self.read_events(limit=MAX_EVENTS_FOR_EXTRACTION)
        if not events:
            return []

        # Group events into interaction bundles
        bundles = self._group_into_bundles(events)

        # Score each bundle
        scored_bundles = []
        for bundle_key, bundle_events in bundles.items():
            score = self._score_bundle(bundle_events)
            if score >= min_score:
                scored_bundles.append((bundle_key, bundle_events, score))

        # Extract patterns from high-scoring bundles
        new_patterns = []
        for bundle_key, bundle_events, score in scored_bundles:
            pattern = self._extract_pattern(bundle_key, bundle_events, score)
            if pattern:
                new_patterns.append(pattern)

        # Merge with existing patterns
        merged = self._merge_patterns(new_patterns)

        # Save to cache and disk
        self._patterns_cache = self._organize_by_domain(merged)
        self._save_patterns_cache()
        self._events_since_extraction = 0

        # Update domain insights
        self._update_domain_insights(merged)

        print(f"[LearningStore] Extracted {len(new_patterns)} patterns, "
              f"{len(merged)} total after merge")

        return merged

    def _group_into_bundles(
        self, events: List[FeedbackEvent]
    ) -> Dict[str, List[FeedbackEvent]]:
        """Group events by interaction context (thread + query)."""
        bundles: Dict[str, List[FeedbackEvent]] = defaultdict(list)

        for event in events:
            # Use thread_id + user_query hash as the bundle key
            query_hash = hashlib.md5(event.user_query.lower().strip().encode()).hexdigest()[:8]
            bundle_key = f"{event.thread_id}:{query_hash}"
            bundles[bundle_key].append(event)

        return dict(bundles)

    def _score_bundle(self, events: List[FeedbackEvent]) -> float:
        """
        Score an interaction bundle based on its feedback signals.

        Returns a score in [0.0, 1.0] where:
        - 1.0 = highly successful interaction
        - 0.5 = neutral
        - 0.0 = highly unsuccessful
        """
        raw_score = 0.0
        max_possible = 0.0

        signals_seen = set()
        for event in events:
            if event.signal in signals_seen:
                continue  # Count each signal type once per bundle
            signals_seen.add(event.signal)

            weight = SIGNAL_WEIGHTS.get(event.signal, 0.0)
            raw_score += weight
            max_possible += abs(weight)

            # Special handling for dwell time
            if event.signal == FeedbackSignal.DWELL_TIME:
                dwell_seconds = event.metadata.get("dwell_time_seconds", 0)
                # 5-60 seconds is optimal reading time
                if 5 <= dwell_seconds <= 60:
                    raw_score += 0.05
                elif dwell_seconds < 2:
                    raw_score -= 0.05  # Too fast = probably not useful

            # Validation score bonus
            if event.validation_score is not None:
                # Normalize: 95+ is full bonus, 80- is penalty
                if event.validation_score >= 95:
                    raw_score += 0.10
                elif event.validation_score >= 80:
                    raw_score += 0.05
                else:
                    raw_score -= 0.05

        # Normalize to [0, 1]
        if max_possible > 0:
            normalized = (raw_score + max_possible) / (2 * max_possible)
        else:
            normalized = 0.5  # Neutral if no signals

        return max(0.0, min(1.0, normalized))

    def _extract_pattern(
        self,
        bundle_key: str,
        events: List[FeedbackEvent],
        score: float,
    ) -> Optional[InteractionPattern]:
        """Extract an InteractionPattern from a scored bundle."""
        if not events:
            return None

        # Get representative event (first one with user_query)
        representative = None
        for e in events:
            if e.user_query:
                representative = e
                break
        if not representative:
            representative = events[0]

        # Collect tool chains from all events in the bundle
        all_tools = []
        for e in events:
            all_tools.extend(e.tool_chain)
        # Deduplicate while preserving order
        seen = set()
        unique_tools = []
        for t in all_tools:
            if t not in seen:
                seen.add(t)
                unique_tools.append(t)

        # Determine query type and domain
        query_type = detect_query_type(representative.user_query)
        domain = representative.domain or detect_domain_from_query(representative.user_query)

        # Determine source
        positive_signals = [e for e in events if SIGNAL_SENTIMENT.get(e.signal) == FeedbackSentiment.POSITIVE]
        if any(e.signal == FeedbackSignal.THUMBS_UP for e in events):
            source = "positive_feedback"
        elif any(e.signal == FeedbackSignal.PIPELINE_COMPLETED for e in events):
            source = "successful_pipeline"
        elif any(e.signal == FeedbackSignal.VALIDATION_PASSED for e in events):
            source = "high_validation"
        else:
            source = "implicit_positive"

        # Build insight text
        insight = self._build_insight(representative, unique_tools, score, events)

        now = datetime.utcnow().isoformat() + "Z"
        pattern_id = f"pat_{hashlib.md5(f'{bundle_key}:{now}'.encode()).hexdigest()[:12]}"

        return InteractionPattern(
            pattern_id=pattern_id,
            source=source,
            query_type=query_type,
            domain=domain,
            user_query_example=representative.user_query[:200],
            effective_tool_chain=unique_tools,
            effective_prompt_context=insight,
            feedback_score=score,
            times_reinforced=1,
            last_reinforced=now,
            created_at=now,
        )

    def _build_insight(
        self,
        event: FeedbackEvent,
        tool_chain: List[str],
        score: float,
        all_events: List[FeedbackEvent],
    ) -> str:
        """Build a human-readable insight from a successful interaction."""
        parts = []

        # Query context
        if event.domain:
            parts.append(f"For {event.domain} domain tasks")
        if event.user_query:
            query_summary = event.user_query[:100]
            parts.append(f"when user asked '{query_summary}'")

        # Tool chain insight
        if tool_chain:
            chain_str = " -> ".join(tool_chain[:5])
            parts.append(f"the tool sequence [{chain_str}] was effective")

        # Validation insight
        val_events = [e for e in all_events if e.validation_score is not None]
        if val_events:
            best_score = max(e.validation_score for e in val_events)
            parts.append(f"achieving {best_score:.1f}% compliance")

        # Response quality insight
        if any(e.signal == FeedbackSignal.RESPONSE_COPIED for e in all_events):
            parts.append("the response was copied by the user (high satisfaction)")

        return ". ".join(parts) + "." if parts else ""

    def _merge_patterns(
        self, new_patterns: List[InteractionPattern]
    ) -> List[InteractionPattern]:
        """Merge new patterns with existing ones, reinforcing duplicates."""
        # Load existing patterns
        existing = self._load_all_patterns()

        # Build lookup by (query_type, domain, tool_chain_hash)
        existing_lookup: Dict[str, InteractionPattern] = {}
        for p in existing:
            key = self._pattern_dedup_key(p)
            existing_lookup[key] = p

        # Merge
        for new_p in new_patterns:
            key = self._pattern_dedup_key(new_p)
            if key in existing_lookup:
                # Reinforce existing pattern
                existing_p = existing_lookup[key]
                existing_p.times_reinforced += 1
                existing_p.last_reinforced = new_p.last_reinforced
                # Moving average of score
                existing_p.feedback_score = (
                    existing_p.feedback_score * 0.7 + new_p.feedback_score * 0.3
                )
                # Update insight if new one is richer
                if len(new_p.effective_prompt_context) > len(existing_p.effective_prompt_context):
                    existing_p.effective_prompt_context = new_p.effective_prompt_context
            else:
                existing_lookup[key] = new_p

        # Return all patterns sorted by score * reinforcement
        all_patterns = list(existing_lookup.values())
        all_patterns.sort(
            key=lambda p: p.feedback_score * min(p.times_reinforced, 10),
            reverse=True,
        )

        # Keep top 100 patterns
        return all_patterns[:100]

    def _pattern_dedup_key(self, pattern: InteractionPattern) -> str:
        """Generate a deduplication key for a pattern."""
        chain_hash = hashlib.md5(
            "|".join(pattern.effective_tool_chain).encode()
        ).hexdigest()[:8]
        return f"{pattern.query_type}:{pattern.domain or 'general'}:{chain_hash}"

    # =========================================================================
    # PATTERN RETRIEVAL
    # =========================================================================

    def get_relevant_patterns(
        self,
        query: str,
        domain: Optional[str] = None,
        top_k: int = 3,
    ) -> List[InteractionPattern]:
        """
        Retrieve patterns relevant to the current query.

        Strategy (local-cache-first for low latency):
        1. Check in-memory cache
        2. Filter by domain if provided
        3. Score relevance by query type match
        4. Return top_k patterns
        """
        if not self._patterns_cache:
            self._load_patterns_cache()

        candidates = []

        # Get domain-specific patterns
        if domain and domain in self._patterns_cache:
            candidates.extend(self._patterns_cache[domain])

        # Get general patterns
        if "_general" in self._patterns_cache:
            candidates.extend(self._patterns_cache["_general"])

        if not candidates:
            # Fallback: get all patterns
            for patterns in self._patterns_cache.values():
                candidates.extend(patterns)

        # Score relevance
        query_type = detect_query_type(query)
        scored = []
        for pattern in candidates:
            relevance = self._compute_relevance(pattern, query_type, domain)
            scored.append((pattern, relevance))

        # Sort by relevance * feedback_score
        scored.sort(key=lambda x: x[1] * x[0].feedback_score, reverse=True)

        return [p for p, _ in scored[:top_k]]

    def _compute_relevance(
        self,
        pattern: InteractionPattern,
        query_type: str,
        domain: Optional[str],
    ) -> float:
        """Compute relevance score of a pattern to the current query."""
        score = 0.0

        # Query type match
        if pattern.query_type == query_type:
            score += 0.5

        # Domain match
        if domain and pattern.domain == domain:
            score += 0.3
        elif pattern.domain is None:
            score += 0.1  # General patterns are somewhat relevant

        # Reinforcement bonus
        score += min(pattern.times_reinforced * 0.02, 0.2)

        return score

    def get_domain_insights(self, domain: str) -> Dict[str, Any]:
        """Get learning insights for a specific domain."""
        if not self.domain_insights_file.exists():
            return {}

        try:
            with open(self.domain_insights_file, "r") as f:
                all_insights = json.load(f)
            return all_insights.get(domain, {})
        except Exception:
            return {}

    # =========================================================================
    # METRICS
    # =========================================================================

    def compute_metrics(self) -> Dict[str, Any]:
        """Compute aggregated feedback metrics."""
        events = self.read_events(limit=5000)
        if not events:
            return {
                "total_interactions": 0,
                "total_feedback_events": 0,
                "positive_rate": 0.0,
                "negative_rate": 0.0,
                "copy_rate": 0.0,
                "regeneration_rate": 0.0,
                "pipeline_success_rate": 0.0,
                "avg_validation_score": 0.0,
                "hitl_approval_rate": 0.0,
                "domain_metrics": {},
                "tool_success_rates": {},
                "patterns_extracted": len(self._load_all_patterns()),
                "signal_counts": {},
                "computed_at": datetime.utcnow().isoformat() + "Z",
            }

        total = len(events)

        # Count by signal
        signal_counts: Dict[str, int] = defaultdict(int)
        for e in events:
            signal_counts[e.signal.value] += 1

        # Count by sentiment
        sentiment_counts: Dict[str, int] = defaultdict(int)
        for e in events:
            sentiment_counts[e.sentiment.value] += 1

        # Unique interactions (by thread + query)
        unique_interactions = set()
        for e in events:
            if e.user_query:
                unique_interactions.add(f"{e.thread_id}:{e.user_query[:50]}")
        total_interactions = max(len(unique_interactions), 1)

        # Rates
        positive_count = sentiment_counts.get("positive", 0)
        negative_count = sentiment_counts.get("negative", 0)

        copy_count = signal_counts.get(FeedbackSignal.RESPONSE_COPIED.value, 0)
        regen_count = signal_counts.get(FeedbackSignal.RESPONSE_REGENERATED.value, 0)

        pipeline_success = signal_counts.get(FeedbackSignal.PIPELINE_COMPLETED.value, 0)
        pipeline_fail = signal_counts.get(FeedbackSignal.PIPELINE_FAILED.value, 0)
        pipeline_total = pipeline_success + pipeline_fail

        hitl_approved = signal_counts.get(FeedbackSignal.HITL_APPROVED.value, 0)
        hitl_rejected = signal_counts.get(FeedbackSignal.HITL_REJECTED.value, 0)
        hitl_total = hitl_approved + hitl_rejected

        # Validation scores
        val_scores = [e.validation_score for e in events if e.validation_score is not None]
        avg_val = sum(val_scores) / len(val_scores) if val_scores else 0.0

        # Per-domain metrics
        domain_events: Dict[str, List[FeedbackEvent]] = defaultdict(list)
        for e in events:
            if e.domain:
                domain_events[e.domain].append(e)

        domain_metrics = {}
        for domain, d_events in domain_events.items():
            d_positive = sum(1 for e in d_events if e.sentiment == FeedbackSentiment.POSITIVE)
            d_total = len(d_events)
            d_val_scores = [e.validation_score for e in d_events if e.validation_score is not None]
            domain_metrics[domain] = {
                "event_count": d_total,
                "positive_rate": d_positive / d_total if d_total > 0 else 0.0,
                "avg_validation_score": sum(d_val_scores) / len(d_val_scores) if d_val_scores else 0.0,
            }

        # Tool success rates
        tool_outcomes: Dict[str, Dict[str, int]] = defaultdict(lambda: {"success": 0, "fail": 0})
        for e in events:
            if e.tool_chain:
                outcome = "success" if e.sentiment == FeedbackSentiment.POSITIVE else "fail"
                for tool_name in e.tool_chain:
                    tool_outcomes[tool_name][outcome] += 1

        tool_success_rates = {}
        for tool_name, outcomes in tool_outcomes.items():
            total_uses = outcomes["success"] + outcomes["fail"]
            if total_uses > 0:
                tool_success_rates[tool_name] = outcomes["success"] / total_uses

        metrics = {
            "total_interactions": total_interactions,
            "total_feedback_events": total,
            "positive_rate": positive_count / total if total > 0 else 0.0,
            "negative_rate": negative_count / total if total > 0 else 0.0,
            "copy_rate": copy_count / total_interactions,
            "regeneration_rate": regen_count / total_interactions,
            "pipeline_success_rate": pipeline_success / pipeline_total if pipeline_total > 0 else 0.0,
            "avg_validation_score": avg_val,
            "hitl_approval_rate": hitl_approved / hitl_total if hitl_total > 0 else 0.0,
            "domain_metrics": domain_metrics,
            "tool_success_rates": tool_success_rates,
            "patterns_extracted": len(self._load_all_patterns()),
            "signal_counts": dict(signal_counts),
            "computed_at": datetime.utcnow().isoformat() + "Z",
        }

        # Save metrics to disk
        self._save_metrics(metrics)

        return metrics

    # =========================================================================
    # PERSISTENCE HELPERS
    # =========================================================================

    def _load_patterns_cache(self) -> None:
        """Load patterns from disk into memory cache."""
        if not self.patterns_file.exists():
            self._patterns_cache = {}
            return

        try:
            with open(self.patterns_file, "r") as f:
                data = json.load(f)

            self._patterns_cache = {}
            for domain_key, pattern_dicts in data.items():
                self._patterns_cache[domain_key] = [
                    InteractionPattern.from_dict(p) for p in pattern_dicts
                ]
        except Exception as e:
            print(f"[LearningStore] Error loading patterns cache: {e}")
            self._patterns_cache = {}

    def _save_patterns_cache(self) -> None:
        """Save patterns cache to disk."""
        try:
            data = {}
            for domain_key, patterns in self._patterns_cache.items():
                data[domain_key] = [p.to_dict() for p in patterns]

            with open(self.patterns_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[LearningStore] Error saving patterns cache: {e}")

    def _load_all_patterns(self) -> List[InteractionPattern]:
        """Load all patterns from disk as a flat list."""
        if not self._patterns_cache:
            self._load_patterns_cache()

        all_patterns = []
        for patterns in self._patterns_cache.values():
            all_patterns.extend(patterns)
        return all_patterns

    def _organize_by_domain(
        self, patterns: List[InteractionPattern]
    ) -> Dict[str, List[InteractionPattern]]:
        """Organize patterns by domain for efficient lookup."""
        organized: Dict[str, List[InteractionPattern]] = defaultdict(list)
        for p in patterns:
            key = p.domain if p.domain else "_general"
            organized[key].append(p)
        return dict(organized)

    def _update_domain_insights(self, patterns: List[InteractionPattern]) -> None:
        """Update per-domain learning insights from patterns."""
        insights: Dict[str, Dict[str, Any]] = {}

        domain_patterns: Dict[str, List[InteractionPattern]] = defaultdict(list)
        for p in patterns:
            if p.domain:
                domain_patterns[p.domain].append(p)

        for domain, d_patterns in domain_patterns.items():
            # Top tool chains for this domain
            tool_chain_scores: Dict[str, float] = defaultdict(float)
            for p in d_patterns:
                chain_key = " -> ".join(p.effective_tool_chain[:5])
                tool_chain_scores[chain_key] += p.feedback_score * p.times_reinforced

            top_chains = sorted(
                tool_chain_scores.items(), key=lambda x: x[1], reverse=True
            )[:3]

            # Best insights
            best_patterns = sorted(d_patterns, key=lambda p: p.feedback_score, reverse=True)[:3]

            insights[domain] = {
                "pattern_count": len(d_patterns),
                "avg_score": sum(p.feedback_score for p in d_patterns) / len(d_patterns),
                "top_tool_chains": [{"chain": c, "score": s} for c, s in top_chains],
                "top_insights": [p.effective_prompt_context for p in best_patterns if p.effective_prompt_context],
                "updated_at": datetime.utcnow().isoformat() + "Z",
            }

        try:
            with open(self.domain_insights_file, "w") as f:
                json.dump(insights, f, indent=2)
        except Exception as e:
            print(f"[LearningStore] Error saving domain insights: {e}")

    def _save_metrics(self, metrics: Dict[str, Any]) -> None:
        """Save computed metrics to disk."""
        try:
            with open(self.metrics_file, "w") as f:
                json.dump(metrics, f, indent=2)
        except Exception as e:
            print(f"[LearningStore] Error saving metrics: {e}")


# =============================================================================
# SINGLETON
# =============================================================================

_learning_store: Optional[LearningStore] = None


def get_learning_store() -> LearningStore:
    """Get the global LearningStore instance."""
    global _learning_store
    if _learning_store is None:
        _learning_store = LearningStore()
    return _learning_store

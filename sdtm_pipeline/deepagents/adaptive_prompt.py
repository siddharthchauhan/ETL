"""
Adaptive Prompt Builder for SDTM Agent
=======================================
Dynamically enhances the agent's system prompt with learned patterns
from past successful interactions. This is the key module that closes
the feedback loop — turning collected signals into improved responses.

How it works:
1. On every chatbot turn, the builder is called with the user's query
2. It matches the query against cached patterns (local JSON, no API calls)
3. It generates a "## Learned from Past Interactions" section
4. This section is appended to the system prompt for that turn

Performance: <5ms per call (local cache only, no network I/O)

Usage:
    from sdtm_pipeline.deepagents.adaptive_prompt import get_adaptive_prompt_builder

    builder = get_adaptive_prompt_builder()
    learned_context = builder.build_learned_context(
        user_query="Convert DM domain to SDTM",
        domain_hint="DM"
    )
    # Append learned_context to system prompt
"""

from typing import Dict, List, Optional, Any

from .learning_store import get_learning_store, detect_query_type, detect_domain_from_query, LearningStore
from .feedback import InteractionPattern


# =============================================================================
# ADAPTIVE PROMPT BUILDER
# =============================================================================

class AdaptivePromptBuilder:
    """
    Builds dynamic prompt sections from learned interaction patterns.

    The builder reads from the local patterns cache (no API calls)
    and generates a concise "Learned from Past Interactions" section
    that guides the agent toward approaches that previously worked well.
    """

    def __init__(self, learning_store: Optional[LearningStore] = None):
        self._store = learning_store

    @property
    def store(self) -> LearningStore:
        if self._store is None:
            self._store = get_learning_store()
        return self._store

    def build_learned_context(
        self,
        user_query: str,
        domain_hint: Optional[str] = None,
        max_patterns: int = 3,
        max_chars: int = 800,
    ) -> str:
        """
        Build a dynamic prompt section from learned patterns.

        Args:
            user_query: The current user query
            domain_hint: Optional domain hint (e.g., "DM")
            max_patterns: Maximum number of patterns to include
            max_chars: Maximum character length of the section

        Returns:
            A string to append to the system prompt.
            Empty string if no relevant patterns found.
        """
        if not user_query.strip():
            return ""

        # Detect domain from query if not provided
        domain = domain_hint or detect_domain_from_query(user_query)

        # Get relevant patterns
        try:
            patterns = self.store.get_relevant_patterns(
                query=user_query,
                domain=domain,
                top_k=max_patterns,
            )
        except Exception:
            return ""

        if not patterns:
            return ""

        # Build the section
        sections = [
            "\n\n## Learned from Past Interactions\n",
            "Based on previous successful interactions with similar queries:\n",
        ]

        for i, pattern in enumerate(patterns, 1):
            entry = self._format_pattern(i, pattern)
            sections.append(entry)

        # Add domain insights if available
        if domain:
            domain_insight = self._get_domain_insight(domain)
            if domain_insight:
                sections.append(f"\n**{domain} Domain Insight:** {domain_insight}\n")

        result = "\n".join(sections)

        # Truncate if too long
        if len(result) > max_chars:
            result = result[:max_chars - 3] + "..."

        return result

    def _format_pattern(self, index: int, pattern: InteractionPattern) -> str:
        """Format a single pattern as a prompt section entry."""
        parts = []

        # Header with query type and domain
        domain_str = f" ({pattern.domain})" if pattern.domain else ""
        parts.append(f"{index}. **{pattern.query_type}{domain_str}**:")

        # Insight text
        if pattern.effective_prompt_context:
            insight = pattern.effective_prompt_context[:200]
            parts.append(f"   {insight}")

        # Tool chain preference
        if pattern.effective_tool_chain:
            chain = " -> ".join(pattern.effective_tool_chain[:5])
            parts.append(f"   Preferred tools: {chain}")

        # Confidence
        parts.append(
            f"   (Confidence: {pattern.feedback_score:.0%}, "
            f"reinforced {pattern.times_reinforced}x)"
        )

        return "\n".join(parts)

    def _get_domain_insight(self, domain: str) -> str:
        """Get a concise domain-specific insight."""
        try:
            insights = self.store.get_domain_insights(domain)
            if not insights:
                return ""

            top_insights = insights.get("top_insights", [])
            if top_insights:
                return top_insights[0][:200]

            top_chains = insights.get("top_tool_chains", [])
            if top_chains:
                return f"Most effective tool sequence: {top_chains[0].get('chain', '')}"

            return ""
        except Exception:
            return ""

    def get_tool_preference_hints(
        self, domain: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Return tool usage preferences learned from feedback.

        Returns a dict of tool_name -> success_rate (0.0 to 1.0).
        Useful for guiding the agent toward tools that historically work well.
        """
        try:
            metrics = self.store.compute_metrics()
            tool_rates = metrics.get("tool_success_rates", {})

            # If domain-specific, filter by tools used in that domain
            if domain:
                domain_metrics = metrics.get("domain_metrics", {}).get(domain, {})
                if domain_metrics:
                    # Return tools with domain context
                    return tool_rates

            return tool_rates
        except Exception:
            return {}

    def get_learning_summary(self) -> Dict[str, Any]:
        """
        Get a summary of what the agent has learned.
        Useful for the agent to self-report its learning status.
        """
        try:
            metrics = self.store.compute_metrics()

            patterns_by_domain = {}
            for domain_key, patterns in self.store._patterns_cache.items():
                if domain_key != "_general":
                    patterns_by_domain[domain_key] = len(patterns)

            return {
                "total_patterns_learned": metrics.get("patterns_extracted", 0),
                "patterns_by_domain": patterns_by_domain,
                "positive_feedback_rate": metrics.get("positive_rate", 0.0),
                "pipeline_success_rate": metrics.get("pipeline_success_rate", 0.0),
                "avg_validation_score": metrics.get("avg_validation_score", 0.0),
                "top_performing_tools": dict(
                    sorted(
                        metrics.get("tool_success_rates", {}).items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )[:5]
                ),
                "total_feedback_events": metrics.get("total_feedback_events", 0),
            }
        except Exception:
            return {"total_patterns_learned": 0, "status": "no data yet"}


# =============================================================================
# SINGLETON
# =============================================================================

_adaptive_builder: Optional[AdaptivePromptBuilder] = None


def get_adaptive_prompt_builder() -> AdaptivePromptBuilder:
    """Get the global AdaptivePromptBuilder instance."""
    global _adaptive_builder
    if _adaptive_builder is None:
        _adaptive_builder = AdaptivePromptBuilder()
    return _adaptive_builder

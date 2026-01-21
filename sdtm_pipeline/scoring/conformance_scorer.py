"""
Conformance Scoring System
==========================
Calculates weighted conformance scores from multi-layer validation results.

Score Thresholds:
- >= 95%: Submission ready, auto-approve
- 75-94%: Acceptable with warnings
- < 75%: Requires remediation
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


# Default scoring weights for each validation layer
SCORE_WEIGHTS = {
    "structural": 0.20,      # Required variables, types, lengths
    "cdisc": 0.25,           # SDTM-IG rules, CORE conformance
    "cross_domain": 0.15,    # Referential integrity
    "semantic": 0.15,        # Business logic
    "anomaly": 0.10,         # Statistical/physiological anomalies
    "protocol": 0.15,        # Protocol compliance
}

# Thresholds
SUBMISSION_THRESHOLD = 95.0  # >= 95% for auto-approve
ACCEPTABLE_THRESHOLD = 75.0  # 75-94% acceptable with warnings
REMEDIATION_THRESHOLD = 75.0  # < 75% requires remediation


class ConformanceStatus(Enum):
    """Overall conformance status."""
    SUBMISSION_READY = "submission_ready"
    ACCEPTABLE = "acceptable"
    NEEDS_REMEDIATION = "needs_remediation"


@dataclass
class LayerScore:
    """Score for a single validation layer."""
    layer: str
    raw_score: float  # 0-100
    weighted_score: float  # raw_score * weight
    weight: float
    error_count: int
    warning_count: int
    total_checks: int
    details: Optional[str] = None


@dataclass
class ConformanceScore:
    """Overall conformance score with layer breakdown."""
    overall_score: float  # 0-100 weighted average
    status: ConformanceStatus
    layer_scores: Dict[str, LayerScore] = field(default_factory=dict)
    domains_evaluated: List[str] = field(default_factory=list)
    total_errors: int = 0
    total_warnings: int = 0
    recommendations: List[str] = field(default_factory=list)
    calculated_at: str = ""

    def __post_init__(self):
        if not self.calculated_at:
            self.calculated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "overall_score": round(self.overall_score, 2),
            "status": self.status.value,
            "layer_scores": {
                layer: {
                    "raw_score": round(score.raw_score, 2),
                    "weighted_score": round(score.weighted_score, 4),
                    "weight": score.weight,
                    "error_count": score.error_count,
                    "warning_count": score.warning_count,
                    "total_checks": score.total_checks,
                    "details": score.details
                }
                for layer, score in self.layer_scores.items()
            },
            "domains_evaluated": self.domains_evaluated,
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "recommendations": self.recommendations,
            "calculated_at": self.calculated_at
        }


class ConformanceScorer:
    """
    Calculates weighted conformance scores from validation results.

    Combines results from all validation layers into a single
    conformance score that determines submission readiness.
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize scorer with optional custom weights.

        Args:
            weights: Custom weights for validation layers
        """
        self.weights = weights or SCORE_WEIGHTS.copy()

        # Normalize weights to sum to 1.0
        total = sum(self.weights.values())
        if total != 1.0:
            self.weights = {k: v / total for k, v in self.weights.items()}

    def calculate_layer_score(
        self,
        layer: str,
        results: Dict[str, Any]
    ) -> LayerScore:
        """
        Calculate score for a single validation layer.

        Args:
            layer: Layer name (structural, cdisc, etc.)
            results: Validation results for the layer

        Returns:
            LayerScore with raw and weighted scores
        """
        weight = self.weights.get(layer, 0.1)

        # Extract counts from results
        error_count = results.get("error_count", 0)
        warning_count = results.get("warning_count", 0)
        total_records = results.get("total_records", 1)

        # Handle issues list format
        issues = results.get("issues", [])
        if isinstance(issues, list):
            error_count = sum(1 for i in issues if i.get("severity") == "error")
            warning_count = sum(1 for i in issues if i.get("severity") == "warning")

        # Calculate raw score
        # Errors reduce score more than warnings
        # Base score of 100, -5 per error, -1 per warning
        # Normalized by record count to handle different dataset sizes
        if total_records > 0:
            error_penalty = min(50, (error_count / total_records) * 500)
            warning_penalty = min(30, (warning_count / total_records) * 100)
        else:
            error_penalty = min(50, error_count * 5)
            warning_penalty = min(30, warning_count * 1)

        raw_score = max(0, 100 - error_penalty - warning_penalty)

        # Special handling for is_valid flag
        if results.get("is_valid") is False and raw_score > 50:
            raw_score = 50  # Cap at 50 if explicitly marked invalid

        return LayerScore(
            layer=layer,
            raw_score=raw_score,
            weighted_score=raw_score * weight,
            weight=weight,
            error_count=error_count,
            warning_count=warning_count,
            total_checks=len(issues) if issues else error_count + warning_count,
            details=results.get("message", results.get("details"))
        )

    def calculate_score(
        self,
        validation_results: Dict[str, Any]
    ) -> ConformanceScore:
        """
        Calculate overall conformance score from all validation results.

        Args:
            validation_results: Dictionary with results from each validation layer
                Expected format:
                {
                    "structural": {...},
                    "cdisc": {...},
                    "cross_domain": {...},
                    "semantic": {...},
                    "anomaly": {...},
                    "protocol": {...}
                }

        Returns:
            ConformanceScore with overall and per-layer scores
        """
        layer_scores: Dict[str, LayerScore] = {}
        total_errors = 0
        total_warnings = 0
        domains = set()

        # Calculate score for each layer
        for layer in self.weights.keys():
            if layer in validation_results:
                results = validation_results[layer]
                layer_score = self.calculate_layer_score(layer, results)
                layer_scores[layer] = layer_score
                total_errors += layer_score.error_count
                total_warnings += layer_score.warning_count

                # Collect domains
                if "domain" in results:
                    domains.add(results["domain"])
                if "domains_validated" in results:
                    domains.update(results["domains_validated"])
            else:
                # Layer not provided - use neutral score
                layer_scores[layer] = LayerScore(
                    layer=layer,
                    raw_score=100.0,  # No issues found = perfect
                    weighted_score=100.0 * self.weights[layer],
                    weight=self.weights[layer],
                    error_count=0,
                    warning_count=0,
                    total_checks=0,
                    details="Not evaluated"
                )

        # Calculate weighted overall score
        overall_score = sum(ls.weighted_score for ls in layer_scores.values())

        # Determine status
        if overall_score >= SUBMISSION_THRESHOLD:
            status = ConformanceStatus.SUBMISSION_READY
        elif overall_score >= ACCEPTABLE_THRESHOLD:
            status = ConformanceStatus.ACCEPTABLE
        else:
            status = ConformanceStatus.NEEDS_REMEDIATION

        # Generate recommendations
        recommendations = self._generate_recommendations(
            layer_scores, total_errors, total_warnings
        )

        return ConformanceScore(
            overall_score=overall_score,
            status=status,
            layer_scores=layer_scores,
            domains_evaluated=list(domains),
            total_errors=total_errors,
            total_warnings=total_warnings,
            recommendations=recommendations
        )

    def _generate_recommendations(
        self,
        layer_scores: Dict[str, LayerScore],
        total_errors: int,
        total_warnings: int
    ) -> List[str]:
        """Generate improvement recommendations based on scores."""
        recommendations = []

        # Identify lowest scoring layers
        sorted_layers = sorted(
            layer_scores.items(),
            key=lambda x: x[1].raw_score
        )

        for layer, score in sorted_layers[:3]:  # Top 3 worst layers
            if score.raw_score < 80:
                if layer == "structural":
                    recommendations.append(
                        f"Address structural issues: {score.error_count} errors in required variables or data types"
                    )
                elif layer == "cdisc":
                    recommendations.append(
                        f"Fix CDISC conformance: {score.error_count} controlled terminology or date format issues"
                    )
                elif layer == "cross_domain":
                    recommendations.append(
                        f"Resolve cross-domain issues: {score.error_count} referential integrity problems"
                    )
                elif layer == "semantic":
                    recommendations.append(
                        f"Review semantic validation: {score.error_count} business logic violations"
                    )
                elif layer == "anomaly":
                    recommendations.append(
                        f"Investigate anomalies: {score.error_count} statistical or physiological outliers"
                    )
                elif layer == "protocol":
                    recommendations.append(
                        f"Check protocol compliance: {score.error_count} visit window or dosing issues"
                    )

        if total_errors > 0 and not recommendations:
            recommendations.append(
                f"Review and resolve {total_errors} error(s) to improve conformance score"
            )

        if total_warnings > 10:
            recommendations.append(
                f"Consider addressing {total_warnings} warning(s) for optimal data quality"
            )

        return recommendations

    def is_submission_ready(self, score: ConformanceScore) -> bool:
        """
        Check if data is ready for submission.

        Args:
            score: Conformance score to evaluate

        Returns:
            True if score >= 95%
        """
        return score.overall_score >= SUBMISSION_THRESHOLD

    def get_status_message(self, score: ConformanceScore) -> str:
        """Get human-readable status message."""
        if score.status == ConformanceStatus.SUBMISSION_READY:
            return f"SUBMISSION READY: Score {score.overall_score:.1f}% meets threshold"
        elif score.status == ConformanceStatus.ACCEPTABLE:
            return f"ACCEPTABLE WITH WARNINGS: Score {score.overall_score:.1f}% - review recommended"
        else:
            return f"NEEDS REMEDIATION: Score {score.overall_score:.1f}% - address {score.total_errors} errors"


def calculate_conformance_score(
    validation_results: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None
) -> ConformanceScore:
    """
    Convenience function to calculate conformance score.

    Args:
        validation_results: Results from all validation layers
        weights: Optional custom weights

    Returns:
        ConformanceScore
    """
    scorer = ConformanceScorer(weights)
    return scorer.calculate_score(validation_results)


def is_submission_ready(
    validation_results: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None
) -> Tuple[bool, float]:
    """
    Check if validation results indicate submission readiness.

    Args:
        validation_results: Results from all validation layers
        weights: Optional custom weights

    Returns:
        Tuple of (is_ready, score)
    """
    score = calculate_conformance_score(validation_results, weights)
    return score.overall_score >= SUBMISSION_THRESHOLD, score.overall_score

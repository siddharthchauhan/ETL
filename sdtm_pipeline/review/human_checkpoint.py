"""
Human-in-the-Loop Checkpoint System
====================================
Manages checkpoints where human review/approval is required
before the pipeline can proceed.

Checkpoints:
1. After raw validation (if errors)
2. After mapping generation
3. After max iterations reached
4. For critical severity issues
5. Final approval (if score < 95%)
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import os


class HumanCheckpoint(Enum):
    """Checkpoint types in the pipeline."""
    RAW_VALIDATION = "raw_validation"
    MAPPING_REVIEW = "mapping_review"
    SDTM_VALIDATION = "sdtm_validation"
    MAX_ITERATIONS = "max_iterations"
    CRITICAL_ISSUE = "critical_issue"
    FINAL_APPROVAL = "final_approval"


class CheckpointStatus(Enum):
    """Status of a checkpoint."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    TIMEOUT = "timeout"


class ReviewDecision(Enum):
    """Human review decision."""
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    REQUEST_INFO = "request_info"


@dataclass
class CheckpointRecord:
    """Record of a human checkpoint."""
    checkpoint_type: HumanCheckpoint
    status: CheckpointStatus
    created_at: str
    context: Dict[str, Any]
    decision: Optional[ReviewDecision] = None
    reviewer: Optional[str] = None
    reviewed_at: Optional[str] = None
    feedback: Optional[str] = None
    modifications: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_type": self.checkpoint_type.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "context": self.context,
            "decision": self.decision.value if self.decision else None,
            "reviewer": self.reviewer,
            "reviewed_at": self.reviewed_at,
            "feedback": self.feedback,
            "modifications": self.modifications
        }


class CheckpointManager:
    """
    Manages human-in-the-loop checkpoints.

    Provides functionality to:
    - Create checkpoints when conditions are met
    - Track pending reviews
    - Record decisions
    - Resume pipeline after approval
    """

    def __init__(self, study_id: str, output_dir: str = "."):
        self.study_id = study_id
        self.output_dir = output_dir
        self.checkpoints: List[CheckpointRecord] = []
        self.checkpoint_file = os.path.join(
            output_dir, f"checkpoints_{study_id}.json"
        )
        self._load_checkpoints()

    def _load_checkpoints(self) -> None:
        """Load existing checkpoints from file."""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    data = json.load(f)
                    for record in data:
                        self.checkpoints.append(CheckpointRecord(
                            checkpoint_type=HumanCheckpoint(record["checkpoint_type"]),
                            status=CheckpointStatus(record["status"]),
                            created_at=record["created_at"],
                            context=record["context"],
                            decision=ReviewDecision(record["decision"]) if record.get("decision") else None,
                            reviewer=record.get("reviewer"),
                            reviewed_at=record.get("reviewed_at"),
                            feedback=record.get("feedback"),
                            modifications=record.get("modifications")
                        ))
            except Exception as e:
                print(f"Error loading checkpoints: {e}")

    def _save_checkpoints(self) -> None:
        """Save checkpoints to file."""
        try:
            os.makedirs(os.path.dirname(self.checkpoint_file) or ".", exist_ok=True)
            with open(self.checkpoint_file, 'w') as f:
                json.dump(
                    [c.to_dict() for c in self.checkpoints],
                    f,
                    indent=2
                )
        except Exception as e:
            print(f"Error saving checkpoints: {e}")

    def create_checkpoint(
        self,
        checkpoint_type: HumanCheckpoint,
        context: Dict[str, Any]
    ) -> CheckpointRecord:
        """
        Create a new checkpoint requiring human review.

        Args:
            checkpoint_type: Type of checkpoint
            context: Context information for the reviewer

        Returns:
            Created checkpoint record
        """
        record = CheckpointRecord(
            checkpoint_type=checkpoint_type,
            status=CheckpointStatus.PENDING,
            created_at=datetime.now().isoformat(),
            context=context
        )
        self.checkpoints.append(record)
        self._save_checkpoints()

        print(f"\n{'='*60}")
        print(f"HUMAN REVIEW REQUIRED: {checkpoint_type.value}")
        print(f"{'='*60}")
        self._print_checkpoint_context(checkpoint_type, context)
        print(f"{'='*60}\n")

        return record

    def _print_checkpoint_context(
        self,
        checkpoint_type: HumanCheckpoint,
        context: Dict[str, Any]
    ) -> None:
        """Print checkpoint context for reviewer."""
        if checkpoint_type == HumanCheckpoint.RAW_VALIDATION:
            print(f"Raw data validation found issues:")
            print(f"  Errors: {context.get('error_count', 0)}")
            print(f"  Warnings: {context.get('warning_count', 0)}")
            if "domains" in context:
                print(f"  Affected domains: {', '.join(context['domains'])}")

        elif checkpoint_type == HumanCheckpoint.MAPPING_REVIEW:
            print(f"Mapping specifications generated:")
            print(f"  Domains: {context.get('domain_count', 0)}")
            print(f"  Total mappings: {context.get('mapping_count', 0)}")
            print(f"  Output: {context.get('output_path', 'N/A')}")

        elif checkpoint_type == HumanCheckpoint.SDTM_VALIDATION:
            print(f"SDTM validation results:")
            print(f"  Conformance score: {context.get('conformance_score', 0):.1f}%")
            print(f"  Errors: {context.get('error_count', 0)}")
            print(f"  Warnings: {context.get('warning_count', 0)}")

        elif checkpoint_type == HumanCheckpoint.MAX_ITERATIONS:
            print(f"Maximum iterations ({context.get('max_iterations', 3)}) reached")
            print(f"  Current score: {context.get('conformance_score', 0):.1f}%")
            print(f"  Required score: 95%")
            print(f"  Remaining issues: {context.get('remaining_issues', 'Unknown')}")

        elif checkpoint_type == HumanCheckpoint.CRITICAL_ISSUE:
            print(f"Critical issue detected:")
            print(f"  Issue: {context.get('issue_description', 'Unknown')}")
            print(f"  Severity: CRITICAL")
            print(f"  Affected: {context.get('affected_records', 'Unknown')}")

        elif checkpoint_type == HumanCheckpoint.FINAL_APPROVAL:
            print(f"Final approval required:")
            print(f"  Conformance score: {context.get('conformance_score', 0):.1f}%")
            print(f"  Status: {context.get('status', 'Unknown')}")
            print(f"  Domains: {context.get('domains', [])}")

    def get_pending_checkpoints(self) -> List[CheckpointRecord]:
        """Get all pending checkpoints."""
        return [
            c for c in self.checkpoints
            if c.status == CheckpointStatus.PENDING
        ]

    def get_checkpoint(
        self,
        checkpoint_type: HumanCheckpoint
    ) -> Optional[CheckpointRecord]:
        """Get the most recent checkpoint of a specific type."""
        matching = [
            c for c in self.checkpoints
            if c.checkpoint_type == checkpoint_type
        ]
        return matching[-1] if matching else None

    def approve(
        self,
        checkpoint_type: HumanCheckpoint,
        reviewer: str = "system",
        feedback: Optional[str] = None
    ) -> bool:
        """
        Approve a pending checkpoint.

        Args:
            checkpoint_type: Type of checkpoint to approve
            reviewer: Name of the reviewer
            feedback: Optional feedback

        Returns:
            True if checkpoint was approved
        """
        for i, checkpoint in enumerate(self.checkpoints):
            if (checkpoint.checkpoint_type == checkpoint_type and
                checkpoint.status == CheckpointStatus.PENDING):
                self.checkpoints[i] = CheckpointRecord(
                    checkpoint_type=checkpoint.checkpoint_type,
                    status=CheckpointStatus.APPROVED,
                    created_at=checkpoint.created_at,
                    context=checkpoint.context,
                    decision=ReviewDecision.APPROVE,
                    reviewer=reviewer,
                    reviewed_at=datetime.now().isoformat(),
                    feedback=feedback
                )
                self._save_checkpoints()
                return True
        return False

    def reject(
        self,
        checkpoint_type: HumanCheckpoint,
        reviewer: str = "system",
        feedback: Optional[str] = None
    ) -> bool:
        """
        Reject a pending checkpoint.

        Args:
            checkpoint_type: Type of checkpoint to reject
            reviewer: Name of the reviewer
            feedback: Reason for rejection

        Returns:
            True if checkpoint was rejected
        """
        for i, checkpoint in enumerate(self.checkpoints):
            if (checkpoint.checkpoint_type == checkpoint_type and
                checkpoint.status == CheckpointStatus.PENDING):
                self.checkpoints[i] = CheckpointRecord(
                    checkpoint_type=checkpoint.checkpoint_type,
                    status=CheckpointStatus.REJECTED,
                    created_at=checkpoint.created_at,
                    context=checkpoint.context,
                    decision=ReviewDecision.REJECT,
                    reviewer=reviewer,
                    reviewed_at=datetime.now().isoformat(),
                    feedback=feedback
                )
                self._save_checkpoints()
                return True
        return False

    def modify(
        self,
        checkpoint_type: HumanCheckpoint,
        modifications: Dict[str, Any],
        reviewer: str = "system",
        feedback: Optional[str] = None
    ) -> bool:
        """
        Approve with modifications.

        Args:
            checkpoint_type: Type of checkpoint
            modifications: Requested changes
            reviewer: Name of the reviewer
            feedback: Optional feedback

        Returns:
            True if checkpoint was modified
        """
        for i, checkpoint in enumerate(self.checkpoints):
            if (checkpoint.checkpoint_type == checkpoint_type and
                checkpoint.status == CheckpointStatus.PENDING):
                self.checkpoints[i] = CheckpointRecord(
                    checkpoint_type=checkpoint.checkpoint_type,
                    status=CheckpointStatus.MODIFIED,
                    created_at=checkpoint.created_at,
                    context=checkpoint.context,
                    decision=ReviewDecision.MODIFY,
                    reviewer=reviewer,
                    reviewed_at=datetime.now().isoformat(),
                    feedback=feedback,
                    modifications=modifications
                )
                self._save_checkpoints()
                return True
        return False

    def should_pause(self) -> bool:
        """Check if pipeline should pause for human review."""
        return len(self.get_pending_checkpoints()) > 0

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all checkpoints."""
        return {
            "study_id": self.study_id,
            "total_checkpoints": len(self.checkpoints),
            "pending": len([c for c in self.checkpoints if c.status == CheckpointStatus.PENDING]),
            "approved": len([c for c in self.checkpoints if c.status == CheckpointStatus.APPROVED]),
            "rejected": len([c for c in self.checkpoints if c.status == CheckpointStatus.REJECTED]),
            "modified": len([c for c in self.checkpoints if c.status == CheckpointStatus.MODIFIED]),
            "checkpoints": [c.to_dict() for c in self.checkpoints]
        }


# Convenience functions

def create_checkpoint(
    study_id: str,
    checkpoint_type: HumanCheckpoint,
    context: Dict[str, Any],
    output_dir: str = "."
) -> CheckpointRecord:
    """Create a checkpoint requiring human review."""
    manager = CheckpointManager(study_id, output_dir)
    return manager.create_checkpoint(checkpoint_type, context)


def get_pending_checkpoints(
    study_id: str,
    output_dir: str = "."
) -> List[CheckpointRecord]:
    """Get all pending checkpoints for a study."""
    manager = CheckpointManager(study_id, output_dir)
    return manager.get_pending_checkpoints()


# Checkpoint triggers

def should_checkpoint_raw_validation(
    validation_results: Dict[str, Any],
    error_threshold: int = 0
) -> bool:
    """Check if raw validation results require checkpoint."""
    error_count = sum(
        r.get("error_count", 0)
        for r in validation_results.get("results", [])
    )
    return error_count > error_threshold


def should_checkpoint_conformance(
    conformance_score: float,
    threshold: float = 95.0
) -> bool:
    """Check if conformance score requires checkpoint."""
    return conformance_score < threshold


def should_checkpoint_iteration(
    iteration: int,
    max_iterations: int = 3
) -> bool:
    """Check if max iterations reached."""
    return iteration >= max_iterations


def should_checkpoint_critical(
    issues: List[Dict[str, Any]]
) -> bool:
    """Check if critical issues require checkpoint."""
    return any(
        i.get("severity") == "critical"
        for i in issues
    )

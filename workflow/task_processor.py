"""
Task processor for Personal AI Employee System.

Reads tasks from Needs_Action, analyzes them, creates plans,
and routes to appropriate folders based on HITL classification.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
import yaml

from config import settings
from config.database import log_action
from .hitl import HITLClassifier, HITLDecision, ApprovalStatus

logger = logging.getLogger(__name__)


class TaskProcessor:
    """
    Processes tasks from Needs_Action folder.

    Workflow:
    1. Read task file from Needs_Action
    2. Parse metadata and content
    3. Run HITL classification
    4. Create plan file
    5. Route to Pending_Approval or execute directly
    """

    def __init__(self, classifier: Optional[HITLClassifier] = None):
        """
        Initialize the task processor.

        Args:
            classifier: HITL classifier instance (creates default if None)
        """
        self.classifier = classifier or HITLClassifier()
        self.processed_count = 0

    def process_all(self) -> int:
        """
        Process all tasks in Needs_Action folder.

        Returns:
            Number of tasks processed
        """
        tasks = list(settings.needs_action_path.glob("*.md"))
        processed = 0

        for task_path in tasks:
            try:
                if self.process_task(task_path):
                    processed += 1
            except Exception as e:
                logger.error(f"Error processing {task_path}: {e}")
                log_action(
                    action_type="task_process_error",
                    target=str(task_path),
                    result="failure",
                    error_message=str(e),
                )

        return processed

    def process_task(self, task_path: Path) -> bool:
        """
        Process a single task file.

        Args:
            task_path: Path to the task file

        Returns:
            True if processed successfully
        """
        logger.info(f"Processing task: {task_path.name}")

        # Read and parse task
        content = task_path.read_text(encoding="utf-8")
        metadata, body = self._parse_task(content)

        # Run HITL classification
        decision = self.classifier.classify(body, metadata)

        # Create plan
        plan_path = self._create_plan(task_path, metadata, body, decision)

        # Route based on decision
        if decision.requires_approval:
            self._route_to_pending(task_path, plan_path, decision)
        else:
            self._route_to_auto_approved(task_path, plan_path, decision)

        self.processed_count += 1
        return True

    def _parse_task(self, content: str) -> tuple[dict, str]:
        """
        Parse task file content into metadata and body.

        Args:
            content: Raw file content

        Returns:
            Tuple of (metadata dict, body text)
        """
        metadata = {}
        body = content

        # Check for YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    metadata = yaml.safe_load(parts[1]) or {}
                    body = parts[2].strip()
                except yaml.YAMLError:
                    pass

        return metadata, body

    def _create_plan(
        self,
        task_path: Path,
        metadata: dict,
        body: str,
        decision: HITLDecision,
    ) -> Path:
        """
        Create a plan file for the task.

        Args:
            task_path: Original task file path
            metadata: Task metadata
            body: Task body content
            decision: HITL decision

        Returns:
            Path to created plan file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plan_name = f"{timestamp}_plan_{task_path.stem}.md"
        plan_path = settings.plans_path / plan_name

        # Build plan content
        plan_content = f"""---
task: {task_path.name}
created: {datetime.now().isoformat()}
action_type: {decision.action_type.value}
risk_level: {decision.risk_level}
requires_approval: {decision.requires_approval}
status: {'pending_approval' if decision.requires_approval else 'auto_approved'}
---

# Plan: {metadata.get('title', task_path.stem)}

## Original Task

**Source**: {metadata.get('source', 'Unknown')}
**Priority**: {metadata.get('priority', 'normal')}
**Created**: {metadata.get('created', 'Unknown')}

## HITL Analysis

**Action Type**: {decision.action_type.value}
**Risk Level**: {decision.risk_level.upper()}
**Requires Approval**: {'YES' if decision.requires_approval else 'No'}

### Reasons
{self._format_reasons(decision.reasons)}

## Suggested Action

{decision.suggested_action}

## Task Content Summary

{body[:1000]}{'...' if len(body) > 1000 else ''}

---

## Execution Steps

1. {'AWAIT HUMAN APPROVAL' if decision.requires_approval else 'Auto-approved for execution'}
2. {decision.suggested_action}
3. Log result to audit system
4. Move to Done folder

---

*Generated by AI Employee System at {datetime.now().isoformat()}*
"""

        plan_path.write_text(plan_content, encoding="utf-8")
        logger.info(f"Created plan: {plan_path.name}")

        log_action(
            action_type="plan_created",
            target=str(plan_path),
            parameters={
                "task": task_path.name,
                "action_type": decision.action_type.value,
                "requires_approval": decision.requires_approval,
            },
            result="success",
        )

        return plan_path

    def _format_reasons(self, reasons: list[str]) -> str:
        """Format reasons as markdown list."""
        return "\n".join(f"- {reason}" for reason in reasons)

    def _route_to_pending(
        self,
        task_path: Path,
        plan_path: Path,
        decision: HITLDecision,
    ) -> None:
        """
        Route task and plan to Pending_Approval folder.

        Args:
            task_path: Original task file
            plan_path: Created plan file
            decision: HITL decision
        """
        # Move task to Pending_Approval
        pending_task = settings.pending_approval_path / task_path.name
        shutil.move(str(task_path), str(pending_task))

        # Also copy plan to Pending_Approval for context
        pending_plan = settings.pending_approval_path / plan_path.name
        shutil.copy(str(plan_path), str(pending_plan))

        logger.info(f"Routed to Pending_Approval: {task_path.name}")
        logger.info(f"  Reasons: {', '.join(decision.reasons)}")

        log_action(
            action_type="task_pending_approval",
            target=str(pending_task),
            parameters={
                "reasons": decision.reasons,
                "risk_level": decision.risk_level,
            },
            approval_status="pending",
            result="success",
        )

    def _route_to_auto_approved(
        self,
        task_path: Path,
        plan_path: Path,
        decision: HITLDecision,
    ) -> None:
        """
        Route task to Approved folder (auto-approved).

        Args:
            task_path: Original task file
            plan_path: Created plan file
            decision: HITL decision
        """
        # Move task to Approved
        approved_task = settings.approved_path / task_path.name
        shutil.move(str(task_path), str(approved_task))

        # Also copy plan to Approved
        approved_plan = settings.approved_path / plan_path.name
        shutil.copy(str(plan_path), str(approved_plan))

        logger.info(f"Auto-approved: {task_path.name}")

        log_action(
            action_type="task_auto_approved",
            target=str(approved_task),
            parameters={
                "action_type": decision.action_type.value,
            },
            approval_status="auto_approved",
            result="success",
        )

"""
Approval handler for Personal AI Employee System.

Monitors Pending_Approval folder for human decisions and
processes approved tasks.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from config import settings
from config.database import log_action

logger = logging.getLogger(__name__)


class ApprovalHandler:
    """
    Handles the approval workflow.

    Workflow:
    1. Monitor Pending_Approval for tasks awaiting human review
    2. When human moves file to Approved folder, detect and process
    3. Execute approved tasks
    4. Move completed tasks to Done
    """

    def __init__(self, on_approved: Optional[Callable[[Path], None]] = None):
        """
        Initialize approval handler.

        Args:
            on_approved: Callback function when a task is approved
        """
        self.on_approved = on_approved
        self.pending_tasks: set[str] = set()
        self.processed_approvals: set[str] = set()

    def scan_pending(self) -> list[Path]:
        """
        Scan Pending_Approval folder for tasks.

        Returns:
            List of pending task files
        """
        tasks = list(settings.pending_approval_path.glob("*.md"))
        # Filter out plan files, only return task files
        tasks = [t for t in tasks if not t.name.startswith("20") or "_plan_" not in t.name]

        # Update tracking
        self.pending_tasks = {t.name for t in tasks}

        return tasks

    def scan_approved(self) -> list[Path]:
        """
        Scan Approved folder for newly approved tasks.

        Returns:
            List of approved task files ready for execution
        """
        tasks = list(settings.approved_path.glob("*.md"))
        # Filter out plan files
        tasks = [t for t in tasks if "_plan_" not in t.name]

        # Find new approvals (not yet processed)
        new_approvals = [t for t in tasks if t.name not in self.processed_approvals]

        return new_approvals

    def process_approvals(self) -> int:
        """
        Process all newly approved tasks.

        Returns:
            Number of tasks processed
        """
        approved_tasks = self.scan_approved()
        processed = 0

        for task_path in approved_tasks:
            try:
                self._process_approved_task(task_path)
                processed += 1
            except Exception as e:
                logger.error(f"Error processing approved task {task_path}: {e}")
                log_action(
                    action_type="approval_process_error",
                    target=str(task_path),
                    result="failure",
                    error_message=str(e),
                )

        return processed

    def _process_approved_task(self, task_path: Path) -> None:
        """
        Process a single approved task.

        Args:
            task_path: Path to the approved task file
        """
        logger.info(f"Processing approved task: {task_path.name}")

        # Mark as being processed
        self.processed_approvals.add(task_path.name)

        # Log the approval
        log_action(
            action_type="task_approved",
            target=str(task_path),
            approval_status="approved",
            approved_by="human",
            result="success",
        )

        # Call the approval callback if set
        if self.on_approved:
            try:
                self.on_approved(task_path)
            except Exception as e:
                logger.error(f"Approval callback error: {e}")

        # Move to Done folder
        self._move_to_done(task_path)

    def _move_to_done(self, task_path: Path) -> None:
        """
        Move completed task to Done folder.

        Args:
            task_path: Path to the task file
        """
        # Create completion timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Move task file
        done_path = settings.done_path / f"{timestamp}_completed_{task_path.name}"
        shutil.move(str(task_path), str(done_path))

        # Also move associated plan if exists
        plan_name = None
        for plan_file in settings.approved_path.glob(f"*_plan_*{task_path.stem}*.md"):
            plan_done = settings.done_path / f"{timestamp}_completed_{plan_file.name}"
            shutil.move(str(plan_file), str(plan_done))
            plan_name = plan_file.name

        logger.info(f"Moved to Done: {done_path.name}")

        log_action(
            action_type="task_completed",
            target=str(done_path),
            parameters={"plan": plan_name},
            result="success",
        )

    def approve_task(self, task_name: str) -> bool:
        """
        Programmatically approve a task (move from Pending to Approved).

        Args:
            task_name: Name of the task file

        Returns:
            True if approved successfully
        """
        pending_path = settings.pending_approval_path / task_name

        if not pending_path.exists():
            logger.error(f"Task not found in Pending_Approval: {task_name}")
            return False

        # Move to Approved
        approved_path = settings.approved_path / task_name
        shutil.move(str(pending_path), str(approved_path))

        # Also move associated plan
        for plan_file in settings.pending_approval_path.glob(f"*_plan_*{pending_path.stem}*.md"):
            plan_approved = settings.approved_path / plan_file.name
            shutil.move(str(plan_file), str(plan_approved))

        logger.info(f"Task approved: {task_name}")
        return True

    def reject_task(self, task_name: str, reason: str = "") -> bool:
        """
        Reject a task (move to Done with rejected status).

        Args:
            task_name: Name of the task file
            reason: Reason for rejection

        Returns:
            True if rejected successfully
        """
        pending_path = settings.pending_approval_path / task_name

        if not pending_path.exists():
            logger.error(f"Task not found in Pending_Approval: {task_name}")
            return False

        # Add rejection note to file
        content = pending_path.read_text(encoding="utf-8")
        rejection_note = f"""

---

## REJECTED

**Date**: {datetime.now().isoformat()}
**Reason**: {reason or 'No reason provided'}

"""
        pending_path.write_text(content + rejection_note, encoding="utf-8")

        # Move to Done with rejected prefix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        done_path = settings.done_path / f"{timestamp}_REJECTED_{task_name}"
        shutil.move(str(pending_path), str(done_path))

        # Also move associated plan
        for plan_file in settings.pending_approval_path.glob(f"*_plan_*{pending_path.stem}*.md"):
            plan_done = settings.done_path / f"{timestamp}_REJECTED_{plan_file.name}"
            shutil.move(str(plan_file), str(plan_done))

        log_action(
            action_type="task_rejected",
            target=str(done_path),
            parameters={"reason": reason},
            approval_status="rejected",
            result="success",
        )

        logger.info(f"Task rejected: {task_name}")
        return True

    def get_pending_summary(self) -> dict:
        """
        Get summary of pending approvals.

        Returns:
            Summary dict with counts and task list
        """
        pending = self.scan_pending()
        approved = self.scan_approved()

        return {
            "pending_count": len(pending),
            "approved_count": len(approved),
            "pending_tasks": [t.name for t in pending],
            "approved_tasks": [t.name for t in approved],
        }

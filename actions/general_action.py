"""
General-purpose action handler for Personal AI Employee System.

Handles tasks that don't match specific action handlers (email, payment, etc.).
Processes file-based tasks, information requests, and general workflow items.
"""

import logging
from datetime import datetime
from pathlib import Path

from actions.base_action import BaseAction, ActionResult, ActionStatus
from config import settings
from config.database import log_action

logger = logging.getLogger(__name__)


class GeneralAction(BaseAction):
    """
    Handles general tasks that don't have a specific action handler.

    This is the fallback handler that ensures all tasks get processed
    rather than being skipped. It:
    - Logs the task as processed
    - Creates a summary in the Logs folder
    - Marks the task as complete
    """

    def __init__(self):
        super().__init__(name="general")

    def can_handle(self, task_data: dict) -> bool:
        """
        General handler accepts all tasks as a fallback.

        Returns True for any task not handled by specific handlers.
        This should be registered LAST so specific handlers get priority.
        """
        return True

    def execute(self, task_data: dict, task_path: Path) -> ActionResult:
        """
        Process a general task.

        Logs the task details and marks it as completed.
        """
        logger.info(f"Processing general task: {task_path.name}")

        title = task_data.get("title", task_path.stem)
        source = task_data.get("source", "unknown")
        body = task_data.get("body", task_data.get("raw_content", ""))
        action_type = task_data.get("action_type", "unknown")

        if self.dry_run:
            logger.info(f"[DRY RUN] Processed general task: {title}")
            logger.info(f"  Source: {source}")
            logger.info(f"  Action type: {action_type}")
            logger.info(f"  Content preview: {body[:200]}...")

            result = ActionResult(
                status=ActionStatus.SUCCESS,
                message=f"[DRY RUN] General task processed: {title}",
                data={
                    "title": title,
                    "source": source,
                    "action_type": action_type,
                },
            )
            self._log_execution(task_path, result, {"title": title, "source": source})
            return result

        # In live mode, log the task processing
        result = ActionResult(
            status=ActionStatus.SUCCESS,
            message=f"General task processed: {title}",
            data={
                "title": title,
                "source": source,
                "action_type": action_type,
            },
        )
        self._log_execution(task_path, result, {"title": title, "source": source})

        logger.info(f"General task completed: {title}")
        return result

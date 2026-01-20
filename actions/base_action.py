"""
Base action class for Personal AI Employee System.

All action executors inherit from this base class.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from config import settings
from config.database import log_action

logger = logging.getLogger(__name__)


class ActionStatus(Enum):
    """Status of an action execution."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"  # For dry run


@dataclass
class ActionResult:
    """Result of an action execution."""
    status: ActionStatus
    message: str
    data: Optional[dict] = None
    error: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            "status": self.status.value,
            "message": self.message,
            "data": self.data,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


class BaseAction(ABC):
    """
    Base class for all action executors.

    Actions are responsible for:
    - Parsing approved task files
    - Executing the requested action (email, payment, etc.)
    - Logging results to database
    - Handling errors gracefully
    """

    def __init__(self, name: str):
        self.name = name
        self.dry_run = settings.dry_run

    @abstractmethod
    def can_handle(self, task_data: dict) -> bool:
        """
        Check if this action can handle the given task.

        Args:
            task_data: Parsed task data from markdown file

        Returns:
            True if this action can execute the task
        """
        pass

    @abstractmethod
    def execute(self, task_data: dict, task_path: Path) -> ActionResult:
        """
        Execute the action.

        Args:
            task_data: Parsed task data from markdown file
            task_path: Path to the task file

        Returns:
            ActionResult with status and details
        """
        pass

    def _log_execution(
        self,
        task_path: Path,
        result: ActionResult,
        parameters: Optional[dict] = None,
    ) -> None:
        """Log action execution to database."""
        log_action(
            action_type=f"action_{self.name}",
            target=str(task_path),
            parameters=parameters or {},
            result=result.status.value,
            approval_status="executed" if result.status == ActionStatus.SUCCESS else "failed",
        )

    def _parse_task_file(self, task_path: Path) -> dict:
        """
        Parse a task markdown file.

        Expected format:
        ```
        ---
        type: email
        priority: high
        requires_approval: true
        ---

        # Task Title

        Content here...
        ```
        """
        content = task_path.read_text(encoding="utf-8")
        data = {
            "raw_content": content,
            "path": task_path,
            "filename": task_path.name,
        }

        # Parse YAML frontmatter if present
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                import yaml
                try:
                    frontmatter = yaml.safe_load(parts[1])
                    if frontmatter:
                        data.update(frontmatter)
                    data["body"] = parts[2].strip()
                except Exception as e:
                    logger.warning(f"Failed to parse frontmatter: {e}")
                    data["body"] = content
        else:
            data["body"] = content

        return data

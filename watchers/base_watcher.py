"""
Base watcher class for Personal AI Employee System.

All watchers inherit from this abstract class.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import settings
from config.database import log_action

logger = logging.getLogger(__name__)


class BaseWatcher(ABC):
    """Abstract base class for all watchers."""

    def __init__(self, name: str):
        """
        Initialize the watcher.

        Args:
            name: Human-readable name for this watcher
        """
        self.name = name
        self.is_running = False
        self.last_check: Optional[datetime] = None
        self.items_processed = 0

    @abstractmethod
    def start(self) -> None:
        """Start the watcher. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop the watcher. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def check(self) -> list[dict]:
        """
        Check for new items.

        Returns:
            List of new items found (format depends on watcher type)
        """
        pass

    def create_task_file(
        self,
        title: str,
        content: str,
        source: str,
        priority: str = "normal",
        metadata: Optional[dict] = None,
    ) -> Path:
        """
        Create a task file in the Needs_Action folder.

        Args:
            title: Task title (used for filename)
            content: Task content/description
            source: Where this task came from (e.g., 'gmail', 'filesystem')
            priority: Task priority ('high', 'normal', 'low')
            metadata: Additional metadata to include

        Returns:
            Path to the created task file
        """
        # Generate safe filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c if c.isalnum() or c in "-_ " else "_" for c in title)
        safe_title = safe_title[:50].strip()
        filename = f"{timestamp}_{safe_title}.md"

        # Build task content (single-quote values to handle colons/backslashes in YAML)
        safe_yaml_title = title.replace("'", "''")
        safe_yaml_source = source.replace("'", "''")
        task_content = f"""---
title: '{safe_yaml_title}'
source: '{safe_yaml_source}'
priority: {priority}
created: '{datetime.now().isoformat()}'
watcher: {self.name}
status: pending
---

# {title}

## Source
{source}

## Priority
{priority}

## Content

{content}

## Metadata
"""
        if metadata:
            for key, value in metadata.items():
                task_content += f"- **{key}**: {value}\n"
        else:
            task_content += "- None\n"

        task_content += """
---

## Action Required

*Claude Code will analyze this task and create a plan.*
"""

        # Write to Needs_Action folder
        task_path = settings.needs_action_path / filename
        task_path.write_text(task_content, encoding="utf-8")

        # Log the action
        log_action(
            action_type="task_created",
            target=str(task_path),
            parameters={
                "title": title,
                "source": source,
                "priority": priority,
                "watcher": self.name,
            },
            result="success",
        )

        logger.info(f"Created task: {task_path}")
        self.items_processed += 1

        return task_path

    def get_status(self) -> dict:
        """
        Get watcher status.

        Returns:
            Status dictionary
        """
        return {
            "name": self.name,
            "is_running": self.is_running,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "items_processed": self.items_processed,
        }

    def log_error(self, error: Exception, context: str = "") -> None:
        """
        Log an error from this watcher.

        Args:
            error: The exception that occurred
            context: Additional context about what was happening
        """
        error_msg = f"{context}: {str(error)}" if context else str(error)
        logger.error(f"[{self.name}] {error_msg}")

        log_action(
            action_type="watcher_error",
            target=self.name,
            parameters={"context": context},
            result="failure",
            error_message=str(error),
        )

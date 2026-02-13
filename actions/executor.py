"""
Action executor for Personal AI Employee System.

Coordinates execution of approved tasks using registered action handlers.
"""

import logging
from pathlib import Path
from typing import Optional

from actions.base_action import BaseAction, ActionResult, ActionStatus
from actions.email_action import EmailAction, EmailDraftAction
from actions.general_action import GeneralAction
from actions.linkedin_action import LinkedInDraftAction
from actions.social_action import FacebookDraftAction, InstagramDraftAction, TwitterDraftAction
from actions.odoo_action import OdooInvoiceAction, OdooExpenseAction
from config.database import log_action

logger = logging.getLogger(__name__)


class ActionExecutor:
    """
    Executes approved tasks using appropriate action handlers.

    The executor:
    1. Receives approved task files
    2. Parses task data
    3. Finds appropriate action handler
    4. Executes the action
    5. Reports results
    """

    def __init__(self):
        self.actions: list[BaseAction] = []
        self._register_default_actions()

    def _register_default_actions(self) -> None:
        """Register built-in action handlers."""
        # Email actions (specific handlers first)
        self.register(EmailAction())
        self.register(EmailDraftAction())

        # Social media actions
        self.register(LinkedInDraftAction())
        self.register(FacebookDraftAction())
        self.register(InstagramDraftAction())
        self.register(TwitterDraftAction())

        # Odoo accounting actions
        self.register(OdooInvoiceAction())
        self.register(OdooExpenseAction())

        # General fallback handler (MUST be last - catches everything)
        self.register(GeneralAction())

        logger.info(f"Action executor initialized with {len(self.actions)} action handlers")

    def register(self, action: BaseAction) -> None:
        """Register an action handler."""
        self.actions.append(action)
        logger.debug(f"Registered action: {action.name}")

    def execute(self, task_path: Path) -> Optional[ActionResult]:
        """
        Execute an approved task.

        Args:
            task_path: Path to the approved task file

        Returns:
            ActionResult if executed, None if no handler found
        """
        if not task_path.exists():
            logger.error(f"Task file not found: {task_path}")
            return ActionResult(
                status=ActionStatus.FAILED,
                message="Task file not found",
                error=f"File does not exist: {task_path}",
            )

        # Parse task data
        task_data = self._parse_task(task_path)

        # Find appropriate action handler
        handler = self._find_handler(task_data)

        if not handler:
            logger.warning(f"No action handler for task: {task_path.name}")
            log_action(
                action_type="action_no_handler",
                target=str(task_path),
                parameters={"type": task_data.get("type", "unknown")},
                result="skipped",
            )
            return ActionResult(
                status=ActionStatus.SKIPPED,
                message="No action handler available for this task type",
                data={"task_type": task_data.get("type")},
            )

        # Execute action
        logger.info(f"Executing action '{handler.name}' for: {task_path.name}")
        try:
            result = handler.execute(task_data, task_path)
            return result
        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            return ActionResult(
                status=ActionStatus.FAILED,
                message=f"Action execution failed: {str(e)}",
                error=str(e),
            )

    def _find_handler(self, task_data: dict) -> Optional[BaseAction]:
        """Find action handler that can process the task."""
        for action in self.actions:
            if action.can_handle(task_data):
                return action
        return None

    def _parse_task(self, task_path: Path) -> dict:
        """Parse task file into data dictionary."""
        content = task_path.read_text(encoding="utf-8")
        data = {
            "raw_content": content,
            "path": task_path,
            "filename": task_path.name,
        }

        # Parse YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                import yaml
                try:
                    frontmatter = yaml.safe_load(parts[1])
                    if frontmatter:
                        data.update(frontmatter)
                except Exception as e:
                    logger.warning(f"Failed to parse frontmatter via YAML: {e}")
                    # Fallback: extract key-value pairs manually
                    self._parse_frontmatter_fallback(parts[1], data)
                data["body"] = parts[2].strip()
        else:
            data["body"] = content

        return data

    def _parse_frontmatter_fallback(self, frontmatter_text: str, data: dict) -> None:
        """Extract key-value pairs from frontmatter when YAML parsing fails."""
        import re
        for line in frontmatter_text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # Match "key: value" but only split on the FIRST colon
            match = re.match(r'^(\w+):\s*(.+)$', line)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip().strip('"').strip("'")
                data[key] = value

    def get_available_actions(self) -> list[str]:
        """Get list of registered action names."""
        return [a.name for a in self.actions]

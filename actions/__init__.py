"""
Actions module for Personal AI Employee System.

Actions are executors that perform approved tasks.
"""

from actions.base_action import BaseAction, ActionResult, ActionStatus
from actions.email_action import EmailAction, EmailDraftAction
from actions.executor import ActionExecutor

__all__ = [
    "BaseAction",
    "ActionResult",
    "ActionStatus",
    "EmailAction",
    "EmailDraftAction",
    "ActionExecutor",
]

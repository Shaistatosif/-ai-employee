"""
Actions module for Personal AI Employee System.

Actions are executors that perform approved tasks.
"""

from actions.base_action import BaseAction, ActionResult, ActionStatus
from actions.email_action import EmailAction, EmailDraftAction
from actions.general_action import GeneralAction
from actions.linkedin_action import LinkedInDraftAction
from actions.social_action import FacebookDraftAction, InstagramDraftAction, TwitterDraftAction
from actions.odoo_action import OdooInvoiceAction, OdooExpenseAction
from actions.executor import ActionExecutor

__all__ = [
    "BaseAction",
    "ActionResult",
    "ActionStatus",
    "EmailAction",
    "EmailDraftAction",
    "GeneralAction",
    "LinkedInDraftAction",
    "FacebookDraftAction",
    "InstagramDraftAction",
    "TwitterDraftAction",
    "OdooInvoiceAction",
    "OdooExpenseAction",
    "ActionExecutor",
]

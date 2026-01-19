"""
Human-in-the-Loop (HITL) classification for Personal AI Employee System.

Determines whether tasks require human approval based on content analysis.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of actions that can be taken on a task."""
    REPLY_EMAIL = "reply_email"
    SEND_EMAIL = "send_email"
    CREATE_FILE = "create_file"
    DELETE_FILE = "delete_file"
    PAYMENT = "payment"
    SOCIAL_POST = "social_post"
    SOCIAL_REPLY = "social_reply"
    SCHEDULE = "schedule"
    ARCHIVE = "archive"
    INFORMATION = "information"
    UNKNOWN = "unknown"


class ApprovalStatus(Enum):
    """Approval status for tasks."""
    PENDING = "pending"
    AUTO_APPROVED = "auto_approved"
    REQUIRES_APPROVAL = "requires_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class HITLDecision:
    """Result of HITL classification."""
    requires_approval: bool
    reasons: list[str]
    action_type: ActionType
    risk_level: str  # low, medium, high
    suggested_action: str


class HITLClassifier:
    """
    Classifies tasks to determine if human approval is required.

    Based on constitution principles:
    - Payments > $50: requires approval
    - Emails to new recipients: requires approval
    - Social media posts/replies: requires approval
    - File deletions: requires approval
    - Any irreversible action: requires approval
    """

    # Keywords that indicate sensitive content
    SENSITIVE_KEYWORDS = {
        "payment": ["payment", "pay", "transfer", "wire", "invoice", "bill", "charge"],
        "financial": ["bank", "credit card", "account", "money", "dollar", "$", "cost"],
        "personal": ["password", "ssn", "social security", "confidential", "private"],
        "legal": ["contract", "agreement", "legal", "lawsuit", "attorney"],
        "medical": ["medical", "health", "doctor", "prescription", "diagnosis"],
    }

    # Keywords that indicate safe actions
    SAFE_KEYWORDS = ["read", "review", "check", "analyze", "summarize", "draft", "list"]

    # Patterns for detecting amounts
    AMOUNT_PATTERN = re.compile(r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)')

    def __init__(self, known_contacts: Optional[list[str]] = None):
        """
        Initialize the classifier.

        Args:
            known_contacts: List of known email addresses (auto-approve replies)
        """
        self.known_contacts = set(known_contacts or [])

    def classify(self, task_content: str, metadata: Optional[dict] = None) -> HITLDecision:
        """
        Classify a task to determine if human approval is required.

        Args:
            task_content: Full text content of the task
            metadata: Optional metadata (source, type, etc.)

        Returns:
            HITLDecision with approval requirements
        """
        metadata = metadata or {}
        content_lower = task_content.lower()
        reasons = []
        risk_level = "low"

        # Detect action type
        action_type = self._detect_action_type(content_lower, metadata)

        # Check for payment amounts
        amounts = self._extract_amounts(task_content)
        if amounts:
            max_amount = max(amounts)
            if max_amount > 50:
                reasons.append(f"Payment amount ${max_amount:.2f} exceeds $50 threshold")
                risk_level = "high"
            elif max_amount > 0:
                reasons.append(f"Contains payment amount ${max_amount:.2f}")
                risk_level = "medium"

        # Check for sensitive keywords
        for category, keywords in self.SENSITIVE_KEYWORDS.items():
            if any(kw in content_lower for kw in keywords):
                reasons.append(f"Contains {category}-related content")
                if category in ["payment", "financial", "legal"]:
                    risk_level = "high" if risk_level != "high" else risk_level
                elif risk_level == "low":
                    risk_level = "medium"

        # Check email recipient
        if action_type in [ActionType.SEND_EMAIL, ActionType.REPLY_EMAIL]:
            recipient = metadata.get("to") or metadata.get("from", "")
            if recipient and recipient not in self.known_contacts:
                reasons.append(f"Email to unknown recipient: {recipient}")
                if risk_level == "low":
                    risk_level = "medium"

        # Check for file operations
        if action_type == ActionType.DELETE_FILE:
            reasons.append("File deletion is irreversible")
            risk_level = "high"

        # Check for social media
        if action_type in [ActionType.SOCIAL_POST, ActionType.SOCIAL_REPLY]:
            reasons.append("Social media actions are public and visible")
            risk_level = "medium" if risk_level == "low" else risk_level

        # Determine if approval is required
        requires_approval = len(reasons) > 0 or risk_level in ["medium", "high"]

        # Generate suggested action
        suggested_action = self._suggest_action(action_type, requires_approval, content_lower)

        return HITLDecision(
            requires_approval=requires_approval,
            reasons=reasons if reasons else ["Standard processing - no sensitive content detected"],
            action_type=action_type,
            risk_level=risk_level,
            suggested_action=suggested_action,
        )

    def _detect_action_type(self, content: str, metadata: dict) -> ActionType:
        """Detect the type of action requested."""
        source = metadata.get("source", "").lower()

        # Email-related
        if "gmail" in source or "email" in source:
            if "reply" in content or "respond" in content:
                return ActionType.REPLY_EMAIL
            elif "send" in content or "compose" in content:
                return ActionType.SEND_EMAIL
            return ActionType.INFORMATION

        # File operations
        if "delete" in content or "remove" in content:
            return ActionType.DELETE_FILE
        if "create" in content or "write" in content:
            return ActionType.CREATE_FILE

        # Payment
        if any(kw in content for kw in ["pay", "payment", "transfer", "invoice"]):
            return ActionType.PAYMENT

        # Social media
        if any(kw in content for kw in ["post", "tweet", "linkedin", "facebook"]):
            if "reply" in content or "comment" in content:
                return ActionType.SOCIAL_REPLY
            return ActionType.SOCIAL_POST

        # Scheduling
        if any(kw in content for kw in ["schedule", "calendar", "meeting", "appointment"]):
            return ActionType.SCHEDULE

        # Archive/organize
        if any(kw in content for kw in ["archive", "organize", "file", "categorize"]):
            return ActionType.ARCHIVE

        return ActionType.UNKNOWN

    def _extract_amounts(self, content: str) -> list[float]:
        """Extract dollar amounts from content."""
        amounts = []
        for match in self.AMOUNT_PATTERN.finditer(content):
            try:
                amount_str = match.group(1).replace(",", "")
                amounts.append(float(amount_str))
            except ValueError:
                continue
        return amounts

    def _suggest_action(self, action_type: ActionType, requires_approval: bool, content: str) -> str:
        """Generate a suggested action based on classification."""
        if requires_approval:
            return "Move to Pending_Approval for human review"

        suggestions = {
            ActionType.REPLY_EMAIL: "Draft reply and auto-send to known contact",
            ActionType.INFORMATION: "Categorize and archive",
            ActionType.ARCHIVE: "Move to appropriate folder",
            ActionType.SCHEDULE: "Add to calendar",
            ActionType.CREATE_FILE: "Create file in vault",
        }

        return suggestions.get(action_type, "Process and move to Done")

    def add_known_contact(self, email: str) -> None:
        """Add an email to the known contacts list."""
        self.known_contacts.add(email.lower())

    def remove_known_contact(self, email: str) -> None:
        """Remove an email from the known contacts list."""
        self.known_contacts.discard(email.lower())

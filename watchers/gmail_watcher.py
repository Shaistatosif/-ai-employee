"""
Gmail watcher for Personal AI Employee System.

Monitors Gmail inbox for new emails and creates tasks in the vault.
Requires Gmail API credentials configured in .env
"""

import base64
import logging
import os
import pickle
import time
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Optional

# Google API imports - optional, may not be installed
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    Request = None
    Credentials = None
    InstalledAppFlow = None
    build = None
    HttpError = Exception

from config import settings
from config.database import log_action
from .base_watcher import BaseWatcher

logger = logging.getLogger(__name__)

# Gmail API scopes - read-only for safety
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailWatcher(BaseWatcher):
    """
    Watches Gmail inbox for new emails.

    Creates tasks in Needs_Action folder for each new email.
    Respects HITL principles - only reads, never sends.

    Usage:
        watcher = GmailWatcher()
        watcher.start()  # or watcher.check() for one-time check
    """

    def __init__(
        self,
        check_interval: int = 60,
        max_results: int = 10,
        label_ids: Optional[list[str]] = None,
    ):
        """
        Initialize Gmail watcher.

        Args:
            check_interval: Seconds between checks
            max_results: Max emails to fetch per check
            label_ids: Gmail labels to monitor (default: INBOX, UNREAD)
        """
        super().__init__(name="Gmail Watcher")
        self.check_interval = check_interval
        self.max_results = max_results
        self.label_ids = label_ids or ["INBOX", "UNREAD"]
        self.service = None
        self.credentials: Optional[Credentials] = None
        self.processed_ids: set[str] = set()
        self._token_path = Path("token.pickle")
        self._credentials_path = Path("credentials.json")

    def _get_credentials(self) -> Optional[Credentials]:
        """Get or refresh Gmail API credentials."""
        creds = None

        # Load existing token
        if self._token_path.exists():
            with open(self._token_path, "rb") as token:
                creds = pickle.load(token)

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {e}")
                    creds = None

            if not creds:
                if not self._credentials_path.exists():
                    logger.error(
                        f"credentials.json not found. "
                        f"Download from Google Cloud Console and place at: {self._credentials_path.absolute()}"
                    )
                    return None

                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self._credentials_path), SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    logger.error(f"Failed to get credentials: {e}")
                    return None

            # Save token for future use
            with open(self._token_path, "wb") as token:
                pickle.dump(creds, token)

        return creds

    def _build_service(self) -> bool:
        """Build Gmail API service."""
        self.credentials = self._get_credentials()
        if not self.credentials:
            return False

        try:
            self.service = build("gmail", "v1", credentials=self.credentials)
            logger.info("Gmail API service initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to build Gmail service: {e}")
            return False

    def start(self) -> None:
        """Start watching Gmail (blocking)."""
        if not GOOGLE_API_AVAILABLE:
            logger.error("Google API libraries not installed. Run: pip install google-api-python-client google-auth-oauthlib")
            return

        if self.is_running:
            logger.warning(f"{self.name} is already running")
            return

        if not self._build_service():
            logger.error("Failed to initialize Gmail service. Check credentials.")
            return

        self.is_running = True
        log_action(
            action_type="watcher_started",
            target="gmail",
            parameters={"labels": self.label_ids, "interval": self.check_interval},
            result="success",
        )

        logger.info(f"{self.name} started (interval: {self.check_interval}s)")

        try:
            while self.is_running:
                self.check()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop watching Gmail."""
        if not self.is_running:
            return

        self.is_running = False
        log_action(
            action_type="watcher_stopped",
            target="gmail",
            result="success",
        )
        logger.info(f"{self.name} stopped")

    def check(self) -> list[dict]:
        """
        Check for new emails.

        Returns:
            List of new email metadata dicts
        """
        self.last_check = datetime.now()

        if not self.service:
            if not self._build_service():
                return []

        new_emails = []

        try:
            # Get list of messages
            results = (
                self.service.users()
                .messages()
                .list(
                    userId="me",
                    labelIds=self.label_ids,
                    maxResults=self.max_results,
                )
                .execute()
            )

            messages = results.get("messages", [])

            for msg_info in messages:
                msg_id = msg_info["id"]

                # Skip already processed
                if msg_id in self.processed_ids:
                    continue

                # Get full message details
                email_data = self._get_email_details(msg_id)
                if email_data:
                    new_emails.append(email_data)
                    self._create_email_task(email_data)
                    self.processed_ids.add(msg_id)

            if new_emails:
                logger.info(f"Found {len(new_emails)} new email(s)")

        except HttpError as e:
            self.log_error(e, "Gmail API error")
        except Exception as e:
            self.log_error(e, "Error checking Gmail")

        return new_emails

    def _get_email_details(self, msg_id: str) -> Optional[dict]:
        """
        Get detailed email information.

        Args:
            msg_id: Gmail message ID

        Returns:
            Email details dict or None
        """
        try:
            message = (
                self.service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )

            headers = message.get("payload", {}).get("headers", [])

            def get_header(name: str) -> str:
                for h in headers:
                    if h["name"].lower() == name.lower():
                        return h["value"]
                return ""

            # Extract body (prefer plain text)
            body = self._extract_body(message.get("payload", {}))

            # Parse date
            date_str = get_header("Date")
            try:
                email_date = parsedate_to_datetime(date_str) if date_str else datetime.now()
            except Exception:
                email_date = datetime.now()

            return {
                "id": msg_id,
                "from": get_header("From"),
                "to": get_header("To"),
                "subject": get_header("Subject") or "(No Subject)",
                "date": email_date,
                "snippet": message.get("snippet", ""),
                "body": body[:5000],  # Limit body size
                "labels": message.get("labelIds", []),
                "has_attachments": self._has_attachments(message.get("payload", {})),
            }

        except Exception as e:
            logger.error(f"Failed to get email details for {msg_id}: {e}")
            return None

    def _extract_body(self, payload: dict) -> str:
        """Extract email body text."""
        body = ""

        if "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
        elif "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")
                if mime_type == "text/plain" and "data" in part.get("body", {}):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                    break
                elif "parts" in part:
                    body = self._extract_body(part)
                    if body:
                        break

        return body

    def _has_attachments(self, payload: dict) -> bool:
        """Check if email has attachments."""
        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("filename"):
                    return True
                if "parts" in part:
                    if self._has_attachments(part):
                        return True
        return False

    def _create_email_task(self, email_data: dict) -> None:
        """
        Create a task file for the email.

        Args:
            email_data: Email details dict
        """
        # Determine priority based on content
        priority = self._determine_priority(email_data)

        # Check if HITL is required
        hitl_required = self._check_hitl_required(email_data)

        content = f"""## Email Details

**From**: {email_data['from']}
**To**: {email_data['to']}
**Subject**: {email_data['subject']}
**Date**: {email_data['date'].isoformat()}
**Has Attachments**: {'Yes' if email_data['has_attachments'] else 'No'}

## Preview

{email_data['snippet']}

## Full Content

{email_data['body'][:3000]}
{'... [truncated]' if len(email_data['body']) > 3000 else ''}

## Analysis Required

1. Categorize this email (URGENT/HIGH/NORMAL/LOW/SPAM)
2. Determine action needed (REPLY/FYI/ACTION/ARCHIVE)
3. If reply needed, draft a response
4. Check HITL requirements below

## HITL Status

**Requires Approval**: {'YES' if hitl_required else 'No'}
**Reason**: {self._get_hitl_reason(email_data) if hitl_required else 'Known contact, standard processing'}
"""

        self.create_task_file(
            title=f"Email: {email_data['subject'][:40]}",
            content=content,
            source=f"Gmail: {email_data['from']}",
            priority=priority,
            metadata={
                "gmail_id": email_data["id"],
                "from": email_data["from"],
                "subject": email_data["subject"],
                "date": email_data["date"].isoformat(),
                "hitl_required": hitl_required,
            },
        )

    def _determine_priority(self, email_data: dict) -> str:
        """Determine email priority based on content."""
        subject_lower = email_data["subject"].lower()
        body_lower = email_data["body"].lower()

        # Check for urgent keywords
        urgent_keywords = ["urgent", "asap", "emergency", "critical", "immediately"]
        if any(kw in subject_lower or kw in body_lower for kw in urgent_keywords):
            return "high"

        # Check for important labels
        if "IMPORTANT" in email_data["labels"]:
            return "high"

        # Check for invoice/payment keywords
        money_keywords = ["invoice", "payment", "receipt", "bill", "due"]
        if any(kw in subject_lower for kw in money_keywords):
            return "high"

        return "normal"

    def _check_hitl_required(self, email_data: dict) -> bool:
        """Check if human-in-the-loop approval is required."""
        # TODO: Load known contacts from Company_Handbook.md
        # For now, mark all new senders as requiring HITL

        # Check for sensitive content
        sensitive_keywords = ["password", "credit card", "bank", "wire transfer", "confidential"]
        content = (email_data["subject"] + " " + email_data["body"]).lower()

        if any(kw in content for kw in sensitive_keywords):
            return True

        return False

    def _get_hitl_reason(self, email_data: dict) -> str:
        """Get reason why HITL is required."""
        reasons = []

        content = (email_data["subject"] + " " + email_data["body"]).lower()

        if "password" in content or "credit card" in content:
            reasons.append("Contains sensitive information")
        if "wire transfer" in content or "bank" in content:
            reasons.append("Financial content detected")
        if email_data["has_attachments"]:
            reasons.append("Has attachments")

        return "; ".join(reasons) if reasons else "New/unknown sender"


def run_gmail_watcher(
    interval: int = 60,
    max_results: int = 10,
) -> None:
    """
    Run the Gmail watcher (blocking).

    Args:
        interval: Check interval in seconds
        max_results: Max emails per check
    """
    import signal
    import sys

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    settings.ensure_directories()

    watcher = GmailWatcher(check_interval=interval, max_results=max_results)

    def signal_handler(sig, frame):
        logger.info("Shutting down...")
        watcher.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    watcher.start()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gmail Watcher")
    parser.add_argument("--interval", type=int, default=60, help="Check interval (seconds)")
    parser.add_argument("--max", type=int, default=10, help="Max emails per check")

    args = parser.parse_args()
    run_gmail_watcher(interval=args.interval, max_results=args.max)

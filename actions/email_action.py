"""
Email action executor for Personal AI Employee System.

Sends emails via Gmail API when email tasks are approved.
"""

import base64
import logging
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from actions.base_action import BaseAction, ActionResult, ActionStatus
from config import settings

logger = logging.getLogger(__name__)

# Try to import Google API libraries
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    import pickle
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    logger.warning("Google API libraries not available. Email sending disabled.")


class EmailAction(BaseAction):
    """
    Executes email sending tasks via Gmail API.

    Parses approved email tasks and sends them using the
    authenticated Gmail account.
    """

    # Gmail API scope for sending
    SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

    def __init__(self):
        super().__init__(name="email_send")
        self._service = None
        self._credentials_path = Path("credentials.json")
        self._token_path = Path("token_send.pickle")  # Separate token for sending

    def can_handle(self, task_data: dict) -> bool:
        """
        Check if this is an email task.

        Handles tasks with:
        - type: email or email_send or email_reply
        - Contains "To:", "Subject:" in body
        """
        task_type = task_data.get("type", "").lower()
        if task_type in ("email", "email_send", "email_reply", "send_email"):
            return True

        # Check body for email markers
        body = task_data.get("body", "")
        if "To:" in body and "Subject:" in body:
            return True

        return False

    def execute(self, task_data: dict, task_path: Path) -> ActionResult:
        """
        Send an email based on approved task data.

        Expects task_data to contain:
        - to: recipient email address
        - subject: email subject
        - body or message: email content
        - cc (optional): CC recipients
        - reply_to_id (optional): thread ID for replies
        """
        logger.info(f"Executing email action for: {task_path.name}")

        # Parse email details from task
        email_data = self._extract_email_data(task_data)

        if not email_data.get("to"):
            return ActionResult(
                status=ActionStatus.FAILED,
                message="Missing recipient (to) field",
                error="Email task missing required 'to' field",
            )

        if not email_data.get("subject"):
            return ActionResult(
                status=ActionStatus.FAILED,
                message="Missing subject field",
                error="Email task missing required 'subject' field",
            )

        # Dry run check
        if self.dry_run:
            logger.info(f"[DRY RUN] Would send email:")
            logger.info(f"  To: {email_data['to']}")
            logger.info(f"  Subject: {email_data['subject']}")
            logger.info(f"  Body: {email_data['body'][:100]}...")

            result = ActionResult(
                status=ActionStatus.SKIPPED,
                message=f"[DRY RUN] Email to {email_data['to']} prepared but not sent",
                data=email_data,
            )
            self._log_execution(task_path, result, email_data)
            return result

        # Check if Google API is available
        if not GOOGLE_API_AVAILABLE:
            return ActionResult(
                status=ActionStatus.FAILED,
                message="Google API not available",
                error="Install google-api-python-client to enable email sending",
            )

        # Initialize Gmail service
        if not self._init_gmail_service():
            return ActionResult(
                status=ActionStatus.FAILED,
                message="Failed to initialize Gmail service",
                error="Could not authenticate with Gmail API",
            )

        # Send the email
        try:
            message_id = self._send_email(
                to=email_data["to"],
                subject=email_data["subject"],
                body=email_data["body"],
                cc=email_data.get("cc"),
                thread_id=email_data.get("reply_to_id"),
            )

            result = ActionResult(
                status=ActionStatus.SUCCESS,
                message=f"Email sent successfully to {email_data['to']}",
                data={"message_id": message_id, **email_data},
            )
            self._log_execution(task_path, result, email_data)
            logger.info(f"Email sent: {message_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            result = ActionResult(
                status=ActionStatus.FAILED,
                message=f"Failed to send email: {str(e)}",
                error=str(e),
            )
            self._log_execution(task_path, result, email_data)
            return result

    def _extract_email_data(self, task_data: dict) -> dict:
        """
        Extract email fields from task data.

        Handles both structured (YAML) and unstructured (body text) formats.
        """
        email = {
            "to": task_data.get("to") or task_data.get("recipient"),
            "subject": task_data.get("subject"),
            "body": task_data.get("message") or task_data.get("email_body"),
            "cc": task_data.get("cc"),
            "reply_to_id": task_data.get("reply_to_id") or task_data.get("thread_id"),
        }

        # Parse from body text if not in YAML
        body_text = task_data.get("body", "")

        if not email["to"]:
            to_match = re.search(r"To:\s*(.+?)(?:\n|$)", body_text)
            if to_match:
                email["to"] = to_match.group(1).strip()

        if not email["subject"]:
            subject_match = re.search(r"Subject:\s*(.+?)(?:\n|$)", body_text)
            if subject_match:
                email["subject"] = subject_match.group(1).strip()

        if not email["body"]:
            # Extract body after headers
            lines = body_text.split("\n")
            body_start = 0
            for i, line in enumerate(lines):
                if line.strip() == "" and i > 0:
                    body_start = i + 1
                    break
                if line.startswith("Body:") or line.startswith("Message:"):
                    body_start = i + 1
                    break
            email["body"] = "\n".join(lines[body_start:]).strip()

        if not email["cc"]:
            cc_match = re.search(r"CC:\s*(.+?)(?:\n|$)", body_text)
            if cc_match:
                email["cc"] = cc_match.group(1).strip()

        return email

    def _init_gmail_service(self) -> bool:
        """Initialize Gmail API service with authentication."""
        if self._service:
            return True

        creds = None

        # Load saved credentials
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
                    logger.error("credentials.json not found")
                    return False

                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self._credentials_path), self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    logger.error(f"Failed to authenticate: {e}")
                    return False

            # Save credentials
            with open(self._token_path, "wb") as token:
                pickle.dump(creds, token)

        try:
            self._service = build("gmail", "v1", credentials=creds)
            return True
        except Exception as e:
            logger.error(f"Failed to build Gmail service: {e}")
            return False

    def _send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> str:
        """
        Send email via Gmail API.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            cc: CC recipients (comma-separated)
            thread_id: Thread ID for replies

        Returns:
            Message ID of sent email
        """
        message = MIMEMultipart()
        message["to"] = to
        message["subject"] = subject

        if cc:
            message["cc"] = cc

        message.attach(MIMEText(body, "plain"))

        # Encode message
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        body_data = {"raw": raw}
        if thread_id:
            body_data["threadId"] = thread_id

        # Send via Gmail API
        result = (
            self._service.users()
            .messages()
            .send(userId="me", body=body_data)
            .execute()
        )

        return result.get("id", "unknown")


class EmailDraftAction(BaseAction):
    """
    Creates email drafts instead of sending.

    Used for emails that need additional review.
    """

    def __init__(self):
        super().__init__(name="email_draft")

    def can_handle(self, task_data: dict) -> bool:
        """Handle draft email tasks."""
        task_type = task_data.get("type", "").lower()
        return task_type in ("email_draft", "draft_email")

    def execute(self, task_data: dict, task_path: Path) -> ActionResult:
        """
        Create an email draft in the vault.

        Drafts are saved to obsidian_vault/Drafts/ for human review
        before actual sending.
        """
        drafts_path = settings.vault_path / "Drafts"
        drafts_path.mkdir(exist_ok=True)

        # Extract email data
        email_data = {
            "to": task_data.get("to", ""),
            "subject": task_data.get("subject", ""),
            "body": task_data.get("message", task_data.get("body", "")),
        }

        # Create draft file
        draft_filename = f"draft_{task_path.stem}.md"
        draft_path = drafts_path / draft_filename

        draft_content = f"""---
type: email_send
to: {email_data['to']}
subject: {email_data['subject']}
status: draft
created: {task_path.stat().st_mtime}
---

# Email Draft

**To**: {email_data['to']}
**Subject**: {email_data['subject']}

---

{email_data['body']}

---

*Move this file to `Approved/` to send the email.*
"""

        draft_path.write_text(draft_content, encoding="utf-8")

        result = ActionResult(
            status=ActionStatus.SUCCESS,
            message=f"Email draft created: {draft_path.name}",
            data={"draft_path": str(draft_path), **email_data},
        )
        self._log_execution(task_path, result, email_data)

        logger.info(f"Email draft created: {draft_path}")
        return result

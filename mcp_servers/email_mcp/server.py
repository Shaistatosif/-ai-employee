"""
Email MCP Server for Personal AI Employee System.

Provides tools for Claude Desktop/Code to interact with Gmail:
- send_email: Send an email via Gmail API
- draft_email: Create an email draft in the vault
- list_recent_emails: List recently processed email tasks
- search_emails: Search through processed email tasks

Run with: python -m mcp_servers.email_mcp.server
"""

import base64
import logging
import os
import pickle
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import settings

logger = logging.getLogger(__name__)

# Create the MCP server
mcp = FastMCP(
    "AI Employee - Email",
    version="1.0.0",
)

# Google API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False


def _get_gmail_service(scope: str = "send"):
    """Get authenticated Gmail API service."""
    if not GOOGLE_API_AVAILABLE:
        raise RuntimeError(
            "Google API libraries not installed. "
            "Run: pip install google-api-python-client google-auth-oauthlib"
        )

    scopes_map = {
        "send": ["https://www.googleapis.com/auth/gmail.send"],
        "readonly": ["https://www.googleapis.com/auth/gmail.readonly"],
    }
    scopes = scopes_map.get(scope, scopes_map["send"])

    token_path = PROJECT_ROOT / f"token_{scope}.pickle"
    credentials_path = PROJECT_ROOT / "credentials.json"

    creds = None
    if token_path.exists():
        with open(token_path, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not credentials_path.exists():
                raise RuntimeError(
                    f"credentials.json not found at {credentials_path}. "
                    "Download from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), scopes
            )
            creds = flow.run_local_server(port=0)

        with open(token_path, "wb") as f:
            pickle.dump(creds, f)

    return build("gmail", "v1", credentials=creds)


@mcp.tool()
def send_email(
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
) -> str:
    """
    Send an email via Gmail API.

    IMPORTANT: This action is logged and audited. Use responsibly.
    In DRY_RUN mode, the email will NOT be sent.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body text (plain text)
        cc: Optional CC recipients (comma-separated)

    Returns:
        Confirmation message with message ID or dry-run notice
    """
    if settings.dry_run:
        return (
            f"[DRY RUN] Email prepared but NOT sent:\n"
            f"  To: {to}\n"
            f"  Subject: {subject}\n"
            f"  Body: {body[:200]}...\n"
            f"  CC: {cc or 'None'}\n\n"
            f"Set DRY_RUN=false in .env to enable sending."
        )

    try:
        service = _get_gmail_service("send")

        message = MIMEMultipart()
        message["to"] = to
        message["subject"] = subject
        if cc:
            message["cc"] = cc
        message.attach(MIMEText(body, "plain"))

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        result = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw})
            .execute()
        )

        msg_id = result.get("id", "unknown")

        # Log to database
        from config.database import log_action

        log_action(
            action_type="mcp_email_sent",
            target=to,
            parameters={"subject": subject, "cc": cc},
            result="success",
        )

        return f"Email sent successfully!\n  Message ID: {msg_id}\n  To: {to}\n  Subject: {subject}"

    except Exception as e:
        return f"Failed to send email: {str(e)}"


@mcp.tool()
def draft_email(
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
) -> str:
    """
    Create an email draft in the vault's Drafts folder for review.

    The draft will be saved as a markdown file. Move it to Approved/
    to trigger sending.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body text
        cc: Optional CC recipients

    Returns:
        Path to the created draft file
    """
    drafts_path = settings.vault_path / "Drafts"
    drafts_path.mkdir(exist_ok=True)

    now = datetime.now()
    safe_subject = "".join(
        c if c.isalnum() or c in "-_ " else "_" for c in subject
    )[:40].strip()
    filename = f"draft_{now.strftime('%Y%m%d_%H%M%S')}_{safe_subject}.md"
    draft_path = drafts_path / filename

    content = f"""---
type: email_send
to: '{to}'
subject: '{subject}'
cc: '{cc or ""}'
status: draft
created: '{now.isoformat()}'
---

# Email Draft

**To**: {to}
**Subject**: {subject}
**CC**: {cc or "None"}

---

{body}

---

*Move this file to `Approved/` to send the email.*
*Created by Email MCP Server*
"""

    draft_path.write_text(content, encoding="utf-8")

    from config.database import log_action

    log_action(
        action_type="mcp_email_drafted",
        target=str(draft_path),
        parameters={"to": to, "subject": subject},
        result="success",
    )

    return f"Email draft created:\n  Path: {draft_path}\n  To: {to}\n  Subject: {subject}\n\nMove to Approved/ to send."


@mcp.tool()
def list_recent_emails(limit: int = 10) -> str:
    """
    List recently processed email tasks from the Done folder.

    Args:
        limit: Maximum number of emails to list (default 10)

    Returns:
        Formatted list of recent email tasks
    """
    email_files = []

    for folder in [settings.done_path, settings.pending_approval_path, settings.needs_action_path]:
        for f in folder.glob("*Email*.md"):
            try:
                stat = f.stat()
                email_files.append({
                    "name": f.stem,
                    "folder": folder.name,
                    "modified": datetime.fromtimestamp(stat.st_mtime),
                    "path": str(f),
                })
            except Exception:
                continue

    # Sort by most recent
    email_files.sort(key=lambda x: x["modified"], reverse=True)
    email_files = email_files[:limit]

    if not email_files:
        return "No email tasks found."

    lines = [f"Recent Email Tasks ({len(email_files)}):\n"]
    for ef in email_files:
        lines.append(
            f"  - [{ef['folder']}] {ef['name']} "
            f"({ef['modified'].strftime('%Y-%m-%d %H:%M')})"
        )

    return "\n".join(lines)


@mcp.tool()
def search_emails(query: str) -> str:
    """
    Search through processed email tasks in the vault.

    Searches email task filenames and content for the query string.

    Args:
        query: Search query (searches filenames and content)

    Returns:
        Matching email tasks
    """
    query_lower = query.lower()
    results = []

    for folder in [settings.done_path, settings.pending_approval_path, settings.needs_action_path]:
        for f in folder.glob("*Email*.md"):
            try:
                # Check filename
                if query_lower in f.name.lower():
                    results.append({"name": f.stem, "folder": folder.name, "match": "filename"})
                    continue

                # Check content
                content = f.read_text(encoding="utf-8")
                if query_lower in content.lower():
                    # Extract a snippet around the match
                    idx = content.lower().index(query_lower)
                    start = max(0, idx - 50)
                    end = min(len(content), idx + len(query) + 50)
                    snippet = content[start:end].replace("\n", " ").strip()
                    results.append({
                        "name": f.stem,
                        "folder": folder.name,
                        "match": "content",
                        "snippet": f"...{snippet}...",
                    })
            except Exception:
                continue

    if not results:
        return f"No email tasks found matching '{query}'."

    lines = [f"Search Results for '{query}' ({len(results)} matches):\n"]
    for r in results:
        line = f"  - [{r['folder']}] {r['name']} (matched: {r['match']})"
        if "snippet" in r:
            line += f"\n    {r['snippet']}"
        lines.append(line)

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()

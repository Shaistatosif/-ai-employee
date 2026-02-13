"""
WhatsApp watcher for Personal AI Employee System.

Monitors WhatsApp messages via Twilio API and creates tasks in the vault.
Requires Twilio account with WhatsApp Sandbox configured.
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from config import settings
from config.database import log_action
from .base_watcher import BaseWatcher

logger = logging.getLogger(__name__)

# Twilio import - optional
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    TwilioClient = None


class WhatsAppWatcher(BaseWatcher):
    """
    Watches WhatsApp messages via Twilio API.

    Creates tasks in Needs_Action folder for each new message.
    Uses polling mode to check Twilio message history.

    Usage:
        watcher = WhatsAppWatcher(check_interval=60)
        watcher.start()
    """

    def __init__(self, check_interval: int = 60):
        super().__init__(name="WhatsApp Watcher")
        self.check_interval = check_interval
        self._client: Optional[TwilioClient] = None
        self._thread: Optional[threading.Thread] = None
        self._processed_sids: set[str] = set()
        self._last_fetch_time: Optional[datetime] = None

    def _build_client(self) -> bool:
        """Initialize Twilio client."""
        if not TWILIO_AVAILABLE:
            logger.error("Twilio library not installed. Run: pip install twilio")
            return False

        account_sid = settings.twilio_account_sid
        auth_token = settings.twilio_auth_token

        if not account_sid or not auth_token:
            logger.error("Twilio credentials not configured in .env")
            return False

        try:
            self._client = TwilioClient(account_sid, auth_token)
            logger.info("Twilio client initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
            return False

    def start(self) -> None:
        """Start watching WhatsApp messages (non-blocking)."""
        if not TWILIO_AVAILABLE:
            logger.error(
                "Twilio library not installed. Run: pip install twilio"
            )
            return

        if self.is_running:
            logger.warning(f"{self.name} is already running")
            return

        if not self._build_client():
            logger.error("Failed to initialize Twilio client. Check credentials.")
            return

        self.is_running = True
        self._last_fetch_time = datetime.utcnow() - timedelta(minutes=5)

        log_action(
            action_type="watcher_started",
            target="whatsapp",
            parameters={"interval": self.check_interval},
            result="success",
        )

        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info(f"{self.name} started (interval: {self.check_interval}s)")

    def _poll_loop(self) -> None:
        """Polling loop that runs in a background thread."""
        while self.is_running:
            try:
                self.check()
            except Exception as e:
                self.log_error(e, "Error in WhatsApp poll loop")
            time.sleep(self.check_interval)

    def stop(self) -> None:
        """Stop watching WhatsApp."""
        if not self.is_running:
            return

        self.is_running = False
        if self._thread is not None:
            self._thread.join(timeout=self.check_interval + 5)
            self._thread = None

        log_action(
            action_type="watcher_stopped",
            target="whatsapp",
            result="success",
        )
        logger.info(f"{self.name} stopped")

    def check(self) -> list[dict]:
        """
        Check for new WhatsApp messages via Twilio API.

        Returns:
            List of new message dicts
        """
        self.last_check = datetime.now()

        if not self._client:
            if not self._build_client():
                return []

        new_messages = []

        try:
            # Fetch messages received since last check
            whatsapp_from = settings.twilio_whatsapp_from or "whatsapp:"
            messages = self._client.messages.list(
                to=whatsapp_from,
                date_sent_after=self._last_fetch_time,
                limit=20,
            )

            for msg in messages:
                if msg.sid in self._processed_sids:
                    continue

                message_data = {
                    "sid": msg.sid,
                    "from": msg.from_,
                    "to": msg.to,
                    "body": msg.body or "",
                    "date_sent": msg.date_sent,
                    "status": msg.status,
                    "num_media": int(msg.num_media or 0),
                }

                new_messages.append(message_data)
                self._process_message(message_data)
                self._processed_sids.add(msg.sid)

            self._last_fetch_time = datetime.utcnow()

            if new_messages:
                logger.info(f"Found {len(new_messages)} new WhatsApp message(s)")

        except Exception as e:
            self.log_error(e, "Error checking WhatsApp messages")

        return new_messages

    def _process_message(self, msg: dict) -> None:
        """Create a task file for the WhatsApp message."""
        priority = self._detect_priority(msg["body"])

        sender = msg["from"].replace("whatsapp:", "")
        body = msg["body"]

        content = f"""## WhatsApp Message

**From**: {sender}
**Date**: {msg['date_sent'].isoformat() if msg['date_sent'] else 'Unknown'}
**Media Attachments**: {msg['num_media']}

## Message Content

{body}

## Analysis Required

1. Categorize this message (TASK/QUESTION/INFO/SPAM)
2. Determine action needed (REPLY/ACTION/ARCHIVE)
3. If reply needed, draft a response
"""

        self.create_task_file(
            title=f"WhatsApp: {body[:40]}",
            content=content,
            source=f"WhatsApp: {sender}",
            priority=priority,
            metadata={
                "twilio_sid": msg["sid"],
                "from": sender,
                "num_media": msg["num_media"],
            },
        )

    def _detect_priority(self, body: str) -> str:
        """Detect message priority based on keywords."""
        body_lower = body.lower()

        urgent_keywords = [
            "urgent", "asap", "emergency", "critical", "immediately",
            "help", "sos", "important",
        ]
        if any(kw in body_lower for kw in urgent_keywords):
            return "high"

        return "normal"

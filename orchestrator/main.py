"""
Main orchestrator for Personal AI Employee System.

Coordinates watchers, processes tasks, and manages the workflow.
"""

import logging
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import settings
from config.database import log_action, init_database
from watchers import FilesystemWatcher, GmailWatcher, GOOGLE_API_AVAILABLE

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Main orchestrator that coordinates all system components.

    Responsibilities:
    - Start/stop watchers
    - Monitor vault folders for changes
    - Coordinate task processing
    - Handle graceful shutdown
    """

    def __init__(self):
        self.watchers = []
        self.is_running = False
        self.start_time: Optional[datetime] = None
        self.watcher_threads: list[threading.Thread] = []

    def setup(self) -> None:
        """Initialize the system."""
        logger.info("Setting up AI Employee System...")

        # Ensure all directories exist
        settings.ensure_directories()
        logger.info(f"Vault path: {settings.vault_path}")

        # Initialize database (if configured)
        if settings.is_database_configured():
            if init_database():
                logger.info("Database initialized")
            else:
                logger.warning("Database initialization failed - using file logging")
        else:
            logger.info("Database not configured - using file logging only")

        # Create Inbox folder for filesystem watcher
        inbox_path = settings.vault_path / "Inbox"
        inbox_path.mkdir(exist_ok=True)

        # Setup filesystem watcher (always enabled)
        fs_watcher = FilesystemWatcher(watch_path=inbox_path)
        self.watchers.append(fs_watcher)

        # Setup Gmail watcher (if Google API available and credentials.json exists)
        credentials_path = Path("credentials.json")
        if not GOOGLE_API_AVAILABLE:
            logger.info("Gmail watcher disabled (Google API libraries not installed)")
            logger.info("  To enable: pip install google-api-python-client google-auth-oauthlib")
        elif not credentials_path.exists():
            logger.info("Gmail watcher disabled (no credentials.json)")
            logger.info("  To enable: download credentials.json from Google Cloud Console")
        else:
            gmail_watcher = GmailWatcher(check_interval=60, max_results=10)
            self.watchers.append(gmail_watcher)
            logger.info("Gmail watcher enabled (credentials.json found)")

        logger.info("Setup complete")

    def start(self) -> None:
        """Start all watchers and begin processing."""
        if self.is_running:
            logger.warning("Orchestrator is already running")
            return

        self.is_running = True
        self.start_time = datetime.now()

        # Log system start
        log_action(
            action_type="system_started",
            target="orchestrator",
            parameters={
                "dry_run": settings.dry_run,
                "vault_path": str(settings.vault_path),
                "watchers": len(self.watchers),
            },
            result="success",
        )

        # Start all watchers
        for watcher in self.watchers:
            try:
                watcher.start()
                logger.info(f"Started: {watcher.name}")
            except Exception as e:
                logger.error(f"Failed to start {watcher.name}: {e}")

        logger.info("=" * 50)
        logger.info("AI Employee System is running!")
        logger.info(f"  Vault: {settings.vault_path}")
        logger.info(f"  Dry Run: {settings.dry_run}")
        logger.info(f"  Watchers: {len(self.watchers)}")
        logger.info("=" * 50)
        logger.info("Drop files into the Inbox folder to create tasks.")
        logger.info("Press Ctrl+C to stop.")
        logger.info("=" * 50)

    def stop(self) -> None:
        """Stop all watchers and shutdown gracefully."""
        if not self.is_running:
            return

        logger.info("Shutting down AI Employee System...")

        # Stop all watchers
        for watcher in self.watchers:
            try:
                watcher.stop()
                logger.info(f"Stopped: {watcher.name}")
            except Exception as e:
                logger.error(f"Error stopping {watcher.name}: {e}")

        # Log system stop
        uptime = datetime.now() - self.start_time if self.start_time else None
        log_action(
            action_type="system_stopped",
            target="orchestrator",
            parameters={
                "uptime_seconds": uptime.total_seconds() if uptime else 0,
                "items_processed": sum(w.items_processed for w in self.watchers),
            },
            result="success",
        )

        self.is_running = False
        logger.info("Shutdown complete")

    def get_status(self) -> dict:
        """Get system status."""
        uptime = datetime.now() - self.start_time if self.start_time else None
        return {
            "is_running": self.is_running,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "uptime_seconds": uptime.total_seconds() if uptime else 0,
            "dry_run": settings.dry_run,
            "vault_path": str(settings.vault_path),
            "watchers": [w.get_status() for w in self.watchers],
            "pending_tasks": self._count_pending_tasks(),
            "completed_tasks": self._count_completed_tasks(),
        }

    def _count_pending_tasks(self) -> int:
        """Count tasks in Needs_Action folder."""
        try:
            return len(list(settings.needs_action_path.glob("*.md")))
        except Exception:
            return 0

    def _count_completed_tasks(self) -> int:
        """Count tasks in Done folder."""
        try:
            return len(list(settings.done_path.glob("*.md")))
        except Exception:
            return 0

    def run(self) -> None:
        """Run the orchestrator (blocking)."""
        # Handle shutdown signals
        def signal_handler(sig, frame):
            logger.info("Received shutdown signal")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Setup and start
        self.setup()
        self.start()

        # Main loop
        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()


def main():
    """Entry point for the orchestrator."""
    # Setup logging
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Print banner
    print("""
    ============================================================
    |         Personal AI Employee System v0.1.0               |
    |       Your life and business on autopilot.               |
    ============================================================
    """)

    # Run orchestrator
    orchestrator = Orchestrator()
    orchestrator.run()


if __name__ == "__main__":
    main()

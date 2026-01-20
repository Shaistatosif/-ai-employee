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
from workflow import TaskProcessor, ApprovalHandler
from orchestrator.scheduler import Scheduler, WeeklyBriefingGenerator

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
        self.task_processor: Optional[TaskProcessor] = None
        self.approval_handler: Optional[ApprovalHandler] = None
        self.scheduler: Optional[Scheduler] = None
        self.briefing_generator: Optional[WeeklyBriefingGenerator] = None
        self.process_interval = 10  # seconds between processing cycles

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

        # Setup HITL workflow components
        self.task_processor = TaskProcessor()
        self.approval_handler = ApprovalHandler(on_approved=self._on_task_approved)
        logger.info("HITL workflow initialized")

        # Setup scheduler with periodic tasks
        self.scheduler = Scheduler()
        self.briefing_generator = WeeklyBriefingGenerator()

        # Weekly briefing: run every 7 days (604800 seconds)
        self.scheduler.add_task(
            name="weekly_briefing",
            callback=self.briefing_generator.generate,
            interval_seconds=604800,  # 7 days
            run_immediately=False,
        )

        # Dashboard update: run every hour (3600 seconds)
        self.scheduler.add_task(
            name="dashboard_update",
            callback=self._update_dashboard,
            interval_seconds=3600,  # 1 hour
            run_immediately=True,
        )

        logger.info("Scheduler initialized with periodic tasks")

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

        # Start scheduler
        if self.scheduler:
            self.scheduler.start()
            logger.info("Started: Scheduler")

        logger.info("=" * 50)
        logger.info("AI Employee System is running!")
        logger.info(f"  Vault: {settings.vault_path}")
        logger.info(f"  Dry Run: {settings.dry_run}")
        logger.info(f"  Watchers: {len(self.watchers)}")
        logger.info(f"  HITL Workflow: Enabled")
        logger.info(f"  Scheduler: Enabled ({len(self.scheduler.tasks) if self.scheduler else 0} tasks)")
        logger.info("=" * 50)
        logger.info("WORKFLOW:")
        logger.info("  1. Drop files in Inbox/ -> Creates task in Needs_Action/")
        logger.info("  2. AI analyzes -> Creates plan, routes to Pending_Approval/ or Approved/")
        logger.info("  3. Review Pending_Approval/ -> Move to Approved/ to execute")
        logger.info("  4. Completed tasks -> Done/")
        logger.info("=" * 50)
        logger.info("Press Ctrl+C to stop.")
        logger.info("=" * 50)

    def stop(self) -> None:
        """Stop all watchers and shutdown gracefully."""
        if not self.is_running:
            return

        logger.info("Shutting down AI Employee System...")

        # Stop scheduler
        if self.scheduler:
            self.scheduler.stop()
            logger.info("Stopped: Scheduler")

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
            "scheduler": self.scheduler.get_status() if self.scheduler else None,
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

    def _count_pending_approvals(self) -> int:
        """Count tasks in Pending_Approval folder."""
        try:
            return len([f for f in settings.pending_approval_path.glob("*.md")
                       if "_plan_" not in f.name])
        except Exception:
            return 0

    def _on_task_approved(self, task_path: Path) -> None:
        """Callback when a task is approved by human."""
        logger.info(f"Task approved and ready for execution: {task_path.name}")
        # In DRY_RUN mode, we don't execute external actions
        if settings.dry_run:
            logger.info("  (DRY_RUN mode - no external actions executed)")

    def _update_dashboard(self) -> None:
        """Update the Dashboard.md with current system status."""
        try:
            dashboard_path = settings.vault_path / "Dashboard.md"
            now = datetime.now()

            # Gather statistics
            pending_tasks = self._count_pending_tasks()
            pending_approvals = self._count_pending_approvals()
            completed_tasks = self._count_completed_tasks()
            uptime = (now - self.start_time).total_seconds() / 3600 if self.start_time else 0

            # Build dashboard content
            content = f"""# AI Employee Dashboard

**Last Updated**: {now.strftime('%Y-%m-%d %H:%M:%S')}
**System Status**: {"🟢 Running" if self.is_running else "🔴 Stopped"}
**Mode**: {"🧪 DRY RUN" if settings.dry_run else "🚀 LIVE"}

---

## Quick Stats

| Metric | Value |
|--------|-------|
| Tasks Pending | {pending_tasks} |
| Awaiting Approval | {pending_approvals} |
| Completed | {completed_tasks} |
| Uptime | {uptime:.1f} hours |
| Watchers Active | {len(self.watchers)} |

---

## Folders

- 📥 **Inbox**: Drop files here for processing
- 📋 **Needs_Action**: {pending_tasks} task(s) awaiting AI analysis
- ⏳ **Pending_Approval**: {pending_approvals} task(s) need your review
- ✅ **Approved**: Ready for execution
- ✔️ **Done**: Completed tasks archive

---

## Recent Activity

Check `Logs/` folder for detailed action logs.

---

## Scheduled Tasks

| Task | Interval | Next Run |
|------|----------|----------|
| Weekly Briefing | 7 days | Check Briefings/ |
| Dashboard Update | 1 hour | Auto |

---

*Dashboard auto-updates hourly when system is running*
"""

            dashboard_path.write_text(content, encoding="utf-8")
            logger.debug("Dashboard updated")

            log_action(
                action_type="dashboard_updated",
                target=str(dashboard_path),
                parameters={"pending": pending_tasks, "approvals": pending_approvals},
                result="success",
            )
        except Exception as e:
            logger.error(f"Failed to update dashboard: {e}")

    def _process_cycle(self) -> None:
        """Run one cycle of task processing."""
        # Process new tasks from Needs_Action
        if self.task_processor:
            new_tasks = self.task_processor.process_all()
            if new_tasks > 0:
                logger.info(f"Processed {new_tasks} new task(s)")

        # Process approved tasks
        if self.approval_handler:
            approved = self.approval_handler.process_approvals()
            if approved > 0:
                logger.info(f"Completed {approved} approved task(s)")

            # Log pending count periodically
            pending = self._count_pending_approvals()
            if pending > 0:
                logger.debug(f"Tasks awaiting approval: {pending}")

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

        # Main loop with processing
        last_process_time = time.time()
        try:
            while self.is_running:
                current_time = time.time()

                # Run processing cycle at interval
                if current_time - last_process_time >= self.process_interval:
                    self._process_cycle()
                    last_process_time = current_time

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

"""
Scheduler for Personal AI Employee System.

Handles periodic tasks like weekly briefings and maintenance.
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

from config import settings
from config.database import log_action

logger = logging.getLogger(__name__)


class ScheduledTask:
    """Represents a scheduled task."""

    def __init__(
        self,
        name: str,
        callback: Callable,
        interval_seconds: int,
        run_immediately: bool = False,
    ):
        self.name = name
        self.callback = callback
        self.interval_seconds = interval_seconds
        self.last_run: Optional[datetime] = None
        self.next_run: datetime = datetime.now() if run_immediately else datetime.now() + timedelta(seconds=interval_seconds)
        self.run_count = 0
        self.error_count = 0

    def should_run(self) -> bool:
        """Check if task should run now."""
        return datetime.now() >= self.next_run

    def run(self) -> bool:
        """Execute the task."""
        try:
            logger.info(f"Running scheduled task: {self.name}")
            self.callback()
            self.last_run = datetime.now()
            self.next_run = datetime.now() + timedelta(seconds=self.interval_seconds)
            self.run_count += 1
            return True
        except Exception as e:
            logger.error(f"Scheduled task {self.name} failed: {e}")
            self.error_count += 1
            self.next_run = datetime.now() + timedelta(seconds=self.interval_seconds)
            return False


class Scheduler:
    """
    Task scheduler for periodic operations.

    Supports:
    - Interval-based scheduling
    - Weekly briefing generation
    - Dashboard updates
    - Cleanup tasks
    """

    def __init__(self):
        self.tasks: list[ScheduledTask] = []
        self.is_running = False
        self._thread: Optional[threading.Thread] = None

    def add_task(
        self,
        name: str,
        callback: Callable,
        interval_seconds: int,
        run_immediately: bool = False,
    ) -> None:
        """
        Add a scheduled task.

        Args:
            name: Task name for logging
            callback: Function to call
            interval_seconds: Seconds between runs
            run_immediately: Run once immediately on start
        """
        task = ScheduledTask(name, callback, interval_seconds, run_immediately)
        self.tasks.append(task)
        logger.info(f"Scheduled task added: {name} (every {interval_seconds}s)")

    def start(self) -> None:
        """Start the scheduler in background thread."""
        if self.is_running:
            return

        self.is_running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Scheduler started")

    def stop(self) -> None:
        """Stop the scheduler."""
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Scheduler stopped")

    def _run_loop(self) -> None:
        """Main scheduler loop."""
        while self.is_running:
            for task in self.tasks:
                if task.should_run():
                    task.run()
            time.sleep(1)

    def get_status(self) -> dict:
        """Get scheduler status."""
        return {
            "is_running": self.is_running,
            "task_count": len(self.tasks),
            "tasks": [
                {
                    "name": t.name,
                    "interval": t.interval_seconds,
                    "last_run": t.last_run.isoformat() if t.last_run else None,
                    "next_run": t.next_run.isoformat(),
                    "run_count": t.run_count,
                    "error_count": t.error_count,
                }
                for t in self.tasks
            ],
        }


class WeeklyBriefingGenerator:
    """
    Generates weekly CEO briefing reports.

    Analyzes:
    - Completed tasks from Done folder
    - Business goals progress
    - Bottlenecks (tasks pending > 2 days)
    - Subscription usage (if tracked)
    """

    def __init__(self):
        self.last_generated: Optional[datetime] = None

    def generate(self) -> Path:
        """
        Generate weekly briefing report.

        Returns:
            Path to generated briefing file
        """
        now = datetime.now()
        week_start = now - timedelta(days=7)

        # Gather data
        completed_tasks = self._get_completed_tasks(week_start)
        pending_tasks = self._get_pending_tasks()
        bottlenecks = self._find_bottlenecks()
        goals_status = self._read_goals()

        # Generate report
        report = self._build_report(
            now, week_start, completed_tasks, pending_tasks, bottlenecks, goals_status
        )

        # Save to Briefings folder
        filename = f"{now.strftime('%Y-%m-%d')}_Weekly_Briefing.md"
        briefing_path = settings.briefings_path / filename
        briefing_path.write_text(report, encoding="utf-8")

        self.last_generated = now

        log_action(
            action_type="briefing_generated",
            target=str(briefing_path),
            parameters={
                "completed_count": len(completed_tasks),
                "pending_count": len(pending_tasks),
                "bottleneck_count": len(bottlenecks),
            },
            result="success",
        )

        logger.info(f"Weekly briefing generated: {briefing_path}")
        return briefing_path

    def _get_completed_tasks(self, since: datetime) -> list[dict]:
        """Get tasks completed since date."""
        tasks = []
        for task_file in settings.done_path.glob("*.md"):
            try:
                stat = task_file.stat()
                modified = datetime.fromtimestamp(stat.st_mtime)
                if modified >= since:
                    tasks.append({
                        "name": task_file.stem,
                        "completed": modified,
                    })
            except Exception:
                continue
        return sorted(tasks, key=lambda x: x["completed"], reverse=True)

    def _get_pending_tasks(self) -> list[dict]:
        """Get all pending tasks."""
        tasks = []

        # Check Needs_Action
        for task_file in settings.needs_action_path.glob("*.md"):
            tasks.append({
                "name": task_file.stem,
                "folder": "Needs_Action",
                "age_days": self._get_file_age_days(task_file),
            })

        # Check Pending_Approval
        for task_file in settings.pending_approval_path.glob("*.md"):
            if "_plan_" not in task_file.name:
                tasks.append({
                    "name": task_file.stem,
                    "folder": "Pending_Approval",
                    "age_days": self._get_file_age_days(task_file),
                })

        return tasks

    def _find_bottlenecks(self) -> list[dict]:
        """Find tasks pending more than 2 days."""
        bottlenecks = []
        pending = self._get_pending_tasks()

        for task in pending:
            if task["age_days"] > 2:
                bottlenecks.append(task)

        return sorted(bottlenecks, key=lambda x: x["age_days"], reverse=True)

    def _get_file_age_days(self, path: Path) -> float:
        """Get file age in days."""
        try:
            stat = path.stat()
            created = datetime.fromtimestamp(stat.st_mtime)
            return (datetime.now() - created).days
        except Exception:
            return 0

    def _read_goals(self) -> str:
        """Read business goals summary."""
        goals_path = settings.vault_path / "Business_Goals.md"
        if goals_path.exists():
            content = goals_path.read_text(encoding="utf-8")
            # Extract just the key results section
            lines = content.split("\n")
            summary_lines = []
            in_section = False
            for line in lines:
                if "## Key Results" in line or "### KR" in line:
                    in_section = True
                if in_section:
                    summary_lines.append(line)
                    if len(summary_lines) > 15:
                        break
            return "\n".join(summary_lines) if summary_lines else "No goals defined"
        return "Business_Goals.md not found"

    def _build_report(
        self,
        now: datetime,
        week_start: datetime,
        completed: list[dict],
        pending: list[dict],
        bottlenecks: list[dict],
        goals: str,
    ) -> str:
        """Build the briefing report."""
        return f"""# Weekly CEO Briefing

**Generated**: {now.strftime('%Y-%m-%d %H:%M')}
**Period**: {week_start.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}

---

## Executive Summary

- **Tasks Completed This Week**: {len(completed)}
- **Tasks Pending**: {len(pending)}
- **Bottlenecks (>2 days)**: {len(bottlenecks)}

---

## Completed Tasks

{self._format_completed(completed)}

---

## Pending Tasks

{self._format_pending(pending)}

---

## Bottlenecks (Action Required)

{self._format_bottlenecks(bottlenecks)}

---

## Goals Progress

{goals}

---

## Recommendations

{self._generate_recommendations(completed, pending, bottlenecks)}

---

## Next Week Focus

1. Address bottlenecks listed above
2. Review pending approvals in Pending_Approval folder
3. Update Business_Goals.md with progress

---

*Generated by AI Employee System*
*Review time: ~2 minutes*
"""

    def _format_completed(self, tasks: list[dict]) -> str:
        if not tasks:
            return "*No tasks completed this week*"
        lines = []
        for task in tasks[:10]:  # Top 10
            lines.append(f"- [x] {task['name']} ({task['completed'].strftime('%m/%d')})")
        if len(tasks) > 10:
            lines.append(f"- ... and {len(tasks) - 10} more")
        return "\n".join(lines)

    def _format_pending(self, tasks: list[dict]) -> str:
        if not tasks:
            return "*No pending tasks*"
        lines = []
        for task in tasks[:10]:
            lines.append(f"- [ ] {task['name']} ({task['folder']}, {task['age_days']:.0f} days)")
        if len(tasks) > 10:
            lines.append(f"- ... and {len(tasks) - 10} more")
        return "\n".join(lines)

    def _format_bottlenecks(self, tasks: list[dict]) -> str:
        if not tasks:
            return "*No bottlenecks - great job!*"
        lines = []
        for task in tasks:
            lines.append(f"- **{task['name']}** - {task['age_days']:.0f} days in {task['folder']}")
        return "\n".join(lines)

    def _generate_recommendations(
        self, completed: list, pending: list, bottlenecks: list
    ) -> str:
        recommendations = []

        if len(bottlenecks) > 0:
            recommendations.append(f"- **Priority**: Clear {len(bottlenecks)} bottleneck(s) that are blocking progress")

        if len(pending) > 5:
            recommendations.append(f"- Review and prioritize {len(pending)} pending tasks")

        approval_count = sum(1 for t in pending if t["folder"] == "Pending_Approval")
        if approval_count > 0:
            recommendations.append(f"- {approval_count} task(s) awaiting your approval")

        if len(completed) == 0:
            recommendations.append("- No tasks completed this week - review workload and blockers")
        elif len(completed) > 10:
            recommendations.append(f"- Excellent productivity! {len(completed)} tasks completed")

        if not recommendations:
            recommendations.append("- System running smoothly, continue current workflow")

        return "\n".join(recommendations)

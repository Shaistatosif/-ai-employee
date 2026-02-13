"""
Watchdog monitor for Personal AI Employee System.

Monitors watcher health and automatically restarts failed watchers
with exponential backoff. Alerts human when max retries exceeded.
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from config import settings
from config.database import log_action

logger = logging.getLogger(__name__)


class WatchdogMonitor:
    """
    Monitors watcher health and automatically restarts failed watchers.

    Features:
    - Health checks every 60 seconds
    - Exponential backoff restart (1s, 2s, 4s... max 60s)
    - Max 3 restart attempts before alerting human
    - Creates alert files in Pending_Approval/ on failure
    """

    def __init__(self, watchers: list, health_check_interval: int = 60):
        self.watchers = watchers
        self.health_check_interval = health_check_interval
        self.max_restart_attempts = 3
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._restart_counts: dict[str, int] = {}
        self._last_errors: dict[str, str] = {}
        self._restart_history: list[dict] = []

    def start(self) -> None:
        """Start the watchdog monitor in a background thread."""
        if self.is_running:
            return

        self.is_running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"Watchdog started (checking every {self.health_check_interval}s)")

    def stop(self) -> None:
        """Stop the watchdog monitor."""
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Watchdog stopped")

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self.is_running:
            try:
                self._check_health()
            except Exception as e:
                logger.error(f"Watchdog health check error: {e}")
            time.sleep(self.health_check_interval)

    def _check_health(self) -> None:
        """Check health of all watchers."""
        for watcher in self.watchers:
            try:
                if not watcher.is_running:
                    logger.warning(f"Watchdog: {watcher.name} is not running")
                    self._restart_watcher(watcher)
                    continue

                # Check if watcher is stale (no check in 5 minutes)
                if watcher.last_check:
                    stale_threshold = datetime.now() - timedelta(minutes=5)
                    if watcher.last_check < stale_threshold:
                        logger.warning(
                            f"Watchdog: {watcher.name} is stale "
                            f"(last check: {watcher.last_check.isoformat()})"
                        )
                        self._restart_watcher(watcher)

            except Exception as e:
                logger.error(f"Watchdog: Error checking {watcher.name}: {e}")
                self._last_errors[watcher.name] = str(e)

    def _restart_watcher(self, watcher) -> None:
        """Restart a failed watcher with exponential backoff."""
        name = watcher.name
        count = self._restart_counts.get(name, 0)

        if count >= self.max_restart_attempts:
            logger.error(
                f"Watchdog: {name} exceeded max restart attempts ({self.max_restart_attempts})"
            )
            self._alert_human(watcher, f"Failed after {count} restart attempts")
            return

        # Exponential backoff: 1s, 2s, 4s... max 60s
        backoff = min(2 ** count, 60)
        logger.info(f"Watchdog: Restarting {name} (attempt {count + 1}/{self.max_restart_attempts}, backoff {backoff}s)")

        time.sleep(backoff)

        try:
            watcher.stop()
            watcher.start()
            self._restart_counts[name] = count + 1
            self._restart_history.append({
                "watcher": name,
                "attempt": count + 1,
                "timestamp": datetime.now().isoformat(),
                "success": True,
            })

            log_action(
                action_type="watchdog_restart",
                target=name,
                parameters={"attempt": count + 1, "backoff": backoff},
                result="success",
            )
            logger.info(f"Watchdog: {name} restarted successfully")

            # Reset count on successful restart
            if watcher.is_running:
                self._restart_counts[name] = 0

        except Exception as e:
            self._restart_counts[name] = count + 1
            self._last_errors[name] = str(e)
            self._restart_history.append({
                "watcher": name,
                "attempt": count + 1,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e),
            })

            log_action(
                action_type="watchdog_restart",
                target=name,
                parameters={"attempt": count + 1, "backoff": backoff},
                result="failure",
                error_message=str(e),
            )
            logger.error(f"Watchdog: Failed to restart {name}: {e}")

    def _alert_human(self, watcher, error: str) -> None:
        """Create an alert file in Pending_Approval/ for human attention."""
        try:
            now = datetime.now()
            filename = f"{now.strftime('%Y%m%d_%H%M%S')}_ALERT_{watcher.name.replace(' ', '_')}.md"
            alert_path = settings.pending_approval_path / filename

            content = f"""---
title: 'SYSTEM ALERT: {watcher.name} Failed'
source: 'Watchdog Monitor'
priority: high
created: '{now.isoformat()}'
watcher: Watchdog
status: alert
type: system_alert
---

# SYSTEM ALERT: {watcher.name} Failed

## Details

- **Watcher**: {watcher.name}
- **Error**: {error}
- **Time**: {now.strftime('%Y-%m-%d %H:%M:%S')}
- **Restart Attempts**: {self._restart_counts.get(watcher.name, 0)}
- **Max Attempts**: {self.max_restart_attempts}

## Action Required

The {watcher.name} has failed and could not be automatically restarted.

1. Check the system logs for detailed error information
2. Verify the watcher's configuration and dependencies
3. Restart the system manually if needed

## Last Error

```
{self._last_errors.get(watcher.name, 'Unknown')}
```

---

*Generated by Watchdog Monitor*
"""
            alert_path.write_text(content, encoding="utf-8")
            logger.info(f"Watchdog: Alert created at {alert_path}")

            log_action(
                action_type="watchdog_alert",
                target=watcher.name,
                parameters={"alert_path": str(alert_path), "error": error},
                result="alert",
            )

        except Exception as e:
            logger.error(f"Watchdog: Failed to create alert: {e}")

    def get_status(self) -> dict:
        """Get watchdog status."""
        return {
            "is_running": self.is_running,
            "health_check_interval": self.health_check_interval,
            "max_restart_attempts": self.max_restart_attempts,
            "restart_counts": dict(self._restart_counts),
            "last_errors": dict(self._last_errors),
            "restart_history": self._restart_history[-10:],  # Last 10 events
            "watchers_healthy": all(
                w.is_running for w in self.watchers
            ),
        }

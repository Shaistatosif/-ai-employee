"""
Filesystem watcher for Personal AI Employee System.

Monitors a directory for new files and creates tasks in the vault.
This is the simplest watcher - great for testing without API keys.
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Set

from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from watchdog.observers import Observer

from config import settings
from config.database import log_action
from .base_watcher import BaseWatcher

logger = logging.getLogger(__name__)


class NewFileHandler(FileSystemEventHandler):
    """Handle new file events."""

    def __init__(self, watcher: "FilesystemWatcher"):
        self.watcher = watcher
        super().__init__()

    def on_created(self, event: FileCreatedEvent) -> None:
        """Handle file creation event."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        logger.info(f"New file detected: {file_path}")
        self.watcher.process_new_file(file_path)


class FilesystemWatcher(BaseWatcher):
    """
    Watches a directory for new files.

    When a new file is dropped into the watched directory, it creates
    a task in the Needs_Action folder for Claude to process.

    Usage:
        watcher = FilesystemWatcher(watch_path="./inbox")
        watcher.start()
    """

    def __init__(
        self,
        watch_path: Optional[Path] = None,
        extensions: Optional[list[str]] = None,
    ):
        """
        Initialize the filesystem watcher.

        Args:
            watch_path: Directory to watch. Defaults to vault/Inbox
            extensions: File extensions to watch (e.g., ['.txt', '.pdf']).
                       None means watch all files.
        """
        super().__init__(name="Filesystem Watcher")

        # Default to an Inbox folder in the vault
        self.watch_path = watch_path or (settings.vault_path / "Inbox")
        self.extensions = extensions
        self.observer: Optional[Observer] = None
        self.processed_files: Set[str] = set()

        # Ensure watch directory exists
        self.watch_path.mkdir(parents=True, exist_ok=True)

    def start(self) -> None:
        """Start watching the directory."""
        if self.is_running:
            logger.warning(f"{self.name} is already running")
            return

        self.observer = Observer()
        event_handler = NewFileHandler(self)
        self.observer.schedule(event_handler, str(self.watch_path), recursive=False)
        self.observer.start()
        self.is_running = True

        logger.info(f"{self.name} started watching: {self.watch_path}")
        log_action(
            action_type="watcher_started",
            target=str(self.watch_path),
            parameters={"extensions": self.extensions},
            result="success",
        )

    def stop(self) -> None:
        """Stop watching the directory."""
        if not self.is_running or self.observer is None:
            return

        self.observer.stop()
        self.observer.join()
        self.is_running = False

        logger.info(f"{self.name} stopped")
        log_action(
            action_type="watcher_stopped",
            target=str(self.watch_path),
            result="success",
        )

    def check(self) -> list[dict]:
        """
        Manually check for new files (for polling mode).

        Returns:
            List of new files found
        """
        self.last_check = datetime.now()
        new_files = []

        try:
            for file_path in self.watch_path.iterdir():
                if file_path.is_file():
                    file_key = str(file_path)
                    if file_key not in self.processed_files:
                        if self._should_process(file_path):
                            new_files.append({
                                "path": file_path,
                                "name": file_path.name,
                                "size": file_path.stat().st_size,
                                "modified": datetime.fromtimestamp(
                                    file_path.stat().st_mtime
                                ),
                            })
        except Exception as e:
            self.log_error(e, "Error checking for new files")

        return new_files

    def process_new_file(self, file_path: Path) -> None:
        """
        Process a newly detected file.

        Args:
            file_path: Path to the new file
        """
        file_key = str(file_path)

        # Skip if already processed
        if file_key in self.processed_files:
            return

        # Skip if extension not in whitelist (if specified)
        if not self._should_process(file_path):
            logger.debug(f"Skipping file (extension not in whitelist): {file_path}")
            return

        try:
            # Read file content (with size limit for safety)
            content = self._read_file_safely(file_path)

            # Create task in Needs_Action
            self.create_task_file(
                title=f"Process file: {file_path.name}",
                content=f"""A new file was detected in the inbox.

**File**: {file_path.name}
**Path**: {file_path}
**Size**: {file_path.stat().st_size} bytes

## File Content

```
{content}
```

## Requested Action

Please analyze this file and determine the appropriate action:
1. If it's a task/request, create a plan
2. If it's information, file it appropriately
3. If unclear, ask for clarification
""",
                source=f"Filesystem: {self.watch_path}",
                priority="normal",
                metadata={
                    "original_path": str(file_path),
                    "file_size": file_path.stat().st_size,
                    "file_extension": file_path.suffix,
                },
            )

            self.processed_files.add(file_key)

        except Exception as e:
            self.log_error(e, f"Error processing file: {file_path}")

    def _should_process(self, file_path: Path) -> bool:
        """Check if file should be processed based on extension."""
        if self.extensions is None:
            return True
        return file_path.suffix.lower() in self.extensions

    def _read_file_safely(self, file_path: Path, max_size: int = 50000) -> str:
        """
        Read file content safely with size limit.

        Args:
            file_path: Path to file
            max_size: Maximum bytes to read

        Returns:
            File content or truncation notice
        """
        try:
            size = file_path.stat().st_size
            if size > max_size:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read(max_size)
                return f"{content}\n\n[... TRUNCATED - File size: {size} bytes ...]"
            else:
                return file_path.read_text(encoding="utf-8", errors="replace")
        except UnicodeDecodeError:
            return "[Binary file - cannot display content]"
        except Exception as e:
            return f"[Error reading file: {e}]"


def run_filesystem_watcher(
    watch_path: Optional[str] = None,
    poll_mode: bool = False,
    poll_interval: int = 30,
) -> None:
    """
    Run the filesystem watcher (blocking).

    Args:
        watch_path: Directory to watch (optional)
        poll_mode: Use polling instead of OS events
        poll_interval: Seconds between polls (if poll_mode)
    """
    import signal
    import sys

    # Setup logging
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Ensure directories exist
    settings.ensure_directories()

    # Create watcher
    path = Path(watch_path) if watch_path else None
    watcher = FilesystemWatcher(watch_path=path)

    # Handle shutdown gracefully
    def signal_handler(sig, frame):
        logger.info("Shutting down...")
        watcher.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if poll_mode:
        # Polling mode (simpler, works everywhere)
        logger.info(f"Starting in poll mode (interval: {poll_interval}s)")
        watcher.is_running = True
        try:
            while watcher.is_running:
                new_files = watcher.check()
                for file_info in new_files:
                    watcher.process_new_file(file_info["path"])
                time.sleep(poll_interval)
        except KeyboardInterrupt:
            pass
    else:
        # Event mode (more efficient)
        watcher.start()
        try:
            while watcher.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            watcher.stop()


if __name__ == "__main__":
    # Allow running directly: python -m watchers.filesystem_watcher
    import argparse

    parser = argparse.ArgumentParser(description="Filesystem Watcher")
    parser.add_argument("--path", help="Directory to watch")
    parser.add_argument("--poll", action="store_true", help="Use polling mode")
    parser.add_argument("--interval", type=int, default=30, help="Poll interval")

    args = parser.parse_args()
    run_filesystem_watcher(
        watch_path=args.path,
        poll_mode=args.poll,
        poll_interval=args.interval,
    )

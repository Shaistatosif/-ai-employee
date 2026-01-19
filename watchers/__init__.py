"""Watchers module for Personal AI Employee System."""

from .base_watcher import BaseWatcher
from .filesystem_watcher import FilesystemWatcher

# Gmail watcher requires Google API libraries
try:
    from .gmail_watcher import GmailWatcher, GOOGLE_API_AVAILABLE
except ImportError:
    GmailWatcher = None
    GOOGLE_API_AVAILABLE = False

__all__ = ["BaseWatcher", "FilesystemWatcher", "GmailWatcher", "GOOGLE_API_AVAILABLE"]

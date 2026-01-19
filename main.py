#!/usr/bin/env python3
"""
Personal AI Employee System - Main Entry Point

Usage:
    python main.py              # Start the full system
    python main.py --dry-run    # Start in dry-run mode (no external actions)
    python main.py --status     # Show system status

For development:
    python -m watchers.filesystem_watcher --poll  # Run just the filesystem watcher
"""

import argparse
import sys

from config import settings


def main():
    parser = argparse.ArgumentParser(
        description="Personal AI Employee System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    Start the system
  python main.py --dry-run          Start without executing external actions
  python main.py --check            Verify configuration and exit

Environment:
  Copy .env.example to .env and fill in your credentials.
  See README.md for setup instructions.
        """,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without executing external actions",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check configuration and exit",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    # Override dry_run if specified
    if args.dry_run:
        import os
        os.environ["DRY_RUN"] = "true"

    # Check configuration mode
    if args.check:
        print("Configuration Check")
        print("=" * 40)
        print(f"Vault Path: {settings.vault_path}")
        print(f"  Exists: {settings.vault_path.exists()}")
        print(f"Dry Run: {settings.dry_run}")
        print(f"Log Level: {settings.log_level}")
        print(f"Database: {'Configured' if settings.is_database_configured() else 'Not configured'}")
        print(f"Gmail: {'Configured' if settings.is_gmail_configured() else 'Not configured'}")
        print("=" * 40)

        # Check directories
        print("\nDirectory Status:")
        for name in ["needs_action", "plans", "pending_approval", "approved", "done", "logs"]:
            path = getattr(settings, f"{name}_path")
            status = "OK" if path.exists() else "MISSING"
            print(f"  {name}: {status}")

        return 0

    # Import and run orchestrator
    from orchestrator.main import main as run_orchestrator
    run_orchestrator()

    return 0


if __name__ == "__main__":
    sys.exit(main())

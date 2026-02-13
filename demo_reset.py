"""
Demo Reset Script - Cleans vault folders for a fresh presentation.
Run this BEFORE the demo to start with a clean state.

Usage: python demo_reset.py
"""

import shutil
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from config.config import settings

print("\n" + "=" * 50)
print("  AI Employee - Demo Reset")
print("=" * 50)

folders_to_clean = [
    settings.needs_action_path,
    settings.plans_path,
    settings.pending_approval_path,
    settings.approved_path,
    settings.done_path,
    settings.logs_path,
    settings.briefings_path,
    settings.multistep_path,
]

# Keep Inbox files but clean processing folders
for folder in folders_to_clean:
    if folder.exists():
        count = len(list(folder.glob("*.md"))) + len(list(folder.glob("*.yaml")))
        if count > 0:
            for f in folder.glob("*.md"):
                f.unlink()
            for f in folder.glob("*.yaml"):
                f.unlink()
            print(f"  Cleaned: {folder.name}/ ({count} files)")
        else:
            print(f"  Already clean: {folder.name}/")
    else:
        folder.mkdir(parents=True, exist_ok=True)
        print(f"  Created: {folder.name}/")

# Ensure directories exist
settings.ensure_directories()

# Clean Drafts subfolders
drafts = settings.drafts_path
for subfolder in ["LinkedIn", "Facebook", "Instagram", "Twitter", "Invoices", "Expenses"]:
    sub = drafts / subfolder
    if sub.exists():
        for f in sub.glob("*.md"):
            f.unlink()
    sub.mkdir(parents=True, exist_ok=True)

print(f"\n  Vault ready at: {settings.vault_path}")
print("  All folders cleaned for fresh demo!")
print("=" * 50 + "\n")

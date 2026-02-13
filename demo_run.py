"""
Interactive Demo Script for Personal AI Employee System.
Walks through the system step-by-step for presentation.

Usage: python demo_run.py
"""

import sys
import io
import os
import time
import shutil
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from config.config import settings

DEMO_FILES = Path("demo_files")
INBOX = settings.vault_path / "Inbox"


def banner():
    print("""
    ============================================================
    |                                                          |
    |       Personal AI Employee System - LIVE DEMO            |
    |       Your life and business on autopilot.               |
    |                                                          |
    |       Built for AI Employee Hackathon 2026               |
    |       Author: Shaista Tosif                              |
    |                                                          |
    ============================================================
    """)


def pause(msg="Press Enter to continue..."):
    input(f"\n    >>> {msg}")
    print()


def section(title, description):
    print(f"\n    {'='*50}")
    print(f"    {title}")
    print(f"    {'='*50}")
    print(f"    {description}\n")


def show_folder_counts():
    folders = {
        "Inbox": settings.vault_path / "Inbox",
        "Needs_Action": settings.needs_action_path,
        "Pending_Approval": settings.pending_approval_path,
        "Done": settings.done_path,
    }
    print("    Current Folder Status:")
    for name, path in folders.items():
        count = len(list(path.glob("*.md"))) + len(list(path.glob("*.txt")))
        indicator = "<--" if count > 0 else ""
        print(f"      {name:20s}: {count:3d} files  {indicator}")
    print()


def copy_demo_file(filename, wait=True):
    src = DEMO_FILES / filename
    dst = INBOX / filename
    if src.exists():
        shutil.copy2(src, dst)
        print(f"    Dropped: {filename} -> Inbox/")
        if wait:
            time.sleep(2)  # Give watcher time to detect
    else:
        print(f"    ERROR: {src} not found!")


# ============================================================
# DEMO FLOW
# ============================================================

banner()

section(
    "INTRODUCTION",
    "This system automates your digital life using AI.\n"
    "    It watches your files and emails, classifies tasks by risk,\n"
    "    and only asks YOU for approval when something is sensitive."
)

pause("Press Enter to see system architecture...")

section(
    "ARCHITECTURE OVERVIEW",
    "Inbox -> AI Analyzes -> HITL Risk Check -> Auto/Manual -> Done\n\n"
    "    Components:\n"
    "      - 3 Watchers (Filesystem, Gmail, WhatsApp)\n"
    "      - 9 Action Handlers (Email, Social Media, Odoo Accounting)\n"
    "      - HITL Classifier (Payment >$50, Delete, Sensitive = Manual)\n"
    "      - Watchdog Monitor (Auto-restart failed watchers)\n"
    "      - Ralph Loop (Multi-step task persistence)\n"
    "      - 2 MCP Servers (13 tools for Claude Desktop)\n"
    "      - Scheduler (Weekly briefings, hourly dashboard)"
)

pause("Press Enter to start the LIVE system...")

section(
    "STEP 1: Starting the System",
    "Watch the terminal where 'python main.py' is running.\n"
    "    You should see: Watchers started, Gmail fetching emails, etc."
)

print("    Make sure 'python main.py' is running in another terminal!")
pause("Confirm main.py is running, then press Enter...")

show_folder_counts()

# --- DEMO 1: Safe task (auto-approve) ---
section(
    "STEP 2: Safe Task (Auto-Approved)",
    "Dropping a SAFE task: 'Read quarterly report'\n"
    "    Expected: LOW risk -> Auto-approved -> Done"
)

pause("Press Enter to drop the safe task...")
copy_demo_file("01_safe_task.txt")
print("    Waiting for system to process (5 seconds)...")
time.sleep(5)
show_folder_counts()

pause("Notice: Task was auto-approved and moved to Done!")

# --- DEMO 2: Payment >$50 (requires approval) ---
section(
    "STEP 3: High-Risk Payment ($500)",
    "Dropping a PAYMENT task: '$500 to CloudTech'\n"
    "    Expected: HIGH risk -> Pending_Approval (needs YOUR review)"
)

pause("Press Enter to drop the payment request...")
copy_demo_file("02_payment_request.txt")
print("    Waiting for system to process (5 seconds)...")
time.sleep(5)
show_folder_counts()

pause("Notice: Payment went to Pending_Approval! Human must review.")

# --- DEMO 3: Email sending (auto-approve + real send) ---
section(
    "STEP 4: Email Sending (Real Gmail)",
    "Dropping an EMAIL task: Send email via Gmail API\n"
    "    Expected: Auto-approved -> Gmail sends real email!"
)

pause("Press Enter to drop the email task...")
copy_demo_file("03_send_email.txt")
print("    Waiting for email to send (8 seconds)...")
time.sleep(8)
show_folder_counts()

pause("Check your Gmail - real email was sent!")

# --- DEMO 4: Delete task (requires approval) ---
section(
    "STEP 5: Dangerous Task (Delete Files)",
    "Dropping a DELETE task: 'Delete all backup files'\n"
    "    Expected: HIGH risk -> Pending_Approval (blocked!)"
)

pause("Press Enter to drop the delete task...")
copy_demo_file("04_delete_sensitive.txt")
print("    Waiting for system to process (5 seconds)...")
time.sleep(5)
show_folder_counts()

pause("Notice: Delete task BLOCKED! System protected your data.")

# --- Summary ---
section(
    "DEMO COMPLETE - Summary",
    "What we demonstrated:\n\n"
    "    1. Safe task      -> Auto-approved, processed automatically\n"
    "    2. Payment $500   -> BLOCKED, needs human approval\n"
    "    3. Email sending   -> Auto-approved, real email sent via Gmail\n"
    "    4. Delete files    -> BLOCKED, needs human approval\n\n"
    "    The AI Employee handles safe tasks autonomously\n"
    "    but ALWAYS asks YOU before doing anything risky.\n\n"
    "    Gold Tier Features:\n"
    "      - 3 Watchers (File, Gmail, WhatsApp)\n"
    "      - 9 Action Handlers (Email, LinkedIn, FB, Insta, Twitter, Odoo)\n"
    "      - 2 MCP Servers (13 tools)\n"
    "      - Error Recovery (Watchdog with auto-restart)\n"
    "      - Multi-Step Tasks (Ralph Wiggum Loop)\n"
    "      - Enhanced CEO Briefings (email stats, health, metrics)\n"
    "      - Local-first, human-in-the-loop, security-first"
)

print("""
    ============================================================
    |                                                          |
    |       Thank you!                                         |
    |                                                          |
    |       GitHub: github.com/Shaistatosif/-ai-employee       |
    |       Live Demo: ai-employee-system.vercel.app           |
    |                                                          |
    |       Author: Shaista Tosif                              |
    |       AI: Claude Opus 4.6                                |
    |                                                          |
    ============================================================
""")

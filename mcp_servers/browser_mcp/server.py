"""
Vault MCP Server for Personal AI Employee System.

Provides tools for Claude Desktop/Code to manage the AI Employee vault:
- list_tasks: List tasks by folder/status
- get_task: Read a specific task file
- approve_task: Move a task from Pending_Approval to Approved
- create_task: Create a new task in Needs_Action
- get_dashboard: Read the current dashboard
- get_system_status: Get orchestrator status
- force_briefing: Generate a CEO briefing on demand
- list_multistep_tasks: List active multi-step tasks

Run with: python -m mcp_servers.browser_mcp.server
"""

import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import settings

logger = logging.getLogger(__name__)

# Create the MCP server
mcp = FastMCP(
    "AI Employee - Vault Manager",
    version="1.0.0",
)


def _read_task_summary(path: Path) -> dict:
    """Read a task file and return a summary."""
    try:
        content = path.read_text(encoding="utf-8")
        summary = {
            "name": path.stem,
            "path": str(path),
            "folder": path.parent.name,
            "size": len(content),
        }

        # Parse YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                import yaml

                try:
                    fm = yaml.safe_load(parts[1])
                    if fm:
                        summary.update(
                            {
                                "title": fm.get("title", path.stem),
                                "priority": fm.get("priority", "normal"),
                                "source": fm.get("source", "unknown"),
                                "status": fm.get("status", "unknown"),
                                "created": fm.get("created", ""),
                            }
                        )
                except Exception:
                    pass

        return summary
    except Exception as e:
        return {"name": path.stem, "error": str(e)}


@mcp.tool()
def list_tasks(
    folder: str = "all",
    limit: int = 20,
) -> str:
    """
    List tasks in the AI Employee vault.

    Args:
        folder: Which folder to list. Options: 'all', 'inbox', 'needs_action',
                'pending_approval', 'approved', 'done'
        limit: Maximum number of tasks to list (default 20)

    Returns:
        Formatted list of tasks with status and metadata
    """
    folder_map = {
        "inbox": settings.vault_path / "Inbox",
        "needs_action": settings.needs_action_path,
        "pending_approval": settings.pending_approval_path,
        "approved": settings.approved_path,
        "done": settings.done_path,
    }

    if folder == "all":
        folders_to_check = folder_map
    elif folder in folder_map:
        folders_to_check = {folder: folder_map[folder]}
    else:
        return f"Unknown folder '{folder}'. Options: all, inbox, needs_action, pending_approval, approved, done"

    all_tasks = []
    for fname, fpath in folders_to_check.items():
        if not fpath.exists():
            continue
        for f in fpath.glob("*.md"):
            if "_plan_" in f.name:
                continue
            summary = _read_task_summary(f)
            summary["folder"] = fname
            all_tasks.append(summary)

    # Sort by most recent
    all_tasks.sort(
        key=lambda x: x.get("created", "") or x.get("name", ""),
        reverse=True,
    )
    all_tasks = all_tasks[:limit]

    if not all_tasks:
        return f"No tasks found in {folder}."

    # Count by folder
    counts = {}
    for t in all_tasks:
        counts[t["folder"]] = counts.get(t["folder"], 0) + 1

    lines = [f"Tasks ({len(all_tasks)} total):\n"]

    # Summary
    for fname, count in counts.items():
        lines.append(f"  {fname}: {count}")
    lines.append("")

    # Details
    for t in all_tasks:
        title = t.get("title", t["name"])
        priority = t.get("priority", "")
        priority_icon = {"high": "!!!", "normal": "", "low": "."}.get(priority, "")
        lines.append(
            f"  [{t['folder']}] {priority_icon} {title}"
        )

    return "\n".join(lines)


@mcp.tool()
def get_task(task_name: str) -> str:
    """
    Read the full content of a specific task file.

    Searches across all vault folders for the task.

    Args:
        task_name: Task filename (with or without .md extension)

    Returns:
        Full content of the task file
    """
    if not task_name.endswith(".md"):
        task_name += ".md"

    # Search all folders
    search_folders = [
        settings.needs_action_path,
        settings.pending_approval_path,
        settings.approved_path,
        settings.done_path,
        settings.vault_path / "Inbox",
    ]

    for folder in search_folders:
        task_path = folder / task_name
        if task_path.exists():
            content = task_path.read_text(encoding="utf-8")
            return f"[{folder.name}/{task_name}]\n\n{content}"

    # Try partial match
    for folder in search_folders:
        for f in folder.glob("*.md"):
            if task_name.replace(".md", "").lower() in f.name.lower():
                content = f.read_text(encoding="utf-8")
                return f"[{folder.name}/{f.name}]\n\n{content}"

    return f"Task '{task_name}' not found in any folder."


@mcp.tool()
def approve_task(task_name: str) -> str:
    """
    Approve a task by moving it from Pending_Approval to Approved.

    This triggers the approval handler to execute the task.
    IMPORTANT: Only use this after reviewing the task content.

    Args:
        task_name: Task filename (with or without .md extension)

    Returns:
        Confirmation message
    """
    if not task_name.endswith(".md"):
        task_name += ".md"

    source = settings.pending_approval_path / task_name
    destination = settings.approved_path / task_name

    if not source.exists():
        # Try partial match
        matches = [
            f
            for f in settings.pending_approval_path.glob("*.md")
            if task_name.replace(".md", "").lower() in f.name.lower()
            and "_plan_" not in f.name
        ]
        if matches:
            source = matches[0]
            destination = settings.approved_path / source.name
        else:
            return f"Task '{task_name}' not found in Pending_Approval folder."

    try:
        shutil.move(str(source), str(destination))

        # Also move associated plan file if exists
        plan_name = source.stem.replace("completed_", "plan_")
        for plan_file in settings.pending_approval_path.glob(f"*plan*{source.stem}*"):
            plan_dest = settings.approved_path / plan_file.name
            shutil.move(str(plan_file), str(plan_dest))

        from config.database import log_action

        log_action(
            action_type="mcp_task_approved",
            target=str(destination),
            parameters={"task_name": source.name},
            result="success",
        )

        return (
            f"Task approved!\n"
            f"  Moved: {source.name}\n"
            f"  From: Pending_Approval/\n"
            f"  To: Approved/\n"
            f"  The approval handler will execute this task."
        )

    except Exception as e:
        return f"Failed to approve task: {str(e)}"


@mcp.tool()
def reject_task(task_name: str, reason: str = "Rejected by user") -> str:
    """
    Reject a task by moving it from Pending_Approval to Done with rejection note.

    Args:
        task_name: Task filename (with or without .md extension)
        reason: Reason for rejection

    Returns:
        Confirmation message
    """
    if not task_name.endswith(".md"):
        task_name += ".md"

    source = settings.pending_approval_path / task_name

    if not source.exists():
        matches = [
            f
            for f in settings.pending_approval_path.glob("*.md")
            if task_name.replace(".md", "").lower() in f.name.lower()
            and "_plan_" not in f.name
        ]
        if matches:
            source = matches[0]
        else:
            return f"Task '{task_name}' not found in Pending_Approval folder."

    try:
        now = datetime.now()
        done_name = f"{now.strftime('%Y%m%d_%H%M%S')}_rejected_{source.name}"
        destination = settings.done_path / done_name

        # Add rejection note to file
        content = source.read_text(encoding="utf-8")
        content += f"\n\n---\n\n## Rejected\n\n**Date**: {now.isoformat()}\n**Reason**: {reason}\n"
        destination.write_text(content, encoding="utf-8")
        source.unlink()

        from config.database import log_action

        log_action(
            action_type="mcp_task_rejected",
            target=str(destination),
            parameters={"task_name": source.name, "reason": reason},
            result="success",
        )

        return f"Task rejected:\n  {source.name}\n  Reason: {reason}\n  Moved to: Done/"

    except Exception as e:
        return f"Failed to reject task: {str(e)}"


@mcp.tool()
def create_task(
    title: str,
    content: str,
    priority: str = "normal",
    task_type: str = "general",
) -> str:
    """
    Create a new task in the Needs_Action folder.

    The task will be picked up by the workflow engine, classified by HITL,
    and routed to either auto-approval or human review.

    Args:
        title: Task title
        content: Task description and details
        priority: Priority level ('high', 'normal', 'low')
        task_type: Task type ('general', 'email_send', 'linkedin_post', etc.)

    Returns:
        Path to the created task file
    """
    now = datetime.now()
    safe_title = "".join(
        c if c.isalnum() or c in "-_ " else "_" for c in title
    )[:50].strip()
    filename = f"{now.strftime('%Y%m%d_%H%M%S')}_{safe_title}.md"
    task_path = settings.needs_action_path / filename

    safe_yaml_title = title.replace("'", "''")

    task_content = f"""---
title: '{safe_yaml_title}'
source: 'MCP: Vault Manager'
priority: {priority}
created: '{now.isoformat()}'
type: '{task_type}'
watcher: MCP Server
status: pending
---

# {title}

## Source
MCP: Vault Manager (created via Claude)

## Priority
{priority}

## Content

{content}

## Metadata
- **type**: {task_type}
- **created_via**: MCP Server

---

## Action Required

*The workflow engine will analyze and route this task.*
"""

    task_path.write_text(task_content, encoding="utf-8")

    from config.database import log_action

    log_action(
        action_type="mcp_task_created",
        target=str(task_path),
        parameters={"title": title, "priority": priority, "type": task_type},
        result="success",
    )

    return (
        f"Task created:\n"
        f"  Path: {task_path}\n"
        f"  Title: {title}\n"
        f"  Priority: {priority}\n"
        f"  Type: {task_type}\n\n"
        f"The workflow engine will process it on the next cycle."
    )


@mcp.tool()
def get_dashboard() -> str:
    """
    Read the current AI Employee Dashboard.

    Returns:
        Dashboard content (markdown)
    """
    dashboard_path = settings.vault_path / "Dashboard.md"

    if not dashboard_path.exists():
        return "Dashboard.md not found. The system may not be running."

    return dashboard_path.read_text(encoding="utf-8")


@mcp.tool()
def get_system_status() -> str:
    """
    Get a summary of system status including task counts and folder contents.

    Returns:
        System status summary
    """
    folders = {
        "Inbox": settings.vault_path / "Inbox",
        "Needs_Action": settings.needs_action_path,
        "Pending_Approval": settings.pending_approval_path,
        "Approved": settings.approved_path,
        "Done": settings.done_path,
    }

    lines = ["AI Employee System Status\n"]
    lines.append(f"  Vault: {settings.vault_path}")
    lines.append(f"  Mode: {'DRY RUN' if settings.dry_run else 'LIVE'}")
    lines.append(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    total = 0
    for name, path in folders.items():
        if path.exists():
            count = len([
                f for f in path.glob("*.md")
                if "_plan_" not in f.name
            ])
            total += count
            icon = {
                "Inbox": "📥",
                "Needs_Action": "📋",
                "Pending_Approval": "⏳",
                "Approved": "✅",
                "Done": "✔️",
            }.get(name, "📁")
            lines.append(f"  {icon} {name}: {count} task(s)")
        else:
            lines.append(f"  ❌ {name}: folder not found")

    lines.append(f"\n  Total: {total} task(s)")

    # Check for drafts
    drafts_path = settings.vault_path / "Drafts"
    if drafts_path.exists():
        draft_count = len(list(drafts_path.rglob("*.md")))
        lines.append(f"  📝 Drafts: {draft_count}")

    # Check for briefings
    if settings.briefings_path.exists():
        briefing_count = len(list(settings.briefings_path.glob("*.md")))
        lines.append(f"  📊 Briefings: {briefing_count}")

    # Check multi-step tasks
    if settings.multistep_path.exists():
        ms_count = len(list(settings.multistep_path.glob("*.yaml")))
        lines.append(f"  🔄 Multi-step tasks: {ms_count}")

    return "\n".join(lines)


@mcp.tool()
def force_briefing() -> str:
    """
    Generate a CEO briefing report on demand.

    Creates a weekly-style briefing in the Briefings folder.

    Returns:
        Path to the generated briefing file
    """
    try:
        from orchestrator.scheduler import WeeklyBriefingGenerator

        generator = WeeklyBriefingGenerator()
        briefing_path = generator.force_generate()
        return f"Briefing generated:\n  Path: {briefing_path}\n\nOpen the file to review."

    except Exception as e:
        return f"Failed to generate briefing: {str(e)}"


@mcp.tool()
def list_multistep_tasks() -> str:
    """
    List active multi-step tasks (Ralph Wiggum Loop).

    Returns:
        List of active multi-step tasks with progress
    """
    import yaml

    if not settings.multistep_path.exists():
        return "No multi-step tasks found."

    tasks = []
    for f in settings.multistep_path.glob("*.yaml"):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if data:
                tasks.append(data)
        except Exception:
            continue

    if not tasks:
        return "No multi-step tasks found."

    lines = [f"Multi-Step Tasks ({len(tasks)}):\n"]
    for t in tasks:
        steps = t.get("steps", [])
        completed = sum(1 for s in steps if s.get("status") == "completed")
        status = t.get("status", "unknown")
        status_icon = {
            "completed": "✅",
            "in_progress": "🔄",
            "paused": "⏸️",
            "pending": "⏳",
            "failed": "❌",
        }.get(status, "❓")

        lines.append(f"  {status_icon} {t.get('title', 'Unknown')}")
        lines.append(f"    ID: {t.get('id', '?')}")
        lines.append(f"    Progress: {completed}/{len(steps)} steps")
        lines.append(f"    Status: {status}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()

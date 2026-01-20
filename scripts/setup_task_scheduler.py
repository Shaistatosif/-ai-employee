"""
Windows Task Scheduler setup script for Personal AI Employee System.

Creates scheduled tasks to run the orchestrator automatically.
"""

import os
import sys
import subprocess
from pathlib import Path


def get_python_path() -> str:
    """Get the path to the Python executable."""
    return sys.executable


def get_project_path() -> Path:
    """Get the project root path."""
    return Path(__file__).parent.parent.resolve()


def create_task_xml(task_name: str, description: str, script_path: str,
                    trigger_type: str = "startup", interval_minutes: int = 0) -> str:
    """
    Generate Task Scheduler XML configuration.

    Args:
        task_name: Name of the scheduled task
        description: Task description
        script_path: Path to the Python script to run
        trigger_type: "startup" for on-logon, "interval" for recurring
        interval_minutes: Minutes between runs (for interval type)
    """
    python_path = get_python_path()
    project_path = get_project_path()

    # Base trigger - run on user logon
    if trigger_type == "startup":
        trigger_xml = """
      <LogonTrigger>
        <Enabled>true</Enabled>
      </LogonTrigger>"""
    else:
        # Interval-based trigger (runs repeatedly)
        trigger_xml = f"""
      <TimeTrigger>
        <Repetition>
          <Interval>PT{interval_minutes}M</Interval>
          <StopAtDurationEnd>false</StopAtDurationEnd>
        </Repetition>
        <StartBoundary>2024-01-01T00:00:00</StartBoundary>
        <Enabled>true</Enabled>
      </TimeTrigger>"""

    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>{description}</Description>
    <Author>AI Employee System</Author>
  </RegistrationInfo>
  <Triggers>{trigger_xml}
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT5M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>"{python_path}"</Command>
      <Arguments>"{script_path}"</Arguments>
      <WorkingDirectory>{project_path}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""


def create_scheduled_task(task_name: str, xml_content: str) -> bool:
    """
    Create a Windows scheduled task using schtasks.

    Args:
        task_name: Name for the task
        xml_content: Task XML configuration

    Returns:
        True if successful
    """
    # Save XML to temp file
    temp_xml = Path(os.environ.get("TEMP", ".")) / f"{task_name}.xml"
    temp_xml.write_text(xml_content, encoding="utf-16")

    try:
        # Create the task
        result = subprocess.run(
            ["schtasks", "/Create", "/TN", task_name, "/XML", str(temp_xml), "/F"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print(f"✅ Created task: {task_name}")
            return True
        else:
            print(f"❌ Failed to create task: {task_name}")
            print(f"   Error: {result.stderr}")
            return False
    finally:
        # Clean up temp file
        if temp_xml.exists():
            temp_xml.unlink()


def delete_scheduled_task(task_name: str) -> bool:
    """Delete a Windows scheduled task."""
    result = subprocess.run(
        ["schtasks", "/Delete", "/TN", task_name, "/F"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def list_ai_employee_tasks() -> list[str]:
    """List all AI Employee System scheduled tasks."""
    result = subprocess.run(
        ["schtasks", "/Query", "/FO", "LIST"],
        capture_output=True,
        text=True,
    )

    tasks = []
    for line in result.stdout.split("\n"):
        if "AI_Employee" in line:
            task_name = line.split(":")[-1].strip()
            tasks.append(task_name)
    return tasks


def setup_orchestrator_task() -> bool:
    """Create task to run orchestrator on startup."""
    project_path = get_project_path()
    main_script = project_path / "main.py"

    xml = create_task_xml(
        task_name="AI_Employee_Orchestrator",
        description="Runs the Personal AI Employee System orchestrator on user logon",
        script_path=str(main_script),
        trigger_type="startup",
    )

    return create_scheduled_task("AI_Employee_Orchestrator", xml)


def setup_health_check_task() -> bool:
    """Create task to run health check every 15 minutes."""
    project_path = get_project_path()
    health_script = project_path / "scripts" / "health_check.py"

    # Create health check script if it doesn't exist
    if not health_script.exists():
        health_script.write_text('''"""
Health check script for AI Employee System.
Verifies system is running and alerts if not.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import settings


def check_health():
    """Check if the system is healthy."""
    issues = []

    # Check vault exists
    if not settings.vault_path.exists():
        issues.append("Vault path does not exist")

    # Check required folders
    required_folders = [
        settings.needs_action_path,
        settings.pending_approval_path,
        settings.approved_path,
        settings.done_path,
    ]
    for folder in required_folders:
        if not folder.exists():
            issues.append(f"Missing folder: {folder.name}")

    # Check for stale tasks (>2 days old in Pending_Approval)
    import datetime
    for task in settings.pending_approval_path.glob("*.md"):
        age = datetime.datetime.now() - datetime.datetime.fromtimestamp(task.stat().st_mtime)
        if age.days > 2:
            issues.append(f"Stale task: {task.name} ({age.days} days old)")

    if issues:
        print("Health Check FAILED:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("Health Check PASSED")
        return True


if __name__ == "__main__":
    success = check_health()
    sys.exit(0 if success else 1)
''', encoding="utf-8")
        print(f"Created health check script: {health_script}")

    xml = create_task_xml(
        task_name="AI_Employee_Health_Check",
        description="Runs health check for AI Employee System every 15 minutes",
        script_path=str(health_script),
        trigger_type="interval",
        interval_minutes=15,
    )

    return create_scheduled_task("AI_Employee_Health_Check", xml)


def main():
    """Main setup function."""
    print("=" * 60)
    print("Personal AI Employee System - Task Scheduler Setup")
    print("=" * 60)
    print()

    if sys.platform != "win32":
        print("❌ This script is for Windows only.")
        print("   For Linux/macOS, use cron or systemd instead.")
        print()
        print("   Example cron entry (run every 15 min):")
        print("   */15 * * * * cd /path/to/project && python main.py")
        return

    print("This will create the following scheduled tasks:")
    print()
    print("1. AI_Employee_Orchestrator")
    print("   - Runs on user logon")
    print("   - Starts the main orchestrator")
    print("   - Auto-restarts on failure (3 attempts)")
    print()
    print("2. AI_Employee_Health_Check")
    print("   - Runs every 15 minutes")
    print("   - Checks system health")
    print("   - Reports stale tasks")
    print()

    response = input("Proceed with setup? [y/N]: ").strip().lower()
    if response != "y":
        print("Setup cancelled.")
        return

    print()
    print("Creating scheduled tasks...")
    print()

    # Create tasks
    success = True
    success = setup_orchestrator_task() and success
    success = setup_health_check_task() and success

    print()
    if success:
        print("=" * 60)
        print("✅ Setup complete!")
        print()
        print("To manage tasks, use Task Scheduler or these commands:")
        print("  - View: schtasks /Query /TN AI_Employee_Orchestrator")
        print("  - Run now: schtasks /Run /TN AI_Employee_Orchestrator")
        print("  - Disable: schtasks /Change /TN AI_Employee_Orchestrator /Disable")
        print("  - Delete: schtasks /Delete /TN AI_Employee_Orchestrator /F")
        print("=" * 60)
    else:
        print("⚠️ Some tasks failed to create. Check errors above.")


def uninstall():
    """Remove all AI Employee scheduled tasks."""
    print("Removing AI Employee scheduled tasks...")

    tasks = ["AI_Employee_Orchestrator", "AI_Employee_Health_Check"]
    for task in tasks:
        if delete_scheduled_task(task):
            print(f"✅ Deleted: {task}")
        else:
            print(f"⚠️ Could not delete: {task} (may not exist)")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Setup Windows Task Scheduler for AI Employee System")
    parser.add_argument("--uninstall", action="store_true", help="Remove scheduled tasks")

    args = parser.parse_args()

    if args.uninstall:
        uninstall()
    else:
        main()

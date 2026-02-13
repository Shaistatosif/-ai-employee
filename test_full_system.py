"""
Full System Verification Test for Personal AI Employee System.
Tests all Gold Tier components without needing external API keys.

Run: python test_full_system.py
"""

import sys
import io
import os

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

os.chdir(os.path.dirname(os.path.abspath(__file__)))

passed = 0
failed = 0
total = 0

def test(name, func):
    global passed, failed, total
    total += 1
    try:
        result = func()
        if result:
            passed += 1
            print(f"  [PASS] {name}")
        else:
            failed += 1
            print(f"  [FAIL] {name} - returned False")
    except Exception as e:
        failed += 1
        print(f"  [FAIL] {name} - {e}")


# ============================================================
# 1. CONFIG
# ============================================================
print("\n" + "="*60)
print("  1. CONFIGURATION")
print("="*60)

def test_config_loads():
    from config.config import settings
    return settings.vault_path is not None

def test_config_paths():
    from config.config import settings
    paths = [
        settings.needs_action_path,
        settings.plans_path,
        settings.pending_approval_path,
        settings.approved_path,
        settings.done_path,
        settings.logs_path,
        settings.briefings_path,
        settings.drafts_path,
        settings.multistep_path,
    ]
    return all(p is not None for p in paths)

def test_config_ensure_dirs():
    from config.config import settings
    settings.ensure_directories()
    return settings.vault_path.exists()

def test_config_validators():
    from config.config import settings
    return settings.log_level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

def test_config_optional_services():
    from config.config import settings
    return isinstance(settings.is_gmail_configured(), bool) and \
           isinstance(settings.is_whatsapp_configured(), bool) and \
           isinstance(settings.is_odoo_configured(), bool)

test("Config loads", test_config_loads)
test("Config paths exist", test_config_paths)
test("Ensure directories", test_config_ensure_dirs)
test("Config validators", test_config_validators)
test("Optional service checks", test_config_optional_services)


# ============================================================
# 2. DATABASE MODULE
# ============================================================
print("\n" + "="*60)
print("  2. DATABASE MODULE")
print("="*60)

def test_database_import():
    from config.database import log_action
    return callable(log_action)

def test_database_log_action():
    from config.database import log_action
    log_action("test", "test_target", {"key": "val"}, "ok")
    return True

test("Database import", test_database_import)
test("Log action (no DB)", test_database_log_action)


# ============================================================
# 3. WORKFLOW - HITL
# ============================================================
print("\n" + "="*60)
print("  3. WORKFLOW - HITL CLASSIFICATION")
print("="*60)

def test_hitl_import():
    from workflow.hitl import HITLClassifier, HITLDecision
    return True

def test_hitl_low_risk():
    from workflow.hitl import HITLClassifier
    c = HITLClassifier()
    result = c.classify("Read the quarterly report file")
    # HITLDecision is a dataclass, use attribute access
    return result.risk_level == "low" and result.requires_approval == False

def test_hitl_high_risk_payment():
    from workflow.hitl import HITLClassifier
    c = HITLClassifier()
    result = c.classify("Pay $500 to vendor ABC for services")
    return result.risk_level == "high" and result.requires_approval == True

def test_hitl_high_risk_delete():
    from workflow.hitl import HITLClassifier
    c = HITLClassifier()
    result = c.classify("Delete all old backup files")
    return result.risk_level == "high" and result.requires_approval == True

def test_hitl_high_risk_email():
    from workflow.hitl import HITLClassifier
    c = HITLClassifier()
    # Real emails always have source + recipient metadata from the email watcher
    result = c.classify(
        "Send email to unknown@external.com with report",
        metadata={"source": "gmail", "to": "unknown@external.com"}
    )
    return result.requires_approval == True

test("HITL import", test_hitl_import)
test("HITL low risk (read file)", test_hitl_low_risk)
test("HITL high risk (payment >$50)", test_hitl_high_risk_payment)
test("HITL high risk (delete)", test_hitl_high_risk_delete)
test("HITL high risk (email)", test_hitl_high_risk_email)


# ============================================================
# 4. ACTIONS
# ============================================================
print("\n" + "="*60)
print("  4. ACTIONS (All 9 Handlers)")
print("="*60)

def test_action_executor_import():
    from actions.executor import ActionExecutor
    return True

def test_action_executor_count():
    from actions.executor import ActionExecutor
    e = ActionExecutor()
    actions = e.get_available_actions()
    return len(actions) == 9

def test_action_names():
    from actions.executor import ActionExecutor
    e = ActionExecutor()
    names = e.get_available_actions()
    expected = [
        "email_send", "email_draft", "linkedin_draft",
        "facebook_draft", "instagram_draft", "twitter_draft",
        "odoo_invoice", "odoo_expense", "general"
    ]
    return all(n in names for n in expected)

def test_email_action():
    from actions.email_action import EmailAction
    a = EmailAction()
    return a.can_handle({"type": "send_email", "to": "test@test.com"})

def test_linkedin_action():
    from actions.linkedin_action import LinkedInDraftAction
    a = LinkedInDraftAction()
    return a.can_handle({"type": "linkedin_post", "body": "Test post"})

def test_facebook_action():
    from actions.social_action import FacebookDraftAction
    a = FacebookDraftAction()
    return a.can_handle({"type": "facebook_post", "body": "Test post"})

def test_instagram_action():
    from actions.social_action import InstagramDraftAction
    a = InstagramDraftAction()
    return a.can_handle({"type": "instagram_post", "body": "Test post"})

def test_twitter_action():
    from actions.social_action import TwitterDraftAction
    a = TwitterDraftAction()
    return a.can_handle({"type": "twitter_post", "body": "Test post"})

def test_odoo_invoice_action():
    from actions.odoo_action import OdooInvoiceAction
    a = OdooInvoiceAction()
    return a.can_handle({"type": "create_invoice", "body": "Invoice for services"})

def test_odoo_expense_action():
    from actions.odoo_action import OdooExpenseAction
    a = OdooExpenseAction()
    return a.can_handle({"type": "log_expense", "body": "Office supplies"})

def test_general_action():
    from actions.general_action import GeneralAction
    a = GeneralAction()
    return a.can_handle({"type": "anything", "body": "some task"})

test("ActionExecutor import", test_action_executor_import)
test("9 action handlers registered", test_action_executor_count)
test("All action names correct", test_action_names)
test("EmailAction can_handle", test_email_action)
test("LinkedInDraftAction can_handle", test_linkedin_action)
test("FacebookDraftAction can_handle", test_facebook_action)
test("InstagramDraftAction can_handle", test_instagram_action)
test("TwitterDraftAction can_handle", test_twitter_action)
test("OdooInvoiceAction can_handle", test_odoo_invoice_action)
test("OdooExpenseAction can_handle", test_odoo_expense_action)
test("GeneralAction can_handle", test_general_action)


# ============================================================
# 5. WATCHERS
# ============================================================
print("\n" + "="*60)
print("  5. WATCHERS")
print("="*60)

def test_filesystem_watcher():
    from watchers.filesystem_watcher import FilesystemWatcher
    return True

def test_gmail_watcher():
    from watchers.gmail_watcher import GmailWatcher
    return True

def test_whatsapp_watcher():
    from watchers.whatsapp_watcher import WhatsAppWatcher
    return True

def test_watcher_exports():
    from watchers import FilesystemWatcher, GmailWatcher, WhatsAppWatcher
    return True

test("FilesystemWatcher import", test_filesystem_watcher)
test("GmailWatcher import", test_gmail_watcher)
test("WhatsAppWatcher import", test_whatsapp_watcher)
test("All watchers exportable", test_watcher_exports)


# ============================================================
# 6. ORCHESTRATOR
# ============================================================
print("\n" + "="*60)
print("  6. ORCHESTRATOR")
print("="*60)

def test_orchestrator_import():
    from orchestrator import Orchestrator
    return True

def test_watchdog_import():
    from orchestrator.watchdog import WatchdogMonitor
    return True

def test_ralph_loop_import():
    from orchestrator.ralph_loop import RalphWiggumLoop, MultiStepTask, TaskStep
    return True

def test_orchestrator_setup():
    from orchestrator import Orchestrator
    o = Orchestrator()
    o.setup()
    status = o.get_status()
    # Check key fields in status
    return "is_running" in status and "watchers" in status and "watchdog" in status

def test_watchdog_standalone():
    from orchestrator.watchdog import WatchdogMonitor
    w = WatchdogMonitor([])
    status = w.get_status()
    return "watchers_healthy" in status and "is_running" in status

def test_ralph_loop_create():
    from orchestrator.ralph_loop import RalphWiggumLoop
    r = RalphWiggumLoop()
    # create_task takes steps as list of dicts
    steps = [
        {"name": "Step 1", "action": "analyze"},
        {"name": "Step 2", "action": "report"},
    ]
    task = r.create_task("Test Multi-Step", steps)
    return task is not None and task.status == "pending" and len(task.steps) == 2

def test_ralph_loop_active():
    from orchestrator.ralph_loop import RalphWiggumLoop
    r = RalphWiggumLoop()
    tasks = r.get_active_tasks()
    return isinstance(tasks, list)

test("Orchestrator import", test_orchestrator_import)
test("WatchdogMonitor import", test_watchdog_import)
test("RalphWiggumLoop import", test_ralph_loop_import)
test("Orchestrator setup + status", test_orchestrator_setup)
test("Watchdog standalone", test_watchdog_standalone)
test("Ralph Loop create task", test_ralph_loop_create)
test("Ralph Loop active tasks", test_ralph_loop_active)


# ============================================================
# 7. SCHEDULER
# ============================================================
print("\n" + "="*60)
print("  7. SCHEDULER")
print("="*60)

def test_scheduler_import():
    from orchestrator.scheduler import Scheduler, WeeklyBriefingGenerator
    return True

def test_briefing_force_generate():
    from orchestrator.scheduler import WeeklyBriefingGenerator
    # WeeklyBriefingGenerator takes orchestrator=None by default
    b = WeeklyBriefingGenerator()
    path = b.force_generate()
    return path is not None and path.exists()

test("Scheduler import", test_scheduler_import)
test("Force generate briefing", test_briefing_force_generate)


# ============================================================
# 8. TASK PROCESSOR
# ============================================================
print("\n" + "="*60)
print("  8. TASK PROCESSOR")
print("="*60)

def test_task_processor():
    from workflow.task_processor import TaskProcessor
    return True

def test_approval_handler():
    from workflow.approval_handler import ApprovalHandler
    return True

test("TaskProcessor import", test_task_processor)
test("ApprovalHandler import", test_approval_handler)


# ============================================================
# 9. WEB APP
# ============================================================
print("\n" + "="*60)
print("  9. WEB APP (FastAPI)")
print("="*60)

def test_web_app_import():
    from web_app import app, classify_task
    return True

def test_classify_low():
    from web_app import classify_task
    result = classify_task("Read quarterly report")
    return result["risk_level"] == "LOW" and result["requires_approval"] == False

def test_classify_high_payment():
    from web_app import classify_task
    result = classify_task("Pay $200 to vendor")
    return result["risk_level"] == "HIGH" and result["requires_approval"] == True

def test_classify_high_delete():
    from web_app import classify_task
    result = classify_task("Delete all backup files")
    return result["risk_level"] == "HIGH" and result["requires_approval"] == True

test("Web app import", test_web_app_import)
test("Web classify low risk", test_classify_low)
test("Web classify high (payment)", test_classify_high_payment)
test("Web classify high (delete)", test_classify_high_delete)


# ============================================================
# 10. END-TO-END: DROP FILE IN INBOX
# ============================================================
print("\n" + "="*60)
print("  10. END-TO-END: File Drop Simulation")
print("="*60)

def test_e2e_file_drop():
    """Simulate dropping a file in Inbox and processing it."""
    from config.config import settings
    from workflow.hitl import HITLClassifier

    settings.ensure_directories()
    inbox = settings.vault_path / "Inbox"
    inbox.mkdir(parents=True, exist_ok=True)

    # 1. Create test file in Inbox
    test_file = inbox / "e2e_test_verification.txt"
    test_file.write_text("Read and summarize the monthly report", encoding="utf-8")

    # 2. Classify it
    classifier = HITLClassifier()
    content = test_file.read_text(encoding="utf-8")
    classification = classifier.classify(content)

    # 3. Verify low-risk = auto-approve (attribute access, not dict)
    assert classification.requires_approval == False, f"Expected auto-approve, got {classification}"

    # 4. Clean up test file
    test_file.unlink(missing_ok=True)

    return True

def test_e2e_high_risk():
    """Simulate a high-risk task that needs approval."""
    from workflow.hitl import HITLClassifier

    classifier = HITLClassifier()
    result = classifier.classify("Pay $999 to external vendor for premium services")

    assert result.requires_approval == True, f"Expected approval required, got {result}"
    assert result.risk_level == "high"
    return True

def test_e2e_multistep():
    """Create and verify a multi-step task."""
    from orchestrator.ralph_loop import RalphWiggumLoop
    from config.config import settings

    r = RalphWiggumLoop()
    steps = [
        {"name": "Gather data", "action": "read_file"},
        {"name": "Generate report", "action": "create_report"},
        {"name": "Email report", "action": "send_email", "requires_approval": True},
    ]
    task = r.create_task("E2E Quarterly Report Pipeline", steps)

    # Verify task created
    assert task.status == "pending"
    assert len(task.steps) == 3
    assert task.steps[2].requires_approval == True

    # Verify state file persisted
    state_file = settings.multistep_path / f"{task.id}.yaml"
    assert state_file.exists(), f"State file not found: {state_file}"

    return True

def test_e2e_linkedin_draft():
    """Test creating a LinkedIn draft end-to-end."""
    from actions.linkedin_action import LinkedInDraftAction
    from config.config import settings
    from pathlib import Path

    settings.ensure_directories()
    drafts_dir = settings.drafts_path / "LinkedIn"
    drafts_dir.mkdir(parents=True, exist_ok=True)

    action = LinkedInDraftAction()
    task_data = {
        "type": "linkedin_post",
        "body": "Excited to announce our new AI Employee System! #AI #Automation",
        "raw_content": "Create a LinkedIn post about our AI Employee System launch",
    }

    # Create a temp task file
    temp_task = settings.needs_action_path / "test_linkedin.md"
    temp_task.write_text("---\ntype: linkedin_post\n---\nTest LinkedIn post", encoding="utf-8")

    result = action.execute(task_data, temp_task)

    # Clean up
    temp_task.unlink(missing_ok=True)

    return result.status.value == "success"

test("E2E: File drop (low risk auto-approve)", test_e2e_file_drop)
test("E2E: High risk requires approval", test_e2e_high_risk)
test("E2E: Multi-step task persistence", test_e2e_multistep)
test("E2E: LinkedIn draft creation", test_e2e_linkedin_draft)


# ============================================================
# 11. MCP SERVERS
# ============================================================
print("\n" + "="*60)
print("  11. MCP SERVERS")
print("="*60)

def test_email_mcp_import():
    from mcp_servers.email_mcp.server import mcp
    return mcp is not None

def test_vault_mcp_import():
    from mcp_servers.browser_mcp.server import mcp
    return mcp is not None

test("Email MCP server import", test_email_mcp_import)
test("Vault MCP server import", test_vault_mcp_import)


# ============================================================
# 12. FULL ORCHESTRATOR LIFECYCLE
# ============================================================
print("\n" + "="*60)
print("  12. ORCHESTRATOR LIFECYCLE (Setup -> Start -> Status -> Stop)")
print("="*60)

def test_orchestrator_lifecycle():
    """Test full orchestrator lifecycle without blocking."""
    from orchestrator import Orchestrator
    import time

    o = Orchestrator()
    o.setup()

    # Start
    o.start()
    assert o.is_running == True, "Orchestrator should be running"

    # Check status
    status = o.get_status()
    assert status["is_running"] == True
    assert len(status["watchers"]) >= 1  # At least filesystem watcher
    assert status["watchdog"] is not None

    # Brief pause to let threads start
    time.sleep(1)

    # Stop
    o.stop()
    assert o.is_running == False, "Orchestrator should be stopped"

    return True

test("Full lifecycle (setup->start->status->stop)", test_orchestrator_lifecycle)


# ============================================================
# RESULTS
# ============================================================
print("\n" + "="*60)
print(f"  RESULTS: {passed}/{total} passed, {failed} failed")
print("="*60)

if failed == 0:
    print("\n  ALL TESTS PASSED! System is fully operational.\n")
else:
    print(f"\n  {failed} test(s) failed. See above for details.\n")

sys.exit(0 if failed == 0 else 1)

# Presentation Guide - AI Employee System

## Before Demo (2 min setup)

```bash
# Terminal 1: Reset vault for clean demo
python demo_reset.py

# Terminal 1: Start the system
python main.py
```

```bash
# Terminal 2: Run the interactive demo script
python demo_run.py
```

---

## Demo Flow (8-10 minutes)

### 1. Introduction (1 min)
- "This is a Personal AI Employee System"
- "It automates your digital life - files, emails, social media, accounting"
- "Key principle: Human-in-the-Loop - AI only acts autonomously when SAFE"

### 2. Architecture (1 min)
Show the flow:
```
Inbox -> AI Analyzes -> Risk Check -> Auto/Manual -> Done
```
- 3 Watchers: Filesystem, Gmail, WhatsApp
- 9 Action Handlers
- HITL Classification: payments >$50, delete, sensitive = BLOCKED

### 3. Live Demo - Safe Task (1 min)
- Drop `01_safe_task.txt` into Inbox
- Watch terminal: "Auto-approved"
- "See? Safe tasks go through automatically"

### 4. Live Demo - Payment $500 (1 min)
- Drop `02_payment_request.txt` into Inbox
- Watch terminal: "Routed to Pending_Approval"
- "The $500 payment was BLOCKED - needs MY approval"
- Show `Pending_Approval/` folder

### 5. Live Demo - Real Email (2 min)
- Drop `03_send_email.txt` into Inbox
- Watch terminal: "Email sent: [message_id]"
- Open Gmail and show the real email arrived
- "The system sent a REAL email through Gmail API"

### 6. Live Demo - Delete (Dangerous) (1 min)
- Drop `04_delete_sensitive.txt` into Inbox
- Watch terminal: "Routed to Pending_Approval"
- "Delete operations are ALWAYS blocked for safety"

### 7. Gold Tier Features (1 min)
Mention briefly:
- Gmail reads + sends emails (real integration)
- WhatsApp via Twilio
- LinkedIn, Facebook, Instagram, Twitter drafts
- Odoo Community accounting (invoices + expenses)
- Watchdog auto-restarts failed watchers
- Multi-step task persistence (survives restarts)
- 2 MCP Servers with 13 tools for Claude Desktop
- Enhanced weekly CEO briefings

### 8. Conclusion (1 min)
- "Local-first: all data stays on YOUR machine"
- "Human-in-the-loop: AI never acts without permission for risky tasks"
- "Gold Tier complete: all features working"
- Show web demo: https://ai-employee-system.vercel.app

---

## If Sir Asks Questions

**Q: Why local-first and not cloud?**
A: Privacy and control. Your data never leaves your machine. The AI processes everything locally.

**Q: How does HITL classification work?**
A: Rule-based classifier checks for: payment amounts (>$50), delete keywords, sensitive data (passwords, SSN), email to unknown recipients, social media posts. Each gets a risk score.

**Q: What if a watcher crashes?**
A: The Watchdog Monitor checks every 60 seconds. If a watcher dies, it auto-restarts with exponential backoff (1s, 2s, 4s). After 3 failures, it creates an alert for human review.

**Q: Can this handle multi-step tasks?**
A: Yes! The Ralph Wiggum Loop creates multi-step task chains. Each step can require approval. State persists to YAML files, so tasks survive system restarts.

**Q: What's the tech stack?**
A: Python 3.11+, FastAPI, Pydantic, Watchdog, Google Gmail API, Twilio, Odoo XML-RPC, FastMCP, YAML/Markdown vault.

**Q: How many tasks has it processed?**
A: 100+ tasks including real Gmail emails, file processing, and email sending.

---

## Quick Commands

| Command | Purpose |
|---------|---------|
| `python demo_reset.py` | Clean vault for fresh demo |
| `python main.py` | Start the full system |
| `python demo_run.py` | Interactive demo walkthrough |
| `python test_full_system.py` | Run 49 verification tests |
| `python -m uvicorn web_app:app` | Start web demo locally |

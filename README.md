# 🤖 Personal AI Employee System

> **Your life and business on autopilot.** Local-first, human-in-the-loop, AI-powered task automation.

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status: Silver Tier](https://img.shields.io/badge/Status-Silver%20Tier-yellow.svg)](#tier-progress)

---

## ✨ Features

| Feature | Status | Description |
|---------|--------|-------------|
| 📁 **File Watcher** | ✅ Working | Auto-detects files in Inbox folder |
| 🔒 **HITL Approval** | ✅ Working | Human approval for sensitive actions |
| 💰 **Payment Detection** | ✅ Working | Flags payments > $50 for review |
| 📊 **Dashboard** | ✅ Working | Real-time system status in Markdown |
| ⏰ **Scheduler** | ✅ Working | Weekly briefings, hourly updates |
| 📧 **Email Actions** | ✅ Ready | Gmail integration (needs credentials) |
| 🪟 **Windows Support** | ✅ Working | PollingObserver for reliability |

---

## 🚀 Quick Start

### 1. Clone & Setup

```bash
# Clone
git clone https://github.com/Shaistatosif/-ai-employee.git
cd -ai-employee

# Virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Run

```bash
python main.py
```

### 3. Test the Workflow

```bash
# Drop a file in Inbox (new terminal)
echo "Test task for AI" > obsidian_vault/Inbox/test.txt

# Watch the magic happen!
# - File detected → Task created → Auto-processed → Done
```

---

## 🔄 How It Works

```
📥 Inbox          →  📋 Needs_Action  →  📝 Plans
(drop files)         (AI analyzes)       (action plan)
                                              ↓
                                    ┌─────────┴─────────┐
                                    ↓                   ↓
                              ⏳ Pending_Approval    ✅ Approved
                              (risky tasks)         (safe tasks)
                                    ↓                   ↓
                                    └─────────┬─────────┘
                                              ↓
                                         ✔️ Done
                                      (completed)
```

### HITL Decision Logic

| Content | Risk Level | Action |
|---------|------------|--------|
| Read/analyze files | 🟢 Low | Auto-approve |
| Payment < $50 | 🟡 Medium | Auto-approve |
| Payment > $50 | 🔴 High | **Manual approval** |
| Email to unknown | 🔴 High | **Manual approval** |
| Delete files | 🔴 High | **Manual approval** |
| Social media post | 🔴 High | **Manual approval** |

---

## 📁 Project Structure

```
ai-employee/
├── 🧠 orchestrator/
│   ├── main.py              # System coordinator
│   └── scheduler.py         # Weekly briefings, dashboard updates
│
├── 👁️ watchers/
│   ├── filesystem_watcher.py # Monitors Inbox folder
│   └── gmail_watcher.py      # Email monitoring (optional)
│
├── ⚖️ workflow/
│   ├── hitl.py              # Risk classification
│   ├── task_processor.py    # Analyzes tasks, creates plans
│   └── approval_handler.py  # Handles human approval
│
├── ⚡ actions/
│   ├── email_action.py      # Send emails via Gmail
│   └── executor.py          # Coordinates action execution
│
├── 📁 obsidian_vault/       # Your data (Markdown)
│   ├── Dashboard.md         # Live system status
│   ├── Inbox/               # Drop files here
│   ├── Pending_Approval/    # Review these
│   ├── Done/                # Completed tasks
│   └── Logs/                # Action history
│
├── ⚙️ config/
│   └── config.py            # Settings & environment
│
├── main.py                  # Entry point
├── requirements.txt         # Dependencies
└── .env                     # Credentials (not committed)
```

---

## 🎯 Tier Progress

### ✅ Bronze Tier (Complete)
- [x] Obsidian vault with Dashboard
- [x] File watcher (Windows compatible)
- [x] Basic folder workflow
- [x] Configuration management

### ✅ Silver Tier (90% Complete)
- [x] HITL approval workflow
- [x] Risk classification (payments, emails, etc.)
- [x] Scheduler with periodic tasks
- [x] Action executor framework
- [x] Gmail watcher (ready, needs credentials)
- [x] Windows Task Scheduler setup
- [ ] LinkedIn auto-posting

### ⏳ Gold Tier (Future)
- [ ] WhatsApp integration
- [ ] Multiple social platforms
- [ ] Weekly CEO briefings
- [ ] Error recovery system

---

## 🔐 Core Principles

1. **🏠 Local-First** - All data stays on YOUR machine
2. **👤 Human-in-the-Loop** - Sensitive actions need YOUR approval
3. **🔒 Security-First** - Credentials in `.env`, never committed
4. **🤖 Autonomous Where Safe** - AI handles routine tasks automatically

---

## ⚙️ Configuration

Create `.env` file (already gitignored):

```env
# System
VAULT_PATH=./obsidian_vault
DRY_RUN=true
LOG_LEVEL=INFO

# Gmail (optional)
# GMAIL_CLIENT_ID=your_id
# GMAIL_CLIENT_SECRET=your_secret

# Database (optional)
# NEON_DATABASE_URL=postgresql://...
```

---

## 📸 Screenshots

### Dashboard (VS Code / Obsidian)
```
# AI Employee Dashboard

**System Status**: 🟢 Running
**Mode**: 🧪 DRY RUN

| Metric | Value |
|--------|-------|
| Tasks Pending | 0 |
| Awaiting Approval | 0 |
| Completed | 6 |
```

### Console Output
```
============================================================
|         Personal AI Employee System v0.1.0               |
============================================================

INFO - AI Employee System is running!
INFO - Vault: D:\obsidian_vault
INFO - Watchers: 1
INFO - HITL Workflow: Enabled
INFO - Scheduler: Enabled (2 tasks)

INFO - New file detected: payment_request.txt
INFO - Pending approval required (payment > $50)
```

---

## 🛠️ Development

```bash
# Run with verbose logging
python main.py --verbose

# Check system status
python main.py --check

# Setup Windows auto-start
python scripts/setup_task_scheduler.py
```

---

## 📜 License

MIT License - Feel free to use and modify!

---

## 🙏 Credits

Built for the **Personal AI Employee Hackathon 2026**

**Author:** Shaista Tosif
**AI Assistant:** Claude Opus 4.5

---

<p align="center">
  <b>⭐ Star this repo if you find it useful!</b>
</p>

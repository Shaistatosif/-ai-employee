# Personal AI Employee System

> Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop.

## Overview

An autonomous AI assistant that manages personal affairs (Gmail, WhatsApp) and business operations (Social Media, Tasks) 24/7 using Claude Code as the reasoning engine and Obsidian as the management dashboard.

**Current Tier:** Bronze (Minimum Viable)

## Quick Start

### 1. Prerequisites

- Python 3.11+ installed
- Obsidian (optional, for viewing vault)
- Git

### 2. Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd Hackathon-0

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copy environment template
copy .env.example .env    # Windows
cp .env.example .env      # Mac/Linux

# Edit .env with your credentials (optional for Bronze tier)
```

### 4. Gmail Setup (Silver Tier)

To enable Gmail monitoring:

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or select existing)
3. Enable Gmail API:
   - Go to **APIs & Services > Library**
   - Search for "Gmail API"
   - Click **Enable**
4. Create OAuth credentials:
   - Go to **APIs & Services > Credentials**
   - Click **Create Credentials > OAuth client ID**
   - Choose **Desktop application**
   - Download the JSON file
   - Save as `credentials.json` in project root
5. Run setup script:
   ```bash
   python scripts/setup_gmail.py
   ```
6. Authorize in browser when prompted

### 5. Run

```bash
# Check configuration
python main.py --check

# Start the system
python main.py

# Or start in dry-run mode (recommended for testing)
python main.py --dry-run
```

### 6. Test It

1. Drop a text file into `obsidian_vault/Inbox/`
2. Watch the console - a task will be created in `obsidian_vault/Needs_Action/`
3. Open Obsidian vault at `obsidian_vault/` to see the Dashboard

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Watchers      │────▶│  Obsidian Vault │────▶│   Claude Code   │
│ (Gmail, Files)  │     │  (Markdown)     │     │  (Reasoning)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                        │
                               ▼                        ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │  Human Review   │     │   MCP Servers   │
                        │ (Pending_Approval)│    │   (Actions)     │
                        └─────────────────┘     └─────────────────┘
```

## Folder Structure

```
obsidian_vault/
├── Dashboard.md          # System overview
├── Company_Handbook.md   # Rules of engagement
├── Business_Goals.md     # Your objectives
├── Inbox/                # Drop files here for processing
├── Needs_Action/         # Tasks waiting for AI
├── Plans/                # AI-generated action plans
├── Pending_Approval/     # Needs your approval (HITL)
├── Approved/             # Ready for execution
├── Done/                 # Completed tasks
├── Logs/                 # Daily action logs
└── Briefings/            # Weekly CEO reports
```

## Core Principles

1. **Local-First**: All data stays on your machine
2. **Human-in-the-Loop**: Sensitive actions require your approval
3. **Security-First**: Credentials in .env, never committed
4. **Autonomous Where Safe**: AI handles routine tasks automatically

## Security

- All credentials stored in `.env` (never committed)
- `.env` is in `.gitignore` by default
- Audit logging for every action
- DRY_RUN mode for safe testing

## Tier Progress

### Bronze (Complete)
- [x] Obsidian vault with Dashboard.md
- [x] Company_Handbook.md
- [x] Filesystem watcher
- [x] Basic folder structure

### Silver (In Progress)
- [x] Gmail watcher (requires credentials.json)
- [ ] HITL approval workflow
- [ ] MCP server for email
- [ ] Scheduled tasks

### Gold (Future)
- [ ] Multiple watchers
- [ ] Weekly briefings
- [ ] Ralph Wiggum loop
- [ ] Error recovery

## Development

```bash
# Run filesystem watcher only
python -m watchers.filesystem_watcher --poll

# Run with verbose logging
python main.py --verbose

# Check configuration
python main.py --check
```

## Hackathon Submission

- **Tier**: Bronze
- **Repository**: [GitHub URL]
- **Demo Video**: [Link]
- **Security**: Credentials in .env, gitignored

## License

MIT License - See LICENSE file

---

Built for the Personal AI Employee Hackathon 2026

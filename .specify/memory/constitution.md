<!--
SYNC IMPACT REPORT
==================
Version change: 0.0.0 → 1.0.0
Bump rationale: MAJOR - Initial constitution creation with full principle definitions

Modified principles: N/A (initial creation)

Added sections:
- Core Principles (4 principles: Local-First, HITL, Security-First, Autonomous Where Safe)
- Technical Architecture
- Success Criteria (Tiered)
- Security Protocols
- Error Handling
- Governance

Removed sections: N/A (initial creation)

Templates requiring updates:
- .specify/templates/plan-template.md: ✅ Compatible (Constitution Check section aligns)
- .specify/templates/spec-template.md: ✅ Compatible (User stories support HITL workflow)
- .specify/templates/tasks-template.md: ✅ Compatible (Phase structure supports tiered delivery)

Follow-up TODOs:
- TODO(PROJECT_OWNER): Replace "[Your Name]" with actual owner name
- TODO(NEON_SCHEMA): Create database tables per schema in Neon PostgreSQL
-->

# Personal AI Employee System Constitution

## Core Principles

### I. Local-First Architecture

All sensitive data MUST be stored locally in the Obsidian vault (Markdown format). This principle is NON-NEGOTIABLE.

**Requirements:**
- User owns 100% of their data at all times
- No cloud storage for credentials or sensitive information
- Privacy-centric design: data never leaves the local machine without explicit approval
- Obsidian vault serves as the single source of truth for task state

**Rationale:** Local-first architecture ensures user privacy, eliminates vendor lock-in, and maintains data sovereignty. The user can operate fully offline for non-external actions.

### II. Human-in-the-Loop (HITL)

AI MUST NEVER act autonomously on sensitive actions. Human approval is REQUIRED before execution.

**Mandatory Approval Actions:**
- Payments exceeding $50 (all new payments regardless of amount)
- Emails to new/unknown recipients
- Social media posts, replies, and direct messages
- File deletions or moves outside the vault
- Any irreversible external action

**Auto-Approved Actions (Safe Autonomy):**
- Email triage and categorization
- Draft creation (not sending)
- Task prioritization within the vault
- Reading and analyzing data
- Creating files within approved directories

**Workflow:**
1. AI creates action plan in `/Plans/`
2. Sensitive actions → `/Pending_Approval/`
3. Human reviews and moves to `/Approved/`
4. System executes only approved actions
5. Results logged to `/Done/` and Neon database

**Rationale:** Human oversight prevents costly mistakes, maintains trust, and ensures AI operates within user-defined boundaries.

### III. Security-First

All credentials MUST be stored in `.env` files that are NEVER committed to version control.

**Requirements:**
- `.env` MUST be in `.gitignore` before any credential is added
- Audit logging for EVERY action to Neon PostgreSQL database
- DRY_RUN mode MUST be available for all external actions
- Rate limiting on all external API calls
- Credentials rotated monthly (recommended)
- Banking credentials use OS keychain (Windows Credential Manager / macOS Keychain)

**Audit Retention:**
- Minimum 90 days log retention
- Daily 2-minute dashboard review
- Weekly 15-minute action log review
- Monthly 1-hour comprehensive audit

**Rationale:** Security breaches are catastrophic for personal assistant systems handling email, finances, and social accounts. Defense in depth is mandatory.

### IV. Autonomous Where Safe

The system SHOULD automate routine, low-risk tasks to maximize value while respecting HITL boundaries.

**Safe Autonomous Operations:**
- Email triage, categorization, and priority assignment
- Task creation and prioritization
- Weekly business audit generation
- Routine data entry and form filling (read-only sources)
- Dashboard updates and metric calculations
- Briefing document generation

**Explicitly Excluded from Automation:**
- Emotional contexts (condolences, conflicts, sensitive communications)
- Legal matters (contract signing, legal agreements)
- Medical decisions
- Large or unusual financial transactions
- Any irreversible actions

**Rationale:** Automation provides value through consistency and availability (168 hrs/week vs 40 hrs/week). Safe boundaries ensure trust is maintained.

## Technical Architecture

### Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Brain | Claude Code (Sonnet 4) | Reasoning engine and task planning |
| Memory | Obsidian (Markdown) | Dashboard, knowledge base, task state |
| Database | Neon PostgreSQL | Audit logs, structured metrics, email tracking |
| Watchers | Python 3.13+ | Gmail, WhatsApp, filesystem monitoring |
| Actions | MCP Servers (Node.js) | Email sending, browser automation |
| Orchestration | Python orchestrator | Scheduling, coordination, Ralph Wiggum loop |
| Security | .env + python-dotenv | Credential management |

### System Flow

```
External Source (Gmail/WhatsApp/Files)
  → Watcher Script (Python)
    → Creates task.md in /Needs_Action/
      → Claude Code reads vault
        → Creates Plan.md in /Plans/
          → Sensitive? → /Pending_Approval/ (await human)
          → Safe? → Execute directly
            → Human approves → Move to /Approved/
              → MCP Server executes action
                → Log to Neon + move to /Done/
```

### Folder Structure

All operations MUST respect this directory structure:

```
obsidian_vault/
├── Dashboard.md              # Real-time system summary
├── Company_Handbook.md       # Rules of engagement
├── Business_Goals.md         # Objectives and metrics
├── Needs_Action/             # Incoming tasks (watchers write here)
├── Plans/                    # Claude's action plans
├── Pending_Approval/         # HITL queue (human reviews)
├── Approved/                 # Human-approved actions
├── Done/                     # Completed tasks (archived)
├── Logs/                     # Daily action logs
└── Briefings/                # Weekly CEO reports
```

## Success Criteria

### Bronze Tier (Minimum Viable)

- [ ] Obsidian vault with Dashboard.md + Company_Handbook.md
- [ ] One working Watcher (Gmail OR filesystem monitor)
- [ ] Claude Code successfully reads/writes vault
- [ ] Basic folder structure operational
- [ ] All AI functionality as Agent Skills

### Silver Tier (Functional Assistant)

- [ ] 2+ Watchers operational (Gmail + WhatsApp/LinkedIn)
- [ ] Auto-post drafts on LinkedIn for sales generation
- [ ] Claude creates Plan.md files autonomously
- [ ] One MCP server (email sending)
- [ ] HITL approval workflow fully implemented
- [ ] Scheduled tasks via Task Scheduler/cron

### Gold Tier (Autonomous Employee)

- [ ] Full cross-domain integration (Personal + Business)
- [ ] Odoo Community self-hosted accounting
- [ ] Multiple social platforms (Facebook/Instagram + Twitter)
- [ ] Multiple MCP servers operational
- [ ] Weekly CEO Briefing generation
- [ ] Ralph Wiggum loop for multi-step task persistence
- [ ] Error recovery + comprehensive audit logging

### Platinum Tier (Production-Ready)

- [ ] 24/7 cloud deployment (Oracle/AWS VM)
- [ ] Work-zone specialization (Cloud drafts, Local approves)
- [ ] Vault sync via Git/Syncthing
- [ ] Claim-by-move rule for multi-agent coordination
- [ ] Odoo on cloud with HTTPS + automated backups
- [ ] Agent-to-Agent communication (A2A protocol)

## Security Protocols

### Credential Management

| Requirement | Status |
|-------------|--------|
| All secrets in .env | MUST |
| .env in .gitignore | MUST (before first secret) |
| Monthly credential rotation | SHOULD |
| OS keychain for banking | MUST |
| No hardcoded tokens | MUST |

### Approval Thresholds

| Action Type | Auto-Approve | Require Human |
|-------------|--------------|---------------|
| Email replies | Known contacts only | New recipients, bulk sends |
| Payments | < $50 recurring | All new, any > $100 |
| Social posts | Scheduled drafts | Live replies, DMs |
| File operations | Create, read | Delete, move outside vault |

## Error Handling

### Retry Strategy

```python
max_attempts = 3
base_delay = 1  # second
max_delay = 60  # seconds
# Exponential backoff for transient errors
```

### Graceful Degradation

- Gmail API down → Queue emails locally in /Needs_Action/
- Banking timeout → NEVER auto-retry (human must re-initiate)
- Claude unavailable → Watchers continue collecting, queue grows
- Vault locked → Write to temp folder, alert human

### Watchdog Requirements

- Health check every 60 seconds
- Auto-restart crashed watchers (max 3 attempts)
- Alert human on repeated failures
- Health endpoint for external monitoring

## Governance

This constitution is the AUTHORITATIVE source for all development decisions on the Personal AI Employee System.

**Amendment Process:**
1. Propose change with rationale
2. Document in ADR if architecturally significant
3. Update constitution with version increment
4. Propagate changes to dependent templates
5. Commit with `docs: amend constitution to vX.Y.Z`

**Versioning Policy:**
- MAJOR: Principle removal, redefinition, or backward-incompatible governance changes
- MINOR: New principle added, section materially expanded
- PATCH: Clarifications, wording improvements, typo fixes

**Compliance:**
- All PRs MUST verify alignment with constitution principles
- Complexity additions MUST be justified against Principle IV (Autonomous Where Safe)
- Security violations are blocking issues (no exceptions)

**Runtime Guidance:** See `CLAUDE.md` for agent-specific operational guidance.

**Version**: 1.0.0 | **Ratified**: 2026-01-19 | **Last Amended**: 2026-01-19

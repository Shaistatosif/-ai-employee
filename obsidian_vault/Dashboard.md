# AI Employee Dashboard

**Last Updated:** `=date(now)`
**System Status:** OPERATIONAL

---

## Quick Stats

| Metric | Today | This Week |
|--------|-------|-----------|
| Tasks Completed | 0 | 0 |
| Emails Processed | 0 | 0 |
| Pending Approvals | 0 | - |
| Actions Logged | 0 | 0 |

---

## Pending Approvals (HITL Queue)

> Items requiring your review before execution

```dataview
LIST
FROM "Pending_Approval"
SORT file.mtime DESC
```

*No items pending approval*

---

## Recent Activity

### Needs Action
```dataview
TABLE file.mtime as "Created"
FROM "Needs_Action"
SORT file.mtime DESC
LIMIT 5
```

### Recently Completed
```dataview
TABLE file.mtime as "Completed"
FROM "Done"
SORT file.mtime DESC
LIMIT 5
```

---

## System Health

| Component | Status | Last Check |
|-----------|--------|------------|
| Gmail Watcher | Not Started | - |
| Filesystem Watcher | Not Started | - |
| Neon Database | Not Connected | - |
| MCP Servers | Not Started | - |

---

## Today's Priorities

1. [ ] Review pending approvals
2. [ ] Check action logs
3. [ ] Update business goals if needed

---

## Quick Links

- [[Company_Handbook]] - Rules of engagement
- [[Business_Goals]] - Q1 objectives
- [Logs/](Logs/) - Daily action logs
- [Briefings/](Briefings/) - Weekly CEO reports

---

*This dashboard auto-updates when watchers are running. Manual refresh: Close and reopen note.*

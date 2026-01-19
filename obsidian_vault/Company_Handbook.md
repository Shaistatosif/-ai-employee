# Company Handbook

## AI Employee Rules of Engagement

This document defines how your AI Employee operates. All actions MUST comply with these rules.

---

## Core Principles

### 1. You Own Your Data
- All data stays on YOUR machine
- No cloud storage for sensitive information
- You can export/delete everything anytime

### 2. Human Approval Required For
- Payments over $50
- Emails to people not in your contacts
- Social media posts and replies
- Deleting any files
- Any action that can't be undone

### 3. AI Can Act Automatically On
- Reading and organizing emails
- Creating draft responses (not sending)
- Sorting tasks by priority
- Generating reports and briefings
- Updating this dashboard

### 4. Security Rules
- Passwords stored in .env file only
- Every action gets logged
- Test mode available (DRY_RUN)
- Monthly password rotation recommended

---

## How Tasks Flow

```
New Task Arrives (Email/Message/File)
         |
         v
   AI Creates Plan
         |
         v
   Is it sensitive?
    /          \
  YES           NO
   |             |
   v             v
Pending      Execute
Approval     Directly
   |             |
   v             v
You Review   Log Result
   |             |
   v             v
Approve?     Move to Done
   |
  YES
   |
   v
Execute → Log → Done
```

---

## Approval Thresholds

| Action | Auto-OK | Needs Your OK |
|--------|---------|---------------|
| Reply to known contact | Yes | - |
| Email new person | - | Yes |
| Payment < $50 recurring | Yes | - |
| Payment > $50 or new | - | Yes |
| Post scheduled content | Yes | - |
| Reply to comments/DMs | - | Yes |
| Create files | Yes | - |
| Delete files | - | Yes |

---

## Emergency Stop

If something goes wrong:

1. **Quick Stop**: Delete files from `/Approved/` folder
2. **Full Stop**: Close the terminal running the orchestrator
3. **Review**: Check `/Logs/` for what happened
4. **Report**: Log issues for future prevention

---

## Weekly Review Checklist

Every Sunday, AI generates a briefing. You should:

- [ ] Read the weekly briefing (2 min)
- [ ] Review any flagged items
- [ ] Check subscription usage
- [ ] Update business goals if needed
- [ ] Clear old items from Done folder (optional)

---

## Contact Preferences

### Known Contacts (Auto-reply OK)
*Add email addresses of people AI can respond to automatically*

- example@company.com
- team@yourcompany.com

### VIP Contacts (Always notify)
*Add emails where you always want to be notified*

- boss@company.com
- important-client@client.com

### Blocked (Never respond)
*Add emails AI should ignore completely*

- spam@example.com

---

## Business Hours

AI operates 24/7 but respects these preferences:

- **Active Hours**: 9 AM - 6 PM (your timezone)
- **Quiet Hours**: 10 PM - 7 AM
- **During Quiet Hours**: Collect only, no notifications

---

*Last updated: 2026-01-19*
*Review frequency: Monthly or after any incident*

# Email Triage Skill

## Purpose
Categorize and prioritize incoming emails for efficient processing.

## Trigger
New email task appears in `/Needs_Action/`

## Process

1. **Read email metadata**
   - From address
   - Subject line
   - Timestamp
   - Has attachments?

2. **Categorize**
   - URGENT: Contains "urgent", "asap", "emergency", from VIP
   - HIGH: Client emails, invoices, deadlines mentioned
   - NORMAL: Regular correspondence
   - LOW: Newsletters, notifications, automated emails
   - SPAM: Unsubscribe candidates, irrelevant promotions

3. **Determine action**
   - REPLY_NEEDED: Expects response
   - FYI: Information only
   - ACTION_REQUIRED: Task embedded in email
   - ARCHIVE: No action needed

4. **Check HITL requirements**
   - New sender? → Pending Approval
   - Contains request for money? → Pending Approval
   - Emotional content detected? → Pending Approval

5. **Create plan**
   - Draft response if REPLY_NEEDED
   - Extract tasks if ACTION_REQUIRED
   - Move to appropriate folder

## Output
Plan file in `/Plans/` with recommended actions

## Example Plan

```markdown
# Email Plan: Re: Project Proposal

## Classification
- Priority: HIGH
- Category: REPLY_NEEDED
- Sender: client@company.com (Known)

## Recommended Action
Draft reply acknowledging receipt and confirming timeline.

## Draft Response
[Draft content here]

## HITL Required
No - known contact, standard response

## Status
Ready for auto-execution
```

---
name: analyze_blocker
display_name: Analyze Blocker
description: Analyze a blocked task and suggest concrete unblocking steps.
trigger_conditions:
  - event: task_blocked
input_schema:
  task_id:
    type: string
    description: ID of the blocked task
    required: true
---

# Analyze Blocker

When a task is blocked, analyze the situation and propose concrete steps to unblock it.

## Analysis Framework
1. **What's blocked**: Restate the task and its blocker
2. **Root cause**: Why is it actually blocked? (often different from stated blocker)
3. **Dependencies**: What/who does this depend on?
4. **Impact**: What else is this blocking downstream?
5. **Unblock options** (ordered by speed):
   - Quick fix: Can we work around it?
   - Direct action: Who needs to do what?
   - Escalation: Does Joseph need to make a call or reach out?

## Output Format
Return structured JSON:
```json
{
  "task_id": "...",
  "root_cause": "...",
  "impact": "...",
  "unblock_steps": [
    {"action": "...", "owner": "...", "effort": "low/medium/high"}
  ],
  "recommended_action": "..."
}
```

## Rules
- Always suggest at least one thing Joseph can do RIGHT NOW
- Don't just restate the problem — propose solutions
- If the blocker is another person, suggest the specific ask

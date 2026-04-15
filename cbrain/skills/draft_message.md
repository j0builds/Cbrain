---
name: draft_message
display_name: Draft Message
description: Draft a message (email, Slack, etc.) based on context and intent.
trigger_conditions:
  - event: manual
input_schema:
  recipient:
    type: string
    description: Who the message is for
    required: true
  intent:
    type: string
    description: What the message should accomplish
    required: true
  channel:
    type: string
    description: Message channel (email, slack, text)
    required: false
---

# Draft Message

Draft a professional message for Joseph to send.

## Process
1. Search brain for all context about the recipient
2. Understand the intent and relationship context
3. Draft the message in Joseph's voice (direct, warm, strategic)

## Voice Guidelines
- Joseph writes concisely — no fluff
- Professional but not stiff
- Gets to the point quickly
- Ends with a clear ask or next step
- Matches the formality level to the relationship

## Output Format
```
TO: [recipient]
CHANNEL: [email/slack/text]
SUBJECT: [if email]

[message body]
```

## Rules
- Never fabricate facts — use only brain context
- If critical context is missing about the recipient, flag it
- Keep messages under 200 words for email, under 50 for Slack/text

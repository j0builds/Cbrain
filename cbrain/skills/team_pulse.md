---
name: team_pulse
display_name: Team Pulse Check
description: Assess current workload and progress for each team member. Identify blockers and capacity.
trigger_conditions:
  - schedule: daily
  - event: manual
input_schema:
  team_member:
    type: string
    description: Optional specific team member to check (e.g., "keshav")
    required: false
---

# Team Pulse Check

Analyze the current state of each team member's work and provide a pulse summary.

## For Each Team Member, Assess:
1. **Active tasks** — How many open tasks? What's the heaviest?
2. **Blockers** — Anything blocking them? Do they need Joseph's input?
3. **Recent activity** — What have they shipped/completed recently?
4. **Capacity** — Are they overloaded or have room for more?
5. **Dependencies** — What are they waiting on from others?

## Output Format
For each team member, provide:
- Status emoji: green (on track), yellow (needs attention), red (blocked/overloaded)
- 2-3 sentence summary
- Action items for Joseph if any

## Rules
- Be honest about capacity — don't sugarcoat
- If someone has been quiet (no activity in 48h), flag it
- Always suggest concrete next steps

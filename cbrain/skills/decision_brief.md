---
name: decision_brief
display_name: Decision Brief
description: Prepare a structured brief for a pending decision, including options, tradeoffs, and recommendation.
trigger_conditions:
  - event: manual
input_schema:
  topic:
    type: string
    description: The decision topic or question
    required: true
---

# Decision Brief

Prepare a concise decision brief for the CEO. Every decision brief follows this structure:

## Template
1. **Decision Required**: One-sentence framing of what needs to be decided
2. **Context**: 2-3 sentences of relevant background from brain context
3. **Options** (max 3):
   - Option A: Description, pros, cons
   - Option B: Description, pros, cons
   - Option C: Description, pros, cons (if applicable)
4. **Recommendation**: Which option and why (1-2 sentences)
5. **Reversibility**: High/Medium/Low — how easy is it to change course?
6. **Time Sensitivity**: When does this need to be decided by?

## Rules
- Keep total brief under 300 words
- Use brain context to ground the options in real information
- If insufficient context exists, say so explicitly
- Always include a recommendation — CEOs need a starting point, not just options

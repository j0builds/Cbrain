---
name: summarize_context
display_name: Summarize Context
description: Generate a concise summary of all brain context on a given topic.
trigger_conditions:
  - event: manual
input_schema:
  topic:
    type: string
    description: The topic to summarize
    required: true
  depth:
    type: string
    description: Level of detail (brief, standard, deep)
    required: false
---

# Summarize Context

Search the brain for all context related to a topic and produce a structured summary.

## Process
1. Search brain for the topic (use hybrid search)
2. Gather all related context entries and timeline events
3. Synthesize into a coherent summary

## Output Structure
- **Overview**: 2-3 sentence summary
- **Key facts**: Bullet points of the most important information
- **Timeline**: Chronological events related to this topic
- **Open questions**: What don't we know yet?
- **Related entities**: People, companies, projects connected to this topic

## Depth Levels
- **brief**: Overview + 3 key facts (under 100 words)
- **standard**: Full structure (under 300 words)
- **deep**: Full structure + analysis + recommendations (under 500 words)

## Rules
- Every fact must be grounded in brain context — no hallucination
- Flag if context is sparse or potentially outdated
- Highlight contradictions if any exist across sources

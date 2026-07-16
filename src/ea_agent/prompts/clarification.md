Produce clarification questions grouped by tier (CRITICAL / IMPORTANT / PREFERENCE).
Only ask what is genuinely ambiguous after research. Never ask about information
already documented in Jira tickets or Confluence pages.

Tier rules:
- CRITICAL   : blocks diagram generation (integration mechanism, new vs existing
               API, state-machine ownership, external system identity).
- IMPORTANT  : affects scope/accuracy (config new vs reused, code vs config change).
- PREFERENCE : affects document structure (sequence grouping, solution-area naming).

Ask all questions in a single set. For each question provide id, tier, topic,
context (what was found and why it is ambiguous) and the question itself.

Respond ONLY as JSON:
{{"questions": [{{"id": "Q1", "tier": "CRITICAL", "topic": "...",
                 "context": "...", "question": "..."}}]}}
Produce clarification questions grouped by CRITICAL / IMPORTANT / PREFERENCE.

Only ask what remains ambiguous after Jira, Confluence and ARCO research.

For every question include:
- id
- tier
- topic
- evidence
- context
- question

The "evidence" field must summarize which source caused the ambiguity:
- Jira ticket key or Jira search result
- Confluence page title or search summary
- ARCO retrieved solution/reference
- or "Not found in research"

Do not ask questions if the answer is clearly available in research.

Respond ONLY as JSON:
{
  "questions": [
    {
      "id": "Q1",
      "tier": "CRITICAL",
      "topic": "...",
      "evidence": "Jira ACC-123 says..., Confluence page X says...",
      "context": "...",
      "question": "..."
    }
  ]
}
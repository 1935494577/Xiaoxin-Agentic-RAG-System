---
name: industry-research
description: Use for industry trends, annual tech outlooks, and real-time public information (e.g. "2025年AI发展"). Combine web search with internal KB when both public trends and company materials matter.
allowed-tools:
  - web_search
  - kb_search
---

# Industry Research Skill

## When to activate

Load this skill when the user asks about:

- Industry trends, market outlook, or annual summaries (e.g. AI, edtech, short-video)
- Real-time or time-sensitive public information not stored in the knowledge base
- Comparing external trends with internal course / product positioning

## Workflow

1. **Web first for dynamic facts** — call `web_search` with a focused query; cite sources in the answer.
2. **KB for internal alignment** — call `kb_search` when the answer should reference company courses, policies, or selling points.
3. **Synthesize** — separate "public trend" vs "internal material"; do not present web content as internal policy.

## Output rules

- Label web-sourced claims with source titles or URLs when available.
- If KB has no related content, say so explicitly; do not invent internal facts.
- Prefer concise bullet structure for trend summaries.

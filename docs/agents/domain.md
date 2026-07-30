# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT-MAP.md`** at the repo root — points at one `CONTEXT.md` per context. Read each one relevant to the topic.
- **`docs/adr/`** — read ADRs that touch the area you're about to work in. Also check context-scoped ADRs under each package when present.

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The producer skill (`/grill-with-docs`) creates them lazily when terms or decisions actually get resolved.

## File structure (this repo)

Multi-context monorepo:

```
/
├── CONTEXT-MAP.md                 ← index of contexts (create when needed)
├── docs/adr/                      ← system-wide architectural decisions
├── docs/                          ← project docs (项目说明.md, conversation-context.md, …)
├── enterprise_rag/
│   ├── CONTEXT.md                 ← backend: RAG pipeline, API, agent, feedback loop
│   └── docs/adr/                  ← backend-specific ADRs (optional)
└── frontend/
    ├── CONTEXT.md                 ← React Chat + Admin UI
    └── docs/adr/                  ← frontend-specific ADRs (optional)
```

**Context guide:**

| Context | Path | Typical topics |
| ------- | ---- | -------------- |
| Backend RAG | `enterprise_rag/CONTEXT.md` | retrieval, LangGraph, ingest, feedback_loop, SQLite stores |
| Frontend | `frontend/CONTEXT.md` | ChatPage, Admin pages, user profile, streaming UI |
| System-wide | `docs/adr/` | cross-cutting architecture, deployment, security |

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in the relevant `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/grill-with-docs`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (…) — but worth reopening because…_

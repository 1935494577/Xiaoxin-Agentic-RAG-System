# Agent instructions

Enterprise RAG monorepo: Python FastAPI backend (`enterprise_rag/`), React frontend (`frontend/`), shared docs (`docs/`).

**Current product overview (As-Is):** [`docs/项目说明.md`](docs/项目说明.md) — prefer this over any obsolete roadmap files.

## Agent skills

### Issue tracker

Issues live in GitHub Issues for `1935494577/Xiaoxin-Agentic-RAG-System`. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical triage labels; defaults match role names. See `docs/agents/triage-labels.md`.

### Domain docs

Multi-context monorepo: `CONTEXT-MAP.md` at the repo root points to per-package `CONTEXT.md` files. See `docs/agents/domain.md`.

### DeerFlow integration

Agent orchestration (tools, skills, channels) **must** follow [`docs/deerflow-integration.md`](docs/deerflow-integration.md) and local reference repo `D:\bytedance flow\deer-flow`. Do not invent parallel middleware, skill loaders, or channel buses. Token metering for Admin uses this repo’s independent SQLite store (see 项目说明 §4.4).

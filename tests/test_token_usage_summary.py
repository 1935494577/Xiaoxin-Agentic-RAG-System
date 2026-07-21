"""Token usage summary API backed by local SQLite (no DeerFlow)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))


def test_summary_route_registered():
    from api.main import app

    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/api/token-usage/summary" in paths
    assert "/api/threads/{thread_id}/token-usage" in paths


def test_summary_from_local_store(tmp_path, monkeypatch):
    from api import token_usage_store as store
    from jnao_harness.gateway.routers import token_usage as route_mod

    db = tmp_path / "token_usage.db"
    monkeypatch.setattr(store.settings, "token_usage_db_path", db)
    monkeypatch.setattr(store.settings, "token_usage_enabled", True)
    store.init_token_usage_db()
    store.record_llm_call(
        model="m1",
        caller="answer",
        prompt_tokens=10,
        completion_tokens=20,
        session_id="s1",
        question_preview="hello",
    )

    import asyncio

    out = asyncio.run(route_mod.token_usage_summary(limit=10))
    assert out.available is True
    assert out.source == "jnao_sqlite"
    assert out.total_tokens == 30
    assert out.total_calls == 1
    assert out.records[0].caller == "answer"
    assert out.records[0].question_preview == "hello"

    sess = asyncio.run(route_mod.thread_token_usage("s1"))
    assert sess.total_tokens == 30
    assert sess.total_runs == 1


def test_stream_usage_object_extraction(tmp_path, monkeypatch):
    from api import token_usage_store as store

    db = tmp_path / "token_usage.db"
    monkeypatch.setattr(store.settings, "token_usage_db_path", db)
    monkeypatch.setattr(store.settings, "token_usage_enabled", True)
    store.init_token_usage_db()

    class _Usage:
        prompt_tokens = 11
        completion_tokens = 22
        total_tokens = 33

    store.record_usage_object(_Usage(), model="m", caller="answer", session_id="s")
    summary = store.summarize_calls()
    assert summary["total_tokens"] == 33
    assert summary["total_input_tokens"] == 11
    assert summary["total_output_tokens"] == 22

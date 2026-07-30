"""Ops digest API tests."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_build_ops_digest_shape(tmp_path, monkeypatch):
    from api import ops_digest, token_usage_store as store

    db = tmp_path / "token_usage.db"
    monkeypatch.setattr(store.settings, "token_usage_db_path", db)
    monkeypatch.setattr(store.settings, "token_usage_enabled", True)
    store.init_token_usage_db()
    store.record_llm_call(
        model="m",
        caller="answer",
        prompt_tokens=1,
        completion_tokens=2,
        session_id="s",
        question_preview="hi",
    )
    out = ops_digest.build_ops_digest(since_days=1)
    assert "token_usage" in out
    assert out["token_usage"]["total_calls"] >= 1
    assert out["token_usage"]["total_tokens"] >= 3
    assert "feedback" in out
    assert "generated_at" in out

"""Independent token_usage_store (no DeerFlow)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))


def test_record_and_summarize(tmp_path, monkeypatch):
    from api import token_usage_store as store

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
        user_id="u1",
        question_preview="你好世界",
    )
    store.record_llm_call(
        model="m1",
        caller="tool_loop",
        prompt_tokens=5,
        completion_tokens=5,
        session_id="s1",
    )
    store.record_llm_call(
        model="m2",
        caller="answer",
        prompt_tokens=1,
        completion_tokens=2,
        session_id="s2",
    )

    summary = store.summarize_calls(limit=10)
    assert summary["total_tokens"] == 43
    assert summary["total_input_tokens"] == 16
    assert summary["total_output_tokens"] == 27
    assert summary["total_calls"] == 3
    assert len(summary["records"]) == 3
    assert summary["by_model"]["m1"]["total_tokens"] == 40

    sess = store.summarize_session("s1")
    assert sess["total_tokens"] == 40
    assert sess["total_runs"] == 2


def test_record_usage_object_dict(tmp_path, monkeypatch):
    from api import token_usage_store as store

    db = tmp_path / "token_usage.db"
    monkeypatch.setattr(store.settings, "token_usage_db_path", db)
    monkeypatch.setattr(store.settings, "token_usage_enabled", True)
    store.init_token_usage_db()
    store.record_usage_object(
        {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7},
        model="x",
        caller="answer",
        session_id="s",
    )
    summary = store.summarize_calls()
    assert summary["total_tokens"] == 7


def test_disabled_skips_write(tmp_path, monkeypatch):
    from api import token_usage_store as store

    db = tmp_path / "token_usage.db"
    monkeypatch.setattr(store.settings, "token_usage_db_path", db)
    monkeypatch.setattr(store.settings, "token_usage_enabled", False)
    assert store.record_llm_call(model="m", caller="answer", prompt_tokens=1, completion_tokens=1) is None

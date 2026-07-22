"""Aggregate LLM call rows into per-user-question turns."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from api.token_usage_store import aggregate_question_turns  # noqa: E402


def test_aggregate_same_session_question():
    rows = [
        {
            "id": "a",
            "created_at": "2026-07-21T13:47:55+00:00",
            "session_id": "s1",
            "model": "m1",
            "caller": "tool_loop",
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "total_tokens": 120,
            "question_preview": "今日天气",
        },
        {
            "id": "b",
            "created_at": "2026-07-21T13:47:51+00:00",
            "session_id": "s1",
            "model": "m1",
            "caller": "tool_loop",
            "prompt_tokens": 80,
            "completion_tokens": 10,
            "total_tokens": 90,
            "question_preview": "今日天气",
        },
        {
            "id": "c",
            "created_at": "2026-07-21T14:00:00+00:00",
            "session_id": "s1",
            "model": "m1",
            "caller": "answer",
            "prompt_tokens": 50,
            "completion_tokens": 5,
            "total_tokens": 55,
            "question_preview": "你好",
        },
    ]
    turns = aggregate_question_turns(rows, limit=10)
    assert len(turns) == 2
    # newest question first
    assert turns[0]["question_preview"] == "你好"
    assert turns[0]["total_tokens"] == 55
    assert turns[0]["llm_call_count"] == 1
    assert turns[1]["question_preview"] == "今日天气"
    assert turns[1]["total_tokens"] == 210
    assert turns[1]["llm_call_count"] == 2
    assert set(turns[1]["callers"]) == {"tool_loop"}

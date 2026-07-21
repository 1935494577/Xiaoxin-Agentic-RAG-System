"""Strict KB miss must not keep weak retrieval chunks in the prompt."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent.stream_chat import apply_strict_kb_miss_contexts  # noqa: E402


def test_weak_hit_clears_ctx_and_falls_back_when_enabled():
    mode, ctx, meta, missed = apply_strict_kb_miss_contexts(
        kb_ok=False,
        answer_mode="kb",
        ctx=["无关资料 A", "无关资料 B"],
        meta=[{"rerank_score": 0.05}, {"rerank_score": 0.04}],
        general_fallback_enabled=True,
    )
    assert missed is True
    assert mode == "general"
    assert ctx == []
    assert meta == []


def test_weak_hit_clears_ctx_keeps_kb_when_fallback_disabled():
    mode, ctx, meta, missed = apply_strict_kb_miss_contexts(
        kb_ok=False,
        answer_mode="kb",
        ctx=["弱相关"],
        meta=[{"rerank_score": 0.01}],
        general_fallback_enabled=False,
    )
    assert missed is True
    assert mode == "kb"
    assert ctx == []
    assert meta == []


def test_kb_ok_keeps_contexts():
    mode, ctx, meta, missed = apply_strict_kb_miss_contexts(
        kb_ok=True,
        answer_mode="kb",
        ctx=["真命中"],
        meta=[{"rerank_score": 0.9}],
        general_fallback_enabled=False,
    )
    assert missed is False
    assert mode == "kb"
    assert ctx == ["真命中"]
    assert len(meta) == 1

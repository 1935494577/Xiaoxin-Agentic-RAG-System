"""Answer routing tests."""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent.answer_router import resolve_answer_mode  # noqa: E402


def test_kb_when_rerank_high():
    mode = resolve_answer_mode(
        ["ctx"],
        [{"rerank_score": 0.8, "text": "资料"}],
        kb_min_score=0.55,
        general_fallback_enabled=True,
        question="阅读要求",
    )
    assert mode == "kb"


def test_general_when_rerank_low():
    mode = resolve_answer_mode(
        ["ctx"],
        [{"rerank_score": -2.0, "text": "弱相关"}],
        kb_min_score=0.55,
        kb_min_rerank_score=0.0,
        kb_llm_judge=False,
        general_fallback_enabled=True,
        question="珠穆朗玛峰多高",
    )
    assert mode == "general"


def test_kb_when_no_fallback():
    mode = resolve_answer_mode(
        [],
        [],
        kb_min_score=0.55,
        general_fallback_enabled=False,
        question="test",
    )
    assert mode == "kb"

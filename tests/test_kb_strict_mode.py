"""Strict KB-only mode (hybrid expert off)."""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent.answer_prompts import kb_system_prompt  # noqa: E402
from agent.kb_judge import resolve_answer_mode  # noqa: E402


def test_strict_mode_stays_kb_when_retrieval_weak():
    meta = [{"rerank_score": 0.00004, "hybrid_score": 1.0, "text": "x"}]
    mode = resolve_answer_mode(
        "下一步训练建议",
        ["弱相关"],
        meta,
        kb_min_score=0.55,
        kb_min_rerank_score=0.0,
        kb_llm_judge=False,
        general_fallback_enabled=False,
    )
    assert mode == "kb"


def test_strict_kb_prompt_forbids_general_supplement():
    text = kb_system_prompt(strict_kb_only=True)
    assert "仅知识库模式" in text
    assert "禁止用通用常识" in text

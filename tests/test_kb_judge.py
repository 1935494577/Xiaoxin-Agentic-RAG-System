"""KB judge tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent.kb_judge import (  # noqa: E402
    answer_indicates_kb_miss,
    resolve_answer_mode,
    should_use_knowledge_base,
)


def test_general_when_no_context():
    mode = resolve_answer_mode(
        "珠穆朗玛峰多高",
        [],
        [],
        kb_min_score=0.55,
        kb_min_rerank_score=0.0,
        kb_llm_judge=False,
        general_fallback_enabled=True,
    )
    assert mode == "general"


def test_kb_when_rerank_high():
    assert should_use_knowledge_base(
        "阅读要求",
        ["ctx"],
        [{"rerank_score": 0.8, "text": "x"}],
        kb_min_score=0.55,
        kb_min_rerank_score=0.0,
        kb_llm_judge=False,
        llm_runtime=None,
    )


def test_general_when_rerank_low():
    assert not should_use_knowledge_base(
        "珠穆朗玛峰多高",
        ["无关资料"],
        [{"rerank_score": -3.2, "text": "阅读训练"}],
        kb_min_score=0.55,
        kb_min_rerank_score=0.0,
        kb_llm_judge=False,
        llm_runtime=None,
    )


@patch("agent.kb_judge.OpenAI")
def test_llm_judge_no(mock_openai):
    client = MagicMock()
    mock_openai.return_value = client
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="NO"))]
    )
    mode = resolve_answer_mode(
        "你是谁",
        ["阅读资料片段"],
        [{"hybrid_score": 0.4, "text": "阅读"}],
        kb_min_score=0.55,
        kb_min_rerank_score=0.0,
        kb_llm_judge=True,
        general_fallback_enabled=True,
        llm_runtime={"llm_api_key": "sk-test", "llm_api_base": "http://x", "chat_model": "m"},
    )
    assert mode == "general"


def test_hybrid_high_no_rerank_uses_llm_judge():
    """无重排时即使混合分高，也走 LLM 判断。"""
    with patch("agent.kb_judge.OpenAI") as mock_openai:
        client = MagicMock()
        mock_openai.return_value = client
        client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="NO"))]
        )
        mode = resolve_answer_mode(
            "stream trace test",
            ["阅读资料"],
            [{"hybrid_score": 0.9, "text": "阅读"}],
            kb_min_score=0.55,
            kb_min_rerank_score=0.0,
            kb_llm_judge=True,
            general_fallback_enabled=True,
            llm_runtime={"llm_api_key": "sk-test", "llm_api_base": "http://x", "chat_model": "m"},
        )
        assert mode == "general"


def test_kb_miss_detection():
    assert answer_indicates_kb_miss("根据参考资料，资料不足，无法确认。")

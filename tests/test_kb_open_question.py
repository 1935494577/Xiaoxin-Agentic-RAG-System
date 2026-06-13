"""Tests for open-question KB routing."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent.kb_judge import (  # noqa: E402
    is_open_general_question,
    resolve_answer_mode,
    should_use_knowledge_base,
)


def test_is_open_general_question():
    assert is_open_general_question("设计出家长和孩子舒服的交互产品需要考虑什么")
    assert is_open_general_question("UX 设计有哪些原则？")
    assert not is_open_general_question("扫描速记有哪些注意事项")
    assert not is_open_general_question("1-3年级超脑阅读要求是什么")


def test_open_question_high_hybrid_goes_general_without_llm():
    q = "设计出家长和孩子舒服的交互产品软件需要考虑什么"
    assert not should_use_knowledge_base(
        q,
        ["思者孩子右脑型…"],
        [{"hybrid_score": 0.92, "text": "思者解说"}],
        kb_min_score=0.55,
        kb_min_rerank_score=0.0,
        kb_llm_judge=False,
        llm_runtime=None,
    )


@patch("agent.kb_judge.OpenAI")
def test_open_question_llm_no_routes_general(mock_openai):
    client = MagicMock()
    mock_openai.return_value = client
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="NO"))]
    )
    mode = resolve_answer_mode(
        "设计出家长和孩子舒服的交互产品软件需要考虑什么",
        ["思者孩子…"],
        [{"hybrid_score": 0.9, "text": "思者"}],
        kb_min_score=0.55,
        kb_min_rerank_score=0.0,
        kb_llm_judge=True,
        general_fallback_enabled=True,
        llm_runtime={"llm_api_key": "sk-test", "llm_api_base": "http://x", "chat_model": "m"},
    )
    assert mode == "general"


def test_specific_question_high_hybrid_still_kb():
    mode = resolve_answer_mode(
        "扫描速记有哪些注意事项",
        ["扫描速记晋级要求…"],
        [{"hybrid_score": 0.9, "text": "扫描速记"}],
        kb_min_score=0.55,
        kb_min_rerank_score=0.0,
        kb_llm_judge=False,
        general_fallback_enabled=True,
    )
    assert mode == "kb"

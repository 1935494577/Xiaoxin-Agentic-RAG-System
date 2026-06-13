"""Orchestration: prepare_turn tests."""

import sys
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent.conversation.prepare import prepare_turn  # noqa: E402


def test_prepare_turn_topic_shift_clears_history():
    history = [
        {"role": "user", "content": "知识库文档格式？"},
        {"role": "assistant", "content": "支持 PDF…"},
    ]
    with patch("agent.conversation.prepare.condense_turn") as mock_c:
        from agent.conversation.types import CondenseResult

        mock_c.return_value = CondenseResult(
            standalone_query="今天天气怎么样",
            topic_shift=True,
            used_llm=True,
        )
        ctx = prepare_turn(
            message="今天天气怎么样",
            history=history,
            memory_config={"conversation_condense_enabled": True, "history_prune_enabled": True},
            llm_runtime={},
        )
    assert ctx.topic_shift is True
    assert ctx.history_for_llm == []
    assert ctx.retrieval_query == "今天天气怎么样"


def test_prepare_turn_disabled_condense():
    history = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]
    ctx = prepare_turn(
        message="新问题",
        history=history,
        memory_config={"conversation_condense_enabled": False, "history_prune_enabled": False},
        llm_runtime={},
    )
    assert ctx.retrieval_query == "新问题"
    assert ctx.history_for_llm == history


def test_prepare_turn_reset_context():
    history = [
        {"role": "user", "content": "知识库？"},
        {"role": "assistant", "content": "PDF…"},
    ]
    ctx = prepare_turn(
        message="今天天气",
        history=history,
        memory_config={"conversation_condense_enabled": True},
        rolling_summary="旧摘要",
        reset_context=True,
    )
    assert ctx.reset_context is True
    assert ctx.topic_shift is True
    assert ctx.history_for_llm == []
    assert ctx.rolling_summary == ""

"""KB judge tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent.kb_judge import (  # noqa: E402
    ABSOLUTE_RERANK_MIN,
    RERANK_CONFIDENT_MIN,
    answer_indicates_kb_miss,
    assess_retrieval_confidence,
    resolve_answer_mode,
    should_attach_citations,
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


def test_kb_when_rerank_confident():
    assert should_use_knowledge_base(
        "阅读要求",
        ["ctx"],
        [{"rerank_score": 0.8, "text": "x"}],
        kb_min_score=0.55,
        kb_min_rerank_score=0.0,
        kb_llm_judge=False,
        llm_runtime=None,
    )


def test_general_when_rerank_negative():
    assert not should_use_knowledge_base(
        "珠穆朗玛峰多高",
        ["无关资料"],
        [{"rerank_score": -3.2, "text": "阅读训练"}],
        kb_min_score=0.55,
        kb_min_rerank_score=0.0,
        kb_llm_judge=False,
        llm_runtime=None,
    )


def test_general_when_rerank_near_zero():
    """弱相关重排分：fail-closed 走通用，不依赖问法句式。"""
    meta = [{"rerank_score": 0.00004, "hybrid_score": 1.0, "source": "思者解说.txt", "text": "x"}]
    assert assess_retrieval_confidence(meta, kb_min_score=0.55, kb_min_rerank_score=0.0) == "weak"
    mode = resolve_answer_mode(
        "你爱吃鱼嘛",
        ["无关"],
        meta,
        kb_min_score=0.55,
        kb_min_rerank_score=0.0,
        kb_llm_judge=False,
        general_fallback_enabled=True,
    )
    assert mode == "general"


def test_hybrid_only_without_rerank_is_gray_not_confident():
    meta = [{"hybrid_score": 1.0, "text": "扫描速记"}]
    assert assess_retrieval_confidence(meta, kb_min_score=0.55, kb_min_rerank_score=0.0) == "gray"


def test_hybrid_only_fail_closed_without_llm():
    assert not should_use_knowledge_base(
        "扫描速记有哪些注意事项",
        ["扫描速记晋级要求片段"],
        [{"hybrid_score": 0.9, "text": "扫描速记"}],
        kb_min_score=0.55,
        kb_min_rerank_score=0.0,
        kb_llm_judge=False,
        llm_runtime=None,
    )


@patch("agent.kb_judge.OpenAI")
def test_gray_zone_uses_llm_judge(mock_openai):
    client = MagicMock()
    mock_openai.return_value = client
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="NO"))]
    )
    mode = resolve_answer_mode(
        "你是谁",
        ["阅读资料片段"],
        [{"hybrid_score": 0.9, "text": "阅读"}],
        kb_min_score=0.55,
        kb_min_rerank_score=0.0,
        kb_llm_judge=True,
        general_fallback_enabled=True,
        llm_runtime={"llm_api_key": "sk-test", "llm_api_base": "http://x", "chat_model": "m"},
    )
    assert mode == "general"


@patch("agent.kb_judge.OpenAI")
def test_confident_rerank_skips_llm(mock_openai):
    mode = resolve_answer_mode(
        "扫描笔记有哪些注意事项",
        ["扫描速记晋级要求片段"],
        [{"rerank_score": 0.82, "hybrid_score": 0.9, "text": "扫描速记"}],
        kb_min_score=0.55,
        kb_min_rerank_score=0.0,
        kb_llm_judge=True,
        general_fallback_enabled=True,
        llm_runtime={"llm_api_key": "sk-test", "llm_api_base": "http://x", "chat_model": "m"},
    )
    assert mode == "kb"
    mock_openai.assert_not_called()


def test_kb_miss_detection():
    assert answer_indicates_kb_miss("根据参考资料，资料不足，无法确认。")
    assert answer_indicates_kb_miss(
        "喵~很抱歉呀，我还是不认识「永雏塔菲」呢，知识库里没有相关的内容喵(｡•́︿•̀｡)"
    )


def test_should_attach_citations_requires_confident_rerank():
    meta = [{"parent_id": "p1", "source": "a.txt", "rerank_score": 0.8}]
    assert should_attach_citations(answer_mode="kb", answer="根据资料，扫描速记需抽检。", contexts_meta=meta)
    assert not should_attach_citations(
        answer_mode="kb",
        answer="根据资料，扫描速记需抽检。",
        contexts_meta=[{"parent_id": "p1", "source": "思者解说.txt", "rerank_score": 0.00004}],
    )
    assert not should_attach_citations(
        answer_mode="kb",
        answer="知识库中没有相关资料，无法回答。",
        contexts_meta=meta,
    )
    assert not should_attach_citations(answer_mode="general", answer="永雏塔菲是虚拟主播。", contexts_meta=meta)


def test_confidence_threshold_constants():
    assert ABSOLUTE_RERANK_MIN < RERANK_CONFIDENT_MIN

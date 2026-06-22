"""Tests for multi-architecture RAG routing (Classic / Graph / Agentic)."""

from __future__ import annotations

import pytest

from agent.architecture_router import (
    RagArchitecture,
    load_rag_architecture_policy,
    resolve_rag_architecture,
)
from agent.input_modes import DocTaskType, InputMode, resolve_input_mode


CLASSIC_QUESTIONS = [
    "产品 A 的保修期多久？",
    "年假申请截止日期是什么时候？",
    "某个功能怎么配置？",
    "某条政策的适用范围是什么？",
]

GRAPH_QUESTIONS = [
    "哪些产品依赖某个组件？",
    "某个供应商变化会影响哪些下游产品？",
    "某个审批链上有哪些人？",
    "某个客户和哪些项目、合同、团队有关？",
]

AGENTIC_QUESTIONS = [
    "分析销量下降原因",
    "调查某个客服问题的背景",
    "判断一个业务异常来自哪个环节",
    "对一批竞品做综合研究",
    "排查线上故障的可能原因",
]


@pytest.fixture
def policy():
    return load_rag_architecture_policy()


def test_classic_questions_route_classic(policy):
    for q in CLASSIC_QUESTIONS:
        arch, meta = resolve_rag_architecture(
            q,
            department="技术部",
            input_mode="question",
            policy=policy,
            router_enabled=True,
            llm_fallback=False,
        )
        assert arch == "classic", f"expected classic for: {q!r}, got {arch} ({meta})"


def test_graph_questions_route_graph(policy):
    for q in GRAPH_QUESTIONS:
        arch, meta = resolve_rag_architecture(
            q,
            department="技术部",
            input_mode="question",
            policy=policy,
            router_enabled=True,
            llm_fallback=False,
        )
        assert arch == "graph", f"expected graph for: {q!r}, got {arch} ({meta})"


def test_agentic_questions_route_agentic(policy):
    for q in AGENTIC_QUESTIONS:
        arch, meta = resolve_rag_architecture(
            q,
            department="技术部",
            input_mode="question",
            policy=policy,
            router_enabled=True,
            llm_fallback=False,
        )
        assert arch == "agentic", f"expected agentic for: {q!r}, got {arch} ({meta})"


def test_manual_override_wins(policy):
    arch, _ = resolve_rag_architecture(
        "哪些产品依赖某个组件？",
        department="技术部",
        input_mode="question",
        policy=policy,
        request_override="classic",
        router_enabled=True,
    )
    assert arch == "classic"


def test_department_disallows_graph(policy):
    arch, meta = resolve_rag_architecture(
        "哪些产品依赖某个组件？",
        department="运营部",
        input_mode="question",
        policy=policy,
        router_enabled=True,
        llm_fallback=False,
    )
    assert arch != "graph"
    assert meta.get("department_clamped") is True


def test_router_disabled_defaults_classic(policy):
    arch, meta = resolve_rag_architecture(
        "分析销量下降原因",
        department="技术部",
        input_mode="question",
        policy=policy,
        router_enabled=False,
    )
    assert arch == "classic"
    assert meta.get("router_disabled") is True


def test_temp_document_defaults_classic(policy):
    arch, _ = resolve_rag_architecture(
        "总结这份文档",
        department="技术部",
        input_mode="temp_document",
        policy=policy,
        router_enabled=True,
        llm_fallback=False,
    )
    assert arch == "classic"


def test_doc_task_compare_prefers_agentic(policy):
    arch, _ = resolve_rag_architecture(
        "对比两份方案",
        department="技术部",
        input_mode="doc_task",
        doc_task_type="compare",
        policy=policy,
        router_enabled=True,
        llm_fallback=False,
    )
    assert arch == "agentic"


def test_scenario_tag_prefers_graph(policy):
    arch, meta = resolve_rag_architecture(
        "列出相关对象",
        department="技术部",
        input_mode="question",
        scenario_tags=["supply_chain"],
        policy=policy,
        router_enabled=True,
        llm_fallback=False,
    )
    assert arch == "graph"
    assert meta.get("scenario_prefer") == "graph"


def test_graph_and_agentic_signals_prefer_graph(policy):
    arch, meta = resolve_rag_architecture(
        "调查审批链上下游依赖的影响",
        department="技术部",
        input_mode="question",
        policy=policy,
        router_enabled=True,
        llm_fallback=False,
    )
    assert arch == "graph"
    assert meta.get("signal") == "graph+agentic"


def test_resolve_input_mode_from_request():
    mode, task = resolve_input_mode(
        input_mode="doc_task",
        doc_task_type="summary",
        temp_document_id=None,
        message="请总结",
    )
    assert mode == "doc_task"
    assert task == "summary"


def test_resolve_input_mode_temp_doc():
    mode, task = resolve_input_mode(
        input_mode=None,
        doc_task_type=None,
        temp_document_id="doc-123",
        message="这份文件讲了什么",
    )
    assert mode == "temp_document"
    assert task is None

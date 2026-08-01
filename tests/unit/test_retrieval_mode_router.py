"""Retrieval mode routing (exact / semantic / hybrid)."""

from __future__ import annotations

import pytest

from retrieval.retrieval_mode_router import (
    detect_retrieval_mode,
    detect_exam_search_mode,
    resolve_retrieval_mode,
)


@pytest.mark.parametrize(
    "query,expected",
    [
        ("WO-8827391进度", "exact"),
        ("工单 SP-abc123-def4", "exact"),
        ("公司年假政策", "exact"),
        ("超脑阅读", "exact"),
        ("怎么报销差旅费", "semantic"),
        ("为什么库存会下降", "semantic"),
        ("差旅费报销流程是什么", "semantic"),
        ("2024浙江高三数学函数单调性", "hybrid"),
        ("浙江高三 2024 数学卷", "hybrid"),
        ("请假 流程 步骤 要求", "exact"),
    ],
)
def test_detect_retrieval_mode(query: str, expected: str):
    assert detect_retrieval_mode(query) == expected


def test_resolve_retrieval_mode_disabled_defaults_hybrid():
    assert resolve_retrieval_mode("怎么报销", router_enabled=False) == "hybrid"


def test_resolve_retrieval_mode_fast_downgrades_hybrid():
    assert resolve_retrieval_mode("2024浙江高三数学函数", fast_mode=True) == "semantic"


def test_resolve_retrieval_mode_override():
    assert resolve_retrieval_mode("任意", override="exact") == "exact"


def test_detect_exam_search_mode_uuid():
    uid = "550e8400-e29b-41d4-a716-446655440000"
    assert detect_exam_search_mode(uid) == "exact"


def test_detect_exam_search_mode_keywords():
    assert detect_exam_search_mode("浙江 高三 数学") == "exact"
    assert detect_exam_search_mode("函数单调性 相关 题目") == "semantic"

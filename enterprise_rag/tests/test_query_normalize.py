"""Query normalization for retrieval (oral / typo / alias)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from retrieval.query_normalize import (
    build_search_variants,
    expand_bm25_query,
    invalidate_aliases_cache,
    load_query_aliases,
    normalize_query,
)


@pytest.fixture(autouse=True)
def _reset_alias_cache():
    invalidate_aliases_cache()
    yield
    invalidate_aliases_cache()


def test_normalize_oral_and_whitespace():
    assert normalize_query("  咋整超脑阅读啊？  ") == "怎么超脑阅读?"


def test_normalize_fullwidth():
    assert normalize_query("超脑阅读　要求") == "超脑阅读 要求"


def test_expand_bm25_adds_canonical_when_alias_present():
    aliases = {"超脑阅读": ["超脑阅度", "超脑"]}
    expanded = expand_bm25_query("超脑阅度有啥要求", aliases=aliases)
    assert "超脑阅读" in expanded
    assert "超脑阅度" in expanded


def test_build_search_variants_dedupes():
    variants = build_search_variants("咋整超脑阅度")
    assert variants[0] == "咋整超脑阅度"
    assert any("怎么" in v for v in variants)
    assert len(variants) <= 3


def test_rrf_fuse_prefers_shared_hits():
    from retrieval.hybrid_searcher import _rrf_fuse

    a = ["p1", "p2", "p3"]
    b = ["p2", "p1", "p4"]
    scores = _rrf_fuse([a, b])
    assert scores["p1"] > scores["p4"]
    assert scores["p2"] >= scores["p1"]


def test_load_aliases_from_config(tmp_path, monkeypatch):
    cfg = tmp_path / "query_aliases.json"
    cfg.write_text(
        json.dumps({"oral_map": {"咱": "我们"}, "term_aliases": {"测试词": ["测式词"]}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "retrieval.query_normalize._aliases_path",
        lambda: cfg,
    )
    data = load_query_aliases()
    assert data["oral_map"]["咱"] == "我们"
    assert "测式词" in data["term_aliases"]["测试词"]

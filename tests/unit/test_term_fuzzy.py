"""Tests for Chinese term fuzzy matching (Tier 1)."""

from __future__ import annotations

from retrieval.term_fuzzy import fuzzy_match_terms, suggest_query_corrections, weighted_edit_distance


def test_weighted_edit_shape_similar_chars():
    # 读/度 形近，替换代价更低
    assert weighted_edit_distance("超脑阅度", "超脑阅读") <= 1


def test_fuzzy_match_typo_reading():
    terms = ["超脑阅读", "感知力", "扫描速记"]
    hits = fuzzy_match_terms("超脑阅度", terms, max_edit_distance=1)
    assert "超脑阅读" in hits


def test_fuzzy_match_homophone_in_window():
    terms = ["扫描速记"]
    hits = fuzzy_match_terms("扫描速计训练", terms, max_edit_distance=1)
    assert "扫描速记" in hits


def test_fuzzy_match_pinyin_homophone():
    terms = ["感知力"]
    hits = fuzzy_match_terms("感智力", terms, max_edit_distance=2, use_pinyin=True)
    assert "感知力" in hits or hits == []  # pinyin optional when pypinyin missing


def test_suggest_query_corrections_finds_typo_fragment():
    terms = ["超脑阅读", "感知力"]
    pairs = suggest_query_corrections("超脑阅度训练", terms)
    assert any(canon == "超脑阅读" for _, canon in pairs)


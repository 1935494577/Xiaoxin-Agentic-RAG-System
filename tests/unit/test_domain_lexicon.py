"""Tests for domain lexicon extraction and fuzzy query expansion."""

from __future__ import annotations

import json

import pytest

from retrieval.domain_lexicon import (
    extract_domain_terms,
    fuzzy_match_terms,
    ingest_document_terms,
    load_domain_lexicon,
)


@pytest.fixture
def lexicon_path(tmp_path, monkeypatch):
    path = tmp_path / "domain_lexicon.json"
    monkeypatch.setattr("retrieval.domain_lexicon._lexicon_path", lambda: path)
    monkeypatch.setattr("retrieval.query_normalize._aliases_path", lambda: tmp_path / "query_aliases.json")
    (tmp_path / "query_aliases.json").write_text(
        json.dumps({"oral_map": {}, "term_aliases": {}}),
        encoding="utf-8",
    )
    return path


def test_extract_terms_from_headings_and_phrases():
    text = """
# 超脑阅读训练要求
## 感知力培养
1-3年级需完成扫描速记基础练习。
"""
    terms = extract_domain_terms(text)
    assert "超脑阅读" in terms
    assert "感知力" in terms
    assert any("扫描速记" in t for t in terms)


def test_fuzzy_match_typo_to_canonical():
    terms = ["超脑阅读", "感知力", "扫描速记"]
    hits = fuzzy_match_terms("超脑阅度", terms, max_edit_distance=1)
    assert "超脑阅读" in hits


def test_ingest_merges_terms(lexicon_path):
    ingest_document_terms("## 感知力\n训练要点", source="book.txt")
    data = load_domain_lexicon()
    assert "感知力" in data.get("terms", {})

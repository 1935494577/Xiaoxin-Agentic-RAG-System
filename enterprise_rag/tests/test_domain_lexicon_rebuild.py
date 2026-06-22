"""Tests for domain lexicon rebuild helpers."""

from __future__ import annotations

import json

import pytest

from retrieval.domain_lexicon import rebuild_domain_lexicon_from_texts, suggest_and_apply_domain_corrections


@pytest.fixture
def lexicon_path(tmp_path, monkeypatch):
    path = tmp_path / "domain_lexicon.json"
    monkeypatch.setattr("retrieval.domain_lexicon._lexicon_path", lambda: path)
    return path


def test_rebuild_from_texts(lexicon_path):
    stats = rebuild_domain_lexicon_from_texts(
        [("book.txt", "## 感知力\n# 超脑阅读训练要求")],
        replace=True,
    )
    assert stats["term_count"] >= 2
    data = json.loads(lexicon_path.read_text(encoding="utf-8"))
    assert "感知力" in data["terms"]
    assert "超脑阅读" in data["terms"]


def test_suggest_and_apply_domain_corrections(lexicon_path, tmp_path, monkeypatch):
    aliases = tmp_path / "query_aliases.json"
    aliases.write_text(
        json.dumps({"oral_map": {}, "term_aliases": {"超脑阅读": ["超脑阅度"]}}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr("retrieval.query_normalize._aliases_path", lambda: aliases)
    rebuild_domain_lexicon_from_texts([("a.txt", "## 超脑阅读")], replace=True)
    corrected, pairs = suggest_and_apply_domain_corrections("超脑阅度有啥要求")
    assert corrected == "超脑阅读有啥要求"
    assert pairs and pairs[0][1] == "超脑阅读"

"""Tests for miss query analyzer (Phase 3)."""

from __future__ import annotations

import json

import pytest

from retrieval.miss_query_analyzer import (
    analyze_retrieval_misses,
    cluster_miss_questions,
    propose_alias_candidates,
)


@pytest.fixture
def lexicon_env(tmp_path, monkeypatch):
    lexicon = tmp_path / "domain_lexicon.json"
    lexicon.write_text(
        json.dumps(
            {"terms": {"超脑阅读": {"sources": ["a"]}, "感知力": {"sources": ["a"]}}, "updated_at": "t1"}
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("retrieval.domain_lexicon._lexicon_path", lambda: lexicon)
    return lexicon


def test_propose_alias_candidates_merges_counts(lexicon_env):
    questions = ["咋整超脑阅度", "超脑阅度有啥要求", "超脑阅度训练"]
    ranked = propose_alias_candidates(questions)
    assert ranked
    top = ranked[0]
    assert top["canonical"] == "超脑阅读"
    assert top["count"] >= 2
    assert "超脑阅度" == top["alias"]


def test_cluster_miss_questions(lexicon_env):
    clusters = cluster_miss_questions(["超脑阅度有啥要求", "超脑阅度有啥要求", "什么是感知力"])
    assert clusters
    assert any(c["count"] >= 2 for c in clusters)


def test_analyze_retrieval_misses_from_feedback_rows(lexicon_env):
    rows = [
        {"rating": 0, "issue_type": "retrieval_miss", "question": "超脑阅度有啥要求"},
        {"rating": 1, "issue_type": "ok", "question": "谢谢"},
    ]
    out = analyze_retrieval_misses(rows)
    assert out["question_count"] == 1
    assert out["alias_candidates"]

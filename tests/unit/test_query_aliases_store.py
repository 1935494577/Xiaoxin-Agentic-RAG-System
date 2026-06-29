"""Tests for query alias store and feedback alias actions."""

from __future__ import annotations

import json

import pytest

from feedback_loop.actuator import execute_single_action
from feedback_loop.store import enrich_feedback, get_feedback, init_feedback_db, insert_feedback, save_triage_result
from retrieval.query_aliases_store import alias_patch_from_question, merge_term_aliases


@pytest.fixture
def alias_env(tmp_path, monkeypatch):
    db = tmp_path / "chat_sessions.db"
    aliases = tmp_path / "query_aliases.json"
    lexicon = tmp_path / "domain_lexicon.json"
    aliases.write_text(
        json.dumps({"oral_map": {}, "term_aliases": {"超脑阅读": ["超脑阅读"]}}, ensure_ascii=False),
        encoding="utf-8",
    )
    lexicon.write_text(
        json.dumps({"terms": {"超脑阅读": {"sources": ["book.txt"]}, "感知力": {"sources": ["book.txt"]}}, "updated_at": "t1"}),
        encoding="utf-8",
    )
    monkeypatch.setattr("retrieval.query_aliases_store._aliases_path", lambda: aliases)
    monkeypatch.setattr("retrieval.query_normalize._aliases_path", lambda: aliases)
    monkeypatch.setattr("retrieval.domain_lexicon._lexicon_path", lambda: lexicon)
    monkeypatch.setattr("config.settings.query_aliases_path", aliases)
    monkeypatch.setattr("config.settings.domain_lexicon_path", lexicon)
    monkeypatch.setattr("config.settings.chat_sessions_db_path", db)
    init_feedback_db()
    return aliases


def test_alias_patch_from_typo_question(alias_env):
    patch = alias_patch_from_question("咋整超脑阅度")
    assert patch is not None
    assert patch["canonical"] == "超脑阅读"
    assert "超脑阅度" in patch["aliases"]


def test_merge_term_aliases(alias_env):
    applied = merge_term_aliases("感知力", ["感智力"])
    assert applied["ok"] is True
    data = json.loads(alias_env.read_text(encoding="utf-8"))
    assert "感智力" in data["term_aliases"]["感知力"]


def test_apply_query_alias_actuator(alias_env):
    fid = insert_feedback(user_id="u1", rating=0, question="超脑阅度有啥要求", answer_preview="x")
    enrich_feedback(fid, context_count=0, sources=[], trace_snapshot={})
    save_triage_result(
        fid,
        issue_type="retrieval_miss",
        severity="high",
        summary="miss",
        human_review_required=True,
        suggested_actions=[
            {
                "action": "apply_query_alias",
                "confidence": 0.8,
                "patch": {"canonical": "超脑阅读", "aliases": ["超脑阅度"]},
            }
        ],
    )
    row = get_feedback(fid)
    assert row is not None
    result = execute_single_action(row, row["suggested_actions"][0])
    assert result["ok"] is True
    data = json.loads(alias_env.read_text(encoding="utf-8"))
    assert "超脑阅度" in data["term_aliases"]["超脑阅读"]

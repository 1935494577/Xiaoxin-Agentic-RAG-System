"""Admin API for query alias proposals and lexicon rebuild."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from config import settings  # noqa: E402
from feedback_loop.store import enrich_feedback, init_feedback_db, insert_feedback, save_triage_result  # noqa: E402


@pytest.fixture()
def api_client(tmp_path, monkeypatch):
    db = tmp_path / "chat_sessions.db"
    lexicon = tmp_path / "domain_lexicon.json"
    lexicon.write_text(
        json.dumps({"terms": {"超脑阅读": {"sources": ["a"]}}, "updated_at": "t1"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "chat_sessions_db_path", db)
    monkeypatch.setattr(settings, "domain_lexicon_path", lexicon)
    monkeypatch.setattr("retrieval.domain_lexicon._lexicon_path", lambda: lexicon)
    init_feedback_db()

    from api.main import app

    with TestClient(app) as client:
        yield client


def test_alias_proposals_from_miss_feedback(api_client):
    fid = insert_feedback(user_id="u1", rating=0, question="超脑阅度有啥要求")
    enrich_feedback(fid, context_count=0, sources=[])
    save_triage_result(
        fid,
        issue_type="retrieval_miss",
        severity="high",
        summary="miss",
        human_review_required=True,
        suggested_actions=[],
    )
    r = api_client.get(
        "/admin/feedback/alias-proposals",
        headers={"X-Admin-Role": "viewer", "X-Tenant-ID": "internal"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["question_count"] >= 1
    assert any(c["canonical"] == "超脑阅读" for c in data.get("alias_candidates") or [])


def test_rebuild_domain_lexicon_endpoint(api_client, tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "book.txt").write_text("## 感知力\n训练要点", encoding="utf-8")
    lexicon = tmp_path / "domain_lexicon.json"
    monkeypatch.setattr(settings, "data_raw_dir", raw_dir)
    monkeypatch.setattr(settings, "domain_lexicon_path", lexicon)
    monkeypatch.setattr("retrieval.domain_lexicon._lexicon_path", lambda: lexicon)

    r = api_client.post("/ingest/rebuild-domain-lexicon?replace=true")
    assert r.status_code == 200
    data = r.json()
    assert data["term_count"] >= 1
    assert Path(data["lexicon_path"]).is_file()

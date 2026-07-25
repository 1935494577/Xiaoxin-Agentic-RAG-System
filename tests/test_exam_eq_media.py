"""TDD: [[EQ:n]] media ingest_id linkage + resolve to image file."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_resolve_eq_media_file(tmp_path):
    from exam_bank.docx_extract import resolve_eq_media_file

    iid = "abc123media"
    d = tmp_path / iid
    d.mkdir()
    (d / "eq_3.png").write_bytes(b"png")
    (d / "eq_7_ole.wmf").write_bytes(b"wmf")
    assert resolve_eq_media_file(tmp_path, iid, "3").name == "eq_3.png"
    assert resolve_eq_media_file(tmp_path, iid, "7").name.startswith("eq_7")
    assert resolve_eq_media_file(tmp_path, iid, "99") is None


def test_source_paper_and_question_store_media_ingest_id(tmp_path, monkeypatch):
    from exam_bank import store

    monkeypatch.setattr(store.settings, "exam_bank_db_path", tmp_path / "eq.db")
    store.init_exam_bank_db()
    col = store.create_collection(
        name="库", subject="数学", grade="高三", region="浙江", visibility="tenant_shared"
    )
    q = store.create_question(
        collection_id=col["id"],
        qtype="choice",
        stem="已知[[EQ:1]]则",
        options=["[[EQ:2]]", "[[EQ:3]]"],
        media_ingest_id="media_xyz",
        quality_status="published",
    )
    assert q["media_ingest_id"] == "media_xyz"
    sp = store.create_source_paper(
        collection_id=col["id"],
        title="卷",
        raw_text="1. 已知[[EQ:1]]",
        question_ids=[q["id"]],
        media_ingest_id="media_xyz",
    )
    assert sp["media_ingest_id"] == "media_xyz"
    got = store.get_question(q["id"])
    assert got and got["media_ingest_id"] == "media_xyz"


def test_eq_media_api(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from exam_bank import store
    from exam_bank.docx_extract import default_exam_media_root

    monkeypatch.setattr(store.settings, "exam_bank_db_path", tmp_path / "eqapi.db")
    media_root = tmp_path / "exam_media"
    media_root.mkdir()
    monkeypatch.setattr(
        "exam_bank.docx_extract.default_exam_media_root",
        lambda: media_root,
    )
    store.init_exam_bank_db()
    iid = "eqapi01"
    (media_root / iid).mkdir()
    (media_root / iid / "eq_1.png").write_bytes(b"\x89PNG")

    from api.exam_router import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        r = client.get(f"/api/exam/ingest/media/{iid}/eq/1")
        assert r.status_code == 200, r.text
        assert r.content.startswith(b"\x89PNG")
        r404 = client.get(f"/api/exam/ingest/media/{iid}/eq/9")
        assert r404.status_code == 404

"""Exam collection ACL (visibility / owner)."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_list_collections_respects_private(tmp_path, monkeypatch):
    from exam_bank import store

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()

    store.create_collection(
        name="私有",
        subject="数学",
        grade="初二",
        region="杭州",
        visibility="private",
        owner_user_id="alice",
    )
    store.create_collection(
        name="共享",
        subject="数学",
        grade="初二",
        region="宁波",
        visibility="tenant_shared",
        owner_user_id="alice",
    )

    as_bob = store.list_collections(tenant_id="internal", reader_user_id="bob")
    names = {c["name"] for c in as_bob}
    assert any("宁波" in n for n in names)
    assert not any("杭州" in n and "私有" in n for n in names) or "杭州·数学·初二" not in [
        c["name"] for c in as_bob if c.get("visibility") == "private"
    ]
    # bob 看不到 alice 的私有库
    assert not any(
        c.get("region") == "杭州" and c.get("visibility") == "private" for c in as_bob
    )

    as_alice = store.list_collections(tenant_id="internal", reader_user_id="alice")
    regions = {c["region"] for c in as_alice}
    assert "杭州" in regions and "宁波" in regions
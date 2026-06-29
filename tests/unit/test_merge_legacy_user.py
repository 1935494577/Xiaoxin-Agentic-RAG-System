"""Merge legacy anonymous profiles into auth accounts."""

from __future__ import annotations

from api.user_profile_store import merge_legacy_user


def test_merge_legacy_user_copies_avatars_and_sessions(tmp_path, monkeypatch):
    import sqlite3

    db = tmp_path / "chat.db"
    monkeypatch.setattr("api.user_profile_store.settings.chat_sessions_db_path", db)
    monkeypatch.setattr("api.user_profile_store._db_path", lambda: db)

    from api.user_profile_store import init_user_profile_db, upsert_profile

    init_user_profile_db()
    from api.chat_session_store import init_chat_session_db

    init_chat_session_db()
    upsert_profile(
        "u_old",
        display_name="Elysa",
        avatar_url="data:image/png;base64,abc",
        ai_avatar_url="data:image/png;base64,def",
        department="媒体部",
    )

    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO chat_sessions (id, tenant_id, user_id, title, created_at, updated_at) "
            "VALUES ('s1', 'internal', 'u_old', 'hi', 't', 't')"
        )
        conn.commit()

    row = merge_legacy_user("u_old", "auth_new")
    assert row["display_name"] == "Elysa"
    assert row["avatar_url"].startswith("data:image/")
    assert row["ai_avatar_url"].startswith("data:image/")

    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        sess = conn.execute("SELECT user_id FROM chat_sessions WHERE id='s1'").fetchone()
        assert sess["user_id"] == "auth_new"

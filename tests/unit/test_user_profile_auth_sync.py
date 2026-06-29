"""Profile display_name sync from auth account."""

from __future__ import annotations

import pytest

from api.user_profile_store import apply_auth_to_profile, get_profile, init_user_profile_db


@pytest.fixture()
def profile_db(tmp_path, monkeypatch):
    db = tmp_path / "profiles.db"
    monkeypatch.setattr("config.settings.chat_sessions_db_path", db)
    init_user_profile_db()
    return db


def test_apply_auth_syncs_empty_display_name(profile_db):
    row = get_profile("u_sync")
    assert row["display_name"] == ""

    merged = apply_auth_to_profile(
        row,
        {"id": "u_sync", "department": "技术部", "display_name": "Elysa"},
    )
    assert merged["display_name"] == "Elysa"
    assert get_profile("u_sync")["display_name"] == "Elysa"


def test_apply_auth_keeps_existing_display_name(profile_db):
    from api.user_profile_store import upsert_profile

    upsert_profile("u_keep", display_name="Custom", department="技术部")
    row = get_profile("u_keep")

    merged = apply_auth_to_profile(
        row,
        {"id": "u_keep", "department": "技术部", "display_name": "AuthName"},
    )
    assert merged["display_name"] == "Custom"

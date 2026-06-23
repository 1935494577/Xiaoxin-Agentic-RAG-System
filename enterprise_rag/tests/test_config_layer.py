"""Config layering: platform baseline vs per-user overrides."""

from __future__ import annotations

from account_config.store import (
    deep_merge,
    effective_json_config,
    get_user_override,
    init_platform_config_db,
    save_platform_scope,
    save_user_scope_patch,
    set_user_override,
)


def test_deep_merge_nested():
    base = {"a": 1, "nested": {"x": 1, "y": 2}}
    overlay = {"b": 2, "nested": {"y": 9}}
    merged = deep_merge(base, overlay)
    assert merged == {"a": 1, "b": 2, "nested": {"x": 1, "y": 9}}


def test_user_override_isolated_between_users(tmp_path, monkeypatch):
    db = tmp_path / "platform.db"
    monkeypatch.setattr("account_config.store.settings.platform_config_db_path", db)
    init_platform_config_db()

    set_user_override("user_a", "ui", {"max_history_turns": 3})
    set_user_override("user_b", "ui", {"max_history_turns": 8})

    assert get_user_override("user_a", "ui") == {"max_history_turns": 3}
    assert get_user_override("user_b", "ui") == {"max_history_turns": 8}


def test_effective_config_merges_for_non_admin(tmp_path, monkeypatch):
    db = tmp_path / "platform.db"
    monkeypatch.setattr("account_config.store.settings.platform_config_db_path", db)
    init_platform_config_db()
    set_user_override("user_ops", "ui", {"max_history_turns": 4})

    result = effective_json_config(
        "ui",
        lambda: {"max_history_turns": 6, "kb_min_score": 0.55},
        user_id="user_ops",
        is_platform_admin=False,
    )
    assert result["max_history_turns"] == 4
    assert result["kb_min_score"] == 0.55


def test_admin_reads_platform_baseline_only(tmp_path, monkeypatch):
    db = tmp_path / "platform.db"
    monkeypatch.setattr("account_config.store.settings.platform_config_db_path", db)
    init_platform_config_db()
    set_user_override("admin_id", "ui", {"max_history_turns": 2})

    result = effective_json_config(
        "ui",
        lambda: {"max_history_turns": 6},
        user_id="admin_id",
        is_platform_admin=True,
    )
    assert result["max_history_turns"] == 6


def test_save_user_scope_patch_merges(tmp_path, monkeypatch):
    db = tmp_path / "platform.db"
    monkeypatch.setattr("account_config.store.settings.platform_config_db_path", db)
    init_platform_config_db()

    save_user_scope_patch("u1", "ui", {"max_history_turns": 5})
    save_user_scope_patch("u1", "ui", {"kb_min_score": 0.7})

    override = get_user_override("u1", "ui")
    assert override == {"max_history_turns": 5, "kb_min_score": 0.7}


def test_platform_version_bump(tmp_path, monkeypatch):
    db = tmp_path / "platform.db"
    monkeypatch.setattr("account_config.store.settings.platform_config_db_path", db)
    init_platform_config_db()

    v1 = save_platform_scope("ui", updated_by="tech1")
    v2 = save_platform_scope("ui", updated_by="tech1")
    assert v1 == 1
    assert v2 == 2

"""Config actor: only platform writer (tech1) may save global baseline."""

from __future__ import annotations

from account_config.request_auth import can_write_platform_config, resolve_config_actor


def test_can_write_platform_config_only_tech1():
    assert can_write_platform_config({"username": "tech1", "department": "技术部"}) is True
    assert can_write_platform_config({"username": "tech2", "department": "技术部"}) is False
    assert can_write_platform_config({"username": "tech3", "department": "技术部"}) is False
    assert can_write_platform_config({"username": "ops1", "department": "运营部"}) is False


def test_resolve_config_actor(monkeypatch):
    from account_config import request_auth

    monkeypatch.setattr(
        request_auth,
        "get_auth_user",
        lambda _req: {"id": "u2", "username": "tech2", "department": "技术部"},
    )

    class Req:
        pass

    user_id, can_write = resolve_config_actor(Req())  # type: ignore[arg-type]
    assert user_id == "u2"
    assert can_write is False

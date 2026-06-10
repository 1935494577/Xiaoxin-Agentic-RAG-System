"""Resolve default chat model profile without sidebar picker."""

from __future__ import annotations

from typing import Any


def resolve_model_for_chat(prof_data: dict[str, Any] | None) -> tuple[str | None, bool]:
    """Return (model_profile_id, force_env_llm)."""
    if not prof_data or prof_data.get("_auth_error"):
        return None, True
    default_id = prof_data.get("default_profile_id")
    if default_id:
        return str(default_id), False
    profiles = prof_data.get("profiles") or []
    if profiles:
        return str(profiles[0].get("id", "")), False
    return None, True

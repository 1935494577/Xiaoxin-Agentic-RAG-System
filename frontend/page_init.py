"""Shared page bootstrap: sidebar logo, nav chrome, model status light."""

from __future__ import annotations

import time
from typing import Any

import streamlit as st

from chat_runtime import resolve_model_for_chat
from ui_theme import (
    fetch_model_connection_status,
    fetch_ui_config,
    render_minimal_sidebar,
    render_model_status_light,
)

_UI_TTL = 120.0
_PROFILES_TTL = 60.0
_STATUS_TTL = 90.0


def _cached(key: str, ttl: float, loader):
    now = time.time()
    row = st.session_state.get(key)
    if isinstance(row, dict) and now - float(row.get("ts", 0)) < ttl:
        return row.get("val")
    val = loader()
    st.session_state[key] = {"ts": now, "val": val}
    return val


def invalidate_page_cache() -> None:
    for key in ("_ui_cfg", "_model_profiles", "_model_status"):
        st.session_state.pop(key, None)


def init_app_page(
    api_base: str,
    auth: dict[str, str],
    prof_data: dict[str, Any] | None,
    *,
    check_model_status: bool = True,
) -> tuple[dict[str, Any], str | None, bool]:
    ui = _cached("_ui_cfg", _UI_TTL, lambda: fetch_ui_config(api_base, auth))
    render_minimal_sidebar(ui, api_base, auth)

    if prof_data is None:
        prof_data = _cached(
            "_model_profiles",
            _PROFILES_TTL,
            lambda: _load_profiles(api_base, auth),
        )

    profile_id, force_env = resolve_model_for_chat(prof_data)

    if check_model_status:
        status_key = f"_model_status|{profile_id}|{force_env}"

        def _load_status():
            return fetch_model_connection_status(api_base, auth, profile_id, force_env, quick=True)

        connected = _cached(status_key, _STATUS_TTL, _load_status)
        render_model_status_light(connected)
    else:
        connected = False

    return ui, profile_id, force_env


def _load_profiles(api_base: str, auth: dict[str, str]) -> dict[str, Any] | None:
    import streamlit_common as scom

    return scom.fetch_model_profiles(api_base)

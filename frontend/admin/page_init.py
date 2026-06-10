"""Shared page bootstrap: unified top nav, sidebar logo, model status light."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def _cache_get(key: str, ttl: float) -> Any:
    """Return cached value if fresh, else None (sentinel for cache miss)."""
    row = st.session_state.get(key)
    now = time.time()
    if isinstance(row, dict) and now - float(row.get("ts", 0)) < ttl:
        return row.get("val")
    return None


def _cache_set(key: str, val: Any) -> None:
    st.session_state[key] = {"ts": time.time(), "val": val}


def invalidate_page_cache() -> None:
    for key in list(st.session_state.keys()):
        if key in ("_ui_cfg", "_model_profiles", "_nav_links") or str(key).startswith("_model_status"):
            st.session_state.pop(key, None)


def _load_nav(api_base: str, auth: dict[str, str]) -> dict[str, Any]:
    from nav_links import fetch_nav_links

    return fetch_nav_links(api_base, auth)


def init_app_page(
    api_base: str,
    auth: dict[str, str],
    prof_data: dict[str, Any] | None,
    *,
    check_model_status: bool = True,
    nav_id: str = "",
) -> tuple[dict[str, Any], str | None, bool]:
    # -- round 1: resolve ui, nav, profiles (independent) in parallel --
    tasks: dict[str, Any] = {}
    ui = _cache_get("_ui_cfg", _UI_TTL)
    if ui is None:
        tasks["_ui_cfg"] = lambda: fetch_ui_config(api_base, auth)

    nav = _cache_get("_nav_links", _UI_TTL)
    if nav is None:
        tasks["_nav_links"] = lambda: _load_nav(api_base, auth)

    if prof_data is None:
        prof_data = _cache_get("_model_profiles", _PROFILES_TTL)
        if prof_data is None:
            tasks["_model_profiles"] = lambda: _load_profiles(api_base, auth)

    if tasks:
        with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
            futures = {pool.submit(loader): key for key, loader in tasks.items()}
            for fut in as_completed(futures):
                key = futures[fut]
                _cache_set(key, fut.result())

        if "_ui_cfg" in tasks:
            ui = _cache_get("_ui_cfg", _UI_TTL)
        if "_nav_links" in tasks:
            nav = _cache_get("_nav_links", _UI_TTL)
        if "_model_profiles" in tasks:
            prof_data = _cache_get("_model_profiles", _PROFILES_TTL)

    # -- render chrome --
    if nav_id:
        from nav_links import render_unified_nav
        from ui_theme import resolve_app_logo_data_url

        logo = resolve_app_logo_data_url(api_base, auth)
        render_unified_nav(nav_id, nav, logo_src=logo)
    render_minimal_sidebar(ui, api_base, auth)

    # -- round 2: status check (depends on profile resolution from round 1) --
    profile_id, force_env = resolve_model_for_chat(prof_data)
    connected = False
    if check_model_status:
        status_key = f"_model_status|{profile_id}|{force_env}"
        connected = _cache_get(status_key, _STATUS_TTL)
        if connected is None:
            connected = fetch_model_connection_status(api_base, auth, profile_id, force_env, quick=True)
            _cache_set(status_key, connected)
        render_model_status_light(connected)
        connected = bool(connected)

    return ui, profile_id, force_env


def _load_profiles(api_base: str, auth: dict[str, str]) -> dict[str, Any] | None:
    import streamlit_common as scom

    return scom.fetch_model_profiles(api_base)

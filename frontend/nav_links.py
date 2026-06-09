"""Unified top navigation — shared by Streamlit admin pages."""

from __future__ import annotations

import html
import os
from typing import Any

import httpx
import streamlit as st

_FALLBACK = {
    "chat_url": os.environ.get("RAG_CHAT_SPA_URL", "http://127.0.0.1:8502"),
    "admin_url": os.environ.get("RAG_ADMIN_URL", "http://127.0.0.1:8501"),
    "items": [
        {"id": "chat", "label": "对话", "href": os.environ.get("RAG_CHAT_SPA_URL", "http://127.0.0.1:8502"), "external": True, "primary": True},
        {"id": "ingest", "label": "数据入库", "href": f"{os.environ.get('RAG_ADMIN_URL', 'http://127.0.0.1:8501')}/ingest"},
        {"id": "processing", "label": "数据处理", "href": f"{os.environ.get('RAG_ADMIN_URL', 'http://127.0.0.1:8501')}/processing"},
        {"id": "vector_store", "label": "向量库", "href": f"{os.environ.get('RAG_ADMIN_URL', 'http://127.0.0.1:8501')}/vector_store"},
        {"id": "memory", "label": "对话记忆", "href": f"{os.environ.get('RAG_ADMIN_URL', 'http://127.0.0.1:8501')}/memory"},
        {"id": "models", "label": "模型", "href": f"{os.environ.get('RAG_ADMIN_URL', 'http://127.0.0.1:8501')}/models"},
        {"id": "trace", "label": "链路 Trace", "href": f"{os.environ.get('RAG_ADMIN_URL', 'http://127.0.0.1:8501')}/trace"},
        {"id": "tutorial", "label": "教程", "href": f"{os.environ.get('RAG_ADMIN_URL', 'http://127.0.0.1:8501')}/tutorial"},
    ],
}


def fetch_nav_links(api_base: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    try:
        with httpx.Client(base_url=api_base.rstrip("/"), timeout=5.0, headers=headers or None) as c:
            r = c.get("/config/nav")
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return dict(_FALLBACK)


def render_unified_nav(active_id: str, nav: dict[str, Any], *, logo_src: str | None = None) -> None:
    items = nav.get("items") or []
    parts: list[str] = []
    for item in items:
        iid = str(item.get("id") or "")
        label = html.escape(str(item.get("label") or ""))
        href = html.escape(str(item.get("href") or "#"))
        active = iid == active_id
        cls = "unified-nav-link active" if active else "unified-nav-link"
        if item.get("primary") and not active:
            cls += " primary"
        parts.append(f'<a class="{cls}" href="{href}" target="_self">{label}</a>')

    chat_url = html.escape(str(nav.get("chat_url") or ""))
    brand = "企业知识库"
    if logo_src:
        brand = (
            f'<img class="unified-nav-logo" src="{html.escape(logo_src)}" alt="logo"/>'
            f'<span>{html.escape(brand)}</span>'
        )
    bar = (
        '<div class="unified-nav">'
        f'<div class="unified-nav-brand">{brand}</div>'
        '<nav class="unified-nav-links">' + "".join(parts) + "</nav>"
        f'<a class="unified-nav-cta" href="{chat_url}">进入对话</a>'
        "</div>"
    )
    st.markdown(bar, unsafe_allow_html=True)

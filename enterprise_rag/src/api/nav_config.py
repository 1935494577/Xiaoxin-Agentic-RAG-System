"""Unified navigation links for Chat SPA and Streamlit admin."""

from __future__ import annotations

import os
from typing import Any, TypedDict


class AdminPageSpec(TypedDict, total=False):
    id: str
    label: str
    url_path: str
    module: str
    default: bool


# Single registry — keep in sync with frontend/admin/streamlit_app.py pages list.
ADMIN_PAGES: list[AdminPageSpec] = [
    {"id": "ingest", "label": "数据入库", "url_path": "", "module": "pages/ingest.py", "default": True},
    {"id": "processing", "label": "工具", "url_path": "processing", "module": "pages/processing_config.py"},
    {"id": "vector_store", "label": "向量库", "url_path": "vector_store", "module": "pages/vector_store_config.py"},
    {"id": "memory", "label": "对话记忆", "url_path": "memory", "module": "pages/chat_memory_config.py"},
    {"id": "prompts", "label": "提示词", "url_path": "prompts", "module": "pages/prompt_config.py"},
    {"id": "models", "label": "模型", "url_path": "models", "module": "pages/model_config.py"},
    {"id": "trace", "label": "链路 Trace", "url_path": "trace", "module": "pages/trace_config.py"},
    {"id": "tutorial", "label": "教程", "url_path": "tutorial", "module": "pages/tutorial.py"},
]

ADMIN_PAGE_IDS = frozenset(p["id"] for p in ADMIN_PAGES)


def admin_page_href(admin_base: str, page: AdminPageSpec) -> str:
    path = str(page.get("url_path") or "").strip("/")
    if path:
        return f"{admin_base.rstrip('/')}/{path}"
    return f"{admin_base.rstrip('/')}/"


def _admin_url() -> str:
    return (os.environ.get("RAG_ADMIN_URL") or "http://127.0.0.1:8501").rstrip("/")


def _chat_url() -> str:
    return (os.environ.get("RAG_CHAT_SPA_URL") or "http://127.0.0.1:8502").rstrip("/")


def build_nav_config() -> dict[str, Any]:
    admin = _admin_url()
    chat = _chat_url()
    items: list[dict[str, Any]] = [
        {"id": "chat", "label": "Jnao Chat", "href": chat, "external": True, "primary": True},
    ]
    for page in ADMIN_PAGES:
        items.append(
            {
                "id": page["id"],
                "label": page["label"],
                "href": admin_page_href(admin, page),
                "external": False,
            }
        )
    return {"chat_url": chat, "admin_url": admin, "items": items, "admin_pages": list(ADMIN_PAGES)}

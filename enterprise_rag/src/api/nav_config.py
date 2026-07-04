"""Admin page registry — kept in sync with frontend/src/lib/departmentAccess.ts."""

from __future__ import annotations

import os
from typing import Any, TypedDict


class AdminPageSpec(TypedDict):
    id: str
    label: str
    url_path: str


# Order matches ALL_NAV_ITEMS in departmentAccess.ts (excluding chat).
ADMIN_PAGES: list[AdminPageSpec] = [
    {"id": "ingest", "label": "数据入库", "url_path": "ingest"},
    {"id": "scenarios", "label": "业务场景", "url_path": "scenarios"},
    {"id": "processing", "label": "工具", "url_path": "processing"},
    {"id": "vector_store", "label": "向量库", "url_path": "vector-store"},
    {"id": "memory", "label": "对话设置", "url_path": "memory"},
    {"id": "prompts", "label": "提示词", "url_path": "prompts"},
    {"id": "models", "label": "模型", "url_path": "models"},
    {"id": "feedback", "label": "用户反馈", "url_path": "feedback"},
    {"id": "eval_reports", "label": "评测报告", "url_path": "eval-reports"},
    {"id": "trace", "label": "链路 Trace", "url_path": "trace"},
    {"id": "tutorial", "label": "教程", "url_path": "tutorial"},
    {"id": "users", "label": "账号管理", "url_path": "users"},
]

ADMIN_PAGE_IDS = frozenset(p["id"] for p in ADMIN_PAGES)


def admin_page_href(admin_base: str, page: AdminPageSpec) -> str:
    path = str(page.get("url_path") or "").strip("/")
    if path:
        return f"{admin_base.rstrip('/')}/{path}"
    return f"{admin_base.rstrip('/')}/"


def _chat_url() -> str:
    return (os.environ.get("RAG_CHAT_SPA_URL") or "http://127.0.0.1:8502").rstrip("/")


def _admin_url() -> str:
    explicit = (os.environ.get("RAG_ADMIN_URL") or "").strip().rstrip("/")
    if explicit:
        return explicit
    return f"{_chat_url()}/admin"


def build_nav_config() -> dict[str, Any]:
    chat = _chat_url()
    admin = _admin_url()
    items: list[dict[str, Any]] = [
        {"id": "chat", "label": "Jnao Chat", "href": f"{chat}/chat", "external": False, "primary": True},
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

"""Unified navigation links for Chat SPA and Streamlit admin."""

from __future__ import annotations

import os
from typing import Any


def _admin_url() -> str:
    return (os.environ.get("RAG_ADMIN_URL") or "http://127.0.0.1:8501").rstrip("/")


def _chat_url() -> str:
    return (os.environ.get("RAG_CHAT_SPA_URL") or "http://127.0.0.1:8502").rstrip("/")


def build_nav_config() -> dict[str, Any]:
    admin = _admin_url()
    chat = _chat_url()
    return {
        "chat_url": chat,
        "admin_url": admin,
        "items": [
            {"id": "chat", "label": "对话", "href": chat, "external": True, "primary": True},
            {"id": "ingest", "label": "数据入库", "href": f"{admin}/ingest", "external": False},
            {"id": "processing", "label": "数据处理", "href": f"{admin}/processing", "external": False},
            {"id": "vector_store", "label": "向量库", "href": f"{admin}/vector_store", "external": False},
            {"id": "memory", "label": "对话记忆", "href": f"{admin}/memory", "external": False},
            {"id": "brand", "label": "外观", "href": f"{admin}/brand", "external": False},
            {"id": "models", "label": "模型", "href": f"{admin}/models", "external": False},
            {"id": "trace", "label": "链路 Trace", "href": f"{admin}/trace", "external": False},
            {"id": "tutorial", "label": "教程", "href": f"{admin}/tutorial", "external": False},
        ],
    }

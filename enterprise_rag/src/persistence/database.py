"""Database backend selection — SQLite (dev) vs PostgreSQL (production)."""

from __future__ import annotations

import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from config import settings


def uses_postgres() -> bool:
    return bool((settings.database_url or "").strip())


def normalized_database_url() -> str:
    raw = (settings.database_url or "").strip()
    if not raw:
        return ""
    if raw.startswith("postgresql://"):
        return "postgresql+psycopg://" + raw[len("postgresql://") :]
    return raw


@lru_cache(maxsize=1)
def get_sqlalchemy_engine():
    """Lazy SQLAlchemy engine when DATABASE_URL is configured."""
    url = normalized_database_url()
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    from sqlalchemy import create_engine

    return create_engine(url, pool_pre_ping=True)


def connect_sqlite(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def persistence_status() -> dict[str, Any]:
    """Health/diagnostic payload for admin or e2e smoke tests."""
    if uses_postgres():
        parsed = urlparse(normalized_database_url())
        return {
            "backend": "postgres",
            "host": parsed.hostname or "",
            "database": (parsed.path or "").lstrip("/"),
        }
    return {
        "backend": "sqlite",
        "auth_db": str(settings.auth_db_path),
        "chat_sessions_db": str(settings.chat_sessions_db_path),
        "exam_bank_db": str(settings.exam_bank_db_path),
    }

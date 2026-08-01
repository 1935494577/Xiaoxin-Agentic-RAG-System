"""Persistence backend selection tests."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_sqlite_default_when_database_url_empty(monkeypatch):
    from config import settings
    from persistence.database import persistence_status, uses_postgres

    monkeypatch.setattr(settings, "database_url", "")
    assert uses_postgres() is False
    status = persistence_status()
    assert status["backend"] == "sqlite"
    assert "auth_db" in status


def test_postgres_mode_when_database_url_set(monkeypatch):
    from config import settings
    from persistence.database import normalized_database_url, persistence_status, uses_postgres

    monkeypatch.setattr(
        settings,
        "database_url",
        "postgresql://jnao:secret@127.0.0.1:5432/jnao",
    )
    assert uses_postgres() is True
    assert normalized_database_url().startswith("postgresql+psycopg://")
    status = persistence_status()
    assert status["backend"] == "postgres"
    assert status["database"] == "jnao"

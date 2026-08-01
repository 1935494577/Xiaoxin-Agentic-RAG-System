"""`.env` must win over stale shell OPENAI_* for local dev."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_openai_key_prefers_dotenv_over_shell(monkeypatch):
    """Shell OPENAI_API_KEY must not override project .env (regression: invalid OnVr key)."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-shell-stale-key")

    import config

    importlib.reload(config)

    key = (config.settings.openai_api_key or "").strip()
    assert key and not key.endswith("key"), "expected .env key, got shell override"
    assert key == (config.os.environ.get("OPENAI_API_KEY") or "").strip()

"""Shared pytest fixtures for harness integration tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _deerflow_openai_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure config.yaml $OPENAI_* placeholders resolve without a local .env."""
    monkeypatch.setenv("DEER_FLOW_PROJECT_ROOT", str(REPO_ROOT))
    monkeypatch.setenv("DEER_FLOW_CONFIG_PATH", str(REPO_ROOT / "config.yaml"))
    monkeypatch.setenv(
        "DEER_FLOW_EXTENSIONS_CONFIG_PATH",
        str(REPO_ROOT / "extensions_config.json"),
    )
    monkeypatch.setenv("OPENAI_CHAT_MODEL", os.getenv("OPENAI_CHAT_MODEL") or "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_API_BASE", os.getenv("OPENAI_API_BASE") or "http://127.0.0.1:9999/v1")
    monkeypatch.setenv("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY") or "test-key-for-harness-config")

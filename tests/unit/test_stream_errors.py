"""Tests for user-facing stream error messages."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))

from api.stream_errors import format_stream_error


def test_connection_error_translated():
    msg = format_stream_error(Exception("Connection error."))
    assert "无法连接 LLM" in msg
    assert "Admin" in msg or "模型" in msg

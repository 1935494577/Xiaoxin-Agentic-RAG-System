"""Langfuse helper tests."""

import sys
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evaluation.langfuse_trace import (  # noqa: E402
    langfuse_enabled,
    langfuse_trace_url,
)


@patch("evaluation.langfuse_trace.langfuse_package_installed", return_value=False)
@patch("evaluation.langfuse_trace.langfuse_credentials_configured", return_value=True)
@patch("evaluation.langfuse_trace.langfuse_tracing_flag_on", return_value=True)
def test_disabled_without_package(_a, _b, _c):
    assert langfuse_enabled() is False


@patch("evaluation.langfuse_trace.langfuse_package_installed", return_value=True)
@patch("evaluation.langfuse_trace.langfuse_credentials_configured", return_value=True)
@patch("evaluation.langfuse_trace.langfuse_tracing_flag_on", return_value=True)
@patch("evaluation.langfuse_trace.langfuse_host", return_value="https://lf.example")
def test_trace_url(_host, _c, _b, _a):
    url = langfuse_trace_url("abc123")
    assert url == "https://lf.example/trace/abc123"

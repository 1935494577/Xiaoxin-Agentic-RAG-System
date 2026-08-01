"""Local trace status tests."""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evaluation.local_trace import get_trace_status  # noqa: E402


def test_local_path_points_to_data_dir():
    status = get_trace_status()
    path = status["local_path"].replace("\\", "/")
    assert "/enterprise_rag/data/chat_trace.jsonl" in path
    assert path.count("enterprise_rag/enterprise_rag") == 0


def test_status_has_diagnostics():
    status = get_trace_status()
    assert "backend" in status
    assert "local_enabled" in status
    assert "langfuse_enabled" in status
    assert "hints" in status
    assert isinstance(status["hints"], list)

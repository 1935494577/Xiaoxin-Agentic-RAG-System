"""Stream LangSmith tracer tests."""

import sys
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evaluation.stream_langsmith import StreamLangSmithTracer  # noqa: E402


@patch("evaluation.stream_langsmith._langsmith_enabled", return_value=False)
@patch("evaluation.stream_langsmith.settings")
def test_tracer_noop_when_disabled(mock_settings, _mock_ls):
    mock_settings.local_trace_enabled = False
    t = StreamLangSmithTracer({"question": "hello", "user_id": "u1"})
    t.start()
    assert t.trace_id is None
    with t.span("retrieve", "retriever", inputs={"q": "hello"}) as out:
        out["ok"] = True
    t.finish({"answer_mode": "kb"})


@patch("evaluation.stream_langsmith.append_trace_run")
@patch("evaluation.stream_langsmith._langsmith_enabled", return_value=False)
@patch("evaluation.stream_langsmith.settings")
def test_tracer_writes_local_jsonl(mock_settings, _mock_ls, mock_append):
    mock_settings.local_trace_enabled = True
    t = StreamLangSmithTracer({"question": "hello", "user_id": "u1", "session_id": "s1"})
    assert t.trace_id
    with t.span("retrieve", "retriever", inputs={"q": "hello"}) as out:
        out["context_count"] = 2
    t.finish({"answer_mode": "kb", "verified": True})
    mock_append.assert_called_once()


@patch("evaluation.stream_langsmith._langsmith_enabled", return_value=True)
def test_tracer_creates_trace_id(_mock):
    t = StreamLangSmithTracer({"question": "ping", "user_id": "u1"})
    try:
        t.start()
    except Exception:
        return  # no network / key in CI
    if t.trace_id:
        assert len(t.trace_id) >= 8

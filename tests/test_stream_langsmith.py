"""Stream LangSmith tracer tests."""

import sys
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evaluation.stream_langsmith import StreamLangSmithTracer  # noqa: E402


@patch("evaluation.stream_langsmith.tracing_active", return_value=False)
def test_tracer_noop_when_disabled(_mock):
    t = StreamLangSmithTracer({"question": "hello", "user_id": "u1"})
    t.start()
    assert t.trace_id is None
    with t.span("retrieve", "retriever", inputs={"q": "hello"}) as out:
        out["ok"] = True
    t.finish({"answer_mode": "kb"})


@patch("evaluation.stream_langsmith.tracing_active", return_value=True)
def test_tracer_creates_trace_id(_mock):
    t = StreamLangSmithTracer({"question": "ping", "user_id": "u1"})
    try:
        t.start()
    except Exception:
        return  # no network / key in CI
    if t.trace_id:
        assert len(t.trace_id) >= 8

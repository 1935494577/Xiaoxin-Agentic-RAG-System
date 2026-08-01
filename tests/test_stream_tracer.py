"""Stream tracer tests."""

import sys
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evaluation.stream_tracer import StreamTracer  # noqa: E402


@patch("evaluation.stream_tracer.settings")
def test_tracer_noop_when_disabled(mock_settings):
    mock_settings.local_trace_enabled = False
    t = StreamTracer({"question": "hello", "user_id": "u1"})
    assert t.trace_id
    assert len(t.trace_id) >= 8
    with t.span("retrieve", "retriever", inputs={"q": "hello"}) as out:
        out["ok"] = True
    t.finish({"answer_mode": "kb"})


@patch("evaluation.stream_tracer.append_trace_run")
@patch("evaluation.stream_tracer.settings")
def test_tracer_writes_local_jsonl(mock_settings, mock_append):
    mock_settings.local_trace_enabled = True
    t = StreamTracer({"question": "hello", "user_id": "u1", "session_id": "s1"})
    assert t.trace_id
    with t.span("retrieve", "retriever", inputs={"q": "hello"}) as out:
        out["context_count"] = 2
    t.finish({"answer_mode": "kb", "verified": True})
    mock_append.assert_called_once()


@patch("evaluation.stream_tracer.langfuse_enabled", return_value=True)
@patch("evaluation.stream_tracer.get_langfuse_client")
@patch("evaluation.stream_tracer.settings")
def test_tracer_langfuse_root_trace_id(mock_settings, mock_get_client, _lf_on):
    mock_settings.local_trace_enabled = False

    class FakeObs:
        trace_id = "lf-trace-99"

    class FakeCm:
        def __enter__(self):
            return FakeObs()

        def __exit__(self, *args):
            return False

    class FakeClient:
        def start_as_current_observation(self, **kwargs):
            return FakeCm()

    mock_get_client.return_value = FakeClient()

    with patch("langfuse.propagate_attributes") as mock_prop:
        mock_prop.return_value = FakeCm()
        t = StreamTracer({"question": "hi", "user_id": "u1", "session_id": "s1"})
        t.start()
    assert t.trace_id == "lf-trace-99"

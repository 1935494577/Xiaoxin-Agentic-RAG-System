"""Trace event model tests."""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evaluation.trace_events import TraceCollector  # noqa: E402


def test_span_hierarchy_and_latency():
    col = TraceCollector(question="hello")
    with col.span("run", "chat", input={"q": "hello"}):
        with col.span("retrieval", "hybrid_search", input={"top_k": 5}) as child:
            pass
    col.finish(answer_mode="kb")
    rec = col.run.to_record()
    assert rec["trace_id"]
    assert len(rec["spans"]) == 2
    assert rec["spans"][1]["parent_id"] == rec["spans"][0]["span_id"]
    assert rec["spans"][1]["latency_ms"] is not None

"""FeedbackStore / TraceStore abstractions (Sprint E4)."""

from feedback_loop.stores import (
    FeedbackStore,
    JsonlTraceStore,
    SqliteFeedbackStore,
    TraceStore,
    get_feedback_store,
    get_trace_store,
)


def test_store_protocol_instances():
    fb = get_feedback_store()
    tr = get_trace_store()
    assert isinstance(fb, FeedbackStore)
    assert isinstance(tr, TraceStore)
    assert isinstance(fb, SqliteFeedbackStore)
    assert isinstance(tr, JsonlTraceStore)

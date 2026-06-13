"""Stream retrieval profile tests."""

from api.stream_retrieval import build_stream_retrieval_state


def test_standard_vs_fast_profiles():
    std = build_stream_retrieval_state(False)
    fast = build_stream_retrieval_state(True)
    assert std["skip_rerank"] is False
    assert fast["skip_rerank"] is False
    assert std["context_max_chars"] == 0
    assert fast["context_max_chars"] > 0
    assert std["retrieve_top_k"] > fast["retrieve_top_k"]

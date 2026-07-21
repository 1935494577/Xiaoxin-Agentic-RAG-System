"""Token usage helpers used by Admin Token 用量 page."""

from __future__ import annotations


def test_thread_token_usage_route_shape():
    from jnao_harness.gateway.routers.token_usage import ThreadTokenUsageResponse

    empty = ThreadTokenUsageResponse(thread_id="t1")
    assert empty.total_tokens == 0
    assert empty.by_model == {}
    assert empty.by_caller.total_tokens == 0

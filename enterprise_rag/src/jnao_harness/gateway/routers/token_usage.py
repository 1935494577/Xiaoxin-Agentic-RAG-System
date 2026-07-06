"""Thread-level token usage (Jnao RunStore aggregation)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/threads", tags=["token-usage"])


class ThreadTokenUsageModelBreakdown(BaseModel):
    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_runs: int = 0


class ThreadTokenUsageCallerBreakdown(BaseModel):
    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0


class ThreadTokenUsageResponse(BaseModel):
    thread_id: str
    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_runs: int = 0
    by_model: dict[str, ThreadTokenUsageModelBreakdown] = Field(default_factory=dict)
    by_caller: ThreadTokenUsageCallerBreakdown = Field(default_factory=ThreadTokenUsageCallerBreakdown)


@router.get("/{thread_id}/token-usage", response_model=ThreadTokenUsageResponse)
async def thread_token_usage(
    thread_id: str,
    request: Request,
    include_active: bool = Query(default=False),
) -> ThreadTokenUsageResponse:
    """Thread-level token usage aggregation (DeerFlow ``thread_runs`` parity)."""
    try:
        from jnao_harness.gateway.deps import get_run_store

        run_store = get_run_store(request)
    except HTTPException as exc:
        if exc.status_code == 503:
            return ThreadTokenUsageResponse(thread_id=thread_id)
        raise

    if include_active:
        agg = await run_store.aggregate_tokens_by_thread(thread_id, include_active=True)
    else:
        agg = await run_store.aggregate_tokens_by_thread(thread_id)
    return ThreadTokenUsageResponse(thread_id=thread_id, **agg)

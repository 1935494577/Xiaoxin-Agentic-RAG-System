"""Independent Jnao token usage APIs (SQLite). Not DeerFlow RunStore."""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/threads", tags=["token-usage"])
summary_router = APIRouter(prefix="/api/token-usage", tags=["token-usage"])


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


class TokenUsageCallRecord(BaseModel):
    id: str
    created_at: str = ""
    session_id: str = ""
    user_id: str = ""
    channel: str = ""
    model: str = ""
    caller: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    question_preview: str = ""


class TokenUsageSummaryResponse(BaseModel):
    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_calls: int = 0
    # Compat aliases for existing Admin UI metrics
    total_runs: int = 0
    total_llm_calls: int = 0
    by_model: dict[str, ThreadTokenUsageModelBreakdown] = Field(default_factory=dict)
    records: list[TokenUsageCallRecord] = Field(default_factory=list)
    source: str = "jnao_sqlite"
    available: bool = True


@router.get("/{thread_id}/token-usage", response_model=ThreadTokenUsageResponse)
async def thread_token_usage(
    thread_id: str,
    include_active: bool = Query(default=False),
) -> ThreadTokenUsageResponse:
    """Session-level token usage from local SQLite (Chat badge)."""
    del include_active  # local store has no "active run" concept
    from api.token_usage_store import summarize_session

    agg = summarize_session(thread_id)
    by_model = {
        name: ThreadTokenUsageModelBreakdown(**row) if isinstance(row, dict) else row
        for name, row in (agg.get("by_model") or {}).items()
    }
    return ThreadTokenUsageResponse(
        thread_id=thread_id,
        total_tokens=int(agg.get("total_tokens") or 0),
        total_input_tokens=int(agg.get("total_input_tokens") or 0),
        total_output_tokens=int(agg.get("total_output_tokens") or 0),
        total_runs=int(agg.get("total_runs") or 0),
        by_model=by_model,
    )


@summary_router.get("/summary", response_model=TokenUsageSummaryResponse)
async def token_usage_summary(
    limit: int = Query(default=100, ge=1, le=500),
) -> TokenUsageSummaryResponse:
    """Global totals + recent per-call records for Admin Token 用量."""
    from api.token_usage_store import summarize_calls

    out = summarize_calls(limit=limit)
    total_calls = int(out.get("total_calls") or 0)
    by_model = {
        name: ThreadTokenUsageModelBreakdown(**row) if isinstance(row, dict) else row
        for name, row in (out.get("by_model") or {}).items()
    }
    records = [TokenUsageCallRecord(**row) for row in (out.get("records") or [])]
    return TokenUsageSummaryResponse(
        total_tokens=int(out.get("total_tokens") or 0),
        total_input_tokens=int(out.get("total_input_tokens") or 0),
        total_output_tokens=int(out.get("total_output_tokens") or 0),
        total_calls=total_calls,
        total_runs=total_calls,
        total_llm_calls=total_calls,
        by_model=by_model,
        records=records,
        source="jnao_sqlite",
        available=True,
    )

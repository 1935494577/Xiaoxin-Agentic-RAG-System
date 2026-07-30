"""Admin ops digest API."""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/ops", tags=["ops"])


class OpsDigestTokenUsage(BaseModel):
    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_calls: int = 0


class OpsDigestFeedback(BaseModel):
    total: int = 0
    positive: int = 0
    negative: int = 0
    pending_triage: int = 0
    retrieval_miss: int = 0


class OpsDigestResponse(BaseModel):
    since: str = ""
    since_days: int = 1
    token_usage: OpsDigestTokenUsage = Field(default_factory=OpsDigestTokenUsage)
    feedback: OpsDigestFeedback = Field(default_factory=OpsDigestFeedback)
    generated_at: str = ""


@router.get("/digest", response_model=OpsDigestResponse)
def get_ops_digest(since_days: int = Query(default=1, ge=1, le=30)) -> OpsDigestResponse:
    """Lightweight KPIs for Admin (token + feedback window)."""
    from api.ops_digest import build_ops_digest

    raw = build_ops_digest(since_days=since_days)
    return OpsDigestResponse(
        since=str(raw.get("since") or ""),
        since_days=int(raw.get("since_days") or since_days),
        token_usage=OpsDigestTokenUsage(**(raw.get("token_usage") or {})),
        feedback=OpsDigestFeedback(**(raw.get("feedback") or {})),
        generated_at=str(raw.get("generated_at") or ""),
    )

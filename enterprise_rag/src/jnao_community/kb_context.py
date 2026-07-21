"""Jnao run context → legacy kb_search context bridge."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any


@dataclass
class KbRunContext:
    user_department: str = "general"
    allowed_sources: list[str] | None = None
    chat_model: str | None = None
    llm_api_base: str | None = None
    llm_api_key: str | None = None
    top_k: int = 5
    skip_rerank: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


_kb_run_context: ContextVar[KbRunContext | None] = ContextVar("kb_run_context", default=None)


def bind_kb_run_context(
    *,
    user_department: str = "general",
    allowed_sources: list[str] | None = None,
    chat_model: str | None = None,
    llm_api_base: str | None = None,
    llm_api_key: str | None = None,
    top_k: int = 5,
    skip_rerank: bool = False,
    **extra: Any,
) -> Token:
    ctx = KbRunContext(
        user_department=user_department,
        allowed_sources=list(allowed_sources) if allowed_sources else None,
        chat_model=chat_model,
        llm_api_base=llm_api_base,
        llm_api_key=llm_api_key,
        top_k=top_k,
        skip_rerank=skip_rerank,
        extra=dict(extra),
    )
    return _kb_run_context.set(ctx)


def clear_kb_run_context() -> None:
    _kb_run_context.set(None)


def get_kb_run_context() -> KbRunContext | None:
    return _kb_run_context.get()


def apply_kb_run_context_to_legacy() -> None:
    """Push ContextVar state into agent.tools.builtins.kb_search module context."""
    from agent.tools.builtins.kb_search import clear_kb_search_context, set_kb_search_context

    ctx = _kb_run_context.get()
    if ctx is None:
        clear_kb_search_context()
        return
    set_kb_search_context(
        user_department=ctx.user_department,
        allowed_sources=ctx.allowed_sources,
        chat_model=ctx.chat_model,
        llm_api_base=ctx.llm_api_base,
        llm_api_key=ctx.llm_api_key,
        top_k=ctx.top_k,
        skip_rerank=ctx.skip_rerank,
        hits=[],
        **ctx.extra,
    )

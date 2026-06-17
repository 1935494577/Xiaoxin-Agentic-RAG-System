"""Store abstractions for feedback and trace (Sprint E4)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from feedback_loop import store as _sqlite_feedback
from feedback_loop.trace_loader import load_trace_by_id as _load_trace


@runtime_checkable
class FeedbackStore(Protocol):
    def insert(
        self,
        *,
        user_id: str,
        rating: int,
        tenant_id: str = "internal",
        trace_id: str | None = None,
        session_id: str | None = None,
        message_id: str | None = None,
        question: str | None = None,
        answer_preview: str | None = None,
        answer_mode: str | None = None,
        correction: str | None = None,
    ) -> str: ...

    def get(self, feedback_id: str) -> dict[str, Any] | None: ...

    def list(
        self,
        *,
        tenant_id: str = "internal",
        user_id: str | None = None,
        trace_id: str | None = None,
        rating: int | None = None,
        status: str | None = None,
        sort: str = "created_desc",
        since_days: int | None = 7,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict[str, Any]], int]: ...


@runtime_checkable
class TraceStore(Protocol):
    def load_by_id(self, trace_id: str) -> dict[str, Any] | None: ...


class SqliteFeedbackStore:
    """SQLite implementation of FeedbackStore (current production backend)."""

    def insert(self, **kwargs: Any) -> str:
        return _sqlite_feedback.insert_feedback(**kwargs)

    def get(self, feedback_id: str) -> dict[str, Any] | None:
        return _sqlite_feedback.get_feedback(feedback_id)

    def list(self, **kwargs: Any) -> tuple[list[dict[str, Any]], int]:
        return _sqlite_feedback.list_feedback(**kwargs)


class JsonlTraceStore:
    """Local JSONL trace backend."""

    def load_by_id(self, trace_id: str) -> dict[str, Any] | None:
        return _load_trace(trace_id)


_default_feedback_store = SqliteFeedbackStore()
_default_trace_store = JsonlTraceStore()


def get_feedback_store() -> FeedbackStore:
    return _default_feedback_store


def get_trace_store() -> TraceStore:
    return _default_trace_store

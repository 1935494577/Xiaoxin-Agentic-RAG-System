"""Agent trace event model — foundation for full-chain observability.

Future: graph nodes, tool calls, LLM reasoning, performance spans.
Sinks: local JSONL (chat_trace.jsonl), LangSmith (optional).
"""

from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Literal

from config import settings

SpanType = Literal[
    "run",
    "graph_node",
    "tool_call",
    "llm_call",
    "retrieval",
    "verifier",
    "router",
    "fallback",
]

SpanStatus = Literal["ok", "error", "skipped"]


def new_trace_id() -> str:
    return uuid.uuid4().hex


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TraceSpan:
    """One unit of work in an agent run (node, tool, LLM call, etc.)."""

    span_id: str
    trace_id: str
    type: SpanType
    name: str
    status: SpanStatus = "ok"
    parent_id: str | None = None
    started_at: str = field(default_factory=_utc_now)
    ended_at: str | None = None
    latency_ms: float | None = None
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def finish(
        self,
        *,
        status: SpanStatus = "ok",
        output: dict[str, Any] | None = None,
        error: str | None = None,
        started_mono: float | None = None,
    ) -> None:
        self.ended_at = _utc_now()
        if started_mono is not None:
            self.latency_ms = round((time.perf_counter() - started_mono) * 1000, 2)
        self.status = status
        if output is not None:
            self.output = output
        if error:
            self.error = error
            self.status = "error"


@dataclass
class TraceRun:
    """Top-level record for one user request."""

    trace_id: str
    session_id: str | None = None
    user_id: str | None = None
    question: str = ""
    answer_mode: str | None = None
    started_at: str = field(default_factory=_utc_now)
    ended_at: str | None = None
    spans: list[TraceSpan] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "question": self.question,
            "answer_mode": self.answer_mode,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "meta": self.meta,
            "spans": [asdict(s) for s in self.spans],
        }


class TraceCollector:
    """In-memory span collector for one request; flush via append_trace_run."""

    def __init__(
        self,
        *,
        trace_id: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
        question: str = "",
    ) -> None:
        self.run = TraceRun(
            trace_id=trace_id or new_trace_id(),
            session_id=session_id,
            user_id=user_id,
            question=question,
        )
        self._span_stack: list[str] = []

    @property
    def trace_id(self) -> str:
        return self.run.trace_id

    def _parent_id(self) -> str | None:
        return self._span_stack[-1] if self._span_stack else None

    @contextmanager
    def span(
        self,
        span_type: SpanType,
        name: str,
        *,
        input: dict[str, Any] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> Iterator[TraceSpan]:
        sp = TraceSpan(
            span_id=uuid.uuid4().hex[:16],
            trace_id=self.run.trace_id,
            type=span_type,
            name=name,
            parent_id=self._parent_id(),
            input=input,
            meta=meta or {},
        )
        self.run.spans.append(sp)
        self._span_stack.append(sp.span_id)
        t0 = time.perf_counter()
        try:
            yield sp
        except Exception as e:
            sp.finish(status="error", error=str(e)[:500], started_mono=t0)
            raise
        else:
            if sp.ended_at is None:
                sp.finish(started_mono=t0)
        finally:
            self._span_stack.pop()

    def finish(self, *, answer_mode: str | None = None, meta: dict[str, Any] | None = None) -> TraceRun:
        self.run.ended_at = _utc_now()
        if answer_mode:
            self.run.answer_mode = answer_mode
        if meta:
            self.run.meta.update(meta)
        return self.run


def append_trace_run(run: TraceRun) -> Path | None:
    """Append one trace run to local JSONL when enabled."""
    if not settings.local_trace_enabled:
        return None
    path = Path(settings.chat_trace_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(run.to_record(), ensure_ascii=False)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    return path

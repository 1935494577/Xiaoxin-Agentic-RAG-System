"""LangSmith tracing for /chat/stream (OpenAI streaming path)."""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from typing import Any, Iterator

from evaluation.langsmith_trace import tracing_active


def _project_name() -> str | None:
    from config import settings

    proj = (settings.langchain_project or "").strip()
    return proj or None


def _safe_meta(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": state.get("user_id"),
        "user_department": state.get("user_department"),
        "stream_fast_mode": bool(state.get("stream_fast_mode")),
        "chat_model": state.get("chat_model"),
    }


class StreamLangSmithTracer:
    """Manual RunTree spans mirroring LangGraph nodes for stream chat."""

    def __init__(self, state: dict[str, Any]) -> None:
        self.enabled = tracing_active()
        self.state = state
        self.trace_id: str | None = None
        self._root: Any = None

    def start(self) -> None:
        if not self.enabled:
            return
        try:
            from langsmith.run_trees import RunTree
        except ImportError:
            self.enabled = False
            return

        q = str(self.state.get("question") or "")
        self._root = RunTree(
            name="stream_rag_chat",
            run_type="chain",
            inputs={"question": q, **_safe_meta(self.state)},
            project_name=_project_name(),
            tags=["stream", "chat-spa"],
        )
        self._root.post()
        self.trace_id = str(self._root.id)

    @contextmanager
    def span(
        self,
        name: str,
        run_type: str,
        *,
        inputs: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield a mutable outputs dict; record span latency to LangSmith."""
        bucket: dict[str, Any] = {}
        if not self.enabled or self._root is None:
            yield bucket
            return

        from langsmith.run_trees import RunTree

        child: RunTree = self._root.create_child(
            name=name,
            run_type=run_type,  # type: ignore[arg-type]
            inputs=inputs or {},
        )
        child.post()
        t0 = time.perf_counter()
        err: str | None = None
        try:
            yield bucket
        except Exception as e:
            err = str(e)[:500]
            raise
        finally:
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            out = dict(bucket)
            out.setdefault("latency_ms", latency_ms)
            if err:
                child.end(outputs=out or None, error=err)
            else:
                child.end(outputs=out or None)

    def finish(self, outputs: dict[str, Any], *, error: str | None = None) -> None:
        if not self.enabled or self._root is None:
            return
        try:
            if error:
                self._root.end(outputs=outputs or None, error=error)
            else:
                self._root.end(outputs=outputs)
            self._root.patch()
        except Exception:
            pass


def new_stream_tracer(state: dict[str, Any]) -> StreamLangSmithTracer:
    tracer = StreamLangSmithTracer(state)
    tracer.start()
    return tracer


def langsmith_run_url(trace_id: str | None) -> str | None:
    if not trace_id or not tracing_active():
        return None
    return f"https://smith.langchain.com/o/default/projects/p/traces/{trace_id}"

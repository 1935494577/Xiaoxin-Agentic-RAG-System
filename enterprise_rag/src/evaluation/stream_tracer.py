"""Dual-sink tracing for /chat/stream: local JSONL + optional Langfuse v4."""

from __future__ import annotations

import time
from contextlib import AbstractContextManager, contextmanager
from typing import Any, Iterator

from config import settings
from evaluation.langfuse_trace import flush_langfuse, get_langfuse_client, langfuse_enabled
from evaluation.trace_events import TraceCollector, append_trace_run, new_trace_id

_SPAN_TYPES: dict[str, str] = {
    "retrieve": "retrieval",
    "route": "router",
    "draft": "llm_call",
    "fallback": "fallback",
    "verifier": "verifier",
}

_GENERATION_NAMES = frozenset({"draft", "fallback"})


def _safe_meta(state: dict[str, Any]) -> dict[str, Any]:
    mem = state.get("memory_config") or {}
    turn = state.get("turn_meta") or {}
    return {
        "user_id": state.get("user_id"),
        "user_department": state.get("user_department"),
        "session_id": state.get("session_id"),
        "stream_fast_mode": bool(state.get("stream_fast_mode")),
        "chat_model": state.get("chat_model"),
        "routing_model": state.get("routing_model"),
        "assistant_mode": mem.get("_assistant_mode") or state.get("assistant_mode"),
        "chat_routing_tier": mem.get("chat_routing_tier"),
        "condense_used_llm": turn.get("condense_used_llm"),
        "retrieval_mode": turn.get("retrieval_mode"),
    }


class StreamTracer:
    """Per-request spans: JSONL (Admin 反馈) + Langfuse UI (optional)."""

    def __init__(self, state: dict[str, Any]) -> None:
        self.state = state
        self.trace_id: str = new_trace_id()
        self._local: TraceCollector | None = None
        self._lf = langfuse_enabled()
        self._lf_client: Any | None = None
        self._propagate_cm: AbstractContextManager[Any] | None = None
        self._root_cm: AbstractContextManager[Any] | None = None
        self._root_obs: Any | None = None

        if settings.local_trace_enabled:
            self._local = TraceCollector(
                trace_id=self.trace_id,
                session_id=state.get("session_id"),
                user_id=state.get("user_id"),
                question=str(state.get("question") or ""),
            )

    def start(self) -> None:
        if not self._lf:
            return
        client = get_langfuse_client()
        if client is None:
            self._lf = False
            return
        self._lf_client = client
        question = str(self.state.get("question") or "")
        meta = _safe_meta(self.state)
        user_id = str(meta.get("user_id") or "").strip() or None
        session_id = str(meta.get("session_id") or "").strip() or None
        try:
            from langfuse import propagate_attributes

            self._propagate_cm = propagate_attributes(
                user_id=user_id,
                session_id=session_id,
                trace_name="stream_rag_chat",
                metadata={k: v for k, v in meta.items() if v is not None},
                tags=["jnao", "chat-stream"],
            )
            self._propagate_cm.__enter__()
            self._root_cm = self._lf_client.start_as_current_observation(
                as_type="span",
                name="stream_rag_chat",
                input={"question": question, **meta},
            )
            self._root_obs = self._root_cm.__enter__()
            lf_trace_id = getattr(self._root_obs, "trace_id", None)
            if lf_trace_id:
                self.trace_id = str(lf_trace_id)
                if self._local is not None:
                    self._local.run.trace_id = self.trace_id
        except Exception:
            self._lf = False
            self._lf_client = None
            self._close_langfuse_contexts()

    def _close_langfuse_contexts(self) -> None:
        if self._root_cm is not None:
            try:
                self._root_cm.__exit__(None, None, None)
            except Exception:
                pass
            self._root_cm = None
            self._root_obs = None
        if self._propagate_cm is not None:
            try:
                self._propagate_cm.__exit__(None, None, None)
            except Exception:
                pass
            self._propagate_cm = None

    @contextmanager
    def span(
        self,
        name: str,
        run_type: str,
        *,
        inputs: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        bucket: dict[str, Any] = {}
        span_inputs = inputs or {}
        t0 = time.perf_counter()
        err: str | None = None
        local_type = _SPAN_TYPES.get(name, "run")

        lf_cm: AbstractContextManager[Any] | None = None
        lf_obs: Any | None = None
        if self._lf and self._lf_client is not None:
            as_type = "generation" if name in _GENERATION_NAMES else "span"
            obs_name = f"{name}/{run_type}"
            kwargs: dict[str, Any] = {
                "as_type": as_type,
                "name": obs_name,
                "input": span_inputs,
            }
            model = str(span_inputs.get("model") or "").strip()
            if as_type == "generation" and model:
                kwargs["model"] = model
            try:
                lf_cm = self._lf_client.start_as_current_observation(**kwargs)
                lf_obs = lf_cm.__enter__()
            except Exception:
                lf_cm = None
                lf_obs = None

        try:
            if self._local is not None:
                with self._local.span(local_type, name, input=span_inputs) as sp:  # type: ignore[arg-type]
                    try:
                        yield bucket
                    except Exception as e:
                        err = str(e)[:500]
                        if sp.ended_at is None:
                            sp.finish(status="error", error=err, started_mono=t0)
                        raise
                    else:
                        if sp.ended_at is None:
                            sp.finish(
                                output={"result": bucket} if bucket else None,
                                started_mono=t0,
                            )
            else:
                yield bucket
        finally:
            if lf_obs is not None and lf_cm is not None:
                latency_ms = round((time.perf_counter() - t0) * 1000, 2)
                out = dict(bucket)
                out.setdefault("latency_ms", latency_ms)
                try:
                    if err:
                        lf_obs.update(output=out or None, level="ERROR", status_message=err)
                    else:
                        lf_obs.update(output=out or None)
                except Exception:
                    pass
                try:
                    lf_cm.__exit__(None, None, None)
                except Exception:
                    pass

    def finish(self, outputs: dict[str, Any], *, error: str | None = None) -> None:
        if self._local is not None:
            run = self._local.finish(
                answer_mode=str(outputs.get("answer_mode") or "") or None,
                meta={k: v for k, v in outputs.items() if k != "answer_mode"},
            )
            if error:
                run.meta["error"] = error
            append_trace_run(run)

        if self._root_obs is not None:
            try:
                if error:
                    self._root_obs.update(output=outputs or None, level="ERROR", status_message=error)
                else:
                    self._root_obs.update(output=outputs or None)
            except Exception:
                pass
        self._close_langfuse_contexts()
        if self._lf:
            flush_langfuse()


def new_stream_tracer(state: dict[str, Any]) -> StreamTracer:
    tracer = StreamTracer(state)
    tracer.start()
    return tracer

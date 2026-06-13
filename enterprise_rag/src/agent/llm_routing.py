"""Resolve routing vs answer models for preprocessors (condense, kb judge, summary)."""

from __future__ import annotations

from typing import Any, Literal

from config import settings

TaskModel = Literal["routing", "answer"]


def model_for_task(runtime: dict[str, Any], *, task: TaskModel = "routing") -> str:
    """Answer generation uses chat_model; preprocessors prefer routing_model."""
    answer = (runtime.get("chat_model") or "").strip() or settings.openai_chat_model
    if task == "answer":
        return answer
    routing = (runtime.get("routing_model") or "").strip()
    if routing:
        return routing
    fallback = (settings.openai_routing_model or "").strip()
    if fallback:
        return fallback
    return answer


def routing_llm_runtime(runtime: dict[str, Any]) -> dict[str, Any]:
    """Copy runtime with chat_model swapped to routing_model for preprocessor calls."""
    out = dict(runtime)
    out["chat_model"] = model_for_task(runtime, task="routing")
    return out

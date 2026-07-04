"""Assistant mode profiles: knowledge / task / auto."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

AssistantMode = Literal["knowledge", "task", "auto"]

_VALID: frozenset[str] = frozenset({"knowledge", "task", "auto"})


def normalize_assistant_mode(raw: str | None) -> AssistantMode:
    key = (raw or "auto").strip().lower()
    if key in _VALID:
        return key  # type: ignore[return-value]
    return "auto"


@dataclass(frozen=True)
class ModeProfile:
    mode: AssistantMode
    hybrid_expert_mode: bool | None
    rag_architecture: str | None
    agent_reasoning_mode: str | None
    stream_fast_mode: bool | None
    force_tools: bool


def build_mode_profile(mode: AssistantMode, ui_config: dict[str, Any]) -> ModeProfile:
    if mode == "knowledge":
        return ModeProfile(
            mode="knowledge",
            hybrid_expert_mode=False,
            rag_architecture="auto",
            agent_reasoning_mode="direct",
            stream_fast_mode=True,
            force_tools=False,
        )
    if mode == "task":
        return ModeProfile(
            mode="task",
            hybrid_expert_mode=True,
            rag_architecture="agentic",
            agent_reasoning_mode="react",
            stream_fast_mode=False,
            force_tools=True,
        )
    return ModeProfile(
        mode="auto",
        hybrid_expert_mode=None,
        rag_architecture=None,
        agent_reasoning_mode=None,
        stream_fast_mode=None,
        force_tools=False,
    )

"""Resolve assistant mode and apply runtime overrides."""

from __future__ import annotations

from typing import Any

from agent.runtime.modes import AssistantMode, ModeProfile, build_mode_profile, normalize_assistant_mode


def resolve_effective_mode(request_mode: str | None, ui_config: dict[str, Any]) -> AssistantMode:
    if request_mode and normalize_assistant_mode(request_mode) != "auto":
        return normalize_assistant_mode(request_mode)
    return normalize_assistant_mode(str(ui_config.get("default_assistant_mode") or "knowledge"))


def resolve_mode_profile(
    request_mode: str | None,
    ui_config: dict[str, Any],
) -> ModeProfile:
    mode = resolve_effective_mode(request_mode, ui_config)
    return build_mode_profile(mode, ui_config)


def apply_mode_to_memory(mem: dict[str, Any], profile: ModeProfile) -> dict[str, Any]:
    out = dict(mem)
    if profile.agent_reasoning_mode:
        out["agent_reasoning_mode"] = profile.agent_reasoning_mode
    out["_assistant_mode"] = profile.mode
    out["_assistant_force_tools"] = profile.force_tools
    return out


def pick_hybrid_expert_mode(profile: ModeProfile, ui_default: bool) -> bool:
    """Hybrid routing is driven by assistant mode; ui_default applies only to unresolved auto."""
    if profile.hybrid_expert_mode is not None:
        return profile.hybrid_expert_mode
    return bool(ui_default)


def pick_stream_fast_mode(
    profile: ModeProfile,
    request_value: bool | None,
    ui_default: bool,
) -> bool:
    if profile.stream_fast_mode is not None:
        return profile.stream_fast_mode
    if request_value is not None:
        return bool(request_value)
    return bool(ui_default)


def pick_rag_architecture_override(
    profile: ModeProfile,
    request_value: str | None,
) -> str | None:
    if profile.rag_architecture:
        return profile.rag_architecture
    return request_value

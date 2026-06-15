"""Agent reasoning / orchestration modes for general+tools path."""

from __future__ import annotations

from typing import Any, Literal

ReasoningMode = Literal["direct", "react", "plan_execute"]

DEFAULT_REASONING_MODE: ReasoningMode = "react"

REASONING_MODES: dict[str, dict[str, str]] = {
    "direct": {
        "label": "直接回答",
        "description": "不调用对话工具，单次生成（最快，适合纯知识库或常识题）。",
        "policy": (
            "【思考模式 · 直接回答】"
            "不要调用任何对话工具；基于已有上下文、对话历史与常识直接组织回答。"
            "若缺少实时信息，明确说明无法获取，不要编造。"
        ),
    },
    "react": {
        "label": "ReAct（推理+行动）",
        "description": "模型按需调用工具，观察结果后继续推理（默认，适合实时信息）。",
        "policy": (
            "【思考模式 · ReAct】"
            "采用 ReAct：先判断是否需要工具，再调用工具获取事实，根据工具结果继续推理，最后给出完整回答。"
            "每次工具调用应有明确目的；避免重复搜索相同内容。"
        ),
    },
    "plan_execute": {
        "label": "Plan-and-Execute（先计划后执行）",
        "description": "先列简要计划再逐步调用工具，适合多步骤调研类问题。",
        "policy": (
            "【思考模式 · Plan-and-Execute】"
            "在调用任何工具之前，先在心中拟定 2–5 步简要计划（无需向用户展示完整计划）。"
            "再按步骤依次调用工具，每步只解决一个子问题，最后综合所有结果给出结构化回答。"
            "若计划中途发现方向错误，可修订计划并说明依据。"
        ),
    },
}


def normalize_reasoning_mode(raw: str | None) -> ReasoningMode:
    key = (raw or DEFAULT_REASONING_MODE).strip().lower()
    if key in REASONING_MODES:
        return key  # type: ignore[return-value]
    return DEFAULT_REASONING_MODE


def list_reasoning_modes_public() -> list[dict[str, str]]:
    return [
        {"id": mid, "label": meta["label"], "description": meta["description"]}
        for mid, meta in REASONING_MODES.items()
    ]


def reasoning_policy(mode: str | None) -> str:
    meta = REASONING_MODES.get(normalize_reasoning_mode(mode), {})
    return str(meta.get("policy") or "").strip()


def should_use_tool_loop(mode: str | None, *, tools_enabled: bool) -> bool:
    if not tools_enabled:
        return False
    return normalize_reasoning_mode(mode) in ("react", "plan_execute")

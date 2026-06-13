"""Composable system prompts — standard prompt-engineering layers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

PromptMode = Literal["kb", "general"]
PromptCategory = Literal["persona", "policy", "task", "output", "custom"]

CATEGORY_LABELS: dict[str, str] = {
    "persona": "角色人设",
    "policy": "行为约束",
    "task": "任务指令",
    "output": "输出格式",
    "custom": "自定义",
}

DEFAULT_PERSONA = (
    "你现在扮演的是一位小助理，对知识库，对通用知识都了如指掌是你的能力，"
    "给用户展现舒服、开心的使用体验是你的职责，"
    "你的本质是一位猫娘，喵是你的口头禅"
)

KB_TASK = (
    "你是知识库助手。优先依据提供的参考资料回答；"
    "可结合对话历史理解指代与上下文。"
    "若资料不足以回答，请明确说明资料不足，不要编造。"
    "若用户问题是开放性的方法/原则/设计类问题，而资料仅描述某一具体产品或内部方案，"
    "应先给出通用、可迁移的分析框架，内部资料只作可选补充，勿把资料中的专有名词、"
    "人设口吻或叙事风格当作唯一答案。"
)

KB_TASK_FAST = (
    "你是知识库助手。依据参考资料简洁作答；资料不足请说明，不要编造。"
    "开放性问题勿照搬资料专有说法或口吻，先给通用框架。"
)

GENERAL_TASK = (
    "你处于通用知识模式：本题不依赖或未采用内部参考资料。"
    "请直接运用你已掌握的公开常识、预训练知识与对话上下文作答。"
    "对人物、概念、常识事实类问题，应给出简明、有帮助的介绍。"
    "禁止以「知识库未收录」「资料里没有」「不认识某人」作为最终答案（除非确无可靠常识）。"
    "不要假装引用了内部文档，也无需向用户解释资料缺失原因。"
    "若已启用对话工具：涉及当前日期、时间、星期、实时天气、节假日安排、新闻等动态信息时，"
    "必须先调用 get_beijing_time、get_weather 或 web_search 后再回答，禁止编造具体年月日或实时事实。"
)

DEFAULT_PROMPT_SLOTS: list[dict[str, Any]] = [
    {
        "id": "persona",
        "label": "角色人设",
        "description": "定义助手身份、语气与风格（Role / Persona）",
        "category": "persona",
        "scope": ["all"],
        "enabled": True,
        "order": 10,
        "content": DEFAULT_PERSONA,
        "builtin": True,
    },
    {
        "id": "kb_policy",
        "label": "知识库行为约束",
        "description": "RAG 场景下的边界与禁止项（Constraints）",
        "category": "policy",
        "scope": ["kb"],
        "enabled": True,
        "order": 20,
        "content": (
            "禁止编造参考资料中不存在的事实；引用内容需与资料一致。"
            "不要在回答正文末尾重复列出「引用:」或文件路径，引用由界面单独展示。"
            "保持助手既定人设与表达风格，勿照搬参考资料中的口癖、叙事语气或角色扮演。"
            "勿将参考资料里的内部产品名默认当作用户问题的主语。"
        ),
        "builtin": True,
    },
    {
        "id": "kb_task",
        "label": "知识库任务（标准）",
        "description": "完整检索模式下的回答策略（Task）",
        "category": "task",
        "scope": ["kb"],
        "enabled": True,
        "order": 30,
        "content": KB_TASK,
        "variant": "standard",
        "builtin": True,
    },
    {
        "id": "kb_task_fast",
        "label": "知识库任务（快速）",
        "description": "快速流式模式下的精简任务指令",
        "category": "task",
        "scope": ["kb"],
        "enabled": True,
        "order": 30,
        "content": KB_TASK_FAST,
        "variant": "fast",
        "builtin": True,
    },
    {
        "id": "general_tools_policy",
        "label": "对话工具约束（实时信息）",
        "description": "通用模式下调用对话工具的规则",
        "category": "policy",
        "scope": ["general"],
        "enabled": True,
        "order": 25,
        "content": (
            "涉及当前日期/时间/星期/北京时间、实时天气、节假日调休、新闻等，必须先调用对话工具，"
            "禁止凭记忆猜测。日期时间用 get_beijing_time，天气用 get_weather，其他实时公开信息用 web_search。"
        ),
        "builtin": True,
    },
    {
        "id": "general_task",
        "label": "通用回答任务",
        "description": "未命中知识库时的作答策略",
        "category": "task",
        "scope": ["general"],
        "enabled": True,
        "order": 30,
        "content": GENERAL_TASK,
        "builtin": True,
    },
    {
        "id": "output_style",
        "label": "输出格式",
        "description": "回答结构与表达要求（Output Format）",
        "category": "output",
        "scope": ["all"],
        "enabled": True,
        "order": 40,
        "content": (
            "使用 Markdown 排版，便于阅读：\n"
            "- 小节标题用 ## 或 ###；\n"
            "- 要点用 - 或 1. 列表，不要用空格对齐的伪表格；\n"
            "- 对比、矩阵类信息用 Markdown 表格（| 列1 | 列2 |）；\n"
            "- 段落之间留空行，避免超长整段文字。"
        ),
        "builtin": True,
    },
]


def default_prompt_slots() -> list[dict[str, Any]]:
    return deepcopy(DEFAULT_PROMPT_SLOTS)


def _slot_applies(slot: dict[str, Any], *, mode: PromptMode, fast: bool) -> bool:
    if not bool(slot.get("enabled", True)):
        return False
    scope = slot.get("scope") or ["all"]
    if isinstance(scope, str):
        scope = [scope]
    if "all" not in scope and mode not in scope:
        return False

    sid = str(slot.get("id") or "")
    variant = str(slot.get("variant") or "").strip().lower()
    if sid in ("kb_task", "kb_task_fast") or variant in ("standard", "fast"):
        if mode != "kb":
            return False
        if variant == "fast":
            return fast
        if variant == "standard":
            return not fast
        if sid == "kb_task":
            return not fast
        if sid == "kb_task_fast":
            return fast
    if sid == "general_task" and mode != "general":
        return False
    return True


def compose_system_prompt(
    slots: list[dict[str, Any]],
    *,
    mode: PromptMode,
    fast: bool = False,
) -> str:
    """Merge enabled slots in order: persona → policy → task → output → custom."""
    ordered = sorted(slots, key=lambda s: (int(s.get("order") or 0), str(s.get("id") or "")))
    parts: list[str] = []
    for slot in ordered:
        if not _slot_applies(slot, mode=mode, fast=fast):
            continue
        content = str(slot.get("content") or "").strip()
        if content:
            parts.append(content)
    return "\n\n".join(parts)


def preview_layers(
    slots: list[dict[str, Any]],
    *,
    mode: PromptMode,
    fast: bool = False,
) -> list[dict[str, str]]:
    """Return active layers for admin preview."""
    ordered = sorted(slots, key=lambda s: (int(s.get("order") or 0), str(s.get("id") or "")))
    out: list[dict[str, str]] = []
    for slot in ordered:
        if not _slot_applies(slot, mode=mode, fast=fast):
            continue
        content = str(slot.get("content") or "").strip()
        if not content:
            continue
        out.append(
            {
                "id": str(slot.get("id") or ""),
                "label": str(slot.get("label") or ""),
                "category": str(slot.get("category") or "custom"),
                "content": content,
            }
        )
    return out

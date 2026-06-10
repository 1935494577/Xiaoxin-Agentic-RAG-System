"""System prompts and user payloads for kb vs general answering."""

from __future__ import annotations

from typing import Any

from agent.prompt_engine import compose_system_prompt

GENERAL_WORLD_USER_HINT = (
    "（本题请用通用常识作答：若属于公众熟知的人物/概念/事实，请直接介绍，"
    "勿再强调内部知识库是否收录。）"
)


def _resolve_slots(slots: list[dict[str, Any]] | None, persona: str | None) -> list[dict[str, Any]]:
    if slots is not None:
        return slots
    if persona:
        from agent.prompt_engine import default_prompt_slots

        merged = default_prompt_slots()
        for slot in merged:
            if slot.get("id") == "persona":
                slot["content"] = persona.strip()
                break
        return merged
    from api.prompt_config_store import load_prompt_slots

    return load_prompt_slots()


def kb_system_prompt(
    *,
    fast: bool = False,
    slots: list[dict[str, Any]] | None = None,
    persona: str | None = None,
) -> str:
    resolved = _resolve_slots(slots, persona)
    return compose_system_prompt(resolved, mode="kb", fast=fast)


def general_system_prompt(
    *,
    slots: list[dict[str, Any]] | None = None,
    persona: str | None = None,
) -> str:
    resolved = _resolve_slots(slots, persona)
    return compose_system_prompt(resolved, mode="general", fast=False)


def kb_user_content(contexts: list[str], question: str) -> str:
    body = "\n".join(f"[{i + 1}] {t}" for i, t in enumerate(contexts))
    return f"参考资料：\n{body}\n\n用户问题：{question}"


def general_user_content(question: str, *, world_knowledge: bool = True) -> str:
    q = f"用户问题：{question}"
    if world_knowledge:
        return f"{q}\n{GENERAL_WORLD_USER_HINT}"
    return q

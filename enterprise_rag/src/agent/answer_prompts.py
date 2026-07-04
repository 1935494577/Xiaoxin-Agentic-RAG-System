"""System prompts and user payloads for kb vs general answering."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from agent.prompt_engine import KB_TASK_STRICT, KB_TASK_STRICT_FAST, compose_system_prompt
from agent.reasoning_modes import reasoning_policy

_BJ = timezone(timedelta(hours=8))
_WEEKDAYS = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")

GENERAL_WORLD_USER_HINT = (
    "（本题请用通用常识作答：若属于公众熟知的人物/概念/事实，请直接介绍，"
    "勿再强调内部知识库是否收录。）"
)

GENERAL_KB_SUPPLEMENT_HINT = (
    "（若下方提供了内部参考资料：仅在与本题直接相关时酌情补充；"
    "若资料只涉及某一具体产品/方案而本题是开放性方法或设计问题，请以通用框架为主，"
    "可忽略不相关细节，勿照搬资料口吻。）"
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


def _format_time_anchor_local() -> str:
    now = datetime.now(_BJ)
    weekday = _WEEKDAYS[now.weekday()]
    hour = now.hour
    if hour < 6:
        period = "凌晨"
    elif hour < 12:
        period = "上午"
    elif hour < 18:
        period = "下午"
    else:
        period = "晚上"
    return (
        f"【时间基准】北京时间：{now.strftime('%Y年%m月%d日')} {weekday} "
        f"{period} {now.strftime('%H:%M')}（向用户汇报日期与时刻必须与此一致；"
        f"涉及年份、趋势、时事时请以此为准，勿假设仍在训练数据截止年之前）"
    )


def _with_time_anchor(text: str) -> str:
    """Inject server clock so the model does not assume a stale training-era year."""
    anchor = _format_time_anchor_local()
    if anchor in text:
        return text
    return f"{text}\n\n{anchor}"


def kb_system_prompt(
    *,
    fast: bool = False,
    slots: list[dict[str, Any]] | None = None,
    persona: str | None = None,
    reasoning_mode: str | None = None,
    strict_kb_only: bool = False,
) -> str:
    resolved = _resolve_slots(slots, persona)
    if strict_kb_only:
        resolved = [dict(s) for s in resolved]
        strict_text = KB_TASK_STRICT_FAST if fast else KB_TASK_STRICT
        for slot in resolved:
            if str(slot.get("id") or "") in ("kb_task", "kb_task_fast"):
                slot["content"] = strict_text
    text = compose_system_prompt(resolved, mode="kb", fast=fast)
    policy = reasoning_policy(reasoning_mode)
    merged = f"{text}\n\n{policy}" if policy else text
    return _with_time_anchor(merged)


def general_system_prompt(
    *,
    slots: list[dict[str, Any]] | None = None,
    persona: str | None = None,
    reasoning_mode: str | None = None,
) -> str:
    resolved = _resolve_slots(slots, persona)
    text = compose_system_prompt(resolved, mode="general", fast=False)
    policy = reasoning_policy(reasoning_mode)
    merged = f"{text}\n\n{policy}" if policy else text
    return _with_time_anchor(merged)


def kb_user_content(contexts: list[str], question: str) -> str:
    body = "\n".join(f"[{i + 1}] {t}" for i, t in enumerate(contexts))
    return f"参考资料：\n{body}\n\n用户问题：{question}"


def general_user_content(
    question: str,
    *,
    world_knowledge: bool = True,
    contexts: list[str] | None = None,
) -> str:
    q = f"用户问题：{question}"
    hints: list[str] = []
    if world_knowledge:
        hints.append(GENERAL_WORLD_USER_HINT)
    ctx = [str(c).strip() for c in (contexts or []) if str(c).strip()]
    if ctx:
        hints.append(GENERAL_KB_SUPPLEMENT_HINT)
        body = "\n".join(f"[{i + 1}] {t}" for i, t in enumerate(ctx[:5]))
        return f"{q}\n" + "\n".join(hints) + f"\n\n可选内部参考：\n{body}"
    if hints:
        return f"{q}\n{hints[0]}"
    return q

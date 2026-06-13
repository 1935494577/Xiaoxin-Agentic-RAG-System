"""L3: rolling conversation summary (async refresh after message persist)."""

from __future__ import annotations

import logging
from typing import Any

from config import settings
from openai import OpenAI

from agent.llm_routing import model_for_task

logger = logging.getLogger(__name__)


def should_update_summary(
    *,
    turn_count: int,
    history_chars: int,
    every_n_turns: int = 6,
    min_chars: int = 3500,
) -> bool:
    """Whether to trigger async summary refresh."""
    n = max(1, int(every_n_turns))
    if turn_count < 2:
        return False
    if int(history_chars) < int(min_chars):
        return False
    return turn_count % n == 0


def count_user_turns(messages: list[dict[str, Any]]) -> int:
    return sum(1 for m in messages if str(m.get("role") or "") == "user")


def history_char_count(messages: list[dict[str, Any]]) -> int:
    return sum(len(str(m.get("content") or "")) for m in messages)


def format_messages_for_summary(messages: list[dict[str, Any]], *, max_messages: int = 16) -> str:
    tail = messages[-max(2, max_messages):]
    lines: list[str] = []
    for m in tail:
        role = str(m.get("role") or "user")
        content = str(m.get("content") or "").strip()
        if not content:
            continue
        label = "用户" if role == "user" else "助手"
        lines.append(f"{label}：{content[:600]}")
    return "\n".join(lines)


def augment_system_with_summary(system: str, rolling_summary: str | None) -> str:
    summary = (rolling_summary or "").strip()
    if not summary:
        return system
    return (
        f"{system.rstrip()}\n\n"
        f"【此前对话摘要（仅供参考，若与当前问题无关请忽略）】\n"
        f"{summary}"
    )


def summarize_conversation(
    *,
    previous_summary: str,
    messages: list[dict[str, Any]],
    llm_runtime: dict[str, Any] | None = None,
    max_tokens: int = 400,
) -> str:
    """Merge previous summary with recent turns into a compact rolling summary."""
    runtime = llm_runtime or {}
    api_key = (runtime.get("llm_api_key") or "").strip() or settings.openai_api_key
    if not api_key:
        return previous_summary

    api_base = (runtime.get("llm_api_base") or "").strip() or settings.openai_api_base
    headers = runtime.get("llm_extra_headers")
    client_kw: dict[str, Any] = {"api_key": api_key, "base_url": api_base}
    if isinstance(headers, dict) and headers:
        client_kw["default_headers"] = headers
    client = OpenAI(**client_kw)
    model = model_for_task(runtime, task="routing")

    dialog = format_messages_for_summary(messages)
    prev = (previous_summary or "").strip()
    user = (
        f"旧摘要：\n{prev or '（无）'}\n\n"
        f"近期对话：\n{dialog}\n\n"
        "请输出更新后的对话摘要（300字以内，中文，保留关键实体与结论，不要列点编号）。"
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "你是企业对话摘要助手，只输出摘要正文，不要解释。",
            },
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=max(64, int(max_tokens)),
    )
    text = (resp.choices[0].message.content or "").strip()
    return text[:4000] if text else prev


def refresh_rolling_summary_for_session(
    session_id: str,
    user_id: str,
    memory_config: dict[str, Any] | None = None,
    llm_runtime: dict[str, Any] | None = None,
) -> None:
    """
    Background task: refresh session rolling_summary when thresholds met.
    Failures are logged and ignored (must not affect chat).
    """
    from api.chat_session_store import get_rolling_summary, list_messages, set_rolling_summary

    mem = memory_config or {}
    if not bool(mem.get("rolling_summary_enabled", True)):
        return

    sid = (session_id or "").strip()
    uid = (user_id or "").strip()
    if not sid or not uid:
        return

    try:
        messages = list_messages(sid, uid)
        turns = count_user_turns(messages)
        chars = history_char_count(messages)
        every_n = int(mem.get("rolling_summary_every_n_turns") or 6)
        min_chars = int(mem.get("rolling_summary_min_chars") or 3500)
        if not should_update_summary(
            turn_count=turns,
            history_chars=chars,
            every_n_turns=every_n,
            min_chars=min_chars,
        ):
            return

        prev = get_rolling_summary(sid, uid)
        summary = summarize_conversation(
            previous_summary=prev,
            messages=messages,
            llm_runtime=llm_runtime,
            max_tokens=int(mem.get("rolling_summary_max_tokens") or 400),
        )
        if summary:
            set_rolling_summary(sid, uid, summary)
    except Exception:
        logger.exception("rolling_summary refresh failed session=%s", sid)

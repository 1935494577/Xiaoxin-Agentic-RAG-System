"""Short-term conversation memory: trim history and build LLM message lists."""

from __future__ import annotations

from typing import Any

from api.chat_session_store import list_messages, get_session


def _char_len(messages: list[dict[str, Any]]) -> int:
    return sum(len(str(m.get("content") or "")) for m in messages)


def trim_history(
    messages: list[dict[str, Any]],
    *,
    max_turns: int,
    max_chars: int,
) -> list[dict[str, Any]]:
    """Keep the most recent turns within turn and character budgets."""
    if not messages:
        return []

    cleaned: list[dict[str, Any]] = []
    for m in messages:
        role = str(m.get("role") or "").strip().lower()
        content = str(m.get("content") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        cleaned.append({"role": role, "content": content})

    if max_turns > 0:
        # One turn = user (+ optional assistant)
        max_msgs = max(1, int(max_turns) * 2)
        cleaned = cleaned[-max_msgs:]

    if max_chars > 0:
        while cleaned and _char_len(cleaned) > int(max_chars):
            cleaned.pop(0)

    return cleaned


def load_session_history(user_id: str, session_id: str, *, limit: int = 40) -> list[dict[str, Any]]:
    if not get_session(session_id, user_id):
        return []
    rows = list_messages(session_id, user_id)
    out: list[dict[str, Any]] = []
    for row in rows[-limit:]:
        role = str(row.get("role") or "").strip().lower()
        content = str(row.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            out.append({"role": role, "content": content})
    return out


def resolve_chat_history(
    *,
    request_history: list[dict[str, Any]] | None,
    user_id: str,
    session_id: str | None,
    max_turns: int,
    max_chars: int,
    long_term_enabled: bool = True,
) -> list[dict[str, Any]]:
    """Merge client history with SQLite session history, then trim."""
    base: list[dict[str, Any]] = []
    if request_history:
        base = list(request_history)
    elif long_term_enabled and session_id and user_id:
        base = load_session_history(user_id, session_id)

    return trim_history(base, max_turns=max_turns, max_chars=max_chars)


def build_llm_messages(
    *,
    system: str,
    history: list[dict[str, Any]],
    user_content: str,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for m in history:
        messages.append({"role": str(m["role"]), "content": str(m["content"])})
    messages.append({"role": "user", "content": user_content})
    return messages

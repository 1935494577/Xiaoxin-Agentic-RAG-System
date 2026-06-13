"""L1: standalone query generation + topic shift detection (single LLM call)."""

from __future__ import annotations

import json
import re
from typing import Any

from config import settings
from openai import OpenAI

from agent.llm_routing import model_for_task

from agent.conversation.types import CondenseResult

_REFERENTIAL = re.compile(
    r"(它|这个|那个|那次|刚才|上面|之前说的|继续|还有呢|然后呢|同样|也呢|那|呢\？|\?)",
    re.IGNORECASE,
)

_STANDALONE_MIN_LEN = 36


def needs_condense(message: str, history: list[dict[str, Any]]) -> bool:
    """Heuristic: skip LLM when message is likely self-contained."""
    if not history:
        return False
    msg = (message or "").strip()
    if not msg:
        return False
    if _REFERENTIAL.search(msg):
        return True
    if len(msg) < _STANDALONE_MIN_LEN:
        return True
    return False


def _format_history_tail(history: list[dict[str, Any]], *, max_turns: int = 4) -> str:
    tail = history[-max(1, max_turns) * 2 :]
    lines: list[str] = []
    for m in tail:
        role = str(m.get("role") or "user")
        content = str(m.get("content") or "").strip()
        if not content:
            continue
        label = "用户" if role == "user" else "助手"
        lines.append(f"{label}：{content[:400]}")
    return "\n".join(lines)


def parse_condense_response(raw: str) -> tuple[str, bool]:
    text = (raw or "").strip()
    if not text:
        return "", False

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            q = str(data.get("standalone_query") or data.get("query") or "").strip()
            shift = bool(data.get("topic_shift", False))
            if q:
                return q, shift
    except json.JSONDecodeError:
        pass

    shift = "topic_shift" in text.lower() and "true" in text.lower()
    q = ""
    for line in text.splitlines():
        line = line.strip()
        if line.lower().startswith("standalone_query"):
            q = line.split(":", 1)[-1].strip().strip('"')
            break
    if not q:
        q = text.splitlines()[0].strip()
    return q, shift


def condense_turn(
    message: str,
    history: list[dict[str, Any]],
    *,
    llm_runtime: dict[str, Any] | None = None,
    max_tokens: int | None = None,
    llm_enabled: bool = True,
) -> CondenseResult:
    """
    Produce standalone retrieval query and topic_shift flag.
    Uses one LLM call when history exists and heuristics say condense is needed.
    """
    msg = (message or "").strip()
    if not msg:
        return CondenseResult(standalone_query="", topic_shift=False, used_llm=False)
    if not history:
        return CondenseResult(standalone_query=msg, topic_shift=False, used_llm=False)
    if not needs_condense(msg, history):
        return CondenseResult(standalone_query=msg, topic_shift=False, used_llm=False)
    if not llm_enabled:
        return CondenseResult(standalone_query=msg, topic_shift=False, used_llm=False)

    runtime = llm_runtime or {}
    api_key = (runtime.get("llm_api_key") or "").strip() or settings.openai_api_key
    if not api_key:
        return CondenseResult(standalone_query=msg, topic_shift=False, used_llm=False)

    api_base = (runtime.get("llm_api_base") or "").strip() or settings.openai_api_base
    headers = runtime.get("llm_extra_headers")
    client_kw: dict[str, Any] = {"api_key": api_key, "base_url": api_base}
    if isinstance(headers, dict) and headers:
        client_kw["default_headers"] = headers
    client = OpenAI(**client_kw)
    model = model_for_task(runtime, task="routing")

    hist_text = _format_history_tail(history)
    system = (
        "你是多轮对话查询理解助手。根据最近对话，输出一行 JSON，不要其它文字。\n"
        '格式：{"standalone_query":"...","topic_shift":true|false}\n'
        "standalone_query：将当前用户消息改写为可独立用于搜索的完整问句（消解指代）。\n"
        "topic_shift：若用户明显切换到与上文无关的新话题则为 true，否则 false。"
    )
    user = f"最近对话：\n{hist_text}\n\n当前用户消息：{msg}"

    kw: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.0,
        "max_tokens": int(max_tokens) if max_tokens is not None else 128,
    }
    resp = client.chat.completions.create(**kw)
    raw = (resp.choices[0].message.content or "").strip()
    standalone, shift = parse_condense_response(raw)
    if not standalone:
        standalone = msg
    return CondenseResult(standalone_query=standalone, topic_shift=shift, used_llm=True)

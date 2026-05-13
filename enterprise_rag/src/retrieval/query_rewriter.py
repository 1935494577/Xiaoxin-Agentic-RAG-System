from __future__ import annotations

from typing import Any

from openai import OpenAI

from config import settings


def rewrite_query(
    user_query: str,
    chat_model: str | None = None,
    *,
    api_base: str | None = None,
    api_key: str | None = None,
    max_tokens: int | None = None,
    default_headers: dict[str, Any] | None = None,
) -> str:
    """将口语化问题改写为更利于检索的查询（可选 LLM）。"""
    key = api_key if (api_key is not None and str(api_key).strip() != "") else settings.openai_api_key
    base = api_base if (api_base is not None and str(api_base).strip() != "") else settings.openai_api_base
    if not key:
        return user_query
    model = (chat_model or "").strip() or settings.openai_chat_model
    client_kw: dict[str, Any] = {"api_key": key, "base_url": base}
    if default_headers:
        client_kw["default_headers"] = default_headers
    client = OpenAI(**client_kw)
    kw: dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "你是搜索查询改写助手。输出一行中文或英文检索式，不要解释。",
            },
            {"role": "user", "content": user_query},
        ],
        "temperature": 0.2,
    }
    if max_tokens is not None:
        kw["max_tokens"] = int(max_tokens)
    resp = client.chat.completions.create(**kw)
    text = (resp.choices[0].message.content or "").strip()
    return text or user_query

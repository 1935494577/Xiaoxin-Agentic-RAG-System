"""Probe OpenAI-compatible LLM endpoints for connectivity."""

from __future__ import annotations

from typing import Any

from openai import OpenAI


def test_llm_connection(
    *,
    api_base: str,
    api_key: str,
    model: str,
    extra_headers: dict[str, str] | None = None,
    timeout_sec: float = 15.0,
) -> tuple[bool, str]:
    key = (api_key or "").strip()
    base = (api_base or "").strip().rstrip("/")
    m = (model or "").strip()
    if not key:
        return False, "未配置 API Key"
    if not base:
        return False, "未配置 API Base"
    if not m:
        return False, "未配置模型名称"

    client_kw: dict[str, Any] = {"api_key": key, "base_url": base, "timeout": timeout_sec}
    if extra_headers:
        client_kw["default_headers"] = extra_headers
    try:
        client = OpenAI(**client_kw)
        resp = client.chat.completions.create(
            model=m,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=8,
            temperature=0,
        )
        _ = (resp.choices[0].message.content or "").strip()
        return True, "连接成功"
    except Exception as e:
        return False, str(e)[:400]

"""User-facing messages for streaming chat failures."""

from __future__ import annotations


def format_stream_error(exc: Exception | str) -> str:
    msg = str(exc).strip() if isinstance(exc, Exception) else str(exc or "").strip()
    if not msg and isinstance(exc, Exception):
        msg = exc.__class__.__name__
    if msg == "Connection error." or "Connection error" in msg:
        return (
            "无法连接 LLM 服务：请检查 Admin → 模型 中的 API Base / Key / 模型名，"
            "或 .env 中的 OPENAI_* 配置；也可访问 /health/llm 诊断。"
        )
    return msg[:400]

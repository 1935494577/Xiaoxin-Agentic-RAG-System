"""Speech-to-text via OpenAI-compatible Whisper API."""

from __future__ import annotations

import io
from typing import Any

from fastapi import HTTPException

from config import settings

MAX_TRANSCRIBE_BYTES = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "audio/webm",
    "audio/mp4",
    "audio/mpeg",
    "audio/wav",
    "audio/ogg",
    "audio/x-wav",
    "application/octet-stream",
}


def transcribe_audio_bytes(
    content: bytes,
    filename: str,
    *,
    language: str = "zh",
    api_key: str | None = None,
    api_base: str | None = None,
) -> str:
    """Transcribe audio bytes with whisper-1 (OpenAI-compatible)."""
    if not content:
        raise HTTPException(status_code=400, detail="音频为空")
    if len(content) > MAX_TRANSCRIBE_BYTES:
        raise HTTPException(status_code=400, detail="音频过大，请缩短录音后重试")

    key = (api_key or settings.openai_api_key or "").strip()
    if not key:
        raise HTTPException(
            status_code=400,
            detail="未配置 API Key：请在「模型配置」中保存密钥，或在 .env 中设置 OPENAI_API_KEY。",
        )

    from openai import OpenAI

    base = (api_base or settings.openai_api_base or "https://api.openai.com/v1").rstrip("/")
    client = OpenAI(api_key=key, base_url=base)

    bio = io.BytesIO(content)
    bio.name = filename or "speech.webm"

    kwargs: dict[str, Any] = {"model": "whisper-1", "file": bio}
    lang = (language or "").strip()
    if lang and lang.lower() not in {"auto", "detect"}:
        kwargs["language"] = lang

    try:
        resp = client.audio.transcriptions.create(**kwargs)
    except Exception as exc:  # noqa: BLE001 — surface provider errors to client
        raise HTTPException(status_code=502, detail=f"语音识别服务异常：{exc}") from exc

    return (getattr(resp, "text", None) or "").strip()

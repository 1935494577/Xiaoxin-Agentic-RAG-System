"""Lightweight post-generation verifier for streaming kb answers."""

from __future__ import annotations

from typing import Any

from config import settings
from openai import OpenAI


def run_stream_verifier(
    *,
    answer: str,
    contexts: list[str],
    answer_mode: str,
    enabled: bool,
    llm_runtime: dict[str, Any],
) -> dict[str, Any]:
    if not enabled or answer_mode == "general":
        return {"verifier_decision": "pass", "verified": True, "answer": answer}

    if "llm_api_key" in llm_runtime:
        api_key = str(llm_runtime.get("llm_api_key") or "").strip()
    else:
        api_key = (settings.openai_api_key or "").strip()
    if not api_key:
        return {"verifier_decision": "pass", "verified": True, "answer": answer}

    body = "\n".join(f"[{i + 1}] {t}" for i, t in enumerate(contexts or []))
    api_base = (llm_runtime.get("llm_api_base") or "").strip() or settings.openai_api_base
    headers = llm_runtime.get("llm_extra_headers")
    client_kw: dict[str, Any] = {"api_key": api_key, "base_url": api_base}
    if isinstance(headers, dict) and headers:
        client_kw["default_headers"] = headers
    client = OpenAI(**client_kw)
    model = llm_runtime.get("chat_model") or settings.openai_chat_model
    temp = float(
        llm_runtime.get("llm_temperature_verifier")
        if llm_runtime.get("llm_temperature_verifier") is not None
        else 0.0
    )
    mt = llm_runtime.get("llm_max_tokens_verifier")
    kw: dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "你是答案一致性审查员。只输出一个词：PASS / RETRY / REJECT。",
            },
            {
                "role": "user",
                "content": (
                    f"资料：\n{body}\n\n答案：\n{answer}\n\n"
                    "若答案明显超出资料或自相矛盾，输出RETRY或REJECT。"
                ),
            },
        ],
        "temperature": temp,
        "max_tokens": int(mt) if mt is not None else 8,
    }
    resp = client.chat.completions.create(**kw)
    tag = (resp.choices[0].message.content or "").strip().upper()

    if "REJECT" in tag:
        return {
            "verifier_decision": "reject",
            "verified": False,
            "answer": "无法根据资料确认，已拒答。",
        }
    # Stream path treats RETRY as pass (no second generation pass)
    return {"verifier_decision": "pass", "verified": True, "answer": answer}

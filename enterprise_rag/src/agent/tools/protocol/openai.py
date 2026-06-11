"""OpenAI-compatible function-calling 协议层。"""

from __future__ import annotations

from typing import Any


def openai_tools_payload(enabled_ids: set[str], definitions: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for tid in sorted(enabled_ids):
        meta = definitions.get(tid)
        if not meta:
            continue
        out.append(
            {
                "type": "function",
                "function": {
                    "name": tid,
                    "description": str(meta.get("description") or meta.get("label") or tid),
                    "parameters": meta.get("parameters") or {"type": "object", "properties": {}},
                },
            }
        )
    return out

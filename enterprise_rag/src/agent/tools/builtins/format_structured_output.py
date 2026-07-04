"""Format assistant draft into a named output schema (structure hint for LLM follow-up)."""

from __future__ import annotations

import json

from agent.output_schemas import get_output_schema, list_output_schemas_public


def format_structured_output(content: str, schema_id: str) -> str:
    schema = get_output_schema(schema_id)
    if not schema:
        available = ", ".join(s["id"] for s in list_output_schemas_public())
        return json.dumps(
            {"ok": False, "error": f"未知 schema_id: {schema_id}", "available": available},
            ensure_ascii=False,
        )
    instruction = str(schema.get("instruction") or "").strip()
    body = (content or "").strip()
    return json.dumps(
        {
            "ok": True,
            "schema_id": schema_id,
            "label": schema.get("label"),
            "instruction": instruction,
            "content_to_format": body[:12000],
            "note": "请模型按 instruction 将 content_to_format 整理为最终输出；勿添加资料外事实。",
        },
        ensure_ascii=False,
        indent=2,
    )

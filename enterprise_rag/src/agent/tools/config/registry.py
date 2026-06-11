"""工具注册表：定义、启停、执行入口。"""

from __future__ import annotations

from typing import Any

from agent.tools.builtins import run_builtin
from agent.tools.config.store import load_json_config, save_json_config

TOOL_DEFINITIONS: dict[str, dict[str, Any]] = {
    "get_weather": {
        "label": "天气查询",
        "description": "查询指定城市或地区的当前天气（温度、体感、湿度、风速等）。",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市或地区名，例如：杭州、北京、上海",
                }
            },
            "required": ["city"],
        },
    },
}

DEFAULT_CONFIG: dict[str, Any] = {
    "chat_tools_enabled": True,
    "tools": {
        tid: {"enabled": True, "label": meta["label"]}
        for tid, meta in TOOL_DEFINITIONS.items()
    },
}


def load_tools_config() -> dict[str, Any]:
    return load_json_config(DEFAULT_CONFIG)


def save_tools_config(patch: dict[str, Any]) -> dict[str, Any]:
    current = load_tools_config()
    if "chat_tools_enabled" in patch:
        current["chat_tools_enabled"] = bool(patch["chat_tools_enabled"])
    if "tools" in patch and isinstance(patch["tools"], dict):
        for tid, row in patch["tools"].items():
            if tid in current["tools"] and isinstance(row, dict):
                current["tools"][tid].update(row)
    save_json_config(current)
    return current


def enabled_tool_ids(cfg: dict[str, Any] | None = None) -> set[str]:
    c = cfg or load_tools_config()
    if not bool(c.get("chat_tools_enabled", True)):
        return set()
    out: set[str] = set()
    for tid, row in (c.get("tools") or {}).items():
        if tid in TOOL_DEFINITIONS and isinstance(row, dict) and row.get("enabled", True):
            out.add(tid)
    return out


def public_tools_config(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    c = cfg or load_tools_config()
    tools = []
    for tid, meta in TOOL_DEFINITIONS.items():
        row = (c.get("tools") or {}).get(tid) or {}
        tools.append(
            {
                "id": tid,
                "label": row.get("label") or meta.get("label") or tid,
                "description": meta.get("description") or "",
                "enabled": bool(row.get("enabled", True)),
            }
        )
    return {
        "chat_tools_enabled": bool(c.get("chat_tools_enabled", True)),
        "tools": tools,
    }


def execute_tool(tool_id: str, arguments: dict[str, Any]) -> str:
    if tool_id not in TOOL_DEFINITIONS:
        return f"工具未注册：{tool_id}"
    return run_builtin(tool_id, arguments)

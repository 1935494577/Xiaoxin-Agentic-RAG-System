"""Known MCP server tool catalogs for Admin UI (static metadata)."""

from __future__ import annotations

from typing import Any

# ReefAPI HTTP MCP — https://reefapi.com/mcp
REEFAPI_MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "search_engines",
        "description": "按意图关键词发现引擎（如 amazon reviews、reddit comments）；无需 Key。",
        "requires_key": False,
        "parameters": [{"name": "keywords", "type": "string", "required": True}],
    },
    {
        "name": "get_catalog",
        "description": "列出账户可用全部引擎与分类；无需 Key。",
        "requires_key": False,
        "parameters": [],
    },
    {
        "name": "get_engine_schema",
        "description": "查看某引擎全部 action 与说明；无需 Key。",
        "requires_key": False,
        "parameters": [{"name": "engine", "type": "string", "required": True}],
    },
    {
        "name": "get_action_schema",
        "description": "查看某 action 必填/可选参数与返回字段；无需 Key。",
        "requires_key": False,
        "parameters": [
            {"name": "engine", "type": "string", "required": True},
            {"name": "action", "type": "string", "required": True},
        ],
    },
    {
        "name": "call_engine",
        "description": "调用引擎 action 拉取结构化实时数据；需 ReefAPI Key，失败不计费。",
        "requires_key": True,
        "parameters": [
            {"name": "engine", "type": "string", "required": True},
            {"name": "action", "type": "string", "required": True},
            {"name": "params", "type": "object", "required": False},
        ],
    },
]

REEFAPI_MCP_PRESET: dict[str, Any] = {
    "enabled": True,
    "type": "http",
    "command": None,
    "args": [],
    "env": {},
    "url": "https://api.reefapi.com/mcp",
    "headers": {"Authorization": "Bearer $REEFAPI_KEY"},
    "description": "ReefAPI 175+ 站点结构化实时数据（电商/社交/域名/房产等）",
}

_KNOWN_BY_NAME: dict[str, list[dict[str, Any]]] = {
    "reefapi": REEFAPI_MCP_TOOLS,
}


def tools_for_mcp_server(name: str, server: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return static tool catalog for a known MCP server."""
    key = (name or "").strip().lower()
    if key in _KNOWN_BY_NAME:
        return list(_KNOWN_BY_NAME[key])
    url = ""
    if isinstance(server, dict):
        url = str(server.get("url") or "").lower()
    if "api.reefapi.com" in url or "reefapi.com/mcp" in url:
        return list(REEFAPI_MCP_TOOLS)
    return []


def reefapi_suggested_server() -> dict[str, Any] | None:
    """Preset when REEFAPI_KEY is set but extensions_config has no reefapi entry."""
    from config import settings

    if not (settings.reefapi_key or "").strip():
        return None
    return dict(REEFAPI_MCP_PRESET)

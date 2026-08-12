"""Read/write extensions_config.json MCP section without importing deerflow.

Main API (8010) runs in .venv which may not include the harness deerflow package;
Gateway (8011) reloads MCP tools after we persist here and proxy cache reset.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from jnao_harness.paths import repo_root


def resolve_config_path() -> Path:
    env = (os.getenv("DEER_FLOW_EXTENSIONS_CONFIG_PATH") or "").strip()
    if env:
        return Path(env).resolve()
    return repo_root() / "extensions_config.json"


def load_extensions_raw() -> tuple[Path, dict[str, Any]]:
    path = resolve_config_path()
    if not path.is_file():
        return path, {"mcpServers": {}, "skills": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return path, {"mcpServers": {}, "skills": {}}
    return path, data


def read_mcp_servers_raw() -> dict[str, dict[str, Any]]:
    _, raw = load_extensions_raw()
    servers = raw.get("mcpServers") or {}
    if not isinstance(servers, dict):
        return {}
    return {str(k): v for k, v in servers.items() if isinstance(v, dict)}


def write_mcp_servers(mcp_servers: dict[str, dict[str, Any]]) -> Path:
    path, raw = load_extensions_raw()
    other = {k: v for k, v in raw.items() if k not in ("mcpServers", "skills")}
    skills = raw.get("skills")
    if not isinstance(skills, dict):
        skills = {}
    payload = {**other, "mcpServers": mcp_servers, "skills": skills}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def reset_local_mcp_cache_if_available() -> None:
    try:
        from deerflow.mcp.cache import reset_mcp_tools_cache
    except ImportError:
        return
    reset_mcp_tools_cache()


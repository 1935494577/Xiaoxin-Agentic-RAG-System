"""Agent 工具配置持久化。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import settings


def config_path() -> Path:
    return Path(
        getattr(settings, "agent_tools_path", settings.ui_config_path.parent / "agent_tools.json")
    )


def load_json_config(default: dict[str, Any]) -> dict[str, Any]:
    path = config_path()
    if not path.is_file():
        return json.loads(json.dumps(default))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return json.loads(json.dumps(default))
    merged = json.loads(json.dumps(default))
    merged.update({k: v for k, v in data.items() if k != "tools"})
    tools = merged.get("tools") or {}
    for tid, row in (data.get("tools") or {}).items():
        if tid in tools and isinstance(row, dict):
            tools[tid].update(row)
    merged["tools"] = tools
    return merged


def save_json_config(current: dict[str, Any]) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")

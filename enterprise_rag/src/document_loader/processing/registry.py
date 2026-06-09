"""Processing tool configuration persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import settings

DEFAULT_CONFIG: dict[str, Any] = {
    "use_llm_router": True,
    "tools": {
        "extract_plain": {"enabled": True, "label": "纯文本解析"},
        "extract_pdf": {"enabled": True, "label": "PDF 解析"},
        "extract_office_html": {"enabled": True, "label": "Office/HTML 解析"},
        "scrub_whitespace": {"enabled": True, "label": "空白规范化"},
        "strip_watermarks": {"enabled": True, "label": "水印行过滤"},
        "redact_pii": {"enabled": True, "label": "敏感信息脱敏"},
    },
    "extension_map": {
        ".txt": "extract_plain",
        ".md": "extract_plain",
        ".markdown": "extract_plain",
        ".pdf": "extract_pdf",
        ".docx": "extract_office_html",
        ".html": "extract_office_html",
        ".htm": "extract_office_html",
    },
}


def _path() -> Path:
    p = getattr(settings, "processing_tools_path", None)
    if p:
        return Path(p)
    return settings.ui_config_path.parent / "processing_tools.json"


def load_config() -> dict[str, Any]:
    path = _path()
    if not path.is_file():
        return json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return json.loads(json.dumps(DEFAULT_CONFIG))
    merged = json.loads(json.dumps(DEFAULT_CONFIG))
    merged.update({k: v for k, v in data.items() if k != "tools"})
    tools = merged.get("tools") or {}
    for tid, row in (data.get("tools") or {}).items():
        if tid in tools and isinstance(row, dict):
            tools[tid].update(row)
    merged["tools"] = tools
    ext = data.get("extension_map")
    if isinstance(ext, dict):
        merged["extension_map"] = {**merged.get("extension_map", {}), **ext}
    return merged


def save_config(patch: dict[str, Any]) -> dict[str, Any]:
    current = load_config()
    if "use_llm_router" in patch:
        current["use_llm_router"] = bool(patch["use_llm_router"])
    if "tools" in patch and isinstance(patch["tools"], dict):
        for tid, row in patch["tools"].items():
            if tid in current["tools"] and isinstance(row, dict):
                current["tools"][tid].update(row)
    if "extension_map" in patch and isinstance(patch["extension_map"], dict):
        current["extension_map"] = {**current.get("extension_map", {}), **patch["extension_map"]}
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return current


def enabled_tool_ids(cfg: dict[str, Any] | None = None) -> set[str]:
    c = cfg or load_config()
    out: set[str] = set()
    for tid, row in (c.get("tools") or {}).items():
        if isinstance(row, dict) and row.get("enabled", True):
            out.add(tid)
    return out


def public_config(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    c = cfg or load_config()
    tools = []
    for tid, row in (c.get("tools") or {}).items():
        if not isinstance(row, dict):
            continue
        tools.append(
            {
                "id": tid,
                "label": row.get("label") or tid,
                "enabled": bool(row.get("enabled", True)),
            }
        )
    return {
        "use_llm_router": bool(c.get("use_llm_router", True)),
        "tools": tools,
        "extension_map": dict(c.get("extension_map") or {}),
    }

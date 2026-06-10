"""Persist pluggable prompt slots (admin-configurable)."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from agent.prompt_engine import CATEGORY_LABELS, default_prompt_slots
from config import settings

_SLOT_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_BUILTIN_IDS = {s["id"] for s in default_prompt_slots()}


def _config_path() -> Path:
    return Path(settings.prompt_config_path)


def _merge_builtin_defaults(stored: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep user edits for known ids; append missing builtins."""
    by_id = {str(s.get("id") or ""): s for s in stored if s.get("id")}
    merged: list[dict[str, Any]] = []
    for default in default_prompt_slots():
        sid = default["id"]
        if sid in by_id:
            row = dict(default)
            row.update(by_id[sid])
            row["id"] = sid
            row["builtin"] = True
            merged.append(row)
            del by_id[sid]
        else:
            merged.append(deepcopy(default))
    for sid, row in sorted(by_id.items()):
        if sid in _BUILTIN_IDS:
            continue
        custom = dict(row)
        custom.setdefault("builtin", False)
        custom.setdefault("category", "custom")
        custom.setdefault("scope", ["all"])
        custom.setdefault("enabled", True)
        custom.setdefault("order", 100)
        merged.append(custom)
    return merged


def _migrate_persona_from_ui(slots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        from api.ui_config_store import load_ui_config
    except Exception:
        return slots
    legacy = str(load_ui_config().get("chat_persona_prompt") or "").strip()
    if not legacy:
        return slots
    out = deepcopy(slots)
    for slot in out:
        if slot.get("id") == "persona":
            slot["content"] = legacy
            break
    return out


def load_prompt_config() -> dict[str, Any]:
    path = _config_path()
    if not path.is_file():
        slots = _migrate_persona_from_ui(default_prompt_slots())
        return {"version": 1, "slots": slots, "categories": CATEGORY_LABELS}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("invalid root")
        raw_slots = data.get("slots")
        if not isinstance(raw_slots, list):
            raw_slots = []
        slots = _merge_builtin_defaults(raw_slots)
        return {"version": int(data.get("version") or 1), "slots": slots, "categories": CATEGORY_LABELS}
    except Exception:
        slots = _migrate_persona_from_ui(default_prompt_slots())
        return {"version": 1, "slots": slots, "categories": CATEGORY_LABELS}


def load_prompt_slots() -> list[dict[str, Any]]:
    return load_prompt_config()["slots"]


def _normalize_slot(row: dict[str, Any], *, allow_new: bool = False) -> dict[str, Any] | None:
    sid = str(row.get("id") or "").strip().lower()
    if not sid or not _SLOT_ID_RE.match(sid):
        return None
    if sid in _BUILTIN_IDS:
        allow_new = True
    elif not allow_new:
        return None
    label = str(row.get("label") or sid).strip()[:64] or sid
    category = str(row.get("category") or "custom").strip().lower()
    if category not in CATEGORY_LABELS:
        category = "custom"
    scope = row.get("scope") or ["all"]
    if isinstance(scope, str):
        scope = [scope]
    scope = [str(x).strip().lower() for x in scope if str(x).strip()]
    if not scope:
        scope = ["all"]
    for s in scope:
        if s not in ("all", "kb", "general"):
            return None
    content = str(row.get("content") or "").strip()[:8000]
    order = int(row.get("order") or 100)
    order = max(0, min(order, 9999))
    builtin = sid in _BUILTIN_IDS
    out: dict[str, Any] = {
        "id": sid,
        "label": label,
        "description": str(row.get("description") or "")[:256],
        "category": category,
        "scope": scope,
        "enabled": bool(row.get("enabled", True)),
        "order": order,
        "content": content,
        "builtin": builtin,
    }
    variant = str(row.get("variant") or "").strip().lower()
    if variant in ("standard", "fast"):
        out["variant"] = variant
    return out


def save_prompt_config(
    *,
    slots: list[dict[str, Any]] | None = None,
    reset_defaults: bool = False,
) -> dict[str, Any]:
    if reset_defaults:
        merged = default_prompt_slots()
    elif slots is None:
        merged = load_prompt_slots()
    else:
        existing = {s["id"]: s for s in load_prompt_slots()}
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        for raw in slots:
            sid_raw = str(raw.get("id") or "").strip().lower()
            allow_new = sid_raw not in _BUILTIN_IDS
            norm = _normalize_slot(raw, allow_new=allow_new)
            if norm is None:
                continue
            sid = norm["id"]
            if sid in seen:
                continue
            seen.add(sid)
            if sid in _BUILTIN_IDS:
                base = next(d for d in default_prompt_slots() if d["id"] == sid)
                row = dict(base)
                row.update(norm)
                row["builtin"] = True
                merged.append(row)
            else:
                norm["builtin"] = False
                merged.append(norm)
        for sid, base in ((d["id"], d) for d in default_prompt_slots()):
            if sid not in seen:
                merged.append(dict(existing.get(sid, base)))
        merged = _merge_builtin_defaults(merged)

    payload = {"version": 1, "slots": merged}
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return load_prompt_config()


def public_prompt_config(*, mode: str = "kb", fast: bool = False) -> dict[str, Any]:
    from agent.prompt_engine import compose_system_prompt, preview_layers

    cfg = load_prompt_config()
    slots = cfg["slots"]
    m: str = mode if mode in ("kb", "general") else "kb"
    return {
        **cfg,
        "preview": {
            "mode": m,
            "fast": fast,
            "layers": preview_layers(slots, mode=m, fast=fast),  # type: ignore[arg-type]
            "composed": compose_system_prompt(slots, mode=m, fast=fast),  # type: ignore[arg-type]
        },
    }

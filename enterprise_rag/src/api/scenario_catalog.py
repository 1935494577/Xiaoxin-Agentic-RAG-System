"""Business scenario catalog — department-facing features + developer tech map."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import settings
from security.department_features import FULL_ACCESS_DEPARTMENT, normalize_department

_CHANNEL_LABELS = {
    "wecom": "企业微信",
    "wechat": "微信",
    "miniprogram": "微信小程序",
    "channels": "视频号",
    "douyin": "抖音",
    "all": "全渠道",
}


def _catalog_path() -> Path:
    return Path(
        getattr(
            settings,
            "scenario_catalog_path",
            settings.data_raw_dir.parent / "config" / "scenario_catalog.json",
        )
    )


def load_scenario_catalog() -> dict[str, Any]:
    path = _catalog_path()
    if not path.is_file():
        return {"version": 1, "title": "", "departments": {}, "scenarios": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"version": 1, "title": "", "departments": {}, "scenarios": []}


def _dept_row(catalog: dict[str, Any], department: str) -> dict[str, Any] | None:
    depts = catalog.get("departments") or {}
    if not isinstance(depts, dict):
        return None
    row = depts.get(department)
    return dict(row) if isinstance(row, dict) else None


def _scenario_for_public(row: dict[str, Any], *, include_tech: bool) -> dict[str, Any]:
    ch = row.get("channel")
    out: dict[str, Any] = {
        "id": str(row.get("id") or ""),
        "label": str(row.get("label") or ""),
        "department": list(row.get("department") or []),
        "channel": ch,
        "channel_label": _CHANNEL_LABELS.get(str(ch or ""), str(ch or "—")),
        "user_goal": str(row.get("user_goal") or ""),
        "steps": list(row.get("steps") or []),
        "scene_preset": row.get("scene_preset"),
        "clarify_option_id": row.get("clarify_option_id"),
        "output_schema_id": row.get("output_schema_id"),
        "tools": list(row.get("tools") or []),
    }
    tech_setup = str(row.get("tech_setup") or "").strip()
    if tech_setup and include_tech:
        out["tech_setup"] = tech_setup
    if include_tech and isinstance(row.get("tech"), dict):
        out["tech"] = dict(row["tech"])
    return out


def list_scenarios_for_department(
    department: str | None,
    *,
    include_tech: bool = False,
) -> list[dict[str, Any]]:
    catalog = load_scenario_catalog()
    dept = normalize_department(department)
    show_all = not dept or dept == FULL_ACCESS_DEPARTMENT
    out: list[dict[str, Any]] = []
    for row in catalog.get("scenarios") or []:
        if not isinstance(row, dict):
            continue
        owners = [normalize_department(str(d)) for d in (row.get("department") or [])]
        if show_all or dept in owners:
            out.append(_scenario_for_public(row, include_tech=include_tech))
    return [s for s in out if s["id"]]


def public_scenario_catalog(
    department: str | None = None,
    *,
    include_tech: bool | None = None,
) -> dict[str, Any]:
    catalog = load_scenario_catalog()
    dept = normalize_department(department) or FULL_ACCESS_DEPARTMENT
    show_tech = include_tech if include_tech is not None else dept == FULL_ACCESS_DEPARTMENT
    dept_info = _dept_row(catalog, dept)
    if dept_info is None and dept != FULL_ACCESS_DEPARTMENT:
        dept_info = _dept_row(catalog, FULL_ACCESS_DEPARTMENT)

    return {
        "title": str(catalog.get("title") or ""),
        "department": dept,
        "department_info": dept_info,
        "chat_note": str((dept_info or {}).get("chat_note") or ""),
        "show_tech": show_tech,
        "scenarios": list_scenarios_for_department(dept, include_tech=show_tech),
        "departments": {
            k: {"label": v.get("label"), "summary": v.get("summary")}
            for k, v in (catalog.get("departments") or {}).items()
            if isinstance(v, dict)
        },
    }

"""Intent clarification for vague questions (content / channel scenarios)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import settings

VALID_CHANNELS = frozenset({"wecom", "wechat", "miniprogram", "channels", "douyin", "all"})


def _config_path() -> Path:
    return Path(getattr(settings, "clarify_options_path", settings.data_raw_dir.parent / "config" / "clarify_options.json"))


def load_clarify_config() -> dict[str, Any]:
    path = _config_path()
    if not path.is_file():
        return {"version": 1, "default_prompt": "", "options": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"version": 1, "default_prompt": "", "options": []}


def normalize_channel(raw: str | None) -> str:
    key = (raw or "all").strip().lower()
    if key in VALID_CHANNELS:
        return key
    aliases = {
        "企业微信": "wecom",
        "微信": "wechat",
        "小程序": "miniprogram",
        "视频号": "channels",
        "抖音": "douyin",
    }
    return aliases.get(key, "all")


def list_clarify_options(*, channel: str | None = None) -> list[dict[str, Any]]:
    cfg = load_clarify_config()
    ch = normalize_channel(channel)
    out: list[dict[str, Any]] = []
    for row in cfg.get("options") or []:
        if not isinstance(row, dict):
            continue
        channels = [normalize_channel(str(c)) for c in (row.get("channels") or ["all"])]
        if ch != "all" and "all" not in channels and ch not in channels:
            continue
        out.append(
            {
                "id": str(row.get("id") or ""),
                "label": str(row.get("label") or ""),
                "hint": str(row.get("hint") or ""),
                "output_schema_id": row.get("output_schema_id"),
            }
        )
    return [o for o in out if o["id"] and o["label"]]


def resolve_clarify_choice(choice_id: str | None) -> dict[str, Any] | None:
    cid = (choice_id or "").strip()
    if not cid:
        return None
    for row in list_clarify_options(channel="all"):
        if row["id"] == cid:
            return row
    return None


def apply_clarify_choice_to_message(message: str, choice: dict[str, Any]) -> str:
    base = (message or "").strip()
    hint = str(choice.get("hint") or "").strip()
    label = str(choice.get("label") or "").strip()
    if not hint:
        return base
    prefix = f"【任务：{label}】{hint}"
    if base:
        return f"{prefix}\n\n用户补充：{base}"
    return prefix


def should_offer_clarify(
    *,
    enabled: bool,
    skip_clarify: bool,
    clarify_choice_id: str | None,
    rule_confidence: float,
    intent: str,
    message: str,
    threshold: float = 0.55,
) -> bool:
    if not enabled or skip_clarify or clarify_choice_id:
        return False
    if intent in ("realtime", "graph", "chitchat"):
        return False
    from agent.chitchat import is_chitchat_message

    if is_chitchat_message(message):
        return False
    text = (message or "").strip()
    if len(text) >= 24 and rule_confidence >= threshold:
        return False
    if rule_confidence >= 0.72:
        return False
    return True


def build_clarify_event(*, channel: str | None = None) -> dict[str, Any]:
    cfg = load_clarify_config()
    options = list_clarify_options(channel=channel)
    return {
        "type": "clarify",
        "prompt": str(cfg.get("default_prompt") or "请选择更接近的方向："),
        "channel": normalize_channel(channel),
        "options": options,
    }

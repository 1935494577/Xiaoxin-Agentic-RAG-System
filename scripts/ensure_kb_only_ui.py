"""Ensure ui_config.json uses knowledge-base-only chat defaults (no hybrid/general fallback)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_PATH = ROOT / "enterprise_rag" / "data" / "ui_config.json"

KB_ONLY_KEYS: dict[str, bool] = {
    "hybrid_expert_mode": False,
    "general_fallback_enabled": False,
    "kb_post_stream_fallback": False,
}


def main() -> int:
    if not UI_PATH.is_file():
        print(f"WARN: {UI_PATH} not found — using server defaults.")
        return 0
    data = json.loads(UI_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        print("WARN: ui_config invalid — skip.")
        return 1
    changed: list[str] = []
    for key, val in KB_ONLY_KEYS.items():
        if data.get(key) is not val:
            data[key] = val
            changed.append(key)
    if changed:
        UI_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("Updated ui_config for KB-only chat:", ", ".join(changed))
    else:
        print("ui_config already KB-only (hybrid/general fallback off).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

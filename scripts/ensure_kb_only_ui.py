"""Ensure ui_config.json uses api_kb_only scene preset."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_PATH = ROOT / "enterprise_rag" / "data" / "ui_config.json"
SRC = ROOT / "enterprise_rag" / "src"
sys.path.insert(0, str(SRC))

from api.scene_presets import scene_preset_patch  # noqa: E402


def main() -> int:
    patch = scene_preset_patch("api_kb_only")
    if not patch:
        print("ERROR: api_kb_only preset missing")
        return 1
    if not UI_PATH.is_file():
        print(f"WARN: {UI_PATH} not found — writing preset defaults.")
        data: dict = {}
    else:
        raw = json.loads(UI_PATH.read_text(encoding="utf-8"))
        data = raw if isinstance(raw, dict) else {}
    changed: list[str] = []
    for key, val in patch.items():
        if data.get(key) != val:
            data[key] = val
            changed.append(key)
    if changed:
        UI_PATH.parent.mkdir(parents=True, exist_ok=True)
        UI_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("Updated ui_config for api_kb_only:", ", ".join(changed))
    else:
        print("ui_config already matches api_kb_only preset.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

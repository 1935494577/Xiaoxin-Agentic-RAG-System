#!/usr/bin/env python3
"""Print bootstrap account credentials (first-time seed only)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from config import settings


def main() -> int:
    path = Path(settings.auth_bootstrap_credentials_path)
    if not path.is_file():
        print("未找到初始账号文件。请先启动 API 一次以自动生成：")
        print(f"  {path}")
        return 1
    print(path.read_text(encoding="utf-8"))
    print(f"文件位置: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

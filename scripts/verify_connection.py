#!/usr/bin/env python3
"""运维脚本：检测前后端是否同步、API 是否可达（含 5 次 × 20 秒重试）。

用法（仓库根目录）:
  python scripts/verify_connection.py
  python scripts/verify_connection.py --api http://127.0.0.1:8010
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from connection_helpers import (  # noqa: E402
    DEFAULT_API,
    RETRY_COUNT,
    RETRY_INTERVAL_SEC,
    check_api_with_retry,
    verify_frontend_backend_sync,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify frontend/backend API connectivity")
    parser.add_argument("--api", default=DEFAULT_API, help="API base URL")
    parser.add_argument("--no-retry", action="store_true", help="Single health ping only")
    args = parser.parse_args()

    print(f"API: {args.api}")

    if args.no_retry:
        from connection_helpers import ping_health

        ok, msg = ping_health(args.api)
        if not ok:
            print(f"FAIL: {msg}")
            return 1
        print("OK: health")
        return 0

    def _log(attempt: int, total: int, ok: bool, msg: str) -> None:
        status = "OK" if ok else msg or "fail"
        print(f"  attempt {attempt}/{total}: {status}")

    print(f"Retry policy: {RETRY_COUNT} times, {RETRY_INTERVAL_SEC}s interval")
    ok, msg = check_api_with_retry(args.api, on_attempt=_log)
    if not ok:
        print(f"FAIL: {msg}")
        return 1

    issues = verify_frontend_backend_sync(args.api)
    if issues:
        for item in issues:
            print(f"SYNC ISSUE: {item}")
        return 1

    print("OK: health + public config in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

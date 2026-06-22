#!/usr/bin/env python3
"""Evaluate query_robustness.jsonl (no API / LLM required)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "enterprise_rag" / "src"
sys.path.insert(0, str(SRC))


def main() -> int:
    from evaluation.query_robustness_eval import run_query_robustness_eval

    report = run_query_robustness_eval()
    summary = {k: v for k, v in report.items() if k != "results"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    for row in report.get("results") or []:
        status = "PASS" if row.get("ok") else "FAIL"
        print(f"  [{status}] {row.get('raw')}")
        for f in row.get("failures") or []:
            print(f"         - {f}")
    failed = int(report.get("failed") or 0)
    if failed:
        print(f"\n{failed} case(s) failed.")
        return 1
    print("\nAll query robustness cases passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

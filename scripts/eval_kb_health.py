#!/usr/bin/env python3
"""Run KB health probe locally (no golden.jsonl required)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> int:
    parser = argparse.ArgumentParser(description="Knowledge base health probe")
    parser.add_argument("--limit", type=int, default=30, help="Max probe questions")
    parser.add_argument("--llm-judge", action="store_true", help="Run LLM relevance judge")
    parser.add_argument("--write", action="store_true", help="Write report JSON under data/eval/")
    args = parser.parse_args()

    from evaluation.kb_health_probe import run_kb_health_probe, write_kb_health_report

    llm_runtime = None
    if args.llm_judge:
        from api.llm_resolve import resolve_llm_runtime
        from api.schemas import ChatRequest

        llm_runtime = resolve_llm_runtime(ChatRequest(message=".", user_id="kb_health_cli"))

    report = run_kb_health_probe(
        limit=args.limit,
        use_llm_judge=args.llm_judge,
        llm_runtime=llm_runtime,
    )
    if report.get("ok") and args.write:
        path = write_kb_health_report(report)
        report = {**report, "written_to": str(path)}

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Offline evaluation for query_robustness.jsonl golden set."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import settings
from retrieval.query_understanding import understand_query


def robustness_path() -> Path:
    return Path(settings.golden_jsonl_path).parent / "query_robustness.jsonl"


def load_robustness_cases(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or robustness_path()
    if not p.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def evaluate_robustness_case(row: dict[str, Any]) -> dict[str, Any]:
    raw = str(row.get("raw") or "")
    qu = understand_query(raw)
    failures: list[str] = []
    if "expect_message" in row and qu.message != row["expect_message"]:
        failures.append(f"message: {qu.message!r} != {row['expect_message']!r}")
    if "expect_intent" in row and qu.intent != row["expect_intent"]:
        failures.append(f"intent: {qu.intent!r} != {row['expect_intent']!r}")
    if "expect_variant_contains" in row:
        needle = str(row["expect_variant_contains"])
        if not any(needle in v for v in qu.search_variants):
            failures.append(f"variants missing {needle!r}: {qu.search_variants}")
    if row.get("expect_canonical_contains"):
        needle = str(row["expect_canonical_contains"])
        if needle not in qu.retrieval_query:
            failures.append(f"canonical missing {needle!r}: {qu.retrieval_query!r}")
    return {
        "raw": raw,
        "ok": not failures,
        "failures": failures,
        "understanding": qu.to_dict(),
    }


def run_query_robustness_eval(path: Path | None = None) -> dict[str, Any]:
    cases = load_robustness_cases(path)
    results = [evaluate_robustness_case(row) for row in cases]
    passed = sum(1 for r in results if r["ok"])
    by_scenario: dict[str, dict[str, Any]] = {}
    for row, result in zip(cases, results):
        scenario = str(row.get("scenario") or "default")
        bucket = by_scenario.setdefault(scenario, {"total": 0, "passed": 0, "failed": 0})
        bucket["total"] += 1
        if result["ok"]:
            bucket["passed"] += 1
        else:
            bucket["failed"] += 1
    for bucket in by_scenario.values():
        total = bucket["total"]
        bucket["pass_rate"] = round(bucket["passed"] / total, 4) if total else 0.0
    return {
        "path": str(path or robustness_path()),
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": round(passed / len(results), 4) if results else 0.0,
        "by_scenario": by_scenario,
        "results": results,
    }

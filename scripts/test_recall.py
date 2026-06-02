#!/usr/bin/env python3
"""Test document recall via POST /retrieve (no LLM answer generation required)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_API = "http://127.0.0.1:8001"

QUERIES = [
    "1-3年级一阶段超脑阅读要求是多少字？",
    "4-6年级二阶段影像追忆需要看完多少字？",
    "高中扫描速记1分钟多少字？",
    "扫描速记逐字倒着背需要注意什么？",
    "二阶段极速运算任意几位数乘法？",
]

CASES = [
    {"label": "部门=技术（与入库一致）", "user_department": "技术", "allowed_sources": ["1-3.txt"]},
    {"label": "部门=general（向量检索会被过滤）", "user_department": "general", "allowed_sources": ["1-3.txt"]},
]


def _snippet(text: str, n: int = 160) -> str:
    return (text or "").replace("\n", " ")[:n] + ("…" if len(text or "") > n else "")


def run(api_base: str = DEFAULT_API) -> int:
    try:
        health = httpx.get(f"{api_base.rstrip('/')}/health", timeout=5)
        if health.status_code != 200:
            print(f"API 不可用: {health.status_code}")
            return 1
    except httpx.HTTPError as e:
        print(f"无法连接 API ({api_base}): {e}")
        print("请先运行: .\\scripts\\run-api.ps1")
        return 1

    report: list[dict] = []
    for case in CASES:
        print(f"\n{'=' * 64}\n{case['label']}\n{'=' * 64}")
        for q in QUERIES:
            payload = {
                "query": q,
                "user_department": case["user_department"],
                "top_k": 3,
                "allowed_sources": case["allowed_sources"],
            }
            r = httpx.post(f"{api_base.rstrip('/')}/retrieve", json=payload, timeout=120)
            entry = {"case": case["label"], "question": q, "status": r.status_code}
            if r.status_code != 200:
                entry["error"] = r.text[:500]
                print(f"\nQ: {q}\n  FAIL {r.status_code}: {r.text[:200]}")
            else:
                data = r.json()
                entry["rewritten_query"] = data.get("rewritten_query")
                entry["hits"] = [
                    {
                        "source": h.get("source"),
                        "rerank_score": h.get("rerank_score"),
                        "snippet": _snippet(h.get("text", "")),
                    }
                    for h in data.get("hits") or []
                ]
                print(f"\nQ: {q}")
                print(f"  改写: {data.get('rewritten_query', '')[:80]}")
                hits = data.get("hits") or []
                if not hits:
                    print("  （无命中）")
                for i, h in enumerate(hits, 1):
                    print(
                        f"  [{i}] rerank={h.get('rerank_score')} "
                        f"src={h.get('source')} | {_snippet(h.get('text', ''), 120)}"
                    )
            report.append(entry)

    out = ROOT / "scripts" / "recall_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n完整报告: {out}")
    return 0


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_API
    raise SystemExit(run(base))

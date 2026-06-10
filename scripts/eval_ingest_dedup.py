#!/usr/bin/env python3
"""Compare retrieval quality/latency with L3 dedup on vs off.

Usage:
  python scripts/eval_ingest_dedup.py              # direct hybrid_search (no API)
  python scripts/eval_ingest_dedup.py --api         # via POST /retrieve
  python scripts/eval_ingest_dedup.py --langsmith   # wrap runs in LangSmith trace

Requires indexed corpus (e.g. 1-3.txt). Set LANGCHAIN_TRACING_V2=true for LangSmith.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "enterprise_rag" / "src"))

DEFAULT_API = "http://127.0.0.1:8010"

QUERIES = [
    "1-3年级一阶段超脑阅读要求是多少字？",
    "4-6年级二阶段影像追忆需要看完多少字？",
    "高中扫描速记1分钟多少字？",
    "扫描速记逐字倒着背需要注意什么？",
    "二阶段极速运算任意几位数乘法？",
]

USER_DEPARTMENT = "技术"


def _snippet(text: str, n: int = 120) -> str:
    t = (text or "").replace("\n", " ")
    return t[:n] + ("…" if len(t) > n else "")


def _metrics(hits: list[dict[str, Any]]) -> dict[str, Any]:
    sources = [str(h.get("source") or "") for h in hits]
    texts = [str(h.get("text") or "") for h in hits]
    unique_sources = len(set(sources))
    dup_text_pairs = 0
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            if texts[i] and texts[i] == texts[j]:
                dup_text_pairs += 1
    return {
        "hit_count": len(hits),
        "unique_sources": unique_sources,
        "duplicate_text_pairs": dup_text_pairs,
        "sources": sources,
    }


def _run_direct(dedup: bool) -> list[dict[str, Any]]:
    from retrieval.hybrid_searcher import hybrid_search

    rows: list[dict[str, Any]] = []
    for q in QUERIES:
        t0 = time.perf_counter()
        _, hits = hybrid_search(
            q,
            USER_DEPARTMENT,
            top_k=5,
            skip_query_rewrite=True,
            retrieval_dedup=dedup,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        m = _metrics(hits)
        m.update(
            {
                "question": q,
                "dedup_enabled": dedup,
                "latency_ms": round(elapsed_ms, 1),
                "hits": [
                    {
                        "source": h.get("source"),
                        "score": h.get("rerank_score", h.get("hybrid_score")),
                        "snippet": _snippet(str(h.get("text") or "")),
                    }
                    for h in hits
                ],
            }
        )
        rows.append(m)
    return rows


def _run_api(api_base: str, dedup: bool) -> list[dict[str, Any]]:
    import httpx

    rows: list[dict[str, Any]] = []
    for q in QUERIES:
        payload = {
            "query": q,
            "user_department": USER_DEPARTMENT,
            "top_k": 5,
            "retrieval_dedup": dedup,
        }
        t0 = time.perf_counter()
        r = httpx.post(f"{api_base.rstrip('/')}/retrieve", json=payload, timeout=120)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        entry: dict[str, Any] = {
            "question": q,
            "dedup_enabled": dedup,
            "latency_ms": round(elapsed_ms, 1),
            "status": r.status_code,
        }
        if r.status_code == 200:
            data = r.json()
            hits = data.get("hits") or []
            entry.update(_metrics(hits))
            entry["hits"] = [
                {
                    "source": h.get("source"),
                    "score": h.get("rerank_score"),
                    "snippet": _snippet(str(h.get("text") or "")),
                }
                for h in hits
            ]
        else:
            entry["error"] = r.text[:300]
        rows.append(entry)
    return rows


def _summarize(label: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [r["latency_ms"] for r in rows if "latency_ms" in r]
    dup_pairs = sum(int(r.get("duplicate_text_pairs") or 0) for r in rows)
    return {
        "label": label,
        "queries": len(rows),
        "avg_latency_ms": round(mean(latencies), 1) if latencies else 0,
        "total_duplicate_text_pairs": dup_pairs,
        "avg_unique_sources": round(
            mean([r.get("unique_sources", 0) for r in rows]) if rows else 0, 2
        ),
    }


def _maybe_trace(fn, use_langsmith: bool):
    if not use_langsmith:
        return fn()
    try:
        from langsmith import traceable
    except ImportError:
        print("langsmith 未安装，跳过 trace 包装")
        return fn()
    wrapped = traceable(name="eval_ingest_dedup")(fn)
    return wrapped()


def main() -> int:
    parser = argparse.ArgumentParser(description="L3 retrieval dedup A/B eval")
    parser.add_argument("--api", action="store_true", help="Use POST /retrieve instead of direct import")
    parser.add_argument("--api-base", default=DEFAULT_API)
    parser.add_argument("--langsmith", action="store_true", help="Wrap eval in LangSmith traceable")
    parser.add_argument(
        "--out",
        default=str(ROOT / "scripts" / "ingest_dedup_eval.json"),
        help="JSON report path",
    )
    args = parser.parse_args()

    def run_eval():
        if args.api:
            import httpx
            try:
                httpx.get(f"{args.api_base.rstrip('/')}/health", timeout=5).raise_for_status()
            except Exception as e:
                print(f"API unavailable: {e}")
                return [], []
            # Warmup (embedding/reranker) so A/B latency is comparable
            _run_api(args.api_base, dedup=True)
        if args.api:
            off = _run_api(args.api_base, dedup=False)
            on = _run_api(args.api_base, dedup=True)
        else:
            _run_direct(dedup=True)  # warmup
            off = _run_direct(dedup=False)
            on = _run_direct(dedup=True)
        return off, on

    off, on = _maybe_trace(run_eval, args.langsmith)

    report = {
        "summary": {
            "dedup_off": _summarize("dedup_off", off),
            "dedup_on": _summarize("dedup_on", on),
        },
        "details": {"dedup_off": off, "dedup_on": on},
    }
    out_path = Path(args.out)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    s_off = report["summary"]["dedup_off"]
    s_on = report["summary"]["dedup_on"]
    print("=== Ingest/Retrieval Dedup Eval ===")
    print(f"dedup OFF: avg_latency={s_off['avg_latency_ms']}ms  dup_pairs={s_off['total_duplicate_text_pairs']}")
    print(f"dedup ON : avg_latency={s_on['avg_latency_ms']}ms  dup_pairs={s_on['total_duplicate_text_pairs']}")
    print(f"Report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

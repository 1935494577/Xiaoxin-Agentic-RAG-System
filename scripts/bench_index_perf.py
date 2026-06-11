"""Benchmark index hot paths; writes timing to debug-4d3f1c.log via instrumented modules."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "enterprise_rag" / "src"))

from config import settings  # noqa: E402
from debug_session_log import write as session_log  # noqa: E402
from indexing import numpy_vector_index as nvi  # noqa: E402
from indexing.bm25_indexer import BM25Index  # noqa: E402


def main() -> None:
    tmp = ROOT / "enterprise_rag" / "data" / "_bench_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    store = tmp / "bench_vectors.json"
    bm25_path = tmp / "bench_bm25.json"

    n, dim = 5000, 384
    rng = np.random.default_rng(42)
    rows = []
    for i in range(n):
        v = rng.standard_normal(dim).astype(np.float32)
        v = v / (np.linalg.norm(v) + 1e-12)
        rows.append(
            {
                "id": f"id{i}",
                "vector": v.tolist(),
                "text": f"t{i}",
                "parent_id": f"p{i}",
                "department": "general",
                "source": "bench",
                "tags": "",
            }
        )
    store.write_text(json.dumps(rows), encoding="utf-8")
    settings.numpy_vector_store_path = store

    nvi.reload_store()
    q = rng.standard_normal(dim).astype(np.float32)
    q = q / np.linalg.norm(q)

    t0 = time.perf_counter()
    for _ in range(10):
        nvi.vector_search(q.tolist(), 20)
    vec_ms = (time.perf_counter() - t0) / 10 * 1000

    idx = BM25Index(bm25_path)
    docs = [
        {
            "parent_id": f"p{i}",
            "content": f"企业制度 文档编号 {i}",
            "department": "general",
            "source": "bench",
            "permission_label": "public",
            "tags": [],
        }
        for i in range(n)
    ]
    idx.index_parent_documents(docs)

    t0 = time.perf_counter()
    for _ in range(50):
        idx.search("企业制度", 20)
    bm25_ms = (time.perf_counter() - t0) / 50 * 1000

    session_log(
        "VERIFY",
        "scripts/bench_index_perf.py",
        "bench_summary",
        {"vector_search_avg_ms": round(vec_ms, 2), "bm25_search_avg_ms": round(bm25_ms, 2), "n": n},
        run_id="post-fix",
    )
    print(f"vector_search avg: {vec_ms:.2f} ms (n={n}, dim={dim}, x10)")
    print(f"bm25_search avg: {bm25_ms:.2f} ms (n={n}, x50)")
    print(f"Log: {ROOT / 'debug-4d3f1c.log'}")


if __name__ == "__main__":
    main()

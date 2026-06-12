"""One-shot performance audit; writes NDJSON to debug-178feb.log."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "debug-178feb.log"
sys.path.insert(0, str(ROOT / "enterprise_rag" / "src"))

from config import settings  # noqa: E402
from indexing import numpy_vector_index as nvi  # noqa: E402
from indexing.bm25_indexer import BM25Index  # noqa: E402
from retrieval.search_cache import get_search_cache  # noqa: E402


def _log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    payload = {
        "sessionId": "178feb",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
        "runId": "perf-audit",
    }
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def bench_numpy(n: int = 5000, dim: int | None = None, iters: int = 10) -> float:
    try:
        from api.vector_store_registry import get_active_store_public

        active_dim = int(get_active_store_public().get("embedding_dim") or 512)
    except Exception:
        active_dim = 512
    if dim is None:
        dim = active_dim
    tmp = ROOT / "enterprise_rag" / "data" / "_audit_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    store = tmp / "audit_vectors.json"
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
                "department": "技术部",
                "permission_label": "internal",
                "source": "audit",
                "tags": "",
            }
        )
    store.write_text(json.dumps(rows), encoding="utf-8")
    settings.numpy_vector_store_path = store
    nvi.reload_store()
    q = rng.standard_normal(dim).astype(np.float32)
    q = q / np.linalg.norm(q)
    t0 = time.perf_counter()
    for _ in range(iters):
        nvi.vector_search(q.tolist(), 20, user_department="技术部")
    return (time.perf_counter() - t0) / iters * 1000


def bench_bm25(n: int = 5000, iters: int = 50) -> float:
    tmp = ROOT / "enterprise_rag" / "data" / "_audit_tmp"
    bm25_path = tmp / "audit_bm25.json"
    idx = BM25Index(bm25_path)
    docs = [
        {
            "parent_id": f"p{i}",
            "content": f"企业制度 文档编号 {i}",
            "department": "general",
            "source": "audit",
            "permission_label": "public",
            "tags": [],
        }
        for i in range(n)
    ]
    idx.index_parent_documents(docs)
    t0 = time.perf_counter()
    for _ in range(iters):
        idx.search("企业制度", 20)
    return (time.perf_counter() - t0) / iters * 1000


def main() -> None:
    # H1: index hot paths within acceptable bounds at 5k docs
    vec_ms = bench_numpy()
    bm25_ms = bench_bm25()
    _log("H1", "audit_perf:bench", "index_latency_5k", {"vector_search_ms": round(vec_ms, 2), "bm25_ms": round(bm25_ms, 2)})

    # H2: production config flags affecting latency/memory
    _log(
        "H2",
        "audit_perf:config",
        "runtime_flags",
        {
            "query_rewrite_enabled": settings.query_rewrite_enabled,
            "stream_skip_rerank": settings.stream_skip_rerank,
            "stream_retrieve_top_k": settings.stream_retrieve_top_k,
            "warmup_models_on_startup": settings.warmup_models_on_startup,
            "warmup_reranker_on_startup": settings.warmup_reranker_on_startup,
            "redis_url_set": bool((settings.redis_url or "").strip()),
            "redis_search_cache_enabled": settings.redis_search_cache_enabled,
            "embedding_batch_size": settings.embedding_batch_size,
            "use_presidio": settings.use_presidio,
        },
    )

    # H3: search cache backend type (reset singleton for fresh settings)
    import retrieval.search_cache as sc

    sc._cached_client = None
    sc._cached_impl = None
    cache = get_search_cache()
    _log(
        "H3",
        "audit_perf:cache",
        "search_cache_impl",
        {"impl": type(cache).__name__, "ttl": settings.redis_search_cache_ttl_seconds},
    )

    # H4: real index size if present
    vec_path = Path(settings.numpy_vector_store_path)
    bm25_path = Path(settings.bm25_index_path)
    _log(
        "H4",
        "audit_perf:data",
        "index_footprint",
        {
            "numpy_exists": vec_path.is_file(),
            "numpy_mb": round(vec_path.stat().st_size / 1024 / 1024, 2) if vec_path.is_file() else 0,
            "bm25_exists": bm25_path.is_file(),
            "bm25_mb": round(bm25_path.stat().st_size / 1024 / 1024, 2) if bm25_path.is_file() else 0,
        },
    )

    print(f"Audit complete -> {LOG}")
    print(f"  vector_search ~{vec_ms:.1f} ms (5k docs)")
    print(f"  bm25_search ~{bm25_ms:.1f} ms (5k docs)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Closed loop (no Docker): Milvus Lite + local BM25 (plan1).

Usage (repo root):
  python scripts/run_closed_loop.py

Requires: pip install -r requirements.txt (milvus-lite, rank-bm25, ...).
First ingest may download embedding weights.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "enterprise_rag" / "src"
sys.path.insert(0, str(SRC))


def _check_infra() -> None:
    from indexing.milvus_indexer import get_vector_backend, init_vector_db

    init_vector_db()
    if get_vector_backend() == "numpy":
        return
    try:
        from pymilvus import utility
    except ImportError as e:
        raise RuntimeError("Missing pymilvus. Run: make install") from e

    _ = utility.get_server_version()


def main() -> int:
    print("[1/5] Starting Milvus Lite + checking server...")
    try:
        _check_infra()
    except Exception as e:
        print(f"FAIL infra: {e}")
        print("Hint: pip install -r requirements.txt; on Windows ensure VC++ runtime if Milvus Lite fails.")
        return 2

    print("[2/5] In-process API (TestClient)...")
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as client:
        h = client.get("/health")
        if h.status_code != 200:
            print(f"FAIL /health: {h.status_code} {h.text}")
            return 3
        print("      /health OK")

        print("[3/5] Ingest sample.txt ...")
        r = client.post("/ingest/path", params={"relative_path": "sample.txt"})
        if r.status_code != 200:
            print(f"FAIL ingest: {r.status_code} {r.text}")
            return 4
        body = r.json()
        print(f"      ingest OK chunks={body.get('chunks_indexed')}")

        print("[4/5] POST /chat ...")
        chat = client.post(
            "/chat",
            json={
                "message": "What orchestrates rewrite, retrieve, rerank, and generate?",
                "user_id": "e2e-user",
                "user_department": "general",
            },
        )
        if chat.status_code != 200:
            print(f"FAIL chat: {chat.status_code} {chat.text}")
            return 5
        cj = chat.json()
        print("      chat OK answer_len=", len(cj.get("answer") or ""))

        print("[5/5] POST /feedback ...")
        fb = client.post(
            "/feedback",
            json={"user_id": "e2e-user", "message_id": "e2e-1", "rating": 1, "correction": None},
        )
        if fb.status_code != 200:
            print(f"FAIL feedback: {fb.status_code} {fb.text}")
            return 6
        print("      feedback OK")

    summary = {
        "status": "PASS",
        "ingest": body,
        "chat_keys": list(cj.keys()),
        "feedback": fb.json(),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

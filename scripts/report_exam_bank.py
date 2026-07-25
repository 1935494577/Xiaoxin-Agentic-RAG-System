from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "enterprise_rag" / "src"))

from exam_bank import store
from exam_bank.store import _connect, _lock

store.init_exam_bank_db()
cols = store.list_collections()
print("collections", len(cols))
with _lock:
    conn = _connect()
    try:
        sps = conn.execute("SELECT COUNT(*) AS c FROM source_papers").fetchone()["c"]
        qs = conn.execute("SELECT COUNT(*) AS c FROM questions").fetchone()["c"]
        by_col = conn.execute(
            """
            SELECT c.region, c.subject, c.grade, COUNT(*) AS c
            FROM questions q
            JOIN collections c ON q.collection_id = c.id
            GROUP BY c.region, c.subject, c.grade
            ORDER BY c DESC
            """
        ).fetchall()
        by_qt = conn.execute(
            "SELECT qtype, COUNT(*) AS c FROM questions GROUP BY qtype ORDER BY c DESC"
        ).fetchall()
    finally:
        conn.close()
print("source_papers", sps)
print("questions", qs)
print("by_collection:")
for r in by_col:
    print(f"  {r['region']}·{r['subject']}·{r['grade']}: {r['c']}")
print("by_qtype:")
for r in by_qt:
    print(f"  {r['qtype']}: {r['c']}")
for c in cols:
    inv = store.collection_inventory(c["id"])
    print(
        c.get("name"),
        "total",
        inv["total"],
        "years",
        (inv.get("years") or [])[:10],
        "exam_types",
        [x["chapter"] for x in (inv.get("by_chapter") or [])[:6]],
        "qtypes",
        inv.get("by_qtype"),
    )

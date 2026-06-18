"""SQLite knowledge graph store (entities + edges)."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any

from config import settings

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def _db_path() -> Path:
    return Path(settings.graph_db_path)


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is not None:
        return _conn
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            entity_type TEXT DEFAULT '',
            source TEXT DEFAULT '',
            department TEXT DEFAULT '',
            parent_id TEXT DEFAULT '',
            title TEXT DEFAULT '',
            bio TEXT DEFAULT '',
            UNIQUE(name, source, parent_id)
        );
        CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
        CREATE INDEX IF NOT EXISTS idx_entities_source ON entities(source);

        CREATE TABLE IF NOT EXISTS edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            src_name TEXT NOT NULL,
            relation TEXT NOT NULL,
            dst_name TEXT NOT NULL,
            source TEXT DEFAULT '',
            department TEXT DEFAULT '',
            parent_id TEXT DEFAULT '',
            confidence REAL DEFAULT 1.0
        );
        CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src_name);
        CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst_name);
        CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source);
        """
    )
    _migrate_entities_columns(conn)
    conn.commit()
    _conn = conn
    return conn


def _migrate_entities_columns(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(entities)").fetchall()}
    if "title" not in cols:
        conn.execute("ALTER TABLE entities ADD COLUMN title TEXT DEFAULT ''")
    if "bio" not in cols:
        conn.execute("ALTER TABLE entities ADD COLUMN bio TEXT DEFAULT ''")


def delete_edges_by_source(source: str) -> None:
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM edges WHERE source = ?", (source,))
        conn.execute("DELETE FROM entities WHERE source = ?", (source,))
        conn.commit()


def upsert_entity_profile(
    *,
    name: str,
    source: str,
    department: str,
    entity_type: str = "person",
    title: str = "",
    bio: str = "",
    parent_id: str = "",
) -> None:
    name = name.strip()
    if not name:
        return
    with _lock:
        conn = _get_conn()
        conn.execute(
            """
            INSERT INTO entities (name, entity_type, source, department, parent_id, title, bio)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name, source, parent_id) DO UPDATE SET
                entity_type=excluded.entity_type,
                department=excluded.department,
                title=excluded.title,
                bio=excluded.bio
            """,
            (name, entity_type, source, department, parent_id, title, bio),
        )
        conn.commit()


def get_entity_profiles(names: list[str], *, department: str | None = None) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for name in names:
        n = name.strip()
        if not n or n in out:
            continue
        with _lock:
            conn = _get_conn()
            params: list[Any] = [n, f"%{n}%"]
            dept_clause = ""
            if department:
                dept_clause = " AND (department = ? OR department = '' OR department IS NULL)"
                params.append(department)
            row = conn.execute(
                f"""
                SELECT name, entity_type, department, title, bio
                FROM entities
                WHERE (name = ? OR name LIKE ?){dept_clause}
                ORDER BY LENGTH(name) ASC
                LIMIT 1
                """,
                params,
            ).fetchone()
        if row:
            out[n] = dict(row)
        else:
            out[n] = {"name": n, "entity_type": "entity", "department": "", "title": "", "bio": ""}
    return out


def import_relationship_bundle(
    *,
    source: str,
    department: str,
    people: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
) -> tuple[int, int]:
    """Import structured people + edges. Returns (people_count, edge_count)."""
    delete_edges_by_source(source)
    pc = 0
    for p in people:
        name = str(p.get("name") or "").strip()
        if not name:
            continue
        upsert_entity_profile(
            name=name,
            source=source,
            department=str(p.get("department") or department),
            entity_type=str(p.get("entity_type") or "person"),
            title=str(p.get("title") or ""),
            bio=str(p.get("bio") or ""),
            parent_id="profile",
        )
        pc += 1
    ec = 0
    for r in relationships:
        upsert_triple(
            src_name=str(r.get("from_name") or r.get("from") or ""),
            relation=str(r.get("relation") or "相关"),
            dst_name=str(r.get("to_name") or r.get("to") or ""),
            source=source,
            department=department,
            parent_id="rel",
            confidence=float(r.get("confidence") or 1.0),
            src_type="person",
            dst_type="person",
        )
        ec += 1
    return pc, ec


def upsert_triple(
    *,
    src_name: str,
    relation: str,
    dst_name: str,
    source: str,
    department: str,
    parent_id: str,
    confidence: float = 1.0,
    src_type: str = "",
    dst_type: str = "",
) -> None:
    src_name = src_name.strip()
    dst_name = dst_name.strip()
    relation = relation.strip()
    if not src_name or not dst_name or not relation:
        return
    if confidence < 0.35:
        return
    with _lock:
        conn = _get_conn()
        for name, etype in ((src_name, src_type), (dst_name, dst_type)):
            conn.execute(
                """
                INSERT INTO entities (name, entity_type, source, department, parent_id)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(name, source, parent_id) DO UPDATE SET entity_type=excluded.entity_type
                """,
                (name, etype, source, department, parent_id),
            )
        conn.execute(
            """
            INSERT INTO edges (src_name, relation, dst_name, source, department, parent_id, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (src_name, relation, dst_name, source, department, parent_id, confidence),
        )
        conn.commit()


def expand_from_seeds(
    seed_names: list[str],
    *,
    department: str | None = None,
    max_hops: int = 2,
    limit: int = 30,
) -> list[dict[str, Any]]:
    """BFS expand entity names; return edge rows with parent_id for text lookup."""
    rows = _expand_from_seeds_impl(seed_names, department=department, max_hops=max_hops, limit=limit)
    if rows or not department:
        return rows
    return _expand_from_seeds_impl(seed_names, department=None, max_hops=max_hops, limit=limit)


def _expand_from_seeds_impl(
    seed_names: list[str],
    *,
    department: str | None,
    max_hops: int,
    limit: int,
) -> list[dict[str, Any]]:
    seeds = [s.strip() for s in seed_names if s and s.strip()]
    if not seeds:
        return []
    seen: set[str] = set()
    frontier = list(seeds)
    results: list[dict[str, Any]] = []
    hops = 0
    with _lock:
        conn = _get_conn()
        while frontier and hops < max_hops and len(results) < limit:
            next_frontier: list[str] = []
            for name in frontier:
                if name in seen:
                    continue
                seen.add(name)
                params: list[Any] = [name, name]
                dept_clause = ""
                if department:
                    dept_clause = " AND (department = ? OR department = '' OR department IS NULL)"
                    params.append(department)
                rows = conn.execute(
                    f"""
                    SELECT src_name, relation, dst_name, source, department, parent_id, confidence
                    FROM edges
                    WHERE (src_name = ? OR dst_name = ?){dept_clause}
                    ORDER BY confidence DESC
                    LIMIT ?
                    """,
                    (*params, limit),
                ).fetchall()
                for row in rows:
                    rec = dict(row)
                    results.append(rec)
                    other = rec["dst_name"] if rec["src_name"] == name else rec["src_name"]
                    if other not in seen:
                        next_frontier.append(str(other))
            frontier = next_frontier
            hops += 1
    return results[:limit]


def list_entities_matching(substring: str, *, limit: int = 10) -> list[str]:
    q = f"%{substring.strip()}%"
    if not substring.strip():
        return []
    with _lock:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT DISTINCT name FROM entities WHERE name LIKE ? LIMIT ?",
            (q, limit),
        ).fetchall()
    return [str(r["name"]) for r in rows]


def list_sources_matching(substring: str, *, limit: int = 5) -> list[str]:
    q = f"%{substring.strip()}%"
    if not substring.strip():
        return []
    with _lock:
        conn = _get_conn()
        rows = conn.execute(
            """
            SELECT source, COUNT(*) AS c FROM edges
            WHERE source LIKE ?
            GROUP BY source
            ORDER BY c DESC
            LIMIT ?
            """,
            (q, limit),
        ).fetchall()
        out = [str(r["source"]) for r in rows]
        if out:
            return out
        erows = conn.execute(
            "SELECT DISTINCT source FROM entities WHERE source LIKE ? LIMIT ?",
            (q, limit),
        ).fetchall()
    return [str(r["source"]) for r in erows]


def pick_center_for_source(source: str, *, department: str | None = None) -> str:
    """Pick CEO / highest-degree node as graph center for a document source."""
    with _lock:
        conn = _get_conn()
        params: list[Any] = [source]
        dept_clause = ""
        if department:
            dept_clause = " AND (department = ? OR department = '' OR department IS NULL)"
            params.append(department)
        row = conn.execute(
            f"""
            SELECT name, title FROM entities
            WHERE source = ?{dept_clause}
            ORDER BY CASE
                WHEN title LIKE '%CEO%' OR title LIKE '%总经理%' THEN 0
                ELSE 1
            END, LENGTH(title) ASC
            LIMIT 1
            """,
            params,
        ).fetchone()
        if row:
            return str(row["name"])
        row2 = conn.execute(
            f"""
            SELECT src_name AS name, COUNT(*) AS c FROM edges
            WHERE source = ?{dept_clause}
            GROUP BY src_name
            ORDER BY c DESC
            LIMIT 1
            """,
            params,
        ).fetchone()
    return str(row2["name"]) if row2 else ""

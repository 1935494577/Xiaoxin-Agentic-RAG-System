"""Exam bank SQLite store — isolated from RAG Chat / Milvus."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from config import settings

from exam_bank.types import (
    DEFAULT_TENANT,
    DIFFICULTY_MAX,
    DIFFICULTY_MIN,
    QUALITY_STATUSES,
)
from exam_bank.subject_catalog import DIFFICULTY_BANDS, normalize_qtype


_lock = RLock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_path() -> Path:
    return Path(settings.exam_bank_db_path)


def init_exam_bank_db() -> None:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        conn = sqlite3.connect(path)
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS collections (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL DEFAULT 'internal',
                    name TEXT NOT NULL,
                    subject TEXT NOT NULL DEFAULT '',
                    grade TEXT NOT NULL DEFAULT '',
                    region TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    visibility TEXT NOT NULL DEFAULT 'private',
                    owner_user_id TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_exam_col_tenant
                    ON collections(tenant_id, created_at DESC);

                CREATE TABLE IF NOT EXISTS questions (
                    id TEXT PRIMARY KEY,
                    collection_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL DEFAULT 'internal',
                    qtype TEXT NOT NULL,
                    difficulty INTEGER NOT NULL DEFAULT 3,
                    stem TEXT NOT NULL,
                    options_json TEXT NOT NULL DEFAULT '[]',
                    answer TEXT NOT NULL DEFAULT '',
                    analysis TEXT NOT NULL DEFAULT '',
                    knowledge_tags TEXT NOT NULL DEFAULT '[]',
                    region TEXT NOT NULL DEFAULT '',
                    year TEXT NOT NULL DEFAULT '',
                    subject TEXT NOT NULL DEFAULT '',
                    grade TEXT NOT NULL DEFAULT '',
                    quality_status TEXT NOT NULL DEFAULT 'draft',
                    content_hash TEXT NOT NULL DEFAULT '',
                    visibility TEXT NOT NULL DEFAULT 'private',
                    owner_user_id TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(collection_id) REFERENCES collections(id)
                );
                CREATE INDEX IF NOT EXISTS idx_exam_q_col
                    ON questions(collection_id, quality_status, qtype, difficulty);

                CREATE TABLE IF NOT EXISTS paper_jobs (
                    id TEXT PRIMARY KEY,
                    collection_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL DEFAULT 'internal',
                    title TEXT NOT NULL DEFAULT '',
                    spec_json TEXT NOT NULL DEFAULT '{}',
                    question_ids_json TEXT NOT NULL DEFAULT '[]',
                    markdown TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                """
            )
            _migrate_exam_columns(conn)
            conn.commit()
        finally:
            conn.close()


def _migrate_exam_columns(conn: sqlite3.Connection) -> None:
    def _cols(table: str) -> set[str]:
        return {str(r[1]) for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}

    col_cols = _cols("collections")
    if "visibility" not in col_cols:
        conn.execute(
            "ALTER TABLE collections ADD COLUMN visibility TEXT NOT NULL DEFAULT 'private'"
        )
    if "owner_user_id" not in col_cols:
        conn.execute(
            "ALTER TABLE collections ADD COLUMN owner_user_id TEXT NOT NULL DEFAULT ''"
        )
    q_cols = _cols("questions")
    if "visibility" not in q_cols:
        conn.execute(
            "ALTER TABLE questions ADD COLUMN visibility TEXT NOT NULL DEFAULT 'private'"
        )
    if "owner_user_id" not in q_cols:
        conn.execute(
            "ALTER TABLE questions ADD COLUMN owner_user_id TEXT NOT NULL DEFAULT ''"
        )


def _connect() -> sqlite3.Connection:
    init_exam_bank_db()
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _row_collection(row: sqlite3.Row) -> dict[str, Any]:
    keys = set(row.keys())
    return {
        "id": row["id"],
        "tenant_id": row["tenant_id"],
        "name": row["name"],
        "subject": row["subject"],
        "grade": row["grade"],
        "region": row["region"],
        "description": row["description"],
        "visibility": row["visibility"] if "visibility" in keys else "private",
        "owner_user_id": row["owner_user_id"] if "owner_user_id" in keys else "",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _parse_tags(raw: str) -> list[str]:
    try:
        data = json.loads(raw or "[]")
        if isinstance(data, list):
            return [str(x) for x in data]
    except Exception:
        pass
    return []


def _row_question(row: sqlite3.Row) -> dict[str, Any]:
    try:
        options = json.loads(row["options_json"] or "[]")
    except Exception:
        options = []
    if not isinstance(options, list):
        options = []
    keys = set(row.keys()) if hasattr(row, "keys") else set()
    return {
        "id": row["id"],
        "collection_id": row["collection_id"],
        "tenant_id": row["tenant_id"],
        "qtype": row["qtype"],
        "difficulty": int(row["difficulty"]),
        "stem": row["stem"],
        "options": [str(x) for x in options],
        "answer": row["answer"],
        "analysis": row["analysis"],
        "knowledge_tags": _parse_tags(row["knowledge_tags"]),
        "region": row["region"],
        "year": row["year"],
        "subject": row["subject"],
        "grade": row["grade"],
        "quality_status": row["quality_status"],
        "content_hash": row["content_hash"],
        "visibility": row["visibility"] if "visibility" in keys else "private",
        "owner_user_id": row["owner_user_id"] if "owner_user_id" in keys else "",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_collection(
    *,
    name: str,
    subject: str = "",
    grade: str = "",
    region: str = "",
    description: str = "",
    tenant_id: str = DEFAULT_TENANT,
    visibility: str = "private",
    owner_user_id: str = "",
) -> dict[str, Any]:
    from platform_acl import normalize_asset_visibility

    now = _utc_now()
    cid = str(uuid.uuid4())
    tid = (tenant_id or DEFAULT_TENANT).strip() or DEFAULT_TENANT
    vis = normalize_asset_visibility(visibility)
    owner = (owner_user_id or "").strip()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO collections
                (id, tenant_id, name, subject, grade, region, description,
                 visibility, owner_user_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cid,
                    tid,
                    (name or "").strip() or "未命名题库",
                    (subject or "").strip(),
                    (grade or "").strip(),
                    (region or "").strip(),
                    (description or "").strip(),
                    vis,
                    owner,
                    now,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM collections WHERE id = ?", (cid,)).fetchone()
        finally:
            conn.close()
    return _row_collection(row)


def list_collections(
    *,
    tenant_id: str = DEFAULT_TENANT,
    reader_user_id: str | None = None,
    apply_acl: bool = True,
) -> list[dict[str, Any]]:
    from platform_acl import filter_readable_assets

    tid = (tenant_id or DEFAULT_TENANT).strip() or DEFAULT_TENANT
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT * FROM collections WHERE tenant_id = ? ORDER BY created_at DESC",
                (tid,),
            ).fetchall()
        finally:
            conn.close()
    items = [_row_collection(r) for r in rows]
    if not apply_acl:
        return items
    # Legacy rows with empty owner: treat as readable within tenant list for compatibility
    # when reader not provided — return tenant_shared + platform + owned
    reader = (reader_user_id or "").strip()
    if not reader:
        return [
            x
            for x in items
            if (x.get("visibility") or "private") in ("tenant_shared", "platform")
            or not (x.get("owner_user_id") or "").strip()
        ]
    return filter_readable_assets(
        items,
        reader_tenant_id=tid,
        reader_user_id=reader,
    )


def get_collection(collection_id: str) -> dict[str, Any] | None:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM collections WHERE id = ?",
                (collection_id,),
            ).fetchone()
        finally:
            conn.close()
    return _row_collection(row) if row else None


def _content_hash(stem: str, answer: str, qtype: str) -> str:
    raw = f"{qtype}|{stem.strip()}|{answer.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def create_question(
    *,
    collection_id: str,
    qtype: str,
    difficulty: int = 3,
    stem: str,
    options: list[str] | None = None,
    answer: str = "",
    analysis: str = "",
    knowledge_tags: list[str] | None = None,
    region: str = "",
    year: str = "",
    subject: str = "",
    grade: str = "",
    quality_status: str = "draft",
    tenant_id: str = DEFAULT_TENANT,
) -> dict[str, Any]:
    col = get_collection(collection_id)
    if not col:
        raise ValueError("collection_not_found")
    qt = normalize_qtype(qtype or "other")
    diff = max(DIFFICULTY_MIN, min(DIFFICULTY_MAX, int(difficulty)))
    status = (quality_status or "draft").strip().lower()
    if status not in QUALITY_STATUSES:
        status = "draft"
    now = _utc_now()
    qid = str(uuid.uuid4())
    stem_s = (stem or "").strip()
    ans = (answer or "").strip()
    opts = [str(x) for x in (options or [])]
    tags = [str(x).strip() for x in (knowledge_tags or []) if str(x).strip()]
    tid = (tenant_id or col["tenant_id"] or DEFAULT_TENANT).strip() or DEFAULT_TENANT
    vis = str(col.get("visibility") or "private")
    owner = str(col.get("owner_user_id") or "")
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO questions (
                    id, collection_id, tenant_id, qtype, difficulty, stem, options_json,
                    answer, analysis, knowledge_tags, region, year, subject, grade,
                    quality_status, content_hash, visibility, owner_user_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    qid,
                    collection_id,
                    tid,
                    qt,
                    diff,
                    stem_s,
                    json.dumps(opts, ensure_ascii=False),
                    ans,
                    (analysis or "").strip(),
                    json.dumps(tags, ensure_ascii=False),
                    (region or col.get("region") or "").strip(),
                    (year or "").strip(),
                    (subject or col.get("subject") or "").strip(),
                    (grade or col.get("grade") or "").strip(),
                    status,
                    _content_hash(stem_s, ans, qt),
                    vis,
                    owner,
                    now,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM questions WHERE id = ?", (qid,)).fetchone()
        finally:
            conn.close()
    return _row_question(row)


def list_questions(
    *,
    collection_id: str,
    qtype: str | None = None,
    difficulty: int | None = None,
    difficulty_min: int | None = None,
    difficulty_max: int | None = None,
    tag: str | None = None,
    status: str | None = "published",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    clauses = ["collection_id = ?"]
    params: list[Any] = [collection_id]
    if status:
        clauses.append("quality_status = ?")
        params.append(status)
    if qtype:
        clauses.append("qtype = ?")
        params.append(qtype)
    if difficulty is not None:
        clauses.append("difficulty = ?")
        params.append(int(difficulty))
    if difficulty_min is not None:
        clauses.append("difficulty >= ?")
        params.append(int(difficulty_min))
    if difficulty_max is not None:
        clauses.append("difficulty <= ?")
        params.append(int(difficulty_max))
    where = " AND ".join(clauses)
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                f"SELECT * FROM questions WHERE {where} ORDER BY created_at DESC",
                params,
            ).fetchall()
        finally:
            conn.close()
    items = [_row_question(r) for r in rows]
    if tag:
        t = tag.strip()
        items = [q for q in items if t in (q.get("knowledge_tags") or [])]
    total = len(items)
    lim = max(1, min(int(limit), 200))
    off = max(0, int(offset))
    return items[off : off + lim], total


def get_question(question_id: str) -> dict[str, Any] | None:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM questions WHERE id = ?",
                (question_id,),
            ).fetchone()
        finally:
            conn.close()
    return _row_question(row) if row else None


def save_paper(
    *,
    collection_id: str,
    title: str,
    spec: dict[str, Any],
    question_ids: list[str],
    markdown: str,
    tenant_id: str = DEFAULT_TENANT,
) -> dict[str, Any]:
    pid = str(uuid.uuid4())
    now = _utc_now()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO paper_jobs
                (id, collection_id, tenant_id, title, spec_json, question_ids_json, markdown, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pid,
                    collection_id,
                    (tenant_id or DEFAULT_TENANT).strip() or DEFAULT_TENANT,
                    (title or "").strip() or "未命名试卷",
                    json.dumps(spec or {}, ensure_ascii=False),
                    json.dumps(list(question_ids), ensure_ascii=False),
                    markdown or "",
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()
    return get_paper(pid) or {"id": pid}


def get_paper(paper_id: str) -> dict[str, Any] | None:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM paper_jobs WHERE id = ?",
                (paper_id,),
            ).fetchone()
        finally:
            conn.close()
    if not row:
        return None
    try:
        spec = json.loads(row["spec_json"] or "{}")
    except Exception:
        spec = {}
    try:
        qids = json.loads(row["question_ids_json"] or "[]")
    except Exception:
        qids = []
    return {
        "id": row["id"],
        "collection_id": row["collection_id"],
        "tenant_id": row["tenant_id"],
        "title": row["title"],
        "spec": spec if isinstance(spec, dict) else {},
        "question_ids": [str(x) for x in qids] if isinstance(qids, list) else [],
        "markdown": row["markdown"],
        "created_at": row["created_at"],
    }


def collection_inventory(collection_id: str) -> dict[str, Any]:
    items, _ = list_questions(
        collection_id=collection_id,
        status="published",
        limit=500,
        offset=0,
    )
    by_qtype: dict[str, int] = {}
    by_band: dict[str, int] = {"easy": 0, "mid": 0, "hard": 0}
    custom: list[str] = []
    for q in items:
        qt = normalize_qtype(str(q.get("qtype") or "other"))
        by_qtype[qt] = by_qtype.get(qt, 0) + 1
        if qt.startswith("custom:") and qt not in custom:
            custom.append(qt)
        d = int(q.get("difficulty") or 3)
        for band, (lo, hi) in DIFFICULTY_BANDS.items():
            if lo <= d <= hi:
                by_band[band] = by_band.get(band, 0) + 1
                break
    return {
        "collection_id": collection_id,
        "total": len(items),
        "by_qtype": by_qtype,
        "by_difficulty_band": by_band,
        "custom_qtypes": custom,
    }

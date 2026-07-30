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
    if "source_paper_id" not in q_cols:
        conn.execute(
            "ALTER TABLE questions ADD COLUMN source_paper_id TEXT NOT NULL DEFAULT ''"
        )
    if "question_no" not in q_cols:
        conn.execute(
            "ALTER TABLE questions ADD COLUMN question_no TEXT NOT NULL DEFAULT ''"
        )
    if "chapter" not in q_cols:
        conn.execute(
            "ALTER TABLE questions ADD COLUMN chapter TEXT NOT NULL DEFAULT ''"
        )
    if "difficulty_coef" not in q_cols:
        conn.execute(
            "ALTER TABLE questions ADD COLUMN difficulty_coef REAL NOT NULL DEFAULT 0"
        )
    if "cognitive_level" not in q_cols:
        conn.execute(
            "ALTER TABLE questions ADD COLUMN cognitive_level TEXT NOT NULL DEFAULT ''"
        )
    if "discrimination" not in q_cols:
        conn.execute(
            "ALTER TABLE questions ADD COLUMN discrimination REAL NOT NULL DEFAULT 0"
        )
    if "textbook_version" not in q_cols:
        conn.execute(
            "ALTER TABLE questions ADD COLUMN textbook_version TEXT NOT NULL DEFAULT ''"
        )
    if "media_ingest_id" not in q_cols:
        conn.execute(
            "ALTER TABLE questions ADD COLUMN media_ingest_id TEXT NOT NULL DEFAULT ''"
        )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS source_papers (
            id TEXT PRIMARY KEY,
            collection_id TEXT NOT NULL,
            tenant_id TEXT NOT NULL DEFAULT 'internal',
            title TEXT NOT NULL DEFAULT '',
            source_filename TEXT NOT NULL DEFAULT '',
            raw_text TEXT NOT NULL DEFAULT '',
            answer_text TEXT NOT NULL DEFAULT '',
            question_ids_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(collection_id) REFERENCES collections(id)
        );
        """
    )
    sp_cols = _cols("source_papers")
    if "media_ingest_id" not in sp_cols:
        try:
            conn.execute(
                "ALTER TABLE source_papers ADD COLUMN media_ingest_id TEXT NOT NULL DEFAULT ''"
            )
        except sqlite3.OperationalError:
            pass
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_exam_sp_col
            ON source_papers(collection_id, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS exam_attempts (
            id TEXT PRIMARY KEY,
            source_paper_id TEXT NOT NULL,
            user_id TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'in_progress',
            paper_snapshot_json TEXT NOT NULL DEFAULT '{}',
            answers_json TEXT NOT NULL DEFAULT '{}',
            results_json TEXT NOT NULL DEFAULT '[]',
            score INTEGER NOT NULL DEFAULT 0,
            max_score INTEGER NOT NULL DEFAULT 0,
            correct_count INTEGER NOT NULL DEFAULT 0,
            graded_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            submitted_at TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(source_paper_id) REFERENCES source_papers(id)
        );
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_exam_attempt_paper
            ON exam_attempts(source_paper_id, created_at DESC)
        """
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
        "source_paper_id": row["source_paper_id"] if "source_paper_id" in keys else "",
        "question_no": row["question_no"] if "question_no" in keys else "",
        "chapter": row["chapter"] if "chapter" in keys else "",
        "difficulty_coef": float(row["difficulty_coef"]) if "difficulty_coef" in keys else 0.0,
        "cognitive_level": row["cognitive_level"] if "cognitive_level" in keys else "",
        "discrimination": float(row["discrimination"]) if "discrimination" in keys else 0.0,
        "textbook_version": row["textbook_version"] if "textbook_version" in keys else "",
        "media_ingest_id": row["media_ingest_id"] if "media_ingest_id" in keys else "",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def default_collection_name(*, region: str, subject: str, grade: str) -> str:
    parts = [p for p in [(region or "").strip(), (subject or "").strip(), (grade or "").strip()] if p]
    return "·".join(parts) if parts else "未命名题库"


def find_collection_scope_conflict(
    *,
    region: str,
    subject: str,
    grade: str,
    tenant_id: str = DEFAULT_TENANT,
    visibility: str = "private",
    owner_user_id: str = "",
) -> dict[str, Any] | None:
    """Same tenant + region + subject + grade: private conflicts per owner; shared conflicts globally."""
    from platform_acl import normalize_asset_visibility

    region_n = (region or "").strip()
    subject_n = (subject or "").strip()
    grade_n = (grade or "").strip()
    if not region_n:
        return None
    tid = (tenant_id or DEFAULT_TENANT).strip() or DEFAULT_TENANT
    vis = normalize_asset_visibility(visibility)
    owner = (owner_user_id or "").strip()

    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM collections
                WHERE tenant_id = ? AND region = ? AND subject = ? AND grade = ?
                """,
                (tid, region_n, subject_n, grade_n),
            ).fetchall()
        finally:
            conn.close()

    for row in rows:
        existing = _row_collection(row)
        e_vis = normalize_asset_visibility(existing.get("visibility") or "private")
        e_owner = (existing.get("owner_user_id") or "").strip()
        if vis == "private" and e_vis == "private":
            if owner and e_owner and owner == e_owner:
                return existing
            if not owner and not e_owner:
                return existing
            continue
        return existing
    return None


def find_collection_name_conflict(
    *,
    name: str,
    subject: str,
    grade: str,
    tenant_id: str = DEFAULT_TENANT,
    visibility: str = "private",
    owner_user_id: str = "",
    region: str = "",
) -> dict[str, Any] | None:
    """Backward-compatible alias: prefer region×subject×grade scope when region given."""
    if (region or "").strip():
        return find_collection_scope_conflict(
            region=region,
            subject=subject,
            grade=grade,
            tenant_id=tenant_id,
            visibility=visibility,
            owner_user_id=owner_user_id,
        )
    # legacy name-based (tests / callers without region)
    from platform_acl import normalize_asset_visibility

    name_n = (name or "").strip() or "未命名题库"
    subject_n = (subject or "").strip()
    grade_n = (grade or "").strip()
    tid = (tenant_id or DEFAULT_TENANT).strip() or DEFAULT_TENANT
    vis = normalize_asset_visibility(visibility)
    owner = (owner_user_id or "").strip()

    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM collections
                WHERE tenant_id = ? AND subject = ? AND grade = ? AND name = ?
                """,
                (tid, subject_n, grade_n, name_n),
            ).fetchall()
        finally:
            conn.close()

    for row in rows:
        existing = _row_collection(row)
        e_vis = normalize_asset_visibility(existing.get("visibility") or "private")
        e_owner = (existing.get("owner_user_id") or "").strip()
        if vis == "private" and e_vis == "private":
            if owner and e_owner and owner == e_owner:
                return existing
            if not owner and not e_owner:
                return existing
            continue
        return existing
    return None


def create_collection(
    *,
    name: str = "",
    subject: str = "",
    grade: str = "",
    region: str = "",
    description: str = "",
    tenant_id: str = DEFAULT_TENANT,
    visibility: str = "private",
    owner_user_id: str = "",
) -> dict[str, Any]:
    from platform_acl import normalize_asset_visibility

    region_n = (region or "").strip()
    if not region_n:
        raise ValueError("region_required")

    now = _utc_now()
    cid = str(uuid.uuid4())
    tid = (tenant_id or DEFAULT_TENANT).strip() or DEFAULT_TENANT
    vis = normalize_asset_visibility(visibility)
    owner = (owner_user_id or "").strip()
    subject_n = (subject or "").strip()
    grade_n = (grade or "").strip()
    # 统一命名：地区·学科·年级（忽略自定义名，保证库身份可读）
    name_n = default_collection_name(region=region_n, subject=subject_n, grade=grade_n)

    conflict = find_collection_scope_conflict(
        region=region_n,
        subject=subject_n,
        grade=grade_n,
        tenant_id=tid,
        visibility=vis,
        owner_user_id=owner,
    )
    if conflict:
        raise ValueError("collection_scope_conflict")

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
                    name_n,
                    subject_n,
                    grade_n,
                    region_n,
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


def difficulty_to_coef(difficulty: int) -> float:
    """Map 1–5 band to 0–1 ease coefficient (higher = easier), for sliders / 预估均分."""
    mapping = {1: 0.92, 2: 0.85, 3: 0.65, 4: 0.45, 5: 0.28}
    return float(mapping.get(int(difficulty), 0.65))


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
    source_paper_id: str = "",
    question_no: str = "",
    chapter: str = "",
    difficulty_coef: float | None = None,
    cognitive_level: str = "",
    discrimination: float | None = None,
    textbook_version: str = "",
    media_ingest_id: str = "",
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
    spid = (source_paper_id or "").strip()
    qno = (question_no or "").strip()
    chap = (chapter or "").strip()
    coef = float(difficulty_coef) if difficulty_coef is not None else difficulty_to_coef(diff)
    coef = max(0.0, min(1.0, coef))
    cog = (cognitive_level or "").strip().lower()
    disc = float(discrimination) if discrimination is not None else 0.0
    disc = max(0.0, min(1.0, disc))
    tb = (textbook_version or "").strip()
    mid = (media_ingest_id or "").strip()
    # 地区跟随题库：各地区各科独立库
    region_n = str(col.get("region") or "").strip() or (region or "").strip()
    subject_n = (subject or col.get("subject") or "").strip()
    grade_n = (grade or col.get("grade") or "").strip()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO questions (
                    id, collection_id, tenant_id, qtype, difficulty, stem, options_json,
                    answer, analysis, knowledge_tags, region, year, subject, grade,
                    quality_status, content_hash, visibility, owner_user_id,
                    source_paper_id, question_no, chapter,
                    difficulty_coef, cognitive_level, discrimination, textbook_version,
                    media_ingest_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    region_n,
                    (year or "").strip(),
                    subject_n,
                    grade_n,
                    status,
                    _content_hash(stem_s, ans, qt),
                    vis,
                    owner,
                    spid,
                    qno,
                    chap,
                    coef,
                    cog,
                    disc,
                    tb,
                    mid,
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
    q: str | None = None,
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
        items = [qrow for qrow in items if t in (qrow.get("knowledge_tags") or [])]
    if q:
        needle = q.strip().lower()
        if needle:
            filtered = []
            for qrow in items:
                stem = str(qrow.get("stem") or "").lower()
                tags = " ".join(str(t) for t in (qrow.get("knowledge_tags") or [])).lower()
                ans = str(qrow.get("answer") or "").lower()
                if needle in stem or needle in tags or needle in ans:
                    filtered.append(qrow)
            items = filtered
    total = len(items)
    lim = max(1, min(int(limit), 10000))
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


def collection_inventory(
    collection_id: str,
    *,
    tags_any: list[str] | None = None,
    chapters_any: list[str] | None = None,
    regions_any: list[str] | None = None,
    years_any: list[str] | None = None,
) -> dict[str, Any]:
    items, _ = list_questions(
        collection_id=collection_id,
        status="published",
        limit=8000,
        offset=0,
    )
    by_tag_counts: dict[str, int] = {}
    by_chapter_counts: dict[str, int] = {}
    by_year_counts: dict[str, int] = {}
    by_qtype_year: dict[str, dict[str, int]] = {}
    regions_set: set[str] = set()
    years_set: set[str] = set()
    custom: list[str] = []
    for q in items:
        qt = normalize_qtype(str(q.get("qtype") or "other"))
        if qt.startswith("custom:") and qt not in custom:
            custom.append(qt)
        for tag in q.get("knowledge_tags") or []:
            t = str(tag).strip()
            if t:
                by_tag_counts[t] = by_tag_counts.get(t, 0) + 1
        chapter = str(q.get("chapter") or "").strip()
        if chapter:
            by_chapter_counts[chapter] = by_chapter_counts.get(chapter, 0) + 1
        region = str(q.get("region") or "").strip()
        if region:
            regions_set.add(region)
        year = str(q.get("year") or "").strip()
        if year:
            years_set.add(year)
            by_year_counts[year] = by_year_counts.get(year, 0) + 1

    tags_f = [t for t in (tags_any or []) if str(t).strip()]
    chapters_f = [c for c in (chapters_any or []) if str(c).strip()]
    regions_f = [r for r in (regions_any or []) if str(r).strip()]
    years_f = [y for y in (years_any or []) if str(y).strip()]
    filtered = items
    if tags_f or chapters_f or regions_f or years_f:
        filtered = []
        for q in items:
            if tags_f:
                qtags = set(q.get("knowledge_tags") or [])
                if not qtags.intersection(tags_f):
                    continue
            if chapters_f and str(q.get("chapter") or "").strip() not in chapters_f:
                continue
            if regions_f and str(q.get("region") or "").strip() not in regions_f:
                continue
            if years_f and str(q.get("year") or "").strip() not in years_f:
                continue
            filtered.append(q)

    by_qtype: dict[str, int] = {}
    by_band: dict[str, int] = {"easy": 0, "mid": 0, "hard": 0}
    for q in filtered:
        qt = normalize_qtype(str(q.get("qtype") or "other"))
        by_qtype[qt] = by_qtype.get(qt, 0) + 1
        year = str(q.get("year") or "").strip() or "未知"
        by_qtype_year.setdefault(qt, {})
        by_qtype_year[qt][year] = by_qtype_year[qt].get(year, 0) + 1
        d = int(q.get("difficulty") or 3)
        for band, (lo, hi) in DIFFICULTY_BANDS.items():
            if lo <= d <= hi:
                by_band[band] = by_band.get(band, 0) + 1
                break

    by_tag = [
        {"tag": k, "count": v}
        for k, v in sorted(by_tag_counts.items(), key=lambda x: (-x[1], x[0]))
    ]
    by_chapter = [
        {"chapter": k, "count": v}
        for k, v in sorted(by_chapter_counts.items(), key=lambda x: (-x[1], x[0]))
    ]
    by_year = [
        {"year": k, "count": v}
        for k, v in sorted(by_year_counts.items(), key=lambda x: x[0], reverse=True)
    ]
    return {
        "collection_id": collection_id,
        "total": len(filtered),
        "total_all": len(items),
        "filter_applied": bool(tags_f or chapters_f or regions_f or years_f),
        "by_qtype": by_qtype,
        "by_qtype_year": by_qtype_year,
        "by_difficulty_band": by_band,
        "by_tag": by_tag,
        "by_chapter": by_chapter,
        "by_year": by_year,
        "regions": sorted(regions_set),
        "years": sorted(years_set, reverse=True),
        "custom_qtypes": custom,
    }


def update_question(question_id: str, **fields: Any) -> dict[str, Any]:
    existing = get_question(question_id)
    if not existing:
        raise ValueError("question_not_found")
    allowed = {
        "qtype",
        "difficulty",
        "stem",
        "options",
        "answer",
        "analysis",
        "knowledge_tags",
        "region",
        "year",
        "subject",
        "grade",
        "quality_status",
        "source_paper_id",
        "question_no",
        "chapter",
        "difficulty_coef",
        "cognitive_level",
        "discrimination",
        "textbook_version",
        "media_ingest_id",
    }
    merged = dict(existing)
    for k, v in fields.items():
        if k in allowed and v is not None:
            merged[k] = v
    qt = normalize_qtype(str(merged.get("qtype") or "other"))
    diff = max(DIFFICULTY_MIN, min(DIFFICULTY_MAX, int(merged.get("difficulty") or 3)))
    status = str(merged.get("quality_status") or "draft").strip().lower()
    if status not in QUALITY_STATUSES:
        status = "draft"
    stem_s = str(merged.get("stem") or "").strip()
    ans = str(merged.get("answer") or "").strip()
    opts = merged.get("options") or []
    if not isinstance(opts, list):
        opts = []
    opts = [str(x) for x in opts]
    tags = merged.get("knowledge_tags") or []
    if not isinstance(tags, list):
        tags = []
    tags = [str(x).strip() for x in tags if str(x).strip()]
    coef = float(merged.get("difficulty_coef") or 0) or difficulty_to_coef(diff)
    coef = max(0.0, min(1.0, coef))
    cog = str(merged.get("cognitive_level") or "").strip().lower()
    disc = max(0.0, min(1.0, float(merged.get("discrimination") or 0)))
    tb = str(merged.get("textbook_version") or "").strip()
    mid = str(merged.get("media_ingest_id") or "").strip()
    now = _utc_now()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                UPDATE questions SET
                    qtype = ?, difficulty = ?, stem = ?, options_json = ?,
                    answer = ?, analysis = ?, knowledge_tags = ?,
                    region = ?, year = ?, subject = ?, grade = ?,
                    quality_status = ?, content_hash = ?,
                    source_paper_id = ?, question_no = ?, chapter = ?,
                    difficulty_coef = ?, cognitive_level = ?, discrimination = ?,
                    textbook_version = ?, media_ingest_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    qt,
                    diff,
                    stem_s,
                    json.dumps(opts, ensure_ascii=False),
                    ans,
                    str(merged.get("analysis") or "").strip(),
                    json.dumps(tags, ensure_ascii=False),
                    str(merged.get("region") or "").strip(),
                    str(merged.get("year") or "").strip(),
                    str(merged.get("subject") or "").strip(),
                    str(merged.get("grade") or "").strip(),
                    status,
                    _content_hash(stem_s, ans, qt),
                    str(merged.get("source_paper_id") or "").strip(),
                    str(merged.get("question_no") or "").strip(),
                    str(merged.get("chapter") or "").strip(),
                    coef,
                    cog,
                    disc,
                    tb,
                    mid,
                    now,
                    question_id,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM questions WHERE id = ?", (question_id,)
            ).fetchone()
        finally:
            conn.close()
    return _row_question(row)


def delete_question(question_id: str) -> bool:
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def delete_collection(collection_id: str) -> bool:
    with _lock:
        conn = _connect()
        try:
            conn.execute("DELETE FROM questions WHERE collection_id = ?", (collection_id,))
            conn.execute(
                "DELETE FROM source_papers WHERE collection_id = ?", (collection_id,)
            )
            cur = conn.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def purge_exam_bank() -> dict[str, Any]:
    """Wipe all exam-bank tables (collections, questions, papers, jobs)."""
    with _lock:
        conn = _connect()
        try:
            tables = [
                "paper_jobs",
                "source_papers",
                "questions",
                "collections",
            ]
            counts: dict[str, int] = {}
            for t in tables:
                try:
                    n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                    counts[t] = int(n)
                    conn.execute(f"DELETE FROM {t}")
                except sqlite3.OperationalError:
                    counts[t] = 0
            conn.commit()
        finally:
            conn.close()
    return {"ok": True, "deleted": counts}


def _row_source_paper(row: sqlite3.Row) -> dict[str, Any]:
    try:
        qids = json.loads(row["question_ids_json"] or "[]")
    except Exception:
        qids = []
    keys = set(row.keys()) if hasattr(row, "keys") else set()
    return {
        "id": row["id"],
        "collection_id": row["collection_id"],
        "tenant_id": row["tenant_id"],
        "title": row["title"],
        "source_filename": row["source_filename"],
        "raw_text": row["raw_text"],
        "answer_text": row["answer_text"],
        "question_ids": [str(x) for x in qids] if isinstance(qids, list) else [],
        "media_ingest_id": row["media_ingest_id"] if "media_ingest_id" in keys else "",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_source_paper(
    *,
    collection_id: str,
    title: str = "",
    source_filename: str = "",
    raw_text: str = "",
    answer_text: str = "",
    question_ids: list[str] | None = None,
    tenant_id: str = DEFAULT_TENANT,
    media_ingest_id: str = "",
) -> dict[str, Any]:
    col = get_collection(collection_id)
    if not col:
        raise ValueError("collection_not_found")
    now = _utc_now()
    pid = str(uuid.uuid4())
    tid = (tenant_id or col["tenant_id"] or DEFAULT_TENANT).strip() or DEFAULT_TENANT
    qids = [str(x) for x in (question_ids or [])]
    mid = (media_ingest_id or "").strip()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO source_papers
                (id, collection_id, tenant_id, title, source_filename, raw_text,
                 answer_text, question_ids_json, media_ingest_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pid,
                    collection_id,
                    tid,
                    (title or "").strip() or "未命名试卷",
                    (source_filename or "").strip(),
                    raw_text or "",
                    answer_text or "",
                    json.dumps(qids, ensure_ascii=False),
                    mid,
                    now,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM source_papers WHERE id = ?", (pid,)).fetchone()
        finally:
            conn.close()
    return _row_source_paper(row)


def get_source_paper(source_paper_id: str) -> dict[str, Any] | None:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM source_papers WHERE id = ?",
                (source_paper_id,),
            ).fetchone()
        finally:
            conn.close()
    return _row_source_paper(row) if row else None


def list_source_papers(*, collection_id: str) -> list[dict[str, Any]]:
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM source_papers
                WHERE collection_id = ?
                ORDER BY created_at DESC
                """,
                (collection_id,),
            ).fetchall()
        finally:
            conn.close()
    return [_row_source_paper(r) for r in rows]


def search_source_papers(
    q: str,
    *,
    collection_id: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Fuzzy match title / filename / collection region·subject·grade·name."""
    tokens = [t for t in (q or "").strip().split() if t]
    if not tokens:
        return []
    lim = max(1, min(50, int(limit or 10)))
    col = (collection_id or "").strip()
    with _lock:
        conn = _connect()
        try:
            clauses = ["1=1"]
            params: list[Any] = []
            if col:
                clauses.append("sp.collection_id = ?")
                params.append(col)
            for tok in tokens:
                clauses.append(
                    "("
                    "sp.title LIKE ? OR sp.source_filename LIKE ? OR "
                    "IFNULL(c.name,'') LIKE ? OR IFNULL(c.region,'') LIKE ? OR "
                    "IFNULL(c.subject,'') LIKE ? OR IFNULL(c.grade,'') LIKE ?"
                    ")"
                )
                like = f"%{tok}%"
                params.extend([like, like, like, like, like, like])
            params.append(lim)
            sql = f"""
                SELECT sp.*, c.name AS collection_name, c.region AS col_region,
                       c.subject AS col_subject, c.grade AS col_grade
                FROM source_papers sp
                LEFT JOIN collections c ON c.id = sp.collection_id
                WHERE {' AND '.join(clauses)}
                ORDER BY sp.created_at DESC
                LIMIT ?
            """
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
    out: list[dict[str, Any]] = []
    for r in rows:
        item = _row_source_paper(r)
        keys = set(r.keys()) if hasattr(r, "keys") else set()
        item["collection_name"] = r["collection_name"] if "collection_name" in keys else ""
        item["region"] = r["col_region"] if "col_region" in keys else ""
        item["subject"] = r["col_subject"] if "col_subject" in keys else ""
        item["grade"] = r["col_grade"] if "col_grade" in keys else ""
        out.append(item)
    return out


def list_recent_source_papers(*, limit: int = 8) -> list[dict[str, Any]]:
    lim = max(1, min(50, int(limit or 8)))
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                """
                SELECT sp.*, c.name AS collection_name, c.region AS col_region,
                       c.subject AS col_subject, c.grade AS col_grade
                FROM source_papers sp
                LEFT JOIN collections c ON c.id = sp.collection_id
                ORDER BY sp.created_at DESC
                LIMIT ?
                """,
                (lim,),
            ).fetchall()
        finally:
            conn.close()
    out: list[dict[str, Any]] = []
    for r in rows:
        item = _row_source_paper(r)
        keys = set(r.keys()) if hasattr(r, "keys") else set()
        item["collection_name"] = r["collection_name"] if "collection_name" in keys else ""
        item["region"] = r["col_region"] if "col_region" in keys else ""
        item["subject"] = r["col_subject"] if "col_subject" in keys else ""
        item["grade"] = r["col_grade"] if "col_grade" in keys else ""
        out.append(item)
    return out


def update_source_paper(
    source_paper_id: str,
    *,
    answer_text: str | None = None,
    question_ids: list[str] | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    existing = get_source_paper(source_paper_id)
    if not existing:
        raise ValueError("source_paper_not_found")
    now = _utc_now()
    ans = existing["answer_text"] if answer_text is None else answer_text
    qids = existing["question_ids"] if question_ids is None else [str(x) for x in question_ids]
    ttl = existing["title"] if title is None else (title or "").strip() or existing["title"]
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                UPDATE source_papers SET
                    answer_text = ?, question_ids_json = ?, title = ?, updated_at = ?
                WHERE id = ?
                """,
                (ans or "", json.dumps(qids, ensure_ascii=False), ttl, now, source_paper_id),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM source_papers WHERE id = ?", (source_paper_id,)
            ).fetchone()
        finally:
            conn.close()
    return _row_source_paper(row)


def _row_exam_attempt(row: sqlite3.Row) -> dict[str, Any]:
    def _load(key: str, default: Any) -> Any:
        empty = "{}" if isinstance(default, dict) else "[]"
        try:
            return json.loads(row[key] or empty)
        except Exception:
            return default

    return {
        "id": row["id"],
        "source_paper_id": row["source_paper_id"],
        "user_id": row["user_id"] or "",
        "status": row["status"],
        "paper_snapshot": _load("paper_snapshot_json", {}),
        "answers": _load("answers_json", {}),
        "results": _load("results_json", []),
        "score": int(row["score"] or 0),
        "max_score": int(row["max_score"] or 0),
        "correct_count": int(row["correct_count"] or 0),
        "graded_count": int(row["graded_count"] or 0),
        "created_at": row["created_at"],
        "submitted_at": row["submitted_at"] or "",
    }


def create_exam_attempt(
    *,
    source_paper_id: str,
    user_id: str = "",
    paper_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not get_source_paper(source_paper_id):
        raise ValueError("source_paper_not_found")
    now = _utc_now()
    aid = str(uuid.uuid4())
    snap = paper_snapshot or {}
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO exam_attempts
                (id, source_paper_id, user_id, status, paper_snapshot_json,
                 answers_json, results_json, score, max_score, correct_count,
                 graded_count, created_at, submitted_at)
                VALUES (?, ?, ?, 'in_progress', ?, '{}', '[]', 0, 0, 0, 0, ?, '')
                """,
                (
                    aid,
                    source_paper_id,
                    (user_id or "").strip(),
                    json.dumps(snap, ensure_ascii=False),
                    now,
                ),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM exam_attempts WHERE id = ?", (aid,)).fetchone()
        finally:
            conn.close()
    return _row_exam_attempt(row)


def get_exam_attempt(attempt_id: str) -> dict[str, Any] | None:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM exam_attempts WHERE id = ?", (attempt_id,)
            ).fetchone()
        finally:
            conn.close()
    return _row_exam_attempt(row) if row else None


def finish_exam_attempt(
    attempt_id: str,
    *,
    answers: dict[str, str],
    results: list[dict[str, Any]],
    score: int,
    max_score: int,
    correct_count: int,
    graded_count: int,
) -> dict[str, Any]:
    existing = get_exam_attempt(attempt_id)
    if not existing:
        raise ValueError("attempt_not_found")
    now = _utc_now()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                UPDATE exam_attempts SET
                    status = 'submitted',
                    answers_json = ?,
                    results_json = ?,
                    score = ?,
                    max_score = ?,
                    correct_count = ?,
                    graded_count = ?,
                    submitted_at = ?
                WHERE id = ?
                """,
                (
                    json.dumps(answers or {}, ensure_ascii=False),
                    json.dumps(results or [], ensure_ascii=False),
                    int(score),
                    int(max_score),
                    int(correct_count),
                    int(graded_count),
                    now,
                    attempt_id,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM exam_attempts WHERE id = ?", (attempt_id,)
            ).fetchone()
        finally:
            conn.close()
    return _row_exam_attempt(row)

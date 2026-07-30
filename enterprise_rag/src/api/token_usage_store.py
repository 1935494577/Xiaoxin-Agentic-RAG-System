"""Independent Jnao LLM token usage (SQLite). Not DeerFlow RunStore."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from config import settings

_lock = Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_path() -> Path:
    return Path(settings.token_usage_db_path)


def token_usage_enabled() -> bool:
    """Honor settings.token_usage_enabled and config.yaml token_usage.enabled."""
    if not bool(getattr(settings, "token_usage_enabled", True)):
        return False
    try:
        from pathlib import Path

        import yaml

        cfg_path = Path(__file__).resolve().parents[3] / "config.yaml"
        if cfg_path.is_file():
            raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            tu = raw.get("token_usage") if isinstance(raw, dict) else None
            if isinstance(tu, dict) and "enabled" in tu:
                return bool(tu.get("enabled"))
    except Exception:
        pass
    return True


def metering_meta_from_state(state: dict[str, Any] | None) -> dict[str, str]:
    st = state or {}
    return {
        "session_id": str(st.get("session_id") or "")[:128],
        "user_id": str(st.get("user_id") or "")[:128],
        "channel": str(st.get("channel") or "")[:64],
        "question_preview": str(st.get("question") or "").strip()[:200],
    }


def init_token_usage_db() -> None:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        conn = sqlite3.connect(path)
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS llm_calls (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    session_id TEXT NOT NULL DEFAULT '',
                    user_id TEXT NOT NULL DEFAULT '',
                    channel TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL DEFAULT '',
                    caller TEXT NOT NULL DEFAULT '',
                    prompt_tokens INTEGER NOT NULL DEFAULT 0,
                    completion_tokens INTEGER NOT NULL DEFAULT 0,
                    total_tokens INTEGER NOT NULL DEFAULT 0,
                    question_preview TEXT NOT NULL DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_llm_calls_created
                    ON llm_calls(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_llm_calls_session
                    ON llm_calls(session_id, created_at DESC);
                """
            )
            conn.commit()
        finally:
            conn.close()


def _as_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def record_llm_call(
    *,
    model: str = "",
    caller: str = "",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int | None = None,
    session_id: str = "",
    user_id: str = "",
    channel: str = "",
    question_preview: str = "",
) -> str | None:
    """Persist one LLM completion. Returns call id, or None when metering disabled."""
    if not token_usage_enabled():
        return None

    pt = _as_int(prompt_tokens)
    ct = _as_int(completion_tokens)
    tt = _as_int(total_tokens) if total_tokens is not None else pt + ct
    if tt <= 0 and (pt > 0 or ct > 0):
        tt = pt + ct

    call_id = uuid.uuid4().hex
    preview = (question_preview or "").strip()[:200]
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with _lock:
        conn = sqlite3.connect(path)
        try:
            conn.execute(
                """
                INSERT INTO llm_calls (
                    id, created_at, session_id, user_id, channel, model, caller,
                    prompt_tokens, completion_tokens, total_tokens, question_preview
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    call_id,
                    _utc_now(),
                    str(session_id or "")[:128],
                    str(user_id or "")[:128],
                    str(channel or "")[:64],
                    str(model or "")[:128],
                    str(caller or "")[:64],
                    pt,
                    ct,
                    tt,
                    preview,
                ),
            )
            conn.commit()
        finally:
            conn.close()
    return call_id


def record_usage_object(
    usage: Any,
    *,
    model: str = "",
    caller: str = "",
    session_id: str = "",
    user_id: str = "",
    channel: str = "",
    question_preview: str = "",
) -> str | None:
    """Extract tokens from OpenAI Usage object / dict and persist."""
    if usage is None:
        return record_llm_call(
            model=model,
            caller=caller,
            session_id=session_id,
            user_id=user_id,
            channel=channel,
            question_preview=question_preview,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
        )
    if isinstance(usage, dict):
        pt = usage.get("prompt_tokens", usage.get("input_tokens", 0))
        ct = usage.get("completion_tokens", usage.get("output_tokens", 0))
        tt = usage.get("total_tokens")
    else:
        pt = getattr(usage, "prompt_tokens", None)
        if pt is None:
            pt = getattr(usage, "input_tokens", 0)
        ct = getattr(usage, "completion_tokens", None)
        if ct is None:
            ct = getattr(usage, "output_tokens", 0)
        tt = getattr(usage, "total_tokens", None)
    return record_llm_call(
        model=model,
        caller=caller,
        prompt_tokens=_as_int(pt),
        completion_tokens=_as_int(ct),
        total_tokens=_as_int(tt) if tt is not None else None,
        session_id=session_id,
        user_id=user_id,
        channel=channel,
        question_preview=question_preview,
    )


def aggregate_question_turns(
    records: list[dict[str, Any]],
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Group LLM call rows by session + question into user-facing turns."""
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    order: list[tuple[str, str]] = []
    for row in records:
        sid = str(row.get("session_id") or "")
        q = str(row.get("question_preview") or "").strip() or "(无摘要)"
        key = (sid, q)
        if key not in groups:
            groups[key] = {
                "session_id": sid,
                "question_preview": q,
                "created_at": str(row.get("created_at") or ""),
                "model": str(row.get("model") or ""),
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "llm_call_count": 0,
                "callers": [],
                "call_ids": [],
            }
            order.append(key)
        g = groups[key]
        g["prompt_tokens"] += int(row.get("prompt_tokens") or 0)
        g["completion_tokens"] += int(row.get("completion_tokens") or 0)
        g["total_tokens"] += int(row.get("total_tokens") or 0)
        g["llm_call_count"] += 1
        caller = str(row.get("caller") or "")
        if caller and caller not in g["callers"]:
            g["callers"].append(caller)
        cid = str(row.get("id") or "")
        if cid:
            g["call_ids"].append(cid)
        created = str(row.get("created_at") or "")
        if created > str(g["created_at"] or ""):
            g["created_at"] = created
            if row.get("model"):
                g["model"] = str(row.get("model") or "")

    ordered = sorted(order, key=lambda k: str(groups[k].get("created_at") or ""), reverse=True)
    cap = max(1, min(int(limit), 500))
    return [groups[k] for k in ordered[:cap]]


def summarize_calls(*, limit: int = 100, session_id: str | None = None) -> dict[str, Any]:
    """Global or session totals + recent call records."""
    init_token_usage_db()
    cap = max(1, min(int(limit), 500))
    path = _db_path()
    if not path.is_file():
        return {
            "total_tokens": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_calls": 0,
            "by_model": {},
            "records": [],
            "turns": [],
        }

    where = ""
    params: list[Any] = []
    if session_id:
        where = "WHERE session_id = ?"
        params.append(str(session_id))

    with _lock:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            agg = conn.execute(
                f"""
                SELECT
                    COALESCE(SUM(total_tokens), 0) AS total_tokens,
                    COALESCE(SUM(prompt_tokens), 0) AS total_input_tokens,
                    COALESCE(SUM(completion_tokens), 0) AS total_output_tokens,
                    COUNT(*) AS total_calls
                FROM llm_calls
                {where}
                """,
                params,
            ).fetchone()

            by_model_rows = conn.execute(
                f"""
                SELECT model,
                       COALESCE(SUM(total_tokens), 0) AS total_tokens,
                       COALESCE(SUM(prompt_tokens), 0) AS total_input_tokens,
                       COALESCE(SUM(completion_tokens), 0) AS total_output_tokens,
                       COUNT(*) AS total_runs
                FROM llm_calls
                {where}
                GROUP BY model
                ORDER BY total_tokens DESC
                """,
                params,
            ).fetchall()

            list_sql = f"""
                SELECT id, created_at, session_id, user_id, channel, model, caller,
                       prompt_tokens, completion_tokens, total_tokens, question_preview
                FROM llm_calls
                {where}
                ORDER BY created_at DESC
                LIMIT ?
            """
            records = conn.execute(list_sql, [*params, max(cap * 3, 50)]).fetchall()
        finally:
            conn.close()

    by_model: dict[str, dict[str, int]] = {}
    for row in by_model_rows:
        name = str(row["model"] or "unknown")
        by_model[name] = {
            "total_tokens": int(row["total_tokens"] or 0),
            "total_input_tokens": int(row["total_input_tokens"] or 0),
            "total_output_tokens": int(row["total_output_tokens"] or 0),
            "total_runs": int(row["total_runs"] or 0),
        }

    record_dicts = [
        {
            "id": str(r["id"]),
            "created_at": str(r["created_at"] or ""),
            "session_id": str(r["session_id"] or ""),
            "user_id": str(r["user_id"] or ""),
            "channel": str(r["channel"] or ""),
            "model": str(r["model"] or ""),
            "caller": str(r["caller"] or ""),
            "prompt_tokens": int(r["prompt_tokens"] or 0),
            "completion_tokens": int(r["completion_tokens"] or 0),
            "total_tokens": int(r["total_tokens"] or 0),
            "question_preview": str(r["question_preview"] or ""),
        }
        for r in records
    ]
    turns = aggregate_question_turns(record_dicts, limit=cap)

    return {
        "total_tokens": int(agg["total_tokens"] or 0) if agg else 0,
        "total_input_tokens": int(agg["total_input_tokens"] or 0) if agg else 0,
        "total_output_tokens": int(agg["total_output_tokens"] or 0) if agg else 0,
        "total_calls": int(agg["total_calls"] or 0) if agg else 0,
        "by_model": by_model,
        "records": record_dicts[:cap],
        "turns": turns,
    }


def summarize_session(session_id: str) -> dict[str, Any]:
    out = summarize_calls(limit=1, session_id=session_id)
    return {
        "thread_id": session_id,
        "total_tokens": out["total_tokens"],
        "total_input_tokens": out["total_input_tokens"],
        "total_output_tokens": out["total_output_tokens"],
        "total_runs": out["total_calls"],
        "by_model": out["by_model"],
    }

"""Read/write query_aliases.json and merge approved alias patches."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import settings
from retrieval.query_normalize import invalidate_aliases_cache, load_query_aliases


def _aliases_path() -> Path:
    return Path(settings.query_aliases_path)


def _proposals_path() -> Path:
    return Path(settings.query_aliases_path).parent / "query_alias_proposals.jsonl"


def load_aliases_file() -> dict[str, Any]:
    path = _aliases_path()
    if not path.is_file():
        return {"oral_map": {}, "term_aliases": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"oral_map": {}, "term_aliases": {}}


def save_aliases_file(data: dict[str, Any]) -> None:
    path = _aliases_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    invalidate_aliases_cache()


def merge_term_aliases(canonical: str, aliases: list[str]) -> dict[str, Any]:
    """Merge aliases under canonical term; returns applied patch."""
    canon = (canonical or "").strip()
    if not canon:
        return {"ok": False, "reason": "empty canonical"}
    extra = [str(a).strip() for a in aliases if str(a).strip()]
    merged = list(dict.fromkeys([canon, *extra]))
    data = load_aliases_file()
    term_aliases: dict[str, list[str]] = dict(data.get("term_aliases") or {})
    existing = list(term_aliases.get(canon) or [])
    combined = list(dict.fromkeys([canon, *existing, *merged]))
    if combined == existing and canon in term_aliases:
        return {"ok": True, "skipped": True, "canonical": canon, "aliases": existing}
    term_aliases[canon] = combined
    data["term_aliases"] = term_aliases
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_aliases_file(data)
    return {"ok": True, "canonical": canon, "aliases": combined}


def append_alias_proposal(
    *,
    canonical: str,
    aliases: list[str],
    question: str = "",
    feedback_id: str = "",
    detail: str = "",
) -> dict[str, Any]:
    proposal = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "canonical": canonical,
        "aliases": aliases,
        "question": question,
        "feedback_id": feedback_id,
        "detail": detail,
        "status": "pending_human_confirm",
    }
    path = _proposals_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(proposal, ensure_ascii=False) + "\n")
    return proposal


def alias_patch_from_question(question: str) -> dict[str, Any] | None:
    """Infer term alias patch when question fuzzy-matches lexicon but uses wrong form."""
    from retrieval.domain_lexicon import list_domain_terms
    from retrieval.term_fuzzy import suggest_query_corrections

    q = (question or "").strip()
    if not q:
        return None
    terms = list_domain_terms(limit=3000)
    if not terms:
        loaded = load_query_aliases().get("term_aliases") or {}
        terms = list(loaded.keys())
    corrections = suggest_query_corrections(q, terms)
    if not corrections:
        return None
    wrong, canon = corrections[0]
    if wrong == canon or canon in q:
        return None
    return {"canonical": canon, "aliases": [wrong]}

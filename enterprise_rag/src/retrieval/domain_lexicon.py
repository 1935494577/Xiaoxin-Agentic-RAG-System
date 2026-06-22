"""Domain term lexicon: auto-extracted from ingested documents + fuzzy query match."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import settings
from retrieval.term_fuzzy import fuzzy_match_terms as _fuzzy_match_terms

_HEADING = re.compile(r"^#{1,4}\s*(.+)$", re.MULTILINE)
_CN_TERM = re.compile(r"[\u4e00-\u9fff]{2,8}")
_PRODUCT_TERM = re.compile(
    r"[\u4e00-\u9fff]{2,4}(?:阅读|速记|运算)|[\u4e00-\u9fff]{2,4}力"
)
_TRAILING_NOISE = re.compile(r"(训练要求|培养|注意事项|基础练习|要求|要点|说明)$")


def _normalize_heading_piece(piece: str) -> str:
    p = _TRAILING_NOISE.sub("", piece.strip()).strip()
    return p
_NOISE_TERMS = frozenset(
    {
        "训练",
        "要求",
        "注意",
        "事项",
        "说明",
        "介绍",
        "内容",
        "文档",
        "章节",
        "部分",
        "如下",
        "详见",
        "参见",
        "年级",
        "学生",
        "老师",
        "公司",
        "部门",
    }
)


def _lexicon_path() -> Path:
    return Path(getattr(settings, "domain_lexicon_path", settings.query_aliases_path.parent / "domain_lexicon.json"))


def load_domain_lexicon() -> dict[str, Any]:
    path = _lexicon_path()
    if not path.is_file():
        return {"terms": {}, "updated_at": ""}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("terms"), dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"terms": {}, "updated_at": ""}


def save_domain_lexicon(data: dict[str, Any]) -> None:
    path = _lexicon_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def extract_domain_terms(text: str, *, max_terms: int = 200) -> list[str]:
    """Extract candidate domain terms from document text (headings + frequent phrases)."""
    raw = (text or "").strip()
    if not raw:
        return []
    found: set[str] = set()
    for m in _HEADING.finditer(raw):
        line = m.group(1).strip()
        for piece in re.split(r"[：:、，,\s]+", line):
            piece = _normalize_heading_piece(piece.strip())
            if 2 <= len(piece) <= 8 and piece not in _NOISE_TERMS:
                found.add(piece)
        for pm in _PRODUCT_TERM.finditer(line):
            term = pm.group(0).strip()
            if 2 <= len(term) <= 8 and term not in _NOISE_TERMS:
                found.add(term)
    for pm in _PRODUCT_TERM.finditer(raw):
        term = pm.group(0).strip()
        if 2 <= len(term) <= 8 and term not in _NOISE_TERMS:
            found.add(term)
    for m in _CN_TERM.finditer(raw):
        term = m.group(0)
        if term in _NOISE_TERMS or len(term) < 2:
            continue
        if any(term.endswith(s) for s in ("的", "了", "吗", "呢", "吧")):
            continue
        found.add(term)
    ordered = sorted(found, key=lambda t: (-len(t), t))
    return ordered[:max_terms]


def ingest_document_terms(text: str, *, source: str, max_terms: int = 80) -> list[str]:
    """Merge extracted terms into domain_lexicon.json (canonical forms from corpus)."""
    terms = extract_domain_terms(text, max_terms=max_terms)
    if not terms:
        return []
    data = load_domain_lexicon()
    bucket: dict[str, Any] = data.setdefault("terms", {})
    src = (source or "").strip() or "unknown"
    for term in terms:
        row = bucket.setdefault(term, {"sources": []})
        sources = row.setdefault("sources", [])
        if src not in sources:
            sources.append(src)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_domain_lexicon(data)
    try:
        from retrieval.term_embeddings import invalidate_term_embedding_cache

        invalidate_term_embedding_cache()
    except ImportError:
        pass
    return terms


def list_domain_terms(*, limit: int = 5000) -> list[str]:
    terms = load_domain_lexicon().get("terms") or {}
    return sorted(terms.keys())[:limit]


def fuzzy_match_terms(query: str, terms: list[str], *, max_edit_distance: int = 1) -> list[str]:
    """Map noisy query fragments to closest domain terms (typo / ASR recovery)."""
    use_pinyin = bool(getattr(settings, "domain_fuzzy_pinyin_enabled", True))
    return _fuzzy_match_terms(
        query,
        terms,
        max_edit_distance=max_edit_distance,
        use_pinyin=use_pinyin,
    )


def suggest_and_apply_domain_corrections(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Apply trusted manual alias corrections to query text (Tier 0/1).

    Domain lexicon fuzzy match only expands search variants — it does not rewrite
    the canonical query, to avoid false positives on large auto-built lexicons.
    """
    from retrieval.query_normalize import load_query_aliases
    from retrieval.term_fuzzy import apply_query_corrections

    base = (text or "").strip()
    if not base:
        return base, []
    corrections: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for canonical, forms in (load_query_aliases().get("term_aliases") or {}).items():
        canon = str(canonical).strip()
        if not canon:
            continue
        for form in sorted({str(f).strip() for f in (forms or []) if str(f).strip()}, key=len, reverse=True):
            if len(form) < 3:
                continue
            if form and form in base and form != canon:
                key = (form, canon)
                if key not in seen:
                    seen.add(key)
                    corrections.append(key)
    if not corrections:
        return base, []
    corrections = _prune_substring_corrections(corrections)
    corrected = apply_query_corrections(base, corrections[:5])
    return corrected, corrections[:5]


def _prune_substring_corrections(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Drop shorter wrong fragments contained in a longer one (avoid 超脑→超脑阅读 on 超脑阅度)."""
    ordered = sorted(pairs, key=lambda row: (-len(row[0]), row[0]))
    kept: list[tuple[str, str]] = []
    for wrong, canon in ordered:
        if any(wrong in prev and wrong != prev for prev, _ in kept):
            continue
        kept.append((wrong, canon))
    return kept


def rebuild_domain_lexicon_from_texts(
    sources: list[tuple[str, str]],
    *,
    max_terms_per_doc: int = 80,
    replace: bool = False,
) -> dict[str, Any]:
    """Rebuild domain lexicon from (source, text) pairs."""
    if replace:
        data: dict[str, Any] = {"terms": {}, "updated_at": ""}
    else:
        data = load_domain_lexicon()
    bucket: dict[str, Any] = data.setdefault("terms", {})
    ingested = 0
    for source, text in sources:
        src = (source or "").strip() or "unknown"
        for term in extract_domain_terms(text, max_terms=max_terms_per_doc):
            row = bucket.setdefault(term, {"sources": []})
            srcs = row.setdefault("sources", [])
            if src not in srcs:
                srcs.append(src)
            ingested += 1
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_domain_lexicon(data)
    try:
        from retrieval.term_embeddings import invalidate_term_embedding_cache

        invalidate_term_embedding_cache()
    except ImportError:
        pass
    return {"term_count": len(bucket), "ingested_rows": ingested, "updated_at": data["updated_at"]}


def rebuild_domain_lexicon_from_raw_dir(
    raw_dir: Path | None = None,
    *,
    replace: bool = False,
    max_terms_per_doc: int = 80,
) -> dict[str, Any]:
    """Scan data/raw for text files and rebuild lexicon."""
    root = Path(raw_dir or settings.data_raw_dir)
    sources: list[tuple[str, str]] = []
    if root.is_dir():
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".txt", ".md", ".markdown"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            rel = str(path.relative_to(root)).replace("\\", "/")
            sources.append((rel, text))
    return rebuild_domain_lexicon_from_texts(
        sources,
        max_terms_per_doc=max_terms_per_doc,
        replace=replace,
    )


def expand_query_with_domain_lexicon(text: str, *, max_hits: int = 3) -> list[str]:
    """Return extra search variant strings from domain fuzzy match."""
    terms = list_domain_terms()
    if not terms:
        return []
    matched = fuzzy_match_terms(text, terms, max_edit_distance=1)
    extras: list[str] = []
    base = (text or "").strip()
    for term in matched[:max_hits]:
        if term and term not in base:
            extras.append(f"{base} {term}".strip())
        elif term:
            extras.append(term)
    return list(dict.fromkeys(extras))

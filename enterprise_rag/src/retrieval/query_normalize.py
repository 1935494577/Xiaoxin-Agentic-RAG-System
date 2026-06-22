"""Rule-based query normalization for retrieval (zero LLM latency)."""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

from config import settings

_DEFAULT_ORAL = {
    "咋整": "怎么",
    "咋弄": "怎么",
    "咋办": "怎么办",
    "咋": "怎么",
    "啥": "什么",
    "啥子": "什么",
    "有木有": "有没有",
    "咋样": "怎么样",
    "怎样": "怎么样",
    "咱": "我们",
    "俺": "我",
}

_DEFAULT_ALIASES: dict[str, list[str]] = {
    "超脑阅读": ["超脑阅度", "超脑", "超脑速读"],
    "极速运算": ["速算", "快速运算"],
    "扫描速记": ["速记"],
    "脑科学": ["脑力", "大脑科学"],
}

_MULTI_SPACE = re.compile(r"\s+")
_VOICE_SEGMENT_SPLIT = re.compile(r"[。！？!?；;]+")
_VOICE_FILLER_SEG = re.compile(
    r"^(?:嗯+|啊+|呃+|那个+|这个+|我就+|电脑+|帮我+|请+|然后+|就是+)$",
    re.IGNORECASE,
)
_VOICE_FILLER_PREFIX = re.compile(
    r"^(?:嗯+|啊+|呃+|那个+|这个+|我就+|电脑+|帮我+|请+|然后+|就是+)[。，,\.!！?？\s]*",
    re.IGNORECASE,
)
_INTENT_HINT = re.compile(
    r"天气|气温|温度|今天|今日|现在|几点|几号|星期|放假|新闻|关系|组织|汇报|"
    r"超脑|阅读|训练|入库|文档|公司|部门",
    re.IGNORECASE,
)


def _aliases_path() -> Path:
    return Path(settings.query_aliases_path)


def invalidate_aliases_cache() -> None:
    load_query_aliases.cache_clear()


@lru_cache(maxsize=1)
def load_query_aliases() -> dict[str, Any]:
    path = _aliases_path()
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                oral = dict(_DEFAULT_ORAL)
                oral.update({str(k): str(v) for k, v in (data.get("oral_map") or {}).items()})
                terms: dict[str, list[str]] = {k: list(v) for k, v in _DEFAULT_ALIASES.items()}
                for k, v in (data.get("term_aliases") or {}).items():
                    canon = str(k).strip()
                    if not canon:
                        continue
                    aliases = [str(x).strip() for x in (v or []) if str(x).strip()]
                    terms[canon] = list(dict.fromkeys([canon, *aliases]))
                return {"oral_map": oral, "term_aliases": terms}
        except (OSError, json.JSONDecodeError):
            pass
    return {"oral_map": dict(_DEFAULT_ORAL), "term_aliases": dict(_DEFAULT_ALIASES)}


def _apply_oral_map(text: str, oral_map: dict[str, str]) -> str:
    out = text
    for src in sorted(oral_map, key=len, reverse=True):
        dst = oral_map[src]
        if src and src in out:
            out = out.replace(src, dst)
    return out


def normalize_query(text: str) -> str:
    """Structural + colloquial normalization for retrieval variants."""
    raw = unicodedata.normalize("NFKC", (text or "").strip())
    if not raw:
        return ""
    raw = _MULTI_SPACE.sub(" ", raw)
    oral = load_query_aliases()["oral_map"]
    out = _apply_oral_map(raw, oral)
    out = _MULTI_SPACE.sub(" ", out).strip()
    out = re.sub(r"[嘛呗啦呀啊呢吧]+([？?。!！])", r"\1", out)
    out = _MULTI_SPACE.sub(" ", out).strip()
    return out or raw


def looks_like_voice_transcript(text: str) -> bool:
    """Heuristic: multi-segment ASR with short filler clauses."""
    raw = unicodedata.normalize("NFKC", (text or "").strip())
    if not raw:
        return False
    segments = [s.strip() for s in _VOICE_SEGMENT_SPLIT.split(raw) if s.strip()]
    if len(segments) >= 2 and any(len(s) <= 4 for s in segments):
        return True
    return bool(_VOICE_FILLER_SEG.search(raw))


def _score_voice_segment(segment: str) -> int:
    seg = (segment or "").strip()
    if not seg or _VOICE_FILLER_SEG.fullmatch(seg):
        return -10
    score = min(len(seg) // 4, 3)
    if _INTENT_HINT.search(seg):
        score += 8
    return score


def clean_oral_user_message(text: str) -> str:
    """
    Pick the most intent-like clause from noisy voice transcripts.
    Used in prepare_turn before condense/routing — does not change answer formatting.
    """
    raw = unicodedata.normalize("NFKC", (text or "").strip())
    if not raw:
        return ""
    if not looks_like_voice_transcript(raw):
        return raw
    segments = [s.strip() for s in _VOICE_SEGMENT_SPLIT.split(raw) if s.strip()]
    candidates = segments if len(segments) > 1 else [raw]
    best_seg = max(candidates, key=_score_voice_segment)
    if _score_voice_segment(best_seg) <= 0:
        best_seg = raw
    cleaned = best_seg
    while True:
        nxt = _VOICE_FILLER_PREFIX.sub("", cleaned).strip(" ，,.!！?？")
        if nxt == cleaned:
            break
        cleaned = nxt
    return cleaned or raw


def expand_bm25_query(text: str, *, aliases: dict[str, list[str]] | None = None) -> str:
    """Append canonical / alias terms when a known form appears in the query."""
    base = (text or "").strip()
    if not base:
        return base
    term_aliases = aliases if aliases is not None else load_query_aliases()["term_aliases"]
    extras: list[str] = []
    for canonical, forms in term_aliases.items():
        hits = [canonical, *forms]
        if any(form and form in base for form in hits):
            extras.extend(h for h in hits if h)
    if not extras:
        return base
    merged = " ".join(dict.fromkeys([base, *extras]))
    return merged


def build_search_variants(text: str, *, max_variants: int = 3) -> list[str]:
    """
    Build distinct retrieval query strings (original + normalized + BM25-expanded).
    Used for multi-path RRF fusion in hybrid_search.
    """
    original = (text or "").strip()
    if not original:
        return []
    variants: list[str] = [original]
    normalized = normalize_query(original)
    if normalized and normalized != original:
        variants.append(normalized)
    expanded = expand_bm25_query(normalized or original)
    if expanded and expanded not in variants:
        variants.append(expanded)
    return variants[: max(1, max_variants)]

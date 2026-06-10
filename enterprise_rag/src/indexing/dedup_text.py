"""Text normalization, content hashing, simhash, and similarity for ingest/retrieval dedup."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from functools import lru_cache

import jieba

_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\u4e00-\u9fff]+", re.UNICODE)


def normalize_text(text: str) -> str:
    """Collapse whitespace and strip for stable hashing."""
    raw = unicodedata.normalize("NFKC", text or "")
    raw = _WS_RE.sub(" ", raw).strip().lower()
    return raw


def content_hash(text: str) -> str:
    normalized = normalize_text(text)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _tokenize(text: str) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []
    return [t for t in jieba.cut(text) if t.strip()]


def _shingles(tokens: list[str], width: int = 3) -> list[str]:
    if not tokens:
        return []
    if len(tokens) < width:
        return [" ".join(tokens)]
    return [" ".join(tokens[i : i + width]) for i in range(len(tokens) - width + 1)]


def simhash64(text: str) -> int:
    """64-bit simhash over word shingles (Chinese via jieba)."""
    shingles = _shingles(_tokenize(text))
    if not shingles:
        return 0
    vector = [0] * 64
    for sh in shingles:
        h = int(hashlib.md5(sh.encode("utf-8")).hexdigest(), 16)
        for i in range(64):
            vector[i] += 1 if (h >> i) & 1 else -1
    out = 0
    for i, v in enumerate(vector):
        if v > 0:
            out |= 1 << i
    return out


def hamming64(a: int, b: int) -> int:
    return (a ^ b).bit_count()


@lru_cache(maxsize=4096)
def _char_ngrams(text: str, n: int = 3) -> frozenset[str]:
    normalized = normalize_text(text)
    normalized = _PUNCT_RE.sub("", normalized)
    if len(normalized) < n:
        return frozenset([normalized]) if normalized else frozenset()
    return frozenset(normalized[i : i + n] for i in range(len(normalized) - n + 1))


def char_ngram_jaccard(a: str, b: str, n: int = 3) -> float:
    """Character n-gram Jaccard similarity in [0, 1]."""
    sa, sb = _char_ngrams(a, n), _char_ngrams(b, n)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


def preview_fingerprint(text: str, max_chars: int = 200) -> str:
    snippet = normalize_text(text)[:max_chars]
    return hashlib.sha1(snippet.encode("utf-8")).hexdigest()[:16]

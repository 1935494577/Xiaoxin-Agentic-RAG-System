"""Chinese term fuzzy match: weighted edit distance, shape-similar chars, optional pinyin."""

from __future__ import annotations

from functools import lru_cache

# 常见 ASR/错字形近字组（替换代价视为 0）
_SHAPE_GROUPS: tuple[frozenset[str], ...] = (
    frozenset("读度渡"),
    frozenset("记纪济计"),
    frozenset("力历利立"),
    frozenset("脑恼"),
    frozenset("阅越悦"),
    frozenset("算酸"),
    frozenset("扫绍"),
    frozenset("知智"),
    frozenset("感敢"),
)


def _shape_similar(a: str, b: str) -> bool:
    if a == b:
        return True
    for group in _SHAPE_GROUPS:
        if a in group and b in group:
            return True
    return False


def _substitution_cost(a: str, b: str, *, shape_similar: bool) -> int:
    if a == b:
        return 0
    if shape_similar and _shape_similar(a, b):
        return 0
    return 1


def weighted_edit_distance(a: str, b: str, *, shape_similar: bool = True) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            ins = cur[j - 1] + 1
            delete = prev[j] + 1
            sub = prev[j - 1] + _substitution_cost(ca, cb, shape_similar=shape_similar)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


@lru_cache(maxsize=4096)
def _pinyin_key(text: str) -> str:
    if not text:
        return ""
    try:
        from pypinyin import Style, lazy_pinyin

        return "".join(lazy_pinyin(text, style=Style.NORMAL))
    except ImportError:
        return ""


def _pinyin_edit_distance(a: str, b: str) -> int | None:
    pa, pb = _pinyin_key(a), _pinyin_key(b)
    if not pa or not pb:
        return None
    if abs(len(pa) - len(pb)) > 4:
        return None
    return weighted_edit_distance(pa, pb, shape_similar=False)


def _term_matches_fragment(
    fragment: str,
    term: str,
    *,
    max_edit_distance: int,
    use_pinyin: bool,
) -> bool:
    if not fragment or not term:
        return False
    if term in fragment or fragment in term:
        return True
    if abs(len(fragment) - len(term)) > max_edit_distance + 1:
        return False
    if weighted_edit_distance(fragment, term) <= max_edit_distance:
        return True
    if use_pinyin:
        pd = _pinyin_edit_distance(fragment, term)
        if pd is not None and pd <= max(1, max_edit_distance):
            return True
    return False


def fuzzy_match_terms(
    query: str,
    terms: list[str],
    *,
    max_edit_distance: int = 1,
    use_pinyin: bool = True,
) -> list[str]:
    """Map noisy query fragments to closest domain terms."""
    q = (query or "").strip()
    if not q or not terms:
        return []
    hits: list[str] = []
    for term in terms:
        if not term or len(term) < 2:
            continue
        if term in q:
            hits.append(term)
            continue
        if _term_matches_fragment(q, term, max_edit_distance=max_edit_distance, use_pinyin=use_pinyin):
            hits.append(term)
            continue
        win_len = len(term)
        if win_len >= 2 and len(q) >= win_len:
            for i in range(0, len(q) - win_len + 1):
                window = q[i : i + win_len]
                if _term_matches_fragment(
                    window,
                    term,
                    max_edit_distance=max_edit_distance,
                    use_pinyin=use_pinyin,
                ):
                    hits.append(term)
                    break
    return list(dict.fromkeys(hits))


def suggest_query_corrections(
    query: str,
    terms: list[str],
    *,
    max_edit_distance: int = 1,
    use_pinyin: bool = True,
) -> list[tuple[str, str]]:
    """Return (wrong_fragment, canonical_term) pairs, longest fragments first."""
    q = (query or "").strip()
    if not q or not terms:
        return []
    pairs: list[tuple[str, str, int]] = []
    seen: set[tuple[str, str]] = set()
    for term in terms:
        if not term or len(term) < 2:
            continue
        win_len = len(term)
        if len(q) < win_len:
            if _term_matches_fragment(q, term, max_edit_distance=max_edit_distance, use_pinyin=use_pinyin):
                key = (q, term)
                if q != term and key not in seen:
                    seen.add(key)
                    pairs.append((q, term, len(q)))
            continue
        for i in range(0, len(q) - win_len + 1):
            window = q[i : i + win_len]
            if window == term:
                continue
            if _term_matches_fragment(
                window,
                term,
                max_edit_distance=max_edit_distance,
                use_pinyin=use_pinyin,
            ):
                key = (window, term)
                if key not in seen:
                    seen.add(key)
                    pairs.append((window, term, len(window)))
    pairs.sort(key=lambda row: (-row[2], row[0]))
    return [(wrong, canon) for wrong, canon, _ in pairs]


def apply_query_corrections(text: str, corrections: list[tuple[str, str]]) -> str:
    out = (text or "").strip()
    for wrong, canon in corrections:
        if wrong and canon and wrong != canon and wrong in out:
            out = out.replace(wrong, canon, 1)
    return out.strip() or text

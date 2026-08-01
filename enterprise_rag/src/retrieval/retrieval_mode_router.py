"""Rule-based retrieval mode routing: exact / semantic / hybrid."""

from __future__ import annotations

import re
import uuid
from typing import Literal

from config import settings

RetrievalMode = Literal["exact", "semantic", "hybrid"]
ExamSearchMode = Literal["exact", "semantic"]

# Ticket / order / SKU-style identifiers
_ID_TOKEN = re.compile(
    r"(?:^|\s)(?:WO|SP|TK|ORD|SKU|ID)[-_]?[\w-]{4,}(?:\s|$)",
    re.I,
)
_UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.I,
)
_PURE_CODE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{5,}$", re.I)

# Semantic question patterns
_SEMANTIC = re.compile(
    r"(怎么|如何|为何|为什么|怎样|是什么|什么是|有哪些|能不能|可不可以|"
    r"什么意思|什么意思|介绍|讲解|说明一下|帮我理解)",
    re.I,
)

# Region with administrative suffix, or common province/city names (exam / policy queries)
_REGION = re.compile(r"[\u4e00-\u9fff]{2,4}(?:省|市|区|县)")
_REGION_NAME = re.compile(
    r"(浙江|江苏|北京|上海|广东|山东|河南|四川|湖北|湖南|河北|安徽|福建|辽宁|陕西|江西|重庆|天津|"
    r"云南|广西|山西|内蒙古|贵州|甘肃|海南|宁夏|青海|西藏|黑龙江|吉林|新疆|香港|澳门|台湾|萧山|深圳|广州|杭州|南京|成都|武汉)"
)
_EXAM_SEMANTIC = re.compile(r"(相关|类似|关于|涉及|主题|知识点|概念)")

# Structured / mixed signals (region, grade, year + topic)
_YEAR = re.compile(r"(19|20)\d{2}")
_GRADE = re.compile(r"(高[一二三]|初[一二三]|小[一二三四五六])")
_TOPIC_WORD = re.compile(r"(函数|方程|几何|概率|数列|三角|向量|导数|写作|实验)")

# Short policy / title-like (keyword-heavy, no question words)
_POLICY_LIKE = re.compile(r"(政策|制度|规定|办法|细则|手册|指南|流程|标准|规范|条例)")


def detect_retrieval_mode(message: str) -> RetrievalMode:
    """Classify KB retrieval backend from user text."""
    q = (message or "").strip()
    if not q:
        return "semantic"

    if _UUID.search(q) or _ID_TOKEN.search(q) or _PURE_CODE.match(q.replace(" ", "")):
        return "exact"

    has_semantic = bool(_SEMANTIC.search(q))
    has_year = bool(_YEAR.search(q))
    has_grade = bool(_GRADE.search(q))
    has_region = bool(_REGION.search(q) or _REGION_NAME.search(q))
    has_topic = bool(_TOPIC_WORD.search(q))
    token_count = len(q.split())

    # Mixed precise tokens + descriptive context
    if (has_year or has_grade or has_region) and (has_topic or len(q) >= 10 or token_count >= 3):
        return "hybrid"
    if token_count >= 3 and has_semantic and (has_year or has_grade or has_region):
        return "hybrid"

    if has_semantic and not (has_year or _ID_TOKEN.search(q)):
        return "semantic"

    # Short title / policy lookup (<=2 tokens or explicit policy words)
    if len(q) <= 20 and (_POLICY_LIKE.search(q) or token_count <= 2):
        return "exact"

    if token_count >= 4 and not has_semantic:
        return "hybrid"

    return "semantic"


def resolve_retrieval_mode(
    message: str,
    *,
    fast_mode: bool = False,
    router_enabled: bool | None = None,
    override: str | None = None,
) -> RetrievalMode:
    """Apply config + fast-mode downgrade on top of rule detection."""
    if override in ("exact", "semantic", "hybrid"):
        return override  # type: ignore[return-value]

    enabled = (
        bool(settings.retrieval_mode_router_enabled)
        if router_enabled is None
        else bool(router_enabled)
    )
    if not enabled:
        return "hybrid"

    mode = detect_retrieval_mode(message)
    if fast_mode and bool(settings.stream_fast_downgrade_hybrid) and mode == "hybrid":
        return "semantic"
    return mode


def detect_exam_search_mode(keywords: str) -> ExamSearchMode:
    """Exam bank: exact ID/title tokens vs broader semantic-style query."""
    q = (keywords or "").strip()
    if not q:
        return "exact"
    if _UUID.search(q):
        return "exact"
    try:
        uuid.UUID(q)
        return "exact"
    except ValueError:
        pass
    tokens = [t for t in q.split() if t]
    if len(tokens) == 1 and len(tokens[0]) <= 24:
        return "exact"
    if _GRADE.search(q) or _REGION.search(q) or _REGION_NAME.search(q) or _YEAR.search(q):
        return "exact"
    if _EXAM_SEMANTIC.search(q):
        return "semantic"
    if len(tokens) <= 3 and not _SEMANTIC.search(q):
        return "exact"
    return "semantic"


def resolve_exam_paper_hits(
    keywords: str,
    *,
    limit: int = 10,
    reader_user_id: str | None = None,
) -> tuple[list[dict], str]:
    """
    Search exam papers with exact-first strategy.
    Returns (hits, search_mode).
    """
    from exam_bank import store

    mode = detect_exam_search_mode(keywords)
    q = (keywords or "").strip()
    if not q:
        return [], mode

    # Exact: UUID id
    if _UUID.search(q):
        pid = _UUID.search(q).group(0)  # type: ignore[union-attr]
        row = store.get_source_paper(pid)
        if row and store.reader_can_access_collection(
            row.get("collection_id") or "",
            reader_user_id=reader_user_id,
        ):
            return [row], "exact"

    try:
        uuid.UUID(q)
        row = store.get_source_paper(q)
        if row and store.reader_can_access_collection(
            row.get("collection_id") or "",
            reader_user_id=reader_user_id,
        ):
            return [row], "exact"
    except ValueError:
        pass

    hits = store.search_source_papers(q, limit=limit, reader_user_id=reader_user_id)
    if hits:
        return hits, mode

    if mode == "exact":
        for tok in q.split():
            hits = store.search_source_papers(tok, limit=limit, reader_user_id=reader_user_id)
            if hits:
                return hits, mode

    return [], mode

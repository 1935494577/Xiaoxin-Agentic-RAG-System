"""Unified query understanding: oral/voice cleanup, variants, intent, rewrite policy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from config import settings
from retrieval.domain_lexicon import expand_query_with_domain_lexicon, suggest_and_apply_domain_corrections
from retrieval.term_embeddings import expand_query_with_embedding_neighbors
from retrieval.query_normalize import (
    build_search_variants,
    clean_oral_user_message,
    looks_like_voice_transcript,
    normalize_query,
)

from retrieval.retrieval_mode_router import resolve_retrieval_mode

QueryIntent = Literal["kb", "realtime", "graph", "chitchat", "unknown"]
RetrievalMode = Literal["exact", "semantic", "hybrid"]

_DEFAULT_REWRITE_THRESHOLD = 0.65


@dataclass(frozen=True)
class QueryUnderstanding:
    raw: str
    message: str
    retrieval_query: str
    search_variants: list[str]
    intent: QueryIntent
    retrieval_mode: RetrievalMode
    rule_confidence: float
    needs_llm_rewrite: bool
    signals: dict[str, Any] = field(default_factory=dict)

    @property
    def canonical_query(self) -> str:
        return self.retrieval_query

    @property
    def noise_stripped(self) -> bool:
        return bool(self.raw and self.message and self.raw.strip() != self.message.strip())

    def intent_label(self) -> str:
        mapping = {
            "kb": "kb_definition",
            "realtime": "realtime_tools",
            "graph": "org_graph",
            "chitchat": "chitchat",
            "unknown": "chitchat",
        }
        return mapping.get(self.intent, self.intent)

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_query": self.canonical_query,
            "search_variants": list(self.search_variants),
            "intent": self.intent_label(),
            "retrieval_mode": self.retrieval_mode,
            "noise_stripped": self.noise_stripped,
            "confidence": round(self.rule_confidence, 4),
            "needs_llm_rewrite": self.needs_llm_rewrite,
            "signals": dict(self.signals),
        }


def rule_confidence(
    raw: str,
    message: str,
    *,
    variant_count: int = 1,
    domain_corrections: int = 0,
) -> float:
    """Heuristic confidence that rule-based variants are enough for retrieval."""
    score = 1.0
    raw = (raw or "").strip()
    message = (message or "").strip()
    if looks_like_voice_transcript(raw):
        score -= 0.35
    if raw and message and raw != message:
        score -= 0.15
    normalized = normalize_query(message)
    if normalized and normalized != message:
        score -= 0.1
    if variant_count >= 2:
        score += 0.08
    if variant_count >= 3:
        score += 0.05
    if domain_corrections > 0:
        score += min(0.18, 0.08 * domain_corrections)
    oral_markers = ("咋", "啥", "俺", "咱", "嘛", "呗", "啦")
    if any(m in raw for m in oral_markers):
        score -= 0.12
    return max(0.0, min(1.0, score))


def needs_llm_retrieval_rewrite(confidence: float, *, threshold: float | None = None) -> bool:
    """Low rule confidence → allow LLM query rewrite at retrieval time."""
    th = threshold if threshold is not None else _DEFAULT_REWRITE_THRESHOLD
    if not bool(settings.query_rewrite_conditional_enabled):
        return bool(settings.query_rewrite_enabled)
    if bool(settings.query_rewrite_enabled):
        return confidence < th
    return confidence < th


def detect_query_intent(message: str) -> QueryIntent:
    from agent.chitchat import is_chitchat_message
    from agent.tools.runtime.routing import (
        is_relationship_graph_question,
        question_needs_realtime_tools,
    )

    q = (message or "").strip()
    if not q:
        return "unknown"
    if is_relationship_graph_question(q):
        return "graph"
    if question_needs_realtime_tools(q):
        return "realtime"
    if is_chitchat_message(q):
        return "chitchat"
    return "kb"


def build_search_variants_enriched(text: str, *, max_variants: int | None = None) -> list[str]:
    cap = max_variants if max_variants is not None else int(settings.query_normalize_max_variants)
    base_variants = build_search_variants(text, max_variants=cap)
    extras = [
        *expand_query_with_domain_lexicon(text),
        *expand_query_with_embedding_neighbors(text),
    ]
    merged: list[str] = []
    for v in [*base_variants, *extras]:
        v = (v or "").strip()
        if v and v not in merged:
            merged.append(v)
    return merged[: max(1, cap + 2)]


def understand_query(raw: str, *, retrieval_query: str | None = None) -> QueryUnderstanding:
    """
    Single entry for user-side text processing before retrieval/routing.
    Does not change answer formatting — only normalizes input and plans retrieval.
    """
    original = (raw or "").strip()
    message = clean_oral_user_message(original) or original
    rq = (retrieval_query or message).strip() or message
    rq, corrections = suggest_and_apply_domain_corrections(rq)
    variants = build_search_variants_enriched(rq)
    confidence = rule_confidence(
        original,
        rq,
        variant_count=len(variants),
        domain_corrections=len(corrections),
    )
    intent = detect_query_intent(rq)
    retrieval_mode = resolve_retrieval_mode(rq)
    needs_rewrite = needs_llm_retrieval_rewrite(confidence)
    signals: dict[str, Any] = {
        "voice_transcript": looks_like_voice_transcript(original),
        "normalized": normalize_query(rq),
    }
    if corrections:
        signals["domain_corrections"] = [{"from": w, "to": c} for w, c in corrections]
    return QueryUnderstanding(
        raw=original,
        message=message,
        retrieval_query=rq,
        search_variants=variants,
        intent=intent,
        retrieval_mode=retrieval_mode,
        rule_confidence=confidence,
        needs_llm_rewrite=needs_rewrite,
        signals=signals,
    )

"""Judge whether retrieved KB chunks are sufficient before answering."""

from __future__ import annotations

from typing import Any

from config import settings
from openai import OpenAI

# KB 回答明确表示「资料里没有」时的兜底触发（用于二次校验，非流式场景）
KB_MISS_MARKERS = (
    "资料不足",
    "无法从参考资料",
    "无法根据参考资料",
    "没有相关信息",
    "未包含",
    "未涉及",
    "无法确认",
    "不能确认",
    "参考资料中未",
    "提供的参考资料",
)


def has_usable_context(contexts: list[str], contexts_meta: list[dict[str, Any]]) -> bool:
    if contexts and any(str(c).strip() for c in contexts):
        return True
    return any(str(row.get("text") or "").strip() for row in contexts_meta or [])


def best_hybrid_score(contexts_meta: list[dict[str, Any]]) -> float:
    best = 0.0
    for row in contexts_meta or []:
        val = row.get("hybrid_score")
        if val is None:
            continue
        try:
            best = max(best, float(val))
        except (TypeError, ValueError):
            continue
    return best


def best_rerank_score(contexts_meta: list[dict[str, Any]]) -> float | None:
    scores: list[float] = []
    for row in contexts_meta or []:
        val = row.get("rerank_score")
        if val is None:
            continue
        try:
            scores.append(float(val))
        except (TypeError, ValueError):
            continue
    return max(scores) if scores else None


def answer_indicates_kb_miss(text: str) -> bool:
    """Heuristic: model admitted KB cannot answer."""
    t = (text or "").strip()
    if not t:
        return True
    hits = sum(1 for m in KB_MISS_MARKERS if m in t)
    if hits >= 2:
        return True
    if hits == 1 and len(t) < 180:
        return True
    return False


def _llm_kb_relevant(
    question: str,
    contexts: list[str],
    llm_runtime: dict[str, Any],
) -> bool:
    api_key = (llm_runtime.get("llm_api_key") or "").strip() or settings.openai_api_key
    if not api_key:
        return False

    api_base = (llm_runtime.get("llm_api_base") or "").strip() or settings.openai_api_base
    headers = llm_runtime.get("llm_extra_headers")
    client_kw: dict[str, Any] = {"api_key": api_key, "base_url": api_base}
    if isinstance(headers, dict) and headers:
        client_kw["default_headers"] = headers
    client = OpenAI(**client_kw)
    model = llm_runtime.get("chat_model") or settings.openai_chat_model

    body = "\n".join(f"[{i + 1}] {c[:800]}" for i, c in enumerate(contexts[:3]))
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "你是检索相关性判断员。仅输出 YES 或 NO。"
                    "YES=参考资料足以直接回答问题；NO=资料不相关或不足以回答。"
                ),
            },
            {
                "role": "user",
                "content": f"用户问题：{question}\n\n检索到的资料：\n{body}",
            },
        ],
        temperature=0.0,
        max_tokens=4,
    )
    tag = (resp.choices[0].message.content or "").strip().upper()
    return tag.startswith("Y")


def should_use_knowledge_base(
    question: str,
    contexts: list[str],
    contexts_meta: list[dict[str, Any]],
    *,
    kb_min_score: float,
    kb_min_rerank_score: float,
    kb_llm_judge: bool,
    llm_runtime: dict[str, Any] | None,
) -> bool:
    """
    True → 走知识库回答；False → 走通用知识。
    流程：检索有结果 → 看重排分/混合分 → 不确定时用 LLM 判断 YES/NO。
    """
    if not has_usable_context(contexts, contexts_meta):
        return False

    rerank = best_rerank_score(contexts_meta)
    if rerank is not None:
        if rerank >= float(kb_min_rerank_score):
            return True
        return False

    hybrid = best_hybrid_score(contexts_meta)
    if hybrid >= float(kb_min_score):
        return True

    if kb_llm_judge and llm_runtime:
        return _llm_kb_relevant(question, contexts, llm_runtime)

    return False


def resolve_answer_mode(
    question: str,
    contexts: list[str],
    contexts_meta: list[dict[str, Any]],
    *,
    kb_min_score: float,
    kb_min_rerank_score: float,
    kb_llm_judge: bool,
    general_fallback_enabled: bool,
    llm_runtime: dict[str, Any] | None = None,
) -> str:
    if not general_fallback_enabled:
        return "kb" if has_usable_context(contexts, contexts_meta) else "kb"

    if should_use_knowledge_base(
        question,
        contexts,
        contexts_meta,
        kb_min_score=kb_min_score,
        kb_min_rerank_score=kb_min_rerank_score,
        kb_llm_judge=kb_llm_judge,
        llm_runtime=llm_runtime,
    ):
        return "kb"
    return "general"

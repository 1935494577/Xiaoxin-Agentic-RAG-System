"""Judge whether retrieved KB chunks are sufficient before answering."""

from __future__ import annotations

import re
from typing import Any, Literal

from config import settings
from openai import OpenAI

from agent.llm_routing import model_for_task

# hybrid_score 为候选集内 min-max 归一化，不能单独作为「命中」依据
# rerank_score 为 cross-encoder 绝对相关分（越高越相关）
ABSOLUTE_RERANK_MIN = 0.12
RERANK_CONFIDENT_MIN = 0.45

RetrievalConfidence = Literal["confident", "gray", "weak"]

# 文本命中任一条即视为「知识库未答上」（触发混合模式通用兜底）
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
    "并没有",
    "无法回答",
    "不能回答",
    "没有关于",
    "无相关",
    "不在资料",
    "不在知识库",
    "知识库中",
    "资料中没有",
    "资料里没",
    "找不到相关",
    "不认识",
    "知识库里",
    "没听说",
    "未收录",
)

KB_MISS_PATTERNS = (
    re.compile(r"知识库.{0,16}(没有|并无|未|不(包含|具备|涉及))"),
    re.compile(r"(无法|不能)(直接)?回答(这个|该|此)?问题"),
    re.compile(r"没有.{0,12}相关(资料|信息|内容)"),
    re.compile(r"资料(中|里)?(并)?(不|未|无).{0,8}(相关|提及|包含)"),
    re.compile(r"(不(认识|了解|清楚)|没听说过?).{0,40}知识库"),
    re.compile(r"知识库.{0,24}(没有|无|未).{0,16}(相关|内容|记录|信息)"),
    re.compile(r"还是(不(认识|了解|知道)|没听说)"),
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


def effective_rerank_floor(kb_min_rerank_score: float, *, topic_shift: bool = False) -> float:
    floor = max(float(kb_min_rerank_score), ABSOLUTE_RERANK_MIN)
    if topic_shift:
        floor = max(floor, ABSOLUTE_RERANK_MIN)
    return floor


def assess_retrieval_confidence(
    contexts_meta: list[dict[str, Any]],
    *,
    kb_min_score: float,
    kb_min_rerank_score: float,
    topic_shift: bool = False,
) -> RetrievalConfidence:
    """
    统一检索置信度评估（路由与引用门控共用）。

    - confident: rerank 明确达标，可 KB + 可挂引用
    - gray: 有候选但分数不确定；须 LLM 复核才能 KB，默认不挂引用
    - weak: 无 rerank 或分数过低；走通用，不挂引用
    """
    rerank = best_rerank_score(contexts_meta)
    rerank_floor = effective_rerank_floor(kb_min_rerank_score, topic_shift=topic_shift)

    if rerank is not None:
        if rerank < rerank_floor:
            return "weak"
        if rerank >= RERANK_CONFIDENT_MIN:
            if topic_shift and rerank < 0.38:
                return "gray"
            return "confident"
        return "gray"

    # 无 rerank：hybrid 仅为候选集内相对排序，不能视为命中
    if best_hybrid_score(contexts_meta) >= float(kb_min_score):
        return "gray"
    return "weak"


def answer_indicates_kb_miss(text: str) -> bool:
    """Heuristic: assistant admitted KB materials cannot answer the question."""
    t = (text or "").strip()
    if not t:
        return True
    for pat in KB_MISS_PATTERNS:
        if pat.search(t):
            return True
    hits = sum(1 for m in KB_MISS_MARKERS if m in t)
    if hits >= 2:
        return True
    if hits == 1 and len(t) < 220:
        return True
    return False


def should_attach_citations(
    *,
    answer_mode: str,
    answer: str,
    contexts_meta: list[dict[str, Any]],
    kb_min_score: float = 0.55,
    kb_min_rerank_score: float = 0.0,
    topic_shift: bool = False,
) -> bool:
    """Only cite when KB mode, answer is substantive, and retrieval is confidently relevant."""
    if answer_mode != "kb":
        return False
    if not contexts_meta:
        return False
    if answer_indicates_kb_miss(answer):
        return False
    return (
        assess_retrieval_confidence(
            contexts_meta,
            kb_min_score=kb_min_score,
            kb_min_rerank_score=kb_min_rerank_score,
            topic_shift=topic_shift,
        )
        == "confident"
    )


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
    model = model_for_task(llm_runtime, task="routing")

    body = "\n".join(f"[{i + 1}] {c[:800]}" for i, c in enumerate(contexts[:3]))
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "你是检索相关性判断员。仅输出 YES 或 NO。\n"
                    "YES=参考资料中有能直接、完整回答用户所问这一点的明确事实或规定；"
                    "用户问的是「某文档/制度/产品中的具体内容」且资料里确有答案。\n"
                    "NO=以下任一情况：资料仅主题/关键词相近；资料描述的是某一具体内部产品/方案，"
                    "而用户问的是开放性的行业方法、设计原则、通用框架或常识/闲聊；"
                    "或主要靠模型常识/公开知识才能答好。"
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
    topic_shift: bool = False,
    kb_llm_judge_always: bool = False,
) -> bool:
    """
    True → 走知识库回答；False → 走通用知识。
    仅依据检索置信度 + 可选 LLM 复核，不解析用户问法句式。
    """
    if not has_usable_context(contexts, contexts_meta):
        return False

    confidence = assess_retrieval_confidence(
        contexts_meta,
        kb_min_score=kb_min_score,
        kb_min_rerank_score=kb_min_rerank_score,
        topic_shift=topic_shift,
    )
    if confidence == "weak":
        return False
    if confidence == "confident":
        if kb_llm_judge_always and kb_llm_judge and llm_runtime:
            return _llm_kb_relevant(question, contexts, llm_runtime)
        return True

    # gray: 无 rerank 或 rerank 处于中间带 — 必须 LLM 确认，否则 fail-closed 走通用
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
    topic_shift: bool = False,
    kb_llm_judge_always: bool = False,
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
        topic_shift=topic_shift,
        kb_llm_judge_always=kb_llm_judge_always,
    ):
        return "kb"
    return "general"

"""Offline KB health probe: auto-generated questions + retrieve + optional LLM judge."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import settings


def _eval_dir() -> Path:
    return Path(settings.golden_jsonl_path).parent


def _probe_questions(*, limit: int = 40) -> list[str]:
    from retrieval.domain_lexicon import load_domain_lexicon

    questions: list[str] = []
    seen: set[str] = set()

    def add(q: str) -> None:
        q = (q or "").strip()
        if len(q) < 4 or q in seen:
            return
        seen.add(q)
        questions.append(q)

    lex = load_domain_lexicon()
    terms = list((lex.get("terms") or {}).keys())
    for term in sorted(terms, key=lambda t: (-len(t), t))[: max(10, limit // 2)]:
        if len(term) >= 2:
            add(f"什么是{term}")
            add(f"{term}有哪些要求")

    try:
        from indexing.document_registry import get_document_registry

        reg = get_document_registry()
        for doc in (reg._docs or {}).values():  # noqa: SLF001
            src = str(doc.get("canonical_source") or "")
            stem = Path(src).stem if src else ""
            if stem and len(stem) >= 2:
                add(f"介绍一下{stem}")
    except Exception:
        pass

    seeds = [
        "超脑阅读训练要求是什么",
        "五者天赋是什么",
        "扫描速记注意事项",
        "感知力训练要点",
    ]
    for s in seeds:
        add(s)

    return questions[:limit]


def run_kb_health_probe(
    *,
    limit: int = 30,
    use_llm_judge: bool = False,
    llm_runtime: dict[str, Any] | None = None,
    user_department: str = "general",
) -> dict[str, Any]:
    from retrieval.hybrid_searcher import hybrid_search

    probes = _probe_questions(limit=limit)
    if not probes:
        return {"ok": False, "error": "no probe questions (empty lexicon and registry)", "probes": 0}

    hits = 0
    llm_ok = 0
    misses: list[dict[str, str]] = []

    for q in probes:
        try:
            _rewritten, parents = hybrid_search(q, user_department=user_department, top_k=5)
            ctx = [str(p.get("text") or "") for p in (parents or [])]
            meta = list(parents or [])
        except Exception as exc:
            misses.append({"question": q, "reason": f"search_error:{exc}"})
            continue
        if not ctx:
            misses.append({"question": q, "reason": "no_context"})
            continue
        hits += 1
        if use_llm_judge and llm_runtime:
            try:
                from agent.kb_judge import should_use_knowledge_base

                ok = should_use_knowledge_base(
                    q,
                    ctx,
                    meta,
                    kb_min_score=0.55,
                    kb_min_rerank_score=0.12,
                    kb_llm_judge=True,
                    llm_runtime=llm_runtime,
                )
                if ok:
                    llm_ok += 1
                else:
                    misses.append({"question": q, "reason": "llm_judge_weak"})
            except Exception:
                pass

    total = len(probes)
    report: dict[str, Any] = {
        "ok": True,
        "probes": total,
        "retrieve_hit_rate": round(hits / total, 4) if total else 0.0,
        "misses": misses[:20],
        "miss_count": len(misses),
    }
    if use_llm_judge:
        report["llm_relevant_rate"] = round(llm_ok / total, 4) if total else 0.0
    return report


def write_kb_health_report(report: dict[str, Any], path: Path | None = None) -> Path:
    dest = path or (_eval_dir() / "kb_health_report.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return dest

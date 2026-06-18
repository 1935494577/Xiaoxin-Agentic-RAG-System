"""LLM entity/relation extraction at ingest time."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from config import settings
from graph.store import delete_edges_by_source, upsert_triple

logger = logging.getLogger(__name__)

_EXTRACT_SYSTEM = (
    "从给定文本中提取实体关系三元组。仅输出 JSON 数组，每项含 "
    'subject, relation, object, subject_type, object_type, confidence(0-1)。'
    "若无明确关系则输出 []。不要编造。"
)


def _parse_triples(raw: str) -> list[dict[str, Any]]:
    text = (raw or "").strip()
    if not text:
        return []
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        text = match.group(0)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [x for x in data if isinstance(x, dict)]


def extract_triples_from_text(
    text: str,
    *,
    llm_runtime: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    api_key = (llm_runtime or {}).get("llm_api_key") or settings.openai_api_key
    if not api_key or not (text or "").strip():
        return []
    try:
        from openai import OpenAI

        from agent.llm_routing import model_for_task

        rt = llm_runtime or {}
        api_base = (rt.get("llm_api_base") or "").strip() or settings.openai_api_base
        headers = rt.get("llm_extra_headers")
        client_kw: dict[str, Any] = {"api_key": api_key, "base_url": api_base}
        if isinstance(headers, dict) and headers:
            client_kw["default_headers"] = headers
        client = OpenAI(**client_kw)
        model = model_for_task(rt, task="routing")
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _EXTRACT_SYSTEM},
                {"role": "user", "content": text[:3000]},
            ],
            temperature=0.0,
            max_tokens=800,
        )
        return _parse_triples(resp.choices[0].message.content or "")
    except Exception:
        logger.warning("graph extract failed", exc_info=True)
        return []


def extract_graph_from_parents(
    parents: list[dict[str, Any]],
    *,
    source: str,
    department: str,
    llm_runtime: dict[str, Any] | None = None,
    max_parents: int | None = None,
) -> int:
    """Extract and store triples from parent chunks. Returns edge count."""
    cap = max_parents if max_parents is not None else int(settings.graph_extraction_max_parents)
    delete_edges_by_source(source)
    count = 0
    for row in parents[:cap]:
        text = str(row.get("text") or row.get("content") or "")
        parent_id = str(row.get("parent_id") or "")
        if not text.strip():
            continue
        for triple in extract_triples_from_text(text, llm_runtime=llm_runtime):
            try:
                conf = float(triple.get("confidence", 0.8))
            except (TypeError, ValueError):
                conf = 0.8
            upsert_triple(
                src_name=str(triple.get("subject") or ""),
                relation=str(triple.get("relation") or "相关"),
                dst_name=str(triple.get("object") or ""),
                source=source,
                department=department,
                parent_id=parent_id,
                confidence=conf,
                src_type=str(triple.get("subject_type") or ""),
                dst_type=str(triple.get("object_type") or ""),
            )
            count += 1
    return count

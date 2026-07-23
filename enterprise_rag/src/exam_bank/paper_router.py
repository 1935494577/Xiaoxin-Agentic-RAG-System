"""LLM-first paper routing agent; rules as fallback."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from exam_bank.section_detect import detect_sections_rules
from exam_bank.subject_catalog import (
    normalize_qtype,
    qtype_label,
    qtypes_for_subject,
    resolve_stage,
)

_log = logging.getLogger(__name__)

_SYSTEM = """你是试卷结构路由助手。根据用户给出的试卷文本片段，识别科目、学段/年级、各大题题型与估计题量。
只输出 JSON，不要 Markdown。字段：
{
  "subject": "数学|语文|英语|物理|化学|生物|历史|地理|政治|其他",
  "grade": "如初二/高一，未知则空字符串",
  "stage": "primary|junior|senior",
  "sections": [
    {"heading": "原标题", "qtype": "choice|fill|short|calc|experiment|cloze|reading|writing|listening|material|other|custom:名称", "approx_count": 0, "start_hint": "可选定位词"}
  ],
  "confidence": 0.0
}
题型须贴近中国大陆中小学真实卷面：数学多为 choice/fill/short(解答题)；勿把计算/证明拆成与三大题并列除非原文如此。
"""


def _extract_json(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _normalize_llm_sections(raw_sections: Any, *, subject: str, grade: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(raw_sections, list):
        return out
    allowed = set(qtypes_for_subject(subject, grade=grade))
    for i, row in enumerate(raw_sections):
        if not isinstance(row, dict):
            continue
        heading = str(row.get("heading") or "").strip()
        qt = normalize_qtype(str(row.get("qtype") or heading or "other"))
        # keep custom even if not in template
        if qt not in allowed and not qt.startswith("custom:") and qt != "other":
            # still accept builtin ids from model
            pass
        approx = row.get("approx_count")
        try:
            approx_n = max(0, int(approx)) if approx is not None else 0
        except (TypeError, ValueError):
            approx_n = 0
        out.append(
            {
                "heading": heading or qtype_label(qt),
                "qtype": qt,
                "label": qtype_label(qt),
                "approx_count": approx_n,
                "start_line": i + 1,
            }
        )
    return out


def route_paper_with_llm(
    text: str,
    *,
    subject_hint: str = "",
    grade_hint: str = "",
    timeout_sec: float = 45.0,
) -> dict[str, Any] | None:
    """Call project chat/routing model (.env deepseek-v4-flash by default)."""
    from exam_bank.llm_client import build_openai_client

    blob = (text or "").strip()
    if not blob:
        return None
    blob = blob[:12000]
    client, rt = build_openai_client(timeout_sec=timeout_sec)
    if client is None:
        _log.warning("exam paper LLM skipped: no API key (source=%s)", rt.get("source"))
        return None
    model = str(rt.get("model") or "").strip()
    if not model:
        return None

    user = {
        "hint_subject": subject_hint or "",
        "hint_grade": grade_hint or "",
        "paper_text": blob,
    }
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            temperature=0.0,
            max_tokens=1200,
        )
        content = (resp.choices[0].message.content or "").strip()
        parsed = _extract_json(content)
        if not parsed:
            return None
        subject = str(parsed.get("subject") or subject_hint or "其他").strip() or "其他"
        grade = str(parsed.get("grade") or grade_hint or "").strip()
        stage = resolve_stage(grade, str(parsed.get("stage") or ""))
        sections = _normalize_llm_sections(parsed.get("sections"), subject=subject, grade=grade)
        conf = parsed.get("confidence")
        try:
            confidence = float(conf) if conf is not None else 0.7
        except (TypeError, ValueError):
            confidence = 0.7
        return {
            "subject": subject,
            "grade": grade,
            "stage": stage,
            "sections": sections,
            "confidence": confidence,
            "router": "llm",
            "model": model,
            "llm_source": rt.get("source"),
            "api_base": rt.get("llm_api_base"),
        }
    except Exception:
        _log.exception("exam paper LLM route failed model=%s base=%s", model, rt.get("llm_api_base"))
        return None


def analyze_paper(
    text: str,
    *,
    subject: str = "",
    grade: str = "",
    use_llm: bool = True,
) -> dict[str, Any]:
    """
    Agent-style paper analysis: LLM route first, merge/fallback to rule sections.
    """
    note = ""
    llm_result: dict[str, Any] | None = None
    if use_llm:
        llm_result = route_paper_with_llm(text, subject_hint=subject, grade_hint=grade)

    rule_sections = detect_sections_rules(text, subject=subject or (llm_result or {}).get("subject") or "")

    if llm_result and llm_result.get("sections"):
        subject_out = str(llm_result.get("subject") or subject or "其他")
        grade_out = str(llm_result.get("grade") or grade or "")
        stage_out = str(llm_result.get("stage") or resolve_stage(grade_out))
        sections = list(llm_result["sections"])
        # fill gaps from rules (headings LLM missed)
        have = {str(s.get("heading") or "") for s in sections}
        for rs in rule_sections:
            if rs.get("heading") not in have:
                sections.append(rs)
        router = "llm"
        confidence = float(llm_result.get("confidence") or 0.7)
        suggested_qtypes = qtypes_for_subject(subject_out, grade=grade_out, stage=stage_out)
        return {
            "subject": subject_out,
            "grade": grade_out,
            "stage": stage_out,
            "sections": sections,
            "suggested_qtypes": [{"id": q, "label": qtype_label(q)} for q in suggested_qtypes],
            "router": router,
            "confidence": confidence,
            "note": note,
            "model": llm_result.get("model") or "",
            "llm_source": llm_result.get("llm_source") or "",
            "api_base": llm_result.get("api_base") or "",
        }

    # rules-only path
    subject_out = subject or "其他"
    grade_out = grade or ""
    stage_out = resolve_stage(grade_out)
    if use_llm and llm_result is None:
        note = "llm_unavailable_fallback_rules"
    elif use_llm and llm_result is not None and not llm_result.get("sections"):
        note = "llm_empty_sections_fallback_rules"
        subject_out = str(llm_result.get("subject") or subject_out)
        grade_out = str(llm_result.get("grade") or grade_out)
        stage_out = str(llm_result.get("stage") or stage_out)
    suggested_qtypes = qtypes_for_subject(subject_out, grade=grade_out, stage=stage_out)
    return {
        "subject": subject_out,
        "grade": grade_out,
        "stage": stage_out,
        "sections": rule_sections,
        "suggested_qtypes": [{"id": q, "label": qtype_label(q)} for q in suggested_qtypes],
        "router": "rules",
        "confidence": 0.4 if rule_sections else 0.1,
        "note": note,
        "model": "",
        "llm_source": "",
        "api_base": "",
    }

"""LLM-assisted explanation and subjective grading for chat exam flow."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

_log = logging.getLogger(__name__)

_EXPLAIN_SYSTEM = """你是中学/高考数学等学科的讲题助教。根据题干、选项、参考答案与用户作答，给出清晰的分步讲解。
只输出一个 JSON 对象，字段：
- explanation: string，分步讲解（可用 $...$ 写公式，勿泄露与题无关内容）
- is_correct: boolean | null（客观题可判则给出；开放作答题无法严格判分时为 null）
- score_hint: string，一句话评价用户作答（如「基本正确，漏写单位」）
- key_points: string[]，2–5 个要点
不要输出 JSON 以外的文字。"""


def _extract_json(text: str) -> dict[str, Any] | None:
    s = (text or "").strip()
    if not s:
        return None
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", s)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def explain_question_with_llm(
    question: dict[str, Any],
    *,
    user_answer: str = "",
    timeout_sec: float = 60.0,
) -> dict[str, Any]:
    """Generate step-by-step explanation; optionally judge subjective answers."""
    from exam_bank.llm_client import build_openai_client

    q = dict(question or {})
    if not q.get("id") and not q.get("stem"):
        return {"ok": False, "error": "invalid_question", "message": "题目无效"}

    client, rt = build_openai_client(timeout_sec=timeout_sec)
    if client is None:
        return {
            "ok": False,
            "error": "llm_not_configured",
            "message": "未配置 API Key / 模型，无法讲解",
        }
    model = str(rt.get("chat_model") or rt.get("model") or "").strip()
    if not model:
        return {
            "ok": False,
            "error": "llm_not_configured",
            "message": "未配置 Chat 模型，无法讲解",
        }

    payload = {
        "qtype": q.get("qtype") or "",
        "stem": q.get("stem") or "",
        "options": q.get("options") or [],
        "reference_answer": q.get("answer") or "",
        "reference_analysis": q.get("analysis") or "",
        "user_answer": (user_answer or "").strip(),
        "subject": q.get("subject") or "",
        "grade": q.get("grade") or "",
    }
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": _EXPLAIN_SYSTEM},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        "temperature": 0.2,
        "max_tokens": 2048,
    }
    try:
        try:
            kwargs["response_format"] = {"type": "json_object"}
            resp = client.chat.completions.create(**kwargs)
        except Exception:
            kwargs.pop("response_format", None)
            resp = client.chat.completions.create(**kwargs)
        content = (resp.choices[0].message.content or "").strip()
        parsed = _extract_json(content)
        if not parsed:
            return {
                "ok": False,
                "error": "llm_json_parse_failed",
                "message": "大模型未返回合法讲解",
                "raw_preview": content[:240],
                "model": model,
            }
        explanation = str(parsed.get("explanation") or "").strip()
        if not explanation:
            return {
                "ok": False,
                "error": "llm_empty_explanation",
                "message": "大模型未生成讲解内容",
                "model": model,
            }
        is_correct = parsed.get("is_correct")
        if is_correct is not None and not isinstance(is_correct, bool):
            is_correct = None
        key_points = parsed.get("key_points")
        if not isinstance(key_points, list):
            key_points = []
        return {
            "ok": True,
            "question_id": str(q.get("id") or ""),
            "explanation": explanation,
            "is_correct": is_correct,
            "score_hint": str(parsed.get("score_hint") or "").strip(),
            "key_points": [str(x).strip() for x in key_points if str(x).strip()],
            "reference_answer": q.get("answer") or "",
            "reference_analysis": q.get("analysis") or "",
            "model": model,
        }
    except Exception:
        _log.exception("explain_question_with_llm failed")
        return {
            "ok": False,
            "error": "llm_api_error",
            "message": "调用大模型讲解失败",
            "model": model,
        }


def explain_question_by_id(
    question_id: str,
    *,
    user_answer: str = "",
    reader_user_id: str | None = None,
) -> dict[str, Any]:
    """Load question from store, enforce ACL, then explain."""
    from exam_bank import store

    qid = (question_id or "").strip()
    if not qid:
        return {"ok": False, "error": "missing_question_id", "message": "请提供题目 ID"}
    q = store.get_question(qid)
    if not q:
        return {"ok": False, "error": "question_not_found", "message": "题目不存在"}
    cid = str(q.get("collection_id") or "").strip()
    if cid and not store.reader_can_access_collection(cid, reader_user_id):
        return {"ok": False, "error": "forbidden", "message": "无权访问该题目"}
    out = explain_question_with_llm(q, user_answer=user_answer)
    if out.get("ok"):
        out["qtype"] = q.get("qtype") or ""
    return out

"""LLM + rule-based feedback triage."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from config import settings
from feedback_loop.issue_types import ISSUE_TYPES, issue_type_label  # noqa: F401 — re-export
from feedback_loop.store import get_feedback, list_feedback, save_triage_result
from openai import OpenAI

_log = logging.getLogger(__name__)

DEFAULT_TRIAGE_PROMPT = """你是企业 RAG 反馈分析员。根据用户反馈、问题、答案摘要、检索上下文与用户纠错，输出**唯一** JSON 对象（不要 markdown）：
{
  "issue_type": "retrieval_miss|hallucination|stale_doc|prompt|tone|ok",
  "severity": "low|medium|high",
  "human_review_required": true,
  "summary": "一句话原因",
  "suggested_actions": [{"action": "add_to_golden|propose_reingest|apply_config_patch", "confidence": 0.0-1.0, "detail": "可选说明"}]
}
规则：rating=1 通常 issue_type=ok；context_count=0 优先 retrieval_miss；用户纠错提到过期/废止倾向 stale_doc；答案与资料明显矛盾为 hallucination。"""


def _prompt_path() -> Path:
    return Path(settings.data_feedback_path).parent / "feedback_triage_prompt.txt"


def load_triage_prompt() -> str:
    path = _prompt_path()
    if path.is_file():
        text = path.read_text(encoding="utf-8").strip()
        if text:
            return text
    return DEFAULT_TRIAGE_PROMPT


def _normalize_issue_type(raw: str | None) -> str:
    val = (raw or "").strip().lower()
    if val in ISSUE_TYPES:
        return val
    return "prompt"


def _normalize_severity(raw: str | None) -> str:
    val = (raw or "").strip().lower()
    if val in ("low", "medium", "high"):
        return val
    return "medium"


def rule_based_triage(row: dict[str, Any]) -> dict[str, Any]:
    rating = int(row.get("rating") or 0)
    if rating >= 1:
        return {
            "issue_type": "ok",
            "severity": "low",
            "human_review_required": False,
            "summary": "用户标记有帮助",
            "suggested_actions": [],
            "mode": "rule",
        }

    correction = str(row.get("correction") or "").lower()
    ctx = row.get("context_count")
    try:
        ctx_n = int(ctx) if ctx is not None else None
    except (TypeError, ValueError):
        ctx_n = None

    if ctx_n == 0:
        return {
            "issue_type": "retrieval_miss",
            "severity": "high",
            "human_review_required": True,
            "summary": "检索上下文为空，可能漏召回或阈值过高",
            "suggested_actions": [
                {"action": "propose_reingest", "confidence": 0.55, "detail": "确认知识库是否覆盖该主题"},
                {
                    "action": "apply_config_patch",
                    "confidence": 0.6,
                    "detail": "采纳后自动略降 kb_min_score 以扩大召回",
                },
            ],
            "mode": "rule",
        }

    if any(k in correction for k in ("过期", "废止", "旧版", "2020", "已更新", "不再适用")):
        return {
            "issue_type": "stale_doc",
            "severity": "high",
            "human_review_required": True,
            "summary": "用户指出文档或答案可能过时",
            "suggested_actions": [
                {"action": "propose_reingest", "confidence": 0.7, "detail": "检查 source 并触发重入库"}
            ],
            "mode": "rule",
        }

    if correction.strip():
        return {
            "issue_type": "hallucination",
            "severity": "medium",
            "human_review_required": True,
            "summary": "用户提供了纠错说明，答案可能与资料不符",
            "suggested_actions": [
                {"action": "add_to_golden", "confidence": 0.75, "detail": "将问答对加入评测集"}
            ],
            "mode": "rule",
        }

    if ctx_n is not None and ctx_n > 0:
        return {
            "issue_type": "prompt",
            "severity": "medium",
            "human_review_required": True,
            "summary": "有检索上下文但用户仍不满意，可能生成或提示词问题",
            "suggested_actions": [
                {"action": "apply_config_patch", "confidence": 0.4, "detail": "人工审阅提示词与 verifier 配置"}
            ],
            "mode": "rule",
        }

    return {
        "issue_type": "tone",
        "severity": "low",
        "human_review_required": False,
        "summary": "负反馈但缺少结构化信号，建议人工扫一眼",
        "suggested_actions": [],
        "mode": "rule",
    }


def _extract_json(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def llm_triage(
    row: dict[str, Any],
    *,
    api_key: str | None = None,
    api_base: str | None = None,
    chat_model: str | None = None,
    timeout_sec: float = 30.0,
) -> dict[str, Any] | None:
    key = (api_key or settings.openai_api_key or "").strip()
    if not key:
        return None
    base = (api_base or settings.openai_api_base or "").strip()
    model = (chat_model or settings.openai_chat_model or "").strip()

    user_blob = {
        "rating": row.get("rating"),
        "question": row.get("question"),
        "answer_preview": row.get("answer_preview"),
        "answer_mode": row.get("answer_mode"),
        "correction": row.get("correction"),
        "context_count": row.get("context_count"),
        "sources": row.get("sources"),
    }
    client = OpenAI(api_key=key, base_url=base, timeout=timeout_sec)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": load_triage_prompt()},
            {"role": "user", "content": json.dumps(user_blob, ensure_ascii=False)},
        ],
        temperature=0.0,
        max_tokens=512,
    )
    content = (resp.choices[0].message.content or "").strip()
    parsed = _extract_json(content)
    if not parsed:
        return None
    actions = parsed.get("suggested_actions")
    if not isinstance(actions, list):
        actions = []
    return {
        "issue_type": _normalize_issue_type(str(parsed.get("issue_type") or "")),
        "severity": _normalize_severity(str(parsed.get("severity") or "")),
        "human_review_required": bool(parsed.get("human_review_required", True)),
        "summary": str(parsed.get("summary") or "").strip()[:500] or issue_type_label(
            _normalize_issue_type(str(parsed.get("issue_type") or ""))
        ),
        "suggested_actions": actions[:5],
        "mode": "llm",
    }


def apply_triage_result(feedback_id: str, result: dict[str, Any]) -> dict[str, Any] | None:
    return save_triage_result(
        feedback_id,
        issue_type=str(result.get("issue_type") or "prompt"),
        severity=str(result.get("severity") or "medium"),
        human_review_required=bool(result.get("human_review_required", True)),
        summary=str(result.get("summary") or ""),
        suggested_actions=list(result.get("suggested_actions") or []),
        triage_mode=str(result.get("mode") or "rule"),
        triage_error=None,
    )


def run_triage_one(
    feedback_id: str,
    *,
    use_llm: bool = True,
    api_key: str | None = None,
    api_base: str | None = None,
    chat_model: str | None = None,
) -> dict[str, Any] | None:
    row = get_feedback(feedback_id)
    if not row:
        return None
    if str(row.get("status") or "pending") != "pending":
        return row

    result: dict[str, Any] | None = None
    err: str | None = None
    if use_llm:
        try:
            result = llm_triage(row, api_key=api_key, api_base=api_base, chat_model=chat_model)
        except Exception as e:
            err = str(e)[:500]
            _log.warning("llm triage failed for %s: %s", feedback_id, err)

    if result is None:
        result = rule_based_triage(row)
        if err:
            result["triage_fallback_reason"] = err

    return apply_triage_result(feedback_id, result)


def run_triage_batch(
    *,
    limit: int | None = None,
    use_llm: bool = True,
    rating: int | None = None,
) -> dict[str, int]:
    batch = limit if limit is not None else settings.feedback_triage_batch_size
    batch = max(1, min(int(batch), 50))
    rows, _ = list_feedback(status="pending", since_days=None, limit=batch, offset=0, rating=rating)
    processed = 0
    failed = 0
    for row in rows:
        fid = str(row.get("id") or "")
        if not fid:
            continue
        try:
            out = run_triage_one(fid, use_llm=use_llm)
            if out and str(out.get("status")) == "triaged":
                processed += 1
            else:
                failed += 1
        except Exception:
            failed += 1
            _log.exception("triage failed for %s", fid)
    return {"processed": processed, "failed": failed, "queued": len(rows)}

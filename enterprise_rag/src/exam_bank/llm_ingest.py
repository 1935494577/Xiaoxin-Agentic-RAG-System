"""LLM-first exam paper item extraction for ingest."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from exam_bank.subject_catalog import normalize_qtype, qtype_label, qtypes_for_subject

_log = logging.getLogger(__name__)

_SYSTEM = """你是中小学试卷结构化入库助手。根据用户提供的「试卷元信息」与「试卷全文」，只抽取正式试题，供题库入库。

硬性要求：
1. 只输出 JSON，不要 Markdown 围栏。
2. 丢弃非试题内容：注意事项、姓名/准考证栏、装订线、评分说明、页眉页脚、纯大题标题行（若无题干）。
3. 按卷面真实大题归类题型 qtype（须贴近该科目常见题型）：choice|fill|short|calc|experiment|cloze|reading|writing|listening|material|other。
4. 每题尽量带 knowledge_tags（知识点短标签，2～5 个中文词）。
5. 每题尽量带 chapter（教材章节/单元名，如「集合与常用逻辑用语」；不确定可空字符串）。
6. 每题给出 difficulty：整数 1～5（1–2 简单，3 中等，4–5 困难），按高考/中考常见难度估计。
7. 若原文含答案/解析（如【答案】【解析】或文末答案），写入 answer、analysis；没有则 answer/analysis 置空字符串。
8. is_question=false 的条目不要出现在 items 里（直接省略）。
9. question_no 用卷面题号字符串（如 "1"、"12"）；选项保留 "A. …" 原文行。

输出 schema：
{
  "answers_embedded": true或false,
  "items": [
    {
      "question_no": "1",
      "qtype": "choice",
      "stem": "题干",
      "options": ["A. …", "B. …"],
      "answer": "",
      "analysis": "",
      "knowledge_tags": ["集合"],
      "chapter": "集合与常用逻辑用语",
      "difficulty": 3,
      "is_question": true
    }
  ]
}
answers_embedded：若多数正式题已能从原文得到答案则为 true，否则 false。
"""


def _extract_json(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json|JSON)?\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw)
        raw = raw.strip()
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


def normalize_llm_items(
    raw_items: Any,
    *,
    subject: str = "",
    grade: str = "",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Filter non-questions; normalize fields. Returns (items, meta)."""
    allowed = set(qtypes_for_subject(subject, grade=grade)) if subject else set()
    items: list[dict[str, Any]] = []
    skipped = 0
    with_answer = 0
    if not isinstance(raw_items, list):
        return [], {"answers_embedded": False, "skipped_non_questions": 0}

    for row in raw_items:
        if not isinstance(row, dict):
            skipped += 1
            continue
        if row.get("is_question") is False:
            skipped += 1
            continue
        stem = str(row.get("stem") or "").strip()
        if not stem:
            skipped += 1
            continue
        # Drop obvious instruction lines mistaken as stems
        if re.match(r"^(注意事项|答题前|考生须知|装订线)", stem):
            skipped += 1
            continue
        qt = normalize_qtype(str(row.get("qtype") or "other"))
        if allowed and qt not in allowed and not str(qt).startswith("custom:") and qt != "other":
            # keep model choice if it's a builtin id
            pass
        opts = row.get("options") or []
        if not isinstance(opts, list):
            opts = []
        options = [str(o).strip() for o in opts if str(o).strip()]
        if options and (qt == "other" or str(qt).startswith("custom:")):
            qt = "choice"
        tags_raw = row.get("knowledge_tags") or []
        if not isinstance(tags_raw, list):
            tags_raw = []
        tags = [str(t).strip() for t in tags_raw if str(t).strip()][:8]
        chapter = str(row.get("chapter") or "").strip()[:80]
        answer = str(row.get("answer") or "").strip()
        analysis = str(row.get("analysis") or "").strip()
        if answer:
            with_answer += 1
        try:
            diff = int(row.get("difficulty") if row.get("difficulty") is not None else 3)
        except (TypeError, ValueError):
            diff = 3
        diff = max(1, min(5, diff))
        items.append(
            {
                "question_no": str(row.get("question_no") or "").strip(),
                "qtype": qt,
                "label": qtype_label(qt),
                "stem": stem,
                "options": options,
                "answer": answer,
                "analysis": analysis,
                "knowledge_tags": tags,
                "chapter": chapter,
                "difficulty": diff,
                "selected": True,
            }
        )

    answers_embedded = bool(items) and (with_answer / max(len(items), 1) >= 0.5)
    return items, {
        "answers_embedded": answers_embedded,
        "skipped_non_questions": skipped,
        "with_answer": with_answer,
    }


def _paper_label(*, subject: str, grade: str, region: str, stage: str) -> str:
    parts = [p for p in [subject.strip(), grade.strip(), region.strip()] if p]
    if stage and stage not in ("", "junior", "senior", "primary"):
        parts.insert(0, stage)
    return "·".join(parts) if parts else "未命名"


def extract_items_with_llm(
    text: str,
    *,
    subject: str = "",
    grade: str = "",
    region: str = "",
    stage: str = "",
    timeout_sec: float = 180.0,
) -> dict[str, Any] | None:
    """Call chat model to extract structured question items.

    Returns a dict always when the client is configured (even on API/JSON failure),
    so the UI can show the real reason. Returns None only when no API key/model.
    """
    from exam_bank.llm_client import build_openai_client
    from exam_bank.subject_catalog import resolve_stage

    blob = (text or "").strip()
    if not blob:
        return None
    # Keep room for system + response; chunk large papers
    chunk_size = 12000
    chunks = [blob[i : i + chunk_size] for i in range(0, len(blob), chunk_size)] or [blob]

    client, rt = build_openai_client(timeout_sec=timeout_sec)
    if client is None:
        _log.warning("exam ingest LLM skipped: no API key (source=%s)", rt.get("source"))
        return None
    # Prefer Chat 同款主模型；routing 小模型容易在长 JSON 上失败/截断
    model = str(rt.get("chat_model") or rt.get("model") or "").strip()
    if not model:
        return None

    st = resolve_stage(grade, stage)
    label = _paper_label(subject=subject, grade=grade, region=region, stage=st)
    qtype_hint = qtypes_for_subject(subject or "数学", grade=grade, stage=st)

    all_items: list[dict[str, Any]] = []
    skipped_total = 0
    last_raw_preview = ""
    json_failures = 0
    try:
        for ci, chunk in enumerate(chunks):
            user_payload = {
                "instruction": (
                    f"请将该（{label}）试卷拆成正式试题入库草案。"
                    f"科目题型参考：{qtype_hint}。"
                    f"这是全文第 {ci + 1}/{len(chunks)} 段；只输出本段中的正式题。"
                ),
                "meta": {
                    "subject": subject,
                    "grade": grade,
                    "region": region,
                    "stage": st,
                },
                "paper_text": chunk,
            }
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": [
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
                ],
                "temperature": 0.0,
                "max_tokens": 8192,
            }
            # DeepSeek / OpenAI-compatible JSON mode (best-effort)
            try:
                kwargs["response_format"] = {"type": "json_object"}
                resp = client.chat.completions.create(**kwargs)
            except Exception:
                kwargs.pop("response_format", None)
                resp = client.chat.completions.create(**kwargs)
            content = (resp.choices[0].message.content or "").strip()
            last_raw_preview = content[:240]
            parsed = _extract_json(content)
            if not parsed:
                json_failures += 1
                _log.warning(
                    "exam ingest LLM empty JSON chunk=%s preview=%s",
                    ci,
                    last_raw_preview[:120],
                )
                continue
            part_items, part_meta = normalize_llm_items(
                parsed.get("items"), subject=subject, grade=grade
            )
            all_items.extend(part_items)
            skipped_total += int(part_meta.get("skipped_non_questions") or 0)

        # de-dupe by question_no+stem prefix
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for it in all_items:
            key = f"{it.get('question_no')}|{(it.get('stem') or '')[:40]}"
            if key in seen:
                continue
            seen.add(key)
            unique.append(it)

        with_ans = sum(1 for it in unique if (it.get("answer") or "").strip())
        answers_embedded = bool(unique) and (with_ans / max(len(unique), 1) >= 0.5)
        base = {
            "items": unique,
            "item_count": len(unique),
            "answers_embedded": answers_embedded,
            "skipped_non_questions": skipped_total,
            "model": model,
            "llm_source": rt.get("source"),
            "api_base": rt.get("llm_api_base"),
            "paper_label": label,
        }
        if unique:
            return {**base, "router": "llm_items"}
        msg = (
            "大模型已响应，但未能解析出正式试题（JSON 为空或被截断）。"
            "请缩短粘贴篇幅后重试，或换一份文本更清晰的试卷。"
        )
        if json_failures:
            msg += f" 有 {json_failures} 段响应无法解析为 JSON。"
        return {
            **base,
            "router": "llm_failed",
            "error": "llm_empty_items",
            "message": msg,
            "raw_preview": last_raw_preview,
        }
    except Exception as e:
        _log.exception("exam ingest LLM failed model=%s", model)
        err = str(e).strip() or e.__class__.__name__
        return {
            "items": [],
            "item_count": 0,
            "answers_embedded": False,
            "skipped_non_questions": 0,
            "router": "llm_failed",
            "error": "llm_api_error",
            "message": f"大模型调用失败：{err}（模型 {model}）。Chat 能用仍可能因超时/限流/该模型不支持长 JSON 导致拆题失败。",
            "model": model,
            "llm_source": rt.get("source"),
            "api_base": rt.get("llm_api_base"),
            "paper_label": label,
        }

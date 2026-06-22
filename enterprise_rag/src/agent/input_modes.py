"""Input mode resolution: question vs temp document vs doc task."""

from __future__ import annotations

import re
from typing import Literal

InputMode = Literal["question", "temp_document", "doc_task"]
DocTaskType = Literal["summary", "compare", "extract", "annotate"]

_SUMMARY_RE = re.compile(r"总结|摘要|概括|全文概述|梳理要点")
_COMPARE_RE = re.compile(r"对比|比较.*与|差异在哪|有何不同")
_EXTRACT_RE = re.compile(r"提取|列出.*所有|结构化输出|表格化")
_ANNOTATE_RE = re.compile(r"批注|解读|点评|逐段说明")


def normalize_input_mode(raw: str | None) -> InputMode | None:
    key = (raw or "").strip().lower()
    if key in ("question", "temp_document", "doc_task"):
        return key  # type: ignore[return-value]
    return None


def normalize_doc_task_type(raw: str | None) -> DocTaskType | None:
    key = (raw or "").strip().lower()
    if key in ("summary", "compare", "extract", "annotate"):
        return key  # type: ignore[return-value]
    return None


def infer_doc_task_from_message(message: str) -> DocTaskType | None:
    """Infer document-task intent from natural language (no UI required)."""
    q = (message or "").strip()
    if len(q) < 4:
        return None
    if _COMPARE_RE.search(q):
        return "compare"
    if _EXTRACT_RE.search(q):
        return "extract"
    if _ANNOTATE_RE.search(q):
        return "annotate"
    if _SUMMARY_RE.search(q):
        return "summary"
    return None


def resolve_input_mode(
    *,
    input_mode: str | None,
    doc_task_type: str | None,
    temp_document_id: str | None,
    message: str,
) -> tuple[InputMode, DocTaskType | None]:
    explicit = normalize_input_mode(input_mode)
    task = normalize_doc_task_type(doc_task_type)

    if explicit == "doc_task":
        return "doc_task", task or infer_doc_task_from_message(message) or "summary"
    if explicit == "temp_document":
        return "temp_document", task
    if explicit == "question":
        return "question", task

    if temp_document_id and str(temp_document_id).strip():
        return "temp_document", task
    if task is not None:
        return "doc_task", task

    inferred = infer_doc_task_from_message(message)
    if inferred:
        return "doc_task", inferred

    return "question", None

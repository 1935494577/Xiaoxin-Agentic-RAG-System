"""Tests for automatic input mode inference from user messages."""

from __future__ import annotations

from agent.input_modes import infer_doc_task_from_message, resolve_input_mode


def test_infer_summary_from_message():
    assert infer_doc_task_from_message("请总结这份制度文档的要点") == "summary"


def test_infer_compare_from_message():
    assert infer_doc_task_from_message("对比方案A与方案B的差异") == "compare"


def test_resolve_defaults_to_question():
    mode, task = resolve_input_mode(
        input_mode=None,
        doc_task_type=None,
        temp_document_id=None,
        message="产品保修期多久？",
    )
    assert mode == "question"
    assert task is None


def test_resolve_infers_doc_task_without_ui():
    mode, task = resolve_input_mode(
        input_mode=None,
        doc_task_type=None,
        temp_document_id=None,
        message="帮我提取文档里所有联系方式",
    )
    assert mode == "doc_task"
    assert task == "extract"

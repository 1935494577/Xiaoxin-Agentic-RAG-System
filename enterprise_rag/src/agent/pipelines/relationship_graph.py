"""Deterministic relationship-graph answers (KB-only safe, no general fallback)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from agent.tools.builtins.relationship_graph import (
    clear_relationship_graph_context,
    set_relationship_graph_context,
    show_relationship_graph,
)
from graph.summary import build_org_graph_markdown
from graph.viz import is_generic_org_graph_query, parse_graph_viz_from_tool_output

__all__ = ["stream_relationship_graph_turn"]


def _compose_answer(viz: dict[str, Any] | None, tool_output: str) -> str:
    if viz and viz.get("edges"):
        return build_org_graph_markdown(viz)
    if tool_output and "未找到" not in tool_output and "暂无" not in tool_output:
        return tool_output.strip()
    return (
        "知识库中暂未找到可展示的组织关系数据。"
        "请先在「数据入库」上传组织关系文档（如组织图、汇报关系说明），"
        "或确认文档已成功解析后再试。"
    )


def stream_relationship_graph_turn(
    state: dict[str, Any],
    *,
    trace: Any,
    quiet: bool,
    emit: Any,
) -> Iterator[str]:
    """Run show_relationship_graph and emit graph_viz + done (skip general LLM)."""
    question = str(state.get("relationship_graph_query") or state.get("question") or "")
    dept = str(state.get("user_department") or "技术部")

    if not quiet:
        yield emit(
            {
                "type": "status",
                "phase": "graph",
                "rag_architecture": "graph",
                "trace_id": trace.trace_id,
            }
        )

    set_relationship_graph_context(user_department=dept, max_hops=4 if is_generic_org_graph_query(question) else 3)
    try:
        with trace.span("graph", "tool", inputs={"question": question}):
            tool_output = show_relationship_graph(query=question)
    finally:
        clear_relationship_graph_context()

    viz = parse_graph_viz_from_tool_output(tool_output)
    answer = _compose_answer(viz, tool_output)
    tool_trace = [
        {
            "tool": "show_relationship_graph",
            "arguments": {"query": question},
            "output": tool_output,
            "ok": bool(viz and viz.get("edges")),
        }
    ]

    if viz and viz.get("nodes"):
        yield emit({"type": "graph_viz", "graph": viz})

    for ch in answer:
        yield emit({"type": "token", "content": ch})

    done_payload = {
        "type": "done",
        "answer": answer,
        "rewritten_query": state.get("retrieval_query") or question,
        "sources": [],
        "source_refs": [],
        "answer_mode": "kb",
        "rag_architecture": "graph",
        "input_mode": state.get("input_mode") or "question",
        "verified": True,
        "trace_id": trace.trace_id,
        "tool_trace": tool_trace,
        "graph_viz": viz if viz and viz.get("nodes") else None,
        "topic_shift": bool(state.get("topic_shift")),
        "retrieval_query": state.get("retrieval_query") or question,
        "routing_model": state.get("routing_model"),
        "chat_routing_tier": (state.get("memory_config") or {}).get("chat_routing_tier") or "balanced",
        "condense_used_llm": bool((state.get("turn_meta") or {}).get("condense_used_llm")),
    }
    trace.finish(
        {
            "answer_mode": "kb",
            "rag_architecture": "graph",
            "verified": True,
            "source_count": 0,
            "graph_fast_path": True,
            "trace_id": trace.trace_id,
        }
    )
    yield emit(done_payload)

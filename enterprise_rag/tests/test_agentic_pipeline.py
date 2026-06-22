"""Tests for Agentic RAG pipeline (mocked tool loop)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_stream_agentic_collects_kb_hits():
    from agent.pipelines.agentic import stream_agentic_answer
    from agent.tools.builtins.kb_search import set_kb_search_context

    set_kb_search_context(
        user_department="技术部",
        hits=[
            {
                "parent_id": "p1",
                "text": "销量分析资料",
                "source": "report.pdf",
                "hybrid_score": 0.8,
                "department": "技术部",
                "permission_label": "internal",
                "tags": [],
            }
        ],
    )

    state: dict = {"question": "分析销量下降原因", "memory_config": {}}
    parts: list[str] = []
    trace: list = []

    def emit(payload):
        return f"data: {payload}\n"

    def replay(tokens):
        for t in tokens:
            yield emit({"type": "token", "content": t})

    with patch("agent.pipelines.agentic.run_tool_loop", return_value=("结论：销量下降因渠道变化。", [])):
        with patch("agent.pipelines.agentic.load_tools_config", return_value={"chat_tools_enabled": True, "tools": {}}):
            with patch("agent.pipelines.agentic.enabled_tool_ids", return_value=set()):
                with patch(
                    "agent.tools.builtins.kb_search.get_kb_hits",
                    return_value=[
                        {
                            "parent_id": "p1",
                            "text": "销量分析资料",
                            "source": "report.pdf",
                            "hybrid_score": 0.8,
                            "department": "技术部",
                            "permission_label": "internal",
                            "tags": [],
                        }
                    ],
                ):
                    list(
                        stream_agentic_answer(
                            state=state,
                            client=MagicMock(),
                            model="test",
                            temperature=0.2,
                            max_tokens=100,
                            history=[],
                            prompt_slots=None,
                            parts=parts,
                            tool_trace_out=trace,
                            emit_event=emit,
                            replay_tokens=replay,
                            emit_tokens=False,
                            max_turns=3,
                        )
                    )

    assert parts[0].startswith("结论")
    assert len(state.get("_agentic_hits") or []) == 1

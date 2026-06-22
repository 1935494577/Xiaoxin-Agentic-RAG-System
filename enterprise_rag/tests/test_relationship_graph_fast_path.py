"""Relationship graph fast path in stream chat (KB-only, no general fallback)."""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture
def graph_db(tmp_path, monkeypatch):
    db = tmp_path / "rg_fast.db"
    monkeypatch.setattr("graph.store.settings.graph_db_path", db)
    monkeypatch.setattr("graph.store._conn", None)
    yield db
    monkeypatch.setattr("graph.store._conn", None)


def test_is_relationship_graph_question_expanded():
    from agent.tools.runtime.routing import is_relationship_graph_question

    assert is_relationship_graph_question("展示科技公司关系图")
    assert is_relationship_graph_question("展示一下公司关系")
    assert is_relationship_graph_question("给我看一下深层公司关系")
    assert is_relationship_graph_question("张振国的上下级")
    assert not is_relationship_graph_question("今天天气怎么样")


def test_viz_followup_with_history():
    from agent.tools.runtime.routing import (
        resolve_relationship_graph_query,
        should_use_relationship_graph_fast_path,
    )

    history = [
        {"role": "user", "content": "展示一下公司关系"},
        {"role": "assistant", "content": "公司核心管理团队…"},
    ]
    assert should_use_relationship_graph_fast_path("展示图", history)
    merged = resolve_relationship_graph_query("展示图", history)
    assert "公司关系" in merged


def test_company_relation_uses_fast_path(graph_db):
    from agent.pipelines.relationship_graph import stream_relationship_graph_turn
    from agent.stream_chat import stream_rag_chat
    from agent.tools.runtime.routing import should_use_relationship_graph_fast_path
    from graph.org_chart import import_org_chart_if_detected

    assert should_use_relationship_graph_fast_path("展示一下公司关系")

    text = "林峰（CTO）：向 张振国 汇报\n张振国（CEO）：管辖 林峰"
    import_org_chart_if_detected(text, source="深层公司关系.txt", department="技术部")

    with patch(
        "agent.stream_chat.stream_relationship_graph_turn",
        wraps=stream_relationship_graph_turn,
    ) as mocked:
        list(
            stream_rag_chat(
                {
                    "question": "展示一下公司关系",
                    "user_id": "u1",
                    "user_department": "技术部",
                    "hybrid_expert_mode": False,
                    "memory_config": {
                        "general_fallback_enabled": False,
                        "kb_post_stream_fallback": False,
                    },
                    "llm_api_key": "sk-test",
                    "quiet_routing": True,
                }
            )
        )
        assert mocked.called


def test_stream_relationship_graph_turn_emits_viz(graph_db):
    from agent.pipelines.relationship_graph import stream_relationship_graph_turn
    from graph.org_chart import import_org_chart_if_detected

    text = """
张振国（CEO）：管辖 林峰
林峰（CTO）：向 CEO 汇报；负责技术路线
"""
    import_org_chart_if_detected(text, source="科技公司关系图测试.txt", department="技术部")

    events: list[dict] = []

    class FakeTrace:
        trace_id = "t1"

        def span(self, *args, **kwargs):
            class Ctx:
                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

            return Ctx()

        def finish(self, *args, **kwargs):
            pass

    def emit(payload):
        events.append(payload)
        return f"data: {payload}\n\n"

    state = {
        "question": "展示科技公司关系图",
        "user_department": "技术部",
        "memory_config": {},
    }
    list(
        stream_relationship_graph_turn(
            state,
            trace=FakeTrace(),
            quiet=True,
            emit=emit,
        )
    )

    types = [e["type"] for e in events]
    assert "graph_viz" in types
    done = next(e for e in events if e["type"] == "done")
    assert done["answer_mode"] == "kb"
    assert done.get("graph_viz")
    assert len(done["graph_viz"]["edges"]) >= 1
    assert "苹果" not in done["answer"].lower() and "google" not in done["answer"].lower()


def test_stream_chat_uses_graph_fast_path_when_kb_only(graph_db):
    from agent.pipelines.relationship_graph import stream_relationship_graph_turn
    from agent.stream_chat import stream_rag_chat
    from graph.org_chart import import_org_chart_if_detected

    text = "林峰（CTO）：向 张振国 汇报\n张振国（CEO）：管辖 林峰"
    import_org_chart_if_detected(text, source="科技公司关系图测试.txt", department="技术部")

    chunks: list[str] = []
    with patch(
        "agent.stream_chat.stream_relationship_graph_turn",
        wraps=stream_relationship_graph_turn,
    ) as mocked:
        for line in stream_rag_chat(
            {
                "question": "展示科技公司关系图",
                "user_id": "u1",
                "user_department": "技术部",
                "hybrid_expert_mode": False,
                "memory_config": {
                    "general_fallback_enabled": False,
                    "kb_post_stream_fallback": False,
                },
                "llm_api_key": "sk-test",
                "quiet_routing": True,
            }
        ):
            chunks.append(line)
        assert mocked.called

    import json

    payloads = [json.loads(c.removeprefix("data: ").strip()) for c in chunks if c.startswith("data:")]
    done = next(p for p in payloads if p.get("type") == "done")
    assert done["answer_mode"] == "kb"
    assert done.get("graph_viz")


def test_viz_followup_stream_uses_fast_path(graph_db):
    from agent.pipelines.relationship_graph import stream_relationship_graph_turn
    from agent.stream_chat import stream_rag_chat
    from graph.org_chart import import_org_chart_if_detected

    text = "林峰（CTO）：向 张振国 汇报\n张振国（CEO）：管辖 林峰"
    import_org_chart_if_detected(text, source="深层公司关系.txt", department="技术部")

    history = [
        {"role": "user", "content": "展示一下公司关系"},
        {"role": "assistant", "content": "（文本摘要）"},
    ]
    with patch(
        "agent.stream_chat.stream_relationship_graph_turn",
        wraps=stream_relationship_graph_turn,
    ) as mocked:
        list(
            stream_rag_chat(
                {
                    "question": "展示图",
                    "user_id": "u1",
                    "user_department": "技术部",
                    "history": history,
                    "hybrid_expert_mode": False,
                    "memory_config": {"general_fallback_enabled": False},
                    "llm_api_key": "sk-test",
                    "quiet_routing": True,
                }
            )
        )
        assert mocked.called
        call_state = mocked.call_args[0][0]
        assert "公司关系" in call_state.get("relationship_graph_query", "")

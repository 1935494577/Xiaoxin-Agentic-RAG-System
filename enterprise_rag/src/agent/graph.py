from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from agent.nodes import (
    AgentState,
    answer_node,
    citer_node,
    retrieve_node,
    route_after_router,
    route_after_verifier,
    router_node,
    verifier_node,
)

try:
    from langgraph.graph import START
except ImportError:
    START = None  # type: ignore[misc, assignment]


def build_rag_graph():
    g = StateGraph(AgentState)
    g.add_node("router", router_node)
    g.add_node("retrieve", retrieve_node)
    # 节点名不可与 AgentState 字段重名（新版 LangGraph 会报错）
    g.add_node("draft", answer_node)
    g.add_node("verifier", verifier_node)
    g.add_node("citer", citer_node)
    if START is not None:
        g.add_edge(START, "router")
    else:
        g.set_entry_point("router")
    g.add_conditional_edges("router", route_after_router, {"retrieve": "retrieve", "reject": END})
    g.add_edge("retrieve", "draft")
    g.add_edge("draft", "verifier")
    g.add_conditional_edges(
        "verifier",
        route_after_verifier,
        {"pass": "citer", "retry": "draft", "reject": END},
    )
    g.add_edge("citer", END)
    return g.compile()


create_agent_graph = build_rag_graph

_app = None


def get_agent_app():
    global _app
    if _app is None:
        _app = build_rag_graph()
    return _app


def run_agent(
    question: str,
    user_id: str,
    user_department: str,
    allowed_sources: list[str] | None = None,
    llm_runtime: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
    memory_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    app = get_agent_app()
    init: AgentState = {
        "question": question,
        "user_id": user_id,
        "user_department": user_department,
        "allowed_sources": allowed_sources,
        "retry_count": 0,
        "history": history or [],
        "memory_config": memory_config or {},
    }
    if llm_runtime:
        init.update(llm_runtime)
    return dict(app.invoke(init))

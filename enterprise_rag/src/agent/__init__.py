"""Agent package — lazy exports to avoid importing LangGraph on submodule load."""

from __future__ import annotations

from typing import Any

__all__ = ["build_rag_graph", "create_agent_graph", "get_agent_app", "run_agent"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from agent.graph import build_rag_graph, create_agent_graph, get_agent_app, run_agent

        return {
            "build_rag_graph": build_rag_graph,
            "create_agent_graph": create_agent_graph,
            "get_agent_app": get_agent_app,
            "run_agent": run_agent,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

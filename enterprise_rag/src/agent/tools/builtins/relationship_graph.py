"""LLM tool: query relationship graph and return viz payload for chat UI."""

from __future__ import annotations

from typing import Any

from graph.viz import build_graph_viz, format_graph_tool_output, resolve_center_from_query

_context: dict[str, Any] = {}


def set_relationship_graph_context(**kwargs: Any) -> None:
    _context.clear()
    _context.update(kwargs)


def clear_relationship_graph_context() -> None:
    _context.clear()


def show_relationship_graph(query: str, center_name: str | None = None, max_hops: int | None = None) -> str:
    """
    根据人物/实体名称展示关系图（上下级、协作等）。
    用户问组织关系、汇报线、人物关系图时调用。
    """
    q = (query or "").strip()
    center = (center_name or "").strip() or resolve_center_from_query(q)
    if not center:
        return "请提供要查看关系的人物或团队名称（center_name 或 query）。"
    hops = int(max_hops) if max_hops is not None else int(_context.get("max_hops") or 3)
    hops = max(1, min(hops, 4))
    dept = str(_context.get("user_department") or "") or "技术部"

    viz = build_graph_viz(center=center, department=dept or None, max_hops=hops, limit=80)

    if not viz.get("edges"):
        from graph.lazy_rebuild import try_rebuild_org_chart_from_disk

        rebuilt = try_rebuild_org_chart_from_disk(query=q, center=center, department=dept)
        if rebuilt:
            pc, ec, src = rebuilt
            viz = build_graph_viz(center=center, department=dept or None, max_hops=hops, limit=80)
            if not viz.get("edges") and ec > 0:
                # 部门过滤可能导致空图，再试不限部门
                viz = build_graph_viz(center=center, department=None, max_hops=hops, limit=80)

    if viz.get("nodes") and not viz.get("edges"):
        return (
            "图谱中暂无关系边数据（仅识别到中心人物）。"
            "请在「数据入库」重新上传组织关系文档，或调用 "
            "POST /ingest/rebuild-relationships?source=文件名 补建关系。"
        )

    return format_graph_tool_output(viz)

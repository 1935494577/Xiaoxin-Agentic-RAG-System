"""Deterministic markdown summary from graph viz payload."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

_EXEC_TITLE_HINTS = ("CEO", "CTO", "CFO", "COO", "战略顾问", "负责人", "总监", "经理")


def _node_rank(title: str) -> int:
    t = title or ""
    for i, hint in enumerate(_EXEC_TITLE_HINTS):
        if hint in t:
            return i
    return len(_EXEC_TITLE_HINTS)


def _label_map(nodes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(n.get("label") or ""): n for n in nodes if n.get("label")}


def _build_hierarchy(edges: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Manager -> direct reports via 汇报 / 管辖 (deduped, stable order)."""
    children: dict[str, list[str]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for e in edges:
        rel = str(e.get("label") or "")
        if rel not in ("汇报", "管辖", "虚线管辖", "虚线指导"):
            continue
        if rel == "汇报":
            child, parent = str(e.get("from_label") or ""), str(e.get("to_label") or "")
        else:
            parent, child = str(e.get("from_label") or ""), str(e.get("to_label") or "")
        if not child or not parent or child == parent:
            continue
        key = (parent, child)
        if key in seen:
            continue
        seen.add(key)
        children[parent].append(child)
    return children


def _find_roots(nodes: list[dict[str, Any]], edges: list[dict[str, Any]], center_label: str) -> list[str]:
    if center_label:
        return [center_label]
    has_manager: set[str] = set()
    all_names = {str(n.get("label") or "") for n in nodes}
    for e in edges:
        if str(e.get("label") or "") == "汇报":
            has_manager.add(str(e.get("from_label") or ""))
    roots = [n for n in all_names if n and n not in has_manager]
    roots.sort(key=lambda name: _node_rank(str(_label_map(nodes).get(name, {}).get("title") or "")))
    return roots[:4] if roots else sorted(all_names)[:1]


def _format_person_line(name: str, nodes_by_label: dict[str, dict[str, Any]], indent: int) -> list[str]:
    n = nodes_by_label.get(name) or {}
    title = str(n.get("title") or "").strip()
    bio = str(n.get("bio") or "").strip()
    prefix = "  " * indent + "- "
    head = f"{prefix}**{name}**"
    if title:
        head += f"（{title}）"
    if bio:
        head += f"：{bio.split(chr(10))[0][:100]}"
    return [head]


def _render_tree(
    name: str,
    *,
    children: dict[str, list[str]],
    nodes_by_label: dict[str, dict[str, Any]],
    indent: int,
    visited: set[str],
    max_depth: int = 4,
) -> list[str]:
    if name in visited or indent > max_depth:
        return []
    visited.add(name)
    lines = _format_person_line(name, nodes_by_label, indent)
    for child in children.get(name, []):
        lines.extend(
            _render_tree(
                child,
                children=children,
                nodes_by_label=nodes_by_label,
                indent=indent + 1,
                visited=visited,
                max_depth=max_depth,
            )
        )
    return lines


def build_org_graph_markdown(viz: dict[str, Any]) -> str:
    """Build structured org summary + collaboration table (no LLM)."""
    nodes = viz.get("nodes") or []
    edges = viz.get("edges") or []
    if not nodes:
        return "未找到可展示的组织关系数据。"

    nodes_by_label = _label_map(nodes)
    center_id = str(viz.get("center_id") or "")
    center_label = next(
        (str(n.get("label") or "") for n in nodes if str(n.get("id") or "") == center_id),
        "",
    )

    lines: list[str] = [
        "根据**知识库组织关系**整理如下（下方为可交互关系图，**点击节点**可查看职责与汇报关系）：",
        "",
        "### **组织架构概览**",
        "",
    ]

    children = _build_hierarchy(edges)
    roots = _find_roots(nodes, edges, center_label)
    visited: set[str] = set()
    for root in roots:
        lines.extend(
            _render_tree(
                root,
                children=children,
                nodes_by_label=nodes_by_label,
                indent=0,
                visited=visited,
            )
        )
        lines.append("")

    key_people = sorted(
        [n for n in nodes if n.get("title") and str(n.get("label") or "") not in visited],
        key=lambda n: (_node_rank(str(n.get("title") or "")), str(n.get("label") or "")),
    )[:8]
    if key_people:
        lines.extend(["### **其他关键岗位**", ""])
        for n in key_people:
            label = str(n.get("label") or "")
            lines.extend(_format_person_line(label, nodes_by_label, 0))
        lines.append("")

    collab = [e for e in edges if str(e.get("label") or "") == "协作"]
    if collab:
        lines.extend(["### **主要协作关系**", "", "| 协作方 A | 协作方 B |", "| --- | --- |"])
        seen: set[tuple[str, str]] = set()
        for e in collab[:16]:
            a, b = str(e.get("from_label") or ""), str(e.get("to_label") or "")
            key = tuple(sorted((a, b)))
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"| {a} | {b} |")
        lines.append("")

    focus = center_label or "组织"
    lines.append(
        f"> 关系图以 **{focus}** 为中心展开，共 **{len(nodes)}** 人、**{len(edges)}** 条关系。"
        "可拖拽节点、滚轮缩放；点击节点查看职责详情。"
    )
    return "\n".join(lines).strip()

"""Build chat-friendly graph visualization payloads from the knowledge graph."""

from __future__ import annotations

import json
import re
from typing import Any

from graph.store import expand_from_seeds, get_entity_profiles, list_entities_matching, list_sources_matching, pick_center_for_source

_GRAPH_VIZ_MARKER_START = "__GRAPH_VIZ_JSON__"
_GRAPH_VIZ_MARKER_END = "__END_GRAPH_VIZ__"


def _safe_id(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\u4e00-\u9fff]", "_", name)[:48] or "node"


def build_graph_viz(
    *,
    center: str,
    department: str | None = None,
    max_hops: int = 2,
    limit: int = 80,
) -> dict[str, Any]:
    """Return {center_id, nodes, edges, summary_lines} for UI rendering."""
    center = center.strip()
    seeds = [center] if center else []
    if not seeds:
        seeds = list_entities_matching(center, limit=1)
    if not seeds:
        return {"center_id": "", "nodes": [], "edges": [], "summary_lines": ["未找到相关人物或实体。"]}

    seed = seeds[0]
    edge_rows = expand_from_seeds([seed], department=department, max_hops=max_hops, limit=limit)
    profiles = get_entity_profiles(
        _collect_names(seed, edge_rows),
        department=department,
    )

    nodes_map: dict[str, dict[str, Any]] = {}
    for name, prof in profiles.items():
        nid = _safe_id(name)
        nodes_map[name] = {
            "id": nid,
            "label": name,
            "type": prof.get("entity_type") or "entity",
            "title": prof.get("title") or "",
            "department": prof.get("department") or "",
            "bio": (prof.get("bio") or "")[:120],
        }

    edges: list[dict[str, str]] = []
    seen_edges: set[tuple[str, str, str]] = set()
    summary_lines: list[str] = []

    for row in edge_rows:
        src = str(row.get("src_name") or "")
        dst = str(row.get("dst_name") or "")
        rel = str(row.get("relation") or "相关")
        if not src or not dst:
            continue
        for name in (src, dst):
            if name not in nodes_map:
                nodes_map[name] = {
                    "id": _safe_id(name),
                    "label": name,
                    "type": "entity",
                    "title": "",
                    "department": str(row.get("department") or ""),
                    "bio": "",
                }
        key = (src, rel, dst)
        if key in seen_edges:
            continue
        seen_edges.add(key)
        edges.append(
            {
                "from": nodes_map[src]["id"],
                "to": nodes_map[dst]["id"],
                "from_label": src,
                "to_label": dst,
                "label": rel,
            }
        )
        summary_lines.append(f"{src} —{rel}→ {dst}")

    center_id = nodes_map.get(seed, {}).get("id") or _safe_id(seed)
    if seed not in nodes_map:
        nodes_map[seed] = {
            "id": center_id,
            "label": seed,
            "type": "person",
            "title": "",
            "department": department or "",
            "bio": "",
        }

    return {
        "center_id": center_id,
        "nodes": list(nodes_map.values()),
        "edges": edges,
        "summary_lines": summary_lines[:12],
    }


def _collect_names(seed: str, edge_rows: list[dict[str, Any]]) -> list[str]:
    names = {seed}
    for row in edge_rows:
        names.add(str(row.get("src_name") or ""))
        names.add(str(row.get("dst_name") or ""))
    return [n for n in names if n.strip()]


def resolve_center_from_query(query: str) -> str:
    q = (query or "").strip()
    if not q:
        return ""
    for pat in (
        r"[「『\"]([^」』\"]+)[」』\"]",
        r"(?:围绕|关于|以|查看|展示|显示)([\u4e00-\u9fffA-Za-z0-9·]{2,16})的",
        r"([\u4e00-\u9fffA-Za-z0-9·]{2,8})的(?:上下级|工作|组织|汇报|人物)?关系",
    ):
        m = re.search(pat, q)
        if m:
            return m.group(1).strip()
    # 按入库文件名/来源关键词匹配（如「科技公司关系图」）
    for token in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,12}", q):
        if token in ("关系图", "组织图", "架构图", "展示", "显示", "一下"):
            continue
        sources = list_sources_matching(token, limit=3)
        if sources:
            center = pick_center_for_source(sources[0])
            if center:
                return center
        names = list_entities_matching(token, limit=3)
        if names:
            return names[0]
    if re.search(r"关系图|组织图|架构图|汇报关系|上下级", q):
        sources = list_sources_matching("关系", limit=5)
        for src in sources:
            center = pick_center_for_source(src)
            if center:
                return center
    candidates = list_entities_matching(q[:8], limit=3)
    return candidates[0] if candidates else ""


def format_graph_tool_output(viz: dict[str, Any]) -> str:
    """Human-readable + machine-parseable block for chat UI."""
    if not viz.get("nodes"):
        return "未找到可展示的关系数据。请确认已通过「关系入库」导入人物与关系。"
    lines = ["已生成关系图数据："]
    for s in viz.get("summary_lines") or []:
        lines.append(f"· {s}")
    payload = json.dumps(viz, ensure_ascii=False, separators=(",", ":"))
    lines.append(_GRAPH_VIZ_MARKER_START)
    lines.append(payload)
    lines.append(_GRAPH_VIZ_MARKER_END)
    return "\n".join(lines)


def parse_graph_viz_from_tool_output(text: str) -> dict[str, Any] | None:
    if _GRAPH_VIZ_MARKER_START not in text:
        return None
    try:
        start = text.index(_GRAPH_VIZ_MARKER_START) + len(_GRAPH_VIZ_MARKER_START)
        end = text.index(_GRAPH_VIZ_MARKER_END, start)
        raw = text[start:end].strip()
        data = json.loads(raw)
        if isinstance(data, dict) and data.get("nodes") is not None:
            return data
    except (ValueError, json.JSONDecodeError):
        return None
    return None

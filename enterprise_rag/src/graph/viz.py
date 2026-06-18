"""Build chat-friendly graph visualization payloads from the knowledge graph."""

from __future__ import annotations

import json
import re
from typing import Any

from graph.store import (
    entity_exists,
    expand_from_seeds,
    get_entity_profiles,
    list_entities_matching,
    list_relationship_sources,
    list_sources_matching,
    pick_center_for_source,
    pick_default_org_center,
    primary_source_for_entity,
)

_GRAPH_VIZ_MARKER_START = "__GRAPH_VIZ_JSON__"
_GRAPH_VIZ_MARKER_END = "__END_GRAPH_VIZ__"


def _safe_id(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\u4e00-\u9fff]", "_", name)[:48] or "node"


def _synthesize_bio(name: str, prof: dict[str, Any], edge_rows: list[dict[str, Any]]) -> str:
    """Fallback when ingest doc has no explicit 负责… block."""
    existing = str(prof.get("bio") or "").strip()
    if existing:
        return existing
    parts: list[str] = []
    title = str(prof.get("title") or "").strip()
    dept = str(prof.get("department") or "").strip()
    if title:
        parts.append(title)
    if dept:
        parts.append(dept)
    reports: list[str] = []
    manages: list[str] = []
    dotted: list[str] = []
    for row in edge_rows:
        src = str(row.get("src_name") or "")
        dst = str(row.get("dst_name") or "")
        rel = str(row.get("relation") or "")
        if src != name:
            continue
        if rel == "汇报":
            reports.append(dst)
        elif rel in ("管辖", "虚线管辖", "虚线指导"):
            manages.append(dst)
        elif rel == "虚线汇报":
            dotted.append(dst)
    if reports:
        parts.append(f"向{'、'.join(dict.fromkeys(reports))}汇报")
    if dotted:
        parts.append(f"虚线汇报{'、'.join(dict.fromkeys(dotted))}")
    if manages:
        parts.append(f"管辖/指导：{'、'.join(dict.fromkeys(manages[:8]))}")
    return "；".join(parts)


def build_graph_viz(
    *,
    center: str,
    department: str | None = None,
    max_hops: int = 2,
    limit: int = 80,
    source: str | None = None,
) -> dict[str, Any]:
    """Return {center_id, nodes, edges, summary_lines} for UI rendering."""
    center = center.strip()
    seeds = [center] if center else []
    if not seeds:
        seeds = list_entities_matching(center, limit=1)
    if not seeds:
        return {"center_id": "", "nodes": [], "edges": [], "summary_lines": ["未找到相关人物或实体。"]}

    seed = seeds[0]
    doc_source = (source or "").strip() or primary_source_for_entity(seed)
    edge_rows = expand_from_seeds(
        [seed], department=department, max_hops=max_hops, limit=limit, source=doc_source or None
    )
    profiles = get_entity_profiles(
        _collect_names(seed, edge_rows),
        department=department,
        source=doc_source or None,
    )
    for name in _collect_names(seed, edge_rows):
        if name not in profiles or not profiles[name].get("title"):
            fallback = get_entity_profiles([name], department=department, source=None)
            if fallback.get(name, {}).get("title") or fallback.get(name, {}).get("bio"):
                profiles[name] = fallback[name]

    nodes_map: dict[str, dict[str, Any]] = {}
    for name, prof in profiles.items():
        nid = _safe_id(name)
        bio = _synthesize_bio(name, prof, edge_rows) or (prof.get("bio") or "")
        nodes_map[name] = {
            "id": nid,
            "label": name,
            "type": prof.get("entity_type") or "entity",
            "title": prof.get("title") or "",
            "department": prof.get("department") or "",
            "bio": str(bio)[:2000],
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
                prof = profiles.get(name) or {}
                bio = _synthesize_bio(name, prof, edge_rows)
                nodes_map[name] = {
                    "id": _safe_id(name),
                    "label": name,
                    "type": "entity",
                    "title": prof.get("title") or "",
                    "department": str(row.get("department") or prof.get("department") or ""),
                    "bio": str(bio)[:2000],
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
        prof = profiles.get(seed) or {}
        bio = _synthesize_bio(seed, prof, edge_rows)
        nodes_map[seed] = {
            "id": center_id,
            "label": seed,
            "type": "person",
            "title": prof.get("title") or "",
            "department": department or prof.get("department") or "",
            "bio": str(bio)[:2000],
        }

    return {
        "center_id": center_id,
        "nodes": list(nodes_map.values()),
        "edges": edges,
        "summary_lines": summary_lines[:12],
        "source": doc_source,
    }


def resolve_graph_source(query: str, center: str, *, department: str | None = None) -> str:
    """Pick one relationship document source for viz (avoid mixing multiple imports)."""
    q = (query or "").strip()
    for token in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,12}", q):
        if token in _SKIP_TOKENS:
            continue
        srcs = list_sources_matching(token, limit=1)
        if srcs:
            return srcs[0]
    if is_generic_org_graph_query(q):
        srcs = list_relationship_sources(limit=1)
        if srcs:
            return srcs[0]
    return primary_source_for_entity(center) or ""


def _collect_names(seed: str, edge_rows: list[dict[str, Any]]) -> list[str]:
    names = {seed}
    for row in edge_rows:
        names.add(str(row.get("src_name") or ""))
        names.add(str(row.get("dst_name") or ""))
    return [n for n in names if n.strip()]


_SKIP_TOKENS = frozenset(
    {
        "关系图",
        "组织图",
        "架构图",
        "展示",
        "显示",
        "一下",
        "给我",
        "查看",
        "所有",
        "整个",
        "公司关系",
        "关系网",
        "组织关系",
        "员工关系",
        "人员关系",
    }
)
_GENERIC_ORG_RE = re.compile(
    r"公司关系|关系网|所有关系|组织关系|员工关系|人员关系|管理团队|汇报线|组织架构|"
    r"公司架构|深层公司|展示.{0,6}关系|关系.{0,4}图",
    re.IGNORECASE,
)


def is_generic_org_graph_query(query: str) -> bool:
    q = (query or "").strip()
    return bool(q and _GENERIC_ORG_RE.search(q))


def _is_garbage_center(name: str) -> bool:
    s = (name or "").strip()
    if not s or len(s) < 2:
        return True
    if s.startswith(("一下", "给我", "所有", "整个", "展示", "显示")):
        return True
    if re.fullmatch(r"[公司科技关系组织架构展示显示一下所有整个网络]+", s):
        return True
    if any(x in s for x in ("公司关系", "关系网", "科技公司", "一下科技")):
        return True
    return False


def _accept_center(name: str, *, department: str | None = None) -> str:
    n = (name or "").strip()
    if _is_garbage_center(n):
        return ""
    if entity_exists(n):
        return n
    matches = list_entities_matching(n, limit=1)
    return matches[0] if matches else ""


def _center_from_sources(query: str, *, department: str | None = None) -> str:
    q = (query or "").strip()
    for token in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,12}", q):
        if token in _SKIP_TOKENS:
            continue
        for src in list_sources_matching(token, limit=3):
            center = pick_center_for_source(src, department=department)
            if center:
                return center
    if re.search(r"关系|组织|架构", q):
        for src in list_sources_matching("关系", limit=5):
            center = pick_center_for_source(src, department=department)
            if center:
                return center
    return pick_default_org_center(department=department)


def resolve_center_from_query(query: str, *, department: str | None = None) -> str:
    q = (query or "").strip()
    if not q:
        return pick_default_org_center(department=department)

    if is_generic_org_graph_query(q):
        center = _center_from_sources(q, department=department)
        if center:
            return center

    for pat in (
        r"[「『\"]([^」』\"]+)[」』\"]",
        r"([\u4e00-\u9fffA-Za-z0-9·]{2,8})的(?:上下级|工作|组织|汇报|人物)?关系",
    ):
        m = re.search(pat, q)
        if m:
            center = _accept_center(m.group(1).strip(), department=department)
            if center:
                return center

    m = re.search(
        r"(?:围绕|关于|以|查看|展示|显示)(?:一下|给我)?([\u4e00-\u9fffA-Za-z0-9·]{2,12})的",
        q,
    )
    if m:
        center = _accept_center(m.group(1).strip(), department=department)
        if center:
            return center

    for token in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,12}", q):
        if token in _SKIP_TOKENS:
            continue
        for src in list_sources_matching(token, limit=3):
            center = pick_center_for_source(src, department=department)
            if center:
                return center
        names = list_entities_matching(token, limit=3)
        for name in names:
            if not _is_garbage_center(name):
                return name

    if re.search(r"关系图|组织图|架构图|汇报关系|上下级", q):
        center = _center_from_sources(q, department=department)
        if center:
            return center

    for src in list_relationship_sources(limit=3):
        center = pick_center_for_source(src, department=department)
        if center:
            return center

    candidates = list_entities_matching(q[:8], limit=3)
    for name in candidates:
        if not _is_garbage_center(name):
            return name
    return ""


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

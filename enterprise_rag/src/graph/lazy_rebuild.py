"""Rebuild org-chart graph from already-ingested text files on disk."""

from __future__ import annotations

import re
from pathlib import Path

from config import settings
from graph.org_chart import import_org_chart_if_detected
from graph.viz import is_generic_org_graph_query


def _candidate_files() -> list[Path]:
    seen: set[str] = set()
    out: list[Path] = []
    for root in (settings.data_processed_dir, settings.data_raw_dir):
        if not root.is_dir():
            continue
        for path in sorted(root.iterdir()):
            if not path.is_file():
                continue
            key = path.name.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(path)
    return out


def _query_tokens(query: str, center: str = "") -> list[str]:
    skip = {"关系图", "组织图", "架构图", "展示", "显示", "一下", "员工", "关系", "公司", "科技"}
    tokens: list[str] = []
    for t in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,16}", query or ""):
        if t not in skip and t not in tokens:
            tokens.append(t)
    if center.strip() and center.strip() not in tokens:
        tokens.append(center.strip())
    return tokens


def try_rebuild_org_chart_from_disk(
    *,
    query: str = "",
    center: str = "",
    department: str,
) -> tuple[int, int, str] | None:
    """
    If graph edges missing, parse org-chart text from ingested files on disk.
    Returns (people_count, edge_count, source) or None.
    """
    tokens = _query_tokens(query, center)
    generic = is_generic_org_graph_query(query or "")
    best: tuple[int, int, str] | None = None

    for path in _candidate_files():
        name = path.name
        if not generic and tokens and not any(t in name for t in tokens):
            if "关系" not in name and "组织" not in name:
                continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if center and not generic and center not in text:
            if not re.search(r"关系图|组织|汇报|管辖", query or ""):
                continue
        counts = import_org_chart_if_detected(text, source=name, department=department)
        if not counts:
            continue
        pc, ec = counts
        if best is None or ec > best[1]:
            best = (pc, ec, name)

    return best

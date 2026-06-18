"""Deterministic org-chart parser for structured relationship ingest text."""

from __future__ import annotations

import re
from typing import Any

from graph.store import import_relationship_bundle

_PERSON_LINE = re.compile(
    r"^(.+?)（([^）]+)）\s*[：:]\s*(.+)$",
    re.MULTILINE,
)
_REPORT_RE = re.compile(r"向\s*(.+?)\s*汇报")
_MANAGE_RE = re.compile(r"管辖\s*(.+?)(?:；|$)")
_SPLIT_TARGETS = re.compile(r"[、,，]")


def _looks_like_org_chart(text: str) -> bool:
    hits = 0
    for m in _PERSON_LINE.finditer(text or ""):
        rest = m.group(3)
        if "汇报" in rest or "管辖" in rest:
            hits += 1
        if hits >= 2:
            return True
    return False


def _build_indexes(
    rows: list[tuple[str, str, str]],
) -> tuple[list[dict[str, Any]], set[str], dict[str, str]]:
    people: list[dict[str, Any]] = []
    by_name: set[str] = set()
    by_title: dict[str, str] = {}
    for name, title, _rest in rows:
        people.append({"name": name, "title": title, "entity_type": "person"})
        by_name.add(name)
        by_title[title] = name
        upper = title.upper()
        for alias in ("CEO", "CTO", "CFO", "COO"):
            if alias in upper:
                by_title[alias] = name
    return people, by_name, by_title


def _resolve_target(raw: str, by_title: dict[str, str], by_name: set[str]) -> str:
    t = raw.strip().strip("；;")
    if not t:
        return ""
    if t in by_name:
        return t
    if t in by_title:
        return by_title[t]
    for title, name in by_title.items():
        if t in title or title in t:
            return name
    for name in by_name:
        if t in name or name in t:
            return name
    return t


def parse_org_chart_text(text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (people, relationships) from org-chart formatted text."""
    rows: list[tuple[str, str, str]] = []
    for m in _PERSON_LINE.finditer(text or ""):
        name = m.group(1).strip()
        title = m.group(2).strip()
        rest = m.group(3).strip()
        if name:
            rows.append((name, title, rest))

    people, by_name, by_title = _build_indexes(rows)
    relationships: list[dict[str, Any]] = []

    for name, _title, rest in rows:
        for rm in _REPORT_RE.finditer(rest):
            target = _resolve_target(rm.group(1), by_title, by_name)
            if target and target != name:
                relationships.append(
                    {"from_name": name, "relation": "汇报", "to_name": target, "confidence": 1.0}
                )

        mm = _MANAGE_RE.search(rest)
        if mm:
            for part in _SPLIT_TARGETS.split(mm.group(1)):
                target = _resolve_target(part.strip(), by_title, by_name)
                if target and target != name:
                    relationships.append(
                        {"from_name": name, "relation": "管辖", "to_name": target, "confidence": 1.0}
                    )

    return people, relationships


def import_org_chart_if_detected(
    text: str,
    *,
    source: str,
    department: str,
) -> tuple[int, int] | None:
    """Parse and import org chart when text matches; returns counts or None."""
    if not _looks_like_org_chart(text):
        return None
    people, relationships = parse_org_chart_text(text)
    if not people:
        return None
    return import_relationship_bundle(
        source=source,
        department=department,
        people=people,
        relationships=relationships,
    )

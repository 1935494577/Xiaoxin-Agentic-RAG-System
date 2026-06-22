"""Deterministic org-chart parser for structured relationship ingest text."""

from __future__ import annotations

import re
from typing import Any

from graph.store import import_relationship_bundle

_PERSON_LINE = re.compile(
    r"^(.+?)（([^）]+)）\s*[：:]\s*(.*)$",
    re.MULTILINE,
)
_SECTION_RE = re.compile(r"^【.+】\s*$")
_REPORT_RE = re.compile(r"向\s*(.+?)\s*汇报")
_DOTTED_REPORT_RE = re.compile(r"向\s*(.+?)\s*虚线汇报")
_REPORT_CLAUSE_RE = re.compile(r"向\s*[^；;（(]+?\s*汇报(?=[；;（(]|$)")
_DOTTED_REPORT_CLAUSE_RE = re.compile(r"向\s*[^；;（(]+?\s*虚线汇报(?=[；;）)]|$)")
_MANAGE_LINE_RE = re.compile(r"^(?:直接)?管辖[：:]\s*(.+)$")
_DOTTED_MANAGE_LINE_RE = re.compile(r"^虚线管辖[：:]\s*(.+)$")
_DOTTED_GUIDE_LINE_RE = re.compile(r"^虚线指导[：:]\s*(.+)$")
_COLLAB_LINE_RE = re.compile(r"^协作关系[：:]\s*(.+)$")
_BILATERAL_COLLAB_RE = re.compile(r"^(.+?)\s*↔\s*(.+?)：(.+)$")
_INLINE_MANAGE_RE = re.compile(r"(?:直接)?管辖\s*([^；;\n]+)")
_SPLIT_TARGETS = re.compile(r"[、,，]")
_HEADCOUNT_RE = re.compile(r"[×xX]\s*\d")


def _normalize_title(title: str) -> str:
    t = (title or "").strip()
    t = re.sub(r"[，,]?\s*新增\s*$", "", t)
    return t.strip()


def _clean_target_token(raw: str) -> str:
    t = (raw or "").strip().strip("；;")
    t = re.sub(r"（新增）", "", t)
    t = re.sub(r"\(新增\)", "", t)
    if "（" in t:
        t = t.split("（", 1)[0].strip()
    return t.strip()


def _is_headcount_placeholder(target: str) -> bool:
    t = _clean_target_token(target)
    if not t:
        return True
    if _HEADCOUNT_RE.search(t):
        return True
    if re.search(r"员×|工程师×|专家×|会计×|出纳×", t):
        return True
    return False


def _split_person_blocks(text: str) -> list[tuple[str, str, str]]:
    """Return [(name, title, block_body)] with continuation lines merged."""
    lines = (text or "").splitlines()
    blocks: list[tuple[str, str, str]] = []
    current: tuple[str, str, str] | None = None
    body_lines: list[str] = []

    def flush() -> None:
        nonlocal current, body_lines
        if not current:
            return
        name, title, first_rest = current
        parts = [p for p in [first_rest.strip(), *body_lines] if p]
        blocks.append((name, title, "\n".join(parts)))
        current = None
        body_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped or _SECTION_RE.match(stripped):
            continue
        if _BILATERAL_COLLAB_RE.match(stripped):
            flush()
            continue
        m = _PERSON_LINE.match(stripped)
        if m:
            flush()
            current = (m.group(1).strip(), m.group(2).strip(), m.group(3).strip())
        elif current is not None:
            body_lines.append(stripped)
    flush()
    return blocks


def _looks_like_org_chart(text: str) -> bool:
    hits = 0
    for _name, _title, body in _split_person_blocks(text or ""):
        if any(
            kw in body
            for kw in ("汇报", "管辖", "直接管辖", "虚线", "协作")
        ):
            hits += 1
        if hits >= 2:
            return True
    if len(_parse_bilateral_collabs(text or "")) >= 1 and hits >= 1:
        return True
    return False


def _build_indexes(
    blocks: list[tuple[str, str, str]],
) -> tuple[list[dict[str, Any]], set[str], dict[str, str]]:
    people: list[dict[str, Any]] = []
    by_name: set[str] = set()
    by_title: dict[str, str] = {}
    for name, title, body in blocks:
        norm_title = _normalize_title(title)
        people.append(
            {
                "name": name,
                "title": norm_title,
                "entity_type": "person",
                "bio": "",
            }
        )
        by_name.add(name)
        by_title[norm_title] = name
        if title != norm_title:
            by_title[title] = name
        upper = norm_title.upper()
        for alias in ("CEO", "CTO", "CFO", "COO"):
            if alias in upper:
                by_title[alias] = name
        for token in re.split(r"[、,/]", norm_title):
            token = token.strip()
            if token:
                by_title[token] = name
    return people, by_name, by_title


def _resolve_target(raw: str, by_title: dict[str, str], by_name: set[str]) -> str:
    t = _clean_target_token(raw)
    if not t or _is_headcount_placeholder(t):
        return ""
    if t in by_name:
        return t
    if t in by_title:
        return by_title[t]
    for title, name in by_title.items():
        if len(title) >= 2 and (t in title or title in t):
            return name
    for name in by_name:
        if t in name or name in t:
            return name
    return ""


def _split_target_list(raw: str) -> list[str]:
    cleaned = re.sub(r"（[^）]*）", "", raw)
    return [_clean_target_token(p) for p in _SPLIT_TARGETS.split(cleaned) if _clean_target_token(p)]


def _add_edge(
    relationships: list[dict[str, Any]],
    seen: set[tuple[str, str, str]],
    *,
    from_name: str,
    relation: str,
    to_name: str,
) -> None:
    if not from_name or not to_name or from_name == to_name:
        return
    key = (from_name, relation, to_name)
    if key in seen:
        return
    seen.add(key)
    relationships.append(
        {"from_name": from_name, "relation": relation, "to_name": to_name, "confidence": 1.0}
    )


def _extract_report_targets(fragment: str) -> list[tuple[str, str]]:
    """Return list of (relation_type, target_raw)."""
    out: list[tuple[str, str]] = []
    for m in _DOTTED_REPORT_RE.finditer(fragment):
        out.append(("虚线汇报", m.group(1).strip()))
    tmp = _DOTTED_REPORT_CLAUSE_RE.sub("", fragment)
    tmp = _REPORT_CLAUSE_RE.sub("", tmp)
    for m in _REPORT_RE.finditer(fragment):
        if "虚线汇报" in m.group(0):
            continue
        out.append(("汇报", m.group(1).strip()))
    return out


def _extract_bio_from_block(body: str) -> str:
    bio_parts: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _COLLAB_LINE_RE.match(stripped):
            bio_parts.append(stripped)
            continue
        if _MANAGE_LINE_RE.match(stripped):
            continue
        if _DOTTED_MANAGE_LINE_RE.match(stripped):
            continue
        if _DOTTED_GUIDE_LINE_RE.match(stripped):
            continue
        cleaned = stripped
        cleaned = _REPORT_CLAUSE_RE.sub("", cleaned)
        cleaned = _DOTTED_REPORT_CLAUSE_RE.sub("", cleaned)
        cleaned = _INLINE_MANAGE_RE.sub("", cleaned)
        cleaned = re.sub(r"^[；;\s]+", "", cleaned)
        cleaned = re.sub(r"[；;\s]+$", "", cleaned)
        if cleaned:
            bio_parts.append(cleaned.strip())
    return "\n".join(bio_parts).strip()


def _parse_block_relationships(
    name: str,
    body: str,
    *,
    by_title: dict[str, str],
    by_name: set[str],
    relationships: list[dict[str, Any]],
    seen: set[tuple[str, str, str]],
) -> None:
    for rel_type, raw_target in _extract_report_targets(body):
        target = _resolve_target(raw_target, by_title, by_name)
        _add_edge(relationships, seen, from_name=name, relation=rel_type, to_name=target)

    for line in body.splitlines():
        stripped = line.strip()
        for pat, rel in (
            (_MANAGE_LINE_RE, "管辖"),
            (_DOTTED_MANAGE_LINE_RE, "虚线管辖"),
            (_DOTTED_GUIDE_LINE_RE, "虚线指导"),
        ):
            m = pat.match(stripped)
            if not m:
                continue
            for part in _split_target_list(m.group(1)):
                if _is_headcount_placeholder(part):
                    continue
                target = _resolve_target(part, by_title, by_name)
                _add_edge(relationships, seen, from_name=name, relation=rel, to_name=target)

    for m in _INLINE_MANAGE_RE.finditer(body.replace("\n", "；")):
        for part in _split_target_list(m.group(1)):
            if _is_headcount_placeholder(part):
                continue
            target = _resolve_target(part, by_title, by_name)
            _add_edge(relationships, seen, from_name=name, relation="管辖", to_name=target)

    collab = _COLLAB_LINE_RE.search(body)
    if collab:
        text = collab.group(1).strip()
        for m in re.finditer(r"与\s*(.+?)(?:对接|联调|协作|探讨|核对|维护|协调|分配|审核|签字|对齐|对接)", text):
            target = _resolve_target(m.group(1).strip(), by_title, by_name)
            _add_edge(relationships, seen, from_name=name, relation="协作", to_name=target)


def _parse_bilateral_collabs(text: str) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        m = _BILATERAL_COLLAB_RE.match(stripped)
        if m:
            rows.append((m.group(1).strip(), m.group(2).strip(), m.group(3).strip()))
    return rows


def parse_org_chart_text(text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (people, relationships) from org-chart formatted text."""
    blocks = _split_person_blocks(text or "")
    people, by_name, by_title = _build_indexes(blocks)
    for i, (name, _title, body) in enumerate(blocks):
        people[i]["bio"] = _extract_bio_from_block(body)

    relationships: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    for name, _title, body in blocks:
        _parse_block_relationships(
            name,
            body,
            by_title=by_title,
            by_name=by_name,
            relationships=relationships,
            seen=seen,
        )

    for left, right, _note in _parse_bilateral_collabs(text or ""):
        a = _resolve_target(left, by_title, by_name)
        b = _resolve_target(right, by_title, by_name)
        _add_edge(relationships, seen, from_name=a, relation="协作", to_name=b)
        _add_edge(relationships, seen, from_name=b, relation="协作", to_name=a)

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


def org_chart_ingest_message(text: str, *, source: str, department: str) -> str:
    """Best-effort org chart import during text ingest; returns UI suffix."""
    try:
        counts = import_org_chart_if_detected(text, source=source, department=department)
    except Exception:
        return ""
    if not counts:
        return ""
    pc, ec = counts
    return f"；已解析组织关系图 {pc} 人、{ec} 条（已覆盖同部门旧关系文档）"

"""Infer exam paper metadata from corpus path / filename."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_YEAR_RE = re.compile(r"(20\d{2})")

_SUBJECTS = (
    "数学",
    "语文",
    "英语",
    "物理",
    "化学",
    "生物",
    "历史",
    "地理",
    "政治",
    "道德与法治",
)

_REGIONS = (
    "浙江",
    "广东",
    "北京",
    "上海",
    "江苏",
    "山东",
    "河南",
    "河北",
    "湖南",
    "湖北",
    "四川",
    "重庆",
    "福建",
    "安徽",
    "江西",
    "陕西",
    "山西",
    "辽宁",
    "吉林",
    "黑龙江",
    "天津",
    "云南",
    "贵州",
    "广西",
    "海南",
    "甘肃",
    "宁夏",
    "青海",
    "新疆",
    "西藏",
    "内蒙古",
    "全国",
)

_GRADE_MAP = {
    "高一": "高一",
    "高二": "高二",
    "高三": "高三",
    "高三-高考": "高三",
    "初一": "初一",
    "初二": "初二",
    "初三": "初三",
    "九年级": "初三",
    "八年级": "初二",
    "七年级": "初一",
}

_EXAM_TYPES: list[tuple[str, str]] = [
    ("高考", "高考"),
    ("新课标", "高考"),
    ("新高考", "高考"),
    ("一模", "一模"),
    ("二模", "二模"),
    ("三模", "三模"),
    ("月考", "月考"),
    ("周测", "周测"),
    ("周考", "周测"),
    ("期末", "期末"),
    ("期中", "期中"),
    ("联考", "联考"),
    ("质检", "质检"),
    ("练习", "练习"),
]


def _paper_kind(name: str) -> str:
    n = name or ""
    if any(k in n for k in ("解析", "答案", "教师版", "教师", "含解析")):
        return "answer"
    if any(k in n for k in ("空白", "学生版", "学生")):
        return "blank"
    if "原卷" in n:
        return "original"
    return "other"


def _stream_track(name: str) -> str:
    if "文科" in name or "【文】" in name or "［文］" in name:
        return "文"
    if "理科" in name or "【理】" in name or "［理］" in name:
        return "理"
    return ""


def _normalize_stem(name: str) -> str:
    stem = name or ""
    for suf in (
        "（空白卷）",
        "（含解析版）",
        "（解析版）",
        "（解析）",
        "（原卷版）",
        "（原卷）",
        "（学生版）",
        "（教师版）",
        "(空白卷)",
        "(含解析版)",
        "(解析版)",
        "(解析)",
        "(原卷版)",
        "(原卷)",
        ".docx",
        ".doc",
        ".pdf",
    ):
        stem = stem.replace(suf, "")
    # also strip loose 含解析版 / 解析版 remnants
    stem = stem.replace("含解析版", "").replace("解析版", "")
    stem = re.sub(r"\s+", "", stem)
    return stem


def _exam_type(text: str) -> str:
    for key, label in _EXAM_TYPES:
        if key in text:
            return label
    return "试卷"


def _find_subject(text: str) -> str:
    for s in _SUBJECTS:
        if s in text:
            return s
    return ""


def _find_region(text: str) -> str:
    # longer names first
    for r in sorted(_REGIONS, key=len, reverse=True):
        if r in text:
            return r
    return ""


def _find_grade(parts: tuple[str, ...], name: str) -> str:
    blob = "/".join(parts) + "/" + name
    for key, g in _GRADE_MAP.items():
        if key in blob:
            return g
    if "高考" in blob and "高" in blob:
        return "高三"
    return ""


def _stage_from_grade(grade: str, blob: str) -> str:
    if grade.startswith("高") or "高中" in blob:
        return "senior"
    if grade.startswith("初") or "初中" in blob:
        return "junior"
    if "小学" in blob:
        return "primary"
    return "senior" if "高考" in blob else ""


def infer_corpus_meta(path: Path | str, *, root: Path | str | None = None) -> dict[str, Any]:
    """
    Parse relative path like:
      2024/高中/高三/数学/浙江/2024年高考….docx
      浙江高考数学/A4 word版/2018年….docx
    """
    p = Path(path)
    name = p.name
    try:
        rel_parts = p.relative_to(Path(root)).parts if root else p.parts
    except ValueError:
        rel_parts = p.parts

    # drop filename
    dirs = rel_parts[:-1] if rel_parts and rel_parts[-1] == name else rel_parts
    blob = "/".join(dirs) + "/" + name

    year = ""
    m = _YEAR_RE.search(name) or _YEAR_RE.search(blob)
    if m:
        year = m.group(1)
    # folder year often first segment
    if dirs and re.fullmatch(r"20\d{2}", dirs[0] or ""):
        year = year or dirs[0]

    subject = _find_subject(blob)
    region = _find_region(blob)
    # 浙江高考数学 archive
    if not region and "浙江高考" in blob:
        region = "浙江"
    if not subject and "数学" in blob:
        subject = "数学"

    grade = _find_grade(tuple(str(x) for x in dirs), name)
    if not grade and ("高考" in blob or "浙江高考数学" in blob):
        grade = "高三"
    stage = _stage_from_grade(grade, blob)
    exam_type = _exam_type(blob)
    paper_kind = _paper_kind(name)
    track = _stream_track(name)

    # layout preference: A4 > A3 > PDF folder
    layout = ""
    if "A4" in blob:
        layout = "A4"
    elif "A3" in blob:
        layout = "A3"
    if "PDF版" in blob or p.suffix.lower() == ".pdf":
        layout = layout or "PDF"

    stem = _normalize_stem(name)

    return {
        "year": year,
        "subject": subject or "未知",
        "region": region or "未知",
        "grade": grade or "未分年级",
        "stage": stage,
        "exam_type": exam_type,
        "paper_kind": paper_kind,
        "track": track,
        "layout": layout,
        "filename": name,
        "dedupe_key": "|".join(
            [
                year or "?",
                region or "?",
                subject or "?",
                grade or "?",
                exam_type,
                track or "-",
                stem,
            ]
        ),
        "collection_key": "|".join([region or "未知", subject or "未知", grade or "未分年级"]),
        "path": str(p),
    }


def rank_paper_candidate(meta: dict[str, Any], path: Path) -> tuple[int, int, int]:
    """Higher is better when choosing among duplicates.

    Prefer answer editions; among formats prefer .docx (EQ extract) > .pdf > legacy .doc
    (legacy .doc often needs unstructured which may be unavailable).
    """
    kind_score = {"answer": 50, "blank": 30, "original": 20, "other": 10}.get(
        str(meta.get("paper_kind") or ""), 0
    )
    ext_score = {".docx": 40, ".pdf": 25, ".doc": 5}.get(path.suffix.lower(), 0)
    layout_score = {"A4": 10, "A3": 5, "PDF": 0}.get(str(meta.get("layout") or ""), 0)
    return (kind_score, ext_score, layout_score)


def select_corpus_files(root: Path | str, *, prefer_answer: bool = True) -> list[dict[str, Any]]:
    """Scan corpus; keep best file per dedupe_key (answer > blank > original)."""
    root_p = Path(root)
    best: dict[str, tuple[tuple[int, int, int], Path, dict[str, Any]]] = {}
    for p in root_p.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in {".docx", ".doc", ".pdf"}:
            continue
        meta = infer_corpus_meta(p, root=root_p)
        if prefer_answer and meta.get("paper_kind") == "original":
            # still consider originals, but lower rank — kept only if no answer twin
            pass
        key = str(meta["dedupe_key"])
        score = rank_paper_candidate(meta, p)
        prev = best.get(key)
        if prev is None or score > prev[0]:
            best[key] = (score, p, meta)
    out: list[dict[str, Any]] = []
    for _score, path, meta in best.values():
        row = dict(meta)
        row["path"] = str(path)
        out.append(row)
    out.sort(key=lambda r: (r.get("year") or "", r.get("region") or "", r.get("filename") or ""))
    return out

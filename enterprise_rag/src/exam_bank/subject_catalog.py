"""Subject × stage question-type templates (aligned with common CN exams)."""

from __future__ import annotations

import re
from typing import Any

BUILTIN_QTYPES = (
    "choice",
    "fill",
    "short",  # 解答/非选择综合（数学常用）
    "calc",
    "experiment",
    "cloze",
    "reading",
    "writing",
    "listening",
    "material",  # 材料分析
    "other",
)

QTYPE_LABELS: dict[str, str] = {
    "choice": "选择题",
    "fill": "填空题",
    "short": "解答题",
    "calc": "计算题",
    "experiment": "实验题",
    "cloze": "完形填空",
    "reading": "阅读理解",
    "writing": "写作",
    "listening": "听力",
    "material": "材料分析题",
    "other": "其他",
}

SECTION_ALIASES: dict[str, str] = {
    "选择题": "choice",
    "选择": "choice",
    "单选题": "choice",
    "多选题": "choice",
    "填空题": "fill",
    "填空": "fill",
    "语法填空": "fill",
    "简答题": "short",
    "简答": "short",
    "解答题": "short",
    "解答": "short",
    "问答题": "short",
    "计算题": "calc",
    "计算": "calc",
    "大题": "short",
    "综合题": "short",
    "应用题": "short",
    "证明题": "short",
    "实验题": "experiment",
    "实验": "experiment",
    "作文": "writing",
    "写作": "writing",
    "书面表达": "writing",
    "阅读理解": "reading",
    "现代文阅读": "reading",
    "古代诗文阅读": "reading",
    "完形填空": "cloze",
    "听力": "listening",
    "材料分析": "material",
    "材料题": "material",
    "非选择题": "short",
}

DIFFICULTY_BANDS: dict[str, tuple[int, int]] = {
    "easy": (1, 2),
    "mid": (3, 3),
    "hard": (4, 5),
}

DIFFICULTY_BAND_LABELS = {"easy": "简单", "mid": "中等", "hard": "困难"}

STAGES = ("primary", "junior", "senior")
STAGE_LABELS = {"primary": "小学", "junior": "初中", "senior": "高中"}

# grade text → stage
GRADE_TO_STAGE: dict[str, str] = {
    "小学": "primary",
    "一年级": "primary",
    "二年级": "primary",
    "三年级": "primary",
    "四年级": "primary",
    "五年级": "primary",
    "六年级": "primary",
    "初一": "junior",
    "初二": "junior",
    "初三": "junior",
    "七年级": "junior",
    "八年级": "junior",
    "九年级": "junior",
    "高一": "senior",
    "高二": "senior",
    "高三": "senior",
}

DEFAULT_GRADES_BY_STAGE: dict[str, list[str]] = {
    "primary": ["小学", "三年级", "四年级", "五年级", "六年级"],
    "junior": ["初一", "初二", "初三"],
    "senior": ["高一", "高二", "高三"],
}

# subject → stage → qtypes（贴近常见卷面）
SUBJECT_STAGE_QTYPES: dict[str, dict[str, tuple[str, ...]]] = {
    "数学": {
        "primary": ("choice", "fill", "short"),
        "junior": ("choice", "fill", "short"),
        "senior": ("choice", "fill", "short"),
    },
    "语文": {
        "primary": ("choice", "fill", "reading", "writing"),
        "junior": ("choice", "fill", "reading", "writing"),
        "senior": ("choice", "reading", "writing"),
    },
    "英语": {
        "primary": ("choice", "fill", "reading", "writing"),
        "junior": ("listening", "choice", "cloze", "reading", "fill", "writing"),
        "senior": ("listening", "choice", "cloze", "reading", "fill", "writing"),
    },
    "物理": {
        "junior": ("choice", "fill", "experiment", "short"),
        "senior": ("choice", "fill", "experiment", "short"),
    },
    "化学": {
        "junior": ("choice", "fill", "experiment", "short"),
        "senior": ("choice", "fill", "experiment", "short"),
    },
    "生物": {
        "junior": ("choice", "fill", "short"),
        "senior": ("choice", "short"),
    },
    "历史": {
        "junior": ("choice", "material"),
        "senior": ("choice", "material"),
    },
    "地理": {
        "junior": ("choice", "material"),
        "senior": ("choice", "material"),
    },
    "政治": {
        "junior": ("choice", "material"),
        "senior": ("choice", "material"),
    },
    "其他": {
        "primary": ("choice", "fill", "short", "other"),
        "junior": ("choice", "fill", "short", "other"),
        "senior": ("choice", "fill", "short", "other"),
    },
}


def resolve_stage(grade: str = "", stage: str = "") -> str:
    s = (stage or "").strip().lower()
    if s in STAGES:
        return s
    g = (grade or "").strip()
    if g in GRADE_TO_STAGE:
        return GRADE_TO_STAGE[g]
    for key, st in GRADE_TO_STAGE.items():
        if key in g:
            return st
    return "junior"


def qtypes_for_subject(subject: str, *, grade: str = "", stage: str = "") -> list[str]:
    key = (subject or "").strip() or "其他"
    st = resolve_stage(grade, stage)
    table = SUBJECT_STAGE_QTYPES.get(key)
    if not table:
        for name, rows in SUBJECT_STAGE_QTYPES.items():
            if name in key or key in name:
                table = rows
                break
    if not table:
        table = SUBJECT_STAGE_QTYPES["其他"]
    if st in table:
        return list(table[st])
    # fallback nearest stage
    for cand in ("junior", "senior", "primary"):
        if cand in table:
            return list(table[cand])
    return list(SUBJECT_STAGE_QTYPES["其他"]["junior"])


def normalize_qtype(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return "other"
    if s.startswith("custom:"):
        return s
    low = s.lower()
    if low in BUILTIN_QTYPES:
        return low
    if s in SECTION_ALIASES:
        return SECTION_ALIASES[s]
    base = s[:-1] if s.endswith("题") and len(s) > 1 else s
    if base in SECTION_ALIASES:
        return SECTION_ALIASES[base]
    for k, v in QTYPE_LABELS.items():
        if v == s:
            return k
    safe = re.sub(r"\s+", "", s)
    if safe in BUILTIN_QTYPES:
        return safe
    return f"custom:{safe}"


def qtype_label(qtype: str) -> str:
    qt = (qtype or "").strip()
    if qt in QTYPE_LABELS:
        return QTYPE_LABELS[qt]
    if qt.startswith("custom:"):
        return qt.split(":", 1)[1] or qt
    return qt or "未知题型"


def subject_catalog_public(*, stage: str = "junior") -> list[dict[str, Any]]:
    st = resolve_stage(stage=stage)
    out = []
    for name in SUBJECT_STAGE_QTYPES:
        qts = qtypes_for_subject(name, stage=st)
        out.append(
            {
                "id": name,
                "label": name,
                "stage": st,
                "stage_label": STAGE_LABELS.get(st, st),
                "grades": list(DEFAULT_GRADES_BY_STAGE.get(st, DEFAULT_GRADES_BY_STAGE["junior"])),
                "qtypes": [{"id": q, "label": qtype_label(q)} for q in qts],
            }
        )
    return out


def difficulty_bands_public() -> list[dict[str, Any]]:
    return [
        {
            "id": bid,
            "label": DIFFICULTY_BAND_LABELS[bid],
            "difficulty_min": rng[0],
            "difficulty_max": rng[1],
        }
        for bid, rng in DIFFICULTY_BANDS.items()
    ]


def stages_public() -> list[dict[str, str]]:
    return [{"id": s, "label": STAGE_LABELS[s]} for s in STAGES]

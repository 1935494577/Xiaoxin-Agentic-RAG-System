"""Helpers shared by exam export (PDF/DOCX/MD): EQ images + noise strip."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_EQ_RE = re.compile(r"\[\[EQ:(\d+)\]\]")

# 菁优网 / 组卷网入库噪音：导出时剥离，避免出现在正式试卷
_NOISE_LINE = re.compile(
    r"^\s*(?:"
    r"【考点】|【专题】|【知识点】|【难度】|【来源】|"
    r"菁优网版权所有|学科网版权|组卷网|"
    r"考点点睛|本题考查"
    r").*$",
    re.M,
)
_NOISE_INLINE = re.compile(
    r"\s*菁优网版权所有\s*|"
    r"\s*【考点】[^【\n]*|"
    r"\s*【专题】[^【\n]*"
)


def strip_export_noise(text: str) -> str:
    """Remove marketplace watermarks / meta lines from stem/analysis for export."""
    s = text or ""
    s = _NOISE_LINE.sub("", s)
    s = _NOISE_INLINE.sub("", s)
    # collapse excess blank lines
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def split_eq_segments(raw: str) -> list[tuple[str, str]]:
    """Return list of ('text', value) | ('eq', id)."""
    s = raw or ""
    out: list[tuple[str, str]] = []
    last = 0
    for m in _EQ_RE.finditer(s):
        if m.start() > last:
            out.append(("text", s[last : m.start()]))
        out.append(("eq", m.group(1)))
        last = m.end()
    if last < len(s):
        out.append(("text", s[last:]))
    return out or [("text", s)]


def resolve_eq_png(
    media_ingest_id: str,
    eq_id: str | int,
    *,
    media_root: Path | str | None = None,
) -> Path | None:
    """Best-effort path to a PNG (or raster) for ReportLab / python-docx."""
    from exam_bank.docx_extract import default_exam_media_root, resolve_eq_media_file

    mid = (media_ingest_id or "").strip()
    if not mid:
        return None
    root = Path(media_root) if media_root is not None else default_exam_media_root()
    path = resolve_eq_media_file(root, mid, eq_id)
    if path is None or not path.is_file():
        return None
    suf = path.suffix.lower()
    if suf in {".png", ".jpg", ".jpeg", ".gif"}:
        return path
    if suf in {".wmf", ".emf"}:
        # Convert beside source for exporters that cannot paint WMF
        png = path.with_suffix(".png")
        if png.is_file():
            return png
        try:
            from PIL import Image

            with Image.open(path) as im:
                im.convert("RGBA").save(png, format="PNG")
            if png.is_file():
                return png
        except Exception:
            return None
    return None


def eq_placeholder_label(eq_id: str | int) -> str:
    return f"[公式{eq_id}]"


def sanitize_question_fields(q: dict[str, Any]) -> dict[str, Any]:
    """Copy question with cleaned stem/options/answer/analysis for export."""
    out = dict(q)
    out["stem"] = strip_export_noise(str(q.get("stem") or ""))
    out["answer"] = strip_export_noise(str(q.get("answer") or ""))
    out["analysis"] = strip_export_noise(str(q.get("analysis") or ""))
    opts = []
    for o in q.get("options") or []:
        cleaned = strip_export_noise(str(o))
        if cleaned:
            opts.append(cleaned)
    out["options"] = opts
    return out

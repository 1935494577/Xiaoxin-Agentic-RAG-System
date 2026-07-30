"""Question completeness for exam-bank closed loop (manage / assemble)."""

from __future__ import annotations

import re
from typing import Any

_OPT_PREFIX = re.compile(r"^[A-Da-d][\.．、:：\)）\s]*")

# choice-like types that need substantive options
_CHOICE_TYPES = frozenset({"choice", "multi", "multi_choice", "single"})


def option_body(text: str) -> str:
    return _OPT_PREFIX.sub("", (text or "").strip()).strip()


def options_incomplete(options: list[Any] | None, *, qtype: str = "") -> bool:
    """True when choice-like item lacks usable option bodies."""
    qt = (qtype or "").strip().lower()
    if qt and qt not in _CHOICE_TYPES:
        return False
    opts = [str(x) for x in (options or [])]
    if not opts:
        return qt in _CHOICE_TYPES or not qt
    bodies = [option_body(o) for o in opts]
    nonempty = [b for b in bodies if b]
    # Need at least 2 real option texts (A/B/C/D alone does not count)
    return len(nonempty) < 2


def incomplete_reasons(question: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    qt = str(question.get("qtype") or "").strip().lower()
    opts = question.get("options")
    if not isinstance(opts, list):
        opts = []
    if qt in _CHOICE_TYPES and options_incomplete(opts, qtype=qt):
        reasons.append("options")
    if not str(question.get("answer") or "").strip():
        reasons.append("answer")
    stem = str(question.get("stem") or "").strip()
    if not stem:
        reasons.append("stem")
    return reasons


def is_question_incomplete(question: dict[str, Any]) -> bool:
    return bool(incomplete_reasons(question))


def annotate_completeness(question: dict[str, Any]) -> dict[str, Any]:
    reasons = incomplete_reasons(question)
    out = dict(question)
    out["incomplete"] = bool(reasons)
    out["incomplete_reasons"] = reasons
    return out


def normalize_question_display(question: dict[str, Any]) -> dict[str, Any]:
    """Collapse PDF glyph-spacing in text fields for UI/export (non-destructive copy)."""
    from exam_bank.paper_clean import collapse_spaced_cjk

    out = dict(question)
    for key in ("stem", "answer", "analysis"):
        if out.get(key):
            out[key] = collapse_spaced_cjk(str(out[key]))
    opts = out.get("options")
    if isinstance(opts, list):
        out["options"] = [collapse_spaced_cjk(str(x)) for x in opts]
    return out

"""Exam bank constants."""

from __future__ import annotations

QTYPES = (
    "choice",
    "fill",
    "short",
    "calc",
    "experiment",
    "cloze",
    "reading",
    "writing",
    "listening",
    "material",
    "other",
)
QUALITY_STATUSES = ("draft", "published")
DIFFICULTY_MIN = 1
DIFFICULTY_MAX = 5
DEFAULT_TENANT = "internal"
EXAM_SCENE_PRESETS = ("exam_assemble", "exam_lesson", "exam_ingest")

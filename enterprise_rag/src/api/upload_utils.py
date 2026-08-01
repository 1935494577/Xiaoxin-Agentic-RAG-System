"""Shared upload filename sanitization."""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException


def safe_upload_filename(filename: str | None) -> str:
    """Basename only; reject path traversal (.., separators)."""
    raw = (filename or "upload.bin").strip()
    name = Path(raw).name
    if not name or name in {".", ".."} or ".." in raw.replace("\\", "/"):
        raise HTTPException(status_code=400, detail="Invalid upload filename")
    return name

"""Load frontend/admin/streamlit_common.py by file path (cached across Streamlit reruns)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_MODULE_NAME = "rag_streamlit_common"


def load_streamlit_common(frontend_dir: Path | None = None):
    root = (frontend_dir or Path(__file__).resolve().parent).resolve()
    path = (root / "streamlit_common.py").resolve()
    if not path.is_file():
        raise ImportError(f"streamlit_common not found: {path}")

    existing = sys.modules.get(_MODULE_NAME)
    if existing is not None:
        cached_mtime = getattr(existing, "__source_mtime__", 0)
        if cached_mtime == path.stat().st_mtime:
            return existing

    spec = importlib.util.spec_from_file_location(_MODULE_NAME, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module spec from {path}")
    mod = importlib.util.module_from_spec(spec)
    mod.__source_mtime__ = path.stat().st_mtime
    sys.modules[_MODULE_NAME] = mod
    spec.loader.exec_module(mod)
    return mod

"""Load frontend/streamlit_common.py by file path (avoids stale sys.modules cache)."""

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

    # Always load from disk; avoid importlib.reload (no __spec__ on file-backed modules).
    sys.modules.pop(_MODULE_NAME, None)

    spec = importlib.util.spec_from_file_location(_MODULE_NAME, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module spec from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[_MODULE_NAME] = mod
    spec.loader.exec_module(mod)
    return mod

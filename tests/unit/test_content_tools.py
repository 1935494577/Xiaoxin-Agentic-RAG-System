"""Builtin tools: list_kb_sources, format_structured_output."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "enterprise_rag" / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

_fmt_path = _SRC / "agent" / "tools" / "builtins" / "format_structured_output.py"
_spec = importlib.util.spec_from_file_location("format_structured_output", _fmt_path)
assert _spec and _spec.loader
_fmt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fmt)
format_structured_output = _fmt.format_structured_output


def test_format_structured_output_unknown_schema():
    raw = format_structured_output("draft", "not_a_schema")
    data = json.loads(raw)
    assert data["ok"] is False
    assert "available" in data


def test_format_structured_output_known_schema():
    raw = format_structured_output("要点一", "selling_points")
    data = json.loads(raw)
    assert data["ok"] is True
    assert data["schema_id"] == "selling_points"
    assert "instruction" in data

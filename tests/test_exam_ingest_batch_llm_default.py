"""TDD: batch corpus ingest defaults to LLM split; --no-llm opts out."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ingest_all_exam_papers.py"


def _load_ingest_script():
    spec = importlib.util.spec_from_file_location("ingest_all_exam_papers", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_batch_ingest_cli_defaults_use_llm_true():
    mod = _load_ingest_script()
    parser = mod.build_arg_parser()
    args = parser.parse_args([])
    assert mod.resolve_use_llm(args) is True


def test_batch_ingest_cli_no_llm_disables():
    mod = _load_ingest_script()
    parser = mod.build_arg_parser()
    args = parser.parse_args(["--no-llm"])
    assert mod.resolve_use_llm(args) is False

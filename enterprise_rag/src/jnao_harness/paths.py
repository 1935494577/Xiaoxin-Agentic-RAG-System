"""Resolve Jnao harness and project paths (Windows dev default included)."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """Monorepo root (parent of enterprise_rag/)."""
    env = (os.getenv("DEER_FLOW_PROJECT_ROOT") or os.getenv("JNAO_REPO_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    # enterprise_rag/src/jnao_harness/paths.py → repo root
    return Path(__file__).resolve().parents[3]


def resolve_harness_root() -> Path:
    """
    Local deer-flow harness package directory.

    Override with AGENT_HARNESS_PATH or DEER_FLOW_HARNESS_PATH when the checkout is not at the default path.
    """
    env = (os.getenv("AGENT_HARNESS_PATH") or os.getenv("DEER_FLOW_HARNESS_PATH") or "").strip()
    if env:
        return Path(env).resolve()
    default = Path(r"D:\bytedance flow\deer-flow\backend\packages\harness")
    if default.is_dir():
        return default
    # Relative fallback from repo root (submodule layout)
    candidate = repo_root() / "vendor" / "deer-flow" / "backend" / "packages" / "harness"
    return candidate.resolve()


def assert_harness_present() -> Path:
    root = resolve_harness_root()
    if not (root / "deerflow").is_dir():
        raise FileNotFoundError(
            f"Agent harness not found under {root}. "
            "Set AGENT_HARNESS_PATH to backend/packages/harness in your harness checkout."
        )
    return root

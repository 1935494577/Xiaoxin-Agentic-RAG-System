"""DF-0: agent harness config + harness path (real parameters, no mocks for file layout)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

# Locked to deer-flow config.example.yaml schema version at integration start.
EXPECTED_CONFIG_VERSION = 17
EXPECTED_MODEL_NAME = "jnao-default"
EXPECTED_WEB_SEARCH_USE = "deerflow.community.tavily.tools:web_search_tool"
EXPECTED_KB_SEARCH_USE = "jnao_community.kb_search:kb_search_tool"
DEFAULT_HARNESS_SUFFIX = Path("backend") / "packages" / "harness"


def _config_path() -> Path:
    return REPO_ROOT / "config.yaml"


def _extensions_path() -> Path:
    return REPO_ROOT / "extensions_config.json"


def _load_config_yaml() -> dict:
    path = _config_path()
    assert path.is_file(), f"missing {path}"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _tool_by_name(cfg: dict, name: str) -> dict:
    tools = cfg.get("tools") or []
    for row in tools:
        if isinstance(row, dict) and row.get("name") == name:
            return row
    raise AssertionError(f"tool {name!r} not in config.yaml tools")


def test_repo_has_deerflow_config_files():
    assert _config_path().is_file()
    assert _extensions_path().is_file()
    assert (REPO_ROOT / "skills" / "public").is_dir()


def test_config_yaml_schema_version_and_token_usage():
    cfg = _load_config_yaml()
    assert cfg.get("config_version") == EXPECTED_CONFIG_VERSION
    token_usage = cfg.get("token_usage") or {}
    assert token_usage.get("enabled") is True


def test_config_yaml_model_uses_openai_env_vars():
    cfg = _load_config_yaml()
    models = cfg.get("models") or []
    assert len(models) >= 1
    primary = models[0]
    assert primary.get("name") == EXPECTED_MODEL_NAME
    assert primary.get("use") == "langchain_openai:ChatOpenAI"
    assert primary.get("model") == "$OPENAI_CHAT_MODEL"
    assert primary.get("openai_api_base") == "$OPENAI_API_BASE"
    assert primary.get("openai_api_key") == "$OPENAI_API_KEY"


def test_config_yaml_tool_groups_include_rag_and_web():
    cfg = _load_config_yaml()
    groups = {g.get("name") for g in (cfg.get("tool_groups") or []) if isinstance(g, dict)}
    assert "web" in groups
    assert "rag" in groups


def test_config_yaml_web_search_uses_tavily_community():
    cfg = _load_config_yaml()
    tool = _tool_by_name(cfg, "web_search")
    assert tool.get("group") == "web"
    assert tool.get("use") == EXPECTED_WEB_SEARCH_USE
    assert tool.get("max_results") == 5


def test_config_yaml_kb_search_registered_for_rag():
    cfg = _load_config_yaml()
    tool = _tool_by_name(cfg, "kb_search")
    assert tool.get("group") == "rag"
    assert tool.get("use") == EXPECTED_KB_SEARCH_USE


def test_extensions_config_json_skills_object():
    data = json.loads(_extensions_path().read_text(encoding="utf-8"))
    assert isinstance(data.get("skills"), dict)
    assert data.get("mcpServers") == {} or isinstance(data.get("mcpServers"), dict)


def test_harness_path_points_to_local_deer_flow():
    from jnao_harness.paths import resolve_harness_root

    root = resolve_harness_root()
    assert root.is_dir(), f"harness root missing: {root}"
    assert (root / "deerflow" / "agents" / "lead_agent").is_dir()
    assert (root / "pyproject.toml").is_file()


def test_harness_does_not_import_app_layer():
    """Port of deer-flow/backend/tests/test_harness_boundary.py against local harness."""
    import ast

    from jnao_harness.paths import resolve_harness_root

    harness_deerflow = resolve_harness_root() / "deerflow"
    violations: list[str] = []
    for py_file in sorted(harness_deerflow.rglob("*.py")):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name
                    if mod == "app" or mod.startswith("app."):
                        violations.append(f"{py_file}:{node.lineno} imports {mod}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module
                if mod == "app" or mod.startswith("app."):
                    violations.append(f"{py_file}:{node.lineno} imports {mod}")
    assert not violations, "harness must not import app:\n" + "\n".join(violations)


@pytest.mark.harness
def test_harness_get_app_config_reads_jnao_config():
    """Requires deerflow-harness installed (see requirements-harness.txt)."""
    deerflow = pytest.importorskip("deerflow")
    from deerflow.config.app_config import AppConfig

    cfg = AppConfig.from_file(str(_config_path()))
    assert cfg.token_usage.enabled is True
    assert cfg.models[0].name == EXPECTED_MODEL_NAME
    web = next(t for t in cfg.tools if t.name == "web_search")
    assert web.use == EXPECTED_WEB_SEARCH_USE
    assert deerflow is not None


@pytest.mark.harness
def test_harness_get_available_tools_includes_kb_and_web_search():
    pytest.importorskip("deerflow")
    from deerflow.config.app_config import AppConfig
    from deerflow.tools import get_available_tools

    app_cfg = AppConfig.from_file(str(_config_path()))
    tools = get_available_tools(app_config=app_cfg, include_mcp=False, subagent_enabled=False)
    names = {t.name for t in tools}
    assert "web_search" in names
    assert "kb_search" in names

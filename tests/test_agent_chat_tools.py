"""Tests for chat agent tools (weather, protocol, executor)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "enterprise_rag" / "src"))

from agent.tools.builtins.weather import get_weather  # noqa: E402
from agent.tools.config.registry import (  # noqa: E402
    TOOL_DEFINITIONS,
    enabled_tool_ids,
    load_tools_config,
    save_tools_config,
)
from agent.tools.protocol.openai import openai_tools_payload  # noqa: E402
from agent.tools.runtime.loop import run_tool_loop  # noqa: E402
from config import settings  # noqa: E402


@pytest.fixture()
def agent_tools_cfg(tmp_path, monkeypatch):
    path = tmp_path / "agent_tools.json"
    monkeypatch.setattr(settings, "agent_tools_path", path)
    yield path


def test_openai_tools_payload_only_enabled():
    payload = openai_tools_payload({"get_weather"}, TOOL_DEFINITIONS)
    assert len(payload) == 1
    assert payload[0]["function"]["name"] == "get_weather"
    assert payload[0]["function"]["parameters"]["required"] == ["city"]


def test_execute_weather_mocked():
    fake = {
        "current_condition": [{"temp_C": "22", "FeelsLikeC": "21", "humidity": "60", "windspeedKmph": "10", "lang_zh": [{"value": "晴"}]}],
        "nearest_area": [{"areaName": [{"value": "杭州"}]}],
    }

    def _fake_urlopen(req, timeout=0):
        resp = MagicMock()
        resp.read.return_value = json.dumps(fake).encode("utf-8")
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("urllib.request.urlopen", _fake_urlopen):
        out = get_weather("杭州")
    assert "杭州" in out
    assert "22" in out
    assert "晴" in out
    assert "建议" in out


def test_agent_tools_config_roundtrip(agent_tools_cfg):
    save_tools_config({"chat_tools_enabled": False, "tools": {"get_weather": {"enabled": False}}})
    cfg = load_tools_config()
    assert cfg["chat_tools_enabled"] is False
    assert enabled_tool_ids(cfg) == set()


def test_run_tool_loop_invokes_weather():
    client = MagicMock()

    tool_call = MagicMock()
    tool_call.id = "call_1"
    tool_call.function.name = "get_weather"
    tool_call.function.arguments = '{"city": "上海"}'

    msg_tools = MagicMock()
    msg_tools.content = ""
    msg_tools.tool_calls = [tool_call]

    msg_final = MagicMock()
    msg_final.content = "上海今天天气不错。"
    msg_final.tool_calls = None

    resp_tools = MagicMock()
    resp_tools.choices = [MagicMock(message=msg_tools, finish_reason="tool_calls")]

    resp_final = MagicMock()
    resp_final.choices = [MagicMock(message=msg_final, finish_reason="stop")]

    client.chat.completions.create.side_effect = [resp_tools, resp_final]

    events: list[dict] = []
    with patch("agent.tools.runtime.loop.execute_tool", return_value="上海 晴 20°C"):
        text, trace = run_tool_loop(
            client,
            model="test-model",
            messages=[{"role": "user", "content": "上海天气怎么样？"}],
            enabled_ids={"get_weather"},
            emit=events.append,
        )

    assert any(e["type"] == "tool_call" and e["tool"] == "get_weather" for e in events)
    assert any(e["type"] == "tool_result" for e in events)
    assert trace[0]["tool"] == "get_weather"
    assert "上海今天" in text

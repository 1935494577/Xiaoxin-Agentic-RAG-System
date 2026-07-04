"""chat_memory_settings must resolve reasoning mode without NameError."""

from __future__ import annotations

from api.chat_memory import chat_memory_settings


def test_chat_memory_settings_includes_reasoning_mode():
    mem = chat_memory_settings()
    assert "agent_reasoning_mode" in mem
    assert mem["agent_reasoning_mode"] in ("direct", "react", "plan_execute")

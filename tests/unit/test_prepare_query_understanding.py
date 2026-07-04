"""Tests for prepare_turn integration with QueryUnderstanding."""

from __future__ import annotations

from agent.conversation.prepare import prepare_turn


def test_prepare_turn_conditional_rewrite_for_noisy_voice():
    turn = prepare_turn(
        message="电脑。今日萧山区天气。我就。",
        history=[],
        memory_config={"conversation_condense_enabled": False},
    )
    assert turn.message == "今日萧山区天气"
    assert turn.skip_retrieval_rewrite is False
    assert turn.meta.get("needs_llm_rewrite") is True
    assert turn.meta.get("query_intent") == "realtime"


def test_prepare_turn_skips_rewrite_for_clean_query():
    turn = prepare_turn(
        message="什么是感知力",
        history=[],
        memory_config={"conversation_condense_enabled": False},
    )
    assert turn.skip_retrieval_rewrite is True
    assert turn.meta.get("query_intent") == "kb"

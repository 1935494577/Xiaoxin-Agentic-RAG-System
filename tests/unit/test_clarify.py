"""Clarify gate for vague content/sales questions."""

from __future__ import annotations

from agent.clarify import (
    apply_clarify_choice_to_message,
    build_clarify_event,
    list_clarify_options,
    normalize_channel,
    resolve_clarify_choice,
    should_offer_clarify,
)


def test_normalize_channel_aliases():
    assert normalize_channel("douyin") == "douyin"
    assert normalize_channel("抖音") == "douyin"
    assert normalize_channel("企业微信") == "wecom"


def test_list_clarify_options_filters_douyin():
    all_opts = list_clarify_options(channel="all")
    assert len(all_opts) >= 4
    douyin = list_clarify_options(channel="douyin")
    ids = {o["id"] for o in douyin}
    assert "short_video" in ids
    assert "selling_points" in ids


def test_should_offer_clarify_when_vague_and_low_confidence():
    assert should_offer_clarify(
        enabled=True,
        skip_clarify=False,
        clarify_choice_id=None,
        rule_confidence=0.4,
        intent="unknown",
        message="超脑阅读",
    )


def test_should_not_clarify_when_choice_already_made():
    assert not should_offer_clarify(
        enabled=True,
        skip_clarify=False,
        clarify_choice_id="selling_points",
        rule_confidence=0.2,
        intent="unknown",
        message="超脑阅读",
    )


def test_apply_clarify_choice_prefixes_message():
    choice = resolve_clarify_choice("selling_points")
    assert choice is not None
    out = apply_clarify_choice_to_message("超脑阅读", choice)
    assert "卖点" in out or "提分" in out
    assert "超脑阅读" in out


def test_build_clarify_event_shape():
    evt = build_clarify_event(channel="wecom")
    assert evt["type"] == "clarify"
    assert evt["channel"] == "wecom"
    assert isinstance(evt["options"], list)
    assert evt["options"][0]["id"]

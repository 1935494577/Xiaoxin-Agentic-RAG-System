"""Structured output templates for content channels."""

from __future__ import annotations

from agent.output_schemas import (
    get_output_schema,
    list_output_schemas_public,
    output_schema_instruction,
)


def test_list_output_schemas_public_douyin_includes_short_video():
    rows = list_output_schemas_public(channel="douyin")
    ids = {r["id"] for r in rows}
    assert "short_video_script" in ids


def test_output_schema_instruction_non_empty_for_selling_points():
    text = output_schema_instruction("selling_points")
    assert "卖点" in text
    assert get_output_schema("missing") is None
    assert output_schema_instruction("missing") == ""

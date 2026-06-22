"""Tests for unified query understanding (Phase 1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from retrieval.query_understanding import (
    understand_query,
    rule_confidence,
    needs_llm_retrieval_rewrite,
)


def test_understand_voice_weather_noise():
    raw = "电脑。今日萧山区天气。我就。我就。"
    qu = understand_query(raw)
    assert qu.message == "今日萧山区天气"
    assert qu.intent == "realtime"
    assert qu.needs_llm_rewrite is True
    assert "今日萧山区天气" in qu.search_variants


def test_understand_oral_typo_gets_variants():
    qu = understand_query("咋整超脑阅度")
    assert any("超脑阅读" in v or "怎么" in v for v in qu.search_variants)
    # 规则扩展成功时不必强制 LLM rewrite
    assert qu.rule_confidence >= 0.65 or qu.needs_llm_rewrite


def test_understand_clean_kb_query_high_confidence():
    qu = understand_query("什么是感知力")
    assert qu.message == "什么是感知力"
    assert qu.intent == "kb"
    assert qu.rule_confidence >= 0.65
    assert qu.needs_llm_rewrite is False


def test_rule_confidence_drops_for_voice():
    assert rule_confidence("电脑。今日萧山区天气。我就。", "今日萧山区天气") < rule_confidence(
        "今日萧山区天气", "今日萧山区天气"
    )


def test_needs_rewrite_respects_threshold():
    assert needs_llm_retrieval_rewrite(0.5, threshold=0.65) is True
    assert needs_llm_retrieval_rewrite(0.9, threshold=0.65) is False


def test_understand_typo_canonicalizes_with_lexicon(tmp_path, monkeypatch):
    lexicon = tmp_path / "domain_lexicon.json"
    aliases = tmp_path / "query_aliases.json"
    lexicon.write_text(
        json.dumps({"terms": {"超脑阅读": {"sources": ["a"]}}, "updated_at": "t1"}),
        encoding="utf-8",
    )
    aliases.write_text(
        json.dumps({"oral_map": {}, "term_aliases": {"超脑阅读": ["超脑阅度"]}}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr("retrieval.domain_lexicon._lexicon_path", lambda: lexicon)
    monkeypatch.setattr("retrieval.query_normalize._aliases_path", lambda: aliases)
    qu = understand_query("超脑阅度有啥要求")
    assert "超脑阅读" in qu.retrieval_query
    assert qu.signals.get("domain_corrections")


def test_understand_exports_unified_dict():
    qu = understand_query("什么是感知力")
    d = qu.to_dict()
    assert d["canonical_query"] == "什么是感知力"
    assert d["intent"] == "kb_definition"
    assert "confidence" in d
    assert isinstance(d["search_variants"], list)


def test_golden_robustness_fixtures():
    path = Path(__file__).resolve().parents[1] / "data" / "eval" / "query_robustness.jsonl"
    assert path.is_file(), "missing query_robustness.jsonl"
    rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(rows) >= 5
    for row in rows:
        qu = understand_query(row["raw"])
        if "expect_message" in row:
            assert qu.message == row["expect_message"], row
        if "expect_intent" in row:
            assert qu.intent == row["expect_intent"], row
        if "expect_variant_contains" in row:
            needle = row["expect_variant_contains"]
            assert any(needle in v for v in qu.search_variants), (row, qu.search_variants)

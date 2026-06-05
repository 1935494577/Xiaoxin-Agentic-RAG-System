"""Processing tool router tests."""

from pathlib import Path

from document_loader.processing.registry import load_config
from document_loader.processing.router import rule_select_tools


def test_rule_select_uncleaned_txt(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello", encoding="utf-8")
    chain = rule_select_tools(p, mode="uncleaned", cfg=load_config())
    assert chain[0] == "extract_plain"
    assert "scrub_whitespace" in chain
    assert "redact_pii" in chain


def test_rule_select_pre_cleaned_pdf(tmp_path):
    p = tmp_path / "b.pdf"
    p.write_bytes(b"%PDF-1.4")
    chain = rule_select_tools(p, mode="pre_cleaned", cfg=load_config())
    assert chain[0] == "extract_pdf"
    assert "redact_pii" not in chain
    assert "scrub_whitespace" in chain


def test_legacy_mode_aliases(tmp_path):
    p = tmp_path / "c.txt"
    p.write_text("x", encoding="utf-8")
    cleaned_legacy = rule_select_tools(p, mode="cleaned", cfg=load_config())
    uncleaned = rule_select_tools(p, mode="uncleaned", cfg=load_config())
    assert cleaned_legacy == uncleaned

    raw_legacy = rule_select_tools(p, mode="raw", cfg=load_config())
    pre = rule_select_tools(p, mode="pre_cleaned", cfg=load_config())
    assert raw_legacy == pre

"""Prompt helpers."""

import importlib.util
import sys
from pathlib import Path

MOD = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src" / "agent" / "answer_prompts.py"
spec = importlib.util.spec_from_file_location("answer_prompts_test", MOD)
assert spec and spec.loader
prompts = importlib.util.module_from_spec(spec)
sys.modules["answer_prompts_test"] = prompts
spec.loader.exec_module(prompts)

kb_user_content = prompts.kb_user_content
general_user_content = prompts.general_user_content
kb_system_prompt = prompts.kb_system_prompt


def test_kb_user_content_includes_refs():
    text = kb_user_content(["资料A"], "问题?")
    assert "参考资料" in text
    assert "问题?" in text


def test_general_user_content():
    assert general_user_content("你好") == "用户问题：你好"


def test_kb_system_prompt_with_persona_override():
    out = kb_system_prompt(fast=False, persona="猫娘，喵")
    assert "猫娘" in out

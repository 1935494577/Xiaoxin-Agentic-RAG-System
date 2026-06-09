"""Prompt helpers."""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent.answer_prompts import kb_user_content, general_user_content  # noqa: E402


def test_kb_user_content_includes_refs():
    text = kb_user_content(["资料A"], "问题?")
    assert "参考资料" in text
    assert "问题?" in text


def test_general_user_content():
    assert general_user_content("你好") == "用户问题：你好"

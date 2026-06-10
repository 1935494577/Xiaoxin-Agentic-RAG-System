"""Conversation memory trimming tests."""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent.conversation_context import trim_history  # noqa: E402


def test_trim_history_by_turns():
    msgs = [{"role": "user", "content": "a"}] * 10
    out = trim_history(msgs, max_turns=2, max_chars=100000)
    assert len(out) <= 4


def test_trim_history_by_chars():
    msgs = [{"role": "user", "content": "x" * 1000}] * 5
    out = trim_history(msgs, max_turns=50, max_chars=1500)
    assert sum(len(m["content"]) for m in out) <= 1500

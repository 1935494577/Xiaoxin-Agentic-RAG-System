"""Step 2: embedding history prune tests."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent.conversation.history_prune import prune_history_by_embedding  # noqa: E402


def _mock_embed(texts):
    """Deterministic vectors for cosine tests."""
    out = []
    for t in texts:
        if "天气" in t:
            out.append([1.0, 0.0, 0.0])
        elif "阅读" in t or "超脑" in t:
            out.append([0.0, 1.0, 0.0])
        elif "训练" in t or "继续" in t:
            out.append([0.0, 0.92, 0.08])
        else:
            out.append([0.33, 0.33, 0.34])
    return out


@patch("agent.conversation.history_prune.embed_texts", side_effect=_mock_embed)
def test_prune_keeps_relevant_turns(mock_embed):
    history = [
        {"role": "user", "content": "超脑阅读要求是什么？"},
        {"role": "assistant", "content": "要求包括…"},
        {"role": "user", "content": "今天北京天气怎么样？"},
        {"role": "assistant", "content": "晴…"},
    ]
    out = prune_history_by_embedding(
        "继续说说阅读训练",
        history,
        min_similarity=0.5,
        max_turns=4,
    )
    user_contents = [m["content"] for m in out if m["role"] == "user"]
    assert any("阅读" in c or "超脑" in c for c in user_contents)
    assert not any("天气" in c for c in user_contents)


@patch("agent.conversation.history_prune.embed_texts", side_effect=_mock_embed)
def test_prune_empty_history(mock_embed):
    assert prune_history_by_embedding("q", [], min_similarity=0.3, max_turns=3) == []

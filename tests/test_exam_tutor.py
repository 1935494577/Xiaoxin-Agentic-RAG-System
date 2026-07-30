"""TDD: LLM explain for chat exam questions."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_explain_question_by_id_acl(tmp_path, monkeypatch):
    from exam_bank import store
    from exam_bank.exam_tutor import explain_question_by_id

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()
    col = store.create_collection(
        name="私库",
        subject="数学",
        grade="高三",
        region="浙江",
        visibility="private",
        owner_user_id="alice",
    )
    q = store.create_question(
        collection_id=col["id"],
        qtype="choice",
        stem="1+1=?",
        options=["A. 1", "B. 2"],
        answer="B",
        quality_status="published",
    )

    denied = explain_question_by_id(q["id"], user_answer="A", reader_user_id="bob")
    assert denied["ok"] is False
    assert denied["error"] == "forbidden"


def test_explain_question_with_llm_parses_json():
    from exam_bank.exam_tutor import explain_question_with_llm

    fake_resp = MagicMock()
    fake_resp.choices = [
        MagicMock(
            message=MagicMock(
                content='{"explanation":"因为 $1+1=2$","is_correct":false,"score_hint":"选错了","key_points":["加法"]}'
            )
        )
    ]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = fake_resp

    with patch("exam_bank.llm_client.build_openai_client", return_value=(mock_client, {"chat_model": "m"})):
        out = explain_question_with_llm(
            {"id": "q1", "qtype": "choice", "stem": "1+1=?", "options": ["A. 1", "B. 2"], "answer": "B"},
            user_answer="A",
        )

    assert out["ok"] is True
    assert "1+1=2" in out["explanation"]
    assert out["is_correct"] is False
    assert out["key_points"] == ["加法"]


def test_explain_question_by_id_success(tmp_path, monkeypatch):
    from exam_bank import store
    from exam_bank.exam_tutor import explain_question_by_id

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()
    col = store.create_collection(name="公开", subject="数学", grade="高三", region="全国")
    q = store.create_question(
        collection_id=col["id"],
        qtype="fill",
        stem="填空",
        options=[],
        answer="2",
        quality_status="published",
    )

    fake_resp = MagicMock()
    fake_resp.choices = [
        MagicMock(message=MagicMock(content='{"explanation":"答案是 2","is_correct":null,"score_hint":"","key_points":[]}'))
    ]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = fake_resp

    with patch("exam_bank.llm_client.build_openai_client", return_value=(mock_client, {"chat_model": "m"})):
        out = explain_question_by_id(q["id"], user_answer="二", reader_user_id="u1")

    assert out["ok"] is True
    assert out["explanation"] == "答案是 2"
    assert out["qtype"] == "fill"

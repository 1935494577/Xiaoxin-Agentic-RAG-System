"""TDD: chat-facing exam paper view + attempt grading (objective items)."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _seed(store):
    col = store.create_collection(
        name="浙江·数学·高三", subject="数学", grade="高三", region="浙江"
    )
    q1 = store.create_question(
        collection_id=col["id"],
        qtype="choice",
        stem=r"若 $\vec{a}\perp\vec{b}$，则 $x=$",
        options=["A. 0", "B. 1", "C. 2", "D. -1"],
        answer="A",
        analysis="垂直则点积为 0",
        quality_status="published",
        question_no="1",
    )
    q2 = store.create_question(
        collection_id=col["id"],
        qtype="choice",
        stem=r"复数 $\bar{z}=$",
        options=["A. $1-i$", "B. $1+i$", "C. $-1$", "D. $i$"],
        answer="A",
        analysis="共轭",
        quality_status="published",
        question_no="2",
    )
    q3 = store.create_question(
        collection_id=col["id"],
        qtype="fill",
        stem="填空：$1+1=$",
        options=[],
        answer="2",
        analysis="",
        quality_status="published",
        question_no="3",
    )
    sp = store.create_source_paper(
        collection_id=col["id"],
        title="2024 样卷",
        source_filename="sample.docx",
        question_ids=[q1["id"], q2["id"], q3["id"]],
    )
    for q in (q1, q2, q3):
        store.update_question(q["id"], source_paper_id=sp["id"])
    return col, sp, q1, q2, q3


def test_build_chat_paper_hides_answers(tmp_path, monkeypatch):
    from exam_bank import store
    from exam_bank.chat_paper import build_chat_paper

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()
    _, sp, q1, _, _ = _seed(store)

    paper = build_chat_paper(sp["id"], include_answers=False)
    assert paper["ok"] is True
    assert paper["type"] == "exam_paper"
    assert paper["title"] == "2024 样卷"
    assert paper["meta"]["question_count"] == 3
    assert paper["mode"] == "preview"
    flat = [it for sec in paper["sections"] for it in sec["items"]]
    assert len(flat) == 3
    assert flat[0]["id"] == q1["id"]
    assert "answer" not in flat[0] or flat[0].get("answer") in ("", None)
    assert not flat[0].get("analysis")


def test_start_and_submit_attempt_grades_choice(tmp_path, monkeypatch):
    from exam_bank import store
    from exam_bank.chat_paper import (
        build_chat_paper,
        start_attempt,
        submit_attempt,
    )

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()
    _, sp, q1, q2, q3 = _seed(store)

    started = start_attempt(sp["id"], user_id="u1")
    assert started["ok"] is True
    aid = started["attempt_id"]
    assert started["status"] == "in_progress"

    result = submit_attempt(
        aid,
        answers={q1["id"]: "A", q2["id"]: "B", q3["id"]: "2"},
    )
    assert result["ok"] is True
    assert result["status"] == "submitted"
    # 2 choice + 1 fill correct except q2 wrong → score 2/3 objective
    assert result["correct_count"] == 2
    assert result["graded_count"] == 3
    by_id = {r["question_id"]: r for r in result["results"]}
    assert by_id[q1["id"]]["correct"] is True
    assert by_id[q2["id"]]["correct"] is False
    assert by_id[q3["id"]]["correct"] is True
    # reveal answers after submit
    assert by_id[q1["id"]]["answer"] == "A"

    paper = build_chat_paper(sp["id"], include_answers=False)
    assert paper["mode"] == "preview"


def test_grade_normalizes_choice_letter(tmp_path, monkeypatch):
    from exam_bank.chat_paper import normalize_objective_answer

    assert normalize_objective_answer("A. 0", "choice") == "A"
    assert normalize_objective_answer("a", "choice") == "A"
    assert normalize_objective_answer(" 2 ", "fill") == "2"

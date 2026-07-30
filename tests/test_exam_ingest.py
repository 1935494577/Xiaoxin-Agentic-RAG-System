"""TDD: exam paper ingest split / commit / apply-answers."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


SAMPLE_PAPER = """一、选择题
1. 下列正确的是
A. 1
B. 2
C. 3
D. 4
2. 另一题
A. 甲
B. 乙
二、填空题
3. 填空：____
"""

SAMPLE_ANSWERS = """1. A
2. B
3. 答案内容
"""


def test_split_items_rules():
    from exam_bank.item_split import split_items_rules

    items = split_items_rules(SAMPLE_PAPER)
    assert len(items) >= 3
    assert items[0]["question_no"] == "1"
    assert items[0]["qtype"] == "choice"
    assert any(o.startswith("A") for o in items[0]["options"])
    assert items[2]["question_no"] == "3"
    assert items[2]["qtype"] == "fill"


ENGLISH_GAOKAO_FRAGMENT = """
注意事项：答题前请认真阅读
第一部分 听力(共两节，满分30分)
第一节(共5小题)
1. What will the speakers do next?
A. Pack bags. B. Gas up their car. C. Get into a taxi.
选出最佳选项。听完后各小题将给出5秒钟 第二部分 阅读(共两节，满分50分)
21. What is the main idea of the passage?
A. Travel. B. Study. C. Work. D. Sports.
第三部分 语言运用(共两节，满分30分)
第一节(共15小题)
41. A. contributed B. generated C. transformed D. shared
第二节(共10小题；每小题1.5分，满分15分)
阅读下面短文，在空白处填入1个适当的单词或括号内单词的正确形式。
56. The policemen were very kind.
第四部分 写作(共两节，满分40分)
第一节(满分15分)
57. 假定你是李华，写作词数应为80个左右。
Dear Tom,
"""


def test_english_part_sections_keep_listening_reading_cloze_writing():
    """高考英语「第X部分」须映射到听力/阅读/完形/语法填空/写作，不能全变成 choice。"""
    from exam_bank.item_split import split_items_rules
    from exam_bank.section_detect import detect_sections_rules

    secs = detect_sections_rules(ENGLISH_GAOKAO_FRAGMENT, subject="英语")
    qtypes = [s["qtype"] for s in secs]
    assert "listening" in qtypes
    assert "reading" in qtypes
    assert "writing" in qtypes

    items = split_items_rules(ENGLISH_GAOKAO_FRAGMENT, subject="英语")
    by_no = {it["question_no"]: it["qtype"] for it in items}
    assert by_no.get("1") == "listening"
    assert by_no.get("21") == "reading"
    assert by_no.get("41") == "cloze"
    assert by_no.get("56") == "fill"
    assert by_no.get("57") == "writing"
    # 注意里的「1.写作词数」不得抢占听力第1题题号
    assert sum(1 for it in items if it["question_no"] == "1") == 1


def test_math_numbered_subquestion_does_not_reset_section_to_other():
    """「19.（1）设函数…」不得覆盖「三、解答题」节题型。"""
    from exam_bank.item_split import split_items_rules

    text = """一、选择题
1. 下列正确的是
A. 1
B. 2
C. 3
D. 4
二、填空题
2. 填____
三、解答题
3.（15分）已知函数 f(x)=x。
（Ⅰ）求 f(1)
19.（1）设函数 g(x)=x，求 g(2)
20.（15分）已知等比数列
"""
    items = split_items_rules(text, subject="数学")
    by_no = {it["question_no"]: it["qtype"] for it in items}
    assert by_no.get("1") == "choice"
    assert by_no.get("2") == "fill"
    assert by_no.get("3") == "short"
    assert by_no.get("19") == "short"
    assert by_no.get("20") == "short"


def test_parse_answer_key():
    from exam_bank.item_split import parse_answer_key

    m = parse_answer_key(SAMPLE_ANSWERS)
    assert m["1"] == "A"
    assert m["2"] == "B"
    assert m["3"] == "答案内容"


def test_commit_and_apply_answers(tmp_path, monkeypatch):
    from exam_bank import store
    from exam_bank.item_split import parse_answer_key, split_items_rules

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()

    col = store.create_collection(name="库", subject="数学", grade="初二", region="浙江")
    items = split_items_rules(SAMPLE_PAPER)
    created = []
    for it in items:
        q = store.create_question(
            collection_id=col["id"],
            qtype=it["qtype"],
            stem=it["stem"],
            options=it["options"],
            quality_status="draft",
            question_no=it["question_no"],
        )
        created.append(q)
    sp = store.create_source_paper(
        collection_id=col["id"],
        title="样卷",
        raw_text=SAMPLE_PAPER,
        question_ids=[q["id"] for q in created],
    )
    for q in created:
        store.update_question(q["id"], source_paper_id=sp["id"])

    mapping = parse_answer_key(SAMPLE_ANSWERS)
    unmatched = []
    for q in created:
        ans = mapping.get(q["question_no"])
        if ans is None:
            unmatched.append(q["question_no"])
            continue
        store.update_question(q["id"], answer=ans)
    store.update_source_paper(sp["id"], answer_text=SAMPLE_ANSWERS)

    q1 = store.get_question(created[0]["id"])
    assert q1["answer"] == "A"
    assert unmatched == []
    sp2 = store.get_source_paper(sp["id"])
    assert "1. A" in sp2["answer_text"]

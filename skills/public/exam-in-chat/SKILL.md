---
name: exam-in-chat
description: Use when the user wants to view a formal exam paper, take a practice test, ask what is in the exam bank (题库), or start answering questions in chat (e.g. 题库里有什么、做试卷、开始答题、标准卷面、模拟考、把某某卷拿出来). Prefer structured exam_paper UI / list_exam_bank over knowledge-base document lists.
allowed-tools:
  - list_exam_bank
  - search_exam_papers
  - present_exam_paper
  - kb_search
---

# Exam in Chat Skill

## Critical: 题库 ≠ 知识库

| 用户说 | 正确工具 | 禁止 |
|--------|----------|------|
| 题库里有什么 / 有哪些试卷 | `list_exam_bank` | `list_kb_sources`、把 PDF 当题库 |
| 把某某卷拿出来做 | `search_exam_papers` → `present_exam_paper` | 用知识库长文冒充卷面 |
| 制度/手册/某本书讲什么 | `kb_search` / `list_kb_sources` | 题库工具 |

## When to activate

- User asks **what is in 题库 / 试卷题库**
- User asks to **do / take / start** an exam or practice paper in the chat
- User wants a **standard exam layout** (卷面) rather than a text summary
- User refers to a paper by title/year (e.g. 2024 新课标 I 卷)

## When NOT to activate

- Ordinary Q&A about a single concept or one question's solution → use `kb_search` only
- Admin组卷 / 导出 Word — point them to `/admin/exam-bank` instead

## Workflow — inventory

1. Call `list_exam_bank`.
2. Present collections + papers from the tool JSON; say clearly this is **试卷题库**, not 知识库.
3. If empty — guide to Admin **数据入库 → 试卷题库**; do **not** fall back to `list_kb_sources`.

## Workflow — take exam

1. Call `search_exam_papers` with keywords from the user (year / title / subject).
2. **0 hits** — tell them to use Admin **数据入库 → 试卷题库**；do **not** invent a paper from KB chunks.
3. **1 hit** — call `present_exam_paper` with that `source_paper_id`; paste the `exam_paper` fence from the tool hint verbatim; tell the user to click **开始答题**.
4. **Multiple hits** — list title + id; ask the user to pick. Optionally include:

````markdown
```exam_candidates
{"items":[{"id":"...","title":"..."}]}
```
````

   Do not call `present_exam_paper` until the user chooses (or there is exactly one match).
5. Math you write yourself must use `$...$` / `$$...$$` delimiters.

## Hard rules

- Never paste a full knowledge-base chunk as a fake interactive paper.
- Never answer 「题库有什么」 with knowledge-base document lists.
- Never reveal answers before the user submits.
- Ordinary handbook/policy questions: do **not** call exam tools.

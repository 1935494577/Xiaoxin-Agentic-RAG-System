"""Detect chat intents that should query the exam bank (not KB)."""

from __future__ import annotations

import re

# Strong: user wants to take / open a paper
_TAKE_PAT = re.compile(
    r"(拿出来|拿来|打开|调出|调出来|开始做|做一下|做一做|给我做|我要做|去做|"
    r"开始答题|模拟考|练习一下|做卷|做题|答卷|开卷)",
    re.I,
)
_PAPER_PAT = re.compile(
    r"(试卷|卷子|真题|高考卷|模拟卷|练习卷|新课标|课标卷|期末卷|月考|"
    r"考试卷|试题|source_paper)",
    re.I,
)
_EXAM_WORD = re.compile(r"(高考|中考|会考|联考|模考)", re.I)

# Noise to strip when building search keywords
_STOP = re.compile(
    r"(将|把|请|帮我|给我|我想|我要|可以|一下|一下啊|喵|主人|"
    r"拿出来|拿来|打开|调出|调出来|开始做|做一下|做一做|去做|开始答题|"
    r"做卷|做题|答卷|开卷|入库的|已经入库|题库里的|题库中的|"
    r"的|了|吧|呢|啊|呀|么|吗|下)"
)


def is_exam_take_intent(text: str) -> bool:
    """True when the user likely wants an interactive exam paper from exam_bank."""
    s = (text or "").strip()
    if not s:
        return False
    if _TAKE_PAT.search(s) and (_PAPER_PAT.search(s) or _EXAM_WORD.search(s)):
        return True
    if re.search(r"(做|答).{0,6}(卷|题)", s) and (_PAPER_PAT.search(s) or _EXAM_WORD.search(s)):
        return True
    # 题库 + 拿出来做 + 卷/题（如「把题库里的浙江卷拿出来做」）
    if (
        _TAKE_PAT.search(s)
        and re.search(r"(题库|试卷题库)", s)
        and re.search(r"(卷|试题|真题)", s)
    ):
        return True
    if re.search(r"(标准卷面|开始答题)", s):
        return True
    return False


_BANK_WORD = re.compile(r"(题库|试卷题库|试题库)")
_INVENTORY_ASK = re.compile(
    r"(有什么|有哪些|有几|内容|概况|清单|目录|看看|查看|展示|列出|盘点|统计|多少|收录)"
)
_KB_ONLY = re.compile(r"(知识库|知识文档|向量库)")


def is_exam_inventory_intent(text: str) -> bool:
    """True when the user asks what is in the exam bank (not the knowledge base)."""
    s = (text or "").strip()
    if not s:
        return False
    # Taking a paper takes precedence over inventory listing
    if is_exam_take_intent(s):
        return False
    # Pure KB questions
    if _KB_ONLY.search(s) and not _BANK_WORD.search(s):
        return False
    if _BANK_WORD.search(s) and _INVENTORY_ASK.search(s):
        return True
    if re.search(r"(有哪些|有什么|列出).{0,10}(试卷|卷子|真题)", s):
        return True
    if re.search(r"(试卷|卷子|真题).{0,10}(有哪些|有什么|清单|目录)", s):
        return True
    return False


def extract_exam_search_query(text: str) -> str:
    """Derive LIKE keywords from a natural-language take-exam request."""
    s = (text or "").strip()
    # Prefer year tokens
    years = re.findall(r"20\d{2}", s)
    # Keep CJK / alnum runs after stripping stop phrases iteratively
    cur = s
    for _ in range(4):
        nxt = _STOP.sub(" ", cur)
        if nxt == cur:
            break
        cur = nxt
    cur = re.sub(r"[^\w\u4e00-\u9fff]+", " ", cur, flags=re.UNICODE)
    parts = [p for p in cur.split() if len(p) >= 1 and p.lower() not in {"vol", "pdf", "docx"}]
    # Drop ultra-generic leftovers
    parts = [p for p in parts if p not in {"卷", "卷子", "试卷", "试题", "题", "做"}]
    if years:
        for y in years:
            if y not in parts:
                parts.insert(0, y)
    q = " ".join(parts[:8]).strip()
    return q or (years[0] if years else "")

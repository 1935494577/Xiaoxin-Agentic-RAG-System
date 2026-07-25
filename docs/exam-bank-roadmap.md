# 题库产品路线 — P0～P4 实施清单

> 对应产品目标：**精选真题入库 → 按难度配比组卷 → 一键导出 →（远期）教案**  
> 原则：默认全自动、少选项；权限在库不在卷；每步自检闭环后再进下一步。

| 阶段 | 目标 | 验收闭环 |
|------|------|----------|
| **P0** | 入库可靠 | LLM 状态可查；失败明确报错；入库即为 published 可组卷；正式卷面导出 | ✅ |
| **P1** | 一句话组卷 | NL → `by_qtype`/`by_qtype_band` → 预览 + 导出 | ✅ |
| **P2** | 难度/标签自动化 | 拆题带 difficulty + knowledge_tags；组卷可按标签筛 | ✅ |
| **P3** | 检索增强 | `q` 搜题干/标签；管理页可搜 | ✅ |
| **P4** | 教案 MVP | 已组试卷 → 教案大纲 Markdown | ✅ |
| **UX v3** | 智能组卷（学科网形态） | 左知识点 + 01/02/03 + 右预览；库存 `by_tag`/`regions`/`years`；`regions_any`/`years_any` | ✅ |
| **UX v3.2** | 元数据闭环 | 入库写 region/year/chapter；左栏章节\|知识点 Tab；地区省市列表；年份近3/5年；三板块可折叠 | ✅ |
| **UX v3.3** | 地区建库 + 试题篮 | 地区×学科×年级独立库；组卷题卡/试题篮/放大卷面；`from-questions` 定稿；见 `exam-bank-basket.md` | ✅ |
| **Arch 11** | 对齐 11.txt 改造 | 改造建议书；字段 difficulty_coef/cognitive_level；`auto-generate`+soft_fallback；可选 OCR deps；orchestrator | ✅ |
| **UX 交互层** | 最优路径 P1 | 难度系数滑块→`difficulty_target_coef`；ECharts 组卷看板；`POST /questions/swap` 智能换题；题干 KaTeX | ✅ |
| **UX 图二布局** | 大屏组卷 | 宽屏三栏；02 旁难度配比表联动易/中/难拆分；底部固定「生成试卷」 | ✅ |
| **金标入库** | 清洗+公式不丢 | DOCX `[[EQ]]`；`/ingest/clean`；规则 19 题金标；fixtures + `ingest_gold_exam_papers.py` | ✅ |
| **全库批入库** | 路径元数据建库 | `corpus_meta` 地区/年级/学科/卷种；去重优先解析卷；`ingest_all_exam_papers.py`；库存 `by_qtype_year` | ✅ |
| **UX v3.1** | 筛选后实时库存 + 场景建议题量 | inventory 支持 tag/region/year；03「库内」随筛选变；「填入建议题量」 | ✅ |

状态在本文与 `exam-bank-issues.md` 同步更新。

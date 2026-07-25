# 题库试卷入库 — 删除 · 导入 · 编辑 · 答案关联

> **状态**：已落地（CRUD + **清洗 + DOCX 公式占位** + 大模型/规则拆题 + 答案按题号写入）  
> **API 总览**：[`exam-bank-api.md`](./exam-bank-api.md)  
> **问题记录**：[`exam-bank-issues.md`](./exam-bank-issues.md)  
> **金标样卷**：`tests/fixtures/exam_papers/`（2022–2025 新课标数学）；脚本 `scripts/ingest_gold_exam_papers.py`

---

## 1. 目标闭环

| # | 环节 | 验收 |
|---|------|------|
| 1 | 删除 | 可删题目；可删题库（级联题目） |
| 2 | 抽取 | DOCX MathType/OLE → `[[EQ:n]]` + `exam_media/`，不丢选项槽位 |
| 3 | 清洗 | 去注意事项/绝密页眉；切开粘连选项 |
| 4 | 导入 | PDF / DOCX / 粘贴 → LLM 或 **规则精准拆题** |
| 5 | 预览入库 | 勾选草案（选项数 / EQ / 答案）→ commit |
| 6 | 答案 | 卷内 `【答案】【解析】` 自动写入；否则 apply-answers |

不做：扫描件 OCR→可编辑 LaTeX、全库 195 份批跑（管道可扩）。

**扫描件 OCR（可选）**：本地 PaddleOCR，**不依赖扫描王**。见下文 §3 OCR。

---

## 1.0 清洗与公式占位（金标逆向）

高考 Word 卷公式多为 **MathType OLE + WMF**。模块：`docx_extract.py`、`paper_clean.py`；`parse_paper_items(..., clean=True)`。金标：**19 题**、选择 4 选项、解析卷 `answers_embedded`。

```bash
set PYTHONPATH=enterprise_rag/src
python scripts/ingest_gold_exam_papers.py
```

---

## 1.1 LLM 拆题（默认开启）

| 能力 | 说明 |
|------|------|
| 过滤噪声 | 清洗层 + LLM；前端可「规则精准拆题」 |
| 题型 | 含 `multi` 多选 |
| 答案 | 【答案】/【解析】嵌入；`answers_embedded` |
| 回退 | LLM 失败明确报错；规则路径不拆注意事项 |

实现：`exam_bank/llm_ingest.py`；入口 `parse_paper_items(..., use_llm=True, clean=True)`。

---

## 2. 数据：`source_papers`

| 字段 | 说明 |
|------|------|
| id | uuid |
| collection_id | 所属题库 |
| title / source_filename | 展示名 / 上传文件名 |
| raw_text | 试卷正文（可含 `[[EQ:n]]`） |
| answer_text | 关联答案卷 |
| question_ids_json | 本卷题目 id 有序列表 |

公式媒体：`enterprise_rag/data/exam_media/{ingest_id}/`；`GET /api/exam/ingest/media/{ingest_id}/{filename}`。

---

## 3. API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/exam/ingest/clean` | `{ text }` → cleaned + warnings |
| POST | `/api/exam/ingest/parse` | `{ text, clean?, use_llm? }` → items + cleaned_text |
| POST | `/api/exam/ingest/upload` | DOCX 公式抽取 → clean → parse；media[] |
| GET | `/api/exam/ingest/ocr/status` | OCR 可选依赖是否就绪 |
| POST | `/api/exam/ingest/ocr` | 扫描 PDF/图片 → PaddleOCR → clean → parse |
| GET | `/api/exam/ingest/media/{ingest_id}/{filename}` | 公式/插图 |
| POST | `/api/exam/ingest/commit` | 批量入库 |
| POST | `/api/exam/ingest/apply-answers` | 按题号写 answer |

### 3.1 OCR 扫描件（可选依赖）

```bash
pip install -r requirements-exam-optional.txt
# 重启后端后：题库入库页 →「OCR 扫描件入库」
# 或 GET /api/exam/ingest/ocr/status 确认 available=true
```

| 项 | 说明 |
|----|------|
| 引擎 | `exam_bank/ocr_ingest.py`：**PaddleOCR** + pypdfium2 渲页；版面+公式用 `paper_structure_parse`（PP-StructureV3 + LaTeX_OCR_rec） |
| 格式 | `.pdf` / `.png` / `.jpg` / `.webp` / `.tif` / `.bmp` |
| 未安装 | API 返回 **503** + 安装提示；文本 PDF/DOCX 仍走 `/ingest/upload` |
| 版面 | 按框坐标近似阅读序（同行左→右）；双栏扫描仍可能串行，可再人工改预览 |

其余 CRUD 见 [`exam-bank-api.md`](./exam-bank-api.md)。

---

## 4. 拆题策略

1. 清洗：`paper_clean`（注意事项、粘连选项）
2. 规则：行首大题号 `1.`（不拆 `(1)`）；节标题推题型；嵌入【答案】【解析】
3. DOCX：`docx_extract` 公式占位
4. 可选 LLM：结构化 JSON items

---

## 5. Admin UI

导入步：**预览清洗** / **规则精准拆题** / 智能拆题 / **OCR 扫描件入库**；清洗前后对照；预览显示选项数与公式占位。

---

## 6. TDD

- `tests/test_exam_ingest.py`
- `tests/test_exam_paper_clean.py`
- `tests/test_exam_gold_gaokao_math.py`
- `tests/test_exam_docx_extract.py`

# 智能组卷 / 教案 — 改造建议书（对齐 11.txt）

> 依据：`11.txt` 三阶段方案 + 本仓现有 `exam_bank` / DeerFlow 规范  
> 原则：**平滑扩展、禁止平行 Agent 架构**；商业题库不抓取。

---

## 1. 现状（自动识别技术栈）

| 层 | 现状 |
|----|------|
| 后端 | FastAPI + SQLite（`exam_bank`）+ LangChain/LangGraph（RAG 主链） |
| 前端 | React + 自有 UI；已有 **ECharts** |
| 入库 | PDF/DOCX/文本 → LLM 拆题 → `questions` / `source_papers` |
| 组卷 | 规则抽题 + NL 组卷 + 试题篮 + 教案大纲 MVP |
| Agent | **须走 DeerFlow**（`docs/deerflow-integration.md`），勿自研 Orchestrator 中间件链 |

### 1.1 表字段缺口（相对 11.txt）

| 字段 | 现状 | 建议 |
|------|------|------|
| `region` | ✅ 题库+题目 | 保持；库级锁定 |
| `difficulty` 1–5 | ✅ | 保留 |
| `difficulty_coef` 0–1 | ❌ | **新增**；滑块/预估均分用 |
| `cognitive_level` | ❌ | **新增** memory/apply/create |
| `discrimination` | ❌ | **新增** 0–1 区分度（可先空） |
| `textbook_version` | ❌ | **新增** 如人教A版 |
| `chapter` / `year` / tags | ✅ | 已有 |

### 1.2 智能体接入层（回答 Prompt 1）

**不要**在 Controller 里堆 LLM，也**不要**另起一套 Middleware。

推荐分层：

```
API (exam_router)
  → exam_bank.orchestrator  （领域编排：调用现有 service，可选发 DeerFlow tool）
      → item_split / llm_ingest / assemble / lesson /（远期）ocr_preprocess
```

- 日常组卷：同步走 `orchestrator.auto_generate`（本仓 Service）。
- 复杂多步（OCR+知识点图谱+教案长文）：注册为 **DeerFlow community tools**，由 `make_lead_agent` 调度。

### 1.3 前端应预留的 API

| 接口 | 状态 | 说明 |
|------|------|------|
| `POST /api/exam/papers/assemble` | ✅ | 硬约束组卷 |
| `POST /api/exam/papers/assemble-nl` | ✅ | 指令即组卷（规则 NL） |
| `POST /api/exam/papers/auto-generate` | **新增别名** | 对齐 11.txt：支持 soft_fallback |
| `POST /api/exam/papers/{id}/lesson` | ✅ | 教案大纲 |
| `POST /api/exam/papers/from-questions` | ✅ | 试题篮定稿 |
| `GET /api/exam/inventory` | ✅ | 库存看板数据源 |
| 流式 SSE `/papers/auto-generate/stream` | ⏳ 阶段二 | 逐题渲染 |
| `POST /api/exam/ingest/ocr` | ✅ | PaddleOCR 可选；`GET .../ocr/status` |

---

## 2. 分阶段落地（对 11.txt）

### 阶段一：智能预处理与入库

| 项 | 路径 |
|----|------|
| 文本 PDF/DOCX | 已有 `document_loader` + `llm_ingest` |
| 扫描件 OCR | **可选依赖** PaddleOCR / PP-StructureV3 + LaTeXOCR + pypdfium2；`POST /api/exam/ingest/ocr`；结构化见 `paper_structure_parse` |
| 结构化 JSON | 已有；补 `difficulty_coef` / `cognitive_level` |
| 跨页拼接 | 中期：版面分析服务（TextIn / 云 OCR）作适配器，不绑死一家 |

### 阶段二：智能引擎

| 项 | 路径 |
|----|------|
| 指令组卷 | 增强 `nl_assemble` + `soft_fallback`（已做兜底） |
| 教案 | 规则大纲 ✅；LLM 长教案 → DeerFlow tool / 现有 chat 模型异步 |
| 遗传算法/强化学习 | **暂缓**；先兜底+标签矩阵，再评估 GA |

### 阶段三：交互与性能

| 项 | 路径 | 状态 |
|----|------|------|
| 难度滑块 / 雷达图 / 预估均分 | 组卷页滑块→`difficulty_target_coef`；`ExamAssembleDashboard`（ECharts） | ✅ |
| 换一题 | `POST /api/exam/questions/swap` + 题卡弹窗 | ✅ |
| 题干 KaTeX | `ExamMathText`（`katex`） | ✅ |
| Redis 缓存热门库存 | 已有 `redis` 依赖；加 `exam_bank/cache.py` 适配 | 下一迭代 |
| 流式出题 | SSE，阶段二 | 下一迭代 |

---

## 3. 依赖清单

### 已有（勿重复装）

`fastapi`、`langchain*`、`langgraph`、`python-docx`、`pdfplumber`、`reportlab`、`redis`、`httpx`、前端 `echarts`

### 核心保留

见根目录 `requirements.txt`。

### 题库可选（扫描 OCR / 公式）

见 `requirements-exam-optional.txt`：

- `paddlepaddle` + `paddleocr[doc-parser]` + `pypdfium2` + `python-docx`（PP-StructureV3 / LaTeXOCR）
- （可选）`paddleocr` / `pymupdf` 作回退

### 前端（交互层已落地）

- `katex`：`ExamMathText` 渲染题干/选项/答案
- `echarts` / `echarts-for-react`：组卷分析看板（知识点雷达、难度、题型）

### 明确不做 / 延后

- 腾讯云 ADP / Coze 作为主编排（与 DeerFlow 冲突）
- 抓取学科网题库
- 大规模换 Ant Design（保持现有组件）

---

## 4. 全局硬约束（写入实现）

1. LLM 调用一律 async 友好（长任务不阻塞事件循环；同步包装放线程池）。
2. 公式目标格式 LaTeX；导出 Word 继续 `python-docx`（MathType 后期）。
3. 不改 User 权限模块；题库沿用 collection `visibility` / `owner_user_id`。
4. Agent 扩展只注册 DeerFlow tools，不新建平行 middleware。

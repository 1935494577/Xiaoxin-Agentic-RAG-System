# 题库 / 组卷子系统 — API 实施文档

> **状态**：MVP + v2 组卷增强（学科题型 / 卷面识别 / 难度档 / 缺题型提示）  
> **分支**：`feature/exam-bank-mvp`  
> **v2 细则**：[`exam-bank-assemble-v2.md`](./exam-bank-assemble-v2.md)  
> **原则**：本 monorepo 内独立模块；数据与 Chat 热路径隔离；TDD；问题写入 [`exam-bank-issues.md`](./exam-bank-issues.md) 再按记录修复。  
> **场景**：与业务场景分类绑定（`scene_preset` / Admin 场景页），不是孤立功能点。

---

## 0. 目标闭环（Definition of Done）

端到端必须全部打通，缺一不可：

| # | 闭环环节 | 验收 |
|---|----------|------|
| 1 | **场景分类** | 存在 `exam_*` 场景预设；Admin/对话设置可选 |
| 2 | **题库空间** | 按学科/年级/地区建 `collection` |
| 3 | **录题** | API + Admin 创建题目（题型/难度/知识点） |
| 4 | **筛选** | 按 collection + qtype + difficulty + tags 列表 |
| 5 | **组卷** | 按学科题型多选配比 + 可选难度档；缺题型提示「没有相应题型」 |
| 5b | **卷面识别** | `detect-sections` 识别「一、选择题」等（规则优先，LLM 可开） |
| 6 | **导出** | Markdown / Word(docx) / PDF 可选；题干+答案解析可开关 |
| 7 | **隔离** | 独立 SQLite；`/api/exam/*`；Chat 默认不读写题库 |
| 8 | **测试** | store / assemble / API 契约测试绿 |
| 9 | **文档** | 本文 + 问题记录 + README / 项目说明更新 |

**后续阶段（本闭环之后）**：教案生成、向量相似题、爬虫语料库。  
扫描件 OCR 已落地（可选依赖）：`POST /api/exam/ingest/ocr` + `GET /api/exam/ingest/ocr/status`。  
**试卷入库（PDF/DOCX/答案关联）**：见 [`exam-bank-ingest.md`](./exam-bank-ingest.md)。

---

## 1. 架构与隔离

```text
┌──────────────────────────────────────────────────────────┐
│ Jnao 壳：Auth / Admin / scene_preset / LLM 配置            │
├────────────────────────────┬─────────────────────────────┤
│ RAG Chat（现有）            │ exam_bank（本子系统）         │
│ /chat*  · 向量切块          │ /api/exam/* · 题级 SQLite     │
│ 默认不访问 exam_bank.db     │ 不写 Milvus 主索引            │
└────────────────────────────┴─────────────────────────────┘
```

| 项 | 约定 |
|----|------|
| 代码包 | `enterprise_rag/src/exam_bank/` |
| DB | `enterprise_rag/data/exam_bank.db`（`settings.exam_bank_db_path`） |
| API 前缀 | `/api/exam` |
| 租户 | `tenant_id` 默认 `internal`（与反馈一致） |
| 前端 | `/admin/exam-bank` |

---

## 2. 场景分类（必须结合）

| scene_preset id | 标签 | 用途 | UI / Chat 行为建议 |
|-----------------|------|------|-------------------|
| `exam_assemble` | 题库组卷 | 按约束出卷 | 默认知识模式关闭工具干扰；Admin 进题库页 |
| `exam_lesson` | 教案备课 | 挂题写教案（Phase 2） | 预留 |
| `exam_ingest` | 试卷入库 | 解析审核（Phase 2） | 预留 |

MVP 落地：`exam_assemble` 写入 `scene_presets.py`，并在场景目录/Admin 可见。

场景与数据维度：

```text
scene: exam_assemble
  → 操作对象: collection（subject × grade × region）
  → 动作: list questions → assemble → export (markdown|docx|pdf)
```

---

## 3. 数据模型

### 3.1 collections

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | uuid |
| tenant_id | TEXT | 默认 internal |
| name | TEXT | 展示名 |
| subject | TEXT | 学科 |
| grade | TEXT | 年级 |
| region | TEXT | 地区侧重点 |
| description | TEXT | 可选 |
| created_at / updated_at | TEXT ISO | |

### 3.2 questions

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | |
| collection_id | TEXT FK | |
| tenant_id | TEXT | |
| qtype | TEXT | `choice` \| `fill` \| `short` \| `calc` \| `other` |
| difficulty | INTEGER | 1–5 |
| stem | TEXT | 题干 |
| options_json | TEXT | JSON 数组，选择题用 |
| answer | TEXT | |
| analysis | TEXT | 解析 |
| knowledge_tags | TEXT | JSON 字符串数组 |
| region / year / subject / grade | TEXT | 可冗余便于筛选 |
| quality_status | TEXT | `draft` \| `published` |
| content_hash | TEXT | 去重 |
| created_at / updated_at | TEXT | |

组卷默认只抽 `quality_status=published`。

### 3.3 paper_jobs（组卷快照）

| 字段 | 说明 |
|------|------|
| id, collection_id, tenant_id | |
| title | 试卷标题 |
| spec_json | 组卷约束原文 |
| question_ids_json | 抽中题序 |
| markdown | 导出正文 |
| created_at | |

---

## 4. API 契约

Base：`/api/exam`  
鉴权：与现有 Admin API 一致（Session / Admin Role，沿用中间件）。

### 4.1 Health / 元数据

```http
GET /api/exam/meta
```

响应：

```json
{
  "available": true,
  "db_path": "...",
  "qtypes": ["choice", "fill", "short", "calc", "other"],
  "difficulty_min": 1,
  "difficulty_max": 5,
  "scene_presets": ["exam_assemble", "exam_lesson", "exam_ingest"]
}
```

### 4.2 Collections

```http
POST   /api/exam/collections
GET    /api/exam/collections?tenant_id=internal&reader_user_id=
GET    /api/exam/collections/{id}
DELETE /api/exam/collections/{id}   # 级联删除题目
# 创建同名冲突（同租户×学科×年级；私有按 owner 互斥）→ 409 collection_name_conflict
```

创建 body：

```json
{
  "name": "某地-初二-数学-真题库",
  "subject": "数学",
  "grade": "初二",
  "region": "某地",
  "description": "侧重点：函数与几何",
  "tenant_id": "internal"
}
```

### 4.3 Questions

```http
POST   /api/exam/questions
GET    /api/exam/questions?collection_id=&qtype=&difficulty=&tag=&status=published&limit=50&offset=0
GET    /api/exam/questions/{id}
PUT    /api/exam/questions/{id}
DELETE /api/exam/questions/{id}
```

创建 body：

```json
{
  "collection_id": "...",
  "qtype": "choice",
  "difficulty": 3,
  "stem": "题干…",
  "options": ["A. …", "B. …", "C. …", "D. …"],
  "answer": "B",
  "analysis": "…",
  "knowledge_tags": ["一次函数", "图像"],
  "region": "某地",
  "year": "2024",
  "quality_status": "published"
}
```

### 4.4 组卷

```http
POST /api/exam/papers/assemble
```

body：

```json
{
  "collection_id": "...",
  "title": "某地初二数学模拟卷 A",
  "include_answers": true,
  "spec": {
    "by_qtype": {"choice": 5, "fill": 3, "short": 2},
    "difficulty_min": 2,
    "difficulty_max": 4,
    "knowledge_tags_any": ["一次函数"],
    "seed": 42
  }
}
```

成功响应：

```json
{
  "ok": true,
  "paper_id": "...",
  "title": "...",
  "question_ids": ["...", "..."],
  "counts": {"choice": 5, "fill": 3, "short": 2},
  "markdown": "# ..."
}
```

失败（题量不足）：

```json
{
  "ok": false,
  "error": "insufficient_questions",
  "detail": {"qtype": "choice", "need": 5, "have": 2}
}
```

HTTP：业务不足用 **400**；参数错误 **422**。

### 4.5 试卷读取 / 导出

```http
GET /api/exam/papers/{id}
GET /api/exam/papers/{id}/export?format=markdown|docx|pdf&include_answers=true
```

`GET /api/exam/meta` 返回 `export_formats: ["markdown","docx","pdf"]`。  
导出响应为文件流（`Content-Disposition: attachment`）；非法 format → 400。

### 4.6 试卷入库 / 答案关联

详见 [`exam-bank-ingest.md`](./exam-bank-ingest.md)：

```http
POST /api/exam/ingest/parse
POST /api/exam/ingest/upload
GET  /api/exam/ingest/ocr/status
POST /api/exam/ingest/ocr
POST /api/exam/ingest/commit
POST /api/exam/ingest/apply-answers
GET  /api/exam/source-papers?collection_id=
```

---

## 5. 组卷算法（可测、确定性）

1. 过滤：`collection_id` + `published` + difficulty 范围 + 可选 tags（any 命中）  
2. 按 `qtype` 分组  
3. 每组用 `seed` 做稳定洗牌后取前 N  
4. 任一题型不足 → 整体失败，不返回残卷  
5. 拼接 Markdown：大题按题型分节；可选「答案与解析」附录  

---

## 6. 实施步骤（严格顺序）

| Step | 内容 | 测试 | 状态 |
|------|------|------|------|
| S0 | 本文 + `exam-bank-issues.md` | — | ✅ |
| S1 | `exam_bank` store：init / collection / question | `test_exam_bank_store.py` | ✅ |
| S2 | `assemble_paper` 纯函数 | `test_exam_bank_assemble.py` | ✅ |
| S3 | FastAPI router + settings + lifespan init | `test_exam_bank_api.py` | ✅ |
| S4 | `exam_*` scene presets | `test_exam_scene_presets.py` | ✅ |
| S5 | Frontend Admin 题库页 + 导航 + client | — | ✅ |
| S6 | README / 项目说明 / 闭环自检清单 | — | ✅ |

每步：**红 → 绿 → 重构**；失败写入 issues 文档后再修。

---

## 7. 前后端分工

### 后端

- `exam_bank/store.py` — SQLite CRUD  
- `exam_bank/assemble.py` — 组卷与 Markdown  
- `exam_bank/export_formats.py` — Markdown / DOCX / PDF 导出  
- `exam_bank/types.py` — 常量 qtypes  
- `api/exam_router.py` — HTTP  
- `config.py` — `exam_bank_db_path`  
- `scene_presets.py` — `exam_assemble` 等  

### 前端

- `lib/examBank.ts` — API client  
- `pages/admin/ExamBankPage.tsx` — 建库 / 录题 / 组卷预览  
- `departmentAccess` — feature `exam_bank`  
- `main.tsx` — route `admin/exam-bank`  

---

## 8. 非目标（MVP 明确不做）

- PDF/OCR 自动拆题（`POST /api/exam/ingest/ocr`，可选 PaddleOCR）  
- 教案全文生成  
- 爬虫语料分析  
- 写入 Milvus 主库  
- 多租户计费  

以上列入 Phase 2+，在 issues 文档用「延期」跟踪，避免局部最优抢工。

---

## 9. 相关文档

- 现状总览：[`项目说明.md`](./项目说明.md)  
- 问题记录：[`exam-bank-issues.md`](./exam-bank-issues.md)  
- 部署安全：沿用现有 Admin 鉴权，不新增匿名写接口  

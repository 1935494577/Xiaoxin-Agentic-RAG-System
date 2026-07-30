# 题库子系统 — 问题与决策记录

> 实施中遇到的问题、根因、修复写入本文。  
> 排障时：**先读本文件相关条目，再带入上下文修复**，避免重复踩坑或只做局部补丁。

---

## 使用方式

1. 复现失败（测试红 / 手工）→ 新增一条 `ISSUE-xxx`  
2. 写清：现象、期望、范围（store/api/fe/scene）  
3. 修复后更新状态为 `resolved`，附 commit / 测试名  
4. 若属 Phase 2+，标 `deferred`，勿在 MVP 硬塞  

---

## 延期（Phase 2+，勿局部抢做）

| ID | 项 | 原因 |
|----|-----|------|
| DEF-001 | ~~PDF 试卷入库解析~~ | **收窄**：文本 PDF/DOCX 拆题见 `exam-bank-ingest.md`；扫描件 OCR 仍延期 |
| DEF-002 | ~~教案生成~~ | **MVP 已落地**：`POST /api/exam/papers/{id}/lesson` 规则大纲；LLM 润色可后续增强 |
| DEF-003 | 爬虫语料洞察库 | 独立数据模型，避免与题表耦合 |
| DEF-004 | 题干向量相似题 | 可选辅索引，组卷主路径不依赖 |
| DEF-005 | 扫描件 / 图片 OCR 试卷 | 依赖 OCR 质量闸门 |

---

## 开放问题

（无）

---

## 已记录

### ISSUE-004 — Chat 可用但拆题失败

| 字段 | 内容 |
|------|------|
| 状态 | resolved |
| 日期 | 2026-07-23 |
| 现象 | 蓝条显示模型已配置，橙条「大模型拆题未成功」；Chat 正常 |
| 根因 | ① 粘贴拆题前端默认 60s 超时，整卷易被 abort；② 失败吞掉上游异常误报成 Key 问题；③ 拆题曾偏好 routing 小模型 |
| 修复 | parse `timeoutMs=180s`；拆题用 `chat_model`；JSON fence/`json_object`；错误透传 |
| 测试 | `test_exam_ingest_llm_errors.py` |

### ISSUE-000 — 文档与实施基线

| 字段 | 内容 |
|------|------|
| 状态 | resolved |
| 日期 | 2026-07-22 |
| 现象 | 需求停留在方案讨论，无 API 契约与闭环定义 |
| 决策 | 本 monorepo 独立 `exam_bank` + `/api/exam`；场景绑定 `exam_assemble`；TDD 按 `exam-bank-api.md` §6 |
| 修复 | 新增 `docs/exam-bank-api.md` 与本文 |

### ISSUE-001 — API 测试加载完整 `api.main` 卡住

| 字段 | 内容 |
|------|------|
| 状态 | resolved |
| 日期 | 2026-07-22 |
| 现象 | `TestClient(app)` 导入 `api.main` 触发 lifespan 模型预热，pytest 长时间无输出 |
| 期望 | 秒级完成 API 契约测试 |
| 范围 | test / api |
| 修复 | `test_exam_bank_api.py` 改为仅挂载 `exam_router` 的轻量 FastAPI |

### ISSUE-002 — store 死锁：`Lock` 重入

| 字段 | 内容 |
|------|------|
| 状态 | resolved |
| 日期 | 2026-07-22 |
| 现象 | pytest 无输出挂死；持锁调用 `_connect` → `init` 再次抢锁 |
| 期望 | CRUD 正常返回 |
| 范围 | store |
| 修复 | `_lock` 改为 `threading.RLock` |

### ISSUE-003 — 缺删除/编辑与试卷入库

| 字段 | 内容 |
|------|------|
| 状态 | resolved |
| 日期 | 2026-07-23 |
| 现象 | Admin 只能增题；粘贴文本识别大节；无 PDF/Word；无答案卷按题号关联 |
| 期望 | CRUD + 文档拆题预览入库 + source_papers 答案关联 |
| 范围 | store / api / fe |
| 决策 | 见 [`exam-bank-ingest.md`](./exam-bank-ingest.md) |
| 修复 | `update/delete` + `item_split` + `/api/exam/ingest/*` + Admin 编辑/导入/答案区；测试 `test_exam_crud` / `test_exam_ingest` / API |

---

## 变更日志

| 日期 | 说明 |
|------|------|
| 2026-07-22 | 创建文档；启动 `feature/exam-bank-mvp` |
| 2026-07-23 | 试卷路由复用 `.env` deepseek-v4-flash（llm_client + base /v1） |
| 2026-07-23 | DEF-001 收窄；启动 CRUD/导入/答案关联（ingest） |

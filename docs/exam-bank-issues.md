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

## 开放问题

（无）

---

## 已记录

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

---

## 延期（Phase 2+，勿局部抢做）

| ID | 项 | 原因 |
|----|-----|------|
| DEF-001 | PDF 试卷入库解析 | 依赖拆题质量闸门，MVP 先手录/JSON |
| DEF-002 | 教案生成 | 依赖稳定题 ID 与模板 |
| DEF-003 | 爬虫语料洞察库 | 独立数据模型，避免与题表耦合 |
| DEF-004 | 题干向量相似题 | 可选辅索引，组卷主路径不依赖 |

---

## 变更日志

| 日期 | 说明 |
|------|------|
| 2026-07-22 | 创建文档；启动 `feature/exam-bank-mvp` |
| 2026-07-23 | 试卷路由复用 `.env` deepseek-v4-flash（llm_client + base /v1） |

# Jnao 全平台数据架构 — 沉淀 · 共享 · 私有

> **状态**：S1–S3 已落地（统一 ACL + 题库 visibility + `DATABASE_URL` 配置位）；S4+ 待做  
> **原则**：知识库与题库共用身份与可见性模型；向量只负责检索，关系库负责归属与权限。  
> **问题记录**：实施问题写入 [`data-platform-issues.md`](./data-platform-issues.md)。

---

## 1. 目标

把 Jnao 从「多套本地文件/SQLite 拼盘」演进为：

1. **可沉淀**：文档、题目、组卷、反馈长期可查可复用  
2. **共享与私有兼顾**：个人草稿 / 组织共享 / 平台精选  
3. **全项目统一**：Chat 知识库与题库组卷同一套 `tenant` + `visibility` + 部门 ACL  

---

## 2. 现状（As-Is）与缺口

| 资产 | 现状存储 | 权限现状 | 缺口 |
|------|----------|----------|------|
| 知识库切块 | Milvus Lite + BM25 | 部门 + 文档 internal/public（`security/access_control`） | 缺统一「空间」元数据、owner、组织共享档 |
| 题库 | `exam_bank.db`（可迁 PG） | `tenant_id` + `visibility` / `owner_user_id`（`platform_acl`） | 线上 PG 统一存储 |
| 账号会话 | `auth.db` / `chat_sessions.db` | 用户级 | 与资产 ACL 未打通 |
| 反馈 | SQLite + `tenant_id` | 租户预留 | 可后迁 PG |
| Token/配置 | 多个 `.db`/json | 单机 | 可后迁 |

---

## 3. 目标架构

```text
┌──────────────── PostgreSQL（线上主元数据）─────────────────┐
│  tenants / users / departments                              │
│  kb_spaces / kb_documents（知识归属与审核）                 │
│  exam_collections / questions / paper_jobs                  │
│  feedback / golden / token_usage（分阶段迁入）              │
└────────────┬──────────────────────────┬────────────────────┘
             │                          │
             ▼                          ▼
    向量+BM25（检索）              对象存储（原文件）
    chunk ↔ document_id            PDF/Word/导出物
```

本地开发：**SQLite 仍可作 exam/auth 后端**；通过 `DATABASE_URL` 为空时回退 SQLite，非空时走 PG（分阶段接通）。

---

## 4. 统一可见性（全资产）

| 值 | 含义 | 知识库 | 题库 |
|----|------|--------|------|
| `private` | 仅 owner（及显式协作，后续） | 个人笔记空间 | 个人草稿题库 |
| `tenant_shared` | 本 `tenant_id` 内可见 | 校/司制度与教研资料 | 校本题库 |
| `platform` | 平台精选（需审核） | 标准模板 | 地区真题精选 |

叠加现有 **部门 ACL**（`can_access_row` / 文档 visibility internal·public）：

```text
最终可读 = tenant 匹配
         ∧ visibility 规则
         ∧ （若绑定部门范围）部门 ACL
```

Chat 检索：先解析用户可见的 `kb_space` / `document_id`，再向量检索（或检索后过滤）。  
组卷：只抽用户可见的 `exam_collections`。

---

## 5. 核心表（目标模型）

### 5.1 身份（已有 auth，演进）

- `tenants(id, name, …)`
- `users` / 部门关系（现有 SQLite → PG）

### 5.2 知识元数据（新建，向量外）

- `kb_spaces(id, tenant_id, owner_user_id, visibility, name, subject?, grade?, …)`
- `kb_documents(id, space_id, source_key, title, visibility, owner_user_id, status, …)`
- chunk 仍在向量库，metadata 带 `document_id` / `space_id`

### 5.3 题库（在现有表上演进）

- `collections` + `visibility`, `owner_user_id`
- `questions` + 同上（默认同 collection）
- `paper_jobs` 保留快照

### 5.4 质量与计量（后迁）

- feedback / golden / token_usage

---

## 6. 实施步骤

| Step | 内容 | 状态 |
|------|------|------|
| **S0** | 本文档 + issues | ✅ |
| **S1** | 统一 `platform_acl`（visibility 常量 + 可读判定） | ✅ |
| **S2** | 题库 SQLite 增补 `visibility`/`owner_user_id` + API 筛选 | ✅ |
| **S3** | `DATABASE_URL` 配置位 + 文档；PG 驱动可选骨架 | ✅（配置位；驱动接通后续） |
| **S4** | 知识库 `kb_spaces` 元数据表（SQLite/PG）与 registry 对齐 | 后续 |
| **S5** | 检索路径接入「可见 document 集合」过滤 | 后续 |
| **S6** | 生产 PG 迁移脚本与双写/切换 | 后续 |

---

## 7. 配置

```env
# 空 = 继续用各业务 SQLite（开发默认）
DATABASE_URL=

# 生产示例
# DATABASE_URL=postgresql+psycopg://jnao:***@127.0.0.1:5432/jnao
```

---

## 8. 非目标（本阶段）

- 一次迁完所有 SQLite  
- 多租户计费 SaaS  
- 推倒重写向量索引  

---

## 9. 相关文档

- 现状总览：[`项目说明.md`](./项目说明.md)  
- 题库 API：[`exam-bank-api.md`](./exam-bank-api.md)  
- 题库路由：[`exam-bank-routing.md`](./exam-bank-routing.md)  
- 部署安全：[`deploy_security.md`](./deploy_security.md)  

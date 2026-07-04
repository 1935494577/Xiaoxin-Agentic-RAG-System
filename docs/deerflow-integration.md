# DeerFlow 集成规范（实现唯一依据）

> **权威源码**：`D:\bytedance flow\deer-flow`（与 [bytedance/deer-flow](https://github.com/bytedance/deer-flow) 一致）  
> **原则**：编排、工具、Skill、Token、渠道 **按 DeerFlow 目录与 API 落地**；本仓库仅做 **RAG/ACL/部门** 适配层，**禁止**另起一套 Agent 架构。

---

## 1. 分层（Harness / App，与 DeerFlow 相同）

| 层 | DeerFlow 路径 | 本仓库对应 | 依赖方向 |
|----|---------------|------------|----------|
| **Harness** | `backend/packages/harness/deerflow/`（`import deerflow.*`） | 同源引入（submodule / path dep / 拷贝同步） | App → Harness |
| **App** | `backend/app/gateway/`、`backend/app/channels/` | `enterprise_rag/src/api/` 扩展 + 新建 `enterprise_rag/src/app/channels/` | 仅 App 可 import deerflow |
| **Skills 目录** | 仓库根 `skills/public`、`skills/custom` | **同路径** | Harness 读取 |
| **配置** | 根目录 `config.yaml`、`extensions_config.json` | **同文件名与 schema** | Gateway 热加载边界同 DeerFlow |

**禁止**：`deerflow.*` import `enterprise_rag.*`（对照 DeerFlow `tests/test_harness_boundary.py`）。

---

## 2. Agent 运行时（替换自研 ReAct 主链）

### 2.1 入口（必须）

| 项 | DeerFlow 参照 |
|----|----------------|
| Lead Agent 工厂 | `deerflow.agents.lead_agent.agent:make_lead_agent` |
| Graph 注册 | `backend/langgraph.json` |
| 运行时 | `deerflow.runtime` — `RunManager` + `run_agent()` + `StreamBridge` |
| Thread 状态 | `deerflow.agents.thread_state:ThreadState` |

**本仓库改造**：

- **任务 / 自动模式**（需工具、Skill、澄清、Todo）：走 **`make_lead_agent` + LangGraph SSE**，不再用 `agent/tools/runtime/loop.py` 作为主编排。
- **知识模式**（纯 KB、低延迟）：可保留现有 `stream_rag_chat` classic 路径，但须在文档与代码注释标明为 **KB 快路径**；与 DeerFlow 主链并存，不得混写 Middleware。

### 2.2 Middleware 链（顺序与类名不可自造）

以 `deerflow.agents.lead_agent.agent:build_middlewares` 为准，共享底座：

`deerflow.agents.middlewares.tool_error_handling_middleware:build_lead_runtime_middlewares`

**必须复用的核心 Middleware**（类名与文件路径与 DeerFlow 一致）：

| Middleware | 文件 |
|------------|------|
| `SkillActivationMiddleware` | `agents/middlewares/skill_activation_middleware.py` |
| `ClarificationMiddleware` | `agents/middlewares/clarification_middleware.py` |
| `TodoMiddleware` | `agents/middlewares/todo_middleware.py` |
| `TokenUsageMiddleware` | `agents/middlewares/token_usage_middleware.py` |
| `DynamicContextMiddleware` | `agents/middlewares/dynamic_context_middleware.py` |
| `ToolOutputBudgetMiddleware` | `agents/middlewares/tool_output_budget_middleware.py` |
| `ToolErrorHandlingMiddleware` | `agents/middlewares/tool_error_handling_middleware.py` |

**禁止**：自研 `TurnMiddleware`、`agent/runtime/middleware.py` 等与 DeerFlow 平行的链。

配置开关（`is_plan_mode`、`token_usage.enabled` 等）**仅**通过 `config.yaml` 控制，行为与 DeerFlow 一致。

---

## 3. 工具层（`get_available_tools`）

### 3.1 组装入口

```python
from deerflow.tools import get_available_tools
```

实现参照：`backend/packages/harness/deerflow/tools/tools.py`

来源顺序（与 DeerFlow 相同）：

1. `config.yaml` → `tools[]`（`name` / `group` / `use: module:attr`）
2. MCP（`extensions_config.json` → `deerflow.mcp`）
3. Built-in：`present_file_tool`、`ask_clarification_tool`、`view_image_tool`
4. 可选：`task_tool`（`subagent_enabled`）

### 3.2 本仓库 RAG 工具注册方式

**不得**继续扩展 `TOOL_DEFINITIONS` 硬编码表作为主路径。应新增 **community 风格包**：

```text
enterprise_rag/src/deerflow_community/
  kb_search.py      # LangChain BaseTool，use: enterprise_rag.deerflow_community.kb_search:kb_search_tool
  list_kb_sources.py
  relationship_graph.py
  format_structured_output.py
```

在 `config.yaml` 中注册（参照 `config.example.yaml` 中 `web_search` / `tavily` 条目）：

```yaml
tools:
  - name: kb_search
    group: rag
    use: enterprise_rag.deerflow_community.kb_search:kb_search_tool
  - name: web_search
    group: web
    use: deerflow.community.tavily.tools:web_search_tool   # 与 DeerFlow 一致，Tavily 走 community
```

### 3.3 Skill 工具白名单

使用 DeerFlow 已有机制：

- `deerflow.skills.tool_policy:filter_tools_by_skill_allowed_tools`
- Skill frontmatter `allowed-tools`（见 §4）

**禁止**：自研 `task_mode_tools_allowlist` 语义；改用 Skill `allowed-tools` + `config.yaml` tool groups。

### 3.4 过渡期

现有 `agent/tools/runtime/routing.py` 仅作 **KB 快路径** 预处理，待 DeerFlow 主链接管 task/auto 后 **删除或降级**为 KB-only 辅助，不得与 `SkillActivationMiddleware` 重复造意图路由。

---

## 4. Skill 层（与 DeerFlow 完全一致）

### 4.1 目录与格式

```text
skills/
├── public/<skill-dir>/SKILL.md
└── custom/...
```

- 解析：`deerflow.skills.parser`、`deerflow.skills.types.Skill`
- 存储：`deerflow.skills.storage.LocalSkillStorage`
- 启停：`extensions_config.json` → skills state（同 DeerFlow）
- 激活：`/skill-name 任务` → `deerflow.skills.slash` + `SkillActivationMiddleware`

`SKILL.md` frontmatter 允许字段以 `deerflow.skills.validation.ALLOWED_FRONTMATTER_PROPERTIES` 为准（含 `allowed-tools`）。

### 4.2 Gateway API（App 层照抄路由语义）

| 路由 | DeerFlow 文件 |
|------|----------------|
| `GET /api/skills` | `app/gateway/routers/skills.py` |
| `PUT /api/skills/{name}` | 同上 |
| `POST /api/skills/install` | 同上 |

本仓库 Admin Skills 页应对齐上述契约，**禁止**自研 `GET /api/v1/skills` 不同 schema。

### 4.3 业务 Skill

将现有 `scenario_catalog.json` / `scene_preset` **迁移**为 `skills/public/` 下 SKILL.md（如 `wecom-parent-dm`、`industry-research`），不再用 Python dict 承载工作流正文。

---

## 5. Token 计量（DeerFlow 实现 + 本仓库 UI）

### 5.1 后端（必须）

| 组件 | DeerFlow 参照 |
|------|----------------|
| 采集中间件 | `TokenUsageMiddleware` |
| Run 进度 / 持久化 | `deerflow.runtime` RunJournal、`token_usage_by_model` |
| Thread 汇总 API | `GET /api/threads/{thread_id}/token-usage`（见 `app/gateway/routers/thread_runs.py` 相关模型） |
| 配置 | `config.yaml` → `token_usage.enabled` |

**禁止**：自研 `agent/runtime/token_usage.py` 平行统计；仅在 DeerFlow 链上挂 `TokenUsageMiddleware`。

### 5.2 前端（必须，对齐 DeerFlow）

参照源码移植（改 API base 为 Jnao 8010）：

| DeerFlow 文件 | 用途 |
|---------------|------|
| `frontend/src/core/messages/usage.ts` | 单条 AI message `usage_metadata` |
| `frontend/src/core/threads/token-usage.ts` | thread 级汇总 query |
| `frontend/src/core/threads/api.ts` | `GET .../token-usage` |
| `frontend/src/core/settings/local.ts` | `tokenUsage` 显示开关 |

本仓库：

- **Chat**：消息级 / 会话级 token（与 DeerFlow 相同交互，非自研 SSE `done.token_usage` 字段）
- **Admin**：thread token 汇总或全局统计页，数据来自 **DeerFlow 同款 API**

---

## 6. 渠道（DeerFlow `app/channels` + Gateway）

### 6.1 后端（目录与类名一致）

从 DeerFlow **拷贝/adapt**（保持 `Channel` ABC、`MessageBus` 语义）：

| 文件 | 作用 |
|------|------|
| `app/channels/base.py` | `Channel` 抽象 |
| `app/channels/message_bus.py` | Inbound/Outbound |
| `app/channels/manager.py` | 调度 → LangGraph SDK / Gateway runs |
| `app/channels/service.py` | 生命周期 |
| `app/channels/store.py` | `channel:chat_id` → `thread_id` |
| `app/channels/feishu.py` | 首个渠道（与 DeerFlow 一致） |

Gateway：

| 路由 | DeerFlow 文件 |
|------|----------------|
| `GET /api/channels/` | `app/gateway/routers/channels.py` |
| `POST /api/channels/{name}/restart` | 同上 |

Agent 调用：渠道 worker 通过 **LangGraph-compatible API** 创建 run/stream（DeerFlow `app/channels/manager.py`），本仓库 Gateway 需嵌入同款 `RunManager`，**禁止**渠道直连自研 `/chat/stream` 旁路（除非该路由本身已是 LangGraph 兼容层）。

### 6.2 前端（Admin）

对齐 DeerFlow Admin/设置中的渠道状态展示（`ChannelStatusResponse`：`service_running` + `channels` dict）。

本仓库：`ChannelsPage.tsx` 字段与 DeerFlow API 一致，**禁止**自设计另一套 channel config schema。

---

## 7. 本仓库保留域（唯一允许差异）

| 模块 | 路径 | 说明 |
|------|------|------|
| 检索 / 索引 / ACL | `enterprise_rag/src/retrieval/`、`indexing/`、`security/` | 不变 |
| KB 快路径对话 | `stream_rag_chat` knowledge 模式 | 与 DeerFlow 主链并列 |
| 部门 / 场景 ACL | `department_auth`、`allowed_sources` | 注入 `kb_search` tool 上下文 |
| 反馈闭环 | `feedback_loop/` | 不变 |
| 前端壳 | `frontend/` Jnao Chat UI | 视觉保持 PRODUCT.md；**Token/渠道/Skill Admin** 行为对齐 DeerFlow |

---

## 8. 实施阶段（严格顺序）

```text
DF-0  引入 deerflow-harness（path: D:\bytedance flow\deer-flow\backend\packages\harness）
DF-1  根目录 config.yaml + extensions_config.json（从 config.example.yaml 复制）
DF-2  skills/ 目录 + 迁移 2 个业务 SKILL.md
DF-3  enterprise_rag.deerflow_community 工具 + config.yaml 注册
DF-4  Gateway 嵌入 make_lead_agent；task/auto → LangGraph stream
DF-5  TokenUsageMiddleware + /api/threads/{id}/token-usage + 前端 usage 模块
DF-6  app/channels + /api/channels + Admin ChannelsPage
DF-7  废弃 loop.py 主路径、自研 skill loader、自研 token store（若已写）
```

每步 PR 须注明 **对照 DeerFlow 文件路径** 与 diff 摘要。

---

## 9. 禁止清单（Code Review 硬规则）

- [ ] 不得新增与 `deerflow.agents.middlewares.*` 同职责的自研 Middleware
- [ ] 不得用 `agent/tools/runtime/loop.py` 作为 task/auto 主编排
- [ ] 不得自研 Skill 格式（必须 `skills/**/SKILL.md` + `LocalSkillStorage`）
- [ ] 不得自研 Token 聚合（必须 `TokenUsageMiddleware` + thread token-usage API）
- [ ] 不得自研渠道总线（必须 `MessageBus` + `Channel` ABC）
- [ ] 不得在 Harness 层 import `enterprise_rag` / `api.main`

---

## 10. 参考文档（本地只读）

| 文档 | 路径 |
|------|------|
| Agent 开发指南 | `D:\bytedance flow\deer-flow\backend\AGENTS.md` |
| 架构总览 | `D:\bytedance flow\deer-flow\backend\docs\ARCHITECTURE.md` |
| 配置示例 | `D:\bytedance flow\deer-flow\config.example.yaml` |

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-06-16 | 初版：以本地 deer-flow 为唯一实现依据，替代自研编排方案 |

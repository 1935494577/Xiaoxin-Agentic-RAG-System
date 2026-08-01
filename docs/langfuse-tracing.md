# Langfuse 全链路追踪

> **目标**：每次对话在 Langfuse UI 可回放 — 检索 / 路由 / LLM 生成 / 工具 /（DeerFlow）Agent 步骤。  
> 与 Admin **反馈 JSONL** 并存：JSONL 供运营「查看链路」；Langfuse 供工程师深度调试。

## 能力对照

| 能力 | Langfuse | 本地 JSONL |
|------|----------|------------|
| 嵌套 span / generation | ✅ | ✅ 扁平 span |
| session / user 分组 | ✅ | ✅ session_id |
| LLM 输入输出 | ✅ generation | ✅ answer_preview |
| 工具调用明细 | ✅（DeerFlow 自动；8010 逐步补） | ⚠️ tool_trace 摘要 |
| 离线评测 / Dataset | ✅ Langfuse 平台 | ❌ |
| 自托管 | ✅ Docker | ✅ 文件 |

## 安装 SDK

**PyPI（CI / 生产）：**

```bash
pip install "langfuse>=4.0.0,<5"
```

**本地源码（你已 clone）：**

```bash
pip install -e D:/LangFuse_python/langfuse-python
```

Harness venv 同样安装（8011 DeerFlow 已依赖 langfuse）：

```powershell
.\scripts\bootstrap-harness-venv.ps1
.\.venv-harness\Scripts\pip install -e D:/LangFuse_python/langfuse-python
```

## 配置（`.env`）

```env
LANGFUSE_TRACING=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
# 自托管示例：LANGFUSE_BASE_URL=http://127.0.0.1:3000
LANGFUSE_BASE_URL=https://cloud.langfuse.com

LOCAL_TRACE_ENABLED=true   # 建议保持开启，Admin 反馈链路仍用 JSONL
```

重启 **8010 API**；若用 task/auto 或 IM DeerFlow 路径，重启 **8011 Gateway**。

## 覆盖范围

| 路径 | 端口 | 追踪方式 |
|------|------|----------|
| 知识模式 `/chat/stream` | 8010 | `stream_tracer` → Langfuse span + JSONL |
| 任务/自动 lead agent | 8011 | DeerFlow `CallbackHandler` + metadata |
| IM（`use_rag_backend: true`） | 8010 | 同知识模式 |

## 查看 Trace

1. 打开 Langfuse UI（`LANGFUSE_BASE_URL`）
2. **Traces** → 按 Session（`chat session_id`）或 User 筛选
3. 单次对话 `trace_id` 与 Chat SSE / 反馈一致；链接格式：  
   `{LANGFUSE_BASE_URL}/trace/{trace_id}`

Admin → **链路 Trace** 页显示 Langfuse 是否就绪。

## 与反馈闭环

- **Langfuse**：观测每 turn 是否按预期执行（检索、路由、生成）
- **feedback_loop**：👍👎 → golden 评测 → alias/配置补丁（质量迭代）

二者互补，不互相替代。

## DeerFlow 对齐

环境变量与 `deerflow.config.tracing_config` 一致；勿在 RAG 层重复造 CallbackHandler。  
8010 用手动 `start_as_current_observation` 对齐 span 名；8011 走 LangGraph 自动树。

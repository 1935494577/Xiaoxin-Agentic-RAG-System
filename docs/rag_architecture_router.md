# 多架构 RAG 自主调度

## 概述

系统根据问题形态、部门策略与三条启发式，在 **Classic / Graph / Agentic** 三种 RAG 架构间自动路由。

```text
提问 / 临时文档 / 文档任务
        ↓
  architecture_router（规则 → 可选 LLM → 部门策略）
        ↓
  classic │ graph │ agentic 管道
        ↓
  kb / general 回答 + 引用
```

## 三条启发式

| 类型 | 典型问法 | 架构 |
|------|----------|------|
| 单跳事实 | 保修期多久、如何配置、适用范围 | **Classic** |
| 关系链 | 谁依赖谁、审批链、关联对象 | **Graph** |
| 开放调查 | 分析原因、排查故障、综合研究 | **Agentic** |

## 配置项（Admin → UI 配置）

| 字段 | 说明 | 默认 |
|------|------|------|
| `rag_arch_router_enabled` | 启用自动架构路由 | `true` |
| `rag_arch_llm_fallback` | 规则不确定时用 routing 模型分类 | `false` |
| `default_rag_architecture` | 默认 `auto` 或固定架构 | `auto` |
| `graph_extraction_enabled` | 入库后异步抽取实体关系 | `true` |
| `agentic_max_turns` | Agentic 工具循环上限 | `6` |

部门策略见 [`enterprise_rag/data/config/rag_architecture_policy.json`](../enterprise_rag/data/config/rag_architecture_policy.json)。

## Chat 使用方式（面向业务用户）

**无需选择 RAG 架构**。发送自然语言问题即可；服务端会根据问法自动在 Classic / Graph / Agentic 间路由（规则优先，可在 Admin 开启 LLM 复核）。

文档类意图也会从问句推断，例如「总结…」「对比 A 与 B」「提取所有…」。

## Chat 请求字段（API / 集成方可选）

- `rag_architecture`: `auto` | `classic` | `graph` | `agentic`
- `input_mode`: `question` | `temp_document` | `doc_task`
- `doc_task_type`: `summary` | `compare` | `extract` | `annotate`
- `temp_document_id`: 会话临时文档 ID
- `allowed_sources`: 限定已入库来源

## API

- `GET /sources/list` — 已入库文档列表（来源筛选）
- `POST /chat/documents/upload` — 会话级临时文档上传

## SSE 事件

路由阶段会推送：

```json
{"type":"status","phase":"routing","rag_architecture":"classic","input_mode":"question"}
```

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_architecture_router.py tests/unit/test_graph_store.py tests/unit/test_agentic_pipeline.py -q
```

Golden 样例：`enterprise_rag/data/eval/routing_architecture_golden.jsonl`

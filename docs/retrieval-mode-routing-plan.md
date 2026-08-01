# 检索模式路由 — 执行方案

> 对齐 Query 路由 + 四层检索 + BM25/Vector/RRF/Rerank 流水线，在 Classic RAG 路径落地。

## 目标

1. **按 query 分型**选择检索后端（exact / semantic / hybrid），降低无效双路检索成本  
2. **单 variant 内** Vector + BM25 改用 RRF 融合（解决量纲不一致）  
3. **可观测**：SSE / trace 暴露 `retrieval_mode` 与 `paths_used`  
4. **题库**：精确 ID / 卷名优先，再 fallback LIKE  
5. **测试闭环**：TDD 覆盖路由规则、各 mode 不调用多余后端、RRF 行为

## 阶段与验收

| 阶段 | 内容 | 验收标准 |
|------|------|----------|
| P1 | `detect_retrieval_mode` 规则路由 | 15+ 单测通过 |
| P2 | `hybrid_search(mode=…)` + 单路 RRF | exact 不调 embed；semantic 不调 BM25 |
| P0 | `retrieval_meta` 写入 trace/SSE | status 含 mode/paths_used |
| P3 | prepare → nodes → stream 接线 | 端到端 stream 测试通过 |
| P4 | exam gate 精确查卷 | UUID/卷名直查 + 单测 |
| P5 | README + config | 文档与配置项齐全 |

## 架构

```
stream_rag_chat
  ├─ exam gate / chitchat / graph  (L1 短路，已有)
  └─ Classic retrieve_node
        └─ resolve_retrieval_mode(message, fast_mode)
              ├─ exact   → BM25 only (+ optional skip rerank)
              ├─ semantic→ Vector only
              └─ hybrid  → BM25 + Vector + RRF → Rerank
```

## 配置项（`config.py` / `.env`）

| 键 | 默认 | 说明 |
|----|------|------|
| `RETRIEVAL_MODE_ROUTER_ENABLED` | `true` | 关闭则始终 hybrid（兼容旧行为） |
| `RRF_K` | `60` | RRF 平滑常数，可 A/B 调至 10–20 |
| `EXACT_SKIP_RERANK_ENABLED` | `true` | exact 且 BM25 top1 分数高时跳过重排 |
| `EXACT_SKIP_RERANK_MIN_SCORE` | `8.0` | BM25 跳过 rerank 阈值 |
| `STREAM_FAST_DOWNGRADE_HYBRID` | `true` | 快速模式下 hybrid→semantic |
| `QUERY_NORMALIZE_ENABLED` | `true` | 规则变体 + 多路 RRF（无 LLM） |

本地开发：复制 `.env.example` → `.env` 后按需调整；清理检索缓存运行 `.\scripts\clean-retrieval-cache.ps1`（**不删**入库索引）。

## 已废弃

- `hybrid_vector_weight` / `hybrid_bm25_weight`：加权融合已改为 RRF；反馈 Actuator 现仅允许 patch `rrf_k`。

## Router 演进（后续）

- L1 规则（本 PR）→ L2 轻量分类器（日志 >500）→ L3 RAGRouter（误路由 >10%）

## 相关文件

- `enterprise_rag/src/retrieval/retrieval_mode_router.py` — 新建  
- `enterprise_rag/src/retrieval/hybrid_searcher.py` — mode 分支 + RRF  
- `enterprise_rag/src/retrieval/query_understanding.py` — 集成 mode  
- `enterprise_rag/src/agent/nodes.py` / `pipelines/classic.py` — 传参  
- `enterprise_rag/src/agent/stream_chat.py` — SSE 可观测  
- `enterprise_rag/src/exam_bank/exam_intent.py` — 题库精确查  
- `tests/unit/test_retrieval_mode_router.py`  
- `tests/test_hybrid_search_modes.py`

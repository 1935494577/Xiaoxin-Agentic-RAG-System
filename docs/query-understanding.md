# Query Understanding 架构与治理

> 输入侧噪声/错字/口语由 **Query Understanding（QU）** 统一处理；**禁止**再为个案改 KB/生成 prompt 或加 scattered `if` 补丁。

## 分层职责

| 层 | 模块 | 职责 |
|----|------|------|
| 入口 | `understand_query()` → `prepare_turn` | 唯一用户侧文本理解入口 |
| Tier 0 | `query_normalize.py` | NFKC、oral_map、语音 filler 分段 |
| Tier 0/1 | `query_aliases.json` | **可信** canonical 纠错（`suggest_and_apply_domain_corrections`） |
| Tier 1 | `domain_lexicon` + `term_fuzzy` | 仅扩 **search variants**，不改写 canonical |
| Tier 2 | `term_embeddings` | embedding 近邻扩 variant |
| Tier 3 | `query_rewriter` | 低置信时条件 LLM rewrite |
| Tier 4 | `hybrid_searcher` | 多路 variant + RRF |
| 检索门控 | `kb_judge.py` | confident / gray / weak + LLM judge |
| 路由 | `query_understanding.detect_query_intent` | kb / realtime / graph；`stream_chat` 读 `turn_meta.query_intent` |
| 生成 | persona / KB prompt / tool loop | **只管回答风格与工具用法**，不管错字纠错 |
| 闭环 | feedback `apply_query_alias` | miss → 合并 alias，而非改 prompt |

## 已废弃（勿恢复）

- **天气 fast path**（直接 dump `get_weather` 文本、跳过 LLM 格式化）— 已删除
- **代码内硬编码 term alias**（`_DEFAULT_ALIASES`）— 已删除；唯一数据源：`enterprise_rag/data/config/query_aliases.json`
- **为单个词改 KB 系统提示词** — 应加 alias / 词表 / golden 用例

## 新增错字 / 口语 / 语音问题时的正确流程

1. 在 `query_robustness.jsonl` 加一条 expect
2. 若属已知 canonical：更新 `query_aliases.json` 或走 feedback `apply_query_alias`
3. 若属 corpus 新词：re-ingest 或 `POST /ingest/rebuild-domain-lexicon`
4. 跑 `.\scripts\query_verify.ps1`

## 验收

```powershell
.\scripts\query_verify.ps1
python scripts/eval_query_robustness.py
```

## SSE 观测

流式对话会发出 `phase: query_understanding`，payload 为 `QueryUnderstanding.to_dict()`，便于确认 Tier 0–2 是否生效，无需猜 prompt。

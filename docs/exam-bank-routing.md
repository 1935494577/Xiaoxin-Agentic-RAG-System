# 题库题型与智能路由 — 整合方案（已实施）

## 策略（混合 + LLM 优先）

```text
固定模板（学科 × 学段）  → UI 默认题型
        ↓
大模型路由 Agent         → 科目 / 年级 / 大题题型 / 估计题量（默认开启）
        ↓ 失败
规则识别「一、选择题」   → 兜底
        ↓
组卷选项 = 模板 ∪ 库内实有 ∪ 自定义；缺题型明确提示
```

用户倾向：**大模型路由 / Agent 调度优于纯固定规则** → `POST /api/exam/analyze-paper` 默认 `use_llm=true`。

## 数学等默认题型（贴近真实卷）

| 学科 | 初中默认 |
|------|----------|
| 数学 | 选择、填空、**解答**（不再并列计算/简答/大题） |
| 语文 | 选择、填空、阅读、写作 |
| 英语 | 听力、选择、完形、阅读、填空、写作 |
| 物理/化学 | 选择、填空、实验、解答 |
| 生物 | 选择、填空/解答 |
| 史地政 | 选择、材料分析 |

学段：`primary` / `junior` / `senior`，年级映射自动解析。

## 代码

- `exam_bank/subject_catalog.py` — 分学段模板  
- `exam_bank/paper_router.py` — LLM Agent + 规则兜底  
- `exam_bank/section_detect.py` — 规则大题标题  
- Admin：学段选择 +「使用大模型路由」开关  

## 配置

**复用 Chat 同一套 `.env`（不要另配模型）：**

```env
OPENAI_API_BASE=https://api.deepseek.com
OPENAI_API_KEY=...
OPENAI_CHAT_MODEL=deepseek-v4-flash
# 可选：OPENAI_ROUTING_MODEL=  # 空则试卷路由也用 CHAT_MODEL
```

实现：`exam_bank/llm_client.py` → 默认模型档（若有 Key）否则 `.env`；DeepSeek base 自动补 `/v1`。  
`GET /api/exam/meta` 的 `llm.model` 可核对当前路由模型。

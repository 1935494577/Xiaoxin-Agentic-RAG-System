# 题库组卷 v2 — 学科题型 / 卷面识别 / 配比组卷

> 承接 [`exam-bank-api.md`](./exam-bank-api.md) MVP。  
> **本版目标**：组卷按**学科 + 年级**驱动题型清单；支持整卷关键词识别题型；多选配比 + 难度配比；缺题型明确提示「没有相应题型」；支持自定义题型。

---

## 1. 产品逻辑

```text
选学科 → 选年级 →（可选）匹配题库 collection
     → 题型清单 = 学科默认题型 ∪ 库内已有题型 ∪ 用户自定义
     → 多选各题型数量 + 可选难度档数量
     → 组卷：不足/缺失 → 失败并提示（不吐残卷）
```

整卷入库文本中的「一、选择题」「二、填空题」「三、解答题」等：

1. **规则优先**识别大题标题 → 映射标准 `qtype`  
2. 可选 **LLM 路由**（`use_llm=true`）补全模糊标题；失败回退规则  
3. 识别结果仅作「建议题型 / 导入辅助」，组卷仍以题库字段为准  

---

## 2. 学科默认题型（可扩展）

| 学科 | 默认 qtype（id） | 中文 |
|------|------------------|------|
| 数学 | choice, fill, calc, short, big | 选择/填空/计算/简答/大题 |
| 语文 | choice, fill, short, big | 选择/填空/简答/大题 |
| 英语 | choice, fill, short | 选择/填空/简答写作等 |
| 物理/化学 | choice, fill, calc, short, big | 同数理化卷常见结构 |
| 其他 | choice, fill, short, other | 通用 |

难度档（组卷配比用）：

| band | 对应 difficulty |
|------|-----------------|
| easy | 1–2 |
| mid | 3 |
| hard | 4–5 |

---

## 3. API 增量

### 3.1 `GET /api/exam/meta` 扩展

返回 `subjects[]`（含 `grades` 建议、`qtypes[]`）、`qtype_labels`、`difficulty_bands`、`section_aliases`。

### 3.2 `GET /api/exam/inventory?collection_id=`

```json
{
  "collection_id": "...",
  "by_qtype": {"choice": 12, "fill": 5},
  "by_difficulty_band": {"easy": 4, "mid": 8, "hard": 5},
  "custom_qtypes": ["证明题"]
}
```

### 3.3 `POST /api/exam/detect-sections`

```json
{"text": "一、选择题\n1....\n二、填空题\n...", "subject": "数学", "use_llm": false}
```

→ `sections: [{heading, qtype, label, start_line}]`

### 3.4 `POST /api/exam/papers/assemble` 扩展 `spec`

```json
{
  "by_qtype": {"choice": 5, "fill": 3, "big": 2},
  "by_difficulty_band": {"easy": 2, "mid": 5, "hard": 3},
  "seed": 42
}
```

错误：

| error | 含义 |
|-------|------|
| `missing_qtype` | 库中**完全没有**该题型 → 文案「没有相应题型：xxx」 |
| `insufficient_questions` | 有题型但数量不够 |
| `insufficient_difficulty` | 难度档数量不够 |

自定义题型：`qtype` 可为任意非空 slug（中文标签经规范化）；录题与组卷一致。

---

## 4. 实施步骤

| Step | 内容 | 状态 |
|------|------|------|
| V2-1 | `subject_catalog` + `section_detect` + 测试 | ✅ |
| V2-2 | assemble 缺题型/难度档 + 自定义 qtype | ✅ |
| V2-3 | inventory / detect / meta API | ✅ |
| V2-4 | Admin：学科年级 → 题型多选数量 → 难度配比 → 缺题提示 | ✅ |
| V2-5 | 文档与问题记录更新 | ✅ |

---

## 5. 非目标（本版不做）

- PDF OCR 整卷拆题落库（仍 DEF-001）  
- 纯 LLM 自动录题无审核  
- 跨多个 collection 自动合并组卷（先选一个库；可按学科年级筛库）  

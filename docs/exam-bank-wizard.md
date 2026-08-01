# 题库 Admin 向导 — 首页入口 + 步进 / 智能组卷

> **状态**：已落地（首页入口 + 入库四步 + **智能组卷 UX v3.2**（章节/知识点 + 元数据闭环））  
> **原则**：第一页只放功能入口；点进后再走步骤。组卷按「章节或知识点 + 设置 + 题型」一页生成并预览。

---

## 1. 信息架构

```text
/admin/exam-bank                 首页：试卷入库 / 试卷导出 / 题库管理
/admin/exam-bank/ingest?step=1   入库四步向导
/admin/exam-bank/assemble        智能组卷：左章节|知识点 + 01/02/03（可折叠）+ 右卷面预览
/admin/exam-bank/manage          已有题库列表（选用/删除/检索）
```

### 入库步骤

| step | 名称 | 闸门 |
|------|------|------|
| 1 | **题库设置**（学段/学科/年级 + 地区省市下拉 + 试卷年份 + 新建或选用题库） | 基本信息齐全且已选用有效题库、无同名重复；芯片可 × 删除 |
| 2 | 导入解析（PDF/Word/粘贴） | **大模型拆题**（注入科目/年级/地区；输出标签+章节）；过滤注意事项等噪声 |
| 3 | 预览编辑 | 勾选草案；确认入库（题目写入 **region / year / chapter**） |
| 4 | 答案关联 | 卷内已含答案可跳过；否则粘贴答案卷或稍后补 |

布局：步骤内容 `max-w-xl` 居中；「上一步 / 下一步」并排居中。未达闸门时按钮禁用（不向用户展示闸门说明文案）。

状态：URL `step` + `sessionStorage` 草稿（`examWizard:v2:{userId}`）；权威数据在服务端。

### 智能组卷（UX v3.2）

三栏布局：

| 区域 | 内容 |
|------|------|
| 左 | **章节 / 知识点** Tab；多选（题量）；清空 |
| 中 01 | 选择题库 + 已选章节/知识点 chips（可折叠） |
| 中 02 | 场景 / 难度 / 优先地区（常用省市，库内优先）/ 优先年份（全部·近3·近5·指定）/ 标题（可折叠） |
| 中 03 | 科目题型需要道数 + 易/中/难；导出格式（可折叠） |
| 底 | 存为模板 / 加载模板（localStorage）；生成试卷 |
| 右 | 正式卷面预览；再次下载；教案大纲 |
| 次要 | 一句话组卷（可折叠） |

API：

- 库存 `GET /api/exam/inventory`：`by_tag` / `by_chapter` / `regions` / `years`；可选 `tag`/`chapter`/`region`/`year`
- Meta `GET /api/exam/meta`：`common_regions`
- 组卷 `POST /api/exam/papers/assemble`：可选 `knowledge_tags_any` / `chapters_any` / `regions_any` / `years_any`
- 一句话 `POST /api/exam/papers/assemble-nl`
- 导出 `GET /api/exam/papers/{id}/export?format=markdown|docx|pdf&include_answers=`
- 教案 `POST /api/exam/papers/{id}/lesson`

组卷配比示例：

```json
{
  "by_qtype": { "choice": 5, "fill": 3 },
  "by_qtype_band": {
    "choice": { "easy": 2, "mid": 2, "hard": 1 },
    "fill": { "easy": 1, "mid": 1, "hard": 1 }
  },
  "knowledge_tags_any": ["奇偶性"],
  "chapters_any": ["集合与常用逻辑用语"],
  "regions_any": ["浙江"],
  "years_any": ["2024"]
}
```

---

## 2. 科目题型包

全程只使用 `GET /api/exam/meta` 返回的当前学科 `qtypes`（英语≠数学）。拆题/组卷下拉与配比表同源。

---

## 3. 相关

- 入库 API：[`exam-bank-ingest.md`](./exam-bank-ingest.md)  
- 组卷 v2：[`exam-bank-assemble-v2.md`](./exam-bank-assemble-v2.md)  
- Chat 卷面：[`exam-chat-paper.md`](./exam-chat-paper.md)  

# Chat 标准卷面与答题

> **状态**：P0–P3 + 入库双通道 + 题库检索 + **做题/盘点意图门闸（感知题库）** 已落地  
> **分支**：`feature/exam-in-chat`

## 闭环

1. Admin **数据入库 → 试卷题库**（`/admin/ingest?channel=exam`）或题库矩阵「试卷入库」→ 得到 `source_paper_id`。  
   **知识文档**通道只进向量库，不产生可答题卷。
2. 用户说「把…卷拿出来做 / 开始答题」等 → **服务端确定性门闸**（不依赖模型是否调工具）：
   - `is_exam_take_intent` → `search_source_papers`（匹配标题/文件名/**题库地区·学科·年级·库名**）
   - 1 命中 → 直接出 `exam_paper` 卷面卡片  
   - 多命中 → `exam_candidates` 点选  
   - 0 命中 → 提示走题库入库（**禁止**用通识编造试卷概况）
3. 用户说「题库里有什么 / 有哪些试卷」等 → **盘点门闸**（`is_exam_inventory_intent`）：
   - 列出 exam_bank 题库与已入库试卷（**禁止** `list_kb_sources` / 知识库 PDF 列表）
   - 空库 → 引导「数据入库 → 试卷题库」
4. 旁白 Markdown：`MarkdownContent` 仅有数学定界符时启用 KaTeX。

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/exam/chat/papers/search?q=` | 按标题/文件名/题库属性模糊检索 |
| GET | `/api/exam/chat/papers/{source_paper_id}` | 标准卷面 JSON（默认无答案） |
| POST | `/api/exam/chat/attempts` | 开始答题 |
| POST | `/api/exam/chat/attempts/{id}/submit` | 交卷（客观题规则判分） |
| POST | `/api/exam/chat/questions/{question_id}/explain` | **大模型分步讲解**（可选带 user_answer） |

## 判题 / 讲解方案

| 能力 | 实现 | 说明 |
|------|------|------|
| 单选 / 多选 / 填空（有标答） | `chat_paper.grade_attempt` 规则判分 | 交卷即时出分，不耗 LLM |
| 解答 / 作文 | 交卷标记「未自动判分」 | 卷面 **AI 讲解本题** 或对话「讲解第 N 题」 |
| 分步讲解 | Tool `explain_exam_question` + API `/explain` | 复用 `exam_bank.llm_client`，Skill `exam-in-chat` 交卷后 workflow |
| Agent 追问 | 任务模式 + Skill | 用户说「为什么第 3 题错了」→ 调 tool |

## 关键模块

- `exam_bank/exam_intent.py` — 做题 / **盘点**意图与关键词抽取  
- `exam_bank/chat_exam_gate.py` — 门闸：检索或盘点题库并生成 SSE / ui_blocks  
- 挂载点：`stream_rag_chat`、`stream_agent_lead` 入口  

## Skill / Tool（补充）

- `list_exam_bank` + `search_exam_papers` + `present_exam_paper` + **`explain_exam_question`** 可供 Agent 显式调用  
- 门闸保证「没调工具也能感知题库」，且 **题库盘点不会误走知识库**

## 手动验证

1. 试卷入库一份「浙江·数学·高三」卷。  
2. Chat：「现在题库里有什么内容」→ 应出现题库/试卷表，**不是**知识库 PDF 列表。  
3. Chat：「将入库的浙江高三卷子拿出来给我做」→ 工具轨迹 + 标准卷面「开始答题」。  
4. 普通制度问答不受影响。

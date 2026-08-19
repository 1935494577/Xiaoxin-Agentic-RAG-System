# Enterprise RAG

面向企业制度与长文档的检索增强生成（RAG）服务：原始文档经清洗与父子两级分块后，子块量化为向量并写入向量库，父块参与 BM25 与上下文拼装；查询经改写、混合检索与重排后，由大模型生成回答，并通过 **LangGraph** 工作流完成校验与引文整理。可选 **Presidio** 脱敏、接口层访问控制与安全响应头。

**当前能力与架构总览（As-Is）** → [`docs/项目说明.md`](docs/项目说明.md)

---

## 已实现功能

| 模块 | 说明 |
|------|------|
| **文档处理** | 解析与清洗（`document_loader`）、父子分块与持久化（`chunker`） |
| **索引** | 向量写入 Milvus Lite（或 numpy 回退）、父文档 BM25（`indexing`）；可选 Elasticsearch 父索引 |
| **嵌入与重排** | FlagEmbedding / sentence-transformers、CrossEncoder 重排；可选 **ModelScope** 下载到 `enterprise_rag/data/models` |
| **检索** | 查询改写、**检索模式路由**（exact / semantic / hybrid，见 [`docs/retrieval-mode-routing-plan.md`](docs/retrieval-mode-routing-plan.md)）、向量 + BM25 **RRF 融合** + 重排；**L3 检索去重**（文本相似度 + MMR）；**检索结果缓存**（Redis 或进程内 TTL 回退）；**Query Understanding 分层**（口语/语音清洗 → 手动 alias canonical 纠错 → 领域词表 fuzzy variant → embedding 近邻 → 条件 LLM rewrite → 多路 RRF）；**灰区/弱命中 LLM judge**（strict KB 未通过则清空 ctx，避免寒暄被脏片段带偏）；反馈闭环 **apply_query_alias** |
| **入库去重** | **L1** 文档 content_hash 别名跳过重复嵌入；**L2** 父块 simhash 近似去重（`indexing/ingest_dedup`） |
| **对话智能体** | LangGraph / SSE；**助手模式**（知识 / 任务 / 自动，默认知识）；**寒暄短路**；**ExecutionTimeline**；**多架构 RAG 调度**（Classic / Graph / Agentic，见 `docs/rag_architecture_router.md`）；**KB-only 默认 direct**；业务场景预设；检索置信度路由；多轮 L1–L4（`docs/conversation-context.md`）；思考模式；**kb_search**；人物关系图；**实时工具 grounding**（`get_weather` 地点校验/别名；`web_search` 时效窗口+权威气象域名；台风/纠错轮强制联网核实）。总览见 [`docs/项目说明.md`](docs/项目说明.md) |
| **HTTP API** | FastAPI：健康检查、入库、**关系入库**、**领域词表重建**、**语音转写**、检索调试、流式对话、会话记忆、可插拔提示词、**场景预设 API**（`POST /config/ui/scene-preset/{id}`）、模型/向量库/UI 配置（`api`） |
| **安全** | 可选 `RAG_API_SECRET`、**`RAG_ADMIN_API_SECRET`**；CORS、可信 Host；**登录身份绑定**（Chat/题库不信任客户端 `user_id`）；**租户由 `auth.tenant_id` 决定**（不信任 `X-Tenant-ID` / body `tenant_id`）；Admin 角色；前端 RequireAuth；注入检测；部门 + ACL |
| **前端** | **Jnao Chat** React SPA（8502）：流式对话；**助手模式切换**（知识/任务/自动，默认知识）；**执行步骤时间线**；**语音输入**；**Chat 内交互关系图**（ECharts）；**聊天公式 KaTeX**（定界符门闸，无公式不渲染）；**Chat 标准卷面卡片**（`ExamPaperCard`：预览 / 开始答题 / 客观题交卷 / 交卷后 **AI 讲解本题**；多选 checkbox；多命中 `ExamCandidateList` 点选）；**SQLite 登录**与**用户资料**；**新话题**；**部门功能门控**；**React 管理后台**（`/admin`）：侧边栏分组（日常运营 / 质量闭环 / 系统配置）、各页「怎么用」指南、**结构化链路详情**（反馈 Trace）；**数据入库双通道**（知识文档 / 试卷题库）；**题库组卷**（`/admin/exam-bank`：学科/年级/地区题库、录题、按配比组卷并导出 Markdown/Word/PDF；场景 `exam_assemble`）；**Token 用量**（本项目 SQLite：全局总量 + 按用户提问聚合 + 今日一览）；入库、工具（含 **MCP 服务器** 可视化配置，见 [`docs/mcp-config.md`](docs/mcp-config.md)）、提示词、模型、对话设置、评测报告、IM 渠道等；**UI 设计系统**（Card/Table/EmptyState/Skeleton 原语、阴影层级 tokens、骨架屏加载态）；**深色模式**（`.dark` 双套色板 + `useTheme` 切换 + 首屏防闪烁）；会话按日期分组、引用来源 chip 化、消息悬停操作（复制/反馈） |
| **题库子系统** | 独立 SQLite + `/api/exam/*`；**地区·学科·年级** 独立建库；入库（DOCX 公式 `[[EQ]]` 占位 + 清洗 + **默认大模型拆题**；**PDF/扫描件** 可选 PP-StructureV3 + **PP-FormulaNet** → `$LaTeX$`）；智能组卷（**默认仅完整题**；**未选难度则随机、不足按库内存量出卷**）；管理页「待补全 / LLM 补全」；**默认导出 Word 国标排版**；**Chat 感知题库**（做题/盘点意图门闸 + **ACL** + **精确查卷** UUID/关键词优先；客观题规则判分；**LLM 分步讲解** `POST /api/exam/chat/questions/{id}/explain`）；工具 `list_exam_bank` + `search_exam_papers` + `present_exam_paper` + **`explain_exam_question`** + Skill `exam-in-chat`；见 [`docs/exam-chat-paper.md`](docs/exam-chat-paper.md) |
| **用户反馈（Sprint A–D）** | 👍👎 反馈 → Triage → 采纳 → **Actuator**（golden / 重入库工单 / 配置补丁 / **query alias**）→ **alias 候选排序**（`GET /admin/feedback/alias-proposals`）→ **golden 评测**（RAGAS 或 naive 回退，对比上一份 Δ）；`config_revisions` 可回滚；Admin **评测报告**页；Feedback 故障时 **Chat 热路径不受影响** |
| **Harness / IM** | DeerFlow 对齐的 harness：`config.yaml`、`run-dev-harness.ps1`（8010+8011+8502）；IM Worker 在 **8011**；**Chat 流式路由**（`CHAT_LEAD_AGENT_ENABLED`：task/auto→DeerFlow lead，knowledge→KB 快路径）；规范见 [`docs/deerflow-integration.md`](docs/deerflow-integration.md) |
| **评测与追踪** | **Langfuse v4**（可选，`LANGFUSE_*`，见 [`docs/langfuse-tracing.md`](docs/langfuse-tracing.md)）+ 本地 JSONL（`LOCAL_TRACE_ENABLED`，Admin 反馈可回放）；DeerFlow 8011 共用 Langfuse；`scripts/eval_ingest_dedup.py` 等 |
| **容器与脚本** | `Dockerfile`、`docker-compose.yml`（profiles：`cache`/`db`/`app`/`legacy`）；外部依赖见 [`docs/external-dependencies.md`](docs/external-dependencies.md)；Windows `.ps1` 与 **macOS/Linux `.sh`** 一键启停；**生产启动** `run-api-prod.ps1` / `run-api-prod.sh`；**缓存清理** `clean-cache.ps1` |

---

## 不纳入版本库的内容

以下条目由 `.gitignore` 排除，请勿把密钥与纯本地产物推送到远程：

- **`.env`**（从 `.env.example` 复制后本地填写密钥与模型服务地址）
- **内部规划稿**：`PROJECT_PLAN.md`、`plan1.md`、`project.txt`
- **虚拟环境与缓存**：`.venv/`、`__pycache__/`、`.pytest_cache/` 等
- **运行期索引与数据产物**：`enterprise_rag/data/milvus_lite/`、`bm25_index.json`、`numpy_vectors.json`、`chunks_*.jsonl`、`processed/**`（除 `.gitkeep`）、`feedback.jsonl`、`golden.jsonl`、`knowledge_graph.db` 等
- **本地 scratch / 调试产物**：`11.txt`、`out.json`、`_ingest_*.txt`、`_sample_*.docx`、`_t.docx`、`debug-*.log`、`.codegraph/`、`enterprise_rag/data/_audit_tmp/`、`enterprise_rag/data/_bench_tmp/`

**嵌入与重排模型**默认下载到 `enterprise_rag/data/models/`，**不纳入 Git**（由 `.gitignore` 排除）；克隆仓库后请在本地按上文「模型获取」方式自行下载权重。

---

## 项目目录结构

```text
xiaoxin_RAG/
├── .env.example                 # 环境变量模板（复制为 .env）
├── .gitignore
├── README.md
├── LICENSE
├── Makefile
├── docker-compose.yml
├── Dockerfile
├── pytest.ini
├── requirements.txt             # 运行依赖（含可选 modelscope）
├── requirements-gpu.txt
├── docs/
│   ├── 项目说明.md              # 当前能力与结构总览（As-Is）
│   ├── optimization-checklist.md # P0–P2 安全/工程优化状态
│   ├── retrieval-mode-routing-plan.md
│   ├── external-dependencies.md # 外部依赖（LLM/Redis/PG/Tavily…）与 Compose profiles
│   ├── data-platform.md         # 全平台数据层：共享/私有、PG 目标架构
│   ├── data-platform-issues.md  # 数据平台实施问题记录
│   ├── exam-bank-api.md         # 题库/组卷 API 实施与闭环
│   ├── exam-bank-issues.md      # 题库实施问题记录
│   ├── exam-chat-paper.md       # Chat 卷面 / 做题 / ACL
│   ├── exam-bank-routing.md     # 试卷 LLM 路由与组卷
│   ├── exam-bank-assemble-v2.md # 组卷配比 v2
│   ├── exam-bank-ingest.md      # 试卷入库：CRUD / PDF·Word / 答案关联
│   ├── exam-bank-wizard.md      # Admin 向导
│   ├── exam-bank-basket.md      # 试题篮
│   ├── conversation-context.md  # 多轮上下文 L1–L4
│   ├── query-understanding.md   # Query Understanding
│   ├── deerflow-integration.md  # DeerFlow / harness 规范
│   ├── rag_architecture_router.md
│   ├── lan_api_chat.md          # 局域网 API
│   ├── deploy_security.md
│   └── production_deploy.md
├── deploy/
│   └── nginx-api.conf.example
├── enterprise_rag/
│   ├── data/
│   │   ├── raw/                 # 原始文档（含示例 sample.txt）
│   │   ├── processed/         # 清洗输出（运行生成，默认不提交）
│   │   ├── chunks/            # 分块 JSONL（运行生成，默认不提交）
│   │   ├── models/            # 嵌入 / 重排权重（本地缓存，不提交）
│   │   ├── eval/              # 评测示例与占位
│   │   └── milvus_lite/       # Milvus Lite 数据目录（不提交）
│   └── src/                   # 应用源码（PYTHONPATH / Uvicorn 工作目录）
│       ├── api/               # FastAPI 路由、Schema、鉴权
│       ├── agent/             # LangGraph 编排；tools/ 为 Chat 对话工具（与入库 processing 独立）
│       ├── chunker/
│       ├── document_loader/
│       ├── indexing/          # Milvus、BM25、嵌入、modelscope_hub
│       ├── retrieval/
│       ├── security/
│       ├── evaluation/
│       ├── config.py
│       └── runtime_device.py
├── frontend/
│   └── src/                    # Jnao Chat React SPA（Vite，端口 8502）+ `/admin`
├── scripts/                     # 安装、启停 API/前端/Chat、评测与预下载
└── tests/                       # pytest 用例（根目录集成测试 + unit/ 模块单测）
```

> **天赋引导式测评**已拆至独立目录 `D:\天赋测试设计方案`（Assessment API 8020 + H5 8520），与本仓库无代码依赖。

---

## 如何操作

### 平台说明

| 平台 | 一键开发 | 仅 API | 管理后台 | 停止服务 |
|------|----------|--------|----------|----------|
| **Windows** | `.\scripts\run-dev.ps1` | `.\scripts\run-api.ps1` | `.\scripts\run_frontend.ps1` | `.\scripts\stop-dev.ps1` |
| **Windows（IM 渠道 / 任务 Agent）** | `.\scripts\run-dev-harness.ps1` | `.\scripts\run-harness-gateway.ps1`（8011） | 同 8502 `/admin/` | `.\scripts\stop-dev.ps1` |
| **Windows（局域网分享 Chat 页面）** | `.\scripts\run-chat-lan-kb.ps1` | — | 同端口 `/admin/` | `.\scripts\stop-dev.ps1` |
| **Windows（局域网暴露 RAG API）** | `.\scripts\run-api-lan.ps1` | 同事直连 `:8010` | — | `.\scripts\stop-dev.ps1` |
| **macOS / Linux** | `./scripts/run-dev.sh` | `./scripts/run-api.sh` | `./scripts/run_frontend.sh` | `./scripts/stop-dev.sh` |

> macOS 不能直接运行 `.ps1`（除非单独安装 PowerShell）。克隆后先赋予执行权限：  
> `chmod +x scripts/*.sh`

**macOS 首次安装：**

```bash
cd <仓库根目录>
./scripts/bootstrap_venv.sh    # 创建 .venv 并安装依赖
cp .env.example .env           # 编辑 API Key 等
./scripts/run-dev.sh           # API 8010 + Frontend SPA 8502（Chat + /admin）
```

依赖：**Python 3.10+**、**Node.js LTS**（Chat SPA）、可选 **Homebrew** 安装 `python3` / `node`。

#### 局域网同事调用 RAG API（推荐：自有客户端 / 脚本）

不开放前端，仅暴露后端 FastAPI，同事请求你本机的 **8010** 端口：

```powershell
.\scripts\stop-dev.ps1
.\scripts\run-api-lan.ps1 -KbOnly
# 首次连不上（管理员）：.\scripts\run-api-lan.ps1 -KbOnly -OpenFirewall
```

接口说明与 curl/Python 示例见 **[docs/lan_api_chat.md](docs/lan_api_chat.md)**。核心端点：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 连通性 |
| POST | `/chat` | 一次性 JSON 回答 |
| POST | `/chat/stream` | SSE 流式（与前端相同协议） |

请求体需含 `message`、`user_id`、`user_department`；知识库专用请加 `"hybrid_expert_mode": false`。

#### 局域网同事访问 Chat 页面（可选）

若同事用浏览器而非 API，见 `run-chat-lan-kb.ps1`（端口 **8502**）。

---

### 1. 安装依赖（Windows 示例）

```powershell
cd <仓库根目录>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

**macOS / Linux：**

```bash
./scripts/bootstrap_venv.sh
cp .env.example .env
source .venv/bin/activate
```

编辑 **`.env`**：至少配置 OpenAI 兼容的 **`OPENAI_API_BASE`**、**`OPENAI_API_KEY`**、**`OPENAI_CHAT_MODEL`**；按需设置 **`USE_MODELSCOPE_DOWNLOAD`**、`EMBEDDING_MODEL`、`RERANKER_MODEL`、`HF_HUB_CACHE`、`TORCH_DEVICE` 等。**流式对话建议 `STREAM_SKIP_RERANK=false`**（重排分用于 KB/通用路由与引用门控）。修改后需重启 API。

### 2. 启动 HTTP API

```powershell
cd enterprise_rag\src
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8010
```

- 开发态文档：<http://127.0.0.1:8010/docs>（若未在 `.env` 中关闭）
- 健康检查：`GET /health`

### 3. 入库示例（`data/raw` 下文件）

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8010/ingest/path?relative_path=sample.txt" -Method Post
```

亦支持：`POST /ingest/text`（JSON 正文）、`POST /ingest/upload`（multipart）、`POST /ingest/preview`（仅清洗预览）。

### 4. 对话

```powershell
$b = @{ message = "你的问题"; user_id = "u1"; user_department = "general" } | ConvertTo-Json -Compress
Invoke-RestMethod -Uri "http://127.0.0.1:8010/chat" -Method Post -Body $b -ContentType "application/json; charset=utf-8" -TimeoutSec 180
```

返回字段包含 **`answer`**、**`sources`**、**`rewritten_query`**。若配置了 **`RAG_API_SECRET`**，请求需携带约定鉴权头（见 `docs/deploy_security.md`）。

### 5. 一键闭环（不启独立 HTTP）

在仓库根目录：

```powershell
.\.venv\Scripts\python.exe scripts\run_closed_loop.py
```

顺序：`Milvus Lite` 检查 → `TestClient` 调 `/health` → `/ingest/path` → `/chat` → `/feedback`。

### 6. 测试

```powershell
cd <仓库根目录>
pytest
```

**部门 ACL 集成测试**（使用 `d:\dataset\各年级要求.txt`，索引写入临时目录，不污染生产库）：

```powershell
pytest tests/test_dept_acl_integration.py -v
# 自定义数据路径：
$env:ACL_TEST_DATASET="D:\dataset\各年级要求.txt"
pytest tests/test_dept_acl_integration.py -q
```

### 7. React 前端（Chat + Admin）

统一 **React SPA**（`frontend/`）：Jnao Chat 与 React 管理后台同域，本地开发端口 **8502**。

**Windows：**

```powershell
cd <仓库根目录>
.\scripts\run_frontend.ps1
```

**macOS / Linux：**

```bash
./scripts/run_frontend.sh
```

一键启动 API + 前端：Windows 用 `run-dev.ps1` 或 `run-dev-harness.ps1`（含 Harness 8011），macOS 用 `./scripts/run-dev.sh`。

**本地开发端口：**

| 服务 | 端口 | 说明 |
|------|------|------|
| API | 8010 | FastAPI / Uvicorn（Enterprise RAG） |
| Harness Gateway | 8011 | DeerFlow 对齐网关（可选，`run-dev-harness.ps1`） |
| Frontend SPA | 8502 | Chat（`/chat`）+ Admin（`/admin/*`） |

### 8. Docker（可选）

外部依赖清单：**[`docs/external-dependencies.md`](docs/external-dependencies.md)**（LLM / Redis / PG / Tavily / 遗留 Milvus）。

```bash
# 本机跑 API，只起 Redis（推荐）
docker compose --profile cache up -d
# REDIS_URL=redis://127.0.0.1:6379/0

# PostgreSQL（数据平台 DATABASE_URL，规划中）
docker compose --profile db up -d

# API 也进容器（端口 8010）+ Redis
docker compose --profile app --profile cache up -d --build

# 遗留：远程 Milvus + Elasticsearch
docker compose --profile legacy up -d
```

Windows：`.\scripts\infra-up.ps1 cache`（或 `db` / `legacy` / `app`）。编排见 **`docker-compose.yml`**、**`Dockerfile`**；反代见 **`deploy/`**。

### 9. 生产部署（性能 / 内存 / 落地）

- 配置模板：**`.env.production.example`**（小模型、Redis 缓存、安全项）
- 完整步骤：**[`docs/production_deploy.md`](docs/production_deploy.md)**
- 生产启动（无热重载）：`.\scripts\run-api-prod.ps1` 或 `./scripts/run-api-prod.sh`

---

## 主要 HTTP 路径

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 存活探测 |
| GET | `/config/public` | 公开运行配置（无密钥） |
| GET/POST/PUT | `/config/ui` `/config/prompts` `/config/processing-tools` `/config/agent-tools` … | UI、提示词、入库工具、**对话工具**等配置 |
| GET/POST/PUT/DELETE | `/config/model-profiles`… | 多供应商模型档案（密钥仅存服务端） |
| POST | `/chat` | RAG 对话（LangGraph） |
| POST | `/chat/stream` | SSE 流式对话（Chat SPA 使用） |
| POST | `/retrieve` | 混合检索 + 重排调试（不调用 LLM 生成） |
| GET/POST | `/chat/sessions`… | 会话与历史消息 |
| GET/PUT | `/users/profile` | 用户资料（昵称、头像、部门权限，SQLite） |
| POST | `/feedback` | 用户反馈（SQLite + 异步 trace 补全） |
| GET | `/admin/feedback` | Admin 反馈列表（状态/严重度筛选） |
| POST | `/admin/feedback/triage` | 批量规则/LLM 研判 |
| POST | `/admin/feedback/{id}/approve` | 采纳并执行 Actuator 动作 |
| GET | `/admin/feedback/config-revisions` | 配置变更版本列表 |
| POST | `/admin/feedback/config-revisions/{id}/rollback` | 回滚配置补丁 |
| POST | `/admin/feedback/evaluate` | 手动触发 golden 评测 |
| GET | `/admin/feedback/eval-reports` | 评测报告列表（含指标 delta） |
| POST | `/admin/feedback/eval-reports/export` | 导出评测报告 JSON |
| POST | `/ingest/preview` | 清洗预览 |
| POST | `/ingest/text` | 文本入库（响应含 `dedup` 去重统计） |
| POST | `/ingest/path` | 按 `data/raw` 相对路径入库 |
| POST | `/ingest/upload` | 上传文件入库 |

---

## 模型与仓库

- **默认缓存目录**：`enterprise_rag/data/models`（可通过 **`MODELSCOPE_CACHE_DIR`** 或 **`HF_HUB_CACHE`** 调整）。
- 权重文件**不随仓库推送**；首次运行入库或对话时会按 `.env` 从魔搭或 Hugging Face 拉取（或提前运行 `scripts/download_rag_models.py` 等脚本）。
- 若你希望团队共享同一套离线权重，可自建对象存储或网盘分发，**不要**把大文件硬塞进 Git；单文件超过 GitHub 约 **100MB** 会直接被拒。

---

## 更多文档

- **现状总览：[`docs/项目说明.md`](docs/项目说明.md)**
- 安全与网关：**`docs/deploy_security.md`**
- 生产部署（性能 / 内存）：**`docs/production_deploy.md`**
- DeerFlow / harness：**`docs/deerflow-integration.md`**

## 许可证

MIT，见仓库根目录 **`LICENSE`**。

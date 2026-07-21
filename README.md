# Enterprise RAG

面向企业制度与长文档的检索增强生成（RAG）服务：原始文档经清洗与父子两级分块后，子块量化为向量并写入向量库，父块参与 BM25 与上下文拼装；查询经改写、混合检索与重排后，由大模型生成回答，并通过 **LangGraph** 工作流完成校验与引文整理。可选 **Presidio** 脱敏、接口层访问控制与安全响应头。

---

## 已实现功能

| 模块 | 说明 |
|------|------|
| **文档处理** | 解析与清洗（`document_loader`）、父子分块与持久化（`chunker`） |
| **索引** | 向量写入 Milvus Lite（或 numpy 回退）、父文档 BM25（`indexing`）；可选 Elasticsearch 父索引 |
| **嵌入与重排** | FlagEmbedding / sentence-transformers、CrossEncoder 重排；可选 **ModelScope** 下载到 `enterprise_rag/data/models` |
| **检索** | 查询改写、向量 + BM25 混合检索、重排；**L3 检索去重**（文本相似度 + MMR）；**检索结果缓存**（Redis 或进程内 TTL 回退）；**Query Understanding 分层**（口语/语音清洗 → 手动 alias canonical 纠错 → 领域词表 fuzzy variant → embedding 近邻 → 条件 LLM rewrite → 多路 RRF）；**灰区/弱命中 LLM judge**（strict KB 未通过则清空 ctx，避免寒暄被脏片段带偏）；反馈闭环 **apply_query_alias** |
| **入库去重** | **L1** 文档 content_hash 别名跳过重复嵌入；**L2** 父块 simhash 近似去重（`indexing/ingest_dedup`） |
| **对话智能体** | LangGraph / SSE；**助手模式**（知识 / 任务 / 自动，`assistant_mode` 驱动路由与工具）；**ExecutionTimeline**（检索→工具→生成步骤）；**多架构 RAG 调度**（Classic / Graph / Agentic 自动或手动路由，见 `docs/rag_architecture_router.md`）；**graph+agentic 双信号优先 Graph**；**KB-only 默认 direct 推理**（`resolve_effective_reasoning_mode`）；**业务场景预设**（一线 KB / 内测全功能 / LAN API，Admin 一键应用）；**检索置信度路由**（rerank confident/gray/weak，引用仅 confident）；**多轮上下文** L1–L4（见 `docs/conversation-context.md`）；**routing_model** 预处理与生成模型分离；**chat_routing_tier**（fast/balanced/quality）；`reset_context` / 滚动摘要；**角色人设预设**（劲脑脑科教育 7 套，管理端选项卡切换）；**思考模式**（直接回答 / ReAct / Plan-and-Execute）；**kb_search** 工具（Agentic 多轮检索）；**人物关系图**（`show_relationship_graph` 快路径 + SQLite 知识图谱）；详见 `docs/assistant-fusion-plan.md` |
| **HTTP API** | FastAPI：健康检查、入库、**关系入库**、**领域词表重建**、**语音转写**、检索调试、流式对话、会话记忆、可插拔提示词、**场景预设 API**（`POST /config/ui/scene-preset/{id}`）、模型/向量库/UI 配置（`api`） |
| **安全** | 可选 `RAG_API_SECRET`、**`RAG_ADMIN_API_SECRET`**（管理 API 独立密钥）、CORS、可信 Host、安全头；**Admin 角色**（`X-Admin-Role`：viewer/operator/admin）；**前端 RequireAuth**（未登录跳转 `/login`）；注入检测；**部门 + 可见范围 ACL** |
| **租户预留（Sprint E）** | `X-Tenant-ID` 中间件（默认 `internal`）；`/api/v1/*` 路由别名；`FeedbackStore` / `TraceStore` 抽象 |
| **前端** | **Jnao Chat** React SPA（8502）：流式对话；**助手模式切换**（知识/任务/自动）；**执行步骤时间线**；**语音输入**；**Chat 内交互关系图**（ECharts）；**SQLite 登录**与**用户资料**；**新话题**；**部门功能门控**；**React 管理后台**（`/admin`）：侧边栏分组（日常运营 / 质量闭环 / 系统配置）、各页「怎么用」指南、**结构化链路详情**（反馈 Trace）；**Token 用量**（本项目 SQLite 独立计量：全局总量 + 每次 LLM 调用记录；Chat 工具栏会话徽章）；入库、工具、提示词、模型、对话设置（含默认助手模式与场景预设）、评测报告、IM 渠道等 |
| **用户反馈（Sprint A–D）** | 👍👎 反馈 → Triage → 采纳 → **Actuator**（golden / 重入库工单 / 配置补丁 / **query alias**）→ **alias 候选排序**（`GET /admin/feedback/alias-proposals`）→ **golden 评测**（RAGAS 或 naive 回退，对比上一份 Δ）；`config_revisions` 可回滚；Admin **评测报告**页；Feedback 故障时 **Chat 热路径不受影响** |
| **规划中（Sprint G / DF-0）** | DeerFlow harness：`config.yaml`、`.venv-harness`、`scripts/bootstrap-harness-venv.ps1`、`run-dev-harness.ps1`（8010+8011+8502）；IM 渠道 Worker 在 **8011**；详见 [`docs/deerflow-integration.md`](docs/deerflow-integration.md) §9 |
| **评测与追踪** | 可选 LangSmith / 本地 JSONL trace；`scripts/eval_ingest_dedup.py` 检索去重 A/B；`scripts/eval_query_robustness.py`（分 scenario 汇总）/ `scripts/query_verify.ps1`；`docs/query-understanding.md` |
| **容器与脚本** | `Dockerfile`、`docker-compose.yml`、`Makefile`；Windows `.ps1` 与 **macOS/Linux `.sh`** 一键启停；**生产启动** `run-api-prod.ps1` / `run-api-prod.sh`；**缓存清理** `clean-cache.ps1` |

---

## 不纳入版本库的内容

以下条目由 `.gitignore` 排除，请勿把密钥与纯本地产物推送到远程：

- **`.env`**（从 `.env.example` 复制后本地填写密钥与模型服务地址）
- **内部规划稿**：`PROJECT_PLAN.md`、`plan1.md`、`project.txt`
- **虚拟环境与缓存**：`.venv/`、`__pycache__/`、`.pytest_cache/` 等
- **运行期索引与数据产物**：`enterprise_rag/data/milvus_lite/`、`bm25_index.json`、`numpy_vectors.json`、`chunks_*.jsonl`、`processed/**`（除 `.gitkeep`）、`feedback.jsonl`、`golden.jsonl`、`knowledge_graph.db` 等
- **本地调试/审计产物**：`debug-*.log`、`.codegraph/`、`enterprise_rag/data/_audit_tmp/`、`enterprise_rag/data/_bench_tmp/`

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
│   ├── conversation-context.md  # 多轮上下文 L1–L4 架构说明
│   ├── query-understanding.md   # Query Understanding 分层与治理
│   ├── assistant-fusion-plan.md # 助手融合阶段计划
│   ├── deerflow-integration.md # DeerFlow 集成规范（实现唯一依据）
│   ├── deploy_security.md       # 部署与安全建议
│   └── phase1_acceptance.md     # 阶段 1 总验收清单
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
./scripts/run-dev.sh           # API 8010 + Chat 8502 + 管理后台 8501
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

### 7. Streamlit 前端（可选）

**Windows：**

```powershell
cd <仓库根目录>
.\scripts\run_frontend.ps1
```

**macOS / Linux：**

```bash
./scripts/run_frontend.sh
```

一键启动三端（API + Chat + 管理后台）：Windows 用 `run-dev.ps1`，macOS 用 `./scripts/run-dev.sh`。

**本地开发端口：**

| 服务 | 端口 | 说明 |
|------|------|------|
| API | 8010 | FastAPI / Uvicorn（Enterprise RAG） |
| 管理后台 | 8501 | Streamlit |
| Jnao Chat | 8502 | React SPA（`frontend/`） |

### 8. Docker（可选）

见根目录 **`docker-compose.yml`** 与 **`Dockerfile`**，结合 **`deploy/`** 下 Nginx 示例做反向代理与 TLS。

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

- 安全与网关：**`docs/deploy_security.md`**
- **生产部署（性能 / 内存）：`docs/production_deploy.md`**
- 变更记录：**`docs/changelog.md`**

## 许可证

MIT，见仓库根目录 **`LICENSE`**。

# 外部依赖清单

> **As-Is**：本文件描述运行 Jnao 时可能用到的**进程外**依赖（SaaS、中间件、可选容器）。  
> Docker 编排见根目录 [`docker-compose.yml`](../docker-compose.yml)。数据层演进见 [`data-platform.md`](./data-platform.md)。

---

## 1. 总览

| 类别 | 依赖 | 本地开发 | 生产建议 | 可 Docker 化 |
|------|------|----------|----------|--------------|
| **必填 SaaS** | OpenAI 兼容 LLM（如 DeepSeek） | `.env` `OPENAI_*` | 同左 | 否（HTTP） |
| **进程内默认** | Milvus Lite / NumPy 向量 + BM25 | 无额外服务 | Lite 或远程 Milvus | Lite 在 API 容器内 |
| **推荐中间件** | Redis（检索缓存） | 可不配（进程内 TTL） | 多 worker 必配 | `profile: cache` |
| **规划中** | PostgreSQL（元数据 / ACL） | `DATABASE_URL` 空=SQLite | 线上填 PG | `profile: db` |
| **可选 SaaS** | Tavily（联网搜索） | `TAVILY_API_KEY` | 按需 | 否 |
| **可选 SaaS** | LangSmith | `LANGCHAIN_TRACING_V2` | 按需 | 否 |
| **可选下载** | 嵌入/重排模型（ModelScope / HF） | `data/models/` | 预下载 | 卷挂载 |
| **遗留栈** | 远程 Milvus + etcd + MinIO + ES | 一般不用 | 大规模向量时 | `profile: legacy` |
| **本机进程** | Frontend / Harness Gateway | `run-dev*.ps1` | 可另容器化 | 当前未进 compose |

---

## 2. 必填：LLM API

| 变量 | 说明 |
|------|------|
| `OPENAI_API_BASE` | 兼容 OpenAI 的 Base（默认 DeepSeek） |
| `OPENAI_API_KEY` | 密钥 |
| `OPENAI_CHAT_MODEL` | Chat / 试卷路由等 |
| `OPENAI_ROUTING_MODEL` | 可选；空则与 CHAT 相同 |

无密钥时 Chat / 试卷 LLM 路由不可用；题库 SQLite CRUD 仍可跑。

---

## 3. 推荐：Redis

- **用途**：混合检索结果缓存（非 LLM 答案缓存）。  
- **回退**：`REDIS_SEARCH_CACHE_ENABLED=true` 且无 `REDIS_URL` → 进程内 TTL。  
- **Docker**：

```bash
docker compose --profile cache up -d
# .env
REDIS_URL=redis://127.0.0.1:6379/0
```

与 API 同 compose 网络时：`REDIS_URL=redis://redis:6379/0`。

---

## 4. 规划：PostgreSQL

- **用途**：全平台元数据 / 题库 ACL 等（见 `data-platform.md`）；当前代码以各业务 SQLite 为主，`DATABASE_URL` 为配置位。  
- **Docker**：

```bash
docker compose --profile db up -d
# 示例
DATABASE_URL=postgresql+psycopg://jnao:jnao@127.0.0.1:5432/jnao
```

容器内互访主机名：`postgres`（用户/库/密码默认 `jnao`，可用环境变量覆盖）。

---

## 5. 可选：Tavily / LangSmith / 模型源

| 依赖 | 变量 | 说明 |
|------|------|------|
| Tavily | `TAVILY_API_KEY` | 对话工具 `web_search` |
| LangSmith | `LANGCHAIN_*` | 链路追踪 |
| ModelScope | `USE_MODELSCOPE_DOWNLOAD` | 国内拉嵌入/重排权重 |
| HuggingFace | `HF_LOCAL_FILES_ONLY` 等 | 本地只读已下载权重 |

---

## 6. 遗留：远程 Milvus + Elasticsearch

默认路径是 **Milvus Lite（或 Windows NumPy）+ 本地 BM25**，**不需要** Docker。

仅在需要独立 Milvus Server / ES 父索引时：

```bash
docker compose --profile legacy up -d
# 或
make infra-up
```

---

## 7. Compose profiles 速查

| Profile | 服务 | 命令示例 |
|---------|------|----------|
| `cache` | Redis | `docker compose --profile cache up -d` |
| `db` | PostgreSQL | `docker compose --profile db up -d` |
| `app` | RAG API 镜像 | `docker compose --profile app,cache up -d --build` |
| `legacy` | Milvus+etcd+MinIO+ES | `docker compose --profile legacy up -d` |

推荐组合：

```bash
# 本机跑 API（8010），只起中间件
docker compose --profile cache --profile db up -d

# API 也进容器（8010）+ Redis（可选再加 db）
docker compose --profile app --profile cache up -d --build
```

---

## 8. 不进 Docker 的本机服务

| 端口 | 进程 | 启动 |
|------|------|------|
| 8010 | Main FastAPI | `run-dev.ps1` / `run-api-prod.*` |
| 8011 | Harness Gateway | `run-dev-harness.ps1` |
| 8502 | React Chat/Admin | 同上 |

DeerFlow harness 路径见 `.env` 的 `DEER_FLOW_*`（本地 checkout，非容器服务）。

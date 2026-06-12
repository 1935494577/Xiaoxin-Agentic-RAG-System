# 生产部署指南（性能 · 内存 · 落地）

面向「提升性能、降低内存、对外提供服务」的推荐路径。默认开发配置（`bge-m3` + 全量预热）适合质量验证，**不适合**小内存机器直接上线。

---

## 1. 内存与性能：优先改 `.env`

| 项 | 开发默认 | 生产推荐 | 效果 |
|----|----------|----------|------|
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | `BAAI/bge-small-zh-v1.5` | 嵌入模型内存约 **2GB → 400MB** |
| `EMBEDDING_BACKEND` | `auto` | `sentence_transformers` | 避免 Flag/ST 双路径试探 |
| `QUERY_REWRITE_ENABLED` | `false` | 保持 `false` | 省一次 LLM 调用，降延迟 |
| `STREAM_SKIP_RERANK` | `true` | 保持 `true` | 流式对话跳过重排，显著提速 |
| `USE_PRESIDIO` | `true` | `false`（若网关已脱敏） | 少加载 spaCy 等组件 |
| `EMBEDDING_BATCH_SIZE` | `8` | `2`~`4`（6GB 显存） | 峰值内存更低 |
| `REDIS_URL` + 缓存 | 未配置 | **配置** | 重复检索命中缓存，跳过嵌入/重排 |
| `WARMUP_RERANKER_ON_STARTUP` | `true` | `false`（仅流式+跳过重排） | 启动少占 ~500MB，首次非流式 `/chat` 略慢 |

完整模板见仓库根目录 **`.env.production.example`**：

```bash
cp .env.production.example .env
# 编辑 API Key、RAG_API_SECRET、CORS、REDIS_URL 等
```

### 模型磁盘

首次部署前预下载（避免 API 启动超时）：

```bash
python scripts/download_rag_models.py
```

---

## 2. Redis 检索缓存（无 Docker 也可）

缓存的是 **混合检索结果**（改写 + 向量 + BM25 + 重排），不是 LLM 最终回答。

**无 Redis 时**：若 `REDIS_SEARCH_CACHE_ENABLED=true` 且未配置 `REDIS_URL`，API 自动使用**进程内 TTL 缓存**（单 worker 开发/小规模可用）。生产多 worker 仍建议 Redis。

### Linux 服务器（推荐）

```bash
sudo apt update && sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

`.env`：

```env
REDIS_URL=redis://127.0.0.1:6379/0
REDIS_SEARCH_CACHE_ENABLED=true
REDIS_SEARCH_CACHE_TTL_SECONDS=600
```

### 云 Redis

阿里云 / 腾讯云 Redis 实例填入连接串即可，格式一般为 `redis://:password@host:6379/0`。

### Windows 本机

- 开发可 **不启 Redis**（功能正常，无缓存）
- 或安装 [Memurai](https://www.memurai.com/) / WSL2 内 `redis-server`

---

## 3. 启动 API（生产）

**不要用 `--reload`**。Milvus Lite 与本地 BM25 索引为单进程文件状态，**建议 `--workers 1`**。

### Windows

若直接运行 `.\scripts\run-api-prod.ps1` 报「禁止运行脚本」，任选其一：

```powershell
# 方式 A：单次绕过执行策略（推荐，不改系统设置）
powershell -ExecutionPolicy Bypass -File .\scripts\run-api-prod.ps1

# 方式 B：不依赖 ps1，直接启动
cd enterprise_rag\src
..\..\.venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8010 --proxy-headers --forwarded-allow-ips 127.0.0.1
```

长期本机开发可（仅当前用户）：`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

```powershell
.\scripts\run-api-prod.ps1
```

### Linux / macOS

```bash
chmod +x scripts/run-api-prod.sh
./scripts/run-api-prod.sh
```

或手动：

```bash
cd enterprise_rag/src
python -m uvicorn api.main:app \
  --host 0.0.0.0 --port 8010 \
  --proxy-headers --forwarded-allow-ips 127.0.0.1
```

### 前端

- **Jnao Chat**（用户）：`frontend/chat` 构建后由 Nginx 托管静态文件，调用 `/chat/stream`
- **Streamlit 管理后台**：内网或 VPN 访问，设置 `STREAMLIT_RAG_API_SECRET`

---

## 4. 安全清单

详见 [`deploy_security.md`](deploy_security.md)。生产最低要求：

- [ ] `RAG_API_SECRET` 已设置（非空随机串）
- [ ] `CORS_ALLOW_ORIGINS` 收窄为实际前端域名
- [ ] `DISABLE_OPENAPI_DOCS=true`
- [ ] HTTPS（Nginx / 云 LB），参考 [`deploy/nginx-api.conf.example`](../deploy/nginx-api.conf.example)
- [ ] `TRUSTED_HOSTS` 设为 API 域名
- [ ] `.env` 与 `model_profiles.json` 不进 Git

---

## 5. 硬件参考

| 场景 | CPU | 内存 | GPU | 说明 |
|------|-----|------|-----|------|
| 最小可运行 | 4 核 | **8 GB** | 无 | `bge-small-zh` + 跳过重排 + 无 Presidio |
| 推荐生产 | 8 核 | **16 GB** | 可选 6GB+ | 小嵌入 + 可选重排 + Redis |
| 高质量检索 | 8 核+ | 16 GB+ | 8 GB+ | 可保留 `bge-m3` + 重排 |

无 GPU 时设 `TORCH_DEVICE=cpu`，内存占用更可控，检索会慢一些。

---

## 6. 监控与调优

1. **重复问题多** → 必开 Redis，适当增大 `REDIS_SEARCH_CACHE_TTL_SECONDS`
2. **知识库频繁更新** → 缩短 TTL（如 120s），或入库后重启 API / 等待 TTL 过期
3. **首 token 慢** → 确认 Chat 使用 `/chat/stream` 且 `stream_fast_mode=true`（UI 默认）
4. **OOM** → 降 `EMBEDDING_BATCH_SIZE`、换 small 模型、`WARMUP_RERANKER_ON_STARTUP=false`

---

## 7. 与 Docker 的关系

- **无 Docker**：本指南路径，直接 Python + Redis + Nginx，适合 Windows 开发机与 Linux VPS
- **有 Docker**：`docker compose --profile cache up -d` 启 Redis；API 见 `docker-compose.yml` 的 `app` profile

Docker 未安装不影响落地，按上文 Linux 原生部署即可。

# 部署与安全（Enterprise RAG API）

## 1. 网关密钥 `RAG_API_SECRET`

- 在 `.env` 中设置 **非空** `RAG_API_SECRET` 后，除白名单外所有接口需要鉴权。
- 白名单（无需密钥）：`GET /health`、`GET /`、`GET /favicon.ico`、以及 `OPTIONS` 预检。
- 客户端任选其一请求头：
  - `X-API-Key: <与服务器相同的密钥>`
  - `Authorization: Bearer <与服务器相同的密钥>`

**Streamlit**：侧栏填写「API 访问密钥」，或设置环境变量 `STREAMLIT_RAG_API_SECRET`（推荐在部署环境中注入，避免人工输入）。

## 2. CORS `CORS_ALLOW_ORIGINS`

- 留空：开发态等价于 `*`，且 `allow_credentials=false`（浏览器规范）。
- 生产：逗号分隔，例如  
  `https://your-streamlit-host.example.com,http://localhost:8501`  
  配置后仅允许列出的来源跨域调用 API。

## 3. 关闭 OpenAPI `DISABLE_OPENAPI_DOCS`

- 设为 `true` 时关闭 `/docs`、`/redoc`、`/openapi.json`；根路径 `/` 返回 JSON 说明而非跳转文档。

## 4. 可信主机 `TRUSTED_HOSTS`

- 逗号分隔，例如 `api.example.com,localhost`。
- 非空时启用 `TrustedHostMiddleware`，减轻 Host 头伪造类问题（仍需 HTTPS + 正确 DNS）。

## 5. HSTS `ENABLE_HSTS`

- 仅在 **全站 HTTPS** 且明确需要时设为 `true`，会向浏览器下发 `Strict-Transport-Security`。

## 6. 模型与 LLM 密钥

- `enterprise_rag/data/model_profiles.json` 存 **明文** 厂商 API Key，请限制文件权限并勿提交 Git（已在 `.gitignore`）。
- 生产应对管理类接口再加一层登录或网络隔离（本仓库仅一层共享密钥）。
- 启用 `USE_MODELSCOPE_DOWNLOAD` 时，模型文件落在 `enterprise_rag/data/models/`（或 `MODELSCOPE_CACHE_DIR`），体积较大，勿提交版本库；注意磁盘与备份策略。

## 7. Docker / Uvicorn

- `Dockerfile` 中已加 `--proxy-headers`；置于 Nginx 后时，请将 `--forwarded-allow-ips` 改为上游 IP 段而非 `*`。
- 多 worker：`uvicorn ... --workers 4`（注意 Milvus Lite / 单文件状态是否可多进程共享，numpy 后端一般可）。

## 8. 检查清单

- [ ] `.env` 中 `RAG_API_SECRET` 已设置且仅注入到可信环境  
- [ ] `CORS_ALLOW_ORIGINS` 已收窄  
- [ ] 生产 `DISABLE_OPENAPI_DOCS=true`  
- [ ] HTTPS 终止在 Nginx / 云负载均衡  
- [ ] 数据卷权限与备份策略  
- [ ] 魔搭或 HF 模型缓存目录不在 Git 中且磁盘充足  

更多 Nginx 片段见 `deploy/nginx-api.conf.example`。

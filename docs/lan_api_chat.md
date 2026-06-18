# 局域网调用本机 Chat RAG API

同事在同一 WiFi/网段内，直接请求**你电脑上的 FastAPI**（默认端口 **8010**），无需打开前端页面。

## 1. 本机启动（API 暴露）

```powershell
cd D:\11
.\scripts\stop-dev.ps1          # 若 8010 已被占用
.\scripts\run-api-lan.ps1 -KbOnly # 知识库专用默认（关闭混合专家/通用兜底）

# 同事连不上时（管理员 PowerShell）：
.\scripts\run-api-lan.ps1 -KbOnly -OpenFirewall
```

脚本会打印局域网地址，例如：`http://192.168.1.88:8010`

## 2. 连通性

```bash
curl http://192.168.1.88:8010/health
```

应返回 `{"status":"ok",...}`。

## 3. 鉴权（可选）

若本机 `.env` 配置了 `RAG_API_SECRET`，每次请求需带头：

```http
X-API-Key: <与 RAG_API_SECRET 相同的值>
```

或：

```http
Authorization: Bearer <密钥>
```

未配置 `RAG_API_SECRET` 时，局域网内可直接调用（仅限可信内网）。

## 4. 非流式对话 `POST /chat`

```bash
curl -X POST "http://192.168.1.88:8010/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "1-3年级超脑阅读要求是什么？",
    "user_id": "colleague_zhang",
    "user_department": "技术部",
    "hybrid_expert_mode": false,
    "rag_architecture": "auto",
    "skip_query_rewrite": true
  }'
```

响应 JSON 含 `answer`、`sources`、`answer_mode`（`kb` / `general`）等。

## 5. 流式对话 `POST /chat/stream`（SSE）

```bash
curl -N -X POST "http://192.168.1.88:8010/chat/stream" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "message": "扫描速记有哪些注意事项？",
    "user_id": "colleague_zhang",
    "user_department": "技术部",
    "hybrid_expert_mode": false,
    "rag_architecture": "auto"
  }'
```

每行格式：`data: {"type":"token","content":"..."}`  
结束事件：`data: {"type":"done","answer":"...","sources":[...],...}`

## 6. 知识库专用参数

| 字段 | 建议值 | 说明 |
|------|--------|------|
| `hybrid_expert_mode` | `false` | 仅知识库，不走通用大模型兜底 |
| `user_department` | 与入库部门一致 | 如 `技术部`，控制可见文档 |
| `rag_architecture` | `"auto"` | 服务端自动选 Classic/Graph/Agentic |
| `allowed_sources` | 可选数组 | 限定检索来源文件名 |

服务端 `ui_config` 在 `-KbOnly` 启动时已关闭 `general_fallback_enabled`。

## 7. 多轮与会话（可选）

```json
{
  "message": "继续上一题",
  "user_id": "colleague_zhang",
  "user_department": "技术部",
  "session_id": "uuid-from-post-chat-sessions",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

- 创建会话：`POST /chat/sessions?user_id=...`
- 读历史：`GET /chat/sessions/{id}/messages?user_id=...`

## 8. Python 示例（流式）

```python
import json
import httpx

base = "http://192.168.1.88:8010"
payload = {
    "message": "超脑阅读的要求？",
    "user_id": "colleague_01",
    "user_department": "技术部",
    "hybrid_expert_mode": False,
}
headers = {"Accept": "text/event-stream"}
# headers["X-API-Key"] = "your-secret"  # 若启用了 RAG_API_SECRET

with httpx.stream("POST", f"{base}/chat/stream", json=payload, headers=headers, timeout=120) as r:
    r.raise_for_status()
    for line in r.iter_lines():
        if not line.startswith("data: "):
            continue
        evt = json.loads(line[6:])
        if evt.get("type") == "token":
            print(evt["content"], end="", flush=True)
        elif evt.get("type") == "done":
            print("\n--- sources:", evt.get("sources"))
```

## 9. 注意事项

- 本机需保持运行 API 进程且不要休眠。
- Windows 防火墙需放行 **TCP 8010**（`-OpenFirewall`）。
- LLM Key 配置在你本机 `.env` / 模型配置里，同事**不需要**自己的 Key。
- 检索的是**你本机**向量库与图谱数据，不是云端共享服务。

OpenAPI 文档（开发态）：`http://127.0.0.1:8010/docs`

# ReefAPI 对话工具接入（知识库 Chat）

把 [ReefAPI](https://reefapi.com/mcp) 的 MCP 能力封装为 Jnao **对话内置工具**，在 Chat（8010）任务/通用工具模式下可用。不依赖企业微信。

## 工具

| 工具 ID | 管理后台显示名 | 作用 |
|---------|----------------|------|
| `reefapi_search` | ReefAPI 引擎发现 | 按意图找引擎，或查看某引擎 actions/参数 |
| `reefapi_call` | ReefAPI 拉数 | `POST /{engine}/v1/{action}`，需 Key |

调用链：`reefapi_search` →（可选再 `reefapi_search(engine=...)`）→ `reefapi_call`。

与 `web_search`（Tavily）：通用网页摘要 / 台风新闻用 Tavily；站点结构化数据用 ReefAPI。

## 配置

1. `.env`：

```bash
REEFAPI_KEY=ak_live_你的密钥
# 可选
# REEFAPI_BASE=https://api.reefapi.com
# REEFAPI_TIMEOUT_SECONDS=60
```

2. 重启 Main API（8010）。

3. 管理后台 **工具 → 对话工具**：确认 `ReefAPI 引擎发现` / `ReefAPI 拉数` 已启用（新工具默认 enabled；若本地有旧的 `agent_tools.json`，保存一次或打开开关）。

**task/auto 模式** 亦可通过 **工具 → MCP 服务器** 添加 ReefAPI HTTP MCP 预设，见 [`mcp-config.md`](mcp-config.md)。

## 代码位置

- 实现：`enterprise_rag/src/agent/tools/builtins/reefapi.py`
- 注册：`agent/tools/config/registry.py`、`builtins/__init__.py`
- 策略：`agent/tools/runtime/prompt.py`

## 自测

```powershell
$env:PYTHONIOENCODING="utf-8"
cd D:\11
pytest tests/test_reefapi_tool.py -q
```

Chat 示例：「用 ReefAPI 查 Reddit 上关于 Anker 737 的讨论」——应先 `reefapi_search` 再 `reefapi_call`。

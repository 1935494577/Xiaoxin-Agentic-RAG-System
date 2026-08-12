# MCP 服务器配置（管理后台）

通过 **管理后台 → 工具 → MCP 服务器** 配置 Model Context Protocol 外部工具，写入仓库根目录 `extensions_config.json` 的 `mcpServers` 字段，格式与 Cursor / Claude Desktop 一致。

## 适用场景

| 路径 | 工具来源 |
|------|----------|
| **Chat 知识快路径**（8010，`assistant_mode=knowledge`） | 内置对话工具：`kb_search`、`web_search`、`reefapi_search` / `reefapi_call` 等（`agent_tools.json`） |
| **Chat task/auto + Harness 主编排**（8011 DeerFlow） | `config.yaml` 工具 + **MCP 服务器** + Skill |

MCP 配置主要供 **task / auto 模式**下的 DeerFlow Agent 加载外部 MCP 工具；知识模式仍走内置工具，无需 MCP。

## 管理后台操作

1. 使用**技术部**账号登录 Admin。
2. 打开 **工具 → MCP 服务器**。
3. 点击 **添加 MCP 服务器** 或 **添加 ReefAPI 预设**。
4. 填写传输类型与参数，保存（自动重置 MCP 工具缓存）。
5. 在 Chat 切换到 **任务** 或 **自动** 模式测试。

### 传输类型

| type | 说明 | 必填字段 |
|------|------|----------|
| `stdio` | 本地子进程（npx / uvx） | `command`、`args` |
| `http` | 远程 Streamable HTTP MCP | `url`、`headers`（可选） |
| `sse` | 远程 SSE MCP | `url`、`headers`（可选） |

**安全限制**：通过 API 保存的 stdio 服务器仅允许 `command` 为 `npx` 或 `uvx`（可在环境变量 `DEER_FLOW_MCP_STDIO_COMMAND_ALLOWLIST` 扩展）。

### 密钥与掩码

- GET 返回的 `env` / `headers` 值为 `***`（掩码）。
- 再次 PUT 时，对已有键留 `***` 表示**保留原值**；新键须填真实值。

## ReefAPI 示例

### 方式 A：MCP（task/auto 模式）

管理后台 **添加 ReefAPI 预设**，或手动配置：

```json
{
  "mcpServers": {
    "reefapi": {
      "enabled": true,
      "type": "http",
      "url": "https://api.reefapi.com/mcp",
      "headers": {
        "Authorization": "Bearer $REEFAPI_KEY"
      },
      "description": "ReefAPI 175+ 站点结构化实时数据"
    }
  }
}
```

`.env`：

```bash
REEFAPI_KEY=ak_live_你的密钥
```

保存后需 **Harness Gateway（8011）** 运行；保存时 Main API 会尝试通知 8011 重置 MCP 缓存。

### 方式 B：内置对话工具（knowledge / 通用工具模式）

见 [`reefapi-mcp接入.md`](reefapi-mcp接入.md)：`reefapi_search` + `reefapi_call`，在 **工具 → 对话工具** 启用。

## API（Main API 8010）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/mcp/config` | 读取配置（敏感字段掩码） |
| PUT | `/api/mcp/config` | 全量更新 `mcp_servers` |
| POST | `/api/mcp/cache/reset` | 重置 MCP 工具缓存（8010 + 8011） |

需技术部 Admin 权限。

Gateway（8011）亦暴露相同路径（DeerFlow 原生路由），Admin 前端统一走 8010。

## 自测

```powershell
$env:PYTHONIOENCODING="utf-8"
cd D:\11
pytest tests/test_mcp_config_api.py -q
```

## 相关文档

- [`deerflow-integration.md`](deerflow-integration.md) §3.1 — MCP 在工具链中的位置
- [`reefapi-mcp接入.md`](reefapi-mcp接入.md) — ReefAPI 内置工具

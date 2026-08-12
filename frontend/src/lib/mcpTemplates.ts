import type { McpServerConfig } from "../api/types";

export type McpTemplate = {
  id: string;
  label: string;
  description: string;
  name: string;
  config: McpServerConfig;
  envHint?: string;
};

/** 与 Cursor / Claude Desktop mcpServers 格式一致的常用官方模板 */
export const MCP_TEMPLATES: McpTemplate[] = [
  {
    id: "reefapi",
    label: "ReefAPI",
    description: "175+ 站点结构化实时数据（HTTP MCP）",
    name: "reefapi",
    envHint: ".env 配置 REEFAPI_KEY",
    config: {
      enabled: true,
      type: "http",
      command: null,
      args: [],
      env: {},
      url: "https://api.reefapi.com/mcp",
      headers: { Authorization: "Bearer $REEFAPI_KEY" },
      description: "ReefAPI 结构化网页数据",
    },
  },
  {
    id: "github",
    label: "GitHub",
    description: "仓库、Issue、PR 等（官方 @modelcontextprotocol/server-github）",
    name: "github",
    envHint: "env: GITHUB_PERSONAL_ACCESS_TOKEN",
    config: {
      enabled: true,
      type: "stdio",
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-github"],
      env: { GITHUB_PERSONAL_ACCESS_TOKEN: "$GITHUB_PERSONAL_ACCESS_TOKEN" },
      url: null,
      headers: {},
      description: "GitHub MCP",
    },
  },
  {
    id: "filesystem",
    label: "Filesystem",
    description: "本地目录读写（官方 server-filesystem）",
    name: "filesystem",
    config: {
      enabled: true,
      type: "stdio",
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"],
      env: {},
      url: null,
      headers: {},
      description: "Filesystem MCP",
    },
  },
  {
    id: "brave-search",
    label: "Brave Search",
    description: "Brave 搜索 API（官方 server-brave-search）",
    name: "brave-search",
    envHint: "env: BRAVE_API_KEY",
    config: {
      enabled: true,
      type: "stdio",
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-brave-search"],
      env: { BRAVE_API_KEY: "$BRAVE_API_KEY" },
      url: null,
      headers: {},
      description: "Brave Search MCP",
    },
  },
  {
    id: "fetch",
    label: "Fetch",
    description: "抓取网页内容（官方 server-fetch）",
    name: "fetch",
    config: {
      enabled: true,
      type: "stdio",
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-fetch"],
      env: {},
      url: null,
      headers: {},
      description: "Fetch MCP",
    },
  },
];

/** 写入本系统 extensions_config.json 前的可读摘要 */
export function templateConfigSummary(template: McpTemplate): { label: string; value: string }[] {
  const c = template.config;
  const rows: { label: string; value: string }[] = [
    { label: "名称", value: template.name },
    { label: "传输", value: c.type },
  ];
  if (c.type === "stdio") {
    rows.push({ label: "command", value: c.command || "" });
    if (c.args?.length) rows.push({ label: "args", value: c.args.join(" ") });
  } else if (c.url) {
    rows.push({ label: "url", value: c.url });
  }
  if (c.env && Object.keys(c.env).length) {
    rows.push({
      label: "env",
      value: Object.entries(c.env)
        .map(([k, v]) => `${k}=${v}`)
        .join(", "),
    });
  }
  if (c.headers && Object.keys(c.headers).length) {
    rows.push({
      label: "headers",
      value: Object.entries(c.headers)
        .map(([k, v]) => `${k}: ${v}`)
        .join(", "),
    });
  }
  return rows;
}

function configForJson(config: McpServerConfig): Record<string, unknown> {
  const out: Record<string, unknown> = { type: config.type };
  if (config.command) out.command = config.command;
  if (config.args?.length) out.args = config.args;
  if (config.url) out.url = config.url;
  if (config.env && Object.keys(config.env).length) out.env = config.env;
  if (config.headers && Object.keys(config.headers).length) out.headers = config.headers;
  if (config.description) out.description = config.description;
  return out;
}

/** Claude Desktop / Cursor 风格的 mcpServers JSON 片段 */
export function templateToJsonSnippet(template: McpTemplate): string {
  return JSON.stringify(
    { mcpServers: { [template.name]: configForJson(template.config) } },
    null,
    2,
  );
}

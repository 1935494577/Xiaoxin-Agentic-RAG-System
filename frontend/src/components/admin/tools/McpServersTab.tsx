import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, RefreshCw, Trash2 } from "lucide-react";
import { fetchMcpConfig, resetMcpCache, saveMcpConfig } from "../../../api/client";
import type { McpConfigData, McpServerConfig, McpTransportType } from "../../../api/types";
import { formatAdminLoadError } from "../../../lib/adminLoadError";
import { SectionGuide } from "../SectionGuide";
import { Button } from "../../ui/Button";
import { Switch } from "../../ui/Switch";
import { SkeletonCard } from "../../ui/Skeleton";
import { toast } from "sonner";

const MASKED = "***";

const TRANSPORT_OPTIONS: { id: McpTransportType; label: string; hint: string }[] = [
  { id: "stdio", label: "stdio（本地进程）", hint: "command + args，如 npx -y @package/name" },
  { id: "http", label: "http（远程 HTTP）", hint: "url + headers，如 ReefAPI / 自建 MCP 网关" },
  { id: "sse", label: "sse（远程 SSE）", hint: "url + headers，旧版 SSE 传输" },
];

const REEFAPI_PRESET: { name: string; config: McpServerConfig } = {
  name: "reefapi",
  config: {
    enabled: true,
    type: "http",
    command: null,
    args: [],
    env: {},
    url: "https://api.reefapi.com/mcp",
    headers: { Authorization: "Bearer $REEFAPI_KEY" },
    description: "ReefAPI 175+ 站点结构化实时数据（电商/社交/域名/房产等）",
  },
};

type KeyValueRow = { key: string; value: string };

function rowsFromRecord(rec: Record<string, string>): KeyValueRow[] {
  const entries = Object.entries(rec || {});
  if (!entries.length) return [{ key: "", value: "" }];
  return entries.map(([key, value]) => ({ key, value }));
}

function recordFromRows(rows: KeyValueRow[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const row of rows) {
    const k = row.key.trim();
    if (!k) continue;
    out[k] = row.value;
  }
  return out;
}

function emptyServer(type: McpTransportType = "stdio"): McpServerConfig {
  return {
    enabled: true,
    type,
    command: type === "stdio" ? "npx" : null,
    args: type === "stdio" ? ["-y"] : [],
    env: {},
    url: type === "stdio" ? null : "",
    headers: {},
    description: "",
  };
}

type EditorState = {
  name: string;
  config: McpServerConfig;
  envRows: KeyValueRow[];
  headerRows: KeyValueRow[];
  argsText: string;
};

function toEditor(name: string, config: McpServerConfig): EditorState {
  return {
    name,
    config,
    envRows: rowsFromRecord(config.env),
    headerRows: rowsFromRecord(config.headers),
    argsText: (config.args || []).join("\n"),
  };
}

export function McpServersTab() {
  const queryClient = useQueryClient();
  const [servers, setServers] = useState<Record<string, McpServerConfig>>({});
  const [editorOpen, setEditorOpen] = useState(false);
  const [editor, setEditor] = useState<EditorState | null>(null);
  const [isNew, setIsNew] = useState(false);

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["mcp-config"],
    queryFn: fetchMcpConfig,
    staleTime: 30_000,
    retry: 2,
    retryDelay: 1500,
  });

  useEffect(() => {
    if (data?.mcp_servers) setServers(data.mcp_servers);
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: (body: McpConfigData) => saveMcpConfig(body),
    onSuccess: (resp) => {
      setServers(resp.mcp_servers);
      toast.success("MCP 配置已保存。");
      queryClient.invalidateQueries({ queryKey: ["mcp-config"] });
    },
    onError: (e: Error) => toast.error(e.message || "保存失败"),
  });

  const resetMutation = useMutation({
    mutationFn: resetMcpCache,
    onSuccess: (resp) => toast.success(resp.message || "缓存已重置"),
    onError: (e: Error) => toast.error(e.message || "重置失败"),
  });

  const serverNames = useMemo(() => Object.keys(servers).sort(), [servers]);

  const persist = (next: Record<string, McpServerConfig>) => {
    setServers(next);
    saveMutation.mutate({ mcp_servers: next });
  };

  const openCreate = (preset?: { name: string; config: McpServerConfig }) => {
    if (preset) {
      setEditor(toEditor(preset.name, preset.config));
      setIsNew(true);
    } else {
      setEditor(toEditor("", emptyServer()));
      setIsNew(true);
    }
    setEditorOpen(true);
  };

  const openEdit = (name: string) => {
    setEditor(toEditor(name, servers[name]));
    setIsNew(false);
    setEditorOpen(true);
  };

  const toggleEnabled = (name: string, enabled: boolean) => {
    persist({ ...servers, [name]: { ...servers[name], enabled } });
  };

  const deleteServer = (name: string) => {
    if (!window.confirm(`确定删除 MCP 服务器「${name}」？`)) return;
    const next = { ...servers };
    delete next[name];
    persist(next);
  };

  const saveEditor = () => {
    if (!editor) return;
    const name = editor.name.trim();
    if (!name) {
      toast.error("请填写服务器名称（英文标识，如 github、reefapi）");
      return;
    }
    if (!/^[a-zA-Z][a-zA-Z0-9_-]*$/.test(name)) {
      toast.error("名称请以字母开头，仅含字母、数字、_、-");
      return;
    }
    if (isNew && servers[name]) {
      toast.error(`名称「${name}」已存在`);
      return;
    }

    const args = editor.argsText
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter(Boolean);

    const config: McpServerConfig = {
      ...editor.config,
      args,
      env: recordFromRows(editor.envRows),
      headers: recordFromRows(editor.headerRows),
    };

    if (config.type === "stdio" && !(config.command || "").trim()) {
      toast.error("stdio 类型需填写 command（如 npx）");
      return;
    }
    if (config.type !== "stdio" && !(config.url || "").trim()) {
      toast.error(`${config.type} 类型需填写 url`);
      return;
    }

    const next = { ...servers };
    if (!isNew && editor.name !== name) {
      delete next[editor.name];
    }
    next[name] = config;
    setEditorOpen(false);
    setEditor(null);
    persist(next);
  };

  if (isLoading) return <SkeletonCard rows={4} />;

  if (error) {
    const msg = formatAdminLoadError(error, "无法加载 MCP 配置，请确认已登录技术部账号且 API 已启动。");
    return (
      <div className="space-y-3">
        <p className="text-error text-sm">{msg}</p>
        <Button variant="secondary" onClick={() => refetch()} disabled={isFetching}>
          {isFetching ? "重试中…" : "重试"}
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SectionGuide
        summary="MCP（Model Context Protocol）让任务/自动模式下的 DeerFlow Agent 连接外部工具服务。配置写入 extensions_config.json，与 Cursor / Claude Desktop 的 mcpServers 格式一致。"
        steps={[
          {
            title: "选择传输类型",
            detail: "stdio：npx/uvx 本地包；http/sse：远程 MCP 端点（如 ReefAPI）。",
          },
          {
            title: "保存并重载",
            detail: "保存后自动重置 MCP 工具缓存；task/auto 模式下次对话即加载新工具。",
          },
          {
            title: "与对话内置工具分工",
            detail: "kb_search / web_search / reefapi_* 走知识快路径内置工具；MCP 主要供 Harness task/auto 主编排。",
          },
        ]}
        tips={[
          "stdio 的 command 仅允许 npx、uvx（安全限制）；参数写在 args 每行一项。",
          "密钥类 env/header 保存后 GET 会显示 ***，再次保存时留 *** 表示保留原值。",
          "ReefAPI 可一键添加预设；需在 .env 配置 REEFAPI_KEY。",
        ]}
      />

      <div className="flex flex-wrap gap-2">
        <Button variant="primary" onClick={() => openCreate()} disabled={saveMutation.isPending}>
          <Plus className="h-4 w-4 mr-1" aria-hidden />
          添加 MCP 服务器
        </Button>
        <Button variant="secondary" onClick={() => openCreate(REEFAPI_PRESET)} disabled={saveMutation.isPending}>
          添加 ReefAPI 预设
        </Button>
        <Button
          variant="secondary"
          onClick={() => resetMutation.mutate()}
          disabled={resetMutation.isPending}
        >
          <RefreshCw className="h-4 w-4 mr-1" aria-hidden />
          {resetMutation.isPending ? "重置中…" : "重置 MCP 缓存"}
        </Button>
      </div>

      {serverNames.length === 0 ? (
        <p className="text-sm text-text-muted rounded-lg border border-dashed border-border px-4 py-8 text-center">
          尚未配置 MCP 服务器。可点击「添加 ReefAPI 预设」快速接入结构化网页数据。
        </p>
      ) : (
        <div className="space-y-3">
          {serverNames.map((name) => {
            const s = servers[name];
            return (
              <div key={name} className="rounded-lg border border-border bg-surface-muted/40 px-4 py-3">
                <div className="flex flex-wrap items-center gap-3">
                  <Switch
                    checked={Boolean(s.enabled)}
                    onCheckedChange={(v) => toggleEnabled(name, v)}
                    id={`mcp-${name}`}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-text font-mono">{name}</span>
                      <span className="text-xs px-1.5 py-0.5 rounded bg-surface border border-border text-text-muted">
                        {s.type}
                      </span>
                    </div>
                    {s.description ? (
                      <p className="text-xs text-text-muted mt-1">{s.description}</p>
                    ) : null}
                    <p className="text-xs text-text-muted mt-1 font-mono truncate">
                      {s.type === "stdio"
                        ? `${s.command || "?"} ${(s.args || []).join(" ")}`
                        : s.url || "（未配置 url）"}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="secondary" size="sm" onClick={() => openEdit(name)}>
                      编辑
                    </Button>
                    <Button variant="secondary" size="sm" onClick={() => deleteServer(name)}>
                      <Trash2 className="h-3.5 w-3.5" aria-hidden />
                    </Button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {editorOpen && editor ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div
            className="bg-surface rounded-xl max-w-lg w-full max-h-[85vh] overflow-hidden flex flex-col shadow-xl"
            role="dialog"
            aria-modal="true"
            aria-labelledby="mcp-editor-title"
          >
            <div className="px-4 py-3 border-b border-border">
              <h3 id="mcp-editor-title" className="font-semibold text-sm text-text">
                {isNew ? "添加 MCP 服务器" : "编辑 MCP 服务器"}
              </h3>
            </div>
            <div className="px-4 py-4 overflow-y-auto space-y-4">
            <label className="block text-sm">
              <span className="text-text-muted">名称（mcpServers 键名）</span>
              <input
                className="mt-1 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
                value={editor.name}
                disabled={!isNew}
                onChange={(e) => setEditor({ ...editor, name: e.target.value })}
                placeholder="reefapi"
              />
            </label>

            <label className="block text-sm">
              <span className="text-text-muted">传输类型</span>
              <select
                className="mt-1 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm"
                value={editor.config.type}
                onChange={(e) => {
                  const type = e.target.value as McpTransportType;
                  setEditor({
                    ...editor,
                    config: {
                      ...editor.config,
                      type,
                      command: type === "stdio" ? editor.config.command || "npx" : null,
                      url: type === "stdio" ? null : editor.config.url || "",
                    },
                  });
                }}
              >
                {TRANSPORT_OPTIONS.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.label}
                  </option>
                ))}
              </select>
              <span className="text-xs text-text-muted">
                {TRANSPORT_OPTIONS.find((o) => o.id === editor.config.type)?.hint}
              </span>
            </label>

            <label className="block text-sm">
              <span className="text-text-muted">描述</span>
              <input
                className="mt-1 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm"
                value={editor.config.description}
                onChange={(e) =>
                  setEditor({ ...editor, config: { ...editor.config, description: e.target.value } })
                }
              />
            </label>

            {editor.config.type === "stdio" ? (
              <>
                <label className="block text-sm">
                  <span className="text-text-muted">command</span>
                  <input
                    className="mt-1 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
                    value={editor.config.command || ""}
                    onChange={(e) =>
                      setEditor({ ...editor, config: { ...editor.config, command: e.target.value } })
                    }
                    placeholder="npx"
                  />
                </label>
                <label className="block text-sm">
                  <span className="text-text-muted">args（每行一项）</span>
                  <textarea
                    className="mt-1 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono min-h-[80px]"
                    value={editor.argsText}
                    onChange={(e) => setEditor({ ...editor, argsText: e.target.value })}
                    placeholder="-y&#10;@modelcontextprotocol/server-github"
                  />
                </label>
              </>
            ) : (
              <label className="block text-sm">
                <span className="text-text-muted">url</span>
                <input
                  className="mt-1 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
                  value={editor.config.url || ""}
                  onChange={(e) =>
                    setEditor({ ...editor, config: { ...editor.config, url: e.target.value } })
                  }
                  placeholder="https://api.reefapi.com/mcp"
                />
              </label>
            )}

            <KeyValueEditor
              label="env（环境变量）"
              rows={editor.envRows}
              onChange={(envRows) => setEditor({ ...editor, envRows })}
              placeholderValue="value 或 $ENV_VAR"
            />

            {editor.config.type !== "stdio" ? (
              <KeyValueEditor
                label="headers（HTTP 头）"
                rows={editor.headerRows}
                onChange={(headerRows) => setEditor({ ...editor, headerRows })}
                placeholderValue="Bearer ak_live_… 或 $REEFAPI_KEY"
              />
            ) : null}

            <p className="text-xs text-text-muted">
              敏感值保存后以 {MASKED} 显示；编辑时留 {MASKED} 表示不修改。
            </p>

            <div className="flex justify-end gap-2 pt-2 border-t border-border mt-2">
              <Button variant="secondary" onClick={() => setEditorOpen(false)}>
                取消
              </Button>
              <Button variant="primary" onClick={saveEditor} disabled={saveMutation.isPending}>
                {saveMutation.isPending ? "保存中…" : "保存"}
              </Button>
            </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function KeyValueEditor({
  label,
  rows,
  onChange,
  placeholderValue,
}: {
  label: string;
  rows: KeyValueRow[];
  onChange: (rows: KeyValueRow[]) => void;
  placeholderValue?: string;
}) {
  const updateRow = (idx: number, patch: Partial<KeyValueRow>) => {
    const next = rows.map((r, i) => (i === idx ? { ...r, ...patch } : r));
    onChange(next);
  };

  const addRow = () => onChange([...rows, { key: "", value: "" }]);
  const removeRow = (idx: number) => {
    const next = rows.filter((_, i) => i !== idx);
    onChange(next.length ? next : [{ key: "", value: "" }]);
  };

  return (
    <div className="text-sm">
      <div className="flex items-center justify-between mb-1">
        <span className="text-text-muted">{label}</span>
        <button type="button" className="text-xs text-brand hover:underline" onClick={addRow}>
          + 添加
        </button>
      </div>
      <div className="space-y-2">
        {rows.map((row, idx) => (
          <div key={idx} className="flex gap-2">
            <input
              className="flex-1 rounded-md border border-border bg-surface px-2 py-1.5 text-xs font-mono"
              value={row.key}
              onChange={(e) => updateRow(idx, { key: e.target.value })}
              placeholder="KEY"
            />
            <input
              className="flex-[2] rounded-md border border-border bg-surface px-2 py-1.5 text-xs font-mono"
              value={row.value}
              onChange={(e) => updateRow(idx, { value: e.target.value })}
              placeholder={placeholderValue}
            />
            <button
              type="button"
              className="text-text-muted hover:text-error px-1"
              onClick={() => removeRow(idx)}
              aria-label="删除行"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

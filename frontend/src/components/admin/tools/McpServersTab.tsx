import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, Plus, RefreshCw, Trash2 } from "lucide-react";
import { fetchMcpConfig, resetMcpCache, saveMcpConfig } from "../../../api/client";
import type {
  McpConfigSave,
  McpServerConfig,
  McpServerEntry,
  McpToolOverview,
  McpTransportType,
} from "../../../api/types";
import { formatAdminLoadError } from "../../../lib/adminLoadError";
import { MCP_TEMPLATES, templateConfigSummary, type McpTemplate } from "../../../lib/mcpTemplates";
import { SectionGuide } from "../SectionGuide";
import { Button } from "../../ui/Button";
import { Switch } from "../../ui/Switch";
import { SkeletonCard } from "../../ui/Skeleton";
import { toast } from "sonner";

const MASKED = "***";

type AddView = "templates" | "template-detail" | "manual";

type EditorState = {
  name: string;
  config: McpServerConfig;
  envText: string;
  headerText: string;
  argsText: string;
};

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

function linesFromRecord(rec: Record<string, string>): string {
  return Object.entries(rec || {})
    .map(([k, v]) => `${k}=${v}`)
    .join("\n");
}

function recordFromLines(text: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq <= 0) continue;
    out[trimmed.slice(0, eq).trim()] = trimmed.slice(eq + 1).trim();
  }
  return out;
}

function toEditor(name: string, config: McpServerConfig): EditorState {
  return {
    name,
    config,
    envText: linesFromRecord(config.env),
    headerText: linesFromRecord(config.headers),
    argsText: (config.args || []).join("\n"),
  };
}

function validateName(name: string): string | null {
  if (!name.trim()) return "请填写服务器名称（英文标识）";
  if (!/^[a-zA-Z][a-zA-Z0-9_-]*$/.test(name)) {
    return "名称请以字母开头，仅含字母、数字、_、-";
  }
  return null;
}

function buildConfigFromEditor(editor: EditorState): McpServerConfig | string {
  const args = editor.argsText
    .split(/\r?\n/)
    .map((s) => s.trim())
    .filter(Boolean);
  const config: McpServerConfig = {
    ...editor.config,
    args,
    env: recordFromLines(editor.envText),
    headers: recordFromLines(editor.headerText),
  };
  if (config.type === "stdio" && !(config.command || "").trim()) {
    return "stdio 需填写 command（npx 或 uvx）";
  }
  if (config.type !== "stdio" && !(config.url || "").trim()) {
    return `${config.type} 需填写 url`;
  }
  return config;
}

export function McpServersTab() {
  const queryClient = useQueryClient();
  const [servers, setServers] = useState<Record<string, McpServerConfig>>({});
  const [entries, setEntries] = useState<Record<string, McpServerEntry>>({});
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const [addOpen, setAddOpen] = useState(false);
  const [addView, setAddView] = useState<AddView>("templates");
  const [pickedTemplate, setPickedTemplate] = useState<McpTemplate | null>(null);
  const [manualEditor, setManualEditor] = useState<EditorState>(() => toEditor("", emptyServer()));

  const [editOpen, setEditOpen] = useState(false);
  const [editEditor, setEditEditor] = useState<EditorState | null>(null);
  const [editOriginalName, setEditOriginalName] = useState("");

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["mcp-config"],
    queryFn: fetchMcpConfig,
    staleTime: 30_000,
    retry: 2,
    retryDelay: 1500,
  });

  useEffect(() => {
    if (!data?.mcp_servers) return;
    setEntries(data.mcp_servers);
    const configs: Record<string, McpServerConfig> = {};
    for (const [name, entry] of Object.entries(data.mcp_servers)) {
      configs[name] = entry.config;
    }
    setServers(configs);
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: (body: McpConfigSave) => saveMcpConfig(body),
    onSuccess: (resp) => {
      setEntries(resp.mcp_servers);
      const configs: Record<string, McpServerConfig> = {};
      for (const [name, entry] of Object.entries(resp.mcp_servers)) {
        configs[name] = entry.config;
      }
      setServers(configs);
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

  const serverNames = useMemo(() => Object.keys(entries).sort(), [entries]);

  const persist = (next: Record<string, McpServerConfig>, onDone?: () => void) => {
    setServers(next);
    saveMutation.mutate(
      { mcp_servers: next },
      { onSuccess: () => onDone?.() },
    );
  };

  const openAdd = () => {
    setAddView("templates");
    setPickedTemplate(null);
    setManualEditor(toEditor("", emptyServer()));
    setAddOpen(true);
  };

  const openEdit = (name: string) => {
    setEditOriginalName(name);
    setEditEditor(toEditor(name, servers[name]));
    setEditOpen(true);
  };

  const saveTemplate = (template: McpTemplate) => {
    const nameErr = validateName(template.name);
    if (nameErr) {
      toast.error(nameErr);
      return;
    }
    if (servers[template.name]) {
      toast.error(`「${template.name}」已存在，请手动配置或先删除`);
      return;
    }
    persist(
      { ...servers, [template.name]: { ...template.config, enabled: true } },
      () => setAddOpen(false),
    );
  };

  const saveManual = () => {
    const nameErr = validateName(manualEditor.name);
    if (nameErr) {
      toast.error(nameErr);
      return;
    }
    if (servers[manualEditor.name.trim()]) {
      toast.error(`名称「${manualEditor.name}」已存在`);
      return;
    }
    const built = buildConfigFromEditor(manualEditor);
    if (typeof built === "string") {
      toast.error(built);
      return;
    }
    persist(
      { ...servers, [manualEditor.name.trim()]: built },
      () => setAddOpen(false),
    );
  };

  const saveEdit = () => {
    if (!editEditor) return;
    const name = editEditor.name.trim();
    const nameErr = validateName(name);
    if (nameErr) {
      toast.error(nameErr);
      return;
    }
    const built = buildConfigFromEditor(editEditor);
    if (typeof built === "string") {
      toast.error(built);
      return;
    }
    const next = { ...servers };
    if (editOriginalName !== name) delete next[editOriginalName];
    next[name] = built;
    setEditOpen(false);
    setEditEditor(null);
    persist(next);
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

  const toggleExpanded = (name: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
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
        summary="MCP 配置格式与 Cursor / Claude Desktop 一致，写入 extensions_config.json。"
        steps={[
          { title: "官方模板", detail: "添加时选常用 MCP，复制 JSON 或一键保存。" },
          { title: "手动配置", detail: "自定义 stdio / http / sse 传输与参数。" },
          { title: "开关与工具", detail: "保存后展开卡片可查看该 MCP 暴露的工具。" },
        ]}
        tips={[
          "stdio 仅允许 npx、uvx；密钥用 $ENV_VAR 引用 .env。",
          "保存后自动重置 MCP 缓存；task/auto 模式下次对话生效。",
        ]}
      />

      {data?.config_path ? (
        <p className="text-xs text-text-muted font-mono break-all">配置文件：{data.config_path}</p>
      ) : null}

      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-sm font-semibold text-text flex-1">MCP 服务器</h3>
        <Button variant="primary" onClick={openAdd} disabled={saveMutation.isPending}>
          <Plus className="h-4 w-4 mr-1" aria-hidden />
          添加 MCP 服务器
        </Button>
        <Button
          variant="secondary"
          onClick={() => resetMutation.mutate()}
          disabled={resetMutation.isPending}
        >
          <RefreshCw className="h-4 w-4 mr-1" aria-hidden />
          {resetMutation.isPending ? "重置中…" : "重置缓存"}
        </Button>
      </div>

      {serverNames.length === 0 ? (
        <p className="text-sm text-text-muted rounded-lg border border-dashed border-border px-4 py-8 text-center">
          尚未配置 MCP 服务器。点击「添加 MCP 服务器」从官方模板选择或手动填写。
        </p>
      ) : (
        <div className="space-y-3">
          {serverNames.map((name) => {
            const entry = entries[name];
            if (!entry) return null;
            const s = servers[name] ?? entry.config;
            const isOpen = expanded.has(name);
            const toolCount = entry.tools?.length ?? 0;
            return (
              <div key={name} className="rounded-lg border border-border bg-surface-muted/40 px-4 py-3">
                <div className="flex flex-wrap items-center gap-3">
                  <Switch
                    checked={Boolean(s.enabled)}
                    onCheckedChange={(v) => toggleEnabled(name, v)}
                    id={`mcp-${name}`}
                    disabled={saveMutation.isPending}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-text font-mono">{name}</span>
                      <span className="text-xs px-1.5 py-0.5 rounded bg-surface border border-border text-text-muted">
                        {s.type}
                      </span>
                      {!s.enabled ? (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-surface border border-border text-text-muted">
                          已关闭
                        </span>
                      ) : null}
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
                {toolCount > 0 ? (
                  <div className="mt-3 border-t border-border/60 pt-2">
                    <button
                      type="button"
                      className="flex items-center gap-1.5 text-xs text-text-muted hover:text-text w-full text-left py-1"
                      onClick={() => toggleExpanded(name)}
                      aria-expanded={isOpen}
                    >
                      {isOpen ? (
                        <ChevronDown className="h-3.5 w-3.5 shrink-0" aria-hidden />
                      ) : (
                        <ChevronRight className="h-3.5 w-3.5 shrink-0" aria-hidden />
                      )}
                      <span className="font-medium">{toolCount} 个工具</span>
                      {!isOpen ? (
                        <span className="text-text-muted/80 truncate">
                          · {entry.tools.map((t) => t.name).join(", ")}
                        </span>
                      ) : null}
                    </button>
                    {isOpen ? (
                      <div className="mt-2 space-y-2 pl-5">
                        {entry.tools.map((tool) => (
                          <McpToolRow key={tool.name} tool={tool} />
                        ))}
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      )}

      {addOpen ? (
        <Modal title="添加 MCP 服务器" onClose={() => setAddOpen(false)}>
          {addView === "templates" ? (
            <div className="space-y-4">
              <p className="text-xs text-text-muted">
                选择官方 MCP 模板，点击「一键配置」直接写入下方 MCP 服务器列表。
              </p>
              <div className="space-y-2">
                {MCP_TEMPLATES.map((tpl) => {
                  const exists = Boolean(servers[tpl.name]);
                  return (
                    <div
                      key={tpl.id}
                      className="rounded-lg border border-border px-3 py-2.5 flex gap-3 items-start"
                    >
                      <button
                        type="button"
                        className="flex-1 min-w-0 text-left"
                        onClick={() => {
                          setPickedTemplate(tpl);
                          setAddView("template-detail");
                        }}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-medium text-sm text-text">{tpl.label}</span>
                          <span className="text-xs text-text-muted font-mono">{tpl.config.type}</span>
                        </div>
                        <p className="text-xs text-text-muted mt-0.5">{tpl.description}</p>
                        {tpl.envHint ? (
                          <p className="text-xs text-text-muted/80 mt-0.5">{tpl.envHint}</p>
                        ) : null}
                      </button>
                      <Button
                        variant="primary"
                        size="sm"
                        className="shrink-0 mt-0.5"
                        disabled={saveMutation.isPending || exists}
                        onClick={() => saveTemplate(tpl)}
                      >
                        {exists ? "已配置" : "一键配置"}
                      </Button>
                    </div>
                  );
                })}
              </div>
              <div className="pt-2 border-t border-border">
                <Button
                  variant="secondary"
                  className="w-full"
                  onClick={() => {
                    setManualEditor(toEditor("", emptyServer()));
                    setAddView("manual");
                  }}
                >
                  手动配置
                </Button>
              </div>
            </div>
          ) : null}

          {addView === "template-detail" && pickedTemplate ? (
            <TemplateDetail
              template={pickedTemplate}
              exists={Boolean(servers[pickedTemplate.name])}
              saving={saveMutation.isPending}
              onBack={() => setAddView("templates")}
              onApply={() => saveTemplate(pickedTemplate)}
              onManual={() => {
                setManualEditor(toEditor(pickedTemplate.name, pickedTemplate.config));
                setAddView("manual");
              }}
            />
          ) : null}

          {addView === "manual" ? (
            <ManualForm
              editor={manualEditor}
              onChange={setManualEditor}
              onBack={() => setAddView(pickedTemplate ? "template-detail" : "templates")}
              onSave={saveManual}
              saving={saveMutation.isPending}
              isNew
            />
          ) : null}
        </Modal>
      ) : null}

      {editOpen && editEditor ? (
        <Modal title="编辑 MCP 服务器" onClose={() => setEditOpen(false)}>
          <ManualForm
            editor={editEditor}
            onChange={setEditEditor}
            onSave={saveEdit}
            saving={saveMutation.isPending}
            isNew={false}
            nameLocked
          />
        </Modal>
      ) : null}
    </div>
  );
}

function Modal({
  title,
  children,
  onClose,
  wide,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div
        className={`bg-surface rounded-xl w-full max-h-[85vh] overflow-hidden flex flex-col shadow-xl ${
          wide ? "max-w-xl" : "max-w-lg"
        }`}
        role="dialog"
        aria-modal="true"
      >
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <h3 className="font-semibold text-sm text-text">{title}</h3>
          <button type="button" className="text-text-muted hover:text-text text-sm" onClick={onClose}>
            关闭
          </button>
        </div>
        <div className="px-4 py-4 overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}

function TemplateDetail({
  template,
  exists,
  saving,
  onBack,
  onApply,
  onManual,
}: {
  template: McpTemplate;
  exists: boolean;
  saving: boolean;
  onBack: () => void;
  onApply: () => void;
  onManual: () => void;
}) {
  const summary = templateConfigSummary(template);
  return (
    <div className="space-y-4">
      <button type="button" className="text-xs text-brand hover:underline" onClick={onBack}>
        ← 返回模板列表
      </button>
      <div>
        <h4 className="font-medium text-sm text-text">{template.label}</h4>
        <p className="text-xs text-text-muted mt-1">{template.description}</p>
        {template.envHint ? (
          <p className="text-xs text-warning mt-1">{template.envHint}</p>
        ) : null}
      </div>
      <div>
        <p className="text-xs text-text-muted mb-2">将写入 MCP 服务器（extensions_config.json）</p>
        <dl className="rounded-lg border border-border bg-surface-muted/40 divide-y divide-border text-xs">
          {summary.map((row) => (
            <div key={row.label} className="flex gap-3 px-3 py-2">
              <dt className="text-text-muted font-mono w-16 shrink-0">{row.label}</dt>
              <dd className="text-text font-mono break-all">{row.value}</dd>
            </div>
          ))}
        </dl>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button variant="primary" onClick={onApply} disabled={saving || exists}>
          {saving ? "配置中…" : exists ? "已配置" : "一键配置"}
        </Button>
        <Button variant="secondary" onClick={onManual}>
          手动修改
        </Button>
      </div>
    </div>
  );
}

function ManualForm({
  editor,
  onChange,
  onSave,
  onBack,
  saving,
  isNew,
  nameLocked,
}: {
  editor: EditorState;
  onChange: (e: EditorState) => void;
  onSave: () => void;
  onBack?: () => void;
  saving: boolean;
  isNew: boolean;
  nameLocked?: boolean;
}) {
  const types: McpTransportType[] = ["stdio", "http", "sse"];

  return (
    <div className="space-y-3">
      {onBack ? (
        <button type="button" className="text-xs text-brand hover:underline" onClick={onBack}>
          ← 返回
        </button>
      ) : null}

      <label className="block text-sm">
        <span className="text-text-muted">名称</span>
        <input
          className="mt-1 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
          value={editor.name}
          disabled={nameLocked}
          onChange={(e) => onChange({ ...editor, name: e.target.value })}
          placeholder="github"
        />
      </label>

      <div>
        <span className="text-xs text-text-muted">传输</span>
        <div className="flex gap-1 mt-1">
          {types.map((t) => (
            <button
              key={t}
              type="button"
              className={`text-xs px-3 py-1.5 rounded-md border font-mono ${
                editor.config.type === t
                  ? "border-brand bg-brand/10 text-brand"
                  : "border-border text-text-muted hover:bg-surface-muted"
              }`}
              onClick={() =>
                onChange({
                  ...editor,
                  config: {
                    ...editor.config,
                    type: t,
                    command: t === "stdio" ? editor.config.command || "npx" : null,
                    url: t === "stdio" ? null : editor.config.url || "",
                  },
                })
              }
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {editor.config.type === "stdio" ? (
        <>
          <label className="block text-sm">
            <span className="text-text-muted">command</span>
            <input
              className="mt-1 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono"
              value={editor.config.command || ""}
              onChange={(e) =>
                onChange({ ...editor, config: { ...editor.config, command: e.target.value } })
              }
              placeholder="npx"
            />
          </label>
          <label className="block text-sm">
            <span className="text-text-muted">args（每行一项）</span>
            <textarea
              className="mt-1 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono min-h-[72px]"
              value={editor.argsText}
              onChange={(e) => onChange({ ...editor, argsText: e.target.value })}
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
              onChange({ ...editor, config: { ...editor.config, url: e.target.value } })
            }
          />
        </label>
      )}

      <label className="block text-sm">
        <span className="text-text-muted">env（KEY=VALUE，每行一项，可选）</span>
        <textarea
          className="mt-1 w-full rounded-md border border-border bg-surface px-3 py-2 text-xs font-mono min-h-[56px]"
          value={editor.envText}
          onChange={(e) => onChange({ ...editor, envText: e.target.value })}
          placeholder="GITHUB_PERSONAL_ACCESS_TOKEN=$GITHUB_PERSONAL_ACCESS_TOKEN"
        />
      </label>

      {editor.config.type !== "stdio" ? (
        <label className="block text-sm">
          <span className="text-text-muted">headers（KEY=VALUE，每行一项，可选）</span>
          <textarea
            className="mt-1 w-full rounded-md border border-border bg-surface px-3 py-2 text-xs font-mono min-h-[56px]"
            value={editor.headerText}
            onChange={(e) => onChange({ ...editor, headerText: e.target.value })}
            placeholder="Authorization=Bearer $REEFAPI_KEY"
          />
        </label>
      ) : null}

      {!isNew ? (
        <p className="text-xs text-text-muted">敏感值已掩码为 {MASKED}；留 {MASKED} 表示不修改。</p>
      ) : null}

      <div className="flex justify-end gap-2 pt-2 border-t border-border">
        <Button variant="primary" onClick={onSave} disabled={saving}>
          {saving ? "保存中…" : "保存"}
        </Button>
      </div>
    </div>
  );
}

function McpToolRow({ tool }: { tool: McpToolOverview }) {
  const params = tool.parameters || [];
  return (
    <div className="rounded-md border border-border/70 bg-surface/60 px-3 py-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-mono font-medium text-text">{tool.name}</span>
        {tool.requires_key ? (
          <span className="text-[10px] px-1 py-0.5 rounded bg-warning-bg text-warning border border-warning/20">
            需 Key
          </span>
        ) : null}
      </div>
      {tool.description ? <p className="text-xs text-text-muted mt-1">{tool.description}</p> : null}
      {params.length > 0 ? (
        <div className="flex flex-wrap gap-1 mt-1.5">
          {params.map((p) => (
            <span
              key={p.name}
              className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-muted border border-border text-text-muted"
            >
              {p.name}
              {p.required ? "" : "?"}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchPrompts, savePrompts } from "../../api/client";
import type { PromptSlot } from "../../api/types";
import { PageHeader } from "../../components/admin/PageHeader";
import { Button } from "../../components/ui/Button";
import { Switch } from "../../components/ui/Switch";
import { Textarea } from "../../components/ui/Textarea";
import { toast } from "sonner";

const SCOPE_LABELS: Record<string, string> = {
  all: "全部场景",
  kb: "知识库",
  general: "通用回答",
};
const SCOPE_OPTIONS = ["all", "kb", "general"];
const CATEGORY_ORDER = ["persona", "policy", "task", "output", "custom"];

type EditSlot = PromptSlot & { content?: string; description?: string; variant?: string };

export default function PromptPage() {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState("kb");
  const [fast, setFast] = useState(true);
  const [expandAll, setExpandAll] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ["prompts", mode, fast],
    queryFn: () => fetchPrompts(mode, fast),
    staleTime: 60_000,
  });

  const [slots, setSlots] = useState<EditSlot[]>([]);
  const [initKey, setInitKey] = useState("");

  const dataKey = `${mode}-${fast}`;
  if (initKey !== dataKey && data?.slots) {
    setSlots(
      data.slots.map((s) => ({
        ...s,
        content: (s as Record<string, unknown>).content as string ?? s.template ?? "",
        description: (s as Record<string, unknown>).description as string ?? "",
      }))
    );
    setInitKey(dataKey);
  }

  const saveMut = useMutation({
    mutationFn: (body: { slots?: Record<string, unknown>[]; reset_defaults?: boolean }) =>
      savePrompts(mode, body.slots ?? [], fast && mode === "kb"),
    onSuccess: () => {
      toast.success("已保存");
      queryClient.invalidateQueries({ queryKey: ["prompts"] });
    },
    onError: (e: Error) => toast.error(e.message || "保存失败"),
  });

  const resetMut = useMutation({
    mutationFn: () =>
      savePrompts(mode, [], fast && mode === "kb").then(() => {
        // Send reset_defaults in the raw request since savePrompts doesn't support it
        const params = new URLSearchParams({ mode });
        if (fast && mode === "kb") params.set("fast", "true");
        return fetch(`/config/prompts?${params}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reset_defaults: true }),
        }).then((r) => {
          if (!r.ok) throw new Error("重置失败");
        });
      }),
    onSuccess: () => {
      toast.success("已恢复默认");
      queryClient.invalidateQueries({ queryKey: ["prompts"] });
    },
    onError: (e: Error) => toast.error(e.message || "重置失败"),
  });

  const updateSlot = (id: string, patch: Partial<EditSlot>) => {
    setSlots((prev) =>
      prev.map((s) => (s.id === id ? { ...s, ...patch } : s))
    );
  };

  const handleSave = () => {
    const payload = slots.map((s) => ({
      id: s.id,
      label: s.label,
      description: s.description ?? "",
      category: s.category,
      scope: s.scope,
      enabled: s.enabled,
      order: s.order,
      content: s.content ?? s.template ?? "",
      builtin: s.builtin,
      ...(s.variant ? { variant: s.variant } : {}),
    }));
    saveMut.mutate({ slots: payload });
  };

  // Group slots by category
  const grouped = (() => {
    const g: Record<string, EditSlot[]> = {};
    for (const cat of CATEGORY_ORDER) g[cat] = [];
    for (const s of [...slots].sort((a, b) => (a.order ?? 100) - (b.order ?? 100))) {
      const cat = s.category || "custom";
      if (!g[cat]) g[cat] = [];
      g[cat].push(s);
    }
    for (const cat of Object.keys(g)) {
      if (!g[cat].length) delete g[cat];
    }
    return g;
  })();

  const categories = (data as Record<string, unknown>)?.categories as Record<string, string> ?? {};

  if (isLoading) {
    return <div className="p-6 text-text-muted text-sm">加载中...</div>;
  }

  if (error) {
    return (
      <div className="p-6">
        <PageHeader title="提示词" />
        <p className="text-error text-sm">无法加载提示词配置，请确认 API 已启动。</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-[900px]">
      <PageHeader
        title="提示词"
        description="按标准 Prompt 工程分层配置 System Prompt：角色人设 → 行为约束 → 任务指令 → 输出格式。各层可独立启用/禁用，保存后立即生效。"
      />

      <div className="space-y-6">
        {/* Toolbar */}
        <div className="flex items-center gap-4 flex-wrap">
          <label className="flex items-center gap-2">
            <span className="text-sm text-text-muted">预览场景：</span>
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              className="h-9 rounded-lg border border-border bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand/20"
            >
              <option value="kb">知识库</option>
              <option value="general">通用回答</option>
            </select>
          </label>
          {mode === "kb" && (
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <Switch checked={fast} onCheckedChange={setFast} id="fast-mode" />
              <span className="text-sm text-text">快速流式</span>
            </label>
          )}
          <label className="flex items-center gap-2 cursor-pointer select-none text-sm text-text-muted">
            <input
              type="checkbox"
              checked={expandAll}
              onChange={(e) => setExpandAll(e.target.checked)}
              className="w-4 h-4 rounded accent-brand"
            />
            全部展开
          </label>
        </div>

        {/* Slot editors */}
        {CATEGORY_ORDER.map((cat) => {
          const rows = grouped[cat];
          if (!rows?.length) return null;
          return (
            <div key={cat}>
              <h3 className="text-sm font-semibold text-text mb-3">
                {categories[cat] || cat}
              </h3>
              <div className="space-y-3">
                {rows.map((slot) => {
                  const isBuiltin = slot.builtin;
                  return (
                    <details
                      key={slot.id}
                      open={expandAll || cat === "persona"}
                      className="border border-border rounded-xl bg-white"
                    >
                      <summary className="px-4 py-3 cursor-pointer select-none hover:bg-surface-muted rounded-xl">
                        <span className="text-sm font-medium text-text">
                          {isBuiltin ? "🔒 " : "➕ "}
                          {slot.label}{" "}
                          <code className="text-xs text-text-muted">({slot.id})</code>
                        </span>
                      </summary>
                      <div className="px-4 pb-4 space-y-3">
                        {slot.description && (
                          <p className="text-xs text-text-muted">{slot.description}</p>
                        )}

                        <div className="grid grid-cols-3 gap-4">
                          <label className="flex items-center gap-2 cursor-pointer select-none">
                            <Switch
                              checked={slot.enabled}
                              onCheckedChange={(v) => updateSlot(slot.id, { enabled: v })}
                            />
                            <span className="text-sm text-text">启用</span>
                          </label>

                          <label className="flex items-center gap-2">
                            <span className="text-xs text-text-muted">顺序：</span>
                            <input
                              type="number"
                              min={0}
                              max={9999}
                              value={slot.order ?? 100}
                              onChange={(e) =>
                                updateSlot(slot.id, { order: Number(e.target.value) })
                              }
                              className="w-20 h-8 rounded border border-border bg-white px-2 text-sm text-center focus:outline-none focus:ring-2 focus:ring-brand/20"
                            />
                          </label>

                          <div className="flex items-center gap-2">
                            <span className="text-xs text-text-muted shrink-0">场景：</span>
                            {SCOPE_OPTIONS.map((sc) => {
                              const scopeArr = Array.isArray(slot.scope)
                                ? slot.scope
                                : [slot.scope ?? "all"];
                              const checked = scopeArr.includes(sc);
                              return (
                                <label
                                  key={sc}
                                  className="flex items-center gap-1 cursor-pointer text-xs"
                                >
                                  <input
                                    type="checkbox"
                                    checked={checked}
                                    onChange={() => {
                                      const next = checked
                                        ? scopeArr.filter((s) => s !== sc)
                                        : [...scopeArr, sc];
                                      updateSlot(slot.id, {
                                        scope: next.length ? next : ["all"],
                                      });
                                    }}
                                    className="w-3.5 h-3.5 rounded accent-brand"
                                  />
                                  {SCOPE_LABELS[sc]}
                                </label>
                              );
                            })}
                          </div>
                        </div>

                        {!isBuiltin && (
                          <input
                            type="text"
                            value={slot.label}
                            onChange={(e) => updateSlot(slot.id, { label: e.target.value })}
                            placeholder="显示名称"
                            className="w-full h-9 rounded-lg border border-border bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand/20"
                          />
                        )}

                        <Textarea
                          value={slot.content ?? ""}
                          onChange={(e) =>
                            updateSlot(slot.id, { content: e.target.value })
                          }
                          placeholder="提示词内容"
                          rows={5}
                        />
                      </div>
                    </details>
                  );
                })}
              </div>
            </div>
          );
        })}

        {/* Add custom slot */}
        <AddCustomSlot
          onAdd={(slot) => {
            setSlots((prev) => [...prev, slot]);
          }}
          existingIds={slots.map((s) => s.id)}
        />

        {/* Actions */}
        <div className="flex items-center gap-3">
          <Button variant="primary" onClick={handleSave} disabled={saveMut.isPending}>
            {saveMut.isPending ? "保存中..." : "保存全部"}
          </Button>
          <Button
            variant="default"
            onClick={() => resetMut.mutate()}
            disabled={resetMut.isPending}
          >
            {resetMut.isPending ? "恢复中..." : "恢复内置默认"}
          </Button>
        </div>

        {/* Composite preview */}
        {data && (
          <div>
            <h3 className="text-sm font-semibold text-text mb-3">合成预览</h3>
            {Array.isArray(((data as Record<string, unknown>)?.preview as Record<string, unknown>)?.layers) && (
              <div className="space-y-2 mb-3">
                {(
                  ((data as Record<string, unknown>)?.preview as Record<string, unknown>)
                    ?.layers as Array<{ label: string; category: string; content: string }>
                ).map((layer, i) => (
                  <details key={i} className="text-sm">
                    <summary className="text-text-muted cursor-pointer">
                      {layer.label} ({layer.category})
                    </summary>
                    <pre className="mt-1 p-2 bg-surface-muted rounded text-xs text-text overflow-auto whitespace-pre-wrap">
                      {layer.content}
                    </pre>
                  </details>
                ))}
              </div>
            )}
            <Textarea
              value={data.composite ?? ""}
              readOnly
              rows={10}
              className="text-xs font-mono"
            />
          </div>
        )}
      </div>
    </div>
  );
}

function AddCustomSlot({
  onAdd,
  existingIds,
}: {
  onAdd: (slot: EditSlot) => void;
  existingIds: string[];
}) {
  const [id, setId] = useState("");
  const [label, setLabel] = useState("");
  const [scope, setScope] = useState<string[]>(["all"]);
  const [content, setContent] = useState("");
  const [error, setError] = useState("");

  const handleAdd = () => {
    const nid = id.trim().toLowerCase();
    if (!/^[a-z][a-z0-9_]{0,63}$/.test(nid)) {
      setError("ID 格式无效：需以小写字母开头，仅含 a-z、0-9、下划线。");
      return;
    }
    if (existingIds.includes(nid)) {
      setError("ID 已存在。");
      return;
    }
    if (!content.trim()) {
      setError("内容不能为空。");
      return;
    }
    onAdd({
      id: nid,
      label: label.trim() || nid,
      description: "",
      category: "custom",
      scope: scope.length ? scope : ["all"],
      enabled: true,
      order: 100,
      template: content.trim(),
      content: content.trim(),
      builtin: false,
    });
    setId("");
    setLabel("");
    setScope(["all"]);
    setContent("");
    setError("");
    toast.success("已添加自定义层（需点「保存全部」提交到服务端）");
  };

  return (
    <div className="p-4 rounded-xl border border-border bg-surface-muted space-y-3">
      <h3 className="text-sm font-semibold text-text">添加自定义层</h3>
      <div className="grid grid-cols-2 gap-3">
        <input
          type="text"
          value={id}
          onChange={(e) => setId(e.target.value)}
          placeholder="ID（小写英文+下划线），例如：compliance_policy"
          className="h-9 rounded-lg border border-border bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand/20"
        />
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="显示名称，例如：合规约束"
          className="h-9 rounded-lg border border-border bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand/20"
        />
      </div>
      <div className="flex items-center gap-3">
        <span className="text-xs text-text-muted shrink-0">适用场景：</span>
        {SCOPE_OPTIONS.map((sc) => (
          <label key={sc} className="flex items-center gap-1 cursor-pointer text-sm">
            <input
              type="checkbox"
              checked={scope.includes(sc)}
              onChange={() => {
                setScope((prev) =>
                  prev.includes(sc) ? prev.filter((s) => s !== sc) : [...prev, sc]
                );
              }}
              className="w-3.5 h-3.5 rounded accent-brand"
            />
            {SCOPE_LABELS[sc]}
          </label>
        ))}
      </div>
      <Textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="提示词内容"
        rows={4}
      />
      {error && <p className="text-xs text-error">{error}</p>}
      <Button variant="default" size="sm" onClick={handleAdd}>
        添加
      </Button>
    </div>
  );
}

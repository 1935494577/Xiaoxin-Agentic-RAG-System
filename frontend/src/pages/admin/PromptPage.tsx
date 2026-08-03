import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchPrompts, savePrompts } from "../../api/client";
import type { PersonaPreset, PromptSlot } from "../../api/types";
import { PageHeader } from "../../components/admin/PageHeader";
import { SectionGuide, ToolbarSection } from "../../components/admin/SectionGuide";
import { PROMPT_PAGE_HELP } from "../../lib/adminHelp";
import {
  PREVIEW_MODE_LABELS,
  displayCategoryLabel,
  displaySlotLabel,
} from "../../lib/promptDisplay";
import { Button } from "../../components/ui/Button";
import { Switch } from "../../components/ui/Switch";
import { Textarea } from "../../components/ui/Textarea";
import { SkeletonCard } from "../../components/ui/Skeleton";
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
  const [showTechnicalIds, setShowTechnicalIds] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ["prompts", mode, fast],
    queryFn: () => fetchPrompts(mode, fast),
    staleTime: 60_000,
  });

  const [slots, setSlots] = useState<EditSlot[]>([]);
  const [initKey, setInitKey] = useState("");
  const [activePersonaId, setActivePersonaId] = useState("knowledge_consultant");
  const [reasoningMode, setReasoningMode] = useState("react");

  const dataKey = `${mode}-${fast}`;
  if (initKey !== dataKey && data?.slots) {
    setSlots(
      data.slots.map((s) => ({
        ...s,
        content: (s as Record<string, unknown>).content as string ?? s.template ?? "",
        description: (s as Record<string, unknown>).description as string ?? "",
      }))
    );
    setActivePersonaId(data.active_persona_id || "knowledge_consultant");
    setReasoningMode(data.agent_reasoning_mode || "react");
    setInitKey(dataKey);
  }

  const saveMut = useMutation({
    mutationFn: () => {
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
      return savePrompts(mode, payload, fast && mode === "kb", {
        active_persona_id: activePersonaId,
        agent_reasoning_mode: reasoningMode,
      });
    },
    onSuccess: () => {
      toast.success("已保存");
      queryClient.invalidateQueries({ queryKey: ["prompts"] });
    },
    onError: (e: Error) => toast.error(e.message || "保存失败"),
  });

  const resetMut = useMutation({
    mutationFn: () =>
      savePrompts(mode, [], fast && mode === "kb", { reset_defaults: true }),
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

  const removeSlot = (id: string) => {
    setSlots((prev) => {
      const target = prev.find((s) => s.id === id);
      if (!target || target.builtin) return prev;
      return prev.filter((s) => s.id !== id);
    });
    toast.success("已移除自定义层（需点「保存全部」生效）");
  };

  const applyPersonaPreset = (preset: PersonaPreset) => {
    setActivePersonaId(preset.id);
    if (preset.content) {
      updateSlot("persona", { content: preset.content });
    }
  };

  const handleSave = () => {
    saveMut.mutate();
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
    return (
      <div className="p-6 max-w-[1100px] space-y-4">
        <SkeletonCard rows={4} />
      </div>
    );
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
        description="分层配置 AI 的回答风格与人设。与「对话设置」配合：那边管检索策略，这里管怎么说。"
      />

      <SectionGuide
        summary={PROMPT_PAGE_HELP.summary}
        steps={PROMPT_PAGE_HELP.steps}
        tips={PROMPT_PAGE_HELP.tips}
      />

      <div className="space-y-6">
        {/* Persona presets */}
        <div>
          <h3 className="text-sm font-semibold text-text mb-2">第一步 · 选择业务角色</h3>
          <p className="text-xs text-text-muted mb-3">
            选择劲脑业务角色后，会自动填入下方「角色人设」层；你仍可微调文案再保存。
          </p>
          <div className="flex flex-wrap gap-2">
            {(data?.persona_presets || []).map((preset) => {
              const active = activePersonaId === preset.id;
              return (
                <button
                  key={preset.id}
                  type="button"
                  title={preset.description}
                  onClick={() => applyPersonaPreset(preset)}
                  className={
                    "px-3 py-1.5 rounded-full text-sm border transition-colors cursor-pointer " +
                    (active
                      ? "bg-brand text-white border-brand"
                      : "bg-white text-text border-border hover:border-brand/50")
                  }
                >
                  {preset.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Reasoning mode — de-emphasized for KB-only users */}
        <details className="rounded-xl border border-border bg-white/60 px-4 py-3">
          <summary className="text-sm font-semibold text-text cursor-pointer select-none">
            高级 · 思考方式（仅通用回答 / 工具路径）
          </summary>
          <p className="text-xs text-text-muted mt-2 mb-3">
            纯知识库一线场景请在「对话设置 → 业务场景预设」选「一线 KB」，默认「直接回答」即可。
            以下仅影响混合专家、实时工具等需要多步推理的路径。
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pb-1">
            {(data?.reasoning_modes || []).map((opt) => {
              const active = reasoningMode === opt.id;
              return (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setReasoningMode(opt.id)}
                  className={
                    "text-left p-3 rounded-xl border transition-colors cursor-pointer " +
                    (active
                      ? "border-brand bg-brand-light/40 ring-1 ring-brand/30"
                      : "border-border bg-white hover:border-brand/40")
                  }
                >
                  <div className="text-sm font-medium text-text">{opt.label}</div>
                  <div className="text-xs text-text-muted mt-1 leading-relaxed">{opt.description}</div>
                </button>
              );
            })}
          </div>
        </details>

        {/* Toolbar */}
        <div className="rounded-xl border border-border bg-surface-muted/40 p-4 space-y-3">
          <h3 className="text-sm font-semibold text-text">第二步 · 预览与编辑哪类回答</h3>
          <ToolbarSection label="预览">
            <label className="flex items-center gap-2">
              <span className="text-sm text-text-muted">回答类型</span>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value)}
                className="h-9 rounded-lg border border-border bg-white px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand/20"
              >
                <option value="kb">{PREVIEW_MODE_LABELS.kb}</option>
                <option value="general">{PREVIEW_MODE_LABELS.general}</option>
              </select>
            </label>
            {mode === "kb" && (
              <label className="flex items-center gap-2 cursor-pointer select-none" title="对应对话设置中的「快速流式检索」开启时使用的精简任务指令">
                <Switch checked={fast} onCheckedChange={setFast} id="fast-mode" />
                <span className="text-sm text-text">快速检索版提示词</span>
              </label>
            )}
          </ToolbarSection>
          <p className="text-xs text-text-muted">
            {mode === "kb"
              ? "编辑下方各层后，右侧「合成预览」展示知识库命中时模型收到的完整指令。"
              : "编辑通用回答相关层（工具规则、通用任务等）；知识库专用层在此预览中不会出现。"}
          </p>
          <div className="flex flex-wrap gap-4 text-sm">
            <label className="flex items-center gap-2 cursor-pointer select-none text-text-muted">
              <input
                type="checkbox"
                checked={expandAll}
                onChange={(e) => setExpandAll(e.target.checked)}
                className="w-4 h-4 rounded accent-brand"
              />
              展开全部层级
            </label>
            <label className="flex items-center gap-2 cursor-pointer select-none text-text-muted">
              <input
                type="checkbox"
                checked={showTechnicalIds}
                onChange={(e) => setShowTechnicalIds(e.target.checked)}
                className="w-4 h-4 rounded accent-brand"
              />
              显示内部标识（开发用）
            </label>
          </div>
        </div>

        {/* Slot editors */}
        <div>
          <h3 className="text-sm font-semibold text-text mb-3">第三步 · 分层文案（由上到下合并进模型）</h3>
        </div>
        {CATEGORY_ORDER.map((cat) => {
          const rows = grouped[cat];
          if (!rows?.length) return null;
          return (
            <div key={cat}>
              <h4 className="text-sm font-medium text-text-muted mb-3">
                {displayCategoryLabel(cat, categories)}
              </h4>
              <div className="space-y-3">
                {rows.map((slot) => {
                  const isBuiltin = slot.builtin;
                  return (
                    <details
                      key={slot.id}
                      open={expandAll || cat === "persona"}
                      className="border border-border rounded-xl bg-white"
                    >
                      <summary className="px-4 py-3 cursor-pointer select-none hover:bg-surface-muted rounded-xl flex items-center justify-between gap-2">
                        <span className="text-sm font-medium text-text">
                          {isBuiltin ? "🔒 " : "➕ "}
                          {displaySlotLabel(slot)}
                          {showTechnicalIds && (
                            <span className="text-xs text-text-muted ml-2">（{slot.id}）</span>
                          )}
                          {slot.variant && (
                            <span className="ml-2 text-xs text-brand">
                              {slot.variant === "fast" ? "快速检索" : slot.variant === "standard" ? "完整检索" : slot.variant}
                            </span>
                          )}
                        </span>
                        {!isBuiltin && (
                          <button
                            type="button"
                            className="shrink-0 text-xs text-error hover:underline px-2 py-1"
                            onClick={(e) => {
                              e.preventDefault();
                              removeSlot(slot.id);
                            }}
                          >
                            删除
                          </button>
                        )}
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
            <h3 className="text-sm font-semibold text-text mb-2">合成预览（保存前可先核对）</h3>
            <p className="text-xs text-text-muted mb-3">
              以下为当前预览类型下，启用层按顺序拼接后的完整 System Prompt。
            </p>
            {Array.isArray(((data as Record<string, unknown>)?.preview as Record<string, unknown>)?.layers) && (
              <div className="space-y-2 mb-3">
                {(
                  ((data as Record<string, unknown>)?.preview as Record<string, unknown>)
                    ?.layers as Array<{ label: string; category: string; content: string }>
                ).map((layer, i) => (
                  <details key={i} className="text-sm border border-border rounded-lg bg-white">
                    <summary className="px-3 py-2 cursor-pointer text-text">
                      {layer.label}
                      <span className="text-text-muted text-xs ml-2">
                        · {displayCategoryLabel(layer.category, categories)}
                      </span>
                    </summary>
                    <pre className="mx-3 mb-3 p-2 bg-surface-muted rounded text-xs text-text overflow-auto whitespace-pre-wrap">
                      {layer.content}
                    </pre>
                  </details>
                ))}
              </div>
            )}
            <Textarea
              value={data.preview?.composed ?? data.composite ?? ""}
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

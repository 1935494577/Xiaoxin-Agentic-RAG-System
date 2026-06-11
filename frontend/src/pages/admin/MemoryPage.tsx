import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchUiConfig, saveUiConfig } from "../../api/client";
import { PageHeader } from "../../components/admin/PageHeader";
import { Button } from "../../components/ui/Button";
import { Switch } from "../../components/ui/Switch";
import { Slider } from "../../components/ui/Slider";
import { Textarea } from "../../components/ui/Textarea";
import { toast } from "sonner";

export default function MemoryPage() {
  const queryClient = useQueryClient();

  const { data: ui, isLoading, error } = useQuery({
    queryKey: ["uiConfig"],
    queryFn: fetchUiConfig,
    staleTime: 60_000,
  });

  const [form, setForm] = useState<Record<string, unknown>>({});

  useEffect(() => {
    if (ui) {
      const raw = ui as Record<string, unknown>;
      setForm({
        max_history_turns: raw.max_history_turns ?? 6,
        max_history_chars: raw.max_history_chars ?? 6000,
        kb_min_score: raw.kb_min_score ?? 0.55,
        kb_min_rerank_score: raw.kb_min_rerank_score ?? 0.0,
        stream_fast_mode: raw.stream_fast_mode ?? true,
        long_term_memory_enabled: raw.long_term_memory_enabled ?? true,
        general_fallback_enabled: raw.general_fallback_enabled ?? false,
        kb_llm_judge: raw.kb_llm_judge ?? true,
        kb_post_stream_fallback: raw.kb_post_stream_fallback ?? false,
        hybrid_expert_mode: raw.hybrid_expert_mode ?? false,
        stream_verifier_enabled: raw.stream_verifier_enabled ?? false,
        graph_verifier_enabled: raw.graph_verifier_enabled ?? false,
        suggested_questions: Array.isArray(raw.suggested_questions)
          ? (raw.suggested_questions as string[]).join("\n")
          : "",
      });
    }
  }, [ui]);

  const saveMutation = useMutation({
    mutationFn: (patch: Record<string, unknown>) => saveUiConfig(patch),
    onSuccess: () => {
      toast.success("已保存");
      queryClient.invalidateQueries({ queryKey: ["uiConfig"] });
    },
    onError: (e: Error) => toast.error(e.message || "保存失败"),
  });

  const set = (key: string, val: unknown) => setForm((f) => ({ ...f, [key]: val }));

  const handleSave = () => {
    const sq = String(form.suggested_questions || "");
    const lines = sq
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean)
      .slice(0, 12);
    saveMutation.mutate({ ...form, suggested_questions: lines });
  };

  if (isLoading) {
    return <div className="p-6 text-text-muted text-sm">加载中...</div>;
  }

  if (error) {
    return (
      <div className="p-6">
        <PageHeader title="对话记忆" />
        <p className="text-error text-sm">无法加载配置，请确认 API 已启动。</p>
      </div>
    );
  }

  const f = (key: string): boolean => Boolean(form[key]);
  const n = (key: string): number => Number(form[key] ?? 0);

  return (
    <div className="p-6 max-w-[820px]">
      <PageHeader
        title="对话记忆"
        description="Jnao Chat 默认仅知识库检索；用户可在对话框上方开启「混合专家模式」。下方为服务端默认与阈值。"
      />

      <div className="space-y-6">
        <div className="grid grid-cols-2 gap-6">
          {/* Left column: numeric inputs */}
          <div className="space-y-4">
            <label className="block">
              <span className="text-sm text-text">短期记忆轮数（max_history_turns）</span>
              <input
                type="number"
                min={1}
                max={50}
                value={n("max_history_turns") || 6}
                onChange={(e) => set("max_history_turns", Number(e.target.value))}
                className="mt-1 flex h-10 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-brand"
              />
              <span className="text-xs text-text-muted">注入模型的最近对话轮数（每轮含用户+助手）。</span>
            </label>

            <label className="block">
              <span className="text-sm text-text">短期记忆字符上限（max_history_chars）</span>
              <input
                type="number"
                min={500}
                max={50000}
                step={500}
                value={n("max_history_chars") || 6000}
                onChange={(e) => set("max_history_chars", Number(e.target.value))}
                className="mt-1 flex h-10 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-brand"
              />
            </label>

            <div>
              <span className="text-sm text-text">
                混合检索阈值（kb_min_score）：{n("kb_min_score")}
              </span>
              <Slider
                value={n("kb_min_score") || 0.55}
                onChange={(v) => set("kb_min_score", v)}
                min={0}
                max={1}
                step={0.05}
              />
              <span className="text-xs text-text-muted">
                快速流式无重排时：混合分 ≥ 阈值则优先知识库；低于阈值时再用 LLM 判断。
              </span>
            </div>

            <label className="block">
              <span className="text-sm text-text">重排分阈值（kb_min_rerank_score）</span>
              <input
                type="number"
                min={-10}
                max={10}
                step={0.1}
                value={n("kb_min_rerank_score")}
                onChange={(e) => set("kb_min_rerank_score", Number(e.target.value))}
                className="mt-1 flex h-10 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-brand"
              />
              <span className="text-xs text-text-muted">
                标准模式有重排分：低于此值视为与问题不相关，走通用回答。
              </span>
            </label>
          </div>

          {/* Right column: toggles */}
          <div className="space-y-3">
            {[
              { key: "stream_fast_mode", label: "内部快速检索（stream_fast_mode）", help: "跳过重排、减小 top_k；与混合专家模式无关，建议保持开启。" },
              { key: "long_term_memory_enabled", label: "长期记忆（long_term_memory_enabled）", help: "开启后，请求带 session_id 时自动从 SQLite 加载历史。" },
              { key: "general_fallback_enabled", label: "全局通用兜底（general_fallback_enabled）", help: "仅当客户端未传 hybrid_expert_mode 时生效。" },
              { key: "kb_llm_judge", label: "LLM 相关性判断（kb_llm_judge）", help: "无重排时必用；避免弱相关片段误走知识库。" },
              { key: "kb_post_stream_fallback", label: "流式 KB 后再 fallback（kb_post_stream_fallback）", help: "混合专家模式开启时由客户端自动启用。" },
              { key: "hybrid_expert_mode", label: "混合专家模式默认开（hybrid_expert_mode）", help: "新用户首次打开 Jnao Chat 时的默认开关状态。" },
              { key: "stream_verifier_enabled", label: "流式 Verifier（stream_verifier_enabled）" },
              { key: "graph_verifier_enabled", label: "同步 /chat Verifier（graph_verifier_enabled）", help: "LangGraph 校验节点，约 +1s；评测时可开。" },
            ].map(({ key, label, help }) => (
              <label key={key} className="flex items-start gap-3 cursor-pointer select-none">
                <div className="mt-0.5 shrink-0">
                  <Switch
                    checked={f(key)}
                    onCheckedChange={(v) => set(key, v)}
                    id={`mem-${key}`}
                  />
                </div>
                <div>
                  <span className="text-sm text-text">{label}</span>
                  {help && <p className="text-xs text-text-muted">{help}</p>}
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Suggested questions */}
        <div>
          <h3 className="text-sm font-semibold text-text mb-2">Jnao Chat 推荐问题</h3>
          <p className="text-xs text-text-muted mb-2">空对话页展示，每行一条，最多 12 条。</p>
          <Textarea
            value={String(form.suggested_questions || "")}
            onChange={(e) => set("suggested_questions", e.target.value)}
            placeholder="每行一个问题"
            rows={4}
          />
        </div>

        <Button variant="primary" onClick={handleSave} disabled={saveMutation.isPending}>
          {saveMutation.isPending ? "保存中..." : "保存"}
        </Button>

        <p className="text-xs text-text-muted">
          对话界面在 <strong>Jnao Chat（8502）</strong>。提示词请在<strong>提示词</strong>页配置。发送时传 session_id 或 history 即可启用多轮记忆。
        </p>
      </div>
    </div>
  );
}

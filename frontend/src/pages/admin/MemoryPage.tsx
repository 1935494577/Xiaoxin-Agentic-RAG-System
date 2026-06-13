import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchUiConfig, saveUiConfig } from "../../api/client";
import { PageHeader } from "../../components/admin/PageHeader";
import { Button } from "../../components/ui/Button";
import { Switch } from "../../components/ui/Switch";
import { Slider } from "../../components/ui/Slider";
import { Textarea } from "../../components/ui/Textarea";
import { Tabs } from "../../components/ui/Tabs";
import { toast } from "sonner";
import { ChevronDown, ChevronRight } from "lucide-react";

function ToggleRow({
  id,
  label,
  help,
  checked,
  onChange,
}: {
  id: string;
  label: string;
  help?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-start gap-3 cursor-pointer select-none">
      <div className="mt-0.5 shrink-0">
        <Switch checked={checked} onCheckedChange={onChange} id={id} />
      </div>
      <div>
        <span className="text-sm text-text">{label}</span>
        {help && <p className="text-xs text-text-muted mt-0.5">{help}</p>}
      </div>
    </label>
  );
}

function FieldHint({ children }: { children: ReactNode }) {
  return <p className="text-xs text-text-muted mt-1">{children}</p>;
}

function AdvancedBlock({ title, children }: { title: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-lg border border-border bg-white/60">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-4 py-3 text-left text-sm font-medium text-text hover:bg-surface-muted/50 rounded-lg cursor-pointer border-none bg-transparent"
      >
        {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        {title}
      </button>
      {open && <div className="px-4 pb-4 pt-0 space-y-4 border-t border-border">{children}</div>}
    </div>
  );
}

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
        conversation_condense_enabled: raw.conversation_condense_enabled ?? true,
        history_prune_enabled: raw.history_prune_enabled ?? true,
        history_prune_min_similarity: raw.history_prune_min_similarity ?? 0.35,
        history_prune_max_turns: raw.history_prune_max_turns ?? 4,
        history_assistant_max_chars: raw.history_assistant_max_chars ?? 600,
        rolling_summary_enabled: raw.rolling_summary_enabled ?? true,
        rolling_summary_every_n_turns: raw.rolling_summary_every_n_turns ?? 6,
        rolling_summary_min_chars: raw.rolling_summary_min_chars ?? 3500,
        chat_routing_tier: raw.chat_routing_tier ?? "balanced",
        condense_llm_enabled: raw.condense_llm_enabled ?? true,
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
        <PageHeader title="对话设置" />
        <p className="text-error text-sm">无法加载配置，请确认 API 已启动。</p>
      </div>
    );
  }

  const f = (key: string): boolean => Boolean(form[key]);
  const n = (key: string): number => Number(form[key] ?? 0);

  const inputCls =
    "mt-1 flex h-10 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-brand";

  const basicTab = (
    <div className="space-y-5">
      <p className="text-xs text-text-muted">
        面向 Jnao Chat 的默认行为。用户可在对话页切换「混合专家模式」与「新话题」；语气与人设请在
        <Link to="/admin/prompts" className="text-brand hover:underline mx-0.5">
          提示词
        </Link>
        页配置。
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <label className="block">
          <span className="text-sm text-text">短期记忆轮数</span>
          <input
            type="number"
            min={1}
            max={50}
            value={n("max_history_turns") || 6}
            onChange={(e) => set("max_history_turns", Number(e.target.value))}
            className={inputCls}
          />
          <FieldHint>注入模型的最近对话轮数（每轮含用户 + 助手）。</FieldHint>
        </label>
        <label className="block">
          <span className="text-sm text-text">短期记忆字符上限</span>
          <input
            type="number"
            min={500}
            max={50000}
            step={500}
            value={n("max_history_chars") || 6000}
            onChange={(e) => set("max_history_chars", Number(e.target.value))}
            className={inputCls}
          />
        </label>
      </div>
      <div className="space-y-3">
        <ToggleRow
          id="mem-hybrid"
          label="混合专家模式（新用户默认开启）"
          help="对应 Chat 页「混合专家」开关的初始状态：知识库优先，必要时通用补充。"
          checked={f("hybrid_expert_mode")}
          onChange={(v) => set("hybrid_expert_mode", v)}
        />
        <ToggleRow
          id="mem-long-term"
          label="长期记忆（session 持久化）"
          help="带 session_id 时从 SQLite 加载历史。"
          checked={f("long_term_memory_enabled")}
          onChange={(v) => set("long_term_memory_enabled", v)}
        />
        <ToggleRow
          id="mem-stream-fast"
          label="快速流式检索"
          help="跳过重排、减小 top_k，降低首 token 延迟。"
          checked={f("stream_fast_mode")}
          onChange={(v) => set("stream_fast_mode", v)}
        />
      </div>
      <div>
        <h3 className="text-sm font-semibold text-text mb-2">空对话推荐问题</h3>
        <FieldHint>Chat 欢迎页展示，每行一条，最多 12 条。</FieldHint>
        <Textarea
          value={String(form.suggested_questions || "")}
          onChange={(e) => set("suggested_questions", e.target.value)}
          placeholder="每行一个问题"
          rows={4}
          className="mt-2"
        />
      </div>
    </div>
  );

  const kbTab = (
    <div className="space-y-5">
      <p className="text-xs text-text-muted">控制何时走知识库回答 vs 通用回答。混合专家开启时，未命中 KB 可自动 fallback。</p>
      <div>
        <span className="text-sm text-text">混合检索阈值（kb_min_score）：{n("kb_min_score")}</span>
        <Slider
          value={n("kb_min_score") || 0.55}
          onChange={(v) => set("kb_min_score", v)}
          min={0}
          max={1}
          step={0.05}
        />
        <FieldHint>快速模式无重排：混合分 ≥ 阈值则优先 KB。</FieldHint>
      </div>
      <label className="block max-w-md">
        <span className="text-sm text-text">重排分阈值（kb_min_rerank_score）</span>
        <input
          type="number"
          min={-10}
          max={10}
          step={0.1}
          value={n("kb_min_rerank_score")}
          onChange={(e) => set("kb_min_rerank_score", Number(e.target.value))}
          className={inputCls}
        />
        <FieldHint>低于此值视为不相关，走通用回答。</FieldHint>
      </label>
      <div className="space-y-3">
        <ToggleRow
          id="mem-general-fb"
          label="全局通用兜底"
          help="仅当客户端未传 hybrid_expert_mode 时作为默认。"
          checked={f("general_fallback_enabled")}
          onChange={(v) => set("general_fallback_enabled", v)}
        />
        <ToggleRow
          id="mem-kb-judge"
          label="LLM 相关性判断"
          help="检索分边缘时用轻量 LLM 复核，减少误走 KB。"
          checked={f("kb_llm_judge")}
          onChange={(v) => set("kb_llm_judge", v)}
        />
        <ToggleRow
          id="mem-kb-post-fb"
          label="流式 KB 后再 fallback"
          help="混合专家模式下由客户端自动启用。"
          checked={f("kb_post_stream_fallback")}
          onChange={(v) => set("kb_post_stream_fallback", v)}
        />
        <ToggleRow
          id="mem-stream-verifier"
          label="流式 Verifier"
          checked={f("stream_verifier_enabled")}
          onChange={(v) => set("stream_verifier_enabled", v)}
        />
        <ToggleRow
          id="mem-graph-verifier"
          label="同步 /chat Verifier"
          help="LangGraph 校验，约 +1s，评测时可开。"
          checked={f("graph_verifier_enabled")}
          onChange={(v) => set("graph_verifier_enabled", v)}
        />
      </div>
    </div>
  );

  const contextTab = (
    <div className="space-y-5">
      <p className="text-xs text-text-muted">
        多轮指代、换题与长会话摘要。默认建议保持开启；开放性问题会自动优先通用回答。
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <ToggleRow
          id="mem-condense"
          label="查询 Condense + 换题检测"
          help="多轮指代改写；完整问句可规则短路，零 LLM。"
          checked={f("conversation_condense_enabled")}
          onChange={(v) => set("conversation_condense_enabled", v)}
        />
        <ToggleRow
          id="mem-prune"
          label="Embedding 历史剪枝"
          help="续聊时只保留语义相近的历史轮次。"
          checked={f("history_prune_enabled")}
          onChange={(v) => set("history_prune_enabled", v)}
        />
        <ToggleRow
          id="mem-summary"
          label="滚动摘要（异步）"
          help="消息落库后后台更新，不占热路径。"
          checked={f("rolling_summary_enabled")}
          onChange={(v) => set("rolling_summary_enabled", v)}
        />
      </div>
      <AdvancedBlock title="高级参数（一般无需修改）">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-3">
          <div>
            <span className="text-sm text-text">
              剪枝相似度：{n("history_prune_min_similarity") || 0.35}
            </span>
            <Slider
              value={n("history_prune_min_similarity") || 0.35}
              onChange={(v) => set("history_prune_min_similarity", v)}
              min={0.1}
              max={0.9}
              step={0.05}
            />
          </div>
          <label className="block">
            <span className="text-sm text-text">剪枝最多保留轮数</span>
            <input
              type="number"
              min={1}
              max={12}
              value={n("history_prune_max_turns") || 4}
              onChange={(e) => set("history_prune_max_turns", Number(e.target.value))}
              className={inputCls}
            />
          </label>
          <label className="block">
            <span className="text-sm text-text">助手历史截断字符</span>
            <input
              type="number"
              min={200}
              max={4000}
              step={100}
              value={n("history_assistant_max_chars") || 600}
              onChange={(e) => set("history_assistant_max_chars", Number(e.target.value))}
              className={inputCls}
            />
          </label>
          <label className="block">
            <span className="text-sm text-text">摘要更新间隔（轮）</span>
            <input
              type="number"
              min={2}
              max={20}
              value={n("rolling_summary_every_n_turns") || 6}
              onChange={(e) => set("rolling_summary_every_n_turns", Number(e.target.value))}
              className={inputCls}
            />
          </label>
          <label className="block sm:col-span-2">
            <span className="text-sm text-text">触发摘要的最小历史字符</span>
            <input
              type="number"
              min={1000}
              max={50000}
              step={500}
              value={n("rolling_summary_min_chars") || 3500}
              onChange={(e) => set("rolling_summary_min_chars", Number(e.target.value))}
              className={inputCls}
            />
          </label>
        </div>
      </AdvancedBlock>
    </div>
  );

  const routingTab = (
    <div className="space-y-5">
      <p className="text-xs text-text-muted">
        控制预处理 LLM 调用次数（condense、KB 判断）。生成回答仍使用
        <Link to="/admin/models" className="text-brand hover:underline mx-0.5">
          模型配置
        </Link>
        中的「回答模型」。
      </p>
      <label className="block max-w-lg">
        <span className="text-sm text-text">延迟档位</span>
        <select
          value={String(form.chat_routing_tier || "balanced")}
          onChange={(e) => set("chat_routing_tier", e.target.value)}
          className={inputCls}
        >
          <option value="fast">fast — 规则为主，零预处理 LLM（最快）</option>
          <option value="balanced">balanced — 默认，边缘 case 才调 LLM</option>
          <option value="quality">quality — 检索命中也 LLM 复核 KB（最严）</option>
        </select>
        <FieldHint>
          fast 会关闭 condense LLM 与 kb LLM judge；quality 会提高 KB 门槛。
        </FieldHint>
      </label>
      <div className="rounded-lg border border-border bg-brand-light/30 px-4 py-3 text-sm text-text">
        <p className="font-medium mb-1">预处理模型（routing_model）</p>
        <p className="text-xs text-text-muted leading-relaxed">
          请在
          <Link to="/admin/models" className="text-brand hover:underline mx-1">
            模型 → 各接入方式
          </Link>
          中配置「预处理模型」（如 gpt-4o-mini）。留空则与回答模型相同。避免在此处与模型页重复配置。
        </p>
      </div>
    </div>
  );

  return (
    <div className="p-6 max-w-[860px]">
      <PageHeader
        title="对话设置"
        description="服务端默认与阈值。Chat 页仅暴露「混合专家」与「新话题」；其余在此分 Tab 管理。"
      />

      <Tabs
        defaultTab="basic"
        tabs={[
          { id: "basic", label: "基础", content: basicTab },
          { id: "kb", label: "检索与 KB", content: kbTab },
          { id: "context", label: "多轮上下文", content: contextTab },
          { id: "routing", label: "性能路由", content: routingTab },
        ]}
        className="mt-4"
      />

      <div className="mt-8 pt-6 border-t border-border">
        <Button variant="primary" onClick={handleSave} disabled={saveMutation.isPending}>
          {saveMutation.isPending ? "保存中..." : "保存全部设置"}
        </Button>
      </div>
    </div>
  );
}

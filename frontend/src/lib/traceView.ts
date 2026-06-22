/** 将 feedback trace JSON 解析为运营可读的中文结构化视图 */

export type TraceDetailRow = { label: string; value: string };

export type TraceSpanView = {
  order: number;
  label: string;
  status: string;
  statusLabel: string;
  latencyMs?: number;
  details: TraceDetailRow[];
  error?: string;
};

export type FeedbackTraceView = {
  traceId: string;
  question: string;
  answerModeLabel: string;
  startedAt: string;
  endedAt: string;
  durationLabel: string;
  overview: TraceDetailRow[];
  spans: TraceSpanView[];
  sources: string[];
  contextCount?: number;
};

const SPAN_LABELS: Record<string, string> = {
  "retrieval/retriever": "① 知识库检索",
  "retrieval/agentic": "① Agent 多轮检索",
  "router/chain": "② 判定回答路径",
  "llm_call/llm": "③ 生成回答",
  "fallback/llm": "③ 通用兜底生成",
  "verifier/llm": "④ 流式校验",
  "run/tool": "关系图谱工具",
};

const STATUS_LABELS: Record<string, string> = {
  ok: "成功",
  error: "失败",
  skipped: "跳过",
};

const ANSWER_MODE_LABELS: Record<string, string> = {
  kb: "知识库",
  general: "通用回答",
};

const RAG_ARCH_LABELS: Record<string, string> = {
  classic: "经典检索",
  graph: "图谱检索",
  agentic: "Agent 多轮",
};

function asRecord(v: unknown): Record<string, unknown> {
  return v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : {};
}

function str(v: unknown): string {
  if (v == null) return "";
  if (typeof v === "string") return v.trim();
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return "";
}

function basename(path: string): string {
  const p = path.replace(/\\/g, "/");
  const i = p.lastIndexOf("/");
  return i >= 0 ? p.slice(i + 1) : p;
}

function unwrapSpanOutput(output: unknown): Record<string, unknown> {
  const o = asRecord(output);
  const inner = asRecord(o.result);
  return Object.keys(inner).length ? inner : o;
}

function spanLabel(type: string, name: string): string {
  const key = `${type}/${name}`;
  if (SPAN_LABELS[key]) return SPAN_LABELS[key];
  const typeOnly: Record<string, string> = {
    retrieval: "检索",
    router: "路由",
    llm_call: "大模型",
    fallback: "兜底",
    verifier: "校验",
  };
  const t = typeOnly[type] || type || "步骤";
  return name && name !== type ? `${t} · ${name}` : t;
}

function formatTime(iso: string): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function formatDuration(started: string, ended: string): string {
  if (!started || !ended) return "—";
  try {
    const ms = new Date(ended).getTime() - new Date(started).getTime();
    if (!Number.isFinite(ms) || ms < 0) return "—";
    if (ms < 1000) return `${ms} 毫秒`;
    return `${(ms / 1000).toFixed(2)} 秒`;
  } catch {
    return "—";
  }
}

function pushRow(rows: TraceDetailRow[], label: string, value: unknown) {
  const s = str(value);
  if (s) rows.push({ label, value: s });
}

function parseRetrieveSpan(out: Record<string, unknown>, inp: Record<string, unknown>): TraceDetailRow[] {
  const rows: TraceDetailRow[] = [];
  pushRow(rows, "检索问句", out.rewritten_query || inp.question);
  pushRow(rows, "检索架构", RAG_ARCH_LABELS[str(out.rag_architecture || inp.rag_architecture)] || out.rag_architecture);
  if (out.context_count != null) {
    rows.push({ label: "命中片段数", value: String(out.context_count) });
  }
  if (inp.stream_fast_mode != null) {
    rows.push({ label: "快速流式", value: inp.stream_fast_mode ? "是" : "否" });
  }
  return rows;
}

function parseRouteSpan(out: Record<string, unknown>): TraceDetailRow[] {
  const rows: TraceDetailRow[] = [];
  const mode = str(out.answer_mode);
  if (mode) {
    rows.push({ label: "最终路径", value: ANSWER_MODE_LABELS[mode] || mode });
  }
  if (out.tool_route_override) {
    rows.push({
      label: "工具路由",
      value: out.tool_route_override === "realtime" ? "实时信息（天气/时间等）" : "已启用对话工具",
    });
  }
  pushRow(rows, "RAG 架构", RAG_ARCH_LABELS[str(out.rag_architecture)] || out.rag_architecture);
  return rows;
}

function parseLlmSpan(out: Record<string, unknown>, inp: Record<string, unknown>): TraceDetailRow[] {
  const rows: TraceDetailRow[] = [];
  pushRow(rows, "模型", inp.model);
  const mode = str(inp.answer_mode || out.answer_mode);
  if (mode) rows.push({ label: "回答模式", value: ANSWER_MODE_LABELS[mode] || mode });
  if (out.answer_len != null) rows.push({ label: "回答长度", value: `${out.answer_len} 字` });
  if (out.verified != null) rows.push({ label: "校验通过", value: out.verified ? "是" : "否" });
  const tools = out.tool_trace;
  if (Array.isArray(tools) && tools.length) {
    rows.push({ label: "工具调用", value: `${tools.length} 次` });
  }
  return rows;
}

function spanDetails(type: string, name: string, span: Record<string, unknown>): TraceDetailRow[] {
  const inp = asRecord(span.input);
  const out = unwrapSpanOutput(span.output);
  if (type === "retrieval" || name === "retriever" || name === "agentic") {
    return parseRetrieveSpan(out, inp);
  }
  if (type === "router" || name === "chain") {
    return parseRouteSpan(out);
  }
  if (type === "llm_call" || type === "fallback" || type === "verifier" || name === "llm") {
    return parseLlmSpan(out, inp);
  }
  const rows: TraceDetailRow[] = [];
  const q = str(inp.question);
  if (q) rows.push({ label: "输入摘要", value: q.length > 80 ? `${q.slice(0, 80)}…` : q });
  return rows;
}

export function parseFeedbackTrace(raw: Record<string, unknown>): FeedbackTraceView {
  const traceId = str(raw.trace_id) || "—";
  const question = str(raw.question);
  const answerMode = str(raw.answer_mode);
  const meta = asRecord(raw.meta);
  const startedAt = str(raw.started_at);
  const endedAt = str(raw.ended_at);

  const overview: TraceDetailRow[] = [];
  pushRow(overview, "用户", raw.user_id);
  pushRow(overview, "会话", raw.session_id);
  if (answerMode) {
    overview.push({ label: "回答路径", value: ANSWER_MODE_LABELS[answerMode] || answerMode });
  }
  pushRow(
    overview,
    "RAG 架构",
    RAG_ARCH_LABELS[str(meta.rag_architecture)] || meta.rag_architecture
  );
  if (meta.source_count != null) {
    overview.push({ label: "引用来源", value: `${meta.source_count} 个` });
  }
  if (meta.kb_fallback === true) {
    overview.push({ label: "兜底", value: "知识库未命中后走通用回答" });
  }
  if (meta.verified === false) {
    overview.push({ label: "校验", value: "未通过流式校验" });
  }
  pushRow(overview, "错误", meta.error);

  const sources: string[] = [];
  const seen = new Set<string>();
  let contextCount: number | undefined;

  const spansRaw = Array.isArray(raw.spans) ? raw.spans : [];
  const spans: TraceSpanView[] = spansRaw.map((item, idx) => {
    const sp = asRecord(item);
    const type = str(sp.type);
    const name = str(sp.name);
    const status = str(sp.status) || "ok";
    const out = unwrapSpanOutput(sp.output);

    if (out.context_count != null && contextCount == null) {
      const n = Number(out.context_count);
      if (Number.isFinite(n)) contextCount = n;
    }
    const metaList = out.contexts_meta;
    if (Array.isArray(metaList)) {
      for (const row of metaList) {
        const src = str(asRecord(row).source);
        if (src && !seen.has(src)) {
          seen.add(src);
          sources.push(src);
        }
      }
    }

    let latencyMs: number | undefined;
    if (sp.latency_ms != null) {
      const n = Number(sp.latency_ms);
      if (Number.isFinite(n)) latencyMs = n;
    }

    return {
      order: idx + 1,
      label: spanLabel(type, name),
      status,
      statusLabel: STATUS_LABELS[status] || status,
      latencyMs,
      details: spanDetails(type, name, sp),
      error: str(sp.error) || undefined,
    };
  });

  return {
    traceId,
    question,
    answerModeLabel: ANSWER_MODE_LABELS[answerMode] || answerMode || "—",
    startedAt: formatTime(startedAt),
    endedAt: formatTime(endedAt),
    durationLabel: formatDuration(startedAt, endedAt),
    overview,
    spans,
    sources: sources.map((s) => basename(s)),
    contextCount,
  };
}

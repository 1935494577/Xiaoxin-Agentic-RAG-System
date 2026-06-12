import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  approveFeedback,
  exportFeedbackJsonl,
  fetchFeedbackList,
  fetchFeedbackTrace,
  rejectFeedback,
  runFeedbackTriage,
} from "../../api/client";
import type { FeedbackItem } from "../../api/types";
import { PageHeader } from "../../components/admin/PageHeader";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { toast } from "sonner";

const PAGE_SIZE = 20;

const ISSUE_LABELS: Record<string, string> = {
  retrieval_miss: "检索未命中",
  hallucination: "幻觉 / 与资料不符",
  stale_doc: "文档过时",
  prompt: "提示词 / 生成",
  tone: "语气 / 表达",
  ok: "无问题",
};

function ratingLabel(rating: number): { text: string; variant: "success" | "warning" | "default" } {
  if (rating === 1) return { text: "👍 有帮助", variant: "success" };
  if (rating === 0) return { text: "👎 没帮助", variant: "warning" };
  return { text: `评分 ${rating}`, variant: "default" };
}

function severityVariant(sev: string | null | undefined): "success" | "warning" | "default" {
  if (sev === "high") return "warning";
  if (sev === "medium") return "default";
  return "success";
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function FeedbackInboxPage() {
  const queryClient = useQueryClient();
  const [offset, setOffset] = useState(0);
  const [ratingFilter, setRatingFilter] = useState<"" | "0" | "1">("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sort, setSort] = useState<"created_desc" | "severity_desc">("severity_desc");
  const [sinceDays, setSinceDays] = useState(7);
  const [traceDetail, setTraceDetail] = useState<Record<string, unknown> | null>(null);
  const [traceLoading, setTraceLoading] = useState(false);
  const [actionId, setActionId] = useState<string | null>(null);

  const queryKey = useMemo(
    () => ["feedback-list", offset, ratingFilter, statusFilter, sort, sinceDays],
    [offset, ratingFilter, statusFilter, sort, sinceDays]
  );

  const { data, isLoading, error, refetch } = useQuery({
    queryKey,
    queryFn: () =>
      fetchFeedbackList({
        offset,
        limit: PAGE_SIZE,
        since_days: sinceDays,
        sort,
        status: statusFilter || undefined,
        rating: ratingFilter === "" ? undefined : Number(ratingFilter),
      }),
    staleTime: 15_000,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["feedback-list"] });

  const openTrace = async (item: FeedbackItem) => {
    if (!item.trace_id) {
      toast.message("该反馈未关联 trace_id");
      return;
    }
    setTraceLoading(true);
    try {
      const trace = await fetchFeedbackTrace(item.trace_id);
      setTraceDetail(trace);
    } catch {
      toast.error("无法加载 Trace，请确认 LOCAL_TRACE_ENABLED 且存在对应记录");
    } finally {
      setTraceLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const res = await exportFeedbackJsonl();
      toast.success(`已导出 ${res.exported} 条到 feedback.jsonl`);
    } catch {
      toast.error("导出失败");
    }
  };

  const handleTriage = async (useLlm: boolean) => {
    try {
      const res = await runFeedbackTriage({ limit: 30, use_llm: useLlm, rating: 0 });
      toast.success(`Triage 完成：处理 ${res.processed} 条，队列 ${res.queued} 条`);
      invalidate();
    } catch {
      toast.error("Triage 失败");
    }
  };

  const handleApprove = async (id: string) => {
    setActionId(id);
    try {
      await approveFeedback(id);
      toast.success("已采纳建议（待 Sprint C Actuator 执行）");
      invalidate();
    } catch {
      toast.error("操作失败");
    } finally {
      setActionId(null);
    }
  };

  const handleReject = async (id: string) => {
    setActionId(id);
    try {
      await rejectFeedback(id);
      toast.success("已驳回");
      invalidate();
    } catch {
      toast.error("操作失败");
    } finally {
      setActionId(null);
    }
  };

  return (
    <div className="p-6 max-w-[1100px]">
      <PageHeader
        title="用户反馈"
        description="Chat 点赞/点踩与可选纠错 → 规则或 LLM Triage 分类 → 运营采纳/驳回。负反馈优先按严重度排序。"
      />

      <div className="flex flex-wrap items-center gap-3 mb-4">
        <label className="text-sm text-text-muted">
          时间
          <select
            className="ml-2 border border-border rounded-md px-2 py-1 text-sm bg-white"
            value={sinceDays}
            onChange={(e) => {
              setSinceDays(Number(e.target.value));
              setOffset(0);
            }}
          >
            <option value={7}>近 7 天</option>
            <option value={30}>近 30 天</option>
            <option value={90}>近 90 天</option>
          </select>
        </label>
        <label className="text-sm text-text-muted">
          评分
          <select
            className="ml-2 border border-border rounded-md px-2 py-1 text-sm bg-white"
            value={ratingFilter}
            onChange={(e) => {
              setRatingFilter(e.target.value as "" | "0" | "1");
              setOffset(0);
            }}
          >
            <option value="">全部</option>
            <option value="1">👍</option>
            <option value="0">👎</option>
          </select>
        </label>
        <label className="text-sm text-text-muted">
          状态
          <select
            className="ml-2 border border-border rounded-md px-2 py-1 text-sm bg-white"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">全部</option>
            <option value="pending">待 Triage</option>
            <option value="triaged">已分类</option>
            <option value="approved">已采纳</option>
            <option value="rejected">已驳回</option>
          </select>
        </label>
        <label className="text-sm text-text-muted">
          排序
          <select
            className="ml-2 border border-border rounded-md px-2 py-1 text-sm bg-white"
            value={sort}
            onChange={(e) => setSort(e.target.value as "created_desc" | "severity_desc")}
          >
            <option value="severity_desc">严重度优先</option>
            <option value="created_desc">时间最新</option>
          </select>
        </label>
        <Button type="button" variant="primary" onClick={() => handleTriage(false)}>
          规则 Triage
        </Button>
        <Button type="button" variant="default" onClick={() => handleTriage(true)}>
          LLM Triage
        </Button>
        <Button type="button" variant="default" onClick={() => refetch()}>
          刷新
        </Button>
        <Button type="button" variant="default" onClick={handleExport}>
          导出 JSONL
        </Button>
        <span className="text-xs text-text-muted ml-auto">
          共 {total} 条 · 第 {page}/{totalPages} 页
        </span>
      </div>

      {isLoading && <p className="text-sm text-text-muted">加载中...</p>}
      {error && (
        <p className="text-sm text-warning">无法加载反馈列表，请确认 API 已启动。</p>
      )}

      {!isLoading && !error && items.length === 0 && (
        <p className="text-sm text-text-muted py-8 text-center">暂无反馈记录</p>
      )}

      <div className="space-y-3">
        {items.map((item) => {
          const badge = ratingLabel(item.rating);
          const issueLabel = item.issue_type ? ISSUE_LABELS[item.issue_type] || item.issue_type : null;
          return (
            <div
              key={item.id}
              className="border border-border rounded-lg p-4 bg-white shadow-sm"
            >
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <Badge variant={badge.variant}>{badge.text}</Badge>
                {item.status && item.status !== "pending" && (
                  <Badge variant="default">{item.status}</Badge>
                )}
                {issueLabel && (
                  <Badge variant={item.issue_type === "ok" ? "success" : "warning"}>
                    {issueLabel}
                  </Badge>
                )}
                {item.severity && (
                  <Badge variant={severityVariant(item.severity)}>{item.severity}</Badge>
                )}
                {item.answer_mode && (
                  <Badge variant={item.answer_mode === "kb" ? "success" : "warning"}>
                    {item.answer_mode === "kb" ? "知识库" : "通用"}
                  </Badge>
                )}
                <span className="text-xs text-text-muted">{formatTime(item.created_at)}</span>
                <span className="text-xs text-text-muted">用户 {item.user_id}</span>
                {item.context_count != null && (
                  <span className="text-xs text-text-muted">检索 {item.context_count} 条</span>
                )}
              </div>
              {item.triage_summary && (
                <p className="text-sm text-brand bg-brand-light rounded px-2 py-1 mb-2">
                  {item.triage_summary}
                </p>
              )}
              {item.correction && (
                <p className="text-sm text-warning bg-warning-bg rounded px-2 py-1 mb-2">
                  用户纠错：{item.correction}
                </p>
              )}
              {item.question && (
                <p className="text-sm text-text mb-1">
                  <span className="text-text-muted">问：</span>
                  {item.question}
                </p>
              )}
              {item.answer_preview && (
                <p className="text-sm text-text-muted line-clamp-2 mb-2">{item.answer_preview}</p>
              )}
              {item.suggested_actions && item.suggested_actions.length > 0 && (
                <ul className="text-xs text-text-muted mb-2 list-disc pl-4">
                  {item.suggested_actions.map((a, i) => (
                    <li key={i}>
                      {a.action}
                      {a.confidence != null ? ` (${Math.round(a.confidence * 100)}%)` : ""}
                      {a.detail ? ` — ${a.detail}` : ""}
                    </li>
                  ))}
                </ul>
              )}
              {item.sources?.length > 0 && (
                <p className="text-xs text-text-muted mb-2">
                  引用：{item.sources.map((s) => s.split(/[/\\]/).pop() || s).join(" · ")}
                </p>
              )}
              <div className="flex flex-wrap gap-2 mt-2">
                {item.status === "triaged" && (
                  <>
                    <Button
                      type="button"
                      variant="primary"
                      className="text-xs"
                      disabled={actionId === item.id}
                      onClick={() => handleApprove(item.id)}
                    >
                      采纳建议
                    </Button>
                    <Button
                      type="button"
                      variant="default"
                      className="text-xs"
                      disabled={actionId === item.id}
                      onClick={() => handleReject(item.id)}
                    >
                      驳回
                    </Button>
                  </>
                )}
                {item.trace_id && (
                  <Button
                    type="button"
                    variant="default"
                    className="text-xs"
                    disabled={traceLoading}
                    onClick={() => openTrace(item)}
                  >
                    查看 Trace
                  </Button>
                )}
                <code className="text-[11px] text-text-muted bg-surface-muted px-2 py-1 rounded">
                  {item.trace_id || item.id}
                </code>
              </div>
            </div>
          );
        })}
      </div>

      {totalPages > 1 && (
        <div className="flex gap-2 mt-6 justify-center">
          <Button
            type="button"
            variant="default"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          >
            上一页
          </Button>
          <Button
            type="button"
            variant="default"
            disabled={offset + PAGE_SIZE >= total}
            onClick={() => setOffset(offset + PAGE_SIZE)}
          >
            下一页
          </Button>
        </div>
      )}

      {traceDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-xl max-w-3xl w-full max-h-[80vh] overflow-hidden flex flex-col shadow-xl">
            <div className="px-4 py-3 border-b border-border flex justify-between items-center">
              <h3 className="font-semibold text-sm">Trace 详情</h3>
              <Button type="button" variant="default" onClick={() => setTraceDetail(null)}>
                关闭
              </Button>
            </div>
            <pre className="p-4 text-xs overflow-auto flex-1 font-mono bg-surface-muted">
              {JSON.stringify(traceDetail, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

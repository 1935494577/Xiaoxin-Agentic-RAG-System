import { useQuery } from "@tanstack/react-query";
import { fetchFeedbackStats } from "../../api/client";
import { Badge } from "../ui/Badge";

const ISSUE_LABELS: Record<string, string> = {
  retrieval_miss: "检索未命中",
  hallucination: "幻觉",
  stale_doc: "文档过时",
  prompt: "提示词",
  tone: "语气",
  ok: "无问题",
  unknown: "未分类",
};

const STATUS_LABELS: Record<string, string> = {
  pending: "待研判",
  triaged: "已分类",
  approved: "已采纳",
  applied: "已执行",
  evaluated: "已评测",
  rejected: "已驳回",
};

type Props = {
  sinceDays?: number;
};

export function FeedbackStatsPanel({ sinceDays = 7 }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ["feedback-stats", sinceDays],
    queryFn: () => fetchFeedbackStats(sinceDays),
    staleTime: 30_000,
  });

  if (isLoading) {
    return <p className="text-sm text-text-muted mb-4">加载统计…</p>;
  }
  if (!data) return null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
      <div className="rounded-lg border border-border bg-surface p-3">
        <p className="text-xs text-text-muted">近 {data.since_days} 天反馈</p>
        <p className="text-2xl font-semibold text-text mt-1">{data.total}</p>
      </div>
      <div className="rounded-lg border border-border bg-surface p-3">
        <p className="text-xs text-text-muted">👍 有帮助</p>
        <p className="text-2xl font-semibold text-success mt-1">{data.positive}</p>
      </div>
      <div className="rounded-lg border border-border bg-surface p-3">
        <p className="text-xs text-text-muted">👎 没帮助</p>
        <p className="text-2xl font-semibold text-warning mt-1">{data.negative}</p>
      </div>
      <div className="rounded-lg border border-border bg-surface p-3">
        <p className="text-xs text-text-muted">待研判</p>
        <p className="text-2xl font-semibold text-brand mt-1">{data.pending_triage}</p>
      </div>
      {data.by_issue_type.length > 0 && (
        <div className="col-span-2 sm:col-span-4 rounded-lg border border-border bg-surface p-3">
          <p className="text-xs text-text-muted mb-2">负反馈问题类型</p>
          <div className="flex flex-wrap gap-2">
            {data.by_issue_type.map((row) => (
              <Badge key={row.issue_type} variant="default">
                {ISSUE_LABELS[row.issue_type] || row.issue_type} · {row.count}
              </Badge>
            ))}
          </div>
        </div>
      )}
      {data.by_status.length > 0 && (
        <div className="col-span-2 sm:col-span-4 rounded-lg border border-border bg-surface p-3">
          <p className="text-xs text-text-muted mb-2">处理状态</p>
          <div className="flex flex-wrap gap-2">
            {data.by_status.map((row) => (
              <Badge key={row.status} variant="default">
                {STATUS_LABELS[row.status] || row.status} · {row.count}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

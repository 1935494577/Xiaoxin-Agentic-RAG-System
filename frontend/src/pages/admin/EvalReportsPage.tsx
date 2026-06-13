import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  exportEvalReports,
  fetchEvalReports,
  runFeedbackEvaluate,
} from "../../api/client";
import { PageHeader } from "../../components/admin/PageHeader";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { toast } from "sonner";

const METRIC_LABELS: Record<string, string> = {
  naive_context_answer_overlap_rate: "上下文-答案重叠率",
  faithfulness: "Faithfulness",
  answer_relevancy: "Answer Relevancy",
  rows: "样本数",
};

function formatMetric(key: string, val: unknown): string {
  if (typeof val === "number") {
    if (key.includes("rate") || key.includes("relevancy") || key === "faithfulness") {
      return `${(val * 100).toFixed(1)}%`;
    }
    return String(val);
  }
  return String(val ?? "—");
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function EvalReportsPage() {
  const queryClient = useQueryClient();
  const [offset, setOffset] = useState(0);
  const [running, setRunning] = useState(false);
  const limit = 20;

  const queryKey = useMemo(() => ["eval-reports", offset], [offset]);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey,
    queryFn: () => fetchEvalReports({ offset, limit }),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const page = Math.floor(offset / limit) + 1;

  const handleRunEval = async () => {
    setRunning(true);
    try {
      const res = await runFeedbackEvaluate();
      if (!res.ok) {
        toast.error(res.error || "评测失败");
        return;
      }
      toast.success(
        `评测完成：${res.golden_rows} 条 golden · ${res.mode === "ragas" ? "RAGAS" : "Naive 回退"}`
      );
      queryClient.invalidateQueries({ queryKey: ["eval-reports"] });
    } catch {
      toast.error("评测请求失败");
    } finally {
      setRunning(false);
    }
  };

  const handleExport = async () => {
    try {
      const res = await exportEvalReports();
      toast.success(`已导出 ${res.exported} 份评测报告（JSON）`);
    } catch {
      toast.error("导出失败");
    }
  };

  return (
    <div className="p-6 max-w-[1100px]">
      <PageHeader
        title="评测报告"
        description="基于 golden.jsonl 离线评测；采纳反馈写入 golden 后会自动异步跑评测并对比上一份指标。"
      />

      <div className="flex flex-wrap gap-2 mb-4 items-center">
        <Button type="button" variant="primary" disabled={running} onClick={handleRunEval}>
          {running ? "评测中…" : "立即评测"}
        </Button>
        <Button type="button" variant="default" onClick={() => refetch()}>
          刷新
        </Button>
        <Button type="button" variant="default" onClick={handleExport}>
          导出 JSON
        </Button>
        <span className="text-xs text-text-muted ml-auto">
          共 {total} 份 · 第 {page}/{totalPages} 页
        </span>
      </div>

      {isLoading && <p className="text-sm text-text-muted">加载中...</p>}
      {error && <p className="text-sm text-warning">无法加载评测报告。</p>}
      {!isLoading && !error && items.length === 0 && (
        <p className="text-sm text-text-muted py-8 text-center">
          暂无报告。请先在反馈 Inbox 采纳坏例写入 golden，或确保 eval/golden.jsonl 有数据后点「立即评测」。
        </p>
      )}

      <div className="space-y-3">
        {items.map((item) => {
          const deltaKeys = Object.keys(item.delta || {});
          return (
            <div key={item.id} className="border border-border rounded-lg p-4 bg-white shadow-sm">
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <Badge variant={item.mode === "ragas" ? "success" : "default"}>
                  {item.mode === "ragas" ? "RAGAS" : "Naive 回退"}
                </Badge>
                <span className="text-xs text-text-muted">{formatTime(item.created_at)}</span>
                <span className="text-xs text-text-muted">golden {item.golden_rows} 条</span>
                {item.feedback_id && (
                  <code className="text-[11px] text-text-muted bg-surface-muted px-2 py-0.5 rounded">
                    反馈 {item.feedback_id.slice(0, 8)}…
                  </code>
                )}
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-text-muted text-xs mb-1">当前指标</p>
                  <ul className="space-y-0.5">
                    {Object.entries(item.metrics || {})
                      .filter(([k]) => k !== "mode" && k !== "ragas_error")
                      .map(([k, v]) => (
                        <li key={k}>
                          {METRIC_LABELS[k] || k}：{formatMetric(k, v)}
                        </li>
                      ))}
                  </ul>
                </div>
                {deltaKeys.length > 0 && (
                  <div>
                    <p className="text-text-muted text-xs mb-1">相对上一份 Δ</p>
                    <ul className="space-y-0.5">
                      {deltaKeys.map((k) => {
                        const d = item.delta[k];
                        const up = typeof d === "number" && d > 0;
                        const down = typeof d === "number" && d < 0;
                        return (
                          <li
                            key={k}
                            className={
                              up ? "text-success" : down ? "text-warning" : "text-text"
                            }
                          >
                            {METRIC_LABELS[k] || k}：{formatMetric(k, d)}
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}
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
            onClick={() => setOffset(Math.max(0, offset - limit))}
          >
            上一页
          </Button>
          <Button
            type="button"
            variant="default"
            disabled={offset + limit >= total}
            onClick={() => setOffset(offset + limit)}
          >
            下一页
          </Button>
        </div>
      )}
    </div>
  );
}

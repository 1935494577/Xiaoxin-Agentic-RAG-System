import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ThumbsDown, ThumbsUp } from "lucide-react";
import { PageHeader } from "../../components/admin/PageHeader";
import { MetricCard } from "../../components/admin/MetricCard";
import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { SkeletonCard } from "../../components/ui/Skeleton";
import {
  fetchOpsDigest,
  fetchTokenUsageSummary,
  opsDigestQueryKey,
  tokenUsageSummaryQueryKey,
  type TokenUsageTurnRecord,
} from "../../lib/threadTokenUsage";
import { formatTokenCount } from "../../lib/tokenUsage";

function formatTime(iso: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("zh-CN", { hour12: false });
}

function callerLabel(caller: string): string {
  if (caller === "answer") return "回答";
  if (caller === "tool_loop") return "工具循环";
  if (caller === "verifier") return "校验";
  return caller || "—";
}

export default function TokenUsagePage() {
  const { data, isFetching, error, refetch, isLoading } = useQuery({
    queryKey: tokenUsageSummaryQueryKey(100),
    queryFn: () => fetchTokenUsageSummary(100),
    staleTime: 10_000,
    refetchInterval: 30_000,
  });
  const digestQuery = useQuery({
    queryKey: opsDigestQueryKey(1),
    queryFn: () => fetchOpsDigest(1),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
  const digest = digestQuery.data;

  const modelRows = useMemo(() => {
    const byModel = data?.by_model || {};
    return Object.entries(byModel).sort(
      (a, b) => (b[1].total_tokens || 0) - (a[1].total_tokens || 0),
    );
  }, [data]);

  const turns: TokenUsageTurnRecord[] = data?.turns?.length
    ? data.turns
    : (data?.records || []).map((r) => ({
        session_id: r.session_id,
        question_preview: r.question_preview,
        created_at: r.created_at,
        model: r.model,
        prompt_tokens: r.prompt_tokens,
        completion_tokens: r.completion_tokens,
        total_tokens: r.total_tokens,
        llm_call_count: 1,
        callers: [r.caller].filter(Boolean),
      }));
  const callCount = data?.total_calls ?? data?.total_llm_calls ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Token 用量"
        description="全局总量按 LLM 调用累计；下方列表按「用户提问」聚合（一次提问可能含多轮工具/回答调用）。"
      >
        <Button type="button" variant="default" size="sm" onClick={() => refetch()} disabled={isFetching}>
          {isFetching ? "刷新中…" : "刷新"}
        </Button>
      </PageHeader>

      <div className="mb-6 rounded-xl border border-border bg-surface-muted/40 p-4 text-sm text-text-muted space-y-1">
        <p>
          Chat 会话工具栏也会显示当前会话徽章。Web / IM 知识库路径经 Main API（8010）自动写入同一库。
        </p>
        <p>
          开关：<code className="text-xs">config.yaml → token_usage.enabled</code>
          {" · "}
          <Link to="/chat" className="text-brand hover:underline">
            打开 Jnao Chat
          </Link>
        </p>
      </div>

      {isLoading ? <SkeletonCard rows={3} /> : null}

      {error ? (
        <p className="text-sm text-warning mb-4">加载失败：{(error as Error).message || "未知错误"}</p>
      ) : null}

      {data && !data.available ? (
        <p className="text-sm text-warning mb-4">Token 计量服务暂不可用，请确认 Main API（8010）已启动。</p>
      ) : null}

      {digest ? (
        <div className="mb-8 space-y-3">
          <h3 className="text-sm font-semibold text-text">今日一览（UTC 日起）</h3>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            <MetricCard
              label="今日 Token"
              value={formatTokenCount(digest.token_usage.total_tokens || 0)}
            />
            <MetricCard label="今日 LLM 调用" value={String(digest.token_usage.total_calls || 0)} />
            <MetricCard label="反馈总数" value={String(digest.feedback.total || 0)} />
            <MetricCard
              label="好评"
              value={String(digest.feedback.positive || 0)}
              icon={ThumbsUp}
              variant="success"
            />
            <MetricCard
              label="差评"
              value={String(digest.feedback.negative || 0)}
              icon={ThumbsDown}
              variant="warning"
            />
            <MetricCard label="检索未命中" value={String(digest.feedback.retrieval_miss || 0)} />
          </div>
          <p className="text-xs text-text-muted">
            待分诊 {digest.feedback.pending_triage || 0}
            {" · "}
            <Link to="/admin/feedback" className="text-brand hover:underline">
              打开反馈收件箱
            </Link>
          </p>
        </div>
      ) : null}

      {data ? (
        <div className="space-y-8">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <MetricCard label="总 Token" value={formatTokenCount(data.total_tokens || 0)} />
            <MetricCard label="输入" value={formatTokenCount(data.total_input_tokens || 0)} />
            <MetricCard label="输出" value={formatTokenCount(data.total_output_tokens || 0)} />
            <MetricCard label="LLM 调用次数" value={String(callCount)} />
          </div>

          {modelRows.length > 0 ? (
            <div>
              <h3 className="mb-3 text-sm font-semibold text-text">按模型汇总</h3>
              <div className="overflow-x-auto rounded-xl border border-border">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-border bg-surface-muted/60 text-text-muted">
                    <tr>
                      <th className="px-3 py-2 font-medium">模型</th>
                      <th className="px-3 py-2 font-medium">总 Token</th>
                      <th className="px-3 py-2 font-medium">输入</th>
                      <th className="px-3 py-2 font-medium">输出</th>
                      <th className="px-3 py-2 font-medium">调用次数</th>
                    </tr>
                  </thead>
                  <tbody>
                    {modelRows.map(([name, row]) => (
                      <tr key={name} className="border-b border-border last:border-0">
                        <td className="px-3 py-2 font-mono text-xs text-text">{name}</td>
                        <td className="px-3 py-2">{formatTokenCount(row.total_tokens || 0)}</td>
                        <td className="px-3 py-2">{formatTokenCount(row.total_input_tokens || 0)}</td>
                        <td className="px-3 py-2">{formatTokenCount(row.total_output_tokens || 0)}</td>
                        <td className="px-3 py-2">{row.total_runs || 0}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}

          <div>
            <div className="mb-3 flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold text-text">按提问汇总</h3>
              <span className="text-xs text-text-muted">最近 {turns.length} 条提问</span>
            </div>

            {turns.length === 0 ? (
              <p className="text-sm text-text-muted">暂无记录。请在 Chat 或 IM 发起对话后再刷新。</p>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-border">
                <table className="w-full min-w-[860px] text-left text-sm">
                  <thead className="border-b border-border bg-surface-muted/60 text-text-muted">
                    <tr>
                      <th className="px-3 py-2 font-medium">时间</th>
                      <th className="px-3 py-2 font-medium">问题摘要</th>
                      <th className="px-3 py-2 font-medium">类型</th>
                      <th className="px-3 py-2 font-medium">LLM 次</th>
                      <th className="px-3 py-2 font-medium">总 Token</th>
                      <th className="px-3 py-2 font-medium">输入</th>
                      <th className="px-3 py-2 font-medium">输出</th>
                      <th className="px-3 py-2 font-medium">模型</th>
                      <th className="px-3 py-2 font-medium">会话</th>
                    </tr>
                  </thead>
                  <tbody>
                    {turns.map((row) => (
                      <tr
                        key={`${row.session_id}-${row.question_preview}-${row.created_at}`}
                        className="border-b border-border last:border-0 align-top"
                      >
                        <td className="px-3 py-2 whitespace-nowrap text-xs text-text-muted">
                          {formatTime(row.created_at)}
                        </td>
                        <td className="px-3 py-2 max-w-[240px] truncate text-text" title={row.question_preview || ""}>
                          {row.question_preview || "—"}
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex flex-wrap gap-1">
                            {(row.callers || []).length
                              ? row.callers.map((c) => (
                                  <Badge key={c} variant="default">
                                    {callerLabel(c)}
                                  </Badge>
                                ))
                              : "—"}
                          </div>
                        </td>
                        <td className="px-3 py-2">{row.llm_call_count}</td>
                        <td className="px-3 py-2 font-medium">{formatTokenCount(row.total_tokens)}</td>
                        <td className="px-3 py-2">{formatTokenCount(row.prompt_tokens)}</td>
                        <td className="px-3 py-2">{formatTokenCount(row.completion_tokens)}</td>
                        <td className="px-3 py-2 font-mono text-xs">{row.model || "—"}</td>
                        <td
                          className="px-3 py-2 font-mono text-[11px] text-text-muted max-w-[140px] truncate"
                          title={row.session_id}
                        >
                          {row.session_id || "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

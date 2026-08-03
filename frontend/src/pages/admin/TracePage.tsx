import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Circle } from "lucide-react";
import { fetchTraceStatus } from "../../api/client";
import type { TraceStatus } from "../../api/types";
import { PageHeader } from "../../components/admin/PageHeader";
import { MetricCard } from "../../components/admin/MetricCard";
import { Badge } from "../../components/ui/Badge";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { SkeletonCard } from "../../components/ui/Skeleton";

export default function TracePage() {
  const { data: trace, isLoading, error } = useQuery({
    queryKey: ["trace-status"],
    queryFn: fetchTraceStatus,
    staleTime: 30_000,
  });

  if (isLoading) {
    return (
      <div className="p-6 max-w-[900px] space-y-4">
        <SkeletonCard rows={2} />
        <SkeletonCard rows={4} />
      </div>
    );
  }

  if (error || !trace) {
    return (
      <div className="p-6">
        <PageHeader title="链路 Trace" description="JSONL + Langfuse 追踪状态" />
        <p className="text-warning text-sm">无法读取 /debug/trace-status，请确认 API 已启动。</p>
      </div>
    );
  }

  const tr = trace as TraceStatus;
  const lfHost = (tr.langfuse_host || "").replace(/\/$/, "");

  return (
    <div className="p-6 max-w-[900px]">
      <PageHeader
        title="链路 Trace"
        description="8010 知识快路径写 JSONL + Langfuse；8011 DeerFlow task/auto 共用 LANGFUSE_*。详见 docs/langfuse-tracing.md"
      />

      <div className="space-y-6">
        <div className="grid grid-cols-3 gap-4">
          <MetricCard
            label="Langfuse"
            value={tr.langfuse_enabled ? "已启用" : "未启用"}
            variant={tr.langfuse_enabled ? "success" : "default"}
          />
          <MetricCard
            label="本地 JSONL"
            value={tr.local_enabled ? "已启用" : "未启用"}
            variant={tr.local_enabled ? "success" : "default"}
          />
          <MetricCard
            label="Trace 活跃"
            value={tr.active ? "是" : "否"}
            variant={tr.active ? "success" : "warning"}
          />
        </div>

        {tr.langfuse_enabled && lfHost ? (
          <p className="text-sm">
            Langfuse UI：{" "}
            <a href={lfHost} target="_blank" rel="noreferrer" className="text-brand underline">
              {lfHost}
            </a>
            {" "}（Traces → 按 Session / User 筛选；单次链接 <code className="text-xs">{lfHost}/trace/&lt;trace_id&gt;</code>）
          </p>
        ) : null}

        {!tr.langfuse_enabled && tr.langfuse_tracing ? (
          <Card>
            <CardHeader>
              <CardTitle>Langfuse 检查项</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-text-muted">
              {[
                { label: "LANGFUSE_TRACING=true", ok: Boolean(tr.langfuse_tracing) },
                { label: "LANGFUSE_PUBLIC_KEY + SECRET_KEY", ok: Boolean(tr.langfuse_configured) },
                { label: "langfuse 包已安装", ok: Boolean(tr.langfuse_package_installed) },
              ].map((item) => (
                <div key={item.label} className="flex items-center gap-2">
                  {item.ok ? (
                    <CheckCircle2 className="h-4 w-4 text-success" aria-label="已完成" />
                  ) : (
                    <Circle className="h-4 w-4 text-text-muted/60" aria-label="未完成" />
                  )}
                  <span className={item.ok ? "text-text" : undefined}>{item.label}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        ) : null}

        <div>
          <h3 className="text-sm font-semibold text-text mb-3">本地 JSONL</h3>
          <p className="text-sm text-text-muted mb-2">
            后端：<code className="text-xs bg-surface-muted px-1.5 py-0.5 rounded">{tr.backend || "off"}</code>
          </p>
          <p className="text-sm text-text-muted mb-2">
            文件：<code className="text-xs bg-surface-muted px-1.5 py-0.5 rounded">{tr.local_path || "—"}</code>
          </p>
          {tr.local_file_exists ? (
            <Badge variant="success">共 {String(tr.local_record_count ?? 0)} 条（Admin 反馈「查看链路」）</Badge>
          ) : (
            <p className="text-xs text-text-muted">开启 LOCAL_TRACE_ENABLED 且产生对话后自动生成。</p>
          )}
        </div>

        {Array.isArray(tr.hints) && tr.hints.length > 0 ? (
          <div>
            <h3 className="text-sm font-semibold text-text mb-2">提示</h3>
            <ul className="list-disc pl-5 text-sm text-text-muted space-y-1">
              {tr.hints.map((h, i) => (
                <li key={i}>{h}</li>
              ))}
            </ul>
          </div>
        ) : null}

        <div>
          <h3 className="text-sm font-semibold text-text mb-2">环境变量（需重启 8010 / 8011）</h3>
          <pre className="p-3 bg-surface-muted rounded-lg text-xs text-text overflow-auto font-mono">
{`LOCAL_TRACE_ENABLED=true

LANGFUSE_TRACING=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
# 本地 SDK: pip install -e D:/LangFuse_python/langfuse-python`}
          </pre>
        </div>
      </div>
    </div>
  );
}

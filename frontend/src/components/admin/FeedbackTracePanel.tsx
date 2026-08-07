import { useState } from "react";
import type { FeedbackTraceView } from "../../lib/traceView";
import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";

type Props = {
  view: FeedbackTraceView;
  raw: Record<string, unknown>;
  onClose: () => void;
};

function DetailGrid({ rows }: { rows: Array<{ label: string; value: string }> }) {
  if (!rows.length) return null;
  return (
    <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
      {rows.map((row) => (
        <div key={row.label} className="contents">
          <dt className="text-text-muted">{row.label}</dt>
          <dd className="text-text break-words">{row.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function FeedbackTracePanel({ view, raw, onClose }: Props) {
  const [showRaw, setShowRaw] = useState(false);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-surface rounded-xl max-w-3xl w-full max-h-[85vh] overflow-hidden flex flex-col shadow-xl">
        <div className="px-4 py-3 border-b border-border flex justify-between items-start gap-3">
          <div>
            <h3 className="font-semibold text-sm text-text">对话链路详情</h3>
            <p className="text-xs text-text-muted mt-0.5">
              追踪 ID：{view.traceId} · 总耗时 {view.durationLabel}
            </p>
          </div>
          <div className="flex gap-2 shrink-0">
            <Button type="button" variant="default" className="text-xs" onClick={() => setShowRaw((v) => !v)}>
              {showRaw ? "结构化视图" : "原始 JSON"}
            </Button>
            <Button type="button" variant="default" onClick={onClose}>
              关闭
            </Button>
          </div>
        </div>

        {showRaw ? (
          <pre className="p-4 text-xs overflow-auto flex-1 font-mono bg-surface-muted">
            {JSON.stringify(raw, null, 2)}
          </pre>
        ) : (
          <div className="p-4 overflow-auto flex-1 space-y-5 text-sm">
            {view.question && (
              <section>
                <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-1">用户问题</h4>
                <p className="text-text bg-surface-muted rounded-lg px-3 py-2 leading-relaxed">{view.question}</p>
              </section>
            )}

            <section>
              <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-2">概览</h4>
              <DetailGrid
                rows={[
                  { label: "开始时间", value: view.startedAt },
                  { label: "结束时间", value: view.endedAt },
                  { label: "回答路径", value: view.answerModeLabel },
                  ...(view.contextCount != null
                    ? [{ label: "检索片段", value: `${view.contextCount} 条` }]
                    : []),
                  ...view.overview,
                ]}
              />
            </section>

            {view.sources.length > 0 && (
              <section>
                <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-2">引用文档</h4>
                <ul className="list-disc pl-5 space-y-0.5 text-text-muted">
                  {view.sources.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </section>
            )}

            <section>
              <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-2">处理步骤</h4>
              {view.spans.length === 0 ? (
                <p className="text-text-muted text-xs">无步骤记录。请确认已开启本地 Trace（LOCAL_TRACE_ENABLED）。</p>
              ) : (
                <ol className="space-y-3 list-none m-0 p-0">
                  {view.spans.map((sp) => (
                    <li key={sp.order} className="rounded-lg border border-border bg-surface px-3 py-2.5">
                      <div className="flex flex-wrap items-center gap-2 mb-1.5">
                        <span className="font-medium text-text">{sp.label}</span>
                        <Badge variant={sp.status === "error" ? "warning" : "success"}>{sp.statusLabel}</Badge>
                        {sp.latencyMs != null && (
                          <span className="text-xs text-text-muted">{sp.latencyMs} ms</span>
                        )}
                      </div>
                      {sp.error && (
                        <p className="text-xs text-warning bg-warning-bg rounded px-2 py-1 mb-1.5">{sp.error}</p>
                      )}
                      <DetailGrid rows={sp.details} />
                    </li>
                  ))}
                </ol>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  );
}

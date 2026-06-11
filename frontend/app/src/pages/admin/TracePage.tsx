import { useQuery } from "@tanstack/react-query";
import { fetchTraceStatus } from "../../api/client";
import type { TraceStatus } from "../../api/types";
import { PageHeader } from "../../components/admin/PageHeader";
import { MetricCard } from "../../components/admin/MetricCard";
import { Badge } from "../../components/ui/Badge";

export default function TracePage() {
  const { data: trace, isLoading, error } = useQuery({
    queryKey: ["trace-status"],
    queryFn: fetchTraceStatus,
    staleTime: 30_000,
  });

  if (isLoading) {
    return <div className="p-6 text-text-muted text-sm">加载中...</div>;
  }

  if (error || !trace) {
    return (
      <div className="p-6">
        <PageHeader
          title="链路 Trace"
          description="LangSmith 与本地 JSONL 追踪状态"
        />
        <p className="text-warning text-sm">无法读取 /debug/trace-status，请确认 API 已启动。</p>
      </div>
    );
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const tr = trace as TraceStatus & { [key: string]: any };

  return (
    <div className="p-6 max-w-[900px]">
      <PageHeader
        title="链路 Trace"
        description="LangSmith：同步 /chat 为 LangGraph；Jnao Chat 流式为 stream_rag_chat。修改 .env 后需重启 API。"
      />

      <div className="space-y-6">
        {/* Metrics */}
        <div className="grid grid-cols-3 gap-4">
          <MetricCard
            label="LangSmith"
            value={tr.langsmith_enabled ? "已启用" : "未启用"}
            variant={tr.langsmith_enabled ? "success" : "default"}
          />
          <MetricCard
            label="本地 JSONL"
            value={(tr.local_trace_enabled || tr.local_enabled) ? "已启用" : "未启用"}
            variant={(tr.local_trace_enabled || tr.local_enabled) ? "success" : "default"}
          />
          <MetricCard
            label="Trace 活跃"
            value={tr.active ? "是" : "否"}
            variant={tr.active ? "success" : "warning"}
          />
        </div>

        {/* LangSmith checks */}
        <div>
          <h3 className="text-sm font-semibold text-text mb-3">LangSmith 检查项</h3>
          <div className="space-y-2">
            {[
              { label: "LANGCHAIN_TRACING_V2=true", ok: Boolean(tr.langsmith_tracing_v2) },
              { label: "LANGCHAIN_API_KEY 已配置", ok: Boolean(tr.langsmith_configured) },
              { label: "langsmith 包已安装", ok: Boolean(tr.langsmith_package_installed) },
            ].map((item) => (
              <div key={item.label} className="flex items-center gap-2 text-sm">
                <span>{item.ok ? "✅" : "⬜"}</span>
                <span className={item.ok ? "text-text" : "text-text-muted"}>{item.label}</span>
              </div>
            ))}
          </div>
          {tr.project && (
            <p className="mt-2 text-sm text-brand bg-brand-light rounded-lg px-3 py-2">
              LangSmith 项目：<code className="text-xs">{String(tr.project)}</code>
            </p>
          )}
        </div>

        {/* Local JSONL */}
        <div>
          <h3 className="text-sm font-semibold text-text mb-3">本地 JSONL</h3>
          <p className="text-sm text-text-muted mb-2">
            文件路径：<code className="text-xs bg-surface-muted px-1.5 py-0.5 rounded">{tr.local_trace_file || tr.local_path || "—"}</code>
          </p>
          {tr.local_file_exists ? (
            <Badge variant="success">
              文件已存在，共 {String(tr.local_trace_lines || tr.local_record_count || 0)} 条记录
            </Badge>
          ) : (
            <p className="text-xs text-text-muted">文件尚未创建（开启本地 trace 且产生对话后会自动生成）。</p>
          )}
        </div>

        {/* Hints */}
        {Array.isArray(tr.hints) && (tr.hints as string[]).length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-text mb-2">待办 / 提示</h3>
            <ul className="list-disc pl-5 text-sm text-text-muted space-y-1">
              {(tr.hints as string[]).map((h, i) => (
                <li key={i}>{h}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Roadmap */}
        <details className="text-sm">
          <summary className="text-text-muted cursor-pointer hover:text-text font-medium">
            演进路线（Agent 全链路追踪）
          </summary>
          <div className="mt-3 p-3 bg-surface-muted rounded-lg text-xs text-text-muted space-y-2">
            <p><strong>目标</strong>：用户自然语言输入 → Agent 规划 → 调工具 → 检索/生成 → 校验 → 输出，全程可回放。</p>
            <table className="w-full border-collapse mt-2">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-1 font-medium">阶段</th>
                  <th className="text-left py-1 font-medium">内容</th>
                  <th className="text-left py-1 font-medium">状态</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-border-light">
                  <td className="py-1">① 基础</td>
                  <td className="py-1">修正路径、状态诊断、LangSmith 可选接入</td>
                  <td className="py-1">✅ 当前</td>
                </tr>
                <tr className="border-b border-border-light">
                  <td className="py-1">② 本地 Span</td>
                  <td className="py-1">每次 /chat/stream 写 JSONL：retrieve / 路由 / 生成 / fallback / 耗时</td>
                  <td className="py-1">✅ 当前</td>
                </tr>
                <tr className="border-b border-border-light">
                  <td className="py-1">③ LangGraph 节点</td>
                  <td className="py-1">为各节点打 Span</td>
                  <td className="py-1">待做</td>
                </tr>
                <tr className="border-b border-border-light">
                  <td className="py-1">④ 工具调用</td>
                  <td className="py-1">入库 Agent、ReAct bind_tools 记录</td>
                  <td className="py-1">待做</td>
                </tr>
                <tr className="border-b border-border-light">
                  <td className="py-1">⑤ 可视化</td>
                  <td className="py-1">管理端 Trace 详情页</td>
                  <td className="py-1">待做</td>
                </tr>
                <tr>
                  <td className="py-1">⑥ 模型思考</td>
                  <td className="py-1">reasoning_content 思维链存档</td>
                  <td className="py-1">待做</td>
                </tr>
              </tbody>
            </table>
          </div>
        </details>

        {/* Env example */}
        <div>
          <h3 className="text-sm font-semibold text-text mb-2">环境变量示例（需重启 API）</h3>
          <pre className="p-3 bg-surface-muted rounded-lg text-xs text-text overflow-auto font-mono">
{`# LangSmith 云端
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_...
LANGCHAIN_PROJECT=enterprise-rag

# 本地 JSONL（/chat/stream 写入）
LOCAL_TRACE_ENABLED=true`}
          </pre>
        </div>
      </div>
    </div>
  );
}

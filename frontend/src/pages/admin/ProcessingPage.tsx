import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchProcessingTools, saveProcessingTools } from "../../api/client";
import type { ProcessingToolsData } from "../../api/types";
import { PageHeader } from "../../components/admin/PageHeader";
import { Button } from "../../components/ui/Button";
import { Switch } from "../../components/ui/Switch";
import { toast } from "sonner";

export default function ProcessingPage() {
  const queryClient = useQueryClient();
  const [useLlmRouter, setUseLlmRouter] = useState(true);
  const [toggles, setToggles] = useState<Record<string, boolean>>({});

  const { data, isLoading, error } = useQuery({
    queryKey: ["processing-tools"],
    queryFn: fetchProcessingTools,
    staleTime: 60_000,
  });

  // Init form state from API data
  useEffect(() => {
    if (data) {
      setUseLlmRouter(Boolean(data.use_hybrid_expert_router));
      const t: Record<string, boolean> = {};
      (data.tools || []).forEach((tool) => {
        t[tool.id] = tool.enabled;
      });
      if (Object.keys(t).length) setToggles(t);
    }
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: (body: ProcessingToolsData) => saveProcessingTools(body),
    onSuccess: () => {
      toast.success("已保存。后续入库将按新配置执行。");
      queryClient.invalidateQueries({ queryKey: ["processing-tools"] });
    },
    onError: (e: Error) => toast.error(e.message || "保存失败"),
  });

  const handleSave = () => {
    const tools = (data?.tools || []).map((t) => ({
      ...t,
      enabled: toggles[t.id] ?? t.enabled,
    }));
    saveMutation.mutate({
      tools,
      use_hybrid_expert_router: useLlmRouter,
    } as ProcessingToolsData);
  };

  if (isLoading) {
    return <div className="p-6 text-text-muted text-sm">加载中...</div>;
  }

  if (error) {
    return (
      <div className="p-6">
        <PageHeader title="工具" description="入库时按文件类型选择解析/清洗工具" />
        <p className="text-error text-sm">无法加载工具配置，请确认 API 已启动。</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-[720px]">
      <PageHeader title="工具" description="入库时按文件类型选择解析/清洗工具；已清洗模式可启用大模型自动选工具。" />

      <div className="space-y-6">
        {/* LLM Router Toggle */}
        <label className="flex items-center gap-3 cursor-pointer select-none">
          <Switch
            checked={useLlmRouter}
            onCheckedChange={setUseLlmRouter}
            id="llm-router"
          />
          <span className="text-sm text-text">启用大模型选工具（LangChain bind_tools）</span>
        </label>

        {/* Tool Toggles */}
        <div>
          <h3 className="text-sm font-semibold text-text mb-3">工具开关</h3>
          <div className="space-y-3">
            {(data?.tools || []).map((tool) => (
              <label
                key={tool.id}
                className="flex items-center gap-3 cursor-pointer select-none"
              >
                <input
                  type="checkbox"
                  checked={toggles[tool.id] ?? tool.enabled}
                  onChange={(e) =>
                    setToggles((prev) => ({ ...prev, [tool.id]: e.target.checked }))
                  }
                  className="w-4 h-4 rounded border-border accent-brand"
                />
                <span className="text-sm text-text">{tool.label}</span>
              </label>
            ))}
          </div>
        </div>

        <Button variant="primary" onClick={handleSave} disabled={saveMutation.isPending}>
          {saveMutation.isPending ? "保存中..." : "保存配置"}
        </Button>

        {/* Extension map */}
        {data?.tools?.length ? (
          <details className="text-sm">
            <summary className="text-text-muted cursor-pointer hover:text-text">
              扩展名 → 解析工具（只读）
            </summary>
            <pre className="mt-2 p-3 bg-surface-muted rounded-lg text-xs text-text-muted overflow-auto">
              {JSON.stringify((data as Record<string, unknown>).extension_map || {}, null, 2)}
            </pre>
          </details>
        ) : null}
      </div>
    </div>
  );
}

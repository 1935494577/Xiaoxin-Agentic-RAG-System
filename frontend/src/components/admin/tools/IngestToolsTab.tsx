import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchProcessingTools, saveProcessingTools } from "../../../api/client";
import type { ProcessingToolsSave } from "../../../api/types";
import { Button } from "../../ui/Button";
import { Switch } from "../../ui/Switch";
import { toast } from "sonner";

export function IngestToolsTab() {
  const queryClient = useQueryClient();
  const [useLlmRouter, setUseLlmRouter] = useState(true);
  const [toggles, setToggles] = useState<Record<string, boolean>>({});

  const { data, isLoading, error } = useQuery({
    queryKey: ["processing-tools"],
    queryFn: fetchProcessingTools,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (data) {
      setUseLlmRouter(Boolean(data.use_llm_router));
      const t: Record<string, boolean> = {};
      (data.tools || []).forEach((tool) => {
        t[tool.id] = tool.enabled;
      });
      if (Object.keys(t).length) setToggles(t);
    }
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: (body: ProcessingToolsSave) => saveProcessingTools(body),
    onSuccess: () => {
      toast.success("已保存。后续入库将按新配置执行。");
      queryClient.invalidateQueries({ queryKey: ["processing-tools"] });
    },
    onError: (e: Error) => toast.error(e.message || "保存失败"),
  });

  const handleSave = () => {
    const toolsPatch: Record<string, { enabled: boolean }> = {};
    for (const t of data?.tools || []) {
      toolsPatch[t.id] = { enabled: toggles[t.id] ?? t.enabled };
    }
    saveMutation.mutate({
      tools: toolsPatch,
      use_llm_router: useLlmRouter,
    });
  };

  if (isLoading) {
    return <p className="text-text-muted text-sm">加载中...</p>;
  }

  if (error) {
    return <p className="text-error text-sm">无法加载入库工具配置，请确认 API 已启动。</p>;
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-text-muted">
        文档入库时按文件类型选择解析/清洗工具；已清洗模式可启用大模型自动选工具。
      </p>

      <label className="flex items-center gap-3 cursor-pointer select-none">
        <Switch checked={useLlmRouter} onCheckedChange={setUseLlmRouter} id="llm-router" />
        <span className="text-sm text-text">启用大模型选工具（LangChain bind_tools）</span>
      </label>

      <div>
        <h3 className="text-sm font-semibold text-text mb-3">工具开关</h3>
        <div className="space-y-3">
          {(data?.tools || []).map((tool) => (
            <label key={tool.id} className="flex items-center gap-3 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={toggles[tool.id] ?? tool.enabled}
                onChange={(e) => setToggles((prev) => ({ ...prev, [tool.id]: e.target.checked }))}
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

      {data?.tools?.length ? (
        <details className="text-sm">
          <summary className="text-text-muted cursor-pointer hover:text-text">
            扩展名 → 解析工具（只读）
          </summary>
          <pre className="mt-2 p-3 bg-surface-muted rounded-lg text-xs text-text-muted overflow-auto">
            {JSON.stringify(data.extension_map || {}, null, 2)}
          </pre>
        </details>
      ) : null}
    </div>
  );
}

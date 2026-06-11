import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchAgentTools, saveAgentTools } from "../../../api/client";
import type { AgentToolsSave } from "../../../api/types";
import { Button } from "../../ui/Button";
import { Switch } from "../../ui/Switch";
import { toast } from "sonner";

export function AgentToolsTab() {
  const queryClient = useQueryClient();
  const [enabled, setEnabled] = useState(true);
  const [toggles, setToggles] = useState<Record<string, boolean>>({});

  const { data, isLoading, error } = useQuery({
    queryKey: ["agent-tools"],
    queryFn: fetchAgentTools,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (data) {
      setEnabled(Boolean(data.chat_tools_enabled));
      const t: Record<string, boolean> = {};
      (data.tools || []).forEach((tool) => {
        t[tool.id] = tool.enabled;
      });
      if (Object.keys(t).length) setToggles(t);
    }
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: (body: AgentToolsSave) => saveAgentTools(body),
    onSuccess: () => {
      toast.success("已保存。对话通用模式下将按新配置调用工具。");
      queryClient.invalidateQueries({ queryKey: ["agent-tools"] });
    },
    onError: (e: Error) => toast.error(e.message || "保存失败"),
  });

  const handleSave = () => {
    const toolsPatch: Record<string, { enabled: boolean }> = {};
    for (const t of data?.tools || []) {
      toolsPatch[t.id] = { enabled: toggles[t.id] ?? t.enabled };
    }
    saveMutation.mutate({
      chat_tools_enabled: enabled,
      tools: toolsPatch,
    });
  };

  if (isLoading) {
    return <p className="text-text-muted text-sm">加载中...</p>;
  }

  if (error) {
    return <p className="text-error text-sm">无法加载对话工具配置，请确认 API 已启动。</p>;
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-text-muted">
        Chat 在<strong className="font-medium text-text">通用回答</strong>
        模式下，模型可调用下列工具（与入库 processing 工具独立）。例如询问「杭州天气怎么样？」会触发天气查询。
      </p>

      <label className="flex items-center gap-3 cursor-pointer select-none">
        <Switch checked={enabled} onCheckedChange={setEnabled} id="chat-tools-master" />
        <span className="text-sm text-text">启用对话工具（function calling）</span>
      </label>

      <div>
        <h3 className="text-sm font-semibold text-text mb-3">可用工具</h3>
        <div className="space-y-4">
          {(data?.tools || []).map((tool) => (
            <div
              key={tool.id}
              className="rounded-lg border border-border bg-surface-muted/40 px-4 py-3"
            >
              <label className="flex items-center gap-3 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={enabled ? (toggles[tool.id] ?? tool.enabled) : false}
                  disabled={!enabled}
                  onChange={(e) =>
                    setToggles((prev) => ({ ...prev, [tool.id]: e.target.checked }))
                  }
                  className="w-4 h-4 rounded border-border accent-brand disabled:opacity-50"
                />
                <span className="text-sm font-medium text-text">{tool.label}</span>
                <span className="text-xs text-text-muted font-mono">{tool.id}</span>
              </label>
              {tool.description ? (
                <p className="mt-2 ml-7 text-xs text-text-muted leading-relaxed">{tool.description}</p>
              ) : null}
            </div>
          ))}
        </div>
      </div>

      <Button variant="primary" onClick={handleSave} disabled={saveMutation.isPending}>
        {saveMutation.isPending ? "保存中..." : "保存配置"}
      </Button>
    </div>
  );
}

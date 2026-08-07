import { useEffect, useMemo } from "react";
import { Maximize2, X } from "lucide-react";
import type { GraphViz } from "../../api/types";
import InteractiveRelationshipGraph from "./InteractiveRelationshipGraph";
import GraphNodeDetailPanel from "./GraphNodeDetailPanel";

type Props = {
  open: boolean;
  onClose: () => void;
  graph: GraphViz;
  selectedNodeId?: string | null;
  onNodeSelect?: (nodeId: string | null) => void;
};

/** 全屏关系图查看：更大画布 + 滚轮缩放。 */
export default function GraphFullscreenViewer({
  open,
  onClose,
  graph,
  selectedNodeId = null,
  onNodeSelect,
}: Props) {
  const centerLabel = useMemo(
    () => graph.nodes.find((n) => n.id === graph.center_id)?.label || "关系图",
    [graph]
  );
  const selectedNode = useMemo(
    () => graph.nodes.find((n) => n.id === selectedNodeId) ?? null,
    [graph.nodes, selectedNodeId]
  );

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      document.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  if (!open) return null;

  const chartHeight = Math.min(Math.max(window.innerHeight - 140, 520), 900);

  return (
    <div className="fixed inset-0 z-[100] flex flex-col bg-black/50 backdrop-blur-[2px]">
      <div
        className="absolute inset-0"
        onClick={onClose}
        aria-hidden
      />
      <div className="relative m-3 sm:m-5 flex flex-col flex-1 min-h-0 rounded-2xl bg-surface shadow-2xl border border-border overflow-hidden">
        <header className="flex items-center justify-between gap-3 px-4 sm:px-5 py-3 border-b border-border shrink-0">
          <div className="min-w-0">
            <h3 className="text-base font-semibold text-text truncate">人物关系网络</h3>
            <p className="text-xs text-text-muted mt-0.5">
              中心：{centerLabel} · {graph.nodes.length} 人 · {graph.edges.length} 条关系
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 p-2 rounded-lg text-text-muted hover:text-text hover:bg-surface-muted cursor-pointer"
            title="关闭 (Esc)"
          >
            <X size={20} />
          </button>
        </header>

        <div className="flex-1 min-h-0 p-3 sm:p-4 overflow-hidden relative">
          <InteractiveRelationshipGraph
            graph={graph}
            height={chartHeight}
            chartKeySuffix="fullscreen"
            scaleMax={5}
            selectedNodeId={selectedNodeId}
            onNodeSelect={onNodeSelect}
          />
          {selectedNode && onNodeSelect && (
            <GraphNodeDetailPanel
              graph={graph}
              node={selectedNode}
              onClose={() => onNodeSelect(null)}
              className="absolute bottom-4 right-4 w-[min(100%,360px)] z-20"
            />
          )}
        </div>

        <footer className="px-4 py-2 border-t border-border text-[11px] text-text-muted text-center shrink-0">
          点击节点看详情 · 拖拽布局 · 滚轮缩放 · Esc 关闭
        </footer>
      </div>
    </div>
  );
}

export function GraphExpandButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-md bg-brand-light text-brand hover:bg-brand/15 cursor-pointer font-medium"
      title="全屏放大查看"
    >
      <Maximize2 size={12} />
      放大查看
    </button>
  );
}

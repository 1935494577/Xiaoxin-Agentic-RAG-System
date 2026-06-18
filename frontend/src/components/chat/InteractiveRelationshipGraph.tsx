import { lazy, Suspense, useMemo } from "react";
import type { GraphViz } from "../../api/types";

const InteractiveChart = lazy(() => import("./InteractiveRelationshipGraphChart"));

type Props = {
  graph: GraphViz;
  height?: number;
  chartKeySuffix?: string;
  onExpandClick?: () => void;
  scaleMax?: number;
};

/** 可拖拽、缩放的关系力导向图（ECharts Graph，按需加载）。 */
export default function InteractiveRelationshipGraph({
  graph,
  height = 420,
  chartKeySuffix = "inline",
  onExpandClick,
  scaleMax = 2.5,
}: Props) {
  const chartKey = useMemo(
    () => `${chartKeySuffix}-${graph.center_id}-${graph.nodes.length}-${graph.edges.length}`,
    [graph, chartKeySuffix]
  );

  if (!graph.nodes.length) {
    return null;
  }

  return (
    <div className="relative w-full rounded-lg overflow-hidden bg-gradient-to-br from-slate-50 to-white border border-border/50 group">
      {onExpandClick && (
        <button
          type="button"
          onClick={onExpandClick}
          className="absolute top-2 left-2 z-10 inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded-md bg-white/90 border border-border/80 text-text-muted hover:text-brand hover:border-brand/40 shadow-sm opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity cursor-pointer"
          title="放大查看"
        >
          点击放大
        </button>
      )}
      <Suspense
        fallback={
          <div
            className="flex items-center justify-center text-sm text-text-muted"
            style={{ height }}
          >
            关系图加载中…
          </div>
        }
      >
        <InteractiveChart graph={graph} height={height} chartKey={chartKey} scaleMax={scaleMax} />
      </Suspense>
      <p className="absolute top-2 right-3 text-[10px] text-text-muted/70 pointer-events-none">
        拖拽节点 · 滚轮缩放 · 按住空白处平移
      </p>
    </div>
  );
}

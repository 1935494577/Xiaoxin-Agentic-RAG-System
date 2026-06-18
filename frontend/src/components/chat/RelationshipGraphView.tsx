import { useMemo, useState } from "react";
import type { GraphViz, GraphVizEdge } from "../../api/types";
import InteractiveRelationshipGraph from "./InteractiveRelationshipGraph";
import GraphFullscreenViewer, { GraphExpandButton } from "./GraphFullscreenViewer";
import GraphNodeDetailPanel from "./GraphNodeDetailPanel";

type Props = {
  graph: GraphViz;
};

function RelationRow({ edge }: { edge: GraphVizEdge }) {
  return (
    <div className="flex items-center gap-2 flex-wrap text-sm py-1.5 px-2 rounded-lg bg-surface-muted/60">
      <span className="font-medium text-text">{edge.from_label}</span>
      <span className="text-[11px] px-2 py-0.5 rounded-full bg-brand-light text-brand font-medium shrink-0">
        {edge.label}
      </span>
      <span className="text-text-muted">→</span>
      <span className="font-medium text-text">{edge.to_label}</span>
    </div>
  );
}

function previewHeight(nodeCount: number): number {
  if (nodeCount > 20) return 520;
  if (nodeCount > 12) return 480;
  return 440;
}

/** 关系图：内联预览 + 全屏放大 + 关系明细。 */
export default function RelationshipGraphView({ graph }: Props) {
  const [fullscreen, setFullscreen] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const selectedNode = useMemo(
    () => graph.nodes.find((n) => n.id === selectedNodeId) ?? null,
    [graph.nodes, selectedNodeId]
  );

  if (!graph.nodes.length) {
    return (
      <p className="text-sm text-text-muted mt-3">暂无关系数据，请先通过关系入库导入人物与关系。</p>
    );
  }

  const openFullscreen = () => setFullscreen(true);

  return (
    <>
      <div className="mt-4 rounded-xl border border-border bg-surface-muted/20 p-3 sm:p-4 space-y-3">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <span className="text-xs font-semibold tracking-wide text-text-muted">人物关系网络</span>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-text-muted">
              {graph.nodes.length} 人 · {graph.edges.length} 条关系
            </span>
            <GraphExpandButton onClick={openFullscreen} />
          </div>
        </div>

        <div className="relative">
          <InteractiveRelationshipGraph
            graph={graph}
            height={previewHeight(graph.nodes.length)}
            onExpandClick={openFullscreen}
            selectedNodeId={selectedNodeId}
            onNodeSelect={setSelectedNodeId}
          />
          {selectedNode && (
            <GraphNodeDetailPanel
              graph={graph}
              node={selectedNode}
              onClose={() => setSelectedNodeId(null)}
              className="absolute bottom-2 left-2 right-2 sm:left-auto sm:right-2 sm:w-[min(100%,320px)] z-20"
            />
          )}
        </div>

        {graph.edges.length > 0 && (
          <details className="group pt-1">
            <summary className="cursor-pointer text-[11px] text-text-muted hover:text-text select-none list-none flex items-center gap-1">
              <span className="group-open:rotate-90 transition-transform inline-block">▸</span>
              查看关系明细列表
            </summary>
            <div className="space-y-1.5 mt-2 max-h-48 overflow-y-auto">
              {graph.edges.map((e, i) => (
                <RelationRow key={`${e.from}-${e.to}-${e.label}-${i}`} edge={e} />
              ))}
            </div>
          </details>
        )}
      </div>

      <GraphFullscreenViewer
        open={fullscreen}
        onClose={() => setFullscreen(false)}
        graph={graph}
        selectedNodeId={selectedNodeId}
        onNodeSelect={setSelectedNodeId}
      />
    </>
  );
}

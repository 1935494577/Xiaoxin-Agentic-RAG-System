import { X } from "lucide-react";
import type { GraphViz, GraphVizNode } from "../../api/types";
import { getNodeRelations } from "../../lib/graphViz";

type Props = {
  graph: GraphViz;
  node: GraphVizNode;
  onClose: () => void;
  className?: string;
};

function RelationTags({ label, names }: { label: string; names: string[] }) {
  if (!names.length) return null;
  return (
    <div className="space-y-1">
      <p className="text-[10px] font-medium text-text-muted uppercase tracking-wide">{label}</p>
      <div className="flex flex-wrap gap-1">
        {names.map((name) => (
          <span
            key={name}
            className="text-[11px] px-2 py-0.5 rounded-full bg-surface-muted text-text border border-border/60"
          >
            {name}
          </span>
        ))}
      </div>
    </div>
  );
}

/** 节点详情：职责 bio + 汇报/管辖关系（点击图节点打开）。 */
export default function GraphNodeDetailPanel({ graph, node, onClose, className = "" }: Props) {
  const rel = getNodeRelations(graph, node.id);
  const hasRelations =
    rel.reportsTo.length ||
    rel.directReports.length ||
    rel.manages.length ||
    rel.managedBy.length ||
    rel.dottedReports.length ||
    rel.dottedManages.length ||
    rel.dottedManagedBy.length ||
    rel.dottedDirectReports.length ||
    rel.dottedGuides.length ||
    rel.collaborations.length;

  return (
    <div
      className={`rounded-xl border border-border bg-white/95 backdrop-blur-sm shadow-lg p-3 sm:p-4 space-y-3 max-h-[min(320px,45vh)] overflow-y-auto ${className}`}
      role="dialog"
      aria-label={`${node.label} 详情`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h4 className="text-sm font-semibold text-text truncate">{node.label}</h4>
          {(node.title || node.department) && (
            <p className="text-xs text-text-muted mt-0.5">
              {[node.title, node.department].filter(Boolean).join(" · ")}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={onClose}
          className="shrink-0 p-1 rounded-md text-text-muted hover:text-text hover:bg-surface-muted cursor-pointer"
          title="关闭详情"
        >
          <X size={16} />
        </button>
      </div>

      {node.bio ? (
        <div>
          <p className="text-[10px] font-medium text-text-muted uppercase tracking-wide mb-1">
            职责 / 负责范围
          </p>
          <p className="text-xs text-text leading-relaxed whitespace-pre-wrap">{node.bio}</p>
        </div>
      ) : (
        <p className="text-xs text-text-muted italic">暂无职责描述（可在关系入库文档中补充「负责…」等内容）</p>
      )}

      {hasRelations && (
        <div className="space-y-2 pt-1 border-t border-border/60">
          <RelationTags label="汇报给" names={rel.reportsTo} />
          <RelationTags label="直接下属" names={rel.directReports} />
          <RelationTags label="管辖" names={rel.manages} />
          <RelationTags label="上级管辖" names={rel.managedBy} />
          <RelationTags label="虚线汇报" names={rel.dottedReports} />
          <RelationTags label="虚线管辖" names={rel.dottedManages} />
          <RelationTags label="虚线管辖方" names={rel.dottedManagedBy} />
          <RelationTags label="虚线汇报下属" names={rel.dottedDirectReports} />
          <RelationTags label="虚线指导" names={rel.dottedGuides} />
          <RelationTags label="协作" names={rel.collaborations} />
        </div>
      )}
    </div>
  );
}

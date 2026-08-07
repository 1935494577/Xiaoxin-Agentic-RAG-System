import { useState } from "react";
import { ExamPaperCard } from "./ExamPaperCard";
import type { ExamCandidateItem } from "../../lib/examPaperBlocks";

type Props = {
  items: ExamCandidateItem[];
};

export function ExamCandidateList({ items }: Props) {
  const [selectedId, setSelectedId] = useState<string>("");
  const selected = items.find((x) => x.id === selectedId);

  if (!items.length) return null;

  return (
    <div className="mt-3 rounded-xl border border-border bg-surface overflow-hidden" data-testid="exam-candidates">
      <div className="px-3 py-2 border-b border-border bg-surface-muted/40">
        <p className="text-xs font-medium text-text">题库检索到多份试卷，请选择一份开始作答</p>
      </div>
      <ul className="divide-y divide-border-light">
        {items.map((it) => {
          const active = selectedId === it.id;
          return (
            <li key={it.id}>
              <button
                type="button"
                onClick={() => setSelectedId(it.id)}
                className={[
                  "w-full text-left px-3 py-2.5 text-sm cursor-pointer transition-colors",
                  active ? "bg-brand/5" : "hover:bg-surface-muted/60",
                ].join(" ")}
              >
                <span className="font-medium text-text">{it.title || it.id}</span>
                <span className="block text-[11px] text-text-muted mt-0.5">
                  {it.question_count != null ? `${it.question_count} 题` : ""}
                  {it.source_filename ? ` · ${it.source_filename}` : ""}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      {selected ? (
        <div className="px-2 pb-2">
          <ExamPaperCard sourcePaperId={selected.id} titleHint={selected.title} />
        </div>
      ) : null}
    </div>
  );
}

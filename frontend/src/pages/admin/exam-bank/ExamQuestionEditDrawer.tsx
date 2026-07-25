import { useEffect, useState } from "react";
import type { ExamQuestion } from "../../../lib/examBank";
import { updateExamQuestion } from "../../../lib/examBank";
import { ExamMathText } from "./ExamMathText";

type Props = {
  question: ExamQuestion | null;
  qtypeLabel: (id: string) => string;
  onClose: () => void;
  onSaved: (q: ExamQuestion) => void;
};

/** Side drawer to edit stem / options / answer without leaving assemble view. */
export function ExamQuestionEditDrawer({ question, qtypeLabel, onClose, onSaved }: Props) {
  const [stem, setStem] = useState("");
  const [optionsText, setOptionsText] = useState("");
  const [answer, setAnswer] = useState("");
  const [analysis, setAnalysis] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!question) return;
    setStem(question.stem || "");
    setOptionsText((question.options || []).join("\n"));
    setAnswer(question.answer || "");
    setAnalysis(question.analysis || "");
    setErr("");
  }, [question]);

  if (!question) return null;

  const save = async () => {
    setBusy(true);
    setErr("");
    try {
      const options = optionsText
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean);
      const updated = await updateExamQuestion(question.id, {
        stem: stem.trim(),
        options,
        answer: answer.trim(),
        analysis: analysis.trim(),
      });
      onSaved(updated);
      onClose();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] flex justify-end bg-black/40" onClick={onClose}>
      <div
        className="h-full w-full max-w-lg bg-surface border-l-2 border-border shadow-xl flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-2 px-4 py-3 border-b border-border">
          <div>
            <p className="text-sm font-semibold text-text">编辑题目</p>
            <p className="text-[11px] text-text-muted">
              {qtypeLabel(question.qtype)} · 保留 [[EQ:n]] 与公式图关联
            </p>
          </div>
          <button type="button" className="rounded-md border px-2.5 py-1 text-xs" onClick={onClose}>
            关闭
          </button>
        </div>
        <div className="flex-1 overflow-auto px-4 py-3 space-y-3 text-sm">
          <label className="block space-y-1">
            <span className="text-xs text-text-muted">题干</span>
            <textarea
              className="w-full min-h-[100px] rounded-md border border-border bg-surface px-2 py-1.5"
              value={stem}
              onChange={(e) => setStem(e.target.value)}
            />
          </label>
          <div className="rounded-md border border-dashed border-border px-2 py-2 text-xs">
            <p className="text-text-muted mb-1">预览</p>
            <ExamMathText text={stem} mediaIngestId={question.media_ingest_id} />
          </div>
          <label className="block space-y-1">
            <span className="text-xs text-text-muted">选项（每行一项，可含 A. / B.）</span>
            <textarea
              className="w-full min-h-[80px] rounded-md border border-border bg-surface px-2 py-1.5 font-mono text-xs"
              value={optionsText}
              onChange={(e) => setOptionsText(e.target.value)}
            />
          </label>
          <label className="block space-y-1">
            <span className="text-xs text-text-muted">答案</span>
            <textarea
              className="w-full min-h-[48px] rounded-md border border-border bg-surface px-2 py-1.5"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
            />
          </label>
          <label className="block space-y-1">
            <span className="text-xs text-text-muted">解析</span>
            <textarea
              className="w-full min-h-[64px] rounded-md border border-border bg-surface px-2 py-1.5"
              value={analysis}
              onChange={(e) => setAnalysis(e.target.value)}
            />
          </label>
          {err ? <p className="text-xs text-warning whitespace-pre-wrap">{err}</p> : null}
        </div>
        <div className="border-t border-border px-4 py-3 flex justify-end gap-2">
          <button type="button" className="rounded-md border px-3 py-1.5 text-xs" onClick={onClose}>
            取消
          </button>
          <button
            type="button"
            disabled={busy || !stem.trim()}
            className="rounded-md bg-brand text-white px-3 py-1.5 text-xs font-medium disabled:opacity-50"
            onClick={() => void save()}
          >
            {busy ? "保存中…" : "保存"}
          </button>
        </div>
      </div>
    </div>
  );
}

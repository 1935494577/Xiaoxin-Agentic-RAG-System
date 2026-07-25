import { useState } from "react";
import type { ExamQuestion } from "../../../lib/examBank";
import { ExamMathText } from "./ExamMathText";

const DIFF_LABEL: Record<number, string> = {
  1: "容易",
  2: "容易",
  3: "适中",
  4: "困难",
  5: "困难",
};

function diffScore(d: number, coef?: number): string {
  if (typeof coef === "number" && coef > 0) return coef.toFixed(2);
  const map: Record<number, string> = { 1: "0.95", 2: "0.85", 3: "0.65", 4: "0.45", 5: "0.25" };
  return map[d] || "0.65";
}

export function ExamQuestionCard({
  q,
  index,
  qtypeLabel,
  inBasket,
  onToggleBasket,
  sourceTitle,
  onOpenSource,
  onEdit,
  onSwap,
  swapBusy,
}: {
  q: ExamQuestion;
  index: number;
  qtypeLabel: (id: string) => string;
  inBasket: boolean;
  onToggleBasket: () => void;
  sourceTitle?: string;
  onOpenSource?: () => void;
  onEdit?: () => void;
  onSwap?: () => void;
  swapBusy?: boolean;
}) {
  const [showAns, setShowAns] = useState(false);
  const d = Number(q.difficulty || 3);
  const metaBits = [q.year || "", q.region || "", q.chapter || ""].filter(Boolean);

  return (
    <article
      className="rounded-lg border-2 border-border bg-surface px-4 py-3 space-y-2 hover:border-brand/50 transition-colors cursor-pointer"
      onClick={() => onEdit?.()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onEdit?.();
        }
      }}
      role={onEdit ? "button" : undefined}
      tabIndex={onEdit ? 0 : undefined}
      title={onEdit ? "点击编辑本题" : undefined}
    >
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {metaBits.length ? (
          <span className="rounded bg-brand/10 px-2 py-0.5 text-brand font-medium">
            {metaBits.join("·")}
          </span>
        ) : null}
        <span className="text-text-muted">{qtypeLabel(q.qtype)}</span>
        <span className="text-text-muted">
          {DIFF_LABEL[d] || "适中"} ({diffScore(d, q.difficulty_coef)})
        </span>
        <span className="ml-auto text-text-muted">#{index + 1}</span>
      </div>

      <div className="text-sm text-text leading-relaxed">
        <span className="font-medium mr-1">{index + 1}.</span>
        <ExamMathText text={q.stem} mediaIngestId={q.media_ingest_id} />
      </div>
      {(q.options || []).length > 0 ? (
        <ul className="grid gap-1 sm:grid-cols-2 text-sm text-text">
          {q.options.map((o) => (
            <li key={o}>
              <ExamMathText text={o} mediaIngestId={q.media_ingest_id} />
            </li>
          ))}
        </ul>
      ) : null}

      {showAns ? (
        <div className="rounded-md bg-surface-muted/50 border border-border px-3 py-2 text-xs space-y-1">
          {q.answer ? (
            <p>
              <span className="font-semibold text-brand">【答案】</span>
              <ExamMathText text={q.answer} mediaIngestId={q.media_ingest_id} />
            </p>
          ) : (
            <p className="text-text-muted">暂无答案</p>
          )}
          {q.analysis ? (
            <p>
              <span className="font-semibold text-brand">【解析】</span>
              <ExamMathText text={q.analysis} mediaIngestId={q.media_ingest_id} />
            </p>
          ) : null}
          {(q.knowledge_tags || []).length ? (
            <p className="text-text-muted">知识点：{(q.knowledge_tags || []).join("、")}</p>
          ) : null}
        </div>
      ) : null}

      <div
        className="flex flex-wrap items-center gap-3 pt-1 text-xs border-t border-border/60"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          className="text-text-muted hover:text-brand"
          onClick={() => setShowAns((v) => !v)}
        >
          {showAns ? "收起答案" : "查看答案/解析"}
        </button>
        {onEdit ? (
          <button type="button" className="text-text-muted hover:text-brand" onClick={onEdit}>
            编辑
          </button>
        ) : null}
        {onSwap ? (
          <button
            type="button"
            className="text-text-muted hover:text-brand disabled:opacity-50"
            disabled={swapBusy}
            onClick={onSwap}
          >
            {swapBusy ? "换题中…" : "智能换题"}
          </button>
        ) : null}
        {q.source_paper_id ? (
          <button
            type="button"
            className="text-brand hover:underline"
            onClick={onOpenSource}
            title={sourceTitle || "来源试卷"}
          >
            {sourceTitle ? `原卷：${sourceTitle}` : "查看原题试卷"}
          </button>
        ) : (
          <span className="text-text-muted">无来源卷关联</span>
        )}
        <button
          type="button"
          className={`ml-auto rounded-md border-2 px-2.5 py-1 font-medium ${
            inBasket
              ? "border-brand text-brand bg-brand/5"
              : "border-brand bg-brand text-white"
          }`}
          onClick={onToggleBasket}
        >
          {inBasket ? "移出试题篮" : "加入试题篮"}
        </button>
      </div>
    </article>
  );
}

export function ExamBasketPanel({
  items,
  qtypeLabel,
  onRemove,
  onClear,
  onFinalize,
  finalizeBusy,
  totalInPool,
}: {
  items: ExamQuestion[];
  qtypeLabel: (id: string) => string;
  onRemove: (id: string) => void;
  onClear: () => void;
  onFinalize: () => void;
  finalizeBusy?: boolean;
  totalInPool: number;
}) {
  const byType = items.reduce<Record<string, number>>((acc, q) => {
    const k = q.qtype || "other";
    acc[k] = (acc[k] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="rounded-xl border-2 border-border bg-surface shadow-sm flex flex-col max-h-[640px]">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border">
        <p className="text-sm font-semibold text-text">
          试题篮 <span className="text-text-muted font-normal">共 {items.length} 道</span>
        </p>
        <button type="button" className="text-xs text-text-muted hover:text-brand" onClick={onClear}>
          清空
        </button>
      </div>
      <div className="px-3 py-1.5 text-[11px] text-text-muted border-b border-border flex flex-wrap gap-2">
        {Object.entries(byType).map(([qt, n]) => (
          <span key={qt}>
            {qtypeLabel(qt)} {n}
          </span>
        ))}
        {!items.length ? <span>从左侧题卡加入，或一键组卷后自动装入</span> : null}
      </div>
      <ul className="flex-1 overflow-auto px-2 py-2 space-y-1.5">
        {items.map((q, i) => (
          <li
            key={q.id}
            className="flex gap-2 rounded-lg border border-border px-2 py-1.5 text-xs"
          >
            <span className="text-text-muted shrink-0">{i + 1}.</span>
            <span className="flex-1 line-clamp-2 text-text">
              <ExamMathText text={q.stem} mediaIngestId={q.media_ingest_id} />
            </span>
            <button
              type="button"
              className="text-text-muted hover:text-warning shrink-0"
              onClick={() => onRemove(q.id)}
              aria-label="移除"
            >
              ×
            </button>
          </li>
        ))}
      </ul>
      <div className="border-t border-border px-3 py-2 space-y-2">
        <p className="text-[11px] text-text-muted">
          候选池 {totalInPool} 题 · 已选 {items.length}
        </p>
        <button
          type="button"
          disabled={!items.length || finalizeBusy}
          className="w-full rounded-lg bg-brand text-white text-sm font-medium py-2 disabled:opacity-50"
          onClick={onFinalize}
        >
          {finalizeBusy ? "生成中…" : "去组卷并导出"}
        </button>
      </div>
    </div>
  );
}

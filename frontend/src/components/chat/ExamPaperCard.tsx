import { useCallback, useEffect, useMemo, useState } from "react";
import { ExamMathText } from "../../pages/admin/exam-bank/ExamMathText";
import {
  fetchChatExamPaper,
  startChatExamAttempt,
  submitChatExamAttempt,
  type ChatAttemptSubmit,
  type ChatExamPaper,
  type ChatPaperItem,
} from "../../lib/examBank";
import { useAuth } from "../../hooks/useAuth";

type Props = {
  sourcePaperId: string;
  /** Optional preloaded title while fetching */
  titleHint?: string;
};

type Phase = "loading" | "preview" | "answering" | "submitted" | "error";

function optionLetter(opt: string, index: number): string {
  const m = /^\s*([A-Da-d])[.\s、．]/.exec(opt);
  if (m) return m[1].toUpperCase();
  return String.fromCharCode(65 + index);
}

function QuestionBlock({
  item,
  index,
  mediaIngestId,
  phase,
  value,
  onChange,
  result,
}: {
  item: ChatPaperItem;
  index: number;
  mediaIngestId?: string;
  phase: Phase;
  value: string;
  onChange: (v: string) => void;
  result?: ChatAttemptSubmit["results"][number];
}) {
  const no = item.no || String(index + 1);
  const mid = item.media_ingest_id || mediaIngestId;
  const answering = phase === "answering";
  const reviewed = phase === "submitted";

  return (
    <div className="py-3 border-b border-border-light last:border-0">
      <div className="text-[15px] leading-7 text-text mb-2">
        <span className="font-medium mr-1">{no}.</span>
        <ExamMathText text={item.stem} mediaIngestId={mid} />
        {item.score ? (
          <span className="text-xs text-text-muted ml-1">（{item.score}分）</span>
        ) : null}
      </div>
      {item.options?.length ? (
        <div className="space-y-1.5 pl-1">
          {item.options.map((opt, oi) => {
            const letter = optionLetter(opt, oi);
            const selected = value.toUpperCase() === letter;
            const isCorrect = reviewed && result?.correct === true && selected;
            const isWrong = reviewed && result?.correct === false && selected;
            return (
              <label
                key={`${item.id}-${oi}`}
                className={[
                  "flex items-start gap-2 rounded-md px-2 py-1.5 text-sm cursor-pointer",
                  answering ? "hover:bg-surface-muted/80" : "",
                  selected && answering ? "bg-brand/5 ring-1 ring-brand/30" : "",
                  isCorrect ? "bg-emerald-50 ring-1 ring-emerald-300" : "",
                  isWrong ? "bg-red-50 ring-1 ring-red-300" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                {answering ? (
                  <input
                    type="radio"
                    className="mt-1"
                    name={`q-${item.id}`}
                    checked={selected}
                    onChange={() => onChange(letter)}
                  />
                ) : (
                  <span className="w-4 shrink-0 text-text-muted">{letter}.</span>
                )}
                <span className="leading-6">
                  <ExamMathText text={opt.replace(/^\s*[A-Da-d][.\s、．]\s*/, "")} mediaIngestId={mid} />
                </span>
              </label>
            );
          })}
        </div>
      ) : answering || reviewed ? (
        <input
          type="text"
          className="mt-1 w-full max-w-md border border-border rounded-md px-2.5 py-1.5 text-sm bg-white"
          placeholder="填写答案"
          value={value}
          disabled={!answering}
          onChange={(e) => onChange(e.target.value)}
        />
      ) : null}
      {reviewed && result ? (
        <div className="mt-2 text-xs space-y-1 text-text-muted">
          <p>
            {result.scored ? (
              result.correct ? (
                <span className="text-emerald-700">回答正确</span>
              ) : (
                <span className="text-red-700">回答错误</span>
              )
            ) : (
              <span>主观题未自动判分</span>
            )}
            {result.answer ? (
              <>
                {" · 参考答案："}
                <ExamMathText text={result.answer} className="inline" mediaIngestId={mid} />
              </>
            ) : null}
          </p>
          {result.analysis ? (
            <p className="leading-5">
              解析：
              <ExamMathText text={result.analysis} className="inline" mediaIngestId={mid} />
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function ExamPaperCard({ sourcePaperId, titleHint }: Props) {
  const { userId } = useAuth();
  const [phase, setPhase] = useState<Phase>("loading");
  const [error, setError] = useState("");
  const [paper, setPaper] = useState<ChatExamPaper | null>(null);
  const [attemptId, setAttemptId] = useState("");
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitResult, setSubmitResult] = useState<ChatAttemptSubmit | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setPhase("loading");
    setError("");
    void (async () => {
      try {
        const p = await fetchChatExamPaper(sourcePaperId, false);
        if (cancelled) return;
        setPaper(p);
        setPhase("preview");
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "加载试卷失败");
        setPhase("error");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sourcePaperId]);

  const flatItems = useMemo(() => {
    const items: ChatPaperItem[] = [];
    for (const sec of paper?.sections || []) {
      items.push(...(sec.items || []));
    }
    return items;
  }, [paper]);

  const resultById = useMemo(() => {
    const m = new Map<string, ChatAttemptSubmit["results"][number]>();
    for (const r of submitResult?.results || []) {
      m.set(r.question_id, r);
    }
    return m;
  }, [submitResult]);

  const onStart = useCallback(async () => {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const res = await startChatExamAttempt(sourcePaperId, userId || "");
      setAttemptId(res.attempt_id);
      if (res.paper) setPaper(res.paper);
      setAnswers({});
      setSubmitResult(null);
      setPhase("answering");
    } catch (e) {
      setError(e instanceof Error ? e.message : "无法开始答题");
    } finally {
      setBusy(false);
    }
  }, [busy, sourcePaperId, userId]);

  const onSubmit = useCallback(async () => {
    if (!attemptId || busy) return;
    setBusy(true);
    setError("");
    try {
      const res = await submitChatExamAttempt(attemptId, answers);
      setSubmitResult(res);
      setPhase("submitted");
    } catch (e) {
      setError(e instanceof Error ? e.message : "交卷失败");
    } finally {
      setBusy(false);
    }
  }, [attemptId, answers, busy]);

  if (phase === "loading") {
    return (
      <div className="mt-3 rounded-xl border border-border bg-white p-4 text-sm text-text-muted animate-pulse">
        正在加载标准卷面…
      </div>
    );
  }

  if (phase === "error" || !paper) {
    return (
      <div className="mt-3 rounded-xl border border-dashed border-warning/50 bg-warning/5 p-4 text-sm text-warning">
        {error || titleHint || "试卷不可用（请确认已题库入库）"}
      </div>
    );
  }

  const mediaId = paper.media_ingest_id;

  return (
    <div className="mt-3 rounded-xl border border-border bg-[#fbfaf7] shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-border bg-white">
        <h3 className="text-base font-semibold text-text tracking-tight text-center">
          {paper.title || titleHint || "试卷"}
        </h3>
        <p className="mt-1 text-center text-xs text-text-muted">
          满分 {paper.meta.total_score} 分 · 共 {paper.meta.question_count} 题
          {paper.meta.duration_min ? ` · 建议用时 ${paper.meta.duration_min} 分钟` : ""}
        </p>
        <p className="mt-2 text-center text-xs text-text-muted">
          姓名__________　班级__________　考号__________
        </p>
      </div>

      <div className="px-4 py-2 max-h-[min(70vh,640px)] overflow-y-auto">
        {paper.sections.map((sec) => (
          <section key={sec.heading} className="mb-2">
            <h4 className="text-sm font-semibold text-text mt-3 mb-1">{sec.heading}</h4>
            {sec.items.map((item, idx) => {
              const globalIndex = flatItems.findIndex((x) => x.id === item.id);
              return (
                <QuestionBlock
                  key={item.id}
                  item={item}
                  index={globalIndex >= 0 ? globalIndex : idx}
                  mediaIngestId={mediaId}
                  phase={phase}
                  value={answers[item.id] || ""}
                  onChange={(v) => setAnswers((prev) => ({ ...prev, [item.id]: v }))}
                  result={resultById.get(item.id)}
                />
              );
            })}
          </section>
        ))}
      </div>

      <div className="px-4 py-3 border-t border-border bg-white flex flex-wrap items-center gap-2">
        {phase === "preview" ? (
          <button
            type="button"
            onClick={() => void onStart()}
            disabled={busy}
            className="text-sm px-3.5 py-1.5 rounded-md bg-brand text-white hover:bg-brand-dark disabled:opacity-50 cursor-pointer"
          >
            {busy ? "准备中…" : "开始答题"}
          </button>
        ) : null}
        {phase === "answering" ? (
          <>
            <button
              type="button"
              onClick={() => void onSubmit()}
              disabled={busy}
              className="text-sm px-3.5 py-1.5 rounded-md bg-brand text-white hover:bg-brand-dark disabled:opacity-50 cursor-pointer"
            >
              {busy ? "交卷中…" : "交卷"}
            </button>
            <span className="text-xs text-text-muted">
              已答 {Object.values(answers).filter((v) => v.trim()).length}/{flatItems.length}
            </span>
          </>
        ) : null}
        {phase === "submitted" && submitResult ? (
          <p className="text-sm text-text">
            客观题得分{" "}
            <strong>
              {submitResult.score}/{submitResult.max_score}
            </strong>
            （正确 {submitResult.correct_count}/{submitResult.graded_count}）
          </p>
        ) : null}
        {error ? <span className="text-xs text-warning">{error}</span> : null}
      </div>
    </div>
  );
}

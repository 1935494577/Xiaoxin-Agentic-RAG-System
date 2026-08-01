import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "../../../components/ui/Button";
import { useAuth } from "../../../context/AuthContext";
import {
  deleteExamCollection,
  fetchExamCollections,
  fetchExamQuestions,
  formatExamApiError,
  llmCompleteExamCollectionIncomplete,
  llmCompleteExamQuestion,
} from "../../../lib/examBank";
import { loadExamWizardDraft, saveExamWizardDraft } from "../../../lib/examWizardStore";
import { ExamMathText } from "./ExamMathText";
import { ExamField, ExamWizardChrome, examControlClass } from "./ExamWizardChrome";

const REASON_LABEL: Record<string, string> = {
  options: "缺选项",
  answer: "缺答案",
  stem: "题干过短",
};

export default function ExamBankManagePage() {
  const { session } = useAuth();
  const userId = session?.userId || session?.username || "";
  const qc = useQueryClient();
  const nav = useNavigate();
  const [error, setError] = useState("");
  const [hint, setHint] = useState("");
  const [activeId, setActiveId] = useState("");
  const [searchQ, setSearchQ] = useState("");
  const [committedQ, setCommittedQ] = useState("");
  const [onlyIncomplete, setOnlyIncomplete] = useState(false);

  const colsQ = useQuery({
    queryKey: ["exam-collections-manage", userId],
    queryFn: () => fetchExamCollections(),
  });

  const questionsQ = useQuery({
    queryKey: ["exam-questions-search", activeId, committedQ, onlyIncomplete],
    queryFn: () =>
      fetchExamQuestions(activeId, {
        status: "all",
        q: committedQ || undefined,
        completeness: onlyIncomplete ? "incomplete" : undefined,
        limit: 200,
      }),
    enabled: Boolean(activeId),
  });

  const del = useMutation({
    mutationFn: (id: string) => deleteExamCollection(id),
    onSuccess: (_body, id) => {
      const d = loadExamWizardDraft(userId);
      if (d.collectionId === id) {
        saveExamWizardDraft(userId, {
          ...d,
          collectionId: "",
          collectionName: "",
          region: "",
          sourcePaperId: "",
        });
      }
      if (activeId === id) setActiveId("");
      void qc.invalidateQueries({ queryKey: ["exam-collections"] });
      void qc.invalidateQueries({ queryKey: ["exam-collections-manage"] });
    },
    onError: (e: Error) => setError(formatExamApiError(e.message)),
  });

  const completeOne = useMutation({
    mutationFn: (qid: string) => llmCompleteExamQuestion(qid),
    onSuccess: (body) => {
      setError("");
      setHint(
        body.skipped
          ? "该题已完整，无需补全"
          : `已补全：${(body.updated_fields || []).join("、") || "字段"}`,
      );
      void qc.invalidateQueries({ queryKey: ["exam-questions-search", activeId] });
    },
    onError: (e: Error) => setError(formatExamApiError(e.message)),
  });

  const completeBatch = useMutation({
    mutationFn: (cid: string) => llmCompleteExamCollectionIncomplete(cid, { limit: 10 }),
    onSuccess: (body) => {
      setError("");
      setHint(
        `批量补全：尝试 ${body.attempted} · 成功 ${body.updated} · 失败 ${body.failed}`,
      );
      void qc.invalidateQueries({ queryKey: ["exam-questions-search", activeId] });
    },
    onError: (e: Error) => setError(formatExamApiError(e.message)),
  });

  return (
    <ExamWizardChrome title="题库管理">
      {error ? <p className="text-sm text-warning whitespace-pre-wrap">{error}</p> : null}
      {hint ? <p className="text-sm text-brand">{hint}</p> : null}
      <ul className="space-y-3">
        {(colsQ.data?.items || []).map((c) => (
          <li
            key={c.id}
            className={`rounded-xl border-2 bg-surface px-4 py-3 space-y-2 ${
              activeId === c.id ? "border-brand" : "border-border"
            }`}
          >
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                className="flex-1 min-w-[12rem] text-left"
                onClick={() => {
                  setActiveId(c.id);
                  setCommittedQ("");
                  setSearchQ("");
                  setOnlyIncomplete(false);
                  setHint("");
                }}
              >
                <p className="text-sm font-medium text-text">{c.name}</p>
                <p className="text-xs text-text-muted">
                  {c.subject} · {c.grade}
                  {c.region ? ` · ${c.region}` : ""} · {c.visibility || "private"}
                </p>
              </button>
              <button
                type="button"
                className="text-sm text-brand hover:underline"
                onClick={() => {
                  const d = loadExamWizardDraft(userId);
                  saveExamWizardDraft(userId, {
                    ...d,
                    subject: c.subject || d.subject,
                    grade: c.grade || d.grade,
                    region: c.region || "",
                    collectionId: c.id,
                    collectionName: c.name,
                    visibility: c.visibility || "private",
                    step: 3,
                  });
                  nav("/admin/exam-bank/ingest?step=2");
                }}
              >
                继续入库
              </button>
              <Link
                to={`/admin/exam-bank/assemble?collection=${encodeURIComponent(c.id)}`}
                className="text-sm text-brand hover:underline"
              >
                组卷
              </Link>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => {
                  if (window.confirm(`删除题库「${c.name}」及其全部题目？`)) del.mutate(c.id);
                }}
              >
                删除
              </Button>
            </div>

            {activeId === c.id ? (
              <div className="border-t border-border pt-3 space-y-3">
                <div className="flex flex-col sm:flex-row gap-2 sm:items-end">
                  <ExamField label="检索题干 / 知识点" className="flex-1">
                    <input
                      className={examControlClass}
                      value={searchQ}
                      placeholder="如：集合、导数"
                      onChange={(e) => setSearchQ(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") setCommittedQ(searchQ.trim());
                      }}
                    />
                  </ExamField>
                  <div className="flex flex-wrap gap-2 items-center">
                    <Button type="button" size="sm" onClick={() => setCommittedQ(searchQ.trim())}>
                      搜索
                    </Button>
                    <label className="flex items-center gap-1.5 text-xs text-text-muted cursor-pointer">
                      <input
                        type="checkbox"
                        checked={onlyIncomplete}
                        onChange={(e) => setOnlyIncomplete(e.target.checked)}
                      />
                      仅待补全
                    </label>
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      disabled={completeBatch.isPending}
                      onClick={() => {
                        setHint("正在批量补全（最多 10 题）…");
                        completeBatch.mutate(c.id);
                      }}
                    >
                      {completeBatch.isPending ? "补全中…" : "一键 LLM 补全"}
                    </Button>
                  </div>
                </div>
                <p className="text-xs text-text-muted">
                  共 {questionsQ.data?.total ?? "…"} 题
                  {committedQ ? ` · 关键词「${committedQ}」` : ""}
                  {onlyIncomplete ? " · 待补全" : ""}
                </p>
                <ul className="max-h-64 overflow-auto space-y-2 text-sm">
                  {(questionsQ.data?.items || []).map((q) => (
                    <li key={q.id} className="rounded-lg border border-border px-3 py-2 space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-xs text-text-muted">
                          {q.qtype} · 难度 {q.difficulty}
                          {(q.knowledge_tags || []).length
                            ? ` · ${(q.knowledge_tags || []).join("、")}`
                            : ""}
                        </p>
                        {q.incomplete ? (
                          <span className="rounded bg-warning/15 px-1.5 py-0.5 text-[10px] text-warning">
                            待补全
                            {(q.incomplete_reasons || [])
                              .map((r) => REASON_LABEL[r] || r)
                              .join("·")}
                          </span>
                        ) : (
                          <span className="rounded bg-brand/10 px-1.5 py-0.5 text-[10px] text-brand">
                            完整
                          </span>
                        )}
                        {q.incomplete ? (
                          <button
                            type="button"
                            className="text-xs text-brand hover:underline ml-auto"
                            disabled={completeOne.isPending}
                            onClick={() => completeOne.mutate(q.id)}
                          >
                            LLM 补全
                          </button>
                        ) : null}
                      </div>
                      <p className="text-text break-words leading-relaxed">
                        <ExamMathText text={q.stem} mediaIngestId={q.media_ingest_id} />
                      </p>
                    </li>
                  ))}
                  {questionsQ.isFetched && !(questionsQ.data?.items || []).length ? (
                    <li className="text-text-muted text-xs">无匹配题目</li>
                  ) : null}
                </ul>
              </div>
            ) : null}
          </li>
        ))}
        {!colsQ.data?.items?.length ? (
          <p className="text-sm text-text-muted">
            暂无题库。{" "}
            <Link to="/admin/exam-bank/ingest?step=1" className="text-brand hover:underline">
              去创建
            </Link>
          </p>
        ) : null}
      </ul>
    </ExamWizardChrome>
  );
}

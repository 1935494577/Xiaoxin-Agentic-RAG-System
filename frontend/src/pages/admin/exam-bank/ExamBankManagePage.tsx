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
} from "../../../lib/examBank";
import { loadExamWizardDraft, saveExamWizardDraft } from "../../../lib/examWizardStore";
import { ExamField, ExamWizardChrome, examControlClass } from "./ExamWizardChrome";

export default function ExamBankManagePage() {
  const { session } = useAuth();
  const userId = session?.userId || session?.username || "";
  const qc = useQueryClient();
  const nav = useNavigate();
  const [error, setError] = useState("");
  const [activeId, setActiveId] = useState("");
  const [searchQ, setSearchQ] = useState("");
  const [committedQ, setCommittedQ] = useState("");

  const colsQ = useQuery({
    queryKey: ["exam-collections-manage", userId],
    queryFn: () => fetchExamCollections({ readerUserId: userId || undefined }),
  });

  const questionsQ = useQuery({
    queryKey: ["exam-questions-search", activeId, committedQ],
    queryFn: () => fetchExamQuestions(activeId, { status: "all", q: committedQ || undefined }),
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

  return (
    <ExamWizardChrome title="题库管理">
      {error ? <p className="text-sm text-warning">{error}</p> : null}
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
                <div className="flex flex-col sm:flex-row gap-2">
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
                  <div className="flex items-end">
                    <Button type="button" size="sm" onClick={() => setCommittedQ(searchQ.trim())}>
                      搜索
                    </Button>
                  </div>
                </div>
                <p className="text-xs text-text-muted">
                  共 {questionsQ.data?.total ?? "…"} 题
                  {committedQ ? ` · 关键词「${committedQ}」` : ""}
                </p>
                <ul className="max-h-64 overflow-auto space-y-2 text-sm">
                  {(questionsQ.data?.items || []).map((q) => (
                    <li key={q.id} className="rounded-lg border border-border px-3 py-2">
                      <p className="text-xs text-text-muted">
                        {q.qtype} · 难度 {q.difficulty}
                        {(q.knowledge_tags || []).length
                          ? ` · ${(q.knowledge_tags || []).join("、")}`
                          : ""}
                      </p>
                      <p className="text-text whitespace-pre-wrap break-words">{q.stem}</p>
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

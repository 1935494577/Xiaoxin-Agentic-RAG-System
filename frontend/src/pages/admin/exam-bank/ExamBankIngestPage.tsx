import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "../../../components/ui/Button";
import { useAuth } from "../../../context/AuthContext";
import {
  applyExamAnswers,
  cleanExamIngest,
  commitExamIngest,
  createExamCollection,
  deleteExamCollection,
  fetchExamCollections,
  fetchExamMeta,
  fetchExamSourcePapers,
  formatExamApiError,
  parseExamIngest,
  uploadExamIngest,
  uploadExamOcrIngest,
  fetchExamOcrStatus,
  type ExamIngestItem,
  fetchExamLlmStatus,
} from "../../../lib/examBank";
import {
  INGEST_STEPS,
  loadExamWizardDraft,
  saveExamWizardDraft,
  type ExamWizardDraft,
} from "../../../lib/examWizardStore";
import { ExamField, ExamWizardChrome, examControlClass } from "./ExamWizardChrome";

function WizardNav({
  showPrev,
  showNext,
  onPrev,
  onNext,
  nextLabel = "下一步",
  nextDisabled = false,
  nextBusy = false,
}: {
  showPrev: boolean;
  showNext: boolean;
  onPrev?: () => void;
  onNext?: () => void;
  nextLabel?: string;
  nextDisabled?: boolean;
  nextBusy?: boolean;
}) {
  if (!showPrev && !showNext) return null;
  return (
    <div className="flex justify-center items-center gap-3 pt-6">
      {showPrev ? (
        <Button type="button" size="sm" variant="ghost" onClick={onPrev}>
          上一步
        </Button>
      ) : null}
      {showNext ? (
        <Button
          type="button"
          size="sm"
          disabled={nextDisabled || nextBusy}
          onClick={onNext}
        >
          {nextLabel}
        </Button>
      ) : null}
    </div>
  );
}

export default function ExamBankIngestPage() {
  const { session } = useAuth();
  const userId = session?.userId || session?.username || "";
  const qc = useQueryClient();
  const nav = useNavigate();
  const [params, setParams] = useSearchParams();
  const step = Math.min(
    INGEST_STEPS.length,
    Math.max(1, Number(params.get("step") || 1) || 1),
  );

  const [draft, setDraft] = useState<ExamWizardDraft>(() => loadExamWizardDraft(userId));
  const [error, setError] = useState("");
  const [busyHint, setBusyHint] = useState("");
  const [cleanHint, setCleanHint] = useState("");

  useEffect(() => {
    setDraft(loadExamWizardDraft(userId));
  }, [userId]);

  useEffect(() => {
    saveExamWizardDraft(userId, { ...draft, step });
  }, [draft, step, userId]);

  const goStep = (n: number) => {
    setParams({ step: String(n) });
  };

  const patch = (p: Partial<ExamWizardDraft>) => setDraft((d) => ({ ...d, ...p }));

  const metaQ = useQuery({
    queryKey: ["exam-meta", draft.stage, draft.grade],
    queryFn: () => fetchExamMeta({ stage: draft.stage, grade: draft.grade }),
  });
  const llmStatusQ = useQuery({
    queryKey: ["exam-llm-status"],
    queryFn: () => fetchExamLlmStatus(),
    staleTime: 60_000,
  });
  const ocrStatusQ = useQuery({
    queryKey: ["exam-ocr-status"],
    queryFn: () => fetchExamOcrStatus(),
    staleTime: 60_000,
  });
  const subjects = metaQ.data?.subjects || [];
  const subjectMeta = subjects.find((s) => s.id === draft.subject) || subjects[0];
  const grades = subjectMeta?.grades || ["初一", "初二", "初三"];

  const metaReady = Boolean(draft.subject?.trim() && draft.grade?.trim());

  const colsQ = useQuery({
    queryKey: ["exam-collections", draft.subject, draft.grade, userId],
    queryFn: () =>
      fetchExamCollections({
        subject: draft.subject,
        grade: draft.grade,
      }),
    enabled: step >= 1 && metaReady,
    refetchOnMount: "always",
    staleTime: 0,
  });

  const sourcePapersQ = useQuery({
    queryKey: ["exam-source-papers", draft.collectionId],
    queryFn: () => fetchExamSourcePapers(draft.collectionId),
    enabled: Boolean(draft.collectionId) && step >= 4,
  });

  const draftItems: ExamIngestItem[] = useMemo(() => {
    try {
      return JSON.parse(draft.draftItemsJson || "[]");
    } catch {
      return [];
    }
  }, [draft.draftItemsJson]);

  const collections = colsQ.data?.items || [];

  const duplicateNames = useMemo(() => {
    const counts = new Map<string, number>();
    for (const c of collections) {
      const n = (c.name || "").trim();
      if (!n) continue;
      counts.set(n, (counts.get(n) || 0) + 1);
    }
    return [...counts.entries()].filter(([, n]) => n > 1).map(([n]) => n);
  }, [collections]);

  const resolvedCollectionName = (
    draft.region && draft.subject && draft.grade
      ? `${draft.region}·${draft.subject}·${draft.grade}`
      : draft.collectionName.trim() || ""
  ).trim();

  const scopeConflict =
    Boolean(draft.region && draft.subject && draft.grade) &&
    collections.some(
      (c) =>
        (c.region || "").trim() === draft.region.trim() &&
        (c.subject || "").trim() === draft.subject.trim() &&
        (c.grade || "").trim() === draft.grade.trim(),
    );

  const metaDone = Boolean(
    draft.stage?.trim() &&
      draft.subject?.trim() &&
      draft.grade?.trim() &&
      draft.region?.trim(),
  );
  const selectedInList = Boolean(
    draft.collectionId && collections.some((c) => c.id === draft.collectionId),
  );
  /** 第 1 步：学段学科年级地区 + 已选题库 */
  const setupDone = metaDone && selectedInList;
  const previewCanProceed =
    draftItems.some((x) => x.selected) || draftItems.length === 0;

  const step1FormSyncedRef = useRef(false);
  useEffect(() => {
    if (step !== 1) {
      step1FormSyncedRef.current = false;
      return;
    }
    if (!colsQ.isFetched) return;
    const items = colsQ.data?.items || [];

    setDraft((d) => {
      const id = (d.collectionId || "").trim();
      if (id && !items.some((c) => c.id === id)) {
        return {
          ...d,
          collectionId: "",
          collectionName: "",
          region: "",
          sourcePaperId: "",
        };
      }
      return d;
    });

    if (!step1FormSyncedRef.current) {
      step1FormSyncedRef.current = true;
      setDraft((d) => {
        if ((d.collectionId || "").trim()) return d;
        if (!d.collectionName && !d.region) return d;
        return { ...d, collectionName: "", region: "" };
      });
    }
  }, [step, colsQ.isFetched, colsQ.dataUpdatedAt, colsQ.data?.items]);

  useEffect(() => {
    if (step > 1 && !setupDone && colsQ.isFetched) goStep(1);
  }, [step, setupDone, colsQ.isFetched]);

  const createCol = useMutation({
    mutationFn: () => {
      if (!metaDone) {
        throw new Error(
          JSON.stringify({ detail: { message: "请先选择学段、学科、年级与地区" } }),
        );
      }
      if (scopeConflict) {
        throw new Error(
          JSON.stringify({
            detail: {
              error: "collection_scope_conflict",
              message: `已存在「${resolvedCollectionName}」，请直接选用该题库`,
            },
          }),
        );
      }
      return createExamCollection({
        name: resolvedCollectionName,
        subject: draft.subject,
        grade: draft.grade,
        region: draft.region,
        visibility: draft.visibility,
      });
    },
    onSuccess: (row) => {
      patch({
        collectionId: row.id,
        collectionName: row.name,
        region: row.region || draft.region,
      });
      void qc.invalidateQueries({ queryKey: ["exam-collections"] });
      setError("");
    },
    onError: (e: Error) => setError(formatExamApiError(e.message)),
  });

  const delCol = useMutation({
    mutationFn: (id: string) => deleteExamCollection(id),
    onSuccess: (_body, id) => {
      setDraft((d) => {
        if (d.collectionId !== id) return d;
        return {
          ...d,
          collectionId: "",
          collectionName: "",
          region: "",
          sourcePaperId: "",
        };
      });
      void qc.invalidateQueries({ queryKey: ["exam-collections"] });
      setError("");
    },
    onError: (e: Error) => setError(formatExamApiError(e.message)),
  });

  const parseMut = useMutation({
    mutationFn: async (opts?: { useLlm?: boolean }) => {
      const useLlm = opts?.useLlm ?? true;
      setBusyHint(useLlm ? "正在清洗并大模型拆题…" : "正在清洗并以规则精准拆题…");
      return parseExamIngest({
        text: draft.paperText,
        subject: draft.subject,
        grade: draft.grade,
        region: draft.region,
        stage: draft.stage,
        use_llm: useLlm,
        clean: true,
      });
    },
    onSuccess: (body) => {
      setBusyHint("");
      if (
        body.error === "llm_extract_failed" ||
        body.router === "llm_failed" ||
        body.error === "llm_api_error" ||
        body.error === "llm_empty_items"
      ) {
        setError(
          body.message ||
            "大模型拆题未成功。可点「规则精准拆题」，或检查模型 API。",
        );
        if (body.cleaned_text) {
          patch({
            cleanedText: body.cleaned_text,
            cleanWarningsJson: JSON.stringify(body.clean_warnings || []),
            ingestRawText: body.raw_text || draft.paperText,
          });
        }
        return;
      }
      const items = (body.items || []).map((it) => ({
        ...it,
        selected: it.selected !== false,
        options: it.options || [],
        knowledge_tags: it.knowledge_tags || [],
      }));
      if (!items.length) {
        setError("未识别到正式试题，请换卷或改用规则拆题。");
        return;
      }
      patch({
        draftItemsJson: JSON.stringify(items),
        ingestRawText: body.raw_text || draft.paperText,
        cleanedText: body.cleaned_text || "",
        cleanWarningsJson: JSON.stringify(body.clean_warnings || []),
        mediaJson: JSON.stringify(body.media || []),
        ingestFilename: "",
        answersEmbedded: Boolean(body.answers_embedded),
      });
      setError("");
      goStep(3);
    },
    onError: (e: Error) => {
      setBusyHint("");
      const msg = formatExamApiError(e.message);
      if (/abort|timeout|timed out|signal is aborted/i.test(msg) || e.name === "AbortError") {
        setError("拆题请求超时或被中断。整卷拆题可能需要 1～3 分钟，请稍后重试。");
        return;
      }
      setError(msg);
    },
  });

  const cleanMut = useMutation({
    mutationFn: async () => cleanExamIngest(draft.paperText),
    onSuccess: (body) => {
      patch({
        cleanedText: body.cleaned || "",
        cleanWarningsJson: JSON.stringify(body.warnings || []),
      });
      setCleanHint(
        `已清洗：去掉 ${(body.removed_sections || []).join("、") || "无"}；${body.stats?.line_count ?? "?"} 行`,
      );
      setError("");
    },
    onError: (e: Error) => setError(formatExamApiError(e.message)),
  });

  const uploadMut = useMutation({
    mutationFn: async (file: File) => {
      setBusyHint("正在抽取公式占位、清洗并拆题…");
      return uploadExamIngest(file, {
        subject: draft.subject,
        grade: draft.grade,
        region: draft.region,
        stage: draft.stage,
        use_llm: draft.useLlm,
        clean: true,
      });
    },
    onSuccess: (body) => {
      setBusyHint("");
      if (
        body.error === "llm_extract_failed" ||
        body.router === "llm_failed" ||
        body.error === "llm_api_error" ||
        body.error === "llm_empty_items"
      ) {
        setError(body.message || "大模型拆题未成功。公式占位已抽取，可改规则拆题。");
        patch({
          paperText: body.raw_text || draft.paperText,
          cleanedText: body.cleaned_text || "",
          cleanWarningsJson: JSON.stringify([
            ...(body.clean_warnings || []),
            ...(body.extract_warnings || []),
          ]),
          mediaJson: JSON.stringify(body.media || []),
          ingestRawText: body.raw_text || "",
          ingestFilename: body.source_filename || "",
        });
        return;
      }
      const items = (body.items || []).map((it) => ({
        ...it,
        selected: it.selected !== false,
        options: it.options || [],
        knowledge_tags: it.knowledge_tags || [],
      }));
      if (!items.length) {
        setError("未识别到正式试题，请换卷或改用规则拆题。");
        return;
      }
      patch({
        paperText: body.raw_text || draft.paperText,
        ingestRawText: body.raw_text || "",
        ingestFilename: body.source_filename || "",
        cleanedText: body.cleaned_text || "",
        cleanWarningsJson: JSON.stringify(body.clean_warnings || []),
        mediaJson: JSON.stringify(body.media || []),
        draftItemsJson: JSON.stringify(items),
        answersEmbedded: Boolean(body.answers_embedded),
      });
      setError("");
      goStep(3);
    },
    onError: (e: Error) => {
      setBusyHint("");
      const msg = formatExamApiError(e.message);
      if (/abort|timeout|timed out|signal is aborted/i.test(msg) || e.name === "AbortError") {
        setError("拆题请求超时或被中断。整卷拆题可能需要 1～3 分钟，请稍后重试。");
        return;
      }
      setError(msg);
    },
  });

  const ocrMut = useMutation({
    mutationFn: async (file: File) => {
      setBusyHint("正在 OCR 识别扫描件（可能需数分钟）…");
      return uploadExamOcrIngest(file, {
        subject: draft.subject,
        grade: draft.grade,
        region: draft.region,
        stage: draft.stage,
        use_llm: draft.useLlm,
        clean: true,
      });
    },
    onSuccess: (body) => {
      setBusyHint("");
      const items = (body.items || []).map((it) => ({
        ...it,
        selected: it.selected !== false,
        options: it.options || [],
        knowledge_tags: it.knowledge_tags || [],
      }));
      if (!items.length) {
        setError("OCR 已出文字但未拆出试题，可先预览正文后改用规则拆题。");
        patch({
          paperText: body.raw_text || draft.paperText,
          ingestRawText: body.raw_text || "",
          ingestFilename: body.source_filename || "",
          cleanedText: body.cleaned_text || "",
          cleanWarningsJson: JSON.stringify([
            ...(body.clean_warnings || []),
            ...(body.ocr_warnings || []),
          ]),
        });
        return;
      }
      patch({
        paperText: body.raw_text || draft.paperText,
        ingestRawText: body.raw_text || "",
        ingestFilename: body.source_filename || "",
        cleanedText: body.cleaned_text || "",
        cleanWarningsJson: JSON.stringify([
          ...(body.clean_warnings || []),
          ...(body.ocr_warnings || []),
          body.ocr_engine ? `OCR:${body.ocr_engine} ${body.ocr_page_count || 0}页` : "",
        ].filter(Boolean)),
        draftItemsJson: JSON.stringify(items),
        answersEmbedded: Boolean(body.answers_embedded),
      });
      setError("");
      goStep(3);
    },
    onError: (e: Error) => {
      setBusyHint("");
      const msg = formatExamApiError(e.message);
      if (/ocr_unavailable|rapidocr|paddleocr|pymupdf|pypdfium2/i.test(msg)) {
        setError(
          `${msg}\n请执行：pip install -r requirements-exam-optional.txt -i https://pypi.tuna.tsinghua.edu.cn/simple 后重启后端。`,
        );
        return;
      }
      if (/abort|timeout|timed out|signal is aborted/i.test(msg) || e.name === "AbortError") {
        setError("OCR 超时。扫描 PDF 页数较多时请拆成少页再试，或提高超时后重试。");
        return;
      }
      setError(msg);
    },
  });

  const commitMut = useMutation({
    mutationFn: () => {
      let mediaIngestId = "";
      try {
        const media = JSON.parse(draft.mediaJson || "[]") as { ingest_id?: string }[];
        mediaIngestId = (media.find((m) => m.ingest_id)?.ingest_id || "").trim();
      } catch {
        mediaIngestId = "";
      }
      return commitExamIngest({
        collection_id: draft.collectionId,
        title: draft.ingestFilename || "导入试卷",
        source_filename: draft.ingestFilename,
        raw_text: draft.ingestRawText || draft.paperText,
        region: draft.region,
        year: draft.paperYear,
        quality_status: "published",
        media_ingest_id: mediaIngestId,
        items: draftItems,
      });
    },
    onSuccess: (body) => {
      patch({
        sourcePaperId: body.source_paper.id,
        draftItemsJson: "[]",
      });
      void qc.invalidateQueries({ queryKey: ["exam-questions", draft.collectionId] });
      void qc.invalidateQueries({ queryKey: ["exam-source-papers", draft.collectionId] });
      setError("");
      goStep(4);
    },
    onError: (e: Error) => setError(formatExamApiError(e.message)),
  });

  const applyAns = useMutation({
    mutationFn: () =>
      applyExamAnswers({
        source_paper_id: draft.sourcePaperId,
        answer_text: draft.answerText,
      }),
    onSuccess: (body) => {
      setError(
        body.unmatched?.length
          ? `已写入 ${body.updated} 题；未匹配：${body.unmatched.join(", ")}`
          : `已写入 ${body.updated} 题答案`,
      );
      void qc.invalidateQueries({ queryKey: ["exam-questions", draft.collectionId] });
    },
    onError: (e: Error) => setError(formatExamApiError(e.message)),
  });

  useEffect(() => {
    const first = sourcePapersQ.data?.items?.[0]?.id;
    if (first && !draft.sourcePaperId) patch({ sourcePaperId: first });
  }, [sourcePapersQ.data?.items, draft.sourcePaperId]);

  const showPrev = step > 1 && setupDone;
  const nextDisabledSetup = !setupDone;
  const nextDisabledPreview =
    !(setupDone && previewCanProceed) || commitMut.isPending;
  const finishDisabled = !setupDone;

  return (
    <ExamWizardChrome title="试卷入库" step={step}>
      {error ? (
        <p className="mx-auto max-w-xl text-sm text-warning whitespace-pre-wrap rounded-lg border border-warning/40 bg-warning/5 px-3 py-2 text-center">
          {error}
        </p>
      ) : null}
      {busyHint ? <p className="mx-auto max-w-xl text-sm text-brand text-center">{busyHint}</p> : null}

      {step === 1 ? (
        <section className="mx-auto w-full max-w-xl space-y-5">
          <div className="rounded-xl border-2 border-border bg-surface p-4 space-y-4 shadow-sm">
            <p className="text-sm font-medium text-text text-center">基本信息</p>
            <div className="grid gap-3 sm:grid-cols-3">
              <ExamField label="学段">
                <select
                  className={examControlClass}
                  value={draft.stage}
                  onChange={(e) => patch({ stage: e.target.value })}
                >
                  {(metaQ.data?.stages || []).map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </ExamField>
              <ExamField label="学科">
                <select
                  className={examControlClass}
                  value={draft.subject}
                  onChange={(e) => {
                    const id = e.target.value;
                    const meta = subjects.find((s) => s.id === id);
                    patch({
                      subject: id,
                      grade: meta?.grades?.[0] || draft.grade,
                      collectionId: "",
                      collectionName: "",
                      region: "",
                    });
                  }}
                >
                  {(subjects.length ? subjects : [{ id: "数学", label: "数学" }]).map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </ExamField>
              <ExamField label="年级">
                <select
                  className={examControlClass}
                  value={draft.grade}
                  onChange={(e) =>
                    patch({
                      grade: e.target.value,
                      collectionId: "",
                      collectionName: "",
                      region: "",
                    })
                  }
                >
                  {grades.map((g) => (
                    <option key={g} value={g}>
                      {g}
                    </option>
                  ))}
                </select>
              </ExamField>
            </div>
          </div>

          <div className="rounded-xl border-2 border-border bg-surface p-4 space-y-4 shadow-sm">
            <p className="text-sm font-medium text-text text-center">题库空间</p>
            <div className="grid gap-3 sm:grid-cols-2">
              <ExamField label="地区（必选）">
                <select
                  className={examControlClass}
                  value={draft.region}
                  onChange={(e) => patch({ region: e.target.value, collectionId: "" })}
                >
                  <option value="">请选择省市</option>
                  {(metaQ.data?.common_regions || []).map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </ExamField>
              <ExamField label="自动库名">
                <input
                  className={examControlClass}
                  value={resolvedCollectionName || "选择地区·学科·年级后生成"}
                  readOnly
                  disabled
                />
              </ExamField>
              <ExamField label="试卷年份（可选）">
                <input
                  className={examControlClass}
                  placeholder="如：2024（也可从文件名识别）"
                  value={draft.paperYear}
                  onChange={(e) => patch({ paperYear: e.target.value.trim() })}
                />
              </ExamField>
              <ExamField label="可见范围">
                <select
                  className={examControlClass}
                  value={draft.visibility}
                  onChange={(e) => patch({ visibility: e.target.value })}
                >
                  <option value="private">私有（仅自己）</option>
                  <option value="tenant_shared">组织共享</option>
                  <option value="platform">平台精选</option>
                </select>
              </ExamField>
            </div>

            {scopeConflict ? (
              <p className="text-xs text-warning text-center">
                「{resolvedCollectionName}」已存在，请在下方直接选用
              </p>
            ) : null}

            <div className="flex justify-center">
              <Button
                type="button"
                size="sm"
                onClick={() => createCol.mutate()}
                disabled={createCol.isPending || Boolean(scopeConflict) || !metaDone}
              >
                {createCol.isPending ? "创建中…" : "创建地区题库"}
              </Button>
            </div>

            {collections.length > 0 ? (
              <div className="space-y-2 border-t border-border pt-3">
                <p className="text-xs text-text-muted text-center">已有题库（点击选用）</p>
                <div className="flex flex-wrap justify-center gap-2">
                  {collections.map((c) => {
                    const dup = duplicateNames.includes((c.name || "").trim());
                    const selected = draft.collectionId === c.id;
                    return (
                      <div
                        key={c.id}
                        className={`inline-flex items-stretch rounded-lg border-2 text-xs ${
                          selected
                            ? "border-brand bg-brand/10 text-brand"
                            : dup
                              ? "border-warning/60 text-warning"
                              : "border-border text-text-muted"
                        }`}
                      >
                        <button
                          type="button"
                          className="px-3 py-2"
                          onClick={() => {
                            patch({
                              collectionId: c.id,
                              collectionName: c.name,
                              region: c.region || "",
                              subject: c.subject || draft.subject,
                              grade: c.grade || draft.grade,
                            });
                            setError("");
                          }}
                        >
                          {(c.region || "?") + " · " + (c.subject || "") + " · " + (c.grade || "")}
                        </button>
                        <button
                          type="button"
                          className="px-2 border-l border-inherit opacity-70 hover:opacity-100 hover:bg-black/5"
                          title="删除"
                          aria-label={`删除 ${c.name}`}
                          disabled={delCol.isPending}
                          onClick={() => {
                            if (
                              !window.confirm(
                                `确定删除题库「${c.name}」？其中的题目也会一并删除。`,
                              )
                            ) {
                              return;
                            }
                            delCol.mutate(c.id);
                          }}
                        >
                          ×
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : null}
          </div>

          <WizardNav
            showPrev={false}
            showNext
            nextDisabled={nextDisabledSetup}
            onNext={() => {
              if (nextDisabledSetup) return;
              setError("");
              goStep(2);
            }}
          />
          <p className="text-center">
            <Link to="/admin/exam-bank" className="text-sm text-text-muted hover:text-brand">
              返回首页
            </Link>
          </p>
        </section>
      ) : null}

      {step === 2 ? (
        <section className="mx-auto w-full max-w-3xl space-y-5">
          {!setupDone ? (
            <p className="text-sm text-warning text-center rounded-xl border-2 border-warning/40 bg-warning/5 px-3 py-2">
              请先完成上一步并选用题库
            </p>
          ) : (
            <div className="rounded-xl border-2 border-border bg-surface p-4 space-y-4 shadow-sm">
              <p className="text-sm font-medium text-text text-center">
                「{draft.subject}
                {draft.grade ? ` · ${draft.grade}` : ""}
                {draft.region ? ` · ${draft.region}` : ""}」试卷导入
              </p>
              {llmStatusQ.data ? (
                <p
                  className={`text-xs text-center rounded-lg border px-3 py-2 ${
                    llmStatusQ.data.configured
                      ? "border-brand/30 bg-brand/5 text-brand"
                      : "border-warning/40 bg-warning/5 text-warning"
                  }`}
                >
                  {llmStatusQ.data.message}
                  {llmStatusQ.data.configured && llmStatusQ.data.model
                    ? `（${llmStatusQ.data.model}）`
                    : ""}
                  {!llmStatusQ.data.configured
                    ? " — 仍可用「规则精准拆题」处理高考真题结构。"
                    : ""}
                </p>
              ) : null}
              {ocrStatusQ.data ? (
                <p
                  className={`text-xs text-center rounded-lg border px-3 py-2 ${
                    ocrStatusQ.data.available
                      ? "border-border bg-surface-muted/40 text-text-muted"
                      : "border-warning/40 bg-warning/5 text-warning"
                  }`}
                >
                  {ocrStatusQ.data.available
                    ? `OCR 就绪（${(ocrStatusQ.data.engines || []).join(" + ") || "paddleocr"}）：扫描 PDF/图片可走「OCR 扫描件入库」，无需扫描王`
                    : `OCR 未安装：${ocrStatusQ.data.hint || "pip install -r requirements-exam-optional.txt"}（请装到项目 .venv）`}
                </p>
              ) : null}
              <ExamField label="粘贴试卷全文（可含答案解析）">
                <textarea
                  className={`${examControlClass} min-h-[140px] resize-y`}
                  placeholder="将试卷文本粘贴到此处…"
                  value={draft.paperText}
                  onChange={(e) => patch({ paperText: e.target.value })}
                />
              </ExamField>
              {draft.cleanedText ? (
                <div className="space-y-2">
                  <p className="text-xs font-medium text-text-muted">清洗后预览（注意事项已剔除）</p>
                  {cleanHint ? <p className="text-xs text-brand">{cleanHint}</p> : null}
                  <pre className="max-h-40 overflow-auto rounded-lg border border-border bg-surface-muted/40 p-3 text-xs whitespace-pre-wrap">
                    {draft.cleanedText.slice(0, 4000)}
                    {draft.cleanedText.length > 4000 ? "\n…" : ""}
                  </pre>
                </div>
              ) : null}
              <div className="flex flex-col sm:flex-row justify-center gap-2 items-stretch sm:items-center flex-wrap">
                <label
                  className={`${examControlClass} cursor-pointer text-center text-brand border-brand/40 hover:bg-brand/5 sm:flex-1`}
                >
                  <input
                    type="file"
                    accept=".pdf,.docx,.doc,.txt,.md"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) uploadMut.mutate(f);
                      e.target.value = "";
                    }}
                  />
                  {uploadMut.isPending ? "解析中…" : "上传 PDF / Word"}
                </label>
                <label
                  className={`${examControlClass} cursor-pointer text-center sm:flex-1 ${
                    ocrStatusQ.data?.available === false
                      ? "opacity-60 border-dashed"
                      : "text-brand border-brand/40 hover:bg-brand/5"
                  }`}
                  title={
                    ocrStatusQ.data?.available === false
                      ? ocrStatusQ.data.hint || "需安装 OCR 可选依赖"
                      : "扫描件 / 图片 PDF，本地 PaddleOCR，无需扫描王"
                  }
                >
                  <input
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg,.webp,.tif,.tiff,.bmp"
                    className="hidden"
                    disabled={ocrMut.isPending}
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) ocrMut.mutate(f);
                      e.target.value = "";
                    }}
                  />
                  {ocrMut.isPending
                    ? "OCR 识别中…"
                    : ocrStatusQ.data?.available === false
                      ? "OCR 未安装"
                      : "OCR 扫描件入库"}
                </label>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  disabled={!draft.paperText.trim() || cleanMut.isPending}
                  onClick={() => cleanMut.mutate()}
                >
                  {cleanMut.isPending ? "清洗中…" : "预览清洗"}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  className="sm:flex-1 py-2.5"
                  onClick={() => parseMut.mutate({ useLlm: true })}
                  disabled={
                    !draft.paperText.trim() ||
                    parseMut.isPending ||
                    llmStatusQ.data?.configured === false
                  }
                >
                  {parseMut.isPending ? "拆题中…" : "智能拆题并预览"}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="default"
                  disabled={!draft.paperText.trim() || parseMut.isPending}
                  onClick={() => parseMut.mutate({ useLlm: false })}
                >
                  规则精准拆题
                </Button>
              </div>
              <p className="text-[11px] text-text-muted text-center">
                Word 中 MathType 公式会保留为 [[EQ:n]] 占位并落盘图片，避免选项内容丢失
              </p>
            </div>
          )}
          <WizardNav
            showPrev={showPrev || step > 1}
            showNext={false}
            onPrev={() => {
              setError("");
              goStep(1);
            }}
          />
        </section>
      ) : null}

      {step === 3 ? (
        <section className="mx-auto w-full max-w-xl space-y-5">
          {draftItems.length > 0 ? (
            <div className="rounded-xl border-2 border-border bg-surface p-4 space-y-3 shadow-sm">
              <p className="text-sm font-medium text-text text-center">预览编辑</p>
              <p className="text-xs text-text-muted text-center">
                共 {draftItems.length} 题
                {draft.answersEmbedded ? " · 卷内已含答案" : " · 答案待补全"}
                {" · "}
                选项齐全{" "}
                {
                  draftItems.filter(
                    (x) =>
                      !["choice", "multi"].includes(x.qtype) ||
                      (x.options || []).length >= 4,
                  ).length
                }
                /{draftItems.length}
                {" · "}
                含公式占位{" "}
                {
                  draftItems.filter(
                    (x) =>
                      /\[\[EQ:\d+\]\]/.test(x.stem || "") ||
                      (x.options || []).some((o) => /\[\[EQ:\d+\]\]/.test(o)),
                  ).length
                }{" "}
                题；勾选后确认入库
              </p>
              <ul className="max-h-80 overflow-auto space-y-3 text-sm">
                {draftItems.map((it, idx) => (
                  <li
                    key={`${it.question_no}-${idx}`}
                    className="rounded-lg border-2 border-border bg-surface-muted/30 p-3 flex gap-3 items-start"
                  >
                    <input
                      type="checkbox"
                      className="mt-1 h-4 w-4 accent-brand shrink-0"
                      checked={it.selected}
                      onChange={(e) => {
                        const next = draftItems.map((r, i) =>
                          i === idx ? { ...r, selected: e.target.checked } : r,
                        );
                        patch({ draftItemsJson: JSON.stringify(next) });
                      }}
                    />
                    <div className="min-w-0 flex-1 space-y-1.5">
                      <p className="text-xs text-text-muted">
                        第 {it.question_no || "?"} 题 · {it.label || it.qtype}
                        {(it.options || []).length
                          ? ` · ${it.options.length} 选项`
                          : ""}
                        {/\[\[EQ:\d+\]\]/.test(it.stem || "") ||
                        (it.options || []).some((o) => /\[\[EQ:\d+\]\]/.test(o))
                          ? " · 含公式图"
                          : ""}
                        {typeof it.difficulty === "number" ? ` · 难度 ${it.difficulty}` : ""}
                        {(it.knowledge_tags || []).length
                          ? ` · ${(it.knowledge_tags || []).join("、")}`
                          : ""}
                        {it.chapter ? ` · 章:${it.chapter}` : ""}
                        {it.answer ? ` · 答案 ${it.answer}` : ""}
                      </p>
                      <p className="text-text whitespace-pre-wrap break-words leading-relaxed">
                        {it.stem}
                      </p>
                      {(it.options || []).length > 0 ? (
                        <div className="grid gap-1.5 sm:grid-cols-2">
                          {(it.options || []).map((opt, oi) => (
                            <div
                              key={`${idx}-opt-${oi}`}
                              className="rounded-md border border-border bg-surface px-2.5 py-1.5 text-xs text-text"
                            >
                              {opt}
                            </div>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-sm text-text-muted text-center rounded-xl border-2 border-border px-3 py-4">
              暂无拆题结果，请返回上一步重新解析
            </p>
          )}

          <WizardNav
            showPrev={showPrev}
            showNext
            nextDisabled={nextDisabledPreview}
            nextBusy={commitMut.isPending}
            nextLabel={
              draftItems.some((x) => x.selected)
                ? commitMut.isPending
                  ? "入库中…"
                  : "确认入库并下一步"
                : "下一步"
            }
            onPrev={() => {
              setError("");
              goStep(2);
            }}
            onNext={() => {
              if (nextDisabledPreview) return;
              if (draftItems.some((x) => x.selected)) {
                commitMut.mutate();
                return;
              }
              setError("");
              goStep(4);
            }}
          />
        </section>
      ) : null}

      {step === 4 ? (
        <section className="mx-auto w-full max-w-xl space-y-5">
          <div className="rounded-xl border-2 border-border bg-surface p-4 space-y-4 shadow-sm">
            <p className="text-sm font-medium text-text text-center">答案关联</p>
            {draft.answersEmbedded ? (
              <p className="text-xs text-text-muted text-center">
                卷内已解析出答案，可直接完成；也可粘贴补充答案卷按题号覆盖。
              </p>
            ) : (
              <p className="text-xs text-text-muted text-center">
                卷内未带齐答案：可粘贴答案文档按题号写入，或稍后在题库中补。
              </p>
            )}
            <ExamField label="源试卷（可空）">
              <select
                className={examControlClass}
                value={draft.sourcePaperId}
                onChange={(e) => patch({ sourcePaperId: e.target.value })}
              >
                <option value="">选择源试卷</option>
                {(sourcePapersQ.data?.items || []).map((sp) => (
                  <option key={sp.id} value={sp.id}>
                    {sp.title || sp.id.slice(0, 8)}
                  </option>
                ))}
              </select>
            </ExamField>
            <ExamField label="答案文本（按题号）">
              <textarea
                className={`${examControlClass} min-h-[100px] resize-y`}
                placeholder={"1. A\n2. B\n3. …"}
                value={draft.answerText}
                onChange={(e) => patch({ answerText: e.target.value })}
              />
            </ExamField>
            <div className="flex flex-wrap justify-center gap-2">
              <Button
                type="button"
                size="sm"
                onClick={() => applyAns.mutate()}
                disabled={!draft.sourcePaperId || !draft.answerText.trim() || applyAns.isPending}
              >
                按题号写入答案
              </Button>
              <Button type="button" size="sm" variant="ghost" onClick={() => nav("/admin/exam-bank")}>
                稍后补充，回首页
              </Button>
            </div>
          </div>
          <WizardNav
            showPrev={showPrev}
            showNext
            nextDisabled={finishDisabled}
            nextLabel="完成，去组卷"
            onPrev={() => {
              setError("");
              goStep(3);
            }}
            onNext={() => {
              if (finishDisabled) return;
              nav("/admin/exam-bank/assemble");
            }}
          />
        </section>
      ) : null}

      <p className="text-xs text-text-muted text-center">
        步骤 {step}/{INGEST_STEPS.length}
      </p>
    </ExamWizardChrome>
  );
}
